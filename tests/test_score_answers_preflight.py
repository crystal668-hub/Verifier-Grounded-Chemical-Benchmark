from __future__ import annotations

import json
from pathlib import Path

from verifier_grounded_benchmark.cli import score_answers
from verifier_grounded_benchmark.evaluation.external_dependencies import (
    ExternalDependencyError,
)


def test_cli_reports_preflight_failure_before_evaluation(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    answers_path = tmp_path / "answers.jsonl"
    answers_path.write_text(
        json.dumps({"task_id": "xtb_020_pyrene_substituent_energy_min", "response": "FINAL ANSWER: C"})
        + "\n",
        encoding="utf-8",
    )
    failure = ExternalDependencyError(
        [
            {
                "executable": "crest",
                "expected_version": "2.12",
                "status": "error",
                "message": "required executable crest was not found",
            }
        ]
    )
    def reject_missing_dependency(specs):
        assert {dependency["executable"] for spec in specs
                for dependency in spec.get("external_dependencies", [])} == {"xtb", "crest"}
        raise failure

    monkeypatch.setattr(score_answers, "preflight_external_dependencies", reject_missing_dependency)

    exit_code = score_answers.main(
        ["--track", "open_generation_xtb", "--answers", str(answers_path)]
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["error"] == "verifier_environment_error"
    assert payload["dependencies"][0]["executable"] == "crest"
