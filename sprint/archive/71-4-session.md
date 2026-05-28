---
story_id: "71-4"
jira_key: null
epic: null
workflow: "tdd"
---

# Story 71-4: Player-action transcript — contrast bump on own-echo + persist peer action post-resolution

## Story Details
- **ID:** 71-4
- **Type:** Bug, 3 points
- **Workflow:** tdd
- **Repo:** sidequest-ui
- **Branch:** feat/71-4-player-action-transcript-contrast-persist

## Problem Statement

Two readability/persistence issues in the multiplayer action visibility subsystem (ADR-036, amended 2026-05-03):

1. **Contrast bump on own-echo**: When a player's own submitted action is echoed back into the narration transcript, the rendering contrast is too low (`text-muted-foreground/70`), making it hard to read. The own action should have higher contrast than peer actions to distinguish it from surrounding narration.

2. **Persist peer action post-resolution**: Peer players' action text (from `ACTION_REVEAL` messages during composition/submission) is currently shown only in the ephemeral `PeerRevealList` UI during the wait phase. Once a turn resolves, the `PeerRevealList` is cleared and peer actions vanish. Per ADR-036 doctrine (collaborative visibility by default), peer action text should be persisted into the main narration transcript/cards so the table can review what each player did after resolution.

## Acceptance Criteria

### AC1: Own-action contrast bump
- [ ] Player's own submitted `player-action` segment in the narrative transcript has visibly higher contrast than peer-contributed segments
- [ ] The CSS styling distinguishes own vs. peer actions (likely via a data attribute or CSS class on the player-action element)
- [ ] Contrast ratio passes WCAG AA accessibility standards (4.5:1 minimum for body text)

### AC2: Peer action persistence
- [ ] When a peer player submits an action (`ACTION_REVEAL` with `status="submitted"`), that action text is recorded and persisted
- [ ] After `TURN_STATUS{status="resolved"}`, the peer action entries appear in the narration card stream alongside or immediately after the turn's `player-action` segments
- [ ] Peer actions render with lower contrast than own actions (visual hierarchy: own > peer > prose)
- [ ] Test: multiplayer session with 2+ players, each player submits, verify both own and peer actions appear in scrollback post-resolution

## Technical Approach

### Part 1: Contrast Bump (Own-Action Styling)
1. Add a data attribute or CSS class to the `player-action` segment renderer to distinguish own vs. peer actions
2. Modify `narrativeRenderers.tsx` `renderSegment()` to accept an optional `isOwnAction` parameter
3. Pass `isOwnAction` from `NarrationCards` or segment builder — will need to wire player_id from state
4. Update CSS in `narrativeRenderers.tsx` or `archetype-chrome.css` to apply higher contrast for own actions (e.g., `text-foreground` instead of `text-muted-foreground/70`)

### Part 2: Peer Action Persistence
1. Extend the `NarrativeSegment` type to support a new `peer-action` kind (or reuse `player-action` with an `is_peer` flag)
2. Extend `buildSegments()` in `narrativeSegments.ts` to accept a `peerActionsMap` parameter (Map<player_id, ActionRevealEntry>)
3. When building segments from `messages`, inject peer action entries at the appropriate turn boundaries — likely immediately after the turn's primary `player-action` (own action), or grouped at turn end
4. Wire the peer reveals from `usePeerReveals` hook into the segment builder
   - Pass `peerReveals.reveals` from `GameBoard` → `NarrationCards` → `buildSegments()`
   - Trigger segment rebuild on peer reveals update (already happens via message flow, but ensure round/turn boundaries align)
5. Add tests:
   - Unit test in `narrativeSegments.ts` validating peer actions appear in the right turn
   - Integration test in action-reveal-wiring validating full end-to-end flow (send ACTION_REVEAL, verify it persists post-TURN_STATUS resolved)

## Implementation Notes

- **Player ID context**: The segment builder currently doesn't track player identity. Will need to pass `currentPlayerId` (or `selfPlayerId`) to `buildSegments()` to know which segments are own vs. peer.
- **Timing**: Peer reveals are ephemeral (cleared on round transition). The segment builder will need a snapshot of the peer reveals at turn resolution time, or we persist them separately.
- **Styling layer**: Both changes are in the rendering/CSS layer — no backend changes needed. Backend already emits ACTION_REVEAL with all necessary metadata.
- **PeerRevealList integration**: The PeerRevealList (currently above InputBar) shows composing/submitted state during the wait phase. This story is about moving that information into the persistent narration transcript post-resolution.

## Sm Assessment

Setup verified for peloton handoff to TEA (Radar O'Reilly) for the RED phase. Two-part UI bug in sidequest-ui, both in the render/CSS layer (no backend — ACTION_REVEAL already carries the metadata):
1. Contrast bump on own-action echo (readability — this is a player-facing surface; Alex the slower reader benefits from legible own-action echo).
2. Persist peer action text in the transcript post-resolution (extends ADR-036's 2026-05-03 collaborative-visibility amendment from wait-phase-only into the persistent narration).

**Routing notes for the team:**
- TEA leads RED — write failing tests for both ACs. Part 2 needs the segment-builder (narrativeSegments.ts buildSegments) to know own-vs-peer identity (currentPlayerId) and to snapshot peer reveals at turn-resolution time (they're ephemeral, cleared on round transition — that's the trap).
- MP / ADR-036 watch for Reviewer: peer-action persistence must respect perception filtering (ADR-104/105) — a peer's action text is only persisted if it was already visible per the collaborative-visibility rule; do NOT surface hidden/sealed actions. (Sealed-visibility is PvP-only and not implemented, but the firewall must not regress.)
- Wiring test required (project doctrine): full ACTION_REVEAL → persisted-segment flow through the real component, not just a buildSegments unit assert.
- Dev: the peer-reveal snapshot-at-resolution is the load-bearing design choice — coordinate with Architect if the ephemeral→persistent bridge needs a new state holder vs. deriving from message history.
- Architect on standby — ADR-036/104/105 perception implications make this worth a spec-check at green.

Branch off current develop (c8e0546, includes 71-3). A previous lane's uncommitted WIP (3 archetype-chrome CSS files) is in the shared checkout — do NOT stage/disturb. Clear to hand to TEA.

## Delivery Findings

### TEA (test design)
- **Question** (non-blocking): The wiring threads `peerActions: Map<round, ActionRevealEntry[]>` into the narration component. I inferred the prop name `peerActions` on `NarrationCards`. Dev should confirm the prop name and — critically — wire ALL THREE narration components (`NarrationScroll` is the production default per `NarrativeView`, plus `NarrationFocus`, `NarrationCards`), not just one. Affects `NarrativeView.tsx` + the three components. *Found by TEA during test design.*
- **Gap** (blocking for AC2): The snapshot-before-clear capture must be added to App's `TURN_STATUS{resolved}` handler (`App.tsx:792-799`) BEFORE `peerRevealsClearRef.current?.()` fires, and the resulting accumulator threaded App → GameBoard → NarrativeWidget → NarrativeView → narration component (5 hops). Partial wiring = half-feature; the e2e wiring test only passes when the full chain renders the persisted segment. *Found by TEA during test design.*
- **Question** (non-blocking): In MP, does the client receive peers' `PLAYER_ACTION` in `messages`, or only its own? The locked design assumes `messages` PLAYER_ACTION = own (is_peer absent) and peers arrive only via the accumulator. If peer PLAYER_ACTION frames also land in `messages`, own/peer detection needs `currentPlayerId` in buildSegments too. Dev/Architect to confirm. *Found by TEA during test design.*

### Dev (implementation)
- **Resolved (TEA's PLAYER_ACTION question):** traced both ends — server never `room.broadcast(PlayerActionMessage(...))` (peer visibility is ACTION_REVEAL + TURN_STATUS only); client `handleMessage` has no PLAYER_ACTION case (own enters `messages` via the optimistic `setMessages` in `handleSend`). So PLAYER_ACTION in `messages` is OWN-ONLY by construction → `selfPlayerId` correctly dropped from the contract; own/peer = source (message vs accumulator). *Confirmed by Dev during implementation.*
- **Improvement** (non-blocking, DEFERRED): peer actions do not survive a WS reconnect — the server does not replay ACTION_REVEAL into narration, so the persisted accumulator is reset on the reconnect messages-purge (App.tsx, kept consistent with the wiped scroll). Pre-existing ephemeral-channel limitation (ADR-036), NOT a regression. Affects `App.tsx` reconnect handler + `usePersistedPeerActions`. Out of 71-4 scope; would need a server-side replay of resolved peer actions. *Found by Dev during implementation.*

### Reviewer (code review)
- **Question / Improvement** (non-blocking): `capture` is called with the RAW `peerReveals.reveals` (`App.tsx:1325`), not `mergedPeerReveals`. In the race where a peer's `TURN_STATUS{submitted}` arrives but their last `ACTION_REVEAL` was still `composing`, `mergePeerRevealsWithSubmittedStatus` would upgrade the status to submitted whereas the raw map still reads composing — so `capture` (submitted-only filter) OMITS that peer from the persistent transcript. This **fails closed** (peer absent, never shown with unverified text) so it is NOT a firewall regression — and arguably the *current behavior is preferable*: using `mergedPeerReveals` would persist the stale `composing` TEXT under a `submitted` label (the final edited text never arrived via ACTION_REVEAL). So this is a genuine AC2-completeness vs text-accuracy tradeoff, not a clear bug. Affects `App.tsx:1325` / `usePersistedPeerActions`. Surfaced for Architect's call (he authored the contract); non-blocking either way. *Found by Reviewer + reviewer-security during code review.*
- **No firewall finding.** Independently traced peer-text provenance end-to-end and confirm the Architect's by-construction claim: server-filtered ACTION_REVEAL → `usePeerReveals.reveals` (self-dropped at usePeerReveals.ts:57) → `capture(currentRound, peerReveals.reveals)` (App.tsx:1324-1325, before clear at :817) → `persistedPeerActions.byRound` → `peerActionsByRound` (App.tsx:2182) → `buildSegments` `pushPeerRound` `text: entry.action`. No TURN_STATUS/messages/snapshot origin for peer text. Firewall INTACT. *Confirmed by Reviewer during code review.*

## Architect Assessment (spec-check)

**Focus:** Perception-firewall integrity (ADR-104/105) + correct extension of ADR-036 collaborative visibility. Verified against the GREEN code at `c764159`, not the summary.

**Spec Alignment:** Aligned. **Firewall: INTACT (by construction).** **Mismatches: none blocking.**

### Firewall verification (the load-bearing check) — PASS
- **Single source for peer text.** Peer-action text enters the transcript through exactly one path: `buildSegments`'s `pushPeerRound()`, which reads `entry.action` ONLY from the `peerActionsByRound` accumulator (`narrativeSegments.ts`). No peer branch reads `action`/text off a `TURN_STATUS`, `ACTION_REVEAL`, or any `messages` frame. Confirmed by reading the diff — the only `text: entry.action` is inside `pushPeerRound`.
- **Accumulator is downstream of the firewall.** The accumulator is fed solely by `usePersistedPeerActions.capture(round, reveals)`, where `reveals` is `usePeerReveals.reveals` — strictly downstream of the ADR-105 broadcast firewall and the reducer's self-drop/seq-monotonicity. No new fetch, no new origin. Persisting "what was visible in wait-phase" cannot surface "what was hidden." Invariant holds.
- **Submitted-only + dedup.** `capture` filters `status==="submitted"` and dedups per `player_id` within the round (`usePersistedPeerActions.ts:38-52`). A composing-only reveal never persists.
- **Capture beats the wipe.** In App's `TURN_STATUS{status==="resolved"}` branch, `peerRevealsSnapshotRef.current?.()` runs immediately BEFORE `peerRevealsClearRef.current?.()` (`App.tsx:806` region). Snapshot precedes clear — the sharp edge is correct.
- **Reset on reconnect.** `persistedPeerActionsResetRef` is wired to the reconnect messages-purge (`App.tsx:667` region), keeping the accumulator consistent with the wiped scroll. The reconnect non-survival is a pre-existing ephemeral-channel limitation (ADR-036), correctly logged by Dev as a deferred finding — not a regression.

### Contract adherence (A–E) — PASS
- A: `is_peer?` + `character_name?` on `NarrativeSegment`, peer=true polarity. ✓
- B: own `text-foreground` / peer `text-muted-foreground`, `/70` opacity removed from BOTH, `data-peer="true|false"` marker on the player-action element. ✓ Peer rows prefix `character_name: ` for attribution — a sound, in-spec rendering choice.
- C: turn-boundary placement at `NARRATION_END`, positional i-th-boundary←i-th-round. ✓
- D: `buildSegments(messages, peerActionsByRound?: Map<number, ActionRevealEntry[]>)`, positional, single Map; prop name consistent at every layer; **both** turn-grouping gates excluded — `groupIntoTurns` (NarrationCards) AND `buildTurnPages.isTurnStarter` both guard `&& !is_peer`. ✓ Wired through all three narration components (Scroll default + Focus + Cards). ✓
- E: firewall invariant — confirmed above.

### Findings (non-blocking)
1. **Dev's after-loop fallback — ACCEPTED, firewall-neutral.** The fallback appends any captured round with no matching `NARRATION_END` boundary at the end of the segment list. Source is still exclusively the accumulator, so it introduces no firewall exposure. It also can't double-render: `turnBoundaryIndex` advances per `NARRATION_END` and the fallback starts at that index, so each captured round is emitted exactly once. Necessary for the e2e harness (no narration frames) and as a transient safety net before a just-resolved turn's `NARRATION_END` lands. Good call.
2. **Positional-placement fragility — KNOWN LIMITATION of the contract I authored, ACCEPTED for 71-4.** The "i-th boundary ← i-th captured round" rule is exact only when every turn that produced a `NARRATION_END` also produced a captured peer round. A peer-less round (e.g. a solo moment, or a mid-session join) would shift subsequent placements by one. This is **firewall-safe** (still accumulator-only) and **cosmetic** (a peer line could attach to an adjacent turn). It is a limitation of the no-round-in-`PLAYER_ACTION` constraint I pinned, NOT a Dev defect — Dev implemented the contract faithfully. In the steady-state MP submit-barrier case (all seated players submit every round) placement is correct. **Recommend a follow-up refinement** if precise placement under peer-less rounds is ever needed: anchor by tagging the own `player-action` segment with its round (requires the server to add `round` to `PlayerActionPayload`, or the client to stamp it at `handleSend` from `currentRound`). Logging as a candidate, not blocking.
3. **Process hygiene (NOT a code finding) — uncommitted CSS WIP in the shared checkout.** `git status` shows `src/styles/archetype-chrome.css`, `src/index.css`, and `src/__tests__/chrome-archetype-css.test.ts` modified in the working tree (a terminal-archetype `em`-color legibility fix, unrelated to 71-4). These are NOT in commit `c764159` — 71-4's commit is exactly the 10 story files, clean. This matches the SM's setup warning ("a previous lane's uncommitted WIP — do NOT stage/disturb"). **Action for whoever opens 71-4's PR: do NOT `git add -A`** — stage only 71-4's files so the other lane's WIP doesn't ride into this PR.

**Decision:** Proceed to review. Firewall intact, contract met, scope clean. Reviewer to manually confirm the WCAG 4.5:1 token math against the genre themes (per TEA's logged deviation) and to keep the uncommitted CSS WIP out of the 71-4 PR.

## Design Deviations

### TEA (test design)
- **WCAG AA contrast asserted at token level, not computed ratio**
  - Spec source: 71-4 AC1 (contrast ratio passes WCAG AA 4.5:1)
  - Spec text: "Contrast ratio passes WCAG AA accessibility standards (4.5:1 minimum for body text)"
  - Implementation: Tests assert the high-contrast `text-foreground` token on own actions vs the `text-muted-foreground` token on peer actions; jsdom cannot compute rendered contrast ratios.
  - Rationale: jsdom has no layout/color engine; the token distinction is the testable proxy. Actual 4.5:1 verification is a Reviewer/manual concern.
  - Severity: minor
  - Forward impact: Reviewer should manually confirm the chosen foreground token meets 4.5:1 against the card background.
- **E2E wiring test mirrors App's capture in a Host harness**
  - Spec source: project wiring doctrine + SM Assessment routing note
  - Spec text: "full ACTION_REVEAL → persisted-segment flow through the real component"
  - Implementation: The wiring Host reproduces App's snapshot-before-clear handler (real `useGameSocket` + real `usePeerReveals` + real `NarrationCards`), rather than mounting all of `App`.
  - Rationale: App is too large to mount in a focused wiring test; the existing `action-reveal-wiring.test.tsx` established this Host-mirror pattern. The real socket, hook, and component are exercised; only the App glue is mirrored.
  - Severity: minor
  - Forward impact: Dev's actual App capture logic must match the Host's filter(submitted)+dedup(player_id,round) semantics; Reviewer should diff the two.

### Dev (implementation)
- **buildSegments placement adds an after-loop fallback beyond the positional boundary rule**
  - Spec source: Architect CORRECTED-FINAL contract (placement)
  - Spec text: "peer group at the resolved round's turn boundary, after the own narration block, seq order; positional i-th-boundary←i-th-round"
  - Implementation: kept the positional i-th-NARRATION_END←i-th-round emission AND added an after-loop pass that appends any captured peer rounds with no matching NARRATION_END boundary at the end of the transcript.
  - Rationale: the e2e harness (and any transcript with no narration frames yet) sends ACTION_REVEAL + TURN_STATUS only — neither enters `messages` — so there is no NARRATION_END to anchor to; without the fallback the persisted peer text never renders and the e2e presence-assertions fail. In production every resolved round's NARRATION_END is in `messages`, so the boundary path handles placement; the fallback is a safety net. Firewall-neutral (peer text still sourced exclusively from the accumulator).
  - Severity: minor
  - Forward impact: none functional; flagged to Architect for spec-check confirmation. Placement of a captured round only changes (boundary vs end) in the degenerate no-NARRATION_END case.
- **`capture(round, reveals)` groups by the passed round, not `entry.round`**
  - Spec source: `usePersistedPeerActions.test.tsx` (TEA hook RED) + e2e Host bridge
  - Spec text: "capture(round, reveals): ... accumulates into byRound[round]"
  - Implementation: hook groups submitted reveals under the passed `round` arg (matches the hook RED test exactly). App calls `capture(currentRound, peerReveals.reveals)`. The e2e Host groups by `entry.round`; behaviorally identical because usePeerReveals only ever holds the current round's reveals, so `currentRound === entry.round`.
  - Rationale: the hook RED test pins `capture(round, reveals)`; matched it. Behaviorally equivalent to the Host's `entry.round` grouping under the usePeerReveals single-round invariant.
  - Severity: trivial
  - Forward impact: none — same byRound result under the single-round-reveals invariant.

### Reviewer (audit)
- **TEA: "WCAG AA asserted at token level, not computed ratio"** → ✓ ACCEPTED by Reviewer. jsdom genuinely cannot compute rendered contrast; the token assertion is the right unit-test proxy. I performed the manual ratio check (see Reviewer Assessment → WCAG): own (`text-foreground`) passes 4.5:1 with a large margin in both base themes; peer (`text-muted-foreground`) is comfortable in dark and borderline-at-threshold in the base light theme — recorded as a LOW non-blocking observation. Deviation is sound.
- **TEA: "E2E wiring Host mirrors App's capture"** → ✓ ACCEPTED by Reviewer. I diffed Dev's actual App resolved-branch capture (`usePersistedPeerActions.capture`: filter `status==="submitted"`, dedup per `player_id`, group by round — App.tsx:1324-1325) against the e2e Host's inline bridge (test :97-105: identical filter + dedup, group by `e.round`). **Functionally identical** under the single-round-reveals invariant (`currentRound === entry.round`). The e2e proves the right thing.
- **Dev: after-loop fallback** → ✓ ACCEPTED (concur with Architect: accumulator-only source, emits each round once via the advancing boundary index, firewall-neutral; necessary for the no-NARRATION_END harness case).
- **Dev: capture groups by passed `round` not `entry.round`** → ✓ ACCEPTED (trivial; equivalent under the single-round invariant, matches the hook RED contract).
- No undocumented deviations found.

### Architect (reconcile)

Reviewed every prior deviation entry (TEA ×2, Dev ×2, Reviewer audit) against the shipped code at `c764159`. All five are accurate, substantive, and match what I verified independently at spec-check — no corrections needed. Confirmed the implementation reconciles with the story context, the contract I pinned (A–E), and ADR-036/104/105.

**RULING — Potter's LOW-1 (capture passes RAW `peerReveals.reveals`, not `mergedPeerReveals`): RATIFIED as correct intended behavior. Fail-closed is the contract.**

- Traced the two maps. `mergePeerRevealsWithSubmittedStatus(peerReveals.reveals, turnStatusEntries)` (App.tsx:1337-1340) overrides a peer's status to `submitted` for the **PeerRevealList display** whenever TURN_STATUS says submitted — even if that peer's last ACTION_REVEAL was still `composing`. `capture(currentRound, peerReveals.reveals)` (App.tsx:1324-1325) deliberately uses the **raw** map.
- The race: peer X's final submitted ACTION_REVEAL is lost/late, so the raw map holds X at `composing` carrying X's **composing-stage draft text**, while TURN_STATUS{submitted} has arrived. Merged would mark X submitted → `capture` would persist X's *draft* under a "submitted" label. Raw keeps X at composing → the `status==="submitted"` filter drops X → X is omitted.
- **Why raw is right:** this is a persistent transcript the table reviews after the fact. The cost of merged is persisting **text the player never committed** (a half-typed or pre-edit draft) and attributing it to them as their final action — a correctness defect in a permanent record. The cost of raw is **omitting** a peer in the narrow window where their final reveal was lost. For a transcript, *accuracy of attributed text outweighs completeness*. Never persist unverified text under a submitted label. This also matches the project's fail-loud / no-silent-fallback ethos: omit rather than silently record wrong words.
- **Not a deviation from my contract.** My pinned §E specified the capture source as "a snapshot of the already-revealed `peerReveals.reveals` map" — i.e. raw. Dev implemented exactly that. I'm ratifying it as the deliberate, correct design point, and I concur with Potter and the lead.
- **Forward-impact guard:** the codebase now has BOTH a raw path (capture) and a `mergedPeerReveals` (display). A future maintainer could "helpfully" wire merged into capture and silently reintroduce the stale-draft bug. **Recommend a one-line inline comment at the capture site** (App.tsx:1324) stating capture MUST use raw, never merged, with the reason. Low-effort regression fence; flag for Dev to add (non-blocking — can ride a later touch of that file).

**Potter's LOW-2 (peer `text-muted-foreground` ~4.5:1, 0.04 margin in light base theme; genre `theme_css` may shift per-genre tokens): ACCEPTABLE AS-IS for 71-4; recommend a small follow-up.**

- AC bar is met: AC1 (own ≥ 4.5:1) passes with a large margin; AC3 requires only peer < own (hierarchy holds). No AC requires peer to independently clear 4.5:1 — peer is the de-emphasized register by design.
- The residual concern is genuine but minor: peer text sits right at the AA threshold in the light base theme, and server-injected per-genre `theme_css` (not in the repo, so unverifiable here) could push a given genre's `--muted-foreground` below it.
- **Recommend a follow-up story** (not blocking 71-4): an empirical axe/devtools contrast sweep of the peer action register across the live genre themes; if any genre drops peer below ~4.5:1, bump that genre's peer token. This pairs naturally with per-genre theme a11y QA and isn't specific to this story's logic. Your call on backlog priority.

**AC deferrals:** none. All ACs DONE. The reconnect non-survival is a pre-existing ephemeral-channel sub-limitation (Dev's deferred finding), not an AC deferral — no cross-check needed.

**Reconcile verdict:** Reconciles clean. Firewall intact (three-pass verified), contract A–E met, fallback blessed, raw-vs-merged ratified as fail-closed-correct. Clear to finish — with the selective staging the lead noted (keep the 3 archetype-chrome WIP files OUT of the 71-4 PR).

## TEA Assessment

**Tests Required:** Yes
**Status:** RED — 6 failing (ready for Dev), 5 guards passing. Lint clean.

**Test Files:**
- `src/__tests__/player-action-transcript-71-4.test.tsx` — AC1 contrast + AC2 unit/firewall/focus
- `src/__tests__/peer-action-persistence-wiring-71-4.test.tsx` — AC2 end-to-end wiring

**RED (failing for the right reason):**
| Test | AC | Why RED |
|------|----|---------|
| own player-action higher contrast than muted default | AC1 | all actions use `text-muted-foreground/70` today |
| own vs peer distinct contrast classes | AC1 | own==peer today |
| buildSegments persists submitted peer reveal as is_peer segment | AC2 | buildSegments ignores 2nd param |
| peer action not a turn-page starter (buildTurnPages) | AC2 | peer player-action currently starts a new page |
| e2e: submitted peer action survives TURN_STATUS{resolved} | AC2 | persistence path unimplemented |
| e2e: dedup one-per-peer | AC2 | persistence path unimplemented |

**Guards (passing now, must keep passing):**
- AC1 peer player-action stays muted
- AC2 buildSegments firewall (entry absent from map → not rendered)
- AC2 single-player unchanged (no accumulator → no peer segs)
- AC2 component-boundary firewall (TURN_STATUS-borne action text never surfaces)
- AC2 e2e composing-only reveal does not persist

**Pinned to Architect ruling A1:** `buildSegments(messages, peerActions: Map<round, ActionRevealEntry[]>)`; peer actions reuse `player-action` kind + `is_peer:true`; own=is_peer absent (high contrast), peer=is_peer true (lower); placement at round turn boundary; peer action not a turn-page starter; snapshot at resolved filtered to submitted + deduped.

**Handoff:** To Dev for GREEN.

---

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed (commit c764159, pushed):**
- `src/lib/narrativeSegments.ts` — `NarrativeSegment` gains `is_peer`/`character_name`; `buildSegments(messages, peerActionsByRound?)` emits is_peer player-action segments at each round's turn boundary (positional + after-loop fallback); `buildTurnPages` isTurnStarter excludes is_peer
- `src/components/narrativeRenderers.tsx` — player-action own (`text-foreground`/`data-peer="false"`) vs peer (`text-muted-foreground`/`data-peer="true"`); `/70` opacity removed; peer shows `character_name: text`
- `src/hooks/usePersistedPeerActions.ts` (NEW) — `{ byRound, capture(round, reveals), reset }`; submitted-only + dedup per (player_id, round)
- `src/components/NarrationCards.tsx` — `peerActionsByRound` prop → buildSegments; `groupIntoTurns` excludes is_peer
- `src/components/NarrationScroll.tsx`, `NarrationFocus.tsx`, `src/screens/NarrativeView.tsx`, `GameBoard/widgets/NarrativeWidget.tsx`, `GameBoard/GameBoard.tsx` — thread `peerActionsByRound` (full production chain; Scroll is the default)
- `src/App.tsx` — `usePersistedPeerActions`; snapshot-before-clear via `peerRevealsSnapshotRef` in the resolved branch; `reset` on reconnect purge; `peerActionsByRound` → GameBoard

**Tests:** 16 new green (9 unit + 3 e2e wiring + 4 hook); 5 guards stay green. Full client suite **1638/1638** (163 files). tsc 0. eslint clean (1 pre-existing unrelated `displayName` warning).

**Wiring (doctrine):** full 5-hop chain App→GameBoard→NarrativeWidget→NarrativeView→{NarrationScroll(default)|NarrationFocus|NarrationCards}; e2e proves the ACTION_REVEAL→resolved-snapshot→persisted-segment flow through the real units.

**Firewall:** peer text sourced exclusively from the firewall-filtered accumulator — never a TURN_STATUS frame; held by construction (Architect spec-check requested).

**WCAG:** own `text-foreground` (~15:1), peer `text-muted-foreground` (~4.5:1 light / ~7:1 dark) in the base theme; the AA-breaking `/70` opacity removed. Per-genre themes individually responsible.

**Branch:** feat/71-4-player-action-transcript-contrast-persist — commit c764159, pushed.

**Handoff:** To review (Colonel Potter), pending Architect (Major Houlihan) firewall spec-check.

### Reconciliation to CORRECTED-FINAL contract (commit ca831d3)

Tests re-pinned to the Architect corrected-final contract (supersedes earlier interface notes):
- `is_peer?: boolean` (snake) + `character_name?: string` on `NarrativeSegment`; **no `selfPlayerId`** (own-vs-peer is by source — server never re-broadcasts PLAYER_ACTION to peers).
- `buildSegments(messages, peerActionsByRound?: Map<number, ActionRevealEntry[]>)` — positional 2nd param.
- Render markers: own → `data-peer="false"` + `text-foreground`; peer → `data-peer="true"` + `text-muted-foreground`. **`/70` opacity deleted** (the AC1 bug). Tests assert the marker + token, not exact Tailwind/WCAG ratio.
- Two turn-grouping gates both exclude peers: `groupIntoTurns` (NarrationCards) + `isTurnStarter` (narrativeSegments).
- New `hooks/usePersistedPeerActions.ts` seam: `{ byRound; capture(round, reveals) [submitted-only + dedup by player_id]; reset() }`; `capture` called at `TURN_STATUS{resolved}` **before** `usePeerReveals.clear()`.
- `NarrationCardsProps` gains only `peerActionsByRound` (must be threaded to all three narration components).

**Final RED tally:** 8 assertion-level failures (verified right reason) + 4 guards green; the `usePersistedPeerActions` hook file is RED via missing-module import (expected until Dev creates the hook — its 4 assertions become live then).

**Test files:**
- `src/__tests__/player-action-transcript-71-4.test.tsx` (AC1 + AC2 unit/firewall/grouping/regression)
- `src/__tests__/peer-action-persistence-wiring-71-4.test.tsx` (e2e wiring)
- `src/hooks/__tests__/usePersistedPeerActions.test.tsx` (snapshot-seam hook)

## Subagent Results

Toggles (`workflow.reviewer_subagents`): only `preflight` + `security` enabled; the other seven disabled, pre-filled Skipped.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (1638/1638; 16 new tests; tsc 0; lint clean 1 pre-existing; 0 smells) | confirmed 0, dismissed 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled — self-assessed (capture/clear ordering, dedup, peer-less round) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled — self-assessed (no swallowed errors) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled — self-assessed (16 tests, incl. 2 firewall negatives) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled — self-assessed (comments accurate, cite ADRs) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled — self-assessed (is_peer optional flag, Map types) |
| 7 | reviewer-security | Yes | findings | 1 LOW (raw-vs-merged reveals, fails closed — not a leak) | confirmed 1 (non-blocking), firewall CLEAN |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled — self-assessed (minimal, one render path flag-differentiated) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled — Rule Compliance by Reviewer |

**All received:** Yes (2 enabled returned; 7 disabled, pre-filled Skipped)
**Total findings:** 0 blocking. 2 LOW non-blocking (security raw-vs-merged completeness gap; peer-contrast borderline in base light theme). Firewall CLEAN (independently verified + security + Architect concur).

## Reviewer Assessment

**Verdict:** APPROVED

The load-bearing risk — a perception-firewall leak of hidden peer actions into the persistent transcript — is cleared. I independently traced peer-text provenance end-to-end (not just trusting the Architect's claim or the guard tests) and confirmed there is exactly one source, and it is firewall-filtered. Clean, well-tested, well-documented work.

**Dispatched subagent coverage (tags):**
- `[SEC]` reviewer-security (enabled): firewall CLEAN — peer text sourced only from the accumulator; TURN_STATUS case reads only `player_name`/`status` (never `.action`); `is_peer` strict-equality (no own/peer mislabel); no `dangerouslySetInnerHTML` on peer text (JSX text node); no peer-content logging. One LOW completeness-gap (raw-vs-merged reveals, fails closed) — confirmed non-blocking.
- `[EDGE]` (disabled — self-assessed): capture-before-clear ordering correct (App.tsx:813 before :817); dedup per player_id; composing-only excluded; the peer-less-round positional shift is the Architect's known limitation → follow-up 71-10. The raw-vs-merged race is the one real edge (LOW, fails closed).
- `[SILENT]` (disabled — self-assessed): no swallowed errors; `capture` early-returns on empty submitted set (benign); reset is a no-op when empty.
- `[TEST]` (disabled — self-assessed): 16 tests — 9 unit (incl. two explicit firewall negatives: "does NOT persist… even if its text rides a broader frame" and "NarrationCards never surfaces peer text carried by a TURN_STATUS frame"), 3 e2e wiring (submitted survives resolved+clear; composing-only doesn't persist; dedup), 4 hook. The empty-map-vs-no-arg single-player regression test is a nice touch. Behavioral, not source-grep.
- `[DOC]` (disabled — self-assessed): comments are accurate and load-bearing — the usePersistedPeerActions docstring correctly states the firewall invariant and the e2e-Host-mirror intent; the buildSegments comment correctly states peer text derives only from the accumulator. No stale/misleading docs.
- `[TYPE]` (disabled — self-assessed): `is_peer?: boolean` optional flag (own omits, peer sets) is a clean discriminator; `Map<number, ActionRevealEntry[]>` typed; no `as any`, no non-null abuse. tsc exit 0.
- `[SIMPLE]` (disabled — self-assessed): minimal and DRY — one render path flag-differentiated (not a duplicate peer renderer), reuses the existing reveals/segment machinery. No over-engineering.
- `[RULE]` (disabled — self-assessed): see Rule Compliance.

### Independent firewall trace (the load-bearing check) — INTACT

Server-filtered `ACTION_REVEAL` → `usePeerReveals.reveals` (self dropped at `usePeerReveals.ts:57`) → `peerRevealsSnapshotRef` = `capture(currentRound, peerReveals.reveals)` (`App.tsx:1324-1325`), invoked at `TURN_STATUS{resolved}` (`:813`) BEFORE `clear()` (`:817`) → `usePersistedPeerActions.capture` (submitted-only filter + dedup per player_id) → `persistedPeerActions.byRound` → `peerActionsByRound={…}` (`App.tsx:2182`) → all three narration components → `buildSegments(messages, peerActionsByRound)` → `pushPeerRound` → `text: entry.action`. **The only source of peer-action text is the firewall-filtered accumulator.** Verified buildSegments' TURN_STATUS and PLAYER_ACTION cases do not read `.action` for peer text. Persisting "what was visible" cannot surface "what was hidden."

### Wiring — all three components (not half-wired)

`NarrationScroll` (production default, `:26`), `NarrationFocus` (`:30`), `NarrationCards` (`:61`) each thread `peerActionsByRound` into `buildSegments`, via App.tsx:2182 → GameBoard (206/267/433) → NarrativeWidget (15/23/28) → NarrativeView (16/19/30) → LayoutComponent. Behavioral e2e test + the two firewall-negative unit tests confirm reachability. A Cards-only half-wire (which would pass unit but fail production NarrationScroll) is ruled out.

### WCAG manual check (jsdom can't compute — TEA's logged deviation)

Base tokens (`index.css`, OKLCH); player-action renders on `bg-card/50`:
- **Own = `text-foreground`:** light `0.145` (near-black) on card `0.98` → ≈14-15:1; dark `0.985` on card `0.205` → comfortable. **PASS with large margin, both themes.** The old `text-muted-foreground/70` (the AC1 readability bug) is removed — AC1 satisfied.
- **Peer = `text-muted-foreground`:** dark `0.708` on card `0.205` → ≈5.7:1, **PASS**; light `0.556` (≈#737373) on card `0.98` → **≈4.5:1, right at the threshold.**
- own > peer holds (foreground > muted-foreground). AC3 (peer lower than own) satisfied.

**[LOW / non-blocking] Peer-contrast borderline:** in the base LIGHT theme, peer text uses the standard `text-muted-foreground` token, which lands ≈4.5:1 on the card — at the WCAG AA threshold. This (a) satisfies the ACs (AC1's 4.5:1 is for the own-action bump, which passes comfortably; AC3 only requires peer < own), (b) uses the app-wide design-system muted token, not anything 71-4 invented, and (c) is a strict improvement over the prior `/70` opacity. Honest caveat: precise OKLCH→sRGB→WCAG computation at a ~0.04 margin isn't reliable by hand, and genre `theme_css` (server-injected from sidequest-content, not in this repo) may shift the muted/card tokens per genre — so I cannot certify peer ≥4.5:1 across all genres from the repo alone. Recommend an empirical contrast check (devtools / axe) if strict peer-AA across every genre is desired; ties to TEA's logged jsdom-can't-compute deviation. Not a 71-4 blocker.

### Rule Compliance

TypeScript lang-review (`.pennyfarthing/gates/lang-review/typescript.md`):
| # | Rule | Verdict |
|---|------|---------|
| 1 | Type-safety escapes | PASS — no `as any`/`@ts-ignore`/non-null abuse in diff |
| 4 | Null/undefined | PASS — optional `is_peer?`, `peerActionsByRound?` guarded; `?? []` defaults |
| 6 | **React/JSX** | PASS — `useMemo` deps include `peerActionsByRound`; new hook deps correct; no `dangerouslySetInnerHTML` on peer text; `useState`/`useCallback` stable |
| 8 | Test quality | PASS — specific assertions, firewall negatives, single-player regression; behavioral |
| 10 | Input validation | PASS — peer text rendered as escaped JSX text node |
| 2,3,5,7,9,11,12,13 | (generics/enum/module/async/build/error/perf/fix-regress) | N/A or PASS — none implicated |

Project rules (`sidequest-ui/CLAUDE.md`): No Silent Fallbacks — PASS (capture early-return benign; reset no-op). No Stubbing — PASS. Wire Up What Exists — PASS (reuses reveals/segment machinery). Verify Wiring — PASS (e2e through real components, all three). Every Test Suite Needs a Wiring Test — PASS (peer-action-persistence-wiring e2e). No Source-Text Wiring Tests — PASS (behavioral). OTEL — N/A (cosmetic render/CSS, no subsystem decision; CLAUDE.md exempts cosmetic UI).

### Devil's Advocate

Hardest attack — **leak a hidden peer action.** The only peer-text source is the accumulator, fed solely by `peerReveals.reveals`, which is downstream of the server broadcast firewall (ADR-105) and drops self. There is no code path reading `.action` from TURN_STATUS, a snapshot, or `messages` frames addressed to others (verified by me + security + Architect, three independent passes). Can't leak. **Stale-text attack:** the raw-vs-merged gap (security LOW) means a TURN_STATUS-ahead race omits a peer — but it fails CLOSED (omit, never show stale/unverified text), so it's safer, not leakier. **Double-render attack:** the boundary index advances per NARRATION_END and the after-loop fallback starts at that index → each captured round emits once (Architect verified; I concur). **Identity-leak via styling:** `is_peer` is set only in `pushPeerRound`; renderer branches on strict `=== true`; own (PLAYER_ACTION) never sets it → no path renders peer text as own or vice versa. **Placement drift:** a peer-less round shifts positional placement (Architect's known limitation → 71-10) — cosmetic, firewall-safe. **Contrast:** peer light is at threshold (LOW). Nothing the devil surfaced is blocking; the firewall is airtight.

### Non-blocking observations (summary)
- **[LOW]** Security raw-vs-merged completeness gap (App.tsx:1325) — fails closed; arguably current behavior is preferable (avoids stale composing-text). Architect's call.
- **[LOW]** Peer-contrast borderline in base light theme (~4.5:1) — standard muted token, satisfies ACs, improves on `/70`; recommend empirical per-genre check.
- **[INFO]** e2e Host groups by `entry.round`, production by `currentRound` param — equivalent under single-round invariant (Dev logged it).

**Data flow traced:** ACTION_REVEAL (server-filtered) → reveals (self-dropped) → capture-before-clear → byRound → buildSegments peer segment → escaped JSX text. Own action: PLAYER_ACTION message → buildSegments (is_peer absent) → text-foreground. Safe at every hop.

**Handoff:** APPROVED → Architect for spec-reconcile → finish. PR hygiene: keep the 3 uncommitted archetype-chrome WIP files out of the 71-4 PR (stage only the 13 committed files).