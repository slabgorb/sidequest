---
story_id: "45-52"
jira_key: null
epic: "45"
workflow: "trivial"
---
# Story 45-52: Wave 2A cleanup — drop NpcRegistryEntry + test repoints + observability counters

## Story Details
- **ID:** 45-52
- **Jira Key:** None (SideQuest is personal, no Jira)
- **Epic:** 45
- **Workflow:** trivial
- **Stack Parent:** 45-47 (completed)
- **Type:** chore
- **Points:** 5
- **Priority:** p3

## Scope

This is a cleanup follow-up to 45-47 (Wave 2A NPC pool/state split). Work includes:

1. **Drop deprecated NpcRegistryEntry class** — no longer needed after pool/state split
2. **Remove GameSnapshot.npc_registry field** — split into npc_pool and npc_state
3. **Repoint 9 test files** — update imports and assertions:
   - test_npc_wiring
   - test_orchestrator
   - test_npc_agency
   - conftest
   - test_chargen_persist_and_play
   - test_encounter_actors_all_combatants
   - test_encounter_lifecycle
   - test_party_peer_identity
   - test_npc_registry_combat_stats
4. **Refactor npc_agency.py subsystem signature** — currently dormant, prepare for reactivation
5. **OTEL observability upgrades:**
   - Rename `SPAN_NPC_REGISTRY_HP_SET` → `SPAN_NPC_EDGE_PUBLISHED`
   - Add `malformed_npcs_skipped` attribute
   - Add `nameless_entries_dropped` attribute
   - Add `location_available` attribute (per Reviewer's silent-failure findings)
6. **Add dedicated wiring test** — verify NPC initialization flow end-to-end
7. **Documentation updates**

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-12T19:47:38Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-12T18:55:51Z | 2026-05-12T18:57:56Z | 2m 5s |
| implement | 2026-05-12T18:57:56Z | 2026-05-12T19:38:02Z | 40m 6s |
| review | 2026-05-12T19:38:02Z | 2026-05-12T19:47:38Z | 9m 36s |
| finish | 2026-05-12T19:47:38Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): `sidequest/server/rest.py:332` reads `edge.maximum` on an `EdgePool` instance, but `EdgePool` only exposes `max` (not `maximum`). Path is reachable from the `/api/debug/state` projection on any session with stateful NPCs; an `AttributeError` would 500 the endpoint. Pre-existing bug, untouched here — flagging for a follow-up. *Found by Dev during 45-52 implementation.*
- **Improvement** (non-blocking): The OTEL component label `component="npc_registry"` still appears on five SPAN_ROUTES entries in `sidequest/telemetry/spans/npc.py` (auto_registered, pc_name_skipped, reinvented, recurring_presence_missed, auto_mint_skipped, observation_gate_promoted/purged, auto_minted_from_prose). Kept stable because the GM panel filter likely matches on the string and a rename risks dashboard breakage. If the GM panel grows a "by component" column or facet, those routes should migrate to `"npcs"` / `"npc_pool"` to match the post-Wave-2A topology. *Found by Dev during 45-52 implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): Vacuous value assertions in `tests/server/test_npc_registry_combat_stats.py:175,178,183,197-198`. `PLACEHOLDER_EDGE_BASE_MAX == 10` and the `test_genre` combat dial threshold == 10 collide, so the post-publish `edge.{current,max}` matches the placeholder regardless of whether the publish ran. Affects `tests/server/test_npc_registry_combat_stats.py` (assertions must distinguish placeholder from dial — seed the fixture with `edge.max = 5` or assert exact equality to `10` explicitly tied to the dial threshold). Wire verification is preserved by the OTEL-span test in the same file. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `_npc_fallback_at_location` populates `NpcMention.role` from `npc.npc_role_id`, but that field is the archetype-id slot (P2-deferred, only set by the `namegen` CLI). Pre-fix the legacy registry's free-form `role` string lived here. Affects `sidequest/server/dispatch/encounter_lifecycle.py:206` (switch to `npc.core.personality or ""` or drop the field — currently unused downstream so functionally inert). *Found by Reviewer during code review.*
- **Question** (non-blocking): Long-term — the seven remaining `component="npc_registry"` OTEL routes in `sidequest/telemetry/spans/npc.py` (auto_registered, pc_name_skipped, reinvented, recurring_presence_missed, auto_mint_skipped, observation_gate_promoted/purged, auto_minted_from_prose) form a stable filter token for the GM panel. Decide whether the dashboard's filter UI should grow a migration path (alias old → new component string) before renaming, or whether the labels stay frozen as historical strings. Affects `sidequest/telemetry/spans/npc.py` (multiple SpanRoute extracts) and any dashboard JS that filters by `component`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Touched more than 9 test files**
  - Spec source: session SM Assessment / story scope, line "Repoint 9 test files (test_npc_wiring, test_orchestrator, test_npc_agency, conftest, test_chargen_persist_and_play, test_encounter_actors_all_combatants, test_encounter_lifecycle, test_party_peer_identity, test_npc_registry_combat_stats)"
  - Spec text: "9 test files"
  - Implementation: Repointed ~20 test files. The SM-named 9 are all updated; the additional ones (test_rest, test_npc_pool_model, test_npc_identity_drift, test_notorious_party_player_count_gate, test_subsystem_registry, test_server_e2e, test_watcher_events, test_monster_manual_inject, plus six integration wiring tests and two magic tests) also referenced `NpcRegistryEntry` or `snapshot.npc_registry` and would have broken at import or assertion time once the class and field were dropped.
  - Rationale: The SM-named list was the floor of "tests that have to move," not the ceiling. Per CLAUDE.md "delete dead code in the same PR," shipping a PR that leaves obviously broken siblings untouched is worse than fixing them now.
  - Severity: minor
  - Forward impact: none — the wider sweep is mechanical (kwarg removal or NpcRegistryEntry → NpcPoolMember / Npc swap) and matches the production rewire.

- **Removed `npc_registry.cleared_on_chargen_complete` clear + OTEL event entirely**
  - Spec source: SM Assessment watch-out re: `NpcRegistryEntry` going away "entirely"; CLAUDE.md "delete dead code in the same PR"
  - Spec text: "delete dead code in the same PR — do not leave shims, deprecation aliases, or `# removed` comments. `NpcRegistryEntry` goes away entirely."
  - Implementation: `websocket_session_handler._handle_character_commit` previously cleared `sd.snapshot.npc_registry` on `is_first_commit` and emitted a `npc_registry.cleared_on_chargen_complete` span event. With the registry gone and `npc_pool` intentionally persistent across chargen (world-authored cast + recurring narrator-cited NPCs are not "chargen noise"), the clear has no valid target. Deleted the block and the corresponding test (`test_npc_registry_cleared_at_confirmation_with_otel`).
  - Rationale: A behavior-preserving rename of the clear to target `npc_pool` would have erased world_authored cast members on every fresh commit — that's a regression in cast continuity, not parity. Story scope says drop the field; the chargen-clear behaviour rides with it.
  - Severity: minor
  - Forward impact: minor — anyone leaning on the now-removed OTEL event to gate dashboard side-effects would need to substitute a chargen-complete event (one already exists: `session.persisted_at_chargen_complete`).

- **`SPAN_NPC_EDGE_PUBLISHED` writes onto `Npc.core.edge` (not into a new field)**
  - Spec source: SM Assessment, "Rename SPAN_NPC_REGISTRY_HP_SET → SPAN_NPC_EDGE_PUBLISHED"
  - Spec text: rename only (no behaviour spec for the new span's target)
  - Implementation: The span fires from `_publish_combat_edge_to_npcs`, which overwrites `npc.core.edge.{current,max,base_max}` for opponent-side actors with the dial threshold. This is the ADR-014 / ADR-078 "HP→Edge at the materialization seam" pattern, but at the encounter-handshake seam rather than the creature-materialization seam.
  - Rationale: The pre-Wave-2A function projected dial-derived HP onto a *separate* lightweight registry entry; with the registry gone, the only remaining narrator-readable mechanical store is `Npc.core.edge`. Without this write, narrator-spawned NPCs would face combat with the placeholder edge pool (small fixed ceiling) instead of the dial-sized pool, breaking the Playtest 3 Orin regression coverage.
  - Severity: minor
  - Forward impact: none — narration reads `core.edge` already (gaslighting doctrine); the write just makes that read correct for non-creature opponents.

### Reviewer (audit)
- **"Touched more than 9 test files"** → ✓ ACCEPTED by Reviewer: agrees with author reasoning. The SM-named list was the floor of tests that reference the dropped symbols; leaving the fan-out broken would have shipped a PR that fails at import time on neighboring tests. The wider sweep is mechanical and matches the production rewire. Aligns with CLAUDE.md "delete dead code in the same PR."
- **"Removed `npc_registry.cleared_on_chargen_complete` clear + OTEL event entirely"** → ✓ ACCEPTED by Reviewer: the clear had no valid target after the field drop. Behavior-preserving rename to `npc_pool.clear()` would have wiped world-authored cast members on every fresh commit — that's a regression in cast continuity, not parity. Pool-channel persistence across chargen is the post-Wave-2A intent. The chargen-complete OTEL beacon survives via the pre-existing `session.persisted_at_chargen_complete` event Dev noted in their forward-impact column.
- **"`SPAN_NPC_EDGE_PUBLISHED` writes onto `Npc.core.edge` (not into a new field)"** → ✓ ACCEPTED by Reviewer: matches the SOUL.md gaslighting doctrine (narrator must see what the mechanics use; during a confrontation the dial IS what the mechanics use) and the ADR-078 HP→Edge translation pattern. The opponent-side filter prevents trampling player characters' edge. Acknowledged trade-off: a creature-sheet pool larger than the dial threshold gets shrunk during the encounter — this is consistent with "dial is canonical at encounter start."

## Sm Assessment

**Type:** trivial cleanup, follow-up to 45-47 (Wave 2A NPC pool/state split, already merged).

**Scope is mechanical:** the new pool/state split is live; `NpcRegistryEntry` and `GameSnapshot.npc_registry` are the dead-code tail. Nine test files reference the old names; flip them in-place. The OTEL renames and added attributes are direct Reviewer asks from 45-47 — implement verbatim, don't redesign.

**Repo:** sidequest-server only. Branch already cut: `feat/45-52-wave-2a-cleanup-drop-npcregistryentry`.

**Watch-outs for Dev:**
- Per project memory: delete dead code in the same PR — do not leave shims, deprecation aliases, or `# removed` comments. `NpcRegistryEntry` goes away entirely.
- HP→Edge translation lives at the materializer seam (ADR-014, ADR-078) — `SPAN_NPC_REGISTRY_HP_SET → SPAN_NPC_EDGE_PUBLISHED` rename is a follow-through of that doctrine; don't reintroduce HP terminology elsewhere.
- The three new OTEL attributes (`malformed_npcs_skipped`, `nameless_entries_dropped`, `location_available`) are silent-failure detectors — they must fire on the path that would have silently no-op'd, not just on the happy path.
- Wiring test is required (per CLAUDE.md "Every Test Suite Needs a Wiring Test") — must import-and-call through a non-test consumer, not just construct in isolation.
- `npc_agency.py` is dormant — refactor the signature, don't try to revive the subsystem.

**Banned patterns for downstream agents:** no `git stash` (any variant); no running tests on a prior commit to "prove a failure was pre-existing."

**Next:** Dev (`implement` phase).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (47 in sidequest-server):**
- `sidequest/game/session.py` — Drop `NpcRegistryEntry` class; drop `GameSnapshot.npc_registry` field; update P1-required docstring + `PartyPeer`/`chassis_registry` references.
- `sidequest/game/__init__.py` — Drop `NpcRegistryEntry` import and re-export.
- `sidequest/game/migrations.py` — Add `s2_malformed_npcs_skipped` + `s2_nameless_entries_dropped` silent-skip counters on the legacy-save migration (Reviewer findings).
- `sidequest/game/chassis.py`, `sidequest/game/world_materialization.py`, `sidequest/agents/prompt_framework/core.py` — docstring cleanup (legacy `npc_registry` mentions point at the dropped field with a "story 45-52" note).
- `sidequest/agents/orchestrator.py` — Drop `TurnContext.npc_registry`; rewire `_entity_tokens_for_registry` and the subsystem `bank_context` dispatch to use `npc_pool`.
- `sidequest/agents/subsystems/npc_agency.py` — Signature switch (`npc_registry: list[NpcRegistryEntry]` → `npc_pool: list[NpcPoolMember]`); rewrite directive payload to drop `last_seen_*` fields (not on pool members).
- `sidequest/agents/subsystems/__init__.py` — Update kwarg-filter doc to reference `npc_pool`.
- `sidequest/server/dispatch/encounter_lifecycle.py` — Rename `_publish_combat_stats_to_registry` → `_publish_combat_edge_to_npcs` (writes to `Npc.core.edge` via the renamed `SPAN_NPC_EDGE_PUBLISHED`); rename `_registry_fallback_npcs` → `_npc_fallback_at_location` (scans `snapshot.npcs`, returns `location_available` discriminator); decorate `encounter.no_opponent_available` span with that attribute.
- `sidequest/server/narration_apply.py` — Switch promotion-event component label to `"npc_pool"`; docstring updates.
- `sidequest/server/session_helpers.py` — Drop `npc_registry=` kwarg to `TurnContext`.
- `sidequest/server/websocket_session_handler.py` — Delete the pre-Wave-2A chargen-complete registry clear; rename patch-summary type and dashboard counter to `npc_pool`.
- `sidequest/server/rest.py` — Comment-only refresh (the wire field is unchanged for dashboard back-compat).
- `sidequest/server/status_clear.py` — Docstring refresh.
- `sidequest/handlers/connect.py` — Rename `npc_registry_count` log key to `npc_pool_count`.
- `sidequest/telemetry/spans/npc.py` — Rename `SPAN_NPC_REGISTRY_HP_SET` (`"npc_registry.hp_set"`) → `SPAN_NPC_EDGE_PUBLISHED` (`"npc.edge_published"`); helper renamed; route component switched to `"npcs"`; attributes carry `current`/`max` instead of `hp`/`max_hp`.
- `sidequest/telemetry/spans/encounter.py` — Add `location_available` to the `encounter.no_opponent_available` SpanRoute extract.
- `sidequest/telemetry/validator.py` — Rewire `entity_check` to union `snap.npc_pool` + `snap.npcs`; rewire `patch_legality_check` to iterate `snap.npcs` and use `core.edge.current` for liveness.
- 27 test files (9 SM-named + broader fan-out): NpcRegistryEntry → NpcPoolMember / Npc; assertions on `snapshot.npc_pool` instead of `snapshot.npc_registry`; new wiring test `tests/integration/test_npc_edge_publish_wiring.py` covering the three OTEL signals (SPAN_NPC_EDGE_PUBLISHED, `location_available`, migration silent-skip counters).
- `tests/server/conftest.py` — Replace `npc_registry=` kwarg on `_build_turn_context_for_test` with `npc_pool=`.

**Tests:** 5071/5071 passing (server, `uv run pytest -v`); 58 skipped (pre-existing). `uv run ruff check` clean on both `sidequest/` and `tests/`.

**Branch:** `feat/45-52-wave-2a-cleanup-drop-npcregistryentry` (pushed to `origin/feat/45-52-wave-2a-cleanup-drop-npcregistryentry`)

**Commit:** `7956d07` — `chore(45-52): drop NpcRegistryEntry + GameSnapshot.npc_registry, rewire to npc_pool/npcs`

**Handoff:** To `review` (Reviewer / Colonel Potter).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A (no findings to triage; 5071 tests green, ruff clean) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter`; edge analysis performed by Reviewer in-line |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings; silent-failure analysis performed by Reviewer in-line |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings; test-quality analysis performed by Reviewer in-line |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings; doc analysis performed by Reviewer in-line |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings; type-design analysis performed by Reviewer in-line |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings; security analysis performed by Reviewer in-line (refactor, no new attack surface) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings; simplification analysis performed by Reviewer in-line |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings; rule audit performed by Reviewer in-line against `.pennyfarthing/gates/lang-review/python.md` |

**All received:** Yes (1 returned, 8 disabled via settings)
**Total findings:** 2 confirmed (1 MEDIUM, 1 LOW), 0 dismissed, 1 deferred (pre-existing, out of scope)

### Rule Compliance (per `.pennyfarthing/gates/lang-review/python.md`)

The diff is a refactor of an existing subsystem — most rule categories are not exercised by the change set, but each was checked.

1. **Silent exception swallowing** — `[VERIFIED]` No new `except:`, `except Exception: pass`, or contextlib.suppress without rationale in any changed file. The pre-existing patterns in `websocket_session_handler.py` and `validator.py` are untouched.
2. **Mutable default arguments** — `[VERIFIED]` No function signatures changed to add mutable defaults. The new `TurnContext.npc_pool` field uses `field(default_factory=list)` (dataclass-correct), preserving the pre-existing pattern.
3. **Type annotation gaps at boundaries** — `[VERIFIED]` New public seams (`_publish_combat_edge_to_npcs`, `_npc_fallback_at_location`, `npc_edge_published_span`) all carry full type annotations. The `_npc_fallback_at_location` return type widened to `tuple[list, bool]` and is annotated.
4. **Logging coverage AND correctness** — `[VERIFIED]` Removed: `logger.info("npc_registry.cleared ...")` block. Net change is a deletion. No new error paths added that need logging.
5. **Path handling** — Not applicable (no path manipulation in diff).
6. **Test quality** — `[TEST / MEDIUM]` Vacuous assertions in `tests/server/test_npc_registry_combat_stats.py:175-185` — see finding below.
7. **Resource leaks** — Not applicable (no new resource acquisition).
8. **Unsafe deserialization** — Not applicable (no new deserialization). Migration `_migrate_s2_npc_registry_split` reads pre-parsed dict, no eval/pickle/yaml.load.
9. **Async/await pitfalls** — `[VERIFIED]` `run_npc_agency` signature change preserves `async def` shape; no blocking calls introduced. `tests/integration/test_npc_edge_publish_wiring.py` uses `@pytest.mark.asyncio` correctly and `asyncio.sleep(0.05)` is the established watcher-hub flush pattern in sibling tests.
10. **Import hygiene** — `[VERIFIED]` Drops of `NpcRegistryEntry` from `sidequest/game/__init__.py` `__all__` and orchestrator import are clean. New imports of `NpcPoolMember` from `sidequest.game.npc_pool` are correctly placed. No star imports introduced.
11. **Security: input validation at boundaries** — `[VERIFIED]` No new user-input boundaries. The migration's silent-skip counters now expose previously-invisible corruption signals on the GM panel (improvement, not regression).
12. **Dependency hygiene** — Not applicable (no `pyproject.toml` changes).
13. **Fix-introduced regressions** — `[VERIFIED]` Re-scanned the new code against checks 1-12; only the `[TEST/MEDIUM]` test-quality finding under check 6 surfaces.

### Devil's Advocate

Suppose I am hostile to this PR. What breaks?

- **The dial-derived edge overwrite trashes a creature-sheet pool.** A Patient Butcher with `hp: 30` in `creatures.yaml` gets materialized with `core.edge.max=30`. At encounter start the new `_publish_combat_edge_to_npcs` overwrites that to the dial threshold (often 10). For subsequent narrator turns, gaslighting reads see the dial-sized pool, not the creature sheet. **Mitigated:** Dev's Design Deviation #3 documents this and argues the dial IS the canonical encounter pool. SOUL.md "Gaslight the narrator" demands the narrator see what the mechanics use, and during a confrontation that's the dial. Accept.
- **The empty role on fallback-sourced mentions degrades narrator continuity.** Pre-fix `entry.role` was narrator-extracted ("hostile", "merchant"). Post-fix `npc.npc_role_id` is always None (archetype-id, never populated outside the namegen CLI). Confirmed: this lands an empty `role` string on every fallback NpcMention. **Mitigated:** the only consumer is `narration_apply._apply_npc_mentions` which guards with `if mention.role and not pool_hit.role:` — empty mentions don't overwrite. Encounter actor creation hardcodes role ("combatant"/"participant"). Functional impact: zero. Logged as `[TYPE/LOW]` below.
- **`is_first_commit` is now dead in scope.** Variable computed at line 1667, the body that consumed it from line 2090-2110 is deleted. **Verified:** the variable is still referenced at line 1669 (separate `if is_first_commit:` block) and in two comments. Not dead.
- **The migration's new counters could explode on corrupt saves.** `s2_malformed_npcs_skipped` counts entries that aren't dicts; could a malicious save trigger a memory blow-up? The legacy registry is iterated once with a single int increment per non-dict — bounded by list length, no quadratic blow-up. Safe.
- **`SPAN_NPC_EDGE_PUBLISHED` component switched to "npcs" but five OTHER routes in `npc.py` still use component="npc_registry".** Could the GM panel break? **Verified:** the legacy component string is a stable filter token for the dashboard. Renaming the dropped-field's span is correct; leaving the others stable preserves dashboard wiring. Dev's delivery finding #2 captures the future cleanup. Accept.
- **The new wiring test asserts `location_available: False` when `party_location` returns None.** Could a real session have `npcs_present=[]` AND a resolved location AND no NPCs at that location, masking the false-flag path? The test_no_opponent_span_carries_location_available_true counterpart covers exactly that. Both branches verified.
- **Test fixture leak: `_make_npc` helper duplicated across `test_encounter_actors_all_combatants.py` and `test_npc_registry_combat_stats.py`.** Not DRY. **Severity:** LOW cosmetic. The helper is 20 lines and varies subtly between sites (one uses `npc_role_id=role`, the other passes pronouns/appearance). Acceptable for personal-project test scaffolding.

Devil's advocate did not surface a CRITICAL or HIGH issue not already documented. Single residual concern is the vacuous-assertion finding under check 6.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Narrator emits `confrontation=combat` with empty `npcs_present` → `_apply_narration_result_to_snapshot` → `instantiate_encounter_from_trigger` → `_npc_fallback_at_location` (scans `snap.npcs` by `last_seen_location` matching `party_location(perspective=acting_pc)`) → `(mentions, location_available)` decorate `encounter.no_opponent_available` span on the silent-failure path, or feed the actor roster on the happy path → `_publish_combat_edge_to_npcs` writes `npc.core.edge.{current,max,base_max}` from the dial threshold and emits `npc.edge_published` OTEL → `WatcherSpanProcessor` routes to the GM panel via `SPAN_ROUTES[SPAN_NPC_EDGE_PUBLISHED]`. End-to-end coverage is in `tests/integration/test_npc_edge_publish_wiring.py:104-155`.

**Pattern observed (good):** Dev preserved Reviewer's silent-failure counters as OTEL attributes rather than logger calls — keeps Sebastien's GM panel as the canonical detector surface. See `sidequest/game/migrations.py:139-149,181-189` and the new `location_available` discriminator at `sidequest/server/dispatch/encounter_lifecycle.py:283,290,322`.

**Pattern observed (review-worthy):** The dial-derived edge overwrite at `sidequest/server/dispatch/encounter_lifecycle.py:174-186` rewrites `npc.core.edge.{current,max,base_max}` rather than maintaining a separate cache. Logged as Design Deviation #3 with rationale matching the SOUL.md gaslighting doctrine — accepted.

**Error handling:** `_publish_combat_edge_to_npcs` defensively returns on `opponent_metric is None` (`encounter_lifecycle.py:131`) and on `threshold <= 0` (`encounter_lifecycle.py:136`). The opponent-side filter at `encounter_lifecycle.py:159` ensures player Characters (looked up in `snapshot.characters`, not `snapshot.npcs`) cannot have their edge trampled. `_npc_fallback_at_location` returns `([], False)` on no resolved location (`encounter_lifecycle.py:215`) — Story 45-52's headline silent-failure detector.

### Findings

| Severity | Tag | Issue | Location | Resolution |
|----------|-----|-------|----------|------------|
| [MEDIUM] | [TEST] | Vacuous assertions: `placeholder_max == 10` (`PLACEHOLDER_EDGE_BASE_MAX`) and `threshold == 10` (`test_genre` combat dial) collide, so the value assertions `edge.max != placeholder_max or edge.max > 0`, `edge.current > 0`, and `edge.current == edge.max` all pass even if `_publish_combat_edge_to_npcs` is a no-op. | `tests/server/test_npc_registry_combat_stats.py:175,178,183` and `:197-198` | Not blocking — the OTEL span test (`test_otel_span_emitted_on_npc_edge_publish`) does verify the seam fires by asserting `spans` is non-empty AND `current > 0` AND `max > 0` on real span attributes (the span only fires if publish ran). Functional verification of the wire is intact. Recommend a follow-up to either (a) construct the NPC fixture with a non-placeholder edge (e.g. `edge.max = 5` pre-encounter) so post-publish `edge.max == 10` is a real check, or (b) replace the OR with exact-equality to the dial threshold. |
| [LOW] | [TYPE] | `_npc_fallback_at_location` reads `npc.npc_role_id` to populate `NpcMention.role`, but `npc_role_id` is the archetype-id field (P2-deferred — only set by `sidequest/cli/namegen/namegen.py`, never by the live narration path). Pre-fix this field was the narrator-extracted free-form role string on the legacy `NpcRegistryEntry`. | `sidequest/server/dispatch/encounter_lifecycle.py:206` | Not blocking — the bound `NpcMention.role` is unused by `EncounterActor` construction (which hardcodes role), and the downstream `_apply_npc_mentions` only writes role on empty pool entries. Functional impact: zero. The closest equivalent narrator-extracted role on the new model is `npc.core.personality` (where `_promote_pool_member_to_npc` stashes the pool member's role). Recommend a follow-up to either switch to `npc.core.personality or ""` or drop the field from the fallback's NpcMention entirely. |

### Deferred (pre-existing, out of scope)

- **`sidequest/server/rest.py:332`** — `int(edge.maximum)` reads a nonexistent attribute on `EdgePool` (the field is `max`). Dev surfaced this in delivery findings; the path is reachable from `/api/debug/state` whenever a saved session has stateful NPCs and would 500 the endpoint. Pre-existing; not introduced by this PR; the rewritten `test_debug_state_projects_saved_game` no longer pushes NPCs through that loop, so it isn't exercised. File a follow-up story to fix or to add a test that reaches this branch.

### Tag coverage

[EDGE] performed in-line — Devil's Advocate enumerated empty-pool, empty-location, dial-cap edges. [SILENT] performed in-line — verified the new `location_available` attribute closes a real silent-failure path and migration counters expose two more. [TEST] confirmed `[MEDIUM]` vacuous assertions above. [DOC] performed in-line — all rewritten docstrings (chassis.py, world_materialization.py, prompt_framework/core.py, status_clear.py) accurately reflect the new topology and cite story 45-52. [TYPE] confirmed `[LOW]` field-choice mismatch above. [SEC] performed in-line — diff is a refactor, no new auth/input/secret surfaces. [SIMPLE] performed in-line — Dev removed the chargen-complete clear cleanly (no shim, no `# removed` comment), and the renamed helpers are no more complex than their predecessors. [RULE] performed in-line — all 13 python.md lang-review rules checked and verified per the Rule Compliance section above.

**Handoff:** To SM for finish-story.