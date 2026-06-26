def get_legacy_title_penalty(title):
    if not title:
        return 0.2, "Missing current title (0.2x)"
    title_lower = title.lower()
    tech_keywords = [
        "engineer", "developer", "scientist", "programmer", "tech", "architect", 
        "data", "ai", "ml", "nlp", "software", "analyst", "cto", "computer", "system"
    ]
    non_tech_keywords = [
        "marketing", "sales", "hr", "human resources", "recruiter", "recruiting", 
        "accountant", "finance", "legal", "writer", "designer", "graphic", "content", 
        "operations", "business"
    ]
    has_tech_kw = any(kw in title_lower for kw in tech_keywords)
    is_non_tech = any(kw in title_lower for kw in non_tech_keywords)
    if "manager" in title_lower and not has_tech_kw:
        is_non_tech = True
    if is_non_tech or not has_tech_kw:
        return 0.2, f"Title Trap Penalty applied (Current Title: '{title}' is non-technical, 0.2x)"
    return 1.0, "Technical title matched (1.0x)"

def get_legacy_company_modifier(experience):
    if not experience:
        return 1.0, "No experience history (1.0x)"
    consulting_giants = ["tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini", "hcl"]
    has_startup_or_product = False
    all_are_consulting = True
    for job in experience:
        company_name = job.get("company_name", "").lower()
        company_type = job.get("company_type", "").lower()
        if company_type in ["startup", "product"] or any(kw in company_name for kw in ["openai", "anthropic", "google", "meta", "netflix", "stripe", "anyscale", "runpod"]):
            has_startup_or_product = True
        is_consulting = any(cg in company_name for cg in consulting_giants) or company_type == "consulting"
        if not is_consulting:
            all_are_consulting = False
    if all_are_consulting:
        return 0.1, "IT Consulting Penalty applied (worked exclusively at legacy IT consulting firms, 0.1x)"
    elif has_startup_or_product:
        return 1.2, "Product/Startup Bonus applied (experience at a startup or product company, 1.2x)"
    return 1.0, "Standard company archetype (1.0x)"

def get_legacy_activity_modifier(candidate):
    months = candidate.get("months_since_last_login", 0.0)
    rate = candidate.get("recruiter_response_rate", 1.0)
    months_mult = 1.0
    rate_mult = 1.0
    reasons = []
    if months > 6:
        months_mult = max(0.2, round(1.0 - 0.1 * (months - 6), 3))
        reasons.append(f"Stale Activity Penalty ({months} months since last login, {months_mult}x)")
    if rate < 0.3:
        rate_mult = max(0.1, round(rate / 0.3, 3))
        reasons.append(f"Low Response Rate Penalty (response rate: {rate * 100:.1f}%, {rate_mult}x)")
    activity_mult = round(months_mult * rate_mult, 4)
    reason_str = "; ".join(reasons) if reasons else "Active and responsive profile (1.0x)"
    return activity_mult, reason_str
