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
**Phase:** finish
**Phase Started:** 2026-05-24T22:15:54Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | - | - |

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `scripts/render_common.py` - slug resolution now checks `item["slug"]` → `item["id"]` → `slugify(item["name"])`

**Tests:** 49/49 passing (pre-existing failures in test_claude_tab.py and test_playtest_split.py unrelated)
**Branch:** feat/53-6-render-common-slugify-prefer-item-slug (pushed)

**Handoff:** To review phase

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 | confirmed 1 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 returned, 1 with findings)
**Total findings:** 1 confirmed, 0 dismissed, 0 deferred

### Devil's Advocate

What if someone submits a content PR with a creature id of `../../../etc/shadow`? The `slugify()` function — which IS the sanitization layer — replaces `/` with `-` and strips dots, so any value run through it becomes filesystem-safe. But the new `item.get("id")` path skips `slugify()` entirely. The items dictionary flows from YAML files authored by content contributors. While today those are trusted authors committing to a repo with PR review, the code should not assume its inputs are pre-sanitized. Pathlib's `/` operator does NOT normalize `..` components — `Path("/a/b") / "../evil.png"` produces `/a/b/../evil.png` which resolves outside the tree. This means a crafted creature ID could write a PNG to any filesystem location writable by the operator running the script. The blast radius is limited (operator machine, local disk, requires compromised content YAML), but the fix is trivial: wrap `item.get("id")` in `slugify()`. The entire point of having `slugify()` is to be the sanitization barrier between arbitrary text and filesystem paths. Bypassing it defeats the purpose, even for "trusted" data. Defense-in-depth says: sanitize at the boundary where text becomes a path component, always.

### Rule Compliance

1. **No Silent Fallbacks** — The `or` chain is not a "silent fallback" in the CLAUDE.md sense (that rule targets config/service routing). This is a prioritized resolution chain where each step is intentional. COMPLIANT.
2. **No Stubbing** — No stubs. COMPLIANT.
3. **Verify Wiring** — The `id` field flows from `generate_creature_images.py:52` into `render_batch` correctly. COMPLIANT.

## Reviewer Assessment

**Verdict:** APPROVED (after in-review fix)

| Severity | Issue | Location | Resolution |
|----------|-------|----------|------------|
| [MEDIUM] | [SEC] Path traversal: `item.get("id")` bypassed `slugify()` sanitization | `scripts/render_common.py:499` | Fixed in 75e65f6 — id now wrapped in `slugify()` |

**Observations:**
1. [SEC] `item.get("id")` bypasses slugify sanitization — confirmed by security subagent. CWE-22 path traversal. Current content is safe but code should be defense-in-depth.
2. [VERIFIED] Tests pass — 8/8 in test_poi_output_routing.py. Evidence: preflight subagent confirmed GREEN.
3. [VERIFIED] Functional intent correct — creature items carry `id` field (e.g. `aboleth`, `mummy_lord`) which should be used as stable filename. Evidence: `generate_creature_images.py:52` passes `creature.get("id", "unknown")`.
4. [VERIFIED] Existing callers (POI, portrait) unaffected — POI items already set `"slug"` explicitly (generate_poi_images.py:68), portrait items set `"slug"` from `char.get("id")` (generate_portrait_images.py:61). The new `item.get("id")` only activates for creatures.
5. [VERIFIED] No silent fallback violation — the `or` chain is an intentional priority resolution, not a masked configuration failure. Compliant with CLAUDE.md "No Silent Fallbacks" rule.

[EDGE] N/A (disabled)
[SILENT] N/A (disabled)
[TEST] N/A (disabled)
[DOC] N/A (disabled)
[TYPE] N/A (disabled)
[SEC] Path traversal via unsanitized id field — confirmed, medium severity
[SIMPLE] N/A (disabled)
[RULE] N/A (disabled)

**Data flow traced:** YAML creatures.yaml → collect_creatures() → item["id"] → render_batch line 499 → Path join → filesystem write. The `id` value never passes through sanitization.

**Error handling:** `item.get("id")` returns None if missing, which is falsy and falls through to `slugify()`. No crash risk. The concern is not errors but malicious input.

**Fix is trivial:** Change `item.get("id")` to `slugify(item.get("id"))` (slugify handles None? No — needs guard). Better: keep the current `or` chain but wrap the id:
```python
slug = item.get("slug") or (item.get("id") and slugify(item["id"])) or slugify(item["name"])
```

**Handoff:** To SM for finish-story

## Delivery Findings

- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): The `slugify()` function could accept `None` gracefully (return empty string) to simplify resolution chains. Affects `scripts/render_common.py` (slugify function signature). *Found by Reviewer during code review.*

## Design Deviations

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- No undocumented deviations found. The implementation matches the story intent (prefer item.slug/id over computed slug).