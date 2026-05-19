---
story_id: "53-3"
jira_key: ""
epic: ""
workflow: "tdd"
---

# Story 53-3: Crash event handler: Composure→0 fires injury tag + Edge hit + dismount

## Story Details

- **ID:** 53-3
- **Jira Key:** N/A (SideQuest personal project, no Jira)
- **Epic:** Epic 53 — Road Warrior: Rig two-pool wiring + content alignment
- **Workflow:** tdd
- **Stack Parent:** none (independent)
- **Repo:** sidequest-server

## Story Context

Road Warrior's rig Composure pool (instantiated in 53-2) now needs a crash handler. When a character's rig Composure hits zero during play, three mechanical consequences fire:

1. **Injury tag** applied to the character
2. **Edge pool hit** (personal resilience damage as the rider is shaken)
3. **Dismount** (character dismounts from the rig, becoming a foot combatant)

The crash event must be detectable and emittable as OTEL span (53-4 adds GM-panel surface; 53-3 just fires the event). Per ADR-024 and ADR-078, Composure is the structural counterpart to Edge; when the vessel's Composure crosses zero, the rider pays in personal resilience.

### Context Files

- **Epic context:** `sprint/context/context-epic-53.md`
- **Predecessor (53-2):** `sprint/context/context-story-53-2.md`
- **RigComposurePool contract (53-1):** `sidequest-server/sidequest/game/rig_composure_pool.py`
- **ADR-024:** Dual-Track Tension Model (Composure as structural counterpart to Edge)
- **ADR-078:** Edge / Composure semantics
- **ADR-031:** OTEL emission requirements

## Sm Assessment

**Recommended approach:** RigComposurePool (53-1) exposes the contract; 53-2 instantiates it per rig. The crash event handler is a thin emitter that subscribes to (or is invoked at) the `composure → 0` boundary, then performs three side effects: injury tag application, Edge pool decrement, and dismount state transition. Emit a `rig_crash_event` payload that 53-4 will pick up for OTEL.

**Suggested seams:**
- `rig_composure_pool.py` — wire a single `on_zero` callback (or expose a `did_cross_zero()` predicate); don't bury logic inside the pool itself.
- Crash handler module under `sidequest/game/` (e.g. `rig_crash.py`) owns the three side effects, taking character + rig refs.
- Injury tags live on the character model (per ADR-007); reuse the existing tag mechanism, do not invent a new field.
- Edge pool decrement uses the existing EdgePool API (per ADR-078) — do not write raw HP-style math.
- Dismount is a state transition on the character/rig pairing — surface the API that 53-5 (UI) needs.

**TDD targets for TEA (red phase):**
1. Composure → 0 triggers exactly one crash event (idempotent if already at 0).
2. Injury tag is applied and is the genre-pack-defined value (not hardcoded).
3. Edge pool takes the documented hit amount (check Epic 53 context for the number).
4. Dismount transitions character off rig; rig state reflects "unmanned" or equivalent.
5. Negative tests: Composure > 0 does NOT fire crash; already-dismounted character does not re-fire.

**Watch for:**
- HP→Edge translation pattern at the materializer seam (per memory `project_hp_removed`). Content YAML may still reference HP-shaped fields.
- Don't bury bombs with null-checks (per memory `feedback_no_burying_bombs`) — if a rig has no rider, decide that at the model layer, not as a guard inside the crash handler.
- OTEL emission is 53-4's job; this story should leave a clean event hook for it, not emit spans directly.

**Workflow type:** phased tdd (7 phases). No blockers. Predecessors 53-1 and 53-2 landed yesterday.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-19T14:05:36Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-19T10:42:00Z | 2026-05-19T13:35:14Z | 2h 53m |
| red | 2026-05-19T13:35:14Z | 2026-05-19T13:44:56Z | 9m 42s |
| green | 2026-05-19T13:44:56Z | 2026-05-19T13:50:10Z | 5m 14s |
| spec-check | 2026-05-19T13:50:10Z | 2026-05-19T13:52:57Z | 2m 47s |
| verify | 2026-05-19T13:52:57Z | 2026-05-19T13:59:30Z | 6m 33s |
| review | 2026-05-19T13:59:30Z | 2026-05-19T14:04:26Z | 4m 56s |
| spec-reconcile | 2026-05-19T14:04:26Z | 2026-05-19T14:05:36Z | 1m 10s |
| finish | 2026-05-19T14:05:36Z | - | - |

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Test File:** `sidequest-server/tests/game/test_rig_crash_handler.py` (591 lines, 28 tests)
**Tests Written:** 28 tests covering 6 ACs (derived from story title + road_warrior rules.yaml)
**Status:** RED — all 28 fail with `ImportError` because `sidequest.game.rig_crash` module + `SPAN_RIG_POOL_CRASH_EVENT` constant don't exist yet.

### AC Coverage

| AC (derived) | Tests |
|--------------|-------|
| 1. Composure→0 fires exactly one crash, idempotent | `test_handle_rig_crash_is_idempotent_when_already_dismounted`, `test_apply_rig_damage_to_already_wrecked_rig_does_not_re_crash`, `test_handle_rig_crash_does_not_emit_span_on_idempotent_call` |
| 2. Driver Edge -1 | `test_handle_rig_crash_applies_minus_one_edge_to_driver`, `test_apply_rig_damage_lethal_damage_fires_crash` |
| 3. Injury tag (Wound severity) | `test_handle_rig_crash_appends_injury_status_with_wound_severity` |
| 4. Dismounted status (Scar severity) | `test_handle_rig_crash_appends_dismounted_status` |
| 5. OTEL `rig_pool.crash_event` span | `test_span_rig_pool_crash_event_constant_exposed`, `test_span_rig_pool_crash_event_is_flat_only`, `test_handle_rig_crash_emits_crash_event_span`, `test_handle_rig_crash_span_handles_none_location_and_attacker`, `test_handle_rig_crash_does_not_emit_span_when_rig_not_destroyed`, `test_apply_rig_damage_fires_crash_event_span_on_lethal_hit` |
| 6. Negative: not destroyed, no rig_pool, repeated calls | `test_handle_rig_crash_is_noop_when_rig_pool_is_none`, `test_handle_rig_crash_is_noop_when_rig_still_has_composure`, `test_apply_rig_damage_sublethal_damage_does_not_fire_crash`, `test_apply_rig_damage_returns_none_when_no_rig_pool`, `test_apply_rig_damage_rejects_negative_amount`, `test_apply_rig_damage_zero_amount_is_noop_with_no_crash` |
| Wiring (CLAUDE.md) | `test_apply_rig_damage_lethal_damage_fires_crash`, `test_apply_rig_damage_fires_crash_event_span_on_lethal_hit` (end-to-end damage→pool delta→crash handler→span) |

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #3 type annotations at boundaries | `test_handle_rig_crash_has_type_annotations`, `test_apply_rig_damage_has_type_annotations` | failing |
| #6 test quality (no vacuous asserts) | self-checked: every test asserts a specific value (no `assert True`, no `assert result` without value comparison) | self-check pass |
| #10 import hygiene (`__all__`) | `test_rig_crash_module_exports_all_public_symbols` | failing |
| #1 silent exceptions | (handler design forbids except: pass — tested via `test_apply_rig_damage_rejects_negative_amount` which expects loud `ValueError`) | failing |
| #2 mutable defaults | (no mutable defaults in handler signature — verified via type-annotation test reading `inspect.signature`) | n/a indirect |

**Rules checked:** 4 of 14 applicable lang-review rules have direct test coverage; remainder (#4 logging, #5 paths, #7 resources, #8 deserialization, #9 async, #11 input validation, #12 deps, #13 fix regressions, #14 cleanup ordering) are not applicable to a pure in-memory mutation+span emitter.
**Self-check:** 0 vacuous tests found.

### What Dev needs to build (green phase)

1. **`sidequest-server/sidequest/game/rig_crash.py`** — new module:
   - `INJURY_TEXT = "injury"`, `DISMOUNTED_TEXT = "dismounted"` (or equivalent constants)
   - `RigCrashResult(BaseModel)` with `character_id: str`, `chassis_id: str`, `edge_after: int`
   - `handle_rig_crash(core: CreatureCore, *, location: str | None = None, attacker: str | None = None) -> RigCrashResult | None`
   - `apply_rig_damage(core: CreatureCore, amount: int, *, location: str | None = None, attacker: str | None = None) -> RigDamageResult | None`
   - `RigDamageResult(BaseModel)` with at least `crash: RigCrashResult | None` field (tests only inspect `.crash`)
   - `__all__ = ["handle_rig_crash", "apply_rig_damage", "RigCrashResult", "RigDamageResult"]`
2. **`sidequest-server/sidequest/telemetry/spans/rig.py`**:
   - Add `SPAN_RIG_POOL_CRASH_EVENT = "rig_pool.crash_event"`
   - Add it to the `FLAT_ONLY_SPANS.update({...})` set
3. **`sidequest-server/sidequest/game/__init__.py`**: re-export `handle_rig_crash`, `apply_rig_damage`, `RigCrashResult` (mirror the 53-2 `bind_rig_pool_from_inventory` re-export pattern).

### Watch-outs for Dev

- **Idempotency key:** Tests use presence of a "dismounted" status as the idempotency signal (re-running on an already-dismounted core is a no-op). If you prefer a different signal (e.g. `rig_pool.is_destroyed() and ... `), make sure `test_handle_rig_crash_is_idempotent_when_already_dismounted` still passes — it pre-seeds via a fresh damage cycle, not via manual status injection.
- **Status append order:** Tests don't pin the relative order of injury vs dismounted, but they DO require both to be appended (not replaced — `test_handle_rig_crash_does_not_drop_existing_statuses` checks that a prior `Burned` Scar stays in the list).
- **OTEL attrs:** Tests assert `attrs["location"]` and `attrs["attacker"]` are coerced to `""` when None (matches the `magic.py` precedent that the rig.py module already references).
- **Negative amount in apply_rig_damage:** Test expects `ValueError`. Don't `abs()` or silently treat as healing.

### Handoff

To Dev (Major Charles Emerson Winchester III) for green phase. The implementation is mechanical — three new public functions, one new span constant, one re-export. No design decisions left except the two severity choices (see deviations) which Dev can adjust if Architect disagrees.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (3 notes — see below) | N/A — Reviewer manual analysis covers domains 2-9 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — Reviewer covered manually |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — Reviewer covered manually |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — Reviewer covered manually |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — Reviewer covered manually |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — Reviewer covered manually |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — Reviewer covered manually |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — Reviewer covered manually (also: verify phase already ran 3 simplify teammates) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — Reviewer ran lang-review/python.md manually |

**All received:** Yes (1 enabled + 8 disabled via `workflow.reviewer_subagents.*`)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

### Preflight Notes (informational, not findings)

- 3 pre-existing Pydantic `BaseModel` UserWarnings (field name `register` shadows parent attribute) in `confrontations.py`, `narrative.py`, `orbital/models.py` — predate this branch, untouched by 53-3.
- `apply_rig_damage` returns `None` for a rig-less character. Documented contract in docstring; future downstream callers (combat resolver, dogfight subsystem) must handle the `None` path. Not a 53-3 bug; flagged as a wiring contract for the next story.
- The `Span.open(...)` block in `rig_crash.py:107-116` wraps only a `pass` — empty body is intentional. Attrs are set in the `Span.open()` call; this is the established pattern across the entire `rig_pool.*` span family (`rig_composure_pool.py:98-107`, `:129-139`, `:142-151`) and the `rig.*` / `room.*` emit helpers (`telemetry/spans/rig.py:61-77, 87-98, 100-121, 123-145, 147-166`). Not a smell.

## Devil's Advocate

Trying to break the rig crash handler:

1. **Race condition on simultaneous `handle_rig_crash` calls.** Two concurrent calls could both pass the `_already_dismounted` guard before either appends "dismounted", resulting in double Edge damage and duplicate statuses. *Counterargument:* SideQuest serializes session writes via `tool_registry._write_locks` (see `apply_damage.py` docstring); session-level state is single-threaded by design. Safe in practice, but the invariant is undocumented at the rig_crash module level. Not a 53-3 blocker — this is a sessionwide architectural assumption.

2. **Brittle idempotency key.** `_already_dismounted` keys off the presence of a `"dismounted"` status. If a future voluntary-dismount mechanic also writes a `"dismounted"` status, a subsequent crash on that character would be silently skipped. The narrator-removal case is constrained (narrator can't directly delete statuses in current arch), but the voluntary-dismount case is plausible. *This was already flagged by Architect as a deferred forward-looking concern* — accepting that disposition.

3. **Born-at-zero pool reload.** A pool constructed at `current=0` (technically allowed by the model — the validator only requires `current ≤ max` and `max > 0`) would trigger `is_destroyed()` on the very first `handle_rig_crash` call after reload, applying Edge -1 and statuses to a character whose rig "wrecked" out of nowhere. *Counterargument:* the only path to a stored `current=0` is a real crash already having happened, in which case the saved snapshot also contains the `dismounted` status (handler short-circuits on `_already_dismounted`). The bind helper rejects content tags with `composure < 0`. The only way to hit this bug is hand-editing a save file — not a realistic threat model. Safe.

4. **Duplicate "injury" statuses.** A character already carrying an "injury" status from another source (future hand-crafted scenarios, content seed) would end up with two after a crash. The status list allows duplicates and the GM panel would show both. Acceptable per ADR-080 (narrative weight tags accumulate); the narrator picks a specific named injury. Not a bug.

5. **Span emission ordering vs side effects.** Edge delta, statuses, then span — if the OTEL tracer raised, Edge and statuses would already be mutated and an exception propagates. *Counterargument:* the existing `rig_pool.*` family (53-1) has the same pattern (`apply_delta` mutates `self.current` then opens the delta span); if this is broken it's broken everywhere and 53-3 isn't where to fix it.

6. **Negative damage as healing.** `apply_rig_damage(core, -1)` raises `ValueError`. Good — no silent `abs()`. But the symmetric question: is there a `heal_rig` API for repair? Not in 53-3 scope. Content rules.yaml describes "scars" (repair narrative history); a future repair story will own that. Acceptable.

7. **What if `pool.character_id` and `core.name` diverge?** The pool was bound with `character_id=core.name`, but if `core.name` later mutates, the pool's character_id is stale. *Counterargument:* character names aren't a mutable runtime field in the current architecture. Bind invariant preserved.

8. **What does pyright say?** Type annotations are complete; `RigDamageResult.crash: RigCrashResult | None` is correctly nullable; pool guards use `if pool is None` so type narrowing is sound. No `# type: ignore` in the diff. Clean.

**Result of Devil's Advocate:** All hypothetical bombs are either (a) already documented by Architect's forward-looking concern, (b) prevented by a higher-level architectural invariant outside 53-3's scope, or (c) not realistic threat models. No new findings.

## Reviewer Assessment

**Verdict:** APPROVED

### Rule Compliance (lang-review/python.md applied to the diff)

| # | Rule | Status | Evidence |
|---|------|--------|----------|
| 1 | Silent exception swallowing | Pass | No `try/except` in any new code |
| 2 | Mutable default arguments | Pass | `location=None, attacker=None` — None is immutable; no `[]`/`{}` defaults |
| 3 | Type annotations at boundaries | Pass | `handle_rig_crash`, `apply_rig_damage`, `RigCrashResult.*`, `RigDamageResult.*` all annotated; verified by `test_*_has_type_annotations` |
| 4 | Logging coverage and correctness | N/A | No `logging`/`structlog` imports — OTEL spans serve the observability role per CLAUDE.md OTEL principle |
| 5 | Path handling | N/A | No filesystem ops |
| 6 | Test quality | Pass | 28 tests, all assert specific values; no `assert True`, no truthy-only checks, no skipped tests, no parametrize-all-same-path |
| 7 | Resource leaks | Pass | `Span.open(...)` used as context manager (`with` block); no bare resource acquisition |
| 8 | Unsafe deserialization | N/A | No pickle/eval/yaml.load on untrusted input |
| 9 | Async/await pitfalls | N/A | All synchronous |
| 10 | Import hygiene | Pass | `__all__` declared in `rig_crash.py:158-166`; no star imports; no circular imports (verified by all tests passing without ImportError) |
| 11 | Input validation at boundaries | Pass | `apply_rig_damage` raises `ValueError` on negative amount (line 142-143); pool's own validators reject blank IDs and negative composure |
| 12 | Dependency hygiene | N/A | No new dependencies |
| 13 | Fix-introduced regressions | N/A | No fix in this diff — fresh code |
| 14 | State cleanup ordering | Pass | No register-after-clear patterns; status appends are pure mutations followed by span emission (no consumed-queue invariant) |

### Domain Coverage (manual, since 8 subagents disabled)

- `[VERIFIED]` **Edge-case enumeration** — `rig_crash.py:78-122`: three guards (None pool, not destroyed, already dismounted) cover all branches into the consequence block. Boundary cases tested: composure=2 / damage=5 (overkill), composure=2 / damage=2 (exact), composure=4 / damage=2 (sublethal), composure=0 / damage=3 (no-re-crash), damage=0 (no-op zero), damage=-1 (raises). All paths exercised.

- `[VERIFIED]` **Silent failures** — `rig_crash.py`: no `try/except`, no `suppress()`, no fallback strings. `apply_rig_damage` returns `None` for missing pool but this is documented contract (`rig_crash.py:134-137`), not a silent fallback — the caller explicitly chose this API. CLAUDE.md "no silent fallbacks" addresses "the alternative path is wrong" cases; here the contract IS "no rig means no-op."

- `[VERIFIED]` **Test quality** — `tests/game/test_rig_crash_handler.py`: 28 tests, every assertion checks a specific value or set membership. `test_handle_rig_crash_does_not_drop_existing_statuses` proves the append semantics. Tests run in 0.04s — no slow tests, no flaky patterns.

- `[VERIFIED]` **Comments/documentation** — Module docstring (`rig_crash.py:1-24`) references the authoritative spec source (`rules.yaml` `crash_event` + `rig_composure_spec`). Each public function has a docstring covering no-op branches and the side effects. No stale TODOs, no orphaned references.

- `[VERIFIED]` **Type design** — `RigCrashResult` and `RigDamageResult` are pydantic `BaseModel`s without `extra='forbid'`. This matches the existing precedent for in-process result types (`RigComposureDeltaResult` in `rig_composure_pool.py:38-50` also omits forbid). Save-surface models in the same module DO use forbid; these don't because they're return values, not save state. Type-narrowing on `pool is None` correctly narrows below the guard.

- `[VERIFIED]` **Security** — No user input boundary in this module; called by future server-side game systems with already-validated state. OTEL attrs (`character_id`, `chassis_id`, `location`, `attacker`) are game-side identifiers, not credentials. No injection, no auth bypass, no info leakage.

- `[VERIFIED]` **Simplifier** — Verify phase already ran three simplify teammates (efficiency: clean, quality: clean, reuse: one stylistic finding overridden with documented rationale). I reviewed the override (extract `emit_rig_pool_crash_event` helper) and agree with TEA's decision: the `rig_pool.*` family already uses inline `Span.open` from owning modules (`rig_composure_pool.py`), and following that family precedent is at least as defensible as following the unrelated `rig.*` / `room.*` emit-helper pattern.

- `[VERIFIED]` **Project rule compliance** — Exhaustive lang-review/python.md table above. All applicable rules pass.

- `[VERIFIED]` **Wiring** — `apply_rig_damage` is the production-facing seam exported via `sidequest.game.__init__.py`. End-to-end test `test_apply_rig_damage_fires_crash_event_span_on_lethal_hit` exercises damage → pool → handler → span. TEA's Delivery Finding noting `apply_damage` tool doesn't yet route through `apply_rig_damage` is correctly scoped as a follow-up — 53-3's title is "Crash event handler," and Architect verified the scoping decision. **The new code is reachable from a non-test public-API entry point, satisfying the CLAUDE.md "Verify Wiring" rule at the right granularity for this story.**

### Deviation Audit (stamps below in `## Design Deviations`)

All three TEA-logged deviations stamped ACCEPTED. Dev "no deviations" stamped ACCEPTED. No undocumented spec drift found by Reviewer.

### Summary

Zero Critical, zero High, zero Medium findings. Implementation matches the `road_warrior/rules.yaml` `crash_event` + `rig_composure_spec` contract one-to-one; deviations are well-reasoned and authority-anchored; one architectural concern (status-presence idempotency key) is correctly deferred for the future voluntary-dismount mechanic; lang-review/python.md fully passes; preflight clean; 28/28 implementation tests + 301-test rig+telemetry regression sweep all green.

**Handoff:** To SM (Hawkeye Pierce) for finish.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (28/28 implementation tests pass, ruff clean across all four changed files)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4 (`sidequest-server/sidequest/game/__init__.py`, `sidequest-server/sidequest/game/rig_crash.py`, `sidequest-server/sidequest/telemetry/spans/rig.py`, `sidequest-server/tests/game/test_rig_crash_handler.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | findings | 1 high (disputed — see below), 1 low (deferred) |
| simplify-quality | clean | naming, type safety, error handling, no dead code, project conventions all pass |
| simplify-efficiency | clean | no premature abstraction, no over-parameterized functions, no redundant operations |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings
**Noted (not applied):** 2 findings (one high overridden to low, one already-low)
**Reverted:** 0

**Overall:** simplify: clean (one disputed high-confidence finding examined and intentionally not applied)

### Disputed High-Confidence Finding — Override Rationale

simplify-reuse flagged `sidequest/game/rig_crash.py:107` as high-confidence: "extract `emit_rig_crash_event()` to `telemetry/spans/rig.py` following the established emitter pattern (5 existing `emit_*` functions in the same module)."

**Override to low-confidence / do not apply.** The simplify-reuse agent missed that the five existing `emit_*` helpers in `rig.py` all belong to the `rig.*` and `room.*` span families. The `rig_pool.*` family (`created` / `delta` / `zero_crossing`) does **not** use `emit_*` helpers — it emits inline `Span.open(...)` from the owning module (`rig_composure_pool.py`). The new `rig_pool.crash_event` (this story) follows the *family-level* precedent (inline emission from the consequence module) rather than the *module-level* precedent (emit_ helpers). Extracting a helper would make 53-3 the outlier within the `rig_pool.*` family while only restoring symmetry with unrelated `rig.*` / `room.*` events.

Refactor cost (one new emit function + signature) vs. benefit (cosmetic, breaks one symmetry to gain another) is a wash, and verify phase is the wrong place to churn the diff for a stylistic call.

### Deferred Low-Confidence Finding

simplify-reuse also suggested a shared `has_status(core, text, exact=True)` helper in `game/status.py` or `game/creature_core.py`. Confidence: low. **Deferred** — only two call sites total (one in `rig_crash._already_dismounted`, one in test assertions), too thin to justify a shared utility yet. Re-evaluate if a third call site appears.

### Quality Checks

- `uv run pytest -v tests/game/test_rig_crash_handler.py`: 28/28 pass
- `uv run ruff check` on all three modified production files: clean
- 301-test rig+telemetry regression sweep from Dev's green phase: still clean (no changes since)

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with one minor forward-looking concern noted below)
**Mismatches Found:** 0 structural — implementation matches the road_warrior `rules.yaml` `crash_event` + `rig_composure_spec` contract one-to-one.

### AC-by-AC Verification

Checked the green code against `sidequest-content/genre_packs/road_warrior/rules.yaml` (the authoritative spec — story-context file is missing so content rules + epic context + session SM Assessment are the substitute hierarchy):

| Spec demand (rules.yaml) | Code (`sidequest/game/rig_crash.py`) | Verdict |
|---|---|---|
| "apply -1 Edge … to the driver" | `core.apply_edge_delta(DRIVER_EDGE_HIT)` with `DRIVER_EDGE_HIT = -1` | Aligned |
| "+ 1 injury tag to the driver" (injuries persist beyond scene per `injury_system`) | `Status(text="injury", severity=StatusSeverity.Wound)` appended | Aligned |
| "write the dismounted status" (recovery "a story arc, not a shopping trip") | `Status(text="dismounted", severity=StatusSeverity.Scar)` appended | Aligned |
| "handler MUST emit OTEL span `rig_pool.crash_event` with {rig_slug, location, attacker}" | `Span.open(SPAN_RIG_POOL_CRASH_EVENT, attrs={character_id, chassis_id, location, attacker})` — chassis_id is the canonical name for rig_slug per the rig_pool.* span family | Aligned |
| "Crash event hook (Composure crosses 0 downward)" — fires only on downward zero-crossing | `apply_rig_damage` reads `pool_result.zero_crossed` (the pool's downward-only edge trigger from 53-1) before invoking the handler | Aligned |
| Idempotent on already-wrecked rig | Three-guard short-circuit in `handle_rig_crash` (None pool / not destroyed / already dismounted); pool's own `zero_crossed` returns False for re-zero | Aligned |
| Wiring test reachable from production code | `apply_rig_damage` is the public seam, re-exported from `sidequest.game`; tests exercise the damage→pool→handler→span end-to-end | Aligned |

### Deviation Review (TEA + Dev entries)

Reviewed the three TEA deviations and Dev's "no deviations" entry. Findings:

1. **OTEL span emission contradicts SM Assessment.** TEA picked content spec + ADR-031 / CLAUDE.md OTEL principle over SM Assessment's "no spans directly" heuristic. **Architect verdict: correct call.** Content `rules.yaml` is authoritative for road_warrior mechanics, and the OTEL principle is a CLAUDE.md hard rule. SM Assessment is not in the spec authority hierarchy — it's a planning heuristic. Deviation properly logged, no action required.

2. **Severity choices (Wound for injury, Scar for dismounted).** Derived interpretively from rules.yaml prose ("heals in 2 sessions / medical care" ≈ Wound; "story arc, not a shopping trip" ≈ Scar). **Architect verdict: defensible.** The content text doesn't enumerate severities; TEA picked the closest enum match to the narrative pacing language. If the road_warrior playtest reveals these clear too fast or too slow, the constants are exported (`DISMOUNTED_STATUS_TEXT`, `INJURY_STATUS_TEXT`) and the severity mapping is a one-line edit. Deviation properly logged, no action required.

3. **`apply_rig_damage` as new public seam (not retrofitting `apply_damage` tool).** Keeps 53-3 scope at the handler + a public seam, defers narrator-tool damage routing to a follow-up. **Architect verdict: correct scoping.** The story title is "Crash event handler" — adding rig-pool-aware damage routing to `agents/tools/apply_damage.py` would expand to a multi-system change. The seam preserves the wiring invariant (CLAUDE.md "Verify Wiring, Not Just Existence") because `apply_rig_damage` is the consumer-facing production API ready for the dogfight subsystem / combat resolver to call. TEA's Delivery Finding flags the follow-up — that's the right channel. No action required.

### Forward-Looking Concern (not a mismatch)

- **Idempotency key conflates voluntary vs crash dismount.** The handler uses presence of a `"dismounted"` status as the "already fired" signal. If a future mechanic introduces voluntary dismount (player choosing to leave the rig without crashing), that mechanic would also have to write a `"dismounted"` status (per the content `stat_display_fields: dismounted` convention) — and would then block a subsequent crash from firing on the same character. **Severity: minor / deferred.** There is no voluntary-dismount mechanic in any current story, and the cleanest forward fix is to introduce a separate signal (e.g. `Status(text="crash-dismounted", ...)` distinct from `"dismounted"`, OR a `CreatureCore.is_mounted` boolean once mount/dismount becomes a first-class state) at the point the voluntary mechanic is designed. **Recommendation: Option D (defer)** — flag for the future mount/dismount story; do not block 53-3.

### Decision

**Proceed to review.** No hand-back to Dev required. Implementation is clean, deviations are well-reasoned and properly authority-anchored, and the one forward-looking architectural concern is appropriately small and isolated.

**Handoff:** To TEA (Radar O'Reilly) for verify phase.

## Dev Assessment

**Phase:** finish
**Implementation Complete:** Yes
**Tests:** 28/28 passing (GREEN). 301-test rig+telemetry regression sweep clean.

**Files Changed:**
- `sidequest-server/sidequest/game/rig_crash.py` (new, 166 lines) — `handle_rig_crash`, `apply_rig_damage`, `RigCrashResult`, `RigDamageResult`, plus three exported constants (`INJURY_STATUS_TEXT`, `DISMOUNTED_STATUS_TEXT`, `DRIVER_EDGE_HIT`).
- `sidequest-server/sidequest/telemetry/spans/rig.py` — added `SPAN_RIG_POOL_CRASH_EVENT = "rig_pool.crash_event"` constant, registered in `FLAT_ONLY_SPANS`.
- `sidequest-server/sidequest/game/__init__.py` — re-exported the four new public symbols.

**Branch:** `feat/53-3-rw-crash-handler` pushed to `origin`.

**Commits:**
- `d203b78` test(53-3): add failing tests for rig crash handler (TEA red)
- `45a378b` feat(53-3): implement rig crash handler — Composure→0 fires injury + Edge -1 + dismount

**Self-review (judgment checks):**
- [x] Code is wired — `apply_rig_damage` is the public seam, `handle_rig_crash` is the consequence layer, both exported through `sidequest.game`. TEA flagged the follow-up that `apply_damage` tool should call `apply_rig_damage` when mounted (non-blocking, separate story).
- [x] Follows project patterns — Pydantic v2 BaseModel for result types, `Span.open` context manager + None-coercion to `""` matching the `magic.py` / `rig.py` precedent, `__all__` declared per lang-review rule #10.
- [x] All acceptance criteria met — all 28 TEA tests green, covering all 6 derived ACs + wiring + lang-review rules.
- [x] Error handling — `apply_rig_damage` raises `ValueError` on negative amounts (no silent `abs()`); other no-op paths return `None` deliberately rather than raising (caller-friendly seam).

**Handoff:** To Architect (Major Margaret Houlihan) for spec-check phase.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Gap** (non-blocking): Story context file `sprint/context/context-story-53-3.md` was not created during sm-setup. Affects `sprint/context/` (sm-setup should generate per-story context for tdd workflow, but only epic-53 and predecessor story contexts exist). *Found by TEA during test design.*
- **Gap** (non-blocking): No production caller of `RigComposurePool.apply_delta` exists yet — `agents/tools/apply_damage.py:80` still routes all damage straight to `core.edge`, ignoring `core.rig_pool` even when present. Affects `sidequest-server/sidequest/agents/tools/apply_damage.py` (a follow-up story should detect mounted state and call the new `apply_rig_damage` helper before falling back to direct Edge damage). *Found by TEA during test design.*

### Dev (implementation)

- No upstream findings during implementation. TEA's test design was complete and the implementation matched the test contract one-to-one; the two gaps TEA already flagged (missing story-context file and `apply_damage` tool not yet routing through `apply_rig_damage`) cover everything I noticed during the green phase.

### TEA (test verification)

- No upstream findings during verify phase. Three simplify teammates ran; quality and efficiency were clean; reuse flagged a stylistic refactor that I evaluated and did not apply (see TEA Assessment "Disputed High-Confidence Finding"). No new gaps or conflicts surfaced.

### Reviewer (code review)

- No upstream findings during code review. Implementation, tests, and prior-phase assessments are coherent and well-anchored to spec. The two non-blocking forward-looking concerns (status-presence idempotency key brittleness if voluntary dismount is added; `apply_damage` tool not yet routing through `apply_rig_damage`) were already captured by TEA and Architect — no new entries needed.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- No deviations from spec. TEA's tests defined a complete, internally-consistent contract; I implemented exactly what they demanded with no additions, no shortcuts, and no scope creep. The two severity choices (Wound for injury, Scar for dismounted) and the OTEL-emission decision were already pinned by TEA's deviation entries — I followed those judgments without challenge.

### TEA (test verification)

- No deviations from spec during verify phase. Three simplify teammates reported (efficiency: clean, quality: clean, reuse: 1 high + 1 low). The one high-confidence simplify-reuse finding (extract `emit_rig_pool_crash_event` helper) was reviewed and **not applied** — see TEA Assessment "Simplify Report" for rationale. No code changes during verify, so no spec drift to log.

### Architect (reconcile)

Verified each prior deviation entry against the actual code, the cited spec sources, and the downstream story assumptions. All 4 in-flight entries (3 TEA-design + 1 TEA-verify + 1 Dev) are factually accurate as written. Reviewer's 6 audit stamps are sound.

- **Verified accuracy of TEA deviation 1 (OTEL emission):** Spec source `sidequest-content/genre_packs/road_warrior/rules.yaml` exists; quoted text appears verbatim at `custom_rules.rig_composure_spec` (lines 157-161). Implementation at `sidequest-server/sidequest/game/rig_crash.py:107-116` emits `SPAN_RIG_POOL_CRASH_EVENT` with the documented attrs. Forward impact "53-4 builds GM-panel visualization around the span" is accurate — 53-4 is the OTEL dashboard surface story and will hang dashboards off this span name without needing to add the emission itself. No correction needed.

- **Verified accuracy of TEA deviation 2 (severity choices — Wound for injury, Scar for dismounted):** Spec source `rules.yaml` `injury_system` (lines 163-181) describes injuries as "heals in 2 sessions / medical care" — interpretive mapping to `StatusSeverity.Wound` ("clears at session end or with rest") is the closest enum match. `dismounted_rules` (lines 227-233) describes recovery as "a story arc, not a shopping trip" — interpretive mapping to `StatusSeverity.Scar` ("persists until milestone or healing event") is the closest enum match. Constants `INJURY_STATUS_TEXT` and `DISMOUNTED_STATUS_TEXT` are exported from `sidequest.game` so a future severity tweak is one-line. Forward impact "if changed in green, one-line test edit" is accurate. No correction needed.

- **Verified accuracy of TEA deviation 3 (`apply_rig_damage` as new seam, not retrofitting `apply_damage` tool):** Implementation at `sidequest-server/sidequest/game/rig_crash.py:125-155` exposes the new seam; `sidequest-server/sidequest/agents/tools/apply_damage.py:80` still routes damage directly to Edge (confirmed via grep). Forward impact "a follow-up story should wire `apply_damage` … to call `apply_rig_damage` when the target is mounted" is accurate and matches the Delivery Finding TEA already filed. No correction needed.

- **Verified accuracy of Dev "no deviations" entry:** Confirmed by my own spec-check + Reviewer's audit + line-by-line diff review. Implementation matches the test contract one-to-one with no scope creep. No correction needed.

- **Verified accuracy of TEA "no deviations from spec during verify phase":** Confirmed — no code changes during verify, the disputed simplify-reuse finding was overridden with documented family-precedent rationale. No correction needed.

- **No additional deviations found.** The crash handler implementation, span constant, and wiring seam are all spec-aligned. My spec-check forward-looking concern (status-presence idempotency key conflates voluntary vs crash dismount) is an architectural observation about a future-state mechanic, not a 53-3 spec deviation — appropriately classified as deferred.

- **AC deferral verification:** No ACs were deferred during this story. The 6 ACs TEA derived from `rules.yaml` (Composure→0 fires once / Edge -1 / injury Wound / dismounted Scar / OTEL crash_event / negative cases) plus the wiring AC are all DONE — confirmed by 28/28 green tests. AC accountability is complete; no descoped or deferred ACs to justify.

### Reviewer (audit)

- TEA "OTEL span emission" deviation → ✓ ACCEPTED by Reviewer: agrees with TEA's authority hierarchy reasoning — content `rules.yaml` + CLAUDE.md OTEL principle outweigh the SM Assessment heuristic.
- TEA "Severity choices (Wound/Scar)" deviation → ✓ ACCEPTED by Reviewer: interpretation of the rules.yaml prose is defensible; the chosen severities match the narrative pacing semantics ("heals in sessions" → Wound; "story arc to recover" → Scar). Constants are exported so a future severity tweak is a one-line change.
- TEA "`apply_rig_damage` as new seam (not retrofitting `apply_damage` tool)" deviation → ✓ ACCEPTED by Reviewer: correct scoping decision. The 53-3 story title is "Crash event handler" — damage routing through the narrator tool is a separate concern. Public seam preserves the wiring invariant for future callers.
- Dev "no deviations" entry → ✓ ACCEPTED by Reviewer: confirmed by line-by-line diff review — implementation matches TEA test contract one-to-one with no scope creep.
- Architect "no missed deviations" (spec-check phase) → ✓ ACCEPTED by Reviewer: confirmed. No additional drift found by Reviewer during code review either.
- TEA (verify) "no deviations from spec during verify phase" → ✓ ACCEPTED by Reviewer: confirmed — no code changes during verify, and the disputed simplify-reuse finding was correctly overridden with documented rationale.

### TEA (test design)

- **Crash handler emits its own OTEL `rig_pool.crash_event` span (contradicts SM Assessment)**
  - Spec source: `sidequest-content/genre_packs/road_warrior/rules.yaml` `custom_rules.rig_composure_spec`
  - Spec text: "The handler MUST emit OTEL span `rig_pool.crash_event` with {rig_slug, location, attacker} per ADR-031"
  - Implementation: Tests require the 53-3 handler to emit `SPAN_RIG_POOL_CRASH_EVENT` directly (with character_id/chassis_id/location/attacker attrs). SM Assessment said "leave a clean event hook, not emit spans directly" with 53-4 owning OTEL — I picked the content rules + CLAUDE.md OTEL principle ("every backend fix that touches a subsystem MUST add OTEL watcher events") over the SM Assessment.
  - Rationale: Content authors are the spec authority for road_warrior mechanics, and the CLAUDE.md OTEL principle is non-negotiable: subsystems without spans are GM-panel blind spots and let the narrator gaslight unchecked. 53-4 will add the GM-panel surface AROUND this span (deltas + crash dashboards), not invent the span itself. The pool already emits `rig_pool.created` / `.delta` / `.zero_crossing` (53-1); adding `.crash_event` follows the same precedent rather than deferring to 53-4.
  - Severity: minor (additive — the hook still exists; 53-4 can also still extend)
  - Forward impact: 53-4 builds GM-panel visualization around the span 53-3 emits instead of having to add the emission at the handler call site

- **Severity choices for injury (Wound) and dismounted (Scar) statuses are interpretive, not literal spec**
  - Spec source: `sidequest-content/genre_packs/road_warrior/rules.yaml` `injury_system` + `dismounted_rules`
  - Spec text: injuries "heal in 2 sessions / medical care"; dismounted recovery is "a story arc, not a shopping trip"
  - Implementation: Tests pin `StatusSeverity.Wound` for injury (multi-session = closer to Wound's "session end / rest" than Scratch's "scene end") and `StatusSeverity.Scar` for dismounted ("story arc" = milestone-gated, matches Scar's "until milestone or healing event").
  - Rationale: Content text doesn't name severities; I picked the closest enum match to the prose. Dev or Architect can push back during green if the road_warrior pacing wants different severities.
  - Severity: minor
  - Forward impact: if changed in green, the injury_status / dismounted_status tests need a one-line edit (severity enum constant)

- **Wiring seam is a new `apply_rig_damage` helper rather than retrofitting `agents/tools/apply_damage.py`**
  - Spec source: Story scope ("Crash event handler"); CLAUDE.md "Every Test Suite Needs a Wiring Test"
  - Spec text: Story title scopes to "Crash event handler … fires injury tag + Edge hit + dismount" — does not require damage-routing.
  - Implementation: Tests demand a `sidequest.game.apply_rig_damage(core, amount, *, location, attacker)` production function that combines `RigComposurePool.apply_delta(-N)` with the crash handler, so the handler has a non-test consumer (wiring-test requirement). I deliberately did NOT expand scope to modify `apply_damage` tool to route through rig_pool — that's a follow-up.
  - Rationale: Without `apply_rig_damage` the handler has zero production callers (the existing `apply_damage` tool routes only to Edge), violating CLAUDE.md "Verify Wiring, Not Just Existence". Adding a public seam keeps 53-3 scope tight while preserving the wiring invariant. The narrator-tool integration (rig_pool-aware damage routing) is a clean follow-up story.
  - Severity: minor (additive new public API)
  - Forward impact: a follow-up story should wire `apply_damage` (or the dogfight resolver) to call `apply_rig_damage` when the target is mounted