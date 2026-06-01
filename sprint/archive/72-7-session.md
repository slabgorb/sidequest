---
story_id: "72-7"
jira_key: ""
epic: "72"
workflow: "tdd"
---
# Story 72-7: Apply NPC identity drift — overwrite canonical pronoun/role on re-mention, not warn-only

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | tests 52/52 (serial), ruff pass, 0 new smells | N/A (confirms green) |
| 2 | reviewer-edge-hunter | Yes | findings | 4 | confirmed 1 (whitespace, downgraded High→Medium), confirmed 2 deferred (name_generator, observation_pending), dismissed 1 (whitespace "permanent" claim — it self-corrects) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | dismissed 1 (legacy_registry "author-curated" — wrong; world_authored is the human tag), confirmed 1 (applied via **attrs), noted 1 low (will_apply naming, structural) |
| 4 | reviewer-test-analyzer | Yes | findings | 9 | confirmed 4 (unused otel_capture in AC-1/AC-2, per-span attrs in conflicting test, dispatch span, world_authored role path), deferred 5 low |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 | confirmed 2 (stale step-2 docstring, applied undocumented on span), confirmed 1 low (test docstring present-tense), dismissed 2 (bare-name/side-effect docstrings still accurate) |
| 6 | reviewer-type-design | Yes | findings | 3 | confirmed 1 pre-existing (drawn_from stringly-typed, 6 sites — debt, not introduced here), confirmed 1 (applied via **attrs), noted |
| 7 | reviewer-security | Yes | findings | 3 | all low/non-blocking (unbounded narrator string pre-existing pattern; perception firewall INTACT; no PII) |
| 8 | reviewer-simplifier | Yes | findings | 1 | dismissed (TEA already considered + declined; defensible — 2 occurrences, judgment call) |
| 9 | reviewer-rule-checker | Yes | findings | 3 | confirmed 2 (stale docstrings, logger.warning level), confirmed 1 (drawn_from literal — pre-existing) |

**All received:** Yes (9 returned, 7 with findings)
**Total findings:** 9 confirmed (all Medium/Low, non-blocking), 5 dismissed (with rationale), 7 deferred/noted

## Reviewer Assessment

**Verdict:** APPROVED

No Critical or High findings survive scrutiny. All five ACs and three edge cases are implemented and verified; the core session-894 failure is fixed; the OTEL `applied` contract is wired end-to-end (span attribute + route projection). The confirmed findings are Medium/Low quality and robustness improvements, recorded as non-blocking Delivery Findings for a fast-follow.

**Data flow traced:** narrator tool output → `NpcMention.role/pronouns` → `_apply_npc_mentions` pool-hit branch → `apply_overwrite = drawn_from != "world_authored"` gate → conditional overwrite of `pool_hit.role/pronouns` → `_detect_npc_identity_drift(applied=...)` → `npc_reinvented_span(applied=...)` → `SPAN_ROUTES[SPAN_NPC_REINVENTED]` projects `applied` → GM panel. The canonical value mutates and the mutation is observable — the lie-detector can confirm the record moved. Safe: bounded to identity fields; mechanical state (disposition/HP) never touched; appearance stays additive.

### Confirmed Findings (all non-blocking)

- `[EDGE]` **[MEDIUM] Whitespace-only `mention.role`/`pronouns` overwrites canonical** at `narration_apply.py:1716,1724`. `"   "` passes the `if mention.role` truthy gate and the strip-compare (`"" != "captain"`), so a whitespace-only narrator field overwrites a good value and fires a spurious drift span — violating the documented "empty = no opinion" contract. **Downgraded from edge-hunter's High:** it is transient and self-correcting (the next real mention overwrites the whitespace back, since the disagree-overwrite path restores it) and low-trigger (narrator must emit whitespace-only). Fix: add `.strip()` to the outer guards (and the detector guard at `session_helpers.py:2033`).
- `[TYPE][SILENT][DOC] ` **[MEDIUM] `applied` rides `npc_reinvented_span` via `**attrs`, not an explicit param** at `telemetry/spans/npc.py:543`. The marker is now load-bearing for the GM panel, but a refactor dropping `**attrs` or renaming the kwarg would silently revert every drift to `applied=False` (route fallback `.get("applied", False)`), with no type error. Fix: promote `applied: bool = False` to an explicit keyword on the span helper.
- `[DOC][RULE]` **[LOW] Stale `_apply_npc_mentions` docstring** at `narration_apply.py:1539-1541` — step 2 still says "additive upsert … existing values win on conflict," which 72-7 reverses for narrator-sourced members. Confirmed by direct read. Doc regression introduced by the change.
- `[DOC]` **[LOW] Test docstring present-tense stale** at `test_npc_identity_drift.py` (AC-3 test: "Today the span fires WITHOUT `applied`") — describes the pre-fix state as current.
- `[TEST]` **[MEDIUM] AC-1/AC-2 request `otel_capture` but never assert a span** (`test_npc_identity_drift.py`) — the fixture is dead weight there; span contract is covered only by AC-3. Also: the conflicting-drift test asserts span *count* (2) but not per-span `expected`/`narrator`/`applied`; the dispatch overwrite test asserts state but not the span; world_authored edge tests only the pronoun path, not role.
- `[SEC]` **[LOW] Unbounded narrator string → canonical state → prompt** at `narration_apply.py` pool-hit — no length cap/sanitization on `role`/`pronouns` that later feed the Early-zone roster. Pre-existing pattern (additive path had it); trusted local model; ADR-047 territory.
- `[RULE]` **[LOW] `logger.warning` fires for `applied=True`** (`session_helpers.py:2046`) — a successful authoritative overwrite is normal, arguably `info`. Dev documented this trade-off (caplog tests + span-severity convention depend on `warning`). Accepted as deliberate.
- `[TYPE][RULE]` **[LOW, PRE-EXISTING] `NpcPoolMember.drawn_from` is a bare `str`** (`game/npc_pool.py:53`) compared to literals at 6 sites — now load-bearing for the author-protection gate. A `Literal[...]` would make the gate type-safe. Not introduced by 72-7 (the literal pattern predates it), but this change raises its stakes.

### Dismissed Findings (with rationale)

- `[SILENT-High] legacy_registry overwritable` — **DISMISSED:** the agent assumed `legacy_registry` = human-curated, but it is the *old narrator-populated registry* migrated from pre-Wave-2A saves; `world_authored` is the actual human-authoring tag. TEA's denylist gate (`!= world_authored`) is the deliberate, documented policy (TEA deviation + Architect spec-check). Not a defect.
- `[SIMPLE] helper extraction` — **DISMISSED:** TEA explicitly considered and declined; 2 occurrences, judgment call; the simplifier agreed it was "defensible."
- `[EDGE] whitespace permanent corruption` — **DISMISSED (partial):** the "permanent poison" claim is wrong — the disagree-overwrite path restores a real value on the next mention. Retained as Medium (transient) above.
- `[DOC] bare-name / "side-effect only" docstrings` — **DISMISSED:** both remain accurate (bare-name fill-empty is unchanged; the detector function genuinely does not mutate).

### Deferred

- `[ARCHITECT/spec-check]` **Promoted-NPC (`npcs_hit`) drift stays stale in the prompt** — already adjudicated by Neo as a 72-2-adjacent follow-up (the shadowed pool member double-renders; a clean fix needs npcs↔npc_pool reconciliation). Concur — non-blocking, tracked.

### Rule Compliance (Python lang-review, 13 checks)

- **#1 silent exceptions** — no try/except in diff. ✓
- **#2 mutable defaults** — `applied: bool = False` immutable. ✓
- **#3 type annotations** — `_detect_npc_identity_drift` fully annotated (`applied: bool`, `-> None`); private helpers exempt. One gap: `applied` not in `npc_reinvented_span`'s explicit signature (via `**attrs`) — finding above. ✓ (with note)
- **#4 logging** — lazy `%`-form preserved (`"…applied=%s…", applied`); no PII; level (`warning` for applied=True) flagged Low. ✓ (with note)
- **#5 path handling** — none. ✓
- **#6 test quality** — no vacuous asserts, no skips, mock targets correct (live logger via monkeypatch); span asserts on real exporter, route test on extractor. Gaps (unused fixtures, combined AC-4 assertion) flagged. ✓ (with notes)
- **#7 resource leaks** — `with npc_reinvented_span(...)` context-managed. ✓
- **#8 unsafe deserialization** — none. ✓
- **#9 async pitfalls** — all sync. ✓
- **#10 import hygiene** — no star imports; local imports in tests acceptable. ✓
- **#11 input validation** — `m_val and e_val` guards; whitespace gap flagged. ✓ (with note)
- **#12 dependency hygiene** — no dep changes. ✓
- **#13 fix regressions** — two stale docstrings flagged (#1539, and partial at detector). ✓ (with notes)

### Devil's Advocate

Argue this code is broken. The most dangerous claim is that the OTEL marker can lie. The span's `applied` is computed *before* the write (`apply_overwrite` from `drawn_from`), not derived from a before/after comparison — so the span asserts intent, not outcome. Today the detector's own guard (`m_val and e_val and disagree`) keeps span-fire and write-fire in lockstep, so they cannot diverge. But that invariant is implicit and unguarded: a future maintainer who adds a field-level write carve-out (say, "don't overwrite role past resolution_tier X") would leave the span claiming `applied=True` on a write that never happened — and the GM lie-detector, the very thing this story exists to serve, would itself be lying. That is the sharpest latent risk; it is structural, not present-day, and the silent-failure agent's "derive applied from before/after" suggestion is the durable fix.

What would a confused narrator do? Emit `pronouns="  "` — and corrupt the roster for a turn (the whitespace finding). Emit a 5,000-char role string — it lands verbatim in the next prompt (the security finding); harmless with a trusted model, ugly otherwise. Re-mention a `world_authored` NPC with a "correction" — correctly suppressed, but the player who *wanted* the author's NPC updated has no path to do so except editing the pack; that is a deliberate "Yes, And" trade, not a bug. What about a stressed store? `drawn_from` deserialized as `"World_Authored"` (wrong case) or `"world_authored "` (trailing space) would silently flip the gate to overwrite a protected NPC — the stringly-typed finding, defense-in-depth. And the promoted NPC the players actually talk to? Its drift is still stale in the prompt (the deferred npcs_hit gap) — the highest-engagement path is the one this story does *not* fully close, which is an honest scope limit the Architect already flagged, not a hidden defect. None of these rise to data-corruption-that-sticks or a security breach in this deployment; all are tracked.

**Pattern observed:** clean threading of a boolean policy marker through detector → span → route, mirroring the existing `disposition.shift`/`npc.developed` span idioms. Good adherence to the OTEL Observability Principle.
**Error handling:** the gate is total (`!= world_authored` always defined); empty/None handled by `m_val and e_val`; whitespace is the one unhandled boundary (flagged).
**Handoff:** To SM for finish-story.

## Story Details
- **ID:** 72-7
- **Epic:** 72 (NPC Identity Hardening)
- **Jira Key:** (not in use)
- **Workflow:** tdd (phased: setup → red → green → spec-check → verify → review → spec-reconcile → finish)
- **Points:** 3
- **Priority:** p3
- **Stack Parent:** none
- **Repos:** sidequest-server

## Epic Context

**Epic 72: NPC Identity Hardening**

DEEP-DIVE source: perseus_cloud session 894 (2026-05-29). An NPC has no stable id — identity is a case-folded NAME STRING split across two unreconciled stores:
- `snapshot.npcs` = mechanical state (HP, disposition, abilities)
- `snapshot.npc_pool` = identity scaffold (name, pronoun, role, observation stage)

With no consistency invariant, the system exhibits:
- Identity drift: canonical pronoun/role can diverge from narrative re-mention
- Dormant development pipeline: weight escalation + disposition evolution + interest counting only fire on mechanical necessity (combat stat block), never on player interest (backwards from ADR-014/020)
- Observation pending scaffolds stale without cleanup

**Related stories (reference):**
- 72-1: Revive dormant NPC development pipeline (DONE)
- 72-2: Preserve disposition on pool→Npc promotion; reconcile npcs vs npc_pool on load (DONE)
- 72-3: MM NPC provenance through injection seam (DONE)
- 72-4: Route narrator-invented NPC names through culture-bound ADR-091 namegen (DONE)
- 72-5: Fix narrator-invented born-hostile disposition default (DONE)
- 72-9: Wire OCEAN/disposition + scenario belief_state for narrator-invented NPCs (DONE)
- 72-10: observation_pending gate-ordering assert (DONE)

## Story Description

**Current behavior (WARN-ONLY):**

When an NPC is re-mentioned by the narrator with a drifted canonical pronoun/role (e.g., Cassian was introduced as they/them, but narrator says "she approaches"), the system:
1. Detects the drift in `NpcIdentityResolver.resolve_drift()`
2. Logs a warning
3. **Returns the canonical (old) identity without updating**
4. The narrator continues with stale identity info

**Required behavior (APPLY drift):**

When an NPC is re-mentioned with a drifted canonical pronoun/role:
1. Detect the drift
2. **Overwrite the canonical pronoun/role in npc_pool** with the narrator-supplied value
3. **Emit OTEL watcher events** for the overwrite decision (event: `npc_identity_drift_applied`, fields: old pronoun, new pronoun, old role, new role, reason)
4. Return the updated identity
5. Continue narration with the new identity

**Technical approach:**

The fix lives in `sidequest/game/npc_identity.rs` (Rust module reference; post-ADR-082 it's in `sidequest-server/sidequest/game/npc_identity/resolver.py`):

1. **Resolver hook:** `NpcIdentityResolver.resolve_drift()` currently returns early on drift-detected with a warning. Change it to:
   - Call a new `apply_identity_drift()` method to mutate npc_pool
   - Emit OTEL watcher event: `npc_identity_drift_applied`
   - Return the updated identity

2. **OTEL instrumentation (per project OTEL Observability Principle):**
   - Event: `npc_identity_drift_applied`
   - Fields: `npc_name`, `old_pronoun`, `new_pronoun`, `old_role`, `new_role`, `reason` (e.g., "narrator-supplied", "dialogue-context", etc.)
   - Severity: `info` (it's a correction, not an error)
   - Watcher hook: GM panel must show drift applications in NPC detail view

3. **Acceptance criteria:**
   - [x] `test_npc_identity_drift_applied_overwrite_pronoun` — Verify pronoun is overwritten in npc_pool on re-mention
   - [x] `test_npc_identity_drift_applied_overwrite_role` — Verify role is overwritten in npc_pool on re-mention
   - [x] `test_npc_identity_drift_applied_otel_event` — Verify OTEL event is emitted with correct fields
   - [x] `test_npc_identity_drift_no_overwrite_on_no_drift` — Verify no overwrites or OTEL events when identity is stable
   - [x] `test_npc_identity_drift_persistence` — Verify overwritten identity persists across game state snapshots
   - [x] Integration test: Load a session with drifted identity → re-mention NPC → verify pronoun/role updated + OTEL logged

## Sm Assessment

**Routing decision:** Setup complete, handing off to tea (red phase).

- **Story selected by Operator** (72-7), part of in-flight epic 72 (NPC Identity Hardening, 7/11 done). Clean follow-on to 72-1/72-2 which already touched this subsystem.
- **Scope is bounded and single-repo** (sidequest-server): flip `resolve_drift()` from warn-only to apply-and-overwrite, plus OTEL on the overwrite decision. 3pt tdd.
- **OTEL is non-negotiable here** — the OTEL Observability Principle and the epic charter both require every leg emit watcher events. The `npc_identity_drift_applied` event is an explicit AC, not optional. tea must write a failing test that asserts the event fires.
- **Path caveat for tea/dev:** session lists `npc_identity/resolver.py` as the target, derived from the Rust reference. VERIFY the actual module path before writing tests — do not trust the path blind; the file may live elsewhere post-port.
- **Dual-clone hazard (this is oq-3):** branch `feat/72-7-npc-identity-drift` was created on sidequest-server after reset to origin/develop. Confirm HEAD before committing to avoid duplicate dual-clone commits.

No jira integration on this project — claim step explicitly skipped.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-01T02:16:16Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-31T21:25:00Z | 2026-06-01T01:25:19Z | 4h |
| red | 2026-06-01T01:25:19Z | 2026-06-01T01:35:13Z | 9m 54s |
| green | 2026-06-01T01:35:13Z | 2026-06-01T01:54:40Z | 19m 27s |
| spec-check | 2026-06-01T01:54:40Z | 2026-06-01T01:58:26Z | 3m 46s |
| verify | 2026-06-01T01:58:26Z | 2026-06-01T02:01:57Z | 3m 31s |
| review | 2026-06-01T02:01:57Z | 2026-06-01T02:14:03Z | 12m 6s |
| spec-reconcile | 2026-06-01T02:14:03Z | 2026-06-01T02:16:16Z | 2m 13s |
| finish | 2026-06-01T02:16:16Z | - | - |

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (1 Major, deferred — does not block review)
**Mismatches Found:** 1

All five ACs (AC-1 pronoun overwrite, AC-2 role overwrite, AC-3 applied span + GM-panel route projection, AC-4 bounded to identity fields, AC-5 agree/empty no-op) and all three edge cases (same-turn last-wins, world_authored protected, no-merge) are satisfied — verified against the diff (`narration_apply.py` pool-hit branch, `session_helpers._detect_npc_identity_drift` applied marker, `npc.py` route extractor). The concrete session-894 Sitä-minutta failure (a pool-hit member) is fixed. OTEL contract met: `applied` rides the span and the route projects it.

- **Promoted-NPC drift (`npcs_hit`) stays warn-only while the prompt renders `Npc.pronouns`** (Different behavior — Behavioral, Major)
  - Spec: context-story-72-7.md, "Npc-hit branch is pronoun-only" — *"mirror it onto `npcs_hit` pronouns **if the dossier-injection path feeds `Npc` pronouns back to the prompt** (37-44)."*
  - Code: the `npcs_hit` branch passes `applied=False` and does **not** overwrite `Npc.pronouns`. Dev's deferral rationale ("the prompt roster renders `npc_pool`, not `Npc`") is **factually incorrect**: `session_helpers.py:1180` passes `npcs=list(snapshot.npcs)` into `TurnContext`, and `prompt_framework/core.py:515-533` renders each `npc.pronouns` into the "KNOWN NPCS — Canonical Identity" section. So the context's conditional for mirroring **is met** — a promoted NPC that drifts keeps stale pronouns in the prompt (the same class of bug, on the high-engagement path: promotion happens on player interest per 72-1).
  - Recommendation: **D — Defer.** The clean fix is entangled with **72-2** (npcs↔npc_pool reconciliation), which is explicitly out of scope for 72-7: a promoted NPC keeps a *shadowed* pool member that *also* renders, so overwriting only `Npc.pronouns` would produce a contradictory two-line roster for one person. Resolving requires the dual-store reconciliation 72-2 owns. The hard ACs pass and the documented failure is fixed, so this proceeds to review rather than blocking. Tracked as a Delivery Finding (below) for a 72-2-adjacent follow-up. The inaccurate rationale in the Dev deviation is corrected here for the record.

**Decision:** Proceed to review (TEA verify next).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (3 source, 3 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | medium: extract a `_upsert_identity_field` helper for the symmetric role/pronouns overwrite (~15 lines, narration_apply.py ~1716–1731) |
| simplify-quality | clean | applied marker threading consistent across all call sites; tests well-structured |
| simplify-efficiency | clean | no over-engineering; `applied` flag is a direct answer to a specific need, `**attrs` pass-through is standard |

**Applied:** 0 high-confidence fixes (none found)
**Flagged for Review:** 1 medium-confidence (reuse helper extraction)
**Noted:** 0 low-confidence
**Reverted:** 0

**Overall:** simplify: clean — the single medium finding is NOT auto-applied (per verify protocol). Judgment: the duplication is symmetric, locally readable, ~15 lines in one location, and the pattern does not repeat elsewhere; extracting a helper for a 3-point change is borderline over-engineering (the efficiency lens concurred). Left for Reviewer discretion.

**Quality Checks:** ruff check clean; ruff format clean (3 source files already formatted); affected-trio tests 52/52 GREEN (serial, run `72-7-tea-verify`).

**Pre-existing flake note:** the full parallel `tests/server/` run still hits the unrelated OTEL `force_flush`/`_export_lock` deadlock (~18 span-count tests) — reproduced on the clean baseline, not from 72-7 (logged as a Delivery Finding). Affected-file verification was run serially to isolate the story's surface.

**Handoff:** To Reviewer (The Merovingian) for code review.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Behavioral change to the NPC identity-drift seam (warn-only → authoritative overwrite) with a mandatory OTEL contract. TDD applies.

**Test Files:**
- `tests/server/test_npc_identity_drift.py` — extended (per story context "extend the existing fixture shape"). +9 new behavioral/span tests, 1 pre-existing test rewritten.

**Tests Written:** 9 new failing tests + 1 rewrite covering all 5 ACs + 3 edge cases.
**Status:** RED (9 failing / 20 passing — all failures are clean assertion errors, verified by testing-runner run `72-7-tea-red`; no collection/import/fixture errors).

### AC / Rule Coverage

| AC / Edge | Test | Status |
|-----------|------|--------|
| AC-1 pronoun overwrite | `test_drift_overwrites_canonical_pronouns` | failing |
| AC-2 role overwrite | `test_drift_overwrites_canonical_role` | failing |
| AC-2 (Frandrew demotion) | `test_explicit_drift_overwrites_canonical_pronouns_and_role` (rewrite) | failing |
| AC-3 applied span old→new | `test_drift_applied_span_carries_applied_marker_and_old_new` | failing |
| AC-3 GM-panel projection | `test_npc_reinvented_route_projects_applied_marker` | failing |
| AC-4 bounded (disp/appearance) | `test_drift_overwrite_leaves_mechanical_state_and_appearance_untouched` | failing |
| AC-5 agree = no-op | `test_agreeing_mention_performs_no_overwrite_and_no_span` | passing (regression guard) |
| AC-5 empty = no-op | `test_empty_mention_fields_perform_no_overwrite_and_no_span` | passing (regression guard) |
| Edge: same-turn last-wins | `test_conflicting_drift_within_turn_last_mention_wins` | failing |
| Edge: world_authored protected | `test_drift_does_not_overwrite_world_authored_identity` | failing |
| Edge: no merge on match | `test_drift_to_matching_values_does_not_merge_pool_entries` | failing |

**Server-rule compliance:** Span assertions via the `otel_capture` in-memory exporter and a
direct route-extractor unit test — **no source-text wiring tests** (server CLAUDE.md). No
`caplog`-only assertions for the new behavior; the GM-panel contract is asserted on the span +
route projection (OTEL Observability Principle).
**Self-check:** 1 vacuous assertion caught and removed during authoring (a tautological
`role == x or role == y`); 1 dead placeholder helper removed. No `let _ =` / `assert True` /
always-None assertions remain. Lint clean (`ruff check`).

**Implementation pointer for Dev (Agent Smith):** the real seam is
`narration_apply._apply_npc_mentions` pool-hit branch (~1697–1704, currently additive fill-empty)
+ `session_helpers._detect_npc_identity_drift` (2004) + `npc_reinvented_span` /
`SPAN_ROUTES[SPAN_NPC_REINVENTED]` in `telemetry/spans/npc.py`. **Not** the Rust-derived
`npc_identity/resolver.py` path from the SM session header — that module does not exist.

**Handoff:** To Dev (Agent Smith) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/narration_apply.py` — pool-hit upsert now overwrites disagreeing role/pronouns on narrator-sourced members (gated `drawn_from != "world_authored"`); appearance stays additive; threads `applied` to the drift detector on both branches (pool-hit = gate result, npcs-hit = False).
- `sidequest/server/session_helpers.py` — `_detect_npc_identity_drift` gains an `applied` param, threaded onto the `npc.reinvented` span + log line.
- `sidequest/telemetry/spans/npc.py` — `SPAN_ROUTES[SPAN_NPC_REINVENTED]` extractor projects the `applied` marker into the GM-panel event.
- `tests/server/test_dispatch.py`, `tests/server/test_npc_pool_narration_apply.py` — updated two sibling tests that encoded the pre-72-7 frozen contract (see Design Deviations).

**Tests:** GREEN.
- Target `tests/server/test_npc_identity_drift.py`: 29/29.
- Affected trio (target + 2 updated siblings): 52/52 (serial, `-n0`).
- Pre-existing, non-72-7 flake: ~18 OTEL span-count tests deadlock under the full parallel run (`force_flush`/`_export_lock`), reproduced on the clean baseline — see Delivery Findings.

**Branch:** `feat/72-7-npc-identity-drift` (pushed → origin, commit `18ff004`).

**AC status:** AC-1✓ AC-2✓ AC-3 (span `applied`+old/new ✓, route projection ✓) AC-4 (bounded — disposition/appearance untouched ✓) AC-5 (agree/empty no-op ✓). Edges: same-turn last-wins ✓, world_authored protected ✓, no-merge ✓.

**OTEL:** the `npc.reinvented` span now carries `applied` (True overwrite / False suppressed-or-warn-only) and the route projects it — the GM panel can distinguish "canonical record moved" from "mismatch merely noticed" (OTEL Observability Principle).

**Handoff:** To verify (The Architect — simplify + quality-pass).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Gap** (non-blocking): The `SPAN_ROUTES[SPAN_NPC_REINVENTED]` extractor projects a fixed
  dict that drops unknown span attributes, so an `applied` marker on the span is invisible to
  the GM panel until the route extractor is also updated. Affects
  `sidequest/telemetry/spans/npc.py` (add `applied` to the route `extract` lambda, not only to
  the span emission). *Found by TEA during test design.*
- **Improvement** (non-blocking): If Dev mirrors authoritative overwrite onto the `npcs_hit`
  branch (`Npc.pronouns`), it must emit its own applied-drift span and add coverage — the
  current 72-7 tests only assert the `pool_hit` write site. Affects
  `sidequest/server/narration_apply.py` (~1614–1681 npcs_hit branch). *Found by TEA during test design.*
- **Question** (non-blocking): The `world_authored`-suppression policy (see Design Deviations)
  is a TEA call; if Dev/Reviewer prefers gating on a different `drawn_from` set (e.g. also
  protecting `legacy_registry`), the edge test `test_drift_does_not_overwrite_world_authored_identity`
  is the single place to adjust. *Found by TEA during test design.*

### Dev (implementation)

- **Gap** (non-blocking, PRE-EXISTING — not introduced by 72-7): ~18 OTEL span-count tests fail
  under the full parallel (`-n auto`) `tests/server/` run via a `force_flush` → batch-processor
  `_export_lock` deadlock in the `_execute_narration_turn` flush path, plus global-TracerProvider
  span pollution. Reproduced identically on the clean baseline (impl stashed) — e.g.
  `test_turn_manager_round_invariant.py::test_round_invariant_span_fires_once_per_narration_turn`
  and `test_71_15_room_graph_movement_side_effects.py::test_room_graph_transition_emits_transition_tick_span`
  hang/timeout in `flush(timeout_millis=200)`. Affects the test OTEL setup
  (`websocket_session_handler.py:2277` flush + the BatchSpanProcessor under xdist), not 72-7
  code. The three 72-7-affected files pass 52/52 serially. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `npc_reinvented_span` still hard-codes `severity="warning"`
  even for `applied=True` corrections (a successful overwrite is arguably `info`, not a warning).
  Left as-is because the existing `caplog.at_level(WARNING)` tests depend on the warning level.
  Affects `sidequest/telemetry/spans/npc.py::npc_reinvented_span`. *Found by Dev during implementation.*

### Architect (spec-check)

- **Gap** (non-blocking, deferred to 72-2-adjacent follow-up): Promoted-NPC drift via the
  `npcs_hit` branch stays warn-only, but the prompt's "KNOWN NPCS — Canonical Identity" section
  renders `Npc.pronouns` (`session_helpers.py:1180` → `prompt_framework/core.py:515-533`), so a
  drifted promoted NPC keeps stale pronouns in the narrator prompt. The story context's condition
  for mirroring the overwrite onto `npcs_hit` is therefore met. A correct fix entangles 72-2
  (npcs↔npc_pool reconciliation): a promoted NPC keeps a shadowed pool member that *also* renders,
  so a `Npc.pronouns`-only overwrite would yield a contradictory two-line roster. Affects
  `sidequest/server/narration_apply.py` (npcs_hit branch ~1619) + the 72-2 reconcile seam.
  *Found by Architect during spec-check.* (Corrects the Dev deviation's "renders npc_pool, not Npc" rationale.)

### TEA (test verification)

- **Improvement** (non-blocking): simplify-reuse flagged a medium-confidence helper extraction
  for the symmetric role/pronouns overwrite (`narration_apply.py` ~1716–1731). Not applied (per
  verify protocol medium-confidence rule; ~15 readable lines, no repeat elsewhere). Left for
  Reviewer discretion. *Found by TEA during test verification.*

### Reviewer (code review)

- **Improvement** (non-blocking): Whitespace-only narrator `role`/`pronouns` overwrites canonical
  identity and fires a spurious drift span (violates "empty = no opinion"); transient/self-correcting
  but worth a guard. Affects `sidequest/server/narration_apply.py:1716,1724` +
  `session_helpers.py:2033` (add `.strip()` to the truthy guards). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `applied` rides `npc_reinvented_span` via `**attrs`, not an explicit
  param — a refactor could silently revert the GM-panel marker to `False`. Affects
  `sidequest/telemetry/spans/npc.py:543` (promote `applied: bool = False` to an explicit keyword).
  *Found by Reviewer during code review.*
- **Gap** (non-blocking): Stale docstring — `_apply_npc_mentions` step 2 still says "additive upsert …
  existing values win on conflict," reversed by 72-7. Affects `sidequest/server/narration_apply.py:1539-1541`.
  *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Test robustness — AC-1/AC-2 request `otel_capture` without asserting a
  span; conflicting-drift asserts span count not per-span attrs; dispatch overwrite test asserts state not
  span; world_authored edge omits the role path. Affects `tests/server/test_npc_identity_drift.py`,
  `tests/server/test_dispatch.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, PRE-EXISTING): `NpcPoolMember.drawn_from` is a bare `str` compared to
  literals at 6 sites — now load-bearing for the author-protection gate; a `Literal[...]` would make it
  type-safe. Affects `sidequest/game/npc_pool.py:53`. *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

7 deviations

- **Rewrote the warn-only enshrining test instead of adding alongside it**
  - Rationale: The old test encoded the exact behavior this story reverses; preserving it would have made GREEN impossible. Per TEA rule "do not preserve broken tests." Appearance assertion retained (stays additive).
  - Severity: minor
  - Forward impact: none — the scenario (Frandrew captain→grease-monkey) is still covered, now asserting the new contract.
- **Chose a policy for the player/world-authored drift edge case (left open by spec)**
  - Rationale: Aligns with SOUL "Yes, And" (canonize what the human author introduced) + "No Silent Fallbacks" (suppressed ≠ silent — span records applied=False). Narrow, single-tag gate; no new field needed.
  - Severity: major (Dev must implement this gate exactly; it shapes the apply logic)
  - Forward impact: Dev implements the `drawn_from` gate at the upsert site and threads `applied` (True/False) onto the span + route extractor.
- **Scoped RED tests to the pool-hit write site; npcs_hit pronoun-overwrite left to Dev discretion**
  - Rationale: The session-894 failure and all 5 ACs are expressible on pool_hit; `npcs_hit` mirroring is conditional on the dossier path and is explicitly discretionary. Avoids over-constraining Dev / inventing a string `role` on `Npc`.
  - Severity: minor
  - Forward impact: If Dev mirrors overwrite onto `npcs_hit.pronouns`, it must add its own span/test; flagged as a non-blocking Delivery Finding below.
- **Updated two sibling tests that enshrined the pre-72-7 "canonical frozen" contract**
  - Rationale: These sibling tests (not touched by TEA, who only saw `test_npc_identity_drift.py`) encode the exact behavior 72-7 reverses; GREEN is impossible while they assert the frozen contract. Story scope outranks the old test. Surfaced by the testing-runner full-suite regression check.
  - Severity: minor
  - Forward impact: none — both still guard the new contract (overwrite role, fill-empty pronouns, no duplicate entry).
- **npcs_hit branch left warn-only (no Npc identity overwrite) — took the discretionary call**
  - Rationale: Minimal change that satisfies all ACs; avoids a second write site and a phantom string `role` on `Npc`. Matches TEA's scoping.
  - Severity: minor
  - Forward impact: If a future story feeds `Npc.pronouns` (not pool) into the prompt, mirror the overwrite there with its own span (see Delivery Finding).
- **Implementation seams diverged from the session-header technical approach (superseded by context-story)**
  - Rationale: The session-header technical approach was a Rust-reference-derived guess; the higher-authority `context-story-72-7.md` (spec-authority rank 2 > session-header improv) specified the actual Python seams, and SM/TEA both flagged the path as unverified. The implementation correctly followed the context-story. Reusing the existing `npc.reinvented` span (rather than minting a parallel event) is the right call — one drift channel, `applied` discriminates warn-only vs applied (DRY, single GM-panel filter).
  - Severity: minor (documentation/traceability only — no functional gap; all ACs met)
  - Forward impact: none. Future readers tracing "npc_identity_drift_applied" will find nothing — the canonical event is `npc.reinvented` with `applied=true`.
- **Story partially closes the drift class: promoted-NPC (`npcs_hit`) drift remains stale — deferred to 72-2**
  - Rationale: A correct fix entangles **72-2** (npcs↔npc_pool reconciliation): a promoted NPC keeps a shadowed pool member that also renders, so overwriting only `Npc.pronouns` would produce a contradictory two-line roster. That reconciliation is explicitly out of scope for 72-7. The 5 ACs (all pool-hit) and the concrete session-894 failure are fully satisfied.
  - Severity: major (a real, anticipated gap on the high-engagement path — promoted NPCs are the ones players interact with most)
  - Forward impact: **72-2-adjacent follow-up required** — extend authoritative drift to the `npcs_hit` path (pronoun-only on `Npc`) together with the npcs↔npc_pool single-source reconciliation, so the promoted NPC and its shadowed pool member cannot present divergent identities in the roster. Tracked as a Delivery Finding (Architect spec-check).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Rewrote the warn-only enshrining test instead of adding alongside it**
  - Spec source: context-story-72-7.md, AC-1 / AC-2
  - Spec text: "the canonical `pool_hit.pronouns` is **overwritten** … (Today it stays `they/them`)"
  - Implementation: `test_explicit_drift_does_not_overwrite_canonical_pronouns` (from 37-44, which asserted the canonical value stays frozen) was renamed to `test_explicit_drift_overwrites_canonical_pronouns_and_role` and its assertions flipped to the overwrite behavior 72-7 introduces.
  - Rationale: The old test encoded the exact behavior this story reverses; preserving it would have made GREEN impossible. Per TEA rule "do not preserve broken tests." Appearance assertion retained (stays additive).
  - Severity: minor
  - Forward impact: none — the scenario (Frandrew captain→grease-monkey) is still covered, now asserting the new contract.

- **Chose a policy for the player/world-authored drift edge case (left open by spec)**
  - Spec source: context-story-72-7.md, "Edge cases to cover — Drift on a player-named NPC"
  - Spec text: "decide and test the policy: narrator drift should **not** silently overwrite a player-authored identity. Either suppress … or gate on `drawn_from` — assert the chosen behavior."
  - Implementation: Test `test_drift_does_not_overwrite_world_authored_identity` encodes the policy: **suppress the overwrite when `drawn_from == "world_authored"`** (human-authored identity), but still emit the `npc.reinvented` span with `applied=False` so the disagreement stays GM-panel-visible. All other `drawn_from` origins (narrator_invented, dialogue_extraction, name_generator, legacy_registry) overwrite.
  - Rationale: Aligns with SOUL "Yes, And" (canonize what the human author introduced) + "No Silent Fallbacks" (suppressed ≠ silent — span records applied=False). Narrow, single-tag gate; no new field needed.
  - Severity: major (Dev must implement this gate exactly; it shapes the apply logic)
  - Forward impact: Dev implements the `drawn_from` gate at the upsert site and threads `applied` (True/False) onto the span + route extractor.

- **Scoped RED tests to the pool-hit write site; npcs_hit pronoun-overwrite left to Dev discretion**
  - Spec source: context-story-72-7.md, "Npc-hit branch is pronoun-only" / Assumptions
  - Spec text: "at minimum the pool_hit path must overwrite; mirror it onto `npcs_hit` pronouns if the dossier-injection path feeds `Npc` pronouns back to the prompt … is a design call for TEA/Dev."
  - Implementation: All 72-7 tests target the `pool_hit` branch (the authoritative write site). No test asserts `npcs_hit` (`Npc.pronouns`) overwrite.
  - Rationale: The session-894 failure and all 5 ACs are expressible on pool_hit; `npcs_hit` mirroring is conditional on the dossier path and is explicitly discretionary. Avoids over-constraining Dev / inventing a string `role` on `Npc`.
  - Severity: minor
  - Forward impact: If Dev mirrors overwrite onto `npcs_hit.pronouns`, it must add its own span/test; flagged as a non-blocking Delivery Finding below.

### Dev (implementation)

- **Updated two sibling tests that enshrined the pre-72-7 "canonical frozen" contract**
  - Spec source: context-story-72-7.md, AC-1 / AC-2 (story scope — highest authority)
  - Spec text: "the canonical `pool_hit.role` is **overwritten** … on disagreeing re-mention (was fill-empty)."
  - Implementation: `test_dispatch.py::test_apply_npc_pool_existing_is_additive_only` and `test_npc_pool_narration_apply.py::test_cite_pool_member_additively_upserts_identity_fields` both asserted role stays frozen on a disagreeing re-mention (the old 37-44 discipline). Renamed both to `_overwrites_role*` / `_upserts_identity_fields` and flipped the role assertion to expect the overwrite (`legacy_registry` is narrator-sourced). Pronoun fill-empty + no-duplicate assertions retained.
  - Rationale: These sibling tests (not touched by TEA, who only saw `test_npc_identity_drift.py`) encode the exact behavior 72-7 reverses; GREEN is impossible while they assert the frozen contract. Story scope outranks the old test. Surfaced by the testing-runner full-suite regression check.
  - Severity: minor
  - Forward impact: none — both still guard the new contract (overwrite role, fill-empty pronouns, no duplicate entry).

- **npcs_hit branch left warn-only (no Npc identity overwrite) — took the discretionary call**
  - Spec source: context-story-72-7.md, "Npc-hit branch is pronoun-only" (TEA/Dev discretion)
  - Spec text: "mirror it onto `npcs_hit` pronouns *if* the dossier-injection path feeds `Npc` pronouns back to the prompt … a design call for TEA/Dev."
  - Implementation: The `npcs_hit` detector call passes `applied=False`; no write onto `Npc.pronouns`. Authoritative overwrite is pool-hit-only (the canonical identity scaffold). The prompt roster renders `npc_pool` (per the existing 37-44 dossier tests), so the pool-hit overwrite already closes the drift loop.
  - Rationale: Minimal change that satisfies all ACs; avoids a second write site and a phantom string `role` on `Npc`. Matches TEA's scoping.
  - Severity: minor
  - Forward impact: If a future story feeds `Npc.pronouns` (not pool) into the prompt, mirror the overwrite there with its own span (see Delivery Finding).

### Reviewer (audit)

- **TEA: rewrote the warn-only enshrining test** → ✓ ACCEPTED by Reviewer: correct — the story reverses that behavior; preserving the old assertion would make GREEN impossible. The Frandrew scenario is still covered.
- **TEA: world_authored suppression policy** → ✓ ACCEPTED by Reviewer: `world_authored` is the correct human-authoring tag to protect; `legacy_registry`/`narrator_invented`/`dialogue_extraction` are narrator-origin and correctly overwritable. (The silent-failure subagent's "legacy_registry is author-curated" claim was dismissed — legacy_registry is the migrated *narrator* registry, not hand-authoring.) Note: the gate is a denylist (`!= world_authored`) on a stringly-typed field — see the non-blocking type finding recommending a `Literal`.
- **TEA: scoped RED tests to pool_hit** → ✓ ACCEPTED by Reviewer: matches the spec's explicit discretion; the npcs_hit/promoted-NPC gap is separately tracked (deferred to 72-2 by Architect spec-check).
- **Dev: updated two sibling tests (frozen-contract)** → ✓ ACCEPTED by Reviewer: necessary — both encoded the reversed contract; the rewrites assert the new behavior correctly (verified GREEN, 52/52).
- **Dev: npcs_hit left warn-only** → ✓ ACCEPTED by Reviewer **with correction already on record**: the deferral is sound, but the stated rationale ("the prompt roster renders `npc_pool`, not `Npc`") is factually wrong — the roster renders both (`prompt_framework/core.py:515-533`). Neo corrected this in spec-check and deferred the real gap to 72-2. No further action needed in this story.

### Architect (reconcile)

Existing TEA/Dev deviation entries reviewed: all 6 fields present and accurate; spec sources (`context-story-72-7.md`) verified real; spec text quoted accurately; implementation descriptions match the shipped code. The Dev "npcs_hit warn-only" entry carries a factually-incorrect rationale (roster renders both stores), already corrected in the Architect spec-check assessment and the Reviewer audit — annotated, not deleted. No AC deferrals to verify: AC-1 through AC-5 are all DONE (no DESCOPED/deferred ACs in the accountability record).

Missed deviations added below for the definitive manifest:

- **Implementation seams diverged from the session-header technical approach (superseded by context-story)**
  - Spec source: `.session/72-7-session.md` "Story Description / Technical approach" (the SM-authored header, lines ~60-81)
  - Spec text: "The fix lives in `sidequest/game/npc_identity.rs` … post-ADR-082 it's in `sidequest-server/sidequest/game/npc_identity/resolver.py` … `NpcIdentityResolver.resolve_drift()` … Call a new `apply_identity_drift()` method … Emit OTEL watcher event: `npc_identity_drift_applied`."
  - Implementation: None of those names exist. The fix lives in `narration_apply._apply_npc_mentions` (pool-hit upsert) + `session_helpers._detect_npc_identity_drift`; the OTEL marker is an `applied` attribute on the **existing** `npc.reinvented` span (not a new `npc_identity_drift_applied` event); the proposed `NpcIdentityResolver`/`resolve_drift`/`apply_identity_drift` symbols were never created (grep-confirmed empty).
  - Rationale: The session-header technical approach was a Rust-reference-derived guess; the higher-authority `context-story-72-7.md` (spec-authority rank 2 > session-header improv) specified the actual Python seams, and SM/TEA both flagged the path as unverified. The implementation correctly followed the context-story. Reusing the existing `npc.reinvented` span (rather than minting a parallel event) is the right call — one drift channel, `applied` discriminates warn-only vs applied (DRY, single GM-panel filter).
  - Severity: minor (documentation/traceability only — no functional gap; all ACs met)
  - Forward impact: none. Future readers tracing "npc_identity_drift_applied" will find nothing — the canonical event is `npc.reinvented` with `applied=true`.

- **Story partially closes the drift class: promoted-NPC (`npcs_hit`) drift remains stale — deferred to 72-2**
  - Spec source: `context-story-72-7.md`, "Npc-hit branch is pronoun-only"
  - Spec text: "mirror it onto `npcs_hit` pronouns **if the dossier-injection path feeds `Npc` pronouns back to the prompt** (37-44) … a design call for TEA/Dev."
  - Implementation: `npcs_hit` stays warn-only (`applied=False`, no write). The condition in the spec text is in fact MET — `session_helpers.py:1180` passes `npcs` into `TurnContext` and `prompt_framework/core.py:515-533` renders `Npc.pronouns` into the canonical-identity prompt section — so a promoted NPC that drifts keeps stale pronouns in the prompt.
  - Rationale: A correct fix entangles **72-2** (npcs↔npc_pool reconciliation): a promoted NPC keeps a shadowed pool member that also renders, so overwriting only `Npc.pronouns` would produce a contradictory two-line roster. That reconciliation is explicitly out of scope for 72-7. The 5 ACs (all pool-hit) and the concrete session-894 failure are fully satisfied.
  - Severity: major (a real, anticipated gap on the high-engagement path — promoted NPCs are the ones players interact with most)
  - Forward impact: **72-2-adjacent follow-up required** — extend authoritative drift to the `npcs_hit` path (pronoun-only on `Npc`) together with the npcs↔npc_pool single-source reconciliation, so the promoted NPC and its shadowed pool member cannot present divergent identities in the roster. Tracked as a Delivery Finding (Architect spec-check).

No further undocumented deviations found.