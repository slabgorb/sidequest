### Scene 1 — Before State (1 min) | *Slide 2: Problem*

Open the browser console on the current game client. Navigate to the lobby. There are no verbosity or vocabulary controls visible in `ConnectScreen`. Point to the gap.

**Fallback:** If demo environment isn't available, show the slide with the two code lines: `narrator_verbosity='standard'` and `narrator_vocabulary='literary'` (from `session_helpers.py:1167-1168`) — these are the hardcoded values that were always used regardless of player choice.

---

### Scene 2 — The Lobby Controls (1 min) | *Slide 3: What We Built*

Load the updated lobby at `http://localhost:5173`.

> "Two new controls appear in the lobby below the character fields — Verbosity and Vocabulary."

Click through the options: Concise / Standard / Verbose. Click through: Accessible / Standard / Literary. Set it to **Verbose + Accessible**. Disconnect and reconnect — the selectors should still show **Verbose + Accessible** (localStorage round-trip).

**Fallback:** Show a screenshot of ConnectScreen with both sliders visible and labeled.

---

### Scene 3 — The Connection Payload (1 min) | *Slide 3: What We Built*

Open browser DevTools → Network tab. Connect with **Verbose + Accessible** selected.

Filter for WebSocket traffic. Click the connection frame. Show the outbound message — it carries `narrator_verbosity: "verbose"` and `narrator_vocabulary: "accessible"`.

**Exact command (server-side verification):**
```bash
grep "narrator.settings_resolved" ~/.sidequest/logs/sidequest-server.log | tail -5
```

Expected output: spans with `narrator_verbosity=verbose`, `narrator_vocabulary=accessible`, `narrator_verbosity_source=player`.

**Fallback:** Show the span output pre-captured in a text file.

---

### Scene 4 — Narration at Each Setting (2 min) | *Slide 3 continued*

Submit a turn with the same action at two different settings to show contrast. Use the pre-built test scenario:

```bash
just playtest-scenario verbosity_vocab_compare
```

Or manually: connect with **Concise + Accessible**, submit "I look around the room." Then reconnect with **Verbose + Literary**, submit the same action.

> "Notice the first is a short, plain sentence. The second is a paragraph with period vocabulary."

**Fallback (pre-recorded outputs — show on slide):**
- *Concise + Accessible:* "The room is empty. A door leads east."  
- *Verbose + Literary:* "The chamber lies in mournful stillness, dust motes suspended in the pale column of light admitted by the eastern door — which stands, it seems, slightly ajar."

---

### Scene 5 — Resuming a Session (30 sec) | *Slide 3 continued*

Save and close. Reopen the saved session via slug.

```bash
# In server logs
grep "ready.*narrator" ~/.sidequest/logs/sidequest-server.log | tail -3
```

Show that the `ready` payload carries the previously-chosen settings back to the client — sliders re-populate without the player re-entering their preference.

---

### Scene 6 — GM Dashboard Confirmation (30 sec) | *Slide 4: Why This Approach*

Open `http://localhost:8765/dashboard`. Point to the `narrator.settings_resolved` span column showing `verbose / accessible` for each turn. Show the `source` column: `player` (not `default_for_player_count`).

> "This is the lie detector. Before today, that field didn't exist — we had no way to verify the narrator was actually following the player's preference versus improvising."

---