"""
Transcription service — handles reel transcription and stores to Supabase.
Run with: python server.py
"""

import re
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lib.transcribe import transcribe_reel
from lib.auth import get_user_from_token
from lib.indexer import insert_reel, update_reel, get_reel_by_permalink

app = FastAPI(title="ReelSearch Transcription Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REEL_URL_PATTERN = re.compile(
    r"https?://(www\.)?instagram\.com/(reel|reels|p)/[\w-]+/?"
)


class SubmitRequest(BaseModel):
    url: str


def get_user_id(authorization: Optional[str]) -> str:
    """Extract user_id from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization.split(" ", 1)[1]
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user["id"]


@app.post("/api/submit")
async def submit_reel(req: SubmitRequest, authorization: Optional[str] = Header(None)):
    """Accept a reel URL, transcribe it, store in DB, and return result."""

    # Authenticate user
    user_id = get_user_id(authorization)

    url = req.url.strip()

    # Validate URL
    if not REEL_URL_PATTERN.match(url):
        raise HTTPException(status_code=400, detail="Invalid Instagram reel URL")

    # Normalize permalink
    permalink = url.split("?")[0]
    if not permalink.endswith("/"):
        permalink += "/"

    # Check if already exists
    existing = get_reel_by_permalink(permalink, user_id=user_id)
    if existing:
        return {"status": "exists", "reel": existing}

    # Insert as pending
    reel = insert_reel(permalink, user_id=user_id)
    reel_id = reel["id"]

    try:
        # Transcribe
        transcript, info, error = transcribe_reel(permalink)

        if error:
            update_reel(reel_id, {"status": "error"})
            raise HTTPException(status_code=422, detail=f"Transcription failed: {error}")

        # Update with results
        update_data = {
            "transcript": transcript,
            "status": "done",
            "title": (info or {}).get("title", ""),
            "caption": (info or {}).get("description", ""),
            "thumbnail_url": (info or {}).get("thumbnail", ""),
            "duration": (info or {}).get("duration"),
            "view_count": (info or {}).get("view_count"),
            "like_count": (info or {}).get("like_count"),
        }
        updated = update_reel(reel_id, update_data)

        return {"status": "ok", "reel": updated}

    except HTTPException:
        raise
    except Exception as e:
        update_reel(reel_id, {"status": "error"})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
