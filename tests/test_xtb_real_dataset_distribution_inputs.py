from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data" / "xtb_real_dataset_sources.yaml"


def test_xtb_real_dataset_source_manifest_exists() -> None:
    assert SOURCE_MANIFEST.exists()


def test_xtb_real_dataset_source_manifest_defines_required_sources() -> None:
    with SOURCE_MANIFEST.open() as handle:
        payload = yaml.safe_load(handle)

    assert payload["version"] == 1
    sources = payload["sources"]
    assert {"qm9", "qmugs", "geom_drugs", "tartarus_opv"}.issubset(sources)
    assert sources["qm9"]["status"] == "required"
    assert sources["qmugs"]["status"] == "required"
    assert sources["geom_drugs"]["status"] == "required_for_conformer_subset"
    assert sources["tartarus_opv"]["status"] == "optional_if_unavailable"
    for source in sources.values():
        assert source["url"].startswith("https://")
        assert source["cache_path"].startswith(".cache/xtb_real_datasets/")
        assert "license_note" in source


def test_prepare_xtb_real_dataset_sample_help() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/prepare_xtb_real_dataset_sample.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--source-manifest" in completed.stdout
    assert "--output-dir" in completed.stdout
    assert "--seed" in completed.stdout
    assert "--pilot" in completed.stdout


def test_prepare_xtb_real_dataset_sample_can_process_tiny_fixture(tmp_path) -> None:
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "dataset_name": "unit_fixture",
                        "record_id": "water",
                        "xyz": "3\nwater\nO 0 0 0\nH 0.758602 0 0.504284\nH -0.758602 0 0.504284\n",
                        "charge": 0,
                        "multiplicity": 1,
                        "geometry_source": "fixture_xyz",
                    }
                ),
                json.dumps(
                    {
                        "dataset_name": "unit_fixture",
                        "record_id": "methanol",
                        "xyz": "6\nmethanol\nC 0 0 0\nO 1.43 0 0\nH -0.36 1.02 0\nH -0.36 -0.51 0.883346\nH -0.36 -0.51 -0.883346\nH 1.75 0 0.9\n",
                        "charge": 0,
                        "multiplicity": 1,
                        "geometry_source": "fixture_xyz",
                    }
                ),
            ]
        )
        + "\n"
    )
    output_dir = tmp_path / "out"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_xtb_real_dataset_sample.py",
            "--input-jsonl",
            str(fixture),
            "--output-dir",
            str(output_dir),
            "--seed",
            "123",
            "--pilot",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    sampled = [json.loads(line) for line in (output_dir / "sampled_records.jsonl").read_text().splitlines()]
    assert [row["record_id"] for row in sampled] == ["water", "methanol"]
    assert sampled[0]["dataset_name"] == "unit_fixture"
    assert "heavy_atom_count" in sampled[0]
