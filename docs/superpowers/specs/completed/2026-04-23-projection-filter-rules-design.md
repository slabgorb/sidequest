# ProjectionFilter Rules — Design

**Date:** 2026-04-23
**Author:** Architect (Leonard of Quirm)
**Status:** Draft for review
**Follows:** `docs/superpowers/plans/2026-04-22-mp-03-filtered-sync-and-projections.md`
**Scope:** First real filter rules for MP-03. Replaces the PassThroughFilter-only behaviour shipped in MP-03.

## Summary

MP-03 shipped the per-player projection *pipe* (EventLog → fan-out → `ProjectionFilter` → per-player WebSocket frame) with only a `PassThroughFilter` implementation — every player sees everything. This spec defines the first real filter rules, covering two of the three SOUL.md asymmetric-info scenarios:

- **Targeting** — e.g. secret notes, private dice requests, per-recipient responses
- **Redaction** — e.g. fog-of-war HP, hidden enemy positions, GM-only fields

The third scenario (charm / illusion / false perception) is explicitly **out of scope** because it requires the filter to manufacture false payloads — a different architectural shape that needs narrator cooperation. It will land in a separate spec.

## Non-Goals

- Scenario 3: per-player narrative substitution (charm, illusion, false reality).
- World-level rule overrides (genre-level only for v1).
- All-outbound-message coverage (EventLog-origin events only for v1; filter signature is already shaped to widen later).
- Derived-snapshot store for historical state reconstruction.
- Time/TTL-based redaction; dynamic mask values; predicate conjunction/disjunction.

## Architectural Invariants (load-bearing)

1. **Single source of truth.** The canonical payload is written exactly once to `EventLog`, unmodified, regardless of player count.
2. **Projection at egress.** The filter runs only when bytes are about to leave the server for a specific client. Storage is never per-recipient.
3. **Determinism.** `project(envelope, view, player_id) → FilterDecision` is a pure function. Same inputs, same output. Live and replay must be bit-identical.
4. **GM sees canonical.** The GM panel, OTEL traces, and save files read the unfiltered truth. Only player-destined frames are projected.
5. **No invention.** A rule may mask fields or drop envelopes. It may not reference fields absent from the canonical payload. Inventing false content is scenario-3 territory and is architecturally forbidden here.

## Architecture

```
            ┌──────────────────────────────────┐
            │ Narrator / Session Handler       │
            │   (produces events)              │
            └────────────┬─────────────────────┘
                         │ append (canonical)
                         ▼
                 ┌───────────────┐
                 │   EventLog    │  ← single source of truth (SQLite)
                 └───────┬───────┘
                         │ for each recipient:
                         ▼
            ┌──────────────────────────────────┐
            │  ProjectionFilter.project(       │
            │    envelope, view, player_id)    │
            │                                  │
            │  1. Core invariants (unconfig'd) │
            │  2. Genre rules (from YAML)      │
            │  3. Default: pass-through        │
            └────────────┬─────────────────────┘
                         │ FilterDecision
                         ▼
                ┌─────────────────┐
                │ projection_cache│  ← keyed (event_seq, player_id)
                │   (sqlite)      │     same DB file as EventLog
                └────────┬────────┘
                         │
                         ▼
               per-player WebSocket frames
```

## Interface

```python
# sidequest.game.projection_filter

@dataclass(frozen=True)
class MessageEnvelope:
    """What the filter judges. Superset of EventRow so we can later widen
    coverage to direct-broadcast messages without a signature change."""
    kind: str              # MessageType wire string
    payload_json: str      # canonical JSON
    origin_seq: int | None # EventLog.seq if EventLog-origin, else None


@dataclass(frozen=True)
class FilterDecision:
    include: bool          # False ⇒ don't send this frame to this player
    payload_json: str      # may differ from envelope.payload_json if redacted


class GameStateView(Protocol):
    """Narrow, read-only projection of current session state the filter can read.
    Implemented by SessionHandler; filter never mutates."""
    def is_gm(self, player_id: str) -> bool: ...
    def seat_of(self, player_id: str) -> str | None: ...
    def character_of(self, player_id: str) -> str | None: ...
    def zone_of(self, character_id: str) -> str | None: ...
    def visible_to(self, viewer_character_id: str, target_character_id: str) -> bool: ...
    def owner_of_item(self, item_id: str) -> str | None: ...
    def party_of(self, player_id: str) -> str | None: ...


class ProjectionFilter(Protocol):
    def project(
        self,
        *,
        envelope: MessageEnvelope,
        view: GameStateView,
        player_id: str,
    ) -> FilterDecision: ...
```

Notes:
- `GameStateView` is a Protocol. Testable with a tiny fake; no real session needed.
- `MessageEnvelope` is shaped to later subsume direct-broadcast messages (question 4 variant B); coverage widens in a follow-up without rule rewrites.
- Existing `FilterDecision` and `PassThroughFilter` remain. `PassThroughFilter` becomes the documented "no rules configured" fallback rather than the only implementation.

## Authority Model

Two layers, no world layer for v1.

| Layer | Owner | Authoring surface | Purpose |
|---|---|---|---|
| Core invariants | Engine (Python code) | Core only | Structural guarantees — cannot be weakened by genre. |
| Genre rules | Genre pack | `genre_packs/<genre>/projection.yaml` | Stylistic and mechanical per-player asymmetry. |

### Core invariants (hardcoded)

Run first in the rule chain. Can short-circuit.

| Invariant | Rule |
|---|---|
| **GM sees truth** | If `view.is_gm(player_id)`, return `include=True` with canonical payload. No further rules. |
| **Targeted-by-field** | If the envelope's payload schema declares a `to` field (e.g. `SECRET_NOTE.to`, `DICE_REQUEST.to`, `JOURNAL_RESPONSE.to`, `VOICE_TEXT.to`), include only if `player_id == payload.to` (or `player_id in payload.to` for list fields). |
| **Self-authored** | If payload carries `author_player_id` and kind is in the self-echo set (`PLAYER_ACTION`, `DICE_THROW`, `BEAT_SELECTION`, `CHARACTER_CREATION`), include only for `author_player_id` + GM. |
| **GM-only kind** | `THINKING` (narrator internal monologue) is never routed to players. |
| **No invention** | Schema-level: rules can only name canonical payload fields. Enforced by `sidequest-validate`. |

The "targeted" and "self-echo" kind sets live in a single core table alongside `MessageType` and are cross-checked against payload schemas at test time.

## Predicate Catalog (v1)

The predicate catalog is the **vocabulary of per-player asymmetry**. Closed set, core-owned, each predicate typed and unit-tested.

| Predicate | Signature | Semantics |
|---|---|---|
| `is_gm` | `() → bool` | Viewer is GM. |
| `is_self` | `(field) → bool` | `payload[field] == viewer_character_id` (or viewer_player_id, depending on field type). |
| `is_owner_of` | `(field) → bool` | Viewer's character owns the item/resource referenced by `payload[field]`. |
| `in_same_zone` | `(field) → bool` | `view.zone_of(viewer_character) == view.zone_of(payload[field])`, both non-None. |
| `visible_to` | `(field) → bool` | `view.visible_to(viewer_character, payload[field])`. Umbrella for perception / line-of-sight / stealth the session already tracks. |
| `in_same_party` | `(field) → bool` | `view.party_of(viewer_player) == view.party_of(payload[field])`. |

**Adding a predicate** is a core PR (implementation + test + docs entry in `docs/projection-filter-predicates.md` + `sidequest-validate` update). Genre packs cannot introduce predicates. This is deliberate: every axis of asymmetry goes through review.

## Rule Schema (`genre_packs/<genre>/projection.yaml`)

Three rule types cover scenarios 1 and 2. More rule types can be added later without reshaping.

```yaml
rules:

  # target_only — include only for recipients listed in a field.
  - kind: DICE_RESULT
    target_only:
      field: to              # payload[to] is a player_id or list[player_id]

  # redact_fields — include for everyone; mask listed fields
  # unless predicate holds for the viewer.
  - kind: STATE_UPDATE
    redact_fields:
      - field: target.hp
        unless: visible_to(target)
        mask: "??"
      - field: target.conditions
        unless: visible_to(target)
        mask: []

  - kind: TACTICAL_STATE
    redact_fields:
      - field: enemies[*].position
        unless: in_same_zone(enemies[*])
        mask: null
      - field: enemies[*].intent
        unless: is_gm()
        mask: null

  # include_if — whole-event include gated by a predicate.
  - kind: ACTION_REVEAL
    include_if: in_same_party(revealer)
```

**Field paths** use a small JSON-path subset: dotted keys + `[*]` for wildcarded lists. No arbitrary expressions.

**Mask values** are literals. Type must match the field or be explicitly `null`. A dynamic mask is a future feature.

**GM handling.** GM is always added to the recipient set implicitly by the invariant layer. A `target_only` rule does not need to list GM; a `redact_fields` rule does not need `is_gm()` as an escape hatch because the invariant layer short-circuits first. Rules may still reference `is_gm()` when needed (e.g. `enemies[*].intent` above) — this is redundant with the invariant for GM, but self-documents the rule.

## Rule Chain (evaluation order)

```
project(envelope, view, player_id):
  1. Run CoreInvariants. If it returns a terminal decision (include or omit),
     DONE.
  2. Run GenreRules for envelope.kind in document order:
     a. If a rule carries target_only or include_if and the predicate
        evaluates to False for this player → return include=False,
        short-circuiting all remaining rules for this envelope.
     b. If a rule carries target_only or include_if and it evaluates to True,
        the envelope is kept; continue to any redact_fields in this and
        subsequent rules.
     c. If a rule carries redact_fields, apply each redaction to the working
        payload in document order (mask the field unless the rule's
        `unless` predicate holds for this viewer).
  3. Return FilterDecision(include=True, payload=working-payload-or-canonical).
```

Properties:
- **Deny-by-omission is explicit.** Kinds with no rule and no invariant fall through to pass-through. Unknown kinds never silently vanish (no-silent-fallbacks).
- **Ordering is deterministic.** Rules apply in document order. Conflicting redactions on the same field fail pack validation rather than being silently resolved.
- **Include-gates are short-circuiting in the False direction only.** A `target_only` or `include_if` that fails terminates the chain with `include=False`. A passing include-gate keeps the envelope and allows later `redact_fields` rules to mask fields for the still-included viewer.

Implementation: `ComposedFilter` owns `[CoreInvariantStage, GenreRuleStage]`. Tests can swap either stage.

## Persistence: `projection_cache`

Single new SQLite table alongside `events`, same DB file, same transaction as `EventLog.append()`.

```sql
CREATE TABLE projection_cache (
    event_seq    INTEGER NOT NULL,
    player_id    TEXT NOT NULL,
    include      INTEGER NOT NULL,   -- 0 / 1
    payload_json TEXT,                -- NULL when include=0
    PRIMARY KEY (event_seq, player_id),
    FOREIGN KEY (event_seq) REFERENCES events(seq)
);
```

**Write path (live).** `EventLog.append(env)` returns `seq`. Fan-out loops over connected players, runs `filter.project(...)`, writes the `FilterDecision` to `projection_cache`, then sends the frame. The event append and its associated cache writes occur in a single DB transaction (so the cache never outlives its event or vice versa); frame sends happen after the transaction commits. A cache row always reflects a committed decision.

**Read path (reconnect).** Player reconnects at seq `N`. Server reads `projection_cache` where `player_id = me AND event_seq > N`. Zero re-execution. Bit-identical to what the live player received.

**Mid-session join.** A player who joins mid-session has no cache rows for prior events. We **lazy-fill** on join: replay the event log through the live filter against *current* state, fill their cache rows, then fan-out from now on. This softens the single-truth guarantee for the historical portion (decisions reflect "what the filter would say given present state," not "given state at the time"). This is documented as a known limitation and an acceptable trade to avoid reintroducing the YAGNI'd derived-snapshot store.

**Migration.** `CREATE TABLE IF NOT EXISTS`. No backfill. Existing sessions keep their events; cache fills forward. GM and canonical reads unaffected.

**Storage cost.** ~1 row per (event × connected player). ~2,500 rows per 500-event playgroup session. Trivial.

## Validation (`sidequest-validate`)

Runs at pack load and as a CI step. Pack fails to load on any error (no silent fallbacks).

For every rule in `projection.yaml`:

1. **Kind exists** — member of `MessageType`.
2. **Kind is filter-reachable** — in the set of kinds that flow through `_emit_event`. Unreachable kinds **block** pack load (rules on unreachable kinds silently do nothing otherwise).
3. **Fields exist** — every `field` path resolves against the payload's pydantic schema for that kind. `[*]` must hit list fields.
4. **Predicates exist** — name is in the core catalog. Arg types match the field types.
5. **Masks are type-compatible** — `mask: "??"` on a numeric field fails. Types must match, or be explicitly `null`.
6. **No conflicting redactions** — two rules redacting the same field for the same kind without identical `unless` clauses is an error.
7. **No invented fields in predicates** — predicate args must be valid field paths on the canonical payload.

**Audit artifact:** `pf validate projection <genre>` prints a table of `(kind, field, predicate, mask)` rows — one per rule. This is what a mechanically-minded player (Sebastien) reads to understand what is hidden in the world they are playing.

## OTEL

Every filter decision is observable. This is the lie detector.

**Span:** `projection.filter.decide`
Attributes:
- `event.seq` (or null for non-EventLog envelopes)
- `event.kind`
- `player_id`
- `decision.include` (bool)
- `decision.redactions` (list of redacted field paths, empty if none)
- `rule.source` — one of: `invariant:gm_sees_all` | `invariant:targeted` | `invariant:self_echo` | `invariant:gm_only_kind` | `genre:<genre>/<kind>/<rule_index>` | `default:pass_through`
- `cache.hit` (bool) — true for reconnect replays

**Span:** `projection.cache.fill` — one per (event, player) live write. Attributes: `event.seq`, `player_id`.

**Span:** `projection.cache.lazy_fill` — one per mid-session join. Attributes: `player_id`, `events_filled`, `ms`.

**GM panel exposure.** Panel shows, per event, per player: what was sent, which rule fired, which fields got masked. The canonical truth is shown alongside the projection. If a player sees `hp: ??`, the GM panel shows `hp: 7` beside it. This is the lie-detector working.

**CI assertion.** Every event fanned out produces exactly N `projection_cache` rows and exactly N `projection.filter.decide` spans (N = connected player count). No event escapes through an unfiltered pipe.

## Testing Strategy

Four layers. Every layer required.

1. **Predicate unit tests** — one test per predicate. Fake `GameStateView` + payload → assert `True`/`False`. The axioms.
2. **Rule-schema loader tests** — valid `projection.yaml` loads; every malformed-rule class (unknown predicate, type-mismatched mask, unknown field path, conflicting redactions, unreachable kind) fails loudly with a specific error. One test per error class.
3. **`ComposedFilter` scenario tests** — small `projection.yaml` + fake state → assert exact `FilterDecision`. Covers: each core invariant short-circuit, single rule, rule composition, pass-through for unknown kinds.
4. **End-to-end wiring test** — 2 players + 1 GM session. Events emitted. Assert:
   - Each player receives exactly what the rules prescribe
   - `projection_cache` has `N × events` rows
   - `projection.filter.decide` span count matches
   - **Reconnecting player receives byte-identical frames to the live session**
   - GM canonical view is untouched by any rule

The last bullet is the single-truth invariant made executable. It is the wiring test mandated by project rules — do not skip it.

## Migration & Rollout

Clean sequence. No feature-flag gymnastics.

1. **Core ships** — predicate catalog, `ComposedFilter`, `GameStateView` Protocol, validator changes, `projection_cache` table. No genre has a `projection.yaml` yet, so `ComposedFilter` composes `CoreInvariants + NoGenreRules`. Behaviourally this equals today's `PassThroughFilter` plus the (newly-enforced) core invariants. Ship.
2. **One reference genre opts in** — `mutant_wasteland` (fog-of-war is load-bearing there). Write its `projection.yaml`. Other genres still run pass-through. Ship. Playtest with the playgroup.
3. **Other genres opt in one at a time** as rules get written. No flag day.
4. **`PassThroughFilter` stays** as the documented "no rules configured" fallback, with a docstring pointing at `ComposedFilter`.

**Rollback.** If a genre's `projection.yaml` leaks something, `git revert` that one file. Core stays up. No kill switch needed — filter is per-session, and pack-load failures are loud.

## Open Follow-Ups (not blocking)

- **Scenario 3 — charm / illusion.** Separate spec. Needs narrator cooperation (second prompt pass or pre-declared illusion variants).
- **All-outbound-message coverage.** Today only EventLog-origin events pass through the filter; other WebSocket messages broadcast directly. Filter signature is already `MessageEnvelope`-shaped; widening coverage is a chore-level refactor at the send-side, no rule changes.
- **World-level overrides.** YAGNI until a world asks.
- **Predicate combinators (`all:` / `any:`).** Add when a genre accumulates five near-duplicate rules.
- **Legacy save-endpoint cleanup** (user-flagged item #2, not part of this spec): once this lands, the legacy `/api/saves/*` endpoints and the `(genre, world, player)` save-path helper in `persistence.py` from MP-01 can be deleted. File as chore.

## Impact Assessment

- **Who benefits:** Keith (narrator integrity — the GM panel can finally distinguish structural asymmetry from Claude improvising). Sebastien (mechanical transparency — `pf validate projection <genre>` is his rule-transparency tool). Alex (no specific impact; sealed-letter mechanics are orthogonal).
- **Blast radius:** Bounded. New table, new core module, new YAML file per opting-in genre. Existing `PassThroughFilter` and legacy paths unchanged. Rust-port story intact (rules remain data, not code).
- **Risk:** A miswritten genre rule could over-redact (boring) or under-redact (leak). Mitigations: mandatory validator, mandatory end-to-end wiring test, GM panel lie detector, one-genre-at-a-time rollout with playtest.
