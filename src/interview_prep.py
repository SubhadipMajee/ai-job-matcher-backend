"""
interview_prep.py — generates personalized interview questions, tips,
and model answers based on the candidate's resume and target job description.
"""

import time
from src.ai_client import get_completion, parse_json_safely


def generate_interview_prep(resume_text: str, job_description: str) -> dict:
    """
    Generate tailored interview preparation material.
    """
    time.sleep(1)

    prompt = f"""You are an elite tech interview coach.
Analyze this resume against the target job description and generate interview preparation guidance.

Resume:
{resume_text}

Job Description:
{job_description}

Return ONLY a valid JSON object with exactly this schema (no markdown, no backticks, no extra text):
{{
    "technical_questions": [
        {{
            "question": "Specific technical question",
            "context": "Why this is critical for the role",
            "sample_answer": "Concise high-scoring answer outline",
            "skills_tested": ["Skill1", "Skill2"]
        }}
    ],
    "gap_questions": [
        {{
            "gap": "Area where candidate resume seems light or missing",
            "question": "How interviewer might probe this gap",
            "strategy": "Constructive response strategy highlighting transferable experience"
        }}
    ],
    "behavioral_questions": [
        {{
            "question": "Behavioral question relevant to the role/culture",
            "star_tip": "Specific STAR method tip tailored to candidate background"
        }}
    ],
    "key_tips": [
        "Actionable tip 1",
        "Actionable tip 2",
        "Actionable tip 3"
    ]
}}
"""

    raw = get_completion([{"role": "user", "content": prompt}])
    return parse_json_safely(raw, default={
        "technical_questions": [],
        "gap_questions": [],
        "behavioral_questions": [],
        "key_tips": ["Review core requirements and prepare concrete project anecdotes."]
    })
