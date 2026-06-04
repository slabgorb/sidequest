# Design Recommendation: Confrontation Space Usage

**From:** The Duchess (UX Designer) · **To:** Dev (The White Rabbit) / Architect (The White Queen)
**Date:** 2026-06-04 · **Repo:** `sidequest-ui` · **Epic:** 85 (Post-Playtest UX Polish)
**Component:** `src/components/ConfrontationOverlay.tsx`

---

## The moral (what this MEANS for the player)

A confrontation is the **drama peak** of a scene — the chase, the trial, the duel. Two of
our five players (Sebastien, Jade) play *for the crunch*, and the dial/DC math is the thing
they came to read. Yet on screen the confrontation is rendered as the **smallest, most
cramped** surface in the whole client: a thin bottom strip with the most important readout
(the dials) lost in a low-contrast bar, the beat tiles huddled in one corner, and a 3D die
floating alone in a void.

This violates three SOUL principles at once:

- **Cost Scales with Drama** — the highest-drama moment gets the *least* screen.
- **Diamonds and Coal** — detail should signal importance; here the layout signals "minor."
- **The Guitar Solo** — when one player is in a confrontation the rest of the table must not
  become a silent audience; the wasted space is exactly where their concurrent action should live.

Keith's note from the playtest: *"During confrontations I feel we are not using space well."*
He's right, and it's not just polish — it's the screen telling the player the wrong thing
about what matters.

---

## What I looked at

| Screenshot | Scene | What it shows |
|---|---|---|
| `oq-2/sq-playtest-screenshots/319-confrontation-panel-ux.png` | wonderland Audience/Trial | the panel in isolation — clearest view of the dead space |
| `oq-2/sq-playtest-screenshots/412-circuit2-chase-panel-beat-rolled.png` | the_circuit Road Chase | the panel in full-board context (bottom strip over an empty board) |
| `oq-2/sq-playtest-screenshots/320-audience-resolved-victory.png` | wonderland resolved | panel gone, back to narration + tabs |

---

## Diagnosis — where the space goes (current strip)

`ConfrontationOverlay` is a **1-D horizontal band** mounted between the dockview workspace
and the InputBar (`confrontation-panel … border-t px-3 pt-2 pb-1`). Internally:

```
┌─ confrontation-panel (full width, ~short height) ───────────────────────────────┐
│ G·T  Audience / Trial   YOU ▓▓▓▓····· 4/10      THEM ·········· 0/10              │  ← StatusLine: full-width bar,
│                                                                                  │    two tiny numbers, dark-on-dark
│ ✦ Sets up a scene tag: Court's Own Rule Turned (no dial change by design) 0      │  ← beat-impact callout
│ ┌──────────┐┌──────────┐┌──────────┐┌─────────────┐                              │
│ │Spot Contr││State Case ││Hold Nerve││Appeal Fairns│  …caption overflows →        │     ┌────────┐
│ └──────────┘└──────────┘└──────────┘└─────────────┘        (big empty void)      │     │  3D die │  ← floats
│ ┌──────────┐                                                                     │     │  alone  │     in a
│ │Refuse ✦  │  [Yield]                                                            │     └────────┘     fixed
│ └──────────┘                                                                     │                    200px lane
└──────────────────────────────────────────────────────────────────────────────-─┘
        ▲ beats huddle top-left (grid auto-FILL leaves phantom columns)
```

Four concrete space wasters, each tied to the code:

1. **The dial bar is full-width for two short numbers.** `StatusLine` → `EdgeBar` renders
   `h-1` hairline tracks with `text-[9px]`/`text-[10px]` numerals. The single most important
   mechanical state in the scene is the *thinnest, smallest, lowest-contrast* thing in it.
   (L162 defect 1.)
2. **Beats huddle, leaving phantom columns.** `BeatGrid` uses
   `gridTemplateColumns: repeat(auto-**fill**, minmax(150px, 1fr))`. `auto-fill` keeps empty
   phantom tracks instead of stretching the tiles, so in any container wider than ~4×150px the
   tiles pack left and the remainder is dead. `auto-fit` would collapse the empties and let
   tiles breathe.
3. **The die floats in a fixed 200px lane, disconnected from the beat that threw it.** The
   `InlineDiceTray` lives in a `flex-shrink-0 w-[200px]` column to the right of the beats;
   when idle it's empty space, and when active the roll happens *away* from the tile the player
   clicked — no spatial beat→roll→result chain. (L162 defect 3.)
4. **The board canvas above the strip is unused.** In `412` the entire central/lower board is
   dark and empty during the chase — the most cinematic moment has the most empty pixels.

---

## Recommendations

Two tiers. **Tier A** is layout polish that fits inside the existing strip and belongs in the
already-filed **85-1**. **Tier B** is the real answer to "use space well" — it's a spatial
*promotion* of the confrontation and is bigger than a polish pass, so it wants its own story
(proposed **85-3**) and an Architect nod on the dockview seam.

### Tier A — make the existing strip earn its space (fold into 85-1)

- **A1 · Dial as the headline, not a hairline.** Promote the two dials to the visual top of
  the panel as a single **tug-of-war scoreboard**: one bidirectional bar with `YOU` filling
  from the left and `THEM` from the right toward a center line, large tabular numerals
  (`4 / 10` vs `0 / 10`), and a *visible* empty-track color so `THEM 0/10` is not invisible.
  This reuses the wasted full width for the thing that deserves it. (Also closes L162 defect 1.)
- **A2 · `auto-fill` → `auto-fit` on `BeatGrid`.** One-line change that lets tiles stretch to
  consume the row instead of huddling. Keep the `minmax(150px, 1fr)` so they wrap gracefully.
- **A3 · Anchor the die to the committed beat.** When a beat is clicked, roll the die *in the
  tile's own row* (tile expands to show `rolled 19 vs DC 12 → Critical`), so beat → roll →
  result is one spatial unit. Retire the lonely fixed 200px lane (or shrink it to a compact
  "last roll" chip docked under the active tile). (Closes L162 defect 3.)
- **A4 · Caption wraps inside its card.** `BeatTile`'s italic flavor caption must wrap within
  the tile (or move to a `title`/expand-on-`▾`); never overflow the right edge. (L162 defect 2.)
- **A5 · Reclaim the right void as a beat-history ledger.** The space freed by A3 carries a
  3-line "what just happened" log — `actor · beat · roll vs DC · dial Δ` — so the dial movement
  has visible mechanical provenance. This is the OTEL-in-the-player-UI spirit Sebastien/Jade
  want: they can *see* the engine moved the dial, not just trust the prose.

### Tier B — promote the confrontation into the space it deserves (propose 85-3)

The strip is the wrong *container*, not just badly packed. A confrontation is a mode, and
during it the client should let the encounter **claim the board canvas** rather than sit as a
band beneath an empty one. Reuse the existing **dockview** pattern (Character/Inventory/Map are
already dockview panels) — auto-focus a **Confrontation panel** while an encounter is active,
giving it real 2-D space:

```
┌─ Confrontation (auto-focused dockview panel while active) ──────────────────────────────┐
│  ROAD CHASE — Magpie  vs  Divvie cruisers                       [stakes: shake them or    │
│                                                                  lose the cargo]          │
│  ┌────────────┐                                          ┌────────────┐                   │
│  │  YOU        │   SEPARATION  5 ───────●           2  PURSUIT │  THEM      │  ← opponent   │
│  │ portrait    │   ◄═══════════════╪═══════════►            │ portrait   │    portrait +  │
│  └────────────┘                  (tug-of-war)               └────────────┘    last beat   │
│                                                                                           │
│  YOUR MOVE (pick a beat — plain Enter is locked)            BEAT LEDGER                    │
│  ┌─────────┐┌─────────┐┌─────────┐┌─────────┐              t3 Floor It  7 vs 14  Fail +2🚓 │
│  │Floor It ││Terrain ⚡││Smoke 💨 ││Kill Eng ││  ← stretch  t2 Terrain   12 vs 11 Pass +1   │
│  │PUSH·RS  ││PUSH·Scr ││ANGL·Scr ││PUSH·RS  ││    to fill   t1 (chase begins)              │
│  └─────────┘└─────────┘└─────────┘└─────────┘                                             │
│                                                            🎲 [die rolls under the tile    │
│  MEANWHILE AT THE TABLE  (Guitar Solo — others' concurrent verbs)   you committed]        │
│   • Spark (gunner): "lay down covering fire"   • Haraka (nav): "call the next turn"        │
└──────────────────────────────────────────────────────────────────────────────────────-──┘
```

What Tier B buys (and which principle it pays back):

- **Opponent portrait + name + their last beat** on the THEM side → the confrontation reads as
  *against someone*, and the dial has a face (Diamonds and Coal; ADR-116 "requires an Other").
- **Stakes line** (`set_stakes`) up top → the drama is legible, not implied (Cost Scales with Drama).
- **"Meanwhile at the table"** strip → the non-soloing players' concurrent verbs live in the
  reclaimed space, so a solo never becomes silence (The Guitar Solo — *the* reason to spend the
  pixels here). In solo play this row simply collapses.
- **The dial becomes a true scoreboard**, the beats stretch, the die is anchored, the ledger is
  visible — every Tier A win, now with room to be excellent rather than merely un-broken.

**Open design question for the operator/Architect (the one real decision):** does the
confrontation **replace** the narration dockview panel while active (full takeover — most
cinematic, but hides the running prose), or **split** with it (prose left, confrontation right —
keeps "the soloist reachable" and the others reading along)? My recommendation is **split**:
it preserves the Living World scroll and is the literal embodiment of the Guitar Solo's "keep
the band playing." This is the choice that should gate 85-3 before any code.

---

## Accessibility notes (apply to both tiers)

- Dial numerals + title to **WCAG AA 4.5:1** against the panel — today they fail (dark-gray on
  near-black). The empty THEM track needs its own visible token, not `bg-muted` at panel opacity.
- Beat tiles are the only commit path during a confrontation (plain Enter is locked) → they MUST
  be keyboard-reachable in DOM order with a visible focus ring, and the locked-Enter state needs
  an `aria-live` hint ("pick a beat to commit") so it isn't a silent dead-end for a screen reader.
- The resolution beat (`Refuse the Premise ✦`) is the win move — give it a distinct role/label,
  not just an amber border, so it doesn't read as "just another tile."
- Respect `prefers-reduced-motion` for the die roll and dial-pulse animations.

---

## Mapping to stories

| Recommendation | Home | Notes |
|---|---|---|
| A1–A5 (dial headline, auto-fit, die-anchor, caption wrap, ledger) | **85-1** | extends the legibility story into a same-strip space pass; pure `ui`, no protocol change |
| B (spatial promotion / dockview confrontation mode) | **propose 85-3** | needs the split-vs-takeover decision (Architect) + opponent-portrait & stakes already on the CONFRONTATION payload? verify before scoping |
| Opponent portrait + stakes on payload | check first | if the CONFRONTATION payload lacks `actors[].portrait` / stakes, B has a small server/protocol dependency — flag for Architect |

**Do not re-litigate what works:** the mechanics are sound (dice → dial → tag fire; stat /
kind / DC all exposed — good for the crunch players) and the panel now *surfaces* correctly for
chases (verified, #647). This is about giving a working subsystem the room its drama earns.
