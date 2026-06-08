# Confrontation Intent Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate `ActionRewrite.intent` as the authoritative intent field for confrontation detection by wiring a per-confrontation-def validator into the narration-apply pipeline, deleting the prose-regex lie-detector, and populating `TurnRecord.classified_intent` from the real signal.

**Architecture:** Three-layer change. (1) Each `ConfrontationDef` self-describes an intent verb set derived at pack-load from `label` + `beats[].label` and extended via optional `intent_verbs:`. (2) A pure-function validator in `sidequest-server/sidequest/agents/confrontation_intent_validator.py` compares the narrator's declared `action_rewrite.intent` against the chosen `confrontation` and returns a `ValidationResult` typed by the def's `on_intent_mismatch:` (`warn` / `soft_suggest` / `reprompt`). (3) `narration_apply._apply_narration_result_to_snapshot` dispatches on severity; the orchestrator wraps `run_narration_turn` in a one-shot retry for `reprompt`. The legacy `_CONFRONTATION_TRIGGER_PATTERNS` + scanner + `skipped_with_trigger_keywords` watcher emission are deleted in the same change; `classified_intent="unknown"` hardcodes are removed.

**Tech Stack:** Python 3.12 (uv), pydantic v2, pytest, OpenTelemetry. Pack YAML edits in `sidequest-content/genre_packs/*/rules.yaml`.

**Spec:** `docs/superpowers/specs/2026-05-20-confrontation-intent-validator-design.md`

**Related ADRs:** ADR-033 (Confrontation Engine), ADR-067 (Unified Narrator), ADR-031 (Watcher), ADR-103 (Native OTEL), ADR-101 (Anthropic SDK).

---

## File Map

**NEW**
- `sidequest-server/sidequest/agents/confrontation_intent_validator.py` — `ValidationResult` dataclass, `tokenize()` helper, `validate()` pure function.
- `sidequest-server/tests/agents/test_confrontation_intent_validator.py` — unit tests for the validator.
- `sidequest-server/tests/genre/test_pack_load_intent_schema.py` — pack-load schema + intent-verb derivation tests.
- `sidequest-server/tests/server/test_narration_apply_intent_dispatch.py` — dispatch branch tests (warn / soft_suggest / reprompt) with fixture pack.
- `sidequest-server/tests/agents/test_orchestrator_reprompt_loop.py` — orchestrator one-shot retry.
- `sidequest-server/tests/server/test_intent_classified_invariant.py` — wiring tests + `classified_intent != "unknown"` invariant.
- `sidequest-server/tests/server/test_legacy_trigger_patterns_removed.py` — deletion guard.
- `sidequest-server/tests/server/test_dust_and_lead_horse_replay.py` — replay regression against the 2026-05-20 save.
- `sidequest-server/tests/fixtures/intent_test_pack/` — minimal pack fixture with three confrontations, one per severity.
- `sidequest-server/tests/fixtures/dust_and_lead_horse_replay/` — extracted turns 5–10 + minimal `game_state`.

**MODIFIED — sidequest-server**
- `sidequest/genre/models/rules.py` — add `intent_verbs: list[str] | None` and `on_intent_mismatch: Literal["warn","soft_suggest","reprompt"]` to `ConfrontationDef`; cache `intent_verb_set: frozenset[str]` (excluded from serialization).
- `sidequest/genre/loader.py` — derive + cache `intent_verb_set` per def at load.
- `sidequest/genre/models/pack.py` — add `intent_verbs_by_type` property on `GenrePack` that maps `confrontation_type → frozenset[str]`.
- `sidequest/game/session.py` — add `next_turn_directives: list[str] = Field(default_factory=list)` to `GameSnapshot`.
- `sidequest/server/narration_apply.py` — replace legacy scanner block at `2525-2549` with `confrontation_intent_validator.validate(...)`; add severity dispatch; expose `reprompt_request` on `NarrationApplyOutcome`; populate `TurnRecord.classified_intent` at every exit.
- `sidequest/agents/orchestrator.py` — add one-iteration reprompt wrapper around `run_narration_turn`; thread `extra_directive` into the second call; consume + clear `snapshot.next_turn_directives` in prompt-section assembly (recency zone).
- `sidequest/agents/narrator.py` (and SDK variant `_run_narration_turn_sdk`) — accept optional `extra_directive: str | None` parameter, surfaced into recency zone.
- `sidequest/server/websocket_session_handler.py` — remove `classified_intent="unknown"` at `:4696` and `:4819`; pull from result/applied outcome.
- `sidequest/telemetry/spans.py` — add `confrontation_intent_mismatch_span`, `confrontation_intent_mismatch_resolved_span`, `confrontation_intent_mismatch_reprompt_failed_span`.
- `sidequest/server/dashboard.py` — surface the three new span types.

**DELETED — sidequest-server**
- `sidequest/server/narration_apply.py:425-498` — `_CONFRONTATION_TRIGGER_PATTERNS` tuple and `_scan_for_confrontation_trigger_keywords`.
- `sidequest/server/narration_apply.py:2525-2549` — the lie-detector call + watcher publish (the whole `if not result.confrontation and (snapshot.encounter is None or snapshot.encounter.resolved) and result.narration:` block).
- Any existing test that exercises `_CONFRONTATION_TRIGGER_PATTERNS` directly.

**KEPT (do not delete despite name overlap)**
- `sidequest/agents/narrator_guardrails.py::CONFRONTATION_TRIGGER_CONSTRAINT` — this is the *prompt* guardrail instructing the narrator to emit `confrontation` when its prose triggers; the spec keeps prompt assembly unchanged. The Recency-zone registration at `orchestrator.py:1882` and tool-description usage in `agents/tools/generate_encounter.py:101` both stay.

**MODIFIED — sidequest-content (7 packs)**
For each pack below, add `on_intent_mismatch:` (and `intent_verbs:` when the derived set looks thin) to every confrontation def in `rules.yaml`:
- `caverns_and_claudes/rules.yaml` — combat, chase, negotiation
- `elemental_harmony/rules.yaml` — negotiation, combat, chase
- `mutant_wasteland/rules.yaml` — negotiation, combat, chase
- `road_warrior/rules.yaml` — negotiation, combat, chase
- `space_opera/rules.yaml` — negotiation, ship_combat, combat, chase, dogfight
- `spaghetti_western/rules.yaml` — standoff, negotiation, poker, combat, chase
- `tea_and_murder/rules.yaml` — negotiation, trial, auction, social_duel, scandal

Default policy per spec table:
- Lethal/genre-truth heavy → `reprompt`: combat, ship_combat, dogfight, chase, standoff
- Social-pressure / transactional → `warn`: negotiation, poker, trial, auction, social_duel, scandal
- Everything else → `warn`

**MODIFIED — docs**
- `docs/adr/0067-unified-narrator-agent.md` — amendment recording that the inference site is `confrontation_intent_validator.validate(...)`, `classified_intent` is populated from `action_rewrite.intent` or the matched type, and the legacy regex lie-detector is retired in the same change.

---

## Conventions

- Test commands run from `sidequest-server/`: `uv run pytest -v <path>`. Lint: `uv run ruff check .`. From the orchestrator root, `just server-check` runs both.
- All new modules use 4-space indent, `from __future__ import annotations`, type hints, and `frozen=True` dataclasses where applicable.
- Commit messages follow the repo convention (`feat:`/`refactor:`/`test:`/`docs:`/`chore:`).
- One PR per the spec's one-mechanism doctrine. Each task ends with a commit on the same feature branch so the PR-author can `git log` the work later. Branch name suggestion: `feat/confrontation-intent-validator`.

---

## Task 1: Schema fields on `ConfrontationDef`

Add `intent_verbs` and `on_intent_mismatch` to the pydantic model. Pure schema work — no behavior change yet, no derivation, no consumers.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py:329-396`
- Test: `sidequest-server/tests/genre/test_pack_load_intent_schema.py` (new)

- [ ] **Step 1: Write the failing schema tests**

Create `sidequest-server/tests/genre/test_pack_load_intent_schema.py`:

```python
"""Schema tests for ConfrontationDef.intent_verbs and .on_intent_mismatch."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import ConfrontationDef


def _minimal_def(**extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "type": "negotiation",
        "label": "Tense Negotiation",
        "category": "social",
        "player_metric": {"name": "leverage", "start": 0, "target": 10},
        "opponent_metric": {"name": "patience", "start": 0, "target": 10},
        "beats": [{"id": "haggle", "label": "Haggle", "stat_check": "cha"}],
    }
    base.update(extra)
    return base


def test_on_intent_mismatch_defaults_to_warn() -> None:
    cdef = ConfrontationDef.model_validate(_minimal_def())
    assert cdef.on_intent_mismatch == "warn"


def test_on_intent_mismatch_accepts_three_values() -> None:
    for value in ("warn", "soft_suggest", "reprompt"):
        cdef = ConfrontationDef.model_validate(_minimal_def(on_intent_mismatch=value))
        assert cdef.on_intent_mismatch == value


def test_on_intent_mismatch_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError) as exc:
        ConfrontationDef.model_validate(_minimal_def(on_intent_mismatch="ignore"))
    assert "on_intent_mismatch" in str(exc.value)


def test_intent_verbs_defaults_to_none() -> None:
    cdef = ConfrontationDef.model_validate(_minimal_def())
    assert cdef.intent_verbs is None


def test_intent_verbs_accepts_list_of_strings() -> None:
    cdef = ConfrontationDef.model_validate(
        _minimal_def(intent_verbs=["haggle", "bargain", "barter"])
    )
    assert cdef.intent_verbs == ["haggle", "bargain", "barter"]


def test_intent_verbs_rejects_non_string_elements() -> None:
    with pytest.raises(ValidationError) as exc:
        ConfrontationDef.model_validate(_minimal_def(intent_verbs=["bargain", 5]))
    assert "intent_verbs" in str(exc.value)
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_load_intent_schema.py -v`
Expected: 6 FAIL — `extra="forbid"` rejects unknown fields.

- [ ] **Step 3: Add the two fields to `ConfrontationDef`**

Edit `sidequest-server/sidequest/genre/models/rules.py`. After the existing fields (after `morale: MoraleDef | None = None` near line 358), add:

```python
    # Spec 2026-05-20 confrontation-intent-validator — narrator intent
    # vocabulary surface for the dormant-ActionRewrite.intent activation.
    intent_verbs: list[str] | None = None
    on_intent_mismatch: Literal["warn", "soft_suggest", "reprompt"] = "warn"
```

Add the `Literal` import at the top of the file if not already present:

```python
from typing import Literal
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_load_intent_schema.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Run full pack-load test suite to confirm no production-pack regressions**

Run: `cd sidequest-server && uv run pytest tests/genre/ -v`
Expected: ALL PASS — every existing pack must still load (`extra="forbid"` rejects nothing new; defaults are backward-compatible).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/genre/models/rules.py \
        sidequest-server/tests/genre/test_pack_load_intent_schema.py
git commit -m "feat(rules): add intent_verbs + on_intent_mismatch to ConfrontationDef

Spec 2026-05-20 confrontation-intent-validator step 1: schema-only,
no behavior. Defaults (intent_verbs=None, on_intent_mismatch='warn')
keep all 7 production packs loading unchanged."
```

---

## Task 2: Pack-load intent vocabulary derivation

Compute and cache `intent_verb_set: frozenset[str]` per `ConfrontationDef` at load time. Expose a `GenrePack.intent_verbs_by_type` mapping. Tokenization rules live here — same code path used at validation time later.

**Files:**
- Create: `sidequest-server/sidequest/agents/confrontation_intent_validator.py` (tokenize() only this task)
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (add cached field on ConfrontationDef)
- Modify: `sidequest-server/sidequest/genre/loader.py:540-560` area (call derivation)
- Modify: `sidequest-server/sidequest/genre/models/pack.py:154-200` area (add accessor)
- Test: `sidequest-server/tests/agents/test_confrontation_intent_validator.py` (new — tokenize-only this task)
- Test: `sidequest-server/tests/genre/test_pack_load_intent_schema.py` (extend)

- [ ] **Step 1: Write the failing tokenizer tests**

Create `sidequest-server/tests/agents/test_confrontation_intent_validator.py`:

```python
"""Unit tests for confrontation_intent_validator.

This task: tokenize() only. validate() lands in Task 3.
"""

from __future__ import annotations

from sidequest.agents.confrontation_intent_validator import tokenize


def test_tokenize_lowercases() -> None:
    assert tokenize("Haggle") == frozenset({"haggle"})


def test_tokenize_splits_on_non_alphanumeric() -> None:
    assert tokenize("draw-down, fire!") == frozenset({"draw", "down", "fire"})


def test_tokenize_strips_stopwords() -> None:
    # "the", "a", "with" all dropped
    result = tokenize("the man with a gun")
    assert "the" not in result
    assert "a" not in result
    assert "with" not in result
    assert "man" in result
    assert "gun" in result


def test_tokenize_suffix_strips_ing_ed_s() -> None:
    assert tokenize("haggling") == frozenset({"haggl"})
    assert tokenize("haggled") == frozenset({"haggl"})
    assert tokenize("offers") == frozenset({"offer"})


def test_tokenize_does_not_porter_stem() -> None:
    # "draw" and "drawer" must NOT collapse (Porter would conflate them)
    result = tokenize("draw drawer")
    assert "draw" in result
    assert "drawer" in result


def test_tokenize_empty_input_returns_empty_frozenset() -> None:
    assert tokenize("") == frozenset()
    assert tokenize("   ") == frozenset()


def test_tokenize_idempotent() -> None:
    once = tokenize("Bargaining hard for the horse")
    twice = tokenize(" ".join(sorted(once)))
    assert twice <= once  # tokenizing the output never adds new tokens
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/agents/test_confrontation_intent_validator.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the validator module with `tokenize()`**

Create `sidequest-server/sidequest/agents/confrontation_intent_validator.py`:

```python
"""Confrontation intent validator.

Spec: docs/superpowers/specs/2026-05-20-confrontation-intent-validator-design.md

Activates the dormant ``ActionRewrite.intent`` field as the authoritative
intent signal. Pure function. No I/O. Stateless. Never raises on bad input.

The ``validate()`` function lands in Task 3. This module starts with
``tokenize()`` because pack-load (Task 2) and validation (Task 3) MUST use
byte-identical tokenization rules.
"""

from __future__ import annotations

import re

# Conservative stopword set. Kept short on purpose — the goal is to drop
# function words that add no semantic signal, not to do NLP. Anything that
# could plausibly be a content word in a confrontation label stays.
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "to", "for", "with", "in", "on", "at", "of",
    "and", "or", "but", "is", "are", "was", "were", "be", "been",
    "by", "from",
})

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


def _strip_suffix(token: str) -> str:
    """Light suffix strip. Not a Porter stemmer — kept conservative to
    avoid collapsing distinct content words (e.g. ``draw`` vs ``drawer``).
    """
    # Order matters: -ing before -ed before -s. Each suffix only strips
    # when the stem is at least 3 chars to keep short words intact.
    for suffix in ("ing", "ed", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> frozenset[str]:
    """Tokenize ``text`` into a stopword-stripped, suffix-stripped set.

    Used identically at pack-load (to derive intent_verb_set per
    ConfrontationDef) and at validation time (to tokenize the narrator's
    declared intent string). Idempotent: tokenizing tokens never produces
    new tokens.
    """
    if not text or not text.strip():
        return frozenset()
    lowered = text.lower()
    raw = (t for t in _TOKEN_SPLIT.split(lowered) if t)
    return frozenset(_strip_suffix(t) for t in raw if t not in _STOPWORDS)
```

- [ ] **Step 4: Run tokenize tests, confirm pass**

Run: `cd sidequest-server && uv run pytest tests/agents/test_confrontation_intent_validator.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Write the failing pack-load derivation tests**

Append to `sidequest-server/tests/genre/test_pack_load_intent_schema.py`:

```python
def test_intent_verb_set_derived_from_label_and_beats() -> None:
    cdef = ConfrontationDef.model_validate({
        "type": "negotiation",
        "label": "Tense Negotiation",
        "category": "social",
        "player_metric": {"name": "leverage", "start": 0, "target": 10},
        "opponent_metric": {"name": "patience", "start": 0, "target": 10},
        "beats": [
            {"id": "haggle", "label": "Haggle the Price", "stat_check": "cha"},
            {"id": "offer", "label": "Make an Offer", "stat_check": "cha"},
        ],
    })
    # Derived at construction time and cached on the model.
    verbs = cdef.intent_verb_set
    assert "negotiat" in verbs  # 'negotiation' -> 'negotiat' after -ion? No: only -ing/-ed/-s strip.
    # With our suffix rules, 'negotiation' stays intact (no -ing/-ed/-s ending).
    assert "negotiation" in verbs
    assert "tense" in verbs
    assert "haggle" in verbs
    assert "offer" in verbs
    assert "price" in verbs
    # Stopwords dropped.
    assert "the" not in verbs
    assert "an" not in verbs


def test_intent_verb_set_unions_optional_intent_verbs() -> None:
    cdef = ConfrontationDef.model_validate({
        "type": "negotiation",
        "label": "Tense Negotiation",
        "category": "social",
        "player_metric": {"name": "leverage", "start": 0, "target": 10},
        "opponent_metric": {"name": "patience", "start": 0, "target": 10},
        "beats": [{"id": "haggle", "label": "Haggle", "stat_check": "cha"}],
        "intent_verbs": ["bargain", "barter", "deal"],
    })
    assert {"bargain", "barter", "deal"} <= cdef.intent_verb_set
    assert "haggle" in cdef.intent_verb_set  # label-derived still present


def test_intent_verb_set_empty_when_label_is_only_stopwords() -> None:
    # Pathological case: a label that produces no signal tokens.
    cdef = ConfrontationDef.model_validate({
        "type": "x",
        "label": "the a",
        "category": "social",
        "player_metric": {"name": "m", "start": 0, "target": 1},
        "opponent_metric": {"name": "m", "start": 0, "target": 1},
        "beats": [{"id": "b", "label": "to", "stat_check": "cha"}],
    })
    # 'x' from type is NOT included — only label + beats[].label + intent_verbs.
    # 'the', 'a', 'to' all stopwords.
    assert cdef.intent_verb_set == frozenset()


def test_pack_intent_verbs_by_type_accessor() -> None:
    """GenrePack.intent_verbs_by_type maps confrontation_type -> verb set."""
    from sidequest.genre.models.rules import RulesConfig

    rules = RulesConfig.model_validate({
        "confrontations": [
            {
                "type": "negotiation",
                "label": "Haggle",
                "category": "social",
                "player_metric": {"name": "a", "start": 0, "target": 1},
                "opponent_metric": {"name": "b", "start": 0, "target": 1},
                "beats": [{"id": "b1", "label": "Bargain", "stat_check": "cha"}],
            },
            {
                "type": "combat",
                "label": "Fight",
                "category": "combat",
                "player_metric": {"name": "a", "start": 0, "target": 1},
                "opponent_metric": {"name": "b", "start": 0, "target": 1},
                "beats": [{"id": "b1", "label": "Strike", "stat_check": "str"}],
            },
        ],
    })
    mapping = rules.intent_verbs_by_type
    assert "negotiation" in mapping
    assert "combat" in mapping
    assert "haggle" in mapping["negotiation"]
    assert "fight" in mapping["combat"]
    assert "strike" in mapping["combat"]
```

(`intent_verbs_by_type` is exposed on `RulesConfig` since that's the structure that owns `confrontations`. `GenrePack` already exposes `pack.rules.intent_verbs_by_type` through its `rules: RulesConfig` field — no separate accessor needed.)

- [ ] **Step 6: Run and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_load_intent_schema.py -v`
Expected: 4 new tests FAIL (no `intent_verb_set` attr; no `intent_verbs_by_type`).

- [ ] **Step 7: Add `intent_verb_set` cached field to `ConfrontationDef`**

Edit `sidequest-server/sidequest/genre/models/rules.py` `ConfrontationDef` class. After the new `on_intent_mismatch` field, add:

```python
    # Derived at construction time; excluded from serialization.
    intent_verb_set: frozenset[str] = Field(default_factory=frozenset, exclude=True, init=False)
```

In the existing `_validate` `@model_validator(mode="after")` method (around line 369), append the derivation right before `return self`:

```python
        # Derive intent vocabulary from label + every beat label, then union
        # with any explicitly declared intent_verbs. Tokenization is shared
        # with the validator (Task 3) — both use confrontation_intent_validator.tokenize.
        from sidequest.agents.confrontation_intent_validator import tokenize

        verbs: set[str] = set()
        verbs.update(tokenize(self.label))
        for beat in self.beats:
            verbs.update(tokenize(beat.label))
        if self.intent_verbs:
            for v in self.intent_verbs:
                verbs.update(tokenize(v))
        # Pydantic v2 frozen field assignment via object.__setattr__ —
        # the model isn't frozen but this field is init=False and we set
        # it post-construction.
        object.__setattr__(self, "intent_verb_set", frozenset(verbs))
```

- [ ] **Step 8: Add `intent_verbs_by_type` property to `RulesConfig`**

Same file `rules.py`, find the `class RulesConfig` (around line 580+). Add a property:

```python
    @property
    def intent_verbs_by_type(self) -> dict[str, frozenset[str]]:
        """Mapping of confrontation_type -> derived intent verb set.

        Consumed by sidequest.agents.confrontation_intent_validator.validate.
        Cached implicitly: ConfrontationDef.intent_verb_set is built once at
        model construction. Calling this property re-builds the dict but the
        underlying frozensets are shared.
        """
        return {cd.confrontation_type: cd.intent_verb_set for cd in self.confrontations}
```

- [ ] **Step 9: Verify the import does not create a cycle**

`confrontation_intent_validator.py` imports nothing from `sidequest.genre`. `rules.py` imports `tokenize` lazily inside the validator method. Run:

```bash
cd sidequest-server && uv run python -c "from sidequest.genre.models.rules import ConfrontationDef; print('OK')"
```
Expected: prints `OK`.

- [ ] **Step 10: Run tests and confirm pass**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_load_intent_schema.py tests/agents/test_confrontation_intent_validator.py -v`
Expected: 10 PASS (6 from Task 1 + 4 new).

- [ ] **Step 11: Verify all 7 production packs still load with empty intent_verbs (warning, not error)**

```bash
cd sidequest-server && uv run python -c "
from sidequest.genre.loader import load_genre_pack
from pathlib import Path
root = Path('../sidequest-content/genre_packs')
for pack_dir in sorted(p for p in root.iterdir() if (p / 'pack.yaml').exists()):
    pack = load_genre_pack(pack_dir)
    print(f'{pack_dir.name}: {len(pack.rules.confrontations)} confrontations, intent_verbs_by_type keys = {sorted(pack.rules.intent_verbs_by_type)}')
    for cdef in pack.rules.confrontations:
        verbs = cdef.intent_verb_set
        marker = ' [EMPTY]' if not verbs else ''
        print(f'  {cdef.confrontation_type}: {len(verbs)} verbs{marker}')
"
```
Expected: every pack loads. Note any `[EMPTY]` lines — those are pack-content debt to address in Task 10. Most label-derived sets should be ≥ 2 tokens because every confrontation has a meaningful label + ≥ 1 beat label.

- [ ] **Step 12: Commit**

```bash
git add sidequest-server/sidequest/agents/confrontation_intent_validator.py \
        sidequest-server/sidequest/genre/models/rules.py \
        sidequest-server/tests/agents/test_confrontation_intent_validator.py \
        sidequest-server/tests/genre/test_pack_load_intent_schema.py
git commit -m "feat(intent): derive intent_verb_set per ConfrontationDef at pack-load

Spec 2026-05-20 step 2: tokenize() helper + label/beat derivation +
RulesConfig.intent_verbs_by_type accessor. Pack-load and validation
share the same tokenization to guarantee byte-for-byte vocabulary parity."
```

---

## Task 3: Validator pure function

Add `ValidationResult` dataclass and `validate()` to `confrontation_intent_validator.py`. Pure, stateless, never raises.

**Files:**
- Modify: `sidequest-server/sidequest/agents/confrontation_intent_validator.py`
- Modify: `sidequest-server/tests/agents/test_confrontation_intent_validator.py`

- [ ] **Step 1: Write failing validator tests**

Append to `sidequest-server/tests/agents/test_confrontation_intent_validator.py`:

```python
from dataclasses import dataclass

import pytest

from sidequest.agents.confrontation_intent_validator import (
    ValidationResult,
    validate,
)


# --- Test doubles ---------------------------------------------------------


@dataclass
class _FakeActionRewrite:
    you: str = ""
    named: str = ""
    intent: str = ""


@dataclass
class _FakeConfrontationDef:
    confrontation_type: str
    on_intent_mismatch: str
    intent_verb_set: frozenset[str]


@dataclass
class _FakeRules:
    confrontations: list[_FakeConfrontationDef]

    @property
    def intent_verbs_by_type(self) -> dict[str, frozenset[str]]:
        return {c.confrontation_type: c.intent_verb_set for c in self.confrontations}


@dataclass
class _FakePack:
    rules: _FakeRules

    def confrontation_def(self, ctype: str) -> _FakeConfrontationDef | None:
        return next(
            (c for c in self.rules.confrontations if c.confrontation_type == ctype),
            None,
        )


def _pack(*defs: _FakeConfrontationDef) -> _FakePack:
    return _FakePack(rules=_FakeRules(confrontations=list(defs)))


# --- Tests ----------------------------------------------------------------


def test_validate_returns_none_when_action_rewrite_is_none() -> None:
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset({"haggle", "bargain"}))
    )
    assert validate(None, "negotiation", pack, active_encounter=False) is None


def test_validate_returns_none_when_intent_is_empty() -> None:
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset({"haggle"}))
    )
    assert (
        validate(_FakeActionRewrite(intent=""), None, pack, active_encounter=False)
        is None
    )
    assert (
        validate(_FakeActionRewrite(intent="   "), None, pack, active_encounter=False)
        is None
    )


def test_validate_returns_none_when_pack_is_none() -> None:
    assert (
        validate(
            _FakeActionRewrite(intent="haggle for horse"),
            None,
            None,
            active_encounter=False,
        )
        is None
    )


def test_validate_returns_none_when_active_encounter() -> None:
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset({"haggle"}))
    )
    result = validate(
        _FakeActionRewrite(intent="haggle for the horse"),
        None,
        pack,
        active_encounter=True,
    )
    assert result is None


def test_validate_returns_none_when_declared_matches_inferred() -> None:
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset({"haggle", "bargain"}))
    )
    result = validate(
        _FakeActionRewrite(intent="haggle for horse price"),
        "negotiation",
        pack,
        active_encounter=False,
    )
    assert result is None


def test_validate_returns_none_when_no_type_matches() -> None:
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset({"haggle"})),
        _FakeConfrontationDef("combat", "reprompt", frozenset({"strike", "fight"})),
    )
    result = validate(
        _FakeActionRewrite(intent="look around the room"),
        None,
        pack,
        active_encounter=False,
    )
    assert result is None


def test_validate_flags_single_mismatch() -> None:
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset({"haggle", "bargain"}))
    )
    result = validate(
        _FakeActionRewrite(intent="bargain hard for the horse"),
        None,
        pack,
        active_encounter=False,
    )
    assert result is not None
    assert result.matched_type == "negotiation"
    assert result.declared is None
    assert result.severity == "warn"
    assert "bargain" in result.matched_tokens


def test_validate_returns_severity_from_def() -> None:
    pack = _pack(
        _FakeConfrontationDef("combat", "reprompt", frozenset({"strike"}))
    )
    result = validate(
        _FakeActionRewrite(intent="strike the bandit"),
        None,
        pack,
        active_encounter=False,
    )
    assert result is not None
    assert result.severity == "reprompt"


def test_validate_multi_match_picks_most_token_overlap() -> None:
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset({"haggle"})),
        _FakeConfrontationDef("poker", "warn", frozenset({"haggle", "bluff", "raise"})),
    )
    # 'haggle' alone matches negotiation; 'haggle bluff' matches both, poker wins.
    result = validate(
        _FakeActionRewrite(intent="haggle and bluff"),
        None,
        pack,
        active_encounter=False,
    )
    assert result is not None
    assert result.matched_type == "poker"


def test_validate_multi_match_tie_broken_by_pack_order() -> None:
    pack = _pack(
        _FakeConfrontationDef("standoff", "reprompt", frozenset({"draw"})),
        _FakeConfrontationDef("duel", "reprompt", frozenset({"draw"})),
    )
    result = validate(
        _FakeActionRewrite(intent="draw"),
        None,
        pack,
        active_encounter=False,
    )
    assert result is not None
    assert result.matched_type == "standoff"  # first declared wins


def test_validate_unknown_declared_type_treated_as_none() -> None:
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset({"haggle"}))
    )
    result = validate(
        _FakeActionRewrite(intent="haggle for the horse"),
        "nonexistent_type",
        pack,
        active_encounter=False,
    )
    assert result is not None
    assert result.matched_type == "negotiation"


def test_validate_never_raises_on_malformed_input() -> None:
    # Anything goes — pure function must never raise.
    pack = _pack(
        _FakeConfrontationDef("negotiation", "warn", frozenset())  # empty verbs
    )
    # All of these should return None, not raise:
    assert validate(_FakeActionRewrite(intent="anything"), None, pack, active_encounter=False) is None
    assert validate(_FakeActionRewrite(), None, pack, active_encounter=False) is None
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/agents/test_confrontation_intent_validator.py -v`
Expected: 12 new tests FAIL — `validate` not exported.

- [ ] **Step 3: Implement `ValidationResult` and `validate`**

Append to `sidequest-server/sidequest/agents/confrontation_intent_validator.py`:

```python
from dataclasses import dataclass
from typing import Any, Literal, Protocol


Severity = Literal["warn", "soft_suggest", "reprompt"]


@dataclass(frozen=True)
class ValidationResult:
    """Result of a confrontation intent vs declared-type check.

    Always represents a flagged mismatch. The validator returns None when
    there is nothing to flag.
    """

    matched_type: str
    declared: str | None
    severity: Severity
    matched_tokens: tuple[str, ...]


class _ConfrontationDefLike(Protocol):
    confrontation_type: str
    on_intent_mismatch: str
    intent_verb_set: frozenset[str]


class _PackLike(Protocol):
    rules: Any  # has .confrontations: list[_ConfrontationDefLike]


def validate(
    action_rewrite: Any,
    declared_confrontation: str | None,
    pack: _PackLike | None,
    *,
    active_encounter: bool,
) -> ValidationResult | None:
    """Compare narrator-declared intent against declared confrontation.

    Returns ``None`` for any non-flag case (no intent, encounter active,
    declared matches inferred, nothing matches, pack missing). Never raises.
    """
    if pack is None:
        return None
    rules = getattr(pack, "rules", None)
    if rules is None:
        return None
    if active_encounter:
        return None
    if action_rewrite is None:
        return None
    intent = (getattr(action_rewrite, "intent", "") or "").strip()
    if not intent:
        return None

    intent_tokens = tokenize(intent)
    if not intent_tokens:
        return None

    defs = getattr(rules, "confrontations", None) or []
    # Score every type by token overlap; pack-declaration order is preserved.
    scored: list[tuple[int, int, _ConfrontationDefLike, frozenset[str]]] = []
    for idx, cdef in enumerate(defs):
        verbs = getattr(cdef, "intent_verb_set", None) or frozenset()
        if not verbs:
            continue
        overlap = intent_tokens & verbs
        if overlap:
            scored.append((len(overlap), idx, cdef, overlap))

    if not scored:
        return None

    # Sort: most overlap wins; ties broken by pack order (lower idx wins).
    scored.sort(key=lambda x: (-x[0], x[1]))
    best_count, _, best_cdef, best_overlap = scored[0]

    # If the narrator already declared the winning type, nothing to flag.
    if declared_confrontation == best_cdef.confrontation_type:
        return None

    return ValidationResult(
        matched_type=best_cdef.confrontation_type,
        declared=declared_confrontation,
        severity=best_cdef.on_intent_mismatch,  # type: ignore[arg-type]
        matched_tokens=tuple(sorted(best_overlap)),
    )
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `cd sidequest-server && uv run pytest tests/agents/test_confrontation_intent_validator.py -v`
Expected: 19 PASS (7 tokenize + 12 validate).

- [ ] **Step 5: Lint**

Run: `cd sidequest-server && uv run ruff check sidequest/agents/confrontation_intent_validator.py tests/agents/test_confrontation_intent_validator.py tests/genre/test_pack_load_intent_schema.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/agents/confrontation_intent_validator.py \
        sidequest-server/tests/agents/test_confrontation_intent_validator.py
git commit -m "feat(intent): validate(action_rewrite, declared, pack) pure function

Spec 2026-05-20 step 3: the inference site ADR-067 promised. Pure,
stateless, never raises. Multi-type tie-break by overlap count + pack
order. Returns None for every non-flag case (no intent, active
encounter, declared matches, no overlap)."
```

---

## Task 4: `GameSnapshot.next_turn_directives` field

Add the shared-world directive queue. Pure data field — consumer wiring lands in Task 7 (orchestrator prompt assembly).

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py:566` area (after `encounter:`)
- Test: `sidequest-server/tests/game/test_snapshot_next_turn_directives.py` (new)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_snapshot_next_turn_directives.py`:

```python
"""GameSnapshot.next_turn_directives — shared-world directive queue."""

from __future__ import annotations

from sidequest.game.session import GameSnapshot


def test_default_is_empty_list() -> None:
    snap = GameSnapshot()
    assert snap.next_turn_directives == []


def test_directives_round_trip_through_model_dump() -> None:
    snap = GameSnapshot(
        next_turn_directives=["Last turn suggested negotiation. Open it if true."]
    )
    dumped = snap.model_dump()
    assert dumped["next_turn_directives"] == [
        "Last turn suggested negotiation. Open it if true."
    ]
    restored = GameSnapshot.model_validate(dumped)
    assert restored.next_turn_directives == snap.next_turn_directives


def test_legacy_save_without_field_loads() -> None:
    """Old saves on disk don't have this field — model_validate must default it."""
    legacy_dump = {
        "genre_slug": "spaghetti_western",
        "world_slug": "dust_and_lead",
    }
    snap = GameSnapshot.model_validate(legacy_dump)
    assert snap.next_turn_directives == []
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/game/test_snapshot_next_turn_directives.py -v`
Expected: 2 FAIL (`next_turn_directives` attribute missing), 1 PASS (legacy save: `extra="ignore"` already handles missing fields).

- [ ] **Step 3: Add the field**

Edit `sidequest-server/sidequest/game/session.py` `class GameSnapshot`. After `encounter: StructuredEncounter | None = None` (around line 566), insert:

```python
    # Spec 2026-05-20 confrontation-intent-validator — directive queue
    # populated by the soft_suggest dispatch branch; consumed and cleared
    # by orchestrator prompt assembly at the start of the next turn.
    # Shared-world by design (a missed confrontation affects the whole
    # table). If per-player scoping becomes necessary, revisit per
    # ADR-037 / ADR-104.
    next_turn_directives: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd sidequest-server && uv run pytest tests/game/test_snapshot_next_turn_directives.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Run the full game + persistence suite**

Run: `cd sidequest-server && uv run pytest tests/game/ -v -x`
Expected: ALL PASS. Persistence must round-trip the new field (it does — model_dump/validate is standard pydantic).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/session.py \
        sidequest-server/tests/game/test_snapshot_next_turn_directives.py
git commit -m "feat(session): add GameSnapshot.next_turn_directives field

Spec 2026-05-20 step 4: shared-world directive queue for soft_suggest
dispatch. Default empty list keeps legacy saves loading via the
existing extra='ignore' migration."
```

---

## Task 5: `NarrationApplyOutcome.reprompt_request` + dispatch refactor

Replace the legacy lie-detector block in `narration_apply.py:2525-2549` with the validator dispatch. Add `reprompt_request: RepromptRequest | None` to `NarrationApplyOutcome`. Branch on severity: `warn` / `soft_suggest` apply normally; `reprompt` returns the request and does NOT apply yet.

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py` (lines 425-498, 2525-2549, NarrationApplyOutcome shape)
- Test: `sidequest-server/tests/server/test_narration_apply_intent_dispatch.py` (new)
- Test: `sidequest-server/tests/fixtures/intent_test_pack/` (new minimal fixture pack)

- [ ] **Step 1: Build the minimal fixture pack**

Create `sidequest-server/tests/fixtures/intent_test_pack/pack.yaml`:

```yaml
name: Intent Test Pack
slug: intent_test_pack
description: Minimal pack for confrontation_intent_validator dispatch tests.
version: 1
```

Create `sidequest-server/tests/fixtures/intent_test_pack/rules.yaml`:

```yaml
confrontations:
  - type: negotiation_warn
    label: Haggling Match
    category: social
    player_metric: { name: leverage, start: 0, target: 5 }
    opponent_metric: { name: patience, start: 0, target: 5 }
    beats:
      - id: b1
        label: Bargain
        stat_check: cha
    intent_verbs: [bargain, haggle, deal]
    on_intent_mismatch: warn

  - type: negotiation_soft
    label: Gentle Haggling Match
    category: social
    player_metric: { name: leverage, start: 0, target: 5 }
    opponent_metric: { name: patience, start: 0, target: 5 }
    beats:
      - id: b1
        label: Persuade
        stat_check: cha
    intent_verbs: [persuade, convince, sway]
    on_intent_mismatch: soft_suggest

  - type: combat_reprompt
    label: Combat
    category: combat
    player_metric: { name: hp, start: 0, target: 10 }
    opponent_metric: { name: hp, start: 0, target: 10 }
    beats:
      - id: b1
        label: Strike
        stat_check: str
    intent_verbs: [strike, attack, fight]
    on_intent_mismatch: reprompt
```

(Add only the minimum keys the pack loader requires. Adjust if the loader complains at runtime.)

- [ ] **Step 2: Write the failing dispatch tests**

Create `sidequest-server/tests/server/test_narration_apply_intent_dispatch.py`:

```python
"""Dispatch tests for narration_apply intent-validator branches.

Covers warn / soft_suggest / reprompt severities and the classified_intent
single-exit invariant.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sidequest.agents.orchestrator import ActionRewrite, NarrationTurnResult
from sidequest.game.session import GameSnapshot
from sidequest.genre.loader import load_genre_pack


_FIXTURE_PACK = Path(__file__).parents[1] / "fixtures" / "intent_test_pack"


@pytest.fixture
def pack():
    return load_genre_pack(_FIXTURE_PACK)


def _result(intent: str, confrontation: str | None) -> NarrationTurnResult:
    return NarrationTurnResult(
        narration="prose",
        action_rewrite=ActionRewrite(intent=intent),
        confrontation=confrontation,
        npcs_present=[],
    )


def _snapshot() -> GameSnapshot:
    return GameSnapshot(genre_slug="intent_test_pack", encounter=None)


def test_warn_severity_applies_normally_with_otel(pack, monkeypatch) -> None:
    from sidequest.server import narration_apply

    snap = _snapshot()
    result = _result(intent="bargain hard for the price", confrontation=None)
    room = MagicMock()

    spans: list[str] = []
    monkeypatch.setattr(
        narration_apply,
        "_emit_confrontation_intent_mismatch_span",
        lambda **kw: spans.append(kw.get("severity", "")),
    )

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=pack
    )

    assert spans == ["warn"]
    assert outcome.reprompt_request is None
    assert snap.next_turn_directives == []  # warn does not enqueue


def test_soft_suggest_severity_enqueues_directive(pack, monkeypatch) -> None:
    from sidequest.server import narration_apply

    snap = _snapshot()
    result = _result(intent="persuade the magistrate", confrontation=None)
    room = MagicMock()
    monkeypatch.setattr(
        narration_apply, "_emit_confrontation_intent_mismatch_span", lambda **kw: None
    )

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=pack
    )

    assert outcome.reprompt_request is None
    assert len(snap.next_turn_directives) == 1
    assert "negotiation_soft" in snap.next_turn_directives[0]


def test_reprompt_severity_returns_request_does_not_apply(pack, monkeypatch) -> None:
    from sidequest.server import narration_apply

    snap = _snapshot()
    result = _result(intent="strike the bandit dead", confrontation=None)
    room = MagicMock()
    monkeypatch.setattr(
        narration_apply, "_emit_confrontation_intent_mismatch_span", lambda **kw: None
    )

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=pack
    )

    assert outcome.reprompt_request is not None
    assert outcome.reprompt_request.matched_type == "combat_reprompt"
    assert "combat_reprompt" in outcome.reprompt_request.directive


def test_already_reprompted_degrades_reprompt_to_warn(pack, monkeypatch) -> None:
    from sidequest.server import narration_apply

    snap = _snapshot()
    result = _result(intent="strike again", confrontation=None)
    room = MagicMock()
    spans: list[str] = []
    monkeypatch.setattr(
        narration_apply,
        "_emit_confrontation_intent_mismatch_span",
        lambda **kw: spans.append(kw.get("severity", "")),
    )

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=pack, already_reprompted=True
    )

    assert outcome.reprompt_request is None  # degraded
    assert spans == ["warn"]  # severity force-downgraded


def test_active_encounter_short_circuits(pack, monkeypatch) -> None:
    """When an encounter is live the validator returns None, no dispatch fires."""
    from sidequest.server import narration_apply

    snap = _snapshot()
    snap.encounter = MagicMock(resolved=False)
    result = _result(intent="strike the bandit", confrontation=None)
    room = MagicMock()
    spans: list[str] = []
    monkeypatch.setattr(
        narration_apply,
        "_emit_confrontation_intent_mismatch_span",
        lambda **kw: spans.append(kw.get("severity", "")),
    )

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=pack
    )

    assert spans == []
    assert outcome.reprompt_request is None


def test_classified_intent_populated_on_no_mismatch(pack, monkeypatch) -> None:
    from sidequest.server import narration_apply

    snap = _snapshot()
    result = _result(intent="look around quietly", confrontation=None)
    room = MagicMock()
    monkeypatch.setattr(
        narration_apply, "_emit_confrontation_intent_mismatch_span", lambda **kw: None
    )

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=pack
    )

    assert outcome.classified_intent == "look around quietly"


def test_classified_intent_uses_matched_type_on_mismatch(pack, monkeypatch) -> None:
    from sidequest.server import narration_apply

    snap = _snapshot()
    result = _result(intent="bargain hard", confrontation=None)
    room = MagicMock()
    monkeypatch.setattr(
        narration_apply, "_emit_confrontation_intent_mismatch_span", lambda **kw: None
    )

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=pack
    )

    assert outcome.classified_intent == "negotiation_warn"


def test_classified_intent_unspecified_when_intent_missing(pack, monkeypatch) -> None:
    from sidequest.server import narration_apply

    snap = _snapshot()
    result = _result(intent="", confrontation=None)
    room = MagicMock()

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=pack
    )

    assert outcome.classified_intent == "unspecified"
    assert outcome.classified_intent != "unknown"
```

- [ ] **Step 3: Run and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_narration_apply_intent_dispatch.py -v`
Expected: all FAIL — `NarrationApplyOutcome.reprompt_request` doesn't exist, `_emit_confrontation_intent_mismatch_span` doesn't exist, `_apply_narration_result_to_snapshot` doesn't accept `already_reprompted=`, `classified_intent` not on outcome.

- [ ] **Step 4: Read `NarrationApplyOutcome` current shape**

Run: `grep -n "class NarrationApplyOutcome\|@dataclass" sidequest-server/sidequest/server/narration_apply.py | head -10`

Inspect the dataclass to know what fields exist before adding.

- [ ] **Step 5: Add `RepromptRequest` and extend `NarrationApplyOutcome`**

Edit `sidequest-server/sidequest/server/narration_apply.py`. Near the top with the other dataclasses, add:

```python
@dataclass(frozen=True)
class RepromptRequest:
    """Returned by the apply step when the validator severity is 'reprompt'.

    Carries the directive string the orchestrator should inject into the
    second narrator call's recency zone. Spec 2026-05-20.
    """
    matched_type: str
    declared: str | None
    directive: str
```

Extend `NarrationApplyOutcome` (find the existing dataclass) with:

```python
    reprompt_request: RepromptRequest | None = None
    classified_intent: str = "unspecified"
```

- [ ] **Step 6: Add the OTEL emit helper stub**

Just below the dataclasses, add a small wrapper that the real telemetry span (Task 8) will replace. For now it must exist so the dispatch logic can call it:

```python
def _emit_confrontation_intent_mismatch_span(
    *,
    matched_type: str,
    declared: str | None,
    severity: str,
    matched_tokens: tuple[str, ...],
    reprompt_attempted: bool = False,
    outcome: str | None = None,
) -> None:
    """OTEL span emission for confrontation.intent_mismatch.

    Stubbed here; the canonical implementation lands in
    sidequest.telemetry.spans (Task 8). Importing from there now would
    create a temporary forward reference. Keep this in sync until Task 8
    deletes this stub and replaces with the real span import.
    """
    from sidequest.telemetry.spans import confrontation_intent_mismatch_span

    with confrontation_intent_mismatch_span(
        matched_type=matched_type,
        declared_type=declared,
        severity=severity,
        matched_tokens=list(matched_tokens),
        reprompt_attempted=reprompt_attempted,
        outcome=outcome,
    ):
        pass
```

(If Task 8 hasn't been done yet, this import will fail at runtime — the test monkeypatches it. The real span lands in Task 8 and removes the indirection.)

- [ ] **Step 7: Replace the lie-detector block with validator dispatch**

In `narration_apply.py`, find `_apply_narration_result_to_snapshot` (around line 1696). Change the signature to accept `already_reprompted: bool = False`:

```python
def _apply_narration_result_to_snapshot(
    snapshot: GameSnapshot,
    result: object,
    player_name: str,
    *,
    room: SessionRoom,
    pack: GenrePack | None = None,
    dice_failed: bool | None = None,
    dice_actor: str | None = None,
    from_explicit_action: bool = False,
    opposed_player_d20: int | None = None,
    opposed_player_beat_id: str | None = None,
    opposed_player_actor: str | None = None,
    acting_character_name: str | None = None,
    already_reprompted: bool = False,
) -> NarrationApplyOutcome:
```

Find the legacy block starting at `narration_apply.py:2525` — the comment beginning "Pingpong 2026-05-03 [BUG]" through the `if matched_triggers:` block ending at `:2549`. REPLACE the entire block (`if not result.confrontation and ...:` through the `logger.warning(...)` close) with:

```python
        # Spec 2026-05-20 confrontation-intent-validator — single mechanism.
        # ActionRewrite.intent is the authoritative signal. ADR-067's
        # inference site, finally wired.
        from sidequest.agents.confrontation_intent_validator import validate as _validate_intent

        _mismatch = _validate_intent(
            getattr(result, "action_rewrite", None),
            result.confrontation,
            pack,
            active_encounter=snapshot.encounter is not None and not snapshot.encounter.resolved,
        )

        _classified_intent_value = (
            (getattr(getattr(result, "action_rewrite", None), "intent", "") or "").strip()
            or "unspecified"
        )
        _reprompt_request: RepromptRequest | None = None

        if _mismatch is not None:
            _effective_severity = _mismatch.severity
            if already_reprompted and _effective_severity == "reprompt":
                _effective_severity = "warn"  # bounded retry, fall through

            _classified_intent_value = _mismatch.matched_type
            _outcome_label = None
            if already_reprompted:
                _outcome_label = "fall_through" if _mismatch.severity == "reprompt" else None

            _emit_confrontation_intent_mismatch_span(
                matched_type=_mismatch.matched_type,
                declared=_mismatch.declared,
                severity=_effective_severity,
                matched_tokens=_mismatch.matched_tokens,
                reprompt_attempted=already_reprompted,
                outcome=_outcome_label,
            )

            if _effective_severity == "soft_suggest":
                snapshot.next_turn_directives.append(
                    f"Last turn's intent suggested {_mismatch.matched_type}. "
                    f"If this scene is in fact a {_mismatch.matched_type}, open the "
                    f"encounter on this turn."
                )
            elif _effective_severity == "reprompt":
                _reprompt_request = RepromptRequest(
                    matched_type=_mismatch.matched_type,
                    declared=_mismatch.declared,
                    directive=(
                        f"Previous attempt described a {_mismatch.matched_type} "
                        f"(intent: '{(getattr(getattr(result, 'action_rewrite', None), 'intent', '') or '').strip()}') "
                        f"but did not open one. Either set confrontation={_mismatch.matched_type} "
                        f"or rewrite without {_mismatch.matched_type}-shaped language."
                    ),
                )
```

At the end of `_apply_narration_result_to_snapshot`, wherever it constructs the return value, populate the two new fields:

```python
        return NarrationApplyOutcome(
            ...existing fields...,
            reprompt_request=_reprompt_request,
            classified_intent=_classified_intent_value,
        )
```

(If `_reprompt_request` was set, the function should `return` BEFORE applying narration. Add an early-return branch right after the dispatch block:

```python
        if _reprompt_request is not None:
            return NarrationApplyOutcome(
                ...minimal-shape outcome...,
                reprompt_request=_reprompt_request,
                classified_intent=_classified_intent_value,
            )
```

Inspect the actual `NarrationApplyOutcome` constructor to know which fields default sensibly for the "did not apply" case. If most fields are already `Optional[...] = None`, the early return is straightforward.)

- [ ] **Step 8: Run dispatch tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_narration_apply_intent_dispatch.py -v`
Expected: 8 PASS. Fix concrete issues iteratively — if a test fails, read the failure, fix the code, re-run; do not work around tests.

- [ ] **Step 9: Run the broader narration_apply suite to catch regressions**

Run: `cd sidequest-server && uv run pytest tests/server/ -k "narration_apply or confrontation" -v`
Expected: existing tests still pass. Some tests that exercised `_scan_for_confrontation_trigger_keywords` directly may now fail — those are addressed in Task 9 (legacy deletion).

- [ ] **Step 10: Commit**

```bash
git add sidequest-server/sidequest/server/narration_apply.py \
        sidequest-server/tests/server/test_narration_apply_intent_dispatch.py \
        sidequest-server/tests/fixtures/intent_test_pack/
git commit -m "feat(narration): replace prose lie-detector with intent validator

Spec 2026-05-20 step 5: ActionRewrite.intent + confrontation_intent_validator
become the single mechanism. NarrationApplyOutcome gains reprompt_request
and classified_intent. already_reprompted=True degrades reprompt to warn
for bounded retry."
```

---

## Task 6: Remove `classified_intent="unknown"` hardcodes

Two literal `"unknown"` hardcodes in `websocket_session_handler.py`. Replace with the value from `NarrationApplyOutcome.classified_intent` (or fall back to `"unspecified"` when no outcome — e.g. degraded turns).

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py:4696`, `:4819`
- Test: `sidequest-server/tests/server/test_intent_classified_invariant.py` (new)

- [ ] **Step 1: Write the failing invariant test**

Create `sidequest-server/tests/server/test_intent_classified_invariant.py`:

```python
"""Source-grep guard: no production code path may set classified_intent='unknown'.

This is a static check because exercising every WebSocket path in a unit test
is infeasible. The grep is narrow: production source only (tests/ excluded).
"""

from __future__ import annotations

import subprocess
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[2] / "sidequest"


def test_no_classified_intent_unknown_in_production_source() -> None:
    """No production code path may write `classified_intent="unknown"`.

    Spec 2026-05-20: the literal 'unknown' was a stub. Real values:
    - action_rewrite.intent verbatim (happy path)
    - matched_type (mismatch path)
    - 'unspecified' (intent omitted by narrator)
    """
    result = subprocess.run(
        ["grep", "-rn", '"unknown"', str(SERVER_ROOT)],
        capture_output=True,
        text=True,
    )
    offenders = [
        line for line in result.stdout.splitlines()
        if "classified_intent" in line
    ]
    assert offenders == [], (
        f"Production code still hardcodes classified_intent='unknown': {offenders}"
    )
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_intent_classified_invariant.py -v`
Expected: FAIL — `websocket_session_handler.py:4696` and `:4819` are flagged.

- [ ] **Step 3: Read the two call sites**

```bash
cd sidequest-server && sed -n '4685,4700p' sidequest/server/websocket_session_handler.py
sed -n '4810,4825p' sidequest/server/websocket_session_handler.py
```

Find the surrounding `result` / `applied_outcome` variable name at each site.

- [ ] **Step 4: Replace the first hardcode (`:4696`)**

In `sidequest-server/sidequest/server/websocket_session_handler.py`, change:

```python
                            classified_intent="unknown",  # TODO: tighten when LocalDM exposes intent
```

to:

```python
                            classified_intent=(
                                getattr(applied_outcome, "classified_intent", None)
                                or (getattr(result.action_rewrite, "intent", "") if result.action_rewrite else "").strip()
                                or "unspecified"
                            ),
```

(Confirm the variable name `applied_outcome` matches the surrounding code; substitute the actual local name if different.)

- [ ] **Step 5: Replace the second hardcode (`:4819`)**

Apply the same change at the second call site. If `applied_outcome` is not in scope at `:4819` (e.g. degraded-turn path), fall back to the intent-from-result chain only:

```python
                        classified_intent=(
                            (getattr(getattr(result, "action_rewrite", None), "intent", "") or "").strip()
                            or "unspecified"
                        ),
```

- [ ] **Step 6: Run the invariant guard, confirm pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_intent_classified_invariant.py -v`
Expected: PASS.

- [ ] **Step 7: Run the broader handler suite to catch regressions**

Run: `cd sidequest-server && uv run pytest tests/server/ -v -x`
Expected: existing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/tests/server/test_intent_classified_invariant.py
git commit -m "refactor(telemetry): remove classified_intent='unknown' hardcodes

Spec 2026-05-20 step 6: populate from applied_outcome.classified_intent
(or action_rewrite.intent / 'unspecified' fallback). Pinned by a grep
guard so the literal can't sneak back in."
```

---

## Task 7: Orchestrator one-iteration reprompt loop + directive consumption

Wrap `run_narration_turn` with a single-iteration retry triggered by `NarrationApplyOutcome.reprompt_request`. Inject the directive into the second call. Also wire prompt assembly to consume + clear `snapshot.next_turn_directives` at the start of every turn.

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py` (run_narration_turn area + prompt assembly area ~1850-1910)
- Modify: `sidequest-server/sidequest/agents/narrator.py` / `_run_narration_turn_sdk` to accept `extra_directive`
- Test: `sidequest-server/tests/agents/test_orchestrator_reprompt_loop.py` (new)

- [ ] **Step 1: Write the failing reprompt-loop tests**

Create `sidequest-server/tests/agents/test_orchestrator_reprompt_loop.py`:

```python
"""Orchestrator one-iteration reprompt loop tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_reprompt_request_triggers_second_narrator_call() -> None:
    """When apply returns reprompt_request, narrator is called again with extra_directive."""
    from sidequest.agents.orchestrator import Orchestrator  # adjust import to actual entry

    # Two narrator calls: first returns mismatch, second returns clean.
    narrator = AsyncMock()
    narrator.run_narration_turn.side_effect = [
        MagicMock(action_rewrite=MagicMock(intent="strike"), confrontation=None),
        MagicMock(action_rewrite=MagicMock(intent="strike"), confrontation="combat_reprompt"),
    ]
    # Wiring through the orchestrator's reprompt wrapper — exact constructor
    # signature TBD by reading orchestrator.py. The test asserts that the
    # second narrator call receives extra_directive=<directive string>.
    # Concrete shape: replace Orchestrator(...) with the real entry point.
    ...


@pytest.mark.asyncio
async def test_only_one_retry_then_fall_through() -> None:
    """Second call still flags mismatch → no third call, applies second narration."""
    ...


@pytest.mark.asyncio
async def test_second_call_failure_applies_first_attempt() -> None:
    """Narrator second call raises → apply first attempt's narration."""
    ...


@pytest.mark.asyncio
async def test_no_reprompt_when_apply_returns_no_request() -> None:
    """Happy path: warn/soft_suggest/no-mismatch never triggers second call."""
    ...


@pytest.mark.asyncio
async def test_directives_consumed_and_cleared_in_prompt_assembly() -> None:
    """snapshot.next_turn_directives is rendered into recency zone and cleared."""
    from sidequest.game.session import GameSnapshot
    from sidequest.agents.orchestrator import _consume_next_turn_directives

    snap = GameSnapshot(next_turn_directives=["Open the negotiation."])
    rendered = _consume_next_turn_directives(snap)
    assert "Open the negotiation." in rendered
    assert snap.next_turn_directives == []
```

The first four tests are stubs — flesh out the concrete narrator-stub plumbing once you read the orchestrator's actual entry point signature in Step 2. The fifth test is concrete and drives the directive-consumption helper.

- [ ] **Step 2: Identify orchestrator entry point + narrator-call shape**

```bash
cd sidequest-server && grep -n "def run_narration_turn\|class .*Orchestrator\|async def _run_narration_turn_sdk" sidequest/agents/orchestrator.py | head -10
```

Read the surrounding 40 lines at the chosen wrapper site. The wrapper needs:
1. A first call: `result = await self.run_narration_turn(action, context)`.
2. The apply step that returns `NarrationApplyOutcome` (currently happens in the *server* layer at `websocket_session_handler` or `narration_apply`). Determine where the wrapper lives — it MUST sit between "narrator produced result" and "result is applied" in the call chain. Probably easiest: wrap at the server's WebSocket call site (the one in `websocket_session_handler.py` that currently calls `_apply_narration_result_to_snapshot`), not inside `orchestrator.run_narration_turn`. Adjust the file scope accordingly.

If the wrapper belongs at the WebSocket level, the file modified is `sidequest-server/sidequest/server/websocket_session_handler.py`, not `orchestrator.py`. Decide based on what you read.

- [ ] **Step 3: Implement `_consume_next_turn_directives` helper**

Add to `sidequest-server/sidequest/agents/orchestrator.py` (or a small adjacent module — wherever prompt assembly lives):

```python
def _consume_next_turn_directives(snapshot: GameSnapshot) -> str:
    """Render snapshot.next_turn_directives into a recency-zone string and clear.

    Returns empty string when the queue is empty. Spec 2026-05-20:
    consumed once per turn at prompt-assembly time.
    """
    if not snapshot.next_turn_directives:
        return ""
    rendered = "\n".join(f"- {d}" for d in snapshot.next_turn_directives)
    snapshot.next_turn_directives.clear()
    return rendered
```

Wire it into the prompt-section assembly. In `orchestrator.py`, find the recency-zone registration block near line 1850-1910 (where `confrontation_trigger_constraint` is registered today). Add a section registration BEFORE the existing guardrails block:

```python
        # Spec 2026-05-20 — soft_suggest directives from last turn's
        # confrontation-intent dispatch. Cleared as it's consumed so the
        # queue never persists across turns.
        directive_text = _consume_next_turn_directives(snapshot)
        if directive_text:
            registry.register_section(
                agent_name,
                PromptSection.new(
                    "intent_directives",
                    f"GM-NOTE: One or more inferred intent suggestions from "
                    f"the previous turn:\n{directive_text}",
                    AttentionZone.Recency,
                    SectionCategory.Guardrail,
                ),
            )
```

(Verify `snapshot` is in scope at this point; if not, pass it through from the calling site.)

- [ ] **Step 4: Implement the reprompt wrapper**

The cleanest place is the WebSocket dispatch site that today calls `_apply_narration_result_to_snapshot`. Locate it (likely near `websocket_session_handler.py:4696`-ish). Wrap:

```python
        # Spec 2026-05-20 — one-iteration reprompt loop. The validator may
        # return RepromptRequest when severity=reprompt; we give the narrator
        # exactly one chance to restructure the turn.
        applied_outcome = _apply_narration_result_to_snapshot(
            snapshot, result, player_name, room=room, pack=pack, ...other-kwargs...
        )

        if applied_outcome.reprompt_request is not None:
            try:
                result = await self.orchestrator.run_narration_turn(
                    action, context, extra_directive=applied_outcome.reprompt_request.directive
                )
                applied_outcome = _apply_narration_result_to_snapshot(
                    snapshot, result, player_name,
                    room=room, pack=pack,
                    already_reprompted=True,
                    ...other-kwargs...
                )
            except Exception:
                logger.exception("confrontation.intent_mismatch_reprompt_failed")
                from sidequest.telemetry.spans import (
                    confrontation_intent_mismatch_reprompt_failed_span,
                )
                with confrontation_intent_mismatch_reprompt_failed_span(
                    matched_type=applied_outcome.reprompt_request.matched_type
                ):
                    pass
                # Apply the FIRST attempt by re-running apply without the request.
                # We saved `result` to the first attempt before reassigning above
                # — restore it (use a local variable to remember).
                ...
```

Refine: use two locals (`first_result`, `result`) so the fall-through clearly applies the first attempt's narration. Pseudocode:

```python
        first_result = result
        applied_outcome = _apply_narration_result_to_snapshot(snapshot, first_result, ...)

        if applied_outcome.reprompt_request is not None:
            directive = applied_outcome.reprompt_request.directive
            matched = applied_outcome.reprompt_request.matched_type
            try:
                second_result = await self.orchestrator.run_narration_turn(
                    action, context, extra_directive=directive
                )
                applied_outcome = _apply_narration_result_to_snapshot(
                    snapshot, second_result, ..., already_reprompted=True
                )
                result = second_result
            except Exception:
                logger.exception("confrontation.intent_mismatch_reprompt_failed matched_type=%s", matched)
                from sidequest.telemetry.spans import (
                    confrontation_intent_mismatch_reprompt_failed_span,
                )
                with confrontation_intent_mismatch_reprompt_failed_span(matched_type=matched):
                    pass
                applied_outcome = _apply_narration_result_to_snapshot(
                    snapshot, first_result, ..., already_reprompted=True
                )
                result = first_result
```

- [ ] **Step 5: Thread `extra_directive` through narrator entry points**

In `sidequest-server/sidequest/agents/orchestrator.py:2244` (`run_narration_turn`), add the parameter:

```python
    async def run_narration_turn(
        self,
        action: str,
        context: TurnContext,
        *,
        room: object | None = None,
        extra_directive: str | None = None,
    ) -> NarrationTurnResult:
```

Propagate to `_run_narration_turn_sdk`, `_run_narration_turn_streaming`, and `_run_narration_turn_synchronous`. In each, when `extra_directive` is set, append it to the recency zone of the prompt (the simplest channel — re-use the same `PromptSection` registration shape used for `intent_directives` above). If the streaming and SDK paths build prompts via a shared helper, add the parameter there once.

- [ ] **Step 6: Flesh out the stub tests with real shape**

Now that the orchestrator entry shape is known, complete the four stub tests in `test_orchestrator_reprompt_loop.py` with concrete narrator AsyncMocks and orchestrator construction. Verify each:
1. `narrator.run_narration_turn.call_count == 2` and `call_args_list[1].kwargs["extra_directive"] == directive`.
2. `narrator.run_narration_turn.call_count == 2` (no third call ever) — second mismatch falls through.
3. `narrator.run_narration_turn.call_count == 2`, second raises, applied narration is the first result.
4. `narrator.run_narration_turn.call_count == 1` when first apply has no reprompt request.

- [ ] **Step 7: Run reprompt-loop tests**

Run: `cd sidequest-server && uv run pytest tests/agents/test_orchestrator_reprompt_loop.py -v`
Expected: 5 PASS.

- [ ] **Step 8: Run server + agents suites for regression sweep**

Run: `cd sidequest-server && uv run pytest tests/agents/ tests/server/ -v -x`
Expected: ALL PASS except pre-existing legacy-regex tests (cleared in Task 9).

- [ ] **Step 9: Commit**

```bash
git add sidequest-server/sidequest/agents/orchestrator.py \
        sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/tests/agents/test_orchestrator_reprompt_loop.py
git commit -m "feat(orchestrator): one-iteration reprompt loop + directive recency injection

Spec 2026-05-20 step 7: NarrationApplyOutcome.reprompt_request triggers
exactly one retry with extra_directive in the recency zone. Bounded to
one attempt; fall-through degrades to warn. snapshot.next_turn_directives
consumed + cleared in prompt assembly so soft_suggest cues land on N+1
only."
```

---

## Task 8: Telemetry spans

Add the three new spans to `sidequest/telemetry/spans.py`. Replace the temporary `_emit_confrontation_intent_mismatch_span` helper in `narration_apply.py` with a direct import.

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py` (or `spans/` package — check structure)
- Modify: `sidequest-server/sidequest/server/narration_apply.py` (replace helper)
- Test: `sidequest-server/tests/telemetry/test_confrontation_intent_spans.py` (new)

- [ ] **Step 1: Inspect existing span module structure**

```bash
cd sidequest-server && ls sidequest/telemetry/spans/ 2>/dev/null || head -50 sidequest/telemetry/spans.py
grep -n "encounter_resolved_span\|@contextmanager" sidequest/telemetry/spans*.py sidequest/telemetry/spans/*.py 2>/dev/null | head -10
```

Pattern-match an existing span helper to keep the style consistent.

- [ ] **Step 2: Write the failing span tests**

Create `sidequest-server/tests/telemetry/test_confrontation_intent_spans.py`:

```python
"""OTEL span tests for confrontation.intent_mismatch family."""

from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry import trace


def _setup_exporter() -> InMemorySpanExporter:
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def test_confrontation_intent_mismatch_span_attributes() -> None:
    from sidequest.telemetry.spans import confrontation_intent_mismatch_span

    exporter = _setup_exporter()
    with confrontation_intent_mismatch_span(
        matched_type="negotiation",
        declared_type=None,
        severity="warn",
        matched_tokens=["bargain", "haggle"],
        reprompt_attempted=False,
    ):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "confrontation.intent_mismatch"
    attrs = spans[0].attributes
    assert attrs["matched_type"] == "negotiation"
    assert attrs["severity"] == "warn"
    assert attrs["reprompt_attempted"] is False


def test_confrontation_intent_mismatch_resolved_span() -> None:
    from sidequest.telemetry.spans import confrontation_intent_mismatch_resolved_span

    exporter = _setup_exporter()
    with confrontation_intent_mismatch_resolved_span(matched_type="combat"):
        pass

    spans = exporter.get_finished_spans()
    assert any(s.name == "confrontation.intent_mismatch_resolved" for s in spans)


def test_confrontation_intent_mismatch_reprompt_failed_span() -> None:
    from sidequest.telemetry.spans import (
        confrontation_intent_mismatch_reprompt_failed_span,
    )

    exporter = _setup_exporter()
    with confrontation_intent_mismatch_reprompt_failed_span(matched_type="combat"):
        pass

    spans = exporter.get_finished_spans()
    assert any(s.name == "confrontation.intent_mismatch_reprompt_failed" for s in spans)
```

- [ ] **Step 3: Run and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_confrontation_intent_spans.py -v`
Expected: 3 FAIL (helpers don't exist).

- [ ] **Step 4: Add the spans**

Append to `sidequest-server/sidequest/telemetry/spans.py` (or the right sibling file if the package is split):

```python
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def confrontation_intent_mismatch_span(
    *,
    matched_type: str,
    declared_type: str | None,
    severity: str,
    matched_tokens: list[str],
    reprompt_attempted: bool = False,
    outcome: str | None = None,
) -> Iterator[None]:
    """Spec 2026-05-20: emitted when validate() returns a ValidationResult."""
    tracer = trace.get_tracer("sidequest.confrontation.intent")
    with tracer.start_as_current_span("confrontation.intent_mismatch") as span:
        span.set_attribute("matched_type", matched_type)
        span.set_attribute("declared_type", declared_type or "")
        span.set_attribute("severity", severity)
        span.set_attribute("matched_tokens", ",".join(matched_tokens))
        span.set_attribute("reprompt_attempted", reprompt_attempted)
        if outcome is not None:
            span.set_attribute("outcome", outcome)
        yield


@contextmanager
def confrontation_intent_mismatch_resolved_span(*, matched_type: str) -> Iterator[None]:
    """Emitted when the reprompt loop's second call resolves the mismatch."""
    tracer = trace.get_tracer("sidequest.confrontation.intent")
    with tracer.start_as_current_span("confrontation.intent_mismatch_resolved") as span:
        span.set_attribute("matched_type", matched_type)
        yield


@contextmanager
def confrontation_intent_mismatch_reprompt_failed_span(*, matched_type: str) -> Iterator[None]:
    """Emitted when the narrator's second call raises during reprompt."""
    tracer = trace.get_tracer("sidequest.confrontation.intent")
    with tracer.start_as_current_span("confrontation.intent_mismatch_reprompt_failed") as span:
        span.set_attribute("matched_type", matched_type)
        yield
```

(Ensure `trace` is already imported at the top of the file; the existing spans will tell you the import style.)

- [ ] **Step 5: Delete the temporary helper in narration_apply.py**

In `sidequest-server/sidequest/server/narration_apply.py`, delete the `_emit_confrontation_intent_mismatch_span` helper added in Task 5 step 6, and change the dispatch block's call sites to import + call the canonical span directly:

```python
        from sidequest.telemetry.spans import confrontation_intent_mismatch_span

        ...
        with confrontation_intent_mismatch_span(
            matched_type=_mismatch.matched_type,
            declared_type=_mismatch.declared,
            severity=_effective_severity,
            matched_tokens=list(_mismatch.matched_tokens),
            reprompt_attempted=already_reprompted,
            outcome=_outcome_label,
        ):
            pass
```

Wire the orchestrator's reprompt-success path (in `websocket_session_handler.py` from Task 7) to emit `confrontation_intent_mismatch_resolved_span(matched_type=...)` when the second `_apply_narration_result_to_snapshot` returns `applied_outcome.reprompt_request is None`.

- [ ] **Step 6: Add `mismatch_resolved` emission on success retry**

In `websocket_session_handler.py` reprompt branch from Task 7, after the second apply call:

```python
                applied_outcome = _apply_narration_result_to_snapshot(
                    snapshot, second_result, ..., already_reprompted=True
                )
                if applied_outcome.reprompt_request is None:
                    from sidequest.telemetry.spans import (
                        confrontation_intent_mismatch_resolved_span,
                    )
                    with confrontation_intent_mismatch_resolved_span(matched_type=matched):
                        pass
                result = second_result
```

- [ ] **Step 7: Update the dispatch tests to assert real span names**

Edit `test_narration_apply_intent_dispatch.py` — remove the monkeypatch of `_emit_confrontation_intent_mismatch_span` (it's gone). Use an in-memory exporter as in the telemetry tests, OR monkeypatch the real `confrontation_intent_mismatch_span` to a no-op tracker.

- [ ] **Step 8: Run all impacted suites**

Run: `cd sidequest-server && uv run pytest tests/telemetry/ tests/server/test_narration_apply_intent_dispatch.py tests/agents/test_orchestrator_reprompt_loop.py -v`
Expected: ALL PASS.

- [ ] **Step 9: GM panel / dashboard surface**

In `sidequest-server/sidequest/server/dashboard.py`, find where existing confrontation watcher events are rendered (search for `confrontation_trigger_constraint` or `state_transition`). Add rendering for the three new span names so they show in the GM panel. Pattern-match the existing rendering style — keep it minimal, no new tab unless one obviously fits.

- [ ] **Step 10: Run server tests and lint**

```bash
cd sidequest-server && uv run pytest tests/ -v -x
uv run ruff check .
```
Expected: all pass.

- [ ] **Step 11: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans.py \
        sidequest-server/sidequest/server/narration_apply.py \
        sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/sidequest/server/dashboard.py \
        sidequest-server/tests/telemetry/test_confrontation_intent_spans.py \
        sidequest-server/tests/server/test_narration_apply_intent_dispatch.py
git commit -m "feat(otel): confrontation.intent_mismatch span family + GM panel surface

Spec 2026-05-20 step 8: three spans (intent_mismatch, _resolved,
_reprompt_failed). Dispatch tests now assert real span emission via
in-memory exporter. Dashboard renders the new event names."
```

---

## Task 9: Delete the legacy lie-detector

Removes `_CONFRONTATION_TRIGGER_PATTERNS`, `_scan_for_confrontation_trigger_keywords`, all tests that exercise them. Adds a grep guard so the symbols can't return.

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py:425-498`
- Delete: any test files exercising the legacy symbols (grep below)
- Create: `sidequest-server/tests/server/test_legacy_trigger_patterns_removed.py`

- [ ] **Step 1: Locate tests that reference the legacy symbols**

```bash
cd sidequest-server && grep -rln "_CONFRONTATION_TRIGGER_PATTERNS\|_scan_for_confrontation_trigger_keywords\|skipped_with_trigger_keywords" tests/
```

Note each file. Tests exclusively about the legacy scanner go entirely; tests that incidentally reference it lose only those assertions.

- [ ] **Step 2: Write the grep guard test**

Create `sidequest-server/tests/server/test_legacy_trigger_patterns_removed.py`:

```python
"""Spec 2026-05-20: one mechanism. The legacy prose-regex scanner is dead.

Source-grep guard so the deleted symbols can't sneak back in via revert
or copy-paste.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[2] / "sidequest"


def test_no_confrontation_trigger_patterns_in_source() -> None:
    result = subprocess.run(
        ["grep", "-rn", "_CONFRONTATION_TRIGGER_PATTERNS", str(SERVER_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.stdout == "", f"Legacy symbol resurrected: {result.stdout}"


def test_no_scan_for_confrontation_trigger_keywords_in_source() -> None:
    result = subprocess.run(
        ["grep", "-rn", "_scan_for_confrontation_trigger_keywords", str(SERVER_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.stdout == "", f"Legacy symbol resurrected: {result.stdout}"


def test_no_skipped_with_trigger_keywords_watcher_event() -> None:
    result = subprocess.run(
        ["grep", "-rn", "skipped_with_trigger_keywords", str(SERVER_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.stdout == "", f"Legacy watcher event resurrected: {result.stdout}"
```

- [ ] **Step 3: Run and confirm failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_legacy_trigger_patterns_removed.py -v`
Expected: 3 FAIL — symbols still present.

- [ ] **Step 4: Delete the legacy block in narration_apply.py**

Open `sidequest-server/sidequest/server/narration_apply.py`. Delete:
- Lines 425-498 (the `_CONFRONTATION_TRIGGER_PATTERNS` tuple and `_scan_for_confrontation_trigger_keywords` function, plus the comment block above).
- The remnant of the lie-detector block in `_apply_narration_result_to_snapshot` at the old `:2525-2549` (already replaced in Task 5 — verify the replacement is clean and no leftover comments reference `_scan_for_confrontation_trigger_keywords`).

If `re` is no longer used by the file, remove the `import re` at the top.

- [ ] **Step 5: Delete obsolete test files**

For each test file from Step 1 that exclusively exercised the legacy scanner, delete it. For tests that incidentally referenced it, delete only those assertions and convert them to validator-based equivalents if the test's intent (confirming a mechanism fires) remains relevant.

```bash
# Example — adjust per Step 1's findings
git rm sidequest-server/tests/server/test_legacy_confrontation_trigger_scanner.py
```

- [ ] **Step 6: Re-run the grep guard, expect pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_legacy_trigger_patterns_removed.py -v`
Expected: 3 PASS.

- [ ] **Step 7: Run the full server suite**

Run: `cd sidequest-server && uv run pytest tests/ -v -x`
Expected: ALL PASS.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/server/narration_apply.py \
        sidequest-server/tests/server/test_legacy_trigger_patterns_removed.py
git rm <each-deleted-legacy-test-file>
git commit -m "chore(narration): delete _CONFRONTATION_TRIGGER_PATTERNS lie-detector

Spec 2026-05-20 step 9: one mechanism per problem. The intent validator
is the single source of truth. Grep guards pin the symbols dead."
```

---

## Task 10: Pack content migration (7 packs)

Add `on_intent_mismatch:` to every confrontation def across all 7 production packs, and `intent_verbs:` where the label-derived set is too thin (use the Step 11 audit output from Task 2 as the guide).

**Files:**
- Modify: `sidequest-content/genre_packs/<pack>/rules.yaml` × 7

Severity policy:
- **reprompt** — `combat`, `ship_combat`, `dogfight`, `chase`, `standoff` (lethality / genre-truth heavy)
- **warn** — `negotiation`, `poker`, `trial`, `auction`, `social_duel`, `scandal` (social-pressure / transactional)

Suggested `intent_verbs` extensions per type (only where label-derived set is sparse; check the Task 2 Step 11 audit output and add what's missing):
- `negotiation`: `[haggle, bargain, barter, offer, deal, price, sell, buy, negotiate]`
- `combat`: `[strike, attack, fight, kill, slay, swing, shoot, hit, stab]`
- `chase`: `[chase, pursue, flee, run, escape, follow]`
- `standoff`: `[draw, stare, threaten, intimidate, square, confront]`
- `poker`: `[bet, raise, call, fold, bluff, ante, wager]`
- `ship_combat`: `[fire, broadside, ram, board, evade, cannon]`
- `dogfight`: `[dogfight, intercept, pursue, engage, lock, missile, gun]`
- `trial`: `[testify, accuse, defend, argue, cross-examine, object]`
- `auction`: `[bid, raise, outbid, hammer, lot]`
- `social_duel`: `[insult, riposte, parry, slight, retort, snub]`
- `scandal`: `[whisper, gossip, expose, slander, accuse, rumor]`

- [ ] **Step 1: Update `caverns_and_claudes/rules.yaml`**

For each of `combat`, `chase`, `negotiation`, add fields beneath the existing `label:` line. Example for `combat`:

```yaml
  - type: combat
    label: Combat
    category: combat
    # NEW — Spec 2026-05-20 confrontation-intent-validator
    intent_verbs: [strike, attack, fight, kill, slay, swing, shoot, hit, stab]
    on_intent_mismatch: reprompt
    ...rest of existing def unchanged...
```

Repeat for `chase` (reprompt + chase verbs) and `negotiation` (warn + negotiation verbs).

Run: `cd sidequest-server && uv run python -c "from sidequest.genre.loader import load_genre_pack; p = load_genre_pack('../sidequest-content/genre_packs/caverns_and_claudes'); print({c.confrontation_type: (c.on_intent_mismatch, len(c.intent_verb_set)) for c in p.rules.confrontations})"`
Expected: all three types load, intent_verb_set ≥ 5 each.

- [ ] **Step 2: Update `elemental_harmony/rules.yaml`** — same three types.
- [ ] **Step 3: Update `mutant_wasteland/rules.yaml`** — same three types.
- [ ] **Step 4: Update `road_warrior/rules.yaml`** — same three types.
- [ ] **Step 5: Update `space_opera/rules.yaml`** — `negotiation` (warn), `ship_combat` (reprompt), `combat` (reprompt), `chase` (reprompt), `dogfight` (reprompt).
- [ ] **Step 6: Update `spaghetti_western/rules.yaml`** — `standoff` (reprompt), `negotiation` (warn), `poker` (warn), `combat` (reprompt), `chase` (reprompt).
- [ ] **Step 7: Update `tea_and_murder/rules.yaml`** — `negotiation` (warn), `trial` (warn), `auction` (warn), `social_duel` (warn), `scandal` (warn). No reprompt types — Sonia-axis pacing.

- [ ] **Step 8: Run the audit again to confirm zero `[EMPTY]` markers**

```bash
cd sidequest-server && uv run python -c "
from sidequest.genre.loader import load_genre_pack
from pathlib import Path
root = Path('../sidequest-content/genre_packs')
for pack_dir in sorted(p for p in root.iterdir() if (p / 'pack.yaml').exists()):
    pack = load_genre_pack(pack_dir)
    for cdef in pack.rules.confrontations:
        verbs = cdef.intent_verb_set
        marker = ' [EMPTY]' if not verbs else ''
        print(f'  {pack_dir.name}/{cdef.confrontation_type}: {len(verbs)} verbs, on_intent_mismatch={cdef.on_intent_mismatch}{marker}')
"
```
Expected: every confrontation has ≥ 5 verbs and a non-default `on_intent_mismatch` (or the explicit default `warn`).

- [ ] **Step 9: Run the full server test suite once more**

Run: `cd sidequest-server && uv run pytest tests/ -v -x`
Expected: ALL PASS.

- [ ] **Step 10: Commit (sidequest-content subrepo)**

Note: `sidequest-content/` is a subrepo. Commit there first:

```bash
cd sidequest-content
git checkout -b feat/confrontation-intent-validator
git add genre_packs/caverns_and_claudes/rules.yaml \
        genre_packs/elemental_harmony/rules.yaml \
        genre_packs/mutant_wasteland/rules.yaml \
        genre_packs/road_warrior/rules.yaml \
        genre_packs/space_opera/rules.yaml \
        genre_packs/spaghetti_western/rules.yaml \
        genre_packs/tea_and_murder/rules.yaml
git commit -m "feat(rules): on_intent_mismatch + intent_verbs across 7 packs

Spec 2026-05-20 confrontation-intent-validator. Lethal/genre-truth heavy
confrontations get reprompt; social/transactional get warn. tea_and_murder
keeps everything warn per the playgroup pacing rule (no reprompt-driven
latency hits in the cosy genre)."
cd ..
```

Then commit the subrepo pointer in the orchestrator repo:

```bash
git add sidequest-content
git commit -m "chore(content): bump sidequest-content for intent-validator pack migration"
```

---

## Task 11: Replay regression test

Build a fixture from the 2026-05-20 dust_and_lead save and replay turns 5–10 to assert the validator fires `confrontation.intent_mismatch` with `matched_type=negotiation` on the horse-purchase scene.

**Files:**
- Create: `sidequest-server/tests/fixtures/dust_and_lead_horse_replay/` (extracted minimal save data)
- Create: `sidequest-server/tests/server/test_dust_and_lead_horse_replay.py`

- [ ] **Step 1: Extract the minimal replay fixture from the save**

```bash
SAVE_DIR=/Users/slabgorb/.sidequest/saves/games/2026-05-20-dust_and_lead
ls "$SAVE_DIR"
# Identify the .db. Don't open with SqliteStore (memory:
# project_sqlitestore_open_writes — it mutates on open). Use sqlite3 ro mode.
sqlite3 "file:$SAVE_DIR/<save>.db?mode=ro" -separator $'\t' \
  "SELECT turn_id, agent, content FROM events WHERE event_type='NARRATION' AND turn_id BETWEEN 5 AND 10;" \
  > sidequest-server/tests/fixtures/dust_and_lead_horse_replay/turns_5_10.tsv
sqlite3 "file:$SAVE_DIR/<save>.db?mode=ro" \
  "SELECT snapshot_json FROM game_state ORDER BY rowid DESC LIMIT 1;" \
  > sidequest-server/tests/fixtures/dust_and_lead_horse_replay/snapshot.json
```

Adjust the column names if the schema differs — run `.schema events` and `.schema game_state` to confirm.

- [ ] **Step 2: Reduce the snapshot to a minimal valid `GameSnapshot`**

Hand-trim `snapshot.json` to just the keys `GameSnapshot` requires — `genre_slug` (`spaghetti_western`), `world_slug` (`dust_and_lead`), `characters`, `npcs`, `time_of_day`, and `encounter: null`. Strip every other field; the snapshot only needs to load and have `encounter=None` for the validator's `active_encounter=False` branch.

If the test relies on running the SDK narrator, that's wrong — replay tests stub the narrator. The fixture only needs the `action_rewrite.intent` strings the narrator emitted on each turn, which you can read from the per-turn telemetry or reconstruct from the narration prose. Capture what's available; assert on what the validator does with that input.

- [ ] **Step 3: Write the failing replay test**

Create `sidequest-server/tests/server/test_dust_and_lead_horse_replay.py`:

```python
"""Replay regression — 2026-05-20 dust_and_lead horse-purchase scene.

The bug: five turns of textbook negotiation prose with action_rewrite.intent
like 'negotiate horse price' / 'haggle for the mare' produced zero
confrontation telemetry. The validator must now fire intent_mismatch with
matched_type=negotiation on every such turn.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sidequest.agents.orchestrator import ActionRewrite
from sidequest.game.session import GameSnapshot
from sidequest.genre.loader import load_genre_pack


CONTENT_ROOT = Path(__file__).resolve().parents[3] / "sidequest-content"


@pytest.fixture
def spaghetti_western_pack():
    return load_genre_pack(CONTENT_ROOT / "genre_packs" / "spaghetti_western")


# Captured intent strings from the actual save's per-turn telemetry.
# Add the literal intent strings observed in the 2026-05-20 save below.
DUST_AND_LEAD_HORSE_INTENTS = [
    "negotiate horse price",
    "haggle for the mare",
    "counter with sixty dollars",
    "press the seller on feed cost",
    "accept the deal at sixty-five",
]


@pytest.mark.parametrize("intent", DUST_AND_LEAD_HORSE_INTENTS)
def test_horse_scene_intent_fires_negotiation_mismatch(intent, spaghetti_western_pack) -> None:
    from sidequest.agents.confrontation_intent_validator import validate

    result = validate(
        ActionRewrite(intent=intent),
        declared_confrontation=None,
        pack=spaghetti_western_pack,
        active_encounter=False,
    )

    assert result is not None, f"validator missed intent={intent!r}"
    assert result.matched_type == "negotiation", (
        f"intent={intent!r} matched={result.matched_type} (expected negotiation)"
    )
    assert result.severity == "warn"  # per Task 10 migration policy


def test_horse_scene_full_dispatch_emits_span_and_classifies(
    spaghetti_western_pack,
    monkeypatch,
) -> None:
    """End-to-end through _apply_narration_result_to_snapshot."""
    from sidequest.agents.orchestrator import NarrationTurnResult
    from sidequest.server import narration_apply

    snap = GameSnapshot(genre_slug="spaghetti_western", encounter=None)
    result = NarrationTurnResult(
        narration="'Sixty don't cover the feed she's eaten,' the seller drawls.",
        action_rewrite=ActionRewrite(intent="haggle for the mare"),
        confrontation=None,
        npcs_present=[],
    )
    room = MagicMock()

    spans: list[str] = []
    from sidequest.telemetry import spans as spans_mod
    monkeypatch.setattr(
        spans_mod,
        "confrontation_intent_mismatch_span",
        lambda **kw: _ContextLogger(spans, kw),
    )

    outcome = narration_apply._apply_narration_result_to_snapshot(
        snap, result, "Player1", room=room, pack=spaghetti_western_pack
    )

    assert any(s["matched_type"] == "negotiation" for s in spans), spans
    assert outcome.classified_intent == "negotiation"
    assert outcome.classified_intent != "unknown"


class _ContextLogger:
    def __init__(self, sink: list, attrs: dict) -> None:
        self._sink = sink
        self._attrs = attrs

    def __enter__(self):
        self._sink.append(self._attrs)
        return self

    def __exit__(self, *exc):
        return False
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_dust_and_lead_horse_replay.py -v`
Expected: all PASS once the captured intent strings are real.

If the actual save's intent strings differ from the examples above, update `DUST_AND_LEAD_HORSE_INTENTS` to the real captured values before declaring this task done. If the save lacks per-turn intent telemetry (the validator's whole reason for existing!), capture a synthetic but realistic intent string for each of turns 5–10 by reading the narration prose and writing the intent a competent narrator should have emitted.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/tests/fixtures/dust_and_lead_horse_replay/ \
        sidequest-server/tests/server/test_dust_and_lead_horse_replay.py
git commit -m "test(intent): replay regression for 2026-05-20 dust_and_lead horse scene

Spec 2026-05-20 step 10: the bug that motivated this design. Five
negotiation-shaped intents from the save's actual narrator output now
each fire confrontation.intent_mismatch matched_type=negotiation; the
dispatch path populates classified_intent='negotiation' on the outcome."
```

---

## Task 12: ADR-067 amendment

Record the wiring that delivers ADR-067's unfulfilled inference promise.

**Files:**
- Modify: `docs/adr/0067-unified-narrator-agent.md`

- [ ] **Step 1: Read the existing ADR**

```bash
cat docs/adr/0067-unified-narrator-agent.md
```

Find the spot for an amendment (the file may already have an "Amendments" or "Changelog" section; if not, add one near the end).

- [ ] **Step 2: Append the amendment**

Add (or extend an existing Amendments section):

```markdown
## Amendment — 2026-05-20 — Intent inference site wired

ADR-067 promised inference rather than pre-narration classification, with
the narrator's response implicitly carrying intent information that
post-narration extraction would lift for OTEL and state-machine
transitions. That inference site was never built.

Spec `docs/superpowers/specs/2026-05-20-confrontation-intent-validator-design.md`
delivers it:

1. The inference site is `sidequest.agents.confrontation_intent_validator.validate(...)`.
   It reads `ActionRewrite.intent` (formerly dead infrastructure carried
   through `NarrationTurnResult` with no downstream consumer) and compares
   it to the narrator's declared `confrontation` against vocabulary owned
   by each `ConfrontationDef` in `rules.yaml`.

2. `TurnRecord.classified_intent` is populated from `action_rewrite.intent`
   verbatim on the happy path and from `ValidationResult.matched_type` on
   mismatch. The hardcoded `"unknown"` stub at
   `websocket_session_handler.py` is removed. `"unspecified"` is used
   when the narrator omits `action_rewrite.intent` entirely.

3. The legacy prose-regex lie-detector
   (`_CONFRONTATION_TRIGGER_PATTERNS` and
   `_scan_for_confrontation_trigger_keywords` in
   `sidequest/server/narration_apply.py`) is retired in the same change
   per the one-mechanism-per-problem doctrine. No prose regex against
   narrator output remains.

The unified-narrator topology is unchanged: no specialist agents, no
pre-narration classifier resurrected from ADR-010. The narrator's
prompt assembly and tool-use contract are also unchanged.
```

- [ ] **Step 3: Update the ADR index if needed**

If the index page (`docs/adr/README.md`) lists per-ADR status notes, add a "(amended)" marker to the 067 line.

```bash
grep -n "0067\|067" docs/adr/README.md docs/adr/DRIFT.md 2>/dev/null
```

Edit as appropriate.

- [ ] **Step 4: Commit**

```bash
git add docs/adr/0067-unified-narrator-agent.md docs/adr/README.md docs/adr/DRIFT.md 2>/dev/null
git commit -m "docs(adr): amend ADR-067 — inference site wired via intent validator

Records that the inference + extraction promise is delivered by
confrontation_intent_validator.validate(...) and TurnRecord.classified_intent
is populated from action_rewrite.intent / matched_type. Legacy prose-regex
lie-detector retired in the same change."
```

---

## Final verification

- [ ] **Run the whole server gate**

```bash
just server-check  # ruff + pytest
```
Expected: PASS end-to-end.

- [ ] **Run client + daemon gates (no expected impact, but the change touches a watcher event UI surface)**

```bash
just check-all
```
Expected: PASS.

- [ ] **Smoke a live turn through `just up`**

Boot the stack, start a spaghetti_western / dust_and_lead session, prompt for a horse-buy scene, watch the GM panel for `confrontation.intent_mismatch matched_type=negotiation severity=warn`. Confirm `TurnRecord.classified_intent` reads `"negotiation"` (not `"unknown"`) in the OTEL dashboard. The replay regression test exercises this synthetically; the smoke confirms the real path.

- [ ] **Open the PR**

Per the spec's one-mechanism doctrine, one PR for the whole change:

```bash
git push -u origin feat/confrontation-intent-validator
gh pr create --title "Confrontation Intent Validator — wire ActionRewrite.intent, retire prose regex" \
  --body "$(cat <<'EOF'
## Summary
- Activates ActionRewrite.intent (was dead) as the authoritative confrontation-intent signal
- Adds confrontation_intent_validator.validate (the inference site ADR-067 promised)
- Per-def on_intent_mismatch behaviour (warn / soft_suggest / reprompt) drives dispatch
- One-iteration orchestrator reprompt loop; soft_suggest enqueues a next-turn directive
- TurnRecord.classified_intent populated from real signal (or 'unspecified'); 'unknown' hardcodes removed
- DELETES _CONFRONTATION_TRIGGER_PATTERNS + scanner per one-mechanism-per-problem doctrine
- New OTEL spans: confrontation.intent_mismatch[_resolved|_reprompt_failed]; GM panel renders them
- 7 production packs migrated with intent_verbs + on_intent_mismatch policy
- ADR-067 amended

Spec: docs/superpowers/specs/2026-05-20-confrontation-intent-validator-design.md
Plan: docs/superpowers/plans/2026-05-20-confrontation-intent-validator.md
Driver bug: 2026-05-20 dust_and_lead horse-purchase scene — five-turn negotiation with zero confrontation telemetry.

## Test plan
- [ ] just server-check passes
- [ ] just check-all passes
- [ ] Manual smoke: spaghetti_western/dust_and_lead horse-buy fires confrontation.intent_mismatch matched_type=negotiation in GM panel
- [ ] OTEL: TurnRecord.classified_intent shows actual intent / matched_type, never 'unknown'
- [ ] Replay regression test (test_dust_and_lead_horse_replay.py) passes

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
