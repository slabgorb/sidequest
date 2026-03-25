# Step 7: Commit Version Bump

<purpose>
Stage all version-bumped files, create a release branch, commit, merge to develop, and verify every file was included. This is where the old deploy.sh silently failed — we verify explicitly.
</purpose>

<instructions>
1. Create release branch from develop
2. Stage all version files explicitly (no || true)
3. Verify staged files match expected list
4. Commit with conventional message
5. Merge release branch back to develop
6. Clean up release branch
7. Show verification: committed files vs expected files
</instructions>

<output>
Commit verification showing exactly which files were committed and confirming all expected files are present.
</output>

## Execution

### 7.1 Create Release Branch

```bash
RELEASE_BRANCH="release/{new_version}"
git checkout -b "$RELEASE_BRANCH"
```

### 7.2 Stage Files Explicitly

```bash
# Root files (always staged)
git add VERSION CHANGELOG.md pennyfarthing-dist/src/pf/__init__.py

# Stable-only files (skip for prerelease)
if [[ "$IS_PRERELEASE" != "true" ]]; then
    git add README.md CLAUDE.md
fi
```

### 7.3 Verify Staging

**CRITICAL: This is the check that was missing in deploy.sh.**

```bash
echo "=== Staged Files ==="
git diff --cached --name-only

echo ""
echo "=== Verification ==="
# Check root files are staged (prerelease skips README.md and CLAUDE.md)
ROOT_FILES="VERSION CHANGELOG.md pennyfarthing-dist/src/pf/__init__.py"
if [[ "$IS_PRERELEASE" != "true" ]]; then
    ROOT_FILES="$ROOT_FILES README.md CLAUDE.md"
fi
for f in $ROOT_FILES; do
    if git diff --cached --name-only | grep -q "^$f$"; then
        echo "  ✓ $f"
    else
        echo "  ✗ $f (MISSING from staging!)"
    fi
done
```

If any file is missing, **stop and investigate** before committing.

### 7.4 Commit

```bash
git commit -m "chore: bump version to {new_version}"
```

### 7.5 Merge to Develop

```bash
git checkout develop
git merge "$RELEASE_BRANCH" --no-edit
git branch -d "$RELEASE_BRANCH"
```

### 7.6 Post-Commit Verification

```bash
echo "=== Post-Commit Check ==="
echo "VERSION file: $(cat VERSION)"
echo "pf/__init__.py: $(grep '__version__' pennyfarthing-dist/src/pf/__init__.py)"
```

All should read `{new_version}`. If any don't match, **abort before pushing.**

---

<!-- GATE -->


<switch tool="AskUserQuestion">
  <case value="continue-to-merge-to-main" next="step-08-merge">
    Continue to merge to main
  </case>
  <case value="revise" next="LOOP">
    Revise (amend commit or fix an issue)
  </case>
  <case value="abort-release" next="EXIT">
    Abort release (reset develop to before the merge)
  </case>
</switch>
