# Epic 24: Procedural World-Grounding Systems

## Vision

Anti-mode-collapse infrastructure for the narrator. Procedural generators inject
structured, varied, mechanically-consistent context into narrator prompt zones —
shifting the narrator from **invention** (where it repeats itself) to **curation**
(where it excels).

## Architecture

Follows the Monster Manual pattern (ADR-059):
1. YAML content defines rules/baselines in genre packs
2. Rust generators (or direct YAML injection) produce structured state
3. State injected into narrator prompt zones via dispatch pipeline
4. Narrator selects from proposed state, system reconciles
5. OTEL verifies proposed vs used

**Existing infrastructure to build on:**
- `sidequest-genre` — reads arbitrary YAML from genre packs
- `sidequest-namegen` / `encountergen` / `loadoutgen` — tool binary templates
- `dispatch/mod.rs` (lines 385-405) — prompt zone assembly
- `monster_manual.rs` — persistent pool + lifecycle pattern
- `markov.rs` — culture-appropriate name generation
- `docs/prompt-reworked.md` — narrator prompt template with attention zones
- `scripts/preview-prompt.py` — rapid prompt iteration (primary testing tool)

## Systems (9 total, Phase 1 = first 3)

| # | System | Type | Priority |
|---|--------|------|----------|
| 1 | Weather | On tick | Tier 1 — Phase 1 |
| 2 | Demographics | Baked | Tier 1 — Phase 1 |
| 3 | Calendar | Baked | Tier 1 — Phase 1 |
| 4 | Economy / Trade | Baked + tick | Tier 2 — Phase 2 |
| 5 | Establishments | Baked + tick | Tier 2 — Phase 2 |
| 6 | NPC Schedules | On tick | Tier 2 — Phase 2 |
| 7 | Quest Shapes | Baked | Tier 3 — Phase 3 |
| 8 | Interior Topology | On tick | Tier 3 — Phase 3 |
| 9 | World Maps | Baked (tool) | Tier 3 — Phase 3 |

## Phase 1 Stories (this sprint)

| Story | Points | Type | Repos |
|-------|--------|------|-------|
| 24-1: Define YAML schemas (all 9 systems) | 3 | chore | content, orchestrator |
| 24-2: low_fantasy weather rules | 2 | feature | content |
| 24-3: pinwheel_coast demographics | 2 | feature | content |
| 24-4: pinwheel_coast calendar | 2 | feature | content |
| 24-5: Rust weather generator | 3 | feature | api |
| 24-6: Prompt zone injection | 3 | feature | api |
| 24-7: OTEL spans | 2 | feature | api |
| 24-8: Playtest validation | 2 | chore | orchestrator |
| **Total** | **19** | | |

## Testing Strategy

1. **Prompt preview loop** (`scripts/preview-prompt.py`) — primary iteration tool.
   Author YAML → wire into prompt zone → preview → iterate. No full playtest needed
   until prompt injection is verified.
2. **Scripted scenarios** — run same scenario 5+ times, compare narrator variety
3. **OTEL dashboard** — proposed vs used delta visible in GM panel

## Key Decisions

- **low_fantasy first** — validate schemas before 7-genre rollout
- **Weather is the proof** — cheapest on-tick system, most visible narrator improvement
- **Demographics are baked** — no runtime generation, just YAML in prompt zone
- **Calendar grounds time** — "dawn on Restday in Thawmelt" vs "it's morning"

## PRD Reference

Full PRD at `docs/prd-procedural-world-grounding.md`
Research at `docs/research/procedural-tools-survey.md`
Design lineage at `docs/research/procedural-generation-lineage.md`
