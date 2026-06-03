---
id: 111
title: "Recency-Zone Narrator Guardrails Migrate to Tool Descriptions and Primacy-Cached Output Prose"
status: accepted
date: 2026-05-19
deciders: ["Keith Avery", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [9, 98, 101, 102, 110, 113]
tags: [agent-system, prompt-engineering, observability]
implementation-status: live
implementation-pointer: "sidequest-server/sidequest/agents/narrator_guardrails.py + orchestrator.py guardrail registration + intent_router.py CONFRONTATION_TRIGGER_CORE"
---

> **Amended 2026-05-23 by ADR-113.** The
> `confrontation_trigger_constraint` guardrail (the largest of the
> four, ~3 KB) governed the narrator's decision to populate
> `game_patch.confrontation` and was migrated onto the
> `begin_confrontation` tool description in story 59-1's amendment.
> ADR-113 retires `begin_confrontation` in Epic 59 story 59-4 (atomic
> migration to the IntentRouter spine). The engagement criteria
> migrate again — from the tool description to the IntentRouter's
> Haiku system prompt — and are no longer the narrator's concern.
> Caching tier remains system-block (Stable zone); the rule's
> "tool description is the cached home" intent generalizes to "the
> cached home for an engagement criterion is the system block of the
> agent that decides engagement." See ADR-113 §Decision §Retirement
> of self-reported engagement fields and §Implementation Notes for the
> sequencing detail. The other three guardrails
> (`npc_intro_visual_constraint`, `npc_extraction_constraint`,
> `location_patch_constraint`) are unaffected — they govern narrator
> emission of presentation fields, not engagement, and remain on
> their narrator-tool descriptions.

# ADR-111: Recency-Zone Narrator Guardrails Migrate to Tool Descriptions and Primacy-Cached Output Prose

## Status

Accepted. Implementation tracked under epic 57 (Narrator Prompt Token
Reduction), story 57-4. This ADR ratifies the migration shape — which
guardrails move where — and the backend-gated dual-path discipline. The
per-tool mapping is finalized at implementation time against the live tool
registry; this ADR locks the rule, not the row-by-row spreadsheet.

## Context

Four large prose blocks live in the Recency zone of the per-turn narrator
prompt and re-state tool-use rules on every turn:

| Section name | Site | Size | Governs |
|---|---|---|---|
| `npc_intro_visual_constraint` | `orchestrator.py` | ~1 KB | Emitting `visual_scene` when an `npcs_met` entry has `is_new: true` |
| `confrontation_trigger_constraint` | `orchestrator.py` | ~3 KB | Populating `game_patch.confrontation` on stake-binding turns; specificity; "fire THIS turn" discipline |
| `npc_extraction_constraint` | `orchestrator.py` | ~1.5 KB | Including every named/role-named person in `npcs_present` |
| `location_patch_constraint` | `orchestrator.py` | ~1 KB | Setting `game_patch.location` when prose opens a new bold-titled room |

**Combined: ~6.5 KB / ~1.5 k tokens, every turn, uncached.** They live in the
Recency zone by deliberate choice (the comment trail at each call site says
exactly so): the original schema-block instructions are in the System zone
where attention has decayed by turn 20+, so the rules were re-stated in the
high-attention Recency zone where the model is reliably reading them.

The cost cure of "just cache them" does not apply at the call site as-is:
Recency-zone content rides in the per-turn user message, which the Anthropic
prompt caching API does not cache the way it caches the `system=` array
(ADR-101 Phase D). Caching the guardrails requires *moving* them — not just
re-tagging the zone.

ADR-102 (Tool-Use Protocol for Structured Output) supplies the structural
target. With native tool-use, three caching surfaces exist that *do* persist
across turns:

1. **`system=` array blocks** with `cache_control` — already used for the
   Stable zone of the narrator prompt (ADR-101 Phase D Task 6).
2. **`tools=` array entries** — each tool's `description` field is part of
   the cache key root. Tool descriptions sent on every turn cost once (on
   cache write) and amortize across the save.
   > **NOTE (Story 60-3, 2026-05-22):** this "amortize across the save"
   > assumption is currently broken for the SAME reason block 0 is — the
   > narrator's tool-use loop continuation re-mints the whole cached prefix
   > (system + tools) at 5m on every iter-2+ call, because the growing
   > `tool_use`/`tool_result` conversation has no cache breakpoint. Until
   > Story 60-4 adds a moving 1h breakpoint on the continuation, moving
   > guardrails into tool descriptions does NOT realize the cache rebate.
   > See `sprint/archive/60-3-session.md`.
3. **The slimmed sidecar prose** (`narrator_prompts/output_only_sdk.md`)
   already lives in the Primacy/Stable cached zone via
   `Narrator.build_output_format(..., tool_backend=True)` at
   `narrator.py`.

The four Recency guardrails are *tool-use rules*. They tell the model when to
populate a specific field or call a specific tool. The natural home for a
tool-use rule is the tool's own description — adjacent to the artifact it
governs, in attention space when the model is considering invoking the tool,
and **cached for free** because Anthropic's cache root includes the
tools array.

The legacy `claude -p` backend cannot host this migration. Per project
memory, `claude -p` cannot call tools mid-generation (the transport is a
one-shot subprocess); the entire native-tool-use channel is unavailable.
ADR-101's `SIDEQUEST_LLM_BACKEND` env var defaults to `anthropic_sdk` and
`claude -p` is opt-in. The `narrator.py` docstring still flags the legacy
path as "the playgroup still plays on this path until merge, so it MUST NOT
drift" — that statement reflects a frozen-in-time concern about the SDK
cutover. After the cutover, the legacy path is opt-in safety net only. The
migration is therefore backend-gated, not backend-replacing.

## Decision

**Migrate the four Recency-zone guardrails out of the per-turn user message
on the SDK tool-use path. Retain them unchanged on the legacy `claude -p`
path. Route each guardrail's content to the cached surface adjacent to the
artifact it governs.**

### Routing rule (the principle, not the spreadsheet)

For each Recency guardrail, choose the migration target by *who owns the
artifact the rule governs*:

| Artifact owner under ADR-102 | Migration target |
|---|---|
| A native tool exists for the artifact | The tool's `description` field |
| The artifact is a sidecar field (no tool) | The slimmed-sidecar SDK prose (`narrator_prompts/output_only_sdk.md`) in the Primacy/Stable cached zone |
| The artifact is multi-tool (the rule governs choosing the right one) | The system-block "tool selection" section, paired with concise per-tool reminders inside each candidate tool's description |

The migration target for each guardrail is finalized in the 57-4
implementation pass by reading the live tool registry
(`sidequest-server/sidequest/agents/tools/`) and matching the governed
artifact to its owner. The four current guardrails resolve to:

| Guardrail | Governed artifact | Owner under E1.5-B | Migration target |
|---|---|---|---|
| `npc_intro_visual_constraint` | `visual_scene` field on the game_patch sidecar | Sidecar (slimmed-sidecar retained presentation field) | `output_only_sdk.md` — new "When to attach a visual_scene" subsection |
| `confrontation_trigger_constraint` | `game_patch.confrontation` (start) and `beat_selections` (active) | Mixed: start = `generate_encounter` / `start_confrontation` tool; active = `advance_confrontation` / `advance_encounter_beat` | Trigger-fire prose → start-confrontation tool description; specificity table → system-block "AVAILABLE ENCOUNTER TYPES" section (already present per orchestrator's confrontation context); the "do NOT defer to next turn" rule pinned to the start-confrontation tool description as a one-line invariant |
| `npc_extraction_constraint` | `npcs_present` sidecar list | Sidecar (presentation field; the auto-minter at `session_helpers._auto_mint_prose_only_npcs` is the server-side post-hoc safety net) | `output_only_sdk.md` — new "Roster discipline: prose-named persons" subsection |
| `location_patch_constraint` | `game_patch.location` | `apply_world_patch` tool (location is among the world-patch fields) | `apply_world_patch` description — "Set `location` when prose opens a new bold-titled room or moves the party into a different named space" |

Implementation may refine the table if the live tool registry's field
ownership has drifted from this snapshot; the **routing rule** above is the
contract.

### Backend-gated dual path

The Recency-zone `registry.register_section(...)` calls at
`orchestrator.py`, `:1851`, `:1934`, and `:1989` become conditional on
`context.tool_backend` (or equivalent — the field name is finalized in
implementation; today the equivalent test is
`isinstance(self._client, ToolingLlmClient)` per the `build_output_format`
caller):

```python
if not context.tool_backend:
    registry.register_section(
        agent_name,
        PromptSection.new(
            "npc_intro_visual_constraint",
            …existing prose…,
            AttentionZone.Recency,
            SectionCategory.Guardrail,
        ),
    )
```

On the SDK path, the four sections are *skipped entirely* (zero-byte-leak
discipline matching the pattern at `orchestrator.py` for the
`pending_trope_context` / `active_trope_summary` registrations). The content
lives at its new migration target, paid once and cached.

On the legacy `claude -p` path, the four sections continue to register
unchanged. The legacy path stays byte-identical to pre-111 behavior; the
playgroup safety net is preserved.

### Observability discipline (mandatory per repo CLAUDE.md)

Every guardrail in scope already pairs with an OTEL lie-detector span or a
server-side backstop. **None of those move.** The migration does not weaken
the safety net — it changes only where the *prevention* prose lives. The
post-hoc safety nets continue to fire whenever the prevention misses:

| Guardrail | Lie detector / backstop (unchanged) |
|---|---|
| npc_intro_visual | `render_trigger.py` NPC_INTRO classifier and the existing visual_scene presence checks |
| confrontation_trigger | `narration_apply._scan_for_confrontation_trigger_keywords` (the prose-vs-mechanical-track scanner that produced the 2026-05-03 Pingpong bug report) |
| npc_extraction | `session_helpers._auto_mint_prose_only_npcs` (the prose-only-first-mention catch-loop) and the `narrator.npc_extraction_*` spans it emits |
| location_patch | `narration_apply._apply_narration_result_to_snapshot` drift-repair backstop and the `narrator.location_drift_repaired` WARNING span |

Add one new span at the migration cutover so the GM panel can see the
migration is engaged on a given turn:

```
narrator.recency_guardrails_skipped {
  tool_backend: bool,                      # true on SDK path, false on legacy
  guardrails_skipped: list[str],           # names actually omitted this turn
  bytes_saved: int,                        # sum of len(prose) for omitted sections
}
```

This is the per-turn proof the migration is paying out, and it lets a
future regression (a re-bloat of Recency on the SDK path) be detected on
the GM panel rather than at PR review time.

### Acceptance gate

Story 57-4 is complete when, on a representative recorded playtest replay
exercising the SDK backend:

1. The SDK-path per-turn Recency-zone byte count is **≥ 5 KB smaller** than
   the pre-change baseline, measured via the existing prompt-zone size
   instrumentation and the new `narrator.recency_guardrails_skipped` span.
2. The slimmed-sidecar SDK prose (`narrator_prompts/output_only_sdk.md`)
   contains the migrated subsections for `visual_scene` and
   `npcs_present`. The system-block tool-selection section contains the
   confrontation-type specificity guidance. The `apply_world_patch` tool
   description contains the location-patch invariant. The
   `start_confrontation` / `generate_encounter` tool description contains
   the trigger-fire-this-turn invariant.
3. The four lie-detector spans / backstops fire at the **same or lower**
   rate as the pre-change baseline on the replay. A higher fire rate means
   the migration weakened the prevention; that field's rule is restored to
   the Recency zone on the SDK path (with a documented `# KEEP — migration
   regression on $turn_id` comment) and the savings target is re-measured.
4. The legacy `claude -p` path emits the four Recency sections **byte-
   identical** to the pre-change baseline. The path is exercised once on
   the replay (env-var override) to confirm.
5. The `narrator.recency_guardrails_skipped.bytes_saved` value matches the
   expected migration set on every SDK-path turn (zero on the legacy path).

## Consequences

### Positive

- **Direct cost reduction on every SDK turn:** ~1.5 k tokens / turn, paid
  every turn for the life of every save on the production backend. The
  cache write happens once (on the first turn after a tool-definition
  change); every subsequent turn rides the cache.
- **Attention co-location:** the rule lives where the model is reading
  when it considers the artifact. Tool descriptions are the canonical
  "when to use this tool" surface; the model is trained to read them.
- **Cache-invariant content stays cache-invariant:** today, a Recency
  block invalidates the per-turn prompt regardless of whether the rule
  text changes (the *zone* is uncached). After migration, the rule text
  becomes part of the cached tools / system surface.
- **Lie-detector clarity:** moving the prevention prose without moving
  the post-hoc detection makes the two layers structurally distinct.
  Sebastien's GM-panel view of "which layer caught this miss" stays
  legible.

### Negative

- **Audit cost at every tool addition:** new tools introduced after this
  ADR must consciously decide whether their `description` carries a
  rule-of-use clause. The DROP-list discipline from ADR-110 has its
  analogue here: tool descriptions are a living artifact, not a
  one-shot edit.
- **Cache invalidation on tool-description edits:** any edit to a
  migrated tool's description invalidates the tools-array cache root for
  every active save. The amortization model means a single edit is
  cheap (one cache write per save), but rapid iteration on the wording
  is more expensive than rapid iteration on a Recency-zone prose block
  would be. Mitigation: tool description text is reviewed at the same
  cadence as ADR text — slowly.
- **Dual-path maintenance burden:** the legacy `claude -p` branch keeps
  the Recency prose. Until the legacy path is retired (a follow-up ADR
  if and when the playgroup is fully off it), any future update to the
  four guardrails must be made in two places. Mitigation: the per-tool
  description text and the legacy-path Recency text are derived from a
  single source-of-truth constants file at implementation time, so
  divergence requires deliberate effort rather than a missed edit.

### Neutral

- The Recency zone retains its other contents — `recent_narrative_window`,
  `pacing_hint`, `narrator_directives`, `player_action`, the
  `verbosity` / `vocabulary` blocks. This ADR removes four blocks; the
  zone's role as the high-attention "what just happened and what should
  happen now" surface is unchanged.
- The slimmed-sidecar SDK prose grows by the migrated subsections. The
  Stable cached zone is the correct home for that growth; the per-turn
  cost remains zero after cache warmup.

## Alternatives Considered

### A. Move the four blocks into the System block without splitting per-tool

Single migration target: append the four prose blocks to the cached
`system=` array as a new "tool-use discipline" section.

Rejected because attention co-location is the larger win. A tool-use rule
in the System block is read once at session start; a tool-use rule in the
tool's description is read whenever the model is weighing the tool. The
Pingpong 2026-05-03 bug and the Glenross 2026-05-11 bug both occurred on
sessions that had received the System-block instruction *and ignored it*
under attention decay. The Recency-zone band-aid worked because attention
returned; the durable cure is to put the rule where attention returns
naturally — adjacent to the tool.

The System-block path is the correct fallback for the rules that govern
*choosing between tools* (e.g., the confrontation-type specificity table);
those are not per-tool descriptions and would awkwardly duplicate across
every candidate tool's description if pushed there.

### B. Retain Recency placement; compress prose

Keep the Recency-zone sections but trim each to a 1–2 sentence rule.
Estimated savings: 50–60 % of 6.5 KB.

Rejected because the bug-report prose at each call site is load-bearing.
The detailed examples (`"the cutter spins up THIS turn, fire chase
THIS turn"`, the social triggers table, the role-name list at
`npc_extraction_constraint`) are not stylistic — they are the regression
fingerprints. Compressed prose loses the *specificity that earned the
guardrail its place*. The migration target preserves that specificity at
zero per-turn cost; the compression target preserves only the high-level
rule.

### C. Retire the legacy `claude -p` path in this story

Drop the dual-path discipline; migrate unconditionally; let the legacy
path break.

Rejected as out-of-scope. Retiring the legacy path is a separate
decision with its own risk surface (no rollback if the SDK path hits a
new failure mode). ADR-101 supersedes ADR-001 in policy but does not
remove the legacy code path. The conservative move is to migrate the
guardrails while preserving the legacy escape hatch and address the
retirement separately if and when the SDK path is durably proven on the
playgroup.

### D. Move the guardrails into a separate Anthropic system block with its own cache_control

Three cached system blocks instead of one; the new third block holds the
four guardrails.

Rejected because it duplicates option A's flaw (attention not co-located
with the tool) without compensating gains. The tools array is *already*
cached as part of the system surface root; routing the per-tool rules
into per-tool descriptions costs nothing extra and gives the attention
benefit. A third system block would split the cache key further with no
upside.

## Implementation Notes

- **Story 59-4 / ADR-113 implementation pointer (2026-05-24).** The
  `confrontation_trigger_constraint` guardrail has completed its second
  migration: from the `begin_confrontation` tool description (Story
  59-1) onto the IntentRouter's Haiku system prompt at
  `sidequest/agents/intent_router.py::_SYSTEM_PROMPT`. The
  `begin_confrontation` tool itself is retired — file relocated to
  `sidequest/agents/tools/_retired/begin_confrontation.py` with a
  breadcrumb docstring, original-path import raises ImportError
  (CLAUDE.md "No Silent Fallbacks"). The narrator no longer reads
  confrontation engagement criteria at all because the narrator no
  longer decides engagement — the router does, pre-narrator. The
  `narrator_guardrails.CONFRONTATION_TRIGGER_CONSTRAINT` constant still
  exists for the legacy `claude -p` backend path (which is retired in
  practice per ADR-101 but remains the contract surface). Updated
  caching tier: the criterion now lives on the system block of the
  agent that decides engagement (the router), preserving the cached-home
  intent of this ADR. The
  `npc_intro_visual_constraint`, `npc_extraction_constraint`, and
  `location_patch_constraint` guardrails are unaffected — they govern
  narrator emission of presentation fields, not engagement, and remain
  on their narrator-tool descriptions.

- The four prose constants are extracted to a single source-of-truth
  module (working name: `sidequest/agents/narrator_guardrails.py`)
  housing one named constant per guardrail. Both the legacy Recency
  registration and the migrated tool descriptions reference these
  constants — no string duplication.
- Tool descriptions are edited via the tool's existing definition site
  under `sidequest/agents/tools/<tool>.py`. The migrated subsections
  for the slimmed-sidecar SDK prose are added to
  `narrator_prompts/output_only_sdk.md` directly (already cached).
- Tests (per the server-side wiring-test rule): an integration test
  asserts that on a representative turn, the SDK-path prompt assembly
  emits *zero* bytes for the four section names AND the migrated text is
  present in the SDK tools array / Primacy cached prose. A second test
  asserts the legacy path still emits all four sections byte-identical
  to the pre-change baseline. A replay-based test asserts the four
  lie-detector spans fire at the same-or-lower rate.
- This story coordinates with ADR-110 (story 57-5) only by ordering. They
  touch the same prompt-assembly module but different sections; either
  may merge first. The `narrator.recency_guardrails_skipped` span name
  must not collide with `narrator.state_summary_built` introduced by
  57-5 — both are net-new spans in separate categories.

## References

- ADR-009 — Attention-Aware Prompt Zones (why Recency exists and why the
  Stable cached zone is also high-attention)
- ADR-098 — Stateless Narrator Turns (the bounded-prompt regime this ADR
  optimizes within)
- ADR-101 — Anthropic SDK as Narrator Backend (the caching split this
  ADR exploits)
- ADR-102 — Tool-Use Protocol for Structured Output (the tool-description
  surface this ADR targets; the slimmed-sidecar contract)
- ADR-110 — Game-State Snapshot Slimming (sibling story 57-5; same epic)
- Stories 45-1, 45-8, 45-13, 49-1 — the prior load-bearing edits
  whose contracts are preserved
- Playtest bug reports: Pingpong 2026-05-03 (confrontation trigger),
  Glenross 2026-05-11 (gender flip; secateurs; location drift) — the
  fingerprints the guardrail prose was authored to prevent
