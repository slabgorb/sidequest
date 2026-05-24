---
story_id: "61-11"
epic: "61"
workflow: "tdd"
---
# Story 61-11: Scene-gate genre_chargen / genre_extraction / genre_keeper_monologue (drop from STABLE_SECTION_NAMES)

## Story Details
- **ID:** 61-11
- **Epic:** 61 — Bounded Narrator Prompt: Slim Snapshot + Wire RAG
- **Workflow:** tdd
- **Points:** 2
- **Type:** refactor
- **Repos:** server

## Story Summary

`genre_chargen`, `genre_extraction`, and `genre_keeper_monologue` were promoted to `STABLE_SECTION_NAMES` under ADR-112 / Story 57-3 for cache stability — but unlike the rest of the stable set, they are scene-typed:

- `chargen` prose only matters during character creation
- `extraction` prose only when leaving the dungeon with loot
- `keeper_monologue` only when the Keeper speaks (rare scripted beats)

Carrying ~450 tok of out-of-scope prose on every neutral 'you walk into the tavern' turn is the wrong end of the cache-vs-relevance trade. The cache-thrash argument ADR-112 used to defer `genre_combat_voice` / `genre_chase_voice` (encounter-boundary churn) does not apply here: chargen completes ONCE per session (single cache miss, amortized by turn 5), extraction/keeper_monologue fire on rare scene-type transitions.

## Acceptance Criteria

1. `genre_chargen`, `genre_extraction`, `genre_keeper_monologue` are removed from `STABLE_SECTION_NAMES`
2. Each of the three sections is registered conditionally in `build_narrator_prompt` only when its scene predicate is true; the predicates are derived from existing TurnContext / GameState fields, no new state flags introduced
3. A unit test in `tests/agents/test_prompt_framework/test_bucket.py` asserts each name now maps to `SectionBucket.User`
4. A fixture-driven behavior test in `tests/agents/` constructs a chargen-active TurnContext, calls `build_narrator_prompt`, asserts `genre_chargen` lands in user_message; then constructs a post-chargen TurnContext and asserts `genre_chargen` is absent. Mirror tests for extraction and keeper_monologue
5. ADR-112 receives an amendment recording the three sections' demotion from STABLE plus the predicate-gating decision

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-05-24

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | - | - |

## Delivery Findings

No upstream findings.

## Design Deviations

None yet.

---

## ADR References
- **ADR-112** — Genre Prose Cache Promotion (partial)
- **ADR-098** — Stateless Narrator Turns
- **ADR-111** — Recency-Zone Narrator Guardrails

## Code Paths

**Primary:** `sidequest-server/`
- `sidequest/agents/prompt_framework/bucket.py` — STABLE_SECTION_NAMES (lines 50-53)
- `sidequest/orchestrator.py` — build_narrator_prompt (around line 1491+)
- `tests/agents/test_prompt_framework/test_bucket.py` — unit tests
- `tests/agents/` — behavior tests (new fixtures)

**Documentation:**
- `docs/adr/0112-*.md` — Amendment

## Dependencies

None. Story 61-11 is independent; it completes ADR-112's scope refinement.
