import time
from src.ai_client import get_completion, parse_json_safely


def extract_skills(text, source="resume"):
    time.sleep(1)
    prompt = f"""
Extract a list of technical skills from the following {source} text.
Return ONLY a valid JSON array of strings, nothing else.
Example: ["Python", "React", "SQL"]

Text:
{text}
"""
    raw = get_completion([{"role": "user", "content": prompt}])
    result = parse_json_safely(raw, default=[])
    return result if isinstance(result, list) else []


def ats_score(resume_text, job_description):
    time.sleep(1)
    prompt = f"""
You are an ATS (Applicant Tracking System) evaluator.
Analyze the resume against the job description and return a JSON object with exactly these fields:
{{
    "ats_score": 75,
    "keyword_match": 80,
    "format_score": 70,
    "experience_match": 75,
    "strengths": ["strength1", "strength2", "strength3"],
    "improvements": ["improvement1", "improvement2", "improvement3"]
}}
Return ONLY the JSON, no explanation, no markdown.

Job Description:
{job_description}

Resume:
{resume_text}
"""
    raw = get_completion([{"role": "user", "content": prompt}])
    return parse_json_safely(raw, default={
        "ats_score": 50,
        "keyword_match": 50,
        "format_score": 50,
        "experience_match": 50,
        "strengths": ["Clear structure"],
        "improvements": ["Align keywords with job description"]
    })


def skill_roadmap(missing_skills):
    time.sleep(1)
    prompt = f"""
For each of the following missing skills, provide a learning roadmap.
Return ONLY a JSON array with this exact structure, no explanation, no markdown:
[
  {{
    "skill": "skill name",
    "level": "Beginner/Intermediate/Advanced",
    "time": "estimated time to learn",
    "resources": [
      {{"name": "resource name", "url": "https://...", "type": "Free/Paid"}}
    ]
  }}
]

Missing Skills: {", ".join(missing_skills)}
"""
    raw = get_completion([{"role": "user", "content": prompt}])
    result = parse_json_safely(raw, default=[])
    return result if isinstance(result, list) else []