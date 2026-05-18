# Save Forensics Page — Design Spec

**Date:** 2026-05-18
**Author:** Architect (The White Queen) + Keith
**Status:** Approved for planning
**Repo:** `sidequest-server` (branch off `develop`, `feat/*`)
**Audience:** Keith (dev/diagnostic tool — *not* a player-facing feature; sibling of the GM/OTEL dashboard)

---

## 1. Problem

When a SideQuest session goes wrong (a narrator miss, a mechanical no-show, a
suspicious state value), the only reconstruction method today is opening the
SQLite save by hand and reading `narrative_log` / `events` rows in a sqlite
CLI. That works but is slow, lossy, and forgets the per-player perception
firewall entirely.

We want a **read-only, after-the-fact "autopsy table"**: pick a save, scrub a
turn timeline, and drill into exactly what happened that turn — narrative,
mechanical events, derived state changes, and what each player was *allowed to
see*.

This is the post-mortem counterpart to the live OTEL dashboard. The dashboard
answers "what is happening now"; this page answers "what already happened."

## 2. Goals / Non-Goals

**Goals**
- Browse all local saves and open one for inspection.
- A turn timeline (round-keyed) as the navigational spine.
- Per-turn drill-down: narrative, raw event stream, derived state deltas,
  per-player projection lens, scrapbook.
- Honest truth-tiering: stored vs. derived vs. absent, never blended.
- Mirror the proven `dashboard.py` delivery pattern (self-contained static
  HTML + a thin `FileResponse` route). No React, no build step.

**Non-Goals**
- No save editing or repair (read-only; respects the save-clobber hazard).
- No OTEL/Jaeger span correlation (separate ephemeral store; possible later).
- No new tab inside the live dashboard (explicitly rejected — see §8 C).
- No per-turn *absolute* state reconstruction beyond what events carry.

## 3. Background — what a save actually contains

Saves are SQLite DBs at `~/.sidequest/saves/games/<slug>/save.db`. Relevant
tables (from `sidequest/game/persistence.py`):

| Table | Shape | Role here |
|---|---|---|
| `session_meta` | singleton: genre/world/created/last_played | save header |
| `game_state` | singleton: one `snapshot_json` + `saved_at` | **only stored absolute state — the final snapshot** |
| `narrative_log` | append-only: `round_number`, `author`, `content`, `tags`, `created_at` | the narrative tape |
| `events` | append-only: `seq`, `kind`, `payload_json`, `created_at` | **authoritative replayable mutation log** |
| `projection_cache` | per `(event_seq, player_id)`: `include`, `payload_json` | what each player was allowed to see (ADR-104/105 firewall) |
| `scrapbook_entries` | per `turn_id`: scene/image/world_facts/npcs | per-turn scene cards |

**Load-bearing fact:** there is *no* per-turn state snapshot history — only a
single current `game_state` snapshot. Per `game/event_log.py`:

> "Every narrator-originated mutation (NARRATION, STATE_UPDATE, COMBAT_EVENT,
> etc.) is appended here before fan-out. Peers catch up on reconnect via
> read_since."

So `events` *is* an authoritative event-sourced log: the exact stream a
reconnecting peer folds to rebuild state. Reconstructing "what changed by turn
N" by folding events ≤ N is the **same fold the system already trusts for
catch-up** — not fabrication. The only honesty constraint: the fold can only
surface what events explicitly carry (see §6).

## 4. Architecture & placement

- **Route:** `GET /forensics` → `FileResponse(static/forensics.html)`. A
  four-line sibling of `sidequest/server/dashboard.py`, registered in
  `app.py` next to `dashboard_router`.
- **Page:** `sidequest/server/static/forensics.html` — self-contained
  HTML/CSS/JS, borrowing the dashboard's CSS for visual kinship. Talks to the
  REST endpoints below via `fetch` (no WebSocket — this is offline data).
- **Separate page, not a dashboard tab.** The dashboard is live (`/ws/watcher`,
  in-flight session); forensics is offline post-mortem over plain REST. Keeping
  them separate avoids destabilizing the live GM panel and keeps the two
  time-directions mentally distinct.

## 5. Data layer

New read-only REST endpoints, siblings of `/api/debug/state` in
`sidequest/server/rest.py`:

| Endpoint | Returns |
|---|---|
| `GET /api/debug/saves` | `[{slug, genre, world, created_at, last_played, last_activity_ts}]`, newest-first by save mtime. Reuses the `/api/debug/state` enumeration walk over `<save_dir>/games/<slug>/save.db`. Broken/empty DBs skipped (logged at WARNING, never silently). |
| `GET /api/debug/save/{slug}/timeline` | Ordered list of turns: `[{round, seq_start, seq_end, event_kind_counts, narrative_authors, ts}]` |
| `GET /api/debug/save/{slug}/turn/{round}` | Drill-down bundle for one round (§7) |

**Fold module:** new pure module `sidequest/game/forensic_fold.py`, built on
the *existing* `EventLog.read_since(since_seq=0)` primitive (no new read
mechanism). It walks events in `seq` order and accumulates `STATE_UPDATE`
JSON-patch payloads (ADR-011 patch shape) into a running derived-delta map,
recording for each derived field the set of source event `seq`s that touched
it. Pure function: `(events: list[EventRow]) -> FoldResult`. No DB writes ever.

**Save access:** open each `save.db` read-only via `SqliteStore.open` and
**never checkpoint or write** — respects the WAL/clobber hazard. The forensic
path is strictly read-only.

## 6. The honesty contract (load-bearing)

Three visually distinct truth-tiers, **never blended** in the UI:

- **Stored** — `events` rows, `narrative_log` rows, the final `game_state`
  snapshot. Rendered verbatim from the DB.
- **Derived** — folded state deltas. Badged `derived — not a stored
  snapshot`, with a hover/expander naming the source event `seq`s. Only
  fields that events explicitly carried. Never presented as absolute state.
- **Absent** — a field no event ever touched is rendered as `— (no event
  mutated this)`, **not** as `0`/`null`/a default. No silent fallback, no
  invented value. (Per CLAUDE.md "No Silent Fallbacks" + SOUL OTEL/lie-detector
  doctrine.)

A malformed/un-parseable event payload is **skipped loudly** — logged at
WARNING with its `seq`, surfaced in the drill-down as a visible "unparseable
event @ seq N" marker. Never dropped silently.

## 7. Timeline spine + drill-down

**Spine:** a turn scrubber; each tick is one narrative round, correlated to
its event `seq`-range. The seq↔round join key is resolved by the §9 spike
(R1): either events carry `round_number` in payload, or events bucket by
`created_at` between consecutive `narrative_log` rows. Either way the timeline
is honest; the second is slightly coarser.

**Drill-down panels for the selected turn:**
1. **Narrative** — `narrative_log` rows for that round (author/content/tags).
2. **Event stream** — raw `events` rows in the seq-range (seq · kind ·
   pretty-printed `payload_json`). *Primary truth, verbatim.*
3. **Derived deltas** — accumulated state changes events carried *through*
   this turn, badged `derived` (§6), each delta expandable to its source seqs.
4. **Per-player lens** — `projection_cache` rows for this turn's events: for
   each `player_id`, which events had `include=1` vs `0`, and the projected
   `payload_json` they actually received. Surfaces the ADR-104/105 perception
   firewall — the highest-value forensic panel for MP misbehavior.
5. **Scrapbook** — `scrapbook_entries` for the turn (scene title/type,
   location, image_url, narrative_excerpt, world_facts, npcs_present,
   render_status).

**Final snapshot panel** (turn-independent): the one real stored `game_state`
snapshot, fetched via existing `GET /api/debug/state?session_key={slug}`.
Explicitly labelled *the only stored absolute state*.

## 8. Alternatives considered

- **A — honest event-sourced replay (chosen).** Fold the trusted event log;
  truth-tiered presentation. Highest forensic power without fabrication.
- **B — stream browser, no replay.** Navigable `narrative_log` + raw `events`
  + final snapshot, zero folding. Lower power (can't show mid-session change);
  rejected as the *primary* design but its skeleton is shared with A.
- **C — new tab in the live dashboard.** Rejected: couples offline
  post-mortem to the live-websocket page, blends "now" with "already
  happened," risks destabilizing the live GM panel by editing its file.

## 9. Risks

- **R1 — seq↔round correlation (only real unknown).** Plan task 1 is a spike
  that confirms the join key before any UI work. Fallback (timestamp bucketing)
  is honest if events lack round identity.
- **R2 — `STATE_UPDATE` payload completeness.** The fold reconstructs only
  what flows through events. The §6 honesty contract makes this a feature
  (absent ≠ zero), not a defect. Accepted.
- **R3 — reading a save while its session is live.** Read-only
  `sqlite3.connect` over WAL is safe; we open read-only and never checkpoint.
  Accepted.

## 10. Testing & wiring

- **Fold unit tests** (`forensic_fold.py`): event list → `FoldResult`;
  patch-ordering correctness; source-seq attribution; a malformed-payload row
  asserted to be skipped *loudly* (logged + marker), not silently dropped.
- **Endpoint tests:** `/api/debug/saves`, `.../timeline`,
  `.../turn/{round}` against a real save fixture; broken-DB skip path;
  unknown-slug → empty/sane response (mirrors `/api/debug/state` lossy
  contract).
- **Wiring test (mandatory, per CLAUDE.md):** drive the FastAPI app and assert
  `GET /forensics` returns the HTML *and* the three `/api/debug/save/*` routes
  resolve through the registered router — proving `app.py` wires the new
  router, not merely that the module imports.
- **OTEL:** read-only forensic reads mutate no subsystem; per the doctrine's
  read-only/cosmetic carve-out, no new spans required.

## 11. Out of scope (future)

- OTEL/Jaeger span correlation per turn (the live lie-detector overlaid on the
  post-mortem) — separate ephemeral store; a clean phase 2.
- Save editing/repair mode.
- Cross-save diffing (compare two saves of the same world).
