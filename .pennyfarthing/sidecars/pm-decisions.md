## PM Decisions

### Product direction (settled — don't revisit in grooming or retros)
- **Narrative consistency is the #1 product goal.** The solo narrative experience is the core value prop. Mechanical state (known_facts, LoreStore, NPC registry, inventory) exists specifically as guardrails for the LLM — not as game mechanics for the player. Prioritize consistency bugs (NPC name changes, forgotten items, lost facts, turn count resets) over any feature work. Every sprint.
- **Book conceit is retired.** UI pivoted to persistent docked sidebar + Current Turn Focus + Scrollable History. Decided 2026-04-05. Don't groom stories that rebuild book-metaphor UI or propose "maybe we bring the book back for X." It's dead.
- **No skeumorphism.** Genre-flavored chrome is fine (three archetypes: `parchment`, `terminal`, `rugged`). But UI is functional first — standard interaction patterns, persistent visible state. Reject stories that sacrifice usability for metaphor (Roman numeral turn counters, scroll-to-request-own-stats, paginated storybook).
- **Spoiler protection for world content.** Keith wants to discover narrative surprises in play. Don't write ACs that require him to review spoilers. World-builder stories have creative freedom on flavor/lore/story/NPCs/plot hooks — Keith owns mechanics/crunch only. Only `mutant_wasteland/flickering_reach` is fully spoilable.

### Roadmap-adjacent settled decisions
- **TTS was intentionally stripped from the daemon in story 27-1** (commit 8583162, 2026-04-07). Daemon is image-only. Don't groom "re-enable TTS" stories unless Keith explicitly raises it — he removed it deliberately. If it comes back, it comes back via a new daemon worker, not a protocol fix.
- **ACE-Step music gen runs standalone, not via the daemon.** Lives at `/Users/keithavery/Projects/ACE-Step/` with its own venv. Don't groom stories that route music generation through the daemon — that was tried and stripped in story 27-2.
- **Music is cinematic, not video game BGM.** Stories that propose looping background music get rejected. Overtures, cues, one-shots with fades. Crossfade on mood changes.
- **Music is pre-rendered files**, loaded from `genre_packs/{genre}/audio/music/`. Not daemon-generated, not dynamically composed at runtime.
- **Road warrior music is high priority.** Genre identity is heavily audio-driven (Doof Warrior / Mad Max). Music stories for road_warrior get bumped up relative to other genres.
- **Dinkus and drop caps are CSS-based.** Don't groom stories that generate PNG dinkus or illuminated drop cap images. Fully deprecated.

### Content systems (Keith's 30-year domain — treat as mature)
- **Conlang is a core feature**, not a footnote. Corpus files (`.txt`) with real-world phoneme banks; cultures use `corpora` with `weight` + `lookback` to Markov-generate new names; each faction blends 2+ languages (Clockwork Orange / Nadsat style). `word_list` is for place_nouns and adjectives only. Don't groom stories that replace conlang generation with static name lists or "just use real foreign words."
- **Procedural systems lineage** — NPC registry, trope engine, POI generation, cartography, conlang all draw on 30 years of Keith's prior work (MUSHcode, populinator, lango, gotown, townomatic, steading-o-matic). Don't frame them as experimental. Respect the design conviction.
- **"Yes, And" is a foundational product principle** (SOUL #9) — origin is MUSH softcode accepting player creativity as canon vs. MUD hardcode. Non-negotiable. Stories that propose rejecting player input for "consistency" are wrong by design.

### Infrastructure and process (settled)
- **Tailscale for playtest connectivity** (private network, free for 100 devices). **Cloudflare R2 for asset backup** (10GB free, zero egress). **Cloudflare Tunnel + Access for long-term public exposure.** Don't groom stories that propose alternative infra.
- **Save files live at `~/.sidequest/saves/`** — SQLite `.db` per genre/world/player. Not in the repo.
- **Skip architect gates and spec checks for SideQuest.** Personal project — streamlined RED → GREEN → VERIFY → REVIEW → FINISH. Don't require epic/story context docs. Don't groom stories that add more workflow ceremony.
- **Epic 15 is a zero-new-debt cleanup mandate.** Every Epic 15 story's ACs explicitly forbid stubs, silent fallbacks, and deferral language. PM reviews Epic 15 stories against CLAUDE.md before grooming is finalized.

### Tech stack split (reference for story routing)
- **Rust for everything non-LLM.** `sidequest-game`, `sidequest-protocol`, `sidequest-server`, `sidequest-genre`, `sidequest-agents`, `sidequest-daemon-client`, CLI tools (namegen, encountergen, loadoutgen, validate).
- **Python daemon for ML inference only** — currently only Flux.1 (images). Kokoro (TTS) stripped story 27-1. ACE-Step (music gen) stripped story 27-2, now runs standalone.
- **Claude calls always go through Rust subprocess.** Don't import the Claude SDK into Python.
- **Story routing:** anything that touches game state, protocol, dispatch, or narrator orchestration → `sidequest-api` stories. Anything that runs Flux → `sidequest-daemon` stories. Anything that renders UI → `sidequest-ui` stories. Content authoring → `sidequest-content`.

### Reference locations
- **Original Python SideQuest:** `~/ArchivedProjects/sq-1` — source of truth when grooming porting stories.
- **Ping-pong file:** `/Users/keithavery/Projects/sq-playtest-pingpong.md` (read every 2-3 min during playtests).
- **Ping-pong archive:** `/Users/keithavery/Projects/sq-playtest-archive/{timestamp}.md` (rotate when pingpong gets long).
- **Genre packs:** `sidequest-content/genre_packs/` — NOT `oq-2/genre_packs/` which only has media subdirs.

### Hardware context (for sizing and routing)
- **MacBook Pro M3 Max 128GB.** Can run Flux locally without VRAM constraints. No CUDA — Metal Performance Shaders or CPU only. Unified memory means ML workloads don't round-trip across PCIe. Size ML-adjacent stories knowing this is the target hardware.
