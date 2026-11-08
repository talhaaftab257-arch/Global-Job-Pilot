import re
from datetime import datetime, timezone

PROFILE_SKILLS = {
    "python", "fastapi", "rest api", "rest apis", "langchain", "langgraph",
    "openai", "anthropic", "claude", "gemini", "llm", "large language models",
    "rag", "retrieval augmented generation", "vector database", "embeddings",
    "multi-agent", "agentic", "ai agents", "machine learning", "deep learning",
    "tensorflow", "pytorch", "scikit-learn", "hugging face", "docker",
    "postgresql", "supabase", "sql", "react", "vite", "n8n", "automation"
}

ROLE_TERMS = (
    "ai engineer", "applied ai engineer", "agentic ai engineer", "ai agent developer",
    "ai agents engineer", "llm engineer", "generative ai engineer", "rag engineer",
    "machine learning engineer", "ml engineer", "ai automation engineer",
    "python ai engineer", "ai backend engineer", "full-stack ai engineer",
    "ai solutions engineer", "forward deployed ai engineer", "ai software engineer",
    "multi-agent systems engineer", "intelligent automation engineer",
    "data scientist", "mlops engineer", "nlp engineer", "computer vision engineer",
    "ai application developer", "conversational ai engineer"
)

AI_RELEVANCE_TERMS = (
    "artificial intelligence", "machine learning", "large language model", "llm",
    "generative ai", "deep learning", "neural network", "agentic", "nlp",
    "computer vision", "rag", "langgraph", "langchain", "vector search"
)

def score(job: dict) -> dict:
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    full_text = f"{title} {desc}"

    # 1. Technical skills match (up to 30)
    found_skills = sorted({
        s for s in PROFILE_SKILLS
        if re.search(r"(?<![\w])" + re.escape(s) + r"(?![\w])", full_text)
    })
    # Scale: 6+ skills = full 30 points
    technical_score = min(30, round(30 * (len(found_skills) / 6)))

    # 2. Job responsibility / title match (up to 20)
    if any(t in title for t in ROLE_TERMS):
        role_score = 20
    elif any(t in desc for t in ROLE_TERMS):
        role_score = 12
    else:
        role_score = 4

    # 3. AI / ML relevance (up to 15)
    matched_ai = [t for t in AI_RELEVANCE_TERMS if t in full_text]
    if len(matched_ai) >= 3:
        ai_relevance_score = 15
    elif len(matched_ai) >= 1:
        ai_relevance_score = 10
    else:
        ai_relevance_score = 3

    # 4. Experience and seniority compatibility (up to 10)
    # Candidate is Lead Data Scientist / Senior AI Engineer
    seniority_terms = ("lead", "senior", "staff", "principal", "mid", "experienced")
    if any(s in title for s in ("senior", "lead", "staff")):
        experience_score = 10
    elif any(s in full_text for s in seniority_terms):
        experience_score = 8
    else:
        experience_score = 7

    # 5. Visa sponsorship & relocation (up to 15)
    sponsorship_status = job.get("sponsorship_status", "unverified")
    has_relocation = bool(job.get("relocation_support"))
    if sponsorship_status == "confirmed":
        sponsorship_score = 15
    elif sponsorship_status == "likely":
        sponsorship_score = 10
    elif sponsorship_status == "unverified":
        sponsorship_score = 5 if has_relocation else 3
    else:  # unavailable
        sponsorship_score = 0

    # 6. Location & international eligibility (up to 5)
    country = job.get("country")
    is_remote = bool(re.search(r"\b(remote|anywhere|worldwide)\b", full_text))
    if country or (is_remote and "pakistan" in full_text):
        location_score = 5
    elif is_remote:
        location_score = 4
    else:
        location_score = 2

    # 7. Recency (up to 5)
    try:
        posted = job.get("posted_at")
        if posted:
            dt = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - dt).days
        else:
            age_days = 14
    except Exception:
        age_days = 14

    if age_days <= 1:
        recency_score = 5
    elif age_days <= 3:
        recency_score = 4
    elif age_days <= 7:
        recency_score = 3
    elif age_days <= 30:
        recency_score = 2
    else:
        recency_score = 1

    parts = {
        "technical_score": technical_score,
        "role_score": role_score,
        "ai_relevance_score": ai_relevance_score,
        "experience_score": experience_score,
        "sponsorship_score": sponsorship_score,
        "location_score": location_score,
        "recency_score": recency_score
    }

    total = min(100, sum(parts.values()))

    # Build human-readable match explanation
    top_skills = ", ".join(found_skills[:6]) if found_skills else "role relevance"
    status_text = {
        "confirmed": "Employer explicitly confirms visa sponsorship/relocation.",
        "likely": "Employer has proven sponsorship history.",
        "unverified": "Sponsorship information not explicitly stated in vacancy text.",
        "unavailable": "Vacancy requires existing domestic work authorization without sponsorship."
    }.get(sponsorship_status, "Sponsorship status unverified.")

    explanation = (
        f"Strong match for candidate profile. Aligned skills: {top_skills}. {status_text}"
    )

    return {
        "required_skills": found_skills,
        "match_score": total,
        **parts,
        "match_explanation": explanation
    }
