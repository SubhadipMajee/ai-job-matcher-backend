"""
semantic_matcher.py — embedding-based skill matching using Groq.
"""

import time
from src.ai_client import get_completion, parse_json_safely


def match_skills_semantic(
    resume_skills: list[str],
    job_description: str,
    threshold: int = 50,
) -> dict:
    """
    Score resume skills against a job description using semantic understanding.
    """
    time.sleep(1)

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
        {{"skill": "skill name from resume", "relevance": 90, "matched_to": "which job requirement it matches"}}
    ],
    "missing_skills": ["skill required by job but not in resume at all"],
    "overall_score": 80
}}

Rules:
- relevance 80-100: strong direct match (e.g. "Python" <-> "Python")
- relevance 50-79: related/transferable (e.g. "React" <-> "frontend development")
- relevance 0-49: weak or no connection
- missing_skills: only list truly missing skills, not ones partially covered
- overall_score: weighted average considering coverage of job requirements"""

    raw = get_completion([{"role": "user", "content": prompt}])
    data = parse_json_safely(raw, default={
        "skill_scores": [],
        "missing_skills": [],
        "overall_score": 50,
    })

    matched = []
    partial = []

    for item in data.get("skill_scores", []):
        entry = {
            "skill": item.get("skill", ""),
            "relevance": item.get("relevance", 0),
            "matched_to": item.get("matched_to", ""),
        }
        if entry["relevance"] >= threshold:
            matched.append(entry)
        else:
            partial.append(entry)

    return {
        "score": data.get("overall_score", 0),
        "matched_skills": matched,
        "missing_skills": data.get("missing_skills", []),
        "partial_matches": partial,
    }
