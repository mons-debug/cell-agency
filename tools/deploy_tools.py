"""Deploy tools — Vercel and Cloudflare Pages deployment utilities."""
import os
import subprocess
import httpx
from pathlib import Path
from typing import Optional


VERCEL_TOKEN = os.getenv("VERCEL_TOKEN", "")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")


def deploy_to_vercel(project_dir: str, prod: bool = False) -> dict:
    """
    Deploy a project to Vercel using the CLI.

    Args:
        project_dir: Path to the project directory
        prod: If True, deploy to production; otherwise preview

    Returns:
        dict with deployment URL and status
    """
    if not VERCEL_TOKEN:
        raise EnvironmentError("VERCEL_TOKEN not set. Add it to ~/agency/.env")

    project_path = Path(project_dir).expanduser().resolve()
    if not project_path.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    cmd = ["vercel", "--token", VERCEL_TOKEN, "--yes"]
    if prod:
        cmd.append("--prod")

    result = subprocess.run(
        cmd,
        cwd=str(project_path),
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Vercel deploy failed:\n{result.stderr}")

    # Extract URL from output
    lines = result.stdout.strip().splitlines()
    url = next((l for l in lines if l.startswith("https://")), lines[-1] if lines else "")
    return {"url": url, "stdout": result.stdout, "env": "production" if prod else "preview"}


def check_vercel_deployment(deployment_url: str) -> dict:
    """Check if a Vercel deployment URL is live."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(deployment_url)
            return {"url": deployment_url, "status": resp.status_code, "live": resp.status_code < 400}
    except Exception as e:
        return {"url": deployment_url, "status": 0, "live": False, "error": str(e)}


def deploy_to_cloudflare_pages(
    project_name: str,
    directory: str,
    branch: str = "main",
) -> dict:
    """
    Deploy static files to Cloudflare Pages.

    Args:
        project_name: Cloudflare Pages project name
        directory: Local directory containing the built site
        branch: Git branch name (affects preview vs production)

    Returns:
        dict with deployment URL and status
    """
    if not CF_API_TOKEN or not CF_ACCOUNT_ID:
        raise EnvironmentError(
            "CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID must be set."
        )

    cmd = [
        "npx", "wrangler", "pages", "deploy", directory,
        "--project-name", project_name,
        "--branch", branch,
    ]
    env = os.environ.copy()
    env["CLOUDFLARE_API_TOKEN"] = CF_API_TOKEN
    env["CLOUDFLARE_ACCOUNT_ID"] = CF_ACCOUNT_ID

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Cloudflare Pages deploy failed:\n{result.stderr}")

    lines = result.stdout.strip().splitlines()
    url = next((l for l in lines if "pages.dev" in l), "")
    return {"url": url, "stdout": result.stdout}
