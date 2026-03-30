# Prompt Template: Create Reel Workflow

## Trigger Phrases
- "create reel", "make a reel", "reel about", "instagram reel"

## Workflow Steps

### Step 1 — Strategy Agent (Trend Research + Concept)
```
TASK: Reel Concept Strategy
CLIENT: {client_id}
TOPIC: {topic}
DURATION: {duration_s} seconds (default: 15)

1. find_inspiration("{topic} instagram reel", "instagram", "{industry}")
2. query_learnings("best reel concepts {topic}")
3. generate_reel_concept(client_id, topic, duration_s, style)

Output: structured reel concept JSON (hook, scenes, music, CTA)
```

### Step 2 — Asset Manager (Find Clips/Images)
```
TASK: Reel Asset Selection
CLIENT: {client_id}
BRIEF: {concept.visual_description}

Run search_assets(client_id, "{visual_description}", "all")
Prioritize: video clips > high-res images > generated images

Output: list of asset paths per scene
```

### Step 3 — Video Agent (Reel Production)
```
TASK: Video Editing
CLIENT: {client_id}
CONCEPT: {concept from Step 1}
ASSETS: {assets from Step 2}

1. edit_video(assets, operations) — trim, sequence, add text overlays
2. If video generation needed: generate_video(concept, "mp4")

Output: reel video path (or production brief if API not available)
```

### Step 4 — Design Agent (Reel Cover/Thumbnail)
```
TASK: Reel Cover Design
CLIENT: {client_id}
TOPIC: {topic}
FORMAT: instagram_portrait (1080x1350)

generate_social_image(client_id, "{cover_prompt}", "instagram_portrait")
Output: cover image path
```

### Step 5 — Content Agent (Caption + Audio Direction)
```
TASK: Reel Caption
CLIENT: {client_id}
TOPIC: {topic}
LANGUAGE: {language}

generate_caption(client_id, topic, "instagram", language, "energetic and engaging")

Also provide:
- Audio/music recommendation (genre, mood, BPM)
- Text overlay copy for each scene
Output: caption + audio direction + overlay text
```

### Step 6 — Approval Queue
```
Submit to approval:
- Reel video/production brief
- Cover image path
- Caption draft
- Audio recommendation
- Estimated performance score
```

## Technical Specs
- Format: 9:16 vertical (1080x1920)
- Duration: 7s, 15s, 30s, 60s (hook in first 2s)
- Cover: 1080x1350 (appears in grid)
- Captions: keep short on reels (50-100 words + hashtags)
- Hook rule: first frame must stop the scroll

## Performance Benchmarks (Refine)
- Views > 5,000 = good
- Completion rate > 40% = excellent
- Saves > 50 = viral potential
- Hook: first 2s determines 80% of completion rate
