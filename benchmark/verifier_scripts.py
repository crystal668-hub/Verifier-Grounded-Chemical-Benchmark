from __future__ import annotations

import json
import os
import subprocess
import sys
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
        for key in ("task_id", "version", "object_type")
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
    completed = subprocess.run(
        [python_executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        return {
            "task_id": payload.get("task", {}).get("task_id"),
            "status": "error",
            "failure_type": "verifier_tool_error",
            "message": completed.stderr.strip() or completed.stdout.strip() or f"{script} exited {completed.returncode}",
            "properties": {},
            "scores": {
                "validity_gate": 0.0,
                "domain_gate": 0.0,
                "constraint_scores": [],
                "property_score": 0.0,
                "score": 0.0,
            },
            "versions": {},
        }
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {
            "task_id": payload.get("task", {}).get("task_id"),
            "status": "error",
            "failure_type": "verifier_tool_error",
            "message": f"verification script produced invalid JSON: {exc.msg}",
            "properties": {},
            "scores": {
                "validity_gate": 0.0,
                "domain_gate": 0.0,
                "constraint_scores": [],
                "property_score": 0.0,
                "score": 0.0,
            },
            "versions": {},
        }
    return result
