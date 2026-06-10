# Demo Script — Story 101-6

## Scene 1: Setup (30 sec)

**Presenter says:** "Problem: Daemon housekeeping — delete empty ml/ package, drop dead pygame-ce dependency, fix stale CLAUDE.md daemon tree. Why it matters: a defect was impacting functionality."

**Show:** The issue as users experienced it

## Scene 2: Act 1 (2 min)

**Presenter says:** "We implemented: Daemon housekeeping — delete empty ml/ package, drop dead pygame-ce dependency, fix stale CLAUDE.md daemon tree.
This delivers the following capabilities:
  - sidequest_daemon/ml/ deleted; uv run pytest green; daemon boots (just daemon-status)
  - pygame-ce removed from pyproject; uv sync clean; stale docstring in pipeline_factory.py updated
  - CLAUDE.md daemon tree matches the actual package layout (no audio/, no ml/, training/ + telemetry/ present)
  - ADR-046 status verified against DRIFT.md and pointer corrected if drifted"

**Show:** ## Demo Script — Daemon housekeeping — delete empty ml/ package, drop dead pygame-ce dependency, fix stale CLAUDE.md daemon tree

### Scene 1: Setup (30 sec)
**Presenter says:** "Today we're going to show you what we built for Daemon housekeeping — delete empty ml/ package, drop dead pygame-ce dependency, fix stale CLAUDE.md daemon tree."
**Show:** The project overview

### Scene 2: Demo (1 min)
**Presenter says:** "Here's what this delivers:"
**Show:** sidequest_daemon/ml/ deleted; uv run pytest green; daemon boots (just daemon-status)
**Show:** pygame-ce removed from pyproject; uv sync clean; stale docstring in pipeline_factory.py updated
**Show:** CLAUDE.md daemon tree matches the actual package layout (no audio/, no ml/, training/ + telemetry/ present)
**Show:** ADR-046 status verified against DRIFT.md and pointer corrected if drifted

### Scene 3: Closing (30 sec)
**Presenter says:** "That's Daemon housekeeping — delete empty ml/ package, drop dead pygame-ce dependency, fix stale CLAUDE.md daemon tree — shipped and verified."

## Scene 3: Act 2 (1 min)

**Presenter says:** "Before: The system exhibited incorrect behavior that affected users.
After: Daemon housekeeping — delete empty ml/ package, drop dead pygame-ce dependency, fix stale CLAUDE.md daemon tree — the issue has been resolved and verified with tests."

**Show:** The fix in action, the problem is now resolved

## Scene 4: Closing (30 sec)

**Presenter says:** "The issue is fixed and users can now proceed without problems."

**Show:** The system working correctly after the fix