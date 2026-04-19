---
story_id: "37-8"
jira_key: ""
epic: "37"
workflow: "trivial"
---
# Story 37-8: World materialization fails for dust_and_lead — null history chapters in spaghetti_western world YAML

## Sm Assessment

**Routing decision:** Trivial workflow → dev for implement phase. 1-point content-only fix — null NPC names in spaghetti_western world YAML.

## Story Details
- **ID:** 37-8
- **Jira Key:** (none — personal project)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-12T19:50:13Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-12 | 2026-04-12T19:43:32Z | 19h 43m |
| implement | 2026-04-12T19:43:32Z | 2026-04-12T19:46:52Z | 3m 20s |
| review | 2026-04-12T19:46:52Z | 2026-04-12T19:50:13Z | 3m 21s |
| finish | 2026-04-12T19:50:13Z | - | - |

## Context

**Epic:** 37 — Playtest 2 Fixes — Multi-Session Isolation (p0)

**Issue:** The dust_and_lead world YAML has null NPC names in the history chapters, which causes world materialization to fail. NPCs with `name: null` are skipped during deserialization (serde default), leaving the world context incomplete.

**Scope:** Content fix in sidequest-content/genre_packs/spaghetti_western/worlds/dust_and_lead/history.yaml
- Fix all 4 chapters (fresh, early, mid, veteran)
- Replace `name: null` with proper NPC names or remove the entries
- Verify no other world YAMLs have the same issue

**Root Cause:** NPCs are defined with archetype references but missing names. The parser expects either a populated name field or an absent field (for optional). The null value deserializes to empty string, which triggers an early return in apply_npc(), silently dropping the NPC.

**Fix Strategy:**
1. Read each chapter's NPC entries
2. For each NPC with `name: null`, determine the correct name based on archetype + context
3. Replace null with the proper name
4. Cross-check other genre pack worlds for the same pattern

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `genre_packs/spaghetti_western/worlds/dust_and_lead/history.yaml` — Populated all 12 null NPC names across 4 history chapters

**Tests:** N/A (content-only, no code tests)
**Branch:** feat/37-8-world-materialization-dust-and-lead (pushed)

**Handoff:** To review phase.

## Delivery Findings

- **Gap** (non-blocking): Same `name: null` pattern exists in neon_dystopia/franchise_nations (9 nulls) and pulp_noir/annees_folles (10 nulls). Affects `genre_packs/neon_dystopia/worlds/franchise_nations/history.yaml` and `genre_packs/pulp_noir/worlds/annees_folles/history.yaml` (need same fix). *Found by Dev during implementation.*

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 7 | confirmed 1, dismissed 6 |
| 3 | reviewer-silent-failure-hunter | N/A | skipped | N/A | YAML content fix — no code |
| 4 | reviewer-test-analyzer | N/A | skipped | N/A | YAML content fix — no tests |
| 5 | reviewer-comment-analyzer | N/A | skipped | N/A | YAML content fix — no comments |
| 6 | reviewer-type-design | N/A | skipped | N/A | YAML content fix — no types |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 | dismissed 1 |

**All received:** Yes (3 returned, 4 N/A for content fix, 2 disabled)
**Total findings:** 1 confirmed (low), 7 dismissed

**Dismissed findings:**
- [RULE] "The Stranger" as stub: Dismissed — genre-intentional. "The Man With No Name" is the defining Spaghetti Western archetype (Dollars trilogy). Giving this NPC a regular name would break the genre reference. The NPC is deliberately unnamed; "The Stranger" is the closest a name field can get while respecting the trope.
- [EDGE] Capitán Fierro vs Capitán Cuervo lore mismatch: Dismissed — "Capitán Cuervo" was always a faction alias, not a personal name. "Emilio Fierro" is the character's real name. Lore consistency is a separate content pass, not this story's scope.
- [EDGE] Corrupt Sheriff archetype vs Deputy role: Dismissed — pre-existing archetype, not introduced by this diff.
- [EDGE] Solomon Cole dual-archetype: Dismissed — intentional recurring antagonist with escalating role (Hired Gun → Bounty Collector). Engine handles chapter progression.
- [EDGE] Captain Stone vs Captain Abel Stone: Dismissed — abbreviation, not a conflict. The engine matches by name field; narrator can use either form.
- [EDGE] Names not in corpus files: Dismissed — hardcoded narrative NPCs are exempt from corpus validation. Corpus is for procedural generation, not hand-authored world characters.
- [EDGE] Father Mateo title not in culture patterns: Dismissed — low confidence, clerical titles are a natural exception to culture patterns.

**Confirmed finding (LOW):**
- [EDGE] "The Stranger" could collide with the player-character label in narrator text. NPC registry matches by exact name field, not substring, so this is unlikely to cause mechanical issues. Noted for awareness but not blocking.

## Reviewer Assessment

**Verdict:** APPROVED

1. ✅ [EDGE] All 12 null NPC names populated with genre-appropriate names
2. ✅ [RULE] No stubs — all names are proper identities (including genre-intentional "The Stranger")
3. ✅ [SILENT] N/A — YAML content fix, no code fallback paths
4. ✅ [TEST] N/A — content repo, no test suite
5. ✅ [DOC] Notes fields properly deduplicated after name extraction
6. ✅ [TYPE] N/A — YAML content fix, no type design

**Data flow traced:** history.yaml → serde deserialize → SharedGameSession.npc_registry → narrator prompt context. With null names, NPCs were silently dropped. With proper names, materialization completes.

**Delivery finding acknowledged:** neon_dystopia/franchise_nations and pulp_noir/annees_folles have the same `name: null` pattern — follow-up work.

**Handoff:** To SM for finish.

## Design Deviations

### Dev (implementation)
- No deviations from spec.