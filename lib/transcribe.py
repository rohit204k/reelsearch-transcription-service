"""Extract audio from a reel URL and transcribe it with Whisper."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from .config import Config


def resolve_video_url(reel_url: str) -> Tuple[Optional[str], Optional[dict]]:
    """Use yt-dlp to resolve a reel permalink into a direct video stream URL."""
    import yt_dlp

    opts = {"quiet": True, "no_warnings": True, "format": "best"}
    
    if Config.INSTAGRAM_COOKIES_FILE:
        opts["cookiefile"] = Config.INSTAGRAM_COOKIES_FILE
    elif Config.INSTAGRAM_COOKIES_FROM_BROWSER:
        opts["cookiesfrombrowser"] = (Config.INSTAGRAM_COOKIES_FROM_BROWSER,)
    elif Config.INSTAGRAM_USERNAME and Config.INSTAGRAM_PASSWORD:
        opts["username"] = Config.INSTAGRAM_USERNAME
        opts["password"] = Config.INSTAGRAM_PASSWORD
    elif Config.INSTAGRAM_NETRC_FILE:
        opts["netrc"] = True
        if Config.INSTAGRAM_NETRC_FILE and Config.INSTAGRAM_NETRC_FILE != "~/.netrc":
            opts["netrc_location"] = Config.INSTAGRAM_NETRC_FILE
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(reel_url, download=False)
        if not info:
            return None, None
        return info.get("url"), info


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
