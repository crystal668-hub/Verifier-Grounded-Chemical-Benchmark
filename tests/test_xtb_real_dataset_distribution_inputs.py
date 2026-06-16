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


def test_xtb_real_dataset_source_manifest_records_machine_access_paths() -> None:
    with SOURCE_MANIFEST.open() as handle:
        payload = yaml.safe_load(handle)

    sources = payload["sources"]
    qmugs = sources["qmugs"]
    assert qmugs["access"]["type"] == "nextcloud_public_webdav"
    assert qmugs["access"]["webdav_url"].endswith("/public.php/webdav/")
    assert "structures.tar.gz" in qmugs["access"]["files"]

    geom = sources["geom_drugs"]
    assert geom["access"]["type"] == "harvard_dataverse"
    assert geom["access"]["persistent_id"] == "doi:10.7910/DVN/JNGTDF"
    assert "censo.tar.gz" in geom["access"]["small_validation_files"]

    opv = sources["tartarus_opv"]
    assert opv["access"]["status"] == "manual_or_generated_geometry_required"


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


def test_convert_xtb_real_dataset_sdf_to_jsonl_file_and_tar(tmp_path) -> None:
    import tarfile

    sdf_text = """water
  unit

  3  2  0  0  0  0            999 V2000
    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    0.7586    0.0000    0.5043 H   0  0  0  0  0  0  0  0  0  0  0  0
   -0.7586    0.0000    0.5043 H   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  1  3  1  0
M  END
>  <SOURCE_ID>
unit_water

$$$$
"""
    sdf = tmp_path / "fixture.sdf"
    sdf.write_text(sdf_text)
    output = tmp_path / "out.jsonl"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/convert_xtb_real_dataset_sdf.py",
            "--input",
            str(sdf),
            "--dataset-name",
            "unit_sdf",
            "--output-jsonl",
            str(output),
            "--limit",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert rows[0]["dataset_name"] == "unit_sdf"
    assert rows[0]["record_id"] == "unit_water"
    assert rows[0]["xyz"].startswith("3\n")

    archive = tmp_path / "fixture.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(sdf, arcname="nested/fixture.sdf")
    tar_output = tmp_path / "tar_out.jsonl"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/convert_xtb_real_dataset_sdf.py",
            "--input",
            str(archive),
            "--dataset-name",
            "unit_tar",
            "--output-jsonl",
            str(tar_output),
            "--limit",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    rows = [json.loads(line) for line in tar_output.read_text().splitlines()]
    assert rows[0]["dataset_name"] == "unit_tar"
    assert rows[0]["geometry_source"] == "sdf_3d"


def test_convert_xtb_real_dataset_sdf_filters_tar_members_and_reports_summary(tmp_path) -> None:
    import tarfile

    sdf_text = """methanol
  unit

  6  5  0  0  0  0            999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.4300    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3600    1.0200    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3600   -0.5100    0.8833 H   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3600   -0.5100   -0.8833 H   0  0  0  0  0  0  0  0  0  0  0  0
    1.7500    0.0000    0.9000 H   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  1  3  1  0
  1  4  1  0
  1  5  1  0
  2  6  1  0
M  END
>  <PUBCHEM_COMPOUND_CID>
887

$$$$
"""
    keep = tmp_path / "keep.sdf"
    keep.write_text(sdf_text)
    skip = tmp_path / "skip.sdf"
    skip.write_text(sdf_text.replace("887", "999"))
    archive = tmp_path / "fixture.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(keep, arcname="wanted/keep.sdf")
        handle.add(skip, arcname="ignored/skip.sdf")

    output = tmp_path / "out.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/convert_xtb_real_dataset_sdf.py",
            "--input",
            str(archive),
            "--dataset-name",
            "qmugs",
            "--output-jsonl",
            str(output),
            "--member-name-contains",
            "wanted/",
            "--record-id-property",
            "PUBCHEM_COMPOUND_CID",
            "--limit",
            "5",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    summary = json.loads(completed.stdout)
    assert summary["members_seen"] == 2
    assert summary["members_selected"] == 1
    assert summary["written"] == 1
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert rows[0]["record_id"] == "887"
    assert rows[0]["source_file"] == "wanted/keep.sdf"


def test_prepare_xtb_real_dataset_sample_intermediate_writes_tier_files(tmp_path) -> None:
    def record(dataset_name: str, record_id: str, xyz: str) -> dict[str, object]:
        return {
            "dataset_name": dataset_name,
            "record_id": record_id,
            "xyz": xyz,
            "charge": 0,
            "multiplicity": 1,
            "geometry_source": "fixture_xyz",
        }

    methane = "5\nmethane\nC 0 0 0\nH 0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH -0.63 0.63 -0.63\nH 0.63 -0.63 -0.63\n"
    methanol = "12\nmethanol\nC 0 0 0\nC 1.54 0 0\nC 3.08 0 0\nO 4.51 0 0\nH -0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH 1.54 0.89 -0.63\nH 1.54 -0.89 -0.63\nH 3.08 0.89 0.63\nH 3.08 -0.89 0.63\nH 4.82 0.75 -0.48\nH 4.82 -0.75 -0.48\n"
    ethane = "14\nethane\nC 0 0 0\nC 1.54 0 0\nC 3.08 0 0\nC 4.62 0 0\nH -0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH -0.63 0 -0.89\nH 1.54 0.89 -0.63\nH 1.54 -0.89 -0.63\nH 3.08 0.89 0.63\nH 3.08 -0.89 0.63\nH 5.25 0.63 0.63\nH 5.25 -0.63 0.63\nH 5.25 0 -0.89\n"
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                record("qm9", "methane", methane),
                record("qm9", "methanol", methanol),
                record("qmugs", "ethane", ethane),
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
            "20260615",
            "--intermediate",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    manifest = json.loads((output_dir / "sample_manifest.json").read_text())
    assert manifest["mode"] == "intermediate"
    assert (output_dir / "sampled_records.light.jsonl").exists()
    assert (output_dir / "sampled_records.medium.jsonl").exists()
    assert (output_dir / "sampled_records.expensive.jsonl").exists()
    expensive = [json.loads(line) for line in (output_dir / "sampled_records.expensive.jsonl").read_text().splitlines()]
    assert [row["record_id"] for row in expensive] == ["methanol", "ethane"]
