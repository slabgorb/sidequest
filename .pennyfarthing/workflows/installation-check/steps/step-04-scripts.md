# Step 4: Hook Scripts

<step-meta>
step: 4
name: scripts
workflow: installation-check
agent: devops
gate: false
next: step-05-layout
</step-meta>

<purpose>
Verify that hook script files exist on disk and are executable. Step 3 checked that hooks are registered in settings.local.json — this step checks that the script files those hooks point to actually exist and can run.
</purpose>

<prerequisites>
- Hook configuration reviewed (step 3)
- Installation type known (symlink vs copy mode)
</prerequisites>

<instructions>
1. Run the doctor command for the scripts category
2. For each result, explain the relationship between the settings entry and the script file:
   - **hook/* checks**: Scripts in `.pennyfarthing/scripts/hooks/` (symlink mode) or `.claude/pennyfarthing/scripts/hooks/` (copy mode). These are the actual bash scripts that hooks execute.
   - **Execute permissions**: Scripts must be executable (`chmod +x`). A registered hook pointing to a non-executable script causes "Permission denied" errors on every tool use.
   - **git-hook/* checks**: Scripts in `.git/hooks/` (pre-commit, pre-push, post-merge). Framework repos should use symlinks to `pennyfarthing-dist/scripts/hooks/`; end-user repos use copies.
3. For git hooks, explain the difference between framework symlinks and user copies
4. Present the collaboration menu
</instructions>

<actions>
- Run: `pf validate --json --category scripts`
- Check: Hook scripts at `.pennyfarthing/scripts/hooks/` are executable
- Check: Git hooks at `.git/hooks/` are up-to-date
</actions>

<output>
Present results in two sections:

```markdown
## Hook Scripts

| Script | Status | Detail |
|--------|--------|--------|
| session-start.sh | ... | ... |
| pre-edit-check.sh | ... | ... |
| context-warning.sh | ... | ... |
| context-circuit-breaker.sh | ... | ... |
| bell-mode-hook.sh | ... | ... |
| question-reflector-check.sh | ... | ... |
| sprint-yaml-validation.sh | ... | ... |

## Git Hooks

| Hook | Status | Detail |
|------|--------|--------|
| pre-commit | ... | ... |
| pre-push | ... | ... |
| post-merge | ... | ... |
```
</output>

<switch tool="AskUserQuestion">
  <case value="fix" next="LOOP">
    Fix — Run `pf validate --fix --category scripts` to fix permissions and stale hooks
  </case>
  <case value="explain" next="LOOP">
    Explain — Deep dive on a specific script's behavior
  </case>
  <case value="continue" next="step-05-layout">
    Continue — Proceed to Layout check
  </case>
  <case value="recheck" next="LOOP">
    Recheck — Re-run after manual changes
  </case>
</switch>

<next-step>
After reviewing script results, proceed to step-05-layout.md for Directory & File Layout verification.
</next-step>

## Failure Modes

- Scripts missing after partial update (need `pennyfarthing update`)
- Execute permission stripped by git or file copy operations
- Git hooks stale after package version bump

## Success Metrics

- All hook scripts exist and are executable
- Git hooks match package source (or are custom non-pennyfarthing hooks)
