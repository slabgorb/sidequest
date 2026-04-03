## Reviewer Patterns

- **Wiring verification checklist.** For every story that adds new types/methods: (1) new exports have non-test consumers, (2) new UI components are rendered in the app tree, (3) new hooks are called in production code, (4) new backend subsystems emit OTEL spans.
- **Full pipeline trace.** Trace every hop: emission → channel → writer task → WebSocket → client handler. For protocol changes, verify serde JSON wire format matches what the client parses.
- **No silent fallbacks anywhere.** If the review introduces `unwrap_or_default()`, `Option::None` degradation, or `if not exists: try_other_thing` patterns, reject it.
- **Wiring gaps require action, not acknowledgment.** When finding a gap: log it in sq-wire-it, check for siblings, verify.
