import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.profile_extractor import skill_variants

# A job that mentions this many of your skills counts as a full skill match.
FULL_SKILL_MATCH = 6

GENERIC_TECH_WORDS = [
    "developer", "engineer", "software", "programmer", "analyst", "data",
    "python", "java", "backend", "full stack", "machine learning", "ai",
]
SENIOR_WORDS = [
    "senior", "sr", "lead", "manager", "principal", "head", "director",
    "architect", "staff", "vp",
]
YEARS_PATTERN = re.compile(
    r"(\d{1,2})(?:\s*(?:-|–|to)\s*\d{1,2})?\s*\+?\s*(?:years?|yrs?|yoe)\b",
    re.IGNORECASE,
)


def word_in_text(word: str, text_lower: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])"
    return re.search(pattern, text_lower) is not None


def title_relevance(title: str, candidate_skills: list[str]) -> float:
    title_lower = title.lower()
    if any(
        word_in_text(v, title_lower)
        for skill in candidate_skills
        for v in skill_variants(skill)
    ):
        return 1.0
    if any(word_in_text(word, title_lower) for word in GENERIC_TECH_WORDS):
        return 0.6
    return 0.0


def is_senior(title: str) -> bool:
    title_lower = title.lower()
    return any(word_in_text(word, title_lower) for word in SENIOR_WORDS)


def required_years(text: str) -> int | None:
    years = [int(y) for y in YEARS_PATTERN.findall(text)]
    return min(years) if years else None


def experience_multiplier(required: int | None, experience: float) -> float:
    if required is None:
        return 1.0
    gap = required - experience
    if gap <= 1:
        return 1.0
    return max(0.3, 1 - 0.15 * gap)


def score_job(job: dict, candidate_skills: list[str], similarity: float, experience: float) -> dict:
    full_text = job["title"] + " " + job["description"]
    text_lower = full_text.lower()

    matched = [
        s for s in candidate_skills
        if any(word_in_text(v, text_lower) for v in skill_variants(s))
    ]
    denominator = min(len(candidate_skills), FULL_SKILL_MATCH)
    skill_score = min(1.0, len(matched) / denominator) if denominator else 0
    title_score = title_relevance(job["title"], candidate_skills)

    match_score = 0.4 * skill_score + 0.3 * title_score + 0.3 * similarity

    required = required_years(full_text)
    match_score *= experience_multiplier(required, experience)
    if experience < 5 and is_senior(job["title"]):
        match_score *= 0.5

    return {
        **job,
        "matched_skills": matched,
        "skill_score": round(skill_score, 2),
        "title_score": title_score,
        "similarity_score": round(similarity, 2),
        "required_years": required,
        "match_score": round(match_score, 2),
    }


def rank_jobs(
    jobs: list[dict], candidate_skills: list[str], resume_text: str, experience: float = 0
) -> list[dict]:
    if not jobs:
        return []

    texts = [resume_text] + [j["title"] + " " + j["description"] for j in jobs]
    vectors = TfidfVectorizer(stop_words="english").fit_transform(texts)
    similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

    top = similarities.max() or 1
    scored = [
        score_job(job, candidate_skills, sim / top, experience)
        for job, sim in zip(jobs, similarities)
    ]
    return sorted(scored, key=lambda j: j["match_score"], reverse=True)


def pick_top_jobs(ranked: list[dict], limit: int = 10) -> list[dict]:
    """Take the best jobs from every source, so one source cannot fill the list."""
    sources = {job["source"] for job in ranked}
    if not sources:
        return []

    per_source = max(1, limit // len(sources))
    counts: dict[str, int] = {}
    chosen = []
    for job in ranked:
        if counts.get(job["source"], 0) < per_source:
            chosen.append(job)
            counts[job["source"]] = counts.get(job["source"], 0) + 1

    for job in ranked:
        if len(chosen) >= limit:
            break
        if job not in chosen:
            chosen.append(job)

    return sorted(chosen, key=lambda j: j["match_score"], reverse=True)[:limit]
