# BikeLane

<info>
Workflow orchestration engine. Coordinates multi-agent development through three workflow patterns: phased (agent handoffs), stepped (progressive disclosure with gates), and procedural (flexible checklists).
</info>

## Workflow Types

### Phased — Agent-driven with automatic handoffs

Workflow definitions live in `pennyfarthing-dist/workflows/*.yaml`. Each YAML defines phases, agents, tandem/team pairings, and gates. Use `pf workflow list` to see all available workflows, `pf workflow show <name>` for phase details. **Read the YAML — don't rely on summaries.**

### Stepped — Progressive disclosure with user gates

One step loaded at a time. User approval at decision points. Supports tri-modal execution (create/validate/edit). BMAD 6.0 compatible.

| Workflow | Purpose |
|----------|---------|
| `architecture` | Architectural decision-making (7 steps) |
| `prd` | Product requirements (tri-modal) |
| `research` | Research & discovery (custom modes: market/domain/technical) |
| `sprint-planning` | Sprint planning facilitation |
| `epics-and-stories` | Epic and story breakdown |
| `release` | Release workflow with verification gates |
| `ux-design`, `quick-dev`, `product-brief`, `project-context`, `implementation-readiness` | Other stepped workflows |

### Procedural — Flexible agent-guided processes

No fixed step sequence. Checklist-based, agent discretion on order.

| Workflow | Purpose |
|----------|---------|
| `brainstorming` | Structured problem-solving (62 techniques) |
| `code-review` | Code review checklists |
| `retrospective` | Sprint retrospective |

## State Tracking

Workflow state lives in session files (`.session/{story-id}-session.md`):

```markdown
**Workflow:** architecture
**Type:** stepped
**Phase:** design
**Current Step:** 3
```

## Variable Resolution (priority order)

1. Workflow YAML `variables:` section
2. Session file values
3. `.pennyfarthing/config.local.yaml`
4. Environment/system variables
5. Defaults (e.g., `planning_artifacts: planning-artifacts/`)

## Key Files

| File | Purpose |
|------|---------|
| `pennyfarthing-dist/workflows/*.yaml` | Workflow definitions (19 total) |
| `pennyfarthing-dist/schemas/workflow-schema.md` | YAML schema reference |
| `pennyfarthing-dist/schemas/workflow-step-schema.md` | Step file XML tag schema |
| `packages/core/src/public/components/panels/BikeLanePanel.tsx` | Workflow visualization panel |
| `packages/core/src/public/hooks/useStory.ts` | Story/workflow state hook |
| `pennyfarthing-dist/scripts/migrate-bmad-workflow.mjs` | BMAD 6.0 import migration |

## Commands

| Command | Purpose |
|---------|---------|
| `/pf-workflow list` | List all workflows |
| `/pf-workflow show [name]` | Show workflow details |
| `/pf-workflow start <name>` | Start a workflow |
| `/pf-workflow start <name> --mode <mode>` | Start in specific mode |
| `/pf-workflow resume` | Resume interrupted workflow |
| `/pf-workflow status` | Show current progress |

