---
name: context
description: |
  Create epic or story context documents. Reads sprint YAML for epic/story data,
  reads context-schema.yaml for required sections, populates templates, and writes
  output to sprint/context/. Epic context is a single-agent operation (no tandem).
  Story context uses PM + tandem partner for domain-specific observations.
args: "create epic {id} | create story {id} [--no-tandem] [--tandem architect|ux]"
---

# /pf-context — Context Document Creation

Create structured context documents that downstream agents (TEA, Dev) consume during implementation.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `/pf-context create epic {id}` | Create epic context document |
| `/pf-context create story {id}` | Create story context document |

## Create Epic Context

When invoked with `create epic {id}`:

### Step 1: Read the Schema

Read `pennyfarthing-dist/templates/context-schema.yaml` to get the required and optional sections for epic context documents. The schema is the ONLY authority for sections — never hardcode section names.

### Step 2: Locate the Epic

Find the epic in sprint data. Try these approaches in order:

1. **By ordinal ID:** Run `pf sprint epic show {id}` to get epic metadata (title, Jira key, stories, points, repo)
2. **By Jira key:** If `{id}` is a Jira key (e.g., <PROJECT-KEY>), use it directly

Extract from the epic metadata:
- Epic title
- Jira key
- Story count and total points
- Priority
- Repo
- Story list with titles and points

### Step 3: Find Planning Documents

Check the epic's context in the sprint for referenced planning documents:

1. Read `sprint/context/context-epic-{id}.md` if it already exists (may have partial content)
2. Search `sprint/planning/` for PRDs and related docs that reference this epic
3. Check `docs/adr/` for ADRs that reference this epic's Jira key or topic

Build a planning documents table with document names, paths, and relevant sections.

### Step 4: Load the Template

Read the epic context template at `pennyfarthing-dist/templates/context-epic-template.md`.

### Step 5: Fill the Template

Populate each section from the data gathered:

| Section | Source |
|---------|--------|
| **Overview** | Epic title, description, priority, repo, story count from sprint data |
| **Planning Documents** | Table built in Step 3 |
| **Background** | Synthesize from planning docs — WHY this epic exists, current state, problem being solved |
| **Technical Architecture** | From ADR/planning docs — component structure, key files, data flow, interfaces |
| **Cross-Epic Dependencies** | From sprint data — what this epic depends on and what depends on it |

**Section quality guidelines:**
- Overview: 2-3 sentences plus metadata fields
- Background: 2-4 paragraphs with subsections as needed
- Technical Architecture: Component diagram, key files table, flow description
- Planning Documents: Table with document, path, and relevant sections
- Cross-Epic Dependencies: Bulleted lists of depends-on and depended-on-by

### Step 6: Write the Output

Write the completed context document to:

```
sprint/context/context-epic-{id}.md
```

Where `{id}` is the ordinal epic ID (e.g., `130`), not the Jira key.

### Step 7: Validate (if available)

If the context validator is available, run:

```bash
pf validate context-epic {id}
```

Report any validation errors. If the validator is not yet installed, skip this step.

## Constraints

- **Schema-driven:** Always read `context-schema.yaml` for sections (ADR-0029 Rule #2)
- **No tandem:** Epic context is strategic summary — single-agent operation
- **Naming convention:** `context-epic-{id}.md` with ordinal ID (ADR-0029 Rule #1)
- **Output location:** `sprint/context/` only (ADR-0029 Rule #7)
- **No frontmatter required:** Epic contexts have no required frontmatter (backward compat)

## Create Story Context

When invoked with `create story {id}`:

### Step 1: Read the Schema

Read `pennyfarthing-dist/templates/context-schema.yaml` to get the required and optional sections for story context documents. The schema is the ONLY authority for sections — never hardcode section names.

### Step 2: Locate the Story

Find the story in sprint data:

1. **Parse the story ID:** Extract epic number `{N}` from story ID `{N-N}` (e.g., story `130-2` belongs to epic `130`)
2. **Get story metadata:** Run `pf sprint story show {id}` to get title, points, workflow, type, acceptance criteria
3. **Get epic metadata:** Run `pf sprint epic show {N}` for parent epic context

### Step 3: Select Tandem Partner

Determine the tandem partner based on the story's workflow field from Step 2. The partner provides domain-specific observations during context creation.

**Partner selection mapping:**

| Workflow | Partner | Observation Focus |
|----------|---------|-------------------|
| `tdd` | architect | Technical guardrails, dependencies, constraints |
| `trivial` | architect | Technical guardrails, dependencies, constraints |
| `bdd` | ux-designer | Interaction patterns, accessibility, visual constraints |
| `bdd-tandem` | ux-designer | Interaction patterns, accessibility, visual constraints |

**Override flags:**

- `--no-tandem` — Skip partner spawn entirely. PM creates context solo. Use as escape hatch when tandem is unnecessary or unavailable.
- `--tandem architect` or `--tandem ux` — Override automatic selection. Forces a specific partner regardless of workflow type.

If no flag is provided, use the mapping table above. If the workflow doesn't match any row, default to `architect`.

### Step 4: Validate Parent Epic Context

Check that the parent epic context document exists:

```bash
ls sprint/context/context-epic-{N}.md
```

If the parent epic context file is missing, **fail with a clear error message:**

> Error: Parent epic context `sprint/context/context-epic-{N}.md` does not exist.
> Run `/pf-context create epic {N}` first to create the epic context.

Do not proceed with story context creation if the parent epic context is missing.

### Step 5: Load the Template

Read the story context template at `pennyfarthing-dist/templates/context-story-template.md`.

### Step 6: Spawn Tandem Backseat

If tandem is enabled (not `--no-tandem`), spawn a backseat observer using the tandem protocol. The backseat runs in the background and writes observations to `.session/{story_id}-tandem-{partner}.md`.

**Spawn the backseat** per `pennyfarthing-dist/guides/tandem-protocol.md`:

```
PARTNER: "{partner from Step 3}"
CHARACTER: "{resolve from theme}"
STORY_ID: "{story_id}"
SCOPE: "context-creation"
OBSERVATION_FILE: ".session/{story_id}-tandem-{partner}.md"
```

**Graceful degradation:** If the backseat fails to spawn or errors during observation, log a warning and continue solo. Tandem failure is silent — PM continues without partner observations. Context is still valid but may lack specialist input.

### Step 7: Fill the Template

Read the parent epic context and story metadata. Populate each section:

| Section | Source |
|---------|--------|
| **Business Context** | From epic context overview + story ACs — WHY this story matters, business value |
| **Technical Guardrails** | From epic architecture section + tandem observations — constraints, patterns, key files to use/avoid |
| **Scope Boundaries** | From story metadata — explicit in-scope and out-of-scope items |
| **AC Context** | From story ACs — expand terse acceptance criteria into testable detail |

**Optional sections** (include if relevant to the story's workflow):
- **Interaction Patterns** — UI flows, user journeys (for BDD/UX stories)
- **Accessibility Requirements** — a11y constraints (for frontend stories)
- **Visual Constraints** — design system, layout rules (for UI stories)

As you draft each section, incorporate any tandem observations that have been injected. The backseat partner contributes domain-specific detail:
- **Architect** observations enrich Technical Guardrails and Scope Boundaries
- **UX-Designer** observations enrich Interaction Patterns, Accessibility, and Visual Constraints

### Step 8: Write the Output

Write YAML frontmatter followed by the completed context document:

```markdown
---
parent: context-epic-{N}.md
workflow: {workflow}
---

# Story {id}: {title}

## Business Context
...
```

Write to:

```
sprint/context/context-story-{id}.md
```

Where `{id}` is the story ID (e.g., `130-2`).

### Step 9: Cleanup and Validate

If a tandem backseat is running, terminate it before finishing.

If the context validator is available, run:

```bash
pf validate context-story {id}
```

Report any validation errors. If the validator is not yet installed, skip this step.

## Constraints — Story Context

- **Schema-driven:** Always read `context-schema.yaml` for sections (ADR-0029 Rule #2)
- **Tandem selection:** Workflow field determines partner — tdd/trivial→architect, bdd/bdd-tandem→ux-designer (ADR-0029 Rule #5)
- **Tandem optional:** `--no-tandem` skips partner spawn; backseat failure continues solo (ADR-0029 Rule #9)
- **Parent required:** Must validate parent epic context exists before creating story context
- **Frontmatter required:** Story contexts must include `parent:` field in YAML frontmatter
- **Naming convention:** `context-story-{id}.md` with story ID (ADR-0029 Rule #1)
- **Output location:** `sprint/context/` only (ADR-0029 Rule #7)

## Examples

### Create story context for story 130-2

```
/pf-context create story 130-2
```

Reads story 130-2 metadata, validates epic 130 context exists, loads template, fills sections from epic context and story ACs, writes to `sprint/context/context-story-130-2.md` with `parent: context-epic-130.md` frontmatter.

### Create epic context for epic 130

```
/pf-context create epic 130
```

Reads epic 130 metadata, finds planning docs (PRD, ADR-0029), fills template, writes to `sprint/context/context-epic-130.md`.

### Create epic context by Jira key

```
/pf-context create epic <PROJECT-KEY>
```

Resolves Jira key to ordinal ID, then follows the same flow.
