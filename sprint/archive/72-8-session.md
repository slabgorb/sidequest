---
story_id: "72-8"
jira_key: null
epic: "72"
workflow: "trivial"
---
# Story 72-8: Stamp last_seen_turn/location on encounter presence, not just prose mention

## Story Details
- **ID:** 72-8
- **Jira Key:** null
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-01T06:54:07Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-31T23:30:00Z | 2026-06-01T03:44:07Z | 4h 14m |
| implement | 2026-06-01T03:44:07Z | 2026-06-01T06:43:29Z | 2h 59m |
| review | 2026-06-01T06:43:29Z | 2026-06-01T06:54:07Z | 10m 38s |
| finish | 2026-06-01T06:54:07Z | - | - |

## Sm Assessment

**Story:** 72-8 — Stamp `last_seen_turn` / `last_seen_location` on the encounter-**presence** seam, not just on the prose-mention path. Epic 72 (NPC Identity Hardening), 2pt bug, trivial workflow, sidequest-server only.

**Why it matters:** Today `last_seen_*` is stamped only when the narrator names an NPC in prose (`_apply_npc_mentions` → `npcs_hit`, `narration_apply.py:1239–1242`). An NPC physically seated as an encounter opponent — HP/dials mutated round over round — goes un-stamped if not named that turn, so the engine treats an actively-fought combatant as "not recently seen." This is a precondition for sibling story 72-6 (LRU/last-seen prune), which would otherwise mis-evict active NPCs.

**Where to work (from context doc):** `encounter_lifecycle.py` — stamp at the presence seam `_seed_combat_hp_depletion_to_npcs` (~103–184), beside the existing `npc_edge_published_span` emit, and the parallel dial path `_publish_combat_stats` (~266) if it seats opponents the same way. Reuse `snapshot.party_location(perspective=...)` for location — do **not** invent a second location source (No Silent Fallbacks). Surface the stamped values as attributes on the existing `npc_edge_published_span` (OTEL: subsystem decision, must be visible — Keith's GM-panel lie-detector). No `Npc` model change — fields already exist (`session.py:157,160`).

**Scope guardrails:** Do not regress the prose-mention stamp (confirm it still fires). Do not implement 72-6's eviction. No membership/seating invariant changes (ADR-116). Tests assert *behavior* not source shape (No Source-Text Wiring Tests) — drive the real seam, assert the `Npc`'s stamped fields and/or the span attributes. Cover the three edge cases in the context doc: present-AND-mentioned (one consistent stamp), NPC-leaves (stamp freezes), and no-resolved-location (write `turn` but not a bogus location, mirroring the prose path).

**Context doc:** `sprint/context/context-story-72-8.md` — pre-written, thorough (paths, line numbers, ACs, edge cases). Do not regenerate; read it.

**Decision:** Setup complete, context sufficient for a trivial bug. Handing to Dev for implement phase. No open questions.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): A source-text wiring test asserts `_publish_combat_edge_to_npcs(` appears ≥2× in `encounter_lifecycle.py`. Affects `tests/server/test_npc_registry_combat_stats.py:297-307` (replace with an OTEL-span or fixture-driven behavior assertion per CLAUDE.md "No Source-Text Wiring Tests"). Survived my change but is brittle to refactor. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Neutral / non-opponent participants are not presence-stamped — only opponent-side actors flow through the two combat seams. If a future story wants "presence means presence" for bystanders joined via `participant_joined`, that seam needs the same stamp. Affects `sidequest/server/dispatch/encounter_lifecycle.py` (out of scope for 72-8 per context doc; opponents are the round-over-round mutated set this story targets). *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): The hp_depletion seam (`_seed_combat_hp_depletion_to_npcs`) has no *production-path* wiring test — `test_hp_depletion_seam_stamps_presence` calls it directly with a `types.SimpleNamespace` cdef, bypassing `instantiate_encounter_from_trigger` and the real `ConfrontationDef` accessors. The dial path IS wired-tested via `trigger_encounter`; the hp_depletion dispatch gate (`encounter_lifecycle.py:~1173` win_condition branch threading `acting_character_name=player_name`) is verified only by reading the diff. Affects `tests/server/dispatch/test_72_8_presence_last_seen_stamp.py` (add a `trigger_encounter` test against a real `win_condition: hp_depletion` pack — model on `test_space_opera_swn_combat_e2e.py` — asserting the opponent Npc's stamped fields, **including the CREATE branch** where the opponent has no backing Npc). Confirmed by [TEST] + [RULE] (two specialists, high confidence). *Found by Reviewer during code review.*
- **Gap** (non-blocking): Presence-stamping is gated inside `if cdef.category == "combat"`, so an `opposed_check` **social** confrontation that seats an opponent-side NPC never gets presence-stamped — reproducing 72-8's symptom for non-combat seated opponents. Pre-existing (not regressed by this diff; social opponents were never stamped) and out of 72-8's stated combat-seam scope. Affects `sidequest/server/dispatch/encounter_lifecycle.py` (follow-up story: stamp opponent-side presence for opposed_check/social seams too). Confirmed by [EDGE] (high confidence). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The OTEL span coerces `last_seen_location=npc.last_seen_location or ""`, so a genuinely-None location renders as `""` on the GM panel — indistinguishable from "resolved to empty." Low impact: the `Npc` field itself is correctly preserved (not clobbered), `party_location` returns `None` never `""` (so `""` unambiguously means "unresolved this turn"), and `or ""` is the established codebase OTEL string-hygiene pattern. Affects `sidequest/server/dispatch/encounter_lifecycle.py:~217,~374` (optional: omit the attr when None, or use a `"<unknown>"` sentinel). Confirmed by [SILENT] + [TYPE]. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The new-test module docstring says AC2 is "guarded by" `test_cite_known_npc_updates_last_seen_on_npc`, but that test only exercises the prose path's truthy-location branch, not the no-location branch. Affects the docstring in `tests/server/dispatch/test_72_8_presence_last_seen_stamp.py` (tighten the claim, or add a no-location prose-path test). Confirmed by [DOC]. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. Implemented exactly the two in-scope seams (`_seed_combat_hp_depletion_to_npcs`, `_publish_combat_edge_to_npcs`), reused `snapshot.party_location(perspective=acting_character_name)` (no second location source), mirrored the prose path's write discipline (turn always, location only when truthy), and surfaced the stamp on the existing `npc.edge_published` span (no new span family). No `Npc` model change. Prose path untouched.

### Reviewer (audit)
- **"No deviations from spec" (Dev)** → ✓ ACCEPTED by Reviewer: Verified against the context doc's IN SCOPE (both combat opponent seams stamped via the named accessor), OUT OF SCOPE (prose path untouched — confirmed; no `Npc` model change — confirmed; 72-6 eviction not implemented — confirmed; ADR-116 seating invariants untouched — confirmed), and all three required edge cases (no-location, NPC-leaves-freeze, present-AND-mentioned) are present as tests. The write discipline matches the prose path at `narration_apply.py:1631-1634` exactly (verified by [DOC], high confidence). The implementation is faithful to spec.
- No **undocumented** spec deviations found. The two coverage/scope gaps I confirmed (hp_depletion production-path test; opposed_check social opponents) are *thoroughness/scope* follow-ups, not deviations from what the story specified — the story scoped itself to the two combat seams and delivered exactly those.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/server/dispatch/encounter_lifecycle.py` — added `_stamp_encounter_presence` helper; added `acting_character_name` param to both opponent-presence seams (`_seed_combat_hp_depletion_to_npcs`, `_publish_combat_edge_to_npcs`); resolve `party_location(perspective=...)` once per seam and stamp `last_seen_turn`/`last_seen_location` on each opponent NPC; surfaced `last_seen_turn`/`last_seen_location` as attributes on the existing `npc.edge_published` span; wired both call sites in `instantiate_encounter_from_trigger` to pass `acting_character_name=player_name`.
- `tests/server/dispatch/test_72_8_presence_last_seen_stamp.py` — new: 7 tests covering AC1 (presence stamps without prose, via production wiring), the OTEL span attributes, the hp_depletion seam, and the three edge cases (no resolved location → turn-only; NPC leaves → frozen; present-AND-mentioned → one consistent stamp).

**Tests:** 48/48 passing (GREEN) — 7 new + 41 regression across the 4 touched-seam files (`test_npc_registry_combat_stats`, `test_npc_edge_publish_wiring`, `test_npc_pool_narration_apply`, `test_encounter_lifecycle`). ruff check + format clean.

**Branch:** feat/72-8-stamp-last-seen-encounter-presence (sidequest-server)

**Handoff:** To review phase (The Merovingian / Reviewer).
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 48/48 green, ruff check+format clean, 0 smells |
| 2 | reviewer-edge-hunter | Yes | findings | 7 | confirmed 2 (opposed_check gap, created-branch), dismissed 0, deferred 5 (consistent-with-existing: empty-string mirrors prose, split-party/ship-scale = existing `_npc_fallback_at_location` semantics, turn-phase, span ordering OK) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 1 (span `or ""` coercion, downgraded LOW w/ rationale), dismissed 0, deferred 2 (the `if location:` guard correctly mirrors prose path = intentional, not silent fallback; created-NPC None-location is correct discipline) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 2 (hp_depletion production-wiring test [HIGH], created-branch coverage), dismissed 0, deferred 4 (LOW: span count assert, multi-opponent partial-match, reverse-order consistency, AC2 self-containment) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 1 (AC2 citation overstates coverage), dismissed 0 (docstring "mirrors prose path" VERIFIED accurate — high conf), deferred 1 (72-6 forward-ref label) |
| 6 | reviewer-type-design | Yes | findings | 3 | confirmed 0, dismissed 0, deferred 3 (all LOW: `npc` param annotation exempt-private; non-optional `acting_character_name` is the correct invariant; `or ""` sound) |
| 7 | reviewer-security | Yes | clean | none | N/A — location is fiction-layer data to a local GM panel; no injection sink; O(actors) bounded |
| 8 | reviewer-simplifier | Yes | findings | 5 | confirmed 0, dismissed 0, deferred 5 (all style/proportionate-to-2pt: helper inline, comment dedup, test setup dedup, `_make_npc` defaults, pre-resolve comment) |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 1 (A4 hp_depletion wiring — corroborates [TEST]), deferred 1 (pre-existing `npcs_present: list` bare annotation, not in diff); **0 violations across the other 17 rules** |

**All received:** Yes (9 returned, 6 with findings, 2 clean, all assessed)
**Total findings:** 7 confirmed (0 blocking-severity), 0 dismissed, 18 deferred/non-blocking

### Rule Compliance

Rule-by-rule against CLAUDE.md (server) + Python lang-review checklist, enumerated over every changed function/test:

- **No Silent Fallbacks** — COMPLIANT. `_stamp_encounter_presence` `if location:` *refuses* a bogus location (mirrors prose `narration_apply.py:1631-1634`); it is not an alternative-path fallback. The two seams raise loudly elsewhere (`NoOpponentAvailableError`, `ValueError` on unknown type). Rule-checker A1: 0 violations across 8 instances.
- **No Stubbing** — COMPLIANT. `_stamp_encounter_presence` is a fully-wired 2-line implementation with two real production call sites; no empty shells.
- **No Source-Text Wiring Tests** — COMPLIANT. All 7 new tests assert behavior (Npc field state) or OTEL span attributes; none greps production source. Rule-checker A3: 0 violations.
- **Every Test Suite Needs a Wiring Test** — COMPLIANT at component level: `test_dial_presence_stamps_last_seen_without_prose_mention` drives `trigger_encounter` → `instantiate_encounter_from_trigger` → `_publish_combat_edge_to_npcs` end-to-end. CONFIRMED GAP (non-blocking, Medium): the hp_depletion *path* lacks its own production-path wiring test (logged as a Delivery Finding).
- **OTEL Observability Principle** — COMPLIANT. The recency stamp rides the existing `npc.edge_published` span as `last_seen_turn`/`last_seen_location` attributes (no new span family); `test_dial_presence_stamp_rides_npc_edge_published_span` proves the lie-detector signal. Rule-checker A5: 0 violations.
- **Type annotations at boundaries (lang #3)** — COMPLIANT for new code. `_stamp_encounter_presence` `npc` param is unannotated but the function is module-private (exempt). New `acting_character_name: str` params are annotated and correctly non-optional. (Pre-existing `npcs_present: list` bare annotation is not in this diff.)
- **Mutable defaults / resource leaks / unsafe deser / async / path / deps / input-validation (lang #2,#5,#7,#8,#9,#11,#12)** — COMPLIANT / N/A. Rule-checker: 0 violations (no defaults added, all spans use `with`, no I/O, synchronous, no new deps).
- **Test quality (lang #6)** — COMPLIANT. No vacuous assertions; every test asserts specific turn/location values with diagnostic messages; no skips/xfails.
- **Fix-introduced regressions (lang #13)** — COMPLIANT. Stamp is additive, ordered AFTER hp writes, cannot reduce prior values; `**attrs` span extension is backward-compatible.

### Observations

- [TEST][RULE] **hp_depletion seam lacks production-path wiring coverage** at `tests/server/dispatch/test_72_8_presence_last_seen_stamp.py:158` — `SimpleNamespace` cdef + direct call bypasses `instantiate_encounter_from_trigger` and the real `ConfrontationDef` accessors. Severity: **Medium** (component-level wiring IS proven by the dial path; this is the primary seam's thoroughness gap). Confirmed by two specialists. Non-blocking → logged as Delivery Finding.
- [EDGE] **opposed_check social opponents go un-stamped** — stamping is gated on `cdef.category == "combat"` (call sites at `encounter_lifecycle.py:1181,1197`). A seated social-duel opponent is "present" but never stamped. Severity: **Medium**, pre-existing (not regressed), out of stated scope → follow-up.
- [SILENT][TYPE] **span `last_seen_location or ""` renders None as `""`** at `:217,:374`. Severity: **Low** — the `Npc` field is correctly preserved; `party_location` returns None (never `""`) so `""` is an unambiguous "unresolved" sentinel; matches codebase OTEL hygiene.
- [VERIFIED] **stamp ordering is correct** — `_stamp_encounter_presence` is called BEFORE `npc_edge_published_span` at both seams (`:202` then `:208`; `:366` then `:367`), so the span reports the freshly-stamped (post-write) values, not stale `0`/None. Evidence: diff hunks; corroborated by [EDGE] line-208 trace. Complies with the OTEL principle.
- [VERIFIED] **No Silent Fallbacks honored** — the `if location:` guard refuses to write a bogus location, exactly mirroring the prose path at `narration_apply.py:1631-1634`. Evidence: [DOC] verified the mirror claim accurate (high confidence); [SILENT] confirmed the guard is intentional, not a swallow.
- [VERIFIED] **additive, non-regressive** — stamp cannot reduce `last_seen_turn` (callers pass current turn) and cannot clear `last_seen_location`; `**attrs` span extension is backward-compatible. Evidence: rule-checker #13, 6 instances, 0 violations. `test_npc_leaving_encounter_freezes_last_seen` proves the freeze property.
- [SEC] **clean** — `last_seen_location` is fiction-layer room text to a local-only GM panel; `acting_character_name` reaches only a dict-key lookup in `party_location` (no SQL/shell/template sink); work is O(actors). No findings.
- [SIMPLE] **proportionate** — the 2-line helper extraction and minor test-setup duplication are acceptable for a 2pt bugfix; no over-engineering. Deferred, non-blocking.

### Devil's Advocate

Let me argue this code is broken. First attack: the location is resolved ONCE before the opponent loop and applied to every opponent. In a split-party multiplayer fight, all opponents get stamped with the *triggering* PC's location even if the real fiction places them beside a different PC in another room — so 72-6's prune and `_npc_fallback_at_location` reads could later resurrect or evict an NPC at the wrong place. Counter: this is the *identical* perspective semantics `_npc_fallback_at_location` already uses (`perspective=acting_character_name`), so the stamp is no less accurate than the seating that produced these opponents in the first place; it does not introduce a *new* inaccuracy, and the split-party case is rare and pre-existing. Second attack: empty-string locations. `session.py`'s patch guard is `if patch.location is not None`, which lets `""` into `character_locations`; then `party_location` returns `""`, and `if location:` skips the write while the docstring claims it only skips on `None`. So a real (if degenerate) location is silently dropped. Counter: `""` is itself a degenerate/bogus location — skipping it is *more* correct than stamping it, and the prose path makes the exact same choice, so behavior is consistent table-wide; the true fix (sanitizing `""` at the patch boundary) is upstream and out of scope. Third attack: the freshly-created hp_depletion opponent (`created=True`) with no resolved location ships with `last_seen_location=None`, looking "never seen" to the prune even though it is on the board — a confused GM reading the panel sees a blank location for an NPC actively being fought. Counter: `last_seen_turn` IS stamped (non-zero), and recency-by-turn is what 72-6 keys on; a None location for an NPC whose party genuinely has no resolved location is honest, not a lie. Fourth attack, the strongest: the hp_depletion dispatch *branch* is untested through production — a future refactor that drops `acting_character_name=player_name` from the hp_depletion call site (line 1181) while leaving the dial site intact would pass every test in the suite, because the only hp_depletion test fakes the cdef and calls the function directly. That is a genuine regression window. This is why I confirmed it as a finding rather than waving it through — but its severity is Medium (the wiring exists today and is verified-present in the diff; the dial path proves the threading pattern works), so it is a tracked follow-up, not a merge blocker. A confused user (player) sees none of this — the field is dev-facing. A stressed filesystem is irrelevant (no I/O). Unexpected config fields cannot reach these pure-Python seams. Nothing here corrupts state or crashes a turn.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player action → `instantiate_encounter_from_trigger(player_name=...)` → combat branch → `_seed_combat_hp_depletion_to_npcs` / `_publish_combat_edge_to_npcs(acting_character_name=player_name)` → `actor_loc = snapshot.party_location(perspective=player_name)` → per opponent: `_stamp_encounter_presence(npc, turn, actor_loc)` writes `last_seen_turn` (always) + `last_seen_location` (only if resolved) → `npc.edge_published` span carries both. Safe because: the stamp is additive and ordered after HP writes, the location guard refuses bogus values (No Silent Fallbacks), and the threading is proven end-to-end on the dial path.

**Pattern observed:** Faithful mirror of the prose-mention stamp (`narration_apply.py:1631-1634`) extracted into a shared helper and applied at the two combat opponent seams — at `encounter_lifecycle.py:120-122` (helper), `:202`/`:366` (call sites), `:208-219`/`:367-376` (span surfacing).

**Error handling:** No new failure paths; the seams retain their loud guards (`NoOpponentAvailableError`, `ValueError` on unknown encounter type). Null/None location handled explicitly (turn-only stamp). No swallowed exceptions ([SILENT] 0 swallows; rule-checker A1 0 violations).

**Findings by source (all confirmed, none blocking):** [TEST]/[RULE] hp_depletion production-path wiring test gap (Medium); [EDGE] opposed_check social-opponent scope gap (Medium, pre-existing) + created-branch test gap (Medium); [SILENT]/[TYPE] span `None→""` coercion (Low); [DOC] AC2 citation overstates coverage (Low); [SIMPLE] proportionate style notes (Low, deferred); [SEC] clean. **No Critical/High severity issues** → does not block per the severity rubric. All substantive findings logged as non-blocking Delivery Findings for follow-up.

**Handoff:** To SM (Morpheus) for finish-story.