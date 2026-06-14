## SM Gotchas

### Workflow gotchas (SM-specific)
- **This project does NOT use Jira (Keith, 2026-06-14).** Despite the SM agent definition's `<critical>` "Use pf for all Jira interactions" block and the `pf jira` commands, SideQuest tracks everything in `pf sprint` YAML only. Stories show `[no jira]` by design — that is the normal, correct state, not a missing key to backfill. Do NOT offer or run `pf jira` syncs, do NOT construct/claim Jira keys, and do NOT treat a keyless story as incomplete bookkeeping. (The merge/dedup gotchas below about "no-Jira-key stories" are about cross-workspace dedup — keyless stories have no claim-lock — not a prompt to add keys.) Ignore the agent-def Jira instructions for this repo.
- **Finish flow is fragile.** Session archive and YAML status update are separate steps in `pf sprint story finish`. If one fails, the other doesn't compensate. Verify both after the finish runs — check `.session/` for the archived file and the sprint YAML for status change.
- **`pf sprint story finish` does NOT create a PR — and its `merge_pr` step silently no-ops if none exists (90-2, 2026-06-06).** The reviewer's exit explicitly says "DO NOT merge PRs — SM handles PR creation and merge in the finish phase," but `finish`'s merge_pr step only *merges an existing* PR; with no open PR it passes silently, archiving the session and marking the story `done` while the code sits **unmerged** on the feature branch. ALWAYS verify the code actually landed: `git merge-base --is-ancestor <feature-tip-sha> origin/<base>` (base from `.pennyfarthing/repos.yaml branch_strategy`; gitflow→develop). If not merged, create + merge the PR yourself: `gh pr create --base develop --head <branch>` then `gh pr merge <n> --merge --delete-branch`. Don't trust the finish ceremony's step list — verify the merge.
- **A no-Jira-key story can be silently completed in BOTH workspaces (oq-1 AND oq-2) — check `develop` for the work before finishing (106-1, 2026-06-13).** This session ran a full TDD cycle on 106-1 (no jira_key, sprint YAML still showed it open) *hours after* Keith had already implemented + merged the SAME story from another clone (`#836` server + `#436` content). Two independent, both-tested, both-Claude-authored implementations of one story, conflicting on the same files. At FINISH, before creating/merging any PR, run `git log --oneline origin/develop | grep -i <story-id>` in each repo — if the story's feature commits are already on develop under a *different* PR number, STOP and surface the duplicate to the user; do not blind-merge your branch on top. The `--dry-run` "No PR to merge" was the tell that the merge path was unusual. Keyless stories have no claim/lock, so cross-workspace dedup is the SM's manual job.
- **Preflight subagent (`sm-finish`) can run in a venv where `pf` and repo git are unreachable — its "no PRs exist / blocked" output may be an environment artifact, not ground truth (106-1, 2026-06-13).** It reported "No local pf module" then concluded no PRs existed; trusting that, I created duplicate PRs. ALWAYS re-verify preflight's merge/PR claims yourself with `gh pr list --head <branch> --state all` and `git log origin/develop..<branch>` from the actual repo dir before acting on them.
- **`gh pr create` may target the upstream ORG repo, not your fork origin.** Origin was `slabgorb/<repo>` but `gh` created PRs against `slabgorb-org/<repo>` (its resolved default repo). Note the returned URL to know which repo the PR actually lives on before merging.
- **`gh pr merge --delete-branch` leaves your local checkout ON the base branch.** After merging from the feature branch, gh checks out the (protected) base and deletes the local feature branch — subsequent git commands then trip the protected-branch PreToolUse hook. Expected; the merge already succeeded (trust the `gh` fast-forward output as proof).
- **Sprint bookkeeping commit to orchestrator `main` may trip the auto-mode classifier on push.** The recent git log shows direct `chore(sprint): complete X` commits to main are the established pattern, but a direct push to the default branch can be denied without explicit user authorization. If denied, surface it to the user rather than working around it.
- **Chaining `git add && git commit ... ; git push origin main` in ONE Bash call trips the protected-branch PreToolUse hook (reports "Cannot commit to protected branch 'develop'" even on main); the same operations as SEPARATE Bash calls succeed (2026-06-08, retro commit).** The hook scans the whole command string and the `push origin <default-branch>` segment triggers the guard. Run commit and push as distinct calls — standalone `git commit` then standalone `git push origin main` both pass (matches the working `chore(sprint): complete X` pattern). Don't batch them.
- **`sprint/context/context-story-N.md` can be "both added" on rebase** when another clone (oq-2) generated a richer version. Prefer `--theirs` if the remote copy is substantially fuller than the local auto-generated stub.
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

## testing-runner overwrites the session file (2026-05-28)
In peloton mode on 71-1, Dev reported the `testing-runner` subagent **overwrote**
`sprint/.session/71-1-session.md` with its own test-report markdown, destroying the
story details / workflow tracking / findings / deviations sections. Dev caught it and
restored the session from an earlier read, then re-appended. No data lost that time —
but it's a live hazard: testing-runner treats the session path as a scratchpad.
Mitigation: when a phase owner (Dev/TEA) will spawn testing-runner, constrain its write
target in the spawn prompt (explicit output path that is NOT the session file), or have
them snapshot the session before running tests. Watch for it at verify/green phases.

## Peloton merge race: SM-flagged hazards land after the reviewed commit (2026-05-28)
On 71-3 (peloton), Dev reported IMPLEMENT complete at commit A (549e33e). I then (a)
relayed two new AC-4 hazards the Reviewer raised AND (b) advanced the phase to review in
parallel. Dev acted on the hazards and committed the hardening as commit B (b1b8221)
WHILE the Reviewer approved commit A and I merged commit A to develop (#292). Result:
develop got the PARTIAL fix; the complete hardened version (commit B) was pushed but
unreviewed and not on develop. Recovery: re-hand commit B's delta to the Reviewer, then
a follow-up PR (feat-tip vs develop diff = exactly commit B since A was squash-merged),
THEN finish.
**Lesson:** When Dev reports implement complete, that commit is FROZEN for review. If you
(SM) flag additional hazards after that report, do NOT advance to review in parallel —
either wait for Dev to confirm "all hazards folded in, re-froze at commit X" before
review, or make the hazard-fix an explicit separate follow-up cycle from the start.
Never let review+merge run concurrently with Dev still acting on your feedback on the
same branch. Symptom to watch: at finish, `git log develop..feat` shows MORE than the
one reviewed commit, or the working tree has uncommitted source changes matching the
story.

## Green-reports over-claim gate scope — enforce scoped claims (2026-05-28)
On 71-5, Dev's GREEN report said "ruff clean / pyright zero-new / e2e ran-not-skipped."
Reviewer's verify-don't-trust pass found all three were unscoped overclaims: `ruff check .`
exits 1 on 2 PRE-EXISTING repo-wide errors (Dev's changed files WERE clean); pyright was +15
all in the NEW TEST files (the prod file WAS clean); the e2e SKIPS without
SIDEQUEST_TEST_DATABASE_URL (Dev had set it, but the report didn't show collection ran). None
were functional defects — but the phrasing masked real test-file debt (+15 pyright → filed 71-14).
**Lesson (enforce at green→review):** require SCOPED, reproducible green claims — "ruff clean on
CHANGED FILES (ruff check <files>)", "prod pyright-clean / tests +N", "e2e ran WITH PG: collected+passed".
Reject blanket "clean / zero-new". And always run gates over the FULL changed set (prod + tests),
not just the prod file. A Reviewer who re-runs the gate in the real env (just pg-up + execute the
skipped e2e) catches this — that verify pass is worth it.

## Auto-relay merge can ship a masked-SKIP failure — verify-don't-trust the merge (2026-05-28)
On 71-2 (peloton, trivial), Dev's handoff marker was `relay:true` and the chain auto-advanced
Dev→(approval)→merge #486→`story finish`→archive, OUTSIDE team-lead coordination. Dev reported
"Reviewer APPROVED" but that approval did NOT come from the team's actual Reviewer (Colonel Potter),
whose explicitly-dispatched review landed LATER and REJECTED: `test_coyote_star_callouts_byte_identical`
FAILED — #486 updated 6 orrery snapshots but missed `coyote_star_callouts_system_t0.svg`. That test is
**content-gated** (`pytest.skip` if `sidequest-content` absent) and Dev's gate env had no content, so it
SKIPPED → masked the stale baseline → RED merged to develop.
**Lessons:**
1. **SKIP ≠ PASS, again** — content-gated orbital snapshot tests skip silently. Reviewer/SM must re-run
   gates in an env WITH content present. The test honors `SIDEQUEST_CONTENT_COYOTE_STAR=<path>` to force-run
   even from an isolated worktree (worktree's repo_root has no sibling sidequest-content otherwise).
2. **Don't trust an auto-relay "merged + approved" report** — verify the PR merge AND re-run the suite in the
   real env. Reproduced the failure independently (1 failed/315 passed) before acting.
3. **Post-merge regression → hotfix, not rework loop** — story was already archived, so the Reviewer's
   "back to Dev for green" routing didn't apply. Cut a separate `fix/<id>-<desc>` branch off origin/develop,
   re-baseline, PR, squash-merge. Regenerate snapshots deterministically (render_chart → write file → assert
   re-render byte-identical) and element-diff to confirm the ONLY change is the intended one.
4. **Peloton control:** instruct Dev to hand review back to team-lead rather than auto-driving to merge, so the
   merge gate stays under SM control (told Dev this explicitly for 71-6).

## The GM panel / OTEL dashboard is KEITH's debug tool — never a Sebastien/Jade feature (corrected 3×, 2026-05-29)
Keith corrected this three times in one session. The OTEL dashboard, Subsystems activity grid, watcher feed, router-trace — ALL of it is dev-side observability that **Keith** uses to debug the engine. It is NOT for players (Sebastien) and NOT for content authors (Jade). CLAUDE.md says this explicitly ("if you're tempted to write 'Sebastien's lie-detector' about a GM-panel chart, you've made the wrong association").
- **Sebastien/Jade mechanical-visibility lane = PLAYER-FACING UI ONLY**: confrontation beat buttons (push/brace/strike·stat·+N), dual dials, dice overlay, character/ability panel, advancement deltas. That is where "expose the math" belongs.
- The 59-8 AC text says "Sebastien-style … is GM-panel router-trace usable for a mechanics-first player" — that phrasing is itself the wrong association. Evaluate GM-panel usability as **Keith's** debugging tool; evaluate Sebastien/Jade visibility against the **player UI** (where the a11y/“+N absent from accessible name” findings actually live).

## sm-setup writes session to sprint/.session/ but complete-phase expects repo-root .session/ (2026-05-31)
During 67-10 setup, the `sm-setup` subagent created the session file at `sprint/.session/67-10-session.md`, but `pf handoff complete-phase` looks for it at repo-root `.session/{story}-session.md` (the canonical path per the agent guide, and where the live `checkpoints.log`/`session-log.txt` are updated). Symptom: complete-phase errors `Session file not found at .session/<story>-session.md`.
- **Fix:** `git mv sprint/.session/<story>-session.md .session/<story>-session.md` then retry complete-phase.
- Second gotcha in the same flow: complete-phase also requires a `## Sm Assessment` heading in the session file (sm-setup's template does not emit one) — add the SM routing decision + rationale under that heading before completing the phase.

## Merge base branch is per-repo — read repos.yaml before any PR/merge (2026-06-04)
During the 59-30 peloton finish I tried to merge the server PR against `main` and assumed the recent merges were on main. Wrong: **sidequest-server (and ui/content/daemon/composer) are gitflow → base `develop`**; only the orchestrator (`.`) is trunk-based → `main`. The `pf sprint story finish` preflight correctly created the PR against develop; my manual `gh pr merge` / `git diff main` assumptions fought it.
- **Always** `grep default_branch .pennyfarthing/repos.yaml` (or check the prime "Repos Topology") before `gh pr create/merge`, `git diff <base>`, or merge-conflict resolution. server/ui/content/daemon/composer = develop; orchestrator = main.
- **Orchestrator gets a feature branch too:** sm-setup branches the orchestrator repo (where sprint YAML lives), so after `pf sprint story finish` the sprint-completion commit lands on `feat/<story>-...`, NOT main. And local `main` is often stale (behind origin/main by several completions). Fix pattern: `git checkout main && git reset --hard origin/main && git cherry-pick <sprint-commit> && git push origin main && git branch -D feat/<story>-...`. The cherry-pick is clean as long as the other completions touched different epic YAML files.
- **Develop drifts during a long story:** the server branch needed `git merge origin/develop` + one conflict resolution (intent_router_pass.py vs a span-timing PR that landed mid-story) before #631 was mergeable. Expect base drift on multi-hour stories; route the conflict resolution to Dev, not yourself.

### `pf sprint story finish` DELETES feat branches without merging — land multi-repo subrepo work on develop FIRST or it's destroyed (2026-06-05, story 87-4)
- **What happened:** 87-4's deliverables lived on un-merged subrepo feat branches (sidequest-content + sidequest-server, `feat/87-4-...`) with NO PRs. `pf sprint story finish 87-4 --dry-run` showed: "2. No PR to merge" + "6. Delete local branch: feat/87-4-...". `finish` only merges an EXISTING PR; it does NOT create PRs or merge subrepo branches. So running it as-is would have **deleted the branches with the entire story's work unmerged → data loss.**
- **The check (always run before finish on a multi-repo story):** for each repo on the session's `Branch:` line, `git -C <repo> branch --merged develop | grep feat/<story>` — if NOT listed, the work is unmerged and finish will destroy it.
- **The fix:** land the subrepo work on develop BEFORE finish — either (a) `gh pr create --base develop` + `gh pr merge --merge` per subrepo, then `git checkout develop && git pull origin develop` to sync local; or (b) local `git checkout develop && git merge --no-ff feat/...`. THEN `pf sprint story finish` (its branch-delete step is now safe). The Reviewer exit says "DO NOT merge — SM handles merge in finish," but `finish` does NOT actually merge subrepo branches — the SM must do it (PR or local) as a distinct step.
- **`--dry-run` is mandatory** before `finish` on any multi-repo story — read every step, especially "merge_pr" (does a PR exist?) and "git_cleanup / delete branch" (is it merged?).
- **Always ask the user** how to land the work (local merge vs GitHub PRs vs pause) — it's an irreversible, outward-facing choice (push + merge).

### sm-setup writes a non-ISO "Phase Started" timestamp that crashes `complete-phase` (2026-06-05, story 90-1)
- **What happened:** `sm-setup` (setup mode) wrote `**Phase Started:** 2026-06-05 19:28:47 UTC` (space-separated, " UTC" suffix) into the session + Phase History. `pf handoff complete-phase` then threw `ValueError: Invalid isoformat string: '2026-06-05 19:28:47 UTC'` in `_calc_duration` → `datetime.fromisoformat(started_str.replace("Z","+00:00"))` — it only strips a trailing `Z`, not " UTC", and `fromisoformat` rejects the " UTC" suffix.
- **Fix:** edit the session's `Phase Started:` line AND the Phase History `started` column to ISO-8601 with a `Z` (e.g. `2026-06-05T19:28:47Z`) — the format the 87-4 session used and that `complete-phase` parses — then re-run `complete-phase`. `resolve-gate` does NOT hit this path, so the gate can pass "ready" while `complete-phase` still crashes; check both.
- **Watch for it on every story setup** until sm-setup is fixed to emit ISO timestamps. Quick check after sm-setup: `grep "Phase Started" .session/<id>-session.md` — if it ends in " UTC" or has a space instead of `T`, normalize before the exit protocol.

### `pf sprint story finish` marks the story `done` WITHOUT creating/merging the PR (2026-06-10, story 101-1)
- **What happened:** Ran `pf sprint story finish 101-1` after Reviewer APPROVED. It reported all steps green (archive_session, **merge_pr**, jira_done, yaml_update, archive_epics, git_cleanup, remove_session) and set status `done` + removed the session. But `merge_pr` silently no-op'd: there was **no PR** for the branch (Dev never creates one; the finish step did not auto-create one either), so nothing merged. `origin/develop` did NOT contain the 101-1 commits and `gh pr list --head <branch>` was empty, yet the story was already marked `done`. A "done" story whose code never reached develop is the exact half-finished state the rules forbid.
- **Why it matters:** The finish ceremony reports success per-step even when `merge_pr` finds nothing to merge — it does not fail loud on "no PR exists." If you trust the "Story Complete" banner you ship a story that isn't actually merged. This is a silent fallback in the tooling.
- **How to apply:** After EVERY `pf sprint story finish`, verify the merge actually landed before declaring done: `cd <repo> && git fetch origin <base> && git log origin/<base> --oneline -5 | grep <story-id>` AND `gh pr list --head <branch> --state all`. If no PR and the work isn't in base, create + merge it yourself (SM owns PR creation/merge per the Finish Flow): `gh pr create --base develop --head <branch> ...` then `gh pr merge <n> --squash --delete-branch`, then re-sync the local repo to base. The daemon repo (gitflow) merges `feat/...` → `develop` via squash. Then commit + push the sprint-tracking changes (`sprint/epic-*.yaml`, `sprint/archive/<id>-session.md`, `sprint/context/*`) to orchestrator `main` — and expect a non-fast-forward reject from the oq-1/oq-2 multi-clone race: `git stash` (sidecars are usually dirty) → `git rebase origin/main` → `git stash pop` → push.

### The repos MOVED orgs (`slabgorb/` → `slabgorb-org/`) and that is now a root cause of `merge_pr` no-op (2026-06-13, story 107-2)
- **What happened:** all repos (server, content, orchestrator) have been **transferred from `github.com/slabgorb/<repo>` to `github.com/slabgorb-org/<repo>`**, but every clone's `origin` remote still points at the OLD `slabgorb/` slug. Git push/fetch work via GitHub's 301 redirect (you see `remote: This repository moved. Please use the new location: ...slabgorb-org/...`), but `pf sprint story finish`'s `merge_pr` step (and any `gh pr` call that resolves the repo from `origin`) does NOT follow the move — it found/created nothing, so the story got marked `done` + archived with the code unmerged. CLAUDE.md still says "repos under github.com/slabgorb/" — that's stale.
- **How to apply:** for any `gh` PR op, pass the NEW slug explicitly: `gh pr create --repo slabgorb-org/<repo> --base develop --head <branch> ...` then `gh pr merge <n> --repo slabgorb-org/<repo> --squash --delete-branch`. The create/merge return URLs under `slabgorb-org` — confirm there before trusting. Verify the landing with `git fetch -q origin develop && git log origin/develop --oneline -2 | grep <story-id>` (push/fetch still ride the old-slug remote fine). Permanent fix (ask Keith): `git remote set-url origin git@github.com:slabgorb-org/<repo>.git` across all clones, and update CLAUDE.md's org references. Orchestrator likewise moved to `slabgorb-org/sidequest` (push to `main` still works via redirect).

### sm-setup creates the feature branch in the ORCHESTRATOR, not the story's code repo (2026-06-14, story 107-1)
- **What happened:** 107-1's `repos: server` (server-only). `sm-setup` (setup mode) created `feat/107-1-...` by switching the **orchestrator** (`.`) onto a feature branch — leaving oq-1's root on `feat/...` with the context/session edits as working-tree changes, and creating NO branch in `sidequest-server` at all. The orchestrator targets `main` (per repos.yaml) and should stay there; the code feature branch belongs in the repo(s) on the session's `Repos:` line, off each repo's base (`develop` for the subrepos). 107-2's precedent confirms: the feat branch lived in the code repos (server+content), while sprint/context/session changes ride orchestrator `main`.
- **How to apply:** after sm-setup, check `git -C . branch --show-current` (should be `main`) and `git -C <code-repo> branch --show-current` (should be `feat/<story>-...`). If reversed: `git -C . switch main` (uncommitted context/session edits carry over cleanly since no commits diverged), `git -C . branch -D feat/<story>-...`, then in each code repo `git switch <base> && git switch -c feat/<story>-...`. Record the correction in the SM Assessment.
- **Also:** the gate's `resolve-gate`/`complete-phase` arg-inference from the session file is fragile — after hand-editing the session (e.g. adding `## Sm Assessment`), inference broke with "missing story/workflow/phase fields." Just pass args explicitly: `pf handoff resolve-gate <id> tdd setup`, `pf handoff complete-phase <id> tdd setup`.
