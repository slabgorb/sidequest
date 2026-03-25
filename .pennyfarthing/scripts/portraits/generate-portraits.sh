#!/usr/bin/env bash
#
# Portrait Generator Wrapper
# Activates venv and runs generate-portraits.py with all arguments
#
# Usage:
#   ./scripts/generate-portraits.sh --theme arthurian-mythos --dry-run
#   ./scripts/generate-portraits.sh --engine flux --theme shakespeare
#   ./scripts/generate-portraits.sh --engine sdxl --theme star-trek-tos --output-dir /tmp/portraits
#   ./scripts/generate-portraits.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find PROJECT_ROOT by looking for .pennyfarthing or pennyfarthing-dist marker
_dir="$SCRIPT_DIR"
while [[ ! -d "$_dir/.pennyfarthing" ]] && [[ ! -d "$_dir/pennyfarthing-dist" ]] && [[ "$_dir" != "/" ]]; do
    _dir="$(dirname "$_dir")"
done
PROJECT_ROOT="$_dir"

# Detect engine from args to select the right venv
PYTHON_SCRIPT="$SCRIPT_DIR/generate-portraits.py"
ENGINE="sdxl"
prev_arg=""
for arg in "$@"; do
    if [[ "$prev_arg" == "--engine" ]]; then
        ENGINE="$arg"
        break
    fi
    prev_arg="$arg"
done

# Find Python venv based on engine
# Flux uses ~/.venvs/flux, SDXL uses ~/.venvs/sd
# Priority: VENV_DIR env var > engine-specific > project .venv > fallback
if [[ -z "${VENV_DIR:-}" ]]; then
    if [[ "$ENGINE" == "flux" ]] && [[ -d "$HOME/.venvs/flux" ]]; then
        VENV_DIR="$HOME/.venvs/flux"
    elif [[ -d "$PROJECT_ROOT/.venv" ]]; then
        VENV_DIR="$PROJECT_ROOT/.venv"
    elif [[ -d "$HOME/.venvs/sd" ]]; then
        VENV_DIR="$HOME/.venvs/sd"
    elif [[ -d "$HOME/.venv" ]]; then
        VENV_DIR="$HOME/.venv"
    fi
fi

# Check venv exists
if [[ -z "${VENV_DIR:-}" ]] || [[ ! -d "$VENV_DIR" ]]; then
    echo "Error: Virtual environment not found for engine '$ENGINE'"
    echo "Searched: $PROJECT_ROOT/.venv, ~/.venvs/sd, ~/.venvs/flux, ~/.venv"
    echo "Or set VENV_DIR=/path/to/venv"
    if [[ "$ENGINE" == "flux" ]]; then
        echo "For Flux: python3 -m venv ~/.venvs/flux && pip install torch einops transformers pillow pyyaml"
    else
        echo "For SDXL: python3 -m venv ~/.venvs/sd && pip install diffusers transformers accelerate torch pillow pyyaml"
    fi
    exit 1
fi
echo "Using venv: $VENV_DIR (engine: $ENGINE)"

# Check Python script exists
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "Error: generate-portraits.py not found at $PYTHON_SCRIPT"
    exit 1
fi

# Activate venv and run
source "$VENV_DIR/bin/activate"

# Verify torch is available
if ! python -c "import torch" 2>/dev/null; then
    echo "Error: torch not installed in venv"
    echo "Install with: pip install diffusers transformers accelerate torch pillow"
    deactivate
    exit 1
fi

# Run the portrait generator with all passed arguments
python "$PYTHON_SCRIPT" "$@"
