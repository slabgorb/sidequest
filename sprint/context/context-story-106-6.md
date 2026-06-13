---
parent: 106
---

# Story 106-6 Context

## Title
Narration-truth guardrail — narrator over-claims a player knockdown and negates a
successful hit at low HP (narrates a miss on a Strike Success that removed opponent HP,
and depicts the PC going down while at 1/10 with a live beat menu and no
ENCOUNTER_RESOLVED); symmetric player-down cousin of the fixed
kill-overclaim-on-failed-strike anchor (fbff7135), on a successful player beat.

## Metadata
- **Story ID:** 106-6
- **Type:** bug
- **Points:** 3
- **Priority:** p1
- **Workflow:** tdd
- **Repo:** server
- **Epic:** 106 — WWN combat hardening for beneath_sunden (fair ramp, ruleset-bleed remediation, narration truth)

## Problem

Found on the develop build (`15df814d`) post-restart, 2026-06-13, in
caverns_and_claudes/beneath_sunden (WWN ruleset, ADR-117), session
`2026-06-13-beneath_sunden-0805bbe7`, solo Warrior **Gummo** (they/them), Dungeon
Combat vs "Nearest shape" (sq-playtest-pingpong.md lines 69–83).

**Engine ground truth (OTEL + panel):**
- Player committed **Strike**. OTEL: `ENCOUNTER_BEAT_APPLIED beat_id=strike
  outcome_tier=Success opponent_hp_removed=2` → a real **HIT**, opponent 10→8.
  Beat-impact chip read **"▲ −2 to their HP"** (correct).
- Opponent reprisal `d20=17+2=19 hit`, `1d8=3` → Gummo 4→**1**.
- Panel after the turn: You **1/10**, Them **8/10**, **beat menu still live**
  (Brace/Break Contact/Strike/Committed Blow) → combat **ongoing**, Gummo **NOT down**,
  **no `ENCOUNTER_RESOLVED`**.

**Narration rendered to the player (NarrativeView) — two lies in one paragraph:**
> "The **mace swings wide** — the shape reads it before it arrives, slipping inside
> your guard… The blow catches you across the temple and the shaft tilts sideways.
> **Your knees are on stone before the decision to fall was made. The shape stands
> over you,** and the torchlight is not enough to see its face."

1. **Hit-underclaim:** narration says the player's mace **"swings wide"** (a miss),
   but the beat resolved **Success / −2 to opponent HP** (a hit). The narrator negated
   the player's successful attack.
2. **Knockdown over-claim:** narration depicts the player **going down / finished**
   ("your knees are on stone… the shape stands over you") while the PC is at **1/10 HP
   with a live beat menu** and no `ENCOUNTER_RESOLVED`.

This is the same class as the **fixed** kill-overclaim-on-failed-strike anchor
(`fbff7135`), but on the **player-down** side and on a **successful** player beat.

**RETRACTED — do NOT pursue weapon-name drift** (line 81): the DRIVER initially flagged
"the mace" as wrong, then confirmed Gummo's kit rolled an **Iron Mace** (`equipped:
True`) — the narrator named the weapon correctly. Equipped weapons are correct across
the run. No weapon-name bug; do not include one in scope.

## Root-cause investigation (cite file:line)

The per-beat resolution close is
`_emit_player_beat_resolution_close`
(`sidequest-server/sidequest/server/dispatch/dice.py:1429`), shared by the legacy
in-dispatch flow (`dice.py:780`) and the WN round walk
(`wn_round.py:376`, passing `win_condition=cdef.win_condition`). It is the seam where
the fixed `fbff7135` failed-strike anchor lives, so it is the natural seam for this
symmetric fix. It has exactly three branches:

1. `if encounter_resolved:` (`dice.py:1460`) — stamps the resolution signal + a
   MECHANICAL TRUTH "confrontation has RESOLVED" directive (with a Shock-rider for the
   kill-on-missed-swing case).
2. `elif strike_hp_removed + shock_hp_removed > 0:` (`dice.py:1512`) — the **damaging-hit
   anchor**: anchors the **opponent's** resulting HP + "STILL STANDING; the fight
   continues. Narrate a wound, not a kill." (`dice.py:1527`).
3. `elif win_condition == "hp_depletion":` (`dice.py:1535`) — the **fixed `fbff7135`
   failed-strike anchor**: on a 0-damage non-resolving beat, anchors the **opponent**
   UNHARMED + "STILL STANDING; the fight continues. Narrate the failed attack — do NOT
   describe a hit… death, collapse, or incapacitation." (`dice.py:1556`).

**The bug case (Strike Success, opp 10→8, `strike_hp_removed=2`) takes branch 2.** That
branch anchors only the **target's** survival ("Narrate a wound, not a kill") — it says
**nothing from the player's POV**, so the narrator is free to render the player's blow as
"swings wide." There is **no directive that affirms the player's beat LANDED** consistent
with the −N chip / opponent HP drop. That is the **hit-underclaim** half.

The **reprisal** side is in `_resolve_opponent_reprisal` (`dice.py:1566`). On a hit it
applies HP and anchors the player's resulting HP + "Narrate the hit landing"
(`dice.py:1880`); on a clean/Shock miss it anchors the unchanged/chipped HP
(`dice.py:1749`, `dice.py:1777`). The player-down resolution lives in
`_close_reprisal_depletion` (`dice.py:1935`), whose "taken out of the fight" directive
(`dice.py:2018`) only fires **when `check_hp_depletion` returns non-None** — i.e. the PC
actually hit 0. In the bug case the PC is at **1/10**, so depletion is None and **nothing
anchors "the player is still UP, above 0 HP, not down — keep the fight live."** That is
the **knockdown over-claim** half: the reprisal-hit directive anchors HP=1/10 and "the
hit landed" but never says the PC remains standing, so the narrator escalated a survivable
hit into a knockdown.

So the gap is **symmetric to `fbff7135`** but on the player-survival side: just as a
failed strike got no directive and the narrator invented a kill, here a **successful
player beat + a non-fatal reprisal** gets no player-POV survival directive and the
narrator invents (a) a missed swing and (b) a knockdown.

**Fix shape (preferred — mirror `fbff7135`, NOT a guard).** Add MECHANICAL TRUTH
directive(s), gated to `win_condition == "hp_depletion"`, that anchor the player's own
state on a non-resolving turn:
- when the player's beat **landed** (`strike_hp_removed + shock_hp_removed > 0`), affirm
  the player's blow **connected** for N damage (consistent with the −N chip / opponent HP
  drop) — do NOT narrate it as a miss; and
- when the player **took the reprisal but stayed >0 HP**, affirm the PC is at
  `current/max` HP and **STILL UP / still in the fight, NOT downed or collapsed** — do
  NOT narrate a knockdown, the PC on the ground, or the opponent standing over them.

`sidequest/agents/fabricated_roll_guard.py` (`detect_fabricated_roll`, the recent
narrator-truth tripwire) is the wrong tool here: it pattern-matches **invented numeric
mechanics** ("roll of N", "vs AC", "d20"); it cannot detect a **semantic** contradiction
("swings wide" on a Success, "knees on stone" while alive). The directive-anchor pattern
is the established, refactor-stable fix and keeps this consistent with branches 2 and 3
and the reprisal anchors.

## Business Context

This is the **OTEL lie-detector class** (CLAUDE.md, sidequest-server/CLAUDE.md OTEL
Observability Principle): convincing narration with **zero or contradictory mechanical
backing**. The narrator is "excellent at winging it" — here it wrote a vivid, well-formed
defeat paragraph that contradicts the engine on two axes at once (a Success narrated as a
miss, a 1/10-HP survivor narrated as downed). The GM panel / OTEL is the only thing that
catches it, and the panel says the fight is live.

The harm lands hardest on the **mechanics-first players the epic is for**, Sebastien and
Jade: they read the panel **and** the prose. "Your knees are on stone, the shape stands
over you" reads as **death/dying**; then the engine asks Gummo to pick a beat from a live
menu. That is exactly the dissonance that drove the SWN-crunch / ablative-HP work
(CLAUDE.md) — when the crunch finally fires, the narration must not lie about whether the
player's hit landed or whether the player is still standing. For Keith-as-player, a
narrator that negates a successful swing and fakes a knockdown is precisely the
"convincing but improvising" failure SideQuest exists to defeat.

This is the **narration-truth thread** of Epic 106 (alongside the fair-ramp and
ruleset-bleed threads). It is the player-down/successful-beat symmetric completion of the
already-shipped failed-strike anchor (`fbff7135`); shipping it closes the last known
mechanically-contradictory player-facing prose in beneath_sunden combat from this
playtest.

## Technical Guardrails

- **Mirror the `fbff7135` anchor pattern, do not invent a new mechanism.** The fix is one
  (or a small set of) `MECHANICAL TRUTH (weave into the narration): …` directive(s)
  appended to `snapshot.next_turn_directives` from
  `_emit_player_beat_resolution_close` (`dice.py:1429`) and/or
  `_close_reprisal_depletion` (`dice.py:1935`), structurally identical to the existing
  STILL STANDING / failed-strike / reprisal-hit anchors. Prefer a **directive anchor**
  over extending `fabricated_roll_guard.py` (the guard is a numeric-tell detector and
  cannot see semantic contradictions).
- **Gate to `win_condition == "hp_depletion"`** exactly like the `fbff7135` branch
  (`dice.py:1535`). HP-framed "your blow landed for N / you are at C/M HP and still up"
  wording must **never reach a dial confrontation** (negotiation, chase, poker), where a
  0-strike-damage beat is the norm and a non-fatal "reprisal" is meaningless. `wn_round.py`
  already passes `win_condition=cdef.win_condition` (`wn_round.py:386`); the legacy
  `dice.py:780` call site must pass it too if it doesn't already — verify.
- **Consume the directive silently.** `next_turn_directives` is narrator scaffolding, not
  prose — the existing anchors all say "weave into the narration" and produce no leaked
  text. The [VERIFY] entry (line 96) confirms "no directive leak in any player-facing
  prose" is the current healthy state; the new directive must keep that property (no "C/M
  HP", no "STILL UP", no roll/AC numbers surfacing).
- **Anchor only what the engine knows is true.** Use the real applied values:
  `strike_hp_removed + shock_hp_removed` for the player's landed damage, and
  `player_core.hp.current / player_core.hp.max` for survival — never re-derive or invent.
  Skip-or-soften only on the genuinely ambiguous edges (e.g. a 0-HP multi-combatant
  partial-down, the same caveat branches 2 and 3 already honor at `dice.py:1526` /
  `dice.py:1552`).
- **Both call sites.** The close is shared by the legacy in-dispatch flow (`dice.py:780`)
  and the WN round walk (`wn_round.py:376`) "so the two closes cannot drift"
  (`dice.py:1446`). The fix must live in the shared function so both seams get it.
- **OTEL.** Per the OTEL Observability Principle, the player-survival/hit-landed anchor
  decision should be observable (a span or watcher row) so the GM panel can prove the
  guardrail engaged — the same way branches 2/3 and the reprisal anchors are
  panel-visible. Do not add a silent directive with no telemetry.
- **No silent fallbacks / no stubs** (CLAUDE.md): if the anchor target or player core is
  unresolvable, log loudly and skip (matching the existing `_anchor_core is None` guards),
  never paper over it.

## Scope Boundaries

**In scope:**
- The **player-down / hit-underclaim anchor**: on a Strike Success (or any landed player
  beat) that does NOT resolve the fight under `hp_depletion`, a MECHANICAL TRUTH directive
  that (a) affirms the player's blow **connected** consistent with the −N chip / opponent
  HP drop (kills "swings wide"), and (b) when the player took a non-fatal reprisal, affirms
  the PC is at `C/M` HP and **STILL UP / not downed** (kills the knockdown over-claim).
- Wiring into the shared `_emit_player_beat_resolution_close` / `_close_reprisal_depletion`
  seam so both the legacy and WN-round paths get it, gated to `hp_depletion`.
- OTEL proof the guardrail fired.
- Tests: the failing-first behavior test on the beneath_sunden repro shape, plus a wiring
  test (OTEL span assertion or fixture-driven behavior test per sidequest-server/CLAUDE.md
  "Every Test Suite Needs a Wiring Test" / "No Source-Text Wiring Tests").

**Out of scope:**
- **Weapon-name drift** — RETRACTED by the DRIVER (line 81); the narrator named the Iron
  Mace correctly. Do not touch weapon naming.
- The **low-priority narration register breaks** (pronoun/HP-term wording) — those stay in
  the ping-pong loop, not this story.
- The **reprisal model itself** (unconditional per-beat counter-attack, defensive-beat
  mitigation) → story 106-2.
- **WWN ruleset-bleed** (edge/tag, XP scale) → story 106-3; **starting-armor equip** →
  106-1; **consumables** → 106-4; **death-state coherence** (the dual contradictory status
  on a real down) → 106-5. This story is only the **non-resolving, PC-stays-up** narration
  truth; it must not change the resolution/down path 106-5 owns.
- Extending `fabricated_roll_guard.py` to detect semantic contradictions (a larger,
  separate effort; the directive anchor is the in-scope fix).

## AC Context

The DRIVER's verification recipe (line 83): in beneath_sunden combat, land a **Strike
Success** on a turn the player **also takes heavy damage but stays >0 HP**, then check the
prose.

1. **Hit landed, not a miss.** On a player beat that resolved Success / removed opponent
   HP (the −N beat-impact chip fired), the narration **describes the player's blow
   connecting**, consistent with the opponent's HP drop — it does **NOT** say the attack
   "swings wide", misses, or otherwise negates the successful strike.
2. **Not downed while alive.** While the PC is at **HP > 0 with the beat menu live and no
   `ENCOUNTER_RESOLVED`**, the narration does **NOT** depict the PC as downed, collapsed,
   "knees on stone", finished, or the opponent "standing over" them. A heavy non-fatal hit
   is narrated as a wound the PC absorbs while staying in the fight.
3. **Gated to hp_depletion.** The HP-framed survival/hit-landed wording does not surface in
   a dial confrontation (chase/negotiation/poker) — the new directive only fires when
   `win_condition == "hp_depletion"`, matching the `fbff7135` branch.
4. **Silent consumption.** No directive scaffolding leaks into player-facing prose (no
   "C/M HP", no "STILL UP", no roll/AC numbers) — preserves the healthy "no directive leak"
   state confirmed in the [VERIFY] entry (line 96).
5. **OTEL proof + no regression.** A span/watcher row proves the player-survival/hit-landed
   anchor engaged on the non-resolving turn; the existing `fbff7135` failed-strike anchor,
   the damaging-hit STILL STANDING anchor, and the resolution/down path (the real
   `ENCOUNTER_RESOLVED` close when the PC does hit 0) are unchanged.

## Dependencies / Notes
- **Mirror reference:** the fixed `fbff7135` failed-strike anchor at `dice.py:1535–1563`,
  and its kin — the damaging-hit anchor `dice.py:1512–1534`, the reprisal-hit anchor
  `dice.py:1880`, the reprisal-miss anchors `dice.py:1749` / `dice.py:1777`.
- **Seams to edit:** `_emit_player_beat_resolution_close` (`dice.py:1429`) and/or
  `_close_reprisal_depletion` (`dice.py:1935`); both call sites `dice.py:780` and
  `wn_round.py:376`.
- **Not a guard change:** `sidequest/agents/fabricated_roll_guard.py` stays as-is.
- **Sibling stories** 106-1..106-5 own the ramp/bleed/consumable/death-state threads;
  keep this story strictly to non-resolving player-survival narration truth.
