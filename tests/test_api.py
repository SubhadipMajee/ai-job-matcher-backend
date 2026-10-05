"""
Tests for AI Job Matcher backend.
Covers matching logic, diff engine, cache operations, and protected routes.
"""

import pytest
from fastapi.testclient import TestClient
from api import app
from src.matcher import match_skills
from src.diff_engine import compute_diff, diff_summary
from src.cache import (
    clear_job_cache,
    set_cached_jobs,
    get_cached_jobs,
    make_job_cache_key,
)

client = TestClient(app)


# ── 1. Unit Tests: Skill Matching ───────────────────────────────────────────

def test_match_skills_full_overlap():
    resume_skills = ["Python", "FastAPI", "Docker"]
    job_skills = ["python", "docker"]
    result = match_skills(resume_skills, job_skills)
    assert result["score"] == 100.0
    assert set(result["matched_skills"]) == {"python", "docker"}
    assert result["missing_skills"] == []


def test_match_skills_partial_overlap():
    resume_skills = ["Python"]
    job_skills = ["Python", "Kubernetes"]
    result = match_skills(resume_skills, job_skills)
    assert result["score"] == 50.0
    assert result["matched_skills"] == ["python"]
    assert result["missing_skills"] == ["kubernetes"]


def test_match_skills_zero_overlap():
    resume_skills = ["Ruby"]
    job_skills = ["Go", "Rust"]
    result = match_skills(resume_skills, job_skills)
    assert result["score"] == 0.0
    assert len(result["missing_skills"]) == 2


# ── 2. Unit Tests: Diff Engine ──────────────────────────────────────────────

def test_diff_engine_identical():
    text = "Software Engineer\nPython, FastAPI"
    chunks = compute_diff(text, text)
    summary = diff_summary(chunks)
    assert summary["lines_added"] == 0
    assert summary["lines_removed"] == 0
    assert summary["lines_unchanged"] == 2


def test_diff_engine_modified():
    orig = "Python Developer\nAWS"
    tailored = "Senior Python Developer\nAWS, Docker"
    chunks = compute_diff(orig, tailored)
    summary = diff_summary(chunks)
    assert summary["lines_added"] > 0
    assert summary["lines_removed"] > 0


# ── 3. Unit Tests: TTL Cache ────────────────────────────────────────────────

def test_job_cache_lifecycle():
    clear_job_cache()
    key = make_job_cache_key("python developer", "remote")
    assert get_cached_jobs(key) is None

    mock_jobs = [{"title": "Python Dev", "company": "Acme"}]
    set_cached_jobs(key, mock_jobs)
    assert get_cached_jobs(key) == mock_jobs

    clear_job_cache()
    assert get_cached_jobs(key) is None


# ── 4. API Integration Tests ────────────────────────────────────────────────

def test_endpoint_cache_info():
    response = client.get("/cache/info")
    assert response.status_code == 200
    data = response.json()
    assert "cached_queries_count" in data


def test_endpoint_match():
    response = client.post(
        "/match",
        data={
            "resume_skills": '["Python", "FastAPI"]',
            "job_skills": '["Python", "React"]',
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 50.0
    assert "python" in data["matched_skills"]
    assert data["match_score"] == 50.0


def test_endpoint_match_with_job_description(monkeypatch):
    monkeypatch.setattr("api.extract_skills", lambda desc, source: ["python", "react"])
    response = client.post(
        "/match",
        data={
            "resume_skills": '["Python", "FastAPI"]',
            "job_description": "We need Python and React",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 50.0
    assert "python" in data["matched_skills"]
    assert data["match_score"] == 50.0


def test_endpoint_diff_resume():
    response = client.post(
        "/diff-resume",
        data={
            "original_text": "Skill: Python",
            "tailored_text": "Skill: Python, FastAPI",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "diff" in data
    assert "summary" in data


def test_endpoint_protected_without_auth():
    # Should reject with 401 when Authorization header is missing
    response = client.get("/resume")
    assert response.status_code == 401


def test_endpoint_digest_without_secret():
    # Should reject with 401 when X-Digest-Secret is missing
    response = client.post("/run-digest")
    assert response.status_code == 401
