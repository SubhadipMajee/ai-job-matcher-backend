from src.ai_client import get_completion


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
    return get_completion([{"role": "user", "content": prompt}]).strip()