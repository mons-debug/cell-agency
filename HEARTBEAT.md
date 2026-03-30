# HEARTBEAT — Cell Agency Scheduled Tasks

> This file is read by OpenClaw periodically (~every 30 minutes).
> I follow this checklist strictly. If nothing needs attention, I reply: HEARTBEAT_OK

## Daily Schedule

### 08:00 — Morning Briefing
Send Moncef a Telegram message with:
1. **Active campaigns:** Current status of any running ad campaigns or scheduled posts
2. **Today's content:** Posts scheduled to publish today (with approval status)
3. **Pending approvals:** Anything waiting for Moncef's ✅
4. **Priorities for today:** Top 3 recommended actions
5. **Any alerts:** Issues, failed tasks, low budgets, API errors

Format: Clean, scannable. Use emojis for status (✅ done, ⏳ pending, ⚠️ attention needed, 🔴 urgent).

### 18:00 — Evening Summary
Send Moncef a brief summary:
1. What was accomplished today
2. What is scheduled for tomorrow
3. Any content awaiting review

### 09:00 Monday — Weekly Agency Report
- Summary of the past week's output (posts published, campaigns active, content created)
- Performance highlights if analytics data available
- Plan for the week ahead
- Any decisions needed from Moncef

### 09:30 Monday — Client Weekly Update (Refine Clinic)
- Generate and send weekly report to Refine Clinic via WhatsApp
- Include: posts published, engagement summary, upcoming content
- Language: French or Arabic (Darija) — check brand_vault.md

## Continuous Monitoring (Every 30 min during working hours)

- Check if any MCP server has crashed → alert Moncef if so
- Check if ChromaDB is accessible → log issue if not
- Check pending approval queue → remind Moncef if item is >2 hours old without response

## Autonomous Planning Schedule

These tasks are executed by the **AutonomyEngine** (`core/autonomy_engine.py`).
To trigger manually: call `run_autonomous_task(schedule_name)` via MCP.

### 08:00 Daily — Autonomous Daily Analysis
- Run `run_autonomous_task("daily")` for all active clients
- Performs: performance snapshot + content gap detection
- Confidence ≥ 0.75 → submitted to approval queue with `trigger_source="autonomous"`
- Confidence < 0.75 → saved as draft in `memory/outputs/`
- Check `list_autonomous_drafts()` to review low-confidence outputs

### 09:00 Monday — Autonomous Weekly Strategy
- Run `run_autonomous_task("weekly")` for all active clients
- Performs: weekly optimization report + content gap recommendations
- High-confidence results go to approval queue for Moncef's review

### 09:00 1st of Month — Campaign Opportunity Detection
- Run `run_autonomous_task("monthly")` for all active clients
- Performs: seasonal + local opportunity detection (Morocco context)
- Always saved as draft (confidence capped at 0.70) — manual review required

### Governance Rules (Autonomous Mode)
- Manual commands ALWAYS override autonomous tasks
- Autonomous outputs NEVER auto-execute — they enter approval queue or drafts only
- Confidence threshold: ≥ 0.75 → approval queue; < 0.75 → drafts

## Important Rules

- Do NOT send messages between 23:00 and 07:00 Morocco time (UTC+1)
- Weekends: Saturday morning briefing only, no Sunday messages unless urgent (🔴)
- If heartbeat task fails, log the error to ~/agency/memory/YYYY-MM-DD.md and alert Moncef once
