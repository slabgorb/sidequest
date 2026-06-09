**Total runtime: ~8 minutes**

---

**Scene 1 — Title (Slide 1) | 0:00–0:30**

Open on the title slide. Introduce the story as the sixth installment in a six-week campaign to decouple the game's reference pages from the server's rendering engine.

---

**Scene 2 — The Problem (Slide 2) | 0:30–2:00**

Walk through the "before" state. The server was generating HTML pages that mixed player-visible content with GM-only secrets in a single document. Show Slide 2 bullet: "Server rendered HTML = server controlled the UI = no modernization without surgery."

Fallback: if the live demo below fails, stay on Slide 2 and describe the problem verbally.

---

**Scene 3 — What We Built (Slide 3) | 2:00–4:30**

Transition to the live demo. Open a terminal (server must be running: `just server`).

Run:
```bash
curl -s http://localhost:8765/reference/api/rules/space_opera | python3 -m json.tool | head -60
```

Point out:
- `"schema_version": 1` — versioned contract, safe to build clients against
- `"pack": "space_opera"` — pack-scoped (no world slug in the URL or response)
- `"sections": [...]` — array of section objects, each named and self-contained
- Look for a `rules` section and a `beat_vocabulary` section; confirm `narrator_hint` is **absent** and `obstacles` is **absent** from both

If the server isn't running, show **Slide 3 with a pre-captured JSON snippet** showing the same fields.

Then try an unknown pack to show the 404 guard:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/reference/api/rules/does_not_exist
```
Expected output: `404`. This is the "unknown pack" boundary — the firewall doesn't guess.

---

**Scene 4 — Why This Approach (Slide 4) | 4:30–6:00**

Explain the firewall reuse story. The `reference_visibility.py` classifier has been processing lore sections since Story 100-2 (four stories ago). Rules files are YAML just like lore files. Rather than write a second scrubber, this story routes rules through the same pipeline. The existing keeper carves (`narrator_hint`, `power_tiers.*.npc`, `beat_vocabulary.obstacles`) were already registered — this story connected the pipe, not the logic.

Mention the Unicode bug catch: the test suite caught a vacuous firewall assertion caused by an em-dash in the test fixture data being ASCII-escaped, making the "field is absent" check trivially true. Fixed before merge.

---

**Scene 5 — Roadmap (Slide: Roadmap) | 6:00–7:30**

Point to the two immediate next stories:
- **100-7** (Theme tokens): the same JSON payload will carry CSS variable tokens so the browser can style the page without a WebSocket session
- **100-8** (React shell): the first React routes that consume these endpoints — the payoff for all six Phase 1 stories

---

**Scene 6 — Questions (Slide: Questions) | 7:30–8:00**

Open floor.

---