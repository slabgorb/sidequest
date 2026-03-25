---
name: 'step-01-parse-epic-files'
description: 'Parse epic files and extract all work items for sprint status tracking'

# Path Definitions
workflow_path: '{project_root}/.pennyfarthing/workflows/sprint-planning'

# File References
thisStepFile: './step-01-parse-epic-files.md'
nextStepFile: './step-02-build-sprint-status.md'
---

<purpose>
Parse epic files and extract all work items for sprint status tracking. Build complete inventory of all epics and stories from all epic files.
</purpose>

<instructions>
1. Look for all files matching `{epics_pattern}` in `{epics_location}` (could be a single `epics.md` file or multiple `epic-1.md`, `epic-2.md` files)
2. For each epic file found, extract epic numbers from headers like `## Epic 1:` or `## Epic 2:` and story IDs and titles from patterns like `### Story 1.1: User Authentication`
3. Convert story format from `Epic.Story: Title` to kebab-case key using these conversion rules: Replace period with dash for the ID (1-1), convert title to kebab-case (user-authentication), and final key is `1-1-user-authentication`
4. Use flexible document discovery: Search for whole document first (epics.md, bmm-epics.md, *epic*.md), check for sharded version (epics/index.md), read index.md to understand structure, read all epic section files (epic-1.md, epic-2.md, etc.), and process all epics and stories from combined content. If both exist, use the whole document.
</instructions>

<output>
Complete inventory of all epics and stories from all epic files, with proper kebab-case keys and structured data ready for sprint status building.
</output>

# Step 1: Parse Epic Files and Extract All Work Items

## Goal

Parse epic files and extract all work items for sprint status tracking.

## Actions

1. Look for all files matching `{epics_pattern}` in `{epics_location}`
   - Could be a single `epics.md` file or multiple `epic-1.md`, `epic-2.md` files

2. For each epic file found, extract:
   - Epic numbers from headers like `## Epic 1:` or `## Epic 2:`
   - Story IDs and titles from patterns like `### Story 1.1: User Authentication`
   - Convert story format from `Epic.Story: Title` to kebab-case key: `epic-story-title`

## Story ID Conversion Rules

- Original: `### Story 1.1: User Authentication`
- Replace period with dash: `1-1`
- Convert title to kebab-case: `user-authentication`
- Final key: `1-1-user-authentication`

## Output

Build complete inventory of all epics and stories from all epic files.

## Document Discovery

**Strategy**: Sprint planning needs ALL epics and stories to build complete status tracking.

**Epic Discovery Process:**

1. **Search for whole document first** - Look for `epics.md`, `bmm-epics.md`, or any `*epic*.md` file
2. **Check for sharded version** - If whole document not found, look for `epics/index.md`
3. **If sharded version found**:
   - Read `index.md` to understand the document structure
   - Read ALL epic section files listed in the index (e.g., `epic-1.md`, `epic-2.md`, etc.)
   - Process all epics and their stories from the combined content
4. **Priority**: If both whole and sharded versions exist, use the whole document

**Fuzzy matching**: Be flexible with document names - users may use variations like `epics.md`, `bmm-epics.md`, `user-stories.md`, etc.
