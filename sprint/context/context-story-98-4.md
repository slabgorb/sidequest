---
parent: context-epic-98.md
workflow: trivial
---

# Story 98-4: C2 Content — jump mechanics on reached cartography routes (yula neighbors first)

## Business Context

This story authors the **campaign-scale jump crunch** as content — the fuel /
transit / hazard numbers that make inter-system travel a real mechanical decision
rather than a free hop. It is the content half of the jump-mechanics increment
(S2 + C2), the payoff the mechanics-first players (Sebastien, Jade) ask for at the
campaign scale.

Per Diamonds-and-Coal, jump mechanics are authored **on demand**, edge by edge, as
play reaches them — starting with `yula`'s neighbors. An `adjacent` pair without
an authored `routes` entry is still fully navigable (the ruleset computes a default
cost, 98-5). This story does not block the campaign graph from being whole; it
*enriches* the edges play actually uses.

## Technical Guardrails

**Lane:** GM/World-Builder (YAML only). **Repo:** content. **Depends on:** 98-5
(S2) for the finalized field schema.

**Key file:**
- `worlds/perseus_cloud/cartography.yaml` — the `routes:` section.

**The content model (epic 98 §3 — authoritative; epic-100 spec defers to it):**
- **Connectivity stays on `adjacent:`** — do NOT move or fork it. It already feeds `dungeon/region_projection.py` + `movement.py` and is the *only* input to the d3-dag layout.
- **Jump mechanics are `routes:` entries** — one per traversable `adjacent` pair *that play reaches*. A `routes` entry is an *annotation* on an existing adjacency, not a new connection.
- An `adjacent` pair with **no** matching `routes` entry is a **valid navigable edge** with a ruleset-default jump cost (98-5 AC2) — **not** an error, **not** dangling.
- A `routes` entry whose endpoints are **not** in any `adjacent` list is a route-level anomaly (server drops + WARNs) — never author one.

**What NOT to touch:**
- Do **not** author orbital/system data (that is 98-1's lane).
- Do **not** invent field names — use the exact names 98-5 finalizes (`jump_fuel`, `transit_days`, `drive_rating_min`, `hazard`/`danger`, …).
- Do **not** author routes for edges play has not reached (Diamonds-and-Coal).

## Scope Boundaries

**In scope:**
- `routes:` entries with authored jump mechanics for each reached `yula`-neighbor edge, in the S2-finalized field names.
- Preserving *The Black Door* (`zephyr → ceron`) narrative fields.

**Out of scope:**
- The server adjudication that reads these fields (98-5).
- Default-cost computation for unrouted edges (98-5, ruleset-owned).
- Routes for unreached edges or other systems' neighbors (on demand, future).

## AC Context

- **AC1 — reached `yula` edges carry authored mechanics.** For each `adjacent`
  edge out of `yula` that play reaches, a `routes` entry exists carrying jump
  mechanics in the S2-finalized field names. *Test:* parse `cartography.yaml`;
  for each authored route, assert its endpoints appear in the relevant `adjacent`
  lists and the required jump fields are present and well-typed.
- **AC2 — unreached edges intentionally bare.** Edges not yet reached carry **no**
  `routes` entry and rely on the ruleset default (valid, not an error). *Test:*
  assert the file does not over-author — no routes for unreached `yula` neighbors;
  confirm the graph still treats them as navigable (cross-check 98-5 AC2 default).
- **AC3 — *The Black Door* preserved.** The existing `zephyr → ceron` route keeps
  its narrative fields (`distance`/`danger`/`terrain`/`from_id`/`to_id`); jump
  -mechanics fields are added only if/when that edge is reached. *Test:* assert the
  Black Door entry retains its original fields and is not clobbered by the new
  schema.

## Assumptions

- **98-5 (S2) is merged or its `routes` field schema is finalized and documented before this story starts** — C2 authors against S2's field names. If S2 has not finalized the names, this story cannot complete correctly; sequence C2 after S2's AC3 (schema doc). The dependency graph is `S1 → S2 → C2`.
- "Edges play reaches" is interpretable from current play state (the party is in/near `yula`). If which neighbor edges count as "reached" is ambiguous, default to authoring `yula`'s direct `adjacent` neighbors and flag the rest as on-demand — over-authoring the whole graph violates Diamonds-and-Coal.
- The `trivial` workflow is appropriate because this is additive YAML annotation on existing adjacencies — no engine logic. Validation is schema/load (fields present, endpoints valid, Black Door intact), the same content-validation harness 98-1 uses.
