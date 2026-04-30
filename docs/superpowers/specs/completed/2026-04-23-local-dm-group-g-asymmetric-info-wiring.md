# Local DM — Group G: Asymmetric-Info Wiring — Design

**Date:** 2026-04-23
**Status:** Draft for PM review / story decomposition
**Author:** Architect
**Follows:** `2026-04-23-local-dm-decomposer-design.md` §10 (story-group G, LOAD-BEARING for MP release)
**Composes with:** `2026-04-23-projection-filter-rules-design.md` (landed same day)
**Relates to:** ADR-028 (Perception Rewriter), ADR-029 (Guest NPC Players), ADR-037 (Shared World / Per-Player State), `2026-04-22-multiplayer-session-model-design.md`

---

## Executive Summary

The Local DM decomposer (Group B, merged as PR #29) emits per-event `VisibilityTag`
values that are currently ignored end-to-end — production filters run `ComposedFilter`
with a core-invariants-plus-empty-rules configuration, and no `PerceptionRewriter` exists
in the Python port at all. Group G closes that gap. Its load-bearing shape: **the
decomposer becomes the authoritative upstream of visibility data; the projection stage
landed 2026-04-23 becomes the authoritative downstream consumer.** Nothing new invents
asymmetry; the two new things are (a) a `VisibilityTagFilter` genre-stage rule that
reads tags riding on canonical payloads and (b) a structural-hiding rule in the narrator
prompt builder that refuses to see anything the decomposer flagged
`redact_from_narrator_canonical`.

This document also reconciles a misleading citation: spec §11 names "existing
location-scoped lore-visibility code" as precedent. **That code does not exist.**
`lore_store.py` has category tags, not location scoping; ADR-037's `resolve_region()` is
Rust-only and not ported. The *actual* precedent is the projection engine that shipped
yesterday (`sidequest-server/sidequest/game/projection/`), whose `visible_to(viewer,
target)` predicate and `GameStateView` Protocol are the shape Group G plugs into.

**Biggest structural decision:** Group G does **not** add a parallel visibility system.
`VisibilityTag` rides on the canonical `payload_json` as a reserved `_visibility`
section; `VisibilityTagFilter` is a single new genre-stage rule kind that reads it. No
new Protocol. No new cache table. No new OTEL span shape beyond adding a `rule.source`
tag of `visibility_tag:<source>`.

**Biggest open question:** whether the `PerceptionRewriter` (ADR-028 re-voicing — charm,
blind, deafen, POV inversion for ADR-029 guest NPC players) should compose *before* or
*after* `ProjectionFilter` in the per-recipient pipeline, and whether it is implemented
as a new Python subsystem at all (vs. narrator-host-side per-recipient Opus re-prompts).
See §11.

---

## 1. Precedent Reconciliation (RESOLVE FIRST)

Spec §11 (resolved item 2) cites "existing location-scoped lore-visibility code" as
the template Group G reuses. A careful audit finds no such code in the Python tree.
The actual landscape:

### 1.1 What was searched

| Candidate | Evidence | Verdict |
|---|---|---|
| `sidequest-server/sidequest/game/lore_store.py` | 396 lines. Index keys: `LoreCategory` (History, Geography, Faction, Character, Item, Event, Language) and `LoreSource` (GenrePack, CharacterCreation, GameEvent). Query APIs: `query_by_category`, `query_by_keyword`, `query_by_similarity`. | **No location scoping.** Category is a topic tag, not a scope. The closest hint is `LoreCategory.Geography`, which is a *subject* axis ("this fragment is about geography"), not a *scope* axis ("this fragment is only visible in region X"). |
| `sidequest-server/sidequest/game/lore_seeding.py` / `lore_embedding.py` | 132 + 416 lines. Seeding populates `LoreStore`; embedding worker computes vectors. | Same verdict — no location scoping. The word "visible" appears once in a comment about RAG retrieval, unrelated. |
| ADR-037 `resolve_region()` | `docs/adr/037-shared-world-per-player-state.md` describes region co-location via fuzzy name matching. | **Rust-only.** `grep -rn "resolve_region" sidequest-server/` returns zero hits in Python code. The Python port has not replicated this function; `SessionGameStateView.zone_of()` hardcodes `return None`. |
| `sidequest-server/sidequest/game/projection/` (landed 2026-04-23) | `predicates.py` has `visible_to(viewer, target)` calling `GameStateView.visible_to()`. `view.py` has `SessionGameStateView` returning `False` conservatively until zones are tracked. `composed.py` composes `CoreInvariantStage` + `GenreRuleStage`. | **This is the real precedent.** Not "location-scoped lore-visibility" but "event-kind-scoped per-recipient projection." The naming drift is the spec author's; the code is what it is. |

### 1.2 Finding

The citation in decomposer-spec §11 was a best-guess pointer to architecture the author
expected to find but did not verify. The *conceptual* ancestor is the Rust
`resolve_region()` pattern described in ADR-037; the *actual* Python precedent that
Group G must reuse is the **projection engine landed 2026-04-23**, whose shape is:

```
ComposedFilter
├── CoreInvariantStage   (GM / targeted / self-echo / gm-only — short-circuits)
├── GenreRuleStage       (reads projection.yaml; three rule kinds today:
│                          target_only / include_if / redact_fields)
└── default pass-through (documented, not silent)
```

The `GameStateView.visible_to(viewer_character_id, target_character_id) → bool` Protocol
method is already the per-character-visibility API the rest of the system consumes. The
`visible_to` predicate is already registered and unit-tested. Group G's job is not to
build visibility — it is to feed the existing predicate with real data, and to add one
new rule kind that reads visibility tags riding on the event payload itself.

### 1.3 Diagram: where Group G slots in

```mermaid
flowchart TB
  subgraph upstream[Upstream — Group B (shipped 2026-04-23)]
    DM[Local DM / decomposer]
    DM --> DP[DispatchPackage with VisibilityTag per dispatch/directive/verdict]
  end

  subgraph narr[Narrator stage — Group G adds structural hiding]
    DP --> PB[Prompt Builder]
    PB -- filters out<br/>redact_from_narrator_canonical:true --> NARR[Opus narrator]
    NARR --> CANON[Canonical narration]
  end

  subgraph proj[Projection stage — Group G adds VisibilityTagFilter rule kind]
    CANON -->|payload_json + _visibility sidecar| ENV[MessageEnvelope]
    ENV --> CF[ComposedFilter]
    CF --> CI[CoreInvariantStage]
    CI --> GRS[GenreRuleStage]
    GRS --> VTF[VisibilityTagFilter rule<br/>— new rule kind]
    VTF --> DEC[FilterDecision]
    DEC --> CACHE[(projection_cache)]
    DEC --> WS[Per-player WebSocket frame]
  end

  subgraph rewrite[Rewriter stage — Group G wires ADR-028 / ADR-029]
    DEC -.-> PR[PerceptionRewriter<br/>status-effects + POV inversion]
    PR -.-> WS
  end

  subgraph audit[Safety net — Group G adds]
    CANON -.-> LEAK[Canonical-leak audit<br/>OTEL span — expected zero fires]
  end

  subgraph save[Per-player save — Group G writes filtered event stream]
    DEC --> PSAVE[Peer save.db]
    CANON --> CSAVE[Canonical save.db on narrator-host]
  end
```

**What generalizes from the precedent:** The `ComposedFilter` rule-chain pattern
extends unchanged. The new `VisibilityTagFilter` is just another entry in
`GenreRuleStage`'s evaluation order.

**What changes:** `SessionGameStateView` must grow a zone-tracking field fed by
`DispatchPackage` (§4), and the narrator prompt builder grows a precondition step (§5).

---

## 2. Visibility-Baseline YAML Schema

The decomposer needs defaults to reason against. Genre pack and world YAML layer these.

### 2.1 Genre-pack level: `genre_packs/<genre>/visibility_baseline.yaml`

```yaml
# Genre-wide defaults. Decomposer reads these at session init.
tone: broadcast_heavy | balanced | secret_heavy

# Per-dispatch-subsystem defaults. What the decomposer emits when nothing in
# the turn state suggests otherwise.
default_visibility:
  npc_agency: all                     # NPC decisions are public by default
  confrontation_init: all
  stealth_roll_check: actor_only      # a stealth roll is per-character info
  lore_reveal: actor_only
  dice_roll_private: actor_only

# Per-status-effect fidelity maps. Rewriter consumes alongside decomposer tags.
status_effect_fidelity:
  blinded:
    visual_only: drop
    audio_only: keep
  deafened:
    audio_only: drop
    visual_only: keep
  invisible:  # self-invisibility affects how others perceive actor events
    actor_events_from_others: periphery_only

# What 'all' means in this genre. Protagonists-only vs. include-NPC-seats.
all_scope: protagonists | party_plus_guest_npcs
```

### 2.2 World level: `genre_packs/<genre>/worlds/<world>/visibility_overrides.yaml`

```yaml
# Per-world deltas. Optional. Only fields that override the genre baseline.
default_visibility:
  # mawdeep is a horror-cavern world; everything audio-only by default
  exploration: audio_only_muffled
```

**Schema validation.** Loader fails loudly on unknown subsystem names
(cross-checked against `KNOWN_SUBSYSTEMS` in `sidequest.agents.local_dm`) and unknown
fidelity levels (cross-checked against the `PerceptionFidelity` Literal union in
`sidequest.protocol.dispatch`). No silent fallbacks.

### 2.3 Defaults for the shipping packs (first-pass, SM-refinable)

| Pack | tone | rationale |
|---|---|---|
| `road_warrior` | broadcast_heavy | Convoys see everything; fog-of-war is a follow-car problem only. |
| `caverns_and_claudes` | balanced | Torchlight-ish. Dungeon rooms are small enough that co-presence = visibility. |
| `mutant_wasteland` | secret_heavy | Load-bearing for fog-of-war per the projection spec. |
| `pulp_noir` | secret_heavy | Whole genre is "what does the detective know that the mark doesn't." |
| `victoria` | secret_heavy | Letter-and-ledger era; secrets are the medium. |
| `space_opera` | balanced | Bridge-crew visibility; fog-of-war on the planet. |

---

## 3. `VisibilityTagFilter` — the Core Wiring

### 3.1 Payload carry

The decomposer already produces `VisibilityTag` per dispatch/directive/verdict. These
live on the `DispatchPackage`, not on the canonical narration payload. The projection
filter operates on `MessageEnvelope(kind, payload_json, origin_seq)` — event-kind
granularity, not dispatch granularity.

**Bridge rule:** when the session handler assembles the canonical `NARRATION` payload
(and any other event kind that should be asymmetric-aware), it appends a reserved
`_visibility` key to the payload JSON that aggregates the visibility tags the
decomposer produced for this turn:

```json
{
  "round_number": 42,
  "text": "...canonical prose...",
  "_visibility": {
    "visible_to": ["player:Alice"],           // union of tags on this turn's events
    "fidelity": {"player:Bob": "audio_only_muffled"},
    "redacted_canonical_segments": ["seg_id_3"]  // pre-rendered redaction spans
  }
}
```

The underscore prefix is the convention for "system-reserved non-content keys." The
reserved key is added to the `MessageType`/payload schema so `sidequest-validate`
recognizes it and rules can reference `_visibility.*` paths without the "no invented
fields" guard tripping.

### 3.2 New genre-stage rule kind: `visibility_tag`

Extend `sidequest/game/projection/rules.py` with a fourth rule variant:

```yaml
# genre_packs/<genre>/projection.yaml
rules:
  - kind: NARRATION
    visibility_tag: {}   # no args — the rule reads _visibility from payload
```

Semantics, evaluated after `CoreInvariantStage` but ahead of other genre rules (so
structural-hiding decisions can't be re-opened by later redactions):

1. Read `payload._visibility.visible_to`.
2. If `player_id` is not in that list (and `visible_to != "all"`), return
   `FilterDecision(include=False, payload_json=...)`. Short-circuits the rule chain.
3. Else if `payload._visibility.fidelity[player_id]` is set, apply the fidelity
   transform (see §6) and return `FilterDecision(include=True, payload_json=<rewritten>)`.
4. Else fall through to later rules / pass-through.

**Predicate catalog impact:** no new predicate. The rule reads the payload directly
(via `_visibility`) — it isn't gated by `visible_to(target)` the way genre redactions
are, because the decomposer is already authoritative. The existing `visible_to`
predicate continues to serve genre-authored `redact_fields` rules (fog-of-war for HP,
positions) where no decomposer tag was emitted.

### 3.3 Slot-in to `ComposedFilter`

No signature change. `GenreRuleStage` handles the new rule variant internally. The
`ComposedFilter.project()` flow is unchanged; the OTEL `rule.source` attribute gains a
value `visibility_tag:<source>` where `<source>` is one of `decomposer`, `baseline`,
`gm_override` (for GM-panel per-turn overrides).

### 3.4 Composition with the projection-filter-rules engine (landed 2026-04-23)

Rule evaluation order inside `GenreRuleStage`:

```
1. visibility_tag rule (if present for this kind) — runs first, can short-circuit with include=False.
2. target_only rules — legacy core invariant overlap.
3. include_if rules.
4. redact_fields rules — run on payload AFTER visibility_tag's fidelity rewrite.
```

The `visibility_tag` rule and `redact_fields` rules *compose cleanly*: if the
decomposer says "blind Bob to visual details" and the genre pack says "mask enemy HP
unless visible_to," both apply. The decomposer's tag fires first because it is more
authoritative (derived from world-truth; the rule is derived from genre opinion).

**Validation additions in `sidequest-validate`:**

- `visibility_tag` rule requires the kind's payload schema to declare a `_visibility`
  sub-schema. If absent, pack load fails loudly.
- At most one `visibility_tag` rule per kind per `projection.yaml`. Duplicate =
  authoring error.

---

## 4. Structural Information Hiding (Primary Defense)

This is the load-bearing hardening win from decomposer-spec §11 (resolved item 6). The
narrator physically cannot leak what it was never told.

### 4.1 Narrator prompt builder precondition

Before assembling the `<game_state>` injection block for the Opus narrator, the prompt
builder:

1. Reads the turn's `DispatchPackage`.
2. Iterates `per_player[*].dispatch[*]`, `per_player[*].narrator_instructions[*]`,
   `per_player[*].lethality[*]`, `cross_player[*].dispatch[*]`.
3. For every entry with `visibility.redact_from_narrator_canonical: true`:
   - Remove any game-state fact the dispatch would otherwise have surfaced.
   - Remove the dispatch's `narrator_directive` / `payload` entirely from the
     injection block.
4. Log at DEBUG an OTEL `prompt.redaction.structural` event per redacted entry
   (attributes: `entity_id`, `dispatch_kind`, `idempotency_key`) so the GM panel can
   see what was withheld from the narrator.

### 4.2 Routing the hidden event

A `redact_from_narrator_canonical: true` event must still reach its intended
recipient. The decomposer adds it directly to a per-player `secret_stream` on the
session handler; the session handler emits it as a separate `SECRET_NOTE` event (or
equivalent; see Plan 03) addressed to the `visible_to` list, targeted by the existing
core invariant `invariant:targeted`. **The event never enters the canonical
narration path.**

### 4.3 What the narrator sees, by example (§6.5 of decomposer spec)

Alice sneaks into the warehouse alone. Decomposer emits:

```
SubsystemDispatch(subsystem="lethal_strike", params={target:"guard_A"},
    visibility={visible_to:["player:Alice"], redact_from_narrator_canonical:true})
NarratorDirective(kind="must_not_narrate", payload="Alice_assassination_event",
    visibility={visible_to:["player:Alice"], redact_from_narrator_canonical:true})
```

The prompt builder strips both before narrator invocation. The narrator composes ONE
canonical narration of **the evening at the inn** (Bob/Cass/Dan's co-presence). The
decomposer separately emits a `SECRET_NOTE(to:"player:Alice", payload:"<kill
description>")` event which flows through the core `invariant:targeted` path — Alice
sees it, nobody else does.

The canonical narrator output contains zero bytes of the assassination. The leak is
impossible because the fact is absent from the input.

### 4.4 Unit test contract

`tests/narrator/test_prompt_builder_structural_hiding.py`:

- Feed a `DispatchPackage` with one redact-flagged directive.
- Assert the resulting prompt string does not contain the directive's payload
  or any entity reference that was marked redact.
- Assert the OTEL `prompt.redaction.structural` span fires.

This is the prompt-builder unit test the decomposer spec §10 (G.d) calls out.

---

## 5. Canonical-Leak Audit (Safety Net, OTEL-only)

Primary defense is structural hiding (§4). This layer exists to detect architecture
holes.

### 5.1 Span shape

```
Span name:  narrator.canonical_leak_audit
Attributes:
  turn_id: str
  leaks_detected: int        # expected: 0
  redact_tag_count: int      # total redact_from_narrator_canonical:true tags in turn
  leaked_entities: list[str] # empty when leaks_detected=0
  leaked_fragments: list[str] # short excerpts of offending prose
```

### 5.2 Audit algorithm

After the narrator emits canonical prose, the audit:

1. Enumerates `DispatchPackage` entries with `redact_from_narrator_canonical: true`.
2. For each, extracts entity IDs and any distinctive tokens (e.g., the NPC's name,
   the assassination verb, the item used).
3. Scans canonical prose for these tokens via **structured entity matching** (not
   regex — use the existing NPC registry name-resolution paths in
   `sidequest.game.persistence` and entity-ID lookups). This satisfies the SOUL.md
   Zork constraint: the check is token-set vs. decomposer-emitted structured output,
   not keyword string-match.
4. Emits the span with `leaks_detected = count(matches)`.

### 5.3 Expected-zero semantics

- `leaks_detected == 0` is the steady state. The GM panel shows a green badge.
- `leaks_detected > 0` is a structural-hiding bug. The GM panel shows red; a CI
  assertion on playtest scenarios requires the count to be 0 across the scenario run.
- There is **no runtime blocking**. If the narrator leaks, the already-composed
  canonical prose still ships to the filter stage, where the `visibility_tag` filter
  rule will strip it per-recipient. Two lines of defense; the audit just tells
  Sebastien-at-the-GM-panel that one of them had to work.

---

## 6. Perception Rewriter Hookup (ADR-028)

### 6.1 What ADR-028 asks for

Per-recipient re-voicing for status effects: charmed, blinded, deafened, frightened,
invisible. The ADR is proposed-status in the Python tree; no implementation exists.

### 6.2 Where it slots in

```mermaid
flowchart LR
  CANON[Canonical NARRATION] --> VTF[VisibilityTagFilter rule]
  VTF -- per-recipient<br/>fidelity metadata --> PR[PerceptionRewriter]
  PR --> DEC[FilterDecision]
  DEC --> WS[per-player WS frame]
```

**Open question — §11:** whether PerceptionRewriter runs (a) inside `ComposedFilter` as
a fourth stage, (b) as a separate pipeline step after `ComposedFilter`, or (c) as a
narrator-host-side Opus re-prompt per recipient. Keith's spec (§3.1, §3.3) implies (c)
— "N Perception Rewriter calls (ADR-028)" — but (a) or (b) are cheaper in the
short term. This doc recommends **(b): separate pipeline step after filter, before
WS send**, because:

- It keeps the filter stage pure-functional and deterministic (spec invariant #3).
- It lets PerceptionRewriter receive the already-redacted payload, avoiding work on
  content the recipient wouldn't see anyway.
- It defers the "LLM in the hot path per recipient" question to a later optimization.

### 6.3 Tag fields the rewriter consumes

- `VisibilityTag.perception_fidelity[player_id]` — the fidelity bucket
  (`full | audio_only | audio_only_muffled | visual_only | periphery_only |
  inferred_from_aftermath`).
- Character status effects (charmed / blinded / deafened / frightened / invisible)
  from `CharacterView` (existing) — orthogonal overlay on the fidelity bucket.

The rewriter's job is to turn the canonical prose + (fidelity, status-effects) into
recipient-appropriate prose. Initial implementation can be deterministic (regex-free
sentence filtering via narrator-structured output per ADR-039); LLM re-voicing is a
follow-up.

### 6.4 Single call site

One function: `rewrite_for_recipient(canonical_payload, viewer_character, fidelity)
→ payload_json`. One call site: immediately after `ComposedFilter.project()` returns
`include=True`, before the WS frame sends. Centralized for OTEL visibility
(`narrator.perception_rewrite` span per recipient).

---

## 7. Guest-NPC Inversion (ADR-029)

### 7.1 What changes

For a seat whose player controls an NPC (per ADR-029):

- The NPC's own events have `visible_to` inverted relative to protagonists:
  protagonist events become `visible_to` the NPC-seat only at the NPC's line of sight;
  NPC events flag as `secrets_for: [NPC_seat]` plus public-behavior fields for
  protagonists.
- The PerceptionRewriter runs in **NPC-POV mode** for the NPC seat — narration is
  re-voiced from the NPC's perspective (includes motives, partial truths) rather than
  the protagonist's observed-behavior view.

### 7.2 Where the flip happens

Two coordinated touch-points:

1. **Decomposer side.** When `SessionGameStateView` reports `seat_of(player_id) ==
   "npc"` (or an `npc_character_id` is set on the seat), the decomposer's
   visibility-tag emission inverts: events that would be `visible_to: [protagonists]`
   become `secrets_for: [npc_seat]` with `perception_fidelity: {npc_seat: "full"}` and
   `visible_to: [protagonists, npc_seat]` with `perception_fidelity: {<protagonist>:
   "behavior_only"}`.
2. **Rewriter side.** The `rewrite_for_recipient` call site checks
   `view.seat_of(player_id)`; if it is `npc`, it invokes the NPC-POV rewrite variant
   (new enum on the rewriter protocol, not a new protocol).

The flip is **state-driven, not config-driven**. The genre pack doesn't know whether a
guest is playing an NPC this session; the session does. `SessionGameStateView` gains a
`is_npc_seat(player_id) -> bool` accessor. ADR-029 notes NPC disposition merges guest
input with AI disposition — that mechanic is orthogonal and already ADR-020's
responsibility.

---

## 8. Per-Player Save Projection

### 8.1 Write path split

Today `~/.sidequest/saves/<pack>/<world>/<player>/save.db` holds both `events` and
`narrative_log`. The 2026-04-22 MP spec already names the split:

- **Canonical save** — lives on the narrator-host. Contains the union: every event
  as appended to `EventLog`, unfiltered. Serves the GM panel and replay.
- **Peer save** — lives on each peer's machine. Contains only the per-peer filtered
  event stream + a derived snapshot for fast boot.

### 8.2 How Group G writes each

After `ComposedFilter.project(envelope, view, player_id)` returns a `FilterDecision`
for each connected player on an event:

```
transaction begin
  EventLog.append(canonical_envelope)        # canonical_save writes (unchanged)
  for player in connected_players:
    decision = filter.project(...)
    projection_cache.write(event_seq, player_id, decision)   # existing, from Plan 03
transaction commit

# After commit (unchanged):
for player in connected_players:
  send frame(decision.payload_json) if decision.include   # peer save writes here
```

**Peer save is populated on the peer, not on the host.** The host's responsibility ends
at sending the filtered frame. The peer's WS client appends the received frame's
payload to its local `save.db.events` table under its own `last_seen_seq` cursor (per
MP spec). The host never writes a peer save; the peer never holds canonical data it
didn't see.

### 8.3 Reconnect and mid-session join

Both mechanics are already solved in the projection-filter-rules spec (§Persistence).
`projection_cache` stores the per-recipient `FilterDecision` keyed by
`(event_seq, player_id)`; on reconnect the peer's missed frames are replayed from the
cache — bit-identical to what the live recipient received.

**Mid-session join lazy-fill** carries forward unchanged. A guest NPC player joining
mid-session at round 50 gets their cache lazy-filled from round 1 through the live
filter at present state (documented limitation). If `is_npc_seat(new_player)` is true
at the time of fill, the fill uses NPC-POV visibility, not protagonist visibility —
this is correct: that peer's local history should reflect the POV they're playing.

---

## 9. Test Contract (from decomposer spec §10 G)

| Test | Assertion | Level |
|---|---|---|
| **a. Assassination redaction** | P1 kills NPC in shadows. P2-P4 WS frames contain no bytes of the kill. P2-P4 peer saves contain no event for it. GM canonical save contains the full kill event. | End-to-end |
| **b. Blind fidelity** | P1 is blinded. Narration to P1 contains no visual details — structured diff against canonical shows visual-tagged spans stripped. | End-to-end |
| **c. Guest NPC POV** | Seat N plays NPC. Seat N receives NPC-POV narration (includes motives). Seats 1-3 receive observed-behavior narration (no motives). | End-to-end |
| **d. Structural hiding** | Prompt-builder unit test. Feed a `DispatchPackage` with `redact_from_narrator_canonical: true`. Assert the rendered prompt string contains zero matches of the redacted entity tokens. | Unit |
| **e. Canonical-leak audit** | Integration test runs scenario `scenarios/asymmetric_smoke.yaml`. Assert `narrator.canonical_leak_audit.leaks_detected == 0` for every turn. | Integration + CI |
| **f. Reconnect parity** | P2 disconnects, misses 10 events including one `visible_to: [P1]`. On reconnect P2 receives exactly 9 frames (not 10). Bit-identical to live. | End-to-end |
| **g. VisibilityTagFilter wiring** | Integration test: decomposer emits `visible_to: [player:Alice]`; `ComposedFilter.project(envelope, view, "player:Bob")` returns `include=False` with `rule.source=visibility_tag:decomposer`. | Integration |

All seven required per the "every test suite needs a wiring test" principle in CLAUDE.md.
Tests (d), (e), (g) are also load-bearing for the CLAUDE.md "verify wiring, not just
existence" principle.

---

## 10. Story Decomposition (for PM sizing)

Suggested breakdown, roughly mapped to the 8 §-headings above. Flags: **[MP-SHIP]** =
blocks multiplayer release; **[POST]** = ship-after-MP polish.

| # | Story | Size | Dep on | MP-ship? | Rationale |
|---|---|---|---|---|---|
| G1 | Visibility-baseline YAML schema + loader + genre-pack defaults for 11 packs (§2) | M | — | [MP-SHIP] | Decomposer needs real defaults to emit non-trivial tags; trivial without this. |
| G2 | `VisibilityTagFilter` rule kind — schema + loader + `GenreRuleStage` evaluation + `sidequest-validate` updates (§3) | M | G1 | [MP-SHIP] | The wiring's spine. |
| G3 | Narrator prompt-builder structural hiding (§4) + prompt-redaction OTEL span + unit test (d) | S | — | [MP-SHIP] | Primary defense. Independent of G2; can land in parallel. |
| G4 | Secret-stream routing (redact_from_narrator_canonical events reach recipient via SECRET_NOTE invariant path) (§4.2) | S | G3 | [MP-SHIP] | Completes the structural-hiding pair. Without it, redacted events vanish entirely. |
| G5 | Canonical-leak audit span + CI assertion (§5) | S | G3 | [MP-SHIP] | Smoke detector. Small. |
| G6 | PerceptionRewriter skeleton (fidelity-only, deterministic — no LLM re-voicing yet) + call site between filter and WS send (§6) | M | G2 | [MP-SHIP] | Enables fidelity tests (b). LLM re-voicing deferred. |
| G7 | `SessionGameStateView` zone/visibility fields fed from decomposer state (§1.3) | M | — | [MP-SHIP] | Today's `zone_of` returns `None`; `visible_to` returns `False`. Without real state, every genre-authored `visible_to(target)` redact rule collapses to "always redact." Decomposer needs this infra too. |
| G8 | Per-player save write path — peer appends filtered frames to local save.db (§8) | M | G2 | [MP-SHIP] | Spec §10 G final bullet. Pairs with MP session model. |
| G9 | Guest-NPC inversion — `is_npc_seat` + decomposer flip + rewriter POV-mode (§7) | L | G6, G7 | [POST] | ADR-029 is Proposed; not required to ship MP. Land after MP-ship is green. |
| G10 | LLM re-voicing variant of PerceptionRewriter (replaces G6's deterministic stub) | L | G6 | [POST] | Narrator-host-side Opus re-prompts per recipient. Expensive; defer. |
| G11 | GM-panel view for visibility decisions (what was redacted, per player, per turn) | M | G2, G5 | [POST] | Sebastien-facing. Uses existing spans; no new data. |

**Parallelizable:** G1 ↔ G3 ↔ G7 are independent starting points. G2 waits on G1. G4
waits on G3. G5 waits on G3. G6 waits on G2 and G7. G8 waits on G2.

**MP-ship critical path:** G1 → G2 → G6/G8 (and G3 → G4 → G5 in parallel).

**Smallest shippable increment that satisfies "cannot release MP without G":** G1 +
G2 + G3 + G4 + G5 + G7 + G8. G6 is required for test (b) only; if blind-fidelity can
be punted to post-MP as a known limitation with an OTEL warning, G6 moves to [POST]
and MP ships on six stories.

---

## 11. Open Questions (for PM / user resolution before plan writing)

1. **PerceptionRewriter placement.** Confirmed in this doc as "separate step after
   filter, before WS send" (§6.2). Decomposer-spec §3.1 implies N Opus re-prompts per
   turn (LLM in hot path). Keith: is deterministic fidelity-only acceptable for MP
   ship (G6), with LLM re-voicing as [POST] (G10)? Affects latency budget.

2. **Zone/visibility state authorship.** `SessionGameStateView.zone_of` currently
   returns `None` always. Two paths:
   - (a) Decomposer emits zone updates as `SubsystemDispatch(subsystem="zone_update")`
     entries; session handler applies them. Everything goes through the decomposer.
   - (b) Dedicated zone tracker inside `SessionHandler` updated by existing movement
     subsystems (ADR-055 room-graph, ADR-019 cartography). Decomposer reads the
     tracker, doesn't author it.
   Recommendation: (b). Zones are physics, not narration; the decomposer should read
   physics, not invent it. But (a) is faster to ship if (b) requires unforking the
   Rust `resolve_region` port.

3. **`_visibility` payload key — where does the schema live?** Three options:
   - Common sub-schema referenced from every asymmetric-aware MessageType (clean,
     five-schema-touch change).
   - Top-level envelope field next to `kind`/`payload_json`/`origin_seq` (invasive
     but cleanest — everything in code knows where to look).
   - Stay in `payload_json` as a reserved key, validator-enforced (this doc's current
     proposal; ships with least churn).
   Recommendation: option 3 now, option 2 as a follow-up if the filter's coverage
   widens to non-EventLog messages.

4. **World-level `visibility_overrides.yaml` — v1 or YAGNI?** Plan-3 spec already
   deferred world-level rule overrides. Consistency argues "genre only for v1"; but
   a horror-world overriding a broadcast-heavy genre is the concrete use case that
   can't wait. Recommendation: ship world-level overrides in G1 as a flat delta-dict;
   defer complex rule-overrides.

5. **Canonical save location when narrator-host is a peer.** MP spec names the
   narrator-host as the canonical save holder. If the host is "whoever starts the
   session," the canonical save migrates mid-campaign if a different peer hosts next
   session. Group G inherits this from the MP spec; noting it so a migration mechanism
   doesn't land inside G by accident.

6. **Per-character_id vs per-player_id everywhere.** `VisibilityTag.visible_to` uses
   `player_id`. The projection view uses both. ADR-029 complicates this (one player
   controls one NPC character but may watch a protagonist). Recommendation: keep
   `player_id` as the WS-addressing primitive; derive `character_id` via
   `view.character_of(player_id)` inside the rewriter where POV matters.

---

## 12. Non-Goals (explicit rejections)

Re-stating decomposer-spec §10 G non-goals for continuity:

- **No parallel visibility system.** The projection engine landed 2026-04-23 is the
  substrate; Group G extends it with one new rule kind and one new prompt-builder
  precondition. No new Protocol. No new cache table.
- **No per-player narrator fan-out.** One canonical narrator call per turn + per-
  recipient filter + per-recipient rewriter (resolved §11 of decomposer spec).
- **No narrator self-policing for leaks.** Defense is structural hiding (§4); safety
  net is OTEL (§5). The narrator is never trusted to hide its own secrets.
- **No keyword or regex visibility rules** (SOUL.md Zork). All visibility decisions
  are tag-set operations over decomposer-emitted structured output. The
  canonical-leak audit's entity-matching is not regex — it is entity-ID lookup
  against the NPC registry.
- **No re-invention of the projection-filter-rules engine.** Compose, don't duplicate.
