"""
sdk/openhands_runner.py

Wires the ai-agent-team-spec multi-agent pipeline to the OpenHands Software Agent SDK.

Install:
    pip install openhands-ai>=1.5.0

Usage:
    python sdk/openhands_runner.py --task "Add a /health endpoint to the API"
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import uuid
from typing import Any

try:
    from openhands.core.config import AppConfig, LLMConfig
    from openhands.core.main import create_runtime, run_controller
    from openhands.events.action import MessageAction
except ImportError as e:
    raise SystemExit(
        "openhands-ai is not installed.\n"
        "Run: pip install openhands-ai>=1.5.0"
    ) from e

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "docs" / "agents"
PROMPTS_DIR = DOCS_DIR / "prompts"
SCHEMAS_DIR = DOCS_DIR / "schemas"


def _load_prompt(name: str) -> str:
    """Load a system prompt from docs/agents/prompts/."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        return f"You are the {name} agent in the ai-agent-team-spec pipeline."
    return path.read_text(encoding="utf-8")


def _load_schema(name: str) -> dict[str, Any]:
    """Load a JSON schema from docs/agents/schemas/."""
    path = SCHEMAS_DIR / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

AGENT_SEQUENCE = [
    "orchestrator",
    "planner",
    "builder_backend",
    "builder_frontend",
    "critic",
    "platform",
]


def build_config(llm_model: str, api_key: str) -> AppConfig:
    """Build an OpenHands AppConfig from env / CLI args."""
    llm_cfg = LLMConfig(
        model=llm_model,
        api_key=api_key,
    )
    config = AppConfig(llms={"default": llm_cfg})
    return config


def run_pipeline(task: str, llm_model: str, api_key: str) -> None:
    """Run the full Orchestrator -> Planner -> Builder -> Critic -> Platform pipeline."""
    trace_id = str(uuid.uuid4())
    print(f"\n=== ai-agent-team-spec run  trace_id={trace_id} ===")
    print(f"Task : {task}\n")

    config = build_config(llm_model, api_key)

    for agent_name in AGENT_SEQUENCE:
        print(f"--- [{agent_name}] starting ---")
        system_prompt = _load_prompt(agent_name)
        full_task = (
            f"trace_id: {trace_id}\n\n"
            f"{system_prompt}\n\n"
            f"--- TASK ---\n{task}"
        )
        runtime = create_runtime(config)
        try:
            result = run_controller(
                config=config,
                initial_user_action=MessageAction(content=full_task),
                runtime=runtime,
            )
            print(f"--- [{agent_name}] done  status={result.state} ---\n")
        finally:
            runtime.close()

    print(f"=== Pipeline complete  trace_id={trace_id} ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the ai-agent-team-spec pipeline via OpenHands SDK"
    )
    parser.add_argument("--task", required=True, help="Feature request / task description")
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        help="LLM model identifier (default: env LLM_MODEL)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY", ""),
        help="LLM API key (default: env LLM_API_KEY or ANTHROPIC_API_KEY)",
    )
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit(
            "Set LLM_API_KEY or ANTHROPIC_API_KEY env var, or pass --api-key"
        )

    run_pipeline(task=args.task, llm_model=args.model, api_key=args.api_key)


if __name__ == "__main__":
    main()
