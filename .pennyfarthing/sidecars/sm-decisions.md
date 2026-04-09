## SM Decisions

### Process decisions for SideQuest specifically
- **Skip architect + spec-check + spec-reconcile phases.** Personal project — streamlined RED → GREEN → VERIFY → REVIEW → FINISH. Don't spawn architect agents during TDD. Don't require epic/story context docs. Still spawn architect for genuine design questions when raised in a story.
- **Epic 15 is a zero-new-debt mandate.** Every agent working an Epic 15 story re-reads CLAUDE.md before starting implementation. SM rejects any Epic 15 phase exit that ships stubs, silent fallbacks, `unwrap_or_default()` on required fields, or "follow-up story" deferral language.
- **Memories over sidecars for cross-session learning.** The auto-memory system at `/Users/keithavery/.claude/projects/-Users-keithavery-Projects-oq-2/memory/` is the canonical cross-session store. Sidecars are per-agent operational context loaded at agent activation. When adding new learnings, write to memory first; update sidecars when a pattern becomes stable enough to be operational.
- **Session files live at `.session/{story-id}-session.md`** during active work. Archived to `sprint/archive/` by `pf sprint story finish`. Never write session files directly into `sprint/` — that has broken handoff CLI before.
- **Handoff CLI is the canonical exit protocol.** `pf handoff resolve-gate` → gate check → `pf handoff complete-phase` → `pf handoff marker`. Nothing after the marker. If marker output contains `relay: true`, use the Skill tool to invoke the named skill.

### Product direction (settled — don't revisit in sprint planning)
- **Narrative consistency is the #1 product goal.** The solo narrative experience is the core value prop. Mechanical state (known_facts, LoreStore, NPC registry, inventory) exists as guardrails for the LLM, not as game mechanics for the player. Consistency bugs (NPC name changes, forgotten items, lost facts, turn count resets) are always high priority.
- **Book conceit is retired.** UI has pivoted to persistent docked sidebar + Current Turn Focus + Scrollable History. Decided 2026-04-05. Don't coordinate stories that rebuild the book metaphor.
- **No skeumorphism.** Genre-flavored chrome is fine (three archetypes: `parchment`, `terminal`, `rugged`). But UI is functional first. Reject handoffs where the acceptance criteria sacrifice usability for metaphor.
- **Spoiler protection for world content.** Keith wants to discover narrative surprises in play. World-builder stories have creative freedom on flavor/lore/story/NPCs/plot hooks — don't route them through PM review. Keith owns mechanics only.

### Music / audio (settled)
- **Music is cinematic, not video game BGM.** Overtures, cues, one-shots with fades. Never looping. Crossfade on mood changes.
- **Music is pre-rendered files** from `genre_packs/{genre}/audio/music/`, NOT daemon-generated. Don't route music stories to the daemon crate.
- **ACE-Step for music gen runs standalone**, not via the daemon. Lives at `/Users/keithavery/Projects/ACE-Step/` with its own venv. Stories that generate music should target that pipeline directly.
- **Road warrior music is high priority.** Genre identity is heavily audio-driven — music stories for road_warrior get bumped.

### Voice / TTS (settled)
- **TTS was intentionally stripped from the daemon in story 27-1** (commit 8583162, 2026-04-07). Daemon is image-only. Don't coordinate "re-enable TTS" stories unless Keith explicitly raises them.
- **`--no-tts` defaults to `true`** on sidequest-server (fix `3fe6c2e`, 2026-04-09). The escape hatch `--no-tts=false` is preserved for the day daemon TTS returns.

### Text rendering / UI chrome (settled)
- **Dinkus and drop caps are CSS-based.** No PNG generation. Don't audit for them in sq-audit runs. Don't groom stories that generate these assets.
- **Three genre-chrome archetypes driven by `theme.yaml`:** `parchment` (low_fantasy, victoria, spaghetti_western, caverns_and_claudes), `terminal` (neon_dystopia, space_opera, mutant_wasteland, star_chamber), `rugged` (road_warrior, pulp_noir, elemental_harmony). Don't coordinate stories that propose a fourth archetype without Keith raising it.

### Content systems (Keith's 30-year domain)
- **Conlang is a core feature**, not a footnote. Corpus-based Markov name generation, 2+ language blends per faction (Clockwork Orange / Nadsat style). Don't coordinate stories that replace conlang with static name lists.
- **Procedural systems lineage.** NPC registry, trope engine, POI, cartography, conlang all draw on 30 years of Keith's prior work. Never frame them as experimental in sprint summaries.
- **"Yes, And" is a foundational product principle** (SOUL #9). Non-negotiable. Stories that propose rejecting player input for "consistency" are wrong by design.

### Infrastructure (settled)
- **Tailscale for playtest connectivity**, Cloudflare R2 for asset backup, Cloudflare Tunnel + Access for long-term public exposure. Don't coordinate stories that propose alternative infra.
- **Save files live at `~/.sidequest/saves/`** — SQLite `.db` per genre/world/player. Not in the repo.

### Tech stack split (for story routing)
- **Rust for everything non-LLM.** `sidequest-game`, `sidequest-protocol`, `sidequest-server`, `sidequest-genre`, `sidequest-agents`, `sidequest-daemon-client`, CLI tools.
- **Python daemon for ML inference only.** Currently only Flux.1 images. Kokoro (TTS) stripped story 27-1. ACE-Step (music) stripped story 27-2.
- **Claude calls always go through Rust subprocess.** Stories that propose importing the Claude SDK into Python are routed back for redesign.

### Reference locations
- **Original Python SideQuest:** `~/ArchivedProjects/sq-1` — source of truth when coordinating porting stories.
- **Ping-pong file:** `/Users/keithavery/Projects/sq-playtest-pingpong.md` (read every 2-3 min during active playtest).
- **Ping-pong archive:** `/Users/keithavery/Projects/sq-playtest-archive/{timestamp}.md`.
- **Genre packs:** `sidequest-content/genre_packs/` — the subrepo is the single source of truth. NOT `oq-2/genre_packs/`.

### Hardware context (for sizing and parallelization)
- **MacBook Pro M3 Max 128GB.** Can run Flux locally without VRAM constraints. No CUDA — MPS or CPU only. Unified memory means ML workloads don't round-trip across PCIe. Size ML-adjacent stories knowing this is the target hardware.
- **Velocity context: ~20x human dev speed, sustained since Nov 2025.** Don't size sprints based on what a human would take. Parallel agents change the math 5-10x on parallelizable work.
