"""Instagram Graph API client for fetching media."""

import requests
from typing import Dict, List, Optional
from .config import Config


class InstagramClient:
    def __init__(
        self,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.access_token = access_token or Config.INSTAGRAM_ACCESS_TOKEN
        self.user_id = user_id or Config.INSTAGRAM_USER_ID
        self.base_url = f"{Config.GRAPH_API_BASE}/{Config.GRAPH_API_VERSION}"

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_user_media(self, limit: int = 25, fields: Optional[List[str]] = None) -> Dict:
        """Fetch recent media from the business account."""
        if fields is None:
            fields = [
                "id",
                "media_type",
                "media_url",
                "thumbnail_url",
                "permalink",
                "timestamp",
                "caption",
            ]
        return self._request(
            f"{self.user_id}/media",
            {"fields": ",".join(fields), "limit": min(limit, 100)},
        )

    def get_media_by_id(self, media_id: str, fields: Optional[List[str]] = None) -> Dict:
        """Fetch a single media item by ID."""
        if fields is None:
            fields = [
                "id",
                "media_type",
                "media_url",
                "thumbnail_url",
                "permalink",
                "timestamp",
                "caption",
            ]
        return self._request(media_id, {"fields": ",".join(fields)})

    def get_user_info(self) -> Dict:
        """Get account info for the authenticated user."""
        return self._request(
            self.user_id,
            {"fields": "id,username,account_type,media_count"},
        )
