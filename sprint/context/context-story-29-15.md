---
parent: context-epic-29.md
---

# Story 29-15: Template Library (20 Reusable Room Shapes)

## Business Context

Authoring ASCII grids for hundreds of rooms across all genre packs requires reusable
templates. The template library provides ~20 room shapes that the World Builder (29-16)
selects and customizes. Templates are parameterized by size and room type, covering
corridors, chambers, and special shapes.

## Technical Approach

### Step 1: Create template directory

New directory: `sidequest-content/templates/tactical/`

Each template is a `.ascii` file containing:
- Line 1: metadata comment (`# corridor_straight, 8x4, exits: north south`)
- Remaining lines: the ASCII grid (using only structural glyphs, no legend features)

### Step 2: Author corridor templates

- `corridor_straight_8x4.ascii` -- straight passage, exits on short ends
- `corridor_straight_12x4.ascii` -- longer straight passage
- `corridor_bent_8x8.ascii` -- L-shaped bend
- `corridor_t_12x8.ascii` -- T-intersection
- `corridor_cross_12x12.ascii` -- four-way intersection

### Step 3: Author chamber templates

- `chamber_oval_12x12.ascii` -- nearly circular (Mawdeep-style)
- `chamber_oval_8x8.ascii` -- small circular
- `chamber_rect_12x8.ascii` -- rectangular room
- `chamber_rect_16x12.ascii` -- large rectangular
- `chamber_irregular_12x12.ascii` -- natural cave shape
- `chamber_irregular_16x12.ascii` -- large irregular
- `chamber_kidney_12x8.ascii` -- kidney/bean shape

### Step 4: Author special shape templates

- `room_L_12x12.ascii` -- L-shaped room
- `room_T_16x12.ascii` -- T-shaped room
- `room_alcove_12x12.ascii` -- room with side alcove
- `room_pillared_16x12.ascii` -- rectangular with pillar positions marked
- `room_pool_12x12.ascii` -- circular with central pool
- `room_stepped_12x12.ascii` -- multi-level (steps/platforms)
- `room_gallery_16x8.ascii` -- long room with side alcoves

### Step 5: Template index

Create `sidequest-content/templates/tactical/index.yaml`:
```yaml
templates:
  - file: corridor_straight_8x4.ascii
    room_types: [corridor]
    min_size: [2, 1]
    max_size: [3, 1]
    exits: [2]
  - file: chamber_oval_12x12.ascii
    room_types: [entrance, normal, boss]
    min_size: [3, 3]
    max_size: [4, 4]
    exits: [1, 2, 3, 4]
  ...
```

This lets the World Builder query: "give me a template for a 3x3 normal room with 3 exits."

## Acceptance Criteria

- AC-1: At least 20 template files exist in `sidequest-content/templates/tactical/`
- AC-2: Templates cover corridors (straight, bent, T, cross), chambers (oval, rect, irregular), and special shapes (L, T, alcove, pillared)
- AC-3: Each template has a metadata comment with shape name, dimensions, and exit count
- AC-4: Templates use only structural glyphs (`.`, `#`, `_`) -- no legend features
- AC-5: All templates pass validation rules 1-5 (dimensions, perimeter, flood fill)
- AC-6: `index.yaml` maps each template to room_types, size ranges, and exit counts
- AC-7: Templates are parameterized (exit positions marked but adaptable)

## Key Files

| File | Action |
|------|--------|
| `sidequest-content/templates/tactical/` | NEW: directory with 20 .ascii template files |
| `sidequest-content/templates/tactical/index.yaml` | NEW: template index with metadata |
