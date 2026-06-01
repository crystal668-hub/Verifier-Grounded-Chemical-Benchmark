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

if [[ ! -d "$ATOMISTICSKILLS_HOME/.git" ]]; then
  mkdir -p "$(dirname "$ATOMISTICSKILLS_HOME")"
  git clone "$ATOMISTICSKILLS_REPO" "$ATOMISTICSKILLS_HOME"
fi

cd "$ATOMISTICSKILLS_HOME"

bash conda-envs/base-agent/install.sh
bash conda-envs/drugdisc-agent/install.sh
bash conda-envs/xrd-agent/install.sh
python configure_mcp.py --agent codex --scope project || true

echo "AtomisticSkills first-batch environments are installed at $ATOMISTICSKILLS_HOME"
