---
parent: context-epic-2.md
---

# Story 2-7: State Patch Pipeline — Combat/Chase/World JSON Patches Applied, State Delta Computation, Client Broadcast

## Business Context

After each agent responds, the orchestrator extracts JSON patches from the response and
applies them to game state. The Python `apply_patch()` method is 350 lines of `if "key" in patch:`
checks with coercion, fallbacks, and implicit merge logic. This story replaces that with
typed patch structs that the compiler validates, and a clean delta computation that tells
the client exactly what changed.

This is where the type system pays off most dramatically. Python's patch application is the
single most error-prone part of the codebase — every field is optional, every value might
be the wrong type, and the merge logic has accumulated special cases over months.

**Python source:** `sq-2/sidequest/game/state.py` lines 545-899 (`apply_patch`, 350 lines)
**Python source:** `sq-2/sidequest/game/state_delta.py` (StateDelta computation)
**Python source:** `sq-2/sidequest/orchestrator.py` lines 2071-2180 (`_extract_and_apply_combat_patch`, `_extract_and_apply_chase_patch`)
**ADRs:** ADR-011 (world state JSON patches), ADR-026 (client state mirror), ADR-027 (reactive state messaging)
**Depends on:** Story 2-5 (orchestrator produces patches), Story 1-8 (GameSnapshot, typed patches)

## Technical Approach

### What Python Does

```python
def apply_patch(self, patch: dict, genre_pack=None):
    if "location" in patch:
        self.location = str(patch["location"])
    if "time_of_day" in patch:
        self.time_of_day = str(patch["time_of_day"])
    if "hp_changes" in patch:
        for name, delta in patch["hp_changes"].items():
            char = self._find_character(name)
            if char:
                char.hp = max(0, min(char.max_hp, char.hp + int(delta)))
    if "npc_attitudes" in patch:
        for name, attitude in patch["npc_attitudes"].items():
            disp = self._coerce_attitude(attitude)  # string → int, with frozenset lookup
            if disp is not None:
                npc = self.npc_registry.find_by_name(name)
                if npc:
                    npc.disposition = disp
    if "npcs_present" in patch:
        for npc_data in patch["npcs_present"]:
            # upsert: find by id or name, merge mutable fields, lock identity fields
            existing = self.npc_registry.find_by_name(npc_data.get("name", ""))
            if existing:
                # update mutable: description, location, personality, backstory, role
                # skip locked: pronouns, appearance (set once, never overwrite)
                ...
            else:
                self.npc_registry.add(NPC(**npc_data))
    # ... 30+ more if-blocks for quest_updates, notes, combat, atmosphere, etc.
```

The problems:
- `patch: dict` — anything can be in there, nothing is type-checked
- `_coerce_attitude(attitude)` converts strings like "friendly" → 15, "hostile" → -15 via frozenset lookup with "deceased" → None as a special case. This is a stringly-typed dispatch table.
- NPC upsert has implicit field locking (pronouns/appearance set once) — no type enforcement
- HP changes use `int(delta)` which can raise ValueError on bad data from the agent
- 350 lines of this pattern, each `if` block potentially silently doing nothing on bad data

### What Rust Does Differently

**Typed patch structs (already defined in story 1-11 patches.rs):**

```rust
#[derive(Deserialize, Default)]
#[serde(deny_unknown_fields)]
pub struct WorldStatePatch {
    pub location: Option<String>,
    pub time_of_day: Option<String>,
    pub atmosphere: Option<String>,
    pub hp_changes: Option<HashMap<String, i32>>,
    pub npc_attitudes: Option<HashMap<String, String>>,
    pub quest_updates: Option<HashMap<String, String>>,
    pub notes: Option<String>,
    pub active_stakes: Option<String>,
    pub current_region: Option<String>,
    pub discover_regions: Option<Vec<String>>,
    pub discover_routes: Option<Vec<String>>,
    pub lore_established: Option<Vec<String>>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CombatPatch {
    pub in_combat: Option<bool>,
    pub round_number: Option<u32>,
    pub hp_changes: Option<HashMap<String, i32>>,
    pub turn_order: Option<Vec<String>>,
    pub current_turn: Option<String>,
    pub available_actions: Option<Vec<String>>,
    pub drama_weight: Option<f64>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChasePatch {
    pub separation: Option<i32>,
    pub phase: Option<String>,
    pub event: Option<String>,
}
```

**Why this is better:**
- `deny_unknown_fields` — if the agent sends a field that doesn't exist, deserialization fails immediately instead of being silently ignored
- `Option<i32>` for `hp_changes` values — no `int(delta)` that might throw. If the agent sends `"five"` instead of `5`, serde rejects it at parse time
- Each field's type is explicit — no runtime type coercion

### Patch Application (Typed)

```rust
impl GameState {
    pub fn apply_world_patch(&mut self, patch: &WorldStatePatch) {
        if let Some(loc) = &patch.location {
            self.location = loc.clone();
        }
        if let Some(tod) = &patch.time_of_day {
            self.time_of_day = tod.clone();
        }
        if let Some(hp_changes) = &patch.hp_changes {
            for (name, delta) in hp_changes {
                if let Some(char) = self.find_character_mut(name) {
                    char.apply_hp_delta(*delta);  // clamp_hp already built in story 1-6
                }
            }
        }
        if let Some(attitudes) = &patch.npc_attitudes {
            for (name, attitude_str) in attitudes {
                if let Some(disposition) = Disposition::from_attitude_str(attitude_str) {
                    if let Some(npc) = self.npc_registry.find_by_name_mut(name) {
                        npc.disposition = disposition;
                    }
                }
            }
        }
        // ... remaining fields
    }
}
```

**Attitude coercion becomes a method on Disposition (already a newtype from story 1-6):**

```rust
impl Disposition {
    /// Convert attitude string to numeric disposition.
    /// Python had a 3-way frozenset lookup. Rust uses an enum.
    pub fn from_attitude_str(s: &str) -> Option<Self> {
        let lower = s.to_lowercase();
        // "deceased"/"dead" → None (don't update)
        if lower.contains("deceased") || lower.contains("dead") {
            return None;
        }
        // Check tokens against known attitudes
        let attitude = Attitude::from_str(&lower);
        Some(Self::from_attitude(attitude))
    }
}
```

**NPC upsert with identity locking:**

Python's NPC upsert silently skips locked fields. Rust makes the locking explicit:

```rust
impl NPC {
    /// Merge mutable fields from a patch. Identity fields (pronouns, appearance)
    /// are locked after first set — subsequent patches cannot overwrite them.
    pub fn merge_patch(&mut self, patch: &NpcPatch) {
        // Always updatable
        if let Some(desc) = &patch.description { self.description = desc.clone(); }
        if let Some(loc) = &patch.location { self.location = loc.clone(); }
        if let Some(role) = &patch.role { self.role = role.clone(); }

        // Locked on first set — only write if currently empty
        if self.pronouns.is_empty() {
            if let Some(p) = &patch.pronouns { self.pronouns = p.clone(); }
        }
        if self.appearance.is_empty() {
            if let Some(a) = &patch.appearance { self.appearance = a.clone(); }
        }
    }
}
```

### State Delta Computation (ADR-026)

The client needs to know what changed. Python computes deltas by comparing before/after snapshots:

```rust
pub struct StateDelta {
    pub location: Option<String>,
    pub characters: Vec<CharacterDelta>,
    pub quests: HashMap<String, String>,  // only changed entries
    pub inventory_changes: Vec<InventoryChange>,
}

pub struct CharacterDelta {
    pub name: String,
    pub hp: Option<i32>,
    pub max_hp: Option<i32>,
    pub statuses: Option<Vec<String>>,
}

pub struct InventoryChange {
    pub item: String,
    pub action: InventoryAction,  // Added | Removed
    pub character: String,
}
```

Computation:

```rust
impl GameState {
    pub fn compute_delta(&self, before: &StateSnapshot) -> Option<StateDelta> {
        let mut delta = StateDelta::default();
        let mut has_changes = false;

        if self.location != before.location {
            delta.location = Some(self.location.clone());
            has_changes = true;
        }

        for char in &self.characters {
            if let Some(prev) = before.find_character(&char.name) {
                let mut char_delta = CharacterDelta { name: char.name.clone(), ..Default::default() };
                let mut char_changed = false;
                if char.hp != prev.hp {
                    char_delta.hp = Some(char.hp);
                    char_changed = true;
                }
                // ... max_hp, statuses, inventory
                if char_changed {
                    delta.characters.push(char_delta);
                    has_changes = true;
                }
            }
        }

        if has_changes { Some(delta) } else { None }
    }
}
```

**Type-system win:** `Option<StateDelta>` — None means nothing changed. Python returns
an empty dict `{}` which the client has to check for emptiness.

### Reactive State Messaging (ADR-027)

After patches are applied, the server broadcasts typed messages based on what changed:

```rust
fn broadcast_state_changes(delta: &StateDelta, state: &GameState) -> Vec<GameMessage> {
    let mut messages = Vec::new();

    // Always send PARTY_STATUS after a turn
    messages.push(GameMessage::PartyStatus(build_party_payload(state)));

    // COMBAT_EVENT if combat state changed
    if state.combat.in_combat != pre_combat_state {
        messages.push(GameMessage::CombatEvent(build_combat_payload(state)));
    }

    // CHAPTER_MARKER if location changed
    if delta.location.is_some() {
        messages.push(GameMessage::ChapterMarker(ChapterMarkerPayload {
            location: state.location.clone(),
        }));
    }

    // MAP_UPDATE if regions discovered
    if !state.newly_discovered_regions.is_empty() {
        messages.push(GameMessage::MapUpdate(build_map_payload(state)));
    }

    messages
}
```

Python does this with separate `broadcast_party_status()`, `broadcast_combat_event()`, etc.
methods scattered through `_handle_action()`. Rust collects all messages in one pass
from the delta — deterministic, testable, no missed broadcasts.

## Scope Boundaries

**In scope:**
- `apply_world_patch()`, `apply_combat_patch()`, `apply_chase_patch()` methods on GameState
- `Disposition::from_attitude_str()` — typed attitude coercion replacing frozenset lookup
- NPC upsert with identity field locking
- HP delta application via `clamp_hp` (from story 1-6)
- `StateSnapshot` capture before turn
- `StateDelta` computation (compare before/after)
- Reactive message list generation from delta
- Quest log merge (additive, keyed by quest name)
- Lore/region/route discovery (append, deduplicated)

**Out of scope:**
- Inventory promotion (diamonds-and-coal narrative_weight evolution — defer)
- Character progression patches (affinity/milestone — story 2-8 territory)
- Genie wish system (scenario-specific, defer)
- Axis value updates (tone/theme dimensions — nice-to-have)
- Scenario belief state patches (defer)
- Character knowledge patches (defer)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| World patch applies | Location, time_of_day, atmosphere updated from WorldStatePatch |
| HP changes | `hp_changes: {"Hero": -5}` → character HP reduced by 5, clamped to [0, max_hp] |
| NPC attitude | `npc_attitudes: {"Merchant": "friendly"}` → disposition set to Friendly threshold |
| NPC upsert | New NPC in patch → added to registry. Existing → mutable fields merged |
| Identity locking | NPC pronouns/appearance set once — subsequent patches don't overwrite |
| Combat patch | `CombatPatch` fields applied to CombatState |
| Chase patch | `ChasePatch` fields applied to ChaseState |
| Quest merge | New quests added, existing quests updated by key |
| Region discovery | `discover_regions` appended, deduplicated |
| State delta | `compute_delta()` returns only changed fields |
| No-change delta | Nothing changed → `compute_delta()` returns None |
| Reactive messages | Delta produces correct GameMessage list (PARTY_STATUS, COMBAT_EVENT, etc.) |
| Invalid patch rejected | `deny_unknown_fields` rejects patches with unexpected keys at parse time |

## Type-System Wins Over Python

1. **`deny_unknown_fields`** — unknown patch keys fail at deserialization. Python silently ignores them.
2. **`Option<i32>` for HP** — no `int(delta)` that might throw on bad agent output.
3. **`Disposition` newtype** — attitude coercion is a method, not a frozenset string lookup.
4. **`StateDelta` struct** — typed changes, not a dict that might have any shape.
5. **`Option<StateDelta>`** — None means no changes. No empty-dict ambiguity.
6. **NPC identity locking is explicit** — `merge_patch()` documents which fields lock.
7. **Reactive messages generated from delta** — deterministic, testable, no scattered broadcast calls.
