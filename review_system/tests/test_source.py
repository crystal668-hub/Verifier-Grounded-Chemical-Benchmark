import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from review_system.source import load_catalog, split_attachments

def test_catalog_contains_formal_tracks_and_hides_long_inputs():
    catalog = load_catalog()
    assert {track["name"] for track in catalog["tracks"]} == {"rdkit", "xtb", "property_calculation_basic", "property_calculation_advanced"}
    assert sum(len(track["tasks"]) for track in catalog["tracks"]) == 105
    for track in catalog["tracks"]:
        for task in track["tasks"]:
            assert task["fingerprint"]
            assert "content" not in task["view"].get("attachments", {})

def test_attachment_split_replaces_body_with_reference():
    view, attachments = split_attachments({"task_id":"demo", "prompt":"Input:\n```xyz\n" + "C 0 0 0\n" * 30 + "```"})
    assert "[附件：demo-1.xyz]" in view["prompt"]
    assert attachments[0]["content"].startswith("C 0 0 0")


def test_scoring_view_exposes_answers_ranges_and_multi_field_rules():
    catalog = load_catalog()
    advanced = next(track for track in catalog["tracks"] if track["name"] == "property_calculation_advanced")
    phase_task = next(task for task in advanced["tasks"] if task["task_id"].endswith("002_crystal_phase"))
    scoring = phase_task["scoring"]
    assert scoring["is_multi_field"] is True
    assert scoring["field_count"] == 3
    answers = {rule["property"]: rule for rule in scoring["rules"]}
    assert answers["ambient_pressure_phase"]["standard_answer"] == "alpha"
    assert answers["ambient_pressure_phase"]["score_range"]["kind"] == "精确匹配"
    assert answers["potential_energy_difference"]["score_range"]["min"] == -0.921

    rdkit = next(track for track in catalog["tracks"] if track["name"] == "rdkit")
    qed = next(task for task in rdkit["tasks"] if task["task_id"] == "rdkit_qed_max_001")
    assert qed["scoring"]["rules"][0]["profile"]["full_score_target"] == 1.0
