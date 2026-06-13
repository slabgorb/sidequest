---
parent: 106
---

# Story 106-3 Context

## Title
WWN-gate native combat mechanics ungated by the RulesetModule (ADR-117) — convert
the native edge/tag bleed (edge dial, Counter Stance fleeting tag, to-their-edge
chip) into a STRONG (~-3) next-round opponent penalty expressed in WWN terms (Keith
ruling); and gate native per-tick + chargen-seed XP (135 at L1) so XP follows the
WWN small-integer expedition-XP scale.

## Metadata
- **Story ID:** 106-3
- **Type:** bug
- **Points:** 5
- **Priority:** p1
- **Workflow:** tdd
- **Repo:** server
- **Epic:** 106 — WWN combat hardening for beneath_sunden (fair ramp, ruleset-bleed
  remediation, narration truth)

## Business Context

This story is the **ruleset-bleed thread** of Epic 106, surfaced by the 2026-06-13
single-player combat playtest of `caverns_and_claudes/beneath_sunden` (WWN ruleset,
ADR-117) — OTEL + save-forensics confirmed (`sq-playtest-pingpong.md`, 2026-06-13).
The core combat loop is VERIFIED healthy (Strike ablates HP, reprisal telemetry
splits, beat-impact chip reads the HP channel, lethality/death resolution correct —
pingpong lines 85–98). What this story fixes is two **native mechanics running
ungated inside a WWN-bound world** — the same root cause (ADR-117 RulesetModule does
not override / gate the native confrontation + progression mechanics), so both are
fixed at one architectural locus.

The primary audience is **Keith-as-player** plus the **mechanics-first players
(Sebastien, Jade)** who carried a 140-turn `coyote_star` session on narrative *while
missing the crunch*. When a WWN world shows them a native-engine "edge" dial, a
"Counter Stance" fleeting tag, or a Warrior sitting at **135 XP at level 1**, that is
exactly the kind of mechanically-incoherent surface a career GM and a numbers-first
player will catch instantly. WWN-bound mechanical values must come from the WWN SRD
(standing ruling, `.pennyfarthing/sidecars/gm-decisions.md`, 2026-06-13;
`memory/defer-to-srd-for-mechanics.md`). Both sub-bugs already carry **explicit Keith
rulings** (recorded verbatim below); this story implements them, it does not redesign
them.

### Two sub-problems, one fix locus

| # | Bleed | Source | Keith ruling |
|---|-------|--------|--------------|
| A | **Edge / tag bleed** — the native confrontation edge dial, the "Counter Stance" fleeting tag, and the "to their edge" chip text surface in the WWN chase/combat | pingpong **256–274** ([BUG] native edge/tag bleeds into WWN chase) | Do NOT remove the beats. CONVERT the edge/tag grant into a **next-round penalty to the opponent, in WWN terms**, and it MUST be **STRONG (~-3, "something fierce")** — the old edge was *permanent*, so a weak transient penalty would not be worth the beat. The native edge dial / "Counter Stance" / "to their edge" chip text must **no longer surface under WWN**. |
| B | **XP bleed** — native per-tick advancement (ADR-021 four-track) ticks inside a WWN world; Warrior shows **135 XP at L1**, with TWO faces: a non-zero chargen SEED (10 XP at turn 0) AND a per-turn tick (reaches 135) | pingpong **92–103** ([BUG] native per-tick XP bleeds into WWN) | XP must follow the **WWN small-integer expedition/goal-based scale** (L2 ≈ 3, L3 ≈ 6 — WWN SRD), NOT native per-kill / continuous accrual. **Kill BOTH faces** under a WWN binding: the chargen seed AND the per-tick. WWN-bound values come from the WWN SRD. |

The shared architectural fact: **ADR-117's `RulesetModule` (`game/ruleset/base.py`)
is the seam that owns turn resolution, but it currently has no authority over (a) how
a beat's edge/tag grant is expressed, nor (b) progression/XP at all.** Both native
mechanics run *around* the bound module. The fix is to route both through the module
so WWN can override them — "wire up the seam that exists" (ADR-117), not invent a new
subsystem.

## Technical Guardrails

### The fix locus is the RulesetModule seam (ADR-117) — gate, don't delete

`RulesetModule` (`sidequest-server/sidequest/game/ruleset/base.py`) is the per-session
authority for turn resolution. `WwnRulesetModule`
(`sidequest-server/sidequest/game/ruleset/wwn.py:51`) subclasses
`SwnRulesetModule` (`ruleset/swn.py`), which today **delegates `apply_beat`
verbatim to the shared native engine** (`swn.py:216-227` →
`beat_kinds.apply_beat`; native does the same at `native.py:56-65`). That delegation
is the bleed: WWN inherits the native edge/tag grant table unchanged.

#### Sub-problem A — edge/tag bleed seams (confirmed at the cited lines)

- `beat_kinds.py:171` — `compute_beat_impact` favorable branch emits the
  **"{opponent} to their edge"** chip text (`detail.append(f"{opponent} to their
  edge")`). Confirmed present.
- `beat_kinds.py:236` — `DEFAULT_DELTAS[BeatKind.brace][CritSuccess]` grants the
  **"Counter Stance"** fleeting tag plus `opponent_expr: "-b"` (the edge penalty).
  Confirmed present.
- `beat_kinds.py:250` — `DEFAULT_DELTAS[BeatKind.angle][Success]` is the
  `grants_tag_from_target` / `tag_leverage` (angle) grant path. Confirmed present.
- Under `hp_depletion` the engine **already suppresses the dial deltas** (zeroes
  `own`/`opponent`, `beat_kinds.py:142-146`) — so the *numbers* are held — but the
  **fleeting-tag grant ("Counter Stance") and the favorable/edge chip branch still
  surface** because suppression only zeroes the dial, it does not strip the tag or the
  edge-phrased chip. That is precisely the bleed the player saw.

The WWN fix (per Keith): instead of the native edge/tag grant, the WWN module must
**translate a favorable brace/angle CritSuccess|Success outcome into a STRONG (~-3)
next-round opponent penalty in WWN terms** (a to-hit / modifier penalty the WWN
attack/save resolution already understands — see `WwnRulesetModule.save_params`
`wwn.py:60` and the inherited SWN `attack_params`), and the chip must read the **real
WWN chase-dial advance**, not "to their edge"/"Counter Stance". The cleanest seam is a
WWN override of `apply_beat` (or a ruleset hook the engine consults for *how an edge
grant is expressed*) so the override is WWN-local and **cannot regress native or
SWN/CWN** (mirror the `wwn.py` "COPIED not hoisted" discipline, `wwn.py:5-8`).

**Magnitude is load-bearing.** Keith: it MUST be strong (~-3, "something fierce")
because the native edge it replaces was *permanent*; a weak transient penalty is not
worth spending the beat on. Do not soften this to -1.

#### Sub-problem B — XP bleed seams (confirmed)

- `award_turn_xp` (`server/dispatch/encounter_lifecycle.py:1485-1533`) grants the
  per-turn tick: **25 XP in combat, 10 otherwise**, party-wide, every turn,
  `c.core.xp = c.core.xp + delta` (line 1520).
- `apply_level_ups` (`encounter_lifecycle.py:1545+`) consumes accumulated `core.xp`
  via `_XP_PER_MILESTONE = 100` (line 1542) → milestone → level.
- **Both are called unconditionally in the turn pipeline** —
  `server/websocket_session_handler.py:1419-1422` calls `award_turn_xp(...)` then
  `apply_level_ups(...)` with **no consultation of the bound ruleset**. That is the
  ungated seam.
- The "**chargen seed of 10 XP at turn 0**" is NOT a literal seed in chargen — the
  builder sets `xp=0` (`builder.py:2920`; `creature_core.py:116` defaults `xp: int =
  0`; all materialization paths set `xp=0`). The 10-at-turn-0 the operator saw is
  **`award_turn_xp`'s calm branch (delta=10) firing on the opening turn**. Killing the
  per-tick under WWN therefore also kills the "seed". Verify this against a fresh-turn
  snapshot during RED; if a separate literal seed is found, kill that too — the AC is
  "0 or small-int, never 135 and never the 10".
- `RulesetModule` (`base.py`) has **no XP / advancement method at all** — there is no
  hook to override. The fix adds an XP/advancement authority to the seam (e.g. a
  ruleset method that decides whether/how a turn awards XP and how XP maps to levels),
  with **native** keeping today's per-tick behavior (no regression to non-WWN packs)
  and **WWN** declaring the **small-integer expedition/goal scale** (no per-turn tick;
  XP only on a real WWN expedition/goal award). The unconditional call sites at
  `websocket_session_handler.py:1419-1422` must route through that authority instead
  of calling the native functions directly.

### OTEL is the gate (CLAUDE.md OTEL Observability Principle)

`award_turn_xp` already emits a `state_transition` watcher event tagged
`component=progression` (`encounter_lifecycle.py:1521-1532`); `apply_level_ups` emits
`progression.level_up`. Under WWN:
- The per-turn native tick MUST stop firing (no `award_turn_xp` `op=award_turn_xp`
  emit each turn in a WWN session).
- Any WWN XP gain MUST tie to a **real WWN expedition/goal award OTEL event** — a
  span the GM panel can see, distinguishing "engine awarded a real WWN goal" from
  "Claude improvised XP". WWN spans live in `telemetry/spans/wwn.py` (see the existing
  `wwn_*` span helpers imported at `wwn.py:34-43`) — add the expedition/goal-award span
  there, slug-namespaced (`wwn.xp.*`).
- The edge→penalty conversion MUST emit a WWN-namespaced span proving the strong
  next-round opponent penalty was applied (so the GM panel sees the WWN penalty, not a
  native edge move).

### Test discipline (per server CLAUDE.md)

- **No source-text wiring tests.** Do not grep `beat_kinds.py` / `encounter_lifecycle.py`
  for literals. Use **OTEL span assertions** and **fixture-driven behavior tests**:
  build a WWN-bound snapshot, drive a brace/angle CritSuccess through the real
  `apply_beat`, assert the emitted impact chip + opponent penalty; drive a WWN turn
  through the real pipeline, assert no `award_turn_xp` tick fired and XP stayed
  WWN-scale.
- **Wiring test required:** at least one test must prove the WWN module is actually
  consulted on the production path (`websocket_session_handler` → ruleset), not just
  that the WWN method works in isolation. Registry/dispatch population that runs via
  import side-effects needs a **fresh-interpreter subprocess** test (autouse conftest
  fixtures false-green in-process — `memory/import-sideeffect-registry-wiring-needs-subprocess-test.md`).
- Run `uv run pytest -n0` for race-isolation; cross-check counts directly (don't trust
  `testing-runner` prose — `memory/testing-runner-hallucinates-output.md`). Local
  full-suite needs `postgresql://slabgorb@localhost:5432/sidequest_test`
  (`memory/server-local-pg-role-is-slabgorb.md`).

## Scope Boundaries

### In scope
- **Edge bleed (A):** under a WWN-bound session, the native edge dial, the "Counter
  Stance" fleeting tag, and the "to their edge" chip text no longer surface; a
  favorable brace/angle CritSuccess|Success instead applies a **STRONG (~-3)
  next-round opponent penalty in WWN terms**; the chip reads the real WWN chase-dial
  advance; a WWN OTEL span proves the penalty.
- **XP bleed (B):** under a WWN-bound session, the native per-turn XP tick
  (`award_turn_xp`) and the milestone level-up driven by it no longer apply; XP follows
  the **WWN small-integer expedition/goal scale**; the "10 at turn 0" face is killed
  along with the per-tick; any WWN XP gain ties to a real WWN expedition/goal-award
  OTEL event.
- The `RulesetModule` seam changes (`base.py` + `wwn.py`, and the call-site routing in
  `websocket_session_handler.py`) that make both gateable; the OTEL spans that prove
  both fixes.

### Out of scope (do NOT touch)
- **Native / SWN / CWN behavior** — non-WWN packs keep today's edge/tag grants and
  per-tick XP unchanged (no regression). The WWN override must be WWN-local.
- **Epic 106 sibling stories:** 106-1 (equip starting armor / AC), 106-2 (defensive
  beats mitigate reprisal — the reprisal *model*), 106-4 (consumable heal wiring),
  106-5 (death-state dual-status coherence), 106-6 (narration-truth guardrail). Do not
  fold those fixes in here.
- **The reprisal model itself** — 106-3 is the edge/tag + XP bleeds only; the
  per-beat opponent reprisal is 106-2's design-bearing question.
- **WWN level ladder / advancement effects** beyond making XP WWN-scale and
  expedition-gated — designing the full WWN advancement table is not this story (keep
  it to: no per-tick, small-int, goal-gated, real OTEL event).
- **Content** (no pack/world YAML changes required; this is engine gating). If a WWN
  expedition/goal needs an authored award value, source it from the WWN SRD, do not
  invent a number.
- UI polish (panel portraits, scrapbook captions, narration register) — explicitly
  excluded by the epic.

## AC Context

The acceptance criteria. Both sub-bugs must be demonstrable on the beneath_sunden WWN
repro with OTEL/forensic proof (the lie-detector), not narration assertions alone.

### A — Edge/tag bleed converted to a WWN penalty
1. **No native edge surface under WWN.** In a WWN-bound chase/combat, a Barricade /
   brace CritSuccess shows **no "edge"**, **no "Counter Stance"**, and **no "to their
   edge"** chip text. (Behavior test driving brace CritSuccess through the WWN module's
   `apply_beat`; assert the impact chip string.)
2. **Strong next-round opponent penalty applied.** The favorable brace/angle outcome
   visibly applies a **STRONG (~-3) next-round penalty to the opponent in WWN terms**
   (a real WWN to-hit/save modifier the engine understands) — not a weak transient
   nudge, and expressed via the WWN resolution path, not the native edge dial.
3. **Chip reads the real WWN advance.** The beat-impact chip reads the real WWN
   chase-dial advance, not the native edge phrasing.
4. **OTEL proof.** A WWN-namespaced span (`wwn.*`) fires proving the strong
   next-round opponent penalty was applied (GM-panel visible).

### B — XP gated to the WWN expedition scale
5. **Fresh WWN Warrior shows WWN-scale XP.** A freshly-created WWN Warrior shows
   WWN-scale XP — **0 or a small integer** — **not 135, and not the 10 chargen-seed
   value**.
6. **No silent per-turn tick.** XP does **not** silently tick per turn in a WWN
   session: `award_turn_xp`'s per-turn `op=award_turn_xp` emit does **not** fire each
   turn under WWN (OTEL absence is the proof). The native per-tick remains intact for
   non-WWN packs (regression guard).
7. **Real WWN award is the only gain path.** Any XP gain under WWN ties to a **real
   WWN expedition/goal award OTEL event** (a `wwn.xp.*` span), distinguishing a
   genuine WWN award from improvised/native accrual.

### Cross-cutting
8. **One fix locus.** Both bleeds are fixed by routing through the ADR-117
   `RulesetModule` seam (WWN overrides the native default), not by deleting beats or
   special-casing beneath_sunden.
9. **No regression** to native/SWN/CWN edge grants or per-tick XP; at least one
   wiring test proves the WWN module is consulted on the production turn path.

## Key File Map (cite file:line in implementation)

- `sidequest-server/sidequest/game/ruleset/base.py` — `RulesetModule` ABC, the fix
  seam. No XP/advancement method today; add the XP/advancement authority here.
- `sidequest-server/sidequest/game/ruleset/wwn.py:51` — `WwnRulesetModule` (subclasses
  SWN). WWN-local overrides for the edge→penalty conversion and the expedition-XP
  scale go here.
- `sidequest-server/sidequest/game/ruleset/swn.py:216-227` — SWN `apply_beat`
  delegating to the native engine (the inherited delegation that bleeds).
- `sidequest-server/sidequest/game/ruleset/native.py:56-65` — native `apply_beat`
  delegation (keep unchanged — native baseline).
- `sidequest-server/sidequest/game/beat_kinds.py:171` — "to their edge" chip text;
  `:236` — brace CritSuccess "Counter Stance" + edge penalty; `:250` — angle Success
  grant path; `:142-146` — hp_depletion dial suppression (zeroes numbers but not the
  tag/edge chip — why the bleed surfaces).
- `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py:1485-1533` —
  `award_turn_xp` (per-turn 25/10 tick, the bleed); `:1542` `_XP_PER_MILESTONE`;
  `:1545+` `apply_level_ups`.
- `sidequest-server/sidequest/server/websocket_session_handler.py:1419-1422` — the
  unconditional, ruleset-blind call sites that must route through the seam.
- `sidequest-server/sidequest/telemetry/spans/wwn.py` — WWN span helpers; add
  `wwn.xp.*` (expedition/goal award) and the edge→penalty span here.
- `sidequest-server/sidequest/game/creature_core.py:116` — `xp: int = 0` (the
  accumulator; confirms no literal chargen seed).

## Source Findings (verbatim anchors)
- **Edge bleed:** `sq-playtest-pingpong.md` lines **256–274** — Keith DECISION (273):
  convert edge/tag grant into a STRONG (~-3) next-round opponent penalty in WWN terms;
  native edge dial / "Counter Stance" / "to their edge" no longer surface under WWN.
- **XP bleed:** `sq-playtest-pingpong.md` lines **92–103** — operator diagnosis
  (authoritative): native per-tick advancement (ADR-021) ticking inside WWN, not gated
  by the WWN RulesetModule; WWN uses small-integer expedition XP (L2≈3, L3≈6); TWO
  faces (chargen seed 10 at turn 0 + per-turn tick reaching 135) — both must go.
- **Standing ruling:** WWN-bound mechanical values come from the WWN SRD
  (`.pennyfarthing/sidecars/gm-decisions.md`, 2026-06-13;
  `memory/defer-to-srd-for-mechanics.md`).
