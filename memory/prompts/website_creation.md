# Prompt Template: Website Creation Workflow

## Trigger Phrases
- "build website", "create website", "make website", "landing page for"

## Workflow Steps

### Step 1 — Strategy Agent (Site Strategy)
```
TASK: Website Strategy
CLIENT: {client_id}
SITE_TYPE: {site_type}
PAGES: {pages}

1. Read brandkit (colors, fonts, tone, services, audience)
2. find_inspiration("{industry} website design {site_type}")
3. query_learnings("website best practices {industry}")

Define:
- Page structure and hierarchy
- Key messages per page
- SEO keywords (French + Arabic)
- Conversion goals per page
- User journey mapping
```

### Step 2 — Design Agent (Brand Assets)
```
TASK: Website Brand Preparation
CLIENT: {client_id}

1. list_assets(client_id, "image") — inventory available images
2. choose_best_assets(client_id, "website hero, professional, clinic")
3. If needed: generate_social_image for hero, services banners

Output: list of assets ready for web use
```

### Step 3 — Web Server (Generate Site)
```
TASK: Website Generation
CLIENT: {client_id}
SITE_TYPE: {site_type}
PAGES: {pages}
TECH: nextjs

generate_website(client_id, site_type, pages, "nextjs")

Output:
- clients/{id}/web/ directory
- All page files
- tailwind.config.js with brand colors
- package.json
```

### Step 4 — Nadia (QA + Deploy Approval)
```
REVIEW:
- Brand colors match? ✓/✗
- French language throughout? ✓/✗
- Mobile responsive? ✓/✗
- All pages generated? ✓/✗
- Contact form present? ✓/✗
- SEO metadata? ✓/✗

APPROVAL REQUIRED before deployment
```

### Step 5 — Deploy (After Approval)
```
cd clients/{client_id}/web
npm install
npx vercel --prod
```

## Tech Stack
- Next.js 14 App Router
- Tailwind CSS with brand colors
- TypeScript
- Deploy: Vercel

## Pages (Refine Clinic Standard)
1. **Home** — Hero + Services overview + Testimonials + CTA
2. **Services** — All treatments with details + booking CTA
3. **About** — Story, team, certifications, location
4. **Contact** — Form + WhatsApp + Map + Hours

## SEO Requirements
- Meta title: "[Service] Tanger | Refine Beauty Clinic"
- Meta description: French, 150-160 chars, include city
- H1: One per page, service-focused
- Schema: LocalBusiness markup
- Mobile: Core Web Vitals optimized
