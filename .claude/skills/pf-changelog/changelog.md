---
name: changelog
description: Maintain changelogs following Keep a Changelog format. Use when creating release notes, parsing conventional commits for changelog entries, auto-generating changelog sections from git history, or preparing CHANGELOG.md for releases.
---

<run>
Commands for changelog maintenance:
- Parse conventional commits for changelog entries
- Auto-generate changelog sections from git history
- Version bump decisions using semantic versioning
- Create release notes and CHANGELOG.md updates
</run>

<output>
Changelog entries in Keep a Changelog format:
- Added (new features from `feat:` commits)
- Changed (changes from `perf:` commits, breaking changes)
- Deprecated (features marked for removal)
- Removed (removed features)
- Fixed (bug fixes from `fix:` commits)
- Security (vulnerability fixes)
</output>

# Changelog Management Skill

## When to Use This Skill

- Creating release notes
- Parsing conventional commits for changelog entries
- Auto-generating changelog sections from git history
- Managing semantic versioning changes
- Preparing CHANGELOG.md for releases
- Documenting breaking changes, features, and fixes

## Overview

This skill guides changelog management using the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format combined with [Conventional Commits](https://www.conventionalcommits.org/). This approach ensures consistency, enables automation, and provides clear communication about changes.

**Project Reference:** Pennyfarthing uses Keep a Changelog format in `/CHANGELOG.md` with semantic versioning.

## Keep a Changelog Format Reference

The standard structure is:

```markdown
# Changelog

All notable changes to [Project] are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

*No unreleased changes*

---

## [1.0.0] - 2024-01-15

### Added
- New user-facing features

### Changed
- Changes in existing functionality

### Deprecated
- Features marked for removal

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security vulnerability fixes

---

## [0.9.0] - 2024-01-10
...
```

### Guidelines

1. **One version per section** - Each release gets its own `## [version] - date` heading
2. **Semantic versioning** - Follow MAJOR.MINOR.PATCH (e.g., 1.5.3)
3. **ISO 8601 dates** - Format as YYYY-MM-DD
4. **Categorized entries** - Group changes by type (Added, Changed, Fixed, etc.)
5. **Unreleased section** - Always maintain an `[Unreleased]` section at the top for staging changes
6. **End-user focus** - Write for developers using your project, not your own team

### Section Hierarchy

- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Features soon to be removed (provide migration path)
- **Removed** - Removed features (finalize deprecations)
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes with patches

## Conventional Commits Parsing

[Conventional Commits](https://www.conventionalcommits.org/) structure commits to enable automatic changelog generation:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types and Changelog Mapping

| Commit Type | Changelog Section | Example |
|-------------|-------------------|---------|
| `feat:` | Added | `feat: add user authentication` |
| `fix:` | Fixed | `fix: handle null pointer in parser` |
| `perf:` | Changed | `perf: optimize database queries` |
| `docs:` | (skip) | `docs: update README` |
| `style:` | (skip) | `style: format code` |
| `refactor:` | (skip) | `refactor: simplify module` |
| `test:` | (skip) | `test: add unit tests` |
| `chore:` | (skip) | `chore: update dependencies` |
| `ci:` | (skip) | `ci: update GitHub Actions` |

### Breaking Changes

Mark breaking changes with `!` or `BREAKING CHANGE:` footer:

```bash
# Using ! suffix
feat!: redesign authentication API

# Using footer
feat: change password hashing algorithm

BREAKING CHANGE: passwords now require bcrypt hashing
```

These go into the **Changed** or **Removed** section, not Added.

## Auto-Generation from Git Commits

### Step 1: Get Commits Since Last Tag

```bash
# Find the last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

# Get commits since that tag
if [ -z "$LAST_TAG" ]; then
  git log --format="%H %s" | head -50
else
  git log "${LAST_TAG}..HEAD" --format="%H %s"
fi
```

### Step 2: Parse Conventional Commits

```bash
# Extract type and description from commits
git log "${LAST_TAG}..HEAD" --format="%s" | while read line; do
  TYPE=$(echo "$line" | cut -d: -f1)
  DESC=$(echo "$line" | cut -d: -f2- | sed 's/^ //')
  echo "$TYPE: $DESC"
done
```

### Step 3: Group by Category

```bash
# Group features
git log "${LAST_TAG}..HEAD" --format="%s" | grep "^feat" | sed 's/^feat: /- /'

# Group fixes
git log "${LAST_TAG}..HEAD" --format="%s" | grep "^fix" | sed 's/^fix: /- /'

# Group breaking changes
git log "${LAST_TAG}..HEAD" --format="%B" | grep -A1 "BREAKING CHANGE:" | tail -n +2
```

## Complete Auto-Generation Script

```bash
#!/bin/bash
set -euo pipefail

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
RANGE="${LAST_TAG:+${LAST_TAG}..HEAD}"

echo "## [Unreleased]"
echo ""

# Added (feat commits)
FEATURES=$(git log ${RANGE:---all} --format="%s" | grep "^feat:" || echo "")
if [ -n "$FEATURES" ]; then
  echo "### Added"
  echo "$FEATURES" | sed 's/^feat: /- /'
  echo ""
fi

# Fixed (fix commits)
FIXES=$(git log ${RANGE:---all} --format="%s" | grep "^fix:" || echo "")
if [ -n "$FIXES" ]; then
  echo "### Fixed"
  echo "$FIXES" | sed 's/^fix: /- /'
  echo ""
fi

# Breaking changes
BREAKING=$(git log ${RANGE:---all} --format="%B" | grep -A1 "BREAKING CHANGE:" | grep "^-" || echo "")
if [ -n "$BREAKING" ]; then
  echo "### Changed"
  echo "**Breaking Changes:**"
  echo "$BREAKING"
  echo ""
fi
```

## Version Bump Patterns

### Semantic Versioning

```
MAJOR.MINOR.PATCH

- MAJOR: Incompatible API changes (breaking changes)
- MINOR: Backward-compatible functionality additions
- PATCH: Backward-compatible bug fixes
```

### Decision Tree

```
Breaking change detected?
├─ Yes → MAJOR.0.0  (or X+1.0.0 from X.0.0)
└─ No
   └─ feat: commits present?
      ├─ Yes → X.Y+1.0  (minor version bump)
      └─ No  → X.Y.Z+1  (patch version bump)
```

### Examples

```bash
# Current version: 1.5.0

# Patch release (bug fixes only)
1.5.1  # fix: memory leak in parser

# Minor release (new features, backward-compatible)
1.6.0  # feat: add config validation, feat: support ENV vars

# Major release (breaking changes)
2.0.0  # feat!: redesign CLI API, BREAKING CHANGE: remove old flags
```

## Release Workflow Example

### 1. During Development

Maintain `[Unreleased]` section in CHANGELOG.md:

```markdown
## [Unreleased]

### Added
- New dark mode theme
- User preference persistence

### Fixed
- Memory leak in event handler
- Incorrect timezone calculations
```

### 2. Prepare Release

```bash
# Determine new version (inspect commits)
LAST_VERSION="1.5.0"
COMMITS=$(git log v${LAST_VERSION}..HEAD --format="%s")
echo "$COMMITS" | grep -q "^feat:" && NEW_VERSION="1.6.0" || NEW_VERSION="1.5.1"

echo "Releasing version $NEW_VERSION"
```

### 3. Create Release Section

```bash
# Generate section from commits
NEW_DATE=$(date +%Y-%m-%d)

# Update CHANGELOG.md
sed -i '' "s/## \[Unreleased\]/## [Unreleased]\n\n*No unreleased changes*\n\n---\n\n## [$NEW_VERSION] - $NEW_DATE/" CHANGELOG.md
```

### 4. Commit and Tag

```bash
git add CHANGELOG.md VERSION
git commit -m "chore: bump to version $NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release $NEW_VERSION"
git push origin main --tags
```

## Integration with /pf-git release Command

The `/pf-git release` command in Pennyfarthing can use this skill for:

1. **Auto-detecting new commits** - Run conventional commit analysis since last tag
2. **Generating changelog sections** - Create properly formatted entries
3. **Version bumping** - Semantic versioning based on commit types
4. **Tagging** - Create annotated tags for releases

Reference in `/pf-git release` command:

```markdown
See the [Changelog Skill](/changelog) for patterns on:
- Maintaining CHANGELOG.md
- Parsing conventional commits
- Auto-generating release notes
- Version bump decisions
```

## Best Practices

1. **Commit message quality** - Enforce conventional commits in CI/CD
2. **Review before release** - Manual changelog review catches automation gaps
3. **One changelog file** - Single CHANGELOG.md in project root
4. **Link to releases** - Provide direct links to tags/release pages
5. **Backfill old changes** - If starting Keep a Changelog mid-project, document recent versions
6. **Human-friendly descriptions** - Conventional commits are machine-parseable; enhance for humans
7. **Changelog in PR reviews** - Ensure PR descriptions clarify what should be in changelog

## Tools and Automation

### Conventional Commits Linting

```bash
# Install commitlint
npm install --save-dev @commitlint/config-conventional @commitlint/cli

# Configure .commitlintrc.js
echo "module.exports = {extends: ['@commitlint/config-conventional']}" > .commitlintrc.js

# Test a message
echo "feat: add new feature" | commitlint
```

### Automatic Changelog Generation

Tools that auto-generate from commits:

- **conventional-changelog** - Node.js package
- **changie** - Go-based with template support
- **git-cliff** - Rust-based with flexible templates

Example with conventional-changelog:

```bash
npm install --save-dev conventional-changelog-cli
npx conventional-changelog -p angular -i CHANGELOG.md -s
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Generate Changelog
  run: |
    npx conventional-changelog -p angular -i CHANGELOG.md -s
    git add CHANGELOG.md
    git commit -m "docs: update CHANGELOG" || echo "No changes"
```

## Reference Documentation

- **Keep a Changelog:** https://keepachangelog.com/
- **Conventional Commits:** https://www.conventionalcommits.org/
- **Semantic Versioning:** https://semver.org/
- **conventional-changelog:** https://github.com/conventional-changelog/conventional-changelog
- **Pennyfarthing Release:** `/pf-git release` command
