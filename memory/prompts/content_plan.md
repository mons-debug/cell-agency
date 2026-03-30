# Prompt Template: Content Planning Workflow

## Trigger Phrases
- "plan content", "content calendar", "plan next week", "content plan for"

## Workflow Steps

### Step 1 — Strategy Agent (Research + Audience)
```
TASK: Content Strategy Research
CLIENT: {client_id}
DURATION: {weeks} weeks
PLATFORMS: {platforms}

1. query_learnings("best content themes {client_id}", limit=5)
2. find_inspiration("{industry} content calendar {platform}")
3. detect_content_gaps(client_id)
4. generate_content_strategy(client_id, goal, weeks, platforms)

Output: strategy JSON with themes, content mix, key messages
```

### Step 2 — Content Agent (Create Plan)
```
TASK: Detailed Content Plan
CLIENT: {client_id}
STRATEGY: {strategy from Step 1}
WEEKS: {weeks}

1. create_content_plan(client_id, weeks, themes)
2. For each post in plan: generate brief caption direction

Output: week-by-week content plan with:
- Post topics, formats, languages
- Posting days and times
- Visual direction per post
- Caption briefs
```

### Step 3 — Nadia Reviews
```
REVIEW CHECKLIST:
- Content mix balanced? (education/promo/engagement/BTS)
- Brand themes covered?
- Sensitivity rules respected?
- Posting frequency matches brand guidelines?
- French/Arabic/Darija balance?
- Key service coverage?
Score: /10
```

### Step 4 — Add to Calendar
```
add_to_calendar(client_id, formatted_plan)
```

## Content Mix Guidelines (Refine)
| Type | % | Examples |
|------|---|---------|
| Educational | 35% | How laser works, skincare tips, FAQ |
| Promotional | 25% | Offers, packages, seasonal promos |
| Behind the scenes | 20% | Team, clinic, equipment |
| Testimonials | 10% | Before/after, client reviews |
| Entertainment | 10% | Beauty tips, trends, local moments |

## Posting Schedule (Refine)
- Feed: 4-5 posts/week
- Stories: Daily
- Reels: 2-3/week
- Best times: 08:00, 12:30, 19:30 (Morocco time)
