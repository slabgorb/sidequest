# Story 47-10 Context — C&C Memorization Wiring

**Story ID:** 47-10  
**Points:** 8  
**Priority:** p1  
**Workflow:** tdd  
**Repos:** sidequest-server, sidequest-content, sidequest-ui

---

## Story Summary

Final wiring pass for C&C memorized-spell casting. Converts the shipped `learned_v1` infrastructure into a playable Mage/Cleric surface via a prepared-list gate in `beats_available_for`, null-stat auto-apply in spell resolution, OTEL observability, and UI panel rendering.

## Design Pattern: Dual-Plugin Architecture

**Amended 2026-05-09** — This design uses a two-plugin model:

1. **`learned_v1` — Data layer** (already shipped)
   - Spell catalogs (arcane_l1.yaml, divine_l1.yaml)
   - Pydantic models: `Spell`, `SpellCatalog`, `SpellSave`, `SpellComponents`
   - MagicState collections: `known_spells[actor]`, `prepared_spells[actor]`
   - Plugin operations: `prepare`, `cast`, `rest`, `turn_undead`
   - `magic_init.seed_learned_v1_state` helper for session init

2. **`innate_v1` — Player-facing surface** (existing, retains C&C magic_access)
   - `cast_spell` beat with class_filter and resource_deltas
   - Consumes prepared_spells data via beats_available_for gate
   - Drains spell_slots_<actor> ledger bars via beat.resource_deltas

**Why two plugins:**
- `innate_v1` is the primary C&C magic surface (familiar to the engine)
- `learned_v1` is infrastructure that can be used by any plugin
- The bridge is a **prepared-list gate** in `beats_available_for` — a single-line addition to existing beat filtering

## Key Implementation Details

### 1. Init Wiring (AC1)

**File:** `sidequest-server/sidequest/magic/magic_init.py` — `init_magic_state_for_session()`

**Change:** Call `seed_learned_v1_state()` for every actor whose `ClassDef.magic_config` is non-null.

```python
# Pseudocode
for actor in scenario_state.actors:
    class_def = get_class_def(actor.class_id)
    if class_def.magic_config:
        magic_init.seed_learned_v1_state(
            actor_id=actor.id,
            magic_state=scenario_state.magic_state,
            class_config=class_def.magic_config
        )
```

**Expected state after seed:**
- `magic_state.known_spells[actor_id]` = list of all spells from actor's tradition (12 arcane, 8 divine L1)
- `magic_state.prepared_spells[actor_id]` = empty dict (no spells prepared yet)
- `magic_state.ledger` bars created: `spell_slots_l1_<actor_id>` initialized to actor's B/X L1 slot count

### 2. classes.yaml magic_config (AC2)

**File:** `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`

**Mage block (existing class, adding magic_config):**

```yaml
- id: mage
  # ...existing fields...
  magic_access: innate_v1
  magic_config:
    magic_tradition: arcane
    starting_known_spells: 2
    save_dc_stat: INT
    turn_undead: false
```

**Cleric block (existing class, adding magic_config):**

```yaml
- id: cleric
  # ...existing fields...
  magic_access: innate_v1
  magic_config:
    magic_tradition: divine
    starting_known_spells: 2
    save_dc_stat: WIS
    turn_undead: true
```

**Slot progression table** (per B/X canon, included in magic_config or class definition):
- Mage: L1=2 slots (standard)
- Cleric: L1=2 slots (standard)

### 3. World magic.yaml (AC3)

**File:** `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/magic.yaml`

**Create with:**

```yaml
world_magic:
  active_plugins: [item_legacy_v1, innate_v1, learned_v1]
  
  ledger_bars:
    - id: divine_favor
      display_name: "Divine Favor"
      direction: bidirectional
      range: [-1.0, 1.0]
      initial_value: 0.0
      thresholds:
        - value: 0.7
          label: "blessed"
          flavor: "The Three Rites favor you"
        - value: -0.7
          label: "forsaken"
          flavor: "You have strayed from the Three Rites"
      applies_to_classes: [cleric]
  
  narrator_register: |
    [Sünden magic context block — from spec section 4]
    The Wall stands. Magic flows through Caverns & Claudes like blood through stone,
    but with caution. Fire and Light call to the Divine through their priests.
    Secrets whisper to the Learned through spellbooks and scrolls.
    The Wall records what is cast — and the Wallwrights remember.
```

### 4. Prepared-List Gate (AC4)

**File:** `sidequest-server/sidequest/game/beat_filter.py` — `beats_available_for()`

**Add logic:**

```python
def beats_available_for(
    actor: Character,
    scenario_state: GameSnapshot,
    available_beats: List[Beat],
    magic_state: MagicState
) -> Tuple[List[Beat], Dict[str, str]]:
    """
    Filter beats available for actor.
    Returns (filtered_beats, otel_decisions).
    """
    filtered = []
    decisions = {}
    
    for beat in available_beats:
        # ...existing filters...
        
        # NEW: Prepared-spells gate for cast_spell beats
        if beat.id == "cast_spell" and beat.spell_selection:
            spell_level = beat.spell_level  # e.g., 1 for L1 spells
            if (magic_state.prepared_spells.get(actor.id, {})
                    .get(spell_level, [])):
                # Spell is prepared at this level
                filtered.append(beat)
            else:
                # No spells prepared at this level
                decisions[beat.id] = "rejected_unprepared"
        else:
            filtered.append(beat)
    
    return filtered, decisions
```

**OTEL decision value:** Emit `rejected_unprepared` in beat-filter decision span when spell_selection is not prepared.

### 5. Null-Stat Auto-Apply (AC5)

**File:** `sidequest-server/sidequest/game/narration_apply.py` — spell resolution

**Branch in spell cast resolution:**

```python
def resolve_spell_cast(spell: Spell, actor: Character, target: Character) -> CastResult:
    """
    Resolve spell cast against target.
    """
    result = CastResult(spell_id=spell.id, actor_id=actor.id)
    
    if spell.save.stat is None:
        # Auto-apply path (Magic Missile, Light, etc.)
        result.save_skipped = True
        result.effect_applied = apply_effect_template(spell.effect_template, actor, target)
    else:
        # Opposed-check path (existing)
        save_dc = derive_dc_from_stat(spell.save.stat, actor)
        opposed_result = run_opposed_check(target, stat=spell.save.stat, dc=save_dc)
        result.save_skipped = False
        result.save_stat = spell.save.stat
        result.save_result = opposed_result
        
        if opposed_result == "success":
            result.effect_applied = apply_save_effect(spell.save.effect, spell.effect_template, actor, target)
        else:
            result.effect_applied = apply_effect_template(spell.effect_template, actor, target)
    
    return result
```

**Spell catalog validator:** Reject spells with `save.stat: null` AND `save.effect != none` (inconsistent).

### 6. innate_v1.cast OTEL Span (AC6)

**File:** `sidequest-server/sidequest/magic/otel_spans.py` (or inline in narration_apply)

**Emit on every successful cast:**

```python
# In narration_apply.py or cast_spell handler
with tracer.start_as_current_span("innate_v1.cast") as span:
    span.set_attribute("actor_id", actor.id)
    span.set_attribute("spell_id", spell.id)
    span.set_attribute("validator_outcome", result.validator_outcome)  # ok | rejected_<reason>
    span.set_attribute("slot_consumed", result.slot_consumed)  # boolean
    span.set_attribute("save_skipped", result.save_skipped)  # boolean
    
    if not result.save_skipped:
        span.set_attribute("save_stat", result.save_stat)
        span.set_attribute("save_result", result.save_result)  # success | fail
        if result.damage_applied:
            span.set_attribute("damage_applied", result.damage_applied)
```

### 7. Context Block (AC7)

**File:** `sidequest-server/sidequest/magic/context_builder.py` — magic context zone

**Inject into prompt when MagicState.prepared_spells[actor] is non-empty:**

```markdown
## Learned Magic

**Known Spells (Arcane, L1):** 12 available
**Prepared Spells (L1):** Sleep, Magic Missile
**Slots Remaining (L1):** 0/2 (both cast)

The Mage recalls the weight of the spells she has bound to memory —
the drowsy hum of Sleep, the sharp snap of Force darts. The words are
ready; only the second casting will require a return to rest and study.
```

**Narrator invariant test (ADR-009):** Assert narrator does not name an unprepared spell in narration output.

### 8. UI LedgerPanel (AC8)

**File:** `sidequest-ui/src/components/CharacterPanel/LedgerPanel.tsx`

**Add magic block for actors with prepared_spells:**

```typescript
interface MagicBlockProps {
  actor: Character;
  knownSpells: Spell[];
  preparedSpells: Record<number, Spell[]>;  // level -> [spells]
  spellSlotsRemaining: Record<number, number>;  // level -> count
  divineFavor?: number;
}

export function MagicBlock({ actor, knownSpells, preparedSpells, spellSlotsRemaining, divineFavor }: MagicBlockProps) {
  return (
    <div className="magic-block">
      <div className="known-spells">
        <Collapsible title="Known Spells" count={knownSpells.length}>
          {knownSpells.map(spell => <SpellItem key={spell.id} spell={spell} />)}
        </Collapsible>
      </div>
      
      <div className="prepared-spells">
        {Object.entries(preparedSpells).map(([level, spells]) => (
          <div key={`l${level}`} className="spell-level">
            <span className="level-label">L{level}</span>
            <span className="slot-indicator">{spells.length}/{spellSlotsRemaining[level]} slots</span>
            {spells.map(spell => <SpellItem key={spell.id} spell={spell} />)}
          </div>
        ))}
      </div>
      
      {actor.class === "cleric" && divineFavor !== undefined && (
        <DivineFlavorBar value={divineFavor} thresholds={[0.7, -0.7]} />
      )}
      
      {actor.class === "cleric" && (
        <TurnUndeadButton enabled={hasUndeadInScene} />
      )}
    </div>
  );
}
```

### 9. Pulse-Not-Popup UX (AC9)

**File:** `sidequest-ui/src/styles/magic.css` and beat selection component

**CSS animation:**

```css
.prepared-spells-list.pulse {
  animation: pulse-highlight 0.6s ease-in-out;
}

@keyframes pulse-highlight {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; background-color: rgba(255, 200, 0, 0.2); }
}
```

**Behavior on unprepared cast:**
1. Trigger pulse on `.prepared-spells-list`
2. Add struck-through class to the attempted spell name in log
3. Replace input with narrator nudge (e.g., "The spell isn't ready")
4. No modal, no state rollback

### 10. Integration Test (AC10)

**File:** `sidequest-server/tests/magic/test_c_and_c_casting.py`

**Test sequence:**
1. Init Sünden session with Mage
2. Verify known_spells populated (12 spells)
3. Verify spell_slots_l1_<mage> bar created at 2/2
4. At safe site: prepare Sleep + Magic Missile
5. Cast Magic Missile (auto-apply)
   - Assert innate_v1.cast span fires
   - Assert save_skipped=true
   - Assert spell_slots bar decrements to 1/2
6. Cast Sleep (WIS save)
   - Assert innate_v1.cast span fires
   - Assert save_skipped=false, save_stat=WIS
7. Attempt cast Sleep again (no slots)
   - Assert beat_filter rejects
8. Return to safe site, rest
9. Re-prepare Light instead of Sleep
10. Save and reload session
    - Assert prepared_spells preserved
    - Assert slot bars preserved

### 11. Smoke Playtest (AC11)

**Environment:** Full Sünden delve, full playgroup (Keith + James + Alex + Sebastien)

**Verification:**
- Mage and Cleric both playable end-to-end
- OTEL dashboard displays magic.* spans correctly
- Slot economy (drain, rest reset, prepared list gating) works without friction
- Narrator prose remains engaging and surprising despite mechanical gating

---

## Touch Points (Code Locations)

### sidequest-server

| File | Change | AC |
|------|--------|----| 
| `sidequest/magic/magic_init.py` | Call `seed_learned_v1_state` for actors with magic_config | 1 |
| `sidequest/game/beat_filter.py` | Add prepared-spells gate for cast_spell beat | 4 |
| `sidequest/game/narration_apply.py` | Branch on `save.stat is None` for auto-apply | 5 |
| `sidequest/magic/otel_spans.py` or inline | Emit innate_v1.cast OTEL span | 6 |
| `sidequest/magic/context_builder.py` | Render learned-magic block when prepared_spells non-empty | 7 |
| `tests/magic/test_c_and_c_casting.py` | Integration test for full casting sequence | 10 |

### sidequest-content

| File | Change | AC |
|------|--------|----| 
| `genre_packs/caverns_and_claudes/classes.yaml` | Add magic_config blocks to Mage, Cleric | 2 |
| `genre_packs/caverns_and_claudes/worlds/caverns_sunden/magic.yaml` | Create with active_plugins, divine_favor bar, narrator_register | 3 |

### sidequest-ui

| File | Change | AC |
|------|--------|----| 
| `src/components/CharacterPanel/LedgerPanel.tsx` | Add MagicBlock component | 8 |
| `src/styles/magic.css` | Add pulse animation for prepared-spells list | 9 |
| `tests/magic/test_ledger_panel.test.tsx` | Render test for MagicBlock | 8 |

---

## Testing Strategy

### Unit tests (RED phase)
- Spell catalog validation (save.stat null rules)
- beat_filter prepared-spells gate logic
- null-stat auto-apply branch
- LedgerPanel rendering

### Integration tests (GREEN phase)
- Full Mage casting sequence (AC10)
- Session init with magic_config
- OTEL span emission

### Smoke playtest (AC11)
- Live table with full playgroup
- Keith observes OTEL dashboard
- Cast economics verified

---

## Constraints & Assumptions

### Constraints
- Must not break existing item_legacy_v1 or innate_v1 wiring
- Spell slot bars auto-instantiated at session init (not manual)
- divine_favor bar only applies to Cleric class
- No cantrips in v1 (open question 2 — deferred)

### Assumptions
- Infrastructure from PRs #220/#193/#221/#194 is stable and tested
- B/X slot progression tables are immutable (2 L1 slots for both Mage and Cleric)
- Narrator's unprepared-spell guard is already in place (ADR-009 invariant)

---

## Narrative Anchor

Per CLAUDE.md, this story serves:

- **Keith (forever-GM-now-player):** Mechanical enforcement of prepared-list gating and slot economics gives him genuine surprise — the narrator can't hand-wave past his spell prep choices.
- **James (narrative-first):** Spell prep is a single declared verb at a safe site, not a minigame. Narration remains surprised and engaging.
- **Alex (slow typist, freeze-prone):** No spellbook-transcription UI. Unprepared attempts pulse, not popup. No time pressure.
- **Sebastien (mechanics-first):** GM panel shows the full slot economy live — known list, prepared list, slots remaining, prepared-list gate decisions as OTEL spans.

---

## Related Documents

- **Spec:** `docs/superpowers/specs/2026-05-06-magic-system-caverns-and-claudes-implementation-design.md` (amended 2026-05-09)
- **Architecture:** `docs/superpowers/specs/2026-04-29-magic-system-coyote-reach-architect-addendum.md`
- **Plans:** `docs/superpowers/plans/2026-04-28-magic-system-coyote-reach-v1.md`
- **Class design:** `docs/superpowers/specs/2026-05-08-cnc-bx-class-beats-morale-design.md`
- **ADRs:** ADR-014 (Diamonds and Coal — HP removal), ADR-067 (Narrator architecture)
