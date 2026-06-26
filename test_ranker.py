import re
from ranker import get_dynamic_title_penalty, run_ranking_pipeline

class MockDenseModel:
    def encode(self, texts, **kwargs):
        import numpy as np
        # Return a simple mock embedding array
        # BGE Large embedding dim is 1024
        # If it's a list/batch, return a matrix, otherwise a vector
        is_list = isinstance(texts, list)
        num_texts = len(texts) if is_list else 1
        emb = np.random.randn(num_texts, 1024)
        # Normalize to unit length for cosine similarity
        emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
        if is_list:
            import torch
            return torch.tensor(emb)
        else:
            import torch
            return torch.tensor(emb[0])

class MockCrossEncoder:
    def __init__(self, model_name, device):
        pass
    def predict(self, pairs, **kwargs):
        import numpy as np
        return np.random.rand(len(pairs))

# Monkeypatch CrossEncoder and SentenceTransformer in ranker module
# Monkeypatch CrossEncoder and SentenceTransformer in ranker package submodules
import ranker.pipeline
import ranker.title_penalty
ranker.pipeline.SentenceTransformer = lambda name, device: MockDenseModel()
ranker.pipeline.CrossEncoder = MockCrossEncoder
ranker.title_penalty.SentenceTransformer = lambda name, device: MockDenseModel()

# Test 1: Test get_dynamic_title_penalty with keyword overlap
penalty, reason = get_dynamic_title_penalty("Senior Software Engineer", "Software Engineer")
print("Test 1 (Keyword overlap) penalty:", penalty, "| Reason:", reason)
assert penalty == 1.0
assert "keyword overlap" in reason

# Test 2: Test get_dynamic_title_penalty with no overlap but semantic check (direct)
mock_model = MockDenseModel()
# Directly test with precomputed similarity
penalty, reason = get_dynamic_title_penalty("DevOps Expert", "Software Engineer", precomputed_sim=0.7)
print("Test 2 (Precomputed Sim >= 0.5) penalty:", penalty, "| Reason:", reason)
assert penalty == 1.0

penalty, reason = get_dynamic_title_penalty("DevOps Expert", "Software Engineer", precomputed_sim=0.3)
print("Test 3 (Precomputed Sim < 0.5) penalty:", penalty, "| Reason:", reason)
assert penalty < 1.0

# Test 4: Run ranking pipeline with mock models
candidates = [
    {
        "candidate_id": "CAND_001",
        "current_title": "Software Engineer",
        "experience": [{"title": "Software Engineer", "company_name": "Google", "company_type": "product", "description": "Writing Python"}],
        "skills": ["Python", "PyTorch"],
        "months_since_last_login": 1.0,
        "recruiter_response_rate": 0.9
    },
    {
        "candidate_id": "CAND_002",
        "current_title": "Marketing Manager",
        "experience": [{"title": "Marketing Manager", "company_name": "AdsCorp", "company_type": "other", "description": "Ads"}],
        "skills": ["Marketing"],
        "months_since_last_login": 1.0,
        "recruiter_response_rate": 0.9
    },
    {
        "candidate_id": "Resume_John_AI.pdf",
        "current_title": "Resume_John_AI",
        "raw_resume_text": "John Doe - AI Engineer. Skills: Python, PyTorch, FAISS. Work: NLP Engineer at Stripe.",
        "experience": [],
        "skills": []
    }
]

print("\nRunning mock ranking pipeline...")
results = run_ranking_pipeline(
    job_title="Software Engineer",
    job_description="Python developer with PyTorch skills",
    qualifications="Degree in CS",
    candidates=candidates,
    use_mock_heuristics=False
)

print("\nPipeline execution successful! Results:")
for r in results:
    print(r["candidate_id"], "- Title:", r.get("current_title"), "- Final Score:", r["final_score"], "- Reasoning:", r["reasoning"])

print("\nAll tests passed successfully!")
