from __future__ import annotations

import json

import pytest
import yaml

import verifier_grounded_benchmark as vgb
from verifier_grounded_benchmark.cli import score_answers
from verifier_grounded_benchmark.evaluation import EvaluationEngine
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.registry import TrackDefinition
from verifier_grounded_benchmark.task.resources import package_resource
from verifier_grounded_benchmark.track import Track

PROPERTY_TRACKS = ("property_calculation_basic", "property_calculation_advanced")
OPEN_TRACKS = ("open_generation_rdkit", "open_generation_xtb")


def fail_verifier(*args, **kwargs):
    raise AssertionError("property calculation must not invoke a verifier or dependency preflight")


@pytest.mark.parametrize("name", PROPERTY_TRACKS)
def test_property_track_loads_and_scores_all_gold_without_verifiers(name, monkeypatch):
    definition = TrackDefinition(
        name=name, version="0.10.0", display_name=name,
        task_pack_path="tasks.yaml", scoring_config_path="scoring.yaml", resource_pack=name,
    )
    assert definition.verifier_specs_path is None
    assert not package_resource(name, "verifier_specs.yaml").is_file()
    pack = load_task_pack(package_resource(name, "tasks.yaml"))
    assert pack.verifier_specs_by_id == {}
    track = Track(definition)
    assert track.verifier_specs_by_id == {}
    engine = EvaluationEngine(pack)
    monkeypatch.setattr(engine._open_generation, "evaluate", fail_verifier)
    for task in pack.tasks:
        answer = {"task_id": task.task_id, "answers": [
            {key: gold[key] for key in ("property", "value", "unit") if key in gold}
            for gold in task.raw["gold_answers"]
        ]}
        assert engine.evaluate_one(answer)["scores"]["score"] == 1


@pytest.mark.parametrize("name", PROPERTY_TRACKS)
@pytest.mark.parametrize("custom_pack", [False, True])
def test_property_cli_needs_no_specs_or_external_preflight(name, custom_pack, tmp_path, monkeypatch, capsys):
    track = vgb.load_track(name)
    task = track.task(track.tasks()[0]["task_id"], include_gold=True)
    answer = {"task_id": task["task_id"], "answers": [
        {key: gold[key] for key in ("property", "value", "unit") if key in gold}
        for gold in task["gold_answers"]
    ]}
    answers = tmp_path / "answers.jsonl"
    answers.write_text(json.dumps(answer) + "\n")
    monkeypatch.setattr(score_answers, "preflight_external_dependencies", fail_verifier)
    args = ["--answers", str(answers)]
    if custom_pack:
        for filename in ("tasks.yaml", "scoring.yaml"):
            (tmp_path / filename).write_text(package_resource(name, filename).read_text())
        args += ["--tasks", str(tmp_path / "tasks.yaml"), "--scoring", str(tmp_path / "scoring.yaml")]
    else:
        args += ["--track", name]
    assert score_answers.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["rows"][0]["score"] == 1


@pytest.mark.parametrize("name", OPEN_TRACKS)
def test_open_generation_still_requires_valid_verifier_specs(name, tmp_path):
    tasks = package_resource(name, "tasks.yaml")
    with pytest.raises(ValueError, match="verifier specs are required"):
        load_task_pack(tasks)
    empty_specs = tmp_path / "empty.yaml"
    empty_specs.write_text("verifiers: []\n")
    with pytest.raises(ValueError, match="unknown verifier_id"):
        load_task_pack(tasks, empty_specs)


def test_mixed_pack_cannot_omit_verifier_specs(tmp_path):
    payload = yaml.safe_load(package_resource("property_calculation_basic", "tasks.yaml").read_text())
    generated = yaml.safe_load(package_resource("open_generation_rdkit", "tasks.yaml").read_text())
    payload["tasks"].append(generated["tasks"][0])
    path = tmp_path / "tasks.yaml"
    path.write_text(yaml.safe_dump(payload))
    with pytest.raises(ValueError, match="verifier specs are required"):
        load_task_pack(path)


@pytest.mark.parametrize("args", [
    ["--tasks", "tasks.yaml"],
    ["--scoring", "scoring.yaml"],
    ["--specs", "specs.yaml"],
    ["--track", "property_calculation_basic", "--specs", "specs.yaml"],
])
def test_cli_rejects_incomplete_or_conflicting_pack_options(args):
    with pytest.raises(SystemExit):
        score_answers.parse_args(["--answers", "answers.jsonl", *args])


def test_mixed_suite_keeps_property_scoring_independent_of_open_generation(monkeypatch):
    suite = vgb.load_suite([*OPEN_TRACKS, *PROPERTY_TRACKS])
    assert len(suite.tasks()) == 105
    engine = suite.evaluator().engine
    monkeypatch.setattr(engine._open_generation, "evaluate", fail_verifier)
    result = engine.evaluate_one({
        "task_id": "property_calculation_advanced_013_halogen_bond_energy",
        "answer": 17.11, "unit": "kcal/mol",
    })
    assert result["scores"]["score"] == 1
