# Step 3: Update CHANGELOG

<purpose>
Generate changelog entries from conventional commits since the last release tag. Uses the `/changelog` skill patterns to auto-generate entries, then presents them for human review and editing before they're committed.
</purpose>

<instructions>
1. Find the last release tag
2. Parse conventional commits since that tag
3. Generate Keep a Changelog entries grouped by category
4. Move [Unreleased] content into the new version section
5. Present the draft for review and editing
</instructions>

<output>
Draft CHANGELOG.md section for the new version, ready for user review.
</output>

## Skill Reference

This step follows the `/pf-changelog` skill patterns. See `pennyfarthing-dist/skills/changelog/SKILL.md` for full reference on:
- Keep a Changelog format
- Conventional commit parsing
- Version bump decisions

## Execution

### 3.1 Find Last Tag

```bash
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
echo "Last tag: ${LAST_TAG:-none}"
```

### 3.2 Parse Commits Since Last Release

```bash
RANGE="${LAST_TAG:+${LAST_TAG}..HEAD}"

echo "=== Commits since $LAST_TAG ==="
git log ${RANGE:---all} --format="%s" | head -50
```

### 3.3 Generate Changelog Entries

Group by conventional commit type:

```bash
# Added (feat: commits)
git log ${RANGE:---all} --format="%s" | grep "^feat" | sed 's/^feat[^:]*: /- /'

# Fixed (fix: commits)
git log ${RANGE:---all} --format="%s" | grep "^fix" | sed 's/^fix[^:]*: /- /'

# Changed (perf:, refactor: with breaking changes)
git log ${RANGE:---all} --format="%s" | grep "^perf\|^refactor" | sed 's/^[^:]*: /- /'
```

### 3.4 Draft the New Version Section

Build the new section following Keep a Changelog format:

```markdown
## [{new_version}] - {date}

### Added
- {feat commits, enhanced with human-friendly descriptions}
- {include Jira IDs where available, e.g., (<PROJECT-KEY>)}

### Changed
- {perf/refactor commits that changed behavior}

### Fixed
- {fix commits}
```

**Guidelines:**
- Combine related commits into single entries
- Write for end-users, not the development team
- Include Jira story IDs in parentheses where relevant
- Drop `chore:`, `docs:`, `style:`, `test:`, `ci:` commits (internal only)
- Flag any `BREAKING CHANGE:` commits prominently

### 3.5 Update CHANGELOG.md

Replace `[Unreleased]` placeholder content with the draft, and add a fresh empty `[Unreleased]` section above it:

```markdown
## [Unreleased]

*No unreleased changes*

---

## [{new_version}] - {date}

### Added
...
```

Then regenerate comparison links automatically:

```bash
pennyfarthing-dist/scripts/git/changelog-links.sh --fix
```

This parses version headers and rebuilds all comparison links at the bottom of CHANGELOG.md.

### 3.6 Show Draft for Review

```bash
echo "=== CHANGELOG.md Preview ==="
head -60 CHANGELOG.md
```

**Review the changelog entries.** Are they accurate? Human-friendly? Missing anything?

---

<!-- GATE -->


<switch tool="AskUserQuestion">
  <case value="continue-to-readme-update" next="step-04-readme">
    Continue to README update
  </case>
  <case value="revise-changelog-entries" next="LOOP">
    Revise changelog entries
  </case>
  <case value="abort-release" next="EXIT">
    Abort release
  </case>
</switch>
