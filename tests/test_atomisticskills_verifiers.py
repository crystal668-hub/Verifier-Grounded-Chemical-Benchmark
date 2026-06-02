from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark.evaluate import evaluate_many, load_answers_jsonl, load_tasks, load_verifier_specs
from verifiers import atomisticskills
from verifiers.atomisticskills import (
    evaluate_base_supercell,
    evaluate_drugdisc_descriptors,
    evaluate_xrd_peak,
)
from verifiers.registry import get_verifier


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "atomisticskills_smoke"


def base_task() -> dict:
    return {
        "task_id": "atomisticskills_base_supercell_001",
        "constraints": [{"type": "exact", "property": "atom_count", "value": 4}],
    }


def base_spec(tmp_path: Path) -> dict:
    return {
        "verifier_id": "atomisticskills_base_supercell_mcp_v1",
        "fixture": {"structure_path": str(tmp_path / "Si.cif")},
        "tool": {"server": "base", "name": "supercell_expansion"},
        "expected": {"atom_count": 4, "reduced_formula": "Si"},
        "scoring": {"aggregation": "all_or_nothing"},
    }


def test_registry_resolves_atomisticskills_verifiers() -> None:
    assert get_verifier("atomisticskills_base_supercell_mcp_v1") is evaluate_base_supercell
    assert get_verifier("atomisticskills_drugdisc_descriptors_mcp_v1") is evaluate_drugdisc_descriptors
    assert get_verifier("atomisticskills_xrd_peak_script_v1") is evaluate_xrd_peak


def test_atomisticskills_smoke_tasks_are_experimental_non_formal() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")

    for task in tasks.values():
        assert "experimental_smoke" in task["capability_tags"]
        assert task["formal_track"] is False

    for spec in specs.values():
        assert spec["formal_track"] is False
        assert spec["backend"]["type"] in {"mcp", "script"}


def test_base_supercell_verifier_scores_fake_mcp_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    input_cif = tmp_path / "Si.cif"
    output_cif = tmp_path / "out" / "Si_supercell.cif"
    input_cif.write_text("fixture")

    class FakeMCPAdapter:
        def __init__(self, server_name: str) -> None:
            assert server_name == "base"

        def call_tool(self, tool_name: str, arguments: dict, timeout_seconds: float = 60.0) -> str:
            assert tool_name == "supercell_expansion"
            assert json.loads(arguments["scaling_matrix_json"]) == [2, 1, 1]
            output_cif.parent.mkdir(parents=True)
            output_cif.write_text("generated")
            return f"Successfully created supercell. Saved to {output_cif}"

    monkeypatch.setattr(atomisticskills, "AtomisticSkillsMCPAdapter", FakeMCPAdapter)
    monkeypatch.setattr(
        atomisticskills,
        "inspect_structure",
        lambda path: {"atom_count": 4, "reduced_formula": "Si"},
    )

    result = evaluate_base_supercell(
        {"task_id": "atomisticskills_base_supercell_001", "candidates": [{"json": {"scaling_matrix": [2, 1, 1]}}]},
        base_task(),
        base_spec(tmp_path),
    )

    assert result["status"] == "ok"
    assert result["properties"] == {"atom_count": 4, "reduced_formula": "Si"}
    assert result["scores"]["score"] == 1.0


def test_base_supercell_verifier_reports_parse_error_for_bad_matrix(tmp_path: Path) -> None:
    result = evaluate_base_supercell(
        {"task_id": "atomisticskills_base_supercell_001", "candidates": [{"json": {"scaling_matrix": [2, 0, 1]}}]},
        base_task(),
        base_spec(tmp_path),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0


def test_drugdisc_descriptor_verifier_scores_fake_mcp_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    descriptor_file = tmp_path / "descriptors.json"
    descriptor_file.write_text(
        json.dumps(
            {
                "descriptors": [
                    {
                        "valid": True,
                        "smiles": "CCO",
                        "qed": 0.41,
                        "logp": -0.0,
                        "tpsa": 20.23,
                        "molecular_weight": 46.07,
                    }
                ]
            }
        )
    )

    class FakeMCPAdapter:
        def __init__(self, server_name: str) -> None:
            assert server_name == "drugdisc"

        def call_tool(self, tool_name: str, arguments: dict, timeout_seconds: float = 60.0) -> dict:
            if tool_name == "standardize_molecule":
                return {"success": True, "standardized_smiles": "CCO"}
            if tool_name == "compute_molecular_descriptors":
                Path(arguments["output_file"]).write_text(descriptor_file.read_text())
                return {"success": True, "output_file": arguments["output_file"]}
            raise AssertionError(tool_name)

    monkeypatch.setattr(atomisticskills, "AtomisticSkillsMCPAdapter", FakeMCPAdapter)
    spec = {
        "verifier_id": "atomisticskills_drugdisc_descriptors_mcp_v1",
        "domain": {"allowed_elements": ["C", "H", "O"], "single_component": True},
        "tool": {"server": "drugdisc"},
    }
    task = {
        "task_id": "atomisticskills_drugdisc_descriptor_001",
        "constraints": [{"type": "window", "property": "qed", "min": 0.3, "max": 0.5, "sigma": 0.1}],
    }

    result = evaluate_drugdisc_descriptors(
        {"task_id": task["task_id"], "candidates": [{"smiles": "CCO"}]},
        task,
        spec,
    )

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["qed"] == 0.41
    assert result["scores"]["score"] == 1.0


def test_xrd_peak_verifier_scores_fake_script_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    xrd_json = tmp_path / "out" / "Si_xrd.json"
    xrd_json.parent.mkdir()
    xrd_json.write_text(json.dumps({"x": [20.0, 28.44, 47.3], "y": [5.0, 100.0, 30.0]}))

    class FakeScriptAdapter:
        def run_xrd_calculator(self, structure_path: str, output_dir: str, wavelength: str, timeout_seconds: float) -> Path:
            assert wavelength == "CuKa"
            return xrd_json

    monkeypatch.setattr(atomisticskills, "AtomisticSkillsScriptAdapter", FakeScriptAdapter)
    spec = {
        "verifier_id": "atomisticskills_xrd_peak_script_v1",
        "fixture": {"structure_path": str(tmp_path / "Si.cif")},
        "xrd": {"wavelength": "CuKa", "target_peak": "max_intensity", "tolerance_degrees": 0.1},
    }
    task = {"task_id": "atomisticskills_xrd_peak_001", "constraints": []}

    result = evaluate_xrd_peak(
        {"task_id": task["task_id"], "candidates": [{"value": 28.46, "raw_value": "28.46"}]},
        task,
        spec,
    )

    assert result["status"] == "ok"
    assert result["properties"]["target_two_theta"] == 28.44
    assert result["scores"]["score"] == pytest.approx(0.8)


def test_atomisticskills_smoke_sample_answers_route_when_adapters_are_faked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")
    answers = load_answers_jsonl(TASK_DIR / "sample_answers.jsonl")

    class FakeMCPAdapter:
        def __init__(self, server_name: str) -> None:
            self.server_name = server_name

        def call_tool(self, tool_name: str, arguments: dict, timeout_seconds: float = 60.0):
            if self.server_name == "base":
                out = tmp_path / "base" / "Si_supercell.cif"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text("generated")
                return f"Successfully created supercell. Saved to {out}"
            if self.server_name == "drugdisc" and tool_name == "standardize_molecule":
                return {"success": True, "standardized_smiles": "CCO"}
            if self.server_name == "drugdisc" and tool_name == "compute_molecular_descriptors":
                Path(arguments["output_file"]).write_text(
                    json.dumps(
                        {
                            "descriptors": [
                                {
                                    "valid": True,
                                    "smiles": "CCO",
                                    "qed": 0.41,
                                    "logp": -0.0,
                                    "tpsa": 20.23,
                                    "molecular_weight": 46.07,
                                }
                            ]
                        }
                    )
                )
                return {"success": True, "output_file": arguments["output_file"]}
            raise AssertionError((self.server_name, tool_name))

    class FakeScriptAdapter:
        def run_xrd_calculator(self, structure_path: str, output_dir: str, wavelength: str, timeout_seconds: float) -> Path:
            out = tmp_path / "xrd" / "Si_xrd.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"x": [20.0, 28.44, 47.3], "y": [5.0, 100.0, 30.0]}))
            return out

    monkeypatch.setattr(atomisticskills, "AtomisticSkillsMCPAdapter", FakeMCPAdapter)
    monkeypatch.setattr(atomisticskills, "AtomisticSkillsScriptAdapter", FakeScriptAdapter)
    monkeypatch.setattr(atomisticskills, "inspect_structure", lambda path: {"atom_count": 4, "reduced_formula": "Si"})

    report = evaluate_many(answers, tasks, specs)

    assert report["summary"]["num_answers"] == 3
    assert report["summary"]["num_ok"] == 3
    assert report["summary"]["num_error"] == 0
