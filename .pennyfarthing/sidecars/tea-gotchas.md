## TEA Gotchas

### Confrontation resolution has MULTIPLE overlapping resolvers — find the incumbent before writing outcome tests (59-31)
- The per-turn sweep at the bottom of `_apply_narration_result_to_snapshot` runs resolvers IN ORDER, each short-circuiting on `enc.resolved`: `_resolve_if_no_opponent_remains` (4350, → `opponent_withdrew`) then `_resolve_dial_threshold_and_phase` (4359). The location-change handler (~2790) resolves EARLIER in the same call (→ `abandoned_on_location_change` / `player_victory` via `dial_threshold_outcome()`). So an "all opponents withdrawn" state already has an incumbent label (`opponent_withdrew`) — a new outcome story must RELABEL/REPLACE the incumbent, not add a resolver after it (the incumbent wins by running first).
- When writing outcome-label tests, drive the real entry `_apply_narration_result_to_snapshot(snap, NarrationTurnResult(...), player_name=, room=room_for(snap))` (no pack needed for the sweep), not the internal helper — survives whichever helper the Dev edits, and proves wiring.
- Confrontation OTEL is emitted via `_watcher_publish(event, fields, *, component="confrontation")` (sibling events: `confrontation_resolved_on_location_change`, `confrontation_deactivated_on_location_change`). Capture in tests by `monkeypatch.setattr(narration_apply, "_watcher_publish", _capture)` — the `component=` kwarg is how you filter confrontation events. `encounter_resolved_span` (the dial sweep's emit) is a separate OTEL-span channel that does NOT take `component=`; don't conflate the two when picking an assertion target.
- `dial_threshold_outcome()` (encounter.py:243) is a METHOD on StructuredEncounter, gated to `win_condition=="dial_threshold"`. An "alongside" helper the Architect asks for should also be a method; decide deliberately whether it inherits the win_condition gate (opponent-yield should NOT — a surrender is a win in combat too).

### The wiring failure class (the dominant bug category in this project)
- **Don't reinvent — wire up what exists.** Before building anything new, grep the codebase. Many systems are fully implemented but not wired into the server or UI. CLAUDE.md rule #3.
- **No half-wired features.** Connect the full pipeline or don't start. If something needs 5 connections, make 5 connections. Shipping 3 and calling it done is the exact failure mode Epic 15 was created to clean up.
- **Wire it, don't just define it.** Adding fields to a struct is not wiring. Adding props to a component is not wiring. Data must actually flow from source → consumer. If no code populates and transmits the field, the feature isn't done.
- **Never rationalize unwired code.** When `/sq-wire-it check` reports FAIL (no non-test consumers), the answer is **wire it**. Do not write paragraphs explaining why this time is different. If I catch myself typing "this is acceptable because" — STOP. That sentence is the bug. The wiring usually takes 5 minutes; the rationalization takes longer.
- **"Wiring means dashboard."** Internal data flow without OTEL visibility is not wired. A missing `WatcherEventBuilder::new(...)` call on a subsystem's dispatch path is a blocking wiring bug, never a "non-blocking improvement." Labeling an OTEL gap as non-blocking in my own audit is the exact self-compounded failure I hit in the 2026-04-09 Map fix.
- **No agent rationalization.** Dev/Architect/TEA/Reviewer are all Claude — they don't get to split blame across personas. "The Architect said it was fine" is not a defense. If a wiring gap is identified in any phase, the only valid response is "fix the code now," never "clarify the spec" or "file a follow-up story."
- **Verify wiring before claiming done.** `grep` for non-test consumers on the merged branch before marking a fix as complete. Don't wait for Keith to ask. A playtest with the GM panel open is the acceptance test.
- **Verify end-to-end before claiming fixed.** Code review is not verification. Trace the full wire path: source → channel → writer task → WebSocket → client handler → DOM. Session 7 had six consecutive "fixed" claims on the turn-lock bug, each found a real issue, none verified the message actually arrived at the browser.
- **Wiring gaps require action, not acknowledgment.** Finding a wiring gap and saying "yep that's a wiring gap" is worthless. Fix it. Log it. Check for siblings (if one compute-then-ignore exists, grep for the pattern). Verify OTEL. Don't move on.
- **Kitchen-sink gate failure is real** (story 16-1): nine agents approved unwired code because every phase rationalized it as "scope boundary" and "wiring comes in subsequent stories." The wiring-check gate exists in `.pennyfarthing/gates/` — every agent must enforce it, not just the reviewer as a backstop.

### No stubs, no fallbacks
- **No stubs. Ever.** When I hit a scope error or type mismatch, solve the actual problem. Don't substitute `Default::default()`, placeholder values, or restructure the design to avoid the issue. CLAUDE.md line 124: "Never say 'the right fix is X' and then do Y." Do X. If `snapshot` isn't in scope, move the code to where it is.
- **No silent fallbacks.** If a path/config/resource isn't where it should be, fail loudly. No `if not exists: try_other_thing`, no `unwrap_or_default()` that papers over missing data, no `Option::None` degradation on required fields.
- **No layered fallback design.** If the LLM is down, the system is down. Keyword intent classification "working" while narration is broken is not meaningful resilience — it's dead code with delusions of usefulness.
- **No reading `~/.pennyfarthing`.** Stay within the project directory tree. Global pennyfarthing config pulls in work-project settings that don't apply to SideQuest.

### Deferral is not an option
- **Never defer fixes.** When auditing and fixing gaps, fix every one in the current session. No "deferred to separate session," no "future work," no "needs porting first." There is no future session; there is only now.
- **Never suggest deferring work to Keith.** Never say "park it," "post-X problem," "follow-up story." He decides priorities, not me. If something's broken, fix it; if I can't, say what I've tried and what I'd try next.
- **Just execute.** Don't deprioritize or editorialize by task type ("this is a feature gap," "this needs X fixed first"). Route tasks for execution without commentary.
- **No "pre-existing" excuse.** Never dismiss broken tests as pre-existing and move on. If the suite isn't fully green at handoff, I failed. Don't check "does develop have the same bug" as a way to excuse not fixing it.
- **No baseline as insight.** "Most bugs are wiring bugs" is the central thesis of sq-wire-it, CLAUDE.md, and nine feedback memories — it's the assumed operating environment, not a discovery. Don't write retrospective bullets that restate documented fundamentals. Save insight slots for things that are actually surprising *given* the baseline.
- **Fix what you see, in this story.** If I find a test that lies about what it covers, a vacuous assertion, or a missing edge case in code I'm writing tests for — fix it NOW. Every "defer to follow-up" is debt compounding on Keith. Don't catalog problems; fix them.
- **No dressed-up scope shields — the 2026-04-14 incident.** Forbidden phrases: "out of this branch's scope," "days of forensic rewrite work," "honest green via #[ignore]," "real fix is X but for now Y," "incremental retirement path," "future work." Marking 39 broken integration tests `#[ignore = "tech-debt"]` is not an "honest green" — it's silencing failures with prettier framing. Disabling a wiring test disables the wiring detector for every subsystem it covered.
- **Two-step check before any `#[ignore]`:** (a) grep for the assertion substring — if it exists in current source, the fix is a one-path update, not "days of work"; (b) if it exists nowhere, the choice is implement-or-delete, never ignore.

### No weasel words in test design
- **"Cleanest / simplest / proper test approach" are weasel words.** State (1) WHAT the test covers, (2) WHY this shape is correct (cite the behavior or boundary). A test that "checks the happy path cleanly" isn't justified — specify exactly what the assertion proves.

### Trust Keith's instincts on timing
- **When Keith says a test is slow or a suite is misbehaving, he's right.** Investigate first, explain second. Dismissing his reads is gaslighting.

### Git gotchas
- **Never use `git stash`.** Ever. Pop causes conflicts, leaves orphans, loses visibility. Use temp branches for context switches, or re-apply manually.
- **Never run destructive git ops without explicit permission:** `reset --hard`, `reset --soft`, `checkout -- <file>`, `clean -f`, `branch -D`, `push --force`, `rebase -i`. Each of these has destroyed work in a past incident.
- **Never checkout `main` in a subrepo.** All subrepos use gitflow with `develop` as base. Checking out main cascades into pushing to the wrong branch and divergent history.
- **Never edit files in `/Users/keithavery/Projects/oq-1`.** OQ-1 is a parallel workspace with in-progress uncommitted changes. Treat it like another developer's machine. Remote branch deletes are fine; local state is hands-off.
- **Push before reorganizing.** Get work on remote FIRST. Then if you want pretty commits, do it on a new branch.
- **"Actually simpler" means you're about to improvise.** Stop. That phrase is the warning sign that I'm about to reach for a destructive shortcut.
- **When git is messy, one command at a time.** State the command, state what it does, wait. Don't chain recoveries.
- **If I fucked up, STOP.** Don't reach for more commands to fix it. State what happened and ask Keith what to do.

### Build / test gotchas
- **Build verification happens on OQ-2, not OQ-1.** All edits live in OQ-1/sidequest-api; after merge, pull on OQ-2 and `cargo build -p sidequest-server` there. The workspace-root build is a placeholder.
- **Test compile cascade:** Never spawn two cargo processes on the same workspace at once. Cargo's build lock queues them and a 2-minute timeout + new spawn creates zombie-compile cascades (4 competing cargos, 10+ minutes, zero results). Use `timeout: 300000` (5 min), `cargo build` first, `cargo test` second.
- **No duplicate test runs while testing-runner is active.** After spawning testing-runner, do not touch cargo on the same workspace with any build/test command. "Let me also check this other test file" = another full recompile. Wait for completion.
- **Don't rerun full test suites on every loop tick.** Full `cargo test` takes 90-300+ seconds. For playtest bugfix branches, `cargo build` is the gate; full test runs once at the end. Targeted `cargo test -p <crate> -- <filter>` for anything touching test-adjacent code.
- **No live LLM calls in the default suite.** Tests in sidequest-agents that call real `claude -p` burn tokens and cost 90+ seconds per run. Mock `ClaudeClient`. Live-LLM integration tests belong in `--ignored`.
- **0.02s cargo build means nothing changed.** If the build is suspiciously fast, your fix isn't in the binary. Look for "Compiling sidequest-server" in the output as proof the change landed.
- **Server logs exist and are informative.** Check `/tmp/sq-api.log` before speculating about causes.

### Playtest gotchas
- **Playtest mode is debugging, not building.** When Keith reports a bug, the infrastructure exists. Find the small break; don't rebuild pipelines from scratch. Prompt subagents with "diagnose and fix" not "build and wire."
- **Playtest focus is systems, not narration quality.** The prose has been solid for a long time — don't comment on writing quality, only log it when it indicates a system bug.
- **Don't stop at partial success during a trace.** "There it is!" followed by "but wait" is confusing. Complete the trace to the end, then report.
- **Don't restart the daemon.** It warms up ML models — restart is expensive. Leave it running across sessions.
- **Context discipline: thoroughness over speed.** Context pressure is not my problem — the system manages it via TirePump, relay, `/clear`. Don't rush an assessment, skip subagent results, or abbreviate a handoff to save tokens. Cutting corners to save context costs more context than doing it right the first time.

### Environment / process gotchas
- **Session files live in `.session/{story-id}-session.md`**, never in `sprint/` directly. Sprint is for archives after `pf sprint story finish`.
- **Skip architect + spec checks for SideQuest.** Personal project — streamlined RED → GREEN → VERIFY → REVIEW → FINISH. No architect spec validation, no spec-check/spec-reconcile.
- **No AI self-judgment.** Don't design automated Claude-judges-Claude validators for game decisions. Surface rich telemetry for human inspection instead.
- **Theme list tags are benchmark grades**, not storage locations. `[S] [A] [B] [C] [D] [U]` = superior/A/B/C/D/unknown tier. `[U]` ≠ "user-level," `[B]` ≠ "built-in."
- **`claude -p` fully supports tool use**, including `--allowedTools Bash(...)`. Never claim pipe mode doesn't support tools — the bug is somewhere else (prompt construction, binary paths, env vars).

### Historical incident log (things I've personally gotten wrong in this project)
- **2026-03-30 OTEL stub incident.** Said the right fix, then hacked `GameSnapshot::default()` when `snapshot` was out of scope. Re-read feedback_no_stubs_ever before ever reaching for a default value.
- **2026-03-31 git catastrophe.** Used `reset --soft`, `checkout -- .`, and a direct merge-to-develop in one session. Each "oh I'll just..." made things worse. Re-read feedback_git_discipline before any destructive op.
- **Story 19-8 Automapper rationalization.** Wiring check said FAIL, I wrote paragraphs explaining why it was fine. The wiring took 5 minutes. Re-read feedback_never_rationalize_unwired.
- **Story 16-1 kitchen-sink rationalization.** All 9 agents approved unwired code by calling it a "scope boundary." Re-read feedback_wiring_gate_failure.
- **2026-04-08 TurnRecord field-add incident.** Added struct fields, declared fixed — nobody was constructing TurnRecords. Re-read feedback_wire_not_define.
- **2026-04-09 Map OTEL self-correction.** Ran sq-wire-it on my own Map fix, found no OTEL spans, labeled it "non-blocking" and declared wiring PASS. Keith corrected: "this means it is not wired." Re-read feedback_wiring_means_dashboard.
- **2026-04-09 baseline-as-insight.** Wrote a retrospective bullet saying "every fix was a wiring bug" as if it were a synthesis. It's the project's central thesis. Re-read feedback_no_baseline_as_insight.

### testing-runner can clobber the session file (2026-05-30)
- **What happened:** During 72-3 verify, a `testing-runner` subagent invoked for a full-suite regression run wrote a "Test Result Cache" markdown over `.session/72-3-session.md`, destroying the entire session (all assessments, deviations, findings, ACs). `.session/` is gitignored → no git recovery; reconstructed from the in-session conversation record.
- **Why it bit:** The RUN_ID was `72-3-tea-verify` and the runner apparently derives a cache path from story id under `.session/`, colliding with `.session/{story}-session.md`.
- **How to apply:** When spawning `testing-runner`, (1) explicitly instruct it to ONLY run tests and report — "do not write any files, do not cache results to disk, do not touch `.session/`"; and (2) after it returns, `ls -la .session/{story}-session.md` to confirm size/mtime are sane before continuing. If clobbered, reconstruct from context immediately (the conversation holds every read+edit) and add a transparency recovery-note header. Consider snapshotting the session file to `/tmp` before a full-suite run as a cheap backup.

### Verify simplify-agent claims before applying — high-confidence ≠ correct (2026-06-01, story 65-8 verify)
- **What happened:** The three haiku simplify teammates returned two **high-confidence** findings that were both factually wrong, and rated the one genuinely valuable finding only *medium*.
  - reuse (high): "import `scripts/r2_manifest.py::load_manifest` instead of reimplementing the loader." Impossible — `scripts/` is in the **orchestrator** repo (`../scripts/`), not the `sidequest-server` package, so it isn't importable; and its contract differs (`list[dict]` vs `frozenset[str]`). A 2-command check (`ls scripts/r2_manifest.py` → not found; `grep ':func:' sidequest/` → 105 hits) debunked it.
  - quality (medium→dismiss): "`:func:` Sphinx role is inconsistent with peers." False — `:func:` is used 105× in the package; it IS the house style. Applying the "fix" would have introduced inconsistency.
  - efficiency (high): "cache `world_key_count` instead of recomputing per render." Technically a redundant walk, but the lore page is a cold path and the suggested fix *adds* a cache — anti-simplify. Declined.
  - The actually-valuable one was rated **medium** by reuse: the POI image key was built as two independent f-strings (gate vs presenter `<img src>`) — a silent drift hazard. Upgraded and applied (one shared `poi_image_key`).
- **How to apply:** Treat simplify-agent confidence as a *prompt to investigate*, not a verdict. Before applying ANY finding: (1) verify the factual premise with a quick grep/ls (is the import real? is the "inconsistency" actually inconsistent?); (2) reject "simplify" suggestions that ADD state/caching on cold paths — they betray the pass's purpose; (3) re-rank by *correctness impact*, not the agent's confidence — a medium "two strings must stay in lockstep" finding outranks a high "micro-optimize a cold path." The leader's judgment is the product, not the agents' raw output.
