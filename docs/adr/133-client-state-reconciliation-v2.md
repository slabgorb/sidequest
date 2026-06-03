---
id: 133
title: "Client State Reconciliation v2 — Full-Replay Mirror, Streaming-Narration Accumulator, and ImageBus Scrapbook Merge"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [26, 27, 76]
tags: [frontend-protocol]
implementation-status: live
implementation-pointer: null
---

# ADR-133: Client State Reconciliation v2

> **Documents a system already live in code.** The React client's actual
> reconciliation strategy — re-deriving *all* client state by replaying the full
> message log on every change — shipped incrementally across the post-port UI
> work (state mirror, streaming-narration accumulator, ImageBus scrapbook merge)
> without a governing ADR, and it materially diverges from how ADR-026 describes
> the mirror. ADR-026 reads the mirror as an **incremental accumulator**; the
> implementation is **full-replay-on-every-message**. This record closes that
> architecture-of-record gap, states what the decision *was*, and pulls the two
> companion protocols (streaming-narration accumulation, ImageBus merge) under
> the same idempotent-replay umbrella.

## Context

The client receives a reliable-ordered WebSocket message stream and must derive
several distinct read-models from it: the game-state mirror (HP, location,
quests, knowledge, magic, persistent location descriptions), per-turn streaming
narration (delta chunks plus canonical text), and the image/scrapbook gallery.

ADR-026 framed the mirror as an **incremental accumulator**: "the server
piggybacks state deltas on narration messages so the client stays in sync without
polling," with the §Consequences note that the "server must compute and include
state deltas with *every* narration." The mental model that prose invites is an
append-only reducer that mutates a running state object as each new message lands.

That is **not what the code does.** Three pressures pushed the implementation to
a different shape:

1. **Idempotency under React re-render.** `useStateMirror` runs inside a
   `useEffect` keyed on the `messages[]` array. An accumulator that mutated a
   running object would double-apply on any spurious re-fire and would be
   impossible to reason about under React's render model. A pure function of the
   whole log is trivially correct: same input, same output, every time.

2. **Cross-message ordering dependencies the server does not guarantee at the
   payload level.** Persistent-location deltas (ADR-109
   `LOCATION_OVERLAY_CHANGED`) can arrive *before* their baseline
   (`LOCATION_DESCRIPTION`); the canonical `NARRATION` carries **no `turn_id`**
   and must be matched to whichever streaming turn is active; `JOURNAL_RESPONSE`
   canonical rows must overwrite ephemeral footnote-derived knowledge entries
   laid down earlier in the same log. Resolving these from a single linear pass
   over the complete, ordered log is far simpler than maintaining the
   buffering/matching state across many independent reducer invocations.

3. **`state_delta` is nullable, not always-present** (ADR-026's 2026-05-28
   amendment). A pure-narration turn carries `state_delta=None` and is omitted
   from the wire entirely. The replay simply skips the merge when the delta is
   absent (`useStateMirror.ts`), which is natural in a fold and awkward
   in a mutate-in-place accumulator that assumes a delta per narration.

The companion read-models grew the same way. Streaming narration accumulates
`narration.delta` chunks per `turn_id` (ADR-076 collapsed the *server* protocol
to two narration messages but said nothing about how the client accumulates the
post-collapse streaming deltas). The image gallery merges async `IMAGE` renders
with server-authored `SCRAPBOOK_ENTRY` metadata by turn. Both are derived the
same way the mirror is: a pure function of `messages[]`, recomputed wholesale.

## Decision

**All client read-models are re-derived by replaying the full message log on
every change — idempotent full-replay, never incremental accumulation.** Each
derivation is a pure function of the complete, ordered `messages[]` array; React
recomputes it when the array identity changes and replaces the prior result
wholesale.

### 1. Full-replay game-state mirror

`useStateMirror(messages)` (`sidequest-ui/src/hooks/useStateMirror.ts`) runs
in a `useEffect` over `messages[]`. On every fire it starts from
`EMPTY_GAME_STATE` and a fresh set of local accumulators
(`useStateMirror.ts`) and folds the entire log forward:

- **`SESSION_EVENT`** — captures the local `player_id` on `connected`/`ready`,
  and on `initial_state` resets the whole mirror to the snapshot
  (`:114-132`). Reconnect snapshot replaces, it does not merge.
- **`NARRATION` / `TURN_STATUS`** — `applyDelta` merges the nullable
  `state_delta` (location, quests, characters, `magic_state`) into the running
  `current` (`:304-307`, `applyDelta` at `:363`). `magic_state` mirrors by
  replacement, not merge — server registry is authoritative (`:388-390`).
- **`NARRATION` footnotes** — accumulate into knowledge entries keyed by
  narrator-supplied `fact_id` (ADR-100 Seam C); a footnote without `fact_id` is
  dropped with `console.warn` rather than fabricating an id (`:258-264`).
- **`JOURNAL_RESPONSE`** — canonical knowledge rows; when a `fact_id` was
  already laid down by an ephemeral footnote (defaulted to `'Suspected'`), the
  canonical row **overwrites in place** so the server's authoritative
  `confidence` is not lost behind the ephemeral default (`:146-176`).
- **Handout `IMAGE`** — pushed into the journal, deduped by `render_id`
  (`:99-112`).
- **`ITEM_DEPLETED` / `RESOURCE_MIN_REACHED`** — accumulate into depletion and
  resource-alert slices (`:179-196`).
- **`LOCATION_DESCRIPTION` / `LOCATION_OVERLAY_CHANGED`** — ADR-109 persistent
  location; full-replace baseline plus overlay-only delta with delta-before-
  baseline buffering (see Invariants) (`:204-242`).
- **MP filtering** — when a local `player_id` is known, `state_delta` from
  *other* players' narrations is skipped (their character state arrives via
  `PARTY_STATUS`, not `state_delta`) (`:300-302`).

The mirror only calls `setState` when `messages.length` actually changed
(`:343-347`), so re-renders that do not extend the log are no-ops.

### 2. Streaming-narration accumulator (rebuilt idempotently on replay)

`reduceStreamingNarration` (`sidequest-ui/src/providers/streamingNarration.ts`)
is a pure reducer over a `Map<turn_id, TurnStreamState>` plus an `activeTurnId`.
`useStateMirror` rebuilds the streaming state **from scratch on every replay**
(`useStateMirror.ts, 95, 290-296`) — the same full-replace contract as the
game-state mirror — and pushes it via `setStreamingNarration`, which replaces the
whole slice (`GameStateProvider.tsx, 197-200`).

- A `narration.delta` action appends its `chunk` to the turn keyed by its
  explicit `turn_id` and marks that turn active (`streamingNarration.ts`).
- The canonical `NARRATION` carries **no `turn_id`**; the reducer attaches its
  text to `state.activeTurnId` and then **closes the turn** by clearing
  `activeTurnId` and the stall timer (`:98-122`). `useStateMirror` only routes a
  canonical `NARRATION` through the reducer when a streaming turn is active
  (`useStateMirror.ts`).
- Display rule: `canonical ?? chunks.join("")` (`streamingNarration.ts`).

### 3. HMR-survival persistence split

`GameStateProvider` (`sidequest-ui/src/providers/GameStateProvider.tsx`) persists
across two storage tiers with different lifetimes:

- **`sessionStorage`** holds the full game-state mirror under `sq_game_state`
  (`:150-169, 207-210`). It is hydrated first on mount (`:172-180`) so a Vite HMR
  reload mid-session restores the derived mirror without a server round-trip.
- **`localStorage`** holds only the journal under `sq_journal` (`:126-148,
  213-217`) so handout entries survive a full page reload, not just HMR.

Both readers swallow corrupt/quota errors silently *for the persistence cache
only* — this is an opportunistic cache layer, not a load-bearing data path; the
authoritative source is always the replayed message log.

### 4. ImageBus two-pass merge

`ImageBusProvider` (`sidequest-ui/src/providers/ImageBusProvider.tsx`) derives
the gallery via a `useMemo` over `messages[]` — pure-derive, same family:

- **Pass 1** collects `SCRAPBOOK_ENTRY` payloads into a
  `Map<turn_id, ScrapbookEntry>` (`:215-220`).
- **Pass 2** walks `IMAGE` messages, dedupes by `render_id`, and merges the
  matching scrapbook entry's metadata over the image's payload fallbacks (the
  scrapbook entry wins when present) (`:226-286`).
- Scrapbook entries with **no matching image** still emit a metadata-only card
  with an empty URL (`:293-318`) — the entire point of story 33-18.
- Results sort by `timestamp` then `reverse()` for **newest-first** ordering
  (`:323-324`).

## Invariants / Contracts

- **Idempotent full-replay.** Every read-model is a pure function of the entire
  ordered `messages[]`; replaying the same log yields the same result. There is
  no mutate-in-place accumulator and no message is consumed/destroyed on apply.
- **Delta-before-baseline buffer (ADR-109).** A `LOCATION_OVERLAY_CHANGED` that
  arrives before its `LOCATION_DESCRIPTION` baseline is buffered in
  `pendingOverlays` and merged into the next baseline whose `region_id` matches
  (`useStateMirror.ts`). A buffered or live delta whose `region_id` no
  longer matches the current baseline is **dropped** — a room change is the truth
  source.
- **Canonical NARRATION carries no `turn_id`; match via `activeTurnId`.** The
  streaming reducer routes canonical text to the most-recently-active streaming
  turn and closes it (`streamingNarration.ts`). A canonical `NARRATION`
  with no active turn is a non-streaming narration and does not touch the
  streaming slice.
- **Late-delta discard.** Once a turn's `canonical` is set, any further
  `narration.delta` for that `turn_id` is silently discarded
  (`streamingNarration.ts`).
- **`kind` vs `type` divergence (intentional).** `narration.delta` is **not a
  `GameMessage` variant** — it is discriminated by `kind: "narration.delta"`, not
  by `type`. It falls through `handleMessage`'s `type`-based guards and lands in
  `messages[]` unmodified; `isNarrationDelta` checks the `kind` field explicitly
  (`payloads.ts, 656-664`; consumed at `useStateMirror.ts`). This
  divergence is deliberate: the streaming delta is a sub-message protocol layered
  beneath the canonical `GameMessage` envelope, not a peer of it.
- **Malformed-drop, not silent-fallback.** A `SCRAPBOOK_ENTRY` missing required
  fields (`turn_id`, `location`, `narrative_excerpt`) is **hard-dropped** with a
  `console.error` (`ImageBusProvider.tsx`), and a `narration.delta`
  without `turn_id` is dropped with `console.error` (`useStateMirror.ts`).
  Per the No Silent Fallbacks rule these are schema-drift bugs surfaced loudly,
  not papered over with synthesized defaults.
- **Dedup keys.** Knowledge by `fact_id`, handout journal entries and gallery
  images by `render_id`, scrapbook by `turn_id`.
- **`state_delta` is nullable** (ADR-026 amendment 2026-05-28). The replay skips
  the merge when the delta is absent or empty (`useStateMirror.ts`).

## Consequences

**Positive**

- **Correctness by construction.** A pure fold over the full log cannot
  double-apply, cannot drift from spurious re-renders, and trivially reproduces
  any prior state by replaying a prefix. Cross-message dependencies
  (delta-before-baseline, canonical-no-turn_id, footnote-then-canonical
  knowledge overwrite) resolve in one linear pass instead of as stateful
  bookkeeping smeared across reducer invocations.
- **HMR and reconnect are cheap.** sessionStorage hydration plus full-replay
  means a dev reload or a reconnect snapshot rebuilds every read-model with no
  bespoke recovery logic.
- **One mental model across three read-models.** Mirror, streaming narration,
  and ImageBus are all "pure function of `messages[]`," so a maintainer learns
  the pattern once.

**Negative / cost**

- **Replay is O(N) in log length on every message.** Each new message re-folds
  the entire history. For the playgroup's session lengths (the `coyote_star`
  session ran 140+ turns) this is well within budget — the work is in-memory map
  building over a few hundred messages — but it is not free, and a multi-thousand-
  turn session would eventually want windowing or a memoized prefix-fold. The
  `messages.length` guard (`useStateMirror.ts`) and the ImageBus `useMemo`
  keep React from recomputing when the log has not actually grown, which caps the
  practical cost to once per inbound message.
- **The whole-log array is the source of truth.** Anything not derivable from the
  message stream (the persistence caches) is strictly secondary; a contributor
  must not start treating sessionStorage as authoritative.

## Alternatives considered

- **Incremental accumulation (the ADR-026 mental model).** Mutate a running
  state object per inbound delta. Rejected in practice: fragile under React
  re-render (double-apply), and the cross-message ordering dependencies
  (delta-before-baseline, canonical-no-`turn_id`, footnote-vs-canonical
  knowledge) force per-message buffering state that is harder to reason about
  than a single linear fold. The replay approach trades CPU for correctness and
  simplicity — the right trade at playgroup scale.
- **Server-pushed fully-materialized view per turn.** Have the server send the
  entire client read-model each turn so the client never derives anything.
  Rejected: heavier wire payloads, duplicates state the server already encodes as
  deltas, and undoes ADR-027's reactive-delta design.
- **Persisting the derived mirror as the source of truth.** Treat
  sessionStorage/localStorage as authoritative and patch it incrementally.
  Rejected: reintroduces the drift problem the full-replay design exists to
  avoid; the caches stay opportunistic.

## Reconciliation with ADR-026 / ADR-027 / ADR-076

- **ADR-026 (Client-Side State Mirror) — divergence, called out prominently.**
  ADR-026's §Decision and §Consequences read the mirror as an **incremental
  accumulator** ("the server piggybacks state deltas… include state deltas with
  *every* narration"). The shipped implementation is **full-replay-on-every-
  message**: `useStateMirror` re-derives the entire mirror from
  `EMPTY_GAME_STATE` by folding all of `messages[]` on each change, never
  mutating a running object. ADR-026's *server contract* still holds (deltas ride
  on `NARRATION`/`TURN_STATUS`; reconnect resends `initial_state`), and its
  2026-05-28 amendment (nullable `state_delta`) is exactly what makes the fold's
  skip-when-absent branch correct. **What this ADR supersedes-in-spirit is only
  the client-side accumulation model**, not the server delta contract. ADR-026 is
  not marked superseded — its server-responsibility prose remains accurate — but
  readers should treat *this* ADR as the authority on how the client derives the
  mirror.
- **ADR-027 (Reactive State Messaging) — unchanged, complementary.** ADR-027
  governs the *server push* of reactive deltas; this ADR governs how the client
  *consumes* the resulting stream. No conflict: full-replay is a consumer-side
  strategy over the same reactive messages ADR-027 emits.
- **ADR-076 (Narration Protocol Collapse Post-TTS) — server-side only; does not
  cover client accumulation.** ADR-076 collapsed the *server* narration protocol
  to two messages (`Narration` + `NarrationEnd`) after TTS removal. It is silent
  on the client `NarrationDelta`/`activeTurnId` streaming accumulation documented
  here — the `narration.delta` sub-message and the per-turn streaming reducer are
  a client-side layer that grew after the collapse. This ADR documents that layer
  without altering ADR-076's server-protocol decision.
