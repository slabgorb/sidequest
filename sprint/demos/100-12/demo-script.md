**Total runtime: ~8 minutes.**

**Setup (before presenting):** Server running on port 8765, UI dev server on 5173. Have a browser tab pointed at `http://localhost:5173/reference/lore/space_opera/perseus_cloud`. Have a second tab at `http://localhost:8765/reference/api/lore/space_opera/perseus_cloud` (the raw JSON API).

---

**Slide 1 (Title) — 0:00–0:30**
> "Today we're closing out the Reference Pages epic — twelve stories over two days. Phase 4 is the flip: the old Python HTML engine is retired and the React client owns rendering end-to-end."

---

**Slide 2 (Problem) — 0:30–2:00**
Reference the split-brain map problem. Say: "Every time someone adjusted the world map layout, they had to make the same change in Python and TypeScript. Here's what that looked like."

Show the audience: open `git log --oneline --diff-filter=D -- '*reference_map.py' '*cartographyLayout.ts'` in the terminal. Point out both files deleted in the same commit. Say: "One map renderer, one place to change it from now on."

*Fallback if terminal fails: Slide 2 bullets cover this — read the two filenames aloud.*

---

**Slide 3 (What We Built) — 2:00–4:00**
Live demo in two acts:

**Act A — The public API:**
```bash
curl -s http://localhost:8765/reference/api/lore/space_opera/perseus_cloud | python3 -m json.tool | head -60
```
Point out: `sections` array with typed entries (`cast`, `poi`, `timeline`, `generic_yaml`), `theme_tokens` block at the top, **no** `ocean`, `history_seeds`, `initial_disposition`, or any NPC keeper field visible anywhere in the output.

**Act B — The rendered page:**
Switch to the browser tab at `http://localhost:5173/reference/lore/space_opera/perseus_cloud`. Walk through:
- Cast section with portrait thumbnails (these are R2 URLs resolved server-side)
- POI section with landscape images
- The world map rendered by d3-dag (deterministic node positions — refresh the page and confirm nodes don't move)
- Timeline section

*Fallback if browser rendering fails: switch to Slide 3 screenshot — prepared static screenshot of the reference page.*

---

**Slide 4 (Why This Approach) — 4:00–5:30**
Explain the firewall decision in one sentence: "The Python code that decides what's public stayed in Python — we only moved where pixels get painted." Then show the security constraint live:

```bash
curl -s http://localhost:8765/reference/api/lore/space_opera/perseus_cloud | python3 -c "import sys,json; d=json.load(sys.stdin); print([k for sect in d.get('sections',[]) for k in (sect.get('data') or {}).keys() if 'keeper' in k.lower() or 'ocean' in k.lower() or 'disposition' in k.lower()])"
```
Expected output: `[]` — empty list. Say: "Zero keeper fields crossed the wire."

*Fallback: Slide 4 quote block — copy of this exact command and its expected empty output.*

---

**Roadmap slide — 5:30–7:00**
See Roadmap section below. Touch on epic 98 / the drill-down view briefly: "The map component we built is already wired to accept a selected-node signal — that's the hook epic 98 needs for the orrery drill-down."

---

**Questions — 7:00–8:00**

---