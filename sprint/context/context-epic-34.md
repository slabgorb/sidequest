# Epic 34: 3D Dice Rolling System — MVP

## Why This Epic Exists

SideQuest resolves confrontation beats silently. A player picks a beat, `BeatDef.stat_check`
names the ability, `metric_delta` is applied, and the narrator describes an outcome that has
no visible randomness. Playtests surfaced a single loud complaint: **players want to roll
their own dice.** The tactile ritual of rolling — anticipation, agency, consequence — is the
most visible tabletop ritual missing from the product. Every other RPG convention SideQuest
ships (sealed letters, turn order, stat blocks, genre packs) makes the absence of dice
more conspicuous, not less.

The fix is not a button that says "ROLL" and shows a number. The fix is a physical throw
the player performs with a drag gesture, tumbling dice rendered in real physics, watched
live by every other player in the session, with the result shaping the AI narrator's tone.
The feel of the throw is the feature. A fake result animation would fail this epic as
surely as a plain random number would.

Three constraints shape every decision in this epic:

1. **Server authority is non-negotiable.** Clients render, they do not decide. The throw
   gesture controls animation aesthetics (angle, force, spin path) but not the outcome.
   The outcome is a server-generated seed + server-side RNG resolution. Trivially
   cheat-resistant in multiplayer. See ADR-074.
2. **Deterministic physics replay across clients.** Every connected client must run the
   exact same Rapier simulation from the same seed + throw params and see dice settle on
   the same faces. This rules out non-deterministic physics engines (cannon-es) and forces
   Rapier WASM. See ADR-075.
3. **Sealed letter turn flow must not warp.** Dice are a sub-phase of the reveal phase,
   not a new turn state. DC stays hidden during commitment, revealed at throw time. The
   "I need a 16..." moment depends on that gap.

## Architecture

### Data Flow

```
Sealed phase: player picks beat (no DC visible) ──→ ActionReveal
                                                         ↓
                                            Narrator sets the scene
                                                         ↓
                                            Server: dispatch_beat_selection
                                                         ↓
                                            DiceRequest (DC revealed NOW)
                                                         ↓
                                            Broadcast to all clients
                                                         ↓
                                            Rolling client: drag-and-flick → ThrowParams
                                                         ↓
                                            DiceThrow (client → server)
                                                         ↓
                                            Server: resolve_dice(pool, mod, DC, seed) → ResolvedRoll
                                                         ↓
                                            DiceResult (server → broadcast all clients)
                                                         ↓
                                            All clients: Rapier sim from seed + throw_params
                                                         ↓
                                            Narrator: RollOutcome shapes result prose
                                                         ↓
                                            NarrationPayload (outcome-tinted)
```

### Layer Responsibilities

| Layer | Crate | Responsibility |
|-------|-------|----------------|
| Wire protocol | `sidequest-protocol` | `DiceRequestPayload`, `DiceThrowPayload`, `DiceResultPayload`, `DieSpec`, `DieSides`, `DieGroupResult`, `RollOutcome`, `ThrowParams`. Validated `TryFrom` on deserialization. **Done in 34-2.** |
| Pure game logic | `sidequest-game` (new `dice.rs`) | `resolve_dice(dice, modifier, difficulty, seed) -> Result<ResolvedRoll, ResolveError>`. Pure function. Seeded `StdRng`. No protocol payloads, no I/O, no telemetry. **34-3.** |
| Dispatch orchestration | `sidequest-server` (`dispatch/beat.rs` + new dispatch path) | Intercept beat selection, generate seed, emit `DiceRequest`, await `DiceThrow`, call `resolve_dice`, compose `DiceResultPayload`, broadcast. Holds the OTEL spans. **34-4, 34-8, 34-11.** |
| Narrator integration | `sidequest-agents` / dispatch prompt context | Inject `RollOutcome` into the narrator prompt zone so outcome tone is visible to Claude. **34-9.** |
| Client rendering | `sidequest-ui` (new `dice/` directory) | Lazy-loaded Three.js + Rapier overlay. Drag-and-flick gesture → `ThrowParams`. Seed-driven deterministic replay. Accessibility affordances. **34-5, 34-6, 34-7, 34-10.** |

### Key Types (from 34-2, already on main)

Defined in `sidequest-api/crates/sidequest-protocol/src/message.rs`:

- **`DiceRequestPayload`** — validated wire type. Rejects empty dice pool, blank stat,
  `difficulty == 0` at the deserialization boundary via a private `Raw` intermediary.
- **`DiceThrowPayload`** — rolling player submits throw gesture. Echo-only for animation.
- **`DiceResultPayload`** — validated wire type. Enforces `DieGroupResult.faces.len() ==
  spec.count.get()` on deserialization. `total: i32` (allows negative with penalties).
- **`DieSpec { sides: DieSides, count: NonZeroU8 }`** — one group in a pool. Max 255
  dice per group; zero rejected at type level.
- **`DieSides`** — bounded enum (D4/D6/D8/D10/D12/D20/D100) with `#[non_exhaustive]` and
  `#[serde(from = "u32")]` → `Unknown` forward-compat fallback. `faces() -> Option<u32>`
  returns `None` for `Unknown`.
- **`DieGroupResult { spec: DieSpec, faces: Vec<u32> }`** — resolved face values, keyed
  to the originating `DieSpec` so consumers can attribute rolls back to their group.
- **`RollOutcome`** — `CritSuccess / Success / Fail / CritFail` + `#[serde(other)] Unknown`
  forward-compat fallback. `#[non_exhaustive]`. Intentionally **not** `Eq/Hash` (deriving
  those on a non-exhaustive enum breaks wire stability).
- **`ThrowParams { velocity, angular, position }`** — drag-and-flick gesture capture.
  Animation aesthetics only; outcome is independent.

### Server Authority Model

The client's throw gesture controls animation — angle, force, tumble path — but NOT the
outcome. The server:

1. Receives `DiceThrow` with gesture params.
2. Generates a seed (OS entropy or session-derived).
3. Calls `sidequest_game::dice::resolve_dice(pool, modifier, DC, seed)`, which runs
   `StdRng::seed_from_u64(seed)` and produces the `ResolvedRoll`.
4. Composes `DiceResultPayload` from the resolved faces, outcome, total, seed, and the
   echoed `throw_params`.
5. Broadcasts `DiceResult` to every client.

All clients run identical Rapier physics from the same seed + throw params, producing
identical visual animation. The seed determines which face lands up. The throw params
determine the path to get there. Determinism at both the RNG layer (StdRng is ChaCha-backed
and portable across platforms for a pinned `rand` minor version) and the physics layer
(Rapier WASM is deterministic by design) keeps every client in sync without post-hoc
correction.

### Resolver Interface (34-3)

Locked via architect consultation on 2026-04-11:

```rust
// sidequest-api/crates/sidequest-game/src/dice.rs
use sidequest_protocol::{DieGroupResult, DieSpec, RollOutcome};
use std::num::NonZeroU32;

pub struct ResolvedRoll {
    pub rolls: Vec<DieGroupResult>,
    pub total: i32,
    pub outcome: RollOutcome, // NEVER RollOutcome::Unknown
}

pub fn resolve_dice(
    dice: &[DieSpec],
    modifier: i32,
    difficulty: NonZeroU32,
    seed: u64,
) -> Result<ResolvedRoll, ResolveError>;

#[non_exhaustive]
pub enum ResolveError {
    UnknownDie, // any DieSpec.sides == DieSides::Unknown
    EmptyPool,  // defensive — wire layer already rejects this
}
```

Deliberately narrower than `DiceRequestPayload` for testability. The dispatch layer
composes `DiceResultPayload` from `ResolvedRoll` + echo fields (request_id,
rolling_player_id, character_name, throw_params). Narrowness keeps 34-3's tests free of
wire-type ceremony.

### Crit Semantics (34-3, locked by Keith 2026-04-11)

> "No crits on anything but 20's for now."

- `CritSuccess` fires iff **any d20 in the pool rolls a face of 20**, regardless of DC,
  modifier, or other dice in the pool.
- `CritFail` fires iff **any d20 in the pool rolls a face of 1**, with the same
  unconditionality. If both a 20 and a 1 appear in the same pool (hypothetical 2d20),
  `CritSuccess` wins.
- **Non-d20 dice never trigger crit classification.** A pool with no d20 resolves on
  `total vs difficulty` only — outcomes are `Success` or `Fail`.
- The resolver must NEVER emit `RollOutcome::Unknown`. Unknown is a forward-compat
  deserialization fallback; generating it in code would poison downstream consumers.

This is narrower than a strict reading of the `RollOutcome::CritSuccess` docstring
("natural max on the primary die"). TEA logs it as a design deviation in 34-3. Future
stories may relax this (per-group crit tables, modifier-gated crits, etc.) — do not
overbuild for that now.

### MVP Scope Boundary (Phase 1)

**In scope for Sprint 2 (this epic):**

- Single resolution model: d20 + modifier vs DC
- Pool support at the type level (resolver accepts `&[DieSpec]`), but the only production
  caller in Phase 1 constructs singleton-d20 pools
- All confrontation beats with `stat_check` trigger dice (no selective rolling yet —
  that's a playtest-driven iteration)
- Single default dice skin (white with black numbers)
- No timeout — dice tray persists until the player throws
- One RollOutcome → narrator prompt injection path (no per-outcome prompt templates)
- OTEL spans on all three dispatch points

**Deferred to future epics:**

- Genre-pack dice themes (PBR materials, `dice.yaml` schema)
- Multi-die pools in production use (4d6 damage rolls, 2d10 percentile)
- Contested rolls (two sealed letters → simultaneous dice tray)
- Advantage / disadvantage (2d20 take-highest / take-lowest)
- Per-player dice customization
- Dice history / roll log / statistics
- Exploding dice, reroll mechanics, luck points

## Guardrails

1. **Server authority is absolute.** The client's throw gesture must never influence
   the outcome. If a test proves the rolling client can bias results, the PR fails review.
2. **Determinism is load-bearing.** Every dice path must be deterministic from `(dice, modifier,
   difficulty, seed)`. No `rand::rng()`, no OS entropy inside `resolve_dice`, no wall-clock
   timestamps in the pipeline. Seed sourcing is a dispatch-layer concern; resolution is
   pure.
3. **Single RNG source.** `rand::rngs::StdRng::seed_from_u64` matches existing codebase
   patterns (`scenario_state.rs`, `theme_rotator.rs`, `conlang.rs`). **Do not introduce
   `ChaCha8Rng`, `rand_chacha`, or a second seeded RNG** — that splits reproducibility
   across modules and is exactly the risk flagged in the 34-3 SM assessment.
4. **No stub dispatch.** The resolver must have at least one non-test consumer when
   34-3 ships (wiring-check gate). But that consumer **may not** be a stub
   `dispatch_dice()` that calls `resolve_dice` without broadcasting. If full dispatch
   isn't possible in 34-3 (it isn't — that's 34-4), the wiring lives in an integration
   test under `sidequest-server/tests/` that round-trips through real protocol types.
   Half-wired code is a lie; a wiring test is the truth.
5. **OTEL on every dispatch decision.** Per project rules. `dice.request_sent`,
   `dice.throw_received`, `dice.result_broadcast` — all three land in 34-11 with the
   OTEL spans visible on the GM panel. 34-3 is pure logic and emits nothing; adding
   tracing to a pure function couples it to a concern it doesn't own.
6. **`RollOutcome::Unknown` is wire-only.** It exists as a `#[serde(other)]` fallback for
   forward compat across protocol versions. Server code must never **produce** it. Every
   resolver test must assert `outcome != RollOutcome::Unknown`.
7. **Negative totals pass through.** `DiceResultPayload.total: i32` is signed. The
   resolver must not clamp to zero. The narrator may want to distinguish "failed by 19"
   from "failed by 1," and clamping destroys that information.
8. **Protocol crate is frozen.** `sidequest-protocol/CLAUDE.md` says "COMPLETE — Do Not
   Rewrite." 34-3 and beyond add zero fields to protocol types. If new fields are
   needed, a new ADR lands first and the protocol version bumps.
9. **Sealed letter turn flow is invariant.** Dice are a sub-phase of reveal, not a new
   turn state. `TurnBarrier` is untouched. `ActionReveal` is untouched. If a dice change
   requires modifying the barrier or reveal flow, the design is wrong.
10. **Lazy-loaded UI chunk.** The dice overlay bundle (Three.js + Rapier WASM, ~350 KB
    gzipped) must not load until a `DiceRequest` arrives. Zero bundle cost for the
    action screens. See ADR-075.
11. **Seed must fit in JS safe integer range.** `DiceResultPayload.seed` is `u64` on the
    wire but `number` in the UI (IEEE 754 double). Seeds above `Number.MAX_SAFE_INTEGER`
    (~9×10^15) silently truncate via `JSON.parse`, producing a different seed on the
    client than the server used. This breaks deterministic Rapier replay (34-7). The
    server's seed generation (34-4 dispatch) must bound to `0..2^53-1`, or the wire
    type must change to string + BigInt on the client. Found in 34-5 review.
12. **UI RollOutcome needs Unknown variant.** The Rust enum has `#[serde(other)] Unknown`
    for forward-compat. The TS `RollOutcome` union currently lacks it — a newer server
    outcome would silently render as "Fail". Add `"Unknown"` to the union and a fallback
    branch in DiceOverlay before shipping new outcome variants. Found in 34-5 review.

## Story Dependency Chain

```
Phase 0: Spike (done)
34-1  Owlbear dice fork spike (ui, done)

Phase 1: Protocol + Resolver
34-2  DiceRequest/DiceThrow/DiceResult protocol types (api, done)
34-3  Dice resolution engine — d20+mod vs DC, RollOutcome, seed generation (api, current)

Phase 2: Server Dispatch
34-3 ──→ 34-4  Dispatch integration (beat selection emits DiceRequest, awaits DiceThrow)
34-4 ──→ 34-8  Multiplayer dice broadcast via SharedGameSession
34-4 ──→ 34-9  Narrator outcome injection — RollOutcome shapes narration tone

Phase 3: Client Rendering
34-5  Three.js + Rapier dice overlay (lazy-loaded React component)     ← parallel with 34-4
34-5 ──→ 34-6  Drag-and-throw interaction — gesture capture
34-5 ──→ 34-7  Deterministic physics replay — seed-based Rapier sim

Phase 4: Integration + Accessibility + Telemetry
34-4 + 34-7 ──→ 34-10  Dice accessibility (aria-live, reduced-motion, keyboard throw)
34-4 ──→ 34-11  OTEL dice spans — request_sent, throw_received, result_broadcast
all ─────────→ 34-12  Playtest validation — end-to-end multiplayer dice session
```

Critical path for the sprint goal ("Multiplayer Works For Real"): **34-3 → 34-4 → 34-8**.
UI work (34-5/6/7) can parallelize with server dispatch once 34-3 lands. Narrator injection
(34-9) and OTEL (34-11) slot in after 34-4. Playtest validation (34-12) is the epic exit gate.

## Key Files

| File | Role |
|------|------|
| `docs/adr/074-dice-resolution-protocol.md` | Protocol decision record (wire types, turn flow, server authority) |
| `docs/adr/075-3d-dice-rendering.md` | Rendering decision record (Three.js + Rapier WASM overlay, lazy-load strategy) |
| `sprint/planning/prd-dice-rolling.md` | Full product requirements (success criteria, MVP/Growth/Mature phases, accessibility, metrics) |
| `sidequest-api/crates/sidequest-protocol/src/message.rs` | `GameMessage::DiceRequest/DiceThrow/DiceResult` variants (line 362+); `DiceRequestPayload`, `DiceResultPayload`, `DiceThrowPayload`, `DieSpec`, `DieSides`, `DieGroupResult`, `RollOutcome`, `ThrowParams` (line 1456+); validated deserialization via `dice_payload_raw` module (line 1745+) |
| `sidequest-api/crates/sidequest-protocol/src/dice_protocol_story_34_2_tests.rs` | 34-2 test suite — wire round-trip, forward-compat, validation errors. Reference for 34-3 test style. |
| `sidequest-api/crates/sidequest-game/src/dice.rs` | **NEW in 34-3.** `resolve_dice`, `ResolvedRoll`, `ResolveError`. Pure function. |
| `sidequest-api/crates/sidequest-game/Cargo.toml` | Already depends on `sidequest-protocol` and `rand = { workspace = true }` — no new dependencies for 34-3 |
| `sidequest-api/crates/sidequest-server/tests/` | **NEW in 34-3.** `dice_resolver_wiring_34_3.rs` — integration test proving `sidequest_game::dice::resolve_dice` is reachable from the server crate |
| `sidequest-api/crates/sidequest-server/src/dispatch/beat.rs` | `dispatch_beat_selection` — where 34-4 intercepts beat selection, generates seed, and emits `DiceRequest` |
| `sidequest-api/crates/sidequest-server/src/dispatch/mod.rs` | Dispatch pipeline — where 34-4 hooks dice resolution between beat selection and narration |
| `sidequest-api/crates/sidequest-server/src/shared_session.rs` | `SharedGameSession` — where 34-8 broadcasts `DiceResult` across multiplayer clients |
| `sidequest-api/crates/sidequest-agents/src/` | Narrator prompt context — where 34-9 injects `RollOutcome` for tone shaping |
| `sidequest-api/crates/sidequest-telemetry/src/` | OTEL span definitions — where 34-11 adds `dice.request_sent` / `dice.throw_received` / `dice.result_broadcast` |
| `sidequest-ui/src/dice/` | **NEW in 34-5.** Three.js + Rapier dice overlay React component, lazy-loaded |
| `sidequest-ui/src/hooks/` | **NEW in 34-6.** `useDiceThrowGesture` — drag-and-flick → `ThrowParams` capture |
| `sidequest-api/Cargo.toml` | `rand = "0.9"` workspace dep (line 57) — already in place, no change needed |

## Testing Strategy

1. **Pure-function unit tests (34-3).** `resolve_dice` takes a fixed seed; every test
   asserts exact face values and exact outcome. Covered: DC boundary (total == DC is
   Success, total == DC - 1 is Fail), negative modifier producing negative total,
   singleton d20 crit success (seed forced to produce face 20), singleton d20 crit fail
   (seed forced to produce face 1), mixed pool where d20 crits but d6s don't, pure
   non-d20 pool that never crits, empty pool returning `Err(EmptyPool)`, Unknown die
   returning `Err(UnknownDie)`, determinism (same seed twice → identical output over 100
   iterations), distinct seeds diverge.
2. **Wiring integration test (34-3).** `sidequest-server/tests/dice_resolver_wiring_34_3.rs`
   constructs a full `DiceRequestPayload`, feeds its fields into `resolve_dice`, composes
   a `DiceResultPayload`, and round-trips it through serde. Proves server ↔ game ↔
   protocol reachability without touching `beat.rs`.
3. **Dispatch integration tests (34-4).** Full path: mock beat selection, verify
   `DiceRequest` emitted with correct DC, simulate `DiceThrow` receipt, verify
   `DiceResult` broadcast with expected outcome.
4. **Multiplayer broadcast tests (34-8).** Two-client harness. Rolling player throws;
   verify watcher client receives identical `DiceResult`.
5. **Deterministic physics replay tests (34-7).** Same seed + throw params across two
   client instances produces pixel-identical settled faces.
6. **OTEL assertion tests (34-11).** Verify every dispatch decision emits the expected
   span with the expected fields.
7. **Playtest validation (34-12).** Real multiplayer session with Keith + friends. Feel
   check: does the throw feel good? Does the DC reveal create tension? Do crit moments
   earn reactions?

## Key Decisions

- **StdRng, not ChaCha8Rng.** Matches codebase convention. Single source of reproducibility.
- **Resolver is a pure function over `&[DieSpec]`, not `&DiceRequestPayload`.** Testability
  over convenience. Dispatch layer composes the payload from echo fields.
- **Crit rule: only d20s crit, unconditionally on 20 or 1.** Keith's call, 2026-04-11.
  Narrower than the protocol docstring; logged as a design deviation in 34-3.
- **No per-group crit tables, no modifier-gated crits, no advantage/disadvantage in
  Phase 1.** Deliberate scope discipline. These are playtest-driven feature requests;
  ship the MVP first.
- **Seed sourcing is 34-4's problem, not 34-3's.** Keeps the resolver pure and
  test-exact. 34-4 can choose OS entropy, session state hash, or something else —
  34-3 doesn't care.
- **OTEL lives in the dispatch layer.** Pure functions stay pure.

## PRD / ADR References

- Full PRD: `sprint/planning/prd-dice-rolling.md`
- Protocol ADR: `docs/adr/074-dice-resolution-protocol.md`
- Rendering ADR: `docs/adr/075-3d-dice-rendering.md`
- Reference implementation: Owlbear Rodeo dice roller (`github.com/owlbear-rodeo/dice`),
  forked as reference for 34-5 (not a dependency)
