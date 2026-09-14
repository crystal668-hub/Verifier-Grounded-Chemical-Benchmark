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
