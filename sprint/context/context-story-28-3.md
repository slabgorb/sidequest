---
parent: context-epic-28.md
---

# Story 28-3: Populate Beats in Confrontation Protocol Message

## Business Context

`dispatch/mod.rs:2393` sends `beats: vec![]` in every Confrontation message. The UI's
ConfrontationOverlay (235 LOC, fully functional) renders beat buttons from this array.
Empty array = no buttons = dead interaction loop. The BeatOption type is already defined
in the UI (`ConfrontationOverlay.tsx:20-27`). The ConfrontationPayload beat field exists
in the protocol (`message.rs:752`). There's just nothing in them.

## Technical Approach

### The Fix

In `dispatch/mod.rs` around line 2354-2399 where the Confrontation message is built:
1. Look up the ConfrontationDef from `ctx.confrontation_defs` by `enc.encounter_type`
2. Map `def.beats` to `sidequest_protocol::ConfrontationBeat` structs
3. Populate the `beats` field instead of `vec![]`

### Protocol types already exist

`sidequest-protocol/src/message.rs:752`:
```rust
pub struct ConfrontationBeat {
    pub id: String,
    pub label: String,
    pub metric_delta: i32,
    pub stat_check: String,
    pub risk: Option<String>,
    pub resolution: Option<bool>,
}
```

### UI types already exist

`ConfrontationOverlay.tsx:20-27`:
```typescript
interface BeatOption {
  id: string; label: string; metric_delta: number;
  stat_check: string; risk?: string; resolution?: boolean;
}
```

The mapping is 1:1. The UI is ready. Just populate the data.

## Key Files

| File | Action |
|------|--------|
| `sidequest-server/src/dispatch/mod.rs` | Line ~2393: look up def, map beats, populate field |

## Acceptance Criteria

| AC | Detail | Wiring Verification |
|----|--------|---------------------|
| Beats populated | Confrontation message beats field is non-empty when a def exists | Test: create encounter with known type, verify beats in message |
| 1:1 mapping | Each BeatDef field maps to ConfrontationBeat field (id, label, metric_delta, stat_check, risk, resolution) | Test: verify all fields present |
| Graceful | If no ConfrontationDef found for encounter_type, beats remain empty (implicit combat/chase before 28-10) | Test: unknown type → empty beats |
| OTEL | encounter.beats_sent event with encounter_type, beat_count, beat_ids | Grep: WatcherEventBuilder "beats_sent" in dispatch/mod.rs |
| Wiring | `beats: vec![]` no longer exists on line ~2393 | `grep "beats: vec!\[\]" dispatch/mod.rs` returns nothing |
| UI renders | Beat buttons appear in ConfrontationOverlay when beats are populated | Manual or integration test |

## Scope Boundaries

**In scope:** Populating beats from ConfrontationDef in the Confrontation message
**Out of scope:** Handling beat selection from the UI (28-5), narrator beat selection (28-6)
