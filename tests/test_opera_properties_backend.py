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


def test_parse_opera_output_reads_wide_property_and_applicability_domain_flag() -> None:
    properties = parse_opera_output("ID,WS,AD_WS\ncandidate,-1.25,1\n", "WS")

    assert properties["WS"] == pytest.approx(-1.25)
    assert properties["AD_WS"] == 1


def test_parse_opera_output_maps_single_endpoint_pred_and_ad_columns() -> None:
    output = "MoleculeID,SMILES,pred,AD,AD_index\ncandidate,CCO,-1.25,1,0.8\n"

    properties = parse_opera_output(output, "WS")

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


def test_evaluate_opera_constraint_bad_configured_executable_includes_path(tmp_path) -> None:
    missing_executable = tmp_path / "missing_opera"
    candidate, task, constraint, spec = payload()
    spec["opera"] = {"executable": os.fspath(missing_executable), "mcr_directory": os.fspath(tmp_path)}

    result = evaluate_opera_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert os.fspath(missing_executable) in result["message"]


def test_evaluate_opera_constraint_missing_mcr_directory_maps_to_environment_error(
    tmp_path,
) -> None:
    executable = tmp_path / "fake_opera"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(executable.stat().st_mode | 0o111)
    candidate, task, constraint, spec = payload()
    spec["opera"] = {"executable": os.fspath(executable), "endpoint": "WS"}

    result = evaluate_opera_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert "mcr" in result["message"].lower()


def test_evaluate_opera_constraint_bad_mcr_directory_includes_path(tmp_path) -> None:
    executable = tmp_path / "fake_opera"
    missing_mcr_directory = tmp_path / "missing-mcr"
    executable.write_text("#!/bin/sh\nexit 99\n")
    executable.chmod(executable.stat().st_mode | 0o111)
    candidate, task, constraint, spec = payload()
    spec["opera"] = {"executable": os.fspath(executable), "mcr_directory": os.fspath(missing_mcr_directory)}

    result = evaluate_opera_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert os.fspath(missing_mcr_directory) in result["message"]


def test_evaluate_opera_constraint_runs_fake_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    executable = tmp_path / "fake_opera"
    mcr_directory = tmp_path / "mcr"
    mcr_directory.mkdir()
    executable.write_text(
        "#!/bin/sh\n"
        "test \"$1\" = \"$OPERA_EXPECTED_MCR\" || exit 17\n"
        "shift\n"
        "while [ \"$#\" -gt 0 ]; do\n"
        "  case \"$1\" in\n"
        "    --Output|-o) output=\"$2\"; shift 2 ;;\n"
        "    --Endpoint|-e) endpoint=\"$2\"; shift 2 ;;\n"
        "    --SMI|-s) input=\"$2\"; shift 2 ;;\n"
        "    *) exit 18 ;;\n"
        "  esac\n"
        "done\n"
        "test \"$endpoint\" = \"WS\" || exit 19\n"
        "test -s \"$input\" || exit 20\n"
        "cat > \"$output\" <<'CSV'\n"
        "MoleculeID,SMILES,pred,AD,AD_index\n"
        "candidate,CCO,-1.25,1,0.8\n"
        "CSV\n"
    )
    executable.chmod(executable.stat().st_mode | 0o111)
    candidate, task, constraint, spec = payload()
    spec["opera"] = {
        "executable": os.fspath(executable),
        "mcr_directory": os.fspath(mcr_directory),
        "endpoint": "WS",
    }
    monkeypatch.setenv("OPERA_EXPECTED_MCR", os.fspath(mcr_directory))

    result = evaluate_opera_constraint(candidate, task, constraint, spec)

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["WS"] == pytest.approx(-1.25)
    assert result["properties"]["AD_WS"] == 1


def test_evaluate_opera_constraint_ad_zero_sets_domain_gate_and_score_to_zero(tmp_path) -> None:
    executable = tmp_path / "fake_opera"
    mcr_directory = tmp_path / "mcr"
    mcr_directory.mkdir()
    executable.write_text(
        "#!/bin/sh\n"
        "shift\n"
        "while [ \"$#\" -gt 0 ]; do\n"
        "  case \"$1\" in\n"
        "    --Output|-o) output=\"$2\"; shift 2 ;;\n"
        "    --Endpoint|-e|--SMI|-s) shift 2 ;;\n"
        "    *) exit 18 ;;\n"
        "  esac\n"
        "done\n"
        "cat > \"$output\" <<'CSV'\n"
        "MoleculeID,SMILES,pred,AD\n"
        "candidate,CCO,-1.25,0\n"
        "CSV\n"
    )
    executable.chmod(executable.stat().st_mode | 0o111)
    candidate, task, constraint, spec = payload()
    spec["opera"] = {"executable": os.fspath(executable), "mcr_directory": os.fspath(mcr_directory)}

    result = evaluate_opera_constraint(candidate, task, constraint, spec)

    assert result["status"] == "ok"
    assert result["properties"]["AD_WS"] == 0
    assert result["scores"]["property_score"] == pytest.approx(1.0)
    assert result["scores"]["domain_gate"] == 0.0
    assert result["scores"]["score"] == 0.0
