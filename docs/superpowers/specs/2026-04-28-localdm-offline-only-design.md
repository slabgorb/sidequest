# LocalDM Offline-Only — Design

**Date:** 2026-04-28
**Author:** Architect (Leonard of Quirm)
**Status:** Approved — pending implementation
**Revision:** 2026-04-28 — Pivoted §Components item 5: dropped the
proposed runtime `turn_records.py` writer. The existing
`sidequest/corpus/` module already mines training pairs from saves; the
training corpus is an offline extraction concern, not a runtime write
path. See updated §Data Flow, §Storage, §Testing, §Success Criteria.

## Context

Solo-mode SideQuest turns measure ~60s wall-time. Tracing the critical path
revealed two sequential `claude -p` subprocesses per turn:

1. **LocalDM Haiku decomposer** at `websocket_session_handler.py:1200`
   (~5–10s, stateless, pays full system-prompt cost every turn).
2. **Narrator Opus** at `orchestrator.py:1498` (~15–30s).

LocalDM was added (per `2026-04-23-local-dm-decomposer-design.md`) after
ADR-067 collapsed the multi-agent pipeline. It produces a `DispatchPackage`
that the narrator's prompt currently consumes via the dispatch bank
(`reflect_absence`, `distinctive_detail_hint`, `npc_agency`) and the
visibility-redaction layer (Group G, MP-only).

LocalDM was tried with a persistent session and reverted to stateless on
2026-04-26 due to schema-drift on turn 2+. The full system prompt is
re-ingested every turn, which is why the cost is fixed and high.

ADR-073 envisages LocalDM eventually moving to a local fine-tuned model.
At that point its inline cost drops to milliseconds and the dispatch bank
can re-engage on the live turn.

## Decision

**Take LocalDM off the live turn entirely.** Capture turn inputs to a
training corpus on disk; run LocalDM (or its successor) offline against
that corpus for evaluation and fine-tuning.

The narrator becomes the sole LLM call required before NARRATION
emission. The dispatch bank, prompt redaction, and Group G visibility
machinery remain on disk as **dormant code** — clearly marked, ready to
re-wire when the local fast router lands.

## Goal & Non-Goals

### Goal

Remove ~5–10s from every solo and MP turn by eliminating the LocalDM
Haiku subprocess from the critical path. Establish a turn-record corpus
sufficient for offline LocalDM evaluation and ADR-073 fine-tuning.

### Non-Goals

- Not landing ADR-066 (persistent narrator session). Separate, additive.
- Not removing the `DispatchPackage` schema, the dispatch bank, or
  prompt redaction. They go dormant, not deleted.
- Not solving MP visibility redaction (Group G). When MP wiring lands
  it will need a replacement; out of scope here.
- Not building heuristic replacements for `reflect_absence`,
  `distinctive_detail_hint`, or `npc_agency`. If a missed enhancement
  bites in playtest, promote case-by-case.

## Architecture

### Today (~24–47s critical path)

```
PLAYER_ACTION
  → lore RAG embed                                 (3-5s)
  → LocalDM Haiku decompose                        (5-10s)   ← Claude CLI #1
  → orchestrator.run_narration_turn:
      build_narrator_prompt
        ├─ redact_dispatch_package
        ├─ run dispatch bank
        └─ inject subsystem outputs into prompt
      → narrator Opus                              (15-30s)  ← Claude CLI #2
  → state apply, persist, validator.submit
  → NARRATION frame
```

### After (~15–37s critical path)

```
PLAYER_ACTION
  → lore RAG embed                                 (3-5s)
  → orchestrator.run_narration_turn:
      build_narrator_prompt
        └─ dispatch_package is None → default zones only
      → narrator Opus                              (15-30s)  ← only Claude CLI
  → state apply, persist, validator.submit
  → NARRATION frame
```

The training corpus is mined offline from existing SQLite saves — no
runtime write path is added. The save's `events` table already captures
`PLAYER_ACTION` payloads and the `narrative_log` already captures
narration; `sidequest/corpus/miner.py` extracts `TrainingPair` JSONL on
demand.

The dispatch bank does not run on the live turn. It survives in code for
offline use and for the day a fast local router replaces LocalDM inline.

## Components & Changes

### Files that change

1. `sidequest/server/websocket_session_handler.py`
   - Remove `await sd.local_dm.decompose(...)` call at ~line 1200/1227.
   - Remove `turn_context.dispatch_package = dispatch_package` plumbing.
   - Remove `LocalDM` instantiation on `_SessionData`.
   - Add fire-and-forget call to new turn-record writer after frame
     emission.

2. `sidequest/agents/orchestrator.py`
   - `TurnContext.dispatch_package` field stays (typed `DispatchPackage |
     None`) but is `None` on every live turn.
   - `build_narrator_prompt`: when `dispatch_package is None`, skip the
     `redact_dispatch_package` call and the dispatch-bank execution
     block. Subsystem outputs are not injected into the prompt; the
     narrator builds its prompt from default zones only.

3. `sidequest/agents/local_dm.py`
   - Add the DORMANT marker block (see below) at the top of the file.
   - No instantiation in live code paths.
   - May be lifted into a small CLI under `sidequest/cli/` for offline
     corpus runs in a follow-up story.

4. `sidequest/agents/subsystems/*` and `sidequest/agents/prompt_redaction.py`
   - Add the same DORMANT marker block at the top of each file.
   - No live callers after the change.

**DORMANT marker block** (use verbatim, adjust `<filename>` per file):

```python
"""<filename> — DORMANT.

This module is not invoked on the live turn path as of 2026-04-28
(see docs/superpowers/specs/2026-04-28-localdm-offline-only-design.md).

It is preserved for two consumers:
  1. The offline LocalDM corpus runner (follow-up story).
  2. Re-engagement on the live path once ADR-073's local fine-tuned
     router replaces the Haiku CLI subprocess.

Unit tests for this module remain in `just check-all` so it does not
bit-rot. If you find yourself adding a live caller, you are landing
ADR-073 (or undoing this design); update both ends.
"""
```

5. **No new live writer.** The training corpus is mined offline from
   existing saves. `sidequest/corpus/` already provides:
   - `save_reader.py` — read-only iteration over `events` and
     `narrative_log` tables.
   - `miner.py` — extracts `TrainingPair` rows from a save.
   - `writer.py` — atomic JSONL emit.

   Implementation must verify the existing miner output is sufficient
   for offline LocalDM evaluation. If a field LocalDM needs is missing
   from the save's events/narrative_log, extend the **save schema** or
   the **miner**, not add a parallel runtime writer.

6. **OTEL spans**
   - Remove: `local_dm.decompose` span.
   - No new spans added (no runtime corpus writer to instrument).

### Files that survive untouched

- `sidequest/protocol/dispatch.py` — `DispatchPackage` schema.
- `sidequest/agents/subsystems/__init__.py` and individual subsystem
  modules (dormant).
- `sidequest/agents/prompt_redaction.py` (dormant).
- All MP visibility infrastructure.

## Data Flow

### Live turn

1. Client sends `PLAYER_ACTION { action }`.
2. `_handle_player_action` → `_execute_narration_turn`.
3. `_execute_narration_turn` calls `_retrieve_lore_for_turn` (unchanged).
4. `TurnContext` built with `dispatch_package=None`.
5. `orchestrator.run_narration_turn(action, turn_context)`:
   - `build_narrator_prompt` takes the `None`-dispatch path.
   - Narrator Opus subprocess runs.
6. State apply, persistence, validator submit (unchanged).
7. NARRATION frame emitted.

The existing persistence layer already writes `PLAYER_ACTION` to the
`events` table and narration to `narrative_log` — no additional
runtime corpus path is needed.

### Offline corpus path (existing infrastructure)

`sidequest/corpus/miner.py` reads saves via `SaveReader` and emits
`TrainingPair` JSONL. A future LocalDM offline runner consumes the
miner output. This story's responsibility is verifying the miner output
is sufficient — extending the miner or save schema if not.

### Storage

Saves live at `~/.sidequest/saves/<genre>/<world>/<player>/save.db` per
existing convention. Corpus JSONL is mined into a separate output path
chosen at mining time (the corpus writer refuses any path under the
saves root by design).

## Error Handling

### Narrator fails

Unchanged from today. The turn handler already has degraded-record
paths at `websocket_session_handler.py:1864`. Removing LocalDM does not
change narrator failure handling.

### Latent reader of `dispatch_package`

The implementation must grep every reader of
`turn_context.dispatch_package` and confirm each guards with `is None`
or runs only in dormant-code paths. The `Optional` typing in
`TurnContext` is the canonical guard. Test coverage in §Testing
addresses this.

### Not handled

Subsystem-output regressions ("the narrator no longer says 'the guard
with the broken tooth'") are not errors — they are feature regressions.
No alert. Surface via playtest only.

## Testing

### Wiring tests

- `test_turn_does_not_invoke_local_dm` — patch `LocalDM.decompose` to
  raise; run a full turn; assert turn completes successfully. Catches
  latent re-introduction.
- `test_miner_extracts_action_and_narration_from_post_change_save` —
  run N turns against a real session, then run the corpus miner on
  the resulting save and assert N `TrainingPair` rows with non-empty
  `input_text` (player actions) and `output_text` (narration).

### Unit tests

- `test_build_narrator_prompt_with_none_dispatch_package` — assert no
  `redact_dispatch_package` call, no dispatch bank execution, no
  exceptions.
- Update existing `TurnContext` tests that depend on `dispatch_package`
  being populated. Either rewrite to test the dormant path explicitly
  or keep them as live unit tests of the dormant module.

### Latency benchmark

Scripted scenario in `scenarios/` running ~10 turns end-to-end against
a running server with a recorded-narrator stub (deterministic Opus
latency). Capture `phase_durations_ms` from `TurnRecord`. Assert
`preprocess_llm` phase is absent or zero. Assert `total_ms` is at
least 5s lower than a pre-change baseline (baseline captured in the
implementation plan).

Optional in `just check-all` — needs the narrator stub.

### Out of scope for tests

- Quality of narration without subsystem injections — playtest concern.
- ADR-066 persistent session behavior — separate ADR.

## Risks & Open Questions

### Risk: dormant code rots

`subsystems/`, `prompt_redaction.py`, and `local_dm.py` go untested on
the live path. They may bit-rot until ADR-073 wakes them up. Mitigation:
keep their unit tests passing as part of `just check-all` even though
they have no live callers. If a unit test on dormant code breaks during
unrelated refactoring, the DORMANT marker tells the next agent why it
exists.

### Risk: Group G regression on MP wiring

When MP wiring next lands, visibility redaction will need a replacement.
This design does not provide one. The follow-up MP design must address
this explicitly. The original `2026-04-23-local-dm-group-g-asymmetric-info-wiring.md`
spec is partially superseded — its inline-LocalDM assumption no longer
holds. A new MP-visibility design will need to either (a) wake the
dormant LocalDM path solely for MP turns, or (b) build a heuristic
visibility classifier from game state alone, or (c) accept a different
visibility model.

### Open: ADR status

This change creates architectural drift from `2026-04-23-local-dm-decomposer-design.md`
("LocalDM is on the live critical path"). Either that spec gets a
"superseded by 2026-04-28" header, or this design lands as an ADR
(somewhere in the 090s) that cleanly supersedes the prior LocalDM
inline-call assumption. **Recommendation:** write a short ADR
(`docs/adr/091-localdm-offline-only.md` or next-available) once the
implementation lands, rather than during the design phase.

### Open: LocalDM offline runner

`sidequest/cli/localdm_replay.py` is named here as the offline tool but
not built in this story. A follow-up story will define it. The corpus
schema is intentionally rich enough to support it.

## Success Criteria

1. Solo turn `total_ms` median drops by 5+ seconds over a 10-turn
   benchmark (baseline captured during implementation).
2. `local_dm.decompose` OTEL span no longer appears in live turn traces.
3. The existing corpus miner, run against a post-change session save,
   emits one `TrainingPair` row per played turn with non-empty
   `input_text` (action) and `output_text` (narration).
4. All existing tests pass except those explicitly updated to reflect
   the dormant path.
5. Playtest of one full session (10+ turns) shows no narration-quality
   regression severe enough to block the change. (Subjective; documented
   in the playtest record.)

## Out of Scope (Follow-Ups)

- `sidequest/cli/localdm_replay.py` offline runner.
- ADR draft (091 or next available) formally superseding the inline-
  LocalDM doctrine.
- ADR-066 persistent narrator session wiring.
- MP visibility redaction redesign for the post-LocalDM world.
- Heuristic referent-resolver if playtest surfaces a need.
