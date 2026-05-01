# 45-26

## Problem

**Problem:** The save system had two different ways to identify a game — an old (genre + world + player name) file path, and a newer unique "game slug" code — both active in production simultaneously. **Why it matters:** Dead code paths are security surface, maintenance burden, and a source of subtle bugs. One such bug was discovered during this cleanup: new-style game connections were silently failing to play their opening scene because a counter check used the wrong starting value. Running two parallel identity systems also blocked multiplayer save sharing, which requires the single-slug model.

---

## What Changed

Imagine a library that used to file books two different ways — first by "Author → Genre → Title" shelving, and later by a unique barcode sticker. For a while both systems coexisted. This story throws out the old shelving system entirely.

Specifically:
- **Three API routes were deleted**: the "list my saves," "create a save slot," and "delete a save" endpoints that used genre/world/player-name as the address. Gone.
- **One internal helper function was deleted**: the code that calculated a file path from those three pieces of information (`db_path_for_session`). The barcode-based version (`db_path_for_slug`) is now the only one.
- **The old connection handshake was deleted**: the ~272-line branch that let a game session start by saying "I want genre X, world Y, player Z." Now every connection must present a slug — no slug, no session.
- **A latent bug was fixed**: New-style connections were never triggering the opening scene of a game because a counter was checking `== 0` when it always starts at `1`. Fixed to check "is this the first time this slug has ever connected?" instead.
- **Net result**: ~900 lines of production code removed; the test suite grew 86 lines of permanent guardrails to ensure nothing can re-add the deleted routes.

---

## Why This Approach

The slug model (MP-03) was already the exclusive path used by the UI. These endpoints were **confirmed dead code** — no real traffic, but still tested, maintained, and reachable by anything that could call the API. Keeping dead code alive has compounding costs:

1. It hides bugs (as demonstrated by the opening-scene fix, which would have gone unnoticed under the old path).
2. It doubles the surface area for security review.
3. It blocks future multiplayer work, which requires a single canonical save identity per game.

The correct engineering move at this stage was deletion, not deprecation tags. The UI had already migrated; the only things still hitting the old paths were tests, which were retargeted in the same commit. Automated tests now enforce the absence of these routes at the code level — a future developer cannot accidentally re-add them without a test failure.

---
