---
story_id: "16-11"
jira_key: "none"
epic: "16"
workflow: "tdd"
branch: "feat/16-11-resource-threshold-knownfact"
repos:
  - sidequest-api
points: 3
priority: p1
---

# Story 16-11: Resource threshold → KnownFact pipeline — permanent narrator memory

## Goal
When a ResourcePool crosses a threshold, mint a LoreFragment in LoreStore with the
threshold's event_id and narrator_hint. High relevance ensures it surfaces in every
future narrator prompt via existing budget-aware selection.

## Acceptance Criteria
1. apply_resource_patch crossing → LoreFragment minted in LoreStore
2. LoreFragment has threshold's event_id and narrator_hint
3. High relevance score (surfaces in every narrator prompt)
4. apply_pool_decay crossings also mint LoreFragments
5. No duplicate LoreFragments for already-crossed thresholds
6. Multiple thresholds in one patch → multiple LoreFragments
7. Integration: appears in narrator context selection
