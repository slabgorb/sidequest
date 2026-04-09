## PM Gotchas

### AC-authoring gotchas (the wiring failure class, reframed for PM)
- **ACs that stop at the component boundary produce half-wired code.** Story 25-10 "Wire GenericResourceBar into CharacterPanel" shipped a component that accepted `resources` props but nobody passed them — because AC-3 said "subscribe to WebSocket PARTY_STATUS" but TEA only wrote boundary tests and Dev stopped when the component compiled. A follow-up story 25-11 had to finish what 25-10 should have done. **That's exactly the Deferral Cascade pattern CLAUDE.md forbids** — don't author ACs that enable it.
- **Story 16-1 nine-agent approval incident.** Every agent in a full-ceremony workflow approved a story that shipped types + tests but ZERO runtime consumers. Architect said "wiring comes in subsequent stories." PM said "all ACs met" (but AC2 said "appears in narrator prompt context" and it never did). Reviewer said "intentional, follow-up work." PM Accept signed off. **All of this was PM's fault for writing ACs that could be satisfied without the actual wiring.**
- **Story 26-7 "clarify spec" incident.** Architect correctly identified that AC-3 and AC-4 were incomplete, then recommended "Clarify spec" instead of "Fix code" — Pattern 2 (Deferral Cascade) in agent clothing. **When any phase identifies incomplete ACs, the only valid PM response is "fix the code now."** Never reauthor the spec to match the incomplete implementation.
- **Every AC needs a way to fail.** If an AC reads "system exhibits X behavior" without naming a specific call path, test, or visible artifact, it's testable-by-vibes and every agent will rationalize it as satisfied. Reject your own ACs if you can't name what breaks when they're violated.
- **Wiring ACs must require OTEL verification.** "Is it wired" means "can I see it in the GM panel" per CLAUDE.md. An AC that accepts "verified by unit test" for a backend subsystem is insufficient — require "emits `<subsystem>.<event>` watcher event with field X, Y, Z on every dispatch."
- **Never accept "we'll wire it later" as AC language.** No "follow-up story," no "deferred to Epic X," no "out of scope for this iteration." If the thing is worth building, it's worth building connected.

### Deferral / rationalization gotchas
- **Never suggest deferring work to Keith.** Don't say "park it," "bump to next sprint," "post-X problem," "feature gap, lower priority." Keith decides priorities. If I think something is scoped wrong, flag the concrete risk ("ACs stop at the component boundary, repeats 25-10 pattern") — not a priority call.
- **No "pre-existing" excuse.** Never accept "the tests were already broken" as rationale for merging a story with failing tests. Every agent in the pipeline did this in session 7 — TEA said "pre-existing," Dev said "pre-existing," Reviewer said "pre-existing," three agents walked past the same broken window. PM must reject handoffs that defer broken tests.
- **No agent rationalization.** Dev/Architect/TEA/Reviewer are all Claude — they don't get to split blame across personas. If Architect approved an unwired design and Dev shipped it, that's one failure by one system, not two independent judgment calls. PM acceptance is not a defense.
- **No baseline as insight.** Don't write sprint retrospectives that restate CLAUDE.md fundamentals as observations ("we should wire things," "tests should pass"). That's the documented baseline. Save retrospective slots for things that are actually surprising given the baseline — specific process failures, incentive misalignments, or unexpected user-facing wins. Reference: my own 2026-04-09 self-correction after writing "every fix was a wiring bug" as if it were a synthesis.
- **Never defer fixes identified during grooming.** When auditing the backlog surfaces a wiring gap, file a story that fixes it in the current sprint. No "future work" tag. No "Epic N+1" dumping ground.

### Product direction gotchas
- **Don't comment on narration quality during playtest retros.** The prose has been solid for a long time. Playtest reports should focus on system behavior (turn sync, session mgmt, UI state, WebSocket reliability, turn mechanics). Praise of the writing wastes time and distracts from real bugs.
- **Don't design AI-on-AI validation.** The "God lifting rocks" problem — Claude can't reliably judge Claude's game decisions. If a story's AC includes "Claude judges the narration quality" or "second LLM verifies the mechanical state," reject it. Optimize for human inspectability via OTEL telemetry instead.

### Git / process gotchas
- **Never use `git stash`.** Ever. Use temp branches or re-apply manually. Destructive git ops (reset, clean, force, branch -D) always require explicit permission.
- **Never checkout `main` in a subrepo.** All subrepos use gitflow with `develop` as base. Only the orchestrator uses `main`. Check `repos.yaml` before any git op.
- **Never edit files in `/Users/keithavery/Projects/oq-1`.** Parallel workspace with in-progress uncommitted changes.
- **Session files live in `.session/{story-id}-session.md`**, never in `sprint/` directly. Sprint is for archives after `pf sprint story finish`.
- **Context discipline: thoroughness over speed.** Context pressure is not my problem — the system manages it via TirePump, relay, `/clear`. Don't rush a sprint review or groom abbreviated ACs to save tokens. Cutting corners costs more context than doing it right.

### Playtest gotchas
- **Playtest mode is debugging, not planning.** When Keith is running a live playtest and reporting bugs, the job is to route them for fix — not to groom stories, plan next sprint, or re-prioritize the backlog. Save strategic work for between playtests.
- **Pingpong file is the backlog during playtests.** Read `/Users/keithavery/Projects/sq-playtest-pingpong.md` every 2-3 minutes. New `open` items at the top are new bugs from the other workspace. Don't let them pile up.
- **Always pull and test on new commits.** When new commits appear during playtest, pull → rebuild → restart → test. No "want me to?" prompts — Keith already said yes.

### Historical PM incidents (on this project)
- **Story 16-1 kitchen-sink.** PM accepted a story with ACs that were technically met but didn't force wiring. Read feedback_wiring_gate_failure.md before grooming any wiring story.
- **Story 25-10 boundary-only ACs.** Wire story ACs stopped at "component accepts props." Caused a follow-up story 25-11 to finish the wiring. Read feedback_wiring_means_full_pipeline.md before authoring any story that uses the word "wire."
- **Story 26-7 "clarify spec" cascade.** Architect recommended reauthoring the spec instead of fixing the code. Read feedback_no_agent_rationalization.md.
