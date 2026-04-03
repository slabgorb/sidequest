---
parent: context-epic-23.md
workflow: tdd
---

# Story 23-11: Simplify tool sections — replace verbose flag tables with compact checklist format

## Business Context

The orchestrator's three script tool sections (encountergen, namegen, loadoutgen) use verbose
Markdown flag tables (~490 tokens total across all three). The prompt-reworked.md spec uses a
compact `<tool>` format with just command syntax + usage checklist (~150 tokens total). This
is a 70% token reduction in the Valley zone tool overhead.

Current format (encountergen, ~213 tokens):
```
[ENCOUNTER GENERATOR]
Generate enemy stat blocks from genre pack data.

Command:
{binary_path} --genre-packs-path {packs} --genre {genre} [options]

| Flag | Required | Description |
|------|----------|-------------|
| --tier | No | Power tier 1-4 ... |
...7 rows...

When to call: ...
Output: JSON with ...
Checklist after calling:
- [ ] Use the generated name ...
```

Target format from prompt-reworked.md (~50 tokens):
```
<tool name="ENCOUNTER">
When to call: any time new enemies enter the scene.
<command>sidequest-encounter [--tier N] [--count N] [--culture NAME] ...</command>
<usage>
- [ ] Use the generated name in your narration
- [ ] Reference abilities from the abilities list (not invented ones)
</usage>
</tool>
```

## Technical Guardrails

- Tool sections built in `orchestrator.rs` L297-L393 via match on tool_name
- Each tool has a `format!()` call building the full section string
- The verbose flag tables are not load-bearing — Claude can figure out flag usage from the command signature
- The "when to call" and "checklist after calling" ARE load-bearing — they guide tool invocation timing
- Story 23-6 changes command names to wrappers (do that first or combine)
- Story 23-9 removes --genre/--genre-packs-path flags (do that first or combine)
- **Natural batch: 23-6 + 23-9 + 23-11 all touch the same tool format strings**

## Scope Boundaries

**In scope:**
- Replace 3 verbose tool format strings with compact `<tool>` XML format
- Keep "when to call" guidance
- Keep checklist items
- Remove flag tables (flags visible in command signature)
- Remove "Output: JSON with..." descriptions (not needed — tools return structured data)
- Update `scripts/preview-prompt.py`
- Measure token savings

**Out of scope:**
- Adding new tools
- Changing tool behavior
- ScriptToolConfig struct changes

## AC Context

1. encountergen tool section uses compact `<tool>` XML format
2. namegen tool section uses compact `<tool>` XML format
3. loadoutgen tool section uses compact `<tool>` XML format
4. No flag tables in any tool section
5. "When to call" and checklist preserved in each tool
6. Total tool section tokens reduced by ~60% or more
7. `scripts/preview-prompt.py` updated with compact format
