# 45-52

## Problem

Problem: After splitting the NPC (non-player character) system into two cleaner layers in the prior sprint story (Wave 2A), the old deprecated class — `NpcRegistryEntry` — was left in place as a compatibility shim, and nine test files still pointed at it. Why it matters: tests that point at obsolete code give false assurance. If the new NPC layer broke silently, all nine test suites would still pass, the monitoring dashboard would stay dark, and nobody would know until a playtest session produced ghosts that never die or enemies that don't show up in combat. This story cuts the wire to the old system entirely.

---

## What Changed

Think of the NPC system like a library's card catalog. The old version used a single drawer for everything: "who exists in this world" and "what each character is doing right now" were mixed together in one place called `NpcRegistryEntry`. Wave 2A (the prior story) built a new two-drawer filing cabinet — one drawer for the roster, one for live status. But the old single drawer was still physically attached to the wall with nine cables running to it.

This story:
- **Ripped out the old drawer** (`NpcRegistryEntry` class and `npc_registry` snapshot field — deleted, not deprecated)
- **Reconnected all nine cables** to the new two-drawer system (nine test files updated to use the new NPC APIs)
- **Relabeled the monitoring gauges** — the health signal previously called `NPC_REGISTRY_HP_SET` (a name that referenced HP, which was removed months ago) is now called `NPC_EDGE_PUBLISHED`, matching the actual game mechanic
- **Added three new health counters** to the GM monitoring dashboard: how many malformed NPC records were silently skipped, how many nameless entries were quietly dropped, and whether location data was available when needed — all previously invisible

---

## Why This Approach

The codebase has a firm rule: **no silent fallbacks**. A deprecated class that still compiles and still passes tests is a lie — it says "the system is healthy" when really it's just that nobody has checked the new system yet. By removing the old class entirely rather than leaving it as a fallback, the team forced every reference to update. If something was missed, it breaks loudly at build time, not quietly at 2 AM during a playtest.

The renamed OTEL span (`NPC_EDGE_PUBLISHED`) matters for a different reason: Sebastien — the mechanically-curious player in the group — uses the GM observability panel to understand what the game engine is actually doing. A span named after a mechanic that no longer exists (`HP`) is actively misleading to someone reading the live dashboard.

---
