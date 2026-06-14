# Design — Without Number core extraction: an honest `WithoutNumberRulesetModule` base + lethality/attribute retune

**Date:** 2026-06-13
**Author:** Architect (Atlas the Endurer), at Keith's direction
**Status:** Draft — pending user review
**Promote to:** ADR-142 once a plan exists (load-bearing: restructures the ruleset hierarchy and sets the standardize-on-WN direction)
**Context:** Epic 102 ("Complete the Without Number Family"); the strategic decision to standardize all mechanics on Kevin Crawford's Without Number SRD family (+ Fate Core) and retire the bespoke `native` ruleset.

---

## Why

Keith is standardizing SideQuest's mechanics on the **Without Number SRD family** — WWN, SWN, CWN, AWN — with **Fate Core** to replace the remaining `native`-ruleset genres. The driver is sustainability: you cannot maintain a homebrew system *and* run a generalized content engine. The mechanics should be **owned once by the ruleset** and inherited by every genre, so authoring a world never means re-deriving combat math or lethality.

Licensing is clear: Keith has direct correspondence with Kevin Crawford granting the OK to build on the WN SRDs. The free editions are openly licensed regardless; the personal greenlight means we implement the chassis **faithfully** (Foci, skills, saves, Shock/Trauma/Strain, Effort) rather than defensively paraphrasing. All four SRDs are local:

- `~/Documents/DriveThruRPG/Sine Nomine Publishing/Worlds Without Number System Reference Document/WorldsWithoutNumber_SRD_1.0.pdf`
- `.../Stars Without Number_ Revised Edition _Free Version_/`
- `.../Cities Without Number System Reference Document/`
- `.../Ashes Without Number_ Free Edition/`

### The presenting symptom

Caverns & Claudes chargen produces flat 13/12 ability scores (point-buy 27) and characters die almost instantly. These are **not per-world bugs** — they are what happens when mechanics are re-derived per world instead of owned by the ruleset. The fix is structural, not another hand-tune.

### The structural problem (proven in code)

The server already has a Without Number sharing hierarchy, but it grew **upside-down** — whoever was written first became the base:

```
RulesetModule (ABC — generic; NO chargen surface)
├── NativeRulesetModule              (82 lines — the homebrew being retired)
└── SwnRulesetModule (582 lines)      ← de-facto "WN base" by accident of being first
    ├── WwnRulesetModule(Swn…)        (511 lines)
    └── CwnRulesetModule(Swn…)        (314 lines)
        └── AwnRulesetModule(Cwn…)    (31 lines — "random inheritance")
```

Two consequences:

1. **The smoking gun:** `WwnRulesetModule` *overrides* `ship_attack_params` — a **fantasy** ruleset inherits **starship combat** (and `adjudicate_jump`, spike-drive jumps) from SWN and must neutralize it. That is proof the hierarchy is wrong, not merely untidy.
2. **Chargen shares nothing.** Combat behavior is (messily) inherited via Python, but `char_creation.yaml` resolves **world-authoritative with genre fallback** — world replaces genre wholesale, no ruleset layer at all. Every WN pack re-authors chargen and balance from scratch. That asymmetry *is* the flat-13/instant-death pain.

Epic 102 delivered the *behavior* (cast spine, WN turn model, downed seam) **on top of this inverted hierarchy without ever fixing it.** This spec is the structural completion that "Complete the Without Number Family" implies.

---

## Target architecture

```
RulesetModule (ABC)
├── NativeRulesetModule          (retiring — replaced by Fate Core per genre)
├── FateCoreRulesetModule        (future, parallel tree)
└── WithoutNumberRulesetModule    ← NEW honest shared chassis (Layer 0)
    ├── SwnRulesetModule          (space, spike drives, psionic disciplines)
    ├── WwnRulesetModule          (Arts magic, Warrior: Killing Blow / Veteran's Luck)
    ├── CwnRulesetModule          (cyberware, hacking)
    └── AwnRulesetModule          (mutations, strains)  ← reparented onto core, NOT Cwn
```

Three layers, conceptually:

- **Layer 0 — `WithoutNumberRulesetModule`:** the genuine shared chassis (below). The "stop thinking about mechanics" layer.
- **Layer 1 — WWN / SWN / CWN / AWN:** each extends Layer 0 with *only* its game-specific subsystems. Clean siblings; no `Wwn(Swn)`, no `Awn(Cwn)`.
- **Layer 2 — genre/world binding:** picks a ruleset via `rules.yaml: ruleset:`, supplies **content** (which classes/foci/backgrounds exist, flavor names) — never mechanics. Fate Core slots in here later as a sibling to the whole WN tree.

### Extraction boundary (grounded in the current method surface)

**Moves UP to `WithoutNumberRulesetModule` (genuinely shared):**

| Group | Methods |
|---|---|
| d20 conventions | `stat_modifier`, `compute_dc`, `offer_difficulty`, `find_confrontation` |
| core resolution | `attack_params`, `resolve_opponent_attack`, `apply_beat`, `check_params`, `save_params` (base), `resolve_damage`, `roll_initiative` |
| Effort economy | `commit_effort`, `reclaim_effort`, `reclaim_scene_effort`, `reclaim_day_and_refresh` |
| lethality skeleton | the **Shock / Trauma / Mortal-Injury / System-Strain** death model (currently stranded in `wwn.py`) — the family-wide death model, tuned per-game, not restructured |

**Stays in the Layer-1 sibling (game-specific):**

| Ruleset | Keeps |
|---|---|
| SWN | `ship_attack_params`, `adjudicate_jump`, `activate_discipline` (psionics) |
| WWN | `resolve_spellcast` (Arts), `apply_killing_blow`, `veterans_luck` (Warrior), WWN-tuned `save_params`/`resolve_trauma` overrides |
| CWN | cyberware + `resolve_hacking` |
| AWN | mutations, strains |

**Consistency with the 2026-06-10 magic decision:** WN magic lives on `core.spellcasting` / `core.effort`, owned by the RulesetModule (not the ADR-126 `magic_state` plugin). The Effort economy moving to the core preserves this exactly; `resolve_spellcast` stays WWN-specific and keeps emitting `wwn.spell.cast`.

---

## Scope of THIS spec (the foundation slice)

One plan, **two sequential steps**, so there is no gap to "drop the ball" into between foundation and felt value. The no-ball-drop rule is the governing constraint: a half-extracted base that leaves two rulesets reparented and two not is **worse** than the honest tangle. This slice lands atomically or not at all.

### Step 1 — Extract the WN core (strictly behavior-preserving)

Classic *extract-superclass* refactor:

1. Create `WithoutNumberRulesetModule(RulesetModule)`; lift the shared-chassis methods (table above) up out of `swn.py`.
2. Reparent all four: `Swn`, `Wwn`, `Cwn`, `Awn` each extend `WithoutNumberRulesetModule` directly. Delete the `Wwn(Swn)` / `Cwn(Swn)` / `Awn(Cwn)` chains.
3. Each sibling retains only its game-specific overrides. WWN loses the inherited `ship_attack_params` override entirely (nothing to neutralize once it doesn't inherit spike drives).
4. Registry (`registry.py`) unchanged in behavior — same slugs resolve to the same four modules.

**Hard contract: zero behavior change.** Every WN ruleset's combat / save / Effort / lethality output is byte-identical before and after.

### Step 2 — Retune lethality + attributes (the visible win)

Now that lethality and attribute defaults live in the WN core, make a fresh character not a flat 13 who dies in one hit. **Isolated, deliberate behavior change** — kept separate from Step 1 so the characterization tests cleanly distinguish "refactor (no change)" from "tuning (intended change)."

- Attribute generation: revisit the point-buy budget / array so scores have shape (a 14–16 prime, real dump stats) instead of flat 13s. Cite WWN SRD chargen (attributes + the standard array / point-buy).
- Lethality: tune the Shock/Trauma/Mortal-Injury defaults in the core so first-session lethality matches WWN's actual feel (Mortal Wounds → stabilization window), not instant death. Cite WWN SRD lethality chapter for the numbers.

Both steps ship in one plan. Step 1 lays the WN core; Step 2 makes a character feel different the same week.

---

## Test strategy

- **Characterization (pin Step 1):** before refactor, capture each WN ruleset's output for a representative matrix — `attack_params`, `save_params`, `resolve_damage`, an Effort commit/reclaim cycle, a Shock/Trauma/Mortal-Injury resolution — across SWN/WWN/CWN/AWN. After refactor, assert identical. This is the regression net that makes "atomic, no half-reparent" enforceable.
- **OTEL span parity:** the WN combat/lethality/cast spans (`wwn.*`, `{ruleset}.mortal_injury`/`.shock`, Effort spend, `wwn.spell.cast`) fire identically post-refactor — drive the flow, assert the span (per the OTEL Observability Principle; no source-text wiring tests).
- **Step 2 (intended change):** new assertions for the retuned attribute spread and the survivable-first-hit lethality. These are the *only* tests expected to change between Step 1 and Step 2.
- **Wiring test:** the registry resolves all four slugs to modules whose MRO includes `WithoutNumberRulesetModule`; a reflection check (MRO, not source grep) that no WN sibling inherits from another WN sibling.

---

## Explicitly deferred (named so this spec stays self-contained)

Each becomes its own spec → plan, in this order:

1. **Ruleset chargen seam** — add a chargen contribution surface to `RulesetModule` (attribute-gen, Background→skills, Foci selection), so chargen can be shared by ruleset the way combat now is. *This is the architectural unlock for the original request.*
2. **WWN chargen library** — author the real WWN chargen once (Background granting skills, Foci, skills surfaced), bind caverns_and_claudes / heavy_metal / elemental_harmony to it. Retires the per-pack copy-paste flow.
3. **SWN / AWN / CWN chargen libraries** — same pattern per sibling.
4. **Fate Core** — `FateCoreRulesetModule` + its chargen, replacing `native` per genre.

The original chargen pain is fixed in two passes: Step 2 of *this* spec makes existing chargen produce a survivable, shaped character; deferred #1–#2 make chargen actually exercise WWN's Background/Foci pillars.

---

## Risks / watch-outs

- **Half-reparent is the failure mode.** Mitigated by atomicity + the characterization net: the slice is not "done" until all four siblings reparent and the pinning tests pass.
- **`save_params`/`resolve_trauma` partial overrides.** WWN overrides `save_params` with a `super()` call; the base must move up without changing the override's result. The characterization matrix must include WWN saves specifically.
- **AWN reparent.** AWN currently `Awn(Cwn)` — confirm during extraction that AWN inherits nothing *behaviorally* from CWN that isn't actually WN-core; anything genuinely CWN-shared-with-AWN that isn't WN-core is a real finding to log, not silently move.
- **Native untouched.** `NativeRulesetModule` stays exactly as-is in this slice; its retirement (→ Fate Core) is a separate, later effort. No native behavior changes here.

---

## References

- Adjacent: `sidequest-server/docs/superpowers/specs/2026-06-10-wn-worlds-own-magic-not-magic_state.md` (WN magic on `core.spellcasting`/`core.effort`); `2026-05-26-space-opera-swn-binding-design.md`
- ADR-117 (pluggable ruleset module system), ADR-114 (ablative HP substrate), ADR-033 (confrontation engine), ADR-140 (genre is rulebook only; world owns cast/catalog)
- Code: `sidequest-server/sidequest/game/ruleset/{base,native,swn,wwn,cwn,awn,registry,resolution}.py`
- SRDs: Sine Nomine local copies (paths above)

---

## As-built (implemented 2026-06-13) — deviations from this design

Implemented on branches `feat/wn-core-extraction-adr-142` (server, 10 commits) and `feat/wwn-shaped-standard-array-adr-142` (content, 1 commit). Plan: `sidequest-server/docs/superpowers/plans/2026-06-13-without-number-core-extraction.md`. The structural extraction landed as designed; the following deviations were discovered in code and resolved during execution. **Promote this section into ADR-142.**

1. **The isinstance capability-gate migration was the hidden bulk of Step 1** — ~15 gates the extraction-boundary table never enumerated. AWN's entire capability binding rode on `Awn IS-A Cwn`; flattening broke it. A full Gate Migration Table (EXPAND→`WithoutNumberRulesetModule`, NARROW→`AwnRulesetModule`, KEEP) is the authoritative artifact, in the plan. The reparent and the gate migration are **inseparable** (proven: reparenting WWN without migrating `dice.py`/`session.py`'s `isinstance(..., SwnRulesetModule)` gates leaves WN combat dead) — they landed in one atomic commit, as the spec's atomicity rule demanded.

2. **Psionics is WN-core, not SWN-only (corrects the extraction boundary).** This spec kept `activate_discipline` on SWN. But `heavy_metal` is `ruleset: wwn` *with* a psionic catalog (`test_psionics_dispatch_wiring_102_6`), so reparenting WWN off SWN regressed WWN psionics. `activate_discipline` + `PSIONIC_EFFORT_SOURCE` were moved to `WithoutNumberRulesetModule` (they only call WN-core `commit_effort`/`apply_system_strain`); `_psionic_module` broadened to `WithoutNumberRulesetModule`. Psionics is shared WN-family crunch.

3. **DD-3 (luck-in-core) amended for No Silent Fallbacks.** Hoisting the `luck` save into the core made SWN *silently resolve* a Luck save it has no business having (SWN saves are Physical/Evasion/Mental only). Fix: the core owns `luck` for the three luck-bearing siblings; **SWN overrides `save_params` to reject `luck` loudly**. AWN still reparents cleanly (inherits luck from core).

4. **AWN span correction shipped in Step 1** (user-approved): AWN's lethality spans were the inherited `cwn.*` mislabel; unifying onto slug-parameterized emitters (`spans/wn.py`, mirroring the Effort precedent) corrects them to `awn.*`. The dead per-slug `wwn_*`/`cwn_*` lethality emitter functions were removed; the `cwn.hacking.security_check` and all non-lethality sibling spans were kept.

5. **Lethality tools expanded (DD-5, user-approved "expand latent gaps now"):** `stabilize_mortal_injury` / `adjust_system_strain` extended to WWN; `commit_effort` to all four WN siblings (Effort is core); `use_mutation` + `_awn_mutation_module` narrowed to AWN.

6. **Config tree NOT reparented.** Only the module tree flattened. `AwnConfig(CwnConfig)` / `WwnConfig(SwnConfig)` stand; the hoisted lethality methods guard `isinstance(cfg, (CwnConfig, WwnConfig))` (precedent: `downed_seam.py`). A shared lethality config superclass is deferred.

### Step 2 split along the seam reality (Keith's call, 2026-06-13)

The "visible win" was reshaped once code showed **attribute generation is not ruleset-owned** — it lives in `builder.py` (chargen FSM) + per-pack config. Making it ruleset-owned *is* the deferred "ruleset chargen seam" spec. So:

- **Attributes — per-pack config (Keith's choice).** The three WWN packs (`caverns_and_claudes`, `heavy_metal`, `elemental_harmony`) switched from flat `point_buy` (round-robin → `[13,13,13,12,12,12]`) to the shaped WWN SRD standard array `[14,12,11,10,9,7]`. Enabled by a minimal additive server field `RulesConfig.standard_array` (defaults to the legacy `[15,14,13,12,10,8]` — no existing pack changes). **Known limitation:** fixed-order assignment puts the prime on the first-declared stat (STR — fine for the Warrior-default packs, wrong for caster Callings). The per-archetype *arrange* path is a candidate for the deferred chargen-seam spec.
- **Lethality — deferred to playtest (Keith's call).** The WWN trauma/strain config is already the faithful WWN baseline (in-code comment: "lethality tuning is Keith's call"). The shaped array gives real stats → real HP, which is the primary survivability lever; explicit lethality dialing awaits playtest data and was **not** changed.

### Merge dependency

The content PR (`standard_array:` in pack YAML) **must merge after** the server PR (which adds the `RulesConfig.standard_array` field) — on a server without the field, `extra="forbid"` rejects the packs at load.

### Still deferred (unchanged from "Explicitly deferred" above)

Ruleset chargen seam (#1) — now also owns the attribute *arrange* path and the eventual move of attribute-gen from `builder.py` to ruleset ownership; WWN/SWN/AWN/CWN chargen libraries (#2–#3); Fate Core (#4).
