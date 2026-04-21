# Frontend Redesign — Mockup Directions

**Author:** UX Designer (Klinger)
**Date:** 2026-04-20
**Status:** Direction-pick stage — three distinct compositional premises.
**Context:** Retires the dockview + widget-registry composition. Book conceit already retired per CLAUDE.md. Keeps the existing plumbing (genre theme vars, archetype fonts, 3-mode narration switch, state providers).

---

## Design constraints carried from CLAUDE.md + audit

1. **Playgroup-first.** Keith (both axes, high tolerance, forever-GM-finally-playing), James (narrative-first), Alex (slow reader/typist, freezes under pressure — *design implication: no fast-typist monopolies, generous windows, low chrome*), Sebastien (mechanics-first — *design implication: the GM panel is a feature, not a debug tool*).
2. **Narrative consistency is #1.** The mechanical state must back the story, not crowd it.
3. **Genre feel lives in the silhouette**, not just the paint. Today every genre pack shares the same dock-and-tabs silhouette. A redesign should make `victoria` and `neon_dystopia` structurally different at a glance.
4. **Keep the affordance.** The 3-mode narration switchboard (scroll / focus / cards) is the most valuable piece of existing architecture. Redesign proposes the *new primary reading mode*; scroll/cards can remain as alternates.
5. **Mechanical transparency is first-class.** Sebastien needs the GM/OTEL panel reachable without feeling debug-mode. Keith-as-player wants the narrator to be *trustworthy and inspectable*, not a black box.
6. **No skeumorphism.** Themed chrome is OK; usability over vibes. No paper textures, no torn edges, no simulated book spines.

---

## Direction A — "The DM Screen"

### Premise
A fixed three-panel silhouette. Narration in the middle, always. Left = Character Dossier (who I am, right now). Right = World Context (where I am, what I know, what I carry). The silhouette evokes a physical GM screen: the DM's mechanical ledger on one side, the narrative in the middle, the world map and handouts on the other.

### Desktop wireframe (1440×900 reference)

```
┌───────────────────┬────────────────────────────────────────┬───────────────────┐
│   DOSSIER         │           NARRATION                    │   WORLD           │
│   (fixed 280px)   │           (fluid)                      │   (fixed 320px)   │
│                   │                                        │                   │
│  ┌──────────────┐ │   CHAPTER III · The Lichgate           │  [Map]  [Know]    │
│  │  portrait    │ │                                        │  [Inv]  [NPCs]    │
│  │              │ │   (prior beats, dimmed 55%)            │  [Log]            │
│  └──────────────┘ │   ...                                  │  ─────────────    │
│   Rux · Bastion   │                                        │                   │
│                   │   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │   ┌─────────────┐ │
│   HP  ██████░░   │                                        │   │  TAB BODY   │ │
│   MP  ████░░░░   │   CURRENT TURN (bright · 100%)         │   │             │ │
│                   │   Narrator prose goes here in a        │   │  (map or    │ │
│   ◈ blessed      │   comfortable reading measure...       │   │   knowledge │ │
│   ◈ wounded      │                                        │   │   or gear)  │ │
│                   │   [NPC beat · portrait inline]         │   │             │ │
│   ─ coin 14       │                                        │   │             │ │
│   ─ rations 3     │   ┌────────────────────────────────┐   │   │             │ │
│   ─ ash-dust 1    │   │  ACTION                        │   │   │             │ │
│                   │   │  _________________________     │   │   │             │ │
│   ▸ full sheet    │   │  [submit]  [/ command]         │   │   │             │ │
│                   │   └────────────────────────────────┘   │   └─────────────┘ │
│   companions      │                                        │                   │
│   · James/Rask    │                                        │                   │
│   · Alex/Ven      │                                        │                   │
│                   │                                        │                   │
└───────────────────┴────────────────────────────────────────┴───────────────────┘
│  ♪ audio  ·  ◉ watcher  ·  ⌕ scroll back  ·  save  ·  leave                   │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Interaction & state
- **Narration column** defaults to *focus mode* (current turn big, prior beats dimmed). Scroll wheel reveals history progressively; a rail at top lets you jump to a chapter. Scroll and Cards modes available as alternates via a subtle mode toggle in the chapter header.
- **Dossier left** is the current player's character, *always visible*. On sealed-letter turns it stays your own — you never see another player's dossier. A one-click "▸ full sheet" opens a drawer, it does not navigate away.
- **World right** is a tab strip — Map / Knowledge / Inventory / NPCs / Log — but critically, *the tab that most recently changed lights up with a pip.* When you learn a fact, the Knowledge tab pulses. When an NPC enters, the NPCs tab pulses. Sebastien can leave it on Log; Alex can leave it on Map; James will chase the pulses.
- **Bottom rail** is thin, fixed, low-chrome: audio controls, watcher/OTEL toggle, scroll-back entry, save, leave. The GM/OTEL panel opens as a full-height overlay from the right edge when invoked — it does not steal narration space.
- **Confrontation** (combat / challenge) *takes over the dossier + world columns* with a tactical view and dice tray; narration column stays in place as the scene commentary. Returns to normal on resolution.

### Genre expression
- `victoria` — Dossier and World frames in cream/sepia, cameo-oval portrait, Didone display for chapter headers, ornamental rule (`━━━`) between turns.
- `neon_dystopia` — Dossier frame in low-saturation cyan with a subtle scan-line gradient, portrait in a square bezel, OLED-dark background, monospace chapter label, glow on the HP bar.
- `road_warrior` — Dossier on a sand/rust palette, stencil display font, portrait square with a gritty border, world tabs drawn as road-sign glyphs.
- `spaghetti_western` — Parchment fill, wanted-poster-style portrait, slab serif headers, all rules drawn as rope/whip glyphs.

Same silhouette, radically different texture. Archetype chrome continues to drive body/UI fonts per character.

### Who it serves
| Player | Read |
|---|---|
| **Keith** | Strong. Present-tense focus mode + all-genre structural texture. |
| **Alex** | Strong. Center-anchored reading, no surprise layout shifts. |
| **Sebastien** | Strong. Mechanical state always in the left rail; pips for changes. |
| **James** | Strong. Narrative-center; world tabs reward curiosity. |

### Risks
- 280 + 320 of fixed chrome eats ~40% of width at 1440px. Watch the narration measure — target 60–75ch.
- World column could become "tabs of junk" if every data-type gets one; be ruthless.

---

## Direction B — "The Folio"

### Premise
Two asymmetric columns. The left column is the **present scene** — a single sustained narrative frame at big type with a generous measure. The right column is a **living context sidebar** — the player's character, scene metadata, and collapsed world cards. History is *not visible by default*; the player scrolls back or opens a history overlay. Focus mode is the default; scroll is an opt-in.

This is the direction **closest to the CLAUDE.md-ratified "persistent themed sidebar + current-turn-focus narrative"**.

### Desktop wireframe

```
┌─────────────────────────────────────────────┬──────────────────────────────┐
│                                             │                              │
│   CHAPTER III                               │  ◆ YOU  · Rux the Bastion    │
│   The Lichgate                              │    HP 18/22  ·  MP 4/8       │
│                                             │    ◈ blessed of the gate     │
│   (1–2 prior lines, muted 35%)              │                              │
│   ...you crossed the plaza at dusk...       │    ▸ sheet  ▸ inventory      │
│                                             │                              │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │  ▾ WHERE YOU ARE             │
│                                             │    Lichgate Plaza · dusk     │
│   CURRENT TURN                              │    3 exits · 2 known NPCs    │
│                                             │                              │
│   The ash-woman waits beneath the gate.     │  ▾ WHAT YOU KNOW             │
│   She hasn't blinked. You are close         │    • the gate is sealed      │
│   enough now to see the veins beneath       │    • she wants a key         │
│   her skin — not blue, but the pale          │    • the key is not here     │
│   white of old ivory.                       │                              │
│                                             │  ▸ COMPANIONS (2)            │
│   She speaks your name.                     │                              │
│                                             │  ▸ RECENT NPCS               │
│                                             │                              │
│   ┌──────────────────────────────────────┐  │  ▸ QUESTS (3 active)         │
│   │  [ your action _________________ ]   │  │                              │
│   │  ▸ scroll back    ▸ chapter list     │  │  ─────────────────────       │
│   └──────────────────────────────────────┘  │  ♪ audio   ◉ watcher          │
│                                             │                              │
└─────────────────────────────────────────────┴──────────────────────────────┘
```

### Interaction & state
- **Left column is the scene.** Big type (~20–22px body), generous leading, ~65ch measure. Prior beats visible as 1–2 muted lines above the current turn; that's the whole context you get without scrolling. "▸ scroll back" opens a history overlay (the current scroll mode, essentially) without leaving the scene.
- **Right column is disclosure.** Identity block always open at top (HP, status, resources). Below it, collapsible cards: *Where You Are*, *What You Know*, *Companions*, *Recent NPCs*, *Quests*. Player chooses what to leave open. Playstyle leaves a signature in the sidebar state (localStorage persists their pattern).
- **No tabs on the right.** Cards are the unit. This lets a fact-heavy genre (Victorian mystery) have a long Knowledge card, while a light genre (road_warrior) keeps it collapsed.
- **GM/OTEL panel** opens as a bottom drawer (translucent, 30% height) invoked by watcher icon. Sebastien can pin it open.
- **Confrontation** takes the left column; sidebar stays. Keeps the player grounded.

### Genre expression
- `victoria` — Warm parchment left column, cameo-frame sidebar portrait, Didone/Garamond pairing, ornamental section rules.
- `neon_dystopia` — OLED-dark left column, narrow neon keylines on sidebar cards, typewriter-cursor blink on the input, scanline subtle texture on prose.
- `road_warrior` — Dusty ochre left column, sand-colored sidebar, stencil headers, tire-tread divider glyphs.
- `spaghetti_western` — Sun-bleached parchment, hand-cut slab display, rope-knot section rules.

### Who it serves
| Player | Read |
|---|---|
| **Keith** | Strong. Present-tense, immersive. Good for "GM finally playing." |
| **Alex** | Strongest of the three. Low chrome, single column of prose, no panel drag. |
| **Sebastien** | Mixed. Needs the watcher drawer pinnable — otherwise mechanics feel hidden. |
| **James** | Strong. Narrative-first disclosure in sidebar rewards digging. |

### Risks
- History hidden by default may annoy narrative-first players who want to re-read. Fix: persistent "▸ scroll back" + keyboard shortcut.
- Sidebar needs ruthless curation — every card is attention spent. Candidate for playtest feedback.

---

## Direction C — "The Stage"

### Premise
Narration goes full-bleed. Mechanics are **translucent HUD overlays** invoked on demand or on state change. No persistent panels. The UI is closest to a cinematic game than a document. Keyboard-first: `c` character, `i` inventory, `m` map, `k` knowledge, `w` watcher.

Hardest to land, most genre-expressive when it works. Highest risk with Alex and Sebastien — include only if the playgroup is willing to trade visibility for immersion.

### Desktop wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ═══  ACT II · SCENE 3 · THE LICHGATE  ═══                                 │
│                                                                            │
│                                                                            │
│        (prior beats, 30% · hover or scroll to unfade)                      │
│                                                                            │
│                                                                            │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│                                                                            │
│                                                                            │
│             CURRENT TURN · center stage                                    │
│             wide measure, generous leading,                                │
│             the one thing you're looking at                                │
│                                                                            │
│             The ash-woman waits beneath the gate.                          │
│             She speaks your name.                                          │
│                                                                            │
│             [ your action ______________________________ ]                 │
│                                                                            │
│                                                                            │
│                                                                            │
│   ◍ HP 18    ◍ map    ◍ gear    ◍ know    ◍ who    ◍ log    ◍ watch       │
└────────────────────────────────────────────────────────────────────────────┘
          (clicking or hotkey slides a translucent pane up from below)
```

### Interaction & state
- **Narration is the whole screen.** Chapter header thin at top. Thin mechanic tray at bottom (HP pill + 6 icons). Nothing else persistent.
- **State-change pulses.** HP drop pulses the HP pill; new item pulses the gear icon; new fact pulses the know icon. You can always *see* something happened even if you're not looking at it.
- **On-demand overlays.** Click or hotkey slides a translucent pane (bottom-up for inventory/gear, right-in for map, top-down for knowledge). Panes dismiss on esc or outside click. Never takeover — 60% height max, narration remains readable behind.
- **GM/OTEL** is just another pane (`w`). Sebastien hotkeys between it and the scene.
- **Confrontation** promotes the bottom tray to a tactical strip; dice tray slides up when rolling. Narration adapts to a thinner top banner.

### Genre expression
- `victoria` — Black-velvet full-bleed background with gold typography; overlays are translucent ivory with gilt edges; cameo portraits float in.
- `neon_dystopia` — Deep indigo full-bleed with chromatic aberration on the headline type; overlays are neon-outline, cyberpunk-HUD feel; persistent subtle scanlines.
- `road_warrior` — Bleached-white full-bleed suggesting sun-scorched horizon; overlays are metal-plate with rivets; HP pill looks like a gauge.
- `spaghetti_western` — Wide-aspect "CinemaScope" letterbox framing with sun-bleached sky backdrop; overlays open like an iris.

### Who it serves
| Player | Read |
|---|---|
| **Keith** | Strongest for immersion. But Keith-as-forever-GM may want more mechanical surface. |
| **Alex** | Risky. Minimal chrome is good; hidden mechanics are bad if she needs a reminder. |
| **Sebastien** | Weakest unless watcher is pinnable. Mechanics-first play is friction-taxed. |
| **James** | Strong. Narrative-maximal, distraction-minimal. |

### Risks
- Pulses are load-bearing. If a pulse is missed, Alex may act without knowing her HP dropped. Needs an audio cue + persistent-indicator backup.
- Hardest to keep genre-distinct without drifting into skeumorphism. Needs art-director pass to hold the line.

---

## Mobile stance (applies to A, B, C)

Today = bottom tab bar fallback. That's acceptable for none of these.

- **A** on mobile → stack: Dossier collapses to a pinned header; Narration is the scroll surface; World becomes a drawer from the right edge. Tabs via swipe.
- **B** on mobile → the left column becomes the whole screen; sidebar becomes a drawer from the right. Focus mode natural.
- **C** on mobile → already close to mobile-native. Narration full-bleed, bottom tray is a mobile tab bar that invokes overlays exactly as desktop.

If mobile never matters for the playgroup, document that and ship desktop-first. The dashboards and dossiers are what need work; household-reach polish is aspirational, not load-bearing (per CLAUDE.md audience rubric).

---

## Widget → Region mapping

Keeps continuity with existing components so Dev isn't rebuilding the world.

| Existing component | Direction A | Direction B | Direction C |
|---|---|---|---|
| `NarrativeView` (switchboard) | Center column | Left column | Full-bleed |
| `NarrationFocus` | Default for center | Default | Default |
| `NarrationScroll` | Alternate mode | Alternate (via scroll-back overlay) | Alternate mode |
| `NarrationCards` | Alternate mode | Alternate mode | Alternate mode |
| `CharacterPanel` (HP, resources) | Left column top | Sidebar top | Bottom tray pill (compact) |
| `CharacterSheet` | "▸ full sheet" drawer | "▸ sheet" drawer | `c` overlay |
| `InventoryPanel` | Right tab | Sidebar card | `i` overlay |
| `Automapper` + `MapOverlay` | Right tab | Sidebar card + "▸ expand" | `m` overlay |
| `KnowledgeJournal` | Right tab | Sidebar card | `k` overlay |
| `ConfrontationOverlay` + `InlineDiceTray` | Takes over L+R columns; center remains | Takes over left column; sidebar remains | Promotes bottom tray to tactical strip |
| `ScrapbookGallery` | Right tab | Sidebar card | Background parallax + `g` overlay |
| `Audio` controls | Bottom rail | Sidebar footer | Bottom tray `◍` |
| `Watcher` (OTEL/GM panel) | Right-edge slide-out | Bottom drawer, pinnable | `w` overlay, pinnable |

`JournalView` stays unmounted until handouts return as a feature.

---

## My recommendation (Klinger-note)

**Direction B — "The Folio" — is the one to prototype first.**

Reasons, in order:
1. It's the direction CLAUDE.md already ratified ("persistent themed sidebar + current-turn-focus narrative"). Don't relitigate.
2. It serves Alex best, which is the weakest constraint in the current UI — and Alex is the one most likely to disengage silently.
3. It retains Sebastien if the watcher drawer is pinnable — a small, bounded addition.
4. The compositional leap is modest: left-column-narrative-only + sidebar is a 2-week build on top of existing components, not a rewrite.
5. It exposes genre texture without depending on art-heavy chrome (C's risk).

**Prototype Direction A next** if B tests poorly for Sebastien. A has the strongest mechanical-transparency story and is still a clean silhouette.

**Hold Direction C** unless a playtest reports that the current UI "feels too much like a webpage." C is the right answer to that specific complaint and the wrong answer to everything else.

Next steps I'd propose:
- Pick a direction (or ask me for a hybrid).
- I produce high-fidelity component specs for the winning direction (fonts, spacing, state matrices per component).
- Dev (Winchester) builds a vertical slice in a genre with strong visual identity — `victoria` or `neon_dystopia` — so the genre-expression claim is tested, not assumed.
