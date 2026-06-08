---
story_id: "91-5"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 91-5: Dark-spend detector

## Story Details
- **ID:** 91-5
- **Jira Key:** (none — Jira disabled)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-08T23:39:16Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-08T23:08:21Z | 2026-06-08T23:09:37Z | 1m 16s |
| red | 2026-06-08T23:09:37Z | 2026-06-08T23:19:09Z | 9m 32s |
| green | 2026-06-08T23:19:09Z | 2026-06-08T23:29:22Z | 10m 13s |
| review | 2026-06-08T23:29:22Z | 2026-06-08T23:34:05Z | 4m 43s |
| green | 2026-06-08T23:34:05Z | 2026-06-08T23:37:56Z | 3m 51s |
| review | 2026-06-08T23:37:56Z | 2026-06-08T23:39:16Z | 1m 20s |
| finish | 2026-06-08T23:39:16Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Dev (rework)
- No deviations from spec. Both fixes applied exactly as Colonel Potter specified.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core story — new modules, new method on existing class, new REST endpoints.

**Test Files:**
- `scripts/tests/test_91_5_dark_spend_reconcile.py` — reconciliation script (16 tests)
- `sidequest-server/tests/agents/test_91_5_ledger_instrumented_total.py` — SessionCostLedger.instrumented_total_usd() (7 tests)
- `sidequest-server/tests/server/test_91_5_dark_spend_reconcile_endpoint.py` — REST endpoints (9 tests)

**Tests Written:** 32 tests covering 7 ACs (reconcile script) + 6 ACs (ledger) + 6 ACs (endpoints)
**Status:** RED (failing — ready for Dev)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing | `test_fetch_billed_usd_http_error_raises`, `test_fetch_billed_usd_network_error_raises` | failing |
| #3 type annotations | `test_compute_gap_has_type_annotations` | failing |
| #4 logging level at error | `test_run_reconcile_alert_logs_at_error_level` | failing |
| #6 test quality (no vacuous) | Self-checked — fixed one vacuous pass in endpoint tests | passing |
| #11 input validation at boundaries | `test_post_reconciliation_missing_billed_usd_rejects`, `test_post_reconciliation_missing_alert_field_rejects` | failing |

**Rules checked:** 5 of 13 applicable lang-review rules have test coverage (remaining rules don't apply to the new code surface)
**Self-check:** 1 vacuous pass found and fixed (`test_get_reconciliation_empty_before_any_run` was accepting 404 as valid — fixed to require 200)

### Implementation targets for Dev:
1. **`scripts/reconcile_dark_spend.py`** — new script with `DARK_SPEND_ALERT_THRESHOLD_PCT=10.0`, `compute_gap()`, `fetch_billed_usd()`, `fetch_instrumented_usd()`, `emit_alert()`, `main()`
2. **`sidequest-server/sidequest/agents/cost_safety.py`** — add `SessionCostLedger.instrumented_total_usd() -> float`
3. **`sidequest-server/sidequest/server/rest.py`** (or new `dark_spend.py`) — `GET /api/debug/cost/instrumented`, `GET/POST /api/debug/cost/reconciliation` with Pydantic schema validation and watcher event `dark_spend.gap_detected` when `alert=True`

**Handoff:** To Dev (Major Charles Emerson Winchester III) for implementation

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (E741 lint error) | confirmed 1 |
| 2 | reviewer-edge-hunter | N/A | Skipped | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | N/A | Skipped | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | N/A | Skipped | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | N/A | Skipped | N/A | Disabled via settings |
| 6 | reviewer-type-design | N/A | Skipped | N/A | Disabled via settings |
| 7 | reviewer-security | N/A | Skipped | N/A | Disabled via settings |
| 8 | reviewer-simplifier | N/A | Skipped | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | N/A | Skipped | N/A | Disabled via settings |

**All received:** Yes (1 enabled subagent returned, rest disabled)
**Total findings:** 1 confirmed (lint), 0 dismissed, 0 deferred

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `scripts/reconcile_dark_spend.py` — new reconciliation script; `ReconcileResult` dataclass, `compute_gap()`, `fetch_billed_usd()`, `fetch_instrumented_usd()`, `emit_alert()`, `main()`; DARK_SPEND_ALERT_THRESHOLD_PCT=10.0; ERROR log + sys.exit(1) on alert; raises on missing ANTHROPIC_ADMIN_KEY
- `sidequest-server/sidequest/agents/cost_safety.py` — added `SessionCostLedger.instrumented_total_usd() -> float` (5 lines); sums cumulative_cost_usd; returns 0.0 on empty ledger
- `sidequest-server/sidequest/server/rest.py` — GET /api/debug/cost/instrumented, GET/POST /api/debug/cost/reconciliation with `_ReconcileResultPayload` Pydantic model; fires `dark_spend.gap_detected` watcher (severity=error) when alert=True; E741 rename cost_ledger

**Tests:** 32/32 passing (GREEN)
**Branches:**
- orchestrator: `feat/91-5-dark-spend-detector` (pushed)
- server: `feat/91-5-dark-spend-detector` (pushed, rework commit 731820cc)

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review

## Reviewer Assessment (Pass 1 — REJECTED)

**Verdict: REJECT — one blocking lint error**

### Observations

**[HIGH — BLOCKING] E741 ambiguous variable name `l` at `sidequest/server/rest.py:895`**
`l = _ledger()` — lowercase L is visually indistinguishable from 1/I. Ruff E741 flags this and `uv run ruff check .` (the server-check gate) will fail. Rename to `cost_ledger` or `_cost_ledger`.

**[MEDIUM] `severity="warn"` instead of `"error"` on `dark_spend.gap_detected` event — `rest.py:926`**
The original story context specified `publish_event(severity="error")` for a billing alarm. TEA's test accepts "warn" OR "error", so this passes tests, but the GM dashboard renders error events differently from warn. A billing alarm that displays as warn (yellow) instead of error (red) will look like a routine advisory. Recommend changing to `severity="error"`.

**[MEDIUM] Misleading alert text when server is unreachable — `reconcile_dark_spend.py:140-156`**
`fetch_instrumented_usd` silently returns 0.0 with a WARNING when the server is unreachable. This triggers a 100% dark-spend alert with message "100% of Anthropic spend is uninstrumented" — which is factually false when the server is merely down. An operator will chase dark spend when the real problem is a dead server. The WARNING log at line 141 is easy to miss. `emit_alert` should include "server unreachable" context when instrumented=0 was due to a connection failure, or at minimum the exit-2 path should be taken. Non-blocking for merge, but the operator experience is poor.

**[LOW] `_ReconcileResultPayload` class defined after the function that uses it — `rest.py:940`**
Works due to `from __future__ import annotations` + FastAPI lazy resolution, but unconventional. Future maintainers will not understand why this works. Move the class above `create_rest_router()` or add a comment.

**[VERIFIED] Type annotations on all public functions** — `compute_gap`, `fetch_billed_usd`, `fetch_instrumented_usd`, `emit_alert`, `main`, `instrumented_total_usd` all have full parameter + return type annotations. Complies with Python rule #3.

**[VERIFIED] No silent exception swallowing on the alert path** — `fetch_billed_usd` raises on HTTP/network errors (rule #1). `main()` catches with `sys.exit(2)`. The `fetch_instrumented_usd` path is documented as intentional 0.0 fallback (a design choice, not an accident).

**[VERIFIED] Pydantic input validation on POST** — `_ReconcileResultPayload` requires all 4 fields; FastAPI returns 422 on missing fields. Complies with rule #11.

**[VERIFIED] `DARK_SPEND_ALERT_THRESHOLD_PCT = 10.0`** — constant is correct, pinned, documented.

**[VERIFIED] `ReconcileResult` is `frozen=True`** — immutable result object, cannot be mutated after construction.

**[VERIFIED] ERROR log on alert path** — `emit_alert` uses `logger.error()`. Complies with rule #4.

### Rule Compliance

| Rule | Area | Verdict |
|------|------|---------|
| #1 silent exceptions | `fetch_billed_usd` raises; `fetch_instrumented_usd` returns 0.0 with WARNING (intentional) | PASS |
| #3 type annotations | All public functions annotated | PASS |
| #4 logging level | `emit_alert` uses ERROR; WARNING on server-unreachable | PASS |
| #5 path handling | `pathlib` not needed (urllib URLs only) | N/A |
| #7 resource leaks | All `urlopen` calls use `with` context manager | PASS |
| #8 unsafe deserialization | `json.loads()` on Admin API response (trusted source) | PASS |
| #11 input validation | Pydantic model validates POST body | PASS |

### Devil's Advocate

What if someone deploys this in a k8s cluster where the reconciliation script and the SideQuest server are in different namespaces? `_DEFAULT_SERVER_URL = "http://localhost:8765"` won't reach the server — `fetch_instrumented_usd` returns 0.0 → 100% alert fires on every run. No SIDEQUEST_SERVER_URL documentation at the deployment level. The script will page oncall every time cron runs until someone figures out the URL config.

The `_post_result_to_server` best-effort swallow means if posting fails, the dashboard never shows the result. For a "three channel" alert story, the third channel (dashboard) is silently dropped when the server is unreachable — which is exactly when the operator needs it most.

`compute_gap` uses `max(0.0, ...)` to clamp over-instrumentation to 0%. If instrumented > billed (a different class of bug — double-counting), the gap reads as 0%, no alert. This case is silently accepted as "clean". Not a false negative for the story's target, but a real class of instrumentation bug that would go undetected.

### Conclusion

One blocking issue: E741 lint error at `rest.py:895`. Fix required before merge. The MEDIUM findings (severity level, misleading alert text) are improvement candidates — neither is a correctness bug, but both degrade operator experience.

**Return to Dev for the E741 fix. Recommend also addressing severity="warn"→"error" in the same commit.**

## Reviewer Assessment (Pass 2 — APPROVED)

**Verdict: APPROVE**

### Rework Verification

**[VERIFIED] E741 fix applied — `rest.py:895`**
`cost_ledger = _ledger()` — ambiguous `l` eliminated. `uv run ruff check sidequest/server/rest.py` → `All checks passed!`

**[VERIFIED] Severity corrected — `rest.py:926`**
`severity="error"` — billing alarm will render as error (red) on GM dashboard, not warn (yellow). Matches original story context intent.

**[VERIFIED] 16/16 server tests GREEN** — no regression from the rename.

**[VERIFIED] Rework commit is surgical** — commit `731820cc` touches exactly 4 insertions + 4 deletions in `rest.py` only. No scope creep, no collateral changes.

### Non-blocking findings carried forward (no action required)
- `fetch_instrumented_usd` returns 0.0 on server-unreachable (intentional, documented in docstring; triggers 100% alert which is loud)
- `_ReconcileResultPayload` defined after `create_rest_router` (works due to `from __future__ import annotations`)

These are improvement candidates for a future story, not blockers.

## Sm Assessment

**Story:** 91-5 — Dark-spend detector (3pt, P1)
**Epic:** 91 — Dark Spend / LLM Cost Observability

**Scope confirmed:** Three-layer reconciliation — (1) instrumented spans (llm.request OTEL), (2) Admin API daily billed totals (scripts/anthropic_usage.py), (3) loud alert when gap >10%. GM dashboard surface for the reconciliation result.

**Context:** Epic 91 addresses a structural billing blind spot: ~97% of Anthropic spend (Haiku classification calls) emits no OTEL spans. Stories 91-1 through 91-4 landed the choke-point instrumentation. This story closes the loop with automated reconciliation and alerting so dark spend can never quietly re-emerge.

**Repos:** orchestrator (reconciliation script / cron / alert plumbing) + sidequest-server (GM dashboard surface).

**No blockers.** Ready for red phase.