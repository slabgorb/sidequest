## GM Decisions

### Product direction
- **Narrative consistency is the #1 product goal.** Solo narrative experience is the core value prop. Mechanical state must back the story so the LLM isn't just improvising. Consistency bugs (NPC name changes, forgotten items, lost facts, turn count resets) are always high priority.
- **World building creative split.** Keith owns mechanics/crunch — always raise rules changes for his decision. GM/World Builder gets creative freedom on flavor/lore/story/NPCs/plot hooks. Keith wants to be surprised by world content like a player trusts a DM.
- **Spoiler protection.** Only `mutant_wasteland/flickering_reach` is fully spoilable. For every other genre, Keith wants to discover content in play — don't show him lore/faction/plot in audit summaries or design reviews.
- **Keith's target players (for tone/pacing decisions):** the **primary playgroup** is Keith, James (narrative-first, strong reader), Alex (slower reader, needs inclusive pacing, no fast-typist monopolies), Sebastien (mechanics-first, the only one who wants to see the numbers — the GM panel is a feature for him, not a debug tool). The **aspirational household** (Sonia, Antonio, Pedro) is nice-to-have; never drag primary-audience decisions toward low-reading-tolerance users.

### Music / audio
- **Music is cinematic, not video game BGM.** Overtures, cues, one-shots with fades. Never looping. Crossfade between tracks on mood changes.
- **Music is pre-rendered files from `genre_packs/{genre}/audio/music/`**, NOT daemon-generated. The daemon is image-only. Investigate bugs via (1) the audio directory, (2) API `music_cue_produced` logs, (3) `audio.yaml` mood→track mappings.
- **ACE-Step a2a for theme variations.** `audio2audio` with `ref_audio_strength` 0.25-0.55 produces recognizable leitmotif variations. Pick the best `_full` track per mood as the canonical theme, generate instrument variations via a2a. ACE-Step runs standalone at `/Users/keithavery/Projects/ACE-Step/` with its own venv — not routed through the daemon.
- **Road warrior music is high priority.** Genre identity is heavily audio-driven (Doof Warrior / Mad Max aesthetic). Prioritize music quality and variation count here.

### Content architecture
- **Three-layer content inheritance: base → genre → world.** Base defines structural archetype (no flavor, no lore). Genre enriches with tone (speech patterns, equipment, naming, visual cues). World adds specific lore (faction membership, local knowledge, named relationships). Chargen and NPC generation resolve against this chain. Never flatten layers during authoring.
- **Monster Manual NPCs inject into `<game_state>`** as "NPCs nearby (not yet met by player)." Never as XML casting-call sections, tool instructions, or meta-prompt framing — proven across 6+ iterations that meta-instructions get treated as style inspiration while game_state is treated as world truth.

### Cliche / content quality
- **Cliche granularity dial** (`feedback_specificity_shrinks_cliche.md`). Claude is a cliche engine. Every piece of content sits at some granularity — pick one *finer* than the audience's expertise wall. For Keith's high-expertise domains (software, game mechanics, RPG design, art, narrative, React/Rust), drop to competent-practitioner at minimum; niche-specialist via reference stacking is safer. For domains where he's coarser (non-Western religions, obscure Western esoterica, regional cuisines), specialist-practitioner is usually fine.
- **Reference stacking is the granularity accelerator.** Three specific particulars triangulated into a niche drops granularity three levels in one move. Syncretism (naming real traditions and marking the seams where they collide) is the same technique applied to cultural content.
- **Acceptable ceiling:** one domain specialist somewhere in the world can always still catch it. That's fine. Past *this* audience, not past all possible audiences.

### Forge-theoretical grounding
- **SideQuest is Fortune-in-the-Middle, Story-Now, mechanical-scaffold.** Built to escape El Dorado through structural support, using ConfrontationDefs as a Bang catalog and OTEL as an Illusionism detector.
- **Keith's Creative Agenda is Narrativist-leaning with range toward other CAs.** Bang audits prioritize moments of moral / thematic pressure. Don't over-index on Sim-grade realism or Gamist balance.
- **Read `docs/gm-handbook.md`** before any audit / author / playtest / review operation.
