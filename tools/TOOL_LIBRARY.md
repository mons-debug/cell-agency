# Cell Agency — Complete Tool Library

> Single source of truth for all tools in the agency system.
> Every tool listed here maps to a real implementation in an MCP server or CrewAI wrapper.
> Update this file whenever a tool is added, renamed, or deprecated.

**Last updated:** 2026-03-29
**Total tools:** 104 (33 CrewAI wrappers + 71 MCP tools)
**Stubs:** 2 (Google Ads — needs OAuth2)
**Unreferenced before this update:** 11 (now all wired to agents)

---

## Naming Conventions

| Layer | Convention | Example |
|-------|-----------|---------|
| YAML agent tools list | `namespace.function_name` | `agency.read_file` |
| CrewAI `@tool()` names | `function_name_tool` | `read_file_tool` |
| MCP `@mcp.tool()` names | `function_name` (no suffix) | `agency_read_file` |

**Namespaces:** `agency.*` · `social.*` · `ads.*` · `design.*` · `deploy.*`

**Note on duplicates:** File ops, brand vault, calendar, memory, and web search tools exist in both
`mcp-servers/agency_server.py` (for OpenClaw/MCP sessions) and `tools/crew_tools.py` (for CrewAI
direct execution). This is intentional — two runtime contexts, same underlying logic.

**Note on `memory_store` signature difference:**
- CrewAI wrapper (`crew_tools.py`): takes `metadata_json: str` — JSON string, because CrewAI tools must use primitive types
- MCP version (`agency_server.py`): takes `metadata: Optional[dict]` — native dict, because MCP handles serialization

---

## `agency.*` — Core Agency Tools

Source: `mcp-servers/agency_server.py` | CrewAI wrappers: `tools/crew_tools.py`

### agency.read_file
- **MCP fn:** `agency_read_file(path: str) → str`
- **CrewAI fn:** `read_file_tool(path: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** content_creator, campaign_strategist, seo_specialist, tool_engineer, client_manager, reporting_agent

### agency.write_file
- **MCP fn:** `agency_write_file(path: str, content: str, overwrite: bool = True) → str`
- **CrewAI fn:** `write_file_tool(path: str, content: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** campaign_strategist, seo_specialist, audience_analyst, content_creator, brand_designer, video_editor, frontend_developer, backend_developer, tool_engineer, client_manager, email_marketer, lead_gen_specialist, reporting_agent, analytics_agent

### agency.append_file
- **MCP fn:** `agency_append_file(path: str, content: str) → str`
- **CrewAI fn:** `append_file_tool(path: str, content: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** (available, use for non-overwriting writes)

### agency.list_dir
- **MCP fn:** `agency_list_dir(path: str, pattern: str = "*") → list[str]`
- **CrewAI fn:** `list_dir_tool(path: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** tool_engineer

### agency.create_dir
- **MCP fn:** `agency_create_dir(path: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** frontend_developer, backend_developer

### agency.delete_file
- **MCP fn:** `agency_delete_file(path: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** (available for cleanup operations)

### agency.file_exists
- **MCP fn:** `agency_file_exists(path: str) → bool`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** (available for conditional logic)

### agency.read_brand_vault
- **MCP fn:** `read_brand_vault(client_id: str) → str`
- **CrewAI fn:** `read_brand_vault_tool(client_id: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, router, qa_gate, research_analyst, content_creator, brand_designer, graphic_designer, audience_analyst, ads_manager, client_manager, email_marketer

### agency.update_brand_vault
- **MCP fn:** `update_brand_vault(client_id: str, content: str) → str`
- **CrewAI fn:** `update_brand_vault_tool(client_id: str, content: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** brand_designer

### agency.list_clients
- **MCP fn:** `list_clients() → list[dict]`
- **CrewAI fn:** `list_clients_tool() → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, router, client_manager

### agency.create_client
- **MCP fn:** `create_client(client_id: str, name: str, industry: str, location: str = "") → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** client_manager (for new client onboarding)

### agency.read_calendar
- **MCP fn:** `read_calendar(client_id: str) → str`
- **CrewAI fn:** `read_calendar_tool(client_id: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, campaign_strategist, content_creator, social_media_manager

### agency.add_to_calendar
- **MCP fn:** `add_to_calendar(client_id: str, entry: str) → str`
- **CrewAI fn:** `add_to_calendar_tool(client_id: str, entry: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** campaign_strategist, social_media_manager

### agency.memory_store
- **MCP fn:** `memory_store(collection: str, doc_id: str, content: str, metadata: Optional[dict] = None) → str`
- **CrewAI fn:** `memory_store_tool(collection: str, doc_id: str, content: str, metadata_json: str = "{}") → str`
- **⚠️ Signature note:** CrewAI version uses `metadata_json: str` (JSON string) — intentional, CrewAI requires primitive types
- **Env vars:** none (ChromaDB local)
- **Status:** ✅ working
- **Used by:** research_analyst, seo_specialist, analytics_agent, lead_gen_specialist

### agency.memory_search
- **MCP fn:** `memory_search(collection: str, query: str, n_results: int = 5) → list[dict]`
- **CrewAI fn:** `memory_search_tool(collection: str, query: str, n_results: int = 5) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, research_analyst, campaign_strategist, content_creator, audience_analyst, email_marketer

### agency.memory_get
- **MCP fn:** `memory_get(collection: str, doc_id: str) → Optional[dict]`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, analytics_agent *(added 2026-03-28)*

### agency.memory_delete
- **MCP fn:** `memory_delete(collection: str, doc_id: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** (available for memory management)

### agency.list_memory_collections
- **MCP fn:** `list_memory_collections() → list[str]`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** (available for debugging)

### agency.search_web
- **MCP fn:** `search_web(query: str, n_results: int = 5) → list[dict]`
- **CrewAI fn:** `search_web_tool(query: str, n_results: int = 5) → str`
- **Env vars:** `SERPER_API_KEY` ⚠️ NOT SET YET
- **Status:** ✅ implemented (blocked until SERPER_API_KEY is set)
- **Used by:** research_analyst, seo_specialist, lead_gen_specialist

### agency.search_web_news
- **MCP fn:** — (no MCP version)
- **CrewAI fn:** `search_web_news_tool(query: str, n_results: int = 5) → str`
- **Env vars:** `SERPER_API_KEY` ⚠️ NOT SET YET
- **Status:** ✅ implemented (blocked until SERPER_API_KEY is set)
- **Used by:** research_analyst *(added 2026-03-28)*

### agency.fetch_webpage
- **MCP fn:** `fetch_webpage(url: str) → str`
- **CrewAI fn:** `fetch_webpage_tool(url: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** research_analyst, seo_specialist, lead_gen_specialist

### agency.run_python
- **MCP fn:** `run_python(script: str, timeout: int = 30) → dict`
- **Env vars:** none
- **Status:** ✅ working (requires approval for production use)
- **Used by:** backend_developer, devops_agent, tool_engineer

### agency.log_daily
- **MCP fn:** `log_daily(entry: str) → str`
- **CrewAI fn:** `log_daily_tool(entry: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, research_analyst, content_creator, ads_manager, social_media_manager, client_manager

### agency.read_daily_log
- **MCP fn:** `read_daily_log(date_str: str = "") → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia (for morning briefing)

---

## `social.*` — Instagram & Facebook Tools

Source: `mcp-servers/social_server.py`
**Required env vars:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID` — ⚠️ ALL NOT SET YET

### social.ig_create_image_post
- **MCP fn:** `ig_create_image_post(image_url: str, caption: str, location_id: Optional[str] = None) → dict`
- **Env vars:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** social_media_manager

### social.ig_create_carousel_post
- **MCP fn:** `ig_create_carousel_post(image_urls: list[str], caption: str) → dict`
- **Env vars:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** social_media_manager

### social.ig_schedule_post
- **MCP fn:** `ig_schedule_post(image_url: str, caption: str, publish_time_iso: str) → dict`
- **Env vars:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** social_media_manager

### social.ig_get_recent_posts
- **MCP fn:** `ig_get_recent_posts(limit: int = 10) → list[dict]`
- **Env vars:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** audience_analyst, analytics_agent, reporting_agent

### social.ig_get_account_insights
- **MCP fn:** `ig_get_account_insights(period: str = "day", metric: str = "impressions,reach,profile_views") → dict`
- **Env vars:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** audience_analyst, analytics_agent, reporting_agent

### social.ig_delete_post
- **MCP fn:** `ig_delete_post(media_id: str) → dict`
- **Env vars:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** social_media_manager

### social.ig_hashtag_search
- **MCP fn:** `ig_hashtag_search(hashtag: str) → dict`
- **Env vars:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** (available for content_creator and social_media_manager)

### social.suggest_hashtags
- **MCP fn:** `suggest_hashtags(niche: str, language: str = "en", count: int = 20) → list[str]`
- **Env vars:** none
- **Status:** ✅ working (returns AI-guided suggestions, not live hashtag data)
- **Used by:** content_creator, social_media_manager

### social.fb_post_to_page
- **MCP fn:** `fb_post_to_page(message: str, link: Optional[str] = None) → dict`
- **Env vars:** `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** social_media_manager

### social.fb_get_page_insights
- **MCP fn:** `fb_get_page_insights(metric: str = "page_impressions,page_reach", period: str = "day") → dict`
- **Env vars:** `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** social_media_manager, analytics_agent

---

## `ads.*` — Advertising Tools

Source: `mcp-servers/ads_server.py`
**Required env vars (Meta):** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID` — ⚠️ NOT SET YET
**Required env vars (Google):** `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CUSTOMER_ID` + OAuth2 setup

### ads.meta_list_campaigns
- **MCP fn:** `meta_list_campaigns(status: str = "ACTIVE") → list[dict]`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager, analytics_agent

### ads.meta_create_campaign
- **MCP fn:** `meta_create_campaign(name: str, objective: str, daily_budget_mad: float, status: str = "PAUSED") → dict`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager

### ads.meta_pause_campaign
- **MCP fn:** `meta_pause_campaign(campaign_id: str) → dict`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager

### ads.meta_activate_campaign
- **MCP fn:** `meta_activate_campaign(campaign_id: str) → dict`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager

### ads.meta_update_budget
- **MCP fn:** `meta_update_budget(campaign_id: str, daily_budget_mad: float) → dict`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager

### ads.meta_get_campaign_insights
- **MCP fn:** `meta_get_campaign_insights(campaign_id: str, date_preset: str = "last_7d") → dict`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager, analytics_agent, reporting_agent

### ads.meta_get_ad_account_overview
- **MCP fn:** `meta_get_ad_account_overview() → dict`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager

### ads.meta_list_ad_sets
- **MCP fn:** `meta_list_ad_sets(campaign_id: str) → list[dict]`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager

### ads.meta_list_ads
- **MCP fn:** `meta_list_ads(ad_set_id: str) → list[dict]`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** ads_manager

### ads.google_ads_get_campaign_performance
- **MCP fn:** `google_ads_get_campaign_performance(start_date: str, end_date: str) → list[dict]`
- **Env vars:** `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CUSTOMER_ID` + OAuth2
- **Status:** ❌ STUB — raises NotImplementedError. Needs: `pip install google-ads` + OAuth2 credentials
- **Used by:** ads_manager (not yet wired — blocked by stub)
- **To implement:** See https://developers.google.com/google-ads/api/docs/client-libs/python

### ads.google_ads_pause_campaign
- **MCP fn:** `google_ads_pause_campaign(campaign_id: str) → dict`
- **Env vars:** `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CUSTOMER_ID` + OAuth2
- **Status:** ❌ STUB — raises NotImplementedError
- **Used by:** ads_manager (not yet wired — blocked by stub)

### ads.generate_ads_performance_summary
- **MCP fn:** `generate_ads_performance_summary(client_id: str, period: str = "last_7d") → str`
- **Env vars:** `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID` (optional — degrades gracefully)
- **Status:** ✅ working (returns partial data if tokens missing)
- **Used by:** ads_manager, reporting_agent

---

## `design.*` — Image Generation & Design Tools

Source: `mcp-servers/design_server.py`
**Required env vars:** `GEMINI_API_KEY` ✅ SET · `ADOBE_FIREFLY_CLIENT_ID/SECRET` ⚠️ NOT SET (Gemini fallback available)

### design.generate_social_image
- **MCP fn:** `generate_social_image(client_id: str, prompt: str, format: str = "instagram_square", engine: str = "gemini", filename: Optional[str] = None) → str`
- **Env vars:** `GEMINI_API_KEY` or `ADOBE_FIREFLY_CLIENT_ID`/`ADOBE_FIREFLY_CLIENT_SECRET`
- **Status:** ✅ working (Gemini engine available)
- **Used by:** graphic_designer

### design.generate_logo_concept
- **MCP fn:** `generate_logo_concept(client_id: str, brand_name: str, style: str = "modern minimal", colors: str = "") → str`
- **Env vars:** `GEMINI_API_KEY`
- **Status:** ✅ working
- **Used by:** graphic_designer

### design.generate_ad_creative
- **MCP fn:** `generate_ad_creative(client_id: str, headline: str, background_style: str, product_description: str, format: str = "instagram_square") → str`
- **Env vars:** `GEMINI_API_KEY` or `ADOBE_FIREFLY_CLIENT_ID`/`ADOBE_FIREFLY_CLIENT_SECRET`
- **Status:** ✅ working (Gemini engine available)
- **Used by:** graphic_designer

### design.resize_for_platform
- **MCP fn:** `resize_for_platform(input_path: str, client_id: str, formats: list[str]) → dict[str, str]`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** graphic_designer

### design.add_brand_watermark
- **MCP fn:** `add_brand_watermark(input_path: str, output_path: str, brand_name: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** graphic_designer

### design.parse_design_brief
- **MCP fn:** `parse_design_brief(brief_text: str) → dict`
- **Env vars:** none
- **Status:** ✅ working (returns structured template from brief text)
- **Used by:** graphic_designer *(added 2026-03-28)*

### design.list_client_assets
- **MCP fn:** `list_client_assets(client_id: str, pattern: str = "*.png") → list[str]`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** graphic_designer

### design.get_social_sizes
- **MCP fn:** `get_social_sizes() → dict`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** brand_designer, graphic_designer

---

## `deploy.*` — Deployment Tools

Source: `tools/deploy_tools.py`
**Required env vars:** `VERCEL_TOKEN`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` — ⚠️ ALL NOT SET YET

### deploy.deploy_to_vercel
- **fn:** `deploy_to_vercel(project_dir: str, prod: bool = False) → dict`
- **Env vars:** `VERCEL_TOKEN`
- **Status:** ✅ implemented (blocked until token set)
- **Used by:** frontend_developer, backend_developer, devops_agent

### deploy.check_vercel_deployment
- **fn:** `check_vercel_deployment(deployment_url: str) → dict`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** frontend_developer, devops_agent

### deploy.deploy_to_cloudflare_pages
- **fn:** `deploy_to_cloudflare_pages(project_name: str, directory: str, branch: str = "main") → dict`
- **Env vars:** `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
- **Status:** ✅ implemented (blocked until tokens set)
- **Used by:** devops_agent

---

## `crew.*` — CrewAI-Only Tools (No MCP Equivalent)

Source: `tools/crew_tools.py` only — these are available to CrewAI agents but not via MCP/OpenClaw

### crew.create_project
- **CrewAI fn:** `create_project_tool(client_id: str, project_name: str, project_type: str = "campaign") → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** client_manager *(added 2026-03-28)*

### crew.get_project_status
- **CrewAI fn:** `get_project_status_tool(client_id: str, project_name: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, client_manager *(added 2026-03-28)*

### crew.update_project_status
- **CrewAI fn:** `update_project_status_tool(client_id: str, project_name: str, phase: str, status: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** client_manager *(added 2026-03-28)*

### crew.discussion_log_write
- **CrewAI fn:** `discussion_log_write_tool(client_id: str, project_name: str, agent_name: str, message: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** content_creator, brand_designer, graphic_designer, video_editor *(added 2026-03-28)*

### crew.discussion_log_read
- **CrewAI fn:** `discussion_log_read_tool(client_id: str, project_name: str) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, qa_gate *(added 2026-03-28)*

### crew.approval_queue_add
- **CrewAI fn:** `approval_queue_add_tool(item_id: str, item_type: str, description: str, client_id: str, data: str = "") → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** qa_gate *(added 2026-03-28)*

### crew.approval_queue_list
- **CrewAI fn:** `approval_queue_list_tool(status: str = "pending") → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia *(added 2026-03-28)*

### crew.approval_queue_resolve
- **CrewAI fn:** `approval_queue_resolve_tool(item_id: str, approved: bool, note: str = "") → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia *(added 2026-03-28)*

### crew.store_learning
- **CrewAI fn:** `store_learning_tool(insight: str, source: str, metric: str = "", value: str = "", client_id: str = "") → str`
- **Env vars:** none (uses ChromaDB)
- **Status:** ✅ working
- **Used by:** (available to all agents for storing marketing insights)

---

## Standalone Libraries (Not Tools — Used by MCP Servers Internally)

These are not directly called by agents but are imported by MCP servers:

| File | Imported By |
|------|------------|
| `tools/file_tools.py` | `agency_server.py` |
| `tools/web_tools.py` | `agency_server.py` |
| `tools/image_tools.py` | `design_server.py` |
| `tools/deploy_tools.py` | `mcp-servers` (future), `crew_tools.py` |

---

## Environment Variable → Tool Impact Map

| Env Var | Status | Tools Blocked If Missing |
|---------|--------|------------------------|
| `ANTHROPIC_API_KEY` | ✅ set | All agents (LLM) |
| `TELEGRAM_BOT_TOKEN` | ✅ set | OpenClaw gateway |
| `TELEGRAM_OWNER_ID` | ✅ set | Approval routing |
| `GEMINI_API_KEY` | ✅ set | design.generate_social_image, design.generate_logo_concept, design.generate_ad_creative |
| `SERPER_API_KEY` | ❌ missing | agency.search_web, agency.search_web_news, agency.fetch_webpage (search only) |
| `INSTAGRAM_ACCESS_TOKEN` | ❌ missing | all `social.ig_*` tools |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | ❌ missing | all `social.ig_*` tools |
| `FACEBOOK_ACCESS_TOKEN` | ❌ missing | social.fb_post_to_page, social.fb_get_page_insights |
| `FACEBOOK_PAGE_ID` | ❌ missing | social.fb_post_to_page, social.fb_get_page_insights |
| `META_ACCESS_TOKEN` | ❌ missing | all `ads.meta_*` tools |
| `META_AD_ACCOUNT_ID` | ❌ missing | all `ads.meta_*` tools (format: `act_123456789`) |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | ❌ missing | ads.google_ads_* (STUB anyway) |
| `GOOGLE_ADS_CUSTOMER_ID` | ❌ missing | ads.google_ads_* (STUB anyway) |
| `ADOBE_FIREFLY_CLIENT_ID` | ❌ missing | design.generate_social_image (Gemini fallback available) |
| `ADOBE_FIREFLY_CLIENT_SECRET` | ❌ missing | design.generate_social_image (Gemini fallback available) |
| `VERCEL_TOKEN` | ❌ missing | deploy.deploy_to_vercel |
| `CLOUDFLARE_API_TOKEN` | ❌ missing | deploy.deploy_to_cloudflare_pages |
| `CLOUDFLARE_ACCOUNT_ID` | ❌ missing | deploy.deploy_to_cloudflare_pages |

---

## Infrastructure — Health & Process Management

Source: `infra/health_check.py`, `infra/process_manager.py` | MCP tools: `mcp-servers/agency_server.py`

> No CrewAI wrappers — these are operator/Nadia tools via MCP + startup script.

### MCP: agency_health_check
- **MCP fn:** `agency_health_check() → str`
- **Status:** ✅ working
- **Checks:** env vars (by phase), MCP server PIDs, ChromaDB, task bus dirs, memory, clients, disk
- **Used by:** Nadia via Telegram — instant "is everything OK?" dashboard

### MCP: agency_server_status
- **MCP fn:** `agency_server_status() → str`
- **Status:** ✅ working
- **Used by:** Nadia — see which MCP servers are alive and their PIDs

### MCP: agency_restart_server
- **MCP fn:** `agency_restart_server(server_name: str) → str`
- **Status:** ✅ working
- **Used by:** Nadia — restart a crashed MCP server from Telegram

### MCP: agency_tail_log
- **MCP fn:** `agency_tail_log(server_name: str, lines: int) → str`
- **Status:** ✅ working
- **Used by:** Nadia — read last N log lines to debug a server crash

### Startup Script
- **File:** `start_agency.sh`
- **Usage:** `./start_agency.sh [--check|--stop|--restart|--status]`
- **Starts:** All 4 MCP servers (background, PID tracked) → OpenClaw gateway (foreground)
- **Logs:** `memory/logs/<server>.log`
- **PIDs:** `memory/pids/<server>.pid`

---

## `skill.*` — Skill Evolution System

Source: `skills/skill_tracker.py` | CrewAI wrappers: `tools/crew_tools.py` | MCP tools: `mcp-servers/agency_server.py`

> Logs every skill execution to SQLite (`memory/skill_performance.db`).
> Auto-updates `skills/<skill>/performance.json` after each run.
> Flags underperforming skills (success rate < 80%, QA < 7.0, approval < 70%).

### skill.log_run
- **CrewAI fn:** `skill_log_run_tool(skill, agent, status, client_id, triggered_by, qa_score, duration_s, notes) → str`
- **MCP fn:** `skill_log_run(...)` in `mcp-servers/agency_server.py`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** content_creator, research_analyst, ads_manager, qa_gate

### skill.log_feedback
- **CrewAI fn:** `skill_log_feedback_tool(run_id, feedback, approved) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, qa_gate (records Moncef's approval/rejection per run)

### skill.get_performance
- **CrewAI fn:** `skill_get_performance_tool(skill) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia (check before routing high-stakes tasks)

### MCP: skill_evolution_report
- **MCP fn:** `skill_evolution_report() → str`
- **File:** `mcp-servers/agency_server.py`
- **Status:** ✅ working
- **Used by:** Nadia via Telegram — full agency skill health dashboard

---

## `crew.*` — Agent Communication Protocol (Task Bus)

Source: `comms/task_bus.py` | CrewAI wrappers: `tools/crew_tools.py` | MCP tools: `mcp-servers/agency_server.py`

> File-based async task bus. Tasks stored as JSON files in `memory/tasks/{pending,active,done,failed}/`.
> Agents hand off work without Moncef's manual intervention.

### crew.task_send
- **CrewAI fn:** `task_send_tool(from_agent, to_agent, title, description, inputs_json, skill, priority) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, content_creator, brand_designer, research_analyst, campaign_strategist, qa_gate, ads_manager
- **Typical pipeline:** content_creator → qa_gate → social_media_manager

### crew.task_list
- **CrewAI fn:** `task_list_tool(agent_id, status) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, qa_gate, content_creator, graphic_designer, campaign_strategist, ads_manager, social_media_manager

### crew.task_claim
- **CrewAI fn:** `task_claim_tool(agent_id, task_id) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, qa_gate, content_creator, graphic_designer, campaign_strategist, ads_manager, social_media_manager

### crew.task_complete
- **CrewAI fn:** `task_complete_tool(task_id, outputs_json, note) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, qa_gate, content_creator, brand_designer, graphic_designer, campaign_strategist, ads_manager, social_media_manager

### crew.task_fail
- **CrewAI fn:** `task_fail_tool(task_id, reason) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** qa_gate, graphic_designer (marks tasks they cannot complete)

### crew.task_reply
- **CrewAI fn:** `task_reply_tool(task_id, from_agent, message) → str`
- **Env vars:** none
- **Status:** ✅ working
- **Used by:** nadia, qa_gate, content_creator, graphic_designer, social_media_manager

### MCP: send_agent_task
- **MCP fn:** `send_agent_task(from_agent, to_agent, title, description, inputs_json, skill, priority) → str`
- **File:** `mcp-servers/agency_server.py`
- **Status:** ✅ working
- **Used by:** Nadia via OpenClaw/Telegram — manually dispatch tasks to agents

### MCP: list_agent_tasks
- **MCP fn:** `list_agent_tasks(agent_id, status) → str`
- **File:** `mcp-servers/agency_server.py`
- **Status:** ✅ working
- **Used by:** Nadia — agency-wide task overview or per-agent inbox inspection

### MCP: get_agent_task
- **MCP fn:** `get_agent_task(task_id) → str`
- **File:** `mcp-servers/agency_server.py`
- **Status:** ✅ working
- **Used by:** Nadia — inspect a specific task including full thread of messages

---

## Known Issues & TODOs

| Issue | File | Priority |
|-------|------|---------|
| Google Ads stubs — needs OAuth2 + `google-ads` library | `mcp-servers/ads_server.py` | Medium |
| SERPER_API_KEY not set — all web search blocked | `~/agency/.env` | High |
| Instagram/Facebook tokens not set — publishing blocked | `~/agency/.env` | High |
| Meta Ads tokens not set — ads management blocked | `~/agency/.env` | High |
| No test suite | `tests/` (doesn't exist) | High |
| `suggest_hashtags` returns AI prompt guidance, not live data | `mcp-servers/social_server.py` | Low |
| `agency.ig_hashtag_search` not wired to any agent | `crews/creative_crew.yaml` | Low |
