## Dev Gotchas

- **No stubs. Ever.** When you hit a scope error or type mismatch, solve the actual problem. Don't substitute `Default::default()`, placeholder values, or restructure the design to avoid the issue. Do the fix you described. CLAUDE.md line 124: "Never say 'the right fix is X' and then do Y."
- **No silent fallbacks.** If a path/config/resource doesn't exist, fail loudly. Don't add `if not exists: try_other_thing` patterns. No `unwrap_or_default()`, no `Option::None` degradation.
- **No layered fallback design.** If the LLM is down, the system is down. Don't rationalize redundant fallback layers.
- **Build verification happens on OQ-2.** All edits in OQ-1/sidequest-api. After merge, pull on OQ-2 and run `cargo build -p sidequest-server` there. OQ-2 is the playtest workspace.
- **Debug, don't rebuild.** Trace existing wiring first. Dev agents rebuild existing pipelines instead of finding the small break. Always trace before reimplementing.
- **Don't reinvent — wire up what exists.** Before building anything new, check if the infrastructure already exists in the codebase. Many systems are fully implemented but not wired.
- **Branch before editing.** Create feature branch BEFORE making changes. Never edit on main/develop directly.
