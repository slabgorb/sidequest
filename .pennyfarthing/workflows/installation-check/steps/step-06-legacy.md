# Step 6: Legacy Artifact Cleanup

<step-meta>
step: 6
name: legacy
workflow: installation-check
agent: devops
gate: true
next: step-07-tools
</step-meta>

<purpose>
Detect and clean up legacy artifacts from previous Pennyfarthing versions. These include old statusline scripts, persona configs at deprecated paths, legacy sidecar directories, and hook commands still using `.sh` scripts instead of `pf hooks` commands. This step has a gate because some fixes delete files.
</purpose>

<prerequisites>
- Layout check completed (step 5)
- User understands current vs legacy file locations
</prerequisites>

<instructions>
1. Run the doctor command for the legacy category
2. For each result, explain what the legacy artifact is and why it should be cleaned up:
   - **legacy/.claude/scripts/statusline.sh**: Old statusline location that may shadow the proper `.pennyfarthing/scripts/misc/statusline.sh`.
   - **legacy/.claude/persona-config.yaml**: Pre-v7 theme config. Should be migrated to `.pennyfarthing/config.local.yaml`.
   - **legacy/.claude/project/agents/sidecars**: Pre-v8 sidecar location. Should be at `.pennyfarthing/sidecars/`.
   - **legacy/sprint/sidecars**: Another pre-v8 sidecar location.
   - **legacy/.claude/project/hooks/setup-env.sh**: Pre-v9 hook location. Should be at `.pennyfarthing/project/hooks/`.
   - **settings/statusline-path**: settings.local.json references a legacy statusline script path.
   - **legacy/hook-commands**: Hook entries in settings.local.json still use `.sh` script paths instead of `pf hooks` commands. The `.sh` scripts work (they're shims) but `pf hooks` is faster — no shell indirection.
3. For each fix, explain what will be deleted or moved and whether it's reversible
4. Present gate criteria — user must approve before files are deleted

**IMPORTANT:** Legacy cleanup deletes files. The user may have customized legacy locations. Always explain what will be removed before applying fixes.
</instructions>

<actions>
- Run: `pf validate --json --category legacy`
- Check: No legacy artifacts at `.claude/scripts/`, `.claude/persona-config.yaml`
- Check: No legacy sidecar directories
- Check: Hook commands use `pf hooks` not `.sh` scripts
</actions>

<output>
Present results:

```markdown
## Legacy Artifact Check Results

| Artifact | Status | Detail |
|----------|--------|--------|
| statusline.sh | ... | ... |
| persona-config.yaml | ... | ... |
| agent sidecars | ... | ... |
| sprint sidecars | ... | ... |
| project hooks | ... | ... |
| statusline path | ... | ... |
| hook commands | ... | ... |

### Cleanup Actions
[For each warning, explain what the fix will do: delete, move, or update]
```
</output>

<gate>
## Completion Criteria
- [ ] All legacy artifacts reviewed with user
- [ ] User understands what each cleanup action will do
- [ ] User approved or declined each destructive cleanup
- [ ] No unapproved file deletions performed
</gate>

<switch tool="AskUserQuestion">
  <case value="fix" next="LOOP">
    Fix — Run `pf validate --fix --category legacy` to clean up (requires gate approval)
  </case>
  <case value="explain" next="LOOP">
    Explain — Deep dive on a specific legacy artifact's history
  </case>
  <case value="continue" next="step-07-tools">
    Continue — Approve cleanup and proceed to Tools check
  </case>
  <case value="recheck" next="LOOP">
    Recheck — Re-run after manual cleanup
  </case>
</switch>

<next-step>
After user approves legacy cleanup, proceed to step-07-tools.md for Optional Tools verification.
</next-step>

## Failure Modes

- Deleting customized legacy files without checking for user modifications
- Not explaining that `.sh` shims still work (migration is optional optimization)
- Removing sidecar directories before confirming new location has the content

## Success Metrics

- All legacy artifacts addressed (cleaned up or acknowledged)
- User made informed decisions about each cleanup action
- Gate approval recorded
