"""
semantic_matcher.py — embedding-based skill matching using Groq.

Why this is better than the existing set-intersection approach:
  - "React" matches "frontend frameworks"
  - "Postgres" matches "relational databases"
  - "AWS Lambda" matches "serverless computing"

How it works:
  1. We ask the LLM to score each user skill against the job description
     on a 0-100 semantic relevance scale.
  2. Skills scoring >= the threshold count as "matched".
  3. We also extract truly missing skills that have no semantic overlap.

This uses Groq's fast LLM inference rather than a local embedding model,
keeping dependencies minimal and deployment simple (no PyTorch on Render).

The existing match_skills() in matcher.py is left untouched — both
approaches are available and the frontend can choose which to call.
"""

import time
import os
import json as _json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def match_skills_semantic(
    resume_skills: list[str],
    job_description: str,
    threshold: int = 50,
) -> dict:
    """
    Score resume skills against a job description using semantic understanding.

    Parameters
    ----------
    resume_skills   : skills extracted from the user's resume
    job_description : full text of the job posting
    threshold       : minimum relevance score (0-100) to count as a match

    Returns
    -------
    {
        "score":            int,        # overall match percentage 0-100
        "matched_skills":   [ { "skill": str, "relevance": int, "matched_to": str } ],
        "missing_skills":   [ str ],    # key requirements not covered by resume
        "partial_matches":  [ { "skill": str, "relevance": int, "matched_to": str } ],
    }
    """
    time.sleep(1)   # respect Groq rate limits

    skills_str = ", ".join(resume_skills)

    prompt = f"""You are a technical recruiter doing a deep skill-match analysis.

Given these RESUME SKILLS: [{skills_str}]

And this JOB DESCRIPTION:
{job_description}

Analyze how well each resume skill matches the job requirements.
Consider synonyms, related technologies, and transferable skills.
For example: "React" is relevant to a job asking for "frontend frameworks".

Return ONLY a JSON object with exactly this structure, no explanation:
{{
    "skill_scores": [
        {{"skill": "skill name from resume", "relevance": 0-100, "matched_to": "which job requirement it matches"}}
    ],
    "missing_skills": ["skill required by job but not in resume at all"],
    "overall_score": 0-100
}}

Rules:
- relevance 80-100: strong direct match (e.g. "Python" ↔ "Python")
- relevance 50-79: related/transferable (e.g. "React" ↔ "frontend development")
- relevance 0-49: weak or no connection
- missing_skills: only list truly missing skills, not ones partially covered
- overall_score: weighted average considering coverage of job requirements"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError:
        # Fallback: try eval if JSON parsing fails (Groq sometimes adds comments)
        try:
            data = eval(raw)
        except Exception:
            return {
                "score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "partial_matches": [],
            }

    # Separate matched from partial based on threshold
    matched  = []
    partial  = []

    for item in data.get("skill_scores", []):
        entry = {
            "skill":      item.get("skill", ""),
            "relevance":  item.get("relevance", 0),
            "matched_to": item.get("matched_to", ""),
        }
        if entry["relevance"] >= threshold:
            matched.append(entry)
        else:
            partial.append(entry)

    return {
        "score":           data.get("overall_score", 0),
        "matched_skills":  matched,
        "missing_skills":  data.get("missing_skills", []),
        "partial_matches": partial,
    }
