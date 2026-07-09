from __future__ import annotations

import json
import subprocess
import sys


def test_check_admet_ai_env_outputs_json() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/env/check_admet_ai_env.py", "--smiles", "CCO"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["versions"]["admet-ai"] == "2.0.1"
    assert payload["models"]["num_ensembles"] == 2
    assert payload["models"]["task_group_sizes"] == [31, 10]
    assert payload["prediction"]["smiles"] == "CCO"
    properties = payload["prediction"]["properties"]
    assert "Solubility_AqSolDB" in properties
    assert "hERG" in properties
    assert "AMES" in properties
    assert "BBB_Martins" in properties
    assert "Caco2_Wang" in properties
