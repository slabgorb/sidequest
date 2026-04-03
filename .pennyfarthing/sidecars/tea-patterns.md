## TEA Patterns

- **When Dev hits test failures from test design issues (not impl bugs), consult TEA.** During 2-9 GREEN, Dev found 3 tests with conflicting ordering expectations. TEA consultation confirmed server behavior was correct and tests needed adjustment. This saves debugging rounds.
- **Wiring test pattern.** For any story that adds new types/methods: at least one test must verify the code has a non-test consumer in the runtime pipeline. The test calls through the production code path, not just the library function directly.
- **OTEL verification in tests.** Backend wiring stories should have tests that check OTEL spans are emitted. If the subsystem doesn't emit spans, the GM panel can't verify it's working.
