---
story_id: "106-1"
jira_key: ""
epic: "106"
workflow: "tdd"
---
# Story 106-1: Equip starting armor at chargen and derive AC from the WWN SRD (ramp lever #1)

## Story Details
- **ID:** 106-1
- **Jira Key:** (none — this project uses content YAML tracking, not Jira)
- **Workflow:** tdd (phased: setup → red → green → review → finish)
- **Stack Parent:** none (independent story)
- **Repos:** sidequest-server (develop), sidequest-content (develop)
- **Branch Strategy:** gitflow

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-13T21:18:04Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-13T20:46:58Z | 2026-06-13T20:49:50Z | 2m 52s |
| red | 2026-06-13T20:49:50Z | 2026-06-13T21:01:32Z | 11m 42s |
| green | 2026-06-13T21:01:32Z | 2026-06-13T21:10:38Z | 9m 6s |
| review | 2026-06-13T21:10:38Z | 2026-06-13T21:18:04Z | 7m 26s |
| finish | 2026-06-13T21:18:04Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `warrior_kit.armor: [leather_armor, shield_wood, helmet_iron]` rolls exactly ONE item (`equipment_tables.yaml` has no `rolls_per_slot.armor` → default 1), so a Warrior can roll `shield_wood` or `helmet_iron` **alone**, not just leather. If the content PR only adds `armor_class` to `leather_armor`, ~2/3 of Warriors hit the loud-fail path. Affects `sidequest-content/genre_packs/caverns_and_claudes/inventory.yaml` (add `armor_class` to all three armor entries per the WWN SRD) and `equip_starting_armor` (the which-armor-rolled / combination rule). *Found by TEA during test design.*
- **Question** (non-blocking): WWN models a **shield** as a flat **AC bonus** on top of body armor and a **helmet** as no base-AC change — they are not standalone "base AC" items. Since the kit rolls a single armor piece, a shield-only or helmet-only Warrior has no body armor to set AC. The SRD-faithful rule for a sole shield/helmet roll (base 10 + shield bonus? re-roll? treat as unarmored-with-bonus?) needs Keith's ruling — the story context already flags multi-piece combination as SRD/Keith territory. Affects `equip_starting_armor` derivation rule + content semantics. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): `helmet_iron` is in `warrior_kit.armor` (a 1-roll slot) but WWN has **no helmet base-AC**, so I left it WITHOUT `armor_class` — a Warrior who rolls it alone (~1/3 of the time, since the slot is `[leather_armor, shield_wood, helmet_iron]`) now hits the loud-fail path and fights at AC 10 with a `chargen.armor_class_missing` warning. This is correct No-Silent-Fallback behavior but leaves a real ~1/3 survivability hole for the playgroup. **Recommend Keith pick one:** (a) drop `helmet_iron` from the `warrior_kit.armor` roll slot (helmets aren't body armor), (b) model shield/helmet as **+AC modifiers** layered on body armor (the deferred multi-piece combination rule), or (c) accept the loud-fail. Affects `sidequest-content/.../equipment_tables.yaml` (`warrior_kit.armor`) + a future `equip_starting_armor` combination rule. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `shield_wood` was given `armor_class: 13` (WWN shield as a sole defence). The WWN "+1 when worn WITH body armor" rule is **not** implemented — moot today because the kit rolls a single piece, but the future multi-piece story must add best-armor + shield-bonus combination in `equip_starting_armor` (it currently derives AC from the first armor item carrying a catalog `armor_class`). *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): `helmet_iron` (and `chain_shirt`) are `category: armor` with no `armor_class`. `helmet_iron` IS in `warrior_kit.armor` → ~1/3 of Warriors roll it and fight at AC 10 (loud-fail warn+span). `chain_shirt` is NOT in any kit roll table (verified `equipment_tables.yaml` — warrior `[leather_armor, shield_wood, helmet_iron]`, expert `[leather_armor]`, mage `[]`), so it is harmless today but would loud-fail if a future kit adds it. Corroborated independently by reviewer-security. Engine behavior is correct (loud-fail); this is a **content/design** decision for Keith (the helmet/shield bonus-semantics question already raised by TEA + Dev). Affects `sidequest-content/.../inventory.yaml` + `equipment_tables.yaml`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): add a pydantic field validator to `CatalogItem.armor_class` (`sidequest-server/sidequest/genre/models/inventory.py:164`), e.g. `ge=1, le=30`, so a malformed or nonsensical content value (`armor_class: 0`, negative, or a string) is rejected at pack-load rather than silently setting AC to a bad value at chargen. Covers the `armor_class: 0 → AC 0` edge the engine does not currently guard (`catalog_ac is None` is the only check). Hardening, not a live bug (no such content exists). Affects `genre/models/inventory.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC-3 reprisal-vs-AC: pinned upstream field + reused existing e2e for the downstream read**
  - Spec source: context-story-106-1.md, AC-3
  - Spec text: "the opponent reprisal reads the recomputed AC (dice.py:1636); the ENCOUNTER_OPPONENT_ATTACK span shows target_ac = the equipped value (13), not 10"
  - Implementation: pinned the upstream half (`test_derived_ac_lands_on_the_field_the_reprisal_reads` — chargen raises `core.armor_class`, the exact field dice.py:1636 reads); the downstream half (reprisal rolls vs `player_core.armor_class`) is already proven by `tests/integration/test_opponent_reprisal_e2e.py`, which forces hit/miss by setting the player's AC. No new full-encounter reprisal test authored.
  - Rationale: a new encounter+cdef+snapshot reprisal test would duplicate existing coverage of the read; 106-1 only adds the *write* (chargen setting AC).
  - Severity: minor
  - Forward impact: if the reprisal stops reading `core.armor_class`, the existing e2e (not this story's tests) is the guard.
- **Multi-piece / sole-shield armor combination not tested — single body-armor (leather) only**
  - Spec source: context-story-106-1.md, Technical Approach + Scope
  - Spec text: "If multiple armor pieces are equipped (torso + shield + helm) … resolve from the SRD, not by guessing"
  - Implementation: tests cover the single-armor (leather) derivation only; shield-only / helmet-only / multi-piece combination is not pinned.
  - Rationale: the kit rolls exactly one armor item (see Delivery Finding), so multi-piece doesn't arise from the kit; the sole-shield/helmet semantics need a Keith ruling and are out of this story's confirmed scope. Captured as a Delivery Finding instead of an invented test.
  - Severity: minor
  - Forward impact: Dev + content must resolve the sole-shield/helmet case before a Warrior who rolls one is testable; flagged for Keith.
- **Loud-fail implemented as WARNING + error span (not a raised exception)**
  - Spec source: context-story-106-1.md, AC-4
  - Spec text: "a kit armor item with no catalog armor_class fails loud (warn/error span) and does NOT silently leave the PC at AC 10"
  - Implementation: tests assert a WARNING log + `chargen.armor_class_missing` span (AC stays 10 loudly), mirroring the sibling `chargen.starting_equipment_missing` pattern — not a raised exception that would abort chargen.
  - Rationale: a content gap must not crash a player's chargen; the codebase surfaces chargen content gaps loudly via warn+span, not exceptions.
  - Severity: minor
  - Forward impact: none — matches established No-Silent-Fallback chargen pattern.
- **RED is a single collection ImportError, not N independently-collectable failures**
  - Spec source: TDD RED convention
  - Spec text: tests must fail before implementation
  - Implementation: the module imports `equip_starting_armor` at top level, so the whole file REDs at collection until the contract symbol exists; the 18 tests then fail/pass granularly once it does.
  - Rationale: top-level import keeps "the test is the spec" unambiguous (one clear "implement me" signal); the span-constant imports are inside their tests so they fail granularly post-collection.
  - Severity: minor
  - Forward impact: Dev sees one collection error first, then 18 granular tests after stubbing the symbol.

### Dev (implementation)
- **Derivation reads the FIRST armor item carrying a catalog `armor_class` (single-piece assumption)**
  - Spec source: context-story-106-1.md, Technical Approach
  - Spec text: "If multiple armor pieces are equipped (torso + shield + helm) … state the WWN-faithful combination rule … resolve from the SRD"
  - Implementation: `equip_starting_armor` equips every `category == "armor"` item but derives `core.armor_class` from the FIRST armor item with a non-None catalog `armor_class` (no best-armor / shield-bonus combination).
  - Rationale: the kit rolls a single armor piece (`warrior_kit.armor` has no `rolls_per_slot` override → 1), so multi-piece never arises in scope; implementing a combination rule now would be unverified speculation against an unruled SRD question (flagged for Keith).
  - Severity: minor
  - Forward impact: the deferred multi-piece story must replace "first armor with armor_class" with a best-armor + shield-bonus rule (see Delivery Findings).
- **helmet_iron content left without `armor_class` (loud-fail), not given an invented value**
  - Spec source: context-story-106-1.md, Scope ("leather_armor mandatory; … helmet_iron if the multi-piece rule needs them") + standing ruling (WWN SRD, no invented numbers)
  - Spec text: "Source the value from the WWN SRD armor table, not an invented number"
  - Implementation: added `armor_class` to `leather_armor` (13) and `shield_wood` (13) — both have WWN SRD values — but NOT to `helmet_iron`, which has no WWN base-AC. A helmet-only roll therefore loud-fails rather than receiving a fabricated number.
  - Rationale: the standing ruling forbids inventing AC values; a helmet has no SRD base-AC, so loud-fail is the honest outcome (surfaces the content/design question rather than masking it).
  - Severity: minor
  - Forward impact: ~1/3 of Warriors (helmet roll) stay at AC 10 + warning until Keith rules on the helmet slot (see Delivery Findings).

### Reviewer (audit)
All six logged deviations (4 TEA + 2 Dev) reviewed:
- **TEA — AC-3 reuse existing e2e for the reprisal read** → ✓ ACCEPTED: verified `tests/integration/test_opponent_reprisal_e2e.py` already forces hit/miss by setting the player's AC, proving the reprisal reads `core.armor_class`; this story only adds the write. A duplicate full-encounter test would add no coverage. Sound.
- **TEA — multi-piece/sole-shield not tested (leather only)** → ✓ ACCEPTED: `warrior_kit.armor` rolls exactly one piece (no `rolls_per_slot.armor`), so multi-piece never arises in scope. Correct to defer rather than invent against an unruled SRD question.
- **TEA — loud-fail as WARNING + span, not a raise** → ✓ ACCEPTED: verified the sibling `chargen.starting_equipment_missing` (chargen_loadout.py:194-204) uses the identical warn+span pattern; raising mid-chargen would regress consistency and crash a player over a content gap. Matches AC-4 ("fails loud (warn/error span)"). This directly refutes reviewer-security finding #1's "should raise" recommendation.
- **TEA — RED as single collection ImportError** → ✓ ACCEPTED: standard TDD; harmless, resolved at GREEN.
- **Dev — derivation reads the FIRST armor with a catalog armor_class (single-piece)** → ✓ ACCEPTED: correct for the 1-roll kit; the multi-piece best-armor+shield-bonus rule is a documented follow-up.
- **Dev — helmet_iron left without armor_class (loud-fail, no invented value)** → ✓ ACCEPTED: SRD-faithful (helmet has no WWN base-AC) and the standing ruling forbids invented numbers; the loud-fail correctly surfaces it. The product impact (~1/3 Warriors at AC 10) is captured as a non-blocking content finding for Keith — not a code defect.

No undocumented deviations found — the diff matches the logged design decisions.

**Setup Exit Gate:** READY

**Context Available:** Yes — story context at `sprint/context/context-story-106-1.md` (Architect-authored, comprehensive).

**Branch Strategy:** gitflow (feat/106-1-equip-starting-armor-wwn-ac on both server and content develop branches).

**Workflow Type:** phased (tdd: setup → red → green → review → finish).

**Next Agent:** tea-red (first phase after setup in the phased tdd workflow).

**Notes:**
- No Jira claim required (this project uses content YAML tracking, JIRA_KEY intentionally empty).
- Story context already exists; not overwritten.
- Two coordinated subrepos (server + content) require parallel PRs to develop branches.
- AAC context: WWN Warrior armor-derivation (chargen) + opponent reprisal AC proof (OTEL). See context doc for full technical scope and acceptance criteria.

## TEA Assessment

**Tests Required:** Yes
**Reason:** behavioral bug + new derivation step + new OTEL spans — full RED coverage warranted (not a chore bypass).

**Test Files:**
- `sidequest-server/tests/server/test_106_1_chargen_armor_equip.py` — 18 tests covering AC-1…AC-5, the OTEL gate, SPAN_ROUTES registration, and a real-pack wiring test.

**Tests Written:** 18 tests covering all 5 ACs.
**Status:** RED (verified — `uv run pytest tests/server/test_106_1_chargen_armor_equip.py -n0` → collection `ImportError: cannot import name 'equip_starting_armor'`, the contract symbol). All 18 gate behind it and fail granularly once the symbol + spans + content land.

**The contract these tests pin (Dev implements to satisfy):**
- New `equip_starting_armor(character, inventory_config, *, genre="", world="", player_id="") -> int` in `sidequest/server/dispatch/chargen_loadout.py`, called from the chargen-confirm wire `chargen_mixin.py:1239` **after** `apply_starting_loadout`. Equips the kit-rolled armor (category `armor`), recomputes `core.armor_class` from the equipped armor's `CatalogItem.armor_class`, returns the resulting AC.
- New spans: `SPAN_CHARGEN_ARMOR_EQUIPPED = "chargen.armor_equipped"` (attrs: `armor_item_id`, `armor_class`, `ac_before`, `ac_after`, `equipped`, + genre/world/player_id) and `SPAN_CHARGEN_ARMOR_CLASS_MISSING = "chargen.armor_class_missing"` (attrs incl. `armor_item_id`) — both registered in `SPAN_ROUTES`.
- Content (sidequest-content): add WWN-SRD `armor_class` to `caverns_and_claudes/inventory.yaml` armor entries (leather = 13; **see Delivery Finding — all three of leather/shield/helmet can roll, cite the SRD row in the content PR**).
- Loud-fail (warn + missing-span) when the equipped armor has no catalog `armor_class`; AC stays 10 loudly, never silently, never invented.

**Test map (AC → test):**
| AC | Test(s) |
|----|---------|
| AC-1 armor equips | `test_kit_armor_is_equipped_at_chargen` |
| AC-2 AC from SRD/content | `test_armor_class_derived_from_catalog_value`, `test_armor_class_follows_content_not_a_hardcoded_constant` |
| AC-3 reprisal reads AC | `test_derived_ac_lands_on_the_field_the_reprisal_reads` (+ existing `test_opponent_reprisal_e2e.py` for the read — see deviation) |
| AC-4 no silent fallback | `test_missing_catalog_armor_class_fails_loud`, `test_missing_catalog_armor_class_does_not_invent_an_ac`, `test_armor_class_missing_span_fires_on_content_gap` |
| AC-5 no regression | `test_unarmored_character_stays_at_ac_10`, `test_weapon_items_are_not_touched_by_the_armor_step`, `test_idempotent_on_already_equipped_armor` |
| OTEL gate | `test_armor_equipped_span_fires_with_attributes`, `test_armor_equipped_span_does_not_fire_for_unarmored` |
| SPAN routing | `TestArmorSpanRouting::*` (3 tests) |
| Wiring (real pack) | `test_real_warrior_armor_equips_and_derives_against_real_content` |

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #1/#4 no silent fallback → error path logs | `test_missing_catalog_armor_class_fails_loud` (asserts WARNING) + `test_armor_class_missing_span_fires_on_content_gap` | RED |
| #6 test quality (meaningful assertions) | self-checked — every test asserts a specific value; no `assert True`, no bare-truthy, no assertion-free tests | pass |
| OTEL discipline (CLAUDE.md) | `chargen.armor_equipped` gate span + SPAN_ROUTES registration + routing-completeness lint | RED |
| No source-text wiring tests (CLAUDE.md) | wiring proven via real-pack OTEL span + fixture behavior, not `read_text()`/grep | pass |

**Rules checked:** 4 of 13 applicable (the rest — mutable defaults, async, deserialization, paths, resource leaks, imports — are not exercised by this story's surface; they apply to the Dev's implementation and are the lang-review gate's job at review).
**Self-check:** 0 vacuous tests (all assertions check specific values/spans).

**Wiring test:** `test_real_warrior_armor_equips_and_derives_against_real_content` builds a real Warrior through the real `CharacterBuilder` against the real `caverns_and_claudes` pack and runs the production `equip_starting_armor` against the real catalog — RNG-robust (asserts against whichever of leather/shield/helmet rolled) and exercises BOTH halves of the two-sided gap. **Dev:** the chargen-confirm call site (`chargen_mixin.py:1239`) is where the new call belongs; consider upgrading this wiring test in the verify/GREEN phase to drive the confirm handler and assert the span fires through the production confirm path.

**Handoff:** To Agent Smith (Dev) for GREEN. Two coordinated PRs (server code + content YAML) — the AC-2/wiring tests depend on the content `armor_class` value, so land both together.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 16/16 passing (GREEN) — `uv run pytest tests/server/test_106_1_chargen_armor_equip.py -n0` → 16 passed. (TEA's "18" was an overcount; the file has 16 test functions.)

**Files Changed:**
- `sidequest-server/sidequest/server/dispatch/chargen_loadout.py` — new `equip_starting_armor(character, inventory_config, *, genre, world, player_id) -> int`: equips `category == "armor"` kit items, derives `core.armor_class` from the equipped item's catalog `armor_class`, loud-fails (warn + `chargen.armor_class_missing` span) on a missing catalog value, emits `chargen.armor_equipped` on success.
- `sidequest-server/sidequest/telemetry/spans/chargen.py` — new `SPAN_CHARGEN_ARMOR_EQUIPPED` + `SPAN_CHARGEN_ARMOR_CLASS_MISSING` constants with `SPAN_ROUTES` entries (state_transition / character_creation).
- `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py` — wired `equip_starting_armor` into the chargen-confirm path immediately after `apply_starting_loadout` (shares the resolved `loadout_inventory`).
- `sidequest-server/tests/server/test_106_1_chargen_armor_equip.py` — lint/format fixup of TEA's suite (getattr→attr; identical assertion).
- `sidequest-content/genre_packs/caverns_and_claudes/inventory.yaml` — WWN-SRD `armor_class: 13` on `leather_armor` and `shield_wood` (helmet left without — see Delivery Findings).

**Branches (pushed):**
- sidequest-server `feat/106-1-equip-starting-armor-wwn-ac` @ `d937d912`
- sidequest-content `feat/106-1-equip-starting-armor-wwn-ac` @ `27e8a33`

**Quality gates:**
- 106-1 suite: 16/16 green (incl. real-pack wiring test — ran, not skipped).
- Regression: `test_chargen_loadout.py` + routing-completeness lint + `test_chargen_dispatch.py` + `test_cc_chargen_e2e.py` → 36 passed, 20 skipped (graceful DB skips). Combat: `test_opponent_reprisal_e2e.py` + `test_wwn_caverns_dispatch.py` → 14 passed.
- ruff: clean (changed files). format: clean (changed files). pyright: my new code 0 errors; the 16 `chargen_mixin.py` errors are the pre-existing mixin `_room`-access pattern, none in my edit range.

**Self-review:**
- Wired end-to-end: the new step runs in the production chargen-confirm path (`chargen_mixin`), proven by the real-pack OTEL-span test — not just unit-reachable.
- Follows project patterns: mirrors `apply_starting_loadout`'s span+warn loud-fail shape; spans registered in `SPAN_ROUTES` per OTEL discipline.
- ACs met: AC-1..AC-5 all green; AC-3 upstream pinned + existing reprisal e2e covers the read.
- No silent fallbacks: missing catalog `armor_class` → loud warn + span, AC stays 10 (never invented).

**Two open items for Keith (see Delivery Findings):** the `helmet_iron` slot (no WWN base-AC → ~1/3 of Warriors loud-fail at AC 10) and the deferred shield/multi-piece +AC combination rule.

**Handoff:** To The Architect (TEA) for the verify phase (simplify + quality-pass).

---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 blocking (48/48 tests green, ruff+format clean; 1 advisory note) | confirmed 0, dismissed 0, deferred 0 (1 note verified) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings (test quality assessed by Reviewer — see Rule Compliance) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (type review by Reviewer — `int|None` boundary verified) |
| 7 | reviewer-security | Yes | findings | 5 (2 "high", 3 "med") | confirmed 1 (downgraded to non-blocking), dismissed 4 (with rationale) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 enabled subagents returned; 7 disabled and pre-filled)
**Total findings:** 1 confirmed (non-blocking), 4 dismissed (with rationale), 0 deferred

### Security finding dispositions (reviewer-security)
- **#1 "silent fallback on missing armor_class — should raise" (HIGH)** → **DISMISSED as a violation; substance retained as non-blocking content finding.** The premise is factually wrong: the path emits a WARNING **and** a `chargen.armor_class_missing` OTEL span — that is not silent. It is the codebase's established loud-fail-for-chargen-content-gaps convention (sibling `chargen.starting_equipment_missing`, chargen_loadout.py:194-204, warns+spans, does not raise) and is exactly what AC-4 specifies: *"fails loud (warn/error span) and does NOT silently leave the PC at AC 10."* The "raise instead" recommendation would crash a player's chargen over a content gap and contradict the sibling pattern. The real substance (helmet/chain content gap, product impact) is captured as a non-blocking finding for Keith.
- **#4 "chain_shirt missing armor_class — silent fallback when in a kit" (HIGH)** → **DISMISSED.** Premise verified false: `chain_shirt` is not in any kit roll table (`warrior_kit.armor=[leather_armor,shield_wood,helmet_iron]`, `expert_kit.armor=[leather_armor]`, `mage_kit.armor=[]`). It never reaches `equip_starting_armor` via a kit, so the path is dead. If a future kit adds it, the loud-fail surfaces it. Defensive `armor_class: 15` noted as a non-blocking improvement.
- **#5 "helmet_iron missing armor_class — mis-categorised" (MED)** → **CONFIRMED (non-blocking).** Real content gap, corroborates TEA+Dev. Engine handles it correctly (loud-fail); the remediation (re-categorise helmet / model as +modifier) is Keith's content/design call. In Delivery Findings.
- **#2 "player_id in span attributes = PII" (MED)** → **DISMISSED.** Pre-existing project-wide pattern (player_id is in 10 existing chargen-span attribute sets, incl. the sibling `starting_equipment_missing`); not introduced by this story. Personal LAN project (CLAUDE.md), OTEL → local GM panel. Not a regression; any change belongs in a project-wide telemetry-privacy story.
- **#3 "unguarded int() coercion footgun" (MED)** → **DISMISSED as a runtime risk; retained as a hardening improvement.** `CatalogItem.armor_class` is typed `int | None` (inventory.py:164), so pydantic rejects malformed values at pack-LOAD — `int(catalog_ac)` only ever sees `int|None` at runtime. The agent's "malformed YAML reaches int()" scenario cannot occur. The suggested `ge=1` field validator is a good hardening (also closes the `armor_class: 0 → AC 0` edge) → captured as a non-blocking Delivery Finding.

## Rule Compliance

Rules enumerated against every changed type/function/content item (lang-review/python.md + CLAUDE.md + SOUL.md):

- **No Silent Fallbacks (CLAUDE.md/SOUL.md)** — `equip_starting_armor` paths: (a) `inventory_config is None` → returns unchanged AC (consistent with `apply_starting_loadout`'s None no-op) ✓; (b) no armor item → returns unchanged AC (correct — unarmored classes stay 10) ✓; (c) armor with no catalog `armor_class` → **WARNING + `chargen.armor_class_missing` span**, AC stays 10 loudly ✓ (NOT silent — mirrors sibling at :194-204). **COMPLIANT.**
- **No invented mechanical numbers (standing ruling 2026-06-13)** — AC derived solely from `catalog_item.armor_class`; no engine-side AC constant. Content values `13`/`13` sourced from WWN SRD armor table with citation comments. **COMPLIANT** (1 function + 2 content items checked).
- **OTEL Observability Principle (CLAUDE.md)** — both decisions emit spans: success `chargen.armor_equipped` (ac_before/after, item id, equipped) + failure `chargen.armor_class_missing`; both registered in `SPAN_ROUTES` and proven by `test_routing_completeness_still_passes`. **COMPLIANT.**
- **python.md #1 silent exceptions** — no bare/`pass` except in diff. **COMPLIANT.**
- **python.md #3 type annotations** — `equip_starting_armor` fully annotated (params + `-> int`). **COMPLIANT.**
- **python.md #4 logging** — `logger.warning` with `%s/%d` lazy args (not f-strings); warning level correct for a content gap. **COMPLIANT.**
- **python.md #6 test quality** — 16 tests, every one asserts a specific value/span; no `assert True`, no bare-truthy, no assertion-free tests; the one `pytest.skip` (line 454) is a legit content-availability guard, not a smell (confirmed by preflight). **COMPLIANT.**
- **python.md #8 unsafe deserialization** — no `yaml.load`/`eval`/`pickle` in diff; content loaded via the pack loader (safe) upstream. **COMPLIANT.**
- **No source-text wiring tests (CLAUDE.md)** — wiring proven by real-pack OTEL-span test + fixture behavior, no `read_text()`/grep. **COMPLIANT.**

## Devil's Advocate

Argue this code is broken. **Angle 1 — the bug isn't actually fixed for a third of Warriors.** `warrior_kit.armor` rolls one of three items with equal weight; `helmet_iron` has no `armor_class`, so ~33% of fresh Warriors still walk into the Dropmouth at AC 10 — the exact lethality the story exists to kill. A skeptic says "ramp lever #1 only pulls two-thirds of the way." *Rebuttal:* the engine is correct and loud (warn+span); the helmet has no WWN base-AC to assign (inventing one violates the standing ruling), so this is a content/design decision explicitly deferred to Keith and captured in three independent findings. The story scope made *leather* mandatory (done) and others conditional. Rejecting would have no spec-aligned fix — there is no number to add. **Angle 2 — state corruption via armor_class: 0.** If a content author writes `armor_class: 0`, `catalog_ac is None` is False, so AC is set to 0 (always-hit). *Rebuttal:* no such content exists; pydantic accepts it but a `ge=1` validator (filed as a non-blocking improvement) is the right fix at the load boundary. Real but latent, content-only, non-blocking. **Angle 3 — a confused player wears "chain mail" at AC 10.** *Rebuttal:* `chain_shirt` is not in any kit roll table (verified), so it cannot be issued today; the loud-fail covers any future addition. **Angle 4 — idempotency/reload.** Could re-running corrupt AC? *Rebuttal:* `equip_starting_armor` runs only in the chargen-confirm path (not on save reload), and the idempotency test proves a second pass holds AC at 13. **Angle 5 — multi-armor over-equip.** The loop equips every armor item but derives from the first. *Rebuttal:* the kit rolls one; documented single-piece assumption; multi-piece is a filed follow-up. Conclusion: every "broken" angle resolves to either a verified-false premise or a known, flagged, non-blocking content/design item. No code defect blocks.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `inventory.yaml` armor catalog (`armor_class: 13`) → `resolve_inventory` → `equip_starting_armor` filters `category=="armor"` items → `catalog_item.armor_class` → `core.armor_class` mutation + `chargen.armor_equipped` span → read by the opponent reprisal at `dice.py:1636` (`target_ac = int(player_core.armor_class)`). Safe: the value originates in content (no invented constant), the mutation is observable (span), and the consumer is pre-existing + already tested.

**Dispatch-tagged observations:**
- `[PRE]` Preflight: 48/48 tests green (16 story + 30 sibling loadout + 2 routing lint), ruff clean, format clean. No blockers. Advisory `chain_shirt` note resolved (not kit-rolled).
- `[SEC]` Security finding #5 CONFIRMED non-blocking: `helmet_iron`/`chain_shirt` content `armor_class` gap → product impact (~1/3 Warriors at AC 10), flagged for Keith. Findings #1/#4 dismissed (false "silent"/"in-kit" premises); #2/#3 dismissed (pre-existing pattern / pydantic-guaranteed boundary), #3's validator idea retained as a hardening improvement.
- `[EDGE]` Disabled (settings). Reviewer-checked boundaries: None config, no-armor, missing-AC, multi-armor, idempotent re-run, `armor_class: 0` (latent, non-blocking) — all handled or filed.
- `[SILENT]` Disabled (settings). Reviewer-checked: the only fallthrough (`catalog_ac is None`) emits warn+span+AC-stays-10 — verified NOT silent; matches sibling `starting_equipment_missing` (:194-204).
- `[TEST]` Disabled (settings). Reviewer-checked: all 16 tests assert specific values/spans; coverage spans AC-1..AC-5 + OTEL gate + routing + real-pack wiring. No vacuous assertions.
- `[DOC]` Disabled (settings). Reviewer-checked: docstring + content comments cite WWN SRD and scope boundaries accurately; no stale/misleading comments.
- `[TYPE]` Disabled (settings). Reviewer-checked: `CatalogItem.armor_class: int|None` validated at load; `equip_starting_armor` fully typed; `core.armor_class` mutation type-safe.
- `[SIMPLE]` Disabled (settings). Reviewer note: `catalog_by_id` is rebuilt here (also built in `apply_starting_loadout`) — minor, acceptable for two independent functions; not worth coupling them.
- `[RULE]` Disabled (settings). Reviewer-checked exhaustively — see Rule Compliance: all applicable python.md + CLAUDE.md + SOUL.md rules compliant.

**Pattern observed:** the new loud-fail mirrors the established `chargen.starting_equipment_missing` warn+span pattern (`chargen_loadout.py:194-204`) — consistent, OTEL-observable. Good pattern adherence.

**Error handling:** content gap → `logger.warning` + `chargen.armor_class_missing` span, AC held at the unarmored default (loud, not silent). None/empty inventory → safe early returns. No unhandled exception paths (pydantic guarantees the `int|None` boundary).

**Wiring:** `equip_starting_armor` imported and called in the production chargen-confirm path (`chargen_mixin.py`) immediately after `apply_starting_loadout` on a shared `loadout_inventory`; proven end-to-end by the real-pack OTEL-span test.

**Non-blocking follow-ups (for Keith / future stories):** helmet/shield bonus-semantics + `helmet_iron` armor slot ruling; defensive `chain_shirt: armor_class 15`; `CatalogItem.armor_class` `ge=1` pydantic validator. All in Delivery Findings.

**Handoff:** To Morpheus (SM) for finish-story.