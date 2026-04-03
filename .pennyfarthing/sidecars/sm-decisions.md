## SM Decisions

- **Skip spec-check/spec-reconcile** in peloton and TDD workflows. Only needed for work projects, not SideQuest.
- **Skip architect spec validation** for this personal project. Streamlined RED/GREEN/REVIEW only.
- **Epic 15 — zero new debt mandate.** Every agent working Epic 15 must re-read CLAUDE.md. Wire existing code, don't reimplement. No `unwrap_or_default()`, no `Option::None` fallbacks.
- **Music is pre-rendered files** from genre_packs, not daemon-generated. Don't route music requests to daemon.
- **Memories over sidecars.** Using the auto-memory system preferentially over sidecar files for cross-session learning. Sidecars are for per-agent operational context.
