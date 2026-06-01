## TEA Patterns

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
- **Rust vs Python split.** If it doesn't operate an LLM, it goes in Rust (game engine, state, protocol, markov chains, name gen). If it runs model inference (Flux, Kokoro, ACE-Step — *not* Claude), it's in the Python daemon. Claude CLI calls go through Rust subprocess.
- **Sidecar tool pattern** (Epic 20): Narrator calls tool → parser validates → `assemble_turn` consumes. Established by `item_acquire`, `merchant_transact`, `lore_mark`. All future narrator-exposed tools follow this pattern.
- **Script tool prompt pattern** (ADR-056): Expose Rust generator binaries to the narrator via skill-style checklists (carrot), not threatening gate language (stick). Clear command table, "when to call" guidance, post-call checklist. Never "You MUST" or "Do NOT" — LLMs bash against hard gates.
- **No server-side re-invocation of the LLM to judge the LLM.** Post-hoc validation lives in OTEL spans ("was the tool used? did output match state?"), not a second LLM round-trip. The user calls this the "God lifting rocks" problem.
- **React `key` as layout reset tool.** Changing `key` on a stateful component forces React to unmount and remount it fresh — cleanest way to reset dockview/three.js/etc. without imperative reset code. Used in `GameBoard key={currentGenre}` to fix the Dockview drift bug.

### Content-mechanics stories span two repos (71-24)
- **A genre-pack mechanics story scoped `repos: sidequest-content` still needs a `sidequest-server` test branch.** The YAML bank lives in content, but the TDD tests are Python and exercise the server seams: the loader (`sidequest.genre.loader.load_genre_pack`), `RulesConfig.intent_verbs_by_type`, `confrontation_intent_validator.validate` (the real intent→`matched_type` path), and the production seating+resolution path (`instantiate_encounter_from_trigger` + `dispatch_dice_throw`). Create a matching `feat/<id>-…` branch on sidequest-server, commit the tests there, and log a Delivery Finding so SM-finish handles PRs in BOTH repos.
- **Canonical real-pack confrontation test to mirror:** `sidequest-server/tests/server/test_space_opera_swn_combat_e2e.py`. Helpers `_seated_combat` (seats via `instantiate_encounter_from_trigger` with `NpcMention(side="opponent")`) + `_throw` (`face=[20]` winning d20 through `dispatch_dice_throw`) + the `otel_capture` fixture (`tests/server/conftest.py`). Combat resolves on `enc.outcome == "player_victory"` after opponent `hp.current <= 0`; assert the `encounter.resolved` span `source == "hp_depletion"`. This is the sanctioned exception to "tests don't point at content."
- **A new SWN `combat`+`hp_depletion` confrontation MUST seed `opponent_default_stats` hp/armor_class/dexterity** or the loader's cross-field validator (`rules.py` ~528-565) raises at load — fail-loud by design so the content author finds it before a player triggers the encounter.
- **Intent reroute is verb-set membership, not a code change.** Moving a verb between confrontation types = moving it in the YAML `intent_verbs` list. `validate()` scores by token overlap (`tokenize` strips light suffixes; `-ss` and ≤5-char words like "swing" survive), most-overlap wins, ties by pack-declaration order. To prove a reroute: assert the verb is in `intent_verbs_by_type[newtype]` and ABSENT from the old type, then drive a real action string through `validate()` and assert `matched_type`.

### Git / branch patterns
- **Gitflow on every subrepo.** Subrepos (sidequest-server, sidequest-ui, sidequest-content, sidequest-daemon) target `develop`. Only the orchestrator targets `main`. Always check `repos.yaml` before any git op.
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
