---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-27: Trope progression cooldown + simultaneous-active cap

## Business Context

**Playtest 3 evidence (Felix, mid-session):** Sebastien — the playgroup's
single mechanical-first player, the human the GM panel exists for —
reported narrative thread confusion directly. The cause was a pile-up:
multiple tropes simultaneously in the `progressing` state, each spitting
beat directives into the narrator's prompt, none of them given prominence.
The narrator could not tell which thread was "now" and which was
"background", so the prose oscillated between threads turn-to-turn rather
than committing to one. From Sebastien's seat this looks like the
narrator improvising — which is exactly the lie-detector failure
CLAUDE.md says we must engineer against.

This story sits at the intersection of four ADRs:

- **ADR-018 (Trope Engine)** — defines the `dormant → active →
  progressing → resolved` lifecycle, `rate_per_turn` / `rate_per_day`
  passive advancement, and threshold-keyed beat fires. Currently in drift
  status (`implementation-status: drift`, pointer 87): the *data model*
  was ported (`sidequest/genre/models/tropes.py:29` `PassiveProgression`,
  `sidequest/game/session.py:253` `TropeState`) but **the tick loop and
  fire predicate were not** — `rate_per_turn` is loaded by the resolver
  (`sidequest/genre/resolve.py:149`) and never read. Confirmed by audit:
  no `progress +=` site exists. The only mutation site for `active_tropes`
  is `WorldMaterializer._apply_trope` at
  `sidequest/game/world_materialization.py:429`, which upserts a status
  literal copied from `history.yaml` chapters — not a tick.
- **ADR-024 (Dual-Track Tension Model)** — `drama_weight` is already a
  contention signal (gambler's ramp + HP stakes); pile-up of progressing
  tropes is essentially an *uncoordinated* drama-weight source. The cap
  + cooldown bring trope progression under the same load discipline.
- **ADR-025 (Pacing Detection)** — `TensionTracker.pacing_hint` already
  emits `escalation_beat` when boring streak crosses threshold. The new
  cooldown is the symmetric brake: after a fire, suppress new activations
  for N turns, the way `escalation_beat` only fires past `escalation_streak`.
- **ADR-014 (Diamonds and Coal)** — `narrative_weight` is the cross-system
  scaling lever. Tropes pile-up is the trope-flavored case of treating
  every signal as diamond. The cap forces a coal/diamond split: the K
  active tropes are diamond (Early zone, full prompt weight), the rest
  are coal (queued, not in prompt at all).

Audience: Sebastien (lie-detector audience, mechanical-first) is the
direct beneficiary because he reads OTEL spans and the GM panel directly.
Keith-as-player is the indirect beneficiary because trope pile-up is one
of the things a career human GM would never do — a real DM tracks one or
two threads at a time and sets the others on shelves.

**Soft dependency on 45-9 (`total_beats_fired` increments).** 45-9 is the
prerequisite for trope-tempo telemetry to be honest: today
`snapshot.total_beats_fired` is frozen at 0 (session.py:380), so any
"average progression" or "fires per turn" statistic computed from it is a
lie. The description calls this out as "telemetry-improves after 45-9
lands" — meaning 45-27 SHOULD ship its OTEL spans regardless, but the GM
panel's tempo-over-time view becomes meaningful only once 45-9 is in.
This is a sequencing note, not a hard block.

## Technical Guardrails

### The shape of this fix

This is a **multi-dimensional tuning + structural** story. The five fix
dimensions in the description are not five alternatives; they are five
independent knobs, all of which land:

1. **Per-tick progression rate** — turn down the existing
   `rate_per_turn` impact (or add a global multiplier), so the floor
   advances slower in the absence of player engagement.
2. **Simultaneous-active cap (2-3)** — a hard ceiling on
   `count(t for t in active_tropes if t.status == "progressing")`. The
   (N+1)th candidate is queued, not promoted.
3. **Foreground / background prompt zone split** — the K most-active
   progressing tropes go to the Early zone (load-bearing); the rest, if
   they reach the prompt at all, go to Valley.
4. **Stagger fire-readiness** — when multiple tropes would fire on the
   same turn, only the highest-progress one fires this turn; the others
   slide to the next eligible turn.
5. **Cooldown after fire** — after a beat fires (or a trope `Resolves`),
   no new trope may transition `dormant → progressing` for N turns.

Each dimension is its own seam, and each gets a span. None of them is
"the" fix; they compose.

### The wire-first seam (gate-blocking)

The current Python tree has **no progression engine** — only a state
container and a YAML extractor. The wire-first gate therefore requires
that the test exercise the actual *tick site* introduced by this story,
called from a real turn dispatch path, not a unit-test on the tick
function in isolation. Two seams:

1. **Tick seam** — a new tick function (suggested name: `tick_tropes`)
   that takes `(snapshot, genre_pack, *, now_turn)` and mutates
   `snapshot.active_tropes` in place. It must be called from
   `_execute_narration_turn()` in
   `sidequest/server/session_handler.py` (around the
   `record_interaction()` call at the end of the turn — the same site
   45-1's `build_shared_world_delta` was wired against). The wire-first
   test must drive a multi-turn narration through the session handler
   and assert the tick fires once per turn, not call `tick_tropes`
   directly.
2. **Prompt-zone seam** — `TurnContext.pending_trope_context` (Early
   zone, `sidequest/agents/orchestrator.py:330`,
   registered at orchestrator.py:1151) and
   `TurnContext.active_trope_summary` (Valley zone,
   orchestrator.py:352, registered at orchestrator.py:1235) already
   exist as fields but **are never populated** anywhere
   (`grep -rn 'pending_trope_context\|active_trope_summary'` finds only
   the field declaration and the orchestrator registration). The fix
   wires `_build_turn_context` in
   `sidequest/server/session_helpers.py:148` to render those two
   fields from `snapshot.active_tropes`, with the K-most-active going
   into `pending_trope_context` and the remainder (truncated) into
   `active_trope_summary`. The wire-first test must hit
   `_build_turn_context` and assert both fields populate as expected.

The cap, cooldown, and stagger predicates live inside `tick_tropes`. Do
not promote them into `TurnManager` — they are domain logic, not turn
bookkeeping.

### Existing reuse points

- **`TropeState` model** (`sidequest/game/session.py:253`) — extend with
  the fields needed for cooldown bookkeeping (`fire_cooldown_until: int`,
  per-turn or per-interaction; `last_fired_turn: int | None`). Use
  `model_config = {"extra": "ignore"}` for forward-compat with old saves.
- **`PassiveProgression`** (`sidequest/genre/models/tropes.py:29`) —
  already carries `rate_per_turn`, `accelerators`, `decelerators`,
  `accelerator_bonus`, `decelerator_penalty`. The tick uses these. No
  schema change.
- **`TropeDefinition.escalation`** (`sidequest/genre/models/tropes.py:57`)
  — the threshold-keyed beat list. Fire predicate compares pre-tick and
  post-tick `progress` against thresholds; downward-crossing
  `detect_crossings` pattern lives in `sidequest/game/thresholds.py:11`
  and is reusable as a model.
- **`AttentionZone.Early` / `AttentionZone.Valley`** — already used
  throughout `orchestrator.py` for foreground/background separation. The
  Early zone is the "load-bearing" foreground in the description's
  language; Valley is the background.
- **`WorldMaterializer._apply_trope`** (line 429) — must NOT be rewritten;
  it remains the YAML→state path. The new tick is a sibling concern.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md OTEL principle)

The trope-engine span constants already exist as dead code in
`sidequest/telemetry/spans.py:152-158` and live in `FLAT_ONLY_SPANS`
(spans.py:2235-2241 — Phase 2 deferred baseline). This story moves them
out of `FLAT_ONLY_SPANS` and into `SPAN_ROUTES` with proper extract
lambdas, plus adds a new per-turn aggregate span. Required emissions:

| Span | When | Required attributes |
|------|------|---------------------|
| `turn.tropes` (existing constant `SPAN_TURN_TROPES`) | once per `tick_tropes()` call, regardless of whether anything fired | `active_trope_count` (int — progressing only), `progression_max` (float, 0.0-1.0), `progression_avg` (float), `queued_count` (int — tropes capped out and waiting), `cooldown_active` (bool), `turn_number` (int) |
| `trope.tick` (existing constant `SPAN_TROPE_TICK_PER`) | per-trope, inside the loop | `trope_id`, `progress_before`, `progress_after`, `delta`, `accelerator_hits`, `decelerator_hits` |
| `trope_activate` (existing constant `SPAN_TROPE_ACTIVATE`) | on `dormant → progressing` transition | `trope_id`, `from_status`, `to_status`, `cap_used` (int — slots in use after activation) |
| `trope_resolve` (existing constant `SPAN_TROPE_RESOLVE`) | on `progressing → resolved` transition | `trope_id`, `final_progress`, `beats_fired_total`, `cooldown_until_turn` |
| `trope.cap_blocked` (NEW constant `SPAN_TROPE_CAP_BLOCKED`) | when a candidate trope is held back because the cap is full | `trope_id` (the blocked one), `current_active_count`, `cap` |
| `trope.cooldown_blocked` (NEW constant `SPAN_TROPE_COOLDOWN_BLOCKED`) | when activation is blocked because cooldown is in effect | `trope_id`, `cooldown_until_turn`, `current_turn` |

The three "active count / max progression / avg progression" attributes
on `turn.tropes` are exactly what the story description calls out as the
required GM-panel emissions; place them on a single per-turn aggregate
span so the GM panel can render tempo with one query, not a join.

`SPAN_ROUTES` registration: `event_type="state_transition"`,
`component="tropes"`, `field="active_tropes"`, with `op` differentiated
per span (`tick`, `activate`, `resolve`, `cap_blocked`, `cooldown_blocked`).
Follow the pattern in `spans.py:332` (the 45-1 handshake span) for the
extract lambda shape.

### Cap, cooldown, K — the magic numbers

Make these constants, exported from a single module
(`sidequest/game/trope_tuning.py` or extend `sidequest/game/thresholds.py`).
Per CLAUDE.md "no silent fallbacks" and the spirit of ADR-068 (Magic
Literal Extraction), do not scatter them as inline literals.

Suggested initial values, expressly subject to playtest tuning:

- `MAX_SIMULTANEOUS_ACTIVE = 3` — matches description's "2-3"; pick the
  upper end and let playtest pull it down if pile-up persists.
- `FIRE_COOLDOWN_TURNS = 2` — short enough that the genre still feels
  alive, long enough that two beats can't land back-to-back.
- `FOREGROUND_K = 2` — at most 2 tropes get Early-zone billing;
  remainder (up to MAX) go Valley.
- `PROGRESSION_RATE_MULTIPLIER = 0.5` — half the YAML-declared
  `rate_per_turn` until playtest says otherwise.

Per-genre overrides are out of scope (see Scope Boundaries).

### Test files (where new tests should land)

- New: `tests/game/test_trope_tick.py` — unit tests for the tick
  function: cap, cooldown, stagger, rate multiplier, accelerator/
  decelerator application, beat-fire predicate.
- New: `tests/server/test_trope_engine_wiring.py` — wire-first boundary
  test driving multi-turn narration through `session_handler_factory()`
  (`tests/server/conftest.py:330`) with a fake genre pack carrying 4
  tropes; assert (a) only K go to `pending_trope_context`, (b) tick is
  called once per turn, (c) the (N+1)th trope is queued, not active,
  (d) `turn.tropes` span fires on every turn including silent ones.
- Extend: `tests/telemetry/test_spans.py` — register routes for
  the trope spans; remove from `FLAT_ONLY_SPANS`.
- Extend: `tests/server/test_encounter_trope_resolution.py` already
  exists for the encounter↔trope resolve path; add a regression that
  resolution kicks the cooldown on.

## Scope Boundaries

**In scope:**

- New `tick_tropes(snapshot, genre_pack, *, now_turn)` function with
  rate multiplier, simultaneous cap, fire cooldown, stagger predicate.
- Extend `TropeState` with `fire_cooldown_until` and `last_fired_turn`
  fields (forward-compat: `model_config = {"extra": "ignore"}`).
- Wire `tick_tropes` into `_execute_narration_turn()` once per turn.
- Render `pending_trope_context` (Early zone, K most-active tropes)
  and `active_trope_summary` (Valley zone, queued/background) into
  `_build_turn_context`. Both fields exist already; populate them.
- Move trope-engine spans out of `FLAT_ONLY_SPANS` into `SPAN_ROUTES`.
- New aggregate span `turn.tropes` carrying `active_trope_count`,
  `progression_max`, `progression_avg`, `queued_count`,
  `cooldown_active` per turn.
- New spans `trope.cap_blocked`, `trope.cooldown_blocked` for
  diagnostic visibility on activation refusals.
- Constants module for the four tuning numbers.
- Wire-first integration test reproducing the Felix pile-up scenario:
  4 candidate tropes, cap=3 → 3 active + 1 queued; one fires →
  cooldown blocks the queued one for N turns.

**Out of scope:**

- **Trope authoring changes.** Genre packs' `tropes.yaml` files are
  unchanged. New fields are runtime-only.
- **Resolution mechanic.** How a trope transitions to `resolved` is
  sibling story 45-20 (`trope_resolved` write-back). 45-27 only
  *responds* to the resolution by kicking the cooldown.
- **Per-genre tuning overrides.** A future story could let
  `genre_packs/<g>/pack.yaml` override `MAX_SIMULTANEOUS_ACTIVE` or
  `FIRE_COOLDOWN_TURNS`. 45-27 ships with global constants; per-genre
  is a follow-up if playtest demands it.
- **`history.yaml` materialization changes.** `_apply_trope`
  (`world_materialization.py:429`) is the YAML→state path and stays
  intact. The tick is a sibling concern; do not merge them.
- **Cross-session passive advancement (`rate_per_day`).** The Python
  port has no day-clock yet. Story scope is `rate_per_turn` only;
  `rate_per_day` is read but unused (status quo preserved).
- **UI changes.** GM panel reads `turn.tropes` via the watcher
  pipeline that already exists. No new UI work in this story.

## AC Context

The story's title carries the contract; the description's five
dimensions expand to six numbered ACs:

1. **Cap blocks the (N+1)th simultaneous-active trope.**
   - Test: drive a fake genre pack with 4 candidate tropes whose
     activation triggers all match this turn's player input. After tick,
     assert `len([t for t in active_tropes if t.status == "progressing"])
     == MAX_SIMULTANEOUS_ACTIVE` and the (N+1)th trope's status remains
     `dormant`. The blocked one MUST emit `trope.cap_blocked`.
   - Wire-first: scenario runs through `_execute_narration_turn()`,
     not via direct calls to `tick_tropes`.

2. **Cooldown blocks new activation for `FIRE_COOLDOWN_TURNS` turns
   after any beat fires.**
   - Test: tick to a turn where one trope's progress crosses a beat
     threshold. On that turn, set `cooldown_until = now + N`. On turns
     `now+1` through `now+N`, a fresh candidate trope is held in
     `dormant` and emits `trope.cooldown_blocked`. On turn `now+N+1`,
     it activates normally.
   - Negative test: an *already-active* trope continues to progress
     during cooldown — cooldown only gates new activations.

3. **Stagger predicate prevents two beats firing the same turn.**
   - Test: two tropes both cross beat thresholds on the same tick.
     Assert exactly one emits `beat_fired` (or the equivalent extractor
     write); the other's pre-fire progress is held at the threshold and
     it fires next eligible turn (after cooldown).
   - Asserts `progression_max` on `turn.tropes` reflects the held trope.

4. **Foreground/background prompt zone split — narrator sees only K
   most-active tropes in Early zone.**
   - Test: drive a snapshot with 5 progressing tropes (cap=5 for the
     test, or override). Assert the resulting `TurnContext` has
     `pending_trope_context` carrying exactly `FOREGROUND_K` trope
     beat directives (the highest-progress ones) and
     `active_trope_summary` carrying the remainder (truncated to a
     summary line per trope). Negative test: with 0 active tropes,
     both fields are `None` and neither prompt section is registered
     (zero-byte-leak discipline matches 45-1's `state_summary` pattern).
   - Wire-first: assertion runs against the `TurnContext` returned
     by `_build_turn_context`, not against a `render_trope_summary`
     helper unit-tested in isolation.

5. **`turn.tropes` aggregate span fires every turn with the three
   required metrics.**
   - Test: 5-turn narration. Assert span fires 5 times, and each
     carries `active_trope_count` (int, monotone-bounded by
     MAX_SIMULTANEOUS_ACTIVE), `progression_max` (float in [0.0, 1.0]),
     `progression_avg` (float in [0.0, 1.0]). Sebastien's lie-detector
     reads these three fields.
   - Test: span fires even on turns where active_trope_count == 0
     (empty world). The absence of tropes is itself a tempo signal
     — silence on the wire would look like the engine never ran.
   - Test: `SPAN_ROUTES[SPAN_TURN_TROPES]` is registered with
     `component="tropes"` so the watcher pipeline dispatches it to
     the GM panel; the constant is no longer in `FLAT_ONLY_SPANS`.

6. **Per-trope activate/resolve spans fire on the matching transition.**
   - Test: drive a trope through `dormant → progressing → resolved`
     across several turns. Assert exactly one `trope_activate` and one
     `trope_resolve` event with the required attributes. The
     `trope_resolve` event MUST carry `cooldown_until_turn` so the GM
     panel can show the cooldown bar.
