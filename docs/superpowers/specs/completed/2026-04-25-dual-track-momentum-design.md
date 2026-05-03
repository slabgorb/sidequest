# Dual-Track Momentum — Design

**Date:** 2026-04-25
**Status:** Approved (brainstorming) — implementation plan pending
**Scope:** `sidequest-server` (engine + narrator prompt assembly), `sidequest-content` (rules.yaml migration across shipping packs)
**Reference save:** `~/.sidequest/saves/games/2026-04-25-dungeon_survivor/save.db` — solo `caverns_and_claudes` / `dungeon_survivor`, encounter resolved at `momentum=11` while narration shows the player KO'd

## Problem

The current encounter momentum metric is a single bidirectional dial shared by every actor in the encounter. Every beat applies its `metric_delta` uniformly to that dial regardless of which side acted, so an enemy's `attack` advances the **party-winning** threshold by the same amount as a player's `attack`. The design comment in `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml:80-91` describes momentum as "positive = party is winning, negative = party is losing," but the code at `sidequest-server/sidequest/server/narration_apply.py:337` and the legacy `sidequest-server/sidequest/server/narration_apply.py:552` apply deltas without consulting `actor.role`:

```python
enc.metric.current += applied_delta
```

Three structural failures compound:

1. **Sign collapse.** Because the engine is actor-blind, in solo play the NPCs (which outnumber the PC) drag the metric toward `threshold_high` regardless of who is winning the fiction. The `2026-04-25-dungeon_survivor` save reaches `momentum=11` (player victory by the engine) on a turn whose narration shows Sam Jones on his knees with a sickle to the temple while the Host shouts "AND THAT IS YOUR SEASON ELEVEN OPENER, FOLKS!"
2. **No structured failure branch.** Beats like `shield_bash` describe their downside in free-text `risk:` ("Overcommitted — lose 2 momentum and take a counter on failure") but never set `failure_metric_delta`. The fail branch in `narration_apply.py:308-314` only fires when *both* `dice_failed is True` and `beat.failure_metric_delta is not None`. On free-text turns there is no dice outcome, so even if structured failure values existed they would not fire.
3. **Narrator doesn't know the encounter ended.** After `enc.resolved` flips true at beat 5, the next four narration events in the save (events 6–9) continue to describe combat: a parry, a missed lunge, the temple-strike KO, the Promo magnanimously letting the contestant up, and finally an off-channel hiss when the Host runs out of script. The encounter snapshot says "resolved, player won"; the narrator says "the rookie ate canvas." Two systems telling two different stories about the same moment.

The current `outcome` is `f"resolved at beat {n}"`, which carries no win/loss information for the narrator or the consequence pipeline to act on.

A fourth issue compounds the first three: the save's `events` rows are all `kind='NARRATION'`. The OTEL spans the engine emits today (`encounter.beat_applied`, `encounter.resolved`, etc. — see `sidequest-server/sidequest/telemetry/spans.py`) and the watcher events `_watcher_publish` produces for state transitions are not surviving as queryable events the GM panel can read post-hoc. The GM panel is the lie-detector this project depends on per CLAUDE.md's OTEL Observability Principle — without it the engine can claim "encounter resolved player_victory at beat 5" while the prose shouts "Sam is on his knees" and nobody can tell which is true. **This is in scope.** Every change in this spec emits observable, queryable telemetry, and the regression playtest must demonstrate the GM panel rendering the corrected beat-by-beat flow against the existing save.

## Design summary

Replace the single bidirectional `metric` with **two ascending dials per encounter** (`player_metric` and `opponent_metric`), each beat applied to the dial of the actor's *side* — a structured field declared by the narrator, never inferred. Outcome becomes a structured enum and the narrator receives a one-shot `[ENCOUNTER RESOLVED]` prompt zone after the dial crosses.

Five further additions, each extending an existing SideQuest type rather than introducing a parallel system:

1. **Beat `kind`.** Every beat declares a kind ∈ `{strike, brace, push, angle}` that determines its mechanical contract — what its delta means, whether it can resolve the encounter, whether it can create scene tags. This replaces the current "every beat is a free-form bag of fields" with a small, typed taxonomy. Per-kind defaults make most beats one-line declarations.
2. **Five-tier outcome resolution.** Existing `RollOutcome` (`CritFail / Fail / Success / CritSuccess`) gets a `Tie` tier when the roll exactly meets difficulty. Beats declare per-tier deltas, with sensible defaults inferred from `kind`. The boolean `dice_failed` is replaced with the structured outcome.
3. **Encounter tags.** A new `StructuredEncounter.tags: list[EncounterTag]` field. `angle`-kind beats create tags with a leverage count; future beats can spend leverage to gain a delta bonus. v1 ships data model + telemetry + narrator visibility; the spend mechanic is v2.
4. **Statuses with severity.** Existing `Character.statuses: list[str]` becomes `list[Status]` with `severity ∈ {scratch, wound, scar}` and an `absorbed_shifts` count. v1 ships the structured shape and a forward-migration path for bare strings; the absorption-at-threshold mechanic is v2.
5. **Yield action.** A structured player exit. `YIELD` is a new player-action message kind; on receipt the encounter resolves with `outcome="yielded"`, the narrator gets the structured signal, and the player's `EdgePool` refreshes by `1 + 1 per scratch_or_worse_taken_this_encounter`. The "I want out" structurally honored, no fight-to-the-death assumption.

**No HP.** No HP. No HP. Momentum dials are the encounter-level pressure; statuses are the actor-level lingering cost. Damage is never a number that ticks down a hit-point reserve.

**No string matching.** Side, kind, outcome tier, severity, beat id, confrontation type, encounter outcome — every routable signal is a closed enum or a keyed lookup. Per SOUL.md "The Zork Problem," the narrator's natural-language ceiling stays open (text labels on tags and statuses are free-form prose) while the engine's contracts stay structured (mechanical fields are enums). The existing `hostile_keywords` substring-match block at `narration_apply.py:466-472` is deleted, not refactored.

**Native vocabulary.** Every concept here is a SideQuest term. `kind`, `Tie`, `EncounterTag`, `leverage`, `Status.severity`, `yield`, `EdgePool` — none of these are imports of another system's terminology. The mechanical *insights* drawn from tabletop RPG design (typed actions, multi-tier outcomes, scene tags, narrative-cost wounds, voluntary concession) are real and load-bearing; the words used to describe them are ours.

## Architecture

### Schema changes (`pack rules.yaml`)

Each `confrontation` definition replaces its single `metric` with two dials, and each beat declares a `kind` plus per-tier `deltas`:

```yaml
confrontations:
  - type: combat
    label: Dungeon Combat
    category: combat
    player_metric:
      name: momentum
      starting: 0
      threshold: 10
    opponent_metric:
      name: momentum
      starting: 0
      threshold: 10
    beats:
      - id: attack
        label: Attack
        kind: strike
        base: 2                         # success delta on own dial
        stat_check: STR
        narrator_hint: …

      - id: defend
        label: Defend
        kind: brace
        base: 1                         # success delta on opponent dial (negative direction implied by kind)
        stat_check: CON
        narrator_hint: …

      - id: shield_bash
        label: Shield Bash
        kind: strike
        base: 4
        deltas:
          crit_fail:  { own: -2 }       # promoted from free-text "risk:"
          crit_success: { own: 4, grants_tag: "Off-Balance" }
        stat_check: STR
        narrator_hint: …

      - id: feint
        label: Feint
        kind: angle
        target_tag: "Out of Position"   # text on the tag this beat creates
        stat_check: DEX
        narrator_hint: …

      - id: flee
        label: Flee
        kind: push
        stat_check: DEX
        # `push` kind defaults to `resolution: true` on success and crit_success
```

Beats specify only the fields they need. The engine fills in any unspecified outcome tier from the **kind defaults** in the next section. Per-tier overrides at `deltas:` win over kind defaults; kind defaults win over engine zeros.

Field semantics, *all measured from the actor's perspective*:

| field | meaning | default |
|---|---|---|
| `kind` | one of `strike` / `brace` / `push` / `angle` — drives outcome semantics | required |
| `base` | scalar magnitude; how `kind` reads it depends on the kind | `1` |
| `deltas.<tier>.own` | delta to the actor's own dial at that outcome tier | from kind defaults |
| `deltas.<tier>.opponent` | delta to the other side's dial at that outcome tier | from kind defaults |
| `deltas.<tier>.grants_tag` | text label of an encounter tag created at this tier | `None` |
| `deltas.<tier>.grants_fleeting_tag` | text label of a single-use tag (one charge, vanishes on use) | `None` |
| `deltas.<tier>.resolution` | beat ends the encounter at this tier | from kind defaults |
| `target_tag` | for `angle` beats, the default text of the tag created on `success` | required for `angle` |
| `stat_check` | the stat rolled to determine outcome tier | required when dice path is used |
| `narrator_hint` | free-form prose hint shown to the narrator when this beat is selected | optional |

### Beat kinds and outcome tiers

Four kinds, five tiers. Each kind has a default delta table; a beat overrides only what it needs.

**Outcome tiers** (extending `RollOutcome`):

| Tier | Trigger | Existing? |
|---|---|---|
| `CritFail` | nat-1 on a d20 in pool | yes |
| `Fail` | `total < difficulty` | yes |
| `Tie` | `total == difficulty` | **new** |
| `Success` | `difficulty < total < difficulty + 3` | yes |
| `CritSuccess` | nat-20 on a d20 OR `total >= difficulty + 3` | extended |

The `CritSuccess` rule gains the `total >= difficulty + 3` clause to cover the "decisive margin" case that is currently only granted by a nat-20. Crit by margin is the structural equivalent of a tabletop "succeed-with-style" outcome and is needed for the `angle` kind's two-leverage tag grant. Existing nat-20 path remains.

**Default delta tables.** `b` denotes the beat's `base`. Authors override per-tier deltas to depart from these defaults; in C&C migration most beats won't override anything except the occasional `crit_fail` when a beat has a real-world risk like `shield_bash`.

`strike` — advance own dial / press the opponent:

| Tier | own | opponent | extras |
|---|---:|---:|---|
| CritFail | `0` | `0` | — |
| Fail | `0` | `0` | — |
| Tie | `b // 2` | `0` | a graze; round down |
| Success | `b` | `0` | — |
| CritSuccess | `b` | `0` | `grants_fleeting_tag: "Opening"` |

`brace` — absorb / counter:

| Tier | own | opponent | extras |
|---|---:|---:|---|
| CritFail | `0` | `+1` | a free hit lands |
| Fail | `0` | `0` | — |
| Tie | `0` | `-(b // 2)` | partial absorption |
| Success | `0` | `-b` | — |
| CritSuccess | `0` | `-b` | `grants_fleeting_tag: "Counter Stance"` |

`push` — achieve a discrete narrative goal (flee, climb, persuade-out, slip-the-handcuffs):

| Tier | own | opponent | extras |
|---|---:|---:|---|
| CritFail | `-1` | `0` | backslide |
| Fail | `0` | `0` | — |
| Tie | `0` | `0` | partial: encounter advances narratively but does not resolve |
| Success | `0` | `0` | `resolution: true` |
| CritSuccess | `0` | `0` | `resolution: true`, `grants_fleeting_tag: "Clean Exit"` |

`angle` — set up a scene tag for future leverage:

| Tier | own | opponent | extras |
|---|---:|---:|---|
| CritFail | `0` | `0` | the angle backfires: opposing side gets a fleeting tag named after `target_tag` |
| Fail | `0` | `0` | — |
| Tie | `0` | `0` | `grants_fleeting_tag: <target_tag>` (one charge, vanishes on use) |
| Success | `0` | `0` | `grants_tag: <target_tag>` with `leverage: 1` |
| CritSuccess | `0` | `0` | `grants_tag: <target_tag>` with `leverage: 2` |

A `push` beat with `Tie` doesn't resolve but doesn't waste the turn either — it advances the *narrative* state. The narrator gets a structured signal in the encounter zone that the goal is "in progress" so the prose can reflect partial achievement.

### Encounter tags

```python
class EncounterTag(BaseModel):
    text: str                # free-form prose label, e.g. "Off-Balance", "On Fire"
    created_by: str          # actor name
    target: str | None       # actor name (per-actor tag) or None (scene tag)
    leverage: int            # remaining bonus charges; 0 means "tracked but spent"
    fleeting: bool           # True = clears at end of scene, regardless of leverage
    created_turn: int
```

Stored on `StructuredEncounter.tags: list[EncounterTag]`. Created by `angle` beats and by `grants_tag` / `grants_fleeting_tag` extras on other kinds. Visible in:

- The narrator's encounter prompt zone (rendered as a bullet list under the active actors).
- The GM panel (timeline rows of kind `ENCOUNTER_TAG_CREATED`).
- The encounter snapshot in saves (full round-trip).

**v1 mechanic:** create, display, persist. Tags exist as scene state the narrator can lean on prose-wise, and the GM panel can show them — but the engine does not yet *spend* leverage. A future beat declaring "I leverage the *Off-Balance* tag" is v2.

**v2 mechanic** (deferred): a beat may declare `consumes_leverage_from: <tag_text>` to spend one charge for a `+2` to its outcome tier (e.g., a Tie becomes a Success). When `leverage` reaches `0` and the tag is `fleeting`, the engine removes it; otherwise it stays as scene context.

### Statuses with severity

`Character.statuses` becomes structured:

```python
class StatusSeverity(str, Enum):
    Scratch = "Scratch"     # clears at scene end
    Wound = "Wound"          # clears at session end
    Scar = "Scar"            # clears only at a milestone / healing event

class Status(BaseModel):
    text: str                # free-form prose, e.g. "Cracked Temple", "Mocked on Live TV"
    severity: StatusSeverity
    absorbed_shifts: int     # 0 in v1; the absorption mechanic is v2
    created_turn: int
    created_in_encounter: str | None
```

**Migration of existing string statuses.** The current `list[str]` carries free prose like `"Bleeding"`. The pack-load and save-load paths convert each bare string to `Status(text=<the string>, severity=Scratch, absorbed_shifts=0, created_turn=0, created_in_encounter=None)`. No content authoring change is required for existing packs; new authoring uses the structured form.

**v1 mechanic:** narrator can declare new statuses on actors via the existing narration-extraction path (extended schema). Statuses appear on the character sheet and in GM panel telemetry. They do not yet absorb shifts.

**v2 mechanic** (deferred): when an actor's side is about to cross threshold, the engine offers a status take to absorb shifts. Player actors get an interactive prompt; NPC actors get the choice declared by the narrator. The status's `absorbed_shifts` is set to its severity's absorption budget (`Scratch=2`, `Wound=4`, `Scar=6`). This is the core "no HP, but combat hurts narratively" mechanic and is the major v2 deliverable.

**Recovery.** v1 spec, v1 wiring: `Scratch` statuses clear at scene end (existing `EncounterPhase.Resolution` transition is the natural hook). `Wound` and `Scar` recovery flows lean on existing systems (rest, narrative milestones) and are tuned per-pack content-side; the engine simply tracks `severity` and lets pack-defined recovery hooks fire on it.

### Yield action

A new player-action message kind: `YIELD`. Surface area:

- **Wire.** New `MessageType.YIELD` in `sidequest/protocol`. Payload carries no fields — yielding is a structural intent.
- **UI.** A "Yield" button in the active-encounter panel, plus a `/yield` command-line. Available whenever an encounter is active and the player's side has not already yielded.
- **Engine.** On receipt:
  - `enc.outcome = "yielded"`, `enc.resolved = True`.
  - `pending_resolution_signal` set with `outcome="yielded"` and a count of statuses-of-severity-≥-Scratch the yielding actor accumulated during the encounter.
  - The yielding actor's `EdgePool.current` increases by `1 + status_count`, capped at `EdgePool.max`. (This is the existing edge refresh mechanism — `EdgePool.recovery_triggers` already supports `OnResolution`; a new trigger value `OnYield` is added.)
  - Multi-PC: any PC can yield individually; their actor's role becomes `withdrawn` and they take no further beats this encounter. The encounter resolves only when *every* `side="player"` actor has yielded or been taken out.

- **Narrator.** The `[ENCOUNTER RESOLVED]` zone gains a third outcome value (`yielded`) and prose-direction:

  ```
  outcome: yielded
  yielded_actors: [Sam Jones]
  edge_refreshed: 3
  Describe the actor's exit on their own terms — they chose to leave.
  Honor the choice. The opposing side does not pursue or strike further.
  ```

  This is the "Alex freezes in combat, taps yield" path. Mechanically the encounter is over; narratively the player narrated their own out. No DM-bullying.

- **NPC yields** (v2). The same data path supports NPC yielding (the Promo throws his sickle down: a season-eleven Stalker can canonically tap out for the cameras). Engine-side, an NPC yield is a narrator-declared event — the narrator emits `npc_yielded: <actor>` in the next turn's payload. v1 does not implement; the data model is forward-compatible.

### Engine changes (`sidequest-server`)

**`StructuredEncounter`** (`sidequest/game/encounter.py`):

- Replace `metric: EncounterMetric` with `player_metric: EncounterMetric` and `opponent_metric: EncounterMetric`. Each is the existing ascending shape (`name`, `current`, `starting`, `threshold`). Drop `MetricDirection` — both dials are ascending; bidirectional was the single-dial workaround.
- Add `tags: list[EncounterTag] = []`.
- `EncounterActor` gains `side: Literal["player", "opponent", "neutral"]`, set at instantiation from the narrator's payload, and `withdrawn: bool = False` (set by yield).
- `outcome` becomes one of: `player_victory`, `opponent_victory`, `resolution_beat:<beat_id>`, `yielded`, or `None` while unresolved. Replaces the current `f"resolved at beat {n}"` string.

**`BeatSelection`** (`sidequest/agents/orchestrator.py:91-98`): shape gains `outcome: RollOutcome` (the resolved tier). Side is looked up via the named actor; the narrator does not re-declare side per beat. On dice-replay turns the engine fills `outcome` from the dice resolution; on free-text turns the narrator emits the tier it intends.

**`Status`** (`sidequest/game/creature_core.py`): `statuses: list[str]` becomes `statuses: list[Status]` per the structured shape above. Loader migrates bare strings forward.

**`_apply_beat`** (`sidequest/server/narration_apply.py:273-385` and `sidequest/server/dispatch/dice.py:127-168`): replaced with a single helper that resolves the per-tier deltas, routes by side, and processes any tag/resolution extras:

```
def _apply_beat(enc, actor, beat, outcome: RollOutcome) -> ResolutionResult:
    if actor.side == "neutral" or actor.withdrawn:
        emit_watcher("beat_skipped", reason="neutral_or_withdrawn")
        return ResolutionResult.unresolved()

    deltas = resolve_tier_deltas(beat, outcome)   # merges per-kind defaults + per-beat overrides

    own  = enc.player_metric if actor.side == "player" else enc.opponent_metric
    other = enc.opponent_metric if actor.side == "player" else enc.player_metric

    own.current   += deltas.own
    other.current += deltas.opponent

    if deltas.grants_tag:
        enc.tags.append(EncounterTag(text=deltas.grants_tag, leverage=deltas.tag_leverage,
                                     fleeting=False, created_by=actor.name, ...))
    if deltas.grants_fleeting_tag:
        enc.tags.append(EncounterTag(text=deltas.grants_fleeting_tag, leverage=1,
                                     fleeting=True, created_by=actor.name, ...))
    if deltas.tag_backfire:                       # angle CritFail
        enc.tags.append(EncounterTag(text=beat.target_tag, leverage=1,
                                     fleeting=True, created_by=actor.name,
                                     target=opposite_side_first_actor(enc, actor.side)))

    enc.beat += 1
    _advance_phase(enc)

    return _check_resolution(enc, beat, deltas)
```

`_check_resolution` checks `player_metric.current >= player_metric.threshold` first, then `opponent_metric.current >= opponent_metric.threshold`, then `deltas.resolution`. The first to fire sets `enc.resolved = True` and `enc.outcome` to the matching value.

**Tie-break.** Beat application within a turn iterates `result.beat_selections` in order. ADR-036 sealed-letter turns guarantee player beats arrive before NPC beats. First threshold crossed wins; later beats are still applied (for telemetry truth) but do not change `outcome`.

**Side validation.** Narrator payload declaring a `side` outside `{"player","opponent","neutral"}` raises `ValueError`. No silent fallback. The `encounter.invalid_side` span fires before the exception so the panel sees the contract break.

**Yield handler.** New `MessageType.YIELD` dispatch in `sidequest/server/dispatch/`. On receipt:

```
def handle_yield(snapshot, player_id):
    enc = snapshot.encounter
    if enc is None or enc.resolved:
        return DispatchError("no active encounter")
    actor = enc.find_actor_for_player(player_id)
    actor.withdrawn = True
    if all(a.withdrawn or a.taken_out for a in enc.actors if a.side == "player"):
        enc.resolved = True
        enc.outcome = "yielded"
        snapshot.pending_resolution_signal = ResolutionSignal(
            outcome="yielded",
            yielded_actors=[a.name for a in enc.actors if a.side == "player" and a.withdrawn],
            edge_refreshed=compute_edge_refund(snapshot, enc),
        )
        refund_edge(snapshot, enc)
```

**Deletions:**

- `apply_encounter_updates` and its keyword-bucket actor classification at `narration_apply.py:403-602`. Already dead per the comment at `session_handler.py:2852`; same PR per the dead-code-removal rule.
- The `MetricDirection` enum and its `_DIRECTION_BY_NAME` map at `dispatch/encounter_lifecycle.py:26-30`.
- The `hostile_keywords` substring match at `narration_apply.py:466-472`.

### Narrator integration

**Narrator output schema additions:**

- `npcs_present` / `npcs_met` entries gain `side ∈ {"player","opponent","neutral"}`. Required.
- Each `BeatSelection` gains `outcome ∈ {"CritFail","Fail","Tie","Success","CritSuccess"}`. On dice-replay turns the engine overwrites this from the actual dice tier; on free-text turns the narrator's declared tier stands.
- A new `status_changes` array, each entry `{actor: <name>, status: {text, severity}}` — the narrator emits these to declare new actor statuses driven by the prose. Required-when-applicable; the narrator prompt zone is extended with the closed `severity` set.

**Side declaration.** Prompt zone at `agents/narrator.py:177-182` is extended with:

> Each NPC entry must include `"side"`: one of `"player"` (party allies), `"opponent"` (anyone the party is fighting), or `"neutral"` (bystanders, narrators, audience). This is structural — `role` remains free-form prose, `side` is a closed enum the engine routes on.

**Outcome declaration.** Prompt zone is extended with:

> Each `beat_selection` must include `"outcome"`: one of `"CritFail"`, `"Fail"`, `"Tie"`, `"Success"`, `"CritSuccess"`. This is the tier the prose describes — `"Fail"` if the action did not succeed, `"Success"` if it cleanly worked, `"Tie"` if it succeeded at a minor cost or partially, `"CritSuccess"` if it succeeded with a notable extra benefit (advantage, momentum shift), `"CritFail"` if it failed badly and the actor is now in a worse position than before. Match the tier to the prose.

**Encounter zone — tags + statuses.** When an encounter is active, the prompt zone now lists current tags and per-actor statuses:

```
Active encounter: combat
Player metric: 4 / 10
Opponent metric: 7 / 10
Actors:
  - Sam Jones (side=player, statuses: [Bruised Ribs (Wound)])
  - The Promo (side=opponent)
Encounter tags:
  - "Off-Balance" on The Promo (leverage 1, created turn 3)
  - "Cracked Plate" on The Promo (fleeting, created turn 4)
```

The narrator can lean on tags in prose ("the Promo, still off-balance, swings wide") and the GM panel sees the same state.

**Active-encounter context exclusion.** The current code at `narration_apply.py:241-242` only skips *re-instantiation* when `enc.resolved is True`. The narrator prompt assembly that injects available beats and actor lists still fires on resolved encounters. The fix: the prompt assembler short-circuits when `enc.resolved` is true and instead emits the resolution zone described next.

**`[ENCOUNTER RESOLVED]` zone (one-shot).** When `_apply_beat` flips `enc.resolved` to true, session state stashes a `pending_resolution_signal: ResolutionSignal | None` slot. On the *next* narrator turn, prompt assembly injects:

```
[ENCOUNTER RESOLVED]
type: combat
outcome: opponent_victory
final_player_metric: 4
final_opponent_metric: 11
The encounter has ended this turn. Describe the resolution and any
immediate transition out of the scene. Do NOT emit beat_selections.
Do NOT continue describing the encounter as if it were active.
```

After consumption, the slot is cleared. If the narrator emits `beat_selections` in the same turn anyway (it shouldn't), the engine drops them with a `beat_skipped reason=encounter_resolved` watcher event — same pattern as the existing dice-replay-turn filter at `narration_apply.py:289-298`.

**Why a structured zone, not free-form context.** The narrator currently reads encounter state from the snapshot via the standard prompt zones; the resolution signal is *transient* (one turn) and *load-bearing* (must change behavior). A dedicated zone is the cheapest way to make the contract unambiguous, matches the existing pattern of structured prompt zones in `narrator.py`, and is easy to test (search for the literal `[ENCOUNTER RESOLVED]` header in the assembled prompt).

### Data flow (one turn, mid-fight)

```
PLAYER_ACTION
  → narrator.turn(prompt) → NarrationTurnResult{
        beat_selections: [{actor: "Sam", beat_id: "attack"},
                          {actor: "The Promo", beat_id: "attack"},
                          {actor: "The Host", beat_id: "neutral"}],
        npcs_present: [{name: "The Promo", side: "opponent", …},
                       {name: "The Host", side: "neutral", …}],
        prose: "The sword catches the seam at the ribs…"
     }
  → _apply_narration_result_to_snapshot:
      for sel in beat_selections:
          actor = enc.find_actor(sel.actor)
          _apply_beat(enc, actor, beat_lookup[sel.beat_id], dice_failed)
        # Sam (side=player) attack +2 → player_metric: 0 → 2
        # Promo (side=opponent) attack +2 → opponent_metric: 0 → 2
        # Host (side=neutral) → dropped, watcher event
      if enc.resolved:
          sd.pending_resolution_signal = ResolutionSignal(
              encounter_type=enc.encounter_type,
              outcome=enc.outcome,
              final_player_metric=enc.player_metric.current,
              final_opponent_metric=enc.opponent_metric.current,
          )
  → emit NARRATION frame
NEXT TURN:
  → narrator prompt assembly:
      if sd.pending_resolution_signal:
          inject [ENCOUNTER RESOLVED] zone
          do not inject active-encounter zone
          sd.pending_resolution_signal = None
      else if enc and not enc.resolved:
          inject active-encounter zone (existing behavior)
```

## Multi-participant cases

Five cases the design must handle. Cases 1–4 are v1; case 5 is v2.

| # | Case | Handling |
|---|---|---|
| 1 | Solo PC vs. multi-NPC | PC declared `side=player`, hostile NPCs `side=opponent`, neutrals `side=neutral`. Routing applies. |
| 2 | Multi-PC playgroup | All PCs `side=player`; their per-round beats stack on `player_metric`. ADR-036 sealed-letter turns assemble the per-player beats into one ordered list before `_apply_beat` iteration. |
| 3 | Mixed sides (party + ally vs. enemies) | Allied NPC `side=player`, fights alongside the party. Same routing — no per-faction subdivision in v1. |
| 4 | Non-combatants in actor list | Announcer/audience/bystanders declared `side=neutral`. Their beats (if any) are dropped with telemetry. They appear in prose without touching the dials. |
| 5 | Charm / turncoat / 3-way politics | **Out of scope for v1.** The data model already supports it (side is a real field on a stored actor), but mid-encounter side mutation, three-way thresholds, and charm-driven beat redirection are deferred. The v1 contract: side is set at actor instantiation and is not changed during the encounter. |

**Threshold tuning under multi-PC pressure.** Three PCs apply roughly 3× the per-round pressure to `opponent_metric` than one PC does. v1 keeps the per-pack threshold fixed (default 10) — the playgroup's own pacing is the tuning lever, not the engine. If playtest with the full Sunday group shows fights ending in 2 rounds, content authors raise the threshold per pack. Engine support for party-size-scaled thresholds can land later without schema changes (it's a single multiplier read at instantiation).

## Migration impact

Each shipping pack's `rules.yaml` confrontations get edited. Engine changes break the old schema; content migration must land in the same release.

| Pack | Notes |
|---|---|
| `caverns_and_claudes` | Primary victim of current bug. `dungeon_survivor` world relies on this; canary content for stories 1–2 tests. |
| `heavy_metal` | Migrate every confrontation in `rules.yaml`. |
| `space_opera` | Migrate every confrontation in `rules.yaml`. |
| `spaghetti_western` | Migrate every confrontation in `rules.yaml`. The current `bidirectional` duel maps cleanly to two ascending dials. |
| `mutant_wasteland` | Migrate every confrontation in `rules.yaml`. |
| `elemental_harmony` | Migrate every confrontation in `rules.yaml`. |
| `genre_workshopping/*` | Drafts. Migrate only those promoted to shipping during this work. |

Story 3 begins with a `rg -n "metric:" sidequest-content/genre_packs/*/rules.yaml` pass to enumerate every confrontation that needs touching, so the migration list is generated from the source rather than guessed.

Per-pack edits:

- Split single `metric` → `player_metric` + `opponent_metric`.
- For each beat: declare `kind` (`strike` / `brace` / `push` / `angle`); set `base`; only override `deltas.<tier>` when the beat departs from kind defaults.
- Promote any free-text `risk:` failure description into a structured `deltas.crit_fail` (or `deltas.fail`) entry.
- Map existing beats to kinds: anything labeled "Attack", "Strike", "Bash", "Shoot" → `strike`. "Defend", "Block", "Parry", "Dodge" → `brace`. "Flee", "Climb", "Persuade", "Sneak Past" → `push`. "Feint", "Distract", "Set Up", "Spot Weakness" → `angle`. New beats authored in the new vocabulary.
- For `angle` beats (often new), declare `target_tag` text in setting-appropriate prose.

Content authors decide tuning; engine routes the numbers and tier semantics.

## Telemetry

Every decision point in the new engine emits an OTEL span **and** a watcher event, and the watcher event is persisted to the save's `events` table as a typed row. Per CLAUDE.md's OTEL Observability Principle, the GM panel is the lie-detector: it must be able to render the full beat-by-beat history of any encounter from the saved events alone, without consulting in-memory state. Today the panel cannot do that for momentum because the only `kind` the `events` table stores is `NARRATION`.

### Span inventory

Existing spans (`sidequest-server/sidequest/telemetry/spans.py`) extended:

| Span | New / changed attributes |
|---|---|
| `encounter.confrontation_initiated` | `player_metric_threshold`, `opponent_metric_threshold`, `player_actor_count`, `opponent_actor_count`, `neutral_actor_count` |
| `encounter.beat_applied` | `actor_side`, `beat_kind`, `outcome_tier`, `metric_target` (`player`/`opponent`/`both`), `own_delta`, `opponent_delta` |
| `encounter.beat_failure_branch` | (deprecated — replaced by `beat_applied` with `outcome_tier=Fail`/`CritFail`; remove if no other consumer) |
| `encounter.resolved` | `outcome` (structured: `player_victory`/`opponent_victory`/`resolution_beat:<id>`/`yielded`), `final_player_metric`, `final_opponent_metric`, `triggering_side` |
| `combat.tick` | `player_metric_current`, `opponent_metric_current` |

New spans:

| Span | Attributes | Fires when |
|---|---|---|
| `encounter.beat_skipped` | `reason` ∈ {`neutral_actor`, `encounter_resolved`, `withdrawn_actor`, `dice_replay_turn`, `unknown_beat_id`}, `actor`, `actor_side`, `beat_id` | A beat selection is dropped instead of applied. Promotes existing `logger.info` at `narration_apply.py:289-298` into a span. |
| `encounter.invalid_side` | `actor_name`, `declared_side`, `valid_set` | Narrator declared a side outside the closed enum. Span fires *before* the `ValueError`. |
| `encounter.invalid_outcome_tier` | `beat_id`, `actor`, `declared_tier`, `valid_set` | Narrator declared an outcome tier outside `RollOutcome`. Same fail-loud semantics. |
| `encounter.metric_advance` | `side`, `delta_kind` (`own`/`cross`), `delta`, `before`, `after` | Once per side that changed inside `_apply_beat`. |
| `encounter.tag_created` | `tag_text`, `created_by`, `target` (actor name or `null` for scene), `leverage`, `fleeting`, `created_via` (`angle_beat` / `extras`) | When `_apply_beat` adds a tag to `enc.tags`. |
| `encounter.tag_backfire` | `tag_text`, `created_by`, `target`, `triggering_beat` | An `angle` beat's CritFail places the tag on the opposing side. |
| `encounter.status_added` | `actor`, `text`, `severity`, `source` (`narrator_extraction` / `engine` / `player_input`) | When a status is added to an actor's list during a turn. |
| `encounter.yield_received` | `player_id`, `actor_name`, `prior_metric_state`, `statuses_taken_this_encounter` | When a YIELD message is dispatched. |
| `encounter.yield_resolved` | `outcome=yielded`, `yielded_actors`, `edge_refreshed` | When yield causes encounter resolution (all player-side actors withdrawn). |
| `encounter.resolution_signal_emitted` | `outcome`, `final_player_metric`, `final_opponent_metric`, plus yield-specific extras when applicable | When `pending_resolution_signal` is set. |
| `encounter.resolution_signal_consumed` | Same as above | When the next narrator turn injects the `[ENCOUNTER RESOLVED]` zone. |

### Watcher publish parity

Every span above is paired with a `_watcher_publish` call carrying the same attributes under a `state_transition` event with `field="encounter"` and an `op` matching the span's local name (e.g., `op="beat_applied"`, `op="metric_advance"`, `op="resolution_signal_emitted"`). This is the existing pattern at `narration_apply.py:506-518` and elsewhere — the spec just extends it to every new decision point so the live GM panel receives the same view as the post-hoc replay.

### Persistence: new event kinds

The save's `events` table (`sidequest/game/persistence`) accepts arbitrary `kind` strings. The watcher publish handler is extended so `state_transition` events whose `field` is `"encounter"` are written to `events` as typed rows alongside `NARRATION`:

| `events.kind` | Source span | Payload contents |
|---|---|---|
| `ENCOUNTER_STARTED` | `encounter.confrontation_initiated` | encounter type, both metric thresholds, actor list with side, turn |
| `ENCOUNTER_BEAT_APPLIED` | `encounter.beat_applied` | actor, actor_side, beat_id, beat_kind, outcome_tier, deltas, turn |
| `ENCOUNTER_METRIC_ADVANCE` | `encounter.metric_advance` | side, delta_kind, delta, before, after, turn |
| `ENCOUNTER_BEAT_SKIPPED` | `encounter.beat_skipped` | reason, actor, beat_id, turn |
| `ENCOUNTER_TAG_CREATED` | `encounter.tag_created` (and `tag_backfire`) | tag_text, created_by, target, leverage, fleeting, created_via, turn |
| `ENCOUNTER_STATUS_ADDED` | `encounter.status_added` | actor, text, severity, source, turn |
| `ENCOUNTER_YIELD` | `encounter.yield_received` and `yield_resolved` (distinguished by `op`) | actor, statuses_taken, edge_refreshed, turn |
| `ENCOUNTER_RESOLVED` | `encounter.resolved` | outcome, final metrics, triggering_side, beat count |
| `ENCOUNTER_RESOLUTION_SIGNAL` | both `signal_emitted` and `signal_consumed` (distinguished by an `op` field in the payload) | outcome, final metrics, turn |

Per-player projection (`projection_cache`) inherits the existing `visible_to: "all"` policy for combat events — the entire encounter timeline is shared world state in v1, matching how `NARRATION` already handles the `_visibility` field. (Per-player asymmetric encounter views are a separate concern under ADR-028.)

### GM panel verification

The GM panel already renders rows from the `events` table. Adding new `kind` values means the panel handler grows cases for each new kind to render an encounter timeline: a side-by-side dial view of `player_metric` and `opponent_metric` over the encounter's beats, with each `ENCOUNTER_BEAT_APPLIED` row labeling which dial moved and which actor moved it, terminating at the `ENCOUNTER_RESOLVED` row. **No fix in this spec is considered complete until the panel can render this view for the regression save replay.** That is the lie-detector check — if the dial says player_victory and the prose says KO, the panel must show the row-by-row evidence.

If the existing panel rendering pipeline doesn't yet read non-`NARRATION` rows, that wiring is part of Story 1 — wire-it-up, not reinvent. Existing handlers should be extended; no parallel pipeline is created.

## Testing

**Unit (`sidequest-server/tests/server/test_narration_apply.py` + `tests/server/dispatch/test_dice.py` + `tests/server/test_beat_kinds.py`):**

- *Side routing.* `_apply_beat` with `actor.side="player"` advances `player_metric`; `"opponent"` mirrors; `"neutral"` advances neither and emits a `beat_skipped` event.
- *Withdrawn actor.* `_apply_beat` with `actor.withdrawn=True` is a no-op + `beat_skipped` event.
- *Per-kind defaults.* For each kind (`strike`, `brace`, `push`, `angle`), a parametrized test runs each of the five tiers with a beat that declares only `kind` and `base`, asserting the resulting deltas + tag/resolution extras match the default tables.
- *Per-tier override.* Beat with explicit `deltas.crit_fail.own = -2` overrides the kind default (`shield_bash` regression).
- *Tie tier.* Dice resolver returning `total == difficulty` produces `RollOutcome.Tie`; `_apply_beat` reads the Tie row.
- *CritSuccess by margin.* Dice resolver with `total >= difficulty + 3` (no nat-20) returns `RollOutcome.CritSuccess`; existing nat-20 path also still returns `CritSuccess`.
- *Tag creation on angle Success.* `enc.tags` contains a non-fleeting tag with `leverage=1` and the beat's `target_tag` text.
- *Tag creation on angle CritSuccess.* Same with `leverage=2`.
- *Tag backfire on angle CritFail.* A tag is placed on the opposing side, fleeting, leverage 1.
- *Fleeting tag from strike CritSuccess.* `Opening` tag is appended to `enc.tags` with `fleeting=True`.
- *Resolution from push success.* `enc.resolved=True`, `outcome="resolution_beat:<id>"`.
- *Resolution thresholds.* `player_metric` crossing first → `"player_victory"`; `opponent_metric` first → `"opponent_victory"`. Tie-break is iteration order.
- *Status migration.* Loading a snapshot whose `statuses` is `["Bleeding"]` produces `[Status(text="Bleeding", severity=Scratch, absorbed_shifts=0, ...)]`.
- *Status addition from narrator extraction.* A `status_changes` payload from the narrator appends to the named actor's `statuses` list.
- *Invalid side on actor declaration.* Instantiation raises `ValueError`; `encounter.invalid_side` span fires before the raise.
- *Invalid outcome tier.* Narrator emits `outcome="Wibble"` on a beat selection; `ValueError` raised, `encounter.invalid_outcome_tier` span fires before the raise.
- *Yield handler.* Single-PC encounter receives YIELD; `enc.resolved=True`, `outcome="yielded"`, `pending_resolution_signal` populated, `EdgePool.current` increased by `1 + status_count`.
- *Multi-PC yield.* Two PCs in encounter, one yields. Encounter remains active. Second yields. Encounter resolves with `yielded_actors=[both]`.

**Integration (`tests/server/test_session_encounter.py`):**

- Full encounter from instantiation through 5 beats to threshold cross. Final snapshot has `resolved=True` and structured outcome.
- Next turn after resolution: assembled narrator prompt contains the literal string `[ENCOUNTER RESOLVED]`, does *not* contain the active-encounter zone, and `pending_resolution_signal` is cleared after consumption.
- Same scenario but narrator emits `beat_selections` on the post-resolution turn anyway: dropped with watcher event, encounter remains resolved, no double-application.

**Wiring:**

- One end-to-end test that goes through the live `SessionHandler` path with a stub Claude returning a scripted `NarrationTurnResult`. Assert `_apply_beat` is called for each selection, that `pending_resolution_signal` is read on the next turn, and that the prompt assembler short-circuits the active-encounter zone when `enc.resolved`.

**Telemetry (`tests/server/test_encounter_telemetry.py`):**

- For each new and extended span, a unit test asserts the span fires with the documented attributes. Use the existing in-memory span recorder pattern.
- For each new `events.kind`, an integration test asserts the watcher publish path writes a row to the events table with the documented payload shape.
- One end-to-end test loads a fresh save db, runs a 3-beat encounter, queries `SELECT kind, payload_json FROM events WHERE kind LIKE 'ENCOUNTER_%' ORDER BY seq`, and asserts the timeline contains: `ENCOUNTER_STARTED`, three `ENCOUNTER_BEAT_APPLIED` rows with correct `actor_side` values, the corresponding `ENCOUNTER_METRIC_ADVANCE` rows, and (if threshold crossed) `ENCOUNTER_RESOLVED` with structured outcome.
- An invalid-side test asserts `encounter.invalid_side` span fires *before* `ValueError` propagates, so the panel observation is preserved through the failure.

**Regression playtest:**

- Replay the `2026-04-25-dungeon_survivor` save's 5 beats against the new engine using the new `caverns_and_claudes` pack. Assert `outcome == "opponent_victory"`. The current save's narration becomes consistent with the dial.
- After the replay, query the events table for the encounter timeline and assert the GM panel can render the beat-by-beat view: every beat attributed to its actor, every dial movement attributed to its side, terminating at the structured outcome. This is the lie-detector check — without it, the fix is unverifiable and the spec is not done.

## Story breakdown

One epic, five stories. The first three are v1 and must ship together (the engine schema break would orphan content otherwise). Stories 4–5 are the v2 mechanics that activate the data models v1 ships.

### v1 stories (ship together)

1. **Engine core + schema.**
   - `EncounterMetric` / `StructuredEncounter` reshape, `EncounterActor.side` + `withdrawn`, `EncounterTag`, `Status` + `StatusSeverity`, `BeatSelection.outcome`.
   - `RollOutcome.Tie` added; `CritSuccess` margin clause added in `resolve_dice_with_faces`.
   - Beat `kind` parsing, per-kind default tables (`strike` / `brace` / `push` / `angle`), per-tier `deltas` overrides.
   - `_apply_beat` rewrite (tier-aware, side-aware, tag-aware), `_check_resolution` with structured `outcome`, `_advance_phase` unchanged.
   - Pack loader: parse new schema; bare-string `statuses` migrated forward; reject the old single-`metric` and the old per-success-only `metric_delta` shapes with clear errors.
   - `caverns_and_claudes` `rules.yaml` migrated as the canary.
   - Deletions: `MetricDirection`, legacy `apply_encounter_updates`, `hostile_keywords` block, `failure_metric_delta` / `failure_opponent_metric_delta` legacy fields once the migration is done.
   - Tests: unit (per-kind tables, per-tier overrides, tag creation, status migration, tier resolution).

2. **Narrator awareness + telemetry + persistence + GM panel.**
   - Narrator output-schema additions: `side` per NPC, `outcome` per beat selection, `status_changes` array.
   - `pending_resolution_signal` slot on `_SessionData`; `[ENCOUNTER RESOLVED]` prompt zone (with `outcome=yielded` variant); active-encounter zone enriched with tags + statuses; short-circuit on `enc.resolved`.
   - Drop-with-telemetry for post-resolution beats and withdrawn actors.
   - Full span inventory wired (existing extended + new), with `_watcher_publish` parity at every decision point.
   - Watcher → `events`-table persistence for all `ENCOUNTER_*` kinds (extending existing publish path; no parallel pipeline).
   - GM panel handler extended to render the timeline: dial-pair view, beat rows with kind + tier + actor + side, tag-creation rows, status-add rows, yield rows, terminating in `ENCOUNTER_RESOLVED`.
   - Tests: integration + telemetry + regression playtest against `dungeon_survivor` with the lie-detector panel render assertion.

3. **Yield action + content migration.**
   - `MessageType.YIELD` wire payload; UI button + `/yield` command in client.
   - Server dispatch handler per the Yield section above.
   - `EdgePool.recovery_triggers` gains `OnYield`; refund computation.
   - All shipping packs' `rules.yaml` migrated to the new schema (kinds, tiers, tags). Per-pack tuning pass with content notes.
   - Pack-load smoke test for each: instantiate every confrontation, no schema errors.
   - Tests: yield handler unit + multi-PC integration; per-pack load tests.

### v2 stories (unlock v1 data models)

4. **Tag leverage spending.**
   - Beat schema gains `consumes_leverage_from: <tag_text>` (optional). When set, `_apply_beat` increments the resolved tier by one step (Tie → Success, Success → CritSuccess) for that beat, and decrements the named tag's `leverage`. Fleeting tags vanish at `leverage=0`; persistent tags remain at `leverage=0` as scene context.
   - Narrator schema extension: `consumes_leverage` per beat selection.
   - Telemetry: `encounter.leverage_consumed` span + `ENCOUNTER_LEVERAGE_CONSUMED` event row.
   - Tests: leverage upgrades tier, fleeting tag removed when consumed, narrator-declared consume validated against active tags.

5. **Status absorption.**
   - When `_apply_beat` would advance an actor's `own.current` past their side's threshold, the engine pauses with a "take a status" prompt.
   - Player-side: PC receives an interactive choice (severity tier; up to severity's absorption budget against the would-be cross). NPC-side: narrator declares the status take in the same turn's `status_changes`.
   - Status's `absorbed_shifts` is set; the dial advance is reduced by that amount; encounter continues if absorption keeps the dial under threshold.
   - `Scratch=2`, `Wound=4`, `Scar=6` absorption budgets.
   - Recovery: `Scratch` clears at scene end (existing resolution hook); `Wound` and `Scar` recovery hooks fire on per-pack triggers.
   - Telemetry: `encounter.status_absorbed` span + `ENCOUNTER_STATUS_ABSORBED` event row.
   - Tests: absorption blocks the cross, partial absorption (severity insufficient), Scratch clears at resolution, Wound persists, regression against `dungeon_survivor` (Sam takes "Cracked Temple" Wound, opponent_metric stays under threshold, encounter continues).

## Out of scope

- **Mid-encounter side mutation.** Charm, turncoat, ally betrayal — switching `actor.side` after instantiation. The data model supports it (side is a real field on a stored actor); prompt and engine logic don't activate it. Future epic.
- **Three-way encounters.** Party + city guard + bandits as three distinct sides. v1 keeps two sides; neutrals are prose-only actors.
- **Party-size threshold scaling.** A multi-PC playgroup hits `opponent_metric` faster than solo. v1 leaves per-pack thresholds fixed; content authors tune. Engine adjustment lands later if playtest demands it.
- **HP / damage tracking.** Explicitly out of scope. Statuses (with v2 absorption) are the actor-level cost mechanism; momentum dials are the encounter-level cost mechanism. There is no number that ticks down a hit-point reserve, ever.
- **Compelled actions.** A GM (or another player) forcing an actor to act per a status or tag. Big design surface; separate epic.
- **Spatial zones in encounters.** Movement, ranges, terrain. Genre-specific, separate epic.
- **NPC yielding.** Data model supports it; v1 does not implement the narrator-emit path. Folded into a future v2+ story alongside compels.

### Anchored explicitly to clarify scope

These are *in* scope for this epic, surfaced here to disambiguate from the "out" list:

- **Tag creation, display, and persistence** (v1): `angle` beats and beat extras add tags; tags appear in narrator zones, GM panel, and saves.
- **Tag leverage spending** (v2 — story 4): beats consume leverage from existing tags for a tier upgrade.
- **Status declaration, severity, and recovery hooks** (v1): structured shape, narrator-declared, scene-end clearing for Scratches.
- **Status absorption at threshold** (v2 — story 5): the take-a-wound mechanic. The marquee v2 deliverable.
- **Yield as a structured player exit** (v1 — story 3): full wire, dispatch, edge refund, narrator zone variant.
