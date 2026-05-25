# 64-6

## Problem

**Problem:** A hidden wiring knot in the server's startup code caused one of the dungeon map tests to fail whenever it ran by itself — even though the full test suite appeared to pass. **Why it matters:** Intermittent, isolation-dependent failures are the most dangerous kind of bug. They hide until the worst possible moment — a demo, a deploy, or a late-night session — and they erode trust in the test suite itself. If you can't run a single test in isolation, your safety net has holes.

---

## What Changed

Two modules in the server were each trying to load the other before either one had finished loading. Imagine two people who refuse to enter a room until the other person is already inside — nobody gets in.

The specific knot: `session_handler` was importing from `websocket_session_handler`, and `websocket_session_handler` was re-exporting a symbol from `session_handler` for backwards compatibility. Python's module loader hit this loop and either crashed or produced a half-initialized module, depending on which file Python happened to load first.

The fix cut the loop. The backwards-compatibility re-export was moved or restructured so neither module depends on the other at import time. Both modules can now load independently, in any order, without waiting on each other.

---

## Why This Approach

The simplest fix for a circular import is always to break the cycle at its weakest link — the place where the dependency is least essential. Here that was the backwards-compat re-export: a convenience shim that existed only so old call sites didn't have to update their import paths. That shim was the sole reason the cycle existed. Removing or relocating it cost nothing functionally and eliminated the entire problem class.

The alternative — restructuring both modules into a shared third module — would have been correct but disproportionate for a 2-point bugfix. The targeted cut is the right tool here.

---
