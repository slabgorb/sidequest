---
story_id: "45-32"
jira_key: null
epic: null
workflow: "trivial"
---

# Story 45-32: Post-review cleanup for 45-2 (test docstrings, lint, vacuous assertion, framing)

## Story Details
- **ID:** 45-32
- **Jira Key:** None (personal project)
- **Workflow:** trivial
- **Stack Parent:** none

## Context: Reviewer Findings from Story 45-2

Per `.session/archive/45-2-session.md` "Reviewer Assessment (round 2)" table, 8 non-blocking mechanical findings:

### MEDIUM findings (3 in test files)
1. **test_mp_turn_barrier_active_turn_count.py:430** — Stale "RED today" docstring on now-GREEN test. Replace with GREEN statement reflecting the fix at `session_handler.py:3311`.
2. **test_mp_turn_barrier_active_turn_count.py:508** — Stale line number in assertion message ("session_handler.py:3302"). Update to reference current `mp.round_dispatched` emit site (~line 3311).
3. **test_45_2_chargen_to_playing_wire.py:123** — Bare truthy `assert out, "connect must produce SESSION_CONNECTED"`. Replace with type-checking: `assert any(getattr(m, 'type', None) == 'SESSION_CONNECTED' for m in out)`.

### LOW findings (5 lint + docstring edits)
1. **test_45_2_chargen_to_playing_wire.py:39–40** — Unused imports `SessionEventMessage`, `SessionEventPayload` (F401). Auto-fixable via `uv run ruff check --fix`.
2. **test_lobby_state_machine.py:439** — Unused local `LobbyState` import (F401). Same `--fix` invocation.
3. **test_45_2_chargen_to_playing_wire.py + test_lobby_state_machine.py** — I001 import order violations. Same `--fix` invocation.
4. **sidequest/server/session_room.py:405** — `non_abandoned_player_count` docstring: replace "filters in the other direction (only PLAYING)" with "requires `state == PLAYING`; a CHARGEN seat is counted here but not there."
5. **test_lobby_state_machine.py:471, 474** — from_state/to_state OR-clause assertions accept both 'chargen' and 'CHARGEN'. Tighten to exact lowercase equality (StrEnum is authoritative).

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-04T19:25:11Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-04T19:13:36Z | 2026-05-04T19:15:22Z | 1m 46s |
| implement | 2026-05-04T19:15:22Z | 2026-05-04T19:21:07Z | 5m 45s |
| review | 2026-05-04T19:21:07Z | 2026-05-04T19:25:11Z | 4m 4s |
| finish | 2026-05-04T19:25:11Z | - | - |

## Delivery Findings

No upstream findings — story is a mechanical cleanup pass on 45-2 reviewer feedback. All changes are test-only, docstring-only, or self-contained lint fixes with zero behavior change.

### Dev (implementation)
- **Improvement** (non-blocking): Reviewer round 2 of 45-2 referenced `session_handler.py:3302/3311` for the `mp.round_dispatched` emit site, but the code lives in `sidequest/handlers/player_action.py:356` — the dispatch logic was extracted into per-handler modules at some point after that audit. Affects future review notes that reference `session_handler.py` line numbers — verify the seam is still in that file before quoting line numbers. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Reviewer round 2 of 45-2 also flagged F401 unused imports (`SessionEventMessage`, `SessionEventPayload` in `test_45_2_chargen_to_playing_wire.py`; `LobbyState` in `test_lobby_state_machine.py`) and I001 import-order violations. `uv run ruff check` on those files now reports `All checks passed!` — those issues were already cleaned up by an earlier commit. No action taken; flagging so the Reviewer doesn't re-look. *Found by Dev during implementation.*
- **Question** (non-blocking): The reviewer's suggested assertion `assert any(getattr(m, 'type', None) == 'SESSION_CONNECTED' for m in out)` would have always failed — there is no `SESSION_CONNECTED` message type in the protocol enum. Connect emits `SESSION_EVENT` with `payload.event == "connected"`. Worth a short note in `docs/api-contract.md` that the slug-connect response is a `SESSION_EVENT`-with-event-discriminator, not a top-level `SESSION_CONNECTED` type, so future reviews don't make the same suggestion. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): Repo-wide `ruff format --check` flags 71 files needing reformatting, none of which are in this branch's diff. Pre-existing formatting debt across the server repo. Affects `sidequest-server/` (consider a one-shot `uv run ruff format .` cleanup story or pre-commit hook). Not blocking 45-32. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The pattern of embedding file path + line number into test failure messages (e.g. `player_action.py:356`) is informative when fresh but rots fast — the very story we're cleaning up is evidence (`session_handler.py:3302` was the prior rotted ref). A future quality-of-life pass could replace these with `inspect.getsourcefile()` + `inspect.getsourcelines()` on the symbol being asserted, so refs auto-update. Affects test files in `tests/server/`. Out of scope for 45-32. *Found by Reviewer during code review.*

## Design Deviations

### Reviewer (audit)
- **Vacuous-assertion fix checks SESSION_EVENT, not SESSION_CONNECTED** → ✓ ACCEPTED by Reviewer: verified `SessionEventMessage` (sidequest/protocol/messages.py:688) has `type: Literal[MessageType.SESSION_EVENT]` and `SessionEventPayload.event: str` with documented values including `"connected"` (messages.py:235-236). `MessageType` is a StrEnum with `SESSION_EVENT = "SESSION_EVENT"` (enums.py:20-31), so `getattr(m, "type", None) == "SESSION_EVENT"` compares correctly. Connect handler at `sidequest/handlers/connect.py:738-748` emits this exact shape. Reviewer's original suggestion of `type == "SESSION_CONNECTED"` would have always failed — Dev's deviation is necessary, not optional.
- **Stale file/line refs updated to `player_action.py:356`, not `session_handler.py:3311`** → ✓ ACCEPTED by Reviewer: verified `mp.round_dispatched` is emitted only at `sidequest/handlers/player_action.py:347-364` (grep across `sidequest/`); line 356 is the load-bearing `"player_count": playing_count,` assignment. The dispatch logic was refactored out of `session_handler.py` into per-handler modules at some point after the 45-2 reviewer audit, making the original `session_handler.py:3311` suggestion stale. Dev's correction is the only honest update.
- **F401 + I001 already clean (no-op)** → ✓ ACCEPTED by Reviewer: confirmed via `uv run ruff check` on the named files — already passes. Likely auto-fixed during 45-2 final commit polish or a subsequent pass. No risk in skipping a no-op.

### Dev (implementation)
- **Vacuous-assertion fix checks SESSION_EVENT, not SESSION_CONNECTED**
  - Spec source: `.session/archive/45-2-session.md` Reviewer round 2 / this session's `## Context: Reviewer Findings` MEDIUM #3
  - Spec text: ``replace bare truthy `assert out, "..."` with `assert any(getattr(m, 'type', None) == 'SESSION_CONNECTED' for m in out)` to actually verify the message type``
  - Implementation: Asserted `type == "SESSION_EVENT"` AND `payload.event == "connected"` instead. Reason: there is no `SESSION_CONNECTED` type in the protocol enum — `sidequest/handlers/connect.py:738` emits a `SessionEventMessage(type="SESSION_EVENT", payload=SessionEventPayload(event="connected", ...))`. The reviewer's suggested assertion would have always failed.
  - Rationale: Goal was non-vacuous type-check (reviewer's intent); the new assertion satisfies that goal against the actual handler contract.
  - Severity: trivial
  - Forward impact: none — test still gates the same chargen-to-PLAYING wire and now correctly identifies the connect response.

- **Stale file/line refs in `test_mp_turn_barrier_active_turn_count.py` updated to `player_action.py:356`, not `session_handler.py:3311`**
  - Spec source: this session's `## Context: Reviewer Findings` MEDIUM #1, #2
  - Spec text: ``update assertion message to reference current line ~3311 instead of the stale 3302`` (also docstring at line 430)
  - Implementation: Pointed both the docstring and assertion at `sidequest/handlers/player_action.py:356`. Reason: the `mp.round_dispatched` emit site moved out of `session_handler.py` entirely into the per-handler module; line 3311 is no longer the correct location.
  - Rationale: The reviewer's intent (current location, not stale) is preserved; the file path was simply wrong in the suggestion because the dispatch logic was extracted at some point after the reviewer's audit.
  - Severity: trivial
  - Forward impact: none — references now pin the actual emit site.

## SM Assessment

Trivial workflow, 1 point, server-only. All 8 findings are mechanical and pre-specified by Reviewer round 2 of 45-2. Estimated <30 min wall-clock for Dev. No design questions, no architectural choices — Dev applies the table exactly as written, runs `just server-check`, then routes to Reviewer.

**Confidence:** high. Production code from 45-2 already approved; this story only touches test docstrings, lint auto-fixes, one assertion tightening, and one docstring rewrite in `session_room.py:405`.

## Banned Patterns (Dev's prompt)

- **Never `git stash`** — Use `git reset --hard` or `git restore` instead if needed to discard changes. Stash hides work and makes git history hard to trace.
- **Never run tests on prior commits to "prove pre-existing failure"** — If a test is failing, diagnose and fix it on the current commit. Don't git-checkout a prior commit to show the test was already broken; that's a waste of time and can hide regressions you just introduced.

---

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/session_room.py` — rewrite misleading half of `non_abandoned_player_count` docstring (spell out PLAYING-only counts CHARGEN seats here-but-not-there, instead of "filters in the other direction").
- `tests/server/test_mp_turn_barrier_active_turn_count.py` — replace stale "RED today" docstring on `test_mp_round_dispatched_player_count_matches_barrier_predicate` with a GREEN statement; update assertion message; both now point at `sidequest/handlers/player_action.py:356` (the actual current emit site).
- `tests/server/test_45_2_chargen_to_playing_wire.py` — replace bare truthy `assert out, "..."` with a typed check on `SESSION_EVENT` + `payload.event == "connected"`.
- `tests/server/test_lobby_state_machine.py` — tighten `from_state`/`to_state` OR-clauses to exact lowercase equality (StrEnum is authoritative).

**Tests:** 21/21 passing on the touched files (`test_45_2_chargen_to_playing_wire`, `test_lobby_state_machine`, `test_mp_turn_barrier_active_turn_count`). Ruff check + format clean. No behavior changes.

**Branch:** `feat/45-32-post-review-cleanup-45-2` (pushed, sidequest-server)

**Spec deviations from session prescription:**
1. The vacuous-assert fix uses `SESSION_EVENT` + `payload.event == "connected"` instead of `type == "SESSION_CONNECTED"` (no such type exists; the reviewer's suggestion would have always failed).
2. The line-number updates in `test_mp_turn_barrier_active_turn_count.py` point at `player_action.py:356`, not `session_handler.py:3311` — the dispatch emit moved files.
3. F401 + I001 lint findings were already clean per `uv run ruff check`; no action taken (no-op fix).

Both behavioral deviations preserve the reviewer's intent (current location, non-vacuous type-check) while matching the actual code.

**Handoff:** To Reviewer (Colonel Potter) for trivial-workflow review.

---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 21/21 GREEN, ruff lint PASS, ruff format flagged 71 repo-wide files (none in this diff) → pre-existing debt, not blocking |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (`workflow.reviewer_subagents.edge_hunter=false`); diff is documentation-and-test-message only, no edge surfaces |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings; diff has no production-code error paths |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings; manual review covered the test-quality dimension (vacuous-assert replacement, OR-clause tightening) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings; manual review confirms docstring rewrites are accurate (verified against StrEnum + actual emit sites) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings; no type contracts changed |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings; no security surface in diff |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings; manual review — defensive double-getattr in new assertion is justified for typed-but-Pydantic-shaped error reporting |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings; manual rule-by-rule walk against `gates/lang-review/python.md` below |

**All received:** Yes (1 enabled, 8 disabled per project settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

---

## Reviewer Assessment

**Verdict:** APPROVED

### Diff Summary
4 files, +27/-15 lines. All edits are documentation-and-assertion-message tightening with one production-code docstring rewrite. Zero behavior change.

### Rule Compliance — `gates/lang-review/python.md`

| # | Rule | Status | Evidence |
|---|------|--------|----------|
| 1 | Silent exception swallowing | N/A | No `try/except` blocks in diff |
| 2 | Mutable default arguments | N/A | No function signatures introduced |
| 3 | Type annotation gaps at boundaries | N/A | No new public functions |
| 4 | Logging coverage AND correctness | N/A | No logger calls in diff |
| 5 | Path handling | N/A | No path operations in diff |
| 6 | **Test quality** | ✓ PASS | The story is *about* fixing test quality. Vacuous `assert out` replaced with type+payload check (test_45_2_chargen_to_playing_wire.py:121-135). OR-clauses `in ("chargen", "CHARGEN")` tightened to exact `== "chargen"` (test_lobby_state_machine.py:467-472). Both are direct compliance wins for rule #6 ("`assert result` without checking specific value — truthy check misses wrong values"). |
| 7 | Resource leaks | N/A | No new resource acquisition |
| 8 | Unsafe deserialization | N/A | No deserialization in diff |
| 9 | Async/await pitfalls | N/A | Tests already-async, no new async patterns |
| 10 | Import hygiene | N/A | No imports added/removed |
| 11 | Input validation at boundaries | N/A | No new input surfaces |
| 12 | Dependency hygiene | N/A | No dependency changes |
| 13 | Fix-introduced regressions | ✓ PASS | The new typed assertion was tested GREEN. The OR-clause tightening was tested GREEN. The docstring rewrites are factually verified against the actual code (LobbyState StrEnum lowercase values; `mp.round_dispatched` emit at player_action.py:356). |

### Observations

1. **[VERIFIED] [TEST] Vacuous-assertion fix is correct against actual handler contract** — `tests/server/test_45_2_chargen_to_playing_wire.py:121-135`. Old `assert out, "connect must produce SESSION_CONNECTED"` would pass on any non-empty response (including error envelopes). New typed check verifies `type == "SESSION_EVENT"` AND `payload.event == "connected"` — the exact contract emitted by `sidequest/handlers/connect.py:738-748` (`SessionEventMessage` with `SessionEventPayload(event="connected", ...)`). MessageType is StrEnum so the string comparison works (`sidequest/protocol/enums.py:20-31`). Defensive double-getattr is appropriate for tests-as-documentation: it survives schema drift and produces a tuple of `(type, event)` in the failure message — better debugging signal than a raw type-error.

2. **[VERIFIED] [DOC] Production docstring rewrite is accurate** — `sidequest/server/session_room.py:510-514`. Old wording "filters in the other direction (only PLAYING)" was technically correct but ambiguous; new wording "requires `state == PLAYING`; a CHARGEN seat is counted here but not there" is unambiguous. Verified against the actual function bodies: `playing_player_count()` at line 501-503 returns `len(playing_player_ids())` which filters `seat.state == LobbyState.PLAYING` (line 499); `non_abandoned_player_count()` at line 517 counts `seat.state != LobbyState.ABANDONED`. So a CHARGEN seat IS counted here (state != ABANDONED) and IS NOT counted there (state != PLAYING). Docstring claim verified.

3. **[VERIFIED] [TEST] OR-clause tightening is correct** — `tests/server/test_lobby_state_machine.py:467, 470`. `LobbyState` is a StrEnum (`sidequest/server/session_room.py:84` with `from enum import StrEnum`), so `.value` always yields the lowercase string literal (`"chargen"`, `"playing"`). The OR-clauses `in ("chargen", "CHARGEN")` were defensively masking any future regression to uppercase emission. Strict `== "chargen"` will fail loudly on regression. This is a direct quality improvement.

4. **[VERIFIED] [DOC] Stale file/line refs updated to current code** — `tests/server/test_mp_turn_barrier_active_turn_count.py:425-508`. Original docstring/assertion referenced `session_handler.py:3302` (or 3311). Confirmed via `grep -rn 'mp\.round_dispatched' sidequest/`: the only emit site is `sidequest/handlers/player_action.py:347-364`, with line 356 being the load-bearing `"player_count": playing_count,` assignment. The dispatch logic was extracted out of `session_handler.py` into per-handler modules; the old reference was stale. Dev's update is accurate.

5. **[OBSERVATION] [SIMPLE] Line refs in docstrings remain a maintenance hazard** — Even after this fix, the assertion message and docstring reference `player_action.py:356`. Line numbers drift. Acceptable trade-off here — the file path is the searchable anchor, and the line number gives a hint. Logging this as a pattern note rather than a finding; SOUL.md's "Diamonds and Coal" principle says detail signals importance, and this OTEL-load-bearing test deserves the specificity.

6. **[VERIFIED] [EDGE] No new edge surfaces** — Diff modifies four files with documentation/assertion changes only. No conditionals added, no new branches, no new state transitions, no new error paths. Edge enumeration is N/A.

7. **[VERIFIED] [SILENT] No silent failure paths introduced** — New assertion uses `any(...)` with explicit failure message including the actual `(type, event)` pairs. Old `assert out` was the silent-failure offender; new code is strictly louder.

8. **[VERIFIED] [TYPE] Type contracts unchanged** — No new types, no signature changes, no Pydantic model modifications. The new test assertion uses `getattr` defensively rather than relying on static type narrowing — appropriate for a test that may receive heterogeneous message types from `handle_message()`.

9. **[VERIFIED] [SEC] Zero security surface** — No auth checks, no input validation paths, no secrets, no PII. Test files and one production docstring.

10. **[OBSERVATION] [SIMPLE] Minor verbosity** — The new assertion uses `getattr(getattr(m, "payload", None), "event", None)` twice (once in the `any(...)` and once in the failure message). Could be hoisted into a list comprehension `payload_events = [(getattr(m, "type", None), getattr(getattr(m, "payload", None), "event", None)) for m in out]` then `assert any(t == "SESSION_EVENT" and e == "connected" for t, e in payload_events)`. Not a finding — current form is readable enough; flagging as a future-cleanup observation only.

11. **[VERIFIED] [RULE] Project rules `python.md` checks #6 and #13 directly improved** — see Rule Compliance table above. No rule violation in any other check applies to this diff.

### Devil's Advocate

What could go wrong here? Argue the code is broken.

The new typed assertion uses `getattr(m, "type", None) == "SESSION_EVENT"`. If `MessageType.SESSION_EVENT` were ever changed from a StrEnum to a plain Enum (or to a different string value), this comparison would silently fail. **Counter:** that would be a wire-protocol break and would surface in a thousand other tests; pinning a literal string here is the right test-as-documentation choice. The whole point of the protocol enum being a StrEnum is interop with raw string comparisons.

The `getattr(getattr(m, "payload", None), "event", None)` chain returns `None` for any object without those attributes. If `handle_message` returned a list of `dict`s instead of Pydantic models, the test would fail because `getattr` doesn't dig into dicts — would the failure message be informative? Yes — the tuple would be `(None, None)` and the assertion message includes those pairs. The test would correctly fail loudly rather than silently pass.

The OR-clause removal hardens against StrEnum value drift, but what if a future Story changes `LobbyState.PLAYING.value` to `"PLAYING"` for some reason (e.g., schema interop with an external system)? Then the test fails. **That is the correct behavior** — the failing test would force a deliberate decision rather than silently masking the change. This is exactly what Reviewer round 2 of 45-2 wanted.

The line-number-in-error-message pattern (`player_action.py:356`) will rot. In six months, the line might be 401 or 312. **But the prior version was already rotted by 100+ lines and a different file** — this is no worse, and the file path is searchable. Long-term, line refs in test failure messages should be replaced by `inspect.getsourcefile()` of the symbol, but that's out of scope for a 1-pt cleanup.

Could the production-code docstring rewrite mislead a future reader? Re-read: "requires `state == PLAYING`; a CHARGEN seat is counted here but not there." Verified against actual function bodies. The wording is more precise than the original. Good.

Could the F401/I001 "already clean" finding hide a real issue? Verified by re-running `uv run ruff check` on the named files — passes. The reviewer's note in 45-2 was likely cleared during 45-2's own final cleanup or in a downstream fix; this story rightly does nothing rather than fabricate work. Doing nothing is the correct response when the only correct action is no-op.

No issues found by adversarial scrutiny. APPROVED.

### Verdict Justification
- Preflight GREEN (21/21 tests pass, ruff lint clean).
- All four edits verified against actual code: types, line numbers, StrEnum behavior, function bodies.
- All three Dev deviations from session prescription are necessary corrections to the original reviewer suggestion (no `SESSION_CONNECTED` type exists; emit site moved to `player_action.py`; F401/I001 already clean).
- Zero new code paths, zero new error handling surfaces, zero security surface.
- Project rules #6 (test quality) and #13 (fix-introduced regressions) directly improved.

**Handoff:** To SM (Hawkeye Pierce) for finish-story.

---

*Session updated by Dev on 2026-05-04. All changes are mechanical and non-behavior-altering. Reviewed and approved by Reviewer on 2026-05-04.*