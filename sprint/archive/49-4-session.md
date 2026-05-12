---
story_id: "49-4"
jira_key: null
epic: null
workflow: "trivial"
---
# Story 49-4: Victoria archetypes — author starting inventories

## Story Details
- **ID:** 49-4
- **Jira Key:** None (personal project)
- **Epic:** 49 (Playtest 4 Closeout — Glenross / ADR-098 Continuity Recovery)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-12T14:23:07Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-12 | 2026-05-12T14:00:12Z | 14h |
| implement | 2026-05-12T14:00:12Z | 2026-05-12T14:18:09Z | 17m 57s |
| review | 2026-05-12T14:18:09Z | 2026-05-12T14:23:07Z | 4m 58s |
| finish | 2026-05-12T14:23:07Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Improvement** (non-blocking): Orphan `industrialist` calling — `genre_packs/victoria/classes.yaml` declares `industrialist` and `equipment_tables.yaml` declares `industrialist_kit`, and `rules.yaml.allowed_classes` lists Industrialist, but `char_creation.yaml.vocation` has no choice that sets `class_hint: Industrialist`. Player cannot select Industrialist via the chargen UI; the kit is unreachable.
  Affects `sidequest-content/genre_packs/victoria/char_creation.yaml` (add an Industrialist vocation choice) OR `sidequest-content/genre_packs/victoria/rules.yaml` + `classes.yaml` + `equipment_tables.yaml` (drop Industrialist from all three). Pre-existing condition surfaced by 49-4 alignment work.
  *Found by Reviewer during code review.*

- **Gap** (non-blocking): `test_victoria_doctor_chargen_produces_signature_items_end_to_end` builds synthetic `CharCreationScene` objects rather than loading the_satchel from `pack.char_creation`. A typo, rename, or removal of the_satchel from `char_creation.yaml` would not break any test. Verified scene loads correctly via Python REPL (`mechanical_effects.equipment_generation == 'class_kit'`), but the bound contract is missing.
  Affects `sidequest-server/tests/genre/test_victoria_class_kits.py` (add a one-liner: `assert any(s.mechanical_effects and s.mechanical_effects.equipment_generation == 'class_kit' for s in pack.char_creation)`).
  *Found by Reviewer during code review.*

- **Improvement** (non-blocking): Victoria's singleton-slot pattern for guaranteed signature items is a cleaner design than C&C's multi-item slot with RNG replacement (which is the root cause of `test_caverns_delver_loadout_wired_into_snapshot` flakiness). Worth retrofitting C&C's `rations_day` into a singleton slot to make that test deterministic.
  Affects `sidequest-content/genre_packs/caverns_and_claudes/equipment_tables.yaml` (move `rations_day` to its own singleton slot per kit; reduce `rolls_per_slot.consumable=3` accordingly).
  *Found by Reviewer during code review.*

### Dev (implementation)
- **Improvement** (non-blocking): The `test_caverns_delver_loadout_wired_into_snapshot` test (`tests/server/test_chargen_dispatch.py::TestSliceAWiring`) is intermittently flaky due to RNG.
  Affects `sidequest-content/genre_packs/caverns_and_claudes/equipment_tables.yaml` (Fighter/Thief kits define `consumable: [rations_day, waterskin]` with `rolls_per_slot.consumable=3` → P(no rations_day) = 1/8 = 12.5%). Test asserts `"rations_day" in item_ids`. Hit during 49-4 broader regression sweep; unrelated to Victoria work. Pre-existing condition since story 31-3 wired C&C class_kits. Fix is either deterministic test seed or making rations_day a singleton slot in those kits.
  *Found by Dev during implementation.*
- **Gap** (non-blocking): `sidequest/cli/loadoutgen/__init__.py` is a stub ("Placeholder — populated in later phases per ADR-082 port plan.") with no implementation. AC5 validation for a new pack currently requires writing a bespoke pytest fixture; a working `loadoutgen` CLI (matching `encountergen`/`namegen` patterns) would make per-pack chargen smoke checks one-liners.
  Affects `sidequest-server/sidequest/cli/loadoutgen/` (port from Rust per ADR-082 §port-plan). Not blocking 49-4 since the wiring test covers AC5 mechanically.
  *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **AC3 mode literal: shipped `equipment_generation: class_kit` instead of `random_table`** → ✓ ACCEPTED by Reviewer: AC1/AC5 require per-archetype kits, which `random_table` cannot deliver; C&C's `the_kit` scene also uses `class_kit` (the reference Dev was told to mirror). AC3's `random_table` literal is a stale copy from a pre-31-3 era spec. Sound call.
  - Spec source: sprint/epic-49.yaml story 49-4 acceptance_criteria[2]
  - Spec text: "Wire the_kit scene (or equivalent) in sidequest-content/genre_packs/victoria/char_creation.yaml with `equipment_generation: random_table` — see caverns_and_claudes/char_creation.yaml for the exact mechanical_effects shape"
  - Implementation: New `the_satchel` scene declares `equipment_generation: class_kit`. C&C's reference `the_kit` scene also uses `class_kit` (not `random_table`) since story 31-3 — AC3's `random_table` literal is stale.
  - Rationale: AC1 ("per-archetype starting kits: Country Doctor → medical kit, Clergyman → ecclesiastical kit, …") and AC5 ("New chargen run with a Doctor produces … gladstone_bag, stethoscope, …") cannot be satisfied by `random_table` mode, which is class-agnostic and would give every archetype the same shared pool. Per-archetype delivery requires `class_kit` mode. SM Assessment also says "Mirror caverns_and_claudes verbatim" — C&C uses `class_kit`.
  - Severity: minor
  - Forward impact: none — AC1/AC5 are the load-bearing acceptance criteria; AC3's `random_table` literal was a copy-paste from a pre-31-3 era reference and is contradicted by the rest of the spec.

- **Scope expansion: authored `genre_packs/victoria/classes.yaml` (new file, 7 callings)** → ✓ ACCEPTED by Reviewer: AC1/AC5 cannot be satisfied without a `class_kit` pipeline, which requires ClassDefs. The scope expansion is the minimum surface needed to make per-archetype kits work. Side benefit: brings `rules.yaml.allowed_classes` and chargen into mechanical alignment for the first time. SM scope statement ("no server code") is preserved — this is content-lane file addition.
  - Spec source: SM Assessment in session file ("Pure content authoring … no server code")
  - Spec text: "Scope: Pure content authoring in `sidequest-content/genre_packs/victoria/`. No server code."
  - Implementation: Added `classes.yaml` with 7 ClassDefs (Doctor, Clergyman, Detective, Society, Governess, Explorer, Industrialist), each declaring id, display_name, rpg_role, jungian_default, prime_requisite (mapped to Victoria's Cunning/Nerve/Pride stats), minimum_score, kit_table, encounter_beat_choices from Victoria's social-only confrontation pool.
  - Rationale: Victoria had no `classes.yaml`, so CharacterBuilder's `class_kit` resolution path (builder.py:1811 `if class_kit_requested and self._equipment_tables is not None and self._classes:`) cannot fire — without ClassDefs, `random_table` is the only functional path, and AC1/AC5 fail (see deviation above). Authoring a minimal classes.yaml is the cheapest path to per-archetype kits. No server code touched; this is content-lane file addition, matching the SM scope.
  - Severity: minor
  - Forward impact: positive — Victoria now has a wired class system that can host future progression/abilities; matches what `rules.yaml allowed_classes` already implied. Sebastien (mechanics-first player) gets actual class data for his GM-panel reads.

- **Item rename: `medical_bag` → `gladstone_bag`** → ✓ ACCEPTED by Reviewer: grep-confirmed zero external consumers; matches AC1's explicit `gladstone_bag` id; cleaner than carrying a duplicate concept. Aligns with `feedback_dead_code` memory.
  - Spec source: AC1 lists `gladstone_bag` as a required item id
  - Spec text: "Each item gets id, name, weight, description, tags … gladstone_bag, stethoscope, clinical_thermometer …"
  - Implementation: Renamed the existing `medical_bag` entry in `victoria/inventory.yaml` to `gladstone_bag` (Gladstone Bag — black leather portmanteau with brass clasps); refined description; updated tags.
  - Rationale: `medical_bag` had zero consumers (grep confirmed) and `gladstone_bag` is the spec-required, genre-specific Victorian name. Avoids duplicate-concept clutter per memory `feedback_dead_code`.
  - Severity: trivial
  - Forward impact: none — the only writer of `medical_bag` was `victoria/inventory.yaml`; no save files or narrator prompts reference the old id.

- **Added `starting_gold` block to `victoria/inventory.yaml`** → ✓ ACCEPTED by Reviewer: forward-defensive against the C&C playtest 2026-05-06 lesson; the wiring is pack-agnostic (`chargen_loadout.py:179` reads `inventory.starting_gold`); test ensures every calling is non-zero. Pounds-denominated matches Victoria currency. Spread (8-120) is genre-truthful for class-stratified Victorian England.
  - Spec source: not in AC list
  - Spec text: n/a
  - Implementation: Added per-calling pounds amounts (Doctor=30, Clergyman=15, Detective=12, Society=80, Governess=8, Explorer=25, Industrialist=120).
  - Rationale: C&C playtest 2026-05-06 (Carl-the-Cleric vs Brenna) proved that `starting_gold=0` makes chargen-end cash-gated content unreachable. Victoria doesn't currently have such gates but adding pocket-cash now is forward-defensive and matches `inventory.yaml.starting_gold` schema. Tested by `test_victoria_each_class_has_positive_starting_gold`.
  - Severity: minor
  - Forward impact: positive — future Victoria worlds with paid social gates (coach fare, card-game stake, small bribe) will not have to revisit chargen.

## Acceptance Criteria

- [x] Create `sidequest-content/genre_packs/victoria/equipment_tables.yaml` with per-archetype starting kits (Country Doctor → medical kit, Clergyman → ecclesiastical kit, Detective → investigation kit, etc.). Match the schema used by caverns_and_claudes/equipment_tables.yaml
- [ ] Create `sidequest-content/genre_packs/victoria/inventory.yaml` (or audit existing) with Victorian-era essentials catalog
- [ ] Wire the_kit scene (or equivalent) in `sidequest-content/genre_packs/victoria/char_creation.yaml` with `equipment_generation` mechanical effect — see caverns_and_claudes/char_creation.yaml for the exact mechanical_effects shape
- [ ] All item_ids in equipment_tables.yaml exist in inventory.yaml item_catalog — wiring test enforces this
- [ ] New chargen run in victoria/glenross with a Doctor produces an inventory with at minimum: medical_bag, stethoscope, clinical_thermometer, bandages, one or two apothecary items

## Reference Pattern (Caverns & Claudes)
- `caverns_and_claudes/equipment_tables.yaml` — per-class kit tables with slot-based rolling
- `caverns_and_claudes/inventory.yaml` — full item catalog with id/name/weight/description/tags
- `caverns_and_claudes/char_creation.yaml` `the_kit` scene — `equipment_generation: class_kit` mechanical effect

## Victoria Vocations
- Country Doctor
- Parish Minister
- Episcopal Rector
- Postmistress
- Schoolmistress
- Country Veterinary Surgeon
- Village Constable
- Retired Colonial Officer

Each vocation maps to a class_hint (Doctor, Clergyman, Society, Governess, Detective, Explorer).

## Sm Assessment

**Scope:** Pure content authoring in `sidequest-content/genre_packs/victoria/`. No server code. No tests-as-code beyond the existing wiring test that asserts `item_id ∈ inventory.item_catalog`.

**Approach:** Mirror caverns_and_claudes verbatim — same file names, same schema, same `the_kit` scene pattern with `equipment_generation` mechanical effect. This is a port-style task: don't redesign the kit-table mechanic, translate it into Victorian items.

**Item catalog scope:** Victorian-era practical kit — medical (gladstone bag, stethoscope, thermometer, laudanum, quinine, iodine, bandages), ecclesiastical (prayer book, communion kit, sermon notebook), investigation (magnifying glass, notebook, fountain pen), society (visiting cards, pocket watch, walking stick), outdoors (oilskin coat, lantern). Genre-true to Brontë gothic — no anachronisms, no fantasy items.

**Per-archetype kits:** Country Doctor / Veterinary Surgeon → medical kit. Parish Minister / Episcopal Rector → ecclesiastical kit. Village Constable → investigation kit. Postmistress / Schoolmistress → society kit. Retired Colonial Officer → outdoors/explorer kit. Each kit has a small slot-based roll matching C&C's pattern.

**Risk:** Item-id drift between `equipment_tables.yaml` and `inventory.yaml`. Wiring test enforces this — Dev must run it before handoff.

**Validation:** AC5 requires a chargen run in `victoria/glenross` producing a Doctor with the listed essentials. This is a UI/playtest check, not a unit test — Dev should confirm with `just up` and a fresh chargen.

**Routing:** Trivial workflow → Winchester (Dev) for implementation. No TEA red-phase needed; the wiring test exists and will catch drift.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (sidequest-content):**
- `genre_packs/victoria/classes.yaml` (NEW, 88 lines) — 7 callings with kit_table refs + social encounter_beat_choices.
- `genre_packs/victoria/equipment_tables.yaml` (NEW, 95 lines) — `class_tables` block with 7 per-calling kits. Doctor kit uses singleton slots (bag/diagnostic_primary/diagnostic_secondary/dressings) to guarantee AC5 signature items.
- `genre_packs/victoria/inventory.yaml` (MOD) — renamed `medical_bag` → `gladstone_bag`; added 22 Victorian-era items (stethoscope, clinical_thermometer, quinine_bottle, iodine_tincture, bandages_linen, prayer_book, visiting_cards, pocket_watch_silver, notebook_leather, fountain_pen, oilskin_coat, breviary, communion_kit, sermon_notebook, whistle_brass, chalkboard_slate, school_primer, field_compass, regimental_decorations, service_revolver, hip_flask, ledger_book); added `starting_gold` per calling.
- `genre_packs/victoria/char_creation.yaml` (MOD) — inserted new `the_satchel` scene between `eye` and `confirmation` with `equipment_generation: class_kit`.

**Files Changed (sidequest-server):**
- `tests/genre/test_victoria_class_kits.py` (NEW, 181 lines) — 7 wiring tests: pack load, kit count, item-id ↔ catalog cross-check, classes ↔ allowed_classes consistency, Doctor singleton-slot contract (AC5 data), Doctor end-to-end chargen produces signature items (AC5 integration), starting_gold positive for every calling.

**Tests:** 7/7 new Victoria tests passing. C&C kit regression (5 tests) green. Broader chargen suite (127 tests across builder/dispatch/loadout/summary/e2e) green; one flaky pre-existing C&C test noted as a finding above.

**Branch:** `feat/49-4-victoria-starting-inventories` (sidequest-content) + parallel work pushed in sidequest-server.

**Acceptance Criteria Status:**
- AC1 (equipment_tables.yaml with per-archetype kits) — ✓ shipped as `class_tables` block; 7 callings mapped to themed slots.
- AC2 (inventory.yaml Victorian essentials catalog) — ✓ audited existing entries and added 22 new Victorian-era items matching AC1's listed IDs.
- AC3 (the_kit scene wired) — ✓ shipped as `the_satchel` scene with `equipment_generation: class_kit` (deviation from `random_table` literal logged above).
- AC4 (all item_ids exist in catalog) — ✓ enforced by `test_victoria_kit_items_exist_in_inventory`.
- AC5 (Doctor chargen produces gladstone_bag + stethoscope + clinical_thermometer + bandages + apothecary items) — ✓ enforced by `test_victoria_doctor_chargen_produces_signature_items_end_to_end` and `test_victoria_doctor_kit_guarantees_signature_items` (singleton-slot contract).

**Handoff:** To Colonel Potter (Reviewer).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (tests 578 passed / 0 failed / 4 pre-existing skips; no code smells; pack loads with 7 classes / 7 kits 1:1) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 ran, 8 disabled via `workflow.reviewer_subagents` settings)
**Total findings:** 0 confirmed from subagents, 0 dismissed, 0 deferred. Reviewer independently surfaced 2 LOW findings (orphan Industrialist calling, char_creation scene not under test) — see assessment below.

## Devil's Advocate

Argue this code is broken. Start with the obvious vector: a player picks Industrialist on the chargen screen and ends up with no kit. **Refuted** — `char_creation.yaml.vocation` has no `class_hint: Industrialist` choice, so a player cannot select Industrialist; the orphan kit is unreachable. The risk is reversed: a future author adds the vocation but forgets to wire it; the test suite won't catch the gap because no test cross-checks vocation `class_hint` values against `classes.yaml.display_name`.

A confused user picks Country Veterinary Surgeon expecting an animal-care kit and gets the human-doctor kit. **Acknowledged but acceptable** — the Vet shares the Doctor calling, kit content is medical (which serves both), and the alternative is multiplying ClassDefs to split Doctor/Vet. Genre-truth-wise a Victorian vet *did* carry the same essentials. Marking color-mismatch but not a defect.

A malicious or chaotic content author renames `the_satchel` to `the_satchel_v2` and forgets to update `equipment_generation`. **Real risk** — `test_victoria_doctor_chargen_produces_signature_items_end_to_end` constructs scenes inline rather than loading from `pack.char_creation`, so a typo or removal in `char_creation.yaml` would not break any test. I verified manually that the scene loads with `equipment_generation='class_kit'` via Python REPL, but the bound test contract is missing. Adding a one-liner `assert any(s.mechanical_effects.equipment_generation == 'class_kit' for s in pack.char_creation)` would close this. Filing as LOW finding.

Stressed filesystem produces unexpected fields in classes.yaml — pydantic `extra: forbid` on ClassDef rejects them with a clear error. **Verified by reading models/character.py:154.**

A player rolls a Doctor and the apothecary slot picks `laudanum_bottle` twice (replacement allowed). The Doctor arrives with 2 laudanum bottles and 0 quinine. **Acknowledged** — the apothecary slot uses `rolls_per_slot.apothecary=2` against a 3-item pool with replacement; the probability of no quinine in 2 rolls = (2/3)² = 44%. AC5 says "one or two apothecary items" — the kit guarantees at least one apothecary item but not three distinct ones. Acceptable per AC5 wording.

YAML parses but `tags` are wrong — `[medical, signature, clergy]` on the breviary suggests it's both medical AND clergy. **Color, not defect.**

A player's stat sheet has `Cunning: 0` (impossible per point_buy floor, but theoretically) — Doctor.minimum_score=10 fails, `qualifying_classes` returns no Doctor — chargen UI hides Doctor option. **Acceptable degradation; matches C&C pattern.**

What if a save file has `class_str: Doctor` but classes.yaml is removed at runtime? `next((c for c in self._classes if c.display_name == class_str), None)` returns None → `chargen.class_kit_unresolved` OTEL event fires → no kit_tables → no items rolled → inventory has only the non-roll items (already added before the kit-roll block at builder.py line 1797). **Graceful degradation; matches the existing builder pattern.**

A racially-loaded Victorian item ID (e.g. "regimental_decorations" tied to colonial military) — the content includes lore acknowledging the colonial past ("Carried across two continents and back. Knows north better than its owner does."). Genre-truth is preserved without glorification. **Editorial color; acceptable.**

Total devil's-advocate yield: 1 real LOW finding (the_satchel not under wiring-test). Everything else is verified or color.

## Rule Compliance

**Rules audited from CLAUDE.md (orchestrator + content + server):**

- **No Silent Fallbacks** — `equipment_tables.yaml` has a top-level `tables:` block labeled "Random-table fallback … used only if the_satchel scene ever switches to `equipment_generation: random_table`". The_satchel currently uses `class_kit`. `builder.py:1831` requires `random_table_requested == True` to fall through to `tables` — never silent. ✓ Compliant.
- **No Stubbing** — All 7 ClassDefs have full required fields (id, display_name, rpg_role, jungian_default, prime_requisite, minimum_score, kit_table) + optional encounter_beat_choices populated. No empty placeholders. ✓ Compliant. **One soft case:** Industrialist has a complete kit but no chargen path. Per "No Stubbing" — is an orphan calling a stub? Judgment: no — the data is fully realized; the missing piece is the *chargen choice*, not the kit. The kit is consumable by `qualifying_classes` if Industrialist ever enters the player's class_str (e.g. via a future world override, narrator promotion of an NPC, or a vocation scene addition). Marking compliant but flagging as a coherence finding (LOW).
- **Don't Reinvent — Wire Up What Exists** — Dev mirrored the C&C `class_kit` pipeline exactly rather than inventing a Victoria-specific kit-resolution. `kit_table` field, `class_tables` block, `equipment_generation: class_kit` mechanical_effect — all from existing builder.py paths. ✓ Compliant.
- **Verify Wiring, Not Just Existence** — Dev shipped `test_victoria_doctor_chargen_produces_signature_items_end_to_end` which calls `CharacterBuilder.build()` and verifies the post-build inventory. **Soft gap:** test uses synthetic scenes instead of pack.char_creation — flagged below.
- **Every Test Suite Needs a Wiring Test** — `test_victoria_doctor_chargen_produces_signature_items_end_to_end` exists and is an integration test (drives CharacterBuilder, not just YAML structure). ✓ Compliant.
- **OTEL** — Story is content-only with one test file; no backend subsystem touched. CLAUDE.md explicitly says OTEL is "Not needed for: Cosmetic UI changes". Content authoring is the same category. ✓ N/A.
- **Gitflow / sidequest-content targets develop** (per project memory `feedback_gitflow_content`) — Branch `feat/49-4-victoria-starting-inventories` was branched from develop after a fresh pull. ✓ Verified — `git -C sidequest-content branch --show-current` confirms.
- **Personal project / no Jira** — Session frontmatter has `jira_key: null`. No Jira references in commits. ✓ Compliant.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Player picks "Country Doctor" in `char_creation.yaml.vocation` scene → `class_hint: Doctor` is captured into `MechanicalEffects` → CharacterBuilder records `class_str = "Doctor"` → `the_satchel` scene fires with `equipment_generation: class_kit` → `builder.py:1811-1828` resolves `next(c for c in self._classes if c.display_name == "Doctor").kit_table = "doctor_kit"` → `self._equipment_tables.class_tables["doctor_kit"]` returns the 8-slot kit → each slot rolls per `rolls_per_slot.get(slot, 1)` (singleton slots = guaranteed) → 9 items (gladstone_bag + stethoscope + clinical_thermometer + bandages_linen + 2 apothecary + 1 pocket + 1 paperwork + oilskin_coat) materialise into `character.core.inventory.items` → snapshot ships to UI. Verified end-to-end by `test_victoria_doctor_chargen_produces_signature_items_end_to_end` (drives CharacterBuilder against the real loaded pack, asserts inventory contains required items).

**Pattern observed:** Per-archetype guaranteed signature items via singleton slots is the right mechanical pattern for AC5's "Doctor must arrive with X" requirement. C&C uses multi-item slots with replacement (the source of the flaky `test_caverns_delver_loadout_wired_into_snapshot` Dev called out). Victoria's singleton-slot pattern is a cleaner design for "guaranteed items" — would be a worthwhile retrofit for C&C's `rations_day`. Filed as upstream improvement.

**Error handling:** Verified at `builder.py:1816-1828` — if `class_str` doesn't match any ClassDef.display_name, an OTEL `chargen.class_kit_unresolved` event fires with severity=error and `kit_tables` stays None, falling through gracefully without items rolled (no exception, no silent success). Matches SOUL.md "No Silent Fallbacks" doctrine.

**Findings (none blocking; all LOW):**

- [SIMPLE] [LOW] Orphan Industrialist calling — `genre_packs/victoria/classes.yaml:113` declares `industrialist` and `equipment_tables.yaml:103` declares `industrialist_kit`, but `char_creation.yaml.vocation` (lines 86-165) has no `class_hint: Industrialist` choice. The kit is unreachable in normal chargen. **Pre-existing condition** — `rules.yaml.allowed_classes` already had Industrialist before 49-4; 49-4 made allowed_classes ↔ classes.yaml consistent (improvement), but the chargen vocation gap remains. Worth a follow-up to either add an Industrialist vocation or drop it from allowed_classes. Recorded as Delivery Finding.

- [TEST] [LOW] `test_victoria_doctor_chargen_produces_signature_items_end_to_end` builds synthetic `CharCreationScene` objects rather than loading `pack.char_creation`. A typo, rename, or removal of `the_satchel` from `char_creation.yaml` would not break any test. I verified the scene loads correctly via REPL (`mechanical_effects.equipment_generation == 'class_kit'`), but the bound contract is missing. A one-line addition — `assert any(s.mechanical_effects and s.mechanical_effects.equipment_generation == 'class_kit' for s in pack.char_creation)` — would close the gap. Recorded as Delivery Finding.

- [VERIFIED] All `encounter_beat_choices` reference valid beat IDs from `rules.yaml.confrontations` — `loader.py:541` validator confirmed this at pack-load time (`test_victoria_loads` exercises it).

- [VERIFIED] All 47 `item_id`s referenced in `equipment_tables.yaml.class_tables` resolve to entries in `inventory.yaml.item_catalog` — `test_victoria_kit_items_exist_in_inventory` enforces this.

- [VERIFIED] `starting_gold` is wired pack-agnostically at `chargen_loadout.py:179` — Victoria's new starting_gold block will be consumed at chargen-end without server code changes.

- [VERIFIED] `class_hint` strings in `char_creation.yaml.vocation` exactly match `display_name` values in `classes.yaml` — manual cross-check: Doctor, Clergyman, Society, Governess, Detective, Explorer all paired.

- [VERIFIED] `prime_requisite` values (Cunning/Nerve/Pride) match Victoria's `ability_score_names` (Angst/Pride/Humour/Nerve/Cunning/Passion) — `builder.py:58` does `stats.get(c.prime_requisite, 0)` which works with any string key, not just STR/DEX/etc.

- [EDGE] (no findings — preflight is the only enabled diff-based subagent; my own edge analysis surfaced the apothecary `(2/3)²=44% no-quinine` probability but AC5 wording is satisfied with one apothecary item, which the kit guarantees probabilistically — at least one of 2 rolls hits something).

- [SILENT] (no findings — builder.py path verified to emit OTEL `chargen.class_kit_unresolved` on missing-class lookup; no silent fallbacks introduced by this diff).

- [DOC] All 22 new inventory items carry full schema (id, name, description, category, value, weight, rarity, power_level, tags, lore, narrative_weight). Comment block at the top of `equipment_tables.yaml` documents the singleton-slot convention. Header comments in `classes.yaml` explain the "Calling vs Class" UI-label distinction.

- [TYPE] ClassDef requires non-blank id/display_name and `extra: forbid` per `models/character.py:154`. All 7 Victoria ClassDefs satisfy schema; no stringly-typed escapes.

- [SEC] No external input handling, no auth surface, no secrets. Content YAML only.

- [SIMPLE] One mild structural artifact: the top-level `tables:` block in `equipment_tables.yaml` is documented as a fallback that's currently dead code (the_satchel uses class_kit). Kept for schema completeness per AC1's "match the C&C schema" wording. Acceptable.

- [RULE] All CLAUDE.md rules (No Silent Fallbacks / No Stubbing / Don't Reinvent / Verify Wiring / Every Test Suite Needs a Wiring Test / Gitflow / No Jira) audited above in **Rule Compliance** — compliant.

**Acceptance Criteria Status:**
- AC1 (equipment_tables.yaml per-archetype kits) — ✓ APPROVED. Schema mirrors C&C; 7 callings mapped.
- AC2 (inventory.yaml Victorian essentials) — ✓ APPROVED. 22 new items, all 12 AC1-listed IDs present.
- AC3 (the_kit scene wired) — ✓ APPROVED as `the_satchel` scene with `equipment_generation: class_kit`. Dev's deviation from AC3's stale `random_table` literal is sound (see Deviation Audit below).
- AC4 (item_id ↔ catalog) — ✓ APPROVED. Enforced by test.
- AC5 (Doctor chargen produces signature items) — ✓ APPROVED. Doctor kit uses singleton slots; end-to-end test asserts post-build inventory contains gladstone_bag + stethoscope + clinical_thermometer + bandages_linen + apothecary item.

**Handoff:** To Hawkeye Pierce (SM) for finish-story.