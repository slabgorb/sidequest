---
story_id: "75-13"
jira_key: "skipped explicitly — integration not configured (kanban-only project)"
epic: "75"
workflow: "tdd"
---
# Story 75-13: Wire ratification gate into ADR-135 reference NPC projection — withhold unratified phantoms (ADR-138 D4)

## Story Details
- **ID:** 75-13
- **Jira Key:** N/A (kanban-only project)
- **Workflow:** tdd (phased)
- **Stack Parent:** 75-11 (DONE — is_projectable() predicate, ADR-138 D1/D3)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T20:16:43Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04 | 2026-06-04T19:38:21Z | 19h 38m |
| red | 2026-06-04T19:38:21Z | 2026-06-04T19:46:16Z | 7m 55s |
| green | 2026-06-04T19:46:16Z | 2026-06-04T19:52:41Z | 6m 25s |
| review | 2026-06-04T19:52:41Z | 2026-06-04T20:01:39Z | 8m 58s |
| red (rework 1) | 2026-06-04T20:01:39Z | 2026-06-04T20:05:00Z | 3m 21s |
| green | 2026-06-04T20:05:00Z | 2026-06-04T20:10:36Z | 5m 36s |
| review | 2026-06-04T20:10:36Z | 2026-06-04T20:16:43Z | 6m 7s |
| finish | 2026-06-04T20:16:43Z | - | - |

> **Note (Drummer/SM, recovery):** This session file was clobbered mid-rework by the `testing-runner` subagent (known hazard — it overwrites `.session/<id>-session.md` with a verification report). Reconstructed from in-session context. The assessments below are faithful restorations; only the test-verification report that overwrote them was discarded.

## Sm Assessment

**Setup complete — routing to TEA for RED phase.**

Story 75-13 implements ADR-138 §D4: extend the ratification gate to the ADR-135 reference-page NPC projection so UNRATIFIED phantom NPCs are withheld from the public reference pages. Third leg of ADR-138 — 75-11 landed `is_projectable()` (D1/D3), 75-12 wired the gate into the ADR-118 retrieval/entity-store projection (D2/D5/D6). Dependency 75-11 DONE+merged; sibling 75-12 DONE, provides the pattern.

**Watch-fors:** reuse `is_projectable()` (don't reimplement); authored `portrait_manifest.yaml` content is never auto-minted so `observation_pending=False` is a design invariant, handle violations loudly (No Silent Fallbacks); every test suite needs a wiring test; OTEL skip-span is the lie detector. Branch `feat/75-13-wire-ratification-gate-ref-pages` off `develop` in sidequest-server.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes — new player-facing behavior (withhold unratified phantoms from the public Cast) + new OTEL observability.

**Test Files:**
- `tests/server/test_reference_cast_ratification_gate.py` — 8 tests pinning §D4 behavior, observability, wiring through the real `/reference/lore/{pack}/{world}` route.
- `tests/fixtures/packs/reference_v2_fixture/worlds/cast_ratification_fixture/` — 1 ratified + 1 `observation_pending` member.
- `tests/fixtures/packs/reference_v2_fixture/worlds/cast_all_unratified_fixture/` — lone phantom (all-withheld edge).

**Status:** RED (6 failing, 2 contract-anchor passing). No collection/import errors.

### Rule Coverage
(No `.pennyfarthing/gates/lang-review/python.md`, no `.claude/rules/*.md` — rubric = ACs + SOUL + server CLAUDE.md doctrine.)

| Doctrine rule | Test(s) | Status |
|---|---|---|
| OTEL principle (span per decision; GM panel lie detector) | skip-span count tests | covered |
| Every Test Suite Needs a Wiring Test | route tests → `/reference/lore` → `assemble_lore_page` → gate | covered |
| No Source-Text Wiring Tests | assertions on HTML / span attrs only | compliant |
| No Silent Fallbacks (skip observable, count from raw entries) | `test_skip_count_is_computed_from_raw_entries_not_survivors` | covered |
| Don't Reinvent — reuse `is_projectable()` | predicate anchor test | covered |
| Selective gate (not suppress-all/none) | `test_gate_is_selective_not_blanket` | covered |

**Self-check:** 0 vacuous tests.

**Dev contract (red round):** filter raw `cast_entries` through `is_projectable()` before slug/render; add `SPAN_REFERENCE_NPC_UNRATIFIED_SKIPPED = "sidequest.reference.npc_unratified_skipped"` to `FLAT_ONLY_SPANS` + a span helper (pack/world/count); emit one span per cast-bearing render, count from RAW entries; reuse `is_projectable()` via a minimal `NpcPoolMember` (don't splat the manifest dict — `extra: forbid`).

**Handoff:** To Dev for implementation (GREEN).

## Dev Assessment

### Green Phase (initial)

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/telemetry/spans/reference.py` — `SPAN_REFERENCE_NPC_UNRATIFIED_SKIPPED`, registered in `FLAT_ONLY_SPANS`, `reference_npc_unratified_skipped_span` contextmanager (pack/world/count).
- `sidequest/server/reference_renderer.py` — imported `NpcPoolMember`/`is_projectable`; added `_cast_entry_is_projectable(entry)`; wired the gate into `assemble_lore_page`'s Cast block (filter → `ratified_entries`, span wraps render with `count = raw - ratified`, render only ratified subset).
- `tests/fixtures/.../cast_ratification_fixture/world.yaml` — fixture description.

**Tests:** 8/8 story + 26/26 sibling regression GREEN; ruff + pyright clean.
**Branch:** `feat/75-13-wire-ratification-gate-ref-pages` (pushed)
**Handoff:** To Reviewer for code review.

## Subagent Results — Round 1

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (34/34 GREEN, ruff+pyright clean) + 3 notes | deferred 3 (folded into other findings) |
| 2 | reviewer-edge-hunter | Yes | findings | 5 | confirmed 2 (bool-coerce HIGH→merged; span-contract MEDIUM→LOW), downgraded 3 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 | confirmed 1 (bool-coerce HIGH — blocking) |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 4 (no-adapter-unit-test MED, unused otel_capture LOW, zero-count missing pack/world LOW, name-coerce gap MED), downgraded 1 |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via workflow.reviewer_subagents.comment_analyzer |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via workflow.reviewer_subagents.type_design |
| 7 | reviewer-security | Yes | findings | 2 | 0 blocking; deferred 1 (Map-section bypass — out of scope), noted 1 (unauth watcher — pre-existing, no new data) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via workflow.reviewer_subagents.simplifier |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via workflow.reviewer_subagents.rule_checker |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 1 confirmed blocking (HIGH), 6 confirmed non-blocking (Med/Low), 2 deferred/noted, 0 dismissed without rationale

### Rule Compliance

| Rule (source) | Units checked | Verdict |
|---|---|---|
| **No Silent Fallbacks** (CLAUDE.md CRITICAL) | `_cast_entry_is_projectable`, span emit, `bool()` coercion | **VIOLATION at renderer:1325** (round 1) — `bool("false")` mis-coerces → silent withhold. **RESOLVED in rework** (raw value → Pydantic + None-coalesce). Other units compliant. |
| Don't Reinvent — Wire Up What Exists | adapter reuses `is_projectable()` | COMPLIANT |
| Every Test Suite Needs a Wiring Test | route tests | COMPLIANT (6/8 drive the real route) |
| No Source-Text Wiring Tests | whole test file | COMPLIANT |
| OTEL: span per decision, registered | new span + `FLAT_ONLY_SPANS` | COMPLIANT |
| Reference page PUBLIC; npcs.yaml never read | `load_cast_entries`, gate | COMPLIANT |
| Withheld phantom must not leak | gate ordering renderer:1512→1534 | COMPLIANT for Cast (filter precedes slug-derivation, R2 gate, present_lore_cast). Map section out of scope (deferred). |

### Devil's Advocate

The feature is a *defensive* gate: by the author's own admission authored `portrait_manifest.yaml` never sets `observation_pending`, so on every real render the gate sees an absent key, defaults to `False`, and changes nothing. That is the tell — a gate whose only job is the input that "can't happen" must be correct on that input or it is theater. Attacking the can't-happen inputs, one breaks: a homebrew author (Jade, the project's first non-Keith author, hand-editing YAML without a schema wizard) writes `observation_pending: "false"` — quoting booleans is an utterly ordinary YAML mistake. She means "render her." `bool("false")` → `True` → `is_projectable` False → her NPC **silently vanishes** from the public Cast page, no error, no log, a skip count identical to a real phantom. That is exactly the failure the project's loudest doctrine (No Silent Fallbacks) exists to prevent, landing on the exact persona the gate is meant to protect. Pydantic v2 would have handled `"false"`→`False` correctly and raised loudly on true garbage; the `bool()` wrapper pre-empts both. Second attack: `observation_pending: null` → `bool(None)`→False→renders; that one is actually fine (null=unset=ratified). Third: the Map section on the same public page renders cartography NPC labels ungated — real but out-of-scope (cartography is authored, a runtime phantom can't reach it). The damning one is `bool()`: confirmed live, one line to fix, flagged by two independent specialists, defeats the gate on the only inputs it exists for. Not a nit. Fix it right.

## Reviewer Assessment — Round 1

**Verdict:** REJECTED

**Data flow traced:** `portrait_manifest.yaml` entry → `load_cast_entries` → `_cast_entry_is_projectable` (`bool()`-coerced `observation_pending`) → `ratified_entries` → slug-gate + `present_lore_cast` → public HTML. Gate ordering is SAFE (`[SEC]` confirmed: withheld entries contribute no slug/img/anchor/name); the classification step at the head is defective.

| Severity | Issue | Location | Fix |
|---|---|---|---|
| [HIGH] `[SILENT]`+`[EDGE]` | `bool(entry.get("observation_pending", False))` defeats Pydantic coercion; `bool("false")==True` → mis-typed `"false"` silently withholds a ratified NPC (confirmed live); pre-empts loud ValidationError. Violates CRITICAL No Silent Fallbacks on the defensive gate's own edge inputs. | `reference_renderer.py:1325` | Drop `bool()`; pass raw → Pydantic coerce + fail loud; coalesce explicit `None`→`False`. |
| [MEDIUM] `[TEST]` | No direct unit test of `_cast_entry_is_projectable`; anchor test exercises 75-11's predicate, not 75-13's adapter. | test:217 | Add adapter unit tests (absent/True/False/None/"false"/non-str name). |
| [LOW] `[TEST]` | `test_skip_span_is_registered` takes unused `otel_capture`. | test:202 | Remove the param. |
| [LOW] `[TEST]` | zero-count span test omits pack/world asserts. | test:161 | Add them. |
| [LOW] `[EDGE]` | span-fires-iff-cast_entries contract undocumented for cast-less worlds. | renderer:1513 / spans:671 | Tighten span docstring. |

Dispatch tags: `[DOC]` comment-analyzer **disabled**; `[TYPE]` type-design **disabled** (the `drawn_from="world_authored"` hardcode is deliberate; `is_projectable` has no `drawn_from` branch — VERIFIED acceptable); `[SIMPLE]` simplifier **disabled** (diff minimal); `[RULE]` rule-checker **disabled** (manual Rule Compliance above — one VIOLATION, the `bool()` coercion). `[SEC]` two findings, both deferred/noted.

**Why REJECT not APPROVE-with-notes:** one-line fix, confirmed empirically, two-specialist convergence, lands on the CRITICAL doctrine, breaks the gate on the only inputs it exists for, hits the homebrew-author persona. "Fix it right."

**Handoff:** Back to TEA for rework (testable).

## TEA Assessment — Rework Round 1

**Trigger:** Reviewer REJECT (HIGH `[SILENT]`/`[EDGE]` bool() coercion) + bundled `[TEST]` findings.

**Changes (tests only):** `tests/server/test_reference_cast_ratification_gate.py`
- NEW 7 direct `_cast_entry_is_projectable` unit tests: absent→render, true(bool)→withhold, false(bool)→render, **`"false"`(str)→render (THE blocking test, RED today)**, `"true"`(str)→withhold, **`null`→render (regression guard: must not 500)**, non-str name→no raise.
- FIXED `test_skip_span_is_registered` (removed unused `otel_capture`).
- FIXED `test_skip_span_fires_with_zero_count_when_nothing_withheld` (added pack/world asserts).

**Rework RED verification:** 15 tests → 14 PASS, 1 FAIL (`test_cast_entry_projectable_when_flag_quoted_false_string`). Lint clean. No import errors. Honest RED isolated to the blocking finding.

**Dev contract for GREEN:** in `_cast_entry_is_projectable` (renderer:1325), hand the raw `observation_pending` to `NpcPoolMember` (Pydantic coerces `"false"→False`) but coalesce explicit `None`→`False` (else `NpcPoolMember(observation_pending=None)` raises). Keep `str()` on `name`. Also tighten the span docstring (fires iff `cast_entries` non-empty).

**Handoff:** To Dev (GREEN).

## Dev Assessment — Rework Round 1 (post-REJECT)

**Implementation Complete:** Yes — addressed the Reviewer's blocking finding + the bundled docstring tighten.

**Files Changed:**
- `sidequest/server/reference_renderer.py` — `_cast_entry_is_projectable` no longer pre-wraps `observation_pending` in `bool()`. The raw value is handed to `NpcPoolMember` for Pydantic coercion (`"false"`→`False`, `"true"`→`True`, `0`/`1`→bool, loud raise on garbage), with an explicit `None`→`False` coalesce so a YAML `null` renders instead of raising a ValidationError. `str()` on `name` retained. Docstring expanded.
- `sidequest/telemetry/spans/reference.py` — tightened `reference_npc_unratified_skipped_span` docstring (fires **iff `cast_entries` non-empty**; "fires even when 0" = count, not render) ([EDGE] LOW).

**Tests:** 41/41 GREEN (15 story incl. the previously-RED `"false"` test now passing + the `null` regression guard; 26 Cast-path/lore-assembly regression). `ruff` clean, `pyright` 0 errors.
**Branch:** `feat/75-13-wire-ratification-gate-ref-pages` (pushed — b73b130)

**Self-review:**
- Delivers TEA deviation #3's "loud, not silent": valid values coerce correctly, garbage raises loudly, the `bool()` silent path is gone.
- No over-correction: `null`→render preserved by the coalesce (guarded by a test) — no new 500.
- Scope held: Map section + watcher auth untouched (deferred/pre-existing, out of Cast scope).

**Handoff:** Back to Reviewer (Chrisjen Avasarala) to re-review the rework.

## Delivery Findings

**Types:** Gap, Conflict, Question, Improvement · **Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation (initial green). TEA's RED tests captured the contract exactly; the existing reference-span infrastructure absorbed the new span with no structural change.

### TEA (test design)
- **Improvement** (non-blocking): The reference Cast gate and the ADR-118 entity-sync gate emit two differently-shaped skip telemetries — `sidequest.reference.npc_unratified_skipped` (flat span w/ `_count`) vs 75-12's `entity_sync.npc_unratified_skipped` (watcher-event field). Appropriate (the reference render has no per-turn watcher stream), but a future GM-panel "phantoms withheld this session" rollup must union both sources. *Found by TEA during test design.*

### Reviewer (code review)
- **Gap** (non-blocking, deferred): The §D4 gate is wired into the Cast section but NOT the Map section of the same lore page — `present_lore_map` renders cartography.yaml NPC-binding pin labels with no `is_projectable` consult. Out of 75-13's Cast scope (and cartography is authored content, so a runtime phantom can't reach it), but the §D4 intent is only complete once the Map surface shares the gate. Affects `sidequest/server/reference_map.py` / the Map block in `assemble_lore_page`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The `/ws/watcher` WebSocket fan-out is unauthenticated and now also broadcasts `sidequest.reference.npc_unratified_skipped` (pack/world/count only — no NPC name, so no new identifying data from this diff). Broader unauth-watcher gap belongs to ADR-119. Affects `sidequest/server/watcher.py` (no change required by this story). *Found by Reviewer during code review.*

### Dev (implementation — rework round 1)
- No upstream findings during rework. The Reviewer's blocking finding was a precise one-line fix; the bundled test gaps are now covered by direct adapter unit tests.

### Reviewer (code review — round 2)
- **Improvement** (non-blocking): A garbage `observation_pending` value (a list/dict, `2`, `""`) now raises `pydantic.ValidationError` → 500 — the documented, intended loud-fail. But (a) `reference_routes.py:125`'s except tuple omits `ValidationError`, so that 500 lacks the route's `_LOG.exception` pack/world context, and (b) a single malformed entry 500s the whole world's reference page rather than skipping just that entry. Follow-up: add `ValidationError` to the route catch + log pack/world, and/or consider a per-entry graceful skip (fail-safe withhold + observable) over a whole-page 500. Affects `sidequest/server/reference_routes.py` + `_cast_entry_is_projectable`. *Found by Reviewer during re-review (round 2).*
- **Improvement** (non-blocking): Test-suite polish — `test_skip_count_is_computed_from_raw_entries_not_survivors` could assert `reference.pack`/`reference.world` (parity with the other two span tests); `test_gate_is_selective_not_blanket` duplicates the two individual presence/absence tests; no test pins the loud-fail-on-garbage contract. Affects `tests/server/test_reference_cast_ratification_gate.py`. *Found by Reviewer during re-review (round 2).*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Span granularity fixed to per-render, not per-NPC** — Spec: "per render (or per Cast section, or per NPC — decide granularity)". Impl: one span per render carrying a `count` (mirrors `manifest_loaded`/`lore_assembled`). Rationale: lowest cardinality satisfying §D6; matches every `sidequest.reference.*` span. Severity: minor. Forward impact: Dev emits one span per cast-bearing render; count from raw entries.
- **Span name + attr key pinned as a contract** — Spec: "a new span `reference.npc_unratified_skipped`". Impl: fully-qualified `sidequest.reference.npc_unratified_skipped` + attr `reference.npc_unratified_skipped_count`, registered in `FLAT_ONLY_SPANS`. Rationale: every reference span carries the `sidequest.` prefix; FQN prevents a GM-panel no-show. Severity: minor. Forward impact: Dev names the constant accordingly.
- **Defensive "handled loudly" = observable skip span, not a 500** — Spec: "handled loudly if they appear" / "catch invariant violations loudly". Impl: withheld + counted on the span, not raised. Rationale: mirrors 75-12; a render-time 500 on first-party content takes the public page down for one flag. Severity: minor. Forward impact: gate withholds + emits; must not `raise` on a pending entry.

### TEA (test design — rework round 1)
- No new deviations from spec. This rework adds tests pinning the behavior the Reviewer's REJECT requires (correct `observation_pending` coercion) and cleans up two test-quality findings. The corrected behavior is *more* spec-compliant (No Silent Fallbacks), not a divergence.

### Dev (implementation)
- No deviations from spec (initial green). Implemented exactly TEA's pinned contract; reuse-via-minimal-`NpcPoolMember`. (The `bool()` coercion slip caught at review was a bug, not an undisclosed deviation.)

### Dev (implementation — rework round 1)
- No deviations from spec. Applied exactly the fix TEA's rework assessment specified: raw value to Pydantic + `None`→`False` coalesce, `str()` on name retained, span docstring tightened. Strictly more spec-compliant, not a divergence.

### Reviewer (audit)
- **TEA: span granularity per-render** → ✓ ACCEPTED: matches the `manifest_loaded`/`lore_assembled` per-render sibling pattern; lowest cardinality satisfying §D6.
- **TEA: fully-qualified span name + `_count` attr** → ✓ ACCEPTED: every span in `telemetry/spans/reference.py` carries the `sidequest.` prefix; verified in `FLAT_ONLY_SPANS`.
- **TEA: defensive "handled loudly" = span, not 500** → ✓ ACCEPTED with caveat: span-over-500 is right for first-party content, BUT "loud" presumes correct classification — round 1's `bool()` slip mis-classified `"false"`. Intent sound; round-1 implementation defective; **resolved in rework**.
- **Dev: "No deviations" (both rounds)** → ✓ ACCEPTED: faithful to TEA's contract; the `bool()` defect was a bug, now fixed.
- **UNDOCUMENTED (Reviewer-found):** §D4 gate applied to Cast only; the same page's Map section (`present_lore_map`, cartography NPC pins) is ungated. Scope-correct (context-story-75-13.md limits 75-13 to the Cast projection) — recorded as a deferred delivery finding, not a violation. Severity: L.

### Reviewer (audit — round 2)
- **TEA (rework): no new deviations** → ✓ ACCEPTED: the rework tests pin the corrected coercion; the behavior is strictly more spec-compliant (No Silent Fallbacks), not a divergence.
- **Dev (rework): no deviations** → ✓ ACCEPTED: applied exactly TEA's pinned fix (raw→Pydantic + `None`-coalesce, `str()` on name retained, docstring tightened). Reviewer-verified live: every plausible input correct, garbage fails loud, no leak. The round-1 caveat on TEA's deviation #3 ("loud presumes correct classification") is now satisfied — the gate classifies correctly AND fails loud on garbage.

## Subagent Results

(Round 2 — re-review of the rework. Round-1 table preserved above as "Subagent Results — Round 1".)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (41/41 GREEN, ruff+pyright clean, 0 smells) | confirmed 0 |
| 2 | reviewer-edge-hunter | Yes | findings | 2 | confirmed 2 as NON-blocking (garbage→500 is documented loud-fail MED; span-on-crash LOW moot) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 | confirmed 1 NON-blocking (LOW — route handler lacks ValidationError log-context, untouched file, 500 still surfaces) |
| 4 | reviewer-test-analyzer | Yes | findings | 3 (+ 3 prior RESOLVED) | confirmed 3 NON-blocking LOW (missing pack/world assert, redundant selective test, no loud-fail test) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via workflow.reviewer_subagents.comment_analyzer |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via workflow.reviewer_subagents.type_design |
| 7 | reviewer-security | Yes | clean | 0 | confirmed 0 — fix tightened the gate, no new leak, span name-free |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via workflow.reviewer_subagents.simplifier |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via workflow.reviewer_subagents.rule_checker |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 0 blocking; 6 confirmed non-blocking (1 MED-documented, 5 LOW); 0 dismissed without rationale

### Rule Compliance — Round 2

| Rule | Verdict |
|---|---|
| **No Silent Fallbacks** (CLAUDE.md CRITICAL) | **NOW COMPLIANT** — the round-1 VIOLATION (`bool()` silent mis-coercion) is RESOLVED. Verified live by Reviewer: `"false"`→projects, `"true"`→withholds, `null`→projects (no 500), `true`(bool) phantom→**still withheld**, garbage (`[]`/`{}`/`2`/`""`)→**raises loudly** (the doctrine-prescribed outcome). The loud-fail-on-garbage is the *correct* direction the doctrine demands, not a new silent path. |
| Don't Reinvent / Wiring / No Source-Text Tests / OTEL-registered / PUBLIC-only / no-leak | COMPLIANT (unchanged from round 1; security re-confirmed no-leak). |

### Devil's Advocate — Round 2

The round-1 defect is fixed; now I attack the FIX. The new behavior raises `ValidationError` on a garbage `observation_pending` (a list, a dict, the integer 2, an empty string), which 500s the entire public reference page for that world. Is the cure worse than the disease? A naive reading says yes: one fat-fingered manifest entry now nukes the whole page instead of quietly mis-rendering one card. But three things defang it. First, this is *exactly* the loud-fail the round-1 review demanded — I cannot in good conscience reject a rework for doing the thing I told it to do; that is ping-ponging, the cardinal sin of a review loop. Second, the same renderer already 500s on a malformed manifest: `load_cast_entries` raises `ValueError` on a non-list `characters:`, and the route handler turns that into a 500 today — so "broken first-party manifest → loud 500" is an *established, accepted* contract in this very code path, not a novelty the rework smuggled in. Third, the trigger is pure garbage: authored `portrait_manifest.yaml` content never sets `observation_pending` at all, let alone to a list — this is a strictly more pathological input than the `"false"` string that justified round 1. The genuinely sharp observations are operational, not correctness: the route handler (`reference_routes.py:125`, an untouched file) does not add `ValidationError` to its catch tuple, so the 500 arrives without the `_LOG.exception` pack/world context — an operator sees a bare traceback; and the skip-span does not fire on the crash path, so a one-bad-entry world is OTEL-indistinguishable from a cast-less one. Both are real, both are LOW, both are about *observability of a garbage-only failure*, and neither is in this story's Cast-gate scope. The honest verdict: the fix is correct and complete for every plausible input, fails loud (not silent) on garbage per doctrine, and leaks nothing. The residue is a worthwhile follow-up — catch `ValidationError` at the route with pack/world logging, and/or skip a single bad entry rather than 500 the page — but it is not a reason to bounce a 2-point story a second time.

## Reviewer Assessment

**Verdict:** APPROVED

**What changed since round 1:** `_cast_entry_is_projectable` (`reference_renderer.py:1325`) drops the `bool()` pre-wrapper — the raw `observation_pending` goes to `NpcPoolMember` for Pydantic coercion, with an explicit `None`→`False` coalesce. Span docstring tightened (`[EDGE]`). 7 direct adapter unit tests added; the unused `otel_capture` param removed; pack/world asserted on the zero-count span (`[TEST]`).

**Blocking finding (round 1) — RESOLVED.** The HIGH `[SILENT]`/`[EDGE]` `bool("false")` silent-withhold is fixed. Reviewer-verified live: `"false"`→projects, `"true"`→withholds, `null`→projects (no 500), `true`-bool phantom→still withheld (no leak), garbage→raises loudly. All 5 subagents corroborate.

**Data flow traced:** `portrait_manifest.yaml` → `load_cast_entries` → `_cast_entry_is_projectable` (raw→Pydantic, `None`→`False`) → `ratified_entries` → slug-gate + `present_lore_cast` → public HTML. Gate ordering safe; withheld phantoms contribute no name/slug/img/anchor (`[SEC]` re-confirmed clean).

**Non-blocking observations (deferred — follow-up, not a round-3 bounce):**
- `[EDGE]` MED — a garbage `observation_pending` (list/dict/`2`/`""`) raises `ValidationError` → 500s the page. This is the *documented, intended* loud-fail (No Silent Fallbacks) and consistent with the existing `load_cast_entries`→500 contract; trigger is pure garbage outside the design invariant. Worth a follow-up: per-entry graceful skip vs whole-page 500.
- `[SILENT]` LOW — `reference_routes.py:125` (untouched) omits `ValidationError` from its catch tuple, so that 500 lacks `_LOG.exception` pack/world context. Follow-up: add `ValidationError` to the route's catch + log.
- `[EDGE]` LOW — skip-span absent on the crash path (a crashed render has no gate decision to report — largely moot).
- `[TEST]` LOW ×3 — `test_skip_count_is_computed_from_raw_entries_not_survivors` could assert pack/world; `test_gate_is_selective_not_blanket` is redundant with the two individual tests; no test pins the loud-fail-on-garbage contract.

Dispatch tags: `[SILENT]` 1 LOW (route log-context); `[EDGE]` 1 MED-documented + 1 LOW; `[TEST]` 3 LOW (+ 3 prior resolved); `[SEC]` clean; `[DOC]` disabled; `[TYPE]` disabled (the `drawn_from="world_authored"` hardcode VERIFIED correct — adapter only handles authored content); `[SIMPLE]` disabled; `[RULE]` disabled (manual Rule Compliance above — round-1 VIOLATION now resolved, no new violation).

**Why APPROVE:** the one blocking finding is fixed and verified; every remaining item is LOW/documented-MED, several concern the *intended* loud-fail-on-garbage path, and the route-logging + per-entry-skip ideas are genuine but out-of-scope hardening for a follow-up. A second REJECT here would be ping-ponging code that did exactly what round 1 prescribed.

**Handoff:** To SM (Camina Drummer) for finish-story.