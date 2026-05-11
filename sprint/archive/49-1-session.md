# Story 49-1: Recency-zone recent-narrative window in narrator prompt

---
story_id: "49-1"
jira_key: null
epic: "49"
workflow: "tdd"
repos: ["sidequest-server"]
---

## Story Details

- **ID:** 49-1
- **Epic:** 49 — Playtest 4 Closeout — Glenross / ADR-098 Continuity Recovery
- **Jira Key:** (none — SideQuest does not use Jira)
- **Workflow:** tdd (phased: setup → red → green → spec-check → verify → review → spec-reconcile → finish)
- **Points:** 5
- **Priority:** p1
- **Assigned to:** slabgorb
- **Repository:** sidequest-server
- **Branch:** feat/49-1-recency-zone-narrative-window
- **Stack Parent:** none (independent story)

## Root Cause & Problem Statement

During the 2026-05-11 Glenross playtest, ADR-098 (stateless narrator turns with dropped --resume flag) delivered the predicted speed win (14-20s per turn instead of 60s+) but introduced narrative continuity regressions:

1. **Father→Mother gender flip:** Turn 5 prose named a male patient ("Father"); turn 6 invented a female "mother/her" with no state constraint
2. **Secateurs set down twice:** Prose-only fact (secateurs on blotter) was forgotten between turns
3. **Recent narrative facts drop:** The narrator loses prior-turn details because narrative_log lives in a JSON dump mid-prompt (Valley zone), far from high-attention areas

**Root cause:** The narrative_log is serialized inside the game_state JSON blob (orchestrator.py:1310, via snapshot.model_dump_json at session_helpers.py:308). This puts conversational history in an attention-decayed zone. Pre-098 the --resume flag kept the whole Claude conversation hot. Post-098 there is no high-attention recent-narration block; the narrator has to dig prior turns out of JSON far above player_action.

## Acceptance Criteria

- [ ] Add `register_section` call in orchestrator.py registering a `recent_narrative_context` section in `AttentionZone.Recency` (alongside player_action, npc_intro_visual_constraint, confrontation_trigger_constraint)
- [ ] Section content is the last K narrative_log entries (default K=4: two player turns + two narrator turns), rendered as readable prose blocks (NOT JSON), labeled by author/round prefix
- [ ] Drop narrative_log from the snapshot dump that feeds `<game_state>` (or cap at 1 entry) so the same data does not ride twice — once high-attention, once decayed
- [ ] **OTEL:** emit `recent_narrative_context_injected` span with turn count and total tokens
- [ ] **Regression test:** stub save fixture mirroring the gender-flip scenario (turn 5 prose names a male patient; turn 6 must not invent a female one)
- [ ] **Replay against ~/.sidequest/saves/games/2026-05-11-glenross/save.db:** narrator on turn 6 references Father/him consistently with turn 5 prose

## Workflow Tracking

**Workflow:** tdd (phased)
**Phase:** setup
**Phase Started:** 2026-05-11T21:27:25Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-11T21:27:25Z | — | — |

## Delivery Findings

No upstream findings at this stage.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

No deviations at this stage. Deviations will be logged as they are discovered during implementation.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Implementation Notes

- The narrative_log is currently serialized at orchestrator.py:1310 and fed to the prompt via session_helpers.py:308
- The Recency section should be registered alongside player_action and other constraints
- OTEL span should track both the count of injected entries and their cumulative token count
- The gender-flip regression test will require a fixtures with male-gendered prose in turn 5 and strict assertions on turn 6 narration
- Real playtest save is at ~/.sidequest/saves/games/2026-05-11-glenross/save.db for end-to-end verification
