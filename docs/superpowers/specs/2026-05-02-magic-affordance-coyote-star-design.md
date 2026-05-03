# Magic Affordance for Coyote Star — Sensitivities on the Abilities Tab

**Author:** Keith (with Inigo / dev)
**Date:** 2026-05-02
**Status:** draft, awaiting Keith's review
**Related:**
- Epic 47, story 47-2 (Phase 4 manual smoke — currently blocked by zero invocations)
- Plan: `docs/superpowers/plans/2026-04-28-magic-system-coyote-reach-v1.md`
- Genre lineage: Chalmers (consciousness substrate), Leckie (Imperial Radch / distributed identity), Wells (Murderbot / constructed self), Tchaikovsky (Children of Time / collective embodied cognition). River-Tam-shaped — involuntary, fragmentary, costly, sometimes retroactive. Leone-McQuarrie is the *visual* lineage only; mechanical/narrative is the list above.

## Problem

Across 8 coyote_star playtest saves spanning 2026-04-30 → 2026-05-02:

- Zero entries in `magic_state.recent_workings`
- Zero Phase-5 confrontation IDs in any event payload
- All bar `current` values are `None` — never touched
- Narration log keyword sweep (sanity / working / bleeding / lattice / psionic / conduit) returns false positives only

Magic infrastructure persists correctly on every save (config + ledger + bar specs), but no player has ever invoked a working. AC1–AC5 of story 47-2 (innate cost, item working, threshold-cross to Bleeding-Through, save/load roundtrip, DEEP_RED-trigger) have never been exercised in a real session.

Root cause (per Keith, who playtested himself): **the in-fiction microbleeds (`magic_microbleed` detail attached to every coyote_star opening — a mug jitters, dust smells of rain, the hum carries something that isn't yours) read as atmosphere, not as invitations to act.** Even the system's author had ZERO clue what they were when he saw them in play. If the GM-turned-player can't read them, no one can.

Compounding: there is no UI surface anywhere that names the player's capacity to reach toward those bleeds. The Abilities tab (`CharacterPanel.tsx::AbilitiesContent`) lists mundane abilities only.

## Audience constraints (from CLAUDE.md)

- Keith / James — high reading tolerance, narrative-first; want the dramatic-reveal moment preserved.
- Sebastien — mechanics-first; wants visible cost transparency on the bars.
- Alex — slow typist, freezes under prose pressure; benefits from an *always-visible* affordance she doesn't have to ask about.
- Sonia — low buy-in; even one cryptic line will tilt her toward leaning into a bleed instead of past it.

CLAUDE.md (SOUL §Zork): "never reduce player input to keyword matching, never gate actions behind UI menus when natural language would serve, never let the interface imply a closed set of options when the set is open." → No buttons, no chips, no pre-fill outside confrontations. Description only.

## Design — chosen approach

**Hybrid reveal pacing (option C from brainstorming):** the Abilities tab carries a one-line cryptic Reader hint at chargen (turn 0), and a Sensitivities subsection that *expands inline* the moment the first bar moves.

**Out-of-confrontation affordance (option A from brainstorming):** description only. No example phrasings, no chips, no buttons. The text names the cost vocabulary (sanity / notice / vitality) and tells the player to use their own words in the input bar.

**In-confrontation affordance:** unchanged. Magic use surfaces as beat buttons in the existing `ConfrontationOverlay`, same as every other beat. No new work.

## Surface

`sidequest-ui/src/components/CharacterPanel.tsx` → `AbilitiesContent`. After the existing bullet-list of abilities, append a new `<SensitivitiesSection>` component.

```
Abilities
- Coreworlder Admin Tradecraft
- Read a Manifest at a Glance
- ...

Sensitivities                       ← new heading, italic, smaller
You hear what the others don't.
Sometimes.                          ← pre-bleed copy
```

After first bar movement:

```
Sensitivities
Something stirred. You felt it.

The substrate has weight — the hum behind the hum,
the thing the dust profile carries that isn't dust.
You can answer. You can refuse. You can push deeper.
You can sit with it.

Sanity is the price of staying open. Notice measures
what you catch. Vitality decides whether you can
carry it back.

No one taught you the shape of this. You learn by
reaching, or by flinching.

  Sanity   ▓▓▓▓▓▓▓▓▓▓░  0.95 / 1.00
  Notice   ▓▓▓▓▓▓▓▓▓▓░  0.95 / 1.00
  Vitality ▓▓▓▓▓▓▓▓▓▓░  0.95 / 1.00

Your own words, in the input bar.
```

## Architecture

### Server: zero changes
`magic_state` is already in `GameSnapshot`, broadcast on PARTY_STATUS deltas. Each bar carries `starting` and `current`. The UI derives pre-/post-bleed state from those values; no new fields, no new message types.

### UI

**Trigger logic (post-bleed detection):**
- Read the active PC's three ledger entries: `character|<name>|sanity`, `|notice`, `|vitality`.
- If `magic_state.ledger` is absent for the active PC → render nothing (Sensitivities section does not appear at all; covers other genres + pre-magic worlds).
- If all three bars have `current === null` OR `current === starting` → pre-bleed mode (cryptic line).
- If any of the three has `current !== null` AND `current !== starting` → post-bleed mode (full text + bar HUD).

**Bar HUD:**
Reuses the existing `GenericResourceBar` component from the Status tab — same visual treatment Sebastien already learns elsewhere. Three rows, sanity / notice / vitality.

**World gate:**
Implicit. The render only fires if the active PC has `magic_state.ledger` entries — coyote_star is currently the only world that produces them. No genre-slug check needed in code; if another world later wires magic, this section starts appearing for it automatically. (Acceptable — once a world has magic, the player needs to know about it.)

### Content

Copy lives in `CharacterPanel.tsx` (hardcoded). Two strings: `PRE_BLEED_COPY` and `POST_BLEED_COPY`. Promotion to genre pack content (`worlds/<slug>/sensitivities.yaml`) is a follow-up if/when a second world wires magic and needs different copy.

Per CLAUDE.md "no abstractions beyond what the task requires" — coyote_star is the only world with magic_state today, so hardcoding the copy is correct, not stubby.

## Out of scope (explicitly)

- **Beat buttons / chips / pre-fill outside confrontations.** Keith's call (option A): description only.
- **Detection pipeline changes.** This story surfaces the affordance and ships. If natural-language invocation still doesn't fire after the next playtest (e.g. player types "I lean into the hum" and the narrator never registers a working in `recent_workings`), that becomes a separate story — Phase 6 territory.
- **Other genres.** No changes to flickering_reach, mawdeep, or any other world. Coyote_star only.
- **In-confrontation magic UI.** Already exists as beat buttons; no work.
- **Server-side state changes.** Zero new fields, zero new messages.
- **Chargen confirmation epilogue rewrite.** The existing epilogue is fine; the cryptic line lives in the UI panel, not in narration.

## Acceptance criteria

1. **AC1 (chargen Reader hint):** Loading a fresh coyote_star save with a newly created PC (no narration yet → no bar movement) shows a `Sensitivities` heading with the pre-bleed copy on the Abilities tab.
2. **AC2 (post-bleed unfold):** When any of the active PC's three bars (`sanity` / `notice` / `vitality`) has `current` set and not equal to `starting`, the Sensitivities section expands inline to show the post-bleed copy + the three-row bar HUD.
3. **AC3 (other-genre absence):** Loading any non-magic save (e.g. mawdeep) shows the Abilities tab with NO Sensitivities heading at all.
4. **AC4 (cost transparency):** The post-bleed bar HUD uses the same `GenericResourceBar` component as the Status tab, so the visual language is consistent across surfaces.
5. **AC5 (no buttons):** No interactive elements in either pre- or post-bleed state. Static text and static bars only.
6. **AC6 (smoke test):** Next coyote_star playtest produces at least one entry in `magic_state.recent_workings` OR a Phase-5 confrontation event in the save's events table — measurable evidence the affordance landed.

AC6 is the real success criterion; AC1–AC5 are mechanical wiring checks that confirm the surface ships correctly.

## Testing

**Wiring tests (vitest, `sidequest-ui/src/__tests__/`):**

- `sensitivities-pre-bleed-wiring.test.tsx` — given a Character with `magic_state.ledger` populated and all three bars at `starting`, render `CharacterPanel` and assert the Sensitivities heading + pre-bleed copy is in the DOM, and the bar HUD is NOT.
- `sensitivities-post-bleed-wiring.test.tsx` — same setup but with `sanity.current = 0.95` (≠ starting `1.00`); assert the post-bleed copy is in the DOM, all three `GenericResourceBar`s are rendered, and the heading is present.
- `sensitivities-absent-when-no-magic-state.test.tsx` — given a Character with no `magic_state.ledger` entry, assert NO Sensitivities heading appears anywhere on the Abilities tab.

**Visual sanity:** Manual render in dev (just up → coyote_star solo → check Abilities tab pre- and post-first-narration).

**No server tests** — server has zero changes.

## Risks

- **AC6 still fails (the real gate).** Even with the Sensitivities section visible, players might still not type magic-shaped actions. If true, Phase 6 widens to invocation vocabulary in the Sensitivities post-bleed copy itself or to a confrontation-style chip set on first bleed (revisit the brainstorming option-C path).
- **Bar HUD redundancy with Status tab.** If Sebastien already watches Status, putting bars on Abilities too may feel duplicative. Mitigation: the Status tab shows ALL resources (mundane + magic); the Abilities tab shows only the three magic bars in their narrative frame. Different lens, same primitive.
- **Pre-bleed cryptic line spoils nothing for new players** — this is a feature, not a risk. River doesn't *quite* know either.
