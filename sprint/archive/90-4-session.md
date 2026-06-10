---
story_id: "90-4"
jira_key: ""
epic: "90"
workflow: "tdd"
---
# Story 90-4: Scene-harness hydrator — seed per-character WWN core.spellcasting (Effort/prepared) and a WWN hp_depletion encounter so a DETERMINISTIC fixture playtest can prove wwn.* combat + wwn.spell.cast live (deterministic counterpart to 90-3 free-play); _hydrate_character + _hydrate_encounter in server/game/scene_harness.py

## Story Details
- **ID:** 90-4
- **Jira Key:** (none — sprint-only project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** server, content
- **Branch Strategy:** gitflow (feat/90-4-scene-harness-wwn-hydrator on develop)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T07:44:40Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T07:04:30Z | 2026-06-10T07:06:57Z | 2m 27s |
| red | 2026-06-10T07:06:57Z | 2026-06-10T07:26:56Z | 19m 59s |
| green | 2026-06-10T07:26:56Z | 2026-06-10T07:35:50Z | 8m 54s |
| review | 2026-06-10T07:35:50Z | 2026-06-10T07:44:40Z | 8m 50s |
| finish | 2026-06-10T07:44:40Z | - | - |

## Sm Assessment

**Setup complete — ready for RED phase (TEA).**

**What this story delivers:** The scene-harness hydrator (`sidequest-server/sidequest/game/scene_harness.py`) currently cannot seed a deterministic WWN fixture. Two gaps, per epic-90 findings (3):
- `_hydrate_character` can't seed per-character WWN `core.spellcasting` (Effort/prepared), so `wwn.spell.cast` can't fire from a fixture.
- `_hydrate_encounter` builds a dial `StructuredEncounter`, not a WWN `hp_depletion` encounter, so deterministic `wwn.*` combat can't be proven.

This is the **deterministic counterpart to 90-3** (which proves the same via live free-play). The scene-harness is the dev-gated HTTP fixture endpoint (ADR-092); making it WWN-aware lets a content-only fixture playtest prove the crunch fires without narrator non-determinism.

**Dependency posture:** No `depends_on`. Siblings 90-1 (encountergen ruleset-awareness) and 90-2 (WWN magic plugin session-bind instantiation) are DONE — the magic_state plumbing 90-2 landed is what makes per-character `core.spellcasting` seedable here. 90-3 (live proof) and this story (deterministic proof) are parallel halves of AC5b.

**Lanes for TEA:** Server is the engine lane (`_hydrate_character`, `_hydrate_encounter`). Content lane is the WWN fixture scenario YAML that exercises both paths. OTEL is load-bearing per CLAUDE.md — the proof is the GM-panel lie-detector seeing `wwn.spell.cast` and `wwn.*` combat spans fire deterministically; RED tests should assert on those spans, not just on hydrator return values. Refs: ADR-059/114/116/117/126/139/092.

**Routing:** phased tdd → next agent **tea** (RED). No code from SM.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

The sprint YAML carried NO acceptance criteria, so I derived AC-1..AC-8 during RED (see the banner at the top of `tests/game/test_scene_harness_hydrator.py` "Story 90-4" section and the TEA deviation log below). Two hydrator functions change in `sidequest/sidequest/game/scene_harness.py`:
- `_hydrate_character` → seed `Character.core.spellcasting` from a `spellcasting:` block (wwn_magic.SpellcastingState).
- `_hydrate_encounter` → read `win_condition:` / `category:` / `actors:` so a fixture can stand up a WWN `hp_depletion` combat seating player + opponent actors.

**Test Files:**
- `tests/game/test_scene_harness_hydrator.py` — 14 new unit tests (synthetic tmp_path fixtures, no real pack). Appended as a "Story 90-4" section after the 50-21 encounter tests.
- `tests/integration/test_wwn_scene_harness_fixture_proof.py` — NEW. 2 end-to-end wiring proofs on the real elemental_harmony pack (skip-guarded on content presence, run `-n0`).

**Tests Written:** 16 tests covering 8 ACs.

**RED verification (testing-runner, RUN_ID 90-4-tea-red):**
- Unit: 9 feature tests FAIL with feature-missing assertions (`spellcasting is None`, `win_condition=='dial_threshold'`, `category==''`, `actors==[]`, no `FixtureValidationError` raised); 4 backward-compat regression-locks PASS (current behavior preserved); 1 multi-PC test re-verified to fail on the spellcasting assertion (not a fixture/pydantic setup error) after adding required `backstory`/`race`.
- Integration: BOTH FAIL (not skip — content is on disk) — cast proof fails on `spellcasting is None`; strike proof fails on `win_condition=='dial_threshold'`.
- Collection clean (no import/syntax errors). `ruff format` + `ruff check` clean on both files.

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing / no silent skip | `test_spellcasting_block_not_a_mapping_raises`, `test_spellcasting_extra_field_rejected`, `test_encounter_invalid_win_condition_raises`, `test_encounter_actors_not_a_list_raises`, `test_encounter_actor_invalid_side_raises` | failing (RED) |
| #6 test quality (meaningful assertions) | self-check: every test asserts a specific value/exception; no `assert True`, no bare-truthy, no assertion-less calls | pass (self) |
| #11 input validation at the fixture-parser boundary | all five fail-loud tests above + `test_encounter_win_condition_hp_depletion_hydrates` (valid-path projection) | failing (RED) |

**Rules checked:** 3 of 13 lang-review rules are materially applicable to a YAML-fixture-parser change (the rest — async, resource leaks, deps, SQL — don't apply to this diff). All three have test coverage.
**Self-check:** 0 vacuous tests found in the new code.

**Handoff:** To Julia (Dev) for GREEN implementation in `scene_harness.py`.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): No committed canonical WWN fixture exists for the dev-gated `POST /dev/scene/{name}` route to load — the integration proof writes its fixture to `tmp_path`. A committed `scenarios/fixtures/wwn_combat_*.yaml` (orchestrator) or a content-side fixture would let a real deterministic playtest exercise this through the HTTP route, not just pytest. Affects `scenarios/fixtures/` (add a canonical WWN spellcasting+hp_depletion fixture once the hydrator lands). *Found by TEA during test design.*
- **Question** (non-blocking): The opponent NPC in the integration fixture relies on the `CreatureCore` default HP (10/10/10) because `_hydrate_npc` seeds no HP — adequate for the ablation proof but means a fixture cannot author opponent HP/AC. If a future deterministic combat needs a specific opponent HP, `_hydrate_npc` would need an `hp`/`max_hp`/`ac` path (out of THIS story's `_hydrate_character`+`_hydrate_encounter` scope). Affects `sidequest/game/scene_harness.py::_hydrate_npc`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): A pack with a renamed `attribute_map` (e.g. elemental_harmony: STRENGTH→Strength) requires callers of `dispatch_dice_throw` to pass `character_stats` keyed by the pack's flavor names, because `swn._stat` matches exact/case-insensitive only and (by design) no longer falls back to neutral-10. Production derives stats from `character.stats`, so this is correct as long as chargen stores flavor-keyed stats — but a fixture/test author can easily pass SWN-canonical abbreviations and hit a fail-loud KeyError. A future hardening could let `_stat` consult `cfg.attribute_map` to translate abbreviated→flavor, but that risks re-softening the deliberate no-fallback contract. Affects `sidequest/game/ruleset/swn.py::_stat`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): `_hydrate_encounter` accepts semantically degenerate combats — `win_condition: hp_depletion` with zero `actors`, all-same-side actors, and duplicate actor names all pass silently. Faithful-projector contract + downstream ADR-116/139 invariants make this non-blocking on a dev-gated tool, but a defense-in-depth hardening should add a loud `hp_depletion ⇒ ≥1 opposite-side actor` + duplicate-name guard. Affects `sidequest/game/scene_harness.py::_hydrate_encounter` (add post-construct validation). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `SpellcastingState` int fields (`casts_remaining`, `casts_per_day`, `max_spell_level`) accept `bool` (coerced to 0/1) and negatives — now reachable from the fixture hydration path. Add `Field(ge=0)` + a bool-reject `@field_validator`. Affects `sidequest/game/wwn_magic.py:58-61` (OUTSIDE this story's diff — pre-existing model). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The belt-and-suspenders path-containment check at `scene_harness.py:95` uses `str.startswith` without a trailing separator (sibling-dir confusion). Replace with `Path.is_relative_to`. PRE-EXISTING `hydrate_fixture` code, NOT in this story's diff; the `_FIXTURE_NAME_RE` guard is the effective control. Affects `sidequest/game/scene_harness.py:95`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Authored AC-1..AC-8 (no ACs in sprint YAML)**
  - Spec source: sprint/epic-90.yaml story 90-4 node; context-story-90-4.md ("No acceptance criteria recorded — TEA to define during the RED phase")
  - Spec text: "scene-harness hydrator seeds WWN spellcasting + hp_depletion encounter for a DETERMINISTIC fixture proof; _hydrate_character + _hydrate_encounter"
  - Implementation: Derived 8 ACs from the story title + epic finding (3) and encoded them as the test rubric (see banner in test_scene_harness_hydrator.py).
  - Rationale: TDD needs concrete, testable behavior; the story title + epic finding fully determine the intended behavior.
  - Severity: minor
  - Forward impact: Architect/Dev should sanity-check the AC set in GREEN; if any AC over/under-shoots intent, adjust before implementing.
- **Fixture schema is EXPLICIT fields (win_condition / category / actors / spellcasting), not cdef-stamped**
  - Spec source: story title; ADR-092 hydrator philosophy (explicit fixture fields, fail-loud)
  - Spec text: "_hydrate_encounter ... a WWN hp_depletion encounter"
  - Implementation: Tests assume the fixture YAML declares `encounter.win_condition`, `encounter.category`, `encounter.actors[]`, and `character.spellcasting{}` directly — the hydrator does NOT load the pack to stamp win_condition/category from the ConfrontationDef the way `instantiate_encounter_from_trigger` does.
  - Rationale: Keeps the hydrator deterministic and decoupled from pack-loading/cdef resolution; matches how every other hydrator block (known_facts, abilities, magic_state) takes explicit fixture fields and fails loud on malformed shapes. The integration proof still sets `encounter.type: combat` so the apply path resolves the real cdef at runtime — the explicit-fields choice only governs what the *hydrator* reads, not what the engine resolves downstream.
  - Severity: minor
  - Forward impact: If Dev/Architect prefers cdef-stamping (DRY against rules.yaml), the win_condition/category tests would need to assert the stamped value instead of the literal — flag before implementing. Either path satisfies the deterministic-proof goal.
- **One comprehensive cast-based wiring proof + one strike proof (not a broader matrix)**
  - Spec source: CLAUDE.md "Every Test Suite Needs a Wiring Test"; story "prove wwn.* combat + wwn.spell.cast"
  - Spec text: "a DETERMINISTIC fixture playtest can prove wwn.* combat + wwn.spell.cast live"
  - Implementation: The cast proof exercises BOTH halves (wwn.spell.cast span + ablative HP via the shared HP channel → state_patch.hp); the strike proof adds the non-spell combat path (elemental_burst, damage_override 2d6). Both seat state via the fixture hydrator, not chargen/trigger.
  - Rationale: The cast path alone proves spellcasting + ablative-HP; the strike adds combat-without-magic coverage. A full per-spell / per-beat matrix is out of scope for a hydrator story.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)
- **Corrected two test-fixture data typos to reach GREEN (no assertion/intent change)**
  - Spec source: tests/game/test_scene_harness_hydrator.py::test_encounter_invalid_win_condition_raises; tests/integration/test_wwn_scene_harness_fixture_proof.py::test_hydrated_wwn_fixture_drives_deterministic_strike
  - Spec text: (1) "an invalid `win_condition` value raises FixtureValidationError ... a typo must surface"; (2) strike proof drives elemental_burst (stat_check: Strength) against the real elemental_harmony pack.
  - Implementation: (1) The fixture wrote `win_condition: hp_depletion` — a VALID Literal — so nothing could be rejected; changed it to the genuine typo `hp_deletion` so the closed-Literal rejection wraps into FixtureValidationError as the docstring intends. (2) The strike test passed SWN-canonical abbreviations `{STR,DEX,CON,INT,WIS,CHA}` as `character_stats`, but elemental_harmony renames the attributes (attribute_map) and the beat's stat_check is the flavor name `Strength`; changed character_stats to the pack's flavor names `{Strength,Agility,Endurance,Insight,Spirit,Harmony}` so `swn._stat` resolves it (it fails loud by design — "no neutral-10 fallback").
  - Rationale: The hydrator implementation (this story's `_hydrate_character` + `_hydrate_encounter`) was already correct: it wraps pydantic ValidationError → FixtureValidationError, and the stat lookup lives in swn.py outside this story's scope. The only way to make these two tests GREEN was to fix the fixture *data* — rejecting the valid `hp_depletion` would break every other test that requires it, and translating abbreviated→flavor stat keys inside `_stat` would reintroduce the neutral-fallback the SWN module deliberately removed.
  - Severity: minor
  - Forward impact: none — assertions, test names, and docstrings are unchanged; only the literal fixture inputs were corrected to match documented intent.

### Reviewer (audit)
- **TEA: Authored AC-1..AC-8 (no ACs in sprint YAML)** → ✓ ACCEPTED by Reviewer: the ACs faithfully decompose the story title + epic-90 finding (3); the 16 tests map cleanly to them and the integration proofs cover the headline "prove wwn.* combat + wwn.spell.cast live" requirement.
- **TEA: Fixture schema is EXPLICIT fields, not cdef-stamped** → ✓ ACCEPTED by Reviewer: faithful-projector design is consistent with every sibling hydrator block (known_facts/abilities/magic_state) — shape-validate + project, fail-loud on malformed shapes. The integration proof still sets `type: combat` so the real cdef resolves at apply time. Sound.
- **TEA: One cast + one strike wiring proof (not a broader matrix)** → ✓ ACCEPTED by Reviewer: the cast proof exercises spellcasting + ablative-HP + the `wwn.spell.cast` span (the lie-detector), the strike adds the non-spell combat path. Adequate wiring coverage per CLAUDE.md "Every Test Suite Needs a Wiring Test"; a per-spell matrix is correctly out of scope.
- **Dev: Corrected two test-fixture data typos to reach GREEN** → ✓ ACCEPTED by Reviewer: both corrections fix genuine TEA fixture-DATA defects (a valid Literal where a typo was intended; SWN-canonical stat keys for a pack that renames its attributes) with assertions/intent unchanged. Verified: the implementation already wraps `ValidationError → FixtureValidationError` (scene_harness.py:332-335, 727-730) and the stat lookup lives in `swn._stat` outside this diff — contorting the implementation to pass the buggy fixtures would have been the wrong fix. Correct call.
- **Reviewer (undocumented):** No undocumented spec deviations found. The diff matches the logged deviations and the AC set.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/scene_harness.py` — `_hydrate_character` seeds `CreatureCore.spellcasting` from a fixture `spellcasting:` block (WWN `SpellcastingState`, fail-loud on non-mapping / extra key); `_hydrate_encounter` reads `win_condition` (default `dial_threshold`), `category` (default `""`), and an `actors:` list (→ `EncounterActor[]`), fail-loud on non-list/non-mapping shapes, with closed-Literal rejections re-wrapped as `FixtureValidationError`.
- `tests/game/test_scene_harness_hydrator.py` — corrected one fixture typo (`hp_depletion` → genuine typo `hp_deletion`) so the invalid-win_condition test exercises a value the Literal actually rejects.
- `tests/integration/test_wwn_scene_harness_fixture_proof.py` — corrected the strike proof's `character_stats` to elemental_harmony's flavor attribute names (`Strength/Agility/Endurance/Insight/Spirit/Harmony`) so `swn._stat` resolves the beat's `stat_check: Strength`.

**Tests:** 115/115 passing (GREEN) — 113 unit (`test_scene_harness_hydrator.py`) + 2 integration (`test_wwn_scene_harness_fixture_proof.py`, run `-n0`). `ruff format` + `ruff check` clean.

**Branch:** feat/90-4-scene-harness-wwn-hydrator (pushed)

**Handoff:** To next phase (verify/review).
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 real smells (1 standard content-guard skip) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Yes | findings | 5 (+1 self-discarded) | confirmed 5 (all downgraded to Medium/Low, non-blocking), dismissed 0, deferred 0 |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings (Reviewer assessed test quality directly — high) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings (Reviewer spot-checked comments — accurate) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 2 (both low/medium confidence) | confirmed 2 (both non-blocking: 1 out-of-diff, 1 file-convention), dismissed 0 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings (Reviewer ran rule-by-rule enumeration directly — see Rule Compliance) |

**All received:** Yes (3 enabled returned; 6 disabled via `workflow.reviewer_subagents` and pre-filled as Skipped)
**Total findings:** 7 confirmed (all Medium/Low, non-blocking), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Summary:** Story 90-4 adds two faithful-projector branches to the scene-harness hydrator — `_hydrate_character` seeds `CreatureCore.spellcasting` from a fixture `spellcasting:` block, and `_hydrate_encounter` reads `win_condition`/`category`/`actors[]` so a deterministic fixture stands up a WWN `hp_depletion` combat. Both halves are proven live by integration tests on the real `elemental_harmony` pack: the cast proof fires `wwn.spell.cast` (refused=False) + ablates HP through the `state_patch.hp` channel (the GM-panel lie-detector), and the strike proof drives `elemental_burst` damage. 115/115 GREEN, ruff clean. The new code follows the established hydrator contract (shape-validate + fail-loud-on-malformed + faithful projection) used by every sibling block. No Critical/High issues.

**Data flow traced:** fixture YAML `name` → `_FIXTURE_NAME_RE` path-traversal guard (scene_harness.py:82) → `.resolve()` + containment check (90-96) → `yaml.safe_load` (109) → `_hydrate_character` splats `spellcasting:` into `SpellcastingState(**raw)` (extra=forbid → typos rejected) → `CreatureCore.spellcasting` → snapshot. Untrusted structure is shape-checked and pydantic-validated at every hop; malformed input fails loud as `FixtureValidationError` (HTTP 422). Safe.

**Pattern observed:** Universal `FixtureValidationError(f"... — {exc}")` wrapping convention across all 8 hydrator blocks (scene_harness.py:116/181/200/219/268/334/603/729) — the new spellcasting (334) and encounter (729) sites follow it exactly. Consistent, refactor-stable, maps parser-internal exceptions to a stable HTTP contract.

**Error handling:** Non-dict `spellcasting` → loud raise (325-329); pydantic `ValidationError` → wrapped (332-335); non-list `actors` → loud raise (695-699); non-dict actor entry → loud raise (700-705); closed-Literal `win_condition`/`side` typo + non-string `category` → pydantic rejects, wrapped at 727-730. Verified by tests `test_spellcasting_block_not_a_mapping_raises`, `test_spellcasting_extra_field_rejected`, `test_encounter_invalid_win_condition_raises`, `test_encounter_actors_not_a_list_raises`, `test_encounter_actor_invalid_side_raises`.

### Observations

- `[VERIFIED]` Path-traversal guard — `_FIXTURE_NAME_RE = ^[A-Za-z0-9][A-Za-z0-9_-]*$` (scene_harness.py:67,82) rejects `..`, separators, NUL, absolute paths; `yaml.safe_load` (109) blocks `!!python/object` RCE. Complies with python.md #8 (unsafe deserialization) and #11 (file-parser input validation). Pre-existing, unchanged by this story.
- `[VERIFIED]` `SpellcastingState` and `EncounterActor.side` are closed types — `extra="forbid"` (wwn_magic.py:56) + `ActorSide = Literal[...]` (encounter.py:78); typo'd keys/values fail loud, matching the "No Silent Fallbacks" rule.
- `[VERIFIED]` Test quality — every 90-4 test asserts a specific value/exception with a descriptive message; positive, backward-compat (spellcasting stays None / win_condition defaults dial_threshold), and fail-loud cases all present. No vacuous assertions (python.md #6). The two Dev fixture-data corrections are sound.
- `[EDGE][MEDIUM]` `win_condition: hp_depletion` with zero/empty `actors` is accepted silently (scene_harness.py:707-712) — no defender for the cast/strike spine. Downgraded from edge-hunter's High: dev-gated tool (ADR-092), happy path proven, the no-Other case is an architectural invariant owned downstream (ADR-116 End-on-No-Other, ADR-139 Win-Condition Liveness / Mechanically-Capable Other), failure self-reveals at dev playtest time, and the faithful-projector contract matches all sibling blocks. Non-blocking; worthwhile defense-in-depth fast-follow (add a loud `hp_depletion ⇒ actors` guard at the hydrator boundary).
- `[EDGE][LOW]` All-same-side actors accepted silently (707-712) — subsumed by the actor-coupling hardening above. Non-blocking.
- `[EDGE][LOW]` Duplicate actor names accepted silently (707-712) — engine name-resolution matches first occurrence. Non-blocking hardening.
- `[EDGE][LOW]` `SpellcastingState` int fields coerce `bool`→int (YAML `casts_remaining: true` → 1) — fix belongs in `wwn_magic.py:59-61` (a `@field_validator` or `Field` constraint), OUTSIDE this story's diff. Non-blocking footgun on a pre-existing model.
- `[EDGE][LOW]` `SpellcastingState` int fields accept negatives (`casts_remaining: -3` silently disables casting) — fix is `Field(ge=0)` in `wwn_magic.py:59-61`, OUTSIDE this diff. Non-blocking.
- `[SEC][LOW]` Belt-and-suspenders containment check `str.startswith(str(fixtures_dir_resolved))` lacks a trailing separator (scene_harness.py:95) — sibling-dir confusion. PRE-EXISTING `hydrate_fixture` code, NOT in this story's diff; the regex (67) is the effective guard and blocks all known traversal. Non-blocking, out-of-scope.
- `[SEC][LOW]` Pydantic `ValidationError` str() echoed into the `FixtureValidationError` message (334/729) reaches the HTTP 422 body — could reflect fixture values. Consistent with the file-wide convention (8 sites), dev-gated, and the fixture author sees their own content (no privilege boundary). Non-blocking.
- `[TEST]` test_analyzer disabled — Reviewer assessed directly: high quality, no vacuous assertions, wiring proofs present. No findings.
- `[SILENT]` silent-failure-hunter disabled — Reviewer assessed directly: the edge-hunter's "silent accept" findings (above) cover this domain; all are fixture-author footguns on a dev-gated tool, downgraded Medium/Low, non-blocking. No swallowed exceptions or empty catches in the diff.
- `[DOC]` comment-analyzer disabled — Reviewer spot-checked: the new comments (314-322, 681-690) accurately describe behavior and cite the correct story/ADR/`extra=forbid` invariants. No stale/misleading docs.
- `[TYPE]` type-design disabled — Reviewer assessed: new params/returns annotated; `EncounterActor`/`SpellcastingState` are validated pydantic models; closed Literals on `win_condition`/`side`. No stringly-typed gaps introduced.
- `[SIMPLE]` simplifier disabled — Reviewer assessed: the two branches mirror existing hydrator blocks; no dead code, no over-engineering. The `(actors_raw or [])` + pre-loop dict-check is the minimal correct shape.
- `[RULE]` rule-checker disabled — Reviewer ran rule-by-rule enumeration (see Rule Compliance). All 13 python.md checks pass on the diff; No-Silent-Fallbacks findings are confirmed-and-downgraded, not dismissed.

### Rule Compliance (.pennyfarthing/gates/lang-review/python.md — enumerated over the diff)

| # | Rule | Instances in diff | Verdict |
|---|------|-------------------|---------|
| 1 | Silent exception swallowing | 2 `except ValidationError` (334, 727) — both re-raise wrapped, no swallow | PASS |
| 2 | Mutable default arguments | 0 new function defaults; `(actors_raw or [])` avoids shared mutable | PASS |
| 3 | Type annotations at boundaries | `_hydrate_character(data: dict[str,Any]) -> Character`, `_hydrate_encounter(raw: Any, *, fixture_name: str) -> StructuredEncounter` annotated | PASS |
| 4 | Logging coverage/correctness | No new log calls in the two branches; the boundary `logger.warning` for YAML errors is pre-existing/correct level | PASS |
| 5 | Path handling | No new path manipulation in diff; `Path` + `resolve()` + `encoding="utf-8"` pre-existing | PASS |
| 6 | Test quality | 10 new unit + 2 integration; specific assertions, no vacuous/skip-without-reason | PASS |
| 7 | Resource leaks | No new file/socket/lock acquisition | PASS (N/A) |
| 8 | Unsafe deserialization | `yaml.safe_load` (pre-existing); `SpellcastingState(**raw)`/`EncounterActor(**entry)` splat into `extra=forbid`/Literal-closed pydantic models — no eval/pickle | PASS |
| 9 | Async/await | No async code in diff | PASS (N/A) |
| 10 | Import hygiene | Added `EncounterActor`, `SpellcastingState` as explicit imports (36, 42); no star/circular | PASS |
| 11 | Input validation at boundaries | spellcasting/actors/win_condition/category all shape- + type-validated, fail-loud; matches No-Silent-Fallbacks | PASS (edge-hunter's semantic cross-field coupling = non-blocking hardening) |
| 12 | Dependency hygiene | No dependency changes | PASS (N/A) |
| 13 | Fix-introduced regressions | Dev's two fixture-data fixes re-scanned vs #1-12 — no new class of bug introduced | PASS |

### Devil's Advocate

Let me argue this code is broken. A malicious or careless fixture author controls the entire YAML. What can they do? First, they can declare `win_condition: hp_depletion` with no `actors` and stand up a combat that has no opponent — the cast/strike spine resolves its defender by filtering for the opposite side, finds nothing, and either throws deep in the apply path or silently produces an unwinnable scene. The edge-hunter is right that the hydrator accepts this silently. They can also seed two `side: player` actors and zero opponents (same failure), or two actors with the same `name` so the engine's name-keyed lookup silently picks the first. On the spellcasting side they can write `casts_remaining: true` (pydantic coerces to 1) or `casts_remaining: -3` (silently disables casting) — neither raises, both violate fail-loud intent. A confused author who fat-fingers `win_conditon` (missing 'i') gets an `extra=forbid`/Literal rejection only on the value, not the key, because the key lives at the encounter-dict level, not inside a forbid'd model — though `_hydrate_encounter` reads via `raw.get` so an unknown sibling key is simply ignored (a real, if minor, silent-accept). What about a huge input — a 10,000-element `actors` list? `yaml.safe_load` will happily build it and the list comprehension will construct 10,000 `EncounterActor`s; there's no length bound, but this is a dev-gated loader, not an internet-facing endpoint, so DoS is not in the threat model. A stressed filesystem (fixture deleted mid-read) is handled — `OSError` → `FixtureValidationError`. Path traversal via `../` or symlink? The regex blocks the traversal strings; the `startswith` containment check is weak (sibling-dir confusion) but is belt-and-suspenders behind the regex and is pre-existing, not this story's code. So the genuine new exposure is a class of *semantically degenerate but structurally valid* encounters and spell economies that the hydrator faithfully projects rather than rejecting. Every one of these is (a) authored by a trusted developer/GM on a dev-gated tool, (b) self-revealing the moment the fixture is run in a playtest, (c) guarded downstream by the documented confrontation-integrity invariants (ADR-116/139), and (d) consistent with the faithful-projector contract every sibling hydrator block already honors. None corrupts persistent state or reaches a production player. That moves them firmly into non-blocking-hardening territory — worth a fast-follow story, not a rejection. The devil finds footguns, not a broken feature.

**Handoff:** To SM (Winston Smith) for finish-story.