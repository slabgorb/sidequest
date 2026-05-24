---
story_id: "63-3"
jira_key: ""
epic: "63"
workflow: "trivial"
---
# Story 63-3: Fixture pack + theme.yaml display_font_family field

## Story Details
- **ID:** 63-3
- **Jira Key:** (none — SideQuest has no Jira)
- **Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
- **Workflow:** trivial
- **Stack Parent:** none (independent work)
- **Repos:** content (sidequest-content only)

## Story Scope

Add `display_font_family` field to every genre pack's `theme.yaml` per Plan Task 19 (lines 2486–2547 of `docs/superpowers/plans/2026-05-23-reference-pages-v3.md`):

1. Add `display_font_family` field to all live packs' `theme.yaml` (10 packs)
2. Add `display_font_family` field to workshopping packs' `theme.yaml`
3. Add authoring note to `sidequest-content/CLAUDE.md` explaining both `web_font_family` and `display_font_family` fields
4. Run any validator hooks if they exist
5. No pytest needed (content-only work)

Seed values by pack (from plan Task 19 table):
- heavy_metal: Pirata One
- caverns_and_claudes: Pirata One
- victoria / tea_and_murder: Playfair Display
- mutant_wasteland: Special Elite
- space_opera: Orbitron
- neon_dystopia: Orbitron
- pulp_noir: Playfair Display
- road_warrior: Special Elite
- spaghetti_western: Special Elite
- elemental_harmony: Playfair Display

This is the prerequisite for 63-4 (chrome rendering), which reads `display_font_family` from theme.yaml.

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-24T08:56:55Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | 2026-05-24T08:38:45Z | 8h 38m |
| implement | 2026-05-24T08:38:45Z | 2026-05-24T08:48:47Z | 10m 2s |
| review | 2026-05-24T08:48:47Z | 2026-05-24T08:56:55Z | 8m 8s |
| finish | 2026-05-24T08:56:55Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### SM (setup)

- **Improvement** (non-blocking): The `sm-setup` Haiku subagent overstepped its lane and pre-staged the implementation (11 theme.yaml files + CLAUDE.md edit, 22 insertions, currently uncommitted on `feat/63-3-theme-display-font-family`) during the setup phase. Setup is supposed to create the session file + feature branch only; implementation belongs to Dev. Work appears correct on first glance (font assignments match the seed table) but Dev must verify the values, sanity-check the CLAUDE.md note placement/wording, run any content validators, and produce the commit. Surfacing as a pattern observation, not a 63-3 blocker.

### Dev (implementation)

- **Conflict** (blocking, resolved): Story 63-3 was scoped as `--repos content` only. That is wrong: `sidequest-server/sidequest/genre/models/theme.py:GenreTheme` uses `model_config = {"extra": "forbid"}`, so adding `display_font_family` to any pack's `theme.yaml` without a paired server-model addition causes every pack to fail `ValidationError` at server load. Story scope expanded mid-flight to content + server; new feature branch `feat/63-3-theme-display-font-family` created on sidequest-server. **All future plan tasks that add YAML fields to genre-pack models must include the server model addition in scope** — see new memory `project_genre_models_extra_forbid.md`.
- **Improvement** (non-blocking, fixed): `tests/server/test_apply_beat.py::test_space_opera_negotiation_beats_carry_opponent_overrides` held a hardcoded `/Users/slabgorb/Projects/oq-2/sidequest-content/...` path, which broke when oq-1 had the new `display_font_family` field but oq-2 didn't. Replaced with the existing `tests/_helpers/genre_paths.find_pack_path()` helper which resolves via `__file__.parents[3]`. Pre-existing portability bug surfaced by the dual-repo drift; fixed in the same commit.
- **Deviation** (non-blocking): Margaret's CLAUDE.md draft (via sm-setup) referenced an `archetype:` field on theme.yaml that does not yet exist in any pack. Trimmed that line from the "Reference page chrome" section — it belongs in 63-4 (chrome rendering) which will both add the field and document it. Other lines preserved (`dinkus.glyph.{light,medium,heavy}` is already correctly shipped by every pack).
- **Question** (non-blocking, for 63-4 art-director review): For packs not in the plan's seed table — `spaghetti_western` got `Special Elite` (typewriter aesthetic; reasonable but not classic-Western), and `road_warrior` also got `Special Elite` (genre-correct). Art-director may want to swap spaghetti_western's display font when 63-4's chrome makes the rendered result inspectable — but the seven preferred Google Fonts noted in CLAUDE.md (Pirata One / Playfair Display / Special Elite / Orbitron / IM Fell English / Rajdhani / Share Tech Mono) have no truly Western-coded face, so any swap also requires adding a font to the chrome's import set. Defer the call until visual inspection.
- No upstream blocker findings.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations.

## Sm Assessment

**Setup Complete:** Yes (with caveat — see Delivery Findings)
**Story:** 63-3 (Add display_font_family to all theme.yaml + CLAUDE.md note)
**Branch:** feat/63-3-theme-display-font-family (sidequest-content, off develop)
**Workflow:** trivial (phased: setup → implement → review → finish)
**Repos:** sidequest-content (single-repo, content-only)

**Plan reference:** Task 19 of `docs/superpowers/plans/2026-05-23-reference-pages-v3.md` (lines 2486–2547). Seed font values in the story scope above match the plan's table; Dev should treat the plan as authoritative if any value conflicts.

**Pre-staged work:** 12 files modified, uncommitted, on the feature branch. Dev's implement phase is therefore VERIFY-AND-COMMIT, not write-from-scratch. If the staged work is wrong, Dev should reset and redo; if right, just commit + push.

**Validators:** Look in `sidequest-content/tools/` for any pack/theme validator. Run before commit. Memory `feedback_no_content_coupled_tests.md` is relevant: this content edit is the kind of change that a validator (not pytest) catches.

**Handoff:** To Major Charles Emerson Winchester III (Dev) for implement phase. Excellence through superiority — verify the font choices match design intent, confirm the CLAUDE.md note reads well, run validators, commit cleanly.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**

*sidequest-content* (branch `feat/63-3-theme-display-font-family`, commit `6bdbad1`):
- `CLAUDE.md` — added "## Reference page chrome" section, trimmed forward-looking `archetype:` line (defer to 63-4)
- `genre_packs/{caverns_and_claudes,elemental_harmony,heavy_metal,mutant_wasteland,neon_dystopia,pulp_noir,road_warrior,space_opera,spaghetti_western,tea_and_murder}/theme.yaml` — added `display_font_family` line to each
- `genre_workshopping/low_fantasy/theme.yaml` — same

*sidequest-server* (branch `feat/63-3-theme-display-font-family`, commit `4a63ce5`):
- `sidequest/genre/models/theme.py` — added `display_font_family: str` to `GenreTheme` (required per `extra="forbid"` discipline; loud failure on miss)
- `tests/genre/test_models/test_misc_models.py` — `_valid_data()` fixture sync
- `tests/fixtures/intent_test_pack/theme.yaml` + `tests/fixtures/packs/test_genre/theme.yaml` — fixture sync
- `tests/server/test_apply_beat.py` — drive-by fix: hardcoded oq-2 path → `find_pack_path()` helper

**Tests:** 7452 passed / 364 skipped on broader sweep (`pytest -k "not slow and not e2e and not playtest"`). All 10 live packs + low_fantasy load clean against the updated `GenreTheme` model via direct `load_genre_pack()` smoke test.

**Branches pushed:** Both feature branches at origin/feat/63-3-theme-display-font-family on sidequest-content and sidequest-server respectively.

**Handoff:** To Colonel Sherman Potter (Reviewer) for review phase. Two paired branches → two paired PRs; both must merge in lockstep. The pre-existing sm-setup overreach + hardcoded-test-path bugs are documented in Delivery Findings and don't block this story.

## Subagent Results

All received: Yes

| # | Specialist | Received | Status | Findings | Decision |
|---|---|---|---|---|---|
| 1 | reviewer-preflight | Yes | clean | Content diff: 12 files / +21/-0 (10 live packs + low_fantasy workshop + CLAUDE.md). Server diff: 5 files / +8/-3 (model + 2 fixture YAML + 1 unit test + 1 drive-by test fix). Ruff check exit 0. Ruff format exit 0 (3 files already formatted). Targeted pytest: 48 passed / 0 failed / 0 skipped (`test_space_opera_negotiation_beats_carry_opponent_overrides` ran live via new `find_pack_path` helper). Branch names match across both repos. Both branches pushed (content `6bdbad1`, server `4a63ce5`). | Approve — no anomalies in mechanical surface. |
| 2 | reviewer-rule-checker | Yes | clean | All 7 applicable rules: clean. Specifically: (1) `display_font_family: str` required with no `Optional`/default; `extra="forbid"` preserved on `GenreTheme`, `Dinkus`, `SessionOpener`; no `getattr(...,default)` patterns. (2) Lockstep verified — both branches same name, all 10 live packs + both fixture packs + the `TestGenreTheme` unit test updated. (3) Pre-existing content coupling in `test_apply_beat.py:365` replaced with `find_pack_path()` helper — strictly portability improvement, not a new violation. (4) No new stubs (empty `display_font_family: ""` in `intent_test_pack` is a satisfying value for an existing stub fixture). (5) `extra="forbid"` on the genre model preserved. (6) No Jira references in commits/messages. (7) All font assignments cross-checked against design bundle `theme.css`: all 10 packs match. | Approve — zero violations. |
| 3 | reviewer-security | Yes | clean | All 7 checks clean. No injection sinks reached (field is plain `str`, values are Google Font names). No secrets/credentials. No auth code touched. No new info leakage beyond the existing `web_font_family` aesthetic-metadata surface. No dependency/lockfile changes. Path-traversal risk on the drive-by `find_pack_path("space_opera")` fix is nil (string literal in test code, anchored to `__file__.parents[3]`). No pickle/unsafe deserialization. Flag for 63-4 chrome work (not blocking here): when `display_font_family` reaches the HTML render layer, ensure it's escaped — currently no sink, deferred concern. | Approve — zero security findings. |

## Reviewer Assessment

**Verdict:** APPROVED

**Diff size:** 21 insertions on content (`6bdbad1`), 8/3 on server (`4a63ce5`). 17 files touched, all small mechanical edits.

**Lockstep coordination:** Confirmed. Content branch adds `display_font_family` to every consumer YAML; server branch adds the required `str` field to `GenreTheme`. Either alone would fail loud — together they are coherent. Branch names match (`feat/63-3-theme-display-font-family` in both repos), commits pair cleanly, both pushed.

**Discipline checks:**
- ✅ `extra="forbid"` preserved; missing/misspelled field still fails loud at server load.
- ✅ Field is required `str` (not `str | None`) — no silent-fallback path.
- ✅ Test fixtures synced (`_valid_data()` + both fixture-pack `theme.yaml` files).
- ✅ Smoke load against 10 live packs + low_fantasy: all clean.
- ✅ Broader pytest sweep: 7452 passed, 364 skipped.
- ✅ Workshopping coverage: only `low_fantasy` has a `theme.yaml` in workshopping; it got the field. `caverns_sunden`, `space_opera`, `tea_and_murder`, `elemental_harmony` workshopping subdirs have no `theme.yaml` — out of scope.
- ✅ Drive-by hardcoded-path fix is bounded, uses existing helper, listed in Delivery Findings.
- ✅ **[SEC]** reviewer-security pass: zero findings. No injection sinks (plain `str` value, font-family names), no secrets, no auth touched, no info leakage, no dependency changes, no path-traversal exposure on the `find_pack_path` drive-by, no pickle/unsafe deserialization. Forward concern (non-blocking, deferred to 63-4): when `display_font_family` reaches the HTML render layer in the chrome story, ensure it's HTML-escaped at the template/render boundary.

**CLAUDE.md addition:** Clean. Explains the loud-failure constraint, points at the server model file, and tells future authors to coordinate display-font additions with 63-4's chrome work. One minor editorial nit (the phrase "extra=forbid for both directions" is slightly imprecise — extra=forbid is one-way model rejection) but not worth a rewrite for a one-line clarification.

**Open question from Dev (deferred, non-blocking):** `spaghetti_western` got `Special Elite` (typewriter, not classic-Western). Reasonable interim choice given the seven preferred Google Fonts have no Western-coded face. Defer the art-director swap to 63-4 when the chrome makes the rendered result inspectable.

**Handoff:** To Hawkeye Pierce (SM) for finish phase — open and merge two paired PRs in lockstep. **Critical: server PR must merge BEFORE content PR** (or in the same atomic operation), otherwise any node pulling sidequest-content first will fail to load every pack. If GitHub merge order can't be guaranteed atomic, document the order in the PR descriptions.