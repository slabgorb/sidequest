# Step 8: Merge to Main

<purpose>
Merge develop into main and create the annotated release tag. This prepares everything for push — still local, still reversible.

**For prerelease:** This step is SKIPPED. Alpha/beta/rc releases stay on develop and are tagged there. Main only receives stable releases.
</purpose>

<instructions>
**If prerelease (`IS_PRERELEASE=true`):**
1. Stay on develop (do NOT checkout main)
2. Create annotated tag on develop with prerelease flag
3. Show tag info
4. Auto-continue to push step

**If stable release:**
1. Checkout main and pull latest
2. Merge develop into main
3. Create annotated tag
4. Show the merge result and tag info
</instructions>

<output>
Merge summary and tag details. Everything is local — nothing has been pushed yet.
</output>

## Execution

### 8.0 Prerelease Check

```bash
if [[ "$IS_PRERELEASE" == "true" ]]; then
    echo "=== Prerelease — Skipping Merge to Main ==="
    echo "Prerelease versions stay on develop. Main only receives stable releases."
    echo ""
fi
```

**If prerelease, skip to 8.3 (tag on develop).**

### 8.1 Update Main (stable only)

```bash
git checkout main
git pull origin main --ff-only || {
    echo "WARNING: Could not fast-forward main. Attempting merge..."
    git pull origin main --no-rebase
}
```

### 8.2 Merge Develop (stable only)

```bash
git merge develop -m "Merge develop into main for release {new_version}"
```

### 8.3 Create Tag

```bash
TAG="v{new_version}"
git tag -a "$TAG" -m "Release {new_version}"
echo "Created tag: $TAG"
```

### 8.4 Verify

```bash
echo "=== Release State ==="
echo "Branch: $(git branch --show-current)"
echo "Tag: $(git tag -l 'v{new_version}')"
echo "HEAD: $(git log --oneline -1)"
echo ""
if [[ "$IS_PRERELEASE" != "true" ]]; then
    echo "=== Branches Ahead of Remote ==="
    echo "main:"
    git log --oneline origin/main..main
    echo "---"
fi
echo "develop:"
git log --oneline origin/develop..develop
```

Everything is local. The next step pushes to the remote — that's the point of no return for git.

---


<switch tool="AskUserQuestion">
  <case value="continue-to-push" next="step-09-push">
    Continue to push
  </case>
  <case value="abort" next="EXIT">
    Abort (delete tag{if stable: , reset main})
  </case>
</switch>
