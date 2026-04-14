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
import os
import pathlib
import uuid

try:
    from pydantic import SecretStr
    from openhands.sdk import LLM, Agent, Conversation, Tool
    from openhands.tools.file_editor import FileEditorTool
    from openhands.tools.terminal import TerminalTool
except ImportError as e:
    raise SystemExit(
        "openhands-ai is not installed.\n"
        "Run: pip install openhands-ai>=1.5.0"
    ) from e

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).parent.parent
PROMPTS_DIR = REPO_ROOT / "docs" / "agents" / "prompts"


def _load_prompt(name: str) -> str:
    """Load a system prompt from docs/agents/prompts/."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        return f"You are the {name} agent in the ai-agent-team-spec pipeline."
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

AGENT_SEQUENCE = [
    "orchestrator",
    "planner",
    "builder_backend",
    "builder_frontend",
    "critic",
    "platform",
]


def run_pipeline(task: str, llm_model: str, api_key: str) -> None:
    """Run the full Orchestrator -> Planner -> Builder -> Critic -> Platform pipeline."""
    trace_id = str(uuid.uuid4())
    cwd = str(pathlib.Path.cwd())

    print(f"\n=== ai-agent-team-spec run  trace_id={trace_id} ===")
    print(f"Task : {task}\n")

    llm = LLM(
        model=llm_model,
        api_key=SecretStr(api_key),
    )

    for agent_name in AGENT_SEQUENCE:
        print(f"--- [{agent_name}] starting ---")

        system_prompt = _load_prompt(agent_name)
        full_message = (
            f"trace_id: {trace_id}\n\n"
            f"{system_prompt}\n\n"
            f"--- TASK ---\n{task}"
        )

        agent = Agent(
            llm=llm,
            tools=[
                Tool(name=TerminalTool.name),
                Tool(name=FileEditorTool.name),
            ],
        )

        conversation = Conversation(agent=agent, workspace=cwd)
        conversation.send_message(full_message)
        conversation.run()

        status = conversation.state.execution_status
        print(f"--- [{agent_name}] done  status={status} ---\n")

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
