"""
user_store.py — read/write user-specific data in Supabase.

Tables used (create these in your Supabase SQL editor — DDL below):

  user_profiles(
      id          uuid PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
      resume_text text,
      resume_skills text[],
      updated_at  timestamptz DEFAULT now()
  );

  saved_searches(
      id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id     uuid REFERENCES auth.users ON DELETE CASCADE,
      job_query   text NOT NULL,
      location    text DEFAULT '',
      created_at  timestamptz DEFAULT now()
  );

  saved_jobs(
      id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id     uuid REFERENCES auth.users ON DELETE CASCADE,
      job_id      text NOT NULL,         -- same stable id built in digest.py
      title       text,
      company     text,
      link        text,
      location    text,
      score       int DEFAULT 0,
      created_at  timestamptz DEFAULT now(),
      UNIQUE(user_id, job_id)
  );

Enable Row Level Security on all three tables and add policies so that
users can only read/write their own rows:
  CREATE POLICY "own rows" ON user_profiles   USING (id = auth.uid());
  CREATE POLICY "own rows" ON saved_searches  USING (user_id = auth.uid());
  CREATE POLICY "own rows" ON saved_jobs      USING (user_id = auth.uid());

The service-role key used in supabase_client.py bypasses RLS, which is fine
for the digest worker.  These user_store functions receive the user_id from
the verified JWT, so they are safe even with RLS disabled.
"""

from src.supabase_client import _client


# ── Resume ───────────────────────────────────────────────────────────────────

def save_resume(user_id: str, resume_text: str, resume_skills: list[str]) -> None:
    """
    Upsert the user's parsed resume into user_profiles.
    'Upsert' means insert if the row doesn't exist yet, update if it does.
    """
    _client().table("user_profiles").upsert(
        {
            "id":             user_id,
            "resume_text":    resume_text,
            "resume_skills":  resume_skills,
            "updated_at":     "now()",
        },
        on_conflict="id",
    ).execute()


def get_resume(user_id: str) -> dict | None:
    """
    Fetch the saved resume for this user, or None if they haven't saved one yet.
    """
    response = (
        _client()
        .table("user_profiles")
        .select("resume_text, resume_skills, updated_at")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return response.data  # None if no row found


# ── Saved searches ────────────────────────────────────────────────────────────

def save_search(user_id: str, job_query: str, location: str = "") -> dict:
    """Insert a new saved search row and return the created record."""
    response = (
        _client()
        .table("saved_searches")
        .insert({"user_id": user_id, "job_query": job_query, "location": location})
        .execute()
    )
    return response.data[0] if response.data else {}


def get_searches(user_id: str) -> list[dict]:
    """Return all saved searches for this user, newest first."""
    response = (
        _client()
        .table("saved_searches")
        .select("id, job_query, location, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def delete_search(user_id: str, search_id: str) -> None:
    """Delete a saved search, ensuring it belongs to this user."""
    _client().table("saved_searches").delete().eq("id", search_id).eq(
        "user_id", user_id
    ).execute()


# ── Saved jobs ────────────────────────────────────────────────────────────────

def save_job(user_id: str, job: dict) -> dict:
    """
    Bookmark a job listing for this user.

    `job` should contain at least: job_id, title, company, link, location, score.
    The UNIQUE(user_id, job_id) constraint means saving the same job twice is a no-op.
    """
    row = {
        "user_id":  user_id,
        "job_id":   job.get("job_id", ""),
        "title":    job.get("title", ""),
        "company":  job.get("company", ""),
        "link":     job.get("link", ""),
        "location": job.get("location", ""),
        "score":    int(job.get("score", 0)),
    }
    response = (
        _client()
        .table("saved_jobs")
        .upsert(row, on_conflict="user_id,job_id")
        .execute()
    )
    return response.data[0] if response.data else {}


def get_saved_jobs(user_id: str) -> list[dict]:
    """Return all bookmarked jobs for this user, newest first."""
    response = (
        _client()
        .table("saved_jobs")
        .select("id, job_id, title, company, link, location, score, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def delete_saved_job(user_id: str, job_id: str) -> None:
    """Remove a bookmarked job, ensuring it belongs to this user."""
    _client().table("saved_jobs").delete().eq("job_id", job_id).eq(
        "user_id", user_id
    ).execute()
