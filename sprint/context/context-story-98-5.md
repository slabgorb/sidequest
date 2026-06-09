---
parent: context-epic-98.md
workflow: tdd
---

# Story 98-5: S2 Server — inter-system jump adjudication via SWN ruleset seam (ADR-117), default cost OTEL-logged

## Business Context

This story makes the campaign-scale **jump** a real adjudicated mechanic: when the
party jumps from one system node to another, the bound ruleset (space_opera → SWN
per ADR-117) computes the cost — drive/fuel, transit time, hazard — instead of a
free hop. It is the server half of the jump-mechanics increment and the engine
that gives the C2 content (98-4) meaning.

Critically, this is **campaign-scale** travel and must stay **separate** from
ADR-130's intra-system course model (the orrery's approximate-Hohmann transit) —
exactly as the two *view* scales (graph vs orrery) stay separate. Conflating the
two movement scales is the failure mode this story must avoid. Per the OTEL
principle, every jump decision emits a watcher span so the GM panel verifies the
crunch actually fired — not Claude's prose.

## Technical Guardrails

**Lane:** Dev. **Repo:** server. **Depends on:** 98-2 (S1) for region-scoped
spatial state.

**Key files:**
- `agents/subsystems/movement.py` — where inter-system jump adjudication is reached from a production path.
- The bound **ruleset module** (ADR-117, space_opera → SWN) — owns the drive/fuel/transit computation.
- `cartography`/region loader — reads `routes` edge fields when present.

**Patterns to follow:**
- Adjudicate jump cost/time/hazard **through the bound ruleset seam** (ADR-117) — do not hard-code SWN math in `movement.py`; call the ruleset so other rulesets can supply their own jump model.
- When a `routes` entry exists for the edge, read its authored fields (98-4). When it does **not**, the ruleset computes a **default** from the SWN drive model — and that default is **explicit and OTEL-logged** (No Silent Fallbacks: the default is a named computation, never a silent zero).
- **Finalize the additive `routes` field names** here (`jump_fuel`, `transit_days`, `drive_rating_min`, `hazard`/reuse `danger` — Dev/SWN call) and **document them for 98-4 (C2)**. C2 cannot author correctly until this schema is fixed.
- Emit an **OTEL span per jump**: from/to region, fuel spent, transit days, hazard roll. Plus a span for the default-cost path (98-5 AC2).

**Edge model (epic 98 §3 — authoritative):** `adjacent` is connectivity; `routes`
is the mechanics annotation this story reads. A missing `routes` entry is a
navigable default-cost edge, not an error. A `routes` entry with endpoints not in
any `adjacent` list is a route-level anomaly (drop + WARN) — do not promote it to
connectivity.

**What NOT to touch:**
- Do **not** modify the ADR-130 intra-system course model — the two movement scales stay separate.
- Do **not** author content (that is 98-4) — this story may add fixtures but the live `cartography.yaml` routes are C2's lane.
- Do **not** alter per-system orrery resolution (98-2's lane).

## Scope Boundaries

**In scope:**
- Inter-system jump adjudication via the SWN ruleset seam, reading `routes` fields when present.
- Explicit, OTEL-logged default jump cost for unrouted edges.
- Finalizing + documenting the additive `routes` field schema for C2.
- OTEL span per jump (from/to, fuel, transit days, hazard).
- A wiring test proving adjudication is reached from `movement.py`.

**Out of scope:**
- Authoring `routes` content for real edges (98-4).
- Intra-system course/transit (ADR-130, untouched).
- UI presentation of jump cost (not in this epic's UI story; 98-3 is the map view-model only).

## AC Context

- **AC1 — jump adjudicated through the bound ruleset.** Inter-system jump
  cost/time/hazard is computed via the ADR-117 SWN drive/fuel/transit model,
  reading `routes` edge fields when present. *Test:* with a `routes` entry on an
  edge, assert the adjudicated cost reflects the authored fields and flows through
  the ruleset seam (not a `movement.py` hard-code).
- **AC2 — explicit, logged default for unrouted edges.** An edge with **no**
  `routes` entry → the ruleset computes a default jump cost from the SWN drive
  model; this default is explicit and **OTEL-logged**. *Test:* jump an unrouted
  edge → assert a non-silent default cost is produced AND a span records it as a
  ruleset default (No Silent Fallbacks). *Edge case:* an edge that is `adjacent`
  but has a `routes` entry with endpoints reversed/mismatched — confirm it is
  treated as the route-level anomaly (drop + WARN), not a silent connectivity.
- **AC3 — `routes` field schema finalized + documented.** The additive field
  names (`jump_fuel`, `transit_days`, `drive_rating_min`, …) are finalized and
  documented so 98-4 (C2) can author against them. *Test:* the schema is asserted
  in code (model/validator) and referenced by a doc the C2 story can cite.
- **AC4 — intra-system course untouched.** The ADR-130 course model is not
  modified — the two movement scales stay separate. *Test:* an intra-system move
  still uses the course model unchanged; assert no jump-adjudication path is
  invoked for intra-system movement.
- **AC5 — OTEL span per jump.** Each jump emits a span with from/to region, fuel
  spent, transit days, hazard roll. *Test:* execute a jump → assert the span
  exists with all five attributes populated.

## Assumptions

- **98-2 (S1) is merged** so region-scoped spatial state exists — the adjudicator knows the party's current region and the target region for a jump. If current/target region is not reachable at the `movement.py` seam, log a Design Deviation.
- The space_opera pack is bound to the **SWN** ruleset (ADR-117) and the SWN module exposes (or can expose) a drive/fuel/transit computation suitable for inter-system jumps. If SWN's SRD jump/drive model needs new surface in the ruleset module, that is in-scope server work for this story — but flag if it balloons beyond 5 points.
- The exact `routes` field names are a **Dev + SWN-seam decision finalized in this story** (AC3) — they are not pre-ordained by the ADR (which lists them as illustrative/additive). C2 (98-4) is sequenced *after* this decision; do not let C2 start authoring against guessed names.
- "Jump" (campaign scale) and "course" (intra-system, ADR-130) are genuinely distinct code paths. If they currently share a transit entry point that would conflate them, separating them is part of this story's work — note it explicitly so the reviewer can confirm the two scales did not get fused.
