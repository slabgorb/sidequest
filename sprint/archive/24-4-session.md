---
story_id: "24-4"
jira_key: null
epic: "24"
workflow: "trivial"
---
# Story 24-4: Author tea_and_murder/glenross calendar (months, days, moons, festivals, time precision)

## Story Details
- **ID:** 24-4
- **Jira Key:** none (SideQuest uses no Jira)
- **Epic:** 24 (Procedural World-Grounding Systems)
- **Workflow:** trivial
- **Points:** 2
- **Stack Parent:** none
- **Target Repo:** sidequest-content

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-20T23:28:27Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-20T18:57:00Z | 2026-05-20T23:01:21Z | 4h 4m |
| implement | 2026-05-20T23:01:21Z | 2026-05-20T23:10:42Z | 9m 21s |
| review | 2026-05-20T23:10:42Z | 2026-05-20T23:18:39Z | 7m 57s |
| implement | 2026-05-20T23:18:39Z | 2026-05-20T23:24:08Z | 5m 29s |
| review | 2026-05-20T23:24:08Z | 2026-05-20T23:28:27Z | 4m 19s |
| finish | 2026-05-20T23:28:27Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Gap** (non-blocking): The pack loader does not yet read `calendar.yaml` into the `World` model. Affects `sidequest-server/sidequest/genre/loader.py` (the `_load_world` function around line 735–880 reads `world.yaml`, `lore.yaml`, `cartography.yaml`, `cultures.yaml`, `legends.yaml`, `history.yaml`, `npcs.yaml`, etc., but has no calendar read) and the `World` model in `sidequest/genre/models/world.py` (needs a `calendar: dict | None` field). Without this wiring, the authored YAML is dead content — the `get_world_grounding` tool's `ctx.world_calendar` will stay `None` and the tool will return `calendar_present=False` for the rest of the world's lifetime. Per the 24-6 commit message (`5cb8c0f` on oq-2): "production wiring at the session-handler call site is downstream work (24-7 / 24-8 territory)" — so loader + session-handler wiring belongs in story 24-7 (OTEL spans) as a precondition for the OTEL `calendar_present=True` assertion 24-7 will want to add. Recommend 24-7 author the loader read + `World.calendar` field + session-handler `ctx.world_calendar = world.calendar` line as one bundled change, since 24-7 will need all three wired before it can observe the proposed-vs-used calendar trace. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Once the schema is formalised in story 24-1, this YAML's free-form `time_precision.registers.<tier>` dict and `bells.<bell>` dict and `festivals[].narrator_hooks` list are good candidates for typed shapes. They were authored in the shape I'd want the schema to enforce — same convention demographics.yaml established. *Found by Dev during implementation.*

### Dev (rework round 2)
- **Improvement** (non-blocking): The `useful.bank_holidays_1908.statutory` / `customary_not_statutory` two-block structure introduced in this rework is a useful shape for the schema to capture when story 24-1 lands — distinguishing "what the law says" from "what the village actually does" matters for every dated narrator question. If the schema models it as a single `bank_holidays` list, it loses the legal-vs-customary distinction this rework was rejected for missing. Affects future schema design at `sidequest-server/sidequest/genre/models/world.py` (when 24-1 formalises the World-grounding shape). *Found by Dev during rework round 2.*

### Reviewer (code review)
- **Improvement** (non-blocking): Add a `tests/genre/test_glenross_grounding_yaml_parse.py` smoke test that calls `yaml.safe_load` on each grounding YAML in `genre_packs/tea_and_murder/worlds/glenross/` (demographics, history, lore, AND calendar). This was test-analyzer's suggestion (confidence: medium); it would make the parseability claim a CI gate rather than a one-time manual check. Affects `sidequest-server/tests/genre/` (new file). Naturally bundles with story 24-7's loader-wiring PR — same surface area, same review pass. *Found by Reviewer during code review.*
- **Gap** (non-blocking): The demographics.yaml `narrator_grounding_phrases` line at `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:625` ("Bells: quarter past and quarter to at the school") implies the school bell rings every quarter-hour all day, but the calendar's `time_precision.bells.school` rule scopes the quarter-hour ringing to the school day only. Tighten the demographics phrase to "Bells: quarter-hours during the school day at the school; Sundays, funerals, fires, and the New Year at the kirk." This is a sibling-file alignment, not a 24-4 fix, but Dev rework on this story is a natural moment to amend it if a one-line edit to demographics.yaml is acceptable. Affects `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:625`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Story 24-7 should bundle three pieces of wiring in one PR: (a) `loader.py:_load_world` add `calendar: Any = _load_yaml_raw_optional(world_path / "calendar.yaml")` and pass through to the `World` constructor; (b) add `calendar: dict | None = None` field on `sidequest/genre/models/world.py`; (c) at session bootstrap, stamp `ctx.world_calendar = world.calendar` so the existing `get_world_grounding` tool (24-6) can read it. Without all three, the YAML authored in this story is inert. The 24-6 commit message (`5cb8c0f`) already named this scope; this finding just makes the file-level shopping list explicit so 24-7 doesn't have to rediscover it. Affects `sidequest-server/sidequest/genre/loader.py:735-880` and `sidequest-server/sidequest/genre/models/world.py` and the session-bootstrap call site (TBD by 24-7). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Genre register correction — Highland Scotland, not English village**
  - Spec source: session SM Assessment (genre-truth notes paragraph)
  - Spec text: "Cosy gothic English-village mystery … late-Edwardian / interwar countryside … parish saint's day"
  - Implementation: Authored as cosy Highland Scots Edwardian 1908 (kirk and chapel, Scottish quarter days, Hogmanay-over-Christmas, the Glorious Twelfth, Wee Free presbytery, the Gaelic month-name substrate). Gothic register dropped to background — world.yaml axis_snapshot has gothic at 0.05, lore is "long warm afternoon of empire" cosy, not gothic.
  - Rationale: SM brief was authored from the genre-pack name (`tea_and_murder`) and BritBox conventions, but `world.yaml`, `demographics.yaml`, `lore.yaml`, and `npcs.yaml` all canonise Glenross as a Highland-Scotland-1908 parish (Castle Ross, the kirk, the Munro distillery, the railway halt to Inverness, the upper-glen Catholic minority). The session file's spec authority hierarchy puts story scope above SM assessment for register; the established world canon is the highest-authority spec source for in-world voice. Honoring the wrong country would have produced a calendar that contradicted the sibling YAMLs the same `get_world_grounding` tool will read alongside it.
  - Severity: minor (correction, not scope change)
  - Forward impact: none — the deliverable shape (months, days, moons, festivals, time precision) is identical; only the register changes. Downstream stories (24-7 wiring, 24-8 playtest validation) see no contract impact.

- **No `world.yaml` calendar pointer added; loader integration left to 24-7**
  - Spec source: session SM Assessment (Verification ask paragraph)
  - Spec text: "check whether glenross/world.yaml needs a calendar pointer or whether the loader globs the directory — confirm before assuming"
  - Implementation: Confirmed `sidequest-server/sidequest/genre/loader.py:_load_world` reads sibling YAMLs by **explicit path** per file (no glob, no pointer). The loader has no `calendar.yaml` read line yet. I did **not** add one in this story.
  - Rationale: Story title is "Author … calendar" — content authoring scope. Server-side loader code + `World` model field would be three new files of Python in a different repo, beyond the trivial workflow's content scope. The 24-6 commit message (`5cb8c0f`) explicitly punts session-handler wiring to 24-7/24-8 and the loader read is the upstream side of the same wiring chain. Logged as a non-blocking Delivery Findings Gap for 24-7 to absorb.
  - Severity: minor (cross-story coordination, not a defect)
  - Forward impact: minor — Story 24-7 must add the loader read, `World.calendar: dict | None` field, and the session-handler `ctx.world_calendar = world.calendar` line before its OTEL `calendar_present=True` assertion can pass. Without that, the YAML authored here is inert until 24-7 ships.

### Dev (rework round 2)
- **Bank Holidays — restructured from flat list into statutory + customary_not_statutory blocks**
  - Spec source: Reviewer Assessment severity table, HIGH finding #2 + Reviewer Devil's Advocate paragraph 3
  - Spec text: "Remove Christmas Day and Boxing Day from the statutory list (their social observance is already covered in festivals.christmas / festivals.boxing_day). Reframe Good Friday as a statutory holiday with a note that the kirk does not close. Either drop 2 January from the statutory list (it became statutory in 1974) or annotate it as 'customary day off, not statutory in 1908.'"
  - Implementation: Chose to *preserve* all eight items but split the list into two named blocks (`statutory:` and `customary_not_statutory:`). The reviewer's suggestion would also have worked, but the two-block shape lets the narrator answer "is the post office open on Boxing Day in 1908?" correctly (it is — the village treats it as a holiday but legally the office could open) AND lets the narrator hold both the "village pretends it's a holiday" and "legally it is not" facts at the same time. Each non-statutory entry now also notes the year it became statutory (1958 for Christmas, 1974 for Boxing Day and 2 January).
  - Rationale: Tea_and_murder's mechanics-first audience (Sebastien in CLAUDE.md) is the prototypical "is the post office open" question-asker. The two-block shape gives the narrator the historical-accuracy ammunition the reviewer flagged was missing. A flat list with annotations could mix the two and would re-introduce the same risk under terser rendering by the grounding tool.
  - Severity: minor (deviation from reviewer's literal suggestion; same intent, richer shape)
  - Forward impact: minor — when story 24-1 formalises the schema, it should preserve the two-block distinction. Logged as a Delivery Findings Improvement so 24-1 sees it.

- **starting_date — added explicit `date:` field on past + future festival references (beyond reviewer's literal ask)**
  - Spec source: Reviewer Assessment severity table, HIGH finding #3
  - Spec text: "Easiest fix: set nearest_festival_past.days_ago: 22 (harvest_home on 25 September, tail of window) and amend the prose from 'a fortnight gone' to 'three weeks gone.' OR widen typical_window to '10 September – 5 October' if a late harvest in 1908 is the intended in-world fact."
  - Implementation: Used `days_ago: 28` (not 22) — Reviewer's suggested 22 would land on Friday 25 September (not Saturday); harvest_home is defined as a Saturday festival. 28 lands on Saturday 19 September (inside the 10–25 window, verified). Prose: "four weeks gone" rather than "three weeks gone" (matches the corrected math). **Beyond the literal ask:** added explicit `date: "1908-09-19"` and `date: "1908-10-31"` fields so any future reader can audit the arithmetic from the YAML alone without recomputing from `days_ago`. Reviewer did not request this, but the file's own internal contradiction (which the reviewer caught) was *caused* by no human ever verifying the math from the date side — making the date explicit prevents the next person from repeating the same drift.
  - Rationale: Defense-in-depth on internal consistency. The two pieces of math (`days_ago` and `date:`) now must agree, and either alone can be audited.
  - Severity: minor (additive — extends reviewer's fix)
  - Forward impact: none — purely additional fields; no consumer requires them yet.

### Reviewer (audit)

- **Dev deviation #1 — "Genre register correction: Highland Scotland, not English village"** → ✓ ACCEPTED by Reviewer. The SM brief was off-genre (English/gothic), the established world canon is unambiguously Highland Scotland Edwardian 1908, and the deviation correctly honours the spec authority hierarchy (world canon over SM assessment for in-world voice). The decision saved the file from contradicting four sibling YAMLs. Pattern is sound; if another SM-brief register conflict surfaces in the future, dev should follow the same path.

- **Dev deviation #2 — "No `world.yaml` calendar pointer added; loader integration left to 24-7"** → ✓ ACCEPTED by Reviewer with note. The loader scoping decision is correct — adding loader+model+session-handler code in this story would have exceeded trivial-workflow content scope and would have duplicated work 24-7 will need to do anyway. The 24-6 commit message (`5cb8c0f` on oq-2) explicitly punts session-handler wiring to 24-7/24-8, and the loader read is the natural upstream side of that change. The Delivery Findings Gap entry is the right place to track this; 24-7 will pick it up. **Note:** the rule-checker correctly flagged this against "No Stubbing" — the rule technically matches but the explicit sequencing and graceful-null degradation in 24-6 mitigate it. Reviewer downgrades severity to non-blocking. If 24-7 is not actively scheduled within the next sprint, escalate.

- **Reviewer-found undocumented deviations (none):** Every textual error flagged in the Reviewer Assessment severity table is a content quality issue, not a spec deviation — Dev did not document them because the brief did not specify "ensure Nov 11 1908 is the correct weekday" or "verify no Catholic congregation contradicts demographics.yaml." These are correctly classified as bugs, not unlogged deviations.

## Sm Assessment

**Scope.** Author a single content file: `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/calendar.yaml`. This is pure content authoring per Epic 24's pattern — no Python code, no schema PRs. Story 24-4 ships content; downstream stories (24-6 narrator grounding tool, 24-7 OTEL, 24-8 playtest validation) consume it.

**Pattern reference (Monster Manual, ADR-059).** YAML in genre pack → Python generator/grounding tool consumes → narrator prompt zone injection → OTEL verifies. See `sprint/context/24-5-story-context.md` for the weather generator that already shipped — calendar lives in the same conceptual slot. Existing glenross world files at `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/` (lore.yaml, demographics.yaml, history.yaml, openings.yaml) show the in-world voice and naming register; calendar should match.

**Required surface (from story title).** months, days, moons, festivals, time precision. The narrator grounding tool (story 24-6, in-flight) will be the consumer — Dev should look at recent sidequest-server commits (`a9599cb` and around `feat/24-5-weather-generator`) and any in-progress `feat/24-6-*` branch to confirm field expectations. If 24-6's consumer shape is not yet stable, keep the YAML self-explanatory and let 24-6 adapt to it; do not block on cross-repo coupling.

**Genre-truth notes for glenross (tea_and_murder).** Cosy gothic English-village mystery; the calendar should feel late-Edwardian / interwar countryside — month names recognizable, festivals tied to village social life (harvest fête, May Day, parish saint's day, hunt season), moons named in folk-superstition register that lets the narrator hook gothic beats. Lean into Diamonds-and-Coal: each festival is a baited hook for a future murder-mystery scene.

**Branch / repo.** Single-repo story. Branch `feat/24-4-glenross-calendar` is live in `sidequest-content` (orchestrator stays on main). Trivial workflow — implement → review → finish, no separate RED phase.

**Verification ask.** YAML parses cleanly; values are in-world specific (no generic Jan/Feb defaults); file is wired into the world via the existing world-load path (check whether glenross/world.yaml needs a calendar pointer or whether the loader globs the directory — confirm before assuming).

**Handoff to:** Puck (dev).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/calendar.yaml` (new, 779 lines) — Highland-Scotland-1908 calendar reference. 12 Gregorian months with Gaelic substrate names and parish texture; 7 days of the week with Sabbath observance notes; 4 Scottish quarter days (Candlemas / Whitsunday / Lammas / Martinmas); 12 folk-named moons in Highland register; 22 festivals from Hogmanay to Boxing Day (with narrator hooks on the load-bearing ones — the Twelfth, the Parish Fete, Hallowe'en, Martinmas, Burns Night); five-tier `time_precision` block keyed to the parish's actual social strata (gentry watch / professional pocket-watch / village mantel-clock / croft sun-and-kettle / Sabbath service-anchored), with school bell + kirk bell + chapel bell + railway clock timing; a default `starting_date` (Saturday 17 October 1908, late afternoon — verified weekday correct against `datetime.date`).

**Tests:** N/A — trivial workflow, content-authoring story, no test phase. YAML verified parseable via `python3 -c "import yaml; yaml.safe_load(open(...))"`. Date sanity verified via `datetime.date(1908, 10, 17).strftime('%A') == 'Saturday'`. No new code paths.

**Branch:** `feat/24-4-glenross-calendar` in `sidequest-content` (commit `7f9cc98`), pushed to origin. Orchestrator stays on `main` (no orchestrator changes this story).

**Wiring status:** The YAML is authored but **not yet wired into the pack loader**. See Delivery Findings (Gap) and Design Deviations (no `world.yaml` pointer added) — loader integration is bundled into story 24-7 per the 24-6 commit message. Without 24-7 the file is inert; the `get_world_grounding` tool returns `calendar_present=False`. The Reviewer should confirm this disposition is correct and not require loader code in this story's PR.

**Handoff:** To Portia (reviewer) via the trivial workflow's review phase.

## Dev Assessment (round 2 — reviewer rework)

**Implementation Complete:** Yes — all six reviewer findings addressed.

**Files Changed:**
- `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/calendar.yaml` — 6 textual edits (3 HIGH, 2 MEDIUM, 1 LOW) per Portia's severity table. 75 lines changed (+48/-29). All edits are in-place rewordings; the file shape, length, and section structure are unchanged.
- `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml` — 1 line (line 625) tightened per Reviewer Gap (`narrator_grounding_phrases` school-bell phrasing aligned with calendar's school-day-scoped rule).

**Per-finding disposition (round 2):**

| # | Severity | Finding | Fix landed |
|---|----------|---------|------------|
| 1 | HIGH | Marymas/Catholic congregation contradicts demographics canon | Chose Reviewer's option (b) — Marymas reframed as Scottish Episcopal high-church observance at St Margaret's (the English-educated rector's high register; ties to demographics' established Episcopal congregation). "Upper-glen Catholics" reframed across all four references as "upper-glen old-faith families" — a Highland folk-survival of pre-Reformation midsummer custom (historically attested), not tied to any congregation. `register:` tags `catholic_minority` → `old_faith_folk` (St John's) + `episcopal_high_church` (Marymas). |
| 2 | HIGH | Bank Holidays 1908 list anachronisms | `useful.bank_holidays_1908` restructured into `statutory` + `customary_not_statutory` blocks. Statutory: New Year's Day, Good Friday (added with note that kirk does not close), first Monday in May, first Monday in August. Customary-not-statutory: 2 January (became statutory 1974), Christmas (1958), Boxing Day (1974), Easter Monday. Each non-statutory entry notes the year it became statutory so the narrator can answer period-accurate "is the post office open on Christmas" questions correctly. |
| 3 | HIGH | starting_date.nearest_festival_past math outside typical_window | Adopted Reviewer's "harvest_home at tail of window" path, refined: `days_ago: 28` → Saturday 19 September 1908 (inside the 10–25 September window, verified Saturday via `datetime.date`). Prose amended "a fortnight gone" → "four weeks gone". Added explicit `date: "1908-09-19"` and `date: "1908-10-31"` fields on past + future festival references so future readers can audit the arithmetic from the YAML alone. |
| 4 | MEDIUM | "(per ADR sensibility)" meta-text leak | Struck the parenthetical. November texture now reads "…the village by itself, which is when most mysteries happen. The Martinmas quarter day reorders the year's finances…" — the in-world meaning is preserved without the engineering vocabulary. |
| 5 | MEDIUM | Old Year's Day drift math | Reworded per Reviewer's suggested phrasing: "Old New Year — frozen at the 1752 adoption offset of eleven days; by strict reckoning the drift to 1908 would put it at 14 January, but the folk tradition does not update". The frozen-folk convention is now explicit. |
| 6 | LOW | "Tuesday's-evening trade" wrong weekday for 1908 | Replaced "Tuesday's-evening" with "midweek-evening" in both occurrences (`months[10].notable_days` Martinmas line and `festivals.martinmas.description`). Weekday-agnostic phrasing — durable across in-world years if the campaign clock ever rolls past 1908. |

**Verification:** Inline Python asserts run as part of the verification pass — all green:
- `yaml.safe_load` parses both files cleanly.
- `datetime.date(1908, 10, 17).strftime('%A') == 'Saturday'` (starting_date weekday correct).
- `start - timedelta(days=28) == 1908-09-19 (Saturday)` and `1908-09-19` is inside the harvest_home `typical_window` "10–25 September".
- `start + timedelta(days=14) == 1908-10-31` (halloween).
- String search: no "Tuesday" in Martinmas description; no "Catholic" anywhere in calendar.yaml; no "ADR" in November texture; bank_holidays_1908 restructured into statutory + customary_not_statutory.

**Tests:** N/A (trivial workflow content rework, same disposition as round 1).

**Branch:** `feat/24-4-glenross-calendar` in `sidequest-content` (commit `c854c7c` on top of `7f9cc98`), pushed to origin. Two commits on the branch now.

**Wiring status:** Unchanged from round 1 — loader integration remains deferred to story 24-7 per the 24-6 commit message. The Delivery Findings Gap entry on this still stands. No new wiring debt introduced by the rework.

**Handoff:** To Portia (reviewer) for re-review.

## Subagent Results (round 2 — focused re-review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes (re-run inline by Reviewer; YAML parses, math verified) | clean | none | N/A — re-confirmed parse + Dev's inline assertions reproduced by Reviewer |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Yes (round 1 finding stable; no test code changed) | findings | 1 (carried) | Carried forward — "no tests" disposition unchanged from round 1; test smoke obligation still transfers to 24-7; no new test debt introduced |
| 5 | reviewer-comment-analyzer | Yes (Reviewer spot-checked all 5 round-1 findings against the rework diff; round-2 diff small enough for direct verification) | findings | 5 carried, all resolved | 4 confirmed-fixed (Marymas/Catholic, bank-holidays, starting_date math, Old Year drift) + 1 dismissed-now-stable (school bell sibling tweak — landed in demographics.yaml as part of bundled fix). Plus my own 2 round-1 findings (ADR meta-leak, Tuesday weekday) both confirmed-fixed via direct diff inspection. |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Yes (round 1 rule mapping stable) | findings | 1 (carried) | Carried forward — "No Stubbing" rule match unchanged; mitigation (24-7 sequencing + 24-6 graceful-null) unchanged; non-blocking. Genre Truth / Crunch-in-Genre / Diamonds-and-Coal / Yes-And re-verified compliant on the round-2 Marymas reframing (Episcopal high-church register matches the cosy/0.75 axis and ties to demographics' English-educated rector). |

**All received:** Yes (re-review pass — 1 subagent re-run by Reviewer inline, 3 carried forward as stable from round 1, 5 pre-filled as skipped/disabled per settings)
**Total findings:** 8 carried + 0 new = all 8 round-1 findings resolved (6 fixed in code, 2 retained as Delivery Findings for downstream stories); 0 new findings in round 2

### Round-2 fix verification (per-finding, verified against actual file state)

Direct verification by Reviewer (not via subagent — round-2 diff is small enough for direct inspection):

| # | Round-1 finding | Round-2 fix | Verification |
|---|-----------------|-------------|--------------|
| 1 | HIGH — Marymas / "upper-glen Catholics" contradicts world canon | "upper-glen Catholics" → "upper-glen old-faith families" (4 sites); Marymas reframed as Scottish Episcopal high-church at St Margaret's (the English-educated rector's higher register, demographics line 209 confirms the laird's family worships at St Margaret's); register tags catholic_minority → old_faith_folk + episcopal_high_church | VERIFIED — `"Catholic" in calendar.yaml` returns False; `marymas.register == "episcopal_high_church"`; `midsummer_st_johns.register == "old_faith_folk"`. The Anglo-Catholic Episcopal register reframe is world-coherent (Scottish Episcopal Church does observe Marian feasts) and ties to demographics' established Episcopal congregation. **Confirmed.** |
| 2 | HIGH — Bank Holidays 1908 anachronisms | Restructured into `statutory:` (4 entries: New Year's Day, Good Friday, first Monday in May, first Monday in August) + `customary_not_statutory:` (4 entries: 2 January, Christmas, Boxing Day, Easter Monday). Each non-statutory entry notes the year it became statutory. Good Friday added as statutory with note that kirk does not close. | VERIFIED — statutory list has 4 items, customary list has 4 items, "Christmas" not in statutory, Christmas/Boxing Day/2 January correctly annotated with their post-1908 statutory adoption years. The two-block shape exceeds the literal reviewer ask (was: "remove Christmas + Boxing Day"); Dev's deviation log explains the choice (preserves the village's social observance while making the legal status auditable for mechanics-first players). Stronger fix than asked for. **Confirmed.** |
| 3 | HIGH — starting_date.nearest_festival_past math outside typical_window | days_ago: 14 → 28 (Saturday 19 September 1908, inside the 10–25 September window); prose "a fortnight gone" → "four weeks gone"; added explicit `date: "1908-09-19"` and `date: "1908-10-31"` fields | VERIFIED — `start_date - 28 days == 1908-09-19 (Saturday)`; `1908-09-19` is inside `typical_window` "10–25 September"; YAML `date:` field agrees with `days_ago:` arithmetic. Dev correctly deviated from reviewer's literal suggestion (days_ago: 22) because 22 would land on Friday — harvest_home is defined as a Saturday festival. Deviation logged and rationale sound. **Confirmed.** |
| 4 | MEDIUM — "(per ADR sensibility)" meta-text leak | Parenthetical struck from November texture | VERIFIED — `"ADR" in november.texture` returns False. In-world meaning preserved. **Confirmed.** |
| 5 | MEDIUM — Old Year's Day drift math | Reworded to acknowledge frozen-at-1752 convention + drift-to-1908 (eleven-day vs thirteen-day offset) | VERIFIED — system.notes line mentions both "frozen" and "1752" and explicitly names the drift to "14 January" as the strict reckoning. The 40-year-history reader will now read this correctly. **Confirmed.** |
| 6 | LOW — "Tuesday's-evening trade" wrong weekday for 1908 | "Tuesday's-evening" → "midweek-evening" in both occurrences (months[10].notable_days line and festivals.martinmas.description) | VERIFIED — "Tuesday" not present in either site. Weekday-agnostic phrasing — durable across in-world years. **Confirmed.** |
| Bundle | (Reviewer's own Gap) demographics.yaml school-bell phrase | "quarter past and quarter to" → "quarter-hours during the school day" (line 625) | VERIFIED — direct diff inspection on demographics.yaml shows the one-line change landed and parses; aligns with calendar's school-bell rule. **Confirmed.** |

### Round-2 regression sweep

Spot-checked the round-2 rework for new content errors introduced by the fixes:

- **Marymas / St John's Eve reframing introduces "Castle Ross attends, in summer best" and "St Margaret's rings a quiet Angelus for the Episcopal side"** — both are mild extensions of canon. Castle Ross's attendance at St Margaret's is established in demographics.yaml line 209 ("The laird's family worships here"); the Angelus is liturgically standard for Anglo-Catholic/high Episcopal observance and the English-educated rector's character is the canonical justification. Neither contradicts any sibling file. **No regression.**
- **"Old-faith families walking down for the [Marymas] service"** — could be read as religiously incoherent (old-faith pre-Reformation households attending an Episcopal service), but in Highland 1908 the Scottish Episcopal Church was historically the closest legal liturgical home for households with Catholic-leaning piety after the 1592 establishment of Presbyterianism; Anglo-Catholic Episcopal services were a recognised refuge. Plausible without contradiction. **No regression.**
- **Bank Holidays "the legal holiday and the kirk's holy-day-keeping diverge here, as they do throughout the Scottish calendar"** — strong claim, but consistent with `festivals.easter.description` ("Scots Presbyterianism has been historically wary of holy-day keeping") and with the Knox/Westminster tradition the kirk descends from. **No regression.**
- **starting_date duplicate-source-of-truth concern (`date:` AND `days_ago:`)** — defensible defense-in-depth, but if either drifts it must drift with the other. Dev acknowledged this in the deviation log; the assertion test covers it. **Acceptable.**
- **No new files added; no deleted content beyond the six targeted fixes.** Diff is narrow and surgical. **Clean.**

### Rule Compliance (round 2 — delta from round 1)

| # | Rule | Round-1 verdict | Round-2 delta |
|---|------|-----------------|---------------|
| 1 | No Silent Fallbacks | COMPLIANT | Unchanged (consumer logic untouched) |
| 2 | No Stubbing | RULE MATCH with mitigation | Unchanged — still tracked in Delivery Findings; mitigation still valid |
| 3 | Verify Wiring | COMPLIANT in scope | Unchanged |
| 4 | Every Test Suite Needs a Wiring Test | N/A | Unchanged |
| 5 | OTEL Observability | COMPLIANT | Unchanged |
| 6 | Genre Truth — register matches axis_snapshot | COMPLIANT | Re-verified on round-2 Marymas reframing — Episcopal high-church register (English-educated rector, sung office, Lady chapel candles) sits cleanly inside the cosy/0.75 axis. The old-faith folk register (pre-Reformation midsummer fire) matches the gothic/0.05 axis: present-but-suppressed, a low-confidence hook the kirk officially does not see. Register calibration improved by the rework — was previously contradicting demographics, now coherent. |
| 7 | Crunch in the Genre, Flavor in the World | COMPLIANT | Improved — round 2 ties Marymas / St John's Eve / Old New Year folk traditions explicitly to the Highland-Scotland-1908 world canon (St Margaret's Episcopal, the English-educated rector, the upper-glen old-faith families, the 1752 calendar reform) rather than importing a generic Catholic minority that did not exist in canon. |
| 8 | Diamonds and Coal | COMPLIANT | Unchanged |
| 9 | Yes, And | COMPLIANT | Unchanged |
| 10 | No Jira / No 1898 org | COMPLIANT | Unchanged (no Jira refs in rework commit) |
| 11 | Durable retention | N/A | Unchanged |
| 12 | Historical/cultural accuracy | VIOLATIONS (3 HIGH) | RESOLVED — all three HIGH violations fixed and verified; both MEDIUMs fixed and verified; LOW fixed and verified. No new historical claims that warrant further verification. |

### Devil's Advocate (round 2)

The rework is clean. The hardest reach in round 2 is the Marymas reframe — Dev took "the Scottish Episcopal Church does observe Marian feasts" and ran with it harder than the reviewer's note suggested, adding a sung office, Lady-chapel candles, and the laird's family in attendance. Is this overclaiming?

Scottish Episcopal in 1908 was not uniformly Anglo-Catholic — there was a "high"/"low" split, and many congregations were closer to mainstream Anglican. But the calendar's text grounds the Anglo-Catholic register specifically in **the rector's character** ("the rector is English-educated and inclined to the higher register"). Demographics.yaml line 209 already canonised the rector as "English-educated"; this is the same English-Anglo-Catholic seam Scott's "Heart of Midlothian" set up for Edwardian fiction. The reframe is conservative given the established character. The laird's-family-attends line is directly supported by demographics' "The laird's family worships here." No overclaim.

The St John's Eve hilltop fire being "a folk survival of pre-Reformation midsummer that the Highland kirk has neither suppressed nor blessed" is historically attested — hilltop midsummer fires persisted in Highland folk practice well into the 20th century, often without congregational sponsorship. Sound.

The bank-holidays restructure is the kind of upgrade I'd hope for: not a literal patch of the four bullet points I flagged, but a re-architecting of the whole section to separate legal-status from social-practice. That's the right shape for a content reference the narrator will be asked to summarise back to a mechanics-first player. The deviation is logged as an Improvement for the 24-1 schema story. Good.

The duplicate source-of-truth on `starting_date.date:` + `days_ago:` is the only thing that bothers me, and only mildly. If 24-7's loader generates a typed `StartingDate` model, it should derive `date` from `year/month/day` and re-derive `days_ago` from the festival reference — at which point the YAML-side `date:` field becomes redundant. But that's a 24-7 problem to solve when the schema lands. For now, defense-in-depth makes sense.

I cannot find a remaining issue to reject on.

### Deviation Audit (round 2 — Dev's two new deviation entries)

- **Dev round-2 deviation #1 — "Bank Holidays restructured into statutory + customary_not_statutory blocks (vs reviewer's literal 'remove Christmas + Boxing Day' suggestion)"** → ✓ ACCEPTED by Reviewer. The reviewer's literal suggestion was "remove Christmas Day and Boxing Day from the statutory list (their social observance is already covered in festivals.christmas / festivals.boxing_day)." Dev's two-block restructure preserves the village's social observance of those days at the calendar level (so the narrator doesn't have to cross-reference back to festivals[] to answer "is the village quiet on Christmas?") AND makes the legal status explicit per item with the year-of-statutory-adoption. This is a structural improvement that better serves the mechanics-first audience (Sebastien — CLAUDE.md "Who This Is For"). The forward-impact note for story 24-1 schema design is correctly logged.
- **Dev round-2 deviation #2 — "starting_date added explicit `date:` field on past + future festival references (beyond reviewer's literal ask)"** → ✓ ACCEPTED by Reviewer with mild caution. Defense-in-depth on internal consistency is sound — the original review-rejection driver was that the math was internally contradictory and no human had checked it. Making the date explicit alongside `days_ago:` lets future readers audit from either side. Mild caution: if these two fields ever drift again, the next reviewer must catch it; Dev's inline assertion test is the safety net and should migrate into the CI smoke test recommended for story 24-7. Logged finding handles that.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `calendar.yaml` (round-2 content-corrected) → (loader integration still deferred to 24-7) → `World.calendar` (proposed) → session-handler → `ToolContext.world_calendar` (also deferred) → `get_world_grounding` tool (24-6, in oq-2/sidequest-server) → narrator prompt. End-to-end remains intentionally incomplete pending 24-7; that disposition was accepted in round 1 and is unchanged. The content side is now correct.

**Pattern observed:** Round-2 rework follows the same demographics.yaml / lore.yaml / history.yaml precedent — versioned `0.1.0`, header docstring with consumer-story pointer, world+genre_pack identity, free-shape body. Round-2 deltas are all in-place rewordings of existing fields plus one structural upgrade (bank-holidays two-block) plus two new `date:` fields. No new sections, no removed sections, no shape changes at the consumer's seam. Surgical.

**Error handling:** N/A — pure data. Consumer logic (`get_world_grounding` in oq-2) unchanged; `calendar_present=False` graceful-null still in effect until 24-7 wires the loader read.

**Subagent finding dispatch (round 2):**

- `[DOC]` reviewer-comment-analyzer — All five round-1 documentation/content findings resolved: (a) Marymas/Catholic-congregation contradiction with demographics.yaml — fixed by reframing as Scottish Episcopal high-church at St Margaret's; (b) Bank Holidays 1908 historical anachronisms (Christmas/Boxing Day/2 January wrongly listed as 1908 statutory) — fixed by restructuring into statutory + customary_not_statutory blocks with per-item year-of-statutory-adoption annotations; (c) Old Year's Day Julian-Gregorian drift math — fixed by explicit frozen-at-1752 acknowledgment; (d) starting_date math contradicting harvest_home.typical_window — fixed via days_ago: 28 → Saturday 1908-09-19, inside window; (e) demographics.yaml sibling bell-phrase tightening — landed in bundled rework. Plus Reviewer's own [DOC] finds (ADR meta-text leak, Tuesday weekday) — both fixed and verified.
- `[RULE]` reviewer-rule-checker — Round-1 "No Stubbing" rule match (unread YAML in oq-1 loader) unchanged in round 2; mitigation (24-7 sequencing + 24-6 graceful-null degradation) unchanged. Non-blocking, tracked in Delivery Findings. Genre Truth / Crunch-in-Genre / Diamonds-and-Coal / Yes-And rules re-verified compliant on the Marymas reframe — Episcopal high-church register now sits inside the cosy/0.75 axis cleanly and ties to demographics' canon, where round-1 had imported a Roman Catholic minority that did not exist in canon (now an outright Genre Truth + Crunch-in-Genre improvement over round 1).
- `[TEST]` reviewer-test-analyzer — "No tests in this story" disposition unchanged from round 1 (precedent: demographics.yaml, lore.yaml, history.yaml shipped without dedicated tests). Test smoke obligation transferred to story 24-7 with the loader wiring; logged as a Delivery Findings Improvement so 24-7 sees it. Dev's inline assertions (round 1 + round 2) acted as the ad-hoc smoke check; making that a CI gate is on 24-7's plate.

**Round-2 round-trip:** Two commits on `feat/24-4-glenross-calendar` (`7f9cc98` initial + `c854c7c` rework). All six reviewer findings from round 1 verified resolved against the file's actual state. Dev's inline assertions reproduced and confirmed by Reviewer. No regressions introduced by the rework. Two new Dev deviations logged (both Reviewer-ACCEPTED). Three new Delivery Findings carried forward to story 24-7 (loader wiring + test smoke + schema-block-preservation note for 24-1).

**Handoff:** To Prospero (SM) for the finish phase. Two commits ready to land via PR against `develop` in sidequest-content.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — YAML parses, UTF-8, not LFS-tracked, no lint configs in content repo, date sanity (17 Oct 1908 = Saturday) confirmed |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Yes | findings | 1 | 1 deferred — "no tests" disposition is defensible (precedent: demographics.yaml, lore.yaml, history.yaml all shipped without dedicated tests in same world); test obligation transfers to story 24-7 when loader wiring lands. Recommendation logged as Delivery Finding for 24-7. |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 | 4 confirmed (3 high + 1 medium), 1 dismissed (low — minor demographics phrasing tweak, not blocking) — see severity table |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Yes | findings | 1 | 1 confirmed — "No Stubbing" rule match (unread YAML) with explicit sequencing mitigation (24-7 wiring + 24-6 graceful-null handling). Severity downgraded to non-blocking with documented 24-7 plan; will be tracked in Delivery Findings, not in severity table. |

**All received:** Yes (4 returned with assessment, 5 pre-filled as skipped/disabled per settings)
**Total findings:** 8 confirmed (5 in severity table below + 3 deferred to Delivery Findings / 24-7), 1 dismissed, 0 deferred-as-blocking

### Reviewer's own findings (in addition to subagent fleet)

I conducted my own date arithmetic against `datetime.date(1908, ...)` and found:
- **Nov 11, 1908 was Wednesday**, not Tuesday. The Martinmas description in `months[10].notable_days` (line 231) and `festivals.martinmas.description` (line 614) both say "the inn doing its best Tuesday's-evening trade." The calendar pins itself to year 1908 (`system.current_year: 1908`, `starting_date.year: 1908`), so this is factually wrong for the in-world year. — [LOW] (added below as [REVIEWER])
- **"(per ADR sensibility)"** meta-comment in `months[10].texture` (November, line 225): "The village is the village by itself, which is when (per ADR sensibility) most mysteries happen." This is a fourth-wall break — the prose is narrator-visible content, and "ADR" is engineering vocabulary that has no in-world referent. — [MEDIUM] (added below as [REVIEWER])

### Rule Compliance

Read against CLAUDE.md (orchestrator + content + server), SOUL.md, and `.pennyfarthing/gates/lang-review/` (no YAML-specific checklist exists; rules drawn from CLAUDE.md / SOUL.md only).

| # | Rule (source) | Applies? | Verdict |
|---|---------------|----------|---------|
| 1 | No Silent Fallbacks (CLAUDE.md) | Yes — applies to consumer (get_world_grounding) | COMPLIANT — explicit `calendar_present=False` OTEL stamp + null payload; no silent default |
| 2 | No Stubbing (CLAUDE.md) | Yes — applies to YAML | RULE MATCH with mitigation — file is fully authored content, not a skeleton, but is unread by oq-1 loader. Explicit sequencing intent in header comment + 24-7 plan + 24-6 graceful-null degradation. Downgraded to non-blocking; tracked in Delivery Findings. |
| 3 | Verify Wiring, Not Just Existence (CLAUDE.md) | Yes | COMPLIANT in scoped sense — the consumer is wired end-to-end (tool registered, ToolContext field present, OTEL emitted); only the bootstrap load path is deferred to 24-7. Wiring rule applies to 24-7's PR, not this one. |
| 4 | Every Test Suite Needs a Wiring Test (CLAUDE.md) | N/A | No test suite introduced; rule applies to 24-7. |
| 5 | OTEL Observability Principle (CLAUDE.md) | Yes — applies to consumer | COMPLIANT — `tool.grounding.calendar_present` already emitted unconditionally. No new OTEL gap from this story. |
| 6 | Genre Truth (SOUL.md) — register matches axis_snapshot | Yes — applies to 89 authored items | COMPLIANT — cosy/0.75 and gothic/0.05 register correctly carried across all months, days, festivals, moons, time-precision tiers. Gothic is present-but-suppressed (Mourning Moon, the "minister officially absent" Hallowe'en). No tonal escalation. |
| 7 | Crunch in the Genre, Flavor in the World (SOUL.md) | Yes | COMPLIANT — all cultural identity (Castle Ross, Munro distillery, Gaelic month names, upper-glen barn, Free Presbyterian Wee Free) scoped to worlds/glenross. None bleeds into pack-level files. |
| 8 | Diamonds and Coal (SOUL.md) — detail signals importance | Yes | COMPLIANT — longest descriptions + richest narrator_hooks land on Martinmas (financial spine) and Glorious Twelfth (gentry peak); minor observances get a one-liner. |
| 9 | Yes, And (SOUL.md) — world grows from play | Yes — applies to narrator_hooks | COMPLIANT — all 18 hooks phrased as open framings ("a stranger first-foots a house with bad luck written on him"), not fixed plot beats. `starting_date` flagged as overridable. |
| 10 | No Jira / No 1898 org (CLAUDE.md) | Yes | COMPLIANT — no Jira references in commit or session. |
| 11 | Durable retention by default (project memory) | N/A | No lifecycle policy introduced. |
| 12 | Historical/cultural accuracy (implicit Genre Truth — the audience is a 40-year RPG veteran per CLAUDE.md "Who This Is For") | Yes — every dated claim, every register, every cultural assignment | VIOLATIONS — see severity table. Three high-severity factual errors that contradict either established world canon (demographics.yaml has no Catholic congregation but calendar imports "upper-glen Catholics") or basic 1908 historiography (Christmas/Boxing Day were not statutory bank holidays until 1974) or internal arithmetic (harvest_home math contradicts its own typical_window). |

### Devil's Advocate

This calendar is going to mislead the narrator the first time Sebastien asks "what's the date today?" — and the answer is going to be "Saturday the seventeenth of October, nineteen-and-eight; the harvest home a fortnight gone." Sebastien is the mechanics-first player, the one who reads the YAML in the GM panel; he will compute that "a fortnight gone" puts harvest home on 3 October, which is outside the calendar's own stated typical window of 10-25 September. The narrator will then have to either improvise an explanation or look incoherent. That is exactly the "Claude winging it" failure mode the OTEL principle exists to prevent — and OTEL won't help here, because the YAML *itself* is internally contradictory, so the spans will all read green while the prose is wrong.

Worse, Marymas. The calendar tells the narrator there are "upper-glen Catholics" who keep a Catholic feast at St Margaret's chapel. Demographics.yaml — the file the narrator also reads through the same grounding tool — says glenross has Church of Scotland, Scottish Episcopal, and Wee Free congregations and nothing else. St Margaret's is Episcopal by the `lore.yaml` and `demographics.yaml` register; the calendar is staging a Catholic procession through an Episcopal building for a congregation that doesn't exist. The first time a player asks "where do the Catholics meet?" or "who's the priest?" the world will fracture. This is *exactly* the cross-file contradiction the SOUL.md "Crunch in the Genre, Flavor in the World" rule is structured to prevent — world canon must be internally coherent, because the narrator surfaces all of it at once.

The Bank Holidays list is more diffuse — the narrator may never call it up — but if a player asks "does the post office open on Christmas?" the calendar will say "Christmas is a bank holiday in 1908" which is historically false (Christmas was not a Scottish bank holiday until 1974), and the surrounding prose ("the village is saving itself for Hogmanay") is then *contradicted by the calendar's own bank-holidays list*. A character who refused to work on Christmas in 1908 Scotland would have been considered eccentric; the calendar implies the opposite.

The "Tuesday's-evening trade" line is small but corrosive: Keith will run a Martinmas scene in this exact world and the narrator will say "the inn was busy as it always is for Martinmas Tuesday-evening" on what is actually a Wednesday in 1908. He will notice. He will then trust the calendar less.

The "(per ADR sensibility)" leak is the kind of fourth-wall break that announces "this YAML was written by an AI for the engineering team." It needs to come out before any narrator sees it.

Devil's Advocate verdict: this calendar is **brilliantly written prose carrying multiple factual landmines that will detonate the first time the narrator surfaces them.** The fixes are small (six text edits) but they MUST land before merge.

### Deviation Audit

(See updates in the Design Deviations section below — both Dev entries audited and stamped.)

## Reviewer Assessment

**Verdict:** REJECTED

**Data flow traced:** `calendar.yaml` → (loader integration deferred to 24-7) → `World.calendar` (proposed) → session-handler → `ToolContext.world_calendar` (also deferred) → `get_world_grounding` tool (24-6, already in oq-2/sidequest-server) → narrator prompt. End-to-end is intentionally incomplete; that part is correctly scoped to 24-7 and acceptable.

**Pattern observed:** Content-grounding YAML follows the demographics.yaml / lore.yaml / history.yaml precedent — versioned at `0.1.0`, header comment explaining the schema-pending status and consumer story, world+genre_pack identity fields, free-shape body. The pattern is consistent and appropriate. Where this file fails is in **factual accuracy and internal consistency**, not in shape.

**Error handling:** N/A — pure data. The consumer side (get_world_grounding in oq-2) handles `world_calendar=None` with explicit `calendar_present=False` OTEL stamp + null payload. Correctly designed by 24-6 and not this story's concern.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [DOC] | Marymas / "upper-glen Catholics" contradicts established world canon — demographics.yaml has only Church of Scotland, Scottish Episcopal, and Wee Free; no Roman Catholic congregation exists. St Margaret's is Scottish Episcopal per `lore.yaml` and `demographics.yaml`. Calendar stages a Catholic procession through an Episcopal building for a congregation that does not exist. | `calendar.yaml:152, 183, 491-499, 529-534` | Choose one: (a) rename "Catholics" to "the old-faith families in the upper glen" with their own informal meeting-place (NOT St Margaret's); (b) reframe Marymas as a Scottish Episcopal high-church observance at St Margaret's and remove the word "Catholic"; OR (c) drop Marymas / St John's hilltop fire entirely. Whichever path, the result must match demographics.yaml's stated three traditions. |
| [HIGH] [DOC] | Bank Holidays 1908 list contains historical anachronisms — Christmas Day and Boxing Day were NOT statutory bank holidays in Scotland in 1908 (they became Scottish bank holidays in 1974). Good Friday IS a 1871-Act Scottish bank holiday but the calendar implies it is not ("kirk does not close"). | `calendar.yaml:771-779` | Remove Christmas Day and Boxing Day from the statutory list (their social observance is already covered in `festivals.christmas` / `festivals.boxing_day`). Reframe Good Friday as a statutory holiday with a note that the kirk does not close (legal and religious can diverge). Either drop 2 January from the statutory list (it became statutory in 1974) or annotate it as "customary day off, not statutory in 1908." |
| [HIGH] [DOC] | `starting_date.nearest_festival_past` math is internally inconsistent — 17 October minus 14 days = 3 October, which is outside `festivals.harvest_home.typical_window` ("10–25 September"). The starting_date's prose "the harvest home a fortnight gone" cannot be true if harvest_home obeys its own declared window. | `calendar.yaml:558-560, 751, 753-755` | Easiest fix: set `nearest_festival_past.days_ago: 22` (harvest_home on 25 September, tail of window) and amend the prose from "a fortnight gone" to "three weeks gone." OR widen `typical_window` to "10 September – 5 October" if a late harvest in 1908 is the intended in-world fact. |
| [MEDIUM] [REVIEWER] | Fourth-wall meta-text leak in narrator-visible prose — November's `texture` field reads "(per ADR sensibility)". ADR is engineering vocabulary; the narrator may quote this prose verbatim. | `calendar.yaml:225` | Strike the parenthetical entirely, OR rewrite as a flavour-only line: "The village is the village by itself, which is when most mysteries happen." (The point survives; the meta-comment goes.) |
| [MEDIUM] [DOC] | Old Year's Day drift math — 12 January is presented as the derived pre-1752 Julian Hogmanay, but by 1908 the strict Julian-Gregorian offset has grown to 13 days, putting Old New Year at 14 January. The 12 January date is a frozen folk convention from 1752, not a live calculation. | `calendar.yaml:52` | Reword to: "…12 January (the Old New Year — frozen at the 1752 adoption offset of eleven days; by strict reckoning it would be 14 January, but the folk tradition does not update)." The 40-year-veteran audience will notice the unflagged drift. |
| [LOW] [REVIEWER] | "Tuesday's-evening trade" for Martinmas — 11 November 1908 was Wednesday, not Tuesday. Calendar pins itself to year 1908. | `calendar.yaml:231, 614` | Replace "Tuesday's-evening" with "weekday-evening" or "midweek" (weekday-agnostic phrasing), OR replace with the correct 1908 weekday ("Wednesday's-evening"). The first option is the more durable fix. |

**Handoff:** Back to Puck (dev) for content rework. All six issues are textual edits — no schema changes, no test changes, no loader changes. Estimate: under 30 minutes of focused YAML editing. Re-review can be quick once the file comes back.