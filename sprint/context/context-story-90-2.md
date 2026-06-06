---
parent: context-epic-90.md
workflow: tdd
---

# Story 90-2: WWN/ADR-126 magic plugin not instantiated at session-bind

## Business Context

This story unblocks live WWN magic proof for the epic. Story 87-4 identified that long_foundry (WWN ruleset) ships a valid `magic.yaml` configuration, but at runtime `snapshot.magic_state` is None, so the narrator's cast paths silently gate and no spells are resolved. The fix is foundational: instantiate the world's MagicPlugin into the session at bind time (before chargen), matching the pattern used for ruleset binding (ADR-117 / story 87-4). This gives the narrator a valid MagicState to validate against from the first turn — and surfaces magic subsystem presence to the GM panel via OTEL (per CLAUDE.md Observability Principle).

The value: once magic_state exists at bind time, chargen confirmation reuses it (adding character-scope bars), and the full magic lifecycle is wired. Story 90-3 (live free-play proof) depends on this.

## Technical Guardrails

**Files to modify:**
- `sidequest/server/session_room.py` — `bind_world()` method; add world-scope magic init call
- `sidequest/server/magic_init.py` — refactor `init_magic_state_for_session` into two helpers (world-scope + character registration)
- `sidequest/handlers/connect.py` — ensure post-bind-world magic init is called; verify chargen reuses existing state

**Patterns to follow (epic 87-4 / ADR-117):**
- Session-bind is the right place to instantiate both ruleset (done at 87-4) and magic (this story)
- Emit OTEL spans for each lifecycle step: `magic.world_bound`, `magic.character_registered`
- Graceful degrade on malformed config: log ERROR, emit watcher event, continue (don't crash session-bind)
- No silent fallbacks: absence of magic.yaml is explicitly logged as a no-op

**Key integration points:**
1. `session_room.bind_world()` line 225–272 — call world-magic init here
2. `_chargen_confirmation()` (handlers/connect.py) — verify it reuses existing magic_state
3. `_backfill_magic_state_on_resume()` (handlers/connect.py line 141–205) — remains a no-op for post-init saves
4. OTEL watcher spans — verify GM panel surfaces `magic.world_bound` and `magic.character_registered`

**Dependencies and blockers:**
- None — this is self-contained; 90-1 (encountergen) is already merged and doesn't block this

## Scope Boundaries

**In scope:**
- Refactor `init_magic_state_for_session()` to support world-only initialization (no character)
- Call world-magic init from session-bind (immediately after `bind_world()` completes)
- Update chargen path to reuse the bound magic_state instead of building a fresh one
- Emit `magic.world_bound` OTEL span at bind time
- Emit `magic.character_registered` OTEL span at chargen confirmation (delta reporting)
- Test: fresh long_foundry session → bind → chargen → spell cast in free-play (AC6 integration test)
- Test: old save without magic_state → resume → backfill gracefully (AC3)

**Out of scope:**
- Chargen UI changes (magic.yaml is already wired for narration, not player-facing)
- Interruption on DEEP_RED flags (that's a named future extension per ADR-126)
- Per-character magic customization at chargen (out of scope; magic config is world-level)
- Daemon music / audio integration (orthogonal)

## AC Context

**AC1: World-scope magic_state at bind time**

When the connect handler calls `room.bind_world(snapshot, store, world_dir, ruleset)`, the session-bind logic should:
- Load `{genre_pack_source_dir}/magic.yaml` and `{genre_pack_source_dir}/worlds/{world_slug}/magic.yaml`
- Call `MagicState.from_config(config)` with an empty character ledger (no character ID yet)
- Assign the built state to `snapshot.magic_state`
- Emit `magic.world_bound` OTEL span with:
  - `world_slug` (e.g., "long_foundry")
  - `active_plugins` (list, e.g., ["learned_v1"])
  - `bar_count` (should be 0 or the count of world-scope bars, if any)
- Worlds without magic.yaml skip this entirely (log at DEBUG, no error)

Test: Snapshot a fresh long_foundry world-bind, assert `snapshot.magic_state is not None` and `snapshot.magic_state.ledger == {}` (empty until character commits).

**AC2: Chargen flow reuses world magic_state**

When `_chargen_confirmation()` runs (chargen selection → confirm):
- Check if `snapshot.magic_state` is already present (bound at world-bind)
- If present, call `snapshot.magic_state.add_character(character_id, character_class)` (existing method)
- If absent (shouldn't happen post-fix, but handle it), fall back to building a fresh state (existing behavior, for old saves)
- Emit `magic.character_registered` OTEL span with:
  - `character_id` (e.g., "Rux")
  - `character_class` (e.g., "Mage")
  - `bar_count_delta` (e.g., 2 — two new character-scope bars added)

Test: Long_foundry chargen confirmation; verify `snapshot.magic_state.ledger` now contains keys like `character|Rux|slots_l1`, `character|Rux|slots_l2`.

**AC3: Resume backfill remains a no-op for post-init saves**

For saves created after this story is merged:
- `snapshot.magic_state` will be populated at world-bind time
- On resume, `_backfill_magic_state_on_resume()` checks `if snapshot.magic_state is not None: return` early
- Backfill does NOT fire; no re-init occurs
- For old saves (pre-fix, magic_state=None), backfill still triggers and gracefully rebuilds

Test: Save a game post-fix (magic_state populated), disconnect, reconnect, verify backfill span does NOT fire and state is unchanged.

**AC4: OTEL lie-detector surfaces magic subsystem engagement**

The GM panel must be able to see:
- `magic.world_bound` span fires when the first player connects and world-bind completes
- `magic.character_registered` span fires when chargen confirmation commits
- No silent no-ops: if magic.yaml is missing, the watcher event is `magic.init_skipped` (existing behavior)
- If magic.yaml is malformed, `magic.init_failed` with error details (existing behavior)

Test: Run long_foundry in Jaeger, connect and confirm chargen, verify the span sequence in the waterfall.

**AC5: No silent failures**

- If `magic.yaml` is malformed, `init_world_magic_state()` catches LoaderError, logs ERROR, emits `magic.init_failed` watcher event, and continues (magic_state remains None)
- If `magic.yaml` is absent, log at DEBUG (no error), emit `magic.init_skipped`, and continue (magic_state remains None, expected for non-magic worlds)
- Session-bind does NOT crash; the world binds cleanly regardless

Test: Inject a malformed magic.yaml in long_foundry, bind a session, verify the error log and watcher event, verify the session still connects.

**AC6: Integration test — long_foundry fresh session, world-bind + chargen + free-play**

End-to-end workflow:
1. Start server + UI
2. Connect to long_foundry, select Mage class, confirm chargen
3. Assert `snapshot.magic_state is not None` at bind time (before chargen)
4. Assert character-scope bars are present after chargen (slots_l1, slots_l2)
5. In free-play, a narrator turn that casts a spell should:
   - Emit `magic_working` in the game_patch
   - Validator runs and produces flags (yellow/red/deep_red)
   - Flags are surfaced in OTEL (watcher event `magic.validate_working`)
   - Narrator prose describes the spell effect
6. Verify Jaeger shows the full span sequence: `magic.world_bound` → chargen → `magic.character_registered` → cast → `magic.validate_working`

This test is identical to story 90-3 AC5b, but run once here to prove 90-2 is sufficient.

## Assumptions

- **Technical:**
  - `init_magic_state_for_session()` can be refactored without breaking chargen (it currently requires a character_id, but we'll make it optional)
  - `MagicState.from_config(config)` works with an empty ledger (no character_id passed)
  - `snapshot.magic_state.add_character()` is idempotent (calling it twice on the same actor is a no-op or safe)
  - World-bind happens exactly once per session (not re-bound across multiple connects)
  - Genre pack's `source_dir` is always available in the connect context (yes, it's loaded for ruleset binding)

- **Domain:**
  - Long_foundry's magic.yaml is valid YAML (it is; verified manually)
  - World-scope magic (if any) uses bar keys that don't conflict with character-scope keys (ADR-126 enforces this via scope prefixing)
  - Worlds without magic.yaml are common and expected (yes; many genres don't model magic at all)

- **Dependency:**
  - Story 90-1 (encountergen) is already merged (it is; verified in current sprint)
  - ADR-126 (pluggable magic system) is the canonical spec (yes; this story implements the integration gap ADR-126 left)

## Interaction Patterns

Not applicable (server-side backend fix, no UI flow changes).

## Accessibility Requirements

Not applicable (server-side logic, no user-facing UI).

## Visual Constraints

Not applicable (server-side logic).
