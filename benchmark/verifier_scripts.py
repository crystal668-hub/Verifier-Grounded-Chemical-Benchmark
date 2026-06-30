from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def build_script_payload(
    answer: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    candidates = answer.get("candidates")
    candidate = candidates[0] if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict) else {}
    task_payload = {
        key: task[key]
        for key in ("task_id", "version", "object_type", "structural_domain")
        if key in task
    }
    return {"task": task_payload, "constraint": constraint, "verifier_spec": spec, "candidate": candidate}


def run_verification_script(
    script_path: str | Path,
    payload: dict[str, Any],
    *,
    timeout_seconds: float,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    script = Path(script_path)
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    try:
        completed = subprocess.run(
            [python_executable, str(script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return verifier_execution_error(
            payload,
            "verifier_timeout",
            f"{script} timed out after {timeout_seconds:g} seconds",
        )
    if completed.returncode != 0:
        return verifier_execution_error(
            payload,
            "verifier_tool_error",
            completed.stderr.strip()
            or completed.stdout.strip()
            or f"{script} exited {completed.returncode}",
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return verifier_execution_error(
            payload,
            "verifier_tool_error",
            f"verification script produced invalid JSON: {exc.msg}",
        )
    validation = validate_verification_result(result)
    if not validation.ok:
        return verifier_execution_error(
            payload,
            "verifier_tool_error",
            f"verification script returned invalid result: {validation.message}",
        )
    return result


@dataclass(frozen=True)
class ResultValidation:
    ok: bool
    message: str | None = None


def validate_verification_result(result: Any) -> ResultValidation:
    if not isinstance(result, dict):
        return ResultValidation(False, "expected JSON object")

    status = result.get("status")
    if status not in {"ok", "error"}:
        return ResultValidation(False, "status must be 'ok' or 'error'")

    task_id = result.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        return ResultValidation(False, "task_id must be a non-empty string")

    properties = result.get("properties")
    if not isinstance(properties, dict):
        return ResultValidation(False, "properties must be an object")

    scores = result.get("scores")
    if not isinstance(scores, dict):
        return ResultValidation(False, "scores must be an object")
    if not isinstance(scores.get("score"), int | float):
        return ResultValidation(False, "scores.score must be a number")
    if not isinstance(scores.get("constraint_scores"), list):
        return ResultValidation(False, "scores.constraint_scores must be a list")

    if status == "error":
        failure_type = result.get("failure_type")
        message = result.get("message")
        if not isinstance(failure_type, str) or not failure_type:
            return ResultValidation(False, "error result must include failure_type")
        if not isinstance(message, str) or not message:
            return ResultValidation(False, "error result must include message")

    return ResultValidation(True)


def verifier_execution_error(
    payload: dict[str, Any],
    failure_type: str,
    message: str,
) -> dict[str, Any]:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    spec = (
        payload.get("verifier_spec")
        if isinstance(payload.get("verifier_spec"), dict)
        else {}
    )
    return {
        "task_id": task.get("task_id"),
        "verifier_id": spec.get("verifier_id"),
        "status": "error",
        "canonical_smiles": None,
        "properties": {},
        "scores": {
            "validity_gate": 0.0,
            "domain_gate": 0.0,
            "constraint_scores": [],
            "property_score": 0.0,
            "score": 0.0,
        },
        "failure_type": failure_type,
        "message": message,
        "versions": {},
    }
