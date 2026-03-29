#!/usr/bin/env python3
"""
Cell Agency — CrewAI Runner
Bridge between OpenClaw/MCP and CrewAI multi-agent execution.

Usage:
  python3 run_crew.py --crew=strategy --task=market_research --inputs='{"client_id":"refine-clinic","industry":"beauty","location":"Tanger"}'
  python3 run_crew.py --crew=creative --task=content_creation --inputs='{"client_id":"refine-clinic","topic":"laser treatment","format":"instagram_post"}'

Returns: JSON to stdout
  {"status": "success", "crew": "...", "task": "...", "result": "...", "output_file": "..."}
  {"status": "error", "error": "..."}
"""

import sys
import json
import argparse
import traceback
from pathlib import Path
from datetime import date

# Add tools/ to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from crewai import Agent, Task, Crew, Process, LLM
import yaml

from crew_tools import get_tools_for_agent

AGENCY_DIR = Path.home() / "agency"
CREWS_DIR = AGENCY_DIR / "crews"

# ─── MODEL MAPPING ────────────────────────────────────────────────────────────
# Map legacy GPT model names → Claude models

MODEL_MAP = {
    "gpt-4o":         "claude-sonnet-4-6",
    "gpt-4o-mini":    "claude-haiku-4-5-20251001",
    "gpt-4":          "claude-sonnet-4-6",
    "gpt-3.5-turbo":  "claude-haiku-4-5-20251001",
}

CREW_FILES = {
    "management":    "management_crew.yaml",
    "strategy":      "strategy_crew.yaml",
    "creative":      "creative_crew.yaml",
    "dev":           "dev_crew.yaml",
    "marketing_ops": "marketing_ops_crew.yaml",
}


def get_llm(model_name: str) -> LLM:
    """Return a CrewAI LLM object, translating legacy model names to Claude."""
    resolved = MODEL_MAP.get(model_name, model_name)
    return LLM(model=resolved, temperature=0.7)


def build_agent(name: str, config: dict) -> Agent:
    """Build a CrewAI Agent from a YAML config dict."""
    llm = get_llm(config.get("llm", "claude-haiku-4-5-20251001"))
    tool_names = config.get("tools", [])
    tools = get_tools_for_agent(tool_names)
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        llm=llm,
        tools=tools,
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
        memory=config.get("memory", False),
        max_iter=config.get("max_iter", 10),
    )


def build_task(name: str, config: dict, agents: dict, context_tasks: list = None) -> Task:
    """Build a CrewAI Task from a YAML config dict."""
    agent = agents.get(config["agent"])
    if not agent:
        raise ValueError(f"Task '{name}' references unknown agent: {config['agent']}")
    return Task(
        description=config["description"],
        expected_output=config["expected_output"],
        agent=agent,
        context=context_tasks or [],
        output_file=config.get("output_file"),
        human_input=config.get("human_input", False),
    )


def run_crew(crew_name: str, task_name: str, inputs: dict) -> dict:
    """
    Load a crew YAML and run a specific task.

    Args:
        crew_name: Key from CREW_FILES dict
        task_name: Task key in the YAML, or 'all' to run all tasks
        inputs: Template variables to interpolate into task descriptions

    Returns:
        Dict with status, result, output_file
    """
    if crew_name not in CREW_FILES:
        return {"status": "error", "error": f"Unknown crew: '{crew_name}'. Available: {list(CREW_FILES.keys())}"}

    yaml_path = CREWS_DIR / CREW_FILES[crew_name]
    if not yaml_path.exists():
        return {"status": "error", "error": f"Crew file not found: {yaml_path}"}

    crew_config = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    # Build agents
    agents = {}
    for agent_name, agent_config in crew_config.get("agents", {}).items():
        # Interpolate template variables in goal/backstory
        for field in ("goal", "backstory", "role"):
            if field in agent_config:
                for k, v in inputs.items():
                    agent_config[field] = agent_config[field].replace("{" + k + "}", str(v))
        agents[agent_name] = build_agent(agent_name, agent_config)

    # Determine which tasks to run
    all_tasks_config = crew_config.get("tasks", {})
    if task_name == "all":
        task_keys = list(all_tasks_config.keys())
    elif task_name in all_tasks_config:
        task_keys = [task_name]
    else:
        return {"status": "error", "error": f"Task '{task_name}' not found. Available: {list(all_tasks_config.keys())}"}

    # Build tasks with template interpolation
    tasks = []
    for key in task_keys:
        tc = dict(all_tasks_config[key])
        for field in ("description", "expected_output"):
            if field in tc:
                for k, v in inputs.items():
                    tc[field] = tc[field].replace("{" + k + "}", str(v))
        task = build_task(key, tc, agents)
        tasks.append(task)

    if not tasks:
        return {"status": "error", "error": "No tasks built."}

    # Build and run the crew
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
    )

    result = crew.kickoff(inputs=inputs)

    # Determine output file if any
    output_file = None
    for key in task_keys:
        if all_tasks_config[key].get("output_file"):
            output_file = all_tasks_config[key]["output_file"]

    return {
        "status": "success",
        "crew": crew_name,
        "task": task_name,
        "result": str(result.raw) if hasattr(result, "raw") else str(result),
        "output_file": output_file,
        "token_usage": str(result.token_usage) if hasattr(result, "token_usage") else None,
    }


# ─── NAMED WORKFLOWS ──────────────────────────────────────────────────────────
# Convenience wrappers for common multi-step tasks

def run_content_creation(client_id: str, topic: str, post_type: str = "instagram_post", project_name: str = "") -> dict:
    """Full content creation: strategy context → content → ready for QA."""
    return run_crew("creative", "content_creation", {
        "client_id": client_id,
        "topic": topic,
        "post_type": post_type,
        "project_name": project_name or f"{post_type}_{date.today().isoformat()}",
    })


def run_market_research(client_id: str, industry: str, location: str) -> dict:
    """Run market research for a client."""
    return run_crew("strategy", "market_research", {
        "client_id": client_id,
        "industry": industry,
        "location": location,
    })


def run_campaign_strategy(client_id: str, goal: str, duration: int = 4, budget: int = 2000) -> dict:
    """Create a full campaign strategy."""
    return run_crew("strategy", "create_campaign_strategy", {
        "client_id": client_id,
        "goal": goal,
        "duration": duration,
        "budget": budget,
    })


def run_weekly_report(client_id: str) -> dict:
    """Generate weekly analytics report."""
    return run_crew("marketing_ops", "generate_weekly_analytics", {
        "client_id": client_id,
    })


def run_qa_review(client_id: str, content: str, brand_guidelines: str) -> dict:
    """Run QA Gate review on content."""
    return run_crew("management", "qa_review", {
        "client_id": client_id,
        "content_to_review": content,
        "brand_guidelines": brand_guidelines,
    })


# ─── CLI ENTRY POINT ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cell Agency CrewAI Runner")
    parser.add_argument("--crew", required=True, help="Crew name (management|strategy|creative|dev|marketing_ops)")
    parser.add_argument("--task", required=True, help="Task name or 'all'")
    parser.add_argument("--inputs", default="{}", help="JSON string of template variables")
    parser.add_argument("--workflow", help="Named workflow shortcut (content|research|strategy|report|qa)")
    args = parser.parse_args()

    try:
        inputs = json.loads(args.inputs)

        if args.workflow:
            workflows = {
                "content": lambda: run_content_creation(
                    inputs.get("client_id", ""), inputs.get("topic", ""),
                    inputs.get("post_type", "instagram_post")
                ),
                "research": lambda: run_market_research(
                    inputs.get("client_id", ""), inputs.get("industry", ""),
                    inputs.get("location", "")
                ),
                "strategy": lambda: run_campaign_strategy(
                    inputs.get("client_id", ""), inputs.get("goal", ""),
                    inputs.get("duration", 4), inputs.get("budget", 2000)
                ),
                "report": lambda: run_weekly_report(inputs.get("client_id", "")),
                "qa": lambda: run_qa_review(
                    inputs.get("client_id", ""), inputs.get("content", ""),
                    inputs.get("brand_guidelines", "")
                ),
            }
            if args.workflow in workflows:
                result = workflows[args.workflow]()
            else:
                result = {"status": "error", "error": f"Unknown workflow: {args.workflow}"}
        else:
            result = run_crew(args.crew, args.task, inputs)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, ensure_ascii=False))
        sys.exit(1)
