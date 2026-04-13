# Example 02: Critic Rejects — Builder Reworks

This example shows the check-and-balance loop when the Critic finds a critical security flaw.

## Scenario
Feature: "Add a file upload endpoint for user profile pictures."

---

## Step 1 — Planner produces micro_spec_v1

```json
{
  "schema": "micro_spec_v1",
  "spec_id": "spec_upload_002",
  "feature_summary": "Profile picture upload endpoint",
  "acceptance_criteria": [
    "POST /api/user/avatar accepts multipart/form-data",
    "Only JPEG and PNG accepted, max 5MB",
    "File stored in object storage, URL returned",
    "Requires authenticated session"
  ],
  "scope_boundary": "Upload only. No image resizing, no CDN config.",
  "requires_migration": false,
  "tests_required": true,
  "risk_level": "medium",
  "trace_id": "trc_002"
}
```

---

## Step 2 — Builder Backend produces first attempt

Builder Backend implements the endpoint but:
- Accepts any file extension (no validation)
- Stores file using the original filename from the client (path traversal risk)
- No auth middleware applied to the route

```json
{
  "schema": "implementation_artifact_backend_v1",
  "artifact_id": "art_backend_002a",
  "spec_id": "spec_upload_002",
  "files_changed": ["src/routes/upload.ts"],
  "test_results": { "passed": 3, "failed": 0 },
  "trace_id": "trc_002"
}
```

---

## Step 3 — Critic rejects

```json
{
  "schema": "review_artifact_v1",
  "artifact_id": "art_backend_002a",
  "ship_recommendation": "reject",
  "findings": [
    {
      "severity": "critical",
      "category": "security",
      "description": "No file type validation. Attackers can upload executable files (.php, .sh). Validate MIME type and extension server-side."
    },
    {
      "severity": "critical",
      "category": "security",
      "description": "Client-supplied filename used for storage path. Path traversal attack possible. Generate a random UUID filename server-side."
    },
    {
      "severity": "high",
      "category": "security",
      "description": "Auth middleware not applied to POST /api/user/avatar. Unauthenticated uploads possible."
    }
  ],
  "acceptance_criteria_met": false,
  "trace_id": "trc_002"
}
```

**Orchestrator action:** Critic rejected. Route back to Builder Backend with findings attached. Do NOT send to Platform.

---

## Step 4 — Builder Backend reworks (attempt 2)

Builder fixes all critical and high findings:
- MIME type checked against allowlist (image/jpeg, image/png)
- Filename replaced with `uuid4() + extension`
- Auth middleware applied

```json
{
  "schema": "implementation_artifact_backend_v1",
  "artifact_id": "art_backend_002b",
  "spec_id": "spec_upload_002",
  "files_changed": ["src/routes/upload.ts", "src/middleware/auth.ts"],
  "test_results": { "passed": 9, "failed": 0 },
  "trace_id": "trc_002"
}
```

---

## Step 5 — Critic approves

```json
{
  "schema": "review_artifact_v1",
  "artifact_id": "art_backend_002b",
  "ship_recommendation": "approve",
  "findings": [],
  "acceptance_criteria_met": true,
  "trace_id": "trc_002"
}
```

---

## Step 6 — Platform deploys

```json
{
  "schema": "deploy_artifact_v1",
  "status": "deployed",
  "environment": "staging",
  "url": "https://staging.example.com",
  "version": "1.4.3",
  "rollback_handle": "rollback_def456",
  "migration_applied": false,
  "trace_id": "trc_002"
}
```

---

## Key check-and-balance points

| Point | Rule enforced |
|-------|---------------|
| Critic found `critical` severity | Mandatory `reject` — no exceptions |
| Orchestrator on reject | Routes BACK to builder with findings, NOT to Platform |
| Builder does NOT self-approve | Must go through Critic again on rework |
| Platform only receives | Artifacts with Critic `approve` or `approve_with_notes` |

---

## Agent interaction map

```
Orchestrator
  └─> Planner             (spec_upload_002)
  └─> Builder Backend     (art_backend_002a) — FIRST ATTEMPT
  └─> Critic              (REJECT: 2 critical, 1 high)
  └─> Builder Backend     (art_backend_002b) — REWORK
  └─> Critic              (APPROVE)
  └─> Platform            (deploy)
  └─> [run_summary_v1 returned]
```
