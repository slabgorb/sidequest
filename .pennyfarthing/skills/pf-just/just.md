---
name: just
description: |
  Run just recipes for project tasks. This skill should be used when starting dev servers,
  running tests, managing Frame GUI, generating portraits, or writing new justfile recipes.
args: "[recipe] [args...]"
---

# /pf-just - Project Task Runner

<run>
Main commands:
- `just --list` - List all available recipes
- `just <recipe>` - Run a specific recipe (e.g., `just build`, `just test`, `just gui`)
</run>

<output>
- `just --list` outputs a list of available recipes with their descriptions
- Individual recipe commands output their execution results (build logs, test results, etc.) depending on the recipe
</output>

`just` is a command runner for project tasks. All commands run from the **project root**.

## Commands

### `/pf-just` or `/pf-just --list`

List all available recipes.

**Run:**
```bash
just --list
```

**Output:** Recipe names with descriptions.

---

### `/pf-just build`

Build all packages in the monorepo.

**Run:**
```bash
just build
```

**What it does:** Runs `pnpm run build` to compile TypeScript across all packages.

---

### `/pf-just test`

Run tests for all packages.

**Run:**
```bash
just test
```

**What it does:** Runs `pnpm test` which executes Node.js native test runner across the monorepo.

---

### `/pf-just test-gui`

Run tests for the GUI package only.

**Run:**
```bash
just test-gui
```

**What it does:** Runs `npm test` in `packages/cyclist/`.

---

### `/pf-just test-gui-watch`

Run GUI tests in watch mode for TDD workflow.

**Run:**
```bash
just test-gui-watch
```

**What it does:** Runs Vitest in watch mode, re-running tests on file changes.

---

### `/pf-just install`

Install dependencies for all packages.

**Run:**
```bash
just install
```

**What it does:** Runs `pnpm install` to install dependencies across the monorepo.

---

## GUI Commands

The `gui` recipe is the main entry point for Frame GUI operations.

### `/pf-just gui` (default)

Launch Frame GUI in web dev mode with hot reload.

**Run:**
```bash
just gui
```

**What it does:** Starts the web server with Vite for browser-based development.

---

### `/pf-just gui here`

Launch Frame GUI for the current directory.

**Run:**
```bash
just gui here
```

**What it does:** Starts the web server with `pwd` as the project directory.

---

### `/pf-just gui server`

Start Frame GUI web server only (no browser).

**Run:**
```bash
just gui server
```

**What it does:** Starts the backend server for headless or remote access.

---

### `/pf-just gui verbose`

Enable debug logging for troubleshooting.

**Run:**
```bash
just gui verbose
```

**Combine flags:**
```bash
just gui here verbose
```

---

### `/pf-just gui dir=<path>`

Launch Frame GUI for a specific project directory.

**Run:**
```bash
just gui dir=/path/to/project
```

**Arguments:**
| Arg | Required | Description |
|-----|----------|-------------|
| `dir=` | Yes | Absolute path to project directory |

---

### `/pf-just gui setup`

First-time setup for Frame GUI development.

**Run:**
```bash
just gui setup
```

**What it does:**
1. Cleans stale artifacts (`rm -rf packages/cyclist/dist/`)
2. Installs dependencies (`pnpm install`)
3. Builds TypeScript (`pnpm run build`)

---

### `/pf-just gui doctor`

Diagnose Frame GUI setup issues.

**Run:**
```bash
just gui doctor
just gui doctor --fix
```

**Arguments:**
| Arg | Required | Description |
|-----|----------|-------------|
| `--fix` | No | Auto-repair detected issues |

**What it does:** Checks for common setup problems and optionally fixes them.

---

### `/pf-just gui build`

Build Frame GUI TypeScript only.

**Run:**
```bash
just gui build
```

**What it does:** Compiles TypeScript in `packages/cyclist/`. Builds workspace dependencies first if missing.

---

### `/pf-just gui clean`

Remove Frame GUI build artifacts.

**Run:**
```bash
just gui clean
```

**What it does:** Removes `packages/cyclist/dist/` directory.

---

## Portrait Commands

Generate AI portraits for persona themes.

### `/pf-just portraits <theme>`

Generate portraits for a specific theme.

**Run:**
```bash
just portraits arthurian-mythos
```

**Arguments:**
| Arg | Required | Description |
|-----|----------|-------------|
| `theme` | Yes | Theme name (e.g., `arthurian-mythos`, `the-expanse`) |

---

### `/pf-just portraits-all`

Generate portraits for all themes.

**Run:**
```bash
just portraits-all
```

**Warning:** This is time-intensive. Generates portraits for all 102 themes.

---

### `/pf-just portraits-preview <theme>`

Preview portraits for a theme without saving.

**Run:**
```bash
just portraits-preview arthurian-mythos
```

**Arguments:**
| Arg | Required | Description |
|-----|----------|-------------|
| `theme` | Yes | Theme name to preview |

---

## Passing Arguments to Recipes

Just recipes accept arguments directly (no `--` separator needed):

```bash
# Correct
just test-gui --filter "B-001"
just gui here verbose

# WRONG - don't use --
just test-gui -- --filter "B-001"
```

---

## Inspecting Recipes

### Show recipe definition

**Run:**
```bash
just --show <recipe>
```

**Example:**
```bash
just --show gui
# Shows the full recipe implementation
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `just` | List available recipes |
| `just build` | Build all packages |
| `just test` | Run all tests |
| `just test-gui` | Run GUI tests |
| `just test-gui-watch` | GUI tests in watch mode |
| `just install` | Install dependencies |
| `just gui` | Web dev mode (default) |
| `just gui here` | Web dev + current directory |
| `just gui server` | Web server only |
| `just gui setup` | First-time setup |
| `just gui doctor` | Diagnose issues |
| `just gui build` | Build TypeScript |
| `just gui clean` | Remove dist/ |
| `just portraits <theme>` | Generate theme portraits |
| `just portraits-all` | Generate all portraits |
| `just portraits-preview <theme>` | Preview portraits |

## Dependencies

```bash
brew install just
# or
cargo install just
```

## Reference

- **Official Docs:** https://just.systems/man/en/
