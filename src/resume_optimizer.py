import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

RESUME_FORMAT_INSTRUCTIONS = """
Format the resume using Markdown with this exact structure:
- Use ## for the candidate's full name (only one ## heading)
- Use a single line right below the name for contact info (email, phone, location, links) separated by " | "
- Use ### for each section heading (e.g., ### Summary, ### Experience, ### Education, ### Skills, ### Certifications, ### Projects)
- For each job/role, put the title and company on one line using bold: **Job Title | Company Name** followed by the dates on the same line in italics: *Start – End*
- Use bullet points (- ) for responsibilities and achievements under each role
- For the Skills section, list skills as a comma-separated line or grouped by category
- Do NOT use ``` code blocks, do NOT use horizontal rules (---), and do NOT wrap output in any extra formatting
- Return ONLY the formatted resume, no explanation or commentary
"""

def optimize_resume(resume_text, missing_skills):
    prompt = f"""
You are a professional resume writer.
Given the resume below and a list of missing skills, rewrite the resume to naturally incorporate the missing skills where relevant.
Do NOT fabricate experience. Only add skills that can be reasonably implied or added to existing bullet points.

Missing Skills: {", ".join(missing_skills)}

Resume:
{resume_text}

{RESUME_FORMAT_INSTRUCTIONS}
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

{RESUME_FORMAT_INSTRUCTIONS}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()