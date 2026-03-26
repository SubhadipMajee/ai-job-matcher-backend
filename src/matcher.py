def match_skills(resume_skills, job_skills):
    resume_set = set([s.lower() for s in resume_skills])
    job_set = set([s.lower() for s in job_skills])
    matched = job_set.intersection(resume_set)
    missing = job_set.difference(resume_set)
    score = round((len(matched) / len(job_set)) * 100, 2) if len(job_set) > 0 else 0
    return {"score": score, "matched_skills": list(matched), "missing_skills": list(missing)}