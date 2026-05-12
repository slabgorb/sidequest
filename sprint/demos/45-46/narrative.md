# 45-46

## Problem

**Problem:** The codebase had a temporary compatibility shim — a fake "old name" for a renamed internal component — that was supposed to live for one release and then be deleted. It overstayed its welcome with no enforcement mechanism, no removal date, and no alarm if something tried to use the old name.

**Why it matters:** Compatibility shims are technical debt with an expiration date. Every day they stay past that date, they become load-bearing by accident — new code quietly depends on the old name, tests start relying on the warning behavior, and the "temporary" bridge becomes permanent. Removing it on schedule proves the rename actually finished.

---

## What Changed

Think of this like a company changing a department's name. In the first week after the rename, you put a forwarding note on the old mailbox: "This is now called NpcEncounterLogTag — please update your address book." That forwarding note was the shim.

This story removes the forwarding note entirely. The old mailbox is gone. Anyone still sending mail to the old address gets an immediate error instead of a silent redirect. The docstring on the class was also updated to say "the forwarding note is gone" rather than "the forwarding note will be removed soon."

Three things changed:
1. **The shim itself was deleted** — the ~30 lines of code that caught old-name references and quietly forwarded them.
2. **Two tests that verified the shim worked were deleted** — they tested behavior that no longer exists.
3. **One test was upgraded** — it now actively asserts the old name is *gone*, acting as a permanent regression guard so the shim can never accidentally come back.

---

## Why This Approach

The rename happened in story 45-43. The shim was always meant to be one-release scaffolding. Removing it in Wave 1 cleanup (story 45-46) is the second half of the same operation — you don't get credit for a rename until the training wheels are off.

The regression guard (the upgraded test that asserts the old name doesn't exist) is the key structural choice. Without it, a future developer could accidentally re-introduce the alias and tests would pass. With it, any attempt to bring the old name back breaks the test suite immediately.

This is the engineering equivalent of destroying the mold after casting a new part, rather than leaving it around where someone might use it again.

---
