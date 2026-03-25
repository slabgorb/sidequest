# Step 9: Push Branches & Tag

<purpose>
Push develop, main, and the release tag to the remote. This is the point of no return for git — once pushed, the tag and commits are public.
</purpose>

<instructions>
1. Push develop branch
2. Push main branch
3. Push tags
4. Verify remote state matches local
5. Return to develop branch
</instructions>

<output>
Push results for each operation. Verification that remote matches local.
</output>

## Point of No Return

After this step, the version tag and commits are public. Reverting requires force-push or a new tag.

**Make sure everything looks correct before continuing.**

## Execution

### 9.1 Push Develop

```bash
echo "Pushing develop..."
git push origin develop
```

### 9.2 Push Main (stable only)

```bash
if [[ "$IS_PRERELEASE" != "true" ]]; then
    echo "Pushing main..."
    git push origin main
else
    echo "Skipping main push (prerelease stays on develop only)"
fi
```

### 9.3 Push Tags

```bash
echo "Pushing tags..."
git push origin --tags
```

### 9.4 Return to Develop

```bash
git checkout develop
```

### 9.5 Verify Remote

```bash
echo "=== Remote Verification ==="
echo "Remote tag:"
git ls-remote --tags origin | grep "v{new_version}"
echo ""
echo "Remote develop HEAD:"
git log --oneline origin/develop -1
if [[ "$IS_PRERELEASE" != "true" ]]; then
    echo ""
    echo "Remote main HEAD:"
    git log --oneline origin/main -1
fi
```

---

<!-- GATE -->


<switch tool="AskUserQuestion">
  <case value="continue-to-github-release" next="step-10-publish">
    Continue to GitHub release
  </case>
  <case value="skip" next="step-10-publish">
    Skip (git is already pushed)
  </case>
</switch>
