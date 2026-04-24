---
id: 88
title: "ADR Frontmatter Schema and Auto-Generated Indexes"
status: accepted
date: 2026-04-24
deciders: ["Keith Avery", "Leonard of Quirm (Architect)", "Ponder Stibbons (Dev)"]
supersedes: []
superseded-by: null
related: [82, 85, 86, 87]
tags: [codebase-decomposition, project-lifecycle]
implementation-status: live
implementation-pointer: null
---

# ADR-088: ADR Frontmatter Schema and Auto-Generated Indexes

> This ADR is the first in the tree to use the frontmatter convention it defines.
> The block above is not a demo — it is the canonical example. Tooling is owed
> before every ADR receives the same treatment (see Migration).

## Context

The ADR collection has reached 87 entries. At this scale, the flat directory and hand-maintained indexes (`docs/adr/README.md`, the compact block in `CLAUDE.md`) stop being usable:

- **Primary reader experience is poor.** 87 entries mix Accepted, Proposed, Superseded, and Historical statuses in the same index. A reader asking "what is the current narrator story?" has to scan the whole list.
- **Maintenance cost scales linearly.** Every ADR landing (or status change) requires two hand-edits in two indexes. Drift between ADR body and index is inevitable and already present.
- **Implementation status is invisible.** ADR-087 established that many accepted ADRs (018, 020, 041, 042, 043, 044, 053, 059, 069) are currently dark in the Python tree — but reading ADR-018 gives no hint that the trope engine isn't live. The reader has to cross-reference ADR-087 manually.
- **Supersession signals are prose, not structured.** `ADR-056 → ADR-059` exists as an English sentence in ADR-059's Relates line. Tooling cannot trace the graph.

Two conventions are already in use for ADR metadata:

- **Old style** (ADRs 001–067 roughly): `## Status\nAccepted\n` prose block, related ADRs scattered through Context/Decision sections.
- **New style** (ADRs 059, 082, 086): bold-key lines directly under the H1 — `**Status:** ... **Date:** ... **Deciders:** ... **Supersedes:** ...`.

Neither is machine-readable. The input document `docs/adr-frontmatter-schema-proposal.md` (now superseded by this ADR) established the design; this ADR promotes it.

The industry pattern at this scale is **structured frontmatter + auto-generated indexes**. Supported by every Markdown toolchain (adr-log, log4brains, Docusaurus, MkDocs, Obsidian). We do not need any of those tools — a ~60-line script reading frontmatter is sufficient — but adopting frontmatter keeps the door open.

## Decision

**Every ADR carries YAML frontmatter conforming to the schema below. The `docs/adr/README.md` index, the `CLAUDE.md` compact ADR-index block, the superseded-ADR archive view, and the implementation-drift view are all auto-generated from frontmatter by a script in `scripts/`. Hand-maintenance of these indexes ends.**

### Schema

```yaml
---
id: 059                              # int (preferred) or zero-padded string; must match filename prefix
title: "Monster Manual — Server-Side Pre-Generation via Game-State Injection"
status: accepted                     # enum: proposed | accepted | superseded | deprecated | historical
date: 2026-04-03                     # ISO 8601 (YYYY-MM-DD). Original accept date.
deciders: [Keith Avery]              # list of strings. Include agent personas: "Naomi Nagata (Architect)"
supersedes: [056]                    # list of ADR IDs (empty list if none)
superseded-by: null                  # single ADR ID or null
related: [001, 003, 007, 020]        # list of ADR IDs
tags: [agent-system, code-generation, npc-character]   # controlled vocabulary, see below
implementation-status: drift         # enum: live | partial | drift | deferred | not-applicable | retired
implementation-pointer: 087          # ADR ID, file path, or null
---
```

### Field definitions

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `id` | int or zero-padded string | ✓ | Redundant with filename but queryable. Tooling uses this, not the filename. |
| `title` | string | ✓ | Duplicates the H1. Keep synchronized; validator warns on drift. |
| `status` | enum | ✓ | Lifecycle state. |
| `date` | ISO date | ✓ | Original acceptance date. Subsequent lifecycle events tracked in prose. |
| `deciders` | list[string] | ✓ | Who was in the room. Agent personas included (audit trail of which persona made the call). |
| `supersedes` | list[ADR-id] | ✓ | Empty list if none. |
| `superseded-by` | ADR-id or null | ✓ | Nygard rule: exactly one successor or null. If two ADRs jointly replace one, chain them A → B → C. |
| `related` | list[ADR-id] | ✓ | Empty list if none. Non-supersession references. |
| `tags` | list[tag] | ✓ | Minimum one. Controlled vocabulary (below). |
| `implementation-status` | enum | ✓ | Live code state. The load-bearing new field. |
| `implementation-pointer` | ADR-id / file path / null | conditional | Required if `implementation-status` is `partial` or `drift`. Optional for `deferred` (many Proposed ADRs have no restoration plan yet). |

### `status` enum

| Value | Meaning |
|-------|---------|
| `proposed` | Design written, not yet agreed. |
| `accepted` | Agreed and current. |
| `superseded` | Replaced by a named successor. Requires `superseded-by`. |
| `deprecated` | Was accepted, now withdrawn without replacement. Rare. |
| `historical` | Describes a feature that no longer exists (e.g., ADR-054 WebRTC voice chat — cut when TTS was removed). Distinct from `superseded` — nothing replaced it. |

### `implementation-status` enum — the load-bearing new field

This is what converts ADR-087's restoration plan into self-maintaining state. Each ADR carries its own verdict; reading any ADR tells you immediately whether its intent is live code.

| Value | Meaning |
|-------|---------|
| `live` | Implementation present in the live codebase, matching the ADR. |
| `partial` | Implementation exists but does not fully satisfy the ADR. Pointer required. |
| `drift` | ADR was implemented (typically Rust-side) but missing from current tree. Pointer required (usually → ADR-087). |
| `deferred` | Accepted/Proposed but not scheduled. Pointer usually → future epic or ADR. |
| `not-applicable` | Design-layer / principle ADRs with no implementation surface (ADR-002 SOUL Principles, ADR-014 Diamonds and Coal, ADR-080 Narrative Weight Trait). |
| `retired` | For `status: superseded` / `status: historical`. Implementation question is moot. |

**Consistency rule:** `status: superseded` or `status: historical` ⇒ `implementation-status: retired`. Validator enforces.

### `tags` — controlled vocabulary

Derived from the current category groupings in `CLAUDE.md`'s compact ADR index. Adding a new tag requires a small ADR so the vocabulary does not sprawl (this is the exact thing that kills informal tag systems at the 50+ scale).

| Tag | Covers |
|-----|--------|
| `core-architecture` | ADRs 001–007 and foundational structural decisions |
| `prompt-engineering` | Prompt zones, attention tiers, rule taxonomy |
| `agent-system` | Narrator/agent architecture, orchestration, routing |
| `game-systems` | Mechanical engine — combat, chase, trope, dice, progression |
| `frontend-protocol` | Client-side concerns, protocol shapes, UI contracts |
| `multiplayer` | Turn coordination, shared/per-player state, perception |
| `transport-infrastructure` | WebSocket, Unix socket, GPU budget, sanitization |
| `narrator` | Narrator-specific: verbosity, vocabulary, structured output |
| `npc-character` | NPC systems: disposition, OCEAN, consequence, affinity |
| `media-audio` | Image/audio pipeline, prerendering, throttles, LoRA |
| `turn-management` | Turn counters, phase tracking |
| `room-graph` | Navigation, tactical grid |
| `code-generation` | Tool binaries, pregen, monster manual |
| `observability` | OTEL, spans, watcher, lie-detection |
| `codebase-decomposition` | Structural/organizational decisions |
| `narrator-migration` | Local model, protocol collapse, TTS-post |
| `genre-mechanics` | Watcher-semantic, LoRA training, confrontation engine, portraits |
| `project-lifecycle` | Port decisions, tracker hygiene, restoration plans |

An ADR typically has 1–3 tags. ADR-067 would be `[agent-system, narrator, narrator-migration]`.

### Validation rules (enforced by hook + CI)

1. `id` matches filename prefix.
2. `title` matches H1 text (warn-only on drift).
3. `supersedes` / `superseded-by` are symmetric — if A supersedes B, B must have `superseded-by: A`.
4. `status: superseded` ⇒ `superseded-by` is set.
5. `status: superseded` or `historical` ⇒ `implementation-status: retired`.
6. `implementation-status: partial` or `drift` ⇒ `implementation-pointer` is set. *(`deferred` is exempt: many Proposed ADRs have no restoration plan yet and pointing them at ADR-087 would be false — the rule was relaxed during implementation on 2026-04-24 to match reality.)*
7. All tags are from the controlled vocabulary.
8. `date` is a valid ISO 8601 date.

A drifted index becomes impossible rather than eventual.

### Auto-generated views

A script — `scripts/regenerate_adr_indexes.py` — regenerates from frontmatter:

1. **`docs/adr/README.md`** — full index sorted by ID; status, impl-status, and tags inline.
2. **`CLAUDE.md` ADR-index block** — compact category-keyed view, auto-generated by grouping on `tags`. Filters to `status: accepted` by default, so superseded ADRs drop out. Of the current 87 entries, 7 are `superseded` / `historical` and disappear from the primary view automatically.
3. **`docs/adr/SUPERSEDED.md`** — archive view. All `superseded` / `historical` ADRs, grouped by successor. Reachable, not in the way.
4. **`docs/adr/DRIFT.md`** — all ADRs with `implementation-status: drift` / `partial` / `deferred`. This is ADR-087's priority list, self-maintaining. When a drift ADR is restored, flip its frontmatter to `live`; it drops off this view on next regeneration.
5. **Supersession Mermaid graph** — optional, small. Shows the chain of successor relationships.

## Open Questions Resolved

The schema-proposal draft (`docs/adr-frontmatter-schema-proposal.md`, now superseded) raised five open questions. Resolutions locked into this ADR:

1. **Single `date` field** — yes. Subsequent lifecycle events (cutover, revision) go in prose, not frontmatter. One field keeps the schema tight.
2. **Tag vocabulary governance** — adding a new tag requires a small ADR. This ADR is the seed list; future ADRs extend it explicitly.
3. **Deciders includes agent personas** — yes. `"Naomi Nagata (Architect)"` is a real audit signal.
4. **Frontmatter, not sidecar files** — ADRs stay self-contained. Standard for Markdown tooling.
5. **No explicit schema version** — the script is the schema. If the schema changes, a migration pass lands in the same PR.

## Migration

### Before → After example (ADR-059)

**Before** (current new-style bold-key lines):

```markdown
# ADR-059: Monster Manual — Server-Side Pre-Generation via Game-State Injection

**Status:** Accepted
**Date:** 2026-04-03
**Deciders:** Keith
**Supersedes:** ADR-056 (Script Tool Generators — narrator-side tool calls)
**Relates to:** ADR-001 (Claude CLI Only), ADR-003 (Genre Pack Architecture), ADR-007 (Unified Character Model), ADR-020 (NPC Disposition)
```

**After:**

```markdown
---
id: 059
title: "Monster Manual — Server-Side Pre-Generation via Game-State Injection"
status: accepted
date: 2026-04-03
deciders: [Keith]
supersedes: [056]
superseded-by: null
related: [001, 003, 007, 020]
tags: [agent-system, code-generation, npc-character]
implementation-status: drift
implementation-pointer: 087
---

# ADR-059: Monster Manual — Server-Side Pre-Generation via Game-State Injection
```

The bold-key lines are replaced by frontmatter. Body prose is unchanged. `implementation-status: drift` tells any reader of ADR-059 that the Python implementation is currently missing and points to ADR-087 for the restoration plan.

### Migration mechanics

One-shot script — `scripts/migrate_adr_frontmatter.py`:

1. **Parse** each ADR for existing metadata (regex handles both old and new styles).
2. **Infer missing fields:**
   - `date` from `git log --diff-filter=A --format=%aI <file>` (first-commit date).
   - `tags` from the category assignment in current `CLAUDE.md` (mapping already authored — script consumes it directly).
   - `implementation-status` from ADR-087's verdict tables: any ADR named in §A/§B/§C/§D/§E/§F gets the corresponding verdict; ADRs not in 087 default to `live` (implemented at port time) or `not-applicable` (principle-layer) based on a short override map.
3. **Emit** frontmatter block at file top. Strip the now-redundant bold-key lines. Leave all other prose intact.
4. **Validate** against the schema. Abort on any ADR it cannot confidently migrate; surface for manual review.

**Estimated work:** one Dev story — migration script + index-generation script + 87 file edits + CI hook. ~1h Dev, ~30m Architect review for ambiguous cases.

**Single atomic PR** containing all migrated ADRs, both scripts, the retired hand-maintained sections, and the pre-commit hook. Reversible by revert.

## Consequences

### Positive

- ADR index maintenance cost drops to zero after the migration.
- Reading any ADR surfaces its live implementation state — no more cross-referencing ADR-087 manually.
- Superseded ADRs drop from the primary view automatically; 7 items leave your surface area at migration time.
- ADR-085 port-drift audits and ADR-087 restoration tracking become queryable. `DRIFT.md` is auto-maintained — when a drift ADR is restored, one frontmatter flip drops it off the list.
- Tag-based filtering answers questions like "what are the current narrator ADRs" in 6 entries instead of 87.
- Supersession graph becomes traceable by tooling, not prose.
- First-class validator catches drift between index and frontmatter at commit time.

### Negative

- 87 files are touched in the migration PR. Review is mostly mechanical but the PR is large.
- A new convention means contributors need to know it. Mitigation: validator fails loudly on missing frontmatter; a short `docs/adr/TEMPLATE.md` gives the pattern.
- `implementation-status` becomes a field that can drift from reality (code changes, frontmatter doesn't). Mitigation: ADR-087's follow-on pass on each restored subsystem includes a frontmatter flip; CI could be taught to check that `live` ADRs have matching code via grep on named entities, but that is out of scope for this ADR.

### Neutral

- Frontmatter is compatible with Docusaurus / MkDocs / log4brains / adr-log if we ever want a static site. Adopting it now keeps the door open without committing to any tool.
- Existing ADR content is preserved verbatim. Only the header metadata moves.

## Implementation Plan

Single Dev story owed:

1. Write `scripts/migrate_adr_frontmatter.py` (one-shot migrator).
2. Write `scripts/regenerate_adr_indexes.py` (steady-state regenerator).
3. Write `scripts/validate_adr_frontmatter.py` (validator — shared logic with the regenerator).
4. Run migration; hand-review the ambiguous cases with Architect.
5. Retire hand-maintained sections of `docs/adr/README.md` and the `CLAUDE.md` ADR-index block (replace with "generated by scripts/regenerate_adr_indexes.py — do not edit by hand").
6. Add `scripts/validate_adr_frontmatter.py` to pre-commit hooks.
7. Update `docs/adr/README.md`'s leading prose to document the convention and link to this ADR.

When implementation lands, flip this ADR's `implementation-status` from `deferred` to `live` and clear `implementation-pointer`.

## What this ADR does **not** do

- **Does not rewrite any ADR's body prose.** Content is preserved verbatim; only the header moves.
- **Does not introduce any external tooling dependency.** Scripts are plain Python reading YAML — no adr-log, no log4brains, no static site generator. Those remain available as future adoption options.
- **Does not enforce implementation-status correctness** beyond structural validation. An ADR claiming `live` when the code is absent is a human/audit failure, not a schema failure. The matching story falls under ADR-085 audits.
- **Does not version the schema.** If the schema changes, the migration PR carries the change. Reader never needs to reason about "schema v1 vs v2."
