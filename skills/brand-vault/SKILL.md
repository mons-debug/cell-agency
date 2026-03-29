---
name: brand-vault
description: Access and manage client brand identity — colors, fonts, tone of voice, content guidelines, logo assets
---

# Brand Vault

Every client's brand identity lives in their Brand Vault. I ensure all content creation respects brand guidelines.

## What I Do

- **Read brand guidelines** for any client before creating content
- **Update brand vault** when new brand info is provided
- **Extract specific brand elements** — colors, tone, target audience, forbidden topics
- **Enforce brand consistency** — flag anything that violates a client's brand guidelines

## Trigger Phrases

"brand guidelines", "brand vault", "brand colors", "tone of voice", "client brand", "what does refine clinic look like", "brand assets"

## How I Work

1. Use `agency.read_brand_vault` to load client brand guidelines
2. Parse key elements: colors, fonts, tone, audience, forbidden topics
3. Return structured brand profile for use by content and design agents
4. Use `agency.update_brand_vault` to save updated brand information

## Brand Vault Fields (per client)

```
- Brand name & tagline
- Primary / secondary colors (hex codes)
- Typography / fonts
- Logo files location
- Target audience (demographics, psychographics)
- Tone of voice (adjectives: professional, friendly, luxurious, etc.)
- Content themes (topics to cover regularly)
- Forbidden topics / sensitivities
- Social media handles
- Website URL
- Key services / products
- Competitors to be aware of
- Content language(s)
```

## Refine Beauty Clinic Brand Notes

- **Tone:** Professional, warm, reassuring. French-Arabic mix for posts.
- **Audience:** Moroccan women, 25–45, Tanger area, middle-to-upper income
- **Colors:** To be confirmed — check brand_vault.md
- **Services:** Laser hair removal, skin treatments, aesthetics
- **Sensitivity:** Medical-adjacent — avoid exaggerated health claims
