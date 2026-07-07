# SolTranNet + MolGpKa Backends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Docker-backed SolTranNet and MolGpKa verifier backends with property scripts, diagnostics, tests, and separate backend docs.

**Architecture:** Keep the existing verifier script contract: each property script reads stdin JSON and writes standardized JSON. Backend evaluators handle SMILES validation, domain gates, model prediction, and scoring. Model execution goes through a narrow Docker runtime adapter now, with the same backend interfaces ready for a future `runtime: local` implementation inside the official verifier image.

**Tech Stack:** Python 3.12, RDKit, pytest, stdlib `subprocess`/`urllib.request`, local Docker Desktop for opt-in smoke tests.

---

## File Structure

- Create `src/verifiers/backends/docker_model_runtime.py`: generic Docker command and HTTP JSON helpers.
- Create `src/verifiers/backends/soltrannet_properties.py`: SolTranNet evaluator, parser, runtime dispatch, and domain gate.
- Create `src/verifiers/backends/molgpka_properties.py`: MolGpKa evaluator, parser, runtime dispatch, and pKa scalar mapping.
- Create `src/verifiers/physchem/__init__.py`: package marker for physical-chemistry ML property scripts.
- Create `src/verifiers/physchem/soltrannet_property_script.py`: shared SolTranNet script wrapper.
- Create `src/verifiers/physchem/soltrannet_log_s.py`: `soltrannet_log_s` script entrypoint.
- Create `src/verifiers/physchem/molgpka_property_script.py`: shared MolGpKa script wrapper.
- Create `src/verifiers/physchem/molgpka_min_pka.py`: `molgpka_min_pka` script entrypoint.
- Create `src/verifiers/physchem/molgpka_max_pka.py`: `molgpka_max_pka` script entrypoint.
- Create `src/verifiers/physchem/molgpka_pka_count.py`: `molgpka_pka_count` script entrypoint.
- Create `scripts/check_soltrannet_env.py`: structured SolTranNet Docker diagnostic.
- Create `scripts/check_molgpka_env.py`: structured MolGpKa Docker diagnostic.
- Create `docs/tracks/SolTranNet.md`: SolTranNet backend capability document.
- Create `docs/tracks/MolGpKa.md`: MolGpKa backend capability document.
- Create `tests/test_docker_model_runtime.py`: runtime adapter unit tests.
- Create `tests/test_soltrannet_properties_backend.py`: SolTranNet backend unit tests.
- Create `tests/test_molgpka_properties_backend.py`: MolGpKa backend unit tests.
- Create `tests/test_physchem_task_scripts.py`: property script wrapper tests.
- Create `tests/test_soltrannet_molgpka_env_scripts.py`: environment check script tests.
- Create `tests/test_soltrannet_molgpka_docker_smoke.py`: opt-in live Docker smoke tests.

Do not add or modify `tasks/`, builtin registry entries, sample answers, or formal verifier specs in this implementation round.

## Task 1: Shared Docker Runtime Adapter

**Files:**
- Create: `src/verifiers/backends/docker_model_runtime.py`
- Test: `tests/test_docker_model_runtime.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_docker_model_runtime.py`:

```python
from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from verifiers.backends import docker_model_runtime as runtime


def test_run_docker_command_maps_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.shutil, "which", lambda command: None)

    with pytest.raises(runtime.DockerRuntimeEnvironmentError) as exc:
        runtime.run_docker_command(["version"], docker_executable="missing-docker", timeout_seconds=1)

    assert "Docker executable not found" in str(exc.value)


def test_run_docker_command_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["timeout"] == 5
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(runtime.shutil, "which", lambda command: "/usr/bin/docker")
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    result = runtime.run_docker_command(["image", "inspect", "example:latest"], timeout_seconds=5)

    assert result.stdout == "ok\n"
    assert calls == [["/usr/bin/docker", "image", "inspect", "example:latest"]]


def test_run_docker_command_maps_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 17, stdout="", stderr="boom")

    monkeypatch.setattr(runtime.shutil, "which", lambda command: "/usr/bin/docker")
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(runtime.DockerRuntimeToolError) as exc:
        runtime.run_docker_command(["run", "bad"], timeout_seconds=5)

    assert "boom" in str(exc.value)


def test_run_docker_command_maps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout=3)

    monkeypatch.setattr(runtime.shutil, "which", lambda command: "/usr/bin/docker")
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(runtime.DockerRuntimeTimeout) as exc:
        runtime.run_docker_command(["run", "slow"], timeout_seconds=3)

    assert "timed out" in str(exc.value)


def test_docker_image_inspect_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        assert args == ["image", "inspect", "example:latest"]
        return runtime.DockerCommandResult(stdout=json.dumps([{"Id": "sha256:123"}]), stderr="", returncode=0)

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)

    assert runtime.docker_image_inspect("example:latest") == {"Id": "sha256:123"}


def test_run_one_shot_container_builds_platform_command(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        assert args == [
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "image:tag",
            "python",
            "-c",
            "print(1)",
        ]
        return runtime.DockerCommandResult(stdout="1\n", stderr="", returncode=0)

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)

    assert runtime.run_one_shot_container(
        image="image:tag",
        command=["python", "-c", "print(1)"],
        platform="linux/amd64",
        timeout_seconds=10,
    ) == "1\n"
```

- [ ] **Step 2: Run adapter tests and verify they fail**

Run:

```bash
uv run pytest tests/test_docker_model_runtime.py -v
```

Expected: FAIL with `ImportError` or `ModuleNotFoundError` because `docker_model_runtime.py` does not exist.

- [ ] **Step 3: Implement the adapter**

Create `src/verifiers/backends/docker_model_runtime.py` with these public names:

```python
"""Shared helpers for Docker-backed model verifier runtimes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class DockerRuntimeEnvironmentError(RuntimeError):
    """Raised when Docker, an image, or a model service is unavailable."""


class DockerRuntimeTimeout(RuntimeError):
    """Raised when a Docker command or model service exceeds its timeout."""


class DockerRuntimeToolError(RuntimeError):
    """Raised when a Docker-backed model returns an execution or schema error."""


@dataclass(frozen=True)
class DockerCommandResult:
    stdout: str
    stderr: str
    returncode: int


def resolve_docker_executable(docker_executable: str | None = None) -> str:
    configured = docker_executable or os.environ.get("VGB_DOCKER_EXECUTABLE") or "docker"
    if os.sep in configured:
        resolved = configured
    else:
        resolved = shutil.which(configured)
    if not resolved:
        raise DockerRuntimeEnvironmentError(f"Docker executable not found: {configured}")
    return resolved


def run_docker_command(
    args: list[str],
    *,
    docker_executable: str | None = None,
    timeout_seconds: float = 60,
    input_text: str | None = None,
    check: bool = True,
) -> DockerCommandResult:
    executable = resolve_docker_executable(docker_executable)
    command = [executable, *args]
    try:
        completed = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DockerRuntimeEnvironmentError(f"Docker executable not found: {executable}") from exc
    except subprocess.TimeoutExpired as exc:
        raise DockerRuntimeTimeout(f"Docker command timed out after {timeout_seconds:g} seconds") from exc

    result = DockerCommandResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"docker exited {result.returncode}"
        raise DockerRuntimeToolError(message)
    return result


def docker_image_inspect(
    image: str,
    *,
    docker_executable: str | None = None,
    timeout_seconds: float = 30,
) -> dict[str, Any]:
    result = run_docker_command(
        ["image", "inspect", image],
        docker_executable=docker_executable,
        timeout_seconds=timeout_seconds,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DockerRuntimeToolError(f"docker image inspect returned invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise DockerRuntimeToolError("docker image inspect returned no image object")
    return payload[0]


def run_one_shot_container(
    *,
    image: str,
    command: list[str],
    platform: str | None = None,
    docker_executable: str | None = None,
    timeout_seconds: float = 60,
    workdir: str | None = None,
) -> str:
    args = ["run", "--rm"]
    if platform:
        args.extend(["--platform", platform])
    if workdir:
        args.extend(["-w", workdir])
    args.append(image)
    args.extend(command)
    return run_docker_command(
        args,
        docker_executable=docker_executable,
        timeout_seconds=timeout_seconds,
    ).stdout


def http_json(
    url: str,
    *,
    method: str = "GET",
    payload: Any | None = None,
    timeout_seconds: float = 30,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            text = response.read().decode()
    except TimeoutError as exc:
        raise DockerRuntimeTimeout(f"HTTP request timed out after {timeout_seconds:g} seconds: {url}") from exc
    except urllib.error.URLError as exc:
        raise DockerRuntimeToolError(f"HTTP request failed for {url}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DockerRuntimeToolError(f"HTTP response from {url} was not JSON: {exc.msg}") from exc


def wait_for_http_json(
    url: str,
    *,
    startup_timeout_seconds: float = 60,
    poll_interval_seconds: float = 1,
) -> Any:
    deadline = time.monotonic() + startup_timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return http_json(url, timeout_seconds=min(5.0, startup_timeout_seconds))
        except (DockerRuntimeToolError, DockerRuntimeTimeout) as exc:
            last_error = exc
            time.sleep(poll_interval_seconds)
    raise DockerRuntimeTimeout(f"HTTP service did not become ready at {url}: {last_error}")


def ensure_http_container(
    *,
    image: str,
    container_name: str,
    host: str,
    port: int,
    container_port: int,
    readiness_url: str,
    docker_executable: str | None = None,
    startup_timeout_seconds: float = 60,
) -> None:
    inspect = run_docker_command(
        ["container", "inspect", "-f", "{{.State.Running}}", container_name],
        docker_executable=docker_executable,
        timeout_seconds=10,
        check=False,
    )
    if inspect.returncode == 0 and inspect.stdout.strip() == "true":
        wait_for_http_json(readiness_url, startup_timeout_seconds=startup_timeout_seconds)
        return
    if inspect.returncode == 0:
        run_docker_command(
            ["rm", container_name],
            docker_executable=docker_executable,
            timeout_seconds=10,
            check=False,
        )

    run_docker_command(
        [
            "run",
            "--rm",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{host}:{port}:{container_port}",
            image,
        ],
        docker_executable=docker_executable,
        timeout_seconds=startup_timeout_seconds,
    )
    wait_for_http_json(readiness_url, startup_timeout_seconds=startup_timeout_seconds)
```

- [ ] **Step 4: Run adapter tests and commit**

Run:

```bash
uv run pytest tests/test_docker_model_runtime.py -v
```

Expected: PASS.

Commit:

```bash
git add src/verifiers/backends/docker_model_runtime.py tests/test_docker_model_runtime.py
git commit -m "feat: add Docker model runtime helpers"
```

## Task 2: SolTranNet Backend

**Files:**
- Create: `src/verifiers/backends/soltrannet_properties.py`
- Test: `tests/test_soltrannet_properties_backend.py`

- [ ] **Step 1: Write failing SolTranNet backend tests**

Create `tests/test_soltrannet_properties_backend.py`:

```python
from __future__ import annotations

from typing import Any

import pytest

from verifiers.backends import docker_model_runtime
from verifiers.backends import soltrannet_properties


def payload() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = {"smiles": "CCO"}
    task = {"task_id": "soltrannet_log_s_001", "version": 1, "object_type": "small_molecule"}
    constraint = {
        "type": "window",
        "property": "soltrannet_log_s",
        "verifier_id": "soltrannet_log_s_v1",
        "min": 2.0,
        "max": 2.5,
        "sigma": 1.0,
    }
    spec = {
        "verifier_id": "soltrannet_log_s_v1",
        "property_name": "soltrannet_log_s",
        "verifier_image": "verifier-grounded:dev",
        "domain": {
            "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [1, 80],
            "mw": [1.0, 1000.0],
            "formal_charge": [-2, 2],
        },
    }
    return candidate, task, constraint, spec


def test_parse_soltrannet_response_reads_solubility() -> None:
    value = soltrannet_properties.parse_soltrannet_response([{"solubility": 2.297180414199829}])

    assert value == pytest.approx(2.297180414199829)


def test_parse_soltrannet_response_rejects_missing_solubility() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        soltrannet_properties.parse_soltrannet_response([{"other": 1.0}])


def test_evaluate_soltrannet_scores_mocked_prediction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(soltrannet_properties, "predict_soltrannet_log_s", lambda smiles, spec: 2.297180414199829)
    candidate, task, constraint, spec = payload()

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["soltrannet_log_s"] == pytest.approx(2.297180414199829)
    assert result["properties"]["heavy_atom_count"] == 3
    assert result["scores"]["score"] == 1.0


def test_evaluate_soltrannet_maps_runtime_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> float:
        raise docker_model_runtime.DockerRuntimeEnvironmentError("Docker daemon unavailable")

    monkeypatch.setattr(soltrannet_properties, "predict_soltrannet_log_s", fail)
    candidate, task, constraint, spec = payload()

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert result["properties"]["heavy_atom_count"] == 3


def test_evaluate_soltrannet_maps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> float:
        raise docker_model_runtime.DockerRuntimeTimeout("slow")

    monkeypatch.setattr(soltrannet_properties, "predict_soltrannet_log_s", fail)
    candidate, task, constraint, spec = payload()

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_timeout"


def test_evaluate_soltrannet_rejects_property_mismatch() -> None:
    candidate, task, constraint, spec = payload()
    spec["property_name"] = "other"

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_evaluate_soltrannet_rejects_multicomponent_smiles() -> None:
    candidate, task, constraint, spec = payload()
    candidate["smiles"] = "CCO.O"

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "validity_error"
```

- [ ] **Step 2: Run SolTranNet tests and verify they fail**

Run:

```bash
uv run pytest tests/test_soltrannet_properties_backend.py -v
```

Expected: FAIL with import error because `soltrannet_properties.py` does not exist.

- [ ] **Step 3: Implement SolTranNet backend**

Create `src/verifiers/backends/soltrannet_properties.py` with these required public functions and constants:

```python
"""SolTranNet aqueous solubility backend for small-molecule verifier scripts."""

from __future__ import annotations

import importlib.metadata as metadata
import math
import os
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifiers.backends import docker_model_runtime as runtime
from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result, error_result


DEFAULT_SOLTRANNET_IMAGE = "ersiliaos/eos6oli:v1.0.0"
DEFAULT_CONTAINER_NAME = "vgb-soltrannet-eos6oli"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18081
DEFAULT_CONTAINER_PORT = 80


def evaluate_soltrannet_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = base_result(task["task_id"], spec.get("verifier_id"), soltrannet_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )

    smiles = candidate.get("smiles")
    if not smiles or not isinstance(smiles, str):
        return error_result(result, "parse_error", "candidate must include a SMILES string")
    if "." in smiles:
        return error_result(result, "validity_error", "multi-component SMILES are not accepted")

    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
    except Exception as exc:
        return error_result(result, "parse_error", f"RDKit parse failed: {exc}")
    if mol is None:
        return error_result(result, "parse_error", "RDKit returned no molecule")

    domain_properties = compute_domain_properties(mol)
    domain_error = check_domain(domain_properties, spec.get("domain") or {})
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=domain_properties)

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    try:
        prediction = predict_soltrannet_log_s(canonical_smiles, spec)
    except runtime.DockerRuntimeEnvironmentError as exc:
        return error_result(result, "verifier_environment_error", str(exc), properties=domain_properties)
    except runtime.DockerRuntimeTimeout as exc:
        return error_result(result, "verifier_timeout", str(exc), properties=domain_properties)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", f"SolTranNet prediction failed: {exc}", properties=domain_properties)

    properties = {**domain_properties, "soltrannet_log_s": prediction}
    try:
        property_score = score_constraint(properties, constraint)
    except Exception as exc:
        return error_result(result, "verifier_spec_error", f"constraint scoring failed: {exc}", properties=properties)

    result.update(
        {
            "status": "ok",
            "canonical_smiles": canonical_smiles,
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [{"property": constraint["property"], "type": constraint["type"], "score": property_score}],
                "property_score": property_score,
                "score": property_score,
            },
        }
    )
    return result


def predict_soltrannet_log_s(smiles: str, spec: dict[str, Any]) -> float:
    config = soltrannet_config(spec)
    base_url = str(config.get("base_url") or os.environ.get("SOLTRANNET_BASE_URL") or "").rstrip("/")
    if not base_url:
        host = str(config["host"])
        port = int(config["port"])
        base_url = f"http://{host}:{port}"
        runtime.ensure_http_container(
            image=str(config["image"]),
            container_name=str(config["container_name"]),
            host=host,
            port=port,
            container_port=int(config["container_port"]),
            readiness_url=f"{base_url}/run/columns/output",
            docker_executable=config.get("docker_executable"),
            startup_timeout_seconds=float(config["startup_timeout_seconds"]),
        )
    payload = runtime.http_json(
        f"{base_url}/run",
        method="POST",
        payload=[smiles],
        timeout_seconds=float(config["prediction_timeout_seconds"]),
    )
    return parse_soltrannet_response(payload)


def parse_soltrannet_response(payload: Any) -> float:
    if not isinstance(payload, list) or not payload:
        raise runtime.DockerRuntimeToolError("SolTranNet response must be a non-empty list")
    row = payload[0]
    if not isinstance(row, dict) or "solubility" not in row:
        raise runtime.DockerRuntimeToolError("SolTranNet response missing 'solubility'")
    value = float(row["solubility"])
    if not math.isfinite(value):
        raise runtime.DockerRuntimeToolError("SolTranNet solubility was not finite")
    return value


def soltrannet_config(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime": "external_docker",
        "image": DEFAULT_SOLTRANNET_IMAGE,
        "container_name": DEFAULT_CONTAINER_NAME,
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "container_port": DEFAULT_CONTAINER_PORT,
        "base_url": None,
        "startup_timeout_seconds": 60,
        "prediction_timeout_seconds": 30,
        **(spec.get("soltrannet") or {}),
    }


def compute_domain_properties(mol: Chem.Mol) -> dict[str, Any]:
    return {
        "mw": Descriptors.MolWt(mol),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
        "formal_charge": Chem.GetFormalCharge(mol),
        "elements": sorted({atom.GetSymbol() for atom in mol.GetAtoms()}),
    }


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    allowed_elements = domain.get("allowed_elements")
    if allowed_elements is not None:
        disallowed = sorted(set(properties["elements"]) - set(allowed_elements))
        if disallowed:
            return f"disallowed elements: {', '.join(disallowed)}"
    for key in ("heavy_atom_count", "mw", "formal_charge"):
        if key not in domain:
            continue
        lower, upper = domain[key]
        if not lower <= properties[key] <= upper:
            return f"{key} outside [{lower}, {upper}]"
    return None


def soltrannet_versions(spec: dict[str, Any]) -> dict[str, Any]:
    config = soltrannet_config(spec)
    return {
        "verifier_image": spec.get("verifier_image"),
        "soltrannet_backend": "eos6oli_v1",
        "soltrannet_image": config["image"],
        "rdkit": metadata.version("rdkit"),
    }
```

- [ ] **Step 4: Run SolTranNet tests and commit**

Run:

```bash
uv run pytest tests/test_soltrannet_properties_backend.py -v
```

Expected: PASS.

Commit:

```bash
git add src/verifiers/backends/soltrannet_properties.py tests/test_soltrannet_properties_backend.py
git commit -m "feat: add SolTranNet backend"
```

## Task 3: MolGpKa Backend

**Files:**
- Create: `src/verifiers/backends/molgpka_properties.py`
- Test: `tests/test_molgpka_properties_backend.py`

- [ ] **Step 1: Write failing MolGpKa backend tests**

Create `tests/test_molgpka_properties_backend.py`:

```python
from __future__ import annotations

from typing import Any

import pytest

from verifiers.backends import docker_model_runtime
from verifiers.backends import molgpka_properties


def payload(property_name: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = {"smiles": "CC(O)=O"}
    task = {"task_id": f"{property_name}_001", "version": 1, "object_type": "small_molecule"}
    constraint = {
        "type": "window",
        "property": property_name,
        "verifier_id": f"{property_name}_v1",
        "min": 7.0,
        "max": 9.0,
        "sigma": 1.0,
    }
    if property_name == "molgpka_pka_count":
        constraint.update({"min": 1, "max": 2})
    spec = {
        "verifier_id": f"{property_name}_v1",
        "property_name": property_name,
        "verifier_image": "verifier-grounded:dev",
        "domain": {
            "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [1, 80],
            "mw": [1.0, 1000.0],
            "formal_charge": [-2, 2],
        },
    }
    return candidate, task, constraint, spec


def test_parse_molgpka_response_reads_values() -> None:
    properties = molgpka_properties.parse_molgpka_response(["CC(O)=O", 1, [8.34]])

    assert properties["molgpka_pka_count"] == 1
    assert properties["molgpka_pka_values"] == [8.34]
    assert properties["molgpka_min_pka"] == pytest.approx(8.34)
    assert properties["molgpka_max_pka"] == pytest.approx(8.34)


def test_parse_molgpka_response_rejects_bad_shape() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response({"bad": "shape"})


def test_evaluate_molgpka_scores_min_max_and_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        molgpka_properties,
        "predict_molgpka_properties",
        lambda smiles, spec: {
            "molgpka_pka_values": [4.2, 8.34],
            "molgpka_pka_count": 2,
            "molgpka_min_pka": 4.2,
            "molgpka_max_pka": 8.34,
        },
    )

    for property_name, expected in [
        ("molgpka_min_pka", 4.2),
        ("molgpka_max_pka", 8.34),
        ("molgpka_pka_count", 2),
    ]:
        candidate, task, constraint, spec = payload(property_name)
        if property_name == "molgpka_min_pka":
            constraint.update({"min": 4.0, "max": 4.5})
        result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)
        assert result["status"] == "ok"
        assert result["canonical_smiles"] == "CC(=O)O"
        assert result["properties"][property_name] == pytest.approx(expected)
        assert result["scores"]["score"] == 1.0


def test_evaluate_molgpka_allows_zero_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        molgpka_properties,
        "predict_molgpka_properties",
        lambda smiles, spec: {"molgpka_pka_values": [], "molgpka_pka_count": 0},
    )
    candidate, task, constraint, spec = payload("molgpka_pka_count")
    constraint.update({"min": 0, "max": 0})

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["status"] == "ok"
    assert result["properties"]["molgpka_pka_count"] == 0
    assert result["scores"]["score"] == 1.0


def test_evaluate_molgpka_min_errors_when_no_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        molgpka_properties,
        "predict_molgpka_properties",
        lambda smiles, spec: {"molgpka_pka_values": [], "molgpka_pka_count": 0},
    )
    candidate, task, constraint, spec = payload("molgpka_min_pka")

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert "no ionizable" in result["message"].lower()
    assert result["properties"]["molgpka_pka_count"] == 0


def test_evaluate_molgpka_maps_runtime_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
        raise docker_model_runtime.DockerRuntimeEnvironmentError("Docker unavailable")

    monkeypatch.setattr(molgpka_properties, "predict_molgpka_properties", fail)
    candidate, task, constraint, spec = payload("molgpka_max_pka")

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"


def test_evaluate_molgpka_rejects_property_mismatch() -> None:
    candidate, task, constraint, spec = payload("molgpka_max_pka")
    spec["property_name"] = "molgpka_min_pka"

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
```

- [ ] **Step 2: Run MolGpKa tests and verify they fail**

Run:

```bash
uv run pytest tests/test_molgpka_properties_backend.py -v
```

Expected: FAIL with import error because `molgpka_properties.py` does not exist.

- [ ] **Step 3: Implement MolGpKa backend**

Create `src/verifiers/backends/molgpka_properties.py` with these required public functions and constants:

```python
"""MolGpKa pKa backend for small-molecule verifier scripts."""

from __future__ import annotations

import importlib.metadata as metadata
import json
import math
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifiers.backends import docker_model_runtime as runtime
from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result, error_result


DEFAULT_MOLGPKA_IMAGE = "ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d"
MOLGPKA_SCALAR_PROPERTIES = {"molgpka_min_pka", "molgpka_max_pka", "molgpka_pka_count"}


def evaluate_molgpka_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = base_result(task["task_id"], spec.get("verifier_id"), molgpka_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )
    if property_name not in MOLGPKA_SCALAR_PROPERTIES:
        return error_result(result, "verifier_spec_error", f"unsupported MolGpKa property {property_name!r}")

    smiles = candidate.get("smiles")
    if not smiles or not isinstance(smiles, str):
        return error_result(result, "parse_error", "candidate must include a SMILES string")
    if "." in smiles:
        return error_result(result, "validity_error", "multi-component SMILES are not accepted")

    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
    except Exception as exc:
        return error_result(result, "parse_error", f"RDKit parse failed: {exc}")
    if mol is None:
        return error_result(result, "parse_error", "RDKit returned no molecule")

    domain_properties = compute_domain_properties(mol)
    domain_error = check_domain(domain_properties, spec.get("domain") or {})
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=domain_properties)

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    try:
        molgpka_properties = predict_molgpka_properties(canonical_smiles, spec)
    except runtime.DockerRuntimeEnvironmentError as exc:
        return error_result(result, "verifier_environment_error", str(exc), properties=domain_properties)
    except runtime.DockerRuntimeTimeout as exc:
        return error_result(result, "verifier_timeout", str(exc), properties=domain_properties)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", f"MolGpKa prediction failed: {exc}", properties=domain_properties)

    properties = {**domain_properties, **molgpka_properties}
    if property_name not in properties:
        return error_result(
            result,
            "domain_error",
            "MolGpKa predicted no ionizable pKa values for min/max pKa scoring",
            properties=properties,
        )

    try:
        property_score = score_constraint(properties, constraint)
    except Exception as exc:
        return error_result(result, "verifier_spec_error", f"constraint scoring failed: {exc}", properties=properties)

    result.update(
        {
            "status": "ok",
            "canonical_smiles": canonical_smiles,
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [{"property": constraint["property"], "type": constraint["type"], "score": property_score}],
                "property_score": property_score,
                "score": property_score,
            },
        }
    )
    return result


def predict_molgpka_properties(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
    config = molgpka_config(spec)
    code = (
        "from cts_molgpka import CTSMolgpka; "
        "import json, sys; "
        "print(json.dumps(CTSMolgpka().main(sys.argv[1])))"
    )
    stdout = runtime.run_one_shot_container(
        image=str(config["image"]),
        platform=str(config["platform"]) if config.get("platform") else None,
        command=["micromamba", "run", "-n", "MolGpka", "python", "-c", code, smiles],
        timeout_seconds=float(config["timeout_seconds"]),
        docker_executable=config.get("docker_executable"),
        workdir="/src",
    )
    return parse_molgpka_stdout(stdout)


def parse_molgpka_stdout(stdout: str) -> dict[str, Any]:
    for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
        try:
            return parse_molgpka_response(json.loads(line))
        except json.JSONDecodeError:
            continue
    raise runtime.DockerRuntimeToolError("MolGpKa stdout contained no JSON prediction")


def parse_molgpka_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list) or len(payload) != 3:
        raise runtime.DockerRuntimeToolError("MolGpKa response must be [smiles, site_count, pka_values]")
    site_count = int(payload[1])
    values_raw = payload[2]
    if not isinstance(values_raw, list):
        raise runtime.DockerRuntimeToolError("MolGpKa pKa values must be a list")
    values = [float(value) for value in values_raw]
    if any(not math.isfinite(value) for value in values):
        raise runtime.DockerRuntimeToolError("MolGpKa pKa values must be finite")
    properties: dict[str, Any] = {
        "molgpka_pka_values": values,
        "molgpka_pka_count": site_count,
    }
    if values:
        properties["molgpka_min_pka"] = min(values)
        properties["molgpka_max_pka"] = max(values)
    return properties


def molgpka_config(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime": "external_docker",
        "image": DEFAULT_MOLGPKA_IMAGE,
        "platform": "linux/amd64",
        "timeout_seconds": 120,
        **(spec.get("molgpka") or {}),
    }


def compute_domain_properties(mol: Chem.Mol) -> dict[str, Any]:
    return {
        "mw": Descriptors.MolWt(mol),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
        "formal_charge": Chem.GetFormalCharge(mol),
        "elements": sorted({atom.GetSymbol() for atom in mol.GetAtoms()}),
    }


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    allowed_elements = domain.get("allowed_elements")
    if allowed_elements is not None:
        disallowed = sorted(set(properties["elements"]) - set(allowed_elements))
        if disallowed:
            return f"disallowed elements: {', '.join(disallowed)}"
    for key in ("heavy_atom_count", "mw", "formal_charge"):
        if key not in domain:
            continue
        lower, upper = domain[key]
        if not lower <= properties[key] <= upper:
            return f"{key} outside [{lower}, {upper}]"
    return None


def molgpka_versions(spec: dict[str, Any]) -> dict[str, Any]:
    config = molgpka_config(spec)
    return {
        "verifier_image": spec.get("verifier_image"),
        "molgpka_backend": "gcn_container_v1",
        "molgpka_image": config["image"],
        "rdkit": metadata.version("rdkit"),
    }
```

- [ ] **Step 4: Run MolGpKa tests and commit**

Run:

```bash
uv run pytest tests/test_molgpka_properties_backend.py -v
```

Expected: PASS.

Commit:

```bash
git add src/verifiers/backends/molgpka_properties.py tests/test_molgpka_properties_backend.py
git commit -m "feat: add MolGpKa backend"
```

## Task 4: Physchem Property Scripts

**Files:**
- Create: `src/verifiers/physchem/__init__.py`
- Create: `src/verifiers/physchem/soltrannet_property_script.py`
- Create: `src/verifiers/physchem/soltrannet_log_s.py`
- Create: `src/verifiers/physchem/molgpka_property_script.py`
- Create: `src/verifiers/physchem/molgpka_min_pka.py`
- Create: `src/verifiers/physchem/molgpka_max_pka.py`
- Create: `src/verifiers/physchem/molgpka_pka_count.py`
- Test: `tests/test_physchem_task_scripts.py`

- [ ] **Step 1: Write failing script wrapper tests**

Create `tests/test_physchem_task_scripts.py`:

```python
from __future__ import annotations

import io
import json
import sys
from typing import Any

import pytest

from verifiers.physchem import molgpka_property_script
from verifiers.physchem import soltrannet_property_script


def run_in_process(main_func: Any, property_name: str, payload: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(sys, "stdout", stdout)
    main_func(property_name)
    return json.loads(stdout.getvalue())


def soltrannet_payload(property_name: str = "soltrannet_log_s") -> dict[str, Any]:
    return {
        "task": {"task_id": "soltrannet_script_001"},
        "constraint": {"property": property_name, "type": "window", "min": 0, "max": 3},
        "verifier_spec": {"verifier_id": "soltrannet_log_s_v1", "property_name": property_name, "verifier_image": "verifier-grounded:dev"},
        "candidate": {"smiles": "CCO"},
    }


def molgpka_payload(property_name: str = "molgpka_pka_count") -> dict[str, Any]:
    return {
        "task": {"task_id": "molgpka_script_001"},
        "constraint": {"property": property_name, "type": "window", "min": 1, "max": 2},
        "verifier_spec": {"verifier_id": f"{property_name}_v1", "property_name": property_name, "verifier_image": "verifier-grounded:dev"},
        "candidate": {"smiles": "CC(O)=O"},
    }


def test_soltrannet_script_helper_calls_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_evaluator(candidate: dict[str, Any], task: dict[str, Any], constraint: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_id": task["task_id"],
            "verifier_id": spec["verifier_id"],
            "status": "ok",
            "canonical_smiles": "CCO",
            "properties": {"soltrannet_log_s": 2.2},
            "scores": {"validity_gate": 1.0, "domain_gate": 1.0, "constraint_scores": [], "property_score": 1.0, "score": 1.0},
            "failure_type": None,
            "message": None,
            "versions": {},
        }

    monkeypatch.setattr(soltrannet_property_script, "evaluate_soltrannet_constraint", fake_evaluator)

    result = run_in_process(soltrannet_property_script.main, "soltrannet_log_s", soltrannet_payload(), monkeypatch)

    assert result["status"] == "ok"
    assert result["properties"]["soltrannet_log_s"] == 2.2


def test_soltrannet_script_helper_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = soltrannet_payload(property_name="other")

    result = run_in_process(soltrannet_property_script.main, "soltrannet_log_s", payload, monkeypatch)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_molgpka_script_helper_calls_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_evaluator(candidate: dict[str, Any], task: dict[str, Any], constraint: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_id": task["task_id"],
            "verifier_id": spec["verifier_id"],
            "status": "ok",
            "canonical_smiles": "CC(=O)O",
            "properties": {"molgpka_pka_count": 1, "molgpka_pka_values": [8.34]},
            "scores": {"validity_gate": 1.0, "domain_gate": 1.0, "constraint_scores": [], "property_score": 1.0, "score": 1.0},
            "failure_type": None,
            "message": None,
            "versions": {},
        }

    monkeypatch.setattr(molgpka_property_script, "evaluate_molgpka_constraint", fake_evaluator)

    result = run_in_process(molgpka_property_script.main, "molgpka_pka_count", molgpka_payload(), monkeypatch)

    assert result["status"] == "ok"
    assert result["properties"]["molgpka_pka_count"] == 1


def test_molgpka_script_helper_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = molgpka_payload(property_name="molgpka_min_pka")

    result = run_in_process(molgpka_property_script.main, "molgpka_pka_count", payload, monkeypatch)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
```

- [ ] **Step 2: Run script tests and verify they fail**

Run:

```bash
uv run pytest tests/test_physchem_task_scripts.py -v
```

Expected: FAIL with import error because `verifiers.physchem` does not exist.

- [ ] **Step 3: Implement property script package and entrypoints**

Create `src/verifiers/physchem/__init__.py`:

```python
"""Physical-chemistry ML property verifier scripts."""
```

Create `src/verifiers/physchem/soltrannet_property_script.py`:

```python
"""Shared CLI helper for SolTranNet property verifier scripts."""

from __future__ import annotations

from verifiers.backends.soltrannet_properties import evaluate_soltrannet_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_soltrannet_constraint,
        sort_keys=True,
    )


__all__ = ["main"]
```

Create `src/verifiers/physchem/soltrannet_log_s.py`:

```python
from __future__ import annotations

from verifiers.physchem.soltrannet_property_script import main


if __name__ == "__main__":
    main("soltrannet_log_s")
```

Create `src/verifiers/physchem/molgpka_property_script.py`:

```python
"""Shared CLI helper for MolGpKa property verifier scripts."""

from __future__ import annotations

from verifiers.backends.molgpka_properties import evaluate_molgpka_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_molgpka_constraint,
        sort_keys=True,
    )


__all__ = ["main"]
```

Create `src/verifiers/physchem/molgpka_min_pka.py`:

```python
from __future__ import annotations

from verifiers.physchem.molgpka_property_script import main


if __name__ == "__main__":
    main("molgpka_min_pka")
```

Create `src/verifiers/physchem/molgpka_max_pka.py`:

```python
from __future__ import annotations

from verifiers.physchem.molgpka_property_script import main


if __name__ == "__main__":
    main("molgpka_max_pka")
```

Create `src/verifiers/physchem/molgpka_pka_count.py`:

```python
from __future__ import annotations

from verifiers.physchem.molgpka_property_script import main


if __name__ == "__main__":
    main("molgpka_pka_count")
```

- [ ] **Step 4: Run script tests and commit**

Run:

```bash
uv run pytest tests/test_physchem_task_scripts.py -v
```

Expected: PASS.

Commit:

```bash
git add src/verifiers/physchem tests/test_physchem_task_scripts.py
git commit -m "feat: add physchem property scripts"
```

## Task 5: Environment Check Scripts

**Files:**
- Create: `scripts/check_soltrannet_env.py`
- Create: `scripts/check_molgpka_env.py`
- Test: `tests/test_soltrannet_molgpka_env_scripts.py`

- [ ] **Step 1: Write failing environment script tests**

Create `tests/test_soltrannet_molgpka_env_scripts.py`:

```python
from __future__ import annotations

import json
import sys
from typing import Any

import pytest

from scripts import check_molgpka_env
from scripts import check_soltrannet_env


def test_check_soltrannet_env_reports_success_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "runtime": {"image": args.image, "mode": "external_docker"},
            "prediction": {"smiles": args.smiles, "soltrannet_log_s": 2.29},
        }

    monkeypatch.setattr(check_soltrannet_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_soltrannet_env.py", "--smiles", "CCO", "--image", "image:tag"])

    check_soltrannet_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["runtime"]["image"] == "image:tag"
    assert payload["prediction"]["soltrannet_log_s"] == 2.29


def test_check_soltrannet_env_reports_error_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {"status": "error", "failure_type": "verifier_environment_error", "message": "Docker unavailable"}

    monkeypatch.setattr(check_soltrannet_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_soltrannet_env.py"])

    check_soltrannet_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"


def test_check_molgpka_env_reports_success_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "runtime": {"image": args.image, "platform": args.platform},
            "prediction": {"smiles": args.smiles, "molgpka_pka_count": 1, "molgpka_pka_values": [8.34]},
        }

    monkeypatch.setattr(check_molgpka_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_molgpka_env.py", "--smiles", "CC(O)=O", "--image", "image:tag"])

    check_molgpka_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["runtime"]["image"] == "image:tag"
    assert payload["prediction"]["molgpka_pka_values"] == [8.34]


def test_check_molgpka_env_reports_error_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {"status": "error", "failure_type": "verifier_tool_error", "message": "bad output"}

    monkeypatch.setattr(check_molgpka_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_molgpka_env.py"])

    check_molgpka_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_tool_error"
```

- [ ] **Step 2: Run environment script tests and verify they fail**

Run:

```bash
uv run pytest tests/test_soltrannet_molgpka_env_scripts.py -v
```

Expected: FAIL with import error because the check scripts do not exist.

- [ ] **Step 3: Implement environment scripts**

Create `scripts/check_soltrannet_env.py` with:

```python
#!/usr/bin/env python
"""Smoke-check the Docker-backed SolTranNet verifier runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPOSITORY_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from verifiers.backends import docker_model_runtime as runtime
from verifiers.backends import soltrannet_properties


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    spec = {
        "verifier_image": "verifier-grounded:dev",
        "soltrannet": {
            "image": args.image,
            "container_name": args.container_name,
            "host": args.host,
            "port": args.port,
            "base_url": args.base_url,
            "startup_timeout_seconds": args.startup_timeout_seconds,
            "prediction_timeout_seconds": args.prediction_timeout_seconds,
        },
    }
    if args.docker_executable:
        spec["soltrannet"]["docker_executable"] = args.docker_executable
    try:
        image = runtime.docker_image_inspect(args.image, docker_executable=args.docker_executable)
        value = soltrannet_properties.predict_soltrannet_log_s(args.smiles, spec)
    except runtime.DockerRuntimeEnvironmentError as exc:
        return {"status": "error", "failure_type": "verifier_environment_error", "message": str(exc), "runtime": {"image": args.image}}
    except runtime.DockerRuntimeTimeout as exc:
        return {"status": "error", "failure_type": "verifier_timeout", "message": str(exc), "runtime": {"image": args.image}}
    except Exception as exc:
        return {"status": "error", "failure_type": "verifier_tool_error", "message": str(exc), "runtime": {"image": args.image}}
    return {
        "status": "ok",
        "failure_type": None,
        "message": None,
        "runtime": {
            "image": args.image,
            "image_id": image.get("Id"),
            "mode": "external_docker",
            "base_url": args.base_url,
            "container_name": args.container_name,
            "host": args.host,
            "port": args.port,
        },
        "prediction": {"smiles": args.smiles, "soltrannet_log_s": value},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smiles", default="CCO")
    parser.add_argument("--image", default=soltrannet_properties.DEFAULT_SOLTRANNET_IMAGE)
    parser.add_argument("--container-name", default=soltrannet_properties.DEFAULT_CONTAINER_NAME)
    parser.add_argument("--host", default=soltrannet_properties.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=soltrannet_properties.DEFAULT_PORT)
    parser.add_argument("--base-url")
    parser.add_argument("--docker-executable")
    parser.add_argument("--startup-timeout-seconds", type=float, default=60)
    parser.add_argument("--prediction-timeout-seconds", type=float, default=30)
    args = parser.parse_args()
    print(json.dumps(build_payload(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

Create `scripts/check_molgpka_env.py` with:

```python
#!/usr/bin/env python
"""Smoke-check the Docker-backed MolGpKa verifier runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPOSITORY_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from verifiers.backends import docker_model_runtime as runtime
from verifiers.backends import molgpka_properties


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    spec = {
        "verifier_image": "verifier-grounded:dev",
        "molgpka": {
            "image": args.image,
            "platform": args.platform,
            "timeout_seconds": args.timeout_seconds,
        },
    }
    if args.docker_executable:
        spec["molgpka"]["docker_executable"] = args.docker_executable
    try:
        image = runtime.docker_image_inspect(args.image, docker_executable=args.docker_executable)
        prediction = molgpka_properties.predict_molgpka_properties(args.smiles, spec)
    except runtime.DockerRuntimeEnvironmentError as exc:
        return {"status": "error", "failure_type": "verifier_environment_error", "message": str(exc), "runtime": {"image": args.image}}
    except runtime.DockerRuntimeTimeout as exc:
        return {"status": "error", "failure_type": "verifier_timeout", "message": str(exc), "runtime": {"image": args.image}}
    except Exception as exc:
        return {"status": "error", "failure_type": "verifier_tool_error", "message": str(exc), "runtime": {"image": args.image}}
    return {
        "status": "ok",
        "failure_type": None,
        "message": None,
        "runtime": {
            "image": args.image,
            "image_id": image.get("Id"),
            "platform": args.platform,
            "mode": "external_docker",
        },
        "prediction": {"smiles": args.smiles, **prediction},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smiles", default="CC(O)=O")
    parser.add_argument("--image", default=molgpka_properties.DEFAULT_MOLGPKA_IMAGE)
    parser.add_argument("--platform", default="linux/amd64")
    parser.add_argument("--docker-executable")
    parser.add_argument("--timeout-seconds", type=float, default=120)
    args = parser.parse_args()
    print(json.dumps(build_payload(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run environment script tests and commit**

Run:

```bash
uv run pytest tests/test_soltrannet_molgpka_env_scripts.py -v
```

Expected: PASS.

Commit:

```bash
git add scripts/check_soltrannet_env.py scripts/check_molgpka_env.py tests/test_soltrannet_molgpka_env_scripts.py
git commit -m "feat: add SolTranNet MolGpKa env checks"
```

## Task 6: Opt-In Live Docker Smoke Tests

**Files:**
- Create: `tests/test_soltrannet_molgpka_docker_smoke.py`

- [ ] **Step 1: Add live smoke tests gated by environment variable**

Create `tests/test_soltrannet_molgpka_docker_smoke.py`:

```python
from __future__ import annotations

import os
from typing import Any

import pytest

from verifiers.backends import molgpka_properties
from verifiers.backends import soltrannet_properties


pytestmark = pytest.mark.skipif(
    os.environ.get("VGB_RUN_DOCKER_SMOKE") != "1",
    reason="set VGB_RUN_DOCKER_SMOKE=1 to run live Docker model smoke tests",
)


DOMAIN = {
    "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
    "heavy_atom_count": [1, 80],
    "mw": [1.0, 1000.0],
    "formal_charge": [-2, 2],
}


def test_live_soltrannet_predicts_ethanol() -> None:
    value = soltrannet_properties.predict_soltrannet_log_s("CCO", {"soltrannet": {}})

    assert isinstance(value, float)


def test_live_soltrannet_backend_scores_ethanol() -> None:
    result = soltrannet_properties.evaluate_soltrannet_constraint(
        {"smiles": "CCO"},
        {"task_id": "live_soltrannet"},
        {
            "type": "window",
            "property": "soltrannet_log_s",
            "verifier_id": "soltrannet_log_s_v1",
            "min": 1.0,
            "max": 3.5,
            "sigma": 1.0,
        },
        {
            "verifier_id": "soltrannet_log_s_v1",
            "property_name": "soltrannet_log_s",
            "domain": DOMAIN,
            "soltrannet": {},
        },
    )

    assert result["status"] == "ok"
    assert isinstance(result["properties"]["soltrannet_log_s"], float)


def test_live_molgpka_predicts_acetic_acid() -> None:
    properties = molgpka_properties.predict_molgpka_properties("CC(=O)O", {"molgpka": {}})

    assert properties["molgpka_pka_count"] >= 1
    assert properties["molgpka_pka_values"]


def test_live_molgpka_backend_scores_acetic_acid_count() -> None:
    result = molgpka_properties.evaluate_molgpka_constraint(
        {"smiles": "CC(O)=O"},
        {"task_id": "live_molgpka"},
        {
            "type": "window",
            "property": "molgpka_pka_count",
            "verifier_id": "molgpka_pka_count_v1",
            "min": 1,
            "max": 3,
            "sigma": 1.0,
        },
        {
            "verifier_id": "molgpka_pka_count_v1",
            "property_name": "molgpka_pka_count",
            "domain": DOMAIN,
            "molgpka": {},
        },
    )

    assert result["status"] == "ok"
    assert result["properties"]["molgpka_pka_count"] >= 1
```

- [ ] **Step 2: Run smoke test file without Docker flag**

Run:

```bash
uv run pytest tests/test_soltrannet_molgpka_docker_smoke.py -v
```

Expected: all tests are skipped.

- [ ] **Step 3: Optionally run live smoke when Docker images are available**

Run only on a machine with both images available:

```bash
VGB_RUN_DOCKER_SMOKE=1 uv run pytest tests/test_soltrannet_molgpka_docker_smoke.py -v
```

Expected: PASS. If Docker Hub DNS or local image availability fails, record the failure in the implementation summary and keep default tests passing.

- [ ] **Step 4: Commit live smoke tests**

Run:

```bash
uv run pytest tests/test_soltrannet_molgpka_docker_smoke.py -v
```

Expected: skipped without `VGB_RUN_DOCKER_SMOKE=1`.

Commit:

```bash
git add tests/test_soltrannet_molgpka_docker_smoke.py
git commit -m "test: add opt-in SolTranNet MolGpKa Docker smoke"
```

## Task 7: Separate Backend Documentation

**Files:**
- Create: `docs/tracks/SolTranNet.md`
- Create: `docs/tracks/MolGpKa.md`

- [ ] **Step 1: Write SolTranNet documentation**

Create `docs/tracks/SolTranNet.md`:

```markdown
# SolTranNet Backend

Status: backend capability document, not a registered formal benchmark track.

## Purpose

This backend wraps SolTranNet through the Ersilia `eos6oli` Docker image to predict a logS-style aqueous solubility value from a single-component small-molecule SMILES.

## Property

| Verifier property | Model output | Meaning |
|---|---|---|
| `soltrannet_log_s` | `solubility` | SolTranNet aqueous solubility prediction, treated as a logS-style scalar for verifier scoring. |

## Runtime

Default development runtime:

```yaml
soltrannet:
  runtime: external_docker
  image: ersiliaos/eos6oli:v1.0.0
  container_name: vgb-soltrannet-eos6oli
  host: 127.0.0.1
  port: 18081
  startup_timeout_seconds: 60
  prediction_timeout_seconds: 30
```

If `SOLTRANNET_BASE_URL` or `soltrannet.base_url` is set, the backend calls that service and does not manage a Docker container.

## Environment Check

```bash
uv run python scripts/check_soltrannet_env.py --smiles CCO
```

The script prints structured JSON with runtime metadata and a sample prediction.

## Limitations

- The backend accepts one single-component SMILES at a time.
- The Ersilia output field is `solubility`; the verifier maps it to `soltrannet_log_s`.
- External Docker is the development deployment path. A future official verifier image should switch this backend to `runtime: local` while keeping the property script and result schema unchanged.
```

- [ ] **Step 2: Write MolGpKa documentation**

Create `docs/tracks/MolGpKa.md`:

```markdown
# MolGpKa Backend

Status: backend capability document, not a registered formal benchmark track.

## Purpose

This backend wraps MolGpKa through the `ghcr.io/quanted/cts-molgpka` Docker image to predict ionizable-site pKa values from a single-component small-molecule SMILES.

## Properties

| Verifier property | Meaning |
|---|---|
| `molgpka_min_pka` | Minimum predicted pKa in the MolGpKa pKa list. |
| `molgpka_max_pka` | Maximum predicted pKa in the MolGpKa pKa list. |
| `molgpka_pka_count` | Number of predicted ionizable pKa values. |

The raw list is retained as `molgpka_pka_values` in verifier result diagnostics.

## Runtime

Default development runtime:

```yaml
molgpka:
  runtime: external_docker
  image: ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d
  platform: linux/amd64
  timeout_seconds: 120
```

The backend uses a one-shot container command that calls `CTSMolgpka().main(smiles)` through `micromamba run -n MolGpka python`.

## Environment Check

```bash
uv run python scripts/check_molgpka_env.py --smiles 'CC(O)=O'
```

The script prints structured JSON with runtime metadata, pKa count, and pKa values.

## Limitations

- The first wrapper does not split acidic and basic pKa sites.
- `molgpka_min_pka` and `molgpka_max_pka` require at least one predicted pKa value.
- `molgpka_pka_count` can score molecules with zero predicted pKa values.
- The current image is amd64 and may run through emulation on arm64 Docker Desktop.
- External Docker is the development deployment path. A future official verifier image should switch this backend to `runtime: local` while keeping the property scripts and result schema unchanged.
```

- [ ] **Step 3: Run tests and commit docs**

Run:

```bash
uv run pytest
```

Expected: PASS.

Commit:

```bash
git add docs/tracks/SolTranNet.md docs/tracks/MolGpKa.md
git commit -m "docs: add SolTranNet MolGpKa backend docs"
```

## Task 8: Full Verification And Scope Guard

**Files:**
- Inspect only: `src/verifier_grounded_benchmark/registry.py`
- Inspect only: `tasks/`

- [ ] **Step 1: Verify no task packs or formal registry entries were added**

Run:

```bash
git status --short
git diff --name-only HEAD~6..HEAD
```

Expected:

- No files under `tasks/` were created or modified.
- `src/verifier_grounded_benchmark/registry.py` was not modified.

- [ ] **Step 2: Run targeted test set**

Run:

```bash
uv run pytest \
  tests/test_docker_model_runtime.py \
  tests/test_soltrannet_properties_backend.py \
  tests/test_molgpka_properties_backend.py \
  tests/test_physchem_task_scripts.py \
  tests/test_soltrannet_molgpka_env_scripts.py \
  tests/test_soltrannet_molgpka_docker_smoke.py \
  -v
```

Expected: unit tests PASS and live Docker smoke tests SKIP unless `VGB_RUN_DOCKER_SMOKE=1`.

- [ ] **Step 3: Run full suite**

Run:

```bash
uv run pytest
```

Expected: PASS.

- [ ] **Step 4: Produce implementation summary**

Summarize:

- New backend files.
- New property scripts.
- New environment check scripts.
- New docs.
- Test results.
- Whether opt-in live Docker smoke was run, skipped, or blocked by local image/network availability.

No commit is required for this step unless a verification fix changes files. If a fix changes files, run the affected tests and then commit that fix before final response.

## Self-Review Checklist

- Spec coverage: Tasks 1-7 cover Docker runtime, SolTranNet backend, MolGpKa backend, property scripts, environment checks, live smoke, and separate docs. Task 8 covers the no-task-pack and no-formal-registry scope guard.
- Placeholder scan: This plan contains no undefined files, no unscoped implementation steps, and no deferred behavior without a concrete migration path.
- Type consistency: Property names are consistently `soltrannet_log_s`, `molgpka_min_pka`, `molgpka_max_pka`, and `molgpka_pka_count`.
