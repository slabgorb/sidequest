# Evropi Starting Kits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author character-unique starting kits for five Evropi playgroup characters (Rux, Prot'Thokk, Hant, Pumblestone, Th`rook), a Ludzo test-inheritance kit, a Sunday-playable narrator sheet amendment, and a micro-ADR (ADR-081) defining two new `AdvancementEffect` enum variants — so that each character is mechanically distinct at turn one.

**Architecture:** Pure content authoring under `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/`, plus one architecture decision record at `docs/adr/081-advancement-effect-variant-expansion.md`. Zero engine code in this plan. Runtime consumption waits for Epic 39 story 5 (milestone-grant loader), which this plan does not block. Sunday session runs under GM fiat via the existing `sunday-progression.md` sheet.

**Tech Stack:** YAML (content), Markdown (docs), bash grep (cross-reference auditing), git (commit cadence). YAML content files are validated by the existing `pf hooks schema-validation` PreToolUse hook on every Write.

**Branch:** All work lands on the current `feat/37-17-stat-name-casing-drift` branch, per earlier decision to leave existing design commits in place rather than reorganize.

**Source spec:** `docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md`

---

## File Structure

**New files:**
- `docs/adr/081-advancement-effect-variant-expansion.md` — micro-ADR covering `AllyEdgeIntercept` and `ConditionalEffectGating` variants
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml` — new Pakook`rook Warlock character draft with full starting_kit, character_resources (reniksnad), trunk, paths, capstones

**Modified files:**
- `docs/adr/README.md` — add ADR-081 to the ADR index
- `docs/adr/078-edge-composure-advancement-rituals.md` — update forward-references from "ADR-079" (genre-theme, conflict) to "ADR-081" (for the two variants landing) and "ADR-082+" (for the rest of the deferred variants)
- `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` — update ADR-079 references to ADR-081/ADR-082+ per the same split
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/rux.yaml` — add starting_kit block
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/prot_thokk.yaml` — add starting_kit block (includes ADR-081 `AllyEdgeIntercept` reference)
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/hant.yaml` — add starting_kit block
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/pumblestone_sweedlewit.yaml` — add starting_kit block
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/ludzo.yaml` — add starting_kit block with `inherits: rux`
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/README.md` — bump scope tally to 6 files (5 playgroup + 1 test sandbox); add Th`rook entry; update scope-tally math
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/sunday-progression.md` — append Th`rook section and reniksnad-dependency narrator guidance

**All character-YAML TODO comments that currently reference "ADR-079"** get rewritten to reference "ADR-081" (for the two v1 variants) or "ADR-082+" (for everything else deferred). This is a cross-file sweep in Task 9.

---

## Task 1: Author ADR-081 (Advancement Effect Variant Expansion v1)

**Files:**
- Create: `docs/adr/081-advancement-effect-variant-expansion.md`

- [ ] **Step 1: Write the ADR**

Write the following to `docs/adr/081-advancement-effect-variant-expansion.md`:

```markdown
# ADR-081: Advancement Effect Variant Expansion (v1)

**Status:** Proposed
**Date:** 2026-04-18
**Deciders:** Keith Avery, Major Houlihan (Architect)
**Related:** ADR-078 (Edge/Composure/Advancement/Rituals), Epic 39

## Context

ADR-078 defined a five-variant `AdvancementEffect` enum (`EdgeMaxBonus`, `BeatDiscount`, `LeverageBonus`, `EdgeRecovery`, `LoreRevealBonus`) and named "ADR-079 — Affinity Hooks Enrichment" as the planned home for four additional variants flagged by the GM's initial draft. ADR-079 was subsequently assigned to *Genre Theme System Unification* (Accepted 2026-04-16), creating a numbering conflict. This ADR takes the next free slot (081) and intentionally scopes itself more narrowly than the original ADR-079 reservation.

During brainstorm authoring of Evropi starting kits (`docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md`), two `AdvancementEffect` variants surfaced as load-bearing at **Tier 1 / character creation**:

1. `AllyEdgeIntercept` — required for Prot'Thokk's *Lil' Sebastian Stands* (the ability that defines his character identity: he dies for the horse).
2. `ConditionalEffectGating` — required for Th`rook's *The Dose Helps* (pact mechanics that flip sign when reniksnad dependency crosses a threshold).

Both are needed to make day-one class differentiation mechanically real rather than narrator-fiat. Without them, Prot'Thokk and Th`rook are indistinguishable from a generic fighter and warlock on the GM panel — defeating the Sebastien-facing dashboard goal.

Other T2/T3 stubs surfaced in the character drafts (`AllyBeatDiscount`, `BetweenConfrontationsAction`, `AllyEdgeGrant`, `EdgeThresholdDelay`, `AllyAttentionIntercept`, `AllyInitiativeGrant`, `FactionTrackingDelay`, `PermanentPursuerDismissal`, `BetweenSessionIncome`, `NPCDebtLadder`, `PacingAcceleration`, `RecordSelfInsertion`, `OneShotNarrativePivot`, `RetroactivePresenceErasure`, `WorldStateInsertion`, `CampaignOnceResurrection`) are **explicitly deferred** to ADR-082+. They gate higher-tier content the playgroup is unlikely to reach in the near future, and designing enum architecture speculatively on stale requirements is wasted work.

## Decision

Extend the `AdvancementEffect` enum (defined in ADR-078) with exactly two new variants. All other requested variants remain deferred to future ADRs, with character YAML drafts carrying `effects: []  # TODO ADR-082+ — <reason>` stubs that preserve authored labels and narration_hints for later wiring.

### Variant 1: `AllyEdgeIntercept`

Redirects `target_edge_delta` from a designated ally to the actor. Self-sacrifice semantics.

```rust
AllyEdgeIntercept {
    /// CreatureCore identities (by name or tag) that this interception applies to.
    /// Empty allows any party ally.
    ally_whitelist: Vec<CreatureRef>,
    /// Maximum target_edge_delta the actor can absorb per redirect event.
    max_redirect: u32,
}
```

**Resolution semantics:**
- Fires as a *reaction* when an enemy beat would apply `target_edge_delta` to an ally matching `ally_whitelist`.
- Up to `max_redirect` of the incoming delta is subtracted from the actor's Edge instead of the ally's.
- Any remainder continues to the original ally target.
- Actor Edge is clamped to a minimum of 1 on the redirect (preventing instant self composure_break on interception — narrative grace).
- Engine emits `advancement.ally_edge_intercept` OTEL event with `actor`, `ally`, `original_delta`, `absorbed_delta`, `remainder`.

**Example (Prot'Thokk):**
```yaml
- id: lil_sebastian_stands
  effects:
    - type: ally_edge_intercept
      ally_whitelist: ["Cheeney", "Lil'Sebastian"]
      max_redirect: 3
```

### Variant 2: `ConditionalEffectGating`

Wraps another `AdvancementEffect` in a condition against character state (initially only ResourcePool threshold comparisons). The wrapped effect is active only when the condition is true; optional `when_false` enables a flipped effect for the opposite condition.

```rust
ConditionalEffectGating {
    condition: ConditionExpr,
    when_true: Box<AdvancementEffect>,
    when_false: Option<Box<AdvancementEffect>>,
}

enum ConditionExpr {
    ResourceAbove { resource: String, threshold: i32 },
    ResourceAtOrBelow { resource: String, threshold: i32 },
}
```

**Resolution semantics:**
- At the moment `resolved_beat_for` is computed for the actor, the condition is evaluated against current character state.
- If `condition` is true, `when_true` is applied as the effective `AdvancementEffect` for this resolution.
- If `condition` is false and `when_false` is `Some`, `when_false` is applied instead.
- If `condition` is false and `when_false` is `None`, no effect.
- Engine emits `advancement.conditional_effect_gating` OTEL event with `actor`, `condition`, `evaluated`, `applied_variant`.

**ConditionExpr grammar — scope note:** Initial release supports only the two ResourcePool comparators listed above. Boolean composition (AND/OR/NOT), multi-resource comparisons, and non-resource conditions are explicitly out of scope for v1.

**Example (Th`rook):**
```yaml
- id: the_dose_helps
  effects:
    - type: conditional_effect_gating
      condition:
        type: resource_above
        resource: reniksnad
        threshold: 5
      when_true:
        type: beat_discount
        beat_id: commit_cost
        resource_mod: { flesh: 1 }
      when_false:
        type: beat_discount        # same beat, inverted resource_mod
        beat_id: commit_cost
        resource_mod: { flesh: -1 }
```

## Scope

### In scope
- Add `AllyEdgeIntercept` variant to `AdvancementEffect` enum
- Add `ConditionalEffectGating` variant with initial `ConditionExpr` grammar
- OTEL events for both variants
- Update `resolved_beat_for` to evaluate conditional gating at resolution time
- Update reaction-dispatch path for intercept semantics (fires before ally Edge mutation)

### Out of scope
- All other deferred variants from the GM draft (listed in Context); these wait for ADR-082+
- Richer `ConditionExpr` grammar (boolean composition, multi-resource, non-resource)
- UI/protocol changes for the new variants (covered by Epic 39 story 7's composure sheet work)
- Authoring non-heavy_metal content that uses these variants

## Consequences

**Positive**
- Unblocks two character-defining Tier 1 abilities (Prot'Thokk's oath, Th`rook's pact mechanics)
- Tightly scoped — two variants, each named and required by a live character draft, not speculative
- Preserves the v1 enum's architectural discipline (no grab-bag enum expansion)
- Sebastien gets visible conditional-gating behavior on the GM panel

**Negative**
- Introduces reaction-dispatch semantics for `AllyEdgeIntercept` — new control flow path in beat resolution
- `ConditionalEffectGating` adds runtime condition evaluation to `resolved_beat_for`, slightly more complex than other variants
- 16+ other requested variants remain as `TODO ADR-082+` stubs; authors must keep two ADR numbers in mind when reading drafts

**Neutral**
- Follows ADR-078's ratified extension pattern (`LoreRevealBonus` was a similar single-variant extension)

## Alternatives considered

1. **Fiat-only (no new variants):** Prot'Thokk's horse-defense and Th`rook's dose-gated beats run under narrator interpretation. Rejected — defeats the GM-panel-visibility goal that makes Sebastien want the mechanical characters.
2. **Comprehensive variant expansion (all 16+ requested):** Define every deferred variant now. Rejected — most gate T2/T3 content the playgroup will not reach soon; speculative architecture on stale requirements.
3. **Reshape *Lil' Sebastian Stands* and *The Dose Helps* to existing day-1 variants:** Attempted during brainstorming. Neither ability maps cleanly — *Lil' Sebastian Stands* is fundamentally a target redirection (no existing variant does this), and *The Dose Helps* requires a bidirectional effect tied to mutable character state (no existing variant has conditional state checks). Rejected as infeasible.

## References

- ADR-078 — Edge/Composure/Advancement/Rituals (baseline enum)
- `docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md` — driving spec
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/prot_thokk.yaml` — `AllyEdgeIntercept` consumer (Lil' Sebastian Stands)
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml` — `ConditionalEffectGating` consumer (The Dose Helps)
```

- [ ] **Step 2: Validate markdown parses cleanly**

Run: `head -20 docs/adr/081-advancement-effect-variant-expansion.md`
Expected: Header block visible, status=Proposed, date=2026-04-18.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/081-advancement-effect-variant-expansion.md
git commit -m "$(cat <<'EOF'
docs(adr): ADR-081 — Advancement Effect Variant Expansion v1

Adds AllyEdgeIntercept (for Prot'Thokk's Lil' Sebastian Stands)
and ConditionalEffectGating (for Th'rook's The Dose Helps) to
the AdvancementEffect enum defined in ADR-078. Tightly scoped —
all other requested variants explicitly deferred to ADR-082+.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Update ADR index and ADR-078 cross-references

**Files:**
- Modify: `docs/adr/README.md`
- Modify: `docs/adr/078-edge-composure-advancement-rituals.md`

- [ ] **Step 1: Find and inspect the ADR README**

Run: `grep -n "ADR-079\|ADR-080\|ADR-081" docs/adr/README.md | head -5`
Expected: Existing entries for 079 (genre-theme-unification) and 080 (unified-narrative-weight-trait).

- [ ] **Step 2: Add ADR-081 line to ADR index**

Find the line referencing ADR-080 in `docs/adr/README.md` and add below it:

```markdown
- [ADR-081](081-advancement-effect-variant-expansion.md) — Advancement Effect Variant Expansion (v1): AllyEdgeIntercept + ConditionalEffectGating
```

Match existing index formatting (same table or list structure as surrounding ADR entries).

- [ ] **Step 3: Update ADR-078 forward-references**

Run: `grep -n "ADR-079" docs/adr/078-edge-composure-advancement-rituals.md`
Expected: Multiple references.

Open `docs/adr/078-edge-composure-advancement-rituals.md` and:
- Change `ADR-079 (Affinity Hooks Enrichment)` → `ADR-081 (Advancement Effect Variant Expansion v1) and ADR-082+ (deferred variants)`
- Change every remaining `ADR-079` in deferral language to `ADR-082+` (since the originally-four-deferred variants are still deferred beyond ADR-081's two)

- [ ] **Step 4: Verify no stale ADR-079 references remain in ADR-078**

Run: `grep -c "ADR-079" docs/adr/078-edge-composure-advancement-rituals.md`
Expected: `0`

- [ ] **Step 5: Commit**

```bash
git add docs/adr/README.md docs/adr/078-edge-composure-advancement-rituals.md
git commit -m "docs(adr): index ADR-081, retarget ADR-078 forward-refs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Update edge-advancement-content.md ADR references

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md`

- [ ] **Step 1: List all ADR-079 references in the content draft**

Run: `grep -n "ADR-079" sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md`
Expected: ~7 references inside YAML comment stubs and prose discussion.

- [ ] **Step 2: Rewrite each reference by category**

All references are about deferred variants — the file talks about Craft T2-T3 and Lore T2-T3 stubs. None of them are Prot'Thokk's AllyEdgeIntercept or Th`rook's ConditionalEffectGating. Therefore **every occurrence of ADR-079 in this file becomes ADR-082+**.

Use sed-equivalent via Edit tool — or apply these concrete replacements:

- `TODO ADR-079` → `TODO ADR-082+`
- `Deferred to ADR-079` → `Deferred to ADR-082+`
- `deferred to ADR-079` → `deferred to ADR-082+`
- `ADR-079 lands` → `the relevant follow-up ADR lands`
- `ADR-079 is filed` → `follow-up ADR(s) are filed`
- Remove any sentences claiming the follow-up ADR will be ADR-079 by name — replace with "a follow-up ADR in the 082+ range"

- [ ] **Step 3: Verify no stale ADR-079 references remain in the content draft**

Run: `grep -c "ADR-079" sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md`
Expected: `0`

- [ ] **Step 4: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md
git commit -m "content(heavy_metal): retarget ADR-079 refs to ADR-082+

Original ADR-079 reservation was displaced by genre-theme-unification
ADR-079. ADR-081 covers the two v1 variants needed now; everything
else deferred to ADR-082+.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Sweep character YAML TODO comments from ADR-079 to ADR-082+

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/rux.yaml`
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/prot_thokk.yaml`
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/hant.yaml`
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/pumblestone_sweedlewit.yaml`
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/ludzo.yaml`
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/README.md`

- [ ] **Step 1: List all ADR-079 references across the character-progression folder**

Run: `grep -rn "ADR-079" sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/`
Expected: ~18 references across the files listed above.

- [ ] **Step 2: Rewrite by variant**

Within these files, **all stubs** refer to deferred variants; **none of them** refer to the two that are landing in ADR-081. The Prot'Thokk `AllyEdgeIntercept` stub is the special case: it gets promoted to ADR-081 (not deferred). The Th`rook file does not exist yet — it will be authored fresh in Task 5 with the correct ADR references from the start.

For each file (except Th`rook):
- **Prot'Thokk** (`prot_thokk.yaml`): change the three `TODO ADR-079 — needs AllyEdgeIntercept`-style comments so that — the `Lil' Sebastian Stands` tier-1 node becomes `effects:` with an actual `ally_edge_intercept` entry (see Step 3 below — that's an ADR-081 consumer, not a stub). The other two `AllyEdgeIntercept` references in the file (tier-3 *Master Is Still Protected* and the other tier-2 *Mistos Can Wait* if present) remain as stubs but with `TODO ADR-082+` if they still need variants not in ADR-081's scope. Inspect each one.
- **All other files** (rux, hant, pumblestone_sweedlewit, ludzo, README): blanket `TODO ADR-079` → `TODO ADR-082+`.

- [ ] **Step 3: Promote Prot'Thokk's *Lil' Sebastian Stands* tier-1 stub to a concrete ADR-081 effect**

In `prot_thokk.yaml`, find the `lil_sebastian_stands` node (currently under the `over_the_horse` path, tier 1). Its `effects:` field currently is:

```yaml
        effects: []  # TODO ADR-079 — needs AllyEdgeIntercept variant specifically
                      # gated on {Cheeney, horse}
```

Replace with:

```yaml
        effects:
          - type: ally_edge_intercept
            ally_whitelist: ["Cheeney", "Lil'Sebastian"]
            max_redirect: 3
          # Lands with ADR-081. See docs/adr/081-advancement-effect-variant-expansion.md.
```

Keep the node's existing `narration_hint` intact — no prose changes.

- [ ] **Step 4: Verify no stale ADR-079 references remain in the folder**

Run: `grep -rc "ADR-079" sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/`
Expected: Every file shows `0`.

- [ ] **Step 5: Verify YAML still parses for each character file**

Run:
```bash
for f in sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/*.yaml; do
  python3 -c "import yaml; yaml.safe_load(open('$f'))" && echo "  OK: $f"
done
```
Expected: Every file prints `OK`.

- [ ] **Step 6: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/
git commit -m "content(evropi): retarget ADR-079 stubs; wire Lil' Sebastian Stands

Blanket TODO ADR-079 -> TODO ADR-082+ across character YAMLs.
Prot'Thokk's Lil' Sebastian Stands tier-1 promoted from stub to
concrete ally_edge_intercept (ADR-081 consumer).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Author Th`rook character YAML

**Files:**
- Create: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml`

- [ ] **Step 1: Write the full Th`rook YAML**

Create `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml` with the following content:

```yaml
# Th`rook — Pakook`rook Warlock, reniksnad-dependent
# PLACEHOLDER NAME — awaiting Sebastien confirmation. Replace `th_rook`/`Th`rook`
# throughout this file at chargen if a canonical name is provided.
#
# Layered on top of heavy_metal/progression.yaml baseline affinity effects.
# No save file yet (~/.sidequest/saves/heavy_metal/evropi/th_rook/) — created
# on first play.

character:
  save_id: th_rook
  name: Th`rook
  race: Pakook`rook
  class: Warlock
  affinity_emphasis:
    primary: [Pact, Ruin]
    secondary: [Lore]
    rare: [Court]
    absent: [Iron, Craft]

starting_kit:
  label: "Sung to the Rock Beneath the Water"
  flavor: "A pact older than the kingdom. It answers the knotsong. It does not care that he is dying."
  grants:
    - id: knotsung_name
      label: "Knotsung Name"
      narration_hint: |
        The patron's name is easier to sing than to speak. Th`rook inflates
        his throat-sac and invokes the pact through knotsong; the invocation
        costs less Voice than a spoken working would. Half a song and half
        a prayer.
      effects:
        - { type: beat_discount, beat_id: invoke, resource_mod: { voice: 1 } }

    - id: creditors_mark
      label: "Creditor's Mark"
      narration_hint: |
        Th`rook recognizes signs of other working in the world — another
        warlock's pact-creditor, an unclosed rite, a place that has been
        negotiated over. Narrator reveals one true fact about any such
        sign on first encounter.
      effects:
        - { type: lore_reveal_bonus, scope: pact_creditor_sign }

    - id: the_dose_helps
      label: "The Dose Helps"
      narration_hint: |
        Reniksnad blunts the body's score-keeping. While Th`rook's reniksnad
        resource is above 5, the commit_cost beat costs 1 less Flesh — the
        drug silences the body's feedback. Below 5 (withdrawal), the same
        beat costs 1 MORE Flesh — the body demands its own attention when
        the drug is not there to silence it. The mechanical line is legible
        to anyone watching the GM panel.
      effects:
        - type: conditional_effect_gating
          condition:
            type: resource_above
            resource: reniksnad
            threshold: 5
          when_true:
            type: beat_discount
            beat_id: commit_cost
            resource_mod: { flesh: 1 }
          when_false:
            type: beat_discount
            beat_id: commit_cost
            resource_mod: { flesh: -1 }
          # Lands with ADR-081. See docs/adr/081-advancement-effect-variant-expansion.md.

character_resources:
  - name: reniksnad
    label: "Reniksnad"
    min: 0
    max: 10
    starting: 7
    voluntary: false
    decay_per_scene: 1
    refill_trigger: "narrator-authored dose event (Wazdia-controlled supply)"
    thresholds:
      - at: 5
        event_id: reniksnad_first_tremor
        narrator_hint: "His hand shakes slightly when he reaches for water. A Wazdia informer would note it."
        direction: crossing_down
      - at: 3
        event_id: reniksnad_withdrawal
        narrator_hint: "Withdrawal has begun. His voice thins; knotsongs fail on the high notes. Voice-spends cost 1 more per invocation while he is here."
        direction: crossing_down
      - at: 0
        event_id: reniksnad_death_clock
        narrator_hint: "The clock has started. He will die within one in-fiction week without another dose. Narrator: this is not dramatic; it is medical."
        direction: crossing_down

trunk:
  id: the_patron_answers_the_knotsong
  label: "The Patron Answers the Knotsong"
  narration_hint: |
    The pact is older than the Zkęd kingdom. It lives in the water where
    reeds meet rock. When Th`rook sings a knotsong — inflated throat-sac,
    eyes half-closed — something answers. Narrator: the patron is never
    fully described, never named in full. Its presence is a pressure and
    a permission. NPCs who hear the knotsong feel nothing consciously;
    Pakook`rook who hear it recognize it and know to look away.
  effects: []   # Trunk carries no mechanical effect beyond the KnownFact
                # injection — ADR-078 baseline Pact tier effects will stack
                # when he crosses Pact thresholds.

paths:
  - id: the_songsworn
    label: "The Songsworn"
    flavor: "The pact itself — voice, flesh, and ledger spent into the water. Bargained magic at its most literal."
    nodes:
      - tier: 1
        id: the_water_is_deep_enough
        label: "The Water Is Deep Enough"
        milestone_category: revelation
        grant_trigger:
          condition: "affinity:Pact:tier:1"
        narration_hint: |
          Near standing water deeper than Th`rook's waist, his pact workings
          resolve as though rehearsed. Narrator treats the invocation as
          having already steadied before he began.
        effects:
          - { type: beat_discount, beat_id: steady_the_rite, resource_mod: { voice: 1 } }

      - tier: 2
        id: the_patron_remembers_the_song
        label: "The Patron Remembers the Song"
        milestone_category: debt
        grant_trigger:
          condition: "affinity:Pact:tier:2"
        narration_hint: |
          When Th`rook closes the book after a working at or near standing
          water, the patron accepts the terms more quickly. Ledger entries
          write themselves shorter.
        effects:
          - { type: beat_discount, beat_id: close_the_book, resource_mod: { ledger: 1 } }

      - tier: 3
        id: sung_into_the_rock
        label: "Sung Into the Rock"
        milestone_category: reckoning
        grant_trigger:
          condition: "affinity:Pact:tier:3"
          usage: "1/arc"
        narration_hint: |
          Once per arc, Th`rook may complete a pact working in a single
          exchange at the site where the swamp meets rock. The patron
          answers in full. Whatever was requested arrives. The price is
          paid simultaneously — and legibly — across all four resources.
        effects:
          - { type: beat_discount, beat_id: force_completion, resource_mod: { ledger: 2, flesh: 1 } }

  - id: the_pe_quiet
    label: "The Pę Quiet"
    flavor: "The addict's hard-won self-knowledge. Not freedom — familiarity."
    nodes:
      - tier: 1
        id: tremor_as_tell
        label: "Tremor as Tell"
        milestone_category: revelation
        grant_trigger:
          condition: "affinity:Ruin:tier:1"
        narration_hint: |
          Th`rook recognizes another reniksnad-addict in any scene. Narrator
          reveals one true fact about their supply — where they get it,
          who they owe, how far from their last dose.
        effects:
          - { type: lore_reveal_bonus, scope: reniksnad_addict }

      - tier: 2
        id: the_body_keeps_its_own_ledger
        label: "The Body Keeps Its Own Ledger"
        milestone_category: ruin
        grant_trigger:
          condition: "affinity:Ruin:tier:2"
        narration_hint: |
          At reniksnad withdrawal (current <= 3), Th`rook's pact workings
          gain a bitter precision. The body is paying attention for him.
        effects:
          - type: conditional_effect_gating
            condition:
              type: resource_at_or_below
              resource: reniksnad
              threshold: 3
            when_true:
              type: leverage_bonus
              beat_id: commit_cost
              target_edge_delta_mod: -1
          # Lands with ADR-081. See docs/adr/081-advancement-effect-variant-expansion.md.

      - tier: 3
        id: dying_but_not_yet
        label: "Dying But Not Yet"
        milestone_category: reckoning
        grant_trigger:
          condition: "affinity:Ruin:tier:3"
          usage: "1/arc"
        narration_hint: |
          Once per arc, at reniksnad = 0 (the death-clock started), Th`rook
          may invoke the pact's emergency clause. The patron defers his
          death by one week at the cost of an unspecified future service.
          Narrator commits to the service later, at a moment of their
          choosing; Th`rook cannot refuse it.
        effects: []   # TODO ADR-082+ — needs DeferredNarratorDebt variant
                      # (out-of-confrontation permanent character flag that
                      # triggers a narrator-authored scene later)

  - id: the_north_road
    label: "The North Road"
    flavor: "The patron named a place. Th`rook is walking toward it. The reniksnad supply south is behind him now."
    nodes:
      - tier: 1
        id: away_from_the_supply
        label: "Away From the Supply"
        milestone_category: oath
        grant_trigger:
          condition: "affinity:Lore:tier:1"
        narration_hint: |
          Th`rook recognizes Wazdia informers, tax-collectors, and
          reniksnad-trade agents on sight. Narrator reveals their role
          on first appearance.
        effects:
          - { type: lore_reveal_bonus, scope: wazdia_reniksnad_agent }

      - tier: 2
        id: the_named_place
        label: "The Named Place"
        milestone_category: revelation
        grant_trigger:
          condition: "affinity:Lore:tier:2"
          usage: "1/session"
        narration_hint: |
          Once per session, Th`rook knows whether the scene's current
          location is closer to or farther from the place the patron
          named. Narrator answers concretely.
        effects:
          - { type: lore_reveal_bonus, scope: patron_destination_proximity }

      - tier: 3
        id: arrival
        label: "Arrival"
        milestone_category: reckoning
        grant_trigger:
          condition: "affinity:Lore:tier:3"
          usage: "1/arc"
          location: "the place the patron named"
        narration_hint: |
          At arrival. The patron speaks in full, once. Narrator authors the
          scene. Whatever the patron is becomes legible to the party.
          Th`rook's reniksnad dependency ends OR transforms — narrator's
          call.
        effects: []   # TODO ADR-082+ — needs PermanentCharacterTransform variant
                      # (mutate character state + resources + narrator contract
                      # in one event)

capstones:
  unlock_condition: "any path tier 2 reached"
  choose: 1
  options:
    - id: the_knotsong_teacher
      label: "The Knotsong Teacher"
      narration_hint: |
        Th`rook takes on an apprentice — a freed Pakook`rook child or a
        Waterfolk bard willing to learn. He teaches the knotsong. The
        apprentice's presence grants Th`rook one additional Voice spend
        per session before thresholds apply.
      permanent_effect: "Apprentice NPC companion; +1 voluntary Voice spend/session budget."
      effects: []   # TODO ADR-082+ — needs PartyMemberGrant + ResourceBudgetBonus variants

    - id: the_freed_water
      label: "The Freed Water"
      narration_hint: |
        Th`rook establishes a safe marsh-settlement for other Pakook`rook
        walking north. The patron approves; the Wazdia does not. Narrator
        treats this location as a recurring safe harbor, with cost.
      permanent_effect: "Named safe-harbor location with factional heat; narrator-authored."
      effects:
        - { type: lore_reveal_bonus, scope: freed_water_settlement }

    - id: the_reniksnad_broken
      label: "The Reniksnad Broken"
      narration_hint: |
        Th`rook breaks the reniksnad dependency through a pact-working that
        substitutes his patron's presence for the drug. He does not die.
        But he also cannot be more than a day's travel from deep water for
        the rest of his life.
      permanent_effect: "Reniksnad resource removed. Geographic constraint added. Narrator-authored."
      effects: []   # TODO ADR-082+ — needs PermanentCharacterTransform variant
```

- [ ] **Step 2: Verify YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml'))"`
Expected: No output (successful parse).

- [ ] **Step 3: Verify no stale `pe` references (drug/city confusion audit)**

Run: `grep -n "pe_\|\"pe\"\|: pe$\| pe " sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml`
Expected: `0` matches (no ambiguous `pe` identifiers; only proper `Pę` city references in prose and `reniksnad` resource identifiers).

Note: The path id `the_pe_quiet` (The Pę Quiet) is intentional — it's a prose reference to the Pę city, not the drug. Verify manually that the grep flagged (if any) only this deliberate use.

- [ ] **Step 4: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml
git commit -m "content(evropi): add Th'rook (Pakook'rook Warlock)

Full character YAML for Sebastien's option. Includes starting_kit
(3 grants, one ADR-081 consumer), character_resources (reniksnad
with three thresholds), trunk, three paths, three capstones.
Backstory: Pę slave city, reniksnad dependency, pact with swamp-
rock entity, walking north toward the patron's named place.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Add starting_kit to Rux

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/rux.yaml`

- [ ] **Step 1: Insert starting_kit block**

In `rux.yaml`, locate the end of the top-level `character:` block (just before the line `trunk:`). Insert the following `starting_kit:` block between `character:` and `trunk:`:

```yaml
starting_kit:
  label: "Servant of the Old Line"
  flavor: "The Tismenni taught their servants three kinds of attention: what is written, where to strike, and how not to be seen."
  grants:
    - id: kept_the_masters_books_kit
      label: "Kept the Master's Books"
      narration_hint: |
        Rux recognizes a sigil, script, or heraldry from 12,000-year
        archive-memory. Narrator reveals one true fact about any written
        or sigiled object he touches, once per scene, auto-success.
      effects:
        - { type: lore_reveal_bonus, scope: written_object }

    - id: strike_from_the_low_line_kit
      label: "Strike from the Low Line"
      narration_hint: |
        Rux's strikes land where Tismenni scholars taught their servants
        to strike. Narrator describes precision, not force — scholar-killer
        language, never duelist. STR 8 is not a constraint on his damage
        language.
      effects:
        - { type: leverage_bonus, beat_id: strike, target_edge_delta_mod: -1 }

    - id: already_dismissed_kit
      label: "Already Dismissed"
      narration_hint: |
        Once per scene while Rux is at half Edge or below, an enemy's eye
        slides past him; a successful beat of his restores composure the
        narrator describes as the posture of having been overlooked.
      effects:
        - { type: edge_recovery, trigger: { type: on_beat_success, while_strained: true }, amount: 2 }
```

Note: The three kit grants mirror the path-tier-1 node effects in the same file, but each uses a `_kit` suffix on the id to prevent collision with the tier-1 nodes that will (eventually) also grant through affinity progression. This is intentional — the kit grants are the *chargen* copy, the tier nodes are the *progression* copy, and during Epic 39 hydration both may be present.

- [ ] **Step 2: Verify YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/rux.yaml'))"`
Expected: No output.

- [ ] **Step 3: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/rux.yaml
git commit -m "content(evropi): add Rux starting_kit (Servant of the Old Line)

Three day-one grants: Kept the Master's Books (lore_reveal_bonus),
Strike from the Low Line (leverage_bonus), Already Dismissed
(edge_recovery while_strained). All day-1 enum.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Add starting_kit to Prot'Thokk

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/prot_thokk.yaml`

- [ ] **Step 1: Insert starting_kit block**

In `prot_thokk.yaml`, between `character:` and `trunk:`, insert:

```yaml
starting_kit:
  label: "The One Who Stands Between"
  flavor: "Three postures: the wall, the broken chain, the body that will not let the horse fall."
  grants:
    - id: stand_in_front_kit
      label: "Stand in Front"
      narration_hint: |
        While Prot'Thokk is at full Edge, adjacent allies benefit from his
        bearing. Narrator describes enemies reading the room and picking
        easier targets. This is posture, not shield.
      effects:
        - { type: edge_max_bonus, amount: 1 }
        - { type: beat_discount, beat_id: brace, edge_delta_mod: -1 }

    - id: broke_the_chains_kit
      label: "Broke the Chains"
      narration_hint: |
        Prot'Thokk frees a bound or captured ally as a single action.
        No lock-roll, no guard-beat. The narrator allows the break.
        Every time he does this, the moment with Cheeney re-surfaces
        in his bearing.
      effects:
        - { type: beat_discount, beat_id: refuse, edge_delta_mod: -1 }

    - id: lil_sebastian_stands_kit
      label: "Lil' Sebastian Stands"
      narration_hint: |
        Any hostile beat targeting Cheeney or Lil' Sebastian (the horse)
        can be intercepted. Prot'Thokk absorbs up to 3 points of the
        target_edge_delta as his own Edge loss; any remainder continues
        to the ally. Actor Edge is clamped to 1 minimum on the redirect
        so the intercept cannot self-break him on the first hit.
      effects:
        - type: ally_edge_intercept
          ally_whitelist: ["Cheeney", "Lil'Sebastian"]
          max_redirect: 3
      # Lands with ADR-081. See docs/adr/081-advancement-effect-variant-expansion.md.
```

Note: *Stand in Front* is a compound grant (two effects under one grant id). If the hydration schema turns out to require one effect per grant, split this into two grants in a follow-up. Flagged in the spec's Open Items #2.

- [ ] **Step 2: Verify YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/prot_thokk.yaml'))"`
Expected: No output.

- [ ] **Step 3: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/prot_thokk.yaml
git commit -m "content(evropi): add Prot'Thokk starting_kit (The One Who Stands Between)

Three day-one grants: Stand in Front (compound edge_max_bonus +
brace discount), Broke the Chains (refuse discount), Lil' Sebastian
Stands (ADR-081 ally_edge_intercept). Prot'Thokk's character-
defining oath is mechanically real at turn one.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Add starting_kit to Hant

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/hant.yaml`

- [ ] **Step 1: Insert starting_kit block**

In `hant.yaml`, between `character:` and `trunk:`, insert:

```yaml
starting_kit:
  label: "Composer on the Surface"
  flavor: "Surface strangers, pheromone-courts, the current he followed up out of the Deep Hollows. All three are crafts."
  grants:
    - id: drowse_kit
      label: "Drowse"
      narration_hint: |
        Once per scene, Hant destabilizes one enemy through pheromone
        composition. Narrator describes sudden fatigue, a misplaced word,
        a step out of stance. No NPC in the scene ever attributes the
        effect to Hant.
      effects:
        - { type: leverage_bonus, beat_id: argue, target_edge_delta_mod: -2 }

    - id: pheromone_court_etiquette_kit
      label: "Pheromone-Court Etiquette"
      narration_hint: |
        Once per scene, Hant reads an NPC's emotional state. Narrator
        answers truthfully and concretely ("she is afraid of the older
        priest"), never vaguely ("she seems nervous").
      effects:
        - { type: lore_reveal_bonus, scope: emotional_state }

    - id: surface_stranger_kit
      label: "Surface Stranger"
      narration_hint: |
        NPCs who have never seen an antman default to wonder or menace
        on first meeting, not hostility. Hant's opening social beat in
        any scene with new NPCs resolves cleaner.
      effects:
        - { type: beat_discount, beat_id: argue, edge_delta_mod: -1 }
```

- [ ] **Step 2: Verify YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/hant.yaml'))"`
Expected: No output.

- [ ] **Step 3: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/hant.yaml
git commit -m "content(evropi): add Hant starting_kit (Composer on the Surface)

Three day-one grants: Drowse (leverage on argue), Pheromone-Court
Etiquette (emotional_state reveal), Surface Stranger (argue discount).
All day-1 enum. Hant has mechanical presence at turn one despite
heavier T2/T3 ally-variant dependencies.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Add starting_kit to Pumblestone

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/pumblestone_sweedlewit.yaml`

- [ ] **Step 1: Insert starting_kit block**

In `pumblestone_sweedlewit.yaml`, between `character:` and `trunk:`, insert:

```yaml
starting_kit:
  label: "The Sage Who Misremembers"
  flavor: "Three ways to know: by reading, by owing, by being unsure. All three produce answers."
  grants:
    - id: read_what_others_cant_kit
      label: "Read What Others Can't"
      narration_hint: |
        Any text in an older script resolves for Pumblestone without
        check. He reads it. He may misquote it later — narrator may have
        him do so at their discretion — but he reads it now.
      effects:
        - { type: lore_reveal_bonus, scope: older_script }

    - id: owed_future_kit
      label: "Owed Future"
      narration_hint: |
        Once per scene, Pumblestone casts a working without naming the
        cost aloud. The invocation costs less Voice up front; narrator
        defers the remainder of the cost to a moment of narrator's
        choosing.
      effects:
        - { type: beat_discount, beat_id: invoke, resource_mod: { voice: 1 } }

    - id: one_map_is_right_kit
      label: "One Map Is Right"
      narration_hint: |
        Once per scene with conflicting intel, Pumblestone declares which
        source is true. Narrator honors it — even if Pumblestone is sure
        of the reasoning for the wrong reasons.
      effects:
        - { type: lore_reveal_bonus, scope: conflicting_intel }
```

- [ ] **Step 2: Verify YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/pumblestone_sweedlewit.yaml'))"`
Expected: No output.

- [ ] **Step 3: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/pumblestone_sweedlewit.yaml
git commit -m "content(evropi): add Pumblestone starting_kit (The Sage Who Misremembers)

Three day-one grants: Read What Others Can't (older_script reveal),
Owed Future (invoke voice discount), One Map Is Right (conflicting_intel
reveal). All day-1 enum.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Add starting_kit to Ludzo (test inheritance)

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/ludzo.yaml`

- [ ] **Step 1: Insert starting_kit inheritance block**

In `ludzo.yaml`, between `character:` and `trunk:`, insert:

```yaml
starting_kit:
  inherits: rux
  note: |
    Test character — mirrors Rux's starting_kit for QA and regression
    playtests. Ludzo's own trunk, paths, and capstones remain authored
    below for flavor continuity, but the mechanical day-one grants
    resolve from rux.yaml's starting_kit block. Keith's sandbox.
```

- [ ] **Step 2: Verify YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/ludzo.yaml'))"`
Expected: No output.

- [ ] **Step 3: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/ludzo.yaml
git commit -m "content(evropi): Ludzo starting_kit inherits Rux (test sandbox)

Ludzo is Keith's QA character. Mechanical day-one grants inherit
from rux.yaml; flavor content (trunk/paths/capstones) stays
authored as Ludzo's own.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Update character-progression README

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/README.md`

- [ ] **Step 1: Update the file index and scope tally**

Replace the current `## Files in this folder` and `## Scope tally` sections with:

```markdown
## Files in this folder

- `rux.yaml` — Kobold Rogue, Tismenni servant-line
- `prot_thokk.yaml` — Half-Orc Fighter, Cheeney's guardian (consumes ADR-081 `ally_edge_intercept`)
- `hant.yaml` — Antman Bard, pheromone-composer (heavy ADR-082+ dependency for T2/T3 ally variants)
- `ludzo.yaml` — Human Rogue, Zkęd exile (test sandbox — starting_kit inherits rux)
- `pumblestone_sweedlewit.yaml` — Gnome Wizard, forgetful sage
- `th_rook.yaml` — Pakook`rook Warlock, reniksnad-dependent (consumes ADR-081 `conditional_effect_gating`; character_resources: reniksnad)

## Scope tally

5 playgroup characters + 1 test sandbox = 6 files.

**Starting kits:** 3 grants per character. All day-1 enum effects EXCEPT:
- Prot'Thokk's *Lil' Sebastian Stands* uses ADR-081 `ally_edge_intercept`
- Th`rook's *The Dose Helps* uses ADR-081 `conditional_effect_gating`
- Th`rook's path *The Body Keeps Its Own Ledger* (tier 2) uses ADR-081 `conditional_effect_gating` (future progression, not day-one)

**Progression content (trunk + paths + capstones):** 13 nodes per character = 65 additional content entries. Roughly half land on day-1 enum; roughly half ship as ADR-082+ stubs with preserved labels and narration_hints.

**Character resources:** Th`rook has a character-scoped `reniksnad` ResourcePool (new schema extension alongside the genre-level Voice/Flesh/Ledger).

**Sunday deployment:** All five playgroup characters run under GM fiat via `../sunday-progression.md`. Post-Epic-39 story 5: starting kits and character resources hydrate at chargen.

(Aberu Kisu retired 2026-04-18.)
```

- [ ] **Step 2: Verify markdown renders cleanly**

Run: `head -80 sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/README.md`
Expected: The Scope tally and Files sections show the updated counts and file list.

- [ ] **Step 3: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/README.md
git commit -m "docs(evropi): update character-progression README for Th'rook + kits

Scope tally now reflects 5 playgroup + 1 sandbox, starting_kit
pattern, ADR-081 consumers, character-scoped reniksnad resource.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Append Th`rook section to sunday-progression.md

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/sunday-progression.md`

- [ ] **Step 1: Insert Th`rook section before the Milestone seeds table**

Open `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/sunday-progression.md`. Find the line `## Milestone seeds for Sunday`. Insert the following **immediately before** that line (including the `---` separator):

```markdown
## Th`rook — Pakook`rook Warlock, reniksnad-dependent

**Name:** Placeholder **Th`rook** until Sebastien confirms a canonical name from prior conversation.

**Trunk — *The Patron Answers the Knotsong*** (persistent)
> The pact is older than the Zkęd kingdom. It lives in the water where reeds meet rock. When Th`rook sings a knotsong — inflated throat-sac, eyes half-closed — something answers. The patron is never fully described, never named in full. Its presence is a pressure and a permission. NPCs who hear the knotsong feel nothing consciously; Pakook`rook who hear it recognize it and know to look away.

**Day-one starting kit — *Sung to the Rock Beneath the Water*:**
- *Knotsung Name* — invocations through knotsong cost 1 less Voice. He inflates the throat-sac and sings the patron's name.
- *Creditor's Mark* — Th`rook recognizes other warlocks' pact-creditors on sight. Narrator reveals one true fact about any such sign on first encounter.
- *The Dose Helps* — **reniksnad-dependent trade-off.** While his reniksnad is above 5, the commit_cost beat costs 1 less Flesh — the drug silences the body. At reniksnad 5 or below (withdrawal), the same beat costs 1 more Flesh. The drug is mechanically productive until it isn't.

**Character resource — Reniksnad (tracked manually by GM this session):**
Starting value: **7** (mid-range, already-addicted baseline).
Decay: **1 per scene**.
Thresholds:
- **At 5** — *first tremor.* His hand shakes slightly when he reaches for water. A Wazdia informer would note it.
- **At 3** — *withdrawal.* His voice thins; knotsongs fail on the high notes. Voice-spends cost 1 more per invocation while he is here.
- **At 0** — *death clock.* He will die within one in-fiction week without another dose. The narrator plays this medically, not dramatically.

Refill: **narrator-authored dose event only.** The Wazdia controls the reniksnad supply south of the Zbóźny foothills. The party may source doses through trade, theft, or a freedman's clandestine line; every option is a scene.

**Backstory:** Born in Pę (the Zkędzała slave-city), force-fed reniksnad from childhood to keep the labor compliant. Somewhere in his teens, working alone in the reed-beds, he heard something in the deep swamp sing back to his knotsong — and negotiated. The pact freed him from the Zkęd. It did not free him from the reniksnad. The patron does not know or care about withdrawal; it cares about the knotsong being sung and the water being deep enough. Th`rook is walking north because the patron named a place, and because the Wazdia's supply is south and he will not go south again.

**The Songsworn** (pact signature path)
- *The Water Is Deep Enough* — pact workings near standing water deeper than waist-height resolve as if rehearsed. Narrator treats invocations as already-steadied.
- *The Patron Remembers the Song* — closing the book on a working at standing water costs less Ledger.
- *Sung Into the Rock* — **1/arc, at the patron's named place only.** The patron answers in full. Whatever is requested arrives; the price is paid simultaneously across all four resources.

**The Pę Quiet** (the addict's hard-won self-knowledge)
- *Tremor as Tell* — recognizes other reniksnad-addicts on sight. Narrator reveals one truth about their supply.
- *The Body Keeps Its Own Ledger* — at withdrawal (reniksnad ≤3), his pact workings gain a bitter precision. Narrator describes the body paying attention for him.
- *Dying But Not Yet* — **1/arc, at reniksnad=0.** Invoke the pact's emergency clause. The patron defers his death by one week at the cost of an unspecified future service the narrator commits to later.

**The North Road** (the buried place, his version)
- *Away From the Supply* — recognizes Wazdia informers, tax-collectors, and reniksnad-trade agents on sight.
- *The Named Place* — once per session, knows whether the current location is closer to or farther from the place the patron named.
- *Arrival* — **1/arc, at arrival only.** The patron speaks in full. Narrator authors the scene. Reniksnad dependency ends or transforms.

**Servitude Thread** (pick ONE at any path's tier 2)
- **The Knotsong Teacher** — takes on an apprentice (freed Pakook`rook child or Waterfolk bard). Their presence grants 1 additional Voice spend per session.
- **The Freed Water** — establishes a safe marsh-settlement for other Pakook`rook walking north. Recurring safe harbor, factional heat.
- **The Reniksnad Broken** — pact-working substitutes patron's presence for the drug. He does not die. But he cannot be more than a day's travel from deep water for the rest of his life.

**Narrator note for Sunday:** Th`rook's reniksnad is the party's shared clock. The GM (Keith) decrements it by 1 at each scene end. At thresholds, the narrator is **required** to deliver the hint prose — not as flavor, as mechanical honesty. If the party finds or trades for a dose, Keith names the refill amount at the moment of administration (typical: +3 to +5, depending on the dose source's quality). Wazdia-supplied reniksnad refills more reliably than street-sourced.

---
```

- [ ] **Step 2: Update the milestone seeds table to include Th`rook**

Still in `sunday-progression.md`, find the milestone seeds table (the `| Character | Seed 1 |...` table). Add a Th`rook row after the Pumblestone row:

```markdown
| Th`rook | swear a knotsong to the party in the patron's hearing | survive a withdrawal scene by a single scene break | refuse a Wazdia dose-offer with a tactical cost |
```

- [ ] **Step 3: Verify no stale references**

Run: `grep -cn "Aberu\|aberu" sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/sunday-progression.md`
Expected: `0`.

- [ ] **Step 4: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/sunday-progression.md
git commit -m "content(evropi): append Th'rook to Sunday progression sheet

Full Th'rook section with trunk, starting kit, reniksnad resource
guidance (decrement cadence + threshold hints), three paths, three
capstones, narrator note. Milestone seeds table gains Th'rook row.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Final cross-reference audit

**Files:**
- (Read-only verification across the modified files)

- [ ] **Step 1: Confirm no stale ADR-079 references anywhere**

Run:
```bash
grep -rn "ADR-079" \
  docs/adr/078-edge-composure-advancement-rituals.md \
  docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md \
  sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md \
  sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/
```
Expected: **No output** (the only ADR-079 in the repo is the file itself, `docs/adr/079-genre-theme-unification.md`, which is the legitimate genre-theme ADR).

- [ ] **Step 2: Confirm no stale Aberu references**

Run:
```bash
grep -rn "Aberu\|aberu" \
  docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md \
  sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/
```
Expected: **No output** (Aberu retired in the design phase).

- [ ] **Step 3: Confirm all 6 character YAML files parse**

Run:
```bash
for f in sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/*.yaml; do
  python3 -c "import yaml; yaml.safe_load(open('$f'))" && echo "  OK: $f"
done
```
Expected: 6 lines, each `OK: <filename>` (rux, prot_thokk, hant, ludzo, pumblestone_sweedlewit, th_rook).

- [ ] **Step 4: Confirm all 6 character files have a starting_kit block**

Run:
```bash
grep -l "^starting_kit:" sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/*.yaml | wc -l
```
Expected: `6`.

- [ ] **Step 5: Confirm ADR-081 is referenced by exactly the two expected consumers**

Run:
```bash
grep -rln "ADR-081\|adr/081" \
  sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/
```
Expected: `prot_thokk.yaml` and `th_rook.yaml` — exactly those two files.

- [ ] **Step 6: Confirm no stale reniksnad/pe confusion**

Run:
```bash
grep -rn "force.fed pę\|pę supply\|pę dependency\|pe_first_tremor\|pe_withdrawal\|pe_death_clock\|name: pe$\|label: \"Pę\"" \
  sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/ \
  docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md
```
Expected: **No output** (all drug references are `reniksnad`; `Pę` only appears as the city name in prose contexts).

- [ ] **Step 7: Final sign-off commit (empty but purposeful)**

If any of steps 1–6 surfaced inconsistencies, fix them inline and commit the fix with a descriptive message. If all pass cleanly, write a short audit note file and commit:

```bash
cat > /tmp/audit-note.md <<'EOF'
# Evropi Starting Kits Implementation — Audit 2026-04-18

All cross-reference checks passed:
- No stale ADR-079 references in spec, ADR-078, edge-advancement-content, or character-progression drafts
- No stale Aberu references
- All 6 character YAMLs parse cleanly
- All 6 character files carry a starting_kit block
- ADR-081 referenced by exactly prot_thokk.yaml and th_rook.yaml
- No reniksnad/pe confusion in drug-vs-city usage

Ready for Epic 39 story 5 hydration consumption.
EOF

# Keep the audit note with the draft cluster so its provenance is clear.
mv /tmp/audit-note.md sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/AUDIT-2026-04-18.md
git add sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/AUDIT-2026-04-18.md
git commit -m "docs(evropi): audit sign-off — Evropi starting-kits content complete

All cross-reference checks passed. Content ready for Epic 39
story 5 hydration.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Summary

13 tasks, all content-layer or ADR-authoring. No engine code, no tests (YAML parse checks and grep audits substitute for traditional test-first flow on pure content). Every task produces a committable, self-contained change.

**Deliverables on completion:**
- ADR-081 covering two new `AdvancementEffect` variants (`AllyEdgeIntercept`, `ConditionalEffectGating`)
- ADR-078 and edge-advancement-content.md reference hygiene (ADR-079 → ADR-081/ADR-082+ split)
- 5 playgroup character YAML files with `starting_kit` blocks (Rux, Prot'Thokk, Hant, Pumblestone, Th`rook)
- 1 test-sandbox character (Ludzo) with inherited kit
- Th`rook full character draft including `character_resources` (reniksnad)
- Sunday-progression.md extended with Th`rook section and reniksnad guidance
- character-progression README bumped to new scope tally
- Final audit note confirming consistency

**Sunday usability:** All five playgroup characters and the reniksnad clock are usable at the table via GM fiat, using the `sunday-progression.md` sheet as narrator-facing prose context.

**Epic 39 handoff:** When story 39-5's `milestone-grant` loader lands, these YAML files hydrate at chargen with zero additional authoring. ADR-081 lands alongside for the two non-day-1 enum variants in use.
