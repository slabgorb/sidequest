---
name: workflow
description: |
  List available workflows, show current workflow details, and switch workflows mid-session. Use when checking available workflow types (TDD, trivial, agent-docs), viewing current workflow phase, switching to a different workflow pattern, or managing BikeLane stepped workflows.
args: "[list|show [name]|set <name>|start <name> [--mode <mode>]|resume [name]|status|check|fix-phase]"
---

# /pf-workflow - Workflow Management

Pennyfarthing uses YAML-defined workflows to control agent sequences. The default TDD workflow (SM > TEA > Dev > Reviewer) can be customized or replaced.

## Quick Reference

### Python CLI Commands

| Command | CLI | Purpose |
|---------|-----|---------|
| `/pf-workflow` or `/pf-workflow list` | `pf workflow list` | List all workflows |
| `/pf-workflow show [name]` | `pf workflow show [name]` | Show workflow details |
| `/pf-workflow set <name>` | Edit session file `**Workflow:**` line | Switch workflow mid-session |
| `/pf-workflow start <name>` | `pf workflow start <name> [--mode M]` | Start stepped workflow |
| `/pf-workflow resume [name]` | `pf workflow resume [name]` | Resume interrupted workflow |
| `/pf-workflow status` | `pf workflow status` | Show stepped workflow progress |
| `/pf-workflow fix-phase <id> <phase>` | `pf workflow fix-phase <id> <phase> [--dry-run]` | Repair session phase |
| Check workflow state | `pf workflow check [--json]` | Current story, phase, state |
| Check phase owner | `pf workflow phase-check <workflow> <phase>` | Which agent owns a phase |
| Get workflow type | `pf workflow type <workflow>` | phased/stepped/procedural |
| Emit handoff marker | `pf workflow handoff <next-agent>` | Handoff marker for Frame GUI |
| Complete step | `pf workflow complete-step [name] [--step N]` | Advance stepped workflow |

### Built-in Workflows

| Workflow | Flow | Triggers |
|----------|------|----------|
| `tdd` (default) | SM > TEA > Dev > Reviewer > SM | features, 3+ points |
| `trivial` | SM > Dev > Reviewer > SM | chores/fixes, 1-2 points |
| `bdd` | SM > UX > TEA > Dev > Reviewer > SM | UI/UX features |
| `agent-docs` | SM > Orchestrator > Tech Writer > SM | docs, agent-file label |
| `architecture` | 7 stepped phases with gates | architecture/design/ADR |

---

**Detailed options and behavior:** [usage.md](usage.md)
**Practical examples:** [examples.md](examples.md)
