---
story_id: "51-1"
jira_key: "none"
epic: "51"
workflow: "trivial"
---
# Story 51-1: Retarget combat-tier caverns fixtures (low/mid/high) to beneath_sunden

## Story Details
- **ID:** 51-1
- **Epic:** 51 — Scenario Fixture Library Wave 1 — Retarget Caverns Fixtures to beneath_sunden
- **Jira Key:** none (SideQuest uses sprint YAML, not Jira)
- **Workflow:** trivial
- **Type:** chore
- **Points:** 3
- **Stack Parent:** none

## Context

This story is part of ADR-092 wave 1 fixture retargeting. The scene harness (sidequest-server/sidequest/handlers/scene_handler.py) loads scenario fixtures from yaml files in sidequest-content/scenarios/. Seven of twelve wave-1 fixtures targeted the deprecated caverns_sunden world (moved to genre_workshopping/ for salvage); five of those seven were combat-tier and need retargeting to the live beneath_sunden world.

The deprecated caverns_sunden was a three-sins prototype and has been superseded by the live beneath_sunden world. All fixture references must migrate from caverns_sunden to beneath_sunden slug.

**Fixtures to retarget (combat-tier, low/mid/high):**
- scenarios/combat_caverns_low.yaml (difficulty: low)
- scenarios/combat_caverns_mid.yaml (difficulty: mid)  
- scenarios/combat_caverns_high.yaml (difficulty: high)
- (Plus two more social fixtures in story 51-2)

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-25T08:13:34Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-25T00:00:00Z | 2026-05-25T08:00:56Z | 8h |
| implement | 2026-05-25T08:00:56Z | 2026-05-25T08:08:00Z | 7m 4s |
| review | 2026-05-25T08:08:00Z | 2026-05-25T08:13:34Z | 5m 34s |
| finish | 2026-05-25T08:13:34Z | - | - |

## Delivery Findings

No upstream findings.

## Sm Assessment

Story 51-1 is a straightforward retargeting of three combat-tier scenario fixture YAMLs from the deprecated `caverns_sunden` world to the live `beneath_sunden` world. Trivial workflow is appropriate — this is a content migration, not a design problem.

**Repos:** content (fixture YAML), server (scene harness may reference world slug in tests)
**Branches:** `feat/51-1-retarget-combat-caverns-fixtures` in both sidequest-content and sidequest-server
**Risk:** Low. Fixture YAML is declarative; the scene harness loads by slug. Main work is updating world references and ensuring creature/location references valid for beneath_sunden.

**Routing:** → Dev (Ponder Stibbons) for implement phase.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `scenarios/fixtures/combat_caverns_low.yaml` — Low-difficulty fixture: L1 Fighter vs Wight in a collapsed guard post, second level
- `scenarios/fixtures/combat_caverns_mid.yaml` — Mid-difficulty fixture: L3 Cleric vs Otyugh in a flooded sump, fourth level
- `scenarios/fixtures/combat_caverns_high.yaml` — High-difficulty fixture: L5 Thief vs Vampire in a scored crypt, eighth level

**Tests:** 125/125 passing (GREEN) — scene harness hydrator + HTTP endpoint tests
**Branch:** feat/51-1-retarget-combat-caverns-fixtures (orchestrator)

**Handoff:** To review phase

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 — canonical parametrize gap | confirmed 1 (MEDIUM, deferred to 51-3) |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 returned, 7 disabled via settings)
**Total findings:** 1 confirmed (MEDIUM, deferred to 51-3), 0 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] All 18 item IDs across 3 fixtures match `caverns_and_claudes/inventory.yaml` — cross-checked: sword_short, shield_wood, torch, rope_hemp, hammer_war, leather_armor, holy_symbol, potion_healing, dagger_iron, lantern, lantern_oil, lockpicks. Evidence: `grep '^  - id:' inventory.yaml` lists all 29 catalog items; every fixture `id:` field is in that set.
2. [VERIFIED] Stat names (STR/DEX/CON/INT/WIS/CHA) match `rules.yaml:33-39` ability_score_names. All three fixtures use exactly these 6 names.
3. [VERIFIED] Classes (Fighter, Cleric, Thief) all in `rules.yaml:9-13` allowed_classes; race "Human" matches `rules.yaml:14-15` allowed_races. No rules violation.
4. [VERIFIED] genre slug `caverns_and_claudes` and world slug `beneath_sunden` match live content at `genre_packs/caverns_and_claudes/worlds/beneath_sunden/world.yaml:20`.
5. [VERIFIED] Creature threat-to-difficulty scaling: Wight (threat 3) → low; Otyugh (threat 4) → mid; Vampire (threat 5) → high. Appropriate escalation per `creatures.yaml` threat_level bands.
6. [VERIFIED] hp/max_hp → EdgePool mapping via `scene_harness.py:307-310`; ac silently dropped per hydrator comment `:285`. Both match all 7 existing canonical fixtures.
7. [VERIFIED] Genre truth — prose matches beneath_sunden tone contract (`world.yaml:35`: "Grave, lethal, Moria-as-tragedy. No winking."). Evidence: "the count of names on the board at Ropefoot", "scored through from the inside" — in register.
8. [MEDIUM] [PREFLIGHT] New fixtures not in canonical parametrize lists at `test_scene_harness_hydrator.py:91-96` and `test_scene_harness.py:276-281`. Pre-existing gap (6 of 10 fixtures absent). Story 51-3 scoped for sweep.
9. [VERIFIED] Structural consistency — all three use identical field sets to existing fixtures (name, genre, world, player_name, location, turn, character, npcs, encounter).
10. [SEC] Security clean — no YAML injection, no prompt-injection payloads, no hardcoded secrets. `yaml.safe_load` + regex guard in hydrator. Content is in-world prose only.

### Rule Compliance

- "No Silent Fallbacks" — N/A: pure YAML, no fallback logic. Compliant.
- "No Stubbing" — Complete fixtures, not stubs. Compliant.
- "Every Test Suite Needs a Wiring Test" — MEDIUM gap: new fixtures not individually named in wiring tests. Pre-existing (6/10 missing). Deferred to 51-3.
- "Genre Truth" (SOUL.md) — Compliant. Prose matches beneath_sunden grave register.
- "Diamonds and Coal" (SOUL.md) — Hooks are specific and earned (scored wards, water against current, jammed door). Not overbaited.

### Devil's Advocate

What if creature names ("Wight", "Otyugh", "Vampire") need to match creatures.yaml entries for the narrator to ground them? No — the hydrator creates Npc objects with free-text names; narrator receives them as snapshot.npcs. Existing fixtures use the same pattern ("Rust Jaw", "Hostile Crewer A"). The creatures.yaml bestiary is for image generation and world-register gating, not runtime NPC lookup.

Are the stat totals balanced? L1 Fighter: 67 pts. L3 Cleric: 74. L5 Thief: 73. B/X 3d6-strict (rules.yaml:1) averages 63. Slightly above average makes sense for combat test fixtures — below-average characters would die before exercising the encounter system. Not a balance concern for dev fixtures.

Could location names conflict with the procedural dungeon engine (ADR-106)? No — current_region is free-text label, not a room-graph node. The procedural engine generates dynamically; fixtures pre-seed a snapshot that bypasses normal session flow. No conflict.

What if DEV_SCENES=1 leaks to production? Same risk model as all 10 fixtures — router only constructed at startup when flag set. Not a new concern.

Could the duplicate "## Delivery Findings" headings in this session file confuse downstream tooling? Possible — the Dev section added a second heading at line 69. However, session files are consumed by humans and the finish script, not by section-deduplicating parsers. Low risk.

### Data Flow

Fixture YAML → `yaml.safe_load` → field extraction → `_hydrate_character` → Character + CreatureCore (EdgePool from hp/max_hp) → `GameSnapshot(**kwargs)` → SQLite via SqliteStore. Safe: safe_load prevents deserialization attacks; regex + resolve guard prevents path traversal; pydantic catches malformed fields.

[EDGE] N/A (disabled) | [SILENT] N/A (disabled) | [TEST] N/A (disabled) | [DOC] N/A (disabled) | [TYPE] N/A (disabled) | [SEC] Clean | [SIMPLE] N/A (disabled) | [RULE] No violations; MEDIUM wiring gap deferred to 51-3

**Handoff:** To Captain Carrot for finish-story

## Delivery Findings

### Reviewer (code review)
- **Gap** (non-blocking): Canonical fixture parametrize lists at `sidequest-server/tests/game/test_scene_harness_hydrator.py:91-96` and `sidequest-server/tests/server/test_scene_harness.py:276-281` cover only 4 of now-10 fixtures. Story 51-3 is scoped for the 12-fixture hydration sweep.
  Affects `sidequest-server/tests/` (add new slugs to parametrize lists).
  *Found by Reviewer during code review.*

### Dev (implementation)
- **Gap** (non-blocking): SM setup created feature branches in sidequest-content and sidequest-server, but the epic repos field is "orchestrator" — fixtures live at `scenarios/fixtures/` in the orchestrator repo. The content/server branches are unused dead branches that should be cleaned up.
  Affects `.session/51-1-session.md` (repos field says content,server; should say orchestrator).
  *Found by Dev during implementation.*

## Design Deviations

### Dev (implementation)
- **Repos mismatch — worked in orchestrator, not content/server**
  - Spec source: .session/51-1-session.md, Context section
  - Spec text: "Repos: content (fixture YAML), server (scene harness may reference world slug in tests)"
  - Implementation: All three fixtures authored in orchestrator's scenarios/fixtures/ directory, no content or server changes needed
  - Rationale: Epic 51 repos field is "orchestrator"; fixtures have always lived in orc-quest/scenarios/fixtures/; the scene harness in server reads from the orchestrator path at runtime via SIDEQUEST config
  - Severity: minor
  - Forward impact: none — the SM-created content/server branches are empty and can be deleted
  - → ✓ ACCEPTED by Reviewer: Epic YAML says "orchestrator", all 7 existing fixtures live in scenarios/fixtures/. Dev followed the established pattern. SM setup was wrong about repos.

### Reviewer (audit)
- No undocumented deviations found.