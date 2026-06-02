from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def build_script_payload(answer: dict[str, Any], task: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    candidates = answer.get("candidates")
    candidate = candidates[0] if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict) else {}
    return {"task": task, "verifier_spec": spec, "candidate": candidate}


def run_verification_script(
    script_path: str | Path,
    payload: dict[str, Any],
    *,
    timeout_seconds: float,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    script = Path(script_path)
    completed = subprocess.run(
        [python_executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
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
