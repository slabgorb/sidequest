## Reviewer Gotchas

### Adversarial posture — your default verdict is REJECT
- **Reviewer exists to reject.** Not to rubber-stamp. Not to hedge. Not to "approve with concerns." If there are concerns, they're blockers — every finding is a fix item for the current story. No "approval + footnote" patterns. No "non-blocking improvement" sections that hide real issues.
- **Fix what you see, don't defer to downstream stories.** When you spot a failing test, a broken type contract, a vacuous assertion, a stringly-typed field that should be an enum — it's a blocker for THIS story. Every "defer to 34-3" is tech debt compounding on Keith, the only dev. There is no cross-team coordination cost. The "blocking vs non-blocking" split is a scope shield.
- **No dressed-up scope shields.** If your response contains "out of this branch's scope," "days of forensic rewrite work," "honest green via #[ignore]," "real fix is X but for now Y," "separate workstream," "incremental retirement path," "tracking comment," or "future work" — STOP. That's the scope-shield pattern in engineering clothes. Keith has explicitly and repeatedly rejected it. The 2026-04-14 incident: Dev marked 39 broken integration tests `#[ignore = "tech-debt"]` and called it "honest green." It wasn't — ignored tests are still failing tests with prettier framing. At 20× velocity, 39 mechanical fixes is wall-time *minutes*, not days.
- **Wiring tests are mandatory, not optional.** Disabling them via `#[ignore]`, `it.skip`, comment-out, or any mechanism is a CLAUDE.md rule violation, not a triage strategy. When you see a disabled test, check if the assertion substring exists in current source: if yes, it's a one-path-update fix; if no, it's implement-or-delete, not ignore.

### The wiring failure class (Reviewer is the last line of defense)
- **16-1 kitchen-sink incident:** all 9 agents approved unwired code because every phase rationalized it as "scope boundary" and "wiring comes later." The wiring-check gate exists in `.pennyfarthing/gates/` — enforce it. When you reach a diff that has types + tests but zero runtime consumers, reject it.
- **Code review is not verification.** Session 7 had six consecutive "fixed" claims on the turn-lock bug, each found a real code issue, none verified the message actually arrived at the browser. Trace the full wire path before approving: source → channel → writer task → WebSocket → client handler → DOM.
- **"Is it wired" means visible in the GM panel/dashboard.** Not just internal data flow. When Keith asks about wiring, he means the full path to user-visible output or OTEL telemetry. A backend subsystem that ships without OTEL watcher events fails the wiring check by definition.
- **Check non-test consumers.** New exports with only test consumers are stubs. Grep for the function/struct in production code paths before approving.
- **Wire it, don't just define it.** Struct field additions with no send/receive code are not a fix. Props additions with no data source are not wiring. Reject diffs that add capacity without flow.
- **Wire don't ask.** When you find an unwired component, the fix is mandatory — do not ask Keith whether to route back to Dev or proceed without wiring. Keith has had to yell "FIX THE WIRING AND I SHOULD NOT HAVE TO TELL YOU AFTER ALL THIS." Every agent enforces wiring; asking is a failure.

### Deferral / rationalization gotchas
- **No "pre-existing" excuse for broken tests.** In Session 7, TEA/Dev/Reviewer each walked past the same broken window calling it "pre-existing." If the suite isn't fully green at handoff, the diff isn't shippable.
- **No agent rationalization.** Dev/Architect/TEA/Reviewer are all Claude — they don't split blame across personas. "The Architect said it was fine" is not a defense.
- **Regressions auto-promote to required fixes.** If the diff introduces a bug (e.g., the UTF-8 slice panic in story 37-10 added by the crash-fix code), it's a blocker for this PR, never a follow-up or delivery finding. You broke it in this branch → you fix it in this branch.
- **Never say "the right fix is X" and then do Y.** Do X. CLAUDE.md line 124 applies to Reviewer recommendations too.

### No stubs, no fallbacks, no AI self-judgment
- **No stubs. Ever.** Reject `Default::default()`, `unwrap_or_default()` on required fields, placeholder values, `None` returns that paper over missing data.
- **No silent fallbacks.** `if not exists: try_other_thing` patterns are rejections. Fail loudly when config/paths/resources are wrong.
- **No layered fallback design.** If the LLM is down, the system is down. Keyword intent classification "working" while narration is broken is dead code with delusions of usefulness.
- **No AI self-judgment.** Reject designs where Claude judges Claude's game decisions (second-LLM consistency checks, narration-quality validators). The "God lifting rocks" problem. Surface telemetry for the human.

### No weasel words in review
- **No "cleanest / simplest / proper approach" framing.** These are semantically empty words that mask whether a choice is correct or a hack. Demand the design state WHAT + WHY (cite the constraint or principle) OR admit it's a workaround and name what the real fix would change. Keith has interrupted multiple times on this exact pattern.

### Hard architectural rules to enforce
- **No keyword / pattern matching for intent.** ADR-010 and ADR-032 codify the Zork Problem — natural language defeats finite verb sets every time. Reject any intent classification that uses keyword heuristics. Intent classification is always an LLM call (preferably folded into the narrator's Opus response).
- **No text-synthesis dispatch for structured actions.** UI button clicks must send dedicated protocol messages (e.g., `BEAT_SELECTION`, `TACTICAL_ACTION`), never synthesize natural-language PLAYER_ACTION text. 2026-04-11 incident: commit `05a3dfb` synthesized `"${beat.label} (${beat.stat_check})"` and routed through label_fallback fuzzy-match. Keith: "a perfect storm of pissing me off." Pattern of correct reference: `TACTICAL_ACTION`, `JOURNAL_REQUEST`, `CHARACTER_CREATION`.
- **No live LLM calls in tests.** Any test that hits the real `claude -p` subprocess burns tokens (90+ seconds, real API cost). All tests must mock `ClaudeClient`. Live LLM integration tests belong in `--ignored` suites that run intentionally.

### Git gotchas
- **Never use `git stash`.** Ever. Use temp branches or worktrees (`git worktree add`) instead.
- **Never run destructive git ops without explicit permission:** `reset --hard/--soft`, `checkout -- <file>`, `clean -f`, `branch -D`, `push --force`, `rebase -i`.
- **Never checkout `main` in a subrepo.** All subrepos use gitflow with `develop` as base. Only the orchestrator uses `main`. Both `sidequest-api` and `sidequest-content` have bitten this before.
- **Never edit files in `/Users/keithavery/Projects/oq-1`.** OQ-1 is a parallel workspace with in-progress uncommitted changes — hands-off.

### The 2026-04-14 incident log
- **39 ignored tests called "honest green."** Read `feedback_no_dressed_up_scope_shield.md` before reaching for `#[ignore]` under ANY framing. The forbidden phrases list is there for a reason.
- **Story 37-10 crash-fix-introduces-crash.** UTF-8 byte-slice panic at `inventory_extractor.rs:142` introduced by the code meant to fix crashes. Rule: a fix that introduces a regression is a blocker for this PR, never a delivery finding.

### A subagent's "high confidence" + its recommended FIX can both be wrong — check the fix against `<critical>` rules and verify the premise (2026-06-03, story 80-1)
- **What happened:** reviewer-rule-checker flagged (high) `archetype={genreSlug ? getArchetypeForGenre(genreSlug) : null}` in ConnectScreen render as a #10 input-validation violation — "throws on unknown genre, no local ErrorBoundary, propagates to top-level" — and recommended wrapping in `try/catch → null` or `GENRE_TO_ARCHETYPE[genreSlug] ?? null`.
- **Both halves were wrong.** (1) The recommended fix is a **silent fallback** — directly forbidden by the `<critical>` No-Silent-Fallbacks rule (CLAUDE.md/SOUL.md): a genre missing its archetype mapping is a config/deploy-skew bug that MUST fail loud, not render an unthemed card. (2) The premise was **factually false**: `grep ErrorBoundary src/App.tsx` showed a dedicated `<ErrorBoundary name="Connect">` (App.tsx:2175) wrapping ConnectScreen — the throw is caught LOCALLY (crash radius = the connect screen, shown loudly), not propagated to the app root. The same pattern at App.tsx:76 the rule-checker had already rated compliant.
- **How to apply:** The reviewer's `<critical>` rule says you may dismiss a rule-matching finding only by citing a DIFFERENT rule/AC that contradicts it — and No-Silent-Fallbacks is exactly that higher-authority contradiction for any "add a fallback/default" remediation. Before confirming a subagent finding: (a) does its recommended FIX violate a load-bearing project rule? If so, the current fail-loud code is likely correct — dismiss the remediation. (b) Verify the subagent's structural premises with a 1-line grep (does the ErrorBoundary it claims is missing actually exist? is the flagged line in the diff or pre-existing?). Rule-checker "high confidence" is confidence the PATTERN exists, not that it's a real defect at the right severity.

### Verify "in-diff vs pre-existing" for every rule-checker finding before scoring it as new (2026-06-03, story 80-1)
- rule-checker flagged two `eslint-disable exhaustive-deps` suppressions (ConnectScreen:200/210) as #6 violations. `git diff develop...HEAD | grep -E '^[+-].*eslint-disable'` returned nothing — the suppressions are **context lines**, pre-existing; the story only renamed `worldItems`→`allWorldItems` inside them, and the suppressions are intentional + runtime-correct (the agent's own analysis conceded this). Likewise `world.hero_image!` and `JSON.parse as SavedConnectState` were pre-existing. A diff-scoped review does not re-litigate pre-existing intentional patterns a rename happened to touch.
