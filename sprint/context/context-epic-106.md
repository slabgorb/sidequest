# Epic 106 Context — WWN combat hardening for beneath_sunden

## Overview

Make L1 `caverns_and_claudes/beneath_sunden` (WWN ruleset, ADR-117) a **fair,
WWN-faithful, and truthful** combat ramp. The core combat loop is already healthy and
verified (the #432 weapon-damage fix made dungeon combat winnable; Strike ablates HP,
opponent reprisal ATTACK/DAMAGE telemetry splits cleanly, the beat-impact chip reads the
HP channel, and lethality/death resolution fires correctly). What remains are the
*peripheral* defects that make the first dungeon a meat-grinder, leak native mechanics
into a WWN world, and let the narrator contradict the engine.

Source of record: the 2026-06-13 single-player combat playtest of beneath_sunden
(`~/Projects/sq-playtest-pingpong.md`), OTEL + save-forensics confirmed. Sibling epic:
**105** (beneath_sunden procedural-deep reachability). Companion epic carved from the
same run: **107** (dungeon scene advance + Monster Manual).

This epic serves the **primary audience** (CLAUDE.md): a survivable, legible L1 dungeon
for Keith's playgroup, and mechanically-honest resolution that mechanics-first players
(Sebastien/Jade) can trust — every fix carries OTEL proof per the project's
lie-detector principle.

## Background

Three threads, all surfaced in the 2026-06-13 run (1-of-5 "Marx brothers" Warriors
survived):

1. **Easy-ramp survivability levers.**
   - **Armor never equipped (106-1):** every Warrior fights at unarmored AC 10 — Leather
     Armor rolls into inventory `equipped:false` and `armor_class` is never recomputed, so
     opponent reprisals roll vs AC 10 (~65% hit) instead of the WWN leather value (~AC 13,
     ~45% hit). The single biggest lethality driver. Weapons *do* auto-equip, so the gap is
     armor-specific.
   - **Unconditional per-beat reprisal (106-2):** the native ADR-033 counter-attack is
     stapled to *every* player beat — even a defensive Brace ate a full killing reprisal.
     A defensive choice mitigates nothing. DESIGN-BEARING (see Technical Architecture).

2. **WWN ruleset-bleed** — native mechanics running ungated inside a WWN-bound world:
   - **Edge/tag system (106-3a):** the confrontation "edge" dial, "Counter Stance" fleeting
     tag, and "to their edge" chip surface in the WWN chase. Keith ruling: convert the
     tag-grant into a **strong (~-3) next-round opponent penalty** in WWN terms; kill the
     edge surface.
   - **Native XP (106-3b):** native per-tick advancement (ADR-021 four-track) ticks inside
     WWN — a Warrior hit 135 XP at L1. WWN uses small-integer expedition/goal XP. (Note: the
     Architect pass corrected the "10 XP chargen seed" theory — it's the calm-branch per-turn
     tick firing on turn 0, not a literal seed; `builder.py` sets xp=0.)

3. **Narration truth** — convincing-narration-vs-mechanics lies:
   - **Dead consumables (106-4):** a heal potion is consumed and a heal is narrated, but HP
     does not change — the effect half of the consumable pipeline is unwired. Bundled with
     Keith's priority ask: beat generation never scans inventory, so consumables can't be
     used mid-confrontation at all (a Zork-Problem/Agency violation).
   - **Death-state incoherence (106-5):** the down/death path emits TWO contradictory
     statuses (terminal "dead" + non-terminal "dies in 6 rounds") with mis-stamped
     provenance (`created_turn:0`). Deterministic 2/2.
   - **Knockdown over-claim (106-6):** narrator negates a successful player hit ("mace swings
     wide" on a Strike Success) and depicts the PC going down at 1/10 with a live beat menu.
     Symmetric player-down cousin of the fixed kill-overclaim anchor (fbff7135).

Standing ruling (`.pennyfarthing/sidecars/gm-decisions.md`, 2026-06-13): **WWN-bound
mechanical values come from the WWN SRD** — never invent numbers (armor AC, heal magnitude,
XP scale all source from the SRD).

## Technical Architecture

**Shared fix locus — the WWN `RulesetModule` (ADR-117).** The ruleset-bleed cluster (106-2,
106-3) is one architectural problem: native mechanics not gated/overridden by the WWN
module in `sidequest-server/sidequest/game/ruleset/` (`base.py` + `wwn.py`). WWN currently
inherits native `beat_kinds.apply_beat` verbatim. The same seam that gates the edge/tag and
XP bleeds is where the reprisal model decision lands.

Per-story seams (confirmed by the Architect context pass — see the per-story files for
file:line detail):

- **106-1** — chargen kit-roll equips weapons but hardcodes `equipped:false` for armor
  (`builder.py`); `core.armor_class` stays at the unarmored default (`creature_core.py`) that
  the reprisal reads (`dice.py`); the content leather entry has no `armor_class` field to
  derive from (`caverns_and_claudes/inventory.yaml`). Two-sided fix (content AC + engine
  equip/derive).
- **106-2** — DESIGN-BEARING. The WWN-faithful initiative path is **~80% already built**
  (`wn_round.py`), but the per-beat reprisal resolver (`dice.py`) is blind to the player's
  beat on both paths, and the `brace` mitigation primitive (`beat_kinds.py`) is unused.
  **Keith owes the ruling:** Option A (route WWN through the existing initiative round + a
  full-defend action — faithful, larger) vs Option B (keep the beat model but make
  defensive beats reduce opponent to-hit/damage or grant a save — smaller, surgical). Dev
  is blocked until this is decided.
- **106-3** — `beat_kinds.py` edge/tag effects (`:171/:236/:250`) survive dial-suppression
  under hp_depletion; native XP `award_turn_xp`/`apply_level_ups` (`encounter_lifecycle.py`)
  called ruleset-blind in `websocket_session_handler.py`. Both gated through the WWN module.
- **106-4** — consume is wired (`narration_apply.py`) but no effect-application hook; the
  `state_patch.hp` span + `HpPool.apply_delta` positive path already exist to reuse;
  beat-scan extends `beats_available_for` (`beat_filter.py`, no inventory param today)
  threaded through `narrator.py` + `confrontation.py`. Heal magnitude from WWN SRD; potion
  needs a heal-amount content field. **Open content decision (Keith):** guaranteed heal slot
  vs intended random scarcity (currently ~30% of Warriors start with zero potions).
- **106-5** — two un-reconciled death sites: `post_resolution_lethality.py` emits the
  correctly-stamped terminal status; WWN's `resolve_downed` (`wwn.py`) appends the unstamped
  "Mortal Injury" status (defaults from `status.py`). Fix = one coherent state + real
  provenance. **Open question:** terminal-dead vs a true (solo-unactionable) WWN dying window.
- **106-6** — mirror the fbff7135 anchor pattern: a new `hp_depletion`-gated MECHANICAL
  TRUTH directive in `dice.py` `_emit_player_beat_resolution_close` affirming the player's
  hit landed and the PC stays up above 0 HP; consumed silently, OTEL-proved.

**Cross-cutting guardrails:** No Silent Fallbacks; every subsystem decision emits an OTEL
span (the GM-panel lie detector); WWN SRD is the sole authority for WWN-bound numbers;
crunch lives in the genre/ruleset, flavor in the world (ADR-140).

## Cross-Epic Dependencies

- **Epic 105** (beneath_sunden procedural-deep reachability) — same dungeon neighborhood;
  105 owns the surface→deep crossing + graph traversal, this epic owns combat mechanics.
- **Epic 107** (dungeon scene advance + Monster Manual) — carved from the same playtest run;
  107-1 (per-room scene advance) and 107-2 (authored bestiary) cover the
  dungeon-infrastructure findings excluded from this epic.

## Planning Documents

- Source findings: `~/Projects/sq-playtest-pingpong.md` (2026-06-13 combat run).
- Standing ruling: `.pennyfarthing/sidecars/gm-decisions.md` (WWN SRD is the authority).
- Per-story context: `sprint/context/context-story-106-{1..6}.md`.
- Key ADRs: 117 (RulesetModule), 033 (beat engine), 116 (single-opponent-seater),
  114 (ablative HP), 123 (LethalityArbiter), 021 (progression).
