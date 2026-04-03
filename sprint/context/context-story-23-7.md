---
parent: context-epic-23.md
workflow: tdd
---

# Story 23-7: Wire tone axes injection into narrator prompt — TurnContext + genre pack models

## Business Context

The prompt-reworked.md spec defines a `<tone>` section with per-axis name, level, and description.
This controls the narrator's stylistic register — comedy vs gravity, wonder vs cynicism, etc.
Currently the narrator has `verbosity` and `vocabulary` controls (Late/Format) but no tone axes.
Genre packs don't define tone axes yet. This story adds the data model and wires injection.

## Technical Guardrails

- No `ToneAxis` type exists anywhere in the codebase yet — this is net new
- Genre pack models live in `sidequest-genre/src/models.rs`
- TurnContext is defined in `orchestrator.rs` L961-L991 — add `tone_axes: Vec<ToneAxis>` field
- The server assembles TurnContext in `dispatch/mod.rs` — must populate tone_axes from genre pack data
- Tone section goes in **Late/Format** zone per the Architect's zone mapping (story 23-1 session)
- `prompt-reworked.md` L167-L173 defines the template:
  ```
  <tone>
  {{#each tone_axes}}
  <axis name="{{name}}" level="{{level}}">
  {{description}}
  </axis>
  {{/each}}
  </tone>
  ```
- Story 23-5 (dynamic tone axes — genre packs define their own axis names) depends on this story
- Update `scripts/preview-prompt.py` to include tone section

## Scope Boundaries

**In scope:**
- Define `ToneAxis { name: String, level: f32, description: String }` in sidequest-genre models
- Add `tone_axes` field to genre pack YAML schema (optional, defaults to empty)
- Add `tone_axes: Vec<ToneAxis>` to TurnContext
- Populate TurnContext.tone_axes from loaded genre pack in server dispatch
- Register `<tone>` section in `build_narrator_prompt()` as Late/Format
- Add OTEL span for tone injection
- Update `scripts/preview-prompt.py`

**Out of scope:**
- Genre-pack-specific axis definitions (23-5 — uses hardcoded defaults for now)
- UI controls for tone adjustment
- Verbosity/vocabulary refactoring

## AC Context

1. ToneAxis struct exists in sidequest-genre models with name, level (0.0-1.0), description
2. Genre pack YAML supports optional `tone_axes` list
3. TurnContext carries tone_axes populated from genre pack
4. `<tone>` section registered in Late/Format zone in build_narrator_prompt()
5. OTEL span emitted with axis names and levels
6. `scripts/preview-prompt.py` shows tone section
