# Workflow Gates

<info>
Conditional checks that block or allow workflow phase transitions. Gates enforce quality thresholds — tests must pass, reviews must be approved, instructions must be unambiguous — before an agent can hand off to the next phase.
</info>

## Overview

Gates live in `pennyfarthing-dist/gates/` and are referenced by workflow YAML files via the `gate.file` field on phase definitions. When an agent finishes a phase, the handoff CLI resolves the gate, spawns a Haiku subagent to evaluate it, and blocks the transition if the gate fails.

## Built-in Gates

| Gate | File | Purpose | Used By |
|------|------|---------|---------|
| **tests-pass** | `gates/tests-pass.md` | Verify all tests pass, working tree clean, correct branch | Dev → Reviewer transitions |
| **tests-fail** | `gates/tests-fail.md` | Verify tests are RED (failing) with AC coverage | TEA → Dev transitions |
| **approval** | `gates/approval.md` | Verify reviewer has issued explicit APPROVED verdict | Reviewer → SM transitions |
| **confidence** | `gates/confidence.md` | Check if user instruction is ambiguous | Any agent entry gate |
| **dev-exit** | `gates/dev-exit.md` | Composite: tests-pass + no debug code | Dev → Reviewer transitions |
| **sm-setup-exit** | `gates/sm-setup-exit.md` | Session file, fields, context, branch created | SM → next agent transitions |
| **merge-ready** | `gates/merge-ready.md` | No open non-draft PRs | SM new work gate |
| **status-sync** | `gates/status-sync.md` | Verify YAML and Jira status match expected state for phase | Phase entry gates |
| **release-ready** | `gates/release-ready.md` | Composite: tests-pass + build, version, changelog | DevOps pre-deploy |
| **reviewer-preflight-check** | `gates/reviewer-preflight-check.md` | Composite: tests-pass + code smells, error boundaries | Reviewer preflight |
| **context-ok** | `gates/context-ok.md` | Verify context usage is below threshold before phase transition | Any phase transition gate |
| **quality-pass** | `gates/quality-pass.md` | Composite: lint + type checks + tests via check.py quality runner | Dev → Reviewer transitions |

## Gate File Format

See [Gate Schema](../schemas/gate-schema.md) for the complete gate file format and XML structure.

## GATE_RESULT Contract

See [Gate Schema](../schemas/gate-schema.md#gate_result-contract) for the full `GATE_RESULT` YAML contract.

## Workflow Integration

Gates are declared in workflow YAML on phase transitions:

```yaml
phases:
  green:
    agent: dev
    gate:
      file: tests-pass     # References gates/tests-pass.md
    next: review
```

## Agent Exit Protocol

Agents interact with gates through the handoff CLI during their exit sequence:

```
1. Agent writes assessment to session file
2. pf handoff resolve-gate {story-id} {workflow} {phase}
   → Reads workflow YAML, finds gate for current phase
   → Returns RESOLVE_RESULT: {status: ready|skip|blocked, gate_file: ...}
3. If ready → spawn Haiku subagent with gate file → GATE_RESULT
4. If GATE_RESULT.status == fail → fix issues, retry (max 3)
5. If GATE_RESULT.status == pass → continue to complete-phase
6. pf handoff complete-phase {story-id} {workflow} {from} {to} {gate-type}
7. pf handoff marker {next-agent}
```

If a phase has no `gate:` block, `resolve-gate` returns `status: skip` and the agent proceeds directly to `complete-phase`.

## Gate Evaluations

Extended evaluation criteria can live in `gates/evaluations/`:

| File | Purpose |
|------|---------|
| `evaluations/confidence-sm.md` | Historical evaluation of SM confidence gate (led to agent-agnostic `confidence` gate) |

## Creating Custom Gates

1. Create `pennyfarthing-dist/gates/my-gate.md` following the XML format above
2. Reference it in a workflow phase: `gate: { file: my-gate }`
3. The gate runner discovers files in the `gates/` directory by name

Gates run as Haiku subagents — keep instructions focused and evaluation criteria concrete.

## Consumer Gate Extensions

Consumer repos can add custom quality checks to existing gates without forking or overriding the built-in gate files. Extensions are **additive only** — they can never weaken or remove built-in checks.

### Setup

1. **Write extension gate files** in `.pennyfarthing/gates/` using the standard `<gate>` schema:

```markdown
<!-- .pennyfarthing/gates/rustfmt-check.md -->
<gate name="rustfmt-check" model="haiku">
<purpose>Verify all Rust files are formatted with rustfmt.</purpose>
<pass>
Run `cargo fmt --check`. Exit code 0 = pass.

GATE_RESULT:
  status: pass
  gate: rustfmt-check
  message: "All Rust files properly formatted"
  checks:
    - name: rustfmt
      status: pass
      detail: "cargo fmt --check passed"
</pass>
<fail>
If cargo fmt --check exits non-zero, list the unformatted files.

GATE_RESULT:
  status: fail
  gate: rustfmt-check
  message: "Rust formatting errors found"
  checks:
    - name: rustfmt
      status: fail
      detail: "{list of unformatted files}"
  recovery:
    - "Run `cargo fmt` to auto-format all files"
</fail>
</gate>
```

2. **Declare extensions** in `.pennyfarthing/repos.yaml`:

```yaml
gates:
  extensions:
    dev-exit:
      - rustfmt-check
      - license-check
    quality-pass:
      - cargo-clippy
```

### How it works

When `resolve-gate` returns `RESOLVE_RESULT`, it includes a `gate_extensions` field listing any configured extensions:

```yaml
RESOLVE_RESULT:
  status: ready
  gate_type: dev_exit
  gate_file: gates/dev-exit
  gate_extensions:
    - gates/rustfmt-check
    - gates/license-check
  next_agent: reviewer
  next_phase: review
```

The agent runs the primary gate first. If it passes and `gate_extensions` is present, each extension gate runs sequentially. AND semantics — the first failure stops the chain. All checks arrays are merged into a combined result via `merge_gate_results()`.

### Key properties

- **Additive only** — extensions cannot weaken or remove built-in checks
- **Config-driven** — toggle extensions without deleting files
- **Same schema** — extension gates use identical `<gate>` XML format
- **Fail-fast** — missing extension file errors at resolve time, not at runtime
- **No workflow changes** — consumer never touches workflow YAML definitions

## Key Files

| File | Purpose |
|------|---------|
| `pennyfarthing-dist/gates/*.md` | Gate definitions |
| `pf/handoff/gate_runner.py` | Spawns gate subagents |
| `pf/handoff/gate_file.py` | Gate file discovery and resolution |
| `pf/handoff/resolve_gate.py` | Resolves gate for a workflow phase |

<info>
**ADR:** `docs/adr/0025-script-first-gate-extraction.md`
</info>
