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

load_dotenv()

def fetch_jobs(job_role, location="", job_type="", num_results=10):
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY"),
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    query = job_role
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
    return jobs