from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_check_atomisticskills_env_script_imports_project_modules(tmp_path: Path) -> None:
    env = {**os.environ, "ATOMISTICSKILLS_HOME": str(tmp_path / "missing-atomisticskills")}

    completed = subprocess.run(
        [sys.executable, "scripts/check_atomisticskills_env.py"],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "ModuleNotFoundError" not in completed.stderr
    assert "mcp_config.json not found" in completed.stderr
