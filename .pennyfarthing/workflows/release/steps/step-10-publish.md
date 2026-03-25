# Step 10: Reinstall pf CLI

<purpose>
Reinstall the pf CLI from the updated source so the new version is live locally.
Consumer projects will pick up the new version on their next `pf init`.
</purpose>

<instructions>
1. Reinstall pf CLI via pipx from pennyfarthing-dist/
2. Verify the installed version matches the release
3. Run pf init on the current project to update local files
</instructions>

<output>
Installed pf version and init confirmation.
</output>

## Execution

### 10.1 Reinstall pf CLI

```bash
cd {project_root}
pipx install --force -e pennyfarthing-dist/
```

### 10.2 Verify Version

```bash
pf --version
# Should show: pf, version {new_version}
```

### 10.3 Update Current Project

```bash
pf init .
```

---


<switch tool="AskUserQuestion">
  <case value="continue-to-github-release" next="step-11-finalize">
    Continue to GitHub release
  </case>
  <case value="skip-github-release" next="step-11-finalize">
    Skip GitHub release
  </case>
</switch>
