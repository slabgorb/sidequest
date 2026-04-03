---
parent: context-epic-23.md
workflow: tdd
---

# Story 23-9: Set SIDEQUEST_GENRE and SIDEQUEST_CONTENT_PATH env vars per-session on script tool commands

## Business Context

Script tools (encountergen, namegen, loadoutgen) currently receive `--genre` and `--genre-packs-path`
as CLI flags embedded in the prompt text. The prompt-reworked.md spec uses bash wrappers that read
`SIDEQUEST_GENRE` and `SIDEQUEST_CONTENT_PATH` from the environment instead. This removes
genre-specific paths from the prompt (shorter tool sections, less noise in Valley zone) and lets
wrappers resolve paths independently.

## Technical Guardrails

- Script tools are invoked by Claude as subprocess calls during narration
- The orchestrator sets `--allowedTools` on the Claude CLI invocation to permit tool use
- Environment variables must be set on the Claude CLI subprocess, not the Rust server process
- `ScriptToolConfig` in orchestrator.rs holds `binary_path` and `genre_packs_path`
- The genre name comes from `context.genre` (Option<String> on TurnContext)
- `content_path` comes from server Args.genre_packs_path
- These env vars should be set once per session (genre doesn't change mid-session)
- Pairs naturally with 23-6 (wrapper names) — the wrappers read these env vars

## Scope Boundaries

**In scope:**
- Set `SIDEQUEST_GENRE` env var on Claude CLI subprocess invocation
- Set `SIDEQUEST_CONTENT_PATH` env var on Claude CLI subprocess invocation
- Remove `--genre` and `--genre-packs-path` flags from tool section prompt text
- Verify wrapper scripts read these env vars (or document what they need)
- Update `scripts/preview-prompt.py`

**Out of scope:**
- Tool section format changes (23-11)
- Wrapper command name changes (23-6 — may already be done)
- Claude CLI client refactoring

## AC Context

1. `SIDEQUEST_GENRE` set on Claude CLI subprocess with current genre name
2. `SIDEQUEST_CONTENT_PATH` set on Claude CLI subprocess with genre_packs_path
3. Tool section prompt text no longer includes `--genre` or `--genre-packs-path` flags
4. Tool sections are shorter (flag removal saves ~20 tokens per tool)
5. Wrapper scripts document env var requirements
6. `scripts/preview-prompt.py` updated
