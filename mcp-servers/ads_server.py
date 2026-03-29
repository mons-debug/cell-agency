"""
Cell Agency — Ads MCP Server
Provides: Meta Ads Manager (Facebook/Instagram ads), Google Ads,
          campaign creation, budget management, performance reporting.
"""
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
from fastmcp import FastMCP

mcp = FastMCP("ads")

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID", "")  # e.g. "act_123456789"
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")

GRAPH_API = "https://graph.facebook.com/v19.0"


def _require_meta():
    if not META_ACCESS_TOKEN or not META_AD_ACCOUNT_ID:
        raise EnvironmentError(
            "META_ACCESS_TOKEN and META_AD_ACCOUNT_ID must be set in ~/agency/.env"
        )


# ─── META ADS ─────────────────────────────────────────────────────────────────

@mcp.tool()
def meta_list_campaigns(status: str = "ACTIVE") -> list[dict]:
    """
    List Meta (Facebook/Instagram) ad campaigns.

    Args:
        status: 'ACTIVE' | 'PAUSED' | 'ARCHIVED' | 'ALL'

    Returns:
        List of campaigns with id, name, status, objective, daily_budget
    """
    _require_meta()
    fields = "id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time"
    params: dict = {
        "fields": fields,
        "access_token": META_ACCESS_TOKEN,
    }
    if status != "ALL":
        params["effective_status"] = f'["{status}"]'

    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_API}/{META_AD_ACCOUNT_ID}/campaigns", params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])


@mcp.tool()
def meta_create_campaign(
    name: str,
    objective: str,
    daily_budget_mad: float,
    status: str = "PAUSED",
) -> dict:
    """
    Create a new Meta ad campaign.

    Args:
        name: Campaign name
        objective: 'OUTCOME_AWARENESS' | 'OUTCOME_TRAFFIC' | 'OUTCOME_ENGAGEMENT' |
                   'OUTCOME_LEADS' | 'OUTCOME_APP_PROMOTION' | 'OUTCOME_SALES'
        daily_budget_mad: Daily budget in MAD (Moroccan Dirham) — will convert to cents
        status: 'PAUSED' (recommended for review) | 'ACTIVE'

    Returns:
        dict with campaign ID
    """
    _require_meta()
    # Meta uses currency in cents/smallest unit. MAD → centimes (×100)
    daily_budget_cents = int(daily_budget_mad * 100)

    with httpx.Client(timeout=20) as client:
        resp = client.post(f"{GRAPH_API}/{META_AD_ACCOUNT_ID}/campaigns", data={
            "name": name,
            "objective": objective,
            "daily_budget": daily_budget_cents,
            "status": status,
            "special_ad_categories": "[]",
            "access_token": META_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def meta_pause_campaign(campaign_id: str) -> dict:
    """Pause a Meta ad campaign."""
    _require_meta()
    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{GRAPH_API}/{campaign_id}", data={
            "status": "PAUSED",
            "access_token": META_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return {"campaign_id": campaign_id, "status": "paused"}


@mcp.tool()
def meta_activate_campaign(campaign_id: str) -> dict:
    """Activate (unpause) a Meta ad campaign."""
    _require_meta()
    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{GRAPH_API}/{campaign_id}", data={
            "status": "ACTIVE",
            "access_token": META_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return {"campaign_id": campaign_id, "status": "active"}


@mcp.tool()
def meta_update_budget(campaign_id: str, daily_budget_mad: float) -> dict:
    """Update the daily budget of a Meta campaign (in MAD)."""
    _require_meta()
    daily_budget_cents = int(daily_budget_mad * 100)
    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{GRAPH_API}/{campaign_id}", data={
            "daily_budget": daily_budget_cents,
            "access_token": META_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return {"campaign_id": campaign_id, "new_daily_budget_mad": daily_budget_mad}


@mcp.tool()
def meta_get_campaign_insights(
    campaign_id: str,
    date_preset: str = "last_7d",
) -> dict:
    """
    Get performance metrics for a Meta campaign.

    Args:
        campaign_id: Campaign ID
        date_preset: 'today' | 'yesterday' | 'last_7d' | 'last_30d' | 'last_month'

    Returns:
        Insights data: impressions, reach, clicks, spend, cpc, ctr, conversions
    """
    _require_meta()
    fields = "impressions,reach,clicks,spend,cpc,ctr,actions,cost_per_action_type"
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_API}/{campaign_id}/insights", params={
            "fields": fields,
            "date_preset": date_preset,
            "access_token": META_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return data[0] if data else {}


@mcp.tool()
def meta_get_ad_account_overview() -> dict:
    """
    Get overview of the Meta ad account: balance, currency, spend limits.
    """
    _require_meta()
    fields = "name,currency,balance,spend_cap,amount_spent,account_status"
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_API}/{META_AD_ACCOUNT_ID}", params={
            "fields": fields,
            "access_token": META_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def meta_list_ad_sets(campaign_id: str) -> list[dict]:
    """List ad sets for a campaign."""
    _require_meta()
    fields = "id,name,status,daily_budget,targeting,start_time,end_time"
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_API}/{campaign_id}/adsets", params={
            "fields": fields,
            "access_token": META_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return resp.json().get("data", [])


@mcp.tool()
def meta_list_ads(ad_set_id: str) -> list[dict]:
    """List ads in an ad set."""
    _require_meta()
    fields = "id,name,status,creative,effective_status"
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{GRAPH_API}/{ad_set_id}/ads", params={
            "fields": fields,
            "access_token": META_ACCESS_TOKEN,
        })
        resp.raise_for_status()
        return resp.json().get("data", [])


# ─── GOOGLE ADS ───────────────────────────────────────────────────────────────

@mcp.tool()
def google_ads_get_campaign_performance(
    start_date: str,
    end_date: str,
) -> list[dict]:
    """
    Get Google Ads campaign performance report.

    Args:
        start_date: YYYY-MM-DD format
        end_date: YYYY-MM-DD format

    Returns:
        List of campaign performance dicts
    """
    if not GOOGLE_ADS_DEVELOPER_TOKEN or not GOOGLE_ADS_CUSTOMER_ID:
        raise EnvironmentError(
            "GOOGLE_ADS_DEVELOPER_TOKEN and GOOGLE_ADS_CUSTOMER_ID must be set."
        )
    # ── STUB ─────────────────────────────────────────────────────────────────
    # Google Ads requires the `google-ads` library + OAuth2 credentials.
    # To implement:
    #   1. pip install google-ads
    #   2. Set GOOGLE_ADS_DEVELOPER_TOKEN and GOOGLE_ADS_CUSTOMER_ID in .env
    #   3. Create a google-ads.yaml with OAuth2 client_id, client_secret, refresh_token
    #   4. Replace this stub with real GoogleAdsClient calls
    # Docs: https://developers.google.com/google-ads/api/docs/client-libs/python
    # See: tools/TOOL_LIBRARY.md — ads.google_ads_get_campaign_performance
    # ─────────────────────────────────────────────────────────────────────────
    raise NotImplementedError(
        "Google Ads not implemented yet. "
        "Needs OAuth2 setup — see tools/TOOL_LIBRARY.md for instructions."
    )


@mcp.tool()
def google_ads_pause_campaign(campaign_id: str) -> dict:
    """Pause a Google Ads campaign.

    Args:
        campaign_id: Google Ads campaign ID to pause

    Returns:
        Confirmation dict

    Raises:
        NotImplementedError: Until OAuth2 setup is complete.
            See tools/TOOL_LIBRARY.md — ads.google_ads_pause_campaign
    """
    # ── STUB ─────────────────────────────────────────────────────────────────
    # See google_ads_get_campaign_performance above for setup instructions.
    # ─────────────────────────────────────────────────────────────────────────
    raise NotImplementedError(
        "Google Ads not implemented yet. "
        "Needs OAuth2 setup — see tools/TOOL_LIBRARY.md for instructions."
    )


# ─── PERFORMANCE SUMMARY ──────────────────────────────────────────────────────

@mcp.tool()
def generate_ads_performance_summary(client_id: str, period: str = "last_7d") -> str:
    """
    Generate a human-readable ads performance summary for a client.

    Args:
        client_id: Client ID (e.g. 'refine-clinic')
        period: Reporting period

    Returns:
        Markdown-formatted performance summary
    """
    try:
        meta_data = {}
        if META_ACCESS_TOKEN and META_AD_ACCOUNT_ID:
            campaigns = meta_list_campaigns("ACTIVE")
            meta_data["active_campaigns"] = len(campaigns)
            meta_data["campaigns"] = campaigns[:3]  # top 3
    except Exception as e:
        meta_data = {"error": str(e)}

    summary = f"""## Ads Performance Summary — {client_id}
**Period:** {period}

### Meta Ads (Facebook/Instagram)
"""
    if "error" in meta_data:
        summary += f"⚠️ Could not fetch data: {meta_data['error']}\n"
    elif "active_campaigns" in meta_data:
        summary += f"- Active campaigns: {meta_data['active_campaigns']}\n"
        for c in meta_data.get("campaigns", []):
            summary += f"- {c.get('name', 'Unknown')} — {c.get('status', '')}\n"
    else:
        summary += "No Meta Ads data available.\n"

    summary += "\n### Google Ads\n- Setup required (OAuth2)\n"
    return summary


if __name__ == "__main__":
    mcp.run()
