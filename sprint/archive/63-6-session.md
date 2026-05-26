---
story_id: "63-6"
jira_key: null
epic: "63"
workflow: "tdd"
---
# Story 63-6: Reference UI test parity for LocationPanel (rolled-in from 63-2)

## Story Details
- **ID:** 63-6
- **Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
- **Title:** LocationPanel region-header reference deep-link (re-scoped from "test parity")
- **Points:** 3
- **Priority:** p2
- **Status:** in_progress
- **Repos:** server, ui
- **Workflow:** tdd

## Technical Context

> **RE-SCOPED 2026-05-26 by SM (Captain Carrot), authorized by Keith.** This was filed as a 1-pt UI-only "test parity" story on the assumption the LocationPanel region-header deep-link already shipped via PR #395. **That assumption is false** — verified by SM against both the feature branch and `develop`:
> - `LocationDescriptionPayload` has **no** `reference_url` field — neither in `sidequest-server/sidequest/protocol/models.py` nor `sidequest-ui/src/types/payloads.ts`.
> - `LocationPanel.tsx:83` renders the region header as a plain `<span>{prettifyRegionId(data.region_id)}</span>` — no anchor, no field to drive one.
> - The **only** location-side `reference_url` that 63-4 shipped is `LocationEntity.reference_url` (`payloads.ts:761`), but `LocationPanel` **deliberately does not render entities** (Zork-Problem doctrine, ADR-109 / story 54-9 — see the comment block at `LocationPanel.tsx` top: "Do not add entity chips here").
>
> So a "parity test" had no production behavior to cover. The story is now the **real AC8 feature**: build the region-header deep-link end-to-end (server emit → UI render), then add the mirror test. Now **3 pts, repos: server + ui**. (YAML `repos` field still reads `ui` — `pf sprint story update` has no `--repos` flag; this session's `**Repos:**` line is authoritative for the workflow, and a server branch has been created.)

**Background:**
- Epic 63-2 (Protocol reference_url fields wired to UI panel hyperlinks) was canceled 2026-05-24 after scope was merged into 63-4.
- 63-4 shipped reference_url for CharacterSheet abilities, PartyMember class, JournalEntry, and LocationEntity — but **not** the LocationDescriptionPayload region-header link (Architect descoped it because it entangled server+ui; it became this story).
- This story completes that descoped slice properly.

**Acceptance Criteria (re-scoped — feature, not parity):**
1. **Server:** add `reference_url: str | None` to `LocationDescriptionPayload` (`protocol/models.py`), populated via the existing reference-anchor machinery (`server/reference_anchors.py` / `server/views.py`) the same way CharacterSheet `class_reference_url` is emitted — links the region to `/reference/lore/<pack>/<world>#location-<slug>`. Graceful: `None` when no anchor resolves (no broken link).
2. **UI type:** add `reference_url?: string | null` to `LocationDescriptionPayload` in `src/types/payloads.ts` (mirrors `LocationEntity.reference_url` already present at line ~761).
3. **UI render:** `LocationPanel.tsx` region header (line ~83) renders as `<a target="_blank" rel="noopener" href={reference_url}>` when set, plain `<span>` when null/undefined. Mirror the CharacterSheet class-subtitle anchor pattern. **Entities stay unrendered** (Zork doctrine — do not regress ADR-109).
4. **Test:** `src/components/__tests__/LocationPanel.reference.test.tsx` mirrors `CharacterSheet.reference.test.tsx` — three cases: reference_url set → anchor (href + target=_blank + rel~=noopener); null → plain text, no link; omitted → plain text, no link.
5. **OTEL:** confirm the location region-anchor emission rides the existing `telemetry/spans/reference.py` span (added in 63-4) so the GM panel can verify location anchors resolve — not just character ones.

**Production Code Under Test / To Build:**
- Server payload: `sidequest-server/sidequest/protocol/models.py` → `LocationDescriptionPayload` (add field)
- Server emit: `sidequest-server/sidequest/server/reference_anchors.py`, `server/views.py` (resolve + populate; follow the CharacterSheet/JournalEntry precedent already there)
- UI type: `sidequest-ui/src/types/payloads.ts:753` `LocationDescriptionPayload` (add field)
- UI component: `sidequest-ui/src/components/LocationPanel.tsx:83` (region header → conditional anchor)
- Pattern reference (anchor render + test): `CharacterSheet.tsx` class subtitle + `CharacterSheet.reference.test.tsx` (the `class_reference_url` cases at lines 54–68)

**Sibling Test (Do Not Duplicate):**
- Existing test: `sidequest-ui/src/components/__tests__/LocationPanel.test.tsx`
- Coverage: prose, terrain badge, overlay pips, entity manifest (Zork doctrine), overlay prose paragraphs
- .reference.test.tsx scope: ONLY the reference_url / deep-link-into-wiki behavior

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-26T15:56:09Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-26 | 2026-05-26T15:04:28Z | 15h 4m |
| red | 2026-05-26T15:04:28Z | 2026-05-26T15:35:26Z | 30m 58s |
| green | 2026-05-26T15:35:26Z | 2026-05-26T15:42:20Z | 6m 54s |
| spec-check | 2026-05-26T15:42:20Z | 2026-05-26T15:44:01Z | 1m 41s |
| verify | 2026-05-26T15:44:01Z | 2026-05-26T15:48:02Z | 4m 1s |
| review | 2026-05-26T15:48:02Z | 2026-05-26T15:54:27Z | 6m 25s |
| spec-reconcile | 2026-05-26T15:54:27Z | 2026-05-26T15:56:09Z | 1m 42s |
| finish | 2026-05-26T15:56:09Z | - | - |

## Story Context — Reference Pages v3 Plan

Epic 63 is implementing reference pages v3 with:
- Per-pack chrome (palette + fonts + dinkus glyphs)
- World-name hero rendering
- Lore section from lore.yaml
- Locked contents rail with IntersectionObserver scroll-spy
- Server-rendered HTML (not React) via `reference_renderer.py`

**Protocol Fields Added (Server-Side):**
Per the v3 plan, the following protocol objects now carry optional `reference_url` fields:
- `AbilityDefinition.reference_url` — links to class signature abilities in /reference/rules/<pack>
- `PartyMember.class_reference_url` — links to class definition in /reference/rules/<pack>
- `JournalEntry.reference_url` — links to lore/location/person entries in /reference/lore/<pack>/<world>
- `LocationEntity.reference_url` — links to location features in /reference/lore/<pack>/<world>
- **LocationDescriptionPayload.reference_url** — links region header to /reference/lore/<pack>/<world>#location-<slug>

**Test Pattern (from CharacterSheet.reference.test.tsx):**
1. Component with reference_url renders as `<a target="_blank" href={url} rel="noopener">` 
2. Component without reference_url (null) renders as plain text
3. Component with reference_url field omitted entirely (undefined) renders as plain text
4. Both cases tested side-by-side for symmetry

## Sm Assessment

**Story selected:** 63-6 — Reference UI test parity for LocationPanel. 1 point, p2, tdd, `ui` only.

**Why this is clean and ready for RED:**
- This is the descope Architect explicitly recommended in 63-4 (session line 290/398): carve the LocationPanel reference test into a standalone UI-only story rather than polluting the 63-4 server diff. 63-6 IS that carve-out.
- The production code (`LocationDescriptionPayload.reference_url` → region header anchor) already shipped on develop via PR #395. **This story adds the missing TEST only** — no production change is expected.
- The template is concrete and present on disk: `CharacterSheet.reference.test.tsx` (2616 bytes). Igor mirrors its three-case structure (reference_url set → `<a target="_blank">`; null → plain text; omitted → plain text) against `LocationPanel.tsx`.
- A sibling `LocationPanel.test.tsx` already exists — the new `.reference.test.tsx` is scoped strictly to deep-link behavior, no coverage overlap.

**Scope guard for downstream:** If RED reveals the production code does NOT actually wire `reference_url` on the region header, that is a flag back to SM — do not silently add production code to "make the test pass." Test-parity only. Genuine missing wiring = scope decision, not a quiet fix.

**Merge gate:** clear. No open PRs on sidequest-ui. No blocking stories.

**Setup correction logged:** sm-setup returned `workflow_type: stepped` for a `tdd` story; verified via `pf workflow type tdd` → **phased**. Routing follows phased exit protocol (→ TEA/red), not the stepped start-command path.

---

### SM Assessment — ADDENDUM (re-scope, 2026-05-26)

**The "clean test-parity" assessment above is SUPERSEDED.** When Igor (TEA) hit the RED-phase context gate, two things surfaced:

1. **Missing artifact:** `context-story-63-6.md` was never created by sm-setup, even though the setup-exit `resolve-gate` reported `status: ready` (with `story-context-validated → create_context` in its recovery config that never fired). SM created the context manually via the gate-recovery pipeline — it now validates (`pf validate context-story 63-6` → exit 0).

2. **False premise (the bigger one):** the story assumed the LocationPanel region-header deep-link "already shipped via PR #395." SM verified against `develop` + branch that it **never existed** — no `reference_url` on `LocationDescriptionPayload` (server `protocol/models.py` or ui `types/payloads.ts`), and `LocationPanel.tsx:83` is a plain `<span>`. The only location `reference_url` that shipped is `LocationEntity.reference_url`, but entities are deliberately unrendered (ADR-109).

**Decision (Keith, 2026-05-26):** Re-scope 63-6 from "1pt UI test parity" to the real AC8 **feature** — build the region-header deep-link end-to-end. Now **3 pts, repos: server + ui**, 5 ACs (see Technical Context). Server branch `feat/63-6-ref-locationpanel-test-parity` created off develop to match the existing UI branch.

**Process learning:** the sm-setup-exit gate passed without the story context actually being on disk. Worth a look — a setup gate that green-lights a missing required artifact is the reason Igor had to bounce. (Filed mentally; not blocking this story.)

**Scope guard now lifted:** GREEN *does* add production code this time — that is the point of the story, not a quiet expansion. Igor should write RED tests that assert the not-yet-built behavior (they will fail correctly), and Ponder builds server+ui to green them.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev/Ponder)

**Test Files:**
- `sidequest-ui/src/components/__tests__/LocationPanel.reference.test.tsx` (new, 4 tests) — region-header anchor render behavior. Mirrors `CharacterSheet.reference.test.tsx`.
- `sidequest-server/tests/server/test_location_description_emit.py` (extended, +4 tests) — payload field contract + handler wiring.

**Tests Written:** 8 tests covering AC1–AC4. AC5 (OTEL) deferred to Dev — see Delivery Findings.

**RED verification (run directly, NOT via testing-runner — it would clobber this live `.session/63-6-session.md`):**
- Server: `4 failed` — model `accepts` raises `extra_forbidden` (field absent); `defaults_none` + both wiring tests fail on missing `reference_url`. The positive wiring test reaches `emit_fn.assert_called_once()` (fixture sound) and fails only on the value — it will go green once Dev resolves the region against POI slugs and sets the field.
- UI: `2 failed | 2 passed` — the two failing tests drive the new anchor (`getByRole('link')` throws against today's plain `<span>`); the two passing tests are the null/omitted regression guards (correctly green now, must stay green after GREEN).

**Key discovery (resolves the SM-flagged "no known-location registry" worry):** the positive path IS buildable. `sidequest-server/sidequest/server/reference_renderer.py::_load_poi_image_slugs(world_dir)` already reads `history.yaml points_of_interest[].slug` (slugified) — that is the authoritative set of regions with a `/reference/lore#location-<slug>` anchor (Story 63-8). Dev resolves: `slugify(region_id) ∈ poi_slugs` → `build_lore_url(pack, world, "location", region_id)`, else `None`. The journal handler's `location_names = ()` stub (`journal_request.py:186`) is NOT the only source — POIs are.

### Rule Coverage

| Rule (lang-review) | Test(s) | Status |
|---|---|---|
| python #1 No silent fallback (AC1: graceful, no guessed URL) | `test_emit_reference_url_is_none_when_region_has_no_poi_anchor` | failing (RED) |
| python #3 Type at boundary (`reference_url: str \| None`) | `test_location_description_payload_accepts_reference_url` / `_defaults_none` | failing (RED) |
| ts target=_blank security (`rel` must contain `noopener`) | UI `renders ... as a target=_blank anchor` | failing (RED) |
| Wiring (CLAUDE.md: every suite needs a wiring test) | `test_emit_populates_reference_url_when_region_is_a_known_poi` (non-test caller `_maybe_emit_location_description`, real fixture round-trip) | failing (RED) |
| ADR-109 Zork doctrine not regressed by the new anchor | UI `does NOT render entities even when reference_url is set` | failing (RED) |
| python #4 OTEL on subsystem decision (AC5) | — deferred to Dev (Delivery Finding) | not covered |

**Rules checked:** 5 of 6 applicable have RED coverage; AC5/OTEL filed as a Delivery Finding for Dev to wire span + mirror-test together.
**Self-check:** 0 vacuous tests. The 2 green UI tests are meaningful regression guards (assert no-link AND label-present), not vacuous.

**Handoff:** To Ponder Stibbons (Dev) for GREEN — server field+emit, UI type+render. Two repos, branches `feat/63-6-ref-locationpanel-test-parity` on both server and ui.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — all 8 story tests pass; lint + typecheck clean on changed files.

**Implementation (minimal, both repos):**
- **Server model:** `LocationDescriptionPayload.reference_url: str | None = None` (`protocol/models.py`).
- **Server resolver:** new pure `reference_url_for_region(pack, world, region_id, known_location_slugs)` in `reference_anchors.py` — `slugify(region_id) ∈ slugs → build_lore_url(...)`, else `None`. Mirrors the sibling `reference_url_for_*` functions.
- **Server wiring:** `_maybe_emit_location_description` loads POI slugs (`load_poi_image_slugs(world_dir)`), resolves the region, and sets `reference_url` on the emitted payload.
- **OTEL (AC5 — completed, not deferred):** emits `reference_url_attached_span` / `reference_url_skipped_span` (kind="location") for the anchor decision, mirroring `journal_request.py`. The GM panel now sees location anchors fire.
- **POI loader promoted:** `_load_poi_image_slugs` → public `load_poi_image_slugs` (one internal caller updated) so the handler doesn't cross-import a private symbol (resolves TEA finding #1).
- **UI type:** `reference_url?: string | null` on `LocationDescriptionPayload` (`types/payloads.ts`).
- **UI render:** `LocationPanel.tsx` region header → `<a target="_blank" rel="noopener noreferrer">` when set, `<span>` otherwise. Entities stay unrendered (ADR-109 — verified by the Zork-doctrine guard test).

**GREEN verification (run directly — testing-runner would clobber this live session):**
- Server: `tests/server/test_location_description_emit.py` + `test_reference_anchors.py` → **27 passed**.
- UI: `LocationPanel.reference.test.tsx` + `LocationPanel.test.tsx` → **16 passed** (4 new + 12 existing, no Zork regression).
- Lint: server ruff clean; UI eslint clean. Typecheck: changed-file pyright clean; UI `tsc --noEmit` clean.

**Pre-existing failures (NOT mine — flagged for Reviewer):** the full server suite shows `14 failed, 8109 passed`. All 14 are in subsystems this story does not touch: `test_61_12_output_format_compaction` (8, confrontation rule-tokens), `test_prompt_cache_attribution_otel` (1, narrator prompt-cache zones — spot-checked, it's about Primacy/Valley cache flags, not my reference spans), `test_audit_namegen_corpora` (4, live corpus audit), `test_dogfight_playtest_smoke` (1). None import the location/reference code path. Consistent with the in-flight epic-59 / corpus-expansion churn on develop. *Did not run a prior commit to "prove" this (banned) — confirmed by subsystem inspection instead.*

**Branches pushed:** `feat/63-6-ref-locationpanel-test-parity` on both server and ui.
**Handoff:** To Granny Weatherwax (Reviewer).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

Structural gate passed (AC coverage, implementation-complete, TEA+Dev deviation subsections). Substance check against the re-scoped ACs:

| AC | Spec | Code | Verdict |
|----|------|------|---------|
| 1 server field+emit | `reference_url` on payload, resolved via anchor machinery, graceful None | `models.py` field (default None); handler resolves via `reference_url_for_region` + `load_poi_image_slugs`, sets it; None when region not in POI manifest | ✓ |
| 2 UI type | optional `reference_url` | `payloads.ts` `reference_url?: string \| null` | ✓ |
| 3 UI render | anchor when set / span otherwise; entities stay unrendered | `LocationPanel.tsx` conditional `<a target=_blank rel="noopener noreferrer">`; no entity rendering added | ✓ |
| 4 test | mirror CharacterSheet, 3 cases | `LocationPanel.reference.test.tsx` 3 cases + Zork-doctrine guard | ✓ |
| 5 OTEL | rides existing reference span | `reference_url_attached`/`_skipped` spans (kind="location") emitted at the decision | ✓ |

**Architectural notes (not mismatches):**
- **Single construction site** confirmed — `LocationDescriptionPayload` is built in exactly one place (`websocket_session_handler.py:1091`), which the handler change fully covers. Session-resume uses the same function (`room_id_override`), so that path is covered too. No bypass.
- **Anchor scheme is internally consistent (no broken links).** The membership gate is `slugify(region_id) ∈ poi_slugs`, and the href is `build_lore_url("location", region_id)` → `#location-{slugify(region_id)}`. Since the matched POI slug equals `slugify(region_id)` and the geography presenter emits `location-{slug}` cards from the same `slugify`-normalised manifest (`reference_renderer.py:955` contract), a link is emitted only when it will resolve in-page. Region/POI slug divergence in real worlds resolves to None (graceful) — the 63-8 slug-consistency concern Dev already filed, correctly out of scope here.
- **`reference_url_for_region` as a new pure function** (vs reusing `reference_url_for_location_entity`) is the right call — slug-set membership vs name-tuple membership are genuinely different contracts. Reuse-first principle respected: it's a thin mirror over the existing `build_lore_url` + `slugify`, not new infrastructure.
- **Diff is right-sized:** server +190 (incl. 126 test lines), UI +123 (incl. 105 test). No scope creep.

**Decision:** Proceed to review (TEA verify next).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8 (server: models, reference_anchors, reference_renderer, websocket_session_handler, test_location_description_emit; ui: LocationPanel, LocationPanel.reference.test, payloads)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | New `reference_url_for_region` correctly read as deliberate parallel-API mirror, not duplication. |
| simplify-quality | 1 finding (low) | Redundant `PayloadWithRef` type intersection in the UI test — `reference_url` is on the base `LocationDescriptionPayload` post-Dev. |
| simplify-efficiency | clean | OTEL `with span(): pass` correctly read as established idiom; no over-engineering. |

**Applied:** 1 fix — removed the `PayloadWithRef` intersection in `LocationPanel.reference.test.tsx`; the factory now types directly against `LocationDescriptionPayload`. (Rated low-confidence by the teammate only because it couldn't confirm the base field was live; as the test's author I verified it is — dead type-cruft, safe to remove per the dead-code principle.) Committed `0c516c6`.
**Flagged for Review:** 0 medium-confidence findings.
**Noted:** 0 low-confidence observations left unaddressed.
**Reverted:** 0.

**Regression check after the fix:** UI reference test `4 passed`; `tsc --noEmit` clean; eslint clean.

**Overall:** simplify: applied 1 fix

**Quality Checks:** server ruff + changed-file pyright clean (GREEN phase); UI eslint + tsc clean. Story tests green both repos (server 27, UI 16). Pre-existing 14 server-suite failures remain in untouched subsystems (flagged by Dev — not this story's diff).
**Handoff:** To Granny Weatherwax (Reviewer).

## Subagent Results

All received: Yes (both enabled subagents returned).

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | PASS | tests green (27 server, 16 UI), ruff/eslint/tsc clean, 0 smells in diff, rename clean, pre-existing 14 failures confirmed unrelated, OTEL spans fire | Accept |
| 2 | reviewer-security | Yes | clean | 0 — URL fully server-constructed + slugify-sanitised, React attr-escaped, rel="noopener noreferrer" present | Accept |

**Disabled via `workflow.reviewer_subagents` settings (not spawned, do not block the gate):** reviewer-edge-hunter, reviewer-silent-failure-hunter, reviewer-test-analyzer, reviewer-comment-analyzer, reviewer-type-design, reviewer-simplifier, reviewer-rule-checker. (Reviewer hunted edge/silent-failure manually — see Finding R1.)

## Reviewer Assessment

**Verdict:** APPROVED (with one non-blocking Minor finding for follow-up)

**Mechanical [PRE]:** preflight PASS — 27 server + 16 UI tests green, ruff/eslint/tsc clean, zero diff smells. The 14 pre-existing full-suite failures independently confirmed unrelated (no imports of LocationDescriptionPayload/reference_url/reference_anchors/reference_renderer/handler; domains are dogfight, namegen corpora, prompt-cache OTEL). Not this story's diff.

**Security [SEC]:** clean. `reference_url` is fully server-constructed via `build_lore_url` with `slugify` on every segment (`[a-z0-9-]` only — no scheme/path/fragment injection), `pack`/`world`/`region_id` come from server session state (not player WS input), React escapes the href attribute, and the new anchor carries `rel="noopener noreferrer"`. No `dangerouslySetInnerHTML`. [SEC] returned 0 findings.

**My own critical read (the subagent set was reduced — edge/silent-failure hunters disabled, so I hunted manually):**

- **VERIFIED — no broken links by construction.** Membership gate `slugify(region_id) ∈ poi_slugs` and href `build_lore_url("location", region_id)` use the same `slugify`, and the lore page emits `location-{slug}` cards from the same manifest. A link is emitted only when it resolves. Region/POI slug divergence → None (graceful). Sound.
- **VERIFIED — graceful default + back-compat.** `reference_url` optional/nullable both sides; old snapshots and region-mode worlds degrade to plain-text header. No `extra=forbid` break for existing producers.
- **VERIFIED — OTEL honoured.** Both attach and skip paths emit spans (mirrors `journal_request.py`); GM panel sees location anchors fire.
- **VERIFIED — Zork doctrine intact.** The anchor wraps only the region label; no entity rendering added. Guard test pins it.

**Finding R1 — Minor (non-blocking, recommend follow-up): unguarded `load_poi_image_slugs` in the graceful turn-path.**
- `_maybe_emit_location_description` is written to degrade gracefully — it emits watcher events (`world_dir_lookup_failed`, `no_source`) rather than raising. The new code calls `load_poi_image_slugs(world_dir)`, which **raises `ValueError` on malformed `history.yaml`**, unguarded; none of the 5 call sites wrap it locally.
- Impact: a content-author YAML typo (realistic — Jade authors content per CLAUDE.md) would propagate an exception through a live per-room-change emit, letting a *cosmetic* deep-link feature disrupt a *load-bearing* location description.
- **Why Minor, not blocking:** it fails LOUD (a clear `ValueError`, not silent corruption — defensible under "No Silent Fallbacks"); the existing `assemble_lore_page` caller has identical exposure (no regression in codebase tolerance); and all valid content works. So this is a hardening opportunity, not a correctness defect.
- **Recommended fix (a future hardening story or a quick amend):** wrap the POI-load + region resolution; on failure emit the already-existing `reference_url_failed_span` (ERROR — loud, GM-panel-visible, *not* silent) and set `reference_url = None` (graceful). ~8 lines. Best-of-both: loud + non-fatal. Resolution: **D (defer)** unless Keith wants it folded in now.

**Decision:** Approve. The implementation is correct, secure, tested, and spec-aligned. R1 is a narrow, loud-failing edge with pre-existing precedent — documented for follow-up, not a merge blocker.

## Delivery Findings

<!-- append-only; do not edit other agents' entries -->

### Reviewer (review)
- **Improvement** (non-blocking): harden `_maybe_emit_location_description` against a malformed `history.yaml` — `load_poi_image_slugs` raises `ValueError` and is called unguarded in an otherwise graceful path. Wrap it, emit `reference_url_failed_span` (ERROR) on failure, degrade `reference_url` to `None`. Affects `sidequest-server/sidequest/server/websocket_session_handler.py::_maybe_emit_location_description` (~8 lines) + a malformed-YAML test. Same exposure pre-exists at `reference_renderer.py::assemble_lore_page`. *Found by Reviewer during review.*

### Dev (implementation)
- No new upstream findings. TEA's findings #1 (private POI-loader import) and #2 (AC5/OTEL) are both resolved in this diff: loader promoted to public, attached/skipped spans wired. Finding #3 (slug-consistency) remains 63-8's concern — unchanged, graceful-None holds.

### TEA (test design)
- **Improvement** (non-blocking): the known-location source for the region anchor is `_load_poi_image_slugs` — currently a **private** (`_`-prefixed) function in `reference_renderer.py`. Dev should reuse it but consider promoting it to a shared, non-underscore helper (e.g. in `reference_anchors.py`) rather than cross-importing a private symbol into `websocket_session_handler.py`. Affects `sidequest-server/sidequest/server/reference_renderer.py` + `reference_anchors.py` (extract/relocate). *Found by TEA during test design.*
- **Gap** (non-blocking): AC5 (OTEL) has no RED test. The handler should emit the existing `reference_url_attached_span` (`sidequest-server/sidequest/telemetry/spans/reference.py`) when it sets the region `reference_url`, so the GM panel sees location anchors fire — not just character/journal ones. Test pattern to mirror: `tests/server/test_location_overlay_emit_otel.py`. Affects `websocket_session_handler.py::_maybe_emit_location_description` + a new OTEL emit test. Dev should wire span + test together in GREEN. *Found by TEA during test design.*
- **Question** (non-blocking): region_id→anchor relies on `slugify(region_id)` matching the POI slug the lore page emits. If a world's cartography region key diverges from its `history.yaml` POI slug (the known 63-8 slug-consistency risk), the link resolves to `None` (correct, graceful) but the region silently has no wiki link. Out of scope for 63-6 (it's 63-8's slug-consistency job), but worth a note if Dev sees real worlds where regions that *should* link don't. *Found by TEA during test design.*

## Design Deviations

### TEA (test design)
- **AC5 (OTEL) covered by a Delivery Finding, not a RED test**
  - Spec source: context-story-63-6.md, AC5
  - Spec text: "A location anchor resolution emits (or is covered by) the `reference.py` span so the GM panel shows location anchors firing."
  - Implementation: No RED test for the span; filed as a Gap finding directing Dev to emit `reference_url_attached_span` and mirror `test_location_overlay_emit_otel.py` during GREEN.
  - Rationale: span-capture needs the watcher harness; bundling span emit + its test in GREEN is cleaner than a brittle RED span assertion, and keeps the RED suite focused on the field/render contract. Dev owns both.
  - Severity: minor
  - Forward impact: Reviewer must confirm the OTEL span ships in GREEN (not silently dropped) — the OTEL principle is load-bearing for this subsystem.
- **Region resolution tested at the wiring layer, not as a new pure resolver**
  - Spec source: context-story-63-6.md, Technical Guardrails (reference_anchors.py)
  - Spec text: "Resolve the location anchor the same way ... follow the CharacterSheet precedent."
  - Implementation: Reused the already-tested `build_lore_url` + `reference_url_for_location_entity`/POI-slug logic; asserted the region→URL/None outcome at the `_maybe_emit_location_description` wiring layer rather than mandating a new `reference_url_for_region` pure function.
  - Rationale: avoids over-specifying Dev's seam; the pure builders are already covered in `test_reference_anchors.py`. If Dev extracts a region helper, a unit test there is welcome but not required by RED.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)
- **Added a new pure resolver `reference_url_for_region` instead of reusing `reference_url_for_location_entity`**
  - Spec source: context-story-63-6.md, Technical Guardrails
  - Spec text: "Resolve the location anchor the same way ... follow the CharacterSheet precedent."
  - Implementation: New function taking `known_location_slugs: frozenset[str]` (slug membership) rather than the entity resolver's `known_location_names: tuple[str, ...]` (name membership).
  - Rationale: a region header keys off `region_id` (a slug) matched against the POI **slug** manifest, whereas `reference_url_for_location_entity` matches a display **name**. Different membership semantics warrant a separate, clearly-named function — still a thin mirror of the sibling.
  - Severity: minor
  - Forward impact: none — additive; sibling resolvers untouched.
- **Promoted `_load_poi_image_slugs` to public `load_poi_image_slugs`**
  - Spec source: TEA Delivery Finding #1 (test design)
  - Spec text: "Dev should reuse it but consider promoting it ... rather than cross-importing a private symbol."
  - Implementation: Renamed the function in `reference_renderer.py` and updated its one internal caller; handler imports the public name.
  - Rationale: avoids importing a `_`-prefixed symbol across modules (a smell Reviewer would flag); minimal churn (one caller).
  - Severity: minor
  - Forward impact: none — pure rename, no behavior change, no remaining references to the old name.

### Architect (reconcile)

**Verification of prior entries:**
- TEA "AC5 (OTEL) covered by a Delivery Finding, not a RED test" — accurate when written, but **status changed**: Dev wired `reference_url_attached_span`/`reference_url_skipped_span` in GREEN, and Reviewer/preflight confirmed both paths fire. The deferral was resolved within this story, not carried forward. Entry stands as the audit trail; no longer an open gap.
- TEA "region resolution tested at the wiring layer, not as a new pure resolver" — superseded by Dev's choice to add `reference_url_for_region` (a pure resolver) anyway; both the unit-level resolver and the wiring test now exist. Over-delivered relative to the deviation. Accurate as a record of TEA's RED-phase decision.
- Dev "new pure resolver `reference_url_for_region`" and "promoted `_load_poi_image_slugs`" — both verified accurate against the diff. Spec sources valid (context-story-63-6.md exists; TEA finding #1 real).

**Missed deviations:**
- **Story re-scoped 1pt UI test-parity → 3pt server+ui feature; YAML `repos` field not updated**
  - Spec source: sprint/epic-63.yaml, story 63-6 `repos` field
  - Spec text: "repos: ui"
  - Implementation: Work spans server + ui; the session `**Repos:**` line reads `server, ui` (authoritative for the workflow) and both feature branches exist, but the sprint YAML `repos` still reads `ui` because `pf sprint story update` exposes no `--repos` flag.
  - Rationale: CLI limitation, not an authoring choice. Flagged so SM's finish ceremony creates PRs for BOTH repos (server + ui), not just ui.
  - Severity: minor
  - Forward impact: **SM finish must merge both server and ui PRs.** If finish reads the YAML `repos` field it will miss the server repo — use the session `**Repos:**` line.
- **AC1 named `server/views.py` as an emit site; it was not touched**
  - Spec source: context-story-63-6.md, AC1 / "Production Code Under Test"
  - Spec text: "populated via the existing reference-anchor machinery (`server/reference_anchors.py` / `server/views.py`)"
  - Implementation: `LocationDescriptionPayload` is constructed in exactly one place — `websocket_session_handler.py::_maybe_emit_location_description` — which is where the field is populated. `views.py` constructs no `LocationDescriptionPayload`, so it was correctly left untouched.
  - Rationale: the spec listed views.py speculatively ("the same way CharacterSheet is emitted"); the actual single construction site is the WS handler. No functional gap.
  - Severity: trivial
  - Forward impact: none.
- **Deferred hardening: unguarded `load_poi_image_slugs` in the graceful turn-path (Reviewer R1)**
  - Spec source: context-story-63-6.md, AC1 ("Graceful: None when no anchor resolves") + ADR-006 graceful degradation
  - Spec text: "Graceful: `None` when no anchor resolves (no broken link)."
  - Implementation: Resolution returns None for the no-anchor case (compliant), BUT `load_poi_image_slugs` raises `ValueError` on malformed `history.yaml` and is called unguarded; a content typo could propagate through a live emit. Deferred per Reviewer (Minor, non-blocking) — fails loud, identical pre-existing exposure at `assemble_lore_page`.
  - Rationale: narrow, loud-failing edge with codebase precedent; blocking a clean story on it would be over-rigorous. Documented for a follow-up hardening (catch → `reference_url_failed_span` → degrade to None).
  - Severity: minor
  - Forward impact: a future hardening story (or quick amend if Keith elects) should wrap the POI load; until then a malformed `history.yaml` disrupts the location emit rather than degrading the deep-link alone.