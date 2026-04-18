# AGENTS.md — ai-agent-team-spec

> Auto-loaded by Codex, Cursor, Claude, and most AI coding agents.
> Read this entire file before touching any code.
> ⚠️ Meta note: This repo DEFINES agent behavior specs. You are an AI agent
> reading a repo about AI agents. The contracts here apply to the agents
> this spec describes — not to you directly — but you should understand
> them deeply before editing anything.

---

## What This Repo Is

A complete, production-ready specification for a multi-agent AI engineering
team that builds and ships web products autonomously.

This repo defines **contracts, prompts, schemas, and examples** for:

| Agent | Role |
|---|---|
| **Orchestrator** | Routes work, enforces gate logic, returns run summary |
| **Planner** | Decomposes request into a scoped, testable micro-spec |
| **Builder Backend** | Implements API, data layer, server logic |
| **Builder Frontend** | Implements UI, client logic, integration |
| **Critic** | Security + quality + scope review — approves or rejects |
| **Platform** | Deploys, manages migrations and rollback |

---

## Repo Structure

```
docs/agents/
├── AGENTS.md                         # Full team spec (canonical reference)
├── release-policy.json               # Environment rules, risk thresholds
├── prompts/                          # System prompts — one per agent
├── schemas/                          # JSON schemas — one per message type
└── examples/                         # End-to-end worked examples
sdk/
└── openhands_runner.py               # OpenHands SDK pipeline runner
```

---

## Critical Architecture Rules

### 1. The separation of duties is inviolable

These lines are HARD — do not blur them:

- **Critic cannot build or deploy** — review only
- **Platform cannot modify code or spec** — deploy only
- **Builders cannot self-approve or deploy** — build only
- **All writes go through Platform** — single state owner
- **Critic `reject` blocks deploy** — no bypass without Orchestrator override logged

If you are adding a feature that crosses these lines, stop and reconsider
the design.

### 2. Prompts are the agent's contract — edit with extreme care

Files in `docs/agents/prompts/` are the verbatim system prompts loaded by
the OpenHands runner. A change here changes agent behavior in every run.
Before editing any prompt:
- Document the exact behavior change you intend in your commit message
- Check whether the change invalidates any example in `docs/agents/examples/`
- Update the example if needed — never leave examples out of sync with prompts

### 3. Schemas are the message contracts — backward compatibility matters

Files in `docs/agents/schemas/` define the JSON schemas for inter-agent
messages. These are versioned (`_v1` suffix). Rules:
- **Never make a breaking change to an existing versioned schema**
- If you need a breaking change, create a new version (`_v2`) and update
  the runner to handle both during transition
- All schema changes must be reflected in the relevant example files

### 4. Gate logic in `openhands_runner.py` must match `release-policy.json`

The runner enforces gate logic programmatically. `release-policy.json` is
the human-readable source of truth for those gates. They must stay in sync.
If you change one, update the other in the same commit.

### 5. Trace IDs must propagate through every message

Every inter-agent message includes a `trace_id` from the originating
request. The runner propagates it. Never strip or regenerate `trace_id`
mid-pipeline — it breaks end-to-end observability.

### 6. Fail loudly — use `agent_error_v1`, never silent failures

All agent errors must be returned as `agent_error_v1` envelopes with
specific error codes. Do not catch and discard errors. Do not return
partial results without flagging them as partial. A silent failure is
worse than a loud one.

### 7. `release-policy.json` controls what can ship — respect risk levels

| Risk level | Behavior |
|---|---|
| `low` | Platform deploys automatically after Critic approval |
| `medium` | Requires Orchestrator confirmation before Platform deploys |
| `critical` | Halts after Planner — requires human approval before any build |

Do not change risk level thresholds without understanding the downstream
gate implications.

---

## How the Pipeline Runs

```
User task
    └── Orchestrator   (routing + gate logic)
          └── Planner  (micro_spec_v1)
                └── [parallel]
                    Builder BE  (implementation_artifact_backend_v1)
                    Builder FE  (implementation_artifact_frontend_v1)
                └── Critic      (review_artifact_v1)
                      ├── approve → Platform (deploy_artifact_v1)
                      └── reject  → back to Builder with findings
                            └── Platform (run_summary_v1 → caller)
```

Running locally:
```bash
export ANTHROPIC_API_KEY="your-key"
python sdk/openhands_runner.py --task "Add a /health endpoint"
```

---

## The Two Examples Are Your Ground Truth

Before making any structural change to prompts, schemas, or gate logic,
read both examples and confirm your change doesn't break either flow:

- `examples/01_feature_happy_path.md` — normal successful delivery
- `examples/02_critic_reject_and_rework.md` — security rejection + rework loop

If your change breaks an example flow, update the example. Never leave
examples stale.

---

## Pre-Ship Checklist

Before committing any change, verify:

- [ ] Prompt change? → Commit message documents exact behavior delta; examples checked
- [ ] Schema change? → No breaking changes to existing `_v1`; new version created if needed
- [ ] Gate logic change in runner? → `release-policy.json` updated to match
- [ ] New agent added? → Has prompt, input schema, output schema, and example coverage
- [ ] Trace ID still propagates end-to-end? → Check runner
- [ ] Both examples still valid against updated prompts/schemas?
- [ ] `agent_error_v1` used for all failure paths — no silent catches
