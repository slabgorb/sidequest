## SM Patterns

### How to work with Keith
- **Senior architect, 30-year dev, full product perspective.** He wore every hat at startups. Trust his scope/priority calls. Talk at the architectural abstraction level — pattern names, trade-offs, system decomposition.
- **Procedural generation domain expert** — MUSHcode, populinator, conlang, gotown lineage. SideQuest content systems are mature, not experimental.
- **Velocity calibration: ~20x human dev speed, sustained.** Don't size sprints based on what a human would do. Parallel agents change the math 5-10x on parallelizable work. There is no "too much for one sprint."
- **Dictation artifacts** ("axiom" → "axum", "SERG" → "serde", "playlist" → "playtest"). Parse for intent.

### Handoff CLI protocol (the SM primary workflow)
- **The canonical phase exit sequence:** `pf handoff resolve-gate` → gate check → `pf handoff complete-phase` → `pf handoff marker`. If marker output contains `relay: true`, invoke the named skill (`/pf-dev`, `/pf-tea`, etc.) via the Skill tool. Otherwise output the fallback and EXIT.
- **Nothing after the marker.** Once `pf handoff marker` runs, the phase is closed. Any further output risks racing with the next agent's activation.
- **Session file path:** `.session/{story-id}-session.md`. Read `**Phase:**`, `**Workflow:**`, `**Repos:**` at startup. Never write session files directly into `sprint/` — that's archive territory, populated only by `pf sprint story finish`.
- **Before starting new work, check phase ownership.** `pf workflow phase-check {workflow} {phase}` returns the current owner. If it's not me, run `pf handoff marker $OWNER` and relay instead of forcing my phase.

### Story lifecycle enforcement
- **Story completion is mandatory.** A story is NOT done until: (1) reviewer approves and merges the PR, (2) SM runs `pf sprint story finish` (archive session, update Jira, clean up). Never mark complete on PR approval alone.
- **Never start new work with blocking open PRs.** The merge-ready gate blocks `/pf-sprint work` if non-draft PRs exist for stories not in `in_review` status. PRs for `in_review` stories are OK (awaiting external review). If stuck in "merged but not finished," run `/pf-reviewer` or `/pf-sm` as appropriate.
- **Verify wiring before declaring a story complete.** After `pf sprint story finish`, before the summary message, grep the merged branch for the new exports in non-test production code paths. Report the wiring check result as part of the completion summary. Do this automatically — never make Keith ask.
- **Spec authority:** story scope (session file) > story context > epic context > architecture docs / SOUL / rules. When sources conflict, the session scope wins. Log deviations in the session file's `## Design Deviations` section at the moment of decision, not at phase exit — the deviations-logged gate validates at exit and rushed entries miss fields.
- **Finish flow is fragile.** Session archive and YAML status update are separate steps. If one fails, the other doesn't compensate. Verify both after `pf sprint story finish`.

### Phase-ownership enforcement for wiring stories
- **Wiring stories must name the specific call site in the ACs at setup time.** Not "X is usable by the server" — "X is called from `dispatch_player_action()`, and result flows to the WebSocket as message type Z." If the session file's ACs don't name the call site, reject the setup and send it back to PM/BA.
- **TEA must write a wiring test, not just unit tests.** Before handing off from TEA to Dev, verify at least one test exercises the production code path end-to-end. If every test stops at the component/library boundary, reject the phase exit.
- **Dev must verify non-test consumers before declaring GREEN.** Library functions with no production callers are stubs, not features. Before accepting Dev's assessment, grep for the new exports in non-test code.
- **Reviewer is the backstop, not the primary enforcement.** Every earlier phase must catch wiring gaps — if it reaches reviewer unwired, the whole chain failed and the incident should be logged as a process failure, not just a fix.

### Git / branch patterns
- **Gitflow on every subrepo.** Subrepos target `develop`, only the orchestrator targets `main`. Always check `repos.yaml` before any git op.
- **Additive git ops need no permission** (commit, push non-force, pull --ff-only, checkout existing, checkout -b, fetch, add). Keith explicitly asked me to stop being tentative with these.
- **Destructive git ops always ask first** — `reset`, `clean`, force-push, `branch -D`, `rebase -i`, `stash` (banned outright). Each has destroyed work in a past incident.
- **Dirty work comparison pattern.** When local uncommitted changes conflict with a pull: commit dirty work to a temp branch, pull clean on the default branch, diff each file local-vs-remote side by side, categorize (identical / remote better / local has extra value / no remote change), cherry-pick deliberately. Never stash.
- **When a hook blocks a commit**, the working tree is fine. Run `git status`. Changes are still there. Fix the issue (wrong branch, etc.) and recommit. Don't stash, don't blame a linter, don't assume code was lost.

### Playtest coordination
- **Pingpong cadence: every 2-3 minutes during active playtest.** Read `/Users/keithavery/Projects/sq-playtest-pingpong.md` frequently. New `open` items at the top are new bugs from OQ-1 — don't let them pile up.
- **Update pingpong status immediately when a fix lands** — not in batches. `open` → `in-progress` → `fixed` → `verified`.
- **Rotate the pingpong at natural breakpoints.** When all tasks are fixed/verified and dev is idle, archive to `/Users/keithavery/Projects/sq-playtest-archive/{timestamp}.md` and start fresh.
- **Always pull and test on new commits.** When `git log HEAD..origin` shows new commits during playtest: pull → rebuild → restart → test. No "want me to?" prompts.
- **Always rebuild on restart.** Every service restart during playtest is a full rebuild. Compile time is negligible vs debugging a stale binary.
- **Keep going.** Work through the checklist autonomously during playtest — don't pause to ask "want me to continue." Keith wants momentum.
- **Restart in existing tmux panes** via Ctrl+C + re-run. Don't close/reopen panes.

### Context discipline (SM's particular responsibility during high-ceremony sessions)
- **Thoroughness over speed.** Context pressure is not my problem — the system manages it via TirePump, relay, `/clear`. Don't rush a handoff, skip subagent results, or abbreviate a gate check to save tokens. Cutting corners costs more context than doing it right. If a gate fails because I cut corners, the whole phase repeats.
- **The right response to high context is a clean handoff, not a rushed one.** Complete the assessment, run the exit protocol, trust relay mode.
