"""
Cell Agency — Design MCP Server
Provides: image generation (Gemini/Firefly), image editing,
          social graphic creation, design brief parsing.
"""
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP
from image_tools import (
    generate_image_gemini,
    generate_image_firefly,
    resize_image,
    add_watermark,
    convert_format,
    encode_image_base64,
)

mcp = FastMCP("design")

CLIENTS_DIR = Path.home() / "agency" / "clients"

# Social media standard dimensions
SOCIAL_SIZES = {
    "instagram_square": (1080, 1080),
    "instagram_portrait": (1080, 1350),
    "instagram_landscape": (1080, 566),
    "instagram_story": (1080, 1920),
    "facebook_post": (1200, 630),
    "facebook_story": (1080, 1920),
    "twitter_post": (1200, 675),
}


# ─── IMAGE GENERATION ─────────────────────────────────────────────────────────

@mcp.tool()
def generate_social_image(
    client_id: str,
    prompt: str,
    format: str = "instagram_square",
    engine: str = "gemini",
    filename: Optional[str] = None,
) -> str:
    """
    Generate a social media image for a client.

    Args:
        client_id: Client ID (e.g. 'refine-clinic')
        prompt: Detailed image description
        format: 'instagram_square' | 'instagram_portrait' | 'instagram_story' |
                'facebook_post' | 'instagram_landscape'
        engine: 'gemini' | 'firefly'
        filename: Optional filename (auto-generated if not provided)

    Returns:
        Path to the generated image
    """
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = filename or f"{format}_{ts}.png"
    output_path = str(CLIENTS_DIR / client_id / "assets" / fname)

    if engine == "firefly":
        size = SOCIAL_SIZES.get(format, (1080, 1080))
        return generate_image_firefly(prompt, output_path, width=size[0], height=size[1])
    else:
        # Map format to Gemini aspect ratio
        aspect_map = {
            "instagram_square": "1:1",
            "instagram_portrait": "4:5",
            "instagram_landscape": "1.91:1",
            "instagram_story": "9:16",
            "facebook_post": "1.91:1",
            "facebook_story": "9:16",
            "twitter_post": "16:9",
        }
        aspect = aspect_map.get(format, "1:1")
        return generate_image_gemini(prompt, output_path, aspect_ratio=aspect)


@mcp.tool()
def generate_logo_concept(
    client_id: str,
    brand_name: str,
    style: str = "modern minimal",
    colors: str = "",
) -> str:
    """
    Generate a logo concept image for a client.

    Args:
        client_id: Client ID
        brand_name: Brand/business name
        style: Style description (e.g. 'modern minimal', 'luxury', 'playful')
        colors: Color guidance (e.g. 'teal and white', 'rose gold')

    Returns:
        Path to the generated logo concept image
    """
    color_hint = f", color palette: {colors}" if colors else ""
    prompt = (
        f"Professional logo design concept for '{brand_name}', {style} style{color_hint}. "
        "Clean vector-style logo on white background. High quality, no text unless part of logo."
    )
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = str(CLIENTS_DIR / client_id / "assets" / f"logo_concept_{ts}.png")
    return generate_image_gemini(prompt, output_path, aspect_ratio="1:1")


@mcp.tool()
def generate_ad_creative(
    client_id: str,
    headline: str,
    background_style: str,
    product_description: str,
    format: str = "instagram_square",
) -> str:
    """
    Generate an ad creative image.

    Args:
        client_id: Client ID
        headline: Ad headline text (will guide visual)
        background_style: Background style (e.g. 'soft pink gradient', 'dark luxury')
        product_description: What the ad is promoting
        format: Social media format

    Returns:
        Path to the generated ad creative
    """
    prompt = (
        f"Professional digital advertisement visual. "
        f"Product/service: {product_description}. "
        f"Mood and background: {background_style}. "
        f"Marketing headline concept: '{headline}'. "
        f"Clean, modern, high-end aesthetic. No text overlays."
    )
    return generate_social_image(client_id, prompt, format=format)


@mcp.tool()
def resize_for_platform(
    input_path: str,
    client_id: str,
    formats: list[str],
) -> dict[str, str]:
    """
    Resize a source image for multiple social media formats.

    Args:
        input_path: Source image path
        client_id: Client ID (output goes to their assets/)
        formats: List of format names from SOCIAL_SIZES

    Returns:
        Dict mapping format → output path
    """
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {}
    for fmt in formats:
        if fmt not in SOCIAL_SIZES:
            results[fmt] = f"Unknown format: {fmt}"
            continue
        w, h = SOCIAL_SIZES[fmt]
        out = str(CLIENTS_DIR / client_id / "assets" / f"{fmt}_{ts}.png")
        results[fmt] = resize_image(input_path, out, w, h)
    return results


@mcp.tool()
def add_brand_watermark(
    input_path: str,
    output_path: str,
    brand_name: str,
) -> str:
    """Add a subtle brand name watermark to an image."""
    return add_watermark(input_path, output_path, brand_name)


@mcp.tool()
def parse_design_brief(brief_text: str) -> dict:
    """
    Parse a design brief text into structured fields.

    Returns dict with: format, style, colors, copy, dimensions, notes
    """
    # This returns a structured prompt for the content/design agent to fill
    return {
        "raw_brief": brief_text,
        "parsed": {
            "format": "to be determined from brief",
            "style": "to be determined from brief",
            "colors": "to be determined from brief",
            "copy": "to be determined from brief",
            "dimensions": "to be determined from brief",
            "notes": "Full parsing requires Claude agent analysis of the brief text",
        },
        "instruction": (
            "Pass this brief to the Brand Designer agent for full creative direction, "
            "then to Graphic Designer for execution."
        ),
    }


@mcp.tool()
def list_client_assets(client_id: str, pattern: str = "*.png") -> list[str]:
    """List design assets for a client."""
    assets_dir = CLIENTS_DIR / client_id / "assets"
    if not assets_dir.exists():
        return []
    return [str(f.name) for f in assets_dir.glob(pattern)]


@mcp.tool()
def get_social_sizes() -> dict:
    """Return all supported social media image dimensions."""
    return {k: {"width": v[0], "height": v[1]} for k, v in SOCIAL_SIZES.items()}


if __name__ == "__main__":
    mcp.run()
