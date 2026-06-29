from __future__ import annotations

import os
from typing import Any

import pytest

from verifiers.backends.opera_properties import evaluate_opera_constraint, parse_opera_output


def payload() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    task = {"task_id": "opera_ws_001", "version": 1, "object_type": "small_molecule"}
    constraint = {
        "type": "window",
        "property": "WS",
        "verifier_id": "opera_ws_v1",
        "min": -2.0,
        "max": -1.0,
        "sigma": 1.0,
    }
    spec = {
        "verifier_id": "opera_ws_v1",
        "property_name": "WS",
        "verifier_image": "verifier-grounded:dev",
        "domain": {
            "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [1, 80],
            "mw": [1.0, 1000.0],
            "formal_charge": [-2, 2],
        },
    }
    candidate = {"smiles": "CCO"}
    return candidate, task, constraint, spec


def test_parse_opera_output_reads_property_and_applicability_domain_flag() -> None:
    properties = parse_opera_output("ID,WS,AD_WS\ncandidate,-1.25,1\n", "WS")

    assert properties["WS"] == pytest.approx(-1.25)
    assert properties["AD_WS"] == 1


def test_evaluate_opera_constraint_missing_executable_maps_to_environment_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPERA_EXECUTABLE", raising=False)
    monkeypatch.setenv("PATH", "")
    candidate, task, constraint, spec = payload()

    result = evaluate_opera_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"


def test_evaluate_opera_constraint_runs_fake_executable(
    tmp_path,
) -> None:
    executable = tmp_path / "fake_opera"
    executable.write_text(
        "#!/bin/sh\n"
        "cat > \"$2\" <<'CSV'\n"
        "ID,WS,AD_WS\n"
        "candidate,-1.25,1\n"
        "CSV\n"
    )
    executable.chmod(executable.stat().st_mode | 0o111)
    candidate, task, constraint, spec = payload()
    spec["opera"] = {"executable": os.fspath(executable), "model": "WS"}

    result = evaluate_opera_constraint(candidate, task, constraint, spec)

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["WS"] == pytest.approx(-1.25)
    assert result["properties"]["AD_WS"] == 1
