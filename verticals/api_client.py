"""Unified HTTP client with retry support."""

from __future__ import annotations

import requests

from .retry import with_retry


class APIClient:
    """Thin wrapper around requests with consistent error handling and retry."""

    @with_retry(max_retries=3, base_delay=2.0)
    def post_json(
        self,
        url: str,
        json_body: dict,
        headers: dict | None = None,
        timeout: int = 60,
    ) -> dict:
        """POST JSON and return parsed response dict."""
        r = requests.post(url, json=json_body, headers=headers or {}, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    @with_retry(max_retries=3, base_delay=2.0)
    def get_json(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int = 30,
    ) -> dict:
        """GET and return parsed response dict."""
        r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()


# Module-level singleton for convenience
_client: APIClient | None = None


def get_client() -> APIClient:
    global _client
    if _client is None:
        _client = APIClient()
    return _client
