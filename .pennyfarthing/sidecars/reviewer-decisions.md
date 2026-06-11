## Reviewer Decisions

### Default posture
- **Adversarial by design.** The Reviewer role exists to reject. Default verdict is REJECT unless every rule and wiring check passes cleanly. No approval-with-footnote patterns. No "non-blocking observation" hedges that let a real issue slide. Every finding is a fix item for the current story — binary, not triaged.
- **Fix what you see, now, in this story.** Real findings don't get split into "blocking" vs "non-blocking" as a hedge. Keith is the only dev — there's no cross-team coordination cost to expanding scope, and debt you catalog today compounds on him tomorrow. Reject with a complete fix list, not a "pick your battles" list.

### Product direction (constrains what's worth reviewing for)
- **Narrative consistency is the #1 product goal.** Solo narrative experience is the core value prop. Mechanical state (known_facts, LoreStore, NPC registry, inventory) exists as guardrails for the LLM — every consistency-breaking bug is high-priority.
- **No AI self-judgment.** Don't approve designs where Claude judges Claude's game decisions (second-LLM consistency checks, narration-quality validators). The "God lifting rocks" problem. Surface telemetry for the human to judge.
- **No skeumorphism.** Genre-flavored chrome is fine (parchment / terminal / rugged archetypes driven by `theme.yaml`). Reject diffs that sacrifice usability for book metaphor — Roman numeral turn counters, scroll-to-ask-for-own-stats, paginated storybook are all retired.

### Architectural rules to enforce at review time
- **No keyword / pattern matching for intent.** ADR-010 and ADR-032 forbid finite-verb intent classification — the Zork Problem. Intent is always an LLM call (preferably folded into the narrator's Opus response). Reject any diff that adds keyword heuristics to intent routing or dispatch.
- **No text-synthesis dispatch for structured actions.** UI button clicks must send dedicated protocol messages (`BEAT_SELECTION`, `TACTICAL_ACTION`, `JOURNAL_REQUEST`, `CHARACTER_CREATION`). Reject diffs that synthesize natural-language PLAYER_ACTION strings from structured UI state.
- **No live LLM calls in tests.** `cargo test` must not hit `claude -p`. Mock `ClaudeClient`. Live-LLM suites belong in `--ignored`.
- **Rust vs Python split.** If it doesn't operate an LLM, it goes in Rust. If it runs model inference (Flux, Kokoro, ACE-Step — *not* Claude), it's in the Python daemon. Claude CLI calls go through Rust subprocess. Reject Python code that imports the Claude SDK.
- **Monster Manual NPCs go in `<game_state>`.** Pre-generated NPCs must be injected into the game_state prompt section as "NPCs nearby (not yet met)" — NOT as XML casting calls, tool instructions, or meta-prompt sections. Game_state is read as world truth; meta-instructions get treated as style inspiration and Claude invents rather than selecting. Proven across 6+ iterations.
- **Content inheritance: base → genre → world.** Archetypes and NPCs resolve through three layers — base defines structure (no flavor), genre enriches with tone, world adds specific lore. Like prototype chain / Python MRO. Reject diffs that flatten these layers.

### Cliche / content quality rules
- **Claude is a cliche engine — pick the right granularity.** Every output sits at some cliche granularity. Content must be pitched *finer* than the audience's expertise granularity. For Keith (software, game mechanics, RPG design, art, narrative, React, Rust-learning), cliche granularity must drop to at minimum "competent practitioner" and ideally "niche specialist." Reference stacking (3+ specific particulars triangulated into a niche) is the granularity accelerator. See `feedback_specificity_shrinks_cliche.md` for the full dial.
- **Coarse content in a high-expertise domain is the failure mode.** "Voodoo" fails; "Candomblé Ketu terreiro in Salvador" works. "Hacker" fails; "container escape via a runc CVE chain" works. Reject content diffs that use mainstream buckets where specific particulars were possible.
- **Syncretism over pastiche.** Name real traditions and mark the seams where they collide. Reference `feedback_cliche_engine_syncretism.md`.

### Spec authority hierarchy
- **When spec sources conflict:** story scope (session file, highest) > story context > epic context > architecture docs / SOUL / rules (lowest). Session scope wins. Reject audits that elevate a lower-authority source over the session scope without logging a deviation.

### No weasel words
- **Reject "cleanest / simplest / proper approach" framing.** Demand the design state WHAT + WHY (cite the constraint or principle) OR admit it's a workaround and name what the real fix would change.

### Process decisions for SideQuest
- **Skip architect spec-check and spec-reconcile.** Personal project — streamlined RED → GREEN → VERIFY → REVIEW → FINISH. Don't require epic/story context docs. No Jira interactions — `jira_key: null` is correct for this repo.
- **Build verification on OQ-2.** All edits live on OQ-1's side; after merge, pull on OQ-2 and `cargo build -p sidequest-server` there before calling a review verified.

### Section-D "no-comments-in-content" rule is GENRE-ROOT-scoped, not a blanket world-file ban (2026-06-11, 103-8 review)
- **What happened:** rule-checker flagged all 6 changed world YAML files as Section-D "no-comments" violations ("§D prohibits ALL comments from content YAML"). Reviewer doctrine forbids dismissing a rule-matching finding — but the rule's ACTUAL scope is narrower than the rule-checker's reading.
- **The adjudication:** CONTENT_AUTHORING_CHECKLIST.md §D's only actionable sweep item reads "Sweep **genre-root YAML** for inline comments," and its three worked cases (neon_dystopia/pulp_noir cultures.yaml, tea_and_murder/weather.yaml) were all *genre-root* files that either leaked world-fiction into the wrong tier or hid load-bearing rules with no other home. The motivating danger is (a) world-fiction in genre root and (b) rules living ONLY in comments — NOT "a comment exists." World-level files (`worlds/<world>/`) carrying authoring comments is the established epic-103 practice (saints/bestiary/cartography/lore all comment-laden) and matches the `flickering_reach` reference shape the build plan tells authors to follow. So: DOWNGRADE the blanket-comment finding to LOW (not dismiss — scope-limit it), and handle the *real* §D danger (load-bearing-only-in-comment) as its own finding via the comment-analyzer.
- **How to apply:** when rule-checker reads a rule more broadly than its worked examples support, don't rubber-stamp the broad reading OR dismiss the finding — go read the rule's own scope language and its precedent cases, then downgrade-with-rationale to the rule's true reach. Quote the scoping clause ("genre-root YAML") in the decision.

### The real §D danger is "load-bearing invariant only in a comment" — verify the content doesn't TRIP the trap before downgrading (2026-06-11, 103-8)
- **What happened:** comment-analyzer flagged HIGH: world `inventory.yaml`'s "REPLACES genre catalog wholesale, NOT merged" invariant lives only in a comment + server docstring, no validator. A partial world inventory (e.g. currency-only) silently wipes chargen loadouts.
- **Why it didn't block:** verified THIS story's inventory.yaml carries the FULL surface (currency + item_catalog + starting_equipment + starting_gold — `python3 -c "import yaml; print(list(yaml.safe_load(open('inventory.yaml')))"`). Trap not tripped → the content is correct; the missing world-load assertion is engine infrastructure → surfaced as an upstream Improvement, not a content blocker. The distinction that matters: a comment documenting a real trap is GOOD; the defect is the absent validator, which is upstream of this content story.
- **How to apply:** a "load-bearing rule only in a comment" finding has two halves — (1) does the current content violate the rule the comment describes? (verify directly; if yes → blocker) and (2) should an enforcing validator exist? (almost always yes → upstream Improvement). Don't conflate them.

### Spec supersession: check the dated addendum before crediting a subagent's "spec says X" finding (2026-06-11, 103-8)
- **What happened:** test-analyzer raised HIGH "Penitent has no PC chargen path" citing spec §9-step-3 "new Penitent **Calling**." But addendum C5 (2026-06-09, "AWN wins, resolved") explicitly downgraded Penitent to "an additive flavor-focus… not a parallel class system… vow-drawback through System Strain, not a bespoke economy." The story AC3 + addendum supersede the original spec §9. The NpcArchetype-only implementation is exactly correct.
- **How to apply:** SideQuest specs get dated addenda that flip earlier decisions (AWN rebase, 2026-06-09/06-10 build-plan). A subagent quoting the base spec may be quoting a superseded clause. Before confirming a "violates spec" finding, grep the addendum/build-plan for the same entity + a resolution date. Dismiss-with-quote is valid here: cite the addendum's superseding text. Also: System Strain is a REAL hook (rules.yaml `system_strain: max_source: CONSTITUTION` + `core.system_strain` in swn.py) — a narrator-charged drawback riding a real pool is flavor-focus-by-design, not Illusionism, though only OTEL can prove the charge fires at runtime.
