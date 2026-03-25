# Port Lessons: Python Technical Debt Audit

What to keep, what to fix, and what to drop when porting SideQuest from Python to Rust.

## Critical: Fix in the Port

### 1. Server/Orchestrator Coupling

**Problem:** `app.py` reaches into orchestrator internals 35+ times — private field mutation (`orchestrator._server_submitted_render`), direct `.state` access for characters/location/combat/inventory, and render cue logic split across both files.

**Fix:** Create an `OrchestrationPort` trait (facade) that exposes:
- `handle_player_action() -> ActionResult`
- `get_game_snapshot() -> GameSnapshot`
- `request_greeting() -> String`

Server talks to the port. Never touches game state directly. In Rust this also avoids borrow-checker nightmares from shared mutable state.

### 2. JSON Extraction Duplicated 4+ Times

**Problem:** The same 3-tier JSON extraction logic (direct parse → markdown fence → freeform search) is copy-pasted across `world_state.py`, `freeform_creator.py`, `guided_creator.py`, `music_director.py`, and a simplified version in `combat.py`.

**Fix:** Single `JsonExtractor` in `sidequest-agents`. One implementation, one place to improve LLM response parsing.

### 3. Three Different Claude CLI Subprocess Patterns

**Problem:** `ClaudeAgent` uses 120s timeout with typed errors. `IntentRouter` uses 30s timeout with `RuntimeError`. `PerceptionRewriter` has **no timeout at all** and silently falls back.

**Fix:** Single `ClaudeClient` struct in `sidequest-agents` with configurable timeout, consistent error types, and a standard retry/fallback policy.

### 4. GameState God Object

**Problem:** `GameState` imports from 8+ modules, has ~30 top-level fields, and `apply_patch()` is a 255-line function that manually mutates everything. State mutations also happen in `progression.py` and `world_builder.py` independently.

**Fix:** Decompose into domain-specific state structs (`CombatState`, `ChaseState`, `PartyState`, `WorldState`). Each owns its mutations behind a typed interface. The top-level `GameState` composes them but doesn't reach into their internals.

### 5. Duplicate Attitude Enums with Different Thresholds

**Problem:** `npc.py` defines `Attitude` (friendly/neutral/hostile) with thresholds at ±10. `dialogue.py` defines `DispositionLevel` (same values) with thresholds at ±25. Same concept, different numbers.

**Fix:** One `Disposition` newtype in `sidequest-game` with a single threshold definition. Derive attitude from disposition in one place.

### 6. HP Clamping Bug

**Problem:** `progression.py:59` clamps HP with `min(character.hp + hp_delta, character.max_hp)` but **doesn't clamp to zero** — negative HP is possible. Two other clamping sites in `state.py` do it correctly.

**Fix:** Single `fn clamp_hp(current: i32, delta: i32, max: i32) -> i32` used everywhere.

## High: Improve in the Port

### 7. No Agent Trait

**Problem:** Each agent (narrator, combat, NPC, world_state, chase) has different method signatures, different context-building patterns, and different error handling. No shared interface.

**Fix:** Define an `Agent` trait:
```
trait Agent {
    fn build_context(&self, state: &GameSnapshot) -> Context;
    fn system_prompt(&self) -> &str;
    async fn execute(&self, client: &ClaudeClient, context: Context) -> Result<AgentResponse>;
}
```

### 8. Context Building Scattered

**Problem:** Every agent manually assembles context by calling format helpers in slightly different orders. The "character block" is rebuilt independently in 4+ agents.

**Fix:** `ContextBuilder` with composable sections. Agents declare which sections they need; builder assembles them consistently.

### 9. Inconsistent Validation

**Problem:** `Character` and `NPC` use shared `validate_not_blank()` from `validators.py`. But `Enemy`, `ActiveEffect`, `Relationship`, `ChaseBeat`, `NarrativeEntry` all duplicate the same inline check: `if not v.strip(): raise ValueError(...)`.

**Fix:** In Rust, use a `NonBlankString` newtype that validates at construction. Used in struct definitions — validation happens once, enforced by the type system.

### 10. Repeated Combatant Fields

**Problem:** `Character`, `NPC`, and `Enemy` all independently define `name`, `hp`, `max_hp`, `level`, `ac`. No shared base.

**Fix:** `Combatant` trait with default implementations. Characters, NPCs, and enemies implement it.

### 11. State Delta Incomplete

**Problem:** `state_delta.py:snapshot_state()` only captures characters, location, and quest_log. Ignores NPCs, combat status, chase state, atmosphere, tropes, discovered regions.

**Fix:** Delta computation should cover all state domains. Each domain struct can implement a `Diffable` trait.

### 12. Logging from Day One

**Problem:** Python logging exists but is text-based, inconsistent in detail level, and some broadcast failures are completely silent (`app.py:1049`).

**Fix:** Use `tracing` crate from the start with structured spans. Define a taxonomy: `EVENT`, `GATE`, `DEGRADED`, `AGENT`. Every log includes `component`, `operation`, and `player_id` where applicable.

## Medium: Clean Up in the Port

### 13. Genre/Scenario Loader Asymmetry

**Problem:** Genre packs use a sophisticated `_FILE_MAP` + helper pattern. Scenario packs manually `yaml.safe_load()` × 5 with no reuse.

**Fix:** Shared `DocumentLoader` trait in `sidequest-genre` that both genre and scenario packs use.

### 14. Trope Inheritance Single-Level Only

**Problem:** `resolve.py` only resolves one level of `extends`. If trope A extends B extends C, only A←B is resolved.

**Fix:** Recursive resolution with cycle detection in the Rust implementation.

### 15. Untyped Data in 6 Locations

**Problem:** `HistoryChapter`, `level_bonuses`, `voice_presets`, `mechanical_effects`, and `creature_voice_effects` all use `dict[str, Any]` or `list[dict[str, Any]]`.

**Fix:** Define explicit Rust structs for all of these. No `serde_json::Value` catchalls.

### 16. `extra="allow"` on All 52 Models

**Problem:** Every Pydantic model silently accepts unknown YAML fields. Typos like `triggres` instead of `triggers` go unnoticed.

**Fix:** Use `#[serde(deny_unknown_fields)]` in Rust. Catch YAML typos at load time.

### 17. Post-Load Cross-Validation

**Problem:** Critical validation (inventory references, corpus file existence, cartography) happens in separate post-load calls that are easy to forget.

**Fix:** Two-phase loading: (1) YAML → typed structs, (2) explicit `validate()` call that checks cross-references. Make the loader return a validated `GenrePack` — can't get an unvalidated one.

## Keep As-Is

These patterns are solid — port them faithfully:

- **format_helpers.py** — Well-factored context formatting functions
- **DEGRADED pattern** — Non-critical subsystems (render, audio, TTS) catch errors and continue with warnings. Good resilience design.
- **Coal-to-diamond inventory** — Unstructured strings promoted to full Items when narratively significant. Elegant pattern, just needs a formal state machine in Rust.
- **Genre pack model hierarchy** — Flat, well-structured, only 6% Optional fields. Maps cleanly to Rust structs.
- **Agency rules** — Consistently documented across agents. Good blueprint for Rust agent prompts.
- **Processing gate** — Player action deduplication via `_processing` set. Clean pattern, use a scoped guard in Rust.
- **Session handler separation** — `session_handler.py` doesn't mutate state, only returns messages. Clean boundary.
