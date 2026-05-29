# SideQuest — Product Feature History

The cross-repo, product-level view of what shipped, by release. SideQuest spans
four repos (`sidequest-server`, `sidequest-ui`, `sidequest-daemon`,
`sidequest-content`) coordinated by this orchestrator; each keeps its own
detailed `CHANGELOG.md`. **This file is the front door** — headline features
only, aggregated across repos. For the per-change detail, see each repo's
CHANGELOG.

> Scope: the current-architecture era, from the Rust→Python port (ADR-082,
> ~2026-04-19) forward. Earlier Rust-prototype history lives in the archived
> `slabgorb/sidequest-api` repo.

---

## Unreleased (since 2026-05-26)

- **PostgreSQL persistence cutover completed (ADR-115).** The full `pg/`
  repository family lands (save, dungeon, telemetry, forensic-reader, events,
  snapshot, narrative, scrapbook, sessions), psycopg3 + connection pool,
  per-session row locks, Alembic-owned DDL, fail-loud `SIDEQUEST_DATABASE_URL`.
  The SQLite **write** layer is deleted (not dual-pathed); a read-only importer
  remains for legacy `.db` files.
- **Pluggable rulesets bound, engine + content (ADR-117).** `space_opera` → **SWN**
  (attack-vs-AC, `hp_depletion`, dogfight shot resolution, 1d8+DEX initiative);
  `neon_dystopia` → **CWN** (System Strain, Trauma/Shock/Mortal-Major injury
  lethality, `net_run` hacking-as-confrontation).
- **space_opera grows to three live worlds** — `aureate_span` promoted out of
  draft (camp-cosmic redirect, 7 portraits + 21 POIs) and `perseus_cloud` shipped,
  alongside `coyote_star`. New **`spaghetti_western/five_points`** (NYC 1856-57)
  with 12 authored + rendered POIs.
- **Render pipeline.** Caller `--steps` honored end-to-end (daemon worker, #94;
  default 15→20); world `visual_style` now overrides genre (stops portrait grammar
  bleeding into landscapes); `render_queue.py` sequential render→sync runner.
- **Client.** Asset preload on reconnect, world-level NPC portraits, round-anchored
  peer-action transcript, genre-theme token persistence fix.
- **Docs.** Live 10-pack inventory refresh, `orc-quest → sidequest` repo rename,
  this `FEATURES.md`.

## [1.3.0] — 2026-05-26

- **Intent Router — mechanical-engagement spine (ADR-113).** A pre-narrator pass
  decomposes each action into a `DispatchPackage`, firing mechanical engines
  *before* narration, with a router-vs-engine OTEL lie-detector.
- **Ablative HP substrate (ADR-114).** HP reclaims the lethality track beneath the
  dials; 0 HP triggers `hp_depletion`. Client relabels the survivability pool
  Edge→HP.
- **Reference pages (Rules + Lore).** Themed HTML routes with deep-links from
  narration, the character sheet (abilities/class), and the knowledge journal.
- **Seed trope engine.** Engagement-triggered seed draws with OTEL routing and
  narrator injection (tea_and_murder content).
- **Per-PC dungeon movement + room-graph navigation (ADR-055/106).**
- **Content.** `shattered_accord`, `pulp_noir`, `neon_dystopia` promoted to
  production; reference-page chrome (`display_font_family`/`archetype`) across all
  10 packs; purchased TableTop Audio wired into 6 packs; ACE-Step `infer_step`
  60→120.
- **Daemon.** Opus music encode 96k→160k; audio2audio reference fetch from R2.

## [1.2.0] — 2026-05-23 *(subrepos; the orchestrator consolidated this window into its 1.3.0)*

- **Anthropic SDK narrator migration completed (ADR-101/102).** The SDK becomes
  the default backend; native tool-use replaces the JSON sidecar; prompt-caching
  cost controls land. `claude -p`/Ollama retired as narrator backends.
- **Runtime procedural Jaquaysed megadungeon (ADR-106).** Generator family
  (backtracker/Prim/cellular/room-and-corridor + braid), region graph with an
  exact Jaquays invariant checker, deterministic sub-seeding, over `beneath_sunden`.
- **Broadcast-layer perception firewall (ADR-104/105).** Per-recipient POV
  narration; secret-routing as a core invariant; public-safe output contract.
- **Scenario system, persistent locations (ADR-109), monster manual, and the
  out-of-band aside channel (ADR-107).**
- **Client.** Live streaming narration (`NarrationDelta`), server-rendered orbital
  chart, ship widget, magic/ledger surface; dice authority restored after the SDK
  cutover severed it.
- **Content.** `tea_and_murder/glenross` (Edwardian Highland cosy-crime),
  `spaghetti_western` promotion, `beneath_sunden` world-register genre-truth gate.

## [1.1.0] — 2026-05-11

- **Rust→Python port restoration (ADR-082).** Backend, chargen, and combat ports
  (StructuredEncounter, ResourcePool, tension/pacing) re-landed in Python.
- **OTEL / observability restoration (ADR-090).** GM dashboard, local Jaeger,
  OTLP tracing, watcher-as-spans.
- **Z-Image Turbo MLX renderer as the sole image worker (ADR-070).** ~108s→33s per
  render; PromptComposer + recipes/catalog cascade (genre/world/culture, camera
  presets, budget-driven LOD); R2 render-upload pipeline. The Flux/LoRA pipeline
  was built and then torn out within this window (net removal).
- **caverns_and_claudes B/X class system.** Fighter/mage/cleric/thief with B26
  saving throws, L1 arcane+divine spell catalogs, and signature abilities
  (Turn Undead / Taunt / Backstab, ADR-097).
- **coyote_star major world authoring** — hierarchical orrery cartography, magic
  configs, Kestrel crew; the road_warrior **Rig MVP**.
- **Cross-pack mechanics.** Six shipping packs migrated to dual-dial momentum;
  `victoria → tea_and_murder` rename; road_warrior + spaghetti_western promoted.
- **Client.** Multiplayer session model + submit-and-wait turn coordination
  (ADR-036), live teammate typing / peer-reveal, 3D dice overlay (ADR-075).

## [1.0.0] — post-port baseline (~2026-04-19)

- **Rust→Python port (ADR-082).** FastAPI/WebSocket game engine, React/TypeScript
  client, Z-Image MLX media daemon, and content packs re-established on the Python
  stack. TTS removed (audio is music + SFX only).
