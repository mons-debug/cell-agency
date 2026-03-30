"""
Cell Agency — Learning MCP Server
Provides: inspiration search, learning storage/retrieval, daily analysis,
          weekly optimization, content gap detection, campaign opportunities.

Uses ChromaDB for semantic search over learnings + inspiration.
This is the intelligence layer — agents query this before creating content.
"""
import os
import sys
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP
import chromadb
import openai

mcp = FastMCP("learning")

AGENCY_DIR      = Path.home() / "agency"
CLIENTS_DIR     = AGENCY_DIR / "clients"
CHROMA_PATH     = AGENCY_DIR / ".chromadb"
MEMORY_DIR      = AGENCY_DIR / "memory"
LEARNINGS_DIR   = MEMORY_DIR / "learnings"
INSPIRATION_DIR = MEMORY_DIR / "inspiration"
PERFORMANCE_DIR = MEMORY_DIR / "performance"
CAMPAIGNS_DIR   = MEMORY_DIR / "campaigns"

# ─── ChromaDB ─────────────────────────────────────────────────────────────────

_chroma = None

def _db():
    global _chroma
    if _chroma is None:
        CHROMA_PATH.mkdir(exist_ok=True)
        _chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _chroma


def _col(name: str):
    return _db().get_or_create_collection(name)


def _ai(system: str, user: str, max_tokens: int = 2000) -> str:
    resp = openai.OpenAI().chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


def _load_brandkit(client_id: str) -> dict:
    kit = CLIENTS_DIR / client_id / "brandkit.json"
    return json.loads(kit.read_text(encoding="utf-8")) if kit.exists() else {}


# ─── INSPIRATION ─────────────────────────────────────────────────────────────

@mcp.tool()
def find_inspiration(
    query: str,
    platform: str = "instagram",
    industry: str = "beauty",
    limit: int = 5,
) -> str:
    """
    Search for marketing inspiration and store results for future reference.

    Searches web + existing inspiration cache in ChromaDB.

    Args:
        query: What you're looking for (e.g. 'aesthetic clinic instagram reels', 'botox content ideas')
        platform: Target platform (instagram, tiktok, pinterest, behance, general)
        industry: Industry context (beauty, medical, restaurant, fashion)
        limit: Max results to return

    Returns:
        JSON array of inspiration sources with titles, descriptions, and insights
    """
    from web_tools import web_search

    # 1. Check cache first
    cached = []
    try:
        col    = _col("inspiration")
        res    = col.query(query_texts=[query], n_results=min(limit, 3))
        cached = [
            {
                "source":      "cache",
                "title":       res["metadatas"][0][i].get("title", ""),
                "url":         res["metadatas"][0][i].get("url", ""),
                "insight":     res["documents"][0][i],
                "platform":    res["metadatas"][0][i].get("platform", ""),
                "cached_at":   res["metadatas"][0][i].get("saved_at", ""),
            }
            for i in range(len(res["ids"][0]))
        ]
    except Exception:
        pass

    # 2. Web search for fresh inspiration
    search_query = f"{query} {platform} {industry} marketing inspiration 2026"
    fresh = []
    try:
        results = web_search(search_query, n_results=limit)
        for r in results:
            fresh.append({
                "source":   "web",
                "title":    r.get("title", ""),
                "url":      r.get("link", ""),
                "snippet":  r.get("snippet", ""),
                "platform": platform,
            })

            # Store in ChromaDB for future use
            doc_id  = f"insp_{hash(r.get('link', query)) % 100000}"
            insight = f"{r.get('title', '')} — {r.get('snippet', '')}"
            _col("inspiration").upsert(
                ids=[doc_id],
                documents=[insight],
                metadatas=[{
                    "title":    r.get("title", ""),
                    "url":      r.get("link", ""),
                    "platform": platform,
                    "industry": industry,
                    "query":    query,
                    "saved_at": datetime.now().isoformat(),
                }],
            )
    except Exception as e:
        fresh = [{"error": str(e), "note": "Set SERPER_API_KEY for web search"}]

    all_results = (cached + fresh)[:limit]
    return json.dumps(all_results, indent=2, ensure_ascii=False)


# ─── STORE LEARNING ──────────────────────────────────────────────────────────

@mcp.tool()
def store_learning(
    insight: str,
    client_id: str = "",
    source: str = "",
    category: str = "general",
    metric: str = "",
    value: str = "",
) -> str:
    """
    Store a marketing learning/insight in the agency knowledge base.

    Args:
        insight: The learning (e.g. 'Short hooks under 2s get 3x completion rate for refine reels')
        client_id: Client this applies to (empty = agency-wide)
        source: Where this came from (e.g. 'instagram analytics march 2026')
        category: Learning category: content_performance | audience_insight | campaign_result |
                  best_practice | brand_guideline | platform_update
        metric: Metric name if measurable (e.g. 'engagement_rate', 'views')
        value: Metric value (e.g. '9.2%', '210000')

    Returns:
        Confirmation with learning ID
    """
    learning_id = f"learn_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(insight) % 10000}"

    # Store in ChromaDB
    collection_name = f"learnings_{client_id}" if client_id else "learnings"
    _col(collection_name).upsert(
        ids=[learning_id],
        documents=[insight],
        metadatas=[{
            "client_id": client_id,
            "source":    source,
            "category":  category,
            "metric":    metric,
            "value":     value,
            "stored_at": datetime.now().isoformat(),
        }],
    )

    # Also save to filesystem for audit trail
    LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LEARNINGS_DIR / f"{date.today().isoformat()}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "id":        learning_id,
            "insight":   insight,
            "client_id": client_id,
            "source":    source,
            "category":  category,
            "metric":    metric,
            "value":     value,
            "stored_at": datetime.now().isoformat(),
        }, ensure_ascii=False) + "\n")

    return json.dumps({
        "stored":   True,
        "id":       learning_id,
        "category": category,
        "client":   client_id or "agency-wide",
    })


# ─── QUERY LEARNINGS ─────────────────────────────────────────────────────────

@mcp.tool()
def query_learnings(
    query: str,
    client_id: str = "",
    category: str = "",
    limit: int = 5,
) -> str:
    """
    Search stored learnings semantically.

    Call this BEFORE generating any content to leverage past insights.

    Args:
        query: What you want to know (e.g. 'best performing content type', 'what hooks work for reels')
        client_id: Filter by client (empty = search all)
        category: Filter by category (optional)
        limit: Max results

    Returns:
        JSON array of relevant learnings sorted by relevance
    """
    results = []

    # Search client-specific collection first
    collections_to_search = []
    if client_id:
        collections_to_search.append(f"learnings_{client_id}")
    collections_to_search.append("learnings")  # Agency-wide

    for col_name in collections_to_search:
        try:
            col = _db().get_collection(col_name)
            where = {"category": category} if category else None
            res = col.query(
                query_texts=[query],
                n_results=limit,
                where=where,
            )
            for i, doc_id in enumerate(res["ids"][0]):
                meta = res["metadatas"][0][i]
                results.append({
                    "id":        doc_id,
                    "insight":   res["documents"][0][i],
                    "client":    meta.get("client_id", "agency-wide"),
                    "category":  meta.get("category", ""),
                    "metric":    meta.get("metric", ""),
                    "value":     meta.get("value", ""),
                    "source":    meta.get("source", ""),
                    "stored_at": meta.get("stored_at", ""),
                    "relevance": round(1 - res["distances"][0][i], 3),
                })
        except Exception:
            pass

    # Deduplicate by insight text and sort by relevance
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x["relevance"], reverse=True):
        if r["insight"] not in seen:
            seen.add(r["insight"])
            unique.append(r)

    return json.dumps(unique[:limit], indent=2, ensure_ascii=False)


# ─── DAILY ANALYSIS ──────────────────────────────────────────────────────────

@mcp.tool()
def daily_analysis(client_id: str) -> str:
    """
    Run daily performance analysis for a client.

    Pulls available performance data, compares to benchmarks,
    generates insights, and stores learnings.

    Args:
        client_id: Client identifier

    Returns:
        JSON analysis report with insights and action items
    """
    brand      = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)
    today      = date.today().isoformat()

    # Load recent learnings for context
    recent_learnings = []
    try:
        raw = query_learnings("recent performance and content", client_id=client_id, limit=3)
        recent_learnings = json.loads(raw)
    except Exception:
        pass

    # Load recent calendar entries
    calendar_content = ""
    cal_file = CLIENTS_DIR / client_id / "calendar.md"
    if cal_file.exists():
        calendar_content = cal_file.read_text(encoding="utf-8")[-2000:]  # last 2000 chars

    system = (
        f"You are a marketing analyst for {brand_name}. "
        "Generate a concise, actionable daily performance analysis. "
        "Respond in valid JSON."
    )
    prompt = f"""Generate a daily marketing analysis for {brand_name}.

Date: {today}
Recent learnings: {json.dumps(recent_learnings, ensure_ascii=False)}
Calendar context: {calendar_content[:500] if calendar_content else 'No recent calendar data'}

Return JSON with:
- "date": "{today}"
- "client": "{client_id}"
- "summary": 2-sentence overview
- "insights": array of 3-5 key insights
- "content_opportunities": array of 2-3 content ideas for today/tomorrow
- "action_items": array of immediate action items with priority (high/medium/low)
- "performance_notes": observations about recent content performance
- "confidence": 0.0-1.0 (confidence in this analysis given available data)
"""
    analysis = _ai(system, prompt, max_tokens=2000)

    try:
        analysis_data = json.loads(analysis)
    except json.JSONDecodeError:
        analysis_data = {"raw": analysis, "date": today, "client": client_id}

    # Save to performance log
    PERFORMANCE_DIR.mkdir(parents=True, exist_ok=True)
    perf_file = PERFORMANCE_DIR / f"{client_id}_{today}.json"
    perf_file.write_text(json.dumps(analysis_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Auto-store high-value insights as learnings
    if "insights" in analysis_data:
        for insight in analysis_data.get("insights", [])[:2]:
            if isinstance(insight, str) and len(insight) > 20:
                store_learning(
                    insight=insight,
                    client_id=client_id,
                    source=f"daily_analysis_{today}",
                    category="content_performance",
                )

    return json.dumps(analysis_data, indent=2, ensure_ascii=False)


# ─── WEEKLY OPTIMIZATION ─────────────────────────────────────────────────────

@mcp.tool()
def weekly_optimization(client_id: str) -> str:
    """
    Run weekly optimization analysis for a client.

    Aggregates daily analyses from the past week, identifies trends,
    and generates optimization recommendations.

    Args:
        client_id: Client identifier

    Returns:
        JSON weekly optimization report with strategic recommendations
    """
    brand      = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)
    today      = date.today()

    # Load daily analyses from past 7 days
    weekly_data = []
    for i in range(7):
        day = (today - timedelta(days=i)).isoformat()
        perf_file = PERFORMANCE_DIR / f"{client_id}_{day}.json"
        if perf_file.exists():
            try:
                weekly_data.append(json.loads(perf_file.read_text(encoding="utf-8")))
            except Exception:
                pass

    # Load top learnings
    top_learnings = []
    try:
        raw = query_learnings("weekly performance trends and optimization", client_id=client_id, limit=5)
        top_learnings = json.loads(raw)
    except Exception:
        pass

    system = (
        f"You are a senior marketing strategist for {brand_name}. "
        "Generate a weekly optimization report with actionable recommendations. "
        "Respond in valid JSON."
    )
    prompt = f"""Generate a weekly marketing optimization report for {brand_name}.

Week ending: {today.isoformat()}
Daily analyses available: {len(weekly_data)} days
Weekly data summary: {json.dumps(weekly_data[:2], ensure_ascii=False)[:1000] if weekly_data else 'Limited data available'}
Top learnings: {json.dumps(top_learnings, ensure_ascii=False)[:500]}

Return JSON with:
- "week_ending": "{today.isoformat()}"
- "client": "{client_id}"
- "summary": executive summary paragraph
- "top_wins": array of 3 wins from this week
- "top_improvements": array of 3 areas to improve
- "content_strategy_updates": specific strategy changes to implement
- "next_week_priorities": array of 5 priority actions for next week
- "prompt_improvements": suggestions for improving agent prompts
- "tools_to_update": any tools or workflows that should be updated
- "confidence": 0.0-1.0
"""
    report_text = _ai(system, prompt, max_tokens=3000)

    try:
        report_data = json.loads(report_text)
    except json.JSONDecodeError:
        report_data = {"raw": report_text, "week_ending": today.isoformat(), "client": client_id}

    # Save weekly report
    reports_dir = CLIENTS_DIR / client_id / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"weekly_{today.isoformat()}.json"
    report_file.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Store key recommendations as learnings
    for item in report_data.get("content_strategy_updates", [])[:2]:
        if isinstance(item, str) and len(item) > 20:
            store_learning(
                insight=item,
                client_id=client_id,
                source=f"weekly_optimization_{today.isoformat()}",
                category="best_practice",
            )

    return json.dumps(report_data, indent=2, ensure_ascii=False)


# ─── CONTENT GAP DETECTION ───────────────────────────────────────────────────

@mcp.tool()
def detect_content_gaps(client_id: str) -> str:
    """
    Analyze content calendar and past performance to detect content gaps.

    Args:
        client_id: Client identifier

    Returns:
        JSON with detected gaps and content opportunities
    """
    brand    = _load_brandkit(client_id)
    themes   = brand.get("content_themes", [])
    services = brand.get("services", [])

    calendar = ""
    cal_file = CLIENTS_DIR / client_id / "calendar.md"
    if cal_file.exists():
        calendar = cal_file.read_text(encoding="utf-8")[-3000:]

    system = "You are a content strategist. Analyze content coverage and identify gaps. Respond in JSON."
    prompt = f"""Analyze content gaps for {brand.get('name', client_id)}.

Content themes: {json.dumps(themes)}
Services: {json.dumps([s.get('name', '') for s in services], ensure_ascii=False)}
Recent calendar: {calendar[:1000] if calendar else 'No data'}

Return JSON with:
- "underrepresented_themes": themes with little coverage
- "missing_service_content": services with no recent content
- "content_opportunities": array of specific content ideas to fill gaps
- "recommended_next_5_posts": concrete post ideas with topic + format + priority
"""
    result = _ai(system, prompt)
    try:
        return result if result.strip().startswith("{") else json.dumps({"analysis": result})
    except Exception:
        return json.dumps({"analysis": result})


if __name__ == "__main__":
    mcp.run()
