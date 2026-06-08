# Wry Whimsy Genre + Oz World — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author a new public-domain genre pack `wry_whimsy` (mechanics chassis) plus the **Oz** world to full playable depth, schema-valid and headless-smoke-testable.

**Architecture:** Content-only build (YAML/Markdown/CSS — no engine code). Genre tier = mechanics + tone + narrator doctrine; world tier = Oz flavor. Native ruleset, wit/**Composure**-first resolution. Authored in `genre_workshopping/wry_whimsy/` (workshop-first). Design source of truth: `docs/superpowers/specs/2026-06-01-travelers-tales-genre-design.md`.

**Tech Stack:** YAML genre/world configs validated against `sidequest-content/pack_schema.yaml` via `python -m sidequest.cli.validate pack <dir>`; headless playtest via `scripts/playtest.py`.

> **Plan-type note (adaptation of writing-plans for content):** This is a content-authoring plan, not TDD code. "Failing test" = the schema validator / loader / smoke-test reporting the file missing or malformed; "passing" = validator green and content present. Each file's required keys and content *shape* are specified here; full prose/lore is authored against the spec at execution time (the spec carries the complete design). The contract checklist (Task 1) is the load-bearing part — get every mandatory file/dir right and the loader stays green.

---

## Mandatory loader contract (from `pack_schema.yaml`) — the checklist that prevents end-of-build failures

**Genre `required_files`:** `pack.yaml`, `theme.yaml`, `archetypes.yaml`, `tropes.yaml`, `lore.yaml`, `audio.yaml`, `rules.yaml`, `char_creation.yaml`, `inventory.yaml`, `lethality_policy.yaml`, `power_tiers.yaml`, `progression.yaml`, `prompts.yaml`, `axes.yaml`, `visibility_baseline.yaml`, `client_theme.css`. (`visual_style.yaml` + `cultures.yaml` are OPTIONAL at genre — flavor lives at world.)

**Genre `required_dirs`:** `audio/music`, `assets/fonts`, `assets/images/portraits`, `assets/images/poi`, `worlds`.

**Genre extensions we declare in `pack.yaml` `extensions:`** (each adds required files): `openings`, `beat_vocabulary`, `archetype_constraints`, `achievements`. (Declaring an extension means its file MUST exist.)

**World `required_files`:** `world.yaml`, `cartography.yaml`, `history.yaml`, `lore.yaml`, `openings.yaml`, `portrait_manifest.yaml`, `tropes.yaml`, `visual_style.yaml`, `archetypes.yaml`.

**World `required_dirs`:** `cultures/` (DIR — per-culture yaml inside), `legends/` (DIR — per-legend yaml inside), `assets/images/portraits`, `assets/images/poi`.

**World extensions we declare:** `archetype_funnels` (`archetype_funnels.yaml`), `npcs` (`npcs.yaml`), `confrontations` (`confrontations.yaml`), `faction_agendas` (`faction_agendas.yaml`).

**`theme.yaml` hard requirements** (pydantic `extra="forbid"`, no silent fallback): `web_font_family`, `display_font_family`, `dinkus.glyph.{light,medium,heavy}`.

**Validator cross-ref rules to satisfy:** trope ids referenced in `history.yaml` chapters and legends' `related_tropes` must resolve against (genre ∪ world) trope ids; archetype `typical_classes`/`typical_races` must exist in `rules.yaml`; `archetype_constraints` jungian/role ids must come from the repo-global `archetypes_base.yaml` and `genre_flavor` must cover EXACTLY those ids.

---

## Pre-flight environment (run once before validating/playtesting)

- [ ] **Confirm env for validator + server.** The validator needs the repo-global `archetypes_base.yaml` (auto-located by walking up). Server load/playtest needs:
```bash
export SIDEQUEST_GENRE_PACKS=/Users/slabgorb/Projects/oq-2/sidequest-content/genre_workshopping
export SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test
```
Note: workshop packs are NOT in the default `genre_packs/` load path — point `SIDEQUEST_GENRE_PACKS` at `genre_workshopping` (or add it) for the smoke-test.

---

## Phase 0 — Branch + scaffold

### Task 1: Branch the content subrepo and scaffold the mandatory dir/file skeleton

**Files:** create the full `genre_workshopping/wry_whimsy/` tree (empty-but-present required dirs with `.gitkeep`; required files created empty, filled in later phases).

- [ ] **Step 1: Branch content off develop** (the pf hook scans all subrepos — branch before first commit anywhere)
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git checkout develop && git pull --ff-only && git checkout -b feat/wry-whimsy-oz
```

- [ ] **Step 2: Create the directory skeleton**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content/genre_workshopping/wry_whimsy
mkdir -p audio/music assets/fonts assets/images/portraits assets/images/poi \
  worlds/oz/cultures worlds/oz/legends \
  worlds/oz/assets/images/portraits worlds/oz/assets/images/poi
find . -type d -empty -exec touch {}/.gitkeep \;
```

- [ ] **Step 3: Verify validator reports missing FILES (not dirs)** — this is the "failing test" baseline
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run python -m sidequest.cli.validate pack \
  /Users/slabgorb/Projects/oq-2/sidequest-content/genre_workshopping/wry_whimsy
```
Expected: errors listing missing required genre files (pack.yaml, theme.yaml, …). Dirs should NOT be reported missing. This confirms the skeleton is correct and the validator runs.

- [ ] **Step 4: Commit the scaffold**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git add genre_workshopping/wry_whimsy && \
  git commit -m "scaffold(wry_whimsy): mandatory dir/file skeleton"
```

---

## Phase 1 — Genre chassis (mechanics + tone + doctrine)

Each task: author the file(s), re-run the validator, commit. The validator is the gate — a task is done when it no longer reports that file missing/malformed and introduces no new cross-ref error.

### Task 2: `pack.yaml` — identity + extension declarations

**Files:** Create `genre_workshopping/wry_whimsy/pack.yaml`

- [ ] **Step 1: Author** — `name: Wry Whimsy`, `version`, `description` (golden-age literary portal fairytale), `lobby_blurb`, `recommended_players` (min 2 / max 5 / sweet_spot 4), `min_sidequest_version`, and crucially the `extensions:` list declaring: `openings`, `beat_vocabulary`, `archetype_constraints`, `achievements`. Model on `genre_workshopping/low_fantasy/pack.yaml` for shape; add the `extensions` block.
- [ ] **Step 2: Validate** — `validate pack …`; expect `pack.yaml` no longer missing; expect new "missing extension file" errors for openings/beat_vocabulary/archetype_constraints/achievements (proves extensions are wired).
- [ ] **Step 3: Commit** — `feat(wry_whimsy): pack.yaml + extension declarations`

### Task 3: `rules.yaml` — native ruleset binding + traveler chargen primitives

**Files:** Create `rules.yaml`

- [ ] **Step 1: Author** — `ruleset: native` (default; explicit). Traveler-appropriate: `stat_generation`, `ability_score_names` (the genre is wit-first — e.g. `WIT, NERVE, HEART, GUILE, WONDER` rather than STR/DEX; confirm native accepts custom names per low_fantasy's `ability_score_names`), `allowed_classes`/`allowed_races` that the archetypes' `typical_classes`/`typical_races` will reference (keep the cross-ref closed), `default_class`, `default_race`, `default_location`, `default_time_of_day`. NO combat-centric rest/encumbrance variants.
- [ ] **Step 2: Validate** — expect `rules.yaml` resolved; no archetype cross-ref errors yet (archetypes come in Task 8).
- [ ] **Step 3: Commit** — `feat(wry_whimsy): native rules.yaml with wit-first ability axes`

### Task 4: `axes.yaml` — tone axes

**Files:** Create `axes.yaml`

- [ ] **Step 1: Author** four tone axes (model on low_fantasy `axes.yaml` `definitions:` shape — `id`, `name`, `description`, `poles:[a,b]`, `default`):
  - `whimsy` (poles `grim`↔`whimsical`, default 0.7)
  - `sense` (poles `nonsense`↔`logical`, default 0.35 — the world runs on dream-logic)
  - `gravity` (poles `light`↔`heavy`, default 0.3 — Oz baseline; worlds override)
  - `menace` (poles `cosy`↔`savage`, default 0.3 — the world's slot on the light→savage gradient; worlds override)
- [ ] **Step 2: Validate** — `axes.yaml` resolved.
- [ ] **Step 3: Commit** — `feat(wry_whimsy): tone axes`

### Task 5: `lethality_policy.yaml` — Composure as the lethality substrate

**Files:** Create `lethality_policy.yaml`

- [ ] **Step 1: Inspect the contract first** — read an existing pack's `lethality_policy.yaml` (e.g. a live pack under `genre_packs/`) to learn the exact key shape the loader expects; author Composure semantics within it (the tracked ablative pool is Composure; pool-exhaustion = "break" not death; recovery governed by the per-world lethality dial). Do NOT invent keys the loader doesn't read — match the schema, express Composure as the policy's reskin.
- [ ] **Step 2: Validate** — `lethality_policy.yaml` resolved.
- [ ] **Step 3: Commit** — `feat(wry_whimsy): lethality_policy — Composure substrate`

### Task 6: `visibility_baseline.yaml` — perception baseline

**Files:** Create `visibility_baseline.yaml`

- [ ] **Step 1: Inspect + author** — read an existing pack's `visibility_baseline.yaml` for the key shape (ADR-104/105 perception baseline); author a sensible default (full collaborative visibility — the playgroup doesn't slip notes; matches ADR-036 doctrine).
- [ ] **Step 2: Validate** — resolved.
- [ ] **Step 3: Commit** — `feat(wry_whimsy): visibility baseline`

### Task 7: `prompts.yaml` — the four-principle narrator doctrine

**Files:** Create `prompts.yaml`

- [ ] **Step 1: Inspect + author** — read an existing pack's `prompts.yaml` for the zone/section keys the loader consumes; author the four doctrine principles (diegetic sincerity / seams-as-bait / place-not-plot / source-fidelity-not-Hollywood) into the appropriate narrator-guidance zones. This is the genre's narrator contract — the highest-leverage content file.
- [ ] **Step 2: Validate** — resolved.
- [ ] **Step 3: Commit** — `feat(wry_whimsy): narrator doctrine prompts`

### Task 8: `archetypes.yaml` + `archetype_constraints.yaml` — the five Travelers

**Files:** Create `archetypes.yaml`, `archetype_constraints.yaml`

- [ ] **Step 1: Read `archetypes_base.yaml`** (repo-global) to get the canonical jungian + rpg_role id sets — `archetype_constraints.genre_flavor` must cover EXACTLY those ids.
- [ ] **Step 2: Author `archetypes.yaml`** — the five coping-style Travelers (Innocent, Wit, Surveyor, Scrapper, Dreamer); each `typical_classes`/`typical_races` MUST be values present in `rules.yaml` (Task 3).
- [ ] **Step 3: Author `archetype_constraints.yaml`** — `valid_pairings` using only canonical jungian/role ids; `genre_flavor` covering exactly the canonical id set.
- [ ] **Step 4: Validate** — expect no "unknown jungian/role id" or "typical_class not in rules" errors.
- [ ] **Step 5: Commit** — `feat(wry_whimsy): five Traveler archetypes + constraints`

### Task 9: `char_creation.yaml`, `progression.yaml`, `power_tiers.yaml` — traveler creation + savvy progression

**Files:** Create the three files

- [ ] **Step 1: Author** — `char_creation.yaml` (Traveler chargen flow); `progression.yaml` + `power_tiers.yaml` expressing growth as *savvy/insight tiers* (learning the world's rules), NOT combat levels. Inspect a live pack's versions for required keys.
- [ ] **Step 2: Validate** — resolved.
- [ ] **Step 3: Commit** — `feat(wry_whimsy): traveler creation + savvy progression`

### Task 10: `beat_vocabulary.yaml` — wit/Composure/trial/escape beats

**Files:** Create `beat_vocabulary.yaml`

- [ ] **Step 1: Author** — beats for the six confrontation types (Audience/Trial, Wit-Duel, Escape, Wonder-Shock, Persuasion, priced-Violence); ensure exit beats carry `resolution: true` (per the hp_depletion authoring trap — prose `consequence:` is inert). Inspect a live pack's `beat_vocabulary.yaml` for shape.
- [ ] **Step 2: Validate** — resolved.
- [ ] **Step 3: Commit** — `feat(wry_whimsy): beat vocabulary`

### Task 11: `inventory.yaml`, `achievements.yaml` — item vocabulary + achievements

**Files:** Create both

- [ ] **Step 1: Author** genre item vocabulary and a handful of genre achievements (e.g. "Pulled the Curtain" — see a seam for what it is). Inspect live-pack shapes.
- [ ] **Step 2: Validate** — resolved.
- [ ] **Step 3: Commit** — `feat(wry_whimsy): inventory + achievements`

### Task 12: `tropes.yaml` (genre) + `lore.yaml` (genre) — structural tropes + mechanics framing

**Files:** Create both

- [ ] **Step 1: Author `tropes.yaml`** — genre-structural tropes (threshold-crossing, impossible-authority, the-incomplete-companion, the-seam-reveal), each with `id` + keyword wiring. These ids form part of the resolved trope set that world `history.yaml`/`legends` cross-ref against — keep ids stable.
- [ ] **Step 2: Author `lore.yaml`** (genre) — thin, mechanics/structure framing of the portal-fairytale form (NOT world flavor — that's Oz's job). Required at genre level.
- [ ] **Step 3: Validate** — resolved; no dangling trope refs (none referenced yet).
- [ ] **Step 4: Commit** — `feat(wry_whimsy): genre tropes + lore framing`

### Task 13: `theme.yaml` + `client_theme.css` + `audio.yaml` — chrome + audio manifest

**Files:** Create the three

- [ ] **Step 1: Author `theme.yaml`** with ALL hard-required keys: `web_font_family`, `display_font_family` (a Google Font already imported by the reference stylesheet — coordinate to avoid an extra fetch), `dinkus.glyph.{light,medium,heavy}`. `extra="forbid"` — no stray keys, no typos.
- [ ] **Step 2: Author `client_theme.css`** — palette/styling (whimsy-with-wry edge; world supplies per-world visual aesthetic).
- [ ] **Step 3: Author `audio.yaml`** — mood→track mood map (tracks deferred; manifest present). Inspect a live pack's `audio.yaml` for the mood key set.
- [ ] **Step 4: Validate** — full genre validation should now be GREEN for genre-tier files (world still incomplete).
- [ ] **Step 5: Commit** — `feat(wry_whimsy): theme chrome + audio manifest`

---

## Phase 2 — Oz world (full depth)

Author against spec §4. Worlds use `cultures/` and `legends/` as DIRS (per-entry yaml).

### Task 14: `world.yaml` + `cartography.yaml` — identity, era, map

**Files:** Create `worlds/oz/world.yaml`, `worlds/oz/cartography.yaml`

- [ ] **Step 1: Author `world.yaml`** — `name: Oz`, `slug: oz`, `cover_poi`, `description`; era = Wizard-era; lethality dial = LOW (override genre default); tone-axis overrides (menace low, gravity low); default opening location. Optionally `draft: true` while assets pending (draft worlds get warnings not errors on assets).
- [ ] **Step 2: Author `cartography.yaml`** — four colored countries (Munchkin blue E / Winkie yellow W / Quadling red S / Gillikin purple N) + green Emerald City center + Yellow Brick Road + the Deadly Desert lethal border. Inspect a live world's `cartography.yaml` for shape.
- [ ] **Step 3: Validate** — `world.yaml`/`cartography.yaml` resolved.
- [ ] **Step 4: Commit** — `feat(oz): world identity + four-country cartography`

### Task 15: `lore.yaml` + `history.yaml` — the place and its past

**Files:** Create `worlds/oz/lore.yaml`, `worlds/oz/history.yaml`

- [ ] **Step 1: Author `lore.yaml`** — four countries + peoples, the green-spectacles humbug, the witch-powers map, the matriarchy pillar (male power = humbug/anxiety), the sealed Secondary World (Deadly Desert). Reference-stack to Baum specifics (silver shoes, Golden Cap, etc.).
- [ ] **Step 2: Author `history.yaml`** — Oz's past (fairy enchantment of the land, witch carve-up, the Wizard's balloon arrival, the hidden infant princess under Mombi). Any trope `id` referenced in a chapter MUST resolve against (genre ∪ Oz) tropes — use ids from Task 12 / Task 18.
- [ ] **Step 3: Validate** — expect no "history references unknown trope id" errors.
- [ ] **Step 4: Commit** — `feat(oz): lore + history`

### Task 16: `cultures/` — the five country-cultures (+ micro-cultures)

**Files:** Create `worlds/oz/cultures/{munchkin,winkie,quadling,gillikin,emerald}.yaml` (+ optional `china_country.yaml`)

- [ ] **Step 1: Author** each culture using **word_list name slots** (curated whimsical-English pools — Dorothy/Ozma/Jinjur/Mombi register), NOT corpus Markov (per the historical-worlds naming precedent — Oz names are coinage, not phonotactic). Use the `slots`/`person_patterns`/`place_patterns` shape from low_fantasy `cultures.yaml`, but `given_name` via `word_list` not `corpora`. Each culture: name, summary, description, slots, patterns.
- [ ] **Step 2: Validate** — cultures dir resolved.
- [ ] **Step 3: Commit** — `feat(oz): five country-cultures with curated name pools`

### Task 17: `legends/` — in-world legends

**Files:** Create `worlds/oz/legends/{lost_princess,deadly_desert,golden_cap}.yaml`

- [ ] **Step 1: Author** each legend; any `related_tropes` ids MUST resolve against (genre ∪ Oz) tropes. The Lost Princess legend is the latent-Ozma deep hook (primed, not triggered).
- [ ] **Step 2: Validate** — expect no "legend references unknown trope id" errors.
- [ ] **Step 3: Commit** — `feat(oz): legends (lost princess primed)`

### Task 18: `tropes.yaml` (Oz) + `archetypes.yaml` (Oz) + `archetype_funnels.yaml`

**Files:** Create the three world files

- [ ] **Step 1: Author Oz `tropes.yaml`** — the seven Oz tropes (Incomplete Companion, Water-Weak Tyrant, Green Spectacles, Helpful Beasts, Deadly Desert, Enchantment-Not-Kill, Lost Princess), each with `id` + keyword wiring. (These ids are referenced by Tasks 15/17 — author this before/with them or reconcile ids.)
- [ ] **Step 2: Author world `archetypes.yaml`** (required at world tier) — Oz-tinted archetype surface.
- [ ] **Step 3: Author `archetype_funnels.yaml`** — how the five genre Travelers funnel into Oz-flavored variants.
- [ ] **Step 4: Validate** — resolved; reconcile any trope-id cross-refs from Tasks 15/17.
- [ ] **Step 5: Commit** — `feat(oz): Oz tropes + archetype funnels`

### Task 19: `npcs.yaml` — the Baum Monster Manual

**Files:** Create `worlds/oz/npcs.yaml`

- [ ] **Step 1: Author** the core cast as pre-gen "NPCs nearby, not yet met" (ADR-059 game-state injection): Scarecrow, Tin Woodman, Cowardly Lion, the Wizard (humbug), Glinda, Wicked Witch of the West (water-weak, Golden Cap), Good Witch of the North, Mombi (holds the Ozma secret), General Jinjur, King of the Winged Monkeys, Queen of the Field Mice, the Hammer-Heads, Toto, and "the Lost Princess" (latent Ozma). Each played straight from Baum with goals (Living World). Inspect a live world's `npcs.yaml` for the required key shape.
- [ ] **Step 2: Validate** — resolved.
- [ ] **Step 3: Commit** — `feat(oz): Baum NPC roster (Monster Manual)`

### Task 20: `confrontations.yaml` + `faction_agendas.yaml` — Composure scenes + Living-World motion

**Files:** Create both

- [ ] **Step 1: Author `confrontations.yaml`** — Oz-specific ConfrontationDefs instancing the six genre types at LOW lethality (Audience-with-the-Wizard, witch-bargain Trial, poppy-field/Hammer-Head Escape, Wonder-Shock at the Desert, beast-Persuasion, priced-Violence the-bucket-of-water). Composure pool; break = enchanted/enslaved/dismissed, recoverable. Ensure exit beats carry `resolution: true`.
- [ ] **Step 2: Author `faction_agendas.yaml`** — the five factions in motion with goals/timelines (Glinda's court, Wizard's regime, Witch of the West, northern hedge-witchcraft, **Jinjur's coiled revolt** + **latent Ozma** as primed advancement hooks).
- [ ] **Step 3: Validate** — resolved.
- [ ] **Step 4: Commit** — `feat(oz): Composure confrontations + faction agendas (primed)`

### Task 21: `openings.yaml` + `visual_style.yaml` + `portrait_manifest.yaml` — entry, look, portraits

**Files:** Create the three

- [ ] **Step 1: Author `openings.yaml`** — threshold-crossing openings (the cyclone / the arrival into a colored country); the sealed-world hook.
- [ ] **Step 2: Author `visual_style.yaml`** — W.W. Denslow 1900-plate aesthetic, American art-nouveau line, flat four-country color fields; NOT MGM technicolor (silver shoes). Include `positive_suffix`. *Wiring note: the daemon hard-requires a genre-level `positive_suffix` independently — confirm one exists or the genre carries a minimal `visual_style.yaml` for the daemon, even though the schema makes it optional at genre tier. Flag as a finding if the daemon load fails.*
- [ ] **Step 3: Author `portrait_manifest.yaml`** — portrait specs for the NPC roster (renders deferred to a later asset pass; manifest present and valid in both supported shapes).
- [ ] **Step 4: Validate** — full WORLD validation green (or warnings-only if `draft: true` for pending assets).
- [ ] **Step 5: Commit** — `feat(oz): openings + Denslow visual style + portrait manifest`

---

## Phase 3 — Validation + smoke-test gate

### Task 22: Full pack validation green

- [ ] **Step 1: Run full validator**
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run python -m sidequest.cli.validate pack \
  /Users/slabgorb/Projects/oq-2/sidequest-content/genre_workshopping/wry_whimsy
```
Expected: PASS (errors = 0; asset warnings acceptable if `draft: true`). Fix any cross-ref errors inline.
- [ ] **Step 2: Commit any fixes** — `fix(wry_whimsy): validator green`

### Task 23: Pack loads in the server + headless smoke-test

- [ ] **Step 1: Confirm the loader ingests the workshop pack** (env from Pre-flight). Start the server pointed at `genre_workshopping`, confirm `wry_whimsy`/`oz` appears in genre/world metadata with no load error. A loader/validator mismatch (e.g. `cultures/` dir vs `cultures.yaml`) surfaces here — if it's a code bug, route to Dev via pingpong with OTEL evidence; do NOT edit engine code.
- [ ] **Step 2: Headless smoke-test** — run a short scripted playtest into Oz (chargen as a Traveler → arrive in a colored country → one Audience/Trial confrontation → talk to one roster NPC). Watch OTEL: confrontation spans fire, Composure tracked, trope engine ticks on keywords, NPC registry picks up roster NPCs, narrator draws from game_state (not improvising).
```bash
cd /Users/slabgorb/Projects/oq-2 && python scripts/playtest.py --genre wry_whimsy --world oz
```
- [ ] **Step 3: Log findings** — SOUL pass (The Test, diegetic sincerity, seams-as-bait); any missing span = code bug → pingpong; any present-but-wrong value = content bug → fix here.
- [ ] **Step 4: Commit** — `test(oz): headless smoke-test findings`

### Task 24: Open the PRs

- [ ] **Step 1: Push + PR the content branch** to `develop`
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git push -u origin feat/wry-whimsy-oz && \
  env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-content --base develop \
  --title "feat: Wry Whimsy genre + Oz world" --body "See orchestrator spec 2026-06-01-travelers-tales-genre-design.md"
```
- [ ] **Step 2: Merge** (squash) once green, then verify the merge landed on `develop`.
- [ ] **Step 3: PR the orchestrator spec+plan** branch (`docs/travelers-tales-genre-design`) to `develop` similarly.

---

## Self-review notes

- **Spec coverage:** every spec §4 Oz element maps to a task (geography→T14, lore/history→T15, cultures→T16, legends→T17, tropes/funnels→T18, NPC roster→T19, confrontations+factions→T20, openings/visual/portraits→T21). Genre chassis §3 → Tasks 2–13. Doctrine §2 → Task 7. Three deferred items (Wonderland/Gulliver deep, asset renders, live Tip→Ozma arc) are out of scope per spec §7 — no tasks, correct.
- **Loader-contract gap closed:** `lethality_policy.yaml`, `visibility_baseline.yaml`, `cultures/`+`legends/` dirs, world `archetypes.yaml` — all now have tasks (were missing from the spec's first-pass manifest).
- **Cross-ref ordering risk:** trope ids are referenced by `history.yaml`/`legends` (Tasks 15/17) but Oz tropes are authored in Task 18 — Task 18 Step 1 and Tasks 15/17 must reconcile ids; flagged in-task. Consider authoring Oz `tropes.yaml` first if executing strictly sequentially.
- **Open verification:** the `cultures/`-dir vs `cultures.yaml`-file question (schema says dir; old `shattered_reach` uses file) is resolved by following the schema (dir) and caught at Task 23 Step 1 if the runtime loader disagrees.
