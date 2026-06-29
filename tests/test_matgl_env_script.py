from __future__ import annotations

import json
import subprocess
import sys


def test_check_matgl_env_reports_json() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_matgl_env.py", "--no-model-load"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert "matgl" in payload["versions"]
    assert payload["pymatgen"]["fixture_formula"] == "Si"
