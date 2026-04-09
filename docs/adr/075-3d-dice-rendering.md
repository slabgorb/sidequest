# ADR-075: 3D Dice Rendering — Three.js + Rapier Physics Overlay

## Status

Proposed

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
