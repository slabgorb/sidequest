# Step 1: Preflight Checks

<purpose>
Verify the repo is in a clean, releasable state. Compute the new version number and preview what will change. Catch problems before any files are modified.
</purpose>

<instructions>
1. Verify working directory is clean (no uncommitted changes)
2. Verify current branch is `develop`
3. Read current version from VERSION file
4. Ask user for bump type (major/minor/patch) if not already known
5. Compute new version number
6. Check git tags for conflicts (tag doesn't already exist)
7. Show summary of what will happen
</instructions>

<output>
Preflight report showing:
- Current version and new version
- Branch status
- Git tag status
- List of files that will be modified
- Ready for user to continue or abort
</output>

## Execution

### 1.1 Clean Working Directory

```bash
cd {project_root}
if [[ -n $(git status --porcelain) ]]; then
    echo "ERROR: Working directory not clean"
    git status --short
    exit 1
fi
```

### 1.2 Branch Check

```bash
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "develop" ]]; then
    echo "ERROR: Must be on develop branch (currently on $CURRENT_BRANCH)"
    exit 1
fi
```

### 1.3 Version Computation

```bash
CURRENT_VERSION=$(cat VERSION)
echo "Current version: $CURRENT_VERSION"
```

**Detect if current version is already a prerelease:**

```bash
if [[ "$CURRENT_VERSION" == *-* ]]; then
    PRERELEASE_TAG="${CURRENT_VERSION#*-}"  # e.g., "alpha.0"
    BASE_VERSION="${CURRENT_VERSION%%-*}"   # e.g., "10.4.0"
    echo "Current version is a prerelease: $CURRENT_VERSION (base: $BASE_VERSION)"
fi
```

Ask user: **What type of release?**

**If current version is stable (no prerelease suffix):**
- `patch` — bug fixes (x.y.Z)
- `minor` — new features (x.Y.0)
- `major` — breaking changes (X.0.0)
- `prepatch` — prerelease for next patch (x.y.Z-alpha.0)
- `preminor` — prerelease for next minor (x.Y.0-alpha.0)
- `premajor` — prerelease for next major (X.0.0-alpha.0)

**If current version is already a prerelease (e.g., 10.4.0-alpha.0):**
- `prerelease` — bump prerelease number (x.y.z-alpha.N+1)
- `promote` — promote to stable (x.y.z, dropping the prerelease suffix)
- `graduate-beta` — graduate to beta (x.y.z-beta.0)
- `graduate-rc` — graduate to release candidate (x.y.z-rc.0)

Compute `NEW_VERSION` from bump type.

**For prerelease bumps**, also ask: **Prerelease channel?** (default: `alpha`)
- `alpha` — early testing, unstable
- `beta` — feature-complete, testing
- `rc` — release candidate, final testing

Set `IS_PRERELEASE=true` and `PRERELEASE_CHANNEL` (alpha/beta/rc) for use in later steps.

### 1.4 Conflict Checks

```bash
# Check git tags
git tag -l "v$NEW_VERSION" | grep -q . && echo "WARNING: Tag v$NEW_VERSION already exists!"
```

### 1.5 E2E Test Gate

Run the consumer E2E test suite. These tests verify that `pf init`, Frame startup,
content preservation, and idempotency all work correctly in isolated environments.

```bash
cd {project_root}
./tests/e2e/run.sh --local
```

All scenarios must pass before proceeding with the release. If any fail, fix the
issue before continuing — these tests protect consumer projects from broken releases.

### 1.6 Preview

```
## Preflight Summary

| Check              | Status |
|--------------------|--------|
| Clean working dir  | ✓/✗    |
| On develop branch  | ✓/✗    |
| Tag not exists     | ✓/✗    |
| E2E tests pass     | ✓/✗    |

**Version:** {CURRENT_VERSION} → {NEW_VERSION}
**Release type:** {stable | prerelease (alpha/beta/rc)}
**Tag:** v{NEW_VERSION}

**Files to modify:**
- VERSION
- pennyfarthing-dist/src/pf/__init__.py
- CHANGELOG.md
{if stable: - README.md, - CLAUDE.md}

**Steps that will be skipped for prerelease:**
{if prerelease: Steps 4 (README), 5 (CLAUDE.md), 6 (Retro), 8 (Merge to main)}
```

---


<switch tool="AskUserQuestion">
  <case value="continue-to-version-bump" next="step-02-bump">
    Continue to version bump
  </case>
  <case value="abort-release" next="EXIT">
    Abort release
  </case>
</switch>
