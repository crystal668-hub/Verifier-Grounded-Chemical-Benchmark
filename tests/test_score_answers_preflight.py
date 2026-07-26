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
        json.dumps({"task_id": "rdkit_qed_max_001", "response": "FINAL ANSWER: C"})
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
    monkeypatch.setattr(
        score_answers,
        "preflight_external_dependencies",
        lambda specs: (_ for _ in ()).throw(failure),
    )

    exit_code = score_answers.main(
        ["--track", "rdkit", "--answers", str(answers_path)]
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["error"] == "verifier_environment_error"
    assert payload["dependencies"][0]["executable"] == "crest"
