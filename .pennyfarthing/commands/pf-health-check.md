---
description: Check Pennyfarthing installation health and apply updates
---

```bash
pf agent start "devops"
```

<agent-activation>
1. Load DevOps agent for infrastructure work
2. Run health check via CLI
</agent-activation>

<purpose>
Examine current Pennyfarthing installation, detect drift from expected state, and guide user through fixes/updates.
</purpose>

<when-to-use>
- After updating Pennyfarthing (see [Updating](#updating) below)
- When something seems broken
- Periodic health verification
- Before starting new sprint
</when-to-use>

<health-checks>

## Health Check Modes

### Quick Mode (CLI — for automation/CI)

```bash
# Run all validators
pf validate

# Check a specific validator
pf validate sprint
pf validate hooks

# Auto-fix issues
pf validate --fix

# Strict mode (warnings as errors)
pf validate --strict
```

Validators: `sprint`, `schema`, `agent`, `workflow`, `skill-command`, `tandem-awareness`

### Interactive Mode (Workflow — for onboarding/troubleshooting)

```
/pf-workflow start installation-check
```

Walks through guided verification with AI-assisted explanation and remediation.

## Check for Updates

```bash
# Check installed version
pf --version

# Upgrade (use whichever you installed with)
pipx upgrade pennyfarthing-scripts       # pipx
uv tool upgrade pennyfarthing-scripts    # uv

# Re-init project after upgrade
pf init
pf doctor
```

</health-checks>

<output-format>

```markdown
# Pennyfarthing Health Check

## Installation: pf v{version}
## Status: [HEALTHY | NEEDS_UPDATE | NEEDS_FIX]

### Checks
| Check | Status | Detail |
|-------|--------|--------|
| Sprint YAML | OK | Valid structure |
| Agent defs | OK | All present |
| Workflows | OK | All valid |
| Hooks | WARN | Missing hook |

### Recommended Actions
1. [Action with command to run]
2. [Action with command to run]
```

</output-format>

<auto-fixes>

```bash
pf validate --fix
```

The CLI can auto-fix:
- Sprint YAML format issues
- Schema validation warnings

**Always ask before applying fixes.**

</auto-fixes>

<drift-detection>

## Agent Behavior Drift Detection

Check if agents are following expected behavioral patterns:

```bash
# Run drift detection
.pennyfarthing/scripts/health/drift-detection.sh

# Verbose mode (see individual files)
.pennyfarthing/scripts/health/drift-detection.sh --verbose
```

The script analyzes archived session files for:

| Agent | Checks For |
|-------|------------|
| **Reviewer** | Substantive comments (not just approvals) |
| **Dev** | Test evidence when declaring GREEN |
| **SM** | Structured handoff sections with target agent |
| **TEA** | Test file references before Dev handoff |

**Healthy rates:** Under 10% drift is considered normal.

**When drift is high:**
- Review agent behavior files for clarity
- Add explicit gates/checklists
- Consider making critical behaviors automatic via scripts

</drift-detection>

<reference>
- **CLI:** `pf validate`, `pf --version`
- **Manifest:** `.pennyfarthing/init-manifest.json` (tracks version and file hashes)
- **Config:** `.pennyfarthing/config.local.yaml` (theme, settings)
- **Symlinks:** `.pennyfarthing/agents/`, `.claude/commands/`, etc.
- **Drift Detection:** `.pennyfarthing/scripts/health/drift-detection.sh`
</reference>
