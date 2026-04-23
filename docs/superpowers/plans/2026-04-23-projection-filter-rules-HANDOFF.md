# ProjectionFilter Rules — Session Handoff

**Paste this entire document into a fresh Claude Code session to resume.**

---

## Where you are

A complete implementation of the ProjectionFilter Rules feature has landed across three repos. The implementation plan is fully executed (25 of 25 tasks). A final cross-task code review ran and identified **3 Critical correctness gaps** + **3 Important observability/tooling gaps** + **5 Minor/Nitpick items** that per-task reviews missed. None are blockers for merge, but C1–C3 break production semantics and should be fixed before any genre ships a non-empty `projection.yaml`.

**Source documents (in order of authority):**
- Design spec: `/Users/slabgorb/Projects/oq-2/docs/superpowers/specs/2026-04-23-projection-filter-rules-design.md`
- Implementation plan: `/Users/slabgorb/Projects/oq-2/docs/superpowers/plans/2026-04-23-projection-filter-rules.md`
- Related spec: `/Users/slabgorb/Projects/oq-2/docs/superpowers/plans/2026-04-22-mp-03-filtered-sync-and-projections.md` (MP-03 — this feature extends, does not replace)

**Context for the feature itself:**
The spec delivers per-player asymmetric info projections for SOUL.md scenarios 1 (targeting — secret notes, private dice) and 2 (redaction — fog-of-war HP, hidden enemy positions). Scenario 3 (charm / illusion / false perception) is **explicitly out of scope** and requires a separate spec with narrator cooperation. The design chose: core-invariant + genre-configured hybrid authority; a closed 6-predicate vocabulary; a `projection_cache` SQLite table so reconnect/replay is byte-identical to live; OTEL spans on every filter decision as the GM-panel lie detector.

## Repo state

### Orchestrator repo: `/Users/slabgorb/Projects/oq-2`
- **Branch:** `chore/sprint-orchestrator-mp01-updates`
- **Commits landed:** `bfb3593` (spec), `daa4473` (plan), `424bfe9` (predicate catalog docs)
- Also filed: sprint story `37-52` in `sprint/epic-37.yaml` — chore to delete legacy `/api/saves/*` endpoints after MP-03

### Work repo: `/Users/slabgorb/Projects/oq-2/sidequest-server`
- **Branch:** `feat/projection-filter-rules`
- **Commits ahead of `feat/phase-3-story-3-4-combat-dispatch`:** 24
- **Test status:** `.venv/bin/python -m pytest` → 1710 passed, 25 skipped, 5 pre-existing failures (in `test_orchestrator.py` and `test_rest.py`, verified pre-existing by stash). 80/80 projection-specific tests green. The E2E wiring test (`tests/server/test_projection_end_to_end_wiring.py`) passes and enforces the single-truth invariant.

Verify with:
```bash
git -C /Users/slabgorb/Projects/oq-2/sidequest-server branch --show-current
git -C /Users/slabgorb/Projects/oq-2/sidequest-server log --oneline 7b3d24f..HEAD
cd /Users/slabgorb/Projects/oq-2/sidequest-server && .venv/bin/python -m pytest tests/game/projection tests/server/test_projection_end_to_end_wiring.py
```

### Content repo: `/Users/slabgorb/Projects/oq-2/sidequest-content`
- **Branch:** `develop` (1 commit)
- Added: `genre_packs/mutant_wasteland/projection.yaml` with empty rules — opt-in marker only; real fog-of-war rules deferred until CONFRONTATION / STATE_UPDATE payload schemas stabilize.

## Commits landed (sidequest-server, newest first)

```
fix(projection): attach OTEL exporter to existing TracerProvider in tests
test(projection): end-to-end wiring test (single-truth invariant)          # T24
feat(projection): GenrePack loader reads + validates projection.yaml       # T22
feat(projection): projection.yaml validate CLI (argparse)                  # T21 — downscoped from click CLI
feat(projection): OTEL spans for filter decide + cache fill                # T20
feat(projection): lazy-fill cache on mid-session join                      # T19
feat(projection): reconnect reads projection_cache                         # T18
feat(projection): wire ComposedFilter + projection_cache into SessionHandler  # T17
feat(projection): ProjectionCache reader/writer                            # T16
feat(projection): ComposedFilter wiring                                    # T15
feat(projection): GenreRuleStage redact_fields handling                    # T14
feat(projection): GenreRuleStage include_if handling                       # T13
feat(projection): GenreRuleStage scaffold with target_only                 # T12
feat(projection): field path applicator (dotted + [*])                     # T11
feat(projection): rule validator (7 semantic checks)                       # T10
feat(projection): rule schema + YAML loader                                # T9
feat(projection): GM-only kind invariant (THINKING)                        # T8
feat(projection): self-authored core invariant                             # T7
feat(projection): targeted-by-field core invariant                         # T6
feat(projection): CoreInvariantStage with GM-sees-canonical                # T5
feat(projection): predicate catalog (6 predicates)                         # T4
feat(projection): SessionGameStateView adapter                             # T3
feat(projection): MessageEnvelope + GameStateView protocol                 # T2
feat(projection): add projection_cache SQLite table                        # T1
```

## Outstanding findings from final code review

### Critical (correctness — fix before shipping a non-empty projection.yaml)

**C1. GM identity is hardcoded to `None` in `_build_game_state_view`.**
Location: `sidequest-server/sidequest/server/session_handler.py:314-319`

The implementation hardcodes `gm_player_id=None` on both return paths. `SessionGameStateView.is_gm()` returns False for every player when `gm_player_id is None`. Consequences:
- `CoreInvariantStage` GM invariant never short-circuits in production
- Any genre rule with `unless: is_gm()` never exempts anyone
- The GM panel's "lie detector" foundation is structurally broken

This is distinct from the (already documented) `player_id_to_character` character-mapping gap. GM identity does NOT need character mapping to work — just "which player is the GM." Today `_SessionData` has a `mode: GameMode | None` field (`GameMode.SOLO` / `GameMode.MULTIPLAYER`) but no explicit GM designation. For solo sessions, the conceptual GM is `None` (no separate GM player); for multiplayer, the GM-seat assignment needs to be plumbed through. Probably the cleanest fix is: for solo, leave `gm_player_id=None` (correct — no human GM); for multiplayer, derive from `self._room.gm_player_id` or an equivalent once MP-02 seating lands. Either way, the comment in `_build_game_state_view` must be honest about this being unwired rather than implying it's fine.

Fix shape: read `_SessionData.mode` + (future) seat assignment from `self._room`; document clearly.

**C2. Single-transaction guarantee violated between `EventLog.append` and `ProjectionCache.write`.**
Location: `sidequest-server/sidequest/game/event_log.py:27-36` and `sidequest-server/sidequest/server/session_handler.py::_emit_event` fan-out loop (line ~347 area)

Spec requires: "The event append and its associated cache writes occur in a single DB transaction (so the cache never outlives its event or vice versa)."

Reality: `EventLog.append()` commits its own `with self._store._conn:` transaction and returns. The fan-out loop then calls `ProjectionCache.write()` for each player, each in its own transaction. A server crash in the gap leaves an event in `EventLog` with zero cache rows. Current mitigation: `lazy_fill` on reconnect fills gaps — but `lazy_fill` runs against *current* GameStateView, not view-at-event-time. Spec documents that softening only for mid-session joins, not post-crash reconnects.

Fix shape: open a single connection-level transaction for the whole emit, append + all cache writes + commit. Either widen `EventLog.append` to accept a callback for cache writes, or have `_emit_event` drive the transaction itself via a dedicated helper.

**C3. `model_copy(update=...)` is a partial merge in fan-out — removed fields leak through.**
Location: `sidequest-server/sidequest/server/session_handler.py::_emit_event` around lines 397-402

Code:
```python
recipient_payload = payload_model.model_copy(
    update={**json.loads(decision.payload_json), "seq": seq}
)
```

`model_copy` with `update` merges — fields NOT in the filtered JSON keep their original canonical values. Today's rules only mask values (string substitutions), so no field ever goes missing from the filtered JSON, so the bug doesn't fire. But any future rule that *drops* a field entirely causes the canonical value to silently appear. Additional smell: `json.loads(decision.payload_json)` is called twice (once at line ~397 into a discarded `filtered_data`, once at line ~401 inside the update).

Fix shape: rebuild the recipient payload from the filtered dict alone (with `seq` injected). Don't use `model_copy`; construct `payload_model.__class__.model_validate(filtered_dict)`.

### Important (observability / drift)

**I5. `FILTER_REACHABLE_KINDS` duplicates `_KIND_TO_MESSAGE_CLS` with no sync test.**
Location: `sidequest-server/sidequest/game/projection/validator.py:28-31` and `sidequest-server/sidequest/server/session_handler.py::_KIND_TO_MESSAGE_CLS`

Both currently `{"NARRATION", "CONFRONTATION"}`. The comment says "Must stay in sync." No test enforces it. Drift = validator rejects valid rules for newly-reachable kinds with a misleading "not filter-reachable" error.

Fix shape: derive `FILTER_REACHABLE_KINDS` from `_KIND_TO_MESSAGE_CLS.keys()` at module import (same lazy-import pattern already used by `_schema_fields_for_kind`). Or add a test that asserts equality.

**I6. OTEL `rule.source` attribute doesn't match spec format.**
Location: `sidequest-server/sidequest/game/projection/composed.py` lines 53-57

Spec requires: `genre:<pack>/<kind>/<rule_index>`
Implementation emits: `genre:<kind>`

GM panel cannot distinguish which rule fired or which genre ships it. Multi-genre observability is blind.

Fix shape: thread the genre-pack name into ComposedFilter at construction; index rules by position when `GenreRuleStage` stores them; combine in `_invariant_source` / `rule.source` attribute emission.

**I7. `_invariant_source` has a silent `"invariant:unknown"` fallback.**
Location: `sidequest-server/sidequest/game/projection/composed.py` (bottom helper)

If a future invariant is added to `CoreInvariantStage` without matching branch in `_invariant_source`, the OTEL attribute silently emits `"invariant:unknown"` instead of failing loud. SOUL.md critical rule: no silent fallbacks.

Fix shape: raise `RuntimeError` (with a loud message naming the envelope kind) in the fallback branch, or make `CoreInvariantStage.evaluate` return a `source` string directly alongside `InvariantOutcome` so the single source of truth is the stage itself.

### Minor / Nitpick

**M8.** `PassThroughFilter` imported but unused in `session_handler.py:48`. Dead import.
**M9.** `projection.cache.lazy_fill` span is missing the `ms` elapsed-time attribute the spec listed.
**M10.** E2E wiring test doesn't cover the solo-player reconnect gap — emitters skip their own fan-out, so without lazy_fill they have no cache row. `lazy_fill` covers them today, but a regression that breaks this path would pass the current E2E test.
**M11.** In `genre_stage.py::evaluate`, `payload` and `working` are aliases to the same dict; `apply_mask` mutates `payload`, so a `TargetOnlyRule` following a `RedactFieldsRule` for the same kind reads the already-mutated dict. Harmless for today's rule shapes; latent ordering dependency worth a comment.
**M12.** Plan called for a dedicated `sidequest/game/projection/otel.py` module for spans; implementation (correctly, IMO) landed helpers in the existing `sidequest/telemetry/spans.py` alongside all other OTEL helpers. Plan was wrong; document deviation.

## Plan deviations logged (from per-task reviews)

- **T1, T2** — test assertions split (sqlite3.Row vs tuple); legit adaptation.
- **T10** — `NonBlankString` is a `RootModel[str]`, not `Annotated[str, ...]`. Added `_unwrap_rootmodel` helper.
- **T17** — `Character` has no `player_id` attribute; `_build_game_state_view` leaves `player_id_to_character` empty with a comment. (Combined with C1 above to form the real gap.)
- **T18/T19** — `lazy_fill` wiring landed in the T18 commit (not T19) because cache-first replay is meaningless without it.
- **T21** — downscoped from "pf click-based CLI" to standalone argparse module `python -m sidequest.cli.validate.projection_check` since `pf` is pennyfarthing-side and sidequest-server has no click dependency.
- **T23** — empty rules file (no concrete fog-of-war rules yet) because CONFRONTATION / STATE_UPDATE payload schemas aren't stable.
- **OTEL test fix (post-T24)** — tests used `trace.set_tracer_provider()` which silently no-ops when a provider is already set; attached SpanProcessor to current provider instead.

## Critical gotchas discovered during implementation

**Signature transition.** `ProjectionFilter.project()` changed from `(event: EventRow, player_id)` to `(envelope: MessageEnvelope, view: GameStateView, player_id)`. All call sites migrated. `PassThroughFilter` still exists in `projection_filter.py` for the Protocol reference implementation, under the new signature.

**`_KIND_TO_MESSAGE_CLS` is the filter-reachable truth table.** Currently only `NARRATION` and `CONFRONTATION` flow through `_emit_event`. Rules authored for any other kind will be blocked by the validator (intended — no silent fallbacks). When a new kind is routed through `_emit_event`, it must be added to `_KIND_TO_MESSAGE_CLS` AND to `FILTER_REACHABLE_KINDS` (see I5).

**`GenrePack.projection_rules` and `GenrePack.source_dir` are new optional fields** added in Task 22. Downstream code that serializes `GenrePack` round-trip should handle them (the model config is `extra="allow"` so this isn't strictly needed).

**Predicate conservatism.** Every predicate returns `False` on missing fields / unknown relationships. This means a redaction rule whose `unless` predicate can't evaluate will keep the field masked — the safe direction. Never the other way.

**Scope explicitly out:**
- Scenario 3 (charm/illusion/substitution) — needs narrator cooperation, separate spec
- World-level rule overrides (genre-level only in v1)
- All-outbound-message coverage (filter signature is `MessageEnvelope`-shaped for later widening; today only EventLog-origin events pass through)
- Derived-snapshot store (YAGNI per MP-03)
- Time/TTL-based redaction; dynamic mask values; predicate conjunction/disjunction

## Recommended next steps

Three tiers for the fix pack, in descending priority:

- **Tier 1 (must fix before shipping a non-empty `projection.yaml`):** C2 (transaction scope) + C3 (model_copy leak). Both are correctness bugs. Scoped to `_emit_event` in `session_handler.py` and `EventLog.append`. Can be one subagent.
- **Tier 2 (must fix for the GM panel to function as a lie detector):** C1 (GM identity gap). Touches `_build_game_state_view` and may need room/seat wiring from MP-02. Should be its own subagent.
- **Tier 3 (observability + cleanup, file as follow-up stories):** I5, I6, I7, M8–M12. None block correctness. File as a single chore story under epic 37 alongside the existing `37-52` legacy-saves chore.

**Quick options when you resume:**
- To fix Tier 1 + Tier 2 now: dispatch two subagents (or one for tier 1, one for tier 2), then re-run full suite + E2E wiring test.
- To ship as-is: file C1/C2/C3 as three separate p1 bug stories under epic 37, merge the `feat/projection-filter-rules` branch into `develop`, then pick up Tier 1 work as the next story.
- To ship with only Tier 1: fix C2 + C3 inline, file C1 as a p1 bug alongside Tier-3 chore, merge.

## Execution method (if continuing with subagents)

Use `superpowers:subagent-driven-development` per task, or for a single focused fix dispatch a single Dev subagent with a tight scope. Full reviewers (`superpowers:code-reviewer`) are appropriate for C1/C2/C3 fixes since each touches fan-out or state semantics.

The original plan file (`docs/superpowers/plans/2026-04-23-projection-filter-rules.md`) can still be referenced for code conventions, file paths, and test patterns. It's complete and accurate; the outstanding items above are deviations from its intent discovered in review.

After any fix pack: merge via `superpowers:finishing-a-development-branch`. The sidequest-server branch targets `develop` (per `repos.yaml` branching strategy, NOT main).

## Base commits for diff anchoring

- sidequest-server base (before work): `7b3d24f` (`chore(server): ruff + pyright cleanup on story 3.4 surface (story 3.4)`)
- sidequest-server head: `git -C sidequest-server rev-parse HEAD` (currently `d31345f` plus the fix commit on top)
- sidequest-content base: whatever `develop` pointed at before the mutant_wasteland projection.yaml commit
- Orchestrator base: `5607c38` (`chore(sprint): reconcile 37-44 status to done`) — but the branch had pre-existing sprint YAML churn when this session started; the 3 docs commits are additive.
