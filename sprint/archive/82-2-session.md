---
story_id: "82-2"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 82-2: Verbosity/Vocabulary player controls: UI sliders + CONNECT plumb + TurnContext read (ADR-049)

## Story Details
- **ID:** 82-2
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T14:27:30Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T13:45:05Z | 2026-06-05T13:46:37Z | 1m 32s |
| red | 2026-06-05T13:46:37Z | 2026-06-05T14:01:21Z | 14m 44s |
| green | 2026-06-05T14:01:21Z | 2026-06-05T14:18:36Z | 17m 15s |
| review | 2026-06-05T14:18:36Z | 2026-06-05T14:27:30Z | 8m 54s |
| finish | 2026-06-05T14:27:30Z | - | - |

## Sm Assessment

ADR-049 is "overstated": the prompt plumbing fires every turn, but the player-control layer is missing end-to-end. The story is a wiring job across two repos with a clear symbol map already in the description — low ambiguity, no design spike needed.

**Scope (four concrete gaps):**
1. UI — no `VerbositySlider.tsx` / `VocabularySlider.tsx`; add controls feeding the CONNECT payload (sidequest-ui).
2. CONNECT plumb — payload values must reach `TurnContext`; today `session_helpers.py` (~:1167-1168) hardcodes `narrator_verbosity='standard'` / `narrator_vocabulary='literary'`, ignoring the payload.
3. Slug-resume — `handlers/connect.py` (~:1402-1403) passes `None`; must carry the persisted/selected settings.
4. Enum parity — `NarratorVocabulary` lacks `default_for_player_count` that `NarratorVerbosity` has (`protocol/enums.py`).

**Plus the project's standing requirement:** OTEL the active verbosity/vocabulary per turn so the GM panel can confirm the setting is engaged, not improvised (OTEL Observability Principle). This is a Keith/dev observability concern — not a player-facing surface.

**TDD notes for TEA:** RED should pin (a) `TurnContext` reads CONNECT-supplied values rather than the hardcoded defaults, (b) slug-resume round-trips the settings, (c) `NarratorVocabulary.default_for_player_count` exists and mirrors the verbosity contract, and (d) per-turn OTEL emits the active settings. UI slider tests live in sidequest-ui (jsdom). Watch the No-Silent-Fallbacks rule: an absent/garbage CONNECT value should resolve through `default_for_player_count`, not silently snap to a literal. Server OTEL deadlock caveat applies — span-count tests run serially with `-n0`.

**Routing:** phased tdd → TEA (red). No blockers, gate clean otherwise.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Test Files:**
- `sidequest-server/tests/protocol/test_enums.py` (appended) — AC3: `NarratorVocabulary.default_for_player_count` parity (5 new tests).
- `sidequest-server/tests/server/test_verbosity_vocabulary_turn_context_wiring.py` (new) — AC2 (read + No-Silent-Fallback) + AC4 (OTEL span + e2e prompt-section wiring) (5 tests).
- `sidequest-ui/src/__tests__/verbosity-vocabulary-sliders.test.tsx` (new) — AC1: `VerbositySlider`/`VocabularySlider` component contract (6 tests).

**Tests Written:** 16 across 3 files, covering all 4 ACs.

**RED verification (testing-runner, server `-n0` per OTEL-deadlock caveat):**
- AC3 enum tests → `AttributeError: NarratorVocabulary has no attribute default_for_player_count` (method absent). ✓ legit RED.
- AC2a `_build_turn_context` reads session choice → got `'standard'` (hardcoded). ✓ legit RED.
- AC2b absent→helper (No Silent Fallback) → got `'standard'`, expected `verbose`. ✓ legit RED.
- AC4 OTEL → no span carrying `narrator_verbosity`/`narrator_vocabulary`. ✓ legit RED.
- AC4 e2e → prompt renders standard/literary, not concise/accessible. ✓ legit RED.
- AC1 UI → `Failed to resolve import "@/components/VerbositySlider"` (component absent). ✓ legit RED.
- Intended green guards pass: `test_absent_vocabulary_resolves_via_helper` (literary), `test_narrator_vocabulary_multiplayer_defaults_to_literary` is RED (helper absent) — both as designed.
- No collection/import errors in my test code. Pre-existing tests still pass (except the unrelated `test_message_type_complete_count` drift — see Delivery Findings).

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #6 Test quality (meaningful assertions, no vacuous) | Phase-C self-check on all 16 tests | done — every test asserts a concrete value; no `assert True`/truthy-only |
| No Silent Fallbacks (SOUL.md / CLAUDE.md) | `test_absent_verbosity_defaults_via_helper_not_standard_literal` | RED |
| No Source-Text Wiring Tests (CLAUDE.md) | all wiring proof is behavioral (TurnContext field / OTEL span / rendered prompt), no source greps | satisfied |
| OTEL Observability (CLAUDE.md) | `test_build_turn_context_emits_active_settings_span` | RED |
| #3 Type annotations at boundaries (new classmethod) | covered indirectly — `default_for_player_count(int) -> NarratorVocabulary` asserted via `isinstance` | RED |

**Rules checked:** the 5 applicable rules above (the rest of python.md — exception swallowing, mutable defaults, resource leaks, deserialization, path handling — are not exercised by this story's test surface).
**Self-check:** 0 vacuous tests (Phase C clean — no `let _ =`/`assert True`/always-None assertions).

**Handoff:** To Dev (Naomi Nagata) for GREEN. Implementation map is in the Sm Assessment + AC context. Two GREEN-phase obligations flagged in Design Deviations: (1) add an App-level wiring test for slider→CONNECT payload; (2) add a resume-`ready`-payload test (not-None).

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** all 16 RED tests now GREEN + 5 new GREEN-obligation tests pass; no regressions. (Pre-existing unrelated `test_message_type_complete_count` still red — see Delivery Findings.)

**Files Changed — sidequest-server:**
- `sidequest/protocol/enums.py` — `NarratorVocabulary.default_for_player_count` (parity, always Literary).
- `sidequest/telemetry/spans/narrator_settings.py` (new) — `narrator.settings_resolved` span + route; registered in `spans/__init__.py`.
- `sidequest/game/session.py` — `GameSnapshot.narrator_verbosity/_vocabulary` (durable, persists across resume).
- `sidequest/server/session_state.py` — `_SessionData.narrator_verbosity/_vocabulary` (live per-turn value).
- `sidequest/server/session_helpers.py` — `_build_turn_context` resolves session choice → `default_for_player_count(player_count_for_gate)` fallback → TurnContext; emits the span.
- `sidequest/handlers/connect.py` — primary connect hydrates sd + persists to snapshot (payload-wins precedence); resume `ready` reports persisted settings (not None).
- Tests: `tests/server/test_verbosity_vocabulary_resume.py` (new).

**Files Changed — sidequest-ui:**
- `src/components/VerbositySlider.tsx`, `src/components/VocabularySlider.tsx` (new) — radiogroup controls (ModePicker idiom).
- `src/lib/narratorPrefs.ts` (new) — localStorage load/save, validate-don't-trust (No Silent Fallbacks).
- `src/App.tsx` — fold `loadNarratorPrefs()` into the slug-connect payload; resume-sync persists server-reported prefs.
- `src/screens/ConnectScreen.tsx` — render both sliders in the lobby, persist on change.
- Tests: `src/__tests__/narrator-prefs-connect-payload-wiring.test.tsx` (new).

**Wiring (end-to-end, verified):** slider → localStorage → CONNECT payload → connect handler → `_SessionData` (+ persisted `GameSnapshot`) → `_build_turn_context` → rendered narrator prompt section; resume `ready` → localStorage → sliders rehydrate. OTEL `narrator.settings_resolved` fires every turn with active values + source (player vs default).

**Self-review:** wired to UI + server prod paths (non-test consumers); follows ModePicker/pacing-span patterns; all 4 ACs met; No-Silent-Fallbacks honored client (omit unset/garbage) + server (default_for_player_count, never a literal); lint clean; 0 new type errors.

**Handoff:** To next phase (review/verify).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 "blocking" + 5 pre-existing TS | dismissed 1 (hallucinated NARRATOR_PREFS), confirmed 0 new |
| 2 | reviewer-edge-hunter | Yes | findings | 9 | confirmed 3 (M1, L2, M3), dismissed 6 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 6 | confirmed 2 (L1, L2-OTEL), dismissed 4 (documented absent→default contract) |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 3 (M2, L3, L5), dismissed/deferred 4 |
| 5 | reviewer-security | Yes | findings | 1 (low) + 4 rule-classes clean | confirmed 0 critical, 1 low (M3 dup) |
| 6 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled via settings)
**Total findings:** 0 confirmed Critical/High; 3 Medium (non-blocking); ~5 Low (non-blocking); 1 dismissed-as-hallucination (preflight NARRATOR_PREFS); several dismissed as the documented absent→default contract.

## Rule Compliance

Rubric: `.pennyfarthing/gates/lang-review/{python,typescript}.md` + SOUL.md/CLAUDE.md.

- **No Silent Fallbacks (CLAUDE.md/SOUL.md):** COMPLIANT. Absent verbosity/vocabulary resolves through `default_for_player_count` and emits the `narrator.settings_resolved` span with `*_source="default_for_player_count"` — loud, not silent. Client `loadNarratorPrefs` validates against an allowlist and OMITS unknown values (server defaults) rather than coercing. The two `narratorPrefs.ts` `catch{}` blocks are documented graceful-degradation for `localStorage` SecurityError/quota — acceptable, though a `console.warn` would surface programming errors (L1, non-blocking).
- **No Source-Text Wiring Tests (CLAUDE.md):** COMPLIANT. Every wiring assertion is behavioral — TurnContext field value, `narrator.settings_resolved` OTEL span, rendered prompt-section markers, and the WS-received CONNECT payload. No `read_text()`/regex-of-source.
- **OTEL Observability (CLAUDE.md):** COMPLIANT. New subsystem decision (active tuning + source) emits a routed span every turn. One LOW divergence (L2): `*_source` uses `is not None` while resolution uses `or` — agree for all current StrEnum members (all truthy); no reachable trigger since the wire field is `NarratorVerbosity|None`.
- **python.md #3 (boundary type annotations):** COMPLIANT. `default_for_player_count(player_count: int) -> NarratorVocabulary` fully annotated; span helper annotated.
- **python.md #6 / typescript.md #8 (test quality):** MOSTLY COMPLIANT. No `assert True`/vacuous asserts. Two documented green-guard tests (L3) and one redundant `hasattr` test (L5) flagged as non-blocking improvements.
- **typescript.md #3 (enum anti-patterns) / #10 (type-level input validation):** COMPLIANT. Closed string-literal unions; `loadNarratorPrefs` validates against `VERBOSITY_VALUES`/`VOCABULARY_VALUES` allowlists before use.
- **Security (ADR-047 prompt-injection / pydantic boundary):** COMPLIANT. Inbound `SessionEventPayload.narrator_verbosity/_vocabulary` are `NarratorVerbosity|None` StrEnums — pydantic rejects unknown values pre-handler. `_build_verbosity_section`/`_build_vocabulary_section` switch on the value and return hardcoded literals; the raw value is never interpolated into the prompt. Span attributes carry only enum names + literal source strings — no PII.

## Reviewer Observations

- [VERIFIED] No prompt-injection surface — `_build_verbosity_section`/`_build_vocabulary_section` (orchestrator.py:1459/1507) switch on the enum and return fixed literals; raw value never interpolated. Wire field is `NarratorVerbosity|None` (messages.py:373/375) so pydantic rejects unknown input. evidence: enum-typed boundary + literal-returning builders.
- [VERIFIED] No-Silent-Fallback honored both ends — server `_build_turn_context` (session_helpers.py:1224) routes absent→`default_for_player_count` and the `narrator.settings_resolved` span records source; client omits unset/garbage rather than coercing (narratorPrefs.ts:25). evidence: span + allowlist validation.
- [VERIFIED] `session._session_data` non-None at the connect hydration block — assigned by `_SessionData(...)` immediately above (connect.py:833); an exception there would skip the block. Dismisses edge-hunter's low-confidence None-access concern.
- [VERIFIED] Preflight "blocking NARRATOR_PREFS" is fabricated — `grep` finds no such variant; MessageType has 55 members on BOTH develop and HEAD; 82-2 never touched the enum. `test_message_type_complete_count` (expects 54) fails identically on develop — pre-existing `QUESTS` drift, not 82-2.
- [MEDIUM][EDGE] M1 — ConnectScreen seeds the slider display to `standard`/`literary` (ConnectScreen.tsx ~:103), but an UNTOUCHED solo session omits the value from CONNECT, so the server applies `default_for_player_count(solo)=verbose`. The slider shows "Standard" while the narrator runs at verbose length — a player-facing display/behavior mismatch (legibility matters for Sebastien/Jade). Non-blocking; follow-up.
- [MEDIUM][TEST] M2 — the payload-wins-over-snapshot precedence (`payload or snapshot`, connect.py:876) is never exercised: both resume tests seed the snapshot and connect with a bare payload. A reversed `or` would pass the suite. Add a "reconnect with a new choice overrides persisted" test. Non-blocking.
- [MEDIUM][EDGE/SEC] M3 — `saveNarratorPrefs` has no `removeItem`, and App.tsx (~:732) only saves when the ready payload carries a truthy value; a stale local pref therefore rides forward when the server reports null. Debatable (local pref arguably IS the player's choice) but worth an explicit product decision. Non-blocking.
- [LOW][SILENT] L1 — bare `catch{}` in narratorPrefs.ts (lines 25/44) swallows programming errors as well as the intended `localStorage` failures; add `console.warn`. Non-blocking.
- [LOW][EDGE/SILENT] L2 — `or` resolution vs `is not None` source-tag divergence (session_helpers.py:1220 vs 1224; connect.py:876). No reachable trigger today (all StrEnum members truthy; wire field enum-typed). Align to `if x is not None else …` for OTEL-honesty/future-proofing. Non-blocking.
- [LOW][TEST] L3 — `test_absent_vocabulary_resolves_via_helper` is green-on-develop (literary == hardcode); documented as a guard with RED teeth elsewhere (AC2a explicit-epic + AC3). Strengthen with a `vocabulary_source` span assertion. Non-blocking.

## Devil's Advocate

Argue this is broken. **Injection:** the strongest attack is feeding hostile text through the narrator-prompt sections — but both axes are closed `StrEnum`s validated by pydantic at the WebSocket boundary, and the section builders return fixed literals keyed on the value, never interpolating it. A malicious client sending `narrator_verbosity="ignore previous instructions"` is rejected before any handler runs. No injection. **Confused user:** the realest complaint is M1 — a solo player opens the lobby, sees "Standard" pre-selected, never touches it, and gets verbose narration. They were shown one thing and given another. That is a genuine (if minor) legibility wart for a mechanics-first player; it does not corrupt state or block play. **Stressed filesystem / storage:** `localStorage` throwing (private mode, quota) is caught and degrades to "no prefs → server default" — correct, though the bare catch would also hide a future code bug (L1). **Unexpected config / old saves:** a pre-82-2 snapshot deserializes the new fields as `None` (`extra: ignore` + default None), resumes with `None`, and the turn builder falls back to the count default — proven by `test_resume_ready_with_unset_prefs_reports_none`. **Reversed logic:** if someone flipped the `payload or snapshot` precedence, the suite would NOT catch it (M2) — a real coverage hole, but the current code is correct and the comment documents intent. **Race:** connect is single-shot per socket; no concurrent mutation of the new fields. **Lie-detector integrity:** the `or`/`is not None` split (L2) could, in a hypothetical future where a falsy enum member exists, make the span report `source="player"` for a defaulted value — but no such member can reach the field (enum-typed wire, non-empty values). Conclusion: the devil finds UX papercuts and coverage/robustness gaps, not a Critical or High defect. Nothing here corrupts data, leaks information, crashes, or violates a project rule in a way that blocks merge.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player slider → `saveNarratorPrefs` (localStorage, allowlist-validated) → `loadNarratorPrefs()` spread into the slug-connect CONNECT payload → pydantic `SessionEventPayload` (enum-validated) → `connect.handle` hydrates `_SessionData` + persists to `GameSnapshot` → `_build_turn_context` resolves (choice → `default_for_player_count` fallback) → `_build_verbosity_section`/`_build_vocabulary_section` (literal switch, no interpolation) → narrator prompt. Resume: snapshot → `_SessionData` → `ready` payload → client rehydrate. Safe because every hop is enum-typed/validated and the prompt builders never interpolate the raw value.

**Pattern observed:** new OTEL span mirrors the established `pacing_hint_span` idiom (narrator_settings.py); sliders mirror `ModePicker`'s radiogroup idiom — consistent with the codebase.

**Error handling:** absent/garbage choice → `default_for_player_count` (loud, span-recorded); `localStorage` failure → graceful degrade to server default; old saves → `None` → count default (test-proven).

**Findings (by specialist):** 0 Critical/High; all non-blocking.
- [EDGE] M1 — ConnectScreen shows `standard` default while untouched solo gets server `verbose` (ConnectScreen.tsx:~103); M3 — no `removeItem`, stale local pref rides forward (App.tsx:~732).
- [TEST] M2 — payload-wins-over-snapshot precedence untested (connect.py:876); L3 — `test_absent_vocabulary_resolves_via_helper` green-on-develop guard; L5 — redundant `hasattr` test.
- [SILENT] L1 — bare `catch{}` in narratorPrefs.ts (25/44) hides programming errors; L2 — `or` vs `is not None` divergence (session_helpers.py:1224) — no reachable trigger (enum-typed wire).
- [SEC] clean — closed StrEnums, pydantic-validated boundary, prompt builders return literals (no interpolation), span attrs carry only enum names (no PII/injection). One low note folded into M3.
- preflight "blocking NARRATOR_PREFS" → dismissed (verified hallucination; MessageType is 55 on develop and HEAD alike).

**Handoff:** To SM for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `tests/protocol/test_enums.py::test_message_type_complete_count` fails on develop (expects 54 MessageType variants, actual 55 — `QUESTS` was added at `protocol/enums.py:136` without bumping the count). Pre-existing drift, NOT caused by 82-2 (I only appended vocabulary tests). Affects `tests/protocol/test_enums.py` (bump the expected count, or delete the brittle count test). Surfaced incidentally by my `-n0` run. *Found by TEA during test design.*
- **Improvement** (non-blocking): The CONNECT inbound `SessionEventPayload.narrator_verbosity`/`narrator_vocabulary` fields already exist (`protocol/messages.py:373-376`) and round-trip — Dev does NOT need to add wire fields, only to *read* them into the session and persist across resume. Affects `handlers/connect.py` (store inbound payload values on the session) + the chosen persistence substrate for resume. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): `tests/protocol/test_enums.py::test_message_type_complete_count` still fails (expects 54 MessageType variants, actual 55 — `QUESTS`); confirmed unrelated to 82-2 and pre-dates it. Affects `tests/protocol/test_enums.py` (bump the count or drop the brittle cardinality test). *Found by Dev during implementation.*
- No other upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): ConnectScreen slider seeds its display to `standard`/`literary`, but an untouched solo session omits the value so the server applies `default_for_player_count`=verbose — display/behavior mismatch. Affects `sidequest-ui/src/screens/ConnectScreen.tsx` (seed the displayed default from the mode-aware `default_for_player_count`, or persist the shown default so it rides the payload). *Found by Reviewer during code review.*
- **Gap** (non-blocking): the payload-wins-over-snapshot precedence (`connect.py` ~:876) is untested — both resume tests connect with a bare payload. Affects `sidequest-server/tests/server/test_verbosity_vocabulary_resume.py` (add a "reconnect with a new choice overrides the persisted snapshot value" case). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `saveNarratorPrefs` has no `removeItem`; a stale local pref rides forward when the server reports null on `ready`. Affects `sidequest-ui/src/lib/narratorPrefs.ts` + `src/App.tsx` (decide product intent: clear-on-null vs local-pref-wins) — and align the `or` resolution with the `is not None` source-tag in `session_helpers.py`/`connect.py` for OTEL-honesty; add `console.warn` to the bare `catch{}`. *Found by Reviewer during code review.*
- **Gap** (non-blocking, pre-existing, NOT 82-2): `tests/protocol/test_enums.py::test_message_type_complete_count` expects 54 MessageType variants but there are 55 (`QUESTS`) on develop and HEAD alike. Affects `sidequest-server/tests/protocol/test_enums.py` (bump the count or drop the brittle cardinality test). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC1 "sent in CONNECT payload" split into component-contract + server-e2e**
  - Spec source: context-story-82-2.md, AC1 ("UI exposes verbosity + vocabulary controls; the selection is sent in the CONNECT payload")
  - Spec text: "the selection is sent in the CONNECT payload"
  - Implementation: AC1 is pinned at TWO seams instead of one full-App WebSocket payload test — (a) `sidequest-ui/src/__tests__/verbosity-vocabulary-sliders.test.tsx` proves the controls exist and emit the choice via `onChange`; (b) `tests/server/test_verbosity_vocabulary_turn_context_wiring.py` (the AC4 e2e) proves a session-carried choice drives the rendered prompt section. The App.tsx plumbing that folds the slider value into the outbound CONNECT object (`pendingConnectPayloadRef`, 4 inline `event:"connect"` sites) is left for Dev to wire.
  - Rationale: App.tsx builds the connect payload inline at 4 sites and the chosen value's storage seam (localStorage vs settings context vs lobby state) is an undecided Dev design choice. A full-App WS test would have to guess that seam and be wrong-by-construction. The component `onChange` contract + the server e2e together cover the chain end-to-end without dictating Dev's storage decision.
  - Severity: minor
  - Forward impact: Dev must add a wiring test (or extend an App-level connect test) proving the slider value reaches the outbound CONNECT payload — the "Every Test Suite Needs a Wiring Test" rule applies to the App-level fold. Flagged for the GREEN phase.
- **No-silent-fallback player count asserted via `room=None` (count 0/1), not a built MP room**
  - Spec source: context-story-82-2.md, AC2 ("missing payload falls back to default_for_player_count, not a silent literal")
  - Spec text: "Edge: missing payload falls back to `default_for_player_count`, not a silent literal."
  - Implementation: the absent-choice test drives `_build_turn_context(sd)` with `room=None` and asserts `verbose` (= `default_for_player_count(0)` = `default_for_player_count(1)`), rather than constructing a real multi-seat `SessionRoom` to test the MP→standard branch.
  - Rationale: `_build_turn_context` calls `build_shared_world_delta(room=...)` and `room.session`, which a partial fake room cannot satisfy; the proven precedent (`test_pacing_hint_turn_context_wiring.py`) uses `room=None`. `verbose != standard` is a sufficient No-Silent-Fallbacks discriminator (it cannot coincide with the hardcoded `standard` literal). The MP→standard branch is left to a green-on-develop guard rather than a fragile room build.
  - Severity: minor
  - Forward impact: the MP (count>1 → standard) defaulting branch is not directly RED-tested; if Dev wires player-count defaulting, the solo discriminator + the explicit-value tests cover correctness. No follow-up required unless MP defaulting regresses.
- **Resume "populates not None" (AC2) not covered by an isolated RED test**
  - Spec source: context-story-82-2.md, AC2 ("slug-resume populates them (not None)")
  - Spec text: "slug-resume populates them (not None)."
  - Implementation: no standalone test for the `handlers/connect.py:1443-1444` resume `ready`-payload path; coverage of the read/fallback contract is via `_build_turn_context` tests instead.
  - Rationale: the resume `ready` payload is emitted deep inside the connect `handle()` method and requires the full Postgres connect harness (`migrated_db` + `_seed_pg_for_slug`), and the persistence substrate for the chosen settings (snapshot field vs sessions column) is an undecided Dev design choice — seeding it would hard-code a guess.
  - Severity: minor
  - Forward impact: Dev should add a resume test (extend `test_solo_auto_seat_on_connect.py`'s harness) asserting the resume `ready` payload carries the persisted settings, not `None`. Flagged for the GREEN phase.
### Dev (implementation)
- **Persisted narrator tuning lives on GameSnapshot; _SessionData mirrors it for the per-turn read**
  - Spec source: context-story-82-2.md, Assumptions ("Persisting the chosen settings across resume is in scope via the existing session store; if it requires a schema change beyond a field, log a deviation")
  - Spec text: "Persisting the chosen settings across resume is in scope via the existing session store"
  - Implementation: added `narrator_verbosity` / `narrator_vocabulary` to BOTH `GameSnapshot` (durable — round-trips the PG JSON save, `extra: ignore` loads pre-82-2 saves as None) and `_SessionData` (the live runtime value `_build_turn_context` reads each turn). Connect hydrates `_SessionData` from the inbound payload (precedence) else the persisted snapshot, and mirrors the resolved choice back onto the snapshot.
  - Rationale: TEA's tests set `sd.narrator_verbosity`, so the per-turn read must be on `_SessionData`; resume durability needs a persisted home, which is the snapshot. No Alembic/DDL change — the snapshot is stored as JSON, so a new pydantic field is "a field," within the assumption's allowance.
  - Severity: minor
  - Forward impact: none — both fields default None; old saves migrate silently to None (→ default_for_player_count).
- **Lobby-chosen prefs bridge to the CONNECT payload via localStorage; only the PRIMARY slug-connect payload carries them**
  - Spec source: context-story-82-2.md, AC1 ("the selection is sent in the CONNECT payload")
  - Spec text: "the selection is sent in the CONNECT payload"
  - Implementation: `src/lib/narratorPrefs.ts` persists/loads the choice (keys `sq:narrator-verbosity`/`-vocabulary`, same idiom as `sq:display-name`); ConnectScreen's sliders write it; App folds `loadNarratorPrefs()` into the primary slug-connect payload (`pendingConnectPayloadRef`). The three RECOVERY/reconnect connect sites (reconnect_required, session_unbound, OPEN-reconnect) do NOT add prefs.
  - Rationale: ConnectScreen → POST/navigate → App slug-connect is decoupled; localStorage is the established bridge. On reconnect the server already holds the persisted snapshot value, so re-sending prefs is redundant — adding them to recovery paths would be dead plumbing.
  - Severity: minor
  - Forward impact: if a future flow lets a player change tuning mid-session (out of scope per 82-2, "Mid-session live re-tuning … can be a follow-up"), that path must send an updated CONNECT/settings message; today only session-start + resume carry the value.
- **TEA's two flagged GREEN obligations are now satisfied (no longer open)**
  - Spec source: session Design Deviations — TEA (test design), the AC1 "sent in CONNECT payload" and resume-not-None entries
  - Spec text: "Dev must add a wiring test … proving the slider value reaches the outbound CONNECT payload" / "Dev should add a resume test … asserting the resume ready payload carries the persisted settings, not None"
  - Implementation: added `sidequest-ui/src/__tests__/narrator-prefs-connect-payload-wiring.test.tsx` (full-App WS harness — asserts the connect message carries the prefs, omits unset/garbage) and `sidequest-server/tests/server/test_verbosity_vocabulary_resume.py` (PG resume harness — asserts the resume `ready` payload carries persisted settings; None-stays-None guard).
  - Rationale: close the wiring obligations TEA deferred to GREEN so the feature is not half-wired.
  - Severity: minor
  - Forward impact: none — obligations resolved.

### Reviewer (audit)
- **TEA — AC1 split into component-contract + server-e2e** → ✓ ACCEPTED by Reviewer: sound — the component `onChange` contract + the App-level WS payload test (added by Dev) + the server e2e together cover the chain; no guessing of an undecided storage seam.
- **TEA — no-silent-fallback via `room=None` (count 0/1) not a built MP room** → ✓ ACCEPTED by Reviewer: `verbose != standard` is a valid discriminator and the room-build fragility is real; reasonable trade-off.
- **TEA — resume not-None deferred to GREEN** → ✓ ACCEPTED by Reviewer: Dev satisfied it with `test_verbosity_vocabulary_resume.py` (PG harness); obligation closed.
- **Dev — persisted tuning on GameSnapshot + _SessionData mirror** → ✓ ACCEPTED by Reviewer: correct — runtime read on `_SessionData` (what tests set) + durable home on the JSON-serialized snapshot, no Alembic/DDL change, `extra: ignore` migrates old saves to None. Within the story's "a field" allowance.
- **Dev — localStorage bridge; only the PRIMARY slug-connect payload carries prefs** → ✓ ACCEPTED by Reviewer: reconnect/recovery paths rely on the server-persisted snapshot, so adding prefs there would be dead plumbing. Mid-session re-tuning is explicitly out of scope per the story.
- **Dev — TEA's two GREEN obligations satisfied** → ✓ ACCEPTED by Reviewer: both wiring tests exist and pass; feature is not half-wired.