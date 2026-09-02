from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from verifier_grounded_benchmark import load_track
from verifier_grounded_benchmark.evaluation.external_dependencies import (
    ExternalDependencyError,
    preflight_external_dependencies,
    verifier_specs_for_answers,
)
from verifier_grounded_benchmark.evaluation.open_generation.verification import runner
from verifier_grounded_benchmark.task.schema.verifier import validate_verifier_specs


def _dependency_spec(
    executable: str,
    version: str,
    *,
    conda_environment: str | None = None,
) -> dict[str, object]:
    dependency = {"executable": executable, "version": version}
    if conda_environment is not None:
        dependency["conda_environment"] = conda_environment
    return {"external_dependencies": [dependency]}


def _write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def test_preflight_connects_named_conda_environment(tmp_path: Path) -> None:
    command_dir = tmp_path / "commands"
    command_dir.mkdir()
    environment_prefix = tmp_path / "envs" / "vgb-crest"
    environment_bin = environment_prefix / "bin"
    environment_bin.mkdir(parents=True)
    _write_executable(
        command_dir / "conda",
        f"printf '%s\\n' {json.dumps(json.dumps({'envs': [str(environment_prefix)]}))}",
    )
    _write_executable(environment_bin / "crest", "echo 'Version 2.12, test build'")
    environ = {"PATH": str(command_dir)}

    checks = preflight_external_dependencies(
        [_dependency_spec("crest", "2.12", conda_environment="vgb-crest")],
        environ=environ,
    )

    assert checks[0]["status"] == "ok"
    assert checks[0]["resolved_path"] == str(environment_bin / "crest")
    assert environ["PATH"].split(os.pathsep)[0] == str(environment_bin)


def test_preflight_rejects_wrong_version(tmp_path: Path) -> None:
    command_dir = tmp_path / "commands"
    command_dir.mkdir()
    _write_executable(command_dir / "xtb", "echo 'xtb version 6.6.0'")

    with pytest.raises(ExternalDependencyError) as raised:
        preflight_external_dependencies(
            [_dependency_spec("xtb", "6.7.1")],
            environ={"PATH": str(command_dir)},
        )

    assert raised.value.checks[0]["status"] == "error"
    assert "does not match required 6.7.1" in raised.value.checks[0]["message"]


def test_preflight_reports_missing_named_environment(tmp_path: Path) -> None:
    with pytest.raises(ExternalDependencyError) as raised:
        preflight_external_dependencies(
            [_dependency_spec("crest", "2.12", conda_environment="vgb-crest")],
            environ={"PATH": str(tmp_path)},
        )

    assert raised.value.checks[0]["status"] == "error"
    assert "Conda environment vgb-crest" in raised.value.checks[0]["message"]


def test_verifier_selection_uses_only_submitted_tasks() -> None:
    track = load_track("xtb")

    regular = verifier_specs_for_answers(
        track._task_pack.tasks_by_id,
        track.verifier_specs_by_id,
        [{"task_id": "xtb_gap_window_001"}],
    )
    conformer_search = verifier_specs_for_answers(
        track._task_pack.tasks_by_id,
        track.verifier_specs_by_id,
        [{"task_id": "xtb_pyrene_substituent_energy_min_020"}],
    )

    assert {
        dependency["executable"]
        for spec in regular
        for dependency in spec["external_dependencies"]
    } == {"xtb"}
    assert {
        dependency["executable"]
        for spec in conformer_search
        for dependency in spec["external_dependencies"]
    } == {"crest", "xtb"}


def test_verifier_schema_rejects_incomplete_external_dependency() -> None:
    with pytest.raises(ValueError, match="version must be a non-empty string"):
        validate_verifier_specs(
            [
                {
                    "verifier_id": "example_v1",
                    "external_dependencies": [{"executable": "example"}],
                }
            ]
        )


def test_subprocess_verifier_stops_before_launch_when_preflight_fails(
    monkeypatch,
) -> None:
    failure = ExternalDependencyError(
        [
            {
                "executable": "crest",
                "status": "error",
                "message": "required executable crest was not found",
            }
        ]
    )
    monkeypatch.setattr(
        runner,
        "preflight_external_dependencies",
        lambda specs, environ: (_ for _ in ()).throw(failure),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("verifier subprocess must not start"),
    )

    evidence = runner.SubprocessPropertyVerifier().verify(
        {"smiles": "C"},
        {"task_id": "example_task"},
        {"property": "energy"},
        {
            "verifier_id": "example_v1",
            "property_name": "energy",
            "external_dependencies": [{"executable": "crest", "version": "2.12"}],
            "executor": {"type": "python_module", "module": "example.verifier"},
        },
    )

    assert evidence.outcome == "evaluation_failed"
    assert evidence.failure_type == "verifier_environment_error"
    assert evidence.failure_scope == "infrastructure"
