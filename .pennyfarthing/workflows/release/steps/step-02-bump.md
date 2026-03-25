# Step 2: Bump Version

<purpose>
Update all version files (VERSION, Python pf CLI, README, CHANGELOG) and show the full diff for review before committing anything.
</purpose>

<instructions>
1. Write new version to VERSION file
2. Update Python pf CLI version (`pennyfarthing-dist/src/pf/__init__.py`)
3. Update README.md version badge
4. Update CHANGELOG.md (version links and header)
5. Show complete diff of all changes for review
</instructions>

<output>
Full git diff showing every version change. User reviews before approving the commit step.
</output>

## Execution

### 2.1 Update VERSION File

```bash
echo "{new_version}" > VERSION
```

### 2.2 Update Python pf CLI Version

```bash
# Update __version__ in pf/__init__.py (source of truth for PyPI package)
sed -i '' -E 's/__version__ = "[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?"/__version__ = "{new_version}"/' pennyfarthing-dist/src/pf/__init__.py
echo "Updated pennyfarthing-dist/src/pf/__init__.py"
```

### 2.3 Update README.md

**Skip for prerelease** — README should always reflect the latest stable version.

```bash
if [[ "$IS_PRERELEASE" != "true" ]]; then
    sed -i '' 's/\*\*v{current_version}\*\*/\*\*v{new_version}\*\*/' README.md
fi
```

### 2.4 Update CHANGELOG.md

```bash
TODAY=$(date +%Y-%m-%d)
# Update [Unreleased] link, add new version header
# See deploy.sh for full sed commands
```

### 2.5 Show Diff for Review

```bash
echo "=== Version Bump Diff ==="
git diff
echo ""
echo "=== Files Changed ==="
git diff --stat
```

**Review the diff carefully.** Every version file should show `{current_version}` → `{new_version}`.

| File | Expected Change |
|------|----------------|
| `VERSION` | `{new_version}` |
| `pennyfarthing-dist/src/pf/__init__.py` | `__version__ = "{new_version}"` |
| `README.md` | Badge updated (stable only) |
| `CHANGELOG.md` | New version header |

**For prerelease:** README.md should NOT appear in the diff.

---

<!-- GATE -->


<switch tool="AskUserQuestion">
  <case value="continue-to-commit" next="step-03-changelog">
    Continue to commit
  </case>
  <case value="revise-a-file-before-committing" next="LOOP">
    Revise a file before committing
  </case>
  <case value="abort-release" next="EXIT">
    Abort release (revert all changes with `git checkout .`)
  </case>
</switch>
