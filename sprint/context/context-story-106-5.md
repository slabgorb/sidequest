---
parent: 106
---

# Story 106-5 Context

## Title
Death-state coherence — the down/death path emits TWO contradictory statuses (terminal
dead/mortally-wounded incapacitating + non-terminal dies-in-6-rounds non-incapacitating)
with mis-stamped provenance (created_turn:0, encounter:None); deterministic 2/2. Emit ONE
coherent state (a real stabilizable dying window OR a terminal dead verdict, never both)
and stamp the real created_turn/created_in_encounter.

## Metadata
- **Story ID:** 106-5
- **Type:** bug
- **Points:** 3
- **Priority:** p1
- **Workflow:** tdd
- **Repo:** server
- **Epic:** 106 — WWN combat hardening for beneath_sunden (fair ramp, ruleset-bleed
  remediation, narration truth)

## Problem

When a PC drops to 0 HP in a WWN-bound world (`caverns_and_claudes/beneath_sunden`,
ADR-117 RulesetModule), `core.statuses` ends up holding **two mutually-exclusive death
states at once**:

1. `{text:'Downed — dead (mortally wounded)', severity:Scar, incapacitating:TRUE,
   created_turn:7, created_in_encounter:combat}` — the genuine terminal lethal-down from
   the LethalityArbiter post-resolution path (ADR-123). Correctly stamped, correctly
   incapacitating.
2. `{text:'Mortal Injury — dies in 6 rounds unless stabilized', severity:Scar,
   incapacitating:FALSE, created_turn:0, created_in_encounter:None}` — a **non-terminal,
   stabilizable** dying-window status with **bogus provenance** (`created_turn:0`,
   `created_in_encounter:None`).

The two statuses come from **two different code paths** — and the differing provenance is
the forensic proof:

- **Terminal "dead" (correctly stamped):** `post_resolution_lethality.py:245-259` builds
  `f"{_DOWNED_PREFIX} — {verdict} (mortally wounded)"` with
  `created_turn=turn, created_in_encounter=enc.encounter_type, incapacitating=True` and
  emits the `ENCOUNTER_STATUS_ADDED` event (`state_transition`/`op=status_added`,
  `decision=lethal_down`, `verdict=dead`) at `post_resolution_lethality.py:313-329`.
- **"Mortal Injury" dying-window (mis-stamped):** the WWN RulesetModule's `resolve_downed`
  at `sidequest-server/sidequest/game/ruleset/wwn.py:255-261` appends
  `Status(text=f"Mortal Injury — dies in {rounds} rounds unless stabilized",
  severity=StatusSeverity.Scar)` — **with no `created_turn` and no `created_in_encounter`**,
  so the `Status` dataclass defaults kick in (`game/status.py:57` `created_turn: int = 0`,
  `:58` `created_in_encounter: str | None = None`). `rounds` comes from
  `cfg.trauma.mortal_injury_rounds`. The same defect exists in `cwn.py:240-245` (and
  `awn.py` inherits CWN), and the Major-Injury status at `wwn.py:275-277` shares it.

**The chargen-seed theory was tested and disproven** (pingpong line 112): a fresh Warrior
Chico `bf7e2e2f` at turn 0 has `core.statuses == []`. The Mortal Injury status is therefore
**created by the down code path itself** (`resolve_downed`), not seeded at creation — it
just *looks* chargen-era because of the `created_turn:0` default.

**Deterministic 2/2** (pingpong line 118): both independent deaths (Zeppo turn 7 / combat,
Chico turn 5 / combat) produce the identical pair — terminal `dead (mortally wounded)`
correctly stamped + `Mortal Injury` always at `created_turn:0`/`enc:None`. Not a fluke; a
death-path bug.

### Two distinct problems (both in scope)

1. **Death path emits a duplicate/incoherent status with mis-stamped provenance (the bug).**
   `resolve_downed` and `post_resolution_lethality` both fire on the same down event and
   both append a status. They are not reconciled: the WWN dying-window status and the
   terminal `dead` status coexist instead of one superseding/gating the other. And the WWN
   one is unstamped.
2. **Contradictory + non-actionable readout (the consequence).** "dead" (terminal,
   incapacitating) and "dies in 6 rounds unless stabilized" (non-terminal, stabilizable)
   are mutually-exclusive WWN states shown together. Worse, the 6-round stabilize clock is a
   **dead letter in solo** — once incapacitated, input is disabled and the PC is "out of the
   action," so there is no path to act on the window. The dying clock is surfaced but
   unactionable.

### Connects to the Groucho observation

The open Groucho note (pingpong line 299 / 116) — "death was an *immediate*
`dead (mortally wounded)` with no intervening WWN dying/stabilize window, Keith's call" — is
explained by this bug. The WWN dying-window status object *does* get created at down-time
(`resolve_downed`), but it is (a) mis-stamped and (b) coexists with the terminal `dead`
verdict from `post_resolution_lethality` rather than **gating** it. The intended WWN flow
(mortally wounded → d6-round stabilize window → dead) is not actually being **driven** by
these two statuses; they are emitted together incoherently. The mechanical question of
whether beneath_sunden's lethality tier *should* run a true dying-window is the design
decision the AC must resolve (see Scope Boundaries).

## Investigation — cited code

- **LethalityArbiter (ADR-123):**
  `sidequest-server/sidequest/agents/lethality_arbiter.py:51-157` — deterministic verdict
  from the genre lethality policy on 0 HP; `_build_verdict` at `:135-156`.
- **Terminal "dead" status creation + correct stamping (the right pattern):**
  `sidequest-server/sidequest/server/post_resolution_lethality.py:245-259`
  (`created_turn=turn`, `created_in_encounter=enc.encounter_type`, `incapacitating=True`).
  Non-lethal "Recovering" branch also stamps correctly at `:281-290`.
- **`ENCOUNTER_STATUS_ADDED` emission:**
  `sidequest-server/sidequest/server/post_resolution_lethality.py:313-329`
  (`field=encounter`, `op=status_added`, `decision`, `verdict`, `status`); routed to the
  `ENCOUNTER_STATUS_ADDED` kind at `sidequest-server/sidequest/telemetry/watcher_hub.py:361`;
  span context at `sidequest-server/sidequest/telemetry/spans/encounter.py:680-709`.
- **"Mortal Injury — dies in N rounds" creation (the mis-stamping bug):**
  `sidequest-server/sidequest/game/ruleset/wwn.py:255-261` — `Status(...)` with NO
  `created_turn` / `created_in_encounter`. Span `wwn_mortal_injury_declared_span` at
  `:262`. Major-Injury status (also unstamped) at `:275-277`. CWN twin:
  `sidequest-server/sidequest/game/ruleset/cwn.py:240-245`; AWN inherits CWN
  (`awn.py:30-32`).
- **`resolve_downed` signature + docstring (declares the Mortal Injury contract):**
  `sidequest-server/sidequest/game/ruleset/wwn.py:234-292` ("Always declares a Mortal
  Injury (Scar status; dies at the end of cfg.trauma.mortal_injury_rounds unless
  stabilized)").
- **Status model + buggy defaults:**
  `sidequest-server/sidequest/game/status.py:45-70` — `created_turn: int = 0` (`:57`),
  `created_in_encounter: str | None = None` (`:58`), `incapacitating` field, `severity`.
- **StatusSeverity enum:** `sidequest-server/sidequest/game/status.py:36-42`
  (`Scratch`/`Wound`/`Scar`/`Boon`).
- **WWN dying-window config:** the dying-window duration is **ruleset config**
  (`cfg.trauma.mortal_injury_rounds`), NOT in the genre `LethalityPolicy`
  (`sidequest/genre/models/lethality.py:25-50`, which only names the `verdicts_on_zero_hp`).
  So WWN *does* express a dying-window duration; whether the lethality verdict for this tier
  should *honor* a stabilize window vs. resolve straight to `dead` is the open design call.

## Business Context

The two mechanics-first players in Keith's playgroup — **Sebastien and Jade** (per CLAUDE.md
"Who This Is For") — would read this state and immediately ask the one question the engine
cannot currently answer: **"Am I dead, or do I have 6 rounds?"** One status says terminal
`dead (mortally wounded)`; the other says non-terminal `dies in 6 rounds unless
stabilized`. They are mutually-exclusive WWN states, and both are shown at once. This is
exactly the contradictory-mechanical-state-surfaced-to-the-player failure that the
mechanics-first audience is most sensitive to — Jade and Sebastien carried a 140-turn game
on mechanical legibility and specifically miss crunch that is *coherent and legible* in the
player UI. A death readout that contradicts itself is the opposite of legible. Death is also
the single highest-stakes moment in a session; getting its mechanical truth wrong undercuts
the whole "good enough to fool a career GM" bar (Keith). The fix must leave a downed PC with
**one** answer to "what is my mechanical state right now."

## Technical Guardrails

- **Forensics-as-lie-detector is load-bearing here.** The two statuses' differing
  provenance (`created_turn:7/enc:combat` vs `created_turn:0/enc:None`) is the *proof* they
  come from two un-reconciled code paths (`post_resolution_lethality` vs ruleset
  `resolve_downed`). Do NOT "fix" this by cosmetically rewriting one string — fix the path
  divergence. The created_turn/created_in_encounter stamps are diagnostic infrastructure;
  preserve them.
- **Any dying-window status MUST carry the real `created_turn` and `created_in_encounter`,
  never 0/None.** The correct pattern already exists at
  `post_resolution_lethality.py:251-252` — `resolve_downed` must be given (and use) the
  current turn and encounter when constructing `Status(...)`. The `Status` dataclass
  *defaults* (`status.py:57-58`) are the trap; relying on them on the death path is the bug.
- **Emit exactly ONE coherent state.** Either a terminal `dead` verdict OR a real
  stabilizable dying window — never both in `core.statuses` simultaneously. The two paths
  (`resolve_downed` + `post_resolution_lethality`) must be reconciled so one gates/supersedes
  the other rather than both appending.
- **OTEL discipline (CLAUDE.md OTEL principle, ADR-031/090/103):** the chosen state must
  emit the matching span. `post_resolution_lethality.py:313-329` already emits
  `ENCOUNTER_STATUS_ADDED`; `wwn.py:262` emits `wwn_mortal_injury_declared_span`. The fix
  must not leave a status in state with no event trail (the exact 2026-06-07 regression
  called out in the `post_resolution_lethality` comment at `:309-312`). The green gate is a
  span/behavior assertion, not a source-text grep (see server CLAUDE.md "No Source-Text
  Wiring Tests").
- **Standing ruling — WWN values come from the WWN SRD** (`.pennyfarthing/sidecars/
  gm-decisions.md`, 2026-06-13). The dying-window round count is already SRD-sourced via
  `cfg.trauma.mortal_injury_rounds`; do not invent a new number.
- **Don't regress the incapacitation marker.** The terminal `dead` status'
  `incapacitating=True` is read by the turn-intake gate so a dead PC's actions never reach
  the narrator (`post_resolution_lethality.py:253-257`). Whatever single state is emitted
  must keep the correct incapacitation semantics for that state.

## Scope Boundaries

- **In scope:**
  - Death-path **status coherence** — reconcile `resolve_downed` (`wwn.py:255-261`) and
    `post_resolution_lethality` (`:245-259`) so a downed PC ends with exactly ONE coherent
    death state, not two contradictory ones.
  - **Provenance stamping** — any dying-window / mortal-injury status must carry the real
    `created_turn` and `created_in_encounter` (fix the unstamped `Status(...)` in
    `wwn.py`; the CWN twin at `cwn.py:240-245` and the Major-Injury status at `wwn.py:275-277`
    are the same defect — fix them consistently, don't half-fix WWN only).
  - The OTEL span(s) proving the single coherent state was applied with real provenance.
- **OPEN QUESTION — flag, do not silently expand:** whether beneath_sunden's lethality tier
  should drive a **true WWN dying-window** (mortally wounded → d6-round stabilize → dead)
  vs. a **terminal dead verdict**. This is a design-bearing call (it is the open Groucho
  observation, "Keith's call"). A *real* dying window is only meaningful if the stabilize
  clock is **actionable** — and in solo today, input is disabled the moment the PC is
  incapacitated, so a 6-round stabilize window is a dead letter (no self-stabilize path, no
  ally). If the AC chooses the dying-window route, surface the actionability gap as a
  follow-up rather than shipping an unactionable clock. **Do not implement a new stabilize
  UI / self-stabilize action in this story** unless the AC explicitly scopes it; default to
  the smaller-change resolution (one coherent state, correctly stamped) and write the
  dying-window-actionability question up as a flagged follow-up.
- **Out of scope:** the other Epic-106 threads — armor-equip / AC (106-1), reprisal
  mitigation (106-2), XP/edge ruleset-bleed (106-3), consumable heal-in-confrontation
  (106-4), narration knockdown/hit-truth (106-6). Multiplayer down/stabilize semantics
  (ally-stabilizes-downed-PC) beyond what the solo repro needs — note any MP follow-up,
  don't build it here. No changes to the LethalityArbiter verdict policy beyond what
  reconciling the two paths requires.

## AC Context

The acceptance criteria must establish:

1. **One coherent death state.** When a WWN PC drops to 0 HP, `core.statuses` contains
   exactly ONE death/down state — either a terminal `dead` verdict OR a single real
   stabilizable dying window — **never both** the terminal `dead (mortally wounded)` and the
   `Mortal Injury — dies in N rounds` simultaneously. (Behavior test on the beneath_sunden
   repro: a Warrior taken to 0 HP in combat ends with a single, non-contradictory death
   state.)
2. **Real provenance on any dying-window/mortal-injury status.** No death-path status
   carries `created_turn:0` or `created_in_encounter:None`; the dying-window/mortal-injury
   status (and the CWN twin + Major-Injury status) carry the real turn and encounter type,
   matching the pattern already used by the terminal `dead` status. (Assert on the stamped
   `created_turn`/`created_in_encounter`, deterministic across the 2/2 repro — turn != 0,
   encounter != None.)
3. **No contradiction between terminal and stabilizable semantics.** The emitted state's
   `incapacitating` flag and reversibility are internally consistent with what it claims: a
   terminal `dead` is incapacitating and not stabilizable; a dying window is a single status
   that does not coexist with a `dead` verdict. A mechanics-first player can answer "am I
   dead or do I have N rounds?" from the single status.
4. **OTEL proof (the gate).** The chosen single state emits its matching span with the real
   provenance — no death-path status left in state without an event trail; the
   `ENCOUNTER_STATUS_ADDED` / `wwn.mortal_injury.declared` span reflects the single coherent
   outcome. Green gate is span/behavior, not source-text grep.
5. **Open dying-window-actionability question recorded.** If the AC selects the terminal-dead
   resolution, the WWN-dying-window decision is documented as a deliberate ruling (not
   silently dropped); if it selects the dying-window resolution, the solo-stabilize
   actionability gap is captured as an explicit follow-up rather than shipping an
   unactionable clock.
6. **No regression** to the terminal-down incapacitation gate (a dead PC's actions still
   never reach the narrator — `post_resolution_lethality.py:253-257`) or to the non-lethal
   "Recovering" branch (`:281-290`).

## Dependencies
- **Design-bearing open question** (terminal-dead vs. true dying-window for this lethality
  tier) is a Keith/Architect ruling — resolve at AC time before Dev commits to a path.
- Independent of sibling 106 stories at the code level, but shares the "WWN values come from
  the SRD" standing ruling with the rest of the epic.
