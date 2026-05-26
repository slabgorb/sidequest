# Changelog

All notable changes to this orchestrator repo are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Subrepos (`sidequest-server`, `sidequest-content`, `sidequest-daemon`, `sidequest-ui`)
keep their own CHANGELOGs; this file tracks orchestrator-side changes only.

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [1.3.0] - 2026-05-26

### Added
- JARGONFILE.md project glossary, linked from README and CLAUDE.md.
- Anthropic SDK migration ADR set (ADR-101/102) with Phase E acceptance
  report and parity tooling; ADR statuses flipped post-merge to make the
  SDK the default narrator backend.
- ADR-105 broadcast-layer perception firewall (completes ADR-104);
  ADR-106 runtime procedural Jaquaysed megadungeon (Sünden Deep);
  ADR-107 out-of-band aside channel; ADR-108 MP item attribution;
  ADR-109 persistent location descriptions; ADRs 110/111/112 narrator
  prompt token reduction; ADR-113 Intent Router mechanical-engagement
  spine; ADR-114 ablative HP substrate (supersedes 078); ADR-115 Postgres
  persistence substrate migration; ADR-116 confrontation requires an Other.
- Scene-harness fixture library Wave 1 (12 fixtures across combat tiers,
  genre coverage, social setups, merchant/veteran-drop scenes), with
  caverns fixtures retargeted from deprecated `caverns_sunden` to live
  `beneath_sunden` (stories 51-1/51-2/51-3) and a hydration validation sweep.
- Beneath Sünden design corpus: ADR-106 plus Plans 1–8 (maze-maker port,
  region graph, depth score, theme palette, set-piece/trope-at-attach,
  session integration, world authoring), content cookbook, and
  caverns_sunden retirement.
- New cross-repo scripts: `r2_sync_packs --files` scoped uploads, labeled
  contact-sheet generator for asset review, and org Usage/Cost
  reconciliation via the Admin API.
- justfile recipes: `pg-up`/`pg-status` (Postgres substrate),
  `content-validate`/`content-validate-all`, `reference-validate-all`,
  `reference-chrome-validate`, `client-typecheck` (tsc -b) and
  `daemon-test` added to `check-all`.
- Seed-trope engine (Epic 22): schema + deck engine, content for
  tea_and_murder, narrator injection, OTEL routing (SPAN_SEED_FIRED),
  engagement-triggered seed draws.
- Epic 24 world-grounding: JSON Schemas for 7 systems, weather/demographics/
  calendar generators and CLIs, narrator grounding tool call, glenross and
  spaghetti_western calendars, bootstrap loader + ToolContext wiring.
- PRD additions: §12 Competitive Landscape & Differentiation, creator
  authoring & monetization brief; reference-pages v1/v2 specs and plans;
  save-forensics post-mortem page spec/plan; durable telemetry substrate
  (forensics Phases 1–2) specs/plans.
- Genre-pack filesystem schema spec + implementation plan; SWN-crunch
  ablative-HP design spec and gear-pharmacopeia plan.

### Changed
- ADR-115 reframed/amended to a direct Postgres port (Postgres ≠ cloud;
  deployment is a separate axis), reversing the phased strangler.
- Epic 59 reframed to the Intent Router mechanical-engagement spine.
- Promoted road_warrior, spaghetti_western, neon_dystopia, pulp_noir, and
  re-promoted heavy_metal to live; CLAUDE.md/README live pack count updated
  to 10 with corrected pack lists.
- victoria genre pack renamed to tea_and_murder across operational refs.
- Subrepo branch_strategy aligned to gitflow (corrected from
  github-flow/trunk-based); dropped stale Flux reference.
- Persistent log directory with rotation and 30-day retention; `just up`
  routed through `_server-cmd`/`_client-cmd`, defaulted to OTLP export +
  watcher-as-spans, with a machine-global singleton lock and resolved
  ANTHROPIC_API_KEY.
- Top-level docs refreshed for the post-port pack list, ADR index, and
  Anthropic-SDK transport reality; ADR-067 amended for the intent-validator
  inference site.

### Fixed
- 63-13 location validator reports malformed YAML instead of crashing;
  64-4 schema-validates pack file contents.
- Renderer honors explicit POI slug instead of re-slugifying the name.
- close_store partial-teardown reconnect crash wired (61-followup-C).
- Playtest preflight cost guard / cache-aware projection and hard-cap
  oversized-canary guards (Epic 61) to curb narrator cache-write runaway.
- ANTHROPIC_API_KEY provisioned in `just server`/`serve` recipes.

### Removed
- Deprecated `caverns_sunden` retired/superseded by `beneath_sunden`;
  caverns_sunden-coupled scenario fixtures and stale screenshot/migration
  tests removed.
- Dead code dropped: redundant second dispatch-bank run (59-11),
  NpcRegistryEntry (45-52), EncounterTag deprecation alias (45-46),
  module-level run_narration_turn (49-5).

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
