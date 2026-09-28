"""
digest.py — reusable pipeline for the daily job digest.

get_matched_jobs() fetches jobs, extracts their required skills via Groq,
scores each one against a provided list of user skills, and returns only
jobs that meet the minimum score threshold.

Existing API endpoints (fetch-jobs, match, job-skills …) are NOT changed;
they still call job_scraper, skill_extractor, and matcher directly.
"""

import time
from src.job_scraper import fetch_jobs
from src.skill_extractor import extract_skills
from src.matcher import match_skills


def get_matched_jobs(
    skills: list[str],
    job_query: str,
    location: str = "",
    min_score: int = 0,
    num_results: int = 10,
) -> list[dict]:
    """
    Full fetch-and-score pipeline that works from a list of skills
    (not an uploaded PDF).

    Parameters
    ----------
    skills       : list of skill strings already extracted from the user's
                   resume, e.g. ["Python", "FastAPI", "SQL"]
    job_query    : search string sent to JSearch, e.g. "Python Developer"
    location     : optional city / country filter, e.g. "Bangalore"
    min_score    : only return jobs whose match score >= this value (0-100)
    num_results  : how many jobs to fetch from JSearch (default 10)

    Returns
    -------
    List of job dicts, each containing all original JSearch fields plus:
        job_id          – a stable unique identifier for deduplication
        score           – match percentage (0-100)
        matched_skills  – skills present in both resume and job description
        missing_skills  – skills required by the job but absent from resume
    Sorted descending by score.
    """
    # ── 1. Fetch raw job listings from JSearch ──────────────────────────
    raw_jobs = fetch_jobs(job_query, location=location, num_results=num_results)

    scored_jobs = []

    for job in raw_jobs:
        description = job.get("description") or ""

        # Skip listings with no description – can't extract skills from them
        if not description.strip():
            continue

        # ── 2. Extract skills from this job's description via Groq ───────
        # extract_skills() already adds a 1-second sleep internally to
        # respect Groq rate limits, so we don't need an extra sleep here.
        job_skills = extract_skills(description, "job description")

        # ── 3. Score the user's skills against the job's required skills ─
        # match_skills() returns { score, matched_skills, missing_skills }
        result = match_skills(skills, job_skills)

        # Skip jobs that don't meet the user's minimum score threshold
        if result["score"] < min_score:
            continue

        # ── 4. Build a stable job_id for deduplication ───────────────────
        # We concatenate title + company and lower-case it.  JSearch
        # doesn't expose a guaranteed unique ID in the free tier fields we
        # already capture, so this is a safe, deterministic fallback.
        title   = (job.get("title")   or "").strip()
        company = (job.get("company") or "").strip()
        job_id  = f"{title}|{company}".lower().replace(" ", "-")

        scored_jobs.append({
            **job,            # title, company, description, link, location, job_type
            "job_id":          job_id,
            "score":           result["score"],
            "matched_skills":  result["matched_skills"],
            "missing_skills":  result["missing_skills"],
        })

    # ── 5. Return best matches first ────────────────────────────────────
    scored_jobs.sort(key=lambda j: j["score"], reverse=True)
    return scored_jobs
