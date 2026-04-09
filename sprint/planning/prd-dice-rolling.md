---
stepsCompleted: ["step-01-initialization", "step-02-discovery", "step-03-success", "step-04-journeys", "step-05-domain-skipped", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish", "step-12-complete"]
inputDocuments:
  - docs/adr/074-dice-resolution-protocol.md
  - docs/adr/075-3d-dice-rendering.md
  - docs/architecture.md
  - docs/api-contract.md
documentCounts:
  briefs: 0
  research: 0
  projectDocs: 2
  adrs: 2
classification:
  projectType: real-time-multiplayer-web-app
  domain: gaming-tabletop-rpg
  complexity: high
  projectContext: brownfield
workflowType: 'prd'
---

# Product Requirements Document — SideQuest 3D Dice Rolling System

**Author:** Keith Avery
**Date:** 2026-04-08
**ADRs:** [074-dice-resolution-protocol](../../docs/adr/074-dice-resolution-protocol.md), [075-3d-dice-rendering](../../docs/adr/075-3d-dice-rendering.md)

## Executive Summary

SideQuest is a multiplayer AI-driven tabletop RPG. Players currently submit actions via sealed letter turns and receive AI-generated narration. Mechanical resolution (confrontation beats) is silent — stats apply directly with no visible randomness.

Players want to roll their own dice. The ritual of rolling — anticipation, agency, consequence — is the most visible missing piece of the tabletop experience.

**What we're building:** A server-authoritative 3D dice rolling system integrated into the sealed letter turn flow. Players commit actions blind, then throw physical dice during the reveal phase. All players watch the roll. The outcome shapes the AI narrator's prose.

**Differentiator:** No existing tool combines 3D physics dice, AI narration, sealed letter turns, and genre-themed aesthetics. VTTs have dice but no AI. AI dungeons have narration but no dice. SideQuest has both.

**Primary use case:** Keith and friends playing together — voice chat on Discord, game in browser. Multiple real players, real sessions. The feel of the throw is the make-or-break.

## Success Criteria

### User Success

- **"I need a 16..." moment** — Player commits action blind (sealed letter), DC reveals with the dice tray. The gap between commitment and knowledge creates tension. Success = players vocalize the number they need before throwing.
- **Table-eruption moment** — Crit success/fail with visual treatment, all players watching the same roll. Success = multiplayer spectators react to each other's rolls.
- **Tactile satisfaction** — Drag-and-throw gesture feels physical. Dice tumble, bounce, settle with real physics. Success = players prefer throwing dice over clicking a button.

### Business Success

- **Feature completeness** — The game feels like a game, not a chat interface. Dice rolling is the most visible missing RPG ritual.
- **Differentiation** — No other AI RPG tool has 3D dice with physics integrated into AI narration.
- **Playtest engagement** — Players stay longer and return more when mechanical moments have ceremony.

### Measurable Outcomes

- Players choose to throw dice (drag gesture) rather than requesting an auto-roll shortcut
- Multiplayer sessions show concurrent spectator engagement during reveal phase rolls
- Zero desync between client physics replays (deterministic verification)
- Technical performance targets met (see Non-Functional Requirements)

## Product Scope

### MVP (Phase 1)

- 3 new WebSocket message types (DiceRequest, DiceThrow, DiceResult) per ADR-074
- Three.js + Rapier WASM overlay in sidequest-ui, lazy-loaded per ADR-075
- Drag-and-throw interaction for the rolling player
- Server-authoritative resolution with seed-based deterministic replay
- d20 + modifier vs DC (single resolution model)
- Integration with confrontation beat system (stat_check triggers DiceRequest)
- DC hidden during sealed phase, revealed at roll time
- All confrontation beats with stat_check trigger dice (defer selective rolling to playtesting)
- No timeout — dice tray persists until player throws
- RollOutcome enum (CritSuccess, Success, Fail, CritFail) fed to narrator for tone shaping
- Single default dice skin (white with black numbers)
- Accessibility: aria-live region, prefers-reduced-motion snap, keyboard spacebar throw
- OTEL spans: dice.request_sent, dice.throw_received, dice.result_broadcast

### Growth (Phase 2)

- Genre-pack dice themes (dice.yaml schema, PBR materials per genre)
- Sound design (dice-on-surface audio matched to genre surface material)
- Slow-motion cinematics on crit success/fail
- Contested rolls via narrator GM call (two simultaneous DiceRequests)
- Dice pool visualization (multiple dice tumbling together, one gesture)
- Selective beat-to-roll mapping based on playtesting (requires_roll flag on BeatDef)

### Vision (Phase 3)

- Genre-configurable resolution systems (2d6, d100, dice pools)
- Dice tower animations (genre-themed: castle, neon tube, mineshaft)
- Persistent player dice collections (cosmetic progression)
- Narrator-called ad hoc rolls outside confrontation
- Pre-warm dice module on game connect

## User Journeys

### Journey 1: The Rolling Player — Success Path

Kira is playing a rogue in a low_fantasy session. Three players, sealed letter turns. She picks "Pick the Lock" from the confrontation beats — committing blind. She doesn't know the DC.

Letters reveal. The narrator describes: "The iron lock is ancient, corroded but stubborn. Kira's fingers find the keyhole..."

The dice tray slides in. She sees: **DC 15 — Dexterity +3 — you need a 12.** Her stomach drops — doable but not guaranteed.

She grabs the d20, flicks. The die tumbles across the tray, bounces off the wall, settles — **17**. Total: 20. Success. The narrator continues: "...and the tumblers yield with a satisfying click."

The other two players saw the whole thing.

### Journey 2: The Spectating Player — Multiplayer Tension

Marcus is watching Kira's letter open. He chose "Guard the Hallway" — no check needed for his action. But Kira's lock pick determines whether they get through.

He sees the dice tray appear on Kira's side. DC 15. He sees her d20 tumble. He's leaning in. 17 — success. Relief. His hallway guard wasn't wasted.

Next letter opens — it's his. No dice needed, the narrator just describes his watchful stance. Clean, quick. Not every action needs ceremony.

### Journey 3: The Rolling Player — Crit Fail

Same session, later encounter. Kira picks "Disarm the Trap." Letters reveal. DC 18 — Dexterity +3 — needs a 15. Tight.

She throws. The die bounces, slows... **natural 1**. CritFail. The narrator shifts tone: "The mechanism snaps. Kira jerks back, but not fast enough — a needle finds her thumb."

The crit fail visual treatment signals disaster before the narration arrives. The ceremony makes the failure memorable, not frustrating.

### Journey 4: The GM — Observability

Keith has the GM panel open. OTEL dashboard shows dice.request_sent spans — every roll, DC, modifier, outcome visible. He notices the narrator writes dramatic narration for successes but bland text for failures.

The dice system feeds RollOutcome to the narrator prompt, but the narrator isn't using it well for CritFail. This is visible because OTEL spans show outcome and narration side-by-side. Without dice OTEL, this quality gap would be invisible.

### Journey-to-Requirement Traceability

| Journey | Requirements Revealed |
|---------|----------------------|
| Rolling Player (success) | FR1-FR7, FR10-FR11, FR13, FR17-FR19 |
| Spectating Player | FR8-FR9, FR14-FR16 |
| Rolling Player (crit fail) | FR3 (RollOutcome), FR17 (narrator tone) |
| GM observability | FR23-FR24 |

### Design Decision: Contested Rolls

Contested rolls (two players' sealed letters conflict) are handled narratively via GM call, not as a protocol-level feature. The narrator decides when to call for opposed checks and emits two DiceRequests. Growth scope — the MVP protocol supports it naturally without special-casing.

## Innovation & Novel Patterns

1. **Genre-themed physics dice in an AI RPG** — No AI dungeon tool has physical dice rolling. VTTs (Roll20, Foundry) have 3D dice but no AI narrator integration. SideQuest combines both.

2. **Deterministic WASM physics for multiplayer sync** — Rapier's deterministic simulation seeded server-side so all clients replay identical physics. Competitive game networking technique applied to tabletop RPG.

3. **DC-reveal-at-roll-time in sealed letter turns** — Two-beat tension arc (commit blind, see DC at throw) doesn't exist in any VTT. Tabletop GMs do this naturally but no digital tool formalizes it at protocol level.

4. **Narrator tone shaped by roll outcome** — RollOutcome fed back to AI narrator so crits produce different prose tone. Closes the loop between physical interaction and AI-generated narrative.

### Competitive Landscape

| Tool | 3D Dice | AI Narrator | Sealed Turns | Genre Themes | Roll-to-Narration |
|------|---------|-------------|--------------|--------------|-------------------|
| Roll20 | Yes | No | No | No | No |
| Foundry VTT | Yes (mod) | No | No | Limited | No |
| Owlbear Rodeo | Yes | No | No | No | No |
| AI Dungeon | No | Yes | No | No | No |
| SideQuest | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

### Validation & Risk

**Validation:** Do players choose to throw (drag gesture) rather than requesting an auto-roll shortcut? Do spectators engage during other players' rolls?

**Key risk:** 3D physics may not feel satisfying. **Mitigation:** Protocol (ADR-074) is rendering-agnostic — swap to 2D or text without server changes. The rendering layer is the riskiest piece but also the most decoupled.

## Technical Decisions

### Resolution Model

MVP: d20 + modifier vs DC. Genre-configurable resolution systems (dice pools, 2d6, d100) deferred. Chargen stat rolls (currently 3d6) may independently migrate to a percentile scale.

### Beat-to-Roll Mapping

Deferred to playtesting. MVP: all confrontation beats with stat_check trigger a dice roll. A requires_roll flag on BeatDef is the likely future mechanism for selective rolling.

### Spectator Wait State

Spectators see the dice tray open with DC, stat, and modifier visible. No countdown, no timeout, no "waiting for..." indicator. The player throws when ready.

### Architecture (from ADRs)

- **Protocol:** 3 new GameMessage variants per ADR-074
- **Rendering:** Three.js + Rapier WASM overlay, lazy-loaded per ADR-075
- **Authority:** Server-authoritative — client gesture affects animation, not outcome
- **Sync:** Deterministic Rapier replay from seed + throw_params across all clients
- **Integration:** Hooks into dispatch_beat_selection() and BeatDef.stat_check
- **Observability:** OTEL spans on all dice events

## Functional Requirements

### Dice Resolution

- FR1: Server can determine when a player action requires a dice roll
- FR2: Server can calculate DC for a confrontation beat based on encounter state
- FR3: Server can resolve a roll outcome (CritSuccess, Success, Fail, CritFail) from die result + modifier vs DC
- FR4: Server can scale confrontation metric_delta based on roll outcome
- FR5: Server can generate a deterministic physics seed for each roll

### Dice Protocol

- FR6: Server can request a dice roll from a specific player during the reveal phase
- FR7: Player can submit a throw gesture to the server
- FR8: Server can broadcast dice results (including physics replay data) to all connected clients
- FR9: All clients can replay identical dice physics from the same seed and throw parameters

### Dice Interaction

- FR10: Rolling player can see the DC, stat, and modifier when the dice tray appears
- FR11: Rolling player can throw dice via a drag-and-flick gesture (mouse or touch)
- FR12: Rolling player can throw dice via keyboard (spacebar) as an accessibility fallback
- FR13: Dice tray persists until the player throws — no timeout

### Spectator Experience

- FR14: Non-rolling players can see the dice tray, DC, and stakes for another player's roll
- FR15: Non-rolling players can watch the dice physics animation in real time
- FR16: Non-rolling players cannot interact with the dice (read-only view)

### Narrative Integration

- FR17: Narrator receives roll outcome to shape narration tone
- FR18: DC is not visible to players during the sealed letter phase — only revealed at roll time
- FR19: Narrator sets the scene (narration chunk) before the dice tray appears

### Accessibility

- FR20: Screen readers receive text announcement of roll results via aria-live region
- FR21: Users with reduced-motion preference see dice snap to final position without animation
- FR22: Roll result information is available in non-visual format

### Observability

- FR23: GM panel can display dice roll events via OTEL spans
- FR24: GM can see roll outcomes alongside narrator output to verify narration quality

## Non-Functional Requirements

### Performance

- NFR1: First roll module load in under 2 seconds (lazy load + WASM init)
- NFR2: Subsequent roll startup in under 16ms (one frame) after module warm
- NFR3: Rapier physics step in under 2ms per frame at 60fps
- NFR4: Dice settle detection in under 3 seconds from throw
- NFR5: Loaded dice module under 50 MB total memory
- NFR6: GPU rendering clamped to devicePixelRatio 2 max
- NFR7: Lazy-loaded dice chunk under 400 KB gzipped

### Accessibility

- NFR8: aria-live result announcement within 500ms of settle
- NFR9: prefers-reduced-motion: dice snap to final position, no animation
- NFR10: Full throw capability via keyboard only (spacebar)

### Multiplayer Determinism

- NFR11: Same seed + throw_params produces bit-identical settled die face on all clients
- NFR12: Rapier WASM determinism verified on M-series (ARM) and Intel (x86) browsers

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| 3D physics doesn't feel satisfying | High | Protocol is rendering-agnostic; swap to 2D or text without server changes |
| Rapier WASM determinism fails cross-platform | High | Test early on M-series + Intel; float precision verification |
| First-roll lazy load feels slow (~2s) | Medium | Acceptable for MVP; pre-warm on connect in Phase 3 |
| Narrator ignores RollOutcome in prose | Medium | OTEL visibility in GM panel catches quality gaps |
| WebGL context conflicts with future 3D | Low | Single canvas overlay pattern per ADR-075 |
