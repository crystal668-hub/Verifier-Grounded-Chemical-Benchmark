from __future__ import annotations

import json
import os
import subprocess
import sys


def test_check_xtb_env_script_reports_missing_executable(tmp_path) -> None:
    env = {**os.environ, "PATH": str(tmp_path)}
    completed = subprocess.run(
        [sys.executable, "scripts/env/check_xtb_env.py"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"
    assert payload["xtb_executable"] is None
    assert "xTB executable not found" in payload["message"]
