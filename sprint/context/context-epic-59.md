# Epic 59: Intent Router — Mechanical-Engagement Spine (REFRAMED 2026-05-23)

> **Reframe note (Houlihan, 2026-05-23).** This epic was originally scoped
> as a single-bug fix for the 2026-05-21 Glenross confrontation-engagement
> regression (Story 59-1, `begin_confrontation` SDK tool — shipped via
> server PRs #378 + #379, merged into develop). Re-inventory on 2026-05-23
> revealed:
>
> 1. The `begin_confrontation` tool is a **targeted point-fix**. It works
>    mechanically (fixture tests pass) and pins confrontation engagement
>    on the SDK backend. AC1's "LLM free tool-choice" leg is still owed
>    via playtest.
> 2. The underlying disease is broader and systemic: **every mechanical
>    engine on the SDK backend rides on the narrator self-reporting a
>    sidecar field, and the narrator emits those unreliably or not at
>    all.** Confrontation was the visible symptom; magic_working,
>    scenario_clue, distinctive_detail, and others fail the same way.
> 3. **Half the receiving plumbing for the real fix is already merged
>    and dormant** — the 2026-04-23 LocalDM Group A/B work shipped
>    `DispatchPackage` types, the `run_dispatch_bank` topo-sort executor,
>    `lethality_arbiter`, `prompt_redaction.redact_dispatch_package`, and
>    5 orchestrator consumer sites all wired to *consume* a
>    DispatchPackage. The single missing piece is the **producer** —
>    `LocalDM` was taken off the live path 2026-04-28 (commit `74d352c`,
>    PR #96) because it was a `claude -p` subprocess that doubled
>    per-turn latency. The shelving reason is now obsolete: Haiku is a
>    cheap SDK call, not a subprocess spawn.
>
> Story 59-1 (`begin_confrontation`) is retained as `done` — it's the
> point-fix that exposed the broader scope and serves as Phase 0 of the
> new shape. The epic now spans the full Intent Router build, atomic
> migration off self-reported engagement fields, and a non-keyword
> OTEL lie-detector watcher to keep us honest.

## Overview

Restore a single authoritative routing spine: a **pre-narrator pass**
that reads each player's submitted action, infers intent as
confidence-scored advisory dispatches, and **engages the matching
mechanical engine directly — before the narrator runs.** The narrator
then narrates already-real state and cannot wing the mechanics. Every
decision emits OTEL so the GM panel can see the engine engaged (not
improvised).

**Priority:** P1 (SOUL Illusionism failure mode — convincing prose with
zero mechanical backing is a project-existential bug)
**Repo:** server
**Stories:** 8 — 59-1 (done, retained) + 59-2 through 59-8 (new, ~29 pts)
**Cross-cutting:** retires the self-reported engagement field path, deprecates
the `_SDK_TOOL_OWNED_FIELDS` zeroing logic for engagement fields, supersedes
ADR-013 on the SDK path, amends ADR-111.

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Spec: Intent Router — Mechanical-Engagement Spine** (`sidequest-server/docs/superpowers/specs/2026-05-22-intent-router-mechanical-engagement-spine-design.md`, PR #385) | The authoritative design. §1 problem, §3 architecture, §5 fail-loud / no-fallback policy, §7 stealth-out-of-scope, §8 testing, §9 migration sequencing. **Read this first.** |
| **Spec: 2026-04-23 Local DM Decomposer Design** (`sidequest-server/docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md`) | Original LocalDM design that produced the merged consumer plumbing (DispatchPackage types, run_dispatch_bank executor, subsystems/, lethality_arbiter, redact_dispatch_package). Group A/B shipped 2026-04; Group E (live wiring) shelved 2026-04-28. |
| **Spec: 2026-04-28 LocalDM Offline-Only Design** (`sidequest-server/docs/superpowers/specs/2026-04-28-localdm-offline-only-design.md`) | The shelving decision. **REVERSED by this epic** — the live path is restored, the offline corpus runner stays as a separate concern. |
| **SOUL.md** (root) | "Illusionism" / "Cost Scales with Drama" — the principle this epic enforces |
| **ADR-067 Unified Narrator Agent** (`docs/adr/067-unified-narrator-agent.md`) | The narrator-as-single-agent decision. Intent Router is the pre-narrator routing layer that doesn't violate this — it engages engines *before* the unified narrator runs |
| **ADR-101 Anthropic SDK Backend** (`docs/adr/101-anthropic-sdk-narrator-backend.md`) | Per-call model routing — Haiku now affordable as a pre-pass without subprocess penalty |
| **ADR-102 Tool-Use Protocol** (`docs/adr/102-tool-use-protocol-structured-output.md`) | The SDK-tool-owned partition the engagement fields are retired from |
| **ADR-111 Recency-Zone Narrator Guardrails into Tool Descriptions** (`docs/adr/111-narrator-guardrails-into-tool-descriptions.md`) | Currently routes engagement criteria onto `begin_confrontation`'s description. **Amends in 59-4** when `begin_confrontation` retires — criteria move to the router's tool prompt |
| **ADR-013 Lazy JSON Extraction** (`docs/adr/013-lazy-json-extraction.md`, drift) | The narrator-emits-sidecar model this epic finally retires on the SDK path. Updates to `superseded-by: 113` in 59-2 |
| **ADR-073 Local Fine-Tuned Model** (`docs/adr/073-local-fine-tuned-narrator-architecture.md`) | The future backend swap point. IntentRouter takes an injected `LlmClient` so the Haiku→local-model swap is later injection, not rewrite |
| **ADR-031 Game Watcher** (`docs/adr/031-game-watcher.md`) | The OTEL discipline the per-dispatch spans honor |

## Background

### What shipped (Phase 0, Story 59-1)

- `sidequest/agents/tools/begin_confrontation.py` — SDK tool that VALIDATES a
  requested confrontation type and SIGNALS engagement via `result.confrontation`.
  Does not create the encounter itself; `narration_apply` consumes the
  result.confrontation field and calls `instantiate_encounter_from_trigger`
  on the canonical snapshot.
- `output_only_sdk.md:97-121` — narrator prompt routes STARTING to
  `begin_confrontation`
- `telemetry/spans/confrontation_intent.py` — `SPAN_CONFRONTATION_UNENGAGED_TURN`
  structural span (not keyword scanning)
- 4 test files: `tests/agents/test_59_1_confrontation_engagement.py`,
  `tests/server/test_59_1_confrontation_engagement.py`,
  `tests/agents/tools/test_begin_confrontation.py`,
  `tests/agents/test_narrator_sdk_hybrid_split.py`
- ADR-111 amended 2026-05-22 to recognize `begin_confrontation` as the
  routing target the rule already permitted

This works. Fixture tests pin the deterministic substrate. The LLM-behavior
leg (does Sonnet/Opus actually call `begin_confrontation` in a real
Glenross session?) is the owed playtest — folded into the epic-wide
playtest validation (59-8).

### What's half-built (the dormant consumer plumbing)

| Component | Location | State |
|-----------|----------|-------|
| `DispatchPackage` protocol (per_player, cross_player, dispatch, narrator_directives, lethality_verdicts) | `sidequest/protocol/dispatch.py` | **Merged, alive, unused on live path** |
| `run_dispatch_bank` topo-sort executor | `sidequest/agents/subsystems/__init__.py:160` | **Merged, alive, never called** |
| `_topo_sort` for depends_on ordering | `sidequest/agents/subsystems/__init__.py:134` | **Merged** |
| `lethality_arbiter.py` (operates on DispatchPackage) | `sidequest/agents/lethality_arbiter.py` | **Merged** |
| `prompt_redaction.redact_dispatch_package` (visibility-tag filtering) | `sidequest/agents/prompt_redaction.py` | **Merged** |
| 5 orchestrator consumer sites (`context.dispatch_package` guards) | `orchestrator.py:1420, 2281, 2296, 2772, 3074` | **Merged, all guarded `if … is not None`, permanently None on SDK path** |
| Three subsystem handlers (chassis_voice, distinctive_detail, npc_agency, reflect_absence) | `sidequest/agents/subsystems/*.py` | **Merged** |
| LocalDM producer | `sidequest/agents/local_dm.py:462` | **DORMANT** since 2026-04-28; the only `DispatchPackage(…)` construction site in non-test code |

### What's broken (the producer-shaped hole)

Per `orchestrator.py:1088` — `_SDK_TOOL_OWNED_FIELDS` zeroes the narrator's
emitted `confrontation` (mapped to advance tools) so even if the narrator
self-reports engagement, the SDK assembler discards it. The only path that
can SET `result.confrontation` today is `begin_confrontation` itself (via
`_assemble_turn_result_sdk` from the tool-call ledger). Magic engagement,
clue advancement, NPC agency dispatches — none have an equivalent tool;
they all wait on narrator sidecar emission that doesn't reliably happen.

`local_dm.py`'s docstring still reads: `"""local_dm — DORMANT. This module
is not invoked on the live turn path as of 2026-04-28…"""`. The 2026-04-28
shelving reason (second `claude -p` subprocess doubles per-turn latency)
is **obsolete** — Haiku via SDK is a single API call sharing the same
transport as the narrator, with per-call model routing already wired in
`agents/model_routing.py:28` (`CallType.CLASSIFICATION → claude-haiku-4-5`).

### Why not a successor epic?

I considered opening Epic 62 with `supersedes: 59` and leaving 59 closed.
Rejected because:

1. **The active sprint shard `sprint/epic-59.yaml` was never closed** — it
   still has 59-1 as `backlog`, despite the work having shipped on develop.
   This is a tracker-side drift that wants cleaning regardless. Reusing 59
   forces the cleanup as part of the reframe.
2. **The scope discovery happened inside this epic's lifecycle** — Houlihan's
   2026-05-22 spec reframe came two days into the original 59-1 implementation.
   Treating that as "new epic" obscures the audit trail.
3. **The shipped point-fix and the broader scope are mechanically continuous**
   — `begin_confrontation` is the engagement signal the router will eventually
   subsume, in the same code path. Keeping them in one epic makes the
   migration sequence and ADR amendments coherent.

The archive shard `sprint/archive/epic-59.yaml` (a snapshot taken at the
mid-reframe moment) stays as historical evidence; the active shard becomes
the canonical reframed record.

## Architecture Decision

**Decision:** Open Epic 59 stays active. Story 59-1 marked `done` (matches
shipped reality). Epic description rewritten to the Intent Router spine
scope. Seven new stories (59-2 through 59-8) drive the build with a
deliberate **no-parallel-window** atomic migration in 59-4.

### Architecture (recap from §3 of the spec)

```
player submit
  → IntentRouter.decompose(action, state_summary)        # Haiku via SDK
  → run_dispatch_bank(package)                            # engages engines, mutates snapshot, OTEL per dispatch
  → narrator turn                                         # sees active state + narrator_instructions; narrates consequence
  → narration_apply                                       # engine-owned fields are NO-OP (engines already fired)
  → lie-detector watcher                                  # router-dispatched vs engine-engaged mismatch span
  → broadcast (perception_rewriter applies status-based redaction)
```

### Critical reuse-first findings

Per Architect pragmatic-restraint discipline, every component proposed
already exists in tree or is a trivial rename of an existing component:

| Component | Reuse source |
|-----------|--------------|
| `IntentRouter` | Rename of `sidequest/agents/local_dm.py:LocalDM` (dormant since 2026-04-28). Re-engage the live path; the `LlmClient` injection point already exists |
| `DispatchPackage` producer call | Existing `LocalDM.decompose(...)` returns DispatchPackage already (line 462). Swap the LLM client from ClaudeClient subprocess to SDK-Haiku adapter |
| Dispatch-bank executor | `run_dispatch_bank` at `subsystems/__init__.py:160` — already topo-sorts depends_on, emits per-dispatch OTEL, gracefully handles per-handler errors |
| Confrontation handler | `instantiate_encounter_from_trigger` at `dispatch/encounter_lifecycle.py:217` (existing, alive — same entrypoint `narration_apply` calls today from the sidecar path) |
| Magic handler | `apply_magic_working` at `narration_apply.py:638` (existing, alive — same entrypoint) |
| Scenario clue handler | `consume_clue_footnotes` at `dispatch/scenario_clue_intake.py:34` (existing, alive) |
| Lie-detector watcher | Repurpose `sidequest/agents/confrontation_intent_validator.py` — the tokenizer already exists, the spans already exist (`confrontation_unengaged_turn_span`, `confrontation_intent_mismatch_span` etc.) — just change the trigger from "narrator-sidecar mismatch" to "router-dispatch vs engine-engaged mismatch" |
| Visibility filtering | `redact_dispatch_package` at `prompt_redaction.py:32` (existing) |
| Per-call model routing | `agents/model_routing.py:28` — `CallType.CLASSIFICATION → claude-haiku-4-5` already declared |

**No new infrastructure proposed.** The work is wiring + retirement +
rename, plus an SDK-Haiku adapter that follows the existing
`AsideResolver`/`_ASIDE_MODEL` pattern from `llm_factory.py:88`.

### Critical "no fallbacks, fail loud" discipline (Memory: `feedback_no_fallbacks_hard`)

Per the spec §5 and the project memory rule "NO fallbacks — hard ban":

- `DispatchPackage.degraded: bool` and `degraded_reason` fields are
  **REMOVED** from the protocol in 59-2 (the producer story). These were
  introduced for the 2026-04-23 design's "degraded → narrator-only" path
  that the spec explicitly rejects. Tests that build `DispatchPackage(degraded=True)`
  get updated to assert the new fail-loud path instead.
- IntentRouter failure (timeout, parse error, schema-invalid): emit
  ERROR span, ONE bounded visible retry, surface failure explicitly if
  retry fails. **No silent narrator-only continuation.**
- Confidence below threshold = correct, intended *non-engagement*, NOT a
  fallback. Logged as a normal dispatch outcome.
- No parallel period between router-engagement and sidecar-engagement:
  59-4 retires `begin_confrontation` and the `result.confrontation`
  consumer path in the SAME change. **One mechanism. One source of
  truth.**

### Cross-cutting risks

| Risk | Mitigation |
|------|------------|
| ADR-036 sealed-rounds: router runs per-submitted-action, but engines must observe all-players-submitted before engaging | Router runs per-action (independent of MP coordination); `run_dispatch_bank` is invoked once per round AFTER all submits land. Per-action invocation collects packages; pre-narrator phase merges them. This honors the existing turn pipeline boundary. |
| ADR-104/105 perception firewall: dispatch params may contain canonical referents not visible to all players | `redact_dispatch_package` already exists for this. Each dispatch carries `visibility` tags; the redactor filters before narrator-prompt assembly. Tested in 59-7. |
| Latency budget: extra Haiku call per turn | Haiku 4.5 ~0.3-0.5s typical for ~2-3K input. Acceptable within "Cost Scales with Drama" — confrontation-shaped turns warrant the spend. Quiet-walk turns will dispatch nothing of consequence; the call still happens but engines no-op. Measure in 59-8. |
| `_SDK_TOOL_OWNED_FIELDS` cleanup risks breaking unrelated tool-owned fields | Only the engagement-shaped fields (`confrontation`) move out; sibling fields (`location`, `scene_mood`, `npcs_present`, etc.) remain narrator-emitted. Cleanup scope is one entry, not the dict. |

## Story Decomposition (8 stories, 29 net new pts)

### 59-1 (DONE, retained) — Narrator never calls advance_confrontation in tea_and_murder (5pt, p1, tdd)

**Status:** done — shipped server PRs #378 + #379, merged into develop
2026-05-22. Sprint shard active YAML to be updated `backlog → done`.
**Reframe role:** Phase 0 — the point-fix that proved the problem and
the targeted ACs (intent verb set, tool description criteria, structural
lie-detector) that the broader epic generalizes.
**Open ledger:** AC1's "LLM free tool-choice playtest" leg folds into 59-8.

### 59-2 — IntentRouter producer skeleton (Haiku via SDK), dormant integration (5pt, p1, tdd)

**Scope:** Revive `local_dm.py` as `intent_router.py` (`IntentRouter` class).
Wire an SDK-Haiku `LlmClient` adapter (mirroring the `AsideResolver` pattern
from `llm_factory.py:88`). Emit `DispatchPackage` per (action, state_summary).
Remove `DispatchPackage.degraded` field and `degraded_reason` from the
protocol; update existing tests. **Not yet called from the live pipeline.**

**Acceptance criteria:**

1. `IntentRouter.decompose(action, state_summary) → DispatchPackage` returns
   a schema-valid package on a synthetic input (fixture test).
2. The `DispatchPackage.degraded` field is REMOVED from the protocol; the
   `_degraded_requires_reason` validator is REMOVED. All existing references
   updated. (Reuse-first: existing tests get migrated, not duplicated.)
3. SDK-Haiku adapter shipped — passes through `claude-haiku-4-5-20251001`
   via `CallType.CLASSIFICATION` model routing. (Reuse `_ASIDE_MODEL` pattern.)
4. `local_dm.py` module-level docstring rewritten — removes "DORMANT" header;
   adds "Production live-path producer for the Intent Router engagement spine".
5. Spec `docs/superpowers/specs/2026-04-28-localdm-offline-only-design.md`
   gains a "Reversed 2026-05-DD" header pointing to this story + ADR-113.
6. **ADR-113 written and accepted** (the LocalDM-revival / Intent Router
   ratification). Supersedes ADR-013 on the SDK path; amends ADR-111
   (engagement-criteria target); references ADR-067/073/101.
7. Fixture tests: parsing valid output, parse failure raises (no silent
   degrade), schema-invalid output raises (no silent degrade).
8. **Wiring test placeholder:** assert IntentRouter is importable and
   constructible with the SDK-Haiku adapter; no live caller yet. (Required
   per CLAUDE.md "Every Test Suite Needs a Wiring Test" — the LIVE wiring
   lands in 59-4.)

**Depends on:** none. **Repos:** server.

### 59-3 — Repurpose confrontation_intent_validator as router-vs-engine lie-detector (3pt, p1, tdd)

**Scope:** Change the trigger of `confrontation_intent_validator` from
"narrator action_rewrite vs engaged encounter mismatch" to
"router-dispatched subsystem vs engine-engaged-on-snapshot mismatch".
Generalize span family `confrontation_intent.*` to `dispatch_engagement.*`
(or keep names, just broaden semantics — Architect calls keep-names for
lower churn). Watcher runs post-turn; pure function `(package,
post_turn_snapshot) → optional[mismatch_span]`.

**Acceptance criteria:**

1. Router dispatched `confrontation:negotiation` + snapshot has no encounter → mismatch span fires (existing `confrontation_unengaged_turn_span` reused).
2. Router dispatched `confrontation:negotiation` + snapshot has matching encounter → no span (no false positive).
3. Router dispatched nothing + snapshot has no encounter → no span (no false positive on quiet turns).
4. Watcher covers `magic_working` and `scenario_clue` dispatch mismatches (extends beyond confrontation to honor the spine's full vocabulary). NEW spans: `dispatch_engagement.{subsystem}.mismatch`.
5. **Wiring test:** drive a synthetic router-dispatched-not-engaged turn through the real watcher hook (not a unit-test mock); assert span emission.
6. The 59-1-shipped `confrontation_intent_mismatch_reprompt_failed_span` self-report-reprompt path is REMOVED (replaced by the watcher; "one mechanism" rule).

**Depends on:** 59-2 (DispatchPackage producer must exist). **Repos:** server.

### 59-4 — Confrontation cutover: live wiring + retire begin_confrontation (atomic) (8pt, p1, tdd)

**Scope:** The big migration. ALL of these in ONE PR (no parallel window):

- Wire confrontation dispatch handler → `instantiate_encounter_from_trigger`
  in `subsystems/confrontation.py` (new handler file).
- Insert `IntentRouter` into the live turn pipeline pre-narrator (orchestrator
  hookup; `context.dispatch_package` populated for real).
- Call `run_dispatch_bank` to engage engines before narrator runs.
- Retire `begin_confrontation` tool: remove from `tools/__init__.py` registry;
  drop from per-turn tool list. Tool file goes to `agents/tools/_retired/` with
  a one-line README pointing here.
- Remove `confrontation` from `_SDK_TOOL_OWNED_FIELDS` (it's no longer SDK-tool-owned).
- Remove the `result.confrontation` consumer in `narration_apply.py` —
  `narration_apply` no longer creates encounters from sidecar fields.
- Update `output_only_sdk.md` §4 — remove `begin_confrontation` routing rule;
  add a note that confrontation engagement is now router-driven and not the
  narrator's concern.
- **Amend ADR-111** with an implementation note: confrontation engagement
  criteria move from `begin_confrontation`'s description to the router's
  Haiku system prompt; cached at SDK system-block (still Stable zone).

**Acceptance criteria:**

1. Fixture: synthetic player action ("I block his way and call the bluff") → IntentRouter dispatches `confrontation:negotiation` → handler creates StructuredEncounter on snapshot BEFORE narrator runs. Verified via OTEL spans: `intent_router.decompose` → `intent_router.dispatch.confrontation` → `encounter.created` in order, all in one round.
2. Retirement guard: assert `narration_apply.py` no longer instantiates an encounter from `result.confrontation` (search-based test on the function body OR behavioral: set result.confrontation manually, assert no encounter created).
3. `begin_confrontation` tool removed from registry; importing it returns a deprecation re-export pointing at the dispatch handler (clean break, not a runtime shim).
4. `_SDK_TOOL_OWNED_FIELDS` no longer contains `confrontation`. Sibling fields untouched.
5. **Live wiring test:** drive the full turn pipeline (orchestrator → router → bank → narrator) end-to-end through a fixture; assert encounter creation happens BEFORE narrator turn, not after.
6. ADR-111 updated; ADR-113's implementation-pointer updated to this story.
7. Failure path (Memory `feedback_no_fallbacks_hard`): mock router to raise → assert ERROR span emitted, one bounded retry attempted, then explicit failure surfaced (no silent narrator-only continuation).
8. The Story 59-1 ACs that targeted `advance_confrontation` invocation are formally superseded — note appended to 59-1's archived session and to ADR-111's commentary.

**Depends on:** 59-2 (router exists), 59-3 (lie-detector watches the new path). **Repos:** server.

### 59-5 — Magic_working dispatch handler + sidecar engagement retirement (5pt, p2, tdd)

**Scope:** Same shape as 59-4, scaled down (less existing wiring to undo):

- `subsystems/magic_working.py` handler → `apply_magic_working`.
- Add `magic_working` to router's dispatch vocabulary (already in spec §3.2).
- Retire `result.magic_working`-driven engagement in `narration_apply.py:638`.
- Update narrator prompt: magic engagement no longer narrator's signal.

**Acceptance criteria:**

1. Fixture: spellcasting action → router dispatches `magic_working` → handler invokes `apply_magic_working` BEFORE narrator runs.
2. Retirement guard for `result.magic_working` sidecar path.
3. Lie-detector covers magic mismatches (verified — falls under 59-3 AC4).
4. Wiring test through pipeline.
5. ADR-013's drift status updated — references ADR-113 as the SDK successor for magic engagement as well.

**Depends on:** 59-4 (router live). **Repos:** server.

### 59-6 — Scenario_clue dispatch handler (3pt, p2, tdd)

**Scope:** Different from 59-4/59-5 — clue advancement currently fires via
narrator footnotes (`fact_id` carrying), which is a legitimate narrator
emission (the narrator reveals what the players learn — that's a narrator
job, not a router job). Router supplements without retiring:

- `subsystems/scenario_clue.py` handler → `consume_clue_footnotes`.
- Router dispatches `scenario_clue` when the player's action explicitly
  references investigation/discovery intent — engaging the clue graph's
  prerequisite-check path proactively.
- **Footnote-driven path stays** — this is a supplementing dispatch, not
  a retirement.

**Acceptance criteria:**

1. Fixture: investigation action ("I search the desk") → router dispatches `scenario_clue:investigation` → handler advances prerequisite-eligible facts.
2. Footnote-driven path unchanged: narrator emits `fact_id` footnote → narration_apply still calls `consume_clue_footnotes`.
3. No double-engagement: router-dispatched and footnote-driven paths share idempotency keys (DispatchPackage validator enforces uniqueness — already exists).
4. Lie-detector covers scenario_clue mismatches.

**Depends on:** 59-4. **Repos:** server.

### 59-7 — Wire the three LocalDM subsystems (npc_agency, distinctive_detail_hint, reflect_absence) (3pt, p2, tdd)

**Scope:** These subsystem modules already exist in
`sidequest/agents/subsystems/` from the 2026-04 build but have no live
dispatch path. Now that the router is live, wire them through
`run_dispatch_bank`. Pure additive — no engine retirement.

**Acceptance criteria:**

1. Each of npc_agency, distinctive_detail_hint, reflect_absence dispatches engages its handler when the router emits it.
2. Fixture tests for each subsystem (mirroring confrontation/magic).
3. `redact_dispatch_package` honored — visibility-tagged dispatches filtered before narrator sees them in `narrator_instructions`.
4. Lie-detector watches these too (extends 59-3 watcher vocabulary).

**Depends on:** 59-4. **Repos:** server.

### 59-8 — Playtest validation: Glenross social confrontation full session (2pt, p1, trivial)

**Scope:** The owed playtest. Folds 59-1 AC1's "LLM free tool-choice"
leg and validates the broader spine.

**Acceptance criteria:**

1. Run a 30-turn Glenross (tea_and_murder) session against the SDK backend with at least three distinct social confrontation triggers (negotiation, social_duel/scandal, trial or auction if reachable).
2. All three confrontations engage — verified via OTEL `intent_router.dispatch.confrontation` + `encounter.created` spans on the corresponding turns, and via GM-panel inspection.
3. Lie-detector emits zero `dispatch_engagement.*.mismatch` spans (no false positives in real play).
4. Submit a session writeup (~200 words) covering Sebastien's mechanical-visibility perspective: is the GM panel's router-trace usable?
5. Latency budget: per-turn router add < 1.2s (Haiku 4.5 expected ~0.3-0.5s; 1.2s budget includes pipeline overhead).
6. Capture any narrative misses in `sprint/archive/59-8-session.md` for post-mortem.

**Depends on:** 59-4, 59-5, 59-6, 59-7. **Repos:** server (with ui/content read-only). **Workflow:** trivial (playtest report, not TDD code).

## ADR Plan

- **ADR-113 (NEW)** — Intent Router as Mechanical-Engagement Spine.
  Status: accepted on 59-2 PR merge. Supersedes ADR-013 on the SDK path
  (which goes from `drift` to `superseded-by: 113` for SDK; `claude -p`
  path remains under ADR-013 until that backend is retired). Amends
  ADR-111 (engagement criteria migrate from `begin_confrontation`
  description to router prompt). References ADR-067, ADR-073, ADR-101,
  ADR-102, ADR-033, ADR-093, ADR-053, ADR-104, ADR-105.

- **ADR-111 (AMEND)** — Implementation note appended in 59-4: the
  confrontation engagement criteria the rule directed onto
  `begin_confrontation` migrate to the router's Haiku system prompt
  (still cached at SDK system-block level). The rule's "tool description
  is the cached home" intent is preserved; the rule's specific tool
  pointer changes.

- **ADR-013 (UPDATE)** — Drift note updated in 59-2: on the SDK path,
  this ADR is superseded by ADR-113. On the `claude -p` legacy path, the
  three-tier extraction strategy remains live until that backend is
  retired. `superseded-by` field becomes `113` (SDK scope).

- **2026-04-28 LocalDM Offline-Only spec** — Reversal header added in
  59-2 pointing to ADR-113. The spec remains historical evidence; its
  premise (LocalDM as a `claude -p` subprocess is too expensive) is
  retired.

## Sequencing & Dependencies

```
59-2 (router skeleton, ADR-113)
  ↓
59-3 (lie-detector repurpose)
  ↓
59-4 (confrontation cutover — ATOMIC, retires begin_confrontation)
  ↓
59-5 (magic_working) ─┬─→ 59-8 (playtest)
59-6 (scenario_clue) ─┤
59-7 (3 subsystems)  ─┘
```

59-2 must complete before 59-3 (lie-detector needs DispatchPackage producer).
59-3 must complete before 59-4 (live cutover wants the watcher catching mismatches from day one).
59-5/59-6/59-7 can run in parallel after 59-4 (no shared touch surface).
59-8 is the capstone — depends on all engagement-bearing stories.

## Open Questions (for the team)

1. **Confidence threshold default** — spec proposed 0.6. Per-subsystem from day one (auditable per engine) vs single global value? Architect lean: **per-subsystem, default 0.6 each**, tunable in genre pack rules.yaml. Resolve in 59-2.
2. **Retry count on router failure** — spec proposed 1. Acceptable for player UX (single "re-reading your action…" beat)? Lean: **1 retry, then loud surface**. Resolve in 59-2.
3. **State-summary encoding for the router** — reuse the narrator's slimmed snapshot (ADR-110), or a purpose-built compact view? Lean: **reuse slimmed snapshot**, drop additional fields the router can't act on (per-engine relevance filter). Resolve in 59-2.
4. **MP merge semantics** — under ADR-036 sealed rounds, router runs per-player-action; how do dispatches merge before engine engagement? Lean: **collect per-action packages, merge in pre-narrator phase using idempotency keys**, fire `run_dispatch_bank` once per round. Cross-player dispatches in `DispatchPackage.cross_player` field already exist for this. Resolve in 59-2.

## Hand-back to SM

The mechanical work the Scrum Master needs to do, in order:

1. **Update active `sprint/epic-59.yaml`** — epic description → reframed text
   (paragraph 1 of this doc's overview), status `ready`, retain story 59-1
   but flip its status `backlog → done`. Add 59-2 through 59-8 entries.
2. **Use `pf sprint story add`** (not manual YAML edit) for the seven new
   stories. Acceptance criteria for each story are written above — copy
   them verbatim into the YAML. Workflow per story: 59-2/3/4/5/6/7 = tdd,
   59-8 = trivial.
3. **Commit on `main`** with message:
   `chore(sprint): reframe Epic 59 — Intent Router Mechanical-Engagement Spine (Houlihan 2026-05-23)`
4. **Begin 59-2 setup** — that's the foundation story; depends on nothing
   else and writes the ADR. Dev: Major Winchester via `/pf-dev`. TDD workflow.
   Repos: `sidequest-server`.

I do not own story creation in YAML — SM does — but the above stories are
complete enough to drop directly into `pf sprint story add` invocations
without further translation.

---

**Architect:** Major Margaret Houlihan
**Date:** 2026-05-23
**Spec under PR:** #385 (sidequest-server `docs/intent-router-spine` → develop)
