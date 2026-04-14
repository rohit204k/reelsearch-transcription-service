"""
Transcription service — handles reel transcription and stores to Supabase.
Run with: python server.py
"""

import re
from typing import Optional
from fastapi import BackgroundTasks, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
from urllib.parse import urlparse

from lib.transcribe import transcribe_reel
from lib.auth import get_user_from_token
from lib.indexer import insert_reel, update_reel, get_reel_by_permalink, get_reel

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


def _process_reel(reel_id: str, permalink: str) -> None:
    """Background task: transcribe reel and update DB."""
    try:
        transcript, info, error = transcribe_reel(permalink)

        if error:
            print(f"Transcription error: {error}")
            update_reel(reel_id, {"status": "error"})
            return

        update_reel(reel_id, {
            "transcript": transcript,
            "status": "done",
            "title": (info or {}).get("title", ""),
            "caption": (info or {}).get("description", ""),
            "thumbnail_url": (info or {}).get("thumbnail", ""),
            "duration": (info or {}).get("duration"),
            "view_count": (info or {}).get("view_count"),
            "like_count": (info or {}).get("like_count"),
        })

    except Exception as e:
        print(f"Transcription exception: {e}")
        update_reel(reel_id, {"status": "error"})


@app.post("/api/submit")
async def submit_reel(
    req: SubmitRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
):
    """Accept a reel URL, insert as pending, kick off transcription in background."""

    user_id = get_user_id(authorization)

    url = req.url.strip()

    if not REEL_URL_PATTERN.match(url):
        raise HTTPException(status_code=400, detail="Invalid Instagram reel URL")

    # Normalize permalink
    permalink = url.split("?")[0]
    if not permalink.endswith("/"):
        permalink += "/"

    # Return existing record immediately if already processed
    existing = get_reel_by_permalink(permalink, user_id=user_id)
    if existing:
        return {"status": "exists", "reel": existing}

    # Insert as pending and return immediately
    reel = insert_reel(permalink, user_id=user_id)

    # Transcribe in background
    background_tasks.add_task(_process_reel, reel["id"], permalink)

    return {"status": "pending", "reel": reel}


@app.get("/api/reels/{reel_id}")
async def get_reel_status(reel_id: str, authorization: Optional[str] = Header(None)):
    """Poll for reel status."""
    get_user_id(authorization)
    reel = get_reel(reel_id)
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    return {"reel": reel}


@app.get("/api/proxy-image")
async def proxy_image(url: str):
    """
    Proxy image endpoint to serve Instagram thumbnails and other images.
    Avoids CORS and referrer policy issues.
    
    Usage: /api/proxy-image?url=<encoded_url>
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")
    
    # Basic URL validation
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    try:
        # Fetch the image with timeout
        response = requests.get(url, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        # Get content type from response headers
        content_type = response.headers.get("content-type", "application/octet-stream")
        
        # Return as streaming response
        return StreamingResponse(
            iter([response.content]),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": "inline",
            }
        )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Image fetch timeout")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch image: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch image: {str(e)}")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
