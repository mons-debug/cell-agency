---
name: client-registry
description: Manage all agency clients — onboard new clients, look up client info, update records
---

# Client Registry

I manage the complete list of Cell Agency clients and their workspace folders.

## What I Do

- **Onboard new clients** — create folder structure, brand vault template, and initial calendar
- **List all clients** — show who we work with
- **Look up client info** — retrieve brand vault and client details by name
- **Update client records** — modify brand vault, contact info, service agreements

## Trigger Phrases

"add client", "new client", "onboard client", "list clients", "client info", "who are our clients", "client details", "create client folder"

## How I Work

1. Use `agency.list_clients` to show all registered clients
2. Use `agency.create_client` to onboard a new client (creates folder + brand vault template)
3. Use `agency.read_brand_vault` to retrieve client brand information
4. Use `agency.update_brand_vault` to modify client records
5. Log new client onboarding to daily memory via `agency.log_daily`

## Client Folder Structure

Each client gets:
```
clients/{client-id}/
├── brand_vault.md    ← identity, colors, tone, guidelines
├── calendar.md       ← content calendar
├── campaigns/        ← campaign briefs and results
├── assets/           ← images, videos, files
└── reports/          ← performance reports
```

## Rules

- Client ID must be URL-safe (lowercase, hyphens): e.g. `refine-clinic`, `acme-corp`
- Always ask Moncef to confirm before creating a new client
- After onboarding, prompt Moncef to fill in the brand vault details

## Active Clients

- **refine-clinic** — Refine Beauty Clinic, Malabata Tanger, Morocco
