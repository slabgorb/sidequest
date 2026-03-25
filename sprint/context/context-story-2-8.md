---
parent: context-epic-2.md
---

# Story 2-8: Trope Engine Runtime — Tick Progression, Escalation Beats, Beat Injection into Narrator Context

## Business Context

Tropes are genre-defined narrative patterns that keep the story moving even when the player
isn't driving the plot. They progress passively each turn, fire escalation beats at
thresholds, and inject story events into the narrator's context. Without tropes, the game
is purely reactive — the narrator only responds to player actions. With tropes, there's
always something brewing.

The trope definitions and data models exist in sidequest-genre (story 1-3/1-5). The
`TropeState` tracking exists in sidequest-game (story 1-7). This story adds the runtime
engine that ticks progression, fires beats, and feeds them to the prompt composer.

**Python source:** `sq-2/sidequest/game/state.py` lines 200-290 (`tick_passive_progression`, `check_escalation_beats`, `activate_trope`, `resolve_trope`)
**Python source:** `sq-2/sidequest/state_processor.py` lines 97-220 (trope tick in `process_turn`)
**ADR:** ADR-018 (trope engine lifecycle)
**Depends on:** Story 2-5 (orchestrator calls trope tick in post-turn update)

## Technical Approach

### What Python Does

```python
def tick_passive_progression(self, trope_defs):
    """Advance each active trope by its rate_per_turn, then check for beats."""
    fired = []
    for ts in self.active_tropes:
        if ts.status in ("resolved", "dormant"):
            continue
        td = self._find_trope_def(ts.trope_definition_id, trope_defs)
        if td and td.passive_progression:
            ts.progression = min(1.0, ts.progression + td.passive_progression.rate_per_turn)
    fired = self.check_escalation_beats(trope_defs)
    return fired

def check_escalation_beats(self, trope_defs):
    fired = []
    for ts in self.active_tropes:
        if ts.status in ("resolved", "dormant"):
            continue
        td = self._find_trope_def(ts.trope_definition_id, trope_defs)
        if td:
            for beat in td.escalation:
                if beat.at <= ts.progression and beat.at not in ts.fired_beats:
                    ts.fired_beats.append(beat.at)
                    fired.append((ts, beat))
    return fired
```

Additionally, in `state_processor.py`:
```python
# Keyword-based acceleration/deceleration
combined_text = (player_input + " " + response).lower()
for ts in state.active_tropes:
    td = find_trope_def(ts.trope_definition_id)
    if td.passive_progression:
        for keyword in td.passive_progression.accelerators:
            if keyword.lower() in combined_text:
                ts.progression = min(1.0, ts.progression + bonus)
                break
        for keyword in td.passive_progression.decelerators:
            if keyword.lower() in combined_text:
                ts.progression = max(0.0, ts.progression - penalty)
                break
```

The problems:
- `fired_beats` is `list[float]` — checking `beat.at not in ts.fired_beats` is O(n) and float comparison is fragile
- Keyword matching is case-insensitive substring search — "accelerator keyword in combined text" can false-match ("war" in "warning")
- Trope definition lookup is linear scan every time
- `_find_trope_def` returns `None` silently if trope ID is wrong — progression just stops with no error

### What Rust Does Differently

**`fired_beats` becomes a `HashSet<OrderedFloat<f64>>`:**

```rust
use ordered_float::OrderedFloat;

pub struct TropeState {
    pub id: Uuid,
    pub trope_definition_id: String,
    pub status: TropeStatus,           // enum, not string
    pub progression: f64,              // 0.0-1.0
    pub activated_at: Option<DateTime<Utc>>,
    pub resolved_at: Option<DateTime<Utc>>,
    pub notes: Vec<String>,
    pub fired_beats: HashSet<OrderedFloat<f64>>,  // O(1) lookup, no float equality issues
    pub role_assignments: HashMap<String, String>,
}
```

**Why `HashSet<OrderedFloat>`:** Python uses `list[float]` and checks membership with `in`,
which is O(n) per check. More importantly, floating point equality is unreliable — `0.33`
might not equal `0.33` after arithmetic. `OrderedFloat` implements `Hash` and `Eq` properly,
and `HashSet` gives O(1) membership checks. For the beat thresholds we're comparing against
(0.25, 0.5, 0.75, 1.0), the values come directly from YAML definitions, so they're exact.

**TropeStatus as enum:**

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TropeStatus {
    Dormant,
    Active,
    Progressing,
    Resolved,
}
```

Python uses `str` enum values — `ts.status in ("resolved", "dormant")` is a runtime string
comparison. Rust uses `matches!(ts.status, TropeStatus::Resolved | TropeStatus::Dormant)` —
exhaustive, typo-proof.

### Trope Engine

```rust
pub struct TropeEngine;

impl TropeEngine {
    /// Advance all active tropes by their passive rate, then check for fired beats.
    pub fn tick(
        state: &mut GameState,
        trope_defs: &[TropeDefinition],
    ) -> Vec<FiredBeat> {
        let def_map: HashMap<&str, &TropeDefinition> = trope_defs.iter()
            .map(|td| (td.id.as_str(), td))
            .collect();

        let mut fired = Vec::new();

        for ts in &mut state.active_tropes {
            if matches!(ts.status, TropeStatus::Resolved | TropeStatus::Dormant) {
                continue;
            }

            let Some(td) = def_map.get(ts.trope_definition_id.as_str()) else {
                tracing::warn!(trope_id = %ts.trope_definition_id, "Trope definition not found");
                continue;
            };

            // Passive progression
            if let Some(pp) = &td.passive_progression {
                ts.progression = (ts.progression + pp.rate_per_turn).min(1.0);
            }

            // Check escalation beats
            for beat in &td.escalation {
                let threshold = OrderedFloat(beat.at);
                if beat.at <= ts.progression && !ts.fired_beats.contains(&threshold) {
                    ts.fired_beats.insert(threshold);
                    fired.push(FiredBeat {
                        trope_id: ts.trope_definition_id.clone(),
                        trope_name: td.name.clone(),
                        beat: beat.clone(),
                    });
                }
            }

            // Update status
            if ts.status == TropeStatus::Active && ts.progression > 0.0 {
                ts.status = TropeStatus::Progressing;
            }
        }

        fired
    }

    /// Apply keyword-based acceleration/deceleration from turn text.
    pub fn apply_keyword_modifiers(
        state: &mut GameState,
        trope_defs: &[TropeDefinition],
        turn_text: &str,  // combined player input + narration
    ) {
        let lower = turn_text.to_lowercase();
        let def_map: HashMap<&str, &TropeDefinition> = trope_defs.iter()
            .map(|td| (td.id.as_str(), td))
            .collect();

        for ts in &mut state.active_tropes {
            if matches!(ts.status, TropeStatus::Resolved | TropeStatus::Dormant) {
                continue;
            }
            let Some(td) = def_map.get(ts.trope_definition_id.as_str()) else { continue };
            let Some(pp) = &td.passive_progression else { continue };

            // Word-boundary matching would be better than substring, but match Python for now
            for keyword in &pp.accelerators {
                if lower.contains(&keyword.to_lowercase()) {
                    ts.progression = (ts.progression + pp.accelerator_bonus).min(1.0);
                    break;  // only one acceleration per trope per turn
                }
            }
            for keyword in &pp.decelerators {
                if lower.contains(&keyword.to_lowercase()) {
                    ts.progression = (ts.progression - pp.decelerator_penalty).max(0.0);
                    break;
                }
            }
        }
    }
}

pub struct FiredBeat {
    pub trope_id: String,
    pub trope_name: String,
    pub beat: EscalationBeat,
}
```

**Trope definition lookup is a HashMap, not linear scan.** Python scans the list of
definitions every time. Rust builds the map once per tick call.

### Beat Injection into Narrator Context

Fired beats are injected into the narrator's prompt context for the next turn:

```rust
impl PromptComposer {
    fn active_tropes_section(&self, state: &GameState, pending_beats: &[FiredBeat]) -> PromptSection {
        let mut content = String::from("Active story threads:\n");

        for ts in &state.active_tropes {
            if matches!(ts.status, TropeStatus::Resolved | TropeStatus::Dormant) {
                continue;
            }
            content.push_str(&format!("- {} (progression: {:.0}%)\n",
                ts.trope_definition_id, ts.progression * 100.0));
        }

        if !pending_beats.is_empty() {
            content.push_str("\nEscalation events to weave into narration:\n");
            for beat in pending_beats {
                content.push_str(&format!("- [{}] {}", beat.trope_name, beat.beat.event));
                if !beat.beat.stakes.is_empty() {
                    content.push_str(&format!(" (stakes: {})", beat.beat.stakes));
                }
                if !beat.beat.npcs_involved.is_empty() {
                    content.push_str(&format!(" (involves: {})", beat.beat.npcs_involved.join(", ")));
                }
                content.push('\n');
            }
        }

        PromptSection {
            name: "active_tropes".into(),
            category: SectionCategory::State,
            zone: AttentionZone::Valley,  // background reference
            content,
            source: Some("trope_engine".into()),
            tokens: estimate_tokens(&content),
        }
    }
}
```

### Trope Lifecycle Methods

```rust
impl GameState {
    pub fn activate_trope(&mut self, trope_def_id: &str) -> &TropeState {
        // Check if already active (idempotent)
        if self.active_tropes.iter().any(|ts| ts.trope_definition_id == trope_def_id) {
            return self.active_tropes.iter()
                .find(|ts| ts.trope_definition_id == trope_def_id).unwrap();
        }
        self.active_tropes.push(TropeState {
            id: Uuid::new_v4(),
            trope_definition_id: trope_def_id.to_string(),
            status: TropeStatus::Active,
            progression: 0.0,
            activated_at: Some(Utc::now()),
            ..Default::default()
        });
        self.active_tropes.last().unwrap()
    }

    pub fn resolve_trope(&mut self, trope_def_id: &str, note: Option<&str>) {
        if let Some(ts) = self.active_tropes.iter_mut()
            .find(|ts| ts.trope_definition_id == trope_def_id) {
            ts.status = TropeStatus::Resolved;
            ts.progression = 1.0;
            ts.resolved_at = Some(Utc::now());
            if let Some(n) = note {
                ts.notes.push(n.to_string());
            }
        }
    }
}
```

### Integration with Orchestrator (story 2-5)

The trope engine runs in the post-turn update:

```rust
// In orchestrator post_turn_update:
let fired_beats = TropeEngine::tick(&mut self.state, &self.genre_pack.tropes);
TropeEngine::apply_keyword_modifiers(
    &mut self.state,
    &self.genre_pack.tropes,
    &format!("{} {}", input, narration),
);
// Store fired_beats for next turn's prompt injection
self.pending_beats = fired_beats;
```

## Scope Boundaries

**In scope:**
- `TropeEngine::tick()` — passive progression + escalation beat firing
- `TropeEngine::apply_keyword_modifiers()` — accelerator/decelerator keywords
- `FiredBeat` struct for beat injection
- Prompt section for active tropes + pending beats
- `activate_trope()` and `resolve_trope()` on GameState
- `TropeStatus` enum (replacing string)
- `HashSet<OrderedFloat<f64>>` for fired_beats

**Out of scope:**
- Trope activation from world state agent (the agent activates them via patch — story 2-7 handles the patch, this story handles the tick)
- Between-session advancement (`rate_per_day`) — nice-to-have, not core loop
- Achievement tracking from trope resolution (future story)
- Scenario-specific pacing (bottle episodes, whodunit acts)
- Role assignments (trope role → character mapping) — defer

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Passive tick | Active trope progression increases by `rate_per_turn` each tick |
| Beat fires | Progression crosses threshold → beat returned in fired list |
| No double fire | Same beat threshold doesn't fire twice (HashSet membership) |
| Resolved skipped | Resolved tropes not ticked or checked for beats |
| Dormant skipped | Dormant tropes not ticked or checked for beats |
| Status update | Active → Progressing when progression moves above 0.0 |
| Keyword acceleration | Accelerator keyword in turn text → bonus applied |
| Keyword deceleration | Decelerator keyword in turn text → penalty applied (floor 0.0) |
| Beat injection | Fired beats appear in narrator prompt context with event + stakes |
| Activate idempotent | Activating already-active trope returns existing, doesn't duplicate |
| Resolve sets 1.0 | Resolving a trope sets progression to 1.0 and status to Resolved |
| Missing def logged | Trope with unknown definition ID → warning logged, skipped |

## Type-System Wins Over Python

1. **`TropeStatus` enum** — `Resolved | Dormant` pattern match vs `in ("resolved", "dormant")` string check.
2. **`HashSet<OrderedFloat>`** — O(1) beat dedup vs O(n) list scan. No float equality issues.
3. **`HashMap` for def lookup** — O(1) vs linear scan per trope per tick.
4. **`FiredBeat` struct** — typed return value vs tuple `(TropeState, EscalationBeat)`.
5. **Missing definition is a logged warning** — not a silent skip. Python returns `None` and the `if td:` check hides the error.
