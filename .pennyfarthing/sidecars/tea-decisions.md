## TEA Decisions

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
  - `parchment` — low_fantasy, victoria, spaghetti_western, caverns_and_claudes
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
