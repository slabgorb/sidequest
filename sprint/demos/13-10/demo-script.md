# Demo Script — 13-10

**Setup:** Two browser windows connected to the same game world, both logged in as players. Server logs visible in a terminal pane.

---

**Slide 2 — Problem**

*[~60 seconds]*

Describe the ghost player scenario in plain terms: Player A disconnects at the exact moment Player B is taking their turn. In the old code, Player A's name stays on the roster. Player B submits their action — the game waits. And waits. There's nothing in the logs. There's no error message. The session is frozen.

Fallback: If live demo isn't running, show the before/after slide instead.

---

**Slide 3 — What We Built**

*[~90 seconds]*

Open the server terminal. Connect Player 1, then Player 2. Then disconnect Player 2 while a lock is held. In the old code: `remaining_players = 2` would persist in logs. In the new code, logs will show:

```
INFO  Turn mode transitioned on player leave remaining_players=1
INFO  remove_player_from_session player_id="player2" remaining_players=1
```

Player 1's session continues normally.

For the barrier add_player failure: trigger a duplicate-player join attempt. Logs will now show:

```
ERROR Failed to add player to barrier — player will not participate in turn collection player_id="player3" error="..."
```

And Player 3's client receives an error message: `"Failed to join turn barrier: <reason>"` instead of silently stalling.

Fallback: Show the Before/After slide.

---

**Slide 4 — Why This Approach**

*[~60 seconds]*

Pull up the diff in GitHub. Point to the before lines — `let _ = barrier.add_player(...)` and `ss_arc.try_lock()` — and explain: the underscore means "throw this away." The `try_lock` means "give up immediately if busy." Both are valid tools in the right context; here they were in the wrong context. The fix is minimal and targeted — no architectural change, just replacing the wrong tool with the right one at each site.

---

**Before/After Slide — live commands (optional)**

```bash
# Trigger a ghost player in the old code:
# 1. Connect two players
# 2. Kill player 2's WebSocket mid-lock
# 3. Player 1 attempts action — hangs indefinitely

# In the new code:
# Same steps — Player 2 cleanup completes, Player 1's action proceeds
# Logs show: "remaining_players=1"
```

---
