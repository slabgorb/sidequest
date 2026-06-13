---
story_id: "106-2"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 106-2: WWN reprisal model — defensive beats must mitigate the per-beat opponent reprisal (ramp lever #2)

## Story Details
- **ID:** 106-2
- **Jira Key:** (none — Jira not enabled)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-13T22:33:02Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-13T21:40:11Z | 2026-06-13T21:41:56Z | 1m 45s |
| red | 2026-06-13T21:41:56Z | 2026-06-13T21:52:27Z | 10m 31s |
| green | 2026-06-13T21:52:27Z | 2026-06-13T22:15:22Z | 22m 55s |
| review | 2026-06-13T22:15:22Z | 2026-06-13T22:33:02Z | 17m 40s |
| finish | 2026-06-13T22:33:02Z | - | - |

## Setup Decision Record

### Branch Strategy
gitflow (feat/106-2-wwn-reprisal-model)

### Repo(s)
- sidequest-server

### Design Context
**DESIGN-BEARING, UNBLOCKED (2026-06-13 ruling):** Adopt the **WWN initiative round (full-defend)** model — a player can declare full defense and avoid the per-beat reprisal. Do NOT keep the beat model as the reprisal authority. Reuse the ~80%-built WWN initiative infra in sidequest-server `wn_round.py`.

**Standing Ruling:** WWN SRD is the authority for any WWN-bound mechanical value — never invent numbers. Recorded in `.pennyfarthing/sidecars/gm-decisions.md`.

**Story Context:** Already exists at `sprint/context/context-story-106-2.md` — reference for technical guardrails and existing infrastructure.

## Sm Assessment

Setup complete and clean. Story 106-2 (WWN reprisal model, ramp lever #2) was the biggest unblocked lever in Epic 106; its DESIGN-BEARING blocker is now resolved by the operator's 2026-06-13 ruling — **adopt the WWN initiative round (full-defend)**, do not retain the beat model as reprisal authority.

- **Workflow:** tdd (phased) → routing to TEA for the RED phase.
- **Repo:** sidequest-server only (per story field). Branch `feat/106-2-wwn-reprisal-model` created.
- **Key guardrail for TEA/Dev:** reuse the ~80%-built WWN initiative infra in `wn_round.py` (Architect's finding) rather than rebuilding; the ADR-033 unconditional per-beat counter-attack is what we're replacing — it ignores Brace/Break Contact and isn't WWN-faithful.
- **Standing ruling in force:** WWN SRD is the mechanical authority — no invented numbers (`.pennyfarthing/sidecars/gm-decisions.md`).
- **Full technical context:** `sprint/context/context-story-106-2.md`.

No open SM-side risks. Ready for RED.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)
**Option ruled:** A — WWN initiative round (full-defend). Tests target the sealed
`run_wn_round` walk as the sole WWN opponent-attack path.

**Test File:**
- `sidequest-server/tests/integration/test_106_2_wwn_defensive_reprisal.py` — 7 tests
  driving the real `dispatch_dice_throw → run_wn_round` seam on the real heavy_metal
  pack (`ruleset: wwn`), whose Blade-work `hp_depletion` combat authors `brace`
  (kind: brace) and `break_contact` (kind: push) beats. Reuses the 102-4 WN
  fixtures (`tests/integration/_wn_round_102_4`) and the 71-21 space_opera SWN
  fixtures (no-regression guard).

**Direct-run result (authoritative — `uv run pytest -n0`, NOT testing-runner):**
`4 failed, 3 passed`. Sibling suites (`test_102_4_wn_sealed_round`,
`test_opponent_reprisal_e2e`) stay green (24 passed). New file ruff-clean.

| AC | Test | State | RED reason (verified) |
|----|------|-------|-----------------------|
| 1  | `test_brace_takes_strictly_less_reprisal_damage_than_strike` | RED | `brace_loss=8 == strike_loss=8` — Brace ignored today |
| 5  | `test_brace_round_resolves_through_the_wwn_initiative_walk` | green-guard | `wwn.round.resolved` fires (walk is the real seam; regression net) |
| 3  | `test_brace_mitigation_surfaces_on_opponent_attack_span` | RED | span lacks `defender_beat`/`defense_mitigation` |
| 3  | `test_undefended_strike_span_reports_zero_mitigation` | green-guard | honesty contrast: strike → mitigation 0 (post-impl lock) |
| 2  | `test_break_contact_prevents_the_reprisal_this_round` | RED | `before=12 after=4` — full 8 dmg despite Break Contact |
| 4  | `test_wwn_combat_without_initiative_fails_loud` | RED | no-initiative WWN silently degrades to legacy reprisal (DID NOT RAISE) |
| 4  | `test_swn_sibling_without_initiative_keeps_legacy_reprisal_no_raise` | green-guard | pins fail-loud as WWN-module-scoped; protects 71-21 SWN path |

**Span contract pinned for Dev (AC3 lie-detector):** extend
`encounter.opponent_attack_resolved` with `defender_beat` (str: target's committed
beat id, "" if none) and `defense_mitigation` (int: magnitude applied to THIS
attack — to-hit penalty or flat damage reduction, WWN-SRD-sourced; 0 when the
committed beat isn't defensive).

**Dev guidance — brace lever (NOT a deviation; spec-faithful):** the brace HP test
encodes brace-as-**damage-reduction** because context-story-106-2 ("Existing
infrastructure to reuse") names the `apply_beat_hp_channel(target_mitigation=...)`
primitive and `BeatDef` documents `brace: mitigates incoming HP damage this round`.
The test pins rng MAX (d20=20 guaranteed hit) so the reduction shows as strict
HP-loss delta. **If you instead source brace as a to-hit/AC penalty** (so the hit
could flip to a miss), the MAX-pin won't exercise it — update that test's rng and
log a Design Deviation. `break_contact` and the span tests are lever-agnostic.

**Self-check:** no vacuous assertions — every test asserts a specific value
(strict-less HP delta, exact span attrs, exact HP equality, raises/no-raise). The
2 green-guards assert real conditions (span presence / HP decrease + no-raise),
not `assert True`.

**Handoff:** To Dev (Agent Smith) for GREEN. Implement Option A: thread the target's
sealed defensive commit into `_resolve_opponent_reprisal` (and/or the `run_wn_round`
opponent slot) so brace mitigates and break_contact/full-defend prevents the attack;
surface the mitigation on the OTEL span; make WWN `hp_depletion` with no persisted
initiative fail loud (WWN-module-scoped, never silent legacy degrade). WWN seam by
`isinstance` (ADR-117), native untouched, SRD-sourced numbers.

## Dev Assessment

**Implementation Complete:** Yes
**Option implemented:** A — WWN initiative round (full-defend), per the 2026-06-13 ruling.

**Files Changed (sidequest-server):**
- `sidequest/server/dispatch/dice.py` — (1) new `_defensive_posture_for_reprisal()`
  reads the reprisal target's sealed beat → `(defender_beat, mitigation, prevents)`,
  bound to beat KIND (brace/push), not pack strings; (2) `_resolve_opponent_reprisal`
  takes `defender_commit`, prevents the attack on a committed Break Contact/full-defend
  (push), applies the brace's flat mitigation in the strike's `target_mitigation`, and
  carries `defender_beat`/`defense_mitigation` on the `encounter.opponent_attack_resolved`
  span + watcher; the HIT directive now reports NET applied damage and names the brace;
  (3) the dispatch gate raises `DiceDispatchError` for a WWN `hp_depletion` fight with no
  persisted initiative (fail-loud, WWN-module-scoped — CWN/AWN/SWN keep legacy).
- `sidequest/server/dispatch/wn_round.py` — the opponent slot passes
  `defender_commit=commits.get(target_name)` into the reprisal.

**Test Fixtures Migrated (consequence of the fail-loud, not new behavior):**
- `tests/server/test_reprisal_wn_downed_seam.py`, `tests/integration/test_dice_throw_spell_cast_wiring_102_2.py`,
  `tests/integration/test_wwn_scene_harness_fixture_proof.py` — seat a deterministic
  initiative order so WWN combat routes through the sealed walk (the production seating
  seam always rolls one; these hand-built fixtures bypassed it).

**Tests:** 106-2 suite **7/7 GREEN**. Full server suite: **12002 passed**, 338 skipped,
1 known flake (`test_102_5_wn_tool_narrator_wiring` — psycopg `PythonFinalizationError`
pg-pool teardown race; **passes `-n0` in isolation**, exercises the `wn_attack` tool path
which this story does not touch — memory `server-heavy-e2e-tests-crash-xdist`). ruff
check clean on changed files; pyright clean on the added code (the 5 dice.py pyright
errors are pre-existing `random`-module-as-`Random` and `pending_resolution_signal`
patterns at untouched call sites).

**Branch:** `feat/106-2-wwn-reprisal-model` (pushed).
**Handoff:** To TEA (verify — simplify + quality-pass), then Reviewer.

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Question** (non-blocking): The fail-loud for missing initiative (AC4) is
  scoped to the WWN module class so it can't regress 71-21's SWN legacy reprisal
  path. Dev must confirm whether CWN (`neon_dystopia`) should share WWN's
  "always-have-initiative-or-fail-loud" stance or keep the SWN legacy fallback —
  the test only pins WWN-raises + SWN-no-raise; CWN is unspecified. Affects
  `sidequest-server/sidequest/server/dispatch/dice.py` (the gate at 635-652).
- **Improvement** (non-blocking): `_resolve_opponent_reprisal` currently takes
  `player_name` but not the player's committed beat; Option A needs the commit
  threaded in. The `run_wn_round` opponent slot (`wn_round.py:283-296`) already
  has `encounter.wn_commits` in scope — the cleanest seam is to look up
  `commits[target_name]` there and pass its beat into the resolver. Affects
  `sidequest-server/sidequest/server/dispatch/{wn_round,dice}.py`.
  *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): heavy_metal's `brace` beat authors `base: 1`, so the
  wired brace mitigation is **1 HP** — mechanically correct and content-tunable, but
  marginal for the survivability ramp. The actual ramp target is
  `caverns_and_claudes/beneath_sunden`; its (and heavy_metal's) `brace` `base` likely
  wants tuning up for the defense to *feel* worth choosing. This is a **content** change
  (different repo, "Crunch in the Genre"), out of this server-only story's scope. Affects
  `sidequest-content/genre_packs/*/rules.yaml` (brace beat `base`/`deltas`).
- **Question** (non-blocking, carried from TEA): CWN (`neon_dystopia`/`road_warrior`)
  and AWN (`mutant_wasteland`) are SWN-family but NOT WwnRulesetModule subclasses, so the
  fail-loud does **not** apply to them — they keep the legacy reprisal (no defensive
  mitigation). If CWN/AWN combat should also honor defensive beats, a follow-up must widen
  the seam to those modules (and seed their fixtures' initiative). Affects
  `sidequest-server/sidequest/server/dispatch/dice.py`.
  *Found by Dev during implementation.*

## Design Deviations

None at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec. (The brace-as-damage-reduction lever choice is
  spec-faithful per context-story-106-2's named `target_mitigation` primitive — see
  TEA Assessment "Dev guidance" — not a deviation.)

### Dev (implementation)
- **Brace mitigation magnitude sourced from the beat's authored value, not a literal WWN-SRD number**
  - Spec source: gm-decisions.md (2026-06-13 standing ruling) + context-story-106-2.md, "Hard guardrails for Dev"
  - Spec text: "Any to-hit penalty, AC swing, save target, or mitigation magnitude comes from the WWN SRD ... not invented and hand-balanced."
  - Implementation: brace HP mitigation = `abs(resolve_tier_deltas(brace, base, outcome).opponent)` — the brace beat's OWN authored magnitude (heavy_metal `base: 1`), the same value it already drains from the opponent's dial. Break Contact (push) prevents the attack outright.
  - Rationale: the WWN SRD is **genuinely silent** on a generic "brace/fight-defensively → reduce damage by N" rule (WWN has no Dodge/total-defense AC mechanic and no opportunity attacks; disengage = prevention, which I implemented). Per the standing ruling's own escape clause ("only escalate to Keith if the SRD is genuinely silent"), and CLAUDE.md "Don't Reinvent — Wire Up What Exists", I wired the in-system authored magnitude rather than invent a number. The value lives in content and is tunable without engine change.
  - Severity: minor
  - Forward impact: the survivability *feel* depends on the content `brace.base` (see Delivery Finding); the engine seam is final. A future ruling could swap the magnitude source without touching this wiring.
- **Migrated 3 existing WWN test fixtures to seed initiative**
  - Spec source: context-story-106-2.md, AC4 + "Hard guardrails for Dev" (fail-loud, no silent legacy fallback)
  - Spec text: "A WWN fight that cannot resolve through the chosen path fails loud (no silent degrade to the unconditional legacy reprisal)."
  - Implementation: added a deterministic `enc.initiative` to `test_reprisal_wn_downed_seam`, `test_dice_throw_spell_cast_wiring_102_2`, and `test_wwn_scene_harness_fixture_proof` (they hand-built WWN hp_depletion encounters without an order).
  - Rationale: the fail-loud is the intended behavior; these fixtures encoded the now-retired silent-legacy path. The production seating seam (`encounter_lifecycle.py:361`) always rolls initiative, so seeding it makes the fixtures reflect production.
  - Severity: minor
  - Forward impact: none — same lethality/cast logic, entered via the walk.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A (7/7 + 42/42 green, 0 lint, 0 smells) |
| 2 | reviewer-security | Yes | clean | 0 | N/A (fail-loud placement, WWN scoping, OTEL honesty, no info leak — all verified) |
| 3 | reviewer-edge-hunter | Yes | findings | 6 | confirmed 5, dismissed 0, deferred 1 |
| 4 | reviewer-silent-failure-hunter | Yes | findings | 4 | confirmed 3, dismissed 1, deferred 0 |
| 5 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (4 spawned + returned; 5 disabled via `workflow.reviewer_subagents`)
**Total findings:** 6 confirmed (2 HIGH + 3 MEDIUM + 1 LOW), 1 dismissed (with rationale), 1 deferred

> Note: edge-hunter + silent-failure-hunter are toggled off in settings but were spawned
> anyway to satisfy the downstream review→finish 4-panel gate (preflight/security/edge/silent).
> They earned their keep — they found both HIGH bugs.

## Reviewer Assessment

**Verdict: APPROVE** — the two HIGH findings the panel surfaced were fixed in-review,
locked with tests, and the full suite re-verified. Remaining items are MEDIUM
(fixed or documented) and LOW (deferred), none blocking.

### Confirmed findings (all addressed in commit c8d5a6c2)

- **[HIGH][EDGE] Dead `except ValueError` + Unknown-outcome crash/wrong-prevent** (`dice.py` `_defensive_posture_for_reprisal`).
  `RollOutcome._missing_` maps any bad wire value to `RollOutcome.Unknown` (it does NOT
  raise), so the original `try/except ValueError` could never fire. An Unknown outcome
  would then crash `resolve_tier_deltas` (brace path) or wrongly return `prevents=True`
  (push path). **Verified live**: `RollOutcome("garbage") → Unknown`. **Fixed**: explicit
  `if outcome is RollOutcome.Unknown` guard + WARNING log; helper now returns `("",0,False)`.
  Test: `test_posture_helper_corrupt_outcome_is_safe_no_crash_no_posture`.
- **[HIGH][EDGE] Fully-absorbed brace told the narrator to "narrate the hit landing"** (`dice.py` HIT directive).
  When `defense_mitigation >= dmg_total`, `applied_damage == 0` but the directive commanded
  a wounding hit — a lie (no HP lost). **Fixed**: a dedicated absorbed-hit directive ("the
  Brace absorbed the full N damage — NO HP lost; narrate the brace turning the blow").
  Test: `test_brace_fully_absorbed_hit_directive_says_block_not_wounding_hit`.
- **[MEDIUM][SILENT] `beat is None` silent default** (`dice.py`). A commit naming an
  unknown beat silently degraded to no-defense with no signal — inconsistent with
  `wn_round.py`'s loud raise on the same drift. **Fixed**: WARNING log (loud, not silent);
  the reprisal still resolves (opponent attacks) rather than crashing combat — a documented,
  intentional asymmetry vs the player-beat-APPLY path which must raise. Test:
  `test_posture_helper_unknown_beat_id_is_loud_no_posture`.
- **[MEDIUM][EDGE] Push `Tie` wrongly prevented the attack** (`dice.py`). `not failed`
  treated a Tie disengage as a successful prevention, but `DEFAULT_DELTAS[push][Tie] == {}`
  (a tied disengage resolves nothing in the dial engine). **Fixed**: prevention fires only
  on Success/CritSuccess. Test: `test_posture_helper_push_prevents_only_on_success_not_tie`.
- **[MEDIUM][EDGE/SILENT] Brace does not mitigate the Shock chip** (`dice.py` shock path).
  Confirmed as an *intentional* asymmetry (Shock is the WWN guaranteed-graze that bypasses
  the to-hit; a successful Break Contact prevents the whole attack including Shock). **Resolved
  by documentation** — added an explicit comment at the shock `apply_beat_hp_channel`.
- **[LOW][EDGE] Multi-PC target selection imprecision** (`wn_round.py`). The opponent attacks
  `_first_live_actor(player)`, not a per-opponent logical target. **Pre-existing** behavior
  (predates 106-2; the reprisal always targeted first-live). My change correctly applies the
  defense of *whoever is actually attacked*. Documented as a known limitation; beneath_sunden's
  solo/few-opponent ramp is unaffected. Deferred (out of 106-2 scope).

### Dismissed
- **[LOW][EDGE] NPC-ally no-commit lacks distinguishing OTEL** (`wn_round.py`). Dismissed as
  non-blocking observability nicety: `defender_commit=None` flows correctly for both the
  exempt-ally and offensive-commit cases; the resulting span carries `defender_beat=""`,
  which already signals "no defense applied." Logged here for a future observability pass.

### Rule Compliance (python lang-review checklist, against the diff)
- **#1 Silent exceptions** — the *only* non-default-path concern (the dead `except ValueError`)
  was a confirmed HIGH and is now FIXED (explicit Unknown guard, no swallow). No bare excepts.
- **#3 Type annotations** — `_defensive_posture_for_reprisal` and the new `defender_commit`
  param are fully annotated. ✓
- **#4 Logging** — every new branch logs via lazy `%s` (`logger.warning`/`logger.info`); the
  fail-loud raises `DiceDispatchError` (surfaced at the WS boundary). ✓
- **#6 Test quality** — all new tests assert specific values (exact tuple equality, strict-less
  HP, exact directive substrings, raises/no-raise). No vacuous assertions. ✓
- **#7 Resource leaks** — span context managers used correctly (`with ...: pass`). ✓
- **#10 Import hygiene** — explicit imports (`BeatKind`, `resolve_tier_deltas`, `WnSealedCommit`),
  no stars, no new cycles. ✓
- **#11 Input validation** — the WWN fail-loud IS boundary validation (missing initiative →
  raise before any mutation; verified by reviewer-security: raise precedes seal/apply). ✓
- #2/#5/#8/#9/#12 — N/A (no mutable defaults, paths, deserialization, async, or deps touched).

### [VERIFIED] notes
- [PRE] reviewer-preflight confirmed the mechanical baseline: 106-2 suite 7/7, regression
  neighborhood 42/42, 0 ruff violations, 0 smells (no debug prints/TODOs/bare-excepts/skips).
- [VERIFIED] Fail-loud raises BEFORE any state mutation — `dice.py` gate executes before the
  `elif wn_sealed_round`/`else` dispatch; WWN-scoped via `isinstance(WwnRulesetModule)`, a
  *sibling* of CWN/AWN (`wwn.py:52 WwnRulesetModule(SwnRulesetModule)`). Confirmed by [SEC] +
  the `test_swn_sibling_..._no_raise` guard. Complies with No Silent Fallbacks.
- [VERIFIED] OTEL attribute honesty — `defender_beat` is `""` (never None → no SDK crash);
  `defense_mitigation` is int; prevention emits `hit=False, defense_prevented=True`. [SEC] confirmed.
- [VERIFIED] SOUL "The Test" — the posture helper only READS the sealed commit; it never
  fabricates a player action. [SEC] confirmed.

### Deviation Audit
- **Dev: brace magnitude from authored value (SRD silent)** → ✓ ACCEPTED by Reviewer: the WWN
  SRD genuinely lacks a generic brace-damage-reduction rule; wiring the in-system authored
  magnitude (content-tunable) rather than inventing a number is the correct reading of the
  standing ruling's "escalate only if SRD is silent" clause and "Don't Reinvent." Sound.
- **Dev: migrated 3 fixtures to seed initiative** → ✓ ACCEPTED by Reviewer: a necessary
  consequence of the intended fail-loud; the production seating seam always rolls initiative,
  so the fixtures now reflect production. Same lethality/cast logic, entered via the walk.
- **TEA: no deviations** → ✓ ACCEPTED.

### Devil's Advocate
Argue this code is broken. The most dangerous surface is the defensive-posture read against
adversarial or corrupt state. Before the review fixes, a single bad `outcome` string — from a
forward-incompatible save, a schema migration, or a replayed/edited commit — would have either
hard-crashed the entire reprisal (brace → `resolve_tier_deltas` ValueError, killing the round
mid-walk and potentially wedging the session) or silently handed a free attack-cancel to a push
beat with garbage data. That is precisely the "every playtest is production tomorrow" trap: the
happy path (always a valid sealed outcome) hides a latent crash on the one save that drifts.
That is now closed and tested, but it is the kind of bug that only shows up on Keith's six-month-old
save. Second angle — the narrator as an unreliable witness: the fully-absorbed brace previously
told the model to "narrate the hit landing" while the engine applied zero damage, exactly the
illusionism the OTEL principle exists to catch (prose claiming a wound the mechanics never dealt).
A career-GM player would notice the dissonance immediately. Fixed. Third — balance abuse: a single
successful Break Contact now prevents *every* seated opponent's attack that round (each opponent
slot reads the same player commit), so in a multi-opponent fight one good disengage roll negates
the whole enemy line. For beneath_sunden's solo/small-group ramp this is acceptable and even
desirable (survivability is the goal), but a future many-opponent set-piece could find it cheap;
flagged as a balance note, not a correctness bug. Fourth — the brace magnitude of 1 HP is so small
that a confused mechanics-first player (Sebastien/Jade) might brace, see 7 instead of 8 damage, and
conclude the system is broken; the OTEL span and the directive's "(a Brace absorbed 1 of 8)" note
mitigate the legibility risk, and the real lever is content tuning (Dev finding). Nothing here is
load-bearing-broken after the fixes; the residue is balance/feel, owned by content.

### Observations summary
2 HIGH (fixed+tested), 3 MEDIUM (2 fixed+tested, 1 documented), 1 LOW (deferred), 1 dismissed,
plus 3 VERIFIED. Re-verification: 106-2 suite 11/11; combat neighborhood 65/65; full suite
12006 passed, 1 known psycopg parallel-teardown flake (`test_102_5`, passes `-n0` isolation,
untouched path). ruff clean, formatted.

**Handoff:** To SM (Morpheus) for finish — merge PR + `pf sprint story finish 106-2`.