import json
from pathlib import Path

import pytest

import verifier_grounded_benchmark as vgb
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "task_backups/2026-10-28-five-tasks"
RETIRED = {
    "rdkit_002_sa_min", "rdkit_005_hba_window", "rdkit_006_hbd_window",
    "rdkit_007_fsp3_max", "property_calculation_advanced_004_ir_top2_frequencies",
}


def test_formal_suite_is_contiguous_and_excludes_retired_tasks():
    expected_counts = {
        "open_generation_rdkit": 10,
        "open_generation_xtb": 20,
        "property_calculation_basic": 51,
        "property_calculation_advanced": 19,
    }
    assert len(vgb.load_suite().tasks()) == 100
    for name, count in expected_counts.items():
        track = vgb.load_track(name)
        ids = [t["task_id"] for t in track.tasks()]
        assert len(ids) == count
        assert RETIRED.isdisjoint(ids)
        index = 1 if name.startswith("open_generation_") else 3
        assert [int(t.split("_")[index]) for t in ids] == list(range(1, count + 1))
        for retired_id in RETIRED:
            with pytest.raises(KeyError):
                track.task(retired_id)
        if name == "open_generation_rdkit":
            assert [s["task_id"] for s in track.sample_answers()] == ids


def test_retired_backups_are_loadable_and_mapping_preserves_order():
    manifest = json.loads((BACKUP / "manifest.json").read_text())
    assert set(manifest["retired_task_ids"]) == RETIRED
    restored = set()
    for name in manifest["tracks"]:
        folder = BACKUP / name
        pack = load_task_pack(
            folder / "tasks.yaml",
            folder / "verifier_specs.yaml" if name.startswith("open_generation_") else None,
            folder / "scoring.yaml",
        )
        restored.update(t.task_id for t in pack.tasks)
        formal = vgb.load_track(name)
        prefix = "rdkit_" if name == "open_generation_rdkit" else "property_calculation_advanced_"
        mapped = [new for old, new in manifest["id_mapping"].items() if old.startswith(prefix)]
        assert mapped == [t["task_id"] for t in formal.tasks()]
    assert restored == RETIRED


def test_shared_verifiers_and_profiles_survive_retirement():
    pack = load_task_pack(
        package_resource("open_generation_rdkit", "tasks.yaml"),
        package_resource("open_generation_rdkit", "verifier_specs.yaml"),
    )
    expected = {
        "rdkit_004_qed_sa": {("rdkit_sa_score_v1", "rdkit_sa_score_minimize_1p0_10p0_v2")},
        "rdkit_006_hba_hbd": {
            ("rdkit_hba_v1", "rdkit_hba_window_2_4_2p0_v2"),
            ("rdkit_hbd_v1", "rdkit_hbd_window_1_2_1p0_v2"),
        },
    }
    for task_id, dependencies in expected.items():
        actual = {(c["verifier_id"], c["scoring_profile"]) for c in pack.tasks_by_id[task_id]["constraints"]}
        assert dependencies <= actual
        for verifier, profile in dependencies:
            assert verifier in pack.verifier_specs_by_id
            assert profile in pack.scoring_profiles
    assert "rdkit_fraction_csp3_v1" not in pack.verifier_specs_by_id
    assert "rdkit_fraction_csp3_maximize_0p0_1p0_v2" not in pack.scoring_profiles
    advanced = load_task_pack(package_resource("property_calculation_advanced", "tasks.yaml"))
    assert not any(key.startswith("property_calculation_advanced_ir_frequency_") for key in advanced.scoring_profiles)
