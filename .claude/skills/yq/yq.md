---
name: yq
description: yq is a YAML processor. Use this skill when reading, modifying, or querying YAML files from the command line.
---

# yq - YAML Processor Skill

<run>
yq [expression] [file]
</run>

<output>
YAML/JSON output depending on specified format
</output>

## Overview

`yq` is a lightweight and portable command-line YAML processor. It's like `jq` but for YAML. This skill covers the mikefarah/yq version (v4+).

## Installation

```bash
# macOS
brew install yq

# Check version (should be v4+)
yq --version
```

## Basic Operations

### Read a Value

```bash
# Read a top-level key
yq '.theme' config.yaml
# Output: discworld

# Read nested value
yq '.agents.sm.character' personas.yaml
# Output: Captain Carrot Ironfoundersson

# Read with default if missing
yq '.missing // "default"' config.yaml
# Output: default
```

### Read Entire Section

```bash
# Get all properties of a key
yq '.agents.sm' personas.yaml
# Output: the entire sm object as YAML

# Output as JSON
yq -o json '.agents.sm' personas.yaml
```

### Check if Key Exists

```bash
# Returns "true" or "false"
yq '.agents.sm | has("helper")' personas.yaml

# Returns null if doesn't exist
yq '.agents.missing' personas.yaml
# Output: null
```

## Modifying YAML

### In-Place Edit

```bash
# Edit file in place
yq -i '.theme = "startrek"' config.yaml

# Add a new key
yq -i '.newkey = "value"' config.yaml

# Delete a key
yq -i 'del(.unwanted)' config.yaml
```

### Output to Stdout (Non-Destructive)

```bash
# Modify and output to stdout (file unchanged)
yq '.count = 42' config.yaml

# Pipe to new file
yq '.theme = "newtheme"' config.yaml > new-config.yaml
```

## Common Patterns

### Iterate Over Arrays

```bash
# List all items
yq '.stories[]' sprint.yaml

# Get specific field from each item
yq '.stories[].title' sprint.yaml

# Filter items
yq '.stories[] | select(.status == "in-progress")' sprint.yaml
```

### Iterate Over Object Keys

```bash
# Get all agent names
yq '.agents | keys' personas.yaml
# Output:
# - sm
# - tea
# - dev
# - reviewer

# Iterate with key-value
yq '.agents | to_entries | .[] | .key + ": " + .value.character' personas.yaml
```

### Merge Files

```bash
# Merge two YAML files (second overwrites first)
yq '. *= load("overrides.yaml")' base.yaml

# Merge specific key
yq '.agents.sm *= load("sm-overrides.yaml")' personas.yaml
```

### Extract to Environment Variables

```bash
# Export as shell variables
eval $(yq -o shell '.database' config.yaml)
# Creates: $host, $port, $name

# Specific format
yq '.theme' config.yaml | xargs -I{} echo "THEME={}"
```

## Working with Multi-Document YAML

```bash
# Select specific document (0-indexed)
yq 'select(document_index == 0)' multi.yaml

# Process all documents
yq '... | select(has("kind"))' k8s-manifests.yaml
```

## String Operations

```bash
# Uppercase
yq '.name | upcase' config.yaml

# String contains
yq '.agents | to_entries | .[] | select(.value.style | contains("honest"))' personas.yaml

# String interpolation
yq '"Theme is: " + .theme' config.yaml
```

## Conditional Logic

```bash
# If-then-else
yq 'if .count > 10 then "many" else "few" end' config.yaml

# Select with condition
yq '.stories[] | select(.points >= 5)' sprint.yaml

# Null coalescing
yq '.optional // "default"' config.yaml
```

## Output Formats

```bash
# YAML (default)
yq '.data' file.yaml

# JSON
yq -o json '.data' file.yaml

# Properties format
yq -o props '.data' file.yaml

# CSV (for arrays)
yq -o csv '.items' file.yaml
```

## Common Use Cases in Pennyfarthing

### Read Persona Config

```bash
# Get current theme
yq '.theme' .claude/persona-config.yaml

# Get agent persona
THEME=$(yq '.theme' .claude/persona-config.yaml)
yq ".agents.sm" personas/themes/${THEME}.yaml
```

### Query Sprint Data

```bash
# Get current sprint stories
yq '.stories[] | select(.status == "todo")' sprint/current-sprint.yaml

# Count stories by status
yq '[.stories[].status] | group_by(.) | map({(.[0]): length}) | add' sprint/current-sprint.yaml
```

### Update Session Files

```bash
# Update status in YAML frontmatter (if using YAML)
yq -i '.status = "in-progress"' .session/current_work.yaml
```

## Quick Reference

| Action | Command |
|--------|---------|
| Read value | `yq '.key' file.yaml` |
| Read nested | `yq '.parent.child' file.yaml` |
| Set value | `yq -i '.key = "value"' file.yaml` |
| Delete key | `yq -i 'del(.key)' file.yaml` |
| Array length | `yq '.array | length' file.yaml` |
| Filter array | `yq '.array[] \| select(.field == "value")' file.yaml` |
| Output JSON | `yq -o json '.' file.yaml` |
| Merge files | `yq '. *= load("other.yaml")' base.yaml` |
| Default value | `yq '.key // "default"' file.yaml` |

## Troubleshooting

### "null" Output

The key doesn't exist. Use `// "default"` for fallback:
```bash
yq '.missing // "not found"' file.yaml
```

### Quotes in Output

yq preserves YAML formatting. Use `-r` (raw) for unquoted strings:
```bash
yq -r '.theme' config.yaml
```

### Boolean as String

YAML booleans (`true`/`false`) are parsed as booleans. Compare accordingly:
```bash
# CORRECT
yq '.enabled == true' config.yaml

# WRONG (comparing to string)
yq '.enabled == "true"' config.yaml
```

## Reference

- **Official Docs:** https://mikefarah.gitbook.io/yq/
- **GitHub:** https://github.com/mikefarah/yq
