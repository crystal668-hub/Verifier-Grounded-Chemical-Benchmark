# OpenMM + OpenFF Local Optional Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a usable local optional OpenMM + OpenFF/GAFF backend/runtime path without adding benchmark tasks.

**Architecture:** Keep OpenMM/OpenFF dependencies outside the default `uv` environment in a conda-forge environment file. Add a script-level environment checker plus reusable backend helpers under `src/verifiers/backends/`, with tests that mock missing optional dependencies so default CI remains lightweight. Do not create task packs, sample answers, verifier specs, task prompts, calibration data, or public registry entries.

**Tech Stack:** Python 3.12, pytest, PyYAML, RDKit already in the default project, optional conda packages `openmm`, `openff-toolkit`, `openff-interchange`, `openmmforcefields`, `ambertools`.

---

## Scope Guard

This implementation must not create or modify:

- `tasks/`
- `tasks/*/sample_answers.jsonl`
- `tasks/*/verifier_specs.yaml`
- public track registry entries for OpenMM
- task prompts, task thresholds, calibration manifests, or sample answers

The deliverable is limited to environment/runtime setup, check scripts, reusable backend code, backend tests, and backend documentation.

## Files

Create:

- `envs/openmm-openff.yml`: conda-forge optional runtime definition.
- `scripts/check_openmm_openff_env.py`: JSON environment and smoke-check script.
- `src/verifiers/backends/openmm_runtime.py`: shared optional import, version, smoke, unit, and error helpers.
- `src/verifiers/backends/openmm_core_properties.py`: OpenMM core fixed-fixture backend.
- `src/verifiers/backends/openmm_openff_properties.py`: OpenFF/GAFF ligand minimization backend.
- `tests/test_openmm_openff_env_file.py`: static environment file tests.
- `tests/test_openmm_openff_env_script.py`: check script tests with mocked imports/runtime.
- `tests/test_openmm_core_backend.py`: core backend tests with mocked runtime.
- `tests/test_openmm_openff_backend.py`: ligand backend tests with mocked runtime.
- `docs/tracks/OpenMM-OpenFF.md`: backend status and local setup docs; no task design.

Modify only if needed:

- `src/verifiers/backends/__init__.py`: leave empty unless the repo pattern requires explicit exports. Do not add task registration.

---

### Task 1: Add Conda Environment File

**Files:**
- Create: `envs/openmm-openff.yml`
- Create: `tests/test_openmm_openff_env_file.py`

- [ ] **Step 1: Write the failing environment-file tests**

Create `tests/test_openmm_openff_env_file.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "envs" / "openmm-openff.yml"


def test_openmm_openff_conda_env_file_exists() -> None:
    assert ENV_FILE.exists()


def test_openmm_openff_conda_env_uses_conda_forge_only() -> None:
    payload = yaml.safe_load(ENV_FILE.read_text())

    assert payload["name"] == "vgb-openmm-openff"
    assert payload["channels"] == ["conda-forge"]


def test_openmm_openff_conda_env_contains_required_packages() -> None:
    payload = yaml.safe_load(ENV_FILE.read_text())
    dependencies = {str(item).split("=")[0] for item in payload["dependencies"]}

    assert dependencies >= {
        "python",
        "openmm",
        "openff-toolkit",
        "openff-interchange",
        "openmmforcefields",
        "ambertools",
        "rdkit",
        "numpy",
        "pyyaml",
        "pytest",
    }


def test_openmm_openff_not_added_to_pyproject_defaults() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()

    assert '"openmm' not in pyproject
    assert '"openff-toolkit' not in pyproject
    assert '"openff-interchange' not in pyproject
    assert '"openmmforcefields' not in pyproject
    assert '"ambertools' not in pyproject
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_openmm_openff_env_file.py -v
```

Expected: fails because `envs/openmm-openff.yml` does not exist.

- [ ] **Step 3: Add the conda environment file**

Create `envs/openmm-openff.yml`:

```yaml
name: vgb-openmm-openff
channels:
  - conda-forge
dependencies:
  - python=3.12
  - openmm
  - openff-toolkit
  - openff-interchange
  - openmmforcefields
  - ambertools
  - rdkit
  - numpy
  - pyyaml
  - pytest
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_openmm_openff_env_file.py -v
```

Expected: all tests in `tests/test_openmm_openff_env_file.py` pass.

- [ ] **Step 5: Run full tests**

Run:

```bash
uv run pytest
```

Expected: full suite passes without OpenMM/OpenFF installed.

- [ ] **Step 6: Commit**

Run:

```bash
git add envs/openmm-openff.yml tests/test_openmm_openff_env_file.py
git commit -m "build: add OpenMM OpenFF optional conda env"
```

---

### Task 2: Add Shared Runtime Helper And Environment Check Script

**Files:**
- Create: `src/verifiers/backends/openmm_runtime.py`
- Create: `scripts/check_openmm_openff_env.py`
- Create: `tests/test_openmm_openff_env_script.py`

- [ ] **Step 1: Write failing check-script tests**

Create `tests/test_openmm_openff_env_script.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
import types
from typing import Any

import pytest

from scripts import check_openmm_openff_env


def test_check_openmm_openff_env_reports_missing_dependency_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def missing_runtime(mode: str) -> dict[str, Any]:
        return {
            "status": "error",
            "failure_type": "verifier_env_error",
            "message": "missing optional dependency: openff.toolkit",
            "versions": {},
            "platforms": [],
            "checks": {
                "core": {"status": "skipped"},
                "openff": {"status": "error", "failure_type": "verifier_env_error"},
                "gaff": {"status": "skipped"},
            },
        }

    monkeypatch.setattr(check_openmm_openff_env, "build_payload", missing_runtime)
    monkeypatch.setattr(sys, "argv", ["check_openmm_openff_env.py", "--mode", "openff"])

    with pytest.raises(SystemExit) as exc:
        check_openmm_openff_env.main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_env_error"
    assert "openff.toolkit" in payload["message"]
    assert captured.err == ""


def test_check_openmm_openff_env_reports_success_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def ok_runtime(mode: str) -> dict[str, Any]:
        assert mode == "core"
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "versions": {"openmm": "8.2.0"},
            "platforms": ["Reference", "CPU"],
            "checks": {"core": {"status": "ok"}},
        }

    monkeypatch.setattr(check_openmm_openff_env, "build_payload", ok_runtime)
    monkeypatch.setattr(sys, "argv", ["check_openmm_openff_env.py", "--mode", "core"])

    check_openmm_openff_env.main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "ok"
    assert payload["failure_type"] is None
    assert captured.err == ""


def test_check_openmm_openff_env_rejects_invalid_mode() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_openmm_openff_env.py", "--mode", "invalid"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 2
    assert "invalid choice" in completed.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_openmm_openff_env_script.py -v
```

Expected: fails because `scripts/check_openmm_openff_env.py` does not exist.

- [ ] **Step 3: Implement `openmm_runtime.py` with optional import and smoke helpers**

Create `src/verifiers/backends/openmm_runtime.py` with this structure:

```python
"""Optional OpenMM/OpenFF runtime helpers."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import math
from dataclasses import dataclass
from typing import Any


ENV_FAILURE = "verifier_env_error"
TOOL_FAILURE = "verifier_tool_error"
DEFAULT_OPENFF_SMILES = "CCO"
DEFAULT_OPENFF_FORCEFIELD = "openff-2.2.1.offxml"


class OpenMMEnvironmentError(RuntimeError):
    """Raised when the optional OpenMM/OpenFF runtime is missing or unusable."""


class OpenMMToolError(RuntimeError):
    """Raised when an installed OpenMM/OpenFF tool fails during calculation."""


@dataclass(frozen=True)
class RuntimeModules:
    openmm: Any
    unit: Any
    app: Any | None = None
    openff_toolkit: Any | None = None
    openff_interchange: Any | None = None
    openmmforcefields: Any | None = None


def package_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "unknown"


def import_required(module_name: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        raise OpenMMEnvironmentError(f"missing optional dependency: {module_name}") from exc


def load_core_modules() -> RuntimeModules:
    openmm = import_required("openmm")
    unit = import_required("openmm.unit")
    return RuntimeModules(openmm=openmm, unit=unit)


def load_openff_modules() -> RuntimeModules:
    openmm = import_required("openmm")
    unit = import_required("openmm.unit")
    app = import_required("openmm.app")
    openff_toolkit = import_required("openff.toolkit")
    openff_interchange = import_required("openff.interchange")
    return RuntimeModules(
        openmm=openmm,
        unit=unit,
        app=app,
        openff_toolkit=openff_toolkit,
        openff_interchange=openff_interchange,
    )


def load_gaff_modules() -> RuntimeModules:
    modules = load_openff_modules()
    openmmforcefields = import_required("openmmforcefields.generators")
    return RuntimeModules(
        openmm=modules.openmm,
        unit=modules.unit,
        app=modules.app,
        openff_toolkit=modules.openff_toolkit,
        openff_interchange=modules.openff_interchange,
        openmmforcefields=openmmforcefields,
    )


def openmm_platforms(openmm: Any) -> list[str]:
    try:
        return [openmm.Platform.getPlatform(index).getName() for index in range(openmm.Platform.getNumPlatforms())]
    except Exception as exc:
        raise OpenMMEnvironmentError(f"failed to enumerate OpenMM platforms: {exc}") from exc


def select_platform(openmm: Any, preferred: str = "Reference") -> Any:
    platforms = openmm_platforms(openmm)
    if preferred in platforms:
        return openmm.Platform.getPlatformByName(preferred)
    if "CPU" in platforms:
        return openmm.Platform.getPlatformByName("CPU")
    if platforms:
        return openmm.Platform.getPlatformByName(platforms[0])
    raise OpenMMEnvironmentError("no OpenMM Reference or CPU platform available")


def finite_float(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise OpenMMToolError(f"{label} was not finite")
    return result


def run_core_smoke(preferred_platform: str = "Reference") -> dict[str, Any]:
    modules = load_core_modules()
    openmm = modules.openmm
    unit = modules.unit
    platform = select_platform(openmm, preferred_platform)

    system = openmm.System()
    system.addParticle(39.9)
    system.addParticle(39.9)
    bond = openmm.HarmonicBondForce()
    bond.addBond(0, 1, 0.2 * unit.nanometer, 100.0 * unit.kilojoule_per_mole / unit.nanometer**2)
    system.addForce(bond)
    integrator = openmm.VerletIntegrator(0.001 * unit.picoseconds)
    context = openmm.Context(system, integrator, platform)
    try:
        context.setPositions([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]] * unit.nanometer)
        initial_state = context.getState(getEnergy=True)
        initial_energy = initial_state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        openmm.LocalEnergyMinimizer.minimize(context, maxIterations=50)
        final_state = context.getState(getEnergy=True, getForces=True)
        minimized_energy = final_state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        forces = final_state.getForces()
        max_force = max(
            vector.norm().value_in_unit(unit.kilojoule_per_mole / unit.nanometer)
            for vector in forces
        )
    finally:
        del context
        del integrator

    return {
        "status": "ok",
        "selected_platform": platform.getName(),
        "initial_energy_kj_mol": finite_float(initial_energy, "initial_energy_kj_mol"),
        "minimized_energy_kj_mol": finite_float(minimized_energy, "minimized_energy_kj_mol"),
        "energy_drop_kj_mol": finite_float(initial_energy - minimized_energy, "energy_drop_kj_mol"),
        "final_max_force_kj_mol_nm": finite_float(max_force, "final_max_force_kj_mol_nm"),
    }
```

Continue the same file with `run_openff_smoke()` and `run_gaff_smoke()`:

```python
def run_openff_smoke(
    smiles: str = DEFAULT_OPENFF_SMILES,
    forcefield_name: str = DEFAULT_OPENFF_FORCEFIELD,
    preferred_platform: str = "Reference",
) -> dict[str, Any]:
    modules = load_openff_modules()
    toolkit = modules.openff_toolkit
    interchange_module = modules.openff_interchange

    try:
        molecule = toolkit.Molecule.from_smiles(smiles, allow_undefined_stereo=True)
        molecule.generate_conformers(n_conformers=1)
        molecule.assign_partial_charges("am1bcc")
        forcefield = toolkit.ForceField(forcefield_name)
        topology = molecule.to_topology()
        interchange = interchange_module.Interchange.from_smirnoff(forcefield, topology)
        system = interchange.to_openmm()
    except Exception as exc:
        raise OpenMMToolError(f"OpenFF parameterization failed: {exc}") from exc

    metrics = run_openmm_system_minimization(
        modules=modules,
        system=system,
        positions=interchange.positions.to_openmm(),
        preferred_platform=preferred_platform,
    )
    metrics.update(
        {
            "status": "ok",
            "forcefield_name": forcefield_name,
            "charge_method": "am1bcc",
            "parameterization_success": 1,
            "system_particle_count": system.getNumParticles(),
        }
    )
    return metrics


def run_gaff_smoke(preferred_platform: str = "Reference") -> dict[str, Any]:
    modules = load_gaff_modules()
    if not hasattr(modules.openmmforcefields, "GAFFTemplateGenerator"):
        raise OpenMMEnvironmentError("GAFFTemplateGenerator is unavailable in openmmforcefields.generators")
    return {
        "status": "ok",
        "ambertools_available": 1,
        "gaff_template_generator_available": 1,
        "message": "GAFF template generator import smoke passed",
    }
```

Add `run_openmm_system_minimization()` above `run_openff_smoke()`:

```python
def run_openmm_system_minimization(
    *,
    modules: RuntimeModules,
    system: Any,
    positions: Any,
    preferred_platform: str,
    max_iterations: int = 200,
) -> dict[str, float | str]:
    openmm = modules.openmm
    unit = modules.unit
    platform = select_platform(openmm, preferred_platform)
    integrator = openmm.VerletIntegrator(0.001 * unit.picoseconds)
    context = openmm.Context(system, integrator, platform)
    try:
        context.setPositions(positions)
        initial_state = context.getState(getEnergy=True)
        initial_energy = initial_state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        openmm.LocalEnergyMinimizer.minimize(context, maxIterations=max_iterations)
        final_state = context.getState(getEnergy=True, getForces=True)
        minimized_energy = final_state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        forces = final_state.getForces()
        max_force = max(
            vector.norm().value_in_unit(unit.kilojoule_per_mole / unit.nanometer)
            for vector in forces
        )
    finally:
        del context
        del integrator

    return {
        "selected_platform": platform.getName(),
        "initial_energy_kj_mol": finite_float(initial_energy, "initial_energy_kj_mol"),
        "minimized_energy_kj_mol": finite_float(minimized_energy, "minimized_energy_kj_mol"),
        "energy_drop_kj_mol": finite_float(initial_energy - minimized_energy, "energy_drop_kj_mol"),
        "final_max_force_kj_mol_nm": finite_float(max_force, "final_max_force_kj_mol_nm"),
    }
```

- [ ] **Step 4: Implement the check script**

Create `scripts/check_openmm_openff_env.py`:

```python
#!/usr/bin/env python
"""Smoke-check optional OpenMM + OpenFF/GAFF local environment."""

from __future__ import annotations

import argparse
import json
from typing import Any

from verifiers.backends import openmm_runtime


def error_payload(message: str, *, check: str | None = None) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {
        "core": {"status": "skipped"},
        "openff": {"status": "skipped"},
        "gaff": {"status": "skipped"},
    }
    if check is not None:
        checks[check] = {"status": "error", "failure_type": openmm_runtime.ENV_FAILURE}
    return {
        "status": "error",
        "failure_type": openmm_runtime.ENV_FAILURE,
        "message": message,
        "versions": {},
        "platforms": [],
        "checks": checks,
    }


def build_payload(mode: str) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    versions = {
        "openmm": openmm_runtime.package_version("openmm"),
        "openff_toolkit": openmm_runtime.package_version("openff-toolkit"),
        "openff_interchange": openmm_runtime.package_version("openff-interchange"),
        "openmmforcefields": openmm_runtime.package_version("openmmforcefields"),
        "rdkit": openmm_runtime.package_version("rdkit"),
    }
    platforms: list[str] = []

    try:
        if mode in {"core", "all"}:
            core = openmm_runtime.run_core_smoke()
            checks["core"] = core
            platforms = openmm_runtime.openmm_platforms(openmm_runtime.load_core_modules().openmm)
        if mode in {"openff", "all"}:
            checks["openff"] = openmm_runtime.run_openff_smoke()
        if mode in {"gaff", "all"}:
            checks["gaff"] = openmm_runtime.run_gaff_smoke()
    except openmm_runtime.OpenMMEnvironmentError as exc:
        check = mode if mode in {"core", "openff", "gaff"} else None
        return error_payload(str(exc), check=check)
    except openmm_runtime.OpenMMToolError as exc:
        return {
            "status": "error",
            "failure_type": openmm_runtime.TOOL_FAILURE,
            "message": str(exc),
            "versions": versions,
            "platforms": platforms,
            "checks": checks,
        }

    return {
        "status": "ok",
        "failure_type": None,
        "message": None,
        "versions": versions,
        "platforms": platforms,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["all", "core", "openff", "gaff"], default="all")
    args = parser.parse_args()

    payload = build_payload(args.mode)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/test_openmm_openff_env_script.py -v
```

Expected: all tests in `tests/test_openmm_openff_env_script.py` pass without OpenMM/OpenFF installed.

- [ ] **Step 6: Run manual missing-environment smoke**

Run:

```bash
uv run python scripts/check_openmm_openff_env.py --mode openff
```

Expected in the default environment without optional packages: exits nonzero with JSON containing `"failure_type": "verifier_env_error"`.

- [ ] **Step 7: Run full tests**

Run:

```bash
uv run pytest
```

Expected: full suite passes.

- [ ] **Step 8: Commit**

Run:

```bash
git add src/verifiers/backends/openmm_runtime.py scripts/check_openmm_openff_env.py tests/test_openmm_openff_env_script.py
git commit -m "feat: add OpenMM OpenFF environment check"
```

---

### Task 3: Add OpenMM Core Fixed-Fixture Backend

**Files:**
- Create: `src/verifiers/backends/openmm_core_properties.py`
- Create: `tests/test_openmm_core_backend.py`

- [ ] **Step 1: Write failing backend tests**

Create `tests/test_openmm_core_backend.py`:

```python
from __future__ import annotations

import pytest

from verifiers.backends import openmm_core_properties
from verifiers.backends.openmm_runtime import OpenMMEnvironmentError, OpenMMToolError


SPEC = {
    "verifier_id": "openmm_core_energy_drop_v1",
    "verifier_image": "verifier-grounded:dev",
    "property_name": "energy_drop_kj_mol",
    "backend": {"type": "openmm_core", "platform": "Reference"},
}
TASK = {"task_id": "openmm_core_backend_probe"}
CONSTRAINT = {"type": "minimize", "property": "energy_drop_kj_mol", "lower": 0.0, "upper": 10.0}


def test_openmm_core_backend_scores_mocked_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_compute(backend: dict) -> dict[str, float | str]:
        assert backend["platform"] == "Reference"
        return {
            "selected_platform": "Reference",
            "initial_energy_kj_mol": 4.5,
            "minimized_energy_kj_mol": 0.5,
            "energy_drop_kj_mol": 4.0,
            "final_max_force_kj_mol_nm": 0.01,
        }

    monkeypatch.setattr(openmm_core_properties, "compute_core_properties", fake_compute)

    result = openmm_core_properties.evaluate_openmm_core_constraint({}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "ok"
    assert result["properties"]["energy_drop_kj_mol"] == 4.0
    assert result["scores"]["constraint_scores"][0]["property"] == "energy_drop_kj_mol"
    assert result["failure_type"] is None


def test_openmm_core_backend_reports_env_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_env(backend: dict) -> dict[str, float | str]:
        raise OpenMMEnvironmentError("missing optional dependency: openmm")

    monkeypatch.setattr(openmm_core_properties, "compute_core_properties", missing_env)

    result = openmm_core_properties.evaluate_openmm_core_constraint({}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_env_error"
    assert "openmm" in result["message"]


def test_openmm_core_backend_reports_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def tool_failure(backend: dict) -> dict[str, float | str]:
        raise OpenMMToolError("OpenMM energy was not finite")

    monkeypatch.setattr(openmm_core_properties, "compute_core_properties", tool_failure)

    result = openmm_core_properties.evaluate_openmm_core_constraint({}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_tool_error"
    assert "not finite" in result["message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_openmm_core_backend.py -v
```

Expected: fails because `openmm_core_properties.py` does not exist.

- [ ] **Step 3: Implement OpenMM core backend**

Create `src/verifiers/backends/openmm_core_properties.py`:

```python
"""OpenMM core fixed-fixture backend."""

from __future__ import annotations

from importlib import metadata
from typing import Any

from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.backends.openmm_runtime import (
    ENV_FAILURE,
    TOOL_FAILURE,
    OpenMMEnvironmentError,
    OpenMMToolError,
    run_core_smoke,
)
from verifiers.result_schema import base_result, error_result


def evaluate_openmm_core_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = base_result(task["task_id"], spec.get("verifier_id"), openmm_core_versions(spec))
    property_name = spec.get("property_name")
    allowed_properties = {property_name, *(spec.get("additional_property_names") or [])}
    if constraint.get("property") not in allowed_properties:
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )

    try:
        properties = compute_core_properties(spec.get("backend") or {})
    except OpenMMEnvironmentError as exc:
        return error_result(result, ENV_FAILURE, str(exc))
    except OpenMMToolError as exc:
        return error_result(result, TOOL_FAILURE, str(exc))
    except Exception as exc:
        return error_result(result, TOOL_FAILURE, f"OpenMM core calculation failed: {exc}")

    try:
        property_score = score_constraint(properties, constraint)
    except Exception as exc:
        return error_result(result, "verifier_spec_error", f"constraint scoring failed: {exc}", properties=properties)

    result.update(
        {
            "status": "ok",
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [
                    {"property": constraint["property"], "type": constraint["type"], "score": property_score}
                ],
                "property_score": property_score,
                "score": property_score,
            },
            "failure_type": None,
            "message": None,
        }
    )
    return result


def compute_core_properties(backend: dict[str, Any]) -> dict[str, float | str]:
    preferred_platform = str(backend.get("platform", "Reference"))
    smoke = run_core_smoke(preferred_platform=preferred_platform)
    return {
        "selected_platform": str(smoke["selected_platform"]),
        "initial_energy_kj_mol": float(smoke["initial_energy_kj_mol"]),
        "minimized_energy_kj_mol": float(smoke["minimized_energy_kj_mol"]),
        "energy_drop_kj_mol": float(smoke["energy_drop_kj_mol"]),
        "final_max_force_kj_mol_nm": float(smoke["final_max_force_kj_mol_nm"]),
    }


def openmm_core_versions(spec: dict[str, Any]) -> dict[str, Any]:
    versions = {"verifier_image": spec.get("verifier_image"), "openmm_core_backend": "fixed_fixture_v1"}
    try:
        versions["openmm"] = metadata.version("openmm")
    except metadata.PackageNotFoundError:
        versions["openmm"] = None
    return versions
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_openmm_core_backend.py -v
```

Expected: all tests in `tests/test_openmm_core_backend.py` pass without OpenMM installed.

- [ ] **Step 5: Run full tests**

Run:

```bash
uv run pytest
```

Expected: full suite passes.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/verifiers/backends/openmm_core_properties.py tests/test_openmm_core_backend.py
git commit -m "feat: add OpenMM core backend"
```

---

### Task 4: Add OpenFF Ligand Backend With GAFF Mode Boundary

**Files:**
- Create: `src/verifiers/backends/openmm_openff_properties.py`
- Create: `tests/test_openmm_openff_backend.py`

- [ ] **Step 1: Write failing ligand backend tests**

Create `tests/test_openmm_openff_backend.py`:

```python
from __future__ import annotations

import pytest

from verifiers.backends import openmm_openff_properties
from verifiers.backends.openmm_runtime import OpenMMEnvironmentError, OpenMMToolError


SPEC = {
    "verifier_id": "openmm_openff_ligand_energy_drop_v1",
    "verifier_image": "verifier-grounded:dev",
    "property_name": "energy_drop_kj_mol",
    "backend": {
        "type": "openmm_openff_ligand",
        "forcefield_family": "openff",
        "forcefield_name": "openff-2.2.1.offxml",
        "platform": "Reference",
    },
    "domain": {
        "allowed_elements": ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
        "heavy_atom_count": [2, 60],
        "formal_charge": [-1, 1],
    },
}
TASK = {"task_id": "openmm_openff_backend_probe"}
CONSTRAINT = {"type": "minimize", "property": "energy_drop_kj_mol", "lower": 0.0, "upper": 20.0}


def test_openmm_openff_backend_scores_mocked_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_compute(smiles: str, backend: dict) -> dict[str, float | int | str]:
        assert smiles == "CCO"
        assert backend["forcefield_family"] == "openff"
        return {
            "forcefield_family": "openff",
            "forcefield_name": "openff-2.2.1.offxml",
            "charge_method": "am1bcc",
            "parameterization_success": 1,
            "system_particle_count": 9,
            "selected_platform": "Reference",
            "initial_energy_kj_mol": 8.0,
            "minimized_energy_kj_mol": 1.0,
            "energy_drop_kj_mol": 7.0,
            "final_max_force_kj_mol_nm": 0.03,
        }

    monkeypatch.setattr(openmm_openff_properties, "compute_ligand_properties", fake_compute)

    result = openmm_openff_properties.evaluate_openmm_openff_constraint({"smiles": "CCO"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["energy_drop_kj_mol"] == 7.0
    assert result["failure_type"] is None


def test_openmm_openff_backend_rejects_invalid_smiles() -> None:
    result = openmm_openff_properties.evaluate_openmm_openff_constraint(
        {"smiles": "not a smiles"},
        TASK,
        CONSTRAINT,
        SPEC,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_openmm_openff_backend_rejects_multi_component_smiles() -> None:
    result = openmm_openff_properties.evaluate_openmm_openff_constraint(
        {"smiles": "CCO.O"},
        TASK,
        CONSTRAINT,
        SPEC,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "validity_error"


def test_openmm_openff_backend_rejects_disallowed_element() -> None:
    result = openmm_openff_properties.evaluate_openmm_openff_constraint(
        {"smiles": "C[Na]"},
        TASK,
        CONSTRAINT,
        {**SPEC, "domain": {**SPEC["domain"], "allowed_elements": ["H", "C"]}},
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"


def test_openmm_openff_backend_reports_env_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_env(smiles: str, backend: dict) -> dict[str, float | int | str]:
        raise OpenMMEnvironmentError("missing optional dependency: openff.toolkit")

    monkeypatch.setattr(openmm_openff_properties, "compute_ligand_properties", missing_env)

    result = openmm_openff_properties.evaluate_openmm_openff_constraint({"smiles": "CCO"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_env_error"
    assert "openff.toolkit" in result["message"]


def test_openmm_openff_backend_reports_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def tool_failure(smiles: str, backend: dict) -> dict[str, float | int | str]:
        raise OpenMMToolError("OpenFF parameterization failed: no parameters")

    monkeypatch.setattr(openmm_openff_properties, "compute_ligand_properties", tool_failure)

    result = openmm_openff_properties.evaluate_openmm_openff_constraint({"smiles": "CCO"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_tool_error"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_openmm_openff_backend.py -v
```

Expected: fails because `openmm_openff_properties.py` does not exist.

- [ ] **Step 3: Implement ligand backend**

Create `src/verifiers/backends/openmm_openff_properties.py`:

```python
"""OpenMM + OpenFF/GAFF ligand minimization backend."""

from __future__ import annotations

from importlib import metadata
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.backends.openmm_runtime import (
    DEFAULT_OPENFF_FORCEFIELD,
    ENV_FAILURE,
    TOOL_FAILURE,
    OpenMMEnvironmentError,
    OpenMMToolError,
    run_gaff_smoke,
    run_openff_smoke,
)
from verifiers.result_schema import base_result, error_result


DEFAULT_BACKEND = {
    "forcefield_family": "openff",
    "forcefield_name": DEFAULT_OPENFF_FORCEFIELD,
    "platform": "Reference",
}


def evaluate_openmm_openff_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = base_result(task["task_id"], spec.get("verifier_id"), openmm_openff_versions(spec))
    property_name = spec.get("property_name")
    allowed_properties = {property_name, *(spec.get("additional_property_names") or [])}
    if constraint.get("property") not in allowed_properties:
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
        ligand_properties = compute_ligand_properties(canonical_smiles, spec.get("backend") or {})
    except OpenMMEnvironmentError as exc:
        return error_result(result, ENV_FAILURE, str(exc), properties=domain_properties)
    except OpenMMToolError as exc:
        return error_result(result, TOOL_FAILURE, str(exc), properties=domain_properties)
    except Exception as exc:
        return error_result(result, TOOL_FAILURE, f"OpenMM/OpenFF calculation failed: {exc}", properties=domain_properties)

    properties = {**domain_properties, **ligand_properties}
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
                "constraint_scores": [
                    {"property": constraint["property"], "type": constraint["type"], "score": property_score}
                ],
                "property_score": property_score,
                "score": property_score,
            },
            "failure_type": None,
            "message": None,
        }
    )
    return result


def compute_ligand_properties(smiles: str, backend: dict[str, Any]) -> dict[str, float | int | str]:
    config = {**DEFAULT_BACKEND, **backend}
    family = str(config.get("forcefield_family", "openff")).lower()
    platform = str(config.get("platform", "Reference"))
    if family == "openff":
        smoke = run_openff_smoke(
            smiles=smiles,
            forcefield_name=str(config.get("forcefield_name", DEFAULT_OPENFF_FORCEFIELD)),
            preferred_platform=platform,
        )
    elif family == "gaff":
        smoke = run_gaff_smoke(preferred_platform=platform)
    else:
        raise OpenMMToolError(f"unsupported forcefield_family: {family}")

    result: dict[str, float | int | str] = {
        "forcefield_family": family,
        "forcefield_name": str(config.get("forcefield_name", DEFAULT_OPENFF_FORCEFIELD)),
        "parameterization_success": int(smoke.get("parameterization_success", 1)),
    }
    for key, value in smoke.items():
        if key == "status":
            continue
        if isinstance(value, (int, float, str)):
            result[key] = value
    return result


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


def openmm_openff_versions(spec: dict[str, Any]) -> dict[str, Any]:
    versions = {"verifier_image": spec.get("verifier_image"), "openmm_openff_backend": "ligand_minimization_v1"}
    for distribution, key in [
        ("openmm", "openmm"),
        ("openff-toolkit", "openff_toolkit"),
        ("openff-interchange", "openff_interchange"),
        ("openmmforcefields", "openmmforcefields"),
    ]:
        try:
            versions[key] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[key] = None
    return versions
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_openmm_openff_backend.py -v
```

Expected: all tests in `tests/test_openmm_openff_backend.py` pass without OpenMM/OpenFF installed.

- [ ] **Step 5: Run OpenMM-focused tests**

Run:

```bash
uv run pytest tests/test_openmm_openff_env_script.py tests/test_openmm_core_backend.py tests/test_openmm_openff_backend.py -v
```

Expected: all OpenMM-related tests pass without optional conda environment.

- [ ] **Step 6: Run full tests**

Run:

```bash
uv run pytest
```

Expected: full suite passes.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/verifiers/backends/openmm_openff_properties.py tests/test_openmm_openff_backend.py
git commit -m "feat: add OpenMM OpenFF ligand backend"
```

---

### Task 5: Add Backend Documentation And No-Task Guard

**Files:**
- Create: `docs/tracks/OpenMM-OpenFF.md`
- Create: `tests/test_openmm_openff_no_tasks.py`

- [ ] **Step 1: Write no-task guard tests**

Create `tests/test_openmm_openff_no_tasks.py`:

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_openmm_backend_does_not_create_task_pack() -> None:
    assert not (ROOT / "tasks" / "openmm_openff").exists()
    assert not (ROOT / "tasks" / "openmm_core").exists()


def test_openmm_backend_is_not_registered_as_formal_track() -> None:
    registry = (ROOT / "src" / "verifier_grounded_benchmark" / "registry.py").read_text()

    assert "openmm_openff" not in registry
    assert "openmm_core" not in registry
```

- [ ] **Step 2: Run test to verify current no-task state**

Run:

```bash
uv run pytest tests/test_openmm_openff_no_tasks.py -v
```

Expected: passes before documentation is added.

- [ ] **Step 3: Create backend documentation**

Create `docs/tracks/OpenMM-OpenFF.md`:

```markdown
# OpenMM + OpenFF/GAFF Backend Status

Updated: 2026-07-03

## Status

This is a local optional backend/runtime path. It is not a formal benchmark
track and is not registered in the public suite.

This round intentionally does not add OpenMM task packs, sample answers,
verifier specs, task prompts, thresholds, or calibration data.

## Local Environment

Create the optional conda environment:

```bash
mamba env create -f envs/openmm-openff.yml
conda activate vgb-openmm-openff
python scripts/check_openmm_openff_env.py --mode all
```

Use `conda env create -f envs/openmm-openff.yml` only when `mamba` is
unavailable.

## Failure Types

- `verifier_env_error`: optional conda environment is missing, inactive, missing
  required packages, missing usable OpenMM platform, or missing GAFF/AmberTools
  support for GAFF mode.
- `verifier_tool_error`: OpenMM/OpenFF/GAFF is installed, but parameterization,
  system creation, minimization, or energy/force evaluation fails.
- `parse_error`: candidate molecular input cannot be parsed.
- `domain_error`: candidate is outside allowed element, charge, atom-count, or
  component-count domain.

## Implemented Backend Surfaces

- `src/verifiers/backends/openmm_core_properties.py`
  - fixed fixture OpenMM energy/minimization smoke
  - no arbitrary SMILES

- `src/verifiers/backends/openmm_openff_properties.py`
  - single-component SMILES ligand path
  - OpenFF/SMIRNOFF primary mode
  - GAFF mode kept behind explicit backend config

## Non-Goals

- No formal OpenMM task pack.
- No benchmark thresholds or task prompts.
- No binding affinity, FEP, docking, long MD, or free-energy scoring.
- No default dependency changes.
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_openmm_openff_no_tasks.py -v
```

Expected: no-task guard passes.

- [ ] **Step 5: Run full tests**

Run:

```bash
uv run pytest
```

Expected: full suite passes.

- [ ] **Step 6: Commit**

Run:

```bash
git add docs/tracks/OpenMM-OpenFF.md tests/test_openmm_openff_no_tasks.py
git commit -m "docs: document OpenMM OpenFF backend status"
```

---

### Task 6: Optional Live Smoke In Conda Environment

**Files:**
- No required file changes.
- Optionally create `docs/research/2026-07-03-openmm-openff-local-env-smoke.md` only if live conda smoke reveals important environment-specific findings.

- [ ] **Step 1: Check whether conda environment is available**

Run:

```bash
conda env list
```

Expected: if `vgb-openmm-openff` exists, continue. If it does not exist and the user has not asked for live installation, skip live smoke and report that only default mocked tests were run.

- [ ] **Step 2: Run OpenMM core live smoke when environment exists**

Run:

```bash
conda run -n vgb-openmm-openff python scripts/check_openmm_openff_env.py --mode core
```

Expected: JSON with `"status": "ok"` and `checks.core.status == "ok"`.

- [ ] **Step 3: Run OpenFF live smoke when environment exists**

Run:

```bash
conda run -n vgb-openmm-openff python scripts/check_openmm_openff_env.py --mode openff
```

Expected: JSON with `"status": "ok"` and `checks.openff.status == "ok"`. If this fails because a package is missing or a toolkit path is unavailable, the JSON must use `"failure_type": "verifier_env_error"`.

- [ ] **Step 4: Run GAFF live smoke when environment exists**

Run:

```bash
conda run -n vgb-openmm-openff python scripts/check_openmm_openff_env.py --mode gaff
```

Expected: either JSON with `"status": "ok"` or JSON with `"failure_type": "verifier_env_error"` naming the missing GAFF/AmberTools dependency. A missing GAFF path must not be reported as `verifier_tool_error`.

- [ ] **Step 5: Commit live-smoke research note only if created**

If `docs/research/2026-07-03-openmm-openff-local-env-smoke.md` was created, run:

```bash
uv run pytest
git add docs/research/2026-07-03-openmm-openff-local-env-smoke.md
git commit -m "docs: record OpenMM OpenFF local smoke results"
```

Expected: full suite passes before commit.

---

## Final Verification

After all implementation commits:

- [ ] **Run full default test suite**

```bash
uv run pytest
```

Expected: full suite passes without OpenMM/OpenFF installed.

- [ ] **Verify no OpenMM tasks were created**

```bash
find tasks -maxdepth 2 -type f | sort | rg -i "openmm|openff|gaff" || true
```

Expected: no output.

- [ ] **Verify default dependencies remain clean**

```bash
rg -n '"openmm|"openff-toolkit|"openff-interchange|"openmmforcefields|"ambertools' pyproject.toml
```

Expected: no output.

- [ ] **Verify working tree**

```bash
git status --short --branch
```

Expected: clean working tree after the final commit.

## Self-Review Notes

Spec coverage:

- Local conda optional environment: Task 1.
- Structured check script: Task 2.
- `verifier_env_error` failure taxonomy: Tasks 2, 3, and 4.
- OpenMM core backend: Task 3.
- OpenFF ligand backend and GAFF boundary: Task 4.
- No task design or registration: Task 5 and final verification.
- Default tests independent of optional environment: every task runs through `uv run pytest`.

The plan deliberately excludes formal task packs, thresholds, sample answers,
and registry updates.
