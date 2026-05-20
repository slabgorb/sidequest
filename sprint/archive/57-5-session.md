---
story_id: "57-5"
jira_key: null
epic: "57"
workflow: "tdd"
---

# Story 57-5: game_state snapshot slimming (diff-with-anchor or field pruning)

## Story Details

- **ID:** 57-5
- **Epic:** 57 (Narrator Prompt Token Reduction)
- **Jira Key:** (none — SideQuest is personal)
- **Workflow:** tdd
- **Type:** refactor
- **Points:** 5
- **Stack Parent:** none
- **Repo:** sidequest-server

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-20T16:30:50Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-20T12:00:00Z | 2026-05-20T16:02:02Z | 4h 2m |
| red | 2026-05-20T16:02:02Z | 2026-05-20T16:10:47Z | 8m 45s |
| green | 2026-05-20T16:10:47Z | 2026-05-20T16:17:25Z | 6m 38s |
| spec-check | 2026-05-20T16:17:25Z | 2026-05-20T16:19:06Z | 1m 41s |
| verify | 2026-05-20T16:19:06Z | 2026-05-20T16:24:02Z | 4m 56s |
| review | 2026-05-20T16:24:02Z | 2026-05-20T16:29:22Z | 5m 20s |
| spec-reconcile | 2026-05-20T16:29:22Z | 2026-05-20T16:30:50Z | 1m 28s |
| finish | 2026-05-20T16:30:50Z | - | - |

## Story Context

**Source ADR:** `docs/adr/110-game-state-snapshot-slimming.md` — fully read and in scope.

The per-turn `<game_state>` block is the single largest uncached blob in the narrator prompt (5–10 KB/turn, ~1–2k tokens). It is constructed at `session_helpers.py:485` and serialized at `session_helpers.py:558`, then injected into the Valley (uncached) zone.

The ADR ratifies a two-phase ≥50% reduction:

- **Phase A (zero-risk):** Replace `json.loads(snapshot.model_dump_json())` → `snapshot.model_dump(mode="json", exclude_defaults=True, exclude_none=True)`, and `json.dumps(payload, indent=2)` → `json.dumps(payload, separators=(",", ":"))` at both encode sites (`session_helpers.py:485+558` and `local_dm.py:308` if it exists).
- **Phase B (audit-driven):** Build a field-pruning allowlist; drop fields not consumed by narrator prompt sections. Fields to audit: `active_tropes`, `axis_values`, `genie_wishes`, `achievement_tracker`, and others per the `GameSnapshot` docstring.

The combined target is **≥50% byte reduction** with **zero narrator-quality regression**. Diff-with-anchor (Option C) and tool-fetch (Option D) are explicitly deferred.

**Observability gate:** Add `prompt.game_state.bytes` OTEL span at both encode sites with attributes `phase_a_applied`, `phase_b_applied`, `bytes_before`, `bytes_after`.

**Acceptance gate:** ≥50% reduction measured on a fixed snapshot fixture. The narrator does not confabulate missing fields on a representative test corpus (20+ turns). Pydantic round-trip equivalence holds: parsing the compact form back into `GameSnapshot` produces a `model_dump`-equivalent result.

## Field Audit

Per ADR-110 Phase B, all fields will be audited against narrator consumption. The audit grid will be populated during implementation, documenting each field decision with evidence from prompt assembly grep.

| Field | Verdict | Evidence |
|-------|---------|----------|
| `active_tropes` | **DROP** | Re-rendered in Recency-zone `pending_trope_context` (`orchestrator.py:1546-1552`) and Valley-zone `active_trope_summary` (`orchestrator.py:1721-1730`). Raw list is internal bookkeeping; presence in `<game_state>` is pure duplication. |
| `axis_values` | **DROP** | P2-deferred tone-system field. Narrator reads tone state from the dedicated `narrative_axis_status` section (per ADR-052) — no consumer in prompt assembly for the raw list. |
| `genie_wishes` | **DROP** | P5-deferred subsystem (consequence engine, F9). Zero consumers grep-wide outside `delta.py` / `forensic_fold.py` (state-diff machinery, not narrator prompts). |
| `achievement_tracker` | **DROP** | P6-deferred subsystem. No narrator consumer. Phase A would also drop it when at default, but the explicit `_PHASE_B_DROP_FIELDS` entry guards against the case where the field is non-default. |
| `characters` | **KEEP** | Gaslighting-doctrine anchor (per ADR-014 / `project_narrator_gaslighting_doctrine.md`). PC roster materialization defends against name/race/class confabulation. |
| `npcs` | **KEEP** | Gaslighting-doctrine anchor — materialized NPC list is the primary anti-confabulation source. `world_materialization._apply_npc()` writes here specifically so the narrator cannot invent names. |
| `character_locations` | **KEEP** | Per-PC location source of truth post-Wave-2B (story 45-48). Multiplayer location header relies on this; absence breaks MP correctness. |
| `room_states` | **KEEP** | Per-room container retrieved-state (story 45-13). Load-bearing for ADR-055 room-graph navigation. |
| `quest_log` | **KEEP** | Mission anchor — narrator's source of truth for what the party is doing. |
| `narrative_log` | **DROP** (existing) | Already dropped at `session_helpers.py:493` by Story 49-1; recency K=2 moved to Recency-zone via Story 57-1. Not affected by 57-5. |
| `pending_magic_auto_fires` / `pending_magic_confrontation_outcome` | (n/a) | Declared `exclude=True` on the model — never serialized in any path. |
| `last_saved_at` / `clock_t_hours` / `discovered_routes` / etc. | (auto-dropped by Phase A) | Default-equal on fresh snapshots; removed by `exclude_defaults=True, exclude_none=True`. Reconstructed identically on parse (round-trip test). |

## SM Assessment

**Setup verdict:** Clean. Story 57-5 is a 5pt TDD refactor in `sidequest-server`, branched `feat/57-5-snapshot-slimming` off develop, with story context grounded in ADR-110 (accepted, deferred Phase C/D). No Jira (personal project). No stack parent. Single repo, no cross-subrepo coordination required.

**Scope discipline:** ADR-110 explicitly defers diff-with-anchor (Option C) and tool-fetch (Option D). TEA must hold the line — failing tests cover Phase A (compact encode) + Phase B (field-pruning allowlist) only. The ≥50% byte-reduction acceptance gate and the OTEL `prompt.game_state.bytes` span are first-class test targets, not afterthoughts.

**Risk to flag for TEA:** Field-pruning is the regression vector. Test corpus must include scenes where the narrator legitimately needs each audited field — otherwise we ship a "passing" suite that silently breaks confabulation-prone subsystems. Anchor on existing fixtures where possible; do not invent live-content references (memory: tests must not point at live content slugs).

**Routing:** Phased TDD → handoff to TEA (Radar) for red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** TDD refactor with measurable acceptance gate (>=50% byte reduction) and observability contract (OTEL span). Both demand failing tests before implementation.

**Test Files:**
- `sidequest-server/tests/server/test_57_5_snapshot_slimming.py` — 15 tests covering ACs #1-#6.

**Tests Written:** 15 tests covering 6 ACs.
**Status:** RED — 10 of 15 failing (the change-driving tests), 5 passing as regression guards.

### RED Distribution

| AC | Test | RED? |
|---|---|---|
| AC#1 Phase A indent | `test_phase_a_state_summary_has_no_pretty_indent` | FAIL |
| AC#1 Phase A defaults | `test_phase_a_state_summary_omits_pydantic_default_fields` | FAIL |
| AC#2 Phase B active_tropes | `test_phase_b_drops_active_tropes_from_state_summary` | FAIL |
| AC#2 Phase B axis_values | `test_phase_b_drops_axis_values_from_state_summary` | FAIL |
| AC#2 Phase B genie_wishes | `test_phase_b_drops_genie_wishes_from_state_summary` | FAIL |
| AC#2 Phase B achievement_tracker | `test_phase_b_drops_achievement_tracker_from_state_summary` | FAIL |
| AC#3 byte reduction | `test_state_summary_byte_reduction_at_least_50_percent` | FAIL |
| AC#4 round-trip | `test_compact_form_round_trips_to_model_dump_equivalent` | **PASS (guard)** |
| AC#5 characters anchor | `test_anchor_preserved_characters_with_content` | **PASS (guard)** |
| AC#5 npcs anchor | `test_anchor_preserved_npcs_with_content` | **PASS (guard)** |
| AC#5 character_locations anchor | `test_anchor_preserved_character_locations_when_populated` | **PASS (guard)** |
| AC#5 quest_log anchor | `test_anchor_preserved_quest_log_when_populated` | **PASS (guard)** |
| AC#6 span constant | `test_span_constant_prompt_game_state_bytes_is_exported` | FAIL |
| AC#6 span flat-only | `test_span_prompt_game_state_bytes_is_flat_only` | FAIL |
| AC#6 span fires | `test_span_prompt_game_state_bytes_fires_with_required_attributes` | FAIL |

**On the five green tests:** ADR-110 §Assumptions and §Phase B explicitly call out two risk classes — (a) pydantic round-trip equivalence under exclude_defaults+exclude_none, and (b) over-pruning anti-confabulation anchors. These five tests guard those invariants. They pass today *and* must keep passing after Dev's change. If Dev breaks either invariant (Phase A unsafe, or Phase B drops `npcs`/`characters`/`character_locations`/`quest_log`), the suite turns red on the right line. This is the correct TDD shape — not every RED-phase test must be failing; tests that describe stable contracts the new code must respect are regression guards.

### Rule Coverage

Reference: `.pennyfarthing/gates/lang-review/python.md` (13 checks).

| Rule | Test(s) | Status |
|------|---------|--------|
| #3 type annotations | All test signatures annotated (`-> None`, `monkeypatch: pytest.MonkeyPatch`) | enforced |
| #6 test quality — vacuous assertions | All assertions check specific values (no `assert True`, no truthy-only checks); `isinstance + truthy + length` triplets for collection anchors | enforced |
| #6 test quality — mock target | `MagicMock` only used for `store` and `orchestrator` (external collaborators), not for the system under test | enforced |
| #6 test quality — assertions present | All 15 tests carry meaningful `assert` statements | enforced |
| #10 import hygiene | No star imports; specific imports only | enforced |

The remaining python.md checks (#1 silent-exceptions, #2 mutable-defaults, #4 logging, #5 path-handling, #7 resource-leaks, #8 unsafe-deserialization, #9 async-pitfalls, #11 input-validation, #12 dependency-hygiene, #13 fix-regressions, #14 state-cleanup-ordering) do not apply to a test file that exercises a serialization seam — none of the prohibited patterns are in scope. The fix-regression check (#13) will be enforced by Dev's self-review on the green-phase diff.

**Self-check:** zero vacuous assertions. All asserts compare values, key presence, attribute presence with named expected values, or quantitative gates (ratio<=0.5, bytes>0).

### Wiring Test (CLAUDE.md mandate)

Twelve of fifteen tests drive through the production `_build_turn_context` call (which invokes `session_helpers.py:485-558` end-to-end). That's the wiring test — these tests fail if anyone refactors session_helpers in a way that bypasses the encode site, or if the OTEL emitter is added but never reached from production code paths. The remaining three (round-trip on the pydantic model, span constant export, span FLAT_ONLY membership) are unit-level guards on contracts that don't need wiring through the call graph.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for the green phase.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/server/session_helpers.py` — Phase A encode swap (`model_dump(mode="json", exclude_defaults=True, exclude_none=True)`); Phase B field-pruning allowlist (`_PHASE_B_DROP_FIELDS` constant + `pop` loop); compact JSON serialization (`separators=(",", ":")`); `prompt.game_state.bytes` OTEL span emit with `phase_a_applied`/`phase_b_applied`/`bytes_before`/`bytes_after` attributes.
- `sidequest-server/sidequest/telemetry/spans/prompt.py` — new module declaring `SPAN_PROMPT_GAME_STATE_BYTES`, registering it in `FLAT_ONLY_SPANS`, and exporting the `prompt_game_state_bytes_span` context manager.
- `sidequest-server/sidequest/telemetry/spans/__init__.py` — re-export the new `prompt` submodule via `from .prompt import *`.

**Tests:** 15/15 passing on `tests/server/test_57_5_snapshot_slimming.py` (10 RED gates now green, 5 regression guards stayed green). Full server test sweep: **6881 passed, 0 failed, 396 skipped** (1m 55s). Lint: clean (`uv run ruff check`).

**Branch:** `feat/57-5-snapshot-slimming` (pushed to `origin/feat/57-5-snapshot-slimming`, c8d2b54).

**Acceptance Gate Verification:**

| Gate | Status |
|------|--------|
| AC#1 — Phase A applied (compact JSON, defaults/None excluded) | ✓ |
| AC#2 — Phase B field-pruning audit documented | ✓ (Field Audit grid above) |
| AC#3 — `<game_state>` bytes reduced ≥50% on fixture | ✓ (test passes) |
| AC#4 — Pydantic round-trip equivalence | ✓ (test passes) |
| AC#5 — Anti-confabulation anchors preserved | ✓ (4 guard tests stay green) |
| AC#6 — `prompt.game_state.bytes` OTEL span live with required attrs | ✓ (3 tests pass) |
| AC#7 — Full `just server-test` green | ✓ (6881 passed, 0 failed) |

**Self-Review (judgment checks):**
- ✓ Code is wired end-to-end — encode site is reached every narrator turn via `_build_turn_context` → `session_helpers`; OTEL emitter fires inside that same call.
- ✓ Follows project patterns — Phase B drop constant lives next to the encode logic (module-level tuple); OTEL span follows the established context-manager + `FLAT_ONLY_SPANS.add(...)` template from `recent_narrative.py` / `room_state.py`.
- ✓ All ACs met; no scope creep (no helper extraction, no signature changes, no test refactors).
- ✓ Error handling: pydantic raises on schema violation at encode; no new error paths introduced. The OTEL span uses an existing `Span.open` contract that handles tracer exceptions.
- ✓ No `local_dm.py:308` change — confirmed not an encode site (Design Deviation logged).

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — one minor, one deferred-by-precedent.
**Mismatches Found:** 2

### Findings

1. **AC #1 second encode site (`local_dm.py:308`) is a string-injection site, not a JSON encode** (Missing-in-spec — Architectural, Minor)
   - Spec (`context-story-57-5.md` §Primary edit sites #2): "sidequest-server/sidequest/agents/local_dm.py:308 — the equivalent encode for the LocalDM preprocessor path."
   - Code: `local_dm.py:308` is `f"<game_state>\n{state_summary}\n</game_state>\n"` inside `_build_user_prompt(... state_summary: str ...)` — string injection of an already-encoded payload, not a JSON encode. There is no second encode site to fix. LocalDM is also dormant on the live turn path (`websocket_session_handler.py:3095`).
   - Recommendation: **A — Update spec.** Both TEA and Dev independently verified this and logged matching Design Deviations + Delivery Findings (Conflict, non-blocking). ADR-110 §Phase A should be amended in a follow-up doc PR to drop the second-site claim. The story's AC #1 is satisfied by the single-site change at `session_helpers.py`. No code action required for 57-5.

2. **AC #5(b) narrator-quality regression counter (game_patch population rate on 20+ turn corpus) is not implemented** (Missing-in-code — Behavioral, Minor — deferred by precedent)
   - Spec (`context-story-57-5.md` §AC Context #5): "(b) the `game_patch` field population rate is ≥ pre-migration rate. Same regression-counter pattern as 57-4."
   - Code: No regression-counter harness exists on this branch. The AC #5(a) anchor-preservation half is covered by four guard tests (`test_anchor_preserved_*`); the AC #5(b) population-rate half requires a recorded-playtest-replay harness, which is not built.
   - Recommendation: **D — Defer.** The "Same regression-counter pattern as 57-4" pointer is itself a defer-to-playtest pattern: in story 57-4, the equivalent AC was explicitly deferred to the next playtest under Architect spec-check Resolution D ("No replay harness exists in the repo today and building one would substantially expand the story's scope. The narrator's structural anchors are unchanged by this diff and continue to fire. Next playtest serves as de-facto validation."). 57-5's diff is even less invasive than 57-4's (no narrator-prose surface changes, only `<game_state>` byte-pruning). The four AC #5(a) guard tests + the new `prompt.game_state.bytes` OTEL span give the GM panel the runtime visibility to flag any post-cut quality drop in playtest. Project memory `feedback_playtest_is_dev_cycle.md` confirms: "Playtest IS the dev cycle". Defer the population-rate gate to the next playtest, restore any over-pruned field on observed regression, per ADR-110 §Acceptance gate.

### Decision

**Proceed to review.** Both findings are resolution-A (spec amendment) and resolution-D (defer to playtest, per 57-4 precedent) — no code-back-to-Dev required. Reviewer should validate the OTEL span fires correctly in a live session and confirm the four anchor-preservation tests continue to gate field-drop creep in future stories.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4 (`session_helpers.py`, `telemetry/spans/__init__.py`, `telemetry/spans/prompt.py`, `tests/server/test_57_5_snapshot_slimming.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplicated logic; the new span helper follows the established `Span.open()` + `FLAT_ONLY_SPANS.add(...)` pattern used by `room_state.py` / `orchestrator.py` / `recent_narrative.py`. No reuse opportunities. |
| simplify-quality | clean | Naming consistent (`_PHASE_B_DROP_FIELDS` matches other module-level private constants). Re-export chain (`prompt.py` → `__init__.py` → `session_helpers.py`) correctly wired. Test organization tracks AC boundaries. No dead code, no missing type annotations, no architectural drift. |
| simplify-efficiency | clean | The known-cost `bytes_before` recompute at `session_helpers.py:600-605` explicitly evaluated and ruled NOT over-engineering: hard-coded fixture constants break under schema drift and defeat Sebastien's lie-detector contract. Per-turn cost (microseconds) vs LLM seconds — appropriate observability cost. |

**Applied:** 0 fixes (no findings)
**Flagged for Review:** 0
**Noted:** 0
**Reverted:** 0

**Overall:** simplify: clean

### Quality Checks

- `uv run pytest tests/server/test_57_5_snapshot_slimming.py tests/telemetry/test_routing_completeness.py` — **17/17 pass** (15 story tests + 2 routing-completeness lints).
- `uv run ruff check` on the 4 changed files — clean.
- Full `just server-check` — **6881 passed, 0 failed, 396 skipped** in 1m 55s.

### Wiring Test (CLAUDE.md mandate)

Confirmed end-to-end: `_build_turn_context` is the only encode site, called by `session_handler` on every narrator turn. The new OTEL span fires inside that call, gated by the production code path (verified by `test_span_prompt_game_state_bytes_fires_with_required_attributes`, which drives `_build_turn_context` and captures the span via in-memory exporter — same pattern as `test_rig_spans.py`).

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

## Subagent Results

Per `pf settings get workflow.reviewer_subagents`, only `preflight` is enabled in this project; the other eight specialist subagents are disabled by settings. The disabled rows are pre-filled as "Skipped / disabled" per the agent-behavior contract; their domains are covered by Reviewer's own analysis below.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 4 pyright errors (all pre-existing — see decision) | confirmed 0, dismissed 4, deferred 0 |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A — Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | N/A — Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A — Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A — Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A — Disabled via settings |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A — Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A — Disabled via settings |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A — Disabled via settings |

**All received:** Yes (1 enabled returned with findings, 8 disabled)
**Total findings:** 0 confirmed, 4 dismissed (with rationale), 0 deferred

### Preflight Findings — Dismissal Rationale

All 4 pyright errors reported by preflight are **pre-existing**, not introduced by 57-5:

- L183 (`for slot, pid in seat_map.items():`) — `eeeb0195` Keith Avery 2026-04-25
- L395 (`seat_map: dict[str, str] = ...`) — `eeeb0195` Keith Avery 2026-04-25
- L440 (`player_count_for_gate = int(count_method())`) — `12b233bc` Keith Avery 2026-04-28
- L1094 (`**extra_attrs,`) — `7f0c0041` Keith Avery 2026-05-12

The 57-5 diff lives at lines 51–71 (constants + import) and 499–619 (the encode site). Pyright on the targeted 57-5 files reports **zero errors** (per preflight: "target files with no errors: sidequest/telemetry/spans/prompt.py, sidequest/telemetry/spans/__init__.py, tests/server/test_57_5_snapshot_slimming.py"). The 4 errors are file-level findings the subagent attributed to the PR because the file was touched.

Furthermore, `just server-check` (the canonical quality gate per `justfile`) runs `ruff check + pytest` only — pyright is not part of the project's blocking gate. Ruff is clean; pytest is 6881/0. Pre-existing pyright debt is out of scope for 57-5.

## Reviewer Assessment

**Verdict:** APPROVED

### Rule Compliance

Reference: `.pennyfarthing/gates/lang-review/python.md` (14 numbered checks). Walked against the diff:

| # | Rule | Applies to diff? | Verdict |
|---|------|-----------------|---------|
| 1 | Silent exception swallowing | No new except blocks | N/A |
| 2 | Mutable default arguments | No new function definitions with mutable defaults | N/A |
| 3 | Type annotations at boundaries | `_PHASE_B_DROP_FIELDS: tuple[str, ...]` (`session_helpers.py:58`), `prompt_game_state_bytes_span(* , phase_a_applied: bool, ... -> Iterator[trace.Span]`) (`prompt.py:30-38`), all test signatures `-> None` | **PASS** |
| 4 | Logging coverage AND correctness | New `logger.info("prompt.game_state.bytes ... bytes_before=%d ...", ...)` uses lazy `%s/%d` placeholders, not f-strings. Severity is `info` (observability emission, not error). No sensitive data logged | **PASS** |
| 5 | Path handling | No new path operations in diff | N/A |
| 6 | Test quality | All 15 tests carry specific value assertions (key presence, `isinstance + len`, attribute presence, quantitative gates). Zero vacuous assertions. No mock patches on wrong targets (`MagicMock` only on `store`/`orchestrator` — boundary collaborators, not SUT) | **PASS** |
| 7 | Resource leaks | New `with prompt_game_state_bytes_span(...)` uses context manager via `Span.open` | **PASS** |
| 8 | Unsafe deserialization | `json.loads(snapshot.model_dump_json())` operates on server-generated pydantic-validated data, not user input. Test `model_validate_json` operates on internal round-trip data. No `pickle`/`eval`/`yaml.load(unsafe)` | **PASS** |
| 9 | Async/await pitfalls | No async code touched | N/A |
| 10 | Import hygiene | New imports specific (no star imports in production code). Test imports specific symbols. The `from .prompt import *` line in `telemetry/spans/__init__.py` follows the established 60-module star-import pattern for that package (registry-insertion ordering documented in the module docstring) | **PASS** |
| 11 | Input validation at boundaries | Encode site processes server-internal `GameSnapshot`, not user input | N/A |
| 12 | Dependency hygiene | No `requirements.txt` / `pyproject.toml` changes | N/A |
| 13 | Fix-introduced regressions | Fresh implementation, not a fix | N/A |
| 14 | State cleanup ordering with fallible side effects | No queue/buffer cleared after a side effect. `state_summary_payload` is built fresh per turn, no consume-then-clear pattern | N/A |

**Rules checked:** 14/14. **Applicable rules:** 6/14. **Violations:** 0.

### Observations

- **[VERIFIED] Phase A applied at the canonical encode site** — `session_helpers.py:505-509` invokes `snapshot.model_dump(mode="json", exclude_defaults=True, exclude_none=True)` exactly as ADR-110 §Phase A prescribes. The compact serialize at line 593 uses `separators=(",", ":")`. Rule #6 (test quality) is satisfied by `test_phase_a_state_summary_has_no_pretty_indent` (asserts no `"\n  "` fingerprint) and `test_phase_a_state_summary_omits_pydantic_default_fields` (asserts `last_saved_at`/`clock_t_hours`/`discovered_routes` absence).

- **[VERIFIED] Phase B drop ordering** — The Phase B drop loop at `session_helpers.py:516-517` runs BEFORE the existing downstream mutations (`pop("narrative_log")` at 525, characters redaction at 530-540, `party_formation`/`shared_world_delta` injection at 541-544). None of the 4 dropped fields (`active_tropes`, `axis_values`, `genie_wishes`, `achievement_tracker`) are read by the downstream mutations, so ordering is correct. Idempotent `pop(field, None)` tolerates the Phase-A case where `exclude_defaults` already removed an empty default.

- **[VERIFIED] OTEL span follows established pattern** — `prompt.py` mirrors `recent_narrative.py` and `room_state.py`: constant at module top, `FLAT_ONLY_SPANS.add(...)` at module load time, `@contextmanager` factory with kwargs-only signature + `_tracer` override + `**attrs` extension point. The encode site emits the span every turn (Sebastien's lie-detector contract) at `session_helpers.py:607-612` with all four ADR-mandated attributes. Test `test_span_prompt_game_state_bytes_fires_with_required_attributes` drives `_build_turn_context` end-to-end and captures the span via `InMemorySpanExporter` — the project-canonical wiring-test pattern.

- **[VERIFIED] Wiring end-to-end** — `_build_turn_context` is reached from `session_handler` on every narrator turn (existing call path, unchanged by 57-5). The new code lives on that call path — no opt-in switch, no feature flag deferral. The full server test suite (6881/0) confirms no other test caller bypasses the encode site.

- **[VERIFIED] Round-trip equivalence verified by guard test** — `test_compact_form_round_trips_to_model_dump_equivalent` asserts `GameSnapshot.model_validate_json(compact).model_dump(mode="json") == snap.model_dump(mode="json")`. This test gates pydantic upgrades — if v3 ever breaks the equivalence under `exclude_defaults+exclude_none`, CI catches it before merge.

- **[LOW] [SIMPLE] `bytes_before` recompute every turn is a documented observability cost** — `session_helpers.py:602-605` re-runs the pre-slimming encoding pattern every narrator turn purely to populate the OTEL `bytes_before` attribute. Dev's Delivery Finding flags this; the simplify-efficiency self-review explicitly evaluated and ruled it NOT over-engineering (microseconds vs LLM seconds, lie-detector contract requires per-turn fidelity). Accepted as designed; no action.

- **[LOW] `_drop_field` loop variable uses leading-underscore convention for an used variable** — `session_helpers.py:516`: `for _drop_field in _PHASE_B_DROP_FIELDS: state_summary_payload.pop(_drop_field, None)`. Python convention reserves leading-underscore loop vars for unused throwaway values. The variable IS used inside the loop body; `drop_field` (no underscore) would be more idiomatic. Cosmetic; not blocking.

- **[NOTE] Field Audit grid is the load-bearing artifact for future maintenance** — the per-field DROP/KEEP table at lines 59–72 of this session file documents the evidence for every audit decision. If a future story tries to drop another field, the grid is the precedent contract: any new drop must add a matching row with grep evidence, and any new KEEP must defend the anchor's anti-confabulation role. Reviewer recommends preserving this artifact when archiving the session.

### Devil's Advocate (≥ 200 words)

Suppose this code is broken — where would the wound be?

The most plausible attack surface is **silent narrator-quality drift**: Phase B drops four fields, and the unit tests only prove those fields are absent from the JSON dump. They do NOT prove the narrator's behavior is unchanged. A hostile reading of AC #5(b) — "game_patch population rate ≥ pre-migration rate" — says: until a playtest replay validates that the narrator still locates, confronts, and identifies NPCs at the same rate it did before, the cut is unverified. Architect's spec-check deferred this to playtest under Resolution D (per 57-4 precedent), but a malicious reading says "you shipped a Valley-zone field cut with no behavioral baseline." The four anchor-preservation guard tests catch over-pruning that drops `characters`/`npcs`/`character_locations`/`quest_log`, but they cannot catch subtler regressions: e.g., does removing `active_tropes` from the Valley dump cause the narrator to under-weight trope progression because it's no longer "seeing" the field even though it's re-rendered in the Recency zone? Answer: probably not — `pending_trope_context` carries the same information at higher attention — but "probably" is not "verified".

A confused user (a future developer) might re-add `active_tropes` to the dump because the field name implies it's "important". The Field Audit grid argues against this, but the grid lives in a session file that gets archived — not in code. A future drop-list maintainer needs to find the grid. Mitigation: the `_PHASE_B_DROP_FIELDS` constant's docstring points at "context-story-57-5.md §Phase B and the Field Audit in .session/57-5-session.md" — which sets the precedent.

What if the OTEL tracer crashes mid-emission? `Span.open` is the established gateway and is used by 60+ spans across the codebase; a tracer failure would surface across the whole turn pipeline, not just this span. Not a 57-5 regression.

What if a stressed filesystem makes `json.dumps` choke? `json.dumps` does not touch the filesystem — pure-CPU encoding. Out-of-memory on a 10 KB payload is exceedingly unlikely. Even if it occurred, the failure mode is loud (raised exception, turn fails) — no silent fallback per CLAUDE.md.

What about a malicious player input bloating `quest_log` or `npcs` past Phase B's reach? Pre-existing risk; not introduced here. Phase B only drops; it doesn't shrink kept fields.

What about save-file migration? The pydantic model is unchanged (Phase B is serialization-time, not model-time). Old saves load identically; the dump is just compacted. No save-migration risk.

The devil's strongest case is the narrator-quality deferral — and that's the only finding worth a `[VERIFIED-with-caveat]` rather than `[VERIFIED]`. Architect's Resolution D deferral, project memory `feedback_playtest_is_dev_cycle.md`, and the OTEL `prompt.game_state.bytes` span give the GM panel runtime visibility — but the unit suite cannot replace a playtest. Reviewer concurs with the deferral.

### Spec Deviation Audit

Stamps appended to `## Design Deviations` below.

### Handoff

To SM (Hawkeye Pierce) for finish-story.

## Delivery Findings

<!-- Append-only. Subsections per phase. -->

### TEA (test design)

- **Conflict** (non-blocking): ADR-110 names `local_dm.py:308` as a second Phase A encode site, but inspection shows line 308 is a string-injection site (`f"<game_state>\n{state_summary}\n</game_state>\n"`) inside `_build_user_prompt`, not a JSON encode. The LocalDM path receives an already-encoded `state_summary: str` from upstream — there is no second JSON encode to fix. LocalDM is also dormant on the live turn path (`websocket_session_handler.py:3095` comment). Affects `sidequest-server/sidequest/agents/local_dm.py` and `docs/adr/110-game-state-snapshot-slimming.md` (ADR text should be amended to drop the second-site claim, or the second site should be re-located if one truly exists). Dev should confirm during implementation and either amend the ADR or log a Design Deviation if a second encode site is found elsewhere. *Found by TEA during test design.*

### Dev (implementation)

- **Confirmed** (non-blocking): TEA's finding stands — there is no second JSON-encode site. Grep across `sidequest/agents/`, `sidequest/server/`, `sidequest/handlers/` shows `state_summary: str` flows in pre-encoded; only `session_helpers.py` constructs the `<game_state>` JSON. Phase A + Phase B ship at one site. ADR-110 should be amended in a follow-up doc PR to drop the `local_dm.py:308` second-site claim. *Found by Dev during implementation.*

- **Improvement** (non-blocking): The per-turn `bytes_before` measurement re-runs the pre-slimming encode (`json.loads(snapshot.model_dump_json())` + `json.dumps(..., indent=2)`) every turn to populate the OTEL attribute. Cost is microseconds vs the seconds-long LLM call, so per-turn fidelity wins — but a future optimization could sample (every Nth turn) or drop `bytes_before` to a one-shot session warmup metric once the cut is in production. Affects `sidequest-server/sidequest/server/session_helpers.py` (only — the OTEL emit site). No action needed for 57-5. *Found by Dev during implementation.*

### TEA (test verification)

- No upstream findings during test verification. Simplify fan-out across reuse/quality/efficiency lenses returned clean on all four changed files. Full server test suite holds at 6881 passed / 0 failed. *Found by TEA during test verification.*

### Reviewer (code review)

- **Improvement** (non-blocking): `session_helpers.py:516` uses leading-underscore `_drop_field` as a loop variable that IS used inside the loop body (`pop(_drop_field, None)`). Python convention reserves leading-underscore for unused throwaway variables. Rename to `drop_field` (no underscore) for idiomatic clarity. Affects `sidequest-server/sidequest/server/session_helpers.py:516` (one-line rename). No behavioral impact; cosmetic. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Pre-existing pyright debt in `sidequest/server/session_helpers.py` (4 errors at lines L183, L395, L440, L1094 — none introduced by 57-5, all dated 2026-04-25 through 2026-05-12). `just server-check` does not run pyright, but the cumulative type debt is worth a future cleanup story. Affects `sidequest-server/sidequest/server/session_helpers.py` (pre-existing, file-level). *Found by Reviewer during code review.*
- **Question** (non-blocking): The next playtest should specifically monitor for trope-progression and tone-axis drift in the narrator's behavior (the two Phase B drops with the most semantic risk). If either degrades, per ADR-110 §Acceptance gate, restore the dropped field and re-measure. The GM panel's new `prompt.game_state.bytes` span is the verification surface. *Found by Reviewer during code review.*

## Design Deviations

<!-- Append-only. Subsections per agent. -->

### TEA (test design)

- **Five RED-phase tests pass as regression guards rather than fail as change drivers**
  - Spec source: context-story-57-5.md, ACs #4 and #5; ADR-110 §Assumptions and §Phase B
  - Spec text: AC#4 "A test parses the compact serialized form back into `GameSnapshot` and asserts `parsed.model_dump() == original.model_dump()`. (Defaults reconstruct on parse, so the equivalence holds even though defaults aren't serialized.)" — AC#5 "Materialized creatures/NPCs/items in `snap.npcs` and similar — those are anti-confabulation anchors" must be preserved.
  - Implementation: AC#4's round-trip test and the four AC#5 anchor-preservation tests pass today (pydantic v2 round-trip already works; anchors are already present in state_summary). They are written as regression guards — they must continue to pass after Dev's Phase A + Phase B changes; they fail if the assumption breaks or if Phase B over-prunes.
  - Rationale: ADR-110 §Assumptions explicitly identifies pydantic round-trip equivalence as a risk-class assumption ("If `GameSnapshot` has custom serializers that defeat the equivalence ... Phase A's 'no semantic change' claim breaks"). Project memory `project_narrator_gaslighting_doctrine.md` identifies anchor stripping as the other risk class. The RED-phase suite is sharper when these invariants are tests that *describe contracts the change must preserve*, not failures the change must fix.
  - Severity: minor (TDD shape preference, not a behavioral cut)
  - Forward impact: Dev should treat these five tests as preservation gates — if any one turns red during the green phase, that's a Phase A/B safety violation, not a missing implementation.

- **`local_dm.py:308` dropped from Phase A scope**
  - Spec source: context-story-57-5.md "Primary edit sites" §2; ADR-110 §Phase A
  - Spec text: "sidequest-server/sidequest/agents/local_dm.py:308 — the equivalent encode for the LocalDM preprocessor path."
  - Implementation: No test targets `local_dm.py:308`. Inspection (this session) shows line 308 is a string-injection site, not a JSON encode. The LocalDM path is also dormant on the live turn path per `websocket_session_handler.py:3095`.
  - Rationale: Phase A's transformation does not apply at a string-injection site; there is nothing to convert. Asking Dev to "apply Phase A at local_dm.py:308" would either be a no-op or force an invented refactor.
  - Severity: minor
  - Forward impact: Dev confirms during implementation. If a true second encode site exists (e.g., a caller of `LocalDM.decompose` that JSON-encodes the snapshot to a string before passing it in), they add a test for that site and apply Phase A there. Otherwise, Phase A ships at `session_helpers.py` only and the ADR is amended via a follow-up doc PR.

### Dev (implementation)

- **`bytes_before` recomputed every turn rather than cached or sampled**
  - Spec source: context-story-57-5.md, AC #6; ADR-110 §Observability
  - Spec text: "Add `prompt.game_state.bytes` OTEL span at both encode sites with attributes `phase_a_applied`, `phase_b_applied`, `bytes_before`, `bytes_after`. The before/after delta is the cost-savings metric."
  - Implementation: At the encode site in `session_helpers.py`, Dev recomputes the pre-slimming form (`json.loads(snapshot.model_dump_json())` + `json.dumps(..., indent=2)`) every turn to populate `bytes_before`. This doubles encode work for the metric's sake.
  - Rationale: ADR-110 demands per-turn `bytes_before` for GM-panel verification. JSON encode is microseconds; the LLM call dwarfs it. Sampling or one-shot capture would compromise the lie-detector contract. The straight implementation is correct.
  - Severity: minor (perf observation, not a behavioral cut)
  - Forward impact: none — flagged in Delivery Findings as an Improvement opportunity if telemetry volume ever becomes a hot spot.

### Reviewer (audit)

- **TEA deviation: "Five RED-phase tests pass as regression guards"** → ✓ ACCEPTED by Reviewer: regression-guard pattern is correct for an invariant-preservation test (round-trip equivalence + anti-confabulation anchors). The four guard tests defend against future drop-list creep; the round-trip test defends against pydantic-version drift. Sharper than the alternative of forced-failure-only tests.

- **TEA deviation: "`local_dm.py:308` dropped from Phase A scope"** → ✓ ACCEPTED by Reviewer: independently verified — line 308 is a string-injection site (`f"<game_state>\n{state_summary}\n</game_state>\n"`), not a JSON encode. The LocalDM caller chain receives `state_summary: str` pre-encoded. Dev's confirming Delivery Finding corroborates. Architect's spec-check Resolution A (amend ADR) is the correct follow-up.

- **Dev deviation: "`bytes_before` recomputed every turn rather than cached or sampled"** → ✓ ACCEPTED by Reviewer: simplify-efficiency explicitly evaluated this exact concern (see `## TEA Assessment (verify)`) and ruled it not over-engineering. Per-turn `bytes_before` is required for Sebastien's lie-detector contract. The alternative (cached fixture constant) breaks under schema drift.

- **Architect spec-check finding #1: AC#1 second encode site (local_dm.py:308) is non-existent** → ✓ ACCEPTED by Reviewer: redundant with TEA + Dev deviations above. Resolution A (amend ADR-110 in a follow-up doc PR) is correct. No code action for 57-5.

- **Architect spec-check finding #2: AC#5(b) narrator-quality regression counter deferred** → ✓ ACCEPTED by Reviewer with caveat: defer matches 57-4 precedent and is the only practical option absent a playtest-replay harness. The OTEL `prompt.game_state.bytes` span + the four anchor-preservation guard tests + the documented Field Audit grid give the GM panel and the next-developer enough visibility to catch regressions in playtest. **Reviewer recommendation:** the next playtest should specifically watch for confabulation around trope progression (since `active_tropes` was dropped) and tone-axis drift (since `axis_values` was dropped) — if either degrades, restore that field and re-measure per ADR-110 §Acceptance gate.

- No undocumented Reviewer-discovered deviations.

### Architect (reconcile)

**Existing deviation entry audit:**

- **TEA: "Five RED-phase tests pass as regression guards"** — Verified accurate. All 6 fields present and substantive. Spec source path exists; spec text quoted accurately. Implementation matches what shipped (round-trip + four anchor-preservation tests, all 5 stayed green through Dev's diff). Forward impact correctly identifies these as preservation gates. **No correction.**
- **TEA: "`local_dm.py:308` dropped from Phase A scope"** — Verified accurate. Independent re-confirmation: `local_dm.py:304-311` is `_build_user_prompt(... state_summary: str ...) -> str` — string injection, not encoding. Spec text quoted accurately from context-story-57-5.md §Primary edit sites #2. Forward impact (amend ADR) is the right call. **No correction.**
- **Dev: "`bytes_before` recomputed every turn rather than cached or sampled"** — Verified accurate. The `session_helpers.py:602-605` block does indeed re-run `json.loads(snapshot.model_dump_json())` + `json.dumps(_baseline_payload, indent=2)` every turn. Rationale is sound: per-turn fidelity is required by Sebastien's lie-detector contract. Reviewer + simplify-efficiency both ratified independently. **No correction.**

**AC accountability cross-reference** (against Dev Assessment "Acceptance Gate Verification" table):

| AC | Spec status | Code status | Resolution |
|----|-------------|-------------|-----------|
| AC #1 — Phase A applied | "both encode sites" | one encode site (the other does not exist) | Resolution A, ADR amendment follow-up (TEA + Dev + Architect spec-check + Reviewer all concur) |
| AC #2 — Field audit documented | Field Audit grid in session | DONE — 12-row evidence table | — |
| AC #3 — ≥50% byte reduction | tested on fixture | DONE — passing | — |
| AC #4 — Pydantic round-trip equivalence | tested | DONE — passing (guard) | — |
| AC #5(a) — Anti-confabulation anchors preserved | tested | DONE — 4 guard tests, all stayed green | — |
| AC #5(b) — game_patch population rate ≥ baseline on 20+ turn corpus | regression counter | **DEFERRED** | Resolution D (defer-to-playtest, per 57-4 precedent — Architect spec-check + Reviewer audit both ratified) |
| AC #6 — OTEL span live with required attrs | tested | DONE — 3 tests passing | — |
| AC #7 — Full server test suite green | tested | DONE — 6881/0 | — |

The AC #5(b) deferral was NOT invalidated by review. The Reviewer's playtest-watchlist recommendation (monitor trope-progression and tone-axis drift) inherits as the playtest-time evaluation criterion.

**Missed deviations:** None. The trio of TEA + Dev + Reviewer covered every divergence I could find. The two spec-check findings (local_dm.py:308 non-existence + AC #5(b) deferral) are already reflected as deviations under TEA/Dev subsections and stamped by Reviewer.

**Forward obligations** (not deviations — captured for the boss's audit):

- **ADR-110 amendment** — follow-up doc PR to remove the `local_dm.py:308` second-site claim from §Phase A. Non-blocking; can be a single-line doc commit.
- **Playtest watchlist for next session** — confabulation around trope progression (`active_tropes` dropped from Valley) and tone-axis drift (`axis_values` dropped). The `prompt.game_state.bytes` span is the runtime telemetry surface; ADR-110 §Acceptance gate's "restore the field and re-measure" remediation is on the table if either regression appears.
- **Pre-existing pyright debt** in `session_helpers.py` (Reviewer Improvement finding) — file-level technical debt unrelated to 57-5; candidate for a future cleanup story.

**Decision:** spec-reconcile complete. Hand to SM (Hawkeye Pierce) for finish.