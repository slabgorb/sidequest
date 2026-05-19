---
parent: context-epic-56.md
workflow: tdd
---

# Story 56-1: Show controlling player's name on character displays (multiplayer only)

## Business Context

A direct request from the play table: the players want each character display to show *who is playing it* (e.g. "Rux — James") so the table can match names to characters at a glance without leaning over to ask. This is a fast-feedback, primary-audience-driven QoL papercut sitting inside Epic 56.

**Audience read** (per `CLAUDE.md` "Who This Is For"):
- **Alex** benefits most. He sometimes freezes under turn pressure; "whose turn is it again, and who is whose?" friction adds up. Persistent name-pairing on the party rail reduces cognitive load every round.
- **James / Sebastien** benefits secondarily. Faster orientation in shared scenes.
- **Keith-as-player** benefits: cross-table social grounding.
- **Sonia / Antonio / Pedro** are not part of the trigger, but the feature does not regress their experience because it is *additive chrome* on existing surfaces — and in single-player it does not render at all (see Scope Boundaries).

**User problem:** When four humans share one screen-shaped table, character-name-only labels create a constant micro-friction of name↔seat matching. The data to fix this (`CharacterSummary.player_id`, equal to the player's typed `displayName`) is already on the wire; the gap is purely render.

**Expected outcome:** In any multiplayer session, every primary character display shows the controlling player's name next to the character's name. In single-player, none of the surfaces change — Keith already knows it is him.

## Technical Guardrails

**Key files (read these first):**

| Path | Role |
|------|------|
| `sidequest-ui/src/components/CharacterPanel.tsx` | Always-visible party rail. **Load-bearing for Alex.** ~1005 LOC — find the existing header block (look for `data-testid="character-header"`) and extend it; do not refactor the panel. |
| `sidequest-ui/src/components/CharacterSheet.tsx` | Modal/expanded sheet. ~101 LOC — small, the natural home for an explicit "played by …" treatment. |
| `sidequest-ui/src/components/GameBoard/widgets/CharacterWidget.tsx` | **7-line wrapper that re-exports `CharacterPanel`.** Inherits the fix automatically. No separate edit needed — but verify visually that the inherited treatment makes sense at widget pixel-budget. |
| `sidequest-ui/src/types/party.ts` | `CharacterSummary.player_id` is the controlling player's name (==`displayName` per server convention). This is the data source. |
| `sidequest-ui/src/components/__tests__/CharacterPanel.test.tsx` | Existing snapshot/behavior tests — extend, don't replace. |
| `sidequest-ui/src/components/__tests__/CharacterSheet.test.tsx` | Existing tests — extend, don't replace. |

**Patterns to follow:**
- The panel header already composes portrait · name · subtitle · level/edge badges. The player-name treatment belongs in the same header block, beside or beneath the character name. Pattern: subordinate visual weight — character name is primary, player name is secondary. Em-dash + smaller/lighter font is the cheap default; a UX-Designer (Viola) tandem may sharpen this if the story author wants polish.
- `CharacterSummary.player_id` is the source. Do not introduce a new prop, new payload, or new server field. The data is on the type already.
- Tests live next to components; the suite is Vitest (`npx vitest run`).

**Dependencies and integration points:**
- The seated-roster signal already lives in `App.tsx` (the "seated set" referenced in lines ~355 / ~688 / ~713) — this is the canonical source for "who is currently a seat in this session." See Assumptions for the SP/MP detection question.
- No protocol changes. No server changes. No new fields. If any of these begin to feel necessary, **stop** and re-scope — that is scope drift away from the QoL premise.

**What NOT to touch:**
- Do not refactor `CharacterPanel.tsx` for length. It is long; that is not this story.
- Do not modify the character creation flow.
- Do not modify the seated/lobby model in `App.tsx`.
- Do not add OTEL spans — per `sidequest-ui/CLAUDE.md` "Not needed for: Cosmetic UI changes (labels, spacing, colors)." This is exactly that.
- Do not introduce a new "is multiplayer?" hook or context unless the existing seated-roster signal genuinely cannot answer the question.

## Scope Boundaries

**In scope:**
- Render the controlling player's name on `CharacterPanel.tsx` (primary surface) in multiplayer sessions.
- Render the controlling player's name on `CharacterSheet.tsx` (modal) in multiplayer sessions.
- Verify the inherited treatment on `CharacterWidget.tsx` (since it re-exports `CharacterPanel`) is acceptable at widget pixel-budget; if it visibly breaks, hide the treatment for the widget surface only.
- Tests covering both the MP-shows path and the SP-omits path on `CharacterPanel` and `CharacterSheet`.
- A wiring test confirming the treatment appears for a real `CharacterSummary` flowing through the production render path, not just a hand-crafted prop in isolation.

**Out of scope:**
- Voice / TTS / portrait-on-tooltip extensions.
- Player-color theming (a likely follow-up paper-cut for a future Wave).
- Showing player names on NPC cards — NPCs are explicitly excluded (no controlling seat to display).
- Showing player names on encounter actors / dice overlays / chase widgets — defer to follow-up if asked.
- Refactor of `CharacterPanel.tsx` length.
- New server payload fields or protocol changes.
- Any "(you)" labeling for the local player — the simple "player name verbatim" treatment is in scope; if Keith wants "(you)" disambiguation, it lands as a follow-up Wave.

## AC Context

**AC-1: In multiplayer sessions, `CharacterPanel` displays the controlling player's name for every seated PC.**
- Pass condition: when rendering a PC `CharacterSummary` whose `player_id` is non-empty in a multiplayer session, the panel header shows `player_id` (or a clearly-derived label such as `— {player_id}`) within the `character-header` block.
- Edge: companion entries (which use a separate `CompanionSummary` shape per the panel's existing `characters?: CharacterSummary[]` prop) do not have a controlling player — they must not render a player-name label.
- Edge: PC with absent/empty `player_id` (e.g. a seat in CHARGEN state) — render character name only, no player suffix; do **not** render `— undefined` or a fallback string.
- Test sketch: render `CharacterPanel` with an MP-shaped `CharacterSummary{ player_id: "Sebastien" }` in an MP context; assert the rendered DOM contains `"Sebastien"` inside the character header region (by testid `character-header`).

**AC-2: In multiplayer sessions, `CharacterSheet` displays the controlling player's name in its header.**
- Pass condition: the sheet header shows the controlling player's name visible to a user reading the sheet — same secondary-visual-weight pattern as AC-1.
- Edge: NPCs displayed via this sheet (if applicable in the existing usage) do not get the suffix.
- Test sketch: render `CharacterSheet` with an MP-shaped PC; assert the player name is present in the header.

**AC-3: `CharacterWidget` inherits the same behavior because it is a re-export wrapper of `CharacterPanel`.**
- Pass condition: passing an MP `CharacterSummary` through `CharacterWidget` produces a render that contains the player name. No code change in `CharacterWidget.tsx` itself unless the inherited render visibly fails at the widget pixel-budget (in which case suppress the suffix via a prop on the wrapper rather than forking the panel).
- Test sketch: shallow render of `CharacterWidget` with an MP `CharacterSummary`; assert the player name renders.

**AC-4: In single-player sessions, none of the three surfaces render the controlling player's name.**
- Pass condition: with a single seated player in the session, the player-name treatment is absent from `CharacterPanel`, `CharacterSheet`, and `CharacterWidget`. No em-dash, no parenthetical, no whitespace gap that betrays the missing label.
- This is the **load-bearing AC** — single-player must not regress (per project memory: `no-player-name-in-sp`). If only one AC ends up with explicit test coverage, this is the one.
- Test sketch: render each component in an SP-shaped session context (seated set of size 1, or whatever signal is chosen — see Assumptions); assert the player name string does **not** appear in the rendered DOM.

**AC-5: NPCs never render a player name in either session mode.**
- Pass condition: any character entry with no `player_id` (or with a clear NPC marker on the type, if one exists) renders without the player-name suffix even in MP.
- Test sketch: MP context, NPC-shaped `CharacterSummary{ player_id: "" }` or equivalent; assert no spurious suffix appears.

**AC-6: Test coverage extends the existing `CharacterPanel.test.tsx` and `CharacterSheet.test.tsx` rather than starting a new suite, and includes at least one wiring test that renders the components inside their normal provider stack to confirm the production data path lights up.**
- Pass condition: new `it(...)` blocks land inside the existing test files. At least one test exercises the real provider stack (`GameStateProvider` / theme) rather than only hand-crafted props.
- Rationale: from project memory and `sidequest-ui/CLAUDE.md` — every test suite needs a wiring test. Existence is not the same as wiring.

## Assumptions

**The big technical assumption — flag for Oberon at setup time:**

The cleanest signal for "this is a multiplayer session" in current UI state has **not been pre-decided** here. Three plausible signals exist:

1. **Seated-player set size** — `App.tsx` already maintains a seated roster (search references around lines 355 / 688 / 713). If `seatedPlayers.size > 1`, treat as MP.
2. **`CharacterSummary` count with non-empty `player_id`** — if more than one seat-bound PC is visible in the party, that's MP by definition.
3. **A session-mode flag** — if one exists on the session payload, it would be the most explicit signal.

**Architect should pick** at story setup based on which signal is most reliable during state transitions (mid-game reseat, late-join, etc.). The choice should be documented in the implementation, not buried.

**Other assumptions:**
- `CharacterSummary.player_id` equals the player's typed `displayName` end-to-end. Per `App.tsx`: `player_id: displayName` on connect. If this equivalence ever breaks, this story breaks. (Unlikely to break in scope; flag as a deviation if observed.)
- Vitest + React Testing Library remain the canonical UI test stack (per `sidequest-ui/CLAUDE.md` and the existing `__tests__/` directory).
- The em-dash + secondary-weight visual pattern is acceptable to ship without a UX-Designer tandem. If Viola is pulled in to refine treatment, that adds scope but does not block AC-1..AC-6.
- No `(you)` self-labeling is in scope (see Scope Boundaries). If the playgroup requests it after seeing the feature live, file a follow-up Wave-1 story.
- The "trigger ask" memory of record is the play-table verbal request from 2026-05-19; there is no PRD. Source-of-truth is this context document plus the audience-axis rubric in `CLAUDE.md`.

If any assumption proves wrong during implementation, log it as a **Design Deviation** in the session file per the standard agent protocol.

## Interaction Patterns

- The pairing should read as one cohesive label, not two competing labels. The visual hierarchy is: **character name (primary) → player name (secondary)**. The character is the in-fiction entity; the player is the off-fiction attribution.
- The pairing must not interfere with existing badge placement (level badge, edge badge, ♦ tick row mentioned in `CharacterPanel.tsx` comments at line ~178).
- Hover / focus / active states: no new interaction is required. The label is static text; existing portrait / sheet-open interactions remain unchanged.
- The pairing should be visible in all character states (turn pending, acting, submitted, idle) — it's identity chrome, not turn-state chrome.

## Accessibility Requirements

- The player-name label is plain text content; it should be readable by a screen reader as part of the character header. If the existing header has `aria-label` or similar attributes, the player-name should be included in the accessible-name composition (e.g. `Rux, played by James`), not appended as decorative-only text.
- No new keyboard interaction. Existing focus/tab order must not be disturbed by adding the label.
- Color contrast: the secondary-weight treatment must remain WCAG AA against the panel background in every genre theme (genre theme overrides per ADR-079). If the existing token palette already provides a "subtle text" token, use it rather than introducing a new color.

## Visual Constraints

- **Use existing tokens.** The panel already comments (lines ~30 / ~54) about token-resolved colors and decorative surfaces. Do not introduce new color tokens for this story.
- **Pixel budget for `CharacterPanel`:** plenty of room beside the character name. The header is a flex column with portrait + name + subtitle area.
- **Pixel budget for `CharacterSheet`:** comparable to panel — small file (101 LOC), header has room.
- **Pixel budget for `CharacterWidget`:** **tight.** This is a board widget. Two acceptable failure modes if the inherited treatment doesn't fit:
  1. Hide the suffix via a prop on the wrapper (preferred).
  2. Truncate/ellipsize the suffix at widget tier.
- **Responsive:** verify the treatment doesn't wrap badly at the narrowest expected panel width. If wrapping is ugly, prefer a single ellipsized line over multi-line.
- **No new animation, no new icons** — this is a label, not a feature surface.
