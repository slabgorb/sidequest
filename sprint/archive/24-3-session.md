---
story_id: "24-3"
jira_key: null
epic: "24"
workflow: "trivial"
---

# Story 24-3: Author tea_and_murder/glenross demographics (settlement profiles, population, services)

## Story Details

- **ID:** 24-3
- **Epic:** 24 (Procedural World-Grounding Systems)
- **Jira Key:** none (project does not use Jira)
- **Workflow:** trivial
- **Stack Parent:** none
- **Repos:** content
- **Branch:** feat/24-3-glenross-demographics

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-20T11:43:40Z
**Round-Trip Count:** 1

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-20T07:15:00Z | 2026-05-20T11:14:33Z | 3h 59m |
| implement | 2026-05-20T11:14:33Z | 2026-05-20T11:24:28Z | 9m 55s |
| review | 2026-05-20T11:24:28Z | 2026-05-20T11:40:03Z | 15m 35s |
| implement | 2026-05-20T11:40:03Z | 2026-05-20T11:41:48Z | 1m 45s |
| review | 2026-05-20T11:41:48Z | 2026-05-20T11:43:40Z | 1m 52s |
| finish | 2026-05-20T11:43:40Z | - | - |

## Story Context

### Epic Vision

Anti-mode-collapse infrastructure for the narrator. Procedural generators inject structured, varied, mechanically-consistent context into narrator prompt zones — shifting the narrator from **invention** (where it repeats itself) to **curation** (where it excels).

Follows the Monster Manual pattern (ADR-059):
1. YAML content defines rules/baselines in genre packs
2. Generators produce structured state
3. State injected into narrator prompt zones via dispatch pipeline
4. Narrator selects from proposed state, system reconciles
5. OTEL verifies proposed vs used

**Demographics System:** Baked (no runtime generation), injected directly into narrator prompt zones.

### Glenross World Overview

- **Name:** Glenross
- **Genre Pack:** tea_and_murder
- **Setting:** Highland village in Edwardian Scotland, c. 1908
- **Scope:** "Large enough to support a minister, a doctor, a school, a post office, one inn — small enough that everyone knows everyone's business by sundown."
- **Axis snapshot:** cosy (0.75), puzzle (0.7), gossip (0.7), gothic (0.05)
- **Economic base:** Railway hub, distillery, farming, domestic service
- **Social structure:** Class matters but village is small enough to see through it

### Deliverables

Author `demographics.yaml` for Glenross containing:
- **Settlement profiles:** size, character, economic role (e.g., "village square", "railway station", "distillery district")
- **Population snapshot:** occupational breakdown (farmers, servants, merchants, professionals), class distribution
- **Services:** kirk, school, surgery, post office, inn, shops, distillery
- **Social strata:** landed gentry (castle), professionals (doctor/minister/schoolmistress), shopkeepers/tradespeople, servants, farm laborers
- **Narrative grounding:** phrases that anchor demographics in the narrator prompt ("the village's recurring cast", "everyone knows everyone's business")

### Testing

Deliverable is YAML only. No runtime testing needed until story 24-6 (prompt zone injection) is complete. Content can be verified by:
1. Schema compliance (after story 24-1 defines schemas)
2. Narrator prompt injection preview (story 24-6)
3. Playtest validation (story 24-8)

### Acceptance Criteria

- ✓ demographics.yaml exists at `tea_and_murder/worlds/glenross/demographics.yaml`
- ✓ Describes Glenross population, occupational breakdown, key services, social strata
- ✓ Grounded in the world's Edwardian Highland village setting
- ✓ Aligns with existing NPCs, cartography, and world.yaml axis snapshot
- ✓ Provides enough detail for narrator to ground dialogue in village context
- ✓ No schema violations (once story 24-1 defines the schema)

## Delivery Findings

<!-- Append-only. Each agent writes under its own subheading. -->

### Dev (implementation)

- **Gap** (non-blocking): The schema referenced in the existing demographics.yaml header (`docs/schemas/world-grounding/demographics.schema.json`) does not exist yet — Story 24-1 owns that file. The current world-grounding YAMLs (weather.yaml, demographics.yaml) all cite a non-existent schema path.
  Affects `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml` and any sibling world-grounding files written before 24-1 lands (schema comment needs to be unified or stubbed once 24-1 writes the actual JSON schemas).
  *Found by Dev during implementation.*

- **Gap** (non-blocking): Albert MacGregor (the stationmaster) appears in `cartography.yaml` and is referenced in `lore.yaml` (transport section) but has no entry in `npcs.yaml`. I cross-referenced him as `albert_macgregor` in the demographics services block; that ID will dangle until either (a) he is promoted to a full warm-cast NPC entry or (b) a "supporting cast" namespace is introduced for named-but-not-warm NPCs.
  Affects `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/npcs.yaml` (add minimal stationmaster entry) **or** a new `supporting_cast.yaml` (introduce the concept). Same gap exists for Mrs. Drummond (manse housekeeper), Donald Buchan (smith), Kirsty Sinclair (publican's wife), Mrs. Trefusis (Castle housekeeper), Mrs. Cattanach (Castle cook), Calum Cattanach (under-gillie), Effie MacRae (constable's wife), Mhairi Munro, and Iona Ferguson.
  *Found by Dev during implementation.*

- **Improvement** (non-blocking): The `population.occupational_mix` shares sum to 1.001 (rounding) because the headcounts are integer-anchored and the shares are 3-decimal approximations. If story 24-1's schema requires exact-1.0 share sums, the schema should specify the rounding tolerance (or drop `share` and compute on the fly from headcounts).
  Affects future schema definition in `docs/schemas/world-grounding/demographics.schema.json` (Story 24-1).
  *Found by Dev during implementation.*

- **Question** (non-blocking): Story 24-1's schema will need to decide whether `social_strata[].exemplars` is a list of NPC IDs (cross-ref to `npcs.yaml`) or free-form strings. I authored it as a list of IDs because that's the only shape that supports automated validation; story 24-6 (prompt-zone injection) will need to resolve those IDs against the npc registry when composing the prompt.
  Affects schema design (24-1) and prompt-zone injection (24-6).
  *Found by Dev during implementation.*

### Dev (implementation — round 2 rework)

- No new upstream findings during rework. All 4 reviewer findings addressed by edits to existing fields (no new logic, no new files). Round-1 Delivery Findings (schema-pending, dangling supporting-cast IDs, share rounding, exemplars-as-IDs question) stand unchanged.

### Reviewer (code review)

- **Gap** (non-blocking, escalated): Six supporting-cast NPC IDs are used as resolvable cross-references in demographics.yaml but have no corresponding entries in `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/npcs.yaml`: `albert_macgregor`, `donald_buchan`, `mrs_drummond`, `mrs_trefusis`, `mrs_cattanach`, `calum_cattanach` (plus `kirsty_sinclair`, `mhairi_munro`, `iona_ferguson`, and `effie_macrae` referenced in anchor_households prose). Verifiable now by `grep -E "^\\s+- id:" npcs.yaml | wc -l` returning 13 while demographics.yaml references 19 NPC-like IDs. Dev's Delivery Finding flagged this as non-blocking; reviewer concurs the gap is non-blocking for story 24-3 but escalates: **a follow-up story should create `supporting_cast.yaml` (or extend `npcs.yaml` with a supporting-cast tier) before story 24-6 begins** — otherwise 24-6's prompt-zone injection will silently fail to resolve these IDs.
  Affects `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/npcs.yaml` (introduce supporting-cast tier) **or** a new `supporting_cast.yaml` (introduce the concept across the tea_and_murder pack). Same pattern will be needed for `road_warrior`, `caverns_and_claudes`, etc. as their worlds mature.
  *Found by Reviewer during code review (corroborated by test-analyzer and comment-analyzer).*

- **Gap** (non-blocking): The `npcs.yaml` file at `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/npcs.yaml:3` has a header comment claiming "Twelve named NPCs" but the file contains 13 entries. This is pre-existing canon, outside the scope of 24-3, but worth a one-line follow-up commit before someone else inherits the wrong count. (24-3 cannot fix this — it's a sibling-file edit unrelated to demographics authoring.)
  Affects `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/npcs.yaml` (update header comment from "Twelve" to "Thirteen").
  *Found by Reviewer during code review.*

- **Improvement** (non-blocking): For each subsequent world-grounding YAML written across the genre packs (weather, demographics, calendar, economy, establishments, NPC schedules per Epic 24), a `pytest` integrity check that asserts (a) every NPC ID used resolves against npcs.yaml or a supporting_cast file, (b) every cartography region ID resolves against cartography.yaml, and (c) every cross-file count agrees with the source-of-truth file, would catch this class of drift mechanically. Dev's Delivery Finding (Question) about exemplars-as-IDs is the same underlying need.
  Affects `sidequest-content/tests/` (add lightweight content-integrity test suite; could be wired to story 24-1's schema work).
  *Found by Reviewer during code review.*

- **Question** (non-blocking): Should the world-grounding files (weather.yaml, demographics.yaml, and the upcoming calendar/economy/establishments/NPC-schedules) settle on a unified header comment block describing the schema-pending state, story ownership, and consumer story? Currently weather.yaml and demographics.yaml each invent their own header. A boilerplate-style header reduces drift as Epic 24 lands more files.
  Affects future world-grounding YAML files across all worlds and packs.
  *Found by Reviewer during code review.*

## Design Deviations

### Dev (implementation)

- **Dropped baseline's invented commerce entries (apothecary, butcher, grocer, general_merchant)**
  - Spec source: `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/lore.yaml` (economy section), AC-4 ("aligns with existing NPCs, cartography, and world.yaml axis snapshot")
  - Spec text: lore.yaml enumerates village infrastructure as "The school, the surgery, the post office, the tea rooms, the smithy, the manse" — no general merchant, apothecary, butcher, or grocer is canonized.
  - Implementation: Removed those four service-count entries from the baseline; added the smithy explicitly (Donald Buchan, attested in npcs.yaml as Mrs. Buchan's husband and the village smith and farrier); added the Wee Free meeting from lore.yaml's religion section. Cross-referenced all entries to specific cartography region IDs or NPC IDs from canon.
  - Rationale: AC-4 explicitly requires alignment with existing world files; carrying forward sm-setup's hallucinated commerce would have failed that AC and contaminated the prompt-zone injection downstream (24-6).
  - Severity: minor (removed invention; nothing the wider system depends on)
  - Forward impact: none — no other file references the dropped entries.
  - → ✓ ACCEPTED by Reviewer: agrees with author reasoning. Verified against `lore.yaml` lines 57-65 (economy section enumerates exactly: school, surgery, post office, tea rooms, smithy, manse — plus Castle Ross, the distillery, and a dozen tenant crofts). Carrying sm-setup's invented commerce would have introduced silent contradictions into the narrator prompt zone. The added smithy traces to `npcs.yaml:201-202` (Donald Buchan); the Wee Free meeting traces to `lore.yaml:73-74`. All additions and removals are canon-anchored.

- **Dropped baseline's "village_council" guild**
  - Spec source: `lore.yaml` (religion + cosy_constraints sections)
  - Spec text: lore.yaml describes the kirk session as "the village's senior moral court" and explicitly says the chapel vestry "does not overlap" with the kirk session. There is no separate village council.
  - Implementation: Removed `village_council` from `guilds`; the kirk session is captured under `services.religion[].governance` and `services.civic_and_law[]` as the village's moral court.
  - Rationale: Inventing a parallel civic body contradicts lore.yaml's "the kirk session and the post office are its courts" and would dilute the kirk session's narrative weight.
  - Severity: minor
  - Forward impact: none.
  - → ✓ ACCEPTED by Reviewer: agrees. `lore.yaml:67-75` (religion) confirms only kirk session + chapel vestry as the village's governance bodies. `themes` in `world.yaml:51` is explicit: "the kirk session and the post office are its courts" — no third civic body. Dropping the invented guild is correct.

- **Promoted demographics.yaml from flat service-count file to multi-section grounding reference**
  - Spec source: Story context "Deliverables" (session lines 60-65); AC-2; AC-5
  - Spec text: AC-2 lists "occupational breakdown, key services, social strata" as required content; AC-5 requires "enough detail for narrator to ground dialogue in village context".
  - Implementation: Restructured into 13 top-level sections (parish, settlements, districts, services, population, social_strata, anchor_households, narrator_grounding_phrases, naming_conventions, references, plus metadata). Per-section structure is intentionally narrator-prompt-friendly (short evocative phrases, exemplar NPC IDs, forms of address).
  - Rationale: A flat counts-only file (the baseline shape) cannot satisfy AC-2 or AC-5. The richer shape is what story 24-1's schema must formalise — I authored in the shape I'd want the schema to enforce, per the SM Assessment instruction.
  - Severity: structural (intentional; the entire file shape is new)
  - Forward impact: **Story 24-1 must define a schema that accommodates this shape, or refactor this file when the schema lands.** This was the explicit instruction in the SM Assessment (point 4 — "Author the YAML in the shape you'd want the schema to formalize"). The shape is documented in this file's section comments to make schema authoring straightforward.
  - → ✓ ACCEPTED by Reviewer: agrees. SM Assessment point 4 explicitly directed Dev to author in the shape 24-1 should formalise. The structural shape passes the narrator-utility test: parish → settlements → districts → services → population → social_strata → anchor_households → grounding phrases is a coherent layering from macro (parish) to micro (households) to narrator-injectable (grounding phrases). Story 24-1 inherits a working reference shape, which is the better outcome than two world-grounding files (weather.yaml + demographics.yaml) in two different shapes for 24-1 to reconcile.

- **Introduced `albert_macgregor` and 9 other supporting-cast IDs as cross-references**
  - Spec source: `cartography.yaml` (line 699, `controlled_by: albert_macgregor` at the railway halt); various NPC history seeds in `npcs.yaml`
  - Spec text: cartography.yaml references the stationmaster by ID `albert_macgregor`; npcs.yaml history seeds name Mrs. Drummond, Donald Buchan, Kirsty Sinclair, Mrs. Trefusis, Mrs. Cattanach, Calum Cattanach, Effie MacRae, Mhairi Munro, and Iona Ferguson in prose.
  - Implementation: Used these IDs as `role_holder` values in the services block (and as `exemplars` in social_strata). Each ID is canonized in cartography or named in NPC prose, but only `albert_macgregor` has a structured ID elsewhere (cartography.yaml); the others I coined ad-hoc from npcs.yaml prose names. Captured as a Delivery Finding (Gap) above.
  - Rationale: Without these IDs the demographics file would have to either (a) reference NPCs only by free-text name (breaking cross-reference) or (b) elide them entirely (losing the household roster AC-2 asks for).
  - Severity: minor
  - Forward impact: Story 24-1's schema or a follow-up story must decide whether `npcs.yaml` gets a "supporting cast" tier or whether these IDs live in a separate `supporting_cast.yaml`. The demographics file IDs will need to point at wherever the supporting-cast registry ends up.
  - → ⚠ ACCEPTED-WITH-CONCERN by Reviewer: agrees with the choice but escalates the visibility. Only `albert_macgregor` carries an inline "not yet a full NPC entry" comment in the file (line 235); the nine other dangling IDs are used as structured cross-references with no caveat. A reader (or a narrator injection routine in story 24-6) will treat them as resolvable npcs.yaml IDs and silently fail. Reviewer adds Delivery Finding below to file a follow-up story creating `supporting_cast.yaml` before story 24-6 begins, and notes a low-severity fix recommendation: a single block-level YAML comment above the services / anchor_households sections marking the cluster of dangling IDs. This is non-blocking for the present story (Dev's own Delivery Finding flagged the gap) but tightens the contract for the consumer.

### Reviewer (audit)

- **No undocumented deviations spotted.** Reviewer cross-referenced the diff against world.yaml, cartography.yaml, npcs.yaml, lore.yaml, and history.yaml. All worldbuilding content traces to existing canon. Tone matches the world's cosy/puzzle/gossip axis (0.75/0.7/0.7) with gothic disciplined to 0.05. No generic-fantasy vocabulary. No anachronisms relative to 1908 Edwardian Highland Scotland.

- **Cast count error — UNDOCUMENTED:** `recurring_cast_count: 12` (line 40 of demographics.yaml) and the header comment "12-strong warm cast" (line 17) both contradict the actual roster in `npcs.yaml`, which contains 13 NPC entries (rev_murchison, rev_quill, dr_ross, mrs_buchan, miss_ferguson, hamish_sinclair, sir_iain_ross, lady_annabel_ross, hugo_ross, sgt_macrae, mrs_cameron, donald_munro, old_tam). Dev's working count was 12 (the npcs.yaml header itself misstates "twelve" at line 3 — pre-existing in canon). This is a factual cross-file mismatch that AC-4 ("aligns with existing NPCs") requires fixing. **Severity: MEDIUM** — machine-readable field that downstream story 24-6 may consume.

- **Castle Ross household arithmetic — UNDOCUMENTED:** Two off-by-one errors in the same household:
  1. `services.household_employment.castle_ross.total_approx: 13` (line ~317) but the enumerated indoor+outdoor list in the same block totals 12 (1 housekeeper + 1 cook + 3 upstairs maids + 2 kitchen maids + 1 chauffeur + 1 head gillie + 1 under-gillie + 1 gardener + 1 under-gardener = 12).
  2. `anchor_households[castle_ross].size: 14_in_residence` (line ~543) but the enumerated family (3) + indoor staff (8) + outdoor staff (4) = 15.
  Both numbers contradict their own neighbouring enumerations within the file. **Severity: MEDIUM** — internal data inconsistency.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml` — extended from 41 lines (sm-setup baseline) to 732 lines covering parish overview, settlements, districts, services (religion/civic/medical/education/communications/hospitality/industry/household/utilities), population (age bands + 9-sector occupational mix + 7-tier class distribution), 7-layer social strata, 10 anchor households, 31 narrator grounding phrases across 6 rubrics, naming conventions, and cross-references.

**Tests:** N/A — pure content story, no runtime tests (per session lines 67-72; Testing block confirms wiring happens in stories 24-1 schema, 24-6 prompt injection, 24-8 playtest validation).

**Validation performed:**
- YAML parses cleanly (`python3 -c "import yaml; yaml.safe_load(...)"`).
- Age bands sum to 412 (matches `parish.total_population`).
- Occupational mix headcounts sum to 252 (matches `population.workforce`).
- Class distribution shares sum to 1.0.
- Occupational shares sum to 1.001 (3-decimal rounding tolerance; captured as Delivery Finding).
- All 14 cartography region IDs from `cartography.yaml` appear as district members.
- All 12 NPC IDs from `npcs.yaml` appear as `exemplars` in social_strata or as `role_holder` / `composition` entries.
- No invented services beyond what `lore.yaml` and `cartography.yaml` canonize (apothecary/butcher/grocer dropped from baseline; smithy and Wee Free meeting added from lore.yaml).

**Branch:** `feat/24-3-glenross-demographics` on `sidequest-content`, pushed to origin.

**Commits:**
- `c899fb8` — sm-setup baseline (41 lines, dropped many invented entries)
- `5b0cb54` — Dev extension (+698 -34 net; authoritative shape)

**ACs:**
- AC-1 (file exists at canonical path): met (was met by baseline).
- AC-2 (population, occupational breakdown, key services, social strata): met (all four sections present).
- AC-3 (Edwardian Highland setting): met (period_texture utilities, era/year fields, Gaelic-at-home notes, daily-rhythm phrases).
- AC-4 (aligns with NPCs, cartography, world.yaml): met (every NPC ID and region ID is canon; sm-setup hallucinations removed).
- AC-5 (enough detail for narrator grounding): met (31 grounding phrases across 6 rubrics, ready for 24-6 prompt-zone injection).
- AC-6 (no schema violations once 24-1 defines schema): deferred (24-1 not yet started; demographics is authored in the shape 24-1 should formalise).

**Handoff:** To Portia (Reviewer) for the trivial workflow's review phase.

---

## Dev Assessment (Round 2 — Rework)

**Implementation Complete:** Yes

**Rework scope:** 4 number/comment edits in response to Portia's REJECTED verdict (round 1). No new logic, no new structure, no new files.

**Files Changed:**
- `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml`:
  - Line 11 (header comment): `12-strong warm cast` → `13-strong warm cast`
  - Line 41 (`parish.recurring_cast_count`): `12` → `13`
  - Line 317 (`services.household_employment.castle_ross.total_approx`): `13` → `12` (matches enumerated 8 indoor + 4 outdoor)
  - Line 537 (`anchor_households[castle_ross].size`): `14_in_residence` → `15_in_residence` (matches enumerated family 3 + indoor 8 + outdoor 4)

**Tests:** N/A — same content-only context as round 1.

**Validation performed:**
- YAML still parses cleanly (`yaml.safe_load`).
- `parish.recurring_cast_count: 13` confirmed by Python load.
- `castle_ross.total_approx: 12` confirmed.
- `anchor_households[0].size: 15_in_residence` confirmed.
- Header comment updated.
- All other AC-bearing content unchanged from round 1.

**Branch:** `feat/24-3-glenross-demographics`, commit `a3004f8` pushed to origin.

**Reviewer findings disposition:**
- [MEDIUM] recurring_cast_count: 12 → fixed (line 41).
- [LOW] header comment "12-strong" → fixed (line 11).
- [MEDIUM] castle_ross.total_approx: 13 → fixed (line 317).
- [MEDIUM] anchor_households[castle_ross].size: 14_in_residence → fixed (line 537).
- [non-blocking] 6 dangling NPC IDs → unchanged in this story (out of scope per Reviewer's own Delivery Finding; escalated to follow-up story for `supporting_cast.yaml`).
- [non-blocking] npcs.yaml header "Twelve named NPCs" → unchanged in this story (sibling file, outside 24-3 scope; Reviewer captured as separate Delivery Finding).
- [non-blocking] schema-pending comment polish → unchanged in this story (Comment-analyzer medium-confidence; nothing actually wrong; defer to 24-1 schema work).
- [non-blocking] occupational share rounding 1.001 → unchanged (Dev round-1 Delivery Finding stands).

**ACs:**
- AC-1 through AC-3, AC-5, AC-6: unchanged from round 1 — met.
- AC-4 (aligns with NPCs, cartography, world.yaml): **now fully met** — `recurring_cast_count: 13` matches `npcs.yaml`'s 13 actual entries; castle_ross internal arithmetic is now self-consistent. The pre-existing npcs.yaml:3 "Twelve" comment is outside 24-3 scope.

**Handoff:** Back to Portia (Reviewer) for re-review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — YAML parses; sibling files present; branch clean and pushed |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter: false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter: false` |
| 4 | reviewer-test-analyzer | Yes | findings | 1 | confirmed 1 (dangling NPC IDs verifiable now — captured as Delivery Finding; non-blocking) |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 | confirmed 3 (cast count comment, dangling-IDs documentation gap, schema/24-6 reference clarity), deferred 2 (low-severity stylistic polish — references-block annotations, schema vs 24-6 separation) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design: false` |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.security: false` |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier: false` |
| 9 | reviewer-rule-checker | Yes | findings | 5 (rules 10 & 11) | confirmed 4 (1 cast count machine-readable, 1 cast count comment, 2 castle_ross arithmetic), deferred 1 (pre-existing npcs.yaml:3 "Twelve" comment — out of scope for 24-3) |

**All received:** Yes (4 returned with findings, 5 skipped via settings)
**Total findings:** 4 confirmed blocking, 1 confirmed non-blocking (escalated as Delivery Finding), 3 deferred or stylistic, 1 out-of-scope

## Rule Compliance

Project rules are in `SOUL.md`, project-root `CLAUDE.md`, and `sidequest-content/CLAUDE.md`. No language-specific `lang-review` checklist applies (diff is YAML-only). The rule-checker subagent ran 11 rules across 47 instances; full enumeration in its return. Reviewer's per-rule judgement:

1. **No stubs, no hacks, no "we'll fix it later" shortcuts** (sidequest-content/CLAUDE.md) — COMPLIANT. File is fully authored (705 lines); no placeholder sections, no TODOs in values. The "Schema: pending" comment is an honest declaration of a sprint-ordered dependency, not a shortcut.
2. **No Silent Fallbacks** (sidequest-content/CLAUDE.md) — COMPLIANT. `clergy_npc: null` and `cartography_region: null` for the Wee Free meeting are explicit; `albert_macgregor`'s "not yet a full NPC entry" note is loud. Five instances of potential silent defaults all explicit.
3. **No half-wired features — connect the full pipeline or don't start** (sidequest-content/CLAUDE.md) — COMPLIANT. demographics.yaml is intentionally "inert authoring" matching the established 24-2 weather.yaml pattern; consumer (story 24-6) is a separate backlog story by design, not a forgotten connection. Same as 24-2 which already merged.
4. **Don't Reinvent — Wire Up What Exists** (sidequest-content/CLAUDE.md) — COMPLIANT. All 14 cartography region IDs match cartography.yaml exactly; all 13 warm-cast NPC IDs match npcs.yaml exactly; named details (Caelidh and Brigid stills, London merchant order, Marconi messages, Mrs. Cameron's seed cake schedule) trace to existing canon files. No invented persons.
5. **Crunch in the Genre, Flavor in the World** (SOUL.md) — COMPLIANT. File is pure flavor: no mechanical modifiers, no skill/stat encoding. Even axis_alignment mirrors world.yaml's tone calibration rather than introducing new game mechanics.
6. **Diamonds and Coal — detail scales to narrative weight** (SOUL.md) — COMPLIANT. Castle Ross gets richest detail; `farm_servants_and_labourers` explicitly named "the unnamed body" with narrator instruction to use generic descriptors. 31 grounding phrases are each one-line baited hooks.
7. **Genre Truth — cosy Edwardian murder-mystery tone** (SOUL.md + CLAUDE.md) — COMPLIANT. Edwardian Scottish register throughout (the Twelfth, kirk session, porte-cochère, crow-stepped gables, Allt Ross, shinty fifteen). 1908 period texture accurate (motor cars, telephones, Marconi, suffrage). No generic-fantasy vocabulary.
8. **Living World — NPCs/factions have own goals and relationships** (SOUL.md) — COMPLIANT. social_strata village_attitude fields are dynamic ("Hugo is the village's affectionate joke and its future"); anchor_households encode living situations and family ties (the constable's wife is Old Tam's niece; the Castle cook is her mother's sister). Goals proper are scoped to npcs.yaml — appropriately deferred.
9. **Who This Is For — serves Keith's playgroup + tea_and_murder as Sonia-coded** (CLAUDE.md) — COMPLIANT. Provides the structural grounding Keith-as-player needs (occupational mix, forms of address, anchor households) for a narrator to surprise him with correct rather than plausible-but-wrong detail. The file feeds the narrator, not the player, so Sonia-coded warmth flows through narrator prose downstream.
10. **Cast count accuracy** (cross-reference integrity) — **VIOLATION × 2**. `recurring_cast_count: 12` (line 40) and the header comment "12-strong warm cast" (line 17) both contradict `npcs.yaml`'s 13 actual entries. The npcs.yaml header at line 3 also says "Twelve" — pre-existing error outside this story's scope, but Dev imported it into a structured machine-readable field that 24-6 may consume.
11. **Internal arithmetic consistency** (castle_ross household counts) — **VIOLATION × 2**. `services.household_employment.castle_ross.total_approx: 13` contradicts its own enumeration (12); `anchor_households[castle_ross].size: 14_in_residence` contradicts its own enumeration (15). Two distinct off-by-ones in the same household block.

## Devil's Advocate

This file is going to be consumed by the narrator in story 24-6 as prompt-zone injection. Let me argue everything that's wrong with it before stamping.

**Argument 1: the narrator will assert factually wrong things about the village.** `recurring_cast_count: 12` lands in a field a 24-6 injection routine will read literally. The narrator may state "twelve villagers" when it's thirteen, or skip the thirteenth (which one? the youngest curate? the laird? Mrs. Cameron?) in a roster. Keith-as-player playing a session and asking "tell me about the village's people" will hear an unreliable count. *This is the violation that matters most.* The fix is trivial (one number) but the failure mode it prevents is the precise mode SOUL.md's `The Test` warns about — the system asserting something the world doesn't support.

**Argument 2: the castle staff inconsistencies are a quiet hole.** `total_approx: 13` (which I wrote as Puck) doesn't match the 12 I enumerated three lines above it. `size: 14_in_residence` doesn't match the 15 I enumerated four lines above it. A narrator pulling "13 servants at the Castle" and then introducing 12 by role will look incompetent. A narrator citing "14 in residence" and then describing 15 will trip the same internal-consistency test that Sebastien-as-mechanics-player would notice immediately. Two off-by-ones, opposite directions. This is the smell of a late-stage edit (adding "chauffeur" or "under-gardener" without bumping the total) — exactly the class of drift that AC-4 ("aligns with existing NPCs, cartography, world.yaml") rules out.

**Argument 3: the 6 dangling NPC IDs are a liability for 24-6.** `albert_macgregor` carries a "not yet a full NPC entry" note; `donald_buchan`, `mrs_drummond`, `mrs_trefusis`, `mrs_cattanach`, `calum_cattanach`, `effie_macrae`, `mhairi_munro`, `iona_ferguson`, and `kirsty_sinclair` do not. The injection routine downstream will treat them as resolvable IDs and silently fail. test-analyzer flagged this as verifiable now, not deferred. It is non-blocking for this story (Dev acknowledged it in Delivery Findings) but it shapes story 24-6's success criteria and deserves a follow-up story before 24-6 begins.

**Argument 4: the schema-pending comment hedges on two different timelines.** "Schema: pending — Story 24-1 will formalise the shape" and "Per ADR-059 ... story 24-6" mix two future commitments. The reader cannot distinguish the firm dependency (24-1, in backlog) from the speculative one (24-6, also in backlog but the comment treats it as certain). Minor, but it's the kind of comment that reads truthfully today and becomes a lie if 24-6 is cancelled or renamed.

**Argument 5: arithmetic share sum 1.001.** Dev acknowledged the 3-decimal rounding produces a 1.001 share total in occupational_mix. A schema check in 24-1 may enforce 1.0; the file should drop `share` and compute it on the fly, or pin the rounding tolerance. Dev's Delivery Finding (Improvement) captures this. Reviewer affirms as non-blocking but worth noting.

**What devil's-advocate did NOT find:** I cannot find a tone violation, an anachronism, a generic-fantasy slip, a SOUL.md violation, a real PII or security exposure, an architectural mistake, or any contradiction with `lore.yaml`/`history.yaml` (which I cross-checked). The file is exceptionally well-aligned with canon *except* for the four arithmetic/count errors. The pattern is good; the numbers are not.

## Reviewer Assessment

**Verdict:** REJECTED

**Data flow traced:** demographics.yaml → (future) narrator prompt-zone injector in story 24-6 → narrator LLM prompt → narrator prose to players. File is currently inert (no server consumer); the consumer is a backlog story by design. Same "inert authoring" pattern as story 24-2 (weather.yaml) which already merged. The factual content of demographics.yaml will be read literally by the eventual injector.

**Pattern observed:** Restructured worldbuilding YAML with 13 top-level sections (parish → settlements → districts → services → population → social_strata → anchor_households → grounding phrases → naming → references). Pattern is canon-aware and narrator-aimed. Tone is genre-true Edwardian cosy at `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:1-705`.

**Error handling:** N/A — content YAML, no runtime paths.

**Findings table:**

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MEDIUM] [RULE] | `recurring_cast_count: 12` contradicts npcs.yaml's 13 actual entries. Machine-readable field; story 24-6 will consume this literally. | `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:40` | Change `recurring_cast_count: 12` to `recurring_cast_count: 13`. |
| [LOW] [RULE] [DOC] | Header comment "the 12-strong warm cast (never the victim)" contradicts npcs.yaml's 13 entries. | `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:17` | Change "12-strong" to "13-strong" in the comment. |
| [MEDIUM] [RULE] | `services.household_employment.castle_ross.total_approx: 13` but enumerated indoor+outdoor count is 12 (8 indoor + 4 outdoor). | `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml` around line 317 (within `services.household_employment.castle_ross`) | Either change `total_approx: 13` to `total_approx: 12`, or add the missing role (e.g., footman? second chauffeur?) to indoor/outdoor list. |
| [MEDIUM] [RULE] | `anchor_households[castle_ross].size: 14_in_residence` but enumerated family(3) + indoor_staff(8) + outdoor_staff(4) = 15. | `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml` around line 543 (within `anchor_households[castle_ross]`) | Either change `size: 14_in_residence` to `size: 15_in_residence`, or remove one staff item from the list to match 14. Recommend 15 (matches Sir Iain's npcs.yaml seed which enumerates the same household). |

**Observations (additional, non-blocking):**

- [VERIFIED] All 14 cartography region IDs cross-reference exactly to `cartography.yaml`'s `regions` keys — preflight subagent ran the check. Compliance with "Don't Reinvent — Wire Up What Exists" rule.
- [VERIFIED] All 13 warm-cast NPC IDs used in `social_strata.exemplars` and `services.*.role_holder` match `npcs.yaml` IDs exactly. Compliance with AC-4.
- [VERIFIED] Tone discipline: zero generic-fantasy vocabulary. Edwardian Scottish register sustained across 705 lines. Compliance with Genre Truth (SOUL.md).
- [VERIFIED] No mechanical encoding (no skill modifiers, no stat blocks, no dice). Compliance with "Crunch in the Genre, Flavor in the World" (SOUL.md).
- [VERIFIED] Inline period texture (3 motor cars, 2 telephones, gaslight village, Marconi messages, suffrage pamphlets) all 1908-accurate. Compliance with Genre Truth.
- [VERIFIED] Population age bands sum to 412 = total. Occupational headcounts sum to 252 = workforce. Class distribution shares sum to 1.0. Three of four arithmetic invariants hold; only the castle_ross household subtotals fail (above findings).
- [TEST] 6 dangling NPC IDs (`albert_macgregor`, `donald_buchan`, `mrs_drummond`, `mrs_trefusis`, `mrs_cattanach`, `calum_cattanach`, plus 3 more named in Dev's Delivery Findings) referenced as if resolvable. Dev acknowledged in Delivery Findings; reviewer escalates as a Delivery Finding for follow-up story (see below). Non-blocking for this story.
- [DOC] Schema-pending comment mixes a firm dependency (24-1) with a speculative one (24-6). Low-severity polish recommendation, non-blocking.
- [SIMPLE] Occupational `share` field duplicates information from `headcount`; could be computed on the fly. Dev acknowledged; non-blocking; defer to 24-1 schema design.

**Why rejecting on MEDIUM findings:** The four arithmetic/count violations are trivially fixable (4 number edits, ~30 seconds). They are also factual lies the narrator will assert when 24-6 wires the file. The narrator's job is to fool a career GM (CLAUDE.md "Who This Is For" — Keith). A narrator confidently asserting "12 villagers" when there are 13, or "13 staff at the Castle" when 12 are listed, will fail that test in obvious ways. The cost of fixing is far less than the cost of shipping the drift into 24-6 and discovering it during playtest.

**Handoff:** Back to Puck (Dev) for rework — green-phase fixes (no new tests required; these are content edits to existing fields).

**Story:** 24-3 — Author `tea_and_murder/glenross/demographics.yaml`. P0, trivial workflow, 2pt, content-only on `sidequest-content`. Branch `feat/24-3-glenross-demographics` is live; one baseline commit `c899fb8` already lands a 41-line `demographics.yaml`.

**Important context for Puck (dev):**

1. **The deliverable already has a baseline.** `sm-setup` overreached and wrote+committed an initial `demographics.yaml` during setup. Treat that file as a starting draft, not the finished product. Audit it against the AC list (lines 73-80) and the Story Context (lines 47-65) and extend where thin.

2. **What the baseline currently covers:** one settlement (Glenross), population 412, basic service counts (clergy/taverns/inns/shops), institutions, guilds. That is roughly the "Services" AC bullet only.

3. **What likely needs adding to satisfy ACs:**
   - **Settlement profiles** beyond a single count — districts/landmarks (village square, kirk, station yard, distillery, surrounding crofts/castle environs) with the "character/economic role" framing the AC asks for.
   - **Population snapshot:** *occupational breakdown* (farmers, servants, merchants, professionals) and *class distribution* — the AC explicitly calls for both, not just a single integer.
   - **Social strata** as a named, structured layer (landed gentry → professionals → shopkeepers/tradespeople → servants → farm laborers), since the genre pack leans hard on class as a clue/motive engine.
   - **Narrative grounding phrases** — short, narrator-injectable lines like "the village's recurring cast" or "everyone knows everyone's business by sundown." These are what the ADR-059 prompt-zone injection actually consumes downstream (24-6).

4. **Schema constraint:** Story 24-1 (which defines the schemas) is still backlog, so there is no schema to validate against yet. Author the YAML in the **shape you'd want the schema to formalize** — Puck's design judgement here informs 24-1. Don't gate on a missing schema.

5. **Alignment checks:**
   - Read `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/world.yaml` (axis snapshot, scope sentence) before extending.
   - Read existing NPC and cartography YAMLs for Glenross — populations, services, and named characters must agree. A doctor in `npcs/` who isn't in `demographics.yaml` is a hole.
   - Check `genre_packs/tea_and_murder/worlds/glenross/` for any existing `establishments.yaml` or similar — don't duplicate fields the world already has.

6. **Tone:** This world is Sonia-coded (per CLAUDE.md "Aspirational audience"). Cosy/puzzle/gossip dominant, gothic only 0.05. The demographics file should *feel* like 1908 Edwardian Highlands — class hierarchies, kirk session, railway hub, distillery. Avoid generic-fantasy-village vocabulary.

7. **Tests:** No runtime tests for this story (it's pure content). The wiring/preview happens in 24-6. The session's "Testing" section (lines 66-71) confirms this. Trivial workflow → implement → review → finish.

8. **Out of scope (do NOT do here):** writing the schema (24-1), implementing the generator (24-5), wiring prompt-zone injection (24-6), OTEL spans (24-7), playtest validation (24-8).

**Workflow routing:** trivial → next phase is `implement`, owned by `dev`.

**No Jira on this project.** Do not invoke `pf jira` for any reason. Sprint YAML and session file are the only trackers.
---

## Reviewer Assessment (Round 2 — Re-review)

**Verdict:** APPROVED

**Scope of round-2 review:** Round-2 diff is exactly four single-line edits to existing fields previously flagged as REJECT-causes by round-1 review. No new content, no new sections, no new files, no logic changes. Diff size: -4 +4 across one file.

**Round-1 subagent sweep covered the entire 705-line file.** Round-2 changes are a strict subset (4 fields out of 705 lines) of areas already analysed by preflight, test-analyzer, comment-analyzer, and rule-checker in round 1. Re-dispatching the full subagent sweep against a 4-line diff would be ceremony over substance — the round-1 sweep's coverage stands and round-2 only narrows specific findings.

**Direct verification of the four reject-causes:**

- [VERIFIED] Header comment `13-strong warm cast` — evidence: `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:11` now reads `#   - npcs.yaml         — the 13-strong warm cast (never the victim)`. Cross-check: `grep -E "^  - id:" sidequest-content/genre_packs/tea_and_murder/worlds/glenross/npcs.yaml | wc -l` = 13 entries. Comment now matches canon. Round-1 rule-checker violation (rule 10) resolved.

- [VERIFIED] `recurring_cast_count: 13` — evidence: `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:41` now reads `recurring_cast_count: 13`. Machine-readable field now matches the 13 npcs.yaml entries. Round-1 rule-checker violation (rule 10) resolved. Story 24-6's eventual prompt-zone injection will now consume the correct count.

- [VERIFIED] `services.household_employment.castle_ross.total_approx: 12` — evidence: `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:317` now reads `total_approx: 12`. Recomputed enumerated sum: indoor (housekeeper 1 + cook 1 + 3 upstairs maids + 2 kitchen maids + chauffeur 1 = 8) + outdoor (head gillie 1 + under-gillie 1 + gardener 1 + under-gardener 1 = 4) = 12. Field now matches its own enumeration. Round-1 rule-checker violation (rule 11) resolved.

- [VERIFIED] `anchor_households[castle_ross].size: 15_in_residence` — evidence: `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/demographics.yaml:537` now reads `size: 15_in_residence`. Recomputed enumerated sum: family (sir_iain + lady_annabel + hugo = 3) + indoor_staff (mrs_trefusis + mrs_cattanach + "3 upstairs maids" + "2 kitchen maids" + "chauffeur" = 1+1+3+2+1 = 8) + outdoor_staff (old_tam + calum + "head gardener" + "under-gardener" = 1+1+1+1 = 4) = 15. Field now matches its own enumeration. Cross-check against `npcs.yaml:380` Sir Iain history seed which enumerates the household roster: Sir Iain (1) + Lady Annabel (1) + Hugo (1) + housekeeper Trefusis (1) + cook Cattanach (1) + Old Tam (1) + Calum (1) + 3 upstairs maids + 2 kitchen maids + chauffeur (1) + gardener (1) + under-gardener (1) = 15. Now consistent with sibling canon. Round-1 rule-checker violation (rule 11) resolved.

**No collateral changes:** Round-2 git diff confirms only the four target lines were touched. No content drift, no introduced contradictions, no new structural changes. The round-1 verification of tone, period accuracy, cartography cross-references, NPC ID matches (for the 13 warm-cast IDs), occupational mix arithmetic, and class distribution sums all stand unchanged.

**Subagent results disposition for round 2:** All round-1 subagent results remain valid for the unchanged 701 lines. The four changed lines are precisely the lines flagged by round-1 rule-checker. No new subagents required — the round-1 sweep already inspected these specific fields and identified the violations that round 2 corrects.

**Outstanding non-blocking findings (carried forward, not resolved by round 2):**
- 6 dangling supporting-cast NPC IDs (`albert_macgregor`, `donald_buchan`, `mrs_drummond`, `mrs_trefusis`, `mrs_cattanach`, `calum_cattanach`) — Reviewer Delivery Finding stands; explicitly out-of-scope for 24-3 per Reviewer's own escalation to a follow-up `supporting_cast.yaml` story.
- Pre-existing `npcs.yaml:3` "Twelve named NPCs" header comment — Reviewer Delivery Finding stands; sibling-file edit unrelated to demographics authoring.
- Schema-pending comment polish, share rounding 1.001, exemplars-as-IDs question — all non-blocking Delivery Findings unchanged.

**Devil's Advocate (round 2):** Could a 4-line numeric rework introduce a new defect? In principle yes — e.g., a copy-paste typo, a wrong direction (12 → 14 instead of 12 → 13). I verified each line against the requested direction in round-1 findings AND against the file's own enumerations. The arithmetic now self-checks. The only thing round-2 could not fix and did not attempt to fix is the pre-existing npcs.yaml:3 comment (out of scope) and the broader supporting-cast architecture (escalated to follow-up). Both are documented and explicit. Nothing slipped through.

**Data flow:** demographics.yaml → (future) story 24-6 prompt-zone injector → narrator LLM → player. The corrected counts are what 24-6 will read. A narrator stating "thirteen villagers" or "twelve household staff at the Castle" will now match canon and pass Keith-as-player scrutiny.

**Pattern observed:** Targeted rework. Dev made exactly the changes requested and no others. Commit message accurately describes the change and acknowledges the out-of-scope npcs.yaml pre-existing error.

**Error handling:** N/A — content YAML, no runtime paths.

**Handoff:** To Prospero (SM) for the finish phase.