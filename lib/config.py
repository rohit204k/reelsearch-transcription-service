import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Instagram
    INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID", "")
    INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "")
    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "")
    
    INSTAGRAM_COOKIES_FILE = os.getenv("INSTAGRAM_COOKIES_FILE", "")
    INSTAGRAM_COOKIES_FROM_BROWSER = os.getenv("INSTAGRAM_COOKIES_FROM_BROWSER", "")
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")
    INSTAGRAM_NETRC_FILE = os.getenv("INSTAGRAM_NETRC_FILE", "")

    # Webhook
    WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "")

    # Instagram Graph API
    GRAPH_API_BASE = "https://graph.instagram.com"
    GRAPH_API_VERSION = "v21.0"

    # Apify
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

    # OpenAI (optional – for Whisper API instead of local model)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
