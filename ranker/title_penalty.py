import re
from sentence_transformers.util import cos_sim

def get_dynamic_title_penalty(candidate_title, target_title, dense_model=None, precomputed_sim=None):
    """
    Dynamically aligns candidate current title against the target position title
    using keyword overlap and semantic cosine similarity checks.
    """
    if not candidate_title or not target_title:
        return 1.0, "Title matched (no verification possible, 1.0x)"
        
    candidate_lower = candidate_title.lower()
    target_lower = target_title.lower()
    
    # Check for direct keyword matches, stripping out seniority and stop words
    ignore_words = {"senior", "junior", "lead", "staff", "principal", "associate", "head", "director", "manager", "vp", "intern", "of", "and", "the", "in", "for", "with", "level", "ii", "iii", "iv", "v"}
    target_words = set(re.findall(r'\b\w+\b', target_lower)) - ignore_words
    candidate_words = set(re.findall(r'\b\w+\b', candidate_lower)) - ignore_words
    
    if not target_words:
        # Target title has only stop words, skip title match check
        return 1.0, "Standard title alignment (1.0x)"
        
    # direct overlap of core words
    if target_words & candidate_words:
        return 1.0, f"Title matched via keyword overlap: '{candidate_title}' is relevant to target '{target_title}' (1.0x)"
        
    # Semantic match using precomputed similarity or dense model if loaded
    sim = precomputed_sim
    if sim is None and dense_model is not None:
        try:
            target_emb = dense_model.encode(target_title, convert_to_tensor=True, show_progress_bar=False)
            candidate_emb = dense_model.encode(candidate_title, convert_to_tensor=True, show_progress_bar=False)
            sim = float(cos_sim(target_emb, candidate_emb)[0][0].item())
        except Exception:
            pass
            
    if sim is not None:
        if sim >= 0.50:
            return 1.0, f"Title semantically relevant: '{candidate_title}' matches target '{target_title}' (similarity: {sim:.2f}, 1.0x)"
        else:
            # Scaled penalty down based on mismatch, minimum 0.2x
            penalty = max(0.2, round(sim * 1.5, 2)) if sim > 0 else 0.2
            penalty = min(1.0, penalty)
            return penalty, f"Title mismatch penalty applied (semantic similarity: {sim:.2f}, {penalty}x)"
            
    # Fallback mismatch penalty
    return 0.2, f"Title mismatch penalty applied (Current Title: '{candidate_title}' is not matching Target: '{target_title}', 0.2x)"
