---
story_id: "97-2"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 97-2: Seal-reconcile roster races reconnect order — first reconnector told the table is solo (sealed=0/1)

## Story Details
- **ID:** 97-2
- **Jira Key:** (not in use)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T22:04:17Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T21:43:06Z | 2026-06-10T21:44:30Z | 1m 24s |
| red | 2026-06-10T21:44:30Z | 2026-06-10T21:52:52Z | 8m 22s |
| green | 2026-06-10T21:52:52Z | 2026-06-10T21:57:27Z | 4m 35s |
| review | 2026-06-10T21:57:27Z | 2026-06-10T22:04:17Z | 6m 50s |
| finish | 2026-06-10T22:04:17Z | - | - |

## Sm Assessment

**Story:** 97-2 — Seal-reconcile roster races reconnect order. 2pt, p2, TDD phased, server-only.

**Problem (measured, reproduced 3x):** After a server reload, both seats reconnect. The FIRST reconnector receives `turn_status.reconciled_on_connect` with `sealed=0/1` — a *solo* roster — instead of `0/2`. Evidence: server log `.20260607-090551` lines 652/668, 863/878.

**Root cause:** `build_seal_reconcile_roster` (`sidequest-server/sidequest/server/turn_status_roster.py`) derives the roster from `room.playing_player_ids()` (live sockets) rather than the durable `snapshot.player_seats`. The first reconnector is the only live socket at that instant, so the roster collapses to 1. Plausibly feeds the seat-2 "Enter enabled / no waiting lock" MP-desync symptom.

**Technical approach (for TEA → Dev):** Source the reconcile roster from the durable `snapshot.player_seats` (committed/sealed seats) rather than live sockets, so a durably-seated-but-not-yet-reconnected peer still counts toward the barrier.

**Load-bearing constraint (do NOT regress):** The 45-2 phantom-chargen-peer guard is the *entire reason* `playing_player_ids()`/`playing_*` exists — to keep mid-chargen phantom peers out of the barrier roster. The fix must distinguish "durably seated PC, socket not yet reconnected" (counts) from "phantom mid-chargen peer" (does not count). A naïve swap to all of `player_seats` risks reintroducing the phantom inflation 45-2 guarded against — TEA's RED tests must cover BOTH the reconnect-count fix AND the phantom-peer non-regression.

**Scope:** server only. No UI/content/daemon changes expected. Branch `feat/97-2-seal-reconcile-roster-reconnect-order` on develop.

**Routing:** TDD phased → handoff to TEA (O'Brien) for the RED phase.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Test Files:**
- `tests/server/test_seal_reconcile_durable_roster.py` — helper-level pins on `build_seal_reconcile_roster`: durable-seat denominator, numerator-survives-when-available, solo guard, phantom-absent-from-seats exclusion.
- `tests/server/test_seal_reconcile_reconnect_order.py` — wiring-level proof against the real `connect` handler + real `SessionRoom` + Postgres: first reconnector after a reload, watcher `roster_size`/`roster_source`, 45-2 phantom CHARGEN-seat regression guard.

**Tests Written:** 7 (4 helper + 3 wiring), covering AC1 (durable denominator) and AC2 (45-2 phantom exclusion).

**RED verification (assertion-level, right reasons):**
| Test | Now | Reason |
|------|-----|--------|
| `..durable_roster::denominator_uses_durable_seats` | FAIL | got `{adam}`, want `{adam,eve}` |
| `..durable_roster::denominator_with_sealed_peer_present` | FAIL | numerator dropped with denominator |
| `..durable_roster::excludes_peer_absent_from_durable_seats` | FAIL | buggy code includes live-list phantom |
| `..durable_roster::solo_session_stays_solo` | PASS | negative guard (must stay green) |
| `..reconnect_order::first_reconnector..full_durable_roster` | FAIL | reconcile roster `[{adam-pid}]` — reproduces log `sealed=0/1` |
| `..reconnect_order::watcher_reports_durable_roster_size` | FAIL | watcher `roster_size=1`, no `roster_source` |
| `..reconnect_order::phantom_chargen_peer_excluded` | PASS | 45-2 regression guard (fails iff fix reads `seated_player_ids()`) |

**Pre-existing roster tests:** `test_seal_reconcile_roster.py` + `test_seal_reconcile_on_connect.py` — 6 passed (no regression; source untouched).

### Design guidance for Dev (Julia)
- The fix sources the reconcile **denominator** from `snapshot.player_seats` (durable, committed-only) rather than the live `room.playing_player_ids()`. Because `player_seats` is written only at `_chargen_confirmation`, this is *also* the 45-2 phantom guard — a mid-chargen peer is absent from `player_seats` and so is excluded for free. The phantom wiring test fails iff you instead read `room.seated_player_ids()` (which includes CHARGEN seats).
- Keep the **numerator** honoring `_submitted` while it is populated (helper test `denominator_with_sealed_peer_present` pins this). Do not project all-pending or all-submitted to "fix" the denominator.
- Add a `roster_source` (or equivalently-named) field to the `turn_status.reconciled_on_connect` watcher event naming the derivation (durable seats vs live sockets) — per story scope + the CLAUDE.md OTEL principle. The watcher test pins `roster_size=2` and the presence of a source field.
- The numerator-across-reload edge (sealed=1/2 surviving a process reload) is **out of scope** — logged as a deviation + Delivery Finding; `_submitted` is runtime-only.

### Rule Coverage
| Rule (lang-review / SOUL / CLAUDE.md) | Test(s) | Status |
|------|---------|--------|
| Every suite needs a wiring test | `test_seal_reconcile_reconnect_order.py` (real connect + room + PG) | failing |
| OTEL on every subsystem decision | `watcher_reports_durable_roster_size` (roster_size + roster_source) | failing |
| No Silent Fallbacks (numerator not approximated) | numerator deferred via logged deviation, not a socket/timeout heuristic | n/a (deviation) |
| Negative/edge assertions (test-paranoia) | `solo_session_stays_solo`, `phantom..excluded` | green guards |
| No vacuous assertions | self-check pass — every test asserts a concrete set/value | clean |

**Self-check:** 0 vacuous tests found. No `let _ =`, no `assert True`, no always-None assertions. Every assertion pins a concrete roster membership, status map, or watcher field.

**Handoff:** To Dev (Julia) for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/turn_status_roster.py` — `build_seal_reconcile_roster` now derives roster membership from the durable `snapshot.player_seats` (committed-only) instead of the live `playing_player_ids`. Denominator is correct for the first reconnector (0/2, not 0/1); phantom chargen peers are excluded because they have no durable seat. Numerator (`_submitted`) and phase projection unchanged.
- `sidequest/handlers/connect.py` — added `roster_source: "durable_seats"` to the `turn_status.reconciled_on_connect` watcher event and `source=durable_seats` to its log line, so desync forensics can distinguish the durable-seat denominator from the old live-socket one.

**Tests:** 13/13 passing (GREEN) — 7 new (4 helper + 3 wiring) + 6 pre-existing seal-reconcile.
**Regression:** turn_status broadcast roster (12), MP/solo auto-seat + reconnect-from-cache + slug-connect (28) — all green. Ruff clean on both changed files.
**Branch:** feat/97-2-seal-reconcile-roster-reconnect-order (pushed)

**AC coverage:**
- AC1 (durable denominator) — `denominator_uses_durable_seats`, `denominator_with_sealed_peer_present`, `first_reconnector_after_reload_reconciles_full_durable_roster`, `watcher_reports_durable_roster_size` all green.
- AC2 (45-2 phantom exclusion) — `excludes_peer_absent_from_durable_seats` + `phantom_chargen_peer_excluded_from_reconnect_roster` green; fix derives from committed seats, never `seated_player_ids()`.
- Solo negative guard (`solo_session_stays_solo`) green — solo still reads 0/1.
- OTEL: watcher event names its source per the CLAUDE.md observability principle.

**Handoff:** To TEA (O'Brien) for the verify phase (simplify + quality-pass).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Question** (non-blocking): The numerator (who has sealed) is NOT durably recoverable across a true server-process reload — `turn_manager._submitted` is runtime-only (`turn.py` `model_post_init`, never serialized) and is reconstructed EMPTY on load. So AC1's edge ("if one seat sealed before the reload, sealed=1/2") cannot be honored after a process reload without persisting seal state, which is out of this 2pt story's scope. Affects `sidequest/game/turn.py` (`_submitted` persistence) — a future story if the table wants seal-survives-reload. *Found by TEA during test design.*
- **Gap** (non-blocking): The reconcile watcher event (`connect.py` ~line 1762, `turn_status.reconciled_on_connect`) does not currently name which roster source produced the count. Story scope asks it to. Tests pin a proposed `roster_source` field; Dev may rename the literal but the event MUST disclose durable-seat vs live-socket derivation. Affects `sidequest/handlers/connect.py` (`_watcher_publish` fields). *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. The TEA design guidance held exactly; the durable-seat denominator + watcher `roster_source` field landed with no surprises, and the numerator-across-reload limit was already captured by TEA's deviation/finding.

### Reviewer (code review)
- **Improvement** (non-blocking): Vestigial `playing_player_ids` param on `build_seal_reconcile_roster` + the caller still computing `room.playing_player_ids()`. A future cleanup could drop both and re-express the phantom-non-leak guard at the wiring level only. Affects `sidequest/server/turn_status_roster.py` + `sidequest/handlers/connect.py:1740` (remove the unused arg/param). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The connect reconcile silently emits no frame when `reconcile_roster` is empty (`connect.py:1743`, `if reconcile_roster:` — pre-existing guard). For an MP session this is correct today (empty `player_seats` ⇒ nobody durably committed ⇒ pre-97-2 live roster was also empty), but an optional watcher event on the MP+room+empty-roster path would let the GM panel distinguish a correct no-op from a future denominator-zero regression. Affects `sidequest/handlers/connect.py` (~1743). *Found by Reviewer during code review.*
- **Gap** (non-blocking): Legacy pre-binding MP saves (characters present, `player_seats={}`) backfill only the *connecting* player's seat (`connect.py:646`), so reconnect order can still under-count the denominator on those specific legacy saves. Out of scope for 97-2 (lobby/FSM excluded; behavior is equivalent to pre-change on that path) but worth a dedicated story if legacy saves are still in play. Affects `sidequest/handlers/connect.py:640-646`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Numerator-across-reload edge deferred to a deviation rather than a forcing test**
  - Spec source: context-story-97-2.md, AC1 edge + Assumptions
  - Spec text: "if one seat had already sealed before the reload, sealed-count must also derive durably (sealed=1/2, not 0/2)" / "If implementation finds it is NOT durable, that's a design deviation to log — do not silently approximate"
  - Implementation: Tests pin the DENOMINATOR fix (durable roster size) only. The numerator-survives-reload case is recorded as a Delivery Finding (Question), not a RED test, because `_submitted` is runtime-only and lost on a process reload — forcing it would expand scope to seal-state persistence.
  - Rationale: The context Assumptions section explicitly prescribes logging a deviation when seal state is not durable. The measured bug (log .20260607-090551) shows sealed=0 in both observed cases, so the denominator is the load-bearing fix.
  - Severity: minor
  - Forward impact: A follow-up story is needed if the table wants seal-survives-reload; this story's tests do not block on it.

### Dev (implementation)
- **Retained the `playing_player_ids` parameter on `build_seal_reconcile_roster` but stopped consulting it for membership**
  - Spec source: context-story-97-2.md, Technical Guardrails
  - Spec text: "prefer changing what `build_seal_reconcile_roster` consumes over changing what `playing_player_ids()` returns"
  - Implementation: The function keeps its `(snapshot, playing_player_ids)` signature, but derives membership from `snapshot.player_seats.keys()` internally; the live `playing_player_ids` arg is no longer read. The production caller (`connect.py`) still passes `room.playing_player_ids()`.
  - Rationale: Changing the signature would have churned the production caller and all existing 67-2 call sites; the 97-2 regression test deliberately passes a phantom *through* this arg to prove it cannot inflate the roster, which only has meaning if the arg is still accepted. Keeping it is the minimal change that satisfies every test without weakening the phantom proof.
  - Severity: minor
  - Forward impact: A future cleanup could drop the now-vestigial arg and its caller, but doing so would require re-expressing the phantom-non-leak test at the wiring level only.

### Reviewer (audit)
- **TEA — numerator-across-reload edge deferred to deviation** → ✓ ACCEPTED by Reviewer: sound. `_submitted` is provably runtime-only (`turn.py` `model_post_init` via `object.__setattr__`, not a pydantic field), so it is unrecoverable after a process reload. The measured bug shows sealed=0 in all three observations, so the denominator is the load-bearing fix; persisting seal state is a legitimately separate, larger story. Honestly logged, not a silent approximation (No Silent Fallbacks respected).
- **Dev — retained vestigial `playing_player_ids` parameter** → ✓ ACCEPTED by Reviewer: agrees with author reasoning. Dropping the param would force the phantom-non-leak helper test (which deliberately passes a leak *through* the arg to prove it cannot inflate the roster) to be re-expressed wiring-only, losing a cheap, sharp unit guard. The param is genuinely unused for membership but the docstring states this explicitly. The reviewer-edge-hunter [EDGE] flag on the same param ("misleading dead arg; `room.playing_player_ids()` could raise before the call") is noted but non-blocking: the caller already computed `room.playing_player_ids()` pre-97-2 (no new failure surface introduced), and the misleading-ness is mitigated by the docstring. Logged as a non-blocking delivery finding for a future cleanup.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (25/25 tests pass, ruff clean, 0 smells) | N/A — confirmed clean |
| 2 | reviewer-edge-hunter | Yes | findings | 6 | confirmed 0, dismissed 4, deferred 2 (all non-blocking) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | 0 (no leakage, no PII, no silent fallback) | N/A — confirmed clean |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (3 enabled returned; 6 disabled via workflow.reviewer_subagents)
**Total findings:** 0 confirmed blocking, 6 assessed (4 dismissed with line-level evidence, 2 deferred as non-blocking out-of-scope)

### Edge-hunter finding disposition
- **#1 empty-roster "silent regression" (high)** → DISMISSED as regression. The `if reconcile_roster:` empty-skip is PRE-EXISTING on develop (`git show develop:connect.py:1743`) — 97-2 did not introduce it. A PLAYING peer is always in `player_seats` at reconcile time (chargen-commit writes both the seat and `player_seats`; the legacy backfill at connect.py:646 + `transition_to_playing` at 1241 run before the reconcile at 1740). The "all in chargen" sub-case has nobody PLAYING, so the pre-change live roster was also empty. Behavior-equivalent. Logged as a non-blocking improvement (optional empty-roster OTEL).
- **#2 legacy-backfill reconnect-order under-count (medium)** → DEFERRED. Pre-existing legacy-save hazard (edge-hunter's own words), affects only pre-binding saves with `player_seats={}`; behavior-equivalent to pre-change. Lobby/FSM is explicitly out of 97-2 scope. Non-blocking delivery finding.
- **#3 ABANDONED-after-commit over-count (high)** → DISMISSED with line-level evidence. `session_room.py:566` gates the ABANDONED transition on `if seat.state == LobbyState.CHARGEN` — a committed/PLAYING player who disconnects is NEVER marked ABANDONED, and ABANDONED (chargen-incomplete) peers are never written to `player_seats`. The premise "completed chargen then abandons" is unreachable. An absent-but-committed peer counting in the roster is the INTENDED fix behavior (the bug is telling the first reconnector it's solo). Docstring claim is accurate.
- **#4 `_submitted` AttributeError via object.__getattribute__ (low)** → DISMISSED. Pre-existing code (unchanged by 97-2); pydantic v2 always invokes `model_post_init` on construction and validation, so `_submitted` is always set.
- **#5 numerator/denominator skew, orphan `_submitted` (low)** → DISMISSED. Theoretical race (a pid submitting before chargen commit), forensic-only, numerator handling unchanged by 97-2; no concrete repro.
- **#6 vestigial param + `room.playing_player_ids()` could raise (medium)** → ACCEPTED as LOW/non-blocking, matches Dev's logged deviation. The caller already computed `playing_player_ids()` pre-97-2 (no new failure surface). Non-blocking cleanup delivery finding.

## Reviewer Assessment

**Verdict:** APPROVED

A surgical, well-tested bugfix. One substantive source line (membership now sourced from durable `snapshot.player_seats` instead of the live `playing_player_ids`), one OTEL field, two new test files (7 tests). Preflight and security clean; edge-hunter's six findings all resolve to non-blocking after line-level verification.

**Observations (8):**
- [VERIFIED] Root-cause fix is correct — `turn_status_roster.py:100` derives `durable_seat_ids = list(snapshot.player_seats.keys())`; `player_seats` is durable (Postgres, ADR-115) and knows the table size before the second socket lands. Evidence: wiring test `test_first_reconnector_after_reload_reconciles_full_durable_roster` now reports roster `{adam,eve}` (0/2) where develop reported `{adam}` (0/1).
- [VERIFIED] 45-2 phantom guard preserved — `player_seats` is written only at `_chargen_confirmation` (`chargen_mixin.py:1492`) / legacy backfill (`connect.py:646`); a mid-chargen phantom (CHARGEN seat) has no entry. Evidence: `session_room.py:566` ABANDONED-from-CHARGEN-only; wiring test `test_phantom_chargen_peer_excluded_from_reconnect_roster` green.
- [VERIFIED] Single production caller — `grep` shows `connect.py:1740` is the only non-test caller, passing the exact source (`room.playing_player_ids()`) being superseded; no divergent caller can behave differently.
- [VERIFIED] Numerator unchanged — `_submitted` still drives `submitted`/`pending` during InputCollection; phase projection (`project_all_submitted` post-fire) untouched. Read-only invariant intact (`test_reconcile_is_read_only_and_does_not_touch_the_barrier` green).
- [EDGE] Empty-`player_seats` MP path emits no reconcile frame — non-blocking; the `if reconcile_roster:` skip is pre-existing on develop and behavior-equivalent. Logged as an optional-OTEL improvement.
- [SEC] No information leakage — character names + seal status already public via the normal TURN_STATUS broadcast; durable roster enlarges the denominator, not the info type. `player_id` (UUID) is distinct from the CF-Access email, which never touches the snapshot. OTEL/log use lazy `%s`, no PII. (reviewer-security: clean.)
- [DOC] Docstring is thorough and accurate — explains the durable-seat rationale, the 45-2-guard-for-free property, and the numerator-reload deviation; verified its ABANDONED claim against `session_room.py:566`. No stale/misleading comment.
- [SIMPLE]/[TYPE]/[RULE]/[SILENT]/[TEST] — specialists disabled via settings; assessed in-line: no over-engineering (one-line change), no new types, no rule violations against the python lang-review checklist (#1 no bare except, #4 lazy `%s` logging + no PII, #6 test quality — every test asserts concrete sets/status maps), no swallowed errors introduced, tests are non-vacuous wiring + helper coverage.

**Rule Compliance (python lang-review + SOUL + CLAUDE.md):**
- #1 Silent exception swallowing — none added; no try/except in the diff.
- #4 Logging — `logger.info` uses lazy `%s` substitution; no PII (player_id is a UUID, slug is not PII); level appropriate (info for a state reconcile). COMPLIANT.
- #6 Test quality — no `assert True`, no truthy-only asserts; every test pins a concrete roster membership set / status map / watcher field. COMPLIANT.
- #9 Async — no blocking calls added in the async connect path; the change is a pure list comprehension. COMPLIANT.
- CLAUDE.md OTEL principle — the subsystem decision emits `turn_status.reconciled_on_connect` with the new `roster_source` discriminator so the GM panel can tell durable-seat from live-socket derivation. COMPLIANT.
- CLAUDE.md No Silent Fallbacks — empty `player_seats` ⇒ empty roster ⇒ frame suppressed (pre-existing), not a substituted wrong default. COMPLIANT.
- SOUL "Tabletop First" / ADR-104/105 perception firewall — no per-player private content flows through the reconcile frame; sent only to the connecting socket. COMPLIANT.

**Data flow traced:** reconnect SESSION_EVENT → `ConnectHandler` → (MULTIPLAYER + room) `build_seal_reconcile_roster(snapshot, room.playing_player_ids())` → membership from `snapshot.player_seats.keys()` → `build_turn_status_roster` (status from `_submitted`) → phase projection → `TurnStatusMessage` to the connecting socket only + `turn_status.reconciled_on_connect{roster_source=durable_seats}` watcher. Safe: durable seats are server-authoritative; no user-supplied field controls the roster.

**Pattern observed:** durable-state-as-authoritative reconciliation — sourcing presence truth from the persisted snapshot rather than transient live sockets — at `turn_status_roster.py:100`. Good pattern; matches ADR-115's persisted-substrate intent.

**Error handling:** blank pid/seat-name are pre-filtered before `NonBlankString` (`turn_status_roster.py:43-47`), so the broadcast can't crash on a stale seat. No new failure surface; `room.playing_player_ids()` was already called by this caller pre-97-2.

### Devil's Advocate
Suppose this is broken. The most dangerous reframing: the fix swaps a *liveness* signal (who is actually connected and playing) for a *durability* signal (who once committed a character). A malicious or merely unlucky table could exploit the gap — a player commits a character, leaves forever, and now every reconnector is told the table is N+1 and the barrier "waits" on a ghost. But the barrier itself is untouched: this reconcile is display-only and the actual turn barrier still reads `playing_player_ids()`. The reconcile only tells a reconnecting tab the roster; it cannot stall the round. A confused user might see "1/2" and wonder who the second person is — but that is strictly better than the bug being fixed, where a real waiting peer was rendered invisible (0/1, "you're solo"), which is the failure that actually breaks Alex's submit-and-wait pacing. What about a stressed filesystem / Postgres hiccup? `player_seats` is read from the already-loaded in-memory snapshot, not a fresh query, so there's no new I/O failure path. Unexpected config / huge input? `player_seats` is bounded by table size (a handful of players); `.keys()` is O(n) on a tiny dict. Race conditions? The read is on the canonical snapshot the room binds; the function is provably read-only (no mutation of `_submitted` or phase), verified by `test_reconcile_is_read_only_and_does_not_touch_the_barrier`. The one genuinely imperfect corner — legacy pre-binding saves where `player_seats={}` and reconnect order matters — is pre-existing, behavior-equivalent to develop, and explicitly out of scope; I logged it as a non-blocking finding rather than letting it slip. Nothing here rises to Critical or High.

**Handoff:** To SM for finish-story.