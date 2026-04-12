"""Store and search reel transcriptions in Supabase."""

from typing import Dict, List, Optional
from .db import get_supabase

TABLE = "reels"


def insert_reel(permalink: str, user_id: str) -> Dict:
    """Insert a new reel with 'pending' status. Returns the record."""
    db = get_supabase()
    result = (
        db.table(TABLE)
        .insert({"permalink": permalink, "status": "pending", "user_id": user_id})
        .execute()
    )
    return result.data[0] if result.data else {}


def update_reel(reel_id: str, data: Dict) -> Dict:
    """Update a reel record by ID."""
    db = get_supabase()
    result = (
        db.table(TABLE)
        .update(data)
        .eq("id", reel_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def get_reel_by_permalink(permalink: str, user_id: str) -> Optional[Dict]:
    """Check if this user already has a reel with this permalink."""
    db = get_supabase()
    result = (
        db.table(TABLE)
        .select("*")
        .eq("permalink", permalink)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def search_reels(query: str, user_id: str, limit: int = 20) -> List[Dict]:
    """Full-text search over transcript and caption, scoped to user."""
    db = get_supabase()
    result = (
        db.rpc(
            "search_reels",
            {"search_query": query, "search_user_id": user_id, "result_limit": limit},
        )
        .execute()
    )
    return result.data or []


def list_reels(user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
    """List completed reels for a user, ordered by newest first."""
    db = get_supabase()
    result = (
        db.table(TABLE)
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "done")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data or []


def delete_reel(reel_id: str) -> None:
    """Delete a reel record by ID."""
    db = get_supabase()
    db.table(TABLE).delete().eq("id", reel_id).execute()


def get_reel(reel_id: str) -> Optional[Dict]:
    """Get a single reel by ID."""
    db = get_supabase()
    result = db.table(TABLE).select("*").eq("id", reel_id).single().execute()
    return result.data
