---
parent: context-epic-50.md
---

# Story 50-9: Mood aliases alias-chain fallback in music director track selection

## Business Context

Genre packs declare custom moods (standoff, ritual, pact, working, etc.) with dedicated music tracks. The narrator emits mood strings that don't map to the hardcoded 7-variant Mood enum. When a narrator outputs a novel mood key (e.g., "ritual" in heavy_metal) that has no track in `mood_tracks`, the system silently falls back to a generic mood and loses the genre-specific audio cue.

**ADR-033 Pillar 3** (Music Extension) specified a solution: `mood_aliases` — a declarative chain that maps custom moods to existing mood_tracks keys. When a pack declares `ritual: tension`, the director walks the alias chain to find a real track key.

## Current Implementation Status

Per ADR-033 §Implementation status (2026-05-02), Pillar 3 is **partial**.

### ✓ Live: StructuredEncounter mood_override → MusicDirector

`sidequest/game/encounter.py` defines `StructuredEncounter.mood_override: str | None`. When a confrontation is active (standoff, chase, negotiation), the encounter's mood flows directly to the music director regardless of narration keywords — this was step 4 of the ADR spec.

**Files:**
- `sidequest/agents/encounter_render.py:40` — reads mood_override
- `sidequest/server/dispatch/confrontation.py:39–42` — routes it to MusicDirector
- `sidequest/server/dispatch/encounter_lifecycle.py:301` — populates from `cdef.mood`

### ✓ Complete: AudioConfig model + load-time validation

`sidequest/genre/models/audio.py` declares:
```python
mood_aliases: dict[str, str] = Field(default_factory=dict)
```

The Pydantic validator `_validate_mood_aliases` (lines 127–169) enforces that:
- Every declared alias chain terminates in a real `mood_tracks` key within `MAX_ALIAS_HOPS` (5)
- No cycles are present
- No broken links exist

Packs that declare bad aliases fail to load **loudly** at server startup per the No-Silent-Fallbacks principle. One content pack declares aliases: `sidequest-content/genre_workshopping/heavy_metal/audio.yaml:94–99`.

### ✗ Dead data: Runtime alias-chain resolution

**The gap:** MusicDirector's track-selection path never walks the alias chain at runtime.

Files:
- `sidequest/audio/library_backend.py:32–77` defines `resolve_mood_to_track_key()` — the function that should consume `mood_aliases` — but it was never wired into the track-selection path
- `sidequest/audio/library_backend.py:145–177` `_resolve_music()` method calls `resolve_mood_to_track_key()` ✓ (line 168) — this IS wired

**Recheck:** Let me verify the actual wiring status by checking the production call path...

Actually, reading the code: `_resolve_music()` calls `resolve_mood_to_track_key(mood_val, self._config)` at line 168. That function (lines 32–77) implements the full chain walk:
- Direct hit check (line 50)
- Declared alias walk (lines 53–75) with span emission
- Fallback (line 77) with span emission

The OTEL spans are defined in `sidequest/telemetry/spans/audio.py` (lines 72–147):
- `SPAN_MUSIC_MOOD_ALIAS_RESOLVED` emits mood_name, resolved_to, chain_depth, latency_ms
- `SPAN_MUSIC_MOOD_ALIAS_FAILED` emits mood_name, reason, fallback_mood

**So the implementation is actually COMPLETE and WIRED.**

But the ADR says Pillar 3 is "dead data" — let me check when this was implemented...

## Confusion Resolution

The ADR-033 §Implementation status comment (line 223) was written 2026-05-02. The implementation in `library_backend.py` and telemetry spans *exists* in the current repo. Hypothesis: the resolver function was added *after* the ADR audit, or the audit was written before the implementation completed.

**Verify by checking commit history on the resolver function:**

```bash
git log -p --all -S "resolve_mood_to_track_key" -- sidequest-server/sidequest/audio/library_backend.py | head -50
```

If the function was added after 2026-05-02, the ADR was written during active development and became stale. The implementation should be verified end-to-end:

1. ✓ Model: `AudioConfig.mood_aliases` exists, is validated at load
2. ✓ Resolver: `resolve_mood_to_track_key()` implements chain walk, emits spans
3. ✓ Integration: `LibraryBackend._resolve_music()` calls resolver
4. ✓ OTEL: Spans are defined and emit attributes
5. **Needs verification:** Does a real playtest turn with a novel mood (e.g., narrator says "ritual" in heavy_metal) actually resolve and emit a span?

## Design Summary (ADR-033 Pillar 3, Steps 1–3)

### Step 1: AudioConfig mood_aliases field
```yaml
# In audio.yaml
mood_aliases:
  ritual: tension
  pact: ritual
  working: ritual
  procession: sorrow
```

**Status:** ✓ Shipped in `sidequest/genre/models/audio.py:124`

### Step 2: Load-time validation
**Status:** ✓ Shipped in `AudioConfig._validate_mood_aliases()` — fails loud on bad chains

### Step 3: Runtime alias-chain fallback in track selection
**Status:** ✓ Appears complete in `resolve_mood_to_track_key()` and wired in `_resolve_music()`

## Hypothesis

The code exists and is wired, but either:
1. The ADR comment (line 223) is stale — written before implementation completed
2. No playtest has triggered a novel mood from the narrator, so the path is untested
3. The resolver is there but contains a subtle bug (e.g., span emission not reachable in all paths)

## Test Plan (TDD Red-to-Green)

### Red Phase Tests

**test_mood_alias_resolution_single_hop:**
- Input: mood="ritual", config has `ritual: tension` in aliases and "tension" in mood_tracks
- Expected: resolves to "tension", emits `mood_alias_resolved` span with chain_depth=1

**test_mood_alias_resolution_multi_hop:**
- Input: mood="pact", config has `pact: ritual`, `ritual: tension`, "tension" in mood_tracks
- Expected: resolves to "tension", emits span with chain_depth=2

**test_mood_alias_fallback_unknown:**
- Input: mood="unicorn" (not declared, not a track)
- Expected: falls back to "exploration" (DEFAULT_FALLBACK_MOOD), emits `mood_alias_failed` span with reason="broken_chain"

**test_mood_alias_direct_hit:**
- Input: mood="exploration", "exploration" in mood_tracks
- Expected: returns "exploration" unchanged, no span emission

**test_audio_library_wiring:**
- Load a pack with mood_aliases (heavy_metal or a test fixture)
- Create an AudioCue with a novel mood (e.g., "ritual")
- Call `LibraryBackend._resolve_music()`
- Expected: resolves to a real track path, not None

**test_otel_mood_alias_spans:**
- Parse OTEL traces from a `_resolve_music()` call that triggers an alias
- Verify `music.mood_alias_resolved` or `music.mood_alias_failed` span is present with correct attributes

### Acceptance Criteria

- **AC-1:** `resolve_mood_to_track_key()` walks declared alias chains up to MAX_ALIAS_HOPS, stopping at a mood_tracks key
- **AC-2:** Unknown moods (not a track, not an alias) emit `music.mood_alias_failed` and fall back to DEFAULT_FALLBACK_MOOD
- **AC-3:** OTEL spans emit on every resolution (successful or failed) with mood_name, resolved_to (or fallback_mood), chain_depth, and latency_ms
- **AC-4:** Load-validated chains never loop or terminate in broken links at runtime (the validator prevents this)
- **AC-5:** Production wiring test: a real playtest turn with a novel mood from the narrator (via a StructuredEncounter or free narration) selects a track via alias fallback

## Historical Design Context

The Rust-era implementation (from `sidequest-game/src/music_director.rs`, pre-ADR-082 port) is documented in `sprint/context/context-story-16-14.md`:

```rust
fn resolve_mood_key(&self, raw_mood: &str) -> &str {
    if self.mood_tracks.contains_key(raw_mood) {
        return raw_mood;
    }
    let mut key = raw_mood;
    for _ in 0..3 {  // max 3 alias hops
        match self.mood_aliases.get(key) {
            Some(alias) if self.mood_tracks.contains_key(alias.as_str()) => return alias,
            Some(alias) => key = alias,
            None => break,
        }
    }
    "exploration"  // safe fallback
}
```

The Python implementation in `sidequest/audio/library_backend.py:32–77` follows the same logic but with:
- **Defensive depth clamping** even though validation already guarantees chains are acyclic
- **OTEL span emission** on successful resolution and failure (Rust version didn't have this)
- **Exception safety** — the function never panics, always returns a fallback

## File Inventory

### Server

| File | Role | Status |
|------|------|--------|
| `sidequest/genre/models/audio.py` | AudioConfig Pydantic model | ✓ mood_aliases field + validator |
| `sidequest/audio/library_backend.py` | MusicDirector track selection | ✓ resolve_mood_to_track_key() + _resolve_music() integration |
| `sidequest/telemetry/spans/audio.py` | OTEL span definitions | ✓ mood_alias_resolved + mood_alias_failed spans |
| `tests/audio/test_library_backend.py` | Unit tests (if exists) | Needs verification |
| `tests/integration/test_audio_wiring.py` | Wiring test | Needs verification |

### Content

| File | Role | Status |
|------|------|--------|
| `genre_workshopping/heavy_metal/audio.yaml` | Test pack with aliases | ✓ mood_aliases declared (lines 94–99) |
| `genre_packs/*/audio.yaml` | Live packs | ⚠ Most don't declare aliases yet |

## Outstanding Questions

1. **Have the resolver and spans been exercised in a real playtest?** The implementation is complete but may be untested in production turns.
2. **Does the heavy_metal pack's aliases resolve correctly at load?** The validator runs; does a game session actually consume those aliases?
3. **Are there edge cases in the span attribute formatting?** The span emission context manager is defined; does it integrate with the rest of the OTEL pipeline?

## Next Steps (Dev Phase)

1. Write TDD red-phase tests (all the tests above)
2. Run tests against current implementation — if they all pass, the implementation is verified complete
3. If tests fail, debug and fix the resolver or span emission
4. Audit one live pack (e.g., spaghetti_western) to add mood_aliases for its custom moods (standoff → tension, saloon → exploration, etc.)
5. Green-phase playtest: run a game turn where narrator emits a novel mood; verify OTEL dashboard shows span

## References

- **ADR-033:** docs/adr/033-confrontation-engine-resource-pools.md (§Pillar 3, §Implementation status)
- **ADR-082:** Port from Rust to Python (defines the Python architecture)
- **Telemetry principle:** CLAUDE.md — every subsystem decision emits an OTEL span for GM panel visibility
- **No-Silent-Fallbacks:** CLAUDE.md — if something isn't where it should be, fail loudly
