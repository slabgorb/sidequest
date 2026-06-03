---
id: 110
title: "Game-State Snapshot Slimming — Compact Encoding + Allowlist Pruning, Diff-with-Anchor Deferred"
status: accepted
date: 2026-05-19
deciders: ["Keith Avery", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [49, 98, 101, 102]
tags: [agent-system, prompt-engineering, observability]
implementation-status: partial
implementation-pointer: sidequest-server/sidequest/server/session_helpers.py#_PHASE_B_DROP_FIELDS
---

# ADR-110: Game-State Snapshot Slimming — Compact Encoding + Allowlist Pruning, Diff-with-Anchor Deferred

## Status

Accepted. Implementation tracked under epic 57 (Narrator Prompt Token Reduction),
story 57-5. This ADR ratifies the two-phase reduction path and explicitly defers
the diff-with-anchor and tool-fetch options to a follow-up if Phase A+B savings
prove inadequate.

**Amendment 2026-05-23 (epic 61).** Phase A+B savings *did* prove inadequate
at long session length — the 2026-05-23 cost-runaway incident (~$313 burned
in 48h) was driven by snapshot fields that grew monotonically with session
length but were not in Phase B's DROP list. Phase C (per-field projections,
NOT diff-with-anchor) shipped under story **61-2** as a smaller, lower-risk
slice of the original Option C: bounded projections (current-room-only,
in-scene-only, tail-K, size-cap) rather than RFC-6902 patches against a
periodic anchor. Diff-with-anchor (the literal Option C in the original
decision table) remains deferred and would now be re-scored against the
61-2 baseline if revisited. Option D (hierarchical lazy load via narrator
tool call) remains deferred for the same reasons given in the original §Alternatives.
See §Implementation Notes 2026-05-23 amendment below for details.

## Context

A token-cost audit of the narrator prompt assembly (see `sidequest/agents/orchestrator.py`
and `sidequest/server/session_helpers.py`) identified the per-turn `<game_state>`
block as the single largest uncached blob in the per-turn user message:

- **Construction site:** `session_helpers.py` — `state_summary_payload = json.loads(snapshot.model_dump_json())`, followed by mutations (drop `narrative_log` per ADR ratifying story 49-1, redact non-self characters per the notorious-party gate, merge `party_formation` and `shared_world_delta`), then `json.dumps(state_summary_payload, indent=2)` at `session_helpers.py`.
- **Injection site:** `orchestrator.py–1590` — wrapped in `<game_state>…</game_state>` and registered in the **Valley** zone of the three-zone caching split (ADR-101 Phase D). Valley is **uncached** by design — state changes every turn, so no `cache_control` breakpoint applies.
- **Observed size:** 5–10 KB / turn, ~1–2 k tokens. Sent every narrator turn.
- **Observed bloat sources:**
  1. `indent=2` pretty-printing — every nesting level pays 1 newline plus 2N spaces. Pure encoding waste; the LLM does not need pretty whitespace.
  2. Pydantic default fields serialized regardless of relevance — empty lists, default strings, `None` values for deferred subsystems (`active_tropes`, `axis_values`, `genie_wishes`, `achievement_tracker`, etc. per the `GameSnapshot` docstring at `session.py–530`).
  3. Fields whose presence in `<game_state>` is **not load-bearing** because the narrator reads them via dedicated prompt sections (e.g., `active_tropes` re-rendered in the Recency-zone `pending_trope_context` block).

The narrator must see ground-truth state — that is the explicit anti-confabulation
posture of the narrator-gaslighting doctrine and ADR-014's diamonds-and-coal
discipline. Cutting `<game_state>` blind risks silent quality regression (the
narrator confabulates a fact that the snapshot would have anchored). The
counter-evidence is that the narrator already does not see `narrative_log` here
(stripped per story 49-1) and the Recency-zone replacement carries the load-
bearing recall surface.

Four design options were on the table:

| Option | Mechanism | Est. savings | Risk | Implementation cost |
|---|---|---|---|---|
| A. Compact JSON encoding | Drop `indent=2`; `exclude_defaults=True, exclude_none=True` | 25–40% | ~zero (encoding-only) | trivial |
| B. Field-pruning allowlist | Audit narrator reads; drop fields no narrator path consumes | 20–40% additional | low (audit-bounded; OTEL-verifiable) | small |
| C. Diff-with-anchor | Periodic full anchor every K turns + JSON Patch (RFC 6902) deltas in between | 50–70% over K-window | medium (stale-anchor misread; replay correctness) | meaningful |
| D. Hierarchical lazy load | Tight summary + narrator `query_state(path)` tool fetches | 70–90% steady-state | medium (narrator may not know what to ask; per-call latency) | large; touches ADR-102 tool registry |

## Decision

**Adopt A + B. Defer C and D.**

The combined Phase A + Phase B target is a **≥50% reduction in `<game_state>`
bytes per turn** with zero narrator-quality regression. This is a single story
(57-5) executed in two phases under one PR.

### Phase A — Compact JSON encoding *(zero-risk baseline)*

At `session_helpers.py` and the equivalent encode in `local_dm.py`:

1. Replace `json.dumps(state_summary_payload, indent=2)` with the compact form
   (`separators=(",", ":")`).
2. Filter `state_summary_payload` to exclude pydantic defaults and `None`
   values BEFORE the post-construction mutations. The canonical entry point
   becomes `snapshot.model_dump(mode="json", exclude_defaults=True, exclude_none=True)`
   rather than `json.loads(snapshot.model_dump_json())`. The downstream mutations
   (`pop("narrative_log")`, character-list redaction, `party_formation` /
   `shared_world_delta` injection) continue to operate on the dict in-place.

**No semantic change.** Pydantic round-trip equivalence is preserved (a consumer
parsing the compact form back into `GameSnapshot` produces a model
`model_dump`-equivalent to the original; defaults reconstruct on parse).

### Phase B — Field-pruning allowlist *(audit-driven cut)*

Introduce a single named function — `build_state_summary_payload(snapshot, ...)` —
that owns the dict construction. The function applies a **DROP list** of field
names that have been audited as not narrator-load-bearing. The audit method:

1. **Static survey:** grep narrator prompt assembly (`orchestrator.py`,
   `narrator.py`, `narrator_prompts/*.md`) for snapshot field references. Any
   field whose name appears only inside `state_summary` serialization and
   nowhere in narrator prose or prompt-section registration is a drop candidate.
2. **Recency-zone overlap check:** any field already re-rendered by a dedicated
   prompt section (e.g., `active_tropes` via `pending_trope_context` /
   `active_trope_summary`, encounter via `encounter_live`/`encounter_summary`,
   NPCs via `npc_roster`) is dropped from `<game_state>` to eliminate
   double-rendering.
3. **Deferred-subsystem trim:** P2/P3/P5/P6 deferred fields per the
   `GameSnapshot` docstring (`session.py–530`) are dropped unless a live
   consumer is found. Their presence as empty defaults is already cheap after
   Phase A; their presence with content is the live-consumer signal.

The DROP list is named, comment-justified per entry, and lives next to the
construction function. **No silent fallbacks** — if a future field's narrator-
relevance is unknown, it stays in by default; the DROP list is the conscious
removal, not the omission.

### Caching posture (unchanged)

`<game_state>` stays in the Valley zone, uncached. Caching the snapshot would
require either a stable-zone anchor (Option C) or a tool-fetched detail model
(Option D); both are deferred.

### Observability (mandatory per repo CLAUDE.md)

Add an OTEL span at the `state_summary_json` construction site:

```
narrator.state_summary_built {
  bytes: int,                      # len(state_summary_json.encode("utf-8"))
  fields_dropped: list[str],       # the DROP list names actually omitted
  fields_emitted: int,             # top-level key count in the final dict
  interaction: int,                # snapshot.turn_manager.interaction
}
```

This is the GM-panel lie detector: it lets Sebastien (and the architect
auditing the next cost regression) see the per-turn dump size and the DROP-list
contents on every turn, not just at PR-review time. Pair the span with a
log line at the same site (matching the existing
`state.room_state_injected` pattern at `session_helpers.py`).

### Acceptance gate

Story 57-5 is complete when, on a representative recorded playtest replay:

1. Per-turn `<game_state>` UTF-8 byte count is **≥ 50% smaller** than the pre-
   change baseline, measured via the new `narrator.state_summary_built` span.
2. The PC's name, the party's current room, the active encounter (if any),
   the active per-room container retrievals, the `shared_world_delta`
   adjacency, and `party_formation` are **all still present** in the emitted
   payload. These are the load-bearing fields per stories 45-1, 45-8, 45-13,
   and the per-room-state injection contract.
3. The replay's narrator output is reviewed for confabulation regressions on
   any field marked for the DROP list. If a regression is found, the field
   moves out of the DROP list and the savings target is re-measured. Any
   field that cannot stay dropped without regression is documented inline
   in the DROP list as `# KEEP — confabulation regression on $turn_id`.
4. The notorious-party gate (story 45-8) still redacts non-self characters
   from the emitted JSON. The gate logic at `session_helpers.py` is
   preserved verbatim — the encoding/pruning changes operate on the dict
   it produces.

## Consequences

### Positive

- **Direct cost reduction:** the largest uncached per-turn blob shrinks by
  ≥50%, paid on every narrator turn for the life of every save. Multiplied
  by playtest hours, this is the largest single recurring cost cut available
  in epic 57 without an ADR-shaped redesign.
- **Observability dividend:** the new span makes future state-summary
  regressions detectable on the GM panel. Today a future snapshot field can
  silently add 2 KB/turn; after this, it adds a visible delta in
  `narrator.state_summary_built.bytes`.
- **Decoupling from the deferred-subsystem fields:** their cost stops scaling
  with default verbosity.

### Negative

- **Audit debt:** the DROP list is a living artifact. Each new `GameSnapshot`
  field forces an explicit decision (emit or drop). This is the cost of an
  allowlist — the alternative is silent re-bloat.
- **Confabulation risk in the playtest after the cut:** the only way to find
  out a field was load-bearing is for the narrator to fabricate around its
  absence. Mitigation: the acceptance gate's regression-review step and the
  KEEP escape hatch inside the DROP list itself.
- **Two phases inside one story:** Phase A is encoding-only and zero-risk;
  Phase B is the audit cut. Reviewing them as a single PR means the savings
  attribution requires reading the new span — not a blocker, but worth
  flagging for the reviewer.

### Neutral

- The Valley-zone caching posture is unchanged. This ADR does not introduce
  any new caching breakpoint and explicitly defers the question of whether
  `<game_state>` should ever be cacheable.
- The pydantic round-trip property is preserved; saved-game persistence is
  untouched. `state_summary_json` is a *transient prompt artifact*, not a
  storage format.

## Alternatives Considered

### Option C — Diff-with-anchor

Send a full snapshot every K turns; in between, send a JSON Patch (RFC 6902)
relative to the last anchor.

Rejected for the current story for three reasons:

1. **Coherence risk under sealed-letter MP:** the narrator's per-turn view is
   already subject to perception filtering (ADR-104) and broadcast-layer
   firewall (ADR-105). A K-turn-back anchor plus per-turn patches multiplies
   the surface area where a filter-vs-anchor mismatch could leak.
2. **Cache-position problem:** the only way diff-with-anchor pays off is if
   the anchor itself rides in a cached position, which the Anthropic prompt
   caching API does not afford for user-message content. Realizing the
   savings requires either an architectural move into the system block
   (large lift, breaks the "system is static" property) or accepting an
   uncached anchor (loses most of the savings).
3. **Phase A + B savings are likely sufficient.** Compact encoding plus a
   targeted DROP list is projected to hit the ≥50% target without the
   diff-machinery cost.

If Phase A + B underdeliver — measured via the new
`narrator.state_summary_built.bytes` span — a follow-up ADR can revisit
Option C with concrete numbers instead of estimates.

### Option D — Hierarchical lazy load via narrator tool call

Replace the dense `<game_state>` block with a tight summary (~200 chars:
`location`, `party_at`, `time_of_day`, `days_elapsed`, `interaction`,
`in_encounter`) and let the narrator call a `query_state(path)` tool
(routed through the ADR-102 tool registry) to fetch detail on demand.

Rejected for the current story for three reasons:

1. **Narrator-doesn't-know-to-ask problem:** the narrator's job is to
   *gaslight from ground truth*, which is the opposite stance from
   *reactively fetch when uncertain*. The model has no signal to query a
   field whose absence it has not noticed.
2. **Tool round-trip latency:** every `query_state` call is an extra round
   trip in the per-turn assembly. The current playgroup pacing model is
   submit-and-wait under ADR-036's 2026-05-03 amendment; adding latency
   here cuts directly into the slow-typist accommodation that gate exists
   to protect.
3. **Larger blast radius:** Option D touches the tool registry, the
   perception-filter boundary (ADR-104/105), and the OTEL span taxonomy
   simultaneously. It is a separate ADR's work, not a sub-step of 57-5.

Option D remains a credible candidate for a future epic if Phase A + B
prove inadequate AND a per-call latency budget is established.

### Option E — Full subjective re-shaping (per-PC `<game_state>`)

Considered briefly: build a separate `<game_state>` per acting PC, scoped
exactly to what that PC perceives. Rejected as overlapping with
ADR-104/105 (perception filtering at the tool layer + broadcast firewall).
The perception apparatus is the correct seam for asymmetric subjective
state, not the encoding-layer slimming this ADR addresses.

## Implementation Notes

- The construction function lives in `session_helpers.py` next to the
  existing logic (no new module). The pre-existing mutations
  (`narrative_log` pop, character-list redaction, `party_formation` /
  `shared_world_delta` merge) remain in place and operate on the dict the
  new function returns.
- The `local_dm.py` `<game_state>` injection site receives the same
  compact-encoded value. Per the dormancy note in the project context
  (CLAUDE.md: "LocalDM preprocessor dormant per 2026-04-28 spec"), this is
  defensive consistency only — the code path is not currently active —
  but keeping both encode sites aligned prevents a future re-activation
  from silently re-bloating.
- Tests: the project's wiring-test rule (server CLAUDE.md, "Every Test
  Suite Needs a Wiring Test") requires at least one integration-level
  assertion. A fixture-replay test asserts the byte-count target on a
  recorded snapshot and asserts the load-bearing-field set is present.
  Unit tests cover compact-encode round-trip equivalence and DROP-list
  field omission.
- The DROP list is reviewed at every PR that adds a `GameSnapshot` field
  going forward. The schema-validation hook does not enforce this today —
  flagged here as a follow-up consideration, not a blocker. **Amendment
  2026-05-23 (story 61-5).** "Reviewed at every PR" failed silently on
  2026-05-19 when ADR-109 added `location_descriptions` as a growing
  persistent field without updating the DROP list. Five days later the
  cost runaway hit. Story **61-5** introduces a pydantic `model_fields`
  reflection test (the "tripwire" pattern, per server CLAUDE.md "No
  Source-Text Wiring Tests") that asserts every top-level `GameSnapshot`
  field is in one of three registries — `_PHASE_B_DROP_FIELDS`,
  `_PHASE_C_PROJECTIONS` (new), or `_BOUNDED_BY_CONSTRUCTION` (new) —
  and fails the test suite when a new field lands without an explicit
  decision. Makes the un-enforced review rule enforceable.

### Amendment 2026-05-23 — Phase C landed under story 61-2

Story 61-2 ("Extend snapshot drop-list to cover the seven growing
fields") landed the per-field projection layer originally framed in the
§Decision table as Phase C / Option C. The implementation is *narrower*
than Option C as originally specified (no RFC-6902 patches, no periodic
anchor) — instead, four bespoke projections fire on every turn:

| Field | Projection | Code |
|---|---|---|
| `room_states` (top-level) | Keep only the acting PC's `current_room_id` entry; empty dict when room is absent (structural anchor preserved). | `session_helpers.py:_apply_phase_c_projections` |
| `npcs` (top-level) | Keep only NPCs whose `last_seen_location == current_room_id` OR who appear in an unresolved encounter's `actors[*].name`. Off-stage NPCs retain identity via `npc_pool` (gaslighting-doctrine anchor). Surviving entries drop nested `belief_state`. | `session_helpers.py:_npc_in_scene` + `_apply_phase_c_projections` |
| `characters[*].known_facts` (nested) | Tail-K=8 per PC (mirrors `persistence.py` journal-render tail). | `session_helpers.py:_apply_phase_c_projections` |
| `scenario_state.discovered_clues` (nested) | Cap at 12, sorted by clue id for determinism (the source is a `set[str]`). | `session_helpers.py:_apply_phase_c_projections` |

Test contract: `sidequest-server/tests/server/test_61_2_snapshot_seven_field_projection.py` (17 tests).
OTEL: `prompt.game_state.bytes` span carries new count attributes
`room_states_dropped`, `npcs_dropped`, `known_facts_truncated_total`,
`clues_truncated`.

**3-of-7 decoy finding.** Epic 61 named *seven* fields as bloat
sources. Validation against `GameSnapshot.model_fields` during 61-2
red-phase surfaced that **three of the seven are not snapshot fields at
all**:

- `journal` — derived from `Character.known_facts` + the event log via
  `JournalRequestHandler` (ADR-100). Not persisted to `GameSnapshot`.
- `footnotes` — per-turn `NarrationResult.footnotes`
  (`orchestrator.py`); event-log-bound, never persisted to snapshot.
- `location_descriptions` — ADR-109 manifests ride out-of-band via
  `LOCATION_DESCRIPTION` WebSocket messages, loaded from
  `cookbook/assemble.py` at room change. No `snapshot.location_descriptions`
  field exists.

These three got **regression guards** in the 61-2 test file (the seven
anchor tests under "Passing tests" in the 61-2 red-phase notes) — if a
future PR materializes any of them onto `GameSnapshot`, the guards fail
fast and force an explicit projection decision. The cost-runaway diagnosis
stands on the four real bloat sources; the 3-decoy correction is a
documentation accuracy point, not a recission of the underlying claim.

**Degraded-location gaslighting doctrine.** When
`snapshot.party_location(perspective=...)` returns `None` or empty
(degraded actor location), the `room_states` and `npcs` projections
**skip** (pass-through the original data) rather than emitting empty
collections. Reasoning: degraded location is not the same as "no NPCs
exist" or "no rooms exist," and silently stripping them would gaslight
the narrator into confabulating around an empty world. The
`known_facts` and `discovered_clues` projections still run (PC- and
scenario-scoped, independent of actor location). An
`actor_location_empty` warning fires BEFORE the projection runs so the
GM panel sees the degraded-location signal next to the skip outcome,
not after.

**Phase D (tool-fetched lazy load) remains deferred.** The
narrator-doesn't-know-to-ask problem and the tool round-trip latency
arguments from the original §Alternatives still apply. If 61-2's bounded
projections still leave the Valley too large at session length 100+, a
future ADR can revisit Phase D with concrete numbers.

## References

- ADR-014 — Diamonds and Coal (narrator detail discipline)
- ADR-049 — Narrator Verbosity (Recency-zone tuning)
- ADR-098 — Stateless Narrator Turns (bounded per-turn prompts)
- ADR-101 — Anthropic SDK as Narrator Backend (three-zone caching split)
- ADR-102 — Tool-Use Protocol for Structured Output (the tool-registry
  seam Option D would touch)
- ADR-104 — Perception Filtering at the Tool Layer
- ADR-105 — Broadcast-Layer Perception Firewall
- Stories 45-1, 45-8, 45-13, 49-1 — the prior load-bearing edits to
  `state_summary` whose contracts this ADR preserves
