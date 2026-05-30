---
story_id: "72-4"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 72-4: Route narrator-invented NPC names through culture-bound ADR-091 namegen

## Story Details
- **ID:** 72-4
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Context
See `sprint/context/context-story-72-4.md` for full business context and technical guardrails.

**Summary:** The narrator currently invents NPC names that bypass ADR-091's culture-bound name generator, producing names that may break genre/culture immersion. This story wires the narrator-invented mint branch (`narration_apply.py:1292-1301`) through `Pack.effective_cultures()` and `NameGenerator.generate_person()` so invented NPCs are phonetically genre/culture-true by construction.

**Load-bearing requirement:** The name generator, corpus loading, Markov chains, and stem-collision filters already exist and ship in every genre pack. This story is **wiring only** — no new name generator implementation.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-30T09:48:04Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-30T04:30:00Z | 2026-05-30T08:30:40Z | 4h |
| red | 2026-05-30T08:30:40Z | 2026-05-30T08:47:46Z | 17m 6s |
| green | 2026-05-30T08:47:46Z | 2026-05-30T09:31:47Z | 44m 1s |
| spec-check | 2026-05-30T09:31:47Z | 2026-05-30T09:33:17Z | 1m 30s |
| verify | 2026-05-30T09:33:17Z | 2026-05-30T09:37:30Z | 4m 13s |
| review | 2026-05-30T09:37:30Z | 2026-05-30T09:46:43Z | 9m 13s |
| spec-reconcile | 2026-05-30T09:46:43Z | 2026-05-30T09:48:04Z | 1m 21s |
| finish | 2026-05-30T09:48:04Z | - | - |

## Sm Assessment

**Story:** 72-4 — Route narrator-invented NPC names through culture-bound ADR-091 namegen (5pts, p2, TDD, sidequest-server).

**Why this is ready for RED:** Story context (`context-story-72-4.md`) is complete and unusually detailed — it pins the exact mint seam (`narration_apply.py:1292-1301`, the Step-3 "novel" branch), names the real reuse seams (`build_from_culture`, `NameGenerator.generate_person`, `has_stem_collision`, `Pack.effective_cultures`), and supplies 5 derivable ACs with edge cases. No design ambiguity blocks test-writing.

**Load-bearing framing for TEA (The Architect):** This is a **WIRING** story, not a generator rewrite — "Don't Reinvent — Wire Up What Exists." The single most important constraint: at least one test must drive the **real** `_apply_narration_result_to_snapshot` → `_apply_npc_mentions` production path and assert the provenance span fired (the mandatory wiring test per server rules), proving the route is reachable end-to-end — not merely that the generator is callable in isolation.

**Span discipline:** Server rule — behavioral/span assertions only, never source-text greps. New provenance span at the rerouted mint must record resolved culture name + source (`world`/`genre`), the narrator's bare name, the generated name, and the collision-reroll flag. Existing mint spans (`npc.referenced match_strategy="invented"`, `npc.auto_registered`) and the namegen-internal guards (`namegen.fail_loud`/`thin_corpus`/`stem_collision`) must keep firing.

**Critical regression guard:** Culture must resolve via `Pack.effective_cultures(world)`, NOT raw `pack.cultures` — that divergence was the session-894 0-NPCs-seeded bug. AC2 covers this.

**No Silent Fallbacks:** Unresolved culture / generation failure must fail loud (warning span + surfaced condition), never silently mint the raw string. TEA/Dev settle the specific recovery; the loudness is the invariant.

**Scope discipline:** Step-3 novel branch ONLY. Disposition (72-5), OCEAN/belief seeding (72-9), promotion preservation (72-2), identity drift (72-7), LRU cap (72-6), and the `ToolContext.name_generators` Phase-E dict are all explicitly out of scope.

**Decision:** Confirm — proceed to RED. Handing off to The Architect.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-pt TDD wiring story with behavioral + span assertions.

**Test Files:**
- `tests/server/test_npc_invented_namegen_routing.py` — 11 tests covering all 5 ACs + edge cases + backward-compat, driving both the mint seam (`_apply_npc_mentions`) and the real production path (`_apply_narration_result_to_snapshot`).

**Tests Written:** 11 tests covering 5 ACs.
**Status:** RED — 10 failing (TypeError on the not-yet-added `name_generator=` / `world=` kwargs, plus the asserted spans don't fire), 1 backward-compat guard passing (`test_no_name_generator_falls_back_to_raw_mint` — legacy raw mint, must stay green). Existing sibling suite `test_npc_pool_narration_apply.py` (13 tests) still green — no regression.

**AC → Test map:**
| AC | Test(s) | Status |
|----|---------|--------|
| AC1 generated-not-raw | `test_invented_branch_mints_generated_name_not_raw_string`, `test_wiring_full_apply_routes_invented_name_through_namegen` | failing |
| AC2 culture via effective_cultures (world vs genre) | `test_wiring_provenance_records_effective_culture_source` | failing |
| AC3 provenance span fired | `test_invented_branch_emits_provenance_span` | failing |
| AC4 loud on unresolved culture | `test_wiring_fails_loud_when_no_culture_bound` | failing |
| AC5 existing/player names respected + no-dup | `test_existing_npc_hit_is_not_regenerated`, `test_existing_pool_member_hit_is_not_regenerated`, `test_generated_name_colliding_with_existing_member_does_not_duplicate` | failing |
| collision reroll | `test_invented_branch_rerolls_on_stem_collision` | failing |
| existing spans preserved | `test_invented_branch_preserves_existing_invented_spans` | failing |
| backward-compat (legacy raw mint) | `test_no_name_generator_falls_back_to_raw_mint` | passing |

**Mandatory wiring test:** `test_wiring_full_apply_routes_invented_name_through_namegen` drives the REAL `_apply_narration_result_to_snapshot` → `_apply_npc_mentions` path with a real `space_opera` pack and asserts the provenance span fired — proving the route is reachable end-to-end, not merely callable (CLAUDE.md "Every Test Suite Needs a Wiring Test").

### Rule Coverage (python.md lang-review)

| Rule | Test(s) / Treatment | Status |
|------|---------------------|--------|
| #1 silent-exceptions / No Silent Fallbacks | `test_wiring_fails_loud_when_no_culture_bound` (loud span on unresolved culture; success span must NOT fire) | failing (RED) |
| #6 test-quality — meaningful assertions | every test asserts specific values (minted name, span attrs, `person_calls` counts); no `assert True`, no truthy-only checks | self-checked clean |
| #6 test-quality — mock target | `NameGenerator.generate_person` patched on the **class** (where the method lives) — robust to Dev's import site; effective_cultures patched on `GenrePack` class | correct target |
| #3 type-annotations | helpers + `_SeqNameGenerator` fully annotated | clean |
| No-source-text-wiring | all wiring proven via OTEL span emission + minted-state assertions, never `read_text()`/grep of source | compliant |

**Rules checked:** 4 of the 13 python.md checks are applicable to a test-only change (the rest target production `.py` Dev will write in GREEN — the gate re-runs against the diff then).
**Self-check:** 0 vacuous tests found (no `assert True`, no `let _`, no always-None `is_none()`; booleans asserted with explicit `is True/False`).

**Handoff:** To Dev (Agent Smith) for GREEN. See Delivery Findings for the threading map (caller adds `world=`, threads from `websocket_session_handler` `_apply_kwargs`; corpus dir = `pack.source_dir/"corpus"` + shared fallback) and the two new spans needing `SPAN_ROUTES` registration.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/telemetry/spans/npc.py` — added `SPAN_NPC_INVENTED_NAME_ROUTED` (`npc.invented_name_routed`) + `SPAN_NPC_INVENTED_NAME_UNROUTED` (`npc.invented_name_unrouted`), both with `SPAN_ROUTES` registration (component `npc_registry`, field `npc_pool`, `event_type=state_transition`) and `@contextmanager` helpers (`npc_invented_name_routed_span` / `npc_invented_name_unrouted_span`). Picked up by the existing `from .npc import *`.
- `sidequest/server/narration_apply.py` — (1) `_generate_invented_name` helper: draws from the culture-bound generator, rejects `has_stem_collision` + existing-store-name candidates, re-rolls (bounded 10), returns `(name, collision_reroll)`. (2) `_resolve_invented_naming_context` helper: resolves culture via `Pack.effective_cultures(world)`, iterates shuffled cultures, builds the first whose corpus succeeds (skips thin/missing-corpus cultures), returns `naming_unresolved=True` only when none build or no pack/culture. (3) `_apply_npc_mentions` gains `name_generator`/`culture_name`/`culture_source` (unit-injection contract) + `pack`/`world` (lazy production path); Step-3 novel branch routes the mint through namegen, emits the routed/unrouted provenance spans, and mints the generated/degraded name (downstream `npc.referenced(invented)` + `npc.auto_registered` now report the minted name). (4) caller `_apply_narration_result_to_snapshot` gains `world` param and threads `pack`+`world` into the seam.
- `sidequest/server/websocket_session_handler.py` — threads `world=sd.world_slug` into the shared `_apply_kwargs` (covers first-apply + reprompt re-apply).
- `tests/server/conftest.py`, `tests/server/test_apply_beat.py` — stubbed `effective_cultures`/`source_dir` on two synthetic mock packs (test-double sync; see Design Deviations).

**Tests:** 11/11 target GREEN (`test_npc_invented_namegen_routing.py`, verified ×3 — no shuffle flakiness); 13/13 sibling GREEN (`test_npc_pool_narration_apply.py`); 6/6 previously-broken apply-pipeline tests fixed. **Full-suite serial diff (branch vs base): zero net new failures** — the only delta is the 10 RED 72-4 tests flipping to GREEN. The 39 remaining full-suite failures are pre-existing environmental/content failures (reference_integration, forensics_routes, lore_rag, app, chargen, scene_listing, culture_context, audit_namegen_corpora, pack_validator) confirmed identical on base. Lint + format clean on all changed files.
**Branch:** feat/72-4-route-invented-npc-names-namegen (not yet pushed)

**Handoff:** To review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (minor deviations, all within the story context's explicit latitude)
**Mismatches Found:** None requiring action (3 logged deviations reviewed + 1 minor observation)

Verified each AC against the diff (not just the Dev Assessment):

- **AC1 generated-not-raw** — `_apply_npc_mentions` Step-3 routes the mint through `_generate_invented_name`; minted `NpcPoolMember.name` is the generator output. Confirmed by `test_invented_branch_mints_generated_name_not_raw_string` + the e2e wiring test. Aligned.
- **AC2 culture via effective_cultures(world)** — `_resolve_invented_naming_context` resolves at `narration_apply.py:1368` via `Pack.effective_cultures(world)`, NOT raw `pack.cultures` (the session-894 divergence guard). `culture_source` rides the provenance span. Aligned.
- **AC3 provenance span** — `npc.invented_name_routed` registered in `SPAN_ROUTES` (npc.py:193) with original/minted/culture/source/reroll attrs. Aligned; resolves the TEA route-registration finding.
- **AC4 loud-on-unresolved** — `npc.invented_name_unrouted` (severity=warning, npc.py:215) fires + deliberate degrade to raw. The story explicitly permits "a deliberate, span-recorded degrade"; Dev chose degrade-not-raise within that latitude. Aligned.
- **AC5 pre-existing respected + no-dup** — Steps 1/2 untouched; `_generate_invented_name` re-rolls against existing PC/Npc/pool names. Aligned.

**Reviewed deviations (Dev subsection):** all three (lazy-resolution-at-seam, iterate-until-buildable culture selection, mock-pack test-double sync) are within the story Assumptions' stated freedom ("built at the mint seam OR session-load"; "selection rule … is a small design choice"). No re-classification needed.

**Minor observation (no action):** `collision_reroll` is set True on *either* a stem collision or an existing-member name clash — broader than the spec's literal "re-roll fired on stem collision." This is an honest superset signal for the GM panel, not drift. Recommendation A (accept as-is).

**Scope check:** Changes confined to the Step-3 novel branch, two new spans, the caller's `world` thread, and two test doubles. No disposition (72-5), OCEAN/belief (72-9), promotion (72-2), identity-drift (72-7), LRU (72-6), or `ToolContext.name_generators` (Phase-E) files touched. Scope-clean.

**Decision:** Proceed to verify. No hand-back to Dev.

## TEA Assessment (verify)

**Phase:** finish (simplify + quality-pass)
**Changed code files (story 72-4 only):** `narration_apply.py`, `telemetry/spans/npc.py`, `websocket_session_handler.py`, `tests/server/conftest.py`, `tests/server/test_apply_beat.py`. (`npc_development.py` + `test_npc_development_pipeline.py` in the develop diff are develop-drift, not this story — excluded.)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | 1 medium (extract existing-names helper), 2 low (span factory, document collision loop) |
| simplify-quality | clean | — |
| simplify-efficiency | 5 findings | 1 high (hoist resolution), 3 medium (set build, enum, fixture stub), 1 low (span factory) |

**Applied:** 0 fixes.
**Flagged for Review / Noted (with dispositions):**

- **[efficiency, HIGH] Hoist lazy culture resolution out of the mint loop** — **REJECTED on merit.** Hoisting `_resolve_invented_naming_context` before the loop (when a pack is present) builds a Markov `NameGenerator` (corpus read + train, up to 100k-word corpora) on *every* apply — including the common case where the narrator cites only existing NPCs (Step-1/2 hits) or no NPCs at all. The lazy-on-first-novel-mint pattern is a deliberate efficiency decision (logged Dev deviation; SOUL "Cost Scales with Drama"). The per-mention guard it would remove is a single boolean compare. Applying this would be a real hot-path regression dressed as a simplification — not applied.
- **[efficiency med + reuse med] Extract `build_existing_actor_names_set(snapshot)` helper** — valid duplication observation, but the pattern pre-exists in `connect.py`/other handlers (not introduced by 72-4) and consolidating is a cross-file refactor outside this story's scope. Captured as a Delivery Finding for a future cleanup. Not applied.
- **[efficiency med] Replace `naming_resolved`/`naming_unresolved` booleans with an enum** — a function-local 3-state; introducing a module-level enum type for it is over-engineering for the contained scope. Current two-flag form is readable. Not applied.
- **[efficiency low + reuse low] Span-registration factory for the two new spans** — would diverge from the explicit per-span `SPAN_ROUTES[...] = SpanRoute(...)` convention every other NPC span in `npc.py` follows (the consistency simplify-quality explicitly praised). Consistency wins. Not applied.
- **[efficiency med] conftest `effective_cultures` stub repetition** — real, but already captured as a non-blocking Delivery Finding (shared `make_synthetic_pack()` helper); a test-infra refactor touching multiple fixtures, out of 72-4 scope. Not applied.
- **[reuse low] Document the collision-retry loop as a reference pattern** — observation only; no code action.

**Reverted:** 0.

**Overall:** simplify: reviewed — 0 fixes applied (1 high-confidence finding rejected on technical merit as an efficiency regression; remaining medium/low findings are out-of-scope refactors or consistency/style preferences, two already logged as Delivery Findings).

**Quality-pass:** lint clean + format clean on all changed files; 11/11 target tests GREEN, 13/13 sibling GREEN; full-suite serial diff vs base = zero net new failures (verified in green phase, re-confirmed below).

**Handoff:** To Reviewer (The Merovingian).

## Subagent Results

Subagent toggles (`workflow.reviewer_subagents`): only `preflight` + `security` enabled; the other 7 disabled. Disabled domains were self-assessed by the Reviewer (rule-by-rule against the python lang-review checklist + own diff read) and tagged in the assessment.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (mechanical) | 0 new smells; 24/24 story tests GREEN; ruff clean | N/A |
| 2 | reviewer-edge-hunter | No | Skipped — disabled | N/A | Disabled via settings — self-assessed (see Observations [EDGE]) |
| 3 | reviewer-silent-failure-hunter | No | Skipped — disabled | N/A | Disabled via settings — self-assessed (see Observations [SILENT]) |
| 4 | reviewer-test-analyzer | No | Skipped — disabled | N/A | Disabled via settings — self-assessed (see Observations [TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped — disabled | N/A | Disabled via settings — self-assessed (see Observations [DOC]) |
| 6 | reviewer-type-design | No | Skipped — disabled | N/A | Disabled via settings — self-assessed (see Observations [TYPE]) |
| 7 | reviewer-security | Yes | findings | 1 medium (CWE-22 path traversal) | confirmed 1 (downgraded to Medium, non-blocking) |
| 8 | reviewer-simplifier | No | Skipped — disabled | N/A | Disabled via settings — self-assessed + TEA verify simplify pass (see Observations [SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped — disabled | N/A | Disabled via settings — self-assessed exhaustively (see Rule Compliance [RULE]) |

**All received:** Yes (2 enabled subagents returned; 7 disabled rows pre-filled + self-assessed)
**Total findings:** 1 confirmed (Medium, non-blocking), 0 dismissed, 0 deferred

### Rule Compliance (python lang-review — 13 checks, enumerated over the diff)

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Silent exception swallowing | PASS | `_resolve_invented_naming_context` (narration_apply.py:1385-1394) catches **specific** `(FileNotFoundError, ValueError)`, logs `logger.warning` per miss, tries next culture, and surfaces all-fail as `naming_unresolved=True` → `npc.invented_name_unrouted` warning span. Fail-loud-and-degrade, not a swallow. Confirmed by reviewer-security (0 violations). |
| 2 | Mutable default arguments | PASS | New params all `None`/`False` defaults (narration_apply.py:1412-1416); no `[]`/`{}`/`set()` defaults. |
| 3 | Type annotation gaps at boundaries | PASS | `_generate_invented_name`, `_resolve_invented_naming_context`, the two span CMs, and all new `_apply_npc_mentions`/`_apply_narration_result_to_snapshot` params are fully annotated; `NameGenerator` under `TYPE_CHECKING`. |
| 4 | Logging coverage & correctness | PASS | Degrade paths use `logger.warning` (recoverable condition — correct level); success uses `logger.info`; lazy `%s` formatting throughout, no f-strings in log calls; no sensitive data. |
| 5 | Path handling | PASS (new code) | `pack.source_dir / "corpus"`, `.parent.parent / "corpus" / "shared"` use `pathlib`. See [SEC] for the pre-existing containment gap in the called `_resolve_corpus_file`. |
| 6 | Test quality | PASS | RED tests assert specific values (minted name, span attrs, `person_calls` counts); `generate_person` patched on the **class** (correct target); e2e `skipif` is legitimate content-gating; fixture stubs minimal + correct. |
| 7 | Resource leaks | PASS | No new `open()`/sockets/locks; corpus reads live in the pre-existing generator module. |
| 8 | Unsafe deserialization | PASS | No pickle/eval/exec/yaml.load(unsafe)/shell=True; confirmed by reviewer-security. |
| 9 | Async/await pitfalls | PASS | All new code is sync, on the sync apply path; no blocking-in-async, no missing await. |
| 10 | Import hygiene | PASS | New top-level import `from ...generator import build_from_culture, has_stem_collision` (no cycle: generator never imports server); `NameGenerator` under `TYPE_CHECKING`. The `from .npc import *` that exports the new span CMs is the pre-existing module convention, not introduced here. |
| 11 | Input validation at boundaries (CWE-22) | **FINDING (Medium)** | See [SEC] below — pre-existing traversal in `generator.py:_resolve_corpus_file`, newly reachable via this wiring. |
| 12 | Dependency hygiene | PASS | No dependency changes. |
| 13 | Fix-introduced regressions | PASS | Full-suite serial diff vs base = zero net new failures (only the 10 RED 72-4 tests flip GREEN); the green-phase mock-pack fixture syncs introduce no broad-catch/wrong-type regressions. |

### Observations (≥5)

- `[SEC]` **[MEDIUM] CWE-22 path traversal in `_resolve_corpus_file` — generator.py:251-263 (and the reject_files loop 336-345)** — joins YAML-supplied corpus filenames (`names_file`, `corpora[].corpus`, `reject_files`) to `corpus_dir`/`fallback_dirs` with no `resolve()` + containment check; a pack YAML with `names_file: ../../../etc/shadow` escapes the corpus tree. The vulnerable code is **pre-existing in `generator.py` and untouched by this story**, but 72-4's `_resolve_invented_naming_context` is the first **production narrator-path** caller of `build_from_culture` (previously only 2 CLIs + the never-landed tool wire), so the wiring broadens the surface. **CONFIRMED (not dismissed — matches rule #11), downgraded to Medium/non-blocking:** corpus filenames are operator-authored pack YAML loaded at boot (the established trust boundary throughout the codebase — same path the CLIs already use), not LLM/network/end-user input; PRs are human-reviewed; and the correct fix (resolve()+containment in the shared ADR-091 module + its reject_files loop, with tests) belongs in a dedicated hardening story, not bolted onto this wiring story. Captured as a Delivery Finding with a follow-up recommendation.
- `[SILENT]` **[VERIFIED] No silent fallbacks** — every degrade path is observable: per-culture build failure → `logger.warning`; all cultures fail → `logger.warning` + `naming_unresolved=True` → `npc.invented_name_unrouted` (severity=warning) span; unresolved at the seam → same span + `logger.warning`. Evidence: narration_apply.py:1387-1403, 1604-1622. Complies with SOUL/CLAUDE "No Silent Fallbacks."
- `[EDGE]` **[LOW] Re-roll exhaustion mints the last (colliding) candidate** — `_generate_invented_name` (narration_apply.py:1336-1342): if all 10 attempts trip stem-collision/existing-name, it returns the last generated candidate (which collided), potentially minting a stem-collision or duplicate name. Mitigants: bound=10 against a ≥200-word corpus makes 10 consecutive collisions astronomically unlikely; and the outcome is observable (`collision_reroll=True` on the routed span). Acceptable as the deliberate "keep the turn moving" degrade. Noted, non-blocking.
- `[EDGE]` **[VERIFIED] Multi-mint collision-set freshness** — for multiple novel mints in one call, `_generate_invented_name` rebuilds `existing` from live `snapshot.npc_pool` (narration_apply.py:1332), which includes members appended earlier in the same loop, so a second invented NPC can't duplicate the first. Evidence: append at :1632 precedes the next iteration's set build.
- `[TYPE]` **[VERIFIED] Resolution tuple is internally consistent** — `_resolve_invented_naming_context` returns generator+culture_name as both-set or both-None (narration_apply.py:1366/1370/1395/1403); the routing guard `name_generator is not None and culture_name is not None` (:1580) cannot half-fire. Booleans asserted with `is True/False` in tests.
- `[TEST]` **[VERIFIED] Mandatory wiring test present** — `test_wiring_full_apply_routes_invented_name_through_namegen` drives the real `_apply_narration_result_to_snapshot` → `_apply_npc_mentions` path on the real space_opera pack and asserts the provenance span fired (proven RED→GREEN in the serial diff). Satisfies CLAUDE.md "Every Test Suite Needs a Wiring Test." 11 tests cover all 5 ACs + collision/edge/backward-compat.
- `[DOC]` **[VERIFIED] Comments accurate, no staleness** — docstrings on both new helpers and the updated `_apply_npc_mentions` describe the lazy/dual-injection contract correctly; the `_INVENTED_NAME_MAX_ATTEMPTS` comment explains the bound; span docstrings document attrs. No misleading or stale comments in the diff.
- `[SIMPLE]` **[VERIFIED] No unnecessary complexity** — the TEA verify simplify pass (reuse/quality/efficiency) ran and applied 0 fixes; the one high-confidence "hoist resolution" finding was correctly rejected as an efficiency regression. The lazy guard is a standard memoization, not over-engineering. I concur.
- `[RULE]` **[VERIFIED] 12/13 python checks PASS, 1 finding** — see Rule Compliance table; only check #11 (CWE-22) yields a finding, handled above.

### Data Flow Trace

Narrator LLM output → `NarrationTurnResult.npcs_present[].name` (e.g. "Bob Hegemonic") → `_apply_narration_result_to_snapshot(..., pack=sd.genre_pack, world=sd.world_slug)` (websocket_session_handler.py:863-864) → `_apply_npc_mentions(pack, world)` → Step-3 novel branch → lazy `_resolve_invented_naming_context` → `pack.effective_cultures(world)` (operator YAML) → `build_from_culture(culture, corpus_dir=pack.source_dir/"corpus", fallback=content_root/corpus/shared)` → `generate_person()` → minted `NpcPoolMember.name`. **Safe at the narrator boundary:** `mention.name` is only logged/stored as data and replaced by the generated name — it is never used as a path, query, or command. **The single residual risk is the corpus *filename* (operator YAML, not narrator), addressed in [SEC].**

### Devil's Advocate

Assume this code is broken. The most dangerous claim in the diff is "the narrator can no longer mint a culture-breaking raw name" — but look harder. First, exhaustion: feed the route a deliberately thin-but-passing corpus that produces only stem-colliding tokens, and after 10 rejects the loop mints the colliding candidate anyway (narration_apply.py:1342), reintroducing the very "Frandrew Andrew" artifact the story exists to kill — and worse, if that candidate equals an existing pool member, AC5(c)'s no-duplicate invariant is silently violated while the routed span cheerfully reports success with `collision_reroll=True`. It is improbable, not impossible. Second, trust: the story's premise is that pack authors are trusted, but the project's own CLAUDE.md brags that "anyone can submit pack/world YAML via PR" — and this very diff is what first drags `build_from_culture`'s unguarded `corpus_dir / filename` join (generator.py:253) onto the live narrator turn. A `names_file: ../../../../etc/passwd` doesn't crash; it trains a Markov chain on the file and can leak fragments of its contents into NPC names shown to players — a low-bandwidth exfiltration channel that no test covers. Third, the world contract: `effective_cultures(world)` is trusted to return a real tuple, but a monkeypatched/legacy snapshot with `world=None` quietly resolves to *genre* cultures, and if those genre corpora are also thin, every invented NPC degrades to raw with a warning the GM may never read — the feature can be silently inert for an entire session while looking wired. Fourth, concurrency: `random.shuffle` mutates a local list (safe), but the per-turn `build_from_culture` does real file I/O on the apply hot path; under a fast multi-NPC turn this is repeated work the lazy guard only partially amortizes (one build per call, but a build every call that mints). None of these rise to Critical/High — the exhaustion case is astronomically unlikely on a healthy corpus and is observable; the traversal requires a malicious operator YAML behind a human-reviewed PR; the inert-feature case is loud (warning + span), just not loud enough to fail the turn. But each is a real edge the happy-path tests don't exercise, and the [SEC] follow-up should not be allowed to rot in the backlog.

## Reviewer Assessment

**Verdict:** APPROVED

**Summary:** Story 72-4 cleanly wires the narrator-invented (Step-3 novel) mint through the ADR-091 culture-bound generator. All 5 ACs are implemented and proven by 11 GREEN tests including the mandatory end-to-end wiring test; 12 of 13 python lang-review checks pass; the full-suite serial diff vs base shows zero net new failures. The three logged deviations are sound and within the story's stated latitude. The single confirmed finding ([SEC] CWE-22) is a **pre-existing** weakness in the shared `generator.py` module that this wiring newly reaches — downgraded to Medium/non-blocking and routed to a follow-up hardening story; it does not block this story.

**Dispatch tags:** `[SEC]` 1 confirmed (Medium, non-blocking) · `[SILENT]` verified clean · `[EDGE]` 1 low + 1 verified · `[TYPE]` verified · `[TEST]` verified · `[DOC]` verified · `[SIMPLE]` verified (TEA simplify pass, 0 fixes) · `[RULE]` 12/13 pass, 1 finding.

**Data flow traced:** narrator `mention.name` → namegen route → minted `NpcPoolMember.name` (safe — narrator string never used as path/query/command; replaced by generated name).
**Pattern observed:** lazy-on-first-novel-mint resolution + iterate-until-buildable culture selection at narration_apply.py:1572-1579 / 1382-1395 — sound, honors "Cost Scales with Drama."
**Error handling:** specific-exception fail-loud-and-degrade with warning logs + `npc.invented_name_unrouted` span at narration_apply.py:1385-1403 / 1604-1622.

**Blocking issues:** None (no Critical/High).
**Handoff:** To SM (Morpheus) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The two e2e tests drive the *full* real `_apply_narration_result_to_snapshot` with a real `space_opera` pack + synthetic snapshot. In RED they fail at the call (unknown `world=` kwarg) before reaching the namegen logic, so the heavy downstream branches (encounter lifecycle, course sidecar, etc.) have NOT yet been exercised with `pack=space_opera` on a synthetic snapshot. Precedent is strong (many tests drive full apply with a real pack), but Dev should confirm GREEN that no pack-gated branch trips on the minimal snapshot; if one does, narrow the snapshot fixture or guard the result rather than weakening the namegen assertions. *Found by TEA during test design.*
- **Question** (non-blocking): `_apply_npc_mentions` is the only production call site (`narration_apply.py:2599`, inside `_apply_narration_result_to_snapshot`). `_apply_narration_result_to_snapshot` already receives `pack: GenrePack | None` but NOT `world` — Dev must add a `world: str | None` param to it AND thread `world=sd.world_slug` from `websocket_session_handler.py:861-876` (the `_apply_kwargs` dict). The corpus dir for `build_from_culture` resolves as `pack.source_dir / "corpus"` + shared fallback `[content_root/corpus/shared]` (mirror `cli/namegen/namegen.py:543-544,604`); `pack.source_dir` is populated by the loader. Affects `sidequest/server/narration_apply.py` + `sidequest/server/websocket_session_handler.py`. *Found by TEA during test design.*
- **Improvement** (non-blocking): New spans `npc.invented_name_routed` and `npc.invented_name_unrouted` need `SPAN_ROUTES` registration in `sidequest/telemetry/spans/npc.py` (component `npc_registry`/`npc_pool`, `event_type=state_transition`) so the GM panel renders them — same pattern as the sibling NPC spans. The tests assert span *emission* (via the global `otel_capture` provider), not route registration, so a follow-up route-registration assertion (mirroring `test_namegen_wiring.py::test_*_span_routed_to_namegen_component`) is worth adding but is not gating 72-4. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): perseus_cloud's `Yulan` world-culture corpus is below the namegen floor — `english_industrial_first.txt` (62 words) and `english_industrial_family.txt` (25 words) are under `FAIL_BELOW_WORDS=200`, so `build_from_culture(Yulan)` raises and the route skips it. Spacer/Thari build fine, so invented-name routing works for perseus_cloud, but Yulan names can never be minted until the corpus is expanded. The yaml flags this as Jade's PROVISIONAL naming. Affects `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cultures/yulan.yaml` + `sidequest-content/corpus/shared/english_industrial_*.txt` (corpus expansion). Already surfaced by the pre-existing `test_audit_namegen_corpora` failures. *Found by Dev during implementation.*
- **Improvement** (non-blocking): The story-context's preferred long-term shape is session-load generator construction with caching (vs. the per-call `build_from_culture` this story does on the first novel mint). The lazy seam is built so a cached generator can drop in behind the existing `name_generator` injection point with no seam change — and that same construction could back-fill the `generate_name` tool's dormant `ToolContext.name_generators` dict (the Phase-E wire that never landed). A future story could unify both. Affects `sidequest/server/narration_apply.py` + `sidequest/agents/tools/tool_registry.py`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `synthetic_two_dial_pack` (and the bare `session_fixture` genre_pack) are `MagicMock`s that don't model the full `GenrePack` contract; each time production starts calling a new pack method the mocks need hand-stubbing (this story had to stub `effective_cultures`). A shared `make_synthetic_pack()` helper that returns a minimally-real pack (or a `MagicMock(spec=GenrePack)` with all resolution helpers pre-stubbed to safe defaults) would stop this recurring. Affects `tests/server/conftest.py`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): CWE-22 path traversal in `_resolve_corpus_file` (`sidequest/genre/names/generator.py:251-263`) and the `reject_files` loop (`:336-345`): YAML-supplied corpus filenames (`names_file`, `corpora[].corpus`, `reject_files`) are joined to `corpus_dir`/`fallback_dirs` with no `Path.resolve()` + containment check, so a pack YAML like `names_file: ../../../etc/shadow` escapes the corpus tree. **Pre-existing** in the shared ADR-091 generator (untouched by 72-4), but this story's `_resolve_invented_naming_context` is the first *production narrator-path* caller of `build_from_culture`, broadening the surface beyond the two CLIs. Recommend a dedicated hardening story: add `candidate.resolve()` + assert it is within `corpus_dir.resolve()`/fallback roots (raise a `CorpusPathError`/`FileNotFoundError` otherwise), covering both `_resolve_corpus_file` and the `reject_files` loop, with a traversal-attempt test. Affects `sidequest/genre/names/generator.py` (add containment guard). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Pinned the naming-context seam as a threaded generator, not pack+world, on `_apply_npc_mentions`**
  - Spec source: context-story-72-4.md, "The mint seam" / Assumptions
  - Spec text: "thread the resolved culture (or the built NameGenerator, or the pack + world) into `_apply_npc_mentions` from its caller ... Prefer threading the already-resolved generator/culture in rather than reaching for a global"
  - Implementation: Unit tests call `_apply_npc_mentions(..., name_generator: NameGenerator | None, culture_name: str | None, culture_source: str | None)`. Culture resolution via `Pack.effective_cultures(world)` + generator construction live in the **caller** (`_apply_narration_result_to_snapshot`), which the e2e tests drive with `pack=` + a new `world=` kwarg. The mint seam only generates/rerolls/mints/emits the provenance span.
  - Rationale: This is the story's stated PREFERRED design and is the only shape that lets the collision-reroll and generated-name-equals-existing-member edge cases be tested deterministically (a real corpus-backed generator cannot be forced to collide). Dev may instead thread `pack`+`world` into `_apply_npc_mentions`; if so, the seven unit tests need their kwargs adjusted and this deviation re-logged — but contract A is the documented preference.
  - Severity: minor
  - Forward impact: Dev's GREEN must match the `name_generator`/`culture_name`/`culture_source` kwarg shape or update the unit tests in lockstep.
- **Pinned concrete OTEL span names + attribute schema the story left to Dev**
  - Spec source: context-story-72-4.md, "OTEL" section + epic note "72-4: namegen-routed mint span"
  - Spec text: "Emit a span at the rerouted mint recording at minimum: resolved `culture` name + culture `source`, the narrator's original bare name, the generated name actually minted, and a boolean for whether a re-roll fired on stem collision."
  - Implementation: success span `npc.invented_name_routed` {`original_name`, `npc_name`(=generated/minted), `culture`, `culture_source`∈{world,genre}, `collision_reroll`:bool, `turn_number`}; loud span `npc.invented_name_unrouted` {`original_name`, `reason`, `world`, `severity`="warning", `turn_number`}. Asserted as strings (constants do not exist yet → clean RED collection).
  - Rationale: ACs require asserting span emission + attributes; a concrete contract is needed to write the tests. Names follow the `npc.*` convention and the OTEL `npc_name` reserved-attribute workaround used by sibling spans.
  - Severity: minor
  - Forward impact: Dev should implement these exact names/attrs (and register both in `SPAN_ROUTES`); a different choice means updating the span-name constants in the test file + re-logging.
- **AC4 loudness asserted; recovery (raise vs degrade) deliberately NOT asserted**
  - Spec source: context-story-72-4.md, "No Silent Fallbacks" / AC-4
  - Spec text: "A *deliberate, span-recorded* degrade is acceptable; a silent swallow is not. The TEA/Dev should pin down which ... the loudness, not the specific recovery, is the invariant."
  - Implementation: `test_wiring_fails_loud_when_no_culture_bound` asserts only that the warning span fired (+ that the success span did NOT). It does not assert raise-vs-mint-raw, leaving recovery to Dev.
  - Severity: minor
  - Forward impact: none — intentional under-specification per spec.

### Dev (implementation)
- **Lazy naming-context resolution inside the mint seam, not eager in the caller**
  - Spec source: context-story-72-4.md, Assumptions ("The generator may be built at the mint seam (per-call `build_from_culture`) or at session-load and threaded through"); TEA deviation "thread the resolved generator/culture in"
  - Spec text: "Construction cost is non-trivial (corpus read + Markov train), so session-load construction with caching is preferable, but either is acceptable so long as the corpus-health guards still fire and the route is reachable."
  - Implementation: `_apply_npc_mentions` accepts BOTH the pinned `name_generator`/`culture_name`/`culture_source` kwargs (unit-test direct-injection contract — unchanged) AND `pack`/`world`. The caller threads `pack`+`world`; the seam resolves the culture + builds the generator LAZILY on the first novel mint only (cached for the rest of the call). The unit tests still inject a pre-built generator directly; the e2e tests drive the pack+world path.
  - Rationale: Eagerly resolving in the caller (my first cut) called `pack.effective_cultures()` on *every* apply — wasteful on quiet turns (builds a Markov generator even when no NPC is invented) AND it broke 83 tests that pass a `MagicMock(spec=GenrePack)` whose `effective_cultures` returns an unpackable mock. Lazy resolution pays the cost only when a novel NPC is actually minted, and naturally avoids the mock breakage for the many apply-pipeline tests that mint no novel NPC. Honors "Cost Scales with Drama."
  - Severity: minor
  - Forward impact: A future session-load generator cache (story-context's preferred long-term shape) can replace the per-call `build_from_culture` behind the same `name_generator` injection point without touching the seam.
- **Iterate bound cultures, use the first that builds (skip thin/missing-corpus cultures) rather than `random.choice` of one**
  - Spec source: context-story-72-4.md, Assumptions ("If a world binds multiple cultures, the selection rule among them ... is a small design choice for the TEA/Dev to settle")
  - Spec text: "the wiring and provenance span are the load-bearing parts."
  - Implementation: `_resolve_invented_naming_context` shuffles the effective culture list and returns the first whose `build_from_culture` succeeds; a culture whose corpus is missing or below the 200-word floor (it raises `FileNotFoundError`/`ValueError` and already emitted `namegen.fail_loud`/`thin_corpus`) is skipped. Loud-degrade (`naming_unresolved`) fires only when NO bound culture builds.
  - Rationale: perseus_cloud's three world cultures include the provisional `Yulan` (its `english_industrial_*` corpora are 25/62 words — below the 200 floor → `build_from_culture` raises). A plain `random.choice` made the e2e culture-source test flaky (~⅓ of runs picked Yulan and degraded to unrouted when the test expects a routed span). Iterate-until-buildable makes the route robust to one thin culture and the test deterministic — Spacer/Thari always build. The Yulan corpus gap is a content issue already caught by `test_audit_namegen_corpora` (pre-existing failure), out of scope for 72-4.
  - Severity: minor
  - Forward impact: When Jade finalizes Yulan's corpus (the yaml flags it PROVISIONAL), no code change is needed — it simply joins the buildable set.
- **Test-double maintenance: stubbed `effective_cultures` on two synthetic mock packs**
  - Spec source: CLAUDE.md "Verify Wiring, Not Just Existence" / new production contract
  - Spec text: n/a (test-infrastructure sync)
  - Implementation: Added `pack.effective_cultures.return_value = ([], "genre")` + `pack.source_dir = None` to `synthetic_two_dial_pack` (`tests/server/conftest.py`) and the inline `MagicMock(spec=GenrePack)` in `tests/server/test_apply_beat.py`. These synthetic packs bind no cultures, so the route correctly fails loud and degrades to the raw narrator name — the minted-name assertions are unchanged.
  - Rationale: `_apply_narration_result_to_snapshot` now calls `pack.effective_cultures(world)`; the bare mocks returned an unpackable `MagicMock`. Production always passes a real `GenrePack` (proven by the e2e wiring tests on the real space_opera pack), so this is keeping test doubles in sync with the expanded contract, not masking a bug.
  - Severity: minor
  - Forward impact: Any future apply-pipeline test using a synthetic mock pack should stub `effective_cultures` the same way (or the shared fixture already does it).

### Reviewer (audit)

All six logged deviations (3 TEA, 3 Dev) reviewed against the story context and code:

- **TEA #1 — naming-context seam as threaded generator (`name_generator`/`culture_name`/`culture_source`)** → ✓ ACCEPTED: matches the story context's stated PREFERRED design; the implemented seam honors it and additionally accepts `pack`/`world` for the lazy production path. Sound.
- **TEA #2 — concrete OTEL span names + attribute schema (`npc.invented_name_routed` / `npc.invented_name_unrouted`)** → ✓ ACCEPTED: names follow the `npc.*` convention and the `npc_name` reserved-attribute workaround; both registered in `SPAN_ROUTES`. Verified in code (npc.py:193/215).
- **TEA #3 — AC4 asserts loudness, not raise-vs-degrade** → ✓ ACCEPTED: the story explicitly delegates the recovery choice; Dev chose span-recorded degrade, which is within latitude.
- **Dev #1 — lazy resolution at the seam, not eager in the caller** → ✓ ACCEPTED: within the story's "build at the mint seam OR session-load" latitude; the eager-first-cut regression (83 tests) and the wasteful-build concern both validate the lazy choice. Honors "Cost Scales with Drama." The simplify-efficiency "hoist out of loop" counter-finding was correctly rejected (would regress the hot path).
- **Dev #2 — iterate bound cultures, first that builds** → ✓ ACCEPTED: within "selection rule is a small design choice"; iterate-until-buildable is more robust than `random.choice` and makes the e2e deterministic. The Yulan thin-corpus content gap is correctly scoped out (caught by `test_audit_namegen_corpora`).
- **Dev #3 — stubbed `effective_cultures` on two synthetic mock packs** → ✓ ACCEPTED: legitimate test-double sync with the expanded production contract; production always passes a real `GenrePack` (proven by the e2e tests). Not masking a bug — the synthetic packs honestly bind no cultures, so the loud-degrade path is exercised.

**Undocumented deviations:** None found. The diff matches the logged deviations; no spec divergence slipped through. (The [SEC] CWE-22 is a pre-existing weakness in an unmodified file, not a spec deviation of this story — captured as a Delivery Finding, not a deviation.)

### Architect (reconcile)

Verified all six prior entries (3 TEA, 3 Dev): spec-source paths exist (`sprint/context/context-story-72-4.md`, `sidequest-server/CLAUDE.md`), quoted spec text is accurate, implementation descriptions match the merged code, and forward-impact references (72-5/72-9 backlog, the session-load cache, future synthetic-pack helper) are valid. All six are complete 6-field entries and Reviewer-stamped ACCEPTED. No AC deferrals occurred (all 5 ACs DONE), so the deferral-justification cross-check is a no-op.

One deviation TEA/Dev did not log explicitly:

- **`collision_reroll` provenance flag broadened from "stem collision" to "any re-roll" (stem collision OR existing-member name clash)**
  - Spec source: `sprint/context/context-story-72-4.md`, "OTEL" section (AC3 / the provenance-span contract)
  - Spec text: "a boolean for whether a re-roll fired on stem collision."
  - Implementation: `_generate_invented_name` (`sidequest/server/narration_apply.py:1334-1342`) sets `collision_reroll=True` when a candidate is rejected for *either* `has_stem_collision(candidate)` *or* `candidate.casefold() in existing` (an existing PC/Npc/pool-member name clash, the AC5(c) no-duplicate path). The literal spec mentions only the stem-collision trigger; the implemented flag is the superset "a re-roll fired (for any reason)." The routed span asserts `collision_reroll is True` only for the stem case (`test_invented_branch_rerolls_on_stem_collision`); the existing-member case does not assert the flag, so the broadening is unconstrained by tests but not contradicted by them.
  - Rationale: An honest GM-panel signal answers "did the generator have to re-roll?" — the cause (stem vs existing-name) is secondary and already distinguishable from the minted name vs the existing store. Collapsing both re-roll triggers into one boolean is simpler and more truthful than a stem-only flag that would read `False` on an existing-member re-roll that demonstrably happened.
  - Severity: trivial
  - Forward impact: None. No sibling story consumes `collision_reroll`. If a future story needs to distinguish the re-roll cause, add a `reroll_reason` attribute rather than overloading the boolean.

The deviation manifest is now complete and self-contained for audit.