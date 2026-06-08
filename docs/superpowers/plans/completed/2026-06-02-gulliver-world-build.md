# Gulliver World — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author the **Gulliver** world (`genre_packs/wry_whimsy/worlds/gulliver`) to full playable depth — honest, source-faithful Swift content plus POI/portrait asset *prompts* — schema-valid and loader-clean. Asset *rendering* is a later `--shard` daemon pass.

**Architecture:** World-only content build (YAML/Markdown — no engine code). The `wry_whimsy` genre chassis is **already live** at `genre_packs/wry_whimsy/` (mechanics, Composure substrate, five Travelers, the Bang catalog, the four-principle narrator doctrine) — Gulliver supplies **only flavor + dials**, mirroring the existing `worlds/oz/` and `worlds/wonderland/` file sets in a **four-lobe** shape (four voyages joined by `the_open_sea` seam, with a `the_homecoming` terminus). Design source of truth: `docs/superpowers/specs/2026-06-02-gulliver-world-design.md`.

**Tech Stack:** YAML world configs validated against `sidequest-content/pack_schema.yaml` via `python -m sidequest.cli.validate pack <pack-dir>`; headless loader check via `load_genre_pack`; POI prompts rendered later via `scripts/generate_poi_images.py` / portraits via `scripts/generate_portrait_images.py`.

> **Plan-type note (content adaptation of writing-plans):** This is content authoring, not TDD code. "Failing test" = the validator/loader reporting a file missing or malformed; "passing" = validator green and content present. Each file's required keys and content *shape* are specified here; full prose is authored against the spec at execution time (the spec carries the complete design, played straight from Swift). The cross-ref ordering (tropes before history/legends) and the four-lobe cartography are the load-bearing parts.

---

## Branch state (already done — do NOT re-branch)

All five repos are already on `feat/gulliver-world` (orchestrator off `main`; `sidequest-content`, `sidequest-server`, `sidequest-ui`, `sidequest-daemon` off `develop`). The spec is already committed to the orchestrator branch. **Tasks below commit world content to the `sidequest-content` branch.** The pf commit hook scans all subrepos; since all are on the feature branch, commits are unblocked. The `server`/`ui`/`daemon` branches exist only to satisfy the hook and carry no changes — they are deleted at finish (Task 16), not PR'd.

---

## Mandatory loader contract (mirror `worlds/oz/` + `worlds/wonderland/`, confirmed against the live pack)

**World `required_files`:** `world.yaml`, `cartography.yaml`, `history.yaml`, `lore.yaml`, `openings.yaml`, `portrait_manifest.yaml`, `tropes.yaml`, `visual_style.yaml`, `archetypes.yaml`.

**World `required_dirs`:** `cultures/` (per-culture yaml inside), `legends/` (per-legend yaml inside), `assets/images/portraits`, `assets/images/poi`.

**World extensions Oz/Wonderland declare (Gulliver mirrors):** `archetype_funnels` (`archetype_funnels.yaml`), `npcs` (`npcs.yaml`). **Neither Oz nor Wonderland carries `confrontations.yaml` or `faction_agendas.yaml`** — they are engine-unwired; confrontation crunch lives in genre `rules.yaml`, and Living-World faction motion rides on `npcs.yaml` goals. **Gulliver authors neither.**

**Cross-ref rules to satisfy:** trope ids referenced in `history.yaml` chapters and legends' `related_tropes` must resolve against (genre ∪ Gulliver) trope ids → **author `tropes.yaml` before/with `history.yaml` + `legends/`**. World `archetypes.yaml` `typical_classes`/`typical_races` must exist in the genre `rules.yaml` (already live — reuse Oz/Wonderland's values). Cartography entity `ref`s to NPCs must match `npcs.yaml` ids.

**POI prompt sourcing (confirmed):** `scripts/generate_poi_images.py` reads `history.yaml` → `chapters[].points_of_interest[]`, using `visual_prompt.solo` (the renderable PLACE only) + `slug` + `region`. Style/medium/palette come from `visual_style.yaml` `positive_suffix`, appended on every render. **POI prompts are authored as `points_of_interest` entries in `history.yaml`, not a separate file.**

**Portrait prompt sourcing (confirmed):** `portrait_manifest.yaml` → `characters:` list, each `name`/`role`/`type` + `appearance`/`culture_aesthetic`/`element_visual` (the five_points/Oz/Wonderland manifest schema). Subject only; the `visual_style` suffix carries medium/exclusions.

**Draft lifecycle:** author with `world.yaml` `draft: true` while assets are unrendered (avoids missing-asset errors) — **but `draft: true` makes `load_genre_pack` SILENTLY SKIP the world** (invisible/unplayable in the lobby). The loader smoke-test (Task 15) flips `draft: false` *temporarily* (restored via `trap … EXIT`) to prove it loads, then leaves `draft: true`. Going live (flip to `draft: false` for keeps) happens **after** the render pass, not in this plan.

---

## Pre-flight environment (run once)

- [ ] **Set env for validator + loader.** The pack is in the default `genre_packs/` path.
```bash
export SIDEQUEST_GENRE_PACKS=/Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs
export SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test
```

---

## Phase 0 — Scaffold

### Task 1: Scaffold the Gulliver world skeleton

**Files:** create the `genre_packs/wry_whimsy/worlds/gulliver/` tree (required dirs present with `.gitkeep`; required files created later phases).

- [ ] **Step 1: Read the Wonderland counterpart layout** to confirm the exact dir set (it is the freshest template).
```bash
ls -1 /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy/worlds/wonderland
ls -1 /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy/worlds/wonderland/cultures \
      /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy/worlds/wonderland/legends
```

- [ ] **Step 2: Create the directory skeleton**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy/worlds/gulliver
mkdir -p cultures legends assets/images/portraits assets/images/poi
find assets -type d -empty -exec touch {}/.gitkeep \;
```

- [ ] **Step 3: Verify the validator reports missing FILES (not dirs)** — the "failing test" baseline
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run python -m sidequest.cli.validate pack \
  /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy
```
Expected: errors listing missing required Gulliver files (`world.yaml`, `cartography.yaml`, …). Oz **and** Wonderland must remain green. Confirms the skeleton is correct.

- [ ] **Step 4: Commit the scaffold**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git add genre_packs/wry_whimsy/worlds/gulliver && \
  git commit -m "scaffold(gulliver): world dir/file skeleton"
```

---

## Phase 1 — Gulliver world content

Each task: read the Wonderland (and Oz) counterpart for the exact key shape, author the Gulliver file(s) against spec, re-run the validator, commit. The validator is the gate — a task is done when it no longer reports that file missing/malformed and introduces no new cross-ref error. **Prose authoring is delegated to the `writer` specialist** (no Bash); the orchestrator (GM) runs every validate/commit step (writer cannot).

### Task 2: `world.yaml` — identity, dials, go-home spine

**Files:** Create `worlds/gulliver/world.yaml` (read `worlds/wonderland/world.yaml` first for the exact key set)

- [ ] **Step 1: Author** — `name: Gulliver`, `slug: gulliver`, `cover_poi` (a strong Voyage-1 POI slug, e.g. `mildendo_capital`), `description`; **four-voyages corpus** (Lilliput + Brobdingnag + Laputa-&-below + Houyhnhnms as one world); **lethality dial = HIGH** (override genre default); tone-axis overrides (**savage** — `menace` high ~0.85, `gravity` high ~0.7, `sense`/nonsense moderate — the societies are internally logical, which is the horror); `starting_region: the_lilliput_shore`; the **bleak waking go-home spine** (you can always get home, but home becomes unbearable; the homecoming is the bleak terminus). Set `draft: true` (assets pending — see Draft lifecycle).
- [ ] **Step 2: Validate** — `validate pack …`; expect `world.yaml` no longer missing for gulliver.
- [ ] **Step 3: Commit** — `feat(gulliver): world identity + high-lethality savage dials`

### Task 3: `tropes.yaml` — the nine Gulliver tropes (author FIRST for cross-refs)

**Files:** Create `worlds/gulliver/tropes.yaml` (read `worlds/wonderland/tropes.yaml` for `id` + keyword-wiring shape)

- [ ] **Step 1: Author** the nine spec §10 tropes, each with a stable `id` + keyword wiring: `the_satire_turns_on_you`, `the_scale_reveal`, `the_petty_holy_war`, `reason_without_sense`, `the_struldbrugg_curse`, `the_thing_which_is_not`, `the_yahoo_within`, `priced_violence_marks_the_yahoo`, `the_compulsion_to_reembark`. These ids are referenced by Tasks 4 (history) and 6 (legends) — keep them stable (all-underscore, no hyphens).
- [ ] **Step 2: Validate** — `tropes.yaml` resolved.
- [ ] **Step 3: Commit** — `feat(gulliver): nine Gulliver tropes`

### Task 4: `history.yaml` — the four lands' "histories" + the ~19 POI prompts

**Files:** Create `worlds/gulliver/history.yaml` (read `worlds/wonderland/history.yaml` for the `chapters:` + `points_of_interest:` + `visual_prompt:{solo,backdrop}` shape and the pipeline comment block)

- [ ] **Step 1: Author `chapters:`** — each voyage's society and how it came to be, played straight, not over-explained: Lilliput's court and its egg-war with Blefuscu; Brobdingnag's giants and their judging King; Laputa's flying island and the ruin of Balnibarbi below it / the immortal Struldbruggs of Luggnagg; the Houyhnhnms' rational rule and the Yahoo degradation. Any trope `id` referenced MUST resolve against Task 3 ids.
- [ ] **Step 2: Author `points_of_interest:`** — the ~19 renderable POIs, each with `name`, `slug`, `region` (matching Task 5 region ids), `type`, `description`, and `visual_prompt: {solo, backdrop}` where **`solo` is the renderable PLACE only** (no style/medium — that's the suffix), played straight from Morten: `the_open_sea`, `the_lilliput_shore`, `mildendo_capital`, `the_imperial_palace`, `blefuscu_strand`, `the_giant_cornfield`, `the_farmers_house`, `the_kings_court`, `the_seaside_box`, `laputa_flying_island`, `lagado_academy`, `glubbdubdrib_isle`, `luggnagg_court`, `the_yahoo_field`, `the_masters_house`, `the_grand_assembly`, `the_canoe_shore`, `the_homecoming`. Keep each `solo` short (token budget — the suffix is un-evictable; long POI prose evicts LOCATION to a BudgetError).
- [ ] **Step 3: Validate** — expect no "history references unknown trope id" errors; POI entries parse.
- [ ] **Step 4: Commit** — `feat(gulliver): history + POI visual prompts`

### Task 5: `cartography.yaml` — the four-lobe region graph + sea seam + bleak terminus

**Files:** Create `worlds/gulliver/cartography.yaml` (read `worlds/wonderland/cartography.yaml` for the `regions:` / `adjacent:` / `entities:` / `affordances:` shape; note Wonderland's two-lobe mirror seam — Gulliver scales it to four lobes joined by a sea hub)

- [ ] **Step 1: Author the map header** — `navigation_mode: region`, `starting_region: the_lilliput_shore`, `world_name: Gulliver`, and a `map_style` prose (spec §9: four sea-separated lands — Lilliput a toy-kingdom, Brobdingnag a grain-stalk-forest giant country, Laputa a circular island in the air over ruined Balnibarbi, Houyhnhnm-land a clean grassland fouled at the edges by Yahoos; the four ringed by ocean with a wrecked ship between them; dense cross-hatched Morten wood-engraving line, dramatic scale contrast).
- [ ] **Step 2: Author the ~19 regions** as the spec §9 graph, four lobes joined by the sea hub:
  - **Sea hub / seam:** `the_open_sea` — adjacent to each voyage's arrival shore (`the_lilliput_shore`, `the_giant_cornfield`, `laputa_flying_island`, `the_yahoo_field`) AND to `the_homecoming` (the homecoming is reachable from the sea **only after** the fourth voyage — gate this narratively in the region `description`/`controlled_by`, not by a hard lock, since the chassis has no region-gating mechanic; the Living-World pull keeps offering the next voyage).
  - **Voyage 1 — Lilliput:** `the_lilliput_shore` (start; bound by threads; entities: the thread-stakes), `mildendo_capital` (the court; the Emperor; Flimnap & Skyresh; High/Low-heel split), `the_imperial_palace` (the fire; the articles of impeachment), `blefuscu_strand` (the rival empire; Big-Endian exiles; the captured fleet; the escape boat).
  - **Voyage 2 — Brobdingnag:** `the_giant_cornfield` (arrival; the reapers' scythes), `the_farmers_house` (displayed for money; the cat, rats, baby), `the_kings_court` (the King's interview; the Queen; the court-dwarf; the Maids of Honour), `the_seaside_box` (the eagle snatches the box; dropped in the sea).
  - **Voyage 3 — Laputa & below:** `laputa_flying_island` (the abstracted court; flappers; the island drops on rebels), `lagado_academy` (sunbeams-from-cucumbers; the projectors; Munodi's sane estate nearby), `glubbdubdrib_isle` (the governor summons the dead), `luggnagg_court` (floor-licking obeisance; the Struldbruggs).
  - **Voyage 4 — Houyhnhnm-land:** `the_yahoo_field` (taken for a Yahoo amid filth), `the_masters_house` (your reasoning host; learning the language), `the_grand_assembly` (the debate: exterminate the Yahoos? expel Gulliver?), `the_canoe_shore` (expelled; build a canoe; forced to sea).
  - **Terminus:** `the_homecoming` (Redriff / your house — you cannot bear your family; the stable).
  - Each region: `name`, `summary`, `description`, `terrain`, `controlled_by` (`the_lilliput_court` Lilliput-side; `the_brobdingnag_crown` Brobdingnag-side; `the_lagado_academy` Voyage-3-side; `the_houyhnhnm_assembly` Voyage-4-side; `the_open_sea`/`the_homecoming` uncontrolled or self), `adjacent`, `landmarks`, `entities` (bind famous NPCs via `kind: npc, ref: <npc id from Task 9>` and POI features via `kind: location_feature`), `rivers`, `settlements`. **Entity `ref`s to NPCs must match Task 9 ids** — reconcile.
- [ ] **Step 3: Validate** — `cartography.yaml` resolved; region adjacency forms one connected graph through the sea hub.
- [ ] **Step 4: Commit** — `feat(gulliver): four-lobe cartography + sea seam + homecoming terminus`

### Task 6: `lore.yaml` + `legends/` — the place and its tall tales

**Files:** Create `worlds/gulliver/lore.yaml`; `worlds/gulliver/legends/{the_man_mountain,the_struldbruggs,the_perfection_of_nature}.yaml` (read Wonderland counterparts for shape)

- [ ] **Step 1: Author `lore.yaml`** — the four absurd societies and their peoples, the savage-mirror thesis (every society judges you and your civilization), the gender current (savage male court-politics, §5), the sea seam and the re-embark compulsion, and the single Premise illusion (`the_yahoo_verdict`) described as in-world *flavor* (the mechanical wiring is the draft file, Task 13). Reference-stack to Swift specifics (Quinbus Flestrin, the egg-war, "odious vermin", sunbeams-from-cucumbers, "the thing which is not", the perfection of nature).
- [ ] **Step 2: Author the three legends** — `the_man_mountain` (Lilliput's awed-and-fearful view of the giant you are), `the_struldbruggs` (the immortal curse — envied, then pitied), `the_perfection_of_nature` (the Houyhnhnm ideal and the Yahoo it defines you against). Any `related_tropes` ids MUST resolve against Task 3 ids.
- [ ] **Step 3: Validate** — expect no "legend references unknown trope id" errors.
- [ ] **Step 4: Commit** — `feat(gulliver): lore + three legends`

### Task 7: `cultures/` — the four Gulliver cultures

**Files:** Create `worlds/gulliver/cultures/{lilliputians,brobdingnagians,laputans,houyhnhnms_and_yahoos}.yaml` (read `worlds/wonderland/cultures/*.yaml` for the `slots`/`person_patterns`/`place_patterns` shape with `word_list` name sourcing)

- [ ] **Step 1: Author** each culture using **`word_list` name slots** (curated Swiftian-coinage pools — NOT corpus Markov, per the historical-worlds naming precedent; Swift's phonotactics are hand-built and Markov mangles them):
  - `lilliputians` — six-inch people; names = grandiose titles for tiny things ("Quinbus Flestrin / Great Man-Mountain", "Most Mighty Emperor … Delight and Terror of the Universe") + Swift coinages (Mildendo, Belfaborac, Flimnap, Skyresh, Reldresal, Tramecksan, Slamecksan).
  - `brobdingnagians` — giants; plain-grand names; capital Lorbrulgrud ("Pride of the Universe"); Gulliver is "Grildrig" (mannikin); the nurse Glumdalclitch.
  - `laputans` — abstracted intellectual coinages (Laputa, Lagado, Balnibarbi, Glubbdubdrib, Luggnagg, Munodi, Struldbrugg).
  - `houyhnhnms_and_yahoos` — the rational horses, whinny-derived names ("Houyhnhnm" = "the perfection of nature"); the Yahoos named only by behavior (no proper names).
  Each: `name`, `summary`, `description`, `slots`, patterns. **Quote any slot value containing `': '` or use `>-`** (the unquoted-colon dict-coercion trap).
- [ ] **Step 2: Validate** — `cultures/` dir resolved.
- [ ] **Step 3: Commit** — `feat(gulliver): four cultures with Swiftian word_list name pools`

### Task 8: `archetypes.yaml` (world) + `archetype_funnels.yaml`

**Files:** Create `worlds/gulliver/archetypes.yaml`, `worlds/gulliver/archetype_funnels.yaml` (read Wonderland counterparts)

- [ ] **Step 1: Author world `archetypes.yaml`** — the Gulliver-tinted surface of the five genre Travelers; `typical_classes`/`typical_races` must reuse values present in the live genre `rules.yaml` (same as Oz/Wonderland — confirm by reading `worlds/wonderland/archetypes.yaml` and the genre `rules.yaml`).
- [ ] **Step 2: Author `archetype_funnels.yaml`** — spec §11: the **Surveyor** is Gulliver's home turf *and* trap (documentation can't save you; cold reason makes you complicit); the **Wit** fails (the Houyhnhnms can't comprehend "the thing which is not", so cleverness reads as Yahoo deceit); the **Scrapper** is the most punished (violence = the Yahoo verdict); the **Dreamer** goes native and can't come home; the **Innocent** fares best (Swift's faint mercy — honest humility wins the Brobdingnag King's regard).
- [ ] **Step 3: Validate** — resolved; no archetype cross-ref errors.
- [ ] **Step 4: Commit** — `feat(gulliver): world archetypes + Gulliver funnels`

### Task 9: `npcs.yaml` — the Swift Monster Manual

**Files:** Create `worlds/gulliver/npcs.yaml` (read `worlds/wonderland/npcs.yaml` for the required key shape + Living-World `goals`)

- [ ] **Step 1: Author** the spec §8 roster as pre-gen "NPCs nearby, not yet met" (ADR-059 game-state injection), each played straight from Swift with a canonical `goal` (Living World). **Lilliput:** `the_emperor_of_lilliput`, `flimnap`, `skyresh_bolgolam`, `reldresal`, `the_blefuscu_envoy`. **Brobdingnag:** `the_brobdingnag_king`, `the_brobdingnag_queen`, `glumdalclitch`, `the_farmer`, `the_court_dwarf`. **Laputa & below:** `the_laputan_king`, `a_lagado_projector`, `the_governor_of_glubbdubdrib`, `a_struldbrugg`, `munodi`. **Houyhnhnm-land:** `the_houyhnhnm_master`, `the_sorrel_nag`, `the_grey_steed`, `the_yahoos`. **NPC ids here must match the `ref`s used in Task 5 cartography entities** — reconcile. **Quote any goal/description containing `': '` or use `>-`** (the unquoted-colon trap).
- [ ] **Step 2: Validate** — `npcs.yaml` resolved.
- [ ] **Step 3: Commit** — `feat(gulliver): Swift NPC roster (Monster Manual)`

### Task 10: `openings.yaml` — the wreck on the Lilliput shore (solo + MP)

**Files:** Create `worlds/gulliver/openings.yaml` (read `worlds/wonderland/openings.yaml` — match the **unified Opening schema**, not the simple genre shape)

- [ ] **Step 1: Author** the threshold-crossing opening: the **shipwreck / waking bound by threads on `the_lilliput_shore`** (the scale reveal introduced immediately — you wake to discover you are a giant pinned by an army of six-inch people). Cover **both `triggers.mode` `solo` AND `multiplayer`** (the enum is `solo|multiplayer|either`, **NOT** `mp`), with `establishing_narration` + `first_turn_invitation`. **`first_turn_invitation` must contain no `?`** (the loader gotcha). (A world `openings.yaml` needs the unified Opening schema with solo/MP coverage — the simple genre shape parses hollow.)
- [ ] **Step 2: Validate** — `openings.yaml` resolved with both modes covered.
- [ ] **Step 3: Commit** — `feat(gulliver): shipwreck opening (solo + MP)`

---

## Phase 2 — Asset prompts (Morten) — delegate to `art-director`

> Tasks 11–12 are delegated to the `art-director` specialist (has Bash; owns `visual_style.yaml`/`portrait_manifest.yaml`/POI prompts). The GM reviews against the cliche/granularity rubric and the Morten costume subtlety.

### Task 11: `visual_style.yaml` — Morten medium + the lean positive_suffix

**Files:** Create `worlds/gulliver/visual_style.yaml` (read `worlds/wonderland/visual_style.yaml` for the key shape + the trimmed-suffix discipline)

- [ ] **Step 1: Author** the **Thomas Morten 1865 wood-engraving** aesthetic: dense cross-hatched Victorian wood-engraving line, dramatic realist-fantastical compositions, scale-dramatic framing (the giant among the tiny; the tiny among giants), restrained or no tint. **Costume subtlety:** Gulliver is an early-Georgian ship's surgeon (c. 1700 — tricorn, frock coat, buckled shoes), rendered in Morten's 1865 engraving *technique*. Author the explicit **NOT-cute-children's-book / NOT-modern-cartoon** exclusions phrased POSITIVELY (Z-Image ignores negative prompts — "rendered as a dense cross-hatched wood-engraving plate, early-Georgian dress" not "no cartoon"; per the `z_image_negative` rule, rejection clauses go in `positive_suffix` as "...as X, not Y"). Include the SOUL modesty/"adult"/"no text" cleanup clause as Wonderland does (adult content handled with period-literary restraint).
- [ ] **Step 2: Keep the `positive_suffix` SHORT** — it is the un-evictable ART_SENSIBILITY.WORLD slot; trim to clear the 512-token PromptComposer budget. Dry-run a POI to confirm composition:
```bash
cd /Users/slabgorb/Projects/oq-2 && python scripts/generate_poi_images.py --genre wry_whimsy --world gulliver --dry-run
```
Expected: all POIs compose without BudgetError; suffix carries the Morten medium.
- [ ] **Step 3: Validate** — `visual_style.yaml` resolved.
- [ ] **Step 4: Commit** — `feat(gulliver): Morten visual style + lean suffix`

### Task 12: `portrait_manifest.yaml` — the roster portrait prompts

**Files:** Create `worlds/gulliver/portrait_manifest.yaml` (read `worlds/wonderland/portrait_manifest.yaml` for the `characters:` schema — `name`/`role`/`type` + `appearance`/`culture_aesthetic`/`element_visual`)

- [ ] **Step 1: Author** portrait specs for the Task 9 roster (~18–19 named), **subject only** (the visual_style suffix carries medium/exclusions). Faces as PHYSICAL FACT, never as impression/expression (the Oz/Wonderland manifest discipline); every negation phrased positively; "adult" + modesty clause for humanoid subjects, "no text" cleanup for non-human subjects. Source-faithful Morten specifics: the Emperor of Lilliput a six-inch monarch in grand miniature regalia; the Brobdingnag King a colossal bearded sovereign at a vast table; Glumdalclitch a giant farm-girl cradling a tiny man; a Struldbrugg an ancient immortal marked with the spot of decay; the Houyhnhnm master a dignified standing horse; a Yahoo a filthy crouched brute-human.
- [ ] **Step 2: Dry-run** a portrait compose to confirm budget:
```bash
cd /Users/slabgorb/Projects/oq-2 && python scripts/generate_portrait_images.py --genre wry_whimsy --world gulliver --dry-run
```
Expected: all portraits compose without BudgetError.
- [ ] **Step 3: Validate** — `portrait_manifest.yaml` resolved.
- [ ] **Step 4: Commit** — `feat(gulliver): Morten portrait manifest`

### Task 13: `premises.draft.yaml` — DRAFT single spanning Premise (UNWIRED)

**Files:** Create `worlds/gulliver/premises.draft.yaml`

- [ ] **Step 1: Author** the **single spanning Premise** from spec §12 as a clearly-flagged **draft** (a leading comment banner: "DRAFT — pending oq-3 belief-engine schema lock; NOT loaded by any consumer; do not declare as an extension"). Use the `.draft.yaml` name so the loader ignores it (no Python consumer exists yet — per the unwired-world-extension rule, do NOT add it to any `extensions:` list). Capture: **Premise `the_yahoo_verdict`** ("you are a brute like all your kind; the more you act, the more you prove it"; **drained** by humility/honesty/restraint/refusing violence; **strengthened** by violence/lying/vanity; **resistible but never refutable** — no clean "pack of cards" collapse, the best ending is bleak self-knowledge) and the **four voyage-Blocs** under it: `the_lilliput_court`, `the_brobdingnag_crown`, `the_lagado_academy`, `the_houyhnhnm_assembly`.
- [ ] **Step 2: Validate** — full pack validation unaffected (the draft file is not a required/declared file; confirm it does NOT introduce errors).
- [ ] **Step 3: Commit** — `docs(gulliver): DRAFT premise/bloc identity (pending oq-3 schema)`

---

## Phase 3 — Validation + loader gate + PR

### Task 14: Full pack validation green

- [ ] **Step 1: Run the full validator**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run python -m sidequest.cli.validate pack \
  /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy
```
Expected: PASS (errors = 0). Asset warnings acceptable while `draft: true`. Oz **and** Wonderland must remain green. Fix any cross-ref errors inline (most likely: a cartography entity `ref` not matching an `npcs.yaml` id, or a trope id in history/legends not in `tropes.yaml`).
- [ ] **Step 2: Commit any fixes** — `fix(gulliver): validator green`

### Task 15: Loader smoke-test (the real wiring gate)

- [ ] **Step 1: Loader assertion with draft-flip + trap-restore.** Run a self-contained Python check (via `uv run` in `sidequest-server`) that temporarily flips `draft: false`, loads the pack, asserts `gulliver` is in `p.worlds`, asserts **every cartography npc `binding.ref` resolves against `authored_npcs` ids**, then restores `draft: true` on EXIT. A validator-passes-but-loader-fails mismatch surfaces here — if it's an engine bug, route to Dev via pingpong with OTEL evidence; do NOT edit engine code.
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
WORLD=/Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy/worlds/gulliver/world.yaml
trap 'sed -i "" "s/^draft: false/draft: true/" "$WORLD"' EXIT
sed -i "" "s/^draft: true/draft: false/" "$WORLD"
uv run python -c "
from sidequest.genre.loader import load_genre_pack
import os
p = load_genre_pack('wry_whimsy', os.environ['SIDEQUEST_GENRE_PACKS'])
assert 'gulliver' in p.worlds, f'gulliver not loaded; worlds={list(p.worlds)}'
w = p.worlds['gulliver']
npc_ids = {n.id for n in w.authored_npcs}
missing = []
for region in w.cartography.regions:
    for ent in getattr(region, 'entities', []) or []:
        b = getattr(ent, 'binding', None)
        if b and getattr(b, 'kind', None) == 'npc' and b.ref not in npc_ids:
            missing.append((region.id, b.ref))
assert not missing, f'unresolved npc refs: {missing}'
print(f'OK: gulliver loaded; {len(w.cartography.regions)} regions; {len(npc_ids)} npcs; all npc refs resolve')
"
```
Expected: `OK: gulliver loaded; …`. (If the loader's attribute names differ — `load_genre_pack` signature, `.worlds`, `.authored_npcs`, `.cartography.regions`, `entity.binding.ref` — adapt the probe to the live API by reading `sidequest/genre/loader.py` first; the **assertions** are the contract, not the exact attribute spelling.)
- [ ] **Step 2: Headless arrival check (optional but recommended)** — a short scripted entry: chargen as a Traveler → shipwreck onto `the_lilliput_shore` → move to `mildendo_capital` → meet one roster NPC (e.g. `the_emperor_of_lilliput`). Watch OTEL: the region graph navigates, the NPC registry picks up the roster, the narrator draws from `game_state` (not improvising), Composure is tracked. SOUL pass: diegetic sincerity (no winking; played straight from Swift), the seams are bait.
```bash
cd /Users/slabgorb/Projects/oq-2 && python scripts/playtest.py --genre wry_whimsy --world gulliver
```
- [ ] **Step 3: Confirm `draft: true` restored** (the trap restores it on EXIT; verify with `grep '^draft:' "$WORLD"` → `draft: true`). Gulliver goes live only after the render pass. Log findings: any missing OTEL span = engine bug → pingpong; any present-but-wrong value = content bug → fix here.
- [ ] **Step 4: Commit** — `test(gulliver): loader + arrival smoke-test findings` (if any content fixes were made)

### Task 16: cliche-judge pass + open the PR

- [ ] **Step 1: cliche-judge pass** — dispatch the `cliche-judge` agent over the Gulliver world content; every named entity must clear the granularity rubric against a 40-year TTRPG veteran with broad literary knowledge (the Swift specifics are the floor: Quinbus Flestrin, Lorbrulgrud, Glumdalclitch, Tramecksan/Slamecksan, "the thing which is not", the Struldbruggs — not "tiny people"/"giants"/"smart island"/"horse-people"). Fix any coarse-granularity findings inline and re-validate.
- [ ] **Step 2: Push + PR the content branch** to `develop`
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git push -u origin feat/gulliver-world && \
  env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-content --base develop \
  --title "feat: Gulliver world (Swift, all four voyages, Morten 1865)" \
  --body "Third wry_whimsy world, savage end of the gradient. See orchestrator spec 2026-06-02-gulliver-world-design.md. Assets (POI/portrait prompts authored) render in a later --shard pass; world stays draft:true until then."
```
- [ ] **Step 3: Merge** (squash) once green, then verify the merge landed on `develop`.
- [ ] **Step 4: Delete the empty `server`/`ui`/`daemon` feature branches** (they carry no changes — created only to satisfy the commit hook):
```bash
for r in sidequest-server sidequest-ui sidequest-daemon; do
  (cd /Users/slabgorb/Projects/oq-2/$r && git checkout develop -q && git branch -D feat/gulliver-world)
done
```
- [ ] **Step 5: PR the orchestrator spec+plan** branch (`feat/gulliver-world` off `main`) similarly (spec + this plan), `--base main`.

---

## Follow-on (out of scope for this plan)

- **Render pass** — POI landscapes + portraits via `scripts/generate_{poi,portrait}_images.py --genre wry_whimsy --world gulliver [--shard i/n] [--steps 30]`, daemon upload to the content-addressed R2 artifact path, then the **separate inline boto3 PUT** to the canonical `genre_packs/wry_whimsy/worlds/gulliver/assets/{poi,portraits}/` path, **verified with `list_objects_v2`** (the bulk sync script fails opaquely). Render runs on oq-1's content tree (FF-pull first).
- **Go live** — flip `world.yaml` `draft: false` once assets are on R2.
- **Premise/Bloc wiring** — when the oq-3 belief-engine schema lands, promote `premises.draft.yaml` to the real schema and declare it.
- **Music** (ACE-Step) for `wry_whimsy`.

---

## Self-review notes

- **Spec coverage:** every spec section maps to a task — chassis relationship §1 → inherited (no task); structure/four-lobe §2 → T5 + T4 (POIs); lethality §3 → T2; confrontations/priced-violence §4 → T3 (`priced_violence_marks_the_yahoo` trope) + T6 (lore); political pillar §5 → T6 (lore) + T9 (npcs goals); go-home spine §6 → T2 + T3 (`the_compulsion_to_reembark`) + T5 (`the_homecoming`); cultures/naming §7 → T7; NPC roster §8 → T9; geography §9 → T5 + POIs T4; tropes §10 → T3; archetype funnels §11 → T8; Premise §12 → T13 (draft) + T6 (lore flavor); Morten visual §13 → T11; file manifest §14 → all of Phase 1–2; out-of-scope §15 → Follow-on; validation gates §16 → T14–T16. Correct.
- **No genre phase:** the `wry_whimsy` chassis is already live (`genre_packs/wry_whimsy/` exists) — this plan is world-only, like the Wonderland build, unlike the Oz build.
- **Cross-ref ordering closed:** `tropes.yaml` (T3) authored before `history.yaml` (T4) and `legends/` (T6) which reference trope ids; cartography entity `ref`s (T5) and `npcs.yaml` ids (T9) flagged to reconcile in both tasks; the T15 loader probe asserts the ref↔id closure.
- **Engine-unwired files correctly omitted:** no `confrontations.yaml`/`faction_agendas.yaml` (Oz/Wonderland carry neither; confrontation crunch is genre `rules.yaml`, faction motion rides npcs goals). `premises.draft.yaml` authored as an explicitly-unloaded draft (single spanning Premise, not four), not a declared extension.
- **Asset-prompt sourcing verified against the scripts:** POI prompts go in `history.yaml.points_of_interest[].visual_prompt.{solo,backdrop}`; portraits in `portrait_manifest.yaml.characters[]`; both rely on the world `visual_style.yaml` `positive_suffix` (kept lean for the token budget).
- **Draft lifecycle made explicit:** author `draft: true`, flip false only for the T15 loader test (trap-restored), go-live deferred to the render pass — closes the "draft silently skips the world" trap.
- **Known traps wired into tasks:** `triggers.mode` solo/multiplayer-not-mp (T10), `first_turn_invitation` no-`?` (T10), unquoted `': '` dict-coercion (T7 cultures, T9 npcs), token-budget BudgetError dry-runs (T11/T12), draft-skip (T15), word_list-not-Markov (T7).
- **Specialist lanes:** `writer` authors prose (Phase 1, no Bash — GM runs validate/commit); `art-director` authors visual_style/portraits/POI prompts (Phase 2, has Bash); `cliche-judge` audits at finish (T16). The GM orchestrates, runs the loader gate, and owns the commits writer can't make.
- **Type/id consistency:** trope ids all-underscore (`the_compulsion_to_reembark`, not hyphen) and identical between T3 and the §10 spec; region ids identical between T4 (POIs), T5 (regions), and T15 (probe `the_lilliput_shore`/`mildendo_capital`); NPC ids identical between T5 entity refs, T9 roster, and the §8 spec; Bloc ids (`the_lilliput_court` etc.) identical between T5 `controlled_by`, T13 premise draft, and the §12 spec.
```
