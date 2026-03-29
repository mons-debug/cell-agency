"""Image tools — generation, editing, and conversion."""
import os
import base64
import httpx
from pathlib import Path
from typing import Optional


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FIREFLY_CLIENT_ID = os.getenv("ADOBE_FIREFLY_CLIENT_ID", "")
FIREFLY_CLIENT_SECRET = os.getenv("ADOBE_FIREFLY_CLIENT_SECRET", "")


def generate_image_gemini(
    prompt: str,
    output_path: str,
    aspect_ratio: str = "1:1",
) -> str:
    """
    Generate an image using Google Gemini (Imagen).

    Args:
        prompt: Text description of the image
        output_path: Where to save the image (must be inside ~/agency/clients/)
        aspect_ratio: '1:1' | '9:16' | '16:9' | '4:3'

    Returns:
        Path to the saved image
    """
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY not set. Add it to ~/agency/.env")

    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.ImageGenerationModel("imagen-3.0-generate-002")
    result = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio=aspect_ratio,
    )

    img = result.images[0]
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out))
    return str(out)


def generate_image_firefly(
    prompt: str,
    output_path: str,
    width: int = 1024,
    height: int = 1024,
    style_preset: Optional[str] = None,
) -> str:
    """
    Generate an image using Adobe Firefly API.

    Args:
        prompt: Text description
        output_path: Where to save the image
        width: Image width in pixels
        height: Image height in pixels
        style_preset: Optional style (e.g. 'photo', 'art', 'graphic')

    Returns:
        Path to the saved image
    """
    if not FIREFLY_CLIENT_ID or not FIREFLY_CLIENT_SECRET:
        raise EnvironmentError(
            "ADOBE_FIREFLY_CLIENT_ID and ADOBE_FIREFLY_CLIENT_SECRET not set."
        )

    # Get access token
    token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": FIREFLY_CLIENT_ID,
        "client_secret": FIREFLY_CLIENT_SECRET,
        "scope": "openid,AdobeID,firefly_api",
    }
    with httpx.Client(timeout=15) as client:
        token_resp = client.post(token_url, data=token_data)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

    # Generate image
    ff_url = "https://firefly-api.adobe.io/v3/images/generate"
    payload: dict = {
        "prompt": prompt,
        "size": {"width": width, "height": height},
        "numVariations": 1,
    }
    if style_preset:
        payload["styles"] = [{"presets": [style_preset]}]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": FIREFLY_CLIENT_ID,
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60) as client:
        gen_resp = client.post(ff_url, json=payload, headers=headers)
        gen_resp.raise_for_status()
        result = gen_resp.json()

    # Download and save
    image_url = result["outputs"][0]["image"]["presignedUrl"]
    with httpx.Client(timeout=30) as client:
        img_data = client.get(image_url).content

    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img_data)
    return str(out)


def resize_image(input_path: str, output_path: str, width: int, height: int) -> str:
    """Resize an image using Pillow."""
    from PIL import Image
    img = Image.open(Path(input_path).expanduser())
    resized = img.resize((width, height), Image.LANCZOS)
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    resized.save(str(out))
    return str(out)


def add_watermark(input_path: str, output_path: str, text: str, opacity: int = 128) -> str:
    """Add a text watermark to an image."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(Path(input_path).expanduser()).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size
    draw.text((w - 200, h - 40), text, fill=(255, 255, 255, opacity))
    watermarked = Image.alpha_composite(img, overlay).convert("RGB")
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    watermarked.save(str(out))
    return str(out)


def convert_format(input_path: str, output_path: str) -> str:
    """Convert image between formats (PNG, JPEG, WEBP, etc.)."""
    from PIL import Image
    img = Image.open(Path(input_path).expanduser())
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out))
    return str(out)


def encode_image_base64(path: str) -> str:
    """Encode an image file to base64 string (for API payloads)."""
    return base64.b64encode(Path(path).expanduser().read_bytes()).decode("utf-8")
