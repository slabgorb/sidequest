# Changelog

All notable changes to this orchestrator repo are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Subrepos (`sidequest-server`, `sidequest-content`, `sidequest-daemon`, `sidequest-ui`)
keep their own CHANGELOGs; this file tracks orchestrator-side changes only.

## [Unreleased]

### Added
- Scene harness fixture library Wave 1 (12 fixtures): combat tier scaling
  (low/mid/high caverns), genre coverage (wasteland brawl, space dogfight,
  space boarding), social setups (tea drawing room, caverns tavern, tea
  negotiation, wasteland poker), merchant bazaar (wasteland), and a
  veteran-drop caverns scene. Replaces the four original fixtures
  (combat_test/dogfight/negotiation/poker), three of which targeted
  workshopping worlds. Spec: docs/superpowers/specs/2026-05-14-scenario-fixture-library-wave-1-design.md.
- Wave-1 caverns fixtures retargeted from deprecated `caverns_sunden` to
  live `beneath_sunden` world (stories 51-1, 51-2). All 5 caverns
  fixtures (combat_caverns_low/mid/high, social_tavern_caverns,
  social_veteran_drop_caverns) confirmed on `beneath_sunden`. Hydration
  sweep validated all 12 fixtures load cleanly with correct genre/world
  bindings (story 51-3).
- Filed 5 scene-harness hydrator extension stories (Wave 2): known_facts,
  scenario_state, StructuredEncounter, magic_state + abilities, multi-PC
  characters list. 18 pts total.

### Changed
- `just server` and `just up` default `DEV_SCENES=1` and set
  `SIDEQUEST_FIXTURES_DIR` to the orchestrator-root `scenarios/fixtures`,
  so `/dev/scene/{name}` is live without per-shell exports.

## [1.1.0] - 2026-05-11

### Added
- ADR-098 — stateless narrator turns (supersedes ADR-066) and accompanying
  spec/plan docs.
- Story 47-5 sprint scaffolding (sprint YAML, session file, four cut-points
  for Magic Phase 6 playgroup playtest).
- README + CLAUDE.md refresh covering the post-port pack list and ADR index.

### Changed
- ADR index regenerated; superseded/drift notes split into dedicated docs.
- API-contract handoff doc for ACTION_REVEAL wire shape.

## [1.0.0] - prior

Initial post-Rust-port orchestration baseline. Not formally tagged at the time;
recorded here for continuity.
