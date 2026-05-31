---
story_id: "72-3"
jira_key: "none"
epic: "72"
workflow: "tdd"
---
# Story 72-3: MM NPC provenance through the injection seam — NpcPatch manual_origin, preserved through merge

> **Recovery note (2026-05-30, TEA verify phase):** This session file was inadvertently
> overwritten by a `testing-runner` subagent that wrote a "test result cache" to this path
> during the verify-phase full-suite run. `.session/` is gitignored, so it was reconstructed
> from the in-session conversation record (every prior read + edit). All assessments,
> deviations, and findings below are faithful to what each phase wrote; the Testing Strategy
> "Integration Tests" sub-bullets and exact phase-history timestamps are best-effort
> reconstructions. The code, tests, and git history are unaffected.

## Story Details
- **ID:** 72-3
- **Jira Key:** none (no Jira integration for this project)
- **Epic:** 72 — NPC Identity Hardening
- **Workflow:** tdd (phased)
- **Stack Parent:** none
- **Points:** 3
- **Priority:** p2
- **Type:** bug

## Context

Monster-Manual (MM) pre-generated NPCs are injected into the game world via the ADR-059 injection seam (`sidequest/server/dispatch/monster_manual_inject.py`). These NPCs are materialized as `Npc` records in the snapshot via `NpcPatch` objects that carry mechanical and flavor data.

Currently, there is **no provenance marker** distinguishing MM-injected NPCs from narrator-invented NPCs. This creates a blind spot: the GM panel cannot verify whether an NPC currently in the world originated from the Monster Manual or was created on-the-fly by the narrator. Per the OTEL observability principle (CLAUDE.md), every subsystem decision must emit spans that allow the GM panel to serve as a lie-detector — proving the system works as intended rather than silently improvising.

**Root cause:** The `NpcPatch` model lacks a provenance field, and the NPC merge pipeline (`_merge_npc_patch` / `_npc_from_patch`) has no logic to preserve such a marker when patches are reapplied or merged.

**Example scenario (from epic context):**
- Turn 1: An MM creature patch injects a "Chalk Moth" into `snapshot.npcs`.
- Turn 2: The party moves to a different location. The session reloads the MM, and a new patch is generated for the same creature. On merge, the patch fields overwrite the Npc fields — but there is no marker to declare "this update came from the Manual, not narrator invention."
- The GM panel has no way to distinguish this update chain from a narrator who invented the creature out of thin air.

**Load-bearing requirement:** The fix must emit an OTEL watcher event so the GM panel can verify MM provenance is preserved through the merge, not silently dropped (matching the "No Silent Fallbacks" doctrine).

## Technical Approach

> **NOTE (superseded by RED contract):** The original SM Technical Approach below proposed
> `manual_origin: str | None` and a *new* OTEL span. TEA's RED tests + the story context
> (`context-story-72-3.md`) adjudicated this to a **boolean** marker on an **extended existing
> span**. The boolean + extended-span design is the binding contract — see Design Deviations
> (TEA + Dev) and the Architect spec-check assessment. The text below is preserved for the record.

### 1. Add `manual_origin` field to `NpcPatch` (sidequest/game/session.py)

Original sketch: `manual_origin: str | None = None`. **Implemented as `manual_origin: bool = False`.**

### 2. Populate `manual_origin` in MM injection seam (monster_manual_inject.py)

`_human_patch()` and `_creature_patch_from_enemy()` set the marker on the returned `NpcPatch`. **Implemented:** both construct `NpcPatch(..., manual_origin=True)`.

### 3. Preserve `manual_origin` in the merge pipeline

`_merge_npc_patch()` carries the marker; `_npc_from_patch()` sets it on the fresh `Npc`. **Implemented:** `_merge_npc_patch` uses monotonic OR (`npc.manual_origin = npc.manual_origin or patch.manual_origin`); `_npc_from_patch` passes `manual_origin=patch.manual_origin`.

### 4. Add `manual_origin` field to the `Npc` class

Alongside `pool_origin`. **Implemented as `manual_origin: bool = False`.**

### 5. Emit OTEL on provenance decision

Original sketch: a *new* span (`npc_manual_origin_preserved`) with `provenance_source`/`action` attributes, fired in both `_npc_from_patch` and `_merge_npc_patch`. **Implemented:** a single `manual_origin: bool` attribute added to the existing per-NPC `npc.spawn_disposition` span (per context Assumption 4 — prefer extension, avoid GM-panel dashboard churn). Merge-path span deferred (see Delivery Findings).

## Acceptance Criteria

(Original ACs phrased the field as `str | None`; the binding contract is the boolean marker per the story context. AC semantics — carries / survives / queryable / OTEL'd / backward-compatible — are unchanged.)

1. **AC1: NpcPatch carries provenance marker** — declared field, optional/defaulted, `extra="forbid"` validates with and without it.
2. **AC2: marker survives materialization into the canonical Npc** — both the fresh-materialize (`_npc_from_patch`) and the name-collision merge (`_merge_npc_patch`) legs record it.
3. **AC3: Npc stores the marker** — declared field, round-trips through Pydantic/JSON.
4. **AC4: OTEL span carries provenance** — the materialization/inject decision emits a span attribute recording provenance.
5. **AC5 (orig.): OTEL emission verifies preservation** — see Architect spec-check: reconciled to AC4's lighter single-attribute-on-existing-span shape; merge-path span deferred.
6. **AC6: backward compatibility** — existing saves/patches load with the field defaulting to the non-MM value; narrator NPCs read not-manual-origin.

**Edge cases:** E1 — narrator-invented NPC must NOT get the marker. E2 — merge collision: MM authorship is authoritative (forward sets, reverse never clears) — monotonic.

## Testing Strategy

### Unit Tests (`tests/game/test_npc_manual_origin.py`)
1. NpcPatch field default + accepts marker + declared-field-not-extra (AC1).
2. Npc field default + declared + pydantic/JSON round-trip (AC3).
3. Marked patch materializes manual-origin Npc via `apply_world_patch` (AC2 fresh leg).
4. Marked patch records marker on existing Npc via merge (AC2 merge leg).
5. Narrator patch materializes non-manual-origin (E1 negative).
6. E2 forward (MM over invented → manual-origin) + E2 reverse (narrator patch does not clear).

### Integration / Wiring Tests (`tests/integration/test_npc_manual_origin_otel.py`)
- Drive the **real** `monster_manual_inject.inject()` production path under `WatcherSpanProcessor` capture: marker reaches `snapshot.npcs` (AC3 wiring) AND `npc.spawn_disposition` span carries `manual_origin=True` (AC4), for both a Manual creature and a Manual human.
- Narrator-path patch fires the same span with `manual_origin=False` (E1 at span level).

## Deferred / Out of Scope
- **Monster Manual seeding logic:** The story assumes the MM is already loaded and available. Seeding tuning (ADR-059) is separate.
- **Narrator-side awareness:** The narrator does not currently read `manual_origin` from the snapshot. Surfacing provenance in narrator context is a separate story.
- **Identity drift:** Story 72-7 (identity drift — overwrite pronoun/role on re-mention) is orthogonal to this provenance marker.

## Dependencies
- **Epic 72-1** (Revive NPC development pipeline) — merged OTEL watcher spans into the NPC spawn flow. This story reuses that span infrastructure.
- **Epic 72-5** (born-hostile default) — owns the `npc.spawn_disposition` span this story extends and the `disposition=-20 if is_creature` default this story must not touch.
- **ADR-059** (Monster Manual pre-generation) — already live. This story adds wiring to the existing injection seam.
- **ADR-031 / ADR-103** (OTEL observability) — span definitions and watcher hooks already live.

## Delivery Findings

No upstream findings.

### TEA (test design)
- **Improvement** (non-blocking): `_merge_npc_patch` (`session.py:1466`) mutates NPC state with **no OTEL span** today — the merge leg is a silent state change. This story makes it carry `manual_origin` (E2 collision: invented→manual is a meaningful authorship flip), but per the context AC4 scope the span attribute is asserted only on the materialization span (`npc.spawn_disposition`, fired in `_npc_from_patch`). A future story could add a merge-provenance span so an invented→manual flip on collision is GM-panel-visible, not just a field write. Affects `sidequest/game/session.py` (`_merge_npc_patch`). *Found by TEA during test design.*
- **Improvement** (non-blocking): `tests/server/dispatch/test_monster_manual_inject.py::test_websocket_session_handler_wires_monster_manual_inject` uses `handler_src.read_text()` source-grep assertions — exactly the pattern `sidequest-server/CLAUDE.md` "No Source-Text Wiring Tests" now prohibits. Pre-existing debt, out of 72-3 scope; flagging for a future cleanup to an OTEL/behavior wiring test. Affects `tests/server/dispatch/test_monster_manual_inject.py`. *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings. (Two pre-existing pyright errors in `session.py` — line ~900 `object`→`ConvertibleToFloat` and line ~1557 `Literal[-20,0]`→`Disposition` — were confirmed present on the base commit before this story's edits and are outside 72-3 scope; not introduced here.)

### Reviewer (code review)
- **Improvement** (non-blocking): Three `asyncio.sleep(0)` calls in `tests/integration/test_npc_manual_origin_otel.py` (lines 164/193/222) lack the explanatory comment that lang-review check #9 requires. The new tests faithfully reproduce the *established* uncommented pattern in the sibling OTEL tests (`test_npc_spawn_disposition_otel.py`, `test_npc_identity_seed_otel.py`, `test_disposition_threshold_crossing.py`). Recommend a one-line comment (e.g. `# yield so the WatcherSpanProcessor flushes the span before we assert`) here and, ideally, a sweep across the sibling OTEL tests. Affects `tests/integration/test_npc_manual_origin_otel.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The `npc_spawn_disposition_span` `pool_origin` docstring (`disposition.py:75-93`, pre-existing, NOT in this diff) was flagged by comment-analyzer as polarity-inverted. On inspection it is actually consistent with the call sites (it describes the span-param value, not the `Npc.pool_origin` field). No action needed for 72-3; noting for the record only. Affects `sidequest/telemetry/spans/disposition.py`. *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- **Provenance modelled as `bool`, not `str | None`**
  - Spec source: `.session/72-3-session.md` → "Technical Approach" (SM), and `context-story-72-3.md` Assumption 1
  - Spec text: SM's Technical Approach proposed `manual_origin: str | None = None` (source markers `"manual_human"` / `"manual_creature"`); context Assumption 1 says "A boolean flag is the minimal shape; an enum is acceptable if it stays consistent."
  - Implementation: Tests pin `manual_origin: bool = False` on both `NpcPatch` and `Npc`.
  - Rationale: The context's ACs are binary ("provenance reads as manual-origin / not") and never ask to distinguish Manual-human from Manual-creature — `is_creature` (and the existing `npc.spawn_disposition` `provenance` dial) already carries that. A boolean also gives unambiguous, monotonic merge semantics for E2 (MM authority wins; never cleared = logical OR), whereas `str | None` invites "which string wins" ambiguity. Minimal correct shape.
  - Severity: minor
  - Forward impact: If a future story needs to record *which* Manual source authored an NPC, the boolean can widen to an enum/str without breaking the binary contract these tests pin (truthy = manual-origin). Dev (Puck): if you prefer the enum now, the merge semantics must stay monotonic (an authored marker is never cleared by a later narrator patch).
- **E2 collision authority pinned to monotonic OR (set-only, never clear)**
  - Spec source: `context-story-72-3.md` → Edge case E2, Assumption 3
  - Spec text: "MM authorship is authoritative on the marker … the engine should not silently keep 'invented' when an authored MM patch arrives. (Symmetric reverse — narrator patch arriving for an NPC already marked manual-origin — should not *clear* the MM marker.)"
  - Implementation: `_merge_npc_patch` must set `npc.manual_origin = npc.manual_origin or patch.manual_origin` (forward sets True; reverse never clears). Pinned by `test_merge_mm_patch_over_invented_npc_records_manual_origin` and `test_merge_narrator_patch_does_not_clear_manual_origin`.
  - Rationale: The context defines both directions but leaves the mechanism open; OR is the only semantics satisfying both clauses without a precedence table. Documented in the test names so the behavior is pinned, not silently chosen.
  - Severity: minor
  - Forward impact: none — this is the documented default; revisit only if the epic owner wants narrator authorship to override Manual authorship (it currently must not).

### Dev (implementation)
- **OTEL provenance attached to the existing span, not a new span**
  - Spec source: `.session/72-3-session.md` → "Technical Approach" §5 (SM), and `context-story-72-3.md` Assumption 4
  - Spec text: SM's Technical Approach §5 proposed a *new* span `npc_manual_origin_preserved` / `npc_merge_provenance_decision` with `action`/`provenance_source` attributes; context Assumption 4 says "attaches to an existing materialization/inject span … rather than a brand-new span, to avoid GM-panel dashboard churn. Prefer extension."
  - Implementation: Added a single `manual_origin: bool` attribute to the existing `npc.spawn_disposition` span (`telemetry/spans/disposition.py` — already fires per-NPC in `_npc_from_patch` from 72-5). No new span; no `action` discriminator.
  - Rationale: Context Assumption 4 explicitly prefers extension over a new span, and TEA's AC4 test asserts the attribute on `npc.spawn_disposition`. One attribute satisfies the lie-detector requirement with zero dashboard churn. The SM Technical Approach text is superseded by the context + the RED contract.
  - Severity: minor
  - Forward impact: The merge leg (`_merge_npc_patch`) still emits no span — an invented→manual flip on collision is a field write only, not GM-panel-visible. Carried as TEA's non-blocking Delivery Finding for a future story; not in 72-3 scope (AC4 scopes the span to materialization).
- **`bool` representation + monotonic-OR merge — implemented per TEA's RED contract**
  - Spec source: `## Design Deviations → TEA (test design)` (this file); `context-story-72-3.md` Assumptions 1 & 3
  - Spec text: SM's Technical Approach proposed `manual_origin: str | None = None` with `if patch.manual_origin is not None: npc.manual_origin = patch.manual_origin` merge logic.
  - Implementation: `manual_origin: bool = False` on `NpcPatch`/`Npc`; merge is `npc.manual_origin = npc.manual_origin or patch.manual_origin`.
  - Rationale: The two TEA deviations above adjudicated this and the RED tests encode it; implementing `str|None` would fail the tests (which assert `is True`/`is False`) and the monotonic-clear-guard test. I am bound to the tests. No new decision — recording the implementation trail.
  - Severity: minor
  - Forward impact: none beyond what the TEA deviations already note.

### Reviewer deviation audit
- **TEA: Provenance modelled as `bool`, not `str | None`** → ✓ ACCEPTED by Reviewer: the ACs are binary and `is_creature` already separates human/creature; bool is the minimal correct shape and widens to enum non-breakingly. Agrees with author reasoning.
- **TEA: E2 collision authority pinned to monotonic OR** → ✓ ACCEPTED by Reviewer: logical OR is the only semantics satisfying both E2 clauses (forward-sets, reverse-never-clears); verified correct against `_merge_npc_patch:1523` and both E2 tests.
- **Dev: OTEL provenance attached to existing span, not a new span** → ✓ ACCEPTED by Reviewer: matches context Assumption 4 (prefer extension, avoid dashboard churn); the merge-leg span gap is a rare-path, pre-existing-design limitation, correctly deferred (Architect Option D) and logged as a non-blocking finding.
- **Dev: `bool` representation + monotonic-OR merge per RED contract** → ✓ ACCEPTED by Reviewer: implementation faithfully matches the RED tests; no new decision.
- No undocumented deviations found by Reviewer — the bool/extended-span divergences from the SM Technical Approach are fully captured by TEA + Dev entries above.

### Architect (reconcile)

Verified all four in-flight deviation entries (TEA ×2, Dev ×2) against the merged code: each has all 6 fields, spec text is accurately quoted from `context-story-72-3.md` / the SM Technical Approach, the Implementation lines match the diff (`session.py:160,347,1523,1564`; `disposition.py:71,91`; `monster_manual_inject.py:192,279`), and the Forward-impact lines are correct. No corrections needed. One deviation was implicit in Dev's forward-impact and is promoted here to a standalone, self-contained manifest entry so the boss can audit the AC5 partial-deferral without cross-referencing:

- **AC5 (original) merge-path provenance span — DEFERRED, not implemented**
  - Spec source: `.session/72-3-session.md` → original Acceptance Criteria, AC5 ("OTEL emission verifies preservation")
  - Spec text: "A second span fires in `_merge_npc_patch` when a patch with `manual_origin` is merged (conditional on `patch.manual_origin is not None`). Both spans include action descriptor so the GM panel can trace the provenance flow."
  - Implementation: No span fires from `_merge_npc_patch`. Provenance on the merge (collision) leg is a field-only write (`npc.manual_origin = npc.manual_origin or patch.manual_origin`, `session.py:1523`). The OTEL attribute is emitted only on the fresh-materialization leg, via the existing `npc.spawn_disposition` span in `_npc_from_patch` (`session.py:1573-1576`). The `action` discriminator was not implemented.
  - Rationale: The higher-authority story context (`context-story-72-3.md` AC4 + Assumption 4) scopes OTEL to "the materialization/inject decision" and explicitly prefers extending one existing span over adding new spans/attributes (dashboard-churn avoidance). The merge leg has *never* emitted a span (pre-existing design of `_merge_npc_patch`), and the dominant production path — `monster_manual_inject.inject()` — materializes fresh NPCs (no prior same-name entry), so it hits `_npc_from_patch` and the span fires *with* `manual_origin`. The merge-flip case (narrator-invented name later authored by the Manual) is rare, and the field is set correctly regardless; only the OTEL *event* for that flip is absent. Architect spec-check recommended Defer (Option D); Reviewer confirmed Medium/non-blocking; behavior is test-covered (`test_marked_patch_records_manual_origin_on_existing_npc_via_merge`, both E2 tests).
  - Severity: minor
  - Forward impact: A future story (or the merge-provenance-span follow-up already captured under `## Delivery Findings → TEA (test design)`) should add a span to `_merge_npc_patch` so an invented→manual authorship flip on collision is GM-panel-visible. Until then, the GM panel attributes provenance correctly for all freshly-materialized (the common case) MM NPCs but will not show an event for the rare in-place authorship flip. No data correctness impact — only observability completeness.

**AC accountability:** AC1–AC4 + E1/E2 DONE and test-covered. AC5 is the only partial: its materialization-span half is DONE; its merge-span + `action`-descriptor half is DEFERRED (entry above). AC6 (backward compat) DONE. No ACs descoped.

## Sm Assessment

**Decision: PROCEED to RED phase (tea).**

Story 72-3 is well-scoped and ready for test-first development. The third leg of epic 72 (NPC Identity Hardening), it adds a `manual_origin` provenance marker to `NpcPatch` so Monster-Manual-injected NPCs (ADR-059) are distinguishable from narrator-invented ones, and ensures that marker survives the npc_pool ↔ snapshot.npcs merge seam rather than being silently dropped.

**Why this is ready:**
- Sibling stories 72-1/72-2/72-4/72-5/72-9 are already merged, so the NPC spawn flow, OTEL watcher spans, and merge pipeline this story extends are live and proven — this is wiring into existing infrastructure, not new construction (per "Don't Reinvent").
- Single repo (sidequest-server), bounded blast radius (NpcPatch data model + the one injection/merge seam), 3 points.
- ACs cover the full chain: field validation → injection-seam population → merge preservation → OTEL emission → backward compatibility for NPCs minted without provenance.

**OTEL is mandatory here, not optional.** Per the project's lie-detector principle, the provenance-preservation decision must emit a watcher span so the GM panel can confirm MM provenance survives merge. The RED phase must include the wiring test that asserts the span fires — a passing data-model test alone does not prove the seam is engaged.

**Skipped:** Jira claim — Jira integration is not configured for this project (JIRA_KEY=none). This is the established state, not an oversight.

**Handoff to:** Hamlet (tea) for the RED phase — author failing tests across AC1–AC6, emphasizing the OTEL span wiring test.

## TEA Assessment (red)

**Tests Required:** Yes
**Reason:** Behavioral feature (new model field + seam preservation + OTEL attribute); not a chore-bypass category.

**Test Files:**
- `tests/game/test_npc_manual_origin.py` — model + merge-seam unit suite (fast, no async/OTEL). AC1, AC3, AC2 (both materialize + merge legs), E1 (negative), E2 (forward + reverse monotonicity), pydantic round-trip.
- `tests/integration/test_npc_manual_origin_otel.py` — wiring + OTEL. Drives the **real** `monster_manual_inject.inject()` production path under span capture (mirrors `test_npc_spawn_disposition_otel.py`). AC3 (marker reaches `snapshot.npcs` via production inject), AC4 (`npc.spawn_disposition` span carries `manual_origin`), E1 at span level.

**Tests Written:** 14 tests covering AC1–AC4 + edges E1/E2 (the context's AC set; session's "AC6 backward-compat" is covered by the default-False + round-trip tests).
**Status:** RED confirmed — 14/14 fail, 0 collection/fixture/import errors. Failure reasons verified RED-for-the-right-reason: `ValidationError` (extra="forbid" rejects undeclared key), `AttributeError` (`Npc`/`NpcPatch` has no `manual_origin`), and field-absence — never a malformed-test signature.

### The contract Dev (Puck) must satisfy
1. `NpcPatch.manual_origin: bool = False` and `Npc.manual_origin: bool = False` (declared fields — both models are `extra="forbid"`).
2. `_npc_from_patch` (`session.py:1501`): set `npc.manual_origin = patch.manual_origin` on the fresh `Npc`. **Do not touch the `disposition=-20 if is_creature` line (72-5's).**
3. `_merge_npc_patch` (`session.py:1466`): `npc.manual_origin = npc.manual_origin or patch.manual_origin` (monotonic — set, never clear).
4. MM emitters in `monster_manual_inject.py`: `_human_patch` (157) and `_creature_patch_from_enemy` (229) construct their `NpcPatch(...)` with `manual_origin=True`. Narrator path leaves the default.
5. OTEL: add a `manual_origin: bool` attribute to `npc_spawn_disposition_span` (`telemetry/spans/disposition.py`) — both the `@contextmanager` signature and the `SPAN_ROUTES[...].extract` dict — and pass `manual_origin=patch.manual_origin` from the `_npc_from_patch` call site. The span already fires there per 72-5; this is one attribute, not a new span (context Assumption 4 — prefer extension).

### Rule Coverage (lang-review `python.md`)
The only checklist rule applicable to test authorship is **#6 Test quality**.

| Rule | Coverage | Status |
|------|----------|--------|
| #6 Test quality — no vacuous asserts | Every test asserts a specific value (`is True`/`is False`, `== 1`, exact span-field values); no `assert True`, no bare-truthy, no skips | self-check passed |
| #6 mock target correctness | `monkeypatch.setattr(spans_module, "tracer", …)` patches where *used* | self-check passed |

**Rules checked:** 1 of 1 test-applicable lang-review rule has coverage.
**Self-check:** 0 vacuous tests found.

**Handoff:** To Puck (Dev) for GREEN.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — both mismatches are sound, pre-logged deviations where the implementation followed the higher-fidelity story *context* over the SM's looser session *Technical Approach* sketch. Structural gate (AC coverage, impl-complete, deviation logging) passed.

**Mismatches Found:** 2 (both Minor)

- **Provenance modelled as `bool`, not `str | None`** (Different behavior — Architectural, Minor)
  - Spec: Session ACs 1/3 say `str | None`. Code: `bool = False`.
  - Recommendation: **A — Update spec.** Context Assumption 1 permits the boolean (minimal shape); the ACs are binary; `is_creature` already distinguishes human/creature; bool gives unambiguous monotonic merge. Sound; no change required.

- **One attribute on the existing span, not a new span + `action` + merge-path span** (Different behavior — Architectural, Minor)
  - Spec: Session AC5 wanted a new span + `action` + a second merge-path span. Code: one `manual_origin` attribute on the existing `npc.spawn_disposition` span; no merge span.
  - Recommendation: **A (extension) + D (defer merge span).** Session AC5 directly conflicts with context Assumption 4 (prefer extension, avoid dashboard churn); the implementation followed the context. The absent merge-flip span is a rare-path observability gap (the dominant `inject()` path materializes fresh → span fires with `manual_origin`; merge only triggers on re-inject of an already-recorded NPC or the invented→MM collision). Field set correctly regardless. Defer to a future story — already captured as TEA's Delivery Finding.

**Decision:** Proceed to review (verify). No Option-B hand-back: both drifts are non-breaking, GREEN, and resolve toward the story context with deviations already logged.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/game/session.py` — added `manual_origin: bool = False` to `NpcPatch` and to `Npc` (alongside `pool_origin`); `_npc_from_patch` carries `patch.manual_origin` onto the fresh `Npc` and passes it to the `npc.spawn_disposition` span; `_merge_npc_patch` does monotonic OR.
- `sidequest/telemetry/spans/disposition.py` — added `manual_origin: bool` to the `npc_spawn_disposition_span` signature, attribute dict, and `SPAN_ROUTES` extract (one new attribute on the existing per-NPC materialization span; no new span).
- `sidequest/server/dispatch/monster_manual_inject.py` — `_human_patch` and `_creature_patch_from_enemy` now construct their `NpcPatch` with `manual_origin=True`.
- `tests/game/test_npc_manual_origin.py`, `tests/integration/test_npc_manual_origin_otel.py` — whitespace reformat only (ruff format).

**Tests:** 41/41 passing (GREEN) at green-phase exit — 14 story tests + 27 regression (3 `npc_spawn_disposition_otel` siblings + 24 `monster_manual_inject`). No siblings broken.

**Quality gates:** `ruff format --check` + `ruff check` clean (5 files). `pyright` on changed source: 2 errors, both confirmed pre-existing on base (outside this diff).

**Implementation notes:** Minimal change — one bool field threaded through the two existing materialization legs + one span attribute. No new abstractions, no new span, no touch to the 72-5 disposition default. Wiring verified end-to-end via the real `inject()` production path.

**Branch:** `feat/72-3-mm-npc-provenance` (pushed)

**Handoff:** To Hamlet (TEA) for the verify phase (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (`session.py`, `monster_manual_inject.py`, `disposition.py`, + 2 test files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 — `manual_origin` follows the `pool_origin` provenance pattern; OR-merge is a unique, load-bearing semantics (not duplication); the `bool(attrs.get(...))` span extractor matches existing extractors and is too trivial to hoist. |
| simplify-quality | clean | 0 — declared fields with correct defaults under `extra="forbid"`; monotonic-OR merge; backward-compatible span signature; comprehensive AC/edge coverage; naming consistent with prior story. |
| simplify-efficiency | clean | 0 — no premature abstraction, no over-parameterization, no redundant ops; OR is the simplest expression of monotonic authorship. |

**Applied:** 0 high-confidence fixes (all three lenses clean)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** Full sidequest-server suite GREEN — **9241 passed, 0 failed**, 361 skipped (43.9s, pytest-xdist `-n auto`). Zero regressions from the `manual_origin` field, the extended `npc.spawn_disposition` span, or the two MM emitters. `ruff format --check` and `ruff check` clean on all five files. Two pre-existing pyright type errors in `session.py` confirmed present on base and outside this diff (logged in Dev findings).

**No simplify commit** — working tree unchanged since Dev's GREEN push.

**Handoff:** To Portia (Reviewer) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (14/14 tests pass, ruff clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 1 (deferred), dismissed 0, noted-Low 5 |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 | confirmed 1 (Low), dismissed 1 (out-of-diff) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 class (×3 sites) | confirmed 1 (Low, rule #9) |

**All received:** Yes (4 enabled returned, 3 with findings; 5 disabled via settings)
**Total findings:** 3 confirmed (all Low/Medium non-blocking), 1 dismissed (with rationale), 5 noted-Low

## Reviewer Assessment

**Verdict:** APPROVED

**Summary:** A clean, minimal 3-point change — one boolean provenance field (`manual_origin`) threaded through the two existing NPC-materialization legs, set by the two MM emitters, and surfaced as one attribute on the existing per-NPC `npc.spawn_disposition` span. No new abstractions, no new span, additions-only (+474 / −0). Full server suite GREEN (9241 passed, 0 failed); the 14 story tests pass and drive the real production `inject()` seam. No Critical or High findings. Three confirmed Low/Medium findings, all non-blocking and either deferred-by-design or matching an established codebase pattern.

**Data flow traced:** MM entry → `_human_patch`/`_creature_patch_from_enemy` set `manual_origin=True` on `NpcPatch` → `inject()` bundles into `WorldStatePatch` → `apply_world_patch` routes to `_npc_from_patch` (fresh: `npc.manual_origin=patch.manual_origin`, span fires with the marker) OR `_merge_npc_patch` (collision: monotonic OR). Result: `snapshot.npcs[].manual_origin` is readable and the materialization decision is OTEL-attributed. Safe — no untrusted input, no failure path; `bool()` cast guards the OTEL attribute.

**Wiring:** Production seam (`monster_manual_inject.inject`, called from `websocket_session_handler` per the pre-existing wiring test) is exercised end-to-end by the integration test; span flows `SPAN_ROUTES` → `WatcherSpanProcessor` → GM panel. Verified wired, not just existing.

**Error handling:** Boolean field with `False` default; `extra="forbid"` rejects unknown keys (fail-loud, No Silent Fallbacks); missing key on old saves → default `False` (backward-compatible). No new exception paths.

### Observations

- `[VERIFIED]` Monotonic-OR merge is correct — `session.py:1523` `npc.manual_origin = npc.manual_origin or patch.manual_origin`; both operands are `bool`, satisfies E2 forward (False→True on MM patch) and E2 reverse (True stays True on narrator patch). Evidence: both E2 tests pass and assert exactly this.
- `[VERIFIED]` Materialization carry-through — `session.py:1564` passes `manual_origin=patch.manual_origin` into the fresh `Npc`; span call at `1573-1576` passes `manual_origin=npc.manual_origin` (equal to patch value at that point). Complies with the OTEL Observability Principle for the materialization decision.
- `[VERIFIED]` Backward compatibility — `Npc`/`NpcPatch` default `manual_origin=False`; `extra="forbid"` does not reject *missing* fields, only extra ones, so pre-72-3 saves load with `False`. Evidence: `test_npc_patch_defaults_manual_origin_false`, `test_npc_defaults_manual_origin_false`, JSON round-trip test.
- `[RULE][LOW]` Three `asyncio.sleep(0)` without comment at `test_npc_manual_origin_otel.py:164/193/222` — lang-review #9. **Confirmed** (rule-matching, not dismissed), downgraded to Low: reproduces the established uncommented pattern in sibling OTEL tests verbatim; trivial one-line fix; non-blocking. Captured as a Reviewer Delivery Finding (Improvement).
- `[TEST][MEDIUM]` `_merge_npc_patch` sets the marker but emits no OTEL span — the invented→manual collision flip is field-only, not GM-panel-visible. **Confirmed**, resolution = **Defer**: pre-existing design (`_merge_npc_patch` never emitted a span), rare path (the dominant `inject()` path materializes fresh → span fires), behavior tested, and already logged + Architect-deferred (Option D). Non-blocking.
- `[DOC][LOW]` `NpcPatch.manual_origin` carries both a block comment and a Pydantic docstring (`session.py:341-348`); sibling fields use docstring-only and the richer block comment is invisible to schema introspection. Cosmetic; non-blocking. (comment-analyzer)
- `[TEST][LOW]` `int(krag.disposition) == 0` in the human inject test couples a 72-3 test to 72-5 behavior — intentional orthogonality guard (the marker didn't turn a human into a creature), acceptable; minor coupling noted. (test-analyzer)
- `[DOC]` **Dismissed:** pre-existing `pool_origin` docstring polarity flag — out of the 72-3 diff and actually consistent with call sites (describes span-param, not the `Npc` field). Rationale for dismissal: not introduced by this story; on inspection, not a defect.
- `[EDGE]` specialist disabled via settings — reviewer self-assessed boundary conditions: only a boolean toggle and a logical OR; no numeric/empty/huge-input boundaries exist. Clean.
- `[SILENT]` specialist disabled — reviewer self-assessed: no try/except, no swallowed errors, no silent fallbacks added; `extra="forbid"` is fail-loud. Clean.
- `[TYPE]` specialist disabled — reviewer self-assessed: `bool` is the correct type for a binary authorship predicate; consistent `NpcPatch`→`Npc` representation; no stringly-typed API. Clean.
- `[SEC]` specialist disabled — reviewer self-assessed: no auth/tenant/injection/secret surface; provenance is internal dev observability. N/A.
- `[SIMPLE]` specialist disabled — reviewer self-assessed (corroborated by the verify-phase simplify fan-out, all 3 lenses clean): no over-engineering, no dead code; OR is the simplest expression of monotonicity. Clean.

### Rule Compliance (lang-review python.md, 13 checks)

Exhaustively enumerated by reviewer-rule-checker across 5 changed files / 47 instances: **12 of 13 checks clean**; check #9 (async — `asyncio.sleep(0)` without comment) has 3 Low sites (see observation above). Specifically verified: #2 mutable defaults — all new defaults are `bool`/immutable (compliant); #3 type annotations — all new fields/params annotated; #6 test quality — all 14 tests have specific non-vacuous assertions, no skips, correct `monkeypatch` target; #8 deserialization — JSON round-trip is on Pydantic-generated trusted data through `model_validate`; #11 input validation — Pydantic `bool` field under `extra="forbid"`, `bool()`-cast before OTEL emit. Project additional rules: **No Source-Text Wiring Tests** — the integration test drives real `inject()`, no `read_text()` greps (compliant); **No Silent Fallbacks** — `extra="forbid"`, explicit OR (compliant); **OTEL Observability** — materialization decision emitted (compliant for the primary path; merge-flip deferred).

### Devil's Advocate

Let me argue this code is broken. **First attack — the merge leg silently lies to the GM panel.** A narrator invents "Hob" on turn 3 (manual_origin=False, no span says "manual"); on turn 5 the Monster Manual authors a "Hob" stat block. `_merge_npc_patch` flips `manual_origin` to True via OR — but fires *no span*. The GM panel, watching the OTEL stream, never sees the authorship change: it saw Hob spawn as narrator-invented and has no event telling it Hob is now Manual-backed. A GM auditing "which NPCs are real" would mis-attribute Hob. Is this fatal? No — because the *dominant* path is `inject()`, which materializes fresh NPCs (the snapshot has no prior "Hob"), hitting `_npc_from_patch` where the span DOES fire with the marker. The merge collision requires a narrator to have invented the exact same name first — rare — and even then the field is correct, only the event is missing. It's a real but bounded observability gap, pre-existing in `_merge_npc_patch`, documented and deferred. **Second attack — monotonicity is wrong if authorship should be revocable.** Suppose a future design wants "narrator overrides Manual." The OR-merge makes the marker permanent — it can never go True→False. But the story's E2 spec explicitly mandates this ("should not clear the MM marker"), so it's correct *by spec*; a reversal would be a new story, not a bug. **Third attack — a confused author sets manual_origin via dict and it's silently dropped.** No: `extra="forbid"` raises on an undeclared key; a declared key validates; a typo fails loud. **Fourth — flaky OTEL test on a stressed CI.** The `_events_for` poll waits up to 1s re-checking every 10ms; the span fires synchronously inside `inject()` and the watcher coroutine is scheduled — 1s of polling is generous and mirrors the stable sibling test. Low risk. **Fifth — backward compat on a huge old save.** A pre-72-3 `Npc` JSON lacks `manual_origin`; Pydantic supplies `False`; no `ValidationError` because forbid rejects only *extra* keys. Verified by the default tests. Conclusion: the devil finds one genuine but bounded gap (merge-flip OTEL), already deferred — nothing that blocks.

**Pattern observed:** Provenance marker extending the existing `pool_origin`/`npc.spawn_disposition` infrastructure rather than adding parallel structures — exemplary "wire up what exists" (`session.py:160`, `disposition.py:71`).

**Handoff:** To SM (Prospero) for finish-story.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-31T04:09:36Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-30 | 2026-05-31T03:35:48Z | 27h 35m |
| red | 2026-05-31T03:35:48Z | 2026-05-31T03:44:00Z | 8m 12s |
| green | 2026-05-31T03:44:00Z | 2026-05-31T03:49:00Z | ~5m |
| spec-check | 2026-05-31T03:49:00Z | 2026-05-31T03:50:16Z | ~1m |
| verify | 2026-05-31T03:50:16Z | 2026-05-31T04:00:07Z | 9m 51s |
| review | 2026-05-31T04:00:07Z | 2026-05-31T04:08:14Z | 8m 7s |
| spec-reconcile | 2026-05-31T04:08:14Z | 2026-05-31T04:09:36Z | 1m 22s |
| finish | 2026-05-31T04:09:36Z | - | - |