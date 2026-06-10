---
story_id: "102-6"
jira_key: ""
epic: "102"
workflow: "tdd"
---
# Story 102-6: Psionics (SWN design §6 follow-on, P7) — SWN/WWN psychic disciplines + Effort economy + System Strain, wired into live dispatch with {ruleset}.effort.commit/reclaim + system_strain.delta spans.

## Story Details
- **ID:** 102-6
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 8
- **Priority:** p2

## Sm Assessment

**Story:** 102-6 — Psionics (SWN design §6 follow-on, P7). SWN/WWN psychic disciplines + Effort economy + System Strain, wired into live dispatch. 8pt, p2, tdd. Repos: server + content.

**Setup state:** Session created; `feat/102-6-psionics-swn-wwn-effort-strain` branched from `develop` in BOTH sidequest-server and sidequest-content. Context validated at `sprint/context/context-story-102-6.md` (parent `context-epic-102.md`). No Jira (personal project — jira_key intentionally empty). Merge gate clear (0 in review). Last backlog story in epic 102.

**Technical landscape for Fezzik (TEA):**
- This is the deferred SWN P7. Substrate exists — 90-7 landed WWN effort *hydration* (`wwn.magic_hydrated`); verify its payload covers the discipline/Effort data shape before building (AC assumption #1). Reuse the cast spine and hydration; do NOT build a parallel "psionics dispatch."
- Activation flows through the SAME dispatch entry points 102-2/102-3 wired (beat path + intent-router path), with Effort accounting instead of slot/cast where rules differ. 102-5 (narrator tool contract) is done — psionic tools follow its pattern.
- **Span set is contractual** and must be RED-tested: `{ruleset}.effort.commit`, `{ruleset}.effort.reclaim`, `system_strain.delta`, plus a discipline-activation span shaped like `wwn.spell.cast`.
- **Strain ledger unity** (AC3): psionic Strain and CWN/AWN lethality Strain MUST hit ONE counter per character — no forked strain fields. Write a mixed-source fixture test that would catch a fork.
- **Effort lifecycle is stateful** (AC2): committed Effort reclaims on scene/day boundaries; wire reclaim into existing scene/time-advance surfaces (ADR-130 precedent). Resume-safe — Effort + Strain round-trip in the save (AC5).
- **Authoring surface** (AC4): a discipline added purely in pack YAML must validate + activate with zero engine edits. Per project memory, content-catalog invariants belong in the pack VALIDATOR, not unit tests — but AC4's code-shaped test uses a *synthetic fixture discipline in a test pack*, NOT a live pack slug (memory: tests must not point at live content).
- **Wiring test required** (AC6, and project doctrine): one integration test from player input → dispatch → spans. Per the Without-Number wiring checklist (project memory), a new ruleset-module-adjacent change has touchpoints plans keep omitting: spans `__init__` re-export, `dice.py` downed-seam guards, and OTEL span-assertion tests — confirm whether psionics touches these.
- Player-facing math (Effort pool committed/free + Strain) must be legible via existing reactive-state surfaces (no new UI components — server,content only; flag to SM if a UI change becomes necessary).

**Recommendation:** Proceed to RED. Start each AC's failing test against the REAL SWN (space_opera) + WWN (heavy_metal) packs where live behavior is asserted, and a synthetic test pack only for the AC4 authoring-surface test.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T23:55:52Z
**Round-Trip Count:** 2

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T22:28:47+00:00 | 2026-06-10T22:31:14Z | 2m 27s |
| red | 2026-06-10T22:31:14Z | 2026-06-10T23:03:28Z | 32m 14s |
| green | 2026-06-10T23:03:28Z | 2026-06-10T23:35:03Z | 31m 35s |
| review | 2026-06-10T23:35:03Z | 2026-06-10T23:41:17Z | 6m 14s |
| green | 2026-06-10T23:41:17Z | 2026-06-10T23:48:09Z | 6m 52s |
| review | 2026-06-10T23:48:09Z | 2026-06-10T23:52:48Z | 4m 39s |
| green | 2026-06-10T23:52:48Z | 2026-06-10T23:53:59Z | 1m 11s |
| review | 2026-06-10T23:53:59Z | 2026-06-10T23:55:52Z | 1m 53s |
| finish | 2026-06-10T23:55:52Z | - | - |

## TEA Assessment

**Tests Required:** Yes
**Reason:** 8pt feature spanning content model + loader + ruleset engine + dispatch + persistence + projection.

**Test Files:**
- `tests/game/ruleset/test_swn_psionics_effort_102_6.py` — Effort lifted to the SWN family base + `{ruleset}`-namespaced commit/reclaim spans + AC1-edge loud-not-silent (Python rule #1).
- `tests/server/test_psionics_dispatch_wiring_102_6.py` — AC1 + AC6 both dispatch paths (free-text `magic_working` + beat `discipline_id` sidecar) + AC3 strain routing/no-fork; mirrors the 102-3 dispatch-bank harness.
- `tests/server/test_psionics_scene_reclaim_102_6.py` — AC2 scene/day reclaim lifecycle for SWN sessions; mirrors `test_wwn_scene_reclaim.py`.
- `tests/integration/test_psionics_authoring_surface_102_6.py` — AC4 YAML→catalog→validate→activate, synthetic inline discipline (no live pack slug); Python rules #8 + #11.
- `tests/persistence/test_psionics_round_trip_102_6.py` — AC5 committed Effort + accumulated Strain survive the production JSON round-trip.
- `tests/server/test_psionics_player_projection_102_6.py` — Sebastien/Jade legibility: Effort/Strain on `PartyMember`; mirrors the 53-5 rig_composure precedent.

**Tests Written:** 38 tests across 6 files covering ACs 1–6 + the player-legibility guardrail.
**Status:** RED — verified via testing-runner (RUN_ID 102-6-tea-red): **30 FAILED, 5 PASSED (regression guards), 3 SKIPPED, 0 test bugs.** Every failure is a missing net-new symbol (ModuleNotFoundError/AttributeError) or a missing-behavior assertion — no setup/collection bugs.

### AC Coverage

| AC | Tests | Status |
|----|-------|--------|
| AC1 discipline activation live (+ zero-Effort loud edge) | `test_freeplay_discipline_activation_fires_discipline_and_effort_spans`, `test_discipline_activation_with_no_free_effort_is_loud`, `test_activation_with_no_free_effort_is_not_a_silent_success` | RED |
| AC2 reclaim lifecycle (scene/day) | `test_end_scene_reclaims_scene_effort_for_swn_session`, `test_end_scene_emits_swn_namespaced_reclaim_span`, `test_swn_day_reclaim_drops_day_commitments_and_is_namespaced` | RED |
| AC3 strain ledger unity (mixed-source) | `test_wwn_psionic_push_routes_strain_through_shared_counter`, `test_psionic_strain_and_lethality_strain_are_one_field_not_forked` (guard, green) | RED + guard |
| AC4 authoring surface (homebrew YAML) | `test_discipline_catalog_loads_from_yaml`, `test_duplicate_discipline_id_rejected`, `test_unknown_discipline_field_rejected`, `test_catalog_get_unknown_id_fails_loud`, `test_yaml_authored_discipline_is_activatable` | RED |
| AC5 persistence (resume-safe) | `test_committed_psionic_effort_survives_round_trip`, `test_reloaded_psychic_can_still_activate`, `test_accumulated_system_strain_survives_round_trip` (guard, green) | RED + guard |
| AC6 wiring (input→dispatch→spans) | `test_freeplay_discipline_activation_fires_discipline_and_effort_spans` (real `run_dispatch_bank`), `test_beat_selection_reads_discipline_id_sidecar`, `test_native_genre_discipline_dispatch_emits_no_swn_spans` (guard, green) | RED + guard |
| Span contract `{ruleset}.effort.commit/reclaim` | `test_swn_commit_emits_swn_namespaced_span`, `test_wwn_commit_still_emits_wwn_namespaced_span` (backward-compat guard) | RED + guard |
| Guardrail: player-facing Effort/Strain legibility | `TestEffortProjectionFields`, `TestStrainProjectionFields` (RED); `TestEffortStrainExtraction` (skipped, see Finding) | RED + skip |

### Rule Coverage (python.md lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exceptions / No Silent Fallbacks | `test_activation_with_no_free_effort_is_not_a_silent_success`, `test_missing_pool_raises_not_silently_noops`, `test_discipline_activation_with_no_free_effort_is_loud`, `test_catalog_get_unknown_id_fails_loud` | RED |
| #6 test quality (meaningful asserts) | self-checked — no `assert True`, no truthy-only checks; 3 skips carry explicit reasons | pass |
| #8 unsafe deserialization | `load_psionic_discipline_catalog` exercised via YAML → must use `yaml.safe_load` (catalog loader) | RED |
| #11 input validation at boundary | `test_duplicate_discipline_id_rejected`, `test_unknown_discipline_field_rejected` (`extra="forbid"`) | RED |

**Rules checked:** 4 of the directly-applicable lang-review rules have test coverage (the rest — async, paths, resource leaks, deps — are not exercised by this story's surface).
**Self-check:** 0 vacuous assertions found; the 5 green tests are intentional regression guards (documented), the 3 skips carry explicit reasons + a backing Delivery Finding.

**Handoff:** To Inigo Montoya (Dev) for GREEN. The net-new symbol contract is enumerated in Design Deviations; the strain-seeding gap, SWN-strain question, and projection-wiring obligation are in Delivery Findings.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `seed_system_strain` (builder.py) gates on `isinstance(cfg, CwnConfig)`, so WWN psychics get `core.system_strain=None` at chargen even though `WwnConfig` carries a `SystemStrainConfig`. AC3 (psionic Strain on the shared counter) requires a strain pool to exist for WWN/SWN psychics. Affects `sidequest/game/builder.py` (`seed_system_strain` must seed for the strain-bearing psionic rulesets), and possibly `SwnConfig` (no `system_strain` block today). *Found by TEA during test design.*
- **Question** (non-blocking): Does SWN proper bear System Strain, or is psionic Strain WWN-only? AC3's "mixed-source one counter" requires *lethality* Strain, which only CWN/WWN/AWN have (`run_cwn_wwn_downed_seam` excludes SWN). The strain-unity tests are written on the WWN (heavy_metal) config for that reason; if Dev scopes SWN psionics to Effort-only (no Strain), `SwnConfig` needs no strain block and the SWN side covers only Effort. Affects `sidequest/genre/models/rules.py` (`SwnConfig`). *Found by TEA during test design.*
- **Gap** (blocking for the projection guardrail only): the player-facing Effort/Strain projection has TWO halves — the `PartyMember` protocol fields (tested, RED) AND the `party_member_from_character` (views.py) population that fills them. The population wiring tests are SKIPPED (heavy handler/_SessionData fixture, mirroring the 53-5 rig_composure precedent). Dev MUST wire the views.py extraction in GREEN, not just add the fields, or the pools exist on the wire but never carry data (CLAUDE.md "Verify Wiring, Not Just Existence"). Affects `sidequest/server/views.py` (`party_member_from_character`). *Found by TEA during test design.*
- **Question** (non-blocking): the story header scopes 102-6 to `server,content`, but the player-facing Effort/Strain legibility (Sebastien/Jade rubric) ultimately needs a UI change to RENDER the new `PartyMember` fields — a `sidequest-ui` repo touch that is out of the declared scope. The server-side protocol+projection is in scope; the UI render is not. Flagging to SM: either accept the server fields landing now (UI render as a follow-on) or expand scope to include ui. *Found by TEA during test design.*

### Dev (implementation)
- **Chargen does NOT yet seed a psionic Effort pool for a Psychic class** (Gap, non-blocking): the engine, dispatch, persistence, and projection are all live and the space_opera discipline catalog loads, but no chargen seam gives a PC a `core.effort["psionic"]` pool. Until that lands (the 90-7 `wwn.magic_hydrated` hydration extended to psionics — TEA's `seed_system_strain` finding is the sibling), the free-text discipline route's `any(c.core.effort ...)` guard is never satisfied in real play, so psionics is wired-but-dormant end-to-end (exactly the state `road_warrior` rig combat was in). The tests prove the spine by seeding the pool directly. Affects `sidequest/game/builder.py` (a `seed_psionic_effort` seam + a Psychic class/`magic_access` marker in space_opera `classes.yaml`). *Found by Dev during implementation.*
- **Standalone pack-validator rule for the discipline catalog deferred** (Improvement, non-blocking): AC4's structural validation (duplicate-id rejection, `extra="forbid"` unknown-field rejection, `yaml.safe_load`) is enforced at MODEL LOAD — `load_psionic_discipline_catalog` fails loud, and the genre/world loader hooks raise `GenreLoadError` on a malformed file (so a bad catalog fails the whole pack load). A dedicated `cli/validate` pass adds no new invariant here (unlike WWN's `_validate_wwn_starting_prepared_refs`, psionic disciplines have no class-`starting_prepared` cross-reference to check). Affects `sidequest/cli/validate` (a discipline-catalog rule could be added if a future cross-reference appears). *Found by Dev during implementation.*
- **heavy_metal (WWN) discipline catalog NOT authored** (Gap, non-blocking): scope lists "the WWN-bound packs that want them (heavy_metal at minimum)"; the engine + AC3 strain-unity path are proven on the wwn config in tests, and the loader hook reads `disciplines_psionic.yaml` for any pack, but only the space_opera (SWN) catalog is authored this story. heavy_metal psionics is a content add when that table wants it. Affects `sidequest-content/genre_packs/heavy_metal/`. *Found by Dev during implementation.*

### Dev (rework — Round-Trip 1, addressing the Reviewer HIGH finding)
- **Fixed the SWN strain-discipline AttributeError + Effort loss** (blocking HIGH → resolved):
  - Spec source: Reviewer Assessment HIGH finding + the SWN-Effort-only design scoping
  - Implementation: (1) `activate_discipline` (swn.py) now checks the strain precondition `strain_cost > 0 and core.system_strain is None` BEFORE committing any Effort — a strain push on a strainless core is a clean loud refusal (`applied=False`, reason set, pool untouched, `{slug}.discipline.activated refused=True` span), never a partial Effort spend and never an opaque AttributeError. When `system_strain` IS seeded (WWN/CWN/AWN), the push routes as before. (2) Content: removed `strain_cost` from the 5 SWN space_opera disciplines (dominate, kinetic_crush, ward_of_foresight, overcharge_working, long_jump) and reworded their `mechanical_effect` to drop the "take N System Strain" clause — SWN is Effort-only here; the push danger now lives in the fiction (genre_description) + a header comment documents the rule. (3) Added 3 regression tests (`TestStrainDisciplineOnStrainlessSwnCoreIsLoud`): refused-loud-without-spending-Effort, no-AttributeError, and a refused-discipline span with no effort.commit.
  - Verified (measured): `dominate` via `run_dispatch_bank` on a SWN psychic now → `bank.errors=[]`, Effort committed normally (3→2), narration directive emitted — was Effort-lost + swallowed AttributeError. The strainless-core guard refuses loudly (tested). 64/64 story tests + 3 skips; 626 ruleset/telemetry; 970 magic/dispatch/session — all green. ruff clean.
  - Severity: minor (the fix); Forward impact: a WWN heavy_metal catalog may still author strain_cost (the engine routes it); the homebrew-strain-on-strainless guard is now defensive across all packs.

### Reviewer (code review)
- **Gap** (blocking): a `strain_cost` discipline activated on a strainless SWN pack AttributeErrors after committing Effort — partial application + silent failure via the dispatch bank. Affects `sidequest/game/ruleset/swn.py` (`activate_discipline` must validate the strain precondition before any mutation and fail loud) AND `sidequest-content/genre_packs/space_opera/disciplines_psionic.yaml` (drop `strain_cost` from the 5 SWN disciplines — SWN is Effort-only here). *Found by Reviewer during code review.* (= the HIGH finding; this is the blocking rework item.)
- **Improvement** (non-blocking): `PsionicDiscipline.strain_cost` is a first-class schema field with no ruleset guard, so homebrew can author a strain discipline for any pack — including strainless ones — with no load-time warning. Consider a validator that rejects `strain_cost > 0` for a pack whose bound ruleset has no System Strain engine (or a clean runtime refusal). Affects `sidequest/genre/models/psionics.py` / pack validator. *Found by Reviewer during code review.*
- **Gap** (non-blocking): `cwn.effort.commit` / `awn.effort.commit` / `*.effort.reclaim` are unrouted — CwnRulesetModule/AwnRulesetModule inherit the lifted Effort engine but only swn+wwn effort routes are registered. No current caller (cwn/awn seed no Effort), so latent; register the routes (or document the exclusion) before cwn/awn ever gain Effort. Affects `sidequest/telemetry/spans/psionics.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Discipline-activation span asserted by structural shape, not an exact literal**
  - Spec source: context-story-102-6.md, AC1 + "Span set is named in the story"
  - Spec text: "plus discipline-activation spans consistent with `wwn.spell.cast`'s shape"
  - Implementation: tests assert a span whose name ends in `.discipline.activated` carrying `actor` + `discipline_id`, rather than pinning one literal string
  - Rationale: the story names the SHAPE, not the exact span name; a structural assert is refactor-stable and lets Dev pick the precise name (e.g. `swn.discipline.activated`) within the contract
  - Severity: minor
  - Forward impact: Dev should keep the `.discipline.activated` suffix + `discipline_id` attribute, or update these asserts
- **Effort engine asserted on the swn-resolved module (family-base lift), not a specific class**
  - Spec source: context-story-102-6.md, Technical Guardrails ("shared core in the family base, per-module catalogs")
  - Spec text: "Where SWN and WWN differ in discipline shape, the module seam differentiates — shared core in the family base"
  - Implementation: tests call `get_ruleset_module("swn").commit_effort(...)` and assert `swn.effort.commit`; they do NOT assert the method lives on `SwnRulesetModule` vs a shared mixin
  - Rationale: the `{ruleset}` span contract requires SWN to commit Effort; lifting the existing WWN engine to the family base (WwnRulesetModule already extends SwnRulesetModule) is the natural impl, but the behavioral assert survives either layout
  - Severity: minor
  - Forward impact: WWN backward-compat is guarded (`wwn.effort.commit` must still fire) — a shared base must not rename the wwn spans
- **AC4 authoring surface tested via inline tmp_path YAML, not an on-disk fixture pack**
  - Spec source: context-story-102-6.md, AC4
  - Spec text: "a new discipline added purely in pack YAML validates and is activatable ... synthetic fixture discipline in a test pack — code-shaped test"
  - Implementation: the discipline catalog is authored as an inline YAML string written to tmp_path and loaded via the catalog loader; activation is driven at the engine level (`activate_discipline`), not through a full on-disk genre pack
  - Rationale: project memory — tests must not point at live content, and a full valid pack adds load-surface unrelated to the authoring contract; the inline YAML proves "authored purely in YAML → validates → activatable" with less coupling. Real pack-catalog completeness is the pack VALIDATOR's job, not a unit test
  - Severity: minor
  - Forward impact: none — Dev still adds the loader hook + validator in `genre/loader.py` for the real packs
- **Net-new symbol names assumed by the suite (documented contract)**
  - Spec source: context-story-102-6.md, scope + the WWN spell-catalog/cast precedent
  - Spec text: "Reuse the cast spine and hydration ... discipline catalogs are content"
  - Implementation: tests reference `sidequest.genre.models.psionics.{PsionicDiscipline,PsionicDisciplineCatalog,load_psionic_discipline_catalog}`, `SwnRulesetModule.activate_discipline/commit_effort/reclaim_*`, `BeatSelection.discipline_id`, `GenrePack.psionic_discipline_catalog`, and `PartyMember.{effort_available,effort_committed,effort_max,system_strain_current,system_strain_max}` — all reached at call time so modules collect and RED is crisp
  - Rationale: each name is dictated by an existing parallel (`wwn_spell.py`, `spell_id`/`mutation_id` sidecars, `rig_composure_*` projection); naming them pins a coherent contract for Dev
  - Severity: minor
  - Forward impact: if Dev renames any symbol, the corresponding tests update in lockstep — behavior/spans are the durable contract
- **Player-facing projection: protocol fields tested RED, views.py population SKIPPED**
  - Spec source: context-story-102-6.md, guardrail #20 (Sebastien/Jade legibility)
  - Spec text: "Effort pool, committed/free, and Strain must be legible in player-facing surfaces (party panel / character sheet projection)"
  - Implementation: `PartyMember` field tests are live RED; the three `party_member_from_character` extraction tests are `pytest.skip` with explicit reasons (heavy handler/_SessionData fixture), mirroring the 53-5 rig_composure precedent
  - Rationale: the projection is a guardrail, not a numbered AC; the protocol-field RED pins the wire contract now, and the views.py wiring is called out as a blocking Delivery Finding so Dev does not leave the fields un-populated
  - Severity: minor
  - Forward impact: Dev must un-skip + implement the extraction (or the GREEN gate's wiring requirement is unmet)

### Dev (implementation)
- **Player-projection wiring: views.py extraction added; the 3 heavy-fixture extraction tests stay skipped (per the 53-5 precedent they mirror)**
  - Spec source: TEA Delivery Finding (blocking for the projection guardrail) + the 53-5 rig_composure precedent the tests cite
  - Spec text: "Dev MUST wire the views.py extraction in GREEN, not just add the fields"
  - Implementation: `party_member_from_character` (views.py) now extracts `effort_available/committed/max` (aggregated across `core.effort` pools) + `system_strain_current/max` and passes them to `PartyMember`. The 3 `TestEffortStrainExtraction` tests remain `pytest.skip` — IDENTICAL to the merged 53-5 `test_party_member_rig_composure.py`, whose 3 `TestPartyMemberRigPoolExtraction` tests are still skipped in production while the rig_composure extraction code is live in views.py.
  - Rationale: the TEA finding required the extraction CODE be wired (done — production path now populates the fields); the heavy handler/_SessionData fixture is the same lift 53-5 declined to build, and the precedent is to wire the code and leave the fixture-bound skips. The protocol-field tests (live RED→GREEN) pin the wire contract.
  - Severity: minor
  - Forward impact: a future fixture-infra story can un-skip both 53-5 and 102-6 extraction tests together; the extraction code is already exercised by every real PARTY_STATUS build.
- **Effort engine + `activate_discipline` lifted to `SwnRulesetModule` (the family base); spans namespaced by `self.slug`**
  - Spec source: context-story-102-6.md, Technical Guardrails ("shared core in the family base") + the `{ruleset}.effort.*` span contract
  - Spec text: "shared core in the family base, per-module catalogs"
  - Implementation: moved `commit_effort`/`reclaim_effort`/`reclaim_scene_effort`/`reclaim_day_and_refresh` from `WwnRulesetModule` to `SwnRulesetModule` and added `activate_discipline`. Emission moved to slug-parameterized `effort_commit_span`/`effort_reclaim_span`/`discipline_activated_span` (new `telemetry/spans/psionics.py`) so a swn-resolved commit reads `swn.effort.commit` and wwn stays `wwn.effort.commit` (backward-compat guard green). Deleted the now-dead `wwn_effort_commit_span`/`wwn_effort_reclaim_span` (kept their SPAN_WWN_EFFORT_* routes — the wwn-slug output still routes through them).
  - Rationale: the natural impl per the family-base directive; behavior/spans are the durable contract.
  - Severity: minor
  - Forward impact: none — `apply_system_strain`/`resolve_spellcast`/lethality stay wwn-only; cwn/awn inherit the Effort engine too (they extend SwnRulesetModule) but ship no discipline catalog, so it's dormant for them.
- **Pre-existing `test_wwn_effort.py::test_requires_wwn_config` updated to pin the broadened (SWN-family) contract**
  - Spec source: AC2 (`reclaim_day_and_refresh` must accept `SwnConfig()` — `test_swn_day_reclaim_drops_day_commitments_and_is_namespaced`)
  - Spec text: AC2 day-reclaim drives the swn-resolved module with `cfg=SwnConfig()`
  - Implementation: `reclaim_day_and_refresh` now guards `isinstance(cfg, SwnConfig)` (was `WwnConfig`) and reads `magic.day_reclaim_requires_comfort` via getattr (SwnConfig has no `magic` block). The old test asserted SwnConfig RAISES; renamed it `test_accepts_swn_family_config` to assert SwnConfig is now ACCEPTED and a non-config (None) still fails loud. This is a deliberate relaxation the AC requires, not a regression — the old invariant the test pinned is superseded.
  - Severity: minor
  - Forward impact: none — WWN backward-compat (the `wwn.effort.*` guards + the WwnConfig day-reclaim test) stays green.
- **Loader hook added (genre + world tier) so authored `disciplines_psionic.yaml` actually populates the catalog**
  - Spec source: TEA AC4 deviation forward impact ("Dev still adds the loader hook + validator in genre/loader.py for the real packs") + CLAUDE.md "Verify Wiring, Not Just Existence"
  - Spec text: AC4 — "a discipline added purely in pack YAML validates and is activatable with zero engine edits"
  - Implementation: `load_genre_pack` reads `disciplines_psionic.yaml` (genre tier) and `worlds/<slug>/disciplines_psionic.yaml` (world tier), OPTIONAL + uncoupled to classes (psionics is optional content); malformed → `GenreLoadError`. Authored a real SWN discipline catalog at the space_opera genre tier (16 disciplines, all six SWN skills, faithful mechanics) so the hook has a real consumer and the content scope is met. Resolver `resolve_psionic_discipline_catalog` mirrors `resolve_wwn_spell_catalog` (world-over-genre, no merge).
  - Rationale: the field would be dead without the disk source; the catalog makes the authoring surface real end-to-end (load → resolve → dispatch verified manually against the live pack).
  - Severity: minor
  - Forward impact: the catalog is content; future worlds/packs drop a `disciplines_psionic.yaml` with zero engine edits (the AC4 promise).

### Reviewer (audit)

Deviation stamps (TEA + Dev entries):
- **TEA: span asserted by structural shape** → ✓ ACCEPTED: the `.discipline.activated` suffix + `discipline_id`/`refused` attrs are honored by `discipline_activated_span`; refactor-stable.
- **TEA: Effort engine asserted on the swn-resolved module (family-base lift)** → ✓ ACCEPTED: the lift to `SwnRulesetModule` is the natural impl and the WWN backward-compat guard is green.
- **TEA: AC4 inline tmp_path YAML, not on-disk pack** → ✓ ACCEPTED: correct per project memory (tests must not point at live content); Dev added the real loader hook + content separately.
- **TEA: net-new symbol names** → ✓ ACCEPTED: names match the wwn_spell/spell_id precedents.
- **TEA: projection protocol fields RED, views.py population SKIPPED** → ✓ ACCEPTED with note: Dev wired the views.py extraction (verified); the skips stay per the 53-5 precedent — but see the [TEST] observation, the extraction should gain one passing test in the rework.
- **Dev: views.py extraction wired, 3 heavy-fixture skips stay (53-5 precedent)** → ✓ ACCEPTED: faithful to the cited precedent; extraction code present and correct.
- **Dev: Effort engine + activate_discipline lifted to SwnRulesetModule; spans namespaced by self.slug** → ✓ ACCEPTED (the lift itself is sound) — BUT the sub-claim about strain is FLAGGED below.
- **Dev: pre-existing test_requires_wwn_config updated to the broadened SWN-family contract** → ✓ ACCEPTED: AC2 deliberately broadens `reclaim_day_and_refresh` to `SwnConfig`; renaming the test to pin the new invariant (SwnConfig accepted, non-config rejected) is correct, not a regression.
- **Dev: loader hook (genre + world tier) + real space_opera catalog** → ✓ ACCEPTED on the hook/resolver mechanism; the AUTHORED CONTENT is FLAGGED below (strain_cost on SWN disciplines).

Flags:
- **Dev deviation "activate_discipline ... AttributeError here is the correct loud failure for a strain discipline authored on a strainless pack"** → ✗ FLAGGED by Reviewer: this reasoning is self-contradicted by the same PR. (1) An AttributeError swallowed by the dispatch bank is NOT "loud" — it produces Effort loss + zero span, the opposite of fail-loud. (2) Dev then SHIPPED exactly such content (5 `strain_cost` disciplines in the SWN space_opera catalog), so the "failure" fires on ordinary play, not just hypothetical homebrew. The engine must validate the strain precondition BEFORE committing Effort and refuse loudly; the SWN content must drop `strain_cost` (SWN is Effort-only here). See the HIGH finding.

### Reviewer (audit) — undocumented deviation
- **SWN content carries System Strain, which the SWN engine does not implement:** Spec/design scoping (TEA Question + Dev's own choice) is "SWN psionics = Effort-only; System Strain is WWN/CWN/AWN." The shipped `disciplines_psionic.yaml` (a SWN pack) authors `strain_cost: 1` on 5 disciplines — a divergence from that scoping that neither the content nor the engine reconciles. Severity: HIGH (it is the root of the HIGH finding).

**Implementation Complete:** Yes

**Files Changed (server — feat/102-6-psionics-swn-wwn-effort-strain):**
- `sidequest/genre/models/psionics.py` (NEW) — `PsionicDiscipline` + `PsionicDisciplineCatalog` (extra=forbid, dup-id reject, fail-loud `.get`) + `load_psionic_discipline_catalog` (yaml.safe_load) — AC4 model
- `sidequest/telemetry/spans/psionics.py` (NEW) — slug-namespaced `effort_commit_span`/`effort_reclaim_span` + `discipline_activated_span`; routes for swn.effort.commit/reclaim + swn/wwn.discipline.activated
- `sidequest/server/dispatch/psionic_discipline_resolve.py` (NEW) — world-over-genre catalog resolver
- `sidequest/game/ruleset/swn.py` — lifted Effort engine + `activate_discipline` to the family base
- `sidequest/game/ruleset/wwn.py` — removed the moved Effort methods (now inherited)
- `sidequest/game/wwn_magic.py` — `DisciplineActivationResult`
- `sidequest/telemetry/spans/wwn.py` — removed dead wwn_effort_*_span fns (kept routes)
- `sidequest/telemetry/spans/__init__.py` — re-export psionics spans
- `sidequest/genre/models/pack.py` — `psionic_discipline_catalog` on GenrePack + World
- `sidequest/genre/loader.py` — genre + world-tier disciplines_psionic.yaml load hook
- `sidequest/agents/subsystems/magic_working.py` — `_run_psionic_freeplay_activation` route + detection
- `sidequest/agents/orchestrator.py` — `BeatSelection.discipline_id` sidecar
- `sidequest/server/session.py` — `end_scene` Effort-reclaim gate broadened to the SwnRulesetModule family
- `sidequest/protocol/models.py` — PartyMember effort/strain projection fields
- `sidequest/server/views.py` — `party_member_from_character` effort/strain extraction
- `tests/game/ruleset/test_wwn_effort.py` — updated 1 pre-existing test to the broadened SWN-family contract

**Files Changed (content — feat/102-6-psionics-swn-wwn-effort-strain):**
- `genre_packs/space_opera/disciplines_psionic.yaml` (NEW) — 16-discipline faithful SWN psionic catalog

**Tests:** 35/35 passing + 3 intentional skips (heavy-fixture extraction, per 53-5 precedent) across the 6 story test files (102-6). Full server suite green (10353 passed; one psycopg-pool teardown flake at interpreter shutdown, confirmed not a regression — passes in isolation and in `tests/agents/`). Genre + integration suites green (1252) with content. `ruff check` + `ruff format --check` clean on all changed files.
**Branch:** feat/102-6-psionics-swn-wwn-effort-strain (server + content)

**Handoff:** To next phase (verify/review).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 3 (3 skips leave views.py extraction untested; 5 TEA test files have format drift; star-import noqa is convention-consistent) | confirmed 2 (coverage gap [TEST], format drift [LOW]), dismissed 1 (star-import is the established spans/__init__ convention) |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings (workflow.reviewer_subagents.edge_hunter=false) — edge analysis done by Reviewer directly (found the HIGH SWN+strain bug) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — silent-failure analysis done by Reviewer (the swallowed AttributeError + Effort loss is the headline finding) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — test-coverage gap (SWN+strain untested) found by Reviewer |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — no untrusted-input surface beyond the LLM-copied spell ref, which is length-capped + catalog-validated (verified) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — rule-by-rule done by Reviewer (see Rule Compliance) |

**All received:** Yes (1 enabled subagent returned; 8 disabled via settings, pre-filled per protocol)
**Total findings:** 4 confirmed (1 HIGH, 1 MEDIUM, 2 LOW/gap), 1 dismissed (with rationale), 1 deferred (latent cwn/awn span routing)

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | A strain-costing discipline activated on a SWN pack raises `AttributeError` (`SwnRulesetModule` has no `apply_system_strain`) AFTER `commit_effort` already spent the Effort — a partial application. In live dispatch the bank swallows it into `bank.errors`, so a player who types "I dominate the guard" on a space_opera psychic LOSES 1 Effort, fires NO discipline span, and gets no effect — the exact silent Illusionism the OTEL principle exists to catch. **Measured** (not asserted): `activate_discipline(dominate)` on a swn core → effort 3→2 then AttributeError; via `run_dispatch_bank` → `bank.errors=[('k1', AttributeError…)]`, effort left at 2. | `sidequest/game/ruleset/swn.py` `activate_discipline` (strain path unguarded + commits Effort before the strain call) + `genre_packs/space_opera/disciplines_psionic.yaml` (5 disciplines carry `strain_cost` though SWN is Effort-only here) | (1) Content: remove `strain_cost` from the SWN space_opera disciplines (dominate, kinetic_crush, ward_of_foresight, overcharge_working, long_jump) — SWN psionics is Effort-only in this codebase (no strain engine on SwnRulesetModule, no strain pool seeded for SWN PCs, no `SystemStrainConfig` on SwnConfig). The "push" stays prose-only. (2) Engine: `activate_discipline` must validate the strain precondition BEFORE committing Effort and fail LOUD (clear ValueError / clean refusal) when a `strain_cost` discipline is activated on a core with no `system_strain` pool — never a partial Effort spend, never an opaque AttributeError. (3) Add a regression test for the SWN+strain guard. |

**Data flow traced:** player free-text ("I dominate the guard") → IntentRouter → `magic_working` dispatch (`{actor, spell:"dominate"}`) → `_run_psionic_freeplay_activation` → `resolve_psionic_discipline_catalog` (genre tier, 16 disciplines) → `activate_discipline(dominate, cfg=SwnConfig)` → `commit_effort` (Effort 3→2, swn.effort.commit fires) → `strain_cost=1 > 0` → `self.apply_system_strain(...)` → **AttributeError** (no such method on SwnRulesetModule) → bank catches + logs `subsystems.dispatch_failed`. Net: Effort spent, no `swn.discipline.activated` span, no narration directive, working silently fails. UNSAFE.

**Pattern observed:** the dispatch route mirrors the 102-3 cast spine faithfully (`sidequest/agents/subsystems/magic_working.py:_run_psionic_freeplay_activation`) — good reuse, correct cast-before-psionic precedence, length-capped LLM ref, fail-loud unknown-discipline premise. The bug is upstream of the route, in the engine's strain handling + the content scoping.

**Error handling:** the `commit_effort` / `reclaim_*` paths fail loud correctly (missing pool → ValueError; over-commit → refused, recorded). The DEFECT is `activate_discipline`'s strain branch: it neither guards the precondition nor orders the mutation safely (commits Effort, THEN attempts strain), so a foreseeable content shape produces a partial mutation + opaque crash.

### Observations

- `[HIGH] SWN strain-discipline AttributeError + Effort loss` at `sidequest/game/ruleset/swn.py` (activate_discipline strain branch) + `disciplines_psionic.yaml` (5 strain_cost disciplines). Measured at unit AND dispatch level.
- `[MEDIUM] Partial-application ordering` at `sidequest/game/ruleset/swn.py` activate_discipline — Effort is committed before the strain call, so ANY strain failure (even a future legitimate one) leaves Effort spent. Precondition checks must precede the first mutation.
- `[TEST][MEDIUM] views.py effort/strain projection has no passing test` — the 3 `TestEffortStrainExtraction` skips leave `party_member_from_character`'s new extraction untested. The extraction code IS wired (verified at `views.py` — effort aggregated across `core.effort`, strain from `core.system_strain`), and this mirrors the merged 53-5 rig_composure precedent (whose extraction tests are also still skipped), so it is NOT a blocker on its own — but combined with the HIGH bug, the projection should get at least one passing extraction test in the rework.
- `[LOW][latent] cwn/awn Effort spans unrouted` — `commit_effort`/`reclaim_*` are inherited by CwnRulesetModule/AwnRulesetModule (they extend SwnRulesetModule), and emit `{self.slug}.effort.*`. Only `swn.effort.*` and `wwn.effort.*` routes are registered (`spans/psionics.py` + `spans/wwn.py`). If cwn/awn ever seed Effort, `cwn.effort.commit` / `awn.effort.commit` would be unrouted and miss the GM panel. No current caller (cwn/awn ship no discipline catalog and seed no Effort), so latent — deferred to a Delivery Finding, not a blocker.
- `[LOW] ruff format drift in 5 TEA test files` (per preflight) — `test_swn_psionics_effort_102_6.py` and 4 sibling story test files would reformat. These are TEA-authored, not Dev's; non-blocking (format is ungated) but worth a `ruff format` sweep in the rework while files are open.
- `[VERIFIED] WWN backward-compat preserved` — `wwn.effort.commit` still routes (`SPAN_WWN_EFFORT_COMMIT` + route kept in `spans/wwn.py:233`; the deleted `wwn_effort_*_span` fns were dead). `test_wwn_commit_still_emits_wwn_namespaced_span` green; the slug-parameterized `effort_commit_span(ruleset=self.slug)` yields `wwn.effort.commit` for WwnRulesetModule. Complies with the `{ruleset}` span contract.
- `[VERIFIED] Catalog fails loud` — `PsionicDisciplineCatalog.get` raises KeyError on unknown id (`genre/models/psionics.py`), `extra="forbid"` + the dup-id `model_validator` reject malformed content; `load_psionic_discipline_catalog` uses `yaml.safe_load` (rule #8). Loader hooks raise `GenreLoadError` on a bad file. Tested + measured (catalog loads OK, 16 disciplines).
- `[VERIFIED] Strain UNITY on WWN is correct` — `test_wwn_psionic_push_routes_strain_through_shared_counter` + `test_psionic_strain_and_lethality_strain_are_one_field_not_forked` green: on the WWN module a push routes through the one `core.system_strain` and emits `wwn.system_strain.delta` with a psionic source. The bug is strictly the SWN (strainless) side.

### Rule Compliance

Checked the lang-review `python.md` checklist + CLAUDE.md criticals against the diff:

- **#1 No silent fallbacks / silent exceptions** — VIOLATION (the HIGH finding): the strain AttributeError is swallowed by the dispatch bank and surfaces as Effort loss with no span — the canonical silent failure this rule + the OTEL principle forbid. All OTHER new code complies (commit/reclaim/catalog all fail loud).
- **#3 Type annotations at boundaries** — COMPLIANT: `load_psionic_discipline_catalog(path: str | Path) -> PsionicDisciplineCatalog`, `activate_discipline` / `_run_psionic_freeplay_activation` / `resolve_psionic_discipline_catalog` all annotated. Checked every new public fn.
- **#6 Test quality** — the 6 story files have meaningful asserts (no vacuous); but the SWN+strain edge is a MISSING case (the rule's "parametrized tests where all cases test the same path" cousin — strain only ever tested on WWN). Skips carry reasons (compliant with the skip-reason rule).
- **#8 Unsafe deserialization** — COMPLIANT: `yaml.safe_load` in the catalog loader; loader hooks reuse it.
- **#10 Import hygiene** — `from .psionics import *  # noqa` in `spans/__init__.py` matches the established per-domain convention (every span submodule); not novel debt. No new circular imports (swn.py→wwn_magic/psionics/spans are all leaf models). COMPLIANT.
- **#11 Input validation at boundaries** — COMPLIANT: the LLM-copied `spell` ref is length-capped (`_MAX_SPELL_REF_CHARS`) before the regex normalize + catalog scan, mirroring the cast spine; the typed ref rides `data` not the narrator directive (ADR-047 lane).
- **CLAUDE.md "Verify Wiring"** — the loader hook + resolver + dispatch route are wired end-to-end (measured: authored YAML → load_genre_pack → resolve → activate). The views.py extraction is wired but untested (the [TEST] observation).

### Devil's Advocate

Argue this code is broken. The headline is already proven: a stressed, ordinary player action — "I dominate the guard's mind", the single most genre-obvious psychic verb — detonates on the marquee SWN world this story ships for. It is not a contrived input; it is the FIRST thing a mechanics-first player (Sebastien, Jade — the exact audience this story names) will type, and it costs them Effort for nothing while the GM panel shows a dispatch error instead of a discipline span. The story's own purpose ("legible crunch the mechanics-first players want") is inverted: the crunch lies. Worse, the failure mode is the precise anti-pattern SOUL + the OTEL principle were written to forbid — a subsystem that spends a resource and emits no truthful span, leaving Claude free to narrate a domination that the engine never performed. A confused player re-reads their Effort pool (now 2/3) and cannot tell why; a careful one files a bug; a forgiving one assumes the rules are mush. What else? Homebrew: Jade authors a SWN discipline with `strain_cost` (the schema ALLOWS it — `strain_cost` is a first-class field on `PsionicDiscipline` with no ruleset guard), and her pack AttributeErrors in play with zero load-time warning — the authoring surface (the load-bearing requirement of this very story) accepts content the engine cannot run. The latent cwn/awn span gap is the same class of trap waiting one story out. The dispatch detection (`any(c.core.effort ...)`) is sound and the cast-before-psionic precedence holds, but none of that matters when the activation itself is a landmine. This is not a polish nit; it is a load-bearing path that fails on the most expected input, undetected by a green test suite because the SWN+strain pairing was never exercised. REJECT is the only honest verdict.

**Handoff:** Back to Fezzik (TEA) for a failing test (strain-costing discipline on a strainless SWN core must fail loud WITHOUT committing Effort), then to Inigo (Dev) for the engine guard + content fix.
---

## Subagent Results (Re-Review — Round-Trip 1)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 (B017 ×2 in the AC4 integration test; HIGH bug confirmed closed; content strain-free) | confirmed 1 (B017 gate failure [RULE]), dismissed 0; verified the HIGH fix |
| 2-9 | (all diff-based) | No | Skipped | disabled | Disabled via settings — re-review focus done by Reviewer directly |

**All received:** Yes (1 enabled subagent returned; 8 disabled per settings)
**Total findings:** 1 confirmed (gate-blocking lint), HIGH from Round-Trip 0 verified RESOLVED

## Reviewer Assessment (Re-Review — Round-Trip 1)

**Verdict:** REJECTED

The Round-Trip 0 HIGH bug is **RESOLVED and verified** (measured): `activate_discipline` now checks the strain precondition BEFORE any mutation — a strain push on a strainless SWN core refuses loudly (`applied=False`, pool untouched, `swn.discipline.activated refused=True` span), never a partial Effort spend, never an AttributeError. `dominate` via `run_dispatch_bank` → `bank.errors=[]`, Effort 3→2 normally, directive emitted. The WWN push path is intact (`test_wwn_psionic_push_routes_strain_through_shared_counter` green), 3 new SWN-guard regression tests pass, and the content is strain-free (all 16 disciplines `strain_cost=0`). Mutation ordering is correct (precondition → Effort commit → Strain apply, all inside the `applied` guard).

**But a NEW gate-blocking lint error remains:**

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] (gate-blocking) | `[RULE]` B017 "Do not assert blind exception: `Exception`" — `with pytest.raises(Exception):` is a project ruff `check` ERROR (pyproject selects `"B"` — flake8-bugbear). `uv run ruff check` (the `check-all`/`server-check` merge-gate command) reports 2 errors; the branch cannot merge. Pre-existing in TEA's AC4 test from RED; slipped through because the green-phase lint scoped to `sidequest/` + `test_wwn_effort.py` and never linted this file. | `tests/integration/test_psionics_authoring_surface_102_6.py:138` (`test_duplicate_discipline_id_rejected`) and `:164` (`test_unknown_discipline_field_rejected`) | Narrow both `pytest.raises(Exception)` → `pytest.raises(ValidationError)` (import `from pydantic import ValidationError`). Measured: both `load_psionic_discipline_catalog` failure paths (duplicate id, unknown field) raise `pydantic.ValidationError`, so the narrowed assert is exact and still proves the loud-rejection contract. Then re-run `uv run ruff check .` to confirm 0 errors. |

**Why this blocks (not a polish nit):** `check-all` is a hard merge prerequisite (SM runs it at finish). A branch with 2 `ruff check` errors fails that gate, so approving now would hand SM a broken finish. The fix is 2 lines + 1 import and does not weaken the tests (ValidationError is exactly what the loader raises).

Dispatch tags this pass: `[RULE]` (B017 lint gate). `[EDGE]`/`[SILENT]`/`[TEST]`/`[DOC]`/`[TYPE]`/`[SEC]`/`[SIMPLE]` — diff-based subagents disabled via settings; Reviewer's direct re-review found no new correctness/silent-failure/edge issues beyond the lint gate, and re-confirmed the Round-Trip 0 HIGH is closed.

**Handoff:** Back to Inigo (Dev) for the 2-line B017 narrowing (green rework — lint gate, no logic change).

### Reviewer (audit) — Re-Review (Round-Trip 1)
- **Round-Trip 0 flag "AttributeError is the correct loud failure ... [shipped strain content fires it in play]"** → ✓ RESOLVED by the rework: the engine guard makes the refusal atomic + loud, and the SWN content dropped `strain_cost`. Verified by measurement + 3 regression tests.
- **New finding:** B017 ×2 (gate-blocking lint) — see the severity table above. Not a spec deviation; a lint-gate failure that must clear before merge.
### Dev (rework — Round-Trip 2, addressing the B017 gate finding)
- **Fixed B017** (gate-blocking → resolved): narrowed both `pytest.raises(Exception)` → `pytest.raises(ValidationError)` (imported `from pydantic import ValidationError`) in `tests/integration/test_psionics_authoring_surface_102_6.py` (`test_duplicate_discipline_id_rejected`, `test_unknown_discipline_field_rejected`). Measured: both loader failure paths raise `pydantic.ValidationError`, so the narrowed asserts are exact and still prove the loud-rejection contract. `uv run ruff check .` now passes (0 errors, was 2); AC4 tests 6/6 green; full story suite 64 passed + 3 skipped. No logic change.
---

## Subagent Results (Final Re-Review — Round-Trip 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — ruff check 0 errors (B017 gone), story 64p/3s, regression 974p, AC4 narrowed tests pass |
| 2-9 | (all diff-based) | No | Skipped | disabled | Disabled via settings — final-pass delta was a 2-line lint narrowing, no new surface |

**All received:** Yes (1 enabled subagent returned clean; 8 disabled per settings)
**Total findings:** 0 — both prior rejection criteria (Round-Trip 0 HIGH, Round-Trip 1 B017) resolved + verified

## Reviewer Assessment

**Verdict:** APPROVED

Both rejection criteria are resolved and verified:
- **Round-Trip 0 HIGH (SWN strain AttributeError + Effort loss)** — `[SILENT]`/`[EDGE]` closed: `activate_discipline` checks the strain precondition before any mutation; a strain push on a strainless core refuses loudly (`applied=False`, pool untouched, `swn.discipline.activated refused=True` span), never partial, never AttributeError. Measured clean at unit + dispatch level; WWN push path intact; 3 regression tests green; SWN content is Effort-only (all 16 disciplines `strain_cost=0`).
- **Round-Trip 1 B017 (blind-except in AC4 test)** — `[RULE]` closed: both `pytest.raises(Exception)` narrowed to `pytest.raises(ValidationError)` (the exact type both loader failure paths raise). `uv run ruff check .` passes (0 errors); the AC4 tests still prove the loud-rejection contract.

**Data flow traced:** player free-text → IntentRouter → `magic_working` dispatch → `_run_psionic_freeplay_activation` → `resolve_psionic_discipline_catalog` → `activate_discipline` → `commit_effort` (`{slug}.effort.commit`) + `{slug}.discipline.activated`; scene/day boundaries reclaim via `Session.end_scene` (SwnRulesetModule family gate) → `{slug}.effort.reclaim`. Strain pushes (WWN/CWN/AWN only) route through the one `core.system_strain` counter → `wwn.system_strain.delta`. Effort + Strain round-trip in the production JSON encoding. Every decision emits a span (OTEL lie-detector satisfied).

**Pattern observed:** the psionic spine faithfully reuses the 102-3 cast-dispatch shape (`sidequest/agents/subsystems/magic_working.py`) with correct cast-before-psionic precedence, length-capped LLM ref, and fail-loud unknown-discipline premise — no parallel "psionics dispatch" was built. The Effort engine lift to `SwnRulesetModule` keeps WWN backward-compat (`wwn.effort.commit` still routes). Slug-namespaced spans + the loader hook (genre+world tier) + the world-over-genre resolver mirror the established `wwn_spell` conventions.

**Error handling:** commit/reclaim/catalog/activation all fail loud (ValueError on missing pool, refused-with-reason on over-commit, KeyError on unknown id, `extra="forbid"` + dup-id `ValidationError` at load, loud refusal on strain-without-pool). No silent fallbacks.

Dispatch tags this story: `[SILENT]` (strain AttributeError — fixed), `[EDGE]` (SWN+strain boundary — fixed + tested), `[RULE]` (B017 — fixed), `[TEST]` (views.py extraction coverage gap — accepted per the 53-5 precedent, extraction code verified wired), `[DOC]`/`[TYPE]`/`[SEC]`/`[SIMPLE]` — no findings (diff-based subagents disabled; Reviewer's direct passes found nothing further). Deferred non-blocking: latent cwn/awn Effort span routing (no current caller — Delivery Finding).

**Handoff:** To Vizzini (SM) for finish-story (PR creation + merge to develop on both server + content).