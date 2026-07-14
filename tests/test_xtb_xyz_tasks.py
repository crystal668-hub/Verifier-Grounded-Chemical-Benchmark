from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from benchmark.answer_extraction import normalize_answer_record
from benchmark.evaluate import load_answers_jsonl, load_tasks, load_verifier_specs


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "xtb_xyz"
LEGACY_TASK_IDS = {
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
}
EXPERT_TASK_IDS = {
    "xtb_formula_dipole_min_014",
    "xtb_two_fluorine_gap_min_015",
    "xtb_c10_f2_gap_min_016",
    "xtb_roy_singlepoint_energy_min_017",
    "xtb_ritonavir_optimized_energy_min_018",
}
EXPERT_VERIFIER_IDS = {
    "xtb_dipole_doublet_gfn2_v1",
    "xtb_gap_charged_closed_shell_gfn2_v1",
    "xtb_total_energy_roy_singlepoint_gfn2_v1",
    "xtb_total_energy_ritonavir_optimized_gfn2_v1",
}


def test_xtb_xyz_tasks_define_first_batch_properties() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")

    assert set(tasks) == LEGACY_TASK_IDS | EXPERT_TASK_IDS
    assert not any("relaxation_energy_min" in task_id for task_id in tasks)
    assert set(specs) == {
        "xtb_gap_gfn2_v1",
        "xtb_dipole_gfn2_v1",
        "xtb_relaxation_energy_gfn2_v1",
        "xtb_lumo_gfn2_v1",
        "xtb_polarizability_gfn2_v1",
        "xtb_solvation_selectivity_alpb_v1",
        "xtb_electrophilicity_gfn1_ipea_v1",
        "xtb_fukui_gfn1_v1",
        "xtb_hessian_thermo_gfn2_v1",
    } | EXPERT_VERIFIER_IDS
    assert specs["xtb_gap_gfn2_v1"]["verification_script"] == "verifiers/xtb/xtb_gap.py"
    assert specs["xtb_dipole_gfn2_v1"]["verification_script"] == "verifiers/xtb/xtb_dipole.py"
    assert specs["xtb_relaxation_energy_gfn2_v1"]["verification_script"] == "verifiers/xtb/xtb_relaxation_energy.py"
    assert specs["xtb_gap_gfn2_v1"]["property_name"] == "homo_lumo_gap"
    assert specs["xtb_dipole_gfn2_v1"]["property_name"] == "dipole_moment"
    assert specs["xtb_relaxation_energy_gfn2_v1"]["property_name"] == "relaxation_energy"
    assert specs["xtb_lumo_gfn2_v1"]["property_name"] == "lumo_energy"
    assert specs["xtb_polarizability_gfn2_v1"]["property_name"] == "polarizability_per_heavy_atom"
    assert specs["xtb_solvation_selectivity_alpb_v1"]["property_name"] == "alpb_water_hexane_selectivity"
    assert specs["xtb_electrophilicity_gfn1_ipea_v1"]["property_name"] == "global_electrophilicity"
    assert specs["xtb_fukui_gfn1_v1"]["property_name"] == "max_f_plus_on_carbon"
    assert specs["xtb_hessian_thermo_gfn2_v1"]["property_name"] == "entropy_298_per_heavy_atom"
    assert specs["xtb_gap_gfn2_v1"]["backend"]["type"] == "local_xtb"
    assert specs["xtb_gap_gfn2_v1"]["backend"]["executable"] == "xtb"
    assert specs["xtb_gap_gfn2_v1"]["backend"]["method"] == "GFN2-xTB"
    assert specs["xtb_electrophilicity_gfn1_ipea_v1"]["backend"]["method"] == "GFN1-xTB/IPEA"
    assert specs["xtb_electrophilicity_gfn1_ipea_v1"]["backend"]["property_command"] == "--vomega"
    assert specs["xtb_fukui_gfn1_v1"]["backend"]["property_command"] == "--vfukui"
    assert specs["xtb_fukui_gfn1_v1"]["additional_property_names"] == ["f_plus_contrast"]
    assert specs["xtb_hessian_thermo_gfn2_v1"]["backend"]["property_command"] == "--ohess"
    assert specs["xtb_hessian_thermo_gfn2_v1"]["additional_property_names"] == ["imaginary_frequency_count"]

    for task_id, task in tasks.items():
        assert task["answer_schema"]["format"] == "final_answer_block"
        assert task["answer_schema"]["value_type"] == "xyz"
        assert task["answer_schema"]["fence_language"] == "xyz"
        assert task["formal_track"] is True
        assert "small_molecule_3d" == task["object_type"]
        assert task["scoring"]["aggregation"] == "geometric_mean"
        quality_constraints = [constraint for constraint in task["constraints"] if constraint.get("role") == "quality_gate"]
        if task_id in LEGACY_TASK_IDS:
            assert len(quality_constraints) == 1
            quality = quality_constraints[0]
            assert quality["property"] == "relaxation_energy"
            assert quality["verifier_id"] == "xtb_relaxation_energy_gfn2_v1"
            assert quality["type"] == "minimize_bounded"
            assert quality["lower"] == 0.0
            assert quality["upper"] == 0.35
        else:
            assert quality_constraints == []
            assert len(task["constraints"]) == 1
        for constraint in task["constraints"]:
            assert constraint["verifier_id"] in specs

    optimization_tasks = [
        "xtb_gap_max_003",
        "xtb_gap_min_004",
        "xtb_dipole_max_005",
        "xtb_low_gap_high_dipole_opt_006",
        "xtb_gap_dipole_window_007",
        "xtb_lumo_min_008",
        "xtb_polarizability_dipole_opt_009",
        "xtb_solvation_selectivity_alpb_010",
        "xtb_electrophilicity_max_011",
    ]
    for task_id in optimization_tasks:
        structural_domain = tasks[task_id]["structural_domain"]
        assert structural_domain["heavy_atom_count"][0] >= 6
        assert "formula_denylist" in structural_domain or "heavy_element_diversity_min" in structural_domain

    fukui_domain = tasks["xtb_fukui_carbon_site_012"]["structural_domain"]
    assert fukui_domain["heavy_atom_count"] == [4, 32]
    assert fukui_domain["carbon_count_min"] == 3
    assert fukui_domain["hetero_atom_count_min"] == 1
    assert "formula_denylist" in fukui_domain

    task_006_constraints = tasks["xtb_low_gap_high_dipole_opt_006"]["constraints"]
    gap = next(item for item in task_006_constraints if item["property"] == "homo_lumo_gap")
    dipole = next(item for item in task_006_constraints if item["property"] == "dipole_moment")
    assert gap["type"] == "minimize_bounded"
    assert gap["upper"] == 5.0
    assert dipole["type"] == "maximize_bounded"
    assert dipole["lower"] == 3.0
    assert dipole["upper"] == 8.0

    hessian_constraints = tasks["xtb_hessian_thermo_stability_013"]["constraints"]
    imaginary = next(item for item in hessian_constraints if item["property"] == "imaginary_frequency_count")
    entropy = next(item for item in hessian_constraints if item["property"] == "entropy_298_per_heavy_atom")
    assert imaginary["role"] == "stability_gate"
    assert imaginary["type"] == "window"
    assert imaginary["min"] == 0
    assert imaginary["max"] == 0
    assert entropy["type"] == "maximize_bounded"
    assert tasks["xtb_hessian_thermo_stability_013"]["structural_domain"]["heavy_atom_count"] == [4, 18]


def test_xtb_gap_max_task_uses_calibrated_high_gap_thresholds() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    gap_max = tasks["xtb_gap_max_003"]
    gap_constraint = next(item for item in gap_max["constraints"] if item["property"] == "homo_lumo_gap")
    structural_domain = gap_max["structural_domain"]

    assert gap_constraint["type"] == "maximize_bounded"
    assert gap_constraint["lower"] == 10.0
    assert gap_constraint["upper"] == 12.0
    assert structural_domain["hetero_atom_count_min"] >= 2
    assert structural_domain["heavy_element_diversity_min"] >= 3
    assert "CF4" in structural_domain["formula_denylist"]
    assert "C2F6" in structural_domain["formula_denylist"]


def test_xtb_advanced_tasks_use_calibrated_tightened_thresholds() -> None:
    from verifiers.common.scoring import score_constraint

    tasks = load_tasks(TASK_DIR / "tasks.yaml")

    lumo = next(item for item in tasks["xtb_lumo_min_008"]["constraints"] if item["property"] == "lumo_energy")
    assert lumo["type"] == "minimize_bounded"
    assert lumo["lower"] == -9.0
    assert lumo["upper"] == -6.0
    assert score_constraint({"lumo_energy": -8.5664}, lumo) == pytest.approx(0.855467, rel=1e-4)
    assert score_constraint({"lumo_energy": -8.0285}, lumo) == pytest.approx(0.676167, rel=1e-4)
    assert score_constraint({"lumo_energy": -5.607}, lumo) == 0.0

    hessian_constraints = tasks["xtb_hessian_thermo_stability_013"]["constraints"]
    entropy = next(item for item in hessian_constraints if item["property"] == "entropy_298_per_heavy_atom")
    imaginary = next(item for item in hessian_constraints if item["property"] == "imaginary_frequency_count")
    assert imaginary["role"] == "stability_gate"
    assert imaginary["min"] == 0
    assert imaginary["max"] == 0
    assert entropy["type"] == "maximize_bounded"
    assert entropy["lower"] == 50.0
    assert entropy["upper"] == 80.0
    assert score_constraint({"entropy_298_per_heavy_atom": 43.397}, entropy) == 0.0
    assert score_constraint({"entropy_298_per_heavy_atom": 65.298}, entropy) == pytest.approx(0.509933, rel=1e-4)
    assert score_constraint({"entropy_298_per_heavy_atom": 75.229}, entropy) == pytest.approx(0.840967, rel=1e-4)

    polarizability = next(
        item
        for item in tasks["xtb_polarizability_dipole_opt_009"]["constraints"]
        if item["property"] == "polarizability_per_heavy_atom"
    )
    solvation = next(
        item
        for item in tasks["xtb_solvation_selectivity_alpb_010"]["constraints"]
        if item["property"] == "alpb_water_hexane_selectivity"
    )
    electrophilicity = next(
        item
        for item in tasks["xtb_electrophilicity_max_011"]["constraints"]
        if item["property"] == "global_electrophilicity"
    )
    fukui = next(
        item
        for item in tasks["xtb_fukui_carbon_site_012"]["constraints"]
        if item["property"] == "max_f_plus_on_carbon"
    )
    assert polarizability["lower"] == 4.0
    assert polarizability["upper"] == 12.0
    assert solvation["lower"] == 0.0
    assert solvation["upper"] == 0.35
    assert score_constraint({"alpb_water_hexane_selectivity": 0.23772563040053657}, solvation) == pytest.approx(
        0.679216,
        rel=1e-4,
    )
    assert score_constraint({"alpb_water_hexane_selectivity": 0.055189565791327444}, solvation) == pytest.approx(
        0.157685,
        rel=1e-4,
    )
    assert electrophilicity["lower"] == 0.5
    assert electrophilicity["upper"] == 3.8
    assert score_constraint({"global_electrophilicity": 2.4939}, electrophilicity) == pytest.approx(0.604212, rel=1e-4)
    assert score_constraint({"global_electrophilicity": 1.8535}, electrophilicity) == pytest.approx(0.410152, rel=1e-4)
    assert fukui["lower"] == 0.05
    assert fukui["upper"] == 0.35


def test_formal_expert_tasks_match_calibrated_contracts() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")
    calibration_dir = TASK_DIR / "expert_calibration"
    calibration_tasks = load_tasks(calibration_dir / "tasks.yaml")
    calibration_specs = load_verifier_specs(calibration_dir / "verifier_specs.yaml")

    for task_id in EXPERT_TASK_IDS:
        formal = tasks[task_id]
        calibrated = calibration_tasks[task_id]
        assert formal["formal_track"] is True
        for field in (
            "prompt",
            "constraints",
            "structural_domain",
            "structure_identity",
            "scoring",
            "failure_policy",
        ):
            if field in calibrated:
                assert formal[field] == calibrated[field]
            else:
                assert field not in formal
        assert {
            key: formal["answer_schema"][key]
            for key in ("format", "final_answer_prefix", "value_type", "fence_language", "cardinality")
        } == calibrated["answer_schema"]

    for verifier_id in EXPERT_VERIFIER_IDS:
        formal = specs[verifier_id]
        calibrated = calibration_specs[verifier_id]
        assert formal["formal_track"] is True
        for field in (
            "verification_script",
            "timeout_seconds",
            "property_name",
            "resources",
            "backend",
            "domain",
        ):
            assert formal[field] == calibrated[field]


def test_formal_expert_tasks_keep_only_source_constraints() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")

    task_2 = tasks["xtb_formula_dipole_min_014"]
    task_3 = tasks["xtb_two_fluorine_gap_min_015"]
    task_4 = tasks["xtb_c10_f2_gap_min_016"]
    roy = tasks["xtb_roy_singlepoint_energy_min_017"]
    ritonavir = tasks["xtb_ritonavir_optimized_energy_min_018"]

    assert task_2["structural_domain"] == {"formula": "C12H16N3O8"}
    assert task_3["structural_domain"] == {
        "allowed_elements": ["H", "C", "O", "N", "S", "F", "Cl"],
        "atom_count": [1, 40],
        "element_count_exact": {"F": 2},
        "element_count_max": {"C": 10},
    }
    assert task_4["structural_domain"] == {
        "allowed_elements": ["H", "C", "O", "N", "S", "F", "Cl"],
        "atom_count": [1, 40],
        "element_count_exact": {"C": 10, "F": 2},
    }
    for task in (task_3, task_4):
        assert "closed-shell" in task["prompt"]
        assert "neutral" not in task["prompt"].lower()
        assert "formula_denylist" not in task["structural_domain"]
        assert "heavy_atom_count" not in task["structural_domain"]

    assert specs[task_2["constraints"][0]["verifier_id"]]["backend"] == {
        "type": "local_xtb",
        "executable": "xtb",
        "method": "GFN2-xTB",
        "charge": 0,
        "uhf": 1,
        "validate_electron_parity": True,
    }
    gap_backend = specs[task_3["constraints"][0]["verifier_id"]]["backend"]
    assert gap_backend["charge_source"] == "xyz_comment"
    assert gap_backend["uhf"] == 0
    assert roy["structure_identity"]["require_stereochemistry"] is False
    assert specs[roy["constraints"][0]["verifier_id"]]["backend"]["calculation_mode"] == "submitted_singlepoint"
    assert ritonavir["structure_identity"]["require_stereochemistry"] is True
    assert ritonavir["structure_identity"]["recheck_after_optimization"] is True
    assert specs[ritonavir["constraints"][0]["verifier_id"]]["backend"]["calculation_mode"] == "optimized"


def test_xtb_xyz_prompts_expose_domain_without_verifier_internals() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")

    required = [
        "Allowed elements: H, C, N, O, F, P, S, Cl, Br.",
        "Atom count must be between",
        "Heavy atom count must be between",
        "all hydrogens explicit",
        "chemically plausible for a neutral closed-shell small molecule",
        "physically reasonable local minimum",
        "more than about 0.35 eV of relaxation",
        "FINAL ANSWER:",
        "```xyz",
    ]
    forbidden = [
        "verifier",
        "verifier_id",
        "verifiers/",
        "sigma",
        "geometric_mean",
        "xtb_gap_gfn2_v1",
        "local xTB",
        "low-energy xTB",
        "GFN2-xTB",
        "benchmark",
    ]
    for task_id, task in tasks.items():
        prompt = task["prompt"]
        if task_id in LEGACY_TASK_IDS:
            for phrase in required:
                assert phrase in prompt
        else:
            assert "FINAL ANSWER:" in prompt
            assert "```xyz" in prompt
        for phrase in forbidden:
            assert phrase not in prompt


def test_xtb_xyz_sample_answers_use_fenced_xyz() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = load_answers_jsonl(TASK_DIR / "sample_answers.jsonl")

    assert answers
    for answer in answers:
        assert answer["task_id"] in tasks
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        assert normalized.ok
        assert normalized.answer is not None
        candidate = normalized.answer["candidates"][0]
        assert "xyz" in candidate
        lines = candidate["xyz"].splitlines()
        assert int(lines[0]) == len(lines) - 2


def test_xtb_verifier_specs_are_yaml_loadable() -> None:
    with (TASK_DIR / "verifier_specs.yaml").open() as handle:
        payload = yaml.safe_load(handle)

    assert len(payload["verifiers"]) == 13
    assert payload["verifiers"][0]["domain"]["allowed_elements"] == ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br"]
    relaxation = next(item for item in payload["verifiers"] if item["verifier_id"] == "xtb_relaxation_energy_gfn2_v1")
    assert relaxation["property"]["role"] == "geometry_quality_gate"
