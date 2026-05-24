---
story_id: "53-6"
jira_key: null
epic: "53"
workflow: "trivial"
---
# Story 53-6: scripts/render_common.slugify prefers item.slug over slugify(name)

## Story Details
- **ID:** 53-6
- **Jira Key:** N/A (no Jira in this project)
- **Workflow:** trivial
- **Stack Parent:** none

## Context
The `scripts/render_common.slugify` function should prefer `item.slug` over `slugify(name)` when generating filenames for rendered images. Current code at line 499 of `scripts/render_common.py` already uses the pattern `slug = item.get("slug") or slugify(item["name"])`, which correctly prefers the slug field when present.

The story is to verify/ensure this pattern is consistently applied across all slug generation code paths in the rendering tooling.

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-05-24

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | - | - |

## Delivery Findings

No upstream findings.

## Design Deviations

None at this stage.
