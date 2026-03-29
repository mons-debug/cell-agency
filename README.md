# Cell Agency — AI Digital Marketing Agency

**Owner:** Moncef
**Director:** Nadia (AI)
**Stack:** OpenClaw + CrewAI + FastMCP + ChromaDB + Claude API
**Interface:** Telegram bot → OpenClaw gateway

---

## Setup Guide — Run This Once

### Step 1 — Install Python 3.11

Your system Python (3.9.6) is too old. Install 3.11 via pyenv:

```bash
brew install pyenv
pyenv install 3.11.9
pyenv global 3.11.9

# Add to ~/.zshrc:
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Reload shell:
source ~/.zshrc
python3 --version  # should show 3.11.9
```

### Step 2 — Install uv (fast Python package manager)

```bash
pip install uv
```

### Step 3 — Install Python dependencies

```bash
cd ~/agency
uv sync
```

### Step 4 — Install OpenClaw

```bash
npm install -g openclaw
openclaw --version  # verify install
```

### Step 5 — Set up your API keys

```bash
cp ~/agency/.env.example ~/agency/.env
# Edit .env and fill in your keys:
nano ~/agency/.env
```

**Required keys to add right now:**
- `ANTHROPIC_API_KEY` — from https://console.anthropic.com
- `TELEGRAM_BOT_TOKEN` — create a bot via @BotFather on Telegram
- `TELEGRAM_OWNER_ID` — your Telegram user ID (message @userinfobot to find it)

### Step 6 — Update OpenClaw config with your Telegram ID

Edit `~/.openclaw/openclaw.json` and update the allowlist with your Telegram user ID (from step 5).

### Step 7 — Update the launchd service with your API keys

Edit the plist file before loading it:
```bash
nano ~/Library/LaunchAgents/com.cell.agency.plist
# Replace REPLACE_WITH_YOUR_KEY placeholders with actual values
```

### Step 8 — Test the gateway manually first

```bash
cd ~/agency
ANTHROPIC_API_KEY=your_key TELEGRAM_BOT_TOKEN=your_token TELEGRAM_OWNER_ID=your_id \
  openclaw gateway --verbose
```

Send `/hello` to your Telegram bot — Nadia should respond.

### Step 9 — Enable auto-start on login (after testing works)

```bash
launchctl load ~/Library/LaunchAgents/com.cell.agency.plist
launchctl start com.cell.agency
```

To check if it's running:
```bash
launchctl list | grep cell.agency
tail -f ~/agency/logs/gateway.log
```

To stop it:
```bash
launchctl stop com.cell.agency
launchctl unload ~/Library/LaunchAgents/com.cell.agency.plist
```

---

## What Was Built

### Directory Structure

```
~/agency/
├── SOUL.md               ← Nadia's identity and agency values
├── USER.md               ← Moncef's profile and preferences
├── MEMORY.md             ← Persistent agency memory
├── HEARTBEAT.md          ← Scheduled daily/weekly tasks
├── pyproject.toml        ← Python dependencies (uv)
├── .env                  ← Your API keys (never commit this)
├── .env.example          ← Template for .env
│
├── skills/               ← 12 OpenClaw skills (hot-reloaded)
│   ├── client-registry/SKILL.md
│   ├── brand-vault/SKILL.md
│   ├── calendar-brain/SKILL.md
│   ├── content-forge/SKILL.md
│   ├── social-pilot/SKILL.md
│   ├── ads-cockpit/SKILL.md
│   ├── seo-radar/SKILL.md
│   ├── report-builder/SKILL.md
│   ├── email-engine/SKILL.md
│   ├── design-brief/SKILL.md
│   ├── lead-hunter/SKILL.md
│   └── client-pulse/SKILL.md
│
├── mcp-servers/          ← 4 FastMCP servers (~77 tools)
│   ├── agency_server.py  ← Files, ChromaDB, search, registry
│   ├── social_server.py  ← Instagram, Facebook publishing
│   ├── ads_server.py     ← Meta Ads, Google Ads
│   └── design_server.py  ← Image generation, design tools
│
├── tools/                ← Python utilities used by MCP servers
│   ├── file_tools.py
│   ├── web_tools.py
│   ├── image_tools.py
│   └── deploy_tools.py
│
├── crews/                ← 22 CrewAI agent definitions (YAML)
│   ├── management_crew.yaml    ← Nadia, Router, QA Gate
│   ├── strategy_crew.yaml      ← Research, Strategy, SEO, Audience
│   ├── creative_crew.yaml      ← Content, Brand, Graphic, Video
│   ├── dev_crew.yaml           ← Frontend, Backend, DevOps, Tools
│   └── marketing_ops_crew.yaml ← Ads, Social, Analytics, Client, Email, Leads, Reports
│
├── clients/
│   └── refine-clinic/    ← First client
│       ├── brand_vault.md
│       ├── calendar.md
│       ├── campaigns/
│       ├── assets/
│       └── reports/
│
└── logs/                 ← Gateway logs
```

### Config Files

- `~/.openclaw/openclaw.json` — OpenClaw gateway configuration
- `~/Library/LaunchAgents/com.cell.agency.plist` — Mac auto-start service

---

## Daily Usage

Once the gateway is running, control everything via Telegram:

| Command / Message | What Nadia Does |
|------------------|----------------|
| `/briefing` | Morning briefing — campaign status, today's tasks |
| `write instagram post for refine clinic about [topic]` | Creates caption draft |
| `generate image for refine clinic — [description]` | Creates social graphic |
| `show me refine clinic calendar` | Shows upcoming content |
| `how are the ads doing?` | Meta Ads performance summary |
| `create weekly report for refine clinic` | Generates weekly report |
| `add new client [name]` | Onboards a new client |
| `what's pending my approval?` | Shows items waiting for ✅ |

Send ✅ to approve any pending content or campaign before it goes live.

---

## Phase Roadmap

| Phase | Status | What It Unlocks |
|-------|--------|----------------|
| 1 — Foundation | ✅ Files ready → install & configure | OpenClaw live, Telegram connected |
| 2 — Core Skills | ✅ Files ready | Morning briefings, client registry, calendar |
| 3 — MCP + Tools | ✅ Files ready | Agents can use tools, web search active |
| 4 — Social Pipeline | 🔑 Needs Meta API keys | Instagram/Facebook publishing |
| 5 — Paid Ads | 🔑 Needs Meta Ads access | Ad campaign management |
| 6 — Design Gen | 🔑 Needs Gemini/Firefly keys | AI image generation |
| 7 — Automation | After above phases | Fully autonomous daily operations |

---

## Refine Clinic Quick Notes

- **Brand vault:** `~/agency/clients/refine-clinic/brand_vault.md`
  → ⚠️ Colors and logo are placeholders — fill in real values
- **Content calendar:** `~/agency/clients/refine-clinic/calendar.md`
- **Instagram handle:** `@refineclinic.tanger` (confirm with Moncef)
- **Target:** Women 25–45, Tanger — French + Darija content

---

## Logs & Monitoring

```bash
# Watch gateway live logs
tail -f ~/agency/logs/gateway.log

# Check for errors
tail -f ~/agency/logs/gateway.err

# Today's activity log
cat ~/agency/memory/$(date +%Y-%m-%d).md

# Test MCP server directly
python3 ~/agency/mcp-servers/agency_server.py

# Verify ChromaDB
python3 -c "import chromadb; c=chromadb.PersistentClient(path='$HOME/agency/.chromadb'); print('Collections:', c.list_collections())"
```

---

## Troubleshooting

**Gateway won't start:**
```bash
openclaw doctor       # built-in diagnostics
openclaw --version    # verify version ≥ 2026.x
```

**Telegram bot not responding:**
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check your user ID is in the allowlist in `~/.openclaw/openclaw.json`
- Check `~/agency/logs/gateway.log` for errors

**MCP server errors:**
```bash
# Test a server manually
cd ~/agency
python3 mcp-servers/agency_server.py
# Should start without error (ctrl+C to stop)
```

**Python import errors:**
```bash
cd ~/agency
uv sync       # reinstall all dependencies
python3 -c "import fastmcp; print('OK')"
```
