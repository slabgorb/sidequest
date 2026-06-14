---
story_id: "113-1"
jira_key: ""
epic: "113"
workflow: tdd
---
# Story 113-1: F2a — Fate action classifier

## Story Details
- **ID:** 113-1
- **Title:** F2a — Fate action classifier: the Intent Router classifies a freeform player action in a `ruleset:fate` pack with an active conflict into a `fate_action` subsystem dispatch routed to the existing `dispatch_fate_action` (F1d), emitting `fate.action.classified` (new F2 lie-detector span)
- **Jira Key:** (none — personal project, slabgorb-org, no Jira integration)
- **Workflow:** tdd (phased: setup → red → green → review → finish)
- **Points:** 5
- **Type:** feature
- **Stack Parent:** none
- **Epic:** 113 (ADR-144 F2 — Fate Core narrator/intent-router integration)
- **Priority:** p1

## Story Context

**One-liner:** The freeform-text counterpart to F1d's explicit `FATE_ACTION` channel. A player types prose in a Fate-bound pack with an active conflict → the Intent Router (Haiku, existing) classifies it into a new `fate_action` subsystem dispatch → the dispatch bank routes it to the **same** engine entry as F1d, `dispatch_fate_action` — emitting the new `fate.action.classified` span so the GM panel can confirm the Fate action was *engaged from language*, not improvised. Both channels (explicit `FATE_ACTION` message + freeform classification) converge on one engine entry; no duplicate classifier, no duplicate engine entry (CLAUDE.md "Don't Reinvent").

**Acceptance Criteria** (mapped 1:1 to the plan's 6 TDD tasks):

- **AC1 — `fate.action.classified` OTEL span (Task 1):** `fate_action_classified_span` added to `sidequest/telemetry/spans/fate.py` with its `SPAN_ROUTES["fate.action.classified"]` entry (event_type `state_transition`, component `fate`, extracting `field=action_classified` + actor/action/skill/target/confidence) so the GM panel surfaces it. Literal-key route (no `SPAN_*` constant) — the routing-completeness lint stays green (same pattern as the F1b/F1c Fate routes). Added to `__all__`.

- **AC2 — `run_fate_action_dispatch` handler + registration (Task 2):** new `sidequest/agents/subsystems/fate_action.py` reads `dispatch.params`, builds a `FateActionPayload` (action/skill/target/difficulty/invoke_aspect/aspect_text mirroring `protocol/fate.py`), emits the classified span, then calls the existing `dispatch_fate_action`. Registered as `("fate_action", run_fate_action_dispatch)` in `_register_defaults` (+ module docstring). **Fail loud:** an invalid `action` (not one of overcome/create_advantage/attack/concede) raises `ValueError`; a non-Fate ruleset / no active encounter / unseated actor surfaces as `FateConflictError` caught and returned as `data["error"]="fate_dispatch_error"` (No Silent Fallbacks — the bank records the gap, never a silent success).

- **AC3 — Router Fate vocabulary (Task 3):** `_build_fate_summary(snapshot)` in `sidequest/server/intent_router_pass.py` projects per-PC skills, fate points, character aspects, live scene/situation aspects, and `active_conflict`. `_build_state_summary` adds a top-level `fate` block **only when** `pack.rules.ruleset == "fate"` (absent for native packs — same conditional-vocab discipline as `confrontation_types`). `FATE_ROUTING_RULES` (fully specified constant) spliced into `intent_router.py`'s `_SYSTEM_PROMPT`; behaviorally conditional ("emit `fate_action` ONLY when a `fate` block is present"), so it is safe in the static cached prompt for non-Fate packs.

- **AC4 — Precondition gate to active conflicts (Task 4):** `_fate_action_precondition_unmet(snapshot)` in `sidequest/agents/dispatch_precondition_gate.py` drops a `fate_action` dispatched with no active/unresolved encounter, emitting the loud `intent_router.dispatch.gated` span. Registered in `_INERT_PRECONDITIONS` + `_GATE_DISPATCHED_TYPE_KEY["fate_action"]="action"`. Does **not** also emit the magic-only `dispatch_engagement.*.mismatch` (the out-of-conflict overcome is epic §7.1's real fix, not this gate's job).

- **AC5 — End-to-end wiring through the real bank (Task 5):** `tests/server/test_fate_classifier_wiring.py` proves (1) runtime registry membership via `get_registered()` (NOT a source grep) and (2) a freeform `fate_action` `SubsystemDispatch` driven through the **real** `run_dispatch_bank` + **real** `get_ruleset_module("fate")` reaches `dispatch_fate_action` → resolves the exchange and fires **both** `fate.action.classified` and `fate.exchange.resolved`.

- **AC6 — Gate (Task 6, verification-only):** scoped `ruff check`/`ruff format`/`pyright` clean on the changed files; the F2a + Fate + router suites green (incl. routing-completeness lint); the non-Fate dispatch spine (existing subsystems, precondition/unregistered/confrontation paths) proven untouched — `fate_action` is purely additive (a registry entry + a behaviorally-conditional prompt section).

**Implementation Plan (complete — 6 TDD tasks, exact signatures + test code, full self-review, NO placeholders):**
`docs/superpowers/plans/2026-06-14-f2a-fate-action-classifier.md`

**Epic decomposition context (F2a–F2d slice map, shared contracts, OTEL inventory, open §7 decisions):**
`docs/superpowers/plans/2026-06-14-f2-narrator-intent-router-integration.md`

**Design Spec:** `docs/superpowers/specs/2026-06-14-fate-core-binding-replaces-native-design.md` §4.5, §6

**Decision of record:** ADR-144 (Fate Core binding replaces the native ruleset — two SRDs, zero homebrew). **Depends on:** F1a–F1d merged (`FateRulesetModule`, `FateActionPayload`, `dispatch_fate_action`, the 12 live Fate spans) — all merged to server `develop`.

**Architecture:** F2a rides the existing pre-narrator spine (ADR-113) — no parallel machinery. Classification is the existing `IntentRouter` (Haiku, forced tool-use), taught one new subsystem (`fate_action`) + the Fate vocabulary via the per-turn state summary + a static routing-rules section; NOT a second LLM call. Mechanical engagement is pre-narrator: the bank engages `dispatch_fate_action` on the canonical snapshot BEFORE the narrator runs, so F2b/F2c narrate already-real Fate state (producer-side Illusionism counter). In-conflict scope only by design.

**Tech Stack:** Python 3.14, FastAPI, pydantic v2, pytest (`-n0`), OpenTelemetry SDK, `uv`.

**Repository:** sidequest-server ONLY (NOT ui/content/daemon). Branch strategy: gitflow, base `develop`, feature branch `feat/f2a-fate-action-classifier`.

**Files in Scope (6 tasks):**
- Task 1: `sidequest/telemetry/spans/fate.py` — `fate_action_classified_span` + `SPAN_ROUTES` entry · test `tests/telemetry/test_fate_action_classified_span.py`
- Task 2: `sidequest/agents/subsystems/fate_action.py` (create) + `sidequest/agents/subsystems/__init__.py` (`_register_defaults` entry + docstring) · test `tests/agents/subsystems/test_fate_action_dispatch.py`
- Task 3: `sidequest/server/intent_router_pass.py` (`_build_fate_summary` + `fate`-block enrichment) + `sidequest/agents/intent_router.py` (`FATE_ROUTING_RULES` → `_SYSTEM_PROMPT`) · test `tests/server/test_fate_classifier_enrichment.py`
- Task 4: `sidequest/agents/dispatch_precondition_gate.py` (`_fate_action_precondition_unmet` + map entries) · test `tests/agents/test_fate_action_precondition_gate.py`
- Task 5: `tests/server/test_fate_classifier_wiring.py` (create) — end-to-end through the real bank + precondition gate
- Task 6: verification-only (lint/format/types/suites)

**Two implementer watch-points (carry into red/green):**
1. **Task 3 Step 5 — confirm the symbol.** Confirm the exact `_SYSTEM_PROMPT` assembly shape in `intent_router.py` before splicing `FATE_ROUTING_RULES` (module-level constant ~line 103–263). The constant text is fully specified; only the splice site needs a look. This is the one "confirm the symbol" note (same style as F1d's resolver-name note).
2. **Scope is in-conflict only by design.** The out-of-conflict overcome (a plain `resolve_action` skill check) is the named follow-up in epic §7.1 — do NOT expand F2a to cover it. The precondition gate drops out-of-conflict `fate_action`s loudly; the gap is flagged, not silently handled.

**Server-test gotchas (project memory):**
- DB: `postgresql://slabgorb@localhost:5432/sidequest_test` (both DB env vars) — the CI yml's `sidequest` role does NOT exist locally and fakes ~26F/1250E.
- Run the new tests with `uv run pytest -n0` (the plan's commands already use `-n0`).
- Registry-membership checks must use runtime `get_registered()`, NOT a source grep (server CLAUDE.md "No Source-Text Wiring Tests"). The plan already does this.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-14T16:39:39Z
**Round-Trip Count:** 0

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-14T16:02:14Z | 2026-06-14T16:06:03Z | 3m 49s |
| red | 2026-06-14T16:06:03Z | 2026-06-14T16:16:50Z | 10m 47s |
| green | 2026-06-14T16:16:50Z | 2026-06-14T16:33:43Z | 16m 53s |
| review | 2026-06-14T16:33:43Z | 2026-06-14T16:39:39Z | 5m 56s |
| finish | 2026-06-14T16:39:39Z | - | - |

## Branch & Context

**Branch Strategy:** gitflow (feat/f2a-fate-action-classifier off develop, sidequest-server subrepo)

**Story Context File:** `sprint/context/context-story-113-1.md`

## Sm Assessment

**Setup complete — story routed to TEA (The Architect) for the red phase.**

- **Story:** 113-1 — F2a Fate action classifier. 5 pts, server-only, tdd (phased: setup → red → green → review → finish).
- **Readiness:** Design and plan are both complete. The implementation plan is exhaustive — 6 TDD tasks, each red-first with the concrete test code already written, exact signatures, and a full self-review scan confirming zero placeholders. TEA writes RED straight from the plan's test code; Dev greens it task-by-task.
- **Dependencies:** F1a–F1d (the Fate ruleset module, `FateActionPayload`, `dispatch_fate_action`, the 12 live Fate spans) are all merged to server `develop` (verified: no open PRs, no in-review stories, origin/develop HEAD `1e883844`). F2a is purely additive on top — a new subsystem registry entry, a `fate` state-summary block, a behaviorally-conditional prompt section, a precondition-gate entry, and one new span. Nothing F2a touches is shared mutable state with F2b/F2c/F2d.
- **Merge gate:** CLEAR — 0 in-progress, 0 in-review, no open non-draft PRs in any repo (F1d / PR #858 already merged).
- **Doctrine guard for TEA/Dev:**
  - **ADR-144 / SOUL "Bind the Ruleset, Don't Balance It":** F2a binds the Fate Core SRD's four-action core; it does NOT recreate or tune any native mechanic. There is no native engine on the Fate path to balance against. If you catch yourself converting/gating a native beat/dial to "make it work with" Fate — stop.
  - **No `full_defense` creep:** Fate Core's four actions are overcome / create_advantage / attack / concede (+ the reactive Defend that Attack/Create-an-Advantage roll against). A "full defense"/"total defense" +2 stance is a d20-ism NOT in the Fate SRD — do not let it smuggle into the classifier or the routing rules.
  - **OTEL lie-detector (CLAUDE.md):** wiring is proven via the new `fate.action.classified` span + runtime `get_registered()` + the real-bank end-to-end drive, never a source-text grep. The classify span emits BEFORE dispatch so a classify-without-engage is visible to the GM panel.
  - **No Silent Fallbacks:** invalid action → `ValueError`; non-Fate ruleset / no conflict → `FateConflictError` surfaced as `data["error"]`; the precondition drop emits `intent_router.dispatch.gated`.
- **Acceptance criteria:** AC1–AC6 captured above, mapped 1:1 to the plan's 6 tasks. AC5 (end-to-end wiring through the real bank) is the mandatory wiring gate — it must fail on `develop` today and pass only when registry + confidence gate + handler + `dispatch_fate_action` + exchange are all wired through.

**Handoff:** The Architect — write the red phase against the plan at `docs/superpowers/plans/2026-06-14-f2a-fate-action-classifier.md`. Every task already carries concrete, red-first test code (Steps 1 in Tasks 1–5) with the exact import surface and fixtures; reuse the existing harnesses the tests import (`GameSnapshot`, `StructuredEncounter`, `FateSheet`, `run_dispatch_bank`, `get_ruleset_module`) rather than stubbing. Run new tests with `uv run pytest -n0` against `postgresql://slabgorb@localhost:5432/sidequest_test`.

## Design Deviations

### TEA (test design)
- **Added one test beyond the plan's enumerated test code: `test_fate_routing_rules_spliced_into_system_prompt`**
  - Spec source: `docs/superpowers/plans/2026-06-14-f2a-fate-action-classifier.md`, Task 3 (Step 5 + Step 6)
  - Spec text: "Splice it into the assembled system prompt … Run the router suite to confirm the prompt still assembles … the additive prompt section breaks no existing router test; the system prompt still builds."
  - Implementation: `tests/server/test_fate_classifier_enrichment.py::test_fate_routing_rules_spliced_into_system_prompt` asserts `FATE_ROUTING_RULES` is both defined (non-empty) AND present in `_SYSTEM_PROMPT`.
  - Rationale: AC3 has two halves — the `fate` state-summary enrichment (covered by the plan's 3 enrichment tests) and the `FATE_ROUTING_RULES` splice into the static prompt. The plan covers the splice only indirectly via "the existing router suite stays green," but that suite tests pre-existing behavior and is purely additive-safe: if Dev defines `FATE_ROUTING_RULES` but forgets the `+ FATE_ROUTING_RULES` splice, NO existing test fails. This direct assertion closes that wiring gap. It is additive coverage (more than the plan), not an omission or weakening.
  - Severity: minor
  - Forward impact: none on sibling stories. Dev must both define the constant and splice it into `_SYSTEM_PROMPT` (Task 3 Step 5) for this test to pass — which is exactly the AC3 requirement.

### Dev (implementation)
- **Handler uses `rng=random.Random()` + a new optional `rng` injection seam, not the plan's bare `rng=random` (module)**
  - Spec source: `docs/superpowers/plans/2026-06-14-f2a-fate-action-classifier.md`, Task 2 Step 3 (handler body + the note "`random` (the module) is the `rng` the production handler passes (matches `FateActionHandler` and `dispatch_dice_throw`)")
  - Spec text: "`rng=random,` … `random` (the module) is the `rng` the production handler passes"
  - Implementation: `run_fate_action_dispatch(..., rng: random.Random | None = None)` passes `rng=rng or random.Random()` to `dispatch_fate_action`. Production omits `rng` (the bank's `_filter_context_for_callable` supplies nothing → default `random.Random()`); tests inject `_FixedRng(0)` via `run_dispatch_bank(context={"rng": ...})` / the direct call.
  - Rationale: (1) The plan's note is factually wrong — the F1d sibling `sidequest/handlers/fate_action.py:85` passes `rng=random.Random()`, not the module; `dispatch_fate_action`'s param is typed `random.Random`, so passing the *module* is a pyright error (Task 6 Step 3 requires 0). (2) The plan's determinism strategy (a fully-depleted Thug taken out by "any" attack) is incomplete: the engine still rolls a *defense*, so an unseeded RNG sometimes makes the attack miss and the Thug survives — the two "attack lands" tests were flaky (passed in isolation by luck, failed in the combined run on `Thug.withdrawn is False`). The `rng` seam mirrors `dispatch_fate_action`'s own `rng` contract and the F1d test's `_FixedRng(0)` pattern, making the bank-driven wiring test deterministic without seeding global state.
  - Severity: minor
  - Forward impact: F2b/F2c handlers that reuse this entry inherit a testable `rng` seam (a feature, not a constraint). Production behavior is unchanged (fresh `random.Random()`).
- **The two span-asserting tests use the `otel_capture` conftest fixture, not the plan/RED's manual `trace.set_tracer_provider(...)`**
  - Spec source: TEA RED test code — `tests/agents/subsystems/test_fate_action_dispatch.py` + `tests/server/test_fate_classifier_wiring.py` (`_otel()` / inline `set_tracer_provider`)
  - Spec text: "`trace.set_tracer_provider(provider)` … install this provider as the process tracer for the assertion"
  - Implementation: both tests now take the `otel_capture` fixture (present in both `tests/agents/conftest.py` and `tests/server/conftest.py`), which attaches a fresh `InMemorySpanExporter` to the *global* provider via `init_tracer()` and tears it down per-test.
  - Rationale: OpenTelemetry's `set_tracer_provider` is set-once-per-process — a second call is ignored. In the combined run the alphabetically-earlier dispatch test claimed the global provider, so the wiring test's own provider was silently dropped and its exporter captured `[]` (the span assertions failed on order, not on behavior). `otel_capture` is the codebase's canonical order-independent span-capture pattern. No assertion changed; only the capture mechanism. The telemetry-span test was left as-is because it passes `_tracer=` explicitly (already order-independent).
  - Severity: minor
  - Forward impact: none — the production span emission is unchanged; this is a test-infrastructure correctness fix.

### Reviewer (audit)
- **TEA — added `test_fate_routing_rules_spliced_into_system_prompt`** → ✓ ACCEPTED by Reviewer: sound and genuinely additive. AC3 has two halves; the plan covered the prompt-splice only via "the existing router suite stays green," which is additive-safe and would NOT catch a forgotten `+ FATE_ROUTING_RULES`. The new test asserts the constant is non-empty AND present in `_SYSTEM_PROMPT` — closes a real wiring gap, strengthens coverage, weakens nothing. Verified the splice exists at `intent_router.py:292` (`+ FATE_ROUTING_RULES`).
- **Dev — `rng=random.Random()` + optional `rng` injection seam (vs the plan's `rng=random` module)** → ✓ ACCEPTED by Reviewer: the plan's note ("`random` the module … matches `FateActionHandler`") was factually wrong — the F1d sibling `sidequest/handlers/fate_action.py:85` passes `rng=random.Random()`, and `dispatch_fate_action`'s param is typed `random.Random` (the module would be a pyright error; Task 6 requires 0). The flakiness it fixes is real: the depleted-Thug fixture only removes *absorption* capacity, but the engine still rolls a *defense*, so an unseeded RNG sometimes misses (the combined-run failure on `Thug.withdrawn is False` confirmed it). The seam mirrors `dispatch_fate_action`'s own `rng` contract and the F1d `_FixedRng(0)` test pattern; production behavior is unchanged (`rng or random.Random()`). Minimal, correct.
- **Dev — `otel_capture` conftest fixture (vs the RED tests' `trace.set_tracer_provider`)** → ✓ ACCEPTED by Reviewer: `set_tracer_provider` is set-once-per-process, so the alphabetically-earlier dispatch test claimed the global provider and the wiring test's exporter captured `[]` (order-dependent, behavior-correct). `otel_capture` (present in both `tests/agents/conftest.py` and `tests/server/conftest.py`) attaches an exporter to the global provider — the codebase's canonical order-independent pattern. No assertion changed.
- **No undocumented deviations found.** The production diff matches the plan's File Structure and Tasks 1–4 exactly; the only departures from the plan's literal code are the two Dev deviations above, both logged. The deferred out-of-conflict overcome (epic §7.1) is correctly left unbuilt and the precondition gate drops it loudly.

## Delivery Findings

<!-- Append findings below. Append-only — never edit another agent's entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The `test_fate_action_dispatch.py` import of `run_fate_action_dispatch` currently sorts into the third-party import block (ruff classifies `sidequest.agents.subsystems.fate_action` as third-party because the module does not exist yet). Once Dev creates `sidequest/agents/subsystems/fate_action.py`, `ruff check` will reclassify it as first-party and flag I001; `ruff format` (plan Task 6 Step 2) auto-fixes it. Expected self-healing artifact of RED-before-module, not a defect — flagged so Dev is not surprised by the one-step re-sort. Affects `tests/agents/subsystems/test_fate_action_dispatch.py` (no action needed beyond the planned Task 6 format). *Found by TEA during test design.*
- **Question** (non-blocking): The non-Fate-ruleset handler test (`test_non_fate_ruleset_returns_error_not_silent_success`) asserts `out.data.get("error") == "fate_dispatch_error"` — this requires the handler to catch `FateConflictError` (a `ValueError` subclass) from `dispatch_fate_action` and return it as `data["error"]`, while the invalid-action path (`test_invalid_action_fails_loud`) requires a *raised* `ValueError` *before* the try/except. Dev must keep the action-validation `raise ValueError(...)` ABOVE the `try: dispatch_fate_action(...) except FateConflictError` block (as the plan's handler does), so a bad action propagates loud and a non-Fate ruleset is caught — they are deliberately different fail-loud shapes. Affects `sidequest/agents/subsystems/fate_action.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The plan's wiring/dispatch test design relied on a fully-depleted Thug to guarantee a taken-out, but the Fate engine still rolls a *defense* — with an unseeded RNG the attack sometimes misses, so the two "attack lands" tests were nondeterministic (green in isolation, red in the combined run). Resolved by adding an `rng` injection seam to the handler (mirroring `dispatch_fate_action`'s own `rng` param) + a `_FixedRng(0)` double in the tests (the F1d pattern). Future Fate handlers (F2b/F2c) should carry the same seam for deterministic bank-level tests. Affects `sidequest/agents/subsystems/fate_action.py` (already has the seam). *Found by Dev during implementation.*
- **Improvement** (non-blocking): The RED tests captured spans via `trace.set_tracer_provider(...)`, which is set-once-per-process — order-dependent and silently empty when another test claims the global provider first (it bit the wiring test in the combined run). Resolved by switching to the `otel_capture` conftest fixture (the codebase's canonical global-provider-attach pattern). Any future span-asserting test should prefer `otel_capture`/`otel_exporter` over `set_tracer_provider`. Affects `tests/agents/subsystems/test_fate_action_dispatch.py`, `tests/server/test_fate_classifier_wiring.py`. *Found by Dev during implementation.*
- The plan's `random` (module) vs `random.Random()` note was inaccurate (the F1d sibling passes `random.Random()`); the handler matches the sibling. No further upstream action needed.

### Reviewer (code review)
- **Improvement** (non-blocking): The `subsystems/__init__.py` module docstring still reads "All eight subsystems are live on the turn path" — the registry now holds 11 (`equip` + `environment_clock` predate this PR, `fate_action` is new). This PR adds the `fate_action` bullet to that docstring region but not the count. Affects `sidequest/agents/subsystems/__init__.py:34` (update "eight" → the live count, or drop the number). Pre-existing staleness, surfaced here because the diff touches the block. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `int(params.get("difficulty", 0) or 0)` raises `ValueError` on a non-numeric LLM `difficulty` (e.g. `"3.5"` or `"hard"`). This is caught by the dispatch bank's generic per-dispatch `except` → recorded as an error span → no engagement (fail-loud, consistent with No-Silent-Fallbacks). It is a *third* failure shape beyond the two documented in the handler docstring (invalid action → `ValueError`; non-Fate/no-conflict → `FateConflictError`). Independently noted by the security subagent as a robustness (not security) concern. Optional hardening for F2b: coerce defensively or validate difficulty in the handler. Affects `sidequest/agents/subsystems/fate_action.py:71`. *Found by Reviewer during code review.*
- **Question** (non-blocking): The router is *instructed* (FATE_ROUTING_RULES) not to emit a `confrontation` dispatch for the same action as a `fate_action`, but nothing structurally prevents the Haiku classifier from emitting both on one turn (a `confrontation` would try to *start* an encounter while `fate_action` acts *in* one). Not data-corrupting (the engines are independent and the precondition gate scopes `fate_action` to a live conflict), and out of F2a's classifier scope — flag for F2b/playtest validation of router disambiguation on Fate packs. Affects router behavior (no file change in F2a). *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** 2 findings (0 Gap, 0 Conflict, 0 Question, 2 Improvement)
**Blocking:** None

- **Improvement:** The `test_fate_action_dispatch.py` import of `run_fate_action_dispatch` currently sorts into the third-party import block (ruff classifies `sidequest.agents.subsystems.fate_action` as third-party because the module does not exist yet). Once Dev creates `sidequest/agents/subsystems/fate_action.py`, `ruff check` will reclassify it as first-party and flag I001; `ruff format` (plan Task 6 Step 2) auto-fixes it. Expected self-healing artifact of RED-before-module, not a defect — flagged so Dev is not surprised by the one-step re-sort. Affects `tests/agents/subsystems/test_fate_action_dispatch.py`.
- **Improvement:** The plan's wiring/dispatch test design relied on a fully-depleted Thug to guarantee a taken-out, but the Fate engine still rolls a *defense* — with an unseeded RNG the attack sometimes misses, so the two "attack lands" tests were nondeterministic (green in isolation, red in the combined run). Resolved by adding an `rng` injection seam to the handler (mirroring `dispatch_fate_action`'s own `rng` param) + a `_FixedRng(0)` double in the tests (the F1d pattern). Future Fate handlers (F2b/F2c) should carry the same seam for deterministic bank-level tests. Affects `sidequest/agents/subsystems/fate_action.py`.

### Downstream Effects

Cross-module impact: 2 findings across 2 modules

- **`sidequest/agents/subsystems`** — 1 finding
- **`tests/agents/subsystems`** — 1 finding

### Deviation Justifications

3 deviations

- **Added one test beyond the plan's enumerated test code: `test_fate_routing_rules_spliced_into_system_prompt`**
  - Rationale: AC3 has two halves — the `fate` state-summary enrichment (covered by the plan's 3 enrichment tests) and the `FATE_ROUTING_RULES` splice into the static prompt. The plan covers the splice only indirectly via "the existing router suite stays green," but that suite tests pre-existing behavior and is purely additive-safe: if Dev defines `FATE_ROUTING_RULES` but forgets the `+ FATE_ROUTING_RULES` splice, NO existing test fails. This direct assertion closes that wiring gap. It is additive coverage (more than the plan), not an omission or weakening.
  - Severity: minor
  - Forward impact: none on sibling stories. Dev must both define the constant and splice it into `_SYSTEM_PROMPT` (Task 3 Step 5) for this test to pass — which is exactly the AC3 requirement.
- **Handler uses `rng=random.Random()` + a new optional `rng` injection seam, not the plan's bare `rng=random` (module)**
  - Rationale: (1) The plan's note is factually wrong — the F1d sibling `sidequest/handlers/fate_action.py:85` passes `rng=random.Random()`, not the module; `dispatch_fate_action`'s param is typed `random.Random`, so passing the *module* is a pyright error (Task 6 Step 3 requires 0). (2) The plan's determinism strategy (a fully-depleted Thug taken out by "any" attack) is incomplete: the engine still rolls a *defense*, so an unseeded RNG sometimes makes the attack miss and the Thug survives — the two "attack lands" tests were flaky (passed in isolation by luck, failed in the combined run on `Thug.withdrawn is False`). The `rng` seam mirrors `dispatch_fate_action`'s own `rng` contract and the F1d test's `_FixedRng(0)` pattern, making the bank-driven wiring test deterministic without seeding global state.
  - Severity: minor
  - Forward impact: F2b/F2c handlers that reuse this entry inherit a testable `rng` seam (a feature, not a constraint). Production behavior is unchanged (fresh `random.Random()`).
- **The two span-asserting tests use the `otel_capture` conftest fixture, not the plan/RED's manual `trace.set_tracer_provider(...)`**
  - Rationale: OpenTelemetry's `set_tracer_provider` is set-once-per-process — a second call is ignored. In the combined run the alphabetically-earlier dispatch test claimed the global provider, so the wiring test's own provider was silently dropped and its exporter captured `[]` (the span assertions failed on order, not on behavior). `otel_capture` is the codebase's canonical order-independent span-capture pattern. No assertion changed; only the capture mechanism. The telemetry-span test was left as-is because it passes `_tracer=` explicitly (already order-independent).
  - Severity: minor
  - Forward impact: none — the production span emission is unchanged; this is a test-infrastructure correctness fix.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-pt feature adding net-new engine surface (a subsystem handler, a router projection, a precondition predicate, an OTEL span) — full RED coverage required, not a chore bypass.

**Test Files (5) — AC mapping:**
- `tests/telemetry/test_fate_action_classified_span.py` — **AC1**: `fate_action_classified_span` emits `fate.action.classified` with actor/action/skill/target attributes; the span is registered in `SPAN_ROUTES` as a `state_transition` route extracting `field=action_classified` + `action` (GM-panel surfaced).
- `tests/agents/subsystems/test_fate_action_dispatch.py` — **AC2**: `run_fate_action_dispatch` builds the payload, routes to `dispatch_fate_action`, resolves the solo exchange (`Thug.withdrawn`, `enc.resolved`), and emits both `fate.action.classified` + `fate.exchange.resolved`; invalid action raises `ValueError` (fail-loud, rule #1); `fate_action` is in the runtime `get_registered()` registry (No-Source-Text-Wiring); a non-Fate ruleset returns `data["error"]="fate_dispatch_error"` and engages nothing (No-Silent-Fallback surfaced).
- `tests/server/test_fate_classifier_enrichment.py` — **AC3**: `_build_fate_summary` projects skills/fate_points/character_aspects/scene_aspects/active_conflict; `_build_state_summary` carries the `fate` block for a `ruleset:fate` pack and OMITS it for a native pack (conditional vocabulary); `FATE_ROUTING_RULES` is defined and spliced into `_SYSTEM_PROMPT` (added test — see Design Deviations).
- `tests/agents/test_fate_action_precondition_gate.py` — **AC4**: `_fate_action_precondition_unmet` returns a reason with no/resolved encounter and `None` with an active conflict; `run_dispatch_precondition_gate` drops the out-of-conflict `fate_action` and emits `intent_router.dispatch.gated` (loud skip, not silent).
- `tests/server/test_fate_classifier_wiring.py` — **AC5 (mandatory wiring)**: runtime `get_registered()` membership + a freeform `fate_action` `SubsystemDispatch` driven through the **real** `run_dispatch_bank` (real `get_ruleset_module("fate")`, real exchange) → `decision == "engaged"`, `Thug.withdrawn`, `enc.resolved`, and both `fate.action.classified` + `fate.exchange.resolved` fire.

**Tests Written:** 15 tests across 5 files covering AC1–AC5. (AC6 is a verification-only gate — scoped lint/format/types/suites — discharged by the green/verify phases, not a unit test.)

**RED verification:** Run serially with `uv run pytest -n0` against `SIDEQUEST_TEST_DATABASE_URL=postgresql://slabgorb@localhost:5432/sidequest_test`. All 15 fail/error for **feature-missing reasons only** — verified directly (not via testing-runner, which project memory flags as hallucination-prone and session-clobbering):
- 4 files error at collection with the exact missing-symbol import errors:
  - `cannot import name 'fate_action_classified_span' from 'sidequest.telemetry.spans.fate'` (AC1)
  - `No module named 'sidequest.agents.subsystems.fate_action'` (AC2)
  - `cannot import name '_build_fate_summary' from 'sidequest.server.intent_router_pass'` (AC3)
  - `cannot import name '_fate_action_precondition_unmet' from 'sidequest.agents.dispatch_precondition_gate'` (AC4)
- `test_fate_classifier_wiring.py` imports only existing symbols, so it executes against the **real bank + live Postgres** and fails precisely on `"fate_action" not in get_registered()` and `decision == 'unknown_subsystem'` (logged `subsystems.unknown subsystem=fate_action`) — proving the entire fixture harness (snapshot/encounter/FateSheet/real dispatch bank/DB) is sound and the ONLY missing piece is production code.

Import-surface pre-verified before writing (TEA paranoia): every existing symbol the fixtures touch was confirmed present and signature-compatible — `get_ruleset_module` re-exported from `sidequest.game.ruleset`; `native`/`fate` slugs registered (so the non-Fate test resolves the native module then `dispatch_fate_action` raises `FateConflictError` on the isinstance gate); `FateActionPayload` fields match the handler exactly; `_build_state_summary(*, pack=…)`, `run_dispatch_precondition_gate(*, package, snapshot, tracer)`, `FateSheet`/`Aspect`/`StressBox`/`StructuredEncounter`/`GameSnapshot` constructors and `AspectKind` literal values (`high_concept`/`situation`/`consequence`) all confirmed.

### Rule Coverage

| Rule (lang-review/python.md + server CLAUDE.md) | Test(s) | Status |
|------|---------|--------|
| #1 Silent exception swallowing → fail loud | `test_invalid_action_fails_loud` (bad action raises `ValueError`, not swallowed); `test_non_fate_ruleset_returns_error_not_silent_success` (engine rejection surfaced as `data["error"]`, never a silent success) | failing |
| #6 Test quality — meaningful assertions | All 15 tests assert concrete values (span attrs, `withdrawn`/`resolved` booleans, dict shapes, membership/non-membership, raised exceptions); 0 vacuous (`assert True`/bare-truthy); no source-text greps | self-check passed |
| No Source-Text Wiring Tests (server CLAUDE.md) | `test_fate_action_is_a_registered_subsystem`, `test_fate_action_is_registered_in_the_live_bank` (runtime `get_registered()`), `test_freeform_fate_action_engages_the_exchange_through_the_bank` (real-bank drive + OTEL span assertions) — no `read_text()`/regex on source | failing |
| OTEL Observability (every subsystem decision emits a span) | `fate.action.classified` asserted in Task 1 + Task 2 + Task 5; `fate.exchange.resolved` asserted through the real path (Task 2 + Task 5); `intent_router.dispatch.gated` asserted on the gate drop (Task 4) | failing |
| Doctrine ADR-143/-144 (bind, don't balance; no `full_defense`) | No native beat/dial/edge mechanic asserted anywhere; only the Fate four-action core + `dispatch_fate_action`; no `full_defense`/defense-stance param in any payload | n/a (compliant by construction) |

**Rules checked:** 3 of 13 lang-review rules + 2 project rules have targeted coverage. The remaining lang-review rules do not apply to this span/handler/router-vocab/gate change: #2 mutable defaults (none introduced), #3 type annotations (public surfaces fully annotated per plan), #4 logging (handler logs `logger.warning` on the caught `FateConflictError`), #5 path handling (no paths), #7 resource leaks (span emitters use `with Span.open(...)`), #8 unsafe deserialization (none), #9 async pitfalls (async handler, no blocking calls), #10 import hygiene (`__all__` updated per AC1), #11 input validation (action validated against `_VALID_ACTIONS`), #12/#13 dependency/fix-regression (no deps added).

**Self-check:** 0 vacuous tests found. Negative assertions present (`"fate" not in summary`, `enc.resolved is False`, `_fate_action_precondition_unmet(...) is None`), fail-loud paths covered (raised `ValueError` + surfaced engine error), and the mandatory wiring test drives production code through the real bank.

**Handoff:** To Dev (Agent Smith) for the green phase. Implement Tasks 1–6 from the plan in order; each task's Step 3+ gives the exact production code. Two non-blocking Delivery Findings to weigh (the import re-sort artifact and the two-different-fail-loud-shapes note). Doctrine guard stands: no native mechanic touched (ADR-143/-144), no `full_defense` creep, OTEL on every decision, no silent fallbacks. Run the suite with `uv run pytest -n0` against `SIDEQUEST_TEST_DATABASE_URL=postgresql://slabgorb@localhost:5432/sidequest_test`.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/telemetry/spans/fate.py` — `fate_action_classified_span` emitter + `SPAN_ROUTES["fate.action.classified"]` (state_transition / fate route) + `__all__` entry (AC1).
- `sidequest/agents/subsystems/fate_action.py` (new) — `run_fate_action_dispatch`: validates the action (fail-loud `ValueError`), builds `FateActionPayload`, emits the classified span before dispatch, routes to `dispatch_fate_action`, catches `FateConflictError` → `data["error"]="fate_dispatch_error"`. Carries an optional `rng` injection seam (default `random.Random()`) (AC2).
- `sidequest/agents/subsystems/__init__.py` — `("fate_action", run_fate_action_dispatch)` in `_register_defaults` + import + docstring bullet (AC2).
- `sidequest/server/intent_router_pass.py` — `_build_fate_summary` (skills/fate_points/character_aspects/scene_aspects/active_conflict) + the `fate`-block enrichment in `_build_state_summary`, gated on `pack.rules.ruleset == "fate"` (AC3).
- `sidequest/agents/intent_router.py` — `FATE_ROUTING_RULES` constant + `+ FATE_ROUTING_RULES` spliced at the end of the `_SYSTEM_PROMPT` concatenation (after `CONFRONTATION_TRIGGER_CORE`) (AC3).
- `sidequest/agents/dispatch_precondition_gate.py` — `_fate_action_precondition_unmet` + `_INERT_PRECONDITIONS["fate_action"]` + `_GATE_DISPATCHED_TYPE_KEY["fate_action"]="action"` (AC4).
- `tests/agents/subsystems/test_fate_action_dispatch.py`, `tests/server/test_fate_classifier_wiring.py` — determinism (`_FixedRng(0)` + `rng` injection) and order-independent span capture (`otel_capture` fixture). Assertions unchanged. See Design Deviations.

**Tests:** 15/15 F2a tests GREEN, stable across 3 consecutive runs (flakiness eliminated). Wider verification:
- Scoped `ruff check` clean (the predicted import re-sort self-healed on `--fix`); `ruff format` left all 11 files unchanged.
- `pyright` on all 6 changed production files: **0 errors, 0 warnings**.
- F2a + Fate + routing-completeness suites: **38 passed** (incl. `test_fate_dispatch_routing.py`, `test_fate_conflict.py`, `test_routing_completeness.py` — the literal-keyed route needs no `SPAN_*` constant, lint stays green).
- Non-Fate dispatch spine (`tests/agents/subsystems/` + `tests/agents/ -k "dispatch or precondition or confrontation or router"`): **390 passed, 3 skipped** — the `FATE_ROUTING_RULES` splice broke no existing router test (watch-point #1 confirmed), and the new registry/precondition entries are purely additive.
- Neighbor suites: telemetry `-k "fate or routing or span"` **286 passed**; server `-k "intent_router or state_summary"` **87 passed**.
- Run with `uv run pytest -n0` against `SIDEQUEST_TEST_DATABASE_URL=postgresql://slabgorb@localhost:5432/sidequest_test`.

**Branch:** `feat/f2a-fate-action-classifier` (pushed; green HEAD on top of TEA's RED commit `4a7a9850`).

**Self-review (judgment checks):**
- *Wired end-to-end:* AC5's wiring test drives the **real** `run_dispatch_bank` → confidence gate → `run_fate_action_dispatch` → real `get_ruleset_module("fate")` → `dispatch_fate_action` → exchange resolves; both `fate.action.classified` and `fate.exchange.resolved` fire. Runtime `get_registered()` confirms registration. Non-test consumer = the live dispatch bank.
- *Follows project patterns:* literal-keyed `SPAN_ROUTES` (F1b/F1c style), capability-gated state-summary vocab (mirrors `confrontation_types`/`witnessed_act_vocabulary`), `_INERT_PRECONDITIONS` registry entry, `rng` seam mirroring `dispatch_fate_action`/`FateActionHandler`.
- *All ACs met:* AC1–AC5 green; AC6 (lint/format/types/suites + spine-untouched) discharged above.
- *Error handling:* fail-loud throughout — invalid action raises `ValueError`; non-Fate ruleset / no conflict / unseated actor → `FateConflictError` surfaced as `data["error"]` (No Silent Fallbacks); the precondition drop emits `intent_router.dispatch.gated`.
- *Doctrine:* no native beat/dial/edge mechanic touched (ADR-143/-144); no `full_defense` creep (the four-action core only); the classify span emits BEFORE dispatch so classify-without-engage is GM-panel-visible.

**Handoff:** To Reviewer (The Merovingian) for code review. Two minor Design Deviations logged with rationale (the `rng` seam + `random.Random()` vs the plan's `rng=random`; the `otel_capture` span-capture switch) — both are correctness fixes that strengthen the tests without changing any assertion or production behavior.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (17 tests GREEN: 15 F2a + 2 routing-completeness; ruff clean; format clean; pyright 0 errors; 0 code smells; purely additive 708/0) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings (test quality assessed by Reviewer directly — see Assessment) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings (doc/comment assessed by Reviewer directly — 1 LOW found) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | 0 (action allowlist-gated; no SQL/shell/eval/path/pickle sink; OTEL attrs game-mechanical only; prompt-injection neutralized by allowlist + no dangerous sink) | confirmed 0, dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings (full lang-review enumeration done by Reviewer directly — see Rule Compliance) |

**All received:** Yes (2 enabled returned clean, 7 disabled pre-filled)
**Total findings:** 0 blocking confirmed; 2 LOW + 1 Question (non-blocking) raised by Reviewer's own analysis covering the disabled specialists' domains.

## Reviewer Assessment

**Verdict:** APPROVED

The production code is clean, additive, fail-loud, OTEL-instrumented, and doctrine-compliant. Both enabled subagents (preflight, security) returned clean; I covered the 7 disabled specialists' domains myself (edge, silent-failure, test, doc, type, simplify, rule). No Critical or High issues. The 2 LOW findings + 1 Question are non-blocking and logged as Delivery Findings.

**Data flow traced (cause → effect):** player freeform text → `IntentRouter` (Haiku) sees the gated `fate` state-summary block (`intent_router_pass.py:384`, only when `pack.rules.ruleset == "fate"`) + the static `FATE_ROUTING_RULES` → emits `SubsystemDispatch(subsystem="fate_action", params={action,…})` → `run_dispatch_precondition_gate` drops it (loud `intent_router.dispatch.gated`) if `snapshot.encounter is None or resolved` → else `run_dispatch_bank` confidence-gates and invokes `run_fate_action_dispatch` → action validated against `_VALID_ACTIONS` (raises `ValueError` on miss) → builds `FateActionPayload` → emits `fate.action.classified` **before** dispatch (so classify-without-engage is GM-panel-visible) → `dispatch_fate_action` (real Fate engine, `isinstance`-gated) seals/resolves the exchange → `FateConflictError` (non-Fate / no conflict / unseated) caught → `data["error"]="fate_dispatch_error"` (surfaced, not swallowed). **Safe because** the only LLM-controlled values (`skill`/`target`/`aspect_text`/`invoke_aspect`/`difficulty`) reach no SQL/shell/eval/path sink — they flow into a pydantic `FateActionPayload` then the Fate engine; `action` is allowlist-gated.

**Pattern observed:** literal-keyed `SPAN_ROUTES["fate.action.classified"]` (no `SPAN_*` constant) at `spans/fate.py:300` — matches the F1b/F1c Fate-route idiom and is correctly excluded from the routing-completeness lint (verified: 2/2 pass). Capability-gated state-summary vocabulary at `intent_router_pass.py:384` mirrors `confrontation_types`/`witnessed_act_vocabulary` exactly. `_INERT_PRECONDITIONS`/`_GATE_DISPATCHED_TYPE_KEY` registry entries mirror `magic_working`. The `rng` seam mirrors `dispatch_fate_action`'s own `rng` param and the F1d `_FixedRng(0)` test double. Idiomatic throughout.

**Error handling:** fail-loud, no silent fallbacks. Invalid action → `ValueError` (`fate_action.py:64`); engine rejection → `FateConflictError` surfaced as `data["error"]` (`fate_action.py:104-106`, `logger.warning` lazy-%s, correct level for a client/config error); precondition drop emits a loud span; `get_ruleset_module` on an unknown slug raises `UnknownRulesetError` uncaught (intentional loud failure, unreachable in prod because the router gates on `ruleset=="fate"`).

**Wiring (VERIFIED):** `[VERIFIED] fate_action reachable end-to-end — tests/server/test_fate_classifier_wiring.py drives the REAL run_dispatch_bank + real get_ruleset_module("fate") → dispatch_fate_action → exchange resolves (Thug.withdrawn, enc.resolved) and both fate.action.classified + fate.exchange.resolved fire; runtime get_registered() confirms registration (subsystems/__init__.py:204). No source-text grep.` Complies with server CLAUDE.md "Every Test Suite Needs a Wiring Test" + "No Source-Text Wiring Tests".

### Rule Compliance (lang-review/python.md, exhaustive over the 6 production files)

- **#1 Silent exception swallowing:** COMPLIANT — the one `except FateConflictError` surfaces via `data["error"]` + `logger.warning`; no bare/blanket excepts; invalid action raises.
- **#2 Mutable default arguments:** COMPLIANT — `rng=None`, `target=""`, `confidence=0.0`, `difficulty=0`; `**attrs` keyword-only. No list/dict/set defaults.
- **#3 Type annotations at boundaries:** COMPLIANT — `run_fate_action_dispatch`, `_build_fate_summary`, `_fate_action_precondition_unmet`, `fate_action_classified_span` all fully annotated (params + return).
- **#4 Logging coverage/correctness:** COMPLIANT — `logger.warning("fate_action.dispatch_error error=%s", exc)` lazy-%s, warning for a client/config error.
- **#5 Path handling:** N/A — no path operations.
- **#6 Test quality:** COMPLIANT — every test asserts concrete values (span attrs, `withdrawn`/`resolved` booleans, dict shapes, membership AND non-membership, raised exceptions); 0 vacuous; `_FixedRng(0)` and `otel_capture` are legitimate test doubles/fixtures, not assertion-weakeners; the wiring test drives production code.
- **#7 Resource leaks:** COMPLIANT — `fate_action_classified_span` uses `with Span.open(...)`.
- **#8 Unsafe deserialization:** COMPLIANT — no pickle/eval/exec/unsafe-yaml/shell=True (security subagent confirmed).
- **#9 Async pitfalls:** COMPLIANT — `run_fate_action_dispatch` is async; `dispatch_fate_action` is sync CPU work (dice), correctly called without `await`; no blocking I/O, no missing await, no gather.
- **#10 Import hygiene:** COMPLIANT — no star imports; `__all__` updated in both `fate.py` and `fate_action.py`; imports sorted (ruff I001 clean).
- **#11 Input validation at boundaries:** COMPLIANT — `action` allowlist-gated before any engine call; other LLM params str-coerced into a pydantic model; no dangerous sink (security subagent confirmed).
- **#12 Dependency hygiene:** COMPLIANT — no dependency changes.
- **#13 Fix-introduced regressions:** COMPLIANT — the Dev determinism/otel fixes introduce no new class of issue (re-scanned).
- **Project rules:** No Silent Fallbacks ✓; OTEL-on-every-decision ✓ (classify/exchange/gated spans); No Source-Text Wiring ✓; ADR-143/-144 "bind don't balance" ✓ (no native beat/dial/edge touched); no `full_defense` creep ✓ (four-action core only, and `FateActionPayload`/`FATE_ROUTING_RULES` carry no defense-stance param).

### Devil's Advocate

Assume this is broken. The sharpest angle is the **LLM-to-engine trust boundary**: `params` come from Haiku classifying *player-controlled freeform prose*, so a malicious player could try to coax a malformed dispatch. What's the worst they get? `action` is allowlist-gated (anything outside the four raises `ValueError`, caught loud) — no injection. `difficulty` is the one unguarded coercion: `int("hard")` raises `ValueError`, but it propagates into the bank's generic catch and becomes an error span, not a crash or a silent wrong-value — annoying, not dangerous. `skill`/`target`/`aspect_text` reach only string lookups in the Fate engine (skill-key match, `encounter.find_actor` name match, an aspect-ledger write) — no SQL, shell, eval, or path, so prompt injection has no sink to escalate into. A *confused* player typing a non-combat action in a Fate conflict just gets the router's best-fit classification or no dispatch; an out-of-conflict action is dropped loudly by the precondition gate AND the prompt tells the model not to emit it (belt and suspenders). Could the GM panel be *lied to*? The classify span fires before dispatch, so a classify-without-engage is *visible*, not hidden — that's the intended honesty, not a gap. The one genuine soft spot is **double-dispatch** (confrontation + fate_action on the same turn) — mitigated only by a prompt instruction, not structurally — but it is out of the classifier's scope, non-corrupting (independent engines), and correctly flagged for F2b/playtest. The stale "eight subsystems" docstring is cosmetic. The `UnknownRulesetError`-uncaught path is unreachable in prod (router gates on `ruleset=="fate"`, which is registered) and fails loud if it ever fires. Nothing here corrupts state, leaks secrets, or silently improvises mechanics. The runtime is honest and the proof (the real-bank wiring test) is honest. (238 words.)

**Handoff:** To SM (Morpheus) for the finish phase (PR creation + merge). I do NOT merge.

[EDGE] disabled — assessed by Reviewer: `int(difficulty)` coercion edge noted LOW (fail-loud). [SILENT] disabled — assessed by Reviewer: no swallowed errors; the one catch surfaces via `data["error"]`. [TEST] disabled — assessed by Reviewer: 0 vacuous, wiring test drives real bank, determinism doubles legitimate. [DOC] disabled — assessed by Reviewer: stale "eight subsystems" count, LOW non-blocking. [TYPE] disabled — assessed by Reviewer: all boundaries annotated, `rng` seam correctly typed. [SEC] clean (subagent). [SIMPLE] disabled — assessed by Reviewer: minimal, no over-engineering, mirrors existing idioms. [RULE] disabled — assessed by Reviewer: 13/13 lang-review rules compliant (see Rule Compliance). [PREFLIGHT] clean (subagent) — tests/lint/format/types all green.