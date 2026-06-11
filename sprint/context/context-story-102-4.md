---
parent: context-epic-102.md
workflow: tdd
---

# Story 102-4: WN turn model — sealed-letter commitment + initiative-ordered resolution + dead_premise

## Business Context

Retires deferred phase P4 of the SWN module design (§6–7). Faithful WN combat is *blind commitment, initiative-ordered resolution*: everyone declares, then 1d8+DEX order resolves the round — and a committed action whose target is already down when its initiative slot arrives is a **dead premise** the narrator must handle, not silently retarget. This is the structural difference between WN-feeling combat and generic turn-taking, and it's shared across all four sisters (SWN/WWN/CWN/AWN). It also harmonizes with the playgroup's submit-and-wait doctrine (ADR-036, Alex's pacing): sealed commitment is mechanically what the table already does socially.

## Technical Guardrails

- **Keith directive (2026-06-10): keep SideQuest turn semantics.** The WN turn model is implemented *inside* SideQuest's existing table model — module seam, ADR-036 submit-and-wait barrier, ADR-051 turn counters — not as a parallel turn system. WN crunch adapts to SideQuest's semantics, never the reverse. (Also noted: Kevin Crawford has confirmed our SRD use is proper — licensing is settled, not a design constraint.)
- **Spec authority:** SWN module design §6 (turn model), §7 (action economy → sealed action menu), plus the P4 initiative-spine design (`2026-05-27-swn-p4-initiative-spine-design.md`) — read both before designing; the initiative spine may be partially landed. Check `game/ruleset/resolution.py` and the encounter/turn modules for existing initiative machinery before building any (Don't Reinvent).
- **Module owns the whole turn (§3, Approach A):** the turn model lives behind the RulesetModule seam, not in generic dispatch. Native-ruleset genres keep today's turn flow untouched.
- **Sealed-commit precedent:** ADR-129's N-seat table engine generalized a sealed-commit loop for poker/auction — study its commit/reveal structure for reuse before writing a new one. ADR-036's turn barrier (no narration until everyone submits) is the MP substrate the sealed letter rides on; peer action text remains visible during the wait phase per the 2026-05-03 amendment (sealed *resolution*, not hidden submission).
- **dead_premise is a narrator call, not engine improv:** when the target is already dropped at the slot, the engine surfaces a typed dead-premise event for the narrator to adjudicate (re-aim is a player/narrator decision in fiction, per The Test — never auto-act the player).
- **Initiative:** 1d8+DEX per the spec — player-facing rolls go through the ADR-074 dice protocol where the spec says they're visible (Sebastien sees the math).
- **ADR-139 invariants** (win-condition liveness, seated-actor durability, dispatch applicability) must hold through reordered resolution — the integrity tests are your regression net.
- Cross-repo: UI needs the commitment/locked state surfaced in the confrontation overlay (committed vs waiting), reusing the existing submit-and-wait presentation if possible.

## Scope Boundaries

**In scope:**
- Round structure: commit phase (sealed action menu per §7) → initiative roll/order → ordered resolution → dead_premise narrator surface
- Shared across the WN family behind the module seam; OTEL spans for phase transitions ({ruleset}.round.committed/.initiative/.resolved, dead_premise emission)
- Server + UI; fixtures for ordered resolution and dead-premise

**Out of scope:**
- Psionics/Effort in the action menu (102-6 layers onto this)
- Narrator tool contract reshape (102-5 — coordinate the dead_premise call shape with it, but don't build the full contract here)
- Native-ruleset turn flow changes; MP lobby/seat changes (ADR-122/129 engines themselves)

## AC Context

1. **Sealed commitment:** in a WN confrontation, all seated participants' actions are committed before any resolution; no resolution output leaks before the barrier closes. Test: MP fixture, assert ordering of events.
2. **Initiative-ordered resolution:** 1d8+DEX rolled per participant; resolution applies in descending order; order and rolls appear in spans and the player-visible surface. Test: seeded RNG fixture asserting exact order (resume-safe randomness per ADR-128 patterns).
3. **dead_premise:** A commits attack-on-B; B drops earlier in the order; at A's slot the engine emits the dead-premise event/narrator call and does NOT auto-resolve A's original action. Test: fixture forcing the kill order; assert no damage applied to a corpse, narrator surface invoked.
4. **Family-wide:** parametrized across swn/wwn/cwn/awn module bindings; native genre untouched (regression).
5. **Wiring:** integration test from DICE_THROW/commit messages through dispatch — not engine-internal calls only.

## Assumptions

- The P4 initiative-spine design landed some groundwork (verify what exists in `resolution.py` first — the delta may be smaller than the story title implies).
- ADR-129's sealed-commit loop is reusable or at least instructive; if it's poker-specific, a WN-shaped commit barrier behind the module seam is acceptable new code (3+ failure justification documented).
- 8 points assumes turn-model state fits the existing encounter state model without a persistence migration.
