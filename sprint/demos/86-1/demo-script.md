**Total runtime: ~8 minutes**

---

**[Slide 1: Title — ~30 seconds]**
"We're going to show you Road Warrior combat going from 'the narrator makes something up' to 'the rules decide.' Quick demo, then I'll walk you through what changed and what's next."

---

**[Slide 2: Problem — ~90 seconds]**
"Before today, a Road Warrior combat scene looked like this."

Run in terminal:
```bash
# Show the old OTEL output — no combat spans firing
just otel
```
Point to the GM Dashboard. Show the confrontation panel: `beat_selections: 0`, no `cwn_strike` or `shock_damage` spans, combat resolution column empty.

"The narrator was improvising. No rules, no math, no way to verify the fight was real. Sebastien and Jade — our mechanics-first players — felt this every session."

*Fallback if dashboard isn't live: Slide 2 has a screenshot of the empty span panel.*

---

**[Slide 3: What We Built — ~2 minutes]**
"Now watch what happens when a driver gets into a fight."

```bash
# Start a road_warrior session and trigger a vehicle confrontation
just playtest --genre road_warrior --scenario driver_combat_smoke
```

On the GM Dashboard, show:
- `cwn_strike` span firing with `damage: 6`, `shock: 2`
- Character HP ticking from `18 → 12` (Shock applied)
- A second hit: `14 → 8` (cumulative)
- Win condition met: `hp_depletion: true`, `winner: player`

"That 18→12→8 progression? That's real math. The engine ran it, not the narrator."

*Fallback: Slide 3 has a before/after screenshot of the OTEL span tree.*

---

**[Slide 4: Why This Approach — ~60 seconds]**
"We reused the CWN ruleset that already powers neon_dystopia. No new plumbing — just a content binding. And we applied the wiring checklist we built from the last two Without-Number integrations, so the integration tests were written before a single line of pack YAML."

Show passing test output:
```bash
cd sidequest-server && uv run pytest tests/genre/test_road_warrior.py -v
```
Expected output: `test_road_warrior_pack_loads_with_dual_dial_schema PASSED`, `test_cwn_spans_fire_on_real_turn PASSED`

---

**[Before/After Comparison — ~60 seconds]**

*Point to Before/After slide.*

"Old Road Warrior: narrator says 'you take a hit' and moves on. New Road Warrior: engine says Shock 4, HP now 14, Trauma threshold not crossed — narrator has facts to work with, not blanks to fill."

---

**[Roadmap — ~60 seconds]**
"This is Plan 1 of 3 for Road Warrior. Plan 2 adds the War Rig — crew-seat vehicle combat, more like a naval engagement than a duel. Plan 3 wires the chase subsystem so pursuit scenes have the same mechanical backbone as fights. After that, Road Warrior is feature-complete."

---

**[Questions — remaining time]**

---