from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_check_atomisticskills_matgl_env_script_imports_project_modules(tmp_path: Path) -> None:
    env = {**os.environ, "ATOMISTICSKILLS_HOME": str(tmp_path / "missing-atomisticskills")}

    completed = subprocess.run(
        [sys.executable, "scripts/check_atomisticskills_matgl_env.py"],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "ModuleNotFoundError" not in completed.stderr
    assert "mcp_config.json not found" in completed.stderr


def test_setup_atomisticskills_matgl_script_installs_only_matgl_agent() -> None:
    script = (ROOT / "scripts" / "setup_atomisticskills_matgl.sh").read_text()

    assert "conda-envs/matgl-agent/install.sh" in script
    assert "conda-envs/base-agent/install.sh" not in script
    assert "conda-envs/drugdisc-agent/install.sh" not in script
    assert "conda-envs/xrd-agent/install.sh" not in script
    assert '"$CONFIGURE_PYTHON" configure_mcp.py --agent codex --scope project || true' in script
