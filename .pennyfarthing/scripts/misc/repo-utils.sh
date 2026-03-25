#!/usr/bin/env zsh
# Pennyfarthing Repository Utilities
# Provides functions for multi-repo operations with backward compatibility
#
# Usage: source scripts/repo-utils.sh
#
# If .pennyfarthing/repos.yaml exists, uses that configuration.
# Otherwise, falls back to legacy $API_REPO/$UI_REPO environment variables.
#
# Core Functions:
#   load_repos_config      - Load repos.yaml or fall back to env vars
#   get_repos              - List all repo names
#   get_repos_of_type TYPE - List repos of a specific type (api, ui, adapter, etc.)
#   get_repo_path NAME     - Get path for a repo
#   get_repo_type NAME     - Get type for a repo
#   get_repo_language NAME - Get language for a repo
#   get_test_command NAME  - Get test command for a repo
#   get_test_filter_flag NAME - Get test filter flag (auto-discovers from language)
#   get_build_command NAME - Get build command for a repo
#   get_lint_command NAME  - Get lint command for a repo
#   get_dependencies NAME  - Get dependencies for a repo
#   get_build_order        - Get repos in dependency order
#   for_each_repo CMD      - Run command in each repo
#   for_each_repo_of_type TYPE CMD - Run command in repos of type
#   is_legacy_mode         - Check if using legacy API_REPO/UI_REPO

set -euo pipefail

# Determine PROJECT_ROOT if not set
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
REPOS_CONFIG="${PROJECT_ROOT}/.pennyfarthing/repos.yaml"

# Cache for parsed config (associative arrays)
declare -A _REPO_PATHS 2>/dev/null || true
declare -A _REPO_TYPES 2>/dev/null || true
declare -A _REPO_LANGUAGES 2>/dev/null || true
declare -A _REPO_TEST_CMDS 2>/dev/null || true
declare -A _REPO_TEST_FILTER_FLAGS 2>/dev/null || true
declare -A _REPO_BUILD_CMDS 2>/dev/null || true
declare -A _REPO_LINT_CMDS 2>/dev/null || true
declare -A _REPO_DEPS 2>/dev/null || true
declare -a _REPO_NAMES 2>/dev/null || true
declare -a _BUILD_ORDER 2>/dev/null || true
_LEGACY_MODE=false
_CONFIG_LOADED=false

# ============================================================================
# Configuration Loading
# ============================================================================

load_repos_config() {
    if [[ "$_CONFIG_LOADED" == "true" ]]; then
        return 0
    fi

    # Reset arrays
    _REPO_PATHS=()
    _REPO_TYPES=()
    _REPO_LANGUAGES=()
    _REPO_TEST_CMDS=()
    _REPO_TEST_FILTER_FLAGS=()
    _REPO_BUILD_CMDS=()
    _REPO_LINT_CMDS=()
    _REPO_DEPS=()
    _REPO_NAMES=()
    _BUILD_ORDER=()

    if [[ -f "$REPOS_CONFIG" ]]; then
        _parse_repos_yaml
        _apply_legacy_compat
        _LEGACY_MODE=false
    else
        _load_legacy_env
        _LEGACY_MODE=true
    fi

    _CONFIG_LOADED=true
}

# Parse repos.yaml using yq (preferred) or Python fallback
_parse_repos_yaml() {
    if command -v yq &>/dev/null; then
        _parse_with_yq
    elif command -v python3 &>/dev/null; then
        _parse_with_python
    else
        echo "ERROR: repos.yaml found but no YAML parser available (yq or python3)" >&2
        echo "Install yq: brew install yq" >&2
        exit 1
    fi
}

_parse_with_yq() {
    local repo_keys
    repo_keys=$(yq -r '.repos | keys | .[]' "$REPOS_CONFIG" 2>/dev/null || echo "")

    if [[ -z "$repo_keys" ]]; then
        echo "WARNING: No repos defined in $REPOS_CONFIG" >&2
        return
    fi

    while IFS= read -r repo; do
        [[ -z "$repo" ]] && continue
        _REPO_NAMES+=("$repo")
        _REPO_PATHS[$repo]=$(yq -r ".repos.\"$repo\".path // \"$repo\"" "$REPOS_CONFIG")
        _REPO_TYPES[$repo]=$(yq -r ".repos.\"$repo\".type // \"unknown\"" "$REPOS_CONFIG")
        _REPO_LANGUAGES[$repo]=$(yq -r ".repos.\"$repo\".language // \"unknown\"" "$REPOS_CONFIG")
        _REPO_TEST_CMDS[$repo]=$(yq -r ".repos.\"$repo\".test_command // \"\"" "$REPOS_CONFIG")
        _REPO_TEST_FILTER_FLAGS[$repo]=$(yq -r ".repos.\"$repo\".test_filter_flag // \"\"" "$REPOS_CONFIG")
        _REPO_BUILD_CMDS[$repo]=$(yq -r ".repos.\"$repo\".build_command // \"\"" "$REPOS_CONFIG")
        _REPO_LINT_CMDS[$repo]=$(yq -r ".repos.\"$repo\".lint_command // \"\"" "$REPOS_CONFIG")

        # Dependencies as comma-separated list
        local deps
        deps=$(yq -r ".repos.\"$repo\".dependencies // [] | join(\",\")" "$REPOS_CONFIG")
        _REPO_DEPS[$repo]="$deps"
    done <<< "$repo_keys"

    # Build order (explicit or default to repo order)
    local build_order
    build_order=$(yq -r '.build_order // [] | .[]' "$REPOS_CONFIG" 2>/dev/null || echo "")
    if [[ -n "$build_order" ]]; then
        while IFS= read -r repo; do
            [[ -n "$repo" ]] && _BUILD_ORDER+=("$repo")
        done <<< "$build_order"
    elif [[ ${#_REPO_NAMES[@]} -gt 0 ]]; then
        _BUILD_ORDER=("${_REPO_NAMES[@]}")
    fi
}

_parse_with_python() {
    local result
    result=$(python3 << 'PYTHON_SCRIPT'
import yaml
import json
import sys
import os

config_path = os.environ.get('REPOS_CONFIG', '.pennyfarthing/repos.yaml')
try:
    with open(config_path) as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(json.dumps({'error': str(e)}))
    sys.exit(1)

repos = config.get('repos', {})
result = {
    'repos': [],
    'build_order': config.get('build_order', list(repos.keys()))
}

for name, repo in repos.items():
    if repo is None:
        repo = {}
    result['repos'].append({
        'name': name,
        'path': repo.get('path', name),
        'type': repo.get('type', 'unknown'),
        'language': repo.get('language', 'unknown'),
        'test_command': repo.get('test_command', ''),
        'test_filter_flag': repo.get('test_filter_flag', ''),
        'build_command': repo.get('build_command', ''),
        'lint_command': repo.get('lint_command', ''),
        'dependencies': ','.join(repo.get('dependencies', []))
    })

print(json.dumps(result))
PYTHON_SCRIPT
    )

    if echo "$result" | grep -q '"error"'; then
        echo "ERROR parsing repos.yaml: $(echo "$result" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("error","unknown"))')" >&2
        exit 1
    fi

    # Parse JSON output into bash arrays
    while IFS= read -r line; do
        local name path type language test_cmd test_filter_flag build_cmd lint_cmd deps
        name=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')
        path=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["path"])')
        type=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["type"])')
        language=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["language"])')
        test_cmd=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["test_command"])')
        test_filter_flag=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["test_filter_flag"])')
        build_cmd=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["build_command"])')
        lint_cmd=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["lint_command"])')
        deps=$(echo "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin)["dependencies"])')

        _REPO_NAMES+=("$name")
        _REPO_PATHS[$name]="$path"
        _REPO_TYPES[$name]="$type"
        _REPO_LANGUAGES[$name]="$language"
        _REPO_TEST_CMDS[$name]="$test_cmd"
        _REPO_TEST_FILTER_FLAGS[$name]="$test_filter_flag"
        _REPO_BUILD_CMDS[$name]="$build_cmd"
        _REPO_LINT_CMDS[$name]="$lint_cmd"
        _REPO_DEPS[$name]="$deps"
    done < <(echo "$result" | python3 -c 'import json,sys; [print(json.dumps(r)) for r in json.load(sys.stdin)["repos"]]')

    # Build order
    while IFS= read -r repo; do
        [[ -n "$repo" ]] && _BUILD_ORDER+=("$repo")
    done < <(echo "$result" | python3 -c 'import json,sys; [print(r) for r in json.load(sys.stdin)["build_order"]]')
}

# Apply legacy_compat section - generate $API_REPO and $UI_REPO for backward compat
_apply_legacy_compat() {
    local api_repo ui_repo

    if command -v yq &>/dev/null; then
        api_repo=$(yq -r '.legacy_compat.api_repo // ""' "$REPOS_CONFIG" 2>/dev/null || echo "")
        ui_repo=$(yq -r '.legacy_compat.ui_repo // ""' "$REPOS_CONFIG" 2>/dev/null || echo "")
    elif command -v python3 &>/dev/null; then
        api_repo=$(python3 -c "import yaml; c=yaml.safe_load(open('$REPOS_CONFIG')); print(c.get('legacy_compat',{}).get('api_repo','') or '')" 2>/dev/null || echo "")
        ui_repo=$(python3 -c "import yaml; c=yaml.safe_load(open('$REPOS_CONFIG')); print(c.get('legacy_compat',{}).get('ui_repo','') or '')" 2>/dev/null || echo "")
    fi

    # Export legacy env vars if defined in repos.yaml
    if [[ -n "$api_repo" && "$api_repo" != "null" ]]; then
        export API_REPO="$api_repo"
    fi
    if [[ -n "$ui_repo" && "$ui_repo" != "null" ]]; then
        export UI_REPO="$ui_repo"
    fi
}

# Fallback to legacy environment variables
_load_legacy_env() {
    if [[ -n "${API_REPO:-}" ]]; then
        _REPO_NAMES+=("$API_REPO")
        _REPO_PATHS[$API_REPO]="$API_REPO"
        _REPO_TYPES[$API_REPO]="api"
        _REPO_LANGUAGES[$API_REPO]="go"
        _REPO_TEST_CMDS[$API_REPO]="just test"
        _REPO_BUILD_CMDS[$API_REPO]="just build"
        _REPO_LINT_CMDS[$API_REPO]="golangci-lint run"
        _REPO_DEPS[$API_REPO]=""
    fi

    if [[ -n "${UI_REPO:-}" ]]; then
        _REPO_NAMES+=("$UI_REPO")
        _REPO_PATHS[$UI_REPO]="$UI_REPO"
        _REPO_TYPES[$UI_REPO]="ui"
        _REPO_LANGUAGES[$UI_REPO]="typescript"
        _REPO_TEST_CMDS[$UI_REPO]="npm run test -- --run"
        _REPO_BUILD_CMDS[$UI_REPO]="npm run build"
        _REPO_LINT_CMDS[$UI_REPO]="npm run lint"
        _REPO_DEPS[$UI_REPO]=""
    fi

    # Handle empty array case for set -u compatibility
    if [[ ${#_REPO_NAMES[@]} -gt 0 ]]; then
        _BUILD_ORDER=("${_REPO_NAMES[@]}")
    else
        _BUILD_ORDER=()
    fi
}

# ============================================================================
# Public API Functions
# ============================================================================

# Check if using legacy mode (no repos.yaml)
is_legacy_mode() {
    load_repos_config
    [[ "$_LEGACY_MODE" == "true" ]]
}

# Get all repo names
get_repos() {
    load_repos_config
    printf '%s\n' "${_REPO_NAMES[@]}"
}

# Get number of repos
get_repo_count() {
    load_repos_config
    echo "${#_REPO_NAMES[@]}"
}

# Get repos of a specific type
get_repos_of_type() {
    local type="$1"
    load_repos_config

    for repo in "${_REPO_NAMES[@]}"; do
        if [[ "${_REPO_TYPES[$repo]:-}" == "$type" ]]; then
            echo "$repo"
        fi
    done
}

# Get path for a repo (relative to PROJECT_ROOT)
get_repo_path() {
    local name="$1"
    load_repos_config
    echo "${_REPO_PATHS[$name]:-}"
}

# Get full path for a repo
get_repo_full_path() {
    local name="$1"
    local path
    path=$(get_repo_path "$name")
    if [[ -n "$path" ]]; then
        echo "$PROJECT_ROOT/$path"
    fi
}

# Get type for a repo
get_repo_type() {
    local name="$1"
    load_repos_config
    echo "${_REPO_TYPES[$name]:-unknown}"
}

# Get language for a repo
get_repo_language() {
    local name="$1"
    load_repos_config
    echo "${_REPO_LANGUAGES[$name]:-unknown}"
}

# Get test command for a repo
get_test_command() {
    local name="$1"
    load_repos_config
    echo "${_REPO_TEST_CMDS[$name]:-}"
}

# Get test filter flag for a repo
# Falls back to language-based defaults if not specified
get_test_filter_flag() {
    local name="$1"
    load_repos_config

    local flag="${_REPO_TEST_FILTER_FLAGS[$name]:-}"

    # If specified in config, use it
    if [[ -n "$flag" ]]; then
        echo "$flag"
        return 0
    fi

    # Auto-discover based on language
    local language="${_REPO_LANGUAGES[$name]:-unknown}"
    case "$language" in
        go)
            echo "-run"
            ;;
        typescript|javascript)
            # Detect Vitest vs Jest from test command
            local test_cmd="${_REPO_TEST_CMDS[$name]:-}"
            if [[ "$test_cmd" == *"vitest"* ]] || [[ "$test_cmd" == *"npm run test"* ]]; then
                echo "-t"  # Vitest
            else
                echo "--testNamePattern"  # Jest
            fi
            ;;
        python)
            echo "-k"  # pytest
            ;;
        rust)
            echo "--"  # cargo test uses -- to pass args
            ;;
        ruby)
            echo "-n"  # minitest
            ;;
        java|kotlin)
            echo "--tests"  # Gradle
            ;;
        *)
            echo ""  # Unknown - no filter support
            ;;
    esac
}

# Get build command for a repo
get_build_command() {
    local name="$1"
    load_repos_config
    echo "${_REPO_BUILD_CMDS[$name]:-}"
}

# Get lint command for a repo
get_lint_command() {
    local name="$1"
    load_repos_config
    echo "${_REPO_LINT_CMDS[$name]:-}"
}

# Get dependencies for a repo (comma-separated)
get_dependencies() {
    local name="$1"
    load_repos_config
    echo "${_REPO_DEPS[$name]:-}"
}

# Get repos in build/dependency order
get_build_order() {
    load_repos_config
    printf '%s\n' "${_BUILD_ORDER[@]}"
}

# ============================================================================
# Iteration Functions
# ============================================================================

# Run command in each repo
# Usage: for_each_repo "git status"
for_each_repo() {
    local cmd="$1"
    load_repos_config

    for repo in "${_REPO_NAMES[@]}"; do
        local path="${_REPO_PATHS[$repo]}"
        local full_path="$PROJECT_ROOT/$path"

        if [[ -d "$full_path" ]]; then
            echo "=== $repo ($path) ==="
            (cd "$full_path" && eval "$cmd") || true
        else
            echo "SKIP: $repo (path not found: $full_path)"
        fi
    done
}

# Run command in each repo of a specific type
# Usage: for_each_repo_of_type "api" "just test"
for_each_repo_of_type() {
    local type="$1"
    local cmd="$2"
    load_repos_config

    for repo in "${_REPO_NAMES[@]}"; do
        if [[ "${_REPO_TYPES[$repo]:-}" == "$type" ]]; then
            local path="${_REPO_PATHS[$repo]}"
            local full_path="$PROJECT_ROOT/$path"

            if [[ -d "$full_path" ]]; then
                echo "=== $repo ($path) ==="
                (cd "$full_path" && eval "$cmd") || true
            fi
        fi
    done
}

# Run command in repos in build order
# Usage: for_each_repo_ordered "make build"
for_each_repo_ordered() {
    local cmd="$1"
    load_repos_config

    for repo in "${_BUILD_ORDER[@]}"; do
        local path="${_REPO_PATHS[$repo]}"
        local full_path="$PROJECT_ROOT/$path"

        if [[ -d "$full_path" ]]; then
            echo "=== $repo ($path) ==="
            (cd "$full_path" && eval "$cmd") || true
        fi
    done
}

# ============================================================================
# Test/Build Functions
# ============================================================================

# Run tests in all repos, respecting build order
run_all_tests() {
    load_repos_config

    local failed=0
    for repo in "${_BUILD_ORDER[@]}"; do
        local path="${_REPO_PATHS[$repo]}"
        local test_cmd="${_REPO_TEST_CMDS[$repo]}"
        local full_path="$PROJECT_ROOT/$path"

        if [[ -z "$test_cmd" ]]; then
            echo "SKIP: $repo (no test command)"
            continue
        fi

        if [[ ! -d "$full_path" ]]; then
            echo "SKIP: $repo (path not found)"
            continue
        fi

        echo "=== Testing $repo ==="
        if (cd "$full_path" && eval "$test_cmd"); then
            echo "PASS: $repo"
        else
            echo "FAIL: $repo"
            ((failed++)) || true
        fi
    done

    return $failed
}

# Run tests in repos of a specific type
run_tests_of_type() {
    local type="$1"
    load_repos_config

    local failed=0
    for repo in "${_BUILD_ORDER[@]}"; do
        if [[ "${_REPO_TYPES[$repo]:-}" != "$type" ]]; then
            continue
        fi

        local path="${_REPO_PATHS[$repo]}"
        local test_cmd="${_REPO_TEST_CMDS[$repo]}"
        local full_path="$PROJECT_ROOT/$path"

        if [[ -z "$test_cmd" ]]; then
            echo "SKIP: $repo (no test command)"
            continue
        fi

        if [[ ! -d "$full_path" ]]; then
            echo "SKIP: $repo (path not found)"
            continue
        fi

        echo "=== Testing $repo ==="
        if (cd "$full_path" && eval "$test_cmd"); then
            echo "PASS: $repo"
        else
            echo "FAIL: $repo"
            ((failed++)) || true
        fi
    done

    return $failed
}

# ============================================================================
# Utility Functions
# ============================================================================

# Filter repos by a list (for story-scoped operations)
# Usage: filter_repos "Pennyfarthing-api,Pennyfarthing-ui" or "all" or "api"
filter_repos() {
    local filter="$1"
    load_repos_config

    case "$filter" in
        all|both)
            get_repos
            ;;
        api|ui|adapter|service|shared|lib)
            get_repos_of_type "$filter"
            ;;
        *)
            # Treat as comma-separated list of repo names
            echo "$filter" | tr ',' '\n'
            ;;
    esac
}

# Check if a repo exists in the configuration
repo_exists() {
    local name="$1"
    load_repos_config

    for repo in "${_REPO_NAMES[@]}"; do
        if [[ "$repo" == "$name" ]]; then
            return 0
        fi
    done
    return 1
}

# Get configuration summary (for debugging)
show_config() {
    load_repos_config

    echo "=== Repo Configuration ==="
    echo "Mode: $(is_legacy_mode && echo 'Legacy (API_REPO/UI_REPO)' || echo 'repos.yaml')"
    echo "Config: $REPOS_CONFIG"
    echo "Repos: ${#_REPO_NAMES[@]}"
    echo ""

    for repo in "${_REPO_NAMES[@]}"; do
        echo "[$repo]"
        echo "  Path: ${_REPO_PATHS[$repo]:-n/a}"
        echo "  Type: ${_REPO_TYPES[$repo]:-n/a}"
        echo "  Language: ${_REPO_LANGUAGES[$repo]:-n/a}"
        echo "  Test: ${_REPO_TEST_CMDS[$repo]:-n/a}"
        echo "  Filter Flag: $(get_test_filter_flag "$repo")"
        echo "  Build: ${_REPO_BUILD_CMDS[$repo]:-n/a}"
        echo "  Deps: ${_REPO_DEPS[$repo]:-none}"
        echo ""
    done

    echo "Build Order: ${_BUILD_ORDER[*]}"
}

# ============================================================================
# Testing Configuration Functions
# ============================================================================

# Get test environment variables for a repo (as KEY=VALUE lines)
# Usage: eval "$(get_test_env "Pennyfarthing-api")"
get_test_env() {
    local name="$1"
    load_repos_config

    if [[ ! -f "$REPOS_CONFIG" ]]; then
        return 0
    fi

    if command -v yq &>/dev/null; then
        yq -r ".repos.\"$name\".test_env // {} | to_entries | .[] | \"export \" + .key + \"=\\\"\" + .value + \"\\\"\"" "$REPOS_CONFIG" 2>/dev/null || true
    elif command -v python3 &>/dev/null; then
        python3 -c "
import yaml
with open('$REPOS_CONFIG') as f:
    c = yaml.safe_load(f)
env = c.get('repos', {}).get('$name', {}).get('test_env', {}) or {}
for k, v in env.items():
    print(f'export {k}=\"{v}\"')
" 2>/dev/null || true
    fi
}

# Get test log directory from config
# Usage: LOG_DIR=$(get_test_log_dir)
get_test_log_dir() {
    load_repos_config

    local log_dir=".session"  # default

    if [[ -f "$REPOS_CONFIG" ]]; then
        if command -v yq &>/dev/null; then
            log_dir=$(yq -r '.testing.log_dir // ".session"' "$REPOS_CONFIG" 2>/dev/null || echo ".session")
        elif command -v python3 &>/dev/null; then
            log_dir=$(python3 -c "
import yaml
with open('$REPOS_CONFIG') as f:
    c = yaml.safe_load(f)
print(c.get('testing', {}).get('log_dir', '.session') or '.session')
" 2>/dev/null || echo ".session")
        fi
    fi

    echo "$PROJECT_ROOT/$log_dir"
}

# Get skip patterns for a language
# Usage: PATTERNS=$(get_skip_patterns "go")
get_skip_patterns() {
    local language="$1"
    load_repos_config

    if [[ ! -f "$REPOS_CONFIG" ]]; then
        # Default patterns if no config
        case "$language" in
            go) echo 't\.Skip' ;;
            typescript|javascript) echo 'it\.skip|describe\.skip|test\.skip' ;;
            python) echo '@pytest\.mark\.skip|pytest\.skip' ;;
            *) echo '' ;;
        esac
        return 0
    fi

    if command -v yq &>/dev/null; then
        local patterns
        patterns=$(yq -r ".testing.skip_patterns_by_language.\"$language\".patterns // [] | join(\"|\")" "$REPOS_CONFIG" 2>/dev/null || echo "")
        if [[ -n "$patterns" ]]; then
            echo "$patterns"
        fi
    elif command -v python3 &>/dev/null; then
        python3 -c "
import yaml
with open('$REPOS_CONFIG') as f:
    c = yaml.safe_load(f)
patterns = c.get('testing', {}).get('skip_patterns_by_language', {}).get('$language', {}).get('patterns', []) or []
print('|'.join(patterns))
" 2>/dev/null || true
    fi
}

# Get skip exceptions for a language
# Usage: EXCEPTIONS=$(get_skip_exceptions "go")
get_skip_exceptions() {
    local language="$1"
    load_repos_config

    if [[ ! -f "$REPOS_CONFIG" ]]; then
        # Default exceptions if no config
        case "$language" in
            go) echo 'LocalStack|not available|CI environment' ;;
            *) echo '' ;;
        esac
        return 0
    fi

    if command -v yq &>/dev/null; then
        yq -r ".testing.skip_patterns_by_language.\"$language\".exceptions // [] | join(\"|\")" "$REPOS_CONFIG" 2>/dev/null || echo ""
    elif command -v python3 &>/dev/null; then
        python3 -c "
import yaml
with open('$REPOS_CONFIG') as f:
    c = yaml.safe_load(f)
exceptions = c.get('testing', {}).get('skip_patterns_by_language', {}).get('$language', {}).get('exceptions', []) or []
print('|'.join(exceptions))
" 2>/dev/null || true
    fi
}

# Get test file pattern for a language
# Usage: PATTERN=$(get_test_file_pattern "go")
get_test_file_pattern() {
    local language="$1"
    load_repos_config

    if [[ ! -f "$REPOS_CONFIG" ]]; then
        # Default patterns if no config
        case "$language" in
            go) echo '*_test.go' ;;
            typescript|javascript) echo '*.test.*' ;;
            python) echo 'test_*.py' ;;
            rust) echo '*.rs' ;;
            *) echo '*' ;;
        esac
        return 0
    fi

    if command -v yq &>/dev/null; then
        local pattern
        pattern=$(yq -r ".testing.skip_patterns_by_language.\"$language\".file_pattern // \"\"" "$REPOS_CONFIG" 2>/dev/null || echo "")
        if [[ -n "$pattern" && "$pattern" != "null" ]]; then
            echo "$pattern"
        else
            # Fallback to defaults
            case "$language" in
                go) echo '*_test.go' ;;
                typescript|javascript) echo '*.test.*' ;;
                python) echo 'test_*.py' ;;
                *) echo '*' ;;
            esac
        fi
    fi
}

# Get container command from config
# Usage: CMD=$(get_container_command)
get_container_command() {
    load_repos_config

    if [[ ! -f "$REPOS_CONFIG" ]]; then
        echo ""
        return 0
    fi

    if command -v yq &>/dev/null; then
        yq -r '.testing.container_command // ""' "$REPOS_CONFIG" 2>/dev/null || echo ""
    elif command -v python3 &>/dev/null; then
        python3 -c "
import yaml
with open('$REPOS_CONFIG') as f:
    c = yaml.safe_load(f)
print(c.get('testing', {}).get('container_command', '') or '')
" 2>/dev/null || echo ""
    fi
}

# ============================================================================
# Initialization
# ============================================================================

# Auto-load config when sourced (can be disabled with REPO_UTILS_LAZY=1)
if [[ "${REPO_UTILS_LAZY:-0}" != "1" ]]; then
    load_repos_config
fi
