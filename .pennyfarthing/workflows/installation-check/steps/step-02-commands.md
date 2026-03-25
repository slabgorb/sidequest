# Step 2: Commands & Skills

<step-meta>
step: 2
name: commands
workflow: installation-check
agent: devops
gate: false
next: step-03-hooks
</step-meta>

<purpose>
Verify that slash commands, skills, user project files, and configuration are properly installed. These are the agent interface layer — what users and agents interact with directly.
</purpose>

<prerequisites>
- Foundation check (step 1) completed
- `.claude/` directory exists
</prerequisites>

<instructions>
1. Run the doctor command for the commands category
2. For each result, explain what it checks and why it matters:
   - **core/commands**: Slash commands (`.claude/commands/pf-*.md`) should be file copies (not symlinks) to avoid node_modules drift. Stale copies mean agents use outdated instructions.
   - **core/skills**: Skills (`.claude/skills/pf-*/`) should also be file copies. Missing skills break agent workflows.
   - **project/directory**: `.claude/project/` holds user-specific project configuration.
   - **project/sidecars**: `.pennyfarthing/sidecars/` stores per-agent learning files that accumulate context across sessions.
   - **persona-config**: `.pennyfarthing/config.local.yaml` sets the active theme. Without it, agents use default (unthemed) personas.
   - **settings.local.json**: The most critical user file — registers hooks with Claude Code. Missing = no hooks, no OTEL, no bell mode.
3. For warnings about stale/symlinked commands, explain the migration from symlinks to copies (v11.3.0+)
4. Present the collaboration menu
</instructions>

<actions>
- Run: `pf validate --json --category commands`
- Check: `.claude/commands/` contains `pf-*` files (copies, not symlinks)
- Check: `.claude/skills/` contains `pf-*` directories (copies, not symlinks)
- Check: `.pennyfarthing/config.local.yaml` exists
</actions>

<output>
Present results in a clear table format:

```markdown
## Commands & Skills Check Results

| Check | Status | Detail |
|-------|--------|--------|
| commands | ... | ... |
| skills | ... | ... |
| project dir | ... | ... |
| sidecars | ... | ... |
| persona config | ... | ... |
| settings.local.json | ... | ... |

### Issues Found
[Explain each failure/warning with remediation steps]
```
</output>

<switch tool="AskUserQuestion">
  <case value="fix" next="LOOP">
    Fix — Run `pf validate --fix --category commands` to auto-repair
  </case>
  <case value="explain" next="LOOP">
    Explain — Deep dive on a specific check result
  </case>
  <case value="continue" next="step-03-hooks">
    Continue — Proceed to Hook Configuration check
  </case>
  <case value="recheck" next="LOOP">
    Recheck — Re-run after manual changes
  </case>
</switch>

<next-step>
After reviewing command and skill results, proceed to step-03-hooks.md for Hook Configuration verification.
</next-step>

## Failure Modes

- Commands still symlinked from pre-v11.3 installs
- Skills missing after partial update
- settings.local.json deleted by user accidentally

## Success Metrics

- All commands and skills are file copies (not symlinks)
- settings.local.json exists
- User understands the symlink-to-copy migration
