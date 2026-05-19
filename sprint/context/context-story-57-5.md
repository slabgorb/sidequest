---
parent: context-epic-57.md
workflow: tdd
---

# Story 57-5: game_state snapshot slimming (diff-with-anchor or field pruning)

## Business Context

The per-turn `<game_state>` block is the single largest uncached blob in the narrator's per-turn user message: **5–10 KB per turn, ~1–2 k tokens, sent every narrator turn**. It is constructed at `session_helpers.py:485` via `json.loads(snapshot.model_dump_json())`, mutated (drop `narrative_log`, redact non-self characters per the notorious-party gate, merge `party_formation` and `shared_world_delta`), and serialized at `session_helpers.py:558` with `json.dumps(state_summary_payload, indent=2)`. It is injected at `orchestrator.py:1581–1590` into the Valley zone of the three-zone caching split — which is uncached by design (state changes every turn).

The audit found three sources of bloat:

1. **`indent=2` pretty-printing.** Every nesting level pays one newline plus 2N spaces. Pure encoding waste — the LLM does not need pretty whitespace.
2. **Pydantic default fields serialized regardless of relevance.** Empty lists, default strings, `None` values for deferred subsystems (`active_tropes`, `axis_values`, `genie_wishes`, `achievement_tracker`, etc. per the `GameSnapshot` docstring at `session.py:518–530`).
3. **Fields whose presence is not load-bearing** because the narrator reads them via dedicated prompt sections (e.g., `active_tropes` re-rendered in the Recency-zone `pending_trope_context` block).

ADR-110 commits to a **two-phase ≥50% reduction** with zero narrator-quality regression, shipped as a single story under one PR. Diff-with-anchor (Option C) and tool-fetch (Option D) are explicitly deferred.

The doctrine constraint is sharp: cutting `<game_state>` blind risks silent quality regression. The narrator-gaslighting doctrine (project memory `project_narrator_gaslighting_doctrine.md`) materializes ground truth into the snapshot specifically *because* the narrator confabulates when starved. The diamonds-and-coal discipline (SOUL.md, ADR-014) likewise depends on the narrator seeing what matters. Every cut must be audit-driven and OTEL-verifiable.

## Technical Guardrails

**Source ADR:** `docs/adr/110-game-state-snapshot-slimming.md` — read in full. Specifically:

- §Context — the construction and injection sites, observed sizes, bloat sources.
- §Decision Phase A — compact JSON encoding with exact API call sequence.
- §Decision Phase B — field-pruning allowlist procedure.
- §Caching posture (unchanged) — Valley zone stays uncached. This story does not change zoning.
- §Observability — `<game_state>` byte-size span before/after, per-turn.
- §Acceptance gate — ≥50% reduction, zero quality regression.
- §Alternatives Considered — why C/D are deferred (read so you don't accidentally reach for them).

**Primary edit sites:**

1. `sidequest-server/sidequest/server/session_helpers.py:485–558` — the construction + serialization path for the SDK / standard backend.
2. `sidequest-server/sidequest/agents/local_dm.py:308` — the equivalent encode for the LocalDM preprocessor path. Per project memory, LocalDM is currently dormant (per the 2026-04-28 spec) but the encode site lives in code and must stay consistent with the canonical path. If LocalDM has been removed entirely, the implementer should confirm and log a Design Deviation.

**Phase A — exact transformation (ADR-110 §Phase A):**

Replace:
```python
state_summary_payload = json.loads(snapshot.model_dump_json())
# ... mutations ...
state_summary_text = json.dumps(state_summary_payload, indent=2)
```

with:
```python
state_summary_payload = snapshot.model_dump(
    mode="json",
    exclude_defaults=True,
    exclude_none=True,
)
# ... mutations (unchanged — operate on the dict in-place) ...
state_summary_text = json.dumps(state_summary_payload, separators=(",", ":"))
```

The downstream mutations (`pop("narrative_log")`, character-list redaction, `party_formation` / `shared_world_delta` injection) continue to operate on the dict in-place. **No semantic change** — pydantic round-trip equivalence holds.

**Phase B — field-pruning allowlist (ADR-110 §Phase B):**

Audit which fields the narrator actually consumes. Build an allowlist; drop fields not on it. Candidate fields to drop (from the audit, **verify per-field before cutting**):

- `active_tropes` — narrator reads from Recency-zone `pending_trope_context` instead.
- `axis_values` — re-rendered in `narrative_axis_status` section.
- `genie_wishes` — deferred subsystem.
- `achievement_tracker` — deferred subsystem.
- (Others — confirm against `GameSnapshot` docstring at `session.py:518–530` and the audit notes that birthed ADR-110.)

Each drop **must** be evidence-based: grep the prompt assembly for the field name; if no prompt section reads it, drop it. If a prompt section does read it, keep it. Document the per-field decision in the session file's "Field Audit" subsection.

**Observability gate (ADR-110 §Observability):**

Add OTEL span `prompt.game_state.bytes` emitted per turn with attributes: `phase_a_applied`, `phase_b_applied`, `bytes_before`, `bytes_after`. The before/after delta is the cost-savings metric. Without this, the cut cannot be verified post-merge.

**Acceptance gate (ADR-110):**

≥50% reduction in `<game_state>` bytes per turn, measured against a fixed snapshot fixture (or a playtest replay corpus). If the combined Phase A + Phase B does not reach 50%, the story does not pass — escalate to Option C (diff-with-anchor) under a new ADR.

**What NOT to touch:**

- Do not change the Valley-zone caching posture. `<game_state>` stays uncached — that's not what this story does.
- Do not implement Option C (diff-with-anchor) or Option D (tool-fetch). Both are explicitly deferred.
- Do not change `GameSnapshot`'s pydantic model. Phase B drops fields at *serialization time*, not at model definition time. The model continues to carry every field; the prompt does not.
- Do not refactor the post-`model_dump` mutations (`pop("narrative_log")`, character redaction, etc.). They are correct as-is; just feed them a different starting dict.
- Do not remove fields that the project-memory `project_narrator_gaslighting_doctrine.md` requires (the materialized creatures/NPCs/items in `snap.npcs` and similar — those are anti-confabulation anchors).

## Scope Boundaries

**In scope:**
- Phase A: replace `json.loads(snapshot.model_dump_json())` → `model_dump(mode="json", exclude_defaults=True, exclude_none=True)` at `session_helpers.py:485` and `local_dm.py:308`.
- Phase A: replace `json.dumps(payload, indent=2)` → `json.dumps(payload, separators=(",", ":"))` at the same sites.
- Phase B: audit each field in the snapshot for narrator consumption; build an allowlist; drop fields not consumed.
- Add `prompt.game_state.bytes` OTEL span at both encode sites.
- TDD: tests asserting Phase A and Phase B independently reach the documented size targets, on a fixed snapshot fixture.
- Pydantic round-trip equivalence test: a consumer parsing the compact form into `GameSnapshot` and back produces a `model_dump`-equivalent result.

**Out of scope:**
- Option C (diff-with-anchor) — deferred per ADR-110.
- Option D (tool-fetch / `query_state` tool) — deferred per ADR-110.
- Changes to `GameSnapshot` pydantic model.
- Changes to Valley-zone caching posture.
- The 57-3 promotions and 57-4 guardrail migrations (separate stories, parallel).
- Changes to the post-`model_dump` mutation pipeline beyond what's necessary to feed it the new starting dict.

## AC Context

1. **Phase A applied at both sites.** `git diff` shows the `model_dump_json` → `model_dump(mode="json", exclude_defaults=True, exclude_none=True)` change and the `indent=2` → `separators=(",", ":")` change at both `session_helpers.py:485+558` and `local_dm.py:308`. (If `local_dm.py` no longer exists, log a Design Deviation; Phase A still ships at `session_helpers.py`.)
2. **Phase B field audit documented.** The session file's "Field Audit" subsection lists every snapshot field with a verdict (kept / dropped) and one-line evidence (grep result of where the field is consumed in the prompt assembly, or "not consumed").
3. **`<game_state>` bytes reduced ≥50%.** Measured on a fixed snapshot fixture (or a replay of a playtest corpus). The OTEL span `prompt.game_state.bytes` shows `bytes_after / bytes_before ≤ 0.5`. If this target is not met, the story does not pass.
4. **Pydantic round-trip equivalence.** A test parses the compact serialized form back into `GameSnapshot` and asserts `parsed.model_dump() == original.model_dump()`. (Defaults reconstruct on parse, so the equivalence holds even though defaults aren't serialized.)
5. **Zero narrator-quality regression.** For a fixed test corpus of 20+ narrator turns: (a) the narrator does not confabulate facts that the snapshot used to anchor, (b) the `game_patch` field population rate is ≥ pre-migration rate. Same regression-counter pattern as 57-4. If the rate drops, the field cut was too aggressive — restore that field and re-measure.
6. **OTEL span live.** `prompt.game_state.bytes` emits per turn with `phase_a_applied`, `phase_b_applied`, `bytes_before`, `bytes_after`. GM panel can read this; the cost-saving claim is verifiable post-merge.
7. **Existing tests stay green.** Full `just server-test` runs green. No regressions in `session_helpers`, `agents/orchestrator`, or `game/session` test modules.

## Assumptions

- Pydantic v2's `model_dump(mode="json", exclude_defaults=True, exclude_none=True)` produces output round-trip-equivalent to `model_dump_json()` for the `GameSnapshot` model. This is documented Pydantic v2 behavior. If `GameSnapshot` has custom serializers that defeat the equivalence (e.g., a field that serializes differently via JSON path), Phase A's "no semantic change" claim breaks and the implementer logs a Design Deviation.
- The narrator's actual field consumption is grep-discoverable in the prompt assembly. If a field is consumed via dynamic attribute access (e.g., `getattr(snapshot, dynamic_field_name)`), grep will miss it; the implementer needs deeper tracing for those cases.
- The narrator-gaslighting doctrine anchors (creatures, NPCs, items materialized into `snap.npcs`) are present and load-bearing. Phase B's allowlist MUST preserve these. If the audit suggests dropping a field that materializer wrote into, that's the doctrine talking back — keep the field, log the false positive.
- ADR-098's stateless-narrator posture is unchanged. This story does not introduce a multi-turn anchor or any state-carrying mechanism beyond what the existing snapshot already does.
- LocalDM may be dormant (per `agents/llm_factory.py` and the 2026-04-28 spec). The implementer confirms at implementation start whether `local_dm.py:308` still exists. If not, Phase A still ships at `session_helpers.py` and the LocalDM site is dropped from scope (Design Deviation logged).
