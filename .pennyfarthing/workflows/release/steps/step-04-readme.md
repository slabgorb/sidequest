# Step 4: Update README

<purpose>
Review and update README.md to reflect the current state of the project. The version badge was already bumped in step 2 — this step covers content: feature counts, new capabilities, install instructions, and any sections that have drifted from reality.
</purpose>

<instructions>
1. Verify the version badge was updated in step 2
2. Audit feature counts (agents, workflows, commands, skills)
3. Check for new capabilities that should be documented
4. Verify install instructions and quick start are current
5. Update any outdated sections
6. Show diff for review
</instructions>

<output>
Updated README.md content reflecting the current release, with diff shown for review.
</output>

## Execution

### 4.1 Verify Version Badge

```bash
grep "^\*\*v" README.md | head -1
# Should show: **v{new_version}**
```

### 4.2 Audit Feature Counts

The README lists specific counts. Verify they're current:

```bash
echo "=== Actual Counts ==="

# Agent count
echo -n "Agents: "
ls pennyfarthing-dist/agents/*.yaml 2>/dev/null | wc -l | tr -d ' '

# Workflow count
echo -n "Workflows: "
ls pennyfarthing-dist/workflows/*.yaml 2>/dev/null | wc -l | tr -d ' '

# Command count
echo -n "Commands: "
ls pennyfarthing-dist/commands/*.md 2>/dev/null | wc -l | tr -d ' '

# Skill count
echo -n "Skills: "
ls -d pennyfarthing-dist/skills/*/ 2>/dev/null | wc -l | tr -d ' '

# Theme count
echo -n "Themes: "
ls -d pennyfarthing-dist/personas/themes/*/ 2>/dev/null | wc -l | tr -d ' '
```

Compare with what README claims and update if different:
- **X Coordinated Agents**
- **Y BikeLane Workflows**
- **Z Slash Commands**
- **W Skills**

### 4.3 Check for New Capabilities

Review the changelog entries from step 3. Any new features that warrant README mention?

Things to look for:
- New agents or workflows added
- New slash commands
- New integrations
- Architecture changes users should know about
- Changed install requirements

### 4.4 Verify Quick Start

```bash
echo "=== Quick Start Section ==="
# Check that install commands still work
grep -A 20 "## Quick Start" README.md
```

Ensure:
- Install command is correct (`pipx install pennyfarthing-scripts`)
- Example commands are valid

### 4.5 Show Diff

```bash
git diff README.md
```

If no changes were needed beyond the version badge, that's fine — just confirm and continue.

---


<switch tool="AskUserQuestion">
  <case value="continue-to-claudemd-update" next="step-05-claude-md">
    Continue to CLAUDE.md update
  </case>
  <case value="revise-readme-content" next="LOOP">
    Revise README content
  </case>
  <case value="skip" next="step-05-claude-md">
    Skip (no README changes needed beyond version badge)
  </case>
</switch>
