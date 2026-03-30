"""
Cell Agency — Video MCP Server
Provides: reel concept generation, video production briefs,
          video editing specs (stubs for future API integration).

Video generation/editing are stubs — will integrate with Runway/Pika/ffmpeg later.
Reel concept generation is fully functional via Claude.
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

mcp = FastMCP("video")

AGENCY_DIR = Path.home() / "agency"
CLIENTS_DIR = AGENCY_DIR / "clients"


def _load_brandkit(client_id: str) -> dict:
    kit_path = CLIENTS_DIR / client_id / "brandkit.json"
    if kit_path.exists():
        return json.loads(kit_path.read_text(encoding="utf-8"))
    return {}


def _generate(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
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


# ─── REEL CONCEPT GENERATION ─────────────────────────────────────────────────

@mcp.tool()
def generate_reel_concept(
    client_id: str,
    topic: str,
    duration_s: int = 15,
    style: str = "educational",
) -> str:
    """
    Generate a structured Instagram Reel / TikTok concept.

    Args:
        client_id: Client identifier
        topic: Reel topic (e.g. 'botox myths', 'laser process explained')
        duration_s: Target duration in seconds (7, 15, 30, 60)
        style: Video style (educational, behind_the_scenes, before_after, testimonial, trending)

    Returns:
        JSON reel concept with hook, scenes, transitions, CTA, music mood
    """
    brand = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)
    services = brand.get("services", [])
    tone = brand.get("tone_of_voice", {}).get("french", "professional and warm")
    sensitivity = brand.get("sensitivity", [])

    system = (
        f"You are a short-form video strategist for {brand_name}. "
        "You create viral reel concepts optimized for engagement. "
        "Respond in valid JSON."
    )
    prompt = f"""Create a {duration_s}-second reel concept:

Topic: {topic}
Style: {style}
Brand tone: {tone}
Services: {json.dumps(services, ensure_ascii=False)}
Sensitivity rules: {json.dumps(sensitivity, ensure_ascii=False)}

Return JSON with:
- "title": working title
- "hook": first 2 seconds — must stop the scroll (text + visual)
- "scenes": array of scenes, each with:
  - "duration_s": seconds
  - "visual": what's shown
  - "text_overlay": on-screen text (if any)
  - "voiceover": narration (if any)
  - "transition": how to transition to next scene
- "cta": final call to action
- "music_mood": recommended music mood/genre
- "text_style": font style recommendation
- "aspect_ratio": "9:16"
- "estimated_engagement": why this concept should perform well
- "caption_brief": direction for the accompanying caption
- "hashtag_suggestions": 10 relevant hashtags
"""
    return _generate(system, prompt, max_tokens=2500)


# ─── VIDEO GENERATION (STUB) ─────────────────────────────────────────────────

@mcp.tool()
def generate_video(
    concept_json: str,
    output_format: str = "mp4",
) -> str:
    """
    Generate a video from a concept (STUB — returns production brief).

    This tool will integrate with Runway ML, Pika, or similar APIs in the future.
    For now, it returns a detailed production brief that can be used for manual creation.

    Args:
        concept_json: JSON string from generate_reel_concept
        output_format: Output format (mp4, mov)

    Returns:
        Production brief with shot list and technical specs
    """
    try:
        concept = json.loads(concept_json) if isinstance(concept_json, str) else concept_json
    except json.JSONDecodeError:
        concept = {"raw": concept_json}

    return json.dumps({
        "status": "stub",
        "message": "Video generation API not yet integrated. Use this production brief for manual creation.",
        "concept": concept,
        "technical_specs": {
            "format": output_format,
            "resolution": "1080x1920",
            "fps": 30,
            "aspect_ratio": "9:16",
        },
        "next_steps": [
            "Use concept scenes as shot list",
            "Record or source clips matching each scene description",
            "Edit in CapCut, Premiere, or similar",
            "Add text overlays as specified",
            "Add music matching the recommended mood",
        ],
        "future_integration": "Runway ML / Pika / Kling API — coming soon",
    }, indent=2, ensure_ascii=False)


# ─── VIDEO EDITING (STUB) ────────────────────────────────────────────────────

@mcp.tool()
def edit_video(
    input_path: str,
    operations: str,
) -> str:
    """
    Edit a video with specified operations (STUB — returns edit instructions).

    Will integrate with ffmpeg or cloud video APIs in the future.

    Args:
        input_path: Path to source video file
        operations: JSON string of operations, e.g. '[{"op": "trim", "start": 0, "end": 15}]'

    Returns:
        Edit instructions (stub — no actual editing performed)

    Supported operations (future):
        - trim: {"op": "trim", "start": 0, "end": 15}
        - add_text_overlay: {"op": "add_text", "text": "...", "position": "center", "start": 0, "end": 5}
        - add_music: {"op": "add_music", "audio_path": "...", "volume": 0.5}
        - speed_change: {"op": "speed", "factor": 1.5}
        - concat: {"op": "concat", "clips": ["path1", "path2"]}
    """
    try:
        ops = json.loads(operations) if isinstance(operations, str) else operations
    except json.JSONDecodeError:
        ops = [{"raw": operations}]

    return json.dumps({
        "status": "stub",
        "message": "Video editing not yet integrated. Use these instructions for manual editing.",
        "input": input_path,
        "operations": ops,
        "future_integration": "ffmpeg CLI or cloud video editing API — coming soon",
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
