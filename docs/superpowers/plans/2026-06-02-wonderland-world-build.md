# Wonderland World — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author the **Wonderland** world (`genre_packs/wry_whimsy/worlds/wonderland`) to full playable depth — honest, source-faithful content plus POI/portrait asset *prompts* — schema-valid and loader-clean. Asset *rendering* is a later `--shard` daemon pass.

**Architecture:** World-only content build (YAML/Markdown — no engine code). The `wry_whimsy` genre chassis is **already live** at `genre_packs/wry_whimsy/` (mechanics, Composure substrate, five Travelers, the Bang catalog, the four-principle narrator doctrine) — Wonderland supplies **only flavor + dials**, mirroring the existing `worlds/oz/` file set in a two-lobed shape. Design source of truth: `docs/superpowers/specs/2026-06-02-wonderland-world-design.md`.

**Tech Stack:** YAML world configs validated against `sidequest-content/pack_schema.yaml` via `python -m sidequest.cli.validate pack <pack-dir>`; headless loader check via the server; POI prompts rendered later via `scripts/generate_poi_images.py` / portraits via `scripts/generate_portrait_images.py`.

> **Plan-type note (content adaptation of writing-plans):** This is content authoring, not TDD code. "Failing test" = the validator/loader reporting a file missing or malformed; "passing" = validator green and content present. Each file's required keys and content *shape* are specified here; full prose is authored against the spec at execution time (the spec carries the complete design, played straight from Carroll). The cross-ref ordering (tropes before history/legends) and the two-lobe cartography are the load-bearing parts.

---

## Mandatory loader contract (mirror `worlds/oz/`, confirmed against the live pack)

**World `required_files`:** `world.yaml`, `cartography.yaml`, `history.yaml`, `lore.yaml`, `openings.yaml`, `portrait_manifest.yaml`, `tropes.yaml`, `visual_style.yaml`, `archetypes.yaml`.

**World `required_dirs`:** `cultures/` (per-culture yaml inside), `legends/` (per-legend yaml inside), `assets/images/portraits`, `assets/images/poi`.

**World extensions Oz declares (Wonderland mirrors):** `archetype_funnels` (`archetype_funnels.yaml`), `npcs` (`npcs.yaml`). **Oz does NOT carry `confrontations.yaml` or `faction_agendas.yaml`** — they are engine-unwired; confrontation crunch lives in genre `rules.yaml`, and Living-World faction motion rides on `npcs.yaml` goals. **Wonderland authors neither.**

**Cross-ref rules to satisfy:** trope ids referenced in `history.yaml` chapters and legends' `related_tropes` must resolve against (genre ∪ Wonderland) trope ids → **author `tropes.yaml` before/with `history.yaml` + `legends/`**. World `archetypes.yaml` `typical_classes`/`typical_races` must exist in the genre `rules.yaml` (already live — reuse Oz's values).

**POI prompt sourcing (confirmed):** `scripts/generate_poi_images.py` reads `history.yaml` → `chapters[].points_of_interest[]`, using `visual_prompt.solo` (the renderable PLACE only) + `slug` + `region`. Style/medium/palette come from `visual_style.yaml` `positive_suffix`, appended on every render. **POI prompts are authored as `points_of_interest` entries in `history.yaml`, not a separate file.**

**Portrait prompt sourcing (confirmed):** `portrait_manifest.yaml` → `characters:` list, each `name`/`role`/`type` + `appearance`/`culture_aesthetic`/`element_visual` (the five_points/Oz manifest schema). Subject only; the `visual_style` suffix carries medium/exclusions.

**Draft lifecycle:** author with `world.yaml` `draft: true` while assets are unrendered (avoids missing-asset errors) — **but `draft: true` makes `load_genre_pack` SILENTLY SKIP the world** (invisible/unplayable in the lobby). The loader smoke-test (Task 12) flips `draft: false` *temporarily* to prove it loads, then restores `draft: true`. Going live (flip to `draft: false` for keeps) happens **after** the render pass, not in this plan.

---

## Pre-flight environment (run once)

- [ ] **Set env for validator + loader.** The pack is now in the default `genre_packs/` path.
```bash
export SIDEQUEST_GENRE_PACKS=/Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs
export SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test
```

---

## Phase 0 — Branch + scaffold

### Task 1: Branch the content subrepo and scaffold the Wonderland world skeleton

**Files:** create the `genre_packs/wry_whimsy/worlds/wonderland/` tree (required dirs present with `.gitkeep`; required files created empty, filled in later phases).

- [ ] **Step 1: Branch content off develop** (the pf hook scans all subrepos — branch before the first commit anywhere)
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git checkout develop && git pull --ff-only && git checkout -b feat/wonderland-world
```

- [ ] **Step 2: Create the directory skeleton**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy/worlds/wonderland
mkdir -p cultures legends assets/images/portraits assets/images/poi
find assets -type d -empty -exec touch {}/.gitkeep \;
```

- [ ] **Step 3: Verify the validator reports missing FILES (not dirs)** — the "failing test" baseline
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run python -m sidequest.cli.validate pack \
  /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy
```
Expected: errors listing missing required Wonderland files (`world.yaml`, `cartography.yaml`, …). Oz must remain green. Confirms the skeleton is correct.

- [ ] **Step 4: Commit the scaffold**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git add genre_packs/wry_whimsy/worlds/wonderland && \
  git commit -m "scaffold(wonderland): world dir/file skeleton"
```

---

## Phase 1 — Wonderland world content

Each task: read Oz's counterpart for the exact key shape, author the Wonderland file(s) against spec, re-run the validator, commit. The validator is the gate — a task is done when it no longer reports that file missing/malformed and introduces no new cross-ref error.

### Task 2: `world.yaml` — identity, dials, go-home spine

**Files:** Create `worlds/wonderland/world.yaml` (read `worlds/oz/world.yaml` first for the exact key set)

- [ ] **Step 1: Author** — `name: Wonderland`, `slug: wonderland`, `cover_poi` (a strong Card-Country POI slug, e.g. `queens_croquet_ground`), `description`; **both-books corpus** (1865 + 1871 as one dream-territory); **lethality dial = MEDIUM** (override genre default); tone-axis overrides (`menace` ~0.5, `sense`/nonsense low — nonsense is the antagonist, `gravity` ~0.45); `starting_region: the_hall_of_doors`; the **waking go-home spine** (you leave by refusing the dream; reshaping it raises the cost of leaving). Set `draft: true` (assets pending — see Draft lifecycle).
- [ ] **Step 2: Validate** — `validate pack …`; expect `world.yaml` no longer missing for wonderland.
- [ ] **Step 3: Commit** — `feat(wonderland): world identity + medium-lethality dials`

### Task 3: `tropes.yaml` — the nine Wonderland tropes (author FIRST for cross-refs)

**Files:** Create `worlds/wonderland/tropes.yaml` (read `worlds/oz/tropes.yaml` for `id` + keyword-wiring shape)

- [ ] **Step 1: Author** the nine spec §8 tropes, each with a stable `id` + keyword wiring: `nonsense_as_authority`, `the_capricious_sentence`, `the_size_game` (eat-me/drink-me), `stuck_in_the_nonsense`, `the_truth_telling_cat`, `only_a_thing_in_his_dream`, `run_to_stay_in_place`, `the_pack_of_cards` (collapse), `the_jabberwock` (the real monster / priced violence). These ids are referenced by Tasks 4 (history) and 6 (legends) — keep them stable.
- [ ] **Step 2: Validate** — `tropes.yaml` resolved.
- [ ] **Step 3: Commit** — `feat(wonderland): nine Wonderland tropes`

### Task 4: `history.yaml` — the dream's "past" + the 13 POI prompts

**Files:** Create `worlds/wonderland/history.yaml` (read `worlds/oz/history.yaml` for the `chapters:` + `points_of_interest:` + `visual_prompt:{solo,backdrop}` shape and the pipeline comment block)

- [ ] **Step 1: Author `chapters:`** — the dream's past played straight, not over-explained: the card court and its terror-theater, the chess-game-in-progress, how the two queens came to rule and the Red King fell asleep, the Jabberwock loose in the Tulgey Wood. Any trope `id` referenced MUST resolve against Task 3 ids.
- [ ] **Step 2: Author `points_of_interest:`** — the ~13 renderable POIs, each with `name`, `slug`, `region` (matching Task 5 region ids), `type`, `description`, and `visual_prompt: {solo, backdrop}` where **`solo` is the renderable PLACE only** (no style/medium — that's the suffix), played straight from Tenniel: `hall_of_doors`, `pool_of_tears`, `white_rabbits_house`, `caterpillars_mushroom`, `duchess_pepper_kitchen`, `mad_tea_party`, `queens_croquet_ground`, `hall_of_justice`, `the_looking_glass` (the mirror seam), `garden_of_live_flowers`, `chessboard_country`, `tweedle_wood`, `wood_of_no_names`, `humpty_dumptys_wall`, `coronation_feast`. Keep each `solo` short (token budget — the suffix is un-evictable; long POI prose evicts LOCATION to a BudgetError).
- [ ] **Step 3: Validate** — expect no "history references unknown trope id" errors; POI entries parse.
- [ ] **Step 4: Commit** — `feat(wonderland): history + 13 POI visual prompts`

### Task 5: `cartography.yaml` — the two-lobe region graph + mirror seam

**Files:** Create `worlds/wonderland/cartography.yaml` (read `worlds/oz/cartography.yaml` for the `regions:` / `adjacent:` / `entities:` / `affordances:` shape)

- [ ] **Step 1: Author the map header** — `navigation_mode: region`, `starting_region: the_hall_of_doors`, `world_name: Wonderland`, and a `map_style` prose (spec §7: Card Country as a heraldic playing-card garden, Looking-Glass Land as a green-and-white chessboard divided by brooks, the two lobes meeting at a tall mantelpiece mirror; engraved Tenniel line).
- [ ] **Step 2: Author the ~13 regions** as the spec §7 graph, two lobes joined by the seam:
  - **Card lobe:** `the_hall_of_doors` (start; entities: tiny garden door, the eat-me cake / drink-me bottle with `grow`/`shrink` affordances), `the_pool_of_tears` (caucus-race shore, White Rabbit's house), `the_tulgey_wood` (Caterpillar's mushroom, the Duchess's pepper-kitchen, the Cheshire Cat; the roaming Jabberwock as a `real_object`-bound npc), `the_mad_tea_party` (stuck at six o'clock), `the_queens_croquet_ground` (flamingo mallets, the rose-tree, the Queen of Hearts), `the_hall_of_justice` (the trial; Card climax).
  - **Seam:** `the_looking_glass` — adjacent to BOTH climax regions, affordance `step_through`.
  - **Glass lobe:** `the_garden_of_live_flowers`, `the_chessboard_country` (brook-squares, the railway leap, the Red Queen), `the_tweedle_wood` (Tweedles, Walrus & Carpenter recital), `humpty_dumptys_wall` (the word-tyrant; the Lion & Unicorn), `the_wood_of_no_names` (forget your name — `lose_the_thread`), `the_coronation_feast` (Glass climax).
  - Each region: `name`, `summary`, `description`, `terrain`, `controlled_by` (`the_queens_terror` blocs Card-side, `the_rigged_game` Glass-side), `adjacent`, `landmarks`, `entities` (bind famous NPCs via `kind: npc, ref: <npc id from Task 9>` and POI features via `kind: location_feature`), `rivers`, `settlements`. **Entity `ref`s to NPCs must match Task 9 ids** — reconcile.
- [ ] **Step 3: Validate** — `cartography.yaml` resolved; region adjacency forms one connected graph through the seam.
- [ ] **Step 4: Commit** — `feat(wonderland): two-lobe cartography region graph + mirror seam`

### Task 6: `lore.yaml` + `legends/` — the place and its tall tales

**Files:** Create `worlds/wonderland/lore.yaml`; `worlds/wonderland/legends/{the_jabberwock,the_pack_of_cards,the_sleeping_red_king}.yaml` (read Oz counterparts for shape)

- [ ] **Step 1: Author `lore.yaml`** — the two dream-countries and their peoples, nonsense-as-authority, the two queens vs the sleeping/absent kings (the gender current), the mirror seam, and the two Premise illusions (`the_queens_terror` / `the_rigged_game`) described as in-world *flavor* (the mechanical wiring is the draft file, Task 11). Reference-stack to Carroll specifics (eat-me/drink-me, six-o'clock tea, painted roses, vorpal sword, "all the running you can do").
- [ ] **Step 2: Author the three legends** — `the_jabberwock` (the vorpal sword; the one real monster), `the_pack_of_cards` (the climactic refusal that ends the dream), `the_sleeping_red_king` (you may be only a thing in his dream). Any `related_tropes` ids MUST resolve against Task 3 ids.
- [ ] **Step 3: Validate** — expect no "legend references unknown trope id" errors.
- [ ] **Step 4: Commit** — `feat(wonderland): lore + three legends`

### Task 7: `cultures/` — the three Wonderland cultures

**Files:** Create `worlds/wonderland/cultures/{card_folk,chesspieces,creature_folk}.yaml` (read `worlds/oz/cultures/*.yaml` for the `slots`/`person_patterns`/`place_patterns` shape with `word_list` name sourcing)

- [ ] **Step 1: Author** each culture using **`word_list` name slots** (curated whimsical-English / epithet / portmanteau pools — NOT corpus Markov, per the historical-worlds naming precedent):
  - `card_folk` — flat heraldic playing-cards; names = card-rank nomenclature ("Five of Spades", "the Knave"), royal-suit titles.
  - `chesspieces` — living chess pieces; names = piece/colour nomenclature ("the White Knight", "the Red Queen"), board-rank.
  - `creature_folk` — talking dream-fauna; names = definite-article epithets ("the March Hare") + Carroll portmanteau coinage ("Bandersnatch", "Jubjub") for invented creatures.
  Each: `name`, `summary`, `description`, `slots`, patterns.
- [ ] **Step 2: Validate** — `cultures/` dir resolved.
- [ ] **Step 3: Commit** — `feat(wonderland): three cultures with curated/epithet/portmanteau name pools`

### Task 8: `archetypes.yaml` (world) + `archetype_funnels.yaml`

**Files:** Create `worlds/wonderland/archetypes.yaml`, `worlds/wonderland/archetype_funnels.yaml` (read Oz counterparts)

- [ ] **Step 1: Author world `archetypes.yaml`** — the Wonderland-tinted surface of the five genre Travelers; `typical_classes`/`typical_races` must reuse values present in the live genre `rules.yaml` (same as Oz — confirm by reading it).
- [ ] **Step 2: Author `archetype_funnels.yaml`** — spec §funnels: the **Wit** is Wonderland's home turf *and* torment (logic doesn't yield to nonsense); the **Dreamer** risks never waking (the Wood of No Names / the Red King's dream); the **Scrapper** is the Jabberwock-slayer but marked everywhere else; the **Surveyor** maps a place that won't hold still; the **Innocent** tinted toward Alice-sincerity ("curiouser and curiouser").
- [ ] **Step 3: Validate** — resolved; no archetype cross-ref errors.
- [ ] **Step 4: Commit** — `feat(wonderland): world archetypes + Wonderland funnels`

### Task 9: `npcs.yaml` — the Carroll Monster Manual

**Files:** Create `worlds/wonderland/npcs.yaml` (read `worlds/oz/npcs.yaml` for the required key shape + Living-World `goals`)

- [ ] **Step 1: Author** the spec §6 roster as pre-gen "NPCs nearby, not yet met" (ADR-059 game-state injection), each played straight from Carroll with a canonical `goal` (Living World). **Card:** `white_rabbit`, `the_caterpillar`, `the_cheshire_cat`, `the_duchess`, `the_cook`, `the_hatter`, `the_march_hare`, `the_dormouse`, `the_mock_turtle`, `the_gryphon`, `the_queen_of_hearts`, `the_king_of_hearts`, `the_knave_of_hearts`, `the_gardeners`. **Glass:** `the_red_queen`, `the_white_queen`, `the_sleeping_red_king`, `the_white_knight`, `tweedledum_and_tweedledee`, `humpty_dumpty`, `the_lion_and_the_unicorn`, `the_jabberwock`. **NPC ids here must match the `ref`s used in Task 5 cartography entities** — reconcile.
- [ ] **Step 2: Validate** — `npcs.yaml` resolved.
- [ ] **Step 3: Commit** — `feat(wonderland): Carroll NPC roster (Monster Manual)`

### Task 10: `openings.yaml` — the fall down the rabbit-hole (solo + MP)

**Files:** Create `worlds/wonderland/openings.yaml` (read `worlds/oz/openings.yaml` — match the **unified Opening schema**, not the simple genre shape)

- [ ] **Step 1: Author** the threshold-crossing opening: the **fall down the rabbit-hole** into the Hall of Doors (the size game introduced immediately). Cover **both `triggers.mode` solo AND MP**, with `establishing_narration` + `first_turn_invitation`. (Per the loader gotcha: a world `openings.yaml` needs the unified Opening schema with solo/MP coverage — the simple genre shape parses hollow.)
- [ ] **Step 2: Validate** — `openings.yaml` resolved with both modes covered.
- [ ] **Step 3: Commit** — `feat(wonderland): rabbit-hole opening (solo + MP)`

---

## Phase 2 — Asset prompts (Tenniel)

### Task 11: `visual_style.yaml` — Tenniel medium + the lean positive_suffix

**Files:** Create `worlds/wonderland/visual_style.yaml` (read `worlds/oz/visual_style.yaml` for the key shape + the trimmed-suffix discipline from content fix #329)

- [ ] **Step 1: Author** the **John Tenniel 1865/71 wood-engraving** aesthetic: Victorian steel/wood-engraving line, dense cross-hatching, period children's-book plate, restrained hand-tint over black line; flat heraldic cards; the famous Tenniel chesspiece designs; Alice-era costume. Author the explicit **NOT-Disney-1951** exclusions phrased POSITIVELY (Z-Image ignores negative prompts — "engraved line and cross-hatching, hand-tinted plate" not "no cartoon"; per the z_image_negative rule, rejection clauses go in `positive_suffix` as "...rendered as X, not Y"). Include the SOUL modesty/"adult"/"no text" cleanup clause as Oz does.
- [ ] **Step 2: Keep the `positive_suffix` SHORT** — it is the un-evictable ART_SENSIBILITY.WORLD slot; trim to clear the 512-token PromptComposer budget (the #329 lesson). Dry-run a POI to confirm composition:
```bash
cd /Users/slabgorb/Projects/oq-2 && python scripts/generate_poi_images.py --genre wry_whimsy --world wonderland --dry-run
```
Expected: all POIs compose without BudgetError; suffix carries the Tenniel medium.
- [ ] **Step 3: Validate** — `visual_style.yaml` resolved.
- [ ] **Step 4: Commit** — `feat(wonderland): Tenniel visual style + lean suffix`

### Task 12: `portrait_manifest.yaml` — the roster portrait prompts

**Files:** Create `worlds/wonderland/portrait_manifest.yaml` (read `worlds/oz/portrait_manifest.yaml` for the `characters:` schema — `name`/`role`/`type` + `appearance`/`culture_aesthetic`/`element_visual`)

- [ ] **Step 1: Author** portrait specs for the Task 9 roster (~16–18 named), **subject only** (the visual_style suffix carries medium/exclusions). Faces as PHYSICAL FACT, never as impression/expression (the Oz manifest discipline); every negation phrased positively; "adult" + modesty clause for humanoid subjects, "no text" cleanup for creatures. Source-faithful Tenniel specifics: the Queen of Hearts as a flat heraldic court-card figure; the White Knight in ramshackle armour mid-tumble; Humpty Dumpty as a great egg in a cravat on a wall; the Cheshire Cat as a broad-grinning tabby fading at the edges; the Jabberwock as Tenniel's waistcoated dragon with a long neck and buck teeth.
- [ ] **Step 2: Dry-run** a portrait compose to confirm budget:
```bash
cd /Users/slabgorb/Projects/oq-2 && python scripts/generate_portrait_images.py --genre wry_whimsy --world wonderland --dry-run
```
Expected: all portraits compose without BudgetError.
- [ ] **Step 3: Validate** — `portrait_manifest.yaml` resolved.
- [ ] **Step 4: Commit** — `feat(wonderland): Tenniel portrait manifest`

### Task 13: `premises.draft.yaml` — DRAFT Premise/Bloc identities (UNWIRED)

**Files:** Create `worlds/wonderland/premises.draft.yaml`

- [ ] **Step 1: Author** the two Premise + Bloc identities from spec §4/§9 as a clearly-flagged **draft** (a leading comment banner: "DRAFT — pending oq-3 belief-engine schema lock; NOT loaded by any consumer; do not declare as an extension"). Use the `.draft.yaml` name so the loader ignores it (no Python consumer exists yet — per the unwired-world-extension rule, do NOT add it to any `extensions:` list). Capture: `the_queens_terror` (authority: queen_of_hearts; bloc: the_card_court; collapse: "pack of cards"; draining-acts: defy-a-sentence-and-survive, expose-the-King-commutes, refuse-the-trial, name-the-pack-of-cards) and `the_rigged_game` (authority: red_queen; bloc: the_chesspieces; collapse: shake-the-queen-at-the-feast; draining-acts: refuse-the-race, reach-the-eighth-square-on-your-terms, name-the-sleeper's-dream).
- [ ] **Step 2: Validate** — full pack validation unaffected (the draft file is not a required/declared file; confirm it does NOT introduce errors).
- [ ] **Step 3: Commit** — `docs(wonderland): DRAFT premise/bloc identities (pending oq-3 schema)`

---

## Phase 3 — Validation + loader gate + PR

### Task 14: Full pack validation green

- [ ] **Step 1: Run the full validator**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run python -m sidequest.cli.validate pack \
  /Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs/wry_whimsy
```
Expected: PASS (errors = 0). Asset warnings acceptable while `draft: true`. Oz must remain green. Fix any cross-ref errors inline (most likely: a cartography entity `ref` not matching an `npcs.yaml` id, or a trope id in history/legends not in `tropes.yaml`).
- [ ] **Step 2: Commit any fixes** — `fix(wonderland): validator green`

### Task 15: Loader smoke-test (the real wiring gate)

- [ ] **Step 1: Temporarily flip `draft: false`** in `world.yaml` and confirm `load_genre_pack` actually ingests Wonderland (a `draft: true` world is silently skipped — the validator passing is NOT proof it loads). Start the server (env from Pre-flight) and confirm `wonderland` appears in the world metadata for `wry_whimsy` with no load error. A loader/validator mismatch surfaces here — if it's an engine bug, route to Dev via pingpong with OTEL evidence; do NOT edit engine code.
- [ ] **Step 2: Headless arrival check** — a short scripted entry into Wonderland: chargen as a Traveler → fall down the rabbit-hole into the Hall of Doors → move to one adjacent region → meet one roster NPC (e.g. the Cheshire Cat). Watch OTEL: the region graph navigates, the NPC registry picks up the roster, the narrator draws from `game_state` (not improvising), Composure is tracked. SOUL pass: diegetic sincerity (no winking), the seams are bait (the Cheshire tells plain truth).
```bash
cd /Users/slabgorb/Projects/oq-2 && python scripts/playtest.py --genre wry_whimsy --world wonderland
```
- [ ] **Step 3: Restore `draft: true`** (assets not yet rendered — Wonderland goes live only after the render pass). Log findings: any missing OTEL span = engine bug → pingpong; any present-but-wrong value = content bug → fix here.
- [ ] **Step 4: Commit** — `test(wonderland): loader + arrival smoke-test findings`

### Task 16: Open the PRs

- [ ] **Step 1: Push + PR the content branch** to `develop`
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git push -u origin feat/wonderland-world && \
  env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-content --base develop \
  --title "feat: Wonderland world (Carroll, both books, Tenniel)" \
  --body "Second wry_whimsy world. See orchestrator spec 2026-06-02-wonderland-world-design.md. Assets (POI/portrait prompts authored) render in a later --shard pass; world stays draft:true until then."
```
- [ ] **Step 2: Merge** (squash) once green, then verify the merge landed on `develop`.
- [ ] **Step 3: PR the orchestrator spec+plan** branch (`docs/travelers-tales-genre-design`) to `develop` similarly (or fold into the existing branch's PR).

---

## Follow-on (out of scope for this plan)

- **Render pass** — POI landscapes + portraits via `scripts/generate_{poi,portrait}_images.py --genre wry_whimsy --world wonderland [--shard i/n] [--steps 30]`, daemon upload to the content-addressed R2 artifact path, then the **separate inline boto3 PUT** to the canonical `genre_packs/wry_whimsy/worlds/wonderland/assets/{poi,portraits}/` path, **verified with `list_objects_v2`** (the bulk sync script fails opaquely). Render runs on oq-1's content tree (FF-pull first).
- **Go live** — flip `world.yaml` `draft: false` once assets are on R2.
- **Premise/Bloc wiring** — when the oq-3 belief-engine schema lands, promote `premises.draft.yaml` to the real schema and declare it.
- **Music** (ACE-Step) for `wry_whimsy`; **Gulliver** world.

---

## Self-review notes

- **Spec coverage:** every spec section maps to a task — identity/go-home §2 → T2; lethality §3 → T2; political pillar/Premises §4/§9 → T13 (draft) + T6 (lore flavor); cultures/naming §5 → T7; NPC roster §6 → T9; region graph §7 → T5 + POI prompts T4; tropes §8 → T3; Tenniel visual §10 → T11; file manifest §11 → all of Phase 1–2; validation gates §13 → T14–T15. Out-of-scope §12 (rendering, premise wiring, Looking-Glass-as-separate-world, music, Gulliver) → Follow-on, no tasks. Correct.
- **No genre phase:** the `wry_whimsy` chassis is already live (confirmed `genre_packs/wry_whimsy/` exists, `genre_workshopping/wry_whimsy/` does not) — this plan is world-only, unlike the Oz build.
- **Cross-ref ordering closed:** `tropes.yaml` (T3) authored before `history.yaml` (T4) and `legends/` (T6) which reference trope ids; cartography entity `ref`s (T5) and `npcs.yaml` ids (T9) flagged to reconcile in both tasks.
- **Engine-unwired files correctly omitted:** no `confrontations.yaml`/`faction_agendas.yaml` (Oz carries neither; confrontation crunch is genre `rules.yaml`, faction motion rides npcs goals). `premises.draft.yaml` authored as an explicitly-unloaded draft, not a declared extension.
- **Asset-prompt sourcing verified against the scripts:** POI prompts go in `history.yaml.points_of_interest[].visual_prompt.{solo,backdrop}`; portraits in `portrait_manifest.yaml.characters[]`; both rely on the world `visual_style.yaml` `positive_suffix` (kept lean for the token budget).
- **Draft lifecycle made explicit:** author `draft: true`, flip false only for the T15 loader test, go-live deferred to the render pass — closes the "draft silently skips the world" trap.
