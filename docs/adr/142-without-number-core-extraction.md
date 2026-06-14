---
id: 142
title: "Without Number Core Extraction — an Honest WithoutNumberRulesetModule Base, Reparented WN Siblings, and a Shaped-Attribute Retune"
status: accepted
date: 2026-06-13
deciders: ["Keith Avery", "Atlas (Architect)"]
supersedes: null
superseded-by: null
related: [33, 114, 117, 126, 140, 143]
tags: [game-systems]
implementation-status: partial
implementation-pointer: "sidequest-server/sidequest/game/ruleset/without_number.py (extracted WN core); swn/wwn/cwn/awn.py reparented onto it; spans/wn.py slug-parameterized emitters; tests/game/ruleset/test_142_wn_core_extraction.py + test_102_4_wn_turn_model_family.py (shipped #841). Step-2 attributes via RulesConfig.standard_array (content packs). Deferred: lethality tuning (awaits playtest), attribute arrange-path, and the ruleset chargen seam (ADR-143 follow-on)."
---

# ADR-142: Without Number Core Extraction — an Honest WithoutNumberRulesetModule Base, Reparented WN Siblings, and a Shaped-Attribute Retune

> **This ADR was promoted from the 2026-06-13 design spec after the work
> shipped** (`feat/wn-core-extraction-adr-142`, server #841; content
> `feat/wwn-shaped-standard-array-adr-142`). It records the decision *and* the
> as-built deviations discovered during execution. ADR-143 ("WN binding replaces
> the native combat engine") depends on this core and previously carried a
> placeholder note about the 141→143 doc gap; this record closes that gap.

## Context

SideQuest's doctrine is **Crunch in the Genre, Flavor in the World** (SOUL.md):
the ruleset owns mechanics once and every genre inherits them, so authoring a
world never means re-deriving combat math or lethality. ADR-117 made resolution
pluggable per genre behind the `RulesetModule` seam; Keith is standardizing the
whole project on Kevin Crawford's **Without Number SRD family** — WWN, SWN, CWN,
AWN — with Fate Core to replace the remaining `native`-ruleset genres. Licensing
is clear: Keith has direct correspondence with Crawford granting the OK to build
on the WN SRDs, so the chassis is implemented **faithfully** (Foci, skills,
saves, Shock/Trauma/Strain, Effort) rather than defensively paraphrased.

### The presenting symptom

Caverns & Claudes chargen produced flat 13/12 ability scores (point-buy 27) and
characters died almost instantly. These are **not per-world bugs** — they are
what happens when mechanics are re-derived per world instead of owned by the
ruleset. The fix is structural, not another hand-tune.

### The structural problem (proven in code)

The server already had a Without Number sharing hierarchy, but it grew
**upside-down** — whoever was written first became the base:

```
RulesetModule (ABC — generic; NO chargen surface)
├── NativeRulesetModule              (82 lines — the homebrew being retired)
└── SwnRulesetModule (582 lines)      ← de-facto "WN base" by accident of being first
    ├── WwnRulesetModule(Swn…)        (511 lines)
    └── CwnRulesetModule(Swn…)        (314 lines)
        └── AwnRulesetModule(Cwn…)    (31 lines — "random inheritance")
```

Two consequences:

1. **The smoking gun:** `WwnRulesetModule` *overrode* `ship_attack_params` — a
   **fantasy** ruleset inherited **starship combat** (and `adjudicate_jump`,
   spike-drive jumps) from SWN and had to neutralize it. That is proof the
   hierarchy was wrong, not merely untidy.
2. **Chargen shared nothing.** Combat behavior was (messily) inherited via
   Python, but `char_creation.yaml` resolved **world-authoritative with genre
   fallback** — world replaces genre wholesale, no ruleset layer at all. Every WN
   pack re-authored chargen and balance from scratch. That asymmetry *is* the
   flat-13/instant-death pain.

Epic 102 delivered the *behavior* (cast spine, WN turn model, downed seam) **on
top of this inverted hierarchy without ever fixing it.** This is the structural
completion that "Complete the Without Number Family" implies.

## Decision

Extract an honest shared chassis and reparent every WN sibling onto it, then —
in a deliberately separate step — retune attribute generation so a fresh
character is no longer a flat 13 who dies in one hit.

### Target architecture

```
RulesetModule (ABC)
├── NativeRulesetModule          (retiring — replaced by Fate Core per genre)
├── FateCoreRulesetModule        (future, parallel tree)
└── WithoutNumberRulesetModule    ← honest shared chassis (Layer 0)
    ├── SwnRulesetModule          (space, spike drives, psionic disciplines)
    ├── WwnRulesetModule          (Arts magic, Warrior: Killing Blow / Veteran's Luck)
    ├── CwnRulesetModule          (cyberware, hacking)
    └── AwnRulesetModule          (mutations, strains)  ← reparented onto core, NOT Cwn
```

- **Layer 0 — `WithoutNumberRulesetModule`:** the genuine shared chassis. The
  "stop thinking about mechanics" layer.
- **Layer 1 — WWN / SWN / CWN / AWN:** each extends Layer 0 with *only* its
  game-specific subsystems. Clean siblings; no `Wwn(Swn)`, no `Awn(Cwn)`.
- **Layer 2 — genre/world binding:** picks a ruleset via `rules.yaml: ruleset:`,
  supplies **content** (which classes/foci/backgrounds exist, flavor names) —
  never mechanics. Fate Core slots in here later as a sibling to the whole WN tree.

### Extraction boundary

**Moves UP to `WithoutNumberRulesetModule` (genuinely shared):**

| Group | Methods |
|---|---|
| d20 conventions | `stat_modifier`, `compute_dc`, `offer_difficulty`, `find_confrontation` |
| core resolution | `attack_params`, `resolve_opponent_attack`, `apply_beat`, `check_params`, `save_params` (base), `resolve_damage`, `roll_initiative` |
| Effort economy | `commit_effort`, `reclaim_effort`, `reclaim_scene_effort`, `reclaim_day_and_refresh` |
| lethality skeleton | the **Shock / Trauma / Mortal-Injury / System-Strain** death model (was stranded in `wwn.py`) — the family-wide death model, tuned per-game, not restructured |

**Stays in the Layer-1 sibling (game-specific):**

| Ruleset | Keeps |
|---|---|
| SWN | `ship_attack_params`, `adjudicate_jump` |
| WWN | `resolve_spellcast` (Arts), `apply_killing_blow`, `veterans_luck`, WWN-tuned `save_params`/`resolve_trauma` overrides |
| CWN | cyberware + `resolve_hacking` |
| AWN | mutations, strains |

**Consistency with the 2026-06-10 magic decision (ADR-126 boundary):** WN magic
lives on `core.spellcasting` / `core.effort`, owned by the RulesetModule (not the
ADR-126 `magic_state` plugin). The Effort economy moving to core preserves this
exactly; `resolve_spellcast` stays WWN-specific and keeps emitting `wwn.spell.cast`.

### Two sequential steps, one atomic plan (the no-ball-drop rule)

A half-extracted base that leaves two rulesets reparented and two not is **worse**
than the honest tangle. The slice lands atomically or not at all.

**Step 1 — Extract the WN core (strictly behavior-preserving).** Classic
extract-superclass refactor: create `WithoutNumberRulesetModule(RulesetModule)`,
lift the shared-chassis methods up out of `swn.py`, reparent all four siblings
directly onto it, delete the `Wwn(Swn)` / `Cwn(Swn)` / `Awn(Cwn)` chains, and have
each sibling retain only its game-specific overrides. **Hard contract: zero
behavior change** — every WN ruleset's combat / save / Effort / lethality output
is byte-identical before and after.

**Step 2 — Retune attributes (the visible win).** An isolated, deliberate
behavior change kept separate from Step 1 so the characterization tests cleanly
distinguish "refactor (no change)" from "tuning (intended change)." Give a fresh
character real shape (a prime, real dump stats) instead of flat 13s, citing the
WWN SRD chargen array.

## Consequences

**Positive**

- Mechanics are owned once by the WN core and inherited family-wide. WWN no longer
  carries starship combat it must neutralize.
- A characterization regression net pins Step 1, making "atomic, no half-reparent"
  enforceable rather than aspirational.
- A fresh WWN character has shaped stats → real HP → survivable first hit, the
  primary survivability lever, the same week the refactor lands.
- This core is the foundation ADR-143 (WN combat owns the WN round) builds on.

**Negative / cost**

- The isinstance capability-gate migration (below) was larger than the design
  enumerated; reparent and gate migration proved inseparable.
- Contributors must internalize that WN siblings are clean siblings: no
  `Wwn(Swn)`. A reflection (MRO) check guards against regressing to cross-sibling
  inheritance.

## As-built — deviations from the design (resolved during execution)

The structural extraction landed as designed; the following deviations were
discovered in code and resolved during execution.

1. **The isinstance capability-gate migration was the hidden bulk of Step 1** —
   ~15 gates the extraction-boundary table never enumerated. AWN's entire
   capability binding rode on `Awn IS-A Cwn`; flattening broke it. A full Gate
   Migration Table (EXPAND→`WithoutNumberRulesetModule`, NARROW→
   `AwnRulesetModule`, KEEP) is the authoritative artifact, in the plan. The
   reparent and the gate migration are **inseparable** (proven: reparenting WWN
   without migrating `dice.py`/`session.py`'s `isinstance(..., SwnRulesetModule)`
   gates leaves WN combat dead) — they landed in one atomic commit, as the
   atomicity rule demanded.

2. **Psionics is WN-core, not SWN-only (corrects the extraction boundary).** The
   design kept `activate_discipline` on SWN. But `heavy_metal` is `ruleset: wwn`
   *with* a psionic catalog (`test_psionics_dispatch_wiring_102_6`), so reparenting
   WWN off SWN regressed WWN psionics. `activate_discipline` +
   `PSIONIC_EFFORT_SOURCE` were moved to `WithoutNumberRulesetModule` (they only
   call WN-core `commit_effort`/`apply_system_strain`); `_psionic_module`
   broadened to `WithoutNumberRulesetModule`. Psionics is shared WN-family crunch.

3. **DD-3 (luck-in-core) amended for No Silent Fallbacks.** Hoisting the `luck`
   save into the core made SWN *silently resolve* a Luck save it has no business
   having (SWN saves are Physical/Evasion/Mental only). Fix: the core owns `luck`
   for the three luck-bearing siblings; **SWN overrides `save_params` to reject
   `luck` loudly**. AWN still reparents cleanly (inherits luck from core).

4. **AWN span correction shipped in Step 1** (user-approved): AWN's lethality
   spans were the inherited `cwn.*` mislabel; unifying onto slug-parameterized
   emitters (`spans/wn.py`, mirroring the Effort precedent) corrects them to
   `awn.*`. The dead per-slug `wwn_*`/`cwn_*` lethality emitter functions were
   removed; `cwn.hacking.security_check` and all non-lethality sibling spans were
   kept.

5. **Lethality tools expanded (DD-5, user-approved "expand latent gaps now"):**
   `stabilize_mortal_injury` / `adjust_system_strain` extended to WWN;
   `commit_effort` to all four WN siblings (Effort is core); `use_mutation` +
   `_awn_mutation_module` narrowed to AWN.

6. **Config tree NOT reparented.** Only the module tree flattened.
   `AwnConfig(CwnConfig)` / `WwnConfig(SwnConfig)` stand; the hoisted lethality
   methods guard `isinstance(cfg, (CwnConfig, WwnConfig))` (precedent:
   `downed_seam.py`). A shared lethality config superclass is deferred.

### Step 2 split along the seam reality (Keith's call, 2026-06-13)

The "visible win" was reshaped once code showed **attribute generation is not
ruleset-owned** — it lives in `builder.py` (chargen FSM) + per-pack config. Making
it ruleset-owned *is* the deferred ruleset chargen seam (now ADR-143's follow-on).
So:

- **Attributes — per-pack config (Keith's choice).** The three WWN packs
  (`caverns_and_claudes`, `heavy_metal`, `elemental_harmony`) switched from flat
  `point_buy` (round-robin → `[13,13,13,12,12,12]`) to the shaped WWN SRD standard
  array `[14,12,11,10,9,7]`. Enabled by a minimal additive server field
  `RulesConfig.standard_array` (defaults to the legacy `[15,14,13,12,10,8]` — no
  existing pack changes). **Known limitation:** fixed-order assignment puts the
  prime on the first-declared stat (STR — fine for Warrior-default packs, wrong
  for caster Callings). The per-archetype *arrange* path is a candidate for the
  chargen-seam spec.
- **Lethality — deferred to playtest (Keith's call).** The WWN trauma/strain
  config is already the faithful WWN baseline. The shaped array gives real stats →
  real HP, which is the primary survivability lever; explicit lethality dialing
  awaits playtest data and was **not** changed.

### Merge dependency

The content PR (`standard_array:` in pack YAML) **had to merge after** the server
PR (which adds the `RulesConfig.standard_array` field) — on a server without the
field, `extra="forbid"` rejects the packs at load.

## Test strategy (as shipped)

- **Characterization (pins Step 1):** each WN ruleset's output captured for a
  representative matrix — `attack_params`, `save_params`, `resolve_damage`, an
  Effort commit/reclaim cycle, a Shock/Trauma/Mortal-Injury resolution — across
  SWN/WWN/CWN/AWN, asserted identical after the refactor.
- **OTEL span parity:** the WN combat/lethality/cast spans (`wwn.*`,
  `{slug}.mortal_injury`/`.shock`, Effort spend, `wwn.spell.cast`) fire identically
  post-refactor — drive the flow, assert the span (OTEL Observability Principle; no
  source-text wiring tests).
- **Step-2 (intended change):** new assertions for the retuned attribute spread.
- **Wiring / MRO check:** the registry resolves all four slugs to modules whose MRO
  includes `WithoutNumberRulesetModule`, and no WN sibling inherits from another WN
  sibling (reflection, not source grep).

Shipped as `tests/game/ruleset/test_142_wn_core_extraction.py` and
`test_102_4_wn_turn_model_family.py` (#841).

## Alternatives considered

- **Leave the inverted hierarchy and keep neutralizing SWN behavior in WWN.**
  Rejected: the `ship_attack_params` override in a fantasy ruleset is the proof
  the hierarchy is wrong; every new WN pack would re-pay the neutralization tax.
- **Reparent only the two worst offenders (partial flatten).** Rejected by the
  no-ball-drop rule: a half-reparented tree is worse than the honest tangle and
  invites the next contributor to "finish later" (which never happens).
- **Move attribute generation onto the ruleset in this same slice.** Deferred:
  attribute-gen lives in `builder.py`, not the ruleset; relocating it *is* the
  chargen-seam effort and would have broken Step 1's "byte-identical refactor"
  contract. Step 2 took the minimal per-pack `standard_array` path instead.

## Deferred (each becomes its own spec → plan)

1. **Ruleset chargen seam** — add a chargen contribution surface to
   `RulesetModule` (attribute-gen + arrange-path, Background→skills, Foci
   selection), so chargen is shared by ruleset the way combat now is. *The
   architectural unlock for the original chargen request.* (Now in flight as the
   ADR-143 follow-on.)
2. **WWN chargen library** — author the real WWN chargen once (Background granting
   skills, Foci, skills surfaced); bind caverns_and_claudes / heavy_metal /
   elemental_harmony to it. Retires the per-pack copy-paste flow.
3. **SWN / AWN / CWN chargen libraries** — same pattern per sibling.
4. **Fate Core** — `FateCoreRulesetModule` + its chargen, replacing `native` per
   genre.
5. **Lethality tuning** — explicit Shock/Trauma/Mortal-Injury dialing once
   playtest data justifies it.

## References

- Design source: `docs/superpowers/specs/2026-06-13-without-number-core-extraction-design.md`
- Plan: `sidequest-server/docs/superpowers/plans/2026-06-13-without-number-core-extraction.md`
- Adjacent: `sidequest-server/docs/superpowers/specs/2026-06-10-wn-worlds-own-magic-not-magic_state.md`; `2026-05-26-space-opera-swn-binding-design.md`
- ADRs: 117 (pluggable ruleset module system), 114 (ablative HP substrate), 33 (confrontation engine), 126 (pluggable magic system), 140 (genre is rulebook only; world owns cast/catalog), 143 (WN binding replaces native combat — builds on this core)
- Code: `sidequest-server/sidequest/game/ruleset/{without_number,base,native,swn,wwn,cwn,awn,registry,resolution}.py`, `spans/wn.py`
- SRDs: Sine Nomine local copies (WWN/SWN/CWN/AWN SRD PDFs)
