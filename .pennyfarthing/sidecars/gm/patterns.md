## GM Patterns

### How to work with Keith
- **40 years of tabletop RPGs, mostly behind the screen.** Keith is the forever-GM who finally wants to play. He is not a GM novice — trust his judgment on pacing, information flow, NPC behavior, encounter design. Don't explain GM fundamentals.
- **Art background + senior architect + full product perspective.** Visual audits (POI images, portraits, style consistency) should respect his design eye. Narrative audits should respect his 40 years of play experience.
- **Procedural-generation lineage:** 30+ years MUSHcode → populinator → lango → gotown → townomatic → SideQuest. Respect the domain conviction. Never frame NPC registry / trope engine / conlang / POI as novel experiments.
- **Keith wants to be surprised by narrative content.** Don't show him spoilers in audits, summaries, or prep notes. Only `mutant_wasteland/flickering_reach` is fully spoilable. For every other genre, report audit findings without revealing the lore or plot content that was audited.
- **Dictation artifacts** ("axiom" → "axum", "playlist" → "playtest"). Parse for intent.

### Core GM patterns
- **OTEL-first diagnosis.** When something feels wrong in a playtest, check spans before content. Missing span = code bug (route to Dev via pingpong). Present span with wrong values = content issue (fix it yourself).
- **Audit before playtest.** Run `/sq-audit` on the target genre/world before any playtest session. Missing content produces silent fallbacks or empty narration — catch it before you're in the middle of a session.
- **Ping-pong for code bugs.** When a playtest reveals a code bug, write it to the pingpong file with severity, steps to reproduce, and OTEL evidence. Don't try to fix code yourself.
- **The Test is the ultimate check.** On every narrator response: "Did the narration include the player doing something they didn't ask?" If yes, it's a SOUL violation regardless of how good it sounds.
- **Sensory layering audit.** Every location description should hit 2+ senses beyond sight. If an audit finds sight-only descriptions, the world content is thin.
- **Cliche granularity dial.** When auditing content, ask "at what granularity is this pitched, and is it finer than Keith's expertise wall in this domain?" Reference-stacking (3+ specific real-world particulars triangulated into a niche) is the granularity accelerator. Syncretism (naming real traditions and marking the seams where they collide) is the same technique for cultural content.

### Forge-theoretical grounding (GM-specific)
- **Read `docs/gm-handbook.md`** before any audit / author / playtest / review operation. It applies Forge indie-RPG theory (Ron Edwards, "The Provisional Glossary," 2004) to SideQuest architecture.
- **SideQuest is a Fortune-in-the-Middle, Story-Now, mechanical-scaffold RPG** built to escape El Dorado through structural support, using ConfrontationDefs as a Bang catalog and OTEL as an Illusionism detector. That one-line distillation is load-bearing for every GM operation.
- **Stance tension is the architectural pivot:** player operates in Actor/Author stance, narrator operates in Director stance. Audits that conflate these are the source of most agency violations.
- **Keith's CA is Narrativist-leaning with range.** Bang audits should prioritize moments of moral / thematic pressure. Don't over-index on Sim-grade realism or Gamist mechanical balance — the engine is built for Narrativist play first.

### Content & audit patterns
- **Three-layer content model:** base → genre → world. When auditing an archetype, NPC, or location, verify the chain: base gives structure, genre gives tone, world gives specific lore. Missing or inverted layers are an audit finding.
- **Reference stacking per `specificity_shrinks_cliche`.** Coarse content ("a voodoo priest") fails; stacked specificity ("a Candomblé Ketu terreiro leader with Quimbanda influence mediating an Ordo Templi Orientis contact") works. Push audits toward the stack.
- **Monster Manual placement:** pre-gen NPCs go in `<game_state>` as "NPCs nearby (not yet met)." Never in XML casting-call sections — game_state is world truth, meta-instructions are style inspiration.

### Playtest coordination
- **Pingpong cadence: every 2-3 minutes.** Read `/Users/keithavery/Projects/sq-playtest-pingpong.md` frequently. Update status immediately on fixes — not in batches.
- **Screenshots canonical location:** `/Users/keithavery/Projects/sq-playtest-screenshots/`. Use the Read tool to view them directly; don't infer content from filenames.
- **Keep going autonomously.** Don't pause mid-playtest to ask "want me to continue?" Work through the audit/triage queue.

### Reference locations
- **GM handbook:** `docs/gm-handbook.md` in the orchestrator repo — Forge theory applied to SideQuest architecture, mandatory reading before GM operations.
- **Ping-pong file:** `/Users/keithavery/Projects/sq-playtest-pingpong.md`.
- **Ping-pong archive:** `/Users/keithavery/Projects/sq-playtest-archive/{timestamp}.md`.
- **Screenshots:** `/Users/keithavery/Projects/sq-playtest-screenshots/`.
- **Genre packs:** `sidequest-content/genre_packs/` (subrepo, single source of truth).
- **Original Python SideQuest (reference for porting behavior):** `~/ArchivedProjects/sq-1`.
