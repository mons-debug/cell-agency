# Cell Agency — Tool Library

> Complete reference for all 10 MCP servers and their tools.
> Last updated: 2026-03-30

---

## Architecture

```
10 MCP Servers → CrewAI wrappers (crew_tools.py) → 6 Agents
```

All tools are callable via:
1. **MCP protocol** — Claude / OpenClaw connects directly
2. **CrewAI `@tool()` wrappers** — agents use them inside crews
3. **Direct Python import** — for workflow engine step execution

---

## Server Map

| Server | Script | Purpose |
|--------|--------|---------|
| `agency` | `mcp-servers/agency_server.py` | Core hub: files, memory, clients, approvals, observability |
| `social` | `mcp-servers/social_server.py` | Instagram, Facebook publishing |
| `ads` | `mcp-servers/ads_server.py` | Meta Ads campaign management |
| `design` | `mcp-servers/design_server.py` | Image generation and editing |
| `content` | `mcp-servers/content_server.py` | Captions, strategies, articles, ad copy |
| `video` | `mcp-servers/video_server.py` | Reel concepts and video briefs |
| `asset` | `mcp-servers/asset_server.py` | Asset search, tagging, management |
| `document` | `mcp-servers/document_server.py` | Reports, proposals, briefs |
| `web` | `mcp-servers/web_server.py` | Website generation and updates |
| `learning` | `mcp-servers/learning_server.py` | ChromaDB knowledge, inspiration, analytics |

---

## 1. Agency Server (`agency`)

Core hub — file operations, client registry, memory, approvals, autonomous planning, observability.

### File Operations
| Tool | Args | Returns |
|------|------|---------|
| `read_file` | `path` | File contents |
| `write_file` | `path, content` | Confirmation |
| `append_file` | `path, content` | Confirmation |
| `list_dir` | `path` | Directory listing |
| `create_dir` | `path` | Confirmation |
| `delete_file` | `path` | Confirmation |
| `file_exists` | `path` | Boolean |

### Web
| Tool | Args | Returns |
|------|------|---------|
| `web_search` | `query, num_results=5` | Search results JSON |
| `fetch_url` | `url` | Page content |

### Client Registry
| Tool | Args | Returns |
|------|------|---------|
| `create_client` | `client_id, name` | Client folder structure |
| `list_clients` | — | All registered clients |
| `read_brandkit` | `client_id` | `brandkit.json` contents |
| `update_brandkit` | `client_id, updates_json` | Updated brandkit |
| `read_brand_vault` | `client_id` | Legacy `brand_vault.md` |

### Memory / Knowledge
| Tool | Args | Returns |
|------|------|---------|
| `store_memory` | `key, value, client_id` | Confirmation |
| `retrieve_memory` | `key, client_id` | Stored value |
| `search_memory` | `query, client_id, limit` | Semantic search results |

### Content Calendar
| Tool | Args | Returns |
|------|------|---------|
| `read_calendar` | `client_id` | Calendar contents |
| `write_calendar` | `client_id, content` | Confirmation |
| `add_calendar_entry` | `client_id, entry` | Confirmation |

### Approval Engine
| Tool | Args | Returns |
|------|------|---------|
| `submit_approval` | `action, client_id, draft_output_json, confidence, workflow_id?, notes?` | `task_id` |
| `approve_task` | `task_id` | Updated task JSON |
| `reject_task` | `task_id, feedback` | Updated task JSON |
| `edit_approval_draft` | `task_id, changes_json` | Updated task JSON |
| `list_approvals` | `client_id?, status?` | Approval list JSON |
| `approval_queue_summary` | — | Human-readable summary |
| `check_requires_approval` | `action, confidence, trigger_source` | Boolean JSON |

### Workflow Engine
| Tool | Args | Returns |
|------|------|---------|
| `create_workflow` | `workflow_name, client_id, inputs_json, trigger_source?` | Workflow JSON |
| `workflow_status` | `workflow_id` | Status dict |
| `approve_workflow` | `workflow_id` | Updated workflow |
| `reject_workflow` | `workflow_id, feedback` | Updated workflow |
| `retry_workflow` | `workflow_id` | Updated workflow |
| `list_workflows` | `client_id?, state?, limit?` | Workflow list |
| `list_workflow_templates` | — | Available templates |

### Deliverables
| Tool | Args | Returns |
|------|------|---------|
| `list_deliverables` | `client_id, workflow_type?, limit?` | Deliverable list |
| `get_deliverable` | `deliverable_id` | Deliverable metadata + files |
| `update_deliverable_performance` | `deliverable_id, metrics_json` | Updated metadata |

### Learning Bridges (convenience wrappers)
| Tool | Args | Returns |
|------|------|---------|
| `run_daily_analysis` | `client_id` | Performance snapshot JSON |
| `run_weekly_optimization` | `client_id` | Weekly report JSON |
| `run_content_gap_detection` | `client_id` | Gap analysis JSON |

### Autonomous Planning
| Tool | Args | Returns |
|------|------|---------|
| `run_autonomous_task` | `schedule_name, client_ids?` | Batch results JSON |
| `list_autonomous_drafts` | `client_id?` | Draft list JSON |

### Observability
| Tool | Args | Returns |
|------|------|---------|
| `agency_dashboard` | — | Full system status JSON |
| `workflow_logs` | `workflow_id, last_n?` | Event log JSON |
| `agent_activity_report` | `agent_id?, hours?` | Activity stats JSON |
| `tool_usage_report` | `days?` | Tool call stats JSON |

---

## 2. Social Server (`social`)

Instagram and Facebook publishing.

| Tool | Args | Returns |
|------|------|---------|
| `publish_instagram_post` | `client_id, image_path, caption, hashtags?` | Post ID |
| `schedule_instagram_post` | `client_id, image_path, caption, scheduled_time` | Scheduled post ID |
| `publish_instagram_reel` | `client_id, video_path, caption` | Reel ID |
| `publish_instagram_story` | `client_id, media_path` | Story ID |
| `get_instagram_insights` | `client_id, post_id?` | Engagement metrics |
| `publish_facebook_post` | `client_id, content, image_path?` | Post ID |
| `get_facebook_insights` | `client_id, post_id?` | Reach, engagement |

---

## 3. Ads Server (`ads`)

Meta Ads campaign management.

| Tool | Args | Returns |
|------|------|---------|
| `create_campaign` | `client_id, objective, budget, audience_json` | Campaign ID |
| `pause_campaign` | `client_id, campaign_id` | Confirmation |
| `resume_campaign` | `client_id, campaign_id` | Confirmation |
| `get_campaign_stats` | `client_id, campaign_id?, days?` | Performance metrics |
| `create_ad_set` | `client_id, campaign_id, targeting_json, budget` | Ad set ID |
| `create_ad` | `client_id, ad_set_id, creative_json` | Ad ID |
| `get_ad_performance` | `client_id, ad_id` | CTR, CPC, ROAS |

---

## 4. Design Server (`design`)

Image generation and editing (Pillow + AI).

| Tool | Args | Returns |
|------|------|---------|
| `generate_image` | `prompt, style?, size?` | Generated image path |
| `edit_image` | `input_path, output_path, operations` | Edited image path |
| `create_post_design` | `client_id, template, text, image_path?, format?` | Composite image path |
| `add_logo` | `client_id, image_path, output_path, position?` | Image with logo |
| `remove_background` | `input_path, output_path` | Image with removed bg (`rembg`) |
| `resize_image` | `input_path, output_path, width, height` | Resized image |
| `add_text_overlay` | `input_path, output_path, text, position?, font_size?` | Image with text |

---

## 5. Content Server (`content`)

Captions, strategies, articles, ad copy — all powered by Claude.

| Tool | Args | Returns |
|------|------|---------|
| `generate_caption` | `client_id, topic, platform, language?, tone?` | Caption + hashtags |
| `generate_content_strategy` | `client_id, goal, duration_weeks, platforms` | Strategy JSON |
| `create_content_plan` | `client_id, weeks, themes?` | Multi-week calendar JSON |
| `generate_article` | `client_id, topic, word_count?, language?` | Long-form article |
| `generate_ad_copy` | `client_id, campaign_goal, offer, language?` | Ad text variations |

---

## 6. Video Server (`video`)

Reel concepts and video production briefs.

| Tool | Args | Returns |
|------|------|---------|
| `generate_reel_concept` | `client_id, topic, duration_s?, style?` | Concept JSON (hook, scenes, transitions, CTA, music) |
| `generate_video` | `concept_json, output_format?` | Production brief (stub — future Runway/Pika) |
| `edit_video` | `input_path, operations` | Edit instructions (stub — future ffmpeg) |

---

## 7. Asset Server (`asset`)

Client asset management — search, tag, choose.

| Tool | Args | Returns |
|------|------|---------|
| `list_assets` | `client_id, asset_type?` | File listing with metadata |
| `search_assets` | `client_id, query, asset_type?, limit?` | Semantic search results |
| `choose_best_assets` | `client_id, brief, count?` | Ranked asset list |
| `tag_assets` | `client_id, asset_paths_json, tags_json` | Confirmation |
| `get_asset_info` | `client_id, asset_path` | Size, dimensions, tags, usage |

---

## 8. Document Server (`document`)

Markdown documents, proposals, reports.

| Tool | Args | Returns |
|------|------|---------|
| `generate_document` | `client_id, doc_type, title, sections_json, language?` | Markdown document |
| `generate_report` | `client_id, report_type, period, data_json?` | Performance report |

`doc_type` options: `proposal`, `brief`, `report`, `plan`, `strategy`

---

## 9. Web Server (`web`)

Next.js website generation and updates.

| Tool | Args | Returns |
|------|------|---------|
| `generate_website` | `client_id, site_type, pages_json?, tech_stack?` | Scaffold path + summary |
| `update_website` | `client_id, page, changes` | Confirmation |

Output saved to `clients/{client_id}/web/`.

---

## 10. Learning Server (`learning`)

ChromaDB-backed knowledge, inspiration search, performance analytics.

| Tool | Args | Returns |
|------|------|---------|
| `store_learning` | `insight, source, client_id?, metric?, value?, category?` | Stored learning ID |
| `query_learnings` | `query, client_id?, category?, limit?` | Semantic search results |
| `find_inspiration` | `query, platform?, industry?, limit?` | Web search + stored results |
| `daily_analysis` | `client_id` | Performance snapshot + insights |
| `weekly_optimization` | `client_id` | Weekly strategy recommendations |
| `detect_content_gaps` | `client_id` | Missing themes + recommended posts |

---

## Workflow Templates

Predefined end-to-end workflows (defined in `core/workflow_registry.py`):

| Template | Steps | Approval Gate |
|----------|-------|---------------|
| `create_instagram_post` | query_learnings → choose_assets → generate_caption → qa_review → **approval** | Before publish |
| `create_reel` | find_inspiration → query_learnings → generate_reel_concept → choose_assets → generate_caption → qa_review → **approval** | Before publish |
| `content_planning` | detect_gaps → generate_strategy → create_plan → qa_review → **approval** | Before finalising |
| `website_creation` | query_learnings → generate_website → qa_review → **approval** | Before deploy |
| `generate_report` | run_analysis → generate_report → qa_review | No approval (internal) |
| `daily_analysis` | run_analysis → detect_gaps | No approval (autonomous) |

---

## Agent → Tool Mapping

| Agent | Primary Tools |
|-------|---------------|
| `nadia` | All approval tools, workflow tools, agency_dashboard, routing |
| `strategy_agent` | web_search, query_learnings, find_inspiration, generate_content_strategy, read_brandkit |
| `content_agent` | generate_caption, create_content_plan, generate_article, generate_report, generate_document |
| `design_agent` | generate_image, create_post_design, edit_image, remove_background, read_brandkit |
| `video_agent` | generate_reel_concept, generate_video, choose_best_assets |
| `asset_manager` | list_assets, search_assets, tag_assets, store_learning, query_learnings |

---

## Governance

| Rule | Detail |
|------|--------|
| Manual > Autonomous | Manual commands always override queued autonomous tasks |
| Confidence threshold | Autonomous actions need ≥ 0.75 to enter approval queue |
| Approval required | Publishing, ads, deploys, brand changes, client comms |
| Retry limit | Max 3 retries per failed workflow step |
| Audit trail | Every workflow event logged to `logs/workflow_logs/` |
