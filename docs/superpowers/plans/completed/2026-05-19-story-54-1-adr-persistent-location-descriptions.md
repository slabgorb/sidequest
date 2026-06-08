# Story 54-1: ADR — Persistent Location Descriptions + Mechanical Manifest

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land an ADR that locks the doctrine, manifest type spec, validator surface, OTEL contract, and two-mode resolver from the persistent-location-descriptions design — so subsequent code stories have a durable decision record to cite.

**Architecture:** Single markdown ADR at `docs/adr/109-persistent-location-descriptions-mechanical-manifest.md`. Follows the established frontmatter schema (ADR-088). The spec at `docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md` is the long-form design; this ADR is the durable scope-locking record. Pattern: mirror ADR-107's structure (Status section pointing at spec, Context, Decision, Consequences, Implementation status `partial` pointing at the spec).

**Tech Stack:** Markdown only. Validation via `pf validate adr`.

**Workflow:** trivial (no tests; doc gate only).

---

### Task 1: Create the ADR file

**Files:**
- Create: `docs/adr/109-persistent-location-descriptions-mechanical-manifest.md`

- [ ] **Step 1: Confirm next free ADR number**

Run:
```bash
ls docs/adr/ | grep -E '^1[0-9]{2}-' | sort | tail -3
```
Expected: highest is `108-mp-item-attribution-recipient-tagging.md`. Use `109`. If something higher has landed since this plan was written, bump.

- [ ] **Step 2: Write the ADR**

Create `docs/adr/109-persistent-location-descriptions-mechanical-manifest.md` with this content:

```markdown
---
id: 109
title: "Persistent Location Descriptions + Mechanical Manifest"
status: accepted
date: 2026-05-19
deciders: ["Keith Avery", "Oberon (Architect agent)"]
supersedes: []
superseded-by: null
related: [3, 14, 26, 55, 96, 100, 103, 104, 106]
tags: [game-systems, frontend-protocol, observability, world-building]
implementation-status: partial
implementation-pointer: docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md
---

# ADR-109: Persistent Location Descriptions + Mechanical Manifest

## Status

Accepted. Design detail and per-story decomposition live in
`docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md`.
The per-task plans for Epic 54 and Epic 55 live in
`docs/superpowers/plans/2026-05-19-story-54-*.md` and
`docs/superpowers/plans/2026-05-19-story-55-*.md`. This ADR is the durable
decision record and scope boundary — it locks the contested calls and the
seams, it does not restate the spec.

## Context

The SideQuest narrator (Anthropic SDK per ADR-101) writes convincing prose
with zero mechanical backing. A player who tugs the "rusted chain hanging
from the ceiling" can discover the chain was improv — there is no chain
object, no affordance, just narrator flavor. Sometimes the improv lands;
often it collapses (overbaited hook per SOUL.md Diamonds-and-Coal,
"narrator-lie" per CLAUDE.md OTEL Observability).

The play table asked for **persistent room/area descriptions, mechanically
backed**. Anything the description names must either be a real game-state
thing with affordances, OR be trivial enough that yes-and promotion handles
player engagement without breaking trust.

This is also a Zork-Problem (CLAUDE.md) call: the manifest is a
**producer-side contract** (what the narrator and authors may claim), never
a **consumer-side gate** (the closed verb set of "things players may
touch"). The player can always introduce new entities the description
didn't mention; the system says yes.

## Decision

Introduce a typed, persistent `LocationEntity` manifest per location,
backed by a three-tier classification, a two-mode runtime resolver, and a
validator. Five locked calls follow.

### 1. Three-tier manifest

Every named entity in a location's description carries a tier:

- `real_object` — fully bound to a game-state subsystem
  (`location_feature` | `npc` | `item` | `clue` | `scenario_clue`).
  Narrator may mechanically engage it; resolver returns its binding.
- `yes_and` — canonical but mechanically minimal. Engagement is honored;
  promotion lifts a `flavor_only` entry to `yes_and` on first mechanical
  touch.
- `flavor_only` — described but mechanically inert. Engaging it promotes
  it to `yes_and` and writes to `location_promotions`.

### 2. Two-mode resolver

The new `resolve_location_entity(label, region_id, mode, engagement_kind)`
tool has two modes that encode the Zork-Problem-safe split:

- `narrator_proactive` — narrator-side prose claim. Manifest miss =
  contract violation. The narrator's pending mechanical action does NOT
  commit; OTEL fires the lie-detector span.
- `player_initiated` — player-side input. Manifest miss = canonization
  (Yes-And). A new `yes_and_minted` entity is written to
  `location_promotions` and the player's action proceeds.

Pure narration (descriptive prose without mechanical commitment) does
not require resolver calls. Every narrator-side mechanical claim
(damage, move, take, modify) MUST route through the resolver — there
is no "claim without resolve" code path. The implementer enforces this
in the agent tool harness.

### 3. Two production paths, single consumer shape

- **POI worlds** (e.g. `tea_and_murder/glenross`) — hand-authored
  manifest in `cartography.yaml regions[*].entities[]`. Replaces the
  untyped `landmarks[]` string array.
- **Procedural worlds** (`beneath_sunden`) — deterministically composed
  at materialize time by `cookbook/assemble.py` and persisted to
  `<world>/rooms/<id>.yaml` alongside the cavern mask.

Both shapes are consumed by the same loader path. No new top-level
entity competes with `regions[]` or `<world>/rooms/<id>.yaml`. ADR-106's
materializer-emits-region pattern extends naturally.

### 4. Authored content never mutates at runtime

Per-game runtime mutations (flavor_only → yes_and promotion and
player-initiated mints) accumulate in a new `location_promotions`
SQLite table keyed by `(save_id, region_id, entity_id)`. Read-time
merge layers promotions on top of authored. Promotions are **durable**
per the durable-retention principle (project memory); no GC.

### 5. Encounter overlays layer, never destroy

Encounter-bound action overrides contribute an `entity_delta` and a
`prose_suffix` merged at read time. Base description and base manifest
never mutate from overlays. Two overlays on the same room concatenate
in encounter-arrival order (deterministic).

## Consequences

### Positive

- Narrator improv against described entities becomes detectable
  (`location.entity.resolve { mode=narrator_proactive, resolved=false }`).
  GM panel surfaces the count per session; over time, drives prose
  revision work.
- Players can canonize entities (Yes-And, Diamonds-and-Coal). The
  manifest grows from play, not just authoring.
- POI and procedural worlds share one consumer path; the cookbook seam
  (ADR-106) extends naturally with `compose_room_prose()`.
- Action overlays earn their screen-time spike (SOUL.md "Cut the Dull
  Bits") with deterministic merge order and no destructive mutation
  of the base.

### Negative

- New table (`location_promotions`) and new validator (`pf validate
  locations`) — two new surfaces with their own CI footprint.
- Content-side cost: every existing world with a `landmarks[]` array
  needs backfill to typed `entities[]` (mitigated by per-pack
  `generic_allowlist[]` and a non-blocking coherence warning).
- Cookbook dressing pool needs to be authored at 8-12 lines per look
  to avoid procedural-prose repetition (Risks §8).

### Scope boundary (v1)

Out of scope, deferred to follow-up ADRs / stories:

- Player-facing entity chips / clickable manifest in the Location tab.
  **Reinforced exclusion** — surfacing the manifest as a UI verb set
  is itself a Zork violation.
- Multi-language prose, audio cues bound to entities, image
  regeneration on overlay.
- Cross-region entities (NPCs go via the NPC subsystem).
- Per-PC perception filtering on the manifest (ADR-104 / ADR-105).
  All entities universally visible to all seated players in v1.

## Implementation guidance for Dev

The spec at
`docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md`
is authoritative. Per-story plans:

- 54-1 (this ADR)
- 54-2 — Server schema + `LOCATION_DESCRIPTION` WebSocket message
- 54-3 — `pf validate locations`
- 54-4, 54-5 — Content backfills
- 54-6 — Resolver + `location_promotions` table
- 54-7 — Encounter overlays
- 54-8 — OTEL spans + GM-panel surfacing
- 54-9 — `LocationPanel.tsx` UI
- 55-1 — Procedural cookbook description+manifest emit (stitch)

Suggested rollout order (spec §7.4): 54-1 → 54-2 → {54-3, 54-9} → 54-6
→ 54-7 → 54-8 → {54-4, 54-5} → 55-1.

### Reference

- Spec: `docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md`
- Related ADRs: ADR-026 (client state mirror), ADR-100 (KnownFacts),
  ADR-103 (native OTEL via tool registry), ADR-104/105 (perception
  filtering — out of scope here), ADR-106 (procedural megadungeon).

```

- [ ] **Step 3: Validate the ADR**

Run:
```bash
pf validate adr
```
Expected: PASS. If it warns about frontmatter fields, fix and re-run.

- [ ] **Step 4: Visual sanity check**

Run:
```bash
head -30 docs/adr/109-persistent-location-descriptions-mechanical-manifest.md
grep -c "^## " docs/adr/109-persistent-location-descriptions-mechanical-manifest.md
```
Expected: header renders, at least 4 `## ` sections (Status, Context, Decision, Consequences).

- [ ] **Step 5: Commit**

```bash
git add docs/adr/109-persistent-location-descriptions-mechanical-manifest.md
git commit -m "docs(adr): ADR-109 persistent location descriptions + mechanical manifest

Locks doctrine, three-tier manifest, two-mode resolver, validator
surface, OTEL contract, and authored-content-immutability call from
the 2026-05-19 design spec. Implementation lives in epic 54 (POI
+ infrastructure) and epic 55 (procedural cookbook stitch)."
```

---

### Task 2: Update ADR index

**Files:**
- Modify: `docs/adr/README.md` (auto-generated index per ADR-088)
- Modify: `CLAUDE.md` (top-level ADR index) — only if a category line needs the new ADR

- [ ] **Step 1: Run the ADR index regenerator**

Run:
```bash
python3 scripts/regenerate_adr_indexes.py
```
Expected: writes `docs/adr/README.md` (and may touch `CLAUDE.md`'s generated block per ADR-088). Diff should show ADR-109 inserted into the appropriate category list(s).

If `scripts/regenerate_adr_indexes.py` does not exist (script renames happen), look for the equivalent under `scripts/` or `pennyfarthing-dist/`:
```bash
find . -name "regenerate_adr*" -type f -not -path "*/.venv/*" | head -5
```

- [ ] **Step 2: Verify index diff**

Run:
```bash
git diff docs/adr/README.md CLAUDE.md | head -50
```
Expected: ADR-109 line(s) added under categories matching its `tags:` (game-systems, frontend-protocol, observability, world-building).

- [ ] **Step 3: Commit the regenerated index**

```bash
git add docs/adr/README.md CLAUDE.md
git commit -m "docs(adr): regenerate ADR index for ADR-109"
```

---

### Self-review checklist

- [ ] Frontmatter has every field ADR-088 requires (`id`, `title`, `status`, `date`, `deciders`, `supersedes`, `superseded-by`, `related`, `tags`, `implementation-status`, `implementation-pointer`).
- [ ] `implementation-pointer` points at the design spec.
- [ ] Decision section has the five locked calls.
- [ ] Consequences section has positive + negative + scope boundary.
- [ ] Implementation guidance lists all 10 stories with their high-level scope.
- [ ] `pf validate adr` passes.
- [ ] ADR index regenerated and committed in a separate commit.
