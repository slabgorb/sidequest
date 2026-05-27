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
- **Fix what you see during finish verification.** If a wiring check fails or a test is broken at finish time, don't archive the story and file a follow-up — block the finish and route back. Every "we'll address in the next sprint" is debt compounding on Keith.
- **No dressed-up scope shields in sprint coordination.** Forbidden framings at phase exit or in sprint retros: "out of this branch's scope," "incremental retirement path," "tracking comment in TECH_DEBT.md," "honest green via #[ignore]," "deferred to follow-up story." Any of these from Dev/TEA/Reviewer is a signal to reject the handoff, not accept it. 2026-04-14 incident: Dev ignored 39 broken integration tests and called it "honest green" — Keith caught it at review. SM should have caught it at finish.
- **Wiring tests are mandatory for story acceptance.** A story that disables wiring tests via `#[ignore]`/`it.skip`/comment-out has broken a CLAUDE.md rule. Reject the finish.
- **Verify story not already shipped** before claiming a backlog story. Cross-machine drift between OQ-1 and OQ-2 means a session file can say "phase: green, reviewer rejected" while `origin/develop` on both clones already has the fix merged. Check `git log origin/develop --grep="<story-id>"` and `gh pr list --state merged --search "<story-id>"` before acting on a stale session verdict. 37-10 lesson: session file was rejected post-merge; fixes were already in develop.

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

## Migrated from auto-memory (2026-05-26)

- **`sprint/current-sprint.yaml` MUST be sharded** — `epics:` is a list of string refs (`['51','53',...]`), each epic in its own `sprint/epic-<id>.yaml`. Inline-dict epics are SILENTLY dropped by the Frame TUI (`pf/frame/ws_push.py:fetch_sprint()` is shard-only) while the CLI tolerates them — the two paths disagree. When adding an epic, write the full shard file + append a string ref; never embed inline. If `pf sprint status` shows more epics than the Frame TUI, suspect inline-dict drift. (Upstream bug pennyfarthing#50.)
- **oq-1 and oq-2 can claim the same story id in parallel** — the next-id picker is local with no cross-clone registry. Before `sm-setup` in any clone, `git fetch origin && git status` and pull if behind. A non-fast-forward push at finish is a tracker-collision smell — inspect `git log HEAD..origin/main` for a duplicate `chore(sprint): complete <id>`. Resolution: renumber the second-to-merge story (subrepo branch/PR labels can't be retroactively renamed — note the drift in YAML).
- **SideQuest never uses Jira — permanently.** Omit `--jira` from every `pf sprint story add`, never run `pf jira *`, never propose a Jira key or ask to attach one. Work is tracked entirely through pf sprint YAML.
- **Verify which plan tasks already shipped before creating stories from a plan** — plans can be days behind the repo. Probe `git -C <repo> log --oneline -20 -- <target-paths>`; skip or shrink stories whose scope is already on develop (2026-05-24 reference-v3: 3 of 5 stories ~95% already shipped, costing a full coordination cycle).
- **Scope `theme.yaml`/validated-YAML field-add stories `--repos content,server`** — genre-pack models use pydantic `extra="forbid"`, so a content-only field add takes the server down at startup with `ValidationError`. The paired server-model update must land in the same PR.
- **`pf sprint story finish` can mark a story `done` + archive the session WITHOUT actually merging the PR** (2026-05-27, 69-2). The finish script printed step `2. merge_pr` but PR #288 stayed OPEN (MERGEABLE/CLEAN, no blocking checks) — develop never advanced. Bookkeeping (status→done, session removed, YAML/epic update, push) all completed, leaving the code stranded off `develop`. ALWAYS verify the merge after finish: `gh pr view <n> --json state,mergedAt` must show `MERGED`. If still OPEN and mergeable, complete it manually: `gh pr merge <n> --merge --delete-branch` (repo uses gitflow merge-commits off `develop`), then `git checkout develop && git pull`. Don't trust the step list printing as proof the step ran.
- **`pf handoff complete-phase setup→red` does NOT block on missing context files** (2026-05-27, 69-2). sm-setup created the session but never wrote `sprint/context/context-story-<id>.md` / `context-epic-<id>.md`; the `sm-setup-exit` resolve-gate returned `status: ready` (it found the SM assessment) and complete-phase succeeded — then TEA's RED context gate hard-blocked because the context didn't exist. The gate's `create_context` recovery did not fire/persist. Mitigation: after sm-setup, explicitly `pf validate context-story <id>` and `context-epic <id>` BEFORE handing to RED; if missing, author them (or run /pf-context) during setup rather than letting RED stall. Architect authored them as recovery this run.

## `pf sprint story finish` breaks on `N-followup-X` story IDs (2026-05-27)

`pf sprint story finish 61-followup-B` fails at the yaml-update step with
`Invalid story ID format: 61-followup-B` — pf's story-ID parser expects `N-N`
and rejects the `followup` suffix. Partial state on failure: session is COPIED
to `sprint/archive/` (original not removed), `review_verdict: approved` gets
added to the story in the epic YAML, but `status` is NOT transitioned and the
session file is NOT removed. Also observed: status transitions never fired into
`epic-61.yaml` during claim/in-progress either — the sprint-YAML integration is
non-functional for followup-suffixed IDs throughout the pipeline, not just at finish.

Also note: `finish` does NOT create a PR — its dry-run shows "No PR to merge" when
none exists. It only merges a pre-existing PR. For a story where Dev pushed a branch
but no PR was opened, you must `gh pr create` + merge separately to integrate.

Recovery when finish breaks on a followup ID: complete by hand matching the sibling
precedent in the same epic file (`status: done`, `completed: <date>`, `pr:`, `branch:`
— see 61-followup-A / 61-followup-D), remove the `.session/` file (archive copy already
exists), commit to main (orchestrator targets main, not develop). FIX: pf story-ID
parser should accept `N-followup-[A-Z]` and `N-N` alike.

## Finish ceremony does NOT merge code; `develop` is protected (2026-05-27, 65-2)
`pf sprint story finish` marks the story `done`, archives the session, and updates
sprint YAML — but its `merge_pr` step is a **no-op here** (no `pr_strategy` in repos.yaml):
it creates no PR and merges nothing. After finish, the feature branches still hold the
code. **You must integrate manually**, and `develop` is a **protected branch** — a
direct `git push origin develop` is blocked by a PreToolUse hook. Use
`gh pr create --base develop --head <branch>` then `gh pr merge <#> --merge --delete-branch`
per subrepo. The orchestrator targets `main` (also via PR, e.g. 65-1 #302 / 65-2 #303),
but `main` itself is **not** push-protected. Always verify post-finish that the code
actually reached develop (`git cat-file -e origin/develop:<file>`), not just that status=done.

## Root `.session` must be a symlink to `sprint/.session` (2026-05-27)
`pf handoff complete-phase` resolves the session at `<repo_root>/.session/{id}-session.md`,
but sm-setup writes/commits sessions to `sprint/.session/`. The bridge is a symlink
`<root>/.session -> sprint/.session`. If that symlink gets clobbered into a real dir
(stray tooling writing into it), complete-phase fails "Session file not found." Fix:
collapse the real dir's contents into `sprint/.session/` and recreate the symlink.

## pg test suite env (2026-05-27)
`tests/persistence/*` + any test using the `migrated_db` fixture SKIP unless
`SIDEQUEST_TEST_DATABASE_URL` is set (e.g. `postgresql://$USER@localhost:5432/sidequest_test`,
provisioned by `just pg-up`). A "skip" is NOT a passing RED/GREEN — set the env first.
Use `-n0` to disable xdist (it's in addopts); `-p no:xdist` breaks the `-n` flag.
