---
story_id: "74-2"
jira_key: "none"
epic: "74"
workflow: "tdd"
---
# Story 74-2: Repoint flavor consumers to the World tier (reference-chrome, render pipeline, audio backend); fixes reference_renderer 500 risk before genre flavor deletion

## Story Details
- **ID:** 74-2
- **Epic:** 74 (Genre tier = mechanics only)
- **Points:** 5
- **Workflow:** tdd
- **Type:** refactor
- **Stack Parent:** none (not stacked)
- **Repos:** sidequest-server, sidequest-daemon

## Epic Context
**Title:** Genre tier = mechanics only

Genre packs hold MECHANICS ONLY; all flavor (lore, cultures, archetypes, theme, visual_style, audio, weather, tropes) lives in the WORLD, not the genre.

**Rationale (Keith, 2026-05-30):** Worlds diverge too hard for shared genre flavor to be meaningful or even correct — spaghetti_western genre tropes authored for the Mexican border are wrong for 1878 Pittsburgh (the_real_mccoy).

**Blocker Status:** 74-1 (Loader refactor — genre-tier flavor becomes world-tier/optional) is DONE (approved 2026-05-31).

## Story Objective
Repoint the live flavor consumers (reference-chrome/reference_renderer, render pipeline, audio backend) to read flavor from the WORLD tier instead of the GENRE tier, so the remaining mandatory genre-tier flavor files can later be safely deleted (74-3 authors world lore; this story makes consumers world-tier-safe first).

**Named Risk:** reference_renderer 500 error when genre flavor is absent — fix that before deletion.

**Key Facts:**
- This story spans TWO repos: sidequest-server AND sidequest-daemon. The daemon hard-requires its own genre-level positive_suffix independently — a server-only change is a no-op for the render pipeline. Both must be touched.
- Visual style is WORLD-level only now (per 64-12); pack/genre visual_style.yaml is optional across server loader + daemon StyleCatalog + pack_schema.
- Spec + full audit doc: `docs/genre-pack-content-audit.md` (orchestrator repo).

## Acceptance Criteria
**Resolution contract: HARD FAIL LOUD (Keith ruling 2026-06-01). World-authoritative; genre tier NEVER consulted — no fallback, no silent default. Supersedes the original "fallback to genre" wording.** Full detail in `sprint/context/context-story-74-2.md`.

1. reference-chrome / reference_renderer + connect-time theme read `world.theme`; genre theme never consulted (assert via consumer output + genre sentinel absent).
2. render pipeline (daemon) reads `world.visual_style` (`positive_suffix`/StyleCatalog); genre visual_style never consulted.
3. audio backend (`_resolve_audio_urls` + audio engine) reads `world.audio`; genre audio never consulted.
4. World-flavor-absent raises a specific NAMED error per surface (not a 500, not a genre fallback, not a silent default), identifying the missing surface + world.
5. OTEL watcher event on every flavor-resolution decision — both success and loud-fail paths.
6. No regressions (server + daemon suites green); design deviations logged per 6-field format.

## Workflow Tracking
**Workflow:** tdd
**Phase:** green
**Phase Started:** 2026-06-01T06:53:03Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-01T03:58:25Z | 2026-06-01T04:00:25Z | 2m |
| red | 2026-06-01T04:00:25Z | 2026-06-01T06:53:03Z | 2h 52m |
| green | 2026-06-01T06:53:03Z | - | - |

## Sm Assessment

**Setup complete — routing to TEA (Radar) for red phase.**

Story 74-2 repoints the live flavor consumers (reference_renderer/reference-chrome, daemon render pipeline, audio backend) to read flavor from the WORLD tier, fixing the named `reference_renderer` 500 risk before genre-tier flavor can be deleted (74-3 authors world lore afterward). Blocker 74-1 (loader makes genre flavor optional) is DONE and approved.

**Scope discipline for downstream agents:**
- **Two repos are mandatory.** sidequest-server AND sidequest-daemon. The daemon hard-requires its own genre-level `positive_suffix` independently — a server-only change is a no-op for the render pipeline (confirmed pattern from 64-12 / prior genre→world moves). Branches created in both: `feat/74-2-repoint-flavor-world-tier`.
- **Open design question for TEA/Architect (do not skip):** AC2/AC3 specify "fallback to genre." Epic 74's stated intent is to *delete* genre flavor entirely. Confirm against `docs/genre-pack-content-audit.md` whether this fallback is a deliberate transitional safety net (consumers go world-safe now, genre files deleted later) or a contradiction to scrub. RED tests should encode whichever answer the audit doc supports — don't hardcode a fallback the epic means to remove.
- **OTEL is an AC, not optional** (AC5): flavor-resolution decisions must emit watcher events so the GM panel can verify world-tier reads are actually firing (project OTEL principle — catches "winging it").
- Reference: `docs/genre-pack-content-audit.md` is the spec + full audit.

Merge gate clear (no open PRs in any repo). No Jira (personal project).

**SM setup repair (2026-06-01, post-TEA bounce):** TEA correctly bounced two setup gaps. Fixed both:
1. Created `sprint/context/context-story-74-2.md` (sm-setup had embedded context in the session but never produced the standalone file; `pf validate context-story 74-2` now exit 0).
2. Corrected ACs: the original AC2/AC3 "fallback to genre" was sm-setup auto-gen error contradicting Keith's audit Decision D ("NO FLAVOR AT GENRE, PERIOD"). Resolved contract = **HARD FAIL LOUD** (Keith ruling 2026-06-01): world-authoritative, genre never consulted, world-absent raises a specific named error. Baked into both the session ACs above and the context file. Confirmed internally consistent with 74-1's already-approved AC2 (loader loud-fail). Routing back to TEA (Radar) to resume RED.

## TEA Assessment

**Tests Required:** Yes
**Phase:** green — RED verified
**Status:** RED (failing, ready for Dev)

**Effective scope (post-Doctor rescope 2026-06-01):** server-only; reference_renderer theme repoint. Daemon AC2 already shipped (64-12 #95); audio AC3 split to a future story.

**Test Files:**
- `sidequest-server/tests/server/test_reference_theme_world_tier.py` (NEW) — the 74-2 world-tier contract (7 tests).
- `sidequest-server/tests/server/test_reference_theme.py` (UPDATED) — 6 HTML-emission tests repointed to world-tier fixtures; loader-contract tests untouched.

**Tests Written:** 13 failing assertions across the two surfaces, covering 4 effective ACs (lore→world theme, rules→default-world theme, world-absent loud-fail/no-genre-fallback, OTEL span). Verified RED with exact failure reasons (not fixture artifacts):
- lore/rules world-absent → `Failed: DID NOT RAISE MissingThemeFieldError` (current code silently falls back to genre — the exact violation).
- rules default-world → HTML carries `data-archetype="genre-sentinel-archetype"` (proves genre-tier read).
- OTEL → no `sidequest.reference.theme_resolved` span exists yet.
Loader-contract tests + `test_reference_theme_module_importable` stay GREEN (tier-agnostic). No phantom DB/collection errors.

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #1 No silent fallbacks | `test_lore_page_world_theme_absent_fails_loud_no_genre_fallback`, `test_rules_page_no_resolvable_world_theme_fails_loud` | failing (RED) |
| #6 Test quality (meaningful assertions) | self-check — all assertions check specific values/sentinels; 0 vacuous | pass |
| OTEL principle (CLAUDE.md) | `test_lore_theme_resolution_emits_world_span`, `test_rules_theme_resolution_emits_world_span` | failing (RED) |
| Wiring test (CLAUDE.md) | `test_rules_page_renders_when_genre_theme_absent` drives the real `assemble_rules_page` production path | failing (RED) |

**Rules checked:** 2 of the directly-test-applicable lang-review rules (#1, #6) plus OTEL + wiring principles. Remaining python.md rules (#2-#5, #7-#13) govern Dev's implementation and are the lang-gate/Reviewer's surface.
**Self-check:** 0 vacuous tests.

**Implementation contract for Dev (Major Winchester):**
1. `assemble_lore_page(pack, world, pack_dir, world_dir)` → read theme from `world_dir/theme.yaml` (via `load_reference_theme(world_dir)`); never `pack_dir`. World theme absent → `MissingThemeFieldError` naming the world (no genre fallback).
2. `assemble_rules_page(pack, pack_dir)` → resolve the pack's DEFAULT world (selection rule undefined for >1 world — see finding; single-world is unambiguous), read that world's theme; never `pack_dir`. Genre `theme.yaml` absent must NOT 500. Default world's theme absent → loud `MissingThemeFieldError`.
3. Emit a `sidequest.reference.theme_resolved` span (add to `telemetry/spans/reference.py`) with `reference.world` + source, on every resolution.
4. `load_reference_theme` itself is tier-agnostic — do NOT change it; change only WHICH dir the assemblers pass.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for GREEN.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (blocking): AC2/AC3 specify "reads flavor from world tier with fallback to genre," which contradicts the authoritative ruling in `docs/genre-pack-content-audit.md` Decision D (Keith, 2026-05-29): "NO FLAVOR AT GENRE, PERIOD." The per-consumer change table in that doc requires all three 74-2 surfaces (theme→reference-chrome, visual_style→render pipeline, audio→audio backend) to "must read world" — no genre fallback. Affects the ACs in the session + the to-be-created `sprint/context/context-story-74-2.md`. **Resolved design contract (Keith ruling 2026-06-01): HARD FAIL LOUD** — consumer reads world flavor when present (genre tier never consulted); when world flavor is absent, raise a specific named error (NOT a 500, NOT a genre fallback, NOT a silent default), per the project "No Silent Fallbacks" principle. OTEL span on every flavor-resolution decision (AC5). *Found by TEA during test design.*
- **Gap** (blocking): `sprint/context/context-story-74-2.md` was never created by sm-setup (context was embedded in the session instead); `pf validate context-story 74-2` fails exit 2. TEA protocol forbids auto-creating context. Affects SM setup — needs `pf-context` creation with the corrected ACs above before RED can proceed. *Found by TEA during test design.* **[RESOLVED by SM: context file created, ACs corrected.]**
- **Conflict** (blocking): **Story scope is substantially stale — measured against the actual codebase (TEA scout pass, 2026-06-01).** Three findings: (1) **AC2 (daemon render pipeline → world visual_style) is ALREADY DONE** by epic 64-12 / PR #95 (`sidequest-daemon` commit `8d8d6c0`): `StyleCatalog.load` already requires world `visual_style.yaml` (raises `StyleMissError` if absent — hard-fail-loud), skips genre when world present, and emits `world_style_applied`/`genre_style_applied` watcher booleans. The **daemon repo needs zero changes** — the "two repos mandatory" premise (from the audit doc + SM setup) is falsified. (2) **AC1 (reference_renderer theme) is the genuine, clean work**: `reference_renderer.py:1073` + `:1141` call `load_reference_theme(pack_dir)` reading genre `pack_dir/theme.yaml`; this is the named `reference_renderer` 500 risk. Repoint to `world_dir`, `MissingThemeFieldError` loud-fail. (3) **AC3 (audio → world audio) is genuine but larger than scoped**: `audio_mixin.py:76` reads `genre_pack.audio`; `World.audio` (raw dict) exists but is consumed *nowhere* in the server (grep = 0 consumers) — the audio_mixin comment "world audio override consumed elsewhere" is stale/wrong. Wiring world audio into the LibraryBackend is net-new work with a dict→AudioConfig type gap. Affects story repo scope + ACs. **Needs SM/Doctor rescope ruling before RED.** *Found by TEA during test design.* **[RESOLVED by Doctor 2026-06-01: tighten to reference_renderer only; daemon dropped; audio → separate story.]**
- **Gap** (non-blocking): The rules-page default-world SELECTION rule is undefined for packs with >1 world. The contract is "rules page resolves the pack's default world and reads its theme," but *which* world (a `pack.yaml`/`world.yaml` `default_world` field? first sorted? only-world?) is a Dev/Architect decision. RED tests use single-world packs so the contract is unambiguous. Affects `sidequest/server/reference_renderer.py` (`assemble_rules_page` default-world resolution). *Found by TEA during test design.*
- **Improvement** (non-blocking): Stale comment in `sidequest/server/websocket_handlers/audio_mixin.py:78-82` claims world-tier audio "is a free-form file consumed elsewhere" — but grep finds zero `world.audio` consumers in the server; it is consumed nowhere. Fix the comment when the split-out audio story lands. *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Story rescoped to server-only — daemon AC2 dropped (already shipped)**
  - Spec source: session AC2 + context-story-74-2.md ("render pipeline (daemon) reads world visual_style")
  - Spec text: "render pipeline (daemon) reads `world.visual_style`; genre never consulted"
  - Implementation: no daemon tests written; AC2 removed from 74-2 RED scope
  - Rationale: world-tier visual_style + hard-fail-loud (`StyleMissError`) + OTEL booleans already shipped in sidequest-daemon `8d8d6c0` (epic 64-12 / PR #95). No failing test is possible for already-correct behavior. Confirmed by direct code read + git log.
  - Severity: major (scope)
  - Forward impact: daemon branch `feat/74-2-repoint-flavor-world-tier` will carry no commits; sprint YAML `repos:` still lists `sidequest-daemon` — SM should narrow to `sidequest-server` at finish. Doctor ruling 2026-06-01 (tighten to reference_renderer).
- **Audio (AC3) split out to a separate story**
  - Spec source: session AC3
  - Spec text: "audio backend (`_resolve_audio_urls` + audio engine) reads `world.audio`; genre never consulted"
  - Implementation: no audio tests written; AC3 removed from 74-2
  - Rationale: `World.audio` is consumed nowhere in the server (grep = 0 consumers); wiring it into LibraryBackend is net-new work with a dict→AudioConfig type gap, not the story title's named `reference_renderer` 500 risk. Doctor ruled tighten-to-reference_renderer (2026-06-01).
  - Severity: major (scope)
  - Forward impact: a new story must be filed for world-audio wiring (SM). The named risk (reference_renderer 500) is fully covered by the remaining scope.
- **Rules page theme resolved via a DEFAULT WORLD (not neutral default, not genre)**
  - Spec source: context-story-74-2.md AC + Keith ruling 2026-06-01
  - Spec text: rules page (`/rules/{pack}`, no world) must read world-tier theme without 500
  - Implementation: RED tests assert `assemble_rules_page(pack, pack_dir)` resolves the pack's default world and reads its theme; genre never read
  - Rationale: Doctor chose "rules page reads a default world" over neutral-default / genre-exempt (2026-06-01)
  - Severity: minor (design choice, in scope)
  - Forward impact: the default-world SELECTION rule for packs with >1 world is undefined — see Delivery Finding. RED fixtures use single-world packs.
- **Existing `test_reference_theme.py` HTML-emission tests repointed to world tier**
  - Spec source: pre-existing tests (lines ~200-278) pinned genre-tier theme reads
  - Spec text: `assemble_rules_page`/`assemble_lore_page` rendered the genre `pack_dir/theme.yaml`
  - Implementation: their fixtures now place theme at the world tier (`_write_world_pack`); 6 now fail RED, 1 (loud-when-missing) stays green as a tier-agnostic invariant
  - Rationale: those tests encoded the pre-74-2 behavior the story changes; left as-is they'd be mystery failures for Dev
  - Severity: minor
  - Forward impact: none — Dev makes them green by repointing the assemblers. Loader-contract tests (load_reference_theme direct) untouched.