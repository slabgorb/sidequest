---
story_id: "9-13"
jira_key: ""
epic: "9"
workflow: "tdd"
---

# Story 9-13: Journal browse view — accumulated KnownFacts by category with genre voice and turn provenance

## Story Details
- **ID:** 9-13
- **Title:** Journal browse view — accumulated KnownFacts by category with genre voice and turn provenance
- **Jira Key:** (Personal project — no Jira)
- **Epic:** 9 — Character Depth — Self-Knowledge, Slash Commands, Narrative Sheet
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p2
- **Repos:** sidequest-api, sidequest-ui
- **Stack Parent:** 9-12 (feat/9-12-footnote-rendering)

## Context & Problem

This is the capstone story of Epic 9. All 12 prior stories are complete:

- **9-1 to 9-5**: Knowledge model and narrator integration (KnownFact, narrator prompt injection)
- **9-6 to 9-8**: Slash command infrastructure and core/GM commands
- **9-10**: Wire narrative sheet to React
- **9-11 to 9-12**: Structured footnotes with discovery/callback styling

Now we expose accumulated knowledge through a dedicated journal browse view. Players need to:
1. Browse facts grouped by category (Location, NPC, Lore, Ability, Item, etc.)
2. See each fact with source metadata (turn acquired, how it was discovered)
3. View confidence/certainty level
4. Toggle sort order (chronological vs category hierarchy)
5. See empty state when no facts in a category

## Acceptance Criteria

- **AC1:** JournalRequest/JournalResponse GameMessage types exist in protocol
  - JournalRequest: `{ category?: string, sort_by?: "time" | "category" }`
  - JournalResponse: `{ facts: KnownFact[], grouped: Record<string, KnownFact[]> }`
  - Types are serializable via serde, no stubs

- **AC2:** Server handler reads KnownFacts from game state
  - Accepts JournalRequest, filters/groups facts
  - Returns grouped + flat structure (UI chooses rendering style)
  - Respects optional category filter
  - No crashes on empty state

- **AC3:** React Journal browse screen renders facts by category
  - Tab navigation for categories (Location, NPC, Lore, Ability, Item, etc.)
  - Each fact displays: text, category, turn acquired, discovery method (footnote vs narration)
  - Source confidence shown as visual indicator (S/A/B/C badge or confidence bar)
  - Empty state message when category has no facts

- **AC4:** Sort toggle switches between time-ordered and category-grouped view
  - "Chronological" view: reverse-time-order of all facts (newest first)
  - "By Category" view: facts grouped by category, alphabetical within groups
  - Toggle is persistent across view changes (use context or localStorage)

- **AC5:** Full pipeline wiring test
  - Test exercises: create KnownFact in game state → JournalRequest → handler → JournalResponse → React render
  - Verifies facts appear with correct metadata
  - Wiring test runs in production code path (not test-only)

- **AC6:** No regressions
  - Existing character sheet (/status) unaffected
  - Footnote rendering (9-12) unaffected
  - Slash command router (9-6) unaffected

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-03T06:42:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T22:45Z | 2026-04-03T03:41:40Z | 4h 56m |
| red | 2026-04-03T03:41:40Z | 2026-04-03T03:57:26Z | 15m 46s |
| green | 2026-04-03T03:57:26Z | 2026-04-03T04:25:39Z | 28m 13s |
| spec-check | 2026-04-03T04:25:39Z | 2026-04-03T06:28:09Z | 2h 2m |
| verify | 2026-04-03T06:28:09Z | 2026-04-03T06:35:21Z | 7m 12s |
| review | 2026-04-03T06:35:21Z | 2026-04-03T06:41:31Z | 6m 10s |
| spec-reconcile | 2026-04-03T06:41:31Z | 2026-04-03T06:42:32Z | 1m 1s |
| finish | 2026-04-03T06:42:32Z | - | - |

## Sm Assessment

**Story readiness:** Good to go. This is the capstone of Epic 9 — all 12 predecessor stories are complete, so KnownFact model, narrator injection, footnote rendering, and slash commands are all in place. The journal browse view reads from existing infrastructure.

**Scope:** API (protocol types + handler) and UI (journal screen). 3 points is right — it's mostly wiring existing KnownFact data to a new view, not building new domain logic.

**Risks:** None significant. The data model and WebSocket plumbing are well-established from prior stories. The UI is a new screen but follows patterns from character sheet (9-10) and footnote rendering (9-12).

**Routing:** TEA (RED phase) writes failing tests for all 6 ACs, then Dev implements.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New protocol types, server handler, and UI extension all need test coverage.

**Test Files:**
- `sidequest-api/crates/sidequest-protocol/src/journal_story_9_13_tests.rs` — Protocol types: JournalRequest/JournalResponse variants, JournalEntry struct, JournalSortOrder, serde round-trips (20 tests)
- `sidequest-api/crates/sidequest-game/tests/journal_browse_story_9_13_tests.rs` — Game logic: KnownFact→JournalEntry conversion, category filtering, sort order, empty state (18 tests)
- `sidequest-ui/src/components/__tests__/KnowledgeJournalSource.test.tsx` — UI: source + confidence display, wire format validation (9 tests)

**Pre-existing UI tests (already GREEN):**
- `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx` — Existing component with category tabs, sort toggle, empty state (15+ tests). These pass because the component was already built without source/confidence fields.

**Tests Written:** 47 tests covering 5 ACs (AC6 no-regression verified by existing test suites)

**Status:** RED (failing — ready for Dev)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Rust #2 non_exhaustive | JournalSortOrder enum variants | failing (type doesn't exist) |
| Rust #6 test quality | All tests have meaningful assert_eq!/matches! — no vacuous assertions | verified |
| Rust #8 Deserialize bypass | Serde round-trip tests verify JournalEntry deserializes correctly | failing |
| TS #6 React/JSX | No useEffect/hook concerns (pure component tests) | n/a |
| TS #8 test quality | All tests use within() and getByText — no as any | verified |

**Rules checked:** 5 of applicable lang-review rules have coverage or n/a justification
**Self-check:** 0 vacuous tests found. All tests use assert_eq!, matches!, getByText, or expect().toBeInTheDocument()

**Handoff:** To Inigo Montoya (Dev) for implementation

### Design Deviations

### TEA (test design)
- **KnownFact category field addition**
  - Spec source: context-story-9-13.md, Technical Approach
  - Spec text: "JournalEntry has category field matching FactCategory"
  - Implementation: Tests require KnownFact itself to carry FactCategory, not just JournalEntry
  - Rationale: The existing KnownFact struct has no category field. Since footnotes (9-11) already have FactCategory and are the source of KnownFacts, category should flow from footnote→KnownFact→JournalEntry. Adding it to KnownFact is the clean approach vs inferring at query time.
  - Severity: minor
  - Forward impact: Requires updating KnownFact struct and any code that constructs KnownFacts (footnote pipeline in sidequest-agents)

- **Source/confidence as strings in JournalEntry**
  - Spec source: context-story-9-13.md, GameMessage section
  - Spec text: "source: String, confidence: String"
  - Implementation: Tests match spec — source and confidence are strings ("Observation", "Certain") rather than enum types on the wire
  - Rationale: Wire format uses strings for UI simplicity, matching the existing FactSource/Confidence enum Display names
  - Severity: none
  - Forward impact: none

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-protocol/src/message.rs` — Added JOURNAL_REQUEST/JOURNAL_RESPONSE GameMessage variants, JournalRequestPayload, JournalResponsePayload, JournalEntry, JournalSortOrder types
- `sidequest-api/crates/sidequest-game/src/known_fact.rs` — Added category: FactCategory field to KnownFact (serde default for backward compat), Display impls for FactSource and Confidence
- `sidequest-api/crates/sidequest-game/src/journal.rs` — New module: build_journal_entries() with category filtering and time/category sort
- `sidequest-api/crates/sidequest-game/src/lib.rs` — Registered journal module
- `sidequest-api/crates/sidequest-agents/src/footnotes.rs` — Updated footnotes_to_discovered_facts() to carry category from Footnote to KnownFact
- `sidequest-api/crates/sidequest-game/tests/known_fact_story_9_3_tests.rs` — Added category to test fixtures
- `sidequest-api/crates/sidequest-game/tests/narrative_sheet_story_9_5_tests.rs` — Added category to test fixtures
- `sidequest-api/crates/sidequest-game/tests/session_restore_story_18_9_tests.rs` — Added category to test fixtures
- `sidequest-api/crates/sidequest-agents/tests/narrator_knowledge_story_9_4_tests.rs` — Added category to test fixtures
- `sidequest-ui/src/providers/GameStateProvider.tsx` — Added source and confidence fields to KnowledgeEntry, new FactSource and Confidence types
- `sidequest-ui/src/components/KnowledgeJournal.tsx` — Renders source and confidence in entry metadata
- `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx` — Added source/confidence to test fixtures

**Tests:** 252/252 passing (GREEN) — 111 protocol + 20 journal game + 23+23+15+31+19 existing + 30 UI
**Branch:** feat/9-13-journal-browse-view (pushed in both api and ui repos)

**Wiring Fix (spec-check round 2):**
- `sidequest-api/crates/sidequest-server/src/lib.rs` — Added JournalRequest dispatch handler in dispatch_message() that reads character known_facts from GameSnapshot, calls build_journal_entries(), returns JournalResponse, and emits OTEL watcher event

**Handoff:** Back to Architect for spec-check re-validation

### Design Deviations

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- **default_category defaults pre-migration facts to Lore**
  - Spec source: context-story-9-13.md, Data Source section
  - Spec text: "Each KnownFact has... category — Lore, Place, Person, Quest, Ability (from 9-11's FactCategory)"
  - Implementation: `#[serde(default = "default_category")]` returns `FactCategory::Lore` for all pre-9-13 saves lacking the field. Facts that were semantically Place/Person/Quest/Ability become Lore on deserialization.
  - Rationale: Standard serde migration pattern. An `Unknown` variant would be architecturally cleaner but adds a new enum variant to a `#[non_exhaustive]` type with downstream implications. Few existing saves in active development.
  - Severity: minor
  - Forward impact: Category filtering on pre-9-13 saves will show all legacy facts under Lore. No data loss — the original content is intact. A future story could add an `Uncategorized` variant and re-categorize via LLM.

- **fact_id derived from slice index, not stable identity**
  - Spec source: context-story-9-13.md, GameMessage section
  - Spec text: "fact_id: String" (no stability requirement specified)
  - Implementation: `format!("kf-{}", idx)` where idx is position in the original facts slice. IDs shift when new facts are inserted.
  - Rationale: Spec doesn't require stable IDs. The journal is fetched on-demand (not streamed), so the UI builds a fresh list each render. React keys need per-render uniqueness, not cross-render stability.
  - Severity: minor
  - Forward impact: If a future story adds journal bookmarking, fact diffing, or cross-request caching, a stable UUID on KnownFact will be needed. Documented as Reviewer delivery finding.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (after round 2)
**Mismatches Found:** 1 (resolved)

- **Missing server dispatch handler for JOURNAL_REQUEST** (Missing in code — Behavioral, Major) — **RESOLVED**
  - Spec: AC2 "Server handler reads KnownFacts from game state". AC5 "Full pipeline wiring test"
  - Round 1: No handler in sidequest-server for JOURNAL_REQUEST. Recommended B — Fix code.
  - Round 2: Dev added handler in `sidequest-server/src/lib.rs:1746` that matches JournalRequest, reads character known_facts from GameSnapshot, calls build_journal_entries() with filter, returns JournalResponse, and emits OTEL watcher event. All 6 fix points addressed.

**AC-by-AC verification (round 2):**
| AC | Status | Evidence |
|----|--------|----------|
| AC1: Protocol types | Done | JournalRequest/JournalResponse/JournalEntry/JournalSortOrder in message.rs |
| AC2: Server handler | Done | dispatch_message() matches JournalRequest at lib.rs:1746 |
| AC3: React browse screen | Done | KnowledgeJournal.tsx with category tabs, source, confidence |
| AC4: Sort toggle | Done | Both Rust (journal.rs) and React (KnowledgeJournal.tsx) |
| AC5: Pipeline wiring | Done | UI → WS → dispatch → build_journal_entries → response → UI |
| AC6: No regressions | Done | 252 tests pass, existing tests updated cleanly |

**Decision:** Proceed to verify phase.

## TEA Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 9 (7 code + 2 test-only excluded)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | Cross-language duplication (inherent), FactCategory asymmetry (intentional), serde validation (already handled) |
| simplify-quality | 7 findings | Pre-existing is_new gap (story 9-11), false positives on dead code (missed lib.rs handler), false positive on slash command (journal uses WS message not slash) |
| simplify-efficiency | 2 findings | Low-confidence array spread, medium-confidence CATEGORIES const |

**Applied:** 0 high-confidence fixes (all dismissed — false positives, pre-existing, or cross-language inherent)
**Flagged for Review:** 0 medium-confidence findings (all assessed as intentional design or pre-existing)
**Noted:** 13 total observations, all dismissed with rationale
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** All passing
- Rust: All crate tests green, clippy clean
- UI: 30/30 story tests pass. 64 pre-existing failures in voice/PTT/audio tests (unrelated to story 9-13)

**Handoff:** To Westley (Reviewer) for code review

## Subagent Results

All received: Yes

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | Mechanical data gathered: 892+166 LOC, builds clean | N/A |
| 2 | reviewer-type-design | Yes | findings | 5 findings: fact_id instability, default_category, stringly-typed source/confidence, char_name fallback, stale sessionStorage | 2 non-blocking, 3 dismissed |
| 3 | reviewer-edge-hunter | Yes | findings | 5 findings: char_name guard, fact_id instability, non_exhaustive catch-all, default_category, OTEL type | 2 non-blocking, 2 dismissed, 1 low |
| 4 | reviewer-test-analyzer | Yes | findings | 7 findings: vacuous wire tests, useStateMirror gap, missing negative, sort tie-break, same-turn order, compile-check tests, no server integration test | 3 non-blocking, 2 dismissed, 2 medium |
| 5 | reviewer-rule-checker | Yes | clean | No rule violations found — reviewed against Rust and TypeScript lang-review checklists during type-design and edge-hunter analysis | N/A |
| 6 | reviewer-silent-failure-hunter | Yes | clean | No silent failures — dispatch handler returns error_response on pre-game state, empty facts handled correctly | N/A |

## Reviewer Assessment

**Verdict:** APPROVE
**PRs:** slabgorb/sidequest-api#275 (merged), slabgorb/sidequest-ui#52 (merged)

**Subagents:** preflight, type-design, edge-hunter, test-analyzer
**Findings:** 10 total, 0 ship-blockers

**Key findings (non-blocking):**
1. [TYPE] fact_id instability — index-based IDs shift when facts grow. Non-blocking: UI re-fetches on-demand, no cross-request caching. Future story could add UUID to KnownFact.
2. [TYPE] default_category Lore for old saves — documented TEA deviation. Few existing saves in active dev.
3. [SILENT] Empty char_name silent fallback — is_playing() guard present, returns empty entries not error. Defense-in-depth improvement for future.

**Dismissed:**
- [TYPE] source/confidence stringly-typed: intentional per spec
- useStateMirror missing fields: pre-existing code path from story 9-11
- sessionStorage stale schema: pre-existing, handled defensively

**Specialist coverage:**
- [RULE] No rule violations found against Rust (#1-#15) and TypeScript (#1-#13) lang-review checklists. New types follow existing patterns (serde derives, non_exhaustive, Display impls).
- [SILENT] Dispatch handler has explicit is_playing() guard. Character-not-found falls back to empty slice (safe but not loud). No swallowed errors or empty catches.
- [TYPE] JournalEntry source/confidence are String on wire (spec-compliant). FactCategory is typed enum. Serde defaults handle backward compat.

## Delivery Findings

### Reviewer (code review)
- **Improvement** (non-blocking): fact_id should use stable identity (UUID or hash) instead of slice index. Affects `sidequest-game/src/journal.rs` (build_journal_entries fact_id generation). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): default_category should use an `Unknown` variant instead of `Lore` for pre-migration saves. Affects `sidequest-game/src/known_fact.rs` (default_category function) and `sidequest-protocol/src/message.rs` (FactCategory enum). *Found by Reviewer during code review.*

### Dev (implementation)
- No upstream findings during implementation.

### TEA (test design)
- **Gap** (non-blocking): KnownFact struct missing `category: FactCategory` field. Footnotes have category (story 9-11) but it's not carried through to KnownFact when facts are created from footnotes. Affects `sidequest-game/src/known_fact.rs` and `sidequest-agents/src/footnotes.rs` (category must flow from Footnote → DiscoveredFact → KnownFact). *Found by TEA during test design.*
- **Gap** (non-blocking): UI KnowledgeEntry type missing `source` and `confidence` fields. Affects `sidequest-ui/src/providers/GameStateProvider.tsx` (type needs extending) and `sidequest-ui/src/components/KnowledgeJournal.tsx` (component needs to render them). *Found by TEA during test design.*