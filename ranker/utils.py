import re
import math

# Custom list of standard English stopwords for dynamic keyword extraction
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "can't", "cannot",
    "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few",
    "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll",
    "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most",
    "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
    "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    "looking", "design", "build", "next", "generation", "key", "responsibilities", "requirements", "experience",
    "candidate", "candidates", "role", "position", "job", "work", "skills", "technologies", "preferred", "requirements",
    "duties", "qualifications", "required", "responsible", "tasks", "duties", "successful", "highly", "ability"
}

def tokenize(text):
    """Tokenizes input text into clean lowercase alphanumeric words."""
    if not text:
        return []
    return re.findall(r'\b\w+\b', text.lower())

def extract_keywords(text, num_keywords=15):
    """
    Tokenizes text, filters out standard stopwords, and extracts the top unique key words.
    Used for creating a dynamic query for BM25 retrieval.
    """
    if not text:
        return []
    words = tokenize(text)
    # Filter stopwords and short numbers/characters
    filtered_words = [w for w in words if w not in STOPWORDS and len(w) > 2 and not w.isdigit()]
    
    # Calculate frequencies
    freq = {}
    for w in filtered_words:
        freq[w] = freq.get(w, 0) + 1
        
    # Sort by frequency
    sorted_words = sorted(freq.keys(), key=lambda x: -freq[x])
    return sorted_words[:num_keywords]

def synthesize_profile(c):
    """
    Creates a structured text narrative combining candidate's title, experience history,
    and skills to maximize semantic model context.
    """
    # Check if this candidate is a raw resume (plain text)
    if "raw_resume_text" in c:
        return c["raw_resume_text"][:10000]
        
    parts = []
    
    # Current Title
    current_title = c.get("current_title", "Unknown Title")
    parts.append(f"Current Title: {current_title}")
    
    # Work Experience History
    exp_list = c.get("experience", [])
    if exp_list:
        exp_parts = []
        for exp in exp_list:
            title = exp.get("title", "Unknown Role")
            company = exp.get("company_name", "Unknown Company")
            comp_type = exp.get("company_type", "")
            desc = exp.get("description", "")
            
            job_str = f"{title} at {company}"
            if comp_type:
                job_str += f" ({comp_type} company)"
            if desc:
                # Truncate description slightly if extremely long to maintain input sequence constraints
                job_str += f": {desc[:200]}"
            exp_parts.append(job_str)
        parts.append("Work History: " + "; ".join(exp_parts))
    
    # Skills
    skills = c.get("skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    elif isinstance(skills, dict):
        skills = list(skills.keys())
        
    if skills:
        skill_strings = []
        for s in skills:
            if isinstance(s, dict):
                skill_val = s.get('name') or s.get('skill_name') or s.get('skill')
                if not skill_val:
                    candidate_keys = [k for k in s.keys() if k.lower() not in ['level', 'years', 'experience', 'proficiency']]
                    skill_val = candidate_keys[0] if candidate_keys else (list(s.keys())[0] if s else '')
                if skill_val:
                    skill_strings.append(str(skill_val))
            elif isinstance(s, list):
                skill_strings.extend([str(item) for item in s if item])
            elif s is not None:
                skill_strings.append(str(s))
        
        c["skills"] = skill_strings
        if skill_strings:
            parts.append("Skills & Technologies: " + ", ".join(skill_strings))
        
    return ". ".join(parts)

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def log_progress(callback, message):
    if callback:
        callback(message)
    else:
        print(message)
