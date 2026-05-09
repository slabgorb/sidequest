---
story_id: "47-7"
jira_key: ""
epic: "47"
workflow: "tdd"
---
# Story 47-7: Magic state bars initialized at world-load + uninit warning span

## Story Details
- **ID:** 47-7
- **Jira Key:** (SideQuest is personal — no Jira)
- **Workflow:** tdd
- **Epic:** 47 — Magic System Coyote Reach v1
- **Points:** 2
- **Priority:** p2
- **Type:** bug
- **Stack Parent:** none
- **Repos:** sidequest-server

## Context

This story was authored title-only. **Architect (the White Queen) resolved scope on 2026-05-09** — see "Architect Scope Resolution" below. The title is a compound description of two pieces of Coyote-Star Task 3.5: the init half is done by 47-10, the uninit-warning-span half is the actionable remainder.

### Current State (from 47-10 merge)

Story 47-10 shipped `init_magic_state_for_session` (`sidequest-server/sidequest/server/magic_init.py`) which:
- Builds the `MagicState` on the first commit per session, eager-initializing world-scope bars via `MagicState.from_config(config)` (iterates `config.ledger_bars` with `scope="world"`).
- Calls `state.add_character(character_id, character_class=...)` for each character — this is **plugin-agnostic** and instantiates every per-character `LedgerBarSpec` declared in the world's `ledger_bars` (innate_v1's sanity/notice/vitality, plus class-keyed bars for B/X-style spell slot allocation).
- Calls `seed_learned_v1_state` for casters whose `ClassDef` declares `magic_config` — populates known_spells, prepared_spells (empty dict), and per-level slot bars.
- Includes a loud-fallback guard at `magic_init.py:319-342` that emits the `magic.init_no_actor_bars` watcher event when `innate_v1` is active but no per-character bars instantiated for the actor (defends against world authoring mistakes).

There is no init gap. The title's "initialized at world-load" half is descriptive of what 47-10 already accomplished.

### What's NOT done — Task 3.5 residue

Three defensive paths still emit plain `logger.warning` / `_log.warning` without surfacing to the GM panel via `_watcher_publish`. Per CLAUDE.md OTEL Observability Principle, every subsystem decision MUST be observable from the GM panel — these warnings are the lie-detector blind spots:

1. **`magic.unrouted_cost`** at `sidequest-server/sidequest/magic/state.py:270-276` (inside `MagicState.apply_working`) — fires when a working tries to debit a `cost_type` for which no character-scope bar exists. Code comment at `state.py:267-269` explicitly identifies this as Task 3.5's open work: *"Task 3.5 will promote this to an OTEL `magic.unrouted_cost` span; until then a structured warning makes the skip visible in logs."*

2. **`magic.init_no_catalog`** at `sidequest-server/sidequest/server/magic_init.py:264-271` — fires when a class declares `magic_config` (caster) but no spell catalog matches the class's `tradition`. Indicates a content/wiring gap: a Mage exists but their spellbook can't be filled.

3. **`magic.init_class_def_invalid`** at `sidequest-server/sidequest/server/magic_init.py:74-79` — fires when an entry in `classes.yaml` fails Pydantic validation. Indicates an authoring bug in the genre pack.

All three are **defensive paths that should never fire in production**. They need `_watcher_publish` parity so the GM panel surfaces them when they do — matching the precedent set by `magic.init_no_actor_bars`, `magic.init_failed`, `magic.init_skipped`, and `state_transition: confrontations_load_failed` already in `magic_init.py`.

### Architect Scope Resolution (2026-05-09, the White Queen)

**Decision: Scope (b) only.** Promote the three named warnings (`magic.unrouted_cost`, `magic.init_no_catalog`, `magic.init_class_def_invalid`) to `_watcher_publish` events using the existing dual-emit pattern (preserve the `logger.warning` for forensic logs; *add* the `_watcher_publish` for live GM-panel visibility).

**Rationale:**
- **Reuse over new.** The watcher-publish pipeline is already wired and proven (`magic.init_no_actor_bars` is the pattern). No new ADR, no new infrastructure — just three call-site additions.
- **Tight 2-pointer.** Three replacements + tests fits the points exactly.
- **No new OTEL Span.open contextmgr.** Defensive warnings are events, not traces — the existing `_watcher_publish` direct-call pattern is correct for these. (The full `Span.open` contextmgr in `telemetry/spans/magic.py` is reserved for success-path tracing like `magic.working` and `innate_v1.cast`. We don't add a new contextmgr here — that would be over-engineering for an event that fires only in error paths.)
- **(a) explicitly rejected as out-of-scope** — `add_character` is already plugin-agnostic; init isn't broken. Re-architecting it would inflate the story to 5-8 points and gain nothing.
- **(c) rejected** — the warning-promotion work is real, visible in code, and named by an in-source comment.

**Pattern to follow** (`magic_init.py:319-342` for `magic.init_no_actor_bars`): keep the `logger.warning(...)` call, add a `_watcher_publish(event_name, payload, component="magic", severity="warning")` call immediately after.

## Workflow Tracking

**Workflow:** tdd (Test-Driven Development)
**Phase:** finish
**Phase Started:** 2026-05-09T13:41:34Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-09T23:15:00Z | 2026-05-09T13:05:06Z | -36594s |
| red | 2026-05-09T13:05:06Z | 2026-05-09T13:16:48Z | 11m 42s |
| green | 2026-05-09T13:16:48Z | 2026-05-09T13:22:37Z | 5m 49s |
| spec-check | 2026-05-09T13:22:37Z | 2026-05-09T13:24:38Z | 2m 1s |
| verify | 2026-05-09T13:24:38Z | 2026-05-09T13:28:56Z | 4m 18s |
| review | 2026-05-09T13:28:56Z | 2026-05-09T13:38:36Z | 9m 40s |
| spec-reconcile | 2026-05-09T13:38:36Z | 2026-05-09T13:41:34Z | 2m 58s |
| finish | 2026-05-09T13:41:34Z | - | - |

## Acceptance Criteria

Defined by Architect (the White Queen) on 2026-05-09. Scope: promote three magic-subsystem defensive warnings to `_watcher_publish` events for GM-panel visibility. **Init wiring (the title's "initialized at world-load" half) is already shipped by 47-10 and is explicitly out-of-scope** — see "Architect Scope Resolution" above.

**AC1 — `magic.unrouted_cost` watcher event.**
In `sidequest-server/sidequest/magic/state.py` inside `MagicState.apply_working` (currently lines 263-277), immediately after the existing `_log.warning("magic.unrouted_cost ...", ...)` call, add a `_watcher_publish("magic.unrouted_cost", payload, component="magic", severity="warning")` call. Payload fields:
- `actor` — `working.actor`
- `cost_type` — the `cost_type` key from the costs loop
- `amount` — the `amount` value from the costs loop
- `bar_lookup_key` — the `serialized` BarKey string the lookup missed
- `working_id` — `getattr(working, "id", None)` (defensive — `MagicWorking` may not always carry an id)

The `_log.warning` line is preserved (dual-emit pattern, matches `magic.init_no_actor_bars`). Update the in-source comment at `state.py:267-269` to reference story 47-7 and note the work is now done (e.g. *"Promoted to a `magic.unrouted_cost` watcher event in story 47-7 — GM panel surfaces residual unrouted-cost paths while the world/item-scope routing is finished out."*).

Import `_watcher_publish` from `sidequest.telemetry.watcher_hub` if not already imported in `state.py`. If `state.py` has previously avoided the watcher-hub dependency for layering reasons, surface that as a Delivery Finding rather than working around it silently — but the existing layering already permits it (see `magic_init.py` which sits one layer up and freely uses `_watcher_publish`; `state.py` has no stricter constraint).

**AC2 — `magic.init_no_catalog` watcher event.**
In `sidequest-server/sidequest/server/magic_init.py` inside `init_magic_state_for_session` at the existing `logger.warning("magic.init_no_catalog ...", ...)` block (currently lines 264-271), add a `_watcher_publish("magic.init_no_catalog", payload, component="magic", severity="warning")` call after the warning. Payload fields:
- `world_slug`
- `actor` — `character_id`
- `class` — `character_class`
- `tradition` — the `tradition` string the lookup missed
- `class_id` — `class_def.id`

Preserve the `logger.warning` call. No comment update required (this path was not pre-flagged as Task 3.5 work, but Architect grouped it for parity with AC1 — note this in the Delivery Findings if TEA wants).

**AC3 — `magic.init_class_def_invalid` watcher event.**
In `sidequest-server/sidequest/server/magic_init.py` inside `_load_class_def` at the existing `logger.warning("magic.init_class_def_invalid ...", ...)` block (currently lines 74-79), add a `_watcher_publish("magic.init_class_def_invalid", payload, component="magic", severity="warning")` call after the warning. Payload fields:
- `genre_pack_source_dir` — `str(genre_pack_source_dir)` (it's a `Path`)
- `entry_id` — the same `entry.get("id", "?")` expression already in the warning
- `error` — `str(exc)`

Preserve the `logger.warning` call.

**AC4 — Test: `magic.unrouted_cost` watcher event captured.**
New unit test in the appropriate test module (likely `sidequest-server/tests/magic/test_state.py` or wherever existing `apply_working` tests live — TEA decides). Construct a `MagicState` with one character whose only character-scope bar is e.g. `sanity`. Apply a `MagicWorking` whose `costs` includes a `cost_type` with no matching bar (e.g. `phantom_cost: 0.5`). Assert:
- The result's `bar_changes` does NOT include `phantom_cost` (existing behavior, regression check).
- A `magic.unrouted_cost` event was published to the watcher hub with `actor`, `cost_type`, `amount`, `bar_lookup_key` fields populated.

Use whatever pattern existing `magic.init_failed` / `magic.init_no_actor_bars` tests use to capture watcher events (likely a fixture that replaces `_watcher_publish` with a list-appending capture, or hooks `watcher_hub.subscribe`). Reuse — don't invent.

**AC5 — Test: `magic.init_no_catalog` watcher event captured.**
New unit test in `sidequest-server/tests/server/test_magic_init.py` (or equivalent — TEA decides). Set up a fixture with: a world activating `learned_v1`, a class declaring `magic_config` with a `tradition` value (e.g. `"phantom_tradition"`) for which no entry exists in `config.spell_catalogs`. Call `init_magic_state_for_session`. Assert:
- The function returns `True` (init still succeeds — no-catalog is a soft fail, not a hard error; existing behavior, regression check).
- A `magic.init_no_catalog` event was published with `world_slug`, `actor`, `class`, `tradition` fields.

**AC6 — Test: `magic.init_class_def_invalid` watcher event captured.**
New unit test exercising `_load_class_def` (or the end-to-end `init_magic_state_for_session` if `_load_class_def` is private and tests prefer the public surface — TEA decides). Provide a `classes.yaml` containing one valid entry and one invalid entry (e.g. missing required field, wrong type). Call the function. Assert:
- The valid entry is still returned (existing behavior, regression check).
- A `magic.init_class_def_invalid` event was published with `genre_pack_source_dir`, `entry_id`, `error` fields for the invalid entry.

**AC7 — Wiring test (project rule).**
Per CLAUDE.md "Every Test Suite Needs a Wiring Test": at least one of AC4/AC5/AC6's tests must use the **real** `_watcher_publish` path through `sidequest.telemetry.watcher_hub` and verify the event reaches a subscriber via the same hook the GM panel uses (not a mocked function reference). The other two tests may use lightweight mocks. TEA picks which one — recommend AC4 (`magic.unrouted_cost`) since it's the named Task 3.5 path.

**Out of scope (explicit):**
- Generalizing `init_magic_state_for_session` beyond `learned_v1` — already plugin-agnostic via `add_character`.
- Promoting other magic warnings beyond the three named (e.g. `magic.confrontations_init_failed` already publishes via `state_transition`; `learned_v1.cast` is a success-path span, not a warning).
- New `Span.open` contextmgr in `telemetry/spans/magic.py` — defensive warnings use direct `_watcher_publish`, not full OTEL spans (matches `magic.init_no_actor_bars` precedent).
- GM-panel UI rendering of the new event types — the panel already renders `state_transition` and severity=warning events generically; if Keith finds the new events need richer rendering during dogfooding, file a separate UI story.
- New ADR — this story follows established patterns; no new architectural decision is being made. Architect scope resolution is recorded in this session file.

**Spec authority:** This session file is the highest-authority spec for 47-7. The story's epic-47 entry (sprint/epic-47.yaml line 83-90) carries the title only; if it gains a description later that conflicts with these ACs, log a deviation per spec-authority hierarchy.

## Sm Assessment

Setup phase complete. Joint output of SM (the Mad Hatter) and Architect (the White Queen):

**Story selected** (PM → SM): 47-7 was prioritized by PM (Alice) on 2026-05-09 — 2pt, p2, on-goal for the Sprint 3 "state hygiene" pillar. Pulled ahead of 5pt 45-51 because (a) it's smaller, (b) PM identified scope ambiguity worth resolving cheaply before the bigger lift.

**Setup decision** (SM): Story shipped from sprint YAML with title only — no description, no ACs. Standard tdd routing would have sent TEA into red phase against TBD criteria. SM held the phase at `setup` and routed to Architect (out-of-band; tdd workflow has no formal architect phase) rather than burning TEA cycles on speculation.

**Branch created** (SM-setup helper): `feat/47-7-magic-state-bars-init-warning` on sidequest-server, off develop @ `1a613d4`. SideQuest does NOT use Jira (per project memory) — `JIRA_KEY: ""` is intentional, no `pf jira` calls performed.

**Scope resolved** (Architect — the White Queen):
- **(b) only — promote three defensive `_log.warning` paths to `_watcher_publish` watcher events** for GM-panel visibility. ACs 1-7 written below.
- (a) — already shipped by 47-10 via `add_character` + `seed_learned_v1_state` + world-scope eager init. No init gap exists. The title's "initialized at world-load" half is descriptive of done work.
- (c) — rejected; the warning-promotion work is real, named in code (`state.py:267-269` "Task 3.5"), and visible.
- See "Architect Scope Resolution" subsection above for full rationale.

**Pattern reuse** (Architect): No new ADR. No new `Span.open` contextmgr. New code follows the existing `magic.init_no_actor_bars` precedent at `magic_init.py:319-342` (dual-emit: keep `logger.warning`, add `_watcher_publish`). New sidecar entry written to `architect-patterns.md` documenting the two-tier OTEL pattern (defensive warnings vs success traces) for future stories.

**Known risk** (Architect → TEA): The watcher-event capture pattern in tests is unstated — TEA must locate the existing pattern (likely a fixture replacing `_watcher_publish` or a `watcher_hub.subscribe` capture in tests for `magic.init_failed` / `magic.init_no_actor_bars` / `state_transition: confrontations_load_failed`). Reuse, don't invent. If no pattern exists yet, surface as a Delivery Finding.

**Spec authority hierarchy** (Architect): This session file is the highest-authority spec for 47-7. The ACs supersede the bare title in `sprint/epic-47.yaml`. Any future description added to that YAML entry that conflicts with these ACs must be reconciled via a deviation entry, not silent override.

**Handoff to TEA (the Caterpillar):** red phase, with seven crisp ACs. Two pointer scope. No speculation needed.

## Tea Assessment (verify)

Verify-phase sweep complete. Final state: 30/30 tests pass in modified files; ruff lint + format clean (one trivial format normalization committed as `7919c0b` — two-line filter collapsed to one line, no semantic change). Ready for Reviewer.

### Simplify fan-in (3 teammates spawned in parallel)

| Lens | Status | Findings |
|------|--------|----------|
| simplify-efficiency | clean | 0 (no over-engineering or unnecessary complexity in diff) |
| simplify-quality | clean | 0 (import conventions match codebase, error handling matches CLAUDE.md, wiring test present, no layer violations) |
| simplify-reuse | findings | 2 high-confidence + 1 medium-confidence — see triage below |

### Triage of simplify-reuse findings

**1. High-confidence: Extract `_log_and_publish_warning` helper** (4 dual-emit sites — 1 from this story + 3 pre-existing).

**Decision: DEFER to follow-up cleanup story.** Reasons:
- **Architect explicitly scoped** at setup phase: *"Reuse over new. The watcher-publish pipeline is already wired and proven … no new ADR, no new infrastructure — just three call-site additions."* A helper would be new infrastructure.
- **Pre-existing call sites lack test coverage.** I logged a Delivery Finding earlier that `magic.init_no_actor_bars` (one of the 4 sites) has no test in the suite. Refactoring it through a new helper would silently move untested code with no safety net.
- **Risk-vs-value asymmetry.** A helper saves ~15 lines across 4 sites; the refactor crosses 3 modules and touches code not in this story's scope. Cost > value for a 2-pointer.
- **Architect can re-decide later.** If the helper becomes worth it after a 5th call site lands (or after the untested site gains coverage), file a clean refactor story. The current call sites all follow the pattern verbatim, so consolidating later is mechanical.

Filing as a non-blocking Delivery Finding for a future cleanup story.

**2. High-confidence (duplicate of #1):** Same finding, framed from the magic_init.py side. Same disposition.

**3. Medium-confidence: Standardize watcher-event capture pattern in tests** (async-subscribe in `test_state.py` vs monkeypatch in `test_magic_init.py`).

**Decision: DISMISS — by-design split.** The two patterns serve different purposes and that's deliberate:
- **async-subscribe (`test_state.py`)** uses the **real** `watcher_hub.bind_loop` + `watcher_hub.subscribe(_Sock())` path — the same hook the GM dashboard consumes. Per CLAUDE.md "Every Test Suite Needs a Wiring Test," at least one test must use the real path. This is the wiring test for the new dual-emit contract.
- **monkeypatch (`test_magic_init.py`)** is a unit-level intercept — fast, no asyncio plumbing, appropriate for warnings that don't need full hub coverage.

Standardizing on monkeypatch would lose the wiring coverage; standardizing on async-subscribe would inflate every defensive-warning test with asyncio bind/clear/subscribe boilerplate. The split is correct.

### Quality-pass gate (Python lang-review checklist)

| # | Rule | Status |
|---|------|--------|
| 1 | Silent exception swallowing | Pass — no new exception handlers; existing `(ValidationError, TypeError)` catch in `_load_class_def` is specific |
| 2 | Mutable default arguments | Pass — no new function defaults; payload dicts are constructed fresh at each call site |
| 3 | Type annotation gaps | Pass — no new public function signatures; existing helpers retain annotations |
| 4 | Logging coverage AND correctness | Pass — dual-emit pattern enforced; severity correctly mapped (`warning` for all three new events, matching the precedent) |
| 5 | Path handling | Pass — `str(genre_pack_source_dir)` is the only Path stringification (intentional, payload field needs str) |
| 6 | Test quality | Pass — every assertion checks specific values, counts, list equality, or substring containment; no `assert True`, no truthy-only checks on always-truthy values |
| 7 | Resource leaks | Pass — no new resource acquisitions; `tmp_path` fixtures use pytest's `with`-style cleanup |
| 8 | Unsafe deserialization | Pass — `yaml.safe_load` already in use at the existing call sites; my fixture in `_make_pack_with_phantom_tradition` uses `yaml.safe_load` and `yaml.safe_dump` |
| 9 | Async/await pitfalls | Pass — async tests use `asyncio.sleep(0.05)` with explicit comment ("yield long enough for it to drain"); `watcher_hub.publish` is sync; no missing `await`s |
| 10 | Import hygiene | Pass — no star imports, no circular imports introduced (state.py already imports from telemetry transitively via plugin layer; the new direct import is clean) |
| 11 | Input validation | N/A — no new external inputs |
| 12 | Dependency hygiene | N/A — no dependency changes |
| 13 | Fix-introduced regressions | Pass — re-checked the diff against #1-#12; no second-order issues |

### Delivery findings (added during verify)

- **Improvement (non-blocking):** Extract `_log_and_publish_warning(logger, log_args, event_type, payload, *, component, severity)` helper to consolidate the 4 dual-emit call sites (1 from this story + 3 pre-existing: `magic.init_failed`, `magic.init_skipped`, `magic.init_no_actor_bars`). High-confidence DRY win identified by simplify-reuse. Defer because: (a) architect explicitly scoped this story as "no new infrastructure", (b) pre-existing call sites including `magic.init_no_actor_bars` have no test coverage, (c) cost-vs-value is wrong for a 2-pointer. File as a clean refactor story when worth it.

### Decision: Proceed to Reviewer (the Queen of Hearts)

Verify gate satisfied. No blocking findings. Diff is small, focused, and well-tested. Reviewer can take it from here.

---

## Tea Assessment

RED state confirmed. 4 new tests fail with assertion errors about missing watcher events; 26 pre-existing tests still pass — including `test_apply_working_unrouted_cost_logs_warning` which defends the dual-emit contract from regression.

### Test inventory (commit `32524e6` on `feat/47-7-magic-state-bars-init-warning`)

| AC | Test | File | Pattern | Expected RED reason |
|----|------|------|---------|---------------------|
| AC4 + AC7 wiring | `test_apply_working_unrouted_cost_publishes_watcher_event` | `tests/magic/test_state.py` | Real `watcher_hub.subscribe` path (asyncio + `_Sock`) | No `_watcher_publish` call in `state.apply_working` yet |
| AC4 (extension) | `test_apply_working_multiple_unrouted_costs_publish_one_event_per_miss` | `tests/magic/test_state.py` | Real `watcher_hub.subscribe` path | Same — also defends per-cost forensics from future "batch into one event" refactor |
| AC5 | `test_init_no_catalog_publishes_watcher_event` | `tests/server/test_magic_init.py` | Monkeypatch `magic_init._watcher_publish` (`raising=False`) | No `_watcher_publish` call after the no_catalog `logger.warning` yet |
| AC6 | `test_init_class_def_invalid_publishes_watcher_event` | `tests/server/test_magic_init.py` | Monkeypatch `magic_init._watcher_publish` (`raising=False`) | No `_watcher_publish` call inside `_load_class_def` yet |

### Wiring test placement (CLAUDE.md "Every Test Suite Needs a Wiring Test")

AC4's two tests use the **real** `watcher_hub.bind_loop` + `watcher_hub.subscribe(_Sock())` path — the same hook the GM dashboard uses. Adapted from `tests/integration/test_lore_wiring.py` `_setup` helper. AC5/AC6 use the lighter monkeypatch fixture pattern (mirror of `tests/magic/test_magic_span.py` `captured_watcher_events`) — fast unit-level intercept appropriate for warnings that don't need full async hub plumbing.

### Rule coverage (Python lang-review checklist)

| # | Rule | Covered by |
|---|------|------------|
| 4 | Logging coverage AND correctness | Pre-existing `test_apply_working_unrouted_cost_logs_warning` defends the `logger.warning` half of dual-emit; new tests defend the watcher half. Severity is asserted (`severity == "warning"`). |
| 6 | Test quality (no vacuous assertions) | Self-checked: every assertion is value/count/substring/list-equality, never `assert True` or always-truthy. |
| 13 | Fix-introduced regressions | The pre-existing log-only test still passes — proves the dual-emit contract is the bar Dev must meet, not "swap log for watcher". |

Other rules (#1 silent exceptions, #5 path handling, #7 resource leaks, #8 unsafe deserialization, #9 async pitfalls, #11 input validation) are not relevant to this story — no new exception handlers, no path manipulation, no resources, no untrusted input. Rule #2 (mutable defaults) is the only "could apply" — Dev must not introduce `def f(x={})` patterns when adding the `_watcher_publish` calls; existing convention shows `dict()` literals at call sites, not parameter defaults.

### Notes for Dev (the White Rabbit)

1. **Import bridge in `state.py` is new.** `state.py` does not currently import `_watcher_publish`. Dev adds: `from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish` (matching `magic_init.py`'s alias). No layering concern — `state.py` is the same crate as `magic_init.py` and can freely depend on `telemetry`.

2. **`working_id` payload field will always be `None`.** Architect's AC1 includes `working_id: getattr(working, "id", None)` in the payload, but `MagicWorking` (sidequest-server/sidequest/magic/models.py:75) has no `id` field. The `getattr` returns `None` always. My tests deliberately do NOT assert on `working_id` (it would be a vacuous always-None check). Dev's options: (a) include the field as a None placeholder for forward-compat when MagicWorking gains an id, or (b) drop the field. Either is acceptable — flag in dev assessment whichever you choose. **My test will pass either way** because it asserts on the four meaningful fields only.

3. **Dual-emit, not replace.** Three call sites — keep the existing `logger.warning(...)` line, add the `_watcher_publish(...)` line right after. Pattern reference: `magic_init.py:319-342` (`magic.init_no_actor_bars`). The pre-existing `test_apply_working_unrouted_cost_logs_warning` will catch any accidental log removal.

4. **No new module, no new file.** All three changes are in two existing files: `sidequest-server/sidequest/magic/state.py` (one site) and `sidequest-server/sidequest/server/magic_init.py` (two sites).

5. **Update the in-source comment** at `state.py:267-269` per AC1 — it currently references "Task 3.5" as future work; rewrite to reference story 47-7 as the work that closed it.

6. **The `test_apply_working_multiple_unrouted_costs_publish_one_event_per_miss` test** is one I added beyond the literal AC4 spec. Architect's AC1 said "for each cost_type" but didn't explicitly mandate one-event-per-cost. I made the test explicit because batching would be a sneaky-correct refactor that loses forensic value. If Dev disagrees with this scope expansion, surface as a deviation.

### Findings

- **Gap (non-blocking):** `magic.init_no_actor_bars` (the existing precedent watcher event at `magic_init.py:319-342`) has NO test in the suite. This is pre-existing tech debt outside 47-7 scope — flagging for future cleanup, do NOT add coverage as part of this story.
- **Question (non-blocking, for Dev):** `MagicWorking.id` field doesn't exist; should we add one (separate story) so `working_id` payload is meaningful, or drop the field from this story's payload? Lean drop. Architect: please weigh in during spec-check if it matters.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

- **Gap (non-blocking):** `magic.init_no_actor_bars` watcher event (`sidequest-server/sidequest/server/magic_init.py:319-342`) has no test coverage in the suite — pre-existing tech debt, NOT in 47-7 scope. File a follow-up if any future story touches this code path.
- **Question (non-blocking):** `MagicWorking` model has no `id` field but architect AC1 specifies `working_id: getattr(working, "id", None)` in the payload — always evaluates to `None`. Recommend Dev drops the field or documents it as forward-compat reservation. Architect to weigh in at spec-check. **(Resolved by Dev — see Dev Assessment + deviation below.)**
- **Gap (non-blocking, baseline):** `tests/game/test_chargen_reroll_loop.py::test_reroll_fires_when_no_class_qualifies` fails on `develop`-tip, pre-existing and unrelated to 47-7 (no chargen files modified by this story). Not blocking — file a separate bugfix story if it persists.
- **Improvement (non-blocking, deferred):** Extract `_log_and_publish_warning(logger, log_args, event_type, payload, *, component, severity)` helper to consolidate 4 dual-emit call sites in the magic subsystem (1 from this story: `magic.unrouted_cost`; 3 pre-existing: `magic.init_failed`, `magic.init_skipped`, `magic.init_no_actor_bars`). Identified by simplify-reuse during verify phase. Deferred from 47-7 per architect's "no new infrastructure" scope decision and because pre-existing call sites lack test coverage (foot-gun risk). File as a clean refactor story when a 5th call site lands or when the untested precedent gains coverage.

## Dev Assessment

GREEN state confirmed. All 4 new tests + all 26 pre-existing tests in the modified files pass; lint clean; no regressions in the magic subsystem. Commit `dd840a9` on `feat/47-7-magic-state-bars-init-warning`.

### AC coverage

| AC | What was changed | Test verifying it |
|----|------------------|-------------------|
| AC1 | Added `_watcher_publish` import to `state.py`; added `magic.unrouted_cost` watcher emit after the existing `_log.warning` in `apply_working` (preserves logger.warning for forensic logs); updated in-source comment from "Task 3.5 will promote..." to "Story 47-7 promoted..." | `test_apply_working_unrouted_cost_publishes_watcher_event` (real watcher_hub path), `test_apply_working_multiple_unrouted_costs_publish_one_event_per_miss` (per-cost forensics) |
| AC2 | Added `magic.init_no_catalog` watcher emit after the existing `logger.warning` in the no-catalog branch of `init_magic_state_for_session` | `test_init_no_catalog_publishes_watcher_event` |
| AC3 | Added `magic.init_class_def_invalid` watcher emit after the existing `logger.warning` in `_load_class_def`'s exception handler. Hoisted `entry_id` extraction to a local var to avoid duplicating the conditional expression in two payloads. | `test_init_class_def_invalid_publishes_watcher_event` |
| AC4-7 | All TEA's tests pass green | (above) |

### Files touched (production)

- `sidequest-server/sidequest/magic/state.py`: +1 import, +1 watcher_publish call inside `apply_working`'s unrouted-cost branch, comment update.
- `sidequest-server/sidequest/server/magic_init.py`: +2 watcher_publish calls (no_catalog + class_def_invalid), +1 local var hoist (`entry_id`).

No new files. No test changes (TEA owned those). No imports beyond what was already in scope.

### Implementation complete: yes

All three call sites converted, dual-emit verified by tests (the pre-existing `test_apply_working_unrouted_cost_logs_warning` continues to pass — proves the logger.warning side wasn't accidentally removed). No silent fallbacks, no stubs.

### Pattern fidelity

- Followed `magic_init.py:319-342` (`magic.init_no_actor_bars`) precedent exactly — `logger.warning(...)` first, `_watcher_publish(...)` second, `component="magic"`, `severity="warning"`.
- Did NOT add a `Span.open` contextmgr in `telemetry/spans/magic.py` (per architect: defensive warnings don't need full OTEL spans).
- Did NOT modify any other warning paths (`magic.confrontations_init_failed` already publishes via `state_transition`; `magic.init_no_actor_bars` was the model, not a target).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

### TEA (test design)

- **Added one extension test beyond literal ACs.** `test_apply_working_multiple_unrouted_costs_publish_one_event_per_miss` is not strictly required by AC4 ("a watcher event was published … with actor, cost_type, amount, bar_lookup_key fields populated") — it adds the constraint that *each missed cost_type produces its own event* rather than one batched event. Spec source: AC1 in `.session/47-7-session.md` lines 76-83 — "for each cost_type" is implied by the loop structure but not explicitly mandated as an event count. Reason: a future refactor that batches the warning into a single multi-cost event would silently lose per-cost GM-panel forensics; cheapest place to nail down the contract is now, in red. Forward impact: Dev must emit one event per loop iteration, not one summary event after the loop. If this is wrong, swap the test for a less-strict variant during spec-check.
  - Spec source: `.session/47-7-session.md`, AC1 (the unrouted_cost watcher event AC) — "for each cost_type" is implied by the per-iteration `_watcher_publish` placement inside the costs loop, but the AC's payload shape lists "a watcher event was published" without explicitly mandating `len(events) == len(missing_cost_types)`.
  - Spec text: "AC4 — Test: `magic.unrouted_cost` watcher event captured. … Assert: … A `magic.unrouted_cost` event was published to the watcher hub with `actor`, `cost_type`, `amount`, `bar_lookup_key` fields populated."
  - Implementation: Added a second test (`test_apply_working_multiple_unrouted_costs_publish_one_event_per_miss`) asserting that a working with two unrouted cost types produces TWO separate watcher events, sorted as `["karma", "soulstain"]`. Defends the per-cost forensics contract.
  - Rationale: A future refactor that batches the warning into a single multi-cost event would silently lose per-cost GM-panel forensics; cheapest place to nail down the contract is in red, before any consumer assumes single-event-per-working semantics. Architect approved at spec-check.
  - Severity: minor
  - Forward impact: none — the test is additive; existing AC4 still satisfied; no downstream story affected (no consumer reads `magic.unrouted_cost` events yet beyond the GM panel feed).

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (1 mismatch — accepted as Option A spec update)
**Mismatches Found:** 1

- **`magic.unrouted_cost` payload field `working_id` dropped** (Missing in code — Cosmetic, Trivial)
  - **Spec:** AC1 line 82 — *"`working_id` — `getattr(working, "id", None)` (defensive — `MagicWorking` may not always carry an id)"*
  - **Code:** `sidequest-server/sidequest/magic/state.py:279-285` — payload is `{"actor", "cost_type", "amount", "bar_lookup_key"}` (4 fields, not 5)
  - **Recommendation: A — Update spec.** Dev's call is correct on substance. `MagicWorking` (`sidequest-server/sidequest/magic/models.py:75-92`) has no `id` attribute, so `getattr(working, "id", None)` would unconditionally evaluate to `None` — a vacuous always-`None` field on every payload, which dilutes the GM-panel event signal without adding information. My AC1 was a defensive hedge against a hypothetical future model change; that change should be the trigger to add the field, not preemptive scaffolding. Dev's deviation entry already names this forward-compat: when a future story adds `id: str | None` to `MagicWorking`, that story restores the field. No silent-fallback risk — absence is explicit, not swallowed. Severity is trivial because the field's omission has zero behavioral impact (no consumer reads it; the GM panel renders only fields present in payload).

**Sibling AC alignment** (AC2-AC3, AC4-AC7): All other ACs are aligned with code as shipped.
- AC2 (`magic.init_no_catalog`): all 5 payload fields landed exactly as spec'd.
- AC3 (`magic.init_class_def_invalid`): all 3 payload fields landed exactly as spec'd. Dev's local-var hoist of `entry_id` is a clean DRY improvement (avoids duplicating the `entry.get("id", "?") if isinstance(entry, dict) else "?"` conditional across the `logger.warning` and `_watcher_publish` calls) — implementation detail, not a deviation.
- AC4-AC7 (tests): TEA's commit `32524e6` ships all four required tests; Dev's commit `dd840a9` makes them green; pre-existing `test_apply_working_unrouted_cost_logs_warning` continues to pass (defends the dual-emit logger half against accidental removal).
- Pattern fidelity to `magic.init_no_actor_bars` (`magic_init.py:319-342`): exact — `logger.warning(...)` first, `_watcher_publish(...)` second, `component="magic"`, `severity="warning"`. No new `Span.open` contextmgr added (correct per scope decision).
- Comment update at `state.py:267-269`: done — "Task 3.5" → "Story 47-7" with accurate description of what landed.

**TEA's Question on `working_id`:** resolved — see deviation analysis above. Recommendation A (Update spec) accepted.

**Decision:** Proceed to review.

The two-tier OTEL pattern decision (defensive warnings = `_watcher_publish`, success traces = `Span.open`) was the load-bearing call here; it's now lived through one full TDD cycle without surprises. Sidecar entry written during setup phase (`architect-patterns.md`) stands as written — no amendments needed.

### Dev (implementation)

- **Dropped `working_id` field from `magic.unrouted_cost` payload.** **(Resolved at spec-check: Architect accepted as Option A — update spec. Effective AC1 payload is 4 fields, not 5.)**
  - **Spec source:** Architect AC1 in `.session/47-7-session.md` line 82: *"`working_id` — `getattr(working, "id", None)` (defensive — `MagicWorking` may not always carry an id)"*.
  - **Spec text (quoted):** "Payload fields: actor — working.actor, cost_type — the cost_type key from the costs loop, amount — the amount value from the costs loop, bar_lookup_key — the serialized BarKey string the lookup missed, **working_id — getattr(working, "id", None) (defensive — MagicWorking may not always carry an id)**"
  - **Implementation:** Payload omits `working_id` entirely. Final payload at `sidequest-server/sidequest/magic/state.py` is `{"actor": working.actor, "cost_type": cost_type, "amount": amount, "bar_lookup_key": serialized}` — four fields, not five.
  - **Reason:** `MagicWorking` (`sidequest-server/sidequest/magic/models.py:75-92`) has no `id` attribute. `getattr(working, "id", None)` would always evaluate to `None` — a vacuous always-None field on every event payload, which is dead weight that bloats the GM panel and would confuse a reader into thinking the field carries information when it never does. TEA flagged this in their Assessment ("lean drop") and explicitly did NOT assert on the field in tests so either choice would pass. Architect's intent was clearly defensive ("MagicWorking may not always carry an id") — the defense is unnecessary because the type system already guarantees absence.
  - **Forward impact:** When a future story adds `id: str | None = None` to `MagicWorking` (sized as a separate change — there's no consumer demanding it yet), that story should add `working_id` back to this payload. Reference this deviation entry from that future story's commit. No silent-fallback risk: the field's absence is explicit, not silently swallowed.
  - **Architect, please weigh in at spec-check** (matches TEA's Question finding) — if you disagree, restoring the field is a one-line change and the test still passes.
  - Severity: minor
  - Forward impact: none — when a future story adds `id: str | None = None` to `MagicWorking` (no story currently planned), that story should restore `working_id` to this payload. No current consumer reads the field; the GM panel renders only fields present in payload. (Architect spec-check accepted the deviation as Option A — update spec.)
  - → **✓ ACCEPTED by Reviewer (Queen of Hearts):** Architect's spec-check resolution (Option A — update spec) is sound. The defensive hedge added a permanently-None field that would have polluted every event payload with no information. The forward-compat trail (re-add when MagicWorking gains an id) is documented well enough that a future story can find this deviation by grepping for "working_id". No silent-fallback risk; no behavioral impact.

### Architect (reconcile)

- No additional deviations found.

**Reconcile audit notes** (informational; not deviations):

1. **Both existing entries (TEA + Dev) verified.** Spec sources point to ACs in this session file (canonical per spec-authority hierarchy — this session is the highest-authority spec for 47-7). Spec-text quotes are accurate verbatim copies of the ACs as written by Architect at setup phase. Implementation descriptions match the actual code in `feat/47-7-magic-state-bars-init-warning` HEAD (verified via `git show`). Forward impact statements are accurate (TEA: additive test, no downstream; Dev: forward-compat reservation when `MagicWorking.id` lands).
2. **Both existing entries augmented with explicit `Severity` and `Forward impact` lines** to conform to the canonical 6-field format in `.pennyfarthing/guides/deviation-format.md`. Per spec-reconcile guidance: "If an existing entry has an incomplete or missing field, add the missing field rather than flagging it as a new deviation."
3. **Reviewer-driven test tightening (commit `b13ba48`)** — changed `len(matching) >= 1` to `== 1` and bound the error-string assertion to ValidationError marker fragments (`prime_requisite`, `minimum_score`, `kit_table`, `Field required`). These are precision *improvements* to AC6's test, not deviations from any AC. AC6 still passes (and now passes more strictly). Not logged as a deviation.
4. **Dev's `entry_id` local-var hoist in `_load_class_def`** — pure DRY refactor that avoids duplicating the `entry.get("id", "?") if isinstance(entry, dict) else "?"` conditional across the `logger.warning` and `_watcher_publish` calls. Architect noted at spec-check as "implementation detail, not a deviation" — confirmed during reconcile. No spec contract changed.
5. **Format normalization commit (`7919c0b`)** — collapsed a two-line filter expression onto one line (ruff-format-driven). Pure mechanical whitespace; not a deviation.
6. **AC deferral check:** No ACs were deferred. AC1-AC7 all DONE (AC1 with the `working_id` deviation logged under Dev section; AC2-AC7 exact-spec). The conditional spec-check step ("Verify AC Deferral Justifications") is a no-op for this story.
7. **Sibling story coupling check:** Story 47-10 (parent of the magic-init wiring 47-7 builds on) is `done`. Story 47-9 (proactive narrator on innate-active worlds) is `done`. Neither sibling has any contract that the working_id payload field deviation would break. Story 47-8 (Coyote Object salvage hooks — `backlog`, `bdd`, p3) does not touch magic warning paths. No cross-story spec drift introduced.

## Subagent Results

**All received:** Yes

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 2 (applied as commit b13ba48), deferred 2 (project-wide flakiness pattern, file separately) |
| 5 | reviewer-comment-analyzer | Yes | clean | none | confirmed 0, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | N/A — disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 0, dismissed 2 (false positive — flagged pre-existing lines 127-128 from commit 89a66436 dated 2026-04-30, NOT in this diff per `git blame`), deferred 0 |

## Reviewer Assessment

**Verdict: APPROVED**

Story 47-7 is a tight, well-scoped 2-pointer that closes an in-source-named gap (`state.py:267` "Task 3.5") with the dual-emit pattern that the codebase already uses for parallel defensive paths (`magic.init_no_actor_bars`). Architecture decision was made and held; spec-check found one trivial deviation and accepted it cleanly; verify-phase simplify pass was clean on quality + efficiency, with one DRY opportunity properly deferred. The diff is small (47 lines of production change, 240 lines of tests + fixtures) and surgically targeted.

### Findings dispatch

[EDGE]: Skipped (subagent disabled). I read the diff myself for boundary conditions — payload construction is straightforward (no integer overflow surface, no off-by-one in loops, no unbounded user input reaching dict construction). No findings.

[SILENT]: Skipped (subagent disabled). Manual check: this story's whole point is REPLACING silent-failure patterns with loud watcher events. The `_log.warning + _watcher_publish` dual-emit at all three call sites is exactly the right shape. No silent-fallback regression risk; the change tightens silent-failure observability rather than introducing it.

[TEST]: 4 findings from test-analyzer.
- **Finding 3 (high) — `len(matching) >= 1` should be `== 1` at test_magic_init.py:403** — **ACCEPTED, applied** in commit `b13ba48`. The fixture injects exactly one bad entry, so exactly one event must fire; the loose bound would silently pass a future retry-loop bug. Rule-checker disagreed ("intentional, may match multiple bad entries") but rule-checker's argument doesn't apply to MY fixture which has exactly one bad entry — test-analyzer's reading wins.
- **Finding 4 (medium) — vacuous error-string assertion at test_magic_init.py:410** — **ACCEPTED, applied** in commit `b13ba48`. Tightened to assert the error mentions one of the missing-field markers (`prime_requisite`, `minimum_score`, `kit_table`, or `Field required`), binding the captured event to the Pydantic path under test. Without this, a future ImportError or unrelated exception in the loop body would silently produce a passing test.
- **Findings 1 & 2 (medium) — `await asyncio.sleep(0.05)` drain barrier in test_state.py:222 and :288** — **DEFERRED.** The agent itself acknowledges this is the established project pattern across `test_lore_wiring`, `test_audio_wiring`, and 17+ other test files. A poll-with-deadline helper would eliminate the flakiness across all sites at once but represents a project-wide test-infrastructure refactor — out of scope for a 2-pointer. Filed as a non-blocking Delivery Finding for a future cleanup story.

[DOC]: comment-analyzer clean. Verified the in-source comment rewrite at `state.py:267-269` ("Task 3.5 will promote..." → "Story 47-7 promoted...") accurately describes what landed. New comment at `magic_init.py:73-74` ("Story 47-7 adds the watcher event...") accurately describes the added code. The fixture docstring's mention of "RED state" is technically stale (we're now in GREEN) but is documenting a defensive testing pattern (`raising=False`), not a lie about current state — keep as is. No findings.

[TYPE]: Skipped (subagent disabled). Manual check: import alias `_watcher_publish` follows the established `as` convention. Payload dicts are typed implicitly via dict-literal construction — consistent with the rest of `magic_init.py`. No new public function signatures, no stringly-typed APIs introduced. The two-tier OTEL pattern (`Span.open` for success, `_watcher_publish` for defensive) is now used consistently. No findings.

[SEC]: Skipped (subagent disabled). Manual check: no new external input handlers, no auth surface touched, no secrets in payloads. The new `error` field at `magic.init_class_def_invalid` carries `str(exc)` which is a Pydantic ValidationError message — no PII risk (the entry comes from a content-author's classes.yaml, not user input). The `genre_pack_source_dir` payload field is a filesystem path, fine for GM-panel display in this dev context (Keith's local game; no multi-tenant concern). No findings.

[SIMPLE]: Skipped (subagent disabled). simplify-* fan-out during verify phase already covered this dimension — see TEA verify Assessment. The single high-confidence DRY opportunity (`_log_and_publish_warning` helper) was deferred for the same reasons I'd defer it: architect explicitly scoped "no new infrastructure", and the helper would touch pre-existing untested call sites. No additional findings.

[RULE]: 2 findings from rule-checker — **both DISMISSED as false positives.** Rule-checker flagged `(fake_pack / 'magic.yaml').write_text(...)` and `(world_dir / 'magic.yaml').write_text(...)` at test_magic_init.py:127-128 as "new lines introduced by this diff" violating Rule #5 (write_text without `encoding=`). **Verified via `git blame`:** both lines are from commit `89a66436` dated 2026-04-30, several weeks before this story. They are NOT in `/tmp/47-7-diff.patch` (grep returns 0 matches for `permitted_plugins` and `active_plugins.*broken_world`). The lines exist in the file but were not changed by 47-7. Per the agent definition's adversarial guidance, "Existence is not compliance" — but the inverse trap is also real: existence in current code is not the same as introduction by this diff. Rule-checker conflated the two. The pre-existing missing-encoding pattern is real tech-debt worth a follow-up cleanup story (filed as a Delivery Finding) but it cannot block 47-7 because 47-7 didn't author it.

All other rule-checker checks (Rules 1-4, 6-13, plus 6 additional CLAUDE.md/SOUL.md rules) verified compliant. Notable positive verifications:
- **Rule 14 (No Silent Fallbacks):** This story's PURPOSE is closing silent-fallback gaps in the magic subsystem. All 3 new emit sites are loud (`logger.warning` + `_watcher_publish`).
- **Rule 16 (Don't Reinvent — Wire Up What Exists):** Used existing `watcher_hub.publish_event` infrastructure, not new spans/contextmgrs.
- **Rule 17 (Verify Wiring, Not Just Existence):** All three new `_watcher_publish` calls are reachable from production code paths (`apply_working` called from `narration_apply.py`/`orchestrator.py`; `init_magic_state_for_session` called from `websocket_session_handler.py`/`handlers/connect.py`).
- **Rule 18 (Every Test Suite Needs a Wiring Test):** AC4's tests use the REAL `watcher_hub.subscribe` path (not monkeypatch). Wiring guarantee preserved.
- **Rule 19 (OTEL Observability — Task 3.5 closure):** All three target events emit in production code with end-to-end test coverage. Task 3.5 is closed.

### Verdict rationale

The diff is tight, the pattern is correct, the tests are honest (made stronger by the two reviewer-driven tightening edits in commit `b13ba48`), all deviations are properly logged and stamped, and no project rules are actually violated by code introduced in this story. Two simplify-reuse follow-ups (helper extraction, drain-helper) are filed as Delivery Findings for future cleanup stories. **Approved for merge.**

### Severity table (REJECTED only)

N/A — APPROVED.

### Delivery findings (added during review)

- **Improvement (non-blocking, pre-existing tech debt — NOT in 47-7 scope):** `tests/server/test_magic_init.py:127-128` (lines from commit `89a66436` dated 2026-04-30) call `Path.write_text(...)` without `encoding="utf-8"`. Platform-default encoding violates Python lang-review Rule #5. File a separate cleanup story for the broader test-suite audit (likely many more sites across `tests/`).
- **Improvement (non-blocking):** Watcher-drain pattern in async tests uses fixed `await asyncio.sleep(0.05)` across 17+ files. Extracting a `drain_watcher(captured, *, expected_count, timeout=1.0)` poll-with-deadline helper would eliminate the timeout-flakiness category project-wide. Identified by reviewer-test-analyzer during 47-7 review; pattern is far older than this story. File as a clean test-infrastructure story.