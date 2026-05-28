---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-12: Comment-guard at peer-reveal capture site (App.tsx) — 'MUST use raw reveals, never merged' to prevent stale-draft regression

## Business Context

Epic 71's completed half cleared the highest-friction findings from the
2026-05-27 `coyote_star` multiplayer playtest. Two of those — 71-5 and 71-13 —
established that MP opening narration and peer-action reveals must route through
the *raw*, per-recipient (firewall-filtered) reveal stream, and that the
persistence/snapshot path must capture from those raw reveals rather than from a
*merged* draft. Using the merged draft reintroduces a **stale-draft regression**:
the merged map blends in `TURN_STATUS` authoritative status for display purposes,
and capturing it carries stale "composing/submitted" state across the round
boundary instead of the clean per-recipient reveal.

This story does not change behavior. It adds an explicit **code comment-guard**
at the peer-reveal capture site in `App.tsx` so a future editor cannot
unknowingly swap the raw reveal source for the merged one and silently re-break
the 71-13 fix. The value is durability: a one-line invariant encoded at the exact
point where the mistake is tempting, protecting an already-shipped correctness
fix. This serves Keith (the dev/maintainer) directly — it is a regression
firewall in the source, not a player-facing surface.

## Technical Guardrails

**File to modify:** `sidequest-ui/src/App.tsx` (only this file).

**Capture site (the guarded region):** the `ACTION_REVEAL` handler inside
`handleMessage`, currently lines **868–872**:

```ts
if (msg.type === MessageType.ACTION_REVEAL) {
  const entry = msg.payload as unknown as ActionRevealEntry;
  setCurrentRound(entry.round);
  peerRevealsApplyRef.current?.(entry);
  return;
}
```

This feeds the *raw* `usePeerReveals` stream (`peerReveals.reveals`). The
snapshot bridge (Story 71-4 / 71-13) captures from that same raw stream:
`peerRevealsSnapshotRef.current = () => persistedPeerActions.capture(currentRound, peerReveals.reveals)` (≈ lines 1324–1325), and the round-resolution branch
calls `peerRevealsSnapshotRef.current?.()` BEFORE `peerRevealsClearRef.current?.()`
(≈ lines 809–817).

**The raw-vs-merged distinction:** `mergedPeerReveals` (≈ lines 1337–1340) is a
`useMemo` over `mergePeerRevealsWithSubmittedStatus(peerReveals.reveals, turnStatusEntries)`.
That merge exists only to fold `TURN_STATUS` authoritative status into the
**display** rows (PeerRevealList). It is a presentation derivation — it must
NEVER be the source for the apply/snapshot/capture path. The comment-guard must
make this explicit at the capture site.

**Pattern to follow:** SideQuest's comment rule — comments explain non-obvious
WHY (a hidden constraint), not WHAT. This comment qualifies: it encodes a real
regression constraint (the stale-draft re-break) that is invisible from the code
alone. Match the existing dated, story-tagged comment style already present
around lines 809–817 and 1328–1336.

**Integration points / what NOT to touch:** Do not alter `usePeerReveals`,
`mergePeerRevealsWithSubmittedStatus`, `usePersistedPeerActions`, the segment
model in `sidequest-ui/src/lib/narrativeSegments.ts`, or any reveal/snapshot
logic. The reveal routing and the raw-capture fix already landed in 71-5/71-13;
this story only adds explanatory text.

## Scope Boundaries

**In scope:**
- Add an explanatory code comment-guard at the `ACTION_REVEAL` peer-reveal
  capture site in `sidequest-ui/src/App.tsx` (≈ lines 868–872) stating that this
  path MUST use the raw per-recipient reveals and MUST NEVER be sourced from the
  merged draft (`mergedPeerReveals`), citing the 71-13 stale-draft regression it
  prevents.

**Out of scope:**
- Any change to reveal capture, merge, snapshot, persistence, or clear logic —
  that behavior landed in 71-5 and 71-13 (both done) and must not be touched.
- Adding the `round` field to `PlayerActionPayload` / round-anchored placement —
  that is 71-10.
- Tests for reveal behavior, contrast/a11y work (71-11), or any other epic-71
  story.

## AC Context

**AC1 — Comment-guard exists at the capture site.**
A code comment appears immediately at/above the `ACTION_REVEAL` handler in
`sidequest-ui/src/App.tsx` (the `peerRevealsApplyRef.current?.(entry)` capture
point, ≈ lines 868–872). For this to pass: the comment must (a) state the
invariant that this path uses the *raw* reveals, (b) explicitly warn never to
source it from the *merged* draft (`mergedPeerReveals` /
`mergePeerRevealsWithSubmittedStatus`), and (c) reference the stale-draft
regression / Story 71-13 that motivates the constraint.
*Verification:* read the file; confirm the comment sits at the capture site and
names both the raw requirement and the merged prohibition.

**AC2 — No behavioral change.**
Only comment text is added; no executable code (the `ACTION_REVEAL` branch, the
snapshot bridge, the merge memo) changes.
*Verification:* `git diff` shows comment-only additions; `npm run build` and
`npx vitest run` pass unchanged (no logic touched).

**AC3 — Comment follows the project comment rule.**
The comment explains the non-obvious WHY (hidden regression constraint), not the
obvious WHAT, and matches the existing dated/story-tagged comment style in the
file.
*Verification:* manual review against the style at lines 809–817 / 1328–1336.

**Edge cases:** None behavioral — this is a documentation-only guard. The only
risk is placing the comment at the wrong site (e.g., at the display-merge memo
instead of the capture handler), which would leave the actual tempting line
unguarded; the comment must sit at the `ACTION_REVEAL` apply call.

## Assumptions

- The peer-reveal capture site remains the `ACTION_REVEAL` handler calling
  `peerRevealsApplyRef.current?.(entry)` (≈ lines 868–872 at time of writing).
  Line numbers may drift; the handler is the stable anchor.
- The raw-vs-merged split is as found: `peerReveals.reveals` is the raw source
  feeding apply/snapshot; `mergedPeerReveals` is display-only. (Confirmed by
  reading App.tsx — no code change validates this beyond inspection.)
- 71-5 and 71-13 are merged and their raw-reveal fix is the current behavior;
  this guard documents that landed state. If either proves reverted, log a
  Design Deviation and notify SM rather than re-implementing the fix here.
