"""Subprocess verifier execution normalized into score-free evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from verifier_grounded_benchmark.evaluation.open_generation.verification.evidence import (
    VerificationEvidence,
)
from verifier_grounded_benchmark.task.resources import resolve_script_path, source_root


CANDIDATE_FAILURES = {
    "parse_error",
    "validity_error",
    "domain_error",
    "identity_error",
    "structure_identity_error",
}
TASK_FAILURES = {"task_error", "verifier_spec_error"}


class SubprocessPropertyVerifier:
    def __init__(self, *, python_executable: str = sys.executable) -> None:
        self.python_executable = python_executable

    def verify(
        self,
        candidate: dict[str, Any],
        task: Mapping[str, Any],
        constraint: Mapping[str, Any],
        spec: Mapping[str, Any],
    ) -> VerificationEvidence:
        payload = {
            "task": {
                key: _plain(task[key])
                for key in ("task_id", "version", "object_type", "structural_domain", "structure_identity")
                if key in task
            },
            "constraint": _plain(constraint),
            "verifier_spec": _plain(spec),
            "candidate": candidate,
        }
        timeout = _timeout(spec)
        command = self._command(spec)
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(source_root()) if not pythonpath else f"{source_root()}{os.pathsep}{pythonpath}"
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return self._failed(payload, "verifier_timeout", f"verifier timed out after {timeout:g} seconds")
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or f"verifier exited {completed.returncode}"
            return self._failed(payload, "verifier_tool_error", message)
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            return self._failed(payload, "verifier_tool_error", f"verifier produced invalid JSON: {exc.msg}")
        return self._normalize_result(result, payload)

    def _command(self, spec: Mapping[str, Any]) -> list[str]:
        executor = spec.get("executor")
        if isinstance(executor, Mapping):
            if executor.get("type") != "python_module":
                raise ValueError(f"unsupported verifier executor: {executor.get('type')}")
            module = executor.get("module")
            if not isinstance(module, str) or not module:
                raise ValueError("python_module executor requires module")
            return [self.python_executable, "-m", module]
        script = spec.get("verification_script")
        if not isinstance(script, str) or not script:
            raise ValueError("verifier spec requires executor or verification_script")
        return [self.python_executable, str(resolve_script_path(script, source_root()))]

    def _normalize_result(
        self, result: Any, payload: dict[str, Any]
    ) -> VerificationEvidence:
        task_id = str(payload["task"].get("task_id"))
        verifier_id = str(payload["verifier_spec"].get("verifier_id"))
        candidate = payload["candidate"]
        if not isinstance(result, dict):
            return self._failed(payload, "verifier_tool_error", "verifier result must be an object")
        if result.get("outcome") in {"verified", "candidate_rejected", "evaluation_failed"}:
            properties = result.get("properties")
            if not isinstance(properties, dict):
                return self._failed(payload, "verifier_tool_error", "evidence properties must be an object")
            return VerificationEvidence(
                outcome=result["outcome"],
                task_id=task_id,
                verifier_id=verifier_id,
                canonical_candidate=result.get("canonical_candidate") or candidate,
                properties=properties,
                diagnostics=result.get("diagnostics") or {},
                versions=result.get("versions") or {},
                failure_type=result.get("failure_type"),
                message=result.get("message"),
                failure_scope=result.get("failure_scope"),
            )
        status = result.get("status")
        properties = result.get("properties")
        if status == "ok" and isinstance(properties, dict):
            canonical = candidate
            if result.get("canonical_smiles") is not None:
                canonical = {"smiles": result["canonical_smiles"]}
            return VerificationEvidence(
                "verified",
                task_id,
                verifier_id,
                canonical,
                properties,
                versions=result.get("versions") or {},
            )
        if status == "error":
            failure_type = str(result.get("failure_type") or "verifier_tool_error")
            message = str(result.get("message") or "verifier failed")
            if failure_type in CANDIDATE_FAILURES:
                return VerificationEvidence(
                    "candidate_rejected",
                    task_id,
                    verifier_id,
                    candidate,
                    properties if isinstance(properties, dict) else {},
                    failure_type=failure_type,
                    message=message,
                    failure_scope="candidate",
                    versions=result.get("versions") or {},
                )
            return self._failed(payload, failure_type, message)
        return self._failed(payload, "verifier_tool_error", "verifier result has invalid outcome/status")

    def _failed(
        self, payload: dict[str, Any], failure_type: str, message: str
    ) -> VerificationEvidence:
        scope = "task" if failure_type in TASK_FAILURES else "infrastructure"
        return VerificationEvidence(
            "evaluation_failed",
            str(payload["task"].get("task_id")),
            str(payload["verifier_spec"].get("verifier_id")),
            payload["candidate"],
            {},
            failure_type=failure_type,
            message=message,
            failure_scope=scope,
        )


def _timeout(spec: Mapping[str, Any]) -> float:
    executor = spec.get("executor")
    if isinstance(executor, Mapping) and executor.get("timeout_seconds") is not None:
        return float(executor["timeout_seconds"])
    return float(spec.get("timeout_seconds", 60.0))


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value
