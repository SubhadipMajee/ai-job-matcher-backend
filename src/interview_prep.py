"""
interview_prep.py — generates personalized interview questions, tips,
and model answers based on the candidate's resume and target job description.

Highlights questions addressing skill gaps between the candidate and the JD,
along with behavioral and technical questions likely to be asked.
"""

import time
import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_interview_prep(resume_text: str, job_description: str) -> dict:
    """
    Generate tailored interview preparation material.

    Parameters
    ----------
    resume_text     : Candidate's resume text
    job_description : Target job description

    Returns
    -------
    {
        "technical_questions": [
            {
                "question": "...",
                "context": "Why they ask this based on JD/Resume",
                "sample_answer": "...",
                "skills_tested": ["..."]
            }
        ],
        "gap_questions": [
            {
                "gap": "Missing skill or experience",
                "question": "How to answer when asked about this missing skill",
                "strategy": "How to pivot/demonstrate quick learning"
            }
        ],
        "behavioral_questions": [
            {
                "question": "...",
                "star_tip": "Situation/Task/Action/Result guidance"
            }
        ],
        "key_tips": ["...", "..."]
    }
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

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            return eval(raw)
        except Exception:
            return {
                "technical_questions": [],
                "gap_questions": [],
                "behavioral_questions": [],
                "key_tips": ["Failed to parse interview prep output."]
            }
