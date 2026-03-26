from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil, os, json

from src.resume_parser import extract_text_from_pdf
from src.job_scraper import fetch_jobs
from src.skill_extractor import extract_skills, ats_score
from src.matcher import match_skills
from src.resume_optimizer import optimize_resume
from src.email_generator import generate_email

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    with open("temp_resume.pdf", "wb") as f:
        shutil.copyfileobj(file.file, f)
    text = extract_text_from_pdf("temp_resume.pdf")
    skills = extract_skills(text, "resume")
    return {"resume_text": text, "resume_skills": skills}

@app.post("/fetch-jobs")
async def get_jobs(job_role: str = Form(...)):
    jobs = fetch_jobs(job_role)
    return {"jobs": jobs}

@app.post("/match")
async def get_match(resume_skills: str = Form(...), job_skills: str = Form(...)):
    result = match_skills(json.loads(resume_skills), json.loads(job_skills))
    return result

@app.post("/job-skills")
async def get_job_skills(job_description: str = Form(...)):
    skills = extract_skills(job_description, "job description")
    return {"job_skills": skills}

@app.post("/optimize-resume")
async def improve_resume(resume_text: str = Form(...), missing_skills: str = Form(...)):
    improved = optimize_resume(resume_text, json.loads(missing_skills))
    return {"improved_resume": improved}

@app.post("/generate-email")
async def get_email(resume_text: str = Form(...), job_title: str = Form(...), company: str = Form(...)):
    email = generate_email(resume_text, job_title, company)
    return {"email": email}

@app.post("/ats-score")
async def get_ats(resume_text: str = Form(...), job_description: str = Form(...)):
    result = ats_score(resume_text, job_description)
    return result