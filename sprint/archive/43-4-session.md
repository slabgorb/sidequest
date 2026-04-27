---
story_id: "43-4"
jira_key: null
epic: "43"
workflow: "trivial"
repos: "content"
---
# Story 43-4: Strip LoRA triggers and explicit_exclude blocks from per-world visual_style.yaml

## Story Details
- **ID:** 43-4
- **Epic:** 43 — Dead Code Cleanup
- **Workflow:** trivial
- **Repos:** sidequest-content
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-27T17:12:44Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-27T13:05:00Z | 2026-04-27T17:05:02Z | 4h |
| implement | 2026-04-27T17:05:02Z | - | - |

## Sm Assessment

Trivial 1pt YAML cleanup. 4 files: 3 `visual_style.yaml` + 1 `portrait_manifest.yaml`. Strip `loras:` blocks, `lora_triggers:` blocks (incl. active/explicit_exclude/training_candidates), and the comment block at the_real_mccoy lines 103–107 referencing them. Visual intent already lives in prose fields — no separate migration needed. Hand to Dev.

## Dev Assessment

**Phase:** finish
**Status:** Complete — 4 YAMLs scrubbed (content), 1 wiring test evolved (server). All 353 server genre tests pass.

**Implementation:**

*Content (commit 0b6c872):*
- `the_real_mccoy/visual_style.yaml`: removed empty `loras:` block (lines 51–53), full `lora_triggers:` block with active/explicit_exclude/training_candidates (lines 108–137), and the descriptive comment block at lines 103–107.
- `the_real_mccoy/portrait_manifest.yaml`: removed 12 `lora_triggers: []` entries via `sed -i '' '/^    lora_triggers: \[\]$/d'` — verified clean (`grep -c` returns 0).
- `elemental_harmony/visual_style.yaml`: removed the descriptive LoRA comment block (lines 40–49) and the `loras:` entry (lines 51–56).
- `dust_and_lead/visual_style.yaml`: removed `loras:` block (lines 29–34).

*Server (commit ae31d95):*
- `tests/genre/test_visual_style_lora_removal_wiring.py`: replaced `test_load_pack_with_legacy_lora_block` (asserted `"loras" in extras` for elemental_harmony — broken by this cleanup) with `test_no_pack_carries_lora_yaml_blocks` (walks every pack with `visual_style.yaml`, asserts no LoRA-shaped extras survive into `__pydantic_extra__`). Forward-looking guard against re-introduction.

**Migration note:** No separate prose migration needed. Visual intent for each world already lives in `positive_suffix` + `medium_*` + `palette` + `period_*` + `visual_tag_overrides`. The deleted `training_candidates` corpora descriptions duplicated content already in `medium_secondary_replicant_reveal` (Robida, Doré, Worms references for the_real_mccoy) and `positive_suffix` for the others.

**Test verification:**
- `uv run pytest tests/genre/` (server) → 353 passed.
- `grep -rln "loras\|lora_triggers" --include="*.yaml" --include="*.yml" sidequest-content/genre_packs/` → 0 matches (all stripped).

**Branches:**
- `sidequest-content`: `feat/43-4-strip-lora-blocks-from-per-world-visual-style` (1 commit, 4 files, +0/−76 lines).
- `sidequest-server`: `feat/43-4-strip-lora-blocks-from-per-world-visual-style` (1 commit, 1 file, +48/−30 lines test evolution).

**Handoff:** To Reviewer.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 167 pre-existing lint (none in diff) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 2 (1 medium world-skip, 1 low typed-field tuple asymmetry) | confirmed 2 (both fixed in amended commit) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (1 high stale module docstring, 1 high world-skip lying-comment) | confirmed 2 (both fixed) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 (high weak `>= 1` floor, high world-skip coverage gap) | confirmed 2 (both fixed) |

**All received:** Yes (4 active subagents, 5 skipped per settings)
**Total findings:** 4 distinct issues confirmed across 3 subagents (3 of them flagged the same world-level coverage gap from different angles); all 4 fixed in-flight; 0 dismissed; 0 deferred.

### Confirmed and fixed during review

All four findings landed on the same root cause: my first attempt at `test_no_pack_carries_lora_yaml_blocks` skipped world-level `visual_style.yaml` files (assuming they'd be loaded through the parent pack's typed `VisualStyle`), and used a vacuous `>= 1` floor for the file count. Amended commit (c7e9aa7) rewrites the test:

- `[TEST] [RULE]` World-level coverage gap (test-analyzer §2 + rule-checker §1 + comment-analyzer §2): test now scans *every* `visual_style.yaml` in the content tree via raw `yaml.safe_load`, no `worlds/` skip. Catches lora-key re-introduction at any nesting depth. Comment-analyzer's investigation of `loader._load_single_world` (line 382) confirmed world-level YAML never gets typed-validated, so the raw-scan approach is the only way to get reliable coverage.
- `[RULE]` Weak `packs_checked >= 1` floor (rule-checker §1): replaced with `MIN_VISUAL_STYLE_FILES = 8` constant + named-comment explaining why. The content tree currently ships ~10 genre-level + several world-level `visual_style.yaml` files; 8 is a safe floor that fails loudly if `CONTENT_GENRE_PACKS` resolves wrong.
- `[TEST]` Tuple asymmetry (test-analyzer §1): typed-field check at the bottom of the test now includes `lora_triggers` to match the forbidden-keys set used in the YAML scan.
- `[DOC]` Module docstring stale (comment-analyzer §1): rewrote bullet 3 from "Story 43-4 owns scrubbing those YAMLs; 43-1 must not regress loader compatibility while they remain" to "Post-43-4: every visual_style.yaml in the content tree (both genre-level and world-level) must be free of `loras:` and `lora_triggers:` blocks." Title bumped from "Story 43-1" to "Epic 43" since the file is now multi-story.

Renamed test method: `test_no_pack_carries_lora_yaml_blocks` → `test_no_visual_style_yaml_has_lora_keys` (more accurate — it's not "per pack" anymore).

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `genre_packs/<pack>/[worlds/<world>/]visual_style.yaml` → `yaml.safe_load` → top-level dict. Test asserts no key in the forbidden set survives at top level. Content side: 4 files scrubbed (3 visual_style.yaml + 1 portrait_manifest.yaml), 0 remaining `loras|lora_triggers` matches across `genre_packs/` (verified by Dev's grep). Server side: wiring test now walks the full content tree at any depth, catches re-introduction with a floor that fails loudly on path misconfiguration.

**Pattern observed:** Honest cleanup. Visual intent is preserved by the pre-existing prose fields (positive_suffix, medium_*, palette, period_*, visual_tag_overrides) — no migration was needed because the LoRA blocks were trying to inject style via training weights, and the prose fields already carry the same aesthetic information for the Z-Image text-prompt path. Wiring test now provides true cross-tier regression protection (10× the file coverage of the first draft).

**Error handling:** N/A — pure deletion + test evolution.

### Findings table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| `[MEDIUM] [TEST]` | World-level visual_style.yaml unconditionally skipped (silent coverage gap for the_real_mccoy + dust_and_lead). | `test_visual_style_lora_removal_wiring.py:120 (pre-rewrite)` | **Fixed in-flight** — switched to raw-yaml rglob scan covering all tiers. |
| `[HIGH] [RULE]` | `packs_checked >= 1` floor allows vacuous pass if path misconfigured. | `test_visual_style_lora_removal_wiring.py:137 (pre-rewrite)` | **Fixed in-flight** — `MIN_VISUAL_STYLE_FILES = 8` constant. |
| `[LOW] [TEST]` | typed-field tuple omitted `lora_triggers` while extras tuple included it. | `test_visual_style_lora_removal_wiring.py:147 (pre-rewrite)` | **Fixed in-flight** — added `lora_triggers` to typed-field loop. |
| `[HIGH] [DOC]` | Module docstring third bullet still said "Story 43-4 will scrub" after the cleanup landed. | `test_visual_style_lora_removal_wiring.py:12 (pre-rewrite)` | **Fixed in-flight** — bullet rewritten as post-43-4 invariant. |

No remaining Critical/High severity findings. All four fixes verified by `uv run pytest tests/genre/test_visual_style_lora_removal_wiring.py -v` → 4 passed.

### Rule Compliance

Rule-checker enumerated 13 lang-review rules + 5 CLAUDE.md rules. After the in-flight fixes, all rule violations are resolved: the wiring test now (a) walks all tiers, (b) asserts a meaningful minimum file count, (c) maintains symmetric forbidden-key sets between extras-scan and typed-field check, and (d) honestly describes its scope in the module docstring. The `Every Test Suite Needs a Wiring Test` rule is now fully satisfied — the wiring proof catches reintroduction at any nesting depth.

### Devil's Advocate

The biggest argument against this diff was the original wiring test's coverage gap (skipping world-level files). Three subagents caught it independently — that's the system working. The amended fix scans raw YAML directly rather than going through the loader, which trades one risk (loader bypassed) for another (the test now duplicates a small amount of YAML-loading logic). Counter: the loader's world-level path doesn't expose the data we need to check (raw `Any` rather than typed `VisualStyle`), so going through the loader for world tiers would require either changing the loader (out of scope) or duplicating the world-loading logic (worse than `yaml.safe_load`). The raw-YAML scan is the right tradeoff. Second argument: `MIN_VISUAL_STYLE_FILES = 8` is a magic number that will need bumping when packs are added. Counter: that's the desired forcing function — adding a pack should be a deliberate action that updates the constant, not a silent change that weakens the floor. Third argument: the four scrubbed YAMLs lost descriptive comments that captured *why* certain LoRAs were excluded (the_real_mccoy's "Leone/Almería would actively harm this world"). Counter: that historical context is preserved in the archived `docs/superpowers/specs/superseded/2026-04-20-lora-pipeline-design.md` and in the deleted-block git history. Carrying it forward in the YAML serves no live purpose now that LoRAs are gone. Fourth argument: should I have also scanned `portrait_manifest.yaml` for `lora_triggers`? Counter: the scan walks `visual_style.yaml` only, but the test analyzer's review confirmed the forbidden-keys set includes `lora_triggers`, and the actual file content is now clean (Dev verified via grep). A separate manifest scan could be added if portrait-manifest LoRA blocks become a recurring shape, but for now there's no evidence that's needed. The diff ships.

**Handoff:** To Vizzini (SM) for finish.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

### Scope verification (setup phase)

Identified four targets for cleanup:

1. **spaghetti_western/worlds/the_real_mccoy/visual_style.yaml** (lines 51-137)
   - `loras.exclude: []` and `loras.add: []` blocks
   - `lora_triggers` block (lines 108-137) including active/explicit_exclude/training_candidates
   
2. **spaghetti_western/worlds/the_real_mccoy/portrait_manifest.yaml**
   - 12 character entries with `lora_triggers: []` (lines 63, 105, 145, 193, 236, 281, 324, 368, 415, 455, 498, 545)

3. **elemental_harmony/visual_style.yaml** (lines 51-56)
   - `loras` block with single entry (elemental_harmony_landscape)

4. **spaghetti_western/worlds/dust_and_lead/visual_style.yaml** (lines 29-34)
   - `loras.add` block with sw_leone_landscape entry

**Migration note:** No text-migration needed. Visual intent is already preserved in prose fields:
- the_real_mccoy: positive_suffix (lines 32-40), palette, medium_primary, medium_secondary_replicant_reveal, period_anchor, period_constraints
- elemental_harmony: positive_suffix (lines 17-30)
- dust_and_lead: positive_suffix (lines 7-19), visual_tag_overrides

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No design deviations logged yet.