# Phase 3 Story 3.4 Combat Dispatch — Session Handoff

**Paste this entire document into a fresh Claude Code session to resume execution.**

---

## Where you are

You are continuing execution of an implementation plan using **subagent-driven development** (`superpowers:subagent-driven-development`). The previous session completed tasks 1-9 of 17 and landed 16 commits on a feature branch. 8 tasks remain.

The plan document is:
- `/Users/slabgorb/Projects/oq-2/docs/superpowers/plans/2026-04-22-phase-3-story-3-4-combat-dispatch.md`

You are porting the combat-dispatch surface from the (now-deleted) Rust `sidequest-api` into Python `sidequest-server`. Phase 3 stories 3.1–3.3 already landed `StructuredEncounter`, `ResourcePool`, `TensionTracker`. Story 3.4 wires them in so a narrator-emitted `confrontation='combat'` actually creates a persisted encounter, the narrator prompt lists its beats + actors, the UI receives a CONFRONTATION message, and OTEL spans fire on every subsystem decision.

## Repo state

**Orchestrator repo:** `/Users/slabgorb/Projects/oq-2` — branch `main` (untouched).

**Work repo:** `/Users/slabgorb/Projects/oq-2/sidequest-server` — branch `feat/phase-3-story-3-4-combat-dispatch` (16 commits ahead of `develop`). All tests green except one pre-existing unrelated failure: `tests/server/test_rest.py::test_list_genres_empty_when_no_packs_dir`.

Check by running (from `/Users/slabgorb/Projects/oq-2`):
```bash
git -C sidequest-server branch --show-current
git -C sidequest-server log --oneline develop..HEAD
```

## Tasks complete (1-9)

| # | Task | Final commit | Notes |
|---|---|---|---|
| 1 | `find_confrontation_def` | 9559b9b | TDD green |
| 2 | `build_confrontation_payload` + `build_clear_confrontation_payload` | fe3302e | Fixed silent-fallback `or` → explicit `is not None` on mood_override |
| 3 | `ConfrontationMessage` + `ConfrontationPayload` protocol + union | 98bd79a | Widened `mood: str \| None = None` to accept clear-builder's `None` |
| 4 | `combat.*` / `encounter.*` OTEL catalog + 8 tests | 85b44f8 | Added `**attrs: Any` escape hatch + `outcome=None` branch test |
| 5 | `TurnContext.encounter_summary` + `confrontation_def` fields | a228663 | Pure field additions |
| 6 | `render_encounter_summary` | e129a62 | Pure function, 4 tests |
| 7 | Narrator `build_encounter_context` renders beats + actors; `TurnContext.encounter` field; orchestrator call-site wired | 30f7333 | Kwargs default None → backwards compatible with 3 pre-existing tests |
| 8 | `_build_turn_context` derives in_combat / in_chase / encounter fields from `snapshot.encounter` | 2486a47 | 205/208 server tests (1 pre-existing REST failure, 2 skipped) |
| 9 | `instantiate_encounter_from_trigger` + `resolve_encounter_from_trope` | 0b17697 | New module `dispatch/encounter_lifecycle.py` |

## Tasks remaining (10-17)

Follow the plan document exactly. Each task has its full content — file paths, failing tests with assertions, implementation code, pytest commands, commit command. The plan's task sections are authoritative.

- **Task 10** — Wire encounter instantiation + beat-selection apply into `_apply_narration_result_to_snapshot` (session_handler.py:1934+). Touches the hot path. Requires adding `pack` kwarg and the existing caller at line 1620. Use **sonnet**.
- **Task 11** — Dispatch CONFRONTATION message on encounter begin/active/end in `_execute_narration_turn` (session_handler.py:1679+). Includes adding `"CONFRONTATION": ConfrontationMessage` to `_KIND_TO_MESSAGE_CLS` and the before/after encounter state tracking. Use **sonnet**.
- **Task 12** — `strip_combat_brackets` helper + aside wiring. Mechanical. Use **haiku**.
- **Task 13** — XP award differential (25 in-combat, 10 out). Use **haiku**. ⚠ Verify the real `Character`/`CreatureCore` xp-field shape before writing the test; the plan's test stub may not match.
- **Task 14** — `apply_resource_patches` — affinity_progress → ResourcePool + mint threshold lore. Use **haiku**. ⚠ Verify `ResourceThreshold` kwargs in `sidequest/game/thresholds.py` — the real constructor may use `event_id` instead of `lore_key`.
- **Task 15** — Wire `resolve_encounter_from_trope` into the dispatch path. The helper already exists from Task 9. Use **haiku**.
- **Task 16** — End-to-end caverns_and_claudes combat walkthrough test (3-turn walkthrough: start → tick → resolve + XP diff regression). Uses `session_handler_factory` fixture that may not exist — add it to `tests/server/conftest.py`. Use **sonnet**.
- **Task 17** — Run `ruff check`, `mypy`, mark plan shipped, Keith playtest gate.

## Critical gotchas discovered during tasks 1-9

**Model-field realities that diverge from plan stubs:**
- `ConfrontationDef.confrontation_type` is aliased to `type` for YAML compat — construct with `type=...` kwarg.
- `BeatDef` requires a `stat_check: str` field (no default). Plan stubs sometimes omit it.
- `MetricDef.direction` is a plain lowercase `str`, NOT the `MetricDirection` enum. The enum exists at `sidequest.game.encounter.MetricDirection` with PascalCase variants (`Ascending`, `Descending`, `Bidirectional`) — used inside `StructuredEncounter.metric`, not on `MetricDef`.
- `ConfrontationPayload.mood` is `str | None = None` (widened to accept the clear-builder's `None`). Do NOT default to `""`.
- `GenrePack` has **no `.slug` attribute**. Use `sd.genre_slug` from `_SessionData` or `pack.meta.name`. Task 9's `instantiate_encounter_from_trigger` currently reads `snapshot.genre_slug` for the OTEL span attribute — Task 10 should add an explicit `genre_slug: str` kwarg to the helper signature and have the caller pass `sd.genre_slug`.
- `GameSnapshot` uses `extra="ignore"` — the `genre=` kwarg (not `genre_slug=`) is silently dropped. Use `GameSnapshot(genre_slug="...")` or construct without and set `snap.genre_slug` if you need it non-empty.

**Telemetry helper conventions:**
- All helpers in `sidequest/telemetry/spans.py` use `_tracer=` (leading underscore) as the tracer kwarg, not `tracer=`. The plan may show `tracer=` in some test snippets — match the actual helper signature.
- Every helper accepts `**attrs: Any` and merges into span attributes. New helpers must follow.

**Pre-existing backwards-compat contract:**
- Three tests at `tests/agents/test_narrator.py:165-200` call `build_encounter_context(registry)` with no kwargs. Task 7's rewrite defaults all three kwargs to None and registers the generic rules unconditionally — preserved. Any future change to this method must not break these.

**Pre-existing failure that is NOT your problem:**
- `tests/server/test_rest.py::test_list_genres_empty_when_no_packs_dir` — fails on develop and on this branch. Unrelated to encounter dispatch. Do not try to fix it.

## Execution method

Use `superpowers:subagent-driven-development` for each task:
1. Dispatch implementer subagent (haiku for mechanical, sonnet for integration).
2. Dispatch spec-compliance reviewer (haiku).
3. Dispatch code-quality reviewer (`superpowers:code-reviewer`, sonnet).
4. Loop on findings until approved.
5. Mark complete, move to next task.

Prompt templates are at `/Users/slabgorb/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.7/skills/subagent-driven-development/` (`implementer-prompt.md`, `spec-reviewer-prompt.md`, `code-quality-reviewer-prompt.md`).

The implementer prompt should contain the full task text from the plan (file paths, failing test code, implementation code, pytest command, commit command) plus a short "Context" section. Do not make the implementer read the plan file — paste the task text.

## Verification before resuming

Run from the orchestrator root:

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git status
# expect: on feat/phase-3-story-3-4-combat-dispatch, clean working tree
git log --oneline develop..HEAD
# expect: 16 commits from f187ffd through 0b17697
uv run --directory . pytest -x -q 2>&1 | tail -5
# expect: all green EXCEPT test_list_genres_empty_when_no_packs_dir (pre-existing)
```

## Start command

Begin with Task 10 (`_apply_narration_result_to_snapshot` encounter wiring). Follow the plan's Task 10 section verbatim, plus: add an explicit `genre_slug: str` kwarg to `instantiate_encounter_from_trigger` in `sidequest/server/dispatch/encounter_lifecycle.py` and update Task 9's 4 tests to pass it (use `"caverns_and_claudes"`). This closes the GenrePack.slug gap noted above before Task 10 makes the first production call.

Dispatch the Task 10 implementer with sonnet. Do not run tasks in parallel — they share `session_handler.py`.

---

## User context (Keith / the project)

- **This is a personal project under `slabgorb` GitHub.** No Jira. No `1898` org. Branches target `develop` on sidequest-server.
- **Playtest gate for Task 17:** Keith plays one combat scene end-to-end before the story closes. Not automatable.
- **OTEL principle:** every subsystem decision must emit a span so the GM panel (Sebastien-tier mechanical visibility) can see it. GM-panel queries read the `combat.*` / `encounter.*` span names — those are byte-identical-to-Rust external contracts; do not rename.
- **CLAUDE.md rules enforced throughout:** no silent fallbacks, no stubbing, no half-wired features. A helper with no production consumer is dead code; the integration test in Task 16 is the closing gate that proves end-to-end wiring.

---

## Emergency rollback

If a Task 10/11/16 dispatch breaks the hot path and you can't un-break it, reset to the last green commit:

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git reset --hard 0b17697  # last known good (Task 9 complete)
```

Do not force-push without explicit user approval.
