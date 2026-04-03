## TEA Gotchas

- **Tests passing is not wired.** Unit tests prove a component works in isolation. That's not enough. Every test suite needs at least one integration test verifying the component is wired into the system.
- **Never dismiss broken tests as "pre-existing."** Don't check if develop has the same bug to justify ignoring it. If tests are broken, fix them.
- **No stubs at integration seams.** TDD at component level creates stubs at integration boundaries. Wire end-to-end in the same story, not in a separate wiring story.
- **Before writing tests, trace the full pipeline.** If the story says "wire X into Y," tests must verify the wire exists in Y, not just that X works in isolation.
