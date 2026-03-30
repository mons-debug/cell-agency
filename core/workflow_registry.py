"""
Cell Agency — Workflow Registry
=================================
Predefined workflow templates. Each template defines the sequence of steps,
which agent handles each step, what tool to call, and whether approval is required.

Available templates:
    create_instagram_post  — strategy → assets → design → caption → QA → approval
    create_reel            — strategy → assets → reel concept → cover → caption → approval
    content_planning       — strategy → content plan → QA → approval → calendar
    website_creation       — strategy → web generation → QA → approval → deploy
    generate_report        — report generation → QA → deliver
    daily_analysis         — learning analysis (autonomous)
"""

from __future__ import annotations

from core.workflow_engine import WorkflowStep


# ── Step builder helper ────────────────────────────────────────────────────────

def _step(
    name: str,
    agent: str,
    tool: str,
    description: str = "",
    inputs: dict = None,
    requires_approval: bool = False,
    max_retries: int = 3,
    timeout_s: int = 120,
) -> WorkflowStep:
    return WorkflowStep(
        name=name,
        agent=agent,
        tool=tool,
        description=description,
        inputs=inputs or {},
        requires_approval=requires_approval,
        max_retries=max_retries,
        timeout_s=timeout_s,
    )


# ── Workflow Templates ─────────────────────────────────────────────────────────

WORKFLOW_TEMPLATES: dict[str, list[dict]] = {

    # ── 1. Create Instagram Post ───────────────────────────────────────────────
    "create_instagram_post": [
        _step(
            name="query_learnings",
            agent="strategy_agent",
            tool="learning.query_learnings",
            description="Query past learnings before creating content",
            inputs={"query": "best performing instagram posts {topic}", "client_id": "{client_id}"},
        ),
        _step(
            name="choose_assets",
            agent="asset_manager",
            tool="asset.choose_best_assets",
            description="Select best assets for this post",
            inputs={"client_id": "{client_id}", "brief": "{topic}", "count": 3},
        ),
        _step(
            name="generate_caption",
            agent="content_agent",
            tool="content.generate_caption",
            description="Generate caption with hook, body, CTA, and hashtags",
            inputs={
                "client_id": "{client_id}",
                "topic": "{topic}",
                "platform": "instagram",
                "language": "{language}",
                "tone": "{tone}",
            },
        ),
        _step(
            name="qa_review",
            agent="nadia",
            tool="builtin.qa_review",
            description="QA review: brand tone, sensitivity, CTA, hashtags",
            inputs={"client_id": "{client_id}"},
        ),
        _step(
            name="approval",
            agent="nadia",
            tool="builtin.noop",
            description="Awaiting owner approval before publishing",
            inputs={},
            requires_approval=True,
        ),
    ],

    # ── 2. Create Reel ────────────────────────────────────────────────────────
    "create_reel": [
        _step(
            name="find_inspiration",
            agent="strategy_agent",
            tool="learning.find_inspiration",
            description="Find reel inspiration for the topic",
            inputs={"query": "{topic} instagram reel", "platform": "instagram", "industry": "beauty"},
        ),
        _step(
            name="query_learnings",
            agent="strategy_agent",
            tool="learning.query_learnings",
            description="Pull past reel insights",
            inputs={"query": "best reel concepts {topic}", "client_id": "{client_id}"},
        ),
        _step(
            name="generate_reel_concept",
            agent="strategy_agent",
            tool="video.generate_reel_concept",
            description="Generate structured reel concept (hook, scenes, CTA, music)",
            inputs={
                "client_id": "{client_id}",
                "topic": "{topic}",
                "duration_s": 15,
                "style": "educational",
            },
        ),
        _step(
            name="choose_assets",
            agent="asset_manager",
            tool="asset.choose_best_assets",
            description="Select video clips or images for the reel",
            inputs={"client_id": "{client_id}", "brief": "{topic} reel visuals", "count": 5},
        ),
        _step(
            name="generate_caption",
            agent="content_agent",
            tool="content.generate_caption",
            description="Generate energetic reel caption with hook and hashtags",
            inputs={
                "client_id": "{client_id}",
                "topic": "{topic}",
                "platform": "instagram",
                "language": "{language}",
                "tone": "energetic and engaging",
            },
        ),
        _step(
            name="qa_review",
            agent="nadia",
            tool="builtin.qa_review",
            description="QA: hook strength, brand tone, technical specs",
            inputs={"client_id": "{client_id}"},
        ),
        _step(
            name="approval",
            agent="nadia",
            tool="builtin.noop",
            description="Awaiting owner approval before publishing reel",
            inputs={},
            requires_approval=True,
        ),
    ],

    # ── 3. Content Planning ────────────────────────────────────────────────────
    "content_planning": [
        _step(
            name="detect_gaps",
            agent="strategy_agent",
            tool="learning.detect_content_gaps",
            description="Detect content gaps and underrepresented themes",
            inputs={"client_id": "{client_id}"},
        ),
        _step(
            name="generate_strategy",
            agent="strategy_agent",
            tool="content.generate_content_strategy",
            description="Generate multi-week content strategy",
            inputs={
                "client_id": "{client_id}",
                "goal": "{goal}",
                "weeks": "{weeks}",
                "platforms": "{platforms}",
            },
        ),
        _step(
            name="create_plan",
            agent="content_agent",
            tool="content.create_content_plan",
            description="Build detailed week-by-week content calendar",
            inputs={
                "client_id": "{client_id}",
                "weeks": "{weeks}",
                "themes": "",
            },
        ),
        _step(
            name="qa_review",
            agent="nadia",
            tool="builtin.qa_review",
            description="QA: content mix, sensitivity, posting frequency",
            inputs={"client_id": "{client_id}"},
        ),
        _step(
            name="approval",
            agent="nadia",
            tool="builtin.noop",
            description="Awaiting owner approval before adding to calendar",
            inputs={},
            requires_approval=True,
        ),
    ],

    # ── 4. Website Creation ───────────────────────────────────────────────────
    "website_creation": [
        _step(
            name="query_learnings",
            agent="strategy_agent",
            tool="learning.query_learnings",
            description="Pull website best practices from knowledge base",
            inputs={"query": "website best practices beauty clinic", "client_id": "{client_id}"},
        ),
        _step(
            name="generate_website",
            agent="design_agent",
            tool="web.generate_website",
            description="Generate full Next.js website scaffold with brand colors",
            inputs={
                "client_id": "{client_id}",
                "site_type": "{site_type}",
                "pages": "{pages}",
                "tech_stack": "nextjs",
            },
            timeout_s=300,
        ),
        _step(
            name="qa_review",
            agent="nadia",
            tool="builtin.qa_review",
            description="QA: brand colors, French language, mobile, SEO metadata",
            inputs={"client_id": "{client_id}"},
        ),
        _step(
            name="approval",
            agent="nadia",
            tool="builtin.noop",
            description="Awaiting owner approval before deployment",
            inputs={},
            requires_approval=True,
        ),
    ],

    # ── 5. Generate Report ────────────────────────────────────────────────────
    "generate_report": [
        _step(
            name="run_analysis",
            agent="content_agent",
            tool="learning.daily_analysis",
            description="Run performance analysis to gather data",
            inputs={"client_id": "{client_id}"},
        ),
        _step(
            name="generate_report",
            agent="content_agent",
            tool="document.generate_report",
            description="Generate formatted performance report",
            inputs={
                "client_id": "{client_id}",
                "report_type": "{report_type}",
                "period": "{period}",
            },
        ),
        _step(
            name="qa_review",
            agent="nadia",
            tool="builtin.qa_review",
            description="QA: accuracy, completeness, format",
            inputs={"client_id": "{client_id}"},
        ),
    ],

    # ── 6. Daily Analysis (autonomous) ───────────────────────────────────────
    "daily_analysis": [
        _step(
            name="run_analysis",
            agent="strategy_agent",
            tool="learning.daily_analysis",
            description="Run daily performance analysis and store insights",
            inputs={"client_id": "{client_id}"},
        ),
        _step(
            name="detect_gaps",
            agent="strategy_agent",
            tool="learning.detect_content_gaps",
            description="Detect content gaps after analysis",
            inputs={"client_id": "{client_id}"},
        ),
    ],
}


# ── Public API ─────────────────────────────────────────────────────────────────

def list_templates() -> list[str]:
    """Return all available workflow template names."""
    return sorted(WORKFLOW_TEMPLATES.keys())


def get_workflow_steps(name: str, inputs: dict) -> list:
    """
    Return a copy of the WorkflowStep list for a named template.
    Raises ValueError if template not found.
    """
    if name not in WORKFLOW_TEMPLATES:
        available = sorted(WORKFLOW_TEMPLATES.keys())
        raise ValueError(
            f"Unknown workflow template: '{name}'. "
            f"Available: {available}"
        )
    # Return deep copies so modifications don't affect the template
    from copy import deepcopy
    return deepcopy(WORKFLOW_TEMPLATES[name])


def get_template_info(name: str) -> dict:
    """Return metadata about a workflow template."""
    if name not in WORKFLOW_TEMPLATES:
        raise ValueError(f"Unknown workflow template: '{name}'")
    steps = WORKFLOW_TEMPLATES[name]
    return {
        "name":            name,
        "step_count":      len(steps),
        "agents":          list(dict.fromkeys(s.agent for s in steps)),
        "tools":           [s.tool for s in steps],
        "approval_steps":  [s.name for s in steps if s.requires_approval],
        "requires_approval": any(s.requires_approval for s in steps),
    }
