---
story_id: "101-5"
jira_key: ""
epic: "101"
workflow: "trivial"
---
# Story 101-5: Retire daemon 'flux' alias shim

## Story Details
- **ID:** 101-5
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-10T10:47:57Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T10:22:37Z | 2026-06-10T10:24:22Z | 1m 45s |
| implement | 2026-06-10T10:24:22Z | 2026-06-10T10:30:14Z | 5m 52s |
| review | 2026-06-10T10:30:14Z | 2026-06-10T10:37:04Z | 6m 50s |
| implement | 2026-06-10T10:37:04Z | 2026-06-10T10:44:18Z | 7m 14s |
| review | 2026-06-10T10:44:18Z | 2026-06-10T10:47:57Z | 3m 39s |
| finish | 2026-06-10T10:47:57Z | - | - |

## Sm Assessment

**Scope (trivial, 2pts, daemon repo):** Pure naming-debt removal in `sidequest-daemon/sidequest_daemon/media/daemon.py`. ADR-070 already holds — `media/workers/` contains only `zimage_mlx_worker.py`; `FluxMLXWorker` is gone. This story retires the dead compatibility shim that still implies a Flux renderer exists.

**Concrete targets (per story description):**
1. `warm_up_flux()` at ~daemon.py:271 — the alias whose stated justification (`--warmup=flux` flag + RPC callers dispatching on `worker="flux"`) no longer has any callers. Remove it, or collapse to `'image'`.
2. The `('all','flux','image')` dispatch target at ~daemon.py:443 — drop the `'flux'` arm.
3. The `--warmup=flux` usage doc at ~daemon.py:9 — update CLI usage text.
4. Stale Flux-vs-Z-Image comments at ~daemon.py:220, 250, 322, 907-909 — rewrite to describe current MPS/CPU device placement, not retired behavior.

**Dev verification gates:**
- Grep `worker="flux"` / `worker='flux'` / `warmup=flux` across `sidequest-server/sidequest/daemon_client`, `sidequest-server/sidequest/media`, and orchestrator `scripts/` to confirm ZERO live callers before deleting (story claims zero — verify, don't assume).
- Check `justfile` / `just daemon` warmup invocations for the `flux` flag and update if present.
- Line numbers are approximate — locate by symbol/string, not line.

**Risk:** Low. No engine behavior change, no API contract touched. The only hazard is an out-of-clone caller (see memory: running stack may read a different clone) — but the grep is the gate.

**Workflow:** trivial/phased → next is `dev` (implement). No tests likely required beyond `daemon-lint`; if Dev adds a guard, a wiring grep-test is the right shape.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-daemon/sidequest_daemon/media/daemon.py` — removed dead `WorkerPool.warm_up_flux()` alias; dropped the `'flux'` arm from both warmup dispatch sites (RPC + CLI startup), collapsing to `("all", "image")`; updated `--warmup=flux` → `--warmup=image` usage doc + `_run_daemon` docstring; swept 5 stale Flux-vs-Z-Image device-placement comments to name Z-Image/MPS.

**Verification gates run:**
- Grep for `worker="flux"` / `warm_up_flux` / `warmup=flux` across `sidequest-server/sidequest/{daemon_client,media}` and orchestrator `scripts/` → ZERO callers (confirmed before deletion).
- justfile uses bare `--warmup` (no `=flux`) → no flag update needed.
- Post-edit: zero `flux` tokens remain in daemon.py; zero `warm_up_flux` refs in repo or tests.

**Tests:** 431/431 passing (GREEN) — full daemon suite via testing-runner; cross-checked 14 warmup/dispatch tests directly (real green, not fabricated).
**Lint:** `ruff check` clean on changed file.
**Branch:** feat/101-5-retire-flux-alias-shim (pushed to origin, base `develop`)

**Note for Reviewer (The Merovingian):** One intentional deviation logged — the CLI-startup dispatch gained `"image"` (was `("all","flux")`) so the newly-documented `--warmup=image` flag isn't a silent no-op. This is the AC's "CLI help reflects reality" requirement; see Design Deviations.

**Handoff:** To review phase.

---

**Rework (review round 1):** Addressed Reviewer's [HIGH] No-Silent-Fallbacks finding. Added `WARMUP_TARGETS` constant + `_validate_warmup_target()` guard; the `warm_up` RPC now returns `UNKNOWN_WORKER` for unknown workers (before warming anything) and `_run_daemon` raises on a bad `--warmup` value instead of starting cold. +8 tests in `tests/test_101_5_warmup_reject_unknown.py`. Full suite **439/439 green**, ruff clean. Branch repushed (`cd72fca`). Retiring `flux` is now loud, not silent.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation. Story scope was self-contained in `sidequest-daemon/.../media/daemon.py`; the zero-caller claim was verified by grep before deletion.

### Reviewer (code review)
- **Gap** (non-blocking): Unknown warmup targets silently no-op while reporting success at both dispatch sites — a pre-existing, class-wide No-Silent-Fallbacks gap (`worker="banana"` / `--warmup=bogus` were never loud either). Affects `sidequest_daemon/media/daemon.py` (`_handle_client` warm_up RPC ~L431, `_run_daemon` CLI warmup ~L1085 — add an explicit unknown-target rejection arm). This story's rework should close the gap for the retired `flux` token specifically; a follow-up could harden the whole class. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Added `"image"` to the CLI-startup warmup dispatch (not just removed `"flux"`)**
  - Spec source: context-story-101-5.md / epic-101.yaml AC ("daemon CLI help reflects reality"); SM Assessment ("Remove the alias (or collapse it to 'image')")
  - Spec text: "Remove the alias (or collapse it to 'image'), update the CLI usage text... daemon CLI help reflects reality"
  - Implementation: Both warmup dispatch sites now match `("all", "image")`. The RPC path already had `"image"`; the CLI-startup path at `_run_daemon` previously matched only `("all", "flux")`, so after retiring `flux` the documented `--warmup=image` flag would have been a silent no-op at startup. Added `"image"` there so the now-documented flag actually warms the image worker.
  - Rationale: The AC requires CLI help to reflect reality. Documenting `--warmup=image` while leaving the startup path matching only `flux`/`all` would make the help lie — violating the AC and the No-Silent-Fallbacks rule. The fix makes the RPC and CLI paths agree.
  - Severity: minor
  - Forward impact: none — no caller passed `worker="flux"` (grep-verified zero); `--warmup=image` now behaves as documented, `--warmup=all` and bare `--warmup` unchanged.

### Dev (rework — review round 1)
- **Added loud rejection of unknown warmup targets at both dispatch sites**
  - Spec source: Reviewer Assessment (review round 1), [HIGH] [SEC][SILENT][RULE] finding
  - Spec text: "Add an explicit unknown-target rejection at BOTH sites: RPC returns error UNKNOWN_WORKER; CLI exits non-zero / raises listing valid targets. Add one small test per site."
  - Implementation: New module constant `WARMUP_TARGETS = {"all","image","embed"}` (single source of truth) + `_validate_warmup_target()` fail-loud guard wired into `_run_daemon`. The `warm_up` RPC now returns an `UNKNOWN_WORKER` JSON-RPC error (via `continue`, before any warmup runs) for unknown workers. 8 tests added (`tests/test_101_5_warmup_reject_unknown.py`): RPC reject + accept, CLI guard reject + accept-all-known, `_run_daemon` wiring, flux-not-valid regression.
  - Rationale: Honors No-Silent-Fallbacks; retires `flux` *loudly* instead of sliding it into a silent bucket. Reviewer-requested.
  - Severity: minor (additive guard; no change to valid-target behavior)
  - Forward impact: any caller sending an unknown `worker=`/`--warmup=` value now gets a loud error instead of false "warm" confirmation. Valid targets (`all`/`image`/`embed`) unchanged.

### Reviewer (audit)
- **Dev's "Added `image` to the CLI-startup warmup dispatch"** → ✓ ACCEPTED by Reviewer: sound and AC-supporting. The RPC/CLI dispatch sets now agree on `("all", "image")` and the documented `--warmup=image` flag actually warms the worker. Ironically, Dev applied the No-Silent-Fallbacks rule to the `--warmup=image` startup case but stopped short of the *unknown-token* case at the same two sites — which round 1 flagged and round 2's rework resolved. No undocumented deviations spotted; the diff matches the logged change exactly.
- **Dev's rework "Added loud rejection of unknown warmup targets at both dispatch sites"** → ✓ ACCEPTED by Reviewer: directly discharges the round-1 [HIGH] finding. The shared `WARMUP_TARGETS` constant + `_validate_warmup_target` guard is the right, DRY shape; RPC `UNKNOWN_WORKER` error and CLI startup raise are both loud; 8 tests including a wiring test. reviewer-security re-confirmed CLOSED with no new issues. No undocumented deviations in the rework.
## Subagent Results

> Round 1 (REJECTED) found the No-Silent-Fallbacks gap. Round 2 (below) re-runs the
> enabled panel on the rework and is the authoritative result.

**Round 2 (post-rework):**

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 439/439 green, ruff clean, 2 files, flux fully excised (only test docstring names it) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (self-assessed: new unknown-token reject branch is covered by 8 tests) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings (silent-failure domain re-checked by reviewer-security — confirmed CLOSED) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings (self-assessed: 8 new tests assert behavior + wiring, no vacuous asserts) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings (self-assessed: comment sweeps accurate; new constant/guard docstrings correct) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (self-assessed: `frozenset` constant + `(str)->None` guard, clean types) |
| 7 | reviewer-security | Yes | clean | none | N/A — original finding confirmed CLOSED at both sites; no new injection/DoS/info-leak |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (self-assessed: guard is DRY via shared constant, not over-engineered) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (rule check performed by Reviewer in Rule Compliance below) |

**All received:** Yes (2 enabled returned clean; 7 disabled via settings, pre-filled)
**Total findings:** 0 confirmed (round-1 [HIGH] resolved), 0 dismissed, 0 deferred

### Rule Compliance

Re-enumerated against the reworked diff:

- **No Silent Fallbacks** — **COMPLIANT (now)**:
  - `_handle_client` warm_up RPC (~L450) — unknown `worker=` returns `UNKNOWN_WORKER` error and `continue`s *before* any warmup; no silent success. FIXED.
  - `_run_daemon` CLI warmup (~L1120) — `_validate_warmup_target(target)` raises `ValueError` on unknown value, crashing startup instead of logging "warm and ready" cold. FIXED.
  - `WARMUP_TARGETS` is the single source of truth for both sites; `flux` is deliberately absent.
- **No Stubbing / dead code** — **COMPLIANT**: dead `warm_up_flux` removed; new guard is live (wiring test proves `_run_daemon` calls it).
- **Don't Reinvent / Verify Wiring** — **COMPLIANT**: guard wired into `_run_daemon`; RPC reject inline. `test_run_daemon_wires_the_warmup_guard` is the wiring test.
- **Every Test Suite Needs a Wiring Test** — **COMPLIANT**: `test_run_daemon_wires_the_warmup_guard` verifies the guard is reachable from the production startup path.
- **OTEL on subsystem decisions** — **N/A**: daemon warmup path, non-narrator; CLAUDE.md exempts. (A reject is a loud error frame / startup crash — already observable.)
- **SOUL narrator rules** — **N/A**: no narrator surface touched.

### Devil's Advocate

Round-2 attempt to break the fix. Could the `continue` inside the `try` swallow the error or skip cleanup? No — `continue` is not an exception, so the `except Exception` arm is not entered; the error frame is written by `_write(...)` *before* the `continue`, and the loop has no post-dispatch `drain()` to skip (the next `await reader.readline()` flushes the buffer). Could the guard over-reject and break a valid caller? No — `test_warm_up_rpc_accepts_known_worker` and the parametrized `test_validate_warmup_target_accepts_known` pin `all`/`image`/`embed` as still-valid, and the full suite is green. Could `--warmup=` (empty string) or `--warmup=Image` (wrong case) still slip through silently? No — both are now `not in WARMUP_TARGETS`, so the RPC returns `UNKNOWN_WORKER` and the CLI raises; the empty/case typo footgun named in round 1 is closed. Could echoing `target!r` leak secrets or enable injection? No — the value is the caller's own input, reflected only into a JSON error string on a *local Unix socket*; it reaches no shell/SQL/path/template sink, and the only "disclosed" data is the static, non-secret valid-target set. The one residual: the broader *class* of unknown tokens beyond `flux` is now also handled here (a bonus), but hardening every other daemon dispatch surface is out of scope — recorded as the non-blocking Delivery Finding. Nothing here rises to a blocker.

## Reviewer Assessment

**Verdict:** APPROVED

> Supersedes the round-1 REJECTED verdict. The [HIGH] No-Silent-Fallbacks finding is resolved and re-verified clean.

**Causality (the why):** The round-1 cause — positive-match dispatch arms with no reject branch, so an unmatched token reached a success path — is eliminated. Both sites now gate on `WARMUP_TARGETS` *before* the match arms: the RPC writes an `UNKNOWN_WORKER` error and skips to the next request; the CLI raises `ValueError` at startup. Effect: retiring `flux` is now loud at every entry point, and the same guard closes the broader unknown-token class as a bonus. Valid targets (`all`/`image`/`embed`) are provably unchanged (green tests + parametrized accept test).

**Resolution of round-1 finding:**

| Severity | Round-1 Issue | Status |
|----------|---------------|--------|
| [HIGH] [SEC] [SILENT] [RULE] | Unknown/retired warmup target silently no-ops while reporting success | **RESOLVED** — `UNKNOWN_WORKER` RPC error + `_validate_warmup_target` startup raise; 8 tests (reject/accept × RPC/CLI, wiring, flux-not-valid). reviewer-security re-confirmed CLOSED at both sites. |

**Tag coverage (all 8):**
- `[SEC]` — reviewer-security round 2: **clean**. Original finding closed; `continue`-in-`try` semantics correct; `target!r` echo is local-socket-only, no injection/DoS/info-leak.
- `[SILENT]` — folded into [SEC]: the swallowed-success path is gone — both sites fail loud.
- `[EDGE]` — specialist disabled; self-assessed VERIFIED: the new unmatched-token branch is the only added edge and is covered by `test_warm_up_rpc_rejects_unknown_worker_loudly` + the CLI guard tests; empty-string/case typos now rejected.
- `[TEST]` — specialist disabled; self-assessed VERIFIED: 8 tests assert real behavior (error code, message, pool-not-called, success path, wiring via `inspect.getsource`), no vacuous asserts. evidence: `tests/test_101_5_warmup_reject_unknown.py`.
- `[DOC]` — specialist disabled; self-assessed VERIFIED: Flux→Z-Image comment sweeps accurate (sole worker is `zimage_mlx_worker.py`, ADR-070); new `WARMUP_TARGETS`/guard docstrings state the fail-loud intent. evidence: daemon.py:9, :163-185.
- `[TYPE]` — specialist disabled; self-assessed VERIFIED: `WARMUP_TARGETS: frozenset[str]`, `_validate_warmup_target(str) -> None`. No stringly-typed drift; constant is the single source of truth. 
- `[SIMPLE]` — specialist disabled; self-assessed VERIFIED: guard is DRY (one constant, one helper) and net-simplifying overall (dead alias removed). No over-engineering.
- `[RULE]` — Reviewer (see Rule Compliance): No-Silent-Fallbacks now COMPLIANT at both sites; wiring-test rule satisfied; all else compliant or N/A.

**Data flow traced:** operator/server `worker`/`--warmup` input → `params.get("worker","all")` / `arg.split("=",1)[1]` → **`WARMUP_TARGETS` membership gate** → (unknown) loud error/raise · (known) match arms warm the worker. The previously-unsafe unmatched leg now terminates in a loud failure. Safe.

**Pattern observed:** membership-gate-before-dispatch with a shared constant — `sidequest_daemon/media/daemon.py:171` (`WARMUP_TARGETS`) consumed at `:453` (RPC) and `:1123` (CLI via `_validate_warmup_target`).

**Error handling:** unknown RPC worker → `UNKNOWN_WORKER` JSON-RPC error (no partial warm); unknown CLI value → `ValueError` at startup (no cold-serving daemon); worker exceptions still → `WARMUP_FAILED` (unchanged).

**Handoff:** To SM (Morpheus) for finish-story. Non-blocking Delivery Finding (harden the whole unknown-token class across other dispatch surfaces) recorded for a future follow-up.