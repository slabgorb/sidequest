---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-10: End-to-end wiring + regression — per-stock integration, flickering_reach regression, cliché audit

## Business Context

The epic's lie-detector story. Per CLAUDE.md's wiring principle and the 90-x/102-x lesson (the narrator will happily improvise crunch that isn't firing), the Seaboard isn't done when its files load — it's done when a character of **every stock** provably runs chargen → opening → confrontation with their Saint drawback or stock trait **mechanically firing, OTEL-asserted** → save cycle. This story also holds the epic's two protective gates: flickering_reach must regress clean, and the cliché bans must hold across everything shipped.

## Technical Guardrails

- **Per-stock integration tests** (server, `tests/integration/`): for each of the six stocks — chargen completes → narrator opening loads (use a 103-8 opening) → a confrontation where the Saint drawback (Saint-Marked), granted trait (Animal/Plant/Synthetic), implant strain cost (Sleeper), or freeform mutation (Wild) fires through real dispatch — asserted via `awn.saint.applied` / `awn.stock.applied` / mutation-use / `system_strain.delta` spans, NOT via narration text. Pattern: the 102-x AC5b dispatch_engagement lie-detector fixtures.
- **Save cycle:** full save → load → state-identical resume for at least one stock with Saint content (the SaintRegistry state must round-trip; ADR-124 save-forensics surfaces can assert the census).
- **flickering_reach regression:** loads clean with zero Saint/stock content; Wild-Mutant chargen unchanged; mutation rolls byte-stable against the (possibly extended) genre catalog — additive entries must not shift existing d100 partitions. This is the AC that protects the sibling world from 103-4's genre additions.
- **Cliché audit:** run the `cliche-judge` agent across all shipped seaboard content (per its validation lane); §11 banned-term scan (Reach/Veil/Spire/Hollow/Drift/Mire/Shroud/Sanctum/Bastion coinages, bottlecaps, water-currency, etc.) as a scripted check — Sleepy Hollow exempt as a real place.
- **Test hygiene:** heavy e2e tests get `@pytest.mark.timeout(120)` (the xdist worker-crash trap); uuid-namespaced session slugs (the seed_slug_for_test collision trap); run suite verification with direct pytest counts, not testing-runner prose.
- **No new features:** this story wires and proves; any gap it finds routes back as a fix to the owning story's surface, not new scope here.

## Scope Boundaries

**In scope:**
- Six per-stock e2e integration tests with OTEL assertions; save-cycle test; flickering_reach regression suite; cliché audit (agent pass + scripted scan); epic DoD checklist sign-off (build plan §4)

**Out of scope:**
- Live multi-hour playtest (post-epic, /sq-playtest lane); performance/calibration tuning (AWN difficulty calibration is ADR-093's ladder, revisited when Plans 3+ land); UI e2e beyond what chargen-flow tests already cover

## AC Context

1. **Six stocks, six green e2e tests**, each asserting its mechanical span fired during a real confrontation — zero assertions on narration prose.
2. **Drawback specificity:** the Saint-Marked test asserts the *drawback* (negative mutation) effect engaged, not merely that mutations exist on the sheet.
3. **Save/load:** post-resume state identical (Saint bundle, stock traits, strain, HP); spans re-fire correctly post-resume.
4. **flickering_reach:** full existing suite green; d100 partition stability proven (fixed-seed roll comparison pre/post catalog additions).
5. **Cliché audit:** cliche-judge findings dispositioned (fixed or explicitly accepted with rationale); scripted ban-scan green.
6. **Epic DoD (build plan §4)** checklist complete and recorded in the session — this story's review is the epic's exit review.

## Assumptions

- All of 103-1..103-9 merged (hard dependency: this story runs last).
- OTEL span capture in tests follows the established watcher-test harness (ADR-132 WatcherHub isolation per session).
- A d100-partition-stability check is implementable as a seeded comparison; if 103-4's additive entries necessarily extend the table, "stability" means existing IDs keep their ranges — document the exact contract with Dev at red phase.
