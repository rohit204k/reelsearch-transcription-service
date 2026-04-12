"""Verify Supabase JWT tokens to extract user info."""

from typing import Optional, Dict
from .db import get_supabase


def get_user_from_token(token: str) -> Optional[Dict]:
    """
    Verify a Supabase access token and return the user dict.
    Returns None if the token is invalid.
    """
    try:
        db = get_supabase()
        res = db.auth.get_user(token)
        if res and res.user:
            return {"id": res.user.id, "email": res.user.email}
        return None
    except Exception:
        return None
