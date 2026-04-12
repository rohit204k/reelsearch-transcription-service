from supabase import create_client
from .config import Config

_client = None


def get_supabase():
    """Return a singleton Supabase client."""
    global _client
    if _client is None:
        _client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
    return _client
