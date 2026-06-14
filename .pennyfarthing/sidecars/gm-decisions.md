# GM Decisions

Standing rulings and doctrine from the operator (Keith) that govern GM/content
work. Append new decisions; don't rewrite history. Convert relative dates to
absolute.

## 2026-06-13 — WWN SRD is the authority for any WWN-bound mechanical question

**Ruling (Keith, verbatim intent):** "When asked 'what should this be like' for
anything under the WWN SRD, the answer is: **use the SRD.**"

**Scope:** Any world/pack bound to the WWN ruleset (`ruleset: wwn` in `rules.yaml`,
ADR-117) — e.g. `caverns_and_claudes/beneath_sunden`, `heavy_metal/barsoom. When a
mechanical value, behavior, or magnitude is unspecified or in doubt — heal amounts,
XP/advancement scale and award model, AC, attack/save math, system strain, effort,
encounter/morale, item effects — **do not invent a number or port a native/legacy
value. Source it from the Worlds Without Number SRD** and cite which SRD rule was
used.

**How to apply:**
- Content authoring: when adding/repairing a WWN-world item or rule, pull the value
  from the WWN SRD, not the native/legacy genre default.
- Playtest findings: when a WWN subsystem produces a value, the correctness oracle is
  the WWN SRD. A value that matches an OSR/D&D-scale (e.g. XP in the hundreds at L1) is
  a **mismatch finding**, because WWN uses small-integer XP (L2 ≈ 3 XP) and
  expedition/goal-based XP, not per-kill XP.
- When wiring an effect (e.g. a healing potion), the magnitude question goes to the
  SRD first; only escalate to Keith if the SRD is genuinely silent.

**Concrete instances this ruling already resolves (2026-06-13 beneath_sunden playtest):**
- *Potion of Mending heal magnitude* → use the WWN SRD healing value, not an invented number.
- *XP scale / award model* → WWN expedition-XP and small-integer scale, not the native
  135-at-L1 number observed on a fresh Warrior.

## 2026-06-13 — Epic 106 ramp rulings (Keith, answering the 106-1 Delivery Findings)

Four blocked-story rulings resolved so Epic 106 (WWN combat hardening for
`beneath_sunden`) can run. All defer to WWN where the SRD speaks.

- **106-2 reprisal model → WWN initiative round (full-defend).** Adopt the WWN
  initiative round so a player can declare full defense and avoid reprisal. Reuses the
  ~80%-built `wn_round.py` infra the Architect found. The beat model does *not* become
  the reprisal authority; WWN initiative does. This is ramp lever #2.
- **helmet_iron → model shield/helmet as +AC modifiers.** Don't drop the item. WWN
  gives helmets no *base* AC, so `helmet_iron` must not occupy the body-armor roll slot
  that leaves ~1/3 of Warriors at AC 10. Model helmet (and shield) as additive AC
  modifiers stacked on body armor, per WWN shield handling. Followup to 106-1.
- **106-4 consumable-use heal magnitude → STILL OPEN (guaranteed vs random scarcity
  not yet ruled).** Heal *magnitude* already governed by the WWN-SRD ruling above
  (Potion of Mending uses the SRD value). The scarcity/slot question (guaranteed heal
  slot vs intended random scarcity) was not asked and remains owed before 106-4 runs.
- **106-5 death-state → true WWN dying window.** Implement a real WWN dying/down state,
  not terminal-dead-only. Caveat carried into the story: the WWN d6 stabilize clock is
  currently unactionable in solo play — the story must address the solo actuator gap,
  not ship a clock nothing can advance.

## 2026-06-14 — Remove the native combat engine under a Without Number binding. DO NOT balance it. (Keith, emphatic)

**Ruling (Keith, verbatim intent):** *"We have tried in the past to make native work
with WWN. This is a DEAD END. We are going to use the Without Number engine so we don't
have to balance. All this 'we were trying to balance native tricks with this other
stuff' — YES, that's the thing we failed at, because the scope was too much. PLEASE get
this clear in ALL documentation — we keep UNDOING it."*

**The point.** We bind Without Number **so that we never have to balance combat.** WN's
published math IS the balance. Layering the native dial/beat engine underneath a WN
binding and tuning the seam re-creates the exact open-ended balancing problem the binding
was meant to eliminate. That hybrid is the dead end. We keep reverting to it because the
reflex — and stale design docs — say "keep `beat_selection`, layer WWN on top."

**Ruling, concretely.** Under a WN binding (`ruleset: wwn` now; `swn`/`cwn`/`awn` staged,
same rule), combat resolves through the Without Number initiative-round engine
(`wn_round.py`). The native ADR-033 beat engine is **DELETED from the WN combat path, not
gated/tuned**: the `strike`/`brace`/`push`/`angle` beat kinds, the edge / fleeting-tag /
"Counter Stance" system, the per-beat auto-reprisal, and the inert dial metrics. **Brace
is not a WWN action.** Each side acts on its own initiative; attack `d20 + hit vs AC`,
weapon dice, Shock, morale, WN saves/lethality/XP.

**This SUPERSEDES** the "Option A full-defend" balance path (#839) and **every**
"tune/convert/gate the native beat" finding: #192 mitigation magnitude, #442
Counter-Stance conversion, Brace tuning. Those are resolved by **removal**, not
adjustment. No agent ships another native-balance patch under a WN world.

**Architecture-of-record:** ADR-143 (`docs/adr/143-wn-binding-replaces-native-combat-no-balancing.md`).
**Doctrine:** SOUL.md → *Bind the Ruleset, Don't Balance It*. **Owner of the rework
spec/epic:** Architect (Neo). FIXER does **not** ship native-balance patches.

**Still valid work (NOT native, not affected by this ruling):** light pool; helmet/armor
AC from the WWN SRD; the guaranteed-heal grant (#843); the Monster Manual per-room
creature binding feeding the WN seater (the WN round must seat its Other from the bound
room roster, per ADR-116, not improvise one — this is the 107-2 finding, and it is a
*seating* fix, not a balance patch). Dial **chase/negotiation** confrontations are not WN
combat and keep the native dial engine even in WN packs.
