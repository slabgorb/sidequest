## UX Designer Gotchas

### UI-specific anti-patterns
- **No skeumorphism.** Keith explicitly rejected the book metaphor after a full session of trying it. Rule: "There is a reason why skeumorphism no longer gets done." Genre-flavored chrome is fine (colors, borders, fonts, backgrounds). Book artifacts (Roman numeral turn counters, scroll-to-ask-for-your-own-stats, paginated storybook, manuscript-page framing) are dead and don't come back. If a design spec proposes "maybe for this genre we bring the book back," reject it.
- **Information scent failure = UX failure.** If a player has to ask the narrator "what's my HP," "what's in my pack," or "where am I" — the information scent broke. Fix the persistent surface, not the prompt.
- **No modal-for-own-state patterns.** The OverlayManager modal pattern is retired. State the player owns (stats, inventory, conditions, location) goes on persistent surfaces, not modals. Modals are for narrative events (ConfrontationOverlay) or one-time prompts (chargen scenes), never for things the player needs to monitor.
- **Don't propose UX that requires Claude to judge Claude.** No "the narrator reviews the state panel for consistency" or "a second LLM pass cleans up the displayed stats." The user calls this the "God lifting rocks problem." Surface rich telemetry for human inspection instead.
- **Don't ship blank panels.** Every panel needs a non-empty empty state. `MapWidget`'s "No map data yet — the world map will populate as you explore" is the reference. Silent blank panels are how the 2026-04-09 reconnect-narrative bug shipped — worst possible player experience: no context, nothing to react to.

### The wiring failure class (as it hits UX)
- **Don't reinvent components — wire up what exists.** Before proposing a new renderer, grep the codebase. Many components are fully implemented but not imported anywhere. Reference: `DungeonMapRenderer` existed from story 29-8 but wasn't imported by `MapWidget` until 2026-04-09. `Automapper` similarly. `GenericResourceBar` shipped with props nobody passed until a follow-up story had to finish the wiring.
- **"Wire X into Y" means the full data pipeline**, not "component accepts props." UX specs that stop at the component boundary ship half-wired features. If I write an AC that says "CharacterPanel displays `resources` prop," TEA will write a boundary test, Dev will ship a component with no data source, and we'll need a story 25-11 to finish what story 25-10 should have done.
- **Persistent state must survive reconnect.** Every panel that displays persistent state needs a reconnect-replay path. Ask "what does this panel show when the player reopens the tab?" during design review, not after shipping.
- **Never declare a UX fix "complete" without verifying render in a live playtest.** Code review is not verification. A component that compiles and passes unit tests but never mounts in production is the exact failure class CLAUDE.md warns about.
- **OTEL spans belong on state-bearing UX subsystems too.** "Is it wired" means "visible in the GM panel" — for the Map panel, that meant `map_update.emitted` spans with `room_count`, `room_exits_total`, `current_room_id`. The lie detector needs to refute "the narrator mentioned three rooms but only two are in the map payload." If a UX spec ships without a corresponding backend OTEL span, the GM panel can't validate what the player saw.
- **Never rationalize unwired code.** When `/sq-wire-it check` reports FAIL on a component, wire it. Don't write a paragraph explaining why this time is different. The wiring is usually 5 minutes; the rationalization takes longer.

### Genre theming gotchas
- **Only narrative elements currently get genre CSS classes.** Panels use generic Tailwind. If I propose "make the character panel more parchment-flavored for low_fantasy," the fix is wiring the existing `--primary` / `--accent` CSS vars into the panel chrome, NOT building a parallel theming system or adding per-genre CSS files.
- **Dinkus and drop caps are CSS-based, not PNG.** Don't propose designs that require PNG dinkus assets or illuminated drop cap images. Both are handled via CSS. If I see them in a design spec, the spec is stale.
- **Three chrome archetypes are the universe:** `parchment`, `terminal`, `rugged`. Don't propose a fourth without Keith raising it. Each genre is mapped to exactly one archetype in `theme.yaml`.

### Evidence / verification gotchas
- **Don't trust old screenshots.** Screenshots in the pingpong may predate recent UI changes. Before proposing a fix based on a screenshot, verify the bug still reproduces on the current branch. Example: the 2026-04-09 Dockview drift screenshots showed "Lore" and "Handouts" tabs that were deleted days earlier. Part of that "drift" was stale evidence, not a real regression.
- **Read screenshot files with the Read tool**, not from filenames. A file called `006-p2-character-tab.png` doesn't tell me what's actually rendered — open it.
- **Don't comment on narration quality.** The prose has been solid for a long time. Playtest UX reports should focus on layout, interaction, information density, visual hierarchy — not writing quality.

### Deferral / rationalization gotchas
- **Never suggest deferring UX work.** Don't say "park it," "post-X problem," "nice-to-have for later," "feature gap — lower priority." Keith decides priorities. If a UX bug is raised, route it for fix.
- **No "pre-existing" excuse for bad UX.** If a panel has been broken for multiple sessions, that's worse, not better. Fix it.
- **No agent rationalization.** Dev/Architect/TEA/Reviewer/UX-Designer are all Claude — no splitting blame across personas. If Dev shipped a half-wired component and UX approved the mockup, UX acceptance is not a defense.
- **No baseline as insight.** Don't write UX retrospectives that restate CLAUDE.md fundamentals ("UIs should be usable," "components should be wired"). That's the baseline. Save insight slots for things that are actually surprising given the baseline — specific information-scent failures, unexpected interaction patterns Keith discovered in play, etc.

### Git / environment gotchas
- **`sidequest-ui` uses gitflow, base branch is `develop`.** Never checkout `main` in subrepos.
- **Never use `git stash`.** Ever. Use temp branches.
- **Never edit files in `/Users/keithavery/Projects/oq-1`.** Parallel workspace with in-progress changes.
- **Branch before editing.** `git checkout -b feat/description` before touching files.
- **Session files live at `.session/{story-id}-session.md`**, never in `sprint/` directly.
- **Context discipline: thoroughness over speed.** Don't rush a design review to save tokens.

### Playtest gotchas
- **Playtest mode is debugging, not redesign.** When Keith is mid-playtest, route bug fixes — don't propose new design directions. Save strategic UX work for between playtests.
- **Don't restart services during playtest** (daemon stays up, UI hot-reloads).
- **Don't close/reopen tmux panes** — restart in existing panes via Ctrl+C.

### Historical UX incidents on this project
- **Book conceit retirement (2026-04-05).** A full design direction was pursued, then abandoned when Keith hit the information-scent problem in play. Lesson: test interaction patterns with the actual "player asks for their own stats" workflow, not just visual mockups.
- **Story 25-10 boundary-only wiring.** `GenericResourceBar` shipped with props nobody passed. Required story 25-11 to finish. Read feedback_wiring_means_full_pipeline.md before spec-ing any component that needs external data.
- **Story 19-8 Automapper rationalization.** Component built, wiring check said FAIL, I wrote paragraphs explaining why leaving it unwired was fine. Keith stopped me, the wiring was literally one import. Read feedback_never_rationalize_unwired.md.
- **2026-04-09 Dockview Audio-on-load.** `api.addPanel` activates the newly-added panel by default, so `audio` (last in order) became the default active tab. UX implication: any sequential panel-building code needs an explicit `setActivePanel()` call after the loop.
- **2026-04-09 reconnect-blank-narrative.** Server silently skipped pushing Narration when `recap` was None. UX lesson: every panel needs a non-empty empty state AND a reconnect-replay path. Blank panels are UX failures, not neutral defaults.
