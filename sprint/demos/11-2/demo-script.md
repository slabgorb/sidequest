# Demo Script — 11-2

**Total estimated time: 8 minutes**

---

**Scene 1 — Title (0:00–0:30) → Slide 1**
Open with the slide. Say: *"Today we're shipping the lore brain — the part of the engine that lets the narrator actually know things about the world it's describing."*

---

**Scene 2 — Problem (0:30–1:30) → Slide 2**
Walk through the problem slide. Reference a concrete pain point: *"Without this, if a player asked about the Iron Consortium faction, the narrator would invent something on the spot — or say nothing. Today we fix that."*

---

**Scene 3 — What We Built (1:30–3:00) → Slide 3**
Describe the card-catalog analogy. Point to the diagram (Slide 3 or embedded). *"The store loads on startup, organizes entries by category, and lets the narrator fetch by category or keyword in under a millisecond."*

---

**Scene 4 — Live Demo (3:00–6:00) → Slide 3 (stay here during demo)**

Open a terminal. Run:

```bash
# Start the API server
just api-run
```

In a second pane, query by category:

```bash
curl -s http://localhost:8080/lore/category/factions | jq .
```

Expected output: a JSON array of faction lore entries (e.g., `"Iron Consortium"`, `"Dust Riders"`, `"The Pale Circuit"`).

Then query by keyword:

```bash
curl -s "http://localhost:8080/lore/search?q=iron" | jq .
```

Expected output: all entries whose text or tags contain `"iron"` — should return at minimum the Iron Consortium entry with its full lore body.

**Fallback:** If the server fails to start, switch to Slide 4 (Why This Approach) and walk through the architecture reasoning. Say: *"The live path is straightforward — let me show you the design instead."*

---

**Scene 5 — Roadmap (6:00–7:30) → Roadmap Slide**
Connect to narrator integration. *"This store is the foundation — next sprint the narrator will call into it automatically when building scene context."*

---

**Scene 6 — Questions (7:30–8:00) → Questions Slide**

---
