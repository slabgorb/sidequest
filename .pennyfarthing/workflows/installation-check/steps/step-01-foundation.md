# Step 1: Foundation Check

<step-meta>
step: 1
name: foundation
workflow: installation-check
agent: devops
gate: false
next: step-02-commands
</step-meta>

<purpose>
Verify the core Pennyfarthing installation exists and is intact. This checks the manifest, core framework directories, symlinks, and file integrity — the foundation everything else depends on.
</purpose>

<prerequisites>
- Project has been initialized with `pf setup`
- Running from the project root directory
</prerequisites>

<instructions>
1. Run the doctor command for the installation category
2. For each result, explain what it checks and why it matters:
   - **manifest/exists**: The manifest tracks installed version and file hashes. Without it, Pennyfarthing can't detect drift or apply updates.
   - **core/* directories**: These contain agents, commands, guides, skills, personas, and scripts. Missing directories mean broken agent invocation.
   - **symlink/* checks** (symlink mode only): Symlinks to node_modules keep files in sync with the installed package version.
   - **core/integrity**: Detects locally modified framework files that may conflict with updates.
   - **core/completeness**: Flags missing files that should have been installed.
3. For any failures, explain the impact and offer remediation
4. Present the collaboration menu
</instructions>

<actions>
- Run: `pf validate --json --category installation`
- Check: manifest.json exists at `.pennyfarthing/manifest.json`
- Check: Core directories exist under `.claude/pennyfarthing/` or via symlinks
</actions>

<output>
Present results in a clear table format:

```markdown
## Foundation Check Results

| Check | Status | Detail |
|-------|--------|--------|
| manifest | ... | ... |
| core files | ... | ... |
| symlinks | ... | ... |

### Issues Found
[Explain each failure/warning with remediation steps]
```
</output>

<switch tool="AskUserQuestion">
  <case value="fix" next="LOOP">
    Fix — Run `pf validate --fix --category installation` to auto-repair
  </case>
  <case value="explain" next="LOOP">
    Explain — Deep dive on a specific check result
  </case>
  <case value="continue" next="step-02-commands">
    Continue — Proceed to Commands & Skills check
  </case>
  <case value="recheck" next="LOOP">
    Recheck — Re-run after manual changes
  </case>
</switch>

<next-step>
After reviewing foundation results, proceed to step-02-commands.md for Commands & Skills verification.
</next-step>

## Failure Modes

- Running from wrong directory (not project root)
- Manifest missing entirely (needs `pf setup`)
- Broken symlinks after `node_modules` cleanup without reinstall

## Success Metrics

- All manifest and core file checks pass
- User understands each check's purpose
- Any failures have clear remediation path
