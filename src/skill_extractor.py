import time
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_skills(text, source="resume"):
    time.sleep(1)
    prompt = f"""
Extract a list of technical skills from the following {source} text.
Return ONLY a Python list of strings, nothing else.
Example: ["Python", "React", "SQL"]

Text:
{text}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    try:
        return eval(raw)
    except:
        return []

def ats_score(resume_text, job_description):
    time.sleep(1)
    prompt = f"""
You are an ATS (Applicant Tracking System) evaluator.
Analyze the resume against the job description and return a JSON object with exactly these fields:
{{
    "ats_score": <number 0-100>,
    "keyword_match": <number 0-100>,
    "format_score": <number 0-100>,
    "experience_match": <number 0-100>,
    "strengths": ["strength1", "strength2", "strength3"],
    "improvements": ["improvement1", "improvement2", "improvement3"]
}}
Return ONLY the JSON, no explanation, no markdown.

Job Description:
{job_description}

Resume:
{resume_text}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    try:
        return eval(raw)
    except:
        return None

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
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    try:
        return eval(raw)
    except:
        return []