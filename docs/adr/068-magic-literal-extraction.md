---
id: 68
title: "Magic Literal Extraction — Domain-Scoped Constants"
status: accepted
date: 2026-04-05
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [codebase-decomposition]
implementation-status: live
implementation-pointer: null
---

# ADR-068: Magic Literal Extraction — Domain-Scoped Constants

## Context

The codebase has grown to ~125k LOC across four repos. Magic strings and numbers
have accumulated organically — the same constant defined three times in different
files, game mechanics tuning knobs buried inline with zero documentation, timing
values scattered as naked `setTimeout` arguments, and pipeline parameters
hardcoded in function calls.

### Symptoms

**Duplicated definitions:**
- `const HAIKU_MODEL: &str = "haiku"` defined identically in `inventory_extractor.rs`,
  `continuity_validator.rs`, and `preprocessor.rs`
- `"opus"` hardcoded inline in `orchestrator.rs`
- `DEFAULT_FADE_MS = 3000` defined separately in both `Crossfader.ts` and `useAudioCue.ts`
- `Duration::from_secs(300)` used for both render timeout and cache TTL — same number,
  different semantic meaning, no way to tell if they should change together

**Undocumented game mechanics:**
- `encountergen` uses `0..10 < 6` for 60% probability, `0..10 < 7` for 70%,
  `-20` for hostile disposition, `8..=14` for level ranges — all inline with no
  explanation of why those values were chosen
- `tension_tracker.rs` has good naming (`BORING_BASE`, `ACTION_DECAY`) but
  `subject.rs` has bare `50.0`, `0.3`, `0.05`, `0.15`, `120`, `100` for scoring weights

**Hardcoded infrastructure:**
- `/tmp/sidequest-renderer.sock`, `/tmp/sidequest-tools`
- `http://localhost:5173` CORS origin
- `stun:stun.l.google.com:19302` ICE server
- `24000` sample rate in both API and UI with no shared definition

**Naked timing values (UI):**
- `App.tsx` has `setTimeout(fn, 100)`, `setTimeout(fn, 500)`, `setTimeout(fn, 1000)`,
  `setTimeout(fn, 2000)` with no indication of what each delay accomplishes

**Half-migrated pipeline config (daemon):**
- `flux_config.py` exists with dimension presets, but `acestep_worker.py` still has
  `infer_step=60`, `guidance_scale=15`, `omega_scale=10` etc. inline

### Why This Matters

1. **Change amplification** — adjusting a timeout means grep-and-pray across repos
2. **Semantic opacity** — `0.15` means nothing; `COMBAT_BONUS_WEIGHT` tells you the design intent
3. **Drift risk** — two copies of the same value will eventually diverge
4. **Onboarding tax** — new contributors (including future Claude sessions) can't distinguish
   tuning knobs from arbitrary choices

## Decision

Extract magic literals into **domain-scoped constant definitions** — grouped by the
subsystem they serve, located near the code that uses them. No global constants file.

### Principles

1. **Domain proximity** — constants live in the module (or a sibling `defaults.rs` / `constants.ts`)
   that gives them meaning. Tension constants stay near the tension tracker.
2. **Semantic naming** — the name explains the *role*, not the *value*:
   `HOSTILE_DISPOSITION_DEFAULT` not `NEGATIVE_TWENTY`.
3. **Single definition** — if two modules need the same constant, it lives in the
   lowest common ancestor crate/package. If they need the same *number* for different
   *reasons*, they get separate named constants.
4. **Cross-boundary contracts stay in protocol** — sample rates, message types, and
   format identifiers that cross the API/UI/daemon boundary are documented in the
   protocol spec. Each side defines its own constant matching the contract — they're
   not shared code, they're shared agreements.
5. **No config promotion without need** — these are engine tuning knobs, not user
   configuration. If runtime tweaking becomes necessary, promote individual constants
   to config values. Until then, code constants are simpler and safer.

### Scope

Constants worth extracting are those that are:
- **Duplicated** across files (any count > 1)
- **Tuning knobs** whose optimal value was determined empirically
- **Infrastructure paths/addresses** that change per environment
- **Timing values** that affect UX behavior

Constants NOT in scope:
- Tailwind CSS design tokens (opacity, spacing) — these are the design language
- Standard algorithm constants (WCAG luminance weights, hex parsing bases)
- Test-only concrete values
- Enum variant `as_str()` canonical strings — these ARE the definition

### Implementation Plan

#### Rust — sidequest-api

| Location | Constants |
|----------|-----------|
| `sidequest-agents/src/models.rs` (new) | `HAIKU_MODEL`, `OPUS_MODEL`, `DEFAULT_CLAUDE_COMMAND`, `DEFAULT_CLAUDE_TIMEOUT`, `EXTRACT_TIMEOUT`, `VALIDATE_TIMEOUT`, `PREPROCESS_TIMEOUT` |
| `sidequest-daemon-client/src/defaults.rs` (new) | `RENDER_TIMEOUT`, `DEFAULT_DAEMON_TIMEOUT`, `DEFAULT_SOCKET_PATH`, `VOICE_SAMPLE_RATE` |
| `sidequest-encountergen/src/main.rs` (top of file) | `ABILITY_INCLUDE_CHANCE`, `HOSTILE_DISPOSITION_DEFAULT`, `ENEMY_DISPOSITION_FLOOR`, `SECOND_WEAKNESS_CHANCE`, `DEFAULT_AC`, ability/weakness probability thresholds, tier-to-level mappings |
| `sidequest-game/src/subject.rs` (top of file) | `EXCERPT_CHAR_LIMIT`, `MIN_SUBJECT_LENGTH`, `LENGTH_SCORE_DIVISOR`, `LENGTH_SCORE_CAP`, `ACTION_SCORE_WEIGHT`, `ACTION_SCORE_CAP`, `COMBAT_BONUS_WEIGHT` |
| `sidequest-server/src/config.rs` or top of `lib.rs` | `CORS_DEV_ORIGINS`, `SIDECAR_DIR` (relocated from `tool_call_parser.rs`) |
| `sidequest-game/src/voice_router.rs` (existing, already partially done) | `DEFAULT_DUCK_AMOUNT_DB`, `DEFAULT_CROSSFADE_MS` |

#### TypeScript — sidequest-ui

| Location | Constants |
|----------|-----------|
| `src/constants/timing.ts` (new) | `NARRATION_FLUSH_DELAY_MS`, `NARRATION_WATCHDOG_MS`, `CHUNK_REVEAL_DELAY_MS`, `WS_READY_CHECK_TIMEOUT_MS`, `WS_READY_CHECK_INTERVAL_MS` |
| `src/constants/audio.ts` (new) | `DEFAULT_FADE_MS` (single definition), `VOICE_SAMPLE_RATE`, `VOICE_PCM_FORMAT` |
| `src/constants/network.ts` (new) | `INITIAL_BACKOFF_MS`, `ICE_STUN_SERVER`, `WS_CLOSE_NORMAL` |

#### Python — sidequest-daemon

| Location | Constants |
|----------|-----------|
| `sidequest_daemon/media/defaults.py` (new) | ACE-Step pipeline defaults (`ACESTEP_INFER_STEPS`, `ACESTEP_GUIDANCE_SCALE`, `ACESTEP_OMEGA_SCALE`, `ACESTEP_DEFAULT_DURATION_S`, `ACESTEP_DEFAULT_SEED`), subject extraction limits (`MAX_SUBJECT_LENGTH`, `SUBJECT_EXTRACT_TIMEOUT_S`), Flux warmup defaults |
| `sidequest_daemon/media/flux_config.py` (existing) | Already has dimension presets — finish the migration so `flux_worker.py` reads from here exclusively |

## Consequences

### Positive
- Grep for a constant name instead of a number — instant discoverability
- Change a tuning knob in one place — no multi-file grep required
- Constants carry design intent in their names — self-documenting game mechanics
- Future Claude sessions can identify tuning surfaces without archaeology

### Negative
- One-time refactoring cost across all four repos (mechanical, low risk)
- Slight indirection — must follow the import to see the value (mitigated by
  domain proximity; the constant is never far from its consumer)
- Risk of over-extraction — not every literal needs a name. `0` and `1` are
  fine inline. A probability threshold that was deliberately chosen is not.

### Neutral
- No runtime behavior change — this is purely a readability/maintainability refactor
- No new dependencies or crate boundaries
- Tests continue to use concrete values inline — test readability trumps DRY

## References

- [tension_tracker.rs](../../sidequest-api/crates/sidequest-game/src/tension_tracker.rs) — good example of the target pattern
- [flux_config.py](../../sidequest-daemon/sidequest_daemon/media/flux_config.py) — partially migrated, finish this
- [encountergen/main.rs](../../sidequest-api/crates/sidequest-encountergen/src/main.rs) — worst offender for inline game mechanics constants
