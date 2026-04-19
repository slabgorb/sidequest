---
story_id: "27-2"
jira_key: ""
epic: "27"
workflow: "trivial"
---
# Story 27-2: Strip ACEStepWorker from daemon runtime

## Story Details
- **ID:** 27-2
- **Jira Key:** (not tracked — personal project)
- **Epic:** 27 (MLX Image Renderer migration)
- **Workflow:** trivial
- **Repos:** daemon
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-07T06:27:50Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-07T06:18:08Z | 2026-04-07T06:19:21Z | 1m 13s |
| implement | 2026-04-07T06:19:21Z | 2026-04-07T06:23:30Z | 4m 9s |
| review | 2026-04-07T06:23:30Z | 2026-04-07T06:27:50Z | 4m 20s |
| finish | 2026-04-07T06:27:50Z | - | - |

## Scope

Pure deletion story. Remove ACE-Step music generation worker infrastructure from the daemon runtime.

**Deletion checklist:**
- [x] Delete `/sidequest_daemon/media/workers/acestep_worker.py`
- [x] Remove `warm_up_acestep()` method from WorkerPool
- [x] Remove `_ensure_acestep()` method from WorkerPool  
- [x] Remove `_acestep` and `_acestep_loaded` attributes from WorkerPool.__init__
- [x] Remove ACE-Step routing from warm_up handler (method == "warm_up")
- [x] Remove ACE-Step status reporting from status() method
- [x] Remove ACE-Step cleanup from cleanup() method
- [x] Remove ACE-Step print from send_status() CLI function

**Context:**
- ACE-Step stays as standalone content-creation script at ~/Projects/ACE-Step
- MUSIC_TIERS routing was already removed in 27-1
- This removes the warmup/cleanup/status infrastructure that still exists from old architecture

**Dependency:** None — independent story

## Sm Assessment

**Story 27-2** is a pure deletion task — remove ACEStepWorker and all ACE-Step runtime infrastructure from the daemon. Companion to 27-1 (TTS removal, now complete).

**Scope:** Delete `acestep_worker.py`, remove `_acestep`/`warm_up_acestep`/`_ensure_acestep`/`_acestep_loaded` from WorkerPool, remove ACE-Step from status/cleanup/warmup handler/send_status. Note: MUSIC_TIERS routing was already removed in 27-1.

**Risk:** Low. Pure subtraction with clear boundaries. ACE-Step continues as standalone script at `~/Projects/ACE-Step`.

**Routing:** Trivial workflow → Dev (implement phase).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest_daemon/media/workers/acestep_worker.py` — Deleted (ACEStepWorker class, 130 LOC)
- `sidequest_daemon/media/daemon.py` — Removed `_acestep`/`_acestep_loaded` fields, `warm_up_acestep()`, `_ensure_acestep()`, ACE-Step cleanup block, ACE-Step in status dict, ACE-Step warmup handler, ACE-Step in send_status. Also fixed stale docstring (removed "tts"), stale comment ("audio + voice" → "audio"), and removed dead ACE-Step comment.
- `pyproject.toml` — Updated description to remove "TTS"

**Tests:** 10/10 passing (GREEN)
**Branch:** feat/27-2-strip-acestep (pushed)

**Handoff:** To review phase (Westley)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | README.md stale refs | confirmed 1 (README stale docs) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | dismissed 2 (pre-existing warmup pattern) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 5 | dismissed 5 (all pre-existing) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 1 (README stale docs), dismissed 3 (pre-existing) |

**All received:** Yes (4 returned, 5 disabled)
**Total findings:** 1 confirmed (LOW — README stale docs), 10 dismissed (pre-existing), 0 deferred

### Subagent Finding Decisions

**Confirmed:**
- [RULE] README.md has 6 stale ACE-Step references (architecture diagram, worker section, env var, CLI flag, warm_up table) — introduced by this PR's incomplete cleanup

**Dismissed (pre-existing, not introduced by this diff):**
- [SILENT] warm_up handler silent no-op for unrecognized targets (daemon.py:169-173) — pre-existing pattern; any unrecognized worker name produced the same empty-result success response before this PR
- [SILENT] _run_daemon startup warmup silent no-op (daemon.py:394) — same pre-existing pattern
- [TYPE] tempfile.mkdtemp fallback (daemon.py:373) — pre-existing, untouched by diff
- [TYPE] EmbedWorker._load_model missing annotation — pre-existing
- [TYPE] pipeline_factory typed as None — pre-existing
- [TYPE] bare dict returns — pre-existing
- [TYPE] render() ValueError without log — pre-existing
- [RULE] pedalboard/scipy/sounddevice dependency status — not this PR's scope
- [RULE] warm_up handler silent no-op per no-silent-fallbacks rule — pre-existing pattern predates this PR; the warmup handler never validated unknown targets

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Deletion completeness — grep for `acestep|ACEStep|ace.?step|_acestep` returns zero hits across entire daemon Python codebase. Evidence: verified via `rg -i` across sidequest-daemon.
2. [VERIFIED] WorkerPool is now single-worker (Flux only) — `__init__` has only `_flux`/`_flux_loaded`, no remnant fields. Evidence: daemon.py:70-74.
3. [VERIFIED] status() only reports Flux — no orphaned "acestep" key. Evidence: daemon.py:108-113.
4. [VERIFIED] cleanup() only cleans Flux — no orphaned ACE-Step cleanup block. Evidence: daemon.py:117-121.
5. [VERIFIED] warmup handler only warms Flux — ACE-Step branch removed. Evidence: daemon.py:171-172.
6. [VERIFIED] 27-1 review findings fixed — stale docstring "tts" removed (daemon.py:369), stale comment "audio + voice" fixed (daemon.py:381), pyproject.toml description updated. Evidence: diff lines.
7. [LOW] README.md has 6 stale ACE-Step references — architecture diagram, worker section, ACE_STEP_PATH env var, --warmup=acestep CLI flag, warm_up table. [RULE]

### Data Flow Traced
Warmup request `{"method": "warm_up", "params": {"worker": "flux"}}` → `_handle_client` → `target="flux"` → `pool.warm_up_flux()` → FluxWorker loads. No ACE-Step code paths remain reachable.

### Wiring Check
Pure deletion — no new wiring needed. Verified no callers of `warm_up_acestep()` or `_ensure_acestep()` remain (grep returns zero).

### Error Handling
Unknown tier → ValueError at render(). Unknown warmup target → empty results dict (pre-existing pattern, not introduced). Both acceptable for scope.

### Security Analysis
No new attack surface. Pure deletion reduces surface area.

### Rule Compliance
- **No silent fallbacks:** Compliant for new code. Pre-existing warmup no-op pattern noted but not introduced.
- **No stubbing:** Compliant. No placeholders.
- **Verify wiring:** Compliant. No dangling imports.
- **OTEL:** N/A for deletion story.

### Devil's Advocate

The README.md stale docs are the real risk here. A developer reading the README would see ACE-Step listed as an active capability with documented env vars and CLI flags. They'd set ACE_STEP_PATH, pass --warmup=acestep, and get... silence. No error, no loaded model, just {"status": "warm", "workers": {}}. The stale docs + silent no-op pattern is a compound footgun.

However: this README was already partially stale (TTS references from 27-1 were likely not cleaned either). The README is not a runtime artifact — it's documentation that should be updated as a follow-on chore. The actual code behavior is correct: ACE-Step is gone, Flux is the only worker, unknown targets produce empty (but not crashing) results.

Could the deletion break the Rust API? The `sidequest-daemon-client` crate was already flagged in 27-1 as having dead TTS code. It doesn't call `warm_up_acestep` directly — the Rust side sends JSON-RPC warm_up requests by method name, not by importing Python classes. The daemon will just ignore the "acestep" target silently (pre-existing behavior).

No critical or high issues. One LOW finding (README stale docs). **APPROVED.**

[EDGE] No findings — disabled via settings
[SILENT] 2 findings — dismissed as pre-existing warmup pattern
[TEST] No findings — disabled via settings
[DOC] README.md stale ACE-Step references — confirmed LOW
[TYPE] 5 findings — dismissed as pre-existing
[SEC] No findings — disabled via settings
[SIMPLE] No findings — disabled via settings
[RULE] README stale docs confirmed LOW; warmup no-op dismissed as pre-existing

**Handoff:** To SM (Vizzini) for finish-story

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): Also fixed 3 stale documentation artifacts from 27-1 review findings: docstring "tts" warmup target, "audio + voice" comment, and pyproject.toml description. These were LOW findings from 27-1 review. Affects `sidequest_daemon/media/daemon.py` and `pyproject.toml`. *Found by Dev during implementation.*
- No other upstream findings.

### Reviewer (code review)
- **Improvement** (non-blocking): README.md has 6 stale ACE-Step references (architecture diagram, worker section, ACE_STEP_PATH env var, --warmup=acestep CLI flag, warm_up protocol table). Affects `sidequest-daemon/README.md` (update to reflect ACE-Step removal). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): sidequest-daemon CLAUDE.md "Why Python" section still mentions ACE-Step. Affects `sidequest-daemon/CLAUDE.md` (update to reflect daemon simplification). *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** 2 findings (0 Gap, 0 Conflict, 0 Question, 2 Improvement)
**Blocking:** None

- **Improvement:** README.md has 6 stale ACE-Step references (architecture diagram, worker section, ACE_STEP_PATH env var, --warmup=acestep CLI flag, warm_up protocol table). Affects `sidequest-daemon/README.md`.
- **Improvement:** sidequest-daemon CLAUDE.md "Why Python" section still mentions ACE-Step. Affects `sidequest-daemon/CLAUDE.md`.

### Downstream Effects

- **`sidequest-daemon`** — 2 findings

### Deviation Justifications

1 deviation

- **Fixed stale documentation from 27-1 alongside 27-2 deletions**
  - Rationale: These were LOW findings from 27-1 review in the same file being edited. Fixing them avoids a separate chore and the changes are minimal (3 string edits)
  - Severity: trivial

## Design Deviations

None yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Fixed stale documentation from 27-1 alongside 27-2 deletions**
  - Spec source: 27-2-session.md, Scope
  - Spec text: Session scope covers ACE-Step removal only
  - Implementation: Also fixed daemon.py docstring ("tts" removed), daemon.py comment ("audio + voice" → "audio"), and pyproject.toml description ("TTS" removed)
  - Rationale: These were LOW findings from 27-1 review in the same file being edited. Fixing them avoids a separate chore and the changes are minimal (3 string edits)
  - Severity: trivial
  - Forward impact: none

### Reviewer (audit)
- **Fixed stale documentation from 27-1** → ✓ ACCEPTED by Reviewer: Good initiative fixing adjacent stale docs in the same file being edited. Minimal scope creep, high value.