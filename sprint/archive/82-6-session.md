---
story_id: "82-6"
jira_key: ""
epic: "82"
workflow: "tdd"
---
# Story 82-6: Wire milestone accumulation → level-up engine + OTEL + player-facing advancement delta (ADR-021 track 1; genre/models/progression.py ~:62)

## Story Details
- **ID:** 82-6
- **Jira Key:** (none — YAML-only sprint)
- **Workflow:** tdd
- **Stack Parent:** none (82-3 structural dependency already satisfied)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T12:31:48Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T11:40:55Z | 2026-06-04T11:42:31Z | 1m 36s |
| red | 2026-06-04T11:42:31Z | 2026-06-04T12:00:02Z | 17m 31s |
| green | 2026-06-04T12:00:02Z | 2026-06-04T12:08:07Z | 8m 5s |
| review | 2026-06-04T12:08:07Z | 2026-06-04T12:17:42Z | 9m 35s |
| red | 2026-06-04T12:17:42Z | 2026-06-04T12:21:31Z | 3m 49s |
| green | 2026-06-04T12:21:31Z | 2026-06-04T12:22:48Z | 1m 17s |
| review | 2026-06-04T12:22:48Z | 2026-06-04T12:31:48Z | 9m |
| finish | 2026-06-04T12:31:48Z | - | - |

## Sm Assessment

**Story:** 82-6 — Wire milestone accumulation → level-up engine + OTEL + player-facing advancement delta (ADR-021 track 1).

**Readiness:** Ready for RED. All setup gates pass:
- Dependency `82-3` is structural — 82-3 has status `split` (decomposed into 82-6/7/8), so the dependency is satisfied by the split itself, not a pending merge.
- Merge gate clear: 0 in-progress, 0 in-review, no open sidequest-server PRs.
- Context doc present and detailed: `sprint/context/context-story-82-6.md` (reused, not overwritten).
- Branch `feat/82-6-wire-milestone-levelup` created off `develop` (server base per repos.yaml).

**Scope (single repo: sidequest-server):**
- Resolve the `TODO: wire at level-up` at `genre/models/progression.py ~:62` — add a runtime engine in the turn pipeline that drives level-up from milestone accumulation.
- Emit an OTEL/watcher span on the level-up crossing, mirroring `SPAN_DISPOSITION_SHIFT` so the GM panel can confirm engagement (OTEL Observability Principle).
- Surface the advancement delta in a **player-facing** projection (mechanics-first — Sebastien/Jade need legible advancement; per CLAUDE.md this is a player-UI concern, not a dev/GM-only emit).

**Out of scope / do NOT touch:**
- Track 4 (journey recap, `persistence.py`/`pg/snapshot.py`) — already live; it is the precedent to mirror, not the target.
- Tracks 2–3 (AffinityState tiers, item narrative_weight) — siblings 82-7 / 82-8.
- Progression YAML schema.

**Wiring requirement:** Per the epic's doctrine ("Verify Wiring, Not Just Existence"), the ADR-021 track-1 frontmatter cannot return to `live` until a production consumer reaches the milestone→level-up path AND emits OTEL. Every test suite must include a wiring test proving the engine is reachable from a production code path.

**Routing:** Phased tdd → handing off to TEA (Amos Burton) for the RED phase.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (blocking): The progression config counts **milestones** (`milestones_per_level`, `milestone_categories` — authored 3/level by space_opera, heavy_metal, road_warrior, neon_dystopia, pulp_noir, mutant_wasteland, elemental_harmony), but the **only live runtime accumulator is `core.xp`** via `award_turn_xp` (`server/dispatch/encounter_lifecycle.py:1299`) — there is no milestone counter on `CreatureCore`. Dev must reconcile the two: either derive milestones-completed from accumulated `core.xp`, or add a milestone counter incremented by specific outcomes. Affects `server/dispatch/encounter_lifecycle.py` + `game/creature_core.py`. The RED tests take the "wire up what exists" path (xp is the accumulator) and seed `core.xp` past the cap so they hold under any positive conversion ratio — see Design Deviation TEA-1. *Found by TEA during test design.*
- **Improvement** (non-blocking): `tests/server/test_xp_award.py::test_award_turn_xp_is_wired_into_the_real_narration_turn` asserts `'award_turn_xp(' in inspect.getsource(...)` — a **source-text wiring test**, explicitly forbidden by sidequest-server `CLAUDE.md` ("No Source-Text Wiring Tests"). The new `test_levelup_turn_wiring.py` replaces that pattern with an OTEL-driven turn test for the adjacent subsystem; the xp-award one should be migrated to the same shape. Affects `tests/server/test_xp_award.py:122-131`. *Found by TEA during test design.*
- **Gap** (non-blocking): `award_turn_xp` already emits a `component="progression"` watcher event for the xp tick but nothing consumes it as a level-up trigger — the live seam is one function-call short of working. The level-up engine should run immediately after `award_turn_xp` at `websocket_session_handler.py:1262`. *Found by TEA during test design.*

### Dev (implementation)
- **Resolved (blocking Conflict)**: Reconciled the milestone-vs-xp impedance mismatch by deriving milestones from the live `core.xp` accumulator (`milestones_completed = max(0, core.xp) // _XP_PER_MILESTONE`, `_XP_PER_MILESTONE=100`) — the "wire up what exists" path TEA recommended. No new milestone counter added to `CreatureCore`. *Resolved by Dev during implementation.*
- **Improvement** (non-blocking): The transient player-facing delta currently rides `Character.last_advancement` (excluded from persistence) and is reset each turn by `apply_level_ups`. A cleaner long-term surface would thread the per-turn `crossings` list directly into the post-turn PARTY_STATUS build rather than parking it on the character; deferred as it isn't required by the ACs. Affects `server/views.py` + `server/dispatch/encounter_lifecycle.py`. *Found by Dev during implementation.*
- The TEA `test_xp_award.py` source-text-wiring Improvement (non-blocking) is left as-is — out of scope for 82-6; should become its own cleanup story.

### Reviewer (code review)
- **Gap** (blocking): AC3's player-facing populate (`party_member_from_character` copying `last_advancement` → `PartyMember.advancement`) is asserted only by field existence, not behavior. Affects `tests/server/test_levelup_turn_wiring.py` (add a populate-and-assert test). *Found by Reviewer during code review.*
- **Gap** (non-blocking): No-downgrade/at-max guard (`<= before`) and the per-turn `last_advancement=None` reset are untested. Affects `tests/integration/test_levelup_otel_wiring.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Consider a `@model_validator` on `ProgressionConfig` failing loud when exactly one of `milestones_per_level`/`max_level` is zero (half-configured pack); out of scope here (progression schema), good follow-up. Affects `genre/models/progression.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **TEA-1: Accumulation source pinned to `core.xp` (not a new milestone counter)**
  - Spec source: context-story-82-6.md, "AC Context" §1 + "Assumptions"
  - Spec text: "Milestone accumulation drives level-up … Turn processing already exposes the outcome signals needed to accumulate milestones … If a needed signal is missing, surfacing it is small and in scope — log a deviation."
  - Implementation: Tests treat the already-live `core.xp` (accumulated by `award_turn_xp`) as the progression accumulator rather than introducing a parallel milestone counter. The behavioral/OTEL tests seed `core.xp` far past the ceiling and assert clamping to `max_level`, so they hold under ANY positive xp→milestone conversion ratio Dev chooses; the exact ratio is left to Dev.
  - Rationale: "Don't Reinvent — Wire Up What Exists" — `core.xp` is the only live accumulator and `award_turn_xp` already tags its emit `component="progression"`. Avoids a second source of truth.
  - Severity: minor
  - Forward impact: If Dev instead adds a discrete milestone counter, `test_levelup_turn_wiring.py` / `test_levelup_otel_wiring.py` seed `core.xp` — Dev must seed the new counter instead and log the change. The pure-math `resolve_level` test is unaffected (it takes abstract `milestones_completed`).

- **TEA-2: Engine API surface chosen by tests (resolve_level / apply_level_ups / LevelUp)**
  - Spec source: context-story-82-6.md, "Technical Guardrails" / "Patterns to follow"
  - Spec text: "Add a runtime engine that runs in the turn pipeline and emits an OTEL/watcher span … Mirror the disposition-shift span shape." (no API names specified)
  - Implementation: RED pins concrete symbols — `resolve_level(milestones_completed, config) -> int` in `genre/models/progression.py` (mirrors the sibling `resolve_wealth_tier`), and `apply_level_ups(snapshot, progression) -> list[LevelUp]` in `server/dispatch/encounter_lifecycle.py` (sibling to `award_turn_xp`; returns crossings like `apply_resource_patches`). Watcher event: `field="progression.level_up"`, `component="progression"`.
  - Rationale: TDD-RED must name the contract; chosen to mirror the nearest existing precedents to minimize novelty.
  - Severity: minor
  - Forward impact: Dev may rename with a logged deviation provided behavior + OTEL field name hold; renames cascade to the three test files.

- **TEA-3: Player-facing surface chosen as a `PartyMember.advancement` field (AC3)**
  - Spec source: context-story-82-6.md, "AC Context" §3
  - Spec text: "The advancement delta is legible in a player-facing surface — the player sees the level change and its driver, not just a silent stat bump."
  - Implementation: RED asserts `PartyMember.model_fields` contains `advancement` (reflection tripwire — the CLAUDE.md-blessed non-source-text exception). Chosen because the track-3 wealth label already rides `PartyMember` via `views.party_member_from_character` → `resolve_wealth_tier`, the exact precedent.
  - Rationale: Strongest existing player-facing precedent; keeps AC3 from being the silent stat bump it explicitly forbids, and keeps the player surface distinct from the GM/OTEL emit (per CLAUDE.md, the OTEL emit is a dev/GM lie-detector, NOT the player surface).
  - Severity: minor
  - Forward impact: Dev may pick a different player surface (e.g. a dedicated notification message) with a logged deviation, as long as before/after/driver is player-legible; that would change `test_party_member_exposes_advancement_delta_field`.

### Dev (implementation)
- **Honored TEA-1/2/3 as specified** — xp-as-accumulator, the `resolve_level`/`apply_level_ups`/`LevelUp` API surface, and `PartyMember.advancement` as the player surface. `LevelUp` is an alias of the new `protocol.models.AdvancementDelta` (one type, clean layering), so the engine return value is directly usable as the player-facing payload. No re-log needed for those.
- **XP→milestone conversion ratio `_XP_PER_MILESTONE = 100`**
  - Spec source: context-story-82-6.md, "AC Context" §1 + Design Deviation TEA-1
  - Spec text: "Milestone accumulation drives level-up … the exact xp→milestone conversion is left to Dev."
  - Implementation: `milestones_completed = max(0, core.xp) // 100` in `encounter_lifecycle.apply_level_ups`. With `award_turn_xp` granting 10 (calm) / 25 (combat) per turn and packs authoring `milestones_per_level` 2–3, one level is ~8–30 turns of play.
  - Rationale: A round, legible constant that yields a sane play cadence; no content authored an xp-per-milestone value, so a default is required (kept as a single named module constant, not scattered literals).
  - Severity: minor
  - Forward impact: Tunable in one place. If a future story makes this genre-authored (e.g. `xp_per_milestone` in progression.yaml), the constant becomes the fallback. The behavioral tests are ratio-agnostic (they seed xp past the cap), so a retune won't break them.

### Reviewer (audit)
- **TEA-1 (xp-as-accumulator)** → ✓ ACCEPTED by Reviewer: "wire up what exists" is the correct call; `core.xp` is the only live accumulator and `award_turn_xp` already tags `component=progression`. No parallel counter introduced. Sound.
- **TEA-2 (engine API: resolve_level/apply_level_ups/LevelUp)** → ✓ ACCEPTED by Reviewer: mirrors `resolve_wealth_tier`/`apply_resource_patches` precedents; `LevelUp = AdvancementDelta` alias keeps one type with clean protocol layering. (Minor readability note flagged by preflight; not a deviation issue.)
- **TEA-3 (player surface = `PartyMember.advancement`)** → ✓ ACCEPTED by Reviewer (surface choice): strongest precedent (track-3 wealth label rides PartyMember), correctly distinct from the GM/OTEL emit. NOTE: the *implementation* of this surface is sound but the *test* for it is the HIGH finding in the verdict — the deviation's chosen surface is right; its coverage is not.
- **Dev (`_XP_PER_MILESTONE=100`)** → ✓ ACCEPTED by Reviewer: a single named constant, sane cadence (~84–210 turns to max on real packs), single point of future tuning. No scattered literals.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core engine wiring (ADR-021 track 1) — not a chore bypass.

**Test Files:**
- `tests/genre/test_models/test_milestone_levelup.py` — pure `resolve_level` math: thresholds, multi-level edge (AC1 edge), `max_level` cap, unconfigured (`per_level==0`) + negative guards. 8 cases (one parametrized table).
- `tests/integration/test_levelup_otel_wiring.py` — `apply_level_ups` engine behavior + `progression.level_up` OTEL watcher event (mirrors `test_disposition_otel_wiring.py` harness) + `LevelUp` delta record (AC3 data) + no-crossing/unconfigured silence. 4 cases.
- `tests/server/test_levelup_turn_wiring.py` — engine fires inside the real `_execute_narration_turn` (AC4 wiring, OTEL-driven, refactor-stable) + `PartyMember.advancement` player surface (AC3). 2 cases.

**Tests Written:** 14 tests covering 4 ACs.
**Status:** RED confirmed (testing-runner, serial `-n0`): 2 collection ImportErrors (`resolve_level`; `apply_level_ups`/`LevelUp`) + 2 assertion failures (level stays 1 in the real turn; no `PartyMember.advancement`). **Zero category-(c) setup errors** — tests are well-formed and fail for the intended reasons.

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| 1 Milestone→level-up (+ multi-level edge) | `resolve_level` math suite; `test_level_up_mutates_level_and_publishes_state_transition` | failing (RED) |
| 2 OTEL emission on crossing | `test_level_up_mutates_level_and_publishes_state_transition`; `test_no_crossing_is_silent_no_level_no_event` | failing (RED) |
| 3 Player-facing delta | `test_level_up_returns_player_facing_delta_record`; `test_party_member_exposes_advancement_delta_field` | failing (RED) |
| 4 Wiring test fails on develop | `test_level_up_fires_inside_the_real_narration_turn` (drives real `_execute_narration_turn`) | failing (RED) |

### Rule Coverage (python lang-review checklist)

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality (no vacuous asserts) | self-check: every test asserts specific values; no `assert True`/bare truthy | pass (self-check) |
| #6 parametrized cases hit distinct paths | `test_threshold_table_per_level_three` — 7 distinct thresholds, not one path re-run | failing (RED) |
| safety / No Silent Fallbacks (no ZeroDivisionError) | `test_unconfigured_progression_is_level_one_without_crashing`; `test_unconfigured_progression_never_levels` | failing (RED) |
| OTEL Observability Principle (subsystem emits a span) | `test_level_up_*_publishes_state_transition`; turn-wiring OTEL assert | failing (RED) |
| No Source-Text Wiring Tests | wiring test is OTEL-driven through the real turn + a reflection tripwire — no `read_text()`/`inspect.getsource` grep | pass (by construction) |

**Rules checked:** test-quality (#6) + project doctrine (No Silent Fallbacks, OTEL Principle, No Source-Text Wiring Tests). Most python lang-review rules (#1 exceptions, #2 mutable defaults, #5 paths, #7 resources, #8 deserialization, #9 async, #11 input validation) target production code and apply to Dev's GREEN implementation, not the test files.
**Self-check:** 0 vacuous tests found.

**Handoff:** To Dev (Naomi) for implementation. Honor Design Deviations TEA-1/2/3 (or re-log if changing them) and the blocking Conflict finding (xp-vs-milestone reconciliation).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/genre/models/progression.py` — `resolve_level(milestones_completed, config)`: pure milestones→level math (sibling of `resolve_wealth_tier`); clamp to `max_level`, floor at 1, guard unconfigured packs against ZeroDivisionError.
- `sidequest/server/dispatch/encounter_lifecycle.py` — `apply_level_ups(snapshot, progression) -> list[LevelUp]` engine + `_XP_PER_MILESTONE=100`; `LevelUp` aliased from `protocol.AdvancementDelta`. Reads live `core.xp`, bumps `core.level` on a crossing, publishes `progression.level_up` `state_transition` (component=`progression`), records the player delta, resets it each turn.
- `sidequest/server/websocket_session_handler.py` — calls `apply_level_ups(snapshot, sd.genre_pack.progression)` immediately after `award_turn_xp` in `_execute_narration_turn` (the production consumer — AC4 wiring).
- `sidequest/protocol/models.py` — new `AdvancementDelta` (character_name/before/after/driver) + `PartyMember.advancement` optional field.
- `sidequest/game/character.py` — transient `last_advancement` (`exclude=True`, never persisted).
- `sidequest/server/views.py` — `party_member_from_character` surfaces `advancement=character.last_advancement` (player-facing — mirrors the track-3 wealth label).

**Tests:** 14/14 new tests GREEN. Regression sweep clean: 46 (target + xp_award/governance/progression) + 154 (wire-parity/protocol/views/party-status/persistence consumers) passing. Ruff check + format clean on all changed files.

**AC status:** AC1 (math + multi-level + cap + guards) ✓ · AC2 (`progression.level_up` OTEL) ✓ · AC3 (player-facing `PartyMember.advancement`) ✓ · AC4 (engine fires inside real `_execute_narration_turn`, OTEL-driven wiring) ✓.

**Branch:** `feat/82-6-wire-milestone-levelup` (pushed to origin).

**Handoff:** To Reviewer (Chrisjen Avasarala) for code review.

### Delivery Findings (Dev)
- See `### Dev (implementation)` under Delivery Findings above: blocking Conflict resolved (xp-as-accumulator); one non-blocking Improvement (thread per-turn crossings into PARTY_STATUS rather than parking on the character) deferred; TEA's `test_xp_award` source-text-wiring cleanup left for its own story.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; 62 tests GREEN; lint/format failures 100% pre-existing (none in branch files) | N/A — confirms green baseline |
| 2 | reviewer-edge-hunter | Yes | findings | 6 (all low/med) | confirmed 1 (crash-loses-notification, non-blocking), downgraded 1 (seat asymmetry → correct-by-design for sealed rounds), dismissed 1 (None-guard), deferred 3 (max_level=1 test, multi-level OTEL granularity, ownership doc) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 (1 med, 2 low) | confirmed 1 as non-blocking follow-up (half-config validation), dismissed 1 (bare apply_level_ups = intentional fail-loud), dismissed 1 (watcher lossy-by-design, pre-existing) |
| 4 | reviewer-test-analyzer | Yes | findings | 8 (4 high-conf, 2 med, 2 low) | **confirmed 4 as blocking-cluster** (AC3 populate untested, at-max guard untested, reset-between-turns untested, vacuous `driver` assertion), confirmed 2 medium (multi-char, award-driven crossing), 2 low (tautology, dup params) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | 0 | N/A — traced MP broadcast path; `last_advancement` party-visible by ADR-036/037 design, no cross-player leak; XP server-only, no overflow/DoS |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 4 confirmed blocking-cluster (test rigor) + 5 confirmed non-blocking + 4 dismissed (with rationale) + several deferred

## Rule Compliance

Rules enumerated from sidequest-server `CLAUDE.md`, `SOUL.md`, and `.pennyfarthing/gates/lang-review/python.md`. Every changed type/function checked.

- **No Silent Fallbacks** — `resolve_level` returns level 1 only when `milestones_per_level<=0 OR max_level<=0` (genuinely-unconfigured packs, e.g. caverns_and_claudes); level 1 is the authored floor, not a fabricated value. COMPLIANT. (Sub-finding: a *half*-configured pack — one field zero, the other not — is silently treated as unconfigured; no real pack triggers it and the progression schema is out of scope, so non-blocking.)
- **No Stubbing / No half-wired features** — engine + OTEL + player surface + turn-pipeline call site all present; no empty shells. COMPLIANT (production); the player-facing populate is wired (`views.py:519` → broadcast) but its automated test is missing — see Verdict.
- **Verify Wiring, Not Just Existence** — `apply_level_ups` has a non-test consumer at `websocket_session_handler.py:1264`, run every turn after `award_turn_xp`. COMPLIANT for the engine. **AC3 player-facing populate: wired in production but the test only asserts field EXISTENCE (`"advancement" in PartyMember.model_fields`), not that the value is copied — this is exactly the "existence ≠ wiring" trap.** VIOLATION (test rigor).
- **Every Test Suite Needs a Wiring Test** — `test_level_up_fires_inside_the_real_narration_turn` drives the real `_execute_narration_turn` and asserts the OTEL event + level. COMPLIANT for the engine→OTEL path. The player-facing surface lacks its wiring test. PARTIAL.
- **No Source-Text Wiring Tests** — wiring proven via OTEL capture + reflection tripwire (`model_fields`); no `inspect.getsource`/`read_text` grep. COMPLIANT.
- **OTEL Observability Principle** — every crossing emits `progression.level_up` (`component=progression`), mirroring `disposition.shift`/`award_turn_xp`. COMPLIANT.
- **lang-review #2 mutable defaults** — none in changed signatures. COMPLIANT.
- **lang-review #3 type annotations at boundaries** — `resolve_level(int, ProgressionConfig) -> int`, `apply_level_ups(GameSnapshot, ProgressionConfig) -> list[LevelUp]`, `AdvancementDelta` fully typed. COMPLIANT.
- **lang-review #6 test quality (no vacuous assertions)** — `assert delta.driver` (test_levelup_otel_wiring.py:148) is a bare truthy check against a hardcoded `"milestone"` — a *different* string would still pass. VIOLATION. `assert delta.before < delta.after` (line 147) is tautological after pinning `==1`/`==5`. Minor.

## Reviewer Observations

- `[VERIFIED]` Level never decreases — `encounter_lifecycle.py:1386` `if new_level <= before: continue` guards downgrade and re-fire at max. Checked against No-Silent-Fallbacks (no fabricated change). Sound — but the guard itself is **untested** (see `[TEST]` below).
- `[VERIFIED]` `apply_level_ups` runs every turn at the same indentation/gating as `award_turn_xp` (`websocket_session_handler.py:1261/1264`) — correct coupling (you only level from XP you were awarded). The `last_advancement=None` reset is therefore reliable each round.
- `[VERIFIED]` `sd.genre_pack.progression` is always present — `GenrePack.progression: ProgressionConfig` is non-optional (`pack.py:220`), loaded from a required `progression.yaml` (`loader.py:1365`). No `None` crash path at the call site.
- `[VERIFIED]` `last_advancement` is `exclude=True` (`character.py:109`) — not persisted; snapshot field-governance test passes (governance covers GameSnapshot top-level only; sub-field on Character is safe). Transient per-turn semantics correct.
- `[VERIFIED]` No cross-player leak — `[SEC]` confirmed `last_advancement` rides the shared party-status frame consistently with HP/level/status (ADR-036/037), each delta tagged with its own `character_name`/`player_id`.
- `[TEST][HIGH]` AC3 player-facing populate is untested — no test passes a Character with non-None `last_advancement` through `party_member_from_character` and asserts `member.advancement` is populated with the right value. Only field-existence is asserted. The headline mechanics-first deliverable (Sebastien/Jade) is verified only by inspection.
- `[TEST][MEDIUM]` The no-downgrade / at-max-level guard (`<= before`) has no test — a `<=`→`<` regression would emit a phantom level-up at the cap and go uncaught.
- `[TEST][MEDIUM]` The per-turn `last_advancement=None` reset for a character who crossed on a *prior* turn is untested — all no-crossing tests start from `None`.
- `[TEST][LOW]` `assert delta.driver` vacuous (rule #6) → should be `== "milestone"`; `assert delta.before < delta.after` tautological.
- `[EDGE][LOW/non-blocking]` Crash between `apply_level_ups` and the PARTY_STATUS emit drops the one-time notification (level itself is durable). Matches Dev's deferred improvement.
- `[SILENT][LOW/non-blocking]` Half-configured progression (one of `milestones_per_level`/`max_level` zero) is silently treated as unconfigured; no current pack triggers it; progression schema is out of scope.

## Devil's Advocate

Argue this is broken. The implementation *looks* complete — engine, OTEL, a player field, a turn-pipeline call — but the most important promise of this story is AC3: that a **mechanics-first player (Sebastien/Jade) actually sees the level-up and its driver**. What proves that promise? Exactly one assertion: `"advancement" in PartyMember.model_fields`. That proves a field is *declared*. It does not prove a single byte of advancement data ever reaches a player. If a future refactor deletes `advancement=character.last_advancement` from `party_member_from_character` (a one-line removal), every test in this story still passes — the field still exists on the model, the engine still emits OTEL, the level still bumps. The player silently goes back to a stat bump with no explanation, and the suite is green. That is precisely the "winging it" failure mode the project's wiring doctrine ("Verify Wiring, Not Just Existence") was written to catch — and here the *test* commits the existence-≠-wiring error the doctrine names.

A confused content author sets `milestones_per_level: 3` and forgets `max_level`: their players never level, no warning fires, and nothing in the suite would tell them why. A stressed reviewer trusts TEA's "0 vacuous tests found" self-attestation — but `assert delta.driver` is vacuous by rule #6, and the no-downgrade invariant (`<= before`) that protects against phantom max-level spam has zero coverage. The engine is correct *today*; the tests do not defend it tomorrow. The production code is sound, but the test suite under-delivers on the one AC that justifies the story existing. That is enough to send back — cheaply, since no production change is required.

## Reviewer Verdict — Round 1 (REJECTED, superseded by round-trip 1)

**Verdict:** REJECTED — test rigor (no production code change required)

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | AC3 player-facing populate untested — only field existence asserted; the `views.py:519` copy of `last_advancement`→`PartyMember.advancement` has no behavioral test | `tests/server/test_levelup_turn_wiring.py` | Build a Character with `last_advancement` set via a real `apply_level_ups`, pass through `party_member_from_character`, assert `member.advancement.after`/`.driver`. Pattern: `test_reference_url_attach.py`. |
| [MEDIUM] | No-downgrade / at-max-level guard (`<= before`) untested | `tests/integration/test_levelup_otel_wiring.py` | Character at `level=5`, `max_level=5`, huge xp → stays 5, `deltas==[]`, no `progression.level_up` event. |
| [MEDIUM] | Per-turn `last_advancement=None` reset (after a prior-turn crossing) untested | `tests/integration/test_levelup_otel_wiring.py` | Cross once (delta set), run again with no new crossing → assert `last_advancement is None`. |
| [LOW] | Vacuous `assert delta.driver` (rule #6) + tautological `before < after` | `tests/integration/test_levelup_otel_wiring.py:147-148` | `assert delta.driver == "milestone"`; drop the tautology. |
| [LOW] | (optional, same pass) multi-character snapshot + award-driven first-crossing not exercised; dup parametrized cases `(0,1)`/`(2,1)` | `tests/...` | Add a 2-PC test (one crosses, one doesn't); add a just-below-threshold test where the turn's own `award_turn_xp` causes the crossing; dedupe. |

**Production code:** correct and complete — no changes requested. All five ACs are functionally met; the engine, OTEL emission, turn-pipeline wiring, and player-facing populate were verified by inspection and corroborated by the security trace. The rejection is a focused **test-hardening pass** to close a HIGH coverage gap on the headline AC plus a rule-#6 vacuous assertion and two Medium invariant gaps.

**Handoff:** Back to TEA (Amos Burton) for the rework — testable gaps, RED phase.

## TEA Rework (round-trip 1)

**Status:** All reviewer findings closed. Production code UNCHANGED (it was correct); this round adds coverage only.

**Tests added/changed:**
- `tests/server/test_levelup_turn_wiring.py` — `test_party_member_from_character_populates_advancement_after_level_up` (the HIGH fix: real `apply_level_ups` → `Character.last_advancement` → `party_member_from_character` copies it to `PartyMember.advancement`; asserts before/after/driver/character_name). Plus `test_party_member_advancement_is_none_without_a_level_up` (negative).
- `tests/integration/test_levelup_otel_wiring.py` — `test_character_already_at_max_level_does_not_re_level_or_emit` (the `<= before` guard); `test_last_advancement_is_cleared_on_a_later_no_crossing_turn` (per-turn reset); `test_multi_character_snapshot_levels_each_pc_independently` (loop + attribution). Tightened `assert delta.driver == "milestone"` (was a bare truthy — rule #6) and dropped the tautological `before < after`.

**Reviewer findings → resolution:**
- [HIGH] AC3 populate untested → **closed** (behavioral populate + negative tests).
- [MED] at-max no-downgrade guard untested → **closed**.
- [MED] per-turn reset untested → **closed**.
- [MED] multi-character loop untested → **closed**.
- [LOW] vacuous `driver` assertion + tautology → **closed**.
- [LOW] dup parametrized cases `(0,1)`/`(2,1)` → **left as-is**: the table is a deliberate complete boundary walk; the standalone tests document intent. Harmless, no value in churn.
- [non-blocking, deferred] half-config `@model_validator`, watcher lossy-by-design, crash-loses-notification → out of scope / pre-existing / Dev-deferred improvement; not addressed this round.

**Tests:** 25/25 levelup tests GREEN (serial `-n0`). Ruff clean. Branch pushed (`4ddb284`).

**Handoff:** To Dev (Naomi) for GREEN confirmation — no implementation needed (production code already correct); verify suite green and pass to Reviewer.

## Dev GREEN Confirmation (round-trip 1)

**No production change** — TEA's rework was coverage-only and the implementation was already correct. Verified GREEN: 79 passed / 0 failed / 41 skipped across the levelup suite + PartyMember/protocol/views/wire-parity/reference-url/xp-award/snapshot-governance regression set (serial `-n0`). Ruff clean on both edited test files. Working tree clean; branch `feat/82-6-wire-milestone-levelup` at `4ddb284` (pushed).

**Design deviations (Dev):** No new deviations this round — no code changed.

**Handoff:** To Reviewer (Chrisjen Avasarala) for re-review of the closed findings.

## Reviewer Re-Review (round-trip 1)

Scope: the rework commit `4ddb284` is **test-only** (verified via `git show --name-only` — zero production `.py` files). Production code is byte-identical to round 1, where every production-code specialist returned clean/non-blocking and I verified the engine, OTEL, wiring, and player populate by inspection (corroborated by the security trace). This re-review focuses on the test delta.

### Subagent Results (re-review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 59 passed/0 failed, ruff clean, 0 smells; independently re-verified the call site at `websocket_session_handler.py:1259` | N/A — green baseline confirmed |
| 2 | reviewer-edge-hunter | Yes (round 1) | findings | carried — production code byte-identical (test-only commit) | round-1 findings stand: all low/med, none blocking |
| 3 | reviewer-silent-failure-hunter | Yes (round 1) | findings | carried — production unchanged | round-1: none blocking |
| 4 | reviewer-test-analyzer | Yes | findings | re-ran on the test delta: **all 5 prior findings CLOSED**; 1 new LOW nit | confirmed closures; new nit non-blocking |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes (round 1) | clean | carried — production unchanged | round-1: clean (no MP cross-leak, XP server-only) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (preflight + test-analyzer fresh this round; production-code specialists carried from round 1 — inputs verified unchanged; 4 disabled)
**Total findings:** prior blocking-cluster all CLOSED; 1 new LOW nit (non-blocking)

### Findings-closure verdict (test-analyzer + my own read)

- **[HIGH] AC3 populate** → ✓ CLOSED. `test_party_member_from_character_populates_advancement_after_level_up` drives the **real** `apply_level_ups` (not a manual set) → real `party_member_from_character` → asserts `member.advancement.{before=1,after=5,driver="milestone",character_name="Rux"}`. A regression dropping `views.py` line 519 fails here; the reflection test alone would not. Independently verified by me (read lines 137-211). Plus a sound negative.
- **[MED] at-max no-downgrade guard** → ✓ CLOSED. `test_character_already_at_max_level_does_not_re_level_or_emit` — level unchanged, `deltas==[]`, no event; catches a `<=`→`<` regression via `deltas==[]`.
- **[MED] per-turn reset** → ✓ CLOSED. `test_last_advancement_is_cleared_on_a_later_no_crossing_turn` — cross then no-cross → `last_advancement is None`.
- **[MED] multi-character loop** → ✓ CLOSED. `test_multi_character_snapshot_levels_each_pc_independently` — only crosser levels/emits, correct attribution, exactly one event.
- **[LOW] vacuous `driver` assert** → ✓ CLOSED. Now `== "milestone"`; tautology removed.

### New finding (this round)

- `[TEST][LOW, non-blocking]` `test_levelup_turn_wiring.py:258` — the pre-condition `assert character.last_advancement is None` checks the Pydantic constructor default before any call; it can't fail in a regression. The load-bearing assertion (`member.advancement is None`, line ~283) is genuine, so the test is valid — this is a redundant readability guard, not a vacuous test. Recommend trimming on the next touch; **does not block** (Reviewer is read-only; not worth a round-trip).

### Devil's Advocate (re-review)

Can I still argue it's broken? The production code is unchanged and was sound in round 1; the only attack surface is the new tests. The HIGH fix could be a fake if it set `last_advancement` by hand and asserted the copy — but it drives the real engine, so it genuinely exercises views.py. The negative test could be a fake if it relied on the engine NOT running and thus proved nothing about the populate — but its load-bearing assertion (`member.advancement is None` after a real `party_member_from_character` build) is exactly the populate path with a None input, which is meaningful. The worst I can find is one redundant pre-condition assert (LOW). No basis to block.

### Deviation Audit (re-review)

No new deviations logged this round (Dev/TEA both recorded "no new deviations — coverage only"). The round-1 stamps stand: TEA-1/2/3 and Dev's `_XP_PER_MILESTONE` all ✓ ACCEPTED. Re-affirmed.

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** turn outcomes → `award_turn_xp` accrues `core.xp` → `apply_level_ups` (post-award, `websocket_session_handler.py:1259`) → `resolve_level` math → `core.level` bump + `progression.level_up` OTEL (GM panel) + `Character.last_advancement` → `party_member_from_character` → `PartyMember.advancement` (player). Both the dev/GM channel and the player channel are exercised by tests.
**Pattern observed:** mirrors the track-3 `resolve_wealth_tier` precedent (pure resolver + player-facing label on PartyMember + OTEL) at `views.py` / `progression.py` — consistent with the established progression idiom.
**Error handling:** unconfigured/half-config packs resolve to floor level 1 (No Silent Fallbacks — authored floor, not fabrication); negative xp guarded by `max(0, …)`; division guarded by the `milestones_per_level<=0` check; level never decreases (`<= before`).
**Tests:** 59 passed / 0 failed (re-review preflight), ruff clean; all 4 ACs covered including the AC3 player-facing populate behavioral chain.
**Outstanding (non-blocking, follow-ups):** redundant pre-condition assert (LOW); half-config `@model_validator` (Improvement, progression-schema scope); per-turn delta threaded directly into PARTY_STATUS instead of parked on the character (Dev's deferred improvement); migrate `test_xp_award`'s source-text wiring test (TEA's flagged cleanup).

**Incorporated specialist findings (all enabled subagents):**
- `[TEST]` — All 5 round-1 test-rigor findings CLOSED (AC3 populate behavioral chain, at-max guard, per-turn reset, multi-character loop, vacuous `driver` assert). 1 new LOW non-blocking nit (redundant pre-condition assert, `test_levelup_turn_wiring.py:258`). Confirmed.
- `[EDGE]` — Round-1 findings stand (production byte-identical): crash-between-apply-and-emit drops the one-time notification (level durable) — non-blocking; seat asymmetry → correct-by-design for sealed-round merged-dispatch; max_level=1 / multi-level OTEL granularity / None-guard → deferred or dismissed. No blocker.
- `[SILENT]` — Round-1 findings stand: bare `apply_level_ups` = intentional fail-loud (No Silent Fallbacks) — dismissed; half-config silent-treat → non-blocking follow-up; watcher lossy-by-design → pre-existing, out of scope. No blocker.
- `[SEC]` — Round-1 CLEAN: `progression.level_up` payload carries no sensitive data; `last_advancement` is party-visible by ADR-036/037 design with correct per-character attribution (no cross-player leak); XP server-awarded only (no overflow/DoS).

**Handoff:** To SM (Camina Drummer) for finish-story.