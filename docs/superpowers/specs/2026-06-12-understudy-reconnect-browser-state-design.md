# Understudy Reconnect via Persisted Browser State — Design

**Date:** 2026-06-12
**Status:** Design (approved, pre-plan)
**Repo:** `sidequest-understudy`
**Related:** `docs/superpowers/specs/completed/2026-06-11-simulated-player-understudy-design.md`

## Problem

An understudy run spends most of its turn budget in character creation. Chargen
alone costs ~12 perceive→decide→act cycles per seat, so a 40–50 turn run barely
reaches real play — exactly the part we want to observe. Each seat uses a fresh
`browser.new_context()` every run, discarding the localStorage a returning
player's browser would keep, so every run re-runs chargen from scratch.

## Goal

Let seats **reconnect** to a session they already created and skip chargen, so
the turn budget goes to play. Stay faithful to the naive black-box client: the
harness should re-acquire identity the same way a real returning player's
browser does — no special "claim character X" logic, no server changes.

Non-goals: server-side session seeding, a fixture/scenario fast-path, auth
identity, cross-day session guarantees.

## Mechanism

The lobby already persists, in localStorage on `localhost:5173`, everything a
returning player needs:

- `sidequest-history` — the one-click-resume list of `(player_name, slug)`
  (`src/screens/lobby/historyStore.ts`).
- `sq:display-name` — the persisted display name.

Playwright's `storage_state` captures a context's localStorage + cookies. So:

1. **Save (automatic, every run).** After a seat's loop ends, snapshot its
   context's `storage_state()` to `<report-dir>/state/seat-{idx}.json`.
2. **Restore (`--reconnect <DIR>`).** For each bot seat `idx`, build its context
   with `new_context(storage_state="<DIR>/state/seat-{idx}.json")`, then the
   normal `goto(session_url)` (the **lobby**, unchanged). The restored history
   surfaces the seat's resume entry; the bot clicks it naively and rejoins its
   character past chargen.

The bot is never told it is reconnecting. It perceives a lobby that happens to
offer a resume button and acts on it — identical to a human reopening the tab.

## CLI / Manifest Surface

One new flag on `understudy run`:

```
--reconnect <DIR>   Restore each bot seat's browser state from <DIR>/state/
                    seat-{idx}.json before it joins. <DIR> is a prior run's
                    report directory.
```

Saving is automatic and unflagged — every run leaves a reusable snapshot under
its own report dir.

Workflow:

```
just understudy four_seat_demo                              # run 1: chargen + play; writes state/
just understudy four_seat_demo --reconnect reports/<run1>  # run 2: resume, skip chargen
```

Run 2 also writes its own `state/`, so reconnect chains run-to-run.

## Seat → State Mapping

Mapping is by **seat index**: `state/seat-{idx}.json` restores into the seat at
position `idx`. The reconnect run MUST declare the same seat order and count as
the seed run (same manifest is the normal case). This is validated, not assumed
(see Failure Modes).

## Architecture / Touchpoints

All in `sidequest-understudy`:

- **`orchestrate/run.py`** — `run_table()` gains a `reconnect: Path | None`
  parameter.
  - When building each bot seat's context, pass
    `storage_state=<reconnect>/state/seat-{idx}.json` if `reconnect` is set.
  - Keep the `context` handle alongside each `SeatRunner` (today it is created
    inline and dropped) so we can call `storage_state()` after `run()`.
  - After `asyncio.gather(...)`, before `browser.close()`, write each seat's
    `storage_state(path=<out>/state/seat-{idx}.json)`. `out` is the per-run
    report dir; this requires resolving the report dir before the report is
    written, or saving state in a known location and having `write_report`
    place it. Simplest: compute the run's output dir up front and write state
    into it; `write_report` already targets that dir.
- **`cli.py`** — add `--reconnect <Path>` option, thread to `run_table`.
- **State path helper** — a single function `seat_state_path(dir, idx) -> Path`
  used by both save and restore, so the convention lives in one place.

No changes to `seat.py` (the perceive/decide/act loop is identity-agnostic), the
brain backends, the server, or the UI.

## Failure Modes (fail loud — No Silent Fallbacks)

- `--reconnect <DIR>` where `<DIR>` does not exist, has no `state/`, or is
  missing `seat-{idx}.json` for any **bot** seat → raise a clear error and exit
  non-zero (manifest/usage error class, exit 2) before launching browsers. Never
  silently fall through to chargen.
- Human seats have no state file and are skipped on both save and restore.
- If the resume entry does not appear at runtime (stale/dead session, server
  restarted, different day so the stored slug no longer loads), the bot naively
  falls into chargen or reports confusion. That is a legitimate finding, not an
  error the harness suppresses or forces around.

## Caveat (documented, not fixed)

The resume entry targets the stored `slug` (`{date}-{world}-mp`). Same-day
reconnect hits the live `-mp` session cleanly. Reconnecting on a later day
targets an older slug; sessions are Postgres-persisted (ADR-115) so it often
still loads, but it is best-effort. Reconnect is designed for the
iterate-on-play loop within a session's life, not long-term replay.

## Testing

1. **State path resolution** — `seat_state_path(dir, idx)` returns
   `<dir>/state/seat-{idx}.json` for representative idx values.
2. **Reconnect validation fails loud** — `run_table(reconnect=<dir missing a
   seat file>)` raises/exits non-zero before browser launch; the error names the
   missing seat.
3. **Restore wiring** — with the existing injection seams (a Playwright fake +
   `model_factory`), assert `new_context` receives `storage_state` pointing at
   the per-seat file when `reconnect` is set, and receives no `storage_state`
   when it is not.
4. **Save wiring** — after a run, `state/seat-{idx}.json` exists for each bot
   seat (and none for human seats).

The Playwright fake mirrors whatever the existing `run_table` wiring test uses;
no real browser in unit tests.

## Out of Scope / YAGNI

- `--reconnect-latest` auto-discovery (use `ls -dt reports/`).
- `--no-save-state` opt-out (saving is cheap; always on).
- Server-side seeding / scenario fast-path.
- Re-mapping seats across differing manifests.
