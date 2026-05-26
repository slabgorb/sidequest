# Demo Script — 63-6

**Total runtime: ~8 minutes**

---

**Slide 1: Title** (0:00–0:30)

*"Today we're closing a gap in the SideQuest reference wiki experience — and doing it in a way that respects the game's existing design principles."*

---

**Slide 2: Problem** (0:30–2:00)

Open a running SideQuest session in the browser (`just up`, then navigate to `http://localhost:5173`). Start a session in any genre pack with a named region — *beneath_sunden* or *space_opera* are reliable.

Show the Location Panel on screen. Point to the region header: *"This is 'The Iron Quarter' — or whatever region the player just entered. It's text. You can read it, but you can't do anything with it. The wiki has a full page on this place — history, lore, points of interest — but there's no bridge."*

**Fallback if the server isn't running:** Show Slide 2 (Problem screenshot — plain-text region header from a pre-existing screenshot). Narrate the same point.

---

**Slide 3: What We Built** (2:00–4:30)

With the game running, navigate to a region that has a known wiki entry (in *beneath_sunden*, move to any named region — "Ropefoot," "The Deep," etc.).

Point to the location panel region header. *"Watch the header."* It now renders as an underlined link.

Click it. A new browser tab opens to `http://localhost:8765/reference/lore/beneath_sunden/ropefoot#location-ropefoot` (or equivalent). Walk through the wiki page briefly: lore section, world-name hero, points of interest images.

Come back to the game. Navigate to an unnamed or procedurally-generated region with no wiki anchor. Point to the plain-text header: *"When there's no wiki entry — or the region is generated on the fly — the header stays as plain text. No broken links."*

**Fallback if live navigation fails:** Show Slide 3 before/after side-by-side: left panel shows plain-text header, right panel shows the same header as a clickable link.

---

**Slide 4: Why This Approach** (4:30–5:30)

*"The team didn't build new infrastructure. The character sheet already linked to class reference pages using this exact pattern. We plugged a new data source — location regions — into the same pipe. Reuse first."*

Show the brief before/after of the character sheet class link (already shipped) alongside the new location link — same visual pattern, same behavior.

---

**Slide (optional): Before/After** (5:30–6:00)

Side-by-side screenshot: location panel with plain `<span>` header vs. location panel with `<a>` anchor. Two lines of text. Three seconds.

---

**Slide: Roadmap** (6:00–7:00)

*"This closes the last missing panel link in Epic 63. Every major in-game surface — character sheet, knowledge journal, location entities, and now the location header — has a path to the reference wiki."*

---

**Slide: Questions** (7:00–8:00)

---
