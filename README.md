# ai-agent-team-spec

A complete, production-ready specification for a multi-agent AI engineering team that builds and ships web products.

## What this is

This repo defines the **contracts, prompts, schemas, and examples** for a team of AI agents that can receive a feature request and autonomously deliver deployed, tested, security-reviewed code.

The design follows proven principles from AI engineering practice:
- **Narrow agents** with clear, non-overlapping responsibilities
- **Explicit contracts**: every agent has a defined input schema, output schema, and allowed tools
- **Planner–Executor–Critic loop** with mandatory check-and-balance gates
- **Centralized orchestration** with a single Orchestrator routing all work
- **Defense in depth**: runtime I/O filters, Critic security review, policy enforcement before deploy
- **Observability first**: trace IDs propagated through every message, structured logs on every state change

---

## Agent team

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Orchestrator** | Routes work, enforces gate logic, returns run summary | Feature request | `run_summary_v1` |
| **Planner** | Decomposes request into a scoped, testable micro-spec | Feature request | `micro_spec_v1` |
| **Builder Backend** | Implements API, data layer, server logic | `micro_spec_v1` | `implementation_artifact_backend_v1` |
| **Builder Frontend** | Implements UI, client logic, integration | `micro_spec_v1` | `implementation_artifact_frontend_v1` |
| **Critic** | Security + quality + scope review. Approves or rejects. | Implementation artifacts + micro_spec | `review_artifact_v1` |
| **Platform** | Deploys to environment, manages migrations and rollback | Approved artifacts | `deploy_artifact_v1` |

### Separation of duties

```
[User Request]
      |
  Orchestrator  <-- single control plane, owns routing and gate logic
      |
   Planner      <-- defines WHAT to build (scope, acceptance criteria)
      |
  [parallel]
  Builder BE    <-- builds HOW (backend only)
  Builder FE    <-- builds HOW (frontend only)
      |
   Critic       <-- reviews artifacts against spec (cannot build or deploy)
      |
  Platform      <-- deploys (cannot change code or spec)
      |
 [Deployed URL]
```

**Where lines are hard:**
- Critic cannot build or deploy
- Platform cannot modify code or spec
- Builders cannot self-approve or deploy
- All writes go through Platform (the single "state owner")
- Critic `reject` blocks deploy — no bypasses without Orchestrator override logged

---

## Repository structure

```
docs/agents/
├── AGENTS.md                         # Full team spec and interaction model
├── release-policy.json               # Environment rules, risk thresholds, approval requirements
├── prompts/
│   ├── orchestrator.md               # Orchestrator system prompt
│   ├── planner.md                    # Planner system prompt
│   ├── builder_backend.md            # Builder Backend system prompt
│   ├── builder_frontend.md           # Builder Frontend system prompt
│   ├── critic.md                     # Critic system prompt
│   └── platform.md                   # Platform system prompt
├── schemas/
│   ├── micro_spec_v1.json            # Planner output schema
│   ├── implementation_artifact_backend_v1.json
│   ├── implementation_artifact_frontend_v1.json
│   ├── review_artifact_v1.json       # Critic output schema
│   ├── deploy_artifact_v1.json       # Platform output schema
│   ├── agent_error_v1.json           # Shared error envelope
│   ├── orchestrator_step_v1.json     # Orchestrator routing step
│   └── run_summary_v1.json           # Final run summary schema
└── examples/
    ├── 01_feature_happy_path.md      # End-to-end: feature in, deployed URL out
    └── 02_critic_reject_and_rework.md # Critic finds critical security flaw, builder reworks
```

---

## How to use this spec

### 1. Use the prompts as system prompts
Each file in `prompts/` is the system prompt for that agent. Load it verbatim as the `system` message when initialising the agent.

### 2. Validate outputs against schemas
Each agent's output must conform to its schema in `schemas/`. Validate before passing to the next agent.

### 3. Enforce gate logic in your orchestrator

| Gate | Rule |
|------|------|
| After Planner | Validate `micro_spec_v1`. Halt if `risk_level=critical` without approval. |
| After Builder | Do NOT send to Platform. Send to Critic first. |
| After Critic | If `ship_recommendation=reject`: route BACK to builder with findings. Never to Platform. |
| After Critic approve | Platform may deploy. |
| After Platform deploy | Return `run_summary_v1` to caller with URL and rollback handle. |

### 4. Propagate trace IDs
Every message must include the `trace_id` from the originating request. All agents echo it on output. This enables end-to-end tracing across the full run.

### 5. Read the examples
- `examples/01_feature_happy_path.md` — normal successful delivery
- `examples/02_critic_reject_and_rework.md` — security rejection and rework loop

---

## Release policy

See `release-policy.json` for:
- Per-environment approval requirements
- Risk level thresholds that block deployment
- Migration safety rules
- Rollback policy

---

## Design principles

1. **Narrow scope per agent** — each agent does one thing and cannot exceed it
2. **Contracts over conversation** — structured JSON schemas, not free-form text
3. **Critic as firewall** — no artifact reaches production without independent security + quality review
4. **Platform as single writer** — no agent mutates shared state except Platform
5. **Observability from day one** — trace IDs, structured logs, failure codes in every schema
6. **Fail loudly** — `agent_error_v1` with specific codes, never silent failures
