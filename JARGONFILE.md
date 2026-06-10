# JARGONFILE.md — SideQuest

> The private language of this project, written down so a tired engineer at 2am
> doesn't have to reverse-engineer it from a variable name.
>
> **This file is a map, not the territory.** When a definition here disagrees
> with `SOUL.md`, an ADR, or the code, *those win* — fix the entry. Each term
> cites where it's actually defined; go there for the authoritative version.
> Terms drift; ADRs marked `partial`/`drift`/`deferred` in `CLAUDE.md` are
> accepted-but-not-fully-live, so treat their jargon as aspirational until the
> code agrees.

---

## RPG theory — the Forge "Big Model" vocabulary

SideQuest is built on tabletop design theory, and its mission statement
(`SOUL.md` `<purpose>`) is written in it. If these read as gibberish, that's
why.

- **Story Now** — Design stance where the story is produced *during* play from
  player choices, not pre-authored and revealed. The opposite of railroading.
  (`SOUL.md`)
- **Fortune-in-the-Middle** — Resolution where the dice are rolled *before* the
  fiction is fully narrated, so the mechanical result shapes what happened
  rather than merely confirming a pre-decided outcome. SideQuest resolves
  mechanically, then narrates to fit. (`SOUL.md`)
- **Bang** — A situation that forces a player to make a meaningful decision.
  SideQuest treats its **Confrontation Defs as a Bang catalog** — pre-authored
  pressure points the narrator can deploy. (`SOUL.md`)
- **Illusionism** — The GM cheat of faking player agency: pretending choices
  matter when the outcome was fixed. SideQuest considers this the cardinal sin
  and uses **OTEL as an Illusionism detector** — telemetry proves the engine
  actually mutated state instead of the narrator just *saying* it did.
  (`SOUL.md`; see **the lie detector**)
- **El Dorado** — The mythical perfect freeform RPG that never needs rules.
  SideQuest's thesis is that you *escape El Dorado through structural support*:
  mechanical scaffolding is what makes freeform play actually work. (`SOUL.md`)

## The narrator doctrine (SOUL.md design laws)

These are the named rules every narrator-facing decision is weighed against.

- **The Zork Problem** — Every prior digital RPG constrains the player to a
  finite verb set (parser keywords, combat menus, dialogue trees). SideQuest's
  natural-language narrator removes that ceiling: the player can attempt
  anything they can articulate. *Never reduce player input to keyword matching.*
  This is the reason the system exists. (`SOUL.md`)
- **Diamonds and Coal** — Detail signals importance; match narrative detail to
  narrative weight. Coal becomes a diamond when players choose to polish it.
  (`SOUL.md`, **ADR-014**)
- **Baited hook** — A detail placed *with intention* to invite engagement: an
  NPC who lingers, a locked door, a name said twice. When the player bites, the
  detail earns promotion to canon. (`SOUL.md`)
- **Overbaited** — Lavishing description on something with no payoff — a
  Chekhov's-gun misfire that promotes coal that should have stayed coal. Scale
  the bait to what's actually on the line. (`SOUL.md`)
- **Untaken bait** — A real hook the player swam past. Don't yank the rod; let
  it stay in the water and resurface naturally. (`SOUL.md`)
- **Yes, And** — When a player introduces something that fits genre truth and
  grants no mechanical advantage, canonize it. Emerging from a suspension pod
  *creates* a suspension-pod facility. The MUSH principle. (`SOUL.md`)
- **Rule of Cool** — Counterweight to genre truth: lean toward allowing creative
  inventions even if implausible. *The gate is mechanical advantage, not
  plausibility.* (`SOUL.md`)
- **Monkey's Paw / the genie grants it literally** — The consequence engine for
  power-grab inventions. The game says yes, then the wish curls: the plasma
  rifle fires once, at the worst moment, at the thing you needed alive.
  (`SOUL.md`; **ADR-041** Genie Wish / Consequence Engine)
- **Cut the Dull Bits** — Chekhov's Gun for scenes. If a scene doesn't force a
  decision, reveal something, or raise stakes — smash-cut past it. "You arrive
  in Montmartre. It's raining." (`SOUL.md`)
- **Crunch in the Genre, Flavor in the World** — The genre is the rulebook
  (mechanics, archetypes, tone); the world is the campaign setting (factions,
  geography, named NPCs). Swap the world, keep the rules. (`SOUL.md`)
- **Tabletop First, Then Better** — Design as a tabletop DM would, then exploit
  the medium where it beats tabletop (per-player private info, simultaneous
  map+narration+sound, persistent visual state). (`SOUL.md`)
- **The Test** — The agency tripwire: *if a response includes the player doing
  something they didn't ask to do, it's wrong.* (`SOUL.md`)

## Engine & domain nouns

- **Genre Pack** — The unit of rules + flavor: a directory of YAML (+ audio,
  images, lore) defining a genre (e.g. `caverns_and_claudes`, `space_opera`,
  `tea_and_murder`). Single source of truth lives in
  `sidequest-content/genre_packs/`. (**ADR-003**, **ADR-004**)
- **World** — A campaign setting *inside* a genre pack (e.g. `beneath_sunden`).
  One genre hosts many worlds. See **Crunch in the Genre**. (`SOUL.md`)
- **Trope** — A genre-defined narrative pattern with a lifecycle that ticks
  forward and fires escalation beats at progression thresholds. (**ADR-018**)
- **Confrontation** — A structured, genre-defined encounter (combat, chase,
  negotiation, duel, dogfight, trial, ritual) resolved via beat selection and
  state deltas. The mechanical spine. **A confrontation requires an Other** —
  it must have an opponent seated at instantiation, or it ends. (**ADR-033**,
  **ADR-116**)
- **Beat** — A selectable mechanical+narrative outcome within a confrontation,
  keyed to a threshold and producing deltas. `beat_selections` firing is the
  signal that the mechanical engine engaged (and is the wrong success metric for
  social-first packs — see **Victoria**). (**ADR-018**, **ADR-033**)
- **beat_filter.py (name collision)** — Two unrelated files share this name; they
  are *not* duplicates. Daemon `sidequest_daemon/renderer/beat_filter.py` decides
  *render-worthiness* (which narrative beats merit an image). Server
  `sidequest/game/beat_filter.py` decides *confrontation beats* (the mechanical
  outcomes above). Same word, different "beat" — don't refactor one expecting the
  other.
- **Ablative HP** — The current lethality substrate (reintroduced **2026-05-25**,
  **ADR-114**): HP is the personal vitality track beneath the mechanical dials,
  ablated by damage. *Content YAML already carries HP* — the materializer
  translates it; don't discard it. (`docs/superpowers/specs/2026-05-25-swn-crunch-ablative-hp-design.md`)
- **EdgePool / Edge** — The *prior* damage model (**ADR-078**, superseded):
  Edge replaced HP for runtime entities. Now superseded by ablative HP; you'll
  still find Edge in older code and ADRs. Translate HP↔Edge at the
  **materialization seam**, never silently. (**ADR-078**, superseded by ADR-114)
- **Narrative Weight / drama weight** — A 0.0–1.0 scalar of story importance and
  drama intensity. Drives narration depth, render priority, and delivery mode.
  (**ADR-024**, **ADR-080**)
- **Disposition** — A clamped numeric scalar of an NPC's attitude toward the
  party, surfaced as a qualitative attitude (friendly/neutral/hostile). Copied
  from authored initial value at the materialization seam. (**ADR-020**)
- **OCEAN** — Big-Five personality model (Openness, Conscientiousness,
  Extraversion, Agreeableness, Neuroticism) driving NPC behavior; evolves live.
  (**ADR-042**)
- **Scenario** — A play-scripted mystery layer: clue graph, belief state, and
  gossip propagation across NPCs. (**ADR-053**)
- **POI** — Point of Interest: a named location rendered as a landscape image.
  One of the image-composition tiers (portrait / POI / illustration).
  (**ADR-086**)

## Pacing & drama

- **Dual-Track Tension** — The model behind drama weight. (**ADR-024**)
- **Gambler's Ramp** — The "quiet turn" track: monotony accumulates as nothing
  happens, raising tension because something *should*. (**ADR-024**)
- **Delivery mode** — How narration is paced by drama weight: roughly
  INSTANT (low) → SENTENCE (mid) → STREAMING (high). (**ADR-024**)
- **Pacing detection** — Automated turn-rhythm monitoring to avoid dead space.
  (**ADR-025**)

## Subsystems & architecture

- **The lie detector** — The **GM panel** (OTEL dashboard, `just otel`). Claude
  is excellent at writing convincing narration with *zero* mechanical backing;
  OTEL spans on every subsystem decision are the only way to tell whether the
  engine engaged or the narrator improvised. Every backend fix that touches a
  subsystem MUST emit watcher events. (`CLAUDE.md`, **ADR-031**, **ADR-090**)
- **Narrator gaslighting** — The doctrine of suppressing narrator improvisation
  by *materializing* creatures/NPCs/items into the game-state snapshot
  (`snap.npcs`, snapshot fields) so the narrator reports them rather than
  inventing them. Done via state injection, **not** by appending an "available
  list" to the prompt. (`world_materialization._apply_npc()`, **ADR-059**,
  **ADR-014**)
- **Materialization seam** — The runtime boundary where authored static content
  becomes live objects. The mandated place to translate B/X HP → runtime
  HP/Edge. Don't bury shape-mismatch bombs in per-site null guards here. (**ADR-007**, **ADR-022**)
- **Daemon** — `sidequest-daemon`, the Python media sidecar (image gen via
  Z-Image MLX, music via ACE-Step) reached over a Unix socket. (**ADR-035**,
  **ADR-070**, **ADR-095**)
- **Render tier** — Image-composition class (portrait / POI landscape /
  illustration) setting generation params. (**ADR-086**)
- **Anchor machinery** — The reference-page system that derives a stable
  in-page anchor URL (`#location-{slug}`) from an entity's name/region via
  `slugify` + `build_lore_url`. A link is emitted only when its slug is in the
  rendered manifest, so links never dangle. (`reference_renderer.py`)
- **Lore RAG** — Semantic-embedding retrieval of lore fragments to inject
  relevant world knowledge into narrator prompts. (**ADR-048**)
- **KnownFact** — Play-derived knowledge extracted from narration and persisted
  with provenance, then re-injected by relevance. (**ADR-100**)
- **Intent Router** — The mechanical-engagement spine that classifies player
  input toward the right subsystem. (**ADR-113**, partial)

## Multiplayer & turn coordination

- **Submit-and-wait barrier** — The MP turn primitive: no narration until
  *every* player submits, then one narrator call resolves the round. Built to
  never rush a slow typist (Alex). Peer action text *is* visible during the wait
  (collaborative default). (**ADR-036**)
- **Sealed-letter** — A name that means **three different things** — keep them
  apart when reading bug reports:
  1. **Submit-and-wait barrier** (above) — *live*.
  2. **Sealed visibility model** — hidden-submission for PvP; *reserved, not
     implemented* (the playgroup doesn't slip notes to the DM).
  3. **Sealed-letter resolution table** — simultaneous hidden-commit lookup for
     dogfight/magic; *live*. (**ADR-036**, **ADR-077**)
- **Shared-world / per-player state split** — Some state is the world's, some is
  per-player; perception filtering happens at the tool/broadcast layer.
  (**ADR-037**, **ADR-104**, **ADR-105**)
- **Deterministic session URL** — `/play/{date}-{world}-mp` *rejoins* an
  existing session. Two fresh-looking lobby flows on the same day land in the
  same session (drop-in). (memory: `project_session_id_dropin`)

## Genre-specific mechanics

- **Dogfight subsystem** — Fighter-vs-fighter encounter (space_opera) where
  pilots commit hidden maneuvers resolved via a sealed-letter cross-product
  table — a StructuredEncounter extension. (**ADR-077**)
- **Sünden Deep / Jaquaysed megadungeon** — `beneath_sunden`'s deep is
  *procedurally generated by design*, not authored. Contiguous edge-expansion
  attaches themed regions to the explored frontier ("Jaquaysed" = looped,
  multi-connected topology, after Jennell Jaquays). An empty map on descent is
  intended, not a bug. (**ADR-106**; memory: `project_beneath_sunden_unmapped_deep`)
- **Complication Ledger** — The record of complications/constraints the
  megadungeon generator curates as it expands. (**ADR-106**)

## Worldbuilding & naming

- **Conlang corpus** — Per-culture word lists in `sidequest-content/corpus/`
  feeding name generation; bind a culture to its source languages here.
  (**ADR-091**)
- **Markov naming** — Procedural names built from culture-specific Markov chains
  over the corpus, so names feel phonetically right per culture. (**ADR-091**)

## Workflow, tooling & infra

- **Orchestrator repo** — *This* repo (cloned as `oq-1` / `oq-2`). Coordinates
  the four subrepos (server, ui, daemon, content). Targets `main`; subrepos use
  github-flow against `develop`. (`CLAUDE.md`, `repos.yaml`)
- **Ping-pong playtest** — A two-clone playtest: `oq-2` drives and *verifies*
  (open→verified), `oq-1` owns the code *fixes*, coordinated through a shared
  ping-pong file. (memory: `project_pingpong_oq2_verifies`, `sq-playtest`)
- **R2** — Cloudflare R2 object storage at `genre_packs/<pack>/...`. Git ships
  the prompts/specs (`*_input_params.json`); R2 ships the binaries (OGG audio,
  PNG images). (**ADR-095**)
- **The playgroup** — The real humans SideQuest is *for*: Keith (forever-GM who
  wants to play), James, Alex (slow typist — never rush), Sebastien & Jade
  (mechanics-first; Jade also *authors*). Features are weighed against these
  people, not personas. (`CLAUDE.md` "Who This Is For")

---

*Maintained by Tech Writer. When you coin a term that outlives the PR that
introduced it, add it here with a citation — THE TRUTH SHALL MAKE YE FRET.*
