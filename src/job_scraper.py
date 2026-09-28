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

def fetch_jobs(job_role, location="", job_type="", company_type="", num_results=10):
    cache_key = make_job_cache_key(job_role, location, job_type, company_type, num_results)
    cached = get_cached_jobs(cache_key)
    if cached is not None:
        return cached

    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY"),
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    query = job_role
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

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    jobs = []
    for job in data.get("data", []):
        jobs.append({
            "title": job.get("job_title"),
            "company": job.get("employer_name"),
            "description": job.get("job_description"),
            "link": job.get("job_apply_link"),
            "location": job.get("job_city", "") + ", " + job.get("job_country", ""),
            "job_type": job.get("job_employment_type", "")
        })
    
    set_cached_jobs(cache_key, jobs)
    return jobs