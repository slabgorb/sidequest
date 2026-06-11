---
story_id: "103-1"
jira_key: ""
epic: "103"
workflow: "tdd"
---
# Story 103-1: Saint layer — saints.yaml schema + SaintRegistry + Saint-Marked chargen preset

## Story Details
- **ID:** 103-1
- **Jira Key:** (none — SideQuest is Jira-less)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-11T02:52:43Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-11T02:51:13Z | 2026-06-11T02:52:43Z | 1m 30s |
| red | 2026-06-11T02:52:43Z | - | - |

## Sm Assessment

**Story:** 103-1 — Saint layer: `saints.yaml` schema + `SaintRegistry` + Saint-Marked chargen preset over `MpEconomy` + `awn.saint.applied` span + 3 proof Saints. 5 pts, p2, tdd. Repos: server, content.

**Why now:** Epic-103 keystone. 103-4 (full Saint canon) is blocked on this schema freeze; the Seaboard's signature chargen path doesn't exist until it lands. Prereqs confirmed live: AWN Plan 2 mutation catalog + MpEconomy stable (102-7 merged 2026-06-10).

**Routing approach (TEA RED phase — Fezzik):** Six ACs map to test families:
1. Schema/loader: fixture YAMLs per malformation (missing drawback, >1 drawback, unknown tradition) → precise validation error.
2. Loud ID validation: bad-fixture load asserts error names offending saint id + mutation id (No Silent Fallbacks — error, not skip).
3. Preset application: chargen integration test asserts sheet = bundle positives + drawback negative, MP math consistent with MpEconomy.
4. Drawback mechanically live: OTEL-asserted confrontation fixture (lie-detector pattern from 102 AC5b).
5. Span: `awn.saint.applied` capture asserts saint id, bundle, drawback, MP arithmetic.
6. Regression: flickering_reach loads clean with NO saints.yaml; present-and-broken is loud.

**Wiring test is mandatory** (CLAUDE.md): at least one integration test proving the registry loads via the production world-load path AND the chargen preset is reachable — not just loader unit tests.

**Guardrails to hold the implementer to:** extend `sidequest/mutation/` (no new top-level subsystem, NOT the MagicPlugin/ADR-126 seam — AWN D5); reuse `MpEconomy` (two presets, one engine — no second pricing path); world-tier only (`worlds/seaboard_of_saints/saints.yaml`, no genre-tier file, ADR-140); do NOT touch `ruleset/awn.py` combat math, Wild-Mutant freeform path, or flickering_reach content.

**Risks / watch:** (a) proof-Saint bundle IDs must hand-map to EXISTING `mutant_wasteland/mutations.yaml` catalog entries — if no clean analog, swap proof Saint, do NOT add genre mutations (that's 103-4). (b) chargen `mutation` step is assumed to have a preset-vs-freeform seam; if a new step is required, log a deviation and keep it additive. (c) OTEL span-assertion is the lie-detector — without it we can't prove the bundle is real crunch vs narrator flavor (Sebastien/Jade requirement).

**Decision:** Proceed to RED. No blocking deviations at setup. Context is complete and validated.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->