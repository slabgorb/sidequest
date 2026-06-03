---
story_id: "77-2"
jira_key: ""
epic: "77"
workflow: "tdd"
---
# Story 77-2: Typed quest/stakes narrator tools — record_quest + set_stakes (ADR-102)

## Story Details
- **ID:** 77-2
- **Jira Key:** (no Jira integration)
- **Epic:** 77 — Quest & Stakes Substrate
- **Workflow:** tdd (Test-Driven Development)
- **Points:** 5
- **Priority:** p2
- **Stack Parent:** none (root story)

## Context

This story implements ADR-102 narrator tool contracts for quest and stakes management. The epic 77 is implementing ADR-137 (quest & stakes substrate), which consolidates quest/stakes creation to typed narrator tools (`record_quest` and `set_stakes`) with cardinality guardrails to prevent state bloat from unbounded narrator strings persisting to Postgres.

Story 77-1 (seed-at-creation) completed the character-creation path for quests via `quest_anchor` + `quest_log` + `active_stakes` seeding from PC drive. This story adds the narrator-controlled path: tools that allow the narrator to record new quests mid-game and set active stakes, both bounded by cardinality caps.

## Acceptance Criteria
1. Bound narrator-controlled state: reuse existing `_ACTIVE_STAKES_GUARDRAIL=1024` (narration_apply.py:5762) for `set_stakes`, and add a cardinality cap for `quest_log` / `quest_anchors` at the ADR-102 / Pydantic schema layer (unbounded narrator strings persist to Postgres → state-bloat vector)

## Technical Notes

### Key Files/Modules
- `sidequest-server/sidequest/game/state.py` — Character/world state models (Pydantic)
- `sidequest-server/sidequest/agents/narration_tools.py` — Narrator tool implementations
- `sidequest-server/sidequest/game/narration_apply.py` — Narration application logic
- `sidequest-server/tests/game/` — Game state tests

### Related ADRs
- ADR-102 — Tool-Use Protocol for Structured Output
- ADR-137 — Quest & Stakes Substrate (design, ADR-137 section: Implementation Stories)

### Dependencies
- Story 77-1 (seed-at-creation) is DONE; this story builds on that foundation
- No external blockers

## Sm Assessment

**Routing:** Single-repo story (sidequest-server), 5pt, tdd phased workflow. No Jira integration — claim skipped. Merge gate clear (no open PRs across any repo). Branch `feat/77-2-typed-quest-stakes-tools` created off `develop`.

**Scope for TEA (RED):** This is the narrator-controlled create/anchor lane for the campaign spine. Two typed tools per ADR-102 — `record_quest` (adds to `quest_log`/`quest_anchors`) and `set_stakes` (writes `active_stakes`). The load-bearing requirement is **cardinality guardrails**: reuse the existing `_ACTIVE_STAKES_GUARDRAIL=1024` cap for `set_stakes`, and add a new quest-count cap at the Pydantic/tool-schema layer so unbounded narrator strings can't bloat Postgres state. The oz playtest (2026-06-02) is the motivating failure — a full "go home" premise ran with empty `quest_log`/`quest_anchors`/`active_stakes`, the exact "convincing narration, zero mechanical backing" tell the OTEL principle exists to catch.

**OTEL reminder for the implementation phase:** per the project's Observability Principle, both tools must emit watcher events so the GM panel can verify the quest/stakes actually landed in state — this subsystem's whole reason for existing is to stop the spine from silently vanishing.

**Open question for TEA to resolve in test design:** the quest-count cap value isn't fixed by the AC (only that one must exist) — pin a concrete cardinality limit in the RED tests and flag it as a Design Deviation if it needs an ADR-137 cross-check.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — verified by `testing-runner`, RUN_ID `77-2-tea-red`, for the right reasons: missing `QuestEntry`/`record_quest`/`set_stakes` + unregistered-successor wiring failure; no test failed for a broken-test-code reason)

**Open design question resolved before writing tests:** the `quest_log` storage shape (the story's one explicit open question) was put to the Operator, who ruled **widen to `dict[str, QuestEntry]`** (not serialize-into-value). Tests encode that contract. See Design Deviations.

**Test Files:**
- `tests/game/test_quest_entry_widening.py` — `QuestEntry` model contract; `GameSnapshot.quest_log` / `WorldStatePatch.quest_log` widened to structured; legacy `dict[str,str]` save migrates on load (no fail-loud on pre-77-2 saves); legacy `quest_updates` apply coerces to QuestEntry; 77-1 `seed_quest_spine` writes a QuestEntry (coherence under the widened type).
- `tests/agents/tools/test_record_quest.py` — mint creates structured entry (AC-2); `quest.created` span attrs (AC-2); mint-with-anchor writes `quest_anchors` + `anchor_id` + `anchor_count` (AC-2, with the 77-3 sequencing note); update-mode changes status + fires `quest.updated` old/new (AC-3); update does NOT mint; cardinality cap refuses mint past 32 loudly + state doesn't grow (AC-1); update still allowed at cap; tight args validation (empty/oversized rejected); no-active-session fatal; routed `state_transition` reaches the GM-panel feed end-to-end via `watcher_hub` (AC-2 lie-detector, not a source grep); subprocess barrel-wiring proof for BOTH tools.
- `tests/agents/tools/test_set_stakes.py` — fresh set on empty (AC-4); `stakes.set` span `is_fresh=true`/`source`/`length` (AC-4); append keeps both + `is_fresh=false` (AC-4); default mode replaces; 1024-guardrail trim keeps fresh tail (AC-1, reuses `_ACTIVE_STAKES_GUARDRAIL`); tight args validation; no-active-session fatal.
- `tests/agents/test_sidecar_coverage_map.py` — added `quest_updates → record_quest` successor row + a wiring test asserting the successor is a registered tool (AC-5; currently RED until the barrel wires it).

**Tests Written:** 31 tests across 4 files covering all 5 AC clusters.

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #11 input validation at boundaries | `test_empty_title_rejected_by_args_model`, `test_empty_objective_rejected_by_args_model`, `test_oversized_objective_rejected_by_args_model`, `test_empty_stakes_rejected_by_args_model`, `test_oversized_stakes_input_rejected_by_args_model` | RED |
| #11 / No Silent Fallbacks | `test_mint_past_cardinality_cap_is_refused_loudly` (structured error, not silent skip) | RED |
| #2 mutable default arguments | `test_quest_entry_instances_do_not_share_anchor_state` | RED |
| #6 test quality (self-check) | all span asserts check exact attr values, not truthiness; round-trips reload via PG and assert concrete fields | n/a |
| CLAUDE.md Wiring (no source-text grep) | `test_record_quest_and_set_stakes_wired_via_barrel_subprocess`, `test_quest_created_routes_to_gm_panel_feed`, `test_quest_updates_successor_tool_is_registered` | RED |
| CLAUDE.md OTEL lie-detector | `test_mint_fires_quest_created_span`, `..._quest_updated`, `test_fresh_stakes_fires_stakes_set_span...`, routed-feed test | RED |

**Rules checked:** 4 of the applicable lang-review rules have explicit RED coverage (the rest — async pitfalls, resource leaks, deserialization, path handling — are not exercised by this pure-Pydantic/tool-handler change).
**Self-check:** 0 vacuous tests — every test asserts concrete values or exact span attributes; no `assert True` / truthy-only / always-None patterns.

**Handoff:** To Dev (Agent Smith) for GREEN. Read the blocking Delivery Finding first — the widened type touches five writers; implement all of them or the type goes incoherent on direct dict mutation (pydantic doesn't validate dict-item assignment). Both tools must emit OTEL via `Span.open(...)` through `spans_module.tracer()` (like `quest_seeded_at_creation_span`) or the routed-feed test stays red.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** Full server suite **9985 passed, 0 failed** (RUN_ID `77-2-dev-green-3`). Story targets (31 new tests) all green; ~10 existing tests updated to the structured contract.
**Branch:** `feat/77-2-typed-quest-stakes-tools` (pushed). No PR (SM owns PR creation).

**Files Changed (production):**
- `sidequest/game/session.py` — new `QuestEntry` model; `quest_log` widened to `dict[str, QuestEntry]` on `GameSnapshot` + `WorldStatePatch` with `mode="before"` migration validators (`_coerce_quest_log`); legacy `quest_updates` apply path coerces str→QuestEntry in place; `_ACTIVE_STAKES_GUARDRAIL` relocated here (canonical home).
- `sidequest/agents/tools/record_quest.py` (new) — mint/evolve tool, 32-quest cardinality cap (mint-only), tight args schema, `quest.created`/`quest.updated` spans, anchor written to `quest_anchors` + `QuestEntry.anchor_id`.
- `sidequest/agents/tools/set_stakes.py` (new) — set/append tool reusing the 1024 guardrail (trim keeps fresh tail), `stakes.set` span, `is_fresh` = empty→populated.
- `sidequest/agents/tools/__init__.py` — barrel imports both tools (registration wiring).
- `sidequest/telemetry/spans/state_patch.py` — `SPAN_QUEST_CREATED`/`SPAN_QUEST_UPDATED`/`SPAN_STAKES_SET` + `SPAN_ROUTES` entries + helper emitters.
- `sidequest/server/narration_apply.py` — live `quest_updates` writer + trope-handshake writer now write `QuestEntry`; re-exports `_ACTIVE_STAKES_GUARDRAIL` from session.
- `sidequest/game/quest_seed.py` — 77-1 seed writes a `QuestEntry`.
- `sidequest/game/world_materialization.py` — chapter-quest writer writes `QuestEntry`.
- `sidequest/game/commands.py` — `/quests` CLI reader reads `entry.status`.
- `sidequest/game/delta.py` — `_to_json` now serializes nested pydantic models (fixed a silent regression where `quest_log` changes were never detected).
- `sidequest/server/static/dashboard.html` — GM dashboard renders structured quest entries (tolerates legacy string).

**Self-review:** Tools wired via barrel + verified by subprocess test; OTEL spans routed to GM-panel feed (verified end-to-end). All ACs met. Cardinality cap + guardrail reuse enforce the bounded-state AC.

**Handoff:** To TEA (The Architect) for verify (simplify + quality-pass).

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (2 minor mismatches — neither blocks; both have a clean resolution path)
**Mismatches Found:** 2
**Structural gate:** PASS (AC coverage present in Dev Assessment, implementation complete, TEA + Dev deviation subsections well-formed).

AC-by-AC substance check (context-story-77-2.md §AC Context):
- **AC-1 (bounded state):** `set_stakes` reuses `_ACTIVE_STAKES_GUARDRAIL=1024` with fresh-tail trim ✓; `record_quest` caps `quest_log` minting at 32 with a loud `ToolResult.error` ✓. Partial gap on the `quest_anchors` half — see M1.
- **AC-2 (mint + quest.created + routed feed):** structured `QuestEntry` minted ✓; `quest.created` carries quest_id/title/source/anchor_count ✓; routed `state_transition` reaches `watcher_hub` ✓ (end-to-end test, not a grep).
- **AC-3 (update mode + quest.updated):** old/new status fired ✓; does not mint on update ✓.
- **AC-4 (set/append + stakes.set):** fresh set, append, and `is_fresh` establishment semantics ✓.
- **AC-5 (wiring):** barrel subprocess proof + coverage-map successor row ✓.

- **`quest_anchors` lacks an explicit cardinality cap** (Missing in code — Behavioral, Minor)
  - Spec: AC-1 names a cardinality cap on "`quest_log` / `quest_anchors`".
  - Code: only `quest_log` *minting* is capped (32). `record_quest` appends to `snapshot.quest_anchors` on both mint and update; the **update** path (`record_quest.py:152-155`) is uncapped, so repeated updates to one quest with distinct anchors could grow `quest_anchors` past any bound. In normal play anchors grow ~1:1 with capped mints, so the realistic bloat vector (mint) IS bounded — this is a pathological-edge gap, not the common case.
  - Recommendation: **D — Defer to 77-3.** ADR-137 + the story's Scope Boundaries explicitly defer promoting `quest_anchors` to a first-class `WorldStatePatch` field *and its real apply path* to 77-3; the anchor-list cap belongs with that promotion. The primary unbounded vector (minting) is already capped here, so deferring does not leave AC-1's intent (bound the Postgres bloat vector) unmet for the common case.

- **`record_quest` requires title+objective on the update path** (Different behavior — Behavioral, Minor)
  - Spec: ADR-137 §One-mechanism — "status-only updates become an update-mode of `record_quest`."
  - Code: `RecordQuestArgs.title`/`objective` are required (`min_length=1`), so a pure status update must resend them (`record_quest.py:149-150` overwrite title/objective every call).
  - Recommendation: **A — Accept (update spec).** The tighter schema is the more defensible ADR-102 binding: the narrator holds title/objective in state, the tool description steers it, and resending enriches legacy-migrated entries (whose title/objective are empty) rather than harming them. No code change; logged here for traceability. A future ergonomic improvement could make them optional-on-update, but it is not required by AC-3 (which only asserts status changes + `quest.updated`).

**Decision:** Proceed to review (TEA verify). Both mismatches are Minor with non-code resolutions (D defer / A accept); no hand-back to Dev. The bounded-state AC's load-bearing half (quest mint cap + stakes guardrail) is met; the deferred half (anchor-list cap) rides 77-3's anchor promotion.

## TEA Assessment (verify — simplify + quality-pass)

**Phase:** finish
**Status:** GREEN confirmed (full suite 9985 green at green-exit; verify regression slice 227 green after the simplify refactor — RUN_ID `77-2-tea-verify`).

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 11 changed files (focus on the 77-2 diff)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings | R1–R4 (high): status-only upsert idiom duplicated across 4 writers; R5 (med): generic span-emitter extraction |
| simplify-quality | clean | no findings |
| simplify-efficiency | 6 findings | E1–E3 (high): "redundant" `ctx.otel_span.set_attribute`; E4/E5 (med): payload echoes; E6 (low): `_json_default` docstring |

**Applied:** 1 fix — **R1–R4** (the four high-confidence duplication findings are one fix): extracted `upsert_quest_status(quest_log, quest_id, status)` in `session.py` and routed the 4 status-only writers (apply path, narration_apply ×2, world_materialization) through it. Removes the duplicated idiom and centralises the widened-type contract (never assign a bare `str` into `quest_log`). Committed `a9ae1ff`. Regression slice 227/227 green.

**Dismissed (high-confidence, but wrong):**
- **E1–E3** — efficiency flagged `ctx.otel_span.set_attribute("tool.quest.*"/"tool.stakes.*")` as redundant with the span helpers. **Not redundant:** those set `tool.<short>.*` on the *dispatch* span — the canonical lie-detector convention `apply_status`/`update_npc_disposition` follow (`tests/.../test_apply_status.py::test_otel_span_carries_status_attrs` asserts `tool.status.*` on the dispatch span). The helpers emit a *separate* routed semantic span (`quest.created`/`stakes.set`) for the state_transition feed. Different spans, different GM-panel consumers — removing the dispatch attrs would break the canonical convention. The agent lacked the `apply_status` test context.
- **R5** — generic `_emit_point_span`. Dismissed: the three new helpers deliberately mirror the *existing* `quest_seeded_at_creation_span` / `state_patch_hp_span` shape in the same module; a generic emitter would make the new ones inconsistent with the file's established per-helper convention. Consistency > DRY here.

**Flagged for review, not applied:**
- **E4** (med): `record_quest` ToolResult echoes title/objective/status — intentional confirmation feedback to the narrator model, not bloat.
- **E5** (med): `set_stakes` returns the full `active_stakes` — lets the narrator see the trimmed result; minor.
- **E6** (low): `delta._json_default` docstring could note it's only reached for nested models.

**Quality Checks:** ruff format + ruff check on all changed files — clean. (Note: a pre-existing, unrelated `UP037` ruff error at `political_state.py:62` exists on `develop`; not in this diff — logged as a Dev delivery finding.)

**Handoff:** To Reviewer (The Merovingian) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (test warning) + baseline notes | confirmed 1, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — domain covered manually (edge cases enumerated below) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — covered: delta `_to_json` bare-except confirmed (LOW) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — covered: RED tests assert concrete values; preflight test-warning confirmed |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — docstrings reviewed manually, accurate |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — covered: QuestEntry/migration-validator reviewed (SEC-3 overlaps) |
| 7 | reviewer-security | Yes | findings | 5 | confirmed 5 (2 downgraded H→M with rationale), dismissed 0, deferred (routed to 77-3/77-4) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — verify phase already ran full simplify fan-out (clean + 1 applied) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — lang-review rules enumerated manually below |

**All received:** Yes (2 enabled returned; 7 disabled via `workflow.reviewer_subagents`, domains covered manually)
**Total findings:** 6 confirmed (2 security downgraded H→M with rationale; 4 already documented as deferred/known), 0 dismissed, anchor-cap + legacy-lane bypasses routed to their owning stories (77-3 / 77-4)

## Reviewer Assessment

**Verdict:** APPROVED (with non-blocking findings; release gated on 77-4 — see below)

**Data flow traced:** narrator LLM → tool args (`RecordQuestArgs`/`SetStakesArgs`, validated at the args boundary: lengths 64/120/500/32/64 and 1024) → handler `repository.load()` → mutate `quest_log`/`quest_anchors`/`active_stakes` → `repository.save()` → OTEL semantic span (`quest.created`/`quest.updated`/`stakes.set`) routed via `SPAN_ROUTES` to the GM-panel `state_transition` feed. Safe: input is length/type-bounded at the Pydantic args boundary before any state write; no SQL string-building (Postgres via parameterized psycopg/Alembic); no eval/pickle/yaml.load.

**Pattern observed:** new WRITE tools mirror the canonical `update_npc_disposition`/`apply_status` shape (load→mutate→save→OTEL) — `agents/tools/record_quest.py:97`, `agents/tools/set_stakes.py:62`. The shared `upsert_quest_status` helper (`game/session.py:467`) centralizes the status-only-upsert idiom across the 4 legacy/status writers.

**Error handling:** both tools return `ToolResult.error("no active session", recoverable=False)` on null session (`record_quest.py:100`, `set_stakes.py:70`); cardinality cap returns a structured recoverable error, not a silent drop (`record_quest.py:109`). `_coerce_quest_log` (`session.py:450`) migrates only the known legacy `str` shape and passes other types through to pydantic to raise loudly — No-Silent-Fallbacks compliant.

### Rule Compliance (lang-review/python.md + server CLAUDE.md)

| Rule | Verdict | Evidence |
|------|---------|----------|
| #1 silent exception swallowing | 1 LOW | `delta._to_json` `except Exception: return ""` (`delta.py:144`) — pre-existing; my change only added the `default=` encoder. Confirmed LOW (SEC-5). |
| #2 mutable default arguments | PASS | `QuestEntry` defaults are immutable (`""`/`"active"`/`None`); no mutable defaults in args models or helpers. `test_quest_entry_instances_do_not_share_anchor_state` proves independence. |
| #3 type annotations at boundaries | PASS | All new handlers/args/helpers fully annotated; `_coerce_quest_log(value: object) -> object` typed. |
| #8 unsafe deserialization | PASS | No pickle/yaml.load/eval/shell. Migration uses pydantic `model_validate` (safe). |
| #11 input validation at boundaries | PASS (new lanes) / see SEC-3 | `RecordQuestArgs`/`SetStakesArgs` bound every field. QuestEntry *model* is intentionally permissive (TEA deviation) — SEC-3 below. |
| No Silent Fallbacks (CLAUDE.md) | PASS | Migration validator fails loud on non-str/non-dict legacy values; cardinality refusal is loud. |
| No Source-Text Wiring Tests | PASS | Wiring proven by subprocess barrel import + routed-feed `watcher_hub` assertion, not grep. |
| OTEL Observability Principle | PASS | Every state write emits a routed span; verified end-to-end to the GM-panel feed. |

### Observations

- `[VERIFIED]` set_stakes guardrail is a hard bound on the NEW lane — `set_stakes.py:78` trims `new_stakes[-1024:]`; args cap input at 1024 (`set_stakes.py:` SetStakesArgs). active_stakes can never exceed 1024 via this tool. Complies with AC-1.
- `[VERIFIED]` record_quest mint cardinality cap is loud and effective on the NEW lane — `record_quest.py:108` refuses mint at `len(quest_log) >= 32` with a structured error; `test_mint_past_cardinality_cap_is_refused_loudly` asserts state doesn't grow.
- `[VERIFIED]` migration is fail-loud for malformed legacy data — `_coerce_quest_log` (`session.py:459-464`) only coerces `str`→`QuestEntry(status=...)`; ints/None/lists pass through and pydantic raises. No silent absorption of unexpected shapes.
- `[VERIFIED]` OTEL routing reaches the GM panel — `state_patch.py` `SPAN_ROUTES[SPAN_QUEST_CREATED]` (component=quest_log) + `test_quest_created_routes_to_gm_panel_feed` drives the tool and asserts the `state_transition` event arrives at `watcher_hub`.
- `[SEC][MEDIUM]` Cardinality cap is a single-tool property, bypassable via the legacy `quest_updates` lane — `upsert_quest_status` (`session.py:467`) has no cap; reachable from `narration_apply.py:2899`, `session.py:1368` apply, `narration_apply.py:6030` handshake. **Downgraded H→M:** this is the documented interim state (story Scope Boundaries: both lanes co-active until 77-4) and is closed by design when 77-4 retires the legacy lane (record_quest then the only mint path → cap becomes system-wide). Routed to the 77-4 release-gate finding. Recommended 77-4 implementation: move the mint-cap guard into `upsert_quest_status`.
- `[SEC][MEDIUM]` active_stakes guardrail bypassable via `apply_world_patch /active_stakes` — `session.py` `_apply_world_patch_inner` assigns `patch.active_stakes` untrimmed; `WorldStatePatch.active_stakes` has no `max_length`; the narrator prompt (`agents/narrator_prompts/output_only.md`) still routes STAKES → apply_world_patch. **Downgraded H→M:** apply_world_patch is the *deprecated* escape hatch the narrator is told not to use, explicitly stripped of quest/stakes paths in 77-4. Closed by the same lockstep retirement. Routed to the 77-4 release-gate finding.
- `[SEC][MEDIUM]` `QuestEntry` model fields have no `max_length` (`session.py:443-446`); a legacy save with an oversized status value loads unbounded. **Assessment:** intentional permissive-model design (TEA deviation — bounds enforced at the args boundary). Strict model `max_length` would FAIL legacy-save loading (defeating the migration's purpose); a truncate-and-log in `_coerce_quest_log` is the No-Silent-Fallbacks-compliant alternative. Pre-77-2 `quest_log` values were short status strings by convention, so realistic risk is low. Non-blocking improvement (delivery finding).
- `[SEC][MEDIUM] = Architect M1` quest_anchors grows unbounded via the update path (`record_quest.py:154`) — independently confirmed by security. Already deferred to 77-3 (quest_anchors → first-class WorldStatePatch field + cap). Confirmed/deferred.
- `[PREFLIGHT][MEDIUM]` `tests/game/test_session.py::test_gamesnapshot_with_character_and_delta_roundtrip` (not in diff) now emits a pydantic serialization warning: it assigns a bare `str` into `quest_log` via `__setitem__`, bypassing the `mode="before"` validator. Production writers are all disciplined (write `QuestEntry`); this is a stale test that should assign a `QuestEntry` / use `upsert_quest_status`. Test hygiene, non-blocking. (Reflects the pydantic-universal property that dict `__setitem__` skips field validation — not unique to quest_log.)
- `[SEC][LOW]` `delta._to_json` swallows serialization errors silently (`delta.py:144`) — pre-existing bare-except; add a `logger.warning` before `return ""`. Already logged as a Dev delivery finding.

### Devil's Advocate

Suppose I want to break this. **Attack 1 — bloat the campaign spine.** I can't via `record_quest` (mint capped at 32, args length-bounded), and I can't via `set_stakes` (1024 trim). But I *can* route through the legacy `quest_updates` extraction or the deprecated `apply_world_patch /active_stakes` — both uncapped and both still wired into the narrator prompt. So the bound the story advertises is, today, theater for a determined/misbehaving narrator. The only thing saving it is the **documented release gate**: 77-2 must not ship without 77-4, which deletes both bypass lanes. If an operator ships 77-2 alone, the bloat AC is unmet. This is why the 77-4 dependency must be loud and release-blocking — and it now is (see delivery findings). **Attack 2 — poison the migration.** A hand-edited legacy save with a 5 MB `quest_log["x"]` string loads into `QuestEntry.status` unbounded (no model cap). It doesn't crash, but it bloats the prompt. Mitigated by: pre-77-2 values were short by convention, and saves are operator-controlled, not attacker-controlled. **Attack 3 — confuse a future dev.** `quest_log[k] = "string"` compiles and runs, only warning at serialization — the test_session.py warning proves this trap is live. The `upsert_quest_status` helper mitigates it for the disciplined path, but the type system doesn't enforce it (pydantic dict-field limitation). **Attack 4 — lost update (73-3).** The tools `load()/save()` a copy rather than mutating `ctx.snapshot`; IF the end-of-turn `room.save()` writes a different canonical object, the tool's write could be clobbered. This matches the canonical `update_npc_disposition`/`apply_status` pattern (tested, shipped), so it's not 77-2-specific — but it's worth confirming in a live multi-tool turn (the new OTEL spans are the detector). Captured as a non-blocking delivery finding. None of these is a defect *in the story's code*; they are interim-lane and pre-existing-pattern concerns, all routed to owners.

**Handoff:** To SM for finish-story. Release is gated on 77-4 landing in lockstep (see delivery findings) — the bounded-state AC is met on the new lanes but is bypassable until 77-4 retires the legacy lanes.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T23:24:47Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T22:21:12Z | 2026-06-03T22:22:50Z | 1m 38s |
| red | 2026-06-03T22:22:50Z | 2026-06-03T22:38:24Z | 15m 34s |
| green | 2026-06-03T22:38:24Z | 2026-06-03T23:01:22Z | 22m 58s |
| spec-check | 2026-06-03T23:01:22Z | 2026-06-03T23:03:28Z | 2m 6s |
| verify | 2026-06-03T23:03:28Z | 2026-06-03T23:12:42Z | 9m 14s |
| review | 2026-06-03T23:12:42Z | 2026-06-03T23:23:21Z | 10m 39s |
| spec-reconcile | 2026-06-03T23:23:21Z | 2026-06-03T23:24:47Z | 1m 26s |
| finish | 2026-06-03T23:24:47Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (blocking): The Operator's ruling to widen `quest_log` to `dict[str, QuestEntry]` expands this story's blast radius beyond the literal scope-boundary list. The widened type forces coherent changes to FIVE call sites that the RED tests now pin: (1) `GameSnapshot.quest_log` type + a load-time migration validator for legacy `dict[str,str]` saves; (2) `WorldStatePatch.quest_log` type; (3) the legacy `quest_updates` apply path (`session.py:1285-1286` `self.quest_log.update(...)`) must coerce str→QuestEntry; (4) the trope handshake writer (`narration_apply.py:6030` `snapshot.quest_log[key] = status_text`); (5) the 77-1 seed writer (`quest_seed.py:80` `snapshot.quest_log[_SEED_QUEST_ID] = f"Active: {source}"`). Affects `sidequest/game/session.py`, `sidequest/game/quest_seed.py`, `sidequest/server/narration_apply.py` (Dev must update all writers or the type goes incoherent on direct dict mutation — pydantic does not validate dict-item assignment). *Found by TEA during test design.*
- **Question** (non-blocking): ADR-137 §OTEL specifies `quest.created` carries `anchor_count` but does not define it. The RED test pins `anchor_count = 1 when an anchor is supplied on mint, else 0` (per-call anchors written, not total `len(quest_anchors)`). If the GM panel wants cumulative anchor count, revisit in 77-3 when `quest_anchors` is promoted to a `WorldStatePatch` field. Affects `sidequest/telemetry/spans/state_patch.py`. *Found by TEA during test design.*
- **Conflict** (non-blocking): 77-4 lockstep is real and unstarted. Until 77-4 retires the legacy `quest_updates` apply and the `apply_world_patch` quest/stakes paths, BOTH the new tools and the old lanes write quests/stakes — and now under a widened type. Do not ship 77-2 to production without 77-4 gated behind it (ADR-137 §Consequences). Affects sprint sequencing. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Pre-existing lint debt unrelated to 77-2 — `sidequest/game/political_state.py:62` trips ruff `UP037` (quoted forward-ref annotation `"PoliticalState | None"` under `from __future__ import annotations`). Present at HEAD on `develop`, not introduced here; I reverted ruff's auto-fix to keep this diff scoped. Affects `sidequest/game/political_state.py` (one-char fix: drop the quotes). *Found by Dev during implementation.*
- **Gap** (non-blocking): `delta.py::_to_json` silently returned `""` on any non-`model_dump` value that wasn't natively JSON-serializable — which is why widening `quest_log` to `QuestEntry` initially made the delta blind to quest changes (both before/after blanked to `""`). Fixed here with a `default=` encoder, but the bare `except Exception: return ""` remains a latent silent-fallback for other field types (against "No Silent Fallbacks"). Affects `sidequest/game/delta.py` (consider narrowing the except / logging). *Found by Dev during implementation.*

### Reviewer (code review)
- **Conflict** (BLOCKING-FOR-RELEASE): 77-2's bounded-state AC is enforced only on the NEW tools; both bounds are bypassable until **77-4** lands. (1) The cardinality cap (32) is bypassable via the legacy `quest_updates` lane — `upsert_quest_status` (`game/session.py:467`) has no cap and is reached from `narration_apply.py:2899`, `session.py` apply, and the trope handshake. (2) The 1024 `active_stakes` guardrail is bypassable via the still-prompt-wired `apply_world_patch /active_stakes` path (`_apply_world_patch_inner` assigns untrimmed; `WorldStatePatch.active_stakes` has no `max_length`; narrator prompt `agents/narrator_prompts/output_only.md` still routes STAKES there). 77-4 retires both lanes, making the cap/guardrail system-wide. **Do not ship 77-2 to production without 77-4 gated behind it** (corroborates the TEA 77-4-lockstep finding with concrete vectors). Affects `narration_apply.py`, `agents/tools/apply_world_patch.py`, `agents/narrator_prompts/output_only.md` (77-4 work). Recommended 77-4 impl: move the mint-cap guard into `upsert_quest_status`; strip `/active_stakes` from apply_world_patch + the narrator prompt. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `QuestEntry` model fields (`title`/`objective`/`status`) have no `max_length`; a hand-edited/legacy save with an oversized value loads unbounded via `_coerce_quest_log`. Bounds are enforced only at the args boundary (intentional TEA deviation). Adding strict model caps would break legacy-save loading; a truncate-and-log in `_coerce_quest_log` is the No-Silent-Fallbacks-compliant alternative if defense-in-depth is wanted. Affects `sidequest/game/session.py` (low realistic risk — pre-77-2 values were short status strings). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): stale test `tests/game/test_session.py::test_gamesnapshot_with_character_and_delta_roundtrip` assigns a bare `str` into `quest_log` via `__setitem__`, bypassing the `mode="before"` validator and emitting a pydantic serialization warning under the widened type. Update it to assign a `QuestEntry` (or use `upsert_quest_status`). Affects `tests/game/test_session.py` (test hygiene; production writers are all disciplined). *Found by Reviewer during code review.*
- **Question** (non-blocking): the new WRITE tools `load()/save()` a repository copy rather than mutating `ctx.snapshot` (matching the canonical `update_npc_disposition`/`apply_status` pattern). IF the end-of-turn `room.save()` writes a different canonical object (ADR-037 / 73-3 lost-update note), a mid-turn tool write could be clobbered. Not 77-2-specific (same pattern as all WRITE tools), but worth confirming in a live multi-tool turn — the new OTEL spans are the detector. Affects `agents/tools/record_quest.py`, `set_stakes.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **quest_log storage shape widened to dict[str, QuestEntry]**
  - Spec source: context-story-77-2.md, "Assumptions" + Technical Guardrails (open design question); ADR-137 §Decision 2
  - Spec text: "quest_log storage shape for a structured quest ... is the one open design question ... The next agent MUST confirm the chosen shape (serialize-into-value vs widen-the-type) with the design before committing — do not silently pick one."
  - Implementation: Resolved via Operator ruling (2026-06-03) — widen the type (option b), not serialize-into-value (option a, the 77-1 precedent). RED tests assert `QuestEntry(title, objective, status='active', anchor_id=None)` and `quest_log: dict[str, QuestEntry]` with a legacy-string migration validator.
  - Rationale: Clean structured reads for the 77-6 UI panel and `quest.updated` old/new status; avoids mixed value formats in one dict. Accepted the larger blast radius (see blocking Delivery Finding) deliberately.
  - Severity: major
  - Forward impact: 77-6 (UI renders structured QuestEntry), 77-4 (legacy lanes retire onto the typed tool under the widened type). Save-migration validator must remain until all pre-77-2 saves are gone.
- **Quest-log cardinality cap pinned at 32**
  - Spec source: sprint YAML AC; context-story-77-2.md AC-1
  - Spec text: "add a cardinality cap for quest_log / quest_anchors at the Pydantic schema layer" — value unspecified.
  - Implementation: `_QUEST_LOG_CARDINALITY_CAP = 32`. Enforced in the handler (mint refused past cap with a structured ToolResult error; updating an existing quest is always allowed). Per-call payload also bounded at the args schema (title ≤120, objective ≤500, status ≤32, anchor ≤64).
  - Rationale: 32 small entries (~16 KB) bounds the Postgres state-bloat vector without restricting a long campaign; the handler (not args_model) owns the count check because the args_model cannot see existing state. SOUL §Cost Scales with Drama: a quiet town walk cannot mint past the cap.
  - Severity: minor
  - Forward impact: If ADR-137 later fixes a canonical cap, change one module constant. Flagged for cross-check.
- **stakes.set `is_fresh` defined as empty→populated (establishment)**
  - Spec source: context-story-77-2.md AC-4; ADR-137 §OTEL
  - Spec text: "is_fresh flag mirrors the existing active_stakes_appended semantics".
  - Implementation: `is_fresh = (active_stakes was empty before this call)` — TRUE on first establishment, FALSE when evolving already-present stakes.
  - Rationale: The oz failure was empty `active_stakes` for 13 turns; the most useful GM-panel lie-detector signal is "the stakes substrate went from empty to populated", which is exactly what `active_stakes_appended` marks for a fresh write. Pinned because the ADR left it to "mirror" an analogous flag.
  - Severity: minor
  - Forward impact: none.
- **set_stakes guardrail trim keeps the last 1024 chars (fresh tail), not handshake head+tail**
  - Spec source: context-story-77-2.md AC-1
  - Spec text: "trims when the resulting active_stakes exceeds it ... the trim preserves the fresh tail (mirror the handshake trim at narration_apply.py:5860)."
  - Implementation: trim to `active_stakes[-1024:]` (keep the freshly-written tail) rather than the handshake's head-budget + marker-tail splice.
  - Rationale: Same intent (preserve the load-bearing fresh content) but robust against the negative-head-budget edge the handshake splice hits when the fresh input approaches 1024 chars. Test asserts `len ≤ 1024 and endswith(fresh)`.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)
- **Relocated `_ACTIVE_STAKES_GUARDRAIL` from narration_apply.py to session.py**
  - Spec source: context-story-77-2.md AC-1 / Technical Guardrails
  - Spec text: "reuse the existing `_ACTIVE_STAKES_GUARDRAIL = 1024` (`narration_apply.py`)"
  - Implementation: Moved the constant's canonical definition to `sidequest/game/session.py` (pure-data module) and re-exported it from `narration_apply.py`. `set_stakes` imports it from `session`.
  - Rationale: `set_stakes` importing `narration_apply` formed an import cycle (`tools → narration_apply → session_helpers → orchestrator → tools`) that crashed all collection. The value (1024) and the public name `narration_apply._ACTIVE_STAKES_GUARDRAIL` are both preserved, so "reuse the existing constant" still holds — only its home moved.
  - Severity: minor
  - Forward impact: none — callers/tests importing it from `narration_apply` still work via the re-export.
- **`delta._to_json` gained a pydantic-aware `default=` encoder**
  - Spec source: implied by the widening (not an explicit AC); the tests `test_delta_quest_log_changed` / `test_gamesnapshot_..._delta_roundtrip` require change detection to keep working.
  - Spec text: (n/a — consequence of widening quest_log)
  - Implementation: Added `_json_default` so `json.dumps` serializes `QuestEntry` values nested in `quest_log`; otherwise the bare-`dict` branch raised and the `except` blanked the field, defeating delta detection.
  - Rationale: Without it, `quest_log` deltas were silently undetectable (a real regression, not just a test break).
  - Severity: minor
  - Forward impact: none.
- **GM dashboard renders structured quest entries**
  - Spec source: implied by the widening; not an explicit AC (player UI is 77-6).
  - Spec text: (n/a)
  - Implementation: `dashboard.html` quest-log block now renders `{title — objective — status}` for object values, tolerating the legacy string shape.
  - Rationale: Avoid `[object Object]` on the dev-facing GM dashboard after the value shape changed; not a half-wired regression. The player-facing quests panel remains 77-6.
  - Severity: minor
  - Forward impact: none.

### Reviewer (audit)
- **TEA: quest_log widened to dict[str, QuestEntry]** → ✓ ACCEPTED by Reviewer: Operator-ruled; tests + migration validator cover legacy-save loading; agrees with author reasoning.
- **TEA: cardinality cap pinned at 32** → ✓ ACCEPTED by Reviewer (new-lane scope): correctly enforced + tested on record_quest mint. NOTE: cap is a single-tool property, bypassable via the legacy quest_updates lane until 77-4 retires it (see SEC finding) — the value/placement on the new tool is sound.
- **TEA: stakes.set is_fresh = empty→populated** → ✓ ACCEPTED by Reviewer: meaningful lie-detector signal, matches the oz empty-stakes failure mode; tested both directions.
- **TEA: guardrail trim keeps last 1024 (fresh tail)** → ✓ ACCEPTED by Reviewer: robust against the negative-budget edge; `endswith(fresh)` asserted.
- **Dev: relocated _ACTIVE_STAKES_GUARDRAIL to session.py** → ✓ ACCEPTED by Reviewer: necessary import-cycle break; value + public name preserved via re-export; "reuse the existing constant" intent honored.
- **Dev: delta._to_json default= encoder** → ✓ ACCEPTED by Reviewer: fixes a real silent regression (quest_log deltas were undetectable). Residual: the bare `except` still swallows silently (SEC-5, LOW — add a warning log).
- **Dev: GM dashboard renders structured entries** → ✓ ACCEPTED by Reviewer: prevents `[object Object]`, tolerates legacy string; HTML-escaped via `esc()`.
- **No undocumented deviations found** beyond those already logged. The two security bypass vectors (cardinality via legacy lane, stakes via apply_world_patch) are not undocumented deviations — they are the explicit interim state the story scope assigns to the 77-4 lockstep partner.

### Architect (reconcile)

Reviewed all TEA (4) and Dev (3) deviation entries: every spec-source path exists (`sprint/context/context-story-77-2.md`, `sprint/context/context-epic-77.md`, `docs/adr/137-quest-stakes-substrate.md`), quoted spec text is accurate, implementation descriptions match the merged code, and all 6 fields are present. Reviewer stamped each ACCEPTED. Two decisions I made during spec-check were recorded in the Architect Assessment but not formalized as 6-field deviation entries — formalizing them here so the manifest is self-contained:

- **record_quest requires title+objective on the status-update path (ADR "status-only update" tightened to full-record)**
  - Spec source: docs/adr/137-quest-stakes-substrate.md, §One-mechanism consolidation
  - Spec text: "Retire the `quest_updates` extraction lane. `record_quest` supersedes it; status-only updates become an update-mode of `record_quest`."
  - Implementation: `RecordQuestArgs.title`/`objective` are required (`min_length=1`) on every call, so an update must resend title+objective (`record_quest.py` args model; update path overwrites all three fields). There is no status-only call shape.
  - Rationale: tighter ADR-102 boundary validation; the narrator holds title/objective in state, and resending enriches legacy-migrated entries (whose title/objective are empty `""`) rather than harming them. Resolution A (update spec) — accepted at spec-check; AC-3 only requires status change + `quest.updated`, which holds.
  - Severity: minor
  - Forward impact: none — if a status-only ergonomic shape is later wanted, make title/objective optional-on-update; not required by any sibling story.
- **quest_anchors cardinality cap deferred to 77-3 (AC-1's "/ quest_anchors" half)**
  - Spec source: context-story-77-2.md, §AC Context AC-1 ("a cardinality cap on `quest_log` / `quest_anchors`")
  - Spec text: "`record_quest` enforces a **cardinality cap** on `quest_log` / `quest_anchors` at the Pydantic schema layer."
  - Implementation: only `quest_log` minting is capped (32, `record_quest.py`). `quest_anchors` (a `list[str]` written directly on the loaded snapshot) has no length cap; the update path appends new anchors uncapped (`record_quest.py:154`).
  - Rationale: Resolution D (defer). The story's Scope Boundaries explicitly assign promoting `quest_anchors` to a first-class `WorldStatePatch` field + its real apply path to **77-3**; the anchor-list cap belongs with that promotion. The primary Postgres bloat vector (minting) is bounded here, so AC-1's intent holds for the common case. Independently confirmed by reviewer-security (SEC-4) and the TEA anchor-sequencing finding.
  - Severity: minor
  - Forward impact: 77-3 must add the `quest_anchors` cap when it promotes the field. Until then, repeated same-quest updates with distinct anchors can grow the list (low realistic risk).

**Interim-bypass note (not a deviation):** the cardinality cap and 1024 stakes guardrail being bypassable via the legacy `quest_updates` lane and the deprecated `apply_world_patch /active_stakes` path is **spec-conformant** — the story scope mandates both lanes stay co-active until the 77-4 lockstep partner retires them. It is therefore tracked as a BLOCKING-FOR-RELEASE delivery finding (Reviewer), not a deviation. The boss's takeaway: 77-2 must not reach production without 77-4.

**AC deferral check:** the sole sprint-YAML AC (bounded narrator-controlled state) is DONE on the new lanes — no ACs were formally deferred/descoped via the ac-completion table, so this step is a no-op. The "/ quest_anchors" sub-clause is the only partial, captured as the M1 deviation above.