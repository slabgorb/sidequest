---
id: 120
title: "Genre/World Flavor Boundary — Mandatory-File Loader Contract, Mechanics-in-Genre, Flavor-in-World"
status: superseded
status_rationale: "Flavor-in-world half stands and is subsumed by ADR-140; the 'mechanics-in-genre' half (archetype templates / classes / spell catalogs / mechanical tropes as genre-tier scaffolding) is invalidated — cast and catalog are world-tier per ADR-140."
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: 140
related: [3, 4, 79, 140]
tags: [core-architecture]
implementation-status: retired
implementation-pointer: "Doctrine superseded by ADR-140 (genre=rulebook, world owns cast/catalog). The flavor-in-world loader code (genre-tier flavor optional, world-authoritative theme/audio/visual_style, per-load OTEL spans) remains live under ADR-140's umbrella: sidequest-server/sidequest/genre/loader.py (_load_single_world, _emit_world_flavor_loaded)."
---

# ADR-120: Genre/World Flavor Boundary

> **Superseded by [ADR-140](140-genre-rulebook-world-cast-catalog.md) (2026-06-06).**
> The *flavor-in-world* decision below (D1–D5) is correct and remains live — it
> is subsumed by ADR-140. But ADR-120's **"mechanics-in-genre"** framing drew the
> crunch boundary in the wrong place: it kept declaring **archetype templates,
> classes/callings, spell catalogs, and "mechanical" tropes** as genre-tier
> scaffolding (see §"Invariants/Contracts" below). Epic 94 invalidated that:
> those are **cast and catalog**, which are **world-tier** and must be
> homebrewable without engine changes. The corrected doctrine — *the genre tier
> is the RULEBOOK only; the world tier owns the cast and catalog* — is ADR-140.
> Read this ADR for the flavor boundary; read ADR-140 for the cast/catalog
> boundary that supersedes the "mechanics-in-genre" claim.

> **Documents a system already live in code, mid-migration.** Epic 74 story 74-1
> shipped (`completed: 2026-05-31`) the loader refactor that moved the
> genre/world flavor boundary into the pack loader — genre-tier flavor files
> went optional, world theme became required-with-loud-fail, and a per-load OTEL
> span was added — without a governing ADR. This record closes that
> architecture-of-record gap and states what the decision *was*, including the
> transitional fallback that 74-2..74-4 will retire.

## Context

SideQuest's doctrine is **Crunch in the Genre, Flavor in the World** (SOUL.md,
ADR-003 §"Genre vs world"): a genre is the rulebook (mechanics, archetypes, tone
axes), a world is the campaign setting (factions, geography, named NPCs,
legends, lore), and one genre can host many worlds. ADR-003 codified the file
layout under that doctrine but, in practice, treated several *flavor* files as
load-bearing at the **genre** tier — its "one file per concern" principle and
the loader hard-required genre-root `lore.yaml`, `theme.yaml`, `audio.yaml`,
`archetypes.yaml`, `cultures.yaml`, and `visual_style.yaml`.

Two facts broke that arrangement (Keith, 2026-05-30, recorded in
`sprint/epic-74.yaml` and `genre-pack-content-audit.md`):

1. **Worlds diverge too hard for shared genre flavor to be meaningful — or even
   correct.** `spaghetti_western` genre tropes authored for the Mexican border
   (`dust_and_lead`) are simply *wrong* for 1878 Pittsburgh (`the_real_mccoy`)
   or the 1850s Sixth Ward (`five_points`). A genre-tier flavor file is, at
   best, redundant with every world that overrides it and, at worst, a source of
   setting-incorrect bleed. The content audit
   (`CONTENT_AUTHORING_CHECKLIST.md` §A) found that **every** live world already
   carries a full `lore.yaml`, making the genre-root copy redundant in all ten
   packs.

2. **The genre tier should hold only mechanics.** Rules, archetype *templates*,
   tone/voice axes, conlang morphemes and culture-naming rules, mechanical
   tropes — anything genre-generic with no proper nouns. Everything that
   presumes one fictional setting (history, legends, named factions/places/cast,
   dated events, the world's theme palette, its audio, its visual prompts)
   belongs to the world.

But the loader stood in the way. Per the checklist's "Loader blocker" note,
genre-root `lore.yaml` (and its siblings) loaded through the **required**
`_load_yaml` path — *"Required; raises GenreLoadError on any failure (file
missing…). No silent fallbacks."* (`loader.py`). **Deleting any genre-root
flavor file made the pack fail to load.** So the boundary could not be enforced
content-side until the *consumer* (the loader) was repointed. That is the work
Epic 74 governs, and story 74-1 is the loader half of it.

This created a sequencing problem that must honor **No Silent Fallbacks**: the
live packs *still ship* genre-tier flavor today, and worlds are not yet all
migrated. The loader cannot simply drop the genre files (worlds would lose their
theme/audio mid-flight) nor silently invent a default. The decision below is the
transitional contract that lets the boundary be enforced *now* while the
per-world migration (74-2..74-4) catches up — loudly, never silently.

## Decision

**The genre pack tier holds only mechanics; the world tier is the authoritative
source for all flavor.** Concretely, in the pack loader
(`sidequest-server/sidequest/genre/loader.py`):

### D1 — Genre-tier flavor is now OPTIONAL (was required)

The genre-root flavor files load through the `*_optional` helpers instead of the
required `_load_yaml`. `load_genre_pack` (`loader.py–1221`) now reads:

- `lore = _load_yaml_optional(path / "lore.yaml", Lore)` (`:1194`)
- `theme = _load_yaml_optional(path / "theme.yaml", GenreTheme)` (`:1195`)
- `archetypes_raw = _load_yaml_raw_optional(path / "archetypes.yaml")` (`:1196`)
- `visual_style = _load_yaml_optional(path / "visual_style.yaml", VisualStyle)` (`:1211`)
- `audio = _load_yaml_optional(path / "audio.yaml", AudioConfig)` (`:1215`)
- `cultures_raw = _load_yaml_raw_optional(path / "cultures.yaml")` (`:1218`)

A genre pack that ships none of these is a valid **mechanics-only pack**.
Absence yields `None`/empty — but this is *not* a silent fallback: the
`*_optional` helpers return `None` **only when the file is absent**; an existing
file that is malformed or schema-invalid still raises `GenreLoadError`
(`_load_yaml_optional`, `loader.py–120` — "If present, failure is still
loud."). Mechanics files stay required: `rules.yaml`, `tropes.yaml`,
`progression.yaml`, `axes.yaml`, `prompts.yaml`, `char_creation.yaml` still load
through `_load_yaml`/`_load_yaml_raw` and fail loud on absence.

### D2 — The world tier loads its own flavor and is authoritative

`_load_single_world` (`loader.py`) reads the world's own flavor surfaces
**raw** (free-form hard-overrides, not the strict genre schemas — e.g.
`five_points/audio.yaml`):

- `visual_style = _load_yaml_raw_optional(world_path / "visual_style.yaml")` (`:946`)
- `world_theme = _load_yaml_raw_optional(world_path / "theme.yaml")` (`:956`)
- `world_audio = _load_yaml_raw_optional(world_path / "audio.yaml")` (`:957`)

World `lore.yaml` is *required* at the world tier
(`lore = _load_yaml(world_path / "lore.yaml", WorldLore)`, `:891`); world tropes,
cultures, archetypes, and history load optionally and override/inherit the genre
templates (trope inheritance via `resolve_trope_inheritance`, `:936`). The
assembled `World` carries `theme=effective_theme`, `audio=world_audio`,
`visual_style=visual_style` (`loader.py–1096`).

### D3 — Theme is world-required, with a loud fail

Theme resolution is the one flavor surface elevated to a hard invariant, because
a themeless client (connect-time chrome + reference pages) is *broken*, not
merely plain. The effective theme is the world's own theme if present, else the
genre theme as a transitional fallback (`effective_theme`, `loader.py–978`):

```
effective_theme = world_theme if world_theme is not None else genre_theme
```

After all worlds load, a **pack-level invariant** (`loader.py–1367`) walks
every non-draft world and raises `GenreLoadError` — naming the world and the
missing `worlds/<slug>/theme.yaml` — if it resolved no theme from *either* tier.
The check lives at the pack level (not inside `_load_single_world`) deliberately
so that direct `_load_single_world` unit fixtures can stay themeless, while every
real pack enforces "every world must supply or inherit a theme."

### D4 — Genre flavor is a *transitional* fallback, not a parallel tier

The genre theme is passed down only as a fallback during the migration
(`_load_single_world(..., genre_theme=theme)`, `loader.py`). Two runtime
shapes coexist behind the boundary — a raw `dict` from the world tier or a typed
`GenreTheme` from the genre fallback — and `World.theme` is deliberately typed
`GenreTheme | dict[str, Any] | None` (`genre/models/pack.py`) so consumers
**branch on the type** (`isinstance(world.theme, GenreTheme)`) rather than
assume one shape. `World.audio` is `dict[str, Any] | None` (`pack.py`): a raw
dict when the world authors one, `None` when genre audio still serves. This dual
shape is a known transitional cost (74-4 hardens it), not a permanent design.

### D5 — Each world-tier flavor load emits an OTEL span

Per the project OTEL Observability Principle (Keith's lie detector; ADR-031 /
ADR-090 / ADR-103), the GM panel must be able to prove the world-tier read
*fired* rather than the engine improvising from a genre default.
`_emit_world_flavor_loaded` (`loader.py–850`) publishes a `state_transition`
watcher event (component `genre`) for each flavor surface the world actually
authors — mirroring the existing `world_items` and `genre_pack` spans:

```
for field_name, value in (
    ("world_theme", world_theme),
    ("world_audio", world_audio),
    ("world_visual_style", visual_style),
):
    if value is not None:
        _emit_world_flavor_loaded(field_name, world_slug=..., source=world_path)
```

The span carries `field`, `op: "loaded"`, `world_slug`, and `source` (the
resolved `<field>.yaml` path). Absence emits no span — there is nothing to
prove — and absence is never fabricated into a fake load.

## Invariants / Contracts

- **Mechanics-in-genre, flavor-in-world.** Genre root = mechanical + genre-generic
  scaffolding only (rules, archetype templates, tone/voice axes, naming rules,
  mechanical tropes). World = all fictional lore. A `lore.yaml` at genre root is
  redundant by design and slated for deletion;
  `CONTENT_AUTHORING_CHECKLIST.md` §"Governing principle" states *"A `lore.yaml`
  at genre root is always wrong."*
- **Theme is world-required, loud-fail.** Every non-draft world must resolve a
  theme from its own tier or (transitionally) the genre fallback; a world that
  resolves neither raises `GenreLoadError`, named (`loader.py–1367`). No
  silent themeless world.
- **Genre flavor = transitional fallback.** Genre-tier theme/audio/lore/etc. are
  optional and serve only until the world tier owns them; they are not a
  permanent second tier. The `genre_theme` parameter exists to be removed.
- **Absence ≠ silence.** `*_optional` returns `None` only on a missing file; a
  present-but-broken file still raises. Mechanics files remain required.
- **World-flavor loads are observable.** Every world theme/audio/visual_style
  load emits a `state_transition` OTEL span (D5); a missing world flavor file
  emits no span (and 74-4 adds a weather-absence span for the one surface where
  silence would otherwise be ambiguous).

## The phased migration (Epic 74)

The boundary cannot be enforced in one cut: the live packs still ship genre
flavor, and consumers (reference-chrome, the render pipeline, the audio backend)
still read it. The epic stages the work so each cut lands on stable ground.

- **74-1 — Loader refactor (DONE, 2026-05-31).** What this ADR documents: genre
  flavor → optional (D1); world tier loads + is authoritative (D2); theme
  world-required loud-fail (D3); transitional `genre_theme` fallback + dual-shape
  `World.theme`/`World.audio` (D4); per-load OTEL span (D5). Review note on
  record: a banned `inspect.getsource` wiring test was introduced and must be
  removed (covered by behavior tests already); `World.theme`/`audio` annotated
  explicitly. *No genre flavor file is deleted by 74-1* — the loader merely
  stops requiring it.
- **74-2 — Repoint flavor consumers to the world tier.** Reference-chrome, the
  render pipeline, and the audio backend still read genre flavor; this repoints
  them at the world tier and fixes a `reference_renderer` 500 risk **before** any
  genre flavor file is deleted.
- **74-3 — Author world-tier lore for every live world.** Guarantees no
  un-migrated world is left with an empty `LoreStore` once genre lore is
  deletable; unblocks the genre-`lore.yaml` deletion.
- **74-4 — World-flavor hardening.** `isinstance` shape-guard on the raw world
  `theme`/`audio` (closing the dual-shape cost from D4), a weather-absence OTEL
  span, and removal of the dead `seed_lore_from_genre_pack` path.

Only **after** 74-2 (consumers repointed) and 74-3 (world lore authored) is it
safe to **delete** the remaining mandatory genre-tier flavor files per the
`CONTENT_AUTHORING_CHECKLIST.md` §A/§B tables (genre-root `lore.yaml` across all
ten packs; flavor smuggled into `seed_tropes.yaml`, `weather.yaml`, etc.). The
transitional `genre_theme` fallback (D4) is removed when no live world depends on
it.

## Consequences

**Positive:**

- A genre is genuinely the rulebook and a world genuinely the setting; flavor
  cannot leak across worlds of the same genre (the `the_real_mccoy` vs
  `dust_and_lead` problem disappears).
- Mechanics-only genre packs are now expressible — a pack can ship rules + axes +
  tropes with zero flavor and remain valid, which is what the world tier needs
  to be the single flavor source.
- World authors (Jade, Keith, future table members) get one authoritative place
  for theme/audio/lore/cultures/tropes per world, served by the loader where it
  is actually read — supporting the "authoring without engine code" requirement.
- Every world flavor load is provable in the GM panel (D5); a stale or missing
  world theme fails loud rather than silently serving a genre default.

**Negative / risks:**

- **Mid-migration dual representation.** Until 74-2..74-4 land, genre flavor and
  world flavor coexist, and `World.theme`/`World.audio` carry two runtime shapes
  (dict XOR typed). Consumers must branch on type; an unguarded attribute access
  on a raw-dict theme is a latent bug (74-4's `isinstance` shape-guard closes
  this).
- **Deletion is gated, not free.** Deleting genre flavor before 74-2 repoints
  consumers would 500 the reference renderer / starve the audio backend. The
  checklist's "Loader blocker" and the consumer repoint must precede any file
  removal — the boundary is enforced in the loader now, but the content cleanup
  waits on the consumer cutover.
- **Transitional fallback can mask un-migrated worlds.** A world with no
  `theme.yaml` still loads today via the genre theme; once the genre theme is
  deleted it will fail loud. 74-3 (author world lore/theme) must precede that
  deletion or the loud-fail surfaces in play.

## Alternatives considered

- **One-shot cut: delete genre flavor + make world flavor required in a single
  change.** Rejected: live packs ship genre flavor and consumers still read it;
  a one-shot cut would 500 the reference renderer and break un-migrated worlds.
  The phased loader-first / consumers-next / content-last sequence (Epic 74) is
  the de-risked path.
- **Silent default theme when a world authors none.** Rejected outright — a
  built-in default theme is a silent fallback (the exact failure mode CLAUDE.md
  forbids). The loud `GenreLoadError` naming the world (D3) is the chosen
  behavior.
- **Keep genre flavor as a permanent co-equal tier (layer world over genre).**
  Rejected: the divergence argument (D1.1) shows genre flavor is frequently
  *wrong* per-world, not merely overridable. A permanent genre flavor tier
  invites setting-incorrect bleed and keeps redundant files alive forever.
- **Promote `theme.yaml` to a required world file in `pack_schema.yaml` and stop
  there.** Insufficient — the schema already lists `theme.yaml` under
  `world.required_files`, but the *loader* is the enforcement point, and it was
  hard-requiring the genre copy. The decision had to move the loader, not just
  the schema doc.

## Reconciliation with ADR-003, ADR-004, ADR-079

- **ADR-003 (Genre Pack Architecture) — partially invalidated.** ADR-003's
  "Genre vs world" section already named the SOUL split ("Crunch in the Genre,
  Flavor in the World"), but its design enshrined flavor files at the genre tier:
  Principle 2 *"One file per concern — each YAML file maps to one subsystem,"* its
  Rust `GenrePack` sketch carries `lore: LoreConfig` as a struct field, and the
  loader hard-required genre-root `lore.yaml`/`theme.yaml`/`audio.yaml`/etc. **What
  changes:** those genre-tier flavor files are now *optional* (D1) and the world
  tier is *authoritative* for flavor (D2); the genre-tier `lore`/`theme`/`audio`
  are no longer load-bearing "one file per concern" entries — they are transitional
  fallbacks slated for deletion. ADR-003's *mechanics* layout (the
  `pack.yaml`/`rules.yaml`/`tropes.yaml`/`prompts.yaml`/`archetypes.yaml`
  always-required core) is **unchanged**; only the flavor files move tiers. ADR-003
  is not superseded — its filesystem-is-source-of-truth stance and its genre/world
  axis survive; this ADR refines *which tier owns flavor* and flips the
  mandatory/optional status of the genre flavor files.
- **ADR-004 (Lazy Genre Binding) — unaffected, reinforced.** ADR-004's
  connect-time `SESSION_EVENT { genre, world }` bind is the exact moment the
  effective theme/audio/visual_style are resolved (world tier first, genre
  fallback second per D3/D4). Lazy binding loads the pack — including its worlds
  and their flavor — on first connect; this ADR only changes *where within that
  load* flavor comes from. No binding-time behavior changes.
- **ADR-079 (Genre Theme System Unification) — compatible; "genre" is a tier
  label, not a source claim.** ADR-079 makes genre `client_theme.css` the single
  CSS source of truth on the *client* and kills the JS bridge. That is orthogonal
  to *which server tier authored the theme tokens*: ADR-079 governs how the UI
  consumes a `client_theme.css`; ADR-120 governs whether that theme is resolved
  from `worlds/<slug>/theme.yaml` (authoritative) or the genre `theme.yaml`
  (transitional fallback). The world tier may carry its own
  `worlds/<slug>/client_theme.css` (`World.world_client_theme_css`,
  `pack.py`), consumed by ADR-079's `:root[data-genre]` mechanism unchanged.
  As the migration completes, the CSS ADR-079 ships is increasingly world-sourced;
  the unification contract on the client is untouched.
