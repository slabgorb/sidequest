---
story_id: "23-1"
epic: "23"
workflow: "kitchen-sink"
---
# Story 23-1: Wire reworked narrator prompt — replace hardcoded narrator.rs with template sections

## Story Details
- **ID:** 23-1
- **Epic:** 23 — Narrator Prompt Architecture
- **Workflow:** kitchen-sink
- **Points:** 8
- **Repos:** api
- **Stack Parent:** none

## Context

Replace the hardcoded system prompt in narrator.rs and the inline section registration in orchestrator.rs:build_narrator_prompt() with the structured template from docs/prompt-reworked.md.

**Prompt architecture:**
- Identity goes to Primacy zone
- Four critical blocks go to Primacy
- Seven important blocks go to Early zone
- Output-style goes to Early
- Tool definitions (generation wrappers) go to Valley
- Player data, world lore, game state, tone stay in Valley/Late as today but use the new structure

**Bash wrappers:** scripts/sidequest-npc, sidequest-encounter, sidequest-loadout replace hardcoded tool paths.

**Environment variables:** SIDEQUEST_GENRE and SIDEQUEST_CONTENT_PATH set per-session.

## Workflow Tracking
**Workflow:** kitchen-sink
**Phase:** setup
**Phase Started:** 2026-04-03T09:23:46Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-03T09:23:46Z | - | - |

## Delivery Findings

No upstream findings at setup.

## Design Deviations

No deviations logged yet.
