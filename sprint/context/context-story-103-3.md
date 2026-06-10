---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-3: Roll the Bones alt-attribute mode — 3d6-in-order + 2-stat reroll budget

## Business Context

"Roll the Bones" is the Gamma World 4e register in chargen: 3d6 per stat, placed in order, embracing the "hopeless character" possibility — an *option* alongside the existing default, never a replacement. The addendum kept it explicitly ("Keep, rephrased to the standard six"). It's small, independent crunch that makes chargen feel like the table experience Keith wants, and the dice belong on screen (ADR-074/075 surfaces exist for player-facing rolls).

## Technical Guardrails

- **Standard six (AWN D4):** STR/DEX/CON/INT/WIS/CHA, in order. No flavor-six names anywhere in code or content (narrator prose may still *say* "reflexes").
- **Additive chargen flag** in `char_creation.yaml` config — the existing attribute step gains a mode toggle; the current default mode is untouched. Genre-tier flag (it's mechanics), available to all mutant_wasteland worlds including flickering_reach.
- **Reroll budget = 2 stats:** player may reroll up to two chosen stats once each; the reroll replaces (not best-of). Deterministic/resume-safe randomness per ADR-128 conventions if the chargen roll path persists seeds.
- **Player-facing rolls:** route through the ADR-074 dice protocol so the rolls are visible/honest, not server-silent. Reuse the existing dice-throw payloads; no new protocol message types.
- **Do not** add new attributes, point-buy changes, or touch the stock/Saint paths (103-1/103-2).

## Scope Boundaries

**In scope:**
- Mode flag + 3d6-in-order roll flow + 2-stat reroll budget (server)
- UI affordance: mode pick + roll/reroll interaction in the attribute step
- Tests incl. one wiring test that the mode is reachable from real chargen

**Out of scope:**
- Any other chargen step; Rimworld-style storyteller dial (deferred v2, world spec §13)
- Changes to the default point-buy mode

## AC Context

1. **Mode selection:** attribute step offers default mode and Roll the Bones; default unchanged when not selected. Test: flow test both paths.
2. **Roll correctness:** six 3d6 results assigned in order STR→CHA; values land 3–18. Test: seeded roll assertion.
3. **Reroll budget:** at most two stats rerollable, once each, replacement semantics; budget enforced server-side (a third reroll request is rejected). Test: budget-exhaustion case.
4. **Visible dice:** rolls surface through the ADR-074 player-facing dice path. Test: payload/span assertion that the throw is player-visible, not improvised.
5. **Hopeless characters allowed:** no floor/uplift applied — a bad array stands. Test: assert no clamping logic engages.

## Assumptions

- Independent of 103-1/103-2 (can land in any order).
- The attribute step exists as a discrete chargen state with a config surface; if attribute generation is currently UI-implicit, the server becomes authoritative for this mode (log deviation if that shifts behavior).
