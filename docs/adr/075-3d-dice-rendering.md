---
id: 75
title: "3D Dice Rendering — Three.js + Rapier Physics Overlay"
status: accepted
date: 2026-04-09
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [74, 79]
tags: [frontend-protocol]
implementation-status: partial
implementation-pointer: 87
---

# ADR-075: 3D Dice Rendering — Three.js + Rapier Physics Overlay

## Context

ADR-074 defines the dice resolution protocol. This ADR addresses the client-side
rendering: how dice appear, animate, and integrate with the existing React DOM UI.

### Current UI stack

- React 19 + Tailwind CSS v4
- Pure DOM rendering with SVG for tactical grids (TacticalGridRenderer)
- D3.js for dashboard charts
- Zero WebGL, Canvas, or 3D dependencies
- Animation limited to CSS `@keyframes` and Tailwind `animate-*` utilities

### Requirements

1. Physically simulated dice — real tumble, bounce, and settle (not CSS tricks)
2. Genre-pack-themed dice skins (bone, chrome, brass, neon, etc.)
3. Overlay pattern — dice float above the game UI without disrupting DOM layout
4. Multiplayer sync — all clients replay identical physics from seed + throw params
5. Lazy-loaded — zero bundle cost until first roll
6. Accessible — screen reader announcements, reduced-motion support

## Decision

### Technology: Three.js + Rapier WASM

Use Three.js for WebGL rendering and Rapier (compiled to WASM) for deterministic
rigid-body physics. Integrate via `@react-three/fiber` (R3F) and `@react-three/rapier`.

**Reference implementation:** Owlbear Rodeo's open-source dice roller
(`github.com/owlbear-rodeo/dice`). This is the only production-quality, TypeScript,
React + Three.js + Rapier dice system available. Fork as reference, not dependency.

| Component | Package | Size (gzipped) |
|-----------|---------|----------------|
| 3D rendering | three + @react-three/fiber | ~150 KB |
| Physics | @dimforge/rapier3d-compat + @react-three/rapier | ~200 KB |
| Total new bundle | | ~350 KB (lazy-loaded) |

### Why Rapier

Rapier is a Rust physics engine compiled to WASM. It is:

- **Deterministic** — same inputs produce same outputs across platforms. This is
  mandatory for multiplayer sync (ADR-074 seed-based replay).
- **Fast** — WASM execution, well within frame budget on M-series and modern browsers.
- **Familiar ecosystem** — same engine used in Rust gamedev (Bevy, etc.), conceptually
  aligned with the sidequest-api Rust backend.

Cannon-ES was considered but lacks cross-platform determinism guarantees.

### Overlay architecture

The dice canvas is a WebGL overlay positioned above the React DOM UI:

```
┌─────────────────────────────────────────┐
│  React DOM (game UI, narration, panels) │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  <Canvas> (R3F)                   │  │
│  │  position: fixed                  │  │
│  │  inset: 0                         │  │
│  │  z-index: 1000                    │  │
│  │  pointer-events: none             │  │
│  │                                   │  │
│  │  When DiceRequest arrives:        │  │
│  │    pointer-events: auto           │  │
│  │    Dice tray slides in            │  │
│  │    Player can flick               │  │
│  │                                   │  │
│  │  After DiceResult settles:        │  │
│  │    pointer-events: none           │  │
│  │    Dice fade out                  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

The canvas is `pointer-events: none` by default — all interaction passes through to
the game UI below. It becomes interactive only during an active dice roll, then
returns to passthrough after the result settles.

### Lazy loading

The entire dice module (Three.js, Rapier WASM, meshes, materials) loads via
`React.lazy()` on first `DiceRequest`. Zero cost at startup. Subsequent rolls
reuse the loaded module.

```tsx
const DiceOverlay = React.lazy(() => import('./dice/DiceOverlay'));
```

The WASM binary for Rapier loads asynchronously within the module. A brief loading
state on first roll is acceptable — subsequent rolls are instant.

### Interaction: drag-and-throw

The rolling player grabs the dice and flicks with mouse or touch:

1. `pointerdown` on dice set — grab
2. `pointermove` — track gesture direction and speed
3. `pointerup` — release, compute `ThrowParams` from gesture
4. Send `DiceThrow` to server
5. Receive `DiceResult` with seed — run Rapier simulation
6. All clients (including thrower) see identical physics

Non-rolling players see the dice appear but cannot interact — `pointer-events` is
selective per player role.

### Deterministic replay

All clients must produce identical visual results:

1. Server generates `seed: u64` and echoes `throw_params`
2. Each client initializes Rapier world with identical config
3. Dice rigid bodies created with same mass, friction, restitution
4. Initial position/velocity/angular set from `throw_params`
5. RNG seeded with `seed` for any stochastic elements
6. Rapier steps deterministically — same inputs, same settle position
7. Face-reading logic determines which face is up (same on all clients)

The seed determines the result. The throw params determine the journey.

### Genre-pack theming

Dice appearance is driven by genre pack configuration:

```yaml
# genre_packs/<genre>/dice.yaml
dice_theme:
  material: bone          # bone | chrome | brass | obsidian | neon | wood | crystal
  surface: oak            # oak | stone | glass | metal | felt — affects sound
  glow: false             # neon_dystopia: true
  color_primary: "#8B7355"
  color_accent: "#F5DEB3"
  font: runes             # runes | digital | serif | sans — number face style
```

Each material maps to a set of PBR textures (albedo, normal, roughness, metallic)
loaded from the genre pack's asset directory. Default fallback: simple white dice
with black numbers.

Sound design (dice-on-surface audio) pairs with the `surface` field — a separate
concern from the visual theme but configured alongside it.

### Cinematic moments

`RollOutcome` from ADR-074 drives visual treatment:

| Outcome | Visual |
|---------|--------|
| `CritSuccess` | Slow-motion final bounce, genre particle burst, screen edge glow |
| `Success` | Normal settle, brief highlight |
| `Fail` | Normal settle, muted palette |
| `CritFail` | Slow-motion, dramatic crack/shatter particle effect, screen shake |

`prefers-reduced-motion` disables slow-mo and particles — dice snap to final
position, result announced immediately.

### Accessibility

- `aria-live="polite"` region outside the canvas announces: "[Character] rolled
  [total] ([rolls] + [modifier]) vs DC [difficulty] — [outcome]"
- `prefers-reduced-motion`: skip animation, snap dice to result position
- Canvas is invisible to screen readers — the `aria-live` region is the only
  accessible surface
- Keyboard fallback: spacebar to throw (default force/direction) for players
  who cannot use pointer gestures

### Performance budget

| Metric | Target |
|--------|--------|
| First roll load | < 2s (lazy load + WASM init) |
| Subsequent roll start | < 16ms (one frame) |
| Physics step | < 2ms per frame at 60fps |
| Settle detection | < 3s from throw to result |
| Memory | < 50 MB for loaded dice module |
| GPU | Single WebGL context, clamped to devicePixelRatio 2 |

M3 Max will run this trivially. Floor target: any device that runs the React UI
can run the dice overlay.

## Consequences

- First significant WebGL dependency in the UI — establishes Three.js + R3F as
  the 3D rendering stack for any future needs (tactical map 3D, character portraits)
- ~350 KB added to lazy-loaded bundle (not startup)
- Genre pack schema gains `dice.yaml` — content authors can theme dice per genre
- Owlbear Rodeo reference is GPLv3 — if the UI is ever open-sourced, the dice
  module must be clean-room or the UI inherits GPL. For a personal project this
  is irrelevant; note it for future decisions.

## Alternatives Considered

### CSS 3D transforms (rejected)
Pure CSS `transform: rotateX/Y/Z` with `perspective`. No real physics, no bounce,
no settle. Looks cheap. Does not produce excitement.

### Babylon.js + Ammo.js (rejected)
The `@3d-dice/dice-box` ecosystem uses Babylon + Ammo. Heavier runtime (~11 MB),
Ammo.js lacks Rapier's determinism guarantees, no TypeScript support in dice-box.

### Pre-rendered video (rejected)
Record N dice animations, play the matching one. No player agency, no throw gesture,
obviously canned after a few rolls. Defeats the purpose.

### Canvas 2D physics (rejected)
Matter.js or similar 2D engine with top-down view. Technically simpler but loses
the 3D tumble that makes physical dice exciting. The whole point is the third
dimension.

## Implementation status (2026-05-02)

The technology stack landed exactly as specified; two architecture
sections of this ADR diverged during implementation and one feature is
not shipping. **Source of truth for current dice rendering** is
`sidequest-ui/src/dice/InlineDiceTray.tsx`,
`sidequest-ui/src/dice/DiceScene.tsx`, and
`sidequest-ui/src/components/ConfrontationOverlay.tsx` — not the §Overlay
architecture diagram or §Interaction: drag-and-throw section above.

### Live (matches spec)

- **Dependencies installed** per §Decision: `three@0.183.2`,
  `@react-three/fiber@9.5.0`, `@react-three/rapier@2.2.0`,
  `@react-three/drei@10.7.7`, `@react-spring/three@10.0.3` (all in
  `sidequest-ui/package.json`).
- **R3F Canvas + Rapier RigidBody wiring** —
  `sidequest-ui/src/dice/DiceScene.tsx, 18–22, 84` mounts a Canvas,
  imports `RigidBody` and `RapierRigidBody`, sets fixed-type ground
  with `friction={10}` and `restitution={0.3}`. Drei `Text` for face
  numbers at line 24.
- **Per-die meshes** — `sidequest-ui/src/dice/d4.ts`, `d6.ts`,
  `d10.ts`, `d12.ts`, `d20.ts`. (`d8` is not needed by the current
  game systems.)
- **Deterministic replay** infrastructure — `replayThrowParams.ts`
  exists; the §Deterministic replay seed-based contract is honored.

### Architecture pivot 1: overlay → inline tray

§Overlay architecture specified a fixed-position full-screen Canvas at
`z-index: 1000` with toggled `pointer-events`. **That design was
implemented and then removed.** Per `sidequest-ui/src/App.tsx–45`:

> "DiceOverlay overlay removed — dice now render inline in the
> Confrontation panel via InlineDiceTray. The DiceOverlay component
> and DiceSpikePage are retained..."

Current rendering: `ConfrontationOverlay.tsx` mounts `InlineDiceTray`
directly inside the confrontation panel. The Canvas stays mounted as
long as the confrontation is active (avoiding WebGL context churn) and
becomes visible only when a `DiceRequest` is in flight. The
full-screen overlay design is dead spec; `DiceOverlay.tsx` is retained
as a component but is not the production rendering path.

### Architecture pivot 2: gesture → click-and-auto-roll

§Interaction: drag-and-throw specified a `pointerdown`/`pointermove`/
`pointerup` flick-gesture pipeline with `ThrowParams` computed from
the player's gesture. **That design was abandoned.** Per the
`InlineDiceTray.tsx–11` header docstring:

> "No gestures, no drag-to-throw. The die sits idle in the tray.
> When a beat button is clicked (which creates a DiceRequest), the
> die auto-rolls with random physics params. Settle → face reported
> → result shown inline."

The motivating "tactile flick" concept that opened this ADR is gone —
replaced by a button click and automated roll. `useDiceThrowGesture.ts`
exists but is not wired through `InlineDiceTray`. The throw params
the server still wants per ADR-074 are now generated automatically,
not from a player gesture.

### Dark / restoration owed (tracked in [ADR-087](087-post-port-subsystem-restoration-plan.md))

- **Genre-pack `dice.yaml` theming.** §Genre-pack theming spec'd a
  per-genre `material` (bone | chrome | brass | obsidian | neon | wood
  | crystal), `surface`, `glow`, `color_primary`, `color_accent`,
  `font` config feeding PBR textures from the pack's asset directory.
  `find sidequest-content -name dice.yaml` returns **zero** hits —
  not shipping in any genre pack. Polish gap, not load-bearing.
- **Cinematic moments / accessibility / reduced-motion / keyboard
  fallback** — §Cinematic moments and §Accessibility specified
  slow-motion crit treatments, `aria-live` announcements,
  `prefers-reduced-motion` snap-to-result, and keyboard-spacebar
  throw fallback. Implementation status of each is **TBD on next
  deeper audit** — they require detailed UI inspection beyond this
  hygiene pass.

### Source of truth

For the current dice-rendering contract, defer to:

- **Active rendering:** `sidequest-ui/src/dice/InlineDiceTray.tsx`
- **Scene:** `sidequest-ui/src/dice/DiceScene.tsx`
- **Mount point:** `sidequest-ui/src/components/ConfrontationOverlay.tsx`
- **Deterministic replay:** `sidequest-ui/src/dice/replayThrowParams.ts`

Not the §Overlay architecture diagram or §Interaction prose above.
ADR text is the original 2026-04-09 design intent; the running
implementation has diverged on the architecture sections while
preserving the technology choice and protocol contract.

## Amendment 2026-05-28 — Original §Architecture / §Interaction marked superseded

Re-confirming the 2026-05-02 status against current code, and flagging the two
upstream design sections as **superseded design** so a reader doesn't mistake
them for the running shape:

- **§Overlay architecture** (the fixed-position full-screen `<Canvas>` at
  `z-index: 1000` with toggled `pointer-events`) is **superseded.** Dice now
  render **inline inside the Confrontation panel** via `InlineDiceTray`. The
  `App.tsx` header (`sidequest-ui/src/App.tsx`) records the overlay's
  removal; `ConfrontationOverlay.tsx` is the live mount point.
- **§Interaction: drag-and-throw** (the `pointerdown`/`pointermove`/`pointerup`
  flick-gesture pipeline) is **superseded.** The current shape is a beat-button
  click that triggers an **auto-roll** with random physics params — see the
  `InlineDiceTray.tsx` docstring ("No gestures, no drag-to-throw ... the
  die auto-rolls"). `useDiceThrowGesture.ts` exists but is not wired through
  `InlineDiceTray`.

No new code findings beyond the 2026-05-02 audit — this amendment only elevates
the divergence note so the two original sections read as dead design.
**Source of truth remains** `sidequest-ui/src/dice/InlineDiceTray.tsx`,
`DiceScene.tsx`, and `components/ConfrontationOverlay.tsx`, per the
§Implementation status section above. The technology stack (Three.js + Rapier
via R3F) and the ADR-074 seed-based replay contract are unchanged and live.

## Amendment (2026-05-31): Dice Theming Is a Hardcoded Client Map, Not Pack YAML

The 2026-05-02 status and 2026-05-28 amendment both recorded that the
§Genre-pack theming `dice.yaml` config **never shipped** (`find sidequest-content
-name dice.yaml` returns zero hits). What neither prior note captured: **per-genre
dice theming did ship — as a hardcoded client-side TypeScript map, not as
content.** The capability exists; it just lives in the frontend bundle instead of
in pack YAML, which is a direct inversion of this ADR's "content authors can theme
dice per genre" §Consequences bullet.

### What is actually live

The production theme source is a `GENRE_DICE_THEMES` record literal in
`sidequest-ui/src/dice/InlineDiceTray.tsx–134`, keyed by genre slug. It carries
**11 genre entries** — `caverns_and_claudes`, `elemental_harmony`, `low_fantasy`,
`tea_and_murder` (parchment archetype); `neon_dystopia`, `space_opera` (terminal
archetype); `mutant_wasteland`, `road_warrior`, `spaghetti_western`, `pulp_noir`,
`heavy_metal` (rugged archetype). Each entry is a `DiceTheme` literal of:

- `dieColor` / `labelColor` — die body and number-face hex colors
- `roughness` / `metalness` — PBR surface params (the same physical knobs the
  ADR's `material: bone | chrome | brass | …` taxonomy was meant to abstract)
- `normalMap` — a hardcoded path under `/textures/dice/*.jpg` (e.g.
  `scratched-plastic-normal.jpg`, `brushed-metal-normal.jpg`), `normalScale`
- `labelFont` — a hardcoded `/fonts/*.ttf` path (EBGaramond, Orbitron, Oswald,
  AmericanTypewriter, Bastarda-K), chosen to match the UI chrome archetype

Theme resolution is `InlineDiceTray.tsx` —
`(genreSlug && GENRE_DICE_THEMES[genreSlug]) || DEFAULT_DICE_THEME` — a synchronous
lookup against the inlined record, with `DEFAULT_DICE_THEME` (from `@local/dice-lib`)
as the fallback for any genre not in the map. The `genreSlug` prop
(`InlineDiceTray.tsx`) is the only input; nothing reads pack config.

So the table in §Genre-pack theming is half-right and half-wrong: the **per-genre
visual differentiation it promised is real and shipping**, but the **delivery
mechanism it specified (`dice.yaml` → PBR textures from the pack asset dir) is
not** — the same data is instead literal-encoded in client TypeScript.

### Authoring-model consequence (the real cost)

This is **drift from ADR-075's pack-YAML design.** The original §Genre-pack theming
section and §Consequences bullet ("Genre pack schema gains `dice.yaml` — content
authors can theme dice per genre") promised that dice appearance would be **content,
editable by a pack author without touching engine or client code.** The shipped
shape breaks that promise:

- **Dice theming is not authorable as content.** To add a theme for a new genre, or
  retune an existing one (color, roughness, normal map, font), an author must edit
  `GENRE_DICE_THEMES` in `InlineDiceTray.tsx`, i.e. write **frontend TypeScript** and
  ship a **UI build + deploy.** There is no YAML, no override, no "Yes, And" path.
- **This is exactly the failure CLAUDE.md names for the Jade authoring requirement:**
  "If authoring what a table wants requires a server change, that's a failure of the
  content surface." Here it's a *client* change, but the failure mode is identical —
  a non-Keith author (Jade, extending `space_opera/perseus_cloud`) cannot give her
  world its own dice look through the paste-new-stuff-in / PR-on-content path; she'd
  need a frontend code change in a different repo.
- **It is also genre-tier-locked, not world-tier.** The map keys on **genre slug**
  only, so the per-world flavor split (MEMORY: "ALL flavor lives in worlds, not
  genre") cannot express a world-specific dice skin even in principle — there is no
  world axis in the lookup at all.

The prior amendments treated `dice.yaml` as a clean "not shipping" polish gap. It
isn't clean: a **client-hardcoded alternative is live in its place**, which means the
*feature* is done but the *authoring surface* the ADR called for is absent and was
quietly routed around. Whether this was a deliberate "ship the look now, wire the
content surface later" call or accreted during the inline-tray pivot, the standing
cost is that dice theming sits on the wrong side of the engine/content line.

### Restoration owed

Re-pointing dice theming at pack/world config — a `dice` block in pack (and
world-override) YAML, loaded and threaded to `InlineDiceTray` as the `DiceTheme`
prop, with `GENRE_DICE_THEMES` demoted to a built-in default table — remains owed if
the content-authoring surface is to match this ADR's intent. Tracked alongside the
other dark items in [ADR-087](087-post-port-subsystem-restoration-plan.md).

**Source of truth for current dice theming:** `GENRE_DICE_THEMES` at
`sidequest-ui/src/dice/InlineDiceTray.tsx–134` and the resolution at
`InlineDiceTray.tsx`. The technology stack and ADR-074 replay contract remain
unchanged and live.
