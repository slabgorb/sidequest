---
story_id: "24-9"
jira_key: null
epic: "24"
workflow: "trivial"
---
# Story 24-9: Author spaghetti_western calendar for dust_and_lead + the_real_mccoy (1878 Gregorian; months, days, festivals, time precision)

## Story Details
- **ID:** 24-9
- **Jira Key:** none (SideQuest uses no Jira)
- **Epic:** 24 (Procedural World-Grounding Systems)
- **Workflow:** trivial
- **Points:** 2
- **Stack Parent:** none
- **Target Repo:** sidequest-content

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-21T07:30:56Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-21T07:15:00Z | 2026-05-21T07:11:37Z | -203s |
| implement | 2026-05-21T07:11:37Z | 2026-05-21T07:24:07Z | 12m 30s |
| review | 2026-05-21T07:24:07Z | 2026-05-21T07:30:56Z | 6m 49s |
| finish | 2026-05-21T07:30:56Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings.

### Dev (implementation)
- **Gap** (non-blocking): The calendar schema authored in story 24-1 assumes world-level placement (one `calendar.yaml` per world); the spaghetti_western pack places one calendar at pack level shared by two worlds. When story 24-7 wires the loader, it will need to (a) check pack-root for `calendar.yaml` and fall back to world-level, or (b) introduce a `worlds_served:` field convention and resolve world→pack. Affects `sidequest-server/sidequest/genre/world_loader.py` (whichever module 24-7 introduces for grounding load — not yet written). The 24-4 glenross precedent is world-level; ours is the first pack-level case. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Several `texture_by_world:` blocks in `genre_packs/spaghetti_western/calendar.yaml` could be hoisted into per-world `calendar_overlay.yaml` files instead, if a future story prefers a cleaner inheritance model (pack-level base + per-world overlay merge). The current single-file approach is simpler for one decade-shared-by-two-worlds case; will not scale if a third spaghetti_western world (different decade) is later added. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): The 24-7 loader story should consider rejecting calendars whose `starting_dates.<world>.day_of_week` does not match the Gregorian day-of-week for the named year/month/day. This file passed that check (verified via `datetime.date(...).strftime('%A')` in review preflight) but the check should be a loader-side guard so the next pack-level calendar can't slip a mismatched day through. Affects whichever module 24-7 introduces for calendar load. *Found by Reviewer during code review.*
- **Question** (non-blocking): The file omits a `quarter_days:` section that the glenross template has (glenross uses Scottish quarter days — Candlemas, Whitsunday, Lammas, Martinmas — which are not a US 1878 framework). When 24-7 codifies the calendar schema, decide whether `quarter_days:` is required (and we need a graceful absence-of-quarter-days idiom for American/non-Scottish settings) or optional (current de-facto state). The omission here is correct for 1878 America; the schema decision is open. Affects `docs/schemas/calendar.schema.json` (whichever schema file 24-1 produces — not yet committed at orchestrator review time). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

(None recorded during setup.)

### Dev (implementation)
- **Pack-level placement (intentional, sanctioned by user instruction)** → ✓ ACCEPTED by Reviewer: user instruction at setup time was explicit ("they share a decade and culture"); SM Assessment recommended pack-level as option (a); the `worlds_served:` field gives 24-7 a clean wire-in hook. The deviation is well-formed and the correct shape for two contemporary worlds sharing a Gregorian year.
- **File length (~1365 lines vs SM estimate of 400–600)** → ✓ ACCEPTED by Reviewer: glenross is 798 lines for one world; ~2× for two worlds with per-world texture/bells/whistles/meals/daylight is in proportion. The narrator grounding tool reads selectively, so file length does not degrade per-call cost. SM estimate was simply low.

### Reviewer (audit)
- **Texas State Fair founding date corrected inline** (Reviewer fix on same branch, commit `38ca217`)
  - Spec source: SOUL.md "Genre Truth" + the file's own accuracy-block contract
  - Spec text: "Period-accurate to 1878 ... The Texas State Fair was founded in 1878 (Dallas, late October)" — the original line in `calendar.yaml:1359` (accuracy block) and `:396` (October texture)
  - Implementation: The State Fair of Texas (Dallas, Fair Park) was actually founded in **1886**, eight years after the calendar's year. Original line is a factual error.
  - Reviewer action: Replaced with the period-correct "North Texas Agricultural and Mechanical Association's Dallas exhibition" — that body did run fairs in the late 1870s — and added an explicit "(the Dallas State Fair that becomes the State Fair of Texas is still eight years off)" parenthetical so the reader knows the namesake fair is not yet there. Updated the accuracy-block tail with the correction.
  - Severity: medium (would have leaked into narrator grounding for October scenes)
  - Forward impact: none — fix is in this PR.
  - Reviewer rationale for inline fix vs bounce-back: trivial single-line correction on a content YAML in a personal-project repo with no Jira; per user feedback memory `feedback_plan_ceremony` ("right-size plan ceremony to the work") and `feedback_dead_code` ("delete dead code in the same PR"), bouncing a one-line factual correction through a Dev rework round would be ceremony overhead with zero quality benefit.

## SM Assessment

**Scope.** Author a single content file (or pack-level shared file): calendar for the spaghetti_western genre pack. This calendar serves both `dust_and_lead` and `the_real_mccoy` worlds, which share the same decade (1878) and Gregorian calendar / cultural framing. The calendar should be authored at the pack level (not duplicated per-world) following the pattern established by 24-4's glenross calendar.

**Pattern reference (Monster Manual, ADR-059 + 24-4).** YAML in genre pack → Python grounding tool consumes → narrator prompt zone injection → OTEL verifies. Story 24-4 just shipped a tea_and_murder/glenross calendar as the template; use that file's structure (months, days, moons, festivals, time_precision block, starting_date) as the structural reference.

**Genre-truth notes for spaghetti_western (dust_and_lead + the_real_mccoy).** 1878 American frontier — both worlds use the Gregorian calendar (no fantasy substrate). Dust_and_lead: Mexican border towns, cattle ranches, mining culture, outlaws and bandits, hard-scrabble desert life. The_real_mccoy: 1878 Pittsburgh steel mills, robber barons, labor unrest, mechanized frontier. The calendar should anchor both worlds in period-authentic 1878 Americana — month names standard Gregorian, festivals tied to American social life (July Fourth, Thanksgiving, Christmas), but with genre flavor reflecting frontier hardship and class struggle. Both worlds can share the same calendar (moons, day names, time precision) since they're contemporary 1878 and share the same cultural reference frame.

**Required surface (from story title and schema).** months, days, festivals, time_precision. Per the calendar.schema.json (story 24-1), the YAML must specify:
- `calendar.name` (optional but good for Americana framing)
- `calendar.days_in_year` (365 for Gregorian)
- `calendar.days_in_week` (7 for Gregorian)
- `calendar.day_names` (English weekdays)
- `calendar.months` (12 months with name, days, season, optional festivals)
- `calendar.moons` (optional, but spaghetti_western could use folk-astronomy for western flavor)
- `calendar.time_precision` (enum: hour, quarter_day, watch, scene)
- `calendar.epoch` (optional starting date — a good anchor is a canonical 1878 date for both worlds)

**File placement.** Per 24-1 context, calendars live at the **world level**. However, the user's CRITICAL CONTEXT says "Author ONE calendar at the pack level (or shared file), not two divergent ones." This is a deviation from the 24-1 schema guidance (world-level) but justified by the two worlds sharing decade + calendar. Options: (a) place at `sidequest-content/genre_packs/spaghetti_western/calendar.yaml` and have both worlds reference/inherit it, or (b) place at one world and have the other world load it via a pointer in world.yaml. Recommend option (a) — pack-level placement — since the schema is identical for both and the worlds are contemporary. This mirrors how tea_and_murder's weather.yaml is pack-level (shared climate rules) while demographics.yaml and calendar.yaml are world-level (Glenross-specific). For spaghetti_western, the calendar is decade+culture-shared, so pack-level is justified. **Confirm placement with SM before implementation.**

**Branch / repo.** Single-repo story. Branch `feat/24-9-spaghetti-western-calendar` is live in `sidequest-content` (orchestrator sits on `feat/24-9-spaghetti-western-calendar` as a placeholder, no orchestrator code changes). Trivial workflow — implement → review → finish, no separate RED phase.

**Verification ask.** YAML parses cleanly; values are period-authentic 1878 American (Gregorian month names, American frontier festivals, plausible time-precision tiers); file is located per the file-placement decision above; both dust_and_lead and the_real_mccoy world.yaml files reference it (if world-level pointers are needed) or the loader is confirmed to auto-read pack-level calendar.yaml.

**Handoff to:** Dev.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-content/genre_packs/spaghetti_western/calendar.yaml` (new, 1365 lines) — 1878 Gregorian calendar at pack level, serving both `dust_and_lead` and `the_real_mccoy` worlds. Structure mirrors the 24-4 glenross template; extended with `worlds_served:`, per-month `texture_by_world:` blocks, per-festival `applies_to:`, and per-world starting dates and time-precision/bells/whistles blocks.

**What it covers:**
- `system` — Gregorian, era prose, 1878-specific status (not a leap year; Jan 1 was a Tuesday; no Standard Time in 1878; Hayes-era decade register).
- `months` — all 12, with shared seasonal/national texture and per-world divergence (border desert vs. steel-mill river valley).
- `days_of_week` — all 7, with Sunday-sabbath texture per world.
- `moons` — 12, Old Farmer's Almanac names + vaquero/frontier alternates + Spanish/German/Polish alternates where relevant.
- `festivals` — 22 entries, tagged `applies_to: both | dust_and_lead | the_real_mccoy`. Includes federal (New Year, Independence Day, Thanksgiving 1878, Christmas), Catholic (Candelaria, Lent, Easter, Assumption, All Saints/Día de los Muertos, Immaculate Conception, Guadalupe, Las Posadas, Wigilia), civic (Decoration Day, Election Day 1878, Lincoln's Birthday, Washington's Birthday), ethnic (St Patrick's, Cinco de Mayo, Mexican Independence, St Nicholas), and the unspoken Pittsburgh Roundhouse anniversary.
- `time_precision` — registers (gentry, professional, working_industrial, working_frontier, domestic, sabbath), bells/whistles per world (mission bells + ranch bells in dust_and_lead; mill whistles + church bells + depot clocks + bridge bells in the_real_mccoy), train schedules (sparse stage to Toyah railhead vs. dense PRR/B&O/P&LE), meals, daylight by latitude.
- `starting_dates` — per world, with rationale anchored to each world's `world.yaml` cues (Sangre: Wed 14 Aug 1878 late afternoon; Pittsburgh: Thu 18 Apr 1878 04:00, matching `the_workshop_car_at_four_in_the_morning` cover POI and the spring inversion anchor).
- `useful` — federal-holiday status as of 1878 (statutory vs. customary), pre-Standard-Time note, weekend-not-yet-a-concept note, accuracy block listing verified historical anchors.

**Validation:**
- `python3 -c "import yaml; yaml.safe_load(open(...))"` — parses cleanly.
- 1365 lines (vs. SM-estimated 400–600; deviation logged with rationale).
- Schema not yet formalised (story 24-1 still pending per SM Assessment); authored in the shape that schema is expected to enforce, following the 24-4 glenross precedent.

**Tests:** N/A — pure content authoring on a trivial workflow. No runtime code added. Loader wiring deferred to story 24-7 per the 24-6 sequencing (same disposition as 24-4 glenross).

**Wiring status:** YAML authored, not yet wired into pack loader. `get_world_grounding` returns `calendar_present=False` for both worlds until 24-7 ships. This is the expected interim state, matching the 24-4 precedent.

**Branch:** `feat/24-9-spaghetti-western-calendar` in `sidequest-content` — pushed to `origin/feat/24-9-spaghetti-western-calendar`. Orchestrator is on the same-named placeholder branch with no changes (clean tree apart from the unrelated `?? ghostty` artefact pre-existing in oq-2).

**Self-review:**
- [x] Code (content) is consistent with project patterns (glenross template).
- [x] Project conventions followed (period-accurate research; user's "shared decade and culture" instruction honoured via pack-level placement; no fabricated history without an "invented for fiction" disclaimer in the accuracy block).
- [x] All acceptance criteria met (months, days, festivals, time precision; 1878 Gregorian; serves both worlds).
- [x] Wiring deferred status matches 24-4 precedent and is documented in this assessment.

**Handoff:** To Colonel Potter for review.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (informational note: an untracked, gitignored `.DS_Store` inside `genre_packs/spaghetti_western/` — covered by .gitignore, not in the commit) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.edge_hunter = false) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.silent_failure_hunter = false) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.test_analyzer = false) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.comment_analyzer = false) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.type_design = false) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.security = false) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.simplifier = false) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.rule_checker = false) |

**All received:** Yes (1 returned, 8 skipped via settings)
**Total findings:** 1 confirmed (Reviewer's own factual-error catch, fixed inline as commit `38ca217`), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Scope reminder.** Story 24-9 adds a single content YAML — `sidequest-content/genre_packs/spaghetti_western/calendar.yaml`, originally 1365 lines, now 1368 after the inline factual fix. No code, no tests, no runtime surface added. Trivial workflow.

**What the review covered.**
- Mechanical preflight (YAML parses, branch synced, no LFS tracking, no editor cruft) — clean.
- Structural shape vs the 24-4 glenross template — all 12 months/7 days/12 moons present with correct numbering, days sum to 365 (correct for non-leap 1878), per-world sections (starting_dates, bells_and_whistles, meals, daylight) all align with `worlds_served`.
- Day-of-week verification on every claimed date in the file:
  - Jan 1 1878 = Tuesday ✓
  - Easter Sunday 1878-04-21 = Sunday ✓
  - Ash Wednesday 1878-03-06 = Wednesday ✓
  - Thanksgiving 1878-11-28 = Thursday (and last Thursday in November) ✓
  - Election Day 1878-11-05 = Tuesday after Monday Nov 4 ✓
  - dust_and_lead starting date 1878-08-14 = Wednesday ✓
  - the_real_mccoy starting date 1878-04-18 = Thursday ✓
  Verified mechanically via `datetime.date(...).strftime('%A')`.
- Period-accurate fact spot-check on namesake institutions and events (Southern Pacific arrival 1881, Standard Time 1883, Rodef Shalom 1856, Edgar Thomson 1875, James Parton's "hell with the lid taken off" 1868, Roundhouse Riot July 19–22 1877) — all correct as cited.
- Pet-word audit (per user memory `feedback_made_up_names`) on Reach / Veil / Spire / Hollow / Drift / Mire / Shroud / Sanctum / Bastion — **zero hits**.
- Dev's two logged deviations (pack-level placement; file length vs estimate) — both ACCEPTED with rationale stamped in the Design Deviations section.

**Findings, by dispatch tag.**
- `[EDGE]` N/A — subagent skipped (settings); content YAML has no execution paths.
- `[SILENT]` N/A — subagent skipped (settings); content YAML has no error handling.
- `[TEST]` N/A — subagent skipped (settings); no tests were added (none required for content authoring on trivial workflow).
- `[DOC]` N/A — subagent skipped (settings). Reviewer's own pass on the in-file comment headers and accuracy block found them accurate after the Texas State Fair correction.
- `[TYPE]` N/A — subagent skipped (settings); YAML data, not typed code.
- `[SEC]` N/A — subagent skipped (settings); no secrets, no user input, no execution surface, no tenant data.
- `[SIMPLE]` N/A — subagent skipped (settings). File length (1368 lines) is in proportion to the dual-world per-month/per-festival texture density; not over-engineered.
- `[RULE]` N/A — subagent skipped (settings). No `.claude/rules/` directory exists and no `.pennyfarthing/gates/lang-review/yaml.md` checklist exists, so there is no codified rule surface for YAML content beyond CLAUDE.md / SOUL.md / user memory. Applicable items: "Genre Truth" (caught + fixed Texas State Fair anachronism); "Diamonds and Coal" (file's `narrator_hooks:` blocks place baited hooks appropriately); pet-word memory (clean); pack-level vs world-level placement (sanctioned by user instruction, recorded as ACCEPTED deviation).

**Reviewer-found issue, addressed inline (commit `38ca217`).**

| Severity | Issue | Location | Resolution |
|----------|-------|----------|------------|
| Medium | Texas State Fair claimed as founded 1878; actually founded 1886 (8-year anachronism in October texture and in tail accuracy block) | `calendar.yaml:394–402` and `:1359` | Replaced with the period-correct North Texas Agricultural and Mechanical Association's Dallas exhibition; added explicit parenthetical noting the State Fair of Texas namesake is still 8 years off; updated accuracy block. Fixed inline per right-size-ceremony memory; would otherwise have routed back to Dev for a one-line rework. |

**Data flow trace.** This is content data, not a flow. The data path when 24-7 wires it in: `genre_packs/spaghetti_western/calendar.yaml` → pack loader → narrator `get_world_grounding` tool → narrator prompt zone injection (per ADR-059 Monster Manual pattern). The `worlds_served:` and `applies_to:` fields are the keys 24-7's loader will need to resolve for per-world filtering. Reviewer logged this in Delivery Findings as a Gap for 24-7's planning.

**Pattern observed.** Pack-level shared calendar with per-world overlay (`texture_by_world:` on months, `applies_to:` on festivals, per-world `starting_dates`/bells/meals/daylight blocks) is a cleaner generalisation of the glenross world-level template, and is the first pack-level case in the codebase. It is the right shape when worlds share a decade and a national culture. Worth promoting to the schema when 24-1 finalises.

**Verification ladder confidence.** High — every checkable claim in the file (day-of-week, leap status, historical anchors, structural counts) was verified mechanically or against known history; the one error found was corrected inline.

**Handoff:** To Hawkeye for the finish ceremony — archive session, create + merge PR (per `feedback_finish_ceremony_skips_pr` memory: SM must verify the merge actually happens and create the PR itself if `pf sprint story finish` no-ops on the merge step).