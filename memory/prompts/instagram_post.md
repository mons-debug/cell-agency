# Prompt Template: Instagram Post Workflow

## Trigger Phrases
- "create instagram post", "make a post", "post about", "create post for"

## Workflow Steps

### Step 1 — Strategy Agent (Brand + Learnings)
```
TASK: Instagram Post Strategy
CLIENT: {client_id}
TOPIC: {topic}
FORMAT: {format}

Before generating, query_learnings("best performing instagram posts {topic}")
to incorporate past insights.

Read brandkit for: colors, tone, audience, sensitivity rules.
Output: post concept (visual direction + content angle + format recommendation)
```

### Step 2 — Asset Manager (Choose Media)
```
TASK: Asset Selection
CLIENT: {client_id}
BRIEF: {concept from Step 1}

Run choose_best_assets({client_id}, "{visual_brief}", count=3)
Return: ranked asset list with paths
```

### Step 3 — Design Agent (Create Post)
```
TASK: Instagram Post Design
CLIENT: {client_id}
IMAGE: {best_asset from Step 2}
TEXT: {key_message}
FORMAT: {format}

If no suitable asset: generate_image(prompt, format)
Then: create_post_design(client_id, image_path, text, format)
Output: designed post image path
```

### Step 4 — Content Agent (Caption)
```
TASK: Instagram Caption
CLIENT: {client_id}
TOPIC: {topic}
LANGUAGE: {language}
FORMAT: {format}
TONE: {brand_tone}
HOOK: strong first line

Run generate_caption(client_id, topic, "instagram", language, tone)
Output: complete caption with hook + body + CTA + hashtags
```

### Step 5 — QA Gate (Nadia Reviews)
```
REVIEW:
- Caption matches brand tone? ✓/✗
- Visual matches brand identity? ✓/✗
- Sensitivity rules followed? ✓/✗
- CTA present and clear? ✓/✗
- Hashtags (15-20, mix FR/AR/local)? ✓/✗
Score: /10
```

### Step 6 — Approval Queue
```
Submit to approval:
- Image preview path
- Caption draft
- Hashtags
- Recommended posting time
- Confidence score
```

### Step 7 — Publish (After Approval)
```
schedule_post(client_id, "instagram", datetime, image_path, caption)
```

## Quality Standards
- Hook: must grab attention in first 2 words
- Caption length: 150-300 words for carousel, 80-150 for single image
- Hashtags: 15-20, never repeat same 30 hashtags every post
- Sensitivity: check brand_vault sensitivity_notes before posting medical claims
- Image: 1080x1080 (square) or 1080x1350 (portrait) at minimum

## Learning Triggers
After approval/rejection:
- store_learning(insight, client_id, "instagram", "content_performance")
