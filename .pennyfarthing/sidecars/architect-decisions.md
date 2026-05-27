## Architect Decisions

### Product direction (settled — don't revisit)
- **Narrative consistency is the #1 product goal.** The solo narrative experience is the core value prop. Mechanical state (known_facts, LoreStore, NPC registry, inventory) exists specifically as guardrails for the LLM — not as game mechanics for the player. Every bug that breaks consistency (NPC name changes, forgotten items, lost facts, turn count resets) is high priority.
- **Book conceit is retired.** UI has pivoted to persistent docked sidebar + Current Turn Focus + Scrollable History. No modal overlays to ask for your own state. Decided 2026-04-05.
- **No skeumorphism.** Genre-flavored chrome is fine (three archetypes: `parchment`, `terminal`, `rugged`). But the UI is functional first — standard interaction patterns, persistent visible state. No Roman numeral turn counters, no paginated storybook, no scroll-to-request-own-stats.
- **Spoiler protection for world content.** Keith wants to discover narrative surprises in play. Flag "this faction has a secret motivation" without revealing what it is. Only `mutant_wasteland/flickering_reach` is fully spoilable.
- **World-building creative split.** Keith owns mechanics/crunch (always discuss rules changes). World Builder has creative freedom on flavor/lore/story/NPCs/plot hooks. Keith wants to be surprised like a player trusts a DM.

### Music / audio
- **Music is cinematic, not video game BGM.** Overtures, cues, one-shots with fades. Never looping. Crossfade between tracks on mood changes.
- **Music is pre-rendered files from `genre_packs/{genre}/audio/music/`**, NOT daemon-generated. The daemon has nothing to do with music. Investigate music bugs via: (1) the audio directory, (2) API `music_cue_produced` logs, (3) `audio.yaml` mood→track mappings. Never check the daemon.
- **ACE-Step for music generation**, not the daemon. Lives at `/Users/keithavery/Projects/ACE-Step/` with its own venv: `.venv/bin/python3 generate_tracks.py --config <genre> --output_dir <path>`. Must be run from the ACE-Step directory. System Python won't work.
- **ACE-Step audio2audio is the validated approach for theme variations.** Produces real leitmotif variations with `ref_audio_strength` 0.25-0.55. Canonical theme per mood + a2a variations, not random text2music. Script: `scripts/generate_theme_variations.py`.
- **Road warrior music is high priority.** Genre identity is heavily audio-driven (Doof Warrior / Mad Max). Prioritize music quality and variation count here.

### Voice / TTS
- **TTS was intentionally stripped from the daemon in story 27-1** (commit 8583162, 2026-04-07). `daemon.py::WorkerPool.render` now only handles Flux tiers and rejects everything else with `Unknown tier: 'tts'`. The daemon is an image-only renderer.
- **`--no-tts` defaults to `true`** on sidequest-server (as of fix `3fe6c2e`, 2026-04-09) to match the daemon reality. The escape hatch `--no-tts=false` is preserved for the day someone restores daemon TTS.
- **Creature voice parameters flow through `VoiceRouter`** — narrator + character archetype + creature type voice assignment. Still wired on the Rust side even though the daemon dropped synthesis.

### Text rendering / UI chrome
- **Dinkus scene breaks are CSS-based.** No PNG images. Don't audit for them, don't generate them.
- **Drop caps are CSS-based.** Same — no illuminated drop cap images to generate.
- **Three genre-chrome archetypes driven by `theme.yaml`:**
  - `parchment` — low_fantasy, tea_and_murder, spaghetti_western, caverns_and_claudes
  - `terminal` — neon_dystopia, space_opera, mutant_wasteland, star_chamber
  - `rugged` — road_warrior, pulp_noir, elemental_harmony
- **Genre theming infrastructure already exists:** `theme.yaml` + `client_theme.css` per genre pack, injected via `useGenreTheme` hook. CSS vars (`--primary`, `--surface`, `--accent`) bridge to Tailwind automatically. The gap is that only narrative elements get genre CSS classes; panels use generic Tailwind — fix in place, don't reinvent.

### Content systems (Keith's 30-year domain)
- **Conlang is a core feature**, not a footnote. Corpus files (`.txt`) contain real-world phoneme banks; cultures use `corpora` with `weight` + `lookback` to Markov-generate new names; each faction blends 2+ languages (Clockwork Orange / Nadsat style, not translation). `word_list` is only for place_nouns and adjectives — given/family names always use corpora. Phonemes feed Kokoro for pronunciation (when/if TTS returns).
- **Procedural systems lineage.** SideQuest's NPC registry, trope engine, POI generation, cartography, conlang — these draw on 30 years of Keith's prior work (MUSHcode, populinator, lango, gotown, townomatic, steading-o-matic). Respect the domain expertise. These are not speculative design experiments.
- **"Yes, And" as a foundational principle** — origin is MUSH softcode accepting player creativity as canon vs. MUD hardcode. This is SOUL principle #9 and it's non-negotiable.

### Infrastructure
- **Tailscale for playtest connectivity** (private network, no port forwarding, free for 100 devices).
- **Cloudflare R2 for asset backup** (10GB free, zero egress). rclone sync from `genre_packs/` for `*.ogg` and `*.png`. `just assets-push` / `just assets-pull` recipes.
- **Cloudflare Tunnel + Access for long-term public exposure.** Domain-based, WAF, rate limiting, player allowlist. e.g. `play.domain.com`.
- **Save files live at `~/.sidequest/saves/`** — SQLite `.db` files, one per genre/world session. Not in the repo. See `.pennyfarthing/guides/save-management.md`.

### Tech stack split
- **Rust for everything non-LLM.** Game engine (`sidequest-game`), protocol (`sidequest-protocol`), server (`sidequest-server`), genre loader (`sidequest-genre`), Claude orchestration (`sidequest-agents`), daemon client (`sidequest-daemon-client`), CLI tools (namegen, encountergen, loadoutgen, validate).
- **Python daemon for ML inference only:** Flux.1 (images), *previously* Kokoro (TTS, stripped story 27-1), *previously* ACE-Step (music, stripped story 27-2 — music gen now runs standalone from `~/Projects/ACE-Step/`). The daemon is an image-only sidecar now.
- **Claude calls always go through Rust subprocess.** Never import the Claude SDK into Python.
- **LoRA pipeline is operational as of 2026-04-07.** Genre-specific Flux LoRAs train to `.safetensors` successfully. Remaining work is loading/verification and render-pipeline integration.

### Prompt architecture rules
- **Monster Manual NPCs inject into `<game_state>` only.** Format: `"- Name (role, faction) — brief personality, speech quirk"`. Proven across 6+ iterations — game_state is read as world truth; meta-instructions (XML casting calls, `available_characters` sections, tool workflow instructions) are read only as style inspiration, so Claude invents names instead of selecting. Never add XML casting sections or Primacy/Recency-zoned "HARD RULE" constraints for NPC selection — all failed.
- **Three-layer content inheritance (base → genre → world)** is the architectural invariant for archetypes, NPCs, locations, archetypes, most structured content. Base = shape, genre = tone, world = lore. Resolution is prototype-chain / Python-MRO. This is the mental model for every new content system — never flatten layers.

### Anti-pattern rules to enforce architecturally
- **No keyword / pattern matching for intent classification** (ADR-010, ADR-032). The Zork Problem. Natural language defeats finite verb sets every time. Intent is always an LLM call (preferably folded into the narrator's Opus response for zero additional latency). Reject any subsystem design that adds keyword heuristics to intent routing, dispatch, or narrator-output interpretation.
- **No text-synthesis dispatch for structured UI actions.** UI button clicks must send dedicated protocol messages (`BEAT_SELECTION`, `TACTICAL_ACTION`, `JOURNAL_REQUEST`, `CHARACTER_CREATION`). Never synthesize natural-language `PLAYER_ACTION` strings from structured UI state. Reference: the 2026-04-11 `05a3dfb` incident where beat-button clicks were fuzzy-matched against narrator label text.
- **No AI judging AI.** Second-LLM validators for narrator output, consistency checks, or game-decision verification are the "God lifting rocks" problem. The first call is already the most semantic reader available.
- **No live LLM calls in test suites.** `cargo test` must mock `ClaudeClient`. Live-LLM suites live in `--ignored`.

### Process decisions for SideQuest specifically
- **Skip architect gates and spec checks.** Personal learning project, not a work repo. TDD runs RED → GREEN → VERIFY → REVIEW → FINISH. No architect spec validation, no spec-check/spec-reconcile, no epic/story context docs required.
- **Epic 15 (Playtest Debt Cleanup) is a zero-new-debt mandate.** Every agent working an Epic 15 story re-reads CLAUDE.md before starting. Wire existing code, don't reimplement. If the function being wired is itself a stub, fix it properly in-story.
- **Build verification happens on OQ-2.** All sidequest-api edits live in OQ-1/sidequest-api. After merge, pull on OQ-2 and `cargo build -p sidequest-server` there (not workspace root — that's a placeholder).

### Reference locations
- **Original Python SideQuest:** `~/ArchivedProjects/sq-1` — source of truth when porting behavior to Rust.
- **ACE-Step music generator:** `/Users/keithavery/Projects/ACE-Step/.venv/bin/python3 generate_tracks.py`.
- **Ping-pong file:** `/Users/keithavery/Projects/sq-playtest-pingpong.md` (read every 2-3 min during active playtest).
- **Ping-pong archive:** `/Users/keithavery/Projects/sq-playtest-archive/{timestamp}.md` (rotate when the pingpong gets long).
- **Genre packs:** `sidequest-content/genre_packs/` (subrepo, single source of truth — NOT `oq-2/genre_packs/` which has only media subdirs).

### Hardware context for Dev decisions
- **MacBook Pro M3 Max 128GB** — can run Flux locally without VRAM constraints. No CUDA, so tooling must support MPS (Metal Performance Shaders) or CPU fallback. Unified memory means ML workloads don't have to round-trip across PCIe. 40-core GPU.

## Migrated from auto-memory — strategic / architecture decisions (2026-05-26)

- **Pluggable SRD ruleset modules (2026-05-26 pivot).** SideQuest stops *being* a ruleset and *hosts* per-genre SRDs as bound `RulesetModule`s (each owns the whole turn); fidelity bar = faithful author's math (customer is the forever-GM). Map: caverns=B/X, space_opera=SWN, neon=CWN(reuses SWN), wasteland=PbtA, pulp=Fate/FAE, heavy_metal=5e; priority SWN+B/X first. ADR-114 HP survives as shared substrate (its "skip SWN math" line reversed); ADR-033 dials re-slotted to native/Fate only. One module/session, no cross-module fallback, unknown `ruleset:` fails loud. Sequence: seam+native-wrap → SWN → B/X. Doc: `docs/superpowers/specs/2026-05-26-pluggable-srd-ruleset-modules-design.md`.
- **Ruleset seam Spec 0 (MERGED PR #466, `fff5d9d`).** `sidequest/game/ruleset/` with `RulesetModule` ABC (find_confrontation, stat_modifier, compute_dc, apply_beat, resolve_damage), `NativeRulesetModule` (slug `native`), fail-loud `get_ruleset_module` registry (`UnknownRulesetError`); `RulesConfig.ruleset` bound at pack load; `dispatch_dice_throw` routes all five ops. TWO deferred debts to fix BEFORE the SWN module: (1) mirror-math dup — `narration_apply.py::_opposed_dc` and `opposed_check.py::_ability_modifier` still hand-copy the DC/modifier math (will silently diverge); (2) layer inversion — `game/ruleset/native.py` imports from `server.dispatch` (game→server backwards), fix by relocating `find_confrontation_def`/`resolve_damage_spec_from_beat_and_actor` into the game layer.
- **Rig/chassis framework** (sibling to magic-taxonomy; flagship `space_opera/coyote_star`). Locked: own design doc `docs/design/rig-taxonomy.md` (α); hardpoints are `{location, function}` pairs, either nullable (R); damage locality D3 (framework declares location hp/critical schema, scene-mechanics own combat math); subsystems are item_legacy_v1 items with `installed_in:{chassis,location}`, salvage = clearing it (S2); `crew_model:` ∈ single_pilot/strict_roles/flexible_roles (C3); MP/solo register is per-genre. Chassis is a first-class world entity classified by `class:`/`provenance:`, OTEL spans on every rig action. Open: bond mechanics, magic-interface hooks, provenance taxonomy, confrontation catalog. (Verify status — entry is from early May.)
- **Postgres importer scope (ADR-115 TG-E, descoped 2026-05-26).** Migrate ONE save ad-hoc (one-shot script/manual), not the whole corpus; drop versioned-bundle/reusable-CLI/dry-run ceremony. KEEP: FK-ordered inserts, created_at→isoformat normalization (else `PgForensicReader.build_timeline` mis-bounds via lexical sort), round-trip sanity check on the real save, preserve original SQLite (WAL-consolidated) until PG verified.
- **Persistent location/room descriptions carry a hard mechanical contract** (Keith 2026-05-19): anything the prose NAMES must either exist in game state as a real interactable, be trivial enough for "yes-and" promotion at touch, or be explicitly atmospheric/untouchable flavor — no floating flavor with an empty trapdoor. Each description is a (prose, entity-manifest) pair with per-entity tier; generate-once serve-many; OTEL spans confirm manifest-entity resolution and flag hallucinations. Applies to POI worlds (authored at world-build) and procedural worlds (at materialize time). Enforces SOUL "Yes, And" + "Diamonds and Coal" + OTEL-lie-detector.
- **Technology choice ≠ deployment model.** Adopting a client-server DB/broker/service does NOT commit the project to cloud/hosted/SaaS/multi-tenant; default to self-hosted framing ("server in the closet"). Keith predicts a shift back to self-hosted as cloud enshittifies (2026-05-26, drafting ADR-115 Postgres). State the capability (concurrency/durability) and leave where-it-runs as its own deferred decision.
