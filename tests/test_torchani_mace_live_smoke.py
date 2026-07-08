from __future__ import annotations

import os
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("VGB_RUN_MLIP_SMOKE") != "1",
    reason="set VGB_RUN_MLIP_SMOKE=1 to run TorchANI/MACE live model smoke tests",
)


def test_check_torchani_env_live_smoke() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_torchani_env.py"],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert completed.returncode == 0
    assert '"status": "ok"' in completed.stdout
    assert "torchani_total_energy_hartree" in completed.stdout


def test_check_mace_mp_env_live_smoke() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_mace_mp_env.py"],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert completed.returncode == 0
    assert '"status": "ok"' in completed.stdout
    assert "mace_mp_energy_per_atom_ev" in completed.stdout
