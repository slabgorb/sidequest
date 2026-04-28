---
story_id: "45-4"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 45-4: Strip {{generated at session start}} placeholder leaks from world history.yamls (split from 37-40 sub-3)

## Story Details
- **ID:** 45-4
- **Jira Key:** (pending)
- **Workflow:** trivial
- **Stack Parent:** none
- **Points:** 1
- **Type:** bug

## Story Description
All evropi/long_foundry/flickering_reach world history.yamls carry `world_history[0].character.name='{{generated at session start}}'` unresolved, polluting narrator context every turn. Either resolve the template at session start (preferred — wire it to chargen output) or remove the literal placeholder so the narrator never sees the curly braces.

**Files affected:**
- sidequest-content/genre_packs/heavy_metal/evropi/history.yaml:182
- sidequest-content/genre_packs/heavy_metal/long_foundry/history.yaml:123
- sidequest-content/genre_packs/mutant_wasteland/flickering_reach/history.yaml:114

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-28T00:02:00Z
**Phase Ended:** 2026-04-27T23:42:10Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-27T23:38:54Z | 2026-04-27T23:42:10Z | ~3m 16s |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

- **Gap, non-blocking:** The story description suggests resolving the template at session start (wire to chargen), but there's no template substitution handler in the codebase. The placeholder `{{generated at session start}}` is loaded directly from world history YAML into narrator context without interpolation. Simpler fix: remove the placeholder entirely and replace with a reasonable sentinel value or leave the field to be populated by actual chargen (but chargen doesn't currently populate history[0].character.name).

### Dev (implementation)

- **Gap, blocking (resolved within story):** The Iocane Powder's initial fix used `name: null` in YAML, which violates `ChapterCharacter.name: str = ""` (non-Optional in pydantic v2). Pydantic raises `ValidationError` → wrapped as `HistoryParseError` → silently caught by `session_handler.py` (graceful degradation), leaving the world snapshot empty. This is a *worse* failure than the original placeholder leak (silent vs. visible). Dev replaced `null` with `""` in all four files; verified parsing via direct `parse_history_chapters()` probe — all four chapters[0].character.name parse to `""`. Affects `sidequest-content/genre_packs/{heavy_metal/evropi,heavy_metal/long_foundry,mutant_wasteland/flickering_reach}/history.yaml` and `sidequest-server/tests/fixtures/packs/test_genre/worlds/flickering_reach/history.yaml`. *Found by Dev during implement-phase verification.*
- **Improvement, non-blocking:** `session_handler.py` swallows `HistoryParseError` and continues with an empty snapshot. This violates the project's "No Silent Fallbacks" principle (CLAUDE.md). Recommend filing a follow-up to either re-raise or emit a loud OTEL warning when world history fails to parse, so future YAML drift surfaces immediately rather than degrading the world silently. Affects `sidequest-server/sidequest/server/session_handler.py` (the parse-and-swallow path used by `_world_history_value`). *Found by Dev during implement-phase verification.*
- **Conflict, non-blocking (pre-existing, unrelated):** `tests/server/dispatch/test_sealed_letter_dispatch_integration.py::test_legacy_beat_selection_path_still_works` asserts `cdef.resolution_mode == ResolutionMode.beat_selection` for the CAC `combat` confrontation, but sidequest-content PR #130 ("migrate combat confrontations to opposed_check") changed the rule to `opposed_check`. Test/content drift. Not caused by 45-4 and out of scope; the testing-runner subagent attempted to "fix" the test inline — Dev reverted the unrelated commit. Affects `sidequest-server/tests/server/dispatch/test_sealed_letter_dispatch_integration.py:439`. *Found by Dev during implement-phase verification.*

### Reviewer (code review)

- **Improvement, non-blocking:** No regression guard prevents future re-introduction of `{{...}}` mustache placeholders in any history.yaml `character.name` field. The materializer's truthy-check at `world_materialization.py:306` allows any non-empty string through, including a literal template token, which would propagate into narrator context. Recommend adding either a `model_validator` on `ChapterCharacter` rejecting `{{`/`}}` substrings, or a `tests/genre/` test that walks every shipping pack and asserts no template tokens in character/NPC name fields. Affects `sidequest-server/sidequest/game/history_chapter.py` (validator) or `sidequest-server/tests/genre/` (lint test). *Found by Reviewer during code review.*
- **Improvement, non-blocking:** `ChapterCharacter.name` empty-string semantics are not documented in the model docstring, while the symmetric `ChapterNpc.name` field documents its blank-name short-circuit at `history_chapter.py:49`. Symmetry gap that becomes meaningful now that empty-string is the canonical "no chapter-supplied name" sentinel after this story. Affects `sidequest-server/sidequest/game/history_chapter.py:33` (add field-level note matching the ChapterNpc docstring style). *Found by Reviewer during code review.*
- **Improvement, non-blocking:** No test exercises the existing-character update branch (`world_materialization.py:348`) with `name=""`. Logic verified by manual code-trace, but a unit test would lock in the "blank name does not overwrite chargen name" contract. Affects `sidequest-server/tests/game/test_world_materialization.py`. *Found by Reviewer during code review (test-analyzer subagent).* 
- **Improvement, non-blocking:** No test exercises the narrator-context path when `character_name` resolves to the `"Adventurer"` fallback. Lower-confidence gap; would catch any future regression where a placeholder string slipped through and reached `build_turn_context`. Affects `sidequest-server/tests/agents/test_orchestrator.py`. *Found by Reviewer during code review (test-analyzer subagent).* 
- **Improvement, non-blocking (pre-existing):** `sidequest-content/CLAUDE.md` "Consumers" section still references the retired Rust `sidequest-api` (`--genre-packs-path` CLI arg) instead of the current Python `sidequest-server` (`SIDEQUEST_GENRE_PACKS` env var). Post-port doc drift from ADR-082 cutover. Affects `sidequest-content/CLAUDE.md`. *Found by Reviewer during code review (comment-analyzer subagent).* 
- **Question, non-blocking:** Existing local save files (`~/.sidequest/saves/*.db`) created before this story may have serialized `world_history` rows containing the literal `{{generated at session start}}` string. Loading such a save would still leak the placeholder into narrator context. Decide whether (a) a save migration is needed, (b) the playgroup's saves should be wiped/regenerated, or (c) the leak is acceptable for pre-existing saves only. Affects `~/.sidequest/saves/*.db` and the save-loading path in `sidequest-server/sidequest/game/persistence.py`. *Found by Reviewer during code review (devil's advocate analysis).* 

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations.

### Dev (implementation)
- **Initial fix used YAML `null`; corrected to empty string `""`**
  - Spec source: Story 45-4 description ("remove the literal placeholder so the narrator never sees the curly braces") and `ChapterCharacter` model in `sidequest-server/sidequest/game/history_chapter.py:33` (`name: str = ""`)
  - Spec text: Story called for placeholder removal; the model field is non-Optional `str` with default `""`
  - Implementation: Replaced `name: "{{generated at session start}}"` with `name: ""` in three world history.yamls plus the matching test fixture (initial sm-setup commits had used `null`)
  - Rationale: `null` deserializes to Python `None`, which fails pydantic validation on a non-Optional `str` field. The error is swallowed by `session_handler` and produces an empty world snapshot — a silent regression worse than the original visible leak. Empty string matches the model default and parses cleanly.
  - Severity: minor (within trivial story scope; no architectural change)
  - Forward impact: none — the field remains populated by chargen flow (when wired) or stays empty until then. No sibling story assumes a non-empty value.
  - **→ ✓ ACCEPTED by Reviewer:** Dev's correction from `null` to `""` is sound and load-bearing. Verified that `null` triggers a swallowed `ValidationError` upstream, and that `""` matches the model's documented default and integrates correctly with `_apply_character` (`world_materialization.py:306, 348`). The choice to defer chargen→history wiring is appropriate — story scope is "remove the placeholder," not "wire the substitution."

### Reviewer (audit)
- No undocumented spec deviations. Dev's single deviation (null → empty-string correction) is fully captured above and accepted. The diff matches story ACs (file/line specific).

## Sm Assessment

**Story:** 1pt P0 trivial — strip three literal `{{generated at session start}}` placeholders from world history.yaml files (evropi, long_foundry, flickering_reach).

**Scope:** Tightly bounded. Story ACs are file/line specific. No template substitution machinery exists, so the simpler arm of the story description applies: remove the placeholder rather than wire it to chargen. A proper chargen→history[0] wiring is out of scope and should be filed separately if desired.

**Setup-phase note:** The Iocane Powder (sm-setup subagent) overstepped its lane and committed the implementation during setup phase (content `4c3d063`, server `52011fc`) — placeholder replaced with `null` in all three files, plus matching test fixture. The work itself is correct and minimal. Dev's implement phase should verify the diff, run the trivial gate (lint + targeted tests), and hand to reviewer. No further code authoring should be needed unless verification surfaces an issue.

**Findings flagged:** One non-blocking Gap (no template handler exists). Acknowledged by the chosen approach (remove rather than resolve).

**Routing:** trivial → implement → review → finish. Next agent: **dev** (Inigo Montoya).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (this phase, on top of sm-setup commits):**
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/history.yaml` — `name: null` → `name: ""`
- `sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/history.yaml` — `name: null` → `name: ""`
- `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/history.yaml` — `name: null` → `name: ""`
- `sidequest-server/tests/fixtures/packs/test_genre/worlds/flickering_reach/history.yaml` — `name: null` → `name: ""`

**Verification:**
- Direct pydantic probe via `parse_history_chapters()` on all four files: all four chapters[0].character.name parse to `""` cleanly (4/4 OK).
- Negative-control: `ChapterCharacter.model_validate({'name': None, ...})` rejects with `ValidationError`; `{'name': ''}` accepted. Confirms the regression mode is real and now avoided.
- Targeted tests: `tests/game/test_world_materialization.py` + `tests/genre/` — **384 passed, 0 failed**.
- Full server suite (excluding pre-existing failure): **2652 passed, 34 skipped, 0 failed**.
- One pre-existing failure (`test_legacy_beat_selection_path_still_works`) is content/test drift from sidequest-content PR #130, unrelated to 45-4. Captured as a non-blocking Conflict in Delivery Findings; testing-runner's attempt to inline-fix it was reverted as out-of-scope.
- Lint: `ruff check tests/fixtures/` clean.
- Content YAML: all three world history.yamls load via `yaml.safe_load`. No remaining `{{generated at session start}}` occurrences in either repo (lone hit in `.worktrees/otel-dashboard-relocation/` is an isolated worktree, out of scope).

**Branches (pushed):**
- `sidequest-content`: `feat/45-4-strip-generated-at-session-start-placeholder` (commits `4c3d063`, `f5176c3`)
- `sidequest-server`: `feat/45-4-strip-generated-at-session-start-placeholder` (commits `52011fc`, `f084456`)

**Handoff:** To reviewer (Westley) for review phase.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (pre-existing unrelated test failure; 173 pre-existing ruff lint baseline) | confirmed 0, dismissed 1, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 3 (missing update-branch test; missing `{{...}}` regression guard; missing fallback-name narrator-context test) | confirmed 0, dismissed 0, deferred 3 |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (undocumented empty-name semantics on `ChapterCharacter.name`; stale Rust `sidequest-api` reference in sidequest-content/CLAUDE.md) | confirmed 0, dismissed 0, deferred 2 |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | N/A — Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | none | confirmed 0, dismissed 0, deferred 0 |

**All received:** Yes (4 enabled returned; 5 disabled pre-filled per settings)
**Total findings:** 0 confirmed (blocking), 1 dismissed (with rationale), 5 deferred

### Decision Rationale

- **[preflight] Pre-existing failing test (`test_legacy_beat_selection_path_still_works`)** — *Dismissed.* Caused by sidequest-content PR #130 which switched CAC combat to `opposed_check`; the assertion was never updated. Already captured by Dev as Conflict in Delivery Findings. Pre-dates this branch and out of scope for a 1pt placeholder strip.
- **[preflight] 173 ruff baseline errors** — *Dismissed.* Branch changes 0 Python files; lint baseline is unchanged.
- **[TEST] Missing update-existing-character branch test (`name=""` on populated snap)** — *Deferred.* Logic verified by direct code read at `world_materialization.py:348` (`if char_data.name:` short-circuits empty string), but a unit test would lock in the behavior. Out of scope for trivial; captured as Improvement.
- **[TEST] Missing regression guard for `{{...}}` placeholder leaks** — *Deferred.* The strongest finding. Story 45-4 fixes the three known instances; without a content-lint or pydantic validator, a future author can re-introduce a mustache placeholder in any history.yaml `character.name` and it will silently propagate to narrator context. The proper fix is a small follow-up: either (a) a `model_validator` on `ChapterCharacter` rejecting `{{`/`}}` substrings, or (b) a tests/genre/ test that walks every shipping pack's history.yaml and asserts no template tokens. Captured as a non-blocking Improvement; not in scope for a 1pt YAML edit.
- **[TEST] Missing narrator-context test for fallback name** — *Deferred.* Lower confidence; covers the `Adventurer` fallback path through `build_turn_context`. Captured as Improvement.
- **[DOC] `ChapterCharacter.name` semantics undocumented** — *Deferred.* The `ChapterNpc` docstring documents the equivalent blank-name short-circuit; `ChapterCharacter` does not. Useful symmetry but outside the diff. Captured as Improvement.
- **[DOC] Stale Rust `sidequest-api` reference in `sidequest-content/CLAUDE.md`** — *Deferred.* Pre-existing post-port drift (ADR-082); unrelated to this story. Captured as Improvement.

## Reviewer Assessment

**Verdict:** APPROVED

**Diff scope:** 4 YAML lines across 4 files. `name: "{{generated at session start}}"` → `name: ""`. Zero Python code changed.

**Data flow traced:** YAML parse → `parse_history_chapters()` → `ChapterCharacter(name="")` → `_apply_character()` (`world_materialization.py:292`).
- New-character path (line 306): `name = char_data.name if char_data.name else "Adventurer"` — empty string is falsy, defaults to `"Adventurer"`. Loud, named, visible to OTEL.
- Existing-character update path (line 348): `if char_data.name:` short-circuits → leaves the player's chargen name untouched. Idiomatic.
- The *previous* value (`"{{generated at session start}}"`) was truthy, which means existing-character updates would have **silently overwritten the player's chargen name** with the literal placeholder string on chapter advance. The fix has a stronger positive effect than just removing the prompt-context leak.

**Pattern observed:** Empty-string-as-absent-sentinel is the established convention for blank chapter character fields — see `_apply_character` falsy-check pattern (`world_materialization.py:306-311`) and `ChapterNpc.name` documented short-circuit (`history_chapter.py:49`). The new YAML values comply with this convention.

**Error handling:** None added; none needed. Pure data change. Negative-control verified by Dev: `ChapterCharacter.model_validate({'name': None})` rejects with `ValidationError`; `{'name': ''}` accepted. The originally-committed `null` value was caught and corrected before review.

**Wiring:** `[VERIFIED]` All four files are loaded by `parse_history_chapters()` via the genre-pack loader (Dev's probe confirmed: 4/4 files parse to `chapter[0].character.name == ""`). Test fixture mirror keeps unit tests representative of shipping packs.

**Findings dispatch (all 8 tags required by gate):**
- `[EDGE]` — N/A (subagent disabled).
- `[SILENT]` — N/A (subagent disabled). Manual check: previous code path was a silent name-overwrite on chapter advance; the fix removes that silent failure rather than introducing a new one.
- `[TEST]` — 3 deferred Improvements (regression guard for `{{...}}` leaks is the strongest; see Subagent Results decision rationale).
- `[DOC]` — 2 deferred Improvements (undocumented `ChapterCharacter.name` semantics; stale Rust reference in content CLAUDE.md).
- `[TYPE]` — N/A (subagent disabled). Manual check: empty string fits the model's non-Optional `str` default; no type contract violated.
- `[SEC]` — N/A (subagent disabled). Manual check: pure data change in genre packs; no auth/input/secret surface touched.
- `[SIMPLE]` — N/A (subagent disabled). The change is the minimum possible — 4 lines, no abstractions added.
- `[RULE]` — 0 violations across 16 rule instances checked (rule-checker clean).

### Rule Compliance

Per `<review-checklist>` mandate: rule-by-rule enumeration against project rules.

| Rule | Source | Diff instances | Compliance |
|------|--------|----------------|------------|
| No Silent Fallbacks | SOUL.md / CLAUDE.md / sidequest-content/CLAUDE.md | 4 (each YAML edit) | ✓ Compliant. Empty string falls through to `"Adventurer"` — a loud, OTEL-visible default — not a silent degradation. The previous placeholder was the actual silent-fallback risk and is now removed. |
| No Stubbing | CLAUDE.md / sidequest-content/CLAUDE.md | 4 | ✓ Compliant. Empty-string is consumed data, not stub code. The model's documented default for blank input is `"Adventurer"`. |
| Don't Reinvent — Wire Up What Exists | CLAUDE.md / sidequest-content/CLAUDE.md | N/A | ✓ Compliant. Uses existing `_apply_character` pattern; no new code. |
| Verify Wiring, Not Just Existence | CLAUDE.md | 4 | ✓ Compliant. Dev verified end-to-end via `parse_history_chapters()` probe on all four files. |
| Every Test Suite Needs a Wiring Test | CLAUDE.md | 0 | ✓ Compliant (no new test suite added). Improvement filed for a future regression-test follow-up. |
| Python lang-review (checks 1–13) | gates/lang-review/python.md | 0 | ✓ Compliant. Diff has zero `.py` changes; no rules apply. |

### Devil's Advocate

I want to argue this code is broken.

**Argument 1: The empty string is a silent fallback in disguise.** A future content author looks at `name: ""`, doesn't realize that empty-string is the model's "absent" sentinel, and reads it as "the character has no name" — a deliberate blank rather than a TODO. Then a *different* future author wires the chargen → history step and assumes empty-string means "explicitly no name, leave it." Under that future change, the chargen-supplied name might be lost. **Counter:** This is a hypothetical future-coupling risk, not a present bug. The current materializer at line 306 ("Adventurer" default) and line 348 (skip update on empty) already encode the correct semantics. The fix is the minimum needed; future authors should read the materializer.

**Argument 2: The narrator could still see the placeholder via cached state.** Old save files (`~/.sidequest/saves/*.db`) may contain `world_history` rows with the literal placeholder string from prior runs. Loading one of those saves would still pollute narrator context. **Counter:** Save files are per-genre per-world SQLite — not affected by genre-pack YAML edits. But this is a real consequence: existing local saves will continue to leak. Acceptable: (a) the leak only affects pre-existing saves, not new sessions; (b) save migration is explicitly out of scope for a 1pt content fix; (c) the playgroup's relevant saves are documented in `.pennyfarthing/guides/save-management.md` and can be cleaned up if needed. Worth a Delivery Finding.

**Argument 3: Empty-string for the narrator could be worse than a placeholder.** If the prompt builder concatenates `"You are playing as {name}."`, an empty name produces `"You are playing as ."` — grammatically broken and possibly distracting. **Counter:** The `_apply_character` materializer assigns `"Adventurer"` for the new-character path before any prompt sees the name (`world_materialization.py:306`); the existing-character path keeps the chargen name. The narrator never sees a literal empty name unless something else upstream is broken. Verified by code-trace.

**Argument 4: No test pins this down.** Three of the 4 YAML files have no fixture-loading test that asserts the materialized character name. A YAML typo in a future edit (e.g., `nam: ""` or wrong indentation) could re-introduce drift undetected. **Counter:** This is the test-analyzer's `[TEST]` regression-guard finding, deferred to a follow-up. Valid concern; not blocking for the immediate fix.

**Devil's advocate net result:** Argument 2 surfaces a previously-unflagged concern about pre-existing save files. Adding it as a Delivery Finding below.

**Observations summary (≥5 required):**
1. `[VERIFIED]` Empty-string is the idiomatic "no chapter-supplied name" sentinel — `world_materialization.py:306` (new-char default `"Adventurer"`) and `world_materialization.py:348` (existing-char update skipped on falsy name) make this the documented contract.
2. `[VERIFIED]` Pre-fix value `"{{generated at session start}}"` was truthy and would have silently overwritten chargen names on chapter advance — the fix removes a silent-name-overwrite bug as a side benefit beyond the narrator-context leak the story scoped.
3. `[VERIFIED]` All 4 YAML files load cleanly via `parse_history_chapters()` (Dev's probe).
4. `[VERIFIED]` Negative-control: `null` would have failed pydantic validation and degraded to empty-snapshot via swallowed `HistoryParseError`; Dev caught and corrected this within the implement phase.
5. `[VERIFIED]` Rule-checker: 0 violations across 16 enumerated rules.
6. `[LOW]` Existing local save files may still contain the literal placeholder string in serialized `world_history` rows — captured as Delivery Finding (non-blocking, pre-existing data hygiene).
7. `[DEFERRED]` No regression test pins the no-mustache invariant for `character.name` — strongest follow-up; captured.
8. `[DEFERRED]` `ChapterCharacter.name` empty-string semantics are documented for `ChapterNpc` but not for `ChapterCharacter` — symmetry gap; captured.

**Handoff:** To SM for finish-story.