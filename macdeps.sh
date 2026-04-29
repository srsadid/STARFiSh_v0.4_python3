#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${ENV_NAME:-starfish-py3}"
PYTHON_VERSION="3.10" # Fixed for legacy compatibility
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "--- STARFiSh macOS Setup ---"

# 1. Use Mamba if available, otherwise Conda
if command -v mamba >/dev/null 2>&1; then
    BIN="mamba"
else
    BIN="conda"
    echo "Note: Install 'mamba' for much faster environment solving."
fi

# 2. Locate conda if not already on PATH
if ! command -v "${BIN}" >/dev/null 2>&1; then
    if [[ -x "${HOME}/miniconda/bin/${BIN}" ]]; then
        BIN="${HOME}/miniconda/bin/${BIN}"
    elif [[ -x "${HOME}/miniconda3/bin/${BIN}" ]]; then
        BIN="${HOME}/miniconda3/bin/${BIN}"
    elif [[ -x "${HOME}/anaconda3/bin/${BIN}" ]]; then
        BIN="${HOME}/anaconda3/bin/${BIN}"
    else
        echo "ERROR: conda/mamba was not found on PATH."
        echo "Install Miniconda first, then re-run this script."
        exit 1
    fi
fi

conda_cmd() {
    "${BIN}" "$@"
}

# 3. Homebrew for system libs (freeglut is not on conda-forge for osx-64)
if command -v brew >/dev/null 2>&1; then
    BREW_BIN="$(command -v brew)"
elif [[ -x "/opt/homebrew/bin/brew" ]]; then
    BREW_BIN="/opt/homebrew/bin/brew"
elif [[ -x "/usr/local/bin/brew" ]]; then
    BREW_BIN="/usr/local/bin/brew"
else
    BREW_BIN=""
fi

if [[ -n "${BREW_BIN}" ]]; then
    echo "Installing system libs via Homebrew (graphviz, freeglut, pkg-config)..."
    "${BREW_BIN}" install graphviz freeglut pkg-config >/dev/null 2>&1 || true
else
    echo "WARNING: Homebrew not found; freeglut/graphviz may be missing for 3D/graph features."
fi

# 4. Create environment with legacy-compatible versions
echo "Creating environment: ${ENV_NAME}..."
conda_cmd create -y -n "${ENV_NAME}" -c conda-forge \
    python="${PYTHON_VERSION}" \
    numpy scipy h5py lxml matplotlib psutil pydot graphviz \
    pyopengl pyglet==1.5.27 chaospy \
    pycairo \
    pygobject \
    gtk3 gdk-pixbuf librsvg \
    pkg-config \
    gobject-introspection

# 3. Fixing the "ModuleNotFoundError: gobject"
# We will create a small shim inside the site-packages so the old code finds what it needs
echo "Applying legacy GTK shims..."
PYTHON_PATH=$(conda_cmd run -n "${ENV_NAME}" python -c "import site; print(site.getsitepackages()[0])")

# This creates a fake 'gobject' module that points to the new 'GObject'
conda_cmd run -n "${ENV_NAME}" python -c "
import os
path = os.path.join('$PYTHON_PATH', 'gobject')
if not os.path.exists(path):
    os.makedirs(path)
    with open(os.path.join(path, '__init__.py'), 'w') as f:
        f.write('from gi.repository import GObject as _GObject\nimport sys\nsys.modules[\"gobject\"] = _GObject\n')
"

echo "Checking installation..."
conda_cmd run -n "${ENV_NAME}" python "${SCRIPT_DIR}/systemCheck.py"

echo "Done. Activate with: conda activate ${ENV_NAME}"
