---
story_id: "86-3"
jira_key: ""
epic: "86"
workflow: "tdd"
---
# Story 86-3: Plan 3 — Vehicle chase confrontation

## Story Details
- **ID:** 86-3
- **Title:** Plan 3 — Vehicle chase confrontation: CWN Vehicle Chases §2.6.2 pace/pursuit model as the chase encounter type (fleeing Drive check = pace; passengers hinder +1..+3; pursuers Dex/Drive vs pace with situational mods); map road_warrior's existing Opening/Pursuit/Escalation/Crisis/Resolution beats; converge into the Plan 2 two-pool combat when vehicles close. OTEL confrontation.* spans on each chase beat.
- **Points:** 5
- **Jira Key:** (none — SideQuest personal project)
- **Workflow:** tdd
- **Repos:** sidequest-server,sidequest-content
- **Stack Parent:** 86-2 (solo rig two-pool vehicle combat — merged)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T15:12:53Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T14:23:43Z | 2026-06-05T14:23:43Z | ~0m |
| red | 2026-06-05T14:23:43Z | 2026-06-05T14:58:27Z | 34m 44s |
| green | 2026-06-05T14:58:27Z | 2026-06-05T15:07:59Z | 9m 32s |
| review | 2026-06-05T15:07:59Z | 2026-06-05T15:12:53Z | 4m 54s |
| finish | 2026-06-05T15:12:53Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Plan 3 has no §6-style implementation spec — the epic
  design doc (`docs/superpowers/specs/2026-06-04-road-warrior-cwn-rig-combat-design.md`)
  fully specs only Plan 1; Plans 2–5 are three-line scopes in §5 plus the §4.x source
  mechanics. I derived the RED contract from §4.2 (CWN Vehicle Chases §2.6.2) + the
  86-2 precedent (faithful stateless math helper + span-asserting integration test),
  which is how 86-2 itself was built (no per-plan spec). No spec authored; flag only.
- **Improvement** (non-blocking): the existing native-dial `chase` confrontation in
  `road_warrior/rules.yaml:409` (separation/pursuit 0→7, WIS/INT beats) is dead prose
  to be **replaced** by the CWN port, not reconciled (Keith, 2026-06-05). Dev should
  remove/rewrite that confrontation block as part of GREEN, not layer onto it.
  Affects `sidequest-content/genre_packs/road_warrior/rules.yaml` (chase confrontation
  + the `chase_system` prose at ~217). *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (blocking): the CWN chase engine has **no production consumer yet**. The live
  road_warrior chase confrontation still resolves through `resolve_opposed_check`
  (`sidequest/game/opposed_check.py` — the ADR-093 shift-band tier model shared by combat
  and social), NOT through the new `resolve_chase_round` (CWN §2.6.2 pace model). Making
  the chase actually CWN-in-play is a *separate, test-driven* increment that must: (1)
  route movement-category confrontations through `resolve_chase_round` instead of the
  shared shift-band resolver; (2) build the catch→combat encounter-type transition (the
  `converges_to_combat` hand-off into Plan 2); (3) replace the native-dial chase
  confrontation + `chase_system` prose in `road_warrior/rules.yaml` with the CWN model
  (TEA's finding above). I did **not** change content this story — a CWN-shaped
  confrontation YAML with no consuming dispatch would be dead content (worse than none).
  Affects `sidequest/server/dispatch/` (movement resolution branch),
  `sidequest/game/opposed_check.py` call sites, and
  `sidequest-content/genre_packs/road_warrior/rules.yaml`. Recommend filing as the
  immediate next story (or folding into Plan 5 content remap). *Found by Dev during
  implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): `chase_pace` public symbols are not re-exported from
  `sidequest/game/__init__.py`, unlike the 86-2 sibling `vehicle_combat`/`rig_crash`. Minor
  API-surface inconsistency — the module imports directly so there is no functional gap;
  worth aligning when the dispatch increment wires a production consumer. Affects
  `sidequest/game/__init__.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `resolve_pursuit` does not clamp/validate `hinder` or
  `situational_modifier` — only the `resolve_chase_round` seam caps hinder (via
  `hinder_penalty`). A future caller invoking the `resolve_pursuit` primitive directly with
  a raw passenger count >3 would silently bypass the +3 cap. Consider asserting/clamping in
  the primitive or documenting the pre-cap contract more loudly when the dispatch caller
  lands. Affects `sidequest/game/chase_pace.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the integration test asserts `ChaseRoundResult.converges_to_combat`
  but not the `converges_to_combat` *span field*; add a span-field assertion when the
  dispatch increment relies on the GM panel reading convergence. Affects
  `tests/integration/test_chase_confrontation_cwn.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Derived ACs from §4.2 + 86-2 precedent (no per-plan spec)**
  - Spec source: epic design §5 (Plan 3 scope) + §4.2 (CWN §2.6.2 mechanics)
  - Spec text: "CWN pace/pursuit (§4.2) as the chase encounter type; … closes into Plan 2 combat when vehicles converge"
  - Implementation: RED contract pinned as a stateless `chase_pace.py` helper + a span-asserting integration test (the 86-2 shape), since no §6-style Plan-3 spec exists.
  - Rationale: 86-2 was built the same way (faithful SRD math helper + integration), with no per-plan spec; the §4.2 mechanics are unambiguous.
  - Severity: minor
  - Forward impact: Dev owns the internal routing (a `resolve_chase_round` seam + `chase.*` span are proposed, open to refinement per the 86-2 "architecture-agnostic" precedent).
- **Replace, not reconcile, the native-dial chase confrontation**
  - Spec source: epic design §1/§4.4 + Keith directive 2026-06-05
  - Spec text: "faithful SRD port, not a redesign"; existing chase = "prose with no mechanical backing"
  - Implementation: tests assert the CWN pace/pursuit model directly; they do NOT exercise or preserve the existing separation/pursuit two-dial confrontation.
  - Rationale: Keith, 2026-06-05 — "we are not interested in current rules and we are using the CWN." The native chase has no mechanical backing to keep.
  - Severity: minor
  - Forward impact: GREEN must rewrite/remove the `road_warrior/rules.yaml` chase block; the old separation/pursuit dials go away.
- **Dropped a trivial `compute_pace` echo to avoid a vacuous test**
  - Spec source: §4.2 ("the fleeing driver's Drive check total IS the pace")
  - Spec text: pace = fleeing Drive(+Dex) check result
  - Implementation: used `chase_check_total(d20, attribute_modifier, drive_skill)` (sums the components — a real, testable invariant) instead of a `compute_pace(total)->total` echo.
  - Rationale: an identity helper would only admit `assert compute_pace(15)==15` (vacuous, banned by the assessment self-check); the component-sum pins the load-bearing "+Dex" inclusion.
  - Severity: trivial
  - Forward impact: none.

### Dev (implementation)
- **Scoped GREEN to the CWN chase engine; deferred the live dispatch + content replacement**
  - Spec source: story title (headline: "chase encounter type … converge into Plan 2 combat … OTEL confrontation.* spans on each chase beat")
  - Spec text: the chase confrontation is wired and converges into combat
  - Implementation: shipped `chase_pace.py` (CWN §2.6.2 engine) + `chase.pursuit_resolved` span only; the live road_warrior chase still routes through `resolve_opposed_check`, and the rules.yaml chase confrontation is unchanged.
  - Rationale: routing the live chase through `resolve_chase_round` means replacing the shared ADR-093 opposed_check shift-band resolver for the movement category + building the catch→combat encounter transition — a large change with no RED tests; doing it in GREEN would be an untested big-bang rewrite of a calibrated path. Mirrors the 86-2 boundary (seam + direct-drive integration test shipped; full dispatch wiring separate). Content-without-dispatch = dead content.
  - Severity: major
  - Forward impact: the chase is not yet CWN-in-play; a follow-up story (blocking Delivery Finding above) must wire dispatch + transition + content. The engine + telemetry contract it lands is stable.
- **Used `StrEnum` instead of TEA's proposed `(str, Enum)` for `PursuitOutcome`**
  - Spec source: TEA seam contract (TEA Assessment)
  - Spec text: `PursuitOutcome(str, Enum): CAUGHT | EVADED`
  - Implementation: `class PursuitOutcome(StrEnum)` — identity and `.value` semantics the tests rely on are unchanged.

### Reviewer (audit)
- **TEA: Derived ACs from §4.2 + 86-2 precedent (no per-plan spec)** → ✓ ACCEPTED by Reviewer: matches how 86-2 was built (seam + direct-drive integration test, no §6 spec); §4.2 mechanics are unambiguous and faithfully ported.
- **TEA: Replace, not reconcile, the native-dial chase confrontation** → ✓ ACCEPTED by Reviewer: aligns with Keith's 2026-06-05 directive and the faithful-port principle; the native chase has no mechanical backing to preserve.
- **TEA: Dropped a trivial `compute_pace` echo to avoid a vacuous test** → ✓ ACCEPTED by Reviewer: sound — `chase_check_total` pins the load-bearing "+Dex" inclusion (a real invariant) rather than an identity echo.
- **Dev: Scoped GREEN to the CWN chase engine; deferred live dispatch + content (Severity: major)** → ✓ ACCEPTED by Reviewer: **verified against the merged 86-2 sibling** — `vehicle_combat.vehicle_ac`/`resolve_ramming` and `rig_crash.apply_rig_damage` likewise have NO production (non-test) consumers (grep: only `game/__init__.py` re-export + tests). The whole 86-2 combat layer is seam-only pending dispatch wiring; 86-3 shipping the chase engine seam-only is consistent, not a half-wiring regression. Dev was transparent and filed a blocking Delivery Finding for the wiring increment.
- **Dev: Used `StrEnum` instead of `(str, Enum)`** → ✓ ACCEPTED by Reviewer: ruff UP042 flags `(str, Enum)` (only E501 ignored), StrEnum is the modern codebase convention, and identity/`.value` semantics the tests rely on are unchanged.
  - Rationale: ruff UP042 flags `(str, Enum)` (only E501 is ignored); StrEnum is the modern codebase convention (renderer/magic/agents) and Python target is 3.12.
  - Severity: trivial
  - Forward impact: none.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Plan 3 is a faithful CWN §2.6.2 (Vehicle Chases) port — new mechanical
behavior (pace/pursuit resolution + per-beat OTEL + catch→combat convergence) that the
GM panel must be able to audit. Mirrors the 86-2 two-tier shape (stateless math helper +
span-asserting integration test).

**Test Files:**
- `sidequest-server/tests/game/test_chase_pace.py` — stateless CWN §2.6.2 pace/pursuit
  math (faithful port; "caller supplies the d20", like `vehicle_combat.py`). 18 tests:
  chase-check component sum (the "+Dex" inclusion), hinder cap at +3 + negative-reject,
  the eight situational-modifier constants/signs, and `resolve_pursuit` strict-beat →
  CAUGHT → `converges_to_combat` (tie loses), with modifier/hinder aggregation and a
  boundary table.
- `sidequest-server/tests/integration/test_chase_confrontation_cwn.py` — the named
  wiring test. Drives a `resolve_chase_round` seam through the real watcher/TracerProvider
  harness; asserts a typed `chase.pursuit_resolved` span (component="chase") fires **per
  round** carrying the §2.6.2 decision (pace/pursuer_effective/outcome), and that a
  pursuer who beats the pace converges into Plan 2 vehicle combat while one who does not
  stays a chase. 5 tests.

**Tests Written:** 23 tests covering the Plan 3 chase behavior (pace, hinder, situational
mods, pursuit resolution, per-beat telemetry, combat convergence).
**Status:** RED — confirmed CLEAN by testing-runner (RUN_ID `86-3-tea-red`): both files
fail solely on `ModuleNotFoundError: sidequest.game.chase_pace`; no db/env/fixture noise.

### Proposed seam (TEA contract — open to Dev refinement, per 86-2 precedent)

```python
# sidequest/game/chase_pace.py (NEW — faithful CWN §2.6.2)
chase_check_total(*, d20, attribute_modifier, drive_skill) -> int   # Drive, usually +Dex
hinder_penalty(passenger_successes: int) -> int                     # +1 each, cap +3, reject <0
PursuitOutcome(str, Enum): CAUGHT | EVADED
PursuitResult(BaseModel): outcome, pursuer_effective, pace, converges_to_combat
resolve_pursuit(*, pursuer_total, pace, situational_modifier=0, hinder=0) -> PursuitResult
    # caught iff pursuer_effective strictly beats pace; CAUGHT => converges_to_combat
resolve_chase_round(*, fleeing_drive_total, pursuer_total, situational_modifier=0,
                    passenger_hinder_successes=0, fleeing_id, pursuer_id,
                    location=None) -> ChaseRoundResult
    # runs resolve_pursuit, emits chase.pursuit_resolved (component="chase"), reports convergence

# situational-modifier constants (signs are load-bearing):
PURSUER_CANNOT_SEE=-2  PURSUER_FLYING_PURSUED_NOT=+3  PURSUED_FLYING_PURSUER_NOT=-3
SPOTTER_RELAYING=+1  HALF_HEARTED_PURSUIT=-1  ENRAGED_VENGEFUL=+1
TERRAIN_KNOWLEDGE_MIN=-2  TERRAIN_KNOWLEDGE_MAX=+2  MAX_HINDER=3
```

Dev also needs a `chase.pursuit_resolved` SpanRoute (`component="chase"`, state_transition;
fields: pace, pursuer_effective, outcome, converges_to_combat, fleeing_id, pursuer_id,
location) wired into `telemetry/spans/` + its `__init__` re-export (Without-Number wiring
checklist), and to **replace** the native-dial chase confrontation in
`sidequest-content/genre_packs/road_warrior/rules.yaml` with the CWN model (Delivery
Finding above).

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|------|---------|--------|
| #6 test quality — no vacuous assertions | self-check: all 23 assert concrete values/enum identity/bool; no `assert True`/`is_none`-on-always-None/`let _` | passing-as-written |
| No Silent Fallbacks (SOUL/CLAUDE.md) | `test_hinder_rejects_negative_successes` (ValueError, not silent 0) | failing (RED) |
| #3 typed boundaries | proposed seam is fully type-annotated (keyword-only, typed returns) — Dev enforces at GREEN | n/a (contract) |
| Wiring test (every suite needs one) | `test_chase_confrontation_cwn.py` drives the real watcher route, asserts span fired | failing (RED) |

**Rules checked:** 4 of the applicable lang-review/project rules have test coverage or a
contract. Most of the python checklist (exception swallowing, mutable defaults, logging,
path handling) targets Dev implementation hygiene on pure-math helpers and is not
pre-testable by TEA beyond the above.
**Self-check:** 0 vacuous tests found (none written; `compute_pace` echo deliberately
dropped — see deviations).

**Handoff:** To Dev (Winchester) for GREEN — implement `chase_pace.py` + the
`chase.pursuit_resolved` span route, and replace the road_warrior chase confrontation
with the CWN model.

---

## Dev Assessment

**Implementation Complete:** Yes (for the scoped GREEN — the CWN chase *engine* + telemetry)
**Files Changed:**
- `sidequest-server/sidequest/game/chase_pace.py` (NEW) — stateless CWN §2.6.2 pace/pursuit
  math (`chase_check_total`, `hinder_penalty` cap +3 / reject <0, eight situational-modifier
  constants, `resolve_pursuit` strict-beat → CAUGHT → `converges_to_combat`) plus the
  `resolve_chase_round` seam that drives `resolve_pursuit` and emits telemetry. `PursuitOutcome`
  is a `StrEnum` (see deviation).
- `sidequest-server/sidequest/telemetry/spans/chase.py` (NEW) — `chase.pursuit_resolved` routed
  span (`component="chase"`, state_transition; pace / pursuer_effective / outcome /
  converges_to_combat / ids / location) + `emit_chase_pursuit_resolved`.
- `sidequest-server/sidequest/telemetry/spans/__init__.py` — re-export `from .chase import *`.

**Tests:** 388 passing / 0 failing (story files `test_chase_pace.py` 22 + `test_chase_confrontation_cwn.py` 5, full `tests/telemetry/` suite, routing-completeness). GREEN, confirmed by testing-runner (RUN_ID `86-3-dev-green` / `86-3-dev-green-2`). ruff check + format + pyright clean on changed files.
**Branch:** `feat/86-3-vehicle-chase-confrontation` (pushed to origin/sidequest-server).

**Scope honesty (read before review):** this lands the faithful CWN §2.6.2 chase **engine**
and its GM-panel telemetry — fully tested. It does **not** yet route the live road_warrior
chase confrontation through it, build the catch→combat transition, or replace the content
YAML — that is a large, untested integration over the shared opposed_check resolver and is
filed as a **blocking Delivery Finding** for the next increment. The content repo branch is
intentionally empty this story (the seam is server-only; content-without-dispatch would be
dead content).

**Handoff:** To Reviewer (Colonel Potter) for code review.

---

## Subagent Results

Project setting `workflow.reviewer_subagents` enables ONLY `preflight`; the other eight
specialists are disabled and were assessed manually by the Reviewer (small, pure-logic diff).

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; 388 pass / 0 fail; ruff+format+pyright clean | N/A |
| 2 | reviewer-edge-hunter | No | Skipped (disabled) | N/A | Manual: tie/cap/sign boundaries covered |
| 3 | reviewer-silent-failure-hunter | No | Skipped (disabled) | N/A | Manual: hinder_penalty raises on <0, no swallowed errors |
| 4 | reviewer-test-analyzer | No | Skipped (disabled) | N/A | Manual: 1 LOW (span converges field unasserted) |
| 5 | reviewer-comment-analyzer | No | Skipped (disabled) | N/A | Manual: docstrings cite SRD §2.6.2, accurate |
| 6 | reviewer-type-design | No | Skipped (disabled) | N/A | Manual: StrEnum + pydantic extra=forbid, keyword-only typed |
| 7 | reviewer-security | No | Skipped (disabled) | N/A | Manual: N/A — pure math, no untrusted input/secrets |
| 8 | reviewer-simplifier | No | Skipped (disabled) | N/A | Manual: 1 LOW (ChaseRoundResult dup of PursuitResult) |
| 9 | reviewer-rule-checker | No | Skipped (disabled) | N/A | Manual rule-by-rule below |

**All received:** Yes (1 enabled subagent returned; 8 disabled via settings, assessed manually)
**Total findings:** 0 confirmed blocking, 5 LOW/non-blocking (see Delivery Findings), 0 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

The diff is a clean, faithful CWN §2.6.2 (Vehicle Chases) port: a stateless pace/pursuit
engine + one routed GM-panel span. 388 tests pass, ruff/format/pyright clean, 0 smells.
No Critical/High issues. The only findings are LOW and non-blocking.

**Observations (tagged by domain; subagents disabled → manual):**

- `[VERIFIED]` **Faithful §2.6.2 port.** Situational-modifier constants and signs match the SRD
  (`chase_pace.py:28-35`); `resolve_pursuit` uses strict-beat semantics (`effective > pace`,
  `chase_pace.py:90-91`) → "beat the pace = catch, tie/under = escape." Evidence:
  `test_tie_does_not_catch` pins tie→evade; the boundary table guards off-by-one/sign.
- `[VERIFIED]` `[SILENT]` **No Silent Fallbacks.** `hinder_penalty` raises `ValueError` on a
  negative count (`chase_pace.py:54-55`) instead of silently returning 0 — complies with the
  CLAUDE.md No-Silent-Fallbacks rule.
- `[VERIFIED]` `[TEST]` **Real wiring test, not source-grep.** The integration test drives
  `resolve_chase_round` through the actual `WatcherSpanProcessor` + `TracerProvider` route and
  asserts `component="chase"` events (`test_chase_confrontation_cwn.py`); routing-completeness
  passes, proving `SPAN_CHASE_PURSUIT_RESOLVED` is registered (`spans/chase.py:21`). Honors the
  "No Source-Text Wiring Tests" rule.
- `[VERIFIED]` **Seam-only scope is NOT a half-wiring regression.** `resolve_chase_round` has no
  production consumer, but the merged 86-2 sibling (`vehicle_combat`, `rig_crash.apply_rig_damage`)
  is likewise seam-only (grep: only `game/__init__.py` re-export + tests). Consistent with the
  epic's decomposition; dispatch wiring is the flagged next increment.
- `[TYPE]` `[VERIFIED]` **Strict typed boundaries.** `PursuitOutcome(StrEnum)`, pydantic models
  with `extra="forbid"`, fully keyword-only annotated signatures.
- `[DOC]` `[VERIFIED]` Docstrings accurately cite CWN §2.6.2 and the design doc; the dormant-prose
  honesty (engine vs. live-wiring) is stated, not implied.
- `[SEC]` N/A — pure arithmetic + a telemetry emit; no untrusted input, no secrets, no auth surface.
- `[SIMPLE]` `[LOW]` `ChaseRoundResult` (`chase_pace.py:100-111`) restates the four `PursuitResult`
  fields plus ids; could compose `PursuitResult`. Readable as-is; non-blocking.
- `[EDGE]` `[LOW]` `resolve_pursuit` does not clamp `hinder`/`situational_modifier` — only the
  `resolve_chase_round` seam caps hinder. A future direct caller could bypass the +3 cap (Delivery
  Finding). Non-blocking.
- `[RULE]` `[LOW]` `chase_pace` not re-exported from `game/__init__.py`, unlike the 86-2 sibling
  (Delivery Finding). Non-blocking.

### Rule Compliance (python lang-review checklist + CLAUDE.md/SOUL.md)

| # | Rule | Verdict |
|---|------|---------|
| 1 | Silent exception swallowing | ✓ none — no try/except; the one validation path raises loudly |
| 2 | Mutable default arguments | ✓ none — defaults are `0` / `None` / keyword-only |
| 3 | Type annotation gaps at boundaries | ✓ all public funcs keyword-only + return-typed; pyright 0 errors |
| 4 | Logging coverage/correctness | ✓ N/A — no logging in pure-math/span modules (telemetry via Span) |
| 5 | Path handling | ✓ N/A — no path manipulation |
| 6 | Test quality (no vacuous asserts) | ✓ all assert concrete values/enum identity/bool; verified, none vacuous |
| — | No Silent Fallbacks (SOUL/CLAUDE.md) | ✓ `hinder_penalty` raises on `<0` |
| — | No Source-Text Wiring Tests (CLAUDE.md) | ✓ integration test drives the real watcher route, asserts span fired |
| — | OTEL Observability (every subsystem decision emits a span) | ✓ `chase.pursuit_resolved` carries the realized §2.6.2 decision |
| — | No half-wired features (CLAUDE.md) | ✓ accepted — seam-only matches merged 86-2; wiring is flagged next increment |

### Devil's Advocate

Arguing this code is broken. **First**, `resolve_pursuit` is a loaded foot-gun: it accepts a raw
`hinder` int and never caps it, trusting callers to pre-cap via `hinder_penalty`. Today only
`resolve_chase_round` calls it, and it caps correctly — but the moment the dispatch increment (or a
test author) calls the `resolve_pursuit` primitive directly with `hinder=passenger_count`, a crew of
five passengers yields a −5 to the pursuer, silently exceeding the SRD's +3 ceiling and handing the
fleeing player an unearned escape. The primitive's permissiveness will outlive the comment that
warns about it. **Second**, neither `situational_modifier` nor `fleeing_drive_total` is range-checked:
a confused caller passing a negative pace makes every pursuer "beat" it and converge to combat — the
chase becomes an ambush regardless of rolls. For a confrontation engine the GM panel is supposed to
audit, an out-of-range pace would render as a legitimate-looking caught-result with no tripwire.
**Third**, the telemetry has a coverage hole: the integration test asserts `pace`, `pursuer_effective`,
and `outcome` on the span, and `converges_to_combat` only on the returned object — so if a refactor
dropped `converges_to_combat` from the *span* extract, every test would still pass while the GM panel
silently lost the combat-handoff signal. **Fourth**, `converges_to_combat` is emitted as a bool OTEL
attribute; bools are valid but less battle-tested than the ints rig spans use, and no test inspects
that field end-to-end. **Mitigations:** all four are latent risks of the *primitive*, not live bugs —
the single production-bound seam (`resolve_chase_round`) caps hinder and sources the pace from a real
Drive check; the convergence object field IS tested. I recorded the cap-bypass, range-validation, and
span-assertion gaps as non-blocking Delivery Findings to be closed alongside the dispatch-wiring
increment, where a hostile/confused caller actually becomes reachable. None rises to High for a
seam with one disciplined caller and no untrusted input.

**Data flow traced:** caller-supplied `fleeing_drive_total` + `pursuer_total` → `resolve_chase_round`
→ `resolve_pursuit` (effective = pursuer + situational − capped-hinder; caught = strict-beat) →
`emit_chase_pursuit_resolved` (routed `component="chase"` span) → `ChaseRoundResult.converges_to_combat`.
Safe: pure arithmetic, no shared mutable state, no untrusted input.
**Pattern observed:** faithful mirror of the 86-2 `vehicle_combat.py` seam + `rig.py` span routing.
**Error handling:** `hinder_penalty` fails loud on `<0`; pydantic `extra="forbid"` rejects stray fields.

**Handoff:** To SM (Hawkeye) for finish-story.