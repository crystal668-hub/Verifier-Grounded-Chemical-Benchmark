from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import verifier_grounded_benchmark as vgb

from scripts.release.build_release import _require_formal_inventory, task_inventory


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TASK_IDS = {
    "rdkit": [
        "rdkit_qed_max_001",
        "rdkit_sa_min_002",
        "rdkit_logp_window_003",
        "rdkit_tpsa_window_004",
        "rdkit_hba_window_005",
        "rdkit_hbd_window_006",
        "rdkit_fsp3_max_007",
        "rdkit_qed_sa_008",
        "rdkit_logp_tpsa_009",
        "rdkit_hba_hbd_010",
        "rdkit_logp_target_011",
    ],
    "xtb": [
        "xtb_gap_window_001",
        "xtb_dipole_window_002",
        "xtb_gap_max_003",
        "xtb_gap_min_004",
        "xtb_dipole_max_005",
        "xtb_low_gap_high_dipole_opt_006",
        "xtb_gap_dipole_window_007",
        "xtb_lumo_min_008",
        "xtb_polarizability_dipole_opt_009",
        "xtb_solvation_selectivity_alpb_010",
        "xtb_electrophilicity_max_011",
        "xtb_fukui_carbon_site_012",
        "xtb_hessian_thermo_stability_013",
        "xtb_formula_dipole_min_014",
        "xtb_two_fluorine_gap_min_015",
        "xtb_c10_f2_gap_min_016",
        "xtb_roy_singlepoint_energy_min_017",
        "xtb_ritonavir_optimized_energy_min_018",
    ],
    "property_calculation": [
        "property_calc_free_energy_001",
        "property_calc_crystal_phase_002",
    ],
}


def test_package_track_versions_and_inventory_are_release_aligned() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    assert version == "0.3.0"

    inventory = task_inventory(version)
    assert inventory["schema_version"] == 2
    assert inventory["result_schema_version"] == "2"
    assert inventory["scoring_version"] == "linear_goal_v2"
    assert inventory["tracks"]["xtb"]["scoring_status"] == "formal"
    assert inventory["scoring_profiles"]
    for track_name, expected_ids in EXPECTED_TASK_IDS.items():
        track = vgb.load_track(track_name)
        assert track.definition.version == version
        assert [task["task_id"] for task in track.tasks()] == expected_ids
        assert inventory["tracks"][track_name]["count"] == len(expected_ids)
        assert inventory["tracks"][track_name]["task_ids"] == expected_ids


def test_release_inventory_rejects_shadow_scoring_tracks() -> None:
    inventory = task_inventory("0.3.0")
    inventory["tracks"]["xtb"]["scoring_status"] = "shadow_pending_research"

    with pytest.raises(RuntimeError, match="xtb"):
        _require_formal_inventory(inventory)


def test_package_readme_uses_current_release_version() -> None:
    readme = (ROOT / "src" / "verifier_grounded_benchmark" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "verifier_grounded_benchmark-0.3.0-py3-none-any.whl" in readme
    assert "verifier_grounded_benchmark-0.1.0" not in readme
