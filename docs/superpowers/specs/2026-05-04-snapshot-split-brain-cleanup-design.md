# Snapshot Split-Brain Cleanup — Design

**Status:** Draft for review
**Date:** 2026-05-04
**Author:** Architect (Man in Black) on Keith's request
**Scope:** `sidequest-server` only (no UI / daemon / content changes)

---

## Context

A targeted audit of `sidequest-server` for split-brain antipatterns surfaced
six places where the same domain truth is stored in two locations on
`GameSnapshot`. Every one of them has either an admission in its own docstring
("the two collections are independently populated"), an active back-fill defense
in calling code (`narration_apply.py:920-930` snapshotting locations before
clobbering), or a name collision that misroutes imports (`EncounterTag` × 2).

The core risk is the **Sebastien lie-detector failure mode**: the GM panel's
authority comes from OTEL spans on a single source of truth per question. When
a snapshot has two stores answering "what is this NPC's HP" or "where is the
party," the panel can't tell which one is authoritative — and the narrator can
narrate convincingly off whichever bag of state Claude saw first. CLAUDE.md's
"GM panel is the lie detector" principle requires single ownership per
question.

## Goals

1. Each domain question on `GameSnapshot` has one authoritative store.
2. Existing saves promote silently to the canonical shape on first load.
3. Sebastien's GM panel can answer "did the narrator pull from the cast pool
   or invent a novel NPC?" via a single OTEL field.
4. The `extra: ignore` forward-compat policy is preserved — new servers
   reading older saves never error.

## Non-goals

- No content rewrite. Genre packs, world data, narrator prompts unchanged
  except for the cast-pool projection update in S2.
- No UI changes. Projections fed to the client (ADR-026/027) preserve their
  existing shape; storage canonicalization is server-internal.
- No fix for `TensionTracker` (dormant subsystem, ADR-024 partial). Out of
  scope.
- No combat HP semantics rework. `EdgePool` is already the canonical model for
  Character/Npc — this design only resolves the registry's legacy `hp/max_hp`
  holdout, it does not redesign composure.

## Findings recap

| Tag | Store A | Store B | Severity |
|---|---|---|---|
| **S1** | `snapshot.world_confrontations` | `snapshot.magic_state.confrontations` | Critical |
| **S2** | `snapshot.npcs` | `snapshot.npc_registry` (+ chassis projection) | Critical |
| **S3** | `snapshot.location` | `snapshot.character_locations[name]` | Major |
| **S4** | `game/encounter_tag.py:EncounterTag` | `game/session.py:EncounterTag` | Moderate (name collision) |
| **S5** | Magic in-flight queues persisted on snapshot | (transient, snapshot-bound) | Minor |
| **S6** | `Combatant.is_broken` body duplicated across implementers | (acceptable today) | Tripwire only |

S1, S2, S3 each have a real divergence path. S4 is a name collision waiting
for an import accident. S5 is a queue that must not survive a save snapshot.
S6 is documented as a tripwire — promote to ABC when a third implementer
arrives.

## Approach: two-wave hybrid

### Wave 1 — Naming & dedup (one story, low-risk)

Single PR, mechanical, no semantic surface change for callers.

- **S1.** Collapse `world_confrontations` into `magic_state.confrontations`.
  Add `coupled_to_chassis: bool` (or equivalent discriminator) to
  `ConfrontationDefinition` if not already present. `room_movement.py` reads
  via filter accessor; `chassis.py:233`'s YAML loader writes into
  `magic_state.confrontations` instead of the duplicate field. Loader
  migration: any save with `world_confrontations` non-empty merges them into
  `magic_state.confrontations` on load (dedupe by `id`), then drops the
  field.

- **S4.** Rename `game/session.py:EncounterTag` → `NpcEncounterLogTag` (its
  docstring already calls it that). `game/__init__.py` exports both names
  with a `from __future__ import annotations`-compatible re-export of the
  old name for one release window, then drops it. The other `EncounterTag`
  in `game/encounter_tag.py` keeps its name (it's the one with three call
  sites and an ADR reference).

- **S5.** Move `magic_state.pending_status_promotions`,
  `snapshot.pending_magic_auto_fires`, `snapshot.pending_magic_confrontation_outcome`
  off the snapshot. They become handler-local state in
  `websocket_session_handler` / `narration_apply` — drained by the same
  function that populates them, never serialized. Loader: ignore the fields
  on read (forward-compat); save migration drops them. Any in-flight save
  taken mid-handler simply re-emits the work on next narration turn (idempotent
  by construction; auto-fire and outcome dispatch are derived from the
  current snapshot state, not from the queue).

**Migration:** read-old-write-new. First save after upgrade is canonical.

**OTEL:** add `snapshot.canonicalize` span on each load that performed any
migration step, with attributes per-field for the GM panel.

**Estimated size:** 3 points. One story.

### Wave 2 — Semantic refactor (sequenced stories)

Each merges independently. Order matters; later stories can read earlier
canonical state.

#### Wave 2 Story A — NPC pool / NPC state split (S2)

The reframe: the registry exists because Claude (under `claude -p`, no
tool-calling) tends to invent cliché NPCs unless the prompt presents an
existing pool to pull from. The pool is randomized sampling (name
generators × archetype tables × culture corpus per ADR-091), generated
at world-bind, and presented to the narrator as "people who exist in this
world." Today, that pool is fused with stateful NPC tracking in
`NpcRegistryEntry`, which carries `last_seen_*` runtime tracking AND
legacy `hp/max_hp` AND chassis projections.

**New shape:**

```python
# Pool of randomized identities the narrator pulls from. Identity-only.
# Regenerable. No mechanical state.
class NpcPoolMember(BaseModel):
    name: str
    role: str | None
    pronouns: str | None
    appearance: str | None
    archetype_id: str | None      # for OTEL attribution back to source
    drawn_from: str                # "name_generator", "world_authored", etc.

# Stateful NPCs — only exist when actually encountered. EdgePool, beliefs, etc.
# Existing Npc model, with one new field:
class Npc(BaseModel):
    core: CreatureCore
    # ...existing fields...
    pool_origin: str | None = None  # name from NpcPoolMember if promoted from pool;
                                    # None if narrator-invented (lie-detector signal)

# GameSnapshot:
npc_pool: list[NpcPoolMember]  # replaces npc_registry for cast purposes
npcs: list[Npc]                # already exists; gains pool_origin field

# Removed:
# - npc_registry (migrated)
# - chassis projection into npc_registry (chassis stay in chassis_registry only)
```

**Narrator prompt projection** (gaslight discipline preserved): the prompt
builder presents `npc_pool` members as "exists in the world" identity blocks,
formatted identically to how `npc_registry` entries appear today. Storage
shape changed; in-prompt projection unchanged. The narrator does not see a
"pool" label — gaslight is preserved by the projection layer.

**Last-seen tracking** (current `last_seen_location` / `last_seen_turn` on
registry): moves onto `Npc` (where it belongs — only encountered NPCs have a
last-seen). Pool members aren't "seen" — they're "exist." This resolves the
type-confusion of last-seen sitting on identity-only records.

**Promotion:** when the narrator's `npcs_present` mentions a name that
matches an `NpcPoolMember`, the apply path creates an `Npc` with
`pool_origin=member.name` and (optionally) leaves the pool member in place
for re-citation, OR removes it (one-shot draw). Decision deferred to story
implementation; either is consistent with the type contract.

**Novel NPC handling** (narrator invented a name not in the pool): create
`Npc(pool_origin=None)`. OTEL emits `npc.invented` span. This is the
Sebastien signal — over time, repeated `npc.invented` spans tell us the pool
wasn't deep enough or wasn't loaded for that scene.

**Chassis projection removal:** chassis live in `chassis_registry` only.
The narrator prompt projection layer reads from both `npc_pool` and
`chassis_registry` and presents them in their own zones (chassis already
have a distinct projection in `prompt_framework/core.py:426`); they never
get folded into the NPC pool list.

**Migration on load:**

```
for entry in old_snapshot.npc_registry:
    if entry.hp is not None or entry.max_hp is not None:
        # Stat block was published — this is an encountered NPC.
        # Promote to Npc with EdgePool from edge_config.
        npcs.append(Npc(
            core=CreatureCore(name=entry.name, ...,
                              edge=edge_pool_from_legacy_hp(entry.hp, entry.max_hp)),
            pool_origin=None,  # we lost the provenance; mark as legacy
        ))
    else:
        # No stats published — pool member.
        npc_pool.append(NpcPoolMember(
            name=entry.name, role=entry.role, pronouns=entry.pronouns,
            appearance=entry.appearance, archetype_id=None,
            drawn_from="legacy_registry",
        ))
```

`last_seen_*` fields on legacy registry entries are dropped on migration —
they'd be wrong anyway, since legacy entries conflated pool and encountered.

**Estimated size:** 8 points. One story (could split if review demands).

#### Wave 2 Story B — Retire `snapshot.location`, derive from `character_locations` (S3)

The party-level `snapshot.location` is the field whichever player narrated
most recently clobbered. The 2026-05-02 multiplayer bug (Blutka location
appearing in Orin's session) led to `character_locations[name]`. The active
back-fill in `narration_apply.py:920-930` exists to keep peers from being
clobbered when the global is overwritten — that defense is split-brain
remediation, not prevention.

**New shape:**

- `snapshot.character_locations: dict[str, str]` is canonical.
- `snapshot.location` is removed.
- A computed accessor `snapshot.party_location(*, perspective: str | None = None)`
  returns either:
  - The acting/highlighted player's location (when `perspective` given), or
  - The "consensus" location across all seated players (when they agree), or
  - `None` when the party is split.

  Callers that today read `snapshot.location` either pass a perspective
  (single-player narrator framing, character-tab header) or check for
  `None` and render "(party split)" (legacy header sites).

**Migration:** on load, if `character_locations` is empty and
`snapshot.location` is non-empty, populate `character_locations[name] =
snapshot.location` for every seated character. Then drop `location`.

**Back-fill defense removed:** `narration_apply.py:920-930` (the snapshot of
peers' locations before clobbering) deletes — the party-level field no
longer exists to clobber.

**OTEL:** `snapshot.party_location_query` span attributes
`perspective_supplied / consensus_found / party_split` — the GM panel can
see when the party is mechanically split and headers might disagree.

**Estimated size:** 5 points. One story.

#### Wave 2 Story C — Combatant ABC tripwire note (S6, no story)

Today: `Character` and `Npc` each carry verbatim two-line bodies for
`is_broken` and `edge_fraction` because the Story 42-1 design deviation
chose Protocol-without-defaults. With two implementers and two-line bodies
this is acceptable.

**Tripwire:** when a third `Combatant` implementer is introduced (`Enemy`
type, ship-as-combatant, anything), promote `Combatant` from a Protocol to
an ABC with default method bodies. Add a CI check that fails when the
class count of `Combatant` implementers in `sidequest/game/` exceeds 2 and
no ABC exists.

This is documented in this ADR; no story is created. The tripwire is the
deliverable — the work is contingent.

## Migration policy: read-old-write-new

Per Keith's directive (this conversation, 2026-05-04): every story in this
design uses migration-on-load. First save after the upgrade promotes the
schema in place. No CLI tool, no version bump, no "migrate-saves" step
Keith has to remember.

Contract:

1. The pydantic loader accepts both legacy and canonical fields
   (`extra: ignore` on `GameSnapshot` already provides forward-compat for
   unknown fields; the migration adds backward-compat for known-legacy fields).
2. A `_migrate_legacy(data: dict) -> dict` function runs before pydantic
   validation. Every per-field migration registers here.
3. The migration emits an OTEL `snapshot.canonicalize` span with per-field
   `migrated: bool` attributes. The GM panel surfaces this on the first
   load of any save touched by Wave 1 or Wave 2 stories.
4. Once migrated, the snapshot is written back canonical on next save —
   no dual-write window.

## OTEL — the lie-detector wiring

Per CLAUDE.md OTEL Observability Principle, every fix in this design adds
spans. The GM panel becomes able to answer:

| Question | Span | Attributes |
|---|---|---|
| Did this narration name a pool NPC or invent? | `npc.referenced` | `pool_origin` (name or `null`), `match_strategy` |
| Were two confrontation stores migrated? | `snapshot.canonicalize` | `s1_world_confrontations_merged: int` |
| Was there a party-location split this turn? | `snapshot.party_location_query` | `consensus_found`, `party_split` |
| Did the narrator clobber peer locations? | (event obsolete after S3) | n/a |

These are server-side spans surfaced through the existing OTEL passthrough
(ADR-058, ADR-090).

## Risks

1. **Save corruption.** Migration-on-load runs on every legacy save. If the
   migration has a bug, the canonical write back corrupts the save. Mitigation:
   the migration writes to a sibling `.db.canonicalize.bak` first (existing
   save backup pattern from `.pennyfarthing/guides/save-management.md`); the
   canonical path swaps in only after successful pydantic round-trip. One
   release of dual-file behavior; remove after stability confirmed.

2. **Narrator prompt regression.** S2 changes how the cast pool is fed into
   the prompt. Even though the projection preserves the gaslight, it's a
   different code path. Mitigation: snapshot before/after prompt diffs on a
   captured save (`scenarios/` has captures); the projection layer is
   covered by golden-text tests before merge.

3. **Hidden `world_confrontations` consumers.** S1's grep showed 5 call
   sites. If a sixth lives in dispatch dead code, it silently gets the empty
   list after migration. Mitigation: deprecation warning on field-read for
   one release before removal.

4. **`character_locations` consensus heuristic.** S3's "consensus across
   seated players" might disagree with current behavior in odd MP edge
   cases. Mitigation: the per-character header path already prefers
   `character_locations[name]` (views.py:394-395); the consensus path is
   only for legacy callers. Document the explicit precedence in the
   accessor.

## Story decomposition (preview)

- **Story X — Wave 1: snapshot dedup & rename.** S1 + S4 + S5. 3 points.
- **Story Y — Wave 2A: NPC pool / state split.** S2. 8 points (split if
  review burdens).
- **Story Z — Wave 2B: derive party location.** S3. 5 points.
- **(no story) — S6 ABC tripwire**, documented in this ADR.

Total: 16 points. Sequenced. Each story has its own OTEL deliverables.

## Acceptance criteria (rolled across stories)

- [ ] No `GameSnapshot` field is duplicated by another field on the same
      snapshot.
- [ ] Loading any pre-cleanup save from `~/.sidequest/saves/` succeeds and
      writes back canonical.
- [ ] OTEL `snapshot.canonicalize` span fires once per migrated save with
      per-field migration attributes.
- [ ] OTEL `npc.referenced` span includes `pool_origin` for every narrated
      NPC reference; the GM panel surfaces invented NPCs as a counter.
- [ ] `narration_apply.py` no longer back-fills peer locations before
      clobbering a global field.
- [ ] No imports of the renamed `NpcEncounterLogTag` remain ambiguous;
      grep for `EncounterTag` returns exactly two distinct types in
      distinct domains.
- [ ] `pending_magic_*` queues do not appear in any saved snapshot.
- [ ] Sebastien's GM panel test scenario (`scenarios/`) shows
      pool-vs-invented attribution on every NPC reference.

## Open questions for review

1. Pool-promotion semantics: when the narrator names a pool member, do we
   *remove* them from the pool (one-shot) or *leave* them (re-cite-able)?
   The design tolerates either — story implementation chooses.
2. Should the per-field deprecation warnings for legacy snapshot fields
   surface in the GM panel directly, or only in server logs? Default:
   GM panel, since that's the audit surface.
3. Wave ordering: are we OK shipping Wave 1 ahead of Wave 2A even though
   Wave 2A is the highest-leverage fix? My recommendation is yes — Wave 1
   is a few days, Wave 2A is two weeks of work, no reason to block.

## References

- Audit findings: this conversation, 2026-05-04.
- ADR-007 Unified Character Model (Character + Npc compose CreatureCore).
- ADR-014 Diamonds and Coal (narrative weight, Chekhov discipline — pool
  members are coal, encountered NPCs are diamond).
- ADR-026/027 Client State Mirror / Reactive State Messaging (projection
  shape preserved).
- ADR-058 Claude Subprocess OTEL Passthrough; ADR-090 OTEL Dashboard
  Restoration.
- ADR-067 Unified Narrator Agent (single persistent session — narrator
  cannot tool-call back; cast pool must be in-prompt).
- ADR-091 Culture-Corpus + Markov Naming (source of pool identity samples).
- CLAUDE.md "GM panel is the lie detector."
- Memory: durable retention by default (Keith plays in years, not weeks).
- Story 39 / EdgePool (CreatureCore composure model — `hp/max_hp` on
  `NpcRegistryEntry` is the holdout).
- Story 45-21 (registry `hp=None` "no claims" discipline — preserved by
  S2's pool/state split).
