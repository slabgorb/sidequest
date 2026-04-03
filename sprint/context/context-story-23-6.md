---
parent: context-epic-23.md
workflow: tdd
---

# Story 23-6: Replace hardcoded binary paths with bash wrapper names in orchestrator tool sections

## Business Context

The orchestrator's script tool sections (encountergen, namegen, loadoutgen) inject full filesystem
paths to compiled Rust binaries (`cfg.binary_path` + `cfg.genre_packs_path`). The prompt-reworked.md
spec uses bash wrapper names instead (`sidequest-encounter`, `sidequest-npc`, `sidequest-loadout`).
Wrapper names are portable, don't leak build paths into the prompt, and match how tools are invoked
in production (via PATH-resolved wrappers that set env vars internally).

## Technical Guardrails

- Script tool sections are built in `orchestrator.rs` L297-L393 inside `build_narrator_prompt()`
- Each tool has a `ScriptToolConfig { binary_path, genre_packs_path }` struct
- The current format strings embed `cfg.binary_path` and `cfg.genre_packs_path` directly
- Replace with wrapper command names: `sidequest-encounter`, `sidequest-npc`, `sidequest-loadout`
- The wrapper scripts already exist in `scripts/` — they resolve paths internally
- Story 23-9 handles env vars (`SIDEQUEST_GENRE`, `SIDEQUEST_CONTENT_PATH`); this story only changes the command names in the prompt text
- Update `scripts/preview-prompt.py` tool sections to match

## Scope Boundaries

**In scope:**
- Replace `cfg.binary_path` references with wrapper names in 3 tool section format strings
- Remove `cfg.genre_packs_path` from tool command syntax (wrappers handle it)
- Update orchestrator tests that assert on tool section content
- Update `scripts/preview-prompt.py` to use wrapper names

**Out of scope:**
- Env var injection (23-9)
- Tool section format simplification (23-11)
- ScriptToolConfig struct changes (may still be needed for allowedTools CLI flag)

## AC Context

1. encountergen tool section uses `sidequest-encounter` not `cfg.binary_path`
2. namegen tool section uses `sidequest-npc` not `cfg.binary_path`
3. loadoutgen tool section uses `sidequest-loadout` not `cfg.binary_path`
4. No filesystem paths appear in any tool section content
5. `scripts/preview-prompt.py` updated to match
6. Existing tool wiring tests updated or extended
