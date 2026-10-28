from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import verifier_grounded_benchmark as vgb
from verifier_grounded_benchmark.cli.score_answers import main
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource


def test_cli_retains_report_and_fails_when_verifier_cannot_execute(tmp_path):
    name = "open_generation_rdkit"
    for filename in ("tasks.yaml", "scoring.yaml", "verifier_specs.yaml"):
        data = yaml.safe_load(package_resource(name, filename).read_text())
        if filename == "verifier_specs.yaml":
            for spec in data["verifiers"]:
                spec["executor"]["module"] = "vgb_nonexistent_rc_test_verifier"
        else:
            data["tasks"] = data["tasks"][:1]
        (tmp_path / filename).write_text(yaml.safe_dump(data))
    answer = json.loads((Path(__file__).parent / "fixtures/open_generation_rdkit_regression_answers.jsonl").read_text().splitlines()[0])
    answers = tmp_path / "answers.jsonl"
    answers.write_text(json.dumps(answer) + "\n")
    result = subprocess.run(
        [sys.executable, "-m", "verifier_grounded_benchmark.cli.score_answers",
         "--tasks", str(tmp_path / "tasks.yaml"),
         "--specs", str(tmp_path / "verifier_specs.yaml"),
         "--scoring", str(tmp_path / "scoring.yaml"),
         "--answers", str(answers), "--require-complete"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["summary"]["coverage"]["complete"]
    assert report["summary"]["num_error"] == 1
    assert report["summary"]["benchmark_score"] is None
    assert report["rows"][0]["failure_type"] == "verifier_tool_error"


@pytest.mark.parametrize("invalid", [10**400, -(10**400), float("nan"), float("inf"), True])
def test_numeric_outliers_do_not_abort_complete_batch(tmp_path, capsys, invalid):
    track = vgb.load_track("property_calculation_basic")
    answers = []
    for task in track.tasks():
        gold = track.task(task["task_id"], include_gold=True)["gold_answers"][0]
        answers.append({"task_id": task["task_id"], "answers": [
            {key: gold[key] for key in ("property", "value", "unit") if key in gold}
        ]})
    answers[0]["answers"][0]["value"] = invalid
    path = tmp_path / "answers.jsonl"
    path.write_text("\n".join(json.dumps(answer) for answer in answers))
    assert main(["--track", track.name, "--answers", str(path), "--require-complete"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["summary"]["num_error"] == 0
    assert report["summary"]["coverage"]["complete"]
    assert [row["score"] for row in report["rows"]] == [0.0] + [1.0] * 50


@pytest.mark.parametrize(("field", "bad"), [
    ("task_pack_id", "another_pack"), ("task_pack_version", "999.0.0"),
    ("task_pack_id", None), ("task_pack_version", None),
])
def test_scoring_must_identify_the_loaded_pack(tmp_path, field, bad):
    name = "property_calculation_basic"
    data = yaml.safe_load(package_resource(name, "scoring.yaml").read_text())
    data["scoring_config"][field] = bad
    path = tmp_path / "scoring.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match=field):
        load_task_pack(package_resource(name, "tasks.yaml"), None, path)


@pytest.mark.parametrize("filename", ["tasks.yaml", "scoring.yaml", "verifier_specs.yaml"])
def test_duplicate_yaml_keys_report_resource_and_line(tmp_path, filename):
    paths = {}
    for name in ("tasks.yaml", "scoring.yaml", "verifier_specs.yaml"):
        text = package_resource("open_generation_rdkit", name).read_text()
        if name == filename:
            text += "\naudit_duplicate: 1\naudit_duplicate: 2\n"
        paths[name] = tmp_path / name
        paths[name].write_text(text)
    with pytest.raises(ValueError, match="duplicate YAML key: audit_duplicate") as exc:
        load_task_pack(paths["tasks.yaml"], paths["verifier_specs.yaml"], paths["scoring.yaml"])
    assert str(Path(tmp_path) / filename) in str(exc.value)
    assert "line" in str(exc.value)
