---
parent: context-epic-87.md
workflow: tdd
---

# Story 87-4: Content sweep + calibration + OTEL playtest — final integration gate for the heavy_metal WWN port

**Story:** 87-4
**Points:** 5
**Workflow:** tdd
**Epic:** 87 (heavy_metal → Worlds Without Number: Faithful Ruleset Port)
**Repos:** sidequest-content (sweep), sidequest-server (calibration/playtest verification)
**Depends on:** 87-1 (done — `ruleset: wwn` binding + hp_depletion combat, content PR #356), 87-2 (done — classes/chargen **and** the folded-in 87-3 magic content, content PR #358)

## Business Context

This is the **final integration gate** for epic 87. Stories 1–2 made heavy_metal a working WWN pack (ablative-HP combat, five WWN Callings, full High Magic spell catalog) — but the pack still carries the **retired bespoke magic framing** (D5: pact/ledger confrontations + custom rules) and residual 5e scaffolding. Until this story lands, the pack presents *two* magic systems — the live WWN Effort/Strain mechanics and the dead pact-ledger framing — and prompts still teach the narrator costs that have no mechanical backing. That is precisely the "improvised prose" failure mode the epic exists to kill, and the OTEL playtest across both worlds (evropi, long_foundry) is the lie-detector proof that combat and magic now fire mechanically.

**Sequencing note:** 87-3 was **canceled because its scope was folded into 87-2** (per Keith 2026-06-05; content PR #358 — "heavy_metal WWN classes, chargen & real magic"). `spells_wwn.yaml` and the `cast_spell` beat exist; PR #358 explicitly left "Story-4 baggage (ledger/pact confrontations) untouched." Nothing upstream is missing.

## Technical Guardrails

**Authoritative spec:** `docs/superpowers/specs/2026-06-04-heavy-metal-wwn-port-design.md` — §5 Story 4 scope, D5 (retire pact/ledger), §8 risks (sweep breadth, calibration false alarms, flavor loss). **Precedent:** EH is the canonical WWN reference; road_warrior Story-4-equivalent for sweep/calibration shape.

**Retirement targets (ground-truthed 2026-06-05, `genre_packs/heavy_metal/`):**
- `rules.yaml:11–16` — `custom_rules:` block: `ledger_tracking: required`, `pact_cost_attribution: required` → **drop**
- `rules.yaml:255` — `pact_working` ("Working the Rite") confrontation → **remove** (replaced by the live `cast_spell` beat from #358)
- `rules.yaml:309` — `debt_collection` ("The Collector at the Door") confrontation → **cut** (D5: no replacement)
- `prompts.yaml:72` — narrator prompt still teaches the pact-cost framing ("a sorcerer who casts twice in one combat pays twice…") → **re-home to WWN truth** (Effort committed, System Strain as the body's toll); the doom-cost *voice* survives, the ledger *mechanics* must not be implied
- `inventory.yaml:149–150` — warlock/pact focus item lore references the patron-contract framing; review against D5 (flavor may stay; implied ledger mechanics may not)

**Sweep doctrine — distinguish three categories (the §8 breadth risk):**
1. **Dead mechanical references** (5e class/race/spell/stat keys the engine or narrator could cite as rules) → remove/remap. PR #358 already dropped `allowed_classes`/`allowed_races`/`banned_spells`/`default_race` and remapped archetypes/char_creation/power_tiers — the sweep *verifies* completeness rather than redoing it. Known stragglers: `openings.yaml:24` ("paladin-style heroism hooks"), any class-name `class_filter`/tag mismatches vs the five Callings (Warrior/Expert/Necromancer/Elementalist/Pact-born).
2. **Legitimate prose flavor** ("sorcerers work shifts", "wizards" as a word, clerical tags) → **keep**. The pack's voice is not baggage.
3. **World content** — evropi's races (kobold, antman, half-orc, gnome) are *deliberate world flavor* wired through `allows_freeform` (`worlds/evropi/char_creation.yaml:16,28`), **not** 5e leftovers. Do not sweep them away. long_foundry gets the same review.

**Calibration (§8, narrower than road_warrior):** heavy_metal is NOT in `COMBAT_PACKS`/`SHIPPED_PACKS`; the dual-dial load test was already migrated in 87-1. Record the baseline failure list before changes; gate on the FULL suite with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS` set. Removing two dial confrontations + custom_rules may surface load-validator or calibration assertions — fix per the EH/road_warrior shape, never by relaxing a validator.

**OTEL playtest (the lie detector):** both worlds, evropi + long_foundry. Combat: `wwn.*` lethality spans + HP ablation on the production dispatch path. Magic: the `wwn.spell.cast` shape proven by `test_wwn_elemental_harmony_dispatch` — cast spent, HP ablated where damage spells fire, B/X arm NOT fired. Span assertions, not source-text greps (server CLAUDE.md). Headless driver: `just playtest` / `scenarios/`.

**Do NOT touch:** the `wwn:` config block, `classes.yaml`, `spells_wwn.yaml` (87-1/87-2 deliverables — sweep may *read* them as the source of truth for live class names); negotiation ("Cold Negotiation") + chase ("Pursuit") dial confrontations (survive per spec §6.1); any other pack; long_foundry portrait assets (known pending, out of scope).

## Scope Boundaries

**In scope:**
- Retire `pact_working` + `debt_collection` confrontations and the `ledger_tracking`/`pact_cost_attribution` custom rules
- Re-home pact-cost narrator prompt language to WWN Effort/Strain truth
- Exhaustive 5e-baggage sweep (genre files + both worlds), per the three-category doctrine above
- Full-suite calibration with env set; baseline recorded first
- OTEL playtest pass on evropi + long_foundry proving combat + magic fire mechanically
- Epic 87 close-out readiness (this is the last story)

**Out of scope:**
- Any engine/Python changes beyond test updates (epic premise: zero engine changes)
- New spell/class content (87-2/#358 closed that)
- long_foundry portrait assets
- Re-tuning trauma/lethality numbers (Keith's crunch call, made in 87-1)
- evropi/long_foundry world-race redesign — freeform races are features

## AC Context

1. **Pact/ledger framing fully retired.** `pact_working`, `debt_collection`, `ledger_tracking`, `pact_cost_attribution` appear nowhere in the pack (genre or world files). Pack loads cleanly after removal. Test: load test + grep assertion.
2. **No dead mechanical 5e references.** No class/race/spell reference the narrator could cite as *rules* that doesn't resolve to live content (five Callings, `spells_wwn.yaml` catalog, world freeform races). Prose flavor explicitly survives. Test: sweep audit documented in the session file; category-3 keeps justified.
3. **Narrator prompts tell the WWN truth.** No prompt text implies pact-ledger mechanics; doom-cost voice carried by Effort/Strain framing. Test: prompts review + at least the playtest narration shows no ledger improvisation.
4. **Full suite green.** Baseline failure list recorded before changes; full suite (env vars set) passes after, with any confrontation-removal fallout fixed per precedent.
5. **WWN combat + magic mechanically proven (D1, 2026-06-05).** Proven by `sidequest-server/tests/integration/test_wwn_heavy_metal_combat.py` (production seating + dice seams on the real `ruleset: wwn` pack: ruleset bound = wwn; Other seats from `opponent_default_stats`; strike ablates HP; `state_patch.hp` span fires; no-toothless-Other + opponent-reprisal invariants hold). The 87-4 honesty bar is met: in the live OTEL runs the lie-detector fired correctly on unbacked narration (OTEL Observability Principle working as designed). The *live* narrator-in-the-loop OTEL proof — deterministic fixture (`wwn.spell.cast` + `wwn.*`) and free-play discovery — is **deferred to epic 90** (stories 90-1..90-4), because it requires server work (encountergen ruleset-awareness, magic-plugin session-bind instantiation, scene-harness spellcasting/encounter seeding) that is out of epic 87's zero-engine-changes premise. Rationale: `docs/superpowers/specs/2026-06-05-ac5-otel-combat-verification-design.md`.
6. **Epic gate.** With 1–5 done, epic 87's premise is delivered: heavy_metal is a faithful WWN pack on both worlds with no dual-truth content remaining.

## Assumptions

- **PR #358's remap is substantially complete** for archetypes/char_creation/power_tiers — the sweep verifies and patches stragglers rather than redoing the remap. If it finds systemic gaps, that's a deviation to log, not silent rework.
- **The playtest can run headless** against a booted stack (`just up`, `just playtest-scenario`) — no UI work needed. If no heavy_metal scenario fixture exists, authoring a minimal one is in scope for AC 5.
- **`evropi` and `long_foundry` are both selectable** (neither `draft: true`) for playtest purposes; if long_foundry is draft-gated, the playtest may target it via direct world selection in the scenario rather than ungating it.
- **Confrontation removal does not break saved sessions** — existing saves referencing retired confrontation types are a server-side concern; if the load path chokes on them, log the finding and route it as an engine issue rather than patching content around it.
