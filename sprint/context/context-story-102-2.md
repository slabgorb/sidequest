---
parent: context-epic-102.md
workflow: tdd
---

# Story 102-2: In-combat cast_spell via the dice path routes to the WN cast spine

## Business Context

The AC5b spellcast blocker. In live play, clicking the "Work a Spell (INT)" beat tile in the confrontation overlay resolves as a **generic INT dice throw**: no `wwn.spell.cast` span, `casts_remaining` stays 2/2, no Effort or System Strain is spent. The WN cast spine exists and works — `_resolve_wwn_cast_for_beat` fires correctly on the narrator-driven apply_beat path — but the UI's primary path (`DiceThrowPayload` → `dispatch_dice_throw`) can't reach it because the payload has no way to say *which spell*. Jade and Sebastien see a spell "cast" with no resource spend; Keith's GM panel shows the mechanic silent while the narration claims magic happened — exactly the Illusionism the OTEL doctrine catches.

## Technical Guardrails

- **Protocol change:** add optional `spell_id` to `DiceThrowPayload` (`sidequest/protocol/dice.py:160`, pydantic v2) and mirror it in `sidequest-ui/src/types/` WebSocket payload definitions. Optional with default `None` — every existing non-cast beat throw must be wire-compatible unchanged.
- **Reuse the spine:** route the dice-path cast into the same resolution `_resolve_wwn_cast_for_beat` (`server/narration_apply.py:261`) uses — extract/share rather than duplicate. The apply_beat path gets `spell_id` from the BeatSelection sidecar; the dice path now gets it from the payload. One cast implementation, two entry points.
- **UI:** ConfrontationOverlay needs spell selection for the cast beat (the prepared-spell list with `casts_remaining`). Project memory: if this adds a GameBoard dock tab it must register in BOTH `widgetRegistry`/GameBoard AND MobileTabView's `TABS` array — but prefer extending the existing overlay beat-tile flow, not a new tab.
- **Zork Problem guardrail:** spell selection is an alternate submit verb layered on typed text — preserve the existing `player_action` carry (typed text + beat click travel together). Never make the picker the only way to cast; free-text casting is 102-3.
- **Player-visible math (Sebastien/Jade):** the resolution surface should expose the spend — Effort committed, casts decremented — via the existing player-facing dice/beat result surfaces, consistent with SWN design §9.
- **Message-type hygiene:** if a new MessageType is added (avoid if possible — extend the existing payload), note the stale `test_message_type_complete_count` 54-vs-55 failure on develop (project memory: pre-existing, unrelated).
- Validation: reject `spell_id` the caster doesn't have prepared / lacks casts for — loudly (No Silent Fallbacks), with a typed error the UI can render.

## Scope Boundaries

**In scope:**
- `spell_id` on `DiceThrowPayload` (server protocol + UI types)
- Dice-dispatch routing: cast beat + `spell_id` → WN cast spine (`wwn.spell.cast` span, Effort/System-Strain/casts spend)
- ConfrontationOverlay spell-selection UI for the cast beat
- Server tests (span + resource assertions) and UI tests (selection → payload), plus a wiring test across the dispatch path

**Out of scope:**
- Free-play typed casting via the intent router (102-3)
- Psionics/disciplines (102-6)
- Narrator tool contract changes (102-5)
- Any change to the apply_beat path — it already works; it is the reference behavior

## AC Context

1. **Cast beat fires the WN cast spine.** DICE_THROW with `beat_id=cast_spell` + `spell_id=X` in a WN genre emits `wwn.spell.cast` (module slug, spell id attrs), decrements `casts_remaining`, applies Effort/System-Strain per the module. Test: deterministic confrontation fixture, assert span + state deltas.
   - Edge: `spell_id` absent on a cast beat → loud, typed rejection (or a defined fallback the story explicitly chooses — no silent generic-INT resolution remains possible for cast beats).
   - Edge: non-cast beats with no `spell_id` behave byte-for-byte as today (regression assertion).
2. **Parity with apply_beat.** The same spell cast via the narrator apply_beat path and via the dice path produce equivalent mechanical outcomes and span shapes (parametrized parity test).
3. **UI selection flow.** Clicking "Work a Spell" surfaces the prepared-spell picker; selection populates `spell_id` in the payload; typed `player_action` text still rides along. Vitest: payload construction + overlay render with `casts_remaining` visible.
4. **Wiring proof.** An integration test drives WebSocket-level DICE_THROW through dispatch to the spine (not a direct function call).

## Assumptions

- The prepared-spell list (and `casts_remaining`) is already available to the client via existing state-mirror projections; if not, exposing it is in-scope as a reactive projection, not a new request/response pair.
- `_resolve_wwn_cast_for_beat`'s body is path-agnostic enough to extract; if it's entangled with narration application, the extraction seam is the first RED test.
- E2E flake guard (project memory): stub the intent-router pass in handler/e2e tests.
