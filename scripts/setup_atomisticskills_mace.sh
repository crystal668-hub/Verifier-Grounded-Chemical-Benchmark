#!/usr/bin/env bash
set -euo pipefail

ATOMISTICSKILLS_HOME="${ATOMISTICSKILLS_HOME:-$HOME/projects/AtomisticSkills}"
ATOMISTICSKILLS_REPO="${ATOMISTICSKILLS_REPO:-https://github.com/learningmatter-mit/AtomisticSkills.git}"

if ! command -v conda >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
    echo "conda not found. Install Miniforge first:"
    echo "  brew install --cask miniforge"
  else
    echo "conda not found. Install Miniforge or another conda distribution first." >&2
  fi
  exit 1
fi

resolve_configure_python() {
  local conda_base
  conda_base="$(conda info --base)"
  if [[ -x "$conda_base/bin/python" ]]; then
    printf '%s\n' "$conda_base/bin/python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

if [[ ! -d "$ATOMISTICSKILLS_HOME/.git" ]]; then
  mkdir -p "$(dirname "$ATOMISTICSKILLS_HOME")"
  git clone "$ATOMISTICSKILLS_REPO" "$ATOMISTICSKILLS_HOME"
fi

cd "$ATOMISTICSKILLS_HOME"

TEMP_ENV_FILE="$(mktemp "${TMPDIR:-/tmp}/mace-agent-cpu-env.yaml.XXXXXX")"
TEMP_REQUIREMENTS_FILE="$(mktemp "${TMPDIR:-/tmp}/mace-agent-pip-requirements.txt.XXXXXX")"
trap 'rm -f "$TEMP_ENV_FILE" "$TEMP_REQUIREMENTS_FILE"' EXIT
cat >"$TEMP_ENV_FILE" <<'YAML'
name: mace-agent
channels:
  - conda-forge
dependencies:
  - python=3.10
  - pytorch
  - python-hostlist
  - pip
YAML

cat >"$TEMP_REQUIREMENTS_FILE" <<'REQ'
mcp
mace-torch>=0.3.15
cython
pymatgen
pymatgen-analysis-diffusion
ase
matcalc
setuptools<70
setuptools-scm
typing-extensions
REQ

conda env remove -n mace-agent -y || true
conda env create -f "$TEMP_ENV_FILE"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate mace-agent
python -m pip install -r "$TEMP_REQUIREMENTS_FILE"

if CONFIGURE_PYTHON="$(resolve_configure_python)"; then
  "$CONFIGURE_PYTHON" configure_mcp.py --agent codex --scope project || true
else
  echo "No Python executable found to run configure_mcp.py; skipping Codex MCP configuration." >&2
fi

echo "AtomisticSkills MACE CPU environment is installed at $ATOMISTICSKILLS_HOME"
