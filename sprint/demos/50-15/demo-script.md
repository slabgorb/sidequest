# Demo Script — 50-15

**Setup (before presenting):** Have the dev server running (`npm run dev`). Load the `tea_and_murder` genre pack and advance to a scene where the narrator has delivered at least two turns of narration containing footnoted clues (e.g., the stopped clock, the half-burned letter).

---

**Slide 1: Title** *(0:00–0:30)*
Introduce: "We're looking at a fix to the Knowledge Journal — the in-game record of everything players have discovered."

---

**Slide 2: Problem** *(0:30–1:30)*
"Every fact in the game has a server-assigned ID, like `fact-clock-stopped-2026-05-14`. Before this fix, the UI ignored that ID and stamped its own: `turn3-footnote2`. The result: open the journal, and the stopped clock appears twice — once from when the narrator first mentioned it, once from when the journal was refreshed."

*Show:* The old behavior can be illustrated with a screenshot or the test output — specifically the AC4 test description: "NARRATION + JOURNAL_RESPONSE sharing a fact_id collapse to one entry — before the fix, knowledge[] had TWO entries."

---

**Slide 3: What We Built** *(1:30–2:30)*
"We removed the UI's ID-stamping logic entirely and replaced it with a single rule: use whatever ID the narrator supplied."

*Show in the diff:*
```
- const factId = `${turnCounter}-${fn.marker ?? knowledge.length}`;
+ if (!fn.fact_id) { console.warn(...); continue; }
+ seenFactIds.add(fn.fact_id);
```
"Three lines removed, two lines added. The deletion is the feature."

Also show: the local `FootnoteData` interface block that was deleted. "The UI had its own private definition of what a footnote was — one that didn't even have a field for `fact_id`. That's why the field was being ignored."

*Fallback if live demo fails:* Show Slide 3 with the diff screenshot. Point to the `-` and `+` lines.

---

**Slide 4: Why This Approach** *(2:30–3:15)*
"The narrator owns fact identity. The UI's job is to reflect it faithfully. Any other approach means the front end and back end are arguing about what the same clue is called, and the player's journal pays the price."

---

**Before/After (optional)** *(3:15–4:00)*
*Before:* Knowledge Journal showing `fact-3-1` and `fact-shared-id-001` as two separate entries for the same stopped clock.
*After:* One entry, keyed `fact-clock-stopped-2026-05-14`, stable across turns.

*Live demo command — run the new test suite:*
```bash
npx vitest run src/hooks/__tests__/useStateMirror-50-15-fact-id.test.tsx
```
Expected output: **13 tests passed**. Point to the AC4 test: "NARRATION footnote and JOURNAL_RESPONSE entry sharing a fact_id collapse to one entry."

*Fallback:* Show the test file's describe block headers — AC1 through AC5 plus the drop-path block — as slide bullets.

---

**Roadmap slide** *(4:00–4:30)*
See Roadmap section below.

**Questions** *(4:30+)*

---
