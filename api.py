from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import shutil, os, json

from src.resume_parser import extract_text_from_pdf
from src.job_scraper import fetch_jobs
from src.skill_extractor import extract_skills, ats_score, skill_roadmap
from src.matcher import match_skills
from src.resume_optimizer import optimize_resume, tailor_resume
from src.email_generator import generate_email
from src.digest import get_matched_jobs
from src.supabase_client import get_active_settings, get_sent_job_ids, insert_sent_jobs
from src.digest_emailer import send_digest_email

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
async def get_jobs(
    job_role: str = Form(...),
    location: str = Form(""),
    job_type: str = Form(""),
    company_type: str = Form("")
):
    jobs = fetch_jobs(job_role, location, job_type, company_type)
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

@app.post("/skill-roadmap")
async def get_roadmap(missing_skills: str = Form(...)):
    skills = json.loads(missing_skills)
    result = skill_roadmap(skills)
    return {"roadmap": result}

@app.post("/tailor-resume")
async def tailor_resume_endpoint(
    resume_text: str = Form(...),
    job_description: str = Form(...)\
):
    result = tailor_resume(resume_text, job_description)
    return {"tailored_resume": result}


# ── Daily digest endpoint ────────────────────────────────────────────────────

@app.post("/run-digest")
async def run_digest(x_digest_secret: str = Header(default="")):
    """
    Protected endpoint called daily by GitHub Actions.

    Auth: compare the X-Digest-Secret header against the DIGEST_SECRET
    environment variable.  Returns 401 if they don't match.

    For each active digest_settings row it:
      1. Calls get_matched_jobs() using the stored skills & query
      2. Filters out job_ids already recorded in sent_jobs
      3. Sends the email via Resend (only if new jobs exist)
      4. Records the newly sent job_ids in sent_jobs
      5. Catches any per-setting exception so one bad row never
         stops the rest from being processed.

    Returns a JSON summary: { settings_processed, emails_sent, errors }
    """
    expected_secret = os.getenv("DIGEST_SECRET", "")
    if not expected_secret or x_digest_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing digest secret")

    settings      = get_active_settings()
    emails_sent   = 0
    errors        = []

    for setting in settings:
        sid = setting["id"]
        try:
            # 1. Fetch and score jobs for this user's query + skills
            all_matches = get_matched_jobs(
                skills      = setting.get("skills") or [],
                job_query   = setting.get("job_query", ""),
                location    = setting.get("location", ""),
                min_score   = setting.get("min_score", 0),
            )

            # 2. Filter out jobs already emailed to this user
            already_sent = get_sent_job_ids(sid)
            new_matches  = [j for j in all_matches if j["job_id"] not in already_sent]

            # 3. Send the email (no-op if new_matches is empty)
            sent = send_digest_email(setting["email"], new_matches)

            # 4. Record the newly sent jobs
            if sent:
                insert_sent_jobs(sid, [j["job_id"] for j in new_matches[:10]])
                emails_sent += 1

        except Exception as exc:
            # Log the error but continue processing the next setting
            errors.append({"settings_id": sid, "error": str(exc)})

    return JSONResponse({
        "settings_processed": len(settings),
        "emails_sent":        emails_sent,
        "errors":             errors,
    })