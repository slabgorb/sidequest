# Magic System Implementation — Coyote Star v1

**Date:** 2026-04-28
**Status:** Design — pre-implementation
**Target playtest:** Keith + James + Alex + Sebastien, full Coyote Star session
**Companion docs:**
- `docs/design/magic-taxonomy.md` (framework)
- `docs/design/magic-plugins/` (plugin specs)
- `docs/design/visible-ledger-and-otel.md`
- `docs/design/confrontation-advancement.md`
- `docs/design/magic-system-handoff.md`

## Purpose

Stand up the magic-system framework — designed in the napkin/plugin work of 2026-04-27 → 2026-04-28 — far enough that **a Coyote Star (space_opera) session can be played end-to-end with magic mechanically live, OTEL-observed, and ledger-visible**. This is a vertical slice of the framework: only the plugins Coyote Star uses, only the patterns Coyote Star exercises, only the UI that Coyote Star plays under.

## Approach

**Content-first, then vertical-first build.** Author Coyote Star's `magic.yaml` *first* as the contract the implementation must satisfy. The framework has not yet survived a fresh world-author writing against it — Coyote Star is the first independent test. If the schema fights the author, fix the schema before any code ships. Then build the implementation only against what Coyote Star actually uses, deferring every framework feature it doesn't (heavy_metal-only patterns, multi-session confrontations, shared-bar propagation, learned_v1, divine_v1, bargained_for_v1, obligation_scales_v1).

## Audience anchors

Per CLAUDE.md, design decisions weigh against actual playgroup members:
- **Keith** (forever-GM-now-player): the system must surprise him. Mechanical enforcement of hard_limits and the OTEL lie-detector are how it does that.
- **James** (narrative-first, played Rux in caverns_and_claudes save): the system can't reduce his agency. Narrator stays in charge of prose.
- **Alex** (slow typist, freezes under pressure): magic must not require fast typing. Sealed-letter pacing already handles this; magic just composes with it.
- **Sebastien** (mechanics-first): the GM panel is a *feature* for him, not a debug tool. The OTEL lie-detector is what makes magic real for Sebastien.

## Locked decisions (this brainstorm)

1. **Approach 1** — Content-first, then vertical-first build (versus pure vertical-first or horizontal-layered).
2. **First playable target = real playgroup playtest**, not solo demo or smoke test. This commits us to a multi-iteration build with intermediate playable cut-points.
3. **Plugin instances eager-instantiated at world-load** time (D1).
4. **`world_knowledge` sub-tag pattern** (D2): single field with optional `local_register` sub-tag, e.g. `primary: classified, local_register: folkloric`. Validator allows `local_register` ≤ `primary` in awareness ordering.
5. **Magic working data rides on existing `game_patch`** as a new `magic_working` field (D3 corrected). Same parser, same enforcement discipline, same telemetry pattern.
6. **Mutation site is `narration_apply.py`** (D4) alongside existing `apply_inventory_changes` etc. No parallel mutation pipeline.
7. **Plugins are code + YAML mix.** Mechanics live in Python (validation, hard_limits enforcement, threshold→status promotion); content lives in YAML (narrator_register, ledger_bar templates, output catalog descriptions). YAML alone would push mechanics into prompt engineering; that's exactly what we don't want.
8. **`LedgerPanel` lives inside `CharacterPanel.tsx`**, not as a sibling component.
9. **`learned_v1` deferred** — no formal training tradition fits Coyote Star's tone.

---

## 1. Content commitment — Coyote Star's magic shape

### Plugin set (v1 ships only these two)

- **`innate_v1`** with `flavor: acquired`. Voidborn station clans + second-gen miners exposed to whatever the long-resident alien species emits develop reflexive psychic touch — minor precognition, sympathetic-feel-at-a-distance, distortion under stress. Untrained, reflexive, can't be aimed reliably. **Delivery mechanisms active:** `native` (voidborn lineage) + `condition` (exposure-event acquisition).
- **`item_legacy_v1`** with `mccoy` + `discovery` + `relational` mechanisms. Named guns and named ships, salvaged alien artifacts that carry agency, frontier-engineering McCoy register. **Subtypes:** `weapon`, `vessel`, `relic`. Items have OCEAN scores, dispositions, may refuse to fire, may bond to specific carriers.

**Deferred:** `learned_v1`, `divine_v1`, `bargained_for_v1`, `obligation_scales_v1`.

### Axes

- **World-knowledge:** `primary: classified, local_register: folkloric`. Hegemony officially denies; frontier folk know it as rumor.
- **Visibility:** `feared` at Hegemony layer, `dismissed` at frontier layer.
- **Intensity:** 0.25 (low). Not a power-fantasy world.
- **Player options:** `can_build_caster: false` for innate (it happens *to* you, no chargen class). `can_build_item_user: true` (gunsmith / pilot / scavenger archetypes).

### Hard limits

Inherited from genre: no resurrection, no FTL telepathy, no tech replacement, no Elemental/Necromantic Domains. **World-specific addition:** psionics never wins decisively against weapons. The Reach's psychic effects are *uncanny*, not *combat-defining*.

### Cost types

`sanity` (innate workings), `notice` (item workings — every body costs sleep), `vitality` (innate-heavy use ages you).

### Ledger bars (v1 — exactly six)

| Bar | Scope | Direction | Threshold(s) | Confrontation hook |
|---|---|---|---|---|
| `sanity` | character | down | 0.40 → The Bleeding-Through | mandatory auto-fire |
| `notice` | character | up | 0.75 → The Quiet Word | mandatory auto-fire |
| `vitality` | character | down | (slow drain, no immediate confrontation in v1) | — |
| `bond_<item_id>` | item | bidirectional | low → item refusal, high → loyalty | narrator-discretion |
| `item_history_<item_id>` | item | up | accumulates resonance | narrator-discretion |
| `hegemony_heat` | world | up (slow decay) | 0.70 → escalation | narrator-discretion |

**Patterns explicitly NOT used in v1:** shared-bar propagation, cyclical reset, multi-session confrontations, cross-scale triggers, world_default_decay_override.

### Named confrontations (5 total)

1. **The Standoff** — item_legacy, weapon-subtype, frontier-classic at the chokepoint geography.
2. **The Salvage** — item_legacy, discovery mechanism. The thing you pulled has its own opinion about being pulled.
3. **The Bleeding-Through** — innate_v1, condition mechanism. Auto-fires when sanity ≤ 0.40.
4. **The Quiet Word** — innate_v1 + social. Auto-fires when notice ≥ 0.75. Hegemony's response when noticed.
5. **The Long Resident** — innate_v1 + item_legacy hybrid. The alien species observes you and may give you something. Once-per-arc.

### Narrator register (paragraph)

> *The Reach doesn't perform miracles. It bleeds through. A ship's pilot taps the panel that wasn't responding and it answers — once, never again. A gunsmith's last bullet hits a target the shooter never aimed at. Someone wakes at 0300 station-time knowing a name they shouldn't. The Hegemony classifies this as Anomaly Class 4 and writes the witnesses' termination orders. The frontier knows it as Coyote work, and you don't say it out loud.*

### Content scope

- `genre_packs/space_opera/magic.yaml` (~150 lines)
- `genre_packs/space_opera/worlds/coyote_star/magic.yaml` (~400 lines)
- `genre_packs/space_opera/worlds/coyote_star/confrontations.yaml` (~150 lines)

---

## 2. Implementation architecture

### 2a. Reuse-first principle

Existing infrastructure absorbs most of what would otherwise be new code. Specifically:

| Was tempted to add | Existing system that absorbs it | Reuse mechanism |
|---|---|---|
| New WebSocket message types | `game/delta.py::StateDelta` boolean flags + `build_protocol_delta()` per-turn delta | Add `magic: bool` flag |
| New "WorkingResolution" toast UI | `game_patch.status_changes` + existing Status renderer | Auto-promote significant cost-crossings into `Status(severity=Wound/Scar)` |
| New GM dashboard tab | `telemetry/spans/` `SPAN_ROUTES` registry + existing dashboard event feed | Register `magic.working` route with `event_type=state_transition, component=magic` |
| New magic-effects model | `game/status.py` Scratch/Wound/Scar | Bleeding-Through onset = `Status(Wound)`, Stigma = `Status(Scar)` |
| New world-state-bar abstraction | `game/tension_tracker.py` | Model `hegemony_heat` after TensionTracker (multi-axis with decay) |
| Bidirectional thresholds | `game/resource_pool.py::ResourceThreshold` | Extend with `direction: Literal["down","up"]` (~5 line patch) |
| New mutation pipeline | `GameSnapshot.apply_resource_patch` | Magic mutations route through existing surface |
| Threshold-crossing narrator memory | `mint_threshold_lore` in resource_pool.py | Free reuse — no new memory infrastructure |

### 2b. New code (5 files, ~1,000 LOC)

| Path | Purpose | Approx LOC |
|---|---|---|
| `sidequest-server/sidequest/game/magic_state.py` | Pydantic aggregate field on `GameSnapshot`. Bar registry keyed by `(scope, owner_id, bar_id)`, plugin-instance config (frozen at world-load), working log. `apply_working()` method. | ~250 |
| `sidequest-server/sidequest/genre/magic_loader.py` | YAML → `WorldMagicConfig`. Pairs plugin `.py` + `.yaml`; both must be present. | ~150 |
| `sidequest-server/sidequest/magic/plugins/innate_v1.py` + `.yaml` | Mechanics + content. Validation, required-attrs, threshold→status promotion logic, output catalog. | ~250 |
| `sidequest-server/sidequest/magic/plugins/item_legacy_v1.py` + `.yaml` | Same shape as innate. | ~250 |
| `sidequest-server/sidequest/magic/validator.py` | `validate(working, world_config) → list[Flag]`. Severity: yellow / red / deep_red. | ~150 |
| `sidequest-ui/src/components/LedgerPanel.tsx` | Section *inside* `CharacterPanel.tsx`. Renders character-scoped bars. | ~200 |

### 2c. Extended code (~250 LOC additions across these files)

| Path | Change |
|---|---|
| `game/session.py` (`GameSnapshot`) | Add `magic_state: MagicState \| None` field. Wire through `compute_delta`, `build_protocol_delta`. |
| `game/delta.py` (`StateDelta`) | Add `magic: bool = False` flag. |
| `game/resource_pool.py` (`ResourceThreshold`) | Add `direction: Literal["down","up"]` (default `"down"` for back-compat). |
| `agents/narrator.py` | Pre-prompt magic context block (allowed_sources, hard_limits, ledger snapshot, active confrontation). Add `magic_working` to `NARRATOR_OUTPUT_ONLY` field list. |
| `server/narration_apply.py` | Parse `magic_working`, call `apply_magic_working`, auto-promote threshold crossings into `status_changes` flow. |
| `sidequest-ui/src/components/CharacterPanel.tsx` | Import and render `LedgerPanel` as a section. ~10 LOC change. |
| `sidequest-ui/src/components/ConfrontationOverlay.tsx` | (Iteration 5) Extend with mandatory-output reveal at outcome time, branch-explicit register. |

### 2d. Registry-only additions (~30 LOC)

- One `SpanRoute` entry for `magic.working` in `telemetry/spans/`.

### 2e. What does NOT change

- Protocol message types (zero added)
- Dashboard UI (zero new widgets in v1)
- Status type system (Scratch/Wound/Scar are reused)
- `dispatch/confrontation.py` flow (magic confrontations are confrontations; no parallel pipeline)
- Save format (legacy saves init empty `magic_state`, no migration warning per "legacy saves are throwaway" memory)
- Inventory model (item bonds extend existing item; no new item table)

### 2f. Plugin code/data split

Plugins are paired files. The split principle: **YAML for what content authors tune, code for what the engine mechanically enforces.**

```
magic/plugins/innate_v1.py
  class InnatePlugin(MagicPlugin):
      def required_span_attrs() -> set[str]
      def validate_working(working, config) -> list[Flag]
      def hard_limits() -> list[HardLimit]
      def threshold_promotions(crossing) -> list[StatusChange]
      def confrontation_outputs(branch) -> list[Output]

magic/plugins/innate_v1.yaml
  narrator_register: |
    The character IS the source...
  ledger_bar_templates:
    sanity: { direction: down, default: 1.0, ... }
  output_catalog:
    - id: control_tier_advance
      description: ...
  examples:
    - flavor: acquired
      consent_state: involuntary
      ...
```

Loader pairs both at world-materialization time; missing either fails loud per project's no-silent-fallback rule.

---

## 3. Worked example — data flow trace

Setting: **The Salvage** confrontation, mid-session at Mendes Post. Sira Mendes (voidborn lineage, no formal training) puts her hand on a panel inside a derelict alien hopper. Narrator decides she's picking something up.

### Pre-prompt context to narrator

`magic.context_builder` injects ~12 lines into the narrator's existing pre-prompt:

```
ACTIVE MAGIC CONTEXT — Coyote Star
allowed_sources: [innate, item_based]
hard_limits: [no_resurrection, no_ftl_telepathy, no_tech_replacement,
              no_mind_compulsion, psionics_never_decisive]
world_knowledge: classified (frontier register: folkloric)
active_ledger_for_actor:
  sanity: 0.78 (threshold_low: 0.40 → The Bleeding-Through)
  notice: 0.22 (threshold_high: 0.75 → The Quiet Word)
  vitality: 0.92
  hegemony_heat (world): 0.31
active_confrontation: the_salvage (round 2 of 3)
If your narration depicts a magic working, emit a magic_working field
in your game_patch with required fields for the firing plugin.
```

Loaded only when the world has `magic.yaml`; absent on quiet turns.

### Narrator output

Prose + game_patch:

```
**Inside the Hopper**

The console's bone-white surface holds Sira's hand for a moment longer
than it should. She feels — not hears — a *direction*: aft, two
compartments, a closed door. The certainty arrives without warning and
leaves a soft ringing in the back of her skull. The Hopper has noticed
her.

```game_patch
{
  "magic_working": {
    "plugin": "innate_v1",
    "mechanism": "condition",
    "actor": "Sira Mendes",
    "costs": {"sanity": 0.12},
    "domain": "psychic",
    "consent_state": "involuntary",
    "flavor": "acquired",
    "narrator_basis": "alien-tech proximity triggers reflexive sympathetic-feel"
  },
  "footnotes": [...],
  "action_rewrite": {...}
}
```

### Server-side application

1. `narration_apply.apply_magic_working(snapshot, working, world_config)` parses block.
2. `magic.validator.validate(working, world_config)` runs:
   - ✅ `innate_v1` ∈ `allowed_sources`
   - ✅ `domain: psychic` ∈ `manifestation.domains`
   - ✅ `consent_state: involuntary` matches `flavor: acquired` per plugin spec
   - ✅ no hard_limits violated
   - Result: empty flag list (clean working)
3. `MagicState.apply_working(working)` mutates ledger via existing `GameSnapshot.apply_resource_patch`:
   - sanity 0.78 → 0.66
   - threshold check (0.66 > 0.40): no Bleeding-Through trigger
4. `apply_resource_patch` mints `LoreFragment` if any threshold crossed (no-op here, free reuse).
5. `watcher_hub.publish_event()` emits `magic.working` span with `flags=[]`, `costs_debited`, `ledger_after`, etc. SPAN_ROUTES routes it to dashboard event feed (`event_type=state_transition, component=magic`).
6. `StateDelta.magic = True`. `build_protocol_delta()` includes magic state in next per-turn delta over the existing message channel.
7. Client receives delta. `GameSnapshot` mirror updates. `LedgerPanel` (inside `CharacterPanel`) animates sanity bar 0.78 → 0.66. No "Bleeding through" status added (threshold not crossed).

### Counterexample — narrator violates a hard_limit

Same scene, but narrator writes "Sira reads the alien captain's mind across-system." Validator emits `DEEP_RED` flag (`hard_limit:no_ftl_telepathy`). Span carries flag. Dashboard event feed renders it red. **v1 does not interrupt narration** — flag-only. Sebastien sees it on the GM panel.

### Counterexample — auto-promotion to status

Different turn: Sira has been working hard for three sessions; sanity is now 0.45. Another working with `costs: {sanity: 0.10}`. Server applies, sanity drops to 0.35, crosses 0.40 threshold. Server auto-emits a `status_changes` ADD: `Status(text="Bleeding through", severity=Wound)`. The Bleeding-Through confrontation auto-fires next turn (mandatory hook). Existing status renderer shows the new Wound. **No new UI for this.**

### Latency

Magic pipeline adds ~5–15ms per working — pure Python data manipulation, no LLM call, no daemon hop. Negligible against existing ~500ms narration apply path.

---

## 4. Build sequence — six iterations to playgroup playtest

### Iteration 1 — Content + plugin abstractions (engine-only)

**Ship:**
- Content YAMLs: `space_opera/magic.yaml`, `coyote_star/magic.yaml`, `coyote_star/confrontations.yaml`
- Plugin pairs: `innate_v1.py`+`.yaml`, `item_legacy_v1.py`+`.yaml`
- `genre/magic_loader.py`
- `magic/validator.py`
- Pydantic models: `WorldMagicConfig`, `MagicState`, `MagicWorking`, `Plugin`, `Flag`
- Tests: load Coyote Star config; validate sample working blocks; assert hard_limits flag correctly

**Cut-point:** `pytest sidequest/magic` passes; can fixture-load Coyote Star and validator runs on canned blocks. **No game integration yet.**

**Risk addressed:** content authoring surfaces schema gaps the design didn't catch. That's the point — fix schema before downstream iterations build on it.

### Iteration 2 — GameSnapshot integration + persistence

**Ship:**
- `magic_state` field on `GameSnapshot`
- Wire through `compute_delta`, `build_protocol_delta`
- `StateDelta.magic` flag
- `ResourceThreshold.direction` extension
- SQLite roundtrip; legacy saves init empty
- Tests: persist/restore, delta detection on bar mutation

**Cut-point:** can construct a Coyote Star session, mutate ledger programmatically, observe state surviving save/load and producing correct StateDeltas.

### Iteration 3 — Narrator integration (loop closes server-side)

**Ship:**
- Pre-prompt magic context block in `narrator.py`
- `magic_working` added to `NARRATOR_OUTPUT_ONLY` field list with required-fields-by-plugin
- `narration_apply.apply_magic_working()`: parse, validate, apply, emit span
- Threshold→`status_changes` auto-promotion (sanity ≤ 0.40 → `Status("Bleeding through", Wound)`)
- `SPAN_ROUTES` entry for `magic.working`
- Tests: scripted narrator output triggers full pipeline; flag severity routing; status auto-promotion

**Cut-point:** solo-script the server. Type a turn that should trigger a working, see the patch parse, the validator run, the ledger move, the span emit, the status fire — all server-side. No UI yet.

### Iteration 4 — UI surface

**Ship:**
- Magic bars section *inside* `CharacterPanel.tsx`
- Verify existing status renderer handles magic-induced statuses (likely zero work)
- Verify existing dashboard event feed renders `magic.working` spans (likely zero work — SPAN_ROUTES handles it)
- Per-genre animation register: deferred (baseline animation only)

**Cut-point:** solo demo. Play a Coyote Star session, see bars rise, see costs land, see "Bleeding through" appear in status panel, see the working span appear in the GM dashboard. Keith plays alone, validates the full vertical works.

### Iteration 5 — Confrontations wired

**Ship:**
- Five named confrontations integrated with `dispatch/confrontation.py`
- Mandatory-output emission at outcome time
- Branch-explicit outcome reveal (extend `ConfrontationOverlay.tsx`)
- Auto-fire triggers (sanity threshold → The Bleeding-Through; notice threshold → The Quiet Word)
- Tests: full confrontation cycle ends with output applied to character

**Cut-point:** two-player playtest. Keith + one playgroup member, one hour. First time the system is asked to entertain humans.

### Iteration 6 — Stabilization + playgroup playtest

**Ship:**
- Multiplayer shared-world: confirm magic state propagates correctly per ADR-037
- Sealed-letter compatibility for private working info
- `hegemony_heat` as world-shared bar via TensionTracker pattern
- Bug-fix pass from iteration 5 playtests
- Cliché-judge hookup: master magic-narration audit checklist as post-session review (not runtime guard)

**Cut-point:** **The Playtest.** Keith + James + Alex + Sebastien. Full session of Coyote Star. Sealed-letter pacing for Alex. Sebastien watches the GM panel and sees the lie-detector catch (or miss) narrator improvisation.

### Effort estimate

| Iter | Engineering days |
|---|---|
| 1 | 4–5 (content authoring parallels code) |
| 2 | 2 |
| 3 | 3–4 |
| 4 | 2 |
| 5 | 4–5 |
| 6 | 3–4 + playtest |

**Total: ~18–22 engineering-days** to playgroup playtest.

---

## 5. Failure modes, OTEL coverage, testing

### 5a. Failure modes and what catches each

| Failure mode | Severity | Caught by |
|---|---|---|
| Narrator narrates a working but emits no `magic_working` field | Narrative/state divergence | **Cliché-judge post-session.** Same failure class as missing `items_lost` after "merchant takes your sword." Existing pattern. |
| Narrator emits `magic_working` with plugin ∉ `allowed_sources` | DEEP_RED flag | `magic.validator` at parse time. Span carries flag. v1 does not interrupt narration — flag-only. |
| Working violates hard_limit (FTL telepathy, resurrection, decisive psionics) | DEEP_RED flag | Validator. Same handling. |
| `consent_state` doesn't match `flavor` per plugin spec | YELLOW flag | Validator. Soft inconsistency, not violation. |
| `domain` ∉ genre's `manifestation.domains` | RED flag | Validator. |
| `magic_working` JSON malformed / missing required field | Parse failure | Existing narrator-retry path. Two retries; on third, empty patch + log `MAGIC_FLAG: parse_failure`. |
| Narrator emits working that should auto-fire confrontation but it doesn't | Confrontation skip | Iteration 5 unit test asserts threshold→confrontation hook. Manual verification in solo demo. |
| Legacy save loaded without `magic_state` | Init empty, no warning | Per project memory: legacy saves are throwaway. No migration. |
| Two players' shared-world deltas disagree on magic state | Multiplayer divergence | Iteration 6 specifically. ADR-037 split: world-state magic (hegemony_heat) is shared; per-character magic is per-player. |

### 5b. OTEL span shape

`magic.working` span (registered in SPAN_ROUTES with `event_type=state_transition, component=magic`):

**Required attributes:**
- `plugin: str` (e.g. "innate_v1")
- `mechanism_engaged: str` (e.g. "condition")
- `actor: str` (character name)
- `domain: str`
- `costs_debited: dict[str, float]`
- `flags: list[Flag]` (severity + reason)
- `narrator_basis: str` (one-sentence why this is a working)
- `ledger_after: dict[str, float]` (snapshot of relevant bars post-mutation)

**Plugin-specific required attributes:**
- `innate_v1`: `flavor`, `consent_state`
- `item_legacy_v1`: `item_id`, `alignment_with_item_nature`

**Why these:** the cliché-judge hooks listed in the magic-system handoff doc audit exactly these fields. Missing `flavor` on an innate working is a YELLOW flag (the audit checklist requires it). Decorative scale-debiting (heavy_metal-only) does not apply to Coyote Star.

### 5c. Testing strategy

**Unit (iteration 1):**
- Plugin loader pairs `.py` + `.yaml`; missing either fails loud
- Validator detects every hard_limit violation in plugin-spec
- Validator detects plugin ∉ allowed_sources
- Validator passes clean workings without flags

**Integration (iteration 2-3):**
- GameSnapshot persist roundtrip with magic_state
- StateDelta.magic flag set when bars mutate
- Threshold crossing emits status_change ADD
- `magic.working` span surfaces via watcher_hub
- Span attributes match plugin's required set

**Wiring tests (per CLAUDE.md "every test suite needs a wiring test"):**
- Iteration 1: a non-test consumer imports `magic_loader` (proves it's wired into `genre/loader.py`)
- Iteration 3: a non-test consumer calls `apply_magic_working` (proves it's wired into `narration_apply.py`)
- Iteration 4: `LedgerPanel` is imported by `CharacterPanel` and reads from `magic_state` selector

**Solo demo (iteration 4):**
Scripted scenario: Sira walks to Mendes Post, enters the derelict, touches the alien panel, narrator describes a working. Verify:
- Bar animates
- Status renders if threshold crossed
- Dashboard event feed shows the span
- Save/load roundtrips state
- Repeat the scenario; ledger is persistent

**Playtest (iteration 5-6):**
The playtest itself is the final validation. Sebastien-shaped success: GM panel catches at least one narrator improvisation. Alex-shaped success: no fast-typing pressure, sealed-letter pacing intact. James-shaped success: prose authority remains with the narrator. Keith-shaped success: he is surprised at least once by something the system enforced and he didn't see coming.

### 5d. What this design does NOT catch

These deferments are deliberate; not gaps:

- **Narrator omitting `magic_working` for a working it described** — caught by cliché-judge post-session, not at runtime. v1's lie-detector is observability, not interruption.
- **Subtle narrator drift over many turns** — the per-turn validator catches discrete violations; aggregate drift (e.g. narrator slowly raising the world's magic-intensity over 30 turns) needs scaled audit, deferred past v1.
- **Plugin-overlap ambiguity** (cleric using a relic — Divine or Item-Legacy?) — Coyote Star has no Divine plugin in v1. Question deferred until a world that uses both ships.
- **Animation language per genre** — Buttercup/UX pass post-v1. v1 ships a baseline neutral animation register.

---

## Out of scope (explicit deferrals)

- Plugins beyond `innate_v1` and `item_legacy_v1` for v1 (no `learned_v1`, `divine_v1`, `bargained_for_v1`, `obligation_scales_v1`)
- Cyclical reset patterns (divine purity, learned prepared_slots)
- Multi-session confrontations (Stratigraphic Resonance, The Cascade — heavy_metal only)
- Shared-bar bidirectional propagation (heavy_metal only)
- Cross-plugin advancement output (`pact_tier` with `target_plugin: another_plugin`)
- Cross-scale trigger declarations
- `narrative_seed_only: true` counter pattern
- Cliché-judge as runtime guard (v1 is post-session review only)
- Narration interruption for DEEP_RED flag
- Per-genre animation register
- World-shared bar UI distinction (hegemony_heat renders the same as character-scoped bars in v1)

These are real features that future worlds will need — but Coyote Star doesn't, so they don't ship in v1. Each gets a story when a world that needs it gets prioritized.

---

## Open questions for architect review

Before iteration 1 starts, an architect (Leonard of Quirm) review pass should resolve:

1. **`control_tier` (innate) vs `discipline_tier` (learned) vs unified `pact_tier`** — the open output-catalog question from the handoff doc. Coyote Star uses only innate's `control_tier`, so v1 ships whatever innate_v1 specifies. The framework-level unification can wait, but architect should confirm the decision doesn't bite us when Iron Hills Bender Academy needs `discipline_tier`.
2. **Plugin spec runtime location** — `magic/plugins/*.py` + `*.yaml` paired files in the server tree. Confirm this is the right location and not, say, served from `sidequest-content/`.
3. **Plugin registry mechanism** — module-level dict populated at import vs. explicit registration call. Either works; pick one and stick with it.
4. **`MagicState` initialization for legacy saves** — confirmed init-empty per memory; architect should confirm this is consistent with how other recently-added GameSnapshot fields handle legacy saves.

## Risks summary

- **Highest:** Coyote Star magic.yaml authoring surfaces a schema gap that requires plugin spec changes. *Mitigation:* iteration 1 is exactly this; expect rework here, schedule budget for it.
- **Medium:** Narrator integration (iteration 3) surprises us — the LLM either over-emits `magic_working` (false positives flooding the dashboard) or under-emits (silent magic). *Mitigation:* solo demo scenario in iteration 4 specifically scripts both extremes and verifies behavior.
- **Medium:** UI bar-animation register feels wrong in space_opera tone, requires UX rework before playtest. *Mitigation:* deferred to Buttercup post-v1; iteration 4 ships baseline that's "correct" not "polished."
- **Low:** Multiplayer shared-world propagation has bugs from per-character vs world-shared bar split. *Mitigation:* iteration 6 dedicates time specifically to this; ADR-037 already governs the split.

## Definition of done — Coyote Star v1

The playgroup sits down. The four players play a session. During that session:

1. Magic fires when narrator describes it firing.
2. Bars on the character panel move when costs land.
3. The Bleeding-Through and The Quiet Word auto-fire when their thresholds cross.
4. Confrontations produce mandatory advancement outputs at outcome time.
5. The OTEL dashboard shows the magic.working span feed; Sebastien can see it.
6. At least one narrator improvisation gets flagged (or — if narrator is well-behaved — no false positives).
7. Alex experiences sealed-letter pacing intact; nothing about magic forces fast typing.
8. The session saves and resumes correctly across a break.
9. No DEEP_RED hard_limit violation passes through unflagged.
10. Keith plays a character. Keith is surprised by something at least once.

If all ten land: v1 is done. If any fail: post-playtest fix iteration before declaring done.
