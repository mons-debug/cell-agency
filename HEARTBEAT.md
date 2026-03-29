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

## Important Rules

- Do NOT send messages between 23:00 and 07:00 Morocco time (UTC+1)
- Weekends: Saturday morning briefing only, no Sunday messages unless urgent (🔴)
- If heartbeat task fails, log the error to ~/agency/memory/YYYY-MM-DD.md and alert Moncef once
