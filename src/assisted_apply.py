"""
assisted_apply.py — Generates a comprehensive "Apply Pack" for a specific job:
1. Tailored ATS-friendly resume
2. Personalized cover letter / application email
3. Direct application link
4. Pre-submission verification checklist

Keeps the human in the loop: empowers the user to apply with higher quality
without violating terms of service or risking automated rejection.
"""

from src.resume_optimizer import tailor_resume
from src.email_generator import generate_email


def generate_apply_pack(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
    link: str = "",
) -> dict:
    """
    Generate tailored resume, email, checklist, and apply link.
    """
    tailored = tailor_resume(resume_text, job_description)
    email = generate_email(resume_text, job_title, company)

    checklist = [
        "Review tailored bullet points to ensure all claims accurately represent your experience.",
        f"Double-check that contact details (email, phone, LinkedIn/GitHub) are up-to-date for {company}.",
        f"Customize the opening and closing lines of the application email for {job_title}.",
        "Attach portfolio, GitHub, or live deployment links relevant to the job requirements.",
        "Check visa/sponsorship and remote/hybrid work requirements if applicable."
    ]

    return {
        "job_title": job_title,
        "company": company,
        "apply_link": link,
        "tailored_resume": tailored,
        "cover_email": email,
        "checklist": checklist,
    }
