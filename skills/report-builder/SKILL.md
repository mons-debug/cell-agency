---
name: report-builder
description: Generate performance reports for clients and internal use — weekly, monthly, campaign reports
---

# Report Builder

I generate professional performance reports for Cell Agency clients and internal tracking.

## What I Do

- **Weekly client reports** — social media performance summary sent via WhatsApp
- **Monthly reports** — comprehensive marketing performance overview
- **Campaign reports** — pre- and post-campaign analysis
- **Internal agency reports** — weekly Moncef briefing
- **Ad performance reports** — Meta and Google Ads results

## Trigger Phrases

"generate report", "weekly report", "monthly report", "performance report", "client report", "how are we doing", "create report for", "send report"

## How I Work

1. Gather data from all sources:
   - Social: `social.ig_get_account_insights`, `social.ig_get_recent_posts`
   - Ads: `ads.meta_list_campaigns`, `ads.meta_get_campaign_insights`
2. Read previous reports for comparison (via `agency.read_file`)
3. Format report in Markdown
4. Save to `clients/{id}/reports/YYYY-MM-DD_report.md`
5. For client delivery: format as a clean WhatsApp message
6. For Moncef: include all details + recommendations

## Report Template (Weekly Client Report)

```markdown
## Rapport Hebdomadaire — [Client Name]
**Semaine du [DATE] au [DATE]**

### 📱 Réseaux Sociaux
- Posts publiés: X
- Portée totale: X personnes
- Impressions: X
- Nouveaux abonnés: +X
- Meilleur post: [title/link]

### 📢 Publicités
- Campagnes actives: X
- Budget dépensé: X MAD
- Résultats: X leads/clics

### 📈 Tendances
[Key observations]

### 🎯 Plan de la semaine prochaine
[Upcoming content and campaigns]
```

## Delivery

- **Weekly client reports:** WhatsApp (Monday 9:30 AM)
- **Internal reports:** Telegram to Moncef (Monday 9:00 AM)
- **All reports saved:** `clients/{id}/reports/`
