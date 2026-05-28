---
parent: context-epic-63.md
workflow: tdd
---

# Story 63-10: Lore surface renders WORLD lore only — stop rendering genre-level lore (Keepers/Maw) + banner intro; resolve genre/world contradiction

## Business Context

The `/reference/lore/<pack>/<world>` pages are SideQuest's in-world wiki for lore immersion. Each world has its own identity, voice, and cosmology — they should render ONLY the world-tier lore (below the fold of the page, in the contents rail sections).

However, `assemble_lore_page()` in `reference_renderer.py` concatenates pack-tier flavor files (cultures.yaml, lore.yaml, history.yaml, factions.yaml) **on top of** world-tier renders, with a "(genre)" label suffix. This works fine for most packs, but creates a **direct contradiction** for `beneath_sunden`:

- **World lore** (beneath_sunden/lore.yaml): Explicitly rejects the Keepers/Maw/Seven-Sins cosmology. Beneath Sünden is a standalone, self-contained tragedy — *one dwarfhold that dug too deep*. No Keepers. No intelligences. Just what came up from the deep, learning the shape of the shaft over two lifetimes.

- **Pack lore** (caverns_and_claudes/lore.yaml): Describes the Keeper cosmology as universal — "The Keepers are the intelligences that dwell within. Whether they built the dungeons or the dungeons built them..." and "Every dungeon has a Maw."

When `/reference/lore/caverns_and_claudes/beneath_sunden` renders, it shows **both** — the world's private history first, then the genre's Keeper cosmology tagged "(genre)" — contradicting the world's own voice and violating the immersion contract.

## Technical Guardrails

**Key files (server-only story):**
- `sidequest-server/sidequest/server/reference_renderer.py` lines 1119–1134 — the `assemble_lore_page()` merge logic that concatenates pack-flavor onto world renders.
- `sidequest-server/sidequest/server/reference_renderer.py` constants `LORE_WORLD_FILES` (line ~465) and `LORE_PACK_FLAVOR_FILES` (line ~465) — the file lists that control what renders.

**Integration points:** The merge happens at the `assemble_lore_page()` function level, which is called from `_assemble_lore_for_world()` in the reference endpoint handler (`views.py`). Verify the change propagates end-to-end by checking the live endpoint.

**Do NOT touch:** the chrome/CSS (63-4/63-7 territory), the anchor/slug system, `EXCLUDED_FILES` policy, or the per-file presenters. This is purely the world-vs-genre file-merge decision.

## OPEN DESIGN QUESTION — ARCHITECT DECISION REQUIRED BEFORE RED

**The Scope of Flavor Exclusion**

The story premise is: "render WORLD lore only." But there is a spectrum of choices:

1. **Absolute world-only** (strictest): Exclude ALL pack-tier files from the lore page merge. Only render `LORE_WORLD_FILES` (openings.yaml, lore.yaml, locations.yaml). Pack-tier `cultures.yaml`, `history.yaml`, `factions.yaml`, `lore.yaml` are never concatenated.

2. **World + factions/cultures** (moderate): Keep world-tier files; exclude the cosmology/setting files. Render `openings.yaml`, `lore.yaml`, `locations.yaml` (world), plus `cultures.yaml` and `factions.yaml` (pack). Exclude pack-tier `history.yaml` and `lore.yaml` (these carry Keeper/Maw/cosmology). *Rationale:* A world can have its own cultures and factions alongside the pack backdrop; these are player-accessible flavor without cosmology override.*

3. **World + flavored cultures/factions** (complex): Same as #2, but strip pack-tier cultures/factions that contradict the world (hard to define; requires per-world overrides).

**The breaking case:** `beneath_sunden` is world-only — it rejects the pack's Keeper cosmology entirely. Beneath Sünden has **no** factions or cultures in its own lore.yaml (only history/geography/cosmology). So all three options converge for this world: only the world lore renders, no contradiction.

**Questions for Architect:**
- Is world-only (#1) the right default, or should some packs allow pack-tier flavor (#2)?
- If #2: should the story disable the merge for `beneath_sunden` only, or should we author a `beneath_sunden/lore.yaml` section that **overrides** (rather than concatenates with) the pack's cultures/factions?
- Should the rendered page indicate when content is from the pack tier vs. the world tier, or is the "(genre)" label sufficient?

This story **CANNOT proceed to RED without Architect sign-off** on which choice to implement. The formal ACs do not exist yet — they depend on the design decision.

## Scope Boundaries

**In scope (pending design decision):**
- Modify `assemble_lore_page()` to either:
  - (Option #1) Remove `LORE_PACK_FLAVOR_FILES` from the merge entirely, or
  - (Option #2) Conditionally exclude pack-tier cosmology files (pack lore.yaml, history.yaml) while keeping cultures/factions.
- Update the file lists (`LORE_WORLD_FILES`, `LORE_PACK_FLAVOR_FILES`) or the merge logic to implement the chosen design.
- Write tests that verify the chosen design (e.g., if #1: `test_assemble_lore_page_world_only_beneath_sunden` asserts pack lore is not present; if #2: asserts cultures render but cosmology does not).
- OTEL telemetry (if any merge decisions are made, confirm they fire reference spans if applicable).

**Out of scope:**
- Chrome, CSS, fonts, palettes, hero, contents rail (63-4/63-7).
- Anchor/slug system, reference_url wiring (63-1 through 63-6, 63-8).
- Empty section suppression (63-11), validator crash-hardening (63-13).
- Per-world lore.yaml authoring in content — that is content's job post-design decision.

## Assumptions

- `assemble_lore_page()` is the **sole** place where pack-tier lore gets merged into world pages. (Verify: grep for LORE_PACK_FLAVOR_FILES usage.)
- The "(genre)" label suffix on pack-tier sections is sufficient to indicate pack-tier content, or a design change is needed (Architect decision).
- beneath_sünden's world lore.yaml is authoritative and represents the intended world voice (confirmed by reading the file).

## Verification Checklist

Before marking READY FOR REVIEW:
- [ ] Architect has ratified a design decision (world-only, world+factions, or world+flavored).
- [ ] Tests exist for the chosen design and pass (RED→GREEN).
- [ ] Live `/reference/lore/caverns_and_claudes/beneath_sunden` endpoint no longer renders Keepers/Maw cosmology.
- [ ] No regressions in other pack/world combinations (e.g., `space_opera/orbital_station` still renders cultures if design is #2).
- [ ] No silent fallbacks; if a world lore.yaml is missing a section that was previously sourced from pack-tier, that is a **Design Deviation** to log (not a bug).
