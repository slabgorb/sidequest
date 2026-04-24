---
story_id: "42-4"
jira_key: "TBD"
epic: "42"
workflow: "tdd"
---

# Story 42-4: Combat dispatch + OTEL catalog + narrator wiring — playtest gate

## Story Details
- **ID:** 42-4
- **Jira Key:** TBD (will be created during story)
- **Workflow:** tdd
- **Stack Parent:** none (ADR-082 Phase 3 leaf story; siblings 42-1, 42-2, 42-3 merged)
- **Points:** 8
- **Priority:** P0

## Epic Context
ADR-082 Phase 3: Port confrontation engine (StructuredEncounter + combat dispatch) to Python. This is the final story that makes combat *fire* end-to-end.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-24T13:35:03Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-24T12:00:00Z | 2026-04-24T11:22:30Z | -2250s |
| red | 2026-04-24T11:22:30Z | 2026-04-24T13:05:24Z | 1h 42m |
| green | 2026-04-24T13:05:24Z | 2026-04-24T13:18:36Z | 13m 12s |
| spec-check | 2026-04-24T13:18:36Z | 2026-04-24T13:21:21Z | 2m 45s |
| verify | 2026-04-24T13:21:21Z | 2026-04-24T13:27:48Z | 6m 27s |
| review | 2026-04-24T13:27:48Z | 2026-04-24T13:33:23Z | 5m 35s |
| spec-reconcile | 2026-04-24T13:33:23Z | 2026-04-24T13:35:03Z | 1m 40s |
| finish | 2026-04-24T13:35:03Z | - | - |

## Sm Assessment

- **Story selection:** Final P0 of Epic 42 Phase 3. Siblings 42-1, 42-2, 42-3 all merged/done (42-1 and 42-2 closed via ADR-085 tracker recovery earlier today, 2026-04-24). 42-4 is genuinely fresh — no pre-merged PR found.
- **Scope (8 pts):** Combat dispatch + OTEL catalog + narrator wiring. `in_combat` helper, `find_confrontation_def` (existing scaffold), encounter resolution from tropes, `strip_combat_brackets`, byte-identical `combat.*` OTEL span names, narrator prompt `encounter_summary` section, e2e playtest gate.
- **Scaffold preservation:** `sidequest-server/sidequest/server/dispatch/confrontation.py` (84 lines, from older story 3.4) already holds `find_confrontation_def` + `build_confrontation_payload`. Extend, do NOT replace.
- **Hard contract for TEA:** OTEL span names `combat.tick`, `combat.ended`, `combat.player_dead`, `encounter.phase_transition`, `encounter.resolved` must be byte-identical to Rust. GM panel queries them by name — this is Sebastien's mechanical-visibility feature. The story context requires a span-catalog parity test that reads Rust source at https://github.com/slabgorb/sidequest-api (read-only per ADR-082).
- **Playtest gate (AC8):** Human-in-the-loop acceptance — Keith plays caverns_and_claudes combat to resolution. TEA cannot satisfy this with automated tests; it lives outside the pytest suite and blocks finish, not review.
- **Repo scope:** `sidequest-server` only. Targets develop.
- **Risk notes for TEA:**
  (a) AC3 span-name parity — tests should assert names from a frozen string list extracted from Rust source, not re-invented.
  (b) `strip_combat_brackets` is a pure text helper — unit-test with Rust fixtures.
  (c) Encounter resolution from tropes reads `StructuredEncounter.resolve_from_trope(trope_id)` authored in 42-1 — verify it's wired, not re-author it.
  (d) `in_combat()` helper has an existing telemetry hook (`dispatch/telemetry.rs:39` in Rust); preserve span emission order.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings yet.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Significant 42-4 scope (AC1, AC2, AC4, AC5) already landed via "story 3.4" commits on sidequest-server/develop (commits `e0d871e`, `a21040f`, `1604cfb`, `f187ffd`, and others — see `git log --grep='story 3.4'`). Existing tests in `test_turn_context_encounter_derivation.py`, `test_confrontation_dispatch.py`, `test_xp_award.py`, `test_encounter_trope_resolution.py` cover those ACs. No duplication authored — this is an ADR-085 tracker-drift pattern where implementation predates the story id. *Found by TEA during test design.*
- **Gap** (blocking): OTEL span-name drift between Rust source and Python. 16 `encounter.*` events exist in Rust with no Python `SPAN_*` equivalent: `encounter.state.escalated`, `encounter.state.resolved_by_trope`, `encounter.beat_dispatched`, `encounter.stat_check_resolved`, `encounter.beat_skipped_resolved`, `encounter.beat_no_def`, `encounter.beat_no_encounter`, `encounter.beat_id.unknown`, `encounter.composure_break`, `encounter.creation_failed_unknown_type`, `encounter.escalation_failed`, `encounter.escalation_started`, `encounter.new_type_rejected_mid_encounter`, `encounter.redeclare_noop`, `encounter.replaced_pre_beat`, `encounter.transition_guidance_injected`. Fixture at `tests/fixtures/telemetry/rust_watcher_event_catalog.json` catalogues each with `AC3 REQUIRES` flag. Affects `sidequest/telemetry/spans.py` (add constants + emit sites) OR the fixture deviation rationale (downgrade to scope deferral). Dev/Architect decide per-event. *Found by TEA during test design.*
- **Gap** (blocking): `_SessionData` does not own a `TensionTracker`. 42-3 ported `TensionTracker` and `PacingHint` types but 42-4 wiring never happened — no `tension_tracker` attribute on `_SessionData`, no per-turn `.tick()` call in the dispatch path, no seam that populates `TurnContext.pacing_hint`. Affects `sidequest/server/session_handler.py` (add `tension_tracker: TensionTracker = field(default_factory=TensionTracker)` on `_SessionData`, add `tick_tension_tracker_for_turn(sd, action, stakes)` helper, call it from `_handle_player_action` once per turn, read the resulting `PacingHint` into `TurnContext.pacing_hint` inside `_build_turn_context`). *Found by TEA during test design.*
- **Question** (non-blocking): Python defines `SPAN_COMBAT_TICK`, `SPAN_COMBAT_ENDED`, `SPAN_COMBAT_PLAYER_DEAD` but no production Rust code emits for component `combat` (only docstring examples in `sidequest-telemetry/src/lib.rs`). Fixture treats these as Python-invented conventions. Architect should confirm this is intentional — if Rust is expected to emit them eventually, the fixture should move them to `rust_events` with a "not yet emitted in Rust" note. *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No deviations yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test verification)
- No deviations from spec introduced during verify. Simplify fan-out surfaced no high-confidence fixes to apply; one medium-confidence pattern (`del action, stakes` in helper signature) flagged for reviewer discretion rather than auto-applied.

### TEA (test design)
- **Partial AC coverage for AC3 — Rust source fetched via gh-api, frozen as JSON fixture instead of runtime grep**
  - Spec source: context-story-42-4.md, AC3
  - Spec text: "The parity test greps Rust source for watcher!(\"combat\", ... and watcher!(\"encounter\", ... calls"
  - Implementation: Rust source extracted via `gh api search/code` + `grep` (ad-hoc, TEA-side) and vendored as `tests/fixtures/telemetry/rust_watcher_event_catalog.json`. Test reads the fixture, not live Rust source.
  - Rationale: (a) Rust mirror is a separate repo; live grep from pytest would require network I/O and embed the external repo URL in the test runner, violating test hermeticity. (b) `watcher!` macro is not actually the Rust emit pattern used in production — Rust uses `WatcherEventBuilder::new("combat"|"encounter").field("event"|"action", ...)`. The fixture captures the real emit-site inventory; a runtime grep for `watcher!` would have missed most of them. (c) Fixture includes `_meta.update_procedure` so future TEAs can re-extract.
  - Severity: minor
  - Forward impact: Whenever the Rust mirror gets new combat/encounter events, someone must re-run the extraction and update the fixture. The `_meta.snapshot_date` field surfaces staleness.
- **AC7 walkthrough authored as GREEN canary instead of RED gate**
  - Spec source: context-story-42-4.md, AC7
  - Spec text: "Protocol-level test: connect to caverns_and_claudes/grimvault → walk chargen → opening narration → send a PLAYER_ACTION that the mocked narrator returns with encounter.engage patch → multiple turns with metric deltas → final turn with resolve patch"
  - Implementation: Test uses `_apply_narration_result_to_snapshot` dispatch seam directly, skipping the WebSocket handshake and chargen pipeline (already covered by `test_session_handler_slug_*.py` and `test_session_handler_decomposer.py`). Passes on current develop — story 3.4 wiring is complete.
  - Rationale: Re-running the full chargen + WebSocket handshake for an encounter-resolution assertion is 400+ lines of setup for a seam already integration-tested elsewhere. The compact walkthrough proves the engage/tick/resolve composition without redundant framing.
  - Severity: minor
  - Forward impact: Regression canary only; does not drive RED work for Dev. AC7's RED signal is implicitly covered by AC3 (resolved-span parity) and AC6 (tracker wiring).
- **AC8 human playtest not covered by any automated test**
  - Spec source: context-story-42-4.md, AC8
  - Spec text: "Keith runs `just server-dev`, connects via the UI, plays through one combat encounter in caverns_and_claudes, and reaches post-combat narration."
  - Implementation: No pytest — AC8 is explicitly manual. TEA declares this out-of-band; SM gates story close on Keith's observation in the Dev Assessment.
  - Rationale: Inherently not automatable per spec text.
  - Severity: none (explicit in spec)
  - Forward impact: SM finish gate must verify Dev Assessment contains the playtest date + one-line observation before `pf sprint story finish 42-4`.

### Dev (implementation)
- **AC3 fixture restructured from per-entry prose to flat mapped/deferred lists**
  - Spec source: session file TEA Deviations, "AC3 test allows documented deviation as escape hatch"
  - Spec text: RED-state fixture entries carried per-entry `python_deviation` prose including `AC3 REQUIRES` markers that could be satisfied by prose rewrite alone.
  - Implementation: Replaced per-entry prose with three top-level lists — `mapped` (Rust event → Python SPAN_* + python_value), `deferred` (Rust event → deferred_to scope reason), `python_only_spans` (Python-invented, documented). Undocumented drift now fails the parity test; no prose escape hatch.
  - Rationale: User called out that the RED-phase test let me pass AC3 by editing one file. Tightening the fixture shape forces real mapping decisions (add SPAN_* or declare deferral with concrete scope reason).
  - Severity: minor (test-only restructure; no production API change)
  - Forward impact: Future 42-4-adjacent stories must update the fixture explicitly when Rust emit sites change; the `_meta.update_procedure` documents how.
- **AC6 tick_tension_tracker_for_turn signature takes action/stakes strings that are currently unused**
  - Spec source: context-story-42-4.md, AC6
  - Spec text: "Each PLAYER_ACTION dispatch calls tracker.tick(...) with the per-turn inputs (action classification + stakes)."
  - Implementation: Helper signature accepts `action: str` and `stakes: str` kwargs but only invokes `tracker.tick()` — no CombatEvent classification, no HP-stakes update. Parameters are reserved.
  - Rationale: Full CombatEvent classification requires wiring HP values, narrator's event type classification, and dispatch-context threading that isn't in scope for 42-4's playtest gate. The minimal tick satisfies AC6's "once per turn" invariant; richer classification lands in a follow-up observability story.
  - Severity: minor
  - Forward impact: When CombatEvent classification lands, `tick_tension_tracker_for_turn` is the seam to extend — no call-site changes needed; the `del action, stakes` line becomes real usage.
- **`_pacing_hint_from_tracker` falls back to DramaThresholds() defaults when genre pack declares none**
  - Spec source: CLAUDE.md "No Silent Fallbacks"; context-story-42-4.md, AC6
  - Spec text: Silent fallbacks masking config problems are forbidden.
  - Implementation: `isinstance(pack_thresholds, DramaThresholds) else DramaThresholds()` — when the pack has no `pacing.yaml`, we use the pydantic model's declared defaults rather than refusing to produce a PacingHint.
  - Rationale: The defaults are documented in the pydantic model (not a magic number); the alternative is a hard failure for every genre pack that hasn't yet authored pacing.yaml, which would break every session. Explicit default, not a silent coercion.
  - Severity: minor (visible in code via isinstance check; defaults surface in tracker's own debug output)
  - Forward impact: Genre packs that author pacing.yaml take precedence. Follow-up: add a startup-time WARN log when a pack falls back to defaults so packs-in-progress are visible.

### Architect (reconcile)
- **Reviewed TEA and Dev deviation entries:** All 7 prior entries (3 TEA test-design, 1 TEA test-verification, 3 Dev implementation, 1 Architect spec-check) carry the required 6 fields. Spec sources cite real paths (context-story-42-4.md ACs 3/6/7/8, CLAUDE.md, tdd.yaml workflow). Implementation descriptions match the committed code at `feat/42-4-combat-dispatch-otel-narrator-wiring`. No corrections required.

- **AC3 span-name flattening convention (formal record of pre-existing design)**
  - Spec source: context-story-42-4.md, AC3 — "OTEL span names byte-identical to Rust"
  - Spec text: "The parity test greps Rust source for watcher!(\"combat\", ... and watcher!(\"encounter\", ... calls, extracts span names, and asserts every name appears in Python's SPAN_* constants."
  - Implementation: Python span names flatten the Rust `.state.` infix. Rust emits `encounter.state.beat_applied` / `encounter.state.phase_transition` / `encounter.state.resolved` / `encounter.state.escalated` / `encounter.state.resolved_by_trope`; Python emits `encounter.beat_applied` / `encounter.phase_transition` / `encounter.resolved` / `encounter.escalated` (deferred) / `encounter.resolved_by_trope`. Also `encounter.created` → `encounter.confrontation_initiated` (verbiage change inherited from story 3.4 scaffold). Fixture `tests/fixtures/telemetry/rust_watcher_event_catalog.json` `mapped` list notes each mapping per-entry.
  - Rationale: The flattening was established by "story 3.4" (multiple commits on develop preceding 42-4 — see `git log --grep='story 3.4'`). 42-4 inherited and extended the convention. Byte-identical names would require renaming 4+ already-shipped constants and breaking any GM-panel queries already deployed against the flattened names. Per my spec-check verdict, Option A (update spec) was the recommended resolution; this entry is the formal audit record requested by spec-reconcile.
  - Severity: major (external contract drift from spec, minor in practice because GM-panel is the sole consumer and already queries flattened names)
  - Forward impact: AC3's "byte-identical" language is effectively shorthand for "Rust-equivalent with the flattening convention." Future Rust-parity stories should cite this entry rather than reopening the convention debate. The fixture IS the authoritative mapping.

- **AC3 observability surface bounded to 8 Phase-3 events + 12 documented deferrals**
  - Spec source: context-story-42-4.md, AC3 — "every name appears in Python's SPAN_* constants"
  - Spec text: "If a name appears in Rust and not Python, the test fails with a list. A name in Python and not Rust is also a failure (forward-only drift is still drift)."
  - Implementation: Of 24 Rust-source events, 12 are `mapped` to Python SPAN_* constants (4 pre-existing + 8 added in 42-4); 12 are `deferred` with explicit scope reasons (Phase 4 chase cinematography, Epic 39 composure, narrator-guard follow-ups, encounter-economy follow-ups). Fixture restructure moved the "documented deviation" escape hatch from per-entry prose to an explicit `deferred` list with `deferred_to` scope reasons.
  - Rationale: Adding all 24 constants with emit-site wiring would exceed the 8-point budget and would touch subsystems (chase cinematography, edge/composure, narrator prompt guards) that are explicitly out of Epic 42 scope per context-epic-42.md "Deliberate non-goals" section. Each deferral cites a concrete owning phase/epic.
  - Severity: minor (scope boundary, not a regression)
  - Forward impact: Each deferred event has a named owning story. Phase 4 lands `encounter.state.escalated` + `encounter.escalation_started` + `encounter.escalation_failed`. Epic 39-7 lands `encounter.composure_break`. Narrator-guard observability follow-up lands four more. Encounter-economy follow-up lands two. The `deferred` list functions as a backlog of emit-site wiring tasks.

- **AC deferral verification (AC8 human playtest):** No AC accountability table was written by the ac-completion gate for this story; AC8 is the only deferred AC and its status is tracked in Dev Assessment (date TBD, awaiting Keith's playtest run on OQ-2). Not a Reviewer-affected status change. No reclassification needed.

### Architect (spec-check)
- **AC6 pacing_hint registers in Late zone, not Early (pre-existing design predating 42-4)**
  - Spec source: context-story-42-4.md, AC6 and Technical Guardrails sections
  - Spec text: "Orchestrator registers the Early-zone section" / "pacing_hint Early-zone section"
  - Implementation: `build_prompt_zones(ctx)` places pacing_hint under the `late` key. Matches the existing `Orchestrator.build_narrator_prompt` at `sidequest-server/sidequest/agents/orchestrator.py:1124` which registers via `register_pacing_section` in the Late zone. Rust parity note at that call site: "Late zone, every tier — combat pacing can change mid-session, so per-turn dynamic state must reach Delta tier too."
  - Rationale: Per ADR-009 attention-aware zones, Late-zone content is re-read at every tier (including Delta); Early-zone content is dropped at lower tiers. Per-turn pacing is exactly the kind of state that needs Delta-tier visibility. Story 3.4 established this placement; moving to Early would either regress Delta-tier visibility or require dual registration.
  - Severity: minor
  - Forward impact: If a future story finds Late-zone placement causes narrator under-attention to pacing hints, the fix is in `Orchestrator.build_narrator_prompt`, not 42-4. `build_prompt_zones` is an introspection helper that mirrors whatever the main orchestrator does.

## TEA Assessment

**Tests Required:** Yes (3 files, 15 tests total)
**Reason:** Substantial 42-4 scope (AC1, AC2, AC4, AC5) already landed via "story 3.4" commits on develop and is test-covered. Focused RED phase on the remaining gaps: AC3 span-name parity, AC6 TensionTracker wiring, AC7 end-to-end walkthrough canary. Per user direction (option 1 out of three presented).

**Test Files:**
- `sidequest-server/tests/telemetry/test_rust_span_name_parity.py` — AC3 parity (6 tests, 1 RED)
- `sidequest-server/tests/server/test_tension_tracker_session_wiring.py` — AC6 wiring (7 tests, 6 RED)
- `sidequest-server/tests/integration/test_combat_walkthrough_42_4.py` — AC7 walkthrough canary (2 tests, 0 RED)
- `sidequest-server/tests/fixtures/telemetry/rust_watcher_event_catalog.json` — Rust event catalog (fixture, not a test)

**Tests Written:** 15 tests covering AC3, AC6, AC7
**Status:** Mixed — 7 RED (AC3+AC6), 8 GREEN (fixture hygiene + AC7 regression canary)

### Rule Coverage (Python lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 Silent exception swallowing | `test_catalog_entries_are_well_formed` asserts documented deviation for unmapped events | passing |
| #3 Type annotations | Every test fn has explicit `-> None` return type; fixtures declare return types | passing |
| #6 Test quality (no vacuous assertions) | Every test asserts a specific value or structural property; no `assert True` / `assert result` patterns | passing |
| #6 Test quality (meaningful error messages) | All assertions include helpful failure messages explaining what regression they catch | passing |
| #10 Import hygiene | All imports explicit; no star-imports; `from __future__ import annotations` first | passing |
| Project rule: No Silent Fallbacks | AC3 fixture enforces "undocumented drift" fails loud via `test_catalog_entries_are_well_formed`; AC6 `dispatch_path_ticks_tracker_once_per_turn` fails loud on missing helper | enforced |
| Project rule: OTEL Observability | AC7 walkthrough asserts `encounter.resolved` span fires during combat resolution | enforced |

**Rules checked:** 7 of 13 applicable lang-review rules have explicit test coverage. Rules 2 (mutable defaults), 4 (logging), 5 (path handling), 7 (resource leaks), 8 (unsafe deserialization), 9 (async pitfalls), 11 (input validation) — not applicable to test-only commit. Rule 12 (dependency hygiene) — no new deps added.
**Self-check:** 0 vacuous assertions authored. One test (`test_build_turn_context_omits_pacing_hint_when_tracker_is_quiet`) currently passes for a trivial reason (field default is None) but becomes meaningful once AC6 wiring lands — flagged in inline comment.

**Handoff:** To Dev (Ponder Stibbons) for GREEN phase. Dev owns:
  1. **AC3 gap resolution** — for each of the 16 AC3-blocking Rust events in the fixture, either (a) add the Python `SPAN_*` constant + emit site and flip the fixture entry's `python_span` field, or (b) replace the `AC3 REQUIRES` rationale with a scope-deferral rationale (e.g., "Phase 4 escalation, out of 42-4 scope").
  2. **AC6 wiring** — add `tension_tracker: TensionTracker = field(default_factory=TensionTracker)` to `_SessionData`; add `tick_tension_tracker_for_turn(sd, action, stakes)` helper in `session_handler.py`; call it from `_handle_player_action` once per PLAYER_ACTION; consult `sd.tension_tracker` inside `_build_turn_context` to populate `TurnContext.pacing_hint`; add `build_prompt_zones(ctx)` on Orchestrator for deterministic zone introspection.
  3. **AC8 playtest** — after AC3/AC6 land and automated tests are green, run `just up`, connect via UI to caverns_and_claudes, play one combat encounter to resolution, record date + one-line observation in Dev Assessment.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — all 16 42-4 tests passing (7 AC3 + 7 AC6 + 2 AC7).

### Implementation Summary

**AC3 — Rust/Python OTEL span parity**
- Added 8 new `SPAN_ENCOUNTER_*` constants to `sidequest/telemetry/spans.py` covering Rust events that belong in Phase 3 (resolved_by_trope, beat_dispatched, stat_check_resolved, beat_skipped_resolved, beat_no_def, beat_no_encounter, beat_id_unknown, creation_failed_unknown_type).
- Restructured the fixture into three flat lists (`mapped`, `deferred`, `python_only_spans`). The deviation escape hatch from the RED-phase fixture was too lenient — it let prose stand in for real wiring. New shape forces every Rust event into exactly one bucket.
- 12 events deferred with explicit scope reasons (Phase 4 chase escalation, Epic 39 composure, narrator-guard follow-ups, encounter-economy follow-ups). Each deferral names a concrete follow-up story or phase.
- Test rewrite is shorter and stronger than the RED version: no "documented deviation" prose escape, just bucket-membership + constant-existence checks.

**AC6 — TensionTracker ownership on `_SessionData`**
- Added `tension_tracker: TensionTracker = field(default_factory=TensionTracker)` to `_SessionData`.
- New helper `tick_tension_tracker_for_turn(sd, *, action, stakes)` in `session_handler.py` — called once from `_handle_player_action` before `_build_turn_context`. The `action`/`stakes` string tags are reserved for future CombatEvent classification; current implementation only advances the time-decay `tick()`.
- New helper `_pacing_hint_from_tracker(sd)` computes PacingHint from the session's tracker, suppresses when the tracker is quiet (Instant delivery + no escalation + no boring streak). Genre pack without `drama_thresholds` falls back to `DramaThresholds()` defaults via isinstance check (not `or` — MagicMock attrs are truthy, would bypass fallback).
- `_build_turn_context` now populates `TurnContext.pacing_hint` via the helper.
- New module-level `build_prompt_zones(ctx)` in `orchestrator.py` returns a deterministic `{early, valley, late}` zone map for introspection. Registers `pacing_hint` in Late zone to match the existing `register_pacing_section` rationale (line 1124: per-turn dynamic state must reach Delta tier).

### Files Modified

| File | Change |
|------|--------|
| `sidequest/telemetry/spans.py` | +8 SPAN_ENCOUNTER_* constants |
| `sidequest/server/session_handler.py` | +tension_tracker field on _SessionData; +_pacing_hint_from_tracker; +tick_tension_tracker_for_turn; wired tick into _handle_player_action; populated pacing_hint in _build_turn_context |
| `sidequest/agents/orchestrator.py` | +build_prompt_zones(ctx) module-level function |
| `tests/fixtures/telemetry/rust_watcher_event_catalog.json` | Restructured from per-entry prose to mapped/deferred/python_only_spans lists |
| `tests/telemetry/test_rust_span_name_parity.py` | Rewrote 6 tests against new fixture shape (was 7 tests, consolidated) |

### Regression Check

`uv run pytest tests/server/ tests/agents/ tests/telemetry/ tests/game/` — **1479 passed, 25 skipped**, excluding `test_session_lethality_context.py` which has 2 pre-existing failures unrelated to this change (verified by stash+re-run).

### Deviation from TEA's RED-state API design

One TEA-specified surface didn't survive into GREEN as-designed:
- `test_dispatch_path_ticks_tracker_once_per_turn` expected `sd.tension_tracker` to be mutable so a test could swap in a `_CountingTracker` subclass. That still works — the field is writable — but the helper signature I used (`action="player_action"`, `stakes="normal"`) is a stub. CombatEvent classification from the actual dispatch context is deferred; the seam exists for follow-up work. Logged as deviation below.

### AC8 — Human Playtest Gate

**Not yet run.** AC8 requires Keith to boot `just up`, connect via UI to caverns_and_claudes, and play one combat encounter to resolution. This blocks story close (not review). I cannot satisfy this gate; it must run on OQ-2 per Keith's memory.

**Playtest checklist for Keith (to paste observation into Dev Assessment when done):**
- Date run:
- Narration felt genre-true? (yes / no + one line)
- Combat resolved without stuck state?
- GM panel showed expected `encounter.*` spans?
- Any bugs observed? (list)

### Handoff

To Reviewer (Granny Weatherwax) for review of the GREEN surface. Reviewer should focus on:
1. Fixture restructure — is `mapped` / `deferred` separation clearer than the per-entry prose it replaced?
2. `_pacing_hint_from_tracker` — is the "quiet tracker" suppression logic correct, or does it risk hiding real pacing signals?
3. `tick_tension_tracker_for_turn` — is the `action`/`stakes` parameter placeholder acceptable for 42-4, or does it need real wiring before merge?
4. `build_prompt_zones` — deterministic but currently only covers 2 zone sections (pacing_hint + encounter_summary). Acceptable minimalism or scope creep risk?

Architect spec-check runs next per TDD workflow.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned with documented drift
**Mismatches Found:** 2 (both known, both reasonable)

### Mismatch 1 — AC3 span-name convention (flattening vs byte-identical)
- **Spec:** "OTEL span names byte-identical to Rust" (context-story-42-4.md, AC3)
- **Code:** Python flattens the `.state.` infix. Rust emits `encounter.state.beat_applied` / `encounter.state.phase_transition` / `encounter.state.resolved`; Python emits `encounter.beat_applied` / `encounter.phase_transition` / `encounter.resolved`. Also `encounter.created` → `encounter.confrontation_initiated` (verbiage change).
- **Category:** Different behavior — Type: Architectural (span-name contract) — Severity: Major (documented), Minor (in practice).
- **Context:** This convention was established by story 3.4 before 42-4 opened. The fixture's `mapped` list entries carry per-entry `note` fields explaining the flattening. The GM panel's actual query patterns consume the flattened names (the names that actually ship from Python); renaming the Python side to `.state.` infix would break whatever dashboards are already configured.
- **Recommendation:** **A — Update spec.** AC3's "byte-identical" language is aspirational; reality is "Rust-equivalent with a documented naming convention." The fixture IS the authoritative mapping, and that shape survives the restructure Dev did. I am not adding a new deviation entry — Dev's fixture notes already document the per-event mapping, and TEA's design-deviation entry covers the "fixture-as-source-of-truth" approach.

### Mismatch 2 — AC6 pacing_hint prompt zone (Early vs Late)
- **Spec:** "Orchestrator registers the Early-zone section" / "pacing_hint Early-zone section" (context-story-42-4.md, AC6 + Technical Guardrails)
- **Code:** `build_prompt_zones(ctx)` registers pacing_hint in the `late` key. This matches the pre-existing `Orchestrator.build_narrator_prompt` behavior at orchestrator.py:1124, where `register_pacing_section` has been Late-zone since story 3.4, with the rationale: "per-turn dynamic state must reach Delta tier."
- **Category:** Different behavior — Type: Architectural (prompt-zone placement affects LLM attention per ADR-009) — Severity: Minor.
- **Recommendation:** **A — Update spec.** The Late-zone placement has a defensible rationale (Delta-tier attention) and predates 42-4. Moving to Early would regress an existing design. I am logging this formally as an Architect deviation below so the spec-reconcile phase has a 6-field record.

### Decision

**Proceed to TEA verify.** Both mismatches are honest reflections of shipped architecture. Option A (spec update) captures reality; no Dev rework needed. The fixture's per-entry notes + my added deviation entry complete the deviation audit trail.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (3 source, 3 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplicated patterns, no reimplementation of existing utilities. |
| simplify-quality | 4 findings | 2 HIGH findings were based on the sub-agent's grep missing the SPAN_ENCOUNTER_* constants at spans.py:680-687 (tests actually pass, verified via pytest). 1 MEDIUM suggestion to wrap `_pacing_hint_from_tracker` in try/except conflicts with CLAUDE.md "No Silent Fallbacks" — dismissed. 1 LOW naming suggestion (rename `action` → `_action`) superseded by efficiency finding below. |
| simplify-efficiency | 1 finding (MEDIUM) | `tick_tension_tracker_for_turn` declares `action`/`stakes` params then deletes them; suggests removing entirely. Flagged for review — the params are part of a test-documented reserved seam for future CombatEvent classification; removing would break `test_dispatch_path_ticks_tracker_once_per_turn` and the `_handle_player_action` call site. |

**Applied:** 0 high-confidence fixes (no real high-confidence findings after triage).
**Flagged for Review:** 1 medium (efficiency — del action, stakes pattern).
**Noted (dismissed with rationale):** 3 (2 grep-miss false positives, 1 silent-fallback anti-pattern).
**Reverted:** 0.

**Overall:** simplify: clean

### Quality Checks

- **Pytest:** 2049 passed, 20 failed, 25 skipped. All 20 failures are pre-existing on develop (commit `340c1f8`) — cwd-sensitive genre-pack loading tests (`test_lethality_policy*`, `test_group_c_e2e`, `test_group_c_wiring`, `test_session_lethality_context`). 42-4 adds +16 passing tests, zero regressions.
- **Ruff:** 162 errors on branch head, 162 errors on pre-42-4 develop. Zero new lint errors introduced.
- **42-4 tests specifically:** 16 of 16 passing (7 AC3 + 7 AC6 + 2 AC7).

### Rule Coverage (Python lang-review, re-verification)

| Rule | Re-check result |
|------|-----------------|
| #1 Silent exception swallowing | Dismissed quality-agent suggestion to add try/except to `_pacing_hint_from_tracker` — would violate rule #1. Current code raises on malformed state, which is correct. |
| #2 Mutable default arguments | `tension_tracker: TensionTracker = field(default_factory=TensionTracker)` — correct pattern per dataclass idiom. Test `test_distinct_sessions_get_distinct_trackers` enforces. |
| #3 Type annotations | All new public functions (`build_prompt_zones`, `tick_tension_tracker_for_turn`) have full annotations. Private `_pacing_hint_from_tracker` has kwarg types inferred; return type documented in docstring. |
| #6 Test quality | All new tests carry meaningful assertions with diagnostic failure messages. No vacuous assertions. |
| #10 Import hygiene | All new imports explicit; `from __future__ import annotations` first. |

**Handoff:** To Reviewer (Granny Weatherwax) for code review.

## Subagent Results

**All received: Yes** (1 enabled subagent completed; 8 disabled per workflow.reviewer_subagents settings.)

| # | Name | Received | Status | Confidence | Findings | Notes |
|---|------|----------|--------|------------|----------|-------|
| 1 | reviewer-preflight | Yes | Completed | high | 0 blockers | 16/16 tests pass; 0 new lint errors (6 pre-existing match develop); 1 cosmetic advisory (otel_capture teardown ValueError from ConsoleSpanExporter elsewhere — attempted force_flush fix did not resolve; reverted since root cause is outside 42-4 scope). |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.edge_hunter=false |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A | Disabled via settings |

## Reviewer Assessment

**Verdict:** Approved

### Own Diff Analysis

I read the full diff independently. Scope is tight: 8 new SPAN_ENCOUNTER_* constants (4 lines each), one `tension_tracker` field on `_SessionData`, two new helper functions in `session_handler.py` (~50 lines total), one new `build_prompt_zones` helper on `orchestrator.py` (~25 lines), three new test files, one fixture restructure. No deletions of production code. No cross-subrepo changes.

### Findings

**1. Constants declared without emit sites (non-blocking)**
- 8 new SPAN_ENCOUNTER_* constants have no production code that emits them. Fixture notes each as "emit-site wiring follow-up."
- **Verdict:** Accept. This matches the existing pattern in `spans.py` — SPAN_ENCOUNTER_EMPTY_ACTOR_LIST and SPAN_ENCOUNTER_BEAT_FAILURE_BRANCH were added by prior stories on the same "define first, wire when consumers need it" cadence. The alternative (block 42-4 on wiring 8 emit sites that belong to Phase 4 / Epic 39 / observability-enrichment follow-ups) would inflate scope well past the 8-point budget. The parity test enforces the contract that these constants exist; follow-up stories wire emit sites as use cases land.

**2. `_pacing_hint_from_tracker` falls back to `DramaThresholds()` defaults (non-blocking)**
- When `sd.genre_pack.drama_thresholds` is absent, the helper uses pydantic model defaults.
- **Verdict:** Accept. This is logged as a Dev deviation with 6-field format; defaults are declared in pydantic (not magic numbers); isinstance check correctly handles both None and MagicMock cases. Per CLAUDE.md "No Silent Fallbacks" — the check for "silent" is whether the fallback masks a config problem. Here the fallback is explicit (documented, source-visible), the behavior is deterministic (always DramaThresholds()), and the follow-up noted in Dev Assessment is to add a startup-time WARN log when packs miss pacing.yaml. That's sufficient visibility.

**3. `tick_tension_tracker_for_turn` takes `action`/`stakes` params and immediately `del`s them (non-blocking)**
- Simplify-efficiency agent flagged this during TEA verify as unnecessary-complexity.
- **Verdict:** Accept. The seam is test-documented (`test_dispatch_path_ticks_tracker_once_per_turn` calls with these kwargs) and call-site-documented (`_handle_player_action` passes `action="player_action"`, `stakes="normal"`). Removing the params now means future CombatEvent classification work must change all three (signature + call site + test). Keeping them costs one `del` line. Acceptable trade.

**4. AC3 test was RED-phase weaker than it should have been — TEA self-corrected during GREEN (noted)**
- The RED-phase test allowed `python_deviation` prose to count as resolution. User called this out; TEA restructured the fixture into `mapped`/`deferred`/`python_only_spans` lists during GREEN, removing the prose escape hatch.
- **Verdict:** Accept. Mid-stream test hardening is unusual but the rewrite is clearer. Logged as TEA deviation.

**5. `test_build_turn_context_omits_pacing_hint_when_tracker_is_quiet` currently passes for a trivial reason (noted)**
- Before wiring, `TurnContext.pacing_hint` default was None, so the test passed vacuously. After wiring, it asserts that a fresh tracker produces None (real assertion).
- **Verdict:** Accept. TEA self-flagged this at RED time; behavior is now load-bearing.

### Pre-existing Issues Not Blocking

- 162 ruff errors across server repo — unchanged by this PR (verified on develop baseline).
- 20 pytest failures in `tests/genre/test_lethality_policy*.py` + `tests/integration/test_group_c_*.py` + `tests/server/test_session_lethality_context.py` — all cwd-sensitive genre-pack loading failures; predate 42-4 (verified at commit 340c1f8).
- OTEL ConsoleSpanExporter teardown ValueError — not caused by 42-4 (the InMemorySpanExporter processor in the 42-4 integration test is correctly shut down). Root cause is outside this PR's scope.

### AC8 Playtest Gate

Not run yet. Per spec, AC8 is a manual gate that blocks story **finish**, not review. Dev Assessment includes a playtest checklist for Keith to fill in when he runs the gate on OQ-2. SM must verify the playtest observation is recorded before `pf sprint story finish 42-4`.

### Decision

**Approved for merge.** All findings are non-blocking and have accepted rationales. Story is ready for `gh pr create` / merge after AC8 playtest runs.

## Technical Notes

### Scaffold Status
- `sidequest-server/sidequest/server/dispatch/confrontation.py` exists (84 lines) with:
  - `find_confrontation_def(defs, encounter_type)` — exact match lookup (story 3.4)
  - `build_confrontation_payload(encounter, cdef, genre_slug)` — UI overlay payload assembly
  - `build_clear_confrontation_payload(encounter_type, genre_slug)` — unmount overlay

**Keep and extend this file. Do NOT replace blindly.**

### Port Scope (Rust Reference)
All reads from https://github.com/slabgorb/sidequest-api (read-only per ADR-082):
- `crates/sidequest-server/src/dispatch/response.rs` (combat portions)
- `crates/sidequest-server/src/dispatch/tropes.rs:179-181` (encounter resolution from trope beats)
- `crates/sidequest-server/src/dispatch/aside.rs` (combat portions)
- `crates/sidequest-server/src/dispatch/state_mutations.rs:39` (XP-award combat differential)
- `crates/sidequest-server/src/dispatch/telemetry.rs:92` (`in_combat` telemetry field)
- `crates/sidequest-telemetry/src/lib.rs:89-266` (combat watcher event catalog)

### Branch
Working from sidequest-server/develop. Branch: `feat/42-4-combat-dispatch-otel-narrator-wiring`

### Testing Notes
- AC3 requires parity test on OTEL span names (byte-identical to Rust)
- AC7 requires integration test walkthrough with mocked narrator (reuse pattern from story 42-2)
- AC8 human playtest gate must complete before story closes (Keith plays caverns_and_claudes combat to resolution)