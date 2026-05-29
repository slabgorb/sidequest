# Epic 71: Playtest bugfix — uncovered findings (coyote_star MP, 2026-05-27)

## Overview

Epic 71 is the catch-all bugfix bucket for open playtest findings from the
2026-05-27 `coyote_star` multiplayer run (plus carryover) that are **not** owned
by any other in-flight epic. Findings were cross-referenced from the ping-pong
tracker and triaged: anything already claimed by epics 59/61/63/64/65/66/67/68/
69/70 was excluded, leaving this epic as the home for the residue. The work spans
two repos — `sidequest-ui` (transcript contrast/a11y, regression comment-guards,
test migration) and `sidequest-server` (intent-router confidence gating,
room-graph per-transition mechanics, scene-harness dev-gate doctrine, pyright
hygiene, peer-action round anchoring).

Seven of the seventeen stories landed during the playtest-fix burst (71-1
through 71-7, plus 71-13). The remaining nine are open: type-hygiene cleanups
(71-8, 71-9, 71-14), a peer-action transcript round-anchor refactor (71-10), a
per-genre contrast a11y sweep (71-11), a regression-guard comment (71-12), and
three ADR-driven mechanical/doctrine stories (71-15 ADR-055, 71-16 ADR-113,
71-17 ADR-092).

**Priority:** P2
**Repo:** sidequest-ui, sidequest-server
**Stories:** 17 (9 open: 71-8, 71-9, 71-10, 71-11, 71-12, 71-14, 71-15, 71-16, 71-17)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-055 Room Graph Navigation** (`docs/adr/055-room-graph-navigation.md`) | §Trope Integration (per-transition `tick_on_room_transition`), §Resource Depletion (`uses_remaining` decrement on transition), §Implementation Status "Confirmed: NOT wired" — drives 71-15 |
| **ADR-113 Intent Router — Mechanical-Engagement Spine** (`docs/adr/113-intent-router-mechanical-engagement-spine.md`) | §Confidence gate (per-subsystem threshold, default 0.6), `DispatchPackage.dispatch[].confidence`, OTEL `intent_router.dispatch.{subsystem}` spans — drives 71-16 |
| **ADR-092 Scene Harness — Dev-Gated HTTP Endpoint** (`docs/adr/092-scene-harness-http-endpoint.md`) | §Decision item 1 (`DEV_SCENES=1` gate) vs §"Design evolution: DEV_SCENES gate removed" (Cloudflare Zero Trust tunnel gating) — the doctrine conflict 71-17 must resolve |
| **ADR-094 Orrery Label Placement** (`docs/adr/094-orrery-label-placement-strategies.md`) | Curved/radial-out strategies, upright-flip on far-arc tangent labels — landed in 71-2 |
| **ADR-107 Out-of-Band Aside Channel** (`docs/adr/107-out-of-band-aside-channel.md`) | MP peer-mirror / `ActionRevealPayload` segment model — context for the transcript-fanout stories (71-10/71-12/71-13) |

## Background

This epic exists because the 2026-05-27 `coyote_star` multiplayer playtest
surfaced a long tail of small, real findings — UI contrast and POV slips,
transcript fanout ordering, narration person-agreement, and unwired ADR
mechanics — that did not fit cleanly into any of the focused epics already in
flight. Rather than scatter these across unrelated epics or let them rot in the
ping-pong tracker, they were collected here as an explicit residue bucket.

The triage rule is what defines the epic: a finding belongs in 71 **only if** no
other epic owns it. Dispatch-bank consolidation (59-11), the reference-renderer
work (epic 63), MP-resilience (epic 67), genre-tone (epic 68), gameboard-UX
(epic 69), and daemon-media (epic 70) all carve out their own findings; what
remains lands here. The `beneath_sunden` unmapped-deep QUESTION is deliberately
excluded by design per ADR-106.

The completed half of the epic already cleared the highest-friction playtest
defects: MP opening narration now POV-swaps the driving player's own card and
routes through `emit_event` for uniform per-recipient POV and perception fanout
(71-5, 71-13), the player-action transcript got an own-echo contrast bump and
peer-action persistence (71-4), and the WS reconnect banner now auto-clears
(71-3). The open work is the cleanup-and-correctness remainder: making those
fixes durable (regression guard 71-12, round-anchored placement 71-10), passing
an a11y bar across all themes (71-11), clearing type-checker debt (71-8, 71-9,
71-14), and finally wiring or resolving the three ADR-backed items that the
playtest re-exposed (71-15, 71-16, 71-17).

## Technical Architecture

The open stories touch five subsystems.

**Intent router (71-16, ADR-113).** The `IntentRouter` (revived `LocalDM`) runs a
Haiku pass over each submitted action and emits a `DispatchPackage`
(`sidequest-server/sidequest/protocol/dispatch.py`) consumed by `run_dispatch_bank`.
71-16 adds per-dispatch confidence scoring and threshold gating: each
`dispatch[]` entry carries `confidence (0.0–1.0)` and a subsystem engages its
engine only at or above a threshold (default 0.6, tunable in genre `rules.yaml`).
Below-threshold dispatches do not fire an engine and are logged with score +
threshold. Files: `sidequest/agents/intent_router.py`,
`sidequest/server/intent_router_pass.py`, OTEL spans in
`sidequest/telemetry/spans/intent_router.py` (`intent_router.decompose`,
`intent_router.dispatch.{subsystem}` with `engaged`, `threshold`, `confidence`).

**Room-graph movement (71-15, ADR-055).** When a world sets
`navigation_mode: room_graph`, valid room transitions must fire
`tick_on_room_transition()` (advancing active tropes once per transition) and
decrement consumable `uses_remaining` (torch burn, ration consumption). ADR-055's
implementation-status section confirms both are currently unwired
(`grep tick_on_room_transition` returns zero hits). Files touch the room-graph
movement path in `sidequest/server/` (map-emit/cartography projection) and the
trope engine.

**MP opening + peer-action transcript (71-10, 71-12).** Peer-action placement is
currently positional; 71-10 adds a `round` field to `PlayerActionPayload`
(`sidequest/protocol/messages.py`) so peer actions anchor by exact round instead.
71-12 adds a comment-guard at the peer-reveal capture site in
`sidequest-ui/src/App.tsx` ("MUST use raw reveals, never merged") to prevent a
stale-draft regression of the 71-13 `emit_event` fix. Segment model lives in
`sidequest-ui/src/lib/narrativeSegments.ts`.

**Reference renderers + type hygiene (71-8, 71-9, 71-14).** 71-8 fixes a
pre-existing pyright error in
`sidequest-server/sidequest/server/reference_presenters.py`
(`present_magic` rows reassignment). 71-9 migrates the
`dice-overlay-wiring-34-5` source-text wiring test to a behavioral assertion.
71-14 clears type-looseness in the 71-5 opening-POV test files (+13) and two
`visibility_sidecar` alias false-positives via `pyright-ignore`.

**Orrery labels + a11y (71-2 done, 71-11).** Orrery label placement lives in
`sidequest-server/sidequest/orbital/{render,label_strategy,models}.py`; 71-2
applied the ADR-094 upright-flip on far-arc tangent labels. 71-11 runs an
axe/devtools peer-action contrast sweep across each live `theme_css`, bumping the
peer token where contrast falls below 4.5:1.

**Scene-harness doctrine (71-17, ADR-092).** ADR-092 §Decision specifies a
`DEV_SCENES=1` env gate, but the §"Design evolution" addendum records that the
gate was removed in favor of Cloudflare Zero Trust tunnel-layer access control.
71-17 is a doctrine-resolution story: decide and document which gating model is
canonical (env gate vs. Cloudflare-only) — no behavioral mechanics, a decision
record.

## Cross-Epic Dependencies

**Depends on:**
- Epic 59 (Intent Router Mechanical-Engagement Spine) — provides the
  `IntentRouter` / `DispatchPackage` / `run_dispatch_bank` foundation that 71-16's
  confidence gate extends. 71-16 is downstream of the 59 dispatch-bank work.

**Excludes (by design — not dependencies, ownership boundaries):**
- This epic explicitly **excludes** findings owned by epics
  **59** (dispatch-bank consolidation, 59-11), **61**, **63** (reference-renderer),
  **64**, **65**, **66**, **67** (MP-resilience), **68** (genre-tone),
  **69** (gameboard-UX), and **70** (daemon-media). It also excludes the
  `beneath_sunden` unmapped-deep QUESTION per ADR-106.

**Depended on by:**
- None. Epic 71 is a terminal bugfix bucket; no other epic consumes its output.
