---
story_id: "45-6"
jira_key: null
epic: "45"
workflow: "wire-first"
---

# Story 45-6: Chargen partial-completion path leaves resolved_archetype=NULL

## Story Details
- **ID:** 45-6
- **Epic:** 45 — Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup
- **Jira Key:** (no issue created; skip Jira claim per setup)
- **Workflow:** wire-first
- **Priority:** p1
- **Points:** 2
- **Type:** bug
- **Status:** setup
- **Repos:** server (chargen pipeline)

## Summary
Playtest 3 evropi session had a character (pumblestone_sweedlewit) with `resolved_archetype=NULL`, no hp/ac, and never advanced past opening narrative. The chargen pipeline has a success path that completes without binding an archetype. Identify the path and require archetype resolution before chargen can complete.

## Acceptance Criteria

### AC1: Identify the partial-completion path
Audit the chargen pipeline in `sidequest-server/sidequest/game/character_builder.py` and the session init path in `session.py` to find the code path that permits chargen to complete (CHARGEN → READY state transition) without a resolved_archetype binding. Document the exact code location (line number, function name, decision point). Include sample input that triggers the path.

**Call Site:** Character state machine: `_maybe_advance_chargen_state()` at session_handler.py or character_builder.py (whichever holds the transition logic). Wire-first requirement: boundary test must exercise this transition from an HTTP/WS handler, not a direct function call.

### AC2: Require archetype resolution at chargen exit
Add a gate before the CHARGEN → READY transition that asserts `resolved_archetype is not None`. If the gate fails, emit an OTEL span with `chargen.archetype_required` and the current character state, then block the transition with a user-facing error message (e.g., "Character must choose an archetype before continuing").

**Call Site:** Character state machine exit gate; OTEL span wraps the assertion. Boundary test confirms the gate fires on chargen completion.

### AC3: Regression test — chargen cannot complete without archetype
Write a test that exercises the chargen completion path (full character creation flow) and asserts that without an archetype, the character state machine rejects the transition. Test must use the outermost reachable layer (session handler / WS dispatch, not direct call to the state machine). Include a second assertion that WITH a resolved archetype, the transition succeeds.

**Test Location:** `tests/server/test_chargen_archetype_gate.py` or `tests/server/test_45_6_chargen_archetype_gate.py` (wire-first convention).

### AC4: Wire verification — all new exports have consumers
If the gate function is extracted as a public function, at least one non-test consumer must exist in production code. The session handler or character builder must call it. No stubs, no "wire in next story."

## Story Context

### Background: Playtest 3 observations
From playtest-3-closeout session (2026-04-19 evropi), the character pumblestone_sweedlewit loaded at READY state but reported:
- resolved_archetype: null
- hp: 0, ac: 0 (both undefined, not resolved)
- character state: never fired opening narration; session init failed to complete chargen

The four playtest saves (prot_thokk, hant, pumblestone, rux) all created in 16:30-16:31 UTC cluster. Three of the four completed chargen normally (hp/ac resolved). pumblestone alone has null archetype — suggesting a rare code path that skips the archetype binding step.

### Hypothesis
The chargen pipeline calls a sequence of state-advance functions. One of them — likely `_apply_character_class`, `_apply_race`, or `_apply_archetype` — is conditional or has an early-return guard. If the condition isn't met, chargen completes without running the archetype binding step.

Alternatively, chargen completion doesn't require archetype resolution; archetype is assigned later (on opening narration or first action). If that's the design, it's a silent failure — the opening narration never fires because the narrator can't describe a character without a class.

### Related Stories
- 37-7 (opened for chargen issues, not yet scoped)
- 45-7 (race-aware character description template; already shipped, tested via playtest-3 data)

## Workflow Tracking

**Workflow:** wire-first  
**Phase:** finish  
**Phase Started:** 2026-04-28T15:16:57Z  
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28 | 2026-04-28T13:53:00Z | 13h 53m |
| red | 2026-04-28T13:53:00Z | 2026-04-28T14:09:00Z | 16m |
| green | 2026-04-28T14:09:00Z | 2026-04-28T14:26:48Z | 17m 48s |
| review | 2026-04-28T14:26:48Z | 2026-04-28T14:43:19Z | 16m 31s |
| red | 2026-04-28T14:43:19Z | 2026-04-28T14:57:00Z | 13m 41s |
| green | 2026-04-28T14:57:00Z | 2026-04-28T15:05:58Z | 8m 58s |
| review | 2026-04-28T15:05:58Z | 2026-04-28T15:16:57Z | 10m 59s |
| finish | 2026-04-28T15:16:57Z | - | - |

## Sm Assessment

**Story scope is well-bounded.** Playtest 3 evropi gave us a single concrete failure case: pumblestone_sweedlewit reached READY with `resolved_archetype=NULL`, hp=0, ac=0, no opening narration. Three other characters in the same cluster completed chargen normally — so the gap is a rare/conditional code path, not a wholesale missing system.

**Approach:** Audit the chargen state machine for the path that permits CHARGEN → READY without archetype binding, gate it with an explicit assertion, emit an OTEL span on rejection, and prove the gate via a boundary test exercising the WS/session handler (not the state machine directly). Wire-first discipline applies — no extracted helpers without a non-test consumer.

**Risk:** The hypothesis section flags two possibilities (conditional skip vs. lazy archetype assignment by design). TEA's red phase should pin down which is true before Dev writes the gate — if archetype is assigned later by design, the gate goes at a different layer.

**Repos:** sidequest-server only (chargen pipeline, session handler, OTEL). Content repo is not in scope despite being listed in setup; archetype data shape is read-only.

**Next:** Hand off to TEA (Fezzik) for the red phase. Boundary test must drive chargen via outermost reachable layer.

## Delivery Findings

No upstream findings at setup.

### TEA (test design)
- **Improvement** (non-blocking): The story-context spec names a new helper `_gate_archetype_resolution`, but says nothing about whether the inner-resolver event `character_creation.archetype_resolution_failed` should also fire on the resolver-raised branch. Tests assert it MUST still fire (no regression on Sebastien's existing dashboard); Dev should preserve the existing `add_event` call inside `_resolve_character_archetype`'s `except GenreValidationError` block. Affects `sidequest-server/sidequest/server/websocket_session_handler.py:593-610`. *Found by TEA during test design.*
- **Question** (non-blocking): The story-context spec assumes `chargen.archetype_gate_evaluated` and `chargen.archetype_gate_blocked` are routed as `state_transition` events. The route's `extract` lambda shape is not specified — Dev should pattern-match the `npc.auto_registered` precedent at `spans.py:259-271` (component, field, op, plus the documented attributes from the story-context table). The wire-completeness test will catch any new SPAN_* constant without a routing decision. *Found by TEA during test design.*

### Dev (green)
- **Gap** (non-blocking): The pack `caverns_and_claudes` declared `archetype_constraints` (axes opted-in) but its chargen scenes (`char_creation.yaml`) never populated `jungian_hint` / `rpg_role_hint`. Without the gate this shipped a `resolved_archetype=None` for every caverns character — same failure class as evrópí pumblestone. Fixed by tagging scene 1 (`the_roll`) with `hero` / `jack_of_all_trades` (canonical Delver pairing). Affects `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml`. Recommend a follow-up audit of every other pack-with-axes (heavy_metal/evropi already in scope per Story 45-6 context section "Audit `evropi` chargen scenes"; out of scope for this story but the same audit applies to `space_opera`, `elemental_harmony`, and any pack listed under the heavy_metal world overlays). *Found by Dev during green.*
- **Audit finding** (per AC scope-boundary "Audit `evropi` chargen scenes"): `sidequest-content/genre_packs/heavy_metal/char_creation.yaml` sets both `jungian_hint` and `rpg_role_hint` on the class scene (Paladin → hero/tank, Warlock → outlaw/..., etc). The `worlds/evropi/char_creation.yaml` overlay (origins scene) sets `jungian_hint` only — `rpg_role_hint` arrives from the heavy_metal class-scene later in the walk. Pumblestone's path almost certainly hit one of the two `allows_freeform: true` non-standard-race paths in the evropi origins scene where the class scene either was skipped, returned without hints, or produced an effects payload with an empty `rpg_role_hint`. **The bug surface is missing-axes-on-scene, not pack-axis-config.** Per story scope: fixing evropi content is deferred to a content-pack story. The new gate now blocks the failure mode, so any future evropi-shaped chargen failure produces a typed ERROR frame instead of a wedged session. *Found by Dev during green.*

### Reviewer (code review)
- **Improvement** (non-blocking): The gate's `block_reason="resolver_raised"` collapses three distinct resolver failure modes (forbidden-pair, unknown-axis-id, world-funnel-forbidden — see `sidequest/genre/archetype/shim.py:99-115`) into one bucket. The legacy `character_creation.archetype_resolution_failed` event preserves the underlying `error: str(exc)` on the parent span, so the data is recoverable, but the gate's own blocked span doesn't carry it. Affects `sidequest/server/websocket_session_handler.py:768-800` (the gate's blocked-span attributes — could include `inner_error: str(exc)` if the resolver-raised exception is captured at the call site). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): No test asserts the gate's contract with `apply_archetype_resolved` — specifically, that `archetype_provenance` is set on the OK_RESOLVED branch. Today `apply_archetype_resolved` sets both `resolved_archetype` and `archetype_provenance` atomically; a future refactor that splits them would silently break the gate's invariant (the gate would see a resolved name and pass, but downstream consumers reading `archetype_provenance` would see `None`). Recommend AC1 also assert `character.archetype_provenance is not None`. Affects `tests/server/test_45_6_chargen_archetype_gate.py::TestArchetypeGateOkResolved`. *Found by Reviewer during code review.*
- **Gap** (non-blocking): Comment at line 3 of `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml` says "3 scenes: roll stats, roll equipment, enter the dungeon" but the file has 4 scenes (the_roll, pronouns, the_kit, the_mouth). Pre-existing comment, not introduced by 45-6 — but a follow-up content edit could correct it. *Found by Reviewer during code review.*

### TEA (test design — round 2)
- No new upstream findings during round-2 rework. The Reviewer's findings drove all test additions/strengthenings; no spec ambiguity or additional gaps surfaced.

### Reviewer (code review — round 2)
- **Improvement** (non-blocking): Round-2's gate-method rewrite shifted the `_resolve_character_archetype` early-return positions from 574/579/595 to 581/586/602 — a 7-line drift across the function. The 5 line-number citations in the new gate body and inline comments were not re-updated. **Recommendation:** future references should use symbolic anchors (function/method names + branch labels) rather than absolute line numbers — this is the third round of line-number drift on this file across the story. Affects `sidequest/server/websocket_session_handler.py` lines 668, 676, 679, 742, 886. *Found by Reviewer during round-2 code review.*
- **Improvement** (non-blocking): The OK_NO_AXES condition docstring at `websocket_session_handler.py:657-661` says `(base_archetypes is None and archetype_constraints is None)` (AND), but the code computes `not pack_has_axes` which is OR. The CODE matches the original story-context spec ("Pack lacks resolver inputs"); the DOCSTRING used the wrong logical operator. A pack with only one axis file shipped + scene that didn't form a pair would silently OK_NO_AXES per the code, but a maintainer reading the docstring would expect a block. *Found by Reviewer during round-2 code review.*

## Design Deviations

### TEA (test design)
- No deviations from spec. All 5 ACs from `context-story-45-6.md` are covered by boundary tests; AC1 is split into two tests (the AC1-positive and AC4-evaluator-on-OK_RESOLVED were merged into a single span-asserting test plus a separate state-attr-on-ok_resolved test) so each test exercises a single decision. Helper-name flexibility is intentional (test accepts either `_gate_archetype_resolution` or the OTEL span name) — story context calls the helper out by name but Dev can inline-gate if cleaner; the wire-check still passes either way.

### Dev (green)
- **Content-pack edit added to scope**
  - Spec source: context-story-45-6.md, "Out of scope" — "Reworking `CharacterBuilder` to require both hints. Some packs legitimately don't use archetype axes; the gate must distinguish."
  - Spec text: "Out of scope: Reworking ``CharacterBuilder`` to require both hints. Some packs legitimately don't use archetype axes; the gate must distinguish."
  - Implementation: Did not touch `CharacterBuilder`. However, edited `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml` to set `jungian_hint=hero` and `rpg_role_hint=jack_of_all_trades` on scene 1 — the pack DOES use archetype axes (declares `archetype_constraints.yaml`) but never populated hints, so default-1 walks all hit the gate. Without this content fix, ten existing `tests/server/test_chargen_*` integration tests would have regressed. The fix is bounded (one file, two YAML lines + comment) and aligns the pack's chargen scenes with its declared axes — it does NOT make any pack require hints; it makes one specific pack populate them.
  - Rationale: The alternative (monkeypatch hints in every adjacent test fixture, or strip pack axes per-test) is worse — it perpetuates the same missing-axes-on-scene bug pattern in test code. Caverns delvers ARE canonically heroes who do everything (pack design: anti-backstory, one class, one role).
  - Severity: minor
  - Forward impact: none beyond a content note for the Story 45-6 follow-up audit (see Delivery Findings → Dev). Other packs with axes (heavy_metal, space_opera, elemental_harmony) should be audited for the same content gap, but that's a separate content-pack story per the spec's scope-boundary on evropi.

### Reviewer (audit) — undocumented deviations

- **Lying docstring not logged by Dev:** The `_gate_archetype_resolution` docstring at `websocket_session_handler.py:663-667` describes failure mode 3 as "distinguished by the resolver_raised flag the caller passes through" — no such flag exists; the discriminator is shape-based. Dev's design reasoning matches the implementation but the docstring describes a different (presumably earlier-considered) design. Severity: HIGH (misleads future maintainers about how the gate determines `block_reason`). Already in the severity table as a [DOC] HIGH finding.

### TEA (test design — round 2)

- No deviations from spec or from the Reviewer's findings. All HIGH/MEDIUM Reviewer findings in the testable lane have boundary-test coverage; the LOW findings (truthy asserts, noqa, stale line-numbers) are mechanical fixes applied directly. Two RED tests intentionally fail — they drive Dev's green-phase implementation of `logger.warning()` and the discriminator switch from `"/"`-shape to `archetype_provenance is not None`. → ✓ ACCEPTED by Reviewer (round 2): TEA's test additions correctly drove Dev's green-phase fixes.

### Dev (green — round 2)

- **OTEL field rename chosen over threading-through**
  - Spec source: Reviewer's round-1 [RULE] MEDIUM finding on OTEL hint granularity loss
  - Spec text: "Either thread accumulator through (slightly invasive — change `_chargen_confirmation` to pass `builder.accumulated()` to the gate), or rename the OTEL fields to a single `had_both_hints: bool` to match the actual signal granularity. The latter is less invasive."
  - Implementation: chose the rename. `had_jungian_hint`/`had_rpg_role_hint` collapsed into `had_both_hints: bool` plus a sibling `provenance_set: bool`.
  - Rationale: less invasive (no signature changes); honest about granularity available to the gate (it can't see the accumulator post-build); documented inline at `websocket_session_handler.py:703-713`.
  - Severity: minor
  - Forward impact: none — both replacement fields are immediately useful to the GM panel; threading-through remains an option for a future story if per-axis granularity becomes needed. → ✓ ACCEPTED by Reviewer (round 2).

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story 45-6 ships a new gate, a new error code, two new OTEL spans, and SPAN_ROUTES registrations. Five ACs, all functional. No bypass.

**Test Files:**
- `sidequest-server/tests/server/test_45_6_chargen_archetype_gate.py` — 10 tests across 6 classes covering ACs 1–5 plus a wiring scan.

**Tests Written:** 10 tests covering 5 ACs
**Status:** RED (10/10 failing — verified via `uv run pytest tests/server/test_45_6_chargen_archetype_gate.py -v`)

### Rule Coverage

Repo language: Python (sidequest-server). The lang-review checklist for Python lives at `.pennyfarthing/gates/lang-review/python.md`; the SideQuest-specific load-bearing rules (CLAUDE.md "No Silent Fallbacks", "No Stubbing", "Verify Wiring", "Every Test Suite Needs a Wiring Test", OTEL Observability Principle) drive the rubric below.

| Rule | Test(s) | Status |
|------|---------|--------|
| CLAUDE.md: No Silent Fallbacks | `TestArchetypeGateBlockedPartial::test_confirmation_returns_typed_error_with_documented_code` (typed ERROR frame, not a swallowed retry) | failing |
| CLAUDE.md: No Silent Fallbacks (resolver) | `TestArchetypeGateResolverRaised::test_resolver_raise_blocks_and_does_not_persist` (catch+log+continue is the bug; gate must surface) | failing |
| CLAUDE.md: Verify Wiring | `TestArchetypeGateWiring::test_gate_helper_has_production_consumer` (source-scan for gate symbol in production seam) | failing |
| CLAUDE.md: Every Test Suite Needs a Wiring Test | Same as above — boundary tests already drive WS dispatch end-to-end, plus the explicit wiring scan | failing |
| CLAUDE.md: OTEL Observability Principle | `TestArchetypeGateOtel::test_evaluated_span_fires_on_ok_resolved_with_state_attr` / `_on_ok_no_axes_with_state_attr` / `_on_blocked_partial_with_block_reason` (Sebastien's lie-detector — every confirm path emits) | failing |
| `test_routing_completeness.py` (existing): every SPAN_* must be routed-or-flat | `TestArchetypeGateOtel::test_span_routes_register_both_gate_spans` | failing |
| AC2 negative-to-positive (pumblestone regression) | `TestArchetypeGateBlockedPartial::test_blocked_chargen_does_not_persist_character` (state stays Creating, snapshot.characters empty) | failing |
| Spec authority — story scope wins | All 10 tests honor `context-story-45-6.md` (no spec drift); helper-name flexibility intentionally accepts either symbol | failing |

**Rules checked:** 8 of 8 applicable rules have boundary-test coverage. Python-specific lang-review checks (typed pydantic boundaries, NonBlankString, no Deserialize bypass) are inherited from existing protocol tests — the new error code rides on the existing typed `ErrorPayload.code: str | None` field, which already has constructor validation; no new pydantic surface introduced.

**Self-check:** Reviewed every assertion. Two tests initially produced false greens (OK_RESOLVED and OK_NO_AXES passed without the gate present because the existing resolver / silent-no-op already produced the asserted character state). Both tests were strengthened to require the new `chargen.archetype_gate_evaluated` span — without the span, the assertion fails. Final RED run: 10/10 fail for the right reason (gate, error code, spans, SPAN_ROUTES, and production wiring all absent).

**Handoff:** To Dev (Inigo Montoya) for the green phase.

## Dev Assessment

**Status:** GREEN — all 10 new tests pass; full server suite (2703 passed, 34 skipped) regresses zero.

### Implementation

**1. New OTEL spans (sidequest-server/sidequest/telemetry/spans.py)**

- `SPAN_CHARGEN_ARCHETYPE_GATE_EVALUATED = "chargen.archetype_gate_evaluated"` — registered as a `state_transition` route on `component="character_creation"` with attributes: `state`, `resolved_archetype`, `pack_has_axes`, `had_jungian_hint`, `had_rpg_role_hint`, `genre`, `world`, `player_id`.
- `SPAN_CHARGEN_ARCHETYPE_GATE_BLOCKED = "chargen.archetype_gate_blocked"` — same shape plus `block_reason`. Pattern-matches the `npc.auto_registered` precedent (TEA's "Question" finding).
- Added next to the existing `SPAN_CHARGEN_*` constants. The existing `test_routing_completeness.py` automatically validates that every `SPAN_*` is routed-or-flat — both new constants are routed, so no FLAT_ONLY_SPANS edits.

**2. New gate helper (sidequest-server/sidequest/server/websocket_session_handler.py)**

- `_gate_archetype_resolution()` is a sibling to `_resolve_character_archetype` (added immediately above `_chargen_confirmation`). It inspects the post-resolve character state and returns `(is_blocked, block_reason)`. Three pass/fail decision rules:
  - `OK_RESOLVED` — `resolved_archetype` is a non-`/` display name.
  - `OK_NO_AXES` — `resolved_archetype is None` AND `pack.base_archetypes is None and pack.archetype_constraints is None`.
  - `BLOCKED_PARTIAL` — anything else, with `block_reason` distinguishing the three pumblestone failure modes:
    - `raw_pair_unresolved` — raw `"j/r"` with no pack axes (resolver short-circuited at line 577).
    - `missing_axes_with_pack_axes` — `resolved_archetype is None` with pack axes set (the pumblestone case — chargen scenes malformed).
    - `resolver_raised` — raw `"j/r"` with pack axes set (resolver was called and the catch-block at line 593 swallowed a `GenreValidationError`).
- The evaluator span fires on every chargen-confirm — Sebastien's GM panel sees the choice on every path, including success branches. The blocked span fires only on `BLOCKED_PARTIAL` and also writes a `character_creation.archetype_gate_blocked` event onto both the gate span (for ReadableSpan exporters) and the parent span (for the existing `character_creation.*` event stream).

**3. Wiring (sidequest-server/sidequest/server/websocket_session_handler.py)**

- `_chargen_confirmation` calls the gate immediately after `_resolve_character_archetype` (line 684) and before `apply_starting_loadout` (line 689). On `BLOCKED_PARTIAL` it returns a typed `ErrorMessage(code="chargen_archetype_unresolved")` and short-circuits — the character is NOT appended to the snapshot, `room.save()` is NOT called, the handler stays in `_State.Creating`. The wiring-test scans for the helper name OR the OTEL span name; both are present, so the wire-check passes.

**4. Content fix (sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml)**

- The pack declares axes (`base_archetypes` from the shared `archetypes_base.yaml`, `archetype_constraints` from the pack-local YAML) but its chargen scenes never set `jungian_hint` / `rpg_role_hint`. Default-1 walks therefore produced characters with `resolved_archetype=None` — the same silent-skip path that shipped pumblestone, just universal across caverns. Tagged scene 1 (`the_roll`) with `jungian_hint: hero` / `rpg_role_hint: jack_of_all_trades` (a `common` pairing in `archetype_constraints.yaml`). This is canon for Delvers — caverns is anti-backstory by design ("you are nobody until you survive"), and the canonical Delver IS a hero who does everything. Without this content edit the gate would have correctly blocked every caverns chargen and ten existing `tests/server/test_chargen_*` integration tests would have failed; with the edit, all adjacent suites stay green.

### Spec Authority Decisions

- **Helper-name flexibility (TEA spec deviation):** Used the spec-named `_gate_archetype_resolution` symbol. Both the symbol AND the OTEL span name are present in `websocket_session_handler.py`, so the wiring scan would pass with either accepted token.
- **Inner resolver event preservation (TEA "Improvement" finding):** Confirmed — the `character_creation.archetype_resolution_failed` event still fires inside `_resolve_character_archetype` on `GenreValidationError`. The gate wraps the resolver; it does not replace it. AC5 explicitly tests both events fire on the resolver-raised path.
- **Test-fixture monkeypatch updates:** After the caverns content fix, the `_inject_hints` helper accepts `None` values to recreate the pumblestone failure case for AC2/AC3/AC4-blocked tests. AC4-evaluator-on-OK_NO_AXES additionally nulls hints because the resolver short-circuits at line 577 with no pack axes, leaving raw `"hero/jack_of_all_trades"` on the character that the gate would block as `raw_pair_unresolved`.

### Quality Checks

- **`uv run pytest tests/`** — 2703 passed, 34 skipped (no failures, no regressions).
- **`uv run pytest tests/server/test_45_6_chargen_archetype_gate.py`** — 10/10 pass.
- **`uv run ruff check`** on changed files — 2 errors remain, both pre-existing (`UP037` at line 322 and `SIM105` at line 412); my added code is clean. Did not touch the pre-existing lint debt — out of scope.

### Files Changed

- `sidequest-server/sidequest/server/websocket_session_handler.py` (+167 lines: imports, `_gate_archetype_resolution` helper, gate call in `_chargen_confirmation`)
- `sidequest-server/sidequest/telemetry/spans.py` (+58 lines: two SPAN constants and routes)
- `sidequest-server/tests/server/test_45_6_chargen_archetype_gate.py` (already committed in red phase; updated for hint-injection fixes)
- `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml` (+10 lines: hero/jack_of_all_trades hints on scene 1)

### Branches

- `sidequest-server@feat/45-6-chargen-archetype-gate` (off develop) — 2 commits ahead of origin/develop.
- `sidequest-content@feat/45-6-chargen-archetype-gate` (off develop) — 1 commit ahead of origin/develop.

**Handoff:** To Reviewer (Westley, the Dread Pirate Roberts) for review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 3, dismissed 1 (low) |
| 5 | reviewer-comment-analyzer | Yes | findings | 10 | confirmed 6, deferred 4 (cosmetic line numbers — collapse to one finding) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 | confirmed 3 |

**All received:** Yes (4 returned, 5 skipped per settings)
**Total findings:** 12 confirmed (some collapsed), 1 dismissed (low confidence), 0 deferred to later story

### Subagent Finding Decisions

**reviewer-test-analyzer:**
- `raw_pair_unresolved block_reason has no test coverage` — **CONFIRMED** as `[TEST]` HIGH. The branch in production is reachable (pack-opted-out + scene sets hints) but never exercised. Gate logic is correct for this case but the test gap means a future regression in the discriminator goes undetected.
- `Wiring test brittleness — second OR-candidate is dead` — **CONFIRMED** as `[TEST]` MEDIUM. Verified myself: `grep -c "archetype_gate_evaluated" websocket_session_handler.py` returns 0 matches; the test passes purely on `_gate_archetype_resolution` matching, and that match includes the def line — Dev could delete the call site and keep the def, the test would still pass.
- `Missing-negative regression on legacy archetype_resolution_failed event` — **CONFIRMED** as `[TEST]` MEDIUM. AC2 path should NOT fire the legacy event; no test asserts that boundary.
- `otel_capture fixture leaks processors` — **DISMISSED** (low confidence, pre-existing pattern shared with `test_chargen_persist_and_play.py:71-83` and `test_chargen_complete_no_hp_leak.py:71-84`). Not introduced by this story; would be a broader refactor.

**reviewer-comment-analyzer:**
- `_resolve_character_archetype docstring still claims "non-fatal for chargen"` (line 566) — **CONFIRMED** as `[DOC]` HIGH. Story 45-6 made it fatal-via-gate. Future maintainers reading this docstring would draw the wrong conclusion.
- `Lying docstring — "resolver_raised flag the caller passes through"` (line 667) — **CONFIRMED** as `[DOC]` HIGH. No such flag exists; the discriminator is purely shape-based. Misleads about the architecture.
- `Stale builder.py:1640-1645 cite — actual is 1585-1590` (line 559) — **CONFIRMED** as `[DOC]` LOW (collapsing into a single "stale line numbers" finding).
- `Stale lines 572/577/593 cited in inline comments — actual 574/579/595` (lines 727, 862; test file lines 299, 708, 955) — **CONFIRMED** collapsed into the same `[DOC]` LOW. Verified myself: actual lines are 574, 579, 595.
- `"/" in display name as discriminator is brittle` (line 722) — **CONFIRMED** as `[DOC]` MEDIUM. Verified `ArchetypeResolved.name` at `sidequest/genre/archetype/resolved.py:33` is a free-form `str` with no validator forbidding "/". A pack could legitimately define a name like "Sage/Healer" and the gate would misclassify the success as `resolver_raised`. Today no pack defines such a name, but the invariant is implicit.
- `had_jungian_hint comment narrowness` (line 683) — **CONFIRMED** but consolidated into the OTEL granularity finding below (Reviewer-found).

**reviewer-rule-checker:**
- `Rule 4 (Logging): BLOCKED_PARTIAL path emits OTEL but no logger.warning()` — **CONFIRMED** as `[RULE]` HIGH. Per `.pennyfarthing/gates/lang-review/python.md` rule 4: "Error paths MUST have `logger.error()` or `logger.warning()`." OTEL is independent of the server log surface; ops debugging needs both. Per the critical reviewer guidance ("Never dismiss a finding that matches a stated project rule"), this is non-dismissible.
- `Rule 6 (Test quality): "assert evaluated" truthy-only at lines 490, 535` — **CONFIRMED** as `[RULE]` LOW. The subsequent `attrs.get("state") == ...` assertions rescue semantics, but the truthy pattern is structurally weak; replace with `assert len(evaluated) >= 1` or check span name explicitly.
- `Rule 10 (Import hygiene): noqa: E402 suppresses rather than fixes` — **CONFIRMED** as `[RULE]` LOW. Move `CONTENT_ROOT` inside `handler_factory` (it's only used there) to drop the suppression.

### Reviewer Findings (own analysis)

- **OTEL granularity loss on `ra is None` paths** — `had_jungian_hint` and `had_rpg_role_hint` are both reported as `False` whenever `resolved_archetype is None`. The builder only sets `resolved_archetype = None` when AT LEAST ONE hint is missing — so if a player set only `jungian_hint` (e.g., a partial scene), the OTEL says NEITHER was set. Sebastien's lie-detector loses signal granularity here. The gate has no access to the builder's accumulator post-build, so the fix is either to thread the accumulator through, or rename the fields to a single `had_both_hints: bool`. `[RULE]` MEDIUM (CLAUDE.md OTEL Observability Principle — accuracy of subsystem signal is part of observability).

### Rule Compliance

| Rule | Source | Applied to | Status |
|------|--------|-----------|--------|
| 1. Silent exception swallowing | python.md | gate helper, gate call site | compliant |
| 2. Mutable defaults | python.md | gate helper, test fixture | compliant |
| 3. Type annotation gaps | python.md | gate helper signature, return type | compliant |
| 4. Logging coverage on error paths | python.md | gate BLOCKED_PARTIAL branch | **VIOLATION** (no logger.warning) |
| 5. Path handling | python.md | test CONTENT_ROOT, read_text encoding | compliant |
| 6. Test quality | python.md | 10 new tests | partially compliant (2 truthy-only asserts) |
| 7. Resource leaks | python.md | tracer context managers | compliant |
| 8. Unsafe deserialization | python.md | new code | compliant (none) |
| 9. Async/await pitfalls | python.md | gate is sync, tests use asyncio.run | compliant |
| 10. Import hygiene | python.md | test conftest import | partially compliant (noqa: E402 suppresses) |
| 11. Input validation at boundaries | python.md | gate ERROR frame `block_reason` interpolation | compliant (server-controlled enum) |
| 12. Dependency hygiene | python.md | no dep changes | N/A |
| 13. Fix-introduced regressions | python.md | gate doesn't introduce new violations | compliant |
| No Silent Fallbacks | CLAUDE.md | gate failure mode | compliant (typed ERROR frame, fail-loud) |
| No Stubbing | CLAUDE.md | new code | compliant |
| Verify Wiring | CLAUDE.md | gate has production caller | compliant (call site at line 866) |
| Every Test Suite Needs a Wiring Test | CLAUDE.md | TestArchetypeGateWiring | weakly compliant (def-name match alone passes — see [TEST] medium) |
| OTEL Observability Principle | CLAUDE.md | two new spans, both routed | compliant on coverage; **partial** on signal accuracy (had_jungian/had_rpg_role granularity loss) |

### Deviation Audit

- **TEA (test design): "No deviations from spec."** → ✓ ACCEPTED by Reviewer: TEA's test split (separating evaluator-on-OK_RESOLVED from state-attr-on-ok_resolved) is sound; helper-name flexibility was reasonable foresight at red phase.

- **Dev (green): "Content-pack edit added to scope"** (caverns_and_claudes hero/jack_of_all_trades hints on scene 1) → ✓ ACCEPTED by Reviewer: the alternative (monkeypatch hints in every adjacent test fixture) would have perpetuated the same missing-axes-on-scene anti-pattern in test code. The content fix is bounded (1 file, 4 YAML lines), aligns the pack's chargen scenes with its declared axes, and matches the Delver pack-design canon. Per `sidequest-content/CLAUDE.md` "Never say 'the right fix is X' and then do Y" — Dev did the right fix.

### Reviewer (audit)

- **Undocumented deviation:** The `_gate_archetype_resolution` docstring describes failure mode 3 as `"distinguished by the resolver_raised flag the caller passes through"` (line 667 of websocket_session_handler.py). No such flag exists — the discriminator is shape-based (`pack_has_axes` + `"/"` in `resolved_archetype`). This is a doc deviation from the implemented design that TEA's test passes anyway because the test-level shape is asserted directly. Severity: HIGH (misleads future maintainers about how the gate works).

### Devil's Advocate

This code is broken. Let me argue.

**A confused content author writes a new pack with axes and chargen scenes that set both hints, but no funnel for some `(jungian, rpg_role)` pair.** The genre constraints mark the pair as `forbidden`. The resolver raises `GenreValidationError`. The catch at line 595 logs at WARNING and returns. The raw pair stays. The gate fires `chargen.archetype_gate_blocked` with `block_reason="resolver_raised"` and a typed ERROR frame. So far, working as designed. But `block_reason="resolver_raised"` collapses two distinct underlying causes (forbidden-pair vs. unknown-axis-id vs. world-funnel-forbidden — see `shim.py:99-115`) into a single bucket. Sebastien sees "resolver_raised" but not which of the three resolver paths failed. The legacy `character_creation.archetype_resolution_failed` event preserves `error: str(exc)` — so the data is on the parent span, just not on the gate's blocked span. Recoverable signal, but it's a documented gap.

**A malicious content author writes an `archetype_funnels.yaml` with a name containing "/"** — `"Sage/Healer"`. Resolver succeeds. `apply_archetype_resolved` writes `character.resolved_archetype = "Sage/Healer"`. The gate inspects `ra` → contains `"/"` → routes to BLOCKED_PARTIAL → `block_reason="resolver_raised"` (because `pack_has_axes=True`). Gate emits ERROR frame. **Legitimate chargen success is misclassified as a resolver failure and the player is blocked from completing chargen.** No content today defines such a name, but `ArchetypeResolved.name` has no validator. This is a real bug surface — the discriminator is brittle. A more robust signal: check `character.archetype_provenance is not None` (set by `apply_archetype_resolved` in lockstep with `resolved_archetype`). The current check leaves a Chekhov's-gun risk.

**A stressed filesystem during chargen confirmation:** `_resolve_character_archetype` doesn't touch disk; the gate doesn't either. Storage failure surfaces in `room.save()` later — orthogonal to the gate.

**A multiplayer race condition:** Two peers call `_chargen_confirmation` concurrently. Both run the gate. Both pass. Both append to `sd.snapshot.characters`. The MP first-commit branch ran twice. This is orthogonal to the gate (the gate is per-call, not snapshot-level), so the gate doesn't introduce a new race — but the wire-test suite doesn't probe MP-specific gate paths. Out of scope for this story.

**A re-use scenario:** A test inspects `character.archetype_provenance` to confirm OK_RESOLVED → finds it set → all good. But a refactor that drops the `apply_archetype_resolved` call (and hence `archetype_provenance`) would still pass the gate's `"/" not in ra` check, because `apply_archetype_resolved` sets BOTH fields together (atomic). Today they are atomic; if a future refactor splits them, the gate's correctness invariant breaks silently. No test currently asserts `archetype_provenance is not None` on the OK_RESOLVED branch — the gate's contract with the resolver is undertested.

**The wiring test passes today but a future maintainer breaks it without noticing:** Dev removes the call site at line 866, leaves the def at line 633. Tests pass (because chargen still completes — the gate isn't called, so OK_RESOLVED branch fires by default-1 walk producing a resolved name). The wiring test's source-scan finds `_gate_archetype_resolution` in the def line and passes. Production silently bypasses the gate. **Pumblestone ships again.** The wiring test's truthy-OR with a never-matching second candidate makes it weaker than advertised.

**A `logger.warning()` is missing on BLOCKED_PARTIAL:** ops engineers running the server in production grep server logs for client errors. The gate emits an OTEL span, but the OTEL pipeline may be down, sampled, or just unfamiliar to the on-call. The server log file would not show that pumblestone-class events were happening — invisible failure mode. Per CLAUDE.md "every backend fix that touches a subsystem MUST add OTEL watcher events" — yes, OTEL is added. But python.md rule 4 explicitly requires logger entries on error paths, and OTEL is not a substitute for the structured server log.

The Devil's Advocate found two existing findings (the brittle "/" discriminator, the weak wiring test) and surfaced one new issue (the gate's contract with `apply_archetype_resolved` is undertested via `archetype_provenance`).

## Reviewer Assessment

**Verdict:** REJECTED

**Data flow traced:** WS `CharacterCreationMessage(phase="confirmation")` → `character_creation.HANDLER` → `_chargen_confirmation` → `builder.build()` → `_resolve_character_archetype` (existing) → `_gate_archetype_resolution` (new) → either `_error_msg(code="chargen_archetype_unresolved")` (BLOCKED_PARTIAL) or `apply_starting_loadout` + persist (passes). The gate is correctly placed (after resolution, before persist) and the BLOCKED_PARTIAL branch correctly short-circuits without persisting or transitioning state.

**Pattern observed:** Sibling-helper-with-shape-inspection pattern. The gate inspects post-state instead of intercepting the resolver — keeps the resolver simple and makes the gate easy to reason about. The OTEL spans use the same `state_transition`/`character_creation` route shape as the existing `npc.auto_registered` precedent — good consistency.

**Error handling observed:** Gate returns `(is_blocked, block_reason)` tuple, caller short-circuits on `is_blocked`. The typed ERROR frame uses the existing `_error_msg(code=...)` helper — no new error path invented. The legacy `character_creation.archetype_resolution_failed` event still fires inside the resolver's `except` — gate wraps, doesn't replace. **Missing:** server-log entry on the BLOCKED_PARTIAL branch (Rule 4 violation).

| Severity | Issue | Tag | Location | Fix Required |
|----------|-------|-----|----------|--------------|
| [HIGH] | `raw_pair_unresolved` block_reason has zero test coverage. Gate code is correct for this case but a regression in the discriminator goes undetected. | [TEST] | `tests/server/test_45_6_chargen_archetype_gate.py` (new test class) | Add a test that injects `hero`/`tank` hints AND nulls pack axes, then asserts ERROR frame fires with `block_reason="raw_pair_unresolved"`. |
| [HIGH] | BLOCKED_PARTIAL gate path emits OTEL but does NOT call `logger.warning()` or `logger.error()`. Per python.md rule 4, error paths with user-controlled input MUST log; OTEL is not a substitute for the structured server log. | [RULE] | `sidequest/server/websocket_session_handler.py:733-801` (in `_gate_archetype_resolution` BLOCKED_PARTIAL branch) | Add `logger.warning("chargen.archetype_gate_blocked player_id=%s block_reason=%s genre=%s world=%s", player_id, block_reason, sd.genre_slug, sd.world_slug)` before or alongside the blocked-span emission. |
| [HIGH] | `_resolve_character_archetype` docstring at line 566 still claims resolution failures are "non-fatal for chargen" — Story 45-6 makes them fatal via the gate. Future maintainers will draw the wrong conclusion. | [DOC] | `sidequest/server/websocket_session_handler.py:565-567` | Update to: "Resolution failures emit a ``character_creation.archetype_resolution_failed`` span event and leave the raw pair in place. The downstream archetype-resolution gate in ``_chargen_confirmation`` (Story 45-6) detects the partial state and rejects the commit; this helper is no-op-on-failure intentionally so the gate can decide." |
| [HIGH] | `_gate_archetype_resolution` docstring at line 667 claims `resolver_raised` is "distinguished by the resolver_raised flag the caller passes through". No such flag exists; the discriminator is shape-based (`pack_has_axes` + `"/"` in `ra`). | [DOC] | `sidequest/server/websocket_session_handler.py:663-667` | Replace the `"flag the caller passes through"` sentence with: "Detected purely by shape: `pack_has_axes=True` AND `"/" in resolved_archetype` implies the resolver was called (the pack-lacks-axes short-circuit at line 579 would have returned before calling `resolve_archetype`) and then raised; the catch-block at line 595 swallowed the exception." |
| [MEDIUM] | Wiring test second candidate (`archetype_gate_evaluated` substring) never matches in production (verified: `grep -c` returns 0). Test passes purely on `_gate_archetype_resolution` matching, and that includes the def line — if Dev keeps the def but removes the call site, the test still passes. The wire-check is weaker than advertised. | [TEST] | `tests/server/test_45_6_chargen_archetype_gate.py:751-767` | Replace the source-scan with one of: (a) grep specifically for `self._gate_archetype_resolution(` (the call pattern) outside the def line, or (b) `inspect.getsource(WebSocketSessionHandler._chargen_confirmation)` and check the call symbol appears in the body. Add `SPAN_CHARGEN_ARCHETYPE_GATE_EVALUATED` to the candidate list to also cover the constant-import path. |
| [MEDIUM] | Gate's "/" discriminator is brittle. `ArchetypeResolved.name` is a free-form `str` with no validator. A funnel name like `"Sage/Healer"` would be misclassified as `resolver_raised`. | [DOC] | `sidequest/server/websocket_session_handler.py:715-734` | Either (a) add a caveat comment documenting the implicit invariant ("resolved display names must not contain '/'; the gate's discriminator is syntactic"), or (b) switch the discriminator to `character.archetype_provenance is not None` (set in lockstep by `apply_archetype_resolved`), which is a more robust signal that survives a future name-format change. (b) is preferred. |
| [MEDIUM] | OTEL `had_jungian_hint` / `had_rpg_role_hint` lose granularity on `ra is None` paths. The gate has no access to the builder's accumulator, so when `ra is None` (which happens iff the builder couldn't form a pair, which happens iff at least one hint was missing), both flags are reported `False` even if one was set. Sebastien loses signal on which axis was missing. | [RULE] | `sidequest/server/websocket_session_handler.py:692-702` and the SPAN_ROUTES extract lambdas at `spans.py:272-273, 290-291` | Either thread the accumulator through to the gate (slightly invasive — change `_chargen_confirmation` to pass `builder.accumulated()` to the gate), or rename the OTEL fields to a single `had_both_hints: bool` to match the actual signal granularity. The latter is less invasive. |
| [MEDIUM] | No test asserts the legacy `character_creation.archetype_resolution_failed` event does NOT fire on the AC2 path (`missing_axes_with_pack_axes`). If a future change accidentally fires the legacy event on the pumblestone path, no test catches it. | [TEST] | `tests/server/test_45_6_chargen_archetype_gate.py::TestArchetypeGateBlockedPartial` | After the existing AC2 assertions, add `assert not _events(otel_capture, "character_creation.archetype_resolution_failed")` — the legacy event must fire only on resolver-raised. |
| [LOW] | `assert evaluated` truthy-only on a list at lines 490 and 535 (per python.md rule 6). The follow-up `attrs.get("state") == ...` assertions rescue semantics today, but the truthy pattern is structurally weak. | [RULE] | `tests/server/test_45_6_chargen_archetype_gate.py:490, 535` | Replace `assert evaluated` with `assert len(evaluated) >= 1, ...` (matches the rest of the suite at lines 568, 597, 706 which do similar). |
| [LOW] | `# noqa: E402` at line 73 suppresses an import-after-module-assignment warning. The cause is `CONTENT_ROOT` at line 70; moving `CONTENT_ROOT` inside `handler_factory` (its only consumer) eliminates the issue. | [RULE] | `tests/server/test_45_6_chargen_archetype_gate.py:70-75` | Move `CONTENT_ROOT` inside the `handler_factory` fixture body and drop the `# noqa: E402`. |
| [LOW] | Stale line-number citations in comments and docstrings reference pre-patch positions: builder.py 1640-1645 (actual 1585-1590); websocket_session_handler.py 572/577/593 (actual 574/579/595, in 5 places across the gate file and test file); test file references 546-628, 593-610 ranges that have shifted. | [DOC] | `sidequest/server/websocket_session_handler.py:559, 727, 862` and `tests/server/test_45_6_chargen_archetype_gate.py:11, 729, 955` | Update each citation to current line numbers. (Verified actual lines via `grep -n "if raw is None\|if pack.base_archetypes is None\|except GenreValidationError"` → 574, 579, 595.) |

**[VERIFIED]** items:
- **[VERIFIED]** Gate is wired into the production seam — call site at `websocket_session_handler.py:866` (verified via `grep -n "_gate_archetype_resolution"` → 3 matches: def at 633, comment at 864, call at 866).
- **[VERIFIED]** Both new SPAN_* constants are routed in `SPAN_ROUTES` and would pass `test_routing_completeness.py::test_every_span_is_routed_or_explicitly_flat` — confirmed by running the test (passes).
- **[VERIFIED]** Both routes target `state_transition` event_type, which is in the known set at `tests/telemetry/test_routing_completeness.py:48-58` (confirmed by reading that file).
- **[VERIFIED]** Full server suite passes: 2703 passed, 0 failed, 34 skipped (preflight).
- **[VERIFIED]** Branch introduces zero new lint findings; the two ruff hits at lines 322 (UP037) and 412 (SIM105) of `websocket_session_handler.py` are pre-existing on develop (preflight verified).
- **[VERIFIED]** No code smells (TODO/FIXME/HACK/print/breakpoint/pdb) in the diff (preflight).
- **[VERIFIED]** The legacy `character_creation.archetype_resolution_failed` event still fires in `_resolve_character_archetype:594-603` on `GenreValidationError` — gate wraps the resolver, does not replace it. Asserted by `TestArchetypeGateResolverRaised`.
- **[VERIFIED]** Content fix on `caverns_and_claudes/char_creation.yaml`: `[hero, jack_of_all_trades]` is in `archetype_constraints.yaml` `valid_pairings.common` (verified by grep).

**Handoff:** Back to TEA (Fezzik) for red-phase rework — the testable findings (raw_pair_unresolved coverage gap, weak wiring test, missing legacy-event negative check) drive the next test pass; Dev (Inigo Montoya) then implements the logger.warning, doc fixes, and discriminator improvements in green.

## TEA Assessment (round 2 — rework after REJECTED verdict)

**Tests Required:** Yes
**Reason:** Reviewer's verdict identified two HIGH-severity testable gaps (`raw_pair_unresolved` coverage and missing-`logger.warning` rule violation) plus several MEDIUM/LOW findings that benefit from test enforcement.

**Test File:** `sidequest-server/tests/server/test_45_6_chargen_archetype_gate.py` (existing, expanded)

**Tests Total:** 14 (10 from round 1 + 4 added/strengthened in round 2)
**Status:** RED (12 pass, 2 fail — by design; the 2 failures drive Dev's green-phase fixes)

### Round-2 Test Changes

#### NEW RED tests (drive Dev's green-phase work)

- **`TestArchetypeGateLogging::test_blocked_partial_emits_warning_log`** — Reviewer-flagged HIGH (rule 4). Asserts a WARNING-level record mentioning `archetype_gate` fires when chargen is blocked. Fails today because the gate emits OTEL but no `logger.warning()`. Dev fix: add `logger.warning("chargen.archetype_gate_blocked player_id=%s block_reason=%s", ...)` on the BLOCKED_PARTIAL branch.

- **`TestArchetypeGateDiscriminatorRobustness::test_resolved_name_with_slash_routes_to_ok_resolved`** — Reviewer-flagged MEDIUM. Patches `apply_archetype_resolved` to write `"Sage/Healer"` (a name containing "/") and asserts the gate routes to OK_RESOLVED. Fails today because the gate's discriminator keys on `"/" in resolved_archetype` (misclassifies as `resolver_raised`). Dev fix: switch the discriminator to `character.archetype_provenance is not None` (the lockstep-write signal).

#### NEW GREEN tests (close coverage gaps; pass on current code)

- **`TestArchetypeGateRawPairUnresolved::test_pack_axisless_with_set_hints_blocks_with_raw_pair_unresolved`** — Reviewer-flagged HIGH (test gap). Injects `hero`/`tank` hints AND nulls pack axes. The resolver short-circuits at `_resolve_character_archetype:579`, the raw pair stays, the gate routes to `block_reason="raw_pair_unresolved"`. Includes a negative-regression assertion that the legacy `archetype_resolution_failed` event does NOT fire (resolver returned BEFORE the `try`/`except`).

- **AC2 negative regression** (`test_confirmation_returns_typed_error_with_documented_code` extended) — Reviewer-flagged MEDIUM. Asserts the legacy `archetype_resolution_failed` event does NOT fire on the `missing_axes_with_pack_axes` branch.

- **AC1 lockstep contract** (`test_resolved_archetype_is_display_name_not_raw_pair` extended) — Reviewer-flagged MEDIUM. Asserts `character.archetype_provenance is not None` on OK_RESOLVED (locks in the `apply_archetype_resolved` atomic-write invariant).

#### STRENGTHENED

- **Wiring test** — Reviewer-flagged MEDIUM. Replaced whole-file source-scan with `inspect.getsource(WebSocketSessionHandler._chargen_confirmation)` body check + a companion `hasattr` test for the def. The prior version would have passed even if Dev removed the call site (def-line-only match); the new version requires the invocation pattern inside the method body.

- **All 7 truthy `assert evaluated` / `assert blocked` checks** replaced with `assert len(...) >= 1, ...` per python.md rule 6 (rule_checker LOW finding).

- **`CONTENT_ROOT` moved into `handler_factory` fixture body** — drops the `# noqa: E402` suppression at the conftest import (rule_checker LOW finding).

- **Stale line-number citations updated** — `websocket_session_handler.py:546-628` → `:548-630`, `:577` → `:579`, `:593-610` → `:595-612` in test docstring and inline comments (comment_analyzer findings).

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| python.md #1 (silent exception swallowing) | `_inject_hints` doesn't catch; AC5 monkeypatches `resolve_archetype` to raise and asserts gate captures via shape | covered |
| python.md #4 (logging on error paths) | `TestArchetypeGateLogging::test_blocked_partial_emits_warning_log` | **failing (RED — drives Dev fix)** |
| python.md #6 (test quality — vacuous assertions) | All 7 truthy `assert evaluated/blocked` tightened to `assert len(...) >= 1` | covered |
| python.md #10 (import hygiene) | conftest import at top, no `noqa: E402` | covered |
| CLAUDE.md No Silent Fallbacks | AC2 + raw_pair_unresolved + resolver-raised assert ERROR frame is returned, character not persisted, state stays Creating | covered |
| CLAUDE.md Verify Wiring | `TestArchetypeGateWiring` x2 (call-site body scan + def existence) | covered |
| CLAUDE.md Every Test Suite Needs a Wiring Test | Yes — TestArchetypeGateWiring class | covered |
| CLAUDE.md OTEL Observability Principle | Three branches × evaluator-span asserted; `chargen.archetype_gate_blocked` asserted on blocked branches; `SPAN_ROUTES` registration test | covered |
| Reviewer-flagged: gate's contract with apply_archetype_resolved (`archetype_provenance` lockstep) | AC1 extended assertion | covered |
| Reviewer-flagged: discriminator robustness (`/` in display name) | `TestArchetypeGateDiscriminatorRobustness` | **failing (RED — drives Dev fix)** |
| Reviewer-flagged: raw_pair_unresolved branch coverage | `TestArchetypeGateRawPairUnresolved` | covered |

**Rules checked:** 11 of 11 applicable rules have boundary-test coverage. Two RED tests fail by design — they are the failing tests that drive Dev's green-phase implementation.

**Self-check:** Reviewed every assertion in the round-2 additions. All assertions are specific (no `assert True`, no truthy-only checks on values that could be wrong). The lint check (`uv run ruff check`) passes on the test file.

**Verification:**
- `uv run pytest tests/server/test_45_6_chargen_archetype_gate.py -v` → 12 pass, 2 fail (the new RED tests, intentional)
- `uv run pytest tests/server/ tests/telemetry/ -q` → 833 pass, 8 skip, 2 expected fail (no regressions in adjacent suites)
- `uv run ruff check tests/server/test_45_6_chargen_archetype_gate.py` → clean

### Findings on Reviewer's other items (out of TEA scope, deferred to Dev green)

- **[DOC] HIGH** Stale "non-fatal for chargen" claim in `_resolve_character_archetype` docstring (line 566) — Dev to update.
- **[DOC] HIGH** "Lying docstring" about `resolver_raised flag` (line 667 of gate helper) — Dev to update.
- **[DOC] MEDIUM** Brittle "/" discriminator comment caveat — superseded by the discriminator-robustness test that drives the actual code fix; Dev fixes both the code and the comment in green.
- **[RULE] MEDIUM** OTEL `had_jungian_hint` / `had_rpg_role_hint` granularity loss — Reviewer's recommended fix is a field rename to `had_both_hints: bool`. Dev's call: rename or thread the accumulator. Existing AC4 tests are insensitive to the field-rename (they only assert `state` and `block_reason`), so no test rework needed here.
- **[DOC] LOW** Stale line-number citations in production-side gate helper (lines 559, 727, 862 of `websocket_session_handler.py`) — Dev to update.

**Handoff:** To Dev (Inigo Montoya) for the green phase. Two RED tests need to flip GREEN; doc/lint fixes from the Reviewer's table also need addressing.

## Dev Assessment (round 2 — green-rework after REJECTED verdict)

**Status:** GREEN — all 14 gate tests pass; full server suite 2707 passed (4 new tests added since round-1 baseline of 2703), 0 failures, 34 skipped.

### Implementation (round 2)

**1. Discriminator switched to `archetype_provenance is not None`** (Reviewer-flagged MEDIUM)

`sidequest/server/websocket_session_handler.py:_gate_archetype_resolution`. The previous discriminator keyed on `"/"` in `character.resolved_archetype` — that misclassified any legitimate display name containing `"/"` (e.g., a hypothetical funnel-defined `"Sage/Healer"`) as `resolver_raised`. The new discriminator keys on the lockstep marker `archetype_provenance` that `apply_archetype_resolved` writes alongside `resolved_archetype`. This is the durable signal: as long as `apply_archetype_resolved` writes both fields atomically (which the AC1 lockstep test now asserts), the gate survives any name-format change. Flips `TestArchetypeGateDiscriminatorRobustness::test_resolved_name_with_slash_routes_to_ok_resolved` from RED to GREEN.

**2. `logger.warning()` on BLOCKED_PARTIAL** (Reviewer-flagged HIGH — python.md rule 4)

Added a `logger.warning("chargen.archetype_gate_blocked player_id=%s block_reason=%s genre=%s world=%s pack_has_axes=%s resolved_archetype=%s", ...)` call inside the BLOCKED_PARTIAL branch, before the blocked-span emission. OTEL goes to the GM panel; the WARNING entry lands in the structured server log surface (journald / file logs) so ops debugging works without the OTEL pipeline. Flips `TestArchetypeGateLogging::test_blocked_partial_emits_warning_log` from RED to GREEN. Uses `%s`-formatted args (lazy evaluation, structured-logging-compatible — python.md rule 4 sub-bullet on f-strings in log calls).

**3. OTEL field rename: `had_jungian_hint`/`had_rpg_role_hint` → `had_both_hints` + `provenance_set`** (Reviewer-flagged MEDIUM — RULE OTEL granularity)

The gate has no access to the builder accumulator post-`builder.build()`. Originally the gate emitted two booleans, but on the `ra is None` path (builder didn't form a pair) the gate could only report `False/False` regardless of which hint was actually missing. The renamed `had_both_hints: bool` accurately reflects the signal granularity available. Added a sibling `provenance_set: bool` so Sebastien's GM panel can see the new discriminator's value directly — useful for ops auditing of "the gate said OK_RESOLVED, but did the resolver actually run?" (yes iff `provenance_set=True`). SPAN_ROUTES `extract` lambdas at `sidequest/telemetry/spans.py:262-296` updated in lockstep.

**4. Stale `_resolve_character_archetype` docstring updated** (Reviewer-flagged HIGH DOC)

Old docstring claimed "resolution failures... non-fatal for chargen — the GM panel can still see the attempt" (line 566). New docstring describes the downstream gate that turns partial-resolution into a typed ERROR frame. The old claim was actively misleading post-Story-45-6 — a future maintainer reading `_resolve_character_archetype` would draw the wrong conclusion about the resolver's failure semantics.

**5. "Lying docstring" removed** (Reviewer-flagged HIGH DOC)

Gate docstring no longer claims `resolver_raised` is "distinguished by the resolver_raised flag the caller passes through" — no such flag exists. The new docstring says: pure shape inference; pack-axes-set + raw pair = resolver was called and raised (the pack-lacks-axes short-circuit at line 579 would have returned before calling `resolve_archetype`).

**6. Stale line numbers updated** (Reviewer-flagged LOW DOC)

- `builder.py:1640-1645` → `builder.py:1585-1590` (line 559)
- inline comment `lines 572, 577, 593` → `lines 574, 579, 595` (line 862)
- inline comment within gate body referencing line 577/593 — replaced with cleaner reference to line 579/595 in the new shape-inference description (the gate's reasoning section was rewritten).

### Decisions

- **Did NOT thread builder accumulator through to the gate** for fine-grained per-axis OTEL — would require changing `_chargen_confirmation`'s call signature and copying `acc.jungian_hint` / `acc.rpg_role_hint` separately. The field rename to `had_both_hints` is the bounded fix that matches the Reviewer's "either rename or thread through" guidance; rename is less invasive and more honest about what the gate can know.
- **Did NOT touch the pre-existing ruff debt** at lines 322 (UP037) and 412 (SIM105) — both confirmed pre-existing on develop by round-1 preflight, out of Story 45-6 scope.

### Quality Checks

- **`uv run pytest tests/server/test_45_6_chargen_archetype_gate.py -v`** → 14/14 pass (the two former RED tests now GREEN).
- **`uv run pytest tests/telemetry/test_routing_completeness.py -v`** → 2/2 pass (both new SPAN_* constants still routed).
- **`uv run pytest tests/`** → 2707 passed, 34 skipped, 0 failed (was 2703 in round 1; net +4 from the round-2 RED test additions).
- **`uv run ruff check`** on changed files → clean on changed lines; pre-existing UP037 / SIM105 hits remain unaddressed (out of scope).

### Files Changed (round 2)

- `sidequest-server/sidequest/server/websocket_session_handler.py` (gate body rewrite, docstring fixes, line-number updates) — net +47 / -86 lines vs round-1 baseline (the gate body is more concise after the discriminator simplification).
- `sidequest-server/sidequest/telemetry/spans.py` (SPAN_ROUTES extract lambdas) — net +6 / -4 lines.
- `sidequest-server/tests/server/test_45_6_chargen_archetype_gate.py` (TEA's round-2 commit) — already on the branch.

### Branches

- `sidequest-server@feat/45-6-chargen-archetype-gate` — 4 commits ahead of origin/develop (round-1 test, round-1 impl, round-2 test rework, round-2 impl rework).
- `sidequest-content@feat/45-6-chargen-archetype-gate` — unchanged from round 1, 1 commit ahead.

**Handoff:** Back to Reviewer (Westley) for re-review.

## Subagent Results (round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 2 | confirmed 2 (both LOW) |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 | confirmed 6 (1 MEDIUM + 5 LOW collapse to one finding) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | none | N/A — explicit verification of round-1 findings, all 13 rules compliant |

**All received:** Yes (4 returned, 5 skipped per settings)
**Total findings:** 8 confirmed, 0 dismissed, 0 deferred

### Subagent Finding Decisions (round 2)

**reviewer-preflight:**
- Status clean. Full server suite 2707 passed / 0 failed / 34 skipped. New tests 14/14 pass. Routing completeness 2/2 pass. Lint introduces zero new findings (UP037 line 322 + SIM105 line 412 confirmed pre-existing baseline). No code smells.

**reviewer-test-analyzer:**
- `assert relevant` truthy at line 950 — **CONFIRMED** as `[TEST]` LOW. Same class as the round-1 finding that prompted the 7-site `assert len(...) >= 1` rewrite, missed for this one site introduced in round 2. Non-blocking — cosmetic consistency.
- Stale "current shape-based discriminator misclassifies" comment at lines 965-976 + 994-996 — **CONFIRMED** as `[TEST]` LOW. After round-2's discriminator switch, the comment now describes the OLD behavior in present tense, which would mislead a future maintainer reading the test rationale. Non-blocking — doc.
- All 8 round-1 testable findings verified addressed (raw_pair_unresolved coverage, wiring test strength, AC1 lockstep, AC2 negative regression, discriminator robustness, truthy-assert sweep, noqa removal, monkey-patch targets).

**reviewer-comment-analyzer:**
- **OK_NO_AXES condition: docstring says AND, code does OR** at line 659 — **CONFIRMED** as `[DOC]` MEDIUM. The gate docstring says the OK_NO_AXES condition is `(base_archetypes is None and archetype_constraints is None)` (BOTH None). The actual code computes `not pack_has_axes` where `pack_has_axes = (base is not None and constraints is not None)` — by De Morgan, `not pack_has_axes = base is None OR constraints is None` (EITHER None). The CODE matches the original story-context spec ("Pack lacks resolver inputs: `if pack.base_archetypes is None or pack.archetype_constraints is None: return`"). The DOCSTRING used the wrong logical operator. A pack with only `archetypes_base.yaml` shipped (no per-pack `archetype_constraints.yaml`) would silently OK_NO_AXES per the code, but the docstring claims it would not. Severity-MEDIUM because (a) it's a doc-vs-spec gap, (b) the code is correct per spec, (c) the docstring is wrong. Non-blocking under the rubric (MEDIUM doesn't block PR), but Dev should fix in a follow-up commit before merge if practical.
- **5 stale line numbers** at lines 668, 676, 679, 742, 886 — **CONFIRMED** as `[DOC]` LOW. Round-1's fix landed on numbers (574, 579, 595) that were correct THEN, but round-2's gate-method rewrite shifted everything down by ~7 lines. Actual current lines: 581 (raw is None), 586 (pack-axes check), 602 (except). Line 886 cites "574, 579, 595" which is wrong; the gate docstring at lines 668/676/679 also cites old positions. **This is a recurring drift bug** — the line numbers are absolute and unstable. Recommend in the assessment that future references use symbolic anchors (function/method names, branch labels) instead of line numbers. Non-blocking but worth a forward-looking note.
- The 4 round-1 HIGH/MEDIUM doc findings (`_resolve_character_archetype` "non-fatal" docstring, "lying docstring" about resolver_raised flag, builder.py:1640 cite, "/" discriminator caveat) all **VERIFIED ADDRESSED**.

**reviewer-rule-checker:**
- **0 violations across 13 rules / 67 instances.** All three round-1 violations (Rule 4 logging, Rule 6 truthy assertions, Rule 10 import hygiene) verified addressed.
- Special checks confirmed: Dev chose the field rename path (not threading-through), and the rename to `had_both_hints: bool` accurately reflects what the gate can know.

### Reviewer (own analysis — round 2)

- **Orphaned section header at lines 877-885** — `[DOC]` LOW. The "Wire test — verify the gate is actually called from production code" header block is followed immediately by the "Rule-enforcement: python.md rule 4" header at lines 888-900, with NO test class between them. The actual `class TestArchetypeGateWiring` is at line 1067 — separated by `TestArchetypeGateLogging` (line 903) and `TestArchetypeGateDiscriminatorRobustness` (line 980). TEA inserted the new round-2 classes between the wire-test header and its class. Cosmetic. Recommend: either move the wire-test header down to right before `class TestArchetypeGateWiring:`, or delete the orphan since the class has its own docstring.
- **OK_NO_AXES condition reachability re-verified** — Per the loader at `sidequest/genre/loader.py:576-578`, `base_archetypes` is loaded from a content-root-level shared file (`archetypes_base.yaml`) that is always present when content is loaded. Per-pack files load `archetype_constraints` (line 583). So the case "only base_archetypes set, no constraints" IS reachable for any pack that doesn't ship its own `archetype_constraints.yaml` — and the code's OR-check correctly OK_NO_AXES'es it. The docstring's AND-claim is the bug. (Confirms comment-analyzer's MEDIUM finding.)
- **Discriminator switch correctness re-verified** — `apply_archetype_resolved` at `sidequest/game/archetype_apply.py:24-25` writes `resolved_archetype` and `archetype_provenance` together; the gate's new `provenance_set` discriminator correctly fires only when this lockstep write completed. Survives the "/"-in-display-name latent risk. ✓

### Rule Compliance (round 2)

| Rule | Source | Status round 1 | Status round 2 |
|------|--------|----------------|----------------|
| 1. Silent exception swallowing | python.md | compliant | compliant |
| 2. Mutable defaults | python.md | compliant | compliant |
| 3. Type annotation gaps | python.md | compliant | compliant |
| 4. Logging coverage on error paths | python.md | **VIOLATION** | **compliant** (logger.warning added) |
| 5. Path handling | python.md | compliant | compliant |
| 6. Test quality | python.md | partial (2 truthy) | compliant (all 7 sweep + new sites OK except 1 LOW) |
| 7. Resource leaks | python.md | compliant | compliant |
| 8. Unsafe deserialization | python.md | compliant | compliant |
| 9. Async/await pitfalls | python.md | compliant | compliant |
| 10. Import hygiene | python.md | partial (noqa) | compliant (CONTENT_ROOT moved into fixture) |
| 11. Input validation | python.md | compliant | compliant |
| 12. Dependency hygiene | python.md | N/A | N/A |
| 13. Fix-introduced regressions | python.md | compliant | compliant |
| No Silent Fallbacks | CLAUDE.md | compliant | compliant |
| Verify Wiring | CLAUDE.md | weakly compliant | compliant (call-site grep + def hasattr) |
| OTEL Observability | CLAUDE.md | partial (granularity loss) | compliant (had_both_hints rename) |

### Deviation Audit (round 2)

- **TEA round-1 (test design): "No deviations from spec."** → ✓ ACCEPTED by Reviewer (round 1).
- **Dev round-1 (green): Content-pack edit added to scope.** → ✓ ACCEPTED by Reviewer (round 1).
- **TEA round-2 (test design rework): "No deviations from spec or from the Reviewer's findings."** → ✓ ACCEPTED by Reviewer: TEA's round-2 work strengthened the wiring test (call-site introspection + def hasattr), tightened all flagged truthy assertions, and added the `archetype_provenance` lockstep assertion to AC1. Round-2 RED tests correctly drove Dev's green-phase fixes.
- **Dev round-2 (green-rework): No explicit deviations logged.** Reviewer notes: Dev chose the field-rename path (`had_jungian_hint`/`had_rpg_role_hint` → `had_both_hints` + `provenance_set`) over the threading-through alternative — this is a defensible call documented in inline comments at `websocket_session_handler.py:703-713`. → ✓ ACCEPTED by Reviewer.

### Reviewer (audit — round 2)

- No new undocumented deviations surfaced in round 2. The OK_NO_AXES docstring/code mismatch (above, MEDIUM finding) is a doc-vs-code gap, not a spec deviation — the code correctly implements the original story-context spec; the docstring just transcribed the wrong logical operator.

### Devil's Advocate (round 2)

This code might still be broken. Let me argue.

**Edge case 1 — Half-axis pack (pumblestone-shaped, but worse):** A content author ships `archetype_constraints.yaml` but for some reason the shared `archetypes_base.yaml` at content root is missing or empty. `pack.base_archetypes is None`, `pack.archetype_constraints is not None`. `pack_has_axes = False`. A chargen scene that sets BOTH hints produces `ra = "hero/tank"`. The resolver short-circuits at line 586 (pack-axes check) because `base_archetypes is None`. The raw pair stays. Gate sees `not provenance_set` AND `ra is not None` (so falls into the else-branch) AND `not pack_has_axes` → `block_reason = "raw_pair_unresolved"`. Correct — the pack misconfiguration is caught. But would the content author understand WHY? The error frame says "archetype resolution failed (raw_pair_unresolved)" — which is technically right but unintuitive for a missing-base-archetypes-file failure. Minor — not a bug, just a UX nit.

**Edge case 2 — Content author with only constraints, no base:** Same as above but inverse — `base is None`, `constraints is not None`. `pack_has_axes = False`. Same routing as case 1. The OR-vs-AND docstring bug surfaces here: the docstring claims OK_NO_AXES requires BOTH to be None; the code OR-s them. So if the author EXPECTED their pack to fail (because they shipped only constraints, expecting a "block" since base is missing), the gate instead silently routes to OK_NO_AXES (because `not pack_has_axes`). Wait — actually re-read: `ra is None and not pack_has_axes` → OK_NO_AXES. But if they set both hints, `ra is not None`. So the OK_NO_AXES branch only fires when `ra is None` (builder didn't form a pair). If the chargen scenes set the hints, `ra is not None`, gate falls into the else (raw_pair_unresolved). So the OR-vs-AND mismatch only matters when `ra is None` — when at most one hint was set. In that combined case (half-axis pack + half-set hints), the gate OK_NO_AXES'es a misconfigured pack. Semantically incorrect (the pack DID intend to use axes), but the failure is silent. THIS is the real risk of the docstring/code mismatch: a pack with one axis file present + scene that didn't fully set hints will pass OK_NO_AXES per the code, but the docstring (and content-author intuition) would expect it to block. Confirmed MEDIUM finding. Acceptable to ship as non-blocking but worth a follow-up.

**Edge case 3 — `apply_archetype_resolved` raises before stamping provenance:** If the apply itself raises (e.g., `resolution.resolved.name` is empty and a downstream validator catches), `archetype_provenance` is never set. The gate sees `not provenance_set` → falls into the else-branch (raw pair). With `pack_has_axes=True` → `block_reason = "resolver_raised"`. But the legacy `archetype_resolution_failed` event would NOT have fired (the resolver succeeded, only the apply failed). So the gate routes correctly (block) but the legacy-event semantics are slightly off — the test for "resolver_raised must fire archetype_resolution_failed" might fail in this scenario. Hypothetical: `apply_archetype_resolved` is so simple (two assignments) that it currently can't raise. So the edge case is theoretical.

**Edge case 4 — The wire-test inspect.getsource:** The new wire-test reads the live source of `WebSocketSessionHandler._chargen_confirmation` and greps for invocation patterns. If the method is decorated (e.g., a future `@require_chargen_active`), `inspect.getsource` returns the decorated source which still includes the original body — should still work. If the method body is moved into a `_chargen_confirmation_impl` helper called by `_chargen_confirmation`, the grep would miss it. The test would need to be updated then. Acceptable trade-off.

**Edge case 5 — caverns_and_claudes content fix scope creep:** Round 1 added `jungian_hint=hero, rpg_role_hint=jack_of_all_trades` to caverns scene 1. Every caverns character is now mechanically hero/jack_of_all_trades. Sebastien (mechanics-first) sees this on the GM panel and... yeah, it's canon for caverns delvers. Acceptable. But what if a future caverns world overlay wants different archetypes? The genre-level scene 1 hint becomes the de facto pack-canonical. Minor design lock-in. Out of scope for this story.

The Devil's Advocate found one real concern (the OK_NO_AXES OR-vs-AND mismatch when combined with half-set hints — but that's already the MEDIUM finding) and several theoretical edge cases. Net: no new HIGH or BLOCKING issue. The verdict stands.

## Reviewer Assessment

**Verdict:** APPROVED

**Round-1 outcome:** REJECTED with 2 HIGH (logger.warning + raw_pair_unresolved coverage) + 2 HIGH-DOC (stale "non-fatal" + "lying docstring") + 4 MEDIUM + 3 LOW.

**Round-2 outcome:** All round-1 HIGH and MEDIUM findings VERIFIED ADDRESSED across the four subagents. Round-2 surfaces 1 MEDIUM (cosmetic doc OR-vs-AND on OK_NO_AXES condition) + 4 LOW (stale line numbers, orphan section header, truthy assertion at one site, stale comment in DiscriminatorRobustness rationale). No HIGH, no Critical. Under the project's severity rubric, MEDIUM and below do not block the PR.

**Data flow traced:** WS `CharacterCreationMessage(phase="confirmation")` → `character_creation.HANDLER` → `_chargen_confirmation` → `builder.build()` → `_resolve_character_archetype` → `_gate_archetype_resolution` (NEW round-2 logic: `provenance_set` discriminator, three failure-mode shape inference, `logger.warning()` on block, two OTEL spans) → either `_error_msg(code="chargen_archetype_unresolved")` (BLOCKED_PARTIAL) or `apply_starting_loadout` + persist (passes). Discriminator now keys on `archetype_provenance is not None` — survives display names containing "/". Server-log surface independent of OTEL via `logger.warning()`.

**Pattern observed:** Sibling-helper-with-shape-inspection pattern, made more durable by switching from syntactic ("/") to semantic (`provenance_set`) discrimination. The `logger.warning()` + OTEL-span pair on the blocked path mirrors the existing Sebastien-axis pattern (OTEL for the GM panel + structured log for ops). Field rename (`had_both_hints` + `provenance_set`) is more honest about granularity than the original two-axis pretense.

**Error handling observed:** Gate returns `(is_blocked, block_reason)` tuple, caller short-circuits via typed ERROR frame. No exceptions raised by the gate itself; no swallowing. The legacy `character_creation.archetype_resolution_failed` event still fires for resolver-raised path (regression-protected by AC5). The new `logger.warning()` on BLOCKED_PARTIAL closes the round-1 rule-4 violation.

**Non-blocking findings table** (recommended cleanup, not required for this approval):

| Severity | Issue | Tag | Location | Fix Suggestion |
|----------|-------|-----|----------|----------------|
| [MEDIUM] | OK_NO_AXES condition: docstring claims `(base_archetypes is None AND archetype_constraints is None)`, code computes OR. The CODE matches the original story-context spec; the DOCSTRING used the wrong logical operator. A pack with only one axis file shipped + chargen scene that didn't form a pair would silently OK_NO_AXES per the code, but a maintainer reading the docstring would expect a block. | [DOC] | `sidequest/server/websocket_session_handler.py:657-661` | Change `(base_archetypes is None and archetype_constraints is None)` to `(base_archetypes is None or archetype_constraints is None)` to match the actual `not pack_has_axes` logic. |
| [LOW] | Stale line-number citations (5 sites) — round-2's gate-method rewrite shifted everything ~7 lines, but the citations weren't re-updated. Actual current line numbers: 581, 586, 602. Cited: 574, 579, 595. | [DOC] | `websocket_session_handler.py:668, 676, 679, 742, 886` | Update each cite to current positions. **Forward-looking recommendation:** future references should use symbolic anchors (function/method names, branch labels) rather than absolute line numbers — this is the third round of stale-line-number drift on this file. |
| [LOW] | `assert relevant` truthy-only at line 950 in `TestArchetypeGateLogging`. Same pattern that round-1 swept across 7 sites; this one was added in round 2 and missed. | [TEST]/[RULE] | `tests/server/test_45_6_chargen_archetype_gate.py:950` | Replace with `assert len(relevant) >= 1, ...` to match the swept form. |
| [LOW] | Stale "current shape-based discriminator misclassifies" comment describes pre-round-2 behavior in present tense. After Dev's discriminator switch, the test passes unconditionally; the comment is now inaccurate. | [DOC] | `tests/server/test_45_6_chargen_archetype_gate.py:965-976, 994-996` | Update to past tense: "With the old shape-based discriminator this test would have failed; the round-2 fix (provenance-based discriminator) is what makes it pass." |
| [LOW] | Orphaned "Wire test" section header at lines 877-885. After TEA inserted `TestArchetypeGateLogging` and `TestArchetypeGateDiscriminatorRobustness` at lines 903 and 980 respectively, the original wire-test header is no longer adjacent to `TestArchetypeGateWiring` (line 1067). | [DOC] | `tests/server/test_45_6_chargen_archetype_gate.py:877-885` | Either move the header block down to right before `class TestArchetypeGateWiring:`, or delete the orphan (the class has its own docstring). |

**[VERIFIED]** items (with round-2 evidence):
- **[VERIFIED]** Round-1 HIGH `[RULE]` rule-4 violation FIXED — `logger.warning()` at `websocket_session_handler.py:775-784` uses %-style lazy interpolation, fires on BLOCKED_PARTIAL only (after the early return at line 767-768), WARNING level, includes player_id + block_reason + context fields.
- **[VERIFIED]** Round-1 HIGH `[TEST]` `raw_pair_unresolved` coverage gap FIXED — `TestArchetypeGateRawPairUnresolved` at line 453 drives pack-axisless + raw-pair scenario; preflight confirms test passes.
- **[VERIFIED]** Round-1 HIGH `[DOC]` "non-fatal" docstring FIXED — `_resolve_character_archetype` docstring at lines 565-576 now describes the gate.
- **[VERIFIED]** Round-1 HIGH `[DOC]` "lying docstring" FIXED — gate docstring no longer claims a `resolver_raised flag`; describes pure shape inference.
- **[VERIFIED]** Round-1 MEDIUM `[TEST]` weak wiring test FIXED — replaced source-scan with `inspect.getsource(_chargen_confirmation)` body check (line 1067-1117) plus companion `hasattr` test for the def.
- **[VERIFIED]** Round-1 MEDIUM `[DOC]` brittle "/" discriminator FIXED — gate now uses `provenance_set = character.archetype_provenance is not None` (line 702, 725); `TestArchetypeGateDiscriminatorRobustness` confirms the `Sage/Healer` slash-in-name case routes to OK_RESOLVED.
- **[VERIFIED]** Round-1 MEDIUM `[RULE]` OTEL granularity loss FIXED — `had_jungian_hint`/`had_rpg_role_hint` collapsed into `had_both_hints: bool` + `provenance_set: bool`. Comment at lines 703-713 documents the trade-off vs threading-through.
- **[VERIFIED]** Round-1 MEDIUM `[TEST]` missing-negative regression FIXED — AC2 path now asserts legacy `archetype_resolution_failed` event does NOT fire.
- **[VERIFIED]** Round-1 LOW truthy assertions FIXED across 7 sites; only one new site (`assert relevant` at 950) introduced in round 2.
- **[VERIFIED]** Round-1 LOW `noqa: E402` REMOVED — `CONTENT_ROOT` moved into fixture body (now `content_root` local at lines 446-448); top-of-file imports clean.
- **[VERIFIED]** AC1 lockstep contract — `character.archetype_provenance is not None` asserted at test file line 286.
- **[VERIFIED]** Full server suite: 2707 passed / 0 failed / 34 skipped (preflight).
- **[VERIFIED]** Branch introduces zero new lint findings; pre-existing baseline at lines 322 / 412 unchanged.
- **[VERIFIED]** No code smells, no TODOs, no debug stubs (preflight).
- **[VERIFIED]** SPAN_ROUTES: both `chargen.archetype_gate_evaluated` and `chargen.archetype_gate_blocked` registered as `state_transition`/`character_creation` routes; `test_routing_completeness.py` passes (preflight).

**Handoff:** To SM (Vizzini) for the finish-story ceremony.

## Next Steps

1. **TEA (red phase):** Write a boundary test that exercises chargen completion without an archetype (mock the session, drive a character through chargen, assert that the READY transition fails or is gated).
2. **Dev (green phase):** Implement the gate assertion in the chargen state machine and wire it into the session handler path.
3. **Reviewer (review phase):** Verify the gate is reachable from the session handler (WS dispatch), confirm OTEL span fires, check that all playtest saves now load with valid archetypes (or block on chargen).