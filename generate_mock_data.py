import json
import random

# Seed for reproducibility
random.seed(42)

tech_titles = [
    "Senior AI Engineer", "Staff Machine Learning Engineer", "Principal AI Architect",
    "Lead NLP Engineer", "Senior Software Engineer (AI/ML)", "AI Research Scientist",
    "Data Scientist", "Machine Learning Specialist"
]
non_tech_titles = [
    "Marketing Specialist", "Sales Manager", "HR Generalist", "Recruiting Coordinator",
    "Product Manager", "Financial Analyst", "Operations Director", "Account Executive",
    "Content Writer", "Graphic Designer"
]

consulting_giants = ["TCS", "Infosys", "Wipro", "Accenture", "Cognizant", "Capgemini", "HCL Technologies"]
product_companies = ["Stripe", "Google", "Meta", "Netflix", "OpenAI", "Anthropic", "Scale AI"]
startups = ["Pinecone", "Qdrant", "LangChain", "Anyscale", "RunPod", "Together AI"]
other_companies = ["Walmart", "Bank of America", "Ford", "Chevron", "Target"]

skills_pool = [
    "Python", "PyTorch", "TensorFlow", "Qdrant", "FAISS", "LoRA", "XGBoost", "LLMs",
    "RAG", "Transformers", "Kubernetes", "Docker", "AWS", "Git", "LangChain", "Vector Databases",
    "SQL", "scikit-learn", "FastAPI", "Prompt Engineering", "Fine-Tuning"
]

def generate_candidate(cid):
    is_technical = random.random() < 0.65
    
    if is_technical:
        current_title = random.choice(tech_titles)
        skills = random.sample(skills_pool, k=random.randint(5, 12))
    else:
        current_title = random.choice(non_tech_titles)
        skills = random.sample(skills_pool, k=random.randint(1, 4))
        if random.random() < 0.3:
            skills.extend(["Qdrant", "FAISS", "LoRA"]) # keyword trap
            
    num_jobs = random.randint(1, 4)
    experience = []
    
    history_type = random.choice(["exclusively_consulting", "mixed", "exclusively_product_startup", "other"])
    
    for i in range(num_jobs):
        if history_type == "exclusively_consulting":
            company_name = random.choice(consulting_giants)
            company_type = "consulting"
        elif history_type == "exclusively_product_startup":
            company_name = random.choice(product_companies + startups)
            company_type = "product" if company_name in product_companies else "startup"
        elif history_type == "mixed":
            company_name = random.choice(consulting_giants + product_companies + startups + other_companies)
            if company_name in consulting_giants:
                company_type = "consulting"
            elif company_name in product_companies:
                company_type = "product"
            elif company_name in startups:
                company_type = "startup"
            else:
                company_type = "other"
        else:
            company_name = random.choice(other_companies)
            company_type = "other"
            
        role_title = random.choice(tech_titles if is_technical else non_tech_titles)
        desc = f"Responsible for tasks at {company_name} as {role_title}. "
        if is_technical:
            desc += "Worked on implementing neural networks, LLM finetuning using LoRA, vector databases like Qdrant and FAISS, and training models with PyTorch."
        else:
            desc += "Worked on project management, marketing strategies, client communication, and general business tasks."
            
        experience.append({
            "title": role_title,
            "company_name": company_name,
            "company_type": company_type,
            "description": desc
        })
        
    months_since_last_login = round(random.uniform(0.1, 15.0), 1)
    recruiter_response_rate = round(random.uniform(0.05, 1.0), 2)
    
    return {
        "candidate_id": f"CAND_{cid:07d}",
        "current_title": current_title,
        "experience": experience,
        "months_since_last_login": months_since_last_login,
        "recruiter_response_rate": recruiter_response_rate,
        "skills": skills
    }

def main():
    candidates = []
    
    # Hand-craft specific archetypes to ensure deterministic testing of filters:
    # 1. Perfect Match (AI Star)
    candidates.append({
        "candidate_id": "CAND_0000001",
        "current_title": "Senior AI Engineer",
        "experience": [
            {"title": "AI Engineer", "company_name": "Qdrant", "company_type": "startup", "description": "Developed vector search indices and optimized FAISS/Qdrant retrievers. Fine-tuned models using LoRA and PyTorch."},
            {"title": "Software Engineer", "company_name": "Google", "company_type": "product", "description": "Worked on NLP systems and training deep learning models."}
        ],
        "months_since_last_login": 0.5,
        "recruiter_response_rate": 0.95,
        "skills": ["Python", "PyTorch", "Qdrant", "FAISS", "LoRA", "XGBoost", "RAG", "LLMs"]
    })
    
    # 2. Title Trap (Marketing manager mentioning keyword trap)
    candidates.append({
        "candidate_id": "CAND_0000002",
        "current_title": "Marketing Manager",
        "experience": [
            {"title": "Social Media Lead", "company_name": "Target", "company_type": "other", "description": "Led campaigns. Interested in AI, machine learning, LoRA, FAISS, Qdrant."}
        ],
        "months_since_last_login": 1.0,
        "recruiter_response_rate": 0.8,
        "skills": ["Marketing", "Qdrant", "FAISS", "LoRA"]
    })
    
    # 3. IT Consulting Exclusively
    candidates.append({
        "candidate_id": "CAND_0000003",
        "current_title": "Senior AI Engineer",
        "experience": [
            {"title": "AI Developer", "company_name": "TCS", "company_type": "consulting", "description": "Consulted on client projects using PyTorch, LoRA, and XGBoost."},
            {"title": "Systems Engineer", "company_name": "Infosys", "company_type": "consulting", "description": "Maintained database servers."}
        ],
        "months_since_last_login": 2.0,
        "recruiter_response_rate": 0.85,
        "skills": ["Python", "PyTorch", "LoRA", "XGBoost"]
    })

    # 4. Inactive AI Engineer
    candidates.append({
        "candidate_id": "CAND_0000004",
        "current_title": "Senior AI Engineer",
        "experience": [
            {"title": "Lead ML Engineer", "company_name": "Scale AI", "company_type": "product", "description": "Led fine-tuning projects with PyTorch and LoRA."}
        ],
        "months_since_last_login": 14.5,
        "recruiter_response_rate": 0.15,
        "skills": ["Python", "PyTorch", "LoRA", "FAISS", "Qdrant"]
    })
    
    for i in range(5, 650):
        candidates.append(generate_candidate(i))
        
    with open("candidates.jsonl", "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c) + "\n")
            
    print(f"Successfully generated {len(candidates)} candidates and wrote to candidates.jsonl")

if __name__ == "__main__":
    main()
