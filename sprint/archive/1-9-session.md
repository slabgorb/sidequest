---
story_id: "1-9"
jira_key: "none"
epic: "1"
workflow: "tdd"
---
# Story 1-9: Prompt framework — PromptSection, attention zones, rule taxonomy, SOUL.md parser

## Story Details
- **ID:** 1-9
- **Epic:** 1 (Rust Workspace Scaffolding)
- **Jira Key:** none (personal project, no Jira integration)
- **Workflow:** tdd
- **Type:** feature
- **Points:** 5
- **Priority:** p1
- **Stack Parent:** 1-2 (done — Protocol crate)

## Story Summary

Build the prompt composition framework that powers Claude CLI subprocess calls. This is a critical component informed by the Python SideQuest's proven attention-zone prompt composer. The framework handles:

1. **PromptSection** — Ordered text blocks with optional context metadata
2. **Attention zones** — Primacy, early, valley, late, recency ordering (from ADR-009)
3. **Rule taxonomy** — Game rules structured for reliable Claude behavior
4. **SOUL.md parser** — Load runtime agent guidelines from disk

This story is independent of game logic (1-3 through 1-8) but a prerequisite for agent infrastructure (1-10).

### Key Responsibilities

- [ ] `PromptSection` struct with content, importance weight, and optional context
- [ ] `AttentionZone` enum (Primacy, Early, Valley, Late, Recency) with ordering logic
- [ ] `RuleSection` enum for game rules: Core, Combat, Chase, Narrative, Custom
- [ ] `SoulData` struct to load SOUL.md files from disk with parsing
- [ ] `PromptComposer` trait for implementing composition strategies
- [ ] Full serde derives for all public types
- [ ] Comprehensive tests for zone ordering and SOUL.md parsing

### Deliverables

**New module:** `crates/sidequest-agents/src/prompt_framework/`

**Structs:**
- `PromptSection` — public, serde(deny_unknown_fields)
- `AttentionZone` — public enum
- `RuleSection` — public enum
- `SoulData` — public, loaded from YAML/Markdown
- `PromptComposer` — public trait

**Tests:**
- Attention zone ordering (verify primacy > early > late > recency)
- SOUL.md parsing roundtrip (load, serialize, verify field preservation)
- PromptSection importance weighting
- RuleSection coverage (all 5 variants)

### Dependencies

- `sidequest-protocol` — GameMessage types for context
- `serde` / `serde_yaml` — parsing and serialization
- `uuid` — for internal IDs (optional)

### Python Reference

See `sq-2/agents/prompt_composer.py` (PromptComposer, _build_attention_zones, _compose_sections) and `sq-2/SOUL.md` (runtime agent guidelines as YAML/Markdown hybrid).

## Workflow Tracking
**Workflow:** tdd
**Phase:** green
**Phase Started:** 2026-03-25

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-25 | 2026-03-25 | <1m |
| red | 2026-03-25 | 2026-03-25 | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Story spec lists `RuleSection` with variants Core/Combat/Chase/Narrative/Custom but Python implementation uses a three-tier taxonomy (Critical/Firm/Coherence). ADR-009 also uses the three-zone model. Tests follow the Python/ADR design. Affects `sprint/epic-1.yaml` (story description may need updating).
- **Improvement** (non-blocking): Story spec says `SoulData` loaded from "YAML/Markdown" but the actual SOUL.md is pure markdown with `**Name.** Text` patterns — no YAML. Tests verify markdown parsing only. *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **RuleSection renamed to RuleTier:** Spec said `RuleSection` with variants Core, Combat, Chase, Narrative, Custom. Python uses `RuleTier` (Critical, Firm, Coherence) which is the actual three-tier taxonomy from ADR-009. Tests use `RuleTier` with the Python's proven taxonomy. Reason: the spec's variants don't match the Python implementation or ADR-009.
- **SectionCategory added:** Spec didn't mention `SectionCategory` but the Python implementation has it (Identity, Guardrail, Soul, Genre, State, Action, Format). Added to tests because `PromptSection` needs it for category-based filtering.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-agents/src/prompt_framework/types.rs` - Implemented AttentionZone::order(), all_ordered(), PromptSection::new(), with_source(), token_estimate(), is_empty()
- `crates/sidequest-agents/src/prompt_framework/soul.rs` - Implemented SoulData methods and parse_soul_md with regex extraction

**Tests:** 63/63 passing (GREEN)
**Branch:** feat/1-9-prompt-framework (pushed)

**Handoff:** To review phase

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core framework types and SOUL.md parser need thorough coverage.

**Test Files:**
- `crates/sidequest-agents/src/prompt_framework/tests.rs` — all prompt framework tests

**Tests Written:** 63 tests covering 6 ACs
- AttentionZone ordering: 14 tests (zone order, Ord impl, all_ordered, sorting, serde)
- SectionCategory: 3 tests (variant count, serde roundtrip)
- RuleTier: 3 tests (variant count, serde roundtrip)
- PromptSection: 10 tests (construction, token estimate, is_empty, serde roundtrip, deny_unknown_fields)
- SOUL.md parser: 10 tests (principle extraction, title, description, edge cases, real file)
- SoulData methods: 7 tests (len, is_empty, get, as_prompt_text)
- PromptComposer trait: 9 tests (zone ordering, insertion order, filtering, compose, clear, multi-agent)
- Edge cases: 5 tests (whitespace, multiline, Copy trait)

**Status:** RED (49 failing, 14 passing — failures are all todo!() panics)

**Handoff:** To Dev for implementation
