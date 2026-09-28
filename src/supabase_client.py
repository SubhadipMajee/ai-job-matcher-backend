"""
supabase_client.py — thin wrapper around supabase-py for digest operations.

Three functions used by the /run-digest endpoint:
  get_active_settings()          → list of active digest_settings rows
  get_sent_job_ids(settings_id)  → set of job_ids already emailed for that setting
  insert_sent_jobs(settings_id, job_ids) → record newly sent jobs
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def _client() -> Client:
    """Create a fresh Supabase client from environment variables."""
    url  = os.getenv("SUPABASE_URL")
    key  = os.getenv("SUPABASE_SERVICE_KEY")   # service-role key bypasses RLS
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


def get_active_settings() -> list[dict]:
    """
    Return all rows from digest_settings where active = true.

    Each row looks like:
      { id, email, job_query, location, min_score, skills, active, created_at }
    """
    response = _client().table("digest_settings").select("*").eq("active", True).execute()
    return response.data or []


def get_sent_job_ids(settings_id: str) -> set[str]:
    """
    Return the set of job_ids already recorded in sent_jobs for this setting.
    Used to filter out duplicates before sending today's digest.
    """
    response = (
        _client()
        .table("sent_jobs")
        .select("job_id")
        .eq("settings_id", settings_id)
        .execute()
    )
    return {row["job_id"] for row in (response.data or [])}


def insert_sent_jobs(settings_id: str, job_ids: list[str]) -> None:
    """
    Record that these job_ids have been emailed for the given setting.
    The UNIQUE(settings_id, job_id) constraint on the table prevents duplicates
    even if called twice, so on_conflict=ignore is safe.
    """
    if not job_ids:
        return
    rows = [{"settings_id": settings_id, "job_id": jid} for jid in job_ids]
    _client().table("sent_jobs").upsert(rows, on_conflict="settings_id,job_id").execute()
