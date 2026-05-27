---
parent: context-epic-69.md
workflow: tdd
---

# Story 69-2: Opening gameboard — full-width action input under narrative + co-located high-contrast HP pip scale

## Business Context

Two playtest-3 findings, two real people:

- **Full-width action input under the narrative (serves Alex).** Alex is a slower typist who freezes under time pressure. The input must read as a prominent, unhurried, full-width invitation directly beneath the narration — never a small or side-docked afterthought. This reinforces the ADR-036 submit-and-wait barrier: the turn waits for everyone, and the UI should say so. The 2026-05-03 amendment keeps peer action text visible during the wait phase — this story must **not** regress that.
- **Co-located high-contrast HP pip scale (serves Sebastien & Jade).** The group's mechanics-first players want the numbers behind the narration legible in the **player-facing** surface. Today HP lives in a Dockview tab they must click into; it isn't glanceable while composing an action. Surfacing a high-contrast HP pip scale next to the input makes the stakes visible at a glance.

This is player-UI work. It is **not** dev observability — no OTEL spans, no GM-panel charts, no watcher telemetry. AC-4/AC-5 reference "matches server state" only in the sense that the *player-visible* pips must reflect the real `PARTY_STATUS` value reactively; verifying that is a wiring/integration concern, not a request to build telemetry.

## Technical Guardrails

**Repo:** `sidequest-ui` only. No server, protocol, or content changes.

**Reuse-first (Architect mandate):** HP pips already exist. Do **not** author a brand-new health widget.
- `CharacterPanel.tsx` renders `FolioEdgeTicks` (diamond pip scale, gold fill / crimson at ≤25%) and `EdgeBadge` (`HP {cur}/{max}` text). Reuse this pip pattern — extract it into a small shared/co-located component if needed, or render a compact variant adjacent to `InputBar`.
- `GenericResourceBar.tsx` exists for thresholded pools; consider it only if a bar reads better than pips — but pips are the established HP idiom, so default to pips.

**Key files:**
- `components/GameBoard/GameBoard.tsx` (~lines 737–806) — bottom input area is already `shrink-0` and full-width (~line 800). Layout work is ensuring the *opening* gameboard presents the input clearly under the narrative and hosts the co-located HP scale — not a from-scratch reposition.
- `components/InputBar.tsx` — the input itself; preserve its `onSend`/`onReveal`/`round`/`confrontationActive` contract. Do not break peer-reveal (ADR-036).
- `components/CharacterPanel.tsx` — source of the pip pattern to reuse (`FolioEdgeTicks`, `FOLIO` token map).
- `hooks/useGameState.ts` / `useStateMirror.ts` — subscribe to party state for reactive HP; `CharacterSummary { hp, hp_max }` from `types/party.ts`.
- `hooks/useGenreTheme.ts` (ADR-079) — use `--primary`/`--accent`/`--destructive` tokens for high-contrast, genre-consistent pips. Do not hardcode hex colors.

**Do NOT touch:** server, WebSocket protocol/message shapes, the Dockview tab contents themselves (CharacterPanel can stay), dice subsystem (that's 69-1), any OTEL/telemetry code.

## Scope Boundaries

**In scope:**
- Action input presented full-width directly beneath the narrative on the opening gameboard, with clear visual hierarchy (narration → input → HP).
- A high-contrast HP pip scale co-located with the input (same container or grouped row), reusing the existing pip idiom and theme tokens.
- Reactive update of the co-located pips when `PARTY_STATUS` changes (no manual refresh).
- Responsive behavior across mobile / tablet / desktop viewports.
- Wiring test proving the co-located HP scale is imported and consumed by GameBoard in production (not just unit-tested in isolation).

**Out of scope:**
- 3D dice camera/scale and dice-lib wiring (story 69-1).
- Any server/protocol change, new message types, or HP *computation* changes.
- Removing or restructuring the CharacterPanel Dockview tab (the full sheet stays; this adds a glanceable summary).
- OTEL/GM-panel/watcher work of any kind.
- TTS/voice, audio.

## AC Context

**AC-1 — Full-width action input below narrative.**
- Pass condition: on the opening gameboard, the action input renders full-width beneath the narrative area (not side-docked, not collapsed/hidden behind a tab), with text input + submit in a horizontal row and a clear narration → input → HP hierarchy.
- Edge cases: empty narrative (still shows input); very long narration (input stays pinned/reachable, no overlap); confrontation active (`confrontationActive` still locks Enter as before).
- Test: render GameBoard with mock game state; assert the input is present, full-width (container spans available width), and ordered below the narrative region.

**AC-2 — Co-located high-contrast HP pip scale.**
- Pass condition: a pip/dot HP scale renders adjacent to / grouped with the input; high contrast via theme tokens; one pip group per active character (or the active PC, per current single-PC opening flow); updates reactively on HP change.
- Edge cases: hp = 0 (all pips empty/danger state); hp = hp_max (full); hp_max large (no overflow — pips wrap or condense); missing/loading party (renders nothing or a skeleton, no crash).
- Test: render the HP scale with `CharacterSummary` fixtures; assert pip count matches `hp_max` and filled count matches `hp`; assert danger styling at ≤25%; assert colors come from theme tokens, not hardcoded hex.

**AC-3 — Responsive.**
- Pass condition: input + HP scale usable on mobile (full-width, no horizontal scroll to reach input), tablet (pips inline or stacked without overflow), desktop (inline horizontal).
- Test: override `matchMedia` per viewport (test-setup defaults to mobile); assert layout invariants hold at each breakpoint.

**AC-4 — Mechanical legibility / matches player-visible state.**
- Pass condition: each character's pips (and/or an accessible label/tooltip) convey `current/max`; the player-visible value equals the latest `PARTY_STATUS` value delivered through `useStateMirror` → `useGameState()`.
- Note: "matches server state" = the rendered pips reflect the reactive store value. This is a UI-reactivity assertion, **not** a telemetry/OTEL requirement.
- Test: integration — push a `PARTY_STATUS` HP update through the mock socket; assert the co-located pips re-render to the new value without manual refresh.

**AC-5 — Submit → state mirror → HP reflect (integration + wiring).**
- Pass condition: submitting an action via the input goes through the existing `onSend`/`useGameSocket().send()` path; a subsequent `PARTY_STATUS` HP change propagates through the state mirror and the co-located pips re-render; peer-reveal (ADR-036) still fires.
- Wiring test (mandatory): assert the co-located HP scale component is imported and rendered by GameBoard in production code (non-test consumer), not merely unit-tested.
- Test: full-chain integration using the MockWebSocket pattern from `__tests__/action-reveal-wiring.test.tsx`.

## Assumptions

- `PARTY_STATUS` already carries `hp`/`hp_max` and flows reactively via `useStateMirror` → `GameStateProvider` (confirmed by code survey). If HP is not actually populated on the opening gameboard, log a Design Deviation rather than adding a server change.
- The opening gameboard uses a single active PC (or small party); the co-located scale shows the player's own character. If MP multi-PC display is required, that's a deviation to flag, not silent scope creep.
- Reusing `FolioEdgeTicks`' pip idiom is acceptable; if extraction proves entangled with CharacterPanel-specific layout, a thin new co-located component that *reuses the token map and pip semantics* is acceptable — but justify it as reuse, not reinvention.

## Interaction Patterns

Opening gameboard, top → bottom: narrative cards → (turn/peer banners) → **full-width action input** → **co-located HP pip scale**. The player reads, glances at HP, types, submits; the turn holds until all players submit (ADR-036). Peer composing/submitted reveals remain visible during the wait.

## Accessibility Requirements

- Input is keyboard-focusable with a semantic label; submit reachable by keyboard.
- HP scale conveys value non-visually (aria-label or text equivalent like `HP 7/10`) — pips alone are insufficient for screen readers.
- High-contrast pip colors should meet WCAG AA against the card background; prefer theme tokens that already satisfy this.

## Visual Constraints

- Use ADR-079 theme tokens (`--primary`, `--accent`, `--destructive`, `--card`, `--border`) — no hardcoded hex. Match the existing `FOLIO` semantic map in CharacterPanel for genre consistency.
- Pips are the established HP idiom; keep the diamond/dot language consistent with `FolioEdgeTicks`.
- Danger threshold at ≤25% renders in the destructive/crimson token, matching current behavior.
