## GM Gotchas

### The narrator lies — OTEL is the polygraph
- **The narrator improvises constantly.** OTEL is the only way to catch it. If a span is missing for a subsystem, the narrator is making it up — no matter how convincing the prose sounds. A span present with wrong values is a content bug (fix it yourself). A span absent is a code bug (route to Dev via pingpong).
- **Don't use AI to judge AI.** Never propose "run the narration through a second LLM to check consistency" — that's the God-lifting-rocks problem. Surface rich OTEL telemetry for human inspection instead.
- **Coarse cliche is the audit failure mode.** Claude is a cliche engine. For Keith's high-expertise domains (software, game mechanics, RPG design, art, narrative, React/Rust), content must drop to competent-practitioner granularity at minimum; niche-specialist via reference stacking is safer. Flag "voodoo" / "hacker" / "mystery cult" as coarse-granularity failures; require syncretism ("Candomblé Ketu terreiro," "container-escape + LLM-weight-poisoning + RAG-corpus-corruption stack") instead. See `feedback_specificity_shrinks_cliche.md`.

### Spoiler / content rules
- **Spoiler protection is real.** Only `mutant_wasteland/flickering_reach` is fully spoilable. Everything else is unspoiled — don't read world secrets during audits of other genre packs.
- **Content belongs at world level, not genre level.** Flavor goes in `worlds/{world}/`, mechanics go in genre root. This is the "Crunch in Genre, Flavor in World" SOUL principle in action.
- **Genre packs have 7 active genres.** spaghetti_western and victoria exist in content but aren't in the active list yet.
- **Content inheritance is three-layer:** base → genre → world. Archetypes and NPCs resolve through this chain. Never flatten layers during audits.
- **Monster Manual NPCs go in `<game_state>`.** Pre-gen NPCs inject into the game_state prompt section as "NPCs nearby (not yet met)." Never audit for XML casting calls, tool-instruction sections, or meta-prompt framing — those all fail because Claude reads them as style inspiration, not world truth.

### Asset rules
- **Music is pre-rendered files, not daemon-generated.** Tracks live in `genre_packs/{genre}/audio/music/`. Don't audit for daemon music endpoints. Investigate bugs via (1) the audio directory, (2) API `music_cue_produced` logs, (3) `audio.yaml` mood→track mappings.
- **Music is cinematic, not video game BGM.** Overtures, cues, one-shots with fades. Never looping. If an audit flags "missing background loop," it's not missing — that's design.
- **Dinkus and drop caps are CSS-based.** Don't flag missing image assets for these — they're deprecated.

### Playtest operational discipline
- **Playtest mode is debugging, not building.** The code is ~98% done — find the small break. Don't propose new features or rebuild pipelines. Route bugs with OTEL evidence, don't wax design.
- **Focus on systems, not narration quality.** The prose has been solid for a long time. Don't comment on writing quality — only log it when it indicates a system bug.
- **Pingpong cadence: every 2-3 minutes during active playtest.** Read `/Users/keithavery/Projects/sq-playtest-pingpong.md` frequently so new `open` items don't pile up. Update status immediately when a fix lands — `open` → `in-progress` → `fixed` → `verified`.
- **Rotate the pingpong when it gets long.** Archive to `/Users/keithavery/Projects/sq-playtest-archive/{timestamp}.md` when all tasks are fixed/verified and dev is idle.
- **Keep going during playtest.** Don't stop to ask "want me to continue?" — Keith wants momentum. Work through the checklist autonomously.
- **Don't restart the daemon.** It warms up ML models — restart is expensive. Leave it running across sessions.
- **Don't churn tmux panes.** Restart services in existing panes via Ctrl+C + re-run. Don't close/reopen.
- **Pull and test when new commits appear.** `git log HEAD..origin` shows new commits during playtest → pull → rebuild → restart → test. No "want me to?" prompts.
- **No "playtest" excuse for deferring fixes.** Every playtest is production tomorrow. Don't downgrade to "quick fix" because it's "just a playtest."

### Deferral / rationalization gotchas
- **Never suggest deferring work.** Don't say "park it," "post-X problem," "nice-to-have for later." Keith decides priorities.
- **No "pre-existing" excuse.** If content has been broken for multiple sessions, that's worse, not better.
- **Fix what you see.** When an audit finds a real problem (missing OTEL span, coarse cliche, Crunch-in-World violation), fix it now or route it with OTEL evidence — don't defer to a "future audit pass."
- **Trust Keith's instincts on game feel.** When he says something felt wrong in play, he's right. Don't rationalize ("the narrator was probably trying to..."). Investigate OTEL first.

### Git / environment
- **Never use `git stash`.** Use `git worktree add` for dirty-tree operations.
- **Never checkout `main` in a subrepo.** `sidequest-content` targets `develop`. Only the orchestrator targets `main`.
- **Never edit files in `/Users/keithavery/Projects/oq-1`.** Parallel workspace, hands-off.
