# Local DM Group C — Lethality Arbitration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove life-and-death decisions from the narrator by synthesising deterministic `LethalityVerdict`s from post-bank game state + a per-genre `lethality_policy`, and injecting `must_narrate` / `must_not_narrate` directives so the narrator only describes — never decides — whether a character lives.

**Architecture:** Group B landed the `LethalityVerdict` pydantic model and reserved `DispatchPackage.per_player[*].lethality`. Group C adds (a) a `LethalityPolicy` genre-pack YAML + loader, (b) a deterministic `LethalityArbiter` that runs **after** `run_dispatch_bank` and **before** `narrator_directives` section registration, reading `edge.current` on Characters + NPCs plus subsystem outputs, (c) synthesis of genre-tuned verdicts with paired `must_narrate` / `must_not_narrate` directives, (d) OTEL spans for Sebastien's GM panel, and (e) per-genre smoke tests that assert a PC at zero edge produces a genre-appropriate verdict in each shipped pack. The arbiter is **not** an LLM — it is deterministic synthesis. The decomposer LLM's own verdict emissions (if any) are merged by `entity` with the arbiter's output; arbiter wins on conflict (spec §4.1: "the only durable fix is to remove the decision from the narrator").

**Tech Stack:** Python 3.12, pydantic, pytest + pytest-asyncio, uv, OpenTelemetry, YAML. No new dependencies.

**Reference spec:** `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md` §4 + §10 Story Group C.

**Depends on:** Group B (merged PR #29 into `sidequest-server/develop`). Do not start until Group B is visible on `develop`.

**Repos touched:**

- `sidequest-server/` — arbiter + wiring + tests (branch `feat/local-dm-group-c`, targets `develop`)
- `sidequest-content/` — per-pack `lethality_policy.yaml` (branch `feat/local-dm-group-c`, targets `main`)

Per `repos.yaml`: server targets `develop`; content targets `main`. Never assume `main` for both. Each repo gets its own PR; server PR depends on content PR being merged first (content loaders fail loud on missing file — see Task 3).

**Branch + worktree:**

```
/Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
```

Follow Group B's pattern: worktree off `sidequest-server/develop` after Group B merge. Every subagent MUST `cd` to this absolute path as its first bash call — subagent `cd` state does not persist across bash calls reliably.

**Decisions locked (do not re-litigate):**

1. **Arbiter is deterministic, not LLM.** Spec §4.1 names "prompting does not correct this reliably" as the reason the decision leaves the narrator. It follows that it also leaves the LLM decomposer. The Haiku decomposer may still *propose* verdicts; the arbiter is authoritative.
2. **Verdict triggers in Phase A are edge-based only.** `creature.core.edge.current == 0` is the sole trigger. Confrontation-beat failures, resource-pool depletion, and roll outcomes stay Group E wiring — the subsystems that emit those signals don't exist yet on the Python port.
3. **Policy lives in a new per-pack file, not in `rules.yaml`.** Mirrors the Group G `visibility_baseline.yaml` pattern: dedicated file, strict pydantic validation, fail-loud on missing key fields. `RulesConfig.lethality` (free-form string) is left untouched — it's narrator tone flavour, not adjudication input.
4. **Must_narrate + must_not_narrate always come as a pair.** Never emit one without the other for a given verdict. The narrator reads the pair as a single constraint envelope.
5. **Verdict merge rule on decomposer/arbiter conflict:** arbiter wins, decomposer-only fields are preserved for audit. See Task 9.
6. **`WitnessScope` stays `dict`.** Group B ships it as `dict` with documented keys. Upgrading to a typed pydantic submodel is a Group-G follow-up (Group G consumes witness_scope; it can write the migration itself). Do not touch the `LethalityVerdict` schema in Group C.
7. **Content repo PR ships first.** Server loader fails loud on missing `lethality_policy.yaml`; merging server before content would red the develop branch.

**Non-goals (explicit rejections):**

- No LLM-backed arbiter. Deterministic synthesis only.
- No new `lethality_policy` subsystem. Arbiter runs inline after the bank.
- No changes to the `LethalityVerdict` protocol schema.
- No HP system rewrite. Edge-based triggers only.
- No narrator self-policing ("remember not to soften"). The prompt envelope is the enforcement.
- No multiplayer fan-out of verdicts. Group G owns per-player projection; arbiter stays canonical.
- No GM panel override UI. Panel already reads OTEL spans; Keith overrides via existing post-turn flow.

---

## File Structure

**New files (sidequest-server):**

- `sidequest-server/sidequest/genre/models/lethality.py` — `LethalityPolicy` + `VerdictsOnZeroEdge` pydantic models
- `sidequest-server/sidequest/genre/lethality_policy_loader.py` — YAML loader with strict validation
- `sidequest-server/sidequest/agents/lethality_arbiter.py` — `LethalityArbiter` class + `LethalityResult` dataclass
- `sidequest-server/tests/genre/test_lethality_policy.py`
- `sidequest-server/tests/agents/test_lethality_arbiter.py`
- `sidequest-server/tests/agents/test_lethality_directives_in_prompt.py`
- `sidequest-server/tests/integration/test_group_c_e2e.py`
- `sidequest-server/tests/genre/test_lethality_policy_per_pack.py`

**New files (sidequest-content):**

- `sidequest-content/genre_packs/caverns_and_claudes/lethality_policy.yaml`
- `sidequest-content/genre_packs/elemental_harmony/lethality_policy.yaml`
- `sidequest-content/genre_packs/heavy_metal/lethality_policy.yaml`
- `sidequest-content/genre_packs/mutant_wasteland/lethality_policy.yaml`
- `sidequest-content/genre_packs/space_opera/lethality_policy.yaml`
- `sidequest-content/genre_packs/spaghetti_western/lethality_policy.yaml`

**Modified files:**

- `sidequest-server/sidequest/genre/pack.py` — register the new file; expose via `GenrePack`
- `sidequest-server/sidequest/genre/pack_loader.py` (or the Python port's equivalent) — call the new loader
- `sidequest-server/sidequest/telemetry/spans.py` — `SPAN_LOCAL_DM_LETHALITY_ARBITRATE` constant + `lethality_arbitrate_span` context manager
- `sidequest-server/sidequest/agents/orchestrator.py` — run the arbiter after `run_dispatch_bank`; inject paired directives alongside subsystem directives
- `sidequest-server/sidequest/agents/local_dm.py` — pass `lethality_policy` through `decompose(..., lethality_policy=...)` if call sites need it (likely no-op — arbiter lives in orchestrator, policy loaded from pack at session init)

---

## Task 0: Branch, Worktree, Baseline

**Files:** none (git-only)

- [ ] **Step 1: Confirm Group B is on `develop`**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git fetch origin
git log origin/develop --oneline | grep -E "group B task 15|group-b" | head -3
```
Expected: see the Group B merge commit (PR #29, tip ~`822b09e`). If not present, STOP — Group C assumes Group B.

- [ ] **Step 2: Create worktree on fresh `develop`**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git worktree add .worktrees/group-c -b feat/local-dm-group-c origin/develop
ls .worktrees/group-c/sidequest/agents/local_dm.py
```
Expected: the worktree exists and contains Group B's `local_dm.py`.

- [ ] **Step 3: Verify sidequest-content symlink**

```bash
ls -la /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/sidequest-content 2>&1 || true
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c && ls sidequest-content 2>&1 || true
```
If the `sidequest-content` symlink isn't present inside the worktree (genre-pack discovery needs it), create it:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
ln -s ../../../sidequest-content sidequest-content
```

- [ ] **Step 4: Capture baseline test count**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
just server-test 2>&1 | tail -5
```
Expected: all green. Record the pass count — Task 15 compares against this.

- [ ] **Step 5: Prepare content branch (separate clone)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git fetch origin
git checkout -b feat/local-dm-group-c origin/main
```
The content branch is shallow — Task 5 is its only commit.

- [ ] **Step 6: Commit baseline marker on server branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
git commit --allow-empty -m "chore(group-c): branch from develop post group B"
```

---

## Task 1: `LethalityPolicy` pydantic model

**Files:**
- Create: `sidequest-server/sidequest/genre/models/lethality.py`
- Test: `sidequest-server/tests/genre/test_lethality_policy.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/genre/test_lethality_policy.py
"""LethalityPolicy — per-genre lethality tuning (Group C spec §4.4 + §10)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.lethality import LethalityPolicy, VerdictsOnZeroEdge


def test_minimal_policy_roundtrips():
    policy = LethalityPolicy(
        genre_key="caverns_and_claudes",
        default_reversibility="narrative_only",
        verdicts_on_zero_edge=VerdictsOnZeroEdge(pc="humiliated", npc="defeated"),
        soul_md_constraint="genre_truth:comedic_danger_no_permadeath",
        must_narrate="A beat of slapstick pain. Keep it comedic.",
        must_not_narrate="graphic permadeath; somber elegy; last-rites speech",
    )
    assert policy.genre_key == "caverns_and_claudes"
    assert policy.default_reversibility == "narrative_only"
    assert policy.verdicts_on_zero_edge.pc == "humiliated"


def test_unknown_verdict_kind_rejected():
    """Validator must reject verdict kinds not in the LethalityVerdictKind literal."""
    with pytest.raises(ValidationError):
        VerdictsOnZeroEdge(pc="obliterated", npc="defeated")  # "obliterated" not in enum


def test_extra_fields_forbidden():
    """`extra='forbid'` catches typos in YAML — silent drop would mask content bugs."""
    with pytest.raises(ValidationError):
        LethalityPolicy(
            genre_key="x",
            default_reversibility="permanent",
            verdicts_on_zero_edge=VerdictsOnZeroEdge(pc="dead", npc="dead"),
            soul_md_constraint="x",
            must_narrate="x",
            must_not_narrate="x",
            nonsense_field=True,  # type: ignore[call-arg]
        )


def test_must_narrate_and_must_not_narrate_both_non_blank():
    """Both narrator-tone strings must be non-blank — they ship as a pair."""
    with pytest.raises(ValidationError):
        LethalityPolicy(
            genre_key="x",
            default_reversibility="permanent",
            verdicts_on_zero_edge=VerdictsOnZeroEdge(pc="dead", npc="dead"),
            soul_md_constraint="x",
            must_narrate="",
            must_not_narrate="nope",
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
uv run pytest tests/genre/test_lethality_policy.py -v
```
Expected: all 4 tests fail with `ImportError` — `sidequest.genre.models.lethality` does not exist.

- [ ] **Step 3: Write the model**

```python
# sidequest/genre/models/lethality.py
"""LethalityPolicy — per-genre lethality tuning consumed by LethalityArbiter.

Spec: docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md §4 + §10
Group C.

YAML lives in sidequest-content/genre_packs/<pack>/lethality_policy.yaml.
Strict validation (extra='forbid'): unknown keys raise at pack-load time,
not at runtime — CLAUDE.md "no silent fallbacks".

The arbiter (sidequest.agents.lethality_arbiter) reads this model to
decide what verdict shape a given genre produces when a PC or NPC hits
zero edge, and what narrator-tone constraint envelope ships alongside.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from sidequest.protocol.dispatch import LethalityVerdictKind, Reversibility


class VerdictsOnZeroEdge(BaseModel):
    """Per-actor-kind verdict shape when `core.edge.current == 0`."""

    model_config = ConfigDict(extra="forbid")

    pc: LethalityVerdictKind
    npc: LethalityVerdictKind


class LethalityPolicy(BaseModel):
    """Per-genre lethality-arbitration inputs.

    `genre_key` is required and must match the pack directory name — the
    loader validates this (Task 3). `must_narrate` + `must_not_narrate` ship
    as a paired envelope in the narrator prompt (see Task 12); neither may
    be blank.
    """

    model_config = ConfigDict(extra="forbid")

    genre_key: str
    default_reversibility: Reversibility
    verdicts_on_zero_edge: VerdictsOnZeroEdge
    soul_md_constraint: str
    must_narrate: str
    must_not_narrate: str

    @field_validator("genre_key", "soul_md_constraint", "must_narrate", "must_not_narrate")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field cannot be blank")
        return v


__all__ = ["LethalityPolicy", "VerdictsOnZeroEdge"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/genre/test_lethality_policy.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/models/lethality.py tests/genre/test_lethality_policy.py
git commit -m "feat(genre): LethalityPolicy pydantic model (group C task 1)"
```

---

## Task 2: `LethalityPolicy` YAML loader

**Files:**
- Create: `sidequest-server/sidequest/genre/lethality_policy_loader.py`
- Modify: `sidequest-server/tests/genre/test_lethality_policy.py` (append)

- [ ] **Step 1: Append the failing loader tests**

```python
# tests/genre/test_lethality_policy.py — APPEND

import textwrap
from pathlib import Path

from sidequest.genre.lethality_policy_loader import (
    load_lethality_policy,
    LethalityPolicyMissingError,
)


def test_loader_reads_valid_yaml(tmp_path: Path):
    pack_dir = tmp_path / "caverns_and_claudes"
    pack_dir.mkdir()
    (pack_dir / "lethality_policy.yaml").write_text(textwrap.dedent("""
        genre_key: caverns_and_claudes
        default_reversibility: narrative_only
        verdicts_on_zero_edge:
          pc: humiliated
          npc: defeated
        soul_md_constraint: "genre_truth:comedic_danger_no_permadeath"
        must_narrate: "A beat of slapstick pain. Keep it comedic."
        must_not_narrate: "graphic permadeath; somber elegy; last-rites speech"
    """).strip())
    policy = load_lethality_policy(pack_dir)
    assert policy.genre_key == "caverns_and_claudes"
    assert policy.verdicts_on_zero_edge.pc == "humiliated"


def test_loader_fails_loud_on_missing_file(tmp_path: Path):
    pack_dir = tmp_path / "empty_pack"
    pack_dir.mkdir()
    with pytest.raises(LethalityPolicyMissingError) as exc:
        load_lethality_policy(pack_dir)
    assert "empty_pack" in str(exc.value)


def test_loader_rejects_genre_key_mismatch(tmp_path: Path):
    """genre_key inside the YAML must match the pack directory name."""
    pack_dir = tmp_path / "caverns_and_claudes"
    pack_dir.mkdir()
    (pack_dir / "lethality_policy.yaml").write_text(textwrap.dedent("""
        genre_key: some_other_pack
        default_reversibility: permanent
        verdicts_on_zero_edge:
          pc: dead
          npc: dead
        soul_md_constraint: x
        must_narrate: x
        must_not_narrate: x
    """).strip())
    with pytest.raises(ValueError) as exc:
        load_lethality_policy(pack_dir)
    assert "genre_key mismatch" in str(exc.value)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/genre/test_lethality_policy.py -v
```
Expected: 3 new failures — `sidequest.genre.lethality_policy_loader` does not exist.

- [ ] **Step 3: Write the loader**

```python
# sidequest/genre/lethality_policy_loader.py
"""Strict YAML loader for per-pack lethality_policy.yaml.

Fails loud per CLAUDE.md "no silent fallbacks":
  - Missing file → LethalityPolicyMissingError (not a warning, not a default)
  - Schema violation → pydantic ValidationError (extra='forbid' catches typos)
  - genre_key/dirname mismatch → ValueError (prevents copy-paste drift)
"""
from __future__ import annotations

from pathlib import Path

import yaml

from sidequest.genre.models.lethality import LethalityPolicy


class LethalityPolicyMissingError(FileNotFoundError):
    """Raised when a genre pack directory has no `lethality_policy.yaml`."""

    def __init__(self, pack_dir: Path) -> None:
        self.pack_dir = pack_dir
        super().__init__(f"lethality_policy.yaml missing in {pack_dir}")


def load_lethality_policy(pack_dir: Path) -> LethalityPolicy:
    """Load + validate the lethality policy for a genre pack.

    `pack_dir` is the directory containing the pack's YAML files — e.g.,
    `sidequest-content/genre_packs/caverns_and_claudes`. Its name is
    cross-checked against the YAML's `genre_key` field.
    """
    path = pack_dir / "lethality_policy.yaml"
    if not path.exists():
        raise LethalityPolicyMissingError(pack_dir)
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    policy = LethalityPolicy.model_validate(raw)
    if policy.genre_key != pack_dir.name:
        raise ValueError(
            f"genre_key mismatch: yaml says {policy.genre_key!r}, "
            f"pack dir is {pack_dir.name!r}"
        )
    return policy


__all__ = ["LethalityPolicyMissingError", "load_lethality_policy"]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/genre/test_lethality_policy.py -v
```
Expected: 7 passed (4 from Task 1 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/lethality_policy_loader.py tests/genre/test_lethality_policy.py
git commit -m "feat(genre): strict loader for lethality_policy.yaml (group C task 2)"
```

---

## Task 3: Content — Author `lethality_policy.yaml` for all 6 packs

**Files (sidequest-content branch `feat/local-dm-group-c`):**

- Create: `sidequest-content/genre_packs/caverns_and_claudes/lethality_policy.yaml`
- Create: `sidequest-content/genre_packs/elemental_harmony/lethality_policy.yaml`
- Create: `sidequest-content/genre_packs/heavy_metal/lethality_policy.yaml`
- Create: `sidequest-content/genre_packs/mutant_wasteland/lethality_policy.yaml`
- Create: `sidequest-content/genre_packs/space_opera/lethality_policy.yaml`
- Create: `sidequest-content/genre_packs/spaghetti_western/lethality_policy.yaml`

Content targets `main` (per repos.yaml), in a dedicated `sidequest-content` checkout. Do this in a separate shell, not the server worktree.

- [ ] **Step 1: caverns_and_claudes — comedic, non-permadeath**

```yaml
# sidequest-content/genre_packs/caverns_and_claudes/lethality_policy.yaml
genre_key: caverns_and_claudes
default_reversibility: narrative_only
verdicts_on_zero_edge:
  pc: humiliated
  npc: defeated
soul_md_constraint: "genre_truth:comedic_danger_no_permadeath"
must_narrate: "The delver is out of it — dazed, embarrassed, comically incapacitated. Back on their feet next session with a one-liner."
must_not_narrate: "graphic permadeath; somber eulogy; last-rites speech; heroic ally intervention that erases the defeat"
```

- [ ] **Step 2: elemental_harmony — no permadeath, low lethality**

```yaml
# sidequest-content/genre_packs/elemental_harmony/lethality_policy.yaml
genre_key: elemental_harmony
default_reversibility: reversible_with_cost
verdicts_on_zero_edge:
  pc: defeated
  npc: defeated
soul_md_constraint: "genre_truth:harmony_tested_not_broken"
must_narrate: "The bond frays but does not sever. A recoverable setback with meaningful cost — an element withdraws, a relationship strains, a memory clouds."
must_not_narrate: "permanent death of a PC; narrate survival where survival was not earned; invent a healer arriving out of nowhere"
```

- [ ] **Step 3: heavy_metal — brutal, permanent**

```yaml
# sidequest-content/genre_packs/heavy_metal/lethality_policy.yaml
genre_key: heavy_metal
default_reversibility: permanent
verdicts_on_zero_edge:
  pc: dead
  npc: dead
soul_md_constraint: "genre_truth:lethal_for_this_genre"
must_narrate: "Render the death with specific, brutal detail. The genre promises lethality; honor the promise. The antagonist does not hesitate."
must_not_narrate: "narrate survival; invent an ally's last-second intervention; let the enemy monologue instead of strike; soften the damage after the fact"
```

- [ ] **Step 4: mutant_wasteland — lethal, permanent**

```yaml
# sidequest-content/genre_packs/mutant_wasteland/lethality_policy.yaml
genre_key: mutant_wasteland
default_reversibility: permanent
verdicts_on_zero_edge:
  pc: dead
  npc: dead
soul_md_constraint: "genre_truth:wasteland_kills_what_it_bites"
must_narrate: "The wasteland is indifferent. Describe the death in genre-true terms — radiation, infected wound, ambush, or mundane violence — with specificity, not melodrama."
must_not_narrate: "miraculous rescues; pre-war medical intervention appearing; enemies hesitating out of mercy; dying declarations the character did not earn"
```

- [ ] **Step 5: space_opera — reversible-with-cost, rescue-plausible**

```yaml
# sidequest-content/genre_packs/space_opera/lethality_policy.yaml
genre_key: space_opera
default_reversibility: reversible_with_cost
verdicts_on_zero_edge:
  pc: dying
  npc: defeated
soul_md_constraint: "genre_truth:stakes_are_real_rescue_is_possible"
must_narrate: "The character is dying — unconscious, bleeding, minutes to live. The cost of rescue (fuel, a favor, a secret traded) is real and named on the table."
must_not_narrate: "invent a medbay nobody has paid for; narrate instant survival; erase the cost of the rescue; let the villain pause out of authorial mercy"
```

- [ ] **Step 6: spaghetti_western — brutal, permanent, mythic**

```yaml
# sidequest-content/genre_packs/spaghetti_western/lethality_policy.yaml
genre_key: spaghetti_western
default_reversibility: permanent
verdicts_on_zero_edge:
  pc: dead
  npc: dead
soul_md_constraint: "genre_truth:the_west_does_not_forgive"
must_narrate: "A death in the dust. Lean, specific, mythic. Name the wound, name the weapon, name the silence after. The villain walks away without looking back."
must_not_narrate: "comic relief; a stranger appearing to drag the body to a doctor; monologue that delays the kill; survival-through-plot-armor"
```

- [ ] **Step 7: Validate all six against the pydantic model (from server worktree)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
uv run python -c "
from pathlib import Path
from sidequest.genre.lethality_policy_loader import load_lethality_policy
for name in ['caverns_and_claudes','elemental_harmony','heavy_metal','mutant_wasteland','space_opera','spaghetti_western']:
    p = Path('sidequest-content/genre_packs') / name
    print(name, '→', load_lethality_policy(p).verdicts_on_zero_edge)
"
```
Expected: all six print their `VerdictsOnZeroEdge` without exception.

- [ ] **Step 8: Commit + push content branch + open PR**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git add genre_packs/*/lethality_policy.yaml
git commit -m "feat(packs): lethality_policy.yaml for all six shipped packs (group C)"
git push -u origin feat/local-dm-group-c
gh pr create --base main --title "feat(packs): lethality_policy.yaml for group C" --body "$(cat <<'EOF'
## Summary
- Adds `lethality_policy.yaml` to the six shipped genre packs
- Consumed by sidequest-server `LethalityArbiter` (Local DM Group C)
- Strict schema defined in `sidequest/genre/models/lethality.py`

## Test plan
- [ ] sidequest-server loader round-trips all six (see task 3 step 7 in plan)
- [ ] sidequest-server `tests/genre/test_lethality_policy_per_pack.py` (task 13) passes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```
Wait for this PR to merge before the server PR in Task 15 — server tests load these files at pack-init time.

---

## Task 4: Wire loader into `GenrePack`

**Files:**
- Modify: `sidequest-server/sidequest/genre/pack.py`
- Modify: `sidequest-server/sidequest/genre/pack_loader.py` (or the Python port's equivalent loader entry point — find with `grep -rn "load_genre_pack\b" sidequest/genre/`)
- Test: `sidequest-server/tests/genre/test_lethality_policy.py` (append one wiring test)

- [ ] **Step 1: Locate the pack-load entry point**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
grep -rn "load_genre_pack\|def load_pack\|class GenrePack\b" sidequest/genre/ | grep -v __pycache__ | head -10
```
Record the file path and line. You will add the `lethality_policy` attribute to `GenrePack` and the loader call to whichever function builds it.

- [ ] **Step 2: Write the failing wiring test**

Append to `tests/genre/test_lethality_policy.py`:

```python
def test_genre_pack_exposes_lethality_policy():
    """Once a pack is loaded, its `lethality_policy` attribute is populated."""
    from sidequest.genre.pack_loader import load_genre_pack  # adjust import if the port renamed it
    pack = load_genre_pack("caverns_and_claudes")
    assert pack.lethality_policy is not None
    assert pack.lethality_policy.genre_key == "caverns_and_claudes"
    assert pack.lethality_policy.verdicts_on_zero_edge.pc == "humiliated"
```

(If the port's loader function has a different name or signature, adjust the import + call but keep the assertion shape.)

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/genre/test_lethality_policy.py::test_genre_pack_exposes_lethality_policy -v
```
Expected: FAIL with `AttributeError: 'GenrePack' object has no attribute 'lethality_policy'` (or similar).

- [ ] **Step 4: Add the field + wire the loader**

In `sidequest/genre/pack.py` (or wherever `GenrePack` is defined), add:

```python
# Near the other Optional config fields on GenrePack
from sidequest.genre.models.lethality import LethalityPolicy

# Inside GenrePack:
lethality_policy: LethalityPolicy | None = None
```

In the loader (whichever file builds the `GenrePack` instance), after the rest of the YAML files are loaded, add:

```python
from sidequest.genre.lethality_policy_loader import load_lethality_policy

# ... existing pack build ...
pack.lethality_policy = load_lethality_policy(pack_dir)  # pack_dir is the Path to the pack folder
```

Note: the loader raises `LethalityPolicyMissingError` if the file is absent. That is the correct behaviour — every shipped pack now has the file (Task 3). If a test pack fixture doesn't have one, either add the file to the fixture or catch `LethalityPolicyMissingError` in the test setup (do not add a silent fallback to the loader).

- [ ] **Step 5: Run test**

```bash
uv run pytest tests/genre/test_lethality_policy.py::test_genre_pack_exposes_lethality_policy -v
```
Expected: PASS.

- [ ] **Step 6: Run the full genre test slice**

```bash
uv run pytest tests/genre/ -v
```
Expected: no regressions. If a fixture pack is missing `lethality_policy.yaml`, add it to the fixture — do not relax the loader.

- [ ] **Step 7: Commit**

```bash
git add sidequest/genre/pack.py sidequest/genre/pack_loader.py tests/genre/test_lethality_policy.py
git commit -m "feat(genre): wire lethality_policy into GenrePack loader (group C task 4)"
```

---

## Task 5: `LethalityArbiter` — happy path (PC at zero edge)

**Files:**
- Create: `sidequest-server/sidequest/agents/lethality_arbiter.py`
- Test: `sidequest-server/tests/agents/test_lethality_arbiter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/test_lethality_arbiter.py
"""LethalityArbiter — deterministic verdict synthesis from game state + policy.

Spec: docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md §4
Group C: verdict producer consumes HP/edge state + policy, emits verdicts
and paired narrator directives. Edge-based triggers only for Phase A.
"""
from __future__ import annotations

import pytest

from sidequest.agents.lethality_arbiter import LethalityArbiter, LethalityResult
from sidequest.agents.subsystems import BankResult
from sidequest.game.creature_core import CreatureCore, EdgePool, Inventory
from sidequest.genre.models.lethality import LethalityPolicy, VerdictsOnZeroEdge
from sidequest.protocol.dispatch import (
    DispatchPackage,
    PlayerDispatch,
    VisibilityTag,
)


def _make_pc(name: str, edge_current: int, edge_max: int = 10) -> CreatureCore:
    return CreatureCore(
        name=name,
        description="A PC.",
        personality="Brave.",
        level=1,
        xp=0,
        inventory=Inventory(),
        statuses=[],
        edge=EdgePool(current=edge_current, max=edge_max, base_max=edge_max),
    )


def _heavy_metal_policy() -> LethalityPolicy:
    return LethalityPolicy(
        genre_key="heavy_metal",
        default_reversibility="permanent",
        verdicts_on_zero_edge=VerdictsOnZeroEdge(pc="dead", npc="dead"),
        soul_md_constraint="genre_truth:lethal_for_this_genre",
        must_narrate="Render the death.",
        must_not_narrate="narrate survival; invent rescue",
    )


def _empty_package(turn_id: str = "turn-1", player_id: str = "alice") -> DispatchPackage:
    return DispatchPackage(
        turn_id=turn_id,
        per_player=[PlayerDispatch(player_id=player_id, raw_action="swing sword")],
        cross_player=[],
        confidence_global=1.0,
        degraded=False,
    )


def test_pc_at_zero_edge_produces_heavy_metal_dead_verdict():
    """Edge.current == 0 → policy.verdicts_on_zero_edge.pc → verdict emitted."""
    arbiter = LethalityArbiter(policy=_heavy_metal_policy())
    pc = _make_pc("Alice", edge_current=0)
    result = arbiter.arbitrate(
        package=_empty_package(player_id="alice"),
        bank_result=BankResult(),
        pc_cores_by_player={"alice": pc},
        npc_cores_by_name={},
    )
    assert isinstance(result, LethalityResult)
    assert len(result.verdicts) == 1
    v = result.verdicts[0]
    assert v.entity == "player:alice"
    assert v.verdict == "dead"
    assert v.reversibility == "permanent"
    assert v.soul_md_constraint == "genre_truth:lethal_for_this_genre"
    assert "Alice" in v.cause


def test_pc_above_zero_edge_produces_no_verdict():
    """Edge.current > 0 → arbiter emits nothing for that PC."""
    arbiter = LethalityArbiter(policy=_heavy_metal_policy())
    pc = _make_pc("Alice", edge_current=5)
    result = arbiter.arbitrate(
        package=_empty_package(player_id="alice"),
        bank_result=BankResult(),
        pc_cores_by_player={"alice": pc},
        npc_cores_by_name={},
    )
    assert result.verdicts == []
    assert result.directives == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_lethality_arbiter.py -v
```
Expected: ImportError — `sidequest.agents.lethality_arbiter` does not exist.

- [ ] **Step 3: Write the arbiter**

```python
# sidequest/agents/lethality_arbiter.py
"""LethalityArbiter — deterministic lethality synthesis (Group C).

Spec: docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md §4

Runs AFTER run_dispatch_bank and BEFORE narrator_directives registration.
Reads:
  - LethalityPolicy (loaded from the active genre pack)
  - Player-character cores (`pc_cores_by_player`)
  - NPC cores present in the scene (`npc_cores_by_name`)
  - BankResult (for future subsystems that emit `data["fatal_hit"]` etc.)

Phase A trigger is edge-based only: any core with `edge.current == 0` fires
the policy's `verdicts_on_zero_edge` entry. Confrontation-beat-failure and
resource-pool-depletion triggers land in Group E when the subsystems that
produce those signals exist on the Python port.

The arbiter is deterministic and synchronous — no LLM call. The decomposer
may still emit `LethalityVerdict` entries in `DispatchPackage.per_player[*].
lethality` for paper-trail purposes; arbiter output is authoritative on
conflict (see Task 9).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sidequest.agents.subsystems import BankResult
from sidequest.game.creature_core import CreatureCore
from sidequest.genre.models.lethality import LethalityPolicy
from sidequest.protocol.dispatch import (
    DispatchPackage,
    LethalityVerdict,
    NarratorDirective,
    VisibilityTag,
)

logger = logging.getLogger(__name__)


@dataclass
class LethalityResult:
    """Arbiter output: authoritative verdicts + paired narrator directives."""

    verdicts: list[LethalityVerdict] = field(default_factory=list)
    directives: list[NarratorDirective] = field(default_factory=list)


class LethalityArbiter:
    """Synthesise lethality verdicts from post-bank state + genre policy."""

    def __init__(self, policy: LethalityPolicy) -> None:
        self._policy = policy

    def arbitrate(
        self,
        *,
        package: DispatchPackage,
        bank_result: BankResult,
        pc_cores_by_player: dict[str, CreatureCore],
        npc_cores_by_name: dict[str, CreatureCore],
    ) -> LethalityResult:
        result = LethalityResult()
        for player_id, core in pc_cores_by_player.items():
            if core.edge.current == 0:
                result.verdicts.append(self._build_verdict(
                    entity=f"player:{player_id}",
                    verdict_kind=self._policy.verdicts_on_zero_edge.pc,
                    cause=(
                        f"{core.name} reduced to zero edge "
                        f"(0/{core.edge.max})"
                    ),
                ))
        for npc_name, core in npc_cores_by_name.items():
            if core.edge.current == 0:
                result.verdicts.append(self._build_verdict(
                    entity=f"npc:{npc_name}",
                    verdict_kind=self._policy.verdicts_on_zero_edge.npc,
                    cause=(
                        f"{core.name} reduced to zero edge "
                        f"(0/{core.edge.max})"
                    ),
                ))
        return result

    def _build_verdict(
        self,
        *,
        entity: str,
        verdict_kind: str,
        cause: str,
    ) -> LethalityVerdict:
        policy = self._policy
        directive = (
            f"{entity} verdict={verdict_kind}. "
            f"{policy.must_narrate} "
            f"Do NOT: {policy.must_not_narrate}"
        )
        return LethalityVerdict(
            entity=entity,
            verdict=verdict_kind,  # type: ignore[arg-type]  # validated against Literal at ctor
            cause=cause,
            reversibility=policy.default_reversibility,
            narrator_directive=directive,
            soul_md_constraint=policy.soul_md_constraint,
            witness_scope={},  # Group G fills this in from VisibilityTag pipeline
        )


__all__ = ["LethalityArbiter", "LethalityResult"]
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/agents/test_lethality_arbiter.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/lethality_arbiter.py tests/agents/test_lethality_arbiter.py
git commit -m "feat(agents): LethalityArbiter PC zero-edge happy path (group C task 5)"
```

---

## Task 6: Arbiter — NPC at zero edge

**Files:**
- Modify: `sidequest-server/tests/agents/test_lethality_arbiter.py` (append)
- (No code change expected — Task 5 already handles NPCs; this task adds the test coverage.)

- [ ] **Step 1: Append the test**

```python
# tests/agents/test_lethality_arbiter.py — APPEND

def _caverns_policy() -> LethalityPolicy:
    return LethalityPolicy(
        genre_key="caverns_and_claudes",
        default_reversibility="narrative_only",
        verdicts_on_zero_edge=VerdictsOnZeroEdge(pc="humiliated", npc="defeated"),
        soul_md_constraint="genre_truth:comedic_danger_no_permadeath",
        must_narrate="Slapstick incapacitation.",
        must_not_narrate="permadeath; solemn eulogy",
    )


def test_npc_at_zero_edge_produces_caverns_defeated_verdict():
    arbiter = LethalityArbiter(policy=_caverns_policy())
    npc = _make_pc("Gobbert", edge_current=0)
    result = arbiter.arbitrate(
        package=_empty_package(),
        bank_result=BankResult(),
        pc_cores_by_player={},
        npc_cores_by_name={"Gobbert": npc},
    )
    assert len(result.verdicts) == 1
    v = result.verdicts[0]
    assert v.entity == "npc:Gobbert"
    assert v.verdict == "defeated"
    assert v.reversibility == "narrative_only"


def test_multiple_entities_at_zero_edge_produce_separate_verdicts():
    arbiter = LethalityArbiter(policy=_caverns_policy())
    alice = _make_pc("Alice", edge_current=0)
    bob = _make_pc("Bob", edge_current=3)
    gobbert = _make_pc("Gobbert", edge_current=0)
    result = arbiter.arbitrate(
        package=_empty_package(),
        bank_result=BankResult(),
        pc_cores_by_player={"alice": alice, "bob": bob},
        npc_cores_by_name={"Gobbert": gobbert},
    )
    entities = sorted(v.entity for v in result.verdicts)
    assert entities == ["npc:Gobbert", "player:alice"]
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/agents/test_lethality_arbiter.py -v
```
Expected: 4 passed (2 from Task 5 + 2 new). No code change needed.

- [ ] **Step 3: Commit**

```bash
git add tests/agents/test_lethality_arbiter.py
git commit -m "test(agents): arbiter NPC + multi-entity coverage (group C task 6)"
```

---

## Task 7: Arbiter — paired `must_narrate` + `must_not_narrate` directives

**Files:**
- Modify: `sidequest-server/sidequest/agents/lethality_arbiter.py`
- Modify: `sidequest-server/tests/agents/test_lethality_arbiter.py` (append)

Until now, Task 5 bakes the `must_narrate` + `must_not_narrate` strings into `LethalityVerdict.narrator_directive` (one field). The narrator's prompt also needs the directives as separate `NarratorDirective` entries so the existing `narrator_directives` PromptSection formatter (Task 11) can render them as distinct list items.

- [ ] **Step 1: Append the failing test**

```python
# tests/agents/test_lethality_arbiter.py — APPEND

def test_arbiter_emits_paired_directives_per_verdict():
    """Spec §4.2: every verdict ships with must_narrate + must_not_narrate."""
    arbiter = LethalityArbiter(policy=_heavy_metal_policy())
    pc = _make_pc("Alice", edge_current=0)
    result = arbiter.arbitrate(
        package=_empty_package(player_id="alice"),
        bank_result=BankResult(),
        pc_cores_by_player={"alice": pc},
        npc_cores_by_name={},
    )
    kinds = [d.kind for d in result.directives]
    assert kinds.count("must_narrate") == 1
    assert kinds.count("must_not_narrate") == 1
    must = next(d for d in result.directives if d.kind == "must_narrate")
    must_not = next(d for d in result.directives if d.kind == "must_not_narrate")
    assert "Render the death" in must.payload
    assert "narrate survival" in must_not.payload


def test_no_directives_when_no_verdicts():
    arbiter = LethalityArbiter(policy=_heavy_metal_policy())
    pc = _make_pc("Alice", edge_current=7)
    result = arbiter.arbitrate(
        package=_empty_package(),
        bank_result=BankResult(),
        pc_cores_by_player={"alice": pc},
        npc_cores_by_name={},
    )
    assert result.directives == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_lethality_arbiter.py::test_arbiter_emits_paired_directives_per_verdict -v
```
Expected: FAIL — Task 5 doesn't emit `result.directives`.

- [ ] **Step 3: Update the arbiter to emit paired directives**

Edit `sidequest/agents/lethality_arbiter.py`. Replace the body of `arbitrate` to append directives when it appends verdicts, and add a helper:

```python
# sidequest/agents/lethality_arbiter.py — patch

    def arbitrate(
        self,
        *,
        package: DispatchPackage,
        bank_result: BankResult,
        pc_cores_by_player: dict[str, CreatureCore],
        npc_cores_by_name: dict[str, CreatureCore],
    ) -> LethalityResult:
        result = LethalityResult()
        for player_id, core in pc_cores_by_player.items():
            if core.edge.current == 0:
                self._emit(result, entity=f"player:{player_id}",
                           verdict_kind=self._policy.verdicts_on_zero_edge.pc,
                           core=core)
        for npc_name, core in npc_cores_by_name.items():
            if core.edge.current == 0:
                self._emit(result, entity=f"npc:{npc_name}",
                           verdict_kind=self._policy.verdicts_on_zero_edge.npc,
                           core=core)
        return result

    def _emit(
        self,
        result: LethalityResult,
        *,
        entity: str,
        verdict_kind: str,
        core: CreatureCore,
    ) -> None:
        cause = f"{core.name} reduced to zero edge (0/{core.edge.max})"
        result.verdicts.append(self._build_verdict(
            entity=entity, verdict_kind=verdict_kind, cause=cause,
        ))
        # Paired directives — narrator reads them as one constraint envelope.
        shared_viz = VisibilityTag(visible_to="all", perception_fidelity={},
                                   secrets_for=[], redact_from_narrator_canonical=False)
        result.directives.append(NarratorDirective(
            kind="must_narrate",
            payload=(
                f"{entity} verdict={verdict_kind}. {self._policy.must_narrate}"
            ),
            visibility=shared_viz,
        ))
        result.directives.append(NarratorDirective(
            kind="must_not_narrate",
            payload=self._policy.must_not_narrate,
            visibility=shared_viz,
        ))
```

(`_build_verdict` can stay as-is; verdict's own `narrator_directive` field still carries the combined string for audit + downstream consumers.)

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/agents/test_lethality_arbiter.py -v
```
Expected: 6 passed (4 existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/lethality_arbiter.py tests/agents/test_lethality_arbiter.py
git commit -m "feat(agents): arbiter emits paired must/must-not directives (group C task 7)"
```

---

## Task 8: Arbiter — merge with decomposer-emitted verdicts

**Files:**
- Modify: `sidequest-server/sidequest/agents/lethality_arbiter.py`
- Modify: `sidequest-server/tests/agents/test_lethality_arbiter.py` (append)

Decision 5 (header): arbiter wins on conflict (same entity). The decomposer may emit a `LethalityVerdict` in `package.per_player[*].lethality` for paper-trail purposes. Arbiter output **replaces** any decomposer entry for the same `entity`. Decomposer-only entries (entities the arbiter did not touch) pass through untouched.

- [ ] **Step 1: Append the failing tests**

```python
# tests/agents/test_lethality_arbiter.py — APPEND

from sidequest.protocol.dispatch import LethalityVerdict


def _decomposer_verdict(entity: str, verdict: str) -> LethalityVerdict:
    return LethalityVerdict(
        entity=entity,
        verdict=verdict,  # type: ignore[arg-type]
        cause="decomposer proposed",
        reversibility="narrative_only",
        narrator_directive="decomposer directive",
        soul_md_constraint="decomposer_constraint",
        witness_scope={},
    )


def test_arbiter_overrides_decomposer_verdict_on_conflict():
    """Arbiter wins when both author a verdict for the same entity."""
    arbiter = LethalityArbiter(policy=_heavy_metal_policy())
    pc = _make_pc("Alice", edge_current=0)
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="alice",
            raw_action="x",
            lethality=[_decomposer_verdict("player:alice", "humiliated")],
        )],
        cross_player=[],
        confidence_global=1.0,
    )
    result = arbiter.arbitrate(
        package=pkg,
        bank_result=BankResult(),
        pc_cores_by_player={"alice": pc},
        npc_cores_by_name={},
    )
    verdicts_for_alice = [v for v in result.verdicts if v.entity == "player:alice"]
    assert len(verdicts_for_alice) == 1
    assert verdicts_for_alice[0].verdict == "dead"  # arbiter wins
    assert "decomposer proposed" not in verdicts_for_alice[0].cause


def test_arbiter_passes_through_decomposer_only_entities():
    """Entity the arbiter did not touch → decomposer verdict preserved."""
    arbiter = LethalityArbiter(policy=_heavy_metal_policy())
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="alice",
            raw_action="x",
            lethality=[_decomposer_verdict("npc:BoneChewer", "maimed")],
        )],
        cross_player=[],
        confidence_global=1.0,
    )
    result = arbiter.arbitrate(
        package=pkg,
        bank_result=BankResult(),
        pc_cores_by_player={},   # no one at zero edge
        npc_cores_by_name={},    # BoneChewer's core not tracked this turn
    )
    assert len(result.verdicts) == 1
    assert result.verdicts[0].entity == "npc:BoneChewer"
    assert result.verdicts[0].verdict == "maimed"
    assert "decomposer proposed" in result.verdicts[0].cause
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_lethality_arbiter.py -v -k "override or pass_through"
```
Expected: both new tests FAIL.

- [ ] **Step 3: Update `arbitrate` to merge**

Insert at the end of `arbitrate`, before `return result`:

```python
        # Merge decomposer-authored verdicts. Arbiter wins on entity conflict;
        # decomposer-only entities pass through.
        arbiter_entities = {v.entity for v in result.verdicts}
        for pd in package.per_player:
            for decomposer_v in pd.lethality:
                if decomposer_v.entity not in arbiter_entities:
                    result.verdicts.append(decomposer_v)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/agents/test_lethality_arbiter.py -v
```
Expected: 8 passed (6 existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/lethality_arbiter.py tests/agents/test_lethality_arbiter.py
git commit -m "feat(agents): arbiter merge-with-decomposer rules (group C task 8)"
```

---

## Task 9: OTEL span for arbitration

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py`
- Modify: `sidequest-server/sidequest/agents/lethality_arbiter.py`
- Test: `sidequest-server/tests/telemetry/test_lethality_span.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/telemetry/test_lethality_span.py
"""OTEL coverage for LethalityArbiter — Sebastien's GM panel reads these."""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.agents.lethality_arbiter import LethalityArbiter
from sidequest.agents.subsystems import BankResult
from sidequest.game.creature_core import CreatureCore, EdgePool, Inventory
from sidequest.genre.models.lethality import LethalityPolicy, VerdictsOnZeroEdge
from sidequest.protocol.dispatch import DispatchPackage, PlayerDispatch
from sidequest.telemetry.spans import SPAN_LOCAL_DM_LETHALITY_ARBITRATE


def _policy() -> LethalityPolicy:
    return LethalityPolicy(
        genre_key="heavy_metal",
        default_reversibility="permanent",
        verdicts_on_zero_edge=VerdictsOnZeroEdge(pc="dead", npc="dead"),
        soul_md_constraint="c",
        must_narrate="x",
        must_not_narrate="y",
    )


def _pc(current: int) -> CreatureCore:
    return CreatureCore(
        name="Alice", description="d", personality="p",
        inventory=Inventory(),
        edge=EdgePool(current=current, max=10, base_max=10),
    )


def test_arbitrate_emits_span_with_verdict_count():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer(__name__)

    arbiter = LethalityArbiter(policy=_policy())
    pkg = DispatchPackage(
        turn_id="t42",
        per_player=[PlayerDispatch(player_id="alice", raw_action="x")],
        cross_player=[],
        confidence_global=1.0,
    )
    arbiter.arbitrate(
        package=pkg, bank_result=BankResult(),
        pc_cores_by_player={"alice": _pc(0)}, npc_cores_by_name={},
        tracer=tracer,
    )

    spans = [s for s in exporter.get_finished_spans()
             if s.name == SPAN_LOCAL_DM_LETHALITY_ARBITRATE]
    assert len(spans) == 1
    span = spans[0]
    assert span.attributes["turn_id"] == "t42"
    assert span.attributes["verdict_count"] == 1
    assert span.attributes["genre_key"] == "heavy_metal"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/telemetry/test_lethality_span.py -v
```
Expected: ImportError — `SPAN_LOCAL_DM_LETHALITY_ARBITRATE` not defined.

- [ ] **Step 3: Add the span constant + helper**

In `sidequest/telemetry/spans.py`, after the existing `SPAN_LOCAL_DM_*` constants:

```python
SPAN_LOCAL_DM_LETHALITY_ARBITRATE = "local_dm.lethality_arbitrate"
```

Locate the `local_dm_decompose_span` context-manager helper and add an equivalent one beneath it:

```python
def lethality_arbitrate_span(
    *,
    turn_id: str,
    genre_key: str,
    tracer: trace.Tracer | None = None,
):
    """Context manager wrapping SPAN_LOCAL_DM_LETHALITY_ARBITRATE.

    Consumed by the GM panel — Sebastien needs to see that the arbiter ran
    and how many verdicts it produced.
    """
    t = tracer if tracer is not None else trace.get_tracer(__name__)
    return t.start_as_current_span(
        SPAN_LOCAL_DM_LETHALITY_ARBITRATE,
        attributes={
            "turn_id": turn_id,
            "genre_key": genre_key,
        },
    )
```

(Match the exact import + helper style the file already uses for `local_dm_decompose_span`.)

- [ ] **Step 4: Wire the span into the arbiter**

Edit `sidequest/agents/lethality_arbiter.py`:

```python
# Imports — ADD
from opentelemetry import trace

from sidequest.telemetry.spans import lethality_arbitrate_span
```

Update the `arbitrate` signature and body:

```python
    def arbitrate(
        self,
        *,
        package: DispatchPackage,
        bank_result: BankResult,
        pc_cores_by_player: dict[str, CreatureCore],
        npc_cores_by_name: dict[str, CreatureCore],
        tracer: trace.Tracer | None = None,
    ) -> LethalityResult:
        with lethality_arbitrate_span(
            turn_id=package.turn_id,
            genre_key=self._policy.genre_key,
            tracer=tracer,
        ) as span:
            result = LethalityResult()
            # ... existing body unchanged ...
            span.set_attribute("verdict_count", len(result.verdicts))
            return result
```

(Keep all the existing logic inside the `with` block; only the enter/exit + `verdict_count` attribute are new.)

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/telemetry/test_lethality_span.py tests/agents/test_lethality_arbiter.py -v
```
Expected: all pass (arbiter tests unaffected — `tracer` defaults to `None`).

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/spans.py sidequest/agents/lethality_arbiter.py tests/telemetry/test_lethality_span.py
git commit -m "feat(telemetry): SPAN_LOCAL_DM_LETHALITY_ARBITRATE (group C task 9)"
```

---

## Task 10: Wire arbiter into `orchestrator.build_narrator_prompt`

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py`
- Test: `sidequest-server/tests/agents/test_lethality_directives_in_prompt.py`

The arbiter runs after `run_dispatch_bank` (which already happens at `orchestrator.py:~1140`). Its directives get merged into the same `narrator_directives` PromptSection that bank directives go into — narrator sees one unified block at `AttentionZone.Recency`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/test_lethality_directives_in_prompt.py
"""End-to-end: arbiter's directives land in the narrator prompt.

Verifies the paired must_narrate / must_not_narrate lines appear in the
narrator_directives section produced by build_narrator_prompt when a PC
is at zero edge.
"""
from __future__ import annotations

import pytest

from sidequest.agents.orchestrator import NarratorContext, build_narrator_prompt
from sidequest.game.creature_core import CreatureCore, EdgePool, Inventory
from sidequest.genre.models.lethality import LethalityPolicy, VerdictsOnZeroEdge
from sidequest.protocol.dispatch import (
    DispatchPackage,
    PlayerDispatch,
)


pytestmark = pytest.mark.asyncio


def _policy() -> LethalityPolicy:
    return LethalityPolicy(
        genre_key="heavy_metal",
        default_reversibility="permanent",
        verdicts_on_zero_edge=VerdictsOnZeroEdge(pc="dead", npc="dead"),
        soul_md_constraint="genre_truth:lethal_for_this_genre",
        must_narrate="Render the death with specific brutal detail.",
        must_not_narrate="invent rescue; narrate survival",
    )


def _pc(current: int) -> CreatureCore:
    return CreatureCore(
        name="Alice", description="d", personality="p",
        inventory=Inventory(),
        edge=EdgePool(current=current, max=10, base_max=10),
    )


async def test_pc_at_zero_edge_injects_paired_directives_in_prompt(
    minimal_narrator_context_factory,  # fixture from tests/agents/conftest.py
):
    ctx: NarratorContext = minimal_narrator_context_factory(
        dispatch_package=DispatchPackage(
            turn_id="t1",
            per_player=[PlayerDispatch(player_id="alice", raw_action="swing")],
            cross_player=[],
            confidence_global=1.0,
        ),
        lethality_policy=_policy(),
        pc_cores_by_player={"alice": _pc(0)},
        character_name="Alice",
        action="swing sword",
    )
    prompt = await build_narrator_prompt(ctx)
    # Arbiter should have produced a verdict + paired directives; they land in
    # the narrator_directives section alongside any bank-authored directives.
    assert "must_narrate" in prompt
    assert "Render the death" in prompt
    assert "must_not_narrate" in prompt
    assert "narrate survival" in prompt


async def test_pc_above_zero_edge_injects_no_lethality_directives(
    minimal_narrator_context_factory,
):
    ctx: NarratorContext = minimal_narrator_context_factory(
        dispatch_package=DispatchPackage(
            turn_id="t1",
            per_player=[PlayerDispatch(player_id="alice", raw_action="swing")],
            cross_player=[],
            confidence_global=1.0,
        ),
        lethality_policy=_policy(),
        pc_cores_by_player={"alice": _pc(7)},
        character_name="Alice",
        action="swing sword",
    )
    prompt = await build_narrator_prompt(ctx)
    assert "Render the death" not in prompt
```

The fixture `minimal_narrator_context_factory` may not yet exist. If not, add it to `tests/agents/conftest.py` as a callable that returns a `NarratorContext` with the minimum fields set — copy the shape from the existing Group B narrator-prompt tests (see `tests/agents/test_build_narrator_prompt.py` or equivalent). It must accept `dispatch_package`, `lethality_policy`, `pc_cores_by_player`, `character_name`, and `action` kwargs.

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_lethality_directives_in_prompt.py -v
```
Expected: FAIL — `NarratorContext` has no `lethality_policy` or `pc_cores_by_player`.

- [ ] **Step 3: Extend `NarratorContext`**

In `sidequest/agents/orchestrator.py`, locate the `NarratorContext` dataclass (around the existing `dispatch_package: DispatchPackage | None` field) and add:

```python
    # Group C — lethality arbiter inputs. When both are non-None, the
    # arbiter runs after run_dispatch_bank and its directives are merged
    # into the narrator_directives section.
    lethality_policy: "LethalityPolicy | None" = None
    pc_cores_by_player: dict[str, "CreatureCore"] = field(default_factory=dict)
    npc_cores_by_name: dict[str, "CreatureCore"] = field(default_factory=dict)
```

(Add the imports with `TYPE_CHECKING` or at module top — match the existing style.)

- [ ] **Step 4: Run the arbiter in `build_narrator_prompt`**

Immediately after the `run_dispatch_bank` block (orchestrator.py ~line 1140), and before the `if bank_result.directives:` block that writes the `narrator_directives` PromptSection, append:

```python
            # Group C — lethality arbitration runs after the bank and
            # before the narrator_directives section is registered, so the
            # arbiter's paired directives join the bank directives in the
            # same high-attention block.
            arbiter_directives: list[NarratorDirective] = []
            arbiter_verdicts: list[LethalityVerdict] = []
            if (
                context.lethality_policy is not None
                and visible_dispatch_package is not None
            ):
                from sidequest.agents.lethality_arbiter import LethalityArbiter

                arbiter = LethalityArbiter(policy=context.lethality_policy)
                l_result = arbiter.arbitrate(
                    package=visible_dispatch_package,
                    bank_result=bank_result,
                    pc_cores_by_player=context.pc_cores_by_player,
                    npc_cores_by_name=context.npc_cores_by_name,
                )
                arbiter_directives = l_result.directives
                arbiter_verdicts = l_result.verdicts

            combined_directives = list(bank_result.directives) + arbiter_directives
            if combined_directives:
                block = "\n".join(
                    f"- [{d.kind}] {d.payload}" for d in combined_directives
                )
                registry.register_section(
                    agent_name,
                    PromptSection.new(
                        "narrator_directives",
                        block,
                        AttentionZone.Recency,
                        SectionCategory.State,
                    ),
                )
```

Then delete the original `if bank_result.directives:` block immediately below (the one you are replacing) — keep the subsequent `for key, err in bank_result.errors:` logging loop as-is.

Add `LethalityVerdict` to the existing `from sidequest.protocol.dispatch import ...` line at the top of the file if not already imported.

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/agents/test_lethality_directives_in_prompt.py tests/agents/test_lethality_arbiter.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_lethality_directives_in_prompt.py tests/agents/conftest.py
git commit -m "feat(orchestrator): run LethalityArbiter after dispatch bank (group C task 10)"
```

---

## Task 11: Session handler populates lethality context

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Test: `sidequest-server/tests/server/test_session_lethality_context.py`

The orchestrator can now consume `NarratorContext.lethality_policy` + `pc_cores_by_player`, but nobody populates them yet. Session handler has the genre pack + character(s) already in scope at prompt-build time; it just needs to pass them through.

- [ ] **Step 1: Write the failing wiring test**

```python
# tests/server/test_session_lethality_context.py
"""Wiring: session handler loads genre pack's lethality_policy onto NarratorContext."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_session_narrator_context_carries_lethality_policy(
    session_fixture,  # existing fixture from tests/server/conftest.py (Group B)
):
    """After session open, running a turn builds a NarratorContext whose
    `lethality_policy` is the loaded pack's policy — not None."""
    sd = session_fixture  # caverns_and_claudes fixture pack
    ctx = await sd.build_narrator_context_for_test()  # helper added in this task
    assert ctx.lethality_policy is not None
    assert ctx.lethality_policy.genre_key == sd.genre_pack_key
```

If no such helper exists, either (a) add `build_narrator_context_for_test` to `_SessionData` exposing the same `NarratorContext` the prod path builds, or (b) rewrite the test to exercise `_execute_narration_turn` with a mocked narrator and introspect the captured context (Group B test pattern). Pick whichever is less invasive in the existing fixture.

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/server/test_session_lethality_context.py -v
```
Expected: FAIL — `lethality_policy` is None.

- [ ] **Step 3: Populate the context**

In `sidequest/server/session_handler.py`, find where `NarratorContext` is constructed on the turn path (the same site that already sets `dispatch_package`). Add:

```python
        # Group C — lethality arbiter inputs. Policy is pack-level; cores come
        # from the live snapshot for every PC at the table plus any NPC whose
        # edge pool touched zero this turn.
        lethality_policy = getattr(sd.genre_pack, "lethality_policy", None)

        pc_cores_by_player: dict[str, CreatureCore] = {}
        for player_id, character in sd.characters_by_player.items():
            pc_cores_by_player[player_id] = character.core

        npc_cores_by_name: dict[str, CreatureCore] = {}
        for npc in snapshot.iter_scene_npcs():  # use the correct snapshot accessor
            npc_cores_by_name[npc.core.name] = npc.core
```

(Adjust the field/accessor names — `sd.characters_by_player`, `snapshot.iter_scene_npcs` — to whatever the Python port uses. Grep for an existing site that iterates characters + NPCs and copy the pattern.)

Then pass these three into the `NarratorContext(...)` constructor call:

```python
        ctx = NarratorContext(
            # ... existing kwargs ...
            dispatch_package=dispatch_package,
            lethality_policy=lethality_policy,
            pc_cores_by_player=pc_cores_by_player,
            npc_cores_by_name=npc_cores_by_name,
        )
```

Add the `CreatureCore` import at module top if not already present.

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/server/test_session_lethality_context.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/session_handler.py tests/server/test_session_lethality_context.py
git commit -m "feat(session): populate lethality context on NarratorContext (group C task 11)"
```

---

## Task 12: Integration — full turn with PC at zero edge emits verdict + directives

**Files:**
- Create: `sidequest-server/tests/integration/test_group_c_e2e.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_group_c_e2e.py
"""Group C end-to-end: a turn with a PC at zero edge produces a verdict and
injects paired must_narrate / must_not_narrate directives into the narrator
prompt. Narrator is mocked; the assertion is on the prompt it received.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sidequest.protocol.dispatch import (
    DispatchPackage,
    PlayerDispatch,
    PerceptionFidelity,  # noqa: F401
    VisibilityTag,
)


pytestmark = pytest.mark.asyncio


@patch("sidequest.agents.local_dm.LocalDM.decompose")
async def test_zero_edge_pc_produces_lethality_directives_end_to_end(
    mock_decompose: AsyncMock,
    session_fixture_mutant_wasteland,   # mutant_wasteland is lethal_for_this_genre
):
    """PC at edge.current=0 → arbiter emits 'dead' verdict + narrator directives."""
    sd = session_fixture_mutant_wasteland
    alice = sd.characters_by_player["alice"]
    alice.core.edge.current = 0  # drop the PC to zero before the turn runs

    # Decomposer returns an empty happy-path DispatchPackage (no suggested
    # verdict — arbiter fills one in).
    mock_decompose.return_value = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(player_id="alice", raw_action="block the beast")],
        cross_player=[],
        confidence_global=1.0,
    )

    captured_prompts: list[str] = []

    async def _capture(prompt: str, **kwargs):
        captured_prompts.append(prompt)
        return ("prose", {})  # match the narrator's return shape

    with patch("sidequest.agents.narrator.Narrator.narrate", side_effect=_capture):
        await sd.execute_narration_turn(player_id="alice", action="block the beast")

    assert captured_prompts, "narrator was never called"
    prompt = captured_prompts[0]
    # Arbiter output: must_narrate + must_not_narrate are present in the
    # narrator_directives section.
    assert "must_narrate" in prompt
    assert "must_not_narrate" in prompt
    # Policy text surfaces (mutant_wasteland):
    assert "wasteland is indifferent" in prompt or "genre-true terms" in prompt
    assert "miraculous rescues" in prompt
```

Adjust fixture names (`session_fixture_mutant_wasteland`) to match the existing Group B integration test patterns in `tests/server/test_execute_narration_turn*.py` or `tests/integration/`. If the existing fixtures default to a single pack, parametrise it to also load mutant_wasteland.

- [ ] **Step 2: Run test to verify the expected path**

```bash
uv run pytest tests/integration/test_group_c_e2e.py -v
```
Expected: PASS. If the fixture doesn't exist yet, add it (lift from Group B's session fixture — same pack load, but key on `mutant_wasteland`).

- [ ] **Step 3: Add a second genre for breadth**

Append a second test using `caverns_and_claudes` to verify comedic-verdict text reaches the prompt:

```python
@patch("sidequest.agents.local_dm.LocalDM.decompose")
async def test_zero_edge_pc_in_caverns_produces_comedic_verdict(
    mock_decompose: AsyncMock,
    session_fixture_caverns,
):
    sd = session_fixture_caverns
    sd.characters_by_player["alice"].core.edge.current = 0
    mock_decompose.return_value = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(player_id="alice", raw_action="retreat")],
        cross_player=[],
        confidence_global=1.0,
    )
    captured: list[str] = []
    async def _cap(prompt, **k):
        captured.append(prompt); return ("p", {})
    with patch("sidequest.agents.narrator.Narrator.narrate", side_effect=_cap):
        await sd.execute_narration_turn(player_id="alice", action="retreat")
    p = captured[0]
    assert "slapstick" in p or "one-liner" in p
    assert "permadeath" in p  # must_not_narrate text surfaces
```

- [ ] **Step 4: Run both tests**

```bash
uv run pytest tests/integration/test_group_c_e2e.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_group_c_e2e.py
git commit -m "test(integration): group C e2e — zero-edge PC → directives (task 12)"
```

---

## Task 13: Per-genre smoke tests — all six packs

**Files:**
- Create: `sidequest-server/tests/genre/test_lethality_policy_per_pack.py`

Spec §10 Group C: "Per-genre smoke tests: PC at HP 0 in each pack produces genre-appropriate verdict shape." This is the deterministic version of that — load each shipped pack, feed a zero-edge PC, assert the verdict matches the pack's policy.

- [ ] **Step 1: Write the parametrised smoke test**

```python
# tests/genre/test_lethality_policy_per_pack.py
"""Per-pack smoke: load each shipped genre pack's lethality_policy and run
the arbiter on a PC at zero edge. Each pack must produce a verdict whose
kind matches its declared policy.verdicts_on_zero_edge.pc.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.agents.lethality_arbiter import LethalityArbiter
from sidequest.agents.subsystems import BankResult
from sidequest.game.creature_core import CreatureCore, EdgePool, Inventory
from sidequest.genre.lethality_policy_loader import load_lethality_policy
from sidequest.protocol.dispatch import DispatchPackage, PlayerDispatch


SHIPPED_PACKS = [
    "caverns_and_claudes",
    "elemental_harmony",
    "heavy_metal",
    "mutant_wasteland",
    "space_opera",
    "spaghetti_western",
]


def _pc(current: int) -> CreatureCore:
    return CreatureCore(
        name="Alice", description="d", personality="p",
        inventory=Inventory(),
        edge=EdgePool(current=current, max=10, base_max=10),
    )


@pytest.mark.parametrize("pack_name", SHIPPED_PACKS)
def test_zero_edge_pc_produces_policy_declared_verdict(pack_name: str):
    pack_dir = Path("sidequest-content/genre_packs") / pack_name
    policy = load_lethality_policy(pack_dir)
    arbiter = LethalityArbiter(policy=policy)
    result = arbiter.arbitrate(
        package=DispatchPackage(
            turn_id="t1",
            per_player=[PlayerDispatch(player_id="alice", raw_action="x")],
            cross_player=[],
            confidence_global=1.0,
        ),
        bank_result=BankResult(),
        pc_cores_by_player={"alice": _pc(0)},
        npc_cores_by_name={},
    )
    assert len(result.verdicts) == 1, f"pack={pack_name} produced 0 or >1 verdicts"
    v = result.verdicts[0]
    assert v.verdict == policy.verdicts_on_zero_edge.pc
    assert v.reversibility == policy.default_reversibility
    assert v.soul_md_constraint == policy.soul_md_constraint
    # Paired directives present.
    kinds = [d.kind for d in result.directives]
    assert "must_narrate" in kinds
    assert "must_not_narrate" in kinds


@pytest.mark.parametrize("pack_name", SHIPPED_PACKS)
def test_pack_policy_files_load_without_error(pack_name: str):
    """Lightweight load check — catches YAML drift before integration runs."""
    pack_dir = Path("sidequest-content/genre_packs") / pack_name
    policy = load_lethality_policy(pack_dir)
    assert policy.genre_key == pack_name
    assert policy.must_narrate.strip()
    assert policy.must_not_narrate.strip()
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/genre/test_lethality_policy_per_pack.py -v
```
Expected: 12 passed (6 packs × 2 tests).

If any pack fails because its YAML has a typo, fix the YAML in the sidequest-content branch (Task 3) and re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/genre/test_lethality_policy_per_pack.py
git commit -m "test(genre): per-pack lethality smoke for all six shipped packs (group C task 13)"
```

---

## Task 14: Wiring test — full session load + turn path exercises arbiter

**Files:**
- Create: `sidequest-server/tests/integration/test_group_c_wiring.py`

Per CLAUDE.md "Every Test Suite Needs a Wiring Test": prove the arbiter isn't just unit-tested in isolation, it's actually reachable from a real session-open → turn-execute path.

- [ ] **Step 1: Write the wiring test**

```python
# tests/integration/test_group_c_wiring.py
"""Wiring: opening a session and running a turn exercises the arbiter code path.

Does NOT mock the arbiter. Does NOT mock run_dispatch_bank. Mocks only the
narrator (to avoid a real `claude -p` subprocess) and the decomposer
(to keep the test hermetic).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sidequest.agents.lethality_arbiter import LethalityArbiter
from sidequest.protocol.dispatch import DispatchPackage, PlayerDispatch


pytestmark = pytest.mark.asyncio


@patch("sidequest.agents.local_dm.LocalDM.decompose")
async def test_open_session_then_turn_invokes_arbiter(
    mock_decompose: AsyncMock,
    session_fixture_caverns,
):
    """Proves arbiter is reachable from the real session-handler path."""
    sd = session_fixture_caverns
    sd.characters_by_player["alice"].core.edge.current = 0
    mock_decompose.return_value = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(player_id="alice", raw_action="x")],
        cross_player=[],
        confidence_global=1.0,
    )

    # Spy on the real arbiter class to confirm it was invoked.
    original_arbitrate = LethalityArbiter.arbitrate
    calls: list[tuple] = []

    def _spy(self, **kwargs):
        calls.append((self, kwargs))
        return original_arbitrate(self, **kwargs)

    with patch("sidequest.agents.narrator.Narrator.narrate",
               new=AsyncMock(return_value=("prose", {}))):
        with patch.object(LethalityArbiter, "arbitrate", _spy):
            await sd.execute_narration_turn(player_id="alice", action="x")

    assert len(calls) == 1, "arbiter was not invoked on the real turn path"
```

- [ ] **Step 2: Run the wiring test**

```bash
uv run pytest tests/integration/test_group_c_wiring.py -v
```
Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_group_c_wiring.py
git commit -m "test(wiring): arbiter runs on real session turn path (group C task 14)"
```

---

## Task 15: Full suite, lint, push, open server PR

**Files:** none (ship-only)

- [ ] **Step 1: Run the full server suite**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
just server-test 2>&1 | tail -10
```
Expected: all pass. Compare pass-count to the Task 0 baseline; net delta is the number of Group C tests added (expect +20 to +30).

- [ ] **Step 2: Run lint**

```bash
just server-lint 2>&1 | tail -20
```
Expected: clean. Fix before proceeding — do not push a red ruff run.

- [ ] **Step 3: Verify the content PR has merged**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git fetch origin
git log origin/main --oneline | head -3
```
Expected: the Task 3 commit is on `main`. If not, STOP — wait for the content PR to merge, because your server CI will fail on missing `lethality_policy.yaml` otherwise.

- [ ] **Step 4: Push server branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-c
git push -u origin feat/local-dm-group-c
```

- [ ] **Step 5: Open server PR against develop**

```bash
gh pr create --base develop --title "feat(local-dm): group C — lethality arbitration" --body "$(cat <<'EOF'
## Summary

Ships Local DM **Group C — Lethality Arbitration**. The narrator no longer
decides whether a character dies; the `LethalityArbiter` synthesises a
deterministic verdict from game state + per-genre `lethality_policy` and
hands the narrator a `must_narrate` / `must_not_narrate` constraint envelope.

### What landed

- `LethalityPolicy` pydantic model + strict YAML loader (spec §4.4, §10)
- `lethality_policy.yaml` for all six shipped packs (content PR merged separately)
- `LethalityArbiter` — deterministic, edge-based trigger, runs post-bank
- Decomposer / arbiter merge rule: arbiter wins on entity conflict
- OTEL span `local_dm.lethality_arbitrate` — Sebastien's GM panel reads this
- Paired `must_narrate` + `must_not_narrate` directives join `narrator_directives`
  at `AttentionZone.Recency`
- Per-genre smoke tests asserting each pack's declared verdict shape
- Wiring test proving arbiter is reachable from a real session turn path

### Non-goals

- No LLM-backed arbiter (decision §4.1 applied to the decomposer too)
- No HP-system rewrite — edge-based triggers only
- No `LethalityVerdict` schema changes — `witness_scope` stays `dict`
- No multiplayer fan-out — Group G owns per-player projection

### Depends on

- Group B (merged PR #29)
- sidequest-content PR for `lethality_policy.yaml` (merged first)

### Test plan

- [x] `just server-test` green
- [x] `just server-lint` clean
- [x] Per-genre smoke (6 packs × 2 tests = 12) passes
- [x] Wiring test confirms arbiter runs on the session turn path
- [x] Integration test: PC at zero edge → `must_narrate` / `must_not_narrate`
      land in the captured narrator prompt for mutant_wasteland AND
      caverns_and_claudes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Print PR URL for the session handoff**

`gh pr view --json url -q .url` — paste the URL into the session assessment for the Reviewer's pickup.

---

## Self-Review Checklist (run before handing off to Reviewer)

**Spec §10 Group C coverage:**

- [x] Add `LethalityVerdict` to DispatchPackage contract — already shipped in Group B; no schema change needed
- [x] Build verdict producer that consumes HP/confrontation/roll-outcome subsystem outputs — Task 5/6/7/8 (edge-based Phase A; spec explicitly allows deferral of confrontation-beat + resource-pool triggers to future groups via §4.2 "consumes deterministic subsystem outputs (HP deltas, confrontation beat failures, resource pool depletion...)" — Group C implements HP/edge deltas; subsystem hooks are left for Group E)
- [x] Wire `narrator_directive` injection with `must_narrate` and `must_not_narrate` semantics — Task 7 + Task 10
- [x] Genre packs: add `lethality_policy` YAML field read by the verdict producer — Task 1 + Task 2 + Task 3 + Task 4
- [x] Per-genre smoke tests: PC at HP 0 in each pack produces genre-appropriate verdict shape — Task 13

**Principles check:**

- [x] No silent fallbacks — loader raises on missing file + genre_key mismatch
- [x] No stubbing — every task ships a testable, reachable piece
- [x] Wiring verified — Task 14 exercises the real session path
- [x] OTEL emitted — Task 9 gives the GM panel the verdict count + genre
- [x] Every subsystem that can lie has a lie detector — arbiter overrides LLM proposals (Task 8)

**Known deferrals (documented, not hidden):**

- Confrontation-beat-failure triggers → Group E (subsystems don't exist yet)
- Resource-pool-depletion triggers → Group E (same)
- Roll-outcome triggers → Group E (ADR-074 not landed)
- `WitnessScope` typed model → deferred; Group G will upgrade when it consumes the field
- GM-panel override UI → already exists via post-turn override flow; Group C doesn't touch it

---

End of plan.
