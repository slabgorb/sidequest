---
story_id: "102-4"
jira_key: ""
epic: "102"
workflow: "tdd"
---

# Story 102-4: WN turn model — sealed-letter commitment + initiative-ordered resolution + dead_premise

## Story Details
- **ID:** 102-4
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** server (sidequest-server), ui (sidequest-ui)
- **Branch Strategy:** gitflow (feat/102-4-wn-turn-model created in both repos)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T20:54:05Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T18:41:32Z | 2026-06-10T18:43:06Z | 1m 34s |
| red | 2026-06-10T18:43:06Z | 2026-06-10T19:03:07Z | 20m 1s |
| green | 2026-06-10T19:03:07Z | 2026-06-10T20:24:42Z | 1h 21m |
| review | 2026-06-10T20:24:42Z | 2026-06-10T20:37:49Z | 13m 7s |
| red | 2026-06-10T20:37:49Z | 2026-06-10T20:43:50Z | 6m 1s |
| green | 2026-06-10T20:43:50Z | 2026-06-10T20:48:33Z | 4m 43s |
| review | 2026-06-10T20:48:33Z | 2026-06-10T20:54:05Z | 5m 32s |
| finish | 2026-06-10T20:54:05Z | - | - |

## Sm Assessment

**Story:** 102-4 — WN turn model: sealed-letter commitment + 1d8+DEX initiative-ordered resolution + dead_premise narrator call. 8 pts, p2, tdd, repos server+ui.

**Setup state:** Session file created; `feat/102-4-wn-turn-model` branched from `develop` in both sidequest-server and sidequest-ui. Story context validated at `sprint/context/context-story-102-4.md` (parent epic context: `context-epic-102.md`). No Jira (personal project — jira_key intentionally empty).

**Dependency state:** Predecessors 102-1 (PC-death downed seam), 102-2 (dice-path cast_spell), 102-3 (free-play cast, PR #805), and 102-8 (doc-drift, PR #797) are all merged to server `develop`. Merge gate is clear — no open PRs. 102-5 (narrator tool contract) and 102-6 (psionics) layer on top of this story; coordinate the dead_premise call *shape* with 102-5 but do not build the full contract here.

**Keith directive (2026-06-10, recorded in story context guardrails):** keep SideQuest turn semantics — the WN turn model is implemented inside SideQuest's existing table model (RulesetModule seam per §3 Approach A, ADR-036 submit-and-wait barrier as the MP substrate, ADR-051 turn counters), never as a parallel turn system. Also: Kevin Crawford confirmed our WN SRD use is proper — licensing settled, not a design consideration.

**Routing rationale:** Workflow tdd (phased) → next phase RED, owner TEA. TEA should start from the AC Context in the story context doc (5 ACs: sealed commitment ordering, seeded-RNG initiative order, dead_premise no-auto-resolve, family-wide parametrization across swn/wwn/cwn/awn, and a wiring test from DICE_THROW/commit messages through dispatch). Per context doc assumptions, verify what the P4 initiative-spine design already landed in `game/ruleset/resolution.py` before writing tests that assume greenfield.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Improvement** (non-blocking): The P4 initiative spine left `dead_premise` as prose only ("an actor reduced to 0 HP does not act" stated in the narrator preamble, `handlers/player_action.py::initiative_preamble`) — once 102-4 lands the mechanical walk, that preamble's rule sentence becomes redundant-but-harmless; 102-5 should reshape it when it builds the tool contract. Affects `sidequest/handlers/player_action.py` (preamble wording revisit). *Found by TEA during test design.*
- **Question** (non-blocking): `DiceThrowOutcome.opposed_pending` (resolution_mode: opposed_check) and the new `commitment_pending` are two defer-the-beat mechanisms on the same dataclass. They cannot both fire today (opposed_check cdefs reject WN cast shapes per 102-2, and no WN pack authors opposed_check), but Dev should assert mutual exclusion loudly rather than leave the interaction implicit. Affects `sidequest/server/dispatch/dice.py` (one invariant check). *Found by TEA during test design.*
- **Gap** (non-blocking): epic 102's seam map shows the narrator apply_beat path (`_resolve_wwn_cast_for_beat`) as a second WN resolution entry point — a narrator-driven cast during a sealed WN round is not covered by this story's ACs (the dice/commit path is). 102-5's tool contract owns that path; flagged so it isn't lost. Affects `sidequest/server/narration_apply.py` (102-5 scope). *Found by TEA during test design.*

### Dev (implementation)

- **Gap** (non-blocking): `kill_order_combat` in the new dead-premise suite dispatched the round during fixture setup BEFORE `otel_capture` installed the in-memory exporter (test-signature ordering instantiated the capture too late), making its two span assertions structurally unsatisfiable. Fixed by making the fixture depend on `otel_capture`. Affects `sidequest-server/tests/integration/test_102_4_dead_premise.py` (done in this phase). *Found by Dev during implementation.*
- **Improvement** (non-blocking): `_roll_and_persist_initiative` rolls with an unseeded `random.Random()`, so every production-seam test inherits a coin-flip walk order — `test_wwn_shock_kill_observability` failed intermittently under the new walk until its order was pinned. Four legacy WN integration files now pin initiative post-seat (shock_kill, reprisal_wn_lethality_e2e, dice_path_spell_cast_102_2, wwn_heavy_metal_combat); consider a seeded rng at the seam for ADR-128 resume-safe randomness. Affects `sidequest/server/dispatch/encounter_lifecycle.py` (seeded-rng follow-up). *Found by Dev during implementation.*
- **Improvement** (non-blocking): the inline narrator turn still runs on every SEALED commit (with the new `[ACTION_COMMITTED]` replay text) — one narration per commit in MP. 102-5's narrator-contract reshape should decide whether commit-phase turns batch behind the ADR-036 barrier instead. Affects `sidequest/handlers/dice_throw.py` (102-5 coordination). *Found by Dev during implementation.*

### Reviewer (code review)

- **Improvement** (non-blocking): the round walk's opponent targeting (`_first_live_actor`) does not honor the taunt-absorb bias that `_opposite_side_first_actor` applies (spec §8 — a taunting Fighter absorbs enemy strikes). No WN pack authors taunt today, so no live behavior diverges, but if taunt ever reaches a WN genre the walk will bypass it silently. Affects `sidequest/server/dispatch/wn_round.py` (`_first_live_actor` should apply the same taunt bias or delegate to a shared live-target helper). *Found by Reviewer during code review.*
- **Question** (non-blocking): the narrator runs between commits and can mutate encounter state before the barrier closes — a WITHDRAWN (not downed) pinned target is not a dead premise, so the sealed swing would re-resolve against the next live opponent at apply time (engine-adjacent retargeting). Unreachable today (the commit replay text gives the narrator no beat vocabulary), but 102-5's commit-phase narrator contract must define what the narrator may mutate mid-seal. Affects `sidequest/server/narration_apply.py` / 102-5 scope. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the commit barrier has no absent-player escape — a player who disconnects after peers seal leaves the round waiting indefinitely with only the CONFRONTATION frame showing who's awaited. Consistent with ADR-036 (never rush the table), but ADR-122 presence ref-counting could surface "waiting on a disconnected seat" to the GM/table. Affects `sidequest/server/dispatch/wn_round.py` + lobby presence (future story). *Found by Reviewer during code review.*

## TEA Assessment

**Tests Required:** Yes

**Test Files:**
- `sidequest-server/tests/integration/_wn_round_102_4.py` — shared fixture helpers (real-pack seating via production seam, forced initiative, dispatch wrapper, span helpers)
- `sidequest-server/tests/integration/test_102_4_wn_sealed_round.py` — AC1+AC2: sealed first commit (no resolution/reprisal/leak), committed_actors payload seam, round-phase span order, resolution_order attr, opponent-acts-first behavioral order proof, solo-table immediate fire
- `sidequest-server/tests/integration/test_102_4_dead_premise.py` — AC3: span with actor/target, no corpse damage (exactly one beat_applied), narrator_hints surface, no auto-retarget with a live bystander (The Test), downed-actor-skips-slot
- `sidequest-server/tests/integration/test_102_4_wn_family_smoke.py` — AC4: first-commit seals across all four REAL WN packs (space_opera/swn, heavy_metal/wwn, neon_dystopia/cwn, mutant_wasteland/awn, content-shape discovered not pinned) + native immediate-resolution characterization guard
- `sidequest-server/tests/game/ruleset/test_102_4_wn_turn_model_family.py` — AC4 inheritance locks: isinstance(SwnRulesetModule) binding across the family, native excluded, family-wide deterministic descending roll_initiative (green characterization — pins the mechanism the dispatch gate relies on)
- `sidequest-server/tests/integration/test_102_4_wn_round_wire_wiring.py` — AC5: WebSocket-level DiceThrowMessage → handler → dispatch → round walk (round spans + opponent-first start order at the wire)
- `sidequest-ui/src/__tests__/confrontation-commitment-102-4.test.tsx` — committed/waiting indicators per player-side actor, none for opponents, none on legacy payloads

**Tests Written:** 21 (18 server + 3 UI) covering 5 ACs
**Status:** RED (verified by testing-runner, RUN_ID 102-4-tea-red / 102-4-tea-red-fix: 14 server tests fail on the missing contract — AttributeError commitment_pending, missing {ruleset}.round.* / wwn.dead_premise spans, DiceDispatchError where today's immediate resolution kills the encounter mid-fixture; 1 UI test fails on missing committed_actors rendering. Green-by-design: family inheritance locks, native characterization guards, UI negative gates. Sanity guard: 237 pre-existing tests still pass, no collection breakage.)

**Contract pinned for Dev (Naomi):**
- `DiceThrowOutcome.commitment_pending: bool = False` — mirrors the `opposed_pending` defer idiom; True = sealed (peers uncommitted), False = this commit fired the round. Solo table: first commit fires immediately (False).
- Spans `{slug}.round.committed` → `{slug}.round.initiative` → `{slug}.round.resolved` (start-time ordered); resolved carries `resolution_order` = comma-space-joined token_ids actually walked. Honest slug per binding (awn, not cwn).
- `{slug}.dead_premise` span with `actor` + `target` attributes; NO beat application for the dead-premised action; NO auto-retarget; narrator_hints gains a line naming actor + fallen target.
- "Actor at 0 HP before its slot does not act" is mechanically enforced (no beat_applied).
- `build_confrontation_payload()["committed_actors"]: list[str]` — sealed player-side actor names; UI `ConfrontationData.committed_actors?: string[] | null` renders `data-testid="commitment-{name}"` with /committed/i / /waiting/i for player-side actors only.
- Opponent resolves at its initiative slot (reprisal-rider retired inside WN rounds); native dispatch byte-for-byte unchanged.
- Reuse leads: ADR-129 sealed-commit loop (commit/reveal structure), `opposed_pending` defer path in dispatch/dice.py, ADR-036 barrier as the MP substrate (sealed *resolution*, not hidden submission — peer text stays visible).

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #1 silent exceptions | malformed-commit paths covered by 102-2's DiceDispatchError suite (unchanged surface); dead-premise = typed span, never swallowed — `test_dead_premise_span_fires_with_actor_and_target` | failing (RED) |
| #6 test quality | Phase C self-check: kill-coincidence vacuous green found in `test_first_commit_runs_no_opponent_reprisal` and fixed (rng pin min, span-driven RED); green-at-RED tests are documented characterization locks | done |
| #9 async pitfalls | wire wiring test drives `handle_message` under pytest.mark.asyncio with AsyncMock narrator — a missing await in the round walk surfaces here | failing (RED) |
| No Silent Fallbacks | `test_native_rolls_no_initiative` + family smoke assert absent ordering is truthful None/no-span, never a default | green lock |
| Wiring-test mandate | `test_102_4_wn_round_wire_wiring.py` (wire → dispatch → round walk) | failing (RED) |
| OTEL principle | every new behavior asserted span-first (round phases, dead_premise, resolution_order) | failing (RED) |

**Rules checked:** 6 of 13 lang-review rules applicable to a test-only diff have coverage; the remaining 7 (mutable defaults, paths, resources, deserialization, imports, deps, fix-regressions) apply to Dev's implementation diff and fall to the verify phase.
**Self-check:** 1 vacuous test found and fixed (kill-coincidence pin); 0 assertion-free tests; no `assert True` / `let _`-equivalents.

**Handoff:** To Dev (Naomi Nagata) for GREEN. Start from the contract block above; verify what `opposed_pending` already defers before building a second mechanism (Don't Reinvent), and keep the round walk behind the module seam (isinstance(SwnRulesetModule), no genre branches).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **dead_premise span named `{ruleset}.dead_premise`, not `encounter.dead_premise`**
  - Spec source: 2026-05-27-swn-p4-initiative-spine-design.md §7 vs context-epic-102.md "Architectural invariants"
  - Spec text: P4 design says "emits the `encounter.dead_premise` signal + span"; epic context says "Every story lands `{ruleset}.{surface}` spans" and "the slug is honest"
  - Implementation: Tests pin `wwn.dead_premise` (slug-scoped), parametrized by module slug
  - Rationale: Epic context is higher authority than the design doc; slug-scoped spans are the AWN "lie the lie-detector can't catch" doctrine
  - Severity: minor
  - Forward impact: 102-5's `swn_adjudicate_dead_premise` tool span should follow the same `{ruleset}.` naming
- **AC2 "rolls appear in the player-visible surface" covered by existing spine tests, not re-pinned**
  - Spec source: context-story-102-4.md AC-2
  - Spec text: "order and rolls appear in spans and the player-visible surface"
  - Implementation: New tests pin order in `{ruleset}.round.*` spans + behavioral kill-order; the player-visible initiative list is already pinned by tests/server/test_confrontation_payload_initiative.py (P4 spine, green)
  - Rationale: Don't duplicate a green pin; the spine's payload projection is unchanged by this story
  - Severity: minor
  - Forward impact: none
- **dead_premise narrator surface pinned via `enc.narrator_hints`, not a new typed tool call**
  - Spec source: context-story-102-4.md guardrail "dead_premise is a narrator call, not engine improv" + scope boundary "narrator tool contract reshape is 102-5"
  - Spec text: "the engine surfaces a typed dead-premise event for the narrator to adjudicate"
  - Implementation: Tests pin the typed OTEL span + a narrator_hints line naming actor/fallen target (narrator_hints is the existing encounter_render → narrator-prompt pipe); the full `swn_adjudicate_dead_premise` tool shape is left to 102-5
  - Rationale: Story scope boundary says coordinate the call *shape* with 102-5 but don't build the contract here; narrator_hints is the only existing narrator-call pipe a test can pin without inventing 102-5's API
  - Severity: minor
  - Forward impact: 102-5 replaces the hint line with the real adjudication tool; the span contract carries over
### Dev (implementation)

- **Sealed round gated on a non-empty persisted initiative (legacy immediate path kept, loudly, when absent)**
  - Spec source: context-story-102-4.md AC-4 / Technical Guardrails
  - Spec text: "Shared across the WN family behind the module seam"; "the turn model lives behind the RulesetModule seam"
  - Implementation: `wn_sealed_round = isinstance(ruleset, SwnRulesetModule) and cdef.win_condition == "hp_depletion" and bool(encounter.initiative)`. A WN hp_depletion combat with NO persisted order resolves on the legacy immediate path and logs `dice.wn_round_skipped reason=no_persisted_initiative` (WARNING)
  - Rationale: The walk's order IS the P4 spine's persisted `encounter.initiative`; production always stamps it at instantiation (`_roll_and_persist_initiative` fails loud on unresolvable DEX). The only empty cases are pre-P4 saves and direct-construction test fixtures — failing those loudly would break dozens of green tests/saves on a state that is legal today. Loud log keeps it a visible capability gate, not a silent fallback
  - Severity: minor
  - Forward impact: a pre-P4 resumed save keeps reprisal-era combat until its next encounter instantiation; tests/server direct-construction fixtures intentionally stay on the legacy path
- **`committed_actors` is additive-conditional on the CONFRONTATION payload (key present only while commits are sealed)**
  - Spec source: TEA contract block (session file) + context-story-102-4.md cross-repo AC
  - Spec text: "`build_confrontation_payload()["committed_actors"]: list[str]` — sealed player-side actor names; UI `committed_actors?: string[] | null`"
  - Implementation: the key is set only when `encounter.wn_commits` is non-empty; native/dial frames and between-round WN frames keep the legacy payload shape, and the UI renders no indicators on key absence (pinned by the UI legacy-payload test)
  - Rationale: matches the optional UI type TEA pinned and keeps native packs byte-for-byte; an always-present key would change every existing CONFRONTATION frame shape for a WN-only surface
  - Severity: minor
  - Forward impact: between rounds (ledger cleared) the overlay shows no commitment chips until the first commit of the next round — the "everyone waiting" zero-commit state renders nothing; revisit if the table wants standing indicators
- **Sealed commits hand the narrator `[ACTION_COMMITTED]` replay text instead of `[BEAT_RESOLVED]`**
  - Spec source: context-story-102-4.md AC-1
  - Spec text: "no resolution output leaks before the barrier closes"
  - Implementation: `_format_commit_replay_action` names the seal, the roll, and who the barrier waits on, with an explicit "do NOT narrate any mechanical outcome yet" directive; the inline narrator turn still runs per commit (ADR-036 visibility — peer action text stays visible)
  - Rationale: the legacy `[BEAT_RESOLVED]` shape would tell the narrator a beat resolved that the engine sealed — engine-sanctioned winging-it; suppressing the narration turn entirely would change handler flow beyond this story's scope (102-5 owns the narrator contract reshape)
  - Severity: minor
  - Forward impact: 102-5's tool contract should formalize the commit-phase narrator input shape

### Reviewer (audit)

- **TEA: dead_premise span named `{ruleset}.dead_premise`, not `encounter.dead_premise`** → ✓ ACCEPTED by Reviewer: epic context outranks the P4 design doc per the spec-authority hierarchy, and the honest-slug doctrine is exactly why the AWN module exists; rule-checker confirmed slug honesty end-to-end (ADD-6).
- **TEA: AC2 player-visible rolls covered by existing spine tests, not re-pinned** → ✓ ACCEPTED by Reviewer: tests/server/test_confrontation_payload_initiative.py is green and the payload projection is untouched by this diff — duplicating a green pin adds maintenance, not safety.
- **TEA: dead_premise narrator surface pinned via narrator_hints, not a new typed tool call** → ✓ ACCEPTED by Reviewer: the story scope boundary explicitly reserves the tool contract for 102-5; narrator_hints is the only existing narrator pipe and the typed OTEL span carries the contract forward.
- **Dev: sealed round gated on a non-empty persisted initiative (legacy path kept, loudly, when absent)** → ✓ ACCEPTED by Reviewer: production always stamps initiative (`_roll_and_persist_initiative` fail-louds on unresolvable DEX), the absence case is logged at WARNING (verified dice.py:646-657), and failing loud instead would brick pre-P4 saves on a state that is legal today. This is a visible capability gate, not a silent fallback — rule-checker concurs (ADD-1).
- **Dev: `committed_actors` additive-conditional on the CONFRONTATION payload** → ✓ ACCEPTED by Reviewer: matches the optional type TEA pinned and keeps native frames byte-for-byte. NOTE: the between-rounds absence ties into the [HIGH] round-2 regression-net finding — the rework's post-round test should pin the key's absence explicitly so this stays a decision, not an accident.
- **Dev: sealed commits hand the narrator `[ACTION_COMMITTED]` replay text** → ✓ ACCEPTED by Reviewer: handing the narrator `[BEAT_RESOLVED]` for a sealed beat would be engine-sanctioned Illusionism; the explicit do-not-narrate-outcome directive is the right interim shape until 102-5 formalizes the commit-phase contract.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**

*sidequest-server (feat/102-4-wn-turn-model, pushed — ed83ad9e):*
- `sidequest/server/dispatch/wn_round.py` (new) — seal_wn_commit / wn_waiting_actors / wn_barrier_closed / run_wn_round: the sealed-commit ledger ops and the initiative-ordered round walk (downed-slot skip, opponent-at-slot via the existing reprisal primitive with `attacker_name`, dead-premise surface, per-slot beat apply + resolution close, ledger clear, `{slug}.round.*` + `{slug}.dead_premise` spans with the honest binding slug)
- `sidequest/server/dispatch/dice.py` — `DiceThrowOutcome.commitment_pending` (mirrors opposed_pending); WN sealed branch gated `isinstance(SwnRulesetModule) and cdef.win_condition == "hp_depletion" and bool(encounter.initiative)` (no order → legacy path + WARNING, never silent); beat application + resolution close extracted to `_apply_committed_player_beat` / `_emit_player_beat_resolution_close` (one beat implementation, two call sites — legacy immediate and the round walk); `_format_commit_replay_action` ([ACTION_COMMITTED] narrator text for sealed commits); round-walk message fan-out; opposed/commitment mutual-exclusion assert (TEA finding)
- `sidequest/game/encounter.py` — `WnSealedCommit` model + `StructuredEncounter.wn_commits` ledger (additive, persists with the encounter)
- `sidequest/server/dispatch/confrontation.py` — `committed_actors` projected onto the CONFRONTATION payload (additive-conditional: key present only while commits are sealed)
- `sidequest/protocol/messages.py` — `ConfrontationPayload.committed_actors` declared (model is extra="forbid"; undeclared key would crash the mid-turn MP emit)
- `sidequest/telemetry/spans/wn_round.py` (new, + `__init__.py` import) — slug-parametrized WN round span helpers, SPAN_ROUTES registered for all four family slugs
- Tests: `test_102_4_dead_premise.py` fixture now depends on `otel_capture` (TEA fixture-ordering bug — setup-time spans were uncapturable); four legacy production-seam WN files pin `enc.initiative` post-seat (shock_kill_observability, reprisal_wn_lethality_e2e, dice_path_spell_cast_102_2, wwn_heavy_metal_combat) because the seam's 1d8+DEX roll is unseeded and the walk order was a coin flip — PC-first reproduces their pre-102-4 strike-then-answer choreography; ruff import-sort autofix on 3 test files (pre-existing)

*sidequest-ui (feat/102-4-wn-turn-model, pushed — 0b64231):*
- `src/components/ConfrontationOverlay.tsx` — `ConfrontationData.committed_actors?: string[] | null`; StatusLine renders `commitment-{name}` Committed/Waiting chips for player-side actors only; legacy payloads render none

**Tests:** 35/35 story tests passing (32 server incl. protocol roundtrips + 3 UI). Full server suite 11432 passed / 5 failed — all 5 verified pre-existing and unrelated (4× corpus word-count audits in tests/scripts/test_audit_namegen_corpora.py, 1× tests/protocol/test_api_contract_aside.py missing-doc guard; both red with my diff stashed). UI suite 2043 passed / 1 failed (lobby-start-ws-open timeout — pre-existing on develop per dev-gotchas sidecar). Order-stability: the four re-pinned legacy files ran 3× serially, 57/57 green. Lint clean both repos (1 pre-existing UI exhaustive-deps warning). Verified by testing-runner RUN_IDs 102-4-dev-green{,-pass1,-pass2,-full-final,-full-final2,-confirm}.

**Branch:** feat/102-4-wn-turn-model (server + ui, both pushed; no PR — SM owns that in finish)

**Notes for verify/review:**
- The opponent reprisal primitive gained an optional `attacker_name` so each seated opponent attacks AS its own slot token in multi-opponent rounds; legacy callers unchanged.
- Native dispatch is byte-for-byte untouched (sealed branch is unreachable: isinstance gate + native ships no initiative); the family smoke + native characterization guards pin this.
- TEA's mutual-exclusion finding addressed with a loud assert before the outcome return.

**Handoff:** To next phase (verify)
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 4 scope flags | confirmed 0, dismissed 4 (verified against the raw diff: the four legacy-test additions are the documented initiative pins + ruff format churn, zero assertion changes), deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — domain self-assessed by Reviewer (see [EDGE] in assessment) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — domain self-assessed by Reviewer (see [SILENT] in assessment) |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 4 (round-2 ledger net [HIGH], double-commit untested [MEDIUM], MP wire proof [MEDIUM], downed-actor no-dead-premise negative [LOW]), dismissed 0, deferred 3 (fixture-internal precondition, auto-retarget narrowness, wire HP assert — LOW polish, noted for TEA's discretion in rework) |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 | confirmed 6 (1 promoted beyond doc: hardcoded source="dice_throw_beat" in the shared close mislabels round-walk resolutions [MEDIUM]; 5 stale/lying docstrings [LOW]), dismissed 0, deferred 0 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — domain self-assessed by Reviewer (see [TYPE] in assessment) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — domain self-assessed by Reviewer (see [SEC] in assessment) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — domain self-assessed by Reviewer (see [SIMPLE] in assessment) |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 3 (PY-3 missing annotations ×3 [LOW]), dismissed 1 (PY-10 star import — the established convention for every span module in spans/__init__.py; consistency with the file's own registry pattern is the governing convention, not a new violation) |

**All received:** Yes (4 enabled returned, 5 disabled per workflow.reviewer_subagents settings)
**Total findings:** 13 confirmed, 5 dismissed (with rationale), 3 deferred

### Rule Compliance

Rule-checker ran the full lang-review checklists (python.md 13 rules + typescript.md 13 rules) plus the project doctrine rules against every new/changed function, class, and field — 26 rules, 87 instances enumerated. Results, cross-checked by me:

- **PY-1 silent exceptions (12 instances):** compliant — no except blocks in wn_round.py; every refusal is a typed `DiceDispatchError`/`ValueError`.
- **PY-2 mutable defaults (14):** compliant.
- **PY-3 type annotations (14):** 3 VIOLATIONS — `run_wn_round(rng)` (wn_round.py:137) unannotated (`random.Random`); `_apply_committed_player_beat(beat, actor)` (dice.py:1010) unannotated (`BeatDef`, `EncounterActor`); `_emit_player_beat_resolution_close(beat)` (dice.py:1419) unannotated. Confirmed [RULE][LOW].
- **PY-4 logging (8+):** compliant — every slot skip logs at the correct level with %s args; the no-initiative legacy gate logs WARNING.
- **PY-6 test quality (24):** compliant — no vacuous asserts, no source-text wiring tests; `span_start_order` missing from `_wn_round_102_4.__all__` noted as informational.
- **PY-10 imports (6):** 1 flagged, DISMISSED — `from .wn_round import *` in spans/__init__.py is the file's universal registry convention.
- **PY-5/7/8/11/12/13, TS-1..TS-13:** compliant (TS: `string[] | null` typing, Array.isArray runtime guard before Set construction, type-only import in the test, no hooks added, no dangerouslySetInnerHTML).
- **No Silent Fallbacks (5):** compliant — unknown beat_id raises; double commit raises; invalid slug raises; no-initiative degradation logs WARNING; extra="forbid" on WnSealedCommit.
- **OTEL principle (7 surfaces):** compliant — round.committed/.initiative/.resolved + dead_premise spans, wn_commit_sealed / wn_round_resolved / wn_slot_skipped_downed watcher events. One attribution defect found by comment-analyzer (source label, [MEDIUM] below).
- **SOUL The Test (2):** compliant — dead premise emits + hints, never retargets; pinned-premise target on the commit makes non-retargeting structural.
- **Epic 102 isinstance/honest-slug invariant (4):** compliant — gate is `isinstance(ruleset, SwnRulesetModule)` (dice.py:628); spans parametrized by `pack.rules.ruleset` with `_require_family_slug` enforcement; the one `pack.rules.ruleset == "wwn"` literal inside `_apply_committed_player_beat` is the pre-existing Killing Blow feature gate moved verbatim from develop:619, not a new genre branch.

### Devil's Advocate

Assume this is broken. A fast-clicking player double-commits: the second DICE_THROW raises `DiceDispatchError` AFTER the dice spans were emitted — loud and stateless, but the UI just sees an error toast on a roll it animated; nothing pins this path, so a regression to silent-overwrite would ship unnoticed (that became a [MEDIUM] finding). A player disconnects after sealing: the barrier waits forever — `wn_waiting_actors` only excuses the withdrawn and the downed, not the absent. ADR-036's submit-and-wait substrate has the same property by design (never rush the table), but nothing surfaces "waiting on a ghost" beyond the CONFRONTATION frame. Round two is the nightmare case: if `wn_commits.clear()` ever regresses, the first commit of every subsequent round instantly closes the barrier and the headline mechanism of this story silently reverts to immediate resolution — and the suite stays green, because every test ends after round one. That is my [HIGH]. The narrator runs between commits and is fully empowered to mutate encounter state (withdraw the pinned target, even resolve the encounter) before the barrier closes; the walk guards `encounter.resolved` and downed targets, but a withdrawn-pinned-target swing would re-resolve against the next opponent at apply time — engine improv distance from The Test, unreachable today (the commit replay text gives the narrator no beat vocabulary) but 102-5 must own it. A resumed pre-P4 save silently fights with reprisal semantics (accepted, logged loudly). Multi-opponent rounds focus-fire the first live PC — mechanically faithful, socially rough if that PC is Alex's. And the persisted `commit.outcome` string round-trips through `RollOutcome()` — a corrupted save crashes the walk loudly mid-round, which is correct doctrine but worth knowing.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [TEST] | No regression net for the round-ledger reset: nothing asserts `wn_commits == []` / `committed_actors` absent after a round fires, and no test runs a SECOND round. A one-line regression (dropping `encounter.wn_commits.clear()`) silently reverts AC1 to immediate resolution for every round after the first — suite stays green. Multi-round combat is the normal case at the table. | `sidequest-server/tests/integration/test_102_4_wn_sealed_round.py` (gap); `sidequest/server/dispatch/wn_round.py:330` (the unpinned clear) | TEA: post-round assertions (ledger empty, payload key absent) + a round-2 proof (next first-commit seals again, commitment_pending True, no second round.resolved) |
| [MEDIUM] [DOC] | Shared resolution close hardcodes `source="dice_throw_beat"` on `encounter.resolved` span + persisted watcher row even when invoked from the round walk — GM panel and ADR-124 forensics misattribute round-walk resolutions. OTEL is the lie detector; its labels must not lie. | `sidequest/server/dispatch/dice.py` `_emit_player_beat_resolution_close` (span + watcher publish); call site `wn_round.py:318` | Add `source` param defaulting to "dice_throw_beat"; pass "wn_round" from the walk; pin with a span-attribute assertion |
| [MEDIUM] [TEST] | Double-commit rejection (`seal_wn_commit` raises) is implemented but unexercised — a fast-click/retry client is a realistic path | `sidequest/server/dispatch/wn_round.py:67-71` | TEA: same-actor second dispatch raises DiceDispatchError; ledger keeps exactly one entry |
| [MEDIUM] [TEST] | MP sealed-commit has no WIRE-level proof — the wire test is solo-only; the seal-then-fire two-player sequence is proven at dispatch level only | `sidequest-server/tests/integration/test_102_4_wn_round_wire_wiring.py` | TEA: two PCs through `handle_message` — first seals (no round.resolved), second fires |
| [LOW] [DOC] | Stale/lying docs after the refactor: module docstring step 3 and `dispatch_dice_throw` summary claim unconditional beat application; "d20 throw above" pointer inside the extracted helper; mid-turn-emit comment claims metrics already landed; `WnRoundResult` field docs | `dice.py:9, 310, 856, 1326`; `wn_round.py:130` | Dev: doc fixes per comment-analyzer suggestions |
| [LOW] [RULE] | PY-3 annotation gaps on boundary helpers | `wn_round.py:137` (`rng: random.Random`); `dice.py:1010` (`beat: BeatDef`, `actor: EncounterActor`); `dice.py:1419` (`beat: BeatDef`) | Dev: annotate |
| [LOW] [TEST] | Downed-actor test should assert NO `wwn.dead_premise` fires — pins "I am down" (§6) as distinct from "my target is down" | `tests/integration/test_102_4_dead_premise.py:146` | TEA: one negative span assert |

**Self-assessed domains (subagents disabled via settings):**
- [EDGE] Walk slot taxonomy enumerated by me: unseated token (WARN+skip), downed (info+watcher+skip), withdrawn (info+skip), opponent-after-resolution (ADR-139 skip), no-live-target (WARN+skip), player-without-commit (WARN+skip), dead premise (span+hint+skip), resolved-before-apply (skip) — every branch loud, evidence wn_round.py:185-290. Solo table proven; empty-initiative proven legacy.
- [SILENT] No swallowed errors in the new code; the one degradation path (WN combat without persisted initiative → legacy resolution) logs WARNING at dice.py:646-657 — visible, accepted as a deviation.
- [TYPE] `WnSealedCommit` is extra="forbid" with typed fields; `outcome` stored as the RollOutcome value string and round-tripped via `RollOutcome(commit.outcome)` — a corrupt save fails loud at the walk, never coerces. `committed_actors: list[str] | None` declared on the extra="forbid" `ConfrontationPayload` (messages.py:833) — the crash-on-undeclared-key trap was caught and closed during green.
- [SEC] No new untrusted input surfaces: beat_id/spell_id validation precedes any mutation (unchanged); `committed_actors` exposes only seated player names — consistent with ADR-036's 2026-05-03 visibility amendment (sealed resolution, not hidden submission); per-recipient frames route through the same `build_confrontation_payload` (confrontation.py:712), so no perception-firewall divergence.
- [SIMPLE] The extraction REDUCED net complexity (one beat implementation, two call sites; the walk reuses `_resolve_opponent_reprisal` instead of reimplementing). `WnRoundResult.resolution_order` is unconsumed by the caller — kept as the natural result surface, but its doc should say span-only (folded into the [LOW][DOC] finding).

**Data flow traced:** DICE_THROW payload → validation (beat_id/spell_id/stat, pre-mutation) → to-hit resolution → seal_wn_commit (ledger append, watcher event) → barrier check → run_wn_round walks persisted initiative descending → per-slot `_apply_committed_player_beat` (HP via apply_beat_hp_channel) / `_resolve_opponent_reprisal(attacker_name=slot)` → `{slug}.round.resolved` + ledger clear → broadcast (dice pairs in slot order, then CONFRONTATION frame with committed_actors via `emit_confrontation` supplier) → UI `ConfrontationData.committed_actors` → StatusLine chips (player-side only). Safe because every mutation is post-validation, synchronous within one dispatch (no await between seal and walk — no interleave), and every decision emits a span or watcher event.

**Pattern observed:** Good — capability binding via `isinstance(SwnRulesetModule)` with the honest-slug span namespace (dice.py:628, spans/wn_round.py) extends the epic invariant cleanly; the deliberate two-way function-level import between dice.py and wn_round.py is documented at both sites.

**Error handling:** Double commit, unknown beat_id, invalid slug, and malformed cast commits all raise typed errors before/without partial state; the only degradation path logs WARNING (dice.py:646). Verified no bare except in the diff (rule-checker PY-1, 12 instances).

**Why REJECTED:** one [HIGH] — the story's core invariant (the barrier re-arms each round) has zero test coverage beyond round one. The implementation is correct today; the net that keeps it correct is missing. Findings are testable → red rework to TEA, with the [MEDIUM] source-label fix and [LOW] doc/annotation fixes for Dev in the same cycle.

**Handoff:** Back to TEA (red rework) for the regression-net tests; Dev follows for the source param, annotations, and doc fixes.
## TEA Assessment (review-rework round 1)

**Tests Required:** Yes — Reviewer findings, all testable.

**Test changes (sidequest-server, ca436358, pushed):**
- `tests/integration/test_102_4_wn_sealed_round.py` — 4 new tests: `test_round_fire_clears_the_commit_ledger_and_payload_key` + `test_second_round_first_commit_seals_again` ([HIGH] regression net — the barrier re-arms each round, the ledger empties, committed_actors leaves the payload), `test_double_commit_in_one_round_is_a_loud_typed_rejection` ([MEDIUM] characterization lock on the existing guard), `test_round_walk_resolution_close_carries_wn_round_source` ([MEDIUM] **the RED driver** — encounter.resolved from a walk close must carry source="wn_round")
- `tests/integration/test_102_4_wn_round_wire_wiring.py` — `test_mp_wire_first_commit_seals_second_commit_fires_the_round` ([MEDIUM] two PCs via `snapshot.player_seats`, first handle_message seals with zero round/reprisal spans, second fires exactly one round); `_strike_message` gained player_id/request_id params
- `tests/integration/test_102_4_dead_premise.py` — downed-actor test now pins NO `wwn.dead_premise` (§6 "actor down" vs §6.4 "target down" distinction); `kill_order_combat` owns its kill-choreography precondition internally

**Status:** RED (verified by testing-runner, RUN_ID 102-4-tea-red-rework1): 17 passed (green-by-design regression locks — ledger clear, round-2 re-seal, double-commit, MP wire, downed-no-dead-premise all hold against the current implementation) + 1 expected failure: `test_round_walk_resolution_close_carries_wn_round_source` got sources `{'dice_throw_beat', 'hp_depletion'}`, needs `'wn_round'`.

**Contract for Dev (Naomi):** add a `source: str = "dice_throw_beat"` parameter to `_emit_player_beat_resolution_close` (threading it into BOTH the `encounter_resolved_span` call and the op="resolved" watcher publish), and pass `source="wn_round"` from the walk's call site (`wn_round.py:318`). Legacy/opposed callers keep the default — no other behavior change. While in green, also clear the Reviewer's [LOW] items: PY-3 annotations (`rng: random.Random` wn_round.py:137; `beat: BeatDef`, `actor: EncounterActor` dice.py:1010; `beat: BeatDef` dice.py:1419) and the five stale-doc fixes (dice.py:9 step 3, :310 summary, :856 mid-turn-emit comment, :1326 "d20 throw above" pointer; wn_round.py:130 WnRoundResult field docs) per the comment-analyzer's suggested wordings in the Reviewer Assessment.

**Note on the observed `hp_depletion` source:** the solo-kill fixture also surfaces an `encounter.resolved` span with source="hp_depletion" — that one comes from the depletion close inside the walk's opponent/reprisal machinery and is honest; the assertion requires membership of "wn_round", not exclusivity, precisely so that close stays untouched.

### Rule Coverage (rework delta)

| Rule | Test | Status |
|------|------|--------|
| OTEL principle (honest labels) | test_round_walk_resolution_close_carries_wn_round_source | failing (RED driver) |
| #1 silent exceptions / loud rejection | test_double_commit_in_one_round_is_a_loud_typed_rejection | green lock |
| Wiring-test mandate (MP) | test_mp_wire_first_commit_seals_second_commit_fires_the_round | green lock |
| #6 test quality (fixture self-guard) | kill_order_combat internal precondition | green lock |

**Design deviations (rework):** none — the rework tests follow the Reviewer's prescribed shapes verbatim.

**Delivery findings (rework):** none beyond those already logged.

**Handoff:** To Dev (Naomi Nagata) for GREEN — one code seam (`source` param) plus the [LOW] annotation/doc fixes; all regression locks must stay green.
## Dev Assessment (review-rework round 1)

**Implementation Complete:** Yes

**Files Changed (sidequest-server, f7f4a9a5, pushed):**
- `sidequest/server/dispatch/dice.py` — `_emit_player_beat_resolution_close` gains `source: str = "dice_throw_beat"`, threaded into BOTH the `encounter_resolved_span` and the persisted op="resolved" watcher row; `beat: BeatDef` / `actor: EncounterActor` annotations on the extracted helpers; module wire-flow step 3 + `dispatch_dice_throw` summary now describe the sealed path truthfully; stale "d20 throw above" pointer and the mid-turn-emit comment fixed (Reviewer [LOW] doc list, comment-analyzer wordings)
- `sidequest/server/dispatch/wn_round.py` — walk's close call passes `source="wn_round"`; `rng: random.Random` annotation (matches the `_resolve_opponent_reprisal` precedent); `WnRoundResult` field docs distinguish caller-consumed `messages` from span-only `resolution_order`

**Tests:** 33/33 story tests GREEN including the rework RED driver (`test_round_walk_resolution_close_carries_wn_round_source`) and all 17 regression locks. Full server suite 11437 passed / 5 failed — the same 5 known pre-existing failures (corpus audits + api-contract doc guard). Lint clean. Verified by testing-runner RUN_ID 102-4-dev-green-rework1.

**Branch:** feat/102-4-wn-turn-model (server f7f4a9a5, ui 0b64231 unchanged this round; both pushed)

**Design deviations (rework):** none — implemented the Reviewer/TEA contract verbatim.

**Delivery findings (rework):** none new.

**Handoff:** To Reviewer for re-review.
## Reviewer Assessment

**Re-review round 1 — Verdict:** APPROVED

**Process note:** the round-1 full review record stands above (Subagent Results 9/9, Rule Compliance, Devil's Advocate). This re-review verified the rework delta (server ca436358 + f7f4a9a5; UI unchanged at 0b64231) against the rejection table, with an independent preflight (full suite 11437 passed / 5 known pre-existing failures, ruff clean, UI 102-4 tests 3/3, zero smells in the delta).

**Rejection-table disposition — every row closed:**

| Round-1 finding | Disposition | Evidence |
|---|---|---|
| [HIGH] [TEST] round-ledger reset unpinned | ✓ CLOSED | `test_round_fire_clears_the_commit_ledger_and_payload_key` (ledger empties + committed_actors leaves the payload) and `test_second_round_first_commit_seals_again` (barrier re-arms; exactly one round-1 resolved span) — both green against the implementation, both would fail on a dropped `wn_commits.clear()` |
| [MEDIUM] [DOC] source="dice_throw_beat" mislabel from the walk | ✓ CLOSED | `_emit_player_beat_resolution_close(source=...)` threaded into BOTH `encounter_resolved_span` AND the persisted op="resolved" watcher row (dice.py:1430-1466); walk passes `source="wn_round"` (wn_round.py close call); pinned RED→GREEN by `test_round_walk_resolution_close_carries_wn_round_source` (verified individually in re-review preflight) |
| [MEDIUM] [TEST] double-commit untested | ✓ CLOSED | `test_double_commit_in_one_round_is_a_loud_typed_rejection` — DiceDispatchError match="already committed", single ledger entry |
| [MEDIUM] [TEST] MP wire proof missing | ✓ CLOSED | `test_mp_wire_first_commit_seals_second_commit_fires_the_round` — two PCs via `snapshot.player_seats` (the production MP seat resolution), first handle_message emits zero round/reprisal spans, second fires exactly one round |
| [LOW] [DOC] stale docs ×5 | ✓ CLOSED | module step 3 + dispatch summary describe the sealed path; "d20 throw that produced ``outcome_tier``"; mid-turn-emit comment covers the sealed frame; WnRoundResult field docs (verified in delta diff) |
| [LOW] [RULE] PY-3 annotations ×3 | ✓ CLOSED | `rng: random.Random` (wn_round.py — matches the `_resolve_opponent_reprisal` precedent), `beat: BeatDef` + `actor: EncounterActor` (dice.py:1022-1026), `beat: BeatDef` (dice.py:1433) |
| [LOW] [TEST] downed-actor negative span assert | ✓ CLOSED | `test_actor_dropped_before_its_slot_does_not_act` now pins NO `wwn.dead_premise` (§6 vs §6.4); `kill_order_combat` owns its kill precondition |

**Dispatch-tag coverage carried from round 1:** [EDGE] [SILENT] [TEST] [DOC] [TYPE] [SEC] [SIMPLE] [RULE] — no new findings in the delta from any lens; the rework introduced no new branches beyond the `source` parameter default, whose legacy callers keep "dice_throw_beat" byte-for-byte (verified: only the wn_round.py call site passes a non-default).

**Data flow traced (delta):** walk close → `source="wn_round"` → `encounter.resolved` span attr + op="resolved" watcher row → WatcherSpanProcessor → GM panel / `_maybe_persist_encounter_row` forensics. Legacy in-dispatch close keeps the default — no consumer pins the old value anywhere in tests (grepped round 1).

**Error handling:** unchanged from round 1 (verified compliant); the new tests now exercise the double-commit rejection path.

**Deviation audit (rework):** TEA and Dev both logged "no deviations" for the rework — nothing new to stamp; all six round-1 deviations remain ACCEPTED.

**Delivery findings:** No new upstream findings during re-review (round-1 findings stand).

**Handoff:** To SM (Camina Drummer) for finish-story — PR creation and merge are SM's. UI branch 0b64231 + server branch f7f4a9a5, both pushed, no PRs yet.