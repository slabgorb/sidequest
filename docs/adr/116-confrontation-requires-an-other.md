---
id: 116
title: "A Confrontation Requires an Other — Participant Membership Invariant, Single Opponent-Seater, End-on-No-Other"
status: accepted
date: 2026-05-26
deciders: ["Keith Avery", "Leonard of Quirm (Architect)"]
supersedes: []
superseded-by: null
related: [24, 31, 33, 77, 113, 114]
tags: [game-systems]
implementation-status: partial
implementation-pointer: sprint/context/context-story-59-13.md
---

# ADR-116: A Confrontation Requires an Other

> **Amends, does not supersede.** This completes the participant model implied by
> ADR-033 (Genre Mechanics Engine — Confrontations) and the dual-track design
> (`docs/superpowers/specs/2026-04-25-dual-track-momentum-design.md`), and it
> overturns one local decision made in **Story 45-33**: the exemption that let
> `category="movement"` (and `social`) confrontations instantiate with no
> opponent seated. See §3.

## Context

### The bug that surfaced it

Story 59-13 was filed as "chase confrontation write-back is broken — dual-dial
frozen 0/7, opponent seat empty, Setup→active never fires." Measurement
(two probes, `tests/server/test_chase_writeback_probe.py`) proved the stated
root cause **false**:

- **Beat write-back works.** With an opponent seated, a chase beat advances the
  opponent dial (0→2) and the phase transitions Setup→Opening. The
  `_apply_narration_result_to_snapshot` → `apply_beat` path is sound for chase,
  identically to combat.
- **The real defect is upstream, in *who gets seated*.** `instantiate_encounter_from_trigger`
  for a chase with no narrator-named NPCs seats **only the player**. With no
  opponent-side actor, every opponent beat is skipped (`apply_beat` returns
  `skipped_reason="neutral_actor"`/no target), so the opponent dial never moves
  and the encounter never leaves Setup.

### The larger problem the bug exposed

The engine has **no enforced concept of confrontation membership** — no
authoritative, type-aware answer to *"who is on the other side of this
confrontation?"* Instead, "who is fighting" is recomputed each turn from a
heuristic: whoever the narrator happened to name this turn, else whoever was
`last_seen_location` in the same room. Worse, the side they get is inferred from
the confrontation's category (`_npc_fallback_at_location`: `opponent` if combat
else `neutral`) — which directly violates the `EncounterActor.side` contract
("*set at instantiation from the narrator's payload; engine never infers it*").

### What already exists (reuse-first audit)

The membership *primitives* are already present — only the entry discipline and
one invariant are missing:

| Concept | Where it lives | Status |
|---|---|---|
| Participant roster | `StructuredEncounter.actors: list[EncounterActor]` | present |
| Membership / alignment | `EncounterActor.side` ∈ {player, opponent, neutral} | present |
| Exit flag | `EncounterActor.withdrawn` (skipped by `apply_beat`) | present |
| Player-exit → resolve | `server/dispatch/yield_action.py` (`all(a.withdrawn …)` for player side) | present |
| Live-opponent count | `confrontation_lifecycle_detector.opponent_alive_count` | present |
| **Opponent entry discipline** | — | **missing** |
| **"Needs an Other" instantiation invariant** | combat-only guard (`NoOpponentAvailableError`) | **incomplete** |
| **Opponent-exit → resolve ("no Other remains")** | — | **missing** |

## Decision

A structured confrontation is, by the dual-dial construction (`player_metric` +
`opponent_metric`), a contest between **two sides**. We make that explicit and
enforce it.

### 1. The invariant: a confrontation requires an Other

A structured confrontation MUST have at least one live (`side="opponent"`,
not `withdrawn`) actor. If no opponent entity can be sourced, it is **not a
confrontation — it is narration.** A "race against time" (chase vs. a clock, a
tide, a blockade) is rendered as prose; an abstraction never gets a seat or a
dial. *Entities get seated and get the opponent dial; abstractions get narrated.*

"Solo" means **one player character**, never "no opponent." The 45-33 reasoning
that a solo chase is "a legitimate one-on-one scene the narrator can populate
later" conflated those two; nothing ever populated the later beat, so the dial
froze forever.

### 2. Single opponent-seater, room-sourced (Fork A: room-only for now)

All opponent entry funnels through **one** seating chokepoint. Sourcing order
when the router/narrator names no opponent:

1. Router-named `npcs_present` (existing).
2. **Room scan** of `snapshot.npcs` at the acting PC's location — NPCs *and*
   bestiary mobs (the same roster, distinguished by `bestiary_id`), seated as
   `side="opponent"` for an adversarial confrontation (not `neutral`).
3. If still none → raise `NoOpponentAvailableError`. The dispatch handler
   (`run_confrontation_dispatch`) already catches this and lets the narrator
   render prose.

Bestiary / encounter-table pull (a *new* pursuer arriving) is **explicitly
deferred** — room-only for this round.

This resolves the `EncounterActor.side` contract violation: the engine *does*
legitimately own opponent-seating for adversarial confrontations. Update that
docstring to say so, and have the seater emit `participant.joined{source, side}`
so the GM panel can answer "why is this raider in my chase?" (OTEL Observability
Principle).

### 3. Generalize the empty-opponent guard — staged rollout

The `NoOpponentAvailableError` guard, today gated on `category == "combat"`,
generalizes to all **adversarial** confrontations. To avoid regressing the
social-first packs (`victoria`, `tea_and_murder`) without playtest validation,
roll out in stages:

- **Now (59-13):** enforce for `movement` (chase). Combat already enforces.
- **Follow-up:** extend to `social` / `pre_combat` after validating against the
  social packs — a negotiation/trial also needs a counterparty, but the failure
  mode must be confirmed against real social-pack flows first.

### 4. End-on-no-Other (Wild Card #9, accepted)

A confrontation resolves when its last live opponent leaves — the **mirror** of
the existing player-side rule in `yield_action.py`. When an opponent becomes
`withdrawn` (yield, defeat, flee, talked-down) and
`opponent_alive_count` drops to 0, resolve the encounter
(`resolved=True`, `outcome` reflecting the disposition) and emit
`participant.left{reason}`. A confrontation ends because there is no longer an
Other — not only because a dial hit threshold.

## Consequences

**Positive**
- One seating chokepoint replaces three disagreeing paths — the actual root cause.
- The "needs an Other" invariant is one architectural truth that covers combat,
  movement, and (staged) social/pre_combat — patching only chase would leave the
  same bomb under the other categories.
- Membership becomes legible on the GM panel via `participant.joined/left` spans.
- Symmetric lifecycle (player-exit and opponent-exit both resolve) — tidy.

**Negative / risks**
- Generalizing the guard could regress social packs if rolled out unstaged —
  hence §3's staging. Watch `victoria` / `tea_and_murder`.
- End-on-no-Other changes resolution semantics: an encounter can now end without
  a dial reaching threshold. Existing resolution consumers must tolerate this
  (they already do for player-side yield).

**Design-for, don't-build (out of scope, keep the seam open)**
- **Mid-scene recruitment** (guards arrive, allies join) — the reason entry
  should be event-shaped, not an instantiation snapshot. Don't build now; don't
  foreclose.
- **Bestiary / encounter-table opponent sourcing** — Fork A deferred.

## Alternatives considered

- **Patch chase only** (fourth special case in `_npc_fallback_at_location`):
  rejected — buries the same bomb under every other confrontation type and adds
  a third disagreeing seating path.
- **New first-class `Participant`/membership type**: rejected (reuse-first) —
  `actors`/`side`/`withdrawn` already model the set; the gap is discipline, not
  data.
- **Let one-sided confrontations stand and have the narrator populate later**
  (the 45-33 position): rejected — nothing populates the later beat; the dial
  freezes. This ADR overturns it.

## Testing guidance (for TEA)

Per this repo's "No Source-Text Wiring Tests" rule, prove wiring via OTEL spans
and fixture-driven behavior, never by grepping source:

- Fixture-drive `instantiate_encounter_from_trigger(encounter_type="chase",
  npcs_present=[])` with a room-present NPC/mob → assert an `opponent`-side actor
  is seated (not neutral); with an empty room → assert `NoOpponentAvailableError`.
- End-to-end: chase instantiated via the production path → advance → assert
  opponent dial moves off 0 and phase transitions (the AC1 the story already
  wanted, now hung on the corrected seam).
- End-on-no-Other: withdraw the last opponent → assert `resolved=True` and a
  `participant.left` span.

## Amendment 2026-05-28 — Implementation reconciliation (live-vs-deferred split)

Audited the four Decision sections against code. More is live than the
`partial` status implies — the only deferred items are the §3 social/pre_combat
staging extension and §2's bestiary/encounter-table sourcing (both explicitly
staged/deferred by the ADR itself, not gaps).

**Live:**
- **§1 invariant + §2 single opponent-seater.** `NoOpponentAvailableError` is
  defined at `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py:38`
  and raised at `:591` when an adversarial encounter would instantiate with no
  opponent after the room-scan fallback. The dispatch handler catches it and
  renders prose — `sidequest-server/sidequest/agents/subsystems/confrontation.py:40,134`
  (imports it; `except NoOpponentAvailableError` at `:134`) around the single
  `instantiate_encounter_from_trigger` chokepoint (`confrontation.py:125`). The
  room-sourced fallback seats opponents as `side="opponent"` for adversarial
  confrontations (`encounter_lifecycle.py:431`, `default_side = "opponent" if
  adversarial else "neutral"`), resolving the `EncounterActor.side` contract
  concern from §Context.
- **§2 OTEL membership spans.** `participant.joined` fires from the seater
  (`encounter_lifecycle.py:686-692`, span at `telemetry/spans/encounter.py:82`,
  `SPAN_PARTICIPANT_JOINED`).
- **§4 End-on-no-Other.** Implemented and **wired into the production narration
  path**: `_resolve_if_no_opponent_remains` at
  `sidequest-server/sidequest/server/narration_apply.py:3155`, called from
  `_apply_narration_result_to_snapshot` at `narration_apply.py:3150`. It sets
  `resolved=True`, `outcome="opponent_withdrew"`, phase→Resolution, and emits a
  `participant.left` span per departed opponent (`narration_apply.py:3174`;
  span at `telemetry/spans/encounter.py`). So §4 is live, not staged.

**Deferred (per the ADR's own staging):**
- **§3 guard generalization is partial by design.** The empty-opponent guard
  fires only on `combat` + `movement`:
  `_ADVERSARIAL_CATEGORIES = frozenset({"combat", "movement"})` at
  `encounter_lifecycle.py:330`, gated through `_is_adversarial` (`:344`). The
  `social` / `pre_combat` extension the ADR flagged for "Follow-up" is **not yet
  enforced** — confirmed by the inline note at `encounter_lifecycle.py:577`
  ("`social` / `pre_combat` remain exempt for now (staged rollout)").
- **§2 bestiary / encounter-table opponent sourcing** — Fork A; explicitly
  deferred in the ADR, room-scan only. No new pursuer-arrival sourcing in code.

Net: §1, §2 (room-only seating + spans), and §4 are live; §3's social/pre_combat
stage and §2's bestiary pull remain deferred exactly as the ADR scoped them. The
`partial` status is accurate, but the deferred surface is narrower than a reader
might assume.

## Amendment (2026-05-31): Confrontation Lifecycle Lie-Detector

The §Context reuse-first audit cited
`confrontation_lifecycle_detector.opponent_alive_count` as a *present data point*
— one of the membership primitives the ADR leaned on (the live-opponent count
that §4 End-on-no-Other compares against 0). That citation only named the field.
This amendment **governs the detector itself as a design surface**: the kill-keyword
corpus, the `narrator_kill_unbacked` classification logic, the multi-opponent
disambiguation, and the per-turn wiring. It is the confrontation-specific complement
to the dispatch-engagement watcher (`sidequest/agents/dispatch_engagement_watcher.py`)
— together they form the GM-panel lie detector that the CLAUDE.md OTEL Observability
Principle demands, and they are an instance of the semantic-telemetry pattern of
**ADR-031** (Game Watcher — Semantic Telemetry for AI Agent Observability).

### Why it exists

The module
(`sidequest-server/sidequest/server/confrontation_lifecycle_detector.py`) traces its
origin to a concrete playtest bug, recorded in its docstring
(`confrontation_lifecycle_detector.py:3-11`): a **2026-05-12 sq-playtest** Chalk Moth
fight where the narrator declared the moth dead, the confrontation panel never cleared,
and the *next* turn the narrator un-killed the moth. The root cause is broader (the
narrator hallucinates kills not backed by metric saturation; rolls fail so the engine
never resolves the encounter mechanically), and fixing the prompt is explicitly out of
this module's scope. What the module does is make the **disconnect visible** in the GM
panel: it classifies each post-narration confrontation state and emits a watcher event
carrying the disagreement surface, so the panel can flag the lie even when the prose is
convincing. This is the OTEL principle applied to a confrontation: prose alone proves
nothing; the span is the lie detector.

### What it observes — post-narration, not a gate

The detector is a pure **observer**, not a guardrail — it never blocks or rewrites
narration, it only records the mismatch. `build_lifecycle_snapshot`
(`confrontation_lifecycle_detector.py:119`) is called *after* narration apply with the
post-apply `encounter`, and produces a frozen, JSON-safe
`ConfrontationLifecycleSnapshot` (`:45`) whose attributes feed a watcher payload 1:1 via
`to_watcher_attrs` (`:84`). The snapshot pairs the narrator's prose claim against the
engine's mechanical truth: `narration_claims_kill` /
`narration_kill_keywords` on the prose side, and
`encounter_active_post_apply`, `encounter_resolved_this_turn`, both dial readings
(`player_metric_*`, `opponent_metric_*`), and `opponent_alive_count` on the engine side.

### The kill-keyword corpus

The prose-side signal is a small, deliberately **high-confidence** corpus of English
kill/death lemmas, `_KILL_PATTERNS` (`confrontation_lifecycle_detector.py:29-42`), each a
word-boundary-anchored case-insensitive regex matched on the lemma rather than
narrator-specific phrasing: `kill(ed|s)`, `slain`, `dead`, `dies`, `lifeless`,
`corpse[ds]`, plus three phrase patterns drawn verbatim from the 2026-05-12 narration —
`go(es) slack` (the physiological-collapse phrasing the narrator used for the Chalk Moth
kill, `:36-38`), `fell still` (the "Silence." continuation, `:39-40`), and
`breath(s|ed) their/its/his/her last` (`:41`). `detect_kill_keywords`
(`:102`) returns at most one matched literal per pattern, lowercased;
`narration_claims_kill` is simply "the list is non-empty" (`:135`). The corpus is
intentionally conservative — word boundaries defend common false-positives like "the
dead end of the tunnel," and the comment at `:23-28` is explicit that further calibration
should land via playtest data, **not** by widening the matcher speculatively (No
Stubbing / fail-loud discipline: keep it small and honest rather than fuzzy).

### The `narrator_kill_unbacked` classification and the multi-opponent disambiguation

The lie-detector core is the `narrator_kill_unbacked` property
(`confrontation_lifecycle_detector.py:68-82`). It returns true only when **all three**
hold:

1. `narration_claims_kill` — the prose used a corpus keyword;
2. `encounter_active_post_apply` — the engine still considers the encounter unresolved
   (`not encounter.resolved`, set at `:147`); and
3. `opponent_alive_count > 0` — at least one opponent-side actor is still in the fight.

That third clause is the **multi-opponent disambiguation** and it is the load-bearing
refinement over a naive "kill word + still active = lie" check. In a genuine
multi-opponent fight, the narrator can legitimately kill *one* opponent while the
confrontation correctly stays active because *others* remain — that is not a lie, and
firing on it would train the GM to ignore the signal. `opponent_alive_count`
(`:159-163`) counts opponent-side `EncounterActor`s whose `withdrawn` flag is not set
(the same flag `apply_beat` honors when skipping withdrawn actors), so the detector only
flags a kill claim when the encounter is active *and there is still an Other the
narrator did not kill*. This is the precise mirror of §4's End-on-no-Other: §4 resolves
when `opponent_alive_count` drops to 0; the lie-detector fires when a kill is claimed yet
that count is still positive. Post-fix, the dashboard expectation
(`:71-76`) is that `narrator_kill_unbacked` reads 0 except in these legitimate
multi-opponent cases — a high-signal regression indicator for the underlying
prose-outruns-the-engine bug.

### Per-turn wiring

The detector is wired into the production narration path, fired **once per CONFRONTATION
emit**, parallel to the existing `confrontation_peer_projection_broadcast` watcher event.
In `websocket_session_handler.py`, after the peer-projection broadcast, the handler
imports `build_lifecycle_snapshot` (`websocket_session_handler.py:1735-1737`), builds the
snapshot from `narration_text`, the pre-apply live flag, the post-apply
`snapshot.encounter`, and `encounter_resolved_this_turn`
(`:1739-1744`), then publishes it through `_watcher_publish("confrontation_lifecycle",
{... **lifecycle_snapshot.to_watcher_attrs()}, component="confrontation")`
(`:1745-1753`). Because `to_watcher_attrs` emits `narrator_kill_unbacked` alongside the
raw narration/engine fields (`:98`), the GM panel receives both the verdict and every
input that produced it on the same per-turn event — it can show *why* a turn was flagged,
not just that it was. The module docstring's wiring note
(`confrontation_lifecycle_detector.py:13-15`) matches this call site.

### Scope and audience note

This is a **Keith/dev observability** surface — a watcher event consumed by the GM panel
to verify the confrontation engine is honest, per CLAUDE.md. It is *not* a player-facing
mechanical-legibility feature and is not framed as one. It changes no resolution
semantics (it is a read-only observer), adds no gate, and leaves the underlying
narrator-hallucination fix to the prompt/engine work it merely makes visible.
