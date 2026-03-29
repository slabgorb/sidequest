---
story_id: "4-6"
jira_key: ""
epic: "4"
workflow: "tdd"
---

# Story 4-6: TTS voice routing — map character/NPC IDs to voice presets from genre pack config

## Story Details
- **ID:** 4-6
- **Workflow:** tdd
- **Stack Parent:** 4-1 (daemon client)
- **Points:** 3
- **Priority:** p1

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T18:46:39Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26T18:28:35Z | 2026-03-26T18:30:00Z | - |
| red | 2026-03-26T18:30:00Z | 2026-03-26T18:35:35Z | 5m 35s |
| green | 2026-03-26T18:35:35Z | 2026-03-26T18:38:00Z | 2m 25s |
| review | 2026-03-26T18:38:00Z | 2026-03-26T18:46:39Z | 8m 39s |
| finish | 2026-03-26T18:46:39Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): Story context describes Rust types (`pub enum TtsModel`, `pub struct VoicePreset`) but implementation target is the Python daemon repo (`sidequest-daemon`). Tests written in Python using Python conventions (Pydantic/dataclass style). Affects `sprint/context/context-story-4-6.md` (context should clarify target language). *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **New module instead of extending existing router**
  - Spec source: context-story-4-6.md, Technical Approach
  - Spec text: "VoiceRouter struct with route() method" (implies single router)
  - Implementation: Tests target new `tts_routing.py` module with `TtsVoiceRouter` class, alongside existing `router.py`/`VoiceRouter`
  - Rationale: Existing `VoiceRouter` already handles narrative parsing + preset registry. New `TtsVoiceRouter` adds typed model enum (`TtsModel`), assignment source tracking (`AssignmentSource`), and speaker identification — different responsibilities. Avoids breaking existing working code.
  - Severity: minor
  - Forward impact: Dev must decide whether to integrate with or replace existing `VoiceRouter`

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story has 10 acceptance criteria covering voice routing, type safety, and speaker identification

**Test Files:**
- `sidequest-daemon/tests/voice/test_tts_voice_routing.py` — 44 tests (35 failing, 9 passing)
- `sidequest-daemon/sidequest_daemon/voice/tts_routing.py` — stubs only

**Tests Written:** 44 tests covering 10 ACs
**Status:** RED (35 failing — ready for Dev)

### AC Coverage

| AC | Tests | Count |
|----|-------|-------|
| Narrator routing | TestTtsVoiceRouterNarratorRouting | 3 |
| Known NPC routing | TestTtsVoiceRouterKnownNpc | 4 |
| Default fallback | TestTtsVoiceRouterDefaultFallback | 4 |
| Model typing | TestTtsModel | 4 |
| Speed preserved | test_preset_has_speed, narrator/npc speed tests | 4 |
| Source tracking | TestAssignmentSource + source assertion tests | 5 |
| Speaker detection | TestIdentifySpeaker | 6 |
| Genre pack load | TestTtsVoiceRouterFromGenrePack | 3 |
| Empty config | TestTtsVoiceRouterEmptyConfig | 2 |
| Test coverage | Self-check + TestLangReviewRules | 4 |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 mutable defaults | test_voice_preset_no_mutable_default | failing |
| #3 type annotations | test_identify_speaker_type_annotations, test_from_genre_pack_type_annotations | 1 passing, 1 failing |
| #6 test quality | Self-check: fixed 2 vacuous tests (speed rejection) | passing |
| #8 unsafe deserialization | test_tts_model_rejects_invalid_value | passing |

**Rules checked:** 4 of 13 applicable python lang-review rules have test coverage
**Self-check:** 2 vacuous tests found and fixed (speed validation tests were catching TypeError from missing init instead of ValueError from validation)

**Handoff:** To Dev (Loki Silvertongue) for implementation

### Dev (implementation)
- No deviations from spec.

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): `from_genre_pack()` and `_parse_preset()` raise bare KeyError/ValueError on malformed config. Wrapping in a domain error with genre pack context would improve debuggability. Affects `sidequest-daemon/sidequest_daemon/voice/tts_routing.py` (add try/except with structured re-raise). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `route()` coerces empty/None character_id to sentinel string `"unknown"` (line 111). Consider validating non-empty in `Speaker.character()` or raising in `route()`. Affects `sidequest-daemon/sidequest_daemon/voice/tts_routing.py` (add guard). *Found by Reviewer during code review.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-daemon/sidequest_daemon/voice/tts_routing.py` - Full implementation of TtsVoiceRouter, VoicePreset, VoiceAssignment, Speaker, and identify_speaker

**Tests:** 44/44 passing (GREEN)
**Branch:** feat/4-6-tts-voice-routing (pushed)

**Handoff:** To next phase (review)

## TEA Verify Assessment

**Phase:** finish
**Status:** GREEN confirmed — 44/44 tests passing

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (tts_routing.py, test_tts_voice_routing.py)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 6 findings | VoicePreset/Speaker/from_genre_pack overlap with existing voice modules — all dismissed (different domain/scope per story ACs) |
| simplify-quality | timeout — no result | Agent ran but result not parseable |
| simplify-efficiency | 4 findings | Enum/property tests called redundant, router tests could be parameterized — all dismissed (tests are RED phase contract, readability > brevity) |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings requiring action
**Noted:** 2 low-confidence observations (VoiceAssignment could be NamedTuple; extract conftest fixture)
**Reverted:** 0

**Dismissal rationale:**
- Reuse findings dismissed because story context explicitly defines new types (TtsModel, AssignmentSource, Speaker) with different semantics than existing protocol.VoicePreset and NarrativeSegmentParser. Merging would violate story scope.
- Efficiency findings dismissed because test method names map 1:1 to ACs, which is the TEA contract. Parameterization obscures AC traceability.

**Quality Checks:** All 44 tests passing (0.02s)
**Handoff:** To Reviewer (Heimdall) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 44/44 tests green, ruff clean, no smells |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 5 | confirmed 3, dismissed 1, deferred 1 |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 3, dismissed 2 |

**All received:** Yes (3 returned with results, 6 disabled via settings)
**Total findings:** 6 confirmed, 3 dismissed (with rationale), 1 deferred

### Finding Decisions

**Confirmed:**
1. [SILENT][RULE] `from_genre_pack()` bare KeyError on missing config keys (line 87) — both subagents flagged independently. Config-load failures raise raw KeyError with no context about which key or genre pack failed. Severity: **MEDIUM** (errors DO propagate — they just lack structured context; fail-fast at startup is acceptable).
2. [RULE] `from_genre_pack()` config param typed as bare `dict` (line 85) — should be `dict[str, Any]`. Severity: **LOW** (functional, just imprecise typing).
3. [SILENT] `_parse_preset()` bare ValueError from TtsModel()/float(speed) (lines 141-143) — unrecognized model or non-numeric speed raises bare ValueError with no per-character context. Severity: **MEDIUM** (same pattern as #1).
4. [SILENT] `route()` coerces None/empty character_id to "unknown" (line 111) — silent fallback makes dropped IDs indistinguishable from legitimately unknown NPCs. Severity: **MEDIUM** (requires misuse via direct __init__ bypass of Speaker.character()).
5. [RULE] Redundant `from typing import Optional` with `from __future__ import annotations` active (line 10) — use `str | None` instead. Severity: **LOW**.
6. [RULE] No logging in module — default NPC fallback path produces no trace (line 120). Severity: **LOW** (fallback to default NPC is designed behavior per story ACs, not an error path).

**Dismissed:**
- [SILENT] identify_speaker narrator fallback (line 135) — DISMISSED: narrator is the correct default for text without dialogue tags. This IS the designed behavior per AC "Speaker detection." re.escape() correctly handles special chars. Low confidence finding, not corroborated.
- [RULE] `_parse_preset()` bare `dict` param (line 138) — DISMISSED: Rule #3 explicitly exempts "internal/private helpers." The `_` prefix marks this private.
- [RULE] Rule #4 logging on from_genre_pack failure path — DISMISSED: bare KeyError raises to caller with full traceback. The module doesn't import logging because it's a data-mapping layer. Adding logging here would be premature.

**Deferred:**
- [SILENT] `_parse_preset()` ValueError context on bad model/speed (lines 141-143) — deferred to future story. The ValueError message from Enum("invalid") is actually descriptive enough for debugging.

### Rule Compliance

**Rule #1 (Silent exceptions):** No bare except, no swallowed exceptions. `from_genre_pack` raises KeyError naturally — not swallowed, just lacks structured context. COMPLIANT (errors propagate).

**Rule #2 (Mutable defaults):** Checked all 8 function/method signatures. No mutable defaults. `Speaker.__init__` uses `Optional[str]=None`. `TtsVoiceRouter.__init__` takes `dict[str, VoicePreset]` as parameter (not default). COMPLIANT.

**Rule #3 (Type annotations):**
- `Speaker.__init__` (line 31): fully annotated. COMPLIANT.
- `Speaker.narrator` (line 36): return type annotated. COMPLIANT.
- `Speaker.character` (line 40): fully annotated. COMPLIANT.
- `VoicePreset.__init__` (line 47): fully annotated. COMPLIANT.
- `VoiceAssignment.__init__` (line 58): fully annotated. COMPLIANT.
- `TtsVoiceRouter.__init__` (line 73): fully annotated. COMPLIANT.
- `TtsVoiceRouter.from_genre_pack` (line 85): `config: dict` — bare dict, should be `dict[str, Any]`. MINOR VIOLATION.
- `TtsVoiceRouter.route` (line 102): fully annotated. COMPLIANT.
- `identify_speaker` (line 127): fully annotated. COMPLIANT.
- `_parse_preset` (line 138): private helper, EXEMPT per rule.

**Rule #4 (Logging):** No logging module imported. No error paths that swallow — all errors propagate. Fallback to default NPC is designed behavior. COMPLIANT (no logging needed for this data-mapping layer).

**Rule #5 (Path handling):** No file operations. N/A.

**Rule #6 (Test quality):** Checked test file — no vacuous assertions (TEA self-checked and fixed 2), no mock patches, all tests have specific value assertions. COMPLIANT.

**Rule #7 (Resource leaks):** No open/connect/lock. N/A.

**Rule #8 (Unsafe deserialization):** `from_genre_pack` receives pre-parsed dict. No pickle/eval/yaml.load/exec. COMPLIANT.

**Rule #9 (Async pitfalls):** No async code. N/A.

**Rule #10 (Import hygiene):** `from typing import Optional` is redundant with `from __future__ import annotations`. MINOR VIOLATION. No star imports, no circular imports.

**Rule #11 (Security):** `re.escape()` used on NPC names before regex interpolation. No SQL, HTML, or file path from user input. COMPLIANT.

**Rule #12 (Dependency hygiene):** No dependency changes. N/A.

**Rule #13 (Fix regressions):** Greenfield module, no prior code. N/A.

### Review Observations

1. [VERIFIED] TtsModel enum prevents raw string model names — `tts_routing.py:13-17` defines Kokoro/Piper variants, `_parse_preset` at line 141 constructs via `TtsModel(cfg["model"])` which raises ValueError on invalid strings. Test at line 29 (`test_no_raw_string_construction`) confirms. Complies with story AC "Model typing."

2. [VERIFIED] VoicePreset speed validation — `tts_routing.py:48-49` guards `speed <= 0` with ValueError. Tests at lines 80-85 confirm both negative and zero rejection with `match="speed"`. No subagent contradicts.

3. [VERIFIED] Speaker factory methods enforce construction contracts — `Speaker.narrator()` at line 36 sets `is_narrator=True`, `Speaker.character()` at line 40 sets `is_narrator=False` with required `character_id`. Tests at lines 106-116 confirm. No subagent contradicts.

4. [VERIFIED] TtsVoiceRouter stores presets privately — `tts_routing.py:80-82` uses `self._narrator_preset`, `self._default_npc_preset`, `self._character_presets` (underscore-prefixed). Callers access via `route()` method only. No public mutation path.

5. [VERIFIED] `re.escape()` prevents regex injection in `identify_speaker` — `tts_routing.py:131` wraps NPC name with `re.escape()` before interpolation into regex pattern. Test at line 152 confirms partial names don't false-positive. COMPLIANT with Rule #11.

6. [MEDIUM] `from_genre_pack()` config param typed as bare `dict` — `tts_routing.py:85`. Should be `dict[str, Any]` for clarity at this public API boundary. Not blocking.

7. [MEDIUM] `route()` silent "unknown" coercion — `tts_routing.py:111` `char_id = speaker.character_id or "unknown"`. Empty string or None bypasses Speaker.character() contract silently. Not blocking because Speaker.character() enforces str type.

8. [LOW] `AssignmentSource.SessionOverride` defined at line 25 but unused. Future placeholder per story context — acceptable for enum extensibility.

9. [LOW] Redundant `Optional` import at line 10 with `from __future__ import annotations` active. Cosmetic.

10. [VERIFIED] Data flow: Genre pack YAML dict → `from_genre_pack()` (line 85) → `_parse_preset()` (line 138) → `TtsModel()` enum coercion + `VoicePreset` construction with speed validation → stored in router fields → `route(Speaker)` → `VoiceAssignment` with source tracking. No mutation after construction. Safe.

### Wiring Check

- `TtsVoiceRouter.from_genre_pack()` accepts raw dict — integration with actual genre pack YAML loading not in this module (caller responsibility). Acceptable for this story scope.
- `identify_speaker()` is a standalone function that returns `Speaker` — composable with `route()`. Wiring is clean.

### Error Handling

- `VoicePreset.__init__`: ValueError on invalid speed. Tested.
- `TtsModel()`: ValueError on invalid model string. Tested.
- `from_genre_pack()`: KeyError on missing config keys. Not caught — propagates naturally. Acceptable fail-fast.
- `_parse_preset()`: ValueError from TtsModel/float propagates. Not caught — acceptable.
- `route()`: No error path — always returns a VoiceAssignment (narrator, explicit, or default). By design.

### Security Analysis

- No auth/authz concerns — pure data routing, no network, no file I/O.
- `re.escape()` on NPC names prevents regex injection.
- No tenant isolation concerns — single-user game engine.
- No sensitive data in voice presets.

### Tenant Isolation Audit

N/A — SideQuest is a single-user personal game engine. No multi-tenancy. No tenant_id fields. No trait methods handling tenant data.

### Devil's Advocate

What if this code is broken? Let me argue against approval.

**The "unknown" sentinel is a ticking bomb.** `route()` at line 111 maps falsy character_id to the literal string "unknown". If any NPC in a genre pack is actually named "unknown", they would collide — `Speaker.character("unknown")` would look up character_presets["unknown"] and get an explicit preset, while a dropped-ID speaker would also map to "unknown" but hit the default path. The behavior diverges based on whether "unknown" is in character_presets. This is a semantic collision waiting to happen. Counterargument: no genre pack is likely to name a character "unknown", and Speaker.character() enforces non-None str, so the only path to this sentinel is via direct __init__ bypass. Risk is low but real.

**The regex patterns are narrower than real narration.** `identify_speaker` only matches "Name says:" and "Name:" patterns. What about "Name whispered:", "Name shouted:", "'Hello,' Name said"? These all fall through to narrator. The test suite confirms this is intentional (test_case_sensitive_matching, test_partial_name_no_false_positive), but in production, this means a significant portion of dialogue will be narrated in the narrator voice rather than the character's voice. Counterargument: the story AC explicitly says "Grimjaw says: hello" — only the `says:` and bare `:` patterns are in scope. Expanding patterns is a future story.

**No integration test with real genre pack YAML.** All tests use dict literals. If the actual genre pack YAML structure has `voice` vs `voice_id` or `speed` as string vs float, the router will fail at runtime. The `_parse_preset` function does `float(cfg["speed"])` which handles both, and `cfg["voice"]` matches the YAML key in `_sample_media_config()`. But there's no contract enforcement between genre pack YAML schema and this module. Counterargument: this is a unit-level story. Integration testing is a separate concern.

**`character_presets` dict is shared by reference.** `TtsVoiceRouter.__init__` at line 82 stores the dict directly: `self._character_presets = character_presets`. The caller retains a reference and could mutate it after construction, silently changing routing. Counterargument: `from_genre_pack()` builds the dict locally (line 92) so the only reference is held by the router. Direct __init__ callers would need to deliberately mutate. Risk is negligible.

**None of these rise above MEDIUM.** The "unknown" sentinel is the strongest argument, but it requires deliberate misuse of the Speaker constructor to trigger. The narrow regex is by design. The dict reference sharing is a Python convention issue. The missing integration test is out of scope.

### Design Deviation Audit

### Reviewer (audit)
- **New module instead of extending existing router** — TEA deviation: created `TtsVoiceRouter` in new `tts_routing.py` instead of extending existing `VoiceRouter` in `router.py`. → ✓ ACCEPTED by Reviewer: existing VoiceRouter handles narrative parsing + preset registry (different domain). New TtsVoiceRouter adds typed model enum, assignment source tracking, and speaker identification. Different responsibilities justify separate module. The existing `protocol.VoicePreset` (Pydantic, with pitch/rate/effects) and new `tts_routing.VoicePreset` (plain class, with model/voice_id/speed) serve different purposes.

### Dev (implementation)
- No deviations from spec. → ✓ ACCEPTED by Reviewer: confirmed no undocumented deviations found.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Genre pack dict → `from_genre_pack()` → `_parse_preset()` → TtsModel enum + VoicePreset (validated) → TtsVoiceRouter (private fields) → `route(Speaker)` → VoiceAssignment with source tracking. Safe — no mutation after construction, no external I/O.

**Pattern observed:** Clean factory pattern with typed enums (TtsModel, AssignmentSource) preventing stringly-typed APIs. Private fields with method-only access on TtsVoiceRouter. `tts_routing.py:80-82`.

**Error handling:** VoicePreset guards speed > 0 (line 48). TtsModel rejects invalid strings via enum (line 141). Config KeyErrors propagate with tracebacks. All error paths tested.

**[EDGE]** — Disabled via settings. Self-assessed: `route()` "unknown" sentinel on empty character_id is MEDIUM but not blocking. Speaker.character() enforces str type at construction.

**[SILENT]** — 3 confirmed MEDIUM findings: bare KeyError/ValueError in config parsing lacks structured context. Acceptable for config-load fail-fast. 1 dismissed (narrator fallback is correct design). 1 deferred (parse error context).

**[TEST]** — Disabled via settings. Self-assessed: 44 tests cover all 10 ACs. TEA self-checked and fixed 2 vacuous tests. No mock patches to verify.

**[DOC]** — Disabled via settings. Self-assessed: all public classes and functions have docstrings. Module docstring present.

**[TYPE]** — Disabled via settings. Self-assessed: TtsModel/AssignmentSource enums prevent raw strings. One minor typing gap (bare `dict` on `from_genre_pack`). No stringly-typed APIs.

**[SEC]** — Disabled via settings. Self-assessed: re.escape() on regex input. No network/file/SQL. No tenant isolation concerns (personal project).

**[SIMPLE]** — Disabled via settings. Self-assessed: 144-line module, no over-engineering. AssignmentSource.SessionOverride is unused but acceptable for enum extensibility.

**[RULE]** — 5 rules checked, 2 minor violations (bare dict type, redundant Optional import). Neither blocking.

| Severity | Issue | Location | Action |
|----------|-------|----------|--------|
| [MEDIUM] | Bare KeyError/ValueError in config parse — no structured context | tts_routing.py:87,141-143 | Non-blocking improvement for future |
| [MEDIUM] | route() "unknown" sentinel on empty character_id | tts_routing.py:111 | Non-blocking — requires constructor misuse |
| [LOW] | from_genre_pack config typed as bare dict | tts_routing.py:85 | Non-blocking — use dict[str, Any] |
| [LOW] | Redundant Optional import | tts_routing.py:10 | Non-blocking — cosmetic |
| [LOW] | AssignmentSource.SessionOverride unused | tts_routing.py:25 | Non-blocking — future placeholder |

**Handoff:** To SM (Baldur the Bright) for finish-story