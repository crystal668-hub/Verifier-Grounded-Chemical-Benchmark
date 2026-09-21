import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from review_system.source import load_catalog, schema_view, source_revision, split_attachments

def test_catalog_contains_formal_tracks_and_hides_long_inputs():
    catalog = load_catalog()
    assert {track["name"] for track in catalog["tracks"]} == {"open_generation_rdkit", "open_generation_xtb", "property_calculation_basic", "property_calculation_advanced"}
    assert sum(len(track["tasks"]) for track in catalog["tracks"]) == 105
    for track in catalog["tracks"]:
        for task in track["tasks"]:
            assert task["fingerprint"]
            assert "content" not in task["view"].get("attachments", {})
            for input_object in task["schema"].get("input_objects", []):
                value = input_object.get("value")
                assert not isinstance(value, str) or len(value.strip()) < 80

def test_attachment_split_replaces_body_with_reference():
    view, attachments = split_attachments({"task_id":"demo", "prompt":"Input:\n```xyz\n" + "C 0 0 0\n" * 30 + "```"})
    assert "[附件：demo-1.xyz]" in view["prompt"]
    assert attachments[0]["content"].startswith("C 0 0 0")


def test_source_revision_prefers_deployment_commit(monkeypatch):
    monkeypatch.setenv("REVIEW_SOURCE_COMMIT", "abc1234")
    assert source_revision() == "abc1234"


def test_schema_view_uses_attachment_reference_from_sanitized_task():
    raw = {
        "task_id": "demo",
        "input_objects": [{"object_id": "structure", "type": "xyz", "value": "C 0 0 0\n" * 30}],
    }
    view, _attachments = split_attachments(raw)
    schema = schema_view(view)
    assert schema["input_objects"][0]["value"] is None
    assert schema["input_objects"][0]["attachment_ref"] == "demo-1.xyz"


def test_scoring_view_exposes_answers_ranges_and_multi_field_rules():
    catalog = load_catalog()
    advanced = next(track for track in catalog["tracks"] if track["name"] == "property_calculation_advanced")
    phase_task = next(task for task in advanced["tasks"] if task["task_id"].endswith("002_crystal_phase"))
    scoring = phase_task["scoring"]
    assert scoring["is_multi_field"] is True
    assert scoring["field_count"] == 3
    answers = {rule["property"]: rule for rule in scoring["rules"]}
    assert answers["ambient_pressure_phase"]["standard_answer"] == "alpha"
    assert answers["ambient_pressure_phase"]["full_score_region"]["kind"] == "exact"
    assert answers["potential_energy_difference"]["full_score_region"]["kind"] == "point"
    assert answers["potential_energy_difference"]["score_range"] == {
        "kind": "interval",
        "min": 0.0,
        "max": 0.879,
        "min_exclusive": False,
        "max_exclusive": True,
        "unit": "eV",
    }

    rdkit = next(track for track in catalog["tracks"] if track["name"] == "open_generation_rdkit")
    qed = next(task for task in rdkit["tasks"] if task["task_id"] == "rdkit_001_qed_max")
    assert qed["scoring"]["rules"][0]["profile"]["full_score_target"] == 1.0


def test_full_score_intervals_are_limited_to_window_profiles():
    catalog = load_catalog()
    interval_rules = [
        rule
        for track in catalog["tracks"]
        for task in track["tasks"]
        for rule in task["scoring"]["rules"]
        if rule.get("full_score_region", {}).get("kind") == "interval"
    ]
    assert interval_rules
    assert all(rule["type"] == "window" for rule in interval_rules)
    assert all(rule["score_range"]["kind"] == "interval" for rule in interval_rules)
    assert all(rule["score_range"]["min_exclusive"] and rule["score_range"]["max_exclusive"] for rule in interval_rules)


def test_score_ranges_represent_nonzero_submitted_values():
    catalog = load_catalog()
    tasks = {
        task["task_id"]: task
        for track in catalog["tracks"]
        for task in track["tasks"]
    }
    qed = tasks["rdkit_001_qed_max"]["scoring"]["rules"][0]["score_range"]
    assert qed == {"kind": "lower_bounded", "min": 0.0, "min_exclusive": True, "unit": "dimensionless"}

    interaction = tasks["property_calculation_advanced_008_interaction_binding_energy"]["scoring"]["rules"][0]["score_range"]
    assert interaction["kind"] == "absolute_interval"
    assert interaction["min"] == pytest.approx(59.04)
    assert interaction["max"] == pytest.approx(79.04)

    log_score = tasks["property_calculation_advanced_015_formaldehyde_socme"]["scoring"]["rules"][0]["score_range"]
    assert log_score["transform"] == "log10"
    assert log_score["min"] == 0.0007340000000000001
    assert log_score["max"] == 0.0734


def test_v0100_catalog_has_task_specific_widths_and_absolute_scoring():
    catalog = load_catalog()
    count = 0
    for track in catalog["tracks"]:
        assert track["version"] == "0.10.0"
        for task in track["tasks"]:
            for rule in task["scoring"]["rules"]:
                profile = rule["profile"]
                if profile.get("provenance", {}).get("tolerance_family") == "noncovalent_energy":
                    count += 1
                    advanced = track["name"] == "property_calculation_advanced"
                    number = task["task_id"].split("_")[3]
                    width = ({"008": 10.0, "013": 5.0}[number] if advanced
                             else 3.0 if number == "013" else 2.0)
                    assert profile["lower_tolerance"] == profile["upper_tolerance"] == width
                    assert profile.get("value_transform", "identity") == ("absolute" if advanced else "identity")
                    assert rule["score_range"]["kind"] == ("absolute_interval" if advanced else "interval")
            if task["task_id"] in {"property_calculation_advanced_008_interaction_binding_energy", "property_calculation_advanced_013_halogen_bond_energy"}:
                assert "Preserve the sign of the energy." not in task["view"]["prompt"]
            if task["task_id"] == "property_calculation_advanced_002_crystal_phase":
                assert task["scoring"]["comparison_groups"][1]["aggregation"] == "all_correct"
    assert count == 9
