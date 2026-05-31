---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-31: space_opera doctrine — move named/backstoried cultures from genre to world layer, genre ships generic culture slots (Crunch in Genre, Flavor in World)

## Business Context

Project doctrine is **"Crunch in the Genre, Flavor in the World"**: the genre pack ships
mechanics (slots, rules, resolution), and named/backstoried flavor lives per-world (CLAUDE.md;
epic 74). The `space_opera` GENRE pack currently violates this — its `cultures.yaml`
declares five **named, backstoried** cultures (Hegemonic, Frontier, Voidborn, Synthetic,
Xeno) whose descriptions reference specific fiction ("Barrayaran aristocracy", "Firefly's
border moons", "Expanse's belters"). That genre-tier flavor is wrong for divergent worlds:
`perseus_cloud` is a post-GHE feudal sector with Spacer/Thari/Yulan cultures, `coyote_star`
runs Broken Drift / Free Miners / Voidborn / Tsveri / Hegemonic, `aureate_span` runs a
baroque corona-megastation roster — none of which are "Barrayaran officers."

This is the same migration epic 74 ran (genre = mechanics only) and the same move 71-32/71-33
made for scenarios (pack → world tier). The correctness win: an NPC's culture tag resolves
against the SAME set the table actually authored, instead of a one-size-genre default. This
is also a **Jade requirement** made concrete — she authors `perseus_cloud` cultures as
content; the genre must ship generic slots a world fills, so authoring named cultures never
requires an engine change. The bug this prevents already bit once: genre name "Hegemonic"
handed to `perseus_cloud` (which only knows spacer/thari/yulan) seeded **0 NPCs**
(`pack.py:262-265`, session 894, 2026-05-29).

## Technical Guardrails

**The genre-tier flavor to move (content):**
- `sidequest-content/genre_packs/space_opera/cultures.yaml` — 5 named cultures:
  `Hegemonic` (`:1`), `Frontier` (`:48`), `Voidborn` (`:81`), `Synthetic` (`:123`),
  `Xeno` (`:173`). Each carries name + backstoried `description` + name-generation `slots`
  / `person_patterns` / `place_patterns`. These are flavor and must not remain at genre tier.

**Where named cultures already live per-world (the destination shape — precedent exists):**
- `worlds/perseus_cloud/cultures/` — `spacer.yaml`, `thari.yaml`, `yulan.yaml` (one
  `Culture` per file, `name:` + `summary:` + `description:` + `slots:` + patterns).
- `worlds/coyote_star/cultures/` — `broken_drift`, `free_miners`, `hegemonic`, `tsveri`,
  `voidborn`.
- `worlds/aureate_span/cultures/` — `cinder_collective`, `crystalline_choir`, `makhani`,
  `span_aristocracy`, `vaal_kesh`.
  **All three live `space_opera` worlds already ship their own `cultures/` dir.** So the
  world tier is already populated; the refactor is primarily *removing* the named cultures
  from the genre tier and confirming the worlds remain self-sufficient.

**How the loader layers genre vs world (the resolution seam — already correct):**
- `sidequest-server/sidequest/genre/loader.py` — genre cultures loaded at `:1218-1220`
  (optional: `_load_yaml_raw_optional(path / "cultures.yaml")`). World cultures loaded at
  `:895-914`: a world `cultures/` DIR is globbed (one `Culture` per `*.yaml`, art-pipeline
  visual-token overlays without a `name` key are skipped, `:902-906`), else a single
  `cultures.yaml` list.
- `sidequest/genre/models/pack.py:267` `effective_cultures(world)` — **world REPLACES
  genre**: *"A world that declares its own cultures/archetypes REPLACES the genre set; a
  world that declares none inherits the genre's."* Returns `(cultures, source)` where source
  is `"world"` when the world supplies a non-empty list, else `"genre"` (`:275-277`). The
  docstring explicitly cites the SOUL "Crunch in the Genre, Flavor in the World" doctrine
  and the perseus seeding bug.
- This is the SINGLE resolution every consumer must use — namegen and `pregen.seed_manual`
  both call it (`pack.py:259-265`). Verify no consumer reads raw `pack.cultures` instead.
- `Culture` model: `sidequest/genre/models/culture.py:32` (`name`, `summary`, `description`,
  `slots: dict[str, CultureSlot]`).

**What "generic culture slots" means at genre tier:**
- Per epic 74's loader refactor (74-1), genre flavor became OPTIONAL — the genre may ship
  NO `cultures.yaml` at all and worlds become authoritative. The cleanest doctrine-true end
  state is: genre `cultures.yaml` either absent, or reduced to generic *mechanical* slot
  scaffolding with no named/backstoried culture. The story's AC ("genre ships generic
  culture slots only") and the doctrine assertion ("no named/backstoried cultures remain at
  genre tier") drive which of these the implementation lands on — confirm with the 74-1
  loader behavior (genre flavor optional, world required-but-loud).

**Precedent to mirror (same pattern, same epic):**
- 71-33 / 71-32 migrated scenarios pack→world via `git mv` with the loader already
  discovering world-tier dirs by location. 74-1 made genre flavor optional and world flavor
  authoritative. This story is the culture instance of the identical migration.

**Do NOT touch:** the `effective_cultures` resolution logic (it already does the right
thing), other genre packs' cultures, world `cultures/` dirs that are already complete
(verify, don't rewrite), or the namegen corpus/Markov engine (ADR-091).

## Scope Boundaries

**In scope:**
- Remove the named/backstoried cultures (Hegemonic, Frontier, Voidborn, Synthetic, Xeno)
  from the `space_opera` GENRE `cultures.yaml` — leaving the genre tier with only generic
  culture slots (or no `cultures.yaml`, per the 74-1 optional-genre-flavor end state).
- Ensure each live `space_opera` world still binds its named cultures correctly after the
  genre cultures are gone — i.e. no world was silently relying on genre-tier `Hegemonic` et
  al. `coyote_star` already ships its own `hegemonic.yaml`/`voidborn.yaml`, so its names are
  world-local; verify the same for `perseus_cloud` and `aureate_span`.
- A test asserting **no named/backstoried cultures remain at genre tier** (the doctrine
  invariant) and that world loading still resolves the named cultures via
  `effective_cultures(world)` with `source == "world"`.

**Out of scope:**
- Authoring NEW per-world cultures — the three live worlds already have their `cultures/`
  dirs; this is a removal-from-genre + verification, not new flavor authoring. If a world is
  found to be genuinely relying on a genre culture (no world equivalent), porting that one
  culture into the world is in scope as a consequence; a broad re-authoring is not.
- Other genre packs (this is `space_opera`-only).
- Changing `effective_cultures` / the loader layering logic (already doctrine-correct).
- The namegen corpus files / Markov engine.

## AC Context

**AC1 — genre pack ships generic culture slots only.**
- After the refactor, the `space_opera` genre `cultures.yaml` (if present) contains no
  named/backstoried culture. Test: load the genre pack WITHOUT a world and assert
  `pack.cultures` (the genre-tier list) contains none of `Hegemonic`, `Frontier`,
  `Voidborn`, `Synthetic`, `Xeno` (and ideally is empty or contains only generic slot
  scaffolding). This is the "no named cultures remain at genre tier" doctrine assertion.
- Edge: the loader treats genre `cultures.yaml` as optional (74-1) — removing the file
  entirely must NOT raise `GenreLoadError`. A test loading the pack with the file absent
  must succeed.

**AC2 — named cultures live under `worlds/<world>/` and world loading still binds them.**
- `effective_cultures("perseus_cloud")` returns the perseus world cultures (Spacer, Thari,
  Yulan) with `source == "world"`. Same for `coyote_star` (Broken Drift, Free Miners,
  Hegemonic, Tsveri, Voidborn) and `aureate_span` (its five). Test: for each live world,
  call `pack.effective_cultures(world)` and assert the returned names match the world's
  `cultures/` dir AND `source == "world"`.
- Edge: a world's `cultures/` dir may contain art-pipeline visual-token overlays without a
  `name` key — the loader skips these (`loader.py:902-906`). The test must assert on
  name-generation `Culture`s only, matching loader behavior.
- Edge / regression guard: the perseus seeding bug (`pack.py:262-265`) — a culture tag
  handed to seeding must resolve against the world set. A test that seeds a `perseus_cloud`
  NPC and asserts a non-zero seed count (culture resolves) guards against re-introducing the
  0-NPC failure.

**AC3 — no named/backstoried cultures remain at genre tier (the doctrine invariant test).**
- A standalone assertion: load `space_opera` genre-only and assert the genre culture list is
  free of named/backstoried entries. This is the test the AC explicitly calls for and the
  durable doctrine guard for future content edits.

## Assumptions

- **The three live worlds are already self-sufficient.** `perseus_cloud`, `coyote_star`,
  and `aureate_span` each already ship a `cultures/` dir with named cultures, so removing
  genre cultures should not orphan any world. This must be VERIFIED per world before
  deletion — if a world was relying on a genre name (e.g. an NPC tagged `Hegemonic` in a
  world that lacks a `hegemonic.yaml`), porting that culture into the world is the fix, not
  reverting the genre removal. `coyote_star` shipping its own `hegemonic.yaml`/`voidborn.yaml`
  is evidence the world-local pattern is already the norm.
- **`effective_cultures` is the single resolution path** and all consumers (namegen,
  `pregen.seed_manual`) already route through it (`pack.py:259-265`). If a consumer is found
  reading raw `pack.cultures` and breaks when it empties, that is a wiring fix in scope —
  log it as a Design Deviation.
- **Genre-tier culture flavor is optional post-74-1.** The loader does not hard-require genre
  `cultures.yaml`. If 74-1's optional-genre-flavor change is not yet merged on this branch,
  removing the file may fail load — confirm 74-1 (or its loader change) is present first;
  if not, that is a dependency to flag to SM.
- **Doctrine end-state is "no named cultures at genre," with generic slots optional.** The
  AC says "generic culture SLOTS (mechanics)." If review decides the cleanest doctrine-true
  state is *no* genre `cultures.yaml` at all (worlds fully authoritative, matching 74-1),
  that satisfies the AC; a residual generic-slot scaffold is acceptable but not required.
  Confirm the intended end-state with the epic-74 doctrine owner during design.

If any assumption proves wrong (a world depends on a genre culture; a consumer bypasses
`effective_cultures`; 74-1 isn't present), log a Design Deviation and notify SM before
widening scope.
