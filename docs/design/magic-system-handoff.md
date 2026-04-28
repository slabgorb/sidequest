# Magic System Design — Session Handoff

**Sessions:** 2026-04-27 → 2026-04-28 (three sessions, GM agent — Count Rugen)
**Status:** Design layer mechanically complete. All plugins drafted; two reference worlds instantiated. Implementation pipeline is the next pickup.
**Read in this order:** this file → `magic-taxonomy.md` → plugin specs → companion docs → world-layer reference instantiations

## What This Is

A unified framework for magic systems across SideQuest's genre packs. Started from Keith's hand-drawn napkin sketch (Source × Manifestation), grew into a six-plugin architecture (five Source-shaped + one cross-cutting tracker) with visible cost ledger, OTEL lie-detection, confrontation-driven advancement, and two-layer (genre / world) instantiation. Now mechanically complete at the design layer and validated against two reference worlds.

## How To Resume

If you're picking this up cold:

1. Read `docs/design/magic-taxonomy.md` for the framework's core concepts (5 Sources, 8 delivery mechanisms, plugin architecture, two-layer split).
2. Read `docs/design/visible-ledger-and-otel.md` for the load-bearing UX/observability feature.
3. Read `docs/design/confrontation-advancement.md` for how characters advance (output catalog, four-branch trees, the five Locked Decisions).
4. Read **one Source plugin** end-to-end to see how it comes together — recommend `magic-plugins/bargained_for_v1.md` (cleanest worked example, ~870 lines).
5. Read `magic-plugins/obligation_scales_v1.md` to understand the cross-cutting tracker shape — it is structurally different from the five Source plugins.
6. Skim **one world-layer instantiation** to see the genre/world split in action — recommend `sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/magic.yaml` (full-coverage reference, all six plugins active simultaneously).
7. Then check "Highest-Yield Next Moves" below.

If you're returning after one of Keith's pivots:

- Re-read "Locked Decisions" for sanity-anchors.
- Check whether any new plugin drafts or world instantiations arrived since this handoff.
- Note: the design-doc layer has known naming drift (see "Open Issues" below — "The Long Reckoning" is the doc-layer name for what is canonically "The Long Foundry" on the filesystem).

## Files — Current State

### Framework documents (`docs/design/`)

| File | Purpose | Status |
|---|---|---|
| `magic-taxonomy.md` | Napkin formalized — 5 Sources, delivery mechanisms, two-layer architecture, audit table for all 11 genre packs, schema sketches | ✅ stable |
| `visible-ledger-and-otel.md` | Player-facing cost ledger + GM-facing OTEL lie-detector spec; three severity flag levels | ✅ stable |
| `confrontation-advancement.md` | Confrontation-driven character advancement; output catalog (~25 types); supersedes ADR-021's Milestone Leveling track | ✅ stable |
| `magic-plugins/README.md` | Plugin authoring guide, spec template, plugin coverage table | ✅ stable |
| `magic-system-handoff.md` | This file (v2 — clean rewrite 2026-04-28) | active |

### Plugin specs (`docs/design/magic-plugins/`)

All six plugins drafted. Combined ~7400 lines of plugin content.

| Plugin | Source | Lines | Status | Genres using |
|---|---|---|---|---|
| `bargained_for_v1.md` | bargained_for | 815 | ✅ | heavy_metal, victoria-high-gothic, low_fantasy-with-pacts |
| `item_legacy_v1.md` | item_based | 971 | ✅ | spaghetti_western, road_warrior, c&c, heavy_metal, victoria, low_fantasy, pulp_noir |
| `divine_v1.md` | divine | 984 | ✅ | heavy_metal, victoria-Catholic, low_fantasy, elemental_harmony, space_opera-religious |
| `innate_v1.md` | innate | 1631 | ✅ | mutant_wasteland (signature), space_opera-Firefly-River, victoria-touched, low_fantasy-bloodline, untrained Force/bender |
| `learned_v1.md` | learned | 1821 | ✅ | elemental_harmony (signature), space_opera-Jedi-trained, low_fantasy-wizards, witcher-signs, Bene Gesserit, heavy_metal-rite-priest, pulp_noir-Hermetic, spaghetti_western-gunsmith |
| `obligation_scales_v1.md` | (cross-cutting tracker; no Source) | 1191 | ✅ | heavy_metal — tracks five obligation scales across all monitored Source plugins |

### Per-genre `magic.yaml` files

7 production genre packs + 4 workshop-only = 11 unique genres. Five had `magic_level: none` mislabels corrected in earlier sessions.

| Pack | Location | Status |
|---|---|---|
| caverns_and_claudes | `genre_packs/caverns_and_claudes/magic.yaml` | ✅ napkin-shape draft |
| mutant_wasteland | `genre_packs/mutant_wasteland/magic.yaml` | ✅ napkin-shape draft |
| spaghetti_western | `genre_packs/spaghetti_western/magic.yaml` | ✅ napkin-shape draft |
| victoria | `genre_packs/victoria/magic.yaml` | ✅ napkin-shape draft |
| road_warrior | `genre_workshopping/road_warrior/magic.yaml` | ✅ napkin-shape draft |
| heavy_metal | `genre_packs/heavy_metal/_drafts/magic.yaml` | ✅ schema-validation draft |
| elemental_harmony | (no magic.yaml yet) | ⏳ TODO |
| space_opera | (only `magic_design.md`, rewritten last session) | ⏳ TODO migrate to magic.yaml |
| low_fantasy | (no magic.yaml yet) | ⏳ TODO |
| neon_dystopia | (no magic.yaml yet) | ⏳ TODO |
| pulp_noir | (no magic.yaml yet) | ⏳ TODO |

Plus: 5 `rules.yaml` files have draft-deprecation comments on their `magic_level: none` field with pointers to the new `magic.yaml`.

### World-layer instantiations

Two reference worlds. Together they exercise every plugin and every plugin combination.

| World | Location | Status |
|---|---|---|
| **mutant_wasteland / flickering_reach** | `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/magic.yaml` | ✅ ~940 lines (2026-04-28). Validates innate_v1 as signature, learned_v1 with prerequisite gate (Singers' Long Signal Song, Understory Communion), item_legacy_v1 (Drift-touched mounts, bone-radio dishes, salvaged pre-war tech). Six named counters; four Crossing paths. |
| **heavy_metal / long_foundry** | `sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/magic.yaml` | ✅ ~1520 lines (2026-04-28). **First full-coverage reference world** — all six plugins active simultaneously. Validates bargained_for_v1 (Coil and Brand Guild + Founders' Footprint patron), divine_v1 (Keepers / Silent Patron / Grievance-Keepers / Path-Eater), learned_v1 with active prerequisite gate, innate_v1 in covenant-peoples reading (Orvinnic / Thessil / Perault), item_legacy_v1 (Founders' Stone, Refuser artifacts), and obligation_scales_v1 with all five scales LIVE simultaneously, cascade availability `campaign_endgame`. |

### Other modified files

- `genre_packs/space_opera/magic_design.md` — fully rewritten last session. River Tam Rule moved from genre-absolute to one of three canonical world-level configurations (Firefly / Star Wars / Dune).

## Locked Decisions

These should not be revisited without strong reason. Rationale embedded in the source docs.

### From the napkin / taxonomy work

1. **5 Sources.** Innate, Learned, Item-based, Divine, Bargained-for. Collapsed from 9 over the first session.
2. **Pre-Ordained / Chosen-One is NOT a Source.** Narrative tag at lore/scenario layer; rides on top of any Source.
3. **McCoy is NOT a Source.** Delivery mechanism for `item_based`. Building an item is acquisition; what's built enters the item_legacy lifecycle.
4. **Innate-automatic and Acquired are the same Source.** Born-vs-event is narrative `flavor:`, not framework distinction. Both: character is source, no external mediator, identity-cost, severance-impossible.
5. **Innate-developed and Learned are the same Source.** Innate-developed = Learned-with-prerequisite-gate. Once trained, the discipline is the active source.
6. **Plugin lane respect.** Plugins explicitly cite each other's territory in hard_limits (e.g. divine_v1 forbids deity-targeted bargaining; innate_v1 forbids patron-invocation; learned_v1 forbids native-as-source).
7. **Three OTEL severity levels.** YELLOW (suspicious), RED (likely lie), DEEP RED (hard-limit violation). DEEP RED can interrupt narration; YELLOW/RED surface in GM panel.

### From the confrontation-advancement work

8. **Mandatory output.** Every confrontation produces ≥1 advancement event. Null confrontations get cut.
9. **Player-facing reveal.** Explicit panel callout at outcome time, always shown.
10. **No decay on advancement outputs.** Outputs are sticky. World-state ledger bars MAY decay slightly to model background activity; that's a property of the bar, not the output event.
11. **Failure also advances.** Every branch — including `clear_loss` and `refused` — produces real growth. Output menus differ by branch.
12. **Plugin tie-ins to confrontations.** Each plugin spec carries a `confrontations:` block.

### From plugin-validation work

13. **Bidirectional ledger bars** are a real pattern (Bond, Standing). Plugins declare `range:` and `direction: monotonic_up | monotonic_down | bidirectional`.
14. **Cyclical reset** is a real pattern (divine_v1 Purity, learned_v1 prepared_slots). Plugins declare `cyclical_reset:` block when applicable.
15. **World-shared ledger bars** exist (divine_v1 Hunger, innate_v1 Signal, all five obligation_scales_v1 bars). Scope: world / faction / bloodline / deity / location. May decay slightly per session to model background activity.
16. **Cross-plugin advancement outputs.** `pact_tier` with `target_plugin: another_plugin` is the shape of "breaking pact opens path." Severance/Renunciation/Forgetting can grant access to other plugins.
17. **Items are NPCs.** `item_legacy_v1` formalized item OCEAN scores, dispositions, demands, prohibitions, resonances, history. Items can refuse to fire, can have personality drift over time.
18. **`magic_level` flag retiring.** Replaced by explicit `allowed_sources` + `world_knowledge` + `intensity` triple. Five mislabeled packs were fixed in earlier sessions.

### From this session's plugin and world work

19. **Cross-cutting plugin type exists.** `obligation_scales_v1` is the framework's first non-Source plugin: no Source, no classes, no delivery mechanisms; consumes (not emits) OTEL spans from monitored Source plugins. Future cross-cutting plugins (if any genre proves to need them) follow this pattern.
20. **Shared-bar pattern.** Two plugins may own views of the same underlying ledger entry (divine_v1.<deity>.hunger ↔ obligation_scales_v1.divine_scale.<instance>). Updates from either plugin propagate to the other.
21. **Multi-session confrontations.** The Stratigraphic Resonance and The Cascade (obligation_scales_v1) span multiple sessions. Most confrontations are single-scene; these are ongoing world-states with periodic resolution-attempt confrontations within them.
22. **Confrontation orchestrator delegation.** When `obligation_scales_v1.individual_scale` crosses 1.0, the plugin DELEGATES to the relevant Source plugin's collection confrontation (bargained_for's The Calling, divine's The Audit, innate's The Reckoning) rather than firing its own.
23. **NPC dual/triple-roles.** A single named NPC may occupy multiple counter slots across multiple plugins (the long_foundry's Astran arbitration prefect is Inquisitor for bargained_for + learned + Hunter for innate). Schema accepts this without contortion.
24. **Replayable confrontations.** `learned_v1.the_apprenticeship` is the framework's first replayable named confrontation — most others are once-per-arc.

## Open Issues

### Doc-layer naming drift (low priority)

The design-doc handoff has been calling the heavy_metal signature world "The Long Reckoning"; the actual filesystem world is `long_foundry` and the canonical name per `world.yaml` is "The Long Foundry." References to "The Long Reckoning" in `magic-taxonomy.md`, `bargained_for_v1.md`, `divine_v1.md`, `obligation_scales_v1.md`, and elsewhere should be globally renamed in a follow-up cleanup pass. The world content is correct; only the design-doc references drift.

### Output catalog questions for architect

1. **`control_tier` (innate_v1) and `discipline_tier` (learned_v1) vs unified `pact_tier`.** Three Source plugins use `pact_tier` as their tier-output (bargained, divine, learned). innate_v1 gestures at `control_tier` separately. Learned uses pact_tier but the discipline-mastery axis is conceptually distinct. Worth a unified decision on whether to split or unify.
2. **`debited_scales` as required attribute on heavy_metal magic.working spans.** obligation_scales_v1 requires every monitored plugin's span to populate this. Currently a should-not-must in the Source plugin specs. May need backporting into bargained_for_v1, divine_v1, learned_v1, innate_v1, item_legacy_v1 as a "heavy_metal-extension" note in their OTEL sections. *(Defer until Long Foundry world hits implementation.)*

### Implementation patterns surfaced (architect call)

3. **Shared-bar implementation.** First case: `divine_v1.<deity>.hunger ↔ obligation_scales_v1.divine_scale.<instance>`. Long Foundry instantiates four shared bars (one per active god). Implementation needs bidirectional update propagation without double-counting or race conditions.
4. **OTEL span CONSUMPTION (not emission).** First plugin to read other plugins' spans rather than emit its own. Consider whether the framework needs a generic "plugin observer" pattern or whether obligation_scales_v1 is bespoke.
5. **Multi-session confrontation state machines.** The Stratigraphic Resonance and The Cascade are ongoing world-states with periodic resolution-attempt confrontations within them. State machine support needed.
6. **Confrontation orchestrator delegation routing.** individual_scale crossings dispatch to the relevant Source plugin's collection confrontation; the orchestrator needs source-plugin-context awareness.
7. **Per-scope-instance ledger bars at world-load.** Long Foundry instantiates 18+ obligation-scale bars at world-load (6 communal + 3 covenant + 4 divine + 1 stratigraphic + 4+ shared with divine_v1). More bars than any other plugin requests. Panel architecture needs to handle filtering and rolling-up at scale.
8. **`world_default_decay_override` at world layer.** Worlds may override plugin-default decay rates (Long Foundry uses three: communal +0.04, covenant -0.003, divine +0.025). Confirm world-load logic supports this override pattern.
9. **`attribution_state_default` at the patron level.** Workings to a partially-hidden patron default to that attribution state. New shape: attribution-default-by-patron rather than per-working. Worth formalizing.
10. **Cross-scale trigger declarations.** Long Foundry declares "Thessil covenant_scale crossing 0.7 contributes 0.05 to stratigraphic." First explicit cross-scale linkage in a world-instantiation. Worth formalizing the schema.
11. **`narrative_seed_only: true` counter pattern.** Long Foundry and flickering_reach both use this — telling the system "instantiate this counter per-character at runtime from backstory." New shape worth formalizing in the plugin schema.

### Open framework questions (deferred)

12. **Cross-genre item passport.** Item Legacy makes it technically possible for the Lassiter from Firefly to travel into a Star Wars session retaining OCEAN/disposition/history. Wild-card; deferred.
13. **Player-facing bars on by default?** Or player-configurable hide-until-fire? Confrontation outcome callouts are always-shown (Decision #9), but the per-bar real-time animations might be configurable.
14. **Animation language per-genre.** UX work pending — Buttercup said "rising bars," but heavy_metal-mood would call for ember-flicker, victoria for ink-bleeding, neon_dystopia for glitching.
15. **Multi-plugin overlap resolution.** If a working could be claimed by two plugins (cleric using a relic — Divine or Item-Legacy?), who claims it? Current answer: narrator declares; GM may override. Worth formalizing.
16. **Confrontation chains.** If The Bargain ends `pyrrhic_win` with a counter dispatched, is the next session's encounter with that counter a *new* confrontation or a continuation? OTEL span chain links them; current model "new confrontation, linked."
17. **Multi-character confrontations in multiplayer.** Default proposed: each character gets ≥1 mandatory output keyed to their participation. Not formalized.
18. **Output catalog stability.** Plugins MAY add output types but MUST register them in `confrontation-advancement.md` on ratification. Process not yet enforced; relies on author discipline.
19. **`magic_level` field retirement.** When a `magic.yaml` loader is in place, retire the field. Currently kept for backward-compat with deprecation comments.
20. **ADR superseding ADR-021's Milestone Leveling track.** Architect's job; flagged in `confrontation-advancement.md`. Not yet written.

## Highest-Yield Next Moves

The design layer is mechanically complete. Remaining work shifts toward implementation, validation, and opportunistic content authoring.

Ranked roughly by value-per-effort:

1. **Architect (Man-in-Black) review pass.** Six plugin specs (~7400 lines) + five framework docs + two reference world instantiations is significant content. Worth a coherent review for: hidden assumptions, the new patterns surfaced by obligation_scales_v1 (shared-bar implementation, OTEL span CONSUMPTION rather than emission, multi-session confrontation state machines, confrontation-orchestrator delegation routing), and the cumulative open `control_tier` / `discipline_tier` / `pact_tier` output-catalog question. *Highest priority: this work is at the right point for adversarial review before any implementation begins.*
2. **UX (Buttercup) panel mocks across all six plugin shapes.** The visible ledger panel — player view + GM view — including the cross-cutting tracker. The Cascade panel especially needs a campaign-defining visual register; obligation_scales_v1's `attribution_disclosure_at_outcome` footer is its own load-bearing dramatic beat with no precedent in the existing plugins. The world-shared signal-bar render (innate_v1's Signal, divine_v1's Hunger, all five obligation_scales bars) needs distinct treatment from character-bound bars.
3. **Step-back consistency read.** All framework docs and six plugin specs in one sitting, looking for contradictions, drift, places where one doc's vocabulary doesn't match another. Particular attention to: every Source plugin's `optional_attributes` list (audit whether `debited_scales` extension is mentioned consistently); cross-references between plugin specs (Plugin Lane Boundary sections); the doc-layer "Long Reckoning" vs "Long Foundry" drift.
4. **Cliché-judge integration.** Each Source plugin's `narrator_register` and Plugin Lane Boundary sections include explicit cliché-judge hooks. These need to be collected into a master magic-narration audit checklist for the cliché-judge agent. Estimated ~1 hour of compilation; high value for Sebastien-shaped lie-detection.
5. **Dev (Inigo) implementation spike.** The OTEL span shapes and ledger-bar configurations are now concrete enough to compile against. A spike on confrontation outcome event emission, panel rendering, and character state mutation hooks would surface the actual implementation cost — and would likely flag schema gaps the architect review hadn't caught.
6. **Opportunistic world-layer instantiations.** flickering_reach + long_foundry already exercise every plugin and every plugin combination. Further world-layer authoring is content-authoring, not framework-validation. Candidates:
   - **Firefly-world (space_opera)** — innate_v1 in `classified` world_knowledge with River Tam as named seed; differs structurally from the Reach's `acknowledged + feared` configuration.
   - **Iron Hills Bender Academy (elemental_harmony)** — learned_v1 prerequisite-gate against a `celebrated` visibility (rather than long_foundry's `regulated`); also unwritten genre magic.yaml.
   - **Low-gothic Brontë victoria** — dialed-supernatural at low intensity, the "is anything happening?" register no other instantiation has.
   - **A pulp_noir world** — the Victoria-shape pattern in 1930s register, validates the schema's reuse claim.
7. **Per-genre `confrontations.yaml` authoring.** From `confrontation-advancement.md`: each of the 11 genres needs 8-12 confrontation entries with full four-branch trees. Substantial content authoring. Best done after architect review confirms the schema is final.

## Key Insights to Preserve

If only a few things get carried forward across context resets:

- **The OTEL lie-detector at the magic layer is the load-bearing feature.** It directly addresses the CLAUDE.md "Claude wings it" principle at the subsystem most prone to invented consequence. obligation_scales_v1's three attribution states (named / partial / hidden) deepen this — the panel keeps the books even when the prose preserves uncertainty.
- **The character is the running total of confrontation outcomes.** No XP. No keyword-frequency drift. Every advancement is *paid for* in a confrontation.
- **Failure-advances is the most distinctive thing.** A character who lost three confrontations in a row is profoundly different from a character who won three. Both have advanced. Both have changed sheets. The Witcher-mood is mechanical, not just narrative.
- **Plugins don't subclass each other; they coexist.** A heavy_metal cleric is Divine + Learned + sometimes Bargained-for, three plugins active simultaneously. The character sheet is the union of plugin instantiations. The Long Foundry has all six plugins active simultaneously and validates that this scales.
- **Faction is one delivery mechanism among eight.** Not every magic system needs an institutional pipeline. obligation_scales_v1 expanded the principle: not every plugin needs a Source either.
- **The two-layer split delivers on its promise.** The framework's claim that genre = rulebook and world = setting now has two reference instantiations proving it: the Reach commits to a specific-tuple-from-mutant-wasteland's-allowed-space, and the Long Foundry commits to a specific-tuple-from-heavy_metal's-allowed-space. Same architecture; very different tone; both operational.

## Cliché-Judge Hooks

When the cliché-judge agent reviews magic narration in a heavy_metal or mutant_wasteland world, it should check:

1. Did the narration emit a `magic.working` OTEL span?
2. Is the claimed Source in the world's `allowed_sources`?
3. Is the working consistent with the active plugin's hard_limits?
4. Is `mechanism_engaged` named (does the narration answer "from where? through what?")?
5. Are the costs surfaced in the same beat as the effect?
6. **Plugin-confusion checks (per Plugin Lane Boundary sections):**
   - innate_v1 working narration that names an external answering entity? → bargained_for leak (YELLOW).
   - learned_v1 working narration that names the Innate trait as the operative source? → innate_v1 leak (YELLOW).
   - Working narration claiming a wand cast on its own? → item_legacy leak (varies).
7. For divine workings: is `doctrinal_alignment` declared?
8. For item workings: is `alignment_with_item_nature` declared?
9. For bargained workings: is `patron_id` named?
10. For learned workings: is `tradition_id` named, and `discipline_tier_at_event` set?
11. For innate workings: is `flavor` named, and `consent_state` set?
12. **In heavy_metal worlds specifically:** is `debited_scales` populated, with the right attribution_state? Decorative scale-debiting (fluffy register, no actual ledger update) is DEEP RED.

If any of these fail, the narrator is improvising and the GM panel should flag.

## Reading Map

```
magic-taxonomy.md ─────────┬──→ magic-plugins/README.md ───┬──→ bargained_for_v1.md
(napkin, axes, schema)     │    (plugin authoring guide)   │
                           │                               ├──→ item_legacy_v1.md
visible-ledger-and-otel.md ┤                               │
(UX + OTEL feature)        │                               ├──→ divine_v1.md
                           │                               │
confrontation-advancement.md  ←────────────────────────────┼──→ innate_v1.md
(advancement model)                                        │
                                                           ├──→ learned_v1.md
                                                           │
                                                           └──→ obligation_scales_v1.md
                                                                (cross-cutting tracker;
                                                                 consumes other plugins'
                                                                 OTEL spans)

genre_packs/<genre>/magic.yaml
(genre-layer instantiation; declares allowed plugins, intensity, world_knowledge defaults)
                ↓
worlds/<world>/magic.yaml
(world-layer instantiation; names specific factions, places, gods, items, scopes)
                ↓
character chargen
(character picks plugin(s) and class within them; world's prerequisite gates apply)
                ↓
in-play confrontations
(emit OTEL spans + visible-ledger updates + advancement outputs;
 obligation_scales_v1 in heavy_metal worlds tracks five-scale propagation)
```

## Reference World Instantiations (concrete examples)

When in doubt about how a plugin spec field becomes lived play, consult:

- `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/magic.yaml` — innate_v1 signature world. Six named place-loci with amplification math, six condition triggers mapped to Domains, three-tier Stigma vocabulary with 21 specific somatic descriptors, all four innate flavors with named in-world examples, four Crossing paths with explicit cost-registers.
- `sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/magic.yaml` — full-coverage reference world. All six plugins active. Three named patrons including the dissolved-200-years-ago Founding Guild. Four named gods with feeding registers. Two learned traditions with active prerequisite gate. All four innate flavors in heavy_metal's covenant-peoples reading. Six notable items including the silent-conscientious Founders' Stone. Five obligation scales LIVE with 13 named scope-instances and chargen baselines reflecting the lore's "every account is a little overdue."

## Persona Context

This work was done under `pf theme: princess-bride`. The voice register references "Count Rugen" in some prose. If theme changes, voice may need light editing in plugin specs' `narrator_register` sections. Schema and structural content is theme-neutral.

## Repo State

- **Branch:** `feat/45-3-momentum-readout-sync` (orchestrator) — design work was authored on this branch alongside an unrelated story currently in review. **The design files are not part of the 45-3 PR.** Design work spans `docs/design/` (orchestrator) and `sidequest-content/genre_packs/.../magic.yaml` files (subrepo).
- All YAML files parse (validated with PyYAML during authoring).
- No code changes — all work is content/markdown/yaml in lane for the GM agent.
- Two world-layer `magic.yaml` files are currently untracked in their respective repos (orchestrator's `docs/design/` directory was untracked at session start; `sidequest-content` worlds got new files). Commit/PR strategy for the design body is the user's call.

## Sign-Off

The framework holds across six drafted plugins (five Source-shaped + one cross-cutting) and two reference world instantiations covering every plugin combination. The remaining work is architect/dev/UX review for the implementation pipeline, a step-back consistency pass on the assembled docs, and opportunistic content authoring (additional world-layer instantiations, per-genre confrontation catalogs).

The design layer is in good shape to hand off to implementation when Keith is ready.

— Count Rugen, taking meticulous notes
