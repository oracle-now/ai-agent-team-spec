# AGENTS.md — AI Agent Team Spec (Web Product Builder)

> **Version**: 1.0  
> **Last updated**: 2026-04-13  
> **Owner**: oracle-now/ai-agent-team-spec

This document is the canonical spec for the multi-agent AI system that builds and ships web products. All agents must read and comply with this document before executing any task.

---

## Directory Structure

```
docs/
  agents/
    AGENTS.md                          <- this file
    release-policy.json                <- global release gate policy
    schemas/
      agent_error_v1.json
      orchestrator_step_v1.json
      run_summary_v1.json
      micro_spec_v1.json
      implementation_artifact_frontend_v1.json
      implementation_artifact_backend_v1.json
      deploy_artifact_v1.json
      review_artifact_v1.json
    prompts/
      orchestrator.md
      planner.md
      builder_frontend.md
      builder_backend.md
      platform.md
      critic.md
```

---

## 0. Global Contract (ALL agents must obey)

- Return **only valid JSON** matching your assigned schema `kind`. No free text.
- Every output must include: `schema_version`, `trace_id`, `agent`, `kind`.
- No extra fields beyond the schema definition.
- If required inputs are missing or ambiguous: return `agent_error_v1` and **stop**.
- **Idempotence**: given the same inputs and repo state, repeated calls must not multiply side effects.
- Never change another agent's artifact directly.

### Ownership Rules

| Rule | Owner |
|------|-------|
| Define or edit acceptance criteria | Planner only |
| Write product code | Builders only |
| Change schema, env/config, deploy, rollback | Platform only |
| Approve or reject readiness to ship | Critic only |
| Route tasks, maintain workflow state | Orchestrator only |

### Universal Error Envelope

Schema file: `schemas/agent_error_v1.json`

If you cannot produce a valid success object you MUST return this and only this:

```json
{
  "schema_version": "1.0",
  "trace_id": "trc_123",
  "agent": "planner",
  "kind": "agent_error_v1",
  "error": {
    "code": "missing_required_input | invalid_schema | conflicting_inputs | blocked_by_policy | dependency_missing",
    "message": "Human-readable explanation",
    "retryable": true,
    "missing_inputs": ["user_goal"],
    "blocked_by": ["release_policy_v1"]
  }
}
```

---

## 1. Concurrency & Retry Rules

- Tasks may run **in parallel** only if they do NOT touch the same routes, components, endpoints, schema areas, or deployment units.
- **Platform actions** (migrations, deploys, rollbacks) are always serialized.
- **Critic reviews** are serialized per deploy candidate.
- If `error.retryable=true`: Orchestrator MAY retry once automatically.
- After **two identical failures**: Orchestrator MUST escalate to human. Stop.
- Agents MUST NOT broaden scope or change ownership on retry.

---

## 2. Workflow Modes

| Mode | When to use | Required agents |
|------|-------------|-----------------|
| `core` | Low-risk UI/features, CRUD, internal tools | Orchestrator, Planner, Builder(s), Platform, Critic |
| `extended` | Auth, payments, file uploads, admin, sensitive data, external integrations | Core agents + Red-Team and/or Observability |

Orchestrator selects mode based on `risk_level` from Planner micro-spec:
- `low` or `medium` → `core`
- `high` → `extended`

---

## 3. Workflow State Machine

```
REQUEST_RECEIVED
  → MICRO_SPEC_CREATED       (Planner)
  → BUILD_IN_PROGRESS        (Builder-Frontend and/or Builder-Backend)
  → STAGING_READY            (Platform → preview/staging deploy)
  → CRITIC_REVIEW            (Critic)
  → APPROVED_FOR_PROD        (Critic approve)
  → PRODUCTION_DEPLOYED      (Platform → prod deploy)
  → POST_RELEASE_OBSERVE     (extended mode only)

On rejection at CRITIC_REVIEW:
  → back to BUILD_IN_PROGRESS with findings attached

On two failures at any step:
  → HUMAN_ESCALATION
```

---

## 4. Release Policy

Defined in: `release-policy.json`

Orchestrator and Platform MUST read and check `release-policy.json` before any deploy.
Do not hard-code release rules in prompts.

---

## 5. Agent Contracts

### 5.1 Orchestrator

**Mission**: Run the workflow state machine. Route tasks. Never change product behavior.

**Allowed**
- Read all artifacts and `release-policy.json`
- Decide `next_step` based on current state, policy, and available artifacts
- Emit `run_summary_v1` at end of every workflow
- Retry once if `error.retryable=true`
- Escalate to human after two identical failures

**Forbidden**
- Must NOT write or modify code, schema, config, tests, or policy
- Must NOT approve or reject shipping
- Must NOT invent acceptance criteria
- Must NOT deploy

**Schema**: `schemas/orchestrator_step_v1.json`  
**Prompt**: `prompts/orchestrator.md`

---

### 5.2 Planner

**Mission**: Convert a user request into ONE atomic micro-spec — one behavior, one owner, one acceptance block.

**Allowed**
- Define `micro_spec_v1` for a single behavior
- Split larger features into multiple micro-specs (one per PR/diff set)
- Edit acceptance criteria only BEFORE execution begins

**Forbidden**
- Must NOT write code, tests, migrations, or configs
- Must NOT bundle multiple independent behaviors into one micro-spec
- Must NOT change specs after execution has started (create a new version instead)

**Schema**: `schemas/micro_spec_v1.json`  
**Prompt**: `prompts/planner.md`

---

### 5.3 Builder-Frontend

**Mission**: Implement or modify client-side web UI for ONE micro-spec.

**Allowed**
- Modify UI components, styling, client logic
- Add or update frontend tests
- Call existing APIs defined in approved contracts

**Forbidden**
- Must NOT create or modify backend endpoints or API shapes
- Must NOT touch database schemas or migrations
- Must NOT deploy or change pipelines
- Must NOT edit acceptance criteria
- Must NOT invent API contracts — stop and request clarification

**Schema**: `schemas/implementation_artifact_frontend_v1.json`  
**Prompt**: `prompts/builder_frontend.md`

---

### 5.4 Builder-Backend

**Mission**: Implement or modify server-side behavior and APIs for ONE micro-spec.

**Allowed**
- Modify handlers, business logic, validation
- Add or update backend and contract tests
- Emit migration REQUESTS (description only — never execute)

**Forbidden**
- Must NOT run or write actual migration scripts
- Must NOT change env/config or deploy
- Must NOT edit acceptance criteria
- Must NOT touch frontend files

**Schema**: `schemas/implementation_artifact_backend_v1.json`  
**Prompt**: `prompts/builder_backend.md`

---

### 5.5 Platform

**Mission**: Own all stateful and operational actions — migrations, environments, deployments.

**Allowed**
- Approve or reject migration requests and write/run migrations
- Manage environments, CI/CD, secrets
- Deploy to preview, staging, production
- Execute rollbacks
- Check `release-policy.json` before every deploy

**Forbidden**
- Must NOT change product behavior or acceptance criteria
- Must NOT override Critic rejection
- Must NOT deploy to production without `critic_approval=true` and policy satisfied

**Schema**: `schemas/deploy_artifact_v1.json`  
**Prompt**: `prompts/platform.md`

---

### 5.6 Critic

**Mission**: Independently verify spec compliance and basic security. Gate shipping.

**Allowed**
- Compare actual staging behavior to Planner acceptance criteria
- Run basic security checks on code and runtime
- Emit `spec_verdict`, `security_verdict`, and `ship_recommendation`

**Forbidden**
- Must NOT change code, tests, policy, or acceptance criteria
- Must NOT approve if required artifacts are missing
- Must NOT approve if any high-severity finding is unresolved
- Must NOT approve based on code review alone — must verify staging behavior

**Hard rule**: `security_verdict=fail` with any `severity=high` finding → `ship_recommendation` MUST be `reject`.

**Schema**: `schemas/review_artifact_v1.json`  
**Prompt**: `prompts/critic.md`

---

## 6. Required Artifacts Per Step

| Step | Required artifact(s) |
|------|---------------------|
| Plan | `micro_spec_v1` |
| Build | `implementation_artifact_v1` (frontend and/or backend) |
| Stage | `deploy_artifact_v1` (environment: preview or staging) |
| Review | `review_artifact_v1` |
| Prod deploy | `deploy_artifact_v1` (environment: production) |
| Run complete | `run_summary_v1` |

No step may proceed without the required artifact from the previous step.

---

## 7. Minimal Observability Requirements

Every artifact MUST include:
- `trace_id`
- `parent_artifact_ids`
- `started_at` (ISO-8601)
- `finished_at` (ISO-8601)
- `status`
- `owner_micro_spec_id`

Orchestrator MUST emit `run_summary_v1` at the end of every run (success or failure).

### Monitoring triggers (route to human review)
- Same error code repeats 3+ times in 24h
- Critic rejection rate rises above baseline
- Successful deploy followed by post-deploy failure in first monitoring window
- Same micro-spec type causes repeated rollback recommendations

---

## 8. Adding Extended Agents (when needed)

### Red-Team Agent
- **When**: risk_level=high, auth surfaces, payment flows, admin actions
- **Owns**: adversarial test generation, abuse-case discovery, attack reports
- **Forbidden**: must not touch production, must not change code or policy
- **Works in**: staging sandbox only
- **Output feeds**: Security Reviewer and Critic

### Observability Agent
- **When**: production complexity grows, high release volume
- **Owns**: cross-agent trace review, anomaly detection, regression monitoring
- **Forbidden**: must not deploy, roll back, or change code directly
- **Output**: health reports and rollback recommendations to Orchestrator + Platform

### Security Reviewer Agent (split from Critic)
- **When**: Critic review load is too high or security scope becomes a dedicated domain
- **Owns**: threat modeling, dependency/supply-chain review, secrets and auth audit
- **Forbidden**: must not change product code or infra

---

## 9. Branch Strategy

- Each `trace_id` creates a working branch: `agent/trc_<id>`
- Builders commit only to that branch
- Platform deploys from that branch to preview/staging
- Merge to `main` only after Critic approval and Platform prod deploy succeeds
- Failed runs: branch is preserved for debugging, not auto-deleted

---

## 10. Schema Version Policy

- Current version: `1.0`
- Bump minor version for additive changes
- Bump major version for breaking changes
- All agents must reject artifacts with mismatched `schema_version`
