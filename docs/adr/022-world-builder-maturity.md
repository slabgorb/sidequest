# ADR-022: WorldBuilder Maturity

> Ported from sq-2. Language-agnostic campaign initialization.

## Status
Accepted

## Context
Starting a new campaign "from zero" is slow. Players want to jump into an established world.

## Decision
WorldBuilder applies cumulative `HistoryChapter` snapshots from genre packs to seed GameState at different maturity levels.

### Maturity Levels
| Level | Description |
|-------|-------------|
| FRESH | Blank slate, world just created |
| EARLY | Basic NPCs and quests established |
| MID | Ongoing storylines, known factions |
| VETERAN | Rich history, complex relationships |

### History Chapters (YAML)
```yaml
history:
  - maturity: EARLY
    npcs_added: [...]
    quests_active: [...]
    lore_established: [...]
  - maturity: MID
    npcs_added: [...]
    tropes_active: [...]
```

Chapters are cumulative — MID includes everything from EARLY.

### API
```rust
pub struct WorldBuilder;

impl WorldBuilder {
    pub fn build(pack: &GenrePack, maturity: Maturity) -> GameState {
        let mut state = GameState::default();
        for chapter in pack.history.iter().filter(|c| c.maturity <= maturity) {
            chapter.apply(&mut state);
        }
        state
    }
}
```

## Consequences
- "In medias res" starts are easy — pick MID or VETERAN
- Genre packs define campaign depth without code
- Useful for testing: `WorldBuilder::build(&pack, Maturity::Veteran)` creates rich test state
