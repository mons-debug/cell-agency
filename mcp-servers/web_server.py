"""
Cell Agency — Web MCP Server
Provides: website generation (Next.js scaffolds), page content generation,
          website updates, landing page creation.

Generated code is saved to clients/{id}/web/.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP
import openai

mcp = FastMCP("web")

AGENCY_DIR  = Path.home() / "agency"
CLIENTS_DIR = AGENCY_DIR / "clients"


def _load_brandkit(client_id: str) -> dict:
    kit = CLIENTS_DIR / client_id / "brandkit.json"
    if kit.exists():
        return json.loads(kit.read_text(encoding="utf-8"))
    return {}


def _generate(system: str, user: str, max_tokens: int = 8000) -> str:
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


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ─── WEBSITE GENERATION ──────────────────────────────────────────────────────

@mcp.tool()
def generate_website(
    client_id: str,
    site_type: str = "landing_page",
    pages: str = "home,services,about,contact",
    tech_stack: str = "nextjs",
) -> str:
    """
    Generate a website scaffold for a client.

    Args:
        client_id: Client identifier (e.g. 'refine')
        site_type: Website type: landing_page | portfolio | clinic | restaurant | ecommerce
        pages: Comma-separated page names to generate
        tech_stack: Tech stack: nextjs | html | react

    Returns:
        JSON with generated files list and web/ directory path
    """
    brand = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)
    colors    = brand.get("colors", {})
    fonts     = brand.get("fonts", {})
    services  = brand.get("services", [])
    location  = brand.get("location", {})
    tagline   = brand.get("tagline", {}).get("fr", "")
    instagram = brand.get("social", {}).get("instagram", "")
    phone     = brand.get("contact", {}).get("phone", "")

    web_dir = CLIENTS_DIR / client_id / "web"
    page_list = [p.strip() for p in pages.split(",")]
    generated_files = []

    system = (
        f"You are a senior frontend developer building a {site_type} for {brand_name}. "
        "Write production-quality Next.js 14 App Router code. "
        "Use Tailwind CSS. Mobile-first. SEO optimized. French language by default."
    )

    # Generate tailwind config with brand colors
    tailwind_config = f"""/** @type {{import('tailwindcss').Config}} */
module.exports = {{
  content: ['./src/**/*.{{js,ts,jsx,tsx,mdx}}'],
  theme: {{
    extend: {{
      colors: {{
        primary:   '{colors.get("primary",   "#C9A98A")}',
        secondary: '{colors.get("secondary", "#FAF7F5")}',
        accent:    '{colors.get("accent",    "#8B1A2F")}',
        text:      '{colors.get("text",      "#2C2C2C")}',
      }},
      fontFamily: {{
        heading: ['{fonts.get("heading", "Playfair Display")}', 'serif'],
        body:    ['{fonts.get("body",    "Lato")}',            'sans-serif'],
      }},
    }},
  }},
  plugins: [],
}};
"""
    _write_file(web_dir / "tailwind.config.js", tailwind_config)
    generated_files.append("tailwind.config.js")

    # Generate package.json
    package_json = json.dumps({
        "name": client_id.replace("_", "-"),
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev":   "next dev",
            "build": "next build",
            "start": "next start",
            "lint":  "next lint",
        },
        "dependencies": {
            "next":          "^14.2.0",
            "react":         "^18.3.0",
            "react-dom":     "^18.3.0",
            "tailwindcss":   "^3.4.0",
            "autoprefixer":  "^10.4.0",
            "postcss":       "^8.4.0",
        },
        "devDependencies": {
            "@types/node":  "^20.0.0",
            "@types/react": "^18.3.0",
            "typescript":   "^5.4.0",
        },
    }, indent=2)
    _write_file(web_dir / "package.json", package_json)
    generated_files.append("package.json")

    # Generate layout
    layout_prompt = f"""Create a Next.js 14 App Router layout.tsx for {brand_name}.

Brand: {brand_name}
Tagline: {tagline}
Colors: primary={colors.get("primary","#C9A98A")}, secondary={colors.get("secondary","#FAF7F5")}, accent={colors.get("accent","#8B1A2F")}
Font heading: {fonts.get("heading","Playfair Display")}, body: {fonts.get("body","Lato")}
Instagram: {instagram}

Include:
- Metadata (title, description, OG tags)
- Header with logo placeholder + nav links: {', '.join(page_list)}
- Footer with contact, address ({location.get("city","Tanger")}), social links
- Google Fonts import for {fonts.get("heading","Playfair Display")} and {fonts.get("body","Lato")}
- Responsive mobile menu (hamburger)

Return ONLY the complete layout.tsx code, no explanation."""

    layout_code = _generate(system, layout_prompt)
    _write_file(web_dir / "src" / "app" / "layout.tsx", layout_code)
    generated_files.append("src/app/layout.tsx")

    # Generate each page
    page_contexts = {
        "home":     f"Homepage with hero section, services overview ({', '.join([s.get('name','') for s in services[:3]])}), why choose us, testimonials CTA",
        "services": f"Services page listing all treatments: {json.dumps([s.get('name','') for s in services], ensure_ascii=False)}. Each with description, benefits, pricing placeholder.",
        "about":    f"About page with clinic story, team, values, certifications, location ({location.get('area','Malabata')}, {location.get('city','Tanger')})",
        "contact":  f"Contact page with form (name, phone, service, message), map placeholder, WhatsApp link, hours, address",
        "blog":     "Blog/news page with latest articles grid",
    }

    for page in page_list:
        context = page_contexts.get(page, f"{page} page content")
        page_prompt = f"""Create a Next.js 14 App Router page.tsx for the {page} page of {brand_name}.

Context: {context}
Brand colors: primary={colors.get("primary","#C9A98A")}, accent={colors.get("accent","#8B1A2F")}
Language: French

Requirements:
- Use Tailwind CSS with brand colors (bg-primary, text-accent, etc.)
- Mobile-first responsive design
- Include proper TypeScript types
- SEO: export metadata with French title and description
- Professional medical aesthetic clinic style

Return ONLY the complete page.tsx code."""

        page_code = _generate(system, page_prompt)
        page_path = "src/app/page.tsx" if page == "home" else f"src/app/{page}/page.tsx"
        _write_file(web_dir / page_path, page_code)
        generated_files.append(page_path)

    # Generate globals.css
    globals_css = f"""@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{
  --color-primary:   {colors.get("primary",   "#C9A98A")};
  --color-secondary: {colors.get("secondary", "#FAF7F5")};
  --color-accent:    {colors.get("accent",    "#8B1A2F")};
  --color-text:      {colors.get("text",      "#2C2C2C")};
}}

body {{
  color: var(--color-text);
  background-color: var(--color-secondary);
  font-family: '{fonts.get("body","Lato")}', sans-serif;
}}

h1, h2, h3, h4, h5, h6 {{
  font-family: '{fonts.get("heading","Playfair Display")}', serif;
}}
"""
    _write_file(web_dir / "src" / "app" / "globals.css", globals_css)
    generated_files.append("src/app/globals.css")

    # Generate README
    readme = f"""# {brand_name} — Website

Generated by Cell Agency on {datetime.now().strftime("%Y-%m-%d")}.

## Stack
- Next.js 14 (App Router)
- Tailwind CSS with {brand_name} brand colors
- TypeScript

## Getting Started

```bash
npm install
npm run dev
```

## Pages
{chr(10).join(f'- /{p} — {page_contexts.get(p, p)}' for p in page_list)}

## Deployment
Deploy to Vercel: `npx vercel --prod`
"""
    _write_file(web_dir / "README.md", readme)
    generated_files.append("README.md")

    return json.dumps({
        "status":          "generated",
        "client":          client_id,
        "site_type":       site_type,
        "tech_stack":      tech_stack,
        "web_dir":         str(web_dir),
        "files_generated": generated_files,
        "pages":           page_list,
        "next_steps": [
            f"cd {web_dir}",
            "npm install",
            "npm run dev",
            "Deploy: npx vercel --prod",
        ],
    }, indent=2, ensure_ascii=False)


# ─── UPDATE WEBSITE ──────────────────────────────────────────────────────────

@mcp.tool()
def update_website(
    client_id: str,
    page: str,
    changes: str,
) -> str:
    """
    Update a specific page of an existing generated website.

    Args:
        client_id: Client identifier
        page: Page to update (e.g. 'home', 'services', 'contact')
        changes: Description of what to change (e.g. 'update hero text to mention Ramadan promotion')

    Returns:
        Updated page code + confirmation
    """
    brand = _load_brandkit(client_id)
    brand_name = brand.get("name", client_id)

    page_path_rel = "src/app/page.tsx" if page == "home" else f"src/app/{page}/page.tsx"
    page_file = CLIENTS_DIR / client_id / "web" / page_path_rel

    if not page_file.exists():
        return json.dumps({
            "error": f"Page file not found: {page_file}",
            "suggestion": f"Run generate_website('{client_id}') first",
        })

    existing_code = page_file.read_text(encoding="utf-8")

    system = (
        f"You are a senior frontend developer updating the {brand_name} website. "
        "Modify the provided code according to the requested changes. "
        "Return the complete updated file, not just the changed section."
    )
    prompt = f"""Update this Next.js page for {brand_name}.

Requested changes: {changes}

Current code:
```tsx
{existing_code}
```

Return ONLY the complete updated page.tsx code."""

    updated_code = _generate(system, prompt)
    page_file.write_text(updated_code, encoding="utf-8")

    return json.dumps({
        "status":   "updated",
        "client":   client_id,
        "page":     page,
        "file":     str(page_file),
        "changes":  changes,
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
