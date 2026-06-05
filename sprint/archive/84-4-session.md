---
story_id: "84-4"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 84-4: WI-6 OTEL score decomposition — per-card retrieval.card.reason + embed_skipped + tier lifecycle spans (extends ADR-118 §D5)

## Story Details
- **ID:** 84-4
- **Jira Key:** (none — no Jira integration for this project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repo:** sidequest-server
- **Branch:** feat/84-4-otel-score-decomposition

## Context
Story 84-1 (WI-1, just merged as PR #673) delivered the unified pertinence scorer
(`pertinence.py`, `PertinenceScore` dataclass) and the `retrieve_turn_context`
orchestration in `retrieval_orchestration.py`. It also emits `retrieval.embed_skipped`
on the `retrieval.universal` span and populates `card_scores: list[PertinenceScore]`.

WI-6 extends the OTEL surface to make the per-card score decomposition observable
on the GM panel. Key design from ADR-118 Amendment §A5:

- **Per-card `retrieval.card.reason`** — each selected card emits its score breakdown:
  the four signal contributions (`mention`, `here`, `recency`, `sim`) and the final
  score, so the GM panel shows WHY a note surfaced and supplies weight-calibration data.
- **`retrieval.embed_skipped`** (bool) — whether the drama-gate (§A1) skipped the
  cosine pass this turn (already emitted by 84-1 on the span; WI-6 ensures it's
  wired to the GM panel).
- **Tier lifecycle spans** (deferred: WI-3/84-6 will add the tiered projection and
  demotion logic; WI-6 is the observability surface for when that lands).

## Scope
- Emit a `retrieval.card.reason` OTEL event/attribute per selected card, with the
  score decomposition from `PertinenceScore` (mention/here/recency/sim contributions
  and the final score).
- Ensure `retrieval.embed_skipped` is wired from the 84-1 state to the OTEL span
  and the GM-panel renderer.
- Prepare the OTEL shape for tier lifecycle events (tier demotions, rehydrations,
  vector-shedding) so they're ready when WI-3 lands — the span shape should be
  extensible with minimal rework.

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-05 06:58:13

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-05 06:58:13 | - | - |

## TEA Assessment

**Tests Required:** Yes
**Reason:** New observability surface on a live subsystem — every AC needs failing coverage, and the OTEL Observability Principle makes the GM-panel emission load-bearing, not cosmetic.

**Test Files:**
- `sidequest-server/tests/game/test_retrieval_reason_payload.py` — pure helpers `dominant_signal` / `card_reason_payload` (contributions, dominant pick, §A1 tie-break, JSON-serializability, present-tier, embed_used). Synthetic `PertinenceScore` fixtures. 9 tests.
- `sidequest-server/tests/game/test_retrieval_card_reason_span.py` — span emission (run `-n0`): `retrieval.card.reason` JSON list per selected card, empty-list on gate-skip, zero-state tier-lifecycle counters, the extended `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` contract + live span carries the WI-6 attrs. 5 tests.
- `sidequest-server/tests/server/dispatch/test_retrieval_reason_watcher.py` — watcher-event fields via the `_capture_publish` spy on `retrieve_for_turn`: `embed_skipped` both polarities, `card_reasons` payload, empty on gate-skip. 4 tests.
- `sidequest-server/tests/server/dispatch/test_retrieval_reason_wiring.py` — production WIRING through the live `_retrieve_entities_for_turn` delegate (real handler + span exporter + real `watcher_hub` subscriber): span `retrieval.card.reason` populated + watcher `embed_skipped` + `card_reasons`. 1 test.

**Tests Written:** 19 tests covering AC-1…AC-7 (AC-8 is the GREEN-gate quality check).
**Status:** RED — 19 failing, 0 passing.
- 9 `ModuleNotFoundError` (`sidequest.telemetry.retrieval_reason` absent — the pure helpers), the rest `AssertionError` on the absent span attrs (`retrieval.card.reason`, the three tier counters), the absent contract-set entries, and the absent watcher-event fields (`embed_skipped`, `card_reasons`). Each assertion shows the EXISTING attrs/fields present, confirming the path runs and only the new surfaces are missing — clean feature-absence, no typos/fixture bugs.
- The wiring test fails PAST the fill assertions (`outcome==success`, card retrieved) on the missing `retrieval.card.reason` span attr — proving the live `_retrieve_entities_for_turn` delegate is genuinely reached.
- The watcher tests fail on the missing KEY (not on event count) — the `universal_retrieval` event IS captured; it just lacks `embed_skipped`/`card_reasons` today.

**Production call path the wiring test pins (where Dev plugs in):**
`websocket_session_handler.py _retrieve_entities_for_turn` → `server/dispatch/universal_retrieval.py retrieve_for_turn` (ADD `embed_skipped` + `card_reasons` to the published `fields`) → `game/retrieval_orchestration.py retrieve_turn_context` / `_finish` (ADD `retrieval.card.reason` JSON attr + zero-state tier counters to the span).

**Run command (OTEL-sensitive — serial):**
`uv run pytest -n0 tests/game/test_retrieval_reason_payload.py tests/game/test_retrieval_card_reason_span.py tests/server/dispatch/test_retrieval_reason_watcher.py tests/server/dispatch/test_retrieval_reason_wiring.py`

**Handoff:** To Dev (Naomi) for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/telemetry/retrieval_reason.py` (NEW, pure) — `dominant_signal(score)` (largest contribution; §A1 tie-break mention>here>recency>sim), `card_reason_payload(score)` (JSON-serializable dict: card_id, 4 contributions, score, dominant, embed_used, tier), `PRESENT_TIER="full"` (the one honest present tier).
- `sidequest/game/retrieval_orchestration.py` — `_finish` now emits `retrieval.card.reason` (a `json.dumps` of the per-card payload list; `[]` on gate-skip) + the three zero-state lifecycle counters (`retrieval.tier_demotions`/`tier_rehydrations`/`vectors_shed` = 0). No scorer/selection change.
- `sidequest/game/entity_card.py` — added `retrieval.embed_skipped` (84-1 forgot it) + `retrieval.card.reason` + the three counters to `UNIVERSAL_RETRIEVAL_SPAN_ATTRS`.
- `sidequest/server/dispatch/universal_retrieval.py` — `retrieve_for_turn` watcher event now carries `embed_skipped` (both polarities) + `card_reasons` (NATIVE list, not double-encoded). **This is the load-bearing AC-3 fix** — the GM panel reads the WatcherHub event, not Jaeger.
- 4 NEW test files (TEA-authored) — import-sort/unused-`pytest` auto-fixed for lint.

**OTEL shapes emitted:**
- Span `retrieval.universal` (`retrieval_orchestration._finish`): `retrieval.card.reason` = JSON string; `retrieval.tier_demotions`/`tier_rehydrations`/`vectors_shed` = 0; (`retrieval.embed_skipped` from 84-1 retained).
- Watcher `state_transition` event (`dispatch/universal_retrieval.retrieve_for_turn`, `component="retrieval"`): `embed_skipped` (bool) + `card_reasons` (native list of payload dicts).
- Two distinct encodings kept distinct: JSON string on the span, native list on the event.

**Tests:** 19/19 new green (9 payload + 5 span + 4 watcher + 1 wiring). Regression: retrieval + 84-1 + all dispatch = 293 passed, 0 failed. `ruff check` on all changed files clean.
**Branch:** feat/84-4-otel-score-decomposition (committed; not pushed — SM finishes).

**Handoff:** To review (Chrisjen Avasarala).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): 84-1 added `retrieval.embed_skipped` to the span EMISSION (`_finish`) but never added it to the `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` contract set in `sidequest/game/entity_card.py`. WI-6 must add it there alongside the new attrs, or the §D5 contract test under-reports the schema. Affects `sidequest/game/entity_card.py`.
- **Gap** (blocking-for-AC-3): The GM-panel reader is the **WatcherHub event stream**, not OTLP/Jaeger. `server/dispatch/universal_retrieval.retrieve_for_turn` publishes the §D5 counts but does NOT include `embed_skipped` — so the drama-gate decision 84-1 shipped is invisible on the dashboard. The load-bearing WI-6 change is extending that published `fields` dict (add `embed_skipped` + `card_reasons`); the span-only change is insufficient. Affects `sidequest/server/dispatch/universal_retrieval.py`.
- **Question** (non-blocking): OTEL attributes cannot hold a list of dicts. The tests pin `retrieval.card.reason` as a **JSON-encoded string** on the span (decoded with `json.loads`) and `card_reasons` as a **native list** on the watcher event (the hub's `_coerce_attr_value` JSON-stringifies it for the synthetic span; the dashboard reads the raw list from the event fields). Dev should keep these two encodings distinct — don't double-encode the watcher field. Affects both emit sites.
- **Improvement** (non-blocking): `tier` in the card-reason payload is the card's PRESENT projection tier — there is exactly one tier today (no demotion until WI-3/84-6). The test only asserts it's a non-empty string, so Dev can emit the real present-tier constant (e.g. `"FULL"`) without inventing demoted tiers. Do NOT add WI-3 demotion/rehydration/vector-shed LOGIC — the three counters are honest `0`s this turn (no dead code). Affects `sidequest/telemetry/retrieval_reason.py` + `retrieve_turn_context`.

### Dev (implementation)
- **Improvement** (non-blocking): `PRESENT_TIER` is a module-level string constant (`"full"`) in `retrieval_reason.py`, not an enum, because there is exactly one projection tier today. WI-3 (84-6) introduces real demotion/rehydration tiers — at that point `PRESENT_TIER` should become a proper tier enum and `card_reason_payload` should take the card's *actual* tier as a parameter rather than always emitting the constant. The seam is the single `tier=` key in the payload. Affects `sidequest/telemetry/retrieval_reason.py`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): The card-reason payload's four contribution keys (`mention`/`here`/`recency`/`sim`) and the `RetrievedEntities.card_scores` field name use the §A1 vocabulary; the GM-panel UI (sidequest-ui, separate repo) will need a matching `card_reasons` reader on the `universal_retrieval` watcher event to render them. WI-6 lands the producer side only; the UI consumer is out of scope here. Affects `sidequest-ui` watcher event types (future). *Found by Dev during implementation.*
- No blocking upstream findings.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations. ACs derive directly from ADR-118 §D5 + Amendment §A5 and the 84-1 surfaces (`card_scores`, `embed_skipped`) already in the tree.

### Dev (implementation)
- No deviations from spec. Implemented exactly to AC-1…AC-7 and TEA's four Delivery Findings: new pure module `sidequest/telemetry/retrieval_reason.py` (`dominant_signal` + `card_reason_payload` + `PRESENT_TIER="full"`), `retrieval.card.reason` JSON-string span attr + three honest-zero tier counters in `_finish`, `retrieval.embed_skipped` + the WI-6 attrs added to `UNIVERSAL_RETRIEVAL_SPAN_ATTRS`, and `embed_skipped` + native-list `card_reasons` added to the `retrieve_for_turn` watcher event. No scorer/algorithm change; no WI-3 lifecycle logic; no stubs.
- Note (not a deviation): the session file carried TWO `## Design Deviations` headings — a duplicate from the template. SM deduped the empty second heading at finish so the deviations-gate tag scan stays unambiguous.

## Reviewer Assessment (84-4, commit 8fcf83d)

**Reviewer:** Chrisjen Avasarala (adversarial review, Lap 2)
**Verdict:** APPROVED — merge-ready. No Blocker or High findings.

**Scope reviewed:** full diff `develop...feat/84-4-otel-score-decomposition` (977 +/0 -):
new `telemetry/retrieval_reason.py`, additive edits to `_finish` (span), `retrieve_for_turn`
(watcher), `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` (contract), 4 new test files. Verified against
ADR-118 §A5 + context ACs 1-8. Extends the OTEL surface approved in 84-1 (PR #673).

**Verification run (OTEL-sensitive, -n0 serial):**
- 84-4 suites (payload + span + watcher + wiring): **19 passed**.
- Regression (84-1 scorer + supersedes-d4 + orchestration + dispatch consumers): **61 passed**.
- `ruff check` on all 4 changed production files: clean. Tree clean, branch + HEAD (8fcf83d) correct.

**Adversarial checks (8 observations):**
1. **AC-3 watcher both polarities — VERIFIED.** `embed_skipped` + `card_reasons` added to the
   published `state_transition` fields (universal_retrieval.py:98,104). Tests pin True-on-gate-skip /
   False-on-fill; wiring test confirms a REAL `watcher_hub` subscriber (live `subscribe`, not a mock)
   receives both on the production delegate. Unconditional dict keys — no silent drop.
2. **Two-encoding non-divergence — VERIFIED.** Span = `json.dumps([...])` (string); watcher = NATIVE
   list. Watcher test asserts `isinstance(list)`; span test asserts `json.loads`. Both from the SAME
   pure `card_reason_payload` — one shape, no double-encode, no Jaeger/panel drift.
3. **No Stubbing (tier + counters) — VERIFIED real.** `EntityCard` has NO tier field today
   (grep-confirmed); `PRESENT_TIER="full"` is the honest single present tier, not a placeholder. The
   three lifecycle counters emit honest `0` (no WI-3 logic exists). No dead WI-3 functions; `tier=` is
   the documented WI-3 seam.
4. **No Silent Fallbacks (gate-skip + try/except) — VERIFIED honest.** Gate-skip emits empty `"[]"`/`[]`
   (present-but-empty, never absent — omitting would be the silent gap). The `card_reasons` comp sits
   inside the pre-existing ADR-006 try/except wrapping ONLY the watcher publish; result still returned at
   line 116. `card_reason_payload` is pure dict-build over validated scalars — the except degrades
   TELEMETRY honestly, does not mask a turn bug.
5. **Scorer untouched — INDEPENDENTLY VERIFIED.** `pertinence.py` byte-for-byte unchanged (empty diff);
   `retrieval_orchestration.py` is **21 +/0 -** (purely additive span emits). TEA's "0 removed" confirmed.
6. **Span-attr contract (84-1 gap class) — CLOSED here, mechanism still one-directional.** All 5 WI-6
   attrs now declared; `test_live_span_carries_full_attr_contract` enforces `declared ⊆ emitted` + pins
   each WI-6 attr (non-vacuous). But it does NOT enforce `emitted ⊆ declared` — a future emitted-but-
   undeclared attr would still pass (the exact 84-1 bug). Hand-closed, not structurally prevented. See
   Should-fix #1. AC-6 itself is satisfied.
7. **`dominant_signal` tie-break / type design — VERIFIED.** `max((contribution, -priority_index))`
   picks largest contribution, ties resolve §A1 mention>here>recency>sim; all adjacent-pair ties tested.
   Pure, reuses `pertinence.py` string consts. Edge: all-zero card → "mention" default, harmless on the
   live path (fill cards always have sim>0). See Nit.
8. **OTEL discipline — VERIFIED.** Decision observable on the WatcherHub reader path; exactly one
   `retrieval.universal` span/turn (wiring test asserts `len==1`).

**Findings (none blocking):**

| Severity | Finding | Location |
|----------|---------|----------|
| Should-fix | Span-attr contract test is one-directional (`declared ⊆ emitted`). The exact 84-1 bug class — an attr emitted but forgotten in `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` — would still pass green. Add a reverse assertion (`{a for a in span.attributes if a.startswith("retrieval.")} ⊆ UNIVERSAL_RETRIEVAL_SPAN_ATTRS`) so the contract is bidirectional. Non-blocking: AC-6 met, gap hand-closed. | `tests/game/test_retrieval_card_reason_span.py:258` |
| Nit | `dominant_signal` returns "mention" for an all-zero-contribution card (tie default). Harmless live (fill cards have sim>0) but a future 0-sim feed gets a misleading headline. Consider a "none" sentinel when max contribution is 0. | `sidequest/telemetry/retrieval_reason.py:36-49` |

**Deviation audit:**
- Dev + TEA both logged **"No deviations."** — confirmed against the diff (exact to AC-1…AC-7 + TEA's
  four findings; no scorer change, no WI-3 logic, no stubs). **ACCEPTED.**
- Note: session carries TWO `## Design Deviations` headings (template duplicate). I appended at
  end-of-file and touched neither — SM dedupes at finish per the noted heading-collision hazard.

**Handoff:** To SM for finish-story. Both findings are non-blocking telemetry-test/edge hygiene on
correct, purely-additive code; recommend folding the bidirectional contract assertion in if cheap,
else track as an 84-x follow-up (it is the structural lock against the 84-1 gap recurring).
