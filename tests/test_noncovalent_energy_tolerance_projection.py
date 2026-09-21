from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/research/2026-09-21-noncovalent-energy-tolerance/project_scores.py"
spec = importlib.util.spec_from_file_location("noncovalent_projection", SCRIPT)
projection = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = projection
spec.loader.exec_module(projection)


def _scoring(track: str) -> dict:
    return yaml.safe_load(
        (ROOT / "src/verifier_grounded_benchmark/task/packs" / track / "scoring.yaml").read_text()
    )


def test_override_changes_only_the_noncovalent_family():
    for track in projection.TRACKS:
        original = _scoring(track)
        candidate = projection.candidate_scoring(original)
        family_profiles = []
        for profile_id, before in original["scoring_profiles"].items():
            after = candidate["scoring_profiles"][profile_id]
            if before.get("unit") == "kcal/mol" and before.get("property") in {
                "binding_energy", "interaction_energy", "halogen_bond_interaction_energy",
            }:
                family_profiles.append(profile_id)
                assert after["lower_tolerance"] == 2.0
                assert after["upper_tolerance"] == 2.0
                assert "error_mode" not in after
                assert "error_parameter" not in after
            else:
                assert after == before
        assert len(family_profiles) == (6 if track.endswith("basic") else 3)
        for profile_id, _before in original["scoring_profiles"].items():
            after = candidate["scoring_profiles"][profile_id]
            if profile_id in family_profiles:
                assert after["lower_tolerance"] == 2.0


def test_override_does_not_mutate_formal_input():
    original = _scoring("property_calculation_basic")
    snapshot = deepcopy(original)
    projection.candidate_scoring(original)
    assert original == snapshot
