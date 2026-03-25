# Step 1: Category Selection

<step-meta>
number: 1
name: category
gate: true
next: step-02-metadata
</step-meta>

<purpose>
Select the benchmark scenario category, scan for existing scenarios in that category, and auto-derive the next available scenario ID.
</purpose>

<instructions>
1. Present all 7 benchmark categories with descriptions
2. Ask the user to select a category
3. Scan `{benchmarks_root}/{category}/` for existing scenario files
4. Display existing scenarios so the user knows what already exists
5. Auto-derive the next ID based on existing files (e.g., if `arch-001` exists, suggest `arch-002`)
6. Route to the correct mode based on category family
</instructions>

<actions>
- Read: `{benchmarks_root}/` directory listing for all categories
- Read: `{benchmarks_root}/{category}/*.yaml` for existing scenarios
</actions>

## Category Reference

Present these categories to the user:

### Code-Based Categories (use `code` mode)
| Category | Prefix | Agent | Description |
|----------|--------|-------|-------------|
| `code-review` | `cr` | reviewer | Code with seeded bugs/vulnerabilities for review |
| `dev` | `dev` | dev | Implementation challenges with bugs or requirements |
| `tea` | `tea` | tea | Code requiring test suite authoring |
| `test-writing` | `tw` | tea | Focused test-writing scenarios |

### Open-Ended Categories (use `open-ended` mode)
| Category | Prefix | Agent | Description |
|----------|--------|-------|-------------|
| `architecture` | `arch` | architect | System design problems with trade-offs |
| `pm` | `pm` | pm | Product/prioritization scenarios with stakeholder dynamics |
| `sm` | `sm` | sm | Feature breakdown and sprint planning challenges |

## ID Derivation

Scan existing files matching `{prefix}-NNN-*.yaml` and derive the next sequential number:
- Files: `arch-001-notification-system.yaml` -> next: `arch-002`
- Files: (none) -> next: `sm-001`

<output>
- Selected category stored in `{scenario_category}`
- Auto-derived ID stored in `{scenario_id}` (prefix + number only, slug added later)
- List of existing scenarios stored in `{existing_scenarios}`
- Mode determined: `code` or `open-ended`
</output>

<gate>
## Completion Criteria
- [ ] Category selected from valid options
- [ ] Existing scenarios scanned and displayed
- [ ] Next ID auto-derived
- [ ] Correct mode determined (code vs open-ended)
</gate>

<switch on="category_family">
  <case value="code-review,dev,tea,test-writing" next="step-02-metadata">
    Code mode -- load steps-code/step-02-metadata.md instead
  </case>
  <case value="architecture,pm,sm" next="step-02-metadata">
    Open-ended mode -- proceed to metadata in steps-open
  </case>
</switch>

<next-step>
After category is selected, proceed to step-02-metadata.md for common metadata fields.
If a code-based category was selected, load from steps-code/ instead.
</next-step>

## Failure Modes

- Not scanning for existing scenarios (leads to duplicate IDs)
- Not routing to the correct mode directory
- Accepting an invalid category name
