import os
import json
from flask import Flask, request, jsonify, send_from_directory
import pypdf
from ranker import run_ranking_pipeline

app = Flask(__name__, static_folder='static', static_url_path='/static')

DEFAULT_JD = """We are looking for a Senior AI Engineer to design and build our next-generation candidate search and discovery system.
Key Responsibilities:
- Design and implement scalable vector search systems using Qdrant and FAISS.
- Fine-tune large language models (LLMs) using PyTorch and parameter-efficient techniques like LoRA.
- Build high-performance retrieval pipelines incorporating RAG (Retrieval-Augmented Generation) and hybrid search (dense + sparse BM25).
- Train and evaluate predictive models using XGBoost, PyTorch, and scikit-learn.
- Optimize search relevance, contextual ranking, and retrieval latency.
"""

DEFAULT_TITLE = "Senior AI Engineer"

@app.route('/')
def index():
    # Serve index.html from static folder
    return send_from_directory('static', 'index.html')

@app.route('/api/defaults', methods=['GET'])
def get_defaults():
    """Loads and returns default job title, description, and the candidate list size."""
    candidates_count = 0
    if os.path.exists("candidates.jsonl"):
        try:
            with open("candidates.jsonl", "r", encoding="utf-8") as f:
                candidates_count = sum(1 for line in f if line.strip())
        except Exception:
            pass
            
    return jsonify({
        "job_title": DEFAULT_TITLE,
        "job_description": DEFAULT_JD,
        "qualifications": "B.S. or M.S. in Computer Science or related field. Experience with PyTorch, Transformers, Qdrant/FAISS, LoRA, and RAG architectures.",
        "default_candidates_count": candidates_count
    })

@app.route('/api/rank', methods=['POST'])
def rank_candidates_api():
    """
    Accepts job parameters and candidate resumes (files or default DB),
    parses resumes, runs the AI ranker, and returns ranked results.
    """
    job_title = request.form.get("job_title", "").strip()
    job_description = request.form.get("job_description", "").strip()
    qualifications = request.form.get("qualifications", "").strip()
    use_defaults = request.form.get("use_defaults", "false").lower() == "true"
    
    candidates = []
    
    # 1. Handle Candidate Source
    if use_defaults:
        # Load from default candidates.jsonl file
        if not os.path.exists("candidates.jsonl"):
            return jsonify({"success": False, "error": "Default candidates file 'candidates.jsonl' not found in workspace."}), 400
            
        with open("candidates.jsonl", "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    candidates.append(json.loads(line))
                except Exception as e:
                    print(f"Warning: failed to parse JSON on line {line_num}: {e}")
                    
    elif 'candidates_file' in request.files:
        # Parse uploaded JSON/JSONL profile database
        file = request.files['candidates_file']
        if file.filename:
            content = file.read().decode('utf-8')
            # Check if JSON or JSONL
            if file.filename.endswith('.jsonl'):
                for line in content.split('\n'):
                    if line.strip():
                        try:
                            candidates.append(json.loads(line))
                        except Exception:
                            pass
            else:
                try:
                    candidates = json.loads(content)
                    if not isinstance(candidates, list):
                        candidates = [candidates]
                except Exception as e:
                    return jsonify({"success": False, "error": f"Failed to parse uploaded JSON file: {e}"}), 400
                    
    elif 'resumes' in request.files or len(request.files.getlist('resumes')) > 0:
        # Parse uploaded raw resume files (PDF/TXT)
        files = request.files.getlist('resumes')
        for file in files:
            if not file.filename:
                continue
                
            filename = file.filename
            ext = filename.rsplit('.', 1)[-1].lower()
            text = ""
            
            try:
                if ext == 'pdf':
                    # Parse PDF pages
                    pdf_reader = pypdf.PdfReader(file)
                    pages_text = []
                    for p in pdf_reader.pages:
                        extracted = p.extract_text()
                        if extracted:
                            pages_text.append(extracted)
                    text = "\n".join(pages_text)
                elif ext == 'txt':
                    # Parse text file
                    text = file.read().decode('utf-8', errors='ignore')
                else:
                    print(f"Skipping unsupported file type: {filename}")
                    continue
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                continue
                
            if not text.strip():
                print(f"Warning: No text extracted from resume: {filename}")
                
            # Attempt to extract a potential candidate name or current title
            # We can use the filename as the default candidate ID & current title
            clean_title = filename.rsplit('.', 1)[0]
            
            candidates.append({
                "candidate_id": filename,
                "current_title": clean_title,
                "raw_resume_text": text,
                "experience": [],
                "skills": []
            })
            
    if not candidates:
        return jsonify({"success": False, "error": "No candidates provided. Please load default candidates, upload a candidates profile file, or upload raw resumes."}), 400
        
    try:
        # Execute the unified ranking pipeline
        # Since this is run dynamically from the web app, set use_mock_heuristics=False
        ranked_results = run_ranking_pipeline(
            job_title=job_title,
            job_description=job_description,
            qualifications=qualifications,
            candidates=candidates,
            use_mock_heuristics=False
        )
        
        # Clean results for response JSON representation (removing numpy/tensor types)
        serializable_results = []
        for c in ranked_results:
            serializable_results.append({
                "candidate_id": c.get("candidate_id", ""),
                "current_title": c.get("current_title", ""),
                "final_score": c.get("final_score", 0.0),
                "s_semantic_prob": c.get("s_semantic_prob", 0.0),
                "title_mult": c.get("title_mult", 1.0),
                "company_mult": c.get("company_mult", 1.0),
                "activity_mult": c.get("activity_mult", 1.0),
                "reasoning": c.get("reasoning", ""),
                "skills": c.get("skills", []),
                "experience": c.get("experience", []),
                "narrative": c.get("narrative", "")
            })
            
        return jsonify({
            "success": True,
            "results": serializable_results
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"An error occurred in the ranking engine: {e}"}), 500

if __name__ == '__main__':
    # Start the server on localhost:8000
    app.run(host='0.0.0.0', port=8000, debug=True)
