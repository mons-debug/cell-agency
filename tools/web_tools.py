"""Web tools — search and scraping utilities."""
import os
import httpx
from typing import Optional


SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"


def web_search(query: str, n_results: int = 5, search_type: str = "search") -> list[dict]:
    """
    Search the web using Serper API.

    Args:
        query: Search query string
        n_results: Number of results to return (default 5)
        search_type: 'search' | 'images' | 'news' | 'places'

    Returns:
        List of result dicts with keys: title, link, snippet
    """
    if not SERPER_API_KEY:
        raise EnvironmentError("SERPER_API_KEY not set. Add it to ~/agency/.env")

    url = f"https://google.serper.dev/{search_type}"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": n_results}

    with httpx.Client(timeout=15) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("organic", [])[:n_results]:
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })
    return results


def fetch_url(url: str, timeout: int = 10) -> str:
    """
    Fetch the text content of a URL.

    Returns the response body as text (HTML/JSON/plain).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CellAgencyBot/1.0)"
    }
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text


def fetch_json(url: str, timeout: int = 10) -> dict:
    """Fetch and parse JSON from a URL."""
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def post_json(url: str, payload: dict, headers: Optional[dict] = None, timeout: int = 15) -> dict:
    """POST JSON to a URL and return parsed JSON response."""
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload, headers=req_headers)
        resp.raise_for_status()
        return resp.json()
