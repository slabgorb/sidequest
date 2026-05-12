# Demo Script — 49-7

**Total runtime: ~8 minutes**

### Scene 1 — The Problem (Slides 1–2) | 0:00–1:30

Open the game to a saved combat session with three players: Carl (Fighter), Donut (Cleric), Katia (Thief). If live demo is unavailable, show the before screenshot from `oq-2/.playwright-mcp/` showing all three players' Confrontation tabs side by side.

Point out: all three tabs show identical lists. Count the buttons aloud — "sixteen options, same for everyone." Ask the audience: "Which of these does a Fighter actually use?" Pause. "About ten of them. The rest belong to other classes."

**Fallback:** Show Slide 2 (Problem) with the screenshot of the 16-button panel and the callout box: "Fighter sees Cast Spell. Cleric sees Backstab."

---

### Scene 2 — What We Built (Slide 3) | 1:30–4:00

Switch to the after state. Boot a fresh 3-PC session in the caverns_sunden world:

```bash
just playtest --scenario caverns_sunden_combat --players carl,donut,katia
```

Navigate to the Confrontation tab for Carl (Fighter). Count the buttons — approximately 10. Highlight that Cast Spell, Backstab, and Turn Undead are gone.

Switch to Donut (Cleric). Show approximately 9–11 buttons depending on remaining spell slots. Point to "Pray for Aid" and "Turn Undead" — present. Point to "Backstab" — absent.

Switch to Katia (Thief). Show approximately 10 buttons. Point to "Backstab" — present. Point to "Turn Undead" — absent.

Say: "Three players, three menus. Each one is exactly the moves that player can actually take."

**Fallback:** Show the after screenshots from `oq-2/.playwright-mcp/` — three side-by-side tabs with different button counts. The slide caption reads: "Carl: 10 actions. Donut: 11 actions. Katia: 10 actions. No overlap where there shouldn't be."

---

### Scene 3 — The Spell Slot Edge Case (Slide 3, continued) | 4:00–5:00

Still on Donut's panel. Burn all spell slots (use the GM panel to set `spell_slots_remaining = 0` if available, or narrate the scenario). Refresh the confrontation:

```bash
# GM panel: set Donut's slots to 0, then re-enter combat
```

Show that "Cast Spell" disappears from Donut's panel when she's out of slots. When slots are restored, it comes back. 

Say: "The panel reflects real-time character state, not a static template."

**Fallback:** Show a two-frame before/after screenshot on Slide 3: "Cast Spell visible (2 slots left)" → "Cast Spell hidden (0 slots left)."

---

### Scene 4 — GM Observability (Slide 4) | 5:00–6:30

Open the GM dashboard (OTEL panel):

```bash
just otel
```

Trigger a combat entry. In the span stream, filter for `confrontation_beat_filter_span`. Show two entries firing per combat activation:

- One with `source=narrator_prompt` — the AI's decision filter
- One with `source=ui_panel_projection` — the player panel filter

Point to the attributes: `recipient_pc`, `recipient_class`, `pool_size: 16`, `filtered_size: 10`. Say: "This is the lie detector. We can see exactly which filter ran, for which player, and what it removed. If the panel ever shows the wrong buttons, this trace tells us why in under 30 seconds."

**Fallback:** Show Slide 4 (Why This Approach) with a screenshot of the two span entries and the callout: "Two filter events, two audiences — narrator and player panel — independently verified."

---

### Scene 5 — Latency Check (Slide 4, continued) | 6:30–7:30

In the server log, grep for the narrator duration line:

```bash
grep "Claude CLI returned streaming narration duration_ms" /tmp/sidequest-server.log | tail -20
```

Show the p50 numbers before and after. The per-recipient loop adds less than 100ms to total dispatch time at four players — roughly the time to blink. Say: "We're building one extra list per player, not rerunning the AI. The overhead is negligible."

**Fallback:** Show a simple table on Slide 4: "Before: 1,240ms avg. After: 1,248ms avg. Delta: 8ms."

---

### Scene 6 — Wrap (Slides 5–6: Roadmap + Questions) | 7:30–8:00

Transition to roadmap slide. Hand to Q&A.

---
