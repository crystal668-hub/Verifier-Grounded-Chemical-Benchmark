from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_check_atomisticskills_mace_env_script_imports_project_modules(tmp_path: Path) -> None:
    env = {**os.environ, "ATOMISTICSKILLS_HOME": str(tmp_path / "missing-atomisticskills")}

    completed = subprocess.run(
        [sys.executable, "scripts/check_atomisticskills_mace_env.py"],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "ModuleNotFoundError" not in completed.stderr
    assert "mcp_config.json not found" in completed.stderr


def test_setup_atomisticskills_mace_script_uses_cpu_install_path_on_macos_arm64() -> None:
    script = (ROOT / "scripts" / "setup_atomisticskills_mace.sh").read_text()

    assert "conda-envs/mace-agent/install.sh" not in script
    assert "pytorch=*=*cuda*" not in script
    assert "mace-agent-cpu-env.yaml" in script
    assert "mace-torch>=0.3.15" in script
    assert "python-hostlist" in script
    assert "sella" not in script
    assert '"$CONFIGURE_PYTHON" configure_mcp.py --agent codex --scope project || true' in script
