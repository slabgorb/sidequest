---
story_id: "103-8"
jira_key: ""
epic: "103"
workflow: "trivial"
---
# Story 103-8: Stocks + dramatic content (GM lane) — full stock roster, Penitent flavor-focus over AWN classes, tropes.yaml, openings.yaml, archetypes.yaml, bestiary/creatures, currency flavor (Mint coins, regional scrips)

## Story Details
- **ID:** 103-8
- **Jira Key:** (not configured)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-11T09:22:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-11T06:17:15Z | 2026-06-11T09:01:07Z | 2h 43m |
| implement | 2026-06-11T09:01:07Z | 2026-06-11T09:09:55Z | 8m 48s |
| review | 2026-06-11T09:09:55Z | 2026-06-11T09:22:32Z | 12m 37s |
| finish | 2026-06-11T09:22:32Z | - | - |

## Sm Assessment

**Verdict:** Setup complete — handoff to Dev for `implement` phase.

- **Story:** 103-8 — Stocks + dramatic content (GM lane). Content-only, trivial workflow.
- **Repo / branch:** sidequest-content @ `feat/103-8-seaboard-stocks-dramatic-content` (created).
- **Story context:** `sprint/context/context-story-103-8.md` — written with full technical guardrails, scope boundaries (in/out), 6 ACs, and assumptions.
- **Technical approach:** Full stocks.yaml roster (Animal/Plant/Synthetic variants) conforming to frozen 103-2 schema; Penitent flavor-focus archetype (no AWN classes); tropes.yaml, openings.yaml, archetypes.yaml, bestiary/creatures, currency flavor. **Zero engine/schema changes** — any schema gap is a conversation with Dev, not a content hack.
- **Key risk flags for Dev:** weapon-bearing bestiary entries MUST carry `damage:` specs (hp_depletion 0-damage lesson, 86-1); openings/tropes reference only valid 103-6 region slugs + 103-7 faction slugs; no banned currency (bottlecaps/water); cliché bans §11 + no facial-scar defaults.
- **Dependencies:** 103-2 (schema) and 103-6 (regions) merged; 103-7 faction slugs needed — coordinate if in flight.

**Handoff:** To Dev (implement phase).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings. All dependencies (103-2 schema, 103-6 regions/bestiary/encounter tables) were present and merged-to-branch; faction references resolve against the 5 lore.yaml traditions (no separate 103-7 factions.yaml is required for this story's tropes/openings, which pin by `region_id` and reference factions in prose).

### Reviewer (code review)
- **Question** (non-blocking): `kiwhosis_folk` carries a Penobscot name (muskrat) but is sited in the Hudson Valley — outside Penobscot polity territory. This is spec-faithful (design §5 authored the assignment verbatim), but it places an Indigenous-language stock outside that nation's land. Affects `genre_packs/mutant_wasteland/worlds/seaboard_of_saints/stocks.yaml` (confirm deliberate uplift-naming spread vs a spec slip — Keith's call; not a Dev fix since changing it would deviate from the governing spec). *Found by Reviewer during code review.*
- **Question** (non-blocking): The Penitent is implemented (correctly, per addendum C5) as a flavor-focus `NpcArchetype`, not a PC Calling — there is no `rules.yaml allowed_classes` entry or `char_creation` step, so a player choosing "Penitent" as a concept has only narrator-flavor, no chargen affordance. Confirm this is the intended v1 (narrator-driven flavor-focus) and any mechanical PC-Calling is a future story. Affects `.../archetypes.yaml`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, upstream/engine): A world `inventory.yaml` REPLACES the genre catalog wholesale (not merged) — this load-bearing invariant lives only in a YAML comment + `inventory_resolve.py` docstring, with no world-load assertion. A partial world inventory would silently wipe chargen loadouts. This story's inventory is full-surface (currency+item_catalog+starting_equipment+starting_gold all present — verified), so no trap is tripped here; but the loader should fail loud on a partial world inventory. Affects `sidequest-server` genre loader (add a required-surface check). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `mountain_laurel_folk` has 2 `granted_mutations` vs 3 for all 16 other Animal/Plant stocks — a one-gift asymmetry that loads fine but is mechanically lighter than every peer. Either add a third mutation or document the deliberate lighter budget in-line. Affects `.../stocks.yaml`. *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** 1 findings (0 Gap, 0 Conflict, 1 Question, 0 Improvement)
**Blocking:** None

- **Question:** `kiwhosis_folk` carries a Penobscot name (muskrat) but is sited in the Hudson Valley — outside Penobscot polity territory. This is spec-faithful (design §5 authored the assignment verbatim), but it places an Indigenous-language stock outside that nation's land. Affects `genre_packs/mutant_wasteland/worlds/seaboard_of_saints/stocks.yaml`.

### Downstream Effects

- **`genre_packs/mutant_wasteland/worlds/seaboard_of_saints`** — 1 finding

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. The 23-stock concrete roster (vs spec §5's "six stocks" conceptual framing) is the explicitly-authorized expansion in the higher-authority story context ("Full stocks.yaml roster — all Animal/Plant/Synthetic variants"), not a deviation from the governing source.

### Reviewer (audit)
- **Dev's no-deviation entry → ✓ ACCEPTED by Reviewer:** The 23-stock roster matches spec §5 + story context exactly (10 animal / 7 plant / 4 synthetic / sleeper / saint_marked); the "six stocks" in spec §5 is the conceptual category set, and the named variants under each category are the spec's own roster. Agrees with author reasoning — no deviation.
- **Undocumented (Reviewer-spotted, non-blocking):** The Penitent is realized as a flavor-focus `NpcArchetype` rather than spec §9-step-3's "new Penitent **Calling**." This is NOT an undocumented deviation — it is the governing resolution: addendum C5 (2026-06-09, "AWN wins, resolved") explicitly downgrades Penitent to "an additive flavor-focus… not a parallel class system." Code follows the higher-authority addendum over the superseded spec §9. Recorded as a Question (above) only to confirm the v1 intent, not flagged as a deviation.

## Dev Assessment

**Implementation Complete:** Yes (content authored in the GM world-builder lane; Dev verified completeness, correctness, and end-to-end loadability, then committed)

**Files Changed (sidequest-content @ `feat/103-8-seaboard-stocks-dramatic-content`):**
- `genre_packs/mutant_wasteland/worlds/seaboard_of_saints/stocks.yaml` — full 23-stock roster (10 animal, 7 plant, 4 synthetic, sleeper, saint_marked)
- `.../char_creation.yaml` — wires the stock step with `stock_id` branching
- `.../archetypes.yaml` (new) — 8 archetypes incl. the Penitent flavor-focus
- `.../inventory.yaml` (new) — Mint coin denominations + 5 regional scrips
- `.../openings.yaml` (new) — 6 region-pinned adventure seeds
- `.../tropes.yaml` (new) — 6 Seaboard tropes

**AC verification:**
1. **Roster completeness** ✓ — all spec-§5 stocks present; all granted_mutations resolve against the 103-catalog (StockRegistry load succeeds).
2. **Indigenous language anchors** ✓ — muwin/kiwhosis (Penobscot), ahtuhq/paquanaog (Wampanoag), region-bound.
3. **Penitent** ✓ — archetype loads (8 total); vow-drawback spends System Strain, no new economy field.
4. **Tropes/openings load** ✓ — 6+6; openings `region_id`s all valid; full-world load passes cross-file opening validators (solo+mp coverage, region refs).
5. **Bestiary** ✓ — every entry carries a `damage:` spec; 37/37 encounter-table creature refs resolve against bestiary ids (103-6 work, verified integrating).
6. **Currency** ✓ — Mint coin (penny→dollar) + 5 scrips; no banned bottlecap/water currency (only the explicit ban-note comment).
- Cliché bans (§11) ✓ — no facial-scar defaults, no banned name suffixes in coined names.

**Load proof:** full `load_genre_pack` against a temp copy with `draft` flipped to false assembles the world cleanly (6 openings / 6 tropes / 8 archetypes / inventory / cartography / 23 stocks / 25 saints) with no `GenreLoadError`. `draft: true` left intact in the repo (intentional selection-gating).

**Tests:** Pack structure validation PASS (0 errors); engine load smoke PASS (stocks/saints/world all parse + resolve).
**Branch:** `feat/103-8-seaboard-stocks-dramatic-content` (pushed)

**Handoff:** To Reviewer (Chrisjen Avasarala) for review.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 errors (26 pre-existing warnings) | confirmed 0, dismissed 0, deferred 0 — all 4 checks PASS (pack validate, YAML parse ×6, full draft-flipped world load, clean tree) |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 8 | confirmed 4 (non-blocking), dismissed 1 (Penitent-no-PC-path: superseded spec), deferred 3 (narrator-intent/cross-consumer) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 3 (non-blocking) — 1 HIGH (inventory replace-not-merge invariant only in comment) downgraded after verifying full-surface inventory; 2 doc nits |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 6 (1 category) | confirmed 0 blocking, downgraded 6→LOW (Section-D "no-comments" applies to genre-root; these are world files matching epic-103 + flickering_reach practice) |

**All received:** Yes (4 enabled returned, 3 with findings; 5 disabled pre-filled as Skipped)
**Total findings:** 0 confirmed blocking, 4 confirmed non-blocking (surfaced as Delivery Findings), 7 dismissed/downgraded (with rationale), 3 deferred

### Decisions on findings

- **[RULE] Section D "no-comments-in-content" (6 files) → DOWNGRADED to LOW, non-blocking.** Not dismissed — adjudicated against the rule's own scope. CONTENT_AUTHORING_CHECKLIST.md §D's actionable sweep item reads "Sweep **genre-root YAML** for inline comments"; its three worked cases were all genre-root files leaking world-fiction or hiding load-bearing rules. These six files are **world-level** (`worlds/seaboard_of_saints/`), and comment-bearing world YAML is the established epic-103 practice (saints/bestiary/cartography/lore/history all comment-laden) and matches the `flickering_reach` reference shape the build plan tells authors to follow. The *real* §D danger — load-bearing rules living only in comments — is handled as its own finding below, not by a blanket comment ban.
- **[DOC] Comment-analyzer HIGH — inventory replace-not-merge invariant only in comment → CONFIRMED non-blocking (Improvement, upstream).** This is the genuine §D concern. Verified this story's `inventory.yaml` carries the full surface (currency 5 / item_catalog 24 / starting_equipment 6 / starting_gold 6), so the silent-loadout-loss trap is NOT tripped here. The missing world-load assertion is engine infrastructure, surfaced as an upstream Improvement.
- **[TEST] Penitent has no PC chargen path (HIGH) → DISMISSED as blocking.** Rationale citing a contradicting governing rule: addendum C5 (2026-06-09, "AWN wins, resolved") states *"Penitent survives **only** as an additive flavor-focus… not a parallel class system,"* which supersedes spec §9-step-3's "new Calling." Story AC3 scopes it "flavor-focus/archetype over AWN classes… Content-only." The NpcArchetype implementation + System-Strain-via-narrator is exactly what the governing source requires. Surfaced as a Question to confirm v1 intent.
- **[TEST] kiwhosis Penobscot-name-in-Hudson-Valley → CONFIRMED non-blocking Question.** Spec-faithful (design §5 authored it verbatim); a culture-geography call for Keith, not a Dev fix.
- **[TEST] mountain_laurel_folk 2-vs-3 mutations → CONFIRMED non-blocking Improvement.** Loads + plays; balance/consistency polish.
- **[TEST] Opening-validator/AC3 "no automated test" (medium) → DEFERRED/downgraded.** The cross-file opening validators ARE wired into the load path (loader.py:1300/1304/1318 — setting refs, region bindings, opening-bank coverage) and ran clean in preflight; the AC3 strain-drawback is narrator-intent with no content-layer assertion possible (the subagent concedes this). Content has no test infra by nature.
- **[TEST] damage-spec form inconsistency (low) → DEFERRED.** Cross-consumer (inventory DamageSpec object vs bestiary string), different models, no load failure.
- **[DOC] char_creation "5-step plus stock step" + stale "(103-2)" provenance → CONFIRMED non-blocking (doc nits).** Minor; recorded for cleanup.
- **[EDGE] / [SILENT] / [TYPE] / [SEC] / [SIMPLE]:** subagents disabled (content-only YAML; no code paths, no auth surface, no type system, no control flow to simplify). Reviewer self-assessed these domains: no edge/boundary logic (pure data), no error-swallowing (declarative), no stringly-typed API risk beyond the documented id-as-name anchor convention, no security/tenant surface, nothing to simplify. N/A.

## Rule Compliance

Exhaustive enumeration against the governing rules (CONTENT_AUTHORING_CHECKLIST.md, design spec §5/§8/§11, addendum C5):

- **World-scoping (genre-root vs world):** all 6 files under `worlds/seaboard_of_saints/` — COMPLIANT (6/6).
- **Stock schema (§5 + build plan §D-B — trait set + granted_mutations + saint_affinity_allowed):** all 23 stocks COMPLIANT (rule-checker enumerated all 20 new + verified the 3 pre-existing); every `granted_mutations` id resolves against the 103-entry AWN catalog (engine StockRegistry load succeeds).
- **§5 roster completeness:** 10 animal + 7 plant + 4 synthetic + sleeper + saint_marked — all spec stocks present (COMPLIANT). Wild Mutant = stock-less default path (no stock_id, by design).
- **§8 currency:** Mint coin (penny→dollar) + exactly the 5 named scrips (Whaling Shares, Lighthouse Letters, Athenaeum Vellum, Mass Pike Tokens, Sleepers' Coupons) — COMPLIANT. Banned-list (bottlecap / MTA-token-cutout / water-currency / nuka / rare-metal-cult): zero violations; `saints_water` (healing consumable) and `purifier` (tool) are not currency; sole "bottlecap/water" mention is the explicit ban-note comment.
- **§11 cliché — banned suffixes (Reach/Veil/Spire/Hollow/Drift/Mire/Shroud/Sanctum/Bastion) in invented proper nouns:** 44 coined names checked (23 stocks, 8 archetypes, 6 tropes, 6 openings, items) — zero violations. `reach` appears only as a weapon-property tag and a prose verb; not coined names.
- **§11 cliché — no facial-scar defaults:** 87 description/narration fields checked — zero violations.
- **§11 cliché — coarse Catholic/spiritualist material:** Penitent/Adjudicator/Whitman-Circle/Lo'in all reference-stacked to specific historical anchors — COMPLIANT.
- **Addendum C5 (Penitent = flavor-focus, System Strain drawback, no bespoke economy):** COMPLIANT — System Strain is a real hook (rules.yaml:25 `system_strain: max_source: CONSTITUTION`, AWN p.52; backed by `core.system_strain` in `swn.py`); zero new economy fields across all 8 archetypes (schema-field scan returned no non-standard keys).
- **hp_depletion / weapon damage (86-1 lesson):** all 5 inventory weapons carry structured `damage: {dice, bonus}`; all 37 bestiary entries carry `damage:`; 37/37 encounter refs resolve — COMPLIANT.
- **Reference-page anchor stability (slug = name):** all entities are NEW names (no renames) — no inbound-link breakage risk — COMPLIANT.
- **Section D (no-comments):** see adjudication above — world-file comments downgraded to LOW; the one load-bearing-only-in-comment invariant surfaced as an upstream Improvement.

## Devil's Advocate

Assume this content is broken. Where would it bite?

**The silent-loadout-loss trap is the sharpest edge.** A world `inventory.yaml` *replaces* the genre catalog wholesale. Had the author shipped a currency-only world inventory — an easy mistake, since "I'm just adding Mint coins" is the natural mental model — every chargen loadout would vanish with no error, and the failure would surface only mid-playtest when a new character starts naked. I verified this story dodges it (full surface present), but the project's own §D precedent screams that the invariant living only in a comment is a future-author landmine. A confused author *will* eventually step on it; the loader should fail loud. Recorded as upstream Improvement.

**A career GM would smell the kiwhosis problem.** Keith has 40 years at the table and a trained eye for specificity — handing him a Penobscot-named muskrat-folk sited in the Hudson Valley, outside Penobscot land, is exactly the kind of culture-geography seam he'd catch and either bless (uplift naming spreading along contact) or reject. Shipping it silently would be the wrong move; surfacing it as a Question is correct. The content is faithful to the spec, but "faithful to a spec that may itself have slipped" is not the same as "right."

**A mechanics-first player (Sebastien/Jade) would feel the mountain_laurel gap and the Penitent's softness.** One stock is a birthright-gift short of every peer — a min-maxer notices instantly and either avoids it or asks why. And the Penitent's "vow-drawback paid in System Strain" is, at the content layer, *narration* — there is no engine field that forces the charge; it rides the narrator choosing to spend the pool. That is precisely the Illusionism risk SOUL names ("OTEL as an Illusionism detector"). The saving grace, which I verified, is that System Strain is a *real* pool (rules.yaml + `core.system_strain`), so the narrator has something concrete to charge and the GM panel can in principle see the `strain_cost` span fire. But there is no content-level guarantee it *will* fire — AC3 is honestly a narrator-intent AC, and the only machine-checkable half (no new economy field) is satisfied. A stressed playtest where the narrator forgets to bill the vow would expose the gap, and only OTEL would catch it.

**What a malicious/confused author breaks:** renaming any stock/archetype later silently bad-anchors every reference-page link (documented project behavior) — but nothing here renames, so no live breakage. Empty/huge inputs are not in play (declarative data, schema-validated at load). The draft flag is the one guard standing between this asset-incomplete world and the selection menu; if someone flips `draft: false` before portraits/visual_style/cultures/legends land, the world enters selection half-dressed — but that flip is out of this story's scope and the flag is correctly left `true`.

None of these rise to Critical/High. The world loads, resolves, and plays; the sharp edges are an upstream validator gap and two design questions for Keith.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player picks `muwin_folk` at chargen → `char_creation.yaml` stock scene sets `stock_id: muwin_folk` → loader applies the stocks.yaml entry → grants `structure/augmented_muscle` + `hybrid/savage_claws` + `hybrid/thick_hide` (all resolve in the 103-id AWN catalog) + STR+2/DEX-1, AC 13, trauma_target_mod 1. End-to-end traceable; safe because the granted ids are catalog-validated at `StockRegistry` load (load succeeds → all resolve).

**Pattern observed:** world-tier CAST/CATALOG override done correctly — stocks/archetypes/inventory/openings/tropes all world-scoped under `worlds/seaboard_of_saints/`, none leaked to genre root (CONTENT_AUTHORING_CHECKLIST §A/B governing principle). `inventory.yaml:17` full-surface override (currency+item_catalog+starting_equipment+starting_gold) honors the replace-not-merge contract.

**Error handling:** the content fails loud by construction — `_load_single_world` raises `GenreLoadError` on malformed files and runs cross-file opening validators (`loader.py:1300/1304/1318`); preflight's draft-flipped full load passed all of them. The one silent-failure *risk* (partial world inventory) is dodged here and surfaced upstream.

**Subagent dispatch tags:** `[EDGE]` N/A-disabled · `[SILENT]` N/A-disabled · `[TEST]` 8 findings, all non-blocking/dismissed/deferred (Penitent-PC-path dismissed per addendum C5; kiwhosis + mountain_laurel surfaced) · `[DOC]` 3 findings non-blocking (inventory invariant → upstream Improvement; 2 doc nits) · `[TYPE]` N/A-disabled · `[SEC]` N/A-disabled · `[SIMPLE]` N/A-disabled · `[RULE]` 11/12 categories fully compliant, Section-D comments downgraded to LOW per scope adjudication.

**ACs:** all 6 met — roster complete + catalog-resolving (AC1), Indigenous anchors present (AC2, prose/register per AC wording), Penitent loads + System-Strain drawback + no new economy field (AC3), tropes/openings load + valid slugs + load-time validators pass (AC4), bestiary damage specs + 37/37 encounter resolution (AC5), currency + no banned types (AC6).

**Handoff:** To SM (Camina Drummer) for finish-story.