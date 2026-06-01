---
story_id: "71-24"
jira_key: ""
epic: "71"
workflow: "tdd"
---
# Story 71-24: perseus_cloud personal-melee combat beat bank — distinct from ship/dogfight beats

## Story Details
- **ID:** 71-24
- **Jira Key:** (Not applicable — no Jira integration for this project)
- **Workflow:** tdd
- **Epic:** 71 — Playtest bugfix — uncovered findings (coyote_star MP, 2026-05-27)
- **Type:** bug
- **Priority:** p2
- **Points:** 3
- **Stack Parent:** none
- **Repos:** sidequest-content

## Story Context

**Finding:** space_opera/perseus_cloud world has ship/dogfight combat beats (ship_combat confrontation type in rules.yaml) but NO ground/personal-melee beat bank. During playtest, when combat moved to planets or interior spaces, the engine had no melee beats to draw from — personal combat defaulted to the generic Firefight beats (shoot, take_cover, overload, retreat) instead of world-specific melee choices.

**Mechanical Gap:** The space_opera ruleset supports multiple confrontation types. Firefight (blaster-based) is genre-wide; ship_combat (dogfight) is genre-wide. Perseus_cloud needs a **personal-melee** confrontation type with distinct beats reflecting the physical combat aesthetic of that world — e.g. pulse-blade, armor-brace, evasive_parry, disengage — distinct from blaster standoffs.

**Content Authoring Task:** Author a personal-melee beat bank in sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/ with the same mechanical structure as the genre-level ship_combat and Firefight beats, wired so the intent router recognizes melee-flavored actions (slash, parry, thrust, dodge) and routes them to personal-melee confrontation rather than Firefight.

## Technical Approach

### Mechanical Model
- **Confrontation Type:** `personal_melee` (new world-level override, paralleling genre-level ship_combat/Firefight)
- **Resolution Mode:** beat_selection (hp_depletion, same as Firefight)
- **Beat Structure:** Four beats mirroring the Firefight archetype:
  - **Strike beat:** High-damage melee attack (pulse-blade slash, or equivalent)
  - **Brace beat:** Defensive stance / armor-absorb damage reduction
  - **Angle beat:** Positioning / setup for advantage (e.g. "expose weak point")
  - **Push beat:** Retreat / disengage from melee range

### Implementation Scope
1. Create `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/rules.yaml` (world-level override)
2. Define `personal_melee` confrontation type with beats, stat checks (Physique/Resolve/Reflex/Cunning), intent verbs matching melee flavor, and mechanics mirroring Firefight HP/AC/damage
3. Wire intent verbs (slash, parry, dodge, thrust, etc.) to personal_melee intent router
4. Validate YAML against confrontation schema (pf validate)
5. Write wiring test: mock narrator intent routing to melee action → personal_melee confrontation instantiates (not Firefight)

### Acceptance Criteria
1. **YAML Authorship:** `worlds/perseus_cloud/rules.yaml` defines `personal_melee` confrontation with four beats (strike/brace/angle/push), stat checks, intent verbs, and hp_depletion resolution
2. **Mechanical Completeness:** beats include damage_override/damage_channel (strike), stat_check (all), narrator_hint, effect/risk/consequence (all), and kind classification (strike/brace/angle/push)
3. **Intent Routing:** melee intent verbs (slash, parry, dodge, thrust, blade, block) resolve to personal_melee, not Firefight (behavioral assertion)
4. **Stat Calibration:** opponent_default_stats (HP, AC, damage) match Firefight baseline (hp: 7, armor_class: 12, 1d6 damage) — no separate balancing pass needed for this sprint
5. **Schema Validation:** `pf validate genus:world genre:space_opera world:perseus_cloud` passes with no ERROR-level gaps; YAML loads cleanly through live loader
6. **Wiring Test:** Exercise real router path — mock PC action ("I slash with my blade") → narrator intent classification → personal_melee confrontation seat + beat bank instantiate (no Firefight seat)
7. **OTEL:** personal_melee confrontation instantiation emits SPAN_CONFRONTATION_CREATED with confrontation_type=personal_melee so GM panel confirms the melee engine is engaged

### Definition References
- **Firefight beats** (genre-level): `genre_packs/space_opera/rules.yaml` lines 321-410
- **Ship_combat beats** (genre-level): `genre_packs/space_opera/rules.yaml` lines 221-319
- **ADR-033** (Confrontation Engine): docs/adr/033-genre-mechanics-engine-confrontations-resource-pools.md
- **ADR-117** (Pluggable Ruleset Module System): docs/adr/117-pluggable-ruleset-module-system.md
- **ADR-120** (Genre/World Flavor Boundary): docs/adr/120-genre-world-flavor-boundary-mandatory-file-loader-contract.md

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-01T04:25:16Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-31 | 2026-06-01T03:42:56Z | 27h 42m |
| red | 2026-06-01T03:42:56Z | 2026-06-01T03:51:59Z | 9m 3s |
| green | 2026-06-01T03:51:59Z | 2026-06-01T04:05:51Z | 13m 52s |
| spec-check | 2026-06-01T04:05:51Z | 2026-06-01T04:08:02Z | 2m 11s |
| verify | 2026-06-01T04:08:02Z | 2026-06-01T04:13:23Z | 5m 21s |
| review | 2026-06-01T04:13:23Z | 2026-06-01T04:23:47Z | 10m 24s |
| spec-reconcile | 2026-06-01T04:23:47Z | 2026-06-01T04:25:16Z | 1m 29s |
| finish | 2026-06-01T04:25:16Z | - | - |

## Sm Assessment

**Decision:** Confirm — proceed to RED phase under tdd workflow.

**Rationale:** Story 71-24 is a content-authoring bug in `sidequest-content` (perseus_cloud has ship/dogfight beats but no personal-melee beat bank). Scope is bounded and well-understood: author a world-level `personal_melee` confrontation beat bank mirroring the genre-level Firefight archetype, wired so the intent router recognizes melee verbs. ACs 1–7 are written with concrete mechanical targets and reference definitions (Firefight beats at `genre_packs/space_opera/rules.yaml:321-410`). The wiring test (AC6) and OTEL emission (AC7) satisfy the project's "Every Test Suite Needs a Wiring Test" and OTEL observability principles.

**Jira:** Explicitly skipped — no Jira integration for this project.

**Branch:** `feat/71-24-perseus-cloud-melee-beats` created on `sidequest-content` (gitflow, branched from develop).

**Routing:** tdd is phased. Next phase = RED, owned by tea (Hamlet) — author failing tests covering schema validation, melee-vs-Firefight intent routing, beat instantiation, and OTEL span emission.

## TEA Assessment

**Tests Required:** Yes
**Phase:** finish

**Test Files:**
- `sidequest-server/tests/server/test_space_opera_melee_e2e.py` — 5 tests pinning the
  `melee` confrontation bank contract. Mirrors the canonical sibling
  `test_space_opera_swn_combat_e2e.py` (real-pack seating + dice + OTEL).

**Tests Written:** 5 tests covering 2 ACs (AC1 distinct melee bank + verb reroute;
AC2 production-path hp_depletion resolution with OTEL + ranged regression guard).
**Status:** RED — `4 failed, 1 passed` (the 1 pass is the regression guard, green by
design; it protects existing ranged matching). Verified via `testing-runner`
(RUN_ID `71-24-tea-red`): no collection/import errors, no skips, all 4 failures are
meaningful (`melee` type unauthored → AssertionError / `ValueError: unknown
encounter_type 'melee'` from the fail-loud seating path).

| AC | Test | Status |
|----|------|--------|
| AC1 (distinct bank) | `test_melee_def_is_combat_hp_depletion_with_distinct_beats` | failing |
| AC1 (verb reroute, mapping) | `test_melee_verbs_route_to_melee_not_firefight_in_mapping` | failing |
| AC1 (verb reroute, real match path) | `test_melee_action_matches_melee_via_real_validator` | failing |
| AC2 (hp_depletion + OTEL wiring) | `test_melee_resolves_on_hp_depletion_with_otel` | failing |
| AC2 (ranged regression) | `test_ranged_shoot_still_routes_to_combat_after_melee_reroute` | passing (guard) |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| OTEL Observability (every subsystem decision emits a span) | `test_melee_resolves_on_hp_depletion_with_otel` asserts `encounter.confrontation_initiated`, `encounter.beat_applied`, `encounter.resolved(source=hp_depletion)` | failing |
| Every Test Suite Needs a Wiring Test | `test_melee_resolves_on_hp_depletion_with_otel` drives the real `instantiate_encounter_from_trigger` + `dispatch_dice_throw` path end-to-end | failing |
| No Source-Text Wiring Tests (sidequest-server) | All wiring proven via OTEL span-capture (`otel_capture`) + behavioral resolution, never `read_text()`/grep | n/a (compliant by construction) |
| No Silent Fallbacks | Lookup uses production `find_confrontation_def` (exact match, no fuzzy); the seating ValueError on unknown type is asserted-compatible (fail loud) | failing |

**Rules checked:** OTEL + wiring + no-source-text + no-silent-fallback (the applicable
SOUL/CLAUDE.md rules for a content-mechanics story; no lang-review/{language}.md
numbered checklist applies to a YAML content addition).
**Self-check:** 0 vacuous tests. Every assertion checks a value or a span attribute;
no `assert True` / bare `is_some()` / `let _ =` equivalents.

**Handoff:** To Dev (Puck) for the green phase — author the `melee` bank in
`sidequest-content/genre_packs/space_opera/rules.yaml` (and any class
`encounter_beat_choices`/`class_filter` wiring) until all 5 tests pass.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 5/5 passing (GREEN); space_opera combat + intent + pack-load regression
suites clean (24 passed total). Verified via `testing-runner` (RUN_ID
`71-24-dev-green-2`, read-only re-run after a clean inventory edit).

**Files Changed (sidequest-content, branch `feat/71-24-perseus-cloud-melee-beats`, pushed):**
- `genre_packs/space_opera/rules.yaml` — added the `melee` confrontation type
  (category combat / beat_selection / hp_depletion) with 4 beats — `slash` (strike,
  weapon-derived), `parry` (brace), `overhand` (strike, 2d6 override + fail-momentum,
  mirrors Firefight `overload`), `withdraw` (push/resolution, voluntary exit);
  `opponent_default_stats` hp 7 / AC 12 / dex 13 + `opponent_damage` 1d6 (Firefight
  baseline). Removed melee verbs (strike/swing/stab) from `combat` (Firefight)
  `intent_verbs` and seated the full melee verb set on `melee`.
- `genre_packs/space_opera/inventory.yaml` — added `vibroblade` weapon (damage 1d6);
  gave pre-existing melee weapons `vibroknife` (1d4+1) and `stun_baton` (1d6) damage
  specs so the bank's weapon-derived strike ablates real HP. Surgical additions
  (+21 lines), comments/formatting preserved.

**Files Changed (sidequest-server):** none by Dev — TEA's test commit (88ac712d) on
the matching `feat/71-24-perseus-cloud-melee-beats` branch is pushed for the PR.

**Wiring proof:** melee beats are universal (`class_filter` omitted) → beat_filter
Gate 1 surfaces them to all 8 allowed classes (verified in `beat_filter.py`); the
production seating+dice path resolves hp_depletion and fires
`encounter.confrontation_initiated` (type=melee), `encounter.beat_applied` (melee
beat_id), and `encounter.resolved` (source=hp_depletion) — asserted by the e2e test.

**Self-review:** ✅ wired end-to-end (not just defined); ✅ follows the Firefight
pattern; ✅ ACs met (distinct bank + reroute + hp_depletion + OTEL + ranged
regression); ✅ error handling = the engine's existing fail-loud paths (unknown
type ValueError, loader cross-ref PackError) — no new silent fallbacks introduced.

**Handoff:** To Architect (Oberon) for the spec-check phase.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — all drift is against the *auto-generated* session
ACs (1-7), and every mismatch resolves **toward** the authoritative story context
(`context-story-71-24.md`) + SOUL doctrine. The implementation is architecturally
sound. Gate `spec_check`: PASS (assessment found, impl complete, TEA+Dev deviations
logged). Substantive read of the authored `melee` block confirms it against the
context's AC1/AC2.

**Mismatches Found:** 3 (all against the haiku-generated session ACs, not the context)

- **Type id + tier: `personal_melee`/world-tier (session AC1) vs `melee`/genre-tier (code)** (Different behavior — Architectural, Major)
  - Spec (session AC1): "`worlds/perseus_cloud/rules.yaml` defines `personal_melee`"
  - Code: `melee` authored in `genre_packs/space_opera/rules.yaml` (genre tier)
  - Recommendation: **A — Update spec.** Genre-tier is the architecturally correct
    home for personal-combat crunch (ADR-120 + SOUL "Crunch in the Genre"); the
    sibling types `combat`/`ship_combat`/`dogfight` are all short, unprefixed,
    genre-tier. A world override would fragment a genre mechanic and deny it to
    `coyote_star`/`aureate_span`. The session ACs were sm-setup-generated and
    contradicted the authoritative context; TEA flagged the Conflict, Dev resolved
    it correctly. Already logged as a Dev deviation. **Confirmed.**

- **No `angle` beat (session AC2 listed strike/brace/angle/push)** (Missing in code — Behavioral, Trivial)
  - Spec (session AC2): "kind classification (strike/brace/angle/push)"
  - Code: beats are strike (slash, overhand) / brace (parry) / push (withdraw) — no angle
  - Recommendation: **A — Update spec.** The four-kind list was illustrative of the
    `BeatKind` enum, not a per-bank requirement. Firefight (the pattern being mirrored)
    has no angle beat either. TEA's tests require kinds ⊆ {strike,brace,angle,push}
    with strike+brace present — satisfied. Not a real gap.

- **OTEL span name: `SPAN_CONFRONTATION_CREATED` (session AC7) vs `encounter.confrontation_initiated` (code)** (Ambiguous spec — Cosmetic, Trivial)
  - Spec (session AC7): "emits SPAN_CONFRONTATION_CREATED"
  - Code: fires the real `encounter.confrontation_initiated` span (type=melee)
  - Recommendation: **A — Update spec.** `SPAN_CONFRONTATION_CREATED` is not a real
    constant; the implementation/tests use the actual tested span. Spec naming error.

**Architectural notes (no action):**
- No ADR warranted — pure reuse of the Firefight pattern (ADR-033 confrontation
  engine, ADR-114 ablative HP) at the genre tier (ADR-120). No new pattern introduced.
- Genre-tier placement means `coyote_star`/`aureate_span` inherit melee too —
  desirable and verified (the `test_world_loads_clean_under_swn` parametrized suite
  for both worlds is green).
- The verb reroute (strike/swing/stab off `combat`) is behaviorally validated by the
  ranged-`shoot`→`combat` regression test; no other consumer depends on those verbs
  living on `combat`.
- The pre-existing perseus_cloud world-file gaps (Dev's Gap finding) are out of scope
  for this genre-tier mechanics story and correctly deferred.

**Decision:** Proceed to review. No hand-back to Dev — all mismatches are spec-side
drift (Option A), the code matches the authoritative design.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (no implementation change in verify; melee suite + regression remain green)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`space_opera/rules.yaml`, `space_opera/inventory.yaml`,
`tests/server/test_space_opera_melee_e2e.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 high + 1 med + 2 low | Test-helper duplication vs `test_space_opera_swn_combat_e2e.py`; 2 low = intentional YAML pattern-mirroring (no action) |
| simplify-quality | clean | Naming/consistency aligns with sibling confrontation banks; no vacuous test assertions |
| simplify-efficiency | clean | Melee bank mirrors Firefight (4 beats), not over-engineered; test complexity is load-bearing wiring |

**Applied:** 1 — `ruff format` on the changed test file (`test_space_opera_melee_e2e.py`),
cosmetic line-wrapping only, committed `0a3020fc` on the server branch; 5 tests
re-verified green after. (Found via `ruff format --check` this phase — the file had
two over-long comprehensions ruff rewraps.)
**Flagged for Review:** 0 medium.
**Noted / Declined with rationale:** the 5 "high" reuse findings + 1 medium.

**Why the reuse extraction was NOT applied (TEA judgment):** The findings are real —
`test_space_opera_melee_e2e.py` mirrors helpers (`_enum_val`, `_load_space_opera`,
`_has_real_content`, `_player_character`, `_seated_*`, `_throw`, `_spans_named`) from
the sibling `test_space_opera_swn_combat_e2e.py`. But genuinely de-duplicating
requires (a) creating a shared `tests/_helpers/space_opera_e2e_fixtures.py` AND
(b) refactoring the **pre-existing, passing** combat e2e test to import it — a file
**outside story 71-24's footprint**, with real regression risk to a load-bearing
suite, right before review. Importing a shared module into only the new file would
not remove the duplication (the combat file would keep its copies) — a pointless
half-measure. Moreover, self-contained e2e modules that wire the production path
directly are this suite's **established convention** (the combat file is the
canonical reference TEA was instructed to mirror in the red phase). Extracting
shared fixtures is a legitimate but separate test-infra refactor; doing it here would
be scope creep that expands the blast radius. The 2 low YAML findings are intentional
pattern-parity (melee mirrors Firefight per "Crunch in the Genre") — correctly no-action.

**Overall:** simplify: clean (1 real reuse observation deferred to a follow-up, logged below)

**Quality Checks:** melee e2e (5) + space_opera combat/intent/pack-load regression
green; `ruff check` + `ruff format --check` both clean on the changed test file after
the format fix above (verified this phase). Content YAML loads clean through
`load_genre_pack`.

**Handoff:** To Reviewer (Portia) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (tests GREEN, lint clean, 0 smells) | 1 note (pre-existing, OOS) | confirmed 0, dismissed 1 (out of scope), deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 6 (5 med, 1 low) | confirmed 6 as non-blocking test-hardening, dismissed 0, deferred 6 to follow-up |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 (high-confidence, low-severity) | confirmed 3, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 (all low) | confirmed 0 (3 exempt private-helpers, 2 contextually-safe truthy), dismissed 5 with rationale; all critical rules A1–A6 PASS |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 0 confirmed blocking; 9 confirmed non-blocking (3 doc + 6 test-hardening); 6 dismissed (1 preflight OOS + 5 rule-checker low/exempt)

**Preflight accuracy note (my own verification):** preflight's narrative "diff summary"
was INACCURATE — it described pre-existing pack content (ship_combat hp_depletion,
`multifocal_laser`, `broadside` damage_channel) as if it were this branch's diff. I
verified directly (`git diff develop...HEAD`): the real diff is ONLY the melee block +
the combat-verb edit (rules.yaml) and three inventory additions (vibroblade + vibroknife/
stun_baton damage). The `multifocal_laser`/`ship_combat` strings the preflight saw are
pre-existing context lines + my own melee-block comment text. Preflight's *result*
(tests GREEN, lint clean, 0 smells) is correct and matches my own runs. Its flagged
`multifocal_laser armor_piercing` item is pre-existing content, not touched here — out
of scope, dismissed.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** A player action ("I swing my vibroblade and stab the corsair")
→ `confrontation_intent_validator.validate` tokenizes + scores overlap against
`intent_verb_set` per type → melee verbs now live on `melee` (removed from `combat`) →
`matched_type == "melee"` → dispatch resolves `find_confrontation_def(..., "melee")`
(exact match, no fuzzy fallback) → `instantiate_encounter_from_trigger` seats the
opponent with content-authored hp 7 / AC 12 / dex 13 → `dispatch_dice_throw` rolls the
strike vs the authored AC, ablates HP via the SWN strike `damage_channel`, resolves on
0 HP (`source=hp_depletion`). Safe: the path reuses the proven Firefight/SWN engine; the
melee bank only supplies content. Verified by the green e2e test driving this exact flow.

**Observations (≥5):**
1. `[VERIFIED]` Melee beats are universal (`class_filter` omitted) → surfaced to all 8
   classes — evidence: `beat_filter.py` `if beat.class_filter is None: pool.append(beat)`
   (Gate 1). Not half-wired; reachable in real play, not just tests.
2. `[VERIFIED]` Verb reroute is complete and non-regressing — evidence: rules.yaml diff
   shows `combat` intent_verbs now `[attack, fight, kill, slay, shoot, hit]` (swing/stab/
   strike removed), melee carries them; `test_ranged_shoot_still_routes_to_combat` green
   proves ranged matching intact.
3. `[VERIFIED]` Genre-tier placement is correct and consistent with `combat`/`ship_combat`/
   `dogfight` (all genre-tier) per ADR-120 "Crunch in the Genre" — evidence: melee authored
   in `genre_packs/space_opera/rules.yaml`, no `worlds/perseus_cloud` override. Confirmed by
   rule-checker A6.
4. `[VERIFIED]` Combat+hp_depletion opponent seed present (hp 7 / armor_class 12 /
   dexterity 13) — the loader's cross-field validator (`rules.py` ~528-565) requires all
   three or raises `PackError`; pack loads clean (preflight + pack-load tests green).
5. `[MEDIUM][DOC]` 3 stale/misleading comments (confirmed below) — `inventory.yaml:48`
   "AC4 calib" (means AC4 the *acceptance criterion*, reads as armor_class 4 — the melee AC
   is 12); test docstring `:1` "(RED)" label now GREEN on merge; test docstring `:18` cites
   "slay" as a rerouted verb (it stayed on `combat`) with a stale `rules.yaml:324` anchor.
6. `[LOW][TEST]` 6 test-hardening gaps (test-analyzer) — no miss-path (`face=[1]`) round-
   trip; opponent-reprisal (71-21) not exercised for melee; validator only tested with
   `declared_confrontation=None` (not the realistic `="combat"` mismatch case); beat-id
   non-empty/uniqueness not asserted; `source='dice_throw_beat'`-absence not asserted;
   regression `combat_ids` empty-set fragility. All non-blocking — see Devil's Advocate.
7. `[LOW]` Verb tie-break risk: a mixed action ("I attack and stab") overlaps `combat`
   (attack) and `melee` (stab) 1-1; ties resolve by pack-declaration order, and `combat`
   precedes `melee`, so a borderline-melee action with a generic verb routes to Firefight.
   Inherent to the overlap design; the narrator/IntentRouter also selects type. Noted, not
   blocking.
8. `[RULE]` rule-checker: 5 Low findings, all dismissed with rationale (see Rule Compliance) —
   3× missing return-type annotations on `_load_space_opera`/`_melee_def`/`_player_character`
   are private-helper-exempt per lang-review #3 and match the sibling file's convention; 2×
   truthy guards (`assert melee.beats` :235, `assert melee_beat_spans` :375) precede/wrap
   specific-value assertions and are not vacuous. Critical project rules A1–A6 (no silent
   fallbacks, no stubbing, no source-text wiring, wiring test present, OTEL coverage,
   genre-tier placement) all PASS. No rule violation blocks.

### Rule Compliance

Exhaustive check (corroborated by rule-checker A1–A6 + my own read):
- **No Silent Fallbacks** — COMPLIANT. `_load_space_opera` catches `PackNotFound` → explicit
  `pytest.skip` (no silent pass); melee seeds hp/ac/dex explicitly (comment "no silent +0");
  the dispatch lookup is exact-match, no fuzzy fallback.
- **No Stubbing** — COMPLIANT. All 4 beats fully specified; no placeholder/TBD/0-damage-
  without-reason beats; tests have real assertions.
- **No Source-Text Wiring Tests** — COMPLIANT. All 5 tests assert on loaded runtime objects
  / `validate()` results / OTEL span-capture; zero `read_text()`/grep-of-source.
- **Every Test Suite Needs a Wiring Test** — COMPLIANT. `test_melee_resolves_on_hp_depletion_with_otel`
  drives the real seating + dice path and asserts production-emitted spans.
- **OTEL Observability** — COMPLIANT. `encounter.confrontation_initiated` (type=melee),
  `encounter.beat_applied` (melee beat_id), `encounter.resolved` (source=hp_depletion) all asserted.
- **Crunch in the Genre / Flavor in the World (ADR-120)** — COMPLIANT. Mechanics at genre tier;
  no world override; siblings consistent.
- **Type annotations on test helpers (lang-review #3)** — 3 private helpers unannotated, but the
  checklist EXEMPTS private helpers and the sibling `test_space_opera_swn_combat_e2e.py` follows
  the identical convention. Not a violation; repo-consistent. Dismissed.
- **Test quality / no vacuous assertions (lang-review #6)** — `assert melee.beats` and
  `assert melee_beat_spans` are truthy guards, but each precedes/wraps specific-value assertions
  (kinds, ids, span attributes). Not vacuous. Dismissed as contextually-safe.

### Devil's Advocate

Argue this is broken. **First attack vector — the miss path is never tested.** Every
`_throw` uses `face=[20]`, a guaranteed hit. The test asserts `request.difficulty ==
opponent.armor_class`, proving the difficulty is *set* to AC — but it never fires a roll
*below* AC to prove a miss leaves HP intact. A regression that ignored AC entirely (always
hit) would pass every assertion. **Counter:** the AC-gating and miss resolution are ENGINE
behavior (SWN module), shared byte-for-byte with the Firefight bank whose e2e test exercises
the same path; the melee content only declares `damage_channel: strike` + the AC seed. A
miss-path bug would be an engine regression caught by the SWN suite, not a melee-content
defect. For a content story, proving the bank routes to the AC-gated engine path (which the
difficulty assertion does) is sufficient. **Second vector — players can never lose.** The
opponent reprisal (71-21) is never exercised in melee; if melee bound the `native` ruleset
instead of `swn`, no enemy turn would fire and the player would be invincible. **Counter:**
melee is genre-tier under the `space_opera` pack which binds `ruleset: swn` at the pack
level (rules.yaml:11) — every confrontation in the pack, melee included, resolves through
swn; there is no per-confrontation ruleset override, so melee cannot diverge from combat
here. **Third vector — verb tie-break.** "I attack and stab" ties combat/melee 1-1 and
resolves to combat (earlier declaration), pulling a melee action into Firefight. **Counter:**
real, but inherent to the overlap design and mitigated by the narrator/IntentRouter type
selection; it degrades to the *old* behavior (Firefight), not a crash — a Low edge, not a
break. **Fourth — a blank/duplicate beat id would slip the distinctness check.** True, but
the authored beats have distinct non-empty ids (slash/parry/overhand/withdraw), verified by
eye and by the passing distinctness assertion. No break found that rises above Low. The
implementation is sound; the gaps are test-coverage paranoia and three cosmetic comment
typos.

**Pattern observed:** Faithful mirror of the Firefight bank (strike/brace/strike/push →
slash/parry/overhand/withdraw) at `genre_packs/space_opera/rules.yaml` — correct reuse, not
duplication-to-extract.

**Error handling:** Reuses the engine's fail-loud paths — unknown type → `ValueError`
(dispatch), missing opponent seed → `PackError` at load (`rules.py:528-565`). No new silent
paths. Verified `inventory.yaml` damage additions prevent the 0-damage silent failure the
comments call out.

**Handoff:** To SM for finish-story. The 3 doc comments + 6 test-hardening items are
non-blocking delivery findings below — recommend the 3 trivial comment fixes be folded in
before/at merge (they are Low but genuinely misleading).

## Delivery Findings

**Agents record upstream observations discovered during their phase.**

No upstream findings at setup phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (blocking — Dev must reconcile before authoring): The session
  **Technical Approach + ACs 1-7** name the type `personal_melee` authored at a
  **world tier** (`worlds/perseus_cloud/rules.yaml`). The **story context**
  (`context-story-71-24.md`, Technical Guardrails / Assumptions) argues the
  opposite and with explicit reasoning: type id `melee` (the "e.g.") authored at
  the **genre tier** (`genre_packs/space_opera/rules.yaml`), because
  "personal-melee crunch is mechanics → belongs in the GENRE rules.yaml" (SOUL:
  *Crunch in the Genre*), inherited by perseus_cloud and the other space_opera
  worlds, with **no per-world override**. The existing sibling types (`combat`,
  `ship_combat`, `dogfight`) are all short, unprefixed, genre-tier — so `melee`
  at genre tier matches both the convention and the context. **My tests anchor on
  `confrontation_type == "melee"` (the `_MELEE_TYPE` constant) and are tier-agnostic**
  (they load the merged pack via `load_genre_pack`, so genre- or world-tier
  authoring both satisfy them). **Resolution for Dev:** author the type as `melee`
  at the genre tier (recommended — follows context + doctrine + naming convention);
  if you instead author `personal_melee`, change `_MELEE_TYPE` in the test file in
  the same commit so tests and YAML agree. Either way, the green phase resolves the
  `melee`-vs-`personal_melee` divergence in ONE place. Affects
  `genre_packs/space_opera/rules.yaml` + `tests/server/test_space_opera_melee_e2e.py`.
  *Found by TEA during test design.*
- **Gap** (non-blocking): Story is scoped `repos: sidequest-content`, but the TDD
  tests are Python and live in `sidequest-server` (they exercise the loader,
  `intent_verbs_by_type`, `confrontation_intent_validator.validate`, and the
  `instantiate_encounter_from_trigger` / `dispatch_dice_throw` seating+resolution
  path — all server-side). This story therefore spans TWO repos: the failing
  tests committed to `sidequest-server` (branch `feat/71-24-perseus-cloud-melee-beats`,
  commit 88ac712d) and the YAML the green phase authors in `sidequest-content`
  (branch already created there). Affects sprint bookkeeping + finish: Dev should
  expect to commit content YAML in `sidequest-content` while the tests verify from
  `sidequest-server`, and SM-finish will need to handle PRs in BOTH repos. *Found
  by TEA during test design.*
- **Improvement** (non-blocking): The melee push/exit ("Fall Back" equivalent with
  `resolution: true`) is NOT pinned by these tests — voluntary mid-combat exit is
  the subject of the sibling soft-lock story (73-2). Firefight's `retreat` beat
  models the pattern (`rules.yaml:398`, `resolution: true`). Dev may author a melee
  push/disengage beat for parity; the tests assert kinds ⊆ {strike,brace,angle,push}
  so a push beat is allowed but not required. Affects
  `genre_packs/space_opera/rules.yaml` (melee bank). *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): `pf validate pack space_opera` reports 4 ERRORs, all
  pre-existing perseus_cloud WORLD-completeness gaps unrelated to this story:
  missing `portrait_manifest.yaml`, `tropes.yaml`, `archetypes.yaml`, and the
  `legends/` directory. My diff touches only genre-tier `rules.yaml` +
  `inventory.yaml` (confirmed via `git diff --name-only`) — zero perseus_cloud
  world files — and the pack still loads clean through the runtime loader
  (`load_genre_pack`, the 19-test `test_pack_load.py` suite is green). The stricter
  pack-structure validator flags world-asset gaps the runtime tolerates. Overlaps
  with 71-25 (perseus_cloud grounding) and the content README's tracked asset gaps.
  Affects `genre_packs/space_opera/worlds/perseus_cloud/` (author the missing world
  files). *Found by Dev during implementation.*
- **Improvement** (non-blocking): A `testing-runner` helper, when asked to verify
  GREEN, edited `inventory.yaml` itself via a full YAML round-trip — stripping all
  comments, mangling a folded `notes` block, escaping em-dashes, and reflowing the
  whole file (300+ line diff for a 3-line need). I reverted it and hand-authored
  the surgical change. Process note for future content-mechanics stories: task
  test-runner helpers READ-ONLY and never let a serializer round-trip reach a
  commit. Recorded in `dev-gotchas.md`. Affects test-verification process only.
  *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): The two space_opera combat e2e suites
  (`test_space_opera_melee_e2e.py` + `test_space_opera_swn_combat_e2e.py`) share
  ~5 near-identical helper functions (`_enum_val`, `_load_space_opera`/
  `_has_real_content`, `_player_character`, `_seated_*`, `_throw`, `_spans_named`).
  A future refactor could extract them to `tests/_helpers/space_opera_e2e_fixtures.py`
  and have both suites import them. NOT done in 71-24: it touches the pre-existing
  combat suite (out of footprint, regression risk before review) and self-contained
  e2e modules wiring the production path directly are this suite's established
  convention. Best handled as a dedicated test-infra refactor story. Affects
  `sidequest-server/tests/server/test_space_opera_{melee,swn_combat}_e2e.py`.
  *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): Three Low-severity but genuinely-misleading comments
  should be fixed (ideally folded in before/at merge): (1) `inventory.yaml:48` vibroblade
  comment reads "rules.yaml melee opponent AC4 calib" — "AC4" means *acceptance criterion 4*
  but reads as armor_class 4; the melee AC is 12. Reword to "(per AC4 / hp 7, AC 12)".
  (2) `test_space_opera_melee_e2e.py:1` module docstring titled "(RED)" + closing "RED:
  every melee assertion fails until the bank is authored" — the bank is authored in this PR
  (GREEN on merge); retitle/trim. (3) same file `:18` docstring cites "slay" as an advertised
  melee verb that was rerouted — "slay" stayed on `combat`; only swing/stab/strike moved, and
  the `rules.yaml:324` line anchor is stale. Affects `genre_packs/space_opera/inventory.yaml`
  + `sidequest-server/tests/server/test_space_opera_melee_e2e.py`. *Found by Reviewer during
  code review.*
- **Improvement** (non-blocking): Test-hardening backlog for the melee e2e suite (test-analyzer):
  add a miss-path round-trip (`face=[1]` leaves HP intact), a non-killing round proving the
  71-21 opponent reprisal fires in melee, a `validate(declared_confrontation="combat")` case
  (the realistic pre-71-24 mismatch), beat-id non-empty/uniqueness assertions, a
  `source='dice_throw_beat'`-absence assertion, and a guard that the `combat` type loaded
  (non-empty) in the regression test. All non-blocking — the core contract is proven and the
  miss/reprisal paths are shared engine behavior already covered by the Firefight/SWN suites.
  Affects `sidequest-server/tests/server/test_space_opera_melee_e2e.py`. *Found by Reviewer
  during code review.*
- **Improvement** (non-blocking): `reviewer-preflight` produced an inaccurate narrative diff
  summary (attributed pre-existing pack content — ship_combat hp_depletion, `multifocal_laser`,
  `broadside` — to this branch). Verified the real diff is scoped (melee block + verb edit + 3
  inventory additions). Process note only; preflight's pass/fail/lint result was correct.
  Affects review process. *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

6 deviations

- **Anchored tests on the literal type id `melee`**
  - Rationale: The intent-match path and dispatch lookup resolve by exact string
  - Severity: minor
  - Forward impact: Dev must author the type as `type: melee` (or rename the
- **Strike beat id discovered dynamically, not pinned**
  - Rationale: Tests the behavioral contract (a melee strike ablates HP through the
  - Severity: minor
  - Forward impact: none — Dev may name melee beats freely (only must avoid the
- **Authored the type as `melee` at the genre tier (not `personal_melee` at world tier)**
  - Rationale: The session's world-tier/`personal_melee` framing contradicts SOUL
  - Severity: minor (resolves a session-vs-context divergence TEA flagged; no
  - Forward impact: none — genre-tier melee is inherited by all space_opera worlds;
- **Gave existing melee weapons (vibroknife, stun_baton) damage specs beyond the literal test need**
  - Rationale: The melee `slash` beat has no `damage_override`, so it resolves
  - Severity: minor (slightly beyond literal AC; completes the feature's wiring)
  - Forward impact: melee now deals real damage for any space_opera class wielding
- **Melee bank omits an `angle` beat that session AC2 enumerated**
  - Rationale: The four-kind list in AC2 enumerated the `BeatKind` enum, not a per-bank
  - Severity: trivial
  - Forward impact: none — an `angle` (tag-creating setup) beat can be added later if
- **Session AC7 named a non-existent OTEL span constant**
  - Rationale: The session ACs were sm-setup-generated and named a span constant that does
  - Severity: trivial
  - Forward impact: none — the OTEL coverage AC7 intended is fully satisfied by the real span.

## Design Deviations

**Agents log spec deviations as they happen — not after the fact.**

### TEA (test design)
- **Anchored tests on the literal type id `melee`**
  - Spec source: context-story-71-24.md, Technical Guardrails / Scope Boundaries
  - Spec text: "A new personal-melee confrontation type in `space_opera` `rules.yaml`
    (e.g. `type: melee`)"
  - Implementation: Tests hardcode `confrontation_type == "melee"` as the contract
    (the `_MELEE_TYPE` constant) rather than discovering the melee type by some
    other property.
  - Rationale: The intent-match path and dispatch lookup resolve by exact string
    on `confrontation_type` (no fuzzy fallback, `confrontation.py:99-101`), so the
    type id IS the contract. The context proposed `melee` ("e.g."); pinning it
    removes ambiguity for the green phase. If Dev names it otherwise (e.g.
    `personal_melee`), update `_MELEE_TYPE` in one place.
  - Severity: minor
  - Forward impact: Dev must author the type as `type: melee` (or rename the
    single constant). Documented in the session so the green phase isn't surprised.
- **Strike beat id discovered dynamically, not pinned**
  - Spec source: context-story-71-24.md, AC2
  - Spec text: "apply melee strike beats, assert HP ablates"
  - Implementation: The resolution test selects the strike beat via
    `next(b.id for b in melee.beats if kind == "strike")` rather than hardcoding a
    beat id like `slash`.
  - Rationale: Tests the behavioral contract (a melee strike ablates HP through the
    SWN channel) without dictating the exact beat id — gives the content author
    naming freedom while still proving the mechanic. Beat-kind/channel/stat are
    asserted; the literal id is not.
  - Severity: minor
  - Forward impact: none — Dev may name melee beats freely (only must avoid the
    Firefight/ship/dogfight ids, which the distinctness test enforces).

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Authored the type as `melee` at the genre tier (not `personal_melee` at world tier)**
  - Spec source: session Technical Approach + ACs 1-7 (highest authority) vs
    context-story-71-24.md Technical Guardrails / Assumptions
  - Spec text: session says "Create `worlds/perseus_cloud/rules.yaml` (world-level
    override)" with `type: personal_melee`; context says `type: melee` at the
    genre `rules.yaml`, "no per-world override," per "Crunch in the Genre."
  - Implementation: Authored `type: melee` in `genre_packs/space_opera/rules.yaml`
    (genre tier). Followed the context + TEA's blocking Conflict finding + the
    `combat`/`ship_combat`/`dogfight` naming convention (all short, unprefixed,
    genre-tier) + TEA's tests (which anchor on `confrontation_type == "melee"`).
  - Rationale: The session's world-tier/`personal_melee` framing contradicts SOUL
    doctrine ("Crunch in the Genre, Flavor in the World") and the sibling types.
    Authoring at genre tier means perseus_cloud AND every other space_opera world
    inherit melee for free — the correct home for mechanics. A world override would
    have made melee perseus_cloud-only, which the context explicitly argues against.
  - Severity: minor (resolves a session-vs-context divergence TEA flagged; no
    behavior is lost — perseus_cloud still gets melee, plus every sibling world)
  - Forward impact: none — genre-tier melee is inherited by all space_opera worlds;
    no per-world melee files exist or are needed.
- **Gave existing melee weapons (vibroknife, stun_baton) damage specs beyond the literal test need**
  - Spec source: context-story-71-24.md AC2 ("apply melee strike beats, assert HP
    ablates") + content/CLAUDE.md "No half-wired features"
  - Spec text: tests require only the player's `vibroblade` to deal damage; AC2
    requires the bank to ablate HP through the strike channel.
  - Implementation: Added `vibroblade` (test weapon + iconic melee blade) AND added
    `damage:` to the pre-existing `vibroknife` (1d4+1) and `stun_baton` (1d6) in
    `inventory.yaml`. Only `vibroblade` was strictly test-required.
  - Rationale: The melee `slash` beat has no `damage_override`, so it resolves
    damage from the actor's weapon (Firefight `shoot` pattern). The melee weapons
    Operative/Smuggler START with (`vibroknife`) had NO damage field — so a player
    swinging their starting blade through the new bank would ablate 0 HP. Shipping
    the bank without giving its weapons damage is a decorative, half-wired feature
    (the exact failure content/CLAUDE.md forbids). Three surgical additions,
    formatting/comments preserved.
  - Severity: minor (slightly beyond literal AC; completes the feature's wiring)
  - Forward impact: melee now deals real damage for any space_opera class wielding
    a melee weapon — desirable. No downside identified.

### Reviewer (audit)
- **TEA: anchored tests on literal type id `melee`** → ✓ ACCEPTED by Reviewer: the
  type id IS the contract (exact-match dispatch, no fuzzy fallback); pinning it is
  correct and matches the authored YAML.
- **TEA: strike beat id discovered dynamically, not pinned** → ✓ ACCEPTED by Reviewer:
  tests the behavioral contract (a strike ablates HP) without over-constraining beat
  naming — sound test design.
- **Dev: authored `melee` at genre tier (not `personal_melee` at world tier)** → ✓
  ACCEPTED by Reviewer: architecturally correct per ADR-120 "Crunch in the Genre" and
  consistent with `combat`/`ship_combat`/`dogfight`; Architect spec-check already
  confirmed (Option A). The session ACs were auto-generated drift; resolving toward the
  authoritative context was the right call.
- **Dev: gave vibroknife/stun_baton damage beyond literal test need** → ✓ ACCEPTED by
  Reviewer: a melee bank whose starting weapons deal 0 HP is half-wired (content/CLAUDE.md
  forbids); the additions complete the feature wiring. Surgical, formatting preserved.

### Architect (reconcile)

**Review of existing entries:** All four logged deviations (TEA ×2, Dev ×2) verified —
each carries all 6 fields, the spec source `sprint/context/context-story-71-24.md` exists
and is quoted accurately, the implementation descriptions match the authored
`genre_packs/space_opera/rules.yaml` melee block + `inventory.yaml` additions, and the
forward-impact statements are accurate (genre-tier melee inherited by all space_opera
worlds; no per-world files). No corrections needed. Reviewer stamped all four ✓ ACCEPTED.

**AC deferral check:** No ACs were deferred or descoped — the context's AC1 (distinct
melee bank + verb reroute) and AC2 (hp_depletion + OTEL + ranged regression) are both fully
met and green. No AC accountability deferrals to reconcile. No-op.

**Missed deviations now documented (2):**

- **Melee bank omits an `angle` beat that session AC2 enumerated**
  - Spec source: `.session/71-24-session.md` session Acceptance Criteria, AC2
  - Spec text: "kind classification (strike/brace/angle/push)"
  - Implementation: The authored `melee` bank has beats of kind strike (`slash`,
    `overhand`), brace (`parry`), and push (`withdraw`) — no `angle` beat.
  - Rationale: The four-kind list in AC2 enumerated the `BeatKind` enum, not a per-bank
    requirement. The Firefight bank being mirrored (`shoot`/`take_cover`/`overload`/
    `retreat`) likewise has no `angle` beat. TEA's tests require kinds ⊆ {strike,brace,
    angle,push} with strike+brace present — satisfied. Caught at spec-check (Option A,
    trivial); not logged in-flight by TEA/Dev, formalized here for audit completeness.
  - Severity: trivial
  - Forward impact: none — an `angle` (tag-creating setup) beat can be added later if
    melee tactics want it; its absence neither breaks resolution nor any test.

- **Session AC7 named a non-existent OTEL span constant**
  - Spec source: `.session/71-24-session.md` session Acceptance Criteria, AC7
  - Spec text: "emits SPAN_CONFRONTATION_CREATED with confrontation_type=personal_melee"
  - Implementation: The engine fires the real, tested span `encounter.confrontation_initiated`
    (carrying `encounter_type=melee`); `SPAN_CONFRONTATION_CREATED` is not a constant in
    the telemetry module. The TEA test asserts the real span.
  - Rationale: The session ACs were sm-setup-generated and named a span constant that does
    not exist; the implementation/tests correctly use the live span. A spec-side naming
    error, not a code deviation. Caught at spec-check (Option A); formalized here.
  - Severity: trivial
  - Forward impact: none — the OTEL coverage AC7 intended is fully satisfied by the real span.