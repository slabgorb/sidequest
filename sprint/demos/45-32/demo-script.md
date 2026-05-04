# Demo Script — 45-32

This story has no visible user-facing changes — it is entirely internal code quality work. There is no runtime behavior to demonstrate. The demo is a "before and after" of the test suite.

**Scene 1 (0:00–1:30) — Slide 1: Title**
Open with: "This is a one-point housekeeping story. We shipped a multiplayer feature in 45-2, got a thorough code review, and this story closes out the non-blocking findings from that review."

**Scene 2 (1:30–3:00) — Slide 2: Problem**
Show the before-state: "Here's the test assertion we inherited." Open `tests/server/test_45_2_chargen_to_playing_wire.py` and show line 123 (before): `assert out, "connect must produce SESSION_CONNECTED"`. Explain: "This passes if the server returns *anything* — including an error. It's a weak gate."

**Scene 3 (3:00–4:30) — Slide 3: What We Built**
Show the after: `assert any(getattr(m, "type", None) == "SESSION_EVENT" and getattr(getattr(m, "payload", None), "event", None) == "connected" for m in out)`. Explain: "Now it only passes if the response is specifically a `SESSION_EVENT` with event value `"connected"`. Wrong message type → test fails."

**Scene 4 (4:30–5:30) — Live demo fallback**
Run: `cd ~/Projects/sidequest-server && uv run pytest tests/server/test_45_2_chargen_to_playing_wire.py tests/server/test_lobby_state_machine.py tests/server/test_mp_turn_barrier_active_turn_count.py -v`
Expected: 21/21 passing. If environment isn't available, show Slide 3 (the diff) and read the green checkmarks from the session log above.

**Scene 5 (5:30–6:30) — Slide 4: Why This Approach**
"The reviewer's own suggestions had two small errors — a message type that doesn't exist, and a file path that's out of date. The team verified against running code before applying fixes. That's the right discipline: cleanup stories can introduce bugs if done mechanically."

**Scene 6 (6:30–7:30) — Before/After Slide**
Walk through the comparison table below.

**Scene 7 (7:30–8:00) — Questions**

---
