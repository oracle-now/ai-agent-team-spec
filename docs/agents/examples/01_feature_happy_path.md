# Example 01: Feature Happy Path

This example traces a complete, successful feature delivery: user story in, deployed URL out.

## Scenario
Feature request: "Add email/password login to the marketing site with a JWT-secured session."

---

## Step 1 — Orchestrator receives request

**Input to Orchestrator:**
```json
{
  "request": "Add email/password login to the marketing site with a JWT-secured session.",
  "environment": "staging",
  "trace_id": "trc_001"
}
```

**Orchestrator action:** Routes to Planner.

---

## Step 2 — Planner produces micro_spec_v1

**Output from Planner:**
```json
{
  "schema": "micro_spec_v1",
  "spec_id": "spec_login_001",
  "feature_summary": "Email/password login with JWT session",
  "acceptance_criteria": [
    "POST /api/auth/login accepts email+password, returns signed JWT",
    "Invalid credentials return 401 with generic error message",
    "Login form renders with email and password fields and submit button",
    "On success, JWT stored in httpOnly cookie, user redirected to /dashboard",
    "Rate limit: max 5 failed attempts per IP per 10 minutes"
  ],
  "scope_boundary": "Login flow only. No registration, password reset, or OAuth.",
  "requires_migration": false,
  "tests_required": true,
  "risk_level": "medium",
  "trace_id": "trc_001"
}
```

**Orchestrator action:** Sends spec to Builder Backend and Builder Frontend in parallel.

---

## Step 3 — Builder Backend produces implementation_artifact_backend_v1

**Output from Builder Backend (summary):**
```json
{
  "schema": "implementation_artifact_backend_v1",
  "artifact_id": "art_backend_001",
  "spec_id": "spec_login_001",
  "files_changed": [
    "src/routes/auth.ts",
    "src/middleware/rateLimit.ts",
    "tests/auth.test.ts"
  ],
  "test_results": { "passed": 12, "failed": 0 },
  "trace_id": "trc_001"
}
```

---

## Step 4 — Builder Frontend produces implementation_artifact_frontend_v1

**Output from Builder Frontend (summary):**
```json
{
  "schema": "implementation_artifact_frontend_v1",
  "artifact_id": "art_frontend_001",
  "spec_id": "spec_login_001",
  "files_changed": [
    "src/pages/login.tsx",
    "src/components/LoginForm.tsx",
    "tests/login.test.tsx"
  ],
  "test_results": { "passed": 8, "failed": 0 },
  "trace_id": "trc_001"
}
```

**Orchestrator action:** Sends both artifacts + micro_spec to Critic.

---

## Step 5 — Critic reviews both artifacts

**Output from Critic:**
```json
{
  "schema": "review_artifact_v1",
  "artifact_id": "art_backend_001",
  "ship_recommendation": "approve",
  "findings": [],
  "acceptance_criteria_met": true,
  "trace_id": "trc_001"
}
```

```json
{
  "schema": "review_artifact_v1",
  "artifact_id": "art_frontend_001",
  "ship_recommendation": "approve_with_notes",
  "findings": [
    {
      "severity": "low",
      "category": "quality",
      "description": "Login button missing aria-label for screen readers."
    }
  ],
  "acceptance_criteria_met": true,
  "trace_id": "trc_001"
}
```

**Orchestrator action:** Both approved (one with low note). Proceed to Platform.

---

## Step 6 — Platform deploys

**Output from Platform:**
```json
{
  "schema": "deploy_artifact_v1",
  "status": "deployed",
  "environment": "staging",
  "url": "https://staging.example.com",
  "version": "1.4.2",
  "rollback_handle": "rollback_abc123",
  "migration_applied": false,
  "trace_id": "trc_001"
}
```

---

## Step 7 — Orchestrator returns run_summary_v1

```json
{
  "schema": "run_summary_v1",
  "trace_id": "trc_001",
  "status": "success",
  "feature": "Email/password login with JWT session",
  "deployed_url": "https://staging.example.com",
  "version": "1.4.2",
  "rollback_handle": "rollback_abc123",
  "critic_notes": ["Login button missing aria-label for screen readers."]
}
```

---

## Agent interaction map

```
Orchestrator
  └─> Planner          (produces micro_spec_v1)
  └─> Builder Backend  (produces implementation_artifact_backend_v1)
  └─> Builder Frontend (produces implementation_artifact_frontend_v1)
  └─> Critic           (reviews both artifacts, returns review_artifact_v1 x2)
  └─> Platform         (deploys, returns deploy_artifact_v1)
  └─> [returns run_summary_v1 to caller]
```
