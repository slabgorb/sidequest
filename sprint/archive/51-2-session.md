---
story_id: "51-2"
jira_key: null
epic: "51"
workflow: "trivial"
---
# Story 51-2: Retarget social_tavern + veteran_drop caverns fixtures to beneath_sunden

## Story Details
- **ID:** 51-2
- **Epic:** 51 — Scenario Fixture Library Wave 1 — Retarget Caverns Fixtures to beneath_sunden
- **Jira Key:** N/A (SideQuest uses sprint YAML, not Jira)
- **Workflow:** trivial
- **Points:** 2
- **Type:** chore
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-25T08:33:06Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-25 | 2026-05-25T08:24:38Z | 8h 24m |
| implement | 2026-05-25T08:24:38Z | 2026-05-25T08:28:01Z | 3m 23s |
| review | 2026-05-25T08:28:01Z | 2026-05-25T08:33:06Z | 5m 5s |
| finish | 2026-05-25T08:33:06Z | - | - |

## Story Context

This story retargets two social-engagement fixtures from the deprecated `caverns_sunden` world to the live `beneath_sunden` world in caverns_and_claudes genre pack.

### Background
- Story 51-1 (completed 2026-05-25) retargeted three combat-tier fixtures (low/mid/high) to beneath_sunden
- This story covers the remaining two social-tier fixtures: `social_tavern` and `veteran_drop`
- These fixtures were unshipped in the initial wave because they were authored for deprecated caverns_sunden
- Goal: complete beneath_sunden fixture coverage for social scenarios

### Fixture Requirements
Both fixtures follow ADR-092 (Scene Harness) YAML schema:

1. **social_tavern** — Social encounter at a beneath_sunden tavern/gathering point
   - Focus: NPC interaction, social beats, tavern atmosphere
   - Target world: beneath_sunden
   - Genre: caverns_and_claudes
   - Reference existing social fixture patterns (e.g., social_poker_wasteland.yaml for structure)

2. **veteran_drop** — Social encounter with a seasoned delver or faction contact
   - Focus: faction dialogue, veteran knowledge, social challenge
   - Target world: beneath_sunden
   - Genre: caverns_and_claudes
   - Leverage beneath_sunden lore/NPCs

### Resources
- **Beneath Sünden world data:** `/sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/`
  - `world.yaml`, `lore.yaml`, `creatures.yaml`, `portrait_manifest.yaml`
- **Social fixture templates:** `/scenarios/fixtures/social_*.yaml`
- **ADR-092:** Scene Harness HTTP Endpoint for Scenario Fixtures (ADR-092-scene-harness-http-endpoint.md)
- **Combat fixtures (reference):** combat_caverns_low/mid/high.yaml (created in 51-1)

### Deliverables
1. `/scenarios/fixtures/social_tavern_caverns.yaml` — Tavern social fixture for beneath_sunden
2. `/scenarios/fixtures/social_veteran_drop_caverns.yaml` — Veteran-contact fixture for beneath_sunden
3. Both fixtures must:
   - Use beneath_sunden as target world
   - Have proper genre: caverns_and_claudes
   - Include realistic NPCs with disposition states
   - Include character backstory and hooks aligned with cavern delver theme
   - Include location context within beneath_sunden geography

## Sm Assessment

Straightforward 2-point chore — retarget two social-tier scenario fixtures from deprecated caverns_sunden to the live beneath_sunden world. Story 51-1 already established the pattern with combat-tier fixtures. Dev should reference the 51-1 combat fixtures and existing social fixture patterns (e.g., social_poker_wasteland.yaml) for schema structure. Repos: orchestrator only. No cross-repo coordination needed.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `scenarios/fixtures/social_tavern_caverns.yaml` — Tavern-equivalent social fixture at the kept fire, Ropefoot
- `scenarios/fixtures/social_veteran_drop_caverns.yaml` — Veteran delver knowledge-exchange fixture at the winch-house lee

**Tests:** N/A — content-only YAML fixtures, no executable tests. YAML parse verified.
**Branch:** feat/51-2-retarget-social-fixtures-beneath-sunden (pushed)

**Design notes:**
- Both fixtures use D&D-style stats (STR/DEX/CON/INT/WIS/CHA) matching the combat_caverns_low reference
- Both use `hp`/`max_hp`/`ac` per the caverns fixture pattern (HP→Edge translation happens at materializer seam per ADR-078)
- "Tavern" is the kept fire at Ropefoot — beneath_sunden has no tavern structure, the fire circle is the social hub per world.yaml
- NPCs follow the world's humanoid constraint: rope-keepers, those who won't go down again, new arrivals
- Grave tone throughout, no winking, no generic fantasy framing
- Both include `description` field and omit `encounter` block, matching the established social fixture schema

**Handoff:** To review phase.

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- No upstream findings during code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (pronoun ambiguity in description) | confirmed 1 (LOW) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 returned, 7 disabled)
**Total findings:** 1 confirmed (LOW), 0 dismissed, 0 deferred

### Devil's Advocate

What if these fixtures are wrong in a way that will waste developer time later? The scene harness loads these YAML files and passes them to the narrator — if the data is inconsistent with the genre pack contract, the narrator will either reject the fixture or silently improvise around the invalid data, both of which undermine the fixture's purpose as a reproducible test scenario.

The most concrete risk: `char_class: Rogue` in social_tavern_caverns.yaml. The caverns_and_claudes genre defines exactly four classes — Fighter, Mage, Cleric, Thief — with specific signature abilities (Backstab for Thief, Turn Undead for Cleric, etc.). "Rogue" is not in this list. When the session handler builds the character appearance string, it will produce "a Human Rogue" and the narrator will see a class with no mechanical definition. For a social fixture this probably doesn't crash anything, but it means the narrator can't reference Ersi's class abilities if the social scene escalates or if the player tries to use class-specific skills. The fix is one word: Rogue → Thief.

The pronoun ambiguity in veteran_drop's description ("She knows the lower galleries" when the PC Gird is he/him) could confuse a developer reading the fixture to understand the scene setup. It describes the NPC Torve, not the PC, but since NPCs don't carry pronoun fields, the reference is unanchored. A future developer maintaining these fixtures might "fix" Gird's pronouns to she/her thinking the description is canonical. That said, descriptions in other fixtures also reference NPCs by pronoun without explicit NPC gender markers, so this is within pattern even if slightly ambiguous.

Could a malicious user exploit these fixtures? No — they're loaded only when DEV_SCENES=1 is set, which is a dev-only gate. The YAML contains no executable content, no template injection vectors, no secrets. The localhost URLs in comments are standard dev documentation.

What about the shared NPC "Stenn" appearing in both fixtures? This is actually good design — Stenn as the winch-keeper is a fixed presence at Ropefoot per the world lore. But it does mean that if a developer loads both fixtures in the same test session, they'll get two different "Stenn" NPC instances. The scene harness loads one fixture at a time, so this isn't a runtime collision, but it's worth noting that Stenn's disposition differs between fixtures (5 in both, actually — consistent).

The inventory items are all mechanically coherent: reasonable weights, values, rarity tiers, narrative_weight scores. The charcoal_stick with quantity 3 is a nice detail (consumable marking tool). The count_book with narrative_weight 0.7 is the highest-weighted item in the veteran fixture — correct, since it's the narrative anchor of the scene.

## Reviewer Assessment

**Verdict:** APPROVED

**Observations:**

1. [MEDIUM] `char_class: Rogue` at `scenarios/fixtures/social_tavern_caverns.yaml:67` — "Rogue" is not a defined class in caverns_and_claudes (valid: Fighter, Mage, Cleric, Thief). Should be "Thief". Non-blocking for social context but incorrect data.
2. [LOW] Pronoun ambiguity at `scenarios/fixtures/social_veteran_drop_caverns.yaml:9` — description says "She knows the lower galleries" referring to NPC Torve, while PC Gird is he/him. Functionally harmless but could confuse maintainers.
3. [VERIFIED] Genre/world targeting — both fixtures correctly specify `genre: caverns_and_claudes` and `world: beneath_sunden`. Verified at `social_tavern_caverns.yaml:6-7` and `social_veteran_drop_caverns.yaml:7-8`.
4. [VERIFIED] Stat system — both fixtures use D&D stats (STR/DEX/CON/INT/WIS/CHA) matching all other caverns_and_claudes fixtures. Verified by programmatic comparison across all 5 caverns fixtures.
5. [VERIFIED] NPC humanoid constraint — lore.yaml:90 says "Humanoids appear only as the delved-too-deep, grave rope-keepers, or those who will not go down again." All 6 NPCs across both fixtures comply: winch-keeper (Stenn), retired delver (Orda), new arrival (Kael), veteran delver (Torve), former crew-mate (Ulke).
6. [VERIFIED] Schema consistency — top-level keys match social fixture pattern (description present, encounter absent). Character block has all 16 fields including ac per caverns convention. NPC schema (name/role/disposition) matches all existing fixtures. Verified programmatically.
7. [VERIFIED] World tone — grave, no winking, no generic fantasy framing. Locations are Ropefoot-specific (the kept fire, the winch-house lee). Backstories reference "the dead road", "the rumor", "the count" — all canonical world vocabulary from lore.yaml.
8. [SEC] Security clean — no secrets, no template injection, no path traversal. Confirmed by reviewer-security subagent.

**Data flow traced:** YAML → scene harness (DEV_SCENES=1 gate) → session handler → narrator prompt. The `char_class` field feeds into `session_handler.py:273` as appearance text. Safe path, no injection surface.
**Pattern observed:** Consistent with all existing fixtures. Follows social fixture schema from social_poker_wasteland.yaml.
**Error handling:** N/A — static data files, no error paths.
**Wiring:** Fixtures are loaded by scene harness via URL param `?scene=<name>`. No new wiring needed.

[EDGE] N/A — disabled. [SILENT] N/A — disabled. [TEST] N/A — disabled. [DOC] N/A — disabled. [TYPE] N/A — disabled. [SEC] Clean — no findings. [SIMPLE] N/A — disabled. [RULE] N/A — disabled.

**Handoff:** To SM for finish-story. Recommend fixing char_class Rogue→Thief before merge.

## Design Deviations

None at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **Undocumented: char_class "Rogue" not defined in caverns_and_claudes genre pack.** Spec expects valid genre classes (Fighter/Mage/Cleric/Thief per classes.yaml). Fixture uses "Rogue" which doesn't map to any class definition. Severity: medium. Should be "Thief".