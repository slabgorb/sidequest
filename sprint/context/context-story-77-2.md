---
parent: context-epic-77.md
workflow: tdd
---

# Story 77-2: Typed quest/stakes narrator tools — record_quest + set_stakes (ADR-102)

## Business Context

This story is the **load-bearing create/evolve mechanism** for the campaign spine.
Today there is a lane to UPDATE a quest but no first-class lane to CREATE/anchor one,
and stakes only flow from two off-path writers (the **deprecated** `apply_world_patch`
escape hatch the narrator is told never to touch, and a **trope-resolution handshake**
that needs a *resolved* trope and so never fires in a prose-only pack). The
wry_whimsy/oz playtest (2026-06-02, 13 turns) ran an entire "the traveler wants only to
go home" premise with `quest_log: {}`, `quest_anchors: []`, `active_stakes: ""` — a
campaign spine that silently vanished from state. That is exactly the "convincing
narration with zero mechanical backing" failure the OTEL Observability Principle exists
to catch, and the tell no human DM would produce for a forever-GM-turned-player like
Keith.

Crucially, this is the story that **actually closes the gap for prose packs**.
Seed-at-creation (77-1) cannot do it alone there: per the epic AC and `builder.py:423`,
`Character.drive` defaults to `''` when a genre has no drive-shaped chargen scene
(wry_whimsy is exactly such a pack), so the creation seed degrades to an empty spine.
ADR-137's "Option B" — the typed tools delivered here — is the load-bearing fix for
prose packs, because it lets the narrator originate and evolve a quest *in play* from
the prose itself rather than from a chargen-time drive field that doesn't exist. C =
A + B closes the gap at both ends; this story owns the B half and is the only place a
prose-pack spine can come from.

These tools also become the **single create/evolve mechanism** the rest of the epic
consolidates onto — 77-4 (cleanup) migrates the legacy `quest_updates` lane and strips
the `apply_world_patch` quest/stakes paths *onto these tools*. There is nothing to
migrate to until they exist. Player-facing payoff lands in 77-5 (the quests panel), but
only after this server lane is OTEL-verified independently (the GM panel is the
lie-detector).

## Technical Guardrails

**Two NEW typed narrator tools**, both `@tool`-decorated `ToolCategory.WRITE` adapters
following the ADR-102 structured-output contract (Pydantic `args_model`, typed handler,
per-tool OTEL span, `ToolResult` returned to the model). Use an existing WRITE tool as
the canonical shape: `sidequest/agents/tools/update_npc_disposition.py` (loads the
session via `ctx.repository.load()`, mutates `snapshot`, `ctx.repository.save(snapshot)`,
enriches `ctx.otel_span` with `tool.<short>.*` attributes, returns `ToolResult.ok(...)`).

- **`record_quest`** — mint/evolve a quest. ADR-137 specifies the structured shape:
  **id + title + objective + status + optional anchor** (`§Decision 2`). Today
  `snapshot.quest_log` is `dict[str, str]` (id → status-string; `session.py:671`), so a
  structured quest does NOT fit the current storage as-is. **Resolve this explicitly,
  do not assume.** Two viable shapes — confirm with the design before coding:
  (a) keep `quest_log: dict[str, str]` and serialize the structured quest into the
  value, or (b) widen `quest_log` to a structured entry type. Whatever is chosen, the
  tool MUST write `quest_log` and (per the epic write-path diagram) feed `quest_anchors`
  when an anchor is supplied. NOTE the boundary: promoting `quest_anchors` to a
  first-class `WorldStatePatch` field + real apply path is **77-3**, not this story — if
  77-3 has not landed, `record_quest` writing an anchor must either land on the same
  `snapshot.quest_anchors` list (`session.py:736`, a `list[str]` of beat/location ids)
  directly through the loaded snapshot, or the anchor sub-feature defers to 77-3. Flag
  this sequencing in the implementation.
- **`set_stakes`** — set/append `snapshot.active_stakes` (`session.py:742`, a single
  `str`). The epic AC is binding: **reuse the existing `_ACTIVE_STAKES_GUARDRAIL = 1024`**
  (`sidequest/server/narration_apply.py:5805`) so a runaway narrator string cannot
  pollute state. The existing trope handshake (`narration_apply.py:5855-5867`) already
  shows the append-then-trim pattern against that guardrail and tracks an
  `active_stakes_appended` / `is_fresh` flag — mirror it (the `stakes.set` span carries
  `is_fresh`).

**Schema discipline / cost.** Bound both schemas **tightly** (ADR-102 typed contract;
SOUL §Cost Scales with Drama) — a quiet town walk must NOT mint a quest. Per the epic
AC, also add a **cardinality cap on `quest_log` / `quest_anchors` at the Pydantic schema
layer** (unbounded narrator strings persisting to Postgres is a state-bloat vector).
Lean on prompt caching for the added tool surface. Tool descriptions should make the
mint-vs-update distinction explicit so the narrator does not spawn quests gratuitously.

**OTEL spans (the GM-panel lie-detector for this substrate).** Add to
`sidequest/telemetry/spans/state_patch.py` (the existing quest/stakes span home — it
already defines `SPAN_QUEST_UPDATE = "quest_update"` at l.29 and `quest_update_span`
at l.103, each wired through `SPAN_ROUTES` so the `WatcherSpanProcessor` re-emits a
`state_transition` event the GM panel reads). Follow that exact `SPAN_ROUTES[...] =
SpanRoute(...)` + helper-emitter pattern:

| Span | Emitted when | Attributes (per ADR-137 §OTEL) |
|------|--------------|--------------------------------|
| `quest.created` | `record_quest` mints a new quest | `quest_id`, `title`, `source` (creation\|narrator), `anchor_count` |
| `quest.updated` | `record_quest` changes status — **replaces `SPAN_QUEST_UPDATE`** | `quest_id`, `old_status`, `new_status` |
| `stakes.set` | `set_stakes` writes/appends | `length`, `source`, `is_fresh` |

`quest.updated` is the successor to the legacy `quest_update`/`SPAN_QUEST_UPDATE` span;
the legacy span and `quest_update_span` helper are consumed by the
`result.quest_updates` apply at `narration_apply.py:2863-2878`, which 77-4 retires. This
story may keep the old span live alongside the new one until 77-4 cuts the legacy lane.
`quest.seeded_at_creation` (77-1) and `quest.anchor.added` (77-3) are OTHER stories' spans
— do not implement them here.

**Wiring (Verify Wiring, Not Just Existence).** A new tool file is dead until it is
registered. Both tools MUST be added to the barrel import in
`sidequest/agents/tools/__init__.py` (the `from sidequest.agents.tools import (...)`
block) so `@tool` fires at import time and the registry exposes them in
`tool_definitions()`. There is also a hard coverage gate:
`tests/agents/test_sidecar_coverage_map.py` (ADR-102 §Coverage) asserts every former
sidecar field has a designated successor tool — confirm the quest/stakes successor
mapping there stays green (the `quest_updates` sidecar field's successor is now
`record_quest`).

**Path correction for downstream agents:** the epic context lists
`agents/narration_apply.py`; the file actually lives at
`sidequest/server/narration_apply.py`. Line numbers cited in the epic (2872, 5762) are
approximate — the live `quest_log` write is at `narration_apply.py:2863-2878` and the
guardrail constant is `_ACTIVE_STAKES_GUARDRAIL = 1024` at `narration_apply.py:5805`.

## Scope Boundaries

**In scope:**
- The two new typed WRITE tools `record_quest` and `set_stakes` (`@tool` adapters under
  `sidequest/agents/tools/`, ADR-102 contract, Pydantic `args_model`).
- Their write paths: `record_quest` → `quest_log` (+ `quest_anchors` when an anchor is
  given, subject to the 77-3 sequencing note); `set_stakes` → `active_stakes` with the
  `_ACTIVE_STAKES_GUARDRAIL` reuse.
- The three new OTEL spans (`quest.created`, `quest.updated`, `stakes.set`) in
  `telemetry/spans/state_patch.py`, routed via `SPAN_ROUTES` for the GM panel.
- Tightly-bounded schemas + cardinality caps (epic AC).
- Registry wiring (barrel `__init__.py` import) and keeping the sidecar coverage-map
  gate green.

**Out of scope:**
- **Seed-at-creation** (deriving the spine from PC drive/calling at session init) —
  **77-1**.
- **Promoting `quest_anchors` to a first-class `WorldStatePatch` field** (adding it to
  the patch at `session.py:420`/decl region + a real apply path) and wiring it into
  `orbital/course.py` — **77-3**, plus the `quest.anchor.added` span. This story may
  write `snapshot.quest_anchors` directly through the loaded snapshot if an anchor is
  supplied, but must not own the patch-field promotion.
- **Retiring the `quest_updates` extraction lane / stripping `apply_world_patch`
  quest/stakes paths** — **77-4** (`type: refactor`, p3). **LOCKSTEP DEPENDENCY, flag it
  loudly:** ADR-137 §Consequences and the epic guardrail both state 77-4 must land in
  lockstep with this story (the ADR's internal numbering calls this story "77-3" and its
  lockstep partner "77-5" — sprint mapping: ADR 77-3 → sprint **77-2**, ADR 77-5 →
  sprint **77-4**). Until 77-4 cuts the legacy `quest_updates` apply
  (`narration_apply.py:2863`) and the `apply_world_patch` `/active_stakes`+`/quest_log`
  paths, BOTH the new tools AND the old lanes can write quests/stakes — saves could carry
  quests minted by a lane that is about to be retired. Do not delete the legacy lane
  here; do not ship this story to production without 77-4 gated behind it.
- **The quest/objective UI panel** (rendering the `quests` payload) — **77-5**.
- **wry_whimsy `seed_tropes` content** (`active_seeds` carve-out) — **77-6**, content.

## AC Context

The sprint YAML carries a single explicit AC (the bounded-state guardrail); the fuller
acceptance surface is ADR-137 §Decision 2 + §OTEL spans + §One-mechanism consolidation.
Expand into testable detail (TDD — write the failing test first, watch it fail):

1. **Bounded narrator-controlled state (the explicit YAML AC).**
   - `set_stakes` reuses `_ACTIVE_STAKES_GUARDRAIL = 1024` and trims when the resulting
     `active_stakes` exceeds it. RED test: call `set_stakes` with input that pushes
     `active_stakes` past 1024 chars; assert the stored field is ≤ 1024 and the trim
     preserves the fresh tail (mirror the handshake trim at `narration_apply.py:5860`).
   - `record_quest` enforces a **cardinality cap** on `quest_log` / `quest_anchors` at
     the Pydantic schema layer. RED test: a call exceeding the cap is rejected by the
     `args_model` validation (or the handler refuses with a structured `ToolResult`
     error) — assert state does not grow unbounded.

2. **`record_quest` mints a structured quest (create affordance).**
   - Calling `record_quest` with id/title/objective on a snapshot whose `quest_log` is
     empty results in a `quest_log` entry keyed by that id. Assert against the actual
     storage shape chosen (see Technical Guardrails — confirm structured-vs-string with
     the design first).
   - **Span-assertion test (lie-detector):** driving `record_quest` for a NEW quest
     fires the `quest.created` span with `quest_id`, `title`, `source`, `anchor_count`.
     Use the OTEL span-assertion pattern (drive the tool through the registry/handler,
     assert the span fired with the expected attributes) — NOT a source-text grep
     (No Source-Text Wiring Tests, server CLAUDE.md). The `state_patch.py` spans route
     through `SPAN_ROUTES`/`WatcherSpanProcessor`; assert the routed `state_transition`
     event reaches the GM-panel feed, the way `SPAN_QUEST_UPDATE` does.

3. **`record_quest` status-update mode fires `quest.updated`.**
   - Calling `record_quest` against an EXISTING quest id with a changed status updates
     the entry and fires `quest.updated` with `quest_id`, `old_status`, `new_status`.
     This is the behavioral successor to the legacy `quest_updates`/`SPAN_QUEST_UPDATE`
     lane; assert the new span fires (the old one may still co-fire until 77-4).

4. **`set_stakes` sets/appends `active_stakes` and fires `stakes.set`.**
   - Fresh stakes on an empty `active_stakes`: assert the field is set and `stakes.set`
     fires with `length`, `source`, `is_fresh=true`.
   - Append onto existing stakes: assert append behavior and the `is_fresh` flag mirrors
     the existing `active_stakes_appended` semantics (`narration_apply.py:5875`).

5. **Wiring test (mandatory per CLAUDE.md "Every Test Suite Needs a Wiring Test").**
   - Assert both tools are registered and reachable from production code paths — e.g.
     they appear in the registry's `tool_definitions()` after importing the tools barrel,
     and the `test_sidecar_coverage_map.py` gate (ADR-102 §Coverage) still passes with
     `quest_updates`'s successor pointing at `record_quest`. This is the integration leg
     proving the tools are not orphaned adapters.

## Assumptions

- `quest_log` storage shape for a *structured* quest (id+title+objective) is the one
  open design question. Current storage is `dict[str, str]` (`session.py:671`); ADR-137
  asks for structured. The next agent MUST confirm the chosen shape (serialize-into-value
  vs widen-the-type) with the design before committing — do not silently pick one.
- The lockstep with 77-4 is real and gating. If 77-4 is not yet in flight, surface that
  to the SM rather than shipping the new tools alongside an un-retired legacy lane.
- `record_quest`'s optional-anchor sub-feature interacts with 77-3; if 77-3 has not
  landed, either write `snapshot.quest_anchors` directly through the loaded snapshot or
  defer the anchor write to 77-3. Confirm sequencing before coding the anchor path.
