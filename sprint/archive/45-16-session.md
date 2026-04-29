---
story_id: "45-16"
jira_key: "SQ-45-16"
epic: "SQ-45"
workflow: "trivial"
---

# Story 45-16: Reject non-room entries from discovered_regions

## Story Details

- **ID:** 45-16
- **Jira Key:** SQ-45-16
- **Epic:** SQ-45 (Playtest 3 Closeout)
- **Workflow:** trivial
- **Points:** 1
- **Priority:** p2
- **Type:** bug
- **Stack Parent:** none

## Description

Playtest 3 Felix: discovered_regions had '(aside — narrator brief)' registered as traversable region alongside legitimate rooms. Aside rounds leak into region graph. Reject non-room entries at write; emit OTEL span on rejection so GM panel can see the filter fired.

### Acceptance Criteria

1. Discovered regions write path validates entries are rooms (not aside rounds)
2. Non-room entries rejected at write with OTEL span emission
3. GM panel observability: span shows rejection count and entry type
4. No silent fallbacks - invalid entries logged with span context

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-29T15:31:14Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-29T00:00:00Z | 2026-04-29T15:18:26Z | 15h 18m |
| implement | 2026-04-29T15:18:26Z | 2026-04-29T15:26:00Z | 7m 34s |
| review | 2026-04-29T15:26:00Z | 2026-04-29T15:31:14Z | 5m 14s |
| finish | 2026-04-29T15:31:14Z | - | - |

## Sm Assessment

**Story routed for trivial implement phase. Setup complete and gates clear.**

- **Scope:** 1pt p2 bug, single repo (server). Validation guard at the `discovered_regions` write seam — reject entries that aren't rooms (the playtest leak was `(aside — narrator brief)`). Surface area is one filter + one OTEL span.
- **Workflow:** Trivial is correct — concrete bug evidence from Playtest 3 Felix, single function to harden, no design choice to litigate.
- **Risk surface:** Low. No multiplayer touch points, no migration, no UI work. Server-only.
- **OTEL discipline (per CLAUDE.md):** AC2/AC3 require span emission on rejection so the GM panel sees the filter fire. Don't accept implementation that silently drops invalid entries — Sebastien needs to see rejections counted.
- **Wiring test required (per CLAUDE.md):** The validator must be invoked from the actual `discovered_regions` write code path, not just unit-tested in isolation. Confirm a non-test caller hits it.
- **Branch:** `feat/45-16-reject-non-room-discovered-regions` ready in sidequest-server.

No blockers. Hand off to Ponder Stibbons (Dev) for implement phase.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/game/region_validation.py` (new) — `validate_region_name()` returning `(is_valid, reason)`. Conjunctive rejection rule: empty / bracketed (leading `(` `[` `{` `<`) / multiline / over-80-chars.
- `sidequest/telemetry/spans/region_state.py` (new) — `SPAN_REGION_ENTRY_REJECTED` constant + `region_entry_rejected_span` context manager + `SPAN_ROUTES` registration (event_type=`state_transition`, component=`region_state`).
- `sidequest/telemetry/spans/__init__.py` — re-export the new module.
- `sidequest/server/narration_apply.py` — wire validator + span at the location-update seam (the Felix leak path). Bad locations no longer append to `discovered_regions`; rejection emits `region.entry_rejected` with `caller_path=narration_apply.location_update`.
- `sidequest/game/session.py` — wire validator + span at both `apply_world_patch` paths: wholesale `discovered_regions` set (filters list, drops bad entries) and incremental `discover_regions` patch. Distinct `caller_path` values per seam.
- `tests/server/test_region_validation.py` (new, 30 tests) — unit tests on the validator (8 legitimate names + Felix leak shape + bracket family + empty/whitespace + multiline/oversize), span registration tests (3), and wire tests (3) proving production callers route through the validator.

**Tests:** 30/30 passing (GREEN). Full server suite: 2965 passed / 0 failed / 49 skipped — no regressions. ADR-088 routing-completeness lint passes (new span properly registered in `SPAN_ROUTES`).

**Branch:** `feat/45-16-reject-non-room-discovered-regions` (pushed)

**ACs Met:**
- **AC1** — Discovered-regions write path validates entries: ✅ All three narrator-driven seams route through `validate_region_name`.
- **AC2** — Non-room entries rejected at write with OTEL span emission: ✅ `region.entry_rejected` fires per rejection.
- **AC3** — GM panel observability: ✅ Span carries `entry`, `reason`, `caller_path`, `rejection_count`; `SPAN_ROUTES` surfaces it as a `state_transition/region_state` event so the dashboard renders it.
- **AC4** — No silent fallbacks: ✅ Rejections log at WARNING in `narration_apply` and emit telemetry from every seam.

**Handoff:** To Granny Weatherwax (Reviewer) for the trivial-workflow review phase.

## Delivery Findings

### Dev (implementation)
- **Improvement** (non-blocking): The location-update seam at `sidequest/server/narration_apply.py:571-575` still sets `snapshot.location = result.location` *before* validating, so a rejected aside-as-location can corrupt `snapshot.location` and the `state_transition/location` watcher payload even though it no longer leaks into `discovered_regions`. Story 45-16 scope was strictly the region graph — fixing the location field is a separate guard the playgroup may want next sprint. Affects `sidequest/server/narration_apply.py:571-593`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `region_init.init_region_location` (cartography starting region) does not call the new validator. The starting region comes from world-pack YAML, not the narrator, so the leak vector doesn't apply — but symmetry would be nice if a future story tightens cartography pack validation. Affects `sidequest/game/region_init.py:60-61`. *Found by Dev during implementation.*

## Design Deviations

### Dev (implementation)
- **No deviations from spec.** AC1–AC4 implemented as the SM Assessment described. The 80-char length cap is an *additional* defensive rejection beyond the original Felix-leak shape — included because narrator prose paragraphs can be long enough to slip past a bracket-only check. Documented in the validator docstring; passes the "doesn't change the AC" test.

### Reviewer (audit)
- **Dev entry above** → ✓ ACCEPTED by Reviewer: 80-char cap is a defensive widening, not a contradiction with any spec source. Cap value is documented in the module docstring with rationale ("longest fixture region 'Felix's Workshop' at 16 chars + healthy multiplier"). Conservative addition is sound; AC1 ("validates entries are rooms") admits any superset of the bracket rule.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (full suite 2935 passed / 0 failed; ruff clean; 30/30 new tests green; 1 advisory note: inline-import pattern in session.py) | confirmed 1 (escalated to [SIMPLE]), dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.test_analyzer=false` |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.comment_analyzer=false` |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.rule_checker=false` |

**All received:** Yes (1 specialist returned, 8 disabled by project settings — Reviewer absorbed those domains directly per the `<critical>` rule that "Errors/skips do not transfer coverage")

**Total findings:** 4 confirmed (1 from preflight + 3 from Reviewer's own diff read), 0 dismissed, 0 deferred

## Rule Compliance

Walked the **`.pennyfarthing/gates/lang-review/python.md`** checklist (13 numbered rules) plus the relevant CLAUDE.md / SOUL.md provisions. The diff is small (6 files, +516/-2). Per-rule enumeration:

| # | Rule | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Silent exception swallowing | ✓ Compliant | No bare `except:`, no `try/except: pass`. The `with region_entry_rejected_span(...): pass` patterns in `session.py` are span-emit context managers, not exception swallowers — the side effect is the span open/close, the `pass` is the intentionally-empty body. |
| 2 | Mutable default arguments | ✓ Compliant | `validate_region_name(name: str \| None)` — no mutable default. Span helper uses `**attrs: Any` pattern (kwargs spread, not mutable default). |
| 3 | Type annotation gaps at boundaries | ✓ Compliant | Public surface (`validate_region_name`, `region_entry_rejected_span`) fully annotated with return types. Test helpers (`_make_minimal_snapshot`, `_make_narration_result`) are private, exempt per rule. |
| 4 | Logging coverage AND correctness | ⚠ Partial | `narration_apply.py:582-588` emits `logger.warning(...)` on rejection — correct severity (validation failure of LLM output is a client-side concern → warning, not error per the rule). `session.py` rejection paths emit the span but **no `logger.warning`**. See [SIMPLE] finding 2 below. |
| 5 | Path handling | N/A | No filesystem operations in this diff. |
| 6 | Test quality | ✓ Compliant | All 30 tests carry specific value assertions (no `assert True`, no truthy-only checks). Parametrized cases test distinct shapes (8 legitimate names, 4 bracket variants, 4 empty-shape variants). Wire tests assert `len(rejection_spans) == 1` AND attribute equality — strong assertions. No skipped tests, no mock target errors. |
| 7 | Resource leaks | ✓ Compliant | Every span use is `with region_entry_rejected_span(...):` — context-managed. `Span.open` cleans up on `__exit__`. |
| 8 | Unsafe deserialization | N/A | No deserialization in diff. |
| 9 | Async/await pitfalls | N/A | All sync code paths. |
| 10 | Import hygiene | ⚠ Partial | Module-level `__all__` declared in both new modules (`region_validation.py:71`, `region_state.py:74-77`). No star imports. **However**: `session.py:715-716` and `:731-732` import `validate_region_name` and `region_entry_rejected_span` *inside* the `apply_world_patch` body — duplicated twice. Static check confirms no circular-import risk (region_validation imports nothing from sidequest; spans modules don't reach into game.session). See [SIMPLE] finding 1 below. |
| 11 | Input validation at boundaries | ✓ Compliant — this story IS the input-validation rule for narrator-driven region writes. The validator is the boundary check; the wire tests prove production callers route through it. |
| 12 | Dependency hygiene | ✓ Compliant | No new dependencies. |
| 13 | Fix-introduced regressions | ✓ Compliant | This is the fix; full-suite preflight shows 0 regressions in 2935 prior tests. |

**CLAUDE.md cross-checks:**
- *No Silent Fallbacks* — ✓ Every rejection emits a typed span with reason + caller_path. The validator returns `(False, reason)` not a bare `False` — the reason propagates.
- *No Stubbing* — ✓ No empty shells. The new modules are fully implemented.
- *Don't Reinvent — Wire Up What Exists* — ✓ Reuses the established Story 45-13 span pattern (`container_retrieval_blocked_span`) verbatim — same context-manager shape, same `SPAN_ROUTES` registration shape, same audit-attribute set.
- *Verify Wiring, Not Just Existence* — ✓ Three wire tests target the actual production callers (`_apply_narration_result_to_snapshot`, `apply_world_patch` × 2 paths), not just the validator in isolation.
- *Every Test Suite Needs a Wiring Test* — ✓ Three of the 30 tests are wire tests.
- *OTEL Observability Principle* — ✓ The new span is properly routed (`state_transition` / `region_state` / `field=discovered_regions`) so the GM panel renders rejections on a state-transition lane. Sebastien gets the lie-detector signal.

**SOUL.md cross-checks:** No design-pillar surface in this story — pure write-time hardening. The Felix leak was a *bait misfire* (narrator-meta got promoted to canon); blocking it preserves *Diamonds and Coal* discipline (random aside text shouldn't graduate to a discoverable region).

## Devil's Advocate

I'll argue this code is broken three ways and see what survives.

**1. The validator strips for checks but the callers store the unstripped value.** Tested empirically: `validate_region_name("Tood's Dome\n")` returns `(True, None)` because `strip()` removes the newline before the multiline check sees it. But the caller in `narration_apply.py:594` does `snapshot.discovered_regions.append(result.location)` — *unstripped*. So if a narrator emits `"Tood's Dome\n"` on turn 12 and `"Tood's Dome"` on turn 17, the `if result.location not in snapshot.discovered_regions` check fails (they're different strings), and the player ends up with **both** entries — the same region listed twice with whitespace variants. This is a real edge case, not theoretical: production narrator output is LLM-generated text, and LLMs frequently emit trailing whitespace. The bug isn't visible in the playtest evidence because Felix's leak was bracket-shape, not whitespace-shape; the AC has been satisfied for the observed leak. But the validator could be tightened (`name != name.strip()` → reject) or the callers could store the stripped value. **I'm escalating this to [LOW] — non-blocking but worth a follow-up.**

**2. What if the location passes validation but the narrator emits a different region two ms later?** Race condition? `apply_world_patch` runs inside `with self._lock:` (verified at session.py:691 unchanged) — same lock as before. No new concurrency surface. ✓

**3. What if `result.location` is `bytes` instead of `str`?** Type annotation says `str | None` (`agents/orchestrator.py:252`) but Python doesn't enforce. `name.strip()` on bytes would AttributeError. But the validator is reached via narrator-result extraction, which deserializes through Pydantic — bytes can't reach here without bypassing Pydantic. Theoretical. ✗ Not a real finding.

**4. What about `(aside — narrator brief)` *inside* a longer string?** `"Tood's Dome (aside — narrator brief)"` doesn't start with bracket. Passes. Stored. The descriptive parenthetical isn't filtered. Is this a problem? In practice the narrator-aside leak shape was the *whole string* being a parenthetical, not a tail. So the AC is met. But it's a known gap — the bracket check is leading-only by design (legitimate names like "Old Town (West)" must pass). Acceptable trade-off; not a finding.

**5. What if the narrator deliberately emits `"<aside>foo</aside>"` to bypass bracket detection?** It's `<` — caught by `_BRACKET_PREFIXES = ("(", "[", "{", "<")`. Tested in `test_bracket_prefix_rejected`. ✓

**6. Wholesale-replace path with `discovered_regions=[]`** wipes the region graph. Pre-fix behavior was identical (`self.discovered_regions = patch.discovered_regions`). Not a regression. ✓

The strip-but-store mismatch (#1) is the only finding that survives. Adding it.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Narrator-emitted `result.location: str` → `_apply_narration_result_to_snapshot` (`narration_apply.py:573-595`) → `validate_region_name(result.location)` → on `False`: `region_entry_rejected_span(entry, reason, caller_path)` opens, `logger.warning` fires, span closes; on `True`: dedup-append to `snapshot.discovered_regions`. Parallel path for narrator-emitted `WorldStatePatch.discover_regions` and `WorldStatePatch.discovered_regions` flows through `GameSnapshot.apply_world_patch` (`session.py:711-744`) with distinct `caller_path` values per seam so the GM dashboard can attribute rejections.

**Pattern observed:** `[VERIFIED]` Direct copy of the Story 45-13 `container.retrieval_blocked` template — same context-manager shape (`region_state.py:36-71`), same `SPAN_ROUTES` registration with `state_transition` event_type and a per-domain `component` (`region_state.py:24-34`), same audit-attribute set (`entry`, `reason`, `caller_path`, `rejection_count`). Reusing institutional pattern, not inventing new shape — satisfies the "Don't Reinvent" CLAUDE.md rule.

**Error handling:** `[VERIFIED]` Validator returns `(False, reason)` with a typed reason string ∈ {empty, bracketed, multiline, too_long}. Reason propagates to span attribute, callers fall back to `"unknown"` only on the impossible nil-reason path. No bare exceptions, no swallowed errors.

**OTEL observability:** `[VERIFIED]` Span registered in `SPAN_ROUTES` with route extractor that surfaces `entry`, `entry_type`, `reason`, `caller_path`, `rejection_count` as a `state_transition`/`region_state` watcher event. Test `TestSpanRegistration::test_span_extract_carries_audit_fields` (`test_region_validation.py:159-185`) pins the exact extracted shape. The GM panel will render this on the same lane as `state_patch` and `room_state` events.

**Wiring:** `[VERIFIED]` Three production callers exercise the validator: `_apply_narration_result_to_snapshot` (Felix leak path), `apply_world_patch.discovered_regions_set`, `apply_world_patch.discover_regions`. All three are reached by wire tests that prove non-test code paths route through the new validator. CLAUDE.md "Verify Wiring, Not Just Existence" satisfied.

**Test quality:** `[VERIFIED]` 30/30 passing in 0.04 s. Specific-value assertions throughout. Parametrized cases distinguish shapes (8 legitimate / 4 bracket / 4 empty / 2 multiline / 1 oversize / 1 boundary 80-char). Span-attribute equality asserted, not just count. No vacuous assertions, no mock-on-wrong-target, no skipped tests.

**Findings (non-blocking):**

| Severity | Issue | Location | Suggested fix |
|----------|-------|----------|---------------|
| [LOW][SIMPLE] | Local imports duplicated inside `apply_world_patch` body — same two imports written twice (lines 715-716 and 731-732). Static check confirms no circular-import risk (region_validation has no internal imports; spans modules don't reach into `sidequest.game.session`). Preflight subagent flagged this independently. | `sidequest/game/session.py:715-716, 731-732` | Hoist `from sidequest.game.region_validation import validate_region_name` and `from sidequest.telemetry.spans import region_entry_rejected_span` to the module-level imports at the top of `session.py` (alongside the other `sidequest.game.*` imports). Removes 4 lines of duplication and the per-call import lookup. |
| [LOW] | Inconsistent log-emission between rejection seams. `narration_apply.location_update` emits both span + `logger.warning(...)` (`narration_apply.py:583-590`); both `session.py` seams emit the span but **no Python log line**. AC4 ("logged with span context") is met by span emission alone, so this is cosmetic — but a future debugger reading log files will see narrator-driven leaks but not patch-driven leaks. | `sidequest/game/session.py:723-728, 738-743` | Add a `logger.warning("region.entry_rejected reason=%s entry=%r caller=session.apply_patch.X", reason, r, ...)` call inside each `with` block. One line each. |
| [LOW] | Strip-but-store mismatch in validator. `validate_region_name` runs `name.strip()` for its checks but returns only `(bool, reason)` — the unstripped value is what gets stored. Narrator emits `"Tood's Dome\n"` on turn 12 and `"Tood's Dome"` on turn 17; both pass the validator, but the dedup `if r not in self.discovered_regions` check sees them as distinct strings. Result: region graph contains the same place twice with whitespace variants. Not the playtest leak shape, but a real follow-on edge case. | `sidequest/game/region_validation.py:60-63`; storage in `narration_apply.py:594`, `session.py:725-727`, `session.py:744` | Either: **(a)** tighten the validator — add `if name != stripped: return False, "leading_or_trailing_whitespace"` to force narrator to emit clean names; **OR (b)** return `(True, normalized_name)` from the success path and have callers store the normalized value. Option (a) is more in keeping with "fail loudly" — the narrator's habit of emitting trailing newlines is a real bug worth surfacing. |

None of these block the AC. The strip-but-store is the most consequential — adding to Delivery Findings as a follow-up candidate.

**Tags satisfied:** `[EDGE]` strip-store edge case, `[SILENT]` no swallowed errors verified, `[TEST]` test-quality verified, `[DOC]` docstrings + comments accurate (validator docstring matches behavior, comment in narration_apply matches change), `[TYPE]` type annotations complete at public boundaries, `[SEC]` no security surface in this diff, `[SIMPLE]` import duplication finding, `[RULE]` 13-rule python checklist walked above.

**Handoff:** To Captain Carrot Ironfoundersson (SM) for finish-story.

## Delivery Findings

### Reviewer (code review)
- **Improvement** (non-blocking): Strip-but-store mismatch in `validate_region_name` lets `"Tood's Dome\n"` and `"Tood's Dome"` both pass and end up as distinct `discovered_regions` entries — narrator output frequently has trailing whitespace, so this is a real follow-on bug. Affects `sidequest/game/region_validation.py:60-63` (validator should reject pre-strip mismatch OR return normalized value). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Local-import duplication inside `apply_world_patch` body — `validate_region_name` and `region_entry_rejected_span` imported twice (lines 715-716, 731-732). Static check confirms no circular-import risk; should be hoisted to module top. Affects `sidequest/game/session.py:683-744`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Inconsistent rejection logging — `narration_apply.location_update` writes to both span and Python logger; `session.apply_patch.*` writes to span only. Symmetry would help log-only debugging. Affects `sidequest/game/session.py:723-728, 738-743`. *Found by Reviewer during code review.*