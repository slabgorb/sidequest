---
story_id: "63-10"
jira_key: null
epic: "63"
workflow: tdd
---

# Story 63-10: Lore surface renders WORLD lore only — stop rendering genre-level lore (Keepers/Maw) + banner intro; resolve genre/world contradiction

## Story Details

- **ID:** 63-10
- **Jira Key:** (none — personal project, no Jira)
- **Epic:** 63 — Reference pages v3 — chrome + wiki-like anchor links
- **Workflow:** tdd
- **Type:** bug
- **Priority:** p2
- **Points:** 3
- **Repos:** server  <!-- re-scoped from server,content: Architect ratified a pure server-side merge-scope change; no content edit needed. See Design Deviations. -->
- **Branch:** feat/63-10-lore-surface-world-only

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-05-27T20:45:00Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27T20:45:00Z | - | - |

## Story Context

See `/Users/slabgorb/Projects/oq-2/sprint/context/context-story-63-10.md` for full technical guardrails and design questions.

### Verified Premise (per TEA audit against develop HEAD)

- `assemble_lore_page()` in `sidequest-server/sidequest/server/reference_renderer.py` (lines 1119–1134) merges pack-tier flavor files (`LORE_PACK_FLAVOR_FILES`: cultures.yaml, lore.yaml, history.yaml, factions.yaml) on top of world-tier renders, concatenating by stem with label suffix "(genre)".

- This causes `/reference/lore/caverns_and_claudes/beneath_sunden` to render:
  - World's Sünden Deep history (one dwarfhold, no Keepers, honest hole that dug too deep)
  - **THEN** pack's Keeper cosmology tagged "(genre)" (Keepers as intelligences that dwell within, the Maw, etc.)
  - **Result:** direct contradiction — the world explicitly rejects Keepers/Maw/Seven-Sins cosmology.

- The merge was intentionally added in 63-7 (merged; now live on develop). This story is a deliberate reversal, NOT a never-worked bug.

- No formal Acceptance Criteria exist yet in epic YAML — **ARCHITECT DECISION REQUIRED** (see Design Question section below).

## CRITICAL: ARCHITECT DESIGN DECISION REQUIRED BEFORE RED

**The story cannot proceed past setup without Architect ratification of which design to implement.**

### Design Question: Scope of Flavor Exclusion

When rendering `/reference/lore/<pack>/<world>`, should the page include pack-tier lore files?

Three options:

1. **Absolute world-only** (strictest)
   - Exclude ALL pack-tier files from merge.
   - Render only `LORE_WORLD_FILES`: openings.yaml, lore.yaml, locations.yaml.
   - Pack-tier cultures.yaml, history.yaml, factions.yaml, lore.yaml never concatenate.
   - **Impact:** Beneath Sünden renders cleanly (world-only voice). Other worlds (space_opera/orbital_station) lose pack-tier cultures/faction context.

2. **World + factions/cultures** (moderate)
   - Render world-tier files (openings.yaml, lore.yaml, locations.yaml).
   - Also render pack-tier cultures.yaml and factions.yaml (player-accessible flavor).
   - Exclude pack-tier history.yaml and lore.yaml (carry cosmology/Keeper context).
   - **Impact:** Beneath Sünden still renders world-only (its lore.yaml has no cultures/factions). Other worlds inherit pack-level cultures/factions if authored.

3. **World + flavored cultures/factions** (complex)
   - Combine #2 + per-world overrides to strip pack-tier cultures/factions that contradict the world.
   - Requires more content authoring (world-specific overrides).

**Beneath Sünden is the breaking case:** its world lore.yaml explicitly rejects pack-tier Keeper cosmology. All three options converge for this world (only world lore renders).

**For the Architect:**
- Which design is correct for the SideQuest lore hierarchy?
- Should page rendering distinguish pack-tier vs. world-tier content beyond the "(genre)" label?
- Are there other worlds where this decision matters?

**Do NOT proceed to RED until Architect signs off.** The formal ACs depend on this choice.

## Architect Design Decision (RATIFIED)

**Decision:** Option #1 — **Absolute world-only.** Drop `LORE_PACK_FLAVOR_FILES`
from the `assemble_lore_page()` merge entirely. The lore page renders only
world-tier files (`LORE_WORLD_FILES` from `world_dir`). No pack-tier flavor is
concatenated; the `(genre)` label suffix disappears because no pack-flavor
sections render.

**This is a technical-design call, not a product call** — SOUL doctrine resolves
it unambiguously (see Rationale). Ratifying; not escalating to Keith.

### Rationale (grounded in SOUL + 63-7 context)

1. **SOUL — "Crunch in the Genre, Flavor in the World."** The genre tier is the
   *rulebook* (mechanics, archetypes, progression, tone axes). The world tier is
   the *campaign setting* — "factions, geography, legends, named NPCs, cultural
   identity." Lore, cosmology, history, cultures, AND factions are **all
   world-tier concerns** by this doctrine. None of the four `LORE_PACK_FLAVOR_FILES`
   (cultures, lore, history, factions) belongs on a world's lore page as
   authoritative genre-tier content. The 63-7 genre-merge was the actual mistake;
   world-only is the doctrinally-correct default.

2. **63-7 was a chrome/markup-contract story, not a lore-hierarchy ruling.** Its
   commit body (server #409) is entirely about the v3 visual contract: hero
   structure, `.layout`/`.toc` grid, CSS selector alignment, `PACK_TOC` numerals,
   and `_KIND_OVERRIDES["factions"]="cult"` *display naming*. The
   `LORE_PACK_FLAVOR_FILES` merge with the `(genre)` suffix was **incidental
   scaffolding** to surface pack-tier content under the new chrome — not a
   deliberate decision that genre lore belongs on world pages. The `(genre)` label
   was a band-aid acknowledging a tier mismatch. The right fix is to not render it,
   not to label it.

3. **The page is per-world.** `/reference/lore/<pack>/<world>` is the in-world wiki
   for *that world*. It must speak in the world's voice. Concatenating the pack's
   generic backdrop is noise at best (most worlds) and direct contradiction at
   worst (`beneath_sunden` explicitly rejects Keepers/Maw/Seven-Sins).

### Why the other options were rejected

- **Option #2 (world + pack factions/cultures):** Violates SOUL — factions and
  cultures are world-tier, not genre-tier. It would also still leak pack
  `cultures.yaml` (Surface Folk / **Keeper Titles**) onto `beneath_sunden`, whose
  cosmology has no Keepers. Half-fixes the contradiction. Rejected.
- **Option #3 (per-world override stripping):** Requires speculative per-world
  override authoring with no current consumer. Violates "no stubbing" / YAGNI and
  expands scope. Rejected.

### Content facts that constrain the decision

- `caverns_and_claudes` pack tier has only `cultures.yaml` + `lore.yaml`. It has
  **no** `history.yaml` and **no** `factions.yaml` — so 2 of the 4 flavor files
  never existed for this pack. The live contradiction is sourced entirely from
  pack `lore.yaml` (Keeper cosmology, `the_maw` section, `setting_anchor` banner
  "The dungeon is the world…") and pack `cultures.yaml` (Surface Folk / Keeper
  Titles).
- `beneath_sunden` is the **only** world in the pack. (The session's references to
  `space_opera/orbital_station` as a "world+factions" beneficiary are a *different
  pack* and not a live consumer of the pack-flavor merge in any contradicting way.)
- `LORE_WORLD_FILES` already includes `cultures.yaml`, `history.yaml`, `lore.yaml`.
  Dropping the pack-flavor merge is therefore **pure subtraction**: a world that
  authors those at its own tier still renders them; a world that doesn't simply
  shows nothing for them (correct — no silent fallback to pack tier).

### Server-only change — NO content change required

This is purely a server-side merge-scope change. `beneath_sunden` already authors
`history.yaml` + `lore.yaml` at the world tier (they render via `LORE_WORLD_FILES`)
and deliberately has no `cultures.yaml`/`factions.yaml` (correct — one dead
dwarfhold + a camp of latecomers has no cultures of its own). No content authoring
needed.

**Dead-code cleanup (same PR):** After removing the merge, `LORE_PACK_FLAVOR_FILES`
has zero real consumers (the `reference_visibility.py:81` reference is a *comment*,
and `PUBLIC_STEMS` there is an orthogonal spoiler allowlist that must NOT change).
Delete the now-unused `LORE_PACK_FLAVOR_FILES` constant and the `flavor_rendered`
block + merge loop (lines ~1119–1134), and update the `assemble_lore_page`
docstring (lines 1099–1106) to drop the pack-flavor description.

### Acceptance Criteria (testable — for TEA RED)

Drive against `assemble_lore_page(pack, world, pack_dir, world_dir)` with
`pack="caverns_and_claudes"`, `world="beneath_sunden"` (real content dirs), and
assert on the returned HTML string:

- **AC1 — Pack cosmology gone.** Output MUST NOT contain pack-tier lore strings:
  `"The Keepers are the intelligences that dwell within"`, `"Every dungeon has a
  Maw"` (from `the_maw`), nor the pack `setting_anchor` `"The dungeon is the
  world"`.
- **AC2 — Pack cultures gone.** Output MUST NOT contain pack-culture names
  `"Keeper Titles"` or `"Surface Folk"` (sourced from pack `cultures.yaml`).
- **AC3 — No `(genre)` tier label.** Output MUST NOT contain the substring
  `"(genre)"` anywhere (no pack-flavor section renders at all).
- **AC4 — World voice present.** Output MUST contain world-tier content: the
  world history fragment `"Sünden Deep was a working hold"`, the geography
  fragment `"One shaft"`, and `world_name` `"Beneath Sünden"`.
- **AC5 — Tier-isolation (synthetic, refactor-stable).** Construct a synthetic
  pack_dir whose pack-tier `lore.yaml` contains a unique sentinel string and a
  world_dir whose world-tier files do NOT contain it; assert the sentinel is
  ABSENT from the output. (Behavioral — proves pack_dir flavor is not read/merged
  without grepping production source, per the No-Source-Text-Wiring-Tests rule.)
- **AC6 — World-tier files still render (regression guard).** For a world that
  authors world-tier `cultures.yaml`/`history.yaml`/`lore.yaml`, those sections
  still render (they come from `LORE_WORLD_FILES`, which is unchanged). For
  `beneath_sunden` specifically: world `history.yaml` renders; no `cultures`
  section appears (it has none at the world tier — correct, not a fallback to
  pack).
- **AC7 — Dead constant removed.** `LORE_PACK_FLAVOR_FILES` no longer exists in
  `reference_renderer.py` (assert via `hasattr`/`getattr` reflection on the module,
  NOT a source grep — refactor-stable tripwire). `PUBLIC_STEMS` in
  `reference_visibility.py` is unchanged.

**OTEL:** No new span required. This is deterministic reference-page assembly (a
static in-world wiki), not a runtime game subsystem — the OTEL lie-detector
principle targets narrator/engine improvisation, not page rendering. CLAUDE.md
exempts cosmetic/label-scope changes. Existing reference spans
(`sidequest.reference.toc_missing`, world-name WARN-on-fallback) are untouched and
out of scope.

### Forward finding (NOT this story) — CORRECTED 2026-05-27

`factions.yaml` is not in `LORE_WORLD_FILES`. Post-cut, a *world-authored*
`factions.yaml` would not render on its lore page.

**CORRECTION (the original "no consumer" claim was incomplete):** There was no
live *content* consumer, but there WAS a *test* consumer —
`test_reference_chrome_v3.py::test_factions_yaml_emits_cult_namespaced_ids`
(63-7), which seeds a synthetic pack-tier `factions.yaml` and pins
`id="cult-river-cabal"` rendering on the lore page via the now-removed
pack-flavor merge. My YAGNI note addressed live content only; I should have
flagged the existing test as the consumer. SM correctly escalated this (Group B).

**Live-regression check (Architect, read-only): NONE.** Verified all ten live
genre packs — **zero** ship a pack-tier `factions.yaml`
(`ls genre_packs/*/factions.yaml` → no matches). `beneath_sunden` has no factions
at any tier. So shipping the world-only cut removes **no** factions-on-lore-page
rendering that any real world/user sees today. The only thing that rendered
pack-tier factions was the 63-7 synthetic fixture. **Fixture-only — no follow-up
story required, no `LORE_WORLD_FILES` change required.** YAGNI holds for the live
content; the latent gap (factions absent from `LORE_WORLD_FILES`) stays a future
finding to address *only when* a real world authors world-tier factions.

**RULED test disposition (for TEA):**
- **Rescope** `test_factions_yaml_emits_cult_namespaced_ids` (in
  `test_reference_chrome_v3.py`) to assert factions are **ABSENT** from the lore
  page, consistent with world-only. After seeding a pack-tier `factions.yaml`, the
  `assemble_lore_page(...)` output MUST NOT contain `id="cult-river-cabal"` or
  `id="cult-old-folk"` (pack-tier factions no longer merge). Update the docstring
  to cite 63-10 reversing the 63-7 pack-flavor merge. Rename suggestion:
  `test_pack_tier_factions_absent_from_lore_page`. This is the factions-specific
  facet of AC1–AC3/AC5 and belongs with the other absence guards.
- **Keep AS-IS:** `test_kind_overrides_contains_factions_to_cult_mapping` — it is a
  pure unit assertion on `_KIND_OVERRIDES`, independent of rendering. The kind map
  is untouched by this story (only the lore-page render is removed), so it stays
  GREEN and serves as cheap drift-insurance if a future story ever renders
  world-tier factions. Do NOT delete it.

## Delivery Findings

No upstream findings.

### Reviewer (code review)
- **Improvement** (non-blocking, NIT): `reference_visibility.py:81` still carries the comment `# LORE_PACK_FLAVOR_FILES stems (overlap above plus factions)` — that constant is now deleted, so the comment names a dead symbol. The `factions` stem entry below it is correctly RETAINED (orthogonal spoiler allowlist, pinned by `test_ac7_public_stems_unchanged`); only the comment label is stale. Suggest rewording to "factions stem (pack-tier; allowlisted for the rules surface)" or similar so no reader greps for a constant that no longer exists. *Found by Reviewer during code review.*

## Design Deviations

- **2026-05-27 (SM, GREEN blast-radius ruling):** The world-only cut regressed 11 EXISTING tests across 63-7/8/9 (wider than the dispatch scoped). Ruling: **Group A** (9 tests — `test_reference_humanization_guard.py` ×6, `test_reference_integration.py` ×3, `test_reference_chrome.py::test_listdict_item_ids_remain_namespaced`) have pack-tier fixture content; fixed by Dev moving fixtures to WORLD tier (cultures/lore are in `LORE_WORLD_FILES`, still render — intent-preserving, assertions unchanged). **Group B** (`test_reference_chrome_v3.py::test_factions_yaml_emits_cult_namespaced_ids`, 63-7) pins the deliberately-removed pack-flavor merge of factions onto the lore page; factions is NOT in `LORE_WORLD_FILES` (out-of-scope per Architect) so it can't be fixed by a world-tier move. Escalated to Architect: confirm no LIVE pack regresses factions-on-lore-page, then rescope the test to assert factions ABSENT (the sibling `_KIND_OVERRIDES['factions']='cult'` unit test is untouched and still passes). Architect's "no live consumer" forward-finding was incomplete — there was a test consumer.
- **2026-05-27 (SM, post-Architect-design):** Re-scoped story from `server,content` → `server` only. The Architect ratified Option #1 (absolute world-only) as a pure server-side merge-scope change in `assemble_lore_page` — `beneath_sunden` already authors correct world-tier lore/history and has no cultures/factions, so no content YAML edit is required. The `feat/63-10-lore-surface-world-only` branch created in `sidequest-content` during setup is an empty no-op and was deleted (content repo returned to `develop`). Finish ceremony creates a PR for `sidequest-server` only.

## Reviewer Assessment

**Verdict:** APPROVED

A clean, well-scoped pure-subtraction change. Verified all four scrutiny points empirically (ran the suite with live `caverns_and_claudes` so the `@_live` beneath_sunden tests actually executed — 8/8, not skipped; 162 passed across all patched reference files).

**Deviation audit:**
- **Group A fixture moves (SM ruling):** ACCEPTED. Verified intent-preserving — `cultures.yaml`/`lore.yaml` moved pack→world tier; both are in `LORE_WORLD_FILES` so they still render from the only tier the page now reads. Assertions unchanged; the namespacing (`id="culture-highlander"`) and dev-note suppression invariants still exercise. Coverage not neutered.
- **Group B factions rescope:** ACCEPTED. The flip from "asserts present" → "asserts absent" is the exact inversion of a previously-passing positive on identical fixture input — a legitimate behavior-change reflection, not a vacuous absence check. The `factions → cult` namespace mapping remains covered render-independently by `test_kind_overrides_contains_factions_to_cult_mapping`.
- **server-only re-scope + deleted empty content branch:** ACCEPTED. Architect ruled `beneath_sunden` already authors correct world-tier lore; no content edit needed.

**Four scrutiny points:**
1. **Pure subtraction, no silent fallback?** YES — the merge block and `flavor_rendered` call are deleted; no try/except/default substitution introduced. It *removes* a fallback. `test_ac6` proves it against live content: beneath_sunden has no world-tier cultures → no cultures section, no pack fallback. ✅
2. **Group A real intent-preservation?** YES (see audit). ✅
3. **Factions rescope legitimate?** YES (see audit). ✅
4. **Stale `LORE_PACK_FLAVOR_FILES` references?** Constant deleted; zero code consumers (`test_ac7` hasattr tripwire confirms). Only residue is the stale *comment* at `reference_visibility.py:81` — logged as a NIT. ✅

**Observations:** (1) docstring honestly rewritten with the real rationale (beneath_sunden cosmology contradiction); (2) AC5 synthetic-sentinel test is the textbook refactor-stable tier-isolation pattern with a positive sanity anchor so it can't pass on an empty page; (3) `@_live` content-gated tests have positive world-content anchors (`was a working hold`, `id="file-history"`) so absence assertions can't pass vacuously; (4) AC7 dead-constant check uses the reflection tripwire (legitimate per CLAUDE.md, not a source grep); (5) no OTEL span correctly omitted (deterministic assembly, cosmetic-scope exempt — consistent with the repo principle); (6) no security/data concern — pure presentation subtraction.

**Handoff:** To SM for finish ceremony (single-repo PR — sidequest-server).

---

**Session created:** 2026-05-27  
**Feature branches created:** `feat/63-10-lore-surface-world-only` (server + content)  
**Status:** Setup complete. Awaiting Architect design decision before proceeding to RED.
