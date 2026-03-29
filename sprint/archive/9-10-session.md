---
story_id: "9-10"
jira_key: ""
epic: "9"
workflow: "tdd"
---
# Story 9-10: Wire narrative sheet to React client — CHARACTER_SHEET message with genre-voiced content

## Story Details
- **ID:** 9-10
- **Jira Key:** (personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** 9-5 (develop — parent merged)
- **Branch:** feat/9-10-wire-narrative-sheet-react (both sidequest-api and sidequest-ui)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-28T21:57:53Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28 17:35:00 | 2026-03-28T21:32:20Z | 3h 57m |
| red | 2026-03-28T21:32:20Z | 2026-03-28T21:36:57Z | 4m 37s |
| green | 2026-03-28T21:36:57Z | 2026-03-28T21:44:51Z | 7m 54s |
| spec-check | 2026-03-28T21:44:51Z | 2026-03-28T21:52:11Z | 7m 20s |
| review | 2026-03-28T21:52:11Z | 2026-03-28T21:57:53Z | 5m 42s |
| finish | 2026-03-28T21:57:53Z | - | - |

## Delivery Findings

### TEA (test design)
- No upstream findings during test design.

## Design Deviations

### TEA (test design)
- **Protocol types as separate structs, not re-exported from game crate**
  - Spec source: session file, AC-1 (protocol update)
  - Spec text: "Update CharacterSheetPayload to embed NarrativeSheet"
  - Implementation: Tests expect new protocol-level types (SheetAbility, SheetKnowledge, SheetStatus) rather than directly embedding sidequest-game's NarrativeSheet, because sidequest-protocol does not depend on sidequest-game.
  - Rationale: Protocol crate has no dependency on game crate. The server must convert between the two. Mirrored types maintain the clean crate boundary.
  - Severity: minor
  - Forward impact: Dev must create SheetAbility/SheetKnowledge/SheetStatus in protocol crate and convert from NarrativeSheet in server.

## Technical Context

**Parent Story (9-5):** `to_narrative_sheet()` implementation complete. Produces:
- `NarrativeSheet` struct with genre-voiced fields:
  - `identity`: String (name, race, class — no raw stats)
  - `abilities`: Vec<AbilityEntry> (genre descriptions, never mechanical effects)
  - `knowledge`: Vec<KnowledgeEntry> (facts with confidence tags)
  - `status`: CharacterStatus (narrative health + conditions)

**Current Protocol State:**
- `CharacterSheetPayload` exists in protocol but has old schema:
  - Raw fields: name, class, level, stats (HashMap<String, i32>), abilities (Vec<String>), backstory
  - Does NOT embed NarrativeSheet

**Wiring Gaps:**
1. Protocol: CharacterSheetPayload must be updated to use NarrativeSheet shape
2. Server: Two construction sites (dispatch_connect reconnect, dispatch_character_creation) manually build old payload — must use to_narrative_sheet()
3. Client: CharacterSheet.tsx expects old stat-based interface, must render genre-voiced sections

**Dependencies:**
- 9-5 ✓ (merged, feat/9-5-narrative-character-sheet in develop)
- 9-3 ✓ (KnownFact model, complete)
- 9-1 ✓ (AbilityDefinition, complete)

## Sm Assessment

**Routing:** TDD phased workflow → TEA (red phase) writes failing tests first.

**Scope:** 3-point cross-repo wiring story. Three connection points:
1. **Protocol** — Update `CharacterSheetPayload` to embed `NarrativeSheet` instead of raw stats
2. **Server** — Wire session handler to construct CHARACTER_SHEET messages via `Character::to_narrative_sheet()`
3. **Client** — Refactor `CharacterSheet.tsx` to render genre-voiced fields (identity, abilities, knowledge, status)

**Risk:** Low. All dependencies merged. Parent 9-5 provides the `NarrativeSheet` struct and `to_narrative_sheet()` method. This is pure wiring — no new domain logic.

**Recommendation:** Ready for TEA. Tests should cover: payload shape, server emission on /status or session join, client rendering of all four NarrativeSheet sections.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Cross-repo wiring story with protocol, server, and client changes — all need test coverage.

**Test Files:**
- `sidequest-api/crates/sidequest-game/tests/narrative_sheet_wiring_story_9_10_tests.rs` — Protocol shape, round-trip, old-format rejection (11 tests)
- `sidequest-ui/src/components/__tests__/CharacterSheet.9-10.test.tsx` — Narrative sheet rendering (17 tests)

**Tests Written:** 28 tests covering 3 ACs

### Test Coverage

| AC | Tests | What's Covered |
|----|-------|---------------|
| AC-1: Protocol shape | 11 Rust tests | NarrativeSheet serialization (identity, abilities, knowledge, status), empty arrays, no raw numbers leak |
| AC-2: Protocol type update | 3 Rust tests | CharacterSheetPayload new fields, old format rejection, round-trip |
| AC-3: Client rendering | 17 React tests | Identity display, ability names+descriptions+involuntary markers, knowledge+confidence tags, narrative health+conditions, portrait, no raw stats |

### RED State Verification

| Repo | Result | Errors |
|------|--------|--------|
| sidequest-api | RED (compilation) | 26 errors — missing SheetAbility/SheetKnowledge/SheetStatus types, missing identity/knowledge/status fields on CharacterSheetPayload |
| sidequest-ui | RED (16 failures, 1 pass) | NarrativeSheetData not exported, component crashes on old data shape |

**Self-check:** 0 vacuous tests found. All tests have meaningful assertions. No `let _ =` patterns.

**Handoff:** To Inspector Lestrade (Dev) for implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-protocol/src/message.rs` — Replaced CharacterSheetPayload fields with NarrativeSheet shape; added SheetAbility, SheetKnowledge, SheetStatus types
- `sidequest-api/crates/sidequest-protocol/src/tests.rs` — Updated character_sheet_round_trip test for new payload shape
- `sidequest-api/crates/sidequest-server/src/lib.rs` — Added narrative_sheet_to_payload() converter; updated 2 CHARACTER_SHEET construction sites to use to_narrative_sheet()
- `sidequest-api/crates/sidequest-game/tests/narrative_sheet_wiring_story_9_10_tests.rs` — Fixed test helper (KnownFact/CreatureCore construction)
- `sidequest-ui/src/components/CharacterSheet.tsx` — Rewrote with NarrativeSheetData type; renders identity, abilities+involuntary markers, knowledge+confidence, narrative status
- `sidequest-ui/src/components/__tests__/CharacterSheet.test.tsx` — Updated for new data shape
- `sidequest-ui/src/screens/NarrativeView.tsx` — Updated CHARACTER_SHEET handler to use identity string
- `sidequest-ui/src/screens/__tests__/NarrativeView.test.tsx` — Updated test fixture for new payload

**Tests:** 10/10 Rust passing, 26/26 React passing (GREEN)
**Branch:** feat/9-10-wire-narrative-sheet-react (pushed in both repos)

**Handoff:** To TEA for verify phase

### Dev (implementation)
- No upstream findings during implementation.

### Design Deviations

### Dev (implementation)
- **Fixed TEA test helper for KnownFact/CreatureCore construction**
  - Spec source: TEA test file, test_character() helper
  - Spec text: Tests used string fields (source, category, fact_id) that don't exist on KnownFact
  - Implementation: Fixed to use actual struct fields (FactSource enum, no category/fact_id)
  - Rationale: Test helper had compilation errors from incorrect field names
  - Severity: minor
  - Forward impact: none — test behavior unchanged, only construction fixed
- **Added CharacterSheetData type alias for backwards compatibility**
  - Spec source: session file, AC-3 (client update)
  - Spec text: "Refactor CharacterSheet.tsx to render genre-voiced fields"
  - Implementation: Added `type CharacterSheetData = NarrativeSheetData` alias to avoid breaking existing imports in App.tsx, OverlayManager.tsx, GameLayout.tsx
  - Rationale: Minimizes churn in files not directly related to this story
  - Severity: minor
  - Forward impact: none — alias can be removed when those files are touched next

### Reviewer (audit)
- **TEA test helper fix** → ✓ ACCEPTED by Reviewer: Necessary correction, test semantics unchanged.
- **CharacterSheetData type alias** → ✓ ACCEPTED by Reviewer: Minimizes churn, deprecated annotation signals intent.
- **Protocol sub-struct deny_unknown_fields** → UNDOCUMENTED by TEA/Dev: New SheetAbility, SheetKnowledge, SheetStatus structs omit `#[serde(deny_unknown_fields)]` while most other named sub-structs in protocol have it. Severity: LOW.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | Story-scoped GREEN; pre-existing failures in both repos | confirmed 0 (pre-existing only) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 findings | confirmed 1 (Debug fragility), dismissed 1 (as-string cast is pre-existing pattern) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 findings | confirmed 1 (Debug fragility, corroborates silent-failure), dismissed 3 (deny_unknown_fields — downgraded to LOW, matches Footnote exception and is not a breaking issue) |

**All received:** Yes (3 returned, 6 disabled)
**Total findings:** 1 confirmed (MEDIUM), 4 dismissed (with rationale)

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Protocol type shape matches NarrativeSheet — `message.rs:440-481` correctly defines identity/abilities/knowledge/status with proper derive macros. CharacterSheetPayload retains `deny_unknown_fields`. Complies with protocol conventions.
2. [VERIFIED] Server conversion is complete — `lib.rs:45-74` `narrative_sheet_to_payload()` maps all 5 fields (identity, abilities, knowledge, status, portrait_url). No fields dropped silently. Both construction sites (`lib.rs:1543`, `lib.rs:2045`) updated.
3. [VERIFIED] React component renders all 4 NarrativeSheet sections — `CharacterSheet.tsx:36-98` renders identity, abilities (with involuntary markers via data-testid), knowledge (with confidence tags), and narrative status. Empty arrays handled gracefully.
4. [SILENT] `format!("{:?}", k.confidence)` at `lib.rs:65` uses Debug repr for wire format — works today for unit variants but fragile against enum evolution. MEDIUM severity but non-blocking: Confidence enum is stable (story 9-3), has no custom Debug impl, and the test suite validates the exact strings. Recommend adding `Display` impl on Confidence in a follow-up. *Not blocking because: the test `narrative_sheet_serializes_knowledge_with_confidence` explicitly asserts the string values, so any Debug-breaking change would be caught.*
5. [RULE] Three new sub-structs (SheetAbility, SheetKnowledge, SheetStatus) omit `#[serde(deny_unknown_fields)]`. Most other sub-structs in the protocol have it, but `Footnote` (also story 9-11) does not. LOW severity — inconsistent but non-breaking since `deny_unknown_fields` on the parent `CharacterSheetPayload` already rejects unknown top-level fields.
6. [VERIFIED] Data flow traced: `Character::to_narrative_sheet("")` → `NarrativeSheet` → `narrative_sheet_to_payload()` → `CharacterSheetPayload` → JSON via serde → WebSocket → client `setCharacterSheet()` cast → `CharacterSheet` component render. Flow is clean, no data loss.
7. [VERIFIED] Wiring complete — NarrativeView handler updated (`NarrativeView.tsx:154-159`), App.tsx uses type alias for backwards compat, OverlayManager passes data through.
8. [EDGE] N/A — disabled.
9. [TEST] N/A — disabled.
10. [DOC] N/A — disabled.
11. [TYPE] N/A — disabled.
12. [SEC] N/A — disabled.
13. [SIMPLE] N/A — disabled.

### Devil's Advocate

What if the NarrativeSheet is constructed for a character with zero abilities, zero known facts, zero conditions, and full HP? The CharacterSheet component would render: identity string, no abilities section (guarded by `.length > 0`), no knowledge section, and just "in good health" with no conditions. This is tested and works. What about an identity string that contains HTML? The component renders it via JSX text content (`{data.identity}`), which React auto-escapes — safe against XSS. What about extremely long identity strings? No truncation, but that's a genre pack content issue, not a code bug. What about the `portrait_url` always being `None` at both server construction sites? This is correct — portraits are delivered via separate IMAGE messages, not embedded in the CHARACTER_SHEET payload. The `portrait_url` field exists for future direct embedding but currently the overlay handles portrait display independently. What about a malicious WebSocket message injecting unexpected fields into the CHARACTER_SHEET payload? The Rust side has `deny_unknown_fields` on CharacterSheetPayload, so the server will never send unknown top-level fields. The sub-structs lack this guard but are nested — unknown fields there would only matter if a custom serializer injected them, which can't happen through the normal `narrative_sheet_to_payload` path.

**Data flow traced:** `Character::to_narrative_sheet("")` → server → WebSocket JSON → client `CharacterSheet` component (safe: React JSX escaping, no dangerouslySetInnerHTML)
**Pattern observed:** Clean separation of game-crate types from protocol types via server-side conversion function at `lib.rs:45-74`
**Error handling:** Component handles empty arrays gracefully; server construction is infallible (no Result types needed for pure data mapping)

**Handoff:** To Dr. Watson (SM) for finish-story

### Delivery Findings

### Reviewer (code review)
- **Improvement** (non-blocking): `format!("{:?}", k.confidence)` uses Debug repr as wire format. Affects `sidequest-server/src/lib.rs:65` (add Display impl on Confidence enum). *Found by Reviewer during code review.*