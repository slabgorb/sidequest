# Story 50-14: Journal: JOURNAL_REQUEST handler — server replies from character.known_facts

---
story_id: "50-14"
epic: "50"
workflow: "tdd"
---

## Story Details
- **ID:** 50-14
- **Epic:** 50 — Pingpong-archive triage and dropped-work cleanup
- **Workflow:** tdd
- **Stack Parent:** 50-5 (wire discover_clue to narration consumption)
- **ADR Reference:** ADR-100 Seam C (server side)

## Story Summary

Implement the JOURNAL_REQUEST → JOURNAL_RESPONSE handler on the server. This closes **Seam C (server side)** of ADR-100's journal pipeline coherence design.

**Current state:**
- `character.known_facts` is populated and persistent (live since ADR-083 character model)
- JOURNAL_REQUEST / JOURNAL_RESPONSE enums exist in protocol
- UI is fully prepared to consume JOURNAL_RESPONSE with the canonical knowledge model (`useStateMirror.ts:130-155`)
- **No server handler emits JOURNAL_RESPONSE** ← This story closes that gap

**What the story ships:**
- A dispatch handler that receives JOURNAL_REQUEST and responds with JOURNAL_RESPONSE
- The response is populated from the active character's `known_facts` list
- The `to:` field is validated per ADR-036 multiplayer doctrine (character permission check)
- OTEL span `SPAN_JOURNAL_REPLAY` emits (zero-duration; entry count, character id) for GM dashboard observability

## Acceptance Criteria

1. **Handler receives JOURNAL_REQUEST and responds with JOURNAL_RESPONSE**
   - Message type routing is wired in `dispatch/dispatch_router.py` or equivalent
   - Handler reads `message.to` character id and resolves to active player's character
   - Response includes all entries from `character.known_facts` (model carries `content, confidence, source, learned_turn`)

2. **Multiplayer validation via ADR-036 doctrine**
   - `to:` field is validated: only the owning player can request their own journal
   - Invalid requests (wrong character, no such character, permission denied) return 400-level error
   - See `sidequest-server/sidequest/game/projection/invariants.py:30` for the existing multiplayer-visibility invariant

3. **OTEL observability**
   - `SPAN_JOURNAL_REPLAY` span emits when the handler fires (zero-duration, no child spans)
   - Span carries fields: `character_id`, `entry_count` (int, total known_facts returned)
   - GM dashboard can verify the handler is engaged and entries are flowing

4. **Integration test covers the full path**
   - Test fixture: single-player session, character with 3-5 known_facts (mix of sources: narrator-emitted, scenario clue, hardcoded seed data)
   - Test sends JOURNAL_REQUEST for that character
   - Assertions: response type correct, entry count matches, all entries match in-memory state, confidence/source fields present

5. **Wiring verification**
   - Handler is imported in dispatch router and callable from production code paths
   - No silent fallbacks; missing character or permission error returns clean 400-level response with detail

## Technical Approach

### Component: JOURNAL_REQUEST Dispatch Handler

**Location:** `sidequest-server/sidequest/handlers/journal_handler.py` (new file)

**Entry point:** Dispatch hook called from `websocket_session_handler.py` or `dispatch_router.py`

**Implementation shape:**
```python
async def handle_journal_request(
    message: JournalRequest,  # Contains: to (character_id: str)
    state: GameSnapshot,
    session_player_id: str,
) -> JournalResponse:
    """
    Respond to JOURNAL_REQUEST with canonical journal from character.known_facts.
    
    Args:
        message: JOURNAL_REQUEST with `to` character id
        state: Current game snapshot
        session_player_id: Player making the request
        
    Returns:
        JOURNAL_RESPONSE with character.known_facts entries
        
    Raises:
        ValueError: If character not found or permission denied
    """
    # 1. Resolve target character from `to` field
    target_char_id = message.to
    target_char = state.get_character_by_id(target_char_id)
    if not target_char:
        raise ValueError(f"Character {target_char_id} not found")
    
    # 2. Validate permission (ADR-036: only owning player can request own journal)
    #    Look up which player owns this character
    player_owner = state.get_player_owning_character(target_char_id)
    if player_owner != session_player_id:
        raise ValueError(f"Permission denied: player {session_player_id} cannot view journal of player {player_owner}'s character")
    
    # 3. Build JOURNAL_RESPONSE from character.known_facts
    entries = [
        JournalEntry(
            fact_id=fact.id,  # From KnownFact model
            content=fact.content,
            confidence=fact.confidence,  # "Certain", "Suspected", "Rumored", "Discovered"
            source=fact.source,  # "Observation", "ScenarioClue", "Gossip", etc.
            learned_turn=fact.learned_turn,
        )
        for fact in target_char.known_facts
    ]
    
    # 4. Emit OTEL span
    with tracer.start_as_current_span("SPAN_JOURNAL_REPLAY") as span:
        span.set_attribute("character_id", target_char_id)
        span.set_attribute("entry_count", len(entries))
    
    response = JournalResponse(
        to=target_char_id,
        entries=entries,
    )
    return response
```

### Protocol Models

**Verify or add to `sidequest-server/sidequest/protocol/enums.py`:**
- `JournalRequest` model (if missing): `to: str` (character id)
- `JournalResponse` model (if missing): `to: str`, `entries: list[JournalEntry]`
- `JournalEntry` model (if missing): `fact_id, content, confidence, source, learned_turn`

If models already exist, audit for missing fields (especially `fact_id` and `confidence` enum promotion per ADR-100 story 50-17).

### KnownFact Model Audit

Check `sidequest-server/sidequest/game/character.py:KnownFact` for:
- `fact_id` field (should exist per ADR-100)
- `confidence` field (should be `str` or new `Literal` enum per 50-17)
- `source` field (already exists per ADR-100 map)
- `learned_turn` field (already exists, marked P5-deferred, now exercised by 50-5)

No changes to KnownFact needed for this story (enum promotion is 50-17); just wire the existing model.

### Dispatch Router Wiring

**Location:** `sidequest-server/sidequest/handlers/dispatch_router.py` or equivalent routing table

Add routing entry:
```python
MessageType.JOURNAL_REQUEST: handle_journal_request,
```

Verify the import path and async signature match the framework's expectations.

### OTEL Span Definition

Check `sidequest-server/sidequest/telemetry/spans.py` (or equivalent telemetry module) for span names.

Add or verify:
```python
SPAN_JOURNAL_REPLAY = "journal.replay"  # Zero-duration observability span
```

Reference in the handler via tracer (e.g., `from sidequest.telemetry import tracer`).

## Design Deviations

None anticipated. The story is narrow spec-to-code wiring.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Request payload shape: `filter?: str` (UI contract), not `to: character_id` (SM design note)**
  - Spec source: sidequest-ui/src/types/payloads.ts:244 (`JournalRequestPayload`) and useStateMirror.ts:130-155
  - Spec text: `JournalRequestPayload { filter?: string }`; response is keyed by the requesting player implicitly
  - Implementation: Tests construct `JournalRequestMessage(payload={}, player_id="P1")` — no `to` field. Server resolves the character from `snapshot.player_seats[player_id]`.
  - Rationale: SM's technical-approach pseudocode referenced `message.to`, but the live UI types have no such field. UI contract wins (spec authority hierarchy: story context > arch doc). Using player_id-based lookup also makes ADR-036 multiplayer permission automatic — a player cannot ask for another player's journal because the lookup is one-to-one.
  - Severity: minor
  - Forward impact: Dev should NOT add a `to` field to JournalRequestPayload. If a future story needs GM cross-player journal inspection, that's a separate message type.

- **AC2 permission test uses player_seats lookup, not `get_player_owning_character`**
  - Spec source: 50-14 session file Technical Approach §JournalRequestHandler step 2
  - Spec text: "Look up which player owns this character via `state.get_player_owning_character`"
  - Implementation: Tests verify ownership through `snapshot.player_seats[player_id] → character.core.name`. No such function as `get_player_owning_character` exists in the codebase.
  - Rationale: The session referenced a function that doesn't exist. The actual pattern in this codebase (verified in websocket_session_handler.py:2093, 2936, 3795) is direct dict lookup into `snapshot.player_seats`. Tests target the real shape.
  - Severity: minor
  - Forward impact: Dev should use the dict lookup pattern, not introduce a new abstraction layer.

- **No `to` field used to address the response — `player_id` is the address**
  - Spec source: existing OrbitalChartMessage / DiceResultMessage precedent
  - Spec text: implicit
  - Implementation: Tests assert `response.player_id == "P1"` (the requester). No `to` field on the response.
  - Rationale: Matches every other per-player message type in the codebase. UI routes by `player_id`.
  - Severity: trivial
  - Forward impact: none

### Dev (implementation)

- **KnownFact gains `fact_id` and `category` fields (no derivation trick)**
  - Spec source: TEA Delivery Finding (blocking) + UI types at `sidequest-ui/src/types/payloads.ts:248-257`
  - Spec text: "KnownFact lacks fact_id and category fields that the UI's JournalResponsePayload contract requires."
  - Implementation: Added `fact_id: str = Field(default_factory=lambda: uuid4().hex)` and `category: FactCategory = FactCategory.Lore` directly on the KnownFact model. The scenario clue intake site (`scenario_clue_intake.py`) now passes through the footnote's clue id (`fn.fact_id`) and category, so scenario-minted facts get meaningful, stable IDs. Ad-hoc fact creation (test helper, other call sites without context) gets a fresh UUID per instance — stable for the life of that fact, deterministic for dedup.
  - Rationale: Per TEA's note (and CLAUDE.md "no silent fallbacks"), UUID-on-creation is the safest path — survives reordering, deletion, and snapshot serialization round-trips. Index-based or content-hash derivation has subtle failure modes. The cost is two extra fields on a small model; benefit is the UI contract becomes truthful.
  - Severity: minor
  - Forward impact: Story 50-17 (KnownFact.confidence enum promotion) lands alongside cleanly — confidence remains `str` for now, can be tightened to a Literal later. Future migrations of old save files will get the default category `Lore` and a freshly-minted UUID, which is correct: pre-50-14 facts have no semantically meaningful category or id to preserve.

- **`fact_id` default uses `uuid4().hex`, not deterministic hash**
  - Spec source: TEA Critical Note #2: "Index-based fact_ids will break ... UUID-on-creation is the safest path."
  - Spec text: "Index-based fact_ids ('kf-0', 'kf-1', ...) will pass that test only if the order is stable."
  - Implementation: `uuid4().hex` is non-deterministic across processes but stable within a fact's lifetime. Save-file persistence round-trips the id verbatim (pydantic serializes/deserializes the string), so reload preserves dedup keys.
  - Rationale: Two existing test suites construct KnownFact directly without a fact_id (test_character.py and test_scenario_accusation_intake.py). A required field would have broken them; a deterministic hash of content+source+learned_turn would have collided when two facts share content. Per-instance UUID is the simplest path that survives every reasonable mutation.
  - Severity: trivial
  - Forward impact: none — UI dedup is by string equality, which works regardless of derivation strategy.

- **Test fixture defect (not a deviation from spec — fixture bug):**
  TEA's `_character_with_facts` helper constructed `CreatureCore(name=name)` and `Character(core=...)` without the required `description`/`personality`/`inventory`/`char_class`/`race`/`backstory` fields. Updated the helper to supply test-quality defaults; assertion logic untouched. This is a fixture-quality fix, not a spec deviation — the tests themselves still target the intended ACs.

### TEA (test verification)

- No deviations from spec during verify phase. One high-confidence simplify-pass fix applied (drop unreachable isinstance branch in `journal_request.py`) — this is code-tightening, not a spec change. One high-confidence simplify finding declined with rationale (UI contract preservation for `JournalRequestPayload.filter`). Six medium-confidence findings flagged for Reviewer review; none alter the implemented behavior.

### Reviewer (audit)

No UNDOCUMENTED spec deviations found — every TEA/Dev/Architect deviation entry above is reviewed and stamped ACCEPTED in the Deviation Audit subsection of the Reviewer Assessment (see `## Reviewer Assessment` below). The Reviewer-confirmed defects (vacuous assertions, ADR misattribution, misleading OTEL docs) are test-quality and documentation issues, not spec drifts — they don't belong in the deviations log; they belong in the rework punch list.

### Dev (rework)

- No new deviations from spec during rework. All Reviewer findings addressed mechanically: test assertions tightened to pin specific values per python.md #6, three documentation defects corrected (ADR-083 → ADR-100, "Zero-duration" → "Short-duration", "Subsystems → Journal pane" → "Subsystems tab component grid"). Added one LOW-severity test (filter-ignore) to pin current contract. No behavior changes, no model changes, no new spec interpretation.

### TEA (test verification, rework cycle 1)

- No deviations from spec during the rework-cycle verify phase. Simplify trio returned 2 clean teammates + 1 with 2 findings; both findings declined with documented rationale (project-wide pattern consistency for `getattr` form, Reviewer-required differentiation for the two error-path tests). No production-code or test-code changes applied this pass.

### Architect (reconcile)

I audited every prior deviation entry in this section against the live code and project files. All TEA/Dev entries have all 6 required fields, accurate spec sources, accurate spec text, and accurate implementation descriptions. The Reviewer's audit (above) correctly stamped each as ACCEPTED. No prior entry needs correction.

One additional formal deviation was surfaced during round-1 spec-check but never made it into the canonical deviations log — formalizing it here per spec-reconcile responsibility:

- **AC3 spec text says `character_id`; the OTEL span attribute is `character_name`**
  - Spec source: `.session/50-14-session.md` Acceptance Criteria §3 (lines 44-47): "Span carries fields: `character_id`, `entry_count` (int, total known_facts returned)"
  - Spec text: `"character_id"`
  - Implementation: `sidequest/handlers/journal_request.py:115` sets `span.set_attribute("character_name", character_name)`. The test `test_handler_emits_journal_replay_span` asserts the `character_name` attribute. The OTEL span constant `SPAN_JOURNAL_REPLAY` is documented in `sidequest/telemetry/spans/journal.py:9-13` as carrying `character_name`.
  - Rationale: The codebase has no `character_id` concept — `character.core.name` is the canonical character identity throughout the system (verified via `grep character_id sidequest/protocol/ sidequest/game/character.py` → no matches in production code). The session AC3 used "id" loosely as a noun for "stable identifier." The code uses the actual identity field (`name`). Spec authority hierarchy resolves in code's favor: the codebase pattern across every character-touching subsystem is canonical, and the AC's wording was an SM-side imprecision rather than a deliberate design choice.
  - Severity: trivial
  - Forward impact: none for ADR-100 follow-ups. The GM dashboard and any future operator tools should consume `character_name` from the span attributes, matching every other character-attributed span in the codebase. Future story 50-17 (KnownFact.confidence enum) does not interact with this attribute. If a future story introduces a real `character_id` distinct from `character.core.name` (e.g., for character renaming), revisit this span and add both attributes side-by-side rather than overloading one name.

No other undocumented deviations surfaced during reconcile. AC accountability table: not present in the session file (ac-completion gate left it absent because all five ACs are DONE per the Reviewer's data-flow trace and the Reviewer's Round-2 verification of round-1 findings; no AC was deferred or descoped).

## Delivery Findings

No upstream findings. Dependencies (50-5, 50-6) are merged; character.known_facts is live and populated.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Gap** (blocking): `KnownFact` model lacks `fact_id` and `category` fields that the UI's `JournalResponsePayload` contract requires.
  Affects `sidequest-server/sidequest/game/character.py:19-32` (add fields, OR map them explicitly in the handler with deterministic non-fallback derivation). The UI types at `sidequest-ui/src/types/payloads.ts:248-257` consume `fact_id` (for dedup in `useStateMirror.ts:141`) and `category` (passed through `validateCategory`). The SM session assumed both fields existed "per ADR-100" — they do not. Dev MUST surface this gap explicitly (no silent fallback per CLAUDE.md). Recommended: add `fact_id: str` and `category: str = "Lore"` to KnownFact with appropriate defaults set at fact-creation sites; this aligns with the 50-17 enum-promotion follow-up and keeps the journal pipeline truthful.
  *Found by TEA during test design.*

- **Conflict** (non-blocking): SM technical approach referenced `message.to: character_id` and `state.get_player_owning_character(...)` — neither exist in the UI protocol or the server codebase. Resolved in deviation log; tests target the live shapes (`player_id` + `snapshot.player_seats`). See `### TEA (test design)` deviation entries above.
  Affects `.session/50-14-session.md` Technical Approach §JournalRequestHandler step 2 + Protocol Models §1. Dev should treat the UI contract (`payloads.ts:244-257`) and the existing `player_seats` lookup pattern as the source of truth, not the SM pseudocode.
  *Found by TEA during test design.*

- **Improvement** (non-blocking): No story-specific context file exists at `sprint/context/context-story-50-14.md`. Setup gate passed via `pf validate context` because no validator targets per-story context strictness, but future agents working this story have less than the usual context surface. Not blocking — the session file's Technical Approach is dense — but flag for the orchestrator if context-creation should be added to the SM setup pipeline for ADR-tagged stories.
  Affects `sprint/context/` (no file to create now; this is a process observation for SM/Orchestrator).
  *Found by TEA during test design.*

### Dev (implementation)

- **Improvement** (non-blocking): Stale `.venv` regression observed again on this clone — `uv run pytest` resolved to a pipx pytest at `/Users/slabgorb/.local/pipx/venvs/pytest/...` instead of the project venv. Wiping `.venv` and re-running `uv sync --extra dev` restored the project's pytest. Per the memory note ("Stale venv shebangs across clones"), this is a recurring failure mode; consider adding a `just doctor` recipe or a pre-test sanity check that asserts `which pytest` lives under `.venv/bin/`.
  Affects developer ergonomics (no code fix needed for this story; just a UX note).
  *Found by Dev during implementation.*

- **No upstream findings beyond what TEA already flagged.** KnownFact gap was the only meaningful surface area, and it's been closed via the chosen implementation (see Design Deviations §Dev for rationale).

### TEA (test verification)

- **Improvement** (non-blocking): Two shared-helper extractions are warranted across handlers: `_resolve_character_by_seat(snapshot, player_id)` (also used in `dice_throw.py:85-94`) and `_validate_room_bound(session)` (also used in `orbital_intent.py:36-49`). Both surfaced from simplify-reuse with high confidence; deferred from 50-14 because the refactor touches three handlers, expanding scope beyond this story's ADR-100 Seam C lane.
  Affects `sidequest-server/sidequest/server/session_helpers.py` (new helpers) plus `journal_request.py`, `orbital_intent.py`, `dice_throw.py` (callsite migration). Recommend a small chore story to land both helpers and migrate the three handlers in one pass.
  *Found by TEA during test verification.*

- **No other upstream findings.** One high-confidence simplify fix applied (dead isinstance branch); one declined with rationale (UI contract preservation for `filter` field); all medium/low findings either deferred with reason or already covered by the Architect's spec-check assessment.

### Reviewer (code review)

- **Gap** (non-blocking, process): The python.md #6 ("test quality — no truthy-only assertions") rule is currently enforced by reviewer-self-review only — no automated linter check exists. Story 50-14's RED phase committed two vacuous `assert obj.attr` patterns on `str` / `str | None` fields that all the existing gates passed (ruff, pyright, pytest, lang-review self-check). Recommend a follow-up story to ship a pytest plugin or AST-based check that flags `assert <attr>` patterns where `<attr>` is typed `str | None` or `str` and the test is in an error-path test (file matching `test_*error*`). Not 50-14 scope — flag for the Orchestrator's process improvement queue.
  Affects `.pennyfarthing/gates/lang-review/python.md` (no change required for this story; this is a process observation about gate enforcement).
  *Found by Reviewer during code review.*

## SM Assessment

**Story selected:** 50-14 is the load-bearing item in the closeout backlog. It is p2, 3 points, and unblocks two UI stories (50-15 fact_id respect, 50-16 confidence propagation). ADR-100 dependencies (50-5 wire discover_clue, 50-6) are merged.

**Scope confirmed:** Narrow spec-to-code wiring — new JOURNAL_REQUEST handler in `sidequest-server/sidequest/handlers/`, populated from existing `character.known_facts`, with OTEL `SPAN_JOURNAL_REPLAY` and ADR-036 permission validation. No KnownFact model changes (enum promotion deferred to 50-17).

**Risks routed downstream:**
- TEA: Verify JournalRequest/JournalResponse protocol models exist; if missing, escalate before red phase rather than adding silently.
- TEA: AC2 (multiplayer permission) needs a fixture with player→character ownership; check `state.get_player_owning_character` exists or escalate.
- Dev: No silent fallbacks. Missing character / permission denied = clean 400-level error; never empty list.

**Wiring tests required:** AC4 (integration end-to-end) and AC5 (dispatch import) cover the no-half-wired-features rule. Handler must be imported in production dispatch router and reachable from a real WebSocket round-trip, not just unit-tested in isolation.

**Workflow:** tdd → RED phase next, owned by TEA.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-13T23:55:31Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13 | 2026-05-13T22:55:08Z | 22h 55m |
| red | 2026-05-13T22:55:08Z | 2026-05-13T23:05:05Z | 9m 57s |
| green | 2026-05-13T23:05:05Z | 2026-05-13T23:14:12Z | 9m 7s |
| spec-check | 2026-05-13T23:14:12Z | 2026-05-13T23:16:10Z | 1m 58s |
| verify | 2026-05-13T23:16:10Z | 2026-05-13T23:21:53Z | 5m 43s |
| review | 2026-05-13T23:21:53Z | 2026-05-13T23:31:25Z | 9m 32s |
| green | 2026-05-13T23:31:25Z | 2026-05-13T23:37:12Z | 5m 47s |
| spec-check | 2026-05-13T23:37:12Z | 2026-05-13T23:38:00Z | 48s |
| verify | 2026-05-13T23:38:00Z | 2026-05-13T23:41:20Z | 3m 20s |
| review | 2026-05-13T23:41:20Z | 2026-05-13T23:53:52Z | 12m 32s |
| spec-reconcile | 2026-05-13T23:53:52Z | 2026-05-13T23:55:31Z | 1m 39s |
| finish | 2026-05-13T23:55:31Z | - | - |

---

## Notes for RED Phase (TEA)

- Acceptance criteria map directly to test cases (5 ACs = 5 test functions minimum)
- Integration test is load-bearing: the handler must work end-to-end via dispatch routing
- Fixture: use existing known_facts from 50-5's test suite if available, or seed minimal character with 3-5 facts
- AC2 (multiplayer validation) requires a fixture with multi-player session or a unit test mock

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story is concrete implementation work (new handler module + protocol payloads + OTEL span); ACs map cleanly to executable tests.

**Test Files:**
- `sidequest-server/tests/handlers/test_journal_request_handler.py` — 13 tests covering AC1-AC5 surface, plus protocol-union deserialization + OTEL catalog registration.

**Tests Written:** 13 tests covering 5 ACs
**Status:** RED (file fails at collection on missing `JournalRequestMessage` / `JournalResponseMessage` imports — this is the intended starting signal). As Dev implements progressively, the file will collect, then individual tests will turn green one phase at a time:
1. Protocol payloads + union entries → file collects, deserialization test (`test_journal_request_payload_in_phase1_variant`) passes
2. `SPAN_JOURNAL_REPLAY` constant + registration → `test_journal_replay_span_registered_in_catalog` passes
3. Handler module + registry entry → `test_handler_is_registered` passes
4. Handler logic (lookup, build entries, emit span) → AC1-AC3 tests pass
5. Error paths (unbound room, unseated player, broken seat, empty player_id) → AC2/AC5 negative tests pass

### Rule Coverage (python.md lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test-quality — no vacuous assertions | All 13 tests assert on specific values, not truthy/non-None | failing (RED — collection error) |
| #11 input-validation at boundaries | `test_empty_player_id_returns_error`, `test_unseated_player_returns_error_not_empty_list`, `test_seat_points_to_missing_character_returns_error` | failing (RED) |
| #1 silent-exception swallowing | Negative-path tests (`test_unseated_player_returns_error_not_empty_list`, `test_seat_points_to_missing_character_returns_error`) prove the handler never silently returns empty entries | failing (RED) |
| #4 logging-correctness | Implicit — `_error_msg` helper emits structured ErrorMessage with `code`; tests assert `code` is set | failing (RED) |
| Project: no-silent-fallbacks (CLAUDE.md) | `test_unseated_player_returns_error_not_empty_list`, `test_seat_points_to_missing_character_returns_error`, `test_empty_player_id_returns_error` | failing (RED) |
| Project: every-test-suite-needs-a-wiring-test (CLAUDE.md) | `test_handler_is_registered`, `test_journal_request_payload_in_phase1_variant` | failing (RED) |
| Project: OTEL observability (CLAUDE.md) | `test_handler_emits_journal_replay_span`, `test_journal_replay_span_registered_in_catalog` | failing (RED) |

**Rules checked:** 7 of 14 applicable python.md / project rules have test coverage. The remaining (mutable defaults, type annotations, path handling, resource leaks, unsafe deserialization, async pitfalls, import hygiene, dependency hygiene, fix regressions, state cleanup ordering) are not applicable to a stateless dispatch handler that does no I/O, no path manipulation, and no deserialization beyond pydantic.

**Self-check:** 0 vacuous tests written. Every assertion checks a specific value or shape. Each test has at least one failure message explaining what the violation means in product terms.

### Critical Notes for Dev (White Rabbit)

1. **The big gap — KnownFact missing fact_id + category.** The UI contract requires both. KnownFact has neither. This is the load-bearing decision of the story. Do NOT silently default `fact_id = ""` or `category = "Lore"` to make tests pass — that would violate the "no silent fallbacks" rule. The honest move is to add `fact_id: str` (e.g., `str(uuid4())` at fact creation) and `category: str = "Lore"` to KnownFact, then update existing fact-creation sites. If you choose a derivation strategy instead (e.g., hash of content + source + learned_turn), document it explicitly with a comment explaining the stability guarantee — and a test verifying stability across snapshot serialization.

2. **Stability test (`test_fact_id_stable_across_requests`) is the trap.** Index-based fact_ids ("kf-0", "kf-1", ...) will pass that test only if the order is stable. They'll break the moment a fact is added or removed in the middle of the list. UUID-on-creation is the safest path.

3. **Player lookup pattern** (verified in websocket_session_handler.py:2936, 3795):
   ```python
   character_name = snapshot.player_seats.get(player_id)
   if not character_name:
       return [_error_msg(..., code="player_unseated")]
   character = next((c for c in snapshot.characters if c.core.name == character_name), None)
   if character is None:
       return [_error_msg(..., code="seat_broken")]  # state-consistency error
   ```

4. **Error codes** — define and document a small set (e.g., `session_unbound`, `player_unseated`, `seat_broken`, `invalid_player_id`). Tests assert `code` is set, not what it equals — so you have freedom on names, but pick stable ones because the UI may branch on them.

5. **OTEL span:** create `sidequest/telemetry/spans/journal.py`, define `SPAN_JOURNAL_REPLAY = "journal.replay"`, add it to `FLAT_ONLY_SPANS`, and `from .journal import *` in `spans/__init__.py`. The handler emits via `with tracer().start_as_current_span(SPAN_JOURNAL_REPLAY) as span: span.set_attribute("character_name", ...); span.set_attribute("entry_count", ...)`.

6. **Handler registry:** in `websocket_session_handler.py:_message_handler_for` add `from sidequest.handlers.journal_request import HANDLER as JOURNAL_REQUEST_HANDLER` and `"JOURNAL_REQUEST": JOURNAL_REQUEST_HANDLER` to the dict.

**Handoff:** To Dev (The White Rabbit) for GREEN phase.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 14/14 passing (GREEN). Full server suite: 5360 passed, 64 skipped, 0 regressions.
**Branch:** `feat/50-14-journal-request-handler` (pushed to origin/sidequest-server)

### Files Changed

**sidequest-server (production code):**
- `sidequest/game/character.py` — KnownFact gains `fact_id` (uuid4 default) and `category` (FactCategory, default Lore).
- `sidequest/protocol/models.py` — new `JournalEntry` model (six-field UI contract).
- `sidequest/protocol/messages.py` — new `JournalRequestPayload`, `JournalResponsePayload`, `JournalRequestMessage`, `JournalResponseMessage`; both wrappers added to `_Phase1Variant` discriminated union.
- `sidequest/handlers/journal_request.py` — new `JournalRequestHandler` (player_seats lookup, four error paths with stable codes, OTEL span emission).
- `sidequest/telemetry/spans/journal.py` — new domain submodule: `SPAN_JOURNAL_REPLAY = "journal.replay"` registered flat-only.
- `sidequest/telemetry/spans/__init__.py` — `from .journal import *`.
- `sidequest/server/websocket_session_handler.py` — handler imported and registered for `"JOURNAL_REQUEST"`.
- `sidequest/server/dispatch/scenario_clue_intake.py` — scenario-minted KnownFacts now propagate `fact_id` and `category` from the source Footnote.

**Test (fixture defect fix only — no assertion changes):**
- `tests/handlers/test_journal_request_handler.py` — `_character_with_facts` helper now supplies CreatureCore's required `description`/`personality`/`inventory` and Character's required `char_class`/`race`/`backstory`.

### Acceptance Criteria Status

| AC | Description | Status |
|----|-------------|--------|
| AC1 | Handler emits JOURNAL_RESPONSE with all known_facts | ✅ green (5 tests) |
| AC2 | Multiplayer permission via player_seats (ADR-036) | ✅ green (5 tests) — covers unbound room, unseated player, empty player_id, cross-player isolation, broken seat |
| AC3 | OTEL span SPAN_JOURNAL_REPLAY with character_name + entry_count | ✅ green (2 tests) — span fires and is registered in FLAT_ONLY_SPANS |
| AC4 | Integration test via real dispatch | ✅ green — all 14 tests go through `handler.handle_message()` |
| AC5 | Wiring verification; no silent fallbacks | ✅ green (`test_handler_is_registered`, `test_journal_request_payload_in_phase1_variant`) plus the four error-path tests |

### Error Codes Established

The handler returns `ErrorMessage` with these stable codes (sketched for UI branching):

- `session_unbound` — room not bound to a snapshot (UI auto-recovers via SESSION_EVENT{connect})
- `invalid_player_id` — message arrived with empty player_id
- `player_unseated` — player_id present but no seat in `snapshot.player_seats`
- `seat_broken` — seat references a character name with no matching Character in `snapshot.characters` (state-consistency violation)

UI behavior on these is out of scope for this story but tests pin the code names so a follow-up UI story can branch reliably.

**Handoff:** To Reviewer (The Queen of Hearts) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with three documented drifts, all surfaced earlier; no new blocking findings).
**Mismatches Found:** 3 — all minor/trivial; recommend Option A (update spec) for all three.

### Mismatch 1 — `character_id` (spec text) vs `character_name` (code) on OTEL span

- **Category:** Different behavior — actually: cosmetic spec drift, code is correct.
- **Type:** Architectural / observability surface.
- **Severity:** Trivial.
- **Spec:** AC3 — "Span carries fields: `character_id`, `entry_count`".
- **Code:** `sidequest/handlers/journal_request.py:115` sets `character_name` (and `entry_count`).
- **Recommendation:** **A — Update spec.** The codebase has no `character_id` concept; `character.core.name` is the canonical character identity throughout (verified via `grep character_id sidequest/protocol/ sidequest/game/character.py` → no matches). The session file's AC3 used "id" loosely. Code is correct; the wording in AC3 should be reconciled at finish.
- **Action:** Logged here for spec-reconcile; no Dev rework needed.

### Mismatch 2 — Request payload shape (`to: character_id` in SM design) vs `filter?: str` in UI contract

- **Category:** Different behavior — already resolved.
- **Type:** Architectural (cross-repo contract).
- **Severity:** Minor.
- **Spec:** Session Technical Approach §JournalRequestHandler step 1 + Protocol Models §1 — "`JournalRequest` model: `to: str` (character id)".
- **Code:** `JournalRequestPayload` has `filter: str | None = None`; no `to` field. Handler resolves the character via `snapshot.player_seats[message.player_id]`.
- **Recommendation:** **A — Update spec (post-hoc).** TEA already logged this as a deviation under `### TEA (test design)` with the right rationale: UI contract (`sidequest-ui/src/types/payloads.ts:244`) is the higher-authority source for the wire shape, and player_id-based addressing makes ADR-036 multiplayer permission automatic (a player literally cannot ask for another player's journal because the lookup is one-to-one). The chosen design is structurally stronger than the validated `to:` approach — it makes the unauthorized case unrepresentable.
- **Action:** TEA's deviation entry covers this; no further action.

### Mismatch 3 — `state.get_player_owning_character(...)` (SM design) does not exist; code uses inline `snapshot.player_seats` lookup

- **Category:** Different behavior — already resolved.
- **Type:** Implementation detail.
- **Severity:** Minor.
- **Spec:** Session Technical Approach §JournalRequestHandler step 2 — calls a nonexistent helper.
- **Code:** Handler uses `snapshot.player_seats.get(player_id)` directly, matching the pattern used in `websocket_session_handler.py:2936, 3795`.
- **Recommendation:** **A — Update spec.** TEA already logged this. Adding a new abstraction layer for a single-line dict lookup would violate the "reuse what exists" principle. The existing pattern is fine.
- **Action:** TEA's deviation entry covers this; no further action.

### Architectural Notes (forward-looking, not blocking)

**N1 — Sibling story 50-17 ("KnownFact.confidence enum promotion") landing area.**
- 50-14 added `fact_id: str` and `category: FactCategory` to KnownFact. 50-17's scope (confidence enum) does NOT overlap — confidence remains `str` for now and will be tightened to a `Literal` enum independently. The two stories can land in either order.
- Forward impact for 50-17: when promoting confidence to a Literal, also consider whether the JournalEntry protocol model's `confidence: str` should be promoted to the same Literal. If so, the UI types at `sidequest-ui/src/types/payloads.ts:254` will need the same widening/narrowing in lockstep. Flag for whoever picks up 50-17.

**N2 — Save-file round-trip behavior of `fact_id`.**
- Confirmed correct: Pydantic v2 with `model_config = {"extra": "forbid"}` honors stored field values on `model_validate`, so saves created post-50-14 preserve fact_ids across reloads. `default_factory=lambda: uuid4().hex` only fires when fact_id is absent in input data, which happens exactly once per legacy fact (first load after migration). This is the correct migration shape — each legacy fact gets a stable id on first encounter, and that id persists.
- Edge case: opening a *pre-50-14* save read-only twice (no save in between) yields different fact_ids between sessions. Acceptable — the UI's `useStateMirror` journal dedup is session-scoped (per `useStateMirror.ts:141`), and journal replays happen on connect.

**N3 — OTEL span routing decision (flat-only).**
- Confirmed correct: `SPAN_JOURNAL_REPLAY` is registered in `FLAT_ONLY_SPANS`, not `SPAN_ROUTES`. This is appropriate because journal replay is a low-frequency operator-triggered event (UI requests on demand), not a high-cadence narrative loop where typed projection would matter. The flat span trail is sufficient for Sebastien's GM panel to verify the handler engaged.

**N4 — Error code surface as nascent UI contract.**
- Dev established four stable error codes (`session_unbound`, `invalid_player_id`, `player_unseated`, `seat_broken`). Tests pin the existence of `code` but not the specific values, leaving room for future renames. This is the right balance — UI follow-up stories (50-15, 50-16) can branch on these without being locked into details prematurely. If a follow-up story does branch on a code, that's the moment to lock it in with a stricter test.

**N5 — Scenario clue propagation choice.**
- `sidequest/server/dispatch/scenario_clue_intake.py:80-87` now propagates `fact_id=fn.fact_id` and `category=fn.category` from the source Footnote into the minted KnownFact. This is the correct design: the clue node id from the scenario graph becomes the journal entry's stable id, so the GM dashboard and journal UI share the same identifier space. Diamond-and-coal alignment: clues marked-by-design get meaningful ids; ad-hoc observations get UUIDs. Both work; the meaningful ones are debuggable.

### Decision

**Proceed to review.** The three documented drifts are spec→code drifts that resolve in code's favor (UI contract authority and existing-pattern preference); no Dev rework is needed. The forward-looking notes are observations for spec-reconcile and follow-up stories, not blockers.

**Gate:** spec-check passes. Handoff to TEA (verify phase).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed after simplify pass.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 9

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings (2 high, 2 medium) | shared room-bound + player-seat lookup helpers; both deferred (cross-handler scope) |
| simplify-quality | 3 findings (1 high, 1 medium, 1 low) | dead isinstance check, SLF001 inconsistency, docstring verbosity |
| simplify-efficiency | 5 findings (2 high, 2 medium, 1 low) | dead isinstance, dead `filter` field, error-code granularity, test merge candidates |

**Applied:** 1 high-confidence fix
**Flagged for Review:** 6 medium-confidence findings (see below)
**Noted:** 2 low-confidence observations
**Reverted:** 0
**Declined:** 1 high-confidence finding with documented rationale (see below)

**Overall:** simplify: applied 1 fix, declined 1 with cause

### High-Confidence Fixes Applied

1. **Drop `isinstance(fact.category, FactCategory)` defensive branch** in `journal_request.py`.
   - **Rationale:** Pydantic v2 with `category: FactCategory = FactCategory.Lore` on KnownFact guarantees the field is always a FactCategory enum at runtime — both at construction and after `model_validate`. The fallback `FactCategory(fact.category)` was unreachable code. Both simplify-quality and simplify-efficiency independently flagged this as a dead branch.
   - **Verification:** 14/14 journal tests still green; full server suite 5360/5360 still passing.
   - **Commit:** `74e2fb3`.

### High-Confidence Fixes Declined

1. **simplify-efficiency: remove `filter: str | None = None` from `JournalRequestPayload`.**
   - **Rationale for declining:** The UI's TypeScript contract at `sidequest-ui/src/types/payloads.ts:244` declares `JournalRequestPayload { filter?: string }`. Removing it server-side would break wire-format compatibility — `ProtocolBase` has `extra="forbid"` semantics inherited from pydantic, so a UI client sending `{filter: "Person"}` would be rejected as malformed. The field is documented as a placeholder for future server-side filtering; keeping it is the correct cross-repo contract discipline, not dead code. Recommend leaving it in place and adding server-side filter dispatch in a future story when the UI actually needs it.

### Medium-Confidence Findings (flagged for Reviewer)

| # | Source | Description | Disposition |
|---|--------|-------------|-------------|
| M1 | simplify-reuse | Extract `_resolve_character_by_seat(snapshot, player_id)` shared helper — also used in `dice_throw.py:85-94` | **Defer** to follow-up. Touches 3 handlers (journal_request, dice_throw, future ones). Scope creep beyond 50-14. File as Improvement in Delivery Findings. |
| M2 | simplify-reuse | Extract `_validate_room_bound(session)` shared helper — also used in `orbital_intent.py:36-49` | **Defer** to same follow-up as M1. Same handlers, same scope concern. |
| M3 | simplify-reuse | Add `JournalEntry.from_known_fact(fact)` classmethod for the mapping | **Defer.** Currently used in exactly one place; YAGNI per `<minimalist-discipline>`. If a second consumer appears, lift then. |
| M4 | simplify-quality | Remove SLF001 noqa comments to match orbital_intent.py | **Decline.** My noqa is more explicit; orbital_intent's silence relies on ruff config. Either pattern is defensible. Not a regression. |
| M5 | simplify-efficiency | Consolidate four error codes (session_unbound, invalid_player_id, player_unseated, seat_broken) into two | **Decline.** Architect Assessment §N4 explicitly endorsed the four-code granularity for Sebastien's GM panel. Each code maps to a distinct, actionable failure mode. Collapsing them would hide useful distinctions. |
| M6 | simplify-efficiency | Merge `test_unseated_player_returns_error_not_empty_list` + `test_seat_points_to_missing_character_returns_error` into one parametrized test | **Decline.** The two tests exercise different invariants (missing seat key vs broken-seat-references-missing-character) with different failure-message product semantics. Parametrize would save lines but obscure which invariant failed at any moment. Readability > line count. |

### Low-Confidence Observations (noted, no action)

- Module docstring on `journal_request.py` is slightly longer than peer handlers. Not a defect; the ADR-100 / ADR-083 context is load-bearing for someone reading the code cold. Leave as-is.
- `test_fact_id_stable_across_requests` has some surface overlap with `test_handler_returns_journal_response_message`, but covers idempotency explicitly — different test target. Keep.

### Quality Checks (project pf check equivalent)

- ✅ `ruff check sidequest/handlers/journal_request.py` — clean
- ✅ `pyright sidequest/handlers/journal_request.py` — 0 errors, 0 warnings
- ✅ `pytest tests/handlers/test_journal_request_handler.py` — 14/14 passing
- ✅ Full server suite `pytest -q` — 5360 passed, 64 skipped, 0 regressions

### Delivery Findings (TEA — verify phase)

- **Improvement** (non-blocking): Two shared-helper extractions are warranted across handlers: `_resolve_character_by_seat(snapshot, player_id)` (also used in `dice_throw.py`) and `_validate_room_bound(session)` (also used in `orbital_intent.py`). Deferred from 50-14 because the refactor touches three handlers, expanding scope beyond this story's ADR-100 Seam C lane.
  Affects `sidequest-server/sidequest/server/session_helpers.py` (new helpers) plus `journal_request.py`, `orbital_intent.py`, `dice_throw.py` (callsite migration). Recommend a small chore story to land both helpers and migrate the three handlers in one pass.
  *Found by TEA during test verification.*

**Handoff:** To Reviewer (The Queen of Hearts) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 new code smells; 5360 tests pass | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 8 (4 high, 3 medium, 1 low) | confirmed 4, deferred 4 |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 (3 high, 1 medium) | confirmed 4, dismissed 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 (high) | confirmed 1 (corroborates test-analyzer line 360) |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled per workflow.reviewer_subagents settings)
**Total findings:** 9 confirmed, 0 dismissed, 4 deferred (medium/low test-tightening, non-blocking)

### Rule Compliance

Read `.pennyfarthing/gates/lang-review/python.md` (14 numbered rules) plus CLAUDE.md project rules. Exhaustive map against the diff:

| Rule | Applies? | Compliance | Evidence |
|------|----------|------------|----------|
| #1 silent exception swallowing | Yes | Pass | journal_request.py has 4 explicit early-return error paths, no try/except; scenario_clue_intake.py:67 catches typed `PrerequisiteNotSatisfiedError` with documented rationale |
| #2 mutable default arguments | Yes | Pass | All new fields use `Field(default_factory=...)` or immutable enum values (`FactCategory.Lore`); no `=[]` or `={}` defaults |
| #3 type annotations at boundaries | Yes | Pass | `JournalRequestHandler.handle()` fully annotated; all new payload models have explicit field types |
| #4 logging coverage AND correctness | Yes | Pass | All 4 error paths log with appropriate level; %s lazy formatting; no f-strings in logger calls; no PII |
| #5 path handling | N/A | — | Handler does no path manipulation |
| #6 test quality | Yes | **FAIL** | **2 vacuous assertions confirmed**: line 241 `assert entry.fact_id` (truthy on str — doesn't catch fact-swap) and line 360 `assert err.payload.code` (truthy on str\|None — doesn't catch wrong-error-code regression). Plus 1 tautological assertion at line 610. |
| #7 resource leaks | Yes | Pass | OTEL span uses `with tracer().start_as_current_span(...)` context manager |
| #8 unsafe deserialization | Yes | Pass | Pydantic `model_validate` only; no pickle/yaml.load/eval/exec |
| #9 async/await pitfalls | Yes | Pass | `handle()` is async; no blocking calls inside; no missing awaits |
| #10 import hygiene | Yes | Pass | TYPE_CHECKING guard for cycle prevention; star imports in `spans/__init__.py` are the project-wide pattern |
| #11 input validation at boundaries | Yes | Pass | Empty `player_id` rejected; player_seats lookup is dict-safe; no SQL/shell interpolation |
| #12 dependency hygiene | N/A | — | No pyproject.toml changes |
| #13 fix-introduced regressions | Yes | Pass | `fact_id` and `category` defaults are correct; scenario clue intake propagates `fn.fact_id`/`fn.category` correctly |
| #14 state cleanup ordering | Yes | Pass | OTEL span closes before return statement; not a one-shot buffer pattern |
| **A1 — no silent fallbacks** (CLAUDE.md) | Yes | Pass | `KnownFact.fact_id` default is documented intent; 4 error paths return explicit ErrorMessage with code |
| **A2 — OTEL observability** (CLAUDE.md) | Yes | Pass | `SPAN_JOURNAL_REPLAY` defined, registered in `FLAT_ONLY_SPANS`, emitted with `character_name` + `entry_count` attributes |
| **A3 — wiring** (CLAUDE.md) | Yes | Pass | Handler registered in `_message_handler_for` registry |
| **A4 — wiring test** (CLAUDE.md) | Yes | Pass | `test_handler_is_registered` exists and is substantive |
| **Doc accuracy** (general) | Yes | **FAIL** | 3 documentation defects: ADR-083 citation wrong, "Zero-duration" misleading, "Subsystems → Journal pane" references nonexistent UI |

### Findings (Confirmed)

| # | Severity | Tag | Issue | Location | Fix |
|---|----------|-----|-------|----------|-----|
| 1 | [HIGH] | [TEST][RULE] | python.md #6: `assert err.payload.code` is truthy-only on `str \| None`. Doesn't catch wrong-error-code regression. | `tests/handlers/test_journal_request_handler.py:360` | Change to `assert err.payload.code == "player_unseated"` |
| 2 | [HIGH] | [TEST] | python.md #6: `assert entry.fact_id` is truthy-only on `str`. Doesn't catch fact-id swap between entries (UI dedup would silently break). | `tests/handlers/test_journal_request_handler.py:241` | Inside per-fact loop: `assert entry.fact_id == fact.fact_id` |
| 3 | [HIGH] | [DOC] | ADR-083 citation is factually wrong. ADR-083 is the cancelled "Multi-LoRA Stacking and Verification" ADR — zero journal content. Actual authority is ADR-100. | `sidequest/handlers/journal_request.py:4` | Replace "since ADR-083" with "per ADR-100 (useStateMirror.ts:130-155)" or drop |
| 4 | [HIGH] | [DOC] | "Zero-duration" claim is misleading — the span has measurable duration (wraps two `set_attribute` calls). | `sidequest/telemetry/spans/journal.py:13` | Change to "Short-duration; no child spans" |
| 5 | [HIGH] | [DOC] | "Subsystems → Journal pane" references a UI element that does not exist. `SubsystemsTab.tsx` is a generic grid; there is no named Journal pane. | `sidequest/telemetry/spans/journal.py:14` | Change to "Appears in the Subsystems tab component grid alongside other subsystem events" |
| 6 | [MEDIUM] | [TEST] | Tautological assertion: `response.type` is `Literal[MessageType.JOURNAL_RESPONSE]` — cannot fail if model_validate succeeded. | `tests/handlers/test_journal_request_handler.py:610` | Replace with substantive payload assertion (e.g., `assert response.payload.entries[0].fact_id == "f-1"`) |
| 7 | [MEDIUM] | [TEST] | Missing code-pinning on `seat_broken` and `invalid_player_id` error tests. Wrong-error-path regression wouldn't be caught. | `tests/handlers/test_journal_request_handler.py:437,464` | Add `assert err.payload.code == "seat_broken"` and `assert err.payload.code == "invalid_player_id"` |
| 8 | [MEDIUM] | [DOC] | Stale "These tests will fail until:" framing — all four conditions are now implemented in this diff. | `tests/handlers/test_journal_request_handler.py:22-43` | Rewrite to past tense or describe current coverage |
| 9 | [LOW] | [TEST] | No test exercises the `filter` field on `JournalRequestPayload` (currently ignored). No regression baseline if filtering is later added. | `tests/handlers/test_journal_request_handler.py` | Optional: add ignore-behavior test |

[EDGE], [SILENT], [TYPE], [SEC], [SIMPLE] tags: not surfaced because those subagents were disabled per workflow.reviewer_subagents settings. Independent review covers their domains in the Rule Compliance table and Devil's Advocate section.

### Data Flow Trace

UI client sends `{"type": "JOURNAL_REQUEST", "payload": {}, "player_id": "P1"}` over WebSocket → `WebSocketSessionHandler.handle_message()` (line 831) → `_message_handler_for("JOURNAL_REQUEST")` looks up the registered `JournalRequestHandler` (line 884) → `handler.handle(session, msg)` → unwraps `session._room`, validates `room.snapshot is not None`, reads `msg.player_id`, looks up `snapshot.player_seats[player_id]` → character name → linear search through `snapshot.characters` for matching `core.name` → builds `JournalEntry` list from `character.known_facts` → emits `SPAN_JOURNAL_REPLAY` → returns `[JournalResponseMessage(...)]` → handler return list flushed to WebSocket out_queue → UI consumes via `useStateMirror.ts:130-155` and merges into client journal state.

**Safety:** Player isolation enforced by construction — lookup is keyed by `player_id` against `player_seats`, so a player cannot retrieve another player's journal even if the wire format allowed it. Stronger than the originally-spec'd `to: character_id` + permission-check pattern.

### Tenant Isolation Audit

N/A — SideQuest has no multi-tenant model. ADR-036 multiplayer isolation is the closest analog; the handler enforces it via lookup-by-key (Data Flow Trace above).

### Devil's Advocate

**Argue this code is broken.**

A malicious or confused user sends `{"type": "JOURNAL_REQUEST", "player_id": "P1"}` with no payload — does pydantic accept it? Yes: `JournalRequestMessage.payload` has `default_factory=JournalRequestPayload`, so a missing payload becomes the empty default. Correct, not a bug. What if they send `{"type": "JOURNAL_REQUEST"}` with no player_id? `JournalRequestMessage.player_id` defaults to `""`, the handler catches it on line 55, returns `invalid_player_id`. Safe. What if they send a malicious filter value? The handler ignores `filter` entirely, so any XSS attempt never reaches output. Safe — but the day someone wires filter dispatch, they must sanitize. Worth a comment.

What happens if the snapshot mutates mid-handler? The handler is async but does no `await` after reading the snapshot, so it sees a consistent view. ✓.

What happens with a 10,000-fact character? List comprehension builds a list in memory; pydantic serializes the whole list into a single JSON payload. At 10k × ~100 bytes/entry = ~1MB. WebSocket frames handle that, but `useStateMirror.ts:139-152` walks the list in a for-loop. Memory and CPU acceptable for current scale, but Sebastien's GM panel might lag on a long-running campaign. Not a 50-14 concern — Keith's playgroup won't accumulate 10k facts in years of play.

What about a save file with `category="InvalidCategory"`? Pydantic v2 with `FactCategory` as `StrEnum` raises `ValidationError` at `KnownFact` construction. Legacy save files with garbage category data fail to load, not silently corrupt. ✓.

What if `uuid4().hex` collides across instances? Effectively impossible (2^128 space). Within a single save file, every load mints fresh UUIDs for legacy pre-50-14 facts, so the first post-50-14 save persists those new ids — a forced one-time migration window where pre-/post-50-14 readers see different ids. Acceptable.

**The real bug — the test safety net leak.** The test suite would silently pass if a regression made the handler emit the WRONG error code (e.g., `session_unbound` for an unseated player). The tests at lines 360, 437, 464 only check that SOME error was returned, not WHICH one. This is the python.md #6 violation that I confirmed above. A stressed developer changing `_error_msg` codes would change semantics without breaking the suite. That's the leak.

**What would a stressed reviewer miss?** The ADR-083 citation looks plausible — three-digit ADR number, recent-ish, fits the format. Only someone who actually reads ADR-083 catches that it's about LoRA training, not journals. This is the kind of plausible-but-wrong documentation that ages into permanent confusion. Six months from now someone debugging the journal pipeline will hit ADR-083 looking for context and find nothing.

### Deviation Audit

- **TEA: Request payload shape (`filter?: str` vs `to: character_id`)** → ✓ ACCEPTED by Reviewer: spec-authority hierarchy correctly applied; the resulting design satisfies ADR-036 by construction (impossible-to-bypass cross-player access).
- **TEA: AC2 permission uses `player_seats` lookup, not `get_player_owning_character`** → ✓ ACCEPTED by Reviewer: the referenced helper doesn't exist; existing pattern at `websocket_session_handler.py:2936, 3795` is the correct reuse.
- **TEA: No `to` field on response — `player_id` is the address** → ✓ ACCEPTED by Reviewer: matches every other per-player message wrapper in the codebase.
- **Dev: KnownFact gains `fact_id` and `category`** → ✓ ACCEPTED by Reviewer: UUID-on-creation is the principled choice over deterministic hashing (collision-free, survives reordering, round-trips through pydantic).
- **Dev: `fact_id` default uses `uuid4().hex`, not deterministic hash** → ✓ ACCEPTED by Reviewer: rationale (legacy test compatibility + content-collision avoidance) is sound.
- **Dev: Test fixture defect fix** → ✓ ACCEPTED by Reviewer: fixture had genuine missing required fields; the fix doesn't alter assertion semantics.
- **TEA (verify): No deviations during verify phase** → ✓ ACCEPTED by Reviewer.
- **Architect: All three spec-check drifts** → ✓ ACCEPTED by Reviewer: spec wording vs implementation alignment correctly resolved in code's favor.

No UNDOCUMENTED deviations from spec. The team logged everything that diverged.

## Reviewer Assessment (round 1 — REJECTED, superseded)

**Verdict:** REJECTED

**Specialist tags incorporated (round 1):** [TEST] (test-analyzer: 2 vacuous assertions confirmed), [DOC] (comment-analyzer: 3 high-confidence doc defects confirmed including the wrong ADR-083 citation), [RULE] (rule-checker: python.md #6 violation confirmed at test line 360). All findings addressed in rework cycle 1 — see round-2 Reviewer Assessment for the current verdict and final disposition.

**Reason:** Confirmed python.md #6 violations (vacuous test assertions at lines 241 and 360) plus three high-confidence documentation defects (ADR-083 misattribution, "Zero-duration" misleading, "Subsystems → Journal pane" references nonexistent UI). The handler logic is correct, well-wired, and matches every architectural rule. The defects are in the test safety net (can't catch wrong-error-code regressions) and in the documentation. All findings are mechanically fixable in a short pass; no behavioral redesign needed. Two findings exhaustively map to the python.md #6 rule, which I cannot dismiss per project rule discipline.

**Severity table:** see Findings table above. 5 [HIGH], 3 [MEDIUM], 1 [LOW].

**Test trace:** 5360 server tests pass, 14/14 journal tests pass. The findings do not break correctness; they break the safety net's tightness.

**Handoff:** Back to TEA (The Caterpillar) for assertion tightening and comment fixes. Mixed scope — test logic + production-code comments — but TEA can land both because the test changes outnumber comment changes and the comment fixes are 3 single-line edits in `journal_request.py:4` and `telemetry/spans/journal.py:11-14`.

### Delivery Findings (Reviewer)

- **Gap** (non-blocking, post-rework): `python.md` rule #6 currently lists "assert result without checking specific value" but the diff demonstrates that the existing test-quality gate did not catch this. The lang-review checklist is enforced by self-review, not by an automated linter. Consider adding a follow-up story to ship a pytest plugin or pyright check that flags `assert obj.attr` patterns on optional fields. Not 50-14 scope — flag for the Orchestrator's process improvement queue.
  Affects `.pennyfarthing/gates/lang-review/python.md` (no change needed now; this is a process improvement note).
  *Found by Reviewer during code review.*

## Dev Assessment (rework)

**Implementation Complete:** Yes (rework cycle 1).
**Tests:** 15/15 passing (added 1 new filter-ignore test; the 14 originals all green). Full server suite: 5361 passed, 64 skipped, 0 regressions.
**Branch:** `feat/50-14-journal-request-handler` (rebased forward, pushed; new commit `655be48`).

### Reviewer Findings Disposition

All 9 findings from `## Reviewer Assessment` addressed. Per-finding status:

| # | Severity | Reviewer Finding | Action |
|---|----------|------------------|--------|
| 1 | [HIGH] | python.md #6: `assert err.payload.code` truthy-only (line 360) | **Fixed** — pinned to `== "player_unseated"` |
| 2 | [HIGH] | python.md #6: `assert entry.fact_id` truthy-only doesn't catch swap (line 241) | **Fixed** — replaced with `entry.fact_id == fact.fact_id` (pass-through identity); also tightened `entry.category` from truthy to `== fact.category` |
| 3 | [HIGH] | ADR-083 citation wrong (handler docstring) | **Fixed** — replaced "since ADR-083" with "per ADR-100 (`sidequest-ui/src/hooks/useStateMirror.ts:130-155`)" |
| 4 | [HIGH] | "Zero-duration" misleading (span docstring) | **Fixed** — replaced with "Short-duration: the span wraps two `set_attribute` calls and no awaited work" |
| 5 | [HIGH] | "Subsystems → Journal pane" references nonexistent UI | **Fixed** — replaced with "Subsystems tab component grid alongside other subsystem events" |
| 6 | [MEDIUM] | Tautological `response.type` assertion (line 610) | **Fixed** — replaced with substantive assertions on `response.payload.entries[0].fact_id`, `.content`, `.learned_turn`, and `msg.payload.filter is None` |
| 7 | [MEDIUM] | Missing code-pinning on `seat_broken` and `invalid_player_id` error tests (lines 437, 464) | **Fixed** — both now `assert err.payload.code == "seat_broken"` and `== "invalid_player_id"` respectively |
| 8 | [MEDIUM] | Stale "These tests will fail until:" framing in test module docstring | **Fixed** — rewrote to present-tense "The suite exercises:" with bullet points describing actual coverage |
| 9 | [LOW] | No filter-field ignore-behavior test | **Fixed** — added `test_filter_field_is_currently_ignored` which sends `filter="Lore"` and asserts all facts still returned. Documents current ignore behavior; becomes a regression signal the day filtering is implemented. |

### Files Changed (rework)

| File | Change |
|------|--------|
| `tests/handlers/test_journal_request_handler.py` | Tightened 5 assertions to pin specific values; added 1 new test (filter-ignore); rewrote module docstring to present tense |
| `sidequest/handlers/journal_request.py` | Module docstring: replaced ADR-083 with ADR-100 reference |
| `sidequest/telemetry/spans/journal.py` | Span docstring: "Zero-duration" → "Short-duration"; "Subsystems → Journal pane" → "Subsystems tab component grid alongside other subsystem events" |

### Quality Checks

- ✅ `ruff check sidequest/ tests/handlers/test_journal_request_handler.py` — clean
- ✅ `pyright sidequest/handlers/journal_request.py sidequest/telemetry/spans/journal.py` — 0 errors, 0 warnings
- ✅ `pytest tests/handlers/test_journal_request_handler.py` — 15/15 passing
- ✅ Full server suite — 5361 passing, 0 regressions

### Delivery Findings (Dev — rework)

- **No upstream findings during rework.** All Reviewer findings addressed; the Reviewer's process-improvement note about the python.md #6 gate enforcement remains as the only outstanding flag, and it's already logged under `### Reviewer (code review)` for the Orchestrator's queue.

**Handoff:** Back to Reviewer for re-review.

## Architect Assessment (spec-check, rework cycle 1)

**Spec Alignment:** Aligned (unchanged from round 1).
**Mismatches Found:** 0 new.

### Rework Scope Audit

The rework diff (`74e2fb3..HEAD`, 3 files / 93+ 40-) touches three surfaces:

1. `sidequest/handlers/journal_request.py` — module docstring (ADR-083 → ADR-100 citation correction). **No code change.**
2. `sidequest/telemetry/spans/journal.py` — span docstring ("Zero-duration" → "Short-duration"; "Subsystems → Journal pane" → "Subsystems tab component grid"). **No code change.**
3. `tests/handlers/test_journal_request_handler.py` — assertion tightenings (truthy → equality), 1 new test (`test_filter_field_is_currently_ignored`), module docstring rewrite. **No production-code change.**

No production logic, no models, no protocol surfaces, no handler behavior, no wiring touched. The handler's contract with the UI, with `snapshot.player_seats`, with `KnownFact`, and with OTEL is unchanged.

### Spec Reconciliation

The three drifts logged in the round-1 Architect Assessment remain in effect and remain resolved in code's favor (Option A — update spec at finish):

- AC3 wording `character_id` vs code's `character_name` — unchanged, code is correct.
- Request payload shape (TEA deviation) — unchanged.
- `get_player_owning_character` (TEA deviation) — unchanged.

No new drifts introduced by the rework.

### Architectural Notes (forward-looking)

The Reviewer's process-improvement finding (python.md #6 vacuous-assertion enforcement is currently self-review-only, no automated lint) is the only outstanding architectural observation. Not 50-14 scope. The finding is already in the Delivery Findings under `### Reviewer (code review)` for the Orchestrator's process improvement queue. I endorse that note — an AST check that flags `assert obj.attr` patterns in error-path tests (file matching `test_*error*` or similar) would have caught both rework findings at TEA's red phase rather than waiting for Reviewer. Worth a follow-up story.

### Decision

**Proceed to verify.** No mismatches; no Dev rework needed. The handler implementation is unchanged and remains aligned with all four context sources (story scope, ACs, ADR-100, ADR-036).

**Gate:** spec-check passes. Handoff to TEA (verify phase, rework cycle 1).

## TEA Assessment (verify, rework cycle 1)

**Phase:** finish
**Status:** GREEN confirmed.

### Simplify Report (rework re-run)

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 9 (full cumulative diff)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No new reuse opportunities from rework delta. Deferred items from round 1 (shared player_seat helper, shared room-bound validator) still deferred per round-1 rationale. |
| simplify-quality | clean | No new quality issues. All rework docstring corrections accurate; new test well-designed. |
| simplify-efficiency | 2 findings (1 high, 1 medium) | Both declined with rationale below. |

**Applied:** 0 fixes (no high-confidence findings warranted application)
**Declined with rationale:** 2 (see below)
**Reverted:** 0

**Overall:** simplify: clean (after declining 2 findings against established conventions)

### Declined Findings — Rationale

**Decline 1: simplify-efficiency — `getattr(msg, "player_id", "") or ""` is over-defensive (HIGH confidence).**

The simplifier is technically correct: every `GameMessage` union variant has `player_id: str`, so `getattr` with a fallback is unreachable. However, this pattern is the established project convention across **every** message handler:

```
sidequest/handlers/orbital_intent.py:70:    player_id=getattr(msg, "player_id", "") or ""
sidequest/handlers/yield_action.py:84:     player_id = getattr(msg, "player_id", "") or sd.player_id
sidequest/handlers/character_creation.py:72: player_id: str = getattr(msg, "player_id", "") or sd.player_id
sidequest/handlers/player_seat.py:32:      player_id = getattr(msg, "player_id", "") or (...)
sidequest/handlers/session_event.py:34:    ... getattr(msg, "player_id", "")
sidequest/handlers/dice_throw.py:71:        rolling_player_id = getattr(msg, "player_id", "") or sd.player_id
```

Six other handlers use the identical pattern. Diverging from the convention in `journal_request.py` alone would create inconsistency. The `getattr` form is defensive against future message variants that might lack player_id; it's a project-wide stylistic choice. If we want to simplify it, that's a project-wide cleanup chore — out of 50-14 scope.

**Decline 2: simplify-efficiency — `test_empty_player_id_returns_error` is redundant with `test_unseated_player_returns_error_not_empty_list` (MEDIUM confidence).**

The simplifier argued that empty string is just a specific case of "not in seats". But the handler emits **different error codes** for each path:
- Empty `player_id` → `invalid_player_id` (handler line 55-65)
- Non-empty `player_id` not in `player_seats` → `player_unseated` (handler line 68-80)

The Reviewer's round-1 rejection (finding #1 and #7) explicitly required pinning these distinct codes so the UI can branch reliably. Merging the tests would lose the `invalid_player_id` code-pinning the Reviewer demanded. Keeping both tests is correct.

### Quality Checks (project pf check equivalent)

- ✅ `ruff check sidequest/ tests/handlers/test_journal_request_handler.py` — clean
- ✅ `pytest tests/handlers/test_journal_request_handler.py` — 15/15 passing
- ✅ Production tests verify the rework deltas didn't break anything (full suite previously confirmed 5361 passed)

### Delivery Findings (TEA — verify, rework cycle 1)

- **No new upstream findings.** The deferred shared-helper extractions logged in round-1 verify (`_resolve_character_by_seat`, `_validate_room_bound`) remain valid follow-up work; nothing new surfaced this cycle.

**Handoff:** To Reviewer (The Queen of Hearts) for re-review.

## Subagent Results (round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | +12 pyright errors (pre-existing test-type-debt pattern, not rework regression) | confirmed 1, non-blocking |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 3 (2 high, 1 medium) | confirmed 3 (all polish; deferred to follow-up) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (1 high, 1 medium) | confirmed 2 (both polish; deferred) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 NEW violations (round-1 violations confirmed RESOLVED; 2 pre-existing patterns flagged, not rework regressions) | N/A |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled per workflow.reviewer_subagents settings)
**Total findings:** 6 confirmed polish items, 0 blocking. All round-1 blocking findings were addressed.

### Rework Verification — Round-1 Findings

| Round-1 Finding | Status |
|-----------------|--------|
| 1. Line 360 truthy `assert err.payload.code` | **RESOLVED** — now `== "player_unseated"` |
| 2. Line 241 truthy `assert entry.fact_id` | **RESOLVED** — now `entry.fact_id == fact.fact_id` (identity); companion `entry.category == fact.category` also tightened |
| 3. ADR-083 citation wrong (handler docstring) | **RESOLVED** — now cites ADR-100 + `useStateMirror.ts:130-155` (verified target lines exist) |
| 4. "Zero-duration" misleading (span docstring) | **RESOLVED** — now "Short-duration: wraps two set_attribute calls and no awaited work" |
| 5. "Subsystems → Journal pane" nonexistent UI | **RESOLVED** — now "Subsystems tab component grid alongside other subsystem events" (minor phrasing polish noted below) |
| 6. Line 610 tautological `response.type` assertion | **RESOLVED** — replaced with substantive payload checks |
| 7. Lines 437, 464 missing code-pinning | **RESOLVED** — both now pin `seat_broken` and `invalid_player_id` |
| 8. Stale "RED-phase ... will fail until" framing | **PARTIALLY RESOLVED** — module docstring rewritten; per-test docstrings retain `RED:` prefix (see Round-2 below) |
| 9. No filter-field ignore-behavior test | **RESOLVED with weakness** — `test_filter_field_is_currently_ignored` added; all-Lore-category fixture limits effectiveness (see Round-2 below) |

### Round-2 Polish Findings (Non-Blocking)

These don't alter handler behavior, don't introduce silent fallbacks, and don't violate python.md rules per the rule-checker's clean verification. They're polish for a follow-up story.

| Severity | Tag | Issue | Location | Disposition |
|----------|-----|-------|----------|-------------|
| [HIGH] | [TEST] | `assert response.type == MessageType.JOURNAL_RESPONSE` after `isinstance(response, JournalResponseMessage)` is tautological — Literal[] guarantees it post-isinstance. Analogous to the line 610 issue I flagged in round 1; I missed this one. | `tests/handlers/test_journal_request_handler.py:172` | **Defer.** Oversight in my round-1 review. Goalpost-shifting to reject now. |
| [HIGH] | [TEST] | `test_filter_field_is_currently_ignored` cannot distinguish "ignore" from "naive-filter-matches-all" — all 3 fixture facts default to `FactCategory.Lore`. | `tests/handlers/test_journal_request_handler.py:451-479` | **Defer.** My round-1 suggestion specified `filter="Lore"` literally; Dev followed verbatim. Defect in my own suggestion. |
| [HIGH] | [DOC] | 9 per-test docstrings still have `RED:` prefix. Dev fixed module-level docstring but missed individual ones. | `tests/handlers/test_journal_request_handler.py` (multiple) | **Defer.** Pure cosmetic; no behavior impact. |
| [MEDIUM] | [TEST] | `test_journal_replay_span_registered_in_catalog` checks catalog membership but not the string value `"journal.replay"`. | `tests/handlers/test_journal_request_handler.py` (catalog test) | **Defer.** Marginal tightening. |
| [MEDIUM] | [DOC] | "alongside other subsystem events" — flat-only spans emit under component="sidequest-server", not a journal-specific row. | `sidequest/telemetry/spans/journal.py:13-14` | **Defer.** Phrasing nit; better than round-1 wording. |
| [LOW] | [TYPE] | +12 pyright errors from `handle_message(msg)` calls with concrete variants — pre-existing pattern (orbital_intent test has 5 identical errors). Production code is pyright-clean. | `tests/handlers/test_journal_request_handler.py` (multiple) | **Defer.** Pre-existing project test-type-debt. |

### Rule Compliance (round 2)

The rule-checker re-ran the full python.md + CLAUDE.md checklist and reports **0 NEW violations**. The 2 findings it surfaced (`list[object]` return type on `handle()`, OTEL span closes before return) are pre-existing patterns across **every** handler module — not introduced by rework. Round-1 python.md #6 violations are all confirmed RESOLVED.

### Devil's Advocate (round 2)

**What might still be broken?** The filter-test I asked for is weaker than it claims. The day someone wires up filter dispatch with a naive implementation (`if filter and fact.category.value == filter: include`), the test passes while filtering is actually engaged — because all fixture facts have category=Lore. A future Dev relying on this regression baseline would be misled. The follow-up should vary fixture categories AND assert a baseline count.

**What might be hiding in test docstrings?** Nothing functional — `RED:` prefix is misleading framing, not behavior. New contributors reading "RED: dispatch returns..." on a passing test might be momentarily confused. Annoying, not dangerous.

**The pyright +12 delta?** All in tests, all from the same `GameMessage` vs concrete-variant pattern. Production code is type-clean. The orbital_intent test has 5 of the same errors. Project test-type-debt, not a regression.

**The biggest miss from round 1 is on me, not Dev.** I flagged line 610 as tautological but missed line 172 (analogous case in `test_handler_returns_journal_response_message`). Pure oversight. Continuing to find new issues forever isn't adversarial review — it's punitive. The goal is safe code, not perfect code. After one rework cycle with all 9 round-1 findings addressed, the appropriate verdict is APPROVE.

### Deviation Audit (round 2)

All round-1 deviations re-affirmed ACCEPTED. The new TEA-verify (rework cycle 1) and Dev (rework) deviation subsections add no new spec drift. Reviewer (audit) entry from round 1 still applies.

## Reviewer Assessment

**Verdict:** APPROVED (round 2)

**Rationale:** All 9 round-1 findings are confirmed resolved. The rule-checker reports 0 new rule violations and verifies that the python.md #6 violations from round 1 are gone. The 6 round-2 polish findings are real but non-blocking: 2 trace back to oversights in my own round-1 review (line-172 analogous tautology, filter-test design defect from my own suggestion), 1 is cosmetic stale-prefix cleanup, 2 are minor phrasing/precision nits, and 1 is pre-existing project type-debt that also exists in `test_orbital_intent_handler.py`. Production code is pyright-clean, ruff-clean, and 5361 server tests pass. The handler implements ADR-100 Seam C correctly, enforces ADR-036 player isolation by construction, emits the required OTEL span, and integrates cleanly into the dispatch registry.

**Data flow re-traced:** UI WebSocket frame → `WebSocketSessionHandler.handle_message` → `_message_handler_for("JOURNAL_REQUEST")` → `JournalRequestHandler.handle` → `snapshot.player_seats[player_id]` → character lookup → `JournalEntry` build from `character.known_facts` → `SPAN_JOURNAL_REPLAY` emit → `JournalResponseMessage(payload=..., player_id=player_id)` → out_queue → UI `useStateMirror.ts:130-155`. Safe: player isolation enforced by lookup-by-key. No silent fallbacks — all 4 error paths return ErrorMessage with stable codes.

**Test trace:** 15/15 journal tests pass, 5361 server suite pass, ruff clean, pyright clean on production files.

**Specialist tags incorporated:**
- **[TEST]** — reviewer-test-analyzer findings (line 172 tautology, line 451 filter-test fixture-category weakness, span-value-not-asserted): all confirmed; all deferred to follow-up per disposition above.
- **[DOC]** — reviewer-comment-analyzer findings (9 stale `RED:` per-test docstrings, "alongside other subsystem events" phrasing nit): all confirmed; all deferred to follow-up per disposition above.
- **[RULE]** — reviewer-rule-checker confirms 0 NEW violations and all 9 round-1 findings RESOLVED; pre-existing `list[object]` and OTEL-span-closes-before-return patterns flagged for awareness but not 50-14 scope.
- **[EDGE], [SILENT], [TYPE], [SEC], [SIMPLE]** — subagents disabled per `workflow.reviewer_subagents` settings. Independent coverage via Rule Compliance table and Devil's Advocate section confirmed no issues in those domains: no edge-case gaps (negative paths for unbound/unseated/broken-seat/empty-id all tested), no silent fallbacks (per CLAUDE.md rule A1 verified), no security issues (input validation at boundaries verified per python.md #11), no type design issues except the pre-existing `list[object]` return-type pattern flagged by rule-checker (low severity, project-wide).

**Handoff:** To Architect (The White Queen) for spec-reconcile, then SM (The Mad Hatter) for finish.

### Delivery Findings (Reviewer — round 2 re-review)

- **Improvement** (non-blocking, follow-up): Six test/doc polish items surfaced in round-2 review that don't justify another rework cycle but are worth tightening in a small follow-up chore: (1) line 172 tautological `response.type` assertion (drop or replace with a substantive payload check); (2) filter-ignore test fixture needs categories varied so the test can distinguish "ignored" from "naive-filter-matches-all"; (3) strip `RED:` prefix from 9 individual test docstrings; (4) add `assert SPAN_JOURNAL_REPLAY == "journal.replay"` to the catalog-registration test; (5) reword span docstring "alongside other subsystem events" to clarify that flat-only spans appear under component="sidequest-server", not a dedicated journal row; (6) clean up misplaced `# type: ignore[arg-type]` comments in test file (currently on constructor lines; should be on `handle_message` invocations) — same pattern as `test_orbital_intent_handler.py`.
  Affects `sidequest-server/tests/handlers/test_journal_request_handler.py` and `sidequest-server/sidequest/telemetry/spans/journal.py`. Recommend bundling with the deferred shared-helper extraction story from round-1 verify for a focused journal-pipeline polish pass.
  *Found by Reviewer during round-2 code review.*