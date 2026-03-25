# Command Tag Taxonomy Reference

**Status:** 46 command files audited. Last updated: 2026-02-08

---

## Tag Inventory Table

| Tag | Meaning | Usage | Files |
|-----|---------|-------|-------|
| `<purpose>` | What the command does and when to use it | Core rationale & quick summary | 23 |
| `<usage>` | How to invoke the command with syntax & examples | Syntax guide | 13 |
| `<on-invoke>` | Detailed step-by-step execution logic | Complex workflows (benchmarking, solo, checks) | 7 |
| `<workflow>` | High-level workflow phases and process flow | Process documentation | 11 |
| `<when-to-use>` | Situations where command applies | Decision guide | 11 |
| `<reference>` | Links to related files, scripts, skills | Resource index | 11 |
| `<instructions>` | Specific setup or execution steps | Agent-specific | 10 |
| `<agent-activation>` | How to activate agent with CLI | Agent commands | 10 |
| `<execution>` | Detailed execution with options and examples | Script-based commands | 3 |
| `<related>` | Related commands to consider | Cross-reference | 6 |
| `<prerequisites>` | Required setup or conditions | Prerequisite checklist | 2 |
| `<critical>` | Non-negotiable rules or restrictions | Mandatory rules | 2 |
| `<output-format>` | Expected output structure | Output specification | 4 |
| `<critical-integrity-requirements>` | Data integrity constraints (benchmarking) | Specialized validation | 2 |
| `<when-not-to-use>` | When NOT to use this command | Exclusion guidance | 1 |
| `<variants>` | Command variants & differences | Variation guide | 1 |
| `<key-differences>` | How this differs from similar commands | Comparison | 1 |
| `<error-handling>` | Error cases and messages | Error reference | 1 |
| `<integration>` | Integration with other systems | System integration | 2 |
| `<quick-start>` | Quick start for new users | Onboarding | 1 |
| `<commands>` | Subcommands available | Command reference | 1 |
| `<themes>` | Theme selection reference | Theme documentation | 1 |
| `<context-aware>` | Context-aware help based on state | Conditional help | 1 |
| `<health-checks>` | Health check details and procedures | Diagnostic procedures | 1 |
| `<auto-fixes>` | Auto-fix capabilities and warnings | Auto-remediation | 1 |
| `<drift-detection>` | Behavior drift detection | Monitoring | 1 |
| `<requirements>` | Required tools and installations | Tool requirements | 1 |
| `<detection-order>` | Detection priority order | Detection logic | 1 |
| `<agents>` | Agent reference table | Agent directory | 1 |
| `<command>` | YAML frontmatter directive | Metadata | 1 |
| `<architecture>` | High-level architecture diagram | System design | 1 |
| `<parallel-work-flow>` | Parallel work setup flow | Worktree workflow | 1 |
| `<agent-exit>` | Agent exit behavior | State management | 1 |
| `<no-checkpoints>` | Handling missing checkpoints | Edge case | 1 |
| `<checkpoint-labels>` | Checkpoint label patterns | Checkpoint reference | 1 |
| `<stale-checkpoint-warning>` | Stale checkpoint warnings | Warning handling | 1 |
| `<skip-check>` | Emergency skip behavior | Override handling | 1 |
| `<description>` | YAML frontmatter description | Metadata | 1 |
| `<workflow>` (YAML) | YAML frontmatter workflow reference | Metadata | 1 |
| `<skills>` | Related skills | Skill reference | 1 |
| `<commands>` (sub) | Available subcommands | Subcommand reference | 1 |

---

## Recommended Standard

### Mandatory (Expected in all commands)

- **`<purpose>`** — Essential for user understanding
- **`<usage>`** — Essential for activation

### Conditional by Type

**Workflow/Agent Commands (e.g., /pf-sm, /pf-dev, /pf-tea)**
- `<agent-activation>` — Required to show activation
- `<instructions>` — Required for agent behavior

**Script-Based Commands (e.g., /check, /pf-ci run)**
- `<execution>` — Required with options
- `<reference>` — Links to scripts

**Complex Multi-Step (e.g., /benchmark, /solo)**
- `<on-invoke>` — Step-by-step breakdown
- `<reference>` — Links to judge, finalize-run

**Decision-Making Commands (e.g., /patch, /chore)**
- `<when-to-use>` — When to pick this
- `<when-not-to-use>` — When NOT to pick this
- `<related>` — Alternatives to consider

**Workflow/Phase Commands (e.g., /sprint, /pf-git release)**
- `<workflow>` — Phase breakdown
- `<commands>` or subcommand table — Available subcommands

### Optional but Helpful

- `<reference>` — Always include links to related files
- `<related>` — Cross-reference similar commands
- `<error-handling>` — For commands that can fail
- `<output-format>` — For structured output commands

---

## Consistency Gaps

### Missing `<purpose>` (Core)
- (None - all files have purpose or instruction)

### Missing `<usage>` Examples
Files with no usage examples (mostly pure-markdown or markdown+comment style):
- brainstorming.md (informal, no examples needed)
- party-mode.md (informal)
- create-branches-from-story.md
- create-theme.md
- list-themes.md
- permissions.md
- repo-status.md
- retro.md
- show-theme.md
- start-epic.md
- sync-epic-to-jira.md
- sync-work-with-sprint.md
- theme-maker.md
- update-domain-docs.md
- set-theme.md

**ACTION:** Recommend adding `<usage>` with minimal examples to non-markdown commands.

### Missing `<reference>` (Helpful)
Files without resource links:
- brainstorming.md
- create-branches-from-story.md
- create-theme.md
- fix-blocker.md
- git-cleanup.md
- job-fair.md
- list-themes.md
- party-mode.md
- permissions.md
- repo-status.md
- retro.md
- show-theme.md
- start-epic.md
- sync-epic-to-jira.md
- sync-work-with-sprint.md
- theme-maker.md
- update-domain-docs.md
- set-theme.md
- architect.md
- dev.md
- devops.md
- orchestrator.md
- pm.md
- reviewer.md
- sm.md
- tea.md
- tech-writer.md
- ux-designer.md

**ACTION:** Consider adding `<reference>` section to guide files and agent files linking to relevant skill/agent docs.

### Agent Commands Lack Consistency
Agent activation commands (architect, dev, devops, orchestrator, pm, reviewer, sm, tea, tech-writer, ux-designer, work):
- Only have `<agent-activation>` + `<instructions>`
- Missing: `<purpose>`, `<when-to-use>`, `<reference>`

**ACTION:** Add fuller `<purpose>` and `<reference>` to agent commands.

### Missing Tag Patterns by Category

| Command Type | Gap |
|--------------|-----|
| **Theme Commands** (create, set, show, list, theme-maker) | Inconsistent use of `<usage>`. Only `theme-maker` uses XML tags extensively. |
| **Sprint Commands** (sprint, start-epic, close-epic) | Some pure markdown, no `<usage>`. |
| **Git Commands** (chore, patch, git-cleanup, standalone) | Good coverage, no gaps. |
| **Config/Setup** (setup, health-check, permissions) | Needs `<usage>` examples. |

---

## Patterns & Recommendations

### High-Quality Examples (Model These)

**benchmark.md** — Comprehensive tag coverage
- `<purpose>` + `<critical-integrity-requirements>` + `<usage>` + `<on-invoke>` (11 detailed steps) + `<error-handling>` + `<reference>`

**solo.md** — Well-structured complex command
- `<purpose>` + `<architecture>` + `<usage>` + `<on-invoke>` (10 detailed steps) + `<reference>`

**patch.md** — Good decision guidance
- `<purpose>` + `<when-to-use>` + `<when-not-to-use>` + `<usage>` + `<key-differences>` + `<workflow>` + `<related>`

### Improvement Opportunities

**Low-quality (Pure Markdown, No Structure)**
- brainstorming.md — Use `<purpose>`, `<usage>`, `<workflow>` tags
- retro.md — Use `<purpose>`, `<workflow>`, `<reference>` tags
- party-mode.md — Add structure with tags
- start-epic.md → Already has good content, just needs XML tags

**Mixed Quality (Some Tags)**
- help.md — Good breadth, but inconsistent sections
- workflow.md — Minimal; needs expansion
- permissions.md — Good CLI reference, needs `<usage>` tags

---

## Summary

**Total Commands:** 46
**Commands with Purpose Tag:** 23+ (50%+)
**Commands with Usage Tag:** 13 (28%)
**Commands with On-Invoke Detail:** 7 (15%)

**Consistency Score:** ~60% — Good foundation, room for improvement in usage examples and cross-references.

**Key Recommendation:** Standardize on:
1. **All files** → `<purpose>` + `<usage>` (minimum viable)
2. **Complex workflows** → Add `<on-invoke>` with numbered steps
3. **All files** → Add `<reference>` with related file links
4. **Decision commands** → Add `<related>` for alternatives
5. **Convert pure Markdown** → Wrap sections in XML tags for consistency
