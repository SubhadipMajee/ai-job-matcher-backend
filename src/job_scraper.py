import requests
import os
import re
import datetime
from dotenv import load_dotenv
from src.cache import get_cached_jobs, set_cached_jobs, make_job_cache_key

load_dotenv()

CLEARANCE_PATTERNS = [
    r"\bsecret\s+clearance\b",
    r"\btop\s+secret\b",
    r"\bts[\/\-]sci\b",
    r"\bpolygraph\b",
    r"\bclearance\s+required\b",
    r"\bactive\s+clearance\b",
    r"\bsecurity\s+clearance\b",
    r"\bpublic\s+trust\b",
    r"\bmust\s+reside\s+in\s+maryland\b",
]

COMMON_TECH_SKILLS = [
    "python", "react", "javascript", "typescript", "fastapi", "django", "flask",
    "node.js", "nodejs", "sql", "postgresql", "mysql", "mongodb", "redis", "aws",
    "docker", "kubernetes", "git", "ci/cd", "graphql", "rest", "linux", "c++",
    "java", "golang", "go", "rust", "html", "css", "tailwind", "next.js", "nextjs",
    "redux", "kafka", "terraform", "microservices"
]


def requires_clearance_or_residency(job, user_query):
    query_lower = (user_query or "").lower()
    if "clearance" in query_lower or "government" in query_lower or "military" in query_lower:
        return False
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    for pattern in CLEARANCE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def matches_experience_filter(job, experience_level):
    if not experience_level:
        return True
    title_lower = (job.get("title") or "").lower()
    exp_text = (job.get("experience") or "").lower()
    exp_upper = experience_level.upper()

    if exp_upper == "ENTRY_LEVEL":
        # Disqualify Senior, Lead, Staff, Principal, 5+ yrs
        disqualifiers = ["senior", "sr.", "lead", "principal", "architect", "staff", "director"]
        if any(d in title_lower for d in disqualifiers):
            return False
        if "5+" in exp_text or "8+" in exp_text:
            return False

    elif exp_upper == "SENIOR":
        # Disqualify intern, junior
        if "intern" in title_lower or "junior" in title_lower or "entry" in title_lower:
            return False

    elif exp_upper in ("LEAD", "EXECUTIVE"):
        if "intern" in title_lower or "junior" in title_lower or "entry" in title_lower:
            return False

    return True


def format_salary(job):
    min_sal = job.get("job_min_salary")
    max_sal = job.get("job_max_salary")
    period = job.get("job_salary_period") or "yr"
    currency = job.get("job_salary_currency") or "$"
    if currency == "USD":
        currency = "$"

    if min_sal and max_sal:
        return f"{currency}{int(min_sal):,} - {currency}{int(max_sal):,} / {period.lower()}"
    elif min_sal:
        return f"From {currency}{int(min_sal):,} / {period.lower()}"
    elif max_sal:
        return f"Up to {currency}{int(max_sal):,} / {period.lower()}"
    return ""


def format_posted_date(iso_date):
    if not iso_date:
        return ""
    try:
        # e.g. 2026-10-04T12:00:00.000Z
        dt = datetime.datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        diff_days = (now - dt).days
        if diff_days <= 0:
            return "Today"
        elif diff_days == 1:
            return "1 day ago"
        elif diff_days < 30:
            return f"{diff_days} days ago"
        else:
            return dt.strftime("%b %d, %Y")
    except Exception:
        return ""


def compute_quick_score(text, resume_skills):
    if not resume_skills or not text:
        return 0, [], []
    text_lower = text.lower()
    matched = []
    missing = []

    for s in resume_skills:
        s_clean = str(s).strip()
        if not s_clean:
            continue
        pattern = r"(?:\b|_)" + re.escape(s_clean.lower()) + r"(?:\b|_)"
        if re.search(pattern, text_lower):
            matched.append(s_clean)
        else:
            missing.append(s_clean)

    # Also detect missing skills required in the job
    resume_skills_lower = {str(s).strip().lower() for s in resume_skills}
    job_tech_skills = []
    for tech in COMMON_TECH_SKILLS:
        if re.search(r"(?:\b|_)" + re.escape(tech) + r"(?:\b|_)", text_lower):
            job_tech_skills.append(tech)

    job_missing = [t.capitalize() for t in job_tech_skills if t not in resume_skills_lower]
    # Combine candidate's missing with job-specific detected missing
    combined_missing = list(dict.fromkeys(job_missing + missing))[:8]

    total_key_skills = len(matched) + len(job_missing)
    if total_key_skills > 0:
        raw = (len(matched) / total_key_skills) * 100
        # Reasonable bounds between 25% and 95%
        score = int(round(max(25, min(95, raw))))
    else:
        score = 45 if len(matched) > 0 else 20

    return score, matched, combined_missing


def fetch_jobs(job_role, location="", job_type="", company_type="", experience_level="", resume_skills=None, num_results=10):
    cache_key = make_job_cache_key(job_role, location, job_type, company_type, experience_level, num_results)
    cached = get_cached_jobs(cache_key)

    raw_jobs = cached
    if raw_jobs is None:
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY"),
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }

        query = job_role
        if experience_level:
            exp_labels = {
                "ENTRY_LEVEL": "entry level or junior",
                "MID_LEVEL": "mid level",
                "SENIOR": "senior",
                "LEAD": "lead or staff",
                "EXECUTIVE": "director or executive",
            }
            exp_query = exp_labels.get(experience_level.upper(), experience_level)
            query = f"{exp_query} {query}"

        if company_type:
            query += f" at {company_type} company"

        # P0 Issue 2 Fix: If location is empty, search remote/worldwide instead of defaulting to DC/Maryland
        if location and location.strip():
            query += f" in {location.strip()}"
        else:
            query += " remote"

        params = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "num_results": num_results
        }

        if job_type:
            params["employment_types"] = job_type

        if experience_level:
            exp_req_map = {
                "ENTRY_LEVEL": "under_3_years_experience",
                "SENIOR": "more_than_3_years_experience",
                "LEAD": "more_than_3_years_experience",
                "EXECUTIVE": "more_than_3_years_experience",
            }
            if experience_level.upper() in exp_req_map:
                params["job_requirements"] = exp_req_map[experience_level.upper()]

        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        raw_jobs = data.get("data", [])
        set_cached_jobs(cache_key, raw_jobs)

    jobs = []
    for job in raw_jobs:
        req_exp = job.get("job_required_experience") or {}
        months = req_exp.get("required_experience_in_months")
        exp_text = ""
        if months is not None:
            years = round(months / 12, 1)
            if years == int(years):
                years = int(years)
            exp_text = f"{years}+ yrs" if years > 0 else "0 yrs"
        elif req_exp.get("no_experience_required"):
            exp_text = "Entry Level (0 yrs)"
        else:
            title_lower = (job.get("job_title") or "").lower()
            if "senior" in title_lower or "sr." in title_lower:
                exp_text = "5+ yrs (Senior)"
            elif "lead" in title_lower or "principal" in title_lower or "staff" in title_lower:
                exp_text = "8+ yrs (Lead)"
            elif "junior" in title_lower or "entry" in title_lower or "associate" in title_lower or "intern" in title_lower:
                exp_text = "0-2 yrs (Entry)"
            elif "mid" in title_lower:
                exp_text = "3-5 yrs (Mid)"

        location_str = ""
        city = job.get("job_city") or ""
        country = job.get("job_country") or ""
        if city and country:
            location_str = f"{city}, {country}"
        elif city or country:
            location_str = city or country
        else:
            location_str = "Remote"

        is_remote = job.get("job_is_remote", False)
        if is_remote and "remote" not in location_str.lower():
            location_str = f"Remote • {location_str}" if location_str else "Remote"

        salary_str = format_salary(job)
        posted_str = format_posted_date(job.get("job_posted_at_datetime_utc"))
        highlights = job.get("job_highlights") or {}
        qualifications = highlights.get("Qualifications", [])[:3]

        item = {
            "title": job.get("job_title") or "Software Engineer",
            "company": job.get("employer_name") or "Company",
            "description": job.get("job_description") or "",
            "link": job.get("job_apply_link") or "#",
            "location": location_str,
            "job_type": job.get("job_employment_type", ""),
            "experience": exp_text,
            "salary": salary_str,
            "date_posted": posted_str,
            "qualifications": qualifications,
        }

        # P0 Issue 2 Fix: Filter out clearance / residency requirements unless requested
        if requires_clearance_or_residency(item, job_role):
            continue

        # P0 Issue 2 Fix: Respect experience filter strictly
        if not matches_experience_filter(item, experience_level):
            continue

        # P0 Issue 1 Fix: Compute automatic quick score for every job card
        combined_text = f"{item['title']} {item['description']}"
        score, matched_skills, missing_skills = compute_quick_score(combined_text, resume_skills or [])
        item["score"] = score
        item["matched_skills"] = matched_skills
        item["missing_skills"] = missing_skills

        jobs.append(item)

    # P0 Issue 3 Fix: Sort results descending by score
    jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
    return jobs