import re
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder
from sentence_transformers.util import cos_sim
from rank_bm25 import BM25Okapi

from .utils import (
    tokenize,
    extract_keywords,
    synthesize_profile,
    sigmoid,
    log_progress
)
from .heuristics import (
    get_legacy_title_penalty,
    get_legacy_company_modifier,
    get_legacy_activity_modifier
)
from .title_penalty import get_dynamic_title_penalty

# Set PyTorch CPU thread limit to prevent thread locking and CPU contention on Windows
if torch.get_num_threads() > 4:
    torch.set_num_threads(4)

# Device configuration for model inference (GPU/CPU)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def run_ranking_pipeline(job_title, job_description, qualifications, candidates, use_mock_heuristics=False, status_callback=None):
    """
    Executes the full candidate ranking pipeline:
    1. Prepares candidate narratives.
    2. Runs BGE dense vector similarities.
    3. Runs BM25 sparse keyword scores (using dynamic keywords or default hardcoded list).
    4. Merges dense + sparse ranks using RRF.
    5. Re-ranks top 100 using MS-MARCO Cross-Encoder.
    6. Calibrates final scores using (legacy heuristics OR dynamic title matching).
    7. Sorts and returns all candidates.
    """
    total_candidates = len(candidates)
    if total_candidates == 0:
        return []
        
    log_progress(status_callback, f"Synthesizing profiles for {total_candidates} candidates...")
    for c in candidates:
        c["narrative"] = synthesize_profile(c)
        
    # --- STAGE 1: HYBRID RETRIEVAL ---
    
    # Query sentence: JD, qualifications and target title
    query_parts = []
    if job_title:
        query_parts.append(f"Job Title: {job_title}")
    if job_description:
        query_parts.append(f"Description: {job_description}")
    if qualifications:
        query_parts.append(f"Qualifications: {qualifications}")
        
    query_text = ". ".join(query_parts)
    jd_query = "Represent this sentence for searching relevant passages: " + query_text

    # BM25 keywords
    if use_mock_heuristics:
        # Use exact list from original script to maintain compatibility
        bm25_query_words = ["qdrant", "faiss", "lora", "xgboost", "pytorch", "llm", "rag", "transformers", "vector", "search"]
    else:
        # Dynamically extract keywords from input JD and qualifications
        bm25_query_words = extract_keywords(query_text, num_keywords=15)
        
    log_progress(status_callback, f"Analyzing profile keyword match indexes using BM25...")
    tokenized_corpus = [tokenize(c["narrative"]) for c in candidates]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(bm25_query_words).tolist()
    
    # If the candidate database is large, pre-filter via BM25 to avoid slow CPU dense encoding
    pre_filter_limit = 2000
    if total_candidates > pre_filter_limit:
        log_progress(status_callback, f"Pre-filtering: Reducing candidate pool from {total_candidates} to top {pre_filter_limit} via BM25 scores for CPU performance...")
        for idx, c in enumerate(candidates):
            c["_temp_bm25_score"] = bm25_scores[idx]
            
        candidates_sorted = sorted(candidates, key=lambda x: -x["_temp_bm25_score"])
        candidates = candidates_sorted[:pre_filter_limit]
        total_candidates = len(candidates)
        
        # Clean up temp key
        for c in candidates:
            c.pop("_temp_bm25_score", None)
            
        # Re-compute tokenized corpus and BM25 scores for the top candidates
        tokenized_corpus = [tokenize(c["narrative"]) for c in candidates]
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(bm25_query_words).tolist()

    log_progress(status_callback, f"Initializing candidate context semantic parser on {DEVICE}...")
    dense_model = SentenceTransformer("BAAI/bge-small-en-v1.5", device=DEVICE)
    
    log_progress(status_callback, f"Generating dense embeddings for top {total_candidates} profiles (batch encoding)...")
    profile_narratives = [c["narrative"] for c in candidates]
    
    profile_embeddings = dense_model.encode(
        profile_narratives, 
        batch_size=32, 
        show_progress_bar=False, 
        convert_to_tensor=True,
        device=DEVICE
    )
    jd_embedding = dense_model.encode(
        jd_query, 
        convert_to_tensor=True,
        device=DEVICE
    )
    
    log_progress(status_callback, "Computing dense similarities...")
    dense_similarities = cos_sim(jd_embedding, profile_embeddings)[0].cpu().numpy().tolist()
    
    log_progress(status_callback, "Blending semantic matching alignment with keyword indexing...")
    
    # Dense ranks
    dense_ranked_indices = sorted(
        range(total_candidates), 
        key=lambda i: (-dense_similarities[i], candidates[i].get("candidate_id", ""))
    )
    dense_ranks = {candidates[idx].get("candidate_id", ""): r + 1 for r, idx in enumerate(dense_ranked_indices)}
    
    # Sparse ranks
    sparse_ranked_indices = sorted(
        range(total_candidates), 
        key=lambda i: (-bm25_scores[i], candidates[i].get("candidate_id", ""))
    )
    sparse_ranks = {candidates[idx].get("candidate_id", ""): r + 1 for r, idx in enumerate(sparse_ranked_indices)}
    
    for idx, c in enumerate(candidates):
        cid = c.get("candidate_id", f"CAND_{idx}")
        r_dense = dense_ranks[cid]
        r_sparse = sparse_ranks[cid]
        
        c["rrf_score"] = 1.0 / (60.0 + r_dense) + 1.0 / (60.0 + r_sparse)
        c["dense_rank"] = r_dense
        c["sparse_rank"] = r_sparse
        c["dense_score"] = dense_similarities[idx]
        c["sparse_score"] = bm25_scores[idx]
        
    # Slice top 100 (or total if less)
    candidates_sorted_rrf = sorted(candidates, key=lambda x: (-x["rrf_score"], x.get("candidate_id", "")))
    top_n_candidates = candidates_sorted_rrf[:100]
    
    # --- STAGE 2: DEEP CONTEXTUAL RE-RANKING ---
    log_progress(status_callback, "Activating high-precision profile validation checker...")
    cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device=DEVICE)
    
    # Pair Job Profile and Narrative
    pairs = [(query_text, c["narrative"]) for c in top_n_candidates]
    
    log_progress(status_callback, f"Evaluating detailed qualification alignments for top candidate profiles...")
    semantic_scores = cross_encoder.predict(pairs, batch_size=32, show_progress_bar=False)
    
    for c, score in zip(top_n_candidates, semantic_scores):
        c["s_semantic"] = float(score)
        
    # --- STAGE 3: BEHAVIORAL CALIBRATION ---
    log_progress(status_callback, "Performing profile calibration checks and adjustments...")
    
    # Precompute semantic title similarities in batch to avoid slow one-by-one encoding
    if not use_mock_heuristics and dense_model is not None:
        candidates_needing_semantic = []
        titles_needing_semantic = []
        
        for c in top_n_candidates:
            if "raw_resume_text" in c:
                continue
            candidate_title = c.get("current_title", c.get("title", ""))
            if not candidate_title or not job_title:
                continue
            
            candidate_lower = candidate_title.lower()
            target_lower = job_title.lower()
            
            ignore_words = {"senior", "junior", "lead", "staff", "principal", "associate", "head", "director", "manager", "vp", "intern", "of", "and", "the", "in", "for", "with", "level", "ii", "iii", "iv", "v"}
            target_words = set(re.findall(r'\b\w+\b', target_lower)) - ignore_words
            candidate_words = set(re.findall(r'\b\w+\b', candidate_lower)) - ignore_words
            
            if not target_words:
                continue
            if target_words & candidate_words:
                continue
                
            candidates_needing_semantic.append(c)
            titles_needing_semantic.append(candidate_title)
            
        if titles_needing_semantic:
            log_progress(status_callback, f"Batch encoding {len(titles_needing_semantic)} candidate titles for semantic calibration...")
            try:
                target_emb = dense_model.encode(job_title, convert_to_tensor=True, show_progress_bar=False, device=DEVICE)
                candidate_embs = dense_model.encode(
                    titles_needing_semantic,
                    batch_size=32,
                    show_progress_bar=False,
                    convert_to_tensor=True,
                    device=DEVICE
                )
                sim_scores = cos_sim(target_emb, candidate_embs)[0].cpu().numpy().tolist()
                
                for c, sim in zip(candidates_needing_semantic, sim_scores):
                    c["_precomputed_title_sim"] = float(sim)
            except Exception as e:
                log_progress(status_callback, f"Error during batch title encoding: {e}")

    for c in top_n_candidates:
        s_semantic_raw = c["s_semantic"]
        s_semantic_prob = sigmoid(s_semantic_raw)
        
        if use_mock_heuristics:
            title_mult, title_reason = get_legacy_title_penalty(c.get("current_title", ""))
            company_mult, company_reason = get_legacy_company_modifier(c.get("experience", []))
            activity_mult, activity_reason = get_legacy_activity_modifier(c)
        else:
            # Dynamic matching
            if "raw_resume_text" in c:
                title_mult = 1.0
                title_reason = "Title match penalty skipped for raw resume upload (1.0x)"
            else:
                precomputed_sim = c.get("_precomputed_title_sim")
                title_mult, title_reason = get_dynamic_title_penalty(
                    c.get("current_title", c.get("title", "")), 
                    job_title, 
                    dense_model=dense_model, 
                    precomputed_sim=precomputed_sim
                )
            company_mult, company_reason = 1.0, "No company penalty applied (Dynamic upload)"
            activity_mult, activity_reason = 1.0, "No activity penalty applied (Dynamic upload)"
            
        final_score = s_semantic_prob * title_mult * company_mult * activity_mult
        
        c["s_semantic_prob"] = s_semantic_prob
        c["title_mult"] = title_mult
        c["company_mult"] = company_mult
        c["activity_mult"] = activity_mult
        c["final_score"] = final_score
        
        reasons = [
            f"Semantic Relevance Match: {s_semantic_prob * 100:.1f}%",
            f"Requirement Alignment: {title_reason}",
            f"Experience Profile check: {company_reason}",
            f"Platform Activity status: {activity_reason}"
        ]
        c["reasoning"] = ". ".join(reasons)
        
        # Remove the temporary key
        c.pop("_precomputed_title_sim", None)
        
    log_progress(status_callback, "Pipeline processing complete. Sorting results...")
    
    # Sort by score descending, then candidate_id ascending
    final_sorted_candidates = sorted(
        top_n_candidates,
        key=lambda x: (-x["final_score"], x.get("candidate_id", ""))
    )
    
    return final_sorted_candidates
