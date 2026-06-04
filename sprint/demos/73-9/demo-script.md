**Audience:** Engineering leadership, QA, product stakeholders
**Setup:** Terminal with the server repo checked out; test runner available

---

**Scene 1 — (Slide 1: Title) — 0:00–0:30**
Open with the title slide: "73-9: Locking Down the Rulebook — Test Hardening for Combat Feedback." No live demo yet. Introduce the context: "We spent the last week making combat actions readable to players. Today's story is about making sure that readout can never silently break."

---

**Scene 2 — (Slide 2: Problem) — 0:30–2:00**
Show the Problem slide. Narrate: "After 73-4, 73-7, and 73-8, the combat feedback engine knows how to describe a backfire, a setback, a clean exit. But the test suite only spot-checked the happy path. These six edge cases had no safety net." Walk through the six bullets on the slide (backfire fields, opponent setback, same-side overwrite, resolved-skip, UI null-guard, inert-summary text). No code needed here — the slide says it.

**Fallback:** If projector fails, read the six bullets aloud. They're self-explanatory.

---

**Scene 3 — (Slide 3: What We Built) — 2:00–4:30**
Transition to the terminal. Run the new test suite:

```bash
cd sidequest-server && uv run pytest tests/server/test_beat_impact.py tests/server/test_beat_impact_payload_wiring.py -v -n0
```

Expected output: `26 passed in 0.12s`. Point out: "These 26 tests now cover all six edge cases. Before this story, only ~19 of these ran — and several of those were weak 'something exists' checks."

Then run the UI tests:

```bash
cd sidequest-ui && npx vitest run src/__tests__/components/ConfrontationOverlay.beatimpact.coverage.test.tsx
```

Expected output: `3 passed`. "Three new component tests confirm the overlay handles a null player impact without crashing, and renders inert summaries legibly."

**Fallback (if test runner unavailable):** Switch to Slide 3 and show the Reviewer's verification summary: "26/26 server, 44/44 UI — Reviewer ran these independently."

---

**Scene 4 — (Slide 4: Why This Approach) — 4:30–5:30**
Return to slides. "Zero production code changed. The Reviewer confirmed this with a file-name diff — every changed file is a test file. That means zero regression surface. We added coverage without adding risk."

Point to the two replaced assertions: "We also replaced two 'is anything here?' checks with 'is *this specific value* here?' checks. That's the difference between a smoke detector that beeps when the battery dies versus one that actually smells smoke."

---

**Scene 5 — (Slide 5: Roadmap) — 5:30–7:00**
Hand off to the Roadmap slide and follow the section below.

---