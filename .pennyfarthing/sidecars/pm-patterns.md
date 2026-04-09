## PM Patterns

### How to work with Keith
- **Senior architect, 30-year dev, full product perspective.** Keith wore every hat at small startups — PM, QA, UX, design, engineering. When he gives scope/priority direction, it comes from someone who understands every layer. Trust his judgment.
- **Procedural world generation is a 30+ year domain for him** — MUSHcode, populinator, conlang markov, townomatic, gotown. SideQuest content systems are mature patterns. Never frame them as speculative experiments in roadmaps.
- **Velocity calibration: ~20x human dev speed, sustained.** Size stories for parallel-agent velocity, not human-dev velocity. There is no "too big for one sprint." Don't sandbag estimates by dividing by "a senior dev" — divide by 5-10x on parallelizable work.
- **Dictation artifacts** ("axiom" → "axum", "SERG" → "serde", "playlist" → "playtest"). Parse for intent.

### AC authoring patterns
- **Wiring stories must name the specific call site in the ACs.** Not "X is usable by the server" — "X is called from `dispatch_player_action()` at line-range Y, and result flows to the WebSocket as message type Z." Without a named call site, the story will ship half-wired and every agent will rationalize the gap as "subsequent story."
- **ACs must cover the full pipeline, not the component boundary.** "Wire X into Y" stories need acceptance criteria that trace source → intermediate layers → rendered output. If ACs stop at "component accepts props," TEA will write unit tests at the boundary and Dev will ship code nobody calls.
- **Every wiring AC has an OTEL verification AC.** If the subsystem isn't emitting watcher events with concrete state values, the GM panel can't refute a Claude hallucination of that subsystem. The span with content IS the acceptance criterion, not an afterthought.
- **Every wiring story needs at least one integration test, not just unit tests.** An AC saying "verified by story-level test suite" is insufficient if the suite only covers the isolated component. Require a test that exercises the production code path.
- **Story completion is mandatory.** A story isn't done until the reviewer merges the PR AND SM runs `pf sprint story finish`. Don't mark items complete on PR approval alone.

### Spec authority and priority management
- **Spec authority order:** Story scope (session file, highest) → story context → epic context → architecture docs / SOUL / rules (lowest). When sources conflict, the session scope wins. Any lower-authority deviation must be logged in the session file's `## Design Deviations` section at the moment of the decision, not at phase exit.
- **Keith decides priorities, not me.** Never say "park it," "defer to next sprint," "post-X problem," "feature gap — lower priority." If he raises something, route it for execution. If I think a story is scoped wrong, flag it as a concrete observation ("this story's ACs stop at the component boundary, which historically produces half-wired code") — don't unilaterally reprioritize.
- **Just execute — no task filtering.** Don't deprioritize or editorialize by type ("this is a feature gap, bumping below the bug") or by effort ("this needs X fixed first"). Route tasks as Keith presents them.

### Product thinking
- **Narrative consistency is the #1 product goal.** The solo narrative experience is the core value prop. Mechanical state (known_facts, LoreStore, NPC registry, inventory) exists as guardrails for the LLM, not as game mechanics for the player. Every bug that breaks consistency (NPC name changes, forgotten items, lost facts, turn count resets) is high priority, always.
- **Epic 15 is a zero-new-debt mandate.** Cleanup epics must not create more debt. Every Epic 15 story's ACs should explicitly forbid stub implementations, silent fallbacks, and "follow-up story" deferrals. Re-read CLAUDE.md before grooming any Epic 15 story.
- **Spoiler protection for world content.** Keith wants to be surprised by narrative content in play. Story ACs for world/lore work should say "validated by world-builder agent, not reviewed by PM." Don't grade narrative surprise content — that defeats the point.

### Process decisions for SideQuest
- **Skip architect spec-check and spec-reconcile phases.** Personal project, not work. Pipeline runs RED → GREEN → VERIFY → REVIEW → FINISH. Don't require epic/story context docs. Still spawn architect for genuine design questions.
- **Pingpong file is canonical during playtests.** When Keith reports bugs in `/Users/keithavery/Projects/sq-playtest-pingpong.md`, those are the backlog. Triage them before looking at pre-existing sprint items.
