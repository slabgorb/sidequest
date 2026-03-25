# Step 7: Optional Tools

<step-meta>
step: 7
name: tools
workflow: installation-check
agent: devops
gate: false
next: step-08-summary
</step-meta>

<purpose>
Check the pf Python CLI (required — all hooks depend on it).
</purpose>

<prerequisites>
- Core installation verified (steps 1-6)
</prerequisites>

<instructions>
1. Run the doctor command for the tools category
2. For each result, explain what the tool provides and when it's needed:
   - **tools/pf-cli**: **REQUIRED.** The Python `pf` command provides agent activation (`pf agent start`), hook dispatch (`pf hooks`), and sprint management. All Claude Code hooks call `pf` directly — without it, every session is broken. Install via `pipx install -e pennyfarthing-dist/` (editable) or `pipx install pennyfarthing-scripts` (released).
3. For missing tools: pf CLI is **required** (hooks depend on it)
4. Present the collaboration menu
</instructions>

<actions>
- Run: `pf validate --json --category tools`
- Check: `pf` CLI is available and reports a version
</actions>

<output>
Present results:

```markdown
## Tools Check Results

### Python CLI
| Check | Status | Detail |
|-------|--------|--------|
| pf CLI | ... | ... |

### Recommendation
[Based on results, recommend installation if pf CLI is missing]
```
</output>

<switch tool="AskUserQuestion">
  <case value="fix" next="LOOP">
    Fix — Run `pf validate --fix --category tools` to install pf CLI
  </case>
  <case value="explain" next="LOOP">
    Explain — Deep dive on the pf CLI's purpose
  </case>
  <case value="continue" next="step-08-summary">
    Continue — Proceed to Summary
  </case>
  <case value="recheck" next="LOOP">
    Recheck — Re-run after installing tools
  </case>
</switch>

<next-step>
After reviewing tools, proceed to step-08-summary.md for the final health report.
</next-step>

## Failure Modes

- Stale pf shim from deprecated uv install pointing to dead virtualenv

## Success Metrics

- **pf CLI is installed and functional** (non-negotiable — hooks are broken without it)
- User understands which optional tools they need
- Optional tools have clear install path if wanted
</output>
