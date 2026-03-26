import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_email(resume_text, job_title, company_name):
    prompt = f"""
Write a professional job application email for the following:

Job Title: {job_title}
Company: {company_name}

Based on this resume:
{resume_text}

Write a concise, professional email with subject line, opening, why they are a good fit, and closing.
Return the email only, no explanation.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()