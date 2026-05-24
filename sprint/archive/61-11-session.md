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
**Phase:** finish
**Phase Started:** 2026-05-24T12:37:15Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | 2026-05-24T11:21:51Z | 11h 21m |
| red | 2026-05-24T11:21:51Z | 2026-05-24T12:04:45Z | 42m 54s |
| green | 2026-05-24T12:04:45Z | 2026-05-24T12:14:26Z | 9m 41s |
| spec-check | 2026-05-24T12:14:26Z | 2026-05-24T12:16:37Z | 2m 11s |
| verify | 2026-05-24T12:16:37Z | 2026-05-24T12:25:59Z | 9m 22s |
| review | 2026-05-24T12:25:59Z | 2026-05-24T12:35:04Z | 9m 5s |
| spec-reconcile | 2026-05-24T12:35:04Z | 2026-05-24T12:37:15Z | 2m 11s |
| finish | 2026-05-24T12:37:15Z | - | - |

## Delivery Findings

### TEA (test design)
- **Gap** (non-blocking): SM-setup created the feature branch on `sidequest-content` (per the misfiled REPOS=server,content) but NOT on `sidequest-server` where the actual change lives. The content branch was empty and was deleted during the SM redirect; TEA created `feat/61-11-scene-gate-stable-sections` on the server repo manually at first-commit time. Affects `pennyfarthing-dist/agents/sm-setup.md` (branch-creation phase should verify-then-create per listed repo, not assume the field is correct and silent-no-op when a sibling repo turns out to be wrong). *Found by TEA during test design.*
- **Gap** (non-blocking): SM-setup wrote the session file to `sprint/.session/` (legacy/morgue location) instead of `.session/` where `pf handoff complete-phase` expects it. TEA relocated manually before invoking complete-phase. Recurring issue — already captured in user memory `feedback_sm_setup_misfiles_session`. Affects `pennyfarthing-dist/agents/sm-setup.md`. *Found by TEA during test design.*
- **Gap** (non-blocking): SM-setup skipped story context creation; Architect filled in. Recurring per memory. Affects sm-setup MODE=setup. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): 2 tests in `sidequest-server/tests/agents/test_61_9_sdk_commitment.py` (`test_narrator_purpose_with_sdk_backend_returns_tooling_client`, `test_tool_purpose_with_sdk_backend_returns_tooling_client`) fail on `feat/61-11-*` because they require `ANTHROPIC_API_KEY`. Pre-existing on `origin/develop` (since 61-9 merge `e218ac6`); not caused by 61-11. Either the tests should `pytest.skip` when the env var is unset, or the test env should provision the key. *Found by Dev during GREEN verification.*
- **Improvement** (non-blocking): pre-existing pyright error at `sidequest-server/sidequest/agents/orchestrator.py:2678` — `Cannot access attribute "send_stream" for class "LlmClient"`. Pre-existing on develop; ~1000 lines from the 61-11 edit. Fixing it requires a narrowed type or a `cast` around the streaming call site. *Found by Dev during GREEN verification.*
- **Improvement** (non-blocking): ADR-112 amendment in orchestrator `docs/adr/0112-*.md` is still owed (out of scope for the server feature branch). Should record (1) `genre_chargen` demotion + predicate-gate; (2) the deferral of `extraction`/`keeper_monologue` and the runtime-signal gap that blocks their demotion; (3) reference to commit `35f42e6`. Tech Writer surface. *Found by Dev during GREEN verification.*

### TEA (test verification)
- **Improvement** (non-blocking): pre-existing format drift on develop — `sidequest-server/sidequest/server/websocket.py` and `sidequest-server/tests/server/test_61_followup_C_close_store_wiring.py` both fail `ruff format --check` on commits prior to 61-11. Not caused by this story (my diff fixed only the two 61-11 test files). Worth a chore commit on develop. *Found by TEA during verify phase.*

### Reviewer (audit)
- **Improvement** (non-blocking): ADR-112 amendment in orchestrator `docs/adr/0112-*.md` is still owed (also flagged by Dev). The amendment is the AC-5 deliverable that gates "the partial reversal is visible to the next architect." Without it, a future engineer reading ADR-112 cold will see the original full-cache promotion and not know it's been walked back for `genre_chargen`. Recommend SM create a 1-pt chore for Tech Writer and wire it into the finish ceremony. *Found by Reviewer during review phase.*
- **Improvement** (non-blocking): consider follow-up stories to build runtime signals for `extraction_active` and `keeper_speaking` so the other two scene-typed sections can be demoted the same way. The deviation log forecasts this; making it concrete as backlog stories prevents drift. *Found by Reviewer during review phase.*
- **Question** (non-blocking, deferred to a future Dev): the gate at `orchestrator.py:1608` is structurally safe because `opening_directive` only propagates from `_run_opening_turn_narration` (not `_handle_player_action` / `dice_throw`). A future refactor that "helpfully" threads `sd.opening_directive` through every `_build_turn_context` call would re-leak chargen prose on the first player-action turn before the consume-once clear at `websocket_session_handler.py:5371` fires. The consume-once contract (line 5367-5371 comment) is the load-bearing invariant; flag for any future propagation-site change. *Found by Reviewer during devil's-advocate pass.*

## Design Deviations

### TEA (test design)
- **Scope reduced from three sections to one (option A — architect recommendation in context-story-61-11.md §Predicate Audit; user-confirmed 2026-05-24)**
  - Spec source: sprint/epic-61.yaml story 61-11, AC-1 and AC-2
  - Spec text: "remove these three names from STABLE_SECTION_NAMES" + "Each of the three sections is registered conditionally ... predicates derived from existing TurnContext / GameState fields, no new state flags introduced"
  - Implementation: Only `genre_chargen` is demoted and gated; `genre_extraction` and `genre_keeper_monologue` stay on STABLE
  - Rationale: Predicate audit found `chargen_active` IS expressible via existing `TurnContext.opening_directive` (set at `websocket_session_handler.py:181-346`, cleared after opening turn). `extraction_active` and `keeper_speaking` have NO existing runtime signal — neither `TurnContext`, `GameSnapshot`, encounter state, nor `LobbyState` carries them. The SM-forbidden alternative (inventing flags) would expand scope well beyond 2 points. User selected option A 2026-05-24
  - Severity: major (changes count of demoted sections from 3 to 1; ADR-112 amendment AC scope changes correspondingly)
  - Forward impact: ~150 tok/turn savings (chargen only) instead of ~450 tok/turn projected by the story body. Two follow-up stories implied: one to build extraction/keeper runtime signals (or migrate to ADR-113 tool-attached scope), one to demote `genre_town` after profiling

### Architect (reconcile)

- **TEA option-A scope-reduction entry verified accurate.** All 6 fields are present and substantive. Spec source path resolves; quoted spec text matches `sprint/epic-61.yaml` story 61-11 ACs 1 and 2 verbatim; implementation description matches the diff (`bucket.py` removes only `genre_chargen`; `orchestrator.py:1608` adds the predicate gate only to the chargen block; adjacent extraction/keeper/town blocks unchanged). Rationale traces to `sprint/context/context-story-61-11.md` §Predicate Audit. Forward impact's two-follow-up forecast is captured concretely in Reviewer's Delivery Findings.

- **AC-5 (ADR-112 amendment) — DEFERRED, not satisfied within this story**
  - Spec source: sprint/epic-61.yaml story 61-11, AC-5
  - Spec text: "ADR-112 receives an amendment recording the three sections' demotion from STABLE plus the predicate-gating decision"
  - Implementation: NOT performed within the green path. The orchestrator's `docs/adr/0112-*.md` file is unchanged on `main`; the partial-reversal rationale lives only in (a) the in-code docstring in `sidequest-server/sidequest/agents/prompt_framework/bucket.py` (post-`35f42e6`) and (b) the in-code comment block at `sidequest-server/sidequest/agents/orchestrator.py:1594-1607`. The amendment file itself remains owed as a Tech-Writer post-merge deliverable.
  - Rationale: The ADR file lives on the orchestrator repo's `main` branch, not the server feature branch. Touching it from the server PR would split the diff across two repos; the correct pattern is a separate orchestrator commit on `main` after the server PR merges. Dev flagged this as a Delivery Finding (non-blocking improvement) and Reviewer explicitly recommended SM create a 1-pt chore for Tech Writer at finish time. Per memory `feedback_adr_priority_current_over_history`, making the ADR amendment LOUD is preferable to letting it ride uncreated.
  - Severity: minor (doc deliverable, not code; the in-code comments carry the same content for any engineer reading the implementation; only an engineer reading ADR-112 cold without first touching the code would be misled)
  - Forward impact: a future architect reading ADR-112 sees the original full-cache promotion and the original §Defer list (combat_voice, chase_voice) without knowing that `genre_chargen` has been walked back. If the chore is not created at finish, this AC-5 deferral risks rotting into permanent invisible drift. SM MUST create the Tech-Writer chore before story finish per Reviewer's audit finding.

- **AC-4 mirror tests for `extraction` and `keeper_monologue` — INTENTIONALLY NOT WRITTEN (subsumed by AC-1/AC-2 scope reduction)**
  - Spec source: sprint/epic-61.yaml story 61-11, AC-4
  - Spec text: "Mirror tests for extraction and keeper_monologue"
  - Implementation: No mirror tests for `genre_extraction` or `genre_keeper_monologue` predicate-true/false behavior were written, because those two sections were NOT demoted (per the option-A scope reduction). Instead, the parametrized `test_unaffected_stable_sections_still_carry_unconditionally` in `sidequest-server/tests/agents/test_61_11_scene_gated_genre_chargen.py` exercises the OPPOSITE invariant for the two un-demoted sections — that they still register unconditionally on a neutral turn and still land in `system_text`. This is the correct test surface for the reduced scope: a behavior test for "section is gated on X" is meaningless when no gate exists.
  - Rationale: AC-4 was written assuming all three sections would be demoted. Once option A reduced the scope to chargen only, mirror tests for the other two sections would have asserted a behavior that the implementation does NOT have (they are unchanged, not gated). The parametrized regression guard is the appropriate substitute — it pins the un-changed state and catches any future copy-paste of the gate into adjacent blocks.
  - Severity: minor (test surface change tracks the scope reduction; the invariant under test is correct for the implementation)
  - Forward impact: when a follow-up story builds runtime signals for `extraction_active` and/or `keeper_speaking`, that story's TEA should write the mirror tests AC-4 originally specified (predicate-true → section in user_message; predicate-false → section absent). The parametrized regression guard added by 61-11 will need to be retired or narrowed at that point (the parametrize loop would lose whichever section is being demoted).

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

## Sm Assessment

**Scope:** Demote three scene-typed section names from `STABLE_SECTION_NAMES` and register them conditionally based on existing session state. Bounded, ~2 points, no new wires — pure cache-vs-relevance correction inside the prompt framework.

**Why now:** ADR-112 explicitly deferred `genre_combat_voice` / `genre_chase_voice` on cache-thrash grounds, but ate the same cost for chargen/extraction/keeper_monologue without testing whether those firings actually thrash. They don't (chargen: once per session; extraction/keeper: rare scripted beats), so ~450 tok of always-on prose is misallocated cache budget on every neutral turn.

**Predicate sources (must be existing state — no new flags):**
- `chargen_active` — derive from session phase / character creation lifecycle. TEA should locate the exact field during RED-phase fixture construction; `TurnContext` and `GameState` are the named sources in AC #2.
- `extraction_active` — derive from active scene type / dungeon-exit transition.
- `keeper_speaking` — derive from current speaker / scripted-beat marker.

If TEA finds none of these are unambiguously expressible from existing fields, raise it back to SM before inventing a flag — that would invalidate the scope and we'd revisit whether the demotion is correct shape.

**Test surface (per AC #3, #4):**
1. Unit test in `tests/agents/test_prompt_framework/test_bucket.py`: each of the three names maps to `SectionBucket.User` (no longer Stable).
2. Behavior tests in `tests/agents/` for each section: predicate-true TurnContext → section lands in user_message; predicate-false TurnContext → section absent.

**Out of scope (do not creep):**
- `genre_town` — story body explicitly defers ("frequent enough that profiling needed before moving"). Leave on STABLE.
- `genre_combat_voice` / `genre_chase_voice` — ADR-112 deferral stands.
- Snapshot slimming, RAG wiring, recency guardrails — separate epic-61 stories.

**ADR amendment (AC #5):** `docs/adr/0112-*.md` gets an amendment block. Per memory `feedback_adr_priority_current_over_history`, make it LOUD about the partial reversal and point at the predicate-gating commit. Lives on orchestrator main (not the server feature branch); apply alongside the merged server change.

**Risk:** Low. The change is local to two files plus tests, predicates are read-only on existing state, and the reversal direction is conservative (smaller cache footprint, not larger).

**Handoff target:** TEA for RED phase. The four ACs that are testable (#1–#4) drive the failing tests; AC #5 (ADR amendment) is doc work that follows the green merge.

**Forbidden in this story (carry forward to every subagent):** no `git stash` variants; no running tests on a prior commit to "prove" a failure is pre-existing.

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Reason:** Scope-reduced 2-pt refactor with both a pure-Python bucket invariant and a wiring assertion through `Orchestrator.build_narrator_prompt`. Bucket-only would miss the gating; gating-only would miss the bucket. Both halves are load-bearing.

**Test Files:**
- `sidequest-server/tests/agents/test_prompt_framework/test_bucket.py` — replaced `test_genre_chargen_resolves_to_system` with `test_genre_chargen_resolves_to_user` (inverse pin), and updated `test_allowlist_minimum_contents` to drop `genre_chargen` from the required set (comment points at 61-11 amendment). The other three ADR-112 promotions (`extraction`, `keeper_monologue`, `town`) stay on STABLE — their pin tests are untouched.
- `sidequest-server/tests/agents/test_61_11_scene_gated_genre_chargen.py` (NEW) — wiring tests through `Orchestrator.build_narrator_prompt` + `registry.compose_split("narrator")` for the predicate-true / predicate-false / unaffected-sections cases.

**Tests Written:** 3 new failing tests + 3 parametrized regression-guards covering AC #1, AC #2, AC #3, AC #4 (post scope reduction — only `genre_chargen`).

**Status:** RED (3 failing, 11 passing — confirmed via testing-runner `61-11-tea-red`)

### RED state evidence

```
FAILED tests/agents/test_prompt_framework/test_bucket.py::test_genre_chargen_resolves_to_user
  AssertionError: assert <SectionBucket.system> == <SectionBucket.User>
FAILED tests/agents/test_61_11_scene_gated_genre_chargen.py::test_genre_chargen_lands_in_user_message_on_opening_turn
  AssertionError: genre_chargen prose missing from user_message on opening turn
FAILED tests/agents/test_61_11_scene_gated_genre_chargen.py::test_genre_chargen_absent_from_prompt_on_neutral_turn
  AssertionError: genre_chargen prose appeared in system_prompt on neutral (non-opening) turn
```

The first failure is the bucket demotion (today: `genre_chargen` is still in STABLE → resolves to System). The second is the bucket-half wiring (today: even when registered, content lands in `system_text` because of the STABLE membership). The third is the gating-half wiring (today: registration is unconditional, so chargen prose appears in `system_text` on a neutral turn — exactly the per-turn carry the story eliminates).

### Rule Coverage

| Rule (project memory / CLAUDE.md) | Test(s) | Status |
|------|---------|--------|
| `feedback_adr_priority_current_over_history` — make stale ADR claims LOUD on regression | `test_genre_chargen_resolves_to_user` (failure msg explicitly cites 61-11 amendment + ~150-tok cost) | failing as RED, will pin once green |
| Server CLAUDE.md "No Source-Text Wiring Tests" — drive through real handler + assert on typed output | `test_genre_chargen_lands_in_user_message_on_opening_turn` + `test_genre_chargen_absent_from_prompt_on_neutral_turn` use `Orchestrator.build_narrator_prompt` + `registry.compose_split` (real production assembly path, not regex on source) | failing as RED |
| Server CLAUDE.md "Every Test Suite Needs a Wiring Test" — at least one integration test that verifies the component is reachable from production code paths | The two `test_61_11_*` wiring tests call the real async `build_narrator_prompt` end to end | failing as RED |
| Server CLAUDE.md "No Silent Fallbacks" — predicate-false case must SKIP registration, not register-then-empty | `test_genre_chargen_absent_from_prompt_on_neutral_turn` asserts content absent from BOTH `system_text` AND `user_text` — catches both "registered to wrong bucket" and "registered when shouldn't be" silent-substitution failure modes | failing as RED |
| Predicate-from-existing-state rule (SM scope lock) — no new flags introduced | Behavior test only reads `TurnContext.opening_directive` and `turn_number` (both pre-existing Phase 1 fields at `orchestrator.py:647` and `:581`). No new field needed | enforced by construction in fixtures |
| ADR-112 §Defer regression guard — adjacent sections must not get the gate via copy-paste | `test_unaffected_stable_sections_still_carry_unconditionally` (3 parametrized cases for extraction/keeper_monologue/town) — runs on neutral-turn fixture; asserts each still lands in `system_text` | passing today (regression guard for Dev's GREEN edit) |

**Rules checked:** 6 of 6 applicable rules have test coverage.
**Self-check:** 0 vacuous tests. Every assertion compares non-trivial content (bucket enum, substring presence/absence with unique markers, contradicting-bucket negation).

### Dev pointer (GREEN phase)

Two-file diff in `sidequest-server`:

1. `sidequest/agents/prompt_framework/bucket.py:50-53` — drop `"genre_chargen"` from the `STABLE_SECTION_NAMES` frozenset. Update the docstring/comment immediately above the four ADR-112 promotions to note the 61-11 partial reversal; leave the other three names on the list.

2. `sidequest/agents/orchestrator.py:1595-1604` — change the chargen registration guard from `if gp.chargen:` to `if gp.chargen and context.opening_directive is not None:`. Do NOT add a flag to `TurnContext`. Do NOT touch the adjacent blocks for `gp.extraction` (1558-1567), `gp.keeper_monologue` (1571-1580), or `gp.town` (1583-1592) — the regression-guard test catches any bleed-through.

`uv run pytest -v -n0 tests/agents/test_prompt_framework/test_bucket.py tests/agents/test_61_11_scene_gated_genre_chargen.py` should flip all 14 tests to PASS after the two edits.

Full server suite (`uv run pytest -v`) should also stay green — the diff is local; no broader test was relying on `genre_chargen` content appearing in the cached prefix on every turn (the only such assertion I found in `test_bucket.py` is the one this story explicitly replaces).

### Out of scope for Dev (do not creep)

- ADR-112 amendment (orchestrator `docs/adr/0112-*.md` on `main`) — Tech Writer surface, post-merge. Flag in review-phase Delivery Findings.
- Build extraction / keeper runtime signals — future story.
- Demote `genre_town` — future story, requires profiling.
- Touch anything in `narrator_prompts/` — that was the 61-9 surface.

**Handoff:** To Dev (Ponder Stibbons) for GREEN.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — implementation committed, all RED tests now pass.

### Diff applied (server, 3 files)

1. `sidequest/agents/prompt_framework/bucket.py` — dropped `"genre_chargen"` from `STABLE_SECTION_NAMES`; rewrote the ADR-112 docstring above the frozenset to record the partial reversal, name the predicate, and point the next architect at the runtime-signal gap for `extraction`/`keeper_monologue`.

2. `sidequest/agents/orchestrator.py:1595-1604` — chargen registration guard changed from `if gp.chargen:` to `if gp.chargen and context.opening_directive is not None:`. No new field on `TurnContext`. Adjacent blocks (extraction at 1558, keeper at 1571, town at 1583) untouched — the regression-guard test catches any copy-paste bleed.

3. `tests/agents/test_cache_ttl_prefix_and_otel.py` — pre-existing cache-evidence test required updating to reflect the demotion:
   - `test_promoted_genre_prose_lands_in_cached_system_block` now asserts only three still-Stable sections (`extraction`, `keeper`, `town`) ride `system_blocks[0]`, AND adds a regression guard that `<genre-chargen>` is ABSENT from every part of the prompt on a turn with `opening_directive=None`. The fixture comment also explicitly notes the chargen demotion.
   - NEW `test_demoted_genre_chargen_lands_in_user_message_on_opening_turn` — pins the predicate-true / demoted-bucket combination through the SDK request shape (mirrors the same `recorded_requests[0]` assertion path as the existing cache-evidence test, inverted for the demoted section). This is a second wiring test alongside the two TEA wrote — both confirm the same behavior through different assembly paths (`registry.compose_split` vs the full SDK request).

### Test results

| Suite | Pass | Fail | Notes |
|-------|------|------|-------|
| Story-touched (bucket + new behavior + cache-ttl) | 24 | 0 | All three RED tests now GREEN; the cache-evidence test updated to the new shape; pre-existing pin tests for the deferred sections still GREEN |
| Full server suite (`uv run pytest`) | 7512 | 2 | 2 failures are pre-existing on develop |

Pre-existing failures (NOT caused by 61-11):
- `tests/agents/test_61_9_sdk_commitment.py::test_narrator_purpose_with_sdk_backend_returns_tooling_client`
- `tests/agents/test_61_9_sdk_commitment.py::test_tool_purpose_with_sdk_backend_returns_tooling_client`

Both require `ANTHROPIC_API_KEY` (env var not set in the local test environment); they construct a real `AnthropicSdkClient`. They fail on `origin/develop` too (61-9 landed at `e218ac6` and these tests have been failing since). My diff does not touch `llm_factory.py`, `anthropic_sdk_client.py`, or any related construction path — I verified by grepping the diff for `build_llm_client` / `AnthropicSdkClient` / `ENV_BACKEND` and finding zero matches. Flagged below as Delivery Findings non-blocking.

Pre-existing pyright error: `sidequest/agents/orchestrator.py:2678 — Cannot access attribute "send_stream" for class "LlmClient"`. This is at line 2678, ~1000 lines away from my edits (chargen block at 1595-1604). Pre-existing on develop; my diff does not affect it.

### Lint / format / typecheck

- `uv run ruff check` on all three touched files: **clean**.
- `uv run pyright` on bucket.py: clean. On orchestrator.py: one pre-existing error at line 2678 (above), zero new errors in or around my diff at line 1595-1604.

### Things I did NOT do (scope discipline)

- No ADR-112 amendment in orchestrator `docs/adr/` — explicitly out of scope per TEA pointer; Tech Writer post-merge.
- No new field on `TurnContext` — predicate audit found the existing `opening_directive` field sufficed.
- No edits to extraction / keeper_monologue / town registration blocks — regression test `test_unaffected_stable_sections_still_carry_unconditionally` confirms they still fire unconditionally.
- No edits in `sidequest-content` — server-only diff.

**Handoff:** To Reviewer (Granny Weatherwax).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (within the user-confirmed option-A scope reduction)
**Mismatches Found:** 1 doc deliverable deferred — already logged

### Spec-authority pass

Per spec-authority hierarchy (story scope → story context → epic context → architecture docs):

- **Story scope (session ACs, lines 26-32)** — original 5 ACs framed against three sections (chargen, extraction, keeper_monologue).
- **Story context (`sprint/context/context-story-61-11.md` §Predicate Audit + §Resolution)** — recommends option A (chargen-only) with full rationale and explicit Design Deviation pre-log.
- **User decision 2026-05-24** — selected option A via AskUserQuestion at the architect handoff.
- **Design Deviation (session, lines 60-68)** — formal 6-field log of the scope reduction.

The session ACs and the context doc were in tension; the user-confirmed deviation log resolves the tension toward option A. The Dev diff matches option A exactly.

### Per-AC alignment review

| AC (original) | Spec (option-A reduced) | Code | Status |
|---------------|-------------------------|------|--------|
| AC-1 — three names removed from STABLE | only `genre_chargen` removed; extraction/keeper/town stay with rationale comment | `bucket.py` removes `genre_chargen`; doc-comment records the deferral of the other two | Aligned per deviation |
| AC-2 — three sections conditionally registered from existing fields | only chargen gated on `TurnContext.opening_directive` (pre-existing field at `orchestrator.py:647`); extraction/keeper/town unchanged | `orchestrator.py:1595` adds `and context.opening_directive is not None` guard; no flag added to TurnContext | Aligned per deviation |
| AC-3 — unit test asserts each name → User | unit test asserts `genre_chargen` → User AND extraction/keeper/town stay → System (pinning the deferral) | `test_bucket.py::test_genre_chargen_resolves_to_user` + three preserved `_resolves_to_system` pin tests | Aligned per deviation |
| AC-4 — predicate-true/false behavior tests for each section | predicate-true/false behavior tests for chargen; regression-guard test that adjacent blocks don't gate by copy-paste | `test_61_11_scene_gated_genre_chargen.py` (3 tests) + parametrized `test_unaffected_stable_sections_still_carry_unconditionally` (3 cases) + updated cache-evidence test (`test_cache_ttl_prefix_and_otel.py` adds `test_demoted_genre_chargen_lands_in_user_message_on_opening_turn`) | Aligned per deviation |
| AC-5 — ADR-112 amendment | amendment scope rewritten to reflect partial reversal (chargen only) and explicit defer note for extraction/keeper | NOT YET WRITTEN — flagged in Dev Delivery Findings as Tech Writer post-merge surface | **Mismatch: Missing in code** |

### Mismatch detail

- **AC-5 ADR amendment not yet authored** (Missing in code — Cosmetic, Minor)
  - Spec: orchestrator `docs/adr/0112-*.md` gets an amendment block recording (1) `genre_chargen` demotion + predicate-gate, (2) deferral of `extraction`/`keeper_monologue` with the runtime-signal-gap rationale, (3) reference to commit `35f42e6`.
  - Code: no commit on orchestrator main yet; the server commit message + the in-code comments (bucket.py docstring, orchestrator.py:1591-1604 comment block) carry the same content but the ADR file itself is untouched.
  - Recommendation: **D — Defer** to Tech Writer surface. Lives on orchestrator `main` (not the server feature branch); Dev correctly identified this as a separate-PR-on-a-different-repo deliverable. Already flagged in Dev Delivery Findings as a non-blocking improvement. Reviewer should re-flag in their findings so SM creates the doc work item before story finish. **Not blocking the server PR merge.**

### Substantive correctness checks (beyond AC literal)

1. **Predicate choice.** Context doc named two valid formulations — `opening_directive is not None` and `turn_number == 0`. Dev chose the former (the recommended, semantically-tighter one — directly marks "post-chargen handoff turn" vs "first turn for any reason"). ✓
2. **Predicate is read-only.** The chargen registration block only READS `context.opening_directive`; it does not consume/clear it. The clearing remains the responsibility of the existing opening-turn dispatch site (websocket handler). No double-clear risk. ✓
3. **Zero-byte-leak discipline.** The outer `if gp.chargen` guard is preserved; the inner `and context.opening_directive is not None` adds a second gate. If `gp.chargen` is empty (genre has no chargen prose, e.g. some workshop packs), the block skips entirely — no degenerate registration of a `<genre-chargen>\n\n</genre-chargen>` empty wrapper. ✓
4. **No new flags.** `TurnContext` dataclass unchanged. Verified by inspecting the diff — no field additions, no constructor changes. ✓
5. **No bleed into adjacent blocks.** Extraction (1558), keeper (1571), town (1583) blocks are byte-identical in the diff (zero changes). Regression-guard test exercises this via parametrize on a neutral-turn fixture. ✓
6. **Cache-evidence test correctness.** Dev correctly recognized the pre-existing `test_promoted_genre_prose_lands_in_cached_system_block` would FAIL after the demotion and updated it in the same commit. The updated test now: (a) pins the three still-Stable sections in `system_blocks[0]`, (b) pins `<genre-chargen>` ABSENT from every prompt slot on a `opening_directive=None` turn, AND (c) the new sibling test pins `<genre-chargen>` lands in `user_message` (not in either system block) on an `opening_directive`-set turn. The two-test pair is symmetric and catches both halves of the demotion. ✓
7. **Pre-existing failures correctly attributed.** Dev's claim that the two 61-9 SDK tests fail on develop (commit `e218ac6`) is consistent with reading the test code — they construct `AnthropicSdkClient` via `build_llm_client`, which requires `ANTHROPIC_API_KEY`. My grep of the Dev diff confirms no touch to `llm_factory.py` or `anthropic_sdk_client.py`. ✓

### Decision

**Proceed to TEA verify.** No code changes required. The AC-5 (ADR amendment) deferral is the only mismatch and is correctly classified as a Tech-Writer post-merge surface — Reviewer should reflect it as a tracked follow-up; SM should create the work item before story finish.

**Forbidden for downstream (carry forward):** no `git stash`; no testing on a prior commit. Reviewer should attribute pre-existing failures by reading test code + grepping the diff, not by checking out an earlier commit.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed — 24/24 story tests passing on the post-format commit (`7672a81`).

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (orchestrator.py, bucket.py, test_bucket.py, test_61_11_scene_gated_genre_chargen.py, test_cache_ttl_prefix_and_otel.py — diff-only scope)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 6 findings (2 medium, 3 low, 1 high "do-not-change") | conftest extraction for context builders + Prompts factory; intentional split confirmed |
| simplify-quality | 2 findings (both low) | dash vs underscore marker naming; line-number precision in a comment |
| simplify-efficiency | 1 finding (medium) | parametrize → for-loop conversion |

**Applied:** 0 high-confidence fixes (none found)
**Flagged for Review:** 3 medium-confidence findings (see "Triage" below)
**Noted:** 5 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean (no auto-fixes applied)

### Triage (medium-confidence findings)

1. **reuse: extract `_make_opening_turn_context` / `_make_neutral_turn_context` to conftest.py** — Dismissed for this story. The conftest already has `simple_turn_context` (turn 0) and `simple_turn_context_turn_three`. The new 61-11 helpers add `opening_directive` to turn-0 (true case) and turn-5 (false case). Hoisting them exports per-story shapes to every test that uses agents/conftest — adds API surface for very little gain. If a follow-up story (extraction/keeper runtime signal work) reuses these exact shapes, hoist then.

2. **reuse: consolidate Prompts factory between the two files** — Dismissed for this story. The cache-evidence test's `_prompts_with_all_promotions` uses underscore-style markers (`STORY_57_3_*`) and has 3 call-sites already. Unifying the factories means either standardizing markers (touches 3 call-sites + every assertion that greps for `STORY_57_3_*`) or threading override kwargs through — both are larger refactors than the cleanup saves. Out of proportion for a 2-pt story.

3. **efficiency: `@pytest.mark.parametrize` → for-loop on `test_unaffected_stable_sections_still_carry_unconditionally`** — Dismissed with rationale. The subagent recommended a for-loop for ~35-line LOC savings, but missed the test-paranoia counter-argument: parametrize gives 3 independent test records, so if a future Dev breaks the extraction gate the run also reports keeper + town gate breakage. A for-loop short-circuits on first failure and masks the others. Per the TEA `<test-paranoia>` doctrine ("What haven't I tested?"), the regression guard is more useful when each section is its own pytest record. Parametrize stays.

### Low-confidence notes (not applied)

- `STORY-57-3-FIXTURE` (dash) in my new test vs `STORY_57_3_*` (underscore) in the pre-existing cache-evidence test. Style-only across two files; the within-file convention is internally consistent.
- `bucket.py` comment references "chargen block ~1595" — actual span is 1594-1617. Tilde-prefixed line numbers rot anyway; precision is marginally useful. Skipped.
- Two-assertion-paths split (compose_split vs SDK request shape) is intentional and load-bearing — high-confidence "do-not-change" from reuse confirms it.
- Cache-evidence test's `_prompts_with_all_promotions` keeps the chargen marker in the fixture despite chargen being demoted — used by two tests (the demoted predicate-true case and the unchanged-three-sections case). Correct as-is.
- Loop over `promoted_markers` tuple in the cache-evidence test is already DRY (no refactor opportunity).

### Quality-pass gate

- `uv run ruff check .` — **clean** on the touched files (also clean across the full server tree).
- `uv run ruff format --check .` — initially flagged my two test files (parametrize multi-line wrap + trailing list-formatting); fixed via `ruff format` in commit `7672a81`. Two other pre-existing format-drift files on develop (`sidequest/server/websocket.py`, `tests/server/test_61_followup_C_close_store_wiring.py`) are out of scope for 61-11.
- `uv run pytest -v -n0 tests/agents/test_prompt_framework/test_bucket.py tests/agents/test_61_11_scene_gated_genre_chargen.py tests/agents/test_cache_ttl_prefix_and_otel.py` — **24/24 passing** on the post-format commit.
- Full server suite: 7512 passed, 2 pre-existing 61-9 SDK env failures (correctly attributed in Dev's findings).
- Pre-existing pyright error at `orchestrator.py:2678` unchanged.

**Quality Checks:** All passing (within the documented pre-existing scope).
**Handoff:** To Reviewer (Granny Weatherwax).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none (4 rules checked, 0 violations) | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents` settings — pre-filled per gate spec)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred from subagents (both enabled returned clean)

## Reviewer Assessment

**Verdict:** APPROVE
**Severity:** No Critical, no High, no Medium, no Low.

### Diff scope (sanity)

3 commits on `feat/61-11-scene-gate-stable-sections`, 5 files changed.

- `sidequest/agents/prompt_framework/bucket.py` — 1 string removed from a frozenset (`"genre_chargen"`), docstring expanded.
- `sidequest/agents/orchestrator.py:1594-1617` — chargen registration guard tightened with `and context.opening_directive is not None`, comment block added.
- `tests/agents/test_prompt_framework/test_bucket.py` — `test_genre_chargen_resolves_to_system` replaced with inverse `test_genre_chargen_resolves_to_user`; `test_allowlist_minimum_contents` required-set updated to drop `genre_chargen`.
- `tests/agents/test_61_11_scene_gated_genre_chargen.py` (new) — 3 behavior tests + 1 parametrized regression-guard (3 cases) for unaffected sections.
- `tests/agents/test_cache_ttl_prefix_and_otel.py` — `test_promoted_genre_prose_lands_in_cached_system_block` updated to assert only 3 still-Stable sections + adds chargen-absent guard on neutral turn; new sibling `test_demoted_genre_chargen_lands_in_user_message_on_opening_turn` pins the predicate-true case at the SDK request layer.

Preflight + security both clean. No new failures. Lint clean. Format clean post-`7672a81`. 24/24 story-touched tests GREEN; full suite 7512 passed with only the 2 pre-existing 61-9 SDK env failures (Dev correctly attributed; my grep of the diff confirms no touch to `llm_factory.py` / `anthropic_sdk_client.py`).

### Rule Compliance

Enumerated against project rules (SOUL.md, `sidequest-server/CLAUDE.md`, project memory).

| Rule | Applies to | Result |
|------|-----------|--------|
| No Silent Fallbacks (CLAUDE.md) | `orchestrator.py:1608` chargen guard | **COMPLIANT** — compound predicate skips registration entirely when `opening_directive is None`; no empty-string substitution, no default-path fallback. Section simply does not register. Confirmed by reviewer-security rule 1. |
| No Stubbing (CLAUDE.md) | full diff | **COMPLIANT** — no skeleton or placeholder code; pure behavior tightening of an existing block. |
| Don't Reinvent — Wire Up What Exists (CLAUDE.md) | predicate choice | **COMPLIANT** — predicate uses pre-existing `TurnContext.opening_directive` field (set at `websocket_session_handler.py:346`, cleared at line 5371). No new field on TurnContext. |
| Verify Wiring, Not Just Existence (CLAUDE.md) | demotion test surface | **COMPLIANT** — `test_61_11_scene_gated_genre_chargen.py::test_genre_chargen_lands_in_user_message_on_opening_turn` drives the real `Orchestrator.build_narrator_prompt` end to end + `registry.compose_split("narrator")`. Plus `test_demoted_genre_chargen_lands_in_user_message_on_opening_turn` exercises the SDK request shape — two independent assembly paths. |
| Every Test Suite Needs a Wiring Test (CLAUDE.md) | new test file | **COMPLIANT** — the new `test_61_11_*` file is wiring-only; the bucket-unit lives in `test_bucket.py`. |
| No Source-Text Wiring Tests (CLAUDE.md) | new tests | **COMPLIANT** — no `.read_text()` of production source; no regex over `.py` files; assertions are on typed `compose_split` tuples and SDK request `system_blocks` / `messages` structures. |
| OTEL Observability Principle (CLAUDE.md) | the gated registration | **COMPLIANT — verified no new OTEL needed.** The gate adds a precondition to an existing register-yes-no decision; it does not introduce a new subsystem. The framework-level `SPAN_COMPOSE` span at `prompt_framework/core.py:170` already emits `system_chars` / `user_chars` / `section_count`, which observably shift per turn as my gate fires/skips. The dashboard's existing prompt-tab attribution surface (`prompt_assembled` span at `orchestrator.py:2441`) carries the section list. Adding a per-gate OTEL emit would duplicate the framework signal. |
| Predicate-from-existing-state (SM scope lock) | new gate | **COMPLIANT** — `TurnContext` class unchanged; gate reads pre-existing field only. |
| `feedback_no_burying_bombs` (memory) | gate's special-case shape | **COMPLIANT** — the special case is owned end-to-end (registered iff opening turn; absence path = zero-byte leak; no per-site null guard hiding downstream silent no-ops). |
| `feedback_no_fallbacks_hard` (memory) | the chargen-specific narrowing | **COMPLIANT** — no degraded silent alternative; the section just doesn't register. |
| `feedback_adr_priority_current_over_history` (memory) | bucket docstring + orchestrator comment | **COMPLIANT** — both new comment blocks are LOUD about the partial-reversal status, name Story 61-11 + ADR-112 amendment by ID, and point at the predicate-gating decision + the runtime-signal gap that blocks the other two sections. |
| `feedback_plan_ceremony` (memory) | test ceremony for a 2-pt refactor | **COMPLIANT** — 3 behavior tests + 1 parametrized regression-guard + the cache-evidence sibling test is proportional for a load-bearing prompt-routing change. TEA's dismissal of the verify-phase parametrize→for-loop suggestion (independent failure surfaces) holds. |

### Observations

1. **[VERIFIED] gate is robust against stale `sd.opening_directive`** — Only `_run_opening_turn_narration` at `websocket_session_handler.py:5328-5333` propagates `sd.opening_directive` into `TurnContext` via `_build_turn_context(sd, opening_directive=sd.opening_directive, ...)`. The OTHER narration entry points — `handlers/player_action.py:376` and `handlers/dice_throw.py:252` — call `_build_turn_context(sd, ...)` WITHOUT the keyword, so `opening_directive` defaults to `None` on every player-action / dice turn regardless of what `sd.opening_directive` happens to be. Even if the consume-once clear at `websocket_session_handler.py:5371` were skipped (exception during `_execute_narration_turn`), the chargen prose still cannot leak into post-opening turns because the propagation never happens. This is a strong architectural property — the gate's failure surface is limited to a single read site.

2. **[VERIFIED] MP-joiner case is correctly narrowed, not regressed** — `_populate_opening_directive_on_chargen_complete` is invoked ONLY from the `is_first_commit` branch (per its docstring at `websocket_session_handler.py:214-216`). So a peer joining mid-session does NOT get `opening_directive` populated, hence does NOT get chargen prose on their first turn. Pre-fix, chargen prose was glued onto EVERY turn for everyone including MP joiners — but the prose itself ("describe what the character is carrying...the player should know their loadout before they step into the dark") is opening-turn flavor that was being MISAPPLIED to combat / dungeon-crawl / steady-state turns. Post-fix it fires only at the semantically correct moment for the first committer. MP joiners never had a real "opening turn" to use the chargen flavor on — pre-fix's behavior was prose leakage, not feature coverage.

3. **[VERIFIED] zero-byte-leak discipline preserved** — `bucket.py` diff: removes `"genre_chargen"` from the frozenset; STABLE_SECTION_NAMES still contains 13 stable names. `orchestrator.py:1608`: outer `if gp.chargen` guard preserved before the predicate AND-clause, so a genre pack with empty `gp.chargen` (legitimate absence — some workshop packs author no chargen prose) skips registration entirely. No `<genre-chargen>\n\n</genre-chargen>` empty wrapper risk.

4. **[VERIFIED] adjacent registration blocks untouched** — Diff shows `gp.extraction` (1558-1567), `gp.keeper_monologue` (1571-1580), `gp.town` (1583-1592) unchanged byte-for-byte. The parametrized regression-guard test `test_unaffected_stable_sections_still_carry_unconditionally` exercises this on neutral-turn fixtures (`opening_directive=None`, `turn_number=5`); all three cases pass per `61-11-tea-red` testing-runner output. If a future copy-paste edit accidentally added the predicate to one of those blocks, the test fails immediately with the section name in the parametrize id.

5. **[VERIFIED] cache-evidence test correctness** — The pre-existing `test_promoted_genre_prose_lands_in_cached_system_block` was correctly identified as needing update (it asserted all 4 ADR-112 sections in `system_blocks[0]`; 3 remain after demotion). Dev updated the loop to 3 markers AND added an absence-of-chargen guard on the neutral-turn fixture, AND added a sibling test `test_demoted_genre_chargen_lands_in_user_message_on_opening_turn` for the predicate-true case. The two tests together pin the demotion through the SDK request layer — different assembly path from the `compose_split`-driven tests in `test_61_11_scene_gated_genre_chargen.py`. Verify-phase reuse subagent's high-confidence "do-not-consolidate" finding confirms the split is intentional.

6. **[LOW] dash vs underscore marker style** — New tests use `STORY-57-3-EXTRACTION-FIXTURE` (dashes); pre-existing `test_cache_ttl_prefix_and_otel.py` uses `STORY_57_3_EXTRACTION` (underscores). Cosmetic. Per verify-phase quality subagent (low confidence). Not blocking; not worth a fixup commit.

7. **[SEC] no security regression — clean** — Per reviewer-security subagent (4 rules checked, 0 violations) and confirmed by my own audit: (a) no new path for player content into cached system prefix (demotion moves OUT of the cache root); (b) no injection surface on `opening_directive` (server-rendered from `openings.yaml` + chargen state, set exclusively at `websocket_session_handler.py:346`, no WebSocket handler writes from player input); (c) prose relocated from cached system prefix to user_message is a REDUCTION in attack surface (operator-authored YAML now in less-sensitive bucket). The [SEC] tag here records the subagent's clean verdict explicitly per gate requirements — no findings to confirm or dismiss.

### Devil's Advocate

Trying to find what's broken — minimum 200 words.

**Scenario 1: `opening_directive` set but `_run_opening_turn_narration` is never called.** Could happen if `_populate_opening_directive_on_chargen_complete` succeeds but the opening-turn dispatch is gated out by some pre-condition (the deferral gate at `_should_fire_opening_narration` exists per the same file). Then `sd.opening_directive` sits populated forever. But — as I verified in Observation 1 — only `_run_opening_turn_narration` propagates it into TurnContext. Player-action turns ignore `sd.opening_directive` entirely. So even if it sits stale, the gate inside `orchestrator.py:1608` is reading `context.opening_directive` (the TurnContext field), which is always `None` on player-action turns regardless of session state. The chargen prose stays absent. **No bug.**

**Scenario 2: a future Dev refactors `_handle_player_action` to also pass `opening_directive=sd.opening_directive`.** Then stale `sd.opening_directive` would propagate, and chargen prose would re-leak on the first player-action turn (until 5371's clear fires). The regression-guard test `test_genre_chargen_absent_from_prompt_on_neutral_turn` uses `opening_directive=None` directly in its TurnContext fixture, so it doesn't catch this case — it doesn't model the `_build_turn_context` propagation path. **Real risk**, but mitigation lives elsewhere: the consume-once contract at `websocket_session_handler.py:5371` is the authoritative invariant; any change to propagation must respect it. The comment at 5367-5371 ("Rust uses `opening_directive.take()`") makes the invariant explicit. Acceptable.

**Scenario 3: empty `gp.chargen` registration risk.** If a genre pack has `Prompts(chargen="")` (empty string, not None), the outer guard `if gp.chargen and context.opening_directive is not None` short-circuits on falsy chargen (empty string is falsy in Python). Section not registered. Zero-byte leak preserved. **No bug.**

**Scenario 4: an attacker submits player input that contains literal text matching `_populate_opening_directive_on_chargen_complete`'s output format.** They could potentially inject a string that looks like an opening directive. But there's no path for player input to flow into `sd.opening_directive` — the only writer is the server-side resolver. Player input lands in the `action` argument to `_handle_player_action`, which threads into `build_narrator_prompt(action=..., context)` as the user message text. The chargen prose lands in user_message too post-demotion — could there be substring confusion? No: assertions in tests grep for the literal `<genre-chargen>` XML tag wrapping the prose, which the player cannot author into their input without the server first putting it there. **No bug.**

**Scenario 5: cache invalidation cascade.** Demotion changes the cached system prefix on the next narration turn for any session whose pre-fix cache included `genre_chargen`. The first turn after deploy will be a cache miss for every active session. This is a one-time cost (cache rebuilds), not an ongoing penalty. Memory `project_runaway_valley_block_2026_05_23` is the prior history here — cache misses are NOT the bug; cold-cache loops are. This is a single prefix change, not a per-turn re-computation. **Acceptable transient cost.**

Devil's advocate uncovered Scenario 2 as a real future-Dev risk but the invariant + comments at the consume site mitigate it. No findings to add.

### Deviation Audit

- **TEA test design — scope reduced from 3 sections to 1 (option A)** → ✓ ACCEPTED by Reviewer. Architect's predicate audit (context-story-61-11.md §Predicate Audit) demonstrated the runtime-signal gap conclusively; user confirmed option A via AskUserQuestion 2026-05-24. The deviation log carries all 6 fields, the forward-impact note correctly forecasts the two follow-up stories needed. No spec violation.

### Reviewer (audit) — Delivery Findings

(Added under `## Delivery Findings → ### Reviewer (audit)` below.)

### Verdict

**APPROVE.** Diff is bounded, well-documented, structurally robust (gate's failure surface limited to one propagation site), test coverage is proportional with intentional split between bucket-unit / registry-level wiring / SDK-shape paths, no rule violations, no security regression, no new failures. Two non-blocking improvements deferred to SM for the finish ceremony.

**Handoff:** To Architect (Leonard of Quirm) for spec-reconcile, then SM for finish.