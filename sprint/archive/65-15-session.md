---
story_id: "65-15"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 65-15: r2_audit: parse pack audio.yaml in expected_keys() — classical_pd tracks mis-flagged as orphans; real audio 404s go uncaught

## Story Details
- **ID:** 65-15
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T09:56:27Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T09:30:20Z | 2026-06-04T09:32:28Z | 2m 8s |
| red | 2026-06-04T09:32:28Z | 2026-06-04T09:45:25Z | 12m 57s |
| green | 2026-06-04T09:45:25Z | 2026-06-04T09:51:15Z | 5m 50s |
| review | 2026-06-04T09:51:15Z | 2026-06-04T09:56:27Z | 5m 12s |
| finish | 2026-06-04T09:56:27Z | - | - |

## Sm Assessment

**Story:** 65-15 — r2_audit: parse pack audio.yaml in `expected_keys()`.

**Type:** Defect fix (Architect audit 2026-06-03). Single-repo (orchestrator), 2 pts, TDD.

**The bug:** `scripts/r2_audit.py::expected_keys()` learns music tracks ONLY from `audio/music/*_input_params.json` (ACE-Step params). It never parses pack `audio.yaml`. Every track referenced via an `audio.yaml` `path:` is therefore absent from the expected set and mis-reported as an Orphan (present in R2, no YAML). The same blind spot means the audit can NOT catch a real audio 404. Confirmed against `wry_whimsy`/`pulp_noir` `classical_pd` + `ragtime_pd`.

**Technical approach (do NOT reimplement path logic):** The canonical resolver already exists — reuse it. `sidequest-server/sidequest/genre/audio_paths.py::resolve_audio_relpath` defines the rule:
- `path:` starting with `assets/` → shared `genre_packs/assets/...` WITHOUT the pack slug.
- otherwise → pack-local `genre_packs/<slug>/...`.

PR #338 migrated packs to the shared `assets/` prefix, so naive `genre_packs/<pack>/` prefixing is WRONG. Fix: have `expected_keys()` parse each pack `audio.yaml` and resolve each `path:` through the same assets/-vs-pack-local rule.

**Watch-outs for TEA/Dev:**
- Per [[r2-audit-audio-classification-unreliable]] and [[classical-pd-is-per-pack-mirrored]]: shared PD music lives in the shared `genre_packs/assets/audio/` bucket and is referenced via `path: assets/audio/...`. Never assume per-pack copies.
- `r2_audit.py` and any boto3/render-publish work run under the orchestrator root venv (`uv run --project .`), not sidequest-server — see [[render-publish-scripts-use-root-venv]].
- RED phase should pin the regression: a pack whose `audio.yaml` references an `assets/`-prefixed track must NOT be flagged Orphan, AND a `path:` whose resolved key is genuinely missing from R2 MUST be flagged as a 404/missing.

**Routing:** Phased TDD → handing off to TEA (The Architect) for the RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Defect fix with clear, testable behavior on a pure (offline, pyyaml-only) function.

**Test Files:**
- `scripts/tests/test_r2_audit.py` — 7 new tests appended to the existing suite (no R2 network; `tmp_path` fixtures).

**Tests Written:** 7 tests covering 6 ACs (AC1–AC6 from context-story-65-15.md)
**Status:** RED — `5 failed, 14 passed` via `uv run --project . pytest scripts/tests/test_r2_audit.py`

The 5 failing tests drive the fix; 2 of the 7 are forward-compatible regression
guards that already pass (URL passthrough; optional-audio.yaml). The 12
pre-existing tests still pass — the audio.yaml parse is additive and the existing
`_build_pack` fixture (no audio.yaml) is unaffected.

| Test | AC | Pins | RED reason |
|------|----|------|-----------|
| `test_expected_keys_shared_audio_path_is_slugless` | AC1 | `assets/` path → `genre_packs/assets/...` (NO slug); spaces/parens literal; wrong slug-prefixed key absent | key never added today |
| `test_expected_keys_pack_local_audio_path_is_slug_prefixed` | AC2 | pack-local path → `genre_packs/<slug>/...` | key never added today |
| `test_expected_keys_absolute_url_audio_path_is_not_a_key` | AC1-edge | http(s)/abs paths pass through, never a key | guard (passes now + after) |
| `test_audit_does_not_flag_shared_track_as_orphan` | AC3 | headline: R2-present shared track ≠ orphan | track not in expected → orphan today |
| `test_audit_catches_audio_yaml_404` | AC4 | symmetric: YAML path absent from R2+disk → authored_but_not_rendered | uncatchable today |
| `test_expected_keys_missing_audio_yaml_is_not_an_error` | AC5 | optional audio.yaml; params-music still works | guard (passes now + after) |
| `test_expected_keys_audio_yaml_entry_without_path_fails_loudly` | AC6 | no-silent-fallback: pathless entry raises | no parse → no raise today |

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|------|---------|--------|
| #5 Path handling — posix keys, no slug-mangling, literal form | `test_expected_keys_shared_audio_path_is_slugless` (asserts exact literal key + absence of wrong form) | failing (RED) |
| #6 Test quality — meaningful assertions, no skips, no vacuous truthy | self-check below; every test asserts a specific key string or a raise | pass |
| #8 Unsafe deserialization — must reuse `_load_yaml`/`safe_load` | flagged as Delivery Finding (Question) for GREEN; behaviorally enforced by reuse | noted |

**Rules checked:** 3 of 8 python lang-review rules are applicable to this pure
YAML-parsing change (the rest — exception swallowing, mutable defaults, logging,
resource leaks — have no surface here). 3 of 3 applicable rules have coverage or a
documented GREEN constraint.

**Self-check:** 0 vacuous tests. Every test asserts a specific key string or a
`pytest.raises`. No `assert True`, no truthy-only `assert result`, no skips.
The 2 always-passing tests are deliberate forward-compat regression guards (noted
as such), not vacuous assertions.

**Handoff:** To Dev (Agent Smith) for GREEN implementation in `scripts/r2_audit.py`.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `scripts/r2_audit.py` — added `_audio_yaml_keys(genre, genre_dir)` and wired it into `expected_keys()`. Mirrors `audio_paths.py::resolve_audio_relpath`'s `assets/`-vs-pack-local rule locally (orchestrator venv can't import the server package; followed the existing `_slugify_name` mirror-with-comment precedent — TEA's Improvement finding). Updated the module docstring's Music line to name both key sources.

**Approach:** Parse `audio.yaml` `mood_tracks` (mood → list of `{path,...}`). Per path:
- `assets/`-prefixed → `genre_packs/<path>` (shared, slug-less)
- pack-local → `genre_packs/<genre>/<path>`
- `http(s)://` / `/...` → passthrough, not an R2 key (skip)
- missing/empty `path` on a dict entry → raise `ValueError` (no silent fallback)
- `audio.yaml` absent → no keys (optional). `sfx_library` not parsed (out of scope).

**Tests:** 19/19 passing (GREEN) — `uv run --project . pytest scripts/tests/test_r2_audit.py`. ruff clean.

**Real-content wiring verification (production `audit()` path):**
- shared `classical_pd`/`ragtime_pd` orphans: **all → 0** (the headline defect).
- 70 shared `assets/audio` keys now in the expected set (was 0); 0 mis-prefixed.
- 168 `audio.yaml`-declared tracks absent from R2 now caught as `authored_but_not_rendered` — the previously-blind 404s (AC4), consistent with known elemental_harmony/long_foundry asset gaps.

**Branch:** `feat/65-15-r2-audit-parse-audio-yaml` (pushed). Commits: `60c9bc1` (RED tests + context), `<impl>` (GREEN).

**Handoff:** To next phase (review / verify).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (19/19 tests, ruff clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — covered by Reviewer's own edge probes (see [EDGE]) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — covered by Reviewer + security subagent (see [SILENT]) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — covered by Reviewer (see [TEST]) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — covered by Reviewer (see [DOC]) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — covered by Reviewer (see [TYPE]) |
| 7 | reviewer-security | Yes | clean | none (0 findings) | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — covered by Reviewer (see [SIMPLE]) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — covered by Reviewer's Rule Compliance (see [RULE]) |

**All received:** Yes (2 enabled subagents returned clean; 7 disabled via `workflow.reviewer_subagents`, covered by Reviewer directly)
**Total findings:** 0 confirmed blocking, 0 dismissed, 1 LOW non-blocking deferred (mood_tracks-as-list AttributeError)

## Reviewer Assessment

**Verdict:** APPROVED

**Scope:** `scripts/r2_audit.py` (+58/−1) — new `_audio_yaml_keys()` wired into `expected_keys()` — and `scripts/tests/test_r2_audit.py` (+128, 7 new tests). Pure offline audit tool; no network/auth/secrets surface.

**Data flow traced:** authored `genre_packs/<g>/audio.yaml` `mood_tracks[*].path` → `_audio_yaml_keys` (safe-load via `_load_yaml`) → assets/-vs-pack-local relpath key → `expected_keys()` set → `audit()` set-diff vs `r2_manifest.json` → `format_report`/`main` exit code. The `path` value is only ever string-concatenated into a comparison key — never passed to `open()`/`Path()`/shell — so a `../` or null-byte `path` produces a non-matching (spurious-gap) key, not a traversal. Safe.

**Observations (9):**
- `[VERIFIED]` Wiring is live, not just defined — `_audio_yaml_keys(genre, genre_dir)` is unioned into `expected_keys()` at `scripts/r2_audit.py:222`, which feeds the production `audit()`→`main()` path. Dev's real-content run (70 shared keys, 0 classical_pd orphans, 168 caught 404s) independently confirms end-to-end engagement. Complies with CLAUDE.md "Verify Wiring".
- `[SEC]` (security subagent, confirmed) `_audio_yaml_keys` reuses `_load_yaml` → `yaml.safe_load`; no `yaml.load`/`pickle`/`eval` introduced. Python lang-review #8 satisfied — evidence: `scripts/r2_audit.py:53-56`, `:198`.
- `[SILENT]` (Reviewer + security, confirmed) No silent fallbacks: a non-dict entry and a missing/empty `path` both `raise ValueError` with full context (`:203-213`), mirroring `_poi_keys`/`_portrait_keys`. Empty/`None` path caught by `if not rel`. Complies with the critical No-Silent-Fallbacks rule.
- `[EDGE]` (Reviewer's own probes — edge-hunter disabled) Verified against real packs: heavy_metal/wry_whimsy/pulp_noir/space_opera/caverns_and_claudes all parse (15/17/25/27/33 keys, no crash). Bare-string mood value → clean `ValueError`. `assets/`-passthrough and slug-less derivation behave identically to canonical `resolve_audio_relpath`.
- `[EDGE]/[LOW]` `mood_tracks` authored as a *list* raises `AttributeError` (`'list' has no attribute 'items'`) instead of a clean `ValueError`. Still fails loudly — non-blocking. Filed as a Reviewer delivery finding (micro-follow-up: add `isinstance(mood_tracks, dict)` guard).
- `[TEST]` (test-analyzer disabled — Reviewer) 7 tests map to AC1–AC6 + a URL-passthrough edge; assertions are specific (exact literal keys incl. spaces/parens, and the *wrong* slug-prefixed key asserted absent) — not vacuous. AC4 (404-catch) and AC3 (orphan-regression) pin both faces of the defect. No skips, no `assert True`. The two always-green tests are deliberate forward-compat guards, documented as such.
- `[DOC]` (comment-analyzer disabled — Reviewer) Module docstring updated to name both music key sources (`:17`); the `_audio_yaml_keys` docstring + the canonical-rule comment block (`:155-162`) are accurate and name `audio_paths.py::resolve_audio_relpath` as the source of truth. No stale comments. The `sfx_library` out-of-scope boundary is documented, not a silent omission.
- `[TYPE]` (type-design disabled — Reviewer) Signature `(_audio_yaml_keys(genre: str, genre_dir: Path) -> set[str])` is fully annotated and matches the sibling `_poi_keys`/`_portrait_keys`/`_music_keys` contract. Returns `set[str]` for clean union. Module-level constants (`_AUDIO_SHARED_PREFIX`, `_AUDIO_PASSTHROUGH_PREFIXES`) are immutable. No stringly-typed leakage beyond the existing key-string convention.
- `[SIMPLE]` (simplifier disabled — Reviewer) Minimal, mirrors existing helpers; no over-engineering, no dead code, no premature abstraction. The mirror-with-comment is the simplest correct option given the venv/URL constraints (canonical import unavailable).

### Rule Compliance

Project rules checked: CLAUDE.md (No Silent Fallbacks, No Stubbing, Verify Wiring, OTEL), python lang-review checklist.

| Rule | Instances checked | Verdict |
|------|-------------------|---------|
| No Silent Fallbacks (CLAUDE.md) | `_audio_yaml_keys` 3 branches (non-dict, missing path, optional-file absence) | COMPLIANT — malformed→raise; absent optional file→empty set (legitimate, not a fallback) |
| No Stubbing (CLAUDE.md) | new function + wiring | COMPLIANT — fully implemented and wired; `sfx_library` is a documented boundary, not an empty shell |
| Verify Wiring (CLAUDE.md) | `expected_keys` call site | COMPLIANT — `:222`, exercised by real-content run + `audit`/`main` tests |
| OTEL on subsystem fix | n/a | N/A — offline dev audit script, no runtime subsystem / span surface (this is itself a dev-side verification tool) |
| #1 exception swallowing | no `except` introduced | COMPLIANT — no try/except added |
| #3 type annotations at boundaries | new public-ish helper | COMPLIANT — params + return annotated |
| #5 path handling | `genre_dir / "audio.yaml"`, `open` via `_load_yaml(encoding=utf-8)` | COMPLIANT — pathlib; derived values are keys, not opened |
| #6 test quality | 7 new tests | COMPLIANT — specific assertions, no vacuous/skip |
| #8 unsafe deserialization | `_load_yaml` | COMPLIANT — `yaml.safe_load` |

### Devil's Advocate

Arguing this code is broken: A hostile or careless content author controls `audio.yaml`. What can they do? (1) `path: ../../etc/passwd` — but the value is never opened; it becomes the literal key `genre_packs/demo/../../etc/passwd`, which matches nothing in the manifest and merely reports a spurious "authored but not rendered" gap. No filesystem escape — the audit reads only `audio.yaml` itself (a fixed, repo-local path) and never the derived keys. (2) A YAML bomb / billion-laughs — `_load_yaml` uses `safe_load`, which still parses anchors; but this is a checked-in repo file an operator runs against their own tree, not untrusted network input, so DoS-on-self is not a meaningful threat. (3) Shape abuse: `mood_tracks` as a scalar/list — a list raises `AttributeError` (ugly but loud, filed LOW); a scalar like `mood_tracks: 5` → `(5).items()` also `AttributeError` (loud). Neither silently mis-audits. (4) Could the fix *hide* a real orphan? Only if a track were in the manifest AND newly added to the expected set when it shouldn't be — but expected-set membership requires an explicit `audio.yaml path:`, so a genuinely orphaned R2 object (no YAML reference) still surfaces. (5) Could it create false 404s? The 168 newly-caught gaps were checked: they are pack-local `audio/music/*.ogg` declared in YAML but absent from the manifest — i.e. genuinely un-uploaded tracks (consistent with documented elemental_harmony/long_foundry asset gaps). That is the *intended* behavior (AC4), not a false positive — the audit was previously lying by omission. (6) Cross-pack key collision: a shared `assets/` track referenced by ten packs yields one identical slug-less key ten times → set-union dedupes → correct single expected key. Nothing here rises above LOW. The change makes the oracle more honest, not less.

**Pattern observed:** Mirror-canonical-rule-locally-with-cross-reference — `_audio_yaml_keys` at `scripts/r2_audit.py:163` follows the established `_slugify_name` precedent for keeping the audit daemon-import-free. Good, consistent pattern.

**Error handling:** Loud `ValueError` on malformed entries (`:203-213`); optional-file absence returns empty set (`:198-199`). One LOW gap (list-shaped `mood_tracks` → `AttributeError`) — non-blocking.

**Handoff:** To SM for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): `r2_audit.py` is deliberately daemon-import-free and runs under the orchestrator root venv (`uv run --project .`), while the canonical resolver `sidequest-server/.../audio_paths.py::resolve_audio_relpath` lives in the server package and returns a *URL* (not the bare relpath key the audit diffs on). The Dev should prefer a clean import if it works under the orchestrator venv; otherwise mirror the one-line `assets/`-prefix rule locally with a comment naming `audio_paths.py` as canonical — the exact precedent already set by `_slugify_name` in this file. Affects `scripts/r2_audit.py` (`_music_keys`/`expected_keys`).
- **Gap** (non-blocking): `audio.yaml`'s `sfx_library:` section (mood → list of bare relpath strings, e.g. `audio/sfx/page_turn.ogg`) is a *different shape* from `mood_tracks` and is intentionally out of scope for this story (the confirmed defect is music: classical_pd/ragtime_pd). If SFX objects exist in R2 they may surface as their own orphan noise — a candidate follow-up story, not part of 65-15. Affects `scripts/r2_audit.py` (would need a separate sfx-aware key derivation).
- **Question** (non-blocking): the impl must reuse the existing `_load_yaml` helper (which uses `yaml.safe_load`) rather than `yaml.load` — Python lang-review rule #8. Flagged so GREEN does not introduce an unsafe loader.

### Dev (implementation)
- **Improvement** (non-blocking): `scripts/tests/test_claude_tab.py` and `scripts/tests/test_playtest_split.py` have 39 failing tests on `feat/65-15` that are PRE-EXISTING (verified: they fail identically with my impl stashed) and unrelated to 65-15 (no `r2_audit` import). Not addressed here. Affects those two test files — a separate cleanup story is warranted.
- **Resolved** (non-blocking): TEA's import-vs-mirror Question is resolved — confirmed `resolve_audio_relpath` is not cleanly importable from the orchestrator scripts venv and returns a URL (not a relpath key), so the local mirror-with-comment was the correct call (matches `_slugify_name`). The `assets/` rule now lives in two places (`audio_paths.py` canonical + `r2_audit.py` mirror) with a cross-reference comment; if the rule ever changes, both must move — same maintenance contract the file already accepts for slugify.
- The impl reused `_load_yaml` (`yaml.safe_load`) per the rule #8 Question — no unsafe loader introduced.

### Reviewer (code review)
- **Improvement** (non-blocking): a malformed `mood_tracks` that is itself a *list* (instead of a mood→list mapping) raises `AttributeError: 'list' object has no attribute 'items'` rather than a clean `ValueError`. It still fails loudly (no silent fallback), so it is not blocking — but a one-line `isinstance(mood_tracks, dict)` guard would give a clearer operator message, matching the in-entry guards. Affects `scripts/r2_audit.py::_audio_yaml_keys`. Candidate micro-follow-up, not required for this story.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Scoped audio.yaml parsing to `mood_tracks`, excluded `sfx_library`**
  - Spec source: context-story-65-15.md, Scope Boundaries / story description
  - Spec text: "parse each pack audio.yaml and resolve each 'path:'" / "every track referenced via audio.yaml 'path:'"
  - Implementation: Tests pin only `mood_tracks` (music) `path:` entries. The `sfx_library` section uses a different shape (bare relpath strings, not `path:`-keyed dicts) and is not asserted.
  - Rationale: The confirmed defect is music (classical_pd/ragtime_pd mis-flagged as orphans). `sfx_library` carries no `path:` key, so it is outside the literal "`path:`" contract; folding it in would expand scope beyond the defect. Logged as a Delivery Finding for a possible follow-up.
  - Severity: minor
  - Forward impact: If SFX objects in R2 cause their own orphan noise, a separate story is needed; 65-15 does not address it.
  - → ✓ ACCEPTED by Reviewer: Sound. `sfx_library` carries no `path:` key (bare-string list), so it falls outside the literal contract; `mood_tracks` is exactly where the confirmed classical_pd/ragtime_pd defect lives. Out-of-scope is documented in code (line ~163) and captured as a follow-up finding — nothing slips through.

### Dev (implementation)
- **Mirrored the resolver rule locally instead of importing the canonical function**
  - Spec source: context-story-65-15.md, Technical Guardrails / story description
  - Spec text: "CANONICAL RESOLVER EXISTS — reuse it, do NOT reimplement path logic: audio_paths.py::resolve_audio_relpath"
  - Implementation: Added a local `_audio_yaml_keys` encoding only the `assets/`-prefix decision, with a comment naming `audio_paths.py::resolve_audio_relpath` as canonical — did not `import` it.
  - Rationale: `r2_audit.py` is deliberately daemon-import-free and runs under the orchestrator root venv where `sidequest.*` is not importable; the canonical function also returns a served URL, not the bare relpath key the audit diffs on. The context doc pre-authorized this fallback ("follow the `_slugify_name` precedent"). The rule reproduced is one line and cross-referenced.
  - Severity: minor
  - Forward impact: The `assets/`-prefix rule now exists in two places; a future change to the shared-bucket convention must update both `audio_paths.py` and `r2_audit.py` (same contract the file already accepts for `_slugify_name`).
  - → ✓ ACCEPTED by Reviewer: Correct call. Verified the canonical function returns a served URL (via `resolve_asset_url`), not the bare relpath key the audit diffs on, and lives in `sidequest.*` which is not importable from the orchestrator scripts venv. The local mirror reproduces only the one-line `assets/` decision, names the canonical source in a comment, and matches the file's existing `_slugify_name` precedent. The duplication is documented and bounded. Security subagent independently confirmed `yaml.safe_load` reuse — no rule #8 regression.

### Reviewer (audit)
- No undocumented deviations found. The implementation matches the story scope and the two logged deviations both stamped ACCEPTED above. The `assets/`-prefix passthrough rule (`http(s)://`, `/`) and the slug-less shared-key derivation were verified against the canonical `resolve_audio_relpath` source and behave identically.