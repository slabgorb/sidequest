---
parent: context-epic-57.md
workflow: tdd
---

# Story 57-4: Migrate recency guardrail prose into tool-use descriptions

## Business Context

Four large prose blocks live in the **Recency** zone of the per-turn narrator prompt and re-state tool-use rules on every turn:

| Section | Site | Approx size | Governs |
|---|---|---|---|
| `npc_intro_visual_constraint` | `orchestrator.py:1764` | ~1 KB | Emitting `visual_scene` when `npcs_met[*].is_new == true` |
| `confrontation_trigger_constraint` | `orchestrator.py:1851` | ~3 KB | Populating `game_patch.confrontation` on stake-binding turns; specificity; "fire THIS turn" discipline |
| `npc_extraction_constraint` | `orchestrator.py:1934` | ~1.5 KB | Including every named/role-named person in `npcs_present` |
| `location_patch_constraint` | `orchestrator.py:1989` | ~1 KB | Setting `game_patch.location` when prose opens a new bold-titled room |

**Combined: ~6.5 KB / ~1.5 k tokens, every turn, uncached.**

They live in the Recency zone by deliberate choice — the original schema-block instructions are in the System zone where attention has decayed by turn 20+, so the rules were re-stated in the high-attention Recency zone. The cost cure of "just cache them" does not apply at the call site because Recency-zone content rides in the per-turn user message, which the Anthropic API does not cache the way it caches the `system=` array.

ADR-111 supplies the structural target: native tool-use (ADR-102) gives a third caching surface — the `tools=` array's `description` field. Tool descriptions are part of the cache key root, sent on every turn, cost once on cache write, and amortize across the entire save. Migrating each guardrail from a Recency-zone prose block into the `description` of the *tool whose payload field it governs* moves the prose into a cached path while preserving the high-attention positioning the original choice was solving for (tool descriptions ride right next to the tool's schema, which the model attends to whenever it's about to emit the tool call).

> **NOTE (Story 60-3, 2026-05-22):** the "amortize across the save" premise above is currently NOT realized — the narrator's tool-use loop continuation re-mints the whole cached prefix (system + tools) at 5m on every iter-2+ call, because the appended `tool_use`/`tool_result` messages carry no cache breakpoint. So moving prose into tool descriptions still costs a 5m re-write every turn until Story 60-4 adds a moving 1h breakpoint on the continuation. The migration is still worth doing (it's the right surface) but the token/cost win lands only after 60-4. See `sprint/archive/60-3-session.md`.

This is the **single biggest token-reduction story** in epic 57 (~1.5 k tokens × every turn × playtest hours = the largest cost line).

## Technical Guardrails

**Source ADR:** `docs/adr/111-narrator-guardrails-into-tool-descriptions.md` — read in full. Specifically:

- §Context — the four guardrails table with sites, sizes, and what they govern.
- §Decision — the migration rule (which prose moves into which tool's `description`).
- §Backend-gating discipline — only applies to `anthropic_sdk` backend.
- §References — the per-tool mapping is finalized at implementation time against the live tool registry. ADR locks the rule, not the row-by-row spreadsheet.

**Primary edit sites:**

1. `sidequest-server/sidequest/agents/orchestrator.py:1764, :1851, :1934, :1989` — the four Recency-zone registration calls. These are **conditionally removed** on the `anthropic_sdk` backend path and **preserved** on the Ollama / `claude -p` legacy paths.
2. The native tool-use tool registry (per ADR-102) — each migrated guardrail's prose appends into the `description` field of the corresponding tool definition. The exact tool names are resolved at implementation time by reading the live tool registry; ADR-111 leaves this concretization to the implementer.

**Backend-gating pattern:**

```python
if backend_supports_native_tools(backend):
    # Migrated: prose lives in tools= description; Recency registration suppressed.
    pass
else:
    # Legacy path: prose stays in Recency zone.
    register_recency_section("npc_intro_visual_constraint", ...)
```

The discriminator is the backend identifier (`SIDEQUEST_LLM_BACKEND`). The `anthropic_sdk` backend is the only path where the migration applies; the `claude -p` backend cannot reactively call tools mid-generation (project memory `project_claude_p_no_reactive_tools.md`) but it can still use the tool-output schema, so behavior preservation depends on which side actually consumes the description.

**Caution — backend matrix (from project memory and ADR-101 split):**

- `anthropic_sdk` (default backend, ADR-101) — native tool-use, supports `tools=` array with cached descriptions. **Migration applies.**
- `claude -p` subprocess backend (ADR-001 legacy, opt-in) — one-shot subprocess, no `tools=` API. **Migration does NOT apply; Recency-zone prose must stay.**
- Ollama backend (opt-in) — depends on whether the local model serves tool calls. **Treat as legacy path unless the local model genuinely supports the Anthropic-shaped tool-use protocol.**

The migration MUST NOT break the legacy paths. If TDD reveals that backend-gating adds significant complexity, an acceptable compromise is to ship the migration behind a feature flag (`SIDEQUEST_TOOL_DESCRIPTION_GUARDRAILS=1`) defaulting on for SDK, off for legacy. Log this as a Design Deviation.

**Pre- and post-migration regression detection (mandatory per ADR-111):**

Add a narrator-output regression counter — for a fixed corpus of test inputs, count how often each game_patch field is correctly populated before and after the migration. If the post-migration rate is lower, the migration regressed; the description prose needs sharpening or the migration is wrong for that guardrail.

**What NOT to touch:**

- Do not rewrite the guardrail prose. Move it verbatim into the tool description. ADR-111 ratified the migration shape, not a content rewrite.
- Do not refactor `prompt_framework` to add a new bucket. The migration uses the existing `tools=` array surface — no new bucket required.
- Do not delete the Recency-zone registration code paths — backend-gate them, preserve them.
- Do not migrate `genre_combat_voice` / `genre_chase_voice` or other unrelated sections — those belong to 57-3 (and are explicitly deferred there too).
- Do not change tool *schemas* — only the `description` field.

## Scope Boundaries

**In scope:**
- Identify the four target tools in the native tool-use registry that own each guardrail's payload field.
- For each, append the corresponding Recency-zone prose into the tool's `description`.
- Backend-gate the Recency-zone registrations at the four `orchestrator.py` sites.
- TDD: a test per guardrail asserting (a) the migrated prose appears in the SDK-backend `tools=` array, and (b) the Recency registration is suppressed for SDK and present for legacy.
- Add pre/post narrator-output regression counter (ADR-111 mandate).
- Add OTEL spans capturing per-tool description size deltas (ADR-111 observability requirement).

**Out of scope:**
- Rewriting guardrail prose.
- Adding new tools to the registry.
- Changing tool schemas.
- The 57-3 promotions (separate story, parallel).
- The 57-5 snapshot slimming (separate story, parallel).
- A behavior change in the legacy `claude -p` / Ollama paths.
- Migrating other Recency-zone sections (only the four named in ADR-111).

## AC Context

1. **Four guardrails migrated.** For each of `npc_intro_visual_constraint`, `confrontation_trigger_constraint`, `npc_extraction_constraint`, `location_patch_constraint`: the prose appears in the corresponding tool's `description` field on the `anthropic_sdk` backend, verifiable by inspecting the SDK call's `tools=` argument.
2. **SDK-backend Recency registrations suppressed.** On `anthropic_sdk` backend, the four `orchestrator.py` registration sites no longer add Recency-zone sections. Verified by asserting the Recency-zone section list for a test turn does not contain the four names.
3. **Legacy backend Recency registrations preserved.** On `claude -p` (or any non-SDK backend), the four sites still register Recency-zone sections. Verified by toggling `SIDEQUEST_LLM_BACKEND` in the test and asserting the section list contains the four names.
4. **Regression counter shows no drop.** For a fixed test corpus of 20+ narrator turns, the rate of correct `game_patch.confrontation` / `game_patch.location` / `npcs_met` / `npcs_present` field population is ≥ pre-migration rate. If the rate drops, the story does not pass — sharpen the description prose or back out the migration for that guardrail.
5. **OTEL emit confirms description-side ride.** Per-tool spans show the cached description-size growth on cache write turn 1, and `cache_read_input_tokens > 0` for the tools= array on turn 2+.
6. **Existing tests stay green.** Full `just server-test` runs green. No regressions in narrator orchestration, tool-use protocol, or backend dispatch tests.

## Assumptions

- ADR-102 native tool-use is live on the `anthropic_sdk` backend, and the `tools=` array's `description` field rides in the cache key root (per Anthropic API documentation). If this turns out not to be the case — e.g., descriptions are only cached when the schema is also unchanged across turns, and our schemas mutate per turn — log a Design Deviation immediately and consider whether the migration still pays off.
- A "live tool registry" exists in `sidequest-server/sidequest/agents/` where tool definitions live as code (not YAML). The implementer locates this at implementation start. If the registry is YAML-driven, the migration target shifts but the rule (description gets the prose) is the same.
- The four guardrails govern *exactly one* tool each. If implementation reveals a guardrail governs multiple tools, decide per-case: append to all, or pick the primary one. Log as a Design Deviation.
- The Recency-zone narrator turns are still bounded by ADR-098 (stateless, bounded per-turn). This story does not change that — the windowing constant (now `K=2` per story 57-1) stays.
- Project memory's `project_claude_p_no_reactive_tools.md` is correct: `claude -p` cannot call tools mid-generation, so the legacy-path preservation isn't a future-proofing burden; it's permanent for as long as `claude -p` is supported.
