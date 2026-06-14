**Setup:** Running server with a WWN-bound world (e.g., `caverns_and_claudes/beneath_sunden`). Solo player character with combat active. No live demo dependency on multiplayer.

---

**Slide 2: Problem**

*Timing: 90 seconds*

Open a save file mid-combat. Describe the old behavior: "Before this fix, the moment a character's HP hit zero, the session reported them dead. There was no pause, no window, no drama — just a sudden ending."

Show the old status payload (if available in archive): `status: terminal_dead`, no intermediate step, no `stabilizable` field.

Fallback: Show slide screenshot of the flat death transition — no intermediate state visible.

---

**Slide 3: What We Built**

*Timing: 2 minutes*

Run this command to start a solo session in a WWN world:
```bash
just playtest --world beneath_sunden --solo --character "Mira Vane" --hp 3
```

Trigger combat, take enough damage to drop to 0 HP with no remaining hostiles.

Show the WebSocket payload in the terminal:
```
dying_window.opened  { rounds_limit: 4, rounds_elapsed: 0, stabilize_difficulty: 8 }
```

Status panel shows: **Mortally Wounded** (not dead).

Type a free-text action as the downed player: `"I press my cloak against the wound and try to slow the bleeding."`

Show the tick event:
```
dying_window.tick  { rounds_elapsed: 1, stabilize_difficulty: 9 }
```

Point out: difficulty climbed by 1. The clock is real.

Fallback: If live demo fails, show Slide 3 with the annotated payload screenshots from the spec doc.

---

**Slide 4 (optional Before/After)**

*Timing: 60 seconds*

Side-by-side: old session log showing `terminal_dead` firing immediately at 0 HP vs. new log showing the `mortally_wounded` → `dying_window.opened` → two `dying_window.tick` events → `dying_window.resolved` sequence.

---

**Slide: Roadmap**

*Timing: 60 seconds*

Note the two remaining open edges: multiplayer (an ally can stabilize you — the actuator is another player) and the GM-side visibility of the dying window in the watcher panel.

---