# Demo Script — 39-9

**Total time: ~12 minutes**

**Slide 1 — Title (0:00–0:30)**
Introduce the story: "We're going to show you what it looks like when a dungeon actually tests your endurance."

**Slide 2 — Problem (0:30–2:00)**
Reference the playtest log from 2026-05-10. Point out that across a full dungeon descent, CON was checked exactly 3 times out of 35 challenges. Show the before-state of `beat_vocabulary.yaml` — scroll to the CON section. Count the entries aloud. "Three. In a dungeon crawler."

If the file is available live:
```bash
grep -c "stat: CON" sidequest-content/genre_packs/caverns_and_claudes/beat_vocabulary.yaml
```
Expected before: `3`. Expected after: `8+`.

**Slide 3 — What We Built (2:00–5:00)**
Open `beat_vocabulary.yaml` and show the five new beat entries side by side. Read the flavor text for `cave_air_poisoning` aloud — this is the prose a CON-9 character sees vs. a CON-17 character. Make it concrete: "The narrator says something different depending on whether you're physically tough."

Then run a quick live playtest comparison:
```bash
just playtest-scenario caverns_and_claudes_con_check
```
Show terminal output — two runs, one with CON 17, one with CON 9. Count the diverging outcomes. Target: ≥3 distinct beat types trigger different text.

**Fallback if playtest fails**: Go to Slide 3 and show the before/after YAML side-by-side screenshot. Read the beat names and outcomes aloud — the data tells the story without the live run.

**Slide 4 — Why This Approach (5:00–6:30)**
"We didn't touch a single line of Python. No server changes, no deployment risk, no API contract impact. The engine already knew how to handle CON — it just had nothing to do."

**Slide 5 — Before/After (6:30–9:00)**
Show the stat display cleanup. Open `rules.yaml` in the before state — point to `hp`, `max_hp`, `ac` in `stat_display_fields`. "These fields haven't existed in the game for over a year. They were display ghosts." Then show the after state — clean list. "Removed."

```bash
grep -E "hp|max_hp|ac" sidequest-content/genre_packs/caverns_and_claudes/rules.yaml
```
Expected after: no matches.

**Slide 6 — Roadmap (9:00–10:30)**
Position this as foundation for the upcoming CON-forward world design.

**Slide 7 — Questions (10:30–12:00)**

---
