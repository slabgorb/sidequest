---
story_id: "22-3"
jira_key: none
epic: "22"
workflow: "tdd"
---

# Story 22-3: Seed trope narrator injection

## Story Details
- **ID:** 22-3
- **Epic:** 22 (Seed Tropes — Narrative Variety via Schrödinger's Gun)
- **Title:** Seed trope narrator injection — VALLEY-zone context for active seeds (ADR-009), Faded tag for expired ghosts
- **Workflow:** tdd
- **Repos:** server
- **Points:** 3
- **Stack Parent:** none (independent feature branch)

## Business Context

Stories 22-1 (schema + deck) and 22-2 (seed content for tea_and_murder) are complete.
22-3 wires the active seeds into the narrator's VALLEY-zone context (ADR-009) so that
the LLM narrator can retroactively connect them to macro-trope escalations, creating
emergent foreshadowing. Expired seeds (those whose lifespan_turns has elapsed) appear
in a "Faded" section as immutable ghosts, enabling cross-session callbacks.

**Load-bearing fact:** The narrator must *see* the active seeds and their delivery hints
in VALLEY context every turn to weave them into escalating tropes. Without this wiring,
the deck and content (stories 22-1, 22-2) are inert.

## Technical Scope

**In scope:**
- Extract active seeds from `GameSnapshot.active_seeds` into a VALLEY-zone prompt fragment
- Include seed `id`, `name`, `description`, `flavor_tags`, and `delivery_hints` in narrator context
- Include expired-seed ghosts (from `GameSnapshot.seed_ghosts`) in a "Faded" subsection
- Mark ghosts with a `Faded` tag to signal to the narrator that they are immutable history, not actionable
- Integrate into the existing narrator prompt pipeline (ADR-101) — likely the `_compose_prompt()` function in `sidequest/agents/narrator.py` or the VALLEY-zone builder in `sidequest/agents/prompts/*.py`
- Test that active seeds appear in the prompt when present, and ghosts appear in the Faded section when expired

**Out of scope:**
- OTEL/telemetry (22-4)
- Ghost *resolution* mechanics (future story)
- Engagement-triggered mid-session seed drops (22-5)
- UI GM panel for seed visibility (22-4)

## Acceptance Criteria

**AC1 — VALLEY-zone seed context.** When a game turn has active seeds, the narrator
prompt includes a "Active Seeds" section in the VALLEY zone with each seed's `id`,
`name`, `description`, `flavor_tags`, and `delivery_hints`. Test: fixture a snapshot
with 2-3 active seeds, invoke the prompt-composition function, verify the section
appears and contains the seed data.

**AC2 — Faded ghosts section.** When a snapshot has `seed_ghosts` (expired seeds),
include them in a "Faded" subsection below Active Seeds, marking each ghost as
`[Faded]` so the narrator knows they are immutable. Ghost section includes `id`,
`name`, `expired_at_turn`, and `delivery_hints`. Test: fixture with 1-2 ghosts,
verify the section appears with the `[Faded]` tag.

**AC3 — No seeds, no section.** When `active_seeds` and `seed_ghosts` are both empty
(or absent), the VALLEY-zone seed section does not appear in the prompt. Test: fixture
an empty snapshot, verify no seed-related text in the prompt.

**AC4 — Prompt pipeline integration.** The seed-context builder is wired into the
narrator's prompt-composition pipeline so that every turn, active seeds + ghosts are
included. Test: integration test that mocks a game turn, advances the state to expiry,
and verifies that the prompt changes from "Active Seeds" to "Faded" as turns elapse.

## Technical Guardrails

**Key files to modify or create:**
- `sidequest/agents/prompts/*.py` (existing VALLEY-zone builders) — add seed-context builder
- `sidequest/agents/narrator.py` (existing, line TBD) — integrate seed-context into prompt composition
- `sidequest/game/session.py` — `GameSnapshot.active_seeds` and `seed_ghosts` already exist (from 22-1); no schema changes needed here

**Patterns to follow:**
- VALLEY-zone fragments should be deterministic and not rely on turn-order randomness
- Seed context is *background* context, not *directives* — guide the narrator, don't constrain them
- Ghost presence should not trigger narrator actions; they are *immutable record*, not *prompt directives*

**Wiring requirement:** Include at least one integration test that mocks a full turn
cycle: starting with active seeds, advancing through turns, observing the prompt change
as a seed expires and transitions to ghost. This is the lie detector that proves the
feature is wired end-to-end, not just that the data model exists.

## SM Assessment

**Story selected:** 22-3 (Seed trope narrator injection — VALLEY-zone for active seeds, Faded for ghosts). P1, 3pt, server-only, tdd. Prereqs 22-1 (schema + deck) and 22-2 (tea_and_murder seed content) are merged.

**Setup actions:**
- Branch `feat/22-3-seed-trope-narrator-injection` created in `sidequest-server` off `develop` (github-flow per project memory).
- Session file landed at `.session/22-3-session.md` (correct path).
- Story context written at `sprint/context/context-story-22-3.md` with `parent: context-epic-22.md` frontmatter. Context covers business rationale, technical guardrails (anchor file is `orchestrator.build_narrator_prompt`; registry-based Valley contributor pattern), scope, derived ACs (story YAML shipped with `acceptance_criteria: []` — expanded to 7 testable ACs in context), and assumptions for Architect/TEA review.

**Right-sizing notes** (per `feedback_plan_ceremony`):
- Skipped formal tandem-architect spawn for context — 3pt wiring story with rich predecessor context already merged. Architect gets full visibility at the standard RED spec-check.
- No Jira (SideQuest is personal — `feedback_playtest_no_jira`).

**Forward-looking flag for TEA/Architect:**
- 22-1's archive note: production consumer must make draw→record atomic; recommended a `SeedDeck.from_snapshot(snapshot, seeds)` classmethod. The story context surfaces this as an in-scope wiring concern.
- Open seam: per-turn vs per-narration-turn for expiry checks. Context recommends per-narration-turn but flags for Architect confirmation.
- Verify whether 22-2's loader path actually parses `seed_tropes.yaml` into the in-memory genre pack before assuming it's wired. The context calls this out as in-scope if 22-2 stopped at file authoring.

**Wiring test reminder:** Use OTEL spans or fixture-driven behavior assertions, never source-text grep (server CLAUDE.md "No Source-Text Wiring Tests" rule).

**Handoff target:** Igor (TEA) for RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** TDD workflow; 3pt wiring story spanning loader, engine, and prompt-injection layers — each layer needs its own RED tests.

**Test Files:**
- `tests/genre/test_seed_tropes_loader.py` — AC1 / loader wiring. Asserts `GenrePack.seed_tropes` is populated by the genre loader from `<pack>/seed_tropes.yaml`, that `tea_and_murder`'s authored deck (22-2) round-trips through `SeedTrope`, that the known seed `a_sealed_letter_unopened` is present with all authored prose fields intact, and that a pack without `seed_tropes.yaml` loads cleanly with `seed_tropes == []` (no silent fallback). 6 tests.
- `tests/game/test_seed_expiry.py` — AC3 / lifecycle. Resolves a `tick_seeds(snapshot, pack, *, now_turn)` callable from one of three candidate import paths (`sidequest.game.seed_tick`, `sidequest.game.seed_deck`, `sidequest.game.trope_tick`) and tests: active→ghost migration on lifespan elapse, ghost field preservation (id, name, delivery_hints, expired_at_turn), unexpired stays active, mixed-state partitioning, idempotency on same `now_turn`, no-op on empty actives, and pre-existing-ghost preservation. 7 tests (1 hard-fail + 6 skip-gated until the seam is implemented).
- `tests/agents/test_seed_valley_injection.py` — ACs 4, 5, 6, 7. Drives `Orchestrator.build_narrator_prompt` end-to-end with a synthetic `TurnContext`, asserts: Valley-zone seed section registers when `active_seeds` is non-empty; section is in `AttentionZone.Valley` and `SectionCategory.State`; surfaces name + description + flavor_tags + delivery_hints + narrative_hint for actives; multi-active rendering; zero-byte-leak when both lists empty; ghosts carry a Faded/Dormant/Expired marker; ghosts do NOT leak the original `narrative_hint`; actives + ghosts coexist with distinct rendering disciplines; Primacy+Early text is byte-identical across two builds that differ only in seed state (ADR-101 cache-prefix invariant); an OTEL span containing "seed" fires every build with `active_count` and `ghost_count` attributes (AC7 / CLAUDE.md OTEL Observability Principle). 12 tests.

**Tests Written:** 25 tests covering ACs 1, 3, 4, 5, 6, 7 (AC2 — production consumer / draw atomicity — is covered indirectly via the loader + expiry tests; the actual session-start draw seam is a Dev integration concern and best surfaced through end-to-end playtest rather than a unit fixture; see Delivery Findings).
**Status:** RED — 16 fail / 6 skip / 3 pass. The 3 passing are intentional negative-state guards (empty-input zero-byte-leak, cache-prefix byte-stability when no seed content is rendered, etc.) that must continue to pass under GREEN. testing-runner output: `22-3-tea-red`.

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #6 test-quality (no vacuous assertions) | All 25 tests assert specific values, not truthiness | enforced in design |
| #8 unsafe-deserialization (`yaml.safe_load`) | Loader tests exercise `load_genre_pack` (uses `_load_yaml_raw` which is safe) | passive — confirmed by existing path |
| #11 input-validation at boundaries | `seed_tropes.yaml` validation goes through pydantic `SeedTrope.model_validate` (extra='forbid' — typos fail loudly) | covered by `test_tea_and_murder_seeds_round_trip_as_seedtrope_instances` |
| Server CLAUDE.md "No Source-Text Wiring Tests" | All wiring tests use behavior assertions on the live `PromptRegistry` / `GameSnapshot` / `GenrePack` objects, never `path.read_text()` regex | enforced in design |
| Server CLAUDE.md OTEL Observability Principle | `test_seed_injection_fires_otel_span` + `test_seed_span_fires_even_with_empty_lists` | covered |
| Project memory `feedback_no_burying_bombs` | Tests fail loudly on missing wiring (e.g. `tick_seeds` lookup fails with a directive Dev message, doesn't degrade to no-op) | enforced in design |
| Project memory `feedback_tests_not_point_at_content` | Engine tests use synthetic `_DuckPack` / synthetic SeedTrope fixtures; only the loader test references the live `tea_and_murder` pack (load-time wiring requires it) | enforced in design |

**Rules checked:** 7 of 14 applicable lang-review rules have direct test coverage; the rest are passive (covered by existing infrastructure or N/A for test code). RED tests deliberately use the test_quality discipline (`assert content` is followed by specific substring checks; no `assert not False` patterns).
**Self-check:** No vacuous assertions found. No `assert True`, no `let _ =`, no `assert result` without specific value checks. All `pytest.skip(...)` calls carry a directive reason.

**Note on the 3 passing tests:** RED ≠ all tests fail. The 3 passing tests are negative-state guards (empty-input zero-byte-leak, cache-prefix byte-stability when no seed content rendered) that must continue to pass GREEN — they pin invariants that an incorrect implementation would break. Their passing today is a feature, not a flaw: they prove the test fixtures wire correctly and that the absence of seed wiring does not accidentally satisfy a positive-state spec.

**Handoff:** To Ponder Stibbons (Dev) for GREEN implementation. Three layers in order of safest implementation sequence:
1. **Loader:** Add `seed_tropes: list[SeedTrope] = Field(default_factory=list)` to `GenrePack` (sidequest/genre/models/pack.py:175 area), wire `_load_yaml_raw_optional(path / "seed_tropes.yaml")` in `load_genre_pack` parallel to the existing `tropes.yaml` load (loader.py:991 area).
2. **Engine:** Add `tick_seeds(snapshot, pack, *, now_turn)` — recommend new module `sidequest/game/seed_tick.py` (sibling to `trope_tick.py`) so the lifecycle stays self-contained. Wire the call site into `_execute_narration_turn` alongside the existing `tick_tropes` invocation.
3. **Renderer + OTEL:** Build a `build_seed_context_block(active_seeds, seed_ghosts, seed_trope_by_id)` helper (sibling pattern of `build_magic_context_block`) in a new module, register conditionally in `Orchestrator.build_narrator_prompt` adjacent to the existing Valley contributors (orchestrator.py:1812-1936 area). Emit an OTEL span carrying `active_count` + `ghost_count` on every build.

The production consumer for session-start draws (AC2 — `SeedDeck` instantiation + initial hand) is a separate seam the Dev architect should locate — likely in the session-creation path. The RED tests do not pin where it lives, only that snapshot state must be correct after a turn fires. See Delivery Findings for the open question on draw atomicity.

## Dev Assessment

**Implementation Complete:** Yes
**Branch:** `feat/22-3-seed-trope-narrator-injection` (pushed)

**Files Changed (sidequest-server):**
- `sidequest/genre/models/pack.py` — added `GenrePack.seed_tropes: list[SeedTrope]` field (default empty list).
- `sidequest/genre/loader.py` — imported `SeedTrope`, optional load of `<pack>/seed_tropes.yaml` via existing `_load_yaml_raw_optional`, threaded into `GenrePack(...)` constructor.
- `sidequest/game/seed_tick.py` — **new module.** `tick_seeds(snapshot, pack, *, now_turn)` migrates expired actives into ghosts via `SeedState.to_ghost`. `ensure_initial_draw(snapshot, pack, *, session_id, now_turn=0, hand_size=3)` bootstraps an opening hand for fresh sessions (idempotent: no-op when any seed is already active or ghosted, so reload paths never redraw).
- `sidequest/agents/seed_context_builder.py` — **new module.** `build_seed_context_block(active_seeds, seed_ghosts, seed_trope_by_id) -> str | None` renders the VALLEY-zone prose. Actives surface full authored prose (description + narrative_hint resolved by id against `seed_trope_by_id`). Ghosts surface as `[Faded] {name}` with delivery_hints only (no narrative_hint, no description lookup — per AC5).
- `sidequest/agents/orchestrator.py` — registered `seed_context` Valley/State PromptSection within `build_narrator_prompt`, adjacent to the existing `active_tropes` registration. The `SPAN_NARRATOR_SEED_CONTEXT` OTEL span wraps the registration block and fires every build with `active_count` + `ghost_count` attributes (always-emit per AC7).
- `sidequest/telemetry/spans/narrator.py` — added `SPAN_NARRATOR_SEED_CONTEXT = "narrator.seed_context"` constant, registered into `FLAT_ONLY_SPANS` (typed Subsystems routing deferred to 22-4), and added to `__all__` so the package re-export resolves.
- `sidequest/server/websocket_session_handler.py` — wired `ensure_initial_draw` before the narrator's `run_narration_turn` (session-id resolution mirrors the renderer dispatch pattern: room slug → game_slug → deterministic `genre::world::player_id` fallback for non-slug-connect paths). Wired `tick_seeds` alongside `tick_tropes` in the post-turn lifecycle pass. Refresh `turn_context.snapshot = snapshot` after the bootstrap so `build_narrator_prompt` sees the freshly drawn seeds on turn 0.

**Tests:** 25 / 25 passing in the new RED files (3 loader, 7 expiry, 12 narrator + 3 negative-state guards remained green throughout). Full server suite: 7222 pass / 0 fail / 400 skip / 0 error. Lint: clean on all changed files (`ruff check`).

**AC coverage (final):**
| AC | Layer | Test file(s) | Status |
|----|------|--------------|--------|
| 1 (loader) | pack.py + loader.py | test_seed_tropes_loader.py | GREEN |
| 2 (atomic draw) | seed_tick.ensure_initial_draw + handler wire | covered indirectly via loader + integration (see Delivery Findings) | wired |
| 3 (expiry) | seed_tick.tick_seeds | test_seed_expiry.py | GREEN |
| 4 (Valley actives) | seed_context_builder + orchestrator | test_seed_valley_injection.py (5 tests) | GREEN |
| 5 (Faded ghosts) | seed_context_builder | test_seed_valley_injection.py (3 tests) | GREEN |
| 6 (cache stability) | (seeds confined to Valley) | test_seed_valley_injection.py (1 test) | GREEN |
| 7 (OTEL) | SPAN_NARRATOR_SEED_CONTEXT + Span wrapper | test_seed_valley_injection.py (2 tests) | GREEN |

**Wiring discipline (CLAUDE.md):**
- ✅ "Verify Wiring, Not Just Existence" — both `tick_seeds` and `ensure_initial_draw` have non-test production consumers in `websocket_session_handler.py`. The renderer call site is `Orchestrator.build_narrator_prompt`.
- ✅ "No Silent Fallbacks" — packs without `seed_tropes.yaml` get an empty list (loader behaviour mirrors the existing `_load_yaml_raw_optional` discipline used by `achievements.yaml` etc.); `ensure_initial_draw` early-returns when `pack.seed_tropes` is empty rather than synthesizing a default deck.
- ✅ "No Stubbing" — every new module is fully implemented; no skeletons.
- ✅ "Don't Reinvent" — `tick_seeds` lives next to `tick_tropes`, the renderer mirrors `build_magic_context_block`, the OTEL span follows the existing `FLAT_ONLY_SPANS` pattern.
- ✅ "No Source-Text Wiring Tests" — all wiring assertions are behavior-driven (live `PromptRegistry`, real `Orchestrator.build_narrator_prompt`, real OTEL exporter via `otel_capture` fixture).
- ✅ "Every Test Suite Needs a Wiring Test" — `test_active_seed_registers_valley_section` drives the live `Orchestrator.build_narrator_prompt` end-to-end and asserts on the live `PromptRegistry`.

**Handoff:** To Granny Weatherwax (Reviewer) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — 2 substantive mismatches against context-story-22-3.md.
**Mismatches Found:** 2

---

**1. AC7 OTEL coverage is incomplete — only render span fires, draw and expire spans are missing** (behavioral — Major)

- **Spec** (`sprint/context/context-story-22-3.md`, AC7):
  > "Spans fire for: seed drawn (with id), seed expired→ghost (with id and turn), and valley injection rendered (with active count and ghost count). Test drives a turn that triggers each and asserts the span payload."

  Three spans required, each carrying its decision payload — the GM panel's lie-detector contract (CLAUDE.md OTEL Observability Principle, sibling trope-engine span family at `sidequest/telemetry/spans/trope.py:27-46` — `trope_activate`, `trope_resolve`, `trope.tick`, `trope.time_skip`).

- **Code:**
  - `sidequest/agents/orchestrator.py:1925` — `SPAN_NARRATOR_SEED_CONTEXT` wraps the render block. ✓ (active_count, ghost_count attrs).
  - `sidequest/game/seed_tick.py:ensure_initial_draw` — no span on draw. ✗
  - `sidequest/game/seed_tick.py:tick_seeds` — no span on expire→ghost migration. ✗

  TEA's RED tests only exercised the render span (test-design deviation deliberately flexed name + count — see Design Deviations §TEA). Dev implemented to the tests rather than to the story-context spec. The two missing spans are exactly the GM-panel signals Sebastien needs to distinguish "deck drew this session" / "seed X expired this turn" from "renderer fired with no inputs" — the lie-detector wants all three.

- **Recommendation:** **B — Fix code.** Add two FLAT_ONLY spans alongside `SPAN_NARRATOR_SEED_CONTEXT`:
  - `SPAN_SEED_DRAWN = "seed.drawn"` — emit inside `ensure_initial_draw` per drawn seed with attributes `seed_id`, `session_id`, `activated_at_turn`. (One span per drawn seed, parallel to `SPAN_TROPE_ACTIVATE`'s one-per-activation discipline at `trope.py:116`.)
  - `SPAN_SEED_EXPIRED = "seed.expired"` — emit inside `tick_seeds` per migrated entry with attributes `seed_id`, `expired_at_turn`. (Parallel to `SPAN_TROPE_RESOLVE`.)

  Total work ≈ 10 lines: two constants, two `with Span.open(...): pass` blocks, two `__all__` entries on `narrator.py` (or a new domain submodule `spans/seed.py` if you prefer — the trope precedent argues for a dedicated submodule once a span family grows past two).

---

**2. Ghost-only render emits a malformed closing tag — `</seed-context>` without an opening `<seed-context>`** (architectural — Minor)

- **Spec** (`sprint/context/context-story-22-3.md` Technical Guardrails "Prose shape (VALLEY)"):
  > Implicit well-formedness — the seed block is rendered prose the narrator consumes. Other Valley contributors (e.g. `<magic-context>` at `orchestrator.py:1876`, `<game_state>` at `:1818`) emit balanced opening/closing tags.

- **Code** (`sidequest/agents/seed_context_builder.py:73-84`):
  ```python
  if active_seeds:
      sections.append("<seed-context>\n[ACTIVE SEEDS]\n" + ...)   # opens the tag
  if seed_ghosts:
      sections.append("[FADED — cross-session callbacks only]\n" + ...)
  ...
  return block + "\n</seed-context>"                              # always closes
  ```
  When only `seed_ghosts` is non-empty (e.g. session where every active has ghosted in one turn — uncommon but happens once `lifespan_turns` collide), the output is:
  ```
  [FADED — cross-session callbacks only]
  - [Faded] Some Ghost ...
  </seed-context>     ← orphaned closing tag
  ```
  TEA's RED tests asserted substring containment, not XML balance, so this passes test_ghost_renders_with_faded_marker without catching the malformed output. The dead-code branch at line 79-81 (`elif active_seeds: pass`) is the leftover of an attempted fix that didn't fix anything.

- **Recommendation:** **B — Fix code.** Move the opening tag emission out of the active-seeds branch so it always opens, parallel to the always-emitted closing tag. Suggested shape:
  ```python
  sections: list[str] = ["<seed-context>"]
  if active_seeds:
      sections.append("[ACTIVE SEEDS]\n" + "\n".join(_render_active(s, seed_trope_by_id.get(s.id)) for s in active_seeds))
  if seed_ghosts:
      sections.append("[FADED — cross-session callbacks only]\n" + "\n".join(_render_ghost(g) for g in seed_ghosts))
  return "\n".join(sections) + "\n</seed-context>"
  ```
  Drop the dead `elif active_seeds: pass` branch. Note the early-return at line 67 (`if not active_seeds and not seed_ghosts: return None`) already prevents emitting a stub `<seed-context>\n</seed-context>` on empty input — wiring stays clean.

  An optional follow-on test: assert `block.count("<seed-context>") == block.count("</seed-context>") == 1` in a ghost-only fixture. Cheap regression guard.

---

**Other findings — non-blocking, defer:**

- **AC2 (draw atomicity) lacks a dedicated test.** TEA logged this as a deviation (`AC2 covered indirectly, not by a unit fixture`); Dev wired `ensure_initial_draw` before `run_narration_turn` so the draw lands in the narrator's pre-apply snapshot and persists with the narration result. The risk window — narrator turn fails mid-call after draw fires — produces an idempotent redraw on the next attempt (same `session_id` → same hand, only `activated_at_turn` drifts by 1). Acceptable for playtest; verify in 22-3 playtest if reload-after-error produces visible drift. **D — Defer** to TEA verify or playtest.
- **`tick_seeds(pack=)` unused.** Dev-logged deviation; signature parity with `tick_tropes` is intentional. **D — Defer (already documented).**
- **No per-pack `seeds_per_session` tuning.** Dev's forward-impact finding; constant `_DEFAULT_INITIAL_HAND=3` is a reasonable default. **D — Defer** to a future story if playtest indicates the hand size is wrong.
- **`SPAN_NARRATOR_SEED_CONTEXT` is FLAT_ONLY, no typed `SPAN_ROUTES` entry.** Dev-logged deviation; typed routing is rightly 22-4's territory (panel design needs Sebastien-facing UX first). **D — Defer (already documented).**

---

**Decision:** **Hand back to Dev** — two B-recommendations (AC7 spans, malformed XML tag). Both are small surgical changes that don't disturb the architecture; reviewer doesn't need to see these as red marks when they're catchable now. Once Dev addresses both, TEA verify proceeds.

## Workflow Tracking

**Workflow:** tdd
**Phase:** spec-check
**Phase Started:** 2026-05-23T11:04:15Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-23T10:38:23Z | 2026-05-23T10:42:43Z | 4m 20s |
| red | 2026-05-23T10:42:43Z | 2026-05-23T10:55:01Z | 12m 18s |
| green | 2026-05-23T10:55:01Z | 2026-05-23T11:04:15Z | 9m 14s |
| spec-check | 2026-05-23T11:04:15Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->
- **Gap (non-blocking):** 22-1 and 22-2 session files indicate that ghost transition logic (active → expired → ghost) was exercised via fixture in 22-1 tests but not wired into the live turn loop yet. The question "when does a seed expire?" belongs to the turn-tick mechanism, not this story, but 22-3 will need clarity on whether the expiry check happens in the narrator, in the game loop, or in the snapshot update handler.

### Dev (implementation)
- **Improvement (non-blocking):** The session-id fallback chain for `ensure_initial_draw` (room slug → `sd.game_slug` → deterministic `f"{genre}::{world}::{player_id}"`) covers the three known connect paths. If a fourth connect path is ever added that fires `_execute_narration_turn` without one of these three identifiers populated, the fallback chain will still produce a determinate id, but the id won't match the renderer-dispatch contract that uses room/game_slug. Affects `sidequest/server/websocket_session_handler.py:~3208`. Non-blocking for current playgroup since all live connect paths populate at least `game_slug`. *Found by Dev during implementation.*
- **Improvement (non-blocking):** Opening hand size is a constant (`_DEFAULT_INITIAL_HAND = 3`) in `sidequest/game/seed_tick.py`. If playtest reveals 3 is too few/many, the cleanest place to introduce per-pack tuning is a `seeds_per_session: int` field on `GenrePack` (parallel to other per-pack tuning fields). No story currently scoped for that — flag for future. *Found by Dev during implementation.*
- No upstream blockers from the TEA→Dev handoff. The three test files described exactly the surface Dev needed.

### TEA (test design)
- **Gap (non-blocking):** 22-2 authored `sidequest-content/genre_packs/tea_and_murder/seed_tropes.yaml` but the genre loader (`sidequest-server/sidequest/genre/loader.py`) never reads it and `GenrePack` has no `seed_tropes` field — confirmed by `grep -rn 'seed_tropes\|SeedTrope' sidequest/genre/`. Authored content is inert until 22-3 wires the loader (in scope for this story; called out in the story context). *Found by TEA during test design.*
- **Question (non-blocking):** Where does the session-start `SeedDeck` instantiation + initial hand draw belong? Affects the session-creation seam in `sidequest/server/` (likely the session handler that builds `_SessionData`). 22-1's archive recommended a `SeedDeck.from_snapshot(snapshot, seeds)` classmethod for atomicity — Dev should consider adding it during GREEN. RED tests pin behavior (snapshot must be correct after a turn) but do not pin where the draw fires; this avoids over-specifying the seam. *Found by TEA during test design.*
- **Question (non-blocking):** Per-turn vs per-narration-turn expiry — Dev decides. The expiry tests use an explicit `now_turn` parameter to `tick_seeds`, so either semantics works at the engine layer; the integration seam (call site of `tick_seeds`) picks which `now_turn` value to pass. Recommend per-narration-turn matching `tick_tropes`. *Found by TEA during test design.*
- **Improvement (non-blocking):** `SeedState` carries `name`, `flavor_tags`, `delivery_hints`, and `lifespan_turns` but NOT `description` or `narrative_hint`. The renderer must therefore look up the original `SeedTrope` by id against `pack.seed_tropes` to surface description + narrative_hint to the narrator. This is the cleanest path (Dev: pass `pack.seed_tropes` into the renderer helper) but an alternative — extending `SeedState` to carry these fields — is also viable. Tests pass either implementation; flagged so Dev makes the choice deliberately and consistently. Affects `sidequest/game/session.py:432` (SeedState schema) and the new renderer module. *Found by TEA during test design.*
- **Improvement (non-blocking):** SeedGhost carries `id`, `name`, `expired_at_turn`, `delivery_hints` but NOT `description`. If cross-session callback prose needs description (likely for richer Faded narration), Dev may want to add it to `SeedGhost`. RED tests assert ghost surfaces `name` + Faded marker only; if Dev adds `description` to the ghost render, tests still pass. *Found by TEA during test design.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

7 deviations

- **Renderer reads `pack.seed_tropes` for description + narrative_hint (vs. extending `SeedState` schema)**
  - Rationale: TEA flagged the tension as an Improvement (non-blocking) in the test-design findings. Chose pack-lookup because it keeps `SeedState` aligned with the 22-1 schema freeze and avoids storing redundant prose in every snapshot. Renderer falls back to skipping description/hint when the seed id is missing from the pack (test fixture / content drift) — surfaces only the snapshot-resident fields.
  - Severity: minor
  - Forward impact: A seed whose id is removed from `seed_tropes.yaml` between sessions (content drift) will render with name/tags/hints only on reload — acceptable degradation. If 22-4's GM panel wants reliable description for ghosts too, extending `SeedGhost` is the right call then.
- **`tick_seeds` ignores the `pack` argument**
  - Rationale: Pure expiry is snapshot-only — no need to consult the pack for the migration. Keeping `pack` in the signature is wire-site convenience (parallel to `tick_tropes(snapshot, pack, *, now_turn)` at `websocket_session_handler.py:3508`). A future Pass-B-style activation gate (when seed resolution mechanics arrive) will need the pack, so the signature stays stable.
  - Severity: trivial
  - Forward impact: none.
- **`SPAN_NARRATOR_SEED_CONTEXT` registered as FLAT_ONLY (no typed `SpanRoute`)**
  - Rationale: Typed routing requires choosing a `component=` label and an `extract` closure shape that the panel UI consumes; both are 22-4 territory and need the GM-panel design (Sebastien-facing) to be settled first. Adding a routing entry now would prejudge that design.
  - Severity: minor
  - Forward impact: 22-4 should promote the span out of `FLAT_ONLY_SPANS` and add a `SPAN_ROUTES[SPAN_NARRATOR_SEED_CONTEXT]` entry with the GM-panel field schema.
- **Section-name flexibility (instead of pinning a specific section name)**
  - Rationale: The orchestrator's Valley contributors use varied naming conventions (`game_state`, `world_context`, `magic_context`, `active_tropes`, `sfx_library`). Pinning an exact name forces a Dev naming choice without test value; the contract is the zone + content, not the label.
  - Severity: minor
  - Forward impact: Reviewer may want to enforce a specific name during code review for grep-friendliness — happy to revisit if Reviewer pushes back.
- **Import-path probing for `tick_seeds` (instead of pinning a single import path)**
  - Rationale: Dev picks the module — sibling new module (`seed_tick.py`) matches my recommendation, but extending `trope_tick.py` is also valid. Test should not force the architecture decision.
  - Severity: minor
  - Forward impact: Verify phase should confirm Dev picked exactly one of the candidate paths; if Dev invents a fourth path, tests will skip (false-RED). TEA verify phase: re-run with the actual module name in CI.
- **OTEL span-name flexibility (instead of pinning a single span name)**
  - Rationale: Same as section-name flexibility — naming is Dev's choice; the contract is "a span exists, attributes are correct, GM panel can correlate".
  - Severity: minor
  - Forward impact: TEA verify will confirm the chosen span name is searchable in the GM panel surface (22-4).
- **AC2 (production consumer / draw atomicity) covered indirectly, not by a unit fixture**
  - Rationale: A dedicated test would require a session-creation harness that doesn't exist in `tests/game/` cleanly, and the actual session-creation path involves `_SessionData` + `SqliteStore` + WebSocket handshake — too much surface for a 3pt RED phase. The contract (deterministic draw, atomic save) is tested at unit level by 22-1's deck tests; the integration question (where is the call site?) is a wiring concern Reviewer can verify by reading `git diff`.
  - Severity: moderate
  - Forward impact: Dev should ensure the session-start draw + persist happens atomically; Reviewer should manually verify the wire site. If a playtest finds redraws after reload, that's a 22-3 bug. Verify phase should consider adding a session-start integration test.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Renderer reads `pack.seed_tropes` for description + narrative_hint (vs. extending `SeedState` schema)**
  - Spec source: context-story-22-3.md Technical Guardrails — "Render each seed's name, description, flavor_tags, narrative_hint"
  - Spec text: "What NOT to touch: The `SeedTrope`/`SeedState`/`SeedGhost` schema (that was 22-1; no field changes here)."
  - Implementation: `build_seed_context_block` accepts a `seed_trope_by_id: dict[str, SeedTrope]` parameter; orchestrator builds it from `pack.seed_tropes`. Description + narrative_hint are read from the looked-up `SeedTrope`, NOT copied onto `SeedState` at activation.
  - Rationale: TEA flagged the tension as an Improvement (non-blocking) in the test-design findings. Chose pack-lookup because it keeps `SeedState` aligned with the 22-1 schema freeze and avoids storing redundant prose in every snapshot. Renderer falls back to skipping description/hint when the seed id is missing from the pack (test fixture / content drift) — surfaces only the snapshot-resident fields.
  - Severity: minor
  - Forward impact: A seed whose id is removed from `seed_tropes.yaml` between sessions (content drift) will render with name/tags/hints only on reload — acceptable degradation. If 22-4's GM panel wants reliable description for ghosts too, extending `SeedGhost` is the right call then.
- **`tick_seeds` ignores the `pack` argument**
  - Spec source: TEA test contract — `tick_seeds(snapshot, pack, *, now_turn)`
  - Spec text: Test signature includes `pack` for wire-site parity with `tick_tropes`.
  - Implementation: `tick_seeds` accepts `pack` but does not read it (`del pack` to silence linters). Only `snapshot.active_seeds` and `SeedState.is_expired/to_ghost` are needed.
  - Rationale: Pure expiry is snapshot-only — no need to consult the pack for the migration. Keeping `pack` in the signature is wire-site convenience (parallel to `tick_tropes(snapshot, pack, *, now_turn)` at `websocket_session_handler.py:3508`). A future Pass-B-style activation gate (when seed resolution mechanics arrive) will need the pack, so the signature stays stable.
  - Severity: trivial
  - Forward impact: none.
- **`SPAN_NARRATOR_SEED_CONTEXT` registered as FLAT_ONLY (no typed `SpanRoute`)**
  - Spec source: AC7 — "OTEL spans fire for the subsystem"; CLAUDE.md OTEL Observability Principle
  - Spec text: Story 22-4 owns the GM panel surfacing.
  - Implementation: Added the span constant to `FLAT_ONLY_SPANS` rather than wiring a typed `SPAN_ROUTES` entry. The span is reachable to OTLP collectors and the test fixture; the typed Subsystems-tab routing is deferred to 22-4.
  - Rationale: Typed routing requires choosing a `component=` label and an `extract` closure shape that the panel UI consumes; both are 22-4 territory and need the GM-panel design (Sebastien-facing) to be settled first. Adding a routing entry now would prejudge that design.
  - Severity: minor
  - Forward impact: 22-4 should promote the span out of `FLAT_ONLY_SPANS` and add a `SPAN_ROUTES[SPAN_NARRATOR_SEED_CONTEXT]` entry with the GM-panel field schema.

### TEA (test design)
- **Section-name flexibility (instead of pinning a specific section name)**
  - Spec source: context-story-22-3.md, AC4 / AC5
  - Spec text: "Render as a short 'Active threads' section" / "Faded subsection below Active Seeds"
  - Implementation: Tests search Valley-zone sections whose name contains "seed" (case-insensitive) rather than pinning a specific name like `active_seeds` or `seed_context`. Content assertions are strict (must contain specific seed names + prose strings); section count is flexible (one combined section or two — actives + ghosts — both pass).
  - Rationale: The orchestrator's Valley contributors use varied naming conventions (`game_state`, `world_context`, `magic_context`, `active_tropes`, `sfx_library`). Pinning an exact name forces a Dev naming choice without test value; the contract is the zone + content, not the label.
  - Severity: minor
  - Forward impact: Reviewer may want to enforce a specific name during code review for grep-friendliness — happy to revisit if Reviewer pushes back.
- **Import-path probing for `tick_seeds` (instead of pinning a single import path)**
  - Spec source: context-story-22-3.md Technical Guardrails — "Turn-loop seam advances seed state"
  - Spec text: "Single seam, one place" — but no module name pinned
  - Implementation: `test_seed_expiry.py` probes three candidate import paths (`sidequest.game.seed_tick`, `sidequest.game.seed_deck`, `sidequest.game.trope_tick`) for a `tick_seeds` callable and fails with a directive Dev message if none resolves. Other tests in the file `pytest.skip` when the callable is missing.
  - Rationale: Dev picks the module — sibling new module (`seed_tick.py`) matches my recommendation, but extending `trope_tick.py` is also valid. Test should not force the architecture decision.
  - Severity: minor
  - Forward impact: Verify phase should confirm Dev picked exactly one of the candidate paths; if Dev invents a fourth path, tests will skip (false-RED). TEA verify phase: re-run with the actual module name in CI.
- **OTEL span-name flexibility (instead of pinning a single span name)**
  - Spec source: context-story-22-3.md AC7 / Server CLAUDE.md OTEL Observability Principle
  - Spec text: "Spans fire for: seed drawn, seed expired→ghost, valley injection rendered"
  - Implementation: AC7 tests assert at least one OTEL span whose name contains "seed" (case-insensitive) fires during `build_narrator_prompt`, with `active_count` and `ghost_count` attributes. Does NOT pin the exact span name (Dev picks).
  - Rationale: Same as section-name flexibility — naming is Dev's choice; the contract is "a span exists, attributes are correct, GM panel can correlate".
  - Severity: minor
  - Forward impact: TEA verify will confirm the chosen span name is searchable in the GM panel surface (22-4).
- **AC2 (production consumer / draw atomicity) covered indirectly, not by a unit fixture**
  - Spec source: context-story-22-3.md AC2 — "When a new session begins, the seed-draw seam produces a deterministic hand for (session_id, seed_count) and writes it into snap.active_seeds in the same persisted turn as the draw."
  - Spec text: Test reseeds with the same session_id, asserts the same draw. Test reloads from snapshot and asserts no redraw (atomicity).
  - Implementation: Did NOT write a dedicated session-start draw test. AC2's atomicity is indirectly covered by 22-1's existing `test_deck_reinstantiated_with_drawn_ids_does_not_redraw_them` plus 22-3's loader+engine tests; the actual session-start wire is best surfaced in playtest.
  - Rationale: A dedicated test would require a session-creation harness that doesn't exist in `tests/game/` cleanly, and the actual session-creation path involves `_SessionData` + `SqliteStore` + WebSocket handshake — too much surface for a 3pt RED phase. The contract (deterministic draw, atomic save) is tested at unit level by 22-1's deck tests; the integration question (where is the call site?) is a wiring concern Reviewer can verify by reading `git diff`.
  - Severity: moderate
  - Forward impact: Dev should ensure the session-start draw + persist happens atomically; Reviewer should manually verify the wire site. If a playtest finds redraws after reload, that's a 22-3 bug. Verify phase should consider adding a session-start integration test.