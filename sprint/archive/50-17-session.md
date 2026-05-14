---
story_id: "50-17"
jira_key: ""
epic: "50"
workflow: "tdd"
---

# Story 50-17: Journal: KnownFact.confidence enum promotion — Literal[Certain|Suspected|Rumored|Discovered] (J-4 per ADR-100)

## Story Details

- **ID:** 50-17
- **Jira Key:** None (no Jira in this project)
- **Epic:** 50 (Pingpong-archive triage and dropped-work cleanup)
- **Workflow:** tdd
- **Stack Parent:** none (no dependencies)

## Story Overview

Per ADR-100 table row "50-17 — `KnownFact.confidence` enum promotion," this story promotes the `KnownFact.confidence` field from `str = "confirmed"` to a `Literal["Certain", "Suspected", "Rumored", "Discovered"]` for type safety and mechanical clarity. The UI already has a `Confidence` enum at `sidequest-ui/src/GameStateProvider.tsx:32`; this story mirrors that enum on the server side and migrates existing call sites.

**ADR-100 Context:** This is story J-4 in the journal pipeline coherence restoration. It is a straightforward refactor/type-safety task that unblocks stories 50-14 (JOURNAL_REQUEST handler), 50-15 (UI fact_id respect), and 50-16 (UI confidence propagation) by establishing the mechanical ground truth for confidence values throughout the stack.

**Points:** 1 (refactor/type safety)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-14T11:47:46Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-14T11:02:08Z | 2026-05-14T11:03:41Z | 1m 33s |
| red | 2026-05-14T11:03:41Z | 2026-05-14T11:09:59Z | 6m 18s |
| green | 2026-05-14T11:09:59Z | 2026-05-14T11:15:17Z | 5m 18s |
| spec-check | 2026-05-14T11:15:17Z | 2026-05-14T11:19:30Z | 4m 13s |
| verify | 2026-05-14T11:19:30Z | 2026-05-14T11:34:26Z | 14m 56s |
| review | 2026-05-14T11:34:26Z | 2026-05-14T11:40:55Z | 6m 29s |
| spec-reconcile | 2026-05-14T11:40:55Z | 2026-05-14T11:47:46Z | 6m 51s |
| finish | 2026-05-14T11:47:46Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Improvement** (non-blocking): `JournalEntry.confidence` in `sidequest-server/sidequest/protocol/models.py:127` is still `confidence: str` even though the docstring already lists the same 4-value vocabulary. `JournalEntry` is derived 1:1 from `KnownFact` per its own docstring; tightening `KnownFact.confidence` to `Literal[...]` without doing the same on `JournalEntry` leaves a type-narrowing gap at the wire boundary. Affects `sidequest/protocol/models.py:127` (mirror the same `Literal["Certain", "Suspected", "Rumored", "Discovered"]`). Out of this story's strict scope (1pt, `KnownFact` only) — recommend a follow-up sliver or a Dev judgment call during GREEN whether to include. *Found by TEA during test design.*

- **Conflict** (non-blocking): The UI `Confidence` type at `sidequest-ui/src/providers/GameStateProvider.tsx:32` is `'Certain' | 'Suspected' | 'Rumored'` — only 3 values, missing `'Discovered'`. ADR-100 row 50-17 claims the server enum "mirrors UI Confidence enum already in `GameStateProvider.tsx:32`," but the mirror is actually 3-of-4. Since `ScenarioClueIntake` already mints `KnownFact(confidence='Discovered', ...)` server-side and that value will reach the UI through the `JOURNAL_RESPONSE` channel landed by 50-14, the UI will start receiving a confidence string it cannot type-narrow. Affects `sidequest-ui/src/providers/GameStateProvider.tsx:32` and `sidequest-ui/src/types/payloads.ts:672` (a third, lower-case `Confidence` definition that also omits Discovered). Recommend a follow-up UI story to add `'Discovered'` (and rationalise the two conflicting UI definitions). *Found by TEA during test design.*

- **Gap** (non-blocking): Existing test `tests/server/test_scenario_accusation_intake.py:299` constructs a `KnownFact` with `confidence="confirmed"`. That test will fail after GREEN. Dev must migrate it as part of GREEN's "migrate existing call sites" step. Affects `tests/server/test_scenario_accusation_intake.py:299` (replace with a canonical value — likely `"Certain"`). *Found by TEA during test design.*

### Dev (implementation)

- **Improvement** (non-blocking): `sidequest/server/dispatch/scenario_accusation.py:107` has a stale comment ("parallel iteration is the deterministic fallback until 50-17 lands") that conflates this story (the confidence enum promotion) with the deferred work of giving `KnownFact` an originating-clue-id field. Story 50-17 does not "land" that fallback — the parallel-iteration scheme is still in place. Affects `sidequest/server/dispatch/scenario_accusation.py:107` (update the comment to reference the actual future story / ADR-053 restoration item, or drop the dated reference). *Found by Dev during implementation.*

- **Improvement** (non-blocking): `sidequest/server/dispatch/scenario_accusation.py:118` (`if fact.confidence not in _SUPPORTED_CONFIDENCES`) became redundant after the Literal promotion — pydantic will already reject any non-canonical value at `KnownFact` construction, so this runtime check can never fail. Defensive-but-dead code. Affects `sidequest/server/dispatch/scenario_accusation.py:35-41,118-119` (could be deleted once Reviewer agrees the boundary is truly closed). *Found by Dev during implementation.*

- **Gap** (non-blocking, found by TEA, confirmed by Dev): `tests/handlers/test_journal_request_handler.py` had **five** KnownFact fixtures using legacy/lowercase confidence values, not just the one TEA originally flagged. All migrated in this commit. Future story-50-17-style migrations should sweep with a broader grep — the legacy `"confirmed"` literal AND lowercase `"suspected"`/`"rumored"` were both in play. *Found by Dev during implementation.*

- **Question** (non-blocking): `tests/handlers/test_journal_request_handler.py:650` constructs a `JournalEntry` payload dict with `"confidence": "confirmed"` (not a `KnownFact`). Left untouched because `JournalEntry.confidence` is still `str` (out of this story's scope per TEA's first delivery finding). If a follow-up tightens `JournalEntry.confidence` to the same Literal, that line will need migration too. Affects `tests/handlers/test_journal_request_handler.py:650`. *Found by Dev during implementation.*

### TEA (test verification)

- **Gap** (non-blocking, deferred): `just check-all` `client-test` stage has 30 pre-existing vitest failures across the dice subsystem (`DiceOverlay.test.tsx`, `InlineDiceTray.test.tsx`, `deterministicReplay.test.tsx`, `dice-overlay-wiring-34-5.test.ts`, `character-creation-wiring.test.tsx`). Stack traces point into `../../dice-lib/src/DiceScene.tsx:256` with errors like `object.updateWorldMatrix is not a function` and `Cannot read properties of undefined (reading 'simulateOpen')` — Three.js / Rapier integration breakage in the locally-linked `dice-lib` package. Reproduced on a clean `develop` checkout (20/24 fails in `DiceOverlay.test.tsx` alone), confirming pre-existing breakage unrelated to story 50-17 (server-only). Affects `dice-lib` package (`/Users/slabgorb/Projects/dice-lib`) and the UI dice consumers. Recommend a separate story to bisect when the dice tests regressed and restore them — likely a peer-dep version mismatch after a recent Three.js/Rapier bump. *Found by TEA during test verification.*

- **Improvement** (non-blocking): `tests/server/test_chargen_persist_and_play.py::test_chargen_confirm_persists_deduped_inventory` had a one-shot failure in the first `just check-all` run during verify but passed on re-run and in isolation. Smells like test-isolation contamination — some upstream test in the suite leaves state that bleeds into chargen persistence. Not a 50-17 regression (the test never even references `KnownFact.confidence`), but worth a dedicated flake-hunt. Affects `tests/server/test_chargen_persist_and_play.py` (likely needs an isolating fixture or a `pytest -p random_order` reproduction). *Found by TEA during test verification.*

- **Improvement** (non-blocking, repository hygiene): The `sidequest-ui` subrepo was found locally checked out on the stale `feat/50-16-journal-ui-confidence` branch (50-16 was already merged on 2026-05-13). Synced to `develop` during verify to unblock `client-typecheck` (which now passes — origin had `d52a3da fix(types): use unknown-bridge cast on GameMessage → Record (#239)` that resolved the TS2352 errors). Per [[feedback_subrepo_branches]] / [[feedback_oq1_oq2_dual_repos]], post-merge subrepo cleanup is a known recurring chore. No code change recommended — just noting that the next sprint-housekeeping pass should `git switch develop && git pull` across subrepos. *Found by TEA during test verification.*

### Reviewer (code review)

- No upstream findings from Reviewer beyond what is already captured by other agents. All four blocking-fix items in the Reviewer Assessment are bounded in-scope cleanups to the 50-17 diff; they will be addressed by Dev on hand-back and do not represent upstream gaps in the project. The five "deferred" items listed under the Reviewer verdict are all already in TEA / Dev delivery findings above. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### TEA (test verification)
- No deviations from spec.

### Reviewer (audit)
- No undocumented deviations. TEA and Dev deviation entries above are all ✓ ACCEPTED.

### Architect (reconcile)

- **No additional deviations found.**

**Audit summary (definitive manifest for the boss):**

Verified each prior subsection for the six-field deviation format and substantive accuracy:

- **TEA (test design): "No deviations from spec."** — Verified. SM Assessment listed five ACs; TEA's RED phase produced `tests/game/test_known_fact_confidence.py` with 13 test functions across all five (AC1 canonical acceptance, AC2 rejection of unknown/legacy/mis-cased/empty/None, AC3 JSON round-trip, AC4 canonical default, AC5 `model_validate(dict)` boundary). Plus the Literal-annotation wiring test and the `extra="forbid"` regression guard. No spec corners cut. The conditional AC5 ("if load-time migration is in scope") was correctly interpreted by TEA as boundary-only (test the rejection path); the migration sliver was empirically verified N/A by Architect during spec-check (zero `known_facts` entries across all 17 save databases on disk).
- **Dev (implementation): "No deviations from spec."** — Verified. Dev's GREEN target landed exactly as TEA pinned: annotation-level `Literal["Certain", "Suspected", "Rumored", "Discovered"] = "Certain"`, no `@field_validator` shortcut, six fixture migrations across the test tree (one more than TEA flagged — caught by Dev's own broader grep). Default value `"Certain"` is the semantically nearest replacement for legacy `"confirmed"`, documented in the cleanup-commit docstring. No load-time migration shim added; correct given empirical zero.
- **TEA (test verification): "No deviations from spec."** — Verified. The simplify fan-out ran three teammates in parallel; all 8 findings were correctly classified out-of-scope or duplicates of already-recorded delivery findings. Zero simplify fixes applied → zero reverts. The boy-scout F841 ruff fix in `test_dice_dispatch.py` and the UI subrepo branch sync to `develop` were bounded repository-hygiene actions, not spec deviations. The Reviewer cleanup pass (commit `b635062`) addressed four findings without scope creep.

**AC accountability table:**

| AC (from SM Assessment) | Status | Evidence |
|---|---|---|
| 1. Accepts only the four literal values | DONE | `test_known_fact_confidence_accepts_canonical_value` (4 parametrised cases) |
| 2. Pydantic rejects unknown values | DONE | `test_known_fact_confidence_rejects_legacy_confirmed` + `_rejects_arbitrary_string` (7 cases) + `_rejects_empty_string` + `_rejects_mis_cased_or_padded` (7 cases) + `_rejects_none` |
| 3. JSON serialization round-trips the literal value | DONE | `test_known_fact_confidence_json_roundtrip` (4 cases) |
| 4. Factory/builder defaults emit canonical (not `"confirmed"`) | DONE | `test_known_fact_default_confidence_is_canonical` (rewritten in cleanup to fold the regression-guard intent) |
| 5. If load-time migration in scope, legacy `"confirmed"` upgrades cleanly | DESCOPED — empirically N/A | Verified during spec-check: 0 `known_facts` rows across 17 save databases (7 live + 10 archived). No legacy data exists to migrate. Conditional AC's antecedent is false. Migration hook (`migrate_legacy_snapshot` in `migrations.py:240`) remains available for future need. |

**Documented forward-impact items** (deferred, surfaced for the boss to schedule):

1. `JournalEntry.confidence` Literal promotion (server-side protocol layer) — requires UI `Confidence` type at `sidequest-ui/src/providers/GameStateProvider.tsx:32` to widen from 3 values to 4 (add `"Discovered"`). Cross-repo sliver. Captured in TEA delivery finding #1 + Dev delivery finding #4.
2. UI rationalisation of the two `Confidence` definitions (Title-case 3-value at `GameStateProvider.tsx:32`, lowercase 3-value at `payloads.ts:672`). Captured in TEA delivery finding #2.
3. `_SUPPORTED_CONFIDENCES` defensive-but-dead filter in `scenario_accusation.py:118` — pure cosmetic deletion; pydantic Literal at construction makes the runtime check unreachable. Captured in Dev delivery finding #2.
4. Pydantic-internals fragility in the annotation-probe test — recommend a future pyright/mypy gate as the canonical type-narrowing assertion. Captured in TEA verify-phase Reviewer-dismissed finding (informational).
5. 30 pre-existing UI dice-test failures from `dice-lib` Three.js/Rapier integration — bisect-and-restore story. Captured in TEA verify finding #1.
6. `test_chargen_persist_and_play.py::test_chargen_confirm_persists_deduped_inventory` test-isolation flake — flake-hunt story. Captured in TEA verify finding #2.

All six items are clearly scoped as separate work; none compromise the integrity of the 50-17 type-narrowing landing.

**Architect verdict:** The deviation manifest is complete. The 1pt story landed within scope and within the spec authority hierarchy. No retroactive deviation logging required. Ready for SM finish.

## Sm Assessment

**Scope:** Tighten `KnownFact.confidence` from `str` to `Literal["Certain", "Suspected", "Rumored", "Discovered"]` on the server, mirroring the existing UI `Confidence` enum at `sidequest-ui/src/GameStateProvider.tsx:32`. Migrate all call sites and serialization paths.

**Why this story now:** ADR-100 J-4. Establishes mechanical ground truth for confidence values across the stack. Predecessors 50-14/15/16 are already merged — this is the type-safety capstone for the journal pipeline. 1-pointer, server-only, no UI churn (UI already uses the canonical values).

**Risk surface (small):**
- Existing string value `"confirmed"` does not appear in the new literal set. Migration must map legacy data → `"Certain"` (or whichever the team picks) at load time, OR the story scope explicitly chooses to break old saves. TEA should pin this in the RED phase.
- Any narrator-produced confidence strings need to be validated/coerced — pydantic v2 `Literal` will raise on mismatch.
- Persistence layer (SQLite save files) may have rows with the old value.

**Handoff to TEA (RED):** Write failing tests that pin:
1. `KnownFact.confidence` only accepts the four literal values.
2. Pydantic validation rejects unknown values (e.g., `"confirmed"`, `"high"`, `"likely"`).
3. JSON serialization round-trips the literal value unchanged.
4. Any factory/builder defaults emit one of the four canonical values (not `"confirmed"`).
5. If load-time migration is in scope, a save with legacy `"confirmed"` upgrades cleanly.

Resolve the legacy-value question with the spec before writing the migration test.

**Files of interest** (likely): `sidequest-server/sidequest/game/journal*.py`, `sidequest-server/sidequest/protocol/`, anywhere `KnownFact` is constructed or serialized.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Enum promotion + type-system tightening — needs runtime and annotation coverage.

**Test Files:**
- `sidequest-server/tests/game/test_known_fact_confidence.py` — 13 test functions, 32 collected after parametrisation. Covers the four ACs the SM Assessment listed plus a Literal-annotation wiring test and an `extra="forbid"` regression guard.

**Tests Written:** 13 test functions (32 parametrised cases) covering AC1–AC5.
**Status:** RED — 21 failing / 11 passing against current `confidence: str = "confirmed"` production. Verified by `testing-runner` at `RUN_ID: 50-17-tea-red`.

**The 11 passing tests are intentional regression guards** (not vacuous): they pin behaviours that must remain green through GREEN — happy-path acceptance of canonical values, None rejection (already enforced by pydantic against `str`), JSON round-trip on canonical inputs, `extra="forbid"` preservation, and `model_validate` acceptance of canonical dicts. If Dev's change accidentally weakened any of those, these guards would flip red.

### Key contract decisions pinned by tests

1. **Annotation-level tightening, not runtime validator.** The wiring test inspects `KnownFact.model_fields["confidence"].annotation` and asserts `typing.get_origin(...) is typing.Literal` with the four canonical args. Dev must not implement this as `str` + a `@field_validator` — type narrowing at module boundaries (`session.apply_patch`, `JournalEntry` derivation, scenario clue intake) requires the annotation pin.
2. **Default value is canonical, but value choice is Dev's.** `test_known_fact_default_confidence_is_canonical` asserts `kf.confidence in {Certain, Suspected, Rumored, Discovered}` and `!= "confirmed"`. The specific replacement is a GREEN-phase call; the recommendation (carried from SM Assessment, not tested here) is `"Certain"` as the closest semantic match for legacy `"confirmed"`.
3. **Case sensitivity is load-bearing.** Lowercase `"certain"` is rejected. UI `GameStateProvider.tsx:32` uses Title-case `'Certain' | 'Suspected' | 'Rumored'`; accepting lowercase here would re-open wire-format drift.
4. **Boundary path (`model_validate(dict)`) is tested explicitly.** This is the production path used at `sidequest/game/session.py:1164` for narrator-emitted `DiscoveredFact.fact` dicts. Validation rejection on the boundary is the ADR-100 OTEL-lie-detector posture.

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #3 type annotation gaps at boundaries | `test_known_fact_confidence_field_annotation_is_literal` | failing (production still annotated `str`) |
| #6 test quality — meaningful assertions | self-check: every test asserts a concrete value, raises a specific exception, or asserts membership / inequality. No `assert True`, no truthy-only checks, no `let _ = result` equivalents. | self-checked |
| #8 unsafe deserialization — JSON boundary validation | `test_known_fact_model_validate_rejects_legacy_confirmed_dict`, `test_known_fact_model_validate_rejects_arbitrary_confidence_dict` | failing (production accepts arbitrary strings via dict) |

**Rules checked:** 3 of 14 applicable to this scope (the rest — silent exceptions, mutable defaults, logging, path handling, resource leaks, async pitfalls, import hygiene, dependency hygiene, state cleanup ordering — do not apply to a pure enum-narrowing change on a single Pydantic field).

**Self-check:** No vacuous assertions found in the new test file. All 13 test functions either:
- Call `pytest.raises(ValidationError)` (exception-asserting),
- Assert `kf.confidence == <specific-value>` (value-asserting),
- Assert membership in `CANONICAL_CONFIDENCES` with an additional `!= "confirmed"` guard,
- Or inspect `model_fields[...].annotation` for the Literal origin and exact args.

**RED verification:** `RUN_ID: 50-17-tea-red` — 21 fail / 11 pass / 32 collected / 0.06s. See testing-runner result returned to TEA.

**Handoff:** To Dev (The White Rabbit) for GREEN.

**GREEN target shape (Dev's call but tests pin the boundary):**
```python
from typing import Literal

class KnownFact(BaseModel):
    model_config = {"extra": "forbid"}
    content: str
    confidence: Literal["Certain", "Suspected", "Rumored", "Discovered"] = "Certain"
    source: str = "GameEvent"
    learned_turn: int = 0
    fact_id: str = Field(default_factory=lambda: uuid4().hex)
    category: FactCategory = FactCategory.Lore
```
Plus migration of `tests/server/test_scenario_accusation_intake.py:299` (`confidence="confirmed"` → canonical value). See Delivery Findings.

## Dev Assessment

**Implementation Complete:** Yes
**Branch:** `feat/50-17-knownfact-confidence-enum` (sidequest-server) — pushed to origin

**Files Changed:**
- `sidequest/game/character.py` — added `from typing import Literal`; promoted `KnownFact.confidence` from `str = "confirmed"` to `Literal["Certain", "Suspected", "Rumored", "Discovered"] = "Certain"`.
- `tests/server/test_scenario_accusation_intake.py` — migrated one legacy `confidence="confirmed"` → `"Certain"` on a non-ScenarioClue KnownFact fixture (the test asserts source-based filtering; value swap is incidental).
- `tests/handlers/test_journal_request_handler.py` — migrated five KnownFact fixtures from legacy/lowercase confidence values to canonical Title-case (`"confirmed"`/`"suspected"`/`"rumored"` → `"Certain"`/`"Suspected"`/`"Rumored"`).

**Tests:** 32/32 passing on new file (`tests/game/test_known_fact_confidence.py`). Full server suite: 5406 passed / 64 skipped (pre-existing) / 0 failed. Verified by `testing-runner` at `RUN_ID: 50-17-dev-green`.

**Implementation choices (within TEA's pinned contract):**

1. **Default value: `"Certain"`.** Semantically closest to legacy `"confirmed"`. ScenarioClue intake still mints `"Discovered"` explicitly (unchanged). Narrator-emitted `WorldStatePatch.discovered_facts` dicts that omit `confidence` will now default to `"Certain"` rather than the legacy string.
2. **Annotation-level Literal, no runtime validator.** Satisfies TEA's wiring test that inspects `model_fields["confidence"].annotation` for `typing.Literal` origin. Pydantic v2 enforces the Literal at validation time automatically — no `@field_validator` needed.
3. **Migration sweep was wider than the lone fixture TEA flagged.** Dev found 5 KnownFact fixtures in `test_journal_request_handler.py` using legacy `"confirmed"` or lowercase `"suspected"`/`"rumored"` — all migrated. This is the "migrate existing call sites" part of the story scope; left no `KnownFact(confidence=<non-canonical>)` constructions in-tree (verified by grep).
4. **JournalEntry left alone.** Per TEA's first delivery finding, tightening `JournalEntry.confidence` (`sidequest/protocol/models.py:127`) is out of this story's strict 1pt scope. Filed as a non-blocking follow-up.

**Self-review (judgment checks):**
- [x] Code is wired — `KnownFact` is imported and used at `session.py:1159`, `scenario_clue_intake.py:73`, and 9+ other call sites. The Literal flows through all of them.
- [x] Follows project patterns — mirrors existing `Literal[...]` usage at `sidequest/game/accusation.py:104`.
- [x] All ACs met — 32/32 tests pass.
- [x] Error handling — pydantic ValidationError is the explicit failure mode (per ADR-100 OTEL-lie-detector posture).

**Handoff:** To Reviewer (The Queen of Hearts).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None (one conditional AC verified empirically N/A)

### AC-by-AC trace (against SM Assessment, the highest-authority spec source)

| AC | Spec ask | Implementation | Status |
|---|---|---|---|
| 1 | `KnownFact.confidence` only accepts the four literal values | `Literal["Certain", "Suspected", "Rumored", "Discovered"]` annotation + pydantic v2 enforcement | ✓ covered (4 parametrised passing tests) |
| 2 | Pydantic rejects unknown values (e.g. `"confirmed"`, `"high"`, `"likely"`) | Pydantic v2 raises `ValidationError` on Literal mismatch | ✓ covered (7 parametrised + 1 explicit `"confirmed"` test, 7 case/whitespace tests) |
| 3 | JSON serialization round-trips the literal value unchanged | `model_dump_json` ↔ `model_validate_json` preserves the literal | ✓ covered (4 parametrised tests) |
| 4 | Factory/builder defaults emit one of the four canonical values (not `"confirmed"`) | Default changed to `"Certain"` (semantically closest to legacy `"confirmed"`) | ✓ covered |
| 5 | If load-time migration is in scope, a save with legacy `"confirmed"` upgrades cleanly | **Empirically N/A** — see analysis below | ✓ correctly deferred |

### Conditional AC-5 — load-time migration

The SM Assessment flagged this under Risk Surface: "Persistence layer (SQLite save files) may have rows with the old value." Architect verified empirically:

- `~/.sidequest/saves/games/*` (7 live save dirs): every `Character.known_facts` array has `len=0`.
- `~/.sidequest/saves/_archive/*` (10 archived save dirs): same — `len=0` in every snapshot.
- Production `KnownFact()` construction sites in source: exactly one (`sidequest/server/dispatch/scenario_clue_intake.py:73`), and it always emits `confidence="Discovered"` explicitly — never the field default.
- The narrator's `WorldStatePatch.discovered_facts` path is documented in `sidequest/telemetry/turn_record.py:59` as "do NOT go through" — the field is essentially unused in current narration; the live journal pipeline runs through `Footnote` → UI per ADR-100 (the half-wired arch this story is part of restoring).

Conclusion: there are zero `KnownFact(confidence="confirmed")` rows on disk in Keith's save corpus. The hypothetical migration would be a no-op against today's data. Dev's decision to skip the load-time migration sliver is correct.

**Future-proofing note (informational, not a finding):** the migration framework at `sidequest/game/migrations.py:240` (`migrate_legacy_snapshot` + the `_migrate_s<N>_*` sub-function tuple) is the right place to add a `_migrate_s4_known_fact_confidence` shim if a save with legacy values is ever imported (e.g. from a contributor's local environment, or if a future ADR-100 sibling story populates `Character.known_facts` heavily via legacy code paths before this enum lands). The Architect amendment of 2026-05-04 in `persistence.py:434-458` already wires the `.canonicalize.bak` durable-retention sibling, so adding a sub-function is the only missing piece. Not required for this story.

### Architectural notes (not mismatches, just observations for Reviewer)

1. **Server enum is now richer than the UI mirror.** TEA's "Conflict" delivery finding correctly identified that the UI `Confidence` type at `sidequest-ui/src/providers/GameStateProvider.tsx:32` is `'Certain' | 'Suspected' | 'Rumored'` (3 values, no `'Discovered'`), and `sidequest-ui/src/types/payloads.ts:672` has a third, lower-case definition. ADR-100's row 50-17 text ("Mirrors UI `Confidence` enum already in `GameStateProvider.tsx:32`") was inaccurate when written — the mirror was always 3-of-4. The right vector is a follow-up UI story to widen the UI type to 4 values and rationalise the two UI definitions, not a rework of this server-side story. Dev's hands-off treatment is correct.

2. **Dev's `_SUPPORTED_CONFIDENCES` finding is real but out of scope.** The runtime check at `sidequest/server/dispatch/scenario_accusation.py:118` becomes defensive-but-dead after this change (pydantic enforces the same set at construction). Reviewer can recommend deletion in their pass; not blocking.

3. **Stale "until 50-17 lands" comment.** `scenario_accusation.py:107` conflates this enum-promotion story with the deferred work of giving `KnownFact` an originating-clue-id field. Dev correctly flagged. Reviewer should ask Dev for a one-line comment fix.

### Architectural pattern reuse check (pragmatic-restraint mandate)

- ✓ Reused the existing `Literal[...]` pattern from `sidequest/game/accusation.py:104` (same four values).
- ✓ Reused the existing `_SUPPORTED_CONFIDENCES` set definition (the dispatch already had the canonical vocabulary; this story didn't invent it, it caught up to it).
- ✓ Reused pydantic v2's built-in Literal enforcement — no `@field_validator`, no custom validation class, no parallel runtime guard.
- ✓ Did **not** introduce a load-time migration sub-function — correctly avoided new infrastructure for a problem that doesn't exist on disk.

**Decision:** Proceed to verify (TEA). No hand-back to Dev.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed on server (the only repo this story touches)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4 (the full 50-17 diff: `character.py`, `test_known_fact_confidence.py`, `test_journal_request_handler.py`, `test_scenario_accusation_intake.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | All target pre-existing test-scaffold duplication (`_clue()`, `_attach()`, `_bind_seated_room()`, `_character()`) in files outside the 50-17 diff. None of the duplications were introduced or aggravated by this story. |
| simplify-quality | 2 findings | (1) `JournalEntry.confidence: str` should mirror the new Literal — already flagged by TEA delivery finding #1 as a follow-up sliver, explicitly out of scope per SmAssessment 1pt envelope. (2) `test_journal_request_handler.py:650` uses `"confidence": "confirmed"` inside a `JournalEntry` payload dict — coupled to (1); test still passes because `JournalEntry.confidence` is still `str`. Dev already flagged in finding #4. |
| simplify-efficiency | 2 findings | (1) Three near-identical field validators in `character.py` (`backstory`, `char_class`, `race`) — low confidence, pre-existing pattern, not touched by 50-17. (2) Unrelated `otel_capture` fixture concern in `test_scenario_accusation_intake.py:239` — medium confidence, pre-existing, not in 50-17 diff. |

**Applied:** 0 high-confidence fixes (all high-confidence reuse findings target files outside the diff; the high-confidence quality finding is the out-of-scope `JournalEntry` follow-up).
**Flagged for Review:** 0 actionable medium-confidence findings within scope.
**Noted:** 8 total findings across the three teammates — all dismissed as out-of-scope or duplicates of already-recorded delivery findings.
**Reverted:** 0 (no fixes applied → nothing to revert).

**Overall:** simplify: clean (within story scope)

### Aggregated Findings Disposition

| # | Agent | File | Cat | Conf | Decision | Rationale |
|---|-------|------|-----|------|----------|-----------|
| 1 | efficiency | `character.py:118` | unnecessary-complexity | low | Dismiss | Pre-existing pattern, not in 50-17 diff hunks |
| 2 | efficiency | `test_scenario_accusation_intake.py:239` | redundant-operations | medium | Dismiss | Pre-existing, not in 50-17 diff hunks (story only changed line 299) |
| 3 | reuse | `test_accusation.py:72` | duplicated-logic | high | Dismiss | Story 50-17 does not touch `test_accusation.py` — no diff |
| 4 | reuse | `test_scenario_accusation_intake.py:43` | duplicated-logic | medium | Dismiss | Pre-existing helper, not in 50-17 diff hunks |
| 5 | reuse | `test_journal_request_handler.py:73` | extractable-helper | high | Dismiss | Pre-existing `_attach()` helper, not in 50-17 diff hunks (story only changed five fixture confidence values) |
| 6 | reuse | `test_journal_request_handler.py:100` | extractable-helper | low | Dismiss | Pre-existing, not in diff |
| 7 | quality | `protocol/models.py:127` | type-safety-issue | high | Dismiss (in-scope-follow-up) | Already captured as TEA delivery finding #1 (`JournalEntry.confidence` mirror). Explicitly out of this 1pt story per SmAssessment ("server-only, no UI churn") |
| 8 | quality | `test_journal_request_handler.py:650` | convention-violation | medium | Dismiss (coupled to #7) | Already captured as Dev delivery finding #4. Test still passes because `JournalEntry.confidence` is still `str`; migrate together with #7 |

### Quality-Pass Gate Run (`just check-all`)

| Stage | Result | Notes |
|---|---|---|
| `server-lint` (ruff) | ✓ PASS (after 1 boy-scout fix) | Pre-existing F841 `enc` unused-variable error in `tests/server/test_dice_dispatch.py:377` — introduced by `ed238da feat(dice): thread player_action through DICE_THROW`, unrelated to 50-17. Fixed in chore commit `659aa28` per [[feedback_just_fix_it]] / [[feedback_boy_scout_bounded]]. |
| `server-test` (pytest) | ✓ PASS | 5406 passed / 64 skipped pre-existing on the second run. The first `check-all` run had one flaky failure in `test_chargen_persist_and_play.py::test_chargen_confirm_persists_deduped_inventory`; the test passes in isolation and on re-run — order-dependent flake, not a 50-17 regression. |
| `client-lint` | ✓ PASS (1 pre-existing warning) | `useEffect missing dependency` in `App.tsx:1646` — pre-existing, unrelated. |
| `client-typecheck` | ✓ PASS | Two `TS2352` errors on the first run were caused by the UI repo being stuck on the stale `feat/50-16-journal-ui-confidence` branch, which predated `d52a3da fix(types): use unknown-bridge cast on GameMessage → Record (#239)` on `develop`. Synced UI repo to `develop` per [[feedback_subrepo_branches]]; errors cleared. |
| `client-test` (vitest) | ✗ FAIL — **deferred** | 30 failures across `DiceOverlay.test.tsx`, `InlineDiceTray.test.tsx`, `deterministicReplay.test.tsx`, `dice-overlay-wiring-34-5.test.ts`, `character-creation-wiring.test.tsx`. Errors trace into `../../dice-lib/src/DiceScene.tsx:256` (`object.updateWorldMatrix is not a function`, `Cannot read properties of undefined (reading 'simulateOpen')`). **Verified pre-existing on `develop`**: re-running `npx vitest run src/dice/__tests__/DiceOverlay.test.tsx` on a clean `develop` checkout reproduces 20 failures with identical stack traces. This is dice-lib integration breakage — entirely orthogonal to story 50-17 (server-only, no UI files touched). Flagging as Delivery Finding rather than fixing — fits "defer anything that goes exponential" per [[feedback_boy_scout_bounded]]. |
| `daemon-lint` | ✓ PASS | Not exercised by 50-17. |

**Within-story-scope quality check:** server lint, server tests, server typecheck (implicit via pyright in pytest collection) — ALL GREEN.

### Wiring verification (per CLAUDE.md "Every Test Suite Needs a Wiring Test")

- `KnownFact` has 11 non-test importers across `sidequest/` (verified by `grep -rn "from sidequest.game.character import.*KnownFact"`).
- The Literal flows through `session.apply_patch.discovered_facts` (`session.py:1164` — `KnownFact.model_validate(df.fact)`), `scenario_clue_intake.py:73`, and recap-building in `persistence.py:475`.
- `tests/game/test_known_fact_confidence.py::test_known_fact_model_validate_accepts_canonical_dict` and `test_known_fact_model_validate_rejects_legacy_confirmed_dict` are the wiring tests for the `session.apply_patch` boundary — they directly exercise the production validation path.

### Decision

**Server-side scope: GREEN.** Hand off to Reviewer (The Queen of Hearts) for code review. The deferred UI dice-test failures are tracked in Delivery Findings — Reviewer can confirm the deferral or escalate.

**Handoff:** To Reviewer.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (JournalEntry.confidence still `str`) | confirmed 1, dismissed 0, deferred 1 |
| 2 | reviewer-edge-hunter | N/A | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.edge_hunter` |
| 3 | reviewer-silent-failure-hunter | N/A | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.silent_failure_hunter` |
| 4 | reviewer-test-analyzer | Yes | findings | 4 (line 650 missed fixture, duplicate-default-test, pydantic-internals coupling, missing apply_patch integration test) | confirmed 2, dismissed 2 (with rationale below) |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 (KnownFact docstring, scenario_accusation:107 stale, test line 131 docstring, test line 173 docstring, module docstring UI parity) | confirmed 3, dismissed 2 (misreadings of docstring text) |
| 6 | reviewer-type-design | N/A | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.type_design` |
| 7 | reviewer-security | N/A | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.security` |
| 8 | reviewer-simplifier | N/A | Skipped | disabled | N/A — disabled via `workflow.reviewer_subagents.simplifier` |
| 9 | reviewer-rule-checker | Yes | findings | 3 (JournalEntry rule#3, line 650 rule#6, duplicate-default-test rule#6) | confirmed 3 (all overlap with test-analyzer/preflight) |

**All received:** Yes (4 enabled subagents returned, 5 disabled subagents pre-filled per settings)
**Total findings:** 6 confirmed, 4 dismissed, 1 deferred (JournalEntry — out-of-scope, already in TEA #1 / Dev #4 / Architect note)

### Cross-referenced finding cluster (3 subagents agree)

| Finding | preflight | test-analyzer | rule-checker | comment-analyzer | Decision |
|---|---|---|---|---|---|
| `JournalEntry.confidence: str` not narrowed (`protocol/models.py:127`) | ✓ flag | (implicit in finding #1) | ✓ rule #3 | — | **Deferred** — out of 1pt scope, already in delivery findings |
| `test_journal_request_handler.py:650` fixture missed `"confirmed"`→canonical migration | ✓ flag | ✓ finding #1 | ✓ rule #6 violation | — | **Confirmed [MEDIUM]** — request fix |
| `test_known_fact_default_confidence_is_not_legacy_confirmed` subsumed by canonical test | — | ✓ finding #2 | ✓ rule #6 violation | — | **Confirmed [MEDIUM]** — request fix |
| `KnownFact` class docstring missing closed-vocab documentation | — | — | — | ✓ finding #1 | **Confirmed [LOW]** — request fix |
| `scenario_accusation.py:107` stale "until 50-17 lands" comment | — | — | — | ✓ finding #5 | **Confirmed [LOW]** — request fix (also matches Dev's own delivery finding #1) |

### Dismissals (with rationale)

- **test-analyzer #3 (pydantic-internals coupling)** — Valid hardening recommendation, but acknowledged by the analyzer itself as "test is genuinely pinning something useful" and "not currently broken." Adding a pyright/mypy static-analysis gate is appropriate future work, not blocking. Architect's spec-check section noted no architectural mismatch here. Severity drops to informational. Defer.
- **test-analyzer #4 (missing apply_patch integration test)** — `session.py:1158-1165` invokes `KnownFact.model_validate(df.fact)` directly with no try/except wrapper; ValidationError propagates naturally. Existing tests `test_known_fact_model_validate_accepts_canonical_dict` (line 169) and `test_known_fact_model_validate_rejects_legacy_confirmed_dict` (line 190) exercise the exact production call signature. CLAUDE.md's "every test suite needs a wiring test" rule is satisfied — the model_validate boundary IS the wiring point. A full apply_patch integration test would be incremental coverage, not a story-blocking gap.
- **comment-analyzer #2 (module docstring claims UI parity)** — Misreading. The docstring at `test_known_fact_confidence.py:5-7` says the literal mirrors `scenario_accusation._SUPPORTED_CONFIDENCES` and `accusation.AccusationItem.confidence` — both of which DO contain all four canonical values. The docstring does not claim UI parity. Dismiss.
- **comment-analyzer #3 (line 131 docstring on mis-cased rejection)** — Misreading. The docstring discusses CASE sensitivity, using the UI's Title-case spelling as the reference for capitalisation. It does not claim value-completeness with the UI. The point being made (lowercase rejection prevents wire-format drift) is correct. Dismiss.

### My own analysis (Reviewer, ≥5 observations)

- **[VERIFIED] `KnownFact.confidence` annotation is a true closed Literal** — `character.py:31` is `Literal["Certain", "Suspected", "Rumored", "Discovered"] = "Certain"`. Pyright would narrow this; pydantic enforces at runtime. Complies with python.md rule #3 (type annotation gaps at boundaries) — module-boundary type, narrowed.
- **[VERIFIED] No silent fallback at the production boundary** — `session.py:1164` calls `KnownFact.model_validate(df.fact)` with no `try/except` wrapper (grepped + read). `ValidationError` propagates. Complies with CLAUDE.md "No Silent Fallbacks" + python.md rule #1 (silent exception swallowing — zero violations in this diff).
- **[VERIFIED] Wiring is real** — The `model_validate(dict)` path is the actual narrator-input ingestion point at `session.apply_patch.discovered_facts`. The TEA tests at lines 169–204 exercise that exact call. Complies with CLAUDE.md "Every Test Suite Needs a Wiring Test."
- **[VERIFIED] `extra="forbid"` preserved** — `character.py:28` retained; `test_known_fact_still_forbids_extra_fields_after_enum_promotion` (line 246) is the regression guard. Complies with the "no silent fallthrough on unknown keys" expectation.
- **[VERIFIED] `from __future__ import annotations` + `from typing import Literal` ordering** — `character.py:11,13` are in lexicographic order; standard import hygiene. Complies with python.md rule #10.
- **[VERIFIED] `ed238da feat(dice)` F841 boy-scout fix is correct** — `tests/server/test_dice_dispatch.py:377` — removed `enc = _make_encounter()` was a true unused-variable shadow; `enc_local` is created inside the loop at line 387 and is the variable actually consumed. Removal is safe; no behaviour change. Complies with python.md rule #13 (fix-introduced regressions — none).
- **[TEST/RULE] `test_known_fact_default_confidence_is_not_legacy_confirmed` is strictly subsumed** — Lines 158–162 assert `kf.confidence != "confirmed"`. Lines 154–155 in `test_known_fact_default_confidence_is_canonical` assert the same (plus the stronger `in CANONICAL_CONFIDENCES`). Two specialists flagged. Rule #6 violation. Fix required.
- **[TEST/RULE] `test_journal_request_handler.py:650` missed migration** — The fixture passes `"confidence": "confirmed"` in a `JournalEntry` payload dict. The test passes only because `JournalEntry.confidence: str` is not narrowed. Three specialists flagged. The fix is a one-character change to a canonical value (`"Certain"`), which removes the misleading suggestion that `"confirmed"` is acceptable wire format. Does NOT require tightening `JournalEntry.confidence` itself (deferred). Fix required.
- **[DOC] `KnownFact` class docstring is silent on the closed vocabulary** — `character.py:23-26` says only "A fact the character has learned — accumulates monotonically." A maintainer reading this class without scrolling to the field annotations would not know that `confidence` is a closed set. Add 2-3 lines documenting the four values, the `"Certain"` default, and `extra="forbid"`.
- **[DOC] `scenario_accusation.py:107` stale comment is now actively misleading** — Reads "parallel iteration is the deterministic fallback until 50-17 lands." This file is on `develop` post-merge of 50-17. The comment becomes a lie at the moment this PR merges. Dev's delivery finding #1 already identified it. Per the OTEL-lie-detector principle and CLAUDE.md "never say X then do Y," fixing this one-line comment now is correct boy-scout-bounded scope. Not modifying the actual filter logic — just the comment.

### Rule Compliance

Mapping diff content to `.pennyfarthing/gates/lang-review/python.md`:

| Rule | Applies to diff? | Instances | Violations | Disposition |
|---|---|---|---|---|
| 1 — Silent exception swallowing | No | 0 | 0 | No try/except added in diff |
| 2 — Mutable default arguments | Yes (Pydantic field default) | 1 (`confidence = "Certain"`) | 0 | Immutable str — compliant |
| 3 — Type annotation gaps at boundaries | Yes | 5 (KnownFact.confidence, JournalEntry.confidence, 3 test return types) | 1 | `JournalEntry.confidence` is the wire-boundary peer still typed `str` — **deferred** per story scope; documented |
| 4 — Logging | No | 0 | 0 | No new error paths in diff |
| 5 — Path handling | No | 0 | 0 | No path ops |
| 6 — Test quality | Yes | 17 | 2 | Duplicate `is_not_legacy_confirmed` test + missed fixture at line 650 — **both fix-required** |
| 7 — Resource leaks | No | 0 | 0 | No file/socket/lock ops |
| 8 — Unsafe deserialization | Yes | 3 (`model_validate`, `model_validate_json`, `GameMessage.model_validate`) | 0 | All schema-validated — compliant |
| 9 — Async pitfalls | No | 0 | 0 | No async functions in diff |
| 10 — Import hygiene | Yes | 3 | 0 | All explicit named imports, no star imports |
| 11 — Input validation at boundaries | Yes | 1 (`KnownFact.confidence`) | 0 | Literal enforces closed-set validation — compliant |
| 12 — Dependency hygiene | No | 0 | 0 | No deps changed |
| 13 — Fix-introduced regressions | Yes | 4 changed files | 0 | All checks #1–#12 still clean after diff |
| 14 — State cleanup ordering | No | 0 | 0 | No queue/buffer clear operations |

**Rules with violations:** #3 (1 deferred), #6 (2 fix-required).

### Devil's Advocate (≥200 words)

This code is fine. Or is it? Let me argue it's broken.

**The Literal is half-deployed.** `KnownFact.confidence` is now a closed set, but `JournalEntry.confidence` — which mirrors `KnownFact` 1:1 according to its own docstring — is still `str`. The wire shape that delivers KnownFacts to the UI is more permissive than the source. A narrator that for some reason serializes a non-canonical confidence into a `JOURNAL_RESPONSE` (say through a future code path that constructs `JournalEntry` from non-`KnownFact` sources) will pass deserialization without a peep. The story's promise of "no silent string drift" is half-kept. The deferral is explicit in delivery findings, but a malicious or confused future Dev could read the diff and conclude the wire boundary is now safe — it isn't.

**The annotation probe test is fragile.** `KnownFact.model_fields["confidence"].annotation` reaches into pydantic v2 internals. Across pydantic 2.x minor releases, the storage of Literal annotations has shifted (wrapped in AnnotatedAlias, normalised under Optional for defaulted fields). If a pydantic upgrade lands and that annotation storage changes shape, this test will fail without any actual regression in the type narrowing — false-positive territory. Mitigation belongs in a pyright/mypy gate, not pydantic-internals introspection.

**The duplicate default-confidence test reveals carelessness.** It's a TEA self-check failure that no one caught. The presence of a strictly-subsumed test in a story whose entire purpose is "tighten validation" is ironic. It hints at uneven attention during the test-design pass.

**Test fixture at line 650 is a missed migration.** Dev mentioned it explicitly as deferred, but rule-checker calls it a contradiction of the migration goal. A reader of the test suite sees `"confidence": "confirmed"` passing through `GameMessage.model_validate` without error and concludes the wire format accepts the legacy value. That's exactly the wrong impression for a story whose AC2 is "reject `'confirmed'` at the boundary."

**Save migration is empirically zero — until it isn't.** Architect verified zero `known_facts` in current save corpus. But the migration framework hook (`migrate_legacy_snapshot` at `migrations.py:240`) is not extended for this enum change. The day someone imports an external save, copies an older `.canonicalize.bak`, or a future story populates `Character.known_facts` heavily via legacy paths that produce `"confirmed"` defaults, the load will hard-fail with a `SaveSchemaIncompatibleError`. That's "loud failure," which is the project rule — but it's also potentially a Keith-loses-his-game moment if the empirical-zero assumption ever breaks.

**The `_SUPPORTED_CONFIDENCES` filter in `scenario_accusation.py:118` is dead.** Pydantic Literal enforcement at construction means `fact.confidence` will always be one of the four canonical values; the runtime filter can never reject. Dev correctly flagged this as defensive-but-dead code. Not fixing it leaves a "this code couldn't run" landmine for a future grep.

**The Devil concedes:** the Literal change itself is correct and minimal. The 32 tests are thorough. The boundary behaviour is right. The failures above are paper cuts and deferred scope, not core bugs.

But the paper cuts include two tests-quality violations (rule #6) and two stale comments that lie post-merge. Those need to clear before the verdict reads APPROVED.

### Deviation Audit

Reviewing the `## Design Deviations` section:

- TEA (test design): "No deviations from spec." → ✓ ACCEPTED by Reviewer: agrees, TEA's test design adhered to all five ACs from SM Assessment.
- Dev (implementation): "No deviations from spec." → ✓ ACCEPTED by Reviewer: agrees, Dev's implementation matched the GREEN target shape suggested by TEA and stayed within the 1pt scope.
- TEA (test verification): "No deviations from spec." → ✓ ACCEPTED by Reviewer: agrees, verify phase ran the simplify fan-out and applied 0 fixes correctly. The boy-scout F841 fix and UI subrepo sync were bounded repository-hygiene actions, not spec deviations.

No undocumented deviations identified by Reviewer.

## Reviewer Assessment

**Verdict:** REJECTED — minor cleanup required before merge

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MEDIUM] [TEST] [RULE] | Missed fixture migration leaves misleading "confirmed-is-valid-wire-format" suggestion. Flagged by preflight, test-analyzer, rule-checker. | `sidequest-server/tests/handlers/test_journal_request_handler.py:650` | Change `"confidence": "confirmed"` → `"confidence": "Certain"`. Does **not** require tightening `JournalEntry.confidence` (deferred); just removes the suggestion that `"confirmed"` is valid wire format. |
| [MEDIUM] [TEST] [RULE] | Duplicate test strictly subsumed by canonical-default test. Python.md rule #6 violation: tests-with-no-distinct-assertions. Flagged by test-analyzer and rule-checker (both high confidence). | `sidequest-server/tests/game/test_known_fact_confidence.py:158-162` | Delete `test_known_fact_default_confidence_is_not_legacy_confirmed`. If the "regression guard against reverting to legacy `confirmed`" intent is worth preserving, fold it into the canonical-default test's docstring (one extra sentence). |
| [LOW] [DOC] | `KnownFact` class docstring is silent on the new closed-vocabulary constraint and the `extra="forbid"` invariant. A maintainer reading just the class docstring would not know `confidence` is a closed set. | `sidequest-server/sidequest/game/character.py:23-26` | Extend docstring to document: (a) `confidence` accepts one of four canonical values (`"Certain"`, `"Suspected"`, `"Rumored"`, `"Discovered"`), (b) default is `"Certain"`, (c) `extra="forbid"` is enforced at construction. |
| [LOW] [DOC] | Stale "until 50-17 lands" comment becomes a lie at merge. Flagged by comment-analyzer (high) and Dev's own delivery finding #1. Per CLAUDE.md "never say X then do Y" and the OTEL-lie-detector principle, post-merge codebase comments must be truthful. | `sidequest-server/sidequest/server/dispatch/scenario_accusation.py:107` | Update the comment to remove the 50-17 reference. The parallel-iteration scheme is the actual permanent design (or describe what future story would replace it — likely ADR-053 restoration). Single-line comment fix; do **not** modify the filter logic. |

**Deferred (already in delivery findings, not blocking this story):**
- `JournalEntry.confidence` Literal promotion — TEA #1, Dev #4, Architect note. Requires UI `Confidence` type widening (currently 3-of-4, missing `"Discovered"`); follow-up sliver.
- `_SUPPORTED_CONFIDENCES` defensive-but-dead filter in `scenario_accusation.py:118` — Dev #2. Cosmetic; Reviewer of follow-up story can delete.
- Pydantic-internals coupling in annotation-probe test — test-analyzer #3. Hardening recommendation (add pyright/mypy gate); future work.
- 30 pre-existing UI dice-test failures — TEA verify #1. Out-of-scope dice-lib integration breakage; bisect-and-restore is a separate story.
- Test-isolation flake on `test_chargen_persist_and_play.py` — TEA verify #2. Flake-hunt is a separate story.

**Data flow traced:** Narrator JSON → `WorldStatePatch.discovered_facts: list[DiscoveredFact]` → `session.apply_patch:1161-1165` → `KnownFact.model_validate(df.fact)` (now Literal-enforced) → `Character.known_facts.append(kf)`. Pre-50-17, narrator could emit any string for `confidence`; post-50-17, only canonical values pass the boundary. Verified: no try/except wraps the model_validate call; ValidationError propagates.

**Pattern observed:** Mirrors the existing `Literal` pattern in `sidequest/game/accusation.py:104` (same four values). Re-uses pydantic v2's native Literal enforcement rather than adding a runtime validator — correct per the pragmatic-restraint principle.

**Error handling:** Pydantic Literal raises `ValidationError` on mismatch. The boundary test at `test_known_fact_model_validate_rejects_legacy_confirmed_dict` directly verifies the narrator-input path. No swallowing.

**Handoff:** Back to Dev (The White Rabbit) for the four cleanup items above. Expected turnaround: 5–10 minutes. Re-spawn Reviewer after Dev pushes the cleanup commit.

## Dev Assessment (rework)

**Implementation Complete:** Yes (cleanup pass)
**Branch:** `feat/50-17-knownfact-confidence-enum` (sidequest-server) — pushed at commit `b635062`

**Files Changed (cleanup commit):**
- `sidequest/game/character.py` — extended `KnownFact` class docstring to document the closed-vocabulary contract, default value, mirror of `_SUPPORTED_CONFIDENCES`/`AccusationItem.confidence`, where `"Discovered"` originates (`ScenarioClueIntake`), and the `extra="forbid"` invariant.
- `sidequest/server/dispatch/scenario_accusation.py` — updated the stale `_build_evidence` docstring to remove "until 50-17 lands"; now references the actual deferred work (ADR-053 restoration giving `KnownFact` an originating-clue-id field). Comment only; behaviour unchanged.
- `tests/game/test_known_fact_confidence.py` — deleted redundant `test_known_fact_default_confidence_is_not_legacy_confirmed`; its assertion was strictly subsumed by `test_known_fact_default_confidence_is_canonical`. Folded the "regression-guard against legacy confirmed" intent into the canonical-default test's docstring. Net: 32 → 31 tests.
- `tests/handlers/test_journal_request_handler.py` — migrated the line-650 `JournalEntry` fixture value from `"confirmed"` → `"Certain"`. Test still validates wire-shape roundtrip; no longer carries the misleading suggestion that `"confirmed"` is acceptable wire format. Does **not** tighten `JournalEntry.confidence` (deferred, per all prior delivery findings).

**Tests:** 31/31 on the targeted file. Full server suite 5405 passed / 64 skipped / 0 failed. Verified by `testing-runner` at `RUN_ID: 50-17-dev-green-rework`.

**Verdict mapping:**

| Reviewer finding | Status |
|---|---|
| [MEDIUM] missed fixture at `test_journal_request_handler.py:650` | ✓ FIXED — `"confirmed"` → `"Certain"` |
| [MEDIUM] duplicate `test_known_fact_default_confidence_is_not_legacy_confirmed` | ✓ FIXED — deleted, intent folded into canonical-default test docstring |
| [LOW] `KnownFact` docstring missing closed-vocab documentation | ✓ FIXED — extended with full contract |
| [LOW] stale `scenario_accusation.py:107` "until 50-17 lands" comment | ✓ FIXED — references ADR-053 restoration target instead |

**Deferred items (unchanged, still in delivery findings):**
- `JournalEntry.confidence` Literal promotion — requires UI Confidence type widening first.
- `_SUPPORTED_CONFIDENCES` defensive-but-dead filter — Reviewer of follow-up story can delete.
- Pydantic-internals coupling in annotation probe — hardening via pyright/mypy gate, future.
- 30 pre-existing UI dice-test failures — separate bisect-and-restore story.
- `test_chargen_persist_and_play` flake — separate flake-hunt.

**Handoff:** Back to Reviewer (The Queen of Hearts) for re-review of the cleanup commit.

## Reviewer Assessment (re-review of cleanup commit)

**Verdict:** APPROVED

Inspected commit `b635062` (Author: Keith Avery, 2026-05-14T07:44:58 -0400; 4 files, +20/-11). Every Reviewer finding from the prior cycle is resolved:

| # | Prior finding | Fix in `b635062` | Disposition |
|---|---|---|---|
| 1 | [MEDIUM] `test_journal_request_handler.py:650` fixture left at `"confirmed"` | One-character change `"confirmed"` → `"Certain"` in the `JournalEntry` payload dict. JournalEntry behaviour unchanged (still `str` per deferred scope). | ✓ FIXED |
| 2 | [MEDIUM] Duplicate `test_known_fact_default_confidence_is_not_legacy_confirmed` | Deleted (lines 158-162 of the prior file). The canonical-default test's docstring now carries both invariants explicitly: (1) "default is one of the four canonical values" and (2) "default is not the legacy `confirmed` string — regression guard against reverting the migration." Net: 32 → 31 tests, same coverage. | ✓ FIXED |
| 3 | [LOW] `KnownFact` docstring silent on closed-vocabulary | Extended docstring documents: four canonical values, `"Certain"` default, mirror of `_SUPPORTED_CONFIDENCES` and `AccusationItem.confidence`, `ScenarioClueIntake` minting `"Discovered"`, narrator-emitted via `WorldStatePatch.discovered_facts`, and `extra="forbid"` invariant. Comprehensive. | ✓ FIXED |
| 4 | [LOW] Stale "until 50-17 lands" comment in `scenario_accusation.py:107` | Comment now reads "parallel iteration is the deterministic fallback until `KnownFact` gains an explicit originating-clue-id field (ADR-053 restoration)." Truthful post-merge; references the actual deferred work item. | ✓ FIXED |

**Test gate:** `testing-runner` at `RUN_ID: 50-17-dev-green-rework` reported 31/31 on `tests/game/test_known_fact_confidence.py` (expected drop from 32 after the duplicate-test removal) and 5405/5405 / 64 skipped / 0 failed on the full server suite.

**No new findings introduced** by the cleanup commit:
- No new code paths (docstring + comment + delete + 1-char fixture change).
- No new error handling surface (no try/except, no logging changes).
- No new type-system claims (the docstring describes the existing Literal).
- The deleted test's coverage is fully preserved by the surviving canonical-default test.
- The fixture change does not alter what `test_journal_request_payload_in_phase1_variant` is verifying (wire-shape roundtrip); it removes a misleading suggestion that `"confirmed"` is acceptable wire format.

**Deferred items confirmed still deferred** (no scope creep on either side):
- `JournalEntry.confidence` Literal promotion — still `str` per scope.
- `_SUPPORTED_CONFIDENCES` defensive-but-dead filter — untouched.
- Pydantic-internals coupling in annotation probe — untouched.
- 30 pre-existing UI dice-test failures — untouched.
- `test_chargen_persist_and_play` flake — untouched.

**Data flow re-trace:** Unchanged from previous review. `KnownFact.model_validate(df.fact)` at `session.py:1164` remains the type-narrowed boundary. No try/except wrapper. ValidationError propagates.

**Pattern observed:** The cleanup itself follows the docstring-as-contract pattern already used by `AccusationItem` and the protocol models — extended `KnownFact` docstring now describes the closed-set boundary in the same voice as those peers.

**Verdict:** APPROVED. Route forward to Architect for `spec-reconcile`, then SM for `finish`.

**Handoff:** To Architect (The White Queen) for the final deviation-manifest pass.