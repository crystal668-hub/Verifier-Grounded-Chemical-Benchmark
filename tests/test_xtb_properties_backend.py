from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb import backend as xtb_properties


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

ACETONITRILE_XYZ = """6
acetonitrile
C 0.000000 0.000000 0.000000
C 1.460000 0.000000 0.000000
N 2.620000 0.000000 0.000000
H -0.360000 1.020000 0.000000
H -0.360000 -0.510000 0.883346
H -0.360000 -0.510000 -0.883346
"""

HYDRONIUM_XYZ = """4
charge=1
O 0.000000 0.000000 0.000000
H 0.980000 0.000000 0.000000
H -0.490000 0.848705 0.000000
H -0.490000 -0.848705 0.000000
"""

NITRIC_OXIDE_XYZ = """2
nitric oxide
N 0.000000 0.000000 0.000000
O 1.150000 0.000000 0.000000
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

XTB_ADVANCED_OPTIMIZE_STDOUT = """
   *** GEOMETRY OPTIMIZATION CONVERGED AFTER 5 ITERATIONS ***

           -------------------------------------------------
          |                Final Singlepoint                |
           -------------------------------------------------

         #    Occupation            Energy/Eh            Energy/eV
      -------------------------------------------------------------
         8        2.0000           -0.4267046             -11.6112 (HOMO)
         9                         -0.2021540              -5.5009 (LUMO)
        10                         -0.2021540              -5.5009
      -------------------------------------------------------------
                  HL-Gap            0.2245506 Eh            6.1103 eV

     #   Z          covCN         q      C6AA      alpha(0)
     1   6 C        3.754    -0.106    22.588     6.777
     2   6 C        1.890     0.119    28.197     8.576
     3   7 N        0.911    -0.241    26.285     7.415
     4   1 H        0.925     0.076     2.020     2.222
     5   1 H        0.925     0.076     2.020     2.222
     6   1 H        0.925     0.076     2.020     2.222

 Mol. C6AA /au.bohr^6  :        377.200527
 Mol. C8AA /au.bohr^8  :       8625.447370
 Mol. alpha(0) /au     :         29.435445

molecular dipole:
                 x           y           z       tot (Debye)
   full:       -1.515      -0.000      -0.000       3.852

           -------------------------------------------------
          | TOTAL ENERGY               -8.688500964005 Eh   |
          | HOMO-LUMO GAP               6.110331625625 eV   |
           -------------------------------------------------

normal termination of xtb
"""

XTB_WATER_ALPB_STDOUT = """
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         ::                     SUMMARY                     ::
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         :: total energy              -8.698523262688 Eh    ::
         :: -> Gsolv                  -0.012153418227 Eh    ::
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
normal termination of xtb
"""

XTB_HEXANE_ALPB_STDOUT = """
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         ::                     SUMMARY                     ::
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         :: total energy              -8.692754669875 Eh    ::
         :: -> Gsolv                  -0.004657863364 Eh    ::
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
normal termination of xtb
"""

XTB_VOMEGA_STDOUT = """
delta SCC IP (eV):   12.4563
delta SCC EA (eV):   -3.1887
Calculation of global electrophilicity index (IP+EA)^2/(8*(IP-EA))
Global electrophilicity index (eV):    0.6862
normal termination of xtb
"""

XTB_VFUKUI_STDOUT = """
Fukui functions:
     #        f(+)     f(-)     f(0)
     1C      -0.034    0.071    0.019
     2C       0.221    0.131    0.176
     3N       0.341    0.375    0.358
     4H       0.157    0.141    0.149
     5H       0.157    0.141    0.149
     6H       0.157    0.141    0.149
           -------------------------------------------------
          |                Property Printout                |
           -------------------------------------------------
normal termination of xtb
"""

XTB_HESSIAN_STDOUT = """
          :  # frequencies                          12      :
          :  # imaginary freq.                       0      :
          :  imag. cutoff                  -20.0000000 cm-1 :

   temp. (K)  partition function   enthalpy   heat capacity  entropy
                                   cal/mol     cal/K/mol   cal/K/mol   J/K/mol
 298.15  VIB   1.44                  487.893      4.450      2.358
         ROT  0.243E+04              888.752      2.981     18.470
         INT  0.349E+04             1376.645      7.431     20.828
         TR   0.254E+27             1481.254      4.968     37.047
         TOT                        2857.8993    12.3992    57.8755   242.1509

         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         ::                  THERMODYNAMIC                  ::
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         :: total free energy          -8.667100871172 Eh   ::
         :: zero point energy           0.044344236700 Eh   ::
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
normal termination of xtb
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


def advanced_spec(verifier_id: str, property_name: str, backend: dict | None = None, additional: list[str] | None = None) -> dict:
    spec = gap_spec()
    spec.update(
        {
            "verifier_id": verifier_id,
            "property_name": property_name,
            "backend": {"type": "local_xtb", "executable": "xtb", "charge": 0, "uhf": 0, **(backend or {})},
        }
    )
    if additional:
        spec["additional_property_names"] = additional
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


class AdvancedFakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path, float, dict]] = []

    def run(self, mode: str, xyz_path: Path, timeout_seconds: float, *, spec: dict) -> xtb_properties.XTBRunResult:
        self.calls.append((mode, xyz_path, timeout_seconds, spec))
        assert xyz_path.exists()
        backend = spec.get("backend") or {}
        if mode == "optimize":
            optimized_path = xyz_path.parent / "xtbopt.xyz"
            optimized_path.write_text(xyz_path.read_text())
            return xtb_properties.XTBRunResult(stdout=XTB_ADVANCED_OPTIMIZE_STDOUT, stderr="", returncode=0)
        if mode == "singlepoint" and backend.get("solvent") == "water":
            return xtb_properties.XTBRunResult(stdout=XTB_WATER_ALPB_STDOUT, stderr="", returncode=0)
        if mode == "singlepoint" and backend.get("solvent") == "hexane":
            return xtb_properties.XTBRunResult(stdout=XTB_HEXANE_ALPB_STDOUT, stderr="", returncode=0)
        if backend.get("property_command") == "--vomega":
            return xtb_properties.XTBRunResult(stdout=XTB_VOMEGA_STDOUT, stderr="", returncode=0)
        if backend.get("property_command") == "--vfukui":
            return xtb_properties.XTBRunResult(stdout=XTB_VFUKUI_STDOUT, stderr="", returncode=0)
        if backend.get("property_command") == "--ohess":
            return xtb_properties.XTBRunResult(stdout=XTB_HESSIAN_STDOUT, stderr="", returncode=0)
        raise AssertionError(f"unexpected run: mode={mode!r}, backend={backend!r}")


def test_parse_xyz_reads_atoms_and_coordinates() -> None:
    molecule = xtb_properties.parse_xyz(WATER_XYZ)

    assert molecule.comment == "water"
    assert [atom.symbol for atom in molecule.atoms] == ["O", "H", "H"]
    assert molecule.atoms[1].x == pytest.approx(0.758602)


def test_parse_xyz_rejects_atom_count_mismatch() -> None:
    with pytest.raises(xtb_properties.XTBParseError, match="atom count"):
        xtb_properties.parse_xyz("4\nwater\nO 0 0 0\nH 0 0 1\nH 0 1 0\n")


def test_inspect_xyz_reports_structural_domain_properties() -> None:
    water = xtb_properties.inspect_xyz(xtb_properties.parse_xyz(WATER_XYZ))
    acetonitrile = xtb_properties.inspect_xyz(xtb_properties.parse_xyz(ACETONITRILE_XYZ))

    assert water["formula"] == "H2O"
    assert water["carbon_count"] == 0
    assert water["hetero_atom_count"] == 1
    assert water["heavy_element_diversity"] == 1

    assert acetonitrile["formula"] == "C2H3N"
    assert acetonitrile["element_counts"] == {"C": 2, "N": 1, "H": 3}
    assert acetonitrile["carbon_count"] == 2
    assert acetonitrile["hetero_atom_count"] == 1
    assert acetonitrile["heavy_element_diversity"] == 2


@pytest.mark.parametrize(
    ("domain", "message"),
    [
        ({"formula": "C3H3N"}, "formula must be C3H3N"),
        ({"element_count_exact": {"C": 3}}, "C count must be 3"),
        ({"element_count_exact": {"F": 2}}, "F count must be 2"),
        ({"element_count_max": {"C": 1}}, "C count exceeds maximum 1"),
    ],
)
def test_check_domain_supports_exact_formula_and_element_counts(
    domain: dict,
    message: str,
) -> None:
    molecule = xtb_properties.parse_xyz(ACETONITRILE_XYZ)
    properties = xtb_properties.inspect_xyz(molecule)

    assert xtb_properties.check_domain(molecule, properties, domain) == message


@pytest.mark.parametrize(
    ("comment", "charge"),
    [("charge=0", 0), ("charge=1", 1), ("charge=-2", -2)],
)
def test_parse_xyz_charge_accepts_exact_syntax(comment: str, charge: int) -> None:
    assert xtb_properties.parse_xyz_charge(comment) == charge


@pytest.mark.parametrize(
    "comment",
    ["", "charge =1", "charge=+1 extra", "molecule charge=1", "charge=1.0"],
)
def test_parse_xyz_charge_rejects_noncanonical_syntax(comment: str) -> None:
    with pytest.raises(xtb_properties.XTBParseError, match="charge=<integer>"):
        xtb_properties.parse_xyz_charge(comment)


def test_resolve_electronic_state_accepts_fixed_doublet() -> None:
    molecule = xtb_properties.parse_xyz(NITRIC_OXIDE_XYZ)
    spec = {"backend": {"charge": 0, "uhf": 1, "validate_electron_parity": True}}

    state = xtb_properties.resolve_electronic_state(molecule, spec)

    assert state.charge == 0
    assert state.uhf == 1
    assert state.electron_count == 15


def test_candidate_declared_charge_reaches_runner_and_result() -> None:
    runner = AdvancedFakeRunner()
    current_task = task("homo_lumo_gap")
    spec = gap_spec()
    spec["backend"] = {
        **spec["backend"],
        "charge_source": "xyz_comment",
        "uhf": 0,
        "validate_electron_parity": True,
    }

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": HYDRONIUM_XYZ},
        current_task,
        current_task["constraints"][0],
        spec,
        runner=runner,
    )

    assert result["outcome"] == "verified"
    assert result["properties"]["charge"] == 1
    assert result["properties"]["uhf"] == 0
    assert result["properties"]["electron_count"] == 10
    assert runner.calls[0][3]["backend"]["charge"] == 1
    assert runner.calls[0][3]["backend"]["uhf"] == 0


def test_candidate_declared_charge_rejects_odd_closed_shell_electron_count() -> None:
    spec = gap_spec()
    spec["backend"] = {
        **spec["backend"],
        "charge_source": "xyz_comment",
        "uhf": 0,
        "validate_electron_parity": True,
    }
    odd_water = WATER_XYZ.replace("water", "charge=1")
    current_task = task("homo_lumo_gap")

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": odd_water},
        current_task,
        current_task["constraints"][0],
        spec,
        runner=FakeRunner(),
    )

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "domain_error"
    assert "electron count" in result["message"]


def test_parse_xtb_output_reads_xtb_671_full_dipole_line() -> None:
    properties = xtb_properties.parse_xtb_output(XTB_671_DIPOLE_STDOUT, require_converged=True)

    assert properties["total_energy_hartree"] == pytest.approx(-5.504066181050)
    assert properties["homo_lumo_gap"] == pytest.approx(5.951189522894)
    assert properties["dipole_moment"] == pytest.approx(2.621)


def test_parse_xtb_output_reads_lumo_and_molecular_polarizability() -> None:
    properties = xtb_properties.parse_xtb_output(XTB_ADVANCED_OPTIMIZE_STDOUT, require_converged=True)

    assert properties["lumo_energy"] == pytest.approx(-5.5009)
    assert properties["molecular_polarizability"] == pytest.approx(29.435445)


def test_parse_xtb_output_reads_alpb_gsolv_in_hartree() -> None:
    properties = xtb_properties.parse_xtb_output(XTB_WATER_ALPB_STDOUT)

    assert properties["gsolv_hartree"] == pytest.approx(-0.012153418227)


def test_parse_xtb_output_reads_global_electrophilicity() -> None:
    properties = xtb_properties.parse_xtb_output(XTB_VOMEGA_STDOUT)

    assert properties["global_electrophilicity"] == pytest.approx(0.6862)


def test_parse_xtb_output_reads_fukui_table() -> None:
    properties = xtb_properties.parse_xtb_output(XTB_VFUKUI_STDOUT)

    assert properties["max_f_plus_on_carbon"] == pytest.approx(0.221)
    assert properties["f_plus_contrast"] == pytest.approx(-0.12)
    assert properties["max_f_plus_atom_index"] == 2
    assert properties["max_f_plus_atom_symbol"] == "C"


def test_parse_xtb_output_reads_hessian_thermochemistry() -> None:
    properties = xtb_properties.parse_xtb_output(XTB_HESSIAN_STDOUT)

    assert properties["imaginary_frequency_count"] == 0
    assert properties["entropy_298"] == pytest.approx(242.1509)


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

    assert result["outcome"] == "verified"
    assert result["properties"]["homo_lumo_gap"] == pytest.approx(6.5)
    assert result["properties"]["homo_lumo_gap_unit"] == "eV"
    assert result["properties"]["atom_count"] == 3
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

    assert result["outcome"] == "verified"
    assert result["properties"]["dipole_moment"] == pytest.approx(1.85)
    assert result["properties"]["dipole_moment_unit"] == "debye"


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

    assert result["outcome"] == "verified"
    expected = (-5.000000000000 - -5.070680245292) * xtb_properties.HARTREE_TO_EV
    assert result["properties"]["relaxation_energy"] == pytest.approx(expected, rel=1e-9)
    assert result["properties"]["relaxation_energy_unit"] == "eV"
    assert [call[0] for call in runner.calls] == ["singlepoint", "optimize"]


@pytest.mark.parametrize(
    ("calculation_mode", "expected_runner_mode", "expected_energy"),
    [
        ("submitted_singlepoint", "singlepoint", -5.0),
        ("optimized", "optimize", -5.070680245292),
    ],
)
def test_xtb_total_energy_supports_submitted_and_optimized_modes(
    calculation_mode: str,
    expected_runner_mode: str,
    expected_energy: float,
) -> None:
    runner = FakeRunner()
    current_task = {
        "task_id": "total_energy_task",
        "constraints": [
            {
                "type": "minimize_bounded",
                "property": "total_energy",
                "verifier_id": "xtb_total_energy_gfn2_v1",
                "lower": -6.0,
                "upper": -4.0,
            }
        ],
    }
    spec = advanced_spec(
        "xtb_total_energy_gfn2_v1",
        "total_energy",
        {"calculation_mode": calculation_mode},
    )

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": METHANE_XYZ},
        current_task,
        current_task["constraints"][0],
        spec,
        runner=runner,
    )

    assert result["outcome"] == "verified"
    assert result["properties"]["total_energy"] == pytest.approx(expected_energy)
    assert result["properties"]["total_energy_unit"] == "hartree"
    assert [call[0] for call in runner.calls] == [expected_runner_mode]


def test_xtb_total_energy_rejects_unknown_calculation_mode() -> None:
    current_task = {
        "task_id": "total_energy_task",
        "constraints": [
            {
                "type": "minimize_bounded",
                "property": "total_energy",
                "verifier_id": "xtb_total_energy_gfn2_v1",
                "lower": -6.0,
                "upper": -4.0,
            }
        ],
    }
    spec = advanced_spec(
        "xtb_total_energy_gfn2_v1",
        "total_energy",
        {"calculation_mode": "unknown"},
    )

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": METHANE_XYZ},
        current_task,
        current_task["constraints"][0],
        spec,
        runner=FakeRunner(),
    )

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_spec_error"
    assert "calculation_mode" in result["message"]


def test_xtb_total_energy_requires_energy_in_output() -> None:
    class MissingEnergyRunner:
        def run(
            self,
            mode: str,
            xyz_path: Path,
            timeout_seconds: float,
            *,
            spec: dict,
        ) -> xtb_properties.XTBRunResult:
            return xtb_properties.XTBRunResult(
                stdout="normal termination of xtb",
                stderr="",
                returncode=0,
            )

    current_task = {
        "task_id": "total_energy_task",
        "constraints": [
            {
                "type": "minimize_bounded",
                "property": "total_energy",
                "verifier_id": "xtb_total_energy_gfn2_v1",
                "lower": -6.0,
                "upper": -4.0,
            }
        ],
    }
    spec = advanced_spec(
        "xtb_total_energy_gfn2_v1",
        "total_energy",
        {"calculation_mode": "submitted_singlepoint"},
    )

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": METHANE_XYZ},
        current_task,
        current_task["constraints"][0],
        spec,
        runner=MissingEnergyRunner(),
    )

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_tool_error"
    assert "total energy" in result["message"]


def test_xtb_lumo_scores_fake_optimized_output() -> None:
    runner = AdvancedFakeRunner()
    current_task = task("lumo_energy", "minimize_bounded")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": ACETONITRILE_XYZ},
        current_task,
        current_task["constraints"][0],
        advanced_spec("xtb_lumo_gfn2_v1", "lumo_energy", {"method": "GFN2-xTB"}),
        runner=runner,
    )

    assert result["outcome"] == "verified"
    assert result["properties"]["lumo_energy"] == pytest.approx(-5.5009)
    assert result["properties"]["lumo_energy_unit"] == "eV"
    assert [call[0] for call in runner.calls] == ["optimize"]


def test_xtb_polarizability_normalizes_by_heavy_atom_count() -> None:
    runner = AdvancedFakeRunner()
    current_task = task("polarizability_per_heavy_atom", "maximize_bounded")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": ACETONITRILE_XYZ},
        current_task,
        current_task["constraints"][0],
        advanced_spec("xtb_polarizability_gfn2_v1", "polarizability_per_heavy_atom", {"method": "GFN2-xTB"}),
        runner=runner,
    )

    assert result["outcome"] == "verified"
    assert result["properties"]["molecular_polarizability"] == pytest.approx(29.435445)
    assert result["properties"]["polarizability_per_heavy_atom"] == pytest.approx(29.435445 / 3)
    assert result["properties"]["polarizability_per_heavy_atom_unit"] == "atomic_units_per_heavy_atom"


def test_xtb_solvation_selectivity_uses_optimized_geometry_and_two_alpb_runs() -> None:
    runner = AdvancedFakeRunner()
    current_task = task("alpb_water_hexane_selectivity", "maximize_bounded")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": ACETONITRILE_XYZ},
        current_task,
        current_task["constraints"][0],
        advanced_spec(
            "xtb_solvation_selectivity_alpb_v1",
            "alpb_water_hexane_selectivity",
            {
                "method": "GFN2-xTB",
                "optimize_before_property": True,
                "solvent_runs": [
                    {"model": "alpb", "solvent": "water"},
                    {"model": "alpb", "solvent": "hexane"},
                ],
            },
        ),
        runner=runner,
    )

    expected = (-0.004657863364 - -0.012153418227) * xtb_properties.HARTREE_TO_EV
    assert result["outcome"] == "verified"
    assert result["properties"]["alpb_water_hexane_selectivity"] == pytest.approx(expected)
    assert result["properties"]["gsolv_water_eV"] == pytest.approx(-0.012153418227 * xtb_properties.HARTREE_TO_EV)
    assert result["properties"]["gsolv_hexane_eV"] == pytest.approx(-0.004657863364 * xtb_properties.HARTREE_TO_EV)
    assert [call[0] for call in runner.calls] == ["optimize", "singlepoint", "singlepoint"]
    assert runner.calls[1][1].name == "xtbopt.xyz"
    assert [call[3]["backend"].get("solvent") for call in runner.calls[1:]] == ["water", "hexane"]


def test_xtb_electrophilicity_runs_vomega_property_command() -> None:
    runner = AdvancedFakeRunner()
    current_task = task("global_electrophilicity", "maximize_bounded")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": ACETONITRILE_XYZ},
        current_task,
        current_task["constraints"][0],
        advanced_spec(
            "xtb_electrophilicity_gfn1_ipea_v1",
            "global_electrophilicity",
            {"method": "GFN1-xTB/IPEA", "property_command": "--vomega", "optimize_before_property": True},
        ),
        runner=runner,
    )

    assert result["outcome"] == "verified"
    assert result["properties"]["global_electrophilicity"] == pytest.approx(0.6862)
    assert result["properties"]["global_electrophilicity_unit"] == "eV"
    assert [call[0] for call in runner.calls] == ["optimize", "property"]
    assert runner.calls[1][3]["backend"]["property_command"] == "--vomega"


def test_xtb_fukui_allows_secondary_constraint_property_from_same_spec() -> None:
    runner = AdvancedFakeRunner()
    current_task = task("f_plus_contrast", "maximize_bounded")
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": ACETONITRILE_XYZ},
        current_task,
        current_task["constraints"][0],
        advanced_spec(
            "xtb_fukui_gfn1_v1",
            "max_f_plus_on_carbon",
            {"method": "GFN1-xTB", "property_command": "--vfukui", "optimize_before_property": True},
            additional=["f_plus_contrast"],
        ),
        runner=runner,
    )

    assert result["outcome"] == "verified"
    assert result["properties"]["max_f_plus_on_carbon"] == pytest.approx(0.221)
    assert result["properties"]["f_plus_contrast"] == pytest.approx(-0.12)
    assert [call[0] for call in runner.calls] == ["optimize", "property"]
    assert runner.calls[1][3]["backend"]["property_command"] == "--vfukui"


def test_xtb_hessian_thermo_allows_imaginary_frequency_hard_constraint_from_same_spec() -> None:
    runner = AdvancedFakeRunner()
    current_task = task("entropy_298_per_heavy_atom", "maximize_bounded")
    hard_constraint = {
        "property": "imaginary_frequency_count",
        "operator": "closed_window",
        "lower": 0,
        "upper": 0,
    }
    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": ACETONITRILE_XYZ},
        current_task,
        hard_constraint,
        advanced_spec(
            "xtb_hessian_thermo_gfn2_v1",
            "entropy_298_per_heavy_atom",
            {"method": "GFN2-xTB", "property_command": "--ohess", "optimize_before_property": True},
            additional=["imaginary_frequency_count"],
        ),
        runner=runner,
    )

    assert result["outcome"] == "verified"
    assert result["properties"]["imaginary_frequency_count"] == 0
    assert result["properties"]["entropy_298"] == pytest.approx(242.1509)
    assert result["properties"]["entropy_298_per_heavy_atom"] == pytest.approx(242.1509 / 3)
    assert [call[0] for call in runner.calls] == ["hessian"]


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

    assert result["outcome"] != "verified"
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

    assert result["outcome"] != "verified"
    assert result["failure_type"] == failure_type
    assert message in str(result["message"])


@pytest.mark.parametrize(
    ("domain_update", "xyz", "message"),
    [
        ({"carbon_count_min": 1}, WATER_XYZ, "carbon_count below minimum 1"),
        ({"hetero_atom_count_min": 2}, ACETONITRILE_XYZ, "hetero_atom_count below minimum 2"),
        ({"heavy_element_diversity_min": 3}, ACETONITRILE_XYZ, "heavy_element_diversity below minimum 3"),
        ({"formula_denylist": ["C2H3N"]}, ACETONITRILE_XYZ, "formula is denied: C2H3N"),
    ],
)
def test_xtb_property_enforces_nontrivial_structural_domain(domain_update: dict, xyz: str, message: str) -> None:
    current_task = task("homo_lumo_gap")
    spec = gap_spec()
    spec["domain"] = {**spec["domain"], **domain_update}

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": xyz},
        current_task,
        current_task["constraints"][0],
        spec,
        runner=FakeRunner(),
    )

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "domain_error"
    assert result["message"] == message


def test_xtb_property_merges_task_structural_domain_with_verifier_domain() -> None:
    current_task = {
        **task("homo_lumo_gap"),
        "structural_domain": {"carbon_count_min": 1},
    }

    result = xtb_properties.evaluate_xtb_property_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        gap_spec(),
        runner=FakeRunner(),
    )

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "domain_error"
    assert result["message"] == "carbon_count below minimum 1"


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

    assert result["outcome"] != "verified"
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

    assert result["outcome"] != "verified"
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


def test_xtb_runner_builds_property_and_solvation_commands(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(WATER_XYZ)
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=XTB_VOMEGA_STDOUT, stderr="")

    monkeypatch.setattr(xtb_properties.shutil, "which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(xtb_properties.subprocess, "run", fake_run)

    runner = xtb_properties.XTBRunner("xtb")
    runner.run(
        "property",
        xyz_path,
        30,
        spec={"backend": {"method": "GFN1-xTB/IPEA", "charge": 0, "uhf": 0, "property_command": "--vomega"}},
    )
    runner.run(
        "singlepoint",
        xyz_path,
        30,
        spec={"backend": {"method": "GFN2-xTB", "charge": 0, "uhf": 0, "solvent_model": "alpb", "solvent": "water"}},
    )
    runner.run(
        "hessian",
        xyz_path,
        30,
        spec={"backend": {"method": "GFN2-xTB", "charge": 0, "uhf": 0, "property_command": "--ohess"}},
    )

    assert calls == [
        ["/usr/bin/xtb", str(xyz_path), "--gfn", "1", "--chrg", "0", "--uhf", "0", "--vomega"],
        ["/usr/bin/xtb", str(xyz_path), "--gfn", "2", "--chrg", "0", "--uhf", "0", "--alpb", "water"],
        ["/usr/bin/xtb", str(xyz_path), "--gfn", "2", "--chrg", "0", "--uhf", "0", "--ohess"],
    ]


@pytest.mark.parametrize(
    ("xyz", "expected"),
    [
        (METHANE_XYZ, None),
        ("1\noxygen only\nO 0 0 0\n", "all hydrogens must be explicit"),
    ],
)
def test_all_hydrogens_explicit_domain(xyz: str, expected: str | None) -> None:
    molecule = xtb_properties.parse_xyz(xyz)
    properties = xtb_properties.inspect_xyz(molecule)

    error = xtb_properties.check_domain(
        molecule, properties, {"all_hydrogens_explicit": True}
    )

    assert error == expected


def test_element_count_parity_checks_present_non_hydrogen_elements_only() -> None:
    molecule = xtb_properties.parse_xyz(
        "10\nodd heavy elements\n"
        "C 0 0 0\nC 1 0 0\nC 2 0 0\n"
        "N 3 0 0\nO 4 0 0\n"
        "H 0 1 0\nH 1 1 0\nH 2 1 0\nH 3 1 0\nH 4 1 0\n"
    )
    properties = xtb_properties.inspect_xyz(molecule)
    domain = {
        "element_count_parity": {
            "parity": "odd",
            "exclude_elements": ["H"],
        }
    }

    assert xtb_properties.check_domain(molecule, properties, domain) is None

    properties["element_counts"]["O"] = 2
    assert xtb_properties.check_domain(molecule, properties, domain) == "O count must be odd"


def test_joint_dipole_gap_calculation_runs_one_optimization(tmp_path: Path) -> None:
    xyz_path = tmp_path / "candidate.xyz"
    xyz_path.write_text(METHANE_XYZ)
    runner = FakeRunner()
    spec = {
        "backend": {
            "joint_properties": ["dipole_moment", "homo_lumo_gap"]
        }
    }

    properties = xtb_properties.run_property_calculation(
        "dipole_moment", runner, xyz_path, 30.0, spec
    )

    assert [call[0] for call in runner.calls] == ["optimize"]
    assert properties == {
        "dipole_moment": 1.85,
        "dipole_moment_unit": "debye",
        "homo_lumo_gap": 6.5,
        "homo_lumo_gap_unit": "eV",
        "optimization_converged": 1,
    }
