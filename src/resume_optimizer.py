import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def optimize_resume(resume_text, missing_skills):
    prompt = f"""
You are a professional resume writer.
Given the resume below and a list of missing skills, rewrite the resume to naturally incorporate the missing skills where relevant.
Do NOT fabricate experience. Only add skills that can be reasonably implied or added to existing bullet points.

Missing Skills: {", ".join(missing_skills)}

Resume:
{resume_text}

Return the improved resume text only, no explanation.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()



    def tailor_resume(resume_text, job_description):
    prompt = f"""
You are an expert resume writer and career coach.
Your task is to tailor the resume below specifically for the job description provided.

Instructions:
- Rewrite bullet points to mirror the language and keywords in the job description
- Prioritize and highlight experiences most relevant to this role
- Add missing keywords naturally without fabricating experience
- Match the tone and terminology used in the job description
- Keep all real experience intact, just reframe and reorder for relevance
- Make it ATS-friendly by including exact phrases from the job description

Job Description:
{job_description}

Resume:
{resume_text}

Return the fully tailored resume text only. No explanation, no commentary.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()