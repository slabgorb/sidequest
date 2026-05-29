---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-9: Migrate dice-overlay-wiring-34-5 source-text wiring test to behavioral assertion

## Business Context

Epic 71 is the residue bucket for the 2026-05-27 `coyote_star` playtest — small,
real correctness and hygiene findings that no focused epic owns. This story sits
in the type-hygiene / test-durability cluster (71-8, 71-9, 71-14) whose job is to
make the playtest fixes *durable* rather than to add behavior.

The specific problem: `sidequest-ui/src/__tests__/dice-overlay-wiring-34-5.test.ts`
proves dice wiring by `fs.readFileSync`-ing source files and regex-matching on
source-code strings (import statements, JSX prop spellings, `useState` names).
Source-text wiring tests are brittle theater — they pin *spellings*, not behavior.
A rename, a refactor to a barrel export, or an equivalent wiring that uses a
different prop name breaks the test without breaking the feature; conversely, the
real dice path could regress while the strings still match. This violates the
project's own doctrine ("Verify Wiring, Not Just Existence" — behavior reachable
from production paths, not string existence).

The value: replace string-matching with a real behavioral assertion that renders
the dice surface and verifies observable behavior, so the test fails when the
feature actually breaks and survives benign refactors. Serves Keith/dev — a
trustworthy regression guard for the player-facing dice surface ADR-074/ADR-075
deliver to Sebastien and Jade (the mechanics-first players who need legible rolls).

## Technical Guardrails

**The target test file (the only file being rewritten):**
- `sidequest-ui/src/__tests__/dice-overlay-wiring-34-5.test.ts`

**What it currently asserts (source-text style — the anti-pattern to remove):**
The file defines a `readSrc()` helper over `fs.readFileSync` and runs `expect(src).toMatch(/.../)`
regexes against raw source. Concretely it pins:
- `App.tsx` strings: `diceRequest={diceRequest}`, `diceResult={diceResult}`,
  `DICE_REQUEST` / `DICE_RESULT` / `DICE_THROW` dispatch, `handleDiceThrow` /
  `onDiceThrow={handleDiceThrow}`, `currentPlayerId={currentPlayerId`,
  `setDiceRequest(null)`/`setDiceResult(null)` inside the `NARRATION_END` branch.
- `components/ConfrontationOverlay.tsx`: `import { InlineDiceTray } from '@/dice/InlineDiceTray'` and `<InlineDiceTray`.
- `dice/DiceOverlay.tsx`: presence of `diceRequest` / `diceResult` / `playerId` /
  `onThrow`, `handleSettle` not being a no-op, `onThrow` signature with `face: number[]`.
- `types/protocol.ts` + `types/payloads.ts`: `MessageType` entries, `DiceRequestPayload` /
  `DiceResultPayload` / `DiceThrowPayload` interfaces, `TypedGameMessage` union members, `face: number[]`.

**Target style — behavioral assertion:**
Render the dice surface with React Testing Library and assert on observable
behavior instead of source strings. The sibling test
`sidequest-ui/src/dice/__tests__/DiceOverlay.test.tsx` is the reference pattern:
it mocks `@react-three/fiber`, `@react-three/rapier`, `@react-three/drei`, and
`@local/dice-lib` (no WebGL in jsdom), then `render(<...>)` and asserts via
`screen.getByTestId("dice-overlay")` / `getByText(/DC 15/)` / `getByRole("status")`
and `onThrow` mock invocation. Reuse those mocks and fixture payload shapes.

**Architect's lens — assert behavior on the *production* path, not the dormant
component.** Per ADR-075 (§"Current rendering", App.tsx header): the standalone
full-screen `DiceOverlay` was retired; production dice render *inline* inside the
Confrontation panel via `InlineDiceTray`, reached
`App → GameBoard → ConfrontationWidget → ConfrontationOverlay → InlineDiceTray`.
The behavioral test should exercise the wired surface (`InlineDiceTray`, or
`ConfrontationOverlay` mounting it) so it proves the *production* wiring, not a
component that ADR-075 explicitly calls "not the production rendering path."
Existing `InlineDiceTray` tests (`dice/__tests__/InlineDiceTray.test.tsx`,
`InlineDiceTray.focal.test.tsx`) show the established render harness for it.

**Behavioral expectations to encode (from ADR-074/ADR-075):**
- Active `DiceRequest` → dice surface visible, showing DC / stat / modifier / character / context (ADR-074 player-facing math legibility).
- Rolling player gets an interactive throw affordance; spectator (player_id ≠ rolling_player_id) sees read-only and cannot fire `onThrow`.
- `DiceResult` → total, outcome label, and per-die faces render; crit outcomes carry distinctive treatment.
- `aria-live="polite"` status region announces the resolved roll (ADR-075 §a11y) — canvas is invisible to screen readers.

**What NOT to touch:** any runtime/production source
(`App.tsx`, `ConfrontationOverlay.tsx`, `DiceOverlay.tsx`, `InlineDiceTray.tsx`,
`types/protocol.ts`, `types/payloads.ts`). No protocol changes, no dice behavior
changes. This is a test-file rewrite only.

## Scope Boundaries

**In scope:**
- Rewrite `sidequest-ui/src/__tests__/dice-overlay-wiring-34-5.test.ts` so its wiring
  proof is a *behavioral* assertion: render the production dice surface
  (`InlineDiceTray` via `ConfrontationOverlay`, per ADR-075) with mocked R3F/Rapier/dice-lib
  and assert observable behavior (visibility on request, rolling-vs-spectator gating,
  result/outcome/face display, aria-live announcement) instead of `fs.readFileSync`
  source-string regexes.
- Keep at least one true wiring/integration assertion (project doctrine: "Every
  Test Suite Needs a Wiring Test") — but expressed behaviorally through the
  production composition, not a grep over App.tsx.

**Out of scope:**
- Any change to dice overlay / inline dice tray runtime behavior or appearance.
- Changes to dice protocol types, payloads, `App.tsx` dispatch, or server-side dice resolution.
- Rewriting other dice tests (`DiceOverlay.test.tsx`, `InlineDiceTray*.test.tsx`,
  `diceProtocol.test.ts`) — they already assert behaviorally.
- Resolving the dormant-`DiceOverlay`-vs-`InlineDiceTray` duplication itself (ADR-075 cleanup).
- Server-side OTEL spans — this is a UI test refactor; no subsystem behavior changes, so no new spans required.

## AC Context

The story has no enumerated ACs in the tracker (1pt trivial); the title is the
contract. Derived, testable acceptance:

1. **No source-text introspection remains.** `dice-overlay-wiring-34-5.test.ts` no
   longer imports `node:fs` / `node:path` and contains no `readFileSync` /
   `readSrc` / `.toMatch(/...source-string.../)` against file contents.
   *Verify:* grep the file — zero `readFileSync`/`fs` references.

2. **Wiring is proven behaviorally on the production path.** The test renders the
   production dice composition (`InlineDiceTray` through `ConfrontationOverlay`,
   per ADR-075) and asserts the dice surface appears for an active `DiceRequest`
   and the roll affordance/result reaches the DOM.
   *Verify:* test renders a component tree (RTL `render`) and uses `screen`/`getByRole`/`getByTestId` queries; passes against current code.
   *Edge cases:* mock R3F/Rapier/dice-lib (no WebGL in jsdom) following `DiceOverlay.test.tsx`; null `diceRequest` → surface absent.

3. **Rolling-vs-spectator behavior is asserted, not string-matched.** A rolling
   player sees an interactive throw affordance; a spectator (`playerId ≠
   rolling_player_id`) does not, and `onThrow` is never fired for the spectator.
   *Verify:* mock `onThrow`; assert `not.toHaveBeenCalled()` for spectator, interactive surface present for roller.

4. **Result + a11y observable.** A provided `DiceResult` renders total, outcome,
   and per-die faces, and the `aria-live="polite"` status region announces the
   roll per ADR-075.
   *Verify:* `getByRole("status")` has `aria-live="polite"`; result text includes character/total/DC/outcome.

5. **Suite is green and the file still earns its name.** `npx vitest run
   src/__tests__/dice-overlay-wiring-34-5.test.ts` passes; the file still
   constitutes a wiring/integration check (renders through the real production
   composition), satisfying "Every Test Suite Needs a Wiring Test".

## Assumptions

- The production dice path is `InlineDiceTray` mounted by `ConfrontationOverlay`
  (ADR-075 §"Current rendering", `ConfrontationOverlay.tsx:325`); the standalone
  `DiceOverlay` is dormant. The behavioral test should target the production path.
  If `ConfrontationOverlay` proves too heavy to render in isolation (deep
  provider/context dependencies), fall back to rendering `InlineDiceTray`
  directly with fixture props — still behavioral, still on the production
  component. Log a Design Deviation if the production composition cannot be
  rendered at all and the test must target `DiceOverlay` instead.
- The R3F/Rapier/dice-lib mocks and fixture payload shapes in
  `DiceOverlay.test.tsx` / `InlineDiceTray.test.tsx` are reusable as-is for the new
  behavioral test.
- Current production code already satisfies the behavioral expectations (this is a
  GREEN refactor of the test, not a RED feature). If a behavioral assertion fails
  against current code, that is a genuine finding — escalate, do not weaken the
  assertion back to a source-string check.
- jsdom + Vitest is the test runner (no real WebGL); `npx vitest run` is the gate.
