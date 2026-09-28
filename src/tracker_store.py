"""
tracker_store.py — read/write application tracker entries in Supabase.

Table: applications
  Stages (in order): saved → applied → interview → offer / rejected

Functions:
  create_application   — add a job to the tracker
  get_applications     — fetch all entries for a user, grouped-friendly
  update_application   — change stage, notes, or applied_at date
  delete_application   — remove an entry
"""

from src.supabase_client import _client

_TABLE = "applications"

# All columns we select back — keeps responses consistent
_SELECT = (
    "id, job_id, title, company, link, stage, "
    "notes, applied_at, created_at, updated_at"
)


def create_application(
    user_id: str,
    job_id: str,
    title: str,
    company: str,
    link: str = "",
    stage: str = "saved",
    notes: str = "",
    applied_at: str | None = None,
) -> dict:
    """
    Add a job to the tracker.

    If the same (user_id, job_id) already exists the row is returned as-is
    (upsert with ignore) so clicking 'Track this job' twice is safe.
    """
    row = {
        "user_id":   user_id,
        "job_id":    job_id,
        "title":     title,
        "company":   company,
        "link":      link,
        "stage":     stage,
        "notes":     notes,
    }
    if applied_at:
        row["applied_at"] = applied_at

    response = (
        _client()
        .table(_TABLE)
        .upsert(row, on_conflict="user_id,job_id")
        .select(_SELECT)
        .execute()
    )
    return response.data[0] if response.data else {}


def get_applications(user_id: str) -> list[dict]:
    """
    Fetch all tracker entries for this user, ordered by most recently updated.

    The frontend groups them by 'stage' to render the kanban columns.
    """
    response = (
        _client()
        .table(_TABLE)
        .select(_SELECT)
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data or []


def update_application(
    user_id: str,
    application_id: str,
    updates: dict,
) -> dict:
    """
    Update one or more fields on an existing tracker entry.

    `updates` is a dict with any subset of:
      { stage, notes, applied_at }

    Only the keys present in `updates` are changed. Always sets updated_at
    to the current timestamp so the row floats to the top of the list.

    Scoping by user_id prevents users from editing each other's entries.
    """
    # Always bump updated_at so sorting works correctly
    updates["updated_at"] = "now()"

    # Whitelist allowed fields so callers can't inject arbitrary columns
    allowed = {"stage", "notes", "applied_at", "updated_at"}
    safe_updates = {k: v for k, v in updates.items() if k in allowed}

    response = (
        _client()
        .table(_TABLE)
        .update(safe_updates)
        .eq("id", application_id)
        .eq("user_id", user_id)     # ownership check
        .select(_SELECT)
        .execute()
    )
    if not response.data:
        return {}
    return response.data[0]


def delete_application(user_id: str, application_id: str) -> None:
    """
    Remove a tracker entry (only if it belongs to this user).
    """
    _client().table(_TABLE).delete().eq("id", application_id).eq(
        "user_id", user_id
    ).execute()
