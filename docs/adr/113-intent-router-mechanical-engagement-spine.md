---
id: 113
title: "Intent Router — Mechanical-Engagement Spine"
status: accepted
date: 2026-05-23
deciders: ["Keith Avery", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [2, 13, 31, 33, 53, 67, 73, 93, 98, 101, 102, 111]
tags: [agent-system, narrator, narrator-migration, observability]
implementation-status: live
implementation-pointer: "sidequest-server intent_router.py + run_dispatch_bank confidence gate (story 71-16, default 0.6, RulesConfig.dispatch_confidence_thresholds)"
---

# ADR-113: Intent Router — Mechanical-Engagement Spine

## Status

Accepted. Implementation tracked under reframed Epic 59 (Intent Router
Mechanical-Engagement Spine), story 59-2 (foundation) through 59-8
(playtest validation). This ADR ratifies the structural decision to route
player intent into mechanical engines **before** the narrator runs, via a
revived `IntentRouter` (renamed `LocalDM`) emitting a `DispatchPackage`
that the existing `run_dispatch_bank` executor consumes.

Partially supersedes **ADR-013** (Lazy JSON Extraction) — on the
`anthropic_sdk` narrator path only. On the legacy `claude -p` ClaudeClient
path, the three-tier extraction strategy in ADR-013 remains live.

Amends **ADR-111** (Recency-Zone Narrator Guardrails into Tool
Descriptions): the confrontation-engagement criteria that ADR-111 routed
onto the `begin_confrontation` tool description migrate to the
IntentRouter's Haiku system prompt (still cached, at the system-block
level — ADR-111's "tool description is the cached home" intent is
preserved; the rule's specific routing target changes).

Reverses the live-path decision in
`docs/superpowers/specs/completed/2026-04-28-localdm-offline-only-design.md`
— LocalDM returns to the live turn path as `IntentRouter`. The offline
corpus runner remains a separate, additive concern (ADR-073 fine-tuning
target).

## Context

### The Illusionism failure mode

SOUL.md's `Illusionism` principle (ADR-002) forbids "convincing prose
with zero mechanical backing." Player-visible regressions in three
consecutive 2026-05 playtests — Pingpong 2026-05-03, Glenross 2026-05-11,
Glenross 2026-05-21 — all share the same fingerprint: the narrator
produces textbook-shaped prose for a mechanical event (confrontation,
discovery, attack) while the engine state behind it remains empty.

The 2026-05-21 Glenross trace was the cleanest reproduction: an explicit
social escalation ("I block his way and call the bluff") produced six
turns of confrontation prose with `confrontation=None` every turn. The
Confrontation Engine (`instantiate_encounter_from_trigger` at
`dispatch/encounter_lifecycle.py`) is wired and alive. It simply
never fires, because nothing reliably tells it to.

### The engines exist (not the broken part)

Verified inventory (2026-05-23):

| Engine | Entry point | Mutates |
|--------|-------------|---------|
| Confrontation (all 6 types) | `instantiate_encounter_from_trigger` (`server/dispatch/encounter_lifecycle.py`) | `snapshot.encounter`, per-actor edge pools |
| Magic / spell working | `apply_magic_working` (`server/narration_apply.py`); `resolve_magic_confrontation` (`dispatch/confrontation.py`) | `snapshot.magic_state.ledger`, `.confrontations` |
| Scenario clue advancement | `consume_clue_footnotes` (`dispatch/scenario_clue_intake.py`) | `snapshot.scenario_state.clue_graph`, `KnownFact`s |
| Three LocalDM-era subsystems (npc_agency, distinctive_detail, reflect_absence) | `sidequest/agents/subsystems/*.py` | various |

### The routing is the broken part

Every engine above fires only when the narrator self-reports a structured
field — `confrontation=<type>`, `magic_working={...}`, footnotes with a
`fact_id`. On the default `anthropic_sdk` backend (ADR-101), the narrator
emits those unreliably or not at all:

- `confrontation` is in `_SDK_TOOL_OWNED_FIELDS` (`orchestrator.py`)
  mapped to the *advance* tools. The SDK assembler **zeros** any narrator
  emission and a fail-loud assertion enforces it. No tool ever *starts* a
  confrontation. Story 59-1's `begin_confrontation` tool fills the
  confrontation slot specifically; magic, scenario_clue, and the LocalDM
  subsystems have no equivalent path on the SDK backend.
- The component built to read **player** intent and route it into
  subsystems — `LocalDM` — was taken off the live path on 2026-04-28
  (commit `74d352c`, PR #96) because, as a second `claude -p` subprocess
  before the narrator, it doubled per-turn subprocess-spawn latency.

The 2026-04-28 shelving was justified at the time. It is no longer:

- The narrator is no longer a subprocess — it's the Anthropic SDK
  (ADR-101), with per-call model routing and prompt caching.
- A Haiku intent pre-pass is now a cheap API call on the same transport,
  not a second subprocess spawn. Per-call model routing already declares
  `CallType.CLASSIFICATION → claude-haiku-4-5-20251001`
  (`agents/model_routing.py`).
- The `LlmClient` abstraction LocalDM was built with means the eventual
  ADR-073 local fine-tuned router is a later dependency injection, not a
  rewrite.

### The half-built consumer plumbing

The 2026-04-23 LocalDM Group A/B work shipped substantial receiving
infrastructure that has been dormant since 2026-04-28:

| Component | Location | State |
|-----------|----------|-------|
| `DispatchPackage` protocol (per_player, cross_player, dispatch, narrator_directives, lethality_verdicts) | `protocol/dispatch.py` | **Merged, alive, unused on live path** |
| `run_dispatch_bank` topo-sort executor | `agents/subsystems/__init__.py` | **Merged, alive, never called** |
| `_topo_sort` for `depends_on` ordering | `agents/subsystems/__init__.py` | **Merged** |
| `lethality_arbiter.py` | `agents/lethality_arbiter.py` | **Merged** |
| `prompt_redaction.redact_dispatch_package` (visibility-tag filtering) | `agents/prompt_redaction.py` | **Merged** |
| Five orchestrator consumer sites (`context.dispatch_package` guards) | `agents/orchestrator.py` lines 1420, 2281, 2296, 2772, 3074 | **All guarded `if … is not None`; permanently `None` on SDK path** |
| Three subsystem handlers | `agents/subsystems/{npc_agency,distinctive_detail,reflect_absence}.py` | **Merged** |

The single missing piece is the **producer**.

### The Zork constraint

SOUL.md's `Zork Problem` forbids reducing player input to a closed verb
set. The fix must **infer** intent without ever gating the open action
space: the player can still attempt anything they can articulate; the
router only decides *which mechanical engines wake alongside* the
narration. A tool selection enum on a per-turn tool list would have
violated this; a confidence-scored advisory dispatch from a Haiku
classifier does not.

### The 59-1 point-fix (relevant prior art)

Story 59-1 (server PRs #378 + #379, merged 2026-05-22) shipped the
`begin_confrontation` SDK tool as a targeted point-fix for the
confrontation slice of this problem. The tool VALIDATES a requested
confrontation type and SIGNALS engagement by populating
`result.confrontation`; `narration_apply` consumes the field and calls
`instantiate_encounter_from_trigger` on the canonical snapshot. The tool
is mechanically correct, its fixture tests pass, and ADR-111 was amended
to recognize the tool description as the routing target.

`begin_confrontation` proves the engagement substrate works. It does not
generalize — magic engagement, scenario_clue advancement, and the three
dormant subsystems have no equivalent. This ADR generalizes.

## Decision

Restore a single authoritative routing spine. A pre-narrator pass reads
each player's submitted action and emits a `DispatchPackage`. The
dispatch-bank executor engages the matching mechanical engine directly
— **before the narrator runs.** The narrator then narrates already-real
state and cannot wing the mechanics. Every decision emits OTEL.

### Pipeline

```
player submit
  → IntentRouter.decompose(action, state_summary)        # Haiku via SDK
  → run_dispatch_bank(package)                            # engages engines, mutates snapshot, OTEL per dispatch
  → narrator turn                                         # sees active state + narrator_directives; narrates consequence
  → narration_apply                                       # engine-owned fields are NO-OP (engines already fired)
  → lie-detector watcher                                  # router-dispatched vs engine-engaged mismatch span
  → broadcast (perception_rewriter applies status-based redaction)
```

### Components (all reuse-first)

1. **`IntentRouter`** — rename + revive of `local_dm.py:LocalDM`.
   Stateless per turn. Injected `LlmClient` (SDK-Haiku adapter now;
   ADR-073 local model later). Reads `(player action, state summary,
   visibility baseline)` → emits a `DispatchPackage`:
   - `dispatch[]` — each `{ subsystem, params, confidence (0.0–1.0),
     depends_on, idempotency_key, visibility }`.
   - `narrator_instructions[]` — `must_narrate`, `must_not_narrate`,
     `distinctive_detail_for_referent`,
     `canonical_only_do_not_reveal_to_others`.
   - referent resolution + `confidence_global`.
   - **No `degraded` fallback flag semantics.** The existing
     `DispatchPackage.degraded` and `degraded_reason` fields are
     removed in story 59-2 (see §No-fallbacks discipline below).

2. **Dispatch vocabulary** — live engines only. The `subsystem` enum is
   closed to engines that exist:
   - `confrontation` → `instantiate_encounter_from_trigger`
   - `magic_working` → `apply_magic_working`
   - `scenario_clue` → `consume_clue_footnotes`
   - `npc_agency` → existing subsystem handler
   - `distinctive_detail_hint` → existing subsystem handler
   - `reflect_absence` → existing subsystem handler

   Excluded with reasons: **stealth** = effect not intent (see
   §Stealth and perception); **perception** = MP info-redaction only,
   no discovery engine; **gossip** = engine exists but is a dormant
   seam (ADR-053), defer to a separate decision; **trope** = automatic
   per-turn progression, never player-dispatched.

3. **Dispatch-bank executor** — `run_dispatch_bank` at
   `agents/subsystems/__init__.py`. Topo-sorts by `depends_on`,
   executes each dispatch through its handler, engaging engines as a
   side effect that mutates `snapshot`. Per-dispatch OTEL.

4. **Lie-detector watcher** — the existing
   `agents/confrontation_intent_validator.py` tokenizer, repurposed.
   *Post-turn*, compares what the router dispatched against what
   actually engaged on the snapshot; emits a watcher span on mismatch
   (e.g. router dispatched `confrontation:negotiation` but
   `snapshot.encounter is None`). Replaces both the deleted keyword
   scanner (`_CONFRONTATION_TRIGGER_PATTERNS`, removed by `93c7659`)
   and the self-report reprompt
   (`confrontation_intent_mismatch_reprompt_failed_span` flow in 59-1).
   **One mechanism.** Span names generalize:
   `dispatch_engagement.{subsystem}.mismatch`.

### Confidence gate

A mechanical dispatch engages its engine **only at or above a confidence
threshold** (default proposed: 0.6 per subsystem, tunable in genre pack
`rules.yaml`). Below threshold, the dispatch does not fire an engine —
it degrades to a `narrator_instruction` hint ("the player may be edging
toward a negotiation"). This is the SOUL "untaken bait" guard: never
force a confrontation the player did not commit to. A below-threshold
*non-engagement* is the correct, intended decision — not a fallback —
and it is logged with its threshold and score.

### Retirement of self-reported engagement fields

In the same change that inserts the router on the live pipeline (story
59-4 for confrontation, 59-5 for magic_working):

- `_SDK_TOOL_OWNED_FIELDS` (`orchestrator.py`) loses the entries
  for retired engagement fields. Sibling fields (`location`,
  `scene_mood`, `npcs_present`, `action_rewrite`, etc.) remain
  narrator-emitted.
- `narration_apply` no longer creates encounters from
  `result.confrontation`, nor invokes `apply_magic_working` from
  `result.magic_working`. The router is the sole engagement authority
  for those subsystems.
- `begin_confrontation` retires (relocates to `agents/tools/_retired/`
  with a README pointer). The tool is removed from the per-turn tool
  list; the narrator prompt's §4 engagement instructions are reworked
  to note that confrontation engagement is router-driven and not the
  narrator's concern.

`scenario_clue` differs: the footnote-driven engagement path (narrator
emits `fact_id` footnote → `consume_clue_footnotes`) stays alive. The
narrator legitimately announces what the players learn — that is a
narrator job. The router supplements by dispatching `scenario_clue`
when the player's action *itself* names an investigation intent. The
two paths share idempotency keys (DispatchPackage already enforces
uniqueness in its validator).

### No-fallbacks discipline (§5 of the source spec, project memory
`feedback_no_fallbacks_hard`)

The IntentRouter is a source-of-truth component. **It has no silent
fallback.** On failure (Haiku timeout, transport error, unparseable
output, schema-invalid package):

1. Emit an ERROR-level OTEL span (`intent_router.failed`, with reason
   and a raw preview).
2. **One bounded, visible retry** — the player sees an explicit
   "re-reading your action…" beat.
3. If the retry also fails: **surface the failure to the GM panel and
   the player as an explicit error.** The turn does not silently
   proceed as narrator-only.

"The table never blocks" is honored by **loud, recoverable** failure —
never by quiet degradation. The 2026-04-23 LocalDM's
`degraded → empty package → narrator-only` path is **removed**, not
ported. The `DispatchPackage.degraded` and `degraded_reason` fields
are deleted from the protocol in 59-2.

Per-dispatch handler errors are caught per-dispatch (one engine failing
does not abort the others), logged at WARNING with an OTEL span, and
the lie-detector catches any resulting classifier-vs-engaged mismatch.

### Telemetry (OTEL discipline per ADR-031)

Every decision emits a span:

- `intent_router.decompose` — action length, model, `confidence_global`,
  dispatch count, latency, retry count.
- `intent_router.dispatch.{subsystem}` — params, confidence, engaged
  (bool), threshold.
- `intent_router.failed` — ERROR, reason, raw preview.
- `dispatch_engagement.{subsystem}.mismatch` — dispatched vs engaged
  divergence (the lie-detector).

The existing `local_dm_decompose_span` is renamed to
`intent_router.decompose` in 59-2.

### Stealth and perception (explicitly out — with homes)

**Stealth is an *effect*, not an intent.** Concealment becomes a status
(alongside `invisible`, `blinded`, `deafened`), applied via the existing
status path (`apply_status` → `status_changes`). The
`perception_rewriter` at the broadcast layer already redacts peer
narration based on those statuses (ADR-104/105). The narrator narrates
the sneaking; the effect lands as a status; the MP firewall already
hides what it should. The router needs no `stealth` dispatch — no stub,
nothing reinvented.

**Perception** stays as MP info-redaction (ADR-104/105). There is no
discovery engine in the codebase; building one would be separate work.

## Consequences

### Positive

- **Illusionism failure mode closes.** Engines fire from observed
  intent, not from narrator self-reporting. The narrator narrates
  consequence, not cause. The GM-panel lie-detector catches any
  remaining drift.
- **Single producer.** `DispatchPackage` has one construction site
  (`IntentRouter.decompose`); today it has zero on the live path.
  Auditing concentrates.
- **Half the work is already done.** The consumer plumbing
  (`DispatchPackage` protocol, `run_dispatch_bank`,
  `lethality_arbiter`, `redact_dispatch_package`, 5 orchestrator
  consumer sites, 3 subsystem handlers) is already merged. The build
  is wiring + retirement + rename, plus one SDK-Haiku adapter that
  mirrors the existing `AsideResolver` pattern.
- **The dormant subsystems wake.** `npc_agency`,
  `distinctive_detail_hint`, `reflect_absence` get live dispatches
  for the first time since 2026-04.
- **ADR-073's swap point is preserved.** `LlmClient` injection means
  the Haiku-via-SDK adapter becomes a local fine-tuned model later
  without changing the IntentRouter contract.
- **ADR-013's drift on the SDK path resolves.** The three-tier JSON
  extraction is retired for SDK-narrator engagement fields (it
  remains live for the legacy `claude -p` backend until that backend
  is retired).

### Negative

- **One extra Haiku call per turn.** Haiku 4.5 latency is ~0.3-0.5s for
  ~2-3K input. Total per-turn budget add ≤1.2s including pipeline
  overhead (verified in 59-8 playtest). Acceptable within SOUL's "Cost
  Scales with Drama" — confrontation-shaped turns earn the spend;
  quiet-walk turns dispatch nothing of consequence (the call still
  happens but engines no-op).
- **A breaking protocol change in `DispatchPackage`.** Tests that build
  `DispatchPackage(degraded=True, …)` are updated in 59-2. The legacy
  LocalDM code path is the only producer; no external consumers exist.
- **An atomic migration window in 59-4.** The confrontation cutover
  retires `begin_confrontation` in the same PR that lights up the
  router's confrontation dispatch. There is no parallel period. This
  is deliberate: per project memory `feedback_one_mechanism_per_problem`,
  parallel detection systems for the same phenomenon are how SideQuest
  ends up in "we don't know what's actually happening" debugging hell.
  The migration risk is mitigated by 59-3 (lie-detector watching from
  day one) and 59-8 (Glenross playtest validation).
- **A failure path requires explicit player-facing surface.** "The
  table never blocks" still holds (a single bounded retry, then a clear
  error), but it does require UI affordance for the
  `intent_router.failed` state. Story 59-2 specifies the GM-panel
  pathway; UI implementation may need a follow-up ticket if existing
  error-surface components do not cover.

### Neutral / explicit non-goals

- **No new engines** (stealth-as-engine, perception-as-discovery). The
  vocabulary is closed to engines that exist.
- **No narrator replacement.** ADR-067's unified narrator stands. The
  router is a pre-narrator layer, not a competing one.
- **No per-genre intent taxonomies.** The router operates on a single
  vocabulary across all genres; genre-specific confrontation types
  remain in `ConfrontationDef`s the confrontation handler consults.
- **No router UI.** The GM panel's OTEL spans are the visible
  surface; no player-facing IntentRouter interface.

## Alternatives Considered

### A. Add per-engine SDK tools (the `begin_confrontation` pattern, generalized)

Ship `begin_magic_working`, `begin_scenario_clue_investigation`,
`begin_npc_agency_check`, etc. — one tool per engine, narrator decides
to call each via its description.

**Rejected.** This is the slot-fill pattern Story 59-1 used, scaled out.
It does not address the structural problem: the narrator's tool-call
selection is unreliable across many tools competing for the same turn
budget. Tool-description proliferation also dilutes the cache benefit
ADR-111 was designed to capture (each tool's description joins the
cached tools array, so adding six tools costs six descriptions per
session-start cache write). A single Haiku classifier picks the right
engine more reliably than a single Opus narrator picks among six tools
weighed against ~20 other tools in its arsenal — and the classifier's
job is auditable in OTEL where the narrator's tool-choice attribution
is opaque.

### B. Keep the narrator-emits-sidecar model; add hard validators

Keep the existing self-report path. Add stricter post-emission
validators that reprompt the narrator on every failure to engage a
shaped turn.

**Rejected.** This is what Story 59-1's `confrontation_intent_validator`
already does for confrontations, and the playtest failure was the
narrator emitting *no* intent at all — which slips through tokenizer-
based validators that require a structured signal to tokenize. Reprompt
loops also amplify the latency problem the router solves cheaply.

### C. Build the router as a deterministic rules engine (no LLM)

Parse player action with hand-tuned regex / keyword rules → dispatch.

**Rejected.** This violates SOUL's `Zork Problem`. A closed verb set is
exactly the failure mode SideQuest exists to escape. Haiku is the open
classifier the rules engine cannot be.

### D. Open a successor epic (Epic 62) instead of reframing Epic 59

Treat the broader scope as new work; close Epic 59 around the shipped
point-fix; ADR-113 references both.

**Rejected.** The active `sprint/epic-59.yaml` shard was never properly
closed (still shows 59-1 as `backlog` despite PR #378 having merged the
work). The reframe scope discovery happened inside Epic 59's lifecycle
(this ADR's source spec is dated 2026-05-22, two days into 59-1's
implementation). Reusing 59 forces a tracker-hygiene cleanup and keeps
the migration sequence and ADR amendments coherent in one place. The
archive shard `sprint/archive/epic-59.yaml` stays as a historical
mid-reframe snapshot; the active shard becomes the canonical reframed
record.

## Implementation Notes

- **Sequencing:** 59-2 (router skeleton + this ADR + protocol cleanup)
  → 59-3 (lie-detector repurpose) → 59-4 (confrontation cutover,
  atomic) → 59-5 (magic_working) ∥ 59-6 (scenario_clue) ∥ 59-7 (3
  subsystems) → 59-8 (Glenross playtest). 59-2 must complete before
  59-3 (DispatchPackage producer must exist). 59-3 must complete
  before 59-4 (lie-detector watches from day one). 59-5/59-6/59-7
  parallel-safe.

- **Open questions for 59-2 architect-pass:** confidence threshold
  defaults (per-subsystem vs single global; lean: per-subsystem 0.6,
  tunable in `rules.yaml`); retry count on router failure (1
  proposed); state-summary encoding (reuse ADR-110 slimmed snapshot
  with per-engine relevance filter); MP merge semantics (collect
  per-action packages, merge in pre-narrator phase via idempotency
  keys, fire `run_dispatch_bank` once per round; cross-player
  dispatches use `DispatchPackage.cross_player` which already exists).

- **Testing strategy (Memory: `feedback_no_content_coupled_tests`):**
  fixture-based only. Synthetic genre packs and synthetic
  `ConfrontationDef`s, never live `genre_packs/*` content. Each
  engine handler has its own fixture; the wiring test drives a
  synthetic action through the real pipeline (orchestrator → router
  → bank → narrator) and asserts engine engagement via OTEL span,
  not source-text grep. The retirement guard asserts
  `narration_apply` no longer instantiates an encounter from
  `result.confrontation`.

- **Test scope and migration debt:** the
  `DispatchPackage.degraded` field removal cascades into existing
  tests under `tests/agents/test_local_dm*.py` and elsewhere. 59-2's
  acceptance criteria mandate migrating those tests to assert the
  fail-loud retry path instead.

- **ADR maintenance:** 59-2 also updates ADR-013's body with a
  "Partially superseded on the SDK path" note and amends ADR-111's
  Implementation Notes section with the engagement-criteria
  migration. The 2026-04-28 LocalDM offline-only spec gets a
  reversal header pointing to this ADR (its premise about
  `claude -p` latency is obsolete; the spec remains historical
  evidence of the shelving rationale).

- **Existing ADR-111 implementation status:** ADR-111 is currently
  `deferred` with pointer `57-4`. The amendment in 59-4 does not
  change its deferred status — that's a separate cache-rebate concern
  (ADR-111 needs the moving 1h cache breakpoint from Story 60-4
  before it realizes savings). The engagement-criteria migration is
  semantic, not cache-driven.

## Amendment 2026-05-28 — confidence-gating is DEFERRED; the spine itself is live

This amendment reconciles the Decision's **§Confidence gate** against the
shipped code. It does **not** revise the original decision — it records
what landed and what did not.

**The router spine is live end-to-end.** The producer the Decision called
for exists and runs on the default `anthropic_sdk` path before the
narrator:

- `IntentRouter` — `sidequest/agents/intent_router.py`.
- `execute_intent_router_pre_narrator_pass` —
  `sidequest/server/intent_router_pass.py`, invoked from
  `sidequest/server/websocket_session_handler.py` (import at
  `:87`) *before* the narrator turn.
- `run_dispatch_bank` — `sidequest/agents/subsystems/__init__.py`
  (topo-sorts and fires the matching handlers, per-dispatch OTEL).
- Lie-detector — `sidequest/agents/dispatch_engagement_watcher.py`
  (emits `dispatch_engagement.{subsystem}.mismatch` post-narration).

So the structural decision (route intent into engines before the narrator,
narrate already-real state, audit via the watcher) is **implemented and
wired**.

**The §Confidence gate is NOT implemented — it is deferred.** The Decision
specified that a mechanical dispatch "engages its engine **only at or above
a confidence threshold** (default proposed: 0.6 per subsystem, tunable in
genre pack `rules.yaml`)." The shipped code does no such thing:

- `run_dispatch_bank` executes **every** emitted dispatch
  unconditionally. The execution loop at
  `sidequest/agents/subsystems/__init__.py` iterates the topo-sorted
  dispatches and calls each handler; there is **no confidence read and no
  threshold comparison** anywhere in the bank. A dispatch is skipped only
  if its subsystem is unregistered or its handler raises.
- There is **no per-dispatch confidence field to gate on.**
  `SubsystemDispatch` (`sidequest/protocol/dispatch.py`) carries
  `subsystem`, `params`, `depends_on`, `idempotency_key`, and
  `visibility` — **no `confidence`.** The only `confidence` floats in the
  protocol are `Referent.confidence` (`dispatch.py`, referent-resolution
  scoring — unrelated to engine gating) and the package-level
  `DispatchPackage.confidence_global` (`dispatch.py`), which nothing
  in the bank consults as a gate. No `rules.yaml` per-subsystem threshold
  key is read.

**Consequence to be explicit about:** today, **every dispatch the router
emits fires its engine.** The "untaken bait" / below-threshold-degrades-to-
narrator-hint behavior described in §Confidence gate does not exist yet.
Per-dispatch confidence scoring and threshold-gating are **DEFERRED, not
implemented.**

Validation of the spine (the 59-8 Glenross playtest gate in §Implementation
Notes) is also still **backlog** — the spine is structurally live but
operationally unvalidated. The confidence-gate work and 59-8 are the two
outstanding items against this ADR; everything else in the Decision shipped.

## References

- ADR-002 — SOUL Principles (Illusionism, Zork Problem, Cost Scales
  with Drama — the principles this ADR enforces)
- ADR-013 — Lazy JSON Extraction (partially superseded by this ADR on
  the SDK path)
- ADR-031 — Game Watcher (the OTEL discipline per-dispatch spans honor)
- ADR-033 — Genre Mechanics Engine (confrontation engine this ADR routes
  into)
- ADR-053 — Scenario System / Clue Graph (the scenario_clue dispatch
  target; gossip excluded as dormant seam, deferred)
- ADR-067 — Unified Narrator Agent (the narrator-as-single-agent
  decision this ADR does not violate; router is pre-narrator)
- ADR-073 — Local Fine-Tuned Model (the future backend swap point;
  IntentRouter's `LlmClient` injection preserves this contract)
- ADR-093 — Confrontation Difficulty Calibration v1 (sibling concern;
  the confrontation engine the dispatch routes into)
- ADR-098 — Stateless Narrator Turns (the bounded-prompt regime this
  ADR honors at the narrator stage)
- ADR-101 — Anthropic SDK as Narrator Backend (the SDK transport that
  makes a Haiku pre-pass cheap)
- ADR-102 — Tool-Use Protocol for Structured Output (the SDK-tool-owned
  partition engagement fields retire from)
- ADR-104 — Perception Filtering at the Tool Layer (MP firewall the
  router defers to)
- ADR-105 — Broadcast-Layer Perception Firewall — Completing ADR-104
  (sibling MP concern; status-based redaction handles stealth-as-effect)
- ADR-111 — Recency-Zone Narrator Guardrails into Tool Descriptions
  (amended by this ADR — engagement-criteria target migration)
- Spec: Intent Router — Mechanical-Engagement Spine
  (`sidequest-server/docs/superpowers/specs/2026-05-22-intent-router-mechanical-engagement-spine-design.md`,
  PR #385) — the implementation-detail source for this ADR
- Spec: 2026-04-23 Local DM Decomposer Design
  (`docs/superpowers/specs/completed/2026-04-23-local-dm-decomposer-design.md`)
  — the original DispatchPackage protocol design whose consumer plumbing
  this ADR re-engages
- Spec: 2026-04-28 LocalDM Offline-Only Design
  (`docs/superpowers/specs/completed/2026-04-28-localdm-offline-only-design.md`)
  — the live-path shelving decision this ADR reverses
- Sprint context: Epic 59 reframe
  (`sprint/context/context-epic-59.md`) — the story decomposition and
  acceptance criteria for the implementation work
