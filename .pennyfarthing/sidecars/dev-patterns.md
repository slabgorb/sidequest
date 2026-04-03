## Dev Patterns

- **Wiring means non-test consumers.** Before declaring GREEN, verify the function is actually called from the production pipeline. Library functions with no consumers are stubs, not features.
- **Combat wiring trace (reference).** IntentRouter → Orchestrator → lib.rs → Protocol → UI CombatOverlay. This is the pattern for verifying any intent-to-UI pipeline.
- **Every backend fix must emit OTEL spans.** The GM panel is the lie detector. If a subsystem isn't emitting spans, you can't tell if it's engaged or Claude is improvising.
- **Sidecar tool pattern.** Narrator calls tool → parser validates → assemble_turn consumes. Established by item_acquire, merchant_transact, lore_mark (Epic 20). Future tools follow this pattern.
- **Script tool prompt pattern.** Expose Rust generator binaries to narrator LLM via skill-style checklists, not threatening instructions.
- **Rust vs Python split.** Markov chains, name gen, game state, combat, protocol → Rust. Image gen, TTS, music gen → Python daemon. Claude CLI calls → Rust subprocess.
- **When explaining Rust to Keith:** Lead with Python comparison (porting from sq-2). Use Go for concepts Python can't express (traits→interfaces, ownership, compile-time enforcement).
