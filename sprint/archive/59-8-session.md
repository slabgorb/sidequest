---
story_id: "59-8"
jira_key: ""
epic: "59"
workflow: "trivial"
---
# Story 59-8: Glenross playtest validation — folds 59-1 AC1 LLM behavior leg

## Story Details
- **ID:** 59-8
- **Jira Key:** (none — Jira not configured)
- **Workflow:** trivial
- **Stack Parent:** 59-7 (done)

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-05-29T16:54:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-29T16:54:00Z | - | - |

## Acceptance Criteria

1. Run 30-turn Glenross (tea_and_murder) session against SDK backend with at least three distinct social confrontation triggers (negotiation, social_duel/scandal, trial or auction if reachable)
2. All three confrontations engage — verified via OTEL intent_router.dispatch.confrontation + encounter.created spans on corresponding turns, and via GM-panel inspection
3. Lie-detector emits zero dispatch_engagement.*.mismatch spans (no false positives in real play)
4. Submit session writeup (~200 words) covering Sebastien-style mechanical-visibility perspective: is GM-panel router-trace usable for a mechanics-first player
5. Latency budget: per-turn router add < 1.2s (Haiku 4.5 expected 0.3-0.5s; budget includes pipeline overhead)
6. Capture any narrative misses or surprises in sprint/archive/59-8-session.md for post-mortem and feed-back into router prompt tuning

## Story Context

This is the playtest story that validates the Intent Router spine (Epic 59) in a real game session. The VERIFICATION ATTEMPTED note (lines 159-160 in epic-59.yaml) documents prior attempts that failed due to:

- Intent Router JSON parsing errors (degradation every turn)
- Dispatch subsystem TypeErrors (missing keyword arguments: snapshot, pack, player_name)

These have been fixed in stories 59-2 through 59-7. The 59-8 mission: run a 30-turn Glenross session where:
- At least 3 distinct social confrontations are triggered (negotiation, social_duel/scandal, trial/auction)
- Each one engages mechanically (OTEL spans: intent_router.dispatch.confrontation + encounter.created)
- No dispatch mismatches fire (59-3's lie-detector clean)
- Router latency stays under budget (~0.3-0.5s per turn)

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

**Source:** Full-stack playtest (oq-1 DRIVER), 2026-05-29, resumed save `2026-05-29-glenross` (Postgres session_id 883). Backend `anthropic_sdk`. Full evidence in `~/Projects/sq-playtest-pingpong.md`; screenshots `100-*`, `101-*` in `.sq-playtest-screenshots/`.

- **[RESOLVED ✅ — was BLOCKING][Gap] social_duel had no resolution path — player soft-locked. FIXED + VERIFIED 2026-05-29.** Root cause (FIXER oq-3, confirmed by code trace): the `concede` beat in `tea_and_murder/rules.yaml` was `kind: push, base: 0` with no `resolution` flag — a `push` only resolves on a Success tier, so a *failed* concede roll never flipped `enc.resolved` and `ENCOUNTER_RESOLVED` never fired. Fix: add `resolution: true` (the declarative always-resolves flag `BeatDef.resolution`, honored on any tier) + regression test `test_glenross_social_duel_concede.py`. **DRIVER verified end-to-end in oq-1:** applied the diff, restarted server, clicked Concede on the stuck duel — concede rolled `tier=Fail` yet `encounter.resolved {outcome: resolution_beat:concede}` fired, `ENCOUNTER_RESOLVED` persisted (seq 42), panel torn down, location advanced to "The Glen Road — Afternoon", Enter unlocked. Screenshot `102-concede-RESOLVED-*`. Caveat: this is per-pack authoring — there is still no *engine-level* universal escape for a confrontation whose dials are unreachable (every pack must author a working concede/withdraw); worth an ADR-116 follow-up. Original finding retained below for the record. **Urgency: was blocking, now resolved.**

  _(original)_ **[Gap] social_duel has no resolution path — player soft-locked.** The one confrontation type that engages in Glenross cannot be completed. `encounter_events` for session 883 = 1 `ENCOUNTER_STARTED` + 5 `ENCOUNTER_BEAT_APPLIED` (all `outcome_tier=Fail, own=0, opp=0`); **no `ENCOUNTER_RESOLVED`/`ENDED` ever fires.** Three compounding failures: (1) player strikes can't land (DC 16 vs applied +1 ≈ nat-15 needed, 5/5 Fail); (2) opponent dial frozen — `encounter.empty_actor_list` means no Other actor bears momentum; (3) `concede` resolves as a normal Fail beat, and the narrator's `advance_encounter_beat beat_to=5` (internal counter maxed) neither emits a resolution nor tears down the panel. Narration declared the duel closed ("The door closes. The glen opens ahead… He gave nothing.") while the state machine stayed open — the exact narration-vs-mechanics drift the GM panel exists to catch, with narration *ahead* of a stuck engine. **Confirmed server-side:** survives Leave+reload AND a full localStorage/sessionStorage/IndexedDB clear + fresh reconnect (Keith's diagnostic). The ADR-026 client mirror has no `encounter` key, so the panel is server-driven; clearing browser data is not a workaround. **Urgency: blocking.**
- **[BLOCKING][Gap] AC5 latency fails every turn.** `intent_router.decompose latency_ms` measured 4561 / 12195 (with a schema_invalid retry) / 5695 / 5753 / 5281 ms across turns — vs the <1.2s budget (Haiku 4.5 expected 0.3–0.5s). Even clean no-retry calls run ~5s, 4–10× over. Schema-invalid first-attempt retries double it. Single biggest AC risk; root cause TBD (local SDK/Haiku throughput vs code). **Urgency: blocking for AC5 as written.**
- **[Question/Gap] AC3 "zero dispatch_engagement.*.mismatch" is unmeetable in Glenross-as-authored.** `dispatch_engagement.scenario_clue.mismatch` fires on investigative turns because the router engages `scenario_clue` (conf ≥0.6) but Glenross ships **no ADR-053 scenario graph** (`snapshot.scenario_state is None`) → 0 directives → mismatch. This is a TRUE positive (lie-detector working), not a router false-positive. Fix is either (a) author a Glenross scenario, or (b) gate the router off `scenario_clue` when `scenario_state is None`. **Urgency: non-blocking (AC interpretation).**
- **[Improvement][player-facing, Sebastien/Jade lane] Beat modifier display ≠ applied.** Verbal Riposte button reads "Cunning **+3**"; the roll panel shows "CUNNING **+1** · need 16 on d20" and "rolled 11 (10 +1) vs DC 16 — Fail". The advertised beat modifier is not the modifier applied. Mechanics-first players see contradictory math. **Urgency: non-blocking.**
- **[Improvement][a11y, player-facing] Beat buttons.** Accessible name is just "Verbal Riposte (Cunning)" — the beat-kind (push/brace/strike) and the `+N` modifier are absent from the accessible name/aria-label (present only as visual text). Prior note also flags ~1.1:1 (dark-on-dark) contrast on the beat buttons. **Urgency: non-blocking.**
- **[POSITIVE] Router + ADR-116 Other-seating + dice all fire correctly.** Explicit confrontation language flips router confidence high (0.92–0.95) and `intent_router.subsystem subsystem=confrontation decision=engaged` seats Sir Iain as the *adversary* (not a friendly fallback) — refutes the 2026-05-28 "Glenross can't furnish confrontations" claim. social_duel beats roll real d20 dice (ADR-074 confirmed: `source=dice_throw`, d20-vs-DC visible in UI) — resolves the open "do social_duel beats roll dice?" question: **yes.** Plain pointed questions route to `npc_agency`; the router under-triggers confrontations on narrative-style pressure and needs confrontation-shaped intent.

### Mechanical-visibility verdict (AC4 / framing correction)
Per the banked correction (sm-gotchas): the OTEL dashboard / GM-panel / router-trace is **Keith's dev debugging tool**, NOT a Sebastien/Jade feature. As a dev tool it performed well — the lie-detector correctly surfaced the scenario_clue gap and the narration-ahead-of-engine drift. The Sebastien/Jade "mechanical visibility" lane is the **player-facing UI** (beat buttons, dials, dice, ability panel); there the dice/DC surface is a genuine legibility win, but the +3-vs-+1 modifier contradiction and the a11y gaps are real player-facing defects. The AC4 text conflates the two — evaluated separately above.

## Writeup (AC4, ~200 words)

The Intent Router spine works. In a real Glenross session against the SDK backend, confrontation-shaped pressure ("I cross-examine him — a contest of wills") reliably flips the router to high confidence (0.92–0.95) and dispatches `subsystem=confrontation`, and ADR-116 seats Sir Iain Ross as the actual adversary rather than a friendly fallback. Beats roll real d20s against a visible DC. For a mechanics-first player the dice/DC surface is exactly the legibility they want.

But the confrontation cannot END. Concede resolves as just another failed beat; the opponent dial is frozen (`encounter.empty_actor_list` — the Other is narrated but never seated as a metric-bearing actor); and no `ENCOUNTER_RESOLVED` ever fires, even after the narrator's prose closes the scene. The player is soft-locked in a duel the story says is over — and it survives reload *and* a full browser-data wipe, so it's purely server-side. The GM panel (Keith's dev lie-detector, not a player feature) earned its keep here: it caught the narration running ahead of a state machine with no exit.

Two hard AC failures stand: router latency is 4–12s/turn (budget <1.2s), and `scenario_clue` mismatches are unavoidable because Glenross ships no scenario graph. The router is sound; the confrontation engine and content are not yet.

## AC Scorecard (interim, playtest 2026-05-29)

| AC | Status | Note |
|----|--------|------|
| 1 — 30-turn session, 3 distinct confrontations triggered | ⛔ blocked | social_duel engaged + soft-locked at turn ~10; negotiation/trial not yet reached (blocked by soft-lock — pivoted to wrap-up per Keith) |
| 2 — all 3 confrontations engage (OTEL + GM-panel) | 🟡 partial | social_duel ENGAGE proven (router dispatch + `encounter.confrontation_initiated` + Other-seating). 2 of 3 types unproven. |
| 3 — zero `dispatch_engagement.*.mismatch` | ⛔ unmeetable as-authored | `scenario_clue.mismatch` is a TRUE positive (#G6: no Glenross scenario graph), not a router false-positive |
| 4 — ~200-word writeup, mechanical-visibility view | ✅ pending writeup | framing corrected (GM panel = dev tool; player-UI = Sebastien/Jade lane) |
| 5 — per-turn router add < 1.2s | ⛔ fail | 4.5–12.2s measured every turn; ~5s even on clean no-retry calls |
| 6 — capture misses/surprises for post-mortem | ✅ | headline = social_duel soft-lock; see Delivery Findings |

## Next Steps

1. **File the blocking soft-lock as its own sprint bug** (confrontation engine, server-side): social_duel — and likely every confrontation type — has no terminal state transition. Concede must resolve as forfeit→`ENCOUNTER_RESOLVED`; max internal beat-count (5) or narrator-declared close must tear down the encounter; provide a confrontation-abort path on Leave. Root sub-bugs to fix together: (a) `encounter.empty_actor_list` — seat the Other as a metric-bearing actor so the opponent dial can advance (ADR-116 mechanical, not just cosmetic narration); (b) `concede` beat → resolution; (c) terminal-state emit + panel teardown.
2. **Decide AC3 disposition** (Architect/Keith): either author a minimal Glenross ADR-053 scenario graph (#G6) so investigative turns have mechanical backing, or gate the router to not engage `scenario_clue` when `snapshot.scenario_state is None`. Until then AC3's literal "zero mismatches" is unmeetable in Glenross.
3. **Root-cause AC5 latency** (separate spike): is the 4–12s `intent_router.decompose` an env/local-Haiku-throughput issue or a code/pipeline issue? Reduce schema-invalid retries (they double the cost). AC5 may need re-baselining if the 0.3–0.5s Haiku expectation is unrealistic on this hardware.
4. **Player-facing fixes (Sebastien/Jade lane):** reconcile beat modifier display (+3) with applied modifier (+1); add beat-kind + `+N` to button aria-labels; raise beat-button contrast above WCAG minimum.
5. **Re-run the engagement legs** (negotiation + trial/auction/scandal) on a FRESH Glenross session once the soft-lock is fixed, to finish AC1/AC2. Save 883 is preserved as repro evidence for the blocking bug — do not delete it.
6. **Story disposition:** 59-8 cannot pass as written (AC1/2/3/5 blocked by engine + content gaps that are out of this validation story's scope). Recommend: keep 59-8 as the validation record (writeup + this scorecard), spin the soft-lock + latency + AC3 into their own backlog stories. SM finish-flow (no Jira).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No deviations yet.
