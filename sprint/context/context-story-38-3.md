---
parent: context-epic-38.md
workflow: tdd
---

# Story 38-3: TurnBarrier Confrontation-Scope Investigation

## Business Context

The dogfight subsystem needs TurnBarrier to run commit-and-reveal cycles WITHIN a
confrontation — each turn, both pilots commit secretly, then the barrier releases for
resolution. Epic 13 built TurnBarrier for session-wide sealed-letter turns. The question
is: can it handle confrontation-scoped cycles without breaking session-level accounting?

This is the riskiest unknown in the epic. If the barrier is already confrontation-safe,
this is a documentation + test story. If not, it's a targeted extension. Either way,
38-5 depends on the answer.

## Technical Guardrails

### CLAUDE.md Wiring Rules (MANDATORY)

1. **Verify Wiring, Not Just Existence.** Don't just confirm TurnBarrier has the right
   methods — verify it can actually be engaged at confrontation scope in a running session
   without corrupting session-level state.
2. **Every Test Suite Needs a Wiring Test.** Integration test proving barrier works at
   confrontation scope FROM the server crate.
3. **No Silent Fallbacks.** If the barrier silently swallows confrontation-scope commits
   into session-scope accounting, that's a silent fallback. Fail loudly.
4. **No Stubbing.** If the barrier needs a scope parameter, implement it. Don't leave a
   `// TODO: add scope` comment.
5. **Don't Reinvent — Wire Up What Exists.** The barrier EXISTS. Extend it if needed.
   Do NOT build a parallel "confrontation barrier."

### Key Files

| File | Action |
|------|--------|
| `sidequest-api/crates/sidequest-game/src/barrier.rs` | Investigate TurnBarrier implementation — can it scope to confrontation? |
| `sidequest-api/crates/sidequest-server/src/shared_session.rs` | Where TurnBarrier is attached — understand lifecycle |
| `sidequest-api/crates/sidequest-server/src/dispatch/` | Where confrontation resolution happens — where barrier would be consumed |

### Critical Investigation Questions

1. Does `TurnBarrier` track which actors have committed? Or does it count commits globally?
2. Can you `drain_actor_commits()` for a confrontation subset without draining session-level commits?
3. If a multiplayer session has a dogfight AND a separate sealed-letter turn happening simultaneously, do the barriers interfere?
4. Is the barrier reusable across multiple commit-reveal cycles within a single session, or is it one-shot?

### Dependencies

- None. Parallel with 38-1, 38-2, 38-4.
- 38-5 BLOCKS on this story's findings.

## Scope Boundaries

**In scope:**
- Investigation: read TurnBarrier code, understand scope model
- If barrier is confrontation-safe: document why, write tests proving it
- If barrier needs extension: add a scope parameter (confrontation ID or similar) that scopes commits to a specific confrontation
- Integration test: run a dogfight-style commit-reveal cycle using the barrier at confrontation scope
- Edge case test: concurrent session-level and confrontation-level barrier usage

**Out of scope:**
- Implementing the SealedLetterLookup handler (38-5)
- Multi-confrontation scenarios (two dogfights in one session simultaneously)
- Three-player dogfight barrier semantics

## AC Context

**AC1: Investigation documented**
- Clear written finding: "barrier is confrontation-safe" OR "barrier needs extension X"
- If extension needed: implementation complete with tests, not just a recommendation

**AC2: Confrontation-scope commit-reveal works**
- Test: create a TurnBarrier, simulate two actors committing maneuvers for a specific
  confrontation, drain commits, verify both commits returned correctly
- The commit must be attributable to a specific confrontation, not just "any pending commit"

**AC3: Session-level isolation**
- Test: session has both a dogfight confrontation and a normal sealed-letter turn in progress
- Dogfight barrier drains only dogfight commits
- Session barrier drains only session commits
- Neither corrupts the other

**AC4: Reusability across turns**
- Test: run 3 consecutive commit-reveal cycles on the same barrier
- Each cycle returns correct commits for that turn
- No stale state from previous turns leaks into current turn

**AC5: Wiring test**
- Integration test in `sidequest-server/tests/` proving the barrier can be acquired and
  used from the server's dispatch path — the same code path 38-5 will use

## Assumptions

- TurnBarrier exists in `sidequest-game/src/barrier.rs` (verify path)
- Epic 13 implemented TurnBarrier for sealed-letter turns (verify it's merged and working)
- The barrier's current API includes some form of `commit()` and `drain()` or `release()`
