---
parent: context-epic-52.md
---

# Story 52-1: ADR-096 subsume amendment + DRIFT/index regenerate

## Business Context

ADR-096 (Cavern Renderer Revival) was authored for a static cavern-rendering approach — pre-rendered
PNGs and mask files authored by hand in genre packs. ADR-106 supersedes this with runtime procedural
generation. However, ADR-096 is not being replaced; it's being repurposed.

The amendment clarifies:
- What ADR-096 still owns: the mask+PNG output format contract
- What changed: they're now produced at runtime by the materializer, not static content
- How to find the runtime path: see ADR-106

The DRIFT/index regeneration is housekeeping:
- Mark ADR-096 with `implementation_status: amended` (not retired)
- Add a "related" link to ADR-106 (symmetric, not supersedes-by)
- Regenerate `docs/adr/README.md` and `docs/adr/DRIFT.md` with new ADR-096 status

This is a 1-point chore that unblocks epic 52.

## Technical Scope

**In scope:**
- Open `docs/adr/096-cavern-renderer-revival.md`
- Update frontmatter: `implementation_status: amended` (change from `partial`)
- Add to frontmatter: `related_adr: [106]` (symmetric, for cross-reference)
- Update body: add "Status: Amended for Runtime Generation" section that points at ADR-106
- Run `scripts/regenerate_adr_indexes.py` to rebuild `README.md` and `DRIFT.md`
- Verify no local changes break the ADR schema

**Out of scope:**
- Implementing the materializer seam (that's 52-2)
- Changing any code in sidequest-server, sidequest-ui, sidequest-content

## Frontmatter Fields

Per ADR-088 (ADR Frontmatter Schema):
- `title` — keep unchanged
- `status` — keep as `accepted`
- `implementation_status` — change to `amended`
- `related_adr` — add `[106]`
- `superseded_by` — remove (this ADR is not retired; it's repurposed)

## AC Context

| AC | Detail |
|----|--------|
| ADR-096 marked amended | frontmatter has `implementation_status: amended` |
| Related links symmetric | ADR-106 lists ADR-096 as related; ADR-096 lists ADR-106 as related |
| No supersedes-by | ADR-096 has no `superseded_by` field; ADR-106 does not supersede it |
| Indexes regenerated | `docs/adr/README.md` and `docs/adr/DRIFT.md` reflect new status |
| Schema valid | `pf context validate` passes on ADR-096 |

## Testing Strategy

- Ensure `pf context validate` passes on the modified ADR
- Visually inspect `docs/adr/README.md` — ADR-096 should appear in DRIFT section with amended status
- Verify ADR-106 is listed and shows relationship to ADR-096

## Notes

The memory note "ADR schema rules enforced at commit" (from project context) specifies:
- `superseded_by` => `implementation_status: retired` (required)
- When changing `implementation_status`, ensure it matches the logical state

Since we're moving from `partial` to `amended`, this is a metadata clarification with no code changes.
