---
story_id: "45-7"
jira_key: ""
epic: "45"
workflow: "trivial"
---
# Story 45-7: Race-aware character description template (split from 37-40 sub-4)

## Story Details
- **ID:** 45-7
- **Jira Key:** (personal project, not tracked)
- **Workflow:** trivial
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p1

## Story Context

Playtest 3 evropi: every save shipped 'A Human {class}' regardless of race (prot_thokk Half-Orc, hant Antman, pumblestone Gnome, rux Kobold). Chargen sets description from a human-assumed template before race substitution. Wire the template to actual race output, or restructure so race is interpolated correctly.

### Root Cause

The character description template in chargen is hardcoded to use "A Human {class}" and does not reflect the actual character race selected during character creation. The race is set elsewhere in the pipeline, but the description template doesn't interpolate it.

### Acceptance Criteria

1. Character description template reflects the selected race (not hardcoded to "A Human")
2. Description format: "A {race} {class}" or equivalent per genre pack
3. Verified across at least one world save that displays the correct description
4. No side effects on other chargen outputs

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-04-28T00:37:01Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28T00:37:01Z | - | - |

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/world_materialization.py` — added `_auto_description` / `_is_auto_description` helpers; create-branch falls back to `A {race} {class}` instead of `An adventurer.`; update branch refreshes the auto-template description when chapter race or class changes; emits `world_materialization.description_refreshed` OTEL event.
- `sidequest-server/tests/game/test_world_materialization.py` — extended two existing tests to assert description text; added two new regression tests (race-change refresh + hand-authored preservation).

**Tests:** 34/34 in test_world_materialization.py; full server suite 2666 passed, 34 skipped.
**Branch:** `feat/45-7-race-aware-character-description-template` (pushed in sidequest-server). No content changes needed.
**PR:** https://github.com/slabgorb/sidequest-server/pull/90

**Handoff:** To review

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Gap** (non-blocking): Story brief says "chargen template is hardcoded to A Human". Code in `sidequest/game/builder.py:1597` already uses `f"A {race_str} {class_str}"`, and `race_str = acc.race_hint or self._default_race or "Human"` (line 1284). The actual bug surfaced in the playtest saves was downstream: `_apply_character` in `sidequest/game/world_materialization.py` updates `char.race` from chapter data but never refreshed the auto-template `core.description`, so a chapter that set race=Half-Orc on a chargen-built character with `description="A Human Fighter"` left the description stale. *Found by Dev during implementation.*
- **Improvement** (non-blocking): If chapters/scenarios are constructing player Characters directly (not via the chargen builder), they should populate `description` explicitly. The new auto-template fallback in `_apply_character` is a safety net, not a license to skip authoring. *Found by Dev during implementation.*
- **Question** (non-blocking): The four playtest saves (prot_thokk, hant, pumblestone, rux) reference races (Half-Orc, Antman, Gnome, Kobold) that aren't in the evropi `char_creation.yaml` race list (Zkęd/Aldkin/Waterfolk/Mistos/Vaermm/Jambiendo/...). These look like fixture/scenario characters built outside the genre-pack chargen flow. Worth confirming the fixture path also hits `_apply_character` — current fix covers it, but the upstream choice of using D&D-style races for an evropi save deserves a separate look. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Bug location moved from chargen builder to world_materialization:** Spec said "chargen template is hardcoded to A Human; wire the template to use actual race". Code investigation showed the chargen template was already race-aware (`f"A {race_str} {class_str}"` in `builder.py:1597`). The actual bug was in `_apply_character` (`world_materialization.py`) which updated race/class from chapter data without refreshing the auto-template description. Implemented the fix where the bug actually lives — added `_auto_description` / `_is_auto_description` helpers, refresh on race/class change when prior description matches the auto-template, and use the auto-template (not "An adventurer.") as the create-branch fallback. Reason: do X, not Y — fix the actual bug.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** chargen confirmation → `session_handler.py:2392` `materialize_from_genre_pack` → `WorldBuilder.build()` → `_apply_chapter` → `_apply_character`. Both create-new (line 328) and update-existing (line 370) paths exercised. Builder's auto-template (`builder.py:1597` `f"A {race_str} {class_str}"`) is byte-identical to `_auto_description`'s output, so the heuristic is exact-match safe.

**Pattern observed:** Heuristic refresh gated on `race_or_class_changed AND _is_auto_description(prev)` — strict equality, no fuzzy fallback. Aligns with CLAUDE.md "No Silent Fallbacks." OTEL event `world_materialization.description_refreshed` emitted at `world_materialization.py:409` with full before/after attribution — Sebastien-visible in GM panel.

**Error handling / null-safety:** `CreatureCore.description` is non-blank-validated (`creature_core.py:201-205`), so `prev_description` is guaranteed a non-None string — `==` comparison in `_is_auto_description` is safe. `ChapterCharacter.description: str | None` with `if char_data.description:` skips both None and empty.

**Wiring:** Confirmed end-to-end. Production caller is `sidequest/server/session_handler.py:2392` (chargen world_materialized event). No half-wired component.

**Test coverage:**
- Create-path: `test_character_created_when_snapshot_empty` (assert `"A Gnome Delver"`), `test_character_created_with_defaults_when_blank` (assert `"A Human Fighter"`).
- Update-path race-change refresh: `test_character_description_refreshed_when_chapter_changes_race` (auto-template `A Human Fighter` → `A Half-Orc Fighter`).
- Hand-authored preservation: `test_character_description_preserved_when_hand_authored`.
- Coverage of class-change-only and combined race+class change is implicit in the heuristic but not asserted directly. Acceptable for trivial-story scope.

**Observations (5+):**
1. (verified good) Helper format is byte-identical to `builder.py:1597` — refresh heuristic catches every chargen-emitted description.
2. (verified good) OTEL event includes prev/new race/class/description — fully GM-panel-verifiable per CLAUDE.md observability principle.
3. (verified good) Update path uses `prev_description` snapshot before any field mutation, so detection runs against pre-update state. Order is correct.
4. (LOW, non-blocking) `_is_auto_description` strict-eq means a hand-authored description that *coincidentally* reads "A Half-Orc Fighter" would be clobbered if the chapter then changed class. Probability negligible; acceptable trade-off documented in the helper docstring.
5. (LOW, non-blocking) No explicit test for class-change (only race-change) on the refresh path. Same code path; not worth a follow-up.
6. (verified good) Lint error in `sidequest/game/world_materialization.py:72` (`CampaignMaturity` should inherit from `StrEnum`) is preexisting on `develop`; out of scope.
7. (verified good) Trivial-workflow scope respected — Dev did not boy-scout adjacent description handling in NPC apply or session.py despite similar shape.

**Test status:** 34/34 in `test_world_materialization.py`. Dev reports 2666 passed / 34 skipped on full server suite. Lint clean on changed lines.

**Severity table:** No Critical, no High, no Medium. Two Low non-blocking notes recorded above.

**Handoff:** To SM for finish-story.
