---
parent: context-epic-69.md
workflow: tdd
---

# Story 69-1: 3D dice camera/scale pull-in + dice-lib wiring audit to real server rolls (ADR-074/075)

## Business Context

Playtest-3 (UX Designer + Keith) found the 3D dice roll doesn't read as a focal
moment — it happens in a small corner frame and the table doesn't register it as
*the* mechanical beat. For the playgroup's mechanics-first players (Sebastien,
Jade) the dice roll is the legible heart of confrontation resolution; if they
can't *see* the roll land, the crunch they came back for is invisible. This story
pulls the dice camera/scale in so a roll becomes a clear, glanceable focal moment,
and audits that the dice tray is driven by **real server rolls** (ADR-074) rather
than any client-side fakery — so what the player sees is what the engine actually
resolved. Pure player-facing UI polish in `sidequest-ui`; no server or protocol
change.

## Technical Guardrails

**The live dice component is `src/dice/InlineDiceTray.tsx`.** Dice render *inline*
inside the Confrontation panel (`components/ConfrontationOverlay.tsx:564` mounts
`<InlineDiceTray>`), NOT as a fullscreen overlay. The old `DiceOverlay.tsx` and
`DiceSpikePage.tsx` are **retained for isolated testing only and are otherwise
dead** (see the comment at `App.tsx:52`). **Do all camera/scale work in
`InlineDiceTray.tsx` — do NOT touch `DiceOverlay.tsx`.** If `DiceOverlay`/
`DiceSpikePage` are confirmed to have zero non-test consumers, flag for deletion
(per the "delete dead code in the same PR" principle) rather than editing them.

- **Camera/scale (current):** `InlineDiceTray` renders a `@react-three/fiber`
  `<Canvas>` in a ~180px square frame (`InlineDiceTray.tsx:325-372`) with a
  **deliberately top-down camera** `position: [0, 2.4, 0]`, `fov: 42`. **This is
  a calibrated constraint, not an accident:** the inline comment records that the
  Playtest 2026-04-24 found *oblique cameras made the "up" face ambiguous*, so the
  top-down frame must be preserved. Any "pull-in" (larger frame, lower camera y /
  narrower fov to fill more of the view) MUST keep the settled up-face
  unambiguously legible. Do not reintroduce an oblique angle to make it "look
  cooler" — face legibility wins.
- **Roll wiring (ADR-074, already server-authoritative):** `InlineDiceTray` takes
  `diceRequest` (from `DICE_REQUEST`) and `diceResult` (from `DICE_RESULT`) props.
  The animated throw params come from `randomThrowParams()` (cosmetic only —
  position/velocity of the toss), but the **settled faces are reproduced from the
  server** via `replayThrowParams(diceResult.throw_params, diceResult.seed, ...)`
  (`InlineDiceTray.tsx:259`). The "wiring audit" AC means *prove* end-to-end that
  the displayed face/total is the server's (seed-replayed), never a client RNG
  result — and that there is no path where a face is invented locally.
- **Data flow:** `DICE_REQUEST`/`DICE_RESULT` WS messages → `App.tsx` state
  (`diceRequest`/`diceResult`, ~line 427, story 34-5) → `GameBoard` props → down
  to `ConfrontationOverlay` → `InlineDiceTray`. The tray only mounts while a
  confrontation is active.
- **Theme tokens (ADR-079):** any visual chrome added to the enlarged frame uses
  the genre theme tokens (`--primary`, `--accent`, `--destructive`) per the epic
  architecture — no hardcoded colors.
- **Test substrate:** Vitest + React Testing Library. Existing dice tests live in
  `src/dice/__tests__/`; confrontation-level reveal coverage in
  `src/components/__tests__/ConfrontationOverlay.outcomereveal.test.tsx`. Per
  project rule, include at least one **wiring test** proving the tray is fed by
  real `DICE_RESULT` payloads and renders the server-derived face.

## Scope Boundaries

**In scope:**
- Camera/scale pull-in in `InlineDiceTray.tsx` so the settled roll is a legible
  focal moment, preserving top-down face legibility.
- Audit + test proving the inline dice tray renders **server-authoritative**
  faces/totals (seed replay of `DICE_RESULT`), with a wiring test.
- If verified dead, removal (or explicit flag for removal) of `DiceOverlay.tsx` /
  `DiceSpikePage.tsx`.

**Out of scope:**
- Action-input repositioning and the HP pip scale — that's story 69-2 (already
  done).
- Any server / protocol / `DICE_REQUEST`/`DICE_RESULT` schema change. ADR-074 is
  consumed, not modified.
- New dice geometry, new die types, or physics-engine changes (Rapier tuning
  beyond camera framing).
- OTEL / GM-panel / watcher telemetry — this is a player-UI story only.

## AC Context

1. **Dice camera/scale pulled in to a legible focal moment.**
   - Pass: the inline tray frame is enlarged and/or the camera reframed so the
     settled die fills materially more of the view than today's ~180px top-down
     frame, while the up-face remains unambiguous.
   - Edge cases: small-viewport / mobile (`matchMedia` mock defaults to mobile in
     `test-setup.ts` — override per test for desktop); confrontation panel docked
     vs. floating; multiple dice in one throw (d20 + modifier dice) must all stay
     in frame.
   - Test: render `InlineDiceTray` with a `diceResult` fixture, assert the Canvas
     frame / camera params reflect the pulled-in values (and that the top-down
     calibration — camera over the dice, not oblique — is retained).

2. **Dice-lib wiring audit: displayed roll == server roll.**
   - Pass: given a `DICE_RESULT` payload with known `throw_params`/`seed`/`rolls`/
     `total`, the tray displays exactly that total and face(s); no code path
     derives a face from a client-side RNG.
   - Edge cases: a `DICE_REQUEST` with no following `DICE_RESULT` (pending state)
     must not display a fabricated face; a `diceResult.request_id` matching a
     prior request must not double-fire (dedup via `lastRequestIdRef`).
   - Test (wiring): feed a real-shaped `DICE_RESULT` through the component (or via
     the MockWebSocket integration pattern in
     `src/__tests__/action-reveal-wiring.test.tsx`) and assert the rendered
     announcement/face equals the server payload — proving the tray is reachable
     and server-fed in a production path.

## Assumptions

- `InlineDiceTray` is the **only** live dice renderer; `DiceOverlay`/
  `DiceSpikePage` have no production consumers. (Verified during setup — grep
  shows only test + isolated-page references. Dev should re-confirm before
  deleting.)
- The top-down camera calibration (2026-04-24 playtest) is still the desired
  constraint — pull-in adjusts distance/frame size, not the viewing angle. If
  Keith/UX want an angled hero shot instead, that's a design deviation: log it and
  notify SM before changing the angle.
- `DICE_RESULT.throw_params` + `seed` remain sufficient for deterministic face
  replay (no schema change needed). If the audit reveals the seed replay is
  lossy/non-deterministic, that's a deviation — escalate, don't paper over it.
- The tray only needs to be legible while a confrontation is active (its only
  mount point). No standalone/out-of-confrontation roll surface is required.

## Interaction Patterns

The roll sequence inside an active confrontation: `DICE_REQUEST` arrives → tray
animates a toss (cosmetic `randomThrowParams`) → `DICE_RESULT` arrives → dice
settle to the server-replayed face → inline announcement
("`{name} rolled {total} ({faces} {±mod}) vs DC {difficulty} — {outcome}`",
`buildAnnouncement`). The pull-in must make the *settle* the focal beat without
breaking this sequence or the existing reveal timing tested in
`ConfrontationOverlay.outcomereveal.test.tsx`.

## Accessibility Requirements

- The numeric result/announcement (`buildAnnouncement`) is the
  accessible source of truth — the 3D render is decorative reinforcement, so the
  text announcement must remain present and screen-reader reachable regardless of
  camera/scale changes.
- Don't gate roll comprehension on the 3D canvas alone (serves low-vision and the
  WebGL-failure graceful-degradation path).

## Visual Constraints

- Frame lives inside the Confrontation panel — the pulled-in size must not
  overflow or crowd out the confrontation content / outcome reveal beneath it.
- Use ADR-079 genre theme tokens for any added chrome; keep high contrast
  consistent with the epic's HP-pip legibility goal.
