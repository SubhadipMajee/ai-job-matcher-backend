# import requests
# import os
# from dotenv import load_dotenv

# load_dotenv()

# def fetch_jobs(job_role, num_results=10):
#     url = "https://jsearch.p.rapidapi.com/search"
#     headers = {
#         "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY"),
#         "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
#     }
#     params = {"query": job_role, "page": "1", "num_pages": "1", "num_results": num_results}
#     response = requests.get(url, headers=headers, params=params)
#     data = response.json()
#     jobs = []
#     for job in data.get("data", []):
#         jobs.append({
#             "title": job.get("job_title"),
#             "company": job.get("employer_name"),
#             "description": job.get("job_description"),
#             "link": job.get("job_apply_link")
#         })
#     return jobs

import requests
import os
from dotenv import load_dotenv
from src.cache import get_cached_jobs, set_cached_jobs, make_job_cache_key

load_dotenv()

def fetch_jobs(job_role, location="", job_type="", company_type="", experience_level="", num_results=10):
    cache_key = make_job_cache_key(job_role, location, job_type, company_type, experience_level, num_results)
    cached = get_cached_jobs(cache_key)
    if cached is not None:
        return cached

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
    if location:
        query += f" in {location}"

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
    jobs = []
    for job in data.get("data", []):
        req_exp = job.get("job_required_experience") or {}
        months = req_exp.get("required_experience_in_months")
        exp_text = ""
        if months is not None:
            years = round(months / 12, 1)
            if years == int(years):
                years = int(years)
            exp_text = f"{years}+ yrs" if years > 0 else "0 yrs"
        elif req_exp.get("no_experience_required"):
            exp_text = "Entry Level"
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

        jobs.append({
            "title": job.get("job_title"),
            "company": job.get("employer_name"),
            "description": job.get("job_description"),
            "link": job.get("job_apply_link"),
            "location": location_str,
            "job_type": job.get("job_employment_type", ""),
            "experience": exp_text,
        })
    
    set_cached_jobs(cache_key, jobs)
    return jobs