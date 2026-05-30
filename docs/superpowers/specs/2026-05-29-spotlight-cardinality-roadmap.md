# Spotlight Cardinality — Multiplayer Confrontation Participation Roadmap

**Date:** 2026-05-29
**Status:** umbrella note — tracks a three-spec decomposition
**Origin:** SOUL principle **The Guitar Solo** (added to `SOUL.md` + `sidequest-content/SOUL.md`, 2026-05-29). Brainstorm grew out of mis-scoped story **59-21** (which was actually about empty lobby sockets — unrelated; that should still close-as-decided).

## The problem

At a multiplayer table, a confrontation can spotlight a subset of players ("a guitar solo"). Solos are good — but *a song of nothing but solos isn't a song*. What do the **other** players do while one (or few) are in the confrontation?

## Ground truth established during the brainstorm

- The **submit-and-wait barrier is live, tested gameplay** (ADR-036; `session_room.py:722` `effective_barrier_count` = all PLAYING peers, minus crash-released). The narrator does not fire until **all** seated players submit. So non-participants are **not** frozen out of the turn loop — they are *required* to submit each round.
- **Multi-actor rounds already work for dial/HP confrontations.** `narration_apply.py:2895–2918` loops `beat_selections` and calls `apply_beat` **once per actor per round**. A 4-player firefight already applies all four beats. A SOUL gate (`_filter_inferred_pc_beats`) drops beats the narrator invents for a non-consenting PC.
- Confrontations split on **spotlight cardinality**, not genre or resolution_mode:

| Class | Examples | Engine support | Gap |
|---|---|---|---|
| **Ensemble** (one party vs opponents, shared dial) | firefight, Trial-by-Tribunal (tea_and_murder), ship_combat, crewed chase | ✅ multi-actor rounds work | *soft* — narrator must seat & honor all willing actors; idle-in-room players need a verb |
| **Duel** (two principals, 1v1) | dogfight (sealed_letter), Duel-of-Wits (tea_and_murder), standoff/pre_combat (spaghetti_western), 1:1 negotiation | ✅ works, strands table *by design* | concurrent thread for the rest — linked confrontation **or** parallel ADR-053 investigation — intercut + bounded short |
| **Free-for-all table** (N independent seats) | **poker** (spaghetti_western), **auction** (tea_and_murder) | ❌ **no model** — forced into a 2-side `player_metric` vs `opponent_metric` dial | needs a real N-seat resolution mode: per-seat parties, shared pot/stakes, betting/bidding order, private per-seat state |

## The three specs (do not drop)

### SPEC 1 — Ensemble weave *(pending)*
Make the narrator reliably **seat and honor** every willing actor in an ensemble confrontation, and give **room-present non-actors** a meaningful verb. Mostly narrator-contract + OTEL; no new resolution math (capability already exists, reliability does not). Smallest of the three.

### SPEC 2 — Duel concurrent-thread *(pending)*
During an *intended* 1v1 (dogfight, Duel of Wits, standoff), give the rest of the table a **concurrent thread** — a linked confrontation (e.g. the carrier's ship_combat / point-defense alongside the fighter duel) **or** a parallel non-confrontation action (ADR-053 investigation: while two sleuths trade barbs in the parlor, the others search the library). Narrated intercut; the solo is bounded short per *Cut the Dull Bits*. Medium.

### SPEC 3 — Free-for-all N-seat table model *(SPECCED — [design doc](2026-05-29-free-for-all-n-seat-table-design.md))*
A new resolution mode for genuine N-seat free-for-alls (poker, auction, and general: council vote, derby). Per-seat parties (no two-side dial), shared stakes (pot / high-bid), private per-seat state (your hand — uses ADR-104/105 perception filtering, generalizing the dogfight sealed-commit), and an in-hand action/betting order distinct from the cross-round barrier. **This is the only true *structural* gap** (Specs 1 & 2 are degrees of "make existing capability reliable"); chosen first because it is the most load-bearing for a group game and has concrete authored content (poker, auction) waiting on it.

## Related ADRs / files
- ADR-033 confrontation engine · ADR-116 participant membership invariant · ADR-077 dogfight (sealed_letter) · ADR-074 opposed_check · ADR-117 pluggable ruleset · ADR-104/105 perception filtering · ADR-053 scenario/clue/gossip · ADR-036 turn coordination
- `sidequest-server/sidequest/game/encounter.py` (StructuredEncounter, EncounterActor, dual EncounterMetric)
- `sidequest-server/sidequest/server/narration_apply.py` (beat apply loop, sealed-letter branch)
- Content: `spaghetti_western/rules.yaml` (poker), `tea_and_murder/rules.yaml` (auction, Duel of Wits, Trial)
