#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${ENV_NAME:-starfish-py3}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
INSTALL_APT="${INSTALL_APT:-0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "STARFiSh dependency setup"
echo "This script expects Miniconda/Anaconda to already be installed."
echo "It will create/update the conda environment: ${ENV_NAME}"
echo ""

case "$(uname -s)" in
	Linux*)
		OS_NAME="linux"
		;;
	Darwin*)
		OS_NAME="macos"
		;;
	*)
		OS_NAME="unknown"
		;;
esac

if [[ ${EUID} -eq 0 && -n "${SUDO_USER:-}" ]]; then
	TARGET_USER="${SUDO_USER}"
	TARGET_HOME="$(getent passwd "${SUDO_USER}" | cut -d: -f6)"
	RUN_AS_USER=(sudo -H -u "${SUDO_USER}")
else
	TARGET_USER="$(id -un)"
	TARGET_HOME="${HOME}"
	RUN_AS_USER=()
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
	echo ""
	echo "Install Miniconda first, then re-run this script:"
	echo "  https://docs.conda.io/en/latest/miniconda.html"
	echo ""
	echo "If conda is already installed, start a new shell or run:"
	echo "  source ~/miniconda3/etc/profile.d/conda.sh"
	exit 1
fi

echo "Using conda: ${CONDA_BIN}"
echo "Target user: ${TARGET_USER}"
echo "Detected OS: ${OS_NAME}"
echo ""

if [[ "${INSTALL_APT}" == "1" ]]; then
	if [[ "${OS_NAME}" != "linux" ]]; then
		echo "ERROR: INSTALL_APT=1 is only supported on Linux/Ubuntu."
		echo "macOS does not use apt-get; continuing is not possible with INSTALL_APT=1."
		exit 1
	fi

	if [[ ${EUID} -eq 0 ]]; then
		PKG_PREFIX=()
	else
		PKG_PREFIX=(sudo)
	fi

	echo "INSTALL_APT=1 set: installing minimal Ubuntu desktop/runtime packages."
	echo "Most STARFiSh dependencies are installed through conda below."
	"${PKG_PREFIX[@]}" apt-get update
	"${PKG_PREFIX[@]}" apt-get install -y \
		build-essential \
		dbus-x11 \
		libgl1 \
		libglu1-mesa \
		libxkbcommon-x11-0
	echo ""
else
	if [[ "${OS_NAME}" == "linux" ]]; then
		echo "Skipping apt-get by default."
		echo "If GTK/OpenGL cannot connect to your desktop later, rerun with:"
		echo "  INSTALL_APT=1 ./ubuntu_dependencies.sh"
	elif [[ "${OS_NAME}" == "macos" ]]; then
		echo "macOS detected: skipping apt-get."
		echo "The solver dependencies will be installed through conda."
		echo "The legacy GTK/VNC/3D visualizers may require additional macOS display setup."
	else
		echo "Unknown OS detected: skipping apt-get."
		echo "The conda environment setup will still be attempted."
	fi
	echo ""
fi

echo "Preparing conda environment: ${ENV_NAME}"
if ! "${RUN_AS_USER[@]}" "${CONDA_BIN}" run -n "${ENV_NAME}" python --version >/dev/null 2>&1; then
	"${RUN_AS_USER[@]}" "${CONDA_BIN}" create -y -n "${ENV_NAME}" -c conda-forge \
		"python=${PYTHON_VERSION}" \
		pip
fi

echo "Installing STARFiSh dependencies from conda-forge"
"${RUN_AS_USER[@]}" "${CONDA_BIN}" install -y -n "${ENV_NAME}" -c conda-forge \
	"python=${PYTHON_VERSION}" \
	pip \
	numpy \
	scipy \
	h5py \
	lxml \
	matplotlib \
	psutil \
	pydot \
	graphviz \
	pygobject \
	pycairo \
	gtk3 \
	gdk-pixbuf \
	librsvg \
	pyopengl \
	freeglut \
	pyglet \
	chaospy

echo "Checking installed modules"
"${RUN_AS_USER[@]}" "${CONDA_BIN}" run -n "${ENV_NAME}" python "${SCRIPT_DIR}/systemCheck.py"

echo ""
echo "Done."
echo "Activate with:"
echo "  conda activate ${ENV_NAME}"
echo ""
echo "Run STARFiSh from the repository root, for example:"
echo "  python Simulator.py -f singleBifurcation_template -n 012 -d test_run -v 0"
if [[ "${OS_NAME}" == "macos" ]]; then
	echo ""
	echo "macOS note:"
	echo "  The numerical solver should work from conda."
	echo "  The original GTK/OpenGL visualizers are Linux-first and may need XQuartz or further GTK fixes."
fi
