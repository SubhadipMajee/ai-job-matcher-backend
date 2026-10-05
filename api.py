from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    has_slowapi = True
except ImportError:
    has_slowapi = False

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
from src.auth import get_current_user
from src.user_store import (
    save_resume, get_resume,
    save_search, get_searches, delete_search,
    save_job, get_saved_jobs, delete_saved_job,
)
from src.tracker_store import (
    create_application, get_applications,
    update_application, delete_application,
)
from src.diff_engine import compute_diff, diff_summary
from src.semantic_matcher import match_skills_semantic
from src.interview_prep import generate_interview_prep
from src.assisted_apply import generate_apply_pack
from src.cache import get_cache_info, clear_job_cache

app = FastAPI(title="AI Job Matcher API", version="2.0.0")

if has_slowapi:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    company_type: str = Form(""),
    experience_level: str = Form(""),
    resume_skills: str = Form("[]")
):
    try:
        parsed_skills = json.loads(resume_skills) if resume_skills else []
        if not isinstance(parsed_skills, list):
            parsed_skills = []
    except Exception:
        parsed_skills = []
    jobs = fetch_jobs(
        job_role,
        location=location,
        job_type=job_type,
        company_type=company_type,
        experience_level=experience_level,
        resume_skills=parsed_skills
    )
    return {"jobs": jobs}

@app.post("/match")
async def get_match(
    resume_skills: str = Form(...),
    job_skills: str | None = Form(None),
    job_description: str | None = Form(None),
):
    try:
        r_skills = json.loads(resume_skills)
    except Exception:
        r_skills = [s.strip() for s in resume_skills.split(",") if s.strip()]

    if job_skills:
        try:
            j_skills = json.loads(job_skills)
        except Exception:
            j_skills = [s.strip() for s in job_skills.split(",") if s.strip()]
    elif job_description:
        j_skills = extract_skills(job_description, "job description")
    else:
        raise HTTPException(status_code=400, detail="Either job_skills or job_description must be provided")

    result = match_skills(r_skills, j_skills)
    result["match_score"] = result["score"]
    result["job_skills"] = j_skills
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


# ── Feature 1: Auth & Persistence ────────────────────────────────────────────
#
# All endpoints here require a valid Supabase JWT in the Authorization header.
# The frontend obtains the token via supabase.auth.signInWithPassword() and
# attaches it as:  Authorization: Bearer <access_token>
#
# Sign-up and login are handled entirely by the Supabase JS client on the
# frontend — no backend endpoints needed for those operations.


# ── Resume ───────────────────────────────────────────────────────────────────

@app.post("/resume/save")
async def save_resume_endpoint(
    resume_text: str = Form(...),
    resume_skills: str = Form(...),          # JSON-encoded list of strings
    user: dict = Depends(get_current_user),
):
    """
    Persist the user's parsed resume text and extracted skills.
    Call this right after /parse-resume succeeds on the frontend.
    """
    skills = json.loads(resume_skills)
    save_resume(user["sub"], resume_text, skills)
    return {"status": "saved"}


@app.get("/resume")
async def get_resume_endpoint(user: dict = Depends(get_current_user)):
    """
    Fetch the user's previously saved resume.
    Returns null fields if they haven't saved one yet.
    """
    data = get_resume(user["sub"])
    if not data:
        return {"resume_text": None, "resume_skills": [], "updated_at": None}
    return data


# ── Saved searches ────────────────────────────────────────────────────────────

@app.post("/searches/save")
async def save_search_endpoint(
    job_query: str = Form(...),
    location:  str = Form(""),
    user: dict = Depends(get_current_user),
):
    """Save a job search query so the user can re-run it later."""
    row = save_search(user["sub"], job_query, location)
    return row


@app.get("/searches")
async def list_searches_endpoint(user: dict = Depends(get_current_user)):
    """Return all saved searches for the logged-in user, newest first."""
    return {"searches": get_searches(user["sub"])}


@app.delete("/searches/{search_id}")
async def delete_search_endpoint(
    search_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a saved search (only succeeds if it belongs to this user)."""
    delete_search(user["sub"], search_id)
    return {"status": "deleted"}


# ── Saved (bookmarked) jobs ───────────────────────────────────────────────────

@app.post("/jobs/save")
async def save_job_endpoint(
    job_data: str = Form(...),               # full job dict, JSON-encoded
    user: dict = Depends(get_current_user),
):
    """
    Bookmark a job listing.
    job_data should be the JSON-stringified job object from /fetch-jobs,
    including at minimum: job_id, title, company, link, location, score.
    """
    job = json.loads(job_data)
    row = save_job(user["sub"], job)
    return row


@app.get("/jobs/saved")
async def list_saved_jobs_endpoint(user: dict = Depends(get_current_user)):
    """Return all bookmarked jobs for the logged-in user, newest first."""
    return {"jobs": get_saved_jobs(user["sub"])}


@app.delete("/jobs/saved/{job_id}")
async def delete_saved_job_endpoint(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove a bookmarked job (only succeeds if it belongs to this user)."""
    delete_saved_job(user["sub"], job_id)
    return {"status": "deleted"}


# ── Feature 3: Application Tracker ───────────────────────────────────────────
#
# Kanban stages in order: saved → applied → interview → offer / rejected
#
# The frontend groups GET /tracker results by the 'stage' field to render
# each kanban column. Moving a card = PATCH /tracker/{id} with { stage: "..." }

from pydantic import BaseModel

class ApplicationIn(BaseModel):
    """Body for POST /tracker — add a job to the kanban board."""
    job_id:     str
    title:      str
    company:    str
    link:       str = ""
    stage:      str = "saved"
    notes:      str = ""
    applied_at: str | None = None   # ISO date string e.g. "2024-03-15"


class ApplicationUpdate(BaseModel):
    """
    Body for PATCH /tracker/{id} — all fields optional.
    Send only the fields you want to change.
    """
    stage:      str | None = None
    notes:      str | None = None
    applied_at: str | None = None


@app.post("/tracker")
async def add_to_tracker(
    body: ApplicationIn,
    user: dict = Depends(get_current_user),
):
    """
    Add a job to the application tracker.
    Calling this twice with the same job_id is safe (upsert, no duplicate).
    """
    entry = create_application(
        user_id    = user["sub"],
        job_id     = body.job_id,
        title      = body.title,
        company    = body.company,
        link       = body.link,
        stage      = body.stage,
        notes      = body.notes,
        applied_at = body.applied_at,
    )
    return entry


@app.get("/tracker")
async def list_tracker(user: dict = Depends(get_current_user)):
    """
    Return all tracker entries for the logged-in user, sorted by most recently
    updated. The frontend groups them by 'stage' for the kanban columns.
    """
    entries = get_applications(user["sub"])
    return {"applications": entries}


@app.patch("/tracker/{application_id}")
async def update_tracker(
    application_id: str,
    body: ApplicationUpdate,
    user: dict = Depends(get_current_user),
):
    """
    Update stage, notes, or applied_at on a tracker entry.
    Used when the user drags a card to a new column or edits notes.
    Only sends the fields that are actually provided (not None).
    """
    # Build a dict of only the non-None fields the caller sent
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"detail": "Nothing to update"}

    entry = update_application(user["sub"], application_id, updates)
    if not entry:
        raise HTTPException(status_code=404, detail="Application not found")
    return entry


@app.delete("/tracker/{application_id}")
async def delete_tracker(
    application_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove an entry from the tracker."""
    delete_application(user["sub"], application_id)
    return {"status": "deleted"}


# ── Feature 4: Better AI (Diff View, Semantic Match, Interview Prep) ─────────

@app.post("/diff-resume")
async def get_resume_diff(
    original_text: str = Form(...),
    tailored_text: str = Form(...),
):
    """
    Compute structured line-by-line diff comparing original vs tailored resume.
    Returns added, removed, and unchanged chunks plus summary stats.
    """
    chunks = compute_diff(original_text, tailored_text)
    summary = diff_summary(chunks)
    return {"diff": chunks, "summary": summary}


@app.post("/semantic-match")
async def get_semantic_match(
    resume_skills: str = Form(...),
    job_description: str = Form(...),
    threshold: int = Form(50),
):
    """
    Perform semantic skill matching via Groq LLM.
    Handles related skills & synonyms (e.g. React ↔ frontend frameworks).
    """
    try:
        skills = json.loads(resume_skills)
    except Exception:
        skills = [s.strip() for s in resume_skills.split(",") if s.strip()]

    result = match_skills_semantic(skills, job_description, threshold=threshold)
    return result


@app.post("/interview-prep")
async def get_interview_prep(
    resume_text: str = Form(...),
    job_description: str = Form(...),
):
    """
    Generate customized interview preparation questions, behavioral questions,
    and gap mitigation strategies tailored to the candidate's resume and job requirements.
    """
    result = generate_interview_prep(resume_text, job_description)
    return result


# ── Feature 5: Cache Management ──────────────────────────────────────────────

@app.get("/cache/info")
async def cache_info():
    """Return in-memory JSearch cache stats."""
    return get_cache_info()


@app.post("/cache/clear")
async def cache_clear():
    """Clear in-memory cache to force fresh JSearch lookups."""
    clear_job_cache()
    return {"status": "cache cleared"}


# ── Feature 6: Assisted Apply ────────────────────────────────────────────────

@app.post("/apply-pack")
async def get_apply_pack(
    resume_text: str = Form(...),
    job_title: str = Form(...),
    company: str = Form(...),
    job_description: str = Form(...),
    link: str = Form(""),
):
    """
    Generate an Assisted Apply Pack for the candidate:
      - Tailored resume highlighting relevant skills and keywords
      - Customized cover/application email
      - Direct apply link
      - Pre-application verification checklist
    """
    pack = generate_apply_pack(
        resume_text=resume_text,
        job_title=job_title,
        company=company,
        job_description=job_description,
        link=link,
    )
    return pack
