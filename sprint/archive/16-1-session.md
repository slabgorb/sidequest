---
story_id: "16-1"
jira_key: "none"
epic: "16"
workflow: "kitchen-sink"
---
# Story 16-1: Narrator resource injection — serialize ResourcePool snapshots into narrator context so the LLM can reference Luck, Humanity, etc.

## Story Details
- **ID:** 16-1
- **Jira Key:** none (personal project)
- **Workflow:** kitchen-sink (phased: setup → analyze → plan → red → green → verify → review → accept → finish)
- **Epic:** 16 — Genre Mechanics Engine — Confrontations & Resource Pools
- **Repository:** sidequest-api (Rust backend)
- **Points:** 3
- **Priority:** p0
- **Status:** setup

## Context

Epic 16 establishes two missing generic subsystems: Confrontation (universal structured encounter engine) and ResourcePool (persistent named resources with spend/gain/threshold/decay).

Story 16-1 is the quick-win 80% fix: extract genre resource declarations from rules.yaml and inject their current values into the narrator's prompt context every turn. This gives the LLM immediate awareness of resources (Luck, Humanity, Heat, etc.) without building the formal ResourcePool struct yet.

The LLM cannot forget what it's told every turn — serializing resources directly into the prompt context achieves the core goal with zero wiring changes to the game engine itself.

**Dependency chain:**
- 16-1 (Narrator resource injection) ← current
  - 16-2 (Confrontation trait + ConfrontationState)
  - 16-3 (Confrontation YAML schema)
  - etc.

## What This Story Does

**Narrator resource injection** parses resource declarations from genre YAML rules files and serializes their current values into the narrator's prompt context before every turn.

### Current State
- `NarratorContext` (narrator.rs) already has injection points for game state
- `PromptFramework` exists and is used by `NarrationPipeline` to assemble prompts
- Genre loaders parse YAML (sidequest-genre crate)
- No formal ResourcePool struct yet (future, in 16-10)

### What Needs to Happen
1. **Extract resource declarations:** Parse `rules.yaml` for a `resources:` section listing resource names and metadata
2. **Read current values:** Look up current resource state in `GameSnapshot` (naive: hardcoded values, or from a temporary storage mechanism)
3. **Serialize to context:** Add a serialized block like:

```
[Resource State]
Luck: 4 / 6 (voluntary)
Humanity: 72 / 100 (involuntary)
Heat: 2 / 5 (decay 0.1/turn, involuntary)
```

4. **Inject into prompt:** Pass this block to the existing `NarratorContext` and `PromptFramework` injection points
5. **Test end-to-end:** Verify the narrator receives resource state in its prompt for all genres that declare resources

### Implementation Strategy
- **No ResourcePool struct yet** — just read genre rules and current state separately
- **Inject before narration** — pass resources as part of game state context
- **Schema-light:** Start with simple `resources:` list in rules.yaml; formalize in 16-10
- **Test via prompt inspection** — verify resource block appears in generated prompts

## Workflow Phases

| Phase | Owner | Input | Output | Status |
|-------|-------|-------|--------|--------|
| setup | sm | — | session_file, branch | in-progress |
| analyze | architect | session_file | requirements_review, reuse_opportunities, story_context | pending |
| plan | pm | requirements_review, reuse_opportunities, story_context | validated_requirements, story_context | pending |
| red | tea | validated_requirements, story_context | failing_tests | pending |
| green | dev | failing_tests | implementation, passing_tests | pending |
| verify | tea | implementation, passing_tests | quality_verified | pending |
| review | reviewer | implementation, passing_tests, quality_verified | code_approval | pending |
| accept | pm | code_approval, implementation | ac_approval | pending |
| finish | sm | ac_approval | archived_session | pending |

## Workflow Tracking
**Workflow:** kitchen-sink
**Phase:** setup
**Phase Started:** 2026-03-31T10:24Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-31T10:24Z | — | — |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations yet.
