---
story_id: "62-1"
epic: "62"
workflow: "trivial"
---

# Story 62-1: Audit + rewrite world descriptions across all packs to decouple from pack catchphrase

## Story Details
- **ID:** 62-1
- **Epic:** 62 — Genre vs World Voice — Pack Catchphrases Stay at Pack
- **Workflow:** trivial
- **Type:** chore
- **Points:** 5
- **Scope:** sidequest-content repo only
- **Branch:** feat/62-1-world-voice-decouple

## Context

Genre packs own signature rhetorical moves (e.g., heavy_metal: "Every empire is ending. Every spell costs."). Worlds within a pack must resolve in their own voice. Currently, multiple worlds are templating the pack's "Every X" parallel couplet structure, making distinct worlds feel like the same author. Worse, chosen catchphrase nouns sometimes don't fit the world's furniture (e.g., Evrópí's "Every crown" is wrong for crown-less peoples like Bladtrablo, Aldkin, Jambiendo).

This story separates pack voice from world voice: audit all 10 live packs + genre_workshopping packs, rewrite world descriptions that have flattened into pack rhetorical templates.

## Workflow Tracking

**Workflow:** trivial  
**Phase:** finish  
**Phase Started:** 2026-05-23T20:14:59Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-23 | 2026-05-23T20:04:44Z | 20h 4m |
| implement | 2026-05-23T20:04:44Z | 2026-05-23T20:10:01Z | 5m 17s |
| review | 2026-05-23T20:10:01Z | 2026-05-23T20:14:59Z | 4m 58s |
| finish | 2026-05-23T20:14:59Z | - | - |

## Acceptance Criteria

1. **Audit table produced** (markdown or yaml in the story session): one row per (pack, world) pair across all 10 live packs + genre_workshopping packs. Each row records:
   - (a) the pack-level catchphrase or signature rhetorical move
   - (b) whether world.yaml description templates that scaffold
   - (c) whether the chosen catchphrase noun even fits the world's furniture (e.g., crowns in a world that spans crown-less peoples)
   - Verdict per row: CLEAN / TEMPLATES_PACK / FITS_WRONG

2. **heavy_metal/long_foundry/world.yaml** description rewritten in its own register (accounting / ledger / covenant language is the world's native voice); the parallel "Every account is a little overdue" twin is dropped; pack catchphrase "Every empire is ending" may stay or go but the parallel "Every X" scaffold does not.

3. **heavy_metal/long_foundry/history.yaml** overview no longer duplicates world.yaml description verbatim — overview either inherits the rewritten description or finds its own framing.

4. **heavy_metal/evropi/world.yaml** description rewritten. The "Three crowns, three ways to fall" tagline carries the count of the authoritarian systems — the description does not repeat that work with "Every crown presses on a different bruise." Description acknowledges the world also contains free peoples without crowns (Bladtrablo, Aldkin, Jambiendo).

5. **For every (pack, world) marked TEMPLATES_PACK or FITS_WRONG** in the audit, the world description is rewritten and the audit row is updated to CLEAN. Worlds marked CLEAN at audit time are left untouched.

6. **Pack-level pack.yaml descriptions are NOT modified** in this story — the catchphrases live there and stay there.

7. **All affected packs still load cleanly.** Run the genre-pack loader / validator (sidequest-server pack load test or equivalent CLI) against every touched pack and verify no regressions.

## Implementation Notes

### Testing / Validation
The implementer should run the genre-pack loader after each pack's rewrites:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/genre/ -k load -q
```

### Constraints
- **No Jira:** This project does not use Jira. Never use `--jira` flag on any pf commands.
- **No asset commits:** All YAML edits only — no generated PNG/JPG/WebP commits (ADR-095 / R2 storage).
- **World voice preservation:** Each world's replacement close must sound like THAT world, not a normalized template. Respect each world's identity and tonal fingerprint (memory: feedback_world_axes_dont_normalize).
- **Pack descriptions untouched:** Only touch world.yaml files and history.yaml overview sections (if duplicated).

### Known Offenders
- **heavy_metal/long_foundry** — duplicates pack catchphrase; also has duplicated history.yaml overview.
- **heavy_metal/evropi** — "Every crown" scaffold is factually wrong for the world's furniture.

## SM Assessment

Setup is complete. Story is well-scoped — content-only sweep, no code repos touched, no Jira. AC list is encoded verbatim from epic-62 (7 ACs). Two known offenders identified up-front so the implementer has a starting point; the rest emerges from the audit table they produce. Trivial workflow is correct — this is a chore, the spec IS the AC list, no TDD required.

The only judgment call worth flagging for Dev: deciding per-world whether to retain "Every empire is ending" as a shared echo OR drop it entirely in that world's voice. Both are defensible — guide is the audit verdict (CLEAN/TEMPLATES_PACK/FITS_WRONG) and the world's native register. When in doubt, lean toward dropping the parallel scaffold but keeping the genre tone elsewhere in the description.

Branch ready: `feat/62-1-world-voice-decouple` on the sidequest-content subrepo (from develop). Handoff to Dev (Winchester) for implement phase. Finest kind.

## Audit Table

Verdict legend: **CLEAN** = world resolves in its own voice. **TEMPLATES_PACK** = world description echoes the pack's signature rhetorical scaffold. **FITS_WRONG** = chosen catchphrase noun doesn't apply to the world's furniture.

| Pack | World | Pack signature | Templates? | Noun fits? | Verdict |
|---|---|---|---|---|---|
| caverns_and_claudes | beneath_sunden | "dungeon is the star" / gear-list close | No — closes on rope/count metaphor, world's own voice | n/a | CLEAN |
| elemental_harmony | burning_peace | "Balance is everything" | No — closes on "Mount Kasai has begun to rumble" | n/a | CLEAN |
| elemental_harmony | shattered_accord | "Balance is everything" | No (description visible) | n/a | CLEAN (separate bug: description is truncated mid-word — see Delivery Findings) |
| heavy_metal | evropi | "Every empire is ending. Every spell costs." | **Yes** — "Every empire is ending. Every crown presses on a different bruise." | **No** — Bladtrablo, Aldkin, Jambiendo, Pakook`rook have no crowns | **TEMPLATES_PACK + FITS_WRONG → rewritten** |
| heavy_metal | long_foundry | same | **Yes** — "Every empire is ending. Every account is a little overdue." | Yes (accounting fits the foundry-covenant world) | **TEMPLATES_PACK → rewritten** |
| heavy_metal | long_foundry (history.yaml overview) | same | **Yes** — duplicated world.yaml close verbatim | n/a | **TEMPLATES_PACK → rewritten** |
| mutant_wasteland | flickering_reach | "Mutations are as common as freckles. Technology is either treasure or trap." | No — closes on the scavenger's rule | n/a | CLEAN |
| neon_dystopia | franchise_nations | "The future arrived and it's not evenly distributed" | No — closes on its own corporate-cheer-as-dread couplet (pizza-in-30 / mandatory survey); distinct rhetorical move | n/a | CLEAN |
| pulp_noir | annees_folles | "purely rational to the ritual worked" / "secrets best left buried" | No — Hemingway/Fitzgerald escalating-triplet close, native to 1920s Paris register | n/a | CLEAN |
| road_warrior | the_circuit | "you are what you drive" | No — closes on its own metaphor ("city collects them like a drain collects rain") | n/a | CLEAN |
| space_opera | coyote_star | "big stakes across bigger distances" | No — closes on the jump-point chokepoint, world's own voice | n/a | CLEAN |
| spaghetti_western | dust_and_lead | "genre handles soul; worlds handle costume" | No — uses antithesis, but antithesis IS the spaghetti western register; the construction differs and the world finds its own balance | n/a | CLEAN (borderline) |
| spaghetti_western | the_real_mccoy | same | No — closes on firing-pin metaphor; the parallel couplet lives in the tagline, not the description | n/a | CLEAN |
| tea_and_murder | glenross | "body off-stage / puzzle fair / tea on" (triplet) | No — uses balanced semicolon parallel but not the "is always X" template | n/a | CLEAN |
| genre_workshopping/elemental_harmony | burning_peace | (workshopping copy of live world) | No | n/a | CLEAN |
| genre_workshopping/low_fantasy | shattered_reach | "steel matters more than spells" | No — closes on "trust is the scarcest currency" | n/a | CLEAN |
| genre_workshopping/space_opera | aureate_span | "big stakes / bigger distances" | No — closes on "dancing on the edge of a supernova" | n/a | CLEAN |
| genre_workshopping/tea_and_murder | blackthorn_moor | tea_and_murder triplet | No — setup vignette with no pack-scaffold close | n/a | CLEAN |

**Rewrites performed (post-rewrite verdict = CLEAN):**
1. `genre_packs/heavy_metal/worlds/evropi/world.yaml` — replaced "Every empire is ending. Every crown presses on a different bruise." with: *"The crowns count themselves as the continent. The steppes, the islands, and the volcanic dark count differently — and older things, twelve thousand years patient, are beginning to stir again."* Acknowledges crown-less peoples (Aldkin steppe, Jambiendo islands, Bladtrablo volcanic dark); keeps heavy_metal cosmological dread without templating the "Every X" scaffold; tagline ("Three crowns, three ways to fall") carries the crown-count work.
2. `genre_packs/heavy_metal/worlds/long_foundry/world.yaml` — replaced "Every empire is ending. Every account is a little overdue." with: *"The arrangement that keeps the foundries lit and the temples fed is older than any current ledger and is, this year, a little overdue."* Drops the parallel scaffold; retains accounting/ledger register native to the world; threads "overdue" into the world-specific covenant arrangement instead of a templated couplet.
3. `genre_packs/heavy_metal/worlds/long_foundry/history.yaml` — replaced the duplicated overview close with: *"The arrangement has held for two centuries. It is, this season, beginning not to."* Gives the DM-prep overview its own drier register, distinct from the world.yaml's in-fiction description, and ends on a tension hook.

**Out of scope (correctly):**
- `genre_packs/heavy_metal/worlds/long_foundry/magic.yaml` quotes "every empire is ending" as a Cascade-class cosmology reference — clearly framed as a quoted callback, not a templated echo. Left untouched.
- All pack.yaml files. Pack-level catchphrases are the canonical home for these phrases.

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Gap** (non-blocking): `genre_packs/elemental_harmony/worlds/shattered_accord/world.yaml` description ends mid-word: "*...drift in slow, grinding orbits above the ruins of the co*" — the sentence is truncated, not the field. Almost certainly an authoring error from a prior session that got committed unfinished. Affects `genre_packs/elemental_harmony/worlds/shattered_accord/world.yaml` (description field needs completion). *Found by Dev during implementation.* Out of scope for 62-1 but worth filing as a separate content chore.
- No other upstream findings.

### Reviewer (code review)
- **Improvement** (non-blocking): A future polish pass could extend the same world-voice-decoupling principle below the world.yaml level — specifically `genre_packs/heavy_metal/worlds/evropi/lore.yaml` (the `history:` paragraph ends on "Every empire is ending. The world is counting down to which ending happens first.") which is in-scope-adjacent but explicitly outside this story's AC. Affects `genre_packs/heavy_metal/worlds/evropi/lore.yaml` (history paragraph could resolve in its own register if Doctor Avery wants the scrub to go deeper). *Found by Reviewer during code review.*
- Confirms Dev's `shattered_accord` truncation finding — independently verified by reading the file: description field ends mid-word at "the ruins of the co". Worth filing as a separate content chore.
- No other upstream findings from review.

## Impact Summary

**Upstream Effects:** 1 findings (0 Gap, 0 Conflict, 0 Question, 1 Improvement)
**Blocking:** None

- **Improvement:** A future polish pass could extend the same world-voice-decoupling principle below the world.yaml level — specifically `genre_packs/heavy_metal/worlds/evropi/lore.yaml` (the `history:` paragraph ends on "Every empire is ending. The world is counting down to which ending happens first.") which is in-scope-adjacent but explicitly outside this story's AC. Affects `genre_packs/heavy_metal/worlds/evropi/lore.yaml`.

### Downstream Effects

- **`genre_packs/heavy_metal/worlds/evropi`** — 1 finding

## Design Deviations

No deviations from spec at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. All 7 acceptance criteria executed verbatim: audit table produced with verdict-per-(pack, world); two known heavy_metal offenders rewritten in their own registers; long_foundry history.yaml overview de-duplicated and given its own framing; no other worlds required rewriting (15/17 verdicts came back CLEAN); pack.yaml descriptions untouched; loader test passes (142 passed, 19 skipped, 0 failures).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — tests 142 passed/0 failed/19 skipped, YAML valid, no smells |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (`workflow.reviewer_subagents.edge_hunter=false`) — content-only diff has no execution paths to enumerate |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — no error-handling code in diff |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — no test changes in diff |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — no comments changed in diff |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — no type definitions in diff |
| 7 | reviewer-security | Yes | clean | none | N/A — no LLM control sequences, role markers, jailbreak patterns, credentials, or PII in new prose; ADR-047 prompt-injection sanitizer would not flag any of the rewrites |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — content polish has no abstraction surface to simplify |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — no language rules apply (pure YAML prose) |

**All received:** Yes (2 enabled subagents returned, 7 pre-disabled and marked Skipped)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

### Rule Compliance

The applicable rules for a content YAML diff are SOUL.md/CLAUDE.md content rules, not the language checklists (no Python/TypeScript/Rust touched). Enumerating each applicable rule against every change:

- **SOUL #3 Genre Truth (consequences follow pack tone)** — Heavy metal pack tone is decay/doom/cost-of-magic. All three rewrites preserve this register: evropi's "older things, twelve thousand years patient, are beginning to stir again" lands the cosmological-dread beat; long_foundry's "is older than any current ledger and is, this year, a little overdue" + "this season, beginning not to" land the slow-failure beat. **Compliant in all 3 files.**
- **SOUL #4 Crunch in Genre, Flavor in World (genre = rulebook, world = setting)** — This story is literally the structural enforcement of #4. Pack catchphrase = genre. World descriptions = setting. The rewrites push the boundary in the correct direction. **Compliant in all 3 files.**
- **SOUL #8 Diamonds and Coal (detail signals importance)** — Evrópí description was already long (heavy detail load) because the world genuinely has 7+ peoples + a buried empire. Rewrite does not balloon detail; it replaces a templated 2-sentence close with a 3-sentence close that genuinely adds (the "count differently" acknowledgement of crown-less peoples and the "older things stirring" hook). Long_foundry rewrites are tighter than the originals. **Compliant.**
- **CLAUDE.md "no half-wired features"** — N/A; this is content polish on already-wired packs, not a feature addition.
- **CLAUDE.md "no silent fallbacks"** — N/A; no code paths touched.
- **CLAUDE.md content "world identity preservation" (memory `feedback_world_axes_dont_normalize`)** — Each rewrite is in its specific world's voice: evropi's gets count-anaphora keyed to its three-peoples-categories logic; long_foundry's stays in ledger/covenant register; history.yaml gets dry DM-prep register distinct from the in-fiction world.yaml. **Compliant — no normalization, three distinct voices.**
- **AC scope discipline (pack.yaml untouched)** — `git diff develop...HEAD` confirms only world.yaml + history.yaml files changed. No pack.yaml in the diff. **Compliant.**

### Observations

- **[VERIFIED] AC-1 audit table complete** — session file's `## Audit Table` section has 17 rows covering 13 live worlds + 4 workshopping worlds, with each row carrying the pack signature, templates-judgment, fits-judgment, and a CLEAN/TEMPLATES_PACK/FITS_WRONG verdict per spec. The 2 flagged rows + 1 secondary history.yaml row are marked as rewritten. Evidence: session file lines 88–104.
- **[VERIFIED] AC-2/AC-4 catchphrase scaffold dropped from world.yaml** — `grep -c "Every empire is ending\\|Every spell costs" genre_packs/*/worlds/*/world.yaml` returns zero matches. Evidence: no world.yaml retains the pack scaffold.
- **[VERIFIED] AC-4 crown-less peoples acknowledged in Evrópí** — Lines 18–20 of `genre_packs/heavy_metal/worlds/evropi/world.yaml`: "The steppes, the islands, and the volcanic dark count differently" maps cleanly to Aldkin (steppes — line 12), Jambiendo (islands — line 13), Bladtrablo (volcanic dark — line 14–15). Acknowledgement is concrete and traceable, not hand-wavy.
- **[VERIFIED] AC-3 history.yaml de-duplicated** — Old history.yaml overview ended on "Every empire is ending. Every account is a little overdue. The city is still working, for now, and still magnificent" — verbatim match to world.yaml close. New history.yaml overview ends on "The arrangement has held for two centuries. It is, this season, beginning not to" — a distinct DM-prep register that no longer duplicates world.yaml's close ("The arrangement that keeps the foundries lit and the temples fed is older than any current ledger and is, this year, a little overdue. The city is still working, for now, and still magnificent."). Evidence: history.yaml:8–17 vs world.yaml:4–13.
- **[VERIFIED] AC-6 pack.yaml untouched** — `git diff develop...HEAD --stat` lists exactly 3 files, none of them pack.yaml. Heavy metal's "Every empire is ending. Every spell costs." catchphrase remains at `genre_packs/heavy_metal/pack.yaml:8` unchanged.
- **[VERIFIED] AC-7 loaders pass** — `cd sidequest-server && uv run pytest tests/genre/ -k load -q` reports 142 passed / 0 failed / 19 skipped (skips pre-existing). [VERIFIED-preflight]
- **[VERIFIED] Borderline audit calls defensible** — Spot-checked Dev's three trickiest CLEAN verdicts (spaghetti_western/dust_and_lead, tea_and_murder/glenross, neon_dystopia/franchise_nations). Each world uses a parallel-sentence close, but the construction differs from the pack's specific scaffold in every case: dust_and_lead uses "It has X / It has Y" subject-predicate antithesis vs pack's "genre... ; worlds..." semicolon balance; glenross uses balanced semicolon parallel with future-tense promise vs pack's "is always X" triplet; franchise_nations uses corporate-cheer-as-dread couplet (pizza/survey) vs pack's "future arrived..." aphorism. Dev's borderline calls hold up.
- **[LOW] Minor cross-rewrite framing tension (non-blocking)** — world.yaml says the arrangement "is older than any current ledger"; history.yaml says "The arrangement has held for two centuries." These are reconcilable ("current ledger" = ledger currently in use, oldest of which date to roughly when the Astran Arrival formalized the arrangement per existing lore.yaml history), but a future reader could read the two framings as slightly inconsistent. Not worth blocking — both lines work in their respective contexts and the existing lore.yaml supports both.
- **[SEC] No prompt-injection surface introduced** — Security subagent confirms no LLM control sequences, role markers, or jailbreak patterns in any of the 3 new prose blocks. Genre pack prose feeds narrator context at runtime per ADR-047; the sanitizer would not flag these strings.
- **[VERIFIED] Out-of-scope decisions defensible** — Dev correctly left `genre_packs/heavy_metal/worlds/long_foundry/magic.yaml` untouched, where "every empire is ending" appears as a *quoted callback* in narrator-tone guidance ("the genre cosmology's 'every empire is ending' rendered as the specific empire ending in this campaign"). That is a meta-reference to the genre, not a templated echo. Similarly, `evropi/lore.yaml` contains the phrase inside a longer history paragraph — out of scope per AC-1's "world.yaml description" wording.

Tag dispatch (mandatory):
[EDGE] — N/A: content-only diff has no execution paths.
[SILENT] — N/A: no error-handling in diff.
[TEST] — N/A: no tests in diff; loader passes via preflight.
[DOC] — N/A: no comments changed (DM-prep YAML comments unchanged).
[TYPE] — N/A: no type definitions in diff.
[SEC] — clean per reviewer-security; no prompt-injection vectors introduced.
[SIMPLE] — N/A: content polish is the unit of work, not an abstraction.
[RULE] — Manual rule check above (SOUL #3, #4, #8, world identity preservation, AC scope) — all compliant.

### Devil's Advocate

A skeptical read of this work would attack on three fronts.

**First, the audit verdicts.** Dev marked 15 of 17 worlds CLEAN, which is a lot of "trust me, this one is fine." A devil's advocate would point out that several CLEAN worlds use parallel-sentence closes that, charitably, *could* be reading the room and unconsciously echoing the genre's preferred rhythm. Glenross's "The village's recurring cast you will come to love; the mystery's victims will arrive on the morning train." mirrors the cosy mystery pack's balanced-parallel triplet just enough that one could argue it's still "in the pack's voice." Same with dust_and_lead's "It has room for all of them. It has patience for none." However, this critique cuts the wrong way: the pack catchphrases ARE the genre's preferred rhythm, and a world is allowed to use the genre's preferred rhythm provided it doesn't copy the specific construction. The 7-AC spec calls out TEMPLATES_PACK as a verdict — meaning the world repeats the pack's scaffold — not "uses a parallel sentence anywhere." Dev's verdicts respect this distinction.

**Second, the rewrites themselves.** A hostile reader might say Evrópí's new close — "The crowns count themselves as the continent. The steppes, the islands, and the volcanic dark count differently — and older things, twelve thousand years patient, are beginning to stir again." — is *also* a parallel-anaphora close, just with "count" instead of "Every." Three sentences, two of them tied by a verb-repetition. Isn't that the same flaw? It is not: pack's "Every X / Every Y" is two-sentence anaphora on the SAME quantifier; Evrópí's "count themselves / count differently" is a deliberate semantic contrast (the crowns presume centrality, the crown-less peoples reject it) keyed to the world's specific political geometry. The repetition serves the world's argument; it does not template the pack's rhetorical shape. Different rhetorical move at the structural level.

**Third, scope.** The catchphrase also appears in `heavy_metal/worlds/evropi/lore.yaml` (the `history:` paragraph) and `heavy_metal/worlds/long_foundry/magic.yaml` (as a quoted cosmology callback). If the principle is "world voices shouldn't template the pack scaffold," shouldn't those echoes also have been scrubbed? They should not, for two reasons: (1) the AC explicitly scopes to "world.yaml description" + the called-out history.yaml duplicate — not the entire heavy_metal corpus; (2) the lore.yaml use is a narrative beat inside a longer paragraph, not a templated description close, and the magic.yaml use is an explicit meta-reference to the genre catchphrase. Both are appropriate inheritances of pack-level voice into lower-level files. If Doctor Avery wants those scrubbed in a future polish pass, that's a follow-up — but story 62-1 stops at world-level descriptions, and stopping there is correct per the spec.

A determined devil would have to argue against the spec itself, not the implementation. The implementation faithfully executes a well-defined chore. No critical or high findings emerge from adversarial reading.

## Deviation Audit

### Reviewer (audit)
- **Dev declared "No deviations from spec"** → ✓ ACCEPTED by Reviewer. Verified against AC list: all 7 ACs executed verbatim, no shortcuts, no scope creep, no scope reduction. The Audit Table is comprehensive (17 rows); the rewrites address every flagged row; pack.yaml is untouched; loaders pass. The only judgment calls Dev made (drop "Every empire is ending" entirely from both worlds rather than retain it as a shared echo) were explicitly permitted by AC-2 ("may stay or go but the parallel 'Every X' scaffold does not"). Sound implementation.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** YAML description fields → genre pack loader → narrator prompt context (per ADR-003 / ADR-004 lazy genre binding). All three rewrites stay within existing prose field semantics; no schema, no field additions/removals; loader test confirms ingestion succeeds.

**Pattern observed:** Genre-vs-world voice separation enforced at content level. Pack catchphrase remains at `genre_packs/heavy_metal/pack.yaml:8`; world descriptions resolve in their own registers at `genre_packs/heavy_metal/worlds/evropi/world.yaml:4-20` (count-anaphora keyed to crown/crown-less geometry) and `genre_packs/heavy_metal/worlds/long_foundry/world.yaml:4-13` (covenant/ledger native register). History.yaml at `genre_packs/heavy_metal/worlds/long_foundry/history.yaml:8-17` gets its own drier DM-prep voice distinct from world.yaml.

**Error handling:** N/A — content-only diff, no execution paths.

**Subagent results:** 2/2 enabled subagents clean. [SEC] reviewer-security returned clean — no LLM control sequences, role markers, jailbreak patterns, credentials, or PII in any of the 3 new prose blocks; ADR-047 prompt-injection sanitizer would not flag any of the rewrites. Preflight GREEN (142/0/19). 7/9 pre-disabled for content-only review per project settings.

**Critical/High findings:** None.

**Low/Informational findings:** 1 — minor cross-rewrite framing tension between world.yaml's "older than any current ledger" and history.yaml's "two centuries" framing (reconcilable, non-blocking).

**Handoff:** To SM (Hawkeye) for finish-story.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/world.yaml` — description close rewritten to acknowledge crown-less peoples and drop the "Every X" couplet scaffold.
- `sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/world.yaml` — description close rewritten in the world's native ledger/covenant register, scaffold dropped.
- `sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/history.yaml` — overview close rewritten to give the DM-prep prose its own drier voice, distinct from the in-fiction description.

**Tests:** `cd sidequest-server && uv run pytest tests/genre/ -k load -q` → **142 passed, 19 skipped, 0 failures.** All affected packs load cleanly post-edit.

**Branch:** `feat/62-1-world-voice-decouple` (sidequest-content subrepo, on develop) — to be pushed after commit.

**Audit summary:** 17 (pack, world) pairs surveyed. 15 verdicts CLEAN at audit time, 2 flagged (both heavy_metal). Post-rewrite, all 17 verdicts are CLEAN. See Audit Table for the full row-by-row breakdown.

**Handoff:** To review phase (Reviewer / Colonel Potter).