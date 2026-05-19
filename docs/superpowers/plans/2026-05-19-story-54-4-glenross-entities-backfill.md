# Story 54-4: Glenross Content Backfill — `landmarks[]` → typed `entities[]`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert every region in `tea_and_murder/glenross/cartography.yaml` from the untyped `landmarks: [...]` string array to the typed `entities: [...]` manifest defined in Story 54-2. Bind real_object entities to the existing 12 warm-cast NPCs / scenario clues where the description prose names them. Land `tea_and_murder` clean under `pf validate locations` strict mode.

**Architecture:** Pure content edit. No server code. Each authored region's existing `landmarks[]` becomes 2–4 typed `LocationEntity` entries. Mapping policy:

| Landmark prose | Tier | Binding |
|---|---|---|
| "the bar with its slate of regulars' tabs" | `real_object` | `kind: location_feature, ref: <region>_<noun>` (e.g. `glenross_arms_bar`) |
| "the telegraph machine behind the back curtain" | `real_object` | `kind: location_feature, ref: post_office_telegraph` |
| Anything that names a known NPC ("Hamish's snug") | `real_object` | `kind: npc, ref: hamish_sinclair` |
| Geraniums, decorations, atmosphere | `flavor_only` | none |
| Anything tied to a scenario clue (scenario authoring is post-v1) | `flavor_only` | (upgrade to `clue` binding in a later story once scenarios author clues for glenross) |

Authoring style — labels are what the *prose* calls the thing, lowercased, no period. Definite article kept when the prose uses it ("the bar", not "bar"). Ids are kebab-snake (`bar`, `telegraph_machine`, `village_notice_board`) — unique per region, never world-globally enforced.

The pack-level `generic_allowlist[]` lands here too (currently absent on `tea_and_murder/genre_pack.yaml`); it catches drift tokens like "the day", "the village", "the parish", "the burn", "the lane", "the schoolyard" that recur across regions and shouldn't be authored as entities.

**Tech Stack:** YAML. `pf validate locations` for verification.

**Workflow:** trivial (no automated tests; validator is the gate).

**Depends on:** 54-2 (Region.entities schema), 54-3 (validator).

---

## File Map

| File | Action |
|---|---|
| `sidequest-content/genre_packs/tea_and_murder/genre_pack.yaml` | modify — add top-level `generic_allowlist:` block |
| `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/cartography.yaml` | modify — for every region under `regions:`, add `entities:` block; leave existing `landmarks:` for backcompat (loader reads `entities` now; spec §10 keeps `landmarks` as legacy until the 54 epic closes) |

Region list (14 total, confirmed via `grep -E "^  [a-z_]+:$" cartography.yaml`):

```
the_glenross_arms        the_manse              the_distillery
the_post_office          st_margarets_chapel    castle_ross
the_tea_rooms            the_kirk_of_st_maelrubha  the_cricket_ground
the_school               the_railway_halt       the_long_pass
the_surgery              the_bridge
```

Authored NPC ids (confirmed via `grep "^  - id:" npcs.yaml`):

```
rev_murchison    dr_ross        sir_iain_ross    hamish_sinclair
rev_quill        mrs_buchan     lady_annabel_ross  sgt_macrae
miss_ferguson    hugo_ross      mrs_cameron        donald_munro    old_tam
```

---

### Task 1: Add the pack-level `generic_allowlist`

**Files:**
- Modify: `sidequest-content/genre_packs/tea_and_murder/genre_pack.yaml`

- [ ] **Step 1: Read the current genre_pack.yaml**

```bash
cat sidequest-content/genre_packs/tea_and_murder/genre_pack.yaml | head -40
```

- [ ] **Step 2: Add the allowlist block**

Append (or insert before any nested block) the following top-level field:

```yaml
# Story 54-4 / ADR-109: drift-suppression list for pf validate locations.
# Phrases here are common-noun definite-article patterns that recur in
# region prose without being mechanical entities — "the day", "the lane",
# the village" etc. Add entries cautiously: any noun that COULD be a
# Diamonds-and-Coal hook should remain a candidate for promotion, not
# be silenced into the allowlist.
generic_allowlist:
  - the village
  - the day
  - the weather
  - the sky
  - the burn
  - the river
  - the lane
  - the road
  - the path
  - the parish
  - the kirkyard
  - the schoolyard
  - the stable yard
  - the back room
  - the front room
  - the back garden
  - the front garden
  - the window
  - the door
  - the doorway
  - the threshold
  - the upstairs
  - the downstairs
  - the corner
  - the wall
  - the ceiling
  - the floor
  - the air
  - the fire
  - the hearth
  - the kettle
  - the tea
  - the morning
  - the afternoon
  - the evening
  - the night
```

- [ ] **Step 3: Sanity-check yaml parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/tea_and_murder/genre_pack.yaml'))" && echo OK
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add sidequest-content/genre_packs/tea_and_murder/genre_pack.yaml
git commit -m "feat(54-4): tea_and_murder generic_allowlist for prose drift suppression

Pack-level allowlist for pf validate locations — silences the common
noun definite-article phrases that appear across glenross regions
without being mechanically modeled. Specific entries: weather, parts
of buildings, time-of-day phrases, geography of the parish."
```

---

### Task 2: Backfill `the_glenross_arms` (pattern-establishing region)

This region is the most heavily inhabited — it's the playgroup's likely starting location and has clean NPC bindings. Do it first to lock the authoring style; then the other 13 follow the same shape.

**Files:**
- Modify: `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/cartography.yaml`

- [ ] **Step 1: Find the region and read its current state**

Run:
```bash
grep -n "the_glenross_arms:" sidequest-content/genre_packs/tea_and_murder/worlds/glenross/cartography.yaml
```
Note line number. Read 30 lines of context around it.

- [ ] **Step 2: Add `entities:` block under the region**

Insert the block **after** the existing `landmarks:` block (and before `rivers:`):

```yaml
    entities:
      - id: bar
        label: the bar
        tier: real_object
        binding:
          kind: location_feature
          ref: glenross_arms_bar
        affordances:
          - lean_on
          - order_drink
          - inspect_tab_slate
      - id: tab_slate
        label: the slate of regulars' tabs
        tier: real_object
        binding:
          kind: location_feature
          ref: glenross_arms_tab_slate
        affordances:
          - read
      - id: snug
        label: the snug at the end
        tier: real_object
        binding:
          kind: location_feature
          ref: glenross_arms_snug
        affordances:
          - enter
          - eavesdrop
      - id: snug_fire
        label: the private fire in the snug
        tier: flavor_only
      - id: upstairs_landing
        label: the upstairs landing
        tier: real_object
        binding:
          kind: location_feature
          ref: glenross_arms_landing
        affordances:
          - ascend
          - knock_on_door
      - id: room_one
        label: room one
        tier: flavor_only
      - id: room_two
        label: room two
        tier: flavor_only
      - id: room_three
        label: room three
        tier: flavor_only
      - id: stable_yard
        label: the stable yard
        tier: real_object
        binding:
          kind: location_feature
          ref: glenross_arms_stable_yard
        affordances:
          - search
      - id: hamish
        label: Hamish Sinclair
        tier: real_object
        binding:
          kind: npc
          ref: hamish_sinclair
      - id: caley
        label: Caley
        tier: real_object
        binding:
          kind: npc
          ref: hamish_sinclair
        affordances:
          - pet
```

(Caley the dog binds to `hamish_sinclair` as a proxy — there is no NPC id for Caley. v2 may mint a non-anthropic NPC; for v1 the binding routes engagement to Hamish, which is the right behavior — Caley belongs to Hamish.)

- [ ] **Step 3: Run the validator scoped to this pack**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations --json --genre-packs-root ../sidequest-content/genre_packs/tea_and_murder | jq '.errors | length, .warnings | length'
```
Expected: errors == 0. Warnings allowed (other regions still have prose drift).

If errors fire:
- `BINDING_UNRESOLVED` → fix the `ref:` to match an existing id, or change `kind: npc` to `location_feature` if the label isn't really an NPC.
- `DUPLICATE_ENTITY_ID` → rename one of the ids.
- `REAL_OBJECT_REQUIRES_BINDING` → either add a binding or drop tier to `yes_and`/`flavor_only`.

- [ ] **Step 4: Commit**

```bash
git add sidequest-content/genre_packs/tea_and_murder/worlds/glenross/cartography.yaml
git commit -m "feat(54-4): glenross_arms entities[] (pattern-establishing region)

11 entities — bar/snug/landing/stable_yard as location_feature, the
three upstairs rooms as flavor_only, Hamish and Caley as npc-bound
(Caley proxies to hamish_sinclair, no separate NPC id for the dog
in v1)."
```

---

### Task 3: Backfill the remaining 13 regions

Repeat the Task-2 pattern for every region under `regions:`. For each:
1. Identify the prose nouns the description names (skim `description:` + `landmarks:`).
2. Real, persistent, mechanically engageable → `real_object` with a `location_feature` binding (`ref: <region>_<noun>`). Items with no current subsystem id are still real_object + location_feature — the location_feature id is itself the id.
3. NPC named in description → `real_object`, `kind: npc`, `ref: <existing npc id>`.
4. Atmospheric, decorative, or one-off → `flavor_only`.

Per-region authoring brief (intent, not full YAML — author them out following the Task-2 shape):

#### `the_post_office` — Mrs Buchan's domain

Real bindings:
- `counter` → location_feature `post_office_counter`
- `brass_scale` → location_feature `post_office_brass_scale` (mentioned in landmarks)
- `telegraph` → location_feature `post_office_telegraph` (mentioned in landmarks, "behind the back curtain")
- `back_curtain` → flavor_only (the curtain itself is dressing)
- `back_room` → location_feature `post_office_back_room` (Catriona's living quarters)
- `kettle` → flavor_only (allowlisted but here it's specifically *her* kettle — keep as flavor_only entity since the description names it)
- `notice_board` → location_feature `village_notice_board` (mentioned in landmarks, *outside* the post office but in this region)
- `wooden_chair` → flavor_only
- `mrs_buchan` → npc, ref `mrs_buchan`

#### `the_tea_rooms` — Mrs Cameron's

- `gossip_table` → location_feature `tea_rooms_gossip_table` ("the round table by the door")
- `discreet_table` → location_feature `tea_rooms_discreet_table` ("the corner table behind the screen")
- `specials_slate` → location_feature `tea_rooms_specials_slate`
- `counter` → location_feature `tea_rooms_counter`
- `half_door` → flavor_only (kitchen half-door)
- `geraniums` → flavor_only (her late mother's — this is bait for emotional engagement, keep flavor_only but it WILL get promoted if a player asks about them)
- `mismatched_window` → flavor_only
- `mrs_cameron` → npc, ref `mrs_cameron`

#### `the_school` — Miss Ferguson

- `coal_stove` → location_feature `school_coal_stove`
- `warmth_bench` → flavor_only (privilege-of-the-eldest atmospheric detail)
- `slate_on_wall` → location_feature `school_slate`
- `cottage_door` → location_feature `school_cottage_door` (Miss Ferguson's private quarters)
- `hawthorn_hedge` → location_feature `school_hawthorn_hedge`
- `stile_to_railway` → location_feature `school_railway_stile`
- `desks` → flavor_only
- `inkwells` → flavor_only
- `bell` → flavor_only (the rope is the engageable thing, but no separate landmark mentions it — keep bell as flavor_only)
- `miss_ferguson` → npc, ref `miss_ferguson`

#### `the_surgery` — Dr Ross

- `surgery_door` → location_feature `surgery_door` (with hours posted)
- `waiting_bench` → location_feature `surgery_waiting_bench`
- `consulting_room` → location_feature `surgery_consulting_room`
- `dispensary` → location_feature `surgery_dispensary`
- `dr_ross` → npc, ref `dr_ross`

(If the description names more, add them. Read the description first.)

#### `the_manse` — Reverend Murchison

- `study` → location_feature `manse_study`
- `hives` → location_feature `manse_hives` (Murchison's bees — he's "done bee-work")
- `garden` → location_feature `manse_garden`
- `front_parlour` → location_feature `manse_parlour`
- `rev_murchison` → npc, ref `rev_murchison`

#### `st_margarets_chapel`

- `chapel_interior` → location_feature `chapel_interior`
- `altar` → location_feature `chapel_altar` (if mentioned)
- `rev_quill` → npc, ref `rev_quill` (the parish's second priest)

#### `the_kirk_of_st_maelrubha`

- `kirkyard` → location_feature `kirk_kirkyard`
- `headstones` → flavor_only
- `pulpit` → location_feature `kirk_pulpit`
- `pews` → flavor_only
- `vestry` → location_feature `kirk_vestry`
- `rev_murchison` → npc, ref `rev_murchison`

#### `the_railway_halt`

- `platform` → location_feature `railway_platform`
- `signal_box` → location_feature `railway_signal_box`
- `waiting_shed` → location_feature `railway_waiting_shed`
- `timetable_board` → location_feature `railway_timetable_board`

#### `the_bridge`

- `parapet` → location_feature `bridge_parapet`
- `keystone` → flavor_only
- `river_below` → flavor_only (the river itself; the burn is allowlisted)

#### `the_distillery` — Donald Munro's

- `still_house` → location_feature `distillery_still_house`
- `bonded_warehouse` → location_feature `distillery_warehouse`
- `mash_tuns` → location_feature `distillery_mash_tuns`
- `office` → location_feature `distillery_office`
- `donald_munro` → npc, ref `donald_munro`

#### `castle_ross`

- `great_hall` → location_feature `castle_great_hall`
- `library` → location_feature `castle_library`
- `armoury` → location_feature `castle_armoury`
- `gun_room` → location_feature `castle_gun_room`
- `drawing_room` → location_feature `castle_drawing_room`
- `family_chapel` → location_feature `castle_family_chapel`
- `sir_iain_ross` → npc, ref `sir_iain_ross`
- `lady_annabel` → npc, ref `lady_annabel_ross`
- `hugo` → npc, ref `hugo_ross`

#### `the_cricket_ground`

- `pavilion` → location_feature `cricket_pavilion`
- `scorebox` → location_feature `cricket_scorebox`
- `pitch` → flavor_only
- `boundary_rope` → flavor_only

#### `the_long_pass`

- `cairns` → location_feature `long_pass_cairns`
- `shielings` → location_feature `long_pass_shielings`
- `old_tam` → npc, ref `old_tam` (if the description places him there)

**Files:**
- Modify: `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/cartography.yaml`

- [ ] **Step 1: Work through each region in order**

For each region from the list above:
  - [ ] Read the region's `description:` block (use Read tool around the region's start line).
  - [ ] Author the `entities:` block per the brief, mirroring Task-2's YAML shape.
  - [ ] Insert AFTER `landmarks:` and BEFORE `rivers:` (or wherever maintains stable diff order).
  - [ ] Move to the next region. Don't batch all 13 in one shot — author one, scan it for typos, move on. The validator catches structural problems but not semantic ones.

- [ ] **Step 2: Validate after each region (optional, but cheap)**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations --genre-packs-root ../sidequest-content/genre_packs/tea_and_murder 2>&1 | tail -20
```

- [ ] **Step 3: Full validator sweep at the end**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations --genre-packs-root ../sidequest-content/genre_packs/tea_and_murder --json | jq '{errors: (.errors | length), warnings: (.warnings | length), error_codes: [.errors[].code] | unique, warning_codes: [.warnings[].code] | unique}'
```
Expected: `errors: 0`, warnings allowed but should drop sharply versus pre-backfill state.

Inspect warnings — every remaining `PROSE_DRIFT` is either:
- A noun phrase that *should* be an entity (add it).
- A common noun that *should* be in `generic_allowlist` (extend allowlist).
- A proper noun for an NPC that *is* in `npcs.yaml` but the validator's normalization missed it (rare; report as bug against 54-3 if it recurs).

Don't chase coherence warnings to zero — non-blocking by design. Aim for *no warning that obviously names a real entity you forgot.*

- [ ] **Step 4: Run the broader server suite to make sure nothing regressed**

```bash
just server-test
```
Expected: green. (The schema is permissive; this should be a no-op for non-validator tests.)

- [ ] **Step 5: Commit each region in its own commit (recommended) or in logical clusters**

```bash
git add sidequest-content/genre_packs/tea_and_murder/worlds/glenross/cartography.yaml
git commit -m "feat(54-4): glenross village-centre regions entities[] backfill

the_post_office, the_tea_rooms, the_school, the_surgery — typed
manifest with location_feature bindings for engageable furniture and
npc bindings for the warm cast members named in prose."
```

Repeat with appropriately-scoped commit messages for:
- "manse + chapel + kirk"
- "outskirts: railway halt + bridge + cricket ground + long pass"
- "distillery + castle ross"

Or one commit for all 13 — author's discretion. Smaller commits make `git blame` more useful later.

---

### Task 4: Optional — drop the legacy `landmarks:` field once the runtime fully uses `entities`

**This is NOT part of 54-4.** Spec §10 keeps `landmarks` as legacy until the 54 epic closes. Removal happens in a follow-up cleanup story after 54-9 ships and consumers no longer read `landmarks`. Do not remove here — it would silently break any consumer still reading the old field.

---

### Self-review checklist

- [ ] Every region under `regions:` in `cartography.yaml` has an `entities:` block.
- [ ] Every `real_object` entity has a `binding:` (validator-enforced).
- [ ] Every `npc` binding `ref:` matches an id in `npcs.yaml`.
- [ ] Every `location_feature` binding `ref:` is unique within its region (validator-enforced via id-uniqueness — the ref doesn't have its own uniqueness check, but in practice keeping the convention `<region>_<noun>` makes it so).
- [ ] No entity's label is empty, and every label corresponds to something the description prose actually says.
- [ ] `pf validate locations` reports 0 errors on `tea_and_murder` (warnings allowed).
- [ ] Coherence warnings have been triaged: no warning names a real entity that should have been authored.
- [ ] `just server-test` green.
- [ ] `generic_allowlist` is restrained — common nouns only, not anything a player might engage with.

### Dependencies / handoff

- **Blocked by:** 54-2, 54-3.
- **Unblocks:** runtime testing of glenross with the resolver (54-6) against real authored manifest.
- **Out of scope:** dropping the legacy `landmarks:` field; minting Caley as an independent non-anthropic NPC; authoring scenario clues that would let `clue` bindings replace some `location_feature` ones.
