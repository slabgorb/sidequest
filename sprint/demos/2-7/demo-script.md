# Demo Script — 2-7

**Total runtime: ~8 minutes**

---

**Slide 1 — Title (0:00–0:30)**

Open with: "This story closes the loop between what the AI says happened and what the game actually remembers."

---

**Slide 2 — Problem (0:30–2:00)**

Walk through the before scenario. Say: "Before this fix, the AI narrator could describe a fight — Thorn takes 8 damage, the innkeeper turns hostile, you discover a new route — and none of it would stick. The game state was unchanged. The player's screen showed nothing. We were narrating into a void."

Point to the Before/After slide. Show the broken output: the party health bar still reads `25/30` after taking damage, the NPC disposition still says `Neutral`, and the map shows no new route.

*Fallback if live demo fails: stay on Slide 2 and reference these exact values verbally.*

---

**Slide 3 — What We Built (2:00–4:00)**

Live terminal demo. Run:

```bash
cargo test --package sidequest-game patch_pipeline 2>&1 | tail -20
```

Expected output: `test result: ok. 47 passed; 0 failed` — point to this number explicitly. "47 tests, 13 acceptance criteria, all green."

Then walk through one concrete test case. Say: "We send a patch saying Thorn takes 8 damage. Before the patch, HP is 25. After: 17. The broadcast fires a `PARTY_STATUS` message with `current_hp: 17, max_hp: 30`. That's what moves the health bar."

*Fallback: Slide 3 bullet list, skip terminal.*

---

**Slide 4 — Why This Approach (4:00–5:30)**

No live demo needed. Talk through the three guardrails: strict validation, deduplication for discovery, identity locking for NPCs. Use the innkeeper as the running example: "Marta's pronouns are set once. No future patch can accidentally change her."

---

**Slide 5 — Before/After (5:30–6:30)**

Reference the Before/After section below. Walk column by column: HP change, NPC attitude, location discovery. Show that each row now resolves correctly.

---

**Slide 6 — Roadmap (6:30–7:30)**

Explain what this unlocks: "Now that state changes are reliably applied and broadcast, the next story (2-8) can wire the WebSocket layer — the messages we're now generating correctly will actually flow to the player's browser."

---

**Slide 7 — Questions (7:30–8:00)**

---
