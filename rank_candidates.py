import json
import os
import csv
import sys
from ranker import run_ranking_pipeline

# --- Configuration & Job Description ---
JOB_TITLE = "Senior AI Engineer"
JOB_DESCRIPTION = """
We are looking for a Senior AI Engineer to design and build our next-generation candidate search and discovery system.
Key Responsibilities:
- Design and implement scalable vector search systems using Qdrant and FAISS.
- Fine-tune large language models (LLMs) using PyTorch and parameter-efficient techniques like LoRA.
- Build high-performance retrieval pipelines incorporating RAG (Retrieval-Augmented Generation) and hybrid search (dense + sparse BM25).
- Train and evaluate predictive models using XGBoost, PyTorch, and scikit-learn.
- Optimize search relevance, contextual ranking, and retrieval latency.
"""

def main():
    input_file = "candidates.jsonl"
    output_file = "ranked_candidates.csv"
    
    # 0. Check Input File Existence
    if not os.path.exists(input_file):
        print(f"Error: Required input file '{input_file}' not found.")
        print("Please run 'generate_mock_data.py' first to produce a sample dataset, or place your own candidates.jsonl in the current directory.")
        sys.exit(1)
        
    print(f"Reading candidates from '{input_file}'...")
    candidates = []
    
    # Handle parsing exceptions gracefully row-by-row
    with open(input_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                candidate = json.loads(line)
                if "candidate_id" not in candidate:
                    print(f"Warning: Line {line_num} missing 'candidate_id'. Skipping.")
                    continue
                candidates.append(candidate)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON on line {line_num}: {e}. Skipping.")
                continue
                
    total_candidates = len(candidates)
    print(f"Successfully loaded {total_candidates} candidates.")
    
    if total_candidates == 0:
        print("Error: No valid candidates to process.")
        sys.exit(1)
        
    print("\nExecuting Pipeline via Ranker Engine...")
    
    # Run the modularized pipeline with legacy heuristics enabled for exact matching
    ranked_results = run_ranking_pipeline(
        job_title=JOB_TITLE,
        job_description=JOB_DESCRIPTION,
        qualifications="",
        candidates=candidates,
        use_mock_heuristics=True
    )
    
    # Slice exactly the top 100 entries
    top_100_candidates = ranked_results[:100]
    print(f"\nExtracted the top {len(top_100_candidates)} candidates.")
    
    # Export to CSV with exact headers: candidate_id, rank, score, reasoning
    print(f"Writing ranked candidates to '{output_file}'...")
    try:
        with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            # Write exactly the specified header
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            
            for rank_idx, c in enumerate(top_100_candidates, 1):
                writer.writerow([
                    c["candidate_id"],
                    rank_idx,
                    f"{c['final_score']:.6f}",
                    c["reasoning"]
                ])
                
        print(f"Success! Exported {len(top_100_candidates)} rows successfully.")
    except Exception as e:
        print(f"Error writing to CSV: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
