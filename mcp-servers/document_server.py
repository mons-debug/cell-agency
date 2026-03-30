"""
Cell Agency — Document MCP Server
Provides: document generation (proposals, briefs, plans),
          performance report generation, Markdown output.
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP
import openai

mcp = FastMCP("document")

AGENCY_DIR   = Path.home() / "agency"
CLIENTS_DIR  = AGENCY_DIR / "clients"
OUTPUTS_DIR  = AGENCY_DIR / "memory" / "outputs"


def _load_brandkit(client_id: str) -> dict:
    kit = CLIENTS_DIR / client_id / "brandkit.json"
    if kit.exists():
        return json.loads(kit.read_text(encoding="utf-8"))
    return {}


def _generate(system: str, user: str, max_tokens: int = 4000) -> str:
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


def _save_output(client_id: str, doc_type: str, content: str) -> str:
    """Save document to memory/outputs/ and return path."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUTS_DIR / client_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{doc_type}_{ts}.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


# ─── DOCUMENT GENERATION ─────────────────────────────────────────────────────

@mcp.tool()
def generate_document(
    client_id: str,
    doc_type: str,
    title: str,
    sections: str = "",
    language: str = "fr",
) -> str:
    """
    Generate a structured document for a client.

    Args:
        client_id: Client identifier (e.g. 'refine')
        doc_type: Document type: proposal | brief | report | plan | strategy | onboarding
        title: Document title
        sections: Comma-separated section names to include (optional)
        language: Language code (fr, en, ar)

    Returns:
        Markdown document content + saved file path
    """
    brand = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)
    lang_map = {"fr": "French", "en": "English", "ar": "Arabic"}
    lang_name = lang_map.get(language, language)

    section_hint = f"\nInclude these sections: {sections}" if sections else ""
    today = date.today().isoformat()

    system = (
        f"You are a professional business writer for {brand_name}. "
        f"Write in {lang_name}. Be thorough, professional, and actionable."
    )

    doc_templates = {
        "proposal":   "marketing proposal with executive summary, objectives, strategy, timeline, budget, and ROI projection",
        "brief":      "creative brief with background, goals, target audience, key messages, deliverables, and timeline",
        "report":     "performance report with executive summary, metrics, analysis, insights, and recommendations",
        "plan":       "project plan with objectives, phases, tasks, timeline, resources, and KPIs",
        "strategy":   "marketing strategy with situation analysis, goals, tactics, channels, budget, and measurement",
        "onboarding": "client onboarding document with welcome, workflow, contacts, tools, timelines, and next steps",
    }
    template = doc_templates.get(doc_type, f"{doc_type} document")

    prompt = f"""Create a {template} for {brand_name}.

Title: {title}
Date: {today}{section_hint}

Brand context:
- Industry: {brand.get('industry', 'unknown')}
- Location: {json.dumps(brand.get('location', {}), ensure_ascii=False)}
- Services: {json.dumps(brand.get('services', []), ensure_ascii=False)}

Format as professional Markdown with clear headings, bullet points where appropriate, and a clean structure.
"""
    content = _generate(system, prompt)
    saved_path = _save_output(client_id, doc_type, content)

    return json.dumps({
        "content": content,
        "saved_to": saved_path,
        "client": client_id,
        "doc_type": doc_type,
        "title": title,
    }, ensure_ascii=False, indent=2)


# ─── REPORT GENERATION ───────────────────────────────────────────────────────

@mcp.tool()
def generate_report(
    client_id: str,
    report_type: str,
    period: str,
    data_json: str = "{}",
) -> str:
    """
    Generate a performance report for a client.

    Args:
        client_id: Client identifier
        report_type: Report type: weekly | monthly | campaign | annual | social | ads
        period: Reporting period (e.g. 'March 2026', 'Week 13 2026', 'Q1 2026')
        data_json: JSON string with performance data to include in the report

    Returns:
        Markdown report content + saved file path
    """
    brand = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)

    try:
        data = json.loads(data_json) if data_json.strip() != "{}" else {}
    except json.JSONDecodeError:
        data = {}

    data_section = ""
    if data:
        data_section = f"\n\nPerformance data provided:\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```"

    system = (
        f"You are a data analyst and marketing strategist for {brand_name}. "
        "Create clear, insightful performance reports with actionable recommendations. "
        "Use French as the primary language."
    )

    report_templates = {
        "weekly":   "weekly social media and marketing performance report",
        "monthly":  "monthly comprehensive marketing performance report",
        "campaign": "campaign performance analysis report",
        "annual":   "annual marketing review and planning report",
        "social":   "social media analytics report",
        "ads":      "paid advertising performance report",
    }
    template = report_templates.get(report_type, f"{report_type} report")

    prompt = f"""Create a {template} for {brand_name}.

Period: {period}
Report type: {report_type}{data_section}

Structure the report with:
1. Executive Summary (3-5 bullet points)
2. Key Metrics Overview (table format)
3. Channel Performance (Instagram, Facebook, Ads if applicable)
4. Top Performing Content
5. Audience Insights
6. What Worked / What Didn't
7. Recommendations for Next Period
8. Next Steps & Action Items

Be specific, data-driven where data is provided, and highlight wins and opportunities.
"""
    content = _generate(system, prompt)
    saved_path = _save_output(client_id, f"report_{report_type}", content)

    return json.dumps({
        "content": content,
        "saved_to": saved_path,
        "client": client_id,
        "report_type": report_type,
        "period": period,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def convert_pdf_to_images(
    pdf_path: str,
    client_id: str,
    output_dir: Optional[str] = None,
    format: str = "PNG",
) -> str:
    """
    Convert a PDF file into images (one per page).

    Args:
        pdf_path: Path to the source PDF
        client_id: Client identifier
        output_dir: Optional subfolder in client's assets (defaults to 'images')
        format: 'PNG' | 'JPEG'
    """
    from pdf2image import convert_from_path
    
    source = Path(pdf_path).expanduser()
    if not source.is_absolute():
        source = AGENCY_DIR / pdf_path
        
    if not source.exists():
        return f"Error: PDF not found at {source}"

    target_root = CLIENTS_DIR / client_id / (output_dir or "images")
    target_root.mkdir(parents=True, exist_ok=True)
    
    # Ensure poppler_path is set if needed on Mac (usually in /usr/local/bin or /opt/homebrew/bin)
    # pdf2image usually finds it in PATH if installed via brew.
    images = convert_from_path(str(source))
    saved_paths = []
    
    for i, image in enumerate(images):
        fname = f"{source.stem}_page_{i+1}.{format.lower()}"
        out_path = target_root / fname
        image.save(str(out_path), format)
        saved_paths.append(str(out_path))
        
    return json.dumps({
        "message": f"Converted {len(images)} pages from {source.name}",
        "saved_paths": saved_paths,
        "format": format
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
