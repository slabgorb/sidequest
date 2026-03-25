# Step 5: Directory & File Layout

<step-meta>
step: 5
name: layout
workflow: installation-check
agent: devops
gate: false
next: step-06-legacy
</step-meta>

<purpose>
Verify that files and directories are at their correct locations. Pennyfarthing has migrated file locations across versions — this step ensures everything is at the current canonical paths and flags any files stuck at old locations.
</purpose>

<prerequisites>
- Foundation and commands checks completed (steps 1-2)
</prerequisites>

<instructions>
1. Run the doctor command for the layout category
2. For each result, explain the expected location and why it matters:
   - **dir/sprint**: `sprint/` directory holds sprint tracking YAML files.
   - **dir/session**: `.session/` stores active work session files for each story.
   - **layout/manifest**: `.pennyfarthing/manifest.json` tracks installed version.
   - **layout/config**: `.pennyfarthing/config.local.yaml` stores theme and local settings.
   - **layout/settings**: `.claude/settings.local.json` registers hooks with Claude Code.
   - **layout/sidecars**: `.pennyfarthing/sidecars/` stores per-agent learning files.
   - **layout/project-hooks**: `.pennyfarthing/project/hooks/` stores user-customized hook scripts (setup-env.sh, auto-load-sm.sh).
   - **layout/*-old-location**: Files found at legacy paths that should be migrated.
3. For old-location warnings, explain when the migration happened and what the fix does
4. Present the collaboration menu
</instructions>

<actions>
- Run: `pf validate --json --category layout`
- Check: `sprint/` and `.session/` directories exist
- Check: Files at canonical `.pennyfarthing/` locations
</actions>

<output>
Present results:

```markdown
## Directory & File Layout Results

| Check | Status | Detail |
|-------|--------|--------|
| sprint dir | ... | ... |
| session dir | ... | ... |
| manifest location | ... | ... |
| config location | ... | ... |
| settings location | ... | ... |
| sidecars location | ... | ... |
| project hooks | ... | ... |

### Migration Needed
[List any files at old locations with migration path]
```
</output>

<switch tool="AskUserQuestion">
  <case value="fix" next="LOOP">
    Fix — Run `pf validate --fix --category layout` to migrate files
  </case>
  <case value="explain" next="LOOP">
    Explain — Deep dive on the file layout evolution
  </case>
  <case value="continue" next="step-06-legacy">
    Continue — Proceed to Legacy cleanup check
  </case>
  <case value="recheck" next="LOOP">
    Recheck — Re-run after manual moves
  </case>
</switch>

<next-step>
After reviewing layout results, proceed to step-06-legacy.md for Legacy artifact cleanup.
</next-step>

## Failure Modes

- Moving files manually without updating references in settings.local.json
- Missing sprint/ or .session/ directories (need `pf setup`)

## Success Metrics

- All files at canonical locations
- No old-location warnings remaining
