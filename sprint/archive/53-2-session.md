---
story_id: "53-2"
epic: "53"
workflow: "tdd"
---
# Story 53-2: Materializer: instantiate rig vessel item → bind RigComposurePool to character

## Story Details
- **ID:** 53-2
- **Epic:** 53 (Road Warrior: Rig two-pool wiring + content alignment)
- **Workflow:** tdd
- **Repos:** sidequest-server
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-19T13:21:04Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-19T12:41:48Z | 2026-05-19T12:47:28Z | 5m 40s |
| red | 2026-05-19T12:47:28Z | 2026-05-19T12:57:36Z | 10m 8s |
| green | 2026-05-19T12:57:36Z | 2026-05-19T13:06:00Z | 8m 24s |
| spec-check | 2026-05-19T13:06:00Z | 2026-05-19T13:08:39Z | 2m 39s |
| verify | 2026-05-19T13:08:39Z | 2026-05-19T13:12:07Z | 3m 28s |
| review | 2026-05-19T13:12:07Z | 2026-05-19T13:18:28Z | 6m 21s |
| spec-reconcile | 2026-05-19T13:18:28Z | 2026-05-19T13:21:04Z | 2m 36s |
| finish | 2026-05-19T13:21:04Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): `Inventory.items` is typed `list[dict]` rather than
  a typed item model — the parser has to defensively probe `item.get("id")`,
  `item.get("tags")` etc. Affects `sidequest/game/creature_core.py` (Inventory),
  `sidequest/game/vessel_tags.py` (parser). A typed `InventoryItem` model would
  let validators reject malformed shapes once at construction instead of per-call.
  Out of scope for 53-2. *Found by TEA during test design.*
- **Question** (non-blocking): The story-context "first vessel item wins" assumption
  is encoded in the tests, but neither the road_warrior inventory.yaml nor the
  starting_equipment table currently allows two vessels per character. If salvage
  scenarios (epic 99 the_salvage hooks) later allow multi-rig, the binder will
  need a ranking pass. *Found by TEA during test design.*
- **Gap** (non-blocking): There is no test in this story for the actual chargen
  end-to-end path (apply_starting_loadout → bind_rig_pools) because that requires
  a CatalogItem fixture with vessel tags. The wiring-test grep enforces *that* a
  production caller exists; Dev should consider whether an integration test in
  `tests/server/dispatch/` would catch broken wiring more directly than a string
  grep. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): `apply_starting_loadout` is the chargen seam
  where the rig binder fires, but the existing dispatch tests
  (`tests/server/dispatch/test_chargen_loadout.py`) do not yet exercise vessel
  items — adding one fixture covering a road_warrior Wheelman loadout would close
  the integration gap TEA flagged and catch any future regression where the
  bind-site is reordered. Affects `tests/server/dispatch/test_chargen_loadout.py`
  (add vessel fixture + assertion). *Found by Dev during implementation.*
- **Improvement** (non-blocking): `Inventory.items: list[dict]` (Phase-1
  carryover from the Rust port per the chargen_loadout module docstring) forces
  the vessel parser to type-check every key probe. The "typed `InventoryItem`
  model" TEA suggested would also slim down the `chargen_loadout._item_dict_*`
  helpers and the dedup pass. Affects `sidequest/game/creature_core.py` (Inventory)
  and downstream callers — distinct epic, not 53-x scope. *Found by Dev during
  implementation.*
- **Question** (non-blocking): The binder uses `core.name` as `character_id`
  (matching `rebind_chassis_bonds_to_character` convention), but if/when SideQuest
  adds the deterministic-character-id field hinted at in chassis bond ledger
  comments ("placeholder until real id arrives"), the rig binder should adopt
  the same id and the binder API may need a `rebind_rig_pools_to_character_id`
  sibling. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): `narration_apply._item_add` at
  `sidequest/server/narration_apply.py:2214` appends item dicts to
  `recipient_char.core.inventory.items` but never calls
  `bind_rig_pool_from_inventory`. If a future narrator-grant flow hands a
  vessel-tagged item to a character (epic 99 salvage, 53-3 vessel swap), the
  item lands in inventory unbound and `core.rig_pool` stays None — defeating
  the lie-detector premise. Out of scope for 53-2 per story-context AC2
  ("character-instantiation time"); MUST be wired before Epic 53 ships any
  narrator-granted vessel. Affects `sidequest/server/narration_apply.py`
  (add binder call after vessel-tagged item append). *Found by Reviewer during
  code review.*
- **Question** (non-blocking): `bind_rig_pools` (snapshot walker) is exported
  and tested but currently has zero production callers — only the per-character
  variant fires from `apply_starting_loadout`. Walker is intended for future
  defensive session-start rebind scenarios (53-3+). If no caller materializes
  in the next two stories, consider whether the walker is dead surface or
  belongs in 53-3 along with the crash handler. Affects
  `sidequest/game/vessel_tags.py` (walker may be removable in favor of
  per-character helper alone). *Found by Reviewer during code review.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/vessel_tags.py` (new, 216 lines) — parser,
  exception, dataclass, `find_vessel_item`, `bind_rig_pool_from_inventory`,
  `bind_rig_pools`.
- `sidequest-server/sidequest/game/creature_core.py` — added
  `rig_pool: RigComposurePool | None = None` field + import.
- `sidequest-server/sidequest/game/__init__.py` — re-exports
  `VesselTags`, `InvalidVesselTagsError`, `parse_vessel_tags`,
  `find_vessel_item`, `bind_rig_pool_from_inventory`, `bind_rig_pools`.
- `sidequest-server/sidequest/server/dispatch/chargen_loadout.py` — wired
  `bind_rig_pool_from_inventory(character.core, character_id=character.core.name)`
  at the end of `apply_starting_loadout` (after the loadout loop, before the
  final-count + OTEL block).
- Tests: applied ruff auto-fix import-sort tweaks to `tests/game/test_vessel_tags.py`
  and `tests/game/test_world_materialization_rig_binding.py`. No assertion changes.

**Tests:** 45/45 passing for story 53-2 (44 new + 1 regression guard).
Full sidequest-server suite: **6613 pass / 0 fail / 396 skip (pre-existing)** —
zero collateral damage from extending CreatureCore.

**Branch:** `feat/53-2-rig-vessel-materializer` (pushed to origin).

**Implementation Notes:**

- **Idempotency strategy:** the binder short-circuits when `core.rig_pool is not
  None`. This preserves damaged pools across snapshot reloads and lets the
  chargen-confirm callsite be called repeatedly without re-firing the
  `rig_pool.created` span (TEA AC4 negative-path test confirms span absence).
- **Production callsite chosen:** end of `apply_starting_loadout`. This is the
  exact seam where class-specific equipment (including `rig_tier_1_prospect`
  for road_warrior classes) lands in `character.core.inventory.items`, so the
  binder finds the vessel item one statement after it was appended. Alternative
  site (websocket_session_handler post-load) would still work but would fire
  later than necessary.
- **OTEL discipline:** no new spans added — the existing model-level
  `rig_pool.created` span (story 53-1) fires from the binder via
  `RigComposurePool.model_post_init`. Story 53-4 owns full GM-panel surface.
- **CLAUDE.md "No Silent Fallbacks":** every malformed shape (missing tag,
  duplicate tag, non-integer, negative, composure>max, missing id, non-vessel
  item, malformed tags list) raises `InvalidVesselTagsError` carrying the
  offending item's id. The binder does NOT swallow these — they propagate up to
  the chargen confirmation handler so operators see exactly which content entry
  needs fixing.
- **No fix to TEA's "production caller grep is fragile" concern beyond the
  actual wiring** — followed up with a delivery-finding flag suggesting a
  proper dispatch fixture in a future story.

**Handoff:** To Reviewer (Colonel Potter) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (45 tests pass, lint clean, no smells, 0 TODOs, 0 console_log, 0 test_skips) | N/A |
| 2 | reviewer-edge-hunter | No | skipped | disabled via `workflow.reviewer_subagents.edge_hunter=false` | N/A — Reviewer covers domain manually |
| 3 | reviewer-silent-failure-hunter | No | skipped | disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` | N/A — Reviewer covers domain manually |
| 4 | reviewer-test-analyzer | No | skipped | disabled via `workflow.reviewer_subagents.test_analyzer=false` | N/A — Reviewer covers domain manually |
| 5 | reviewer-comment-analyzer | No | skipped | disabled via `workflow.reviewer_subagents.comment_analyzer=false` | N/A — Reviewer covers domain manually |
| 6 | reviewer-type-design | No | skipped | disabled via `workflow.reviewer_subagents.type_design=false` | N/A — Reviewer covers domain manually |
| 7 | reviewer-security | No | skipped | disabled via `workflow.reviewer_subagents.security=false` | N/A — Reviewer covers domain manually |
| 8 | reviewer-simplifier | No | skipped | disabled via `workflow.reviewer_subagents.simplifier=false` | N/A — Reviewer covers domain manually + TEA verify simplify trio returned clean (0 findings across reuse/quality/efficiency) |
| 9 | reviewer-rule-checker | No | skipped | disabled via `workflow.reviewer_subagents.rule_checker=false` | N/A — Reviewer enumerates project rules manually below |

**All received:** Yes (1 returned with content, 8 skipped via settings)
**Total findings:** 1 MEDIUM (deferred/forward-looking), 2 LOW (non-blocking), 5 VERIFIED, 0 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

### Findings

| Severity | Tag | Issue | Location |
|----------|-----|-------|----------|
| [VERIFIED] | [—] | Idempotency guard preserves damaged pools on snapshot reload | `vessel_tags.py:177` short-circuits before re-parsing tags when `core.rig_pool is not None`. Confirmed by `test_bind_rig_pools_is_idempotent_on_reload`. Complies with story-context AC3 + CLAUDE.md "No Silent Fallbacks" doctrine. |
| [VERIFIED] | [—] | No silent fallbacks in parser | `vessel_tags.py:91-141` — every malformed shape raises `InvalidVesselTagsError` with the offending item id in the message. 10 negative-path tests in `test_vessel_tags.py` cover missing/empty/duplicate/non-integer/negative/over-max/missing-id/non-vessel/empty-tags/non-list-tags cases. |
| [VERIFIED] | [—] | Production call site actually executes the binder | `chargen_loadout.py:239` invokes `bind_rig_pool_from_inventory(character.core, character_id=character.core.name)` after the loadout-loop append at line 221. Not a dead import — the binder runs every chargen confirmation. The wiring-test grep at `test_world_materialization_rig_binding.py:222-249` would pass even if the function were merely imported, but inspection confirms it's actually called. |
| [VERIFIED] | [—] | CreatureCore strict-extra invariant preserved | `creature_core.py:208` `model_config = {"extra": "forbid"}` unchanged; new `rig_pool: RigComposurePool | None = None` field properly typed Optional with None default. Regression test `test_creature_core_strict_extra_forbid_still_holds` confirms unknown fields still raise `ValidationError`. Sibling-pattern match: identical shape to `edge: EdgePool` at line 217. |
| [VERIFIED] | [—] | OTEL `rig_pool.created` fires exactly once per bound pool | Existing model-side `model_post_init` at `rig_composure_pool.py:90-107` emits the span at construction; binder at `vessel_tags.py:184-191` constructs RigComposurePool once per character. Tests confirm no phantom spans on no-vessel or idempotent paths. No new span added — Story 53-4 owns full GM-panel surface. |
| [MEDIUM] | [SCOPE] | Post-chargen vessel grants don't bind a rig pool | Verified at `sidequest/server/narration_apply.py:2214` — narrator-applied item loot appends to `recipient_char.core.inventory.items` but does NOT call `bind_rig_pool_from_inventory`. If a future scenario grants a vessel via narration ("you find an abandoned rig in the wastes"), the item lands in inventory but `core.rig_pool` stays None. **Not blocking for 53-2** because (a) story-context AC2 explicitly scopes binding to "character-instantiation time", (b) current road_warrior content only ships vessels via `starting_equipment`, (c) salvage scenarios are deferred to epic 99 / story 53-3+. Forward-looking — Epic 53 cannot ship narrator-granted vessels until `narration_apply._item_add` also calls the binder. Logged as Improvement finding for the next epic-53 story to address. |
| [LOW] | [—] | `character_id` is derived from `core.name`, collision-prone in MP | `vessel_tags.py:206` uses `character.core.name` as `character_id`. Two PCs sharing a name produce two pools with `character_id="Mira"`, indistinguishable to the future crash handler (53-3). Mirrors the existing chassis convention at `chassis.py:186` (`rebind_chassis_bonds_to_character` uses the same pattern). Consistent with current tech debt; flagged as forward-looking shared concern with chassis subsystem, not new to this story. |
| [LOW] | [—] | Binder fires unconditionally even when `inventory_config is None` | `chargen_loadout.py:239` calls the binder outside the `if inventory_config is not None:` block. The binder no-ops on empty inventory so no functional harm, but the call is wasted work in the "genre pack has no inventory" path. Trivial — leaving the call outside the conditional is actually more defensive against future code paths that bypass the `inventory_config` check. |

### Data flow traced

Content (`road_warrior/inventory.yaml`) → `CatalogItem` (genre/models/inventory.py) →
`_item_dict_from_catalog` (chargen_loadout.py:48) → `character.core.inventory.items.append(candidate)`
(chargen_loadout.py:221) → `bind_rig_pool_from_inventory(character.core, character_id=character.core.name)`
(chargen_loadout.py:239) → `find_vessel_item` (vessel_tags.py:146) → `parse_vessel_tags` (vessel_tags.py:85)
→ `RigComposurePool(...)` (vessel_tags.py:184) → `core.rig_pool = pool` (vessel_tags.py:192) →
GameSnapshot serialization → SQLite save → snapshot reload → Pydantic rehydrates `rig_pool`
directly via `model_validate_json`. Safe because: (1) parser fails loud on every malformed
shape, (2) idempotent guard prevents reload-time clobbering, (3) `extra='forbid'` invariant
catches any unexpected fields at the save-file boundary.

### Pattern observed

The vessel-tag parser follows the established `EdgePool` / `RigComposurePool` strict-Pydantic
pattern (`vessel_tags.py:67-73` for `VesselTags`, mirrors `creature_core.py:46-78` for `EdgePool`).
The binder follows the `rebind_chassis_bonds_to_character` precedent (`chassis.py:186`) — same
character-id convention, same idempotency philosophy. Good pattern reuse.

### Error handling

- Missing/malformed tags → `InvalidVesselTagsError(item_id, reason)` carrying offending item id (vessel_tags.py:60-64). Chargen flow surfaces this to the operator with content-fix context.
- Blank `character_id` → bare `ValueError("character_id cannot be blank")` at vessel_tags.py:174-175. Validators on the pool itself would also catch this at construction (rig_composure_pool.py:71-75), but failing earlier in the binder gives a friendlier stack.
- Non-dict inventory item → silently skipped at `find_vessel_item` (vessel_tags.py:153-154). Acceptable because `Inventory.items: list[dict]` is enforced by Pydantic upstream — non-dict items can only appear via direct `.append` of a bad value, which would have failed Pydantic validation on next snapshot dump.
- Already-bound `core.rig_pool` on reload → silently preserved (intentional idempotency, not a swallowed error).

### Rule Compliance

Enumerating CLAUDE.md (sidequest-server) and orchestrator CLAUDE.md rules against every changed type/function:

| Rule | Subject | Compliance |
|------|---------|------------|
| **No Silent Fallbacks** | `parse_vessel_tags` | ✓ Every malformed shape raises `InvalidVesselTagsError` with item id |
| **No Silent Fallbacks** | `bind_rig_pool_from_inventory` | ✓ Propagates parser exceptions; idempotent skip is documented behavior, not a silent failure |
| **No Silent Fallbacks** | `bind_rig_pools` walker | ✓ Propagates loudly per docstring; partial-bind state is intentional (per story scope) |
| **No Stubbing** | All new functions | ✓ Every function fully implemented with tests; no `pass` / `TODO` / `NotImplementedError` |
| **Don't Reinvent — Wire Up What Exists** | `VesselTags`, `parse_vessel_tags` | ✓ TEA simplify-reuse subagent confirmed no existing parser for this tag shape; `RigComposurePool` reused from 53-1 not re-implemented |
| **Verify Wiring, Not Just Existence** | `chargen_loadout.py:239` | ✓ Actual function call, not just import — verified by code inspection + `test_bind_rig_pools_imported_by_production_module` grep |
| **Every Test Suite Needs a Wiring Test** | 53-2 tests | ✓ `test_world_materialization_rig_binding.py` exercises snapshot-walker path; production-caller grep confirms `chargen_loadout.py` imports the binder |
| **OTEL Observability Principle** | Binder | ✓ Existing `rig_pool.created` span fires via model `model_post_init`; absent on no-vessel / idempotent path so GM panel can distinguish "no rig" from "rig present but broken" |
| **CLAUDE.md "personal project — no Jira"** | All session docs | ✓ Session marks JIRA_KEY skipped; no Jira references in commits or PRs |
| **gitflow (PRs target develop)** | Branch | ✓ Branch `feat/53-2-rig-vessel-materializer` cut from develop; SM will target develop in finish-phase PR |
| **No "we'll fix it later" shortcuts** | All new code | ✓ Forward-looking concerns are logged as separate findings/improvements with explicit deferral rationale, not as commented-out code or skip flags |
| **Quality Rules: "every playtest is production tomorrow"** | All new code | ✓ Loud-fail discipline holds — no quick fixes; idempotency is principled defense-in-depth, not a hack |
| **SOUL: Gaslight the narrator with game state** (memory `[[narrator_gaslighting_doctrine]]`) | Materialized `rig_pool` in snapshot | ✓ Pool lives in `core.rig_pool` directly; future narrator turns will see Composure in snapshot rather than improvising rig damage |
| **HP→Edge translation at materializer seam** (memory `[[hp_removed]]`) | vessel_tags parser | ✓ No HP field anywhere; composure tags are the only mechanical surface parsed. If vessel items ever sprout HP, the materializer seam is the right translation point |

### Devil's Advocate

A malicious or careless content author writes a vessel item with an empty composure tag —
`["vessel", "rig", "composure:", "composure_max:4"]`. The parser hits `_parse_int_tag` with
`value=""`, `int("")` raises `ValueError`, wrapped in `InvalidVesselTagsError`, and chargen
fails LOUDLY. The player cannot create a Wheelman. This is the documented behavior, not a
bug — but operationally it means one typo in `road_warrior/inventory.yaml` breaks the whole
genre pack. There is no upstream content-side schema validator gating vessel tags before
they reach this parser. The mitigation is that `pf validate` runs on content commits and
the loud failure message includes the item id, so the author can fix the typo from the
stack trace. Acceptable per CLAUDE.md "fail loud" doctrine, but worth a follow-up to add
a content-side vessel-tag linter (separate epic).

A confused homebrew author inherits road_warrior and forgets `composure_max:N` on a custom
rig. Same loud failure. The error message `"vessel item 'rig_homebrew_v1': missing
'composure_max':N tag"` is actually quite helpful — it names the field AND the item, so
fix-it-yourself is obvious without reading source.

A stressed filesystem is irrelevant — this is pure in-memory transformation, no I/O.

What about a corrupted snapshot? `model_validate_json` on `CreatureCore` would fail at the
Pydantic layer with line/column info. The `rig_pool` field would fail to deserialize
loudly, not silently drop. Per `extra=forbid` invariant on both `CreatureCore` and
`RigComposurePool`.

A race condition: two clients hit chargen-confirm simultaneously for the same session.
Both call `apply_starting_loadout` → both call `bind_rig_pool_from_inventory` on the
same `core`. First wins; second sees `core.rig_pool is not None` and silently returns
None per the idempotent guard. The second-fired `model_post_init` OTEL span is also
skipped (no new pool constructed). Acceptable consequence of defense-in-depth, not a
bug. Worth noting: GM panel would see one `rig_pool.created` span even though two clients
"tried" — that's the correct observability surface.

What would a malicious *player* do? Player input never reaches the vessel parser. Vessels
come from genre pack content, not user input. The Zork Problem doctrine ensures the
player can SAY "I find a fancy rig" but the narrator can't unilaterally grant items —
item grants go through a structured tool call with author-controlled inventory dicts. The
narrator can't inject a vessel item bypassing this binder; if 53-3+ adds narrator-granted
vessel paths, the binder MUST be wired there too (logged as MEDIUM scope finding above).

What if `character.core.name` is mutated between bind time and snapshot save? The bound
pool has `character_id="Mira"` baked in; if the name renames to "Mira the Wheelman", the
pool's `character_id` is stale. Crash handler (53-3) would look for "Mira the Wheelman"
and find nothing. This is the same staleness pattern as the chassis bond ledger, which
mitigates via `rebind_chassis_bonds_to_character`. A `rebind_rig_pools_to_character_id`
sibling will be needed if/when SideQuest introduces a stable character id distinct from
name. Logged as LOW finding above.

**Devil's Advocate verdict: no live bugs, two forward-looking concerns already flagged,
no hidden silent fallbacks.**

### Verdict

**APPROVED.**

- All ACs covered by 45 tests (44 new + 1 regression guard), all green.
- Full sidequest-server suite stays at 6613/0/396 — zero collateral damage.
- All applicable project rules verified compliant by enumeration.
- Code is well-scoped, well-named, well-documented, and wired at the only correct seam.
- The two architect-flagged spec mismatches (call site location, round-trip via Pydantic JSON not literal SQLite) are spec-quality issues already accepted.
- Forward-looking concerns (narration_apply vessel-grant wiring, character_id MP collision) are non-blocking deferrals appropriate for later epic-53 stories.

**Handoff:** To SM (Hawkeye Pierce) for finish-story ceremony.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — two minor mismatches, both resolved in favor
of the implementation (Option A / Option C — no code changes warranted).

**Mismatches Found:** 2 substantive, 0 blocking. The structural gate
(`gates/spec-check`) passes cleanly: every AC has Dev-assessment coverage,
implementation is marked complete, both TEA and Dev deviation subsections are
properly formatted.

### Mismatch 1 — Call-site location

- **Category:** Different behavior (call site is in a sibling module to what
  the spec named)
- **Type:** Architectural — picks the actual seam where vessel items appear in
  inventory
- **Severity:** Minor (a better choice than the spec described)
- **Spec** (context-story-53-2.md, Technical Guardrails → Key files):
  > `sidequest/game/world_materialization.py` — primary edit site. The
  > character materialization paths (`_apply_npc`, the player materialization
  > fork — currently three `Inventory()` construction sites around lines 352,
  > 461, 768) build `CreatureCore` instances. Add a "scan inventory for vessel
  > items, instantiate pool, bind" step at the end of those paths.
- **Code:** Wired at the end of
  `sidequest/server/dispatch/chargen_loadout.py::apply_starting_loadout`
  instead of inside `world_materialization.py::_apply_character` /
  `_apply_npc`.
- **Recommendation:** **A — Update spec.** The spec's suggestion was based on
  AC2's "materializer" framing, but `ChapterCharacter` carries no inventory
  field and `_apply_character` constructs every character with `Inventory()`
  (line 352). Vessel items only arrive via `apply_starting_loadout`, where
  the loadout loop appends them to `character.core.inventory.items`. Binding
  inside `world_materialization` would have run before the vessel ever
  reached the inventory — the spec was simply wrong about which seam owns
  inventory-bearing materialization. Dev's choice is the only correct call
  site for the live chargen path. The future "snapshot reload" path will
  rehydrate `core.rig_pool` directly from the serialized JSON via Pydantic
  (no re-binding needed), and the idempotent guard in
  `bind_rig_pool_from_inventory` protects any future defensive call site.

### Mismatch 2 — AC3 round-trip test uses Pydantic JSON, not literal SQLite

- **Category:** Different behavior (different transport, same serialization
  guarantee)
- **Type:** Behavioral (test scope, not production behavior)
- **Severity:** Minor — TEA already logged this kind of choice as a deviation
  and the round-trip is functionally equivalent
- **Spec** (context-story-53-2.md, AC3 expansion):
  > Test: build a snapshot with a rig-bound character, save to SQLite (use
  > the existing session-test helper), reload, assert pool is present and
  > field-equal.
- **Code:** `test_creature_core_round_trip_preserves_rig_pool` +
  `test_creature_core_json_round_trip_preserves_rig_pool` use
  `model_dump`/`model_validate` and `model_dump_json`/`model_validate_json`
  rather than the SQLite session store helper.
- **Recommendation:** **C — Clarify spec.** Pydantic JSON serialization is
  the *exact* marshaling layer SQLite uses for these models (see
  `SqliteStore.save_session` → `model_dump_json` on the snapshot). The
  literal SQLite round-trip would exercise schema migration / connection
  pooling, neither of which is in scope for 53-2's snapshot round-trip
  guarantee. The narrower test is the right surface for proving rig_pool
  persists across the save/load contract. Spec should be reworded:
  "verify CreatureCore Pydantic JSON round-trip preserves rig_pool — the
  marshaling layer SQLite consumes."

### Architectural Notes (informational — no decisions required)

1. **CreatureCore now imports from `rig_composure_pool`.** Before 53-2 the
   module imported only `status`; the new import creates a forward edge from
   the shared-fields layer into a sibling pool module. Risk is bounded —
   `rig_composure_pool` has minimal deps (Pydantic + telemetry spans), no
   circular import emerged in the full test suite (6613 pass / 0 fail), and
   the same pattern would apply if any other optional pool were composed
   into CreatureCore in future. Worth a note in epic 53's architecture
   reference; not blocking.

2. **`bind_rig_pools` (snapshot walker) is exported but has no production
   caller.** Currently only `bind_rig_pool_from_inventory` is called in
   production (from `chargen_loadout`). The walker is tested and ready for
   53-3's defensive "rebind on session-start reload" scenario (if needed)
   or for future multi-character party loading. The wiring-test grep is
   satisfied by either symbol, so this isn't a wiring gap — it's an
   intentionally-prepared API surface. Worth noting so Reviewer doesn't
   flag the walker as dead code.

3. **AC5 production-caller grep is the right tool for now.** TEA's logged
   deviation about preferring a chargen-pipeline integration test stands —
   Dev's follow-up Improvement finding (add a road_warrior Wheelman
   loadout fixture to `tests/server/dispatch/test_chargen_loadout.py`) is
   the right epic-53 follow-up. Not a blocker for this story.

**Decision:** **Proceed to review.** Both mismatches are spec-quality issues,
not implementation defects. The code is correct, the tests are sound, and the
chargen wiring is at the only viable seam. No hand-back to Dev required.

### TEA (test verification)
- No upstream findings during test verification — simplify fan-out returned
  clean on all three lenses; quality-pass gate passes; full regression sweep
  on touched modules is GREEN.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7 (4 production + 3 test files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 findings — no duplicated logic against existing `EdgePool` / `ResourcePool` / `find_npc_by_name` patterns; vessel-tag parsing is a new domain-specific pattern that does not match any existing reusable abstraction |
| simplify-quality | clean | 0 findings — `rig_pool` field comment style matches session.py optional-field precedent; `vessel_tags.py` docstring mirrors `rig_composure_pool.py` structure; imports, exports, and error-handling all follow project conventions |
| simplify-efficiency | clean | 0 findings — `_parse_int_tag` helper is justified (used twice with consistent error context); four-function module surface (parse/find/bind/walk) is correctly scoped; `VesselTags` two-field model is appropriate, not premature |

**Applied:** 0 high-confidence fixes (nothing to apply)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean

### Rule Coverage (post-Dev re-verification)

| Rule | Status |
|------|--------|
| CLAUDE.md "No Silent Fallbacks" | confirmed — every malformed shape raises `InvalidVesselTagsError`; binder propagates loudly through `bind_rig_pools` |
| CLAUDE.md "Every Test Suite Needs a Wiring Test" | confirmed — production-caller grep test passes; `bind_rig_pool_from_inventory` is called from `apply_starting_loadout` (non-test module) |
| CLAUDE.md "Verify Wiring, Not Just Existence" | confirmed — `chargen_loadout.apply_starting_loadout` actually executes the binder at the chargen-confirm seam |
| Save-file safety (`extra='forbid'`) | confirmed — `rig_pool` extension preserves the invariant; regression-guard test still passes |
| OTEL principle | confirmed — `rig_pool.created` span fires from the binder via existing model-side `model_post_init`; no phantom spans on no-vessel / idempotent paths |
| Pydantic strict round-trip | confirmed — both `model_dump`/`model_validate` and `model_dump_json`/`model_validate_json` preserve `rig_pool` |

**Quality Checks:** All passing (ruff clean; 143 focused-sweep tests pass in
1.06s; 17 pre-existing skips; warnings are pre-existing Pydantic shadow-field
noise unrelated to 53-2).

**Handoff:** To Reviewer (Colonel Potter) for code review.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Wiring test uses production-caller grep rather than dispatch integration test**
  - Spec source: context-story-53-2.md, AC5 ("wiring test ... exercises the
    production materializer path end-to-end — not a direct call to a parser
    helper")
  - Spec text: "a 'character with inventory → materialize → assert pool present +
    bound + correct' test"
  - Implementation: The "snapshot in → bound pool out" pattern IS implemented via
    `bind_rig_pools(snap)` on a hand-built GameSnapshot. The *call-site existence*
    check is a `rglob`+`grep` for `bind_rig_pools` / `bind_rig_pool_from_inventory`
    in any non-test `sidequest/**/*.py`. A true chargen-pipeline integration test
    would need a CatalogItem fixture for vessel tags and a stubbed loadout flow.
  - Rationale: The chargen flow runs through `apply_starting_loadout` which needs
    a full GenrePack fixture; building that in this test would 3x the file size
    for marginal coverage gain. The grep test catches the most common wiring
    failure (helper defined but never called) and Dev can choose between
    `chargen_loadout.py` post-hook or `websocket_session_handler.py` post-load.
  - Severity: minor
  - Forward impact: If Dev wires the helper through a roundabout path (e.g.
    importing into a module that doesn't actually invoke it at runtime), the
    grep test would pass falsely. Reviewer should verify the call site actually
    executes during chargen confirmation.

- **CreatureCore.rig_pool field invariant test (`test_creature_core_strict_extra_forbid_still_holds`) is a regression guard, not a behavior assertion**
  - Spec source: context-story-53-2.md, AC3 ("CreatureCore.rig_pool: RigComposurePool | None field + snapshot round-trip")
  - Spec text: extending the existing model without weakening its strictness
  - Implementation: The test already passes today (extra=forbid was already in
    place from 53-1). It is preserved deliberately as a regression guard — if
    Dev removes `model_config = {"extra": "forbid"}` to "make rig_pool optional
    work", this test catches it.
  - Rationale: Vacuous-looking but load-bearing — every extension to a strict
    Pydantic model needs this invariant test or the next field-addition will
    quietly drop it.
  - Severity: minor (visibility — the testing-runner subagent flagged it as
    vacuous; a comment in the test would have prevented that)
  - Forward impact: None for production. For future TEAs, prefer adding a
    `# regression guard` comment when keeping a passing test in a RED commit.

### Reviewer (audit)

- **TEA deviation 1 — Wiring test uses production-caller grep rather than dispatch
  integration test** → ✓ ACCEPTED by Reviewer: the grep is consistent with epic-53's
  existing chassis-binder wiring pattern (`rebind_chassis_bonds_to_character`); a
  proper dispatch fixture is flagged as a follow-up Improvement and Dev's call-site
  choice means inspection trivially confirms the binder actually runs. Not a hidden
  wiring gap.
- **TEA deviation 2 — `test_creature_core_strict_extra_forbid_still_holds` regression
  guard** → ✓ ACCEPTED by Reviewer: legitimate invariant test; the testing-runner
  flag was over-eager. Future RED-phase guards should include an inline comment to
  prevent misclassification (improvement noted, not a defect).
- **Architect mismatch 1 — Call-site moved from `world_materialization.py` to
  `chargen_loadout.py::apply_starting_loadout`** → ✓ ACCEPTED by Reviewer: spec's
  named site cannot work — `_apply_character`/`_apply_npc` operate on empty
  inventories built at line 352/461 of world_materialization.py, and
  `ChapterCharacter` carries no inventory field, so a binder hooked there would
  always find nothing. The chargen-loadout seam is the only viable wiring site
  for the live chargen path. Snapshot reload rehydrates `rig_pool` directly via
  Pydantic; the idempotency guard protects any future defensive call site.
- **Architect mismatch 2 — Round-trip test uses Pydantic JSON, not literal SQLite** →
  ✓ ACCEPTED by Reviewer: `SqliteStore` marshals via `model_dump_json` on the
  snapshot — Pydantic JSON round-trip IS the format SQLite consumes. Narrower test
  is the correct surface.
- **UNDOCUMENTED deviation** — none found that TEA/Dev/Architect missed. The
  forward-looking concerns I logged (narration_apply vessel-grant gap, MP name
  collision, unconditional binder call) are not spec deviations — they are out-of-
  scope architectural follow-ups, properly tagged as Improvements/Lows in my
  Findings table.

### Architect (reconcile)

Two formal deviation entries promoted from the spec-check assessment to the
canonical Design Deviations record. Both were originally documented in
`## Architect Assessment (spec-check)` and stamped ACCEPTED by Reviewer; this
section gives them their 6-field self-contained form so the boss can audit
the story from this section alone without cross-referencing the assessment.
A third entry documents a deviation Dev made implicitly that was never logged
under a Dev subsection.

- **Production call site moved from `world_materialization.py` to `chargen_loadout.py`**
  - Spec source: `sprint/context/context-story-53-2.md`, Technical Guardrails →
    Key files; AC2 (Materializer instantiates and binds the pool)
  - Spec text: "`sidequest-server/sidequest/game/world_materialization.py` —
    primary edit site. The character materialization paths (`_apply_npc`, the
    player materialization fork — currently three `Inventory()` construction
    sites around lines 352, 461, 768) build `CreatureCore` instances. Add a
    'scan inventory for vessel items, instantiate pool, bind' step at the end
    of those paths."
  - Implementation: Binder call wired at the end of
    `sidequest/server/dispatch/chargen_loadout.py::apply_starting_loadout`
    (line 239) after the loadout-loop append at line 221. The
    `world_materialization.py` paths were left unmodified.
  - Rationale: `ChapterCharacter` carries no inventory field; the three
    `world_materialization.py` `Inventory()` construction sites at 352, 461,
    768 build EMPTY inventories. A binder hooked there would always find
    nothing because vessels only arrive via `apply_starting_loadout`. The
    chargen-loadout seam is the only viable wiring site for the live chargen
    path. Snapshot reload rehydrates `rig_pool` directly via Pydantic
    `model_validate_json`, so no re-binding is needed there; the idempotency
    guard at `vessel_tags.py:177` protects any future defensive call site.
  - Severity: minor
  - Forward impact: When Story 53-3 adds the crash handler, it should attach
    to the same chargen-loadout-emitted pool already in `core.rig_pool`; no
    work in world_materialization.py is needed. When Epic 99 / 53-3+ adds
    narrator-granted vessels, the binder MUST also be wired into
    `narration_apply._item_add` at line ~2214 (logged separately as a
    Reviewer Gap finding).

- **AC3 snapshot round-trip tested via Pydantic JSON, not literal SQLite session helper**
  - Spec source: `sprint/context/context-story-53-2.md`, AC3 (Snapshot round-trip)
  - Spec text: "Test: build a snapshot with a rig-bound character, save to
    SQLite (use the existing session-test helper), reload, assert pool is
    present and field-equal."
  - Implementation: `test_creature_core_round_trip_preserves_rig_pool` and
    `test_creature_core_json_round_trip_preserves_rig_pool` in
    `tests/game/test_rig_pool_binding.py` use `model_dump`/`model_validate`
    and `model_dump_json`/`model_validate_json` directly on `CreatureCore`
    rather than driving the full `SqliteStore` save → load cycle.
  - Rationale: `SqliteStore` marshals via `model_dump_json` on the snapshot
    before writing to SQLite, so Pydantic JSON round-trip IS the format SQLite
    consumes — the narrower test exercises the only marshaling layer that can
    actually drop a field. A full SQLite round-trip would additionally
    exercise connection pooling and schema migration, neither of which is in
    scope for 53-2's "snapshot persistence" guarantee.
  - Severity: trivial
  - Forward impact: None for production. If `SqliteStore` ever migrates to a
    non-JSON serialization layer (e.g. pickle, protobuf), AC3 coverage would
    need a re-baseline test against the new marshaling layer.

- **Dev did not write a `### Dev (implementation)` subsection under Design Deviations**
  - Spec source: `pennyfarthing-dist/guides/deviation-format.md` and the Dev
    agent definition's `<deviation-logging>` requirement
  - Spec text: "If no deviations: Write `### Dev (implementation)\n- No
    deviations from spec.`" (Dev must always have a subsection)
  - Implementation: The session's `## Design Deviations` section contains
    `### TEA (test design)` and `### Reviewer (audit)` subsections, but no
    `### Dev (implementation)` subsection. The deviations-logged gate at Dev
    exit passed without it.
  - Rationale: Dev had two implicit deviations (the call-site move documented
    above, and the absence of a separate `materializer.rig_bound` span in
    favor of the existing model-side `rig_pool.created`) but logged them
    instead as Delivery Findings and inline comments in chargen_loadout.py.
    Both deviations are now captured under this Architect (reconcile)
    subsection.
  - Severity: trivial (process — Architect reconcile catches it; no
    production impact)
  - Forward impact: Future stories should ensure Dev writes an explicit
    `### Dev (implementation)` subsection at exit, even when only
    documenting "No deviations from spec." The gate validation may need
    tightening to require all three subsections (TEA, Dev, Reviewer/Architect)
    rather than passing on the first one present.

**AC deferral verification:** No ACs were deferred. All six (parser helper,
materializer instantiate-and-bind, snapshot round-trip, OTEL span, wiring
test, no-silent-fallback negative path) are claimed as covered by the
Dev/TEA assessments. Reviewer's "APPROVED" verdict confirms no AC was
invalidated during review. Conditional step is a no-op.

**Reconcile complete.** The Design Deviations record is now self-contained:
all four substantive deviations (TEA-1 grep wiring, TEA-2 regression guard,
Architect call-site, Architect round-trip) have full 6-field entries with
quoted spec text. The reviewer audit stamps remain as the authoritative
ACCEPT/FLAG record. The boss can audit story 53-2 from this section alone
without external lookups.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story 53-2 introduces new public API (parser + binder + CreatureCore
field) — fits the standard TDD red→green flow.

**Test Files:**
- `sidequest-server/tests/game/test_vessel_tags.py` — parser contract (15 tests)
- `sidequest-server/tests/game/test_rig_pool_binding.py` — CreatureCore field +
  binder + OTEL emission (22 tests + 1 regression guard)
- `sidequest-server/tests/game/test_world_materialization_rig_binding.py` —
  snapshot walker + production-caller wiring (7 tests)

**Tests Written:** 44 failing + 1 regression guard = 45 tests covering all 6 ACs
**Status:** RED (verified by testing-runner — 44 ImportError failures, 1 pre-existing
regression guard passing, collection successful)

### AC Coverage

| AC | Coverage |
|----|----------|
| 1 — vessel-tag parser helper | `test_vessel_tags.py` (15 tests: happy path, missing tag, non-integer, negative, zero-max, composure>max, duplicate, non-vessel, empty tags, missing id) |
| 2 — materializer instantiates + binds pool | `test_rig_pool_binding.py::test_bind_rig_pool_*` (4 tests: happy path, partial-damage preservation, no-vessel returns None, empty inventory) |
| 3 — snapshot round-trip on CreatureCore | `test_rig_pool_binding.py::test_creature_core_*_round_trip*` (3 tests: dict round-trip, JSON round-trip, no-rig stays None) + strict-extra regression guard |
| 4 — OTEL `rig_pool.created` span | `test_rig_pool_binding.py::test_bind_rig_pool_emits*` (3 tests: emits on bind, absent on no-vessel, absent on idempotent re-bind) |
| 5 — wiring test | `test_world_materialization_rig_binding.py` (7 tests: snapshot walker behavior + production-caller grep) |
| 6 — no silent fallback | `test_vessel_tags.py` (7 negative-path tests) + `test_rig_pool_binding.py::test_bind_rig_pool_raises_on_malformed_vessel_tags` + `test_world_materialization_rig_binding.py::test_bind_rig_pools_propagates_invalid_vessel_tags_loudly` |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| CLAUDE.md "No Silent Fallbacks" | parser raises on every malformed shape; binder raises rather than skip | failing |
| CLAUDE.md "Every Test Suite Needs a Wiring Test" | `test_bind_rig_pools_imported_by_production_module` greps for non-test caller | failing |
| CLAUDE.md "Verify Wiring, Not Just Existence" | snapshot-walker test exercises the real `GameSnapshot`/`Character` chain | failing |
| Save-file safety (`extra='forbid'`) | regression guard on `CreatureCore` | passing (pre-existing invariant, preserved) |
| OTEL principle | `rig_pool.created` fires via binder, absent on no-vessel/idempotent | failing |
| Pydantic strict round-trip | `model_dump` → `model_validate` + `model_dump_json` → `model_validate_json` | failing |

**Self-check:** One pre-existing-invariant test passes; rationale documented as
deviation. No vacuous-assertion failures (e.g. no `assert x.is_some()` patterns,
no `let _ = result`). Every assertion checks a concrete value or exception type.

**Handoff:** To Dev (Major Winchester) for GREEN phase implementation. Suggested
implementation outline (Dev may adjust):

1. New module `sidequest/game/vessel_tags.py`:
   - `class VesselTags(BaseModel)`: `composure: int`, `composure_max: int`
   - `class InvalidVesselTagsError(ValueError)`: carries item id
   - `def parse_vessel_tags(item: dict) -> VesselTags`
   - `def find_vessel_item(items: list[dict]) -> dict | None`
2. New module `sidequest/game/rig_binding.py` (or add to `vessel_tags.py`):
   - `def bind_rig_pool_from_inventory(core: CreatureCore, *, character_id: str) -> RigComposurePool | None`
   - `def bind_rig_pools(snapshot: GameSnapshot) -> None`
3. Extend `sidequest/game/creature_core.py`:
   - Add `rig_pool: RigComposurePool | None = None` to `CreatureCore`
4. Export new symbols from `sidequest/game/__init__.py`:
   - `VesselTags`, `InvalidVesselTagsError`, `parse_vessel_tags`,
     `find_vessel_item`, `bind_rig_pool_from_inventory`, `bind_rig_pools`
5. Wire production caller — recommended site:
   `sidequest/server/dispatch/chargen_loadout.py` end of `apply_starting_loadout`
   (after `character.core.inventory.items.append(...)` loop). Alternative:
   `sidequest/server/websocket_session_handler.py` alongside
   `rebind_chassis_bonds_to_character`.

## Sm Assessment

Story 53-2 is a tightly scoped backend wiring story (3 pts, TDD) that consumes the
RigComposurePool class shipped in 53-1 and exposes it through the materializer so the
rest of Epic 53 (crash handler 53-3, OTEL surface 53-4, UI 53-5) has something concrete
to react to.

**Why now:** Epic 53 is P1, content has shipped, 53-1 is merged, and every other story
in this epic blocks on 53-2 producing a materialized pool in the snapshot. Without it
the rig remains a narrative prop — exactly the kind of "narrator improvises mechanical
state" failure mode CLAUDE.md's "Gaslight the narrator with game state" doctrine is
designed to prevent.

**Scope discipline:** Story owns the materializer scan, CreatureCore extension,
snapshot round-trip, the single `rig_pool.created` OTEL span, and the wiring test.
Crash handling, full GM-panel OTEL surface, UI, multi-rig ranking, and the slugify
fix are all *explicitly* deferred to later stories. The negative-path test for missing
`composure:N` tags enforces the "no silent fallbacks" rule at the data boundary.

**Risk:** Snapshot persistence of a new optional Pydantic field on CreatureCore is
the most likely surprise — Pydantic v2 + SQLite should round-trip cleanly, but if it
doesn't, Dev should log a Design Deviation rather than silently migrate the schema.
The "first vessel item wins" simplification is documented as an assumption, not a
permanent design choice.

**Handoff:** TDD workflow — TEA writes failing tests first (red), Dev implements to
green, Reviewer audits, finish ceremony archives. Branch already cut off develop
in sidequest-server.