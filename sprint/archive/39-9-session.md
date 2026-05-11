---
story_id: "39-9"
jira_key: null
epic: "39"
workflow: "trivial"
---
# Story 39-9: Caverns_and_claudes CON rebalance + stat_display cleanup

## Story Details
- **ID:** 39-9
- **Jira Key:** N/A (no Jira tracking for oq-2)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial (phased: setup → implement → review → finish)
**Phase:** finish
**Phase Started:** 2026-05-11T00:04:41Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-10T00:00:00Z | 2026-05-10T23:49:55Z | 23h 49m |
| implement | 2026-05-10T23:49:55Z | 2026-05-10T23:59:50Z | 9m 55s |
| review | 2026-05-10T23:59:50Z | 2026-05-11T00:04:41Z | 4m 51s |
| finish | 2026-05-11T00:04:41Z | - | - |

## Story Summary

Caverns_and_claudes is a dungeon-delve pack where CON should matter heavily, but it's the rarest stat in the beat library (3 of 35 beats). This story rebalances the pack to give CON proper mechanical weight.

**Deliverables:**
1. Add 5+ new CON-flagged obstacles to `beat_vocabulary.yaml` (cave-air poisoning, forced march fatigue, holding breath, cold soak, bad water dysentery)
2. Re-route 2-3 existing brace/endurance beats from ambiguous STR/CON to clear CON ownership in `confrontations.yaml`
3. Remove stale `hp / max_hp / ac` entries from `rules.yaml` stat_display_fields (ADR-014 cleanup)
4. Verify on a delve playtest that CON 17 vs CON 9 differs on ≥3 distinct beat types in a single descent

**Files to modify:**
- `sidequest-content/genre_packs/caverns_and_claudes/beat_vocabulary.yaml`
- `sidequest-content/genre_packs/caverns_and_claudes/confrontations.yaml`
- `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`

## Sm Assessment

Trivial workflow (3pt content tuning). Straightforward YAML edits across three files in `sidequest-content/genre_packs/caverns_and_claudes/`. No code, no tests required beyond a delve playtest at the end. Ready for Winchester (Dev) to implement.

**Key references for Dev:**
- ADR-014 (Diamonds and Coal / HP removal) — drives the `rules.yaml` `stat_display_fields` cleanup
- `beat_vocabulary.yaml` schema: each beat has a `stat` tag (STR/DEX/CON/INT/WIS/CHA/etc.) — pattern-match existing CON beats for shape before adding new ones
- `confrontations.yaml` combat tropes — look for "brace", "endurance", "hold the line" style beats currently flagged STR or STR|CON and pick 2-3 to clean up to pure CON
- New CON beats to add (from story body): cave-air poisoning, forced march fatigue, holding breath, cold soak, bad water dysentery
- Acceptance criterion is delve-playtest verification: CON 17 vs CON 9 should differ on ≥3 distinct beat types in a single descent. Verification step is a manual playtest, not an automated test.

**Repo discipline reminders:**
- sidequest-content uses gitflow — PR base is `develop`, not `main`
- This is oq-2 SideQuest — no Jira; sprint YAML is authoritative

**Sibling work:** 39-10 (Edge seed polish) is the planned follow-up after this one merges.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-content/genre_packs/caverns_and_claudes/beat_vocabulary.yaml` — added 5 new CON-flagged obstacles (cave-air poisoning, forced march fatigue, holding breath, cold soak, bad water dysentery)
- `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml` — stripped `hp`/`max_hp`/`ac` from `stat_display_fields` per ADR-014; added 2 universal CON brace beats to confrontations[combat] (`hold_the_line`, `second_wind`); retagged `shield_bash` STR → CON with rewritten narrator hint
- `sidequest-server/tests/genre/test_models/test_pack_integration.py` — updated obstacle-count snapshot assertion 12 → 17; added guard for `CON obstacle count >= 5`

**CON beat distribution (before → after):**
- Total CON beats: 3/35 (8.5%) → 11/42 (26%)
- CON obstacles: 2 → 7 (Flooded chamber, Gas vent + 5 new)
- CON combat beats: 1 → 4 (defend + hold_the_line + second_wind + shield_bash)

**Verification:**
- Genre loader live-load test: PASS (pack parses cleanly, 17 obstacles, 4 CON combat beats, stat_display_fields clean)
- `uv run pytest -k "genre or caverns or confrontation or beat"`: **920 passed**, 2 failed (both pre-existing, unrelated — see Delivery Findings)
- AC verification deferred to manual delve playtest: with 7 CON obstacles + 3 universal CON combat beats always available, any descent should easily hit ≥3 distinct CON beat types when comparing CON 17 vs CON 9 characters.

**Branches:**
- `sidequest-content` → `feat/39-9-con-rebalance-stat-display-cleanup` (pushed; base `develop`)
- `sidequest-server` → `feat/39-9-obstacle-count-assertion` (pushed; base `develop`) — required because the content data shape change invalidated a hardcoded snapshot assertion

**Handoff:** To review phase (Colonel Potter / Reviewer)

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): Pre-existing test failure in `sidequest-server/tests/genre/test_classes_yaml_loader.py::test_classes_yaml_loads_entries` — synthetic class stubs omit the `saving_throws` block but the cloned pack has spellbook/spells, tripping `_validate_saving_throws_refs`. Affects `sidequest-server/tests/genre/test_classes_yaml_loader.py:65-100` (test stub needs B/X B26 `saving_throws` block on all four class fixtures, or test should clone-and-strip spellbook.yaml alongside classes.yaml). *Found by Dev during implementation — confirmed unrelated to story 39-9 by inspecting the validator code path (loader.py:555 / 971-974) which is keyed on classes/spells, not beat_vocabulary or stat_display_fields.*
- **Improvement** (non-blocking): Pre-existing test failure in `sidequest-server/tests/server/test_chargen_dispatch.py::test_caverns_sunden_first_chapter_lore_populates_snapshot` — test reads `snap.location` but Wave 2B (commit 1f77ca9, story 45-48) replaced party-level `location` with per-character `character_locations`. Affects `sidequest-server/tests/server/test_chargen_dispatch.py:612` (switch to `snap.party_location()` or per-character lookup). *Found by Dev during implementation — confirmed pre-existing by examining the API drift; story 39-9 touches no chargen/dispatch code.*

### Reviewer (code review)
- **Improvement** (non-blocking): `hold_the_line.effect` claims "pass durability to the rest of the party until the next round" but the `BeatDef.effect` field is narrator prose only — the `brace` kind in `beat_kinds.py` reduces incoming damage to **self**, not to allies; there is no engine hook (no `target_select`, no `target_edge_delta`, no party-state mutation) that backs the ally-protection claim. Affects `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml:108` (rephrase the effect text to a self-bracing claim such as "Plant the feet — the next blow has to come through you", or add mechanical machinery for ally damage redirection). *Found by Reviewer during code review — note that the existing `taunt.effect` ("so the squishies survive") has the same Illusionism surface, so this is consistent with pack precedent; flagging for future polish rather than blocking, but the OTEL principle (CLAUDE.md) wants narrator promises that match mechanics.*

## Design Deviations

None yet (setup phase).

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Confrontations live in `rules.yaml`, not a separate `confrontations.yaml`** → ✓ ACCEPTED by Reviewer: filename-only inaccuracy in story body; the data is correctly in `rules.yaml:74` per the existing inline forward-port comment.
  - Spec source: 39-9 story body
  - Spec text: "re-route 2-3 existing brace/endurance beats in confrontations[combat] from STR/CON ambiguity into clean CON ownership... `confrontations.yaml`"
  - Implementation: Edited `rules.yaml` (the actual location of the `confrontations:` key per the inline forward-port comment at rules.yaml:70-73). No `confrontations.yaml` file exists in the pack.
  - Rationale: The data is where the data is. Creating a separate `confrontations.yaml` would have required loader plumbing changes (story is content-only).
  - Severity: minor (filename-only inaccuracy in story body)
  - Forward impact: none — future readers of the story body should know the right file is `rules.yaml`.

- **Scope extended to `sidequest-server` for one test assertion** → ✓ ACCEPTED by Reviewer: the test was a snapshot assertion on data shape; bumping it 12→17 is canonical snapshot maintenance, not server-behavior change. The "no server change" in the story body clearly meant no production code; tracking the data count in a test is required maintenance. The CON-obstacle ≥5 guard is a useful drift-detection improvement.
  - Spec source: 39-9 story body
  - Spec text: "Content-only — no server change."
  - Implementation: Updated `sidequest-server/tests/genre/test_models/test_pack_integration.py` to bump the obstacle-count snapshot assertion (12 → 17) and added a CON-obstacle-count guard (≥5). Pushed as a separate branch on the server repo.
  - Rationale: The content change directly invalidates a hardcoded count in a snapshot test. Without the assertion bump, the server CI goes red the moment the content PR merges. Updating the snapshot is mechanically required by the data change and is the canonical maintenance for snapshot tests of this kind. The story author's "no server change" likely meant no production server code; test assertions tracking data shape are a maintenance category.
  - Severity: minor (test-only, scope expansion not behavior change)
  - Forward impact: minor — the merge sequencing is now: server test branch should merge with or just after the content branch to keep server CI green. SM/Reviewer should coordinate.

- **Retagged 1 existing combat beat (shield_bash), added 2 new CON beats, instead of retagging 2-3 existing** → ✓ ACCEPTED by Reviewer: I cross-checked the existing STR/brace beats and Dev's read is correct — `shield_bash` is the only honest STR/CON ambiguity candidate (`attack`/`cleave` are unambiguous sword swings; `parry`/`pray` are class-flavored DEX/WIS). Adding two new universal CON brace beats is mechanically equivalent for the AC. CON distribution went 3/35 → 11/42 — well past the rebalance target.
  - Spec source: 39-9 story body
  - Spec text: "re-route 2-3 existing brace/endurance beats in confrontations[combat] from STR/CON ambiguity into clean CON ownership"
  - Implementation: Only `shield_bash` (currently STR, body-weight slam) had defensible STR/CON ambiguity among existing combat beats. The other STR beats (`attack`, `cleave`) are unambiguously sword-swing STR; existing brace beats `parry` (DEX, Fighter footwork) and `pray` (WIS, Cleric faith) are class-flavored and shouldn't be muddied. Added two new universal CON brace beats (`hold_the_line`, `second_wind`) to reach the "2-3 beats receive CON ownership" intent without forcibly retagging unsuitable ones.
  - Rationale: The literal "re-route existing" only had 1 honest candidate. Adding 2 new universal CON beats is mechanically equivalent for the AC ("CON 17 vs CON 9 differs on ≥3 distinct beat types") and avoids damaging existing class identity.
  - Severity: minor
  - Forward impact: none — final CON distribution exceeds the rebalance target either way.

### Reviewer (audit)
- No undocumented deviations spotted. All scope expansions and design judgments were logged by Dev and are acceptable.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (tests 28/28 GREEN, code_smells 0, schema-validated, loader smoke-test confirms `stat_display_fields` HP cleanup landed) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.test_analyzer=false` |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.comment_analyzer=false` |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.rule_checker=false` |

**All received:** Yes (1 enabled subagent returned clean; 8 subagents pre-disabled by project settings for content-only stories)
**Total findings:** 0 confirmed from subagents, 0 dismissed; 1 LOW finding from Reviewer's own adversarial pass (`hold_the_line.effect` Illusionism risk, non-blocking)

## Devil's Advocate

Arguing this code is broken:

A malicious or careless content editor could ship the same pattern as `hold_the_line` — beats that promise mechanical effects in their `effect` string without engine backing. The narrator agent reads `effect` to color its prose, and Claude is excellent at "winging it" (per CLAUDE.md OTEL principle). A player reading "Plant the feet — pass durability to the rest of the party until the next round" will reasonably ask "did my allies just take less damage?" The narrator can Yes-And the question, but no game state changed; no edge was transferred; no damage was redirected. This is exactly the Illusionism the OTEL system exists to detect. SOUL.md's `The Test` is also relevant in inversion: if the engine reports something that didn't happen, the narration is wrong by omission. The mitigating factor is that the existing pack already has this pattern (`taunt.effect` says "so the squishies survive" with no target redirection mechanic), so this is consistent with established pack idiom — not a new bug class, just one more instance.

What would a confused user misunderstand? A character builder reading the pack might see four CON combat beats (`defend`, `hold_the_line`, `second_wind`, `shield_bash`) and assume CON-focused builds are now first-class for tanks. Mostly true — but `hold_the_line` and `second_wind` are universal (no class_filter), so a Mage with CON 17 has access to two free brace options that compete with their offensive `cast_spell` and `cast_cantrip`. That's by design (universality was the goal), but a power-gamer might find that bracing-Mage builds become surprisingly viable. This is a balance question for playtest verification, not a correctness bug.

What about stressed-filesystem conditions? YAML is read once at server startup via `GenreLoader.load()`. If `rules.yaml` is partially written during a hot-reload, the loader will fail fast (pydantic `model_config = {"extra": "forbid"}` on BeatDef catches unknown fields, model_validator catches structural issues). Not a new failure mode from this story.

What if a downstream test outside the scope I checked still asserts `hp` in `stat_display_fields`? `grep -rn "stat_display_fields" sidequest-server` returned only the field definition at `genre/models/rules.py:468`. No test or handler asserts contents. UI consumers of HP go through `max_hp` on character state, not `stat_display_fields`, so the HP cleanup doesn't touch them (and they're stale-schema per pre-existing project memory anyway). Cleanup is safe.

What about the `feat/39-9-obstacle-count-assertion` branch — could it land out of order? Yes: if the content PR merges to `sidequest-content/develop` before the server PR merges to `sidequest-server/develop`, the server CI on develop will go red on the next run because the test will assert `== 12` against actual data of 17. This is a coordination concern, not a correctness bug — SM should merge the server branch first, or concurrently. Flagged in the deviation audit.

Conclusion: the Devil's Advocate pass surfaces one balance question (universal brace beats), one coordination concern (PR sequencing), and confirms the Illusionism finding already raised. Nothing rises to High/Critical.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** YAML files → `GenreLoader.load("caverns_and_claudes")` (`sidequest-server/sidequest/genre/loader.py`) → `GenrePack.beat_vocabulary.obstacles` (list[ObstacleDef]) and `GenrePack.rules.confrontations[].beats` (list[BeatDef]). Pack-integration tests validate the full deserialization path. Live-loader smoke test (in preflight) confirms 17 obstacles, 4 CON combat beats, and clean `stat_display_fields`. Safe because pydantic `model_config = {"extra": "forbid"}` on `BeatDef` (`sidequest-server/sidequest/genre/models/rules.py:51`) would have rejected any malformed new entry.

**Pattern observed:** New beats follow established pack idiom (`brace` kind + `CON` stat_check + `edge_delta` for composure recovery) — matches existing `defend` (`rules.yaml:96-101`) and `pray` (`rules.yaml:204-212`). New obstacles follow the four-field schema (name/description/stat_check/failure_penalty) used by every other entry in `beat_vocabulary.yaml`. Consistent. No new patterns invented.

**Error handling:** Loader fails fast on schema drift via pydantic validation. No silent fallbacks introduced. Test assertion at `tests/genre/test_models/test_pack_integration.py:186` now includes a CON-count drift guard (≥5), which improves on the prior single-value snapshot.

**Observations (≥5 required):**
- `[VERIFIED]` All 5 new obstacles have full schema: name, description, stat_check=CON, failure_penalty, tags — `beat_vocabulary.yaml:78-105`. Pydantic `model_config = {"extra": "forbid"}` on `BeatDef`/`ObstacleDef` would reject incomplete entries.
- `[VERIFIED]` `shield_bash` retag preserves all non-stat fields — `rules.yaml:121-131`: `class_filter: [Fighter, Cleric]`, `kind: strike`, `base: 4`, `deltas.crit_fail.own: -2`, `risk` text unchanged. Only `stat_check` (STR→CON) and `narrator_hint` (rewritten for endurance flavor) changed.
- `[VERIFIED]` `shield_bash` retag has no class-progression coupling — `grep -rn shield_bash` shows references only in `classes.yaml:19,108` (encounter_beat_choices, by id), `AbilitiesContent.test.tsx` (by id, in test fixture), and `low_fantasy/audio.yaml` (different pack). No code path depends on its STR identity.
- `[VERIFIED]` `edge_delta: 1` on `second_wind` is schema-supported — `BeatDef.edge_delta: int | None = None` at `sidequest-server/sidequest/genre/models/rules.py:122-ish`; engine consumer at `sidequest-server/sidequest/game/beat_kinds.py:549-580` applies `edge_delta` to actor's core via `apply_edge_delta()`. Mechanically active.
- `[VERIFIED]` `stat_display_fields` HP cleanup is safe — `grep -rn stat_display_fields` returns no UI or handler consumers, only the field declaration at `genre/models/rules.py:468`. UI `max_hp` references are on character-state shape (separate path), pre-existing stale-schema per project memory `project_hp_removed.md`. Cleanup is correct per ADR-014.
- `[VERIFIED]` Test assertion update is minimal and adds guard — `tests/genre/test_models/test_pack_integration.py:184-190` and `:325`. Drift detection for CON count (≥5) is an improvement over a single-value snapshot. Preflight confirms 28/28 GREEN on the feature branch.
- `[VERIFIED]` Two pre-existing test failures (`test_classes_yaml_loads_entries`, `test_caverns_sunden_first_chapter_lore_populates_snapshot`) are confirmed unrelated — first is a synthetic-stub omission of `saving_throws` keyed on the spell-validator code path (`loader.py:555,971-974`); second is a Wave 2B API drift (`snap.location` removed). Neither touches beat_vocabulary, confrontations, or stat_display_fields. Logged in Delivery Findings.
- `[LOW]` `hold_the_line.effect` claims ally-protection ("pass durability to the rest of the party until the next round") without engine backing — `rules.yaml:108`. The `brace` kind in `beat_kinds.py` is self-only; no `target_select` or `target_edge_delta` is set. **Illusionism surface.** Mitigating: existing `taunt.effect` has the same pattern, so this is consistent with pack idiom. Non-blocking; suggest rephrase as a future polish ("Plant the feet — the next blow has to come through you") or — if ally protection is intended — add mechanical machinery in a separate story.

**Subagent dispatch tags accounted for:** `[EDGE]` skipped/disabled · `[SILENT]` skipped/disabled · `[TEST]` skipped/disabled (preflight covered test snapshot validation) · `[DOC]` skipped/disabled · `[TYPE]` skipped/disabled · `[SEC]` skipped/disabled (no auth, no I/O, no user input in YAML data) · `[SIMPLE]` skipped/disabled · `[RULE]` skipped/disabled (Python lang-review checklist applied manually to the one .py file — no violations: type-annotated, no exceptions, no logging, no path handling).

**Rule Compliance:**
- **CLAUDE.md No Silent Fallbacks** — Loader fails loudly on schema drift via pydantic `extra: forbid`. ✓
- **CLAUDE.md No Stubbing** — All new entries are fully populated; no placeholder fields. ✓
- **CLAUDE.md Don't Reinvent — Wire Up What Exists** — New beats reuse existing `kind: brace` + `edge_delta` machinery (`beat_kinds.py:549-580`). ✓
- **CLAUDE.md Verify Wiring** — Preflight live-loader smoke test confirms the pack parses through `GenreLoader.load()` and surfaces all expected fields. ✓
- **CLAUDE.md OTEL Observability Principle** — N/A for content-only changes (cosmetic/data category, no subsystem decision); but the LOW finding on `hold_the_line.effect` is tangentially relevant — narration making claims engine can't verify is exactly what OTEL exists to detect. Not blocking.
- **ADR-014 (Diamonds and Coal)** — `stat_display_fields` HP cleanup is the literal target of this ADR. ✓
- **SOUL.md Diamonds and Coal** — New obstacles are appropriately "coal" with bait-shaped descriptions; not overbaited. ✓
- **SOUL.md Genre Truth** — All new flavor (cave-air, cold soak, dysentery) is on-genre for a dungeon-delve pack. ✓
- **SOUL.md Crunch in the Genre** — Mechanical work (CON rebalance) lives in the genre pack, not the engine. ✓
- **Python lang-review (`gates/lang-review/python.md`)** — Only changed .py is a test file: no exception handling, no mutable defaults, type-annotated (`def test_*() -> None`), no logging, no path handling. ✓
- **No project rule violations.**

**Coordination note for SM:** Two branches must merge close together to keep server CI clean:
- `sidequest-content/feat/39-9-con-rebalance-stat-display-cleanup` (data change)
- `sidequest-server/feat/39-9-obstacle-count-assertion` (test assertion catch-up)

Recommend merging the server branch first (test is forward-compatible with both 12 and 17 obstacle counts? No — it now asserts == 17, so it requires the content change to be present to pass against the actual pack on disk). Actually, since the test reads the pack via filesystem path (`CONTENT_ROOT = Path(__file__).resolve().parents[4] / "sidequest-content" / "genre_packs"`), it reads the sibling content repo's working tree. Merging order doesn't matter for the test's local CI; both must merge before the develop branches reflect the new state. **Either-order merge is safe** as long as both land in the same window.

**Handoff:** To SM (Hawkeye) for finish-story