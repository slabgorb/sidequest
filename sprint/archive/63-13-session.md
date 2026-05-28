---
story_id: "63-13"
jira_key: null
epic: "63"
workflow: "tdd"
---

# Story 63-13: Location validator reports malformed world YAML as a clean Issue, never a traceback (+ runtime degrade)

## Story Details
- **ID:** 63-13
- **Jira Key:** (none — no-jira story)
- **Epic:** 63 — Reference pages v3
- **Workflow:** tdd
- **Repos:** server
- **Branch:** feat/63-13-location-validator-malformed-yaml-guard
- **Points:** 3
- **Priority:** p2
- **Type:** bug
- **Assignee:** slabgorb

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-05-27

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27 | - | - |

## TEA-Verified Premise

**Root cause discovered by 63-6 Reviewer R1 + Keith directive 2026-05-26:**

### Primary — Validator unguarded yaml.safe_load
Location validator `sidequest/cli/validate/locations.py` has two main exposure layers:

1. **helpers with yaml.safe_load UNGUARDED:**
   - `:398` _location_card_slugs (locations.yaml)
   - `:420` _history_poi_slugs (history.yaml)  
   - `:518` cartography.yaml load
   - `:534` rooms/*.yaml loop
   - `:116` npcs.yaml, `:135`, `:149` (same exposure)

2. **Error path:** Malformed world YAML raises raw `yaml.YAMLError` out of `validate_locations_in_world(:552)` → `pf validate locations` aborts with traceback instead of clean Issue. The validator meant to catch authoring errors dies on the exact error it should report.

### Issue-Reporting Mechanism
- Use frozen dataclass `Issue(code, severity: "error"|"warning", message, pack, world, region_id, file, line=None)`
- `ValidationResult` with `errors`/`warnings` + `.record(issue); .success = not errors`
- Pattern exists at line 178: catches pydantic validation → `result.record(Issue(...))` → continue
- **New code:** Issue code = `"MALFORMED_YAML"` (severity: error)
- **Caveat:** `_history_poi_slugs` and `_location_card_slugs` return `set[str]` and don't receive `result`
  - Guard `yaml.safe_load()` at call sites INSIDE `validate_locations_in_world`, or refactor helpers to accept `result+pack/world`
  - Issue MUST carry `file + line` (from `problem_mark`) for clear author-facing message

### Defense-in-Depth (Runtime R1)
`websocket_session_handler._maybe_emit_location_description` (:347) has two `try/except` guards ending at :439. The 63-6 region-anchor block calls:
- `map_emit.py:514 load_poi_image_slugs(world_dir)` **UNGUARDED, outside both try blocks**
- `load_poi_image_slugs` (reference_renderer.py:1105) re-raises `YAMLError` as `ValueError` → crashes live room-change emit

**Fix:** Guard :514, degrade to empty slug set / no reference URL, consistent with function's other two guards.

## Acceptance Criteria

1. **Validator:** Every `yaml.safe_load()` in `cli/validate/locations.py` that reads a world file (history.yaml, locations.yaml, cartography.yaml, room/*.yaml, npcs, scenario, allowlist) catches `yaml.YAMLError` and emits clean `Issue(severity=error, file=<path>, message='malformed YAML: <detail>')` — never traceback. `pf validate locations` exits nonzero with Issue listed.

2. **Validator test:** World fixture with deliberately malformed history.yaml → `validate_locations_in_world` returns `ValidationResult` containing malformed-YAML Issue and does NOT raise. Same coverage for malformed cartography.yaml.

3. **Runtime defense-in-depth (R1):** `websocket_session_handler._maybe_emit_location_description` wraps `load_poi_image_slugs` + `reference_url_for_region` resolution; on `ValueError` (malformed history.yaml) it emits `reference_url_failed_span` (ERROR — loud, GM-panel-visible, not silent) and degrades reference_url to None so location description still emits. Live room-change never crashed by content typo.

4. **Runtime test:** `_maybe_emit_location_description` with malformed history.yaml fixture still emits `LocationDescriptionMessage(reference_url=None)` and fires `reference_url_failed_span`; does not raise.

5. **No silent fallback:** Degrade path is LOUD — `failed_span` at ERROR severity in runtime, explicit Issue in validator. Neither swallows malformed YAML silently.

## Delivery Findings

### Dev (implementation)
- No upstream findings. All 7 validator sites + the runtime seam were exactly as TEA pinned; the existing `reference_url_failed_span` wired cleanly into the runtime guard with no new telemetry needed.

### Reviewer (code review)
- **Improvement** (non-blocking, SHOULD-FIX): `Issue.line = problem_mark.line` stores pyyaml's **0-indexed** line, but the same Issue's `message` embeds `{exc}`, whose text is pyyaml's **1-indexed** rendering — so a single malformed-YAML Issue is internally self-contradictory (verified: a line-3 error yields `problem_mark.line=2` while the message says "line 3"). The audience is a real content author (Jade, per CLAUDE.md) and this story exists specifically to make author-facing validation clean (Keith's 2026-05-26 directive), so an off-by-one line number misdirects exactly the person it serves. One-line fix (`line=mark.line + 1 if mark is not None else None`); TEA's tests assert `line is not None`, so zero churn. Affects `_safe_load_yaml` in `cli/validate/locations.py`. *Found by Reviewer during code review.*

## Design Deviations

### Dev (implementation)
- No deviations from spec. Implemented both layers as dispatched: a shared `_safe_load_yaml` helper routes every validator `yaml.safe_load` (npcs, scenarios, pack allowlist, locations, history, cartography, rooms) to a `MALFORMED_YAML` Issue (file + `problem_mark.line`) and returns None so callers degrade; `result.success` is False on any recorded error. Refactored the 5 side-band/slug loaders to accept `result`+pack/world (per the dispatch's sanctioned option) rather than guarding at call sites — cleaner single seam. Runtime: guarded `load_poi_image_slugs` in `_maybe_emit_location_description`, degrading to `reference_url=None` + firing the existing `reference_url_failed_span` (ERROR). No new OTEL span on the validator (dev tooling).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/cli/validate/locations.py` — new `_safe_load_yaml` (records MALFORMED_YAML, returns None); 5 loaders (`_load_npc_tokens`, `_load_clue_ids`, `_load_allowlist`, `_location_card_slugs`, `_history_poi_slugs`) refactored to take `result`+pack/world; cartography + rooms loads routed through the helper; all callers updated.
- `sidequest/server/websocket_handlers/map_emit.py` — `_maybe_emit_location_description` guards `load_poi_image_slugs`; on failure degrades to `reference_url=None` and fires `reference_url_failed_span` (loud), emit still sends.

**Tests:** 9/9 (test_location_validator_malformed_yaml.py) GREEN. Full suite (server + integration + genre, both env vars): **3012 passed, 234 skipped, 0 failed**. 0 regressions.
**Branch:** feat/63-13-location-validator-malformed-yaml-guard (pushed)

**Handoff:** To verify (TEA)

## Reviewer Deviation Audit

- **Dev — slug-loader signature refactor (accept `result`+pack/world) instead of call-site guards:** ACCEPTED. The dispatch sanctioned this option; verified it produces a single clean seam (`_safe_load_yaml`) and ALL six call sites were updated (`grep` confirms no straggler on the old signature). Cleaner than per-site guards.
- **Dev — no new validator OTEL span:** ACCEPTED. The validator is dev tooling (CLI), not a runtime subsystem — consistent with the OTEL principle's scope. The runtime guard correctly reuses the existing `reference_url_failed_span`.

## Reviewer Assessment

**Verdict:** APPROVED (recommend the one-line +1 line-index fix before finish — see SHOULD-FIX)

Solid two-layer defense-in-depth, verified empirically on all four scrutiny points. The epic's last story lands clean.

**Four scrutiny points:**
1. **None-coalescing exhaustive?** YES. All 7 `_safe_load_yaml` call sites coalesce `or {}`; downstream consumers further guard with `isinstance` (history, locations) or `.get(...) or []`. No path lets `_safe_load_yaml`'s `None` reach an unguarded `.get`/iteration. (The only theoretical gap — a *valid* YAML scalar like `42` reaching `.get` — is pre-existing and out of scope; `_safe_load_yaml` returns `None` only on `YAMLError`, never changing that path.)
2. **Signature refactor — stale callers?** NONE. `grep` across `sidequest/` + `tests/` shows all six call sites (`_load_npc_tokens`, `_load_clue_ids`, `_load_allowlist` ×2, `_history_poi_slugs`, `_location_card_slugs`) pass `result`+pack/world; no caller left on the old arity.
3. **Runtime degrade genuinely loud?** YES — not a silent swallow. The `except` logs a WARNING, publishes a `location_description.poi_manifest_load_failed` watcher event, AND fires `reference_url_failed_span(reason="malformed_poi_manifest")`, then still emits `LocationDescriptionMessage` with `reference_url=None`. Verified `logger` (line 33) and `_watcher_publish` (line 23) are in scope, so the degrade path can't itself NameError-crash the turn. Confirmed `load_poi_image_slugs` genuinely raises `ValueError` on malformed history.yaml (reference_renderer.py:1105) — the guard is live, not dead code.
4. **`result.success` → False?** YES. `record()` routes `severity="error"` into `self.errors`; `success` returns `not self.errors`. Tests assert `result.success is False` on every malformed case.

**SHOULD-FIX (one-line, recommend before merge):** `Issue.line` stores pyyaml's 0-indexed `problem_mark.line`, but the Issue's own message embeds the 1-indexed exc text — internally self-contradictory (verified: line-3 error → field=2, message says "line 3"). The audience is a real content author and the story's purpose is clean author-facing validation, so the off-by-one misdirects exactly whom it serves. `line=mark.line + 1 if mark is not None else None`; TEA asserts `line is not None`, so zero test churn. Not a blocker (functionally correct, doesn't crash, `success` flips right), but cheap to fix now while the file is open. I concur with TEA's lean toward fixing it.

**Observations:** (1) tests are behavior-against-real-validator (write malformed YAML → run real validation → assert Issue + `success is False`), plus a real-path runtime wiring test with `otel_capture` asserting the failed span fired — no source-text wiring; (2) `except Exception` (BLE001) at the runtime seam is broad but correct for a "must not crash a turn" boundary, and is documented; (3) happy-path slug sets unchanged (regression test `test_valid_world_has_no_malformed_yaml_issue`); (4) no security/data concern — error-reporting hardening.

**Handoff:** To SM for finish ceremony (single-repo, sidequest-server). If applying the +1, route to Dev first, then finish.
