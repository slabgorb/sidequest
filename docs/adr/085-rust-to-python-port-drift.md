# ADR-085: Tracker hygiene during the Rust→Python port — handling port-drift

**Status:** Accepted
**Date:** 2026-04-23
**Deciders:** Keith Avery (Bossmang), The Ministry of Silly Walks Official (Architect)
**Related:** ADR-082 (port `sidequest-api` from Rust back to Python)

## Context

ADR-082 ported the backend from Rust (`sidequest-api`) back to Python (`sidequest-server`). The port is a language-change at the bottom of the stack while the feature work above it continues at normal velocity. Epics in flight during the port (notably Epic 37 "Playtest 2 Fixes") accumulated stories that were *delivered* against the Rust tree before ADR-082 landed.

An audit of Epic 37 on 2026-04-23 surfaced a specific failure mode we call **port-drift**:

> A story is marked `done` in the sprint tracker because the Rust implementation shipped and passed review. The port to Python did not carry that implementation forward. The code that satisfied the acceptance criteria no longer exists in the live backend, but the tracker still shows `done`.

Concrete example from the audit: **37-36** (party-peer identity packet) is `done` in sprint YAML. The session archive shows Rust implementation + reviewer approval. The live Python `sidequest-server` has no `PartyPeer` type, no `inject_party_peers()` call, and no peer dossier injection into narrator prompts. The bug the story closed is back in production because the fix did not survive the port.

The opposite failure mode also occurs — **reverse port-drift**:

> A story is marked `backlog` because the Rust implementation never landed, but the Python port incidentally satisfies the acceptance criteria (either through a clean-slate rewrite of the subsystem or through adjacent port work).

Concrete examples: **37-29** (chargen standard-kit mismatch) and **37-44** (NPC identity drift) both still show `backlog` despite the Python port delivering the fix through story 37-23 (chargen dispatch port) and commit `afc2142` respectively.

Both failure modes come from the same root cause: the port moved forward and the tracker did not move with it.

## Decision

During the life of the port (from ADR-082 acceptance to the cutover commit when `sidequest-api` is decommissioned), sprint-tracker status reflects the **live Python backend**, not the Rust reference tree. Every story in flight during this window must be re-verified against the Python codebase before its status is trusted.

### Rules

1. **Status is code-backed, not archive-backed.** A story is `done` only if its acceptance criteria pass against `sidequest-server` (Python). Rust session archives are historical evidence, not proof of current state. If the archive says done and the code says no, the tracker is wrong.

2. **Port-drift is a bug, not a new story.** If a story was marked `done` against Rust and its fix did not survive the port, the correct action is to **re-open the same story**, not to file a fresh one. Preserve the original story number and history; add a "Port verification" section to the session file. This keeps the audit trail clean and prevents story-number inflation.

3. **Reverse port-drift closes the loop quietly.** If a Python port incidentally satisfies a backlog story's AC, mark the story `done` with a one-line note citing the delivering commit/story. No new story needed; no ceremony.

4. **Every in-flight epic gets an audit checkpoint at port cutover.** The cutover commit (when `sidequest-api` is deleted / archived read-only) triggers a mandatory audit pass on every epic that was open during the port window. Architect owns the audit; PM owns the tracker reconciliation.

5. **The Rust archive is a spec, not a contract.** Session archives from the Rust tree describe *what was built*. They are authoritative for design intent — the AC interpretations, the chosen approach, the OTEL span names — and non-authoritative for *current delivery*. Port stories may legitimately deviate from the Rust implementation when the Python idiom differs (e.g., the Rust OTEL span attribute that doesn't translate cleanly). These deviations must be logged per the standard deviation protocol; they are not port-drift.

### Scope — which stories are at risk

Port-drift risk is bounded to stories where:

- The story touches backend code paths owned by `sidequest-server` (dispatch, state, encounter, chargen, narrator, protocol, persistence, OTEL).
- The story was marked `done` or `verify` between 2026-03-30 (Rust port landed) and 2026-04-19 (ADR-082 accepted).
- The story's acceptance criteria assert on behavior observable from the running server (payload shape, state field presence, OTEL span emission, save-file content).

Stories that are **not at port-drift risk**:

- UI-only stories (`sidequest-ui` unaffected by ADR-082, per the port scope table).
- Content-only stories (`sidequest-content` YAML is language-agnostic).
- Daemon stories (`sidequest-daemon` out of scope per ADR-082).
- Tooling / sprint-infrastructure stories (`.pennyfarthing/`, `orc-quest` scripts).

### Audit procedure

When auditing an epic for port-drift:

1. **List all stories** in the epic, grouped by status.
2. **For each `done` story** on the backend slice: locate the implementation in `sidequest-server`. If the fix is absent, flag as port-drift and return the story to its pre-done status (typically `backlog`) with a session-file note.
3. **For each `backlog` story** on the backend slice: check whether the Python port's implementation happens to satisfy the AC (often it does — the porter reads the Rust code as spec and carries the fix forward). If yes, mark `done` with a one-line evidence note.
4. **For `in_progress` stories**: no port-drift possible (the story has not yet claimed completion). No action required.
5. **Bundle stories** with many sub-items need per-sub-item verdicts. Partial completion is common and must be tracked.

## Consequences

### Positive

- **The tracker stops lying.** `done` means done in the code the server actually runs. Sprint planning stops pulling from a distorted list.
- **Port velocity stays honest.** Reverse port-drift credits the porter when adjacent work fixes a backlog bug — this is frequent and deserves visibility.
- **Epic closure becomes possible.** Epic 37 cannot close while its stories' `done` status is not code-backed. The audit is the gate.

### Negative

- **Audits cost time.** One pass per epic at cutover is the commitment. This ADR makes the cost explicit and bounds it.
- **Story re-opens feel like regression.** A `done` story returning to `backlog` is emotionally heavier than it should be. Naming the failure mode (port-drift) removes stigma — the story wasn't "broken", the port didn't carry it forward.

### Risk accepted

- **Audit judgment calls.** The audit relies on Architect reading code and declaring AC satisfaction. This is subjective for fuzzy ACs (e.g., "the narrator no longer fabricates physical separation"). For those stories, a playtest confirmation at cutover is the true gate, not static code reading.

## Evidence — Epic 37 audit (2026-04-23)

Applied the above procedure to Epic 37 (48 stories, 23 backend-slice stories in the audit window).

**Reverse port-drift (backlog → done):**

| Story | Delivering work | Evidence |
|-------|----------------|----------|
| 37-29 | 37-23 chargen dispatch port | `sidequest/server/dispatch/chargen_loadout.py:89-144` |
| 37-44 | multiplayer foundation commit | `afc2142`; `sprint/archive/37-44-session.md` |

**Port-drift (done → re-open recommended):**

| Story | Missing in Python | Blocked follow-on |
|-------|-------------------|-------------------|
| 37-36 | `PartyPeer` type absent; no peer dossier injection | Blocks 37-37 |

**Partial bundles (some sub-items land incidentally):**

| Story | Done sub-items | Remaining |
|-------|----------------|-----------|
| 37-38 | `encounter.outcome` write-back, `NPC.last_seen_turn` update | `total_beats_fired` increment, scrapbook backfill, round-lag |
| 37-41 | `current_region` (via 37-31), NPC auto-registration (via 37-44) | 8 other sub-items |

## Exit — when this ADR retires

This ADR retires at **port cutover + 1 sprint**. At that point `sidequest-api` is archived read-only, the audit checkpoint has run on every open epic, and no story predates the all-Python state. Future stories are written against Python only; port-drift becomes a historical concept. The ADR can be marked Superseded or simply left as Accepted-but-inactive.
