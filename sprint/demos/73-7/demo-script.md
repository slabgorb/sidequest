**Setup before demo:** Have a running SideQuest instance with `space_opera` loaded. Start a `coyote_star`-style encounter with at least one active opponent. The confrontation overlay should be visible on screen.

---

**Scene 1 — The Problem (Slide 2: Problem)**
*Timing: ~60 seconds*

> "Here's the confusion Sebastien and Jade kept hitting."

Open the confrontation overlay in its pre-73-7 state (or show a screenshot). Walk the audience through a turn where the player executes a successful defensive beat — clean exit, no pressure gained. The overlay shows: `"clean exit"` and a `0` or blank where a number might appear.

> "The player did everything right. But the opponent just gained +2 pressure. The old overlay didn't show that. What Sebastien sees is 'my number didn't move' and concludes the game is broken."

Fallback: If live instance isn't available, show the Before screenshot from the slide deck.

---

**Scene 2 — The Fix (Slide 3: What We Built)**
*Timing: ~90 seconds*

Trigger another combat beat in the live session. Watch the Beat Impact Panel update.

Point to the panel and read it aloud:

> "You: clean exit · Them: +2 pressure"

Then scroll to the numeric readout section:
- Your delta: `0` (under `data-testid="beat-impact-own"`)
- Opponent delta: `+2` (under `data-testid="beat-impact-opponent"`)

> "Now Sebastien can see: I didn't move — and neither should I have. The enemy moved. The game is working. Two numbers, both sides, every beat."

Fallback: Show the After screenshot on Slide 3 showing both readouts populated.

---

**Scene 3 — Test Evidence (Slide 4: Why This Approach)**
*Timing: ~45 seconds*

```bash
cd /path/to/sidequest-server
uv run pytest tests/server/test_opponent_beat_impact_payload.py -v -n0
```

Expected: **6 passed** in ~0.12 seconds.

```bash
cd /path/to/sidequest-ui
npx vitest run src/components/__tests__/ConfrontationOverlay.opponentbeatimpact.test.tsx
```

Expected: **4 passed**.

> "Ten tests. Server-side proves the payload carries both sides. UI-side proves the panel renders both numbers. Zero engine changes — we verified the engine math didn't change by comparing directly to what the engine already stored."

Fallback: Show pre-captured terminal output on Slide 4 speaker notes screenshot.

---

**Scene 4 — What's Next (Roadmap slide)**
*Timing: ~30 seconds*

> "Right now the numbers are present and correct, but plain. 73-10 adds CSS styling — so advance shows green, setback shows red, and 'inert miss' looks different from 'nothing happened by design.' The data pipeline is done; the visual language comes next."

---