from __future__ import annotations

from importlib.resources import files

import pytest
import yaml

from verifier_grounded_benchmark.evaluation.open_generation.parsing.dispatcher import normalize_answer_record
from verifier_grounded_benchmark.evaluation.open_generation.scoring import score_constraint_value
from verifier_grounded_benchmark.task.loader import (
    load_answers_jsonl_file as load_answers_jsonl,
    load_task_pack,
    load_tasks_file as load_tasks,
    load_verifier_specs_file as load_verifier_specs,
)
from verifier_grounded_benchmark.task.resources import package_resource


TASKS_RESOURCE = package_resource("xtb", "tasks.yaml")
SPECS_RESOURCE = package_resource("xtb", "verifier_specs.yaml")
ANSWERS_RESOURCE = package_resource("xtb", "sample_answers.jsonl")


def load_xtb_pack():
    return load_task_pack(TASKS_RESOURCE, SPECS_RESOURCE)
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
    "xtb_odd_element_counts_gap_max_019",
    "xtb_pyrene_substituent_energy_min_020",
}
CALIBRATED_EXPERT_TASK_IDS = {
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
    "xtb_odd_element_gap_dipole_gfn2_v1",
    "xtb_pyrene_crest_energy_v1",
}
CALIBRATED_EXPERT_VERIFIER_IDS = {
    "xtb_dipole_doublet_gfn2_v1",
    "xtb_gap_charged_closed_shell_gfn2_v1",
    "xtb_total_energy_roy_singlepoint_gfn2_v1",
    "xtb_total_energy_ritonavir_optimized_gfn2_v1",
}


def test_xtb_xyz_tasks_define_first_batch_properties() -> None:
    pack = load_xtb_pack()
    tasks = pack.tasks_by_id
    specs = pack.verifier_specs_by_id

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
    assert specs["xtb_gap_gfn2_v1"]["executor"]["module"].endswith(".xtb.xtb_gap")
    assert specs["xtb_dipole_gfn2_v1"]["executor"]["module"].endswith(".xtb.xtb_dipole")
    assert specs["xtb_relaxation_energy_gfn2_v1"]["executor"]["module"].endswith(
        ".xtb.xtb_relaxation_energy"
    )
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
        assert task["formal_track"] is True
        assert task["scoring"]["aggregation"] == "geometric_mean"
        if task_id == "xtb_pyrene_substituent_energy_min_020":
            assert task["answer_schema"]["format"] == "final_answer_line"
            assert task["answer_schema"]["value_type"] == "smiles"
            assert task["object_type"] == "small_molecule"
        else:
            assert task["answer_schema"]["format"] == "final_answer_block"
            assert task["answer_schema"]["value_type"] == "xyz"
            assert task["answer_schema"]["fence_language"] == "xyz"
            assert task["object_type"] == "small_molecule_3d"
        quality_constraints = [constraint for constraint in task["constraints"] if constraint.get("role") == "quality_gate"]
        if task_id in LEGACY_TASK_IDS:
            assert len(quality_constraints) == 1
            quality = quality_constraints[0]
            assert quality["property"] == "relaxation_energy"
            assert quality["verifier_id"] == "xtb_relaxation_energy_gfn2_v1"
            assert quality["type"] == "minimize"
            profile = pack.scoring_profiles[quality["scoring_profile"]]
            assert profile["full_score_target"] == 0.05
            assert profile["zero_score_anchor"] == 0.35
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
    assert gap["type"] == "minimize"
    assert pack.scoring_profiles[gap["scoring_profile"]]["zero_score_anchor"] == pytest.approx(9.749630028571)
    assert dipole["type"] == "maximize"
    dipole_profile = pack.scoring_profiles[dipole["scoring_profile"]]
    assert dipole_profile["zero_score_anchor"] == pytest.approx(3.32)
    assert dipole_profile["full_score_target"] == pytest.approx(13.374)

    hessian_constraints = tasks["xtb_hessian_thermo_stability_013"]["constraints"]
    imaginary = next(item for item in hessian_constraints if item["property"] == "imaginary_frequency_count")
    entropy = next(item for item in hessian_constraints if item["property"] == "entropy_298_per_heavy_atom")
    assert imaginary["role"] == "stability_gate"
    assert imaginary["type"] == "window"
    imaginary_profile = pack.scoring_profiles[imaginary["scoring_profile"]]
    assert imaginary_profile["full_score"] == {"min": 0, "max": 0}
    assert entropy["type"] == "maximize"
    assert tasks["xtb_hessian_thermo_stability_013"]["structural_domain"]["heavy_atom_count"] == [4, 18]


def test_xtb_gap_max_task_uses_literature_reviewed_thresholds() -> None:
    pack = load_xtb_pack()
    tasks = pack.tasks_by_id
    gap_max = tasks["xtb_gap_max_003"]
    gap_constraint = next(item for item in gap_max["constraints"] if item["property"] == "homo_lumo_gap")
    structural_domain = gap_max["structural_domain"]

    assert gap_constraint["type"] == "maximize"
    profile = pack.scoring_profiles[gap_constraint["scoring_profile"]]
    assert profile["zero_score_anchor"] == pytest.approx(1.389963462368)
    assert profile["full_score_target"] == pytest.approx(9.749630028571)
    assert structural_domain["hetero_atom_count_min"] >= 2
    assert structural_domain["heavy_element_diversity_min"] >= 3
    assert "CF4" in structural_domain["formula_denylist"]
    assert "C2F6" in structural_domain["formula_denylist"]


def test_xtb_advanced_tasks_use_literature_reviewed_thresholds() -> None:
    pack = load_xtb_pack()
    tasks = pack.tasks_by_id

    lumo = next(item for item in tasks["xtb_lumo_min_008"]["constraints"] if item["property"] == "lumo_energy")
    assert lumo["type"] == "minimize"
    lumo_profile = pack.scoring_profiles[lumo["scoring_profile"]]
    assert lumo_profile["full_score_target"] == -10.6883
    assert lumo_profile["zero_score_anchor"] == -1.94
    assert score_constraint_value(-8.5664, lumo_profile) == pytest.approx(0.75745, rel=1e-4)
    assert score_constraint_value(-8.0285, lumo_profile) == pytest.approx(0.695964, rel=1e-4)
    assert score_constraint_value(-1.0, lumo_profile) == 0.0

    hessian_constraints = tasks["xtb_hessian_thermo_stability_013"]["constraints"]
    entropy = next(item for item in hessian_constraints if item["property"] == "entropy_298_per_heavy_atom")
    imaginary = next(item for item in hessian_constraints if item["property"] == "imaginary_frequency_count")
    assert imaginary["role"] == "stability_gate"
    imaginary_profile = pack.scoring_profiles[imaginary["scoring_profile"]]
    assert imaginary_profile["full_score"] == {"min": 0, "max": 0}
    assert entropy["type"] == "maximize"
    entropy_profile = pack.scoring_profiles[entropy["scoring_profile"]]
    assert entropy_profile["zero_score_anchor"] == pytest.approx(40.59789)
    assert entropy_profile["full_score_target"] == pytest.approx(76.094775)
    assert score_constraint_value(43.397, entropy_profile) == pytest.approx(0.078855, rel=1e-4)
    assert score_constraint_value(65.298, entropy_profile) == pytest.approx(0.695839, rel=1e-4)
    assert score_constraint_value(75.229, entropy_profile) == pytest.approx(0.97561, rel=1e-4)

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
    polarizability_profile = pack.scoring_profiles[polarizability["scoring_profile"]]
    assert polarizability_profile["zero_score_anchor"] == pytest.approx(6.4845643)
    assert polarizability_profile["full_score_target"] == pytest.approx(9.3430346)
    solvation_profile = pack.scoring_profiles[solvation["scoring_profile"]]
    assert solvation_profile["zero_score_anchor"] == pytest.approx(-0.17228322475548233)
    assert solvation_profile["full_score_target"] == pytest.approx(0.3953163242456749)
    assert score_constraint_value(0.23772563040053657, solvation_profile) == pytest.approx(
        0.722356,
        rel=1e-4,
    )
    assert score_constraint_value(0.055189565791327444, solvation_profile) == pytest.approx(
        0.400763,
        rel=1e-4,
    )
    electrophilicity_profile = pack.scoring_profiles[electrophilicity["scoring_profile"]]
    assert electrophilicity_profile["zero_score_anchor"] == pytest.approx(0.4862)
    assert electrophilicity_profile["full_score_target"] == pytest.approx(3.1359)
    assert score_constraint_value(2.4939, electrophilicity_profile) == pytest.approx(0.757708, rel=1e-4)
    assert score_constraint_value(1.8535, electrophilicity_profile) == pytest.approx(0.516021, rel=1e-4)
    fukui_profile = pack.scoring_profiles[fukui["scoring_profile"]]
    assert fukui_profile["zero_score_anchor"] == pytest.approx(0.076)
    assert fukui_profile["full_score_target"] == pytest.approx(0.276)


def test_formal_expert_tasks_match_calibrated_contracts() -> None:
    formal_pack = load_xtb_pack()
    calibration_dir = files("verifier_grounded_benchmark.task.calibration.xtb")
    calibration_pack = load_task_pack(
        calibration_dir.joinpath("tasks.yaml"),
        calibration_dir.joinpath("verifier_specs.yaml"),
    )
    tasks = formal_pack.tasks_by_id
    specs = formal_pack.verifier_specs_by_id
    calibration_tasks = calibration_pack.tasks_by_id
    calibration_specs = calibration_pack.verifier_specs_by_id

    for task_id in CALIBRATED_EXPERT_TASK_IDS:
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
        for constraint in calibrated["constraints"]:
            profile_id = constraint["scoring_profile"]
            assert calibration_pack.scoring_profiles[profile_id] == formal_pack.scoring_profiles[profile_id]
        assert {
            key: formal["answer_schema"][key]
            for key in ("format", "final_answer_prefix", "value_type", "fence_language", "cardinality")
        } == calibrated["answer_schema"]

    for verifier_id in CALIBRATED_EXPERT_VERIFIER_IDS:
        formal = specs[verifier_id]
        calibrated = calibration_specs[verifier_id]
        assert formal["formal_track"] is True
        for field in (
            "executor",
            "property_name",
            "resources",
            "backend",
            "domain",
        ):
            assert formal[field] == calibrated[field]


def test_formal_expert_tasks_keep_only_source_constraints() -> None:
    pack = load_xtb_pack()
    tasks = pack.tasks_by_id
    specs = pack.verifier_specs_by_id

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


def test_xtb_prompts_expose_domain_without_verifier_internals() -> None:
    tasks = load_xtb_pack().tasks_by_id

    required = [
        "Allowed elements: H, C, N, O, F, P, S, Cl, Br.",
        "Atom count must be between",
        "Heavy atom count must be between",
        "all hydrogens explicit",
        "chemically plausible for a neutral closed-shell small molecule",
        "physically reasonable local minimum",
            "relaxation energy at or below 0.05 eV",
            "more than about 0.35 eV will receive little or no credit",
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
            if task["answer_schema"]["value_type"] == "xyz":
                assert "```xyz" in prompt
            else:
                assert "<SMILES>" in prompt
        for phrase in forbidden:
            assert phrase not in prompt


def test_xtb_sample_answers_follow_each_task_schema() -> None:
    tasks = load_xtb_pack().tasks_by_id
    answers = load_answers_jsonl(ANSWERS_RESOURCE)

    assert answers
    for answer in answers:
        assert answer["task_id"] in tasks
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        assert normalized.ok
        assert normalized.answer is not None
        candidate = normalized.answer["candidates"][0]
        if tasks[answer["task_id"]]["answer_schema"]["value_type"] == "xyz":
            assert "xyz" in candidate
            lines = candidate["xyz"].splitlines()
            assert int(lines[0]) == len(lines) - 2
        else:
            assert candidate.get("smiles")


def test_xtb_verifier_specs_are_yaml_loadable() -> None:
    payload = yaml.safe_load(SPECS_RESOURCE.read_text(encoding="utf-8"))

    assert len(payload["verifiers"]) == 15
    assert payload["verifiers"][0]["domain"]["allowed_elements"] == ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br"]
    relaxation = next(item for item in payload["verifiers"] if item["verifier_id"] == "xtb_relaxation_energy_gfn2_v1")
    assert relaxation["property"]["role"] == "geometry_quality_gate"
