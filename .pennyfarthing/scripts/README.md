# Pennyfarthing Scripts

Shell scripts bundled with the `pf` plugin. They live at the plugin root
(`${CLAUDE_PLUGIN_ROOT}/scripts/`) and are resolved by the runtime via
`pf.common.config.get_dist_root()` → `<root>/scripts/...`. Invoke scripts with
their full category path to avoid ambiguity.

## Directory Structure

```
scripts/
├── core/         # Essential scripts (agent-session.sh)
├── workflow/     # Workflow mechanics (finish-story.sh, check.sh)
├── sprint/       # Sprint YAML operations (largely superseded by `pf sprint`)
├── story/        # Story operations (create-story.sh)
├── jira/         # Jira integration (jira-claim-story.sh)
├── git/          # Git operations (deprecated shims → `pf git`)
├── theme/        # Theme operations (list-themes.sh)
├── health/       # Health checks
├── maintenance/  # Maintenance utilities
├── portraits/    # Portrait generation (requires GPU setup)
├── test/         # Test infrastructure (test-setup.sh)
├── tests/        # Script tests
├── lib/          # Shared bash libraries (common.sh, logging.sh)
├── misc/         # Uncategorized utilities
├── hooks/        # Claude Code / git hook scripts (registered by Plan 4's hooks.json)
└── utils/        # Symlinks to canonical copies elsewhere in the tree
```

## Dev-only meta scripts

A handful of scripts at the top level are for Pennyfarthing framework
development and CI only (not part of a user's workflow):

| Script | Purpose |
|--------|---------|
| `handoff-cli.sh` | Test the agent handoff flow |
| `migrate-assets-to-slug.sh` | One-time asset migration |
| `resize-portraits.sh` | Resize portrait images |
| `generate-skill-docs.sh` | Regenerate skill documentation |

## Library usage

Shared libraries in `lib/` are sourced by other scripts:

```bash
SCRIPT_DIR="$(dirname "$0")"
source "$SCRIPT_DIR/../lib/common.sh"
source "$SCRIPT_DIR/../lib/logging.sh"
```

## Adding a new script

1. Pick the appropriate category subdirectory.
2. Add the script there and `chmod +x` it.
3. Update any skill/command markdown that references it.
