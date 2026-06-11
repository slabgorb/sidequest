**Setup before the demo:** Have a browser open to the SideQuest character creation screen, connected to a running server with the Seaboard of Saints pack loaded.

**Slide 2 — Problem:** Narrate: "Before this sprint, if you started a new character in the Seaboard setting, you'd go straight to naming and attributes. You'd have no lineage, no inherited biology. Every character was the same blank slate."

**Slide 3 — What We Built:**

*Scene 1 (0:00–1:00)* — Click "New Character" on the Seaboard of Saints world. Call out that the flow now shows a **Stock selection step** before attributes. The two options visible are Sleeper and [Animal Stock name]. Point to the flavor text for Sleeper: "Woke from cryo-stasis. Carries implants. Costs System Strain."

*Scene 2 (1:00–2:30)* — Select **Sleeper**. Show the attributes screen: point to the auto-applied modifiers (e.g., +1 to a specific stat). Scroll to the System Strain display — show that the Sleeper's implants have already consumed strain slots before the player has done anything. Say: "They didn't choose those implants. They woke up with them. That's the fiction, and it's built into the math."

*Scene 3 (2:30–3:45)* — Advance to the Mutation step. Show the mutation list — it reflects only the mutations valid for a Sleeper. Now go back, change Stock to the Animal option, and return to the Mutation step. The list changes. Say: "The branch is driven entirely by which Stock you picked. The engine doesn't know anything special about Sleepers — it just reads the data."

*Scene 4 (3:45–4:30)* — Open `stocks.yaml` in a text editor (or show a screenshot). Point to the Sleeper entry: the implant IDs, the strain cost, the mutation grants. Say: "This is the entire definition of a Sleeper. Adding a new Stock is this file, nothing else."

**Fallback:** If the live server is unavailable, show the Before/After slide (Slide 5) — a side-by-side of the old flow (no Stock step) versus the new flow (Stock → Attributes → Mutations branched).

---