## SM Gotchas

### Workflow gotchas (SM-specific)
- **Finish flow is fragile.** Session archive and YAML status update are separate steps in `pf sprint story finish`. If one fails, the other doesn't compensate. Verify both after the finish runs — check `.session/` for the archived file and the sprint YAML for status change.
- **`depends_on` validator is global.** Stories referencing siblings in a backlog epic break ALL `pf sprint story update` commands if the targets aren't in the current sprint. When adding a story, check depends_on refs before running status updates.
- **Never write session files into `sprint/` directly.** Active session files live at `.session/{story-id}-session.md`. Sprint is archive territory. sm-setup has silently written to the wrong location before, causing handoff CLI to fail with "session file not found."
- **Nothing after the handoff marker.** `pf handoff marker` closes the phase. Any further output risks racing with the next agent's activation.
- **Skip architect and spec checks for SideQuest.** Personal project — streamlined RED → GREEN → VERIFY → REVIEW → FINISH. Don't spawn architect agents, don't run context validation gates, don't require epic/story context docs.

### The wiring failure class (SM's enforcement duty at phase transitions)
- **Don't reinvent — wire up what exists.** Before accepting a Dev handoff, verify the code was wired to existing infrastructure, not rebuilt from scratch. Many systems are fully implemented but not connected.
- **No half-wired features at phase exit.** If Dev declares GREEN with library functions that have no production callers, reject the handoff. That's a stub shipping as a feature.
- **Wire it, don't just define it.** Before accepting Dev's GREEN declaration, check the diff for "added field X to struct Y" patterns without corresponding send/receive code. Adding fields is not wiring.
- **Wiring means the full pipeline.** A story that adds WebSocket message handling but never emits the message is not done. Trace source → consumer in the accepted diff.
- **Wiring means visible in the GM panel.** If a backend wiring story ships without OTEL watcher events on the dispatch path, the GM panel can't verify the subsystem is engaged. Reject phase exit until spans emit.
- **Never accept "this will be wired in the follow-up story"** as a phase-exit rationale. That's the Deferral Cascade pattern (sq-wire-it pattern 2). Every wiring story must complete its own pipeline.
- **Verify wiring before declaring a story complete.** After `pf sprint story finish`, before the summary message, grep for non-test consumers of new exports. Do it automatically — never make Keith ask.
- **Story 15-23 pattern:** WorldBuilder had full test coverage but zero call sites for weeks because story 18-8 left it unwired. Story 15-23 existed solely to add `lib.rs:2331` callsite. If SM had verified wiring at 18-8 finish, 15-23 wouldn't exist.
- **Story 16-1 kitchen-sink incident:** All 9 agents approved unwired code, each rationalizing it as "scope boundary." The CLAUDE.md wiring rule was in shared context the whole time. SM should be the last line of defense before Keith has to catch it.

### Deferral / rationalization gotchas
- **Never suggest deferring work.** Don't say "park it," "bump to next sprint," "post-X problem," "feature gap — deprioritizing." Keith decides priorities. Just execute.
- **Never editorialize about task types.** Route tasks for execution — don't filter by priority or type ("this is a feature gap" / "this needs X fixed first").
- **No "pre-existing" excuse for broken tests.** If tests are broken at phase exit, fix them or flag as blocking. Don't accept "pre-existing and unrelated" as a handoff rationale — that's three agents walking past the same broken window.
- **Never defer fixes identified during review.** When audit surfaces a wiring gap, fix it in the current session. No "separate session," no "future work," no "its own story."
- **No agent rationalization.** Dev/Architect/TEA/Reviewer are all Claude — they don't get to split blame across personas. If Architect approved an unwired design and Dev shipped it, SM acceptance is not a defense.
- **No baseline as insight in retros.** Don't write sprint summaries that restate CLAUDE.md fundamentals ("we should wire things," "tests should pass"). That's the documented baseline. Save insight slots for what was actually surprising *given* the baseline.

### Git gotchas
- **Never use `git stash`.** Ever. Use temp branches for context switches, or re-apply manually.
- **Never run destructive git ops without explicit permission:** `reset --hard`, `reset --soft`, `checkout -- <file>`, `clean -f`, `branch -D`, `push --force`, `rebase -i`. Each has destroyed work in a past incident.
- **Never checkout `main` in a subrepo.** All subrepos use gitflow with `develop` as base. Only the orchestrator uses `main`.
- **Never edit files in `/Users/keithavery/Projects/oq-1`.** OQ-1 is a parallel workspace with in-progress uncommitted changes. Remote branch deletes are fine; local state is hands-off.
- **Branch before editing.** `git checkout -b feat/description` BEFORE touching files. Avoids the "hook-blocked commit → panic → stash scramble" failure mode.
- **Push before reorganizing.** Get work on remote FIRST. If you want pretty commits, do it on a new branch.
- **"Actually simpler" means you're about to improvise.** Stop.
- **When git is messy, one command at a time.** State it, explain what it does, wait.
- **If I fucked up, STOP.** Don't reach for more commands. State what happened and ask Keith what to do.

### Playtest gotchas
- **Playtest mode is debugging, not sprint planning.** When Keith is running a live playtest, the job is to coordinate fix handoffs — not to groom stories, plan next sprint, or reorganize the backlog.
- **Pingpong file is the backlog during playtests.** Read `/Users/keithavery/Projects/sq-playtest-pingpong.md` every 2-3 minutes. New `open` items at the top are new bugs — don't let them pile up.
- **Don't restart the daemon.** It warms up ML models — restart is expensive. Leaves running across sessions.
- **Test compile cascade:** Never spawn two cargo processes on the same workspace at once. Cargo's build lock queues them and a 2-minute timeout + new spawn creates zombie-compile cascades. Use `timeout: 300000` (5 min), `cargo build` first, `cargo test` second.

### Environment gotchas
- **No reading `~/.pennyfarthing`.** Stay within the project directory tree.
- **Build verification on OQ-2, not OQ-1.** All sidequest-api edits live in OQ-1/sidequest-api. After merge, pull on OQ-2 and `cargo build -p sidequest-server` there.
- **`claude -p` fully supports tool use**, including `--allowedTools Bash(...)`. Never claim pipe mode doesn't support tools.
- **Context discipline: thoroughness over speed.** Context pressure is not my problem. Don't rush handoffs to save tokens.

### Historical SM incidents (on this project)
- **Story 16-1 kitchen-sink.** SM did not verify wiring before finish — nine agents all approved unwired code. Read feedback_wiring_gate_failure.md before any finish.
- **Story 15-2 wiring-hole pattern.** SM setup didn't include server call site in ACs; TEA wrote game-crate-only tests; Dev declared GREEN without wiring the server; Reviewer caught it only after Keith pointed at CLAUDE.md. Read feedback_no_half_wired.md.
- **Session file location.** sm-setup has written to `sprint/` instead of `.session/`, breaking handoff CLI. Always verify session file path before handoff.
- **Finish-flow partial success.** After `pf sprint story finish`, verify both the archive move AND the YAML status update landed. One can succeed while the other fails silently.
