---
story_id: "90-2"
jira_key: ""
epic: "90"
workflow: "tdd"
---
# Story 90-2: WWN/ADR-126 magic plugin not instantiated at session-bind — long_foundry ships magic.yaml but runtime snapshot.magic_state is None, so cast paths gate; instantiate the world MagicPlugin into the session and assert magic_state present via OTEL

## Story Details
- **ID:** 90-2
- **Epic:** 90 (Ruleset-Module Worlds — Live Combat & Magic Verification Enablement)
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Type:** bug
- **Points:** 5
- **Stack Parent:** none
- **Branch:** feat/90-2-wwn-magic-plugin-instantiate
- **Branch Strategy:** gitflow (develop → feat/90-2-...)
- **Repo:** sidequest-server

## Problem Statement

Long_foundry (heavy_metal, WWN ruleset) ships a `magic.yaml` configuration file with the learned_v1 magic plugin active. However, when a session binds to the world during the connect handler, `snapshot.magic_state` remains `None`. This means:

1. The narrator cannot check if a character's magic working is valid (no MagicState to validate against)
2. Cast paths gate on `if snapshot.magic_state is None`, silently no-oping
3. WWN spell resolution never fires even when the narrator triggers it
4. The GM panel's lie-detector (OTEL observability) cannot verify magic subsystem engagement

Per story 87-4 AC5 findings, this is the gap blocking live OTEL proof of WWN magic: the plugin is loaded in code (ADR-126) but never instantiated into the runtime session.

## Root Cause Analysis

Current flow:
1. Connect handler calls `room.bind_world(snapshot)` at line 664/707 — snapshot is fresh or loaded, magic_state is None
2. Session-bind does NOT instantiate magic — it only wires the orbital tier and ruleset slug
3. chargen confirmation calls `init_magic_state_for_session()` — but only when a CHARACTER commits, not when the world binds
4. On a resume (load saved game), the backfill at line 542 (`_backfill_magic_state_on_resume`) tries to rebuild magic_state, but only if characters already exist

The gap: **session-bind does not instantiate magic_state; it waits for chargen confirmation or resume backfill. For a fresh session before any character is created, magic_state is invisible to the narrator.**

## Solution Approach

Instantiate the world's MagicPlugin at session-bind time (in `room.bind_world` or immediately after), keyed on the world's `magic.yaml` alone, NOT on a character (since chargen hasn't happened yet). This gives the narrator a valid MagicState to validate against throughout the session — even before the first character commits.

### Technical Flow

1. **At session-bind (connect handler, post-`bind_world` call):**
   - Extract `world_slug` and `genre_pack.source_dir` from the local context
   - Call a new helper `init_world_magic_state` (or rename/refactor the existing `init_magic_state_for_session`) with a signature that accepts optional `character_id`
   - Load `magic.yaml` from genre/world paths
   - Build `MagicState.from_config(config)` with an **empty ledger** (no character-keyed bars yet)
   - Assign to `snapshot.magic_state`
   - Emit an OTEL span `magic.world_bound` with attributes: `world_slug`, `active_plugins`, `bar_count` (should be 0 or world-scope only)

2. **At chargen confirmation (existing `_chargen_confirmation` path):**
   - If `snapshot.magic_state` already exists (populated at bind time), **reuse it**
   - Call `state.add_character(character_id, character_class)` to register the PC and instantiate character-scope bars
   - Emit an OTEL span `magic.character_registered` with attributes: `character_id`, `character_class`, `bar_count_delta`

3. **On resume (existing `_backfill_magic_state_on_resume` path):**
   - Remain unchanged — the world bind already populated magic_state, so backfill only triggers if it's missing (old saves)

### Implementation Sketch

**Option A: Refactor `init_magic_state_for_session` signature**
- Split into two functions:
  - `init_world_magic_state(genre_pack_source_dir, world_slug)` → MagicState with no character-scope bars
  - `register_character_with_magic_state(state, character_id, character_class)` → mutates state
- Call the first at session-bind; call the second at chargen confirmation
- Pros: clean separation; existing chargen code reuses the registration helper
- Cons: requires refactoring the existing `init_magic_state_for_session`

**Option B: Make `character_id` fully optional**
- Change `init_magic_state_for_session` signature to accept `character_id: str | None = None`
- If `None`, build and assign a bare MagicState (world scope only), emit `magic.world_bound` span
- If provided, add the character (existing behavior), emit `magic.character_registered` span
- Call from bind-time path with `None`, from chargen with the character ID
- Pros: minimal refactor; reuses all existing machinery
- Cons: conflates two concerns in one function

**Recommendation: Option A** (cleaner separation of concerns, aligns with ADR-126's contract model).

## Acceptance Criteria

### AC1: World-scope magic_state at bind time
- [ ] When `room.bind_world()` completes, `snapshot.magic_state` is NOT None (if world ships magic.yaml)
- [ ] magic_state carries the world's active plugins (e.g., `["learned_v1"]` for long_foundry)
- [ ] magic_state ledger is empty (no character-scope bars yet)
- [ ] OTEL span `magic.world_bound` fires with attributes: `world_slug`, `active_plugins`, `bar_count=0` (or number of world-scope bars if any)
- [ ] Worlds without magic.yaml cleanly leave magic_state as None (no error)

### AC2: Chargen flow reuses world magic_state
- [ ] Chargen confirmation calls `state.add_character(character_id, character_class)` on the existing magic_state (not rebuild)
- [ ] After commit, snapshot.magic_state has character-scope bars (e.g., `character|Rux|sanity` for innate_v1)
- [ ] OTEL span `magic.character_registered` emits with attributes: `character_id`, `character_class`, `bar_count_delta` (delta from before/after)
- [ ] Long_foundry Mage chargen produces bars (e.g., `slots_l1`, `slots_l2`) keyed on class magic_config

### AC3: Resume backfill remains a no-op for post-init saves
- [ ] A save created post-fix (with magic_state already populated) resumes cleanly
- [ ] Backfill does not re-initialize or clobber the loaded magic_state
- [ ] Old saves (pre-fix, magic_state=None) still trigger backfill gracefully

### AC4: OTEL lie-detector surfaces magic subsystem engagement
- [ ] GM panel `magic.world_bound` span is visible on first slug-connect (before chargen)
- [ ] GM panel `magic.character_registered` span is visible after chargen confirmation
- [ ] The OTEL span chain confirms magic_state presence and plugin activation across the session lifecycle
- [ ] Test: run long_foundry free-play, check Jaeger for the span sequence

### AC5: No silent failures
- [ ] If magic.yaml is malformed, `init_world_magic_state` logs ERROR and emits a watcher event (existing graceful-degrade pattern from `magic_init.py`)
- [ ] Session bind does NOT crash; magic_state remains None and narrator silently no-ops (same as today, but with an OTEL event so it's visible)
- [ ] Test: break genre/world magic.yaml, verify the error is logged and the span is emitted

### AC6: Integration test — long_foundry fresh session, world-bind + chargen + free-play
- [ ] Create a fresh long_foundry session (connect, select class Mage, confirm)
- [ ] Verify snapshot.magic_state is NOT None at bind time (AC1)
- [ ] Verify character-scope bars appear after chargen (AC2)
- [ ] Cast a spell in play, verify narrator resolves it (magic subsystem active, not gated by missing state)
- [ ] Verify OTEL spans in Jaeger: `magic.world_bound` → chargen → `magic.character_registered` → cast resolution

## Dependencies

- ADR-126: Pluggable Magic System (plugin protocol, import-time registry, validator)
- ADR-117: Pluggable Ruleset Module System (ruleset binding at session-bind; magic_state should follow similar pattern)
- story 87-4: RulesetModule instantiation at session-bind (parallel concern; magic follows the same gate as ruleset)
- story 90-1: encountergen ruleset-awareness (upstream; enables 90-2 content-side testing)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-06T13:04:17Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-06 | 2026-06-06T12:20:58Z | 12h 20m |
| red | 2026-06-06T12:20:58Z | 2026-06-06T12:30:26Z | 9m 28s |
| green | 2026-06-06T12:30:26Z | 2026-06-06T12:42:47Z | 12m 21s |
| review | 2026-06-06T12:42:47Z | 2026-06-06T12:51:24Z | 8m 37s |
| green | 2026-06-06T12:51:24Z | 2026-06-06T12:58:01Z | 6m 37s |
| review | 2026-06-06T12:58:01Z | 2026-06-06T13:04:17Z | 6m 16s |
| finish | 2026-06-06T13:04:17Z | - | - |

## Delivery Findings

### TEA (test design)
- **Gap** (blocking): The story's *named subject* — long_foundry — cannot reach
  GREEN within server-only scope. heavy_metal ships NO genre-level `magic.yaml`,
  yet `load_world_magic` (sidequest/genre/magic_loader.py:62) hard-requires
  `genre_yaml.exists()` and raises `LoaderError` otherwise. Every other magic
  world (space_opera/coyote_star) ships BOTH genre + world `magic.yaml`. So no
  amount of bind-time wiring will populate `magic_state` for long_foundry — the
  config physically cannot load. Affects `sidequest-content/genre_packs/heavy_metal/`
  (needs a genre-level `magic.yaml`) OR `sidequest-server/sidequest/genre/magic_loader.py`
  (relax to support world-only magic). This is a **content-repo / loader decision
  outside this server-only story's declared repos**. The CODE fix (world-bind
  instantiation) is real, valuable, and world-agnostic — coyote_star proves it —
  but story AC1/AC6 *as written against long_foundry* are unsatisfiable until the
  genre-magic gap is resolved. Recommend Architect/PM scope a sibling (content or
  loader) story; 90-2 should retarget its acceptance to coyote_star, or depend on
  the content fix. *Found by TEA during test design.*
- **Improvement** (non-blocking): The bug is NOT long_foundry-specific. `magic_state`
  is None at bind for ANY magic world (coyote_star included) because
  `init_magic_state_for_session` only runs at chargen-confirm + resume-backfill,
  never at bind. The world-bind hook benefits every magic world, not just WWN ones.
  Affects `sidequest/server/magic_init.py` + `sidequest/server/session_room.py`.
  *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (blocking): Confirmed TEA's long_foundry finding from the implementation
  side. The code fix is in and proven world-agnostic (coyote_star: 11 tests GREEN,
  full magic+server suite 3407 passed). But long_foundry magic still will not load
  at runtime — `load_world_magic` raises `LoaderError` on the missing heavy_metal
  genre `magic.yaml`, which `init_world_magic_state` catches → `magic.init_failed` →
  `magic_state` stays None. So the *named subject* is still dark until a content or
  loader decision lands. Affects `sidequest-content/genre_packs/heavy_metal/` (ship a
  genre `magic.yaml`) OR `sidequest/genre/magic_loader.py` (support world-only magic).
  Out of this server-only story's repo scope — needs Architect/PM. *Found by Dev during
  implementation.*

### Reviewer (code review)
- **Gap** (blocking): `ruff check .` fails repo-wide — `I001` import-sort on the new test file. Dev's lint pass only covered the two production files, so the test file's import block + stale `# noqa: E402` slipped through; this fails SM's `check-all` finish gate. Affects `tests/server/test_magic_world_bind.py` (`ruff check --fix` + drop the noqa). *Found by Reviewer during code review.*
- **Conflict** (non-blocking): The `bind_world` function-local import comment asserts an "import cycle" that does not exist — `magic_init` does not import `session_room`. The real concern is startup-order sensitivity via `game.ruleset.native → server.dispatch`. Affects `sidequest/server/session_room.py:282` (correct the comment or promote to top-level after verifying startup order). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `init_world_magic_state` skip paths emit a watcher event but no `logger.info()`, unlike the function's success/error paths — the skip is OTEL-visible but silent in server-log tails. Affects `sidequest/server/magic_init.py:189,:203`. *Found by Reviewer during code review.*

#### Reviewer (code review — Round 2)
- **Improvement** (non-blocking): All three Round 1 Reviewer code-review findings above are RESOLVED on `ed83868e` — `ruff check .` clean repo-wide, import comment corrected to "startup-order hazard", `logger.info` added to both skip paths. Verified independently + by rule-checker (0/47 violations) and preflight. *Found by Reviewer during Round 2 re-review.*
- **Improvement** (non-blocking): Fixture docstring still carries a stale RED-era rationale for `raising=False` ("installs cleanly in RED even before the symbol is referenced") — the symbol (`_watcher_publish`) already exists; the real rationale is rename-defense. Affects `tests/server/test_magic_world_bind.py:71` (rewrite the docstring). LOW — doc accuracy only; non-blocking, opportunistic cleanup. *Found by Reviewer during Round 2 re-review.*
- **Improvement** (non-blocking): Wiring test precondition `assert room.snapshot is not None` (line 439, no message) precedes the load-bearing `magic_state` check; on a future regression the failure message would point at the precondition, not the real defect. Affects `tests/server/test_magic_world_bind.py:439` (fold into the meaningful assertion or add a message). LOW, low-confidence; non-blocking. *Found by Reviewer during Round 2 re-review.*

## Design Deviations

### TEA (test design)
- **Test vehicle is coyote_star, not the story-named long_foundry**
  - Spec source: context-story-90-2.md, AC1/AC6 ("Snapshot a fresh long_foundry world-bind")
  - Spec text: "Create a fresh long_foundry session ... assert snapshot.magic_state is not None at bind time"
  - Implementation: AC tests target `space_opera/coyote_star` (complete, loadable genre+world magic.yaml) instead of long_foundry.
  - Rationale: long_foundry's magic cannot load (no heavy_metal genre magic.yaml — see blocking Delivery Finding). coyote_star exhibits the identical world-agnostic defect (magic_state None at bind) and is the established magic fixture. Testing the code fix on a loadable world keeps RED failing for the *code* reason, not a content gap.
  - Severity: major
  - Forward impact: long_foundry-specific AC6 remains unproven until the genre-magic content gap is closed; a follow-up must re-run AC6 against long_foundry once heavy_metal ships genre magic.yaml.
- **Wiring test targets the `bind_world` seam, not the full connect handler**
  - Spec source: context-story-90-2.md, Technical Guardrails (integration points 1–2: session_room.bind_world + handlers/connect.py)
  - Spec text: "Call world-magic init from session-bind (immediately after `bind_world()` completes)"
  - Implementation: `test_bind_world_instantiates_magic_state` drives `SessionRoom.bind_world(world_dir=...)` directly and asserts `room.snapshot.magic_state` is populated. It does NOT drive the async connect handler end-to-end.
  - Rationale: the connect handler needs full DB + WebSocket + registry infra to run; `bind_world` is the unit-testable world-bind seam and already receives the resolved `world_dir` (from which source_dir/world_slug derive). Server CLAUDE.md forbids source-grep wiring tests, so this is a behavior-driven seam assertion. It pushes Dev toward wiring world-magic init into `bind_world` (the cohesive, testable placement). If Dev instead wires it only into the connect handler, this test stays RED — an intentional design pressure toward the testable seam.
  - Severity: minor
  - Forward impact: if the chosen design puts the hook in the connect handler instead of bind_world, the wiring test must be retargeted; the AC-behavior tests on `init_world_magic_state` are unaffected.
- **AC targets `init_world_magic_state` (Option A) as the concrete API surface**
  - Spec source: context-story-90-2.md, Scope ("Refactor `init_magic_state_for_session()` to support world-only initialization")
  - Spec text: "Recommendation: Option A (cleaner separation of concerns)"
  - Implementation: tests import and call a new `init_world_magic_state(snapshot, genre_pack_source_dir, world_slug)`.
  - Rationale: the spec recommends Option A and the new function is the clearest testable surface. If Dev elects Option B (optional `character_id=None`), the function-name assertions need adjusting but every behavioral assertion transfers.
  - Severity: minor
  - Forward impact: none if Dev follows the recommended Option A.

### Dev (implementation)
- **No `magic.character_registered` span added; relied on existing `magic.init` (first_commit=False)**
  - Spec source: context-story-90-2.md, AC2/AC4
  - Spec text: "Emit `magic.character_registered` OTEL span at chargen confirmation (delta reporting)"
  - Implementation: Left the chargen path's existing `magic.init` watcher event (which already reports `first_commit=False` on the reuse branch) as the GM-panel signal for character registration after world-bind. Did NOT add a new `magic.character_registered` span.
  - Rationale: TEA's tests (highest authority after session scope) assert `magic.init` with `first_commit=False`, not a new span. The existing event already gives the GM panel distinct visibility of the reuse commit, satisfying AC4's observability intent with zero new surface. Adding a second event for the same moment would be redundant (minimalist discipline).
  - Severity: minor
  - Forward impact: if a future consumer keys specifically on a `magic.character_registered` event name, it must use `magic.init`+`first_commit=False` instead.
- **Wired world-magic init into `bind_world` only; did not separately edit `handlers/connect.py`**
  - Spec source: context-story-90-2.md, Technical Guardrails (integration point 3 lists handlers/connect.py)
  - Spec text: "ensure post-bind-world magic init is called" in the connect handler
  - Implementation: Placed the `init_world_magic_state` call inside `SessionRoom.bind_world` (deriving source_dir/world_slug from the already-passed `world_dir`). Both connect-handler bind branches (connect.py:664, :707) route through `bind_world`, so they inherit the hook with no connect.py change.
  - Rationale: `bind_world` is the single cohesive world-bind seam both branches already call; adding the hook there avoids duplicating the call at two sites and is the unit-testable placement TEA's wiring test targets. Less code, one source of truth.
  - Severity: minor
  - Forward impact: none — any future bind caller gets world-magic init for free.
- **Extracted `_load_world_confrontations` helper; refactored the existing chargen first-commit branch to use it**
  - Spec source: TEA tests + existing magic_init.py first-commit confrontations block
  - Spec text: (no explicit spec; DRY between the two world-load paths)
  - Implementation: Pulled the ~25-line confrontations-load-and-degrade block out of `init_magic_state_for_session` into a shared `_load_world_confrontations`, called by both it and the new `init_world_magic_state`.
  - Rationale: avoid duplicating the graceful-degrade confrontations logic across two entry points. Behavior-preserving — full magic suite (3407 tests) stays GREEN.
  - Severity: minor
  - Forward impact: none — single source of truth for confrontations loading.
- **Review-rework round 2: no new deviations**
  - Spec source: Reviewer Assessment (REJECTED, round 1)
  - Spec text: lint blocker + comment accuracy + test-assertion findings
  - Implementation: All fixes were hygiene/accuracy corrections to existing behavior — lint sort, comment rewrites, added `logger.info` to skip paths, tightened test assertions. No behavior change, no spec divergence.
  - Rationale: Reviewer findings were all green-phase cleanups; addressing them introduced no new deviation from the story spec.
  - Severity: trivial
  - Forward impact: none.

### Reviewer (audit)
- **TEA: Test vehicle is coyote_star, not long_foundry** → ✓ ACCEPTED by Reviewer: sound — long_foundry magic genuinely cannot load (verified: heavy_metal ships no genre magic.yaml; `magic_init` does not import `session_room`), and coyote_star reproduces the identical world-agnostic defect. Testing the code fix on a loadable world is the correct call. The long_foundry gap is correctly escalated as a blocking Delivery Finding.
- **TEA: Wiring test targets the `bind_world` seam, not the full connect handler** → ✓ ACCEPTED by Reviewer: correct — driving the async connect handler needs full DB/WS infra; `bind_world` is the unit-testable world-bind seam and the wiring test is behavior-driven (not a source grep), complying with the No-Source-Text-Wiring-Tests rule.
- **TEA: AC targets `init_world_magic_state` (Option A)** → ✓ ACCEPTED by Reviewer: matches the context's stated recommendation; Dev implemented Option A as specified.
- **Dev: No `magic.character_registered` span; relied on `magic.init` (first_commit=False)** → ✓ ACCEPTED by Reviewer: reasonable — the existing `magic.init` event with `first_commit=False` already gives the GM panel distinct visibility of the reuse commit, and TEA's tests assert exactly that. Adding a redundant span would be scope creep. (Forward note preserved for any future consumer keying on the span name.)
- **Dev: Wired into `bind_world` only, not `handlers/connect.py`** → ✓ ACCEPTED by Reviewer: both connect bind branches (664, 707) route through `bind_world`, so the single-seam placement covers them with less code and is the testable site. Verified the resume-ordering interaction (backfill at :542 precedes bind at :664) is safe.
- **Dev: Extracted `_load_world_confrontations` helper** → ✓ ACCEPTED by Reviewer: net simplification (~25 lines de-duplicated), behavior-preserving, full suite green. No concern.
- **Review-rework round 2: no new deviations** → ✓ ACCEPTED by Reviewer (Round 2): confirmed — the rework was pure hygiene (lint sort, comment rewrites, added `logger.info`, tightened 4 test assertions); no behavior change, no spec divergence. Verified clean by all 4 enabled specialists.

## Sm Assessment

Story 90-2 is a well-scoped p2 server-side bug fix from the Ruleset-Module Worlds epic (90). The defect is concrete and observable: long_foundry ships `magic.yaml` but `snapshot.magic_state` is `None` at runtime because the MagicPlugin (ADR-126) is only instantiated at chargen confirmation, not at world-bind. Cast paths therefore gate.

**Why this is ready:** The root cause is identified, the fix is localized to the server's magic + session-bind path, and there is a clear OTEL acceptance hook ("assert magic_state present via OTEL") that gives the GM panel a lie-detector — fully aligned with the project's OTEL Observability Principle. The setup subagent has documented two solution options with a recommendation (Option A: split `init_magic_state_for_session` into world-scope and character-scope), plus resume-backfill handling.

**Why TDD fits:** The failure is assertable (magic_state None → present) and demands a wiring test (ADR-126 plugin actually instantiated and reachable from the cast path, not merely constructed). This is exactly the "Every Test Suite Needs a Wiring Test" case — TEA should author a failing test proving the plugin is bound into the session snapshot before Dev makes it green.

**Unblocks:** Story 90-3 (AC5b live free-play OTEL proof) depends on this firing.

**Routing:** Phased TDD workflow → handing off to TEA (Mr. Praline) for the red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Backend bug fix with an assertable contract (magic_state None → populated at bind) and a load-bearing OTEL hook.

**Test Files:**
- `tests/server/test_magic_world_bind.py` — 11 tests covering the world-bind magic initializer and its wiring.

**Tests Written:** 11 tests covering ACs 1, 2, 3, 5 + the bind_world wiring seam.
**Status:** RED — `ImportError: cannot import name 'init_world_magic_state'` (function not yet implemented). Verified by testing-runner (RUN_ID 90-2-tea-red): collection ERROR, 1 import error, 0 passed. Correct RED for "the world-bind initializer does not exist."

### AC Coverage

| AC | Behavior | Test(s) | Status |
|----|----------|---------|--------|
| AC1 | world-scope magic_state at bind, no character bars | `test_init_world_magic_state_populates_without_character` | RED |
| AC1/AC4 | `magic.world_bound` OTEL event (world_slug, active_plugins, bar_count) | `test_init_world_magic_state_emits_world_bound_event` | RED |
| AC2 | chargen reuses bound state, adds character bars | `test_chargen_reuses_world_bound_magic_state` | RED |
| AC2/AC4 | chargen commit is `first_commit=False` after bind (OTEL proof of reuse) | `test_chargen_after_world_bind_is_a_reuse_commit` | RED |
| AC3 | resume backfill no-op when state already bound | `test_backfill_no_op_after_world_bind` | RED |
| AC5 | no magic.yaml → skip, `magic.init_skipped`, no crash | `test_init_world_magic_state_skips_world_without_magic_yaml` | RED |
| AC5 | source_dir None → skip, magic_state None | `test_init_world_magic_state_skips_when_source_dir_none` | RED |
| AC5 | malformed yaml → ERROR log + `magic.init_failed`, no raise | `test_init_world_magic_state_logs_loader_error_without_raising` | RED |
| — | idempotent: second bind reuses, never clobbers | `test_init_world_magic_state_idempotent_does_not_clobber` | RED |
| Wiring | `bind_world` instantiates magic_state + emits `magic.world_bound` | `test_bind_world_instantiates_magic_state` | RED |
| Wiring | non-magic world binds cleanly, magic_state stays None | `test_bind_world_leaves_nonmagic_world_state_none` | RED |

**Wiring test:** Yes — `test_bind_world_instantiates_magic_state` drives the real
`SessionRoom.bind_world` seam (behavior-driven, not a source grep — server CLAUDE.md
forbids source-grep wiring assertions).
**Self-check:** 0 vacuous tests. Every assertion checks a concrete value (object
identity, ledger key prefixes, event fields with type+shape checks, no bare
`is_some`/`assert True`).

### ⚠️ Blocking finding for Dev/Architect (read before implementing)

The story names **long_foundry**, but its magic config **cannot load**: heavy_metal
ships no genre-level `magic.yaml` and `load_world_magic` hard-requires one. The code
fix is real and world-agnostic (proved against coyote_star), but the long_foundry
AC is unsatisfiable in server-only scope. See Delivery Findings → TEA (blocking Gap).
Decision needed: (a) ship a heavy_metal genre `magic.yaml` (content repo), (b) relax
the loader to support world-only magic, or (c) retarget 90-2's acceptance to
coyote_star and track long_foundry separately.

### Recommended GREEN path for Dev (Bicycle Repair Man)

1. Add `init_world_magic_state(*, snapshot, genre_pack_source_dir, world_slug) -> bool`
   to `sidequest/server/magic_init.py`: skip/loader-error paths identical to
   `init_magic_state_for_session`, but on success build `MagicState.from_config(config)`
   (+ load confrontations as the first-commit branch does), assign to
   `snapshot.magic_state`, emit `magic.world_bound` (world_slug, active_plugins,
   bar_count). Idempotent: return early if `snapshot.magic_state is not None`. NO
   `add_character` call.
2. Wire it into `SessionRoom.bind_world` on first bind (inside the lock, after
   `self._snapshot = snapshot`), deriving `genre_pack_source_dir = world_dir.parent.parent`
   and `world_slug = world_dir.name` from the already-passed `world_dir`. Guard on
   `world_dir is not None`.
3. The existing `init_magic_state_for_session` reuse branch (magic_init.py:253) already
   handles AC2 — once magic_state is pre-populated, chargen hits the `else` (reuse) path
   and reports `first_commit=False`. No change needed there beyond confirming it.

**Handoff:** To Dev (Bicycle Repair Man) for GREEN implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/magic_init.py` — added `init_world_magic_state(*, snapshot, genre_pack_source_dir, world_slug) -> bool` (world-scope MagicState build, idempotent, `magic.world_bound` OTEL event, loud skip/fail paths); extracted shared `_load_world_confrontations` helper and refactored the existing chargen first-commit branch to use it.
- `sidequest/server/session_room.py` — `bind_world` now calls `init_world_magic_state` on first bind (inside the lock), deriving pack source_dir + world_slug from the resolved `world_dir`; function-local import to avoid an import cycle.

**Tests:** 11/11 new (`tests/server/test_magic_world_bind.py`) GREEN. Broad regression: `tests/magic` + `tests/server` = 3407 passed / 0 failed / 188 skipped (baseline). Lint clean on both changed files (ruff).
**Branch:** `feat/90-2-wwn-magic-plugin-instantiate` (pushed to origin).

**ACs satisfied (against the coyote_star vehicle — see deviations):**
- AC1 ✅ world-scope magic_state at bind, no character bars, `magic.world_bound` emitted
- AC2 ✅ chargen reuses the bound state (same object), adds character bars, `first_commit=False`
- AC3 ✅ resume backfill no-op once state is bound
- AC4 ✅ OTEL: `magic.world_bound` at bind, `magic.init`/`first_commit=False` at chargen, `magic.init_skipped`/`magic.init_failed` on degrade
- AC5 ✅ missing/malformed config degrades loudly, never crashes the bind
- AC6 ⚠️ NOT proven against long_foundry — blocked by the content/loader gap (see Delivery Findings). The lifecycle IS proven against coyote_star.

**⚠️ Carries forward to Reviewer/Architect:** The story's named subject **long_foundry** is still dark at runtime — heavy_metal ships no genre `magic.yaml`, so `init_world_magic_state` hits the `LoaderError` → `magic_state` None path. The code fix is correct and world-agnostic; long_foundry specifically needs a content `magic.yaml` (sidequest-content) OR a loader change to support world-only magic (`sidequest/genre/magic_loader.py`) — both outside this server-only story's repo scope. Recommend a sibling story.

**Handoff:** To Reviewer (The Argument Professional) for code review.

### Dev Rework (round 2 — review findings addressed)

All Reviewer findings resolved (commit `ed83868e`):
- **[HIGH] lint blocker** — fixed `I001` import-sort on the test file and dropped the stale `# noqa: E402`. `ruff check .` now reports "All checks passed" (was the merge blocker).
- **[MEDIUM] import-comment accuracy** — rewrote the `bind_world` comment: it's a startup-order hazard (`game.ruleset.native → server.dispatch`), NOT a strict module cycle (`magic_init` does not import `session_room`). Noted the import can move top-level if startup order is later proven safe.
- **[LOW] skip-path logging** — added `logger.info` to both `init_world_magic_state` skip branches for server-log parity with the success/error paths.
- **[LOW] "never silent" docstring** — qualified: the idempotent re-bind path is intentionally silent (prior `magic.world_bound` already signalled engagement).
- **[LOW] bind_world docstring** — added a sentence documenting the magic-init side effect.
- **[LOW] stale RED comments** — module docstring, the import-block comment, and the "RED today" test docstring recast to past tense / removed.
- **[LOW] test assertions** — tightened four: source_dir=None skip now asserts `magic.init_skipped`+reason; idempotent test asserts second call returns `False`; loader-error test pins `levelname == 'ERROR'`; non-magic wiring test asserts `magic.init_skipped`.

**Verification:** `ruff check .` clean; `test_magic_world_bind.py` 11/11 green; `tests/magic`+`tests/server` 3429 passed / 0 failed / 188 skipped. Branch pushed.

**Handoff:** Back to Reviewer (The Argument Professional) for re-review.

## Subagent Results

_(Round 2 re-review — supersedes Round 1. The four enabled specialists were
re-run against the reworked branch `ed83868e`. Round 1 REJECTED assessment is
preserved below under "Reviewer Assessment — Round 1 (REJECTED, superseded)".)_

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (lint blocker resolved, 11/11 green, no new smells) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 1 new (line 439 precondition assert ordering) + 4 R1 fixes confirmed | confirmed 1 (LOW, non-blocking); 4 R1 fixes verified |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 new (line 71 stale RED fixture docstring) + 5 R1 fixes confirmed | confirmed 1 (LOW, non-blocking); 5 R1 fixes verified clean |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 violations / 47 instances / 13 checks | N/A (all 5 R1 rule findings resolved) |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 0 blocking; 2 new LOW (non-blocking) confirmed; all 9 Round 1 findings verified fixed (lint blocker, import-comment, skip-path logger, "never silent" docstring, stale-RED comments, bind_world docstring, 4 test assertions).

## Reviewer Assessment

**Verdict:** APPROVED

Round 2 re-review of the reworked branch (`ed83868e`). I independently re-ran
`ruff check .` — **"All checks passed!"** — confirming the Round 1 [HIGH] lint
blocker, the only thing standing between this change and merge, is genuinely
resolved repo-wide (not just on the two production files). All four enabled
specialists corroborate: preflight clean (11/11 green, no new smells),
rule-checker clean (0/47 violations across 13 checks), test-analyzer confirms
all four assertion-gap fixes are non-vacuous, comment-analyzer confirms five of
six Round 1 doc findings clean. The production logic was already verified correct
in Round 1 (no logic bug, security hole, or silent failure in
`init_world_magic_state` / `bind_world`; resume-ordering idempotence holds) and
is unchanged in substance — the rework was lint + comments + test assertions.

Two **new LOW** findings surfaced in Round 2, both non-blocking (no Critical/High):

| Severity | Issue | Location | Note |
|----------|-------|----------|------|
| [LOW] | Fixture docstring still carries a RED-era rationale for `raising=False` ("installs cleanly in RED even before the symbol is referenced") — now stale; the real rationale is defense against future renames of the private `_watcher_publish` symbol. Same family as the Round 1 stale-RED findings; Dev cleaned the obvious ones but this one survived. `[DOC]` | `tests/server/test_magic_world_bind.py:71` | Independently verified. Doc accuracy only — code is correct. Capture as non-blocking follow-up. |
| [LOW] | Wiring test precondition `assert room.snapshot is not None` (no message) precedes the load-bearing `magic_state is not None` check; if `bind_world` ever left snapshot None the failure message would point at the precondition, not the real regression. `[TEST]` | `tests/server/test_magic_world_bind.py:439` | Independently verified. Diagnostic-clarity nit, low confidence. Non-blocking. |

Neither LOW finding justifies another rework round-trip; both are captured as
non-blocking delivery findings for opportunistic cleanup. **The change is
mergeable.**

**Carried-forward scope note (not a code-review blocker):** AC6 — the story's
named subject `long_foundry` — remains dark at runtime because heavy_metal ships
no genre `magic.yaml`, so `init_world_magic_state` hits the LoaderError → None
path for that world. The server-side fix is correct and world-agnostic (proven
against `coyote_star`); long_foundry needs a content `magic.yaml` or a
world-only-magic loader change, both outside this server-only story's repo scope.
Already logged in Delivery Findings as a sibling-story recommendation.

### Dispatch tags (gate completeness)
- `[EDGE]` — subagent disabled via settings; reviewer manually re-traced boundary paths (idempotent re-bind, missing/malformed yaml, source_dir None, non-magic world) on the reworked branch — all still handled, no finding.
- `[SILENT]` — subagent disabled; reviewer re-audited the two `except` blocks (`LoaderError`, `ConfrontationLoaderError`) plus the new `_load_world_confrontations` catch — all specific, logged at ERROR, watcher-published; the Round 1 skip-path-missing-logger gap is now fixed (logger.info added). No swallowed errors.
- `[TEST]` — test-analyzer confirms all 4 Round 1 assertion fixes non-vacuous; 1 new LOW (precondition ordering, line 439).
- `[DOC]` — comment-analyzer confirms 5/6 Round 1 doc findings clean; 1 new LOW (stale fixture docstring, line 71).
- `[TYPE]` — subagent disabled; reviewer re-checked: new public function fully annotated (`-> bool`, all params typed); helper `-> None`. No regression.
- `[SEC]` — subagent disabled; rule-checker check #11 + reviewer confirm `world_slug` is a server-internal path component, existence-gated, `yaml.safe_load` throughout. No injection surface.
- `[SIMPLE]` — subagent disabled; the `_load_world_confrontations` extraction remains a net simplification (removes duplication); the Round 1 lint/noqa concern is resolved.
- `[RULE]` — rule-checker clean: 0 violations across 47 instances / 13 checks; all 3 confirmed Round 1 rule findings (lint I001, import-comment accuracy, skip-path logger) resolved.

**Data flow traced (re-confirmed):** `world_dir` (genre loader, connect.py:452) → `bind_world` derives `genre_pack_source_dir = world_dir.parent.parent`, `world_slug = world_dir.name` → `init_world_magic_state` → `MagicState.from_config` (world-scope bars only) → `snapshot.magic_state`. Safe: `world_dir` server-internal, existence-gated.

**Pattern observed:** Idempotent-snapshot guard (`if snapshot.magic_state is not None: return False`) mirrors existing MP-aware idempotence in `init_magic_state_for_session` — consistent and correct.

**Error handling:** `LoaderError` / `ConfrontationLoaderError` caught specifically, logged at ERROR, watcher-published, never re-raised — session-bind cannot crash on authoring drift.

**Handoff:** To SM (The Announcer) for finish-story.

---

## Reviewer Assessment — Round 1 (REJECTED, superseded)

**Verdict:** REJECTED

The production logic is correct — across 47 rule instances and four specialists, **no logic bug, security hole, or silent-failure was found in `init_world_magic_state` or the `bind_world` wiring.** The resume-ordering regression risk I traced myself is clean (backfill at connect.py:542 runs before bind_world at :664, so the resumed character's bars are added first and the new bind-time init no-ops via idempotence). However, the change ships a **repo-wide lint failure** that blocks the merge gate, plus a misleading import-rationale comment and a cluster of stale RED-phase artifacts. Fix-and-resubmit.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | `ruff check .` fails repo-wide — `I001` import block un-sorted; the `from sidequest.server.magic_init import init_world_magic_state  # noqa: E402` sits out of sorted order. Dev's lint check only covered the two production files, not the test file. Blocks SM's `check-all` finish gate. `[RULE]` `[SIMPLE]` | `tests/server/test_magic_world_bind.py:31-48` | `uv run ruff check --fix tests/server/test_magic_world_bind.py` — and drop the now-unneeded `# noqa: E402` (RED-phase leftover). |
| [MEDIUM] | Import-rationale comment claims an "import cycle" that does not exist — `magic_init` does **not** import `session_room` (verified). The real hazard is startup-order sensitivity (`game.ruleset.native → server.dispatch`). The misdescription will mislead a future maintainer. `[RULE]` | `sidequest/server/session_room.py:282` | Either promote the import to module top-level (if startup order is safe) or correct the comment to describe the actual startup-order hazard, not a cycle. |
| [LOW] | `magic_init` skip paths emit a `magic.init_skipped` watcher event but no `logger.info()` — every other path in the function (success, LoaderError) has a paired logger line. Skip is OTEL-visible but silent in server-log tails. `[RULE]` | `sidequest/server/magic_init.py:189, :203` | Add a `logger.info("magic.init_skipped ...")` to each skip branch to match the function's own pattern. |
| [LOW] | Docstring claims emits "never silent," but the idempotent re-bind path (`magic_state is not None → return False`) emits nothing. `[DOC]` | `sidequest/server/magic_init.py:179` | Qualify: the idempotent path is intentionally silent (the prior `magic.world_bound` already signalled engagement). |
| [LOW] | Stale RED-phase comments/docstrings now that the code is GREEN: module docstring "Story 90-2 (RED)", the 3-line "this symbol does not exist yet" block above the import, and "This is RED today" in a test docstring. `[DOC]` | `tests/server/test_magic_world_bind.py:1, :45-48, :605` | Recast to past tense / remove the RED scaffolding. |
| [LOW] | `bind_world` docstring documents `world_dir` only for orbital loading — does not mention it now also triggers world-magic init. `[DOC]` | `sidequest/server/session_room.py:233` | Add a sentence noting `init_world_magic_state` is fired here (Story 90-2). |
| [LOW] | Test assertion gaps `[TEST]`: (a) `:211` source_dir-None skip test never asserts the `magic.init_skipped` event though the code emits it; (b) `:266` idempotent test never asserts the second call returns `False` (the documented contract); (c) `:254` loader-error test matches `'magic.init_failed' in message` but doesn't pin `levelname == 'ERROR'`; (d) `:436` non-magic wiring test doesn't assert `magic.init_skipped`. | `tests/server/test_magic_world_bind.py` | Tighten these four assertions (the `captured_magic_init_events` fixture is already wired in sibling tests). |

### Dispatch tags (gate completeness)
- `[EDGE]` — subagent disabled via settings; reviewer manually traced boundary paths (idempotent re-bind, missing/malformed yaml, source_dir None, non-magic world) — all handled, no finding.
- `[SILENT]` — subagent disabled; reviewer manually audited the two `except` blocks (`LoaderError`, `ConfrontationLoaderError`) — both specific, logged at ERROR, watcher-published. No swallowed errors. One *consistency* gap (skip-path missing logger) noted [LOW].
- `[TEST]` — confirmed 4 assertion-gap findings (above).
- `[DOC]` — confirmed 3 doc findings (stale RED comments, "never silent", bind_world docstring).
- `[TYPE]` — subagent disabled; reviewer checked: new public function fully annotated (`-> bool`, all params typed); helper `-> None`. No stringly-typed boundary. Fixture missing annotation is rule-exempt (private/test).
- `[SEC]` — subagent disabled; reviewer checked: `world_slug` is a server-internal path component (from the genre loader, not raw HTTP input), gated by `.exists()`; `yaml.safe_load` used throughout; no injection surface. No finding.
- `[SIMPLE]` — subagent disabled; reviewer checked: the `_load_world_confrontations` extraction removes ~25 lines of duplication — a net simplification. Folded the lint/noqa into [HIGH].
- `[RULE]` — confirmed 3 (lint I001, import-comment accuracy, skip-path logger); 1 exempt; 1 pre-existing.

**Data flow traced:** `world_dir` (resolved by genre loader at connect.py:452) → `bind_world` derives `genre_pack_source_dir = world_dir.parent.parent`, `world_slug = world_dir.name` → `init_world_magic_state` → `MagicState.from_config` (world-scope bars only) → `snapshot.magic_state`. Safe: `world_dir` is server-internal, not user-tainted; path is existence-gated before load.

**Pattern observed:** Idempotent-snapshot guard (`if snapshot.magic_state is not None: return False`) mirrors the existing MP-aware idempotence in `init_magic_state_for_session` — consistent and correct (session_room.py defense for re-bind).

**Error handling:** `LoaderError` and `ConfrontationLoaderError` both caught specifically, logged at ERROR, watcher-published, never re-raised — session-bind cannot crash on authoring drift. Verified at magic_init.py:218-238 and :121-144.

### Rule Compliance (Python lang-review, 13 checks)
- #1 Silent exceptions — COMPLIANT (2 catches, both specific + logged + watcher).
- #2 Mutable defaults — COMPLIANT (5 sigs checked; `character_class=None` scalar; dataclass uses `field(default_factory=...)`).
- #3 Type annotations at boundaries — COMPLIANT for new public surface; fixture/inner-helper gaps are rule-exempt (private/test).
- #4 Logging coverage/correctness — MINOR GAP [LOW]: skip paths watcher-only, no logger line (other paths consistent).
- #5 Path handling — COMPLIANT (pathlib throughout; `write_text(encoding=...)` in tests).
- #6 Test quality — MOSTLY COMPLIANT; 4 assertion-tightening findings [LOW], no vacuous assertions, monkeypatch targets the used alias correctly.
- #7 Resource leaks — COMPLIANT (no raw `open()`; `tmp_path` cleanup).
- #8 Unsafe deserialization — COMPLIANT (`yaml.safe_load`; loaders internal).
- #9 Async pitfalls — COMPLIANT (synchronous call inside existing `with self._lock`).
- #10 Import hygiene — FINDING [MEDIUM]: function-local import comment misdescribes a non-existent cycle.
- #11 Input validation — COMPLIANT (`world_slug` server-internal path component, existence-gated).
- #12 Dependency hygiene — COMPLIANT (no manifest changes).
- #13 Fix-introduced regressions — the local-import "fix" applies a heavier mechanism than a true cycle would require; tied to #10 [MEDIUM].

### Devil's Advocate
Let me argue this code is broken. First, the lint failure is not cosmetic theatre — it means the author's own verification ("lint clean on both changed files") was *scoped to exclude the file most likely to drift*, the test file. That same blind spot is why the stale RED comments survived: the GREEN author never re-read the RED scaffolding. If the author didn't notice "Story 90-2 (RED)" still sitting at the top of a passing test, what else did they not re-read? Second, the import-cycle comment is a landmine. A future maintainer doing legitimate refactoring will read "Local import avoids an import cycle," believe a cycle exists, and either preserve a now-unnecessary runtime import forever or — worse — "prove" there's no cycle, promote it to top-level, and trip the *real* startup-order hazard the comment failed to name (`game.ruleset.native → server.dispatch`). The comment actively misdirects. Third, consider the malicious/confused world author: ship a `magic.yaml` that parses but is structurally bogus. The LoaderError path catches it, logs ERROR, emits `magic.init_failed`, and the session binds with `magic_state=None` — but the *narrator still runs*. The player casts; the cast path gates silently; nothing on the player's screen says "magic is off in this world because your config is broken." That's by design (graceful degrade), but it means the only signal is the GM panel — and if the GM isn't watching, a broken-magic world is indistinguishable from a no-magic world. That's the exact "winging it" failure CLAUDE.md's OTEL principle exists to prevent, and the skip-path-missing-logger gap makes it one notch *more* invisible (no server-log line either). None of these are correctness bugs in the strict sense — the code does what it says — but the cumulative effect is a change that merges a red CI gate, ships a misleading maintenance comment, and leaves a thin observability seam. The lint alone is disqualifying; the rest should be cleaned in the same pass.

**Handoff:** Back to Dev (Bicycle Repair Man) for green rework — all findings are lint/comment/test-assertion cleanups; no new production behavior or failing-test authoring required.