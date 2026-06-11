# Simulated Player — `sidequest-understudy` (Design)

**Date:** 2026-06-11
**Author:** Architect (brainstormed with Keith)
**Status:** Approved design, pre-implementation
**Repos:** new repo `sidequest-understudy` (+ orchestrator justfile/docs wiring)

## Problem

A coherent multiplayer playtest currently requires one human to puppet every
seat. The existing headless driver (`scripts/playtest.py`) is a single-seat,
scripted-action instrument: bare WebSocket, canned action strings, `auto`
chargen. It can poke a mechanic but it cannot role-play, cannot fill the other
chairs of a four-player table, and — because it speaks the wire protocol
directly — it cannot tell us whether the *client surface* is legible to an
actual player.

## Decision summary

Build a new repo, **`sidequest-understudy`**: an autonomous, *naive*
player-client that joins a real SideQuest session through the **actual React
UI in a browser** and role-plays a seat. Launch N of them to fill a table; a
human occupies any remaining seat. Table composition (1 human + 3 bots, 0 + 4,
2 + 2) falls out of "each seat is an independent client" — no composition is
special-cased.

The nine decisions made during brainstorming:

| # | Question | Decision |
|---|----------|----------|
| 1 | Purpose | **Playtest instrument** (coverage, repeatability, OTEL legibility) — not a synthetic teammate |
| 2 | Human placement | **Configurable N** — counts fall out of per-seat independent clients |
| 3 | Action engine | **LLM-per-turn**, in persona, model-agnostic from day one |
| 4–5 | Protocol knowledge / surface | **Black-box client, "as naive as the user."** No server protocol imports, no bare-WebSocket mode. The bot lives in the real UI; headless = windowless browser, headed = visible window. Interface confusion is a *finding*, not a failure |
| 6 | Perception | **Accessibility tree as structured text** (screen-reader model). No pixels, no vision model — preserves model-agnosticism and local-model runs |
| 7 | Findings | **Subjective + objective, reconciled** — bot self-reports friction; harness records behavioral stuck-signals; report pairs them |
| 8 | Personas | **Play-style archetypes mirroring the real playgroup axes** |
| 9 | Output | **Standalone report artifact now; opt-in ping-pong emitter later** (deferred seam, designed not built) |

## The load-bearing principle: "as naive as the user"

The understudy is handed *only what a player is handed* — the rendered game
surface, read as a screen-reader reads it — and nothing privileged: no server
protocol models, no internal types, no pre-digested menu of valid actions. It
must **discover** the affordances. When it can't, that is the instrument
working: we are testing the legibility of the whole client surface through
fresh eyes.

Corollaries:

- **No bare-WebSocket mode.** A bare-WS bot reads raw JSON no human ever
  sees — *too knowledgeable*. The protocol is spoken by the real UI client.
- **The naivety invariant:** the only thing that ever reaches the brain is the
  rendered, semantic page. No pipeline step may inject privileged knowledge to
  "help it along." A helper that rescues a stuck bot has destroyed the
  measurement.
- Pure-UI acceptance is out of scope (handled elsewhere). This instrument
  tests **affordances**: can a naive intelligence find and use the controls
  and play a coherent turn?

## Component map

```
sidequest-understudy/            # Python 3.12, uv-managed, Typer CLI
├── persona/        # play-style archetypes (YAML) + seat seeding
├── perception/     # Playwright a11y-tree → faithful structured-text snapshot
├── brain/          # perceive→decide→act loop; model-agnostic LLM seam
│   └── llm/        #   backends: anthropic · claude_p · ollama
├── actuation/      # resolve bot's named target (role + accessible name) → click/type
├── findings/       # subjective report_confusion + objective stuck-detector + reconciler
├── report/         # run-report writer (transcript + findings + Jaeger OTEL spans)
├── orchestrate/    # session join, seat→archetype assignment, N-bot run, termination
└── pingpong/       # DEFERRED seam — opt-in CONFIRMED-finding emitter
```

Reuse: does **not** reuse `scripts/playtest.py`'s WS driver (rejected
paradigm); **does** reuse its Jaeger `narration.turn` span-pull logic for the
report. Dependencies: Playwright, httpx, pydantic v2, Typer.

## Per-turn brain loop

1. **Perceive — faithfully, not helpfully.** `perception/` renders
   Playwright's accessibility snapshot to compact structured text: roles,
   accessible names, text regions, editable fields, enabled/disabled state.
   The tree is presented **as it actually is**, including ambiguous or
   unlabeled nodes. No post-processing into a clean menu of clickables —
   spoon-feeding affordances would delete the affordance test.

2. **Decide — the LLM, in character.** One LLM call. System prompt = seat
   archetype + game-agnostic framing ("You are a player at a table. Here is
   what's on your screen. What do you do?"). Returns a **typed intent**:
   - `act` — target described *by accessible name/role* the way a player
     would refer to it ("the Send button"), plus optional text to type
   - `report_confusion` — a reason, verbatim
   - `wait` — believes it's not its turn

3. **Act — resolve, then do.** `actuation/` resolves the named target against
   the live a11y tree to a Playwright locator (role + accessible name,
   fuzzy). Three outcomes, all meaningful:
   - clean resolve → click/fill, wait for settle (new narration / turn state)
   - ambiguous resolve → logged as objective friction
   - **failed resolve** → strong objective signal: the bot's mental model of
     the affordances diverged from reality. This is the gold.

4. **Observe.** `findings/` watches behavioral friction with zero LLM
   judgment: resolution failures, same-action repeats (N×), submit timeouts
   (barrier never released), console/JS errors, dead-end loops, no actionable
   element found. Every turn appends a transcript row:
   `perceived snapshot → intent → resolution outcome → resulting narration`.

## Personas: the playgroup as test matrix

Archetypes are YAML data, not code. Structured axes feed the loop
**mechanically**, not just as prose:

- `verbosity` caps action length (enforces the "playtest actions stay short"
  rule)
- `decisiveness` sets how readily the bot chooses `wait` over `act`
- `reading_tolerance` governs how much narration history replays into the
  context window each turn (also the token-cost knob for local models)
- `affordance_hunger` + `narrative_vs_mechanical` steer attention
- `prompt_fragment` carries the in-character voice

The archetype shapes **behavior and attention, not knowledge** — a
`mechanics_first` bot doesn't know the dice tray exists; it *wants* it to and
goes looking. "Looked and couldn't find" is the per-user-type finding this
exists to produce.

Starting set of four, mapped to the real table:

| Archetype | Models | Stress-tests |
|---|---|---|
| `narrative_first` | James | prose-only inputs; ignores mechanical chrome |
| `mechanics_first` | Sebastien/Jade | hunts dice/HP/ability math — are mechanical affordances findable? |
| `hesitant` | Alex | slow, short, waits when unsure — does the barrier hold? does the UI orient a slow player? |
| `engaged_generalist` | Keith/Jade | both axes, high reading — baseline competent player |

Run manifest assigns archetypes to seats:

```yaml
# runs/four_seat_wasteland.yaml
genre: mutant_wasteland
world: flickering_reach
seats:
  - human            # Keith drives seat 1; omit for fully autonomous
  - mechanics_first
  - narrative_first
  - hesitant
turns: 12            # bot turns before graceful exit
```

## Findings: reconcile, report, opt-in loop

Two streams per run:

- **Subjective** — `report_confusion` intents, verbatim, with the perceived
  snapshot attached.
- **Objective** — the stuck-detector's behavioral signals.

The **reconciler** joins them by turn-window and grades every finding:

| Grade | Meaning |
|---|---|
| **CONFIRMED** | both streams agree (bot complained + harness saw friction same turn-window) |
| **BEHAVIORAL** | objective only — bot muddled through without complaining |
| **CLAIMED** | subjective only — complaint with clean behavior (wolf-cry candidate; kept, down-ranked) |

**Report artifact** — one self-contained directory per run:

```
reports/2026-06-11-four_seat_wasteland-r1/
├── report.md          # run summary, findings table by grade, per-seat archetype outcomes
├── findings.json      # machine-readable graded findings (the ping-pong seam reads this)
├── transcript/        # per-seat per-turn: a11y snapshot → intent → resolution → narration
└── spans.jsonl        # server-side narration.turn OTEL spans pulled from Jaeger
```

The spans close the triangle: bot said X, harness saw Y, server's mechanical
record says Z. CONFIRMED finding + spans showing the engine fired correctly =
pure UI-legibility bug. Spans silent = engine bug wearing a UI costume.

**Ping-pong emitter (deferred — seam designed, not built):** a separate
command, `understudy emit-pingpong <report-dir>`, reads `findings.json`,
filters to **CONFIRMED only**, appends to the existing ping-pong file in the
FIXER's format. Never automatic, never CLAIMED-grade noise. The core run has
zero knowledge of ping-pong; the emitter is a consumer of the report.

## Orchestration, model seam, guards

**Session join & chargen.** One Playwright instance, N isolated browser
contexts (one per bot seat), each pointed at the session URL like any player.
Chargen is **played naively too** — it is one of the most affordance-dense
surfaces in the game. (`--fast-chargen` reusing the server's auto-strategy is
deferred, not built now.)

**Model seam.**

```python
class ActionModel(Protocol):
    async def decide(self, system: str, transcript: list[Message]) -> Intent: ...
```

Backends at launch: **anthropic** (SDK, Haiku default), **claude_p**
(subprocess), **ollama** (local HTTP). Per-seat configurable in the manifest
(`model: ollama/qwen3:8b`) — a four-bot run can be all-local and cost zero.
Structured `Intent` via each backend's native JSON/tool path; a malformed
response counts as an objective friction signal, down-weighted (model failure,
not UI failure) but logged so flaky-model noise stays distinguishable from
real findings.

**Cost & termination guards** (ADR-134's lesson, applied client-side):

- Hard turn cap from the manifest — no unbounded runs
- Per-run token ledger for API backends with a configurable ceiling; breach =
  graceful stop + partial report
- Wall-clock cap + per-turn decide-timeout — a stalled barrier or dead model
  ends in a reported timeout finding, not a hung process
- Graceful exit: bot stops acting, report written, browser contexts closed;
  the session itself is left alone (server-owned)

## Testing the tester

- Unit: perception rendering (recorded a11y snapshots → expected structured
  text), reconciler (synthetic streams → expected grades), target resolution
  (fixture DOM → locator outcomes)
- **Wiring test** (house rule): a scripted `FakeActionModel` (no LLM) drives a
  real headless browser against a real dev server through the full
  perceive→decide→act→observe loop — end-to-end wiring proven without burning
  tokens
- The naive-LLM lane is exercised by running it; that *is* the product

## CLI & orchestrator wiring

- `understudy run <manifest>` — execute a run (`--headed` to watch)
- `understudy emit-pingpong <report-dir>` — deferred
- Orchestrator: `just understudy <manifest>` recipe; repo registered in
  `repos.yaml` when created

## Out of scope

- Synthetic-teammate quality (decision 1: instrument, not teammate)
- Pixel/vision perception (re-introduces vision-model dependency; possible
  future mode-flagged skin)
- Bare-WebSocket driving (violates naivety; `scripts/playtest.py` remains for
  mechanic-poking)
- Automatic ping-pong filing (opt-in emitter only, and deferred)
- Sheer UI acceptance testing (handled by other means)
