"""
auth.py — FastAPI dependency that verifies Supabase-issued JWTs.

Supabase now signs tokens with ECC (P-256) / ES256 by default.
We verify tokens using Supabase's public JWKS endpoint so we never
need to store a private key ourselves.

How it works:
  1. Frontend signs in via supabase.auth.signIn*() → gets an access_token (JWT).
  2. Frontend sends: Authorization: Bearer <access_token>
  3. This dependency fetches Supabase's public JWKS (cached after first call),
     finds the key matching the token's "kid" header, and verifies the signature.
  4. Returns the decoded payload { "sub": "<user_uuid>", "email": "...", ... }
     or raises HTTP 401.

Required env var:
  SUPABASE_URL — your project URL, e.g. https://xxxxx.supabase.co
"""

import os
import httpx
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

# HTTPBearer extracts "Authorization: Bearer <token>" from the request header.
# auto_error=False lets us return a clean 401 instead of FastAPI's default 403.
_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """
    Fetch Supabase's public JSON Web Key Set (JWKS) and cache it in memory.

    lru_cache(maxsize=1) means this HTTP call only happens once per server
    process lifetime. If Supabase ever rotates keys, restart the server.

    The JWKS contains the public key(s) Supabase uses to sign JWTs.
    We use the public key to VERIFY tokens — we never see the private key.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL environment variable is not set")

    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    response = httpx.get(jwks_url, timeout=10)
    response.raise_for_status()
    return response.json()


def _find_key(jwks: dict, kid: str) -> dict:
    """
    Find the public key in the JWKS that matches the token's 'kid' header.

    Each token's header contains 'kid' (key ID) so the verifier knows
    which key was used to sign it.
    """
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"No matching public key found for kid={kid!r}. "
               "Try restarting the server if Supabase recently rotated keys.",
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency — use with `user = Depends(get_current_user)`.

    Returns the decoded JWT payload on success (contains at minimum 'sub',
    the user's UUID, and 'email').
    Raises HTTP 401 on any failure.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing. "
                   "Add 'Authorization: Bearer <your_supabase_access_token>'",
        )

    token = credentials.credentials

    try:
        # Step 1: read the header without verifying — just to extract 'kid'
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid", "")

        # Step 2: fetch (or retrieve from cache) Supabase's public JWKS
        jwks = _get_jwks()

        # Step 3: find the right public key for this token
        public_key = _find_key(jwks, kid)

        # Step 4: fully verify the token (signature + expiry + audience)
        # Supabase supports ES256 (ECC P-256, new default) and RS256.
        # HS256 (legacy) is kept for backward compatibility with older projects.
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["ES256", "RS256", "HS256"],
            audience="authenticated",
        )
        return payload

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        )
