"""
Cell Agency — Content MCP Server
Provides: content strategy generation, caption writing, content planning,
          article generation, ad copy creation.

All content is generated via Claude (Anthropic SDK).
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP
import openai

mcp = FastMCP("content")

AGENCY_DIR = Path.home() / "agency"
CLIENTS_DIR = AGENCY_DIR / "clients"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_brandkit(client_id: str) -> dict:
    """Load a client's brandkit.json, returns empty dict if not found."""
    kit_path = CLIENTS_DIR / client_id / "brandkit.json"
    if kit_path.exists():
        return json.loads(kit_path.read_text(encoding="utf-8"))
    return {}


def _generate(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Generate text via OpenAI."""
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# ─── CONTENT STRATEGY ────────────────────────────────────────────────────────

@mcp.tool()
def generate_content_strategy(
    client_id: str,
    goal: str,
    duration_weeks: int = 4,
    platforms: str = "instagram",
) -> str:
    """
    Generate a content strategy for a client.

    Args:
        client_id: Client identifier (e.g. 'refine')
        goal: Marketing goal (e.g. 'increase bookings', 'grow followers')
        duration_weeks: Strategy duration in weeks
        platforms: Comma-separated platforms (e.g. 'instagram,facebook')

    Returns:
        JSON content strategy with themes, posting frequency, content mix
    """
    brand = _load_brandkit(client_id)
    brand_context = ""
    if brand:
        brand_context = f"""
Client: {brand.get('name', client_id)}
Industry: {brand.get('industry', 'unknown')}
Location: {json.dumps(brand.get('location', {}))}
Audience: {json.dumps(brand.get('audience', {}), ensure_ascii=False)}
Tone: {json.dumps(brand.get('tone_of_voice', {}), ensure_ascii=False)}
Services: {json.dumps(brand.get('services', []), ensure_ascii=False)}
Content themes: {json.dumps(brand.get('content_themes', []))}
Languages: {json.dumps(brand.get('languages', ['fr']))}
"""

    system = (
        "You are a digital marketing strategist for a Moroccan marketing agency. "
        "You create practical, actionable content strategies. "
        "Always respond in valid JSON format."
    )
    prompt = f"""Create a {duration_weeks}-week content strategy for this client:

{brand_context}

Goal: {goal}
Platforms: {platforms}

Return a JSON object with:
- "overview": brief strategy summary
- "weekly_themes": array of {duration_weeks} weekly themes
- "content_mix": percentage split by content type (educational, promotional, engagement, behind_the_scenes)
- "posting_frequency": posts per week per platform
- "key_messages": top 5 messages to communicate
- "hashtag_strategy": recommended hashtag groups
- "kpis": measurable success metrics
"""
    return _generate(system, prompt, max_tokens=3000)


# ─── CAPTION GENERATION ──────────────────────────────────────────────────────

@mcp.tool()
def generate_caption(
    client_id: str,
    topic: str,
    platform: str = "instagram",
    language: str = "fr",
    tone: str = "",
) -> str:
    """
    Generate a social media caption for a client.

    Args:
        client_id: Client identifier
        topic: Caption topic (e.g. 'laser hair removal benefits')
        platform: Target platform (instagram, facebook, tiktok)
        language: Language code (fr, ar, darija, en)
        tone: Optional tone override (defaults to brand tone)

    Returns:
        Complete caption with hook, body, CTA, and hashtags
    """
    brand = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)
    brand_tone = tone or brand.get("tone_of_voice", {}).get("french", "professional and warm")
    services = brand.get("services", [])
    hashtags = brand.get("posting", {}).get("hashtags", {})

    lang_map = {"fr": "French", "ar": "Arabic", "darija": "Moroccan Darija", "en": "English"}
    lang_name = lang_map.get(language, language)

    system = (
        f"You are a social media copywriter for {brand_name}. "
        f"Write in {lang_name}. Tone: {brand_tone}. "
        f"Platform: {platform}."
    )
    prompt = f"""Write a {platform} caption about: {topic}

Client services: {json.dumps(services, ensure_ascii=False)}
Existing hashtags: {json.dumps(hashtags, ensure_ascii=False)}

Structure:
1. HOOK — attention-grabbing first line
2. BODY — 2-3 sentences with value
3. CTA — clear call to action
4. HASHTAGS — 15-20 relevant hashtags mixing brand, topic, and local tags

Return the complete caption ready to post."""
    return _generate(system, prompt)


# ─── CONTENT PLAN ────────────────────────────────────────────────────────────

@mcp.tool()
def create_content_plan(
    client_id: str,
    weeks: int = 2,
    themes: str = "",
) -> str:
    """
    Create a detailed multi-week content plan with specific post ideas.

    Args:
        client_id: Client identifier
        weeks: Number of weeks to plan
        themes: Comma-separated themes to focus on (optional)

    Returns:
        JSON content plan with daily post ideas, formats, and topics
    """
    brand = _load_brandkit(client_id)
    brand_context = ""
    if brand:
        brand_context = f"""
Client: {brand.get('name', client_id)}
Services: {json.dumps(brand.get('services', []), ensure_ascii=False)}
Content themes: {json.dumps(brand.get('content_themes', []))}
Posting frequency: {brand.get('posting', {}).get('frequency', '4-5 posts/week')}
Best times: {json.dumps(brand.get('posting', {}).get('best_times', []))}
Languages: {json.dumps(brand.get('languages', ['fr']))}
"""

    theme_hint = f"\nFocus themes: {themes}" if themes else ""

    system = (
        "You are a content planner for a Moroccan marketing agency. "
        "Create detailed, practical content plans. Respond in valid JSON."
    )
    prompt = f"""Create a {weeks}-week content plan:

{brand_context}{theme_hint}

Return JSON with:
- "plan": array of weeks, each containing:
  - "week": week number
  - "theme": weekly theme
  - "posts": array of posts, each with:
    - "day": day name
    - "type": feed_post | story | reel | carousel
    - "topic": specific topic
    - "format": instagram_square | instagram_portrait | instagram_story | reel
    - "language": fr | ar | darija
    - "caption_brief": 1-sentence caption direction
    - "visual_brief": 1-sentence visual direction
"""
    return _generate(system, prompt, max_tokens=4000)


# ─── ARTICLE GENERATION ──────────────────────────────────────────────────────

@mcp.tool()
def generate_article(
    client_id: str,
    topic: str,
    word_count: int = 800,
    language: str = "fr",
) -> str:
    """
    Generate a long-form article or blog post for a client.

    Args:
        client_id: Client identifier
        topic: Article topic
        word_count: Target word count
        language: Language code

    Returns:
        Complete article in Markdown format
    """
    brand = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)
    brand_tone = brand.get("tone_of_voice", {}).get("french", "professional")
    sensitivity = brand.get("sensitivity", [])

    lang_map = {"fr": "French", "ar": "Arabic", "darija": "Moroccan Darija", "en": "English"}
    lang_name = lang_map.get(language, language)

    system = (
        f"You are a content writer for {brand_name}. "
        f"Write in {lang_name}. Tone: {brand_tone}. "
        f"Sensitivity rules: {json.dumps(sensitivity, ensure_ascii=False)}"
    )
    prompt = f"""Write a {word_count}-word article about: {topic}

Format as Markdown with:
- Engaging title (H1)
- Introduction
- 3-5 sections with H2 headings
- Conclusion with CTA
- SEO-friendly structure

The article should be informative, engaging, and aligned with the brand voice."""
    return _generate(system, prompt, max_tokens=max(word_count * 2, 2000))


# ─── AD COPY ─────────────────────────────────────────────────────────────────

@mcp.tool()
def generate_ad_copy(
    client_id: str,
    campaign_goal: str,
    offer: str,
    language: str = "fr",
) -> str:
    """
    Generate ad copy variations for paid campaigns.

    Args:
        client_id: Client identifier
        campaign_goal: What the ad should achieve (bookings, awareness, traffic)
        offer: The specific offer or message
        language: Language code

    Returns:
        JSON with multiple ad copy variations (headlines, descriptions, CTAs)
    """
    brand = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)

    lang_map = {"fr": "French", "ar": "Arabic", "en": "English"}
    lang_name = lang_map.get(language, language)

    system = (
        f"You are an ad copywriter for {brand_name}. "
        f"Write in {lang_name}. Create compelling, concise ad copy. "
        "Respond in valid JSON."
    )
    prompt = f"""Create ad copy for:
Campaign goal: {campaign_goal}
Offer: {offer}

Return JSON with:
- "variations": array of 3 copy variations, each with:
  - "headline": max 40 characters
  - "primary_text": main ad body (max 125 chars for feed)
  - "description": supporting text
  - "cta": call to action button text
  - "long_copy": expanded version for story/feed ads
"""
    return _generate(system, prompt)


if __name__ == "__main__":
    mcp.run()
