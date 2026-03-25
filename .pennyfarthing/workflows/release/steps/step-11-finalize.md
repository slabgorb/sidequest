# Step 11: Finalize Release

<purpose>
Create a GitHub release with release notes, verify everything is consistent, and produce a final summary.
</purpose>

<instructions>
1. Create GitHub release from tag
2. Verify final state
3. Print release summary
</instructions>

<output>
Release summary with links to GitHub release and git tag.
</output>

## Execution

### 11.1 Create GitHub Release

```bash
TAG="v{new_version}"

PRERELEASE_FLAG=""
if [[ "$IS_PRERELEASE" == "true" ]]; then
    PRERELEASE_FLAG="--prerelease"
fi

gh release create "$TAG" \
    --title "v{new_version}" \
    --notes "See [CHANGELOG.md](CHANGELOG.md) for details." \
    $PRERELEASE_FLAG \
    || echo "WARNING: GitHub release creation failed (may already exist)"
```

### 11.2 Final Verification

```bash
echo "=== Final State ==="
echo ""
echo "Git:"
echo "  Branch: $(git branch --show-current)"
echo "  Tag: $(git tag -l 'v{new_version}')"
echo "  VERSION: $(cat VERSION)"
echo ""
echo "pf CLI:"
pf --version
echo ""
echo "GitHub:"
gh release view "v{new_version}" --json url --jq '.url' 2>/dev/null || echo "  No GitHub release"
```

### 11.3 Summary

**For stable release:**

```
╔════════════════════════════════════════════╗
║       Release {new_version} Complete             ║
╠════════════════════════════════════════════╣
║                                            ║
║  Tag:     v{new_version}                         ║
║  GitHub:  (release URL)                    ║
║                                            ║
║  Branches pushed: develop, main            ║
║  Current branch:  develop                  ║
║                                            ║
║  Update consumers:                         ║
║    pipx install --force pennyfarthing-dist ║
║    pf init .                               ║
║                                            ║
╚════════════════════════════════════════════╝
```

**For prerelease:**

```
╔════════════════════════════════════════════════╗
║  Prerelease {new_version} Complete                  ║
╠════════════════════════════════════════════════╣
║                                                ║
║  Tag:       v{new_version}                          ║
║  GitHub:    (prerelease URL)                   ║
║                                                ║
║  Branch pushed: develop (main unchanged)       ║
║  Current branch: develop                       ║
║                                                ║
║  Update consumers:                             ║
║    pipx install --force pennyfarthing-dist    ║
║    pf init .                                   ║
║                                                ║
╚════════════════════════════════════════════════╝
```

---

Release workflow complete. All systems updated.
