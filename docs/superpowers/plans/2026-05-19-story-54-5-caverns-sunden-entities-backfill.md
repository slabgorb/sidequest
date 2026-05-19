# Story 54-5: Caverns_and_Claudes / Beneath Sünden — Surface Anchor `entities[]` Backfill

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backfill the typed `entities[]` manifest onto the two surface-anchor regions of `caverns_and_claudes/beneath_sunden`. Land `caverns_and_claudes` clean under `pf validate locations` for the authored surface — the *procedural* dungeon below the rope is owned by Story 55-1 (cookbook stitch) and is intentionally out of scope here.

**Architecture:** Pure content edit. The spec §7.2 phrases this story as "settlement rooms" but `beneath_sunden` has no `rooms/<id>.yaml` files — its rooms are generated at runtime by the cookbook+materializer (ADR-106). The only *authored* locations are the two cartography regions:

| Region | Role | Existing landmarks |
|---|---|---|
| `ropefoot` | Surface waiting-camp (`starting_region`) | The Winch-House, The Kept Fire, The Board of the Unreturned, The Rigging Benches |
| `the_dropmouth` | The shaft mouth (`cover_poi`) | The Collar, The Rope |

`beneath_sunden` has no `npcs.yaml` (the camp's people are collective — "the winch-keeper", "the camp", "delvers"). All bindings here are `location_feature` or `flavor_only`. The Board of the Unreturned is the campaign's scorekeeper and deserves a real binding; the Rope is the seam-sentinel for the procedural descent (ADR-106 §5 / Plan 7) — also real.

The pack-level `generic_allowlist[]` is added too (currently absent on `caverns_and_claudes/genre_pack.yaml`).

**Tech Stack:** YAML. `pf validate locations` for verification.

**Workflow:** trivial (no automated tests; validator is the gate).

**Depends on:** 54-2 (Region.entities schema), 54-3 (validator).

---

## File Map

| File | Action |
|---|---|
| `sidequest-content/genre_packs/caverns_and_claudes/genre_pack.yaml` | modify — add `generic_allowlist:` block |
| `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/cartography.yaml` | modify — add `entities:` to `ropefoot` and `the_dropmouth` |

---

### Task 1: Pack-level `generic_allowlist`

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/genre_pack.yaml`

- [ ] **Step 1: Read current state**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/genre_pack.yaml | head -40
```

- [ ] **Step 2: Add the allowlist block**

Append at top level:

```yaml
# Story 54-5 / ADR-109: drift suppression for pf validate locations.
# Beneath Sünden's surface prose names the rope, the cold, the shaft,
# the dark, the camp — atmosphere words that recur and aren't
# mechanically modeled. Keep this list tight: the rope and the camp
# are themselves entities in their respective regions; the allowlist
# only suppresses the GENERAL definite-article usages of these nouns
# in other contexts. If you see a player engagement against an
# allowlisted phrase break, narrow the entry.
generic_allowlist:
  - the dark
  - the cold
  - the shaft
  - the deep
  - the descent
  - the camp
  - the night
  - the day
  - the morning
  - the wind
  - the sky
  - the air
  - the stone
  - the rock
  - the lamp
  - the lamps
  - the fire
  - the floor
  - the wall
  - the ceiling
```

(Note: "the rope", "the fire" — there is a deliberate authored entity called `the_kept_fire` in ropefoot and `the_rope` in the dropmouth. The allowlist intentionally does NOT include those — the validator should match by region against the region's own entities first; allowlist only fires when neither region entity nor NPC matches. If the validator implementation in 54-3 doesn't honor that precedence, the validator is buggy and 54-3 should be amended.)

- [ ] **Step 3: Sanity-check yaml parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/caverns_and_claudes/genre_pack.yaml'))" && echo OK
```

- [ ] **Step 4: Commit**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/genre_pack.yaml
git commit -m "feat(54-5): caverns_and_claudes generic_allowlist for prose drift

Pack-level allowlist for pf validate locations — silences the dark,
the cold, the shaft, atmospheric words that recur in Beneath Sünden
surface and (eventually) procedural prose. The_kept_fire and the_rope
are deliberately excluded from the allowlist — both are authored as
entities and should resolve through the region manifest, not through
generic suppression."
```

---

### Task 2: Backfill `ropefoot`

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/cartography.yaml`

- [ ] **Step 1: Read the region's current state**

Already inspected — the description names: the rope, the flat of scoured stone, the winch-house over the drum, the kept fire, two ranks of plank benches, the board, the rope (recurring), and the people. The `landmarks:` block carries detailed entries for the Winch-House, the Kept Fire, the Board of the Unreturned, the Rigging Benches.

- [ ] **Step 2: Insert `entities:` after `landmarks:`**

```yaml
    entities:
      - id: winch_house
        label: the winch-house
        tier: real_object
        binding:
          kind: location_feature
          ref: ropefoot_winch_house
        affordances:
          - enter
          - inspect_drum
          - speak_to_winch_keeper
      - id: winch_drum
        label: the drum
        tier: real_object
        binding:
          kind: location_feature
          ref: ropefoot_winch_drum
        affordances:
          - inspect
          - turn
      - id: winch_pawl
        label: the pawl
        tier: flavor_only
      - id: kept_fire
        label: the kept fire
        tier: real_object
        binding:
          kind: location_feature
          ref: ropefoot_kept_fire
        affordances:
          - tend
          - warm_at
          - stoke
      - id: board_of_unreturned
        label: the board
        tier: real_object
        binding:
          kind: location_feature
          ref: ropefoot_board_of_unreturned
        affordances:
          - read
          - search_for_name
      - id: rigging_benches
        label: the rigging benches
        tier: real_object
        binding:
          kind: location_feature
          ref: ropefoot_rigging_benches
        affordances:
          - sit
          - rig
          - check_knots
      - id: rope
        label: the rope
        tier: real_object
        binding:
          kind: location_feature
          ref: ropefoot_rope
        affordances:
          - inspect
          - test_weight
          - descend
      - id: scoured_stone_flat
        label: the flat of scoured stone
        tier: flavor_only
      - id: lee_side_planks
        label: the salvaged plank wall on the lee side
        tier: flavor_only
      - id: winch_keeper
        label: the winch-keeper
        tier: yes_and
```

Authoring notes:
- `the winch-keeper` is `yes_and` because the prose names a person but there is no authored NPC entry for them (`beneath_sunden` has no `npcs.yaml`). Engagement promotes/canonizes per Diamonds-and-Coal.
- `the_kept_fire` and `the_rope` are intentionally `real_object` because they have mechanical roles (the fire holds back the climbing cold per the prose; the rope is the descent seam to the procedural deep, ADR-106 Plan 7).
- `the_board_of_unreturned` is the campaign scorekeeper per the existing landmark prose — `location_feature` ref reserved for future binding to a real campaign-state object (the names-burned-in list). The scorekeeper *behaviour* lands in a follow-up story; the entity reservation lands here.

- [ ] **Step 3: Validate**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations --json --genre-packs-root ../sidequest-content/genre_packs/caverns_and_claudes | jq '{errors: (.errors | length), error_codes: [.errors[].code] | unique}'
```
Expected: `errors: 0`.

- [ ] **Step 4: Commit**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/cartography.yaml
git commit -m "feat(54-5): ropefoot entities[] backfill

10 entities — winch_house/drum/kept_fire/board_of_unreturned/
rigging_benches/rope as location_feature, atmospheric stonework as
flavor_only, the_winch_keeper as yes_and (no authored NPC, engagement
canonizes per Diamonds-and-Coal). The_kept_fire and the_rope are
deliberately real_object: the fire is mechanically the cold-barrier
in the prose, the rope is the descent seam to the procedural deep
per ADR-106 Plan 7."
```

---

### Task 3: Backfill `the_dropmouth`

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/cartography.yaml`

- [ ] **Step 1: Insert `entities:` after `landmarks:`**

```yaml
    entities:
      - id: collar
        label: the collar
        tier: real_object
        binding:
          kind: location_feature
          ref: dropmouth_collar
        affordances:
          - inspect
          - chalk_mark
          - read_descent_times
      - id: rope
        label: the rope
        tier: real_object
        binding:
          kind: location_feature
          ref: dropmouth_rope
        affordances:
          - test_weight
          - grasp
          - descend
      - id: shaft
        label: the shaft
        tier: real_object
        binding:
          kind: location_feature
          ref: dropmouth_shaft
        affordances:
          - peer_into
          - drop_lamp
          - listen
      - id: cold_draught
        label: the draught
        tier: real_object
        binding:
          kind: location_feature
          ref: dropmouth_cold_draught
        affordances:
          - feel
          - sample
          - smell
      - id: lamp_reach
        label: the dark the lamps do not reach the bottom of
        tier: flavor_only
      - id: chalk_marks
        label: the chalk
        tier: flavor_only
      - id: worked_collar_stone
        label: the dwarf-cut stone
        tier: flavor_only
```

Authoring notes:
- `the_rope` is real_object **in both regions** — that's intentional: the rope is the same rope, but each region's manifest is its own scope. The two entries share the surface label but have distinct ids (`rope` in both) scoped to their region. The validator's id-uniqueness check is per-region.
- `the_cold_draught` is real_object because the prose makes it mechanically significant ("steady, colder than the night on the saddle, smelling of wet rock and the underside of old iron — and it does not vary with the wind because it does not come from the wind"). This is a deliberate hook for Diamonds-and-Coal promotion — players will ask "where does the draught come from?" and the binding gives the resolver something to engage.

- [ ] **Step 2: Validate**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations --json --genre-packs-root ../sidequest-content/genre_packs/caverns_and_claudes | jq '{errors: (.errors | length), error_codes: [.errors[].code] | unique, warnings: (.warnings | length)}'
```
Expected: `errors: 0`. Some `PROSE_DRIFT` warnings are likely on lyrical phrases ("the underside of old iron", "the lit collar"); review each and either add an entity, extend the allowlist, or accept as non-blocking.

- [ ] **Step 3: Triage remaining warnings**

For each warning in the JSON output:
- **Names a real engageable thing the prose treats as load-bearing?** Author it. Probably real_object with a location_feature binding.
- **Generic atmospheric phrase?** Add to allowlist.
- **Idiomatic phrase ("the bottom of") that the regex over-matched?** Accept; this is the validator's known false-positive surface.

- [ ] **Step 4: Full sweep against the pack**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations --genre-packs-root ../sidequest-content/genre_packs/caverns_and_claudes 2>&1 | tail -10
```
Expected: 0 errors.

- [ ] **Step 5: Run server suite**

```bash
just server-test
```
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/cartography.yaml
git commit -m "feat(54-5): the_dropmouth entities[] backfill

7 entities — collar/rope/shaft/cold_draught as location_feature with
descent-relevant affordances, atmospheric phrases as flavor_only. The
cold_draught is deliberately real_object (mechanically significant
per prose — doesn't vary with wind because it doesn't come from wind
— hooked for Diamonds-and-Coal promotion when players investigate
its source)."
```

---

### Task 4: Verify nothing in `caverns_and_claudes` regresses

Beneath Sünden currently has no `rooms/<id>.yaml` files — the procedural rooms are generated at runtime (per ADR-106). The validator should walk zero room files and emit only the two regions' results.

- [ ] **Step 1: Confirm room-file count**

```bash
find sidequest-content/genre_packs/caverns_and_claudes/worlds -name "*.yaml" -path "*/rooms/*" | wc -l
```
Expected: `0` (procedural rooms only persist into saves, not into the content tree). If it's non-zero, those are pre-authored fixture rooms — they need `entities[]` too. The most likely candidate is the test fixture seeded in Story 54-2's Task 3 — but that lives under `sidequest-server/tests/`, not the content tree, so it shouldn't appear here.

- [ ] **Step 2: End-to-end validator across all packs**

```bash
cd sidequest-server && uv run python -m sidequest.cli.validate locations 2>&1 | tail -5
```
Expected: 0 errors across every authored pack (assuming 54-4 also landed). Warnings allowed.

- [ ] **Step 3: If errors elsewhere — STOP**

If errors fire on packs other than `caverns_and_claudes` or `tea_and_murder`, that's a sibling-pack drift unrelated to this story. Don't fix here; file the finding under the session's "Delivery Findings" section per the agent-behavior guide and let the owning story (or a separate cleanup story) handle it.

---

### Self-review checklist

- [ ] Both surface regions (`ropefoot`, `the_dropmouth`) have an `entities:` block.
- [ ] `the_kept_fire`, `the_rope`, `the_collar`, `the_cold_draught` are `real_object` with `location_feature` bindings.
- [ ] No `npc` bindings (no `npcs.yaml` for this world; collective camp folk are `yes_and` instead).
- [ ] `pf validate locations --genre-packs-root .../caverns_and_claudes` reports 0 errors.
- [ ] Pack-level `generic_allowlist` is restrained — common atmospheric nouns only, with explicit exclusions for `the rope` and `the kept fire` (those resolve through the region manifest).
- [ ] No new `rooms/<id>.yaml` files added to the content tree — Sünden Deep stays procedural per ADR-106 Plan 7.
- [ ] `just server-test` green.

### Dependencies / handoff

- **Blocked by:** 54-2, 54-3.
- **Unblocks:** Runtime play of beneath_sunden's surface with the resolver (54-6). The descent into the procedural deep gets its manifest from cookbook composition in 55-1.
- **Out of scope:** Authoring entities for procedurally-materialized rooms (55-1 owns), minting an NPC id for the_winch_keeper (kept as yes_and; if he becomes load-bearing in playtest, a follow-up authoring story can mint him).
