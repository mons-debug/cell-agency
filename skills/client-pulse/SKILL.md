---
name: client-pulse
description: Client relationship management — status updates, satisfaction tracking, communication logs, renewal alerts
---

# Client Pulse

I keep track of client relationships — what's been communicated, how satisfied clients are, and what needs attention.

## What I Do

- **Communication log** — record all client interactions
- **Status updates** — send weekly progress updates to clients via WhatsApp
- **Satisfaction monitoring** — flag when a client hasn't heard from us in too long
- **Renewal alerts** — remind Moncef when contracts are nearing renewal
- **Issue escalation** — flag client complaints or urgent requests

## Trigger Phrases

"client status", "how is refine clinic", "client update", "send update to client", "client communication", "check in with client", "client relationship"

## How I Work

1. Read client records and recent communications
2. Check last contact date
3. Flag if client hasn't received an update in >5 days
4. Draft WhatsApp update message for Moncef's approval
5. Log all communications to `clients/{id}/reports/comms.md`

## Client Health Indicators

| Status | Meaning |
|--------|---------|
| 🟢 Healthy | Regular communication, satisfied, active campaigns |
| 🟡 Attention | No contact in 5–7 days, or minor issue |
| 🔴 Urgent | Complaint, missed deadline, or no contact in 10+ days |

## WhatsApp Update Template (French)

```
Bonjour [Client Name] 👋

Voici votre bilan de la semaine :

✅ [X] publications Instagram publiées
📊 Portée de la semaine : [X] personnes
💬 Meilleur engagement : [top post]

Cette semaine nous préparons :
• [upcoming content]
• [upcoming campaign]

Des questions ? Je suis disponible 😊

— Cell Agency
```

## Communication Rules

- Send client updates via WhatsApp on Monday mornings (after Moncef approves)
- Never contact clients between 10 PM and 8 AM
- Always use French (or Darija if preferred) for Refine Clinic
- Copy Moncef on all client communications (or send for his review first)
