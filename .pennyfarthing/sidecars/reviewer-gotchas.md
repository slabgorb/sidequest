## Reviewer Gotchas

- **16-1 incident: all 9 agents approved unwired code.** Every agent rationalized the gap as "wiring comes later." The wiring-check gate exists but was not enforced during any phase transition. Reviewer is the last line of defense, not the only one — but when it reaches you unwired, catch it.
- **Code review is not verification.** Six commits claimed to fix turn lock. Each found a real code issue. None verified the message actually arrived at the browser. Don't say "the code looks right" — verify the data arrived.
- **"Is it wired" means visible in the GM panel/dashboard.** Not just internal data flow. When Keith asks about wiring, he means the full path to user-visible output or OTEL telemetry.
- **Check non-test consumers.** New exports with only test consumers are stubs. Verify imports in production code paths before approving.
