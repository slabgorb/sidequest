# ProjectionFilter Predicate Catalog

The closed vocabulary of per-player asymmetry. Genre pack `projection.yaml`
files may reference these predicates; they may NOT invent new ones. Adding
a predicate requires a core PR (see bottom of this document).

Each predicate is a pure function of:
- `GameStateView` (read-only session state)
- the canonical event payload
- the viewer's player_id + character_id
- an optional `field_ref` argument (a field path on the payload)

Predicates return `False` on missing fields or unknown relationships — the
conservative direction (for redactions, this keeps the field masked).

## v1 Catalog

| Name | Argument | True when |
|---|---|---|
| `is_gm` | (none) | `view.is_gm(viewer_player_id)` is True. |
| `is_self(field)` | field path → character/player id | `payload[field]` equals the viewer's character id. |
| `is_owner_of(field)` | field path → item id | `view.owner_of_item(payload[field])` equals the viewer's player id. |
| `in_same_zone(field)` | field path → character id | Both viewer's character and `payload[field]` have the same `view.zone_of(...)`. Both must be non-None. |
| `visible_to(field)` | field path → character id | `view.visible_to(viewer_character, payload[field])` is True. |
| `in_same_party(field)` | field path → player id | `view.party_of(viewer)` equals `view.party_of(payload[field])`. Both must be non-None. |

## How to propose a new predicate

1. Open a PR against `sidequest-server/sidequest/game/projection/predicates.py`.
2. Implement the predicate as a function `_name(ctx, field_ref) -> bool`, conservative on missing inputs.
3. Register it in `PREDICATES`.
4. Extend `sidequest-server/sidequest/game/projection/validator.py` signature / field-type checks if the predicate has a special arg type.
5. Add unit tests in `sidequest-server/tests/game/projection/test_predicates.py`.
6. Add a row to the table above.

Keep predicates small and composable. If a genre wants a complex multi-condition
rule, express it as multiple rules rather than one predicate that does too much.
