# MEMORY — Cell Agency Persistent Memory

> This file is never deleted. It contains critical facts I must always remember.
> Updated by Nadia as important decisions are made.

## Agency Status

- **Agency name:** Cell
- **Launch date:** 2026 (newly operational)
- **Owner:** Moncef
- **Director:** Nadia (me)
- **Stack:** OpenClaw + CrewAI + FastMCP + ChromaDB + Claude API
- **Workspace:** ~/agency/

## Active Clients

### Refine Beauty Clinic
- **Type:** Beauty clinic / aesthetics
- **Location:** Malabata, Tanger, Morocco
- **Primary contact:** Via WhatsApp Business
- **Services:** Laser hair removal, skin treatments, aesthetics
- **Target audience:** Moroccan women, 25–45, Tanger area
- **Social channels:** Instagram (primary), Facebook
- **Brand language:** French + Arabic (Darija)
- **Brand vault:** ~/agency/clients/refine-clinic/brand_vault.md
- **Status:** Active — onboarding complete

## Key Decisions Made

- Agency uses API-based AI models only (no local LLMs — Intel Mac 16GB RAM constraint)
- Telegram is owner interface; WhatsApp is client interface
- All client file writes restricted to ~/agency/clients/ directory
- Approval required before any client-facing publishing or ad spend

## System Notes

- Python environment: managed by uv, pyproject.toml at ~/agency/pyproject.toml
- MCP servers: 4 servers (agency, social, ads, design) running via stdio
- ChromaDB: persistent client, collections per client
- Skills directory: ~/agency/skills/ (hot-reloaded by OpenClaw)

## Things to Remember

- Moncef speaks Darija/French/Arabic for client-facing content
- Refine Clinic's brand colors are to be confirmed — check brand_vault.md
- Always log daily activity in ~/agency/memory/YYYY-MM-DD.md
