"""
cache.py — In-memory TTL cache for expensive external API requests (JSearch).

RapidAPI JSearch free tier has strict quotas. Caching searches for 1 hour
prevents duplicate API hits for repeated searches with the same parameters.
"""

from cachetools import TTLCache

# Cache up to 200 distinct search queries for 1 hour (3600 seconds)
_job_cache = TTLCache(maxsize=200, ttl=3600)


def get_cached_jobs(cache_key: tuple):
    """Retrieve cached jobs if available and not expired."""
    return _job_cache.get(cache_key)


def set_cached_jobs(cache_key: tuple, jobs: list):
    """Store jobs in cache."""
    _job_cache[cache_key] = jobs


def make_job_cache_key(
    job_role: str,
    location: str = "",
    job_type: str = "",
    company_type: str = "",
    experience_level: str = "",
    num_results: int = 10
) -> tuple:
    """Build a deterministic cache key tuple."""
    return (
        job_role.strip().lower(),
        location.strip().lower(),
        job_type.strip().lower(),
        company_type.strip().lower(),
        experience_level.strip().lower(),
        num_results,
    )


def clear_job_cache():
    """Clear all cached search entries."""
    _job_cache.clear()


def get_cache_info():
    """Return current cache usage."""
    return {
        "cached_queries_count": len(_job_cache),
        "maxsize": _job_cache.maxsize,
        "ttl_seconds": _job_cache.ttl,
    }
