---
story_id: "45-22"
jira_key: "SQ-45-22"
epic: "Epic 45 (Playtest 3 Closeout)"
workflow: "trivial"
---

# Story 45-22: Player turns logged with author=player (split from 37-41 sub-8)

## Story Details
- **ID:** 45-22
- **Jira Key:** SQ-45-22
- **Epic:** SQ-45 (Playtest 3 Closeout)
- **Points:** 1
- **Priority:** p2
- **Type:** bug
- **Workflow:** trivial
- **Repos:** server
- **Stack Parent:** none
- **Branch:** feat/45-22-player-turn-author-tag (sidequest-server)

## Description

Playtest 3 Felix: 71 narrative_log entries all carry `author='narrator'`, zero player-turn entries. Subsystem engagement is not verifiable from log authorship — Sebastien's GM panel cannot tell *which* entries originated from a player action versus narrator inference.

Append player turns to `narrative_log` with `author=player` (or the character name) so the log distinguishes the two sources.

**Source:** 37-41 sub-8 (Playtest 3 closeout split).

## Acceptance Criteria

1. Player-driven turns append a NarrativeEntry with `author="player"` or the acting character's name (decision documented in Dev Assessment).
2. Narrator turns continue to append with `author="narrator"` (no regression).
3. The narrative_log produced by a session containing both player and narrator turns shows BOTH author values across entries — verified by a wire test, not just unit assertion.
4. No silent fallbacks: if the player-author append site cannot determine the author, fail loudly (raise or warn-with-OTEL) — do not silently default to "narrator".

## Sm Assessment

**Story routed for trivial implement phase. Setup complete and gates clear.**

- **Scope:** 1pt p2 bug, single repo (server). One missing call site: somewhere in the player-action dispatch path, the code appends to `narrative_log` only via the narrator emitter. Player-turn append site needs to write its own entry with `author="player"` (or character name).
- **Workflow:** Trivial — concrete bug evidence (71 entries, zero player-author) and a single-seam fix. No design choice to litigate beyond the author-value decision (literal `"player"` vs character name).
- **Risk surface:** Low. Append-only — no migration, no schema change. Watcher events are unaffected; this is purely cosmetic from a state-mutation standpoint, but load-bearing for OTEL lie-detection (Sebastien needs the audit lane to attribute turns).
- **Author-value decision (open):** Spec leaves "player" vs character name as an OR. Dev should pick one and record in Dev Assessment. Recommendation: literal `"player"` for the role tag, with the character name carried in `speaker` if `NarrativeEntry.speaker` is present (it is — checked session.py:70). That keeps `author` low-cardinality (player/narrator) so dashboards can group, while preserving identity granularity in `speaker`.
- **Wiring test required (per CLAUDE.md):** Must exercise the production player-action dispatch path end-to-end and assert the resulting `narrative_log` has at least one `author="player"` entry alongside narrator entries.
- **OTEL discipline (per CLAUDE.md):** AC4's "fail loudly" requires a span/log when the author cannot be determined. Don't accept silent default-to-narrator behavior.
- **Branch:** `feat/45-22-player-turn-author-tag` ready in sidequest-server.

No blockers. Hand off to Ponder Stibbons (Dev) for implement phase.

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-29T16:14:45Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-29 | 2026-04-29T16:03:23Z | 16h 3m |
| implement | 2026-04-29T16:03:23Z | 2026-04-29T16:10:32Z | 7m 9s |
| review | 2026-04-29T16:10:32Z | 2026-04-29T16:14:45Z | 4m 13s |
| finish | 2026-04-29T16:14:45Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/game/session.py` — `NarrativeEntry.author` now required (no default) with a `field_validator` rejecting blank values. Two-layer schema-level guard: missing field → Pydantic `ValidationError`; blank field → custom `ValueError`. AC4 satisfied at the schema, not just at one call site.
- `sidequest/server/websocket_session_handler.py` — wired the player-turn append in `_execute_narration_turn` immediately before the existing narrator append. New `NarrativeEntry(author="player", content=action, speaker=acting_name, round=interaction)` lands per real player turn. Skipped on `is_opening_turn=True` because the opening-turn `action` is a programmatic seed, not player input.
- `tests/server/test_player_turn_author.py` (new, 12 tests) — schema validator unit tests (4 reject cases + 4 accept cases + 1 missing-field), wire tests on `_execute_narration_turn` (3 — both-authors-logged, speaker carries character name, both entries share round number), opening-turn skip test (1).

**Tests:** 12/12 new tests pass. Full server suite: **2917 passed / 0 failed / 49 skipped** — no regressions despite the breaking schema change (removing `author` default).

**Branch:** `feat/45-22-player-turn-author-tag` (about to push)

**Author-value decision:** `author="player"` (literal, low-cardinality role tag), `speaker=acting_character_name` (high-cardinality identity, resolved via existing `_resolve_acting_character_name` helper). Per SM Assessment recommendation — keeps GM-panel grouping ergonomic while preserving per-PC attribution for multiplayer dashboards.

**ACs Met:**
- **AC1** — Player turns append `author="player"` carrying the raw `action` text. ✅ Wire test `test_player_turn_logs_both_authors`.
- **AC2** — Narrator turns continue with `author="narrator"`. ✅ Same wire test asserts both authors present; full-suite green proves no regression.
- **AC3** — A turn produces both author values. ✅ Same wire test.
- **AC4** — No silent fallbacks. ✅ Schema-level enforcement: blank/missing `author` raises at construction. Future copy-paste of the narrator block that forgets to set author will fail loudly during the very first turn.

**Handoff:** To Granny Weatherwax (Reviewer) for the trivial-workflow review phase.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Schema change beyond strict AC4 scope.** AC4 says "if the player-author append site cannot determine the author, fail loudly." I implemented this not just at the player append site but at the `NarrativeEntry` schema level — making `author` a required field and adding a `field_validator` that rejects blank values. **Why:** A site-local guard would protect today's call sites only; a future contributor copying the narrator-append block could re-introduce the silent-default failure mode. Schema-level enforcement is the only durable backstop. **Severity:** minor — strictly more conservative than the spec; no AC contradicts it. **Forward impact:** Future stories that construct `NarrativeEntry` must always pass an explicit non-blank `author`. Audited existing call sites (`websocket_session_handler.py`, `world_materialization.py`, `persistence.py` load path, all test fixtures) — every one already supplies a non-blank author, so no migration cascade.

### Reviewer (audit)
- **Dev entry above** → ✓ ACCEPTED by Reviewer: schema-level enforcement is exactly the right shape for AC4. Spec text is "fail loudly … do not silently default to 'narrator'" — schema enforcement protects every current and future construction site, not just the one this story touches. CLAUDE.md "No Silent Fallbacks" explicitly endorses this stance ("If something isn't where it should be, fail loudly"). Independently verified the audited call sites: `world_materialization.py:288` (`author=entry.speaker`, where ChapterNarrativeEntry.speaker is `str`-required), `persistence.py:425` (`author=row[1]` from SQL — non-null in all observed saves), and 6 test fixtures all hardcoding `author="narrator"`. No regression cascade.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (full suite 2917 pass / 0 fail / 49 skip; ruff clean; 0 code smells; 3 advisory notes for Reviewer follow-up) | confirmed 0, dismissed 0, deferred 0 — advisory notes folded into Reviewer's own analysis below |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.test_analyzer=false` |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.comment_analyzer=false` |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.rule_checker=false` |

**All received:** Yes (1 specialist returned, 8 disabled by project settings — Reviewer absorbed those domains directly)

**Total findings:** 1 confirmed (own diff read), 0 dismissed, 0 deferred

## Rule Compliance

Walked the **`.pennyfarthing/gates/lang-review/python.md`** 13-rule checklist plus CLAUDE.md / SOUL.md provisions. Diff is small (3 files, +310/-1).

| # | Rule | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Silent exception swallowing | ✓ Compliant | The new player-append code has no try/except. The surrounding `except Exception as exc: logger.error("session.persist_failed error=%s", exc)` (websocket_session_handler.py:1581) is pre-existing and unchanged — out of this diff's scope. **However** see [SIMPLE] finding 1 below: the new player append now sits inside the same swallowing try-block, so a future failure in the player append could mask the narrator append. Existing pattern, but the failure surface widened. |
| 2 | Mutable default arguments | ✓ Compliant | No mutable defaults in changed code. |
| 3 | Type annotation gaps at boundaries | ✓ Compliant | `author_non_blank(cls, v: str) -> str` fully annotated. |
| 4 | Logging coverage AND correctness | ✓ Compliant | Pre-existing `logger.error("session.persist_failed ...")` covers the persistence-failure path. The new player-append code has no separate error path that needs logging — it relies on the same try/except envelope. AC4's "fail loudly" requirement is met by Pydantic raising `ValidationError`, which the parent try/except catches and `logger.error`s. |
| 5 | Path handling | N/A | No filesystem ops in diff. |
| 6 | Test quality | ✓ Compliant | All 12 tests use specific assertions. `test_missing_author_now_fails_loudly` correctly imports `pydantic.ValidationError` and pins the missing-required-field path (verified myself in the diff text). `test_opening_turn_logs_only_narrator` passes `action="(opening seed)"` — non-empty, so the guard is exercised, not vacuous. Wire tests inspect `sd.store.append_narrative.call_args_list` to walk the actual production path. No vacuous assertions, no `mock.patch` on wrong target, no skipped tests. |
| 7 | Resource leaks | N/A | No new resource acquisition. |
| 8 | Unsafe deserialization | N/A | No deserialization. |
| 9 | Async/await pitfalls | ✓ Compliant | Wire tests are correctly `@pytest.mark.asyncio`; no blocking calls in async. |
| 10 | Import hygiene | ✓ Compliant | `field_validator` already imported at session.py:16 (existing import — used by `NpcPatch.name_non_blank`). `_resolve_acting_character_name` already imported at websocket_session_handler.py:118. Tests import `pydantic.ValidationError` lazily inside the test that needs it, avoiding pollution. No star imports, no circular imports introduced. |
| 11 | Input validation at boundaries | ✓ Compliant — this story IS additional input validation at a boundary (player-action ingress), and the schema validator enforces it everywhere. |
| 12 | Dependency hygiene | ✓ Compliant | No new dependencies. |
| 13 | Fix-introduced regressions | ✓ Compliant | Removing the `author: str = ""` default could regress legacy save loads where the SQL `author` column is empty — but per the user-known "Legacy saves are throwaway" rule, fail-loud on legacy data is desired. Full-suite 2917 pass shows no current test regression. |

**CLAUDE.md cross-checks:**
- *No Silent Fallbacks* — ✓ The single most relevant rule for this story. Schema-level rejection of blank `author` is the canonical "fail loudly" implementation.
- *No Stubbing* — ✓ Fully wired.
- *Don't Reinvent — Wire Up What Exists* — ✓ Reuses the existing `_resolve_acting_character_name` helper rather than rolling a new lookup. Reuses Pydantic's `field_validator` pattern already established by `NpcPatch.name_non_blank` (session.py:205-210).
- *Verify Wiring, Not Just Existence* — ✓ Wire tests target the production seam `_execute_narration_turn` via the conftest `session_fixture`. Schema validator is reachable from every NarrativeEntry construction site (verified by audit).
- *Every Test Suite Needs a Wiring Test* — ✓ Three of the 12 tests are wire tests that exercise the actual seam.

**SOUL.md cross-checks:** No design-pillar surface in this story — pure mechanical transparency. The change directly serves Sebastien's lie-detector audience (per CLAUDE.md primary-audience definition).

## Devil's Advocate

I'll argue this code is broken three ways and see what survives.

**1. The new player append now lives inside the persistence try/except envelope.** Looking at the structure (websocket_session_handler.py:1534-1580):

```
with timings.phase("persistence"):
    try:
        # save snapshot
        # NEW: player append (might raise on legacy/edge data)
        # OLD: narrator append
    except Exception as exc:
        logger.error("session.persist_failed error=%s", exc)
```

If the player-append path raises (e.g., `_resolve_acting_character_name` returns something unexpected, or `NarrativeEntry(author="player", ...)` fails), the narrator append is skipped too. **Pre-fix, the narrator append was first inside the try; only its own failure could cancel it.** Now a player-append failure cancels both.

Mitigations: `_resolve_acting_character_name` is documented (session_helpers.py:125-149) to never raise — it falls back to `sd.player_name` as the last resort. `NarrativeEntry(author="player", ...)` cannot raise: `"player"` is non-blank, `content=action` is non-empty (sanitized upstream at player_action.py:57-58), and `round` is a snapshot integer. Failure surface is essentially zero in practice. **Severity: [LOW]** — flagged as a finding because the pattern *widens* the swallow-region, even though the practical failure odds are negligible.

**2. The `is_opening_turn=True` skip is the only no-player-append path. What about other non-player narrators?** Audited every caller of `_execute_narration_turn`:
- `player_action.py:273, 281` — real player turns. Default `is_opening_turn=False`. ✓
- `websocket_session_handler.py:2260` — opening turn. Explicit `is_opening_turn=True`. ✓
- `dice_throw.py:122` — dice resolution. **No `is_opening_turn` argument**, defaults to False. Action is the synthesized `outcome.replay_action_text`. The player did initiate the throw via DICE_THROW message, so logging the replay text as `author="player"` is semantically correct — it's still the player's contribution to the round, just expressed in a server-synthesized form. ✓ Reasonable.

No silent miscategorization. ✓

**3. What about ChapterNarrativeEntry → NarrativeEntry materialization at world_materialization.py:288?** That path does `author=entry.speaker`. ChapterNarrativeEntry.speaker is `str` (required, no validator). If a chapter pack defines a narrative log entry with `speaker: ""` (empty string), the schema validator now raises ValueError → world materialization fails loudly. **Pre-fix** that same case silently produced a NarrativeEntry with `author=""`. Behavior change: silent corruption → loud failure. Per "fail loudly" → desired. Empirically: `grep` across every genre pack found zero blank speakers in chapter YAML. Real-world risk is zero. ✓ Not a finding.

**4. The schema validator runs on every NarrativeEntry load.** A save with 5000 narrative entries triggers 5000 strip-checks on load. Each is O(len(string)). Negligible — even at 100 chars × 5000 entries that's <1ms. ✓ Not a finding.

**5. Dashboard cardinality concern.** `author="player"` is low-cardinality (good for grouping), `speaker=character_name` is high-cardinality (good for identity granularity). But what if a future story decides to use `author=character_name` instead? The schema permits it. The Dev Assessment locks in the "low-cardinality role tag" decision in prose, not in code. A future contributor could split this conventionally without the schema noticing. Cosmetic risk only — Reviewer can re-flag if it happens. ✓ Not a finding.

**6. Race window: snapshot lock.** `apply_world_patch` runs inside `with self._lock:`, but the new player-append code path runs in `_execute_narration_turn` which is NOT inside `apply_world_patch`. Is there a race? Looking at the surrounding code: the SQL writes go through `sd.store` which is one SQLite connection. SQLite has its own per-connection serialization. The orchestrator-protected execution context guarantees one turn at a time per session. ✓ No new race surface.

The widened-swallow-region (#1) is the only finding worth filing. Adding it.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Player WebSocket → PLAYER_ACTION dispatch (`player_action.py`) → sanitization (`sanitize_player_text`) → `_execute_narration_turn(sd, action, ...)` (`websocket_session_handler.py:1377`) → orchestrator narrates → state apply → persistence block (`:1534-1580`) — `if not is_opening_turn:` resolves acting character via `_resolve_acting_character_name`, builds `NarrativeEntry(author="player", content=action, speaker=acting_name, round=interaction)`, appends to `sd.store.append_narrative`; then the existing narrator entry appends with `author="narrator"`. Both entries share the same `round` so the 45-11 round_invariant span (`round == MAX(narrative_log.round_number)`) holds.

**Pattern observed:** `[VERIFIED]` Schema-level validation reuses the existing `field_validator` shape from `NpcPatch.name_non_blank` (session.py:205-210) — same import, same idiom, same error-message style. Reuses `_resolve_acting_character_name` (session_helpers.py:125, already used at session_helpers.py:170 and websocket_session_handler.py:1896) rather than rolling a new lookup. Satisfies "Don't Reinvent" CLAUDE.md rule.

**Error handling:** `[VERIFIED]` AC4's "fail loudly" is enforced at three layers: (a) `author: str` required (Pydantic raises `ValidationError` on missing field), (b) `field_validator` rejecting blank/whitespace strings (raises `ValueError`), (c) the surrounding `try/except` in `_execute_narration_turn` logs the failure as `session.persist_failed` at ERROR severity — failures are loud at both the schema and the log surface.

**OTEL observability:** `[VERIFIED]` Although this story doesn't add new OTEL spans, the fix preserves the 45-11 round_invariant span semantics (`round_number` lockstep) and the existing turn-end span emission. The new entries make the existing dashboard *more* informative — Sebastien can now distinguish player input vs narrator inference without instrumentation changes. Watcher events unaffected.

**Wiring:** `[VERIFIED]` Three wire tests target `_execute_narration_turn` via `session_fixture`: `test_player_turn_logs_both_authors`, `test_player_entry_speaker_is_acting_character`, `test_player_entry_round_matches_interaction`. Plus `test_opening_turn_logs_only_narrator` exercises the `is_opening_turn=True` skip path. CLAUDE.md "Verify Wiring, Not Just Existence" satisfied.

**Test quality:** `[VERIFIED]` 12/12 passing. Specific-value assertions throughout. Validator unit tests cover the rejection cases (empty, whitespace, tab, missing-field) and accept cases (4 parametrized legitimate authors). Wire tests inspect `sd.store.append_narrative.call_args_list` — the correct observation surface given the conftest mocks the store. Round-number lockstep test pins the 45-11 invariant. Opening-turn test passes a non-vacuous action string so the guard is genuinely exercised.

**Schema-change audit:** `[VERIFIED]` Independently audited every NarrativeEntry construction site:
- `websocket_session_handler.py:1556, 1565` — both supply `author=`
- `world_materialization.py:288` — supplies `author=entry.speaker` where `ChapterNarrativeEntry.speaker: str` is required (no default in source schema, zero blank values in pack YAML)
- `persistence.py:425` — load path, supplies `author=row[1]` from SQL (non-null in all observed saves)
- 6 test fixtures across `tests/game/` and `tests/server/` — every one hardcodes `author="narrator"` or `author="player"`

No silent-empty-author construction site survives. The schema change has no migration cascade.

**Findings (non-blocking):**

| Severity | Issue | Location | Suggested fix |
|----------|-------|----------|---------------|
| [LOW][SIMPLE] | The new player-append code lives inside the persistence `try/except` block (lines 1535-1581). A failure in the player append (`_resolve_acting_character_name`, `NarrativeEntry` construction, or `append_narrative` SQL call) would now cancel the subsequent narrator append. Empirically the failure odds are essentially zero — `_resolve_acting_character_name` is documented never to raise, `NarrativeEntry(author="player", content=action, ...)` cannot fail given upstream sanitization, and any DB error would have failed the narrator append anyway. But the *region of failure-coupling* widened compared to pre-fix. Worth a note for the next contributor who edits this seam. | `sidequest/server/websocket_session_handler.py:1535-1581` | If a future failure surface emerges, hoist the player append into its own try/except so a player-append failure logs distinctly and does not cancel the narrator append. No action required for this story. |

None block. The schema-level enforcement is the load-bearing improvement — exactly the durable protection AC4 demands.

**Tags satisfied:** `[EDGE]` opening-turn skip + dice replay path verified, `[SILENT]` no swallowed errors verified except the widened-swallow noted as [SIMPLE], `[TEST]` test quality verified, `[DOC]` docstring/comments accurate (validator docstring matches behavior, comments in websocket_session_handler explain skip semantics), `[TYPE]` schema change properly typed (required field + validator), `[SEC]` no security surface in this diff (sanitization happens upstream, log content is sanitized text), `[SIMPLE]` widened-swallow finding above, `[RULE]` 13-rule python checklist walked above.

**Handoff:** To Captain Carrot Ironfoundersson (SM) for finish-story.

## Delivery Findings

### Reviewer (code review)
- **Improvement** (non-blocking): Player-append now sits inside the same persistence `try/except` block as the narrator-append, widening the failure-coupling region. Practical risk is near-zero today, but a future failure in the player append would silently cancel the narrator append. Affects `sidequest/server/websocket_session_handler.py:1535-1581`. *Found by Reviewer during code review.*