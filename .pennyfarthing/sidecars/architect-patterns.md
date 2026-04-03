## Architect Patterns

- **Rust vs Python split.** If it doesn't involve operating LLMs (Flux, Kokoro, ACE-Step — not Claude), it goes in Rust. Claude calls are Rust CLI subprocesses. Python is for model inference library maturity only.
- **Sidecar tool architecture.** Narrator calls tool → sidecar parser validates → assemble_turn consumes. All mechanical extraction flows through sidecar tools, zero narrator JSON. Established by Epic 20.
- **OTEL is the lie detector.** Every subsystem decision must emit spans. Intent classification, agent routing, state patches, inventory mutations, NPC registry, trope engine, TTS segments. If it doesn't emit, you can't tell if it's engaged or Claude is improvising.
- **Genre packs are single source of truth** in sidequest-content. API loads from configured path. Content changes go in the content repo.
