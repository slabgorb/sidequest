# 51-4

## Problem

**Problem:** Loading a specific pre-built game scenario required a developer to set an environment variable (`DEV_SCENES=1`) before starting the server — and running the server in its normal production mode silently omitted the feature entirely. **Why it matters:** Keith authored a library of scenario fixtures (pre-loaded game states for specific encounters, locations, and situations) so the team could jump straight to interesting moments for playtesting. But every time the server started normally — through the tunnel that real players use — those fixtures were invisible. The tool existed; nobody could reach it without knowing a secret handshake.

---

## What Changed

Think of it like a restaurant that kept its specials board locked in the back office, only readable if a manager unlocked it first. This story moves the specials board to the front of house and puts it on the menu.

Specifically:
1. **The lock is gone.** The server no longer requires a special startup flag to activate the scenario library. It's always on. Access is still gated — only people Keith's Cloudflare tunnel allows in can reach the server at all — so removing the extra lock costs nothing in security.
2. **There's now a menu.** A new server endpoint (`GET /dev/scenes`) scans the fixture folder and returns a list of what's available: name, genre, world, and a short description for each scenario.
3. **The Connect screen shows the menu.** When you open the game's connection page, you now see a "Scene Library" section below the normal connect controls. Each available scenario appears as a card with its name, genre badge, and description. Click a card — the scene loads and you're playing.
4. **Cleanup.** Two configuration variables that existed only to support the old lock were removed from the startup scripts and documentation.

---

## Why This Approach

The old gate existed for a good reason: when the harness was a brand-new, rough dev tool, putting it behind an env var kept it out of players' hands while it matured. That rationale expired once the Cloudflare tunnel became the actual security perimeter — the tunnel's email allowlist is the gatekeeper now, and it's far more robust than a server-side env var. Keeping the gate added friction without adding protection.

Rather than building a new admin interface or an elaborate permissions system, the team wired the *already-complete* fixture library into the *already-complete* connect flow. The fixture files, the hydration logic, the scene-loading endpoint — all of it existed. This story is integration work, not invention. That's why it shipped fast and clean: 45 tests, all green, no new surface to break.

---
