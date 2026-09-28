"""
auth.py — FastAPI dependency that verifies Supabase-issued JWTs.

How it works:
  1. The frontend logs in via the Supabase JS client (supabase.auth.signIn*).
     Supabase returns an access_token (a JWT signed with your project's JWT secret).
  2. The frontend attaches that token to every API request:
         Authorization: Bearer <access_token>
  3. This dependency decodes and verifies the token.
     If it's valid, the route gets a `user` dict containing at least:
         { "sub": "<user_uuid>", "email": "...", ... }
     If it's missing or invalid, FastAPI returns 401 automatically.

We never handle passwords here — Supabase Auth owns that entirely.

Required env var:
  SUPABASE_JWT_SECRET — found in Supabase dashboard →
                        Project Settings → API → JWT Settings → JWT Secret
"""

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

# HTTPBearer extracts the token from the "Authorization: Bearer ..." header.
# auto_error=False means we get None instead of a 403 when the header is absent,
# so we can return a cleaner 401 ourselves.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency — use with `user = Depends(get_current_user)`.

    Returns the decoded JWT payload dict on success.
    Raises HTTP 401 on any auth failure.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server auth is not configured (SUPABASE_JWT_SECRET missing)",
        )

    try:
        # Supabase signs tokens with HS256.
        # audience="authenticated" is the claim Supabase sets for logged-in users.
        payload = jwt.decode(
            credentials.credentials,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        )
