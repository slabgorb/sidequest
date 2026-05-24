# 53-5

## Problem

Problem: Road Warrior drivers were taking rig damage and crashing in the game, but players had no way to see any of it — the character sheet showed nothing about vehicle health, stress, or injury. Why it matters: when your muscle car is held together with duct tape and the narrator describes your engine catching fire, the player should be able to *see* the damage accumulating in real time. Without visible rig stats, players were flying blind — the mechanical drama of Road Warrior was happening invisibly behind the scenes.

---

## What Changed

Think of a car's dashboard: before this story, the CharacterSheet panel in the UI was like a car with a completely blank instrument cluster. The engine had real sensors (built in earlier stories), but no gauges on the dash.

This story added the gauges:

- **Composure bar** — a health bar for your vehicle's structural integrity. Full green when the rig is road-worthy; empties as damage accumulates; hits zero when you crash.
- **Edge bar** — your driver's personal momentum and aggression rating, shown alongside the rig's composure so players can see both pools together.
- **Injury tags** — small red chips that appear when you've been crashed and dismounted. If you got thrown from your vehicle and took injuries, those words now appear right on your character card: "injury," "dismounted."

The work touched three parts of the system: the server's data contract (adding the new fields to the message the server sends players), the TypeScript type definitions (so the UI knows what shape the data is), and the character sheet component itself (so it knows how to display the new bars and tags).

One catch caught during review: all the parts were working correctly, but the middle connector in App.tsx — the code that takes the server's message and hands it to the character sheet — was missing three lines. The new fields were being silently dropped before they ever reached the display. The reviewer caught it, it was fixed, and the final check confirmed all 1,545 UI tests pass.

---

## Why This Approach

The new bars follow the same visual pattern already used for the Edge bar — no new design language invented, just extending an existing pattern players are already familiar with. Showing both the vehicle composure and the driver's edge together keeps related information grouped.

Injury tags come from the server's authoritative list of status effects (set by the crash handler in story 53-3), not from a separate field. That means when the crash handler says "this character has injury status," the UI automatically surfaces it — no duplication, no drift between what happened mechanically and what the player sees.

The conditional rendering means the entire Composure section only appears for characters who are actually in a vehicle. Players who aren't driving see a clean sheet without placeholder bars.

---
