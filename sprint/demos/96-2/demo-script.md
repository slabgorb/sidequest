**Setup (before the presentation):** Have two browser tabs open. Tab A: a fresh character creation flow in Barsoom with Race = Red Martian. Tab B: the same flow with Race = Earthman. Have the GM panel open in a third tab showing the trait provenance table.

**Scene 1 — "The Broken State" (Slide 2: Problem) [~2 min]**
Explain that before this fix, opening Tab A (Red Martian) would show the Earthman Strength boon in the character's starting trait list. Point to the `source: Race` label on that trait. Say: "This Red Martian character has an Earthman bonus. That's like giving a French character a British passport because they're both in Europe."

**Scene 2 — "The Fix in Action" (Slide 3: What We Built) [~3 min]**
Switch to the patched build. Reload Tab A (Red Martian). The Earthman boon is absent — the trait list shows only Red Martian traits. Open Tab B (Earthman). The boon is present, labeled `source: Barsoom World Trait` instead of `source: Race`. Type in the terminal:
```bash
just server-test -k test_earthman_boon
```
Show the green output confirming the boon gate passes for Earthman and fails for all other races.

**Scene 3 — "The Audit Trail" (Slide 4: Why This Approach) [~2 min]**
Switch to the GM panel tab. Navigate to the Trait Provenance section. Show that the `source` column now correctly reads `world:barsoom` for the Earthman boon row instead of `genre:heavy_metal`. Explain that every downstream system — advancement, the balance checker, the narrator's character snapshot — now sees the correct origin.

**Fallback:** If the live server isn't cooperating, switch to Slide 5 (Before/After) and show the screenshot comparison of the trait table with the old `source: Race` label versus the new `source: Barsoom World Trait` label.

---