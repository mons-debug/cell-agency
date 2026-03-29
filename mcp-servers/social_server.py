"""
Cell Agency — Social Media MCP Server
Provides: Instagram Graph API, content scheduling, hashtag research,
          social analytics, post management.
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
from fastmcp import FastMCP

mcp = FastMCP("social")

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
FB_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")

GRAPH_API = "https://graph.facebook.com/v19.0"


def _ig_headers() -> dict:
    return {"Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}"}


def _require_ig():
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
        raise EnvironmentError(
            "INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID must be set in ~/agency/.env"
        )


# ─── INSTAGRAM POSTS ──────────────────────────────────────────────────────────

@mcp.tool()
def ig_create_image_post(
    image_url: str,
    caption: str,
    location_id: Optional[str] = None,
) -> dict:
    """
    Publish an image post to Instagram Business account.

    Args:
        image_url: Public URL of the image (must be accessible by Meta servers)
        caption: Post caption (include hashtags here)
        location_id: Optional Instagram location ID

    Returns:
        dict with post ID and permalink
    """
    _require_ig()

    # Step 1: Create media container
    container_url = f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    params: dict = {
        "image_url": image_url,
        "caption": caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    if location_id:
        params["location_id"] = location_id

    with httpx.Client(timeout=30) as client:
        resp = client.post(container_url, params=params)
        resp.raise_for_status()
        container_id = resp.json()["id"]

    # Step 2: Publish the container
    publish_url = f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    with httpx.Client(timeout=30) as client:
        pub_resp = client.post(publish_url, params={
            "creation_id": container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        pub_resp.raise_for_status()
        post_id = pub_resp.json()["id"]

    return {"post_id": post_id, "container_id": container_id, "status": "published"}


@mcp.tool()
def ig_create_carousel_post(
    image_urls: list[str],
    caption: str,
) -> dict:
    """
    Publish a carousel (multi-image) post to Instagram.

    Args:
        image_urls: List of public image URLs (2–10 images)
        caption: Post caption

    Returns:
        dict with post ID
    """
    _require_ig()
    if not 2 <= len(image_urls) <= 10:
        raise ValueError("Carousel requires 2–10 images")

    # Create individual media containers
    child_ids = []
    with httpx.Client(timeout=30) as client:
        for url in image_urls:
            resp = client.post(f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media", params={
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            })
            resp.raise_for_status()
            child_ids.append(resp.json()["id"])

    # Create carousel container
    with httpx.Client(timeout=30) as client:
        carousel_resp = client.post(f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media", params={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        carousel_resp.raise_for_status()
        carousel_id = carousel_resp.json()["id"]

    # Publish
    with httpx.Client(timeout=30) as client:
        pub_resp = client.post(f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish", params={
            "creation_id": carousel_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        pub_resp.raise_for_status()
        post_id = pub_resp.json()["id"]

    return {"post_id": post_id, "status": "published", "images": len(image_urls)}


@mcp.tool()
def ig_schedule_post(
    image_url: str,
    caption: str,
    publish_time_iso: str,
) -> dict:
    """
    Schedule an Instagram post for a future time.

    Args:
        image_url: Public URL of the image
        caption: Post caption
        publish_time_iso: ISO 8601 datetime in UTC (e.g. '2026-04-01T10:00:00Z')

    Returns:
        dict with container ID and scheduled time
    """
    _require_ig()

    # Convert to Unix timestamp
    dt = datetime.fromisoformat(publish_time_iso.replace("Z", "+00:00"))
    publish_ts = int(dt.timestamp())

    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media", params={
            "image_url": image_url,
            "caption": caption,
            "scheduled_publish_time": publish_ts,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        container_id = resp.json()["id"]

    return {
        "container_id": container_id,
        "scheduled_for": publish_time_iso,
        "status": "scheduled",
    }


@mcp.tool()
def ig_get_recent_posts(limit: int = 10) -> list[dict]:
    """
    Get recent posts from the Instagram Business account.

    Returns list of posts with id, caption, timestamp, media_type, permalink, like_count.
    """
    _require_ig()
    fields = "id,caption,timestamp,media_type,permalink,like_count,comments_count"
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media", params={
            "fields": fields,
            "limit": limit,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return resp.json().get("data", [])


@mcp.tool()
def ig_get_account_insights(period: str = "day", metric: str = "impressions,reach,profile_views") -> dict:
    """
    Get Instagram account-level insights.

    Args:
        period: 'day' | 'week' | 'days_28' | 'month'
        metric: Comma-separated metrics

    Returns:
        Raw insights data from Graph API
    """
    _require_ig()
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/insights", params={
            "metric": metric,
            "period": period,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def ig_delete_post(media_id: str) -> dict:
    """Delete an Instagram post by media ID."""
    _require_ig()
    with httpx.Client(timeout=15) as client:
        resp = client.delete(f"{GRAPH_API}/{media_id}", params={
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return {"deleted": True, "media_id": media_id}


# ─── HASHTAG RESEARCH ─────────────────────────────────────────────────────────

@mcp.tool()
def ig_hashtag_search(hashtag: str) -> dict:
    """
    Search for a hashtag on Instagram and get its media count.

    Returns: hashtag id and media count
    """
    _require_ig()
    with httpx.Client(timeout=15) as client:
        # Search for hashtag
        search_resp = client.get(f"{GRAPH_API}/ig_hashtag_search", params={
            "user_id": INSTAGRAM_BUSINESS_ACCOUNT_ID,
            "q": hashtag.lstrip("#"),
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        search_resp.raise_for_status()
        hashtag_id = search_resp.json()["data"][0]["id"]

        # Get media count
        info_resp = client.get(f"{GRAPH_API}/{hashtag_id}", params={
            "fields": "id,name,media_count",
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })
        info_resp.raise_for_status()
        return info_resp.json()


@mcp.tool()
def suggest_hashtags(niche: str, language: str = "en", count: int = 20) -> list[str]:
    """
    Generate hashtag suggestions for a given niche using Claude (via the caller).

    This returns a structured list — the actual generation is done by the content agent.
    This tool returns format guidance so the agent can fill in the hashtags.

    Args:
        niche: Content niche (e.g. 'beauty clinic morocco', 'laser hair removal')
        language: 'en' | 'fr' | 'ar'
        count: Number of hashtags to suggest

    Returns:
        Prompt-ready instruction for content agent
    """
    return [
        f"[Generate {count} Instagram hashtags for: {niche}]",
        f"[Language preference: {language}]",
        "[Mix: 5 broad (1M+ posts), 10 medium (100k-1M), 5 niche (<100k)]",
        "[Include local/geographic hashtags if location-specific]",
    ]


# ─── FACEBOOK PAGE ────────────────────────────────────────────────────────────

@mcp.tool()
def fb_post_to_page(message: str, link: Optional[str] = None) -> dict:
    """Post a text update (optionally with link) to the Facebook Page."""
    if not FB_ACCESS_TOKEN or not FB_PAGE_ID:
        raise EnvironmentError("FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID must be set.")
    params: dict = {"message": message, "access_token": FB_ACCESS_TOKEN}
    if link:
        params["link"] = link
    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{GRAPH_API}/{FB_PAGE_ID}/feed", params=params)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def fb_get_page_insights(metric: str = "page_impressions,page_reach", period: str = "day") -> dict:
    """Get Facebook Page insights."""
    if not FB_ACCESS_TOKEN or not FB_PAGE_ID:
        raise EnvironmentError("FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID must be set.")
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_API}/{FB_PAGE_ID}/insights", params={
            "metric": metric,
            "period": period,
            "access_token": FB_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run()
