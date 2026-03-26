import requests
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_jobs(job_role, num_results=10):
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY"),
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {"query": job_role, "page": "1", "num_pages": "1", "num_results": num_results}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    jobs = []
    for job in data.get("data", []):
        jobs.append({
            "title": job.get("job_title"),
            "company": job.get("employer_name"),
            "description": job.get("job_description"),
            "link": job.get("job_apply_link")
        })
    return jobs