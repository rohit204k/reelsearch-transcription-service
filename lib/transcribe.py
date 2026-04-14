"""Extract audio from a reel URL and transcribe it with Whisper."""

import subprocess
import tempfile
import requests
from pathlib import Path
from typing import Optional, Tuple
from .config import Config


def resolve_video_url(reel_url: str) -> Tuple[Optional[str], Optional[dict]]:
    """Use Apify instagram-scraper to resolve a reel permalink into a direct video URL."""
    response = requests.post(
        f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={Config.APIFY_API_TOKEN}",
        json={
            "directUrls": [reel_url],
            "resultsType": "posts",
            "resultsLimit": 1,
        },
        timeout=120,
    )
    response.raise_for_status()
    items = response.json()
    if not items:
        return None, None
    item = items[0]
    video_url = item.get("videoUrl")
    if not video_url:
        return None, None
    info = {
        "title": item.get("alt", ""),
        "description": item.get("caption", ""),
        "thumbnail": item.get("displayUrl", ""),
        "duration": item.get("videoDuration"),
        "view_count": item.get("videoViewCount"),
        "like_count": item.get("likesCount"),
    }
    return video_url, info


def extract_audio(video_url: str) -> Optional[str]:
    """Extract audio-only to a temp mp3 file via ffmpeg. Returns the file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()

    cmd = [
        "ffmpeg",
        "-i", video_url,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "128k",
        "-ar", "16000",
        "-y",
        tmp_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        Path(tmp_path).unlink(missing_ok=True)
        return None
    return tmp_path


def transcribe_audio(audio_path: str, model_size: str = "base") -> Optional[str]:
    """Transcribe an audio file using local Whisper model."""
    import whisper

    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    return result.get("text", "").strip() or None


def transcribe_reel(reel_url: str, model_size: str = "base") -> Tuple[Optional[str], Optional[dict], Optional[str]]:
    """
    End-to-end: reel permalink → resolve via yt-dlp → extract audio → transcribe.
    Returns (transcript, metadata, error_message).
    """
    audio_path = None
    try:
        video_url, info = resolve_video_url(reel_url)
        if not video_url:
            return None, None, "Could not resolve video URL"

        audio_path = extract_audio(video_url)
        if not audio_path:
            return None, None, "Could not extract audio"

        transcript = transcribe_audio(audio_path, model_size)
        if not transcript:
            return None, info, "Transcription returned empty"

        return transcript, info, None
    except Exception as e:
        return None, None, str(e)
    finally:
        if audio_path:
            Path(audio_path).unlink(missing_ok=True)
