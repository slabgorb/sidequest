---
story_id: "90-3"
jira_key: ""
epic: "90"
workflow: "tdd"
---
# Story 90-3: AC5b live free-play OTEL proof — a fight-seeker reaches WWN combat (wwn.* + ablative HP) and a caster fires wwn.spell.cast from a world opening, lie-detector quiet, across heavy_metal evropi + long_foundry + barsoom (epic 89); depends on 90-1 statted enemies + 90-2 magic_state

## Story Details
- **ID:** 90-3
- **Jira Key:** none (personal project, sprint YAML authoritative)
- **Workflow:** tdd
- **Stack Parent:** 90-1 (completed upstream)

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-10T21:07:40Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T21:07:40Z | - | - |
| red | - | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

- **Upstream ready (90-1, 90-2):** 90-1 (encountergen ruleset-awareness) completed 2026-06-05, approved. 90-2 (magic_state instantiation) completed 2026-06-06, approved. Both merged to develop and verified in the epic description.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Story Branches

**Repos:** sidequest-content, sidequest-server
**Branch Strategy:** gitflow (feat/90-3-wwn-live-otel-proof on both)

- **sidequest-content:** feat/90-3-wwn-live-otel-proof (targeting develop)
- **sidequest-server:** feat/90-3-wwn-live-otel-proof (targeting develop)

## Architect Decision (magic-path consult, 2026-06-10)

**Decision:** WN ruleset-module worlds (incl. heavy_metal/WWN) own magic via
`core.spellcasting`/`core.effort` → `wwn.spell.cast`, NOT the ADR-126
`magic_init`/`magic_state`/`WorldMagicConfig` plugin framework. The magic_init
AND-gate and `magic_state: null` are OFF the AC5b path — do not relax the gate or
reconcile `long_foundry/magic.yaml`'s schema. That 78KB file is orphaned draft content.
Verified: `wwn.py:466 resolve_spellcast` reads `caster_core.spellcasting` (`:499`);
`grep magic_state game/ruleset/*.py` is empty. AC5b spellcast spine = WN cast spine,
already done in epic 102 (102-1/2/3/4).

Decision doc: `sidequest-server/docs/superpowers/specs/2026-06-10-wn-worlds-own-magic-not-magic_state.md`

**Real remaining AC5b gaps (NOT magic_init):**
1. Combat reachability — fight-seeker must reach a WWN combat (evropi free-play: 11 turns, `active_confrontation: None`). Lane: content / headed proof.
2. Caster statting — headless `strategy: auto` chargen ignores scenario `class:` → non-caster (empty spellcasting). Lane: orchestrator tooling (`scripts/playtest.py`) or headed proof.
3. Live re-verify the epic-102 spine fires (`wwn.spell.cast`, `wwn.*` combat + ablative HP, `{ruleset}.mortal_injury/.shock`).

**Content/observability hygiene (separate):** quarantine/retire `long_foundry/magic.yaml`; optional `magic.ruleset_owned` bind signal for WN packs.
