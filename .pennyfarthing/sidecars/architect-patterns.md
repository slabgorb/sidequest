## Architect Patterns

### How to work with Keith
- **Senior architect, 30-year dev, learning Rust via the SideQuest port.** Talk at the architectural abstraction level — pattern names (trait objects, actor model, CQRS, composition), trade-offs, system decomposition. Don't over-explain general programming concepts.
- **Teaching mode on by default.** Explain Rust idioms as they come up, framed against the Python equivalent first (the port is Python→Rust), then Go when Python can't express the concept (traits → Go interfaces, ownership, compile-time guarantees). `#[derive(Serialize)]` ≈ `@dataclass`; traits ≈ Go interfaces, not Python ABCs.
- **Dictation artifacts expected.** "axiom" → "axum", "SERG" → "serde", "playlist" → "playtest", etc. Parse for intent before correcting.
- **Procedural world generation is a 30+ year domain for Keith** — MUSHcode, populinator, conlang markov, townomatic, gotown. SideQuest content systems are mature patterns he's rebuilt before, not novel experiments. Never treat conlang/NPC registry/tropes/POI as new.
- **Velocity calibration: ~20x human dev speed, sustained since Nov 2025.** Divide "human dev" estimates by 5-10x for parallelizable work. There is no "too much for one session."

### Core wiring patterns
- **Wiring means non-test consumers.** Before declaring GREEN, grep for the function/struct in production code paths. Library functions with no consumers are stubs, not features.
- **Wiring means the full pipeline.** "Wire X into Y" = source → intermediate layers → rendered output, not "component accepts props." ACs and tests must cover the full data flow.
- **Wiring means visible in the GM panel.** Every subsystem emit site gets an OTEL watcher event with content the lie detector needs to refute a Claude hallucination (e.g. `room_count`, `hp_delta`, `item_added`). Internal data flow without OTEL is not wired.
- **Combat wiring trace (reference):** IntentRouter → Orchestrator → lib.rs → Protocol → UI CombatOverlay. This is the template for verifying any intent-to-UI pipeline.
- **Debug, don't rebuild.** The code is ~98% done — find the small break. Trace the existing pipeline front-to-back before writing anything new. Dev agents repeatedly rebuild pipelines that already work.
- **Source-level wiring guard tests.** When a runtime integration test is impractical (dispatch_connect has 55 params, dockview needs real DOM sizing, bool CLI defaults), read the source file from the test and assert the wire exists as a substring/pattern within N lines of the emit site. Pattern reference: `map_telemetry_wiring_tests.rs` in sidequest-server, `gameboard-wiring.test.tsx` in sidequest-ui. These catch "someone deleted the wire in a future refactor" at `cargo test` / `vitest run` time, not at playtest time.

### Architectural patterns
- **OTEL two-tier pattern: defensive warnings = `_watcher_publish` events; success traces = `Span.open` contextmgrs.** In sidequest-server, success/decision paths get full OTEL spans via `Span.open` context managers in `sidequest/telemetry/spans/<domain>.py` (e.g. `magic_working_span`, `innate_v1_cast_span`) — these carry per-call structured trace context. Defensive paths (`magic.init_failed`, `magic.init_no_actor_bars`, `magic.init_no_catalog`, `magic.unrouted_cost`) call `_watcher_publish(event_name, payload, component=..., severity="warning")` directly — no Span.open contextmgr, just an event for the GM panel. Pattern decided in story 47-7 (architect scope resolution 2026-05-09). Don't over-engineer warning paths into full spans — the watcher_publish hub is the right granularity for "this happened defensively" events.
- **Dual-emit warning pattern.** Defensive paths keep the existing `logger.warning(...)` call AND add `_watcher_publish(...)` immediately after. The logger handles forensic post-crash log retrieval; the watcher event handles live GM-panel visibility. Single-source-of-truth doesn't apply here — different consumers, different lifetimes. Reference: `sidequest-server/sidequest/server/magic_init.py:319-342` (`magic.init_no_actor_bars`).
- **Rust vs Python split.** If it doesn't operate an LLM, it goes in Rust (game engine, state, protocol, markov chains, name gen). If it runs model inference (Flux, Kokoro, ACE-Step — *not* Claude), it's in the Python daemon. Claude CLI calls go through Rust subprocess.
- **Sidecar tool pattern** (Epic 20): Narrator calls tool → parser validates → `assemble_turn` consumes. Established by `item_acquire`, `merchant_transact`, `lore_mark`. All future narrator-exposed tools follow this pattern.
- **Script tool prompt pattern** (ADR-056): Expose Rust generator binaries to the narrator via skill-style checklists (carrot), not threatening gate language (stick). Clear command table, "when to call" guidance, post-call checklist. Never "You MUST" or "Do NOT" — LLMs bash against hard gates.
- **No server-side re-invocation of the LLM to judge the LLM.** Post-hoc validation lives in OTEL spans ("was the tool used? did output match state?"), not a second LLM round-trip. The user calls this the "God lifting rocks" problem.
- **React `key` as layout reset tool.** Changing `key` on a stateful component forces React to unmount and remount it fresh — cleanest way to reset dockview/three.js/etc. without imperative reset code. Used in `GameBoard key={currentGenre}` to fix the Dockview drift bug.
- **Dedicated protocol messages for structured UI actions** — `BEAT_SELECTION`, `TACTICAL_ACTION`, `JOURNAL_REQUEST`, `CHARACTER_CREATION` carry structured IDs. Never synthesize natural-language text from button state and route through `PLAYER_ACTION` + fuzzy match. See dev-patterns for the 2026-04-11 incident.
- **Monster Manual placement:** pre-gen NPCs inject into `<game_state>` as "NPCs nearby (not yet met by player)" — never XML casting sections or meta-prompt instructions. Claude reads game_state as world truth; meta gets treated as style inspiration.
- **Three-layer content inheritance: base → genre → world.** Architectural invariant for all structured content (archetypes, NPCs, locations, cultures, archetypes). Base = structure, genre = tone, world = specific lore. Resolution is prototype-chain / Python-MRO style — each layer can add fields, upstream shape is preserved. Never flatten.

### Meta-principle: interpretation is a model problem, not a regex problem
- **The Zork Problem generalizes.** SOUL.md's principle about natural-language narration escaping finite-verb ceilings applies to every axis where the system interprets meaning. Intent classification (ADR-010/032) was the narrator-layer form; the same error recurs in cliche detection, content validation, memory retrieval, prompt routing, anywhere a fuzzy semantic input has to be understood. The rule: **if the input is fuzzy and the system has to decide what it means, keyword/regex matching is a category error** — use the model that can read.
- **The inverse test:** "could this problem be restated as 'understand what the user/caller meant'?" If yes, the regex is wrong. If no (bounded protocol contracts — port numbers, HTTP verbs, JSON keys), regex is fine.
- **Zawinski's quote is the tactical form; Keith's — "just don't work" — is the strategic form.** Anthropic's memory system is an example of the failure: keyword-triggered recall over semantic content produces noisy redundancy (10 memory files for 1 canonical rule). Sidecars are architecturally correct because they assume the reader (Claude) is the semantic layer — the store just needs curated prose, injected whole.

### Git / branch patterns
- **Gitflow on every subrepo.** Subrepos (sidequest-api, sidequest-ui, sidequest-content, sidequest-daemon) target `develop`. Only the orchestrator targets `main`. Always check `repos.yaml` before any git op.
- **Branch before editing.** `git checkout -b feat/description` BEFORE touching files, not after. Avoids the "hook-blocked commit → panic → stash scramble" failure mode.
- **Dirty work comparison pattern.** When local uncommitted changes conflict with a pull: commit dirty work to a temp branch, pull clean on the default branch, diff each file local-vs-remote side by side, categorize (identical / remote better / local has extra value / no remote change), then cherry-pick deliberately. Never stash.
- **Additive git ops need no permission** (commit, push non-force, pull --ff-only, checkout existing, checkout -b, fetch, add). **Destructive git ops always ask first** (reset, clean, force-push, branch -D, rebase -i, stash — banned outright).

### Playtest patterns
- **Pingpong cadence: every 2-3 minutes during active playtest.** Read `/Users/keithavery/Projects/sq-playtest-pingpong.md` frequently so new `open` items at the top don't pile up unnoticed. Update to `fixed` immediately when a fix lands — don't batch.
- **Always pull and test on new commits.** When `git log HEAD..origin` shows new commits during playtest: pull → rebuild → restart → test. No "want me to?" prompt.
- **Always rebuild on restart.** Every service restart during playtest is a full rebuild. Compile time is negligible vs. debugging a stale binary.
- **Keep going.** Work through the checklist autonomously during playtest. Don't pause to ask "want me to continue" — Keith wants momentum.
- **Restart in existing tmux panes.** Send Ctrl+C and re-run the command. Don't close/reopen panes — churn annoys Keith and wastes time.
- **Source-grep tests > integration tests for playtest fixes.** Faster to write, faster to run, catches the exact failure class (someone unwired it in a refactor) without needing a full stack harness.

### Spec hierarchy
- **Spec authority order:** Story scope (session file, highest) → story context → epic context → architecture docs / SOUL / rules (lowest). When sources conflict, the session scope wins. Log deviations **at the moment of the decision**, not at phase exit.
