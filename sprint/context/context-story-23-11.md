---
parent: context-epic-23.md
workflow: tdd
---

# Story 23-11: Rework tool sections — wrapper names, env vars, compact XML format

## Business Context

Combines three related changes to the orchestrator's script tool sections (encountergen, namegen,
loadoutgen) in a single pass through `orchestrator.rs` L297-L393:

1. **Wrapper names** (was 23-6): Replace hardcoded `cfg.binary_path` filesystem paths with
   portable wrapper names (`sidequest-encounter`, `sidequest-npc`, `sidequest-loadout`)
2. **Env vars** (was 23-9): Set `SIDEQUEST_GENRE` and `SIDEQUEST_CONTENT_PATH` on the Claude CLI
   subprocess so wrappers resolve paths from environment, not CLI flags in the prompt
3. **Compact format** (was 23-11): Replace verbose Markdown flag tables (~490 tokens) with compact
   `<tool>` XML format from prompt-reworked.md (~150 tokens). ~70% token reduction in Valley zone.

## Technical Guardrails

- Tool sections built in `orchestrator.rs` L297-L393 via match on tool_name (encountergen, namegen, loadoutgen)
- Each tool currently has a `format!()` call building the section with `cfg.binary_path`, `cfg.genre_packs_path`, `genre`
- `ScriptToolConfig { binary_path, genre_packs_path }` struct holds per-tool config
- Claude CLI invocation is in `client.rs` — env vars set there via `Command::env()`
- Genre name comes from `context.genre` (Option<String> on TurnContext)
- Content path comes from server `Args.genre_packs_path` — must flow to Orchestrator/ClaudeClient
- Wrapper scripts exist in `scripts/` — they read `SIDEQUEST_GENRE` and `SIDEQUEST_CONTENT_PATH`

**Target format from prompt-reworked.md:**
```xml
<tool name="ENCOUNTER">
When to call: any time new enemies enter the scene. Pick flags based on narrative context.
<command>sidequest-encounter [--tier N] [--count N] [--culture NAME] [--archetype NAME] [--role ROLE] [--context TEXT]</command>
<usage>
- [ ] Use the generated name in your narration
- [ ] Reference abilities from the abilities list (not invented ones)
</usage>
</tool>
```

**What to remove:**
- Flag tables (Claude can infer flag usage from command signature)
- "Output: JSON with..." descriptions (structured return, not narrator's concern)
- `--genre` and `--genre-packs-path` flags from command syntax (env var handled)

**What to keep:**
- "When to call" guidance (drives tool invocation timing)
- Checklist items (post-call verification)
- NPC tool's "MANDATORY: Call this BEFORE introducing any new NPC" rule

## Scope Boundaries

**In scope:**
- Replace 3 tool format strings with compact `<tool>` XML format
- Replace binary paths with wrapper names in command syntax
- Remove --genre/--genre-packs-path from command syntax
- Set `SIDEQUEST_GENRE` env var on Claude CLI subprocess
- Set `SIDEQUEST_CONTENT_PATH` env var on Claude CLI subprocess
- Flow `genre_packs_path` from server Args through to ClaudeClient
- Update orchestrator tests for tool sections
- Update `scripts/preview-prompt.py`
- Measure token savings

**Out of scope:**
- Adding new tools
- Changing tool behavior or output format
- ScriptToolConfig struct removal (may still be needed for `--allowedTools`)

## AC Context

1. All 3 tool sections use compact `<tool>` XML format (no flag tables)
2. Commands reference wrapper names (`sidequest-encounter`, `sidequest-npc`, `sidequest-loadout`)
3. No `--genre` or `--genre-packs-path` flags in prompt text
4. No filesystem paths in prompt text
5. `SIDEQUEST_GENRE` env var set on Claude CLI subprocess
6. `SIDEQUEST_CONTENT_PATH` env var set on Claude CLI subprocess
7. "When to call" and checklist preserved for each tool
8. NPC tool "MANDATORY: call before introducing any new NPC" rule preserved
9. Total tool section tokens reduced by ~60% or more vs current
10. `scripts/preview-prompt.py` updated with compact format
11. OTEL: tool section registration visible in ContextBuilder compose span
