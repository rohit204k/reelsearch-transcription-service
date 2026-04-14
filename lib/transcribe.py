"""Extract audio from a reel URL and transcribe it with Whisper."""

import subprocess
import tempfile
import time
import requests
from pathlib import Path
from typing import Optional, Tuple
from .config import Config

APIFY_MAX_WAIT_SECS = 120  # max time to wait for Apify run
APIFY_POLL_INTERVAL = 5
DOWNLOAD_TIMEOUT = 120      # max time to download video
FFMPEG_TIMEOUT = 180        # max time for ffmpeg to extract audio
WHISPER_TIMEOUT = 300       # max time for Whisper transcription


def resolve_video_url(reel_url: str) -> Tuple[Optional[str], Optional[dict]]:
    """Use Apify instagram-scraper (async) to resolve a reel permalink into a direct video URL."""
    token = Config.APIFY_API_TOKEN

    # Step 1: Start the run
    run_response = requests.post(
        f"https://api.apify.com/v2/acts/apify~instagram-scraper/runs?token={token}",
        json={
            "directUrls": [reel_url],
            "resultsType": "posts",
            "resultsLimit": 1,
        },
        timeout=30,
    )
    run_response.raise_for_status()
    run = run_response.json()["data"]
    run_id = run["id"]
    dataset_id = run["defaultDatasetId"]

    # Step 2: Poll until finished
    polls = APIFY_MAX_WAIT_SECS // APIFY_POLL_INTERVAL
    for _ in range(polls):
        time.sleep(APIFY_POLL_INTERVAL)
        status_response = requests.get(
            f"https://api.apify.com/v2/acts/apify~instagram-scraper/runs/{run_id}?token={token}",
            timeout=10,
        )
        status_response.raise_for_status()
        status = status_response.json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            return None, None

    # Step 3: Fetch results
    dataset_response = requests.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={token}",
        timeout=10,
    )
    dataset_response.raise_for_status()
    items = dataset_response.json()
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


def download_video(video_url: str) -> Optional[str]:
    """Download video to a temp file. Returns the file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        with requests.get(video_url, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return tmp_path
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        return None


def extract_audio(video_path: str) -> Optional[str]:
    """Extract audio-only to a temp mp3 file via ffmpeg. Returns the file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "128k",
        "-ar", "16000",
        "-y",
        tmp_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
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
    End-to-end: reel permalink → Apify → download video → extract audio → transcribe.
    Returns (transcript, metadata, error_message).
    """
    video_path = None
    audio_path = None
    try:
        video_url, info = resolve_video_url(reel_url)
        if not video_url:
            return None, None, "Could not resolve video URL"

        video_path = download_video(video_url)
        if not video_path:
            return None, None, "Could not download video"

        audio_path = extract_audio(video_path)
        if not audio_path:
            return None, None, "Could not extract audio"

        transcript = transcribe_audio(audio_path, model_size)
        if not transcript:
            return None, info, "Transcription returned empty"

        return transcript, info, None
    except Exception as e:
        return None, None, str(e)
    finally:
        if video_path:
            Path(video_path).unlink(missing_ok=True)
        if audio_path:
            Path(audio_path).unlink(missing_ok=True)
