from __future__ import annotations

from pathlib import Path

import pytest

from benchmark.evaluate import evaluate_one, load_tasks, load_verifier_specs


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "xtb_xyz"
OPTIMIZATION_TASK_IDS = [
    "xtb_gap_max_003",
    "xtb_gap_min_004",
    "xtb_dipole_max_005",
    "xtb_low_gap_high_dipole_opt_006",
]

BASELINE_XYZ = {
    "water": """3
water
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284
""",
    "methane": """5
methane
C 0.000000 0.000000 0.000000
H 0.629118 0.629118 0.629118
H -0.629118 -0.629118 0.629118
H -0.629118 0.629118 -0.629118
H 0.629118 -0.629118 -0.629118
""",
    "ammonia": """4
ammonia
N 0.000000 0.000000 0.000000
H 0.000000 0.937700 0.381600
H 0.812100 -0.468800 0.381600
H -0.812100 -0.468800 0.381600
""",
    "carbon_dioxide": """3
carbon dioxide
O -1.160000 0.000000 0.000000
C 0.000000 0.000000 0.000000
O 1.160000 0.000000 0.000000
""",
    "hydrogen_cyanide": """3
hydrogen cyanide
H -1.063000 0.000000 0.000000
C 0.000000 0.000000 0.000000
N 1.156000 0.000000 0.000000
""",
    "formaldehyde": """4
formaldehyde
C 0.000000 0.000000 0.000000
O 1.208000 0.000000 0.000000
H -0.604000 0.935000 0.000000
H -0.604000 -0.935000 0.000000
""",
    "ethene": """6
ethene
C -0.669500 0.000000 0.000000
C 0.669500 0.000000 0.000000
H -1.232100 0.928900 0.000000
H -1.232100 -0.928900 0.000000
H 1.232100 0.928900 0.000000
H 1.232100 -0.928900 0.000000
""",
    "benzene": """12
benzene
C 1.397000 0.000000 0.000000
C 0.698500 1.209837 0.000000
C -0.698500 1.209837 0.000000
C -1.397000 0.000000 0.000000
C -0.698500 -1.209837 0.000000
C 0.698500 -1.209837 0.000000
H 2.487000 0.000000 0.000000
H 1.243500 2.153804 0.000000
H -1.243500 2.153804 0.000000
H -2.487000 0.000000 0.000000
H -1.243500 -2.153804 0.000000
H 1.243500 -2.153804 0.000000
""",
    "methanol": """6
methanol
C 0.000000 0.000000 0.000000
O 1.430000 0.000000 0.000000
H -0.360000 1.020000 0.000000
H -0.360000 -0.510000 0.883346
H -0.360000 -0.510000 -0.883346
H 1.750000 0.000000 0.900000
""",
    "acetonitrile": """6
acetonitrile
C 0.000000 0.000000 0.000000
C 1.460000 0.000000 0.000000
N 2.620000 0.000000 0.000000
H -0.360000 1.020000 0.000000
H -0.360000 -0.510000 0.883346
H -0.360000 -0.510000 -0.883346
""",
    "nitromethane": """7
nitromethane
C 0.000000 0.000000 0.000000
N 1.480000 0.000000 0.000000
O 2.050000 1.070000 0.000000
O 2.050000 -1.070000 0.000000
H -0.360000 1.020000 0.000000
H -0.360000 -0.510000 0.883346
H -0.360000 -0.510000 -0.883346
""",
}


@pytest.mark.parametrize("task_id", OPTIMIZATION_TASK_IDS)
@pytest.mark.parametrize("name,xyz", BASELINE_XYZ.items())
def test_simple_common_molecules_do_not_score_high_on_xtb_optimization_tasks(task_id: str, name: str, xyz: str) -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")

    result = evaluate_one(
        {"task_id": task_id, "response": f"FINAL ANSWER:\n```xyz\n{xyz}```"},
        tasks,
        specs,
    )

    assert result["status"] != "ok" or result["scores"]["score"] <= 0.35, (
        task_id,
        name,
        result.get("failure_type"),
        result.get("properties"),
        result.get("scores"),
    )
