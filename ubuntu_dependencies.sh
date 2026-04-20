#!/bin/bash
set -e

ENV_NAME="${ENV_NAME:-starfish-py3}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ${EUID} -eq 0 && -n "${SUDO_USER:-}" ]]; then
	TARGET_USER="${SUDO_USER}"
	TARGET_HOME="$(getent passwd "${SUDO_USER}" | cut -d: -f6)"
	RUN_AS_USER=(sudo -H -u "${SUDO_USER}")
else
	TARGET_USER="$(id -un)"
	TARGET_HOME="${HOME}"
	RUN_AS_USER=()
fi

if [[ ${EUID} -eq 0 ]]; then
	PKG_PREFIX=()
else
	PKG_PREFIX=(sudo)
fi

if command -v conda >/dev/null 2>&1; then
	CONDA_BIN="$(command -v conda)"
elif [[ -n "${CONDA_EXE:-}" && -x "${CONDA_EXE}" ]]; then
	CONDA_BIN="${CONDA_EXE}"
elif [[ -x "${TARGET_HOME}/miniconda3/bin/conda" ]]; then
	CONDA_BIN="${TARGET_HOME}/miniconda3/bin/conda"
elif [[ -x "${TARGET_HOME}/anaconda3/bin/conda" ]]; then
	CONDA_BIN="${TARGET_HOME}/anaconda3/bin/conda"
else
	echo "ERROR: conda was not found."
	echo "If you are using sudo, this is usually a PATH issue."
	echo "Install Miniconda first: https://docs.conda.io/en/latest/miniconda.html"
	echo "Then re-run this script."
	exit 1
fi

echo "Using conda: ${CONDA_BIN} (target user: ${TARGET_USER})"
echo  "Installing system dependencies via apt-get.."
"${PKG_PREFIX[@]}" apt-get -y install build-essential
"${PKG_PREFIX[@]}" apt-get -y install libxml2-dev
"${PKG_PREFIX[@]}" apt-get -y install libxslt-dev
"${PKG_PREFIX[@]}" apt-get -y install python3-gi
"${PKG_PREFIX[@]}" apt-get -y install gir1.2-gtk-3.0
"${PKG_PREFIX[@]}" apt-get -y install graphviz
"${PKG_PREFIX[@]}" apt-get -y install libhdf5-dev

echo "Preparing conda environment: ${ENV_NAME}"
if ! "${RUN_AS_USER[@]}" "${CONDA_BIN}" run -n "${ENV_NAME}" python --version >/dev/null 2>&1; then
	"${RUN_AS_USER[@]}" "${CONDA_BIN}" create -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}" pip
fi

echo "Enforcing Python version in env: ${PYTHON_VERSION}"
"${RUN_AS_USER[@]}" "${CONDA_BIN}" install -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}" pip

echo "Installing GTK bindings via conda-forge (avoids pip source build failures)"
"${RUN_AS_USER[@]}" "${CONDA_BIN}" install -y -n "${ENV_NAME}" -c conda-forge pygobject pycairo

echo "Installing python dependencies inside conda env: ${ENV_NAME}"
"${RUN_AS_USER[@]}" "${CONDA_BIN}" run -n "${ENV_NAME}" python -m pip install --upgrade pip
"${RUN_AS_USER[@]}" "${CONDA_BIN}" run -n "${ENV_NAME}" python -m pip install -r "${SCRIPT_DIR}/requirements.txt"

echo "Done. Activate the environment with: conda activate ${ENV_NAME}"
