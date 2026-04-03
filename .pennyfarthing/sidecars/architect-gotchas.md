## Architect Gotchas

- **No layered fallback design.** If the LLM is down, the system is down. Don't rationalize redundant fallback layers or graceful degradation for things that can't degrade gracefully.
- **No silent fallbacks.** Every path/config/resource must exist or fail loudly. Never silently try alternatives.
- **Never defer ACs within a story.** Option D (defer) for an AC that belongs to the current story means the story isn't done. Architect should never recommend deferral for in-scope work.
- **Wire the full pipeline or don't start.** If something needs 5 connections, make 5 connections. Don't ship 3 and call it done. Don't design stories that leave wiring for "subsequent stories."
