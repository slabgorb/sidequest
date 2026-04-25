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

A fourth issue — `BEAT_APPLIED` watcher events not being persisted to the `events` table — is real but **out of scope** for this spec. The save's `events` rows are all `kind='NARRATION'`; the OTEL spans are emitted in the engine but never flow into the projection store. That is a watcher/storage problem and gets its own spec.

## Design summary

Replace the single bidirectional `metric` with **two ascending dials per encounter**: `player_metric` and `opponent_metric`, each with its own `threshold`. Each beat applies to the dial of the actor's *side*, where `side` is a structured field declared by the narrator (never inferred from role text). Beats may also carry `opponent_metric_delta` to model defensive/disruptive plays that set the other side back rather than advancing one's own. Outcome strings become a structured enum the narrator can switch on. After resolution, the next narrator turn receives a one-shot `[ENCOUNTER RESOLVED]` prompt zone with the structured outcome and final metrics, and is barred from emitting `beat_selections`.

**No HP.** Combat remains a narrative-trend mechanic; momentum is the only encounter-level dial.

**No string matching.** Side, role, beat id, confrontation type, outcome — all structured fields with closed enums or keyed lookups. Per SOUL.md "The Zork Problem," the narrator's natural-language ceiling stays open while the engine's contracts stay structured. The existing `hostile_keywords` substring-match block at `narration_apply.py:466-472` is deleted, not refactored.

## Architecture

### Schema changes (`pack rules.yaml`)

Each `confrontation` definition replaces its single `metric` with two:

```yaml
confrontations:
  - type: combat
    label: Dungeon Combat
    category: combat
    player_metric:
      name: momentum     # display name; engine routes by side, not name
      starting: 0
      threshold: 10
    opponent_metric:
      name: momentum
      starting: 0
      threshold: 10
    beats:
      - id: attack
        label: Attack
        metric_delta: 2              # applied to actor's own side
        stat_check: STR
        narrator_hint: …
      - id: defend
        label: Defend
        metric_delta: 0
        opponent_metric_delta: -1    # set back the other side
        stat_check: CON
        narrator_hint: …
      - id: shield_bash
        label: Shield Bash
        metric_delta: 4
        failure_metric_delta: -2     # was free-text "risk:"; now structured
        stat_check: STR
        narrator_hint: …
      - id: flee
        label: Flee
        metric_delta: 0
        resolution: true
        stat_check: DEX
```

Field semantics, *all measured from the actor's perspective*:

| field | meaning | default |
|---|---|---|
| `metric_delta` | applied to actor's own side on success | `0` |
| `failure_metric_delta` | applied to actor's own side on dice fail | `None` (no fail branch) |
| `opponent_metric_delta` | applied to the *other* side on success | `0` |
| `failure_opponent_metric_delta` | applied to the other side on dice fail | `None` |
| `resolution` | beat ends the encounter regardless of metrics | `false` |

### Engine changes (`sidequest-server`)

**`StructuredEncounter`** (`sidequest/game/encounter.py`):

- Replace `metric: EncounterMetric` with `player_metric: EncounterMetric` and `opponent_metric: EncounterMetric`. Each is the existing ascending shape (`name`, `current`, `starting`, `threshold`). Drop `MetricDirection` — both dials are ascending; bidirectional was the single-dial workaround.
- `EncounterActor` gains `side: Literal["player", "opponent", "neutral"]`, set at instantiation from the narrator's payload. Never mutated in v1.
- `outcome` becomes a structured value: one of `player_victory`, `opponent_victory`, `resolution_beat:<beat_id>`, or `None` while unresolved. Replaces the current `f"resolved at beat {n}"` string.

**`BeatSelection`** (`sidequest/agents/orchestrator.py:91-98`): unchanged shape — `actor` (name) and `beat_id`. Side is looked up via the named actor in the encounter; the narrator does not re-declare side per beat.

**`_apply_beat`** (`sidequest/server/narration_apply.py:273-385` and `sidequest/server/dispatch/dice.py:127-168`): replaced with a single helper that accepts the actor and routes both deltas:

```
def _apply_beat(enc, actor, beat, dice_failed):
    side = actor.side
    if side == "neutral":
        emit_watcher("beat_skipped", reason="neutral_actor")
        return
    own = enc.player_metric if side == "player" else enc.opponent_metric
    other = enc.opponent_metric if side == "player" else enc.player_metric

    own_delta = beat.failure_metric_delta if (dice_failed and beat.failure_metric_delta is not None) else beat.metric_delta
    other_delta = beat.failure_opponent_metric_delta if (dice_failed and beat.failure_opponent_metric_delta is not None) else beat.opponent_metric_delta

    own.current += own_delta
    other.current += other_delta
    enc.beat += 1
    _advance_phase(enc)

    return _check_resolution(enc, beat)
```

`_check_resolution` checks `player_metric.current >= player_metric.threshold` first, then `opponent_metric.current >= opponent_metric.threshold`, then `beat.resolution`. The first one to fire sets `enc.resolved = True` and `enc.outcome` to the matching enum value.

**Tie-break.** Beat application within a turn iterates `result.beat_selections` in order. ADR-036 sealed-letter turns guarantee player beats arrive before NPC beats in the assembled list. The first threshold crossed wins; later beats in the same turn are still applied to their dials (for telemetry truth) but do not change `outcome`.

**Side validation.** When the narrator's payload declares an actor whose `side` is missing or not in `{"player","opponent","neutral"}`, instantiation raises `ValueError`. CLAUDE.md no-silent-fallbacks applied to side routing — this is the contract that makes structured routing possible.

**Deletions:**

- `apply_encounter_updates` and its keyword-bucket actor classification at `narration_apply.py:403-602`. Already dead per the comment at `session_handler.py:2852`; same PR per the dead-code-removal rule.
- The `MetricDirection` enum and its `_DIRECTION_BY_NAME` map at `dispatch/encounter_lifecycle.py:26-30`.
- The `hostile_keywords` substring match at `narration_apply.py:466-472`.

### Narrator integration

**Side declaration.** The narrator output schema gains `side` on each `npcs_present` and `npcs_met` entry, and the `BeatSelection` schema continues to reference the actor by name (the engine reads side from the actor's stored value). The narrator prompt zone added at `agents/narrator.py:177-182` is extended with:

> Each NPC entry must include `"side"`: one of `"player"` (party allies), `"opponent"` (anyone the party is fighting), or `"neutral"` (bystanders, narrators, audience). This is structural — `role` remains free-form prose, `side` is a closed enum the engine routes on.

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

Per-pack edits: split single `metric` → `player_metric` + `opponent_metric`; convert `risk:` flavor for failure penalties into structured `failure_metric_delta`; re-tune `defend`-style beats to use `opponent_metric_delta` where the intent is "set them back" rather than "advance my win." Content authors decide the tuning; engine just routes the numbers.

## Testing

**Unit (`sidequest-server/tests/server/test_narration_apply.py` + `tests/server/dispatch/test_dice.py`):**

- `_apply_beat` with `actor.side="player"`: `player_metric` advances by `metric_delta`, `opponent_metric` unchanged.
- `_apply_beat` with `actor.side="opponent"`: mirror.
- `_apply_beat` with `actor.side="neutral"`: both dials unchanged, watcher event emitted.
- Beat with `opponent_metric_delta=-1` from a player actor: `opponent_metric` decreases.
- Beat with `failure_metric_delta` from an opponent actor on dice fail: opponent's own dial gets the failure value.
- Resolution check: `player_metric` crossing first → `outcome="player_victory"`; `opponent_metric` first → `"opponent_victory"`; resolution beat → `"resolution_beat:<id>"`.
- Tie-break: same-turn list with player and opponent beats both crossing — first in iteration order wins; both deltas still applied.
- Invalid side on actor: instantiation raises `ValueError`.

**Integration (`tests/server/test_session_encounter.py`):**

- Full encounter from instantiation through 5 beats to threshold cross. Final snapshot has `resolved=True` and structured outcome.
- Next turn after resolution: assembled narrator prompt contains the literal string `[ENCOUNTER RESOLVED]`, does *not* contain the active-encounter zone, and `pending_resolution_signal` is cleared after consumption.
- Same scenario but narrator emits `beat_selections` on the post-resolution turn anyway: dropped with watcher event, encounter remains resolved, no double-application.

**Wiring:**

- One end-to-end test that goes through the live `SessionHandler` path with a stub Claude returning a scripted `NarrationTurnResult`. Assert `_apply_beat` is called for each selection, that `pending_resolution_signal` is read on the next turn, and that the prompt assembler short-circuits the active-encounter zone when `enc.resolved`.

**Regression playtest:**

- Replay the `2026-04-25-dungeon_survivor` save's 5 beats against the new engine using the new `caverns_and_claudes` pack. Assert `outcome == "opponent_victory"`. The current save's narration becomes consistent with the dial.

## Story breakdown

One epic, three stories, sequential.

1. **Engine + schema.**
   - `EncounterMetric`/`StructuredEncounter` reshape, `EncounterActor.side`, `BeatSelection` actor lookup.
   - `_apply_beat` rewrite, structured outcomes, deletion of `MetricDirection` and the legacy `apply_encounter_updates` path and the `hostile_keywords` block.
   - Pack loader: parse `player_metric`/`opponent_metric`, `opponent_metric_delta`, `failure_opponent_metric_delta`, `side` on actor declarations; reject the old single-`metric` shape with a clear error.
   - `caverns_and_claudes` `rules.yaml` migrated as the canary content for unit + integration tests (other packs follow in story 3).
   - Tests: unit + integration + wiring per the test plan above.

2. **Narrator awareness.**
   - `pending_resolution_signal` slot on `_SessionData`.
   - `[ENCOUNTER RESOLVED]` prompt zone, active-encounter zone short-circuit on `enc.resolved`.
   - Drop-with-telemetry behavior for beat_selections emitted after resolution.
   - Narrator output-schema docs in `agents/narrator.py` extended to require `side` per NPC.
   - Tests: integration + regression playtest against the dungeon_survivor save.

3. **Content migration.**
   - All shipping packs' `rules.yaml` migrated. Per-pack tuning pass with content notes.
   - Pack-load smoke test for each: instantiate every confrontation, no schema errors.
   - No engine changes.

Stories 1 and 3 must land together (engine breaks old schema). Story 2 can land in the same release or one release later — story 1's engine works correctly without it; the narrator just keeps writing through resolution as it does today, which is exactly the bug story 2 fixes.

## Out of scope

- **OTEL persistence.** `BEAT_APPLIED` and `ENCOUNTER_RESOLVED` watcher events not landing in the `events` table is a real bug. Separate spec.
- **Mid-encounter side mutation.** Charm, turncoat, ally betrayal. v2 — data model supports it, prompt and engine logic don't.
- **Three-way encounters.** Party + city guard + bandits as three distinct sides. v1 keeps two sides and rolls neutrals into prose-only actors.
- **Party-size threshold scaling.** A multi-PC playgroup hits `opponent_metric` faster than solo. v1 leaves the per-pack threshold fixed; content authors tune. Engine adjustment lands later if playtest demands it.
- **HP / damage tracking inside the encounter dial.** Out of scope by explicit user direction. Character HP remains where it lives today (character state); momentum is the encounter trend.
