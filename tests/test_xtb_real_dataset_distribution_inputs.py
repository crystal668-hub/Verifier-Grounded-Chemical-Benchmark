from __future__ import annotations

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
