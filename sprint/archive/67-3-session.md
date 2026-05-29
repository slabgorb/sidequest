---
story_id: "67-3"
jira_key: "67-3"
epic: "epic-67"
workflow: "trivial"
---
# Story 67-3: MP peer-visibility consolidation + slow-typist reassurance (one canonical surface, Composing/Sealed/Resolving)

## Story Details
- **ID:** 67-3
- **Jira Key:** 67-3
- **Epic:** epic-67 (Multiplayer resilience & presence)
- **Workflow:** trivial
- **Type:** bug
- **Points:** 3
- **Priority:** p2
- **Repos:** ui
- **Stack Parent:** none

## Story Context

This story is part of **Epic 67: Multiplayer resilience & presence** (Playtest-3 findings). See `sprint/context/context-epic-67.md` for full epic context and architecture.

**Problem:** Shared-turn / peer-visibility status was scattered across surfaces, and slow typists (like Alex) had no reassurance the table was waiting *with* them, not *on* them. This story consolidates peer-visibility/shared-turn status into ONE canonical surface with the Composing/Sealed/Resolving status the table reads, plus slow-typist reassurance messaging.

**Related ADR:** ADR-036 (Multiplayer Turn Coordination) — submit-and-wait barrier, peer action text visible during wait phase per 2026-05-03 amendment.

**Tech foundation:**
- WebSocket lifecycle: `hooks/useWebSocket.ts` and `hooks/useGameSocket.ts`
- GameBoard turn state: `components/GameBoard.tsx`
- ADR-036 turn states: Composing (collecting player inputs), Sealed (all inputs locked), Resolving (narration in progress)

## Workflow Tracking

**Workflow:** trivial  
**Phase:** implement  
**Phase Started:** 2026-05-28T13:28:44Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T13:26:45Z | 2026-05-28T13:28:44Z | 1m 59s |
| implement | 2026-05-28T13:28:44Z | - | - |

## Sm Assessment

**Scope (confirm):** UI-only consolidation of multiplayer peer-visibility / shared-turn status into one canonical surface keyed on the ADR-036 turn states (Composing → Sealed → Resolving), plus slow-typist reassurance messaging. No server changes — 67-2 already landed the ACTION_REVEAL delivery resilience this presence surface reads.

**Why now / who it serves:** Keith-requested (epic-67) and directly serves **Alex** (slow reader/typist). The reassurance framing is load-bearing: the surface must read "the table is waiting *with* you," never "waiting *on* you." Per ADR-036's 2026-05-03 amendment, peer action text is visible during the wait phase — this story unifies where that status is read, it does not introduce sealed/hidden visibility (that's PvP-only and out of scope).

**Approach for Dev:** Find the existing scattered turn-status surfaces (GameBoard turn state + the submit/wait barrier in `useGameSocket`/`useWebSocket`) and converge them on a single component/state source. Don't reinvent — the Composing/Sealed/Resolving states already exist; this is consolidation + presentation, not new turn mechanics. Confirm with a wiring test that the canonical surface is the one actually rendered during a multiplayer wait.

**Defer:** 67-4 (player-vs-character identity / doubled-header) is independent and stays separate. Don't fold the `X— X` header fix into this story.

**Gate:** Merge gate clear (no open PRs). Session + branch created. Trivial/phased → handoff to Dev for implement.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement  
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): `TurnStatusEntry` is defined twice — `src/types/payloads.ts` (lines 38-42) and re-declared in `src/components/TurnStatusPanel.tsx` (lines 14-18). Harmless today (shapes match) but a future divergence risk. Candidate for a tiny follow-up dedupe; out of scope for 67-3's closure. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. No implementation was performed — see Dev Assessment.

## Dev Assessment

**Implementation Complete:** N/A — story already resolved by prior commit. No code written.

**Determination:** Story 67-3's entire scope was already shipped on `develop` by commit **`ec69c9b`** ("fix(mp): unify peer-barrier status to one Composing → Sealed → Resolving chain", Keith Avery, 2026-05-27), which is an ancestor of this branch's base. Mapping each element of the 67-3 title to that commit:

| 67-3 scope | Delivered by ec69c9b |
|---|---|
| "one canonical surface, Composing/Sealed/Resolving" | "One verb chain across all surfaces: PeerRevealList card and CharacterPanel party badge now read ✓ Sealed / Composing" |
| "MP peer-visibility consolidation" | "The same peer-state was told 3× in 3 places with 3 disagreeing verbs… Killed the duplicate amber 'X acted' banner row" |
| "slow-typist reassurance" | "Slow-typist reassurance (for Alex): a calm, TIMER-FREE line near the input when a peer has sealed and you're still composing" (GameBoard.tsx:565-582) |

ec69c9b also shipped the tests (`GameBoard-slow-typist.test.tsx` +70 lines; updates to PeerRevealList / MultiplayerTurnBanner / CharacterPanel suites).

**Files Changed:** None on `feat/67-3-mp-peer-visibility-consolidation` (working tree clean).

**Tests:** 174/174 passing (GREEN) across the 12 turn-status / peer-visibility test files (run id `67-3-dev-green`). Confirms the canonical surface is wired and rendered during MP wait.

**Disposition (user-directed):** Keith (story stakeholder and author of ec69c9b) chose **"Close as resolved-by-ec69c9b"** — same pattern as 64-10 (resolved by 64-5). No PR; no review of an empty diff. The no-op branch should be torn down by SM during finish.

**Handoff:** To SM (Hawkeye) to close 67-3 as done with a resolved-by-ec69c9b note and remove the empty branch. Review phase skipped per user direction (no diff to review).