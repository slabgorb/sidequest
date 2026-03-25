# Deviation Format Specification

Authoritative format for entries in the `## Design Deviations` section of session files. Gates, agents, and the Architect spec-reconcile phase all reference this document.

## Entry Format

Each deviation entry is a markdown bullet with a bold short description, followed by six indented field lines. All six fields are required.

```markdown
- **{Short description}**
  - Spec source: {document path, section/AC reference}
  - Spec text: "{quoted original specification}"
  - Implementation: {what was actually built or tested}
  - Rationale: {why the deviation was made}
  - Severity: {minor | major}
  - Forward impact: {none | minor | breaking} — {affected story IDs and assumptions}
```

### Required Fields

| # | Field | Value | Description |
|---|-------|-------|-------------|
| 1 | Spec source | Document path and section/AC reference | Where in the spec the original requirement lives. Example: `context-story-5-1.md, AC-3` |
| 2 | Spec text | Quoted original specification | The verbatim text from the spec, in quotation marks. Example: `"reject invalid input with specific error messages"` |
| 3 | Implementation | What was actually built or tested | What the agent did instead of what the spec said |
| 4 | Rationale | Why the deviation was made | One-sentence justification for the departure |
| 5 | Severity | `minor` or `major` | Agent-assessed impact of the deviation |
| 6 | Forward impact | `none`, `minor`, or `breaking` | Whether this deviation affects downstream stories |

### Field Details

**Spec text** must be wrapped in quotation marks to distinguish the original spec language from the agent's paraphrase.

**Severity** is exactly one of:
- `minor` — deviation does not change the functional outcome
- `major` — deviation changes observable behavior or contracts

**Forward impact** is exactly one of:
- `none` — no downstream stories affected (complete value, no story IDs needed)
- `minor — {affected story IDs and assumptions}` — downstream stories may need adjustment
- `breaking — {affected story IDs and assumptions}` — downstream stories have broken assumptions

The em-dash (`—`) separates the impact level from the affected stories. Example: `breaking — Story 5-3 assumes ! is available for filter expressions`.

## Agent Subsections

Deviation entries are organized under agent-specific subsections within `## Design Deviations` in the session file. Each agent populates only their own subsection — TEA does not write under `### Dev (implementation)`, and Dev does not write under `### TEA (test design)`.

The three subsections are:

- `### TEA (test design)` — entries logged by TEA during the RED phase
- `### Dev (implementation)` — entries logged by Dev during the GREEN phase
- `### Architect (reconcile)` — entries logged by Architect during the spec-reconcile phase

### Session File Structure

```markdown
## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- **Used binary tree instead of Vec<FilterExpr>**
  - Spec source: context-story-5-1.md, AC-2
  - Spec text: "Parse filter expressions into a Vec<FilterExpr>"
  - Implementation: Chumsky foldl produces binary tree, used Expr::and() tree
  - Rationale: Chumsky foldl produces binary trees natively, matches DataFusion Expr::and()
  - Severity: minor
  - Forward impact: none

### Architect (reconcile)
- No deviations from spec.
```

## No-Deviation Entries

When an agent has no deviations to report, they write an explicit statement instead of leaving the subsection empty:

```markdown
### TEA (test design)
- No deviations from spec.
```

An empty subsection (heading present, no content) is invalid. The gate rejects it.

## Worked Example

Here is a complete deviation entry with all six fields, showing the `breaking` forward impact pattern:

```markdown
- **No ! as NOT alternative**
  - Spec source: context-story-5-2.md, AC-1
  - Spec text: "Support ! prefix for boolean negation"
  - Implementation: Only 'not' keyword supported, no ! operator
  - Rationale: Ambiguity with shell history expansion in CLI context
  - Severity: major
  - Forward impact: breaking — Story 5-3 assumes ! is available for filter expressions
```

And a minimal deviation with no downstream impact:

```markdown
- **Used property-based generation instead of example list**
  - Spec source: context-story-5-1.md, AC-3
  - Spec text: "reject invalid input with specific error messages"
  - Implementation: Tests use property-based generation to cover broader input space
  - Rationale: Catches more edge cases than enumerated examples
  - Severity: minor
  - Forward impact: none
```

## Gate Enforcement

The `deviations-logged` gate validates entries against this format. It checks the agent-specific subsection (determined by the `AGENT` argument) and verifies each entry has all six required fields. The gate fails with a field-level recovery message naming the entry and the missing field(s).

See `gates/deviations-logged.md` for the gate definition.
