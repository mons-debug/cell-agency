---
name: design-brief
description: Create and manage design briefs — translate marketing needs into visual design specifications
---

# Design Brief

I translate marketing objectives into clear design briefs that the Graphic Designer and Brand Designer agents can execute.

## What I Do

- **Parse creative requests** — understand what needs to be designed and why
- **Create design briefs** — structured specs with dimensions, style, copy, colors
- **Coordinate with brand vault** — ensure designs match brand guidelines
- **Quality check designs** — verify output matches the brief
- **Asset naming and organization** — maintain organized asset library

## Trigger Phrases

"design brief", "create design", "need a graphic", "social media graphic", "poster", "banner", "create visual", "design for", "make image"

## How I Work

1. Get request from Nadia or Moncef: what needs to be designed?
2. Load brand guidelines from `agency.read_brand_vault`
3. Generate a structured design brief
4. Pass brief to Graphic Designer for execution via `design.generate_social_image`
5. Review output against brief
6. Save approved asset to `clients/{id}/assets/`

## Design Brief Template

```
## Design Brief — [Type] — [Client] — [Date]

**Goal:** [What this design needs to achieve]
**Format:** [instagram_square / instagram_story / facebook_post / etc.]
**Dimensions:** [Width × Height px]

**Visual Style:**
- Mood: [luxurious / friendly / clinical / playful]
- Background: [color / gradient / photo / texture]
- Layout: [minimal / bold / editorial]

**Content/Copy:**
- Headline: [Max 5 words]
- Sub-copy: [1–2 lines if needed]
- CTA: [Button text if any]
- Logo: [position: top-right / bottom-center]

**Colors:**
- Primary: [#hex]
- Secondary: [#hex]
- Text: [#hex]

**References/Inspiration:** [describe or link]
**Due:** [date/time]
**Notes:** [anything special]
```

## Asset Naming Convention

`{client-id}_{type}_{format}_{YYYYMMDD}.png`

Examples:
- `refine-clinic_post_ig-square_20260401.png`
- `refine-clinic_story_promo_20260401.png`
- `refine-clinic_ad_facebook_20260401.png`
