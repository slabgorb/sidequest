# Neon Dystopia → CWN Hacking-as-Confrontation (`net_run`)

**Date:** 2026-05-29
**Status:** Design — approved, pending spec review
**Author:** GM (with Keith)
**Series:** Plan 4 of 4 in the neon_dystopia → CWN binding. Builds on the merged
foundation (plan 1), System Strain (plan 2), and combat lethality (plan 3).

## Summary

Implement the **hacking-as-confrontation** section of the CWN ruleset design
(`docs/superpowers/specs/2026-05-28-neon-cwn-ruleset-design.md`, §"Hacking — a
CWN-flavored confrontation"). Replace the legacy dial confrontation `net_combat`
with a CWN-faithful **`net_run`**: a dial-based confrontation whose beats map to
CWN cyberspace Verbs, resolved as **Tech (INT) + Program vs a security-level DC**,
with a network-alert opponent metric. Add a `CwnRulesetModule.resolve_hacking`
engine method and a `cwn.hacking.security_check` OTEL span (the GM-panel
lie-detector for the hacking subsystem), fired by a dispatch seam — mirroring the
Trauma/Shock/Mortal-Injury seams shipped in plan 3.

This is the last of the three cyberpunk engine additions (System Strain,
Trauma/Shock lethality, hacking) the ruleset spec called for. It serves the
playgroup's two mechanics-first players (Sebastien, Jade) by making the security
DC and the Program check legible in the player-facing surface.

## Motivation

`neon_dystopia` currently models hacking as `net_combat` — a momentum dial with
`extraction`/`trace` metrics and `Tech` checks, but **no security-level concept,
no CWN Verb vocabulary, and no OTEL span**. There is no way for the GM panel to
verify the hacking subsystem engaged versus the narrator improvising a hack
("you're in — you slice through the ICE"). CWN supplies a coherent model:
cyberspace actions are skill checks against a difficulty that scales with the
target system's security, and the network fights back by raising an alert/trace
that, on completion, ends the run badly. We adopt that model as a confrontation —
no bespoke cyberspace minigame.

## Decisions (locked in brainstorming)

| Fork | Decision |
|---|---|
| Resolution shape | Dial-based confrontation (NOT HP/AC). `player_metric` = objective progress; `opponent_metric` = network alert/trace; opponent threshold reached = CWN "Alert the Network ×2" loss (reuse `dial_threshold`, no new win condition). |
| Resolution path | **2d6 + Program + INT vs the security DC**, via the ruleset's existing `check_params` (the CWN-faithful skill-check shape), NOT the d20 `attack_params` path combat uses. The dice lib already resolves arbitrary pools — this *selects* the 2d6 shape, it does not build a new resolver. CWN's published security ratings (7–12) are correct as a 2d6 difficulty. |
| Security DC — per scene | **Narrator-set at runtime** from a default. One `net_run` def; the narrator picks the security level when the run opens. |
| Security DC — source | **Named ladder** authored in content (`cwn.hacking.security_tiers`: home/office/facility/black_site → 7/9/11/12). Narrator picks a tier *by name*; engine maps tier → DC. Tier label + DC ride the span and the player surface. |
| Alert coupling | Each network-alert escalation adds **+1** to the effective DC (the CWN situational modifier). |
| Span + engine | `CwnRulesetModule.resolve_hacking(...)` emits `cwn.hacking.security_check` per resolved verb. Dispatch seam fires it when the active confrontation is `net_run` under `ruleset: cwn` (Trauma/Shock precedent). |
| `opposed_check` | **Not needed.** Static security DC → `beat_selection`. Plan-3 follow-up #2 (opposed_check dispatch seams) stays moot for neon. |
| Migration | `net_combat` is **replaced** by `net_run` (rip-and-rebuild; no saves to preserve). |

## Architecture

### `cwn.hacking` config (content + model)

`CwnConfig` (in `sidequest-server/sidequest/genre/models/rules.py`) gains a
`hacking: HackingConfig | None` sub-model:

```python
class HackingConfig(BaseModel):
    model_config = {"extra": "forbid"}
    default_tier: str
    security_tiers: dict[str, int]  # tier name -> DC

    @model_validator(mode="after")
    def _validate(self) -> "HackingConfig":
        if not self.security_tiers:
            raise ValueError("cwn.hacking.security_tiers must be non-empty")
        if self.default_tier not in self.security_tiers:
            raise ValueError(
                f"cwn.hacking.default_tier {self.default_tier!r} "
                f"not in security_tiers {sorted(self.security_tiers)}"
            )
        return self
```

Authored in `neon_dystopia/rules.yaml`:

```yaml
cwn:
  # ... existing attribute_map, system_strain, trauma ...
  hacking:
    default_tier: office
    security_tiers: { home: 7, office: 9, facility: 11, black_site: 12 }
```

`default_tier` is an **authored default**, used when the narrator opens a run
without naming a tier — a declared fallback in content, not a silent code
fallback (honors "No Silent Fallbacks").

### Per-instance security tier on the running confrontation

`StructuredEncounter` (`sidequest/game/encounter.py`) gains:

```python
security_tier: str | None = None  # net_run only; stamped at instantiation
```

It is stamped at confrontation open the same way `win_condition` is stamped from
the `ConfrontationDef`:

- `run_confrontation_dispatch` (`sidequest/agents/subsystems/confrontation.py`)
  reads an optional `dispatch.params["security_tier"]` (the narrator/IntentRouter
  supplies it when classifying "jack into the corp black site") and passes it to
  `instantiate_encounter_from_trigger`.
- `instantiate_encounter_from_trigger` (encounter lifecycle) sets
  `StructuredEncounter.security_tier` to the supplied tier, or to the pack's
  `cwn.hacking.default_tier` when omitted. An unknown tier name (not in the
  ladder) **fails loud** — same posture as an unknown `encounter_type`.

The effective DC at resolution time =
`security_tiers[security_tier] + alert_modifier`, where `alert_modifier` is
derived from the opponent (alert/trace) metric's current escalation (see below).

### `CwnRulesetModule.resolve_hacking`

New method on `CwnRulesetModule` (`sidequest/game/ruleset/cwn.py`):

```python
def resolve_hacking(
    self,
    *,
    verb: str,            # the beat id/label (Run Program, Spoof, Move Nodes, Jack Out)
    tier: str,            # the named security tier (e.g. "black_site")
    base_dc: int,         # security_tiers[tier]
    alert_modifier: int,  # +1 per alert escalation
    outcome: str,         # the resolved RollOutcome tier (crit_fail..crit_success)
    actor: str = "",
    _tracer: trace.Tracer | None = None,
) -> int:
    """Record a CWN cyberspace security check. Returns the effective DC
    (base_dc + alert_modifier). Emits cwn.hacking.security_check — the GM
    lie-detector for the hacking subsystem; fires on EVERY net_run verb so
    the panel sees engaged + unengaged rolls alike."""
```

It computes `effective_dc = base_dc + alert_modifier`, emits the span, and
returns `effective_dc`. It does **not** itself mutate metrics or roll the dice —
the net_run seam builds the 2d6 check request (next section) whose `difficulty`
is this `effective_dc`, the dice lib resolves the throw to a tier, and the
confrontation engine applies the beat's tier deltas to the dials as usual. This
method is the CWN-specific record + DC computation, consistent with how
`resolve_shock`/`resolve_trauma` are thin record-and-compute methods over the
inherited resolution.

### Resolution: the 2d6 check path (composed from the dice lib)

The dice lib already supplies every primitive net_run needs; nothing here is a
new resolver:

- `CheckRollParams` (`ruleset/resolution.py`) already models a `sides=6, count=2`
  pool + modifier + difficulty — the CWN skill-check shape.
- `DiceRequestPayload` (`protocol/dice.py`) already carries an arbitrary
  `DieSpec` **pool** (`[{sides: 6, count: 2}]`), a `modifier`, and the target
  `difficulty`; the physics overlay (ADR-074/075) throws whatever pool the
  request names, so a 2d6 hacking throw is first-class.
- `resolve_dice_with_faces` (`game/dice.py`) already resolves *any* pool vs a
  difficulty into a `RollOutcome` tier — 2d6 crits via `DECISIVE_MARGIN`, d20 via
  nat-20/nat-1. A 2d6 check needs no new tiering code.

So the net_run dispatch seam, instead of calling `attack_params` (d20 vs AC),
calls the ruleset's **`check_params`** to build a 2d6 request with
`modifier = INT mod + Program skill` and `difficulty = effective_dc` (from
`resolve_hacking`), then feeds it through the same `resolve_dice_with_faces` the
combat path uses. The **only** new wiring is the branch that selects the check
shape for `net_run` — today's `dispatch_dice_throw` hardcodes `attack_params`
(`dice.py:297-304`). (Note: `swn.check_params` maps a `difficulty_key` →
`cfg.difficulties[...]`; net_run passes the security DC as the difficulty
*directly*, bypassing the keyed ladder, since the tier→DC mapping is the
`cwn.hacking` ladder, not the generic difficulty band.)

### OTEL span

`sidequest/telemetry/spans/cwn.py` gains:

- `SPAN_CWN_HACKING_SECURITY_CHECK = "cwn.hacking.security_check"`
- a `SPAN_ROUTES[...]` entry (`event_type="state_transition"`, `component="cwn"`)
  extracting `{field: "hacking", actor, verb, tier, base_dc, alert_modifier,
  effective_dc, result}`.
- `cwn_hacking_security_check_span(*, actor, verb, tier, base_dc,
  alert_modifier, effective_dc, result, _tracer=None, **attrs)`.

### Dispatch seam

In the confrontation/dice resolution path (`sidequest/server/dispatch/dice.py`,
sibling to the existing CWN strike/shock/downed seams), after a beat's check
resolves: when `ruleset` is `cwn` **and** the active `StructuredEncounter` is a
`net_run` (encounter_type == "net_run"), call `ruleset.resolve_hacking(...)` with
the beat's verb, the encounter's `security_tier`, the ladder DC, the alert
modifier, and `resolved.outcome`. The seam reads `cwn.hacking.security_tiers` off
the pack's `CwnConfig` to resolve `base_dc`; a `net_run` under `cwn` whose
`security_tier` is unset or unknown fails loud (config/router bug, not a
recoverable choice). No-op for native/swn (those rulesets' `resolve_hacking`
base returns the DC without emitting — see below).

`RulesetModule.resolve_hacking` base (in `base.py`) is a no-emit default that
simply returns `base_dc + alert_modifier` (parallels the base `resolve_shock`
returning 0). Only `cwn` emits the span.

### Beats → CWN Verbs

`net_run` confrontation in `neon_dystopia/rules.yaml` (replaces `net_combat`):

| Beat (verb) | `kind` | Engine effect |
|---|---|---|
| **Run Program** | `strike` | Offensive Verb — advance objective progress (`player_metric`); failure spikes alert (`opponent_metric`) via a `fail` delta. (NOT `crit_fail`: a 2d6 Program check never yields `RollOutcome.CritFail` — that tier is d20-nat-1 only — so the spike must ride `fail`.) |
| **Spoof / Unlock Barrier** | `brace` | Reduce alert / open a path — drops the opponent (alert) metric. |
| **Move Nodes** | `strike` | Advance objective progress toward extraction (incremental data advance — NOT a `push`, which would resolve the run on success; `jack_out` is the exit beat). |
| **Jack Out** | `push` | Exit the run; keep extracted data, end the confrontation. |

`Jack In` is the **confrontation open** (the act of starting the `net_run`), not a
per-turn selectable beat — modeling it as a recurring beat is nonsensical after
turn 1. The entry's security exposure is represented by the run being live (the
first verb the player takes is their first `cwn.hacking.security_check`).

All beats use `stat_check: Tech` (INT) — the Program skill rides the existing
skill term on the 2d6 check. `player_metric` = `data` (extraction objective);
`opponent_metric` = `alert` (network trace), threshold reached = run lost.

### Player-facing legibility (Sebastien / Jade)

The chosen tier label and effective DC are surfaced on the existing
dice/confrontation player surface so a mechanics-first player sees, e.g.,
"Program check vs **Corp Black Site — DC 12**" rather than a bare number. This
reuses the dice-resolution payload's difficulty surfacing (ADR-074); no new UI
component. (The OTEL span is the dev/GM-side lie-detector and is separate from
this player surface.)

## Content edits (`neon_dystopia`)

- **`rules.yaml`**: add the `cwn.hacking` block (ladder + default_tier); delete
  the `net_combat` confrontation; add the `net_run` confrontation with the four
  verb beats above, `player_metric: data`, `opponent_metric: alert`,
  `category: hacking`, `mood: tension`. Keep `Tech` stat checks.
- No `inventory.yaml` / `archetypes.yaml` change required for hacking itself
  (Program is a skill term; deck loadout stays narrative/inventory per the
  ruleset spec's YAGNI boundary).

## Out of scope (YAGNI — per ruleset spec)

- Cyberdeck **CPU/Memory/Access** program economy as live engine.
- Bespoke cyberspace **dogfight minigame** (ADR-077 style).
- Per-program stat blocks / a Verb×Subject matrix beyond the four beats.
- Changes to world content (`franchise_nations`).

## Testing & wiring

All server tests; DB-gated tests skip without `SIDEQUEST_TEST_DATABASE_URL`.

- **Config validation** (`tests/genre/models/`): `HackingConfig` rejects an empty
  ladder and a `default_tier` not in the ladder (fail loud).
- **Engine** (`tests/game/ruleset/test_cwn_hacking.py`):
  - `resolve_hacking` returns `base_dc + alert_modifier`.
  - emits `cwn.hacking.security_check` with `tier`, `base_dc`, `alert_modifier`,
    `effective_dc`, `verb`, `result` attributes.
  - alert modifier raises the effective DC (e.g. tier office=9, +2 alert → 11).
  - base `RulesetModule.resolve_hacking` (native/swn) emits **no** span.
- **Span** (`tests/telemetry/`): `cwn_hacking_security_check_span` fires under the
  expected name and carries the tier + DC attributes.
- **Resolution path** (`tests/server/`): a `net_run` beat builds a **2d6** dice
  request (pool `[{sides:6, count:2}]`), not a d20 attack — assert the request's
  pool and that `difficulty` equals the effective security DC. A controlled
  2d6 face set resolves to the expected `RollOutcome` tier vs that DC.
- **Wiring test (behavior/OTEL — never source-grep)**: load the real
  `neon_dystopia` pack, open a `net_run` (security_tier supplied), drive a
  **Run Program** beat through the production dispatch path, and assert
  `cwn.hacking.security_check` fires with the pack's ladder DC. Proves the
  pack→`CwnRulesetModule` binding, the `cwn.hacking` config, and the dispatch seam
  are reachable from a production code path.
- **End-to-end drive**: a `net_run` confrontation advanced to a player win (data
  metric reaches threshold) and, separately, an opponent win (alert metric reaches
  threshold = "Alert ×2" loss).
- **Default-tier path**: opening a `net_run` without `params["security_tier"]`
  stamps the pack's `default_tier`; an unknown tier fails loud.

## References

- `docs/superpowers/specs/2026-05-28-neon-cwn-ruleset-design.md` §Hacking — the
  approved parent design this implements.
- `docs/superpowers/plans/2026-05-28-neon-cwn-combat-lethality.md` — plan 3, the
  Trauma/Shock/Mortal-Injury seam + span precedent this mirrors.
- ADRs: 033 (confrontation engine), 074 (dice resolution protocol — player-facing
  DC surfacing), 113 (intent router — supplies the confrontation dispatch params),
  117 (pluggable rulesets).
- Source: Cities Without Number SRD v1.0, Kevin Crawford (CC0) — cyberspace Verbs,
  security ratings, Alert the Network.
