# Epic 85: Post-Playtest UX Polish — Confrontation Panel & Location Surface

## Overview

UX-lane follow-ups surfaced by the **2026-06-04 playtest** (road_warrior/`the_circuit` +
wry_whimsy/`wonderland`). The underlying mechanical fixes already landed and verified
(chase engine #647, `discovered_regions` pollution #648); this epic collects the
**player-facing presentation polish** that remained — the parts where the engine is correct
but the screen tells the player the wrong thing about what matters.

**Priority:** P2
**Repo:** ui (primary), server (only if a payload field is found missing — see 85-3)
**Stories:** 3 (3 + 5 + 5 = 13 points)

Two themes:

1. **Confrontation-panel legibility/layout** (85-1, 85-3) — the panel *surfaces* correctly now,
   but the dial readout is illegible (dark-on-dark hairline), beat-caption text overflows its
   card, beats huddle in a corner leaving phantom columns, and a 3D die floats alone in a fixed
   void disconnected from the beat that threw it. Matters most for the **mechanics-first players
   (Sebastien, Jade)** who read the dial/DC math directly in the player UI.
2. **Location-surface "one source of truth"** (85-2) — the header binds to
   `party_status.location` (free-text scene title) while the Location tab binds to the
   region-level `LocationDescriptionPayload`, so the two disagree on screen during intra-region
   POI moves.

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Confrontation Space Usage** (`docs/design/confrontation-space-usage.md`) | Tier A (folds into 85-1: A1 dial scoreboard, A2 auto-fit grid, A3 die anchor, A4 caption wrap, A5 beat-history ledger) + Accessibility notes; Tier B (85-3 proposal) + the split-vs-takeover design question |
| **sq-playtest-pingpong (2026-06-04)** | Findings L162 (confrontation panel: illegible dial, caption overflow, floating die), L105 a/b (location surface divergence) |

## Background

A confrontation is the **drama peak** of a scene — the chase, the trial, the duel — and SOUL's
*Cost Scales with Drama* says the highest-drama moment should command the most screen. Today it
gets the least: a thin bottom strip (`confrontation-panel … border-t`) mounted between the
dockview workspace and the InputBar, with the single most important mechanical readout (the
dials) rendered as a low-contrast hairline. Keith's playtest note — *"During confrontations I
feel we are not using space well"* — is the seed of this epic.

This violates three SOUL principles simultaneously: **Cost Scales with Drama** (least screen for
the peak moment), **Diamonds and Coal** (layout signals "minor" for the most important surface),
and **The Guitar Solo** (the wasted space is exactly where the non-soloing players' concurrent
action should live, so a solo doesn't become silence).

The mechanics themselves are **sound and must not be re-litigated**: dice → dial → tag-fire
works; stat / kind / DC are all exposed (good for the crunch players); the panel now surfaces
correctly for chases (verified, #647). This epic is purely about giving a working subsystem the
room and legibility its drama earns.

The location-surface thread (85-2) is a separate divergence: two bindings for "where am I"
(free-text scene title vs region-level payload) that disagree during intra-region POI moves —
a design-first decision about which is the single source of truth.

## Technical Architecture

**Confrontation panel (85-1, 85-3) — `sidequest-ui`:**

- Single component: `src/components/ConfrontationOverlay.tsx` (~31KB). All sub-pieces are
  internal to this file:
  - `StatusLine` → `EdgeBar` — the dial readout. Renders `h-1` hairline tracks with
    `text-[9px]`/`text-[10px]` numerals (the legibility defect, L162-1).
  - `BeatGrid` — `gridTemplateColumns: repeat(auto-fill, minmax(150px, 1fr))`. `auto-fill`
    keeps phantom empty tracks; `auto-fit` collapses them (A2).
  - `BeatTile` — beat cards; italic flavor caption overflows the right edge (L162-2 / A4).
  - `InlineDiceTray` — 3D die in a `flex-shrink-0 w-[200px]` column, disconnected from the
    clicked tile (L162-3 / A3).
- **Pure UI for 85-1** — no protocol/payload change. The CONFRONTATION payload already carries
  dial values, beats, stat/kind/DC. Render-level only.
- **Existing test surface** (rich — extend, don't reinvent): `src/components/__tests__/`
  (`ConfrontationOverlay.test.tsx`, `.beatimpact*.test.tsx`, `.outcomereveal.test.tsx`,
  `.opponentbeatimpact.test.tsx`) and `src/__tests__/confrontation-*-wiring.test.tsx`. Vitest +
  React Testing Library throughout.
- **85-3 (Tier B)** would promote the confrontation into a **dockview panel** (reusing the
  Character/Inventory/Map dockview pattern) with opponent portrait + stakes + a "Meanwhile at
  the table" Guitar-Solo row. Has a possible **server dependency**: if the CONFRONTATION payload
  lacks `actors[].portrait` / stakes, that's a small protocol add (flag for Architect). Gated on
  the split-vs-takeover decision — out of scope for 85-1.

**Location surface (85-2) — `sidequest-ui` + possibly `server`:** header binds
`party_status.location`; Location tab binds `LocationDescriptionPayload`. Design-first story to
pick one source of truth — not coupled to the confrontation work.

## Cross-Epic Dependencies

**Depends on:**
- Chase/confrontation engine fixes (#647) and `discovered_regions` fix (#648) — already merged
  and verified; this epic is the presentation layer on top of that working mechanism.
- ADR-116 (A Confrontation Requires an Other) — informs the Tier B opponent-portrait framing
  (the dial should have a face). Not load-bearing for 85-1.

**Depended on by:**
- None. This is leaf polish work; no other epic consumes its output.
