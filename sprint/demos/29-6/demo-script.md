# Demo Script — 29-6

**Total runtime: ~6 minutes**

---

**Slide 1 (Title) — 0:00–0:30**
Open with the slide. Say: "Today we're talking about maps — specifically, making them feel like real places."

---

**Slide 2 (Problem) — 0:30–1:30**
Show the before screenshot (old map with floating rooms). Point out: "The entrance is here, the tavern is... somewhere over here, and this tiny square is supposedly a throne room. Players were constantly asking 'where am I?' in playtests." If no screenshot is available, describe the before state verbally and stay on Slide 2.

---

**Slide 3 (What We Built) — 1:30–3:00**
Switch to the live app (or after screenshot). Load the `flickering_reach` scenario — it has enough rooms to show the tree branching clearly. Call out:
- The entrance room at the center
- Two corridors branching left and right with rooms snapping flush against each other (point to a shared wall)
- The throne room rendered noticeably larger than the guard post next to it

Say: "Every room you see is sized to its actual square footage in the game data. Nothing is faked."

*Fallback:* If the app won't load, show the After slide with annotated screenshot. Point to the same three elements.

---

**Slide 4 (Why This Approach) — 3:00–4:15**
Stay on Slide 4. "We chose tree layout because dungeon topology is already a tree — there's one entrance and everything branches from it. Shared-wall snapping costs us nothing extra and eliminates ambiguity. And pulling real dimensions from the game data means the map and the game are always in sync — one source of truth."

---

**Optional Before/After — 4:15–5:00**
Side-by-side comparison. Let it speak for itself; say only: "Same dungeon, same data."

---

**Roadmap — 5:00–5:30**
Hit the highlights (see Roadmap section below).

---

**Questions — 5:30–6:00**

---
