---
name: sq-wire-it
description: Wiring verification and debt tracker. Audit current wiring gaps, review historical wiring failures, and enforce the "no half-wired features" principle across all repos.
---

# sq-wire-it — Wiring Verification & Debt Tracker

<run>
You are the **Wiring Auditor**. Your job is to find code that exists but isn't connected — the most expensive class of bug in this project.

## Why This Exists

Wiring failures are this project's most costly defect category. The cost model:

| Stage | Multiplier | Example |
|-------|-----------|---------|
| Backspace | 1x | Caught while typing |
| Save | 10x | Caught by IDE / lint |
| Commit | 100x | Caught in code review |
| Push / PR | 10,000x | Caught by CI, reviewer, gate |
| Playtest discovery | 1,000,000x | Traced through OTEL, debugged across 4 repos |

The million-to-one ratio is **not** an exaggeration. It's worse here than in most projects because Claude (the narrator LLM) **compensates for missing mechanics by improvising**. The game looks like it works. Combat appears to happen. Items seem to be tracked. But the subsystems aren't engaged — Claude is just writing convincing fiction. The only lie detector is the OTEL dashboard, and if the subsystem isn't emitting spans, there's nothing to catch.

### The Historical Record

**Epic 7 — The Deferral Cascade (1,500 LOC dead code)**
Stories 7-1 through 7-5 each deferred wiring to story 7-9 ("the integration story"). Each deferral was individually reasonable. The wiring-check gate fired correctly every time. Every agent dismissed it by pointing at 7-9. Result: five fully-implemented, fully-tested modules with zero production consumers. ~1,500 lines of dead code.

**Session 5+6 Playtests — 15+ Wiring Bugs**
Post-playtest audit found 15+ cases where components worked in isolation but nothing connected them. TDD per-component created systematic gaps at integration seams. This directly spawned Epic 15's 16 wiring-debt stories.

**Story 15-4 — The Revert**
`PerceptionRewriter.rewrite()` was implemented, tested, reviewed, marked done. Then someone noticed it wasn't wired into `dispatch_player_action()`. The entire TDD cycle — RED, GREEN, REVIEW — wasted. Story reverted to ready.

**Story 9-4 — The Invisible Gap**
`register_knowledge_context` passed 21 tests. Reviewer caught that `PromptRegistry` itself might never be invoked with characters during a real turn. The method worked perfectly. It just wasn't called.

**Story 5-9 — classify_two_tier Dead Code**
Two-tier intent classification added but never called from `process_action()`. No HaikuClassifier implementation existed. The entire two-tier path shipped as dead code.

**Story 15-23 — WorldBuilder Unwired**
`materialize_world()` had full test coverage but zero call sites. Existed specifically because story 18-8 left WorldBuilder unwired. Dev had to add the server callsite at `lib.rs:2331`.

### The Five Failure Patterns

1. **Component-First TDD** — Build model, write tests, mark done. Integration "in another story." That story either never happens or discovers the model doesn't fit.

2. **Deferral Cascade** — One "defer to X-Y" creates three more. Each is individually reasonable. Collectively they produce dead code forests.

3. **Test-Passing Illusion** — All tests green, cargo builds clean, CI passes. But the function is only called from test files. Production code never touches it.

4. **OTEL Blind Spots** — Backend wiring "works" internally but isn't visible in the GM panel. "Is it wired?" means "can I see it in the dashboard?" — not "does the data flow exist internally."

5. **LLM Compensation** — Claude narrates around missing mechanics. Combat looks like it happens. Items seem tracked. The game appears to work. The subsystem was never engaged.

---

## Modes

### Quick Audit (`/sq-wire-it` or `/sq-wire-it audit`)

Scan for unwired exports across all repos:

1. **Find public exports with no non-test consumers:**
   ```bash
   # For each repo in sidequest-api, sidequest-ui, sidequest-daemon:
   # Find pub fn / pub struct / pub enum / pub trait definitions
   # Check each for non-test consumers
   ```

2. **Cross-reference with Epic 15 backlog:**
   ```bash
   pf sprint backlog | grep -i wire
   ```

3. **Check OTEL coverage:**
   Look for subsystems that have implementation but no `send_watcher_event()` calls.

4. **Report format:**
   ```
   ## Wiring Audit — {date}

   ### Unwired Exports (CRITICAL)
   - {export} in {file} — no non-test consumers

   ### Known Wiring Debt (Epic 15 backlog)
   - {story-id}: {title} — {status}

   ### OTEL Blind Spots
   - {subsystem} has no watcher events

   ### Summary
   - {N} unwired exports found
   - {M} wiring stories remain in backlog
   - {K} subsystems missing OTEL coverage
   ```

### Story Check (`/sq-wire-it check`)

Run against the current story's diff to verify wiring before handoff:

1. Read session file for story context
2. Run the wiring-check gate logic (see `gates/wiring-check.md`)
3. For every new `pub fn`, `pub struct`, `pub enum`, `pub trait`:
   - Find non-test consumers
   - If none exist: **FAIL** — wire it or rescope
4. For wiring stories (title contains "wire", "connect", "integrate"):
   - Verify ACs name a specific call site (file + function)
   - Verify that call site exists in the diff

### Debt Report (`/sq-wire-it debt`)

Full accounting of wiring debt across the project:

1. List all Epic 15 stories (15-7 through 15-22) with current status
2. Search other epics for wiring-related stories
3. Scan for `// TODO: wire` or `// FIXME: not wired` comments
4. Cross-reference with the five failure patterns above
5. Estimate total unwired surface area

### History (`/sq-wire-it history`)

Show the project's wiring failure timeline for retrospectives:

1. Git log filtered for wiring-related commits
2. Session archives documenting wiring gaps
3. Stories that were reverted due to incomplete wiring
4. Gate failures and how they were resolved

---

## Rules (Non-Negotiable)

These come directly from CLAUDE.md and the wiring-check gate:

- **No deferrals.** "Story X will wire this later" is not valid.
- **No half-wired features.** Connect the full pipeline or don't start.
- **5 connections = 5 connections.** Don't ship 3 and call it done.
- **Wired = visible in GM panel.** Internal data flow without OTEL spans is not wired.
- **Every test suite needs a wiring test.** Unit tests prove isolation. Wiring tests prove integration.
- **No silent fallbacks.** If something isn't where it should be, fail loudly.

## The Gate

The mechanical enforcement lives in `.pennyfarthing/gates/wiring-check.md`. This skill is the human-readable companion — the "why" behind the gate, the history that justifies zero tolerance, and the audit tools to find gaps the gate can't catch (like missing OTEL spans or subsystems Claude is silently compensating for).

</run>

<output>
Wiring verification with four modes:

- **audit** (default): Scan all repos for unwired public exports, cross-reference Epic 15 backlog, check OTEL coverage
- **check**: Verify current story's diff has no half-wired features (runs wiring-check gate logic)
- **debt**: Full accounting of wiring debt — Epic 15 stories, TODO comments, failure pattern analysis
- **history**: Timeline of wiring failures from git log, session archives, and reverted stories

Includes the project's wiring failure history (Epic 7 deferral cascade, 15+ playtest bugs, story reverts) and the five failure patterns that cause them.
</output>
