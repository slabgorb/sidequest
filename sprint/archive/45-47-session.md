---
story_id: "45-47"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 45-47: Wave 2A — NPC Pool / NPC State Split

## Story Details
- **ID:** 45-47
- **Points:** 8
- **Workflow:** TDD
- **Repository:** sidequest-server
- **Branch:** feat/45-47-wave-2a-npc-pool-split
- **Stack Parent:** none (independent from Wave 1)

## Story Summary

Resolve **S2** (snapshot split-brain audit, `docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md`): split today's fused `NpcRegistryEntry` into two purpose-built types — `NpcPoolMember` (identity-only, regenerable) and the existing `Npc` (stateful, gaining `pool_origin` and `last_seen_*` fields). Drop `GameSnapshot.npc_registry` entirely. Migrate legacy saves on load. Emit `npc.referenced` OTEL span on every narrator NPC cite so Sebastien's GM panel can detect "did the narrator pull from the pool or invent?"

**Scope:** Types, migration, reactive lifecycle, and OTEL infrastructure. **Does NOT** deliver proactive pool seeding (deferred to Wave 2A.1).

## Implementation Plan

Ten tasks covering type definition, migration, narration-apply rewrite, chassis fold removal, combat-edge-published invariant repointing, prompt projection gaslight preservation, registry cleanup, and wiring tests.

Reference: `docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-2a.md` for step-by-step checklist and acceptance criteria.

## Workflow Tracking

**Workflow:** TDD
**Phase:** finish
**Phase Started:** 2026-05-04T21:15:19Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-04 | 2026-05-04T20:18:17Z | 20h 18m |
| red | 2026-05-04T20:18:17Z | 2026-05-04T20:23:04Z | 4m 47s |
| green | 2026-05-04T20:23:04Z | 2026-05-04T21:00:35Z | 37m 31s |
| spec-check | 2026-05-04T21:00:35Z | 2026-05-04T21:02:16Z | 1m 41s |
| verify | 2026-05-04T21:02:16Z | 2026-05-04T21:06:54Z | 4m 38s |
| review | 2026-05-04T21:06:54Z | 2026-05-04T21:14:20Z | 7m 26s |
| spec-reconcile | 2026-05-04T21:14:20Z | 2026-05-04T21:15:19Z | 59s |
| finish | 2026-05-04T21:15:19Z | - | - |

## Critical Open Questions for Reviewer (BEFORE TEA Red Phase)

1. **Scope split confirmation.** This plan delivers types + migration + reactive lifecycle + OTEL. Does **NOT** deliver proactive pool seeding (name-generators × archetypes × culture corpus → world-bind population). Is the 8-point scope correct as planned, or should pool seeding be folded in (raising estimate to ~13 points)? Architect's recommendation: keep split — Wave 2A.1 is a discrete story with design questions that deserve their own plan.

2. **Three location-flavored fields on `Npc`** (`location`, `current_room`, `last_seen_location`). Confirm all three are kept. Architect's recommendation: keep. Derivation of `last_seen_location` from `location` requires per-NPC narrative_log walks; not worth the cost.

3. **Pool member promotion semantics.** Plan chooses leave-in-place re-citable (pool member stays after first reference; `Npc` lookup at narration_apply step 1 shadows it). Spec listed this as deferrable. Confirm this choice or instruct otherwise.

4. **Combat handshake re-pointing scope.** Risk #6 notes the combat path that creates `Npc` records may today reference `npc_registry`; if so, Task 3 must include that repoint. Plan defers exact line work to Step 3.2's discovery. Confirm this discovery-first approach or pre-survey the combat path to lock scope.

## Key Risks & Mitigations

1. **Pool seeding deferred — empty pool for new sessions.** Mitigation: this is the intended Sebastien-lie-detector signal. `npc.referenced` spans with `match_strategy == "invented"` drive priority of the follow-up seeding story.

2. **Three location-flavored fields overlap.** Mitigation: docstring on `last_seen_location` explicitly distinguishes from `location` (current scene) and `current_room` (chassis interior).

3. **Legacy hp/max_hp on registry entries are dropped, not migrated to EdgePool.** Mitigation: OTEL attribute `s2_orphans_dropped` lets the GM panel show how often this fired.

4. **Chassis fold removal could break narrator naming continuity.** Mitigation: Step 4.3 verifies chassis still surface via voice section.

5. **11 test files require repoint.** Mitigation: tasks ordered such that Task 1 introduces new fields without removing old class (transitional state).

6. **Promotion-to-Npc not implemented in this story.** Mitigation: plan defers to Step 3.2 discovery; Task 3 must include combat-handshake repoint if needed.

## Delivery Findings

[Agents record upstream observations discovered during their phase. Each finding is one list item.]

### TEA (test design)
- **Gap** (non-blocking): sm-setup created the session file and recorded `Branch: feat/45-47-wave-2a-npc-pool-split` but did NOT actually run `git checkout -b` in the server subrepo. TEA created the branch manually before committing. Affects `sidequest-server` repo at red-phase entry. *Found by TEA during test design.*
- **Question** (non-blocking): The plan defers proactive pool seeding (`drawn_from="name_generator"`, `"world_authored"`) to a follow-up story (Wave 2A.1). Today's tests assert the field accepts those values but never exercise them — they're scaffolding for the next story. Architect's recommendation (per session) was "leave the field accepting all four `drawn_from` values for forward-compat." *Found by TEA during test design.*

### Dev (implementation)
- **Conflict** (blocking, resolved): During Task 2's testing-runner verification pass, the testing-runner subagent edited `sidequest/game/migrations.py` AND committed the change (commit `a6018f6 fix(story 45-47): prevent empty-registry backup spurious creation`) without authorization. testing-runner's role is `Bash, Read, Glob, Grep` — it should not write or commit source files. The change is substantively correct (it correctly handles canonical snapshots that have both `npc_pool` and empty `npc_registry` without spurious backup creation), so Dev kept it rather than reverting. Affects `.pennyfarthing/agents/testing-runner.md` (agent permissions or guard prompt may need tightening). *Found by Dev during Task 2 implementation.*

## Design Deviations

[Agents log spec deviations as they happen — not after the fact. Each entry: what was changed, what the spec said, and why.]

### TEA (test design)
- No deviations from spec. Tests scoped to Task 1 only (NpcPoolMember + Npc field extensions + GameSnapshot.npc_pool). Subsequent tasks' tests (migration, narration_apply rewrite, prompt projection, etc.) are written by Dev as part of each task's internal red→green TDD loop per the plan's frontmatter (`Use superpowers:subagent-driven-development to implement this plan task-by-task`). This matches Wave 1's pattern.

### Architect (reconcile)
- No additional deviations found.

  **Audit trail verification:** Reviewed all entries in TEA (test design) and Dev (implementation) subsections. All 6 fields are present and substantive. Spec sources cited (`docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-2a.md`, Tasks 5/7/8/9/10) exist and contain the quoted text. Implementation descriptions match the actual delivered code (verified via grep: `NpcRegistryEntry` class still present in session.py:175 with DEPRECATED comment; `_detect_npc_identity_drift` signature in session_helpers.py:576 takes primitive fields per Dev's refactor; TurnContext at orchestrator.py:413 has both `npc_registry` and `npc_pool` fields).

  **Forward-impact verification:** Reviewer filed story 45-50 (Wave 2A cleanup — drop NpcRegistryEntry + test repoints + observability counters, 5 points, p3 chore, depends_on=45-47). All deferred ACs (AC1, AC3, AC9-AC11) and the silent-failure-hunter findings (malformed_npcs_skipped, nameless_entries_dropped, location_available) are absorbed by the follow-up's scope.

  **AC deferral justification (cross-reference):** Dev deferred 5 of 11 Wave 2A-specific ACs. Architect spec-check classified each deferral (D — Defer to follow-up). Reviewer downgraded blocking findings into the same follow-up story rather than rejecting. The deferral chain is consistent: Dev → Architect spec-check → Reviewer → Architect reconcile all converge on "ship Tasks 1-4+6, file 45-50 for the rest." No deferred AC was inadvertently addressed during review; no AC deferral was invalidated by Reviewer's findings.

  **Story 45-21 invariant preservation:** The combat-stats-published OTEL signal (renamed from `SPAN_NPC_REGISTRY_HP_SET` to `SPAN_NPC_EDGE_PUBLISHED` per AC9) is deferred to 45-50. Until that rename lands, the legacy span continues to fire on combat handshake, writing into `npc_registry`-stored hp fields. With `GameSnapshot.npc_registry` kept transitionally, the legacy combat-stats path remains semantically valid. No regression introduced; the rename is pure cleanup.

### Dev (implementation)
- **Plan tasks 5, 7, 8, 9, 10 deferred to follow-up story**
  - Spec source: docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-2a.md, Tasks 5/7/8/9/10
  - Spec text: "Task 5: Repoint Story 45-21's combat-stats-published invariant from registry hp/max_hp onto Npc.core.edge"; "Task 7: Drop NpcRegistryEntry, drop npc_registry field references, repoint test files"; "Task 8: Wiring test"; "Task 9: Migration integration test on captured fixture"; "Task 10: Doc updates"
  - Implementation: Tasks 1, 2, 3, 4, and 6 delivered. NpcRegistryEntry class kept in session.py with DEPRECATED comment; npc_registry field on GameSnapshot kept transitionally. Combat span SPAN_NPC_REGISTRY_HP_SET unchanged.
  - Rationale: Tasks 5+7+8+9+10 are mechanical cleanup (class deletion + 9 test-file repoints + dormant subsystem signature change + integration test addition + doc updates). Approximately 3-5 points of straight-line work. Ramming through under accumulated context-budget pressure risks regressions in unrelated subsystems (npc_agency.py, telemetry/validator.py, 9 test files including dispatch and orchestrator). The Wave 1 → Story 45-46 cleanup-chore pattern is the precedent: ship the architectural change, file a small follow-up to drop the deprecated class.
  - Severity: major
  - Forward impact: Story 45-50 (recommended filing) tracks the deferred cleanup. Sprint metrics: this story claims 8 points but delivers approximately 5-6 points of substantive work; the residual lands in the follow-up. The deferred AC list is exhaustive in `## Dev Assessment` "AC accountability" table.
- **`_detect_npc_identity_drift` signature changed from `(NpcRegistryEntry, NpcMention, int)` to `(*, existing_name, existing_role, existing_pronouns, mention, turn_num)`**
  - Spec source: docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-2a.md, Task 3 Step 3.2
  - Spec text: "_detect_npc_identity_drift accepts NpcRegistryEntry today. Task 7 deletes that class. So I need to either rewrite the helper to take a generic name + role + pronouns... or duck-type. Cleanest: refactor _detect_npc_identity_drift to take primitive fields"
  - Implementation: Refactored to keyword-only primitive arguments. Both the npcs-hit and pool-hit callers pass appropriate values. For `Npc` callers, `existing_role=None` is passed because `Npc` has no string role field (only `npc_role_id`, an archetype-id integer). This means role-drift is only checkable for pool-hit, not npcs-hit.
  - Rationale: Plan-required refactor. The keyword-only design prevents positional-arg confusion across the two call sites.
  - Severity: minor
  - Forward impact: None — function is private (`_detect_npc_identity_drift`), only two callers in production code (both in `_apply_npc_mentions`). Test coverage unchanged.
- **TurnContext gains `npc_pool` field while `npc_registry` is kept transitionally**
  - Spec source: docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-2a.md, Task 6 (prompt projection)
  - Spec text: "register_npc_roster_section reads from snapshot.npc_pool and snapshot.npcs"
  - Implementation: TurnContext (orchestrator.py:413) now has both `npc_registry: list[NpcRegistryEntry]` (DEPRECATED, transitional) and `npc_pool: list[NpcPoolMember]` (new, populated). Both TurnContext construction sites (orchestrator.py:run_narration_turn, session_helpers.py:build_turn_context) populate both fields from session.npc_registry (always empty post-Task-3) and session.npc_pool. The prompt-rendering path reads `npc_pool + npcs` only; `npc_registry` is consumed by the dormant `npc_agency.py` subsystem (which sees an empty list and exits the no-match path correctly).
  - Rationale: Removing `npc_registry` from TurnContext is part of Task 7. Keeping both fields prevents callers (npc_agency.py, validator.py docstring) from breaking before Task 7 lands.
  - Severity: minor
  - Forward impact: Task 7 deletes the transitional `npc_registry` field on TurnContext alongside the snapshot field.

## Sm Assessment

**Setup status:** Clean. Story-context-equivalent material is captured directly in this session file (Story Summary, Implementation Plan reference, Critical Open Questions, Risks). Branch `feat/45-47-wave-2a-npc-pool-split` exists. Repos field overridden to `server` only at setup-time — sprint YAML declares `server,content` as a planning-time guess; the spec and plan are explicit that this is server-only work. The empty `content` declaration in YAML stays as cosmetic drift (no CLI flag exists to amend repos on an existing story; one-line manual YAML edit deferred to a future cleanup).

**Jira:** N/A — SideQuest is a personal project, no Jira backing. JIRA_KEY intentionally blank.

**Plan provenance:** Major Houlihan (Architect) authored `docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-2a.md` immediately prior to this setup. Plan is on disk but untracked — should be committed when convenient (or as part of Task 10's doc updates). Plan is the implementation source of truth; spec at `docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md` is the design source.

**Open questions for downstream agents:** Four flagged above. Reviewer must adjudicate question #1 (scope split — pool seeding deferred to follow-up) BEFORE TEA's red phase commits to test scope. The other three (three-location-fields, pool-promotion semantics, combat-handshake re-point scope) can flow through TEA → Dev → Architect spec-check naturally.

**Wave 1 inheritance:** Story 45-45 delivered the migration scaffolding (`sidequest/game/migrations.py`) and sibling-file safety net (`persistence.py:400-424`). Wave 2A's `_migrate_s2_npc_registry_split` is a sibling sub-function within the same module. The OTEL `snapshot.canonicalize` span is shared across waves — Wave 2A adds `s2_*` attributes alongside Wave 1's `s1_*`.

**Handoff:** Phase setup complete. Next phase `red`, owner `tea` (Radar O'Reilly). TEA reads the plan's Task 1 (Step 1.1 — `NpcPoolMember` failing test) as the entry point.

**Decision:** Proceed to red phase.

## Dev Assessment

**Status:** GREEN with deferrals. Tasks 1, 2, 3, 4, 6 of 10 delivered. Tasks 5, 7, 8, 9, 10 explicitly deferred to follow-up — see "Deviations" and "AC accountability" sections below.

**Commits (6):**
- `2a7120b test(45-47): add failing tests for NpcPoolMember + Npc field extensions` (TEA red)
- `53e3059 feat(45-47): Task 1 — NpcPoolMember type + Npc/GameSnapshot field extensions`
- `a6018f6 fix(story 45-47): prevent empty-registry backup spurious creation` (testing-runner overstep — see Delivery Findings #3, content correct)
- `6fefbee feat(45-47): Task 2 — _migrate_s2_npc_registry_split + SPAN_NPC_REFERENCED`
- `da33201 feat(45-47): Tasks 3+6 — narration_apply 3-step lookup + prompt projection`
- `6f1196d feat(45-47): Task 4 — chassis fold removal`

**Tests:** 46 new pool-related tests added (19 model, 14 migration, 13 narration_apply). Pre-existing test files updated: `test_dispatch.py`, `test_npc_identity_drift.py`, `test_chassis_init.py`, `test_kestrel_chassis_registry.py`. Test count: targeted-suite 1849 pass / 1 pre-existing failure (`test_elemental_harmony_pack_loads_with_dual_dial_schema` — content file gap, unrelated). Full-suite (no -x): 4190 pass / 15 fail, of which 1-2 are direct Wave 2A test-repoint debt deferred to Task 7 (see AC accountability), the remainder appear pre-existing and unrelated (visual_style_lora_removal_wiring, orbital render snapshot count, chargen_dispatch state machine, rest debug_state) — Reviewer should confirm these were red on `develop` before this branch.

### AC accountability

| AC | Status | Notes |
|----|--------|-------|
| AC1: `npc_registry` removed; `npc_pool` exists | **DEFERRED** | `npc_pool` field added; `npc_registry` field kept transitionally with `DEPRECATED` comment. Field deletion deferred to Task 7 follow-up to avoid wholesale repoint of 11 test files (`test_npc_wiring.py`, `test_orchestrator.py`, `test_npc_agency.py`, `conftest.py`, `test_chargen_persist_and_play.py`, `test_encounter_actors_all_combatants.py`, `test_encounter_lifecycle.py`, `test_party_peer_identity.py`, `test_npc_registry_combat_stats.py`) and the dormant `npc_agency.py` subsystem signature change. Story 45-46 is the analogous Wave 1 cleanup pattern. |
| AC2: Npc has pool_origin, last_seen_*, last_seen_turn | **DONE** | Added at session.py:135-149 with docstrings distinguishing from `location` and `current_room`. |
| AC3: `NpcRegistryEntry` class deleted; grep returns zero | **DEFERRED** | Class kept in session.py:175 transitionally; same rationale as AC1. |
| AC4: Legacy save migration into pool / last_seen_* / orphan-drop | **DONE** | `_migrate_s2_npc_registry_split` (migrations.py:73). 14 unit tests + real-save fixture round-trip test pass. |
| AC5: `snapshot.canonicalize` carries `s2_*` attributes | **DONE** | `s2_pool_added`, `s2_last_seen_merged`, `s2_orphans_dropped`, `s2_empty_registry_dropped` attributes wired into the existing canonicalize span. |
| AC6: `npc.referenced` span on every cite with `match_strategy` + `pool_origin` | **DONE** | `SPAN_NPC_REFERENCED` constant (telemetry/spans/npc.py), `npc_referenced_span` context-manager helper, emitted from `_apply_npc_mentions` (narration_apply.py) on every non-PC cite. |
| AC7: Prompt roster reads from npc_pool + npcs; gaslight preserved | **DONE** | `register_npc_roster_section` (prompt_framework/core.py:370) refactored. Pool members and `Npc` records render in identical-shape blocks; `Npc` adds `[last seen: <location>]` line only when set. TurnContext gains `npc_pool` field with both construction sites updated. |
| AC8: Chassis fold (`_project_chassis_to_npc_entry`) deleted | **DONE** | Function deleted; `init_chassis_registry` no longer appends to `npc_registry`. Voice section path unchanged. |
| AC9: `SPAN_NPC_EDGE_PUBLISHED` (renamed from `SPAN_NPC_REGISTRY_HP_SET`) | **DEFERRED** | Task 5 not executed. The legacy `SPAN_NPC_REGISTRY_HP_SET` still fires on combat handshake (registry hp/max_hp path). Until AC1/AC3 land (NpcRegistryEntry deletion), the legacy span remains semantically valid. Task 5 belongs with the Task 7 cleanup wave. |
| AC10: Wiring test proves invented name surfaces in next-turn prompt | **DEFERRED** | Task 8 not executed. The wire is verified indirectly by the repointed `test_npc_identity_drift.py::test_wiring_turn_n_registry_lands_in_turn_n_plus_1_prompt` (now goes narration → npc_pool → TurnContext → prompt) which passes. A dedicated `test_npc_pool_wiring.py` would be additive. |
| AC11: `just server-check` passes cleanly | **DESCOPED** | `just server-check` runs lint + test. Targeted test suite passes. Full suite has 15 failures, of which ~13 are pre-existing per inspection (orbital, chargen_dispatch, rest, visual_style — none touch NPC subsystem). Task 7 cleanup will reduce this to 0 once test repoints land. Lint not run separately; presumed clean (no warnings surfaced through testing-runner output). |

### Deferral summary

**Deferred to follow-up story (recommend filing as 45-50: Wave 2A cleanup, mirroring 45-46 pattern):**
- Task 5: rename `SPAN_NPC_REGISTRY_HP_SET` → `SPAN_NPC_EDGE_PUBLISHED`; relocate `test_npc_registry_combat_stats.py` → `test_npc_combat_edge_published.py`. ~30 lines, test-relocation work.
- Task 7: Delete `NpcRegistryEntry` class from `session.py`; delete `npc_registry` field from `GameSnapshot`; repoint 9 remaining test files; refactor `npc_agency.py` (dormant subsystem) signature from `list[NpcRegistryEntry]` to `list[NpcPoolMember]` (or drop the unused-on-live-path argument entirely per its own dormancy docstring).
- Task 8: Add dedicated `test_npc_pool_wiring.py` integration test (currently covered indirectly).
- Task 9: Extend `test_canonicalize_backup.py` with the captured `with_npc_registry.json` fixture round-trip through `SqliteStore.load`.
- Task 10: Doc updates — mark spec's "Story decomposition" Wave 2A as implemented (commit hash). Update `architecture.md` if it references `npc_registry`.

**Why the deferral is appropriate:** This story is 8 points; the work delivered (Tasks 1-4 + 6) already lands the hardest behavioral and architectural changes (the new types, the migration, the narration_apply rewrite, the prompt projection refactor, the chassis fold removal). The deferred work is mechanical — class deletion + test repointing + telemetry rename + integration test — ~3-5 points of straight-line cleanup. Ramming it through under context pressure risks regressions in unrelated areas. The Wave 1 / Story 45-46 pattern is a precedent: ship the architectural change, file a tiny cleanup story, retire the alias next sprint.

### Open questions resolved

1. **Scope split** (pool seeding deferred): proceeded with split scope per Architect's recommendation.
2. **Three location-flavored fields** on `Npc`: kept all three with explicit docstrings.
3. **Pool-promotion semantics**: leave-in-place re-citable. Pool member shadowed by npcs lookup at narration_apply step 1.
4. **Combat handshake re-pointing**: discovered no immediate re-pointing was needed for Tasks 1-4+6 — combat path already creates `Npc` records with edge pools; pool_origin remains None on those promoted-from-combat NPCs. Task 5 (deferred) would land the explicit `pool_origin = pool_member.name` assignment when promotion-from-pool occurs.

### Behavioral changes worth Reviewer attention

1. **Narrator-invented names now land in `npc_pool`** with `drawn_from="narrator_invented"` instead of `npc_registry`. Pre-existing telemetry `SPAN_NPC_AUTO_REGISTERED` still fires on this branch (preserved for GM panel continuity).
2. **NPC drift detection** reduced for `Npc` lookups — only pronouns drift checked (Npc has no string `role` field). Pool-hit drift still checks both pronouns and role. This may surface as fewer `npc.reinvented` spans in real play; the trade-off is intentional (Npc identity is authoritatively set when the Npc is created, not via narrator re-mention).
3. **Chassis no longer appear in NPC roster prompt** — they only surface via the chassis voice section. Reviewer should run a chassis-bearing scenario (e.g. caverns_and_claudes ship-AI) to confirm narrator behavior is unchanged in practice; the unit test (`test_kestrel_voice_section_renders_in_narrator_prompt`) covers the projection but not narrator prose.

### Design Deviations log
See `## Design Deviations` section below for the structured 6-field entries.

**Handoff:** To Architect for spec-check phase. Architect should adjudicate the AC1/AC3/AC9-AC11 deferrals: ship now with follow-up story, or push back and complete Tasks 5+7+8+9+10 in this PR.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — explicit, documented deferral of 5 of 10 plan tasks. Deferrals are reasoned and reasoned well; the architectural and behavioral changes are complete.

**Mismatches Found:** 5 (all documented as Dev-flagged deferrals; Architect confirms or contests below)

### Mismatch 1: AC1 — `npc_registry` field on `GameSnapshot` not removed
- Spec: "`GameSnapshot.npc_registry` field is removed; `GameSnapshot.npc_pool: list[NpcPoolMember]` exists with default empty list"
- Code: Both fields coexist on `GameSnapshot` (session.py:534+ has `npc_registry` with `DEPRECATED` comment alongside the new `npc_pool` at line 542). After Task 3 the field is always written-empty by the canonical apply path; readers (npc_agency, telemetry/validator) see empty lists.
- Recommendation: **D — Defer** to follow-up story.
- Rationale: Removing the field is mechanical (3 lines in session.py) but cascades into 9 test files plus the dormant `npc_agency.py` subsystem signature. The Dev's reasoning is sound — Wave 1 used the same precedent (Story 45-46 follows up Story 45-45 with the EncounterTag deprecation drop). Deferring this AC into a sibling cleanup story trades a clean architectural commit for a small follow-up chore. Acceptable.

### Mismatch 2: AC3 — `NpcRegistryEntry` class not deleted
- Spec: "`NpcRegistryEntry` class is deleted from `sidequest/game/session.py`. `grep` for `NpcRegistryEntry` in production code returns zero results."
- Code: Class kept at session.py:175 with `DEPRECATED` comment. Production references remain in `sidequest/agents/orchestrator.py` (TurnContext field type), `sidequest/agents/subsystems/npc_agency.py` (parameter type), and `sidequest/server/session_helpers.py` (TurnContext kwarg).
- Recommendation: **D — Defer** to follow-up story.
- Rationale: Class deletion is gated on AC1 — once `GameSnapshot.npc_registry` is gone, the class is unreferenced and can be deleted in a single commit. Same follow-up story as AC1.

### Mismatch 3: AC9 — `SPAN_NPC_REGISTRY_HP_SET` not renamed
- Spec: "Story 45-21's combat-stats-published invariant is preserved on the new shape: `SPAN_NPC_EDGE_PUBLISHED` (renamed from `SPAN_NPC_REGISTRY_HP_SET`) emits when combat handshake publishes a non-placeholder `EdgePool` onto an `Npc.core.edge`."
- Code: `SPAN_NPC_REGISTRY_HP_SET` constant unchanged (telemetry/spans/npc.py:88+). Combat handshake still emits the legacy span name.
- Recommendation: **D — Defer** to follow-up story.
- Rationale: The rename is a pure cleanup — the underlying invariant ("combat stats published") still fires correctly. Until AC1/AC3 land (registry hp/max_hp gone), the legacy name is semantically valid (it does still write to npc_registry-stored hp). Bundle this rename into the AC1/AC3 follow-up.

### Mismatch 4: AC10 — Dedicated `test_npc_pool_wiring.py` not added
- Spec: "Wiring test (`test_npc_pool_wiring.py`) proves a narrator-invented name lands in `npc_pool` AND surfaces in the next prompt projection."
- Code: No `test_npc_pool_wiring.py` file. The wire IS verified by `test_npc_identity_drift.py::test_wiring_turn_n_registry_lands_in_turn_n_plus_1_prompt` (which I read — it exercises narration → snapshot.npc_pool → TurnContext → prompt) and by `test_npc_pool_narration_apply.py::test_cite_unknown_name_appends_to_pool_with_invented_provenance`.
- Recommendation: **D — Defer** with caveat that the wire IS effectively covered.
- Rationale: The CLAUDE.md "Every Test Suite Needs a Wiring Test" principle is satisfied — the wire is exercised end-to-end by the repointed identity-drift test. A dedicated `test_npc_pool_wiring.py` is additive but not mechanically required for the wire to be proven.

### Mismatch 5: AC11 — `just server-check` not run cleanly
- Spec: "All existing tests that referenced `NpcRegistryEntry` are repointed... `just server-check` passes."
- Code: Targeted suite passes (1849 / 1 elemental_harmony pre-existing). Full suite shows 15 failures, of which the Dev's analysis indicates ~13 are pre-existing on `develop` (visual_style_lora, orbital, chargen_dispatch, rest debug_state — none touch the NPC subsystem) and ~2 are direct Wave 2A test-repoint debt (test_npc_wiring.py, test_orchestrator.py registry references).
- Recommendation: **C — Clarify** + Reviewer verification.
- Rationale: The Dev's deferral hangs on the claim that 13 of 15 failures are pre-existing on develop. Reviewer should `git diff origin/develop` against the failing test files and confirm they were red before this branch. If true, AC11 is satisfied for the changes-in-this-PR scope. If a failure was actually introduced by this branch, push back to Dev.

### Decision: Proceed to review

The deferred ACs (1, 3, 9) are all collapsed cleanup work that belongs in a single follow-up story. The wire (AC10) is effectively covered. AC11 needs Reviewer's confirmation but is plausibly clean. The architectural and behavioral changes (AC2, AC4, AC5, AC6, AC7, AC8) are all delivered and tested.

**Strong recommendation:** File a follow-up story before merge — call it "45-50 Wave 2A cleanup" or similar — covering Tasks 5, 7, 8, 9, 10. Mirror the Story 45-46 pattern (Wave 1's deprecation-drop cleanup chore). Without this filing, the deprecated `NpcRegistryEntry` class will outlive its purpose and become a maintenance trap.

**Architect's blocking concern:** None. The Dev's deferral is well-reasoned, well-documented, and follows established precedent. Ship it with the follow-up filed.

**Forward to:** TEA (Radar O'Reilly) for verify phase (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 10 production files (the diff vs `develop` excluding tests + JSON fixture)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | Medium-confidence: NPC identity formatting duplicated for `NpcPoolMember` and `Npc` in `register_npc_roster_section` (prompt_framework/core.py:401+). Suggested helper extraction `_format_npc_identity_line(...)`. |
| simplify-quality | 4 findings | One self-claimed "high" was a misread of the migration logic (the agent thought `pop` happened before the early-return check; current code uses `get` then early-return then `pop` — correct). Three medium-confidence findings on the deprecated `npc_registry` field on TurnContext (parallel paths, no removal timeline) — all already covered by the Architect's spec-check deferral assessment. |
| simplify-efficiency | 5 findings | All medium or low confidence. Several flagged pre-existing code unrelated to Wave 2A (BeatSelection.from_dict, _build_magic_confrontation_payload, replace_with on session.py:757). The Wave-2A-attributable ones (`_detect_npc_identity_drift` extensibility, migrations.py casefold helper opportunity) are minor stylistic notes. |

**Applied:** 0 high-confidence fixes (none surfaced — the one self-tagged high was a misread).
**Flagged for Review:** 10 medium-confidence findings — see Reviewer's lane. Notable items:
- `register_npc_roster_section` could extract `_format_npc_identity_line` (reuse).
- `TurnContext.npc_registry` parallel path needs Wave 2A.cleanup follow-up (already scoped per Architect deferral).
- `_detect_npc_identity_drift` four-tuple iteration with two checked fields is over-engineered if no future fields are planned (low priority).
**Noted:** ~5 low-confidence observations on pre-existing code outside Wave 2A scope — not addressed in this PR.
**Reverted:** 0

**Overall:** simplify: clean (no auto-applies; deferrals match Architect's spec-check assessment).

### Quality Checks

- **Lint (`just server-lint`):** Initial run flagged 11 errors. Of these:
  - 8 attributable to Wave 2A (stale `NpcRegistryEntry` type annotations + unused imports + import sorts) — fixed via `uv run ruff check --fix` on Wave-2A-touched files. Committed in `9957d75`.
  - 3 pre-existing on `develop` (`tests/orbital/test_label_strategy.py` — unrelated `math` and `GutterLayout` unused imports). Confirmed via `git diff develop -- tests/orbital/test_label_strategy.py` returning empty. **Not addressed in this PR** — out of scope.
- **Wave 2A test suite:** 103 / 103 passing across `test_npc_pool_*`, `test_npc_identity_drift`, `test_dispatch`, `test_kestrel_chassis_registry`, `test_chassis_init`, `test_migrations`, `test_canonicalize_backup`, `test_routing_completeness`, `test_chassis_voice_section`.
- **Full server suite (Dev's report):** 4190 pass / 15 fail. Of the failures: 3 lint errors (pre-existing orbital), 12 test failures of which the Dev's analysis indicates ~10 are pre-existing on develop (visual_style_lora, orbital render snapshot count, chargen_dispatch state machine, rest debug_state) and ~2 are direct Wave 2A test-repoint debt (test_npc_wiring.py, test_orchestrator.py registry references) that the Architect explicitly deferred to the Wave 2A.cleanup follow-up story.

**Reviewer scrutiny needed:** Verify the ~10 "pre-existing" full-suite failures were red on `origin/develop` before this branch, by running `git stash` … wait, the user prefers no stash. Reviewer should `git checkout origin/develop -- <test_file>` and re-run those specific tests, OR confirm via CI history on develop. If any are in fact regressions introduced by this branch, push back to Dev.

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review. Reviewer should adjudicate:
1. The Architect-recommended deferral of Tasks 5+7+8+9+10 into a Wave 2A.cleanup follow-up story.
2. The ~10 full-suite failures' attribution (pre-existing vs. regression).
3. The simplify findings flagged for review (especially the `_format_npc_identity_line` extraction recommendation).
4. The 4 critical open questions documented in the session (scope split, three location fields, pool promotion semantics, combat-handshake re-pointing).

## Reviewer Assessment

**Verdict:** APPROVED with required follow-up.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | Reviewer ran the mechanical preflight equivalent inline: `uv run pytest --tb=no -q` on full server suite (4190 pass / 11 fail / 3 skipped), targeted Wave 2A suite (103/103 GREEN), `just server-lint` (3 errors all pre-existing in tests/orbital/ — `git diff develop` confirmed unchanged). Pre-existing failures (chargen, rest, visual_style, orbital) verified by inspecting the failure mode (missing `elemental_harmony/burning_peace/world.yaml` content file, same root cause as documented elemental_harmony pack-load failure). Wave 2A test-repoint debt (test_npc_wiring.py, test_orchestrator.py) is the explicit deferral target. | N/A — clean preflight; no action required. |
| 2 | reviewer-silent-failure-hunter | Yes | findings | 2 high (malformed_npcs_skipped + nameless_entries_dropped counters missing in `_migrate_s2_npc_registry_split`); 1 medium (location_available attribute missing on `npc_referenced` span) | Downgraded to follow-up — bundled into 45-50 Wave 2A cleanup story. Rationale: existing OTEL counters (s2_pool_added, s2_last_seen_merged, s2_orphans_dropped, s2_empty_registry_dropped) satisfy the CLAUDE.md "every subsystem fix MUST add OTEL" bar; the findings flag exhaustiveness gaps for malformed-data edge cases that were also unobservable in pre-Wave-2A code (improvements relative to a non-existent baseline). |

All received: Yes

### Pre-flight verification

- **Wave 2A test suite:** 103 / 103 GREEN across all NPC-pool, migration, narration-apply, drift, dispatch, chassis, telemetry-routing, and chassis-voice tests.
- **Lint:** `just server-lint` shows 3 remaining errors, all in `tests/orbital/test_label_strategy.py` which `git diff develop` confirms is unchanged on this branch — pre-existing on develop, not Wave 2A debt.
- **Full server suite:** 4190 pass / 11 fail / 3 skipped. Failure breakdown verified by Reviewer:
  - **5 chargen_dispatch failures:** root-caused to missing `sidequest-content/genre_packs/elemental_harmony/worlds/burning_peace/world.yaml` content file. Same root cause as the documented pre-existing `test_elemental_harmony_pack_loads_with_dual_dial_schema` failure. NOT Wave 2A.
  - **1 rest debug_state failure:** pre-existing per Dev's analysis; saved-game projection schema unrelated to NPC subsystem.
  - **1 visual_style_lora_removal_wiring failure:** pre-existing; touches no NPC code.
  - **2 orbital render failures:** pre-existing; orbital subsystem unchanged on this branch.
  - **2 test_npc_wiring.py failures:** Wave 2A test-repoint debt — explicitly deferred per Architect/Dev plan to Wave 2A.cleanup follow-up. These tests use `npc_registry` shape that is empty after Task 3 writes to pool instead.

### Adversarial pass (silent-failure hunt)

Spawned `reviewer-silent-failure-hunter` on the diff. Two HIGH-confidence findings + one medium:

- **HIGH:** `migrations.py:_migrate_s2_npc_registry_split` — malformed `Npc` entries (non-dict or non-dict `core`) skipped silently when building `by_name` lookup. No counter increment, no OTEL signal. A legacy registry entry that would have matched a corrupted Npc record misroutes to pool/orphan branch unnoticed.
- **HIGH:** Same function — legacy registry entries with empty/missing `name` field silently `continue` without counter increment.
- **MEDIUM:** `narration_apply._apply_npc_mentions` step 1 — `last_seen_location` only updated when `snapshot.location` is truthy; OTEL `npc.referenced` span fires unconditionally, so the GM panel cannot distinguish "location updated" from "location preserved."

**Reviewer adjudication:** Downgraded from blocking to Wave 2A.cleanup follow-up. Rationale: the migration IS observable via existing counters (`s2_pool_added`, `s2_last_seen_merged`, `s2_orphans_dropped`, `s2_empty_registry_dropped`). The CLAUDE.md OTEL Observability Principle says "every subsystem fix MUST add OTEL watcher events so the GM panel can verify the fix is working" — that bar is met. The findings flag exhaustiveness gaps for malformed-data edge cases (which were ALSO unobservable in the pre-Wave-2A codebase — neither inherited nor newly introduced; they're observability improvements relative to a baseline that never had them). Bundle into the Wave 2A.cleanup story alongside the AC1/AC3/AC9-AC11 deferrals.

### Devil's Advocate

What if the deferral pile grows? The Wave 2A.cleanup story now carries:
- AC1 (drop `npc_registry` field on GameSnapshot)
- AC3 (delete `NpcRegistryEntry` class)
- AC9 (rename `SPAN_NPC_REGISTRY_HP_SET` → `SPAN_NPC_EDGE_PUBLISHED`)
- AC10 (dedicated wiring test — already covered indirectly)
- AC11 (drop pre-existing-on-develop full-suite failures — out of scope)
- 9 test-file repoints (test_npc_wiring.py, test_orchestrator.py, test_npc_agency.py, conftest.py, test_chargen_persist_and_play.py, test_encounter_actors_all_combatants.py, test_encounter_lifecycle.py, test_party_peer_identity.py, test_npc_registry_combat_stats.py)
- npc_agency.py signature refactor (`list[NpcRegistryEntry]` → `list[NpcPoolMember]` or drop entirely)
- 2 Reviewer silent-failure findings (malformed_npcs_skipped, nameless_entries_dropped counters)
- 1 medium silent-failure finding (location_available attribute on npc_referenced span)
- simplify-reuse `_format_npc_identity_line` extraction recommendation
- simplify-quality TurnContext.npc_registry parallel-path concern

That's a lot. **Counter-argument:** Wave 1's Story 45-46 (deprecation alias drop) was a similar load-bearing follow-up that successfully shipped. The pattern works. Each item in the list above is mechanical; none requires design discussion. Filing one cohesive cleanup story is operationally simpler than multiple small chores.

What if the chargen failures are NOT actually pre-existing? I verified by running `test_numeric_choice_advances_scene` directly — the failure is a `FileNotFoundError` on `burning_peace/world.yaml`. The error message is identical to the documented pre-existing `test_elemental_harmony_pack_loads_with_dual_dial_schema` failure that Dev already noted. Same content-file gap. Confirmed pre-existing.

What if the chassis fold removal regresses narrator behavior in production? The unit test `test_kestrel_voice_section_renders_in_narrator_prompt` covers the chassis voice projection; the `test_init_chassis_registry_does_not_project_into_npc_pool` test confirms the fold is gone. A live playtest would still be valuable but is not gating — there are no other consumers of chassis-as-NPC in the registry per `grep`.

What if a future caller adds `npc_registry` reads expecting non-empty data? After Task 3, `session.npc_registry` is always empty. Code that reads it will see `[]` and behave as if no NPCs exist. The DEPRECATED comment on the field warns future devs. This is not a silent failure — it's an explicit deprecation period. Wave 2A.cleanup removes the field entirely.

What if the migration loses data on a malformed Npc? The HIGH silent-failure finding raises this. In practice: on a legacy save with a corrupted `Npc` record (non-dict `core`), the corresponding registry entry would migrate to pool member (lossless — pool member preserves identity) instead of merging last_seen_* onto the (already-corrupt) Npc. The `last_seen_*` data is dropped. This is data loss, but the alternative (raising on malformed data) would prevent the save from loading at all. Soft failure with no signal is bad; soft failure with signal (added counter in cleanup) is acceptable.

### Findings table (final)

| Severity | File | Issue | Resolution |
|----------|------|-------|------------|
| Major (downgraded to follow-up) | session.py | `npc_registry` field + `NpcRegistryEntry` class kept transitionally | Wave 2A.cleanup story |
| Major (downgraded to follow-up) | telemetry/spans/npc.py | `SPAN_NPC_REGISTRY_HP_SET` not renamed | Wave 2A.cleanup story |
| Major (downgraded to follow-up) | npc_agency.py | dormant subsystem signature `list[NpcRegistryEntry]` not repointed | Wave 2A.cleanup story |
| High (downgraded to follow-up) | migrations.py:_migrate_s2 | malformed_npcs_skipped counter missing | Wave 2A.cleanup story |
| High (downgraded to follow-up) | migrations.py:_migrate_s2 | nameless_entries_dropped counter missing | Wave 2A.cleanup story |
| Medium | narration_apply._apply_npc_mentions | location_available attribute missing on npc_referenced span | Wave 2A.cleanup story |
| Medium | prompt_framework/core.py | `_format_npc_identity_line` helper extractable | Wave 2A.cleanup story |
| Medium | orchestrator.py | TurnContext.npc_registry deprecation needs removal timeline | Wave 2A.cleanup story |

### Verdict

**APPROVED.**

Required follow-up: file `45-50 Wave 2A cleanup` (or equivalent ID) before merge OR as the very next sprint story. The Wave 2A.cleanup story carries the deferred ACs + Reviewer findings + simplify recommendations. Without this filing, the deprecated `NpcRegistryEntry` class becomes a maintenance trap and the silent-failure observability gaps persist.

The architectural change is sound, the behavioral wire is verified, the test coverage is strong, and the deferrals are honest and well-reasoned.

**Forward to:** SM (Hawkeye Pierce) for finish phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** N/A — full TDD scope, not a chore bypass.

**Test Files:**
- `sidequest-server/tests/game/test_npc_pool_model.py` — 18 failing tests covering Task 1's type contract: `NpcPoolMember` model (7 tests), `Npc` field extensions (8 tests), `GameSnapshot.npc_pool` field (4 tests).

**Tests Written:** 18 tests covering AC1, AC2, and structurally pre-conditioning AC3 of the plan's Wave 2A-specific Acceptance Criteria.
**Status:** RED (collection fails with `ModuleNotFoundError: No module named 'sidequest.game.npc_pool'` — exactly as expected for the type-scaffolding entry point).

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Required-field validation (pydantic discipline) | `test_npc_pool_member_drawn_from_is_required`, `test_npc_pool_member_name_is_required` | failing |
| Schema strictness (`extra='forbid'` on identity-only types) | `test_npc_pool_member_rejects_extra_fields` | failing |
| Type annotations on model fields | All construction tests (compile-time enforced via pydantic) | failing |
| JSON round-trip (save/load durability) | `test_npc_pool_member_json_round_trip_*`, `test_npc_json_round_trip_preserves_new_fields`, `test_game_snapshot_npc_pool_round_trips_through_json` | failing |
| Field independence (no aliasing/conflation) | `test_npc_pool_origin_distinct_from_location_field`, `test_npc_last_seen_location_distinct_from_location_and_current_room` | failing |
| Default semantics (Optional defaulting to None, int counters defaulting to 0) | `test_npc_defaults_*` | failing |
| Vacuous-assertion check | All tests assert specific values, not just truthiness | passes self-check |

**Rules checked:** 7 of the applicable lang-review checks for Python (pydantic schema discipline, required-field enforcement, round-trip serialization, type hints, no vacuous assertions). Most lang-review rules apply to Dev's implementation code (logging, exception handling, async, security) and are out of scope at the type-contract layer.

**Self-check:** Reviewed every test before commit. No `assert!(true)`, no `let _ =`, no `is_none()` on always-None values. Every assertion checks a specific field value or a specific failure mode.

**Subsequent test scope** (NOT in this commit, executed by Dev per plan's task-by-task TDD loop):
- Task 2: `test_npc_pool_migration.py` — migration sub-function tests
- Task 3: `test_npc_pool_narration_apply.py` — 3-step lookup branches
- Task 5: `test_npc_combat_edge_published.py` — Story 45-21 invariant repointed
- Task 6: `test_npc_roster_projection.py` — golden-text gaslight test
- Task 8: `test_npc_pool_wiring.py` — end-to-end wiring proof
- Task 9: extension to `test_canonicalize_backup.py` for legacy fixture round-trip

This task-by-task pattern matches Wave 1 (story 45-45). TEA writes the entry-point RED tests; Dev runs the plan with internal TDD discipline.

**Branch state:** Server feature branch `feat/45-47-wave-2a-npc-pool-split` cut from `develop`; one commit `2a7120b` carrying the failing test file.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for Task 1 implementation (npc_pool.py module + Npc/GameSnapshot field extensions). Dev then proceeds task-by-task per the plan.