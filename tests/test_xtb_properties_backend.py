from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from verifiers.backends import xtb_properties


WATER_XYZ = """3
water
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284
"""

METHANE_XYZ = """5
methane
C 0.000000 0.000000 0.000000
H 0.629118 0.629118 0.629118
H -0.629118 -0.629118 0.629118
H -0.629118 0.629118 -0.629118
H 0.629118 -0.629118 -0.629118
"""

XTB_STDOUT = """
 | TOTAL ENERGY              -5.070680245292 Eh
 | HOMO-LUMO GAP              6.500000000000 eV
 molecular dipole:
          x           y           z       tot (Debye)
       0.000       0.000       1.850       1.850
 GEOMETRY OPTIMIZATION CONVERGED
"""

XTB_671_DIPOLE_STDOUT = """
   *** GEOMETRY OPTIMIZATION CONVERGED AFTER 4 ITERATIONS ***

         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         ::                     SUMMARY                     ::
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         :: total energy              -5.503248222956 Eh    ::
         :: HOMO-LUMO gap              5.756262039309 eV    ::
         ::.................................................::

molecular dipole:
                 x           y           z       tot (Debye)
 q only:       -0.505      -0.000       0.000
   full:       -1.031      -0.000      -0.000       2.621

           -------------------------------------------------
          | TOTAL ENERGY               -5.504066181050 Eh   |
          | HOMO-LUMO GAP               5.951189522894 eV   |
           -------------------------------------------------
"""


def gap_spec() -> dict:
    return {
        "verifier_id": "xtb_gap_gfn2_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": "homo_lumo_gap",
        "backend": {"type": "local_xtb", "executable": "xtb", "charge": 0, "uhf": 0},
        "domain": {
            "allowed_elements": ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br"],
            "atom_count": [3, 80],
            "heavy_atom_count": [1, 40],
            "max_absolute_coordinate": 30.0,
            "min_interatomic_distance": 0.45,
            "inferred_components": 1,
        },
    }


def dipole_spec() -> dict:
    spec = gap_spec()
    spec.update({"verifier_id": "xtb_dipole_gfn2_v1", "property_name": "dipole_moment"})
    return spec


def relaxation_spec() -> dict:
    spec = gap_spec()
    spec.update({"verifier_id": "xtb_relaxation_energy_gfn2_v1", "property_name": "relaxation_energy"})
    return spec


def task(property_name: str, constraint_type: str = "window") -> dict:
    constraint = {
        "type": constraint_type,
        "property": property_name,
        "verifier_id": f"xtb_{property_name}_gfn2_v1",
        "min": 4.0,
        "max": 7.0,
        "sigma": 0.75,
    }
    if constraint_type == "maximize_bounded":
        constraint = {"type": constraint_type, "property": property_name, "verifier_id": constraint["verifier_id"], "lower": 0.0, "upper": 12.0}
    if constraint_type == "minimize_bounded":
        constraint = {"type": constraint_type, "property": property_name, "verifier_id": constraint["verifier_id"], "lower": 0.0, "upper": 0.5}
    return {"task_id": f"xtb_{property_name}_task", "constraints": [constraint]}


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path, float]] = []

    def run(self, mode: str, xyz_path: Path, timeout_seconds: float, *, spec: dict) -> xtb_properties.XTBRunResult:
        self.calls.append((mode, xyz_path, timeout_seconds))
        assert xyz_path.exists()
        if mode == "singlepoint":
            return xtb_properties.XTBRunResult(stdout=XTB_STDOUT.replace("-5.070680245292", "-5.000000000000"), stderr="", returncode=0)
        return xtb_properties.XTBRunResult(stdout=XTB_STDOUT, stderr="", returncode=0)


def test_parse_xyz_reads_atoms_and_coordinates() -> None:
    molecule = xtb_properties.parse_xyz(WATER_XYZ)

    assert molecule.comment == "water"
    assert [atom.symbol for atom in molecule.atoms] == ["O", "H", "H"]
    assert molecule.atoms[1].x == pytest.approx(0.758602)


def test_parse_xyz_rejects_atom_count_mismatch() -> None:
    with pytest.raises(xtb_properties.XTBParseError, match="atom count"):
        xtb_properties.parse_xyz("4\nwater\nO 0 0 0\nH 0 0 1\nH 0 1 0\n")


def test_parse_xtb_output_reads_xtb_671_full_dipole_line() -> None:
    properties = xtb_properties.parse_xtb_output(XTB_671_DIPOLE_STDOUT, require_converged=True)

    assert properties["total_energy_hartree"] == pytest.approx(-5.504066181050)
    assert properties["homo_lumo_gap"] == pytest.approx(5.951189522894)
    assert properties["dipole_moment"] == pytest.approx(2.621)


def test_xtb_gap_scores_fake_optimized_output() -> None:
    runner = FakeRunner()
    current_task = task("homo_lumo_gap")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        gap_spec(),
        runner=runner,
    )

    assert result["status"] == "ok"
    assert result["properties"]["homo_lumo_gap"] == pytest.approx(6.5)
    assert result["properties"]["homo_lumo_gap_unit"] == "eV"
    assert result["properties"]["atom_count"] == 3
    assert result["scores"]["score"] == 1.0
    assert runner.calls == [("optimize", runner.calls[0][1], 60.0)]


def test_xtb_dipole_scores_fake_optimized_output() -> None:
    runner = FakeRunner()
    current_task = task("dipole_moment", "maximize_bounded")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        dipole_spec(),
        runner=runner,
    )

    assert result["status"] == "ok"
    assert result["properties"]["dipole_moment"] == pytest.approx(1.85)
    assert result["properties"]["dipole_moment_unit"] == "debye"
    assert result["scores"]["score"] == pytest.approx(0.15416666666666667)


def test_xtb_relaxation_energy_uses_singlepoint_and_optimized_energies() -> None:
    runner = FakeRunner()
    current_task = task("relaxation_energy", "minimize_bounded")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": METHANE_XYZ},
        current_task,
        current_task["constraints"][0],
        relaxation_spec(),
        runner=runner,
    )

    assert result["status"] == "ok"
    expected = (-5.000000000000 - -5.070680245292) * xtb_properties.HARTREE_TO_EV
    assert result["properties"]["relaxation_energy"] == pytest.approx(expected, rel=1e-9)
    assert result["properties"]["relaxation_energy_unit"] == "eV"
    assert result["scores"]["score"] == 0.0
    assert [call[0] for call in runner.calls] == ["singlepoint", "optimize"]


def test_xtb_property_reports_verifier_spec_error_for_property_mismatch() -> None:
    current_task = task("homo_lumo_gap")
    spec = {**gap_spec(), "property_name": "dipole_moment"}

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec,
        runner=FakeRunner(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
    assert "does not match" in result["message"]


@pytest.mark.parametrize(
    ("xyz", "failure_type", "message"),
    [
        ("", "parse_error", "candidate must include an XYZ string"),
        ("1\nneon\nNe 0 0 0\n", "domain_error", "disallowed elements"),
        ("3\nbad\nO 0 0 0\nH 0 0 0.1\nH 0 1 0\n", "validity_error", "interatomic distance"),
        ("4\ndisconnected\nO 0 0 0\nH 0.8 0 0.5\nH -0.8 0 0.5\nH 10 10 10\n", "validity_error", "disconnected"),
    ],
)
def test_xtb_property_maps_candidate_validation_errors(xyz: str, failure_type: str, message: str) -> None:
    current_task = task("homo_lumo_gap")

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": xyz},
        current_task,
        current_task["constraints"][0],
        gap_spec(),
        runner=FakeRunner(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == failure_type
    assert message in str(result["message"])


@pytest.mark.parametrize(
    ("exception", "failure_type"),
    [
        (xtb_properties.XTBEnvironmentError("missing xtb"), "verifier_environment_error"),
        (xtb_properties.XTBToolError("bad output"), "verifier_tool_error"),
        (xtb_properties.XTBTimeoutError("timed out"), "verifier_timeout"),
    ],
)
def test_xtb_property_maps_runner_errors(exception: Exception, failure_type: str) -> None:
    class ErrorRunner:
        def run(self, mode: str, xyz_path: Path, timeout_seconds: float, *, spec: dict) -> xtb_properties.XTBRunResult:
            raise exception

    current_task = task("homo_lumo_gap")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        gap_spec(),
        runner=ErrorRunner(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == failure_type


def test_xtb_property_reports_missing_property_from_output() -> None:
    class MissingPropertyRunner:
        def run(self, mode: str, xyz_path: Path, timeout_seconds: float, *, spec: dict) -> xtb_properties.XTBRunResult:
            return xtb_properties.XTBRunResult(stdout="GEOMETRY OPTIMIZATION CONVERGED", stderr="", returncode=0)

    current_task = task("homo_lumo_gap")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        gap_spec(),
        runner=MissingPropertyRunner(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_tool_error"
    assert "missing HOMO-LUMO gap" in str(result["message"])


def test_xtb_runner_builds_official_cli_commands(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(WATER_XYZ)
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=XTB_STDOUT, stderr="")

    monkeypatch.setattr(xtb_properties.shutil, "which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(xtb_properties.subprocess, "run", fake_run)

    runner = xtb_properties.XTBRunner("xtb")
    result = runner.run("optimize", xyz_path, 30, spec={"backend": {"charge": 0, "uhf": 0}})

    assert result.returncode == 0
    assert calls == [["/usr/bin/xtb", str(xyz_path), "--gfn", "2", "--chrg", "0", "--uhf", "0", "--opt"]]
