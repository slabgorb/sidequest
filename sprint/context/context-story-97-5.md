---
parent: context-epic-97.md
workflow: tdd
---

# Story 97-5: Turn-1 double-apply of _apply_npc_mentions — narrator.cache.both_writes_fired root cause

## Business Context

Measured on the blackthorn solo 2026-06-07 turn 1: two byte-identical disposition beats per NPC — two `_apply_npc_mentions` passes in one turn. Server #742 made it harmless at the development seam (`Npc.last_development_turn` dedupe), but the upstream double-apply is unexplained and presumably double-runs **every other per-mention side effect**: `last_seen` updates, pool matching, mint paths (a double-fired mint path on turn 1 is a plausible contributor to the open "Authored roster NPCs seeded TWICE" and double-mint families). It also distorts any interaction counting that 97-1's engagement threshold would key on. Cross-ref: the unfiled `narrator.cache.both_writes_fired` WARN on the ping-pong watch list — likely the same double-execution surfacing in a different subsystem. This is a root-cause story: find why the turn runs the seam twice, fix it at the source, then evaluate whether the seam-level dedupe is dead code (Delete Dead Code in the Same PR doctrine — but only if it's genuinely dead, see guardrails).

## Technical Guardrails

- **Measure, don't assert.** The repro is turn 1 specifically — that suggests the opening/establishing turn path and the normal turn path both invoke the apply, or a replay/re-entry shape (cf. `intent_router.replay_suppressed` dice-replay re-entry, story 91-2 — a known double-entry family). Instrument first: log/trace both call stacks on a reproduced turn-1 before proposing the fix.
- Seams: `_apply_npc_mentions` defined at `sidequest/server/narration_apply.py:1919`, production call site at :4196. Find ALL call paths into :4196's enclosing function (`websocket_session_handler._execute_narration_turn` is the known driver) — the double-apply is upstream of the function, not inside it (beats were byte-identical, same turn number).
- The dedupe seam: `narration_apply.py:2083-2115` + `Npc.last_development_turn` (`sidequest/game/session.py:217`, with the explanatory comment at :214). **Do not remove the dedupe in the same breath as the fix unless the second pass is provably gone in all shapes** (solo turn 1, MP turn 1, reconnect-replay, dice-replay re-entry). The comment at session.py:214 documents why it exists; if removed, the regression test that pins single-application must remain.
- `narrator.cache.both_writes_fired` — locate the WARN's emit site and understand what "both writes" means there; the AC requires it explained or eliminated. If it turns out to be a different defect, the AC is satisfied by the explanation + a separate filing, not by forcing it into this fix.
- Per-mention side effects to audit for double-run damage once the cause is found: `last_seen_location` (npc_agency.py:18 cross-ref), pool matching/`invented_from` alias leg (#738), Step-3 mint, the session_helpers.py:1481 parallel path. The fix should make ALL of them single-fire; the tests should pin at least mention-count and mint-count, not just disposition beats.

## Scope Boundaries

**In scope:**
- Root cause of the double `_apply_npc_mentions` pass on turn 1, fixed at the source
- `both_writes_fired` WARN explained (and eliminated if same cause)
- Regression test pinning exactly one apply pass per narration turn
- Decision (documented) on retiring vs keeping the `last_development_turn` seam dedupe

**Out of scope:**
- 97-1's pool projection (consumes the corrected counts; separate story)
- The open double-mint / roster-seeded-twice entries — unless the root cause turns out to be this same double-apply, in which case note it on those entries rather than expanding this story's tests to cover them
- Valence/development model changes (#742 territory, settled)

## AC Context

1. **"One narration turn produces exactly one _apply_npc_mentions pass (or the second pass is load-bearing and documented)"** — Test: integration-level, through the real `_execute_narration_turn` path (the 45-33 lesson: narrow dispatch-scoped tests miss bystander effects one directory up) — turn 1 of a fresh session applies mentions exactly once per NPC; assert on a side effect with no downstream dedupe (e.g. raw mention/interaction count or an emit counter), NOT on disposition beats (the dedupe would mask the regression). The escape hatch ("load-bearing and documented") exists because turn-1 might legitimately compose opening + first-turn passes — if so, the documentation must live in code comments at the call sites and the dedupe seam stays.
2. **"both_writes_fired WARN explained or eliminated"** — Test/evidence: if same root cause — the WARN no longer fires on a reproduced turn-1 (log assertion); if different — a written explanation in the session file + the WARN filed as its own entry. Either resolution must name the emit site.

## Assumptions

- The double-apply reproduces deterministically on turn 1 of a solo session (it did on blackthorn 2026-06-07). If it proves intermittent, this becomes a forensics-first story — do not guess (measure-don't-assert doctrine).
- #742's dedupe is in the baseline (merged, develop) — tests written here run against post-#742 behavior.
- Full-suite gate with `SIDEQUEST_GENRE_PACKS` + `SIDEQUEST_TEST_DATABASE_URL` set; the 2 known epic-96 baseline failures are the only acceptable reds.
