# TorchANI ANI-2x and MACE-MP Backends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build optional native TorchANI ANI-2x and MACE-MP verifier backends with property scripts, environment diagnostics, tests, and track documents, without adding formal task packs or default runtime dependencies.

**Architecture:** Follow the existing property-script contract: each script reads verifier JSON from stdin and writes standardized result JSON. TorchANI owns a direct-XYZ input path like the xTB backend, while MACE-MP owns a CIF input path like the MatGL backend. Do not add a shared `ase_inputs.py` abstraction in this round; each backend keeps its input parsing local so the two input domains remain independent.

**Tech Stack:** Python 3.12, pytest, ASE, TorchANI 2.8.2, MACE-Torch 0.3.16, pymatgen for CIF parsing, existing `verifiers.script_cli`, `verifiers.result_schema`, and `verifiers.scoring`.

---

## File Structure

- Modify `pyproject.toml`
  - Add optional dependency groups `torchani` and `mace`.
  - Do not add TorchANI, MACE, ASE, pymatgen, or model packages to default `dependencies`.
- Create `src/verifiers/backends/torchani_properties.py`
  - Native TorchANI ANI-2x evaluator for direct XYZ candidates.
  - Owns XYZ parsing, ASE `Atoms` conversion, TorchANI domain checks, and ANI-2x prediction.
- Create `src/verifiers/quantum_ml/__init__.py`
  - Package marker for quantum-ML verifier scripts.
- Create `src/verifiers/quantum_ml/torchani_property_script.py`
  - Shared property script wrapper for TorchANI properties.
- Create `src/verifiers/quantum_ml/torchani_total_energy.py`
  - Entry point for `torchani_total_energy_hartree`.
- Create `src/verifiers/quantum_ml/torchani_energy_per_atom.py`
  - Entry point for `torchani_energy_per_atom_hartree`.
- Create `src/verifiers/quantum_ml/torchani_max_force.py`
  - Entry point for `torchani_max_force_hartree_per_angstrom`.
- Create `src/verifiers/backends/mace_mp_properties.py`
  - Native MACE-MP evaluator for CIF candidates.
  - Owns CIF parsing, pymatgen-to-ASE conversion, material domain checks, and MACE-MP prediction.
- Create `src/verifiers/materials/mace_mp_property_script.py`
  - Shared property script wrapper for MACE-MP properties.
- Create `src/verifiers/materials/mace_mp_energy.py`
  - Entry point for `mace_mp_energy_ev`.
- Create `src/verifiers/materials/mace_mp_energy_per_atom.py`
  - Entry point for `mace_mp_energy_per_atom_ev`.
- Create `src/verifiers/materials/mace_mp_max_force.py`
  - Entry point for `mace_mp_max_force_ev_per_angstrom`.
- Create `src/verifiers/materials/mace_mp_stress_norm.py`
  - Entry point for `mace_mp_stress_norm_ev_per_angstrom3`.
- Create `scripts/check_torchani_env.py`
  - Structured TorchANI diagnostic with an embedded water XYZ smoke.
- Create `scripts/check_mace_mp_env.py`
  - Structured MACE-MP diagnostic with an embedded silicon CIF smoke.
- Create `docs/tracks/TorchANI.md`
  - Backend capability document.
- Create `docs/tracks/MACE-MP.md`
  - Backend capability document.
- Create `tests/test_mlip_optional_dependencies.py`
  - Dependency grouping tests.
- Create `tests/test_torchani_properties_backend.py`
  - TorchANI backend unit tests using fake model objects.
- Create `tests/test_mace_mp_properties_backend.py`
  - MACE-MP backend unit tests using fake calculator output.
- Create `tests/test_torchani_mace_task_scripts.py`
  - Script wrapper mismatch and dispatch tests.
- Create `tests/test_torchani_mace_env_scripts.py`
  - Environment diagnostic JSON tests.
- Create `tests/test_torchani_mace_live_smoke.py`
  - Opt-in real model smoke tests gated by `VGB_RUN_MLIP_SMOKE=1`.

Do not add or modify `tasks/`, builtin registry entries, formal verifier specs, or sample answers in this implementation round.

## Deployment Boundaries

TorchANI deploys as a native optional runtime:

```yaml
backend:
  type: native_torchani
property_name: torchani_total_energy_hartree
torchani:
  model_name: ANI2x
  device: cpu
```

MACE-MP deploys as a native optional runtime:

```yaml
backend:
  type: native_mace_mp
property_name: mace_mp_energy_per_atom_ev
mace_mp:
  model: small
  device: cpu
  default_dtype: float32
```

The first implementation exposes backend capabilities only. Formal tasks should be designed later after calibration because absolute energies depend strongly on composition and input domain.

## Property Names

TorchANI properties:

| Property | Unit | Meaning |
|---|---:|---|
| `torchani_total_energy_hartree` | Hartree | ANI-2x total molecular energy for the submitted XYZ. |
| `torchani_energy_per_atom_hartree` | Hartree/atom | Total energy divided by atom count. |
| `torchani_max_force_hartree_per_angstrom` | Hartree/Angstrom | Maximum force-vector norm over atoms. |

MACE-MP properties:

| Property | Unit | Meaning |
|---|---:|---|
| `mace_mp_energy_ev` | eV | MACE-MP total potential energy for the submitted CIF structure. |
| `mace_mp_energy_per_atom_ev` | eV/atom | Total energy divided by atom count. |
| `mace_mp_max_force_ev_per_angstrom` | eV/Angstrom | Maximum force-vector norm over atoms. |
| `mace_mp_stress_norm_ev_per_angstrom3` | eV/Angstrom^3 | Euclidean norm of ASE 6-component stress. |

## Task 1: Optional Dependency Groups

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_mlip_optional_dependencies.py`

- [ ] **Step 1: Write failing dependency grouping tests**

Create `tests/test_mlip_optional_dependencies.py`:

```python
from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_torchani_and_mace_are_optional_dependencies_only() -> None:
    payload = pyproject()
    default_dependencies = payload["project"]["dependencies"]
    optional = payload["project"]["optional-dependencies"]
    groups = payload["dependency-groups"]

    assert all("torchani" not in item.lower() for item in default_dependencies)
    assert all("mace" not in item.lower() for item in default_dependencies)
    assert "torchani" in optional
    assert "mace" in optional
    assert "torchani" in groups
    assert "mace" in groups


def test_torchani_optional_group_pins_model_runtime() -> None:
    optional = pyproject()["project"]["optional-dependencies"]

    assert "torchani==2.8.2" in optional["torchani"]
    assert "ase==3.28.0" in optional["torchani"]


def test_mace_optional_group_pins_model_runtime() -> None:
    optional = pyproject()["project"]["optional-dependencies"]

    assert "mace-torch==0.3.16" in optional["mace"]
    assert "ase==3.28.0" in optional["mace"]
    assert "pymatgen==2026.5.4" in optional["mace"]
```

- [ ] **Step 2: Run dependency grouping tests and verify they fail**

Run:

```bash
uv run pytest tests/test_mlip_optional_dependencies.py -v
```

Expected: FAIL because `torchani` and `mace` optional groups do not exist.

- [ ] **Step 3: Add optional dependency groups**

Modify `pyproject.toml`:

```toml
[project.optional-dependencies]
torchani = [
    "ase==3.28.0",
    "torchani==2.8.2",
]
mace = [
    "ase==3.28.0",
    "mace-torch==0.3.16",
    "pymatgen==2026.5.4",
]

[dependency-groups]
torchani = [
    "ase==3.28.0",
    "torchani==2.8.2",
]
mace = [
    "ase==3.28.0",
    "mace-torch==0.3.16",
    "pymatgen==2026.5.4",
]
```

Keep the existing `future-backends`, `materials`, and `dev` groups unchanged.

- [ ] **Step 4: Run dependency grouping tests and dry-run resolves**

Run:

```bash
uv run pytest tests/test_mlip_optional_dependencies.py -v
uv pip install --dry-run --target /tmp/vgb-dryrun-torchani torchani==2.8.2
uv pip install --dry-run --target /tmp/vgb-dryrun-mace mace-torch==0.3.16
```

Expected: tests PASS. Both dry-run commands resolve packages on macOS arm64/Python 3.12.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/test_mlip_optional_dependencies.py
git commit -m "build: add optional MLIP dependency groups"
```

## Task 2: TorchANI Backend

**Files:**
- Create: `src/verifiers/backends/torchani_properties.py`
- Test: `tests/test_torchani_properties_backend.py`

- [ ] **Step 1: Write failing TorchANI backend tests**

Create `tests/test_torchani_properties_backend.py`:

```python
from __future__ import annotations

import pytest

from verifiers.backends import torchani_properties


WATER_XYZ = """3
water
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284
"""


def spec(property_name: str = "torchani_total_energy_hartree") -> dict:
    return {
        "verifier_id": f"{property_name}_ani2x_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": property_name,
        "backend": {"type": "native_torchani"},
        "torchani": {"model_name": "ANI2x", "device": "cpu"},
        "domain": {
            "allowed_elements": ["H", "C", "N", "O", "F", "S", "Cl"],
            "atom_count": [2, 80],
            "heavy_atom_count": [1, 40],
        },
    }


def task(property_name: str, constraint_type: str = "window") -> dict:
    if constraint_type == "minimize_bounded":
        constraint = {"type": constraint_type, "property": property_name, "lower": 0.0, "upper": 0.2}
    else:
        constraint = {"type": "window", "property": property_name, "min": -80.0, "max": -70.0, "sigma": 2.0}
    constraint["verifier_id"] = f"{property_name}_ani2x_v1"
    return {"task_id": f"{property_name}_task", "constraints": [constraint]}


def test_torchani_scores_fake_total_energy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        torchani_properties,
        "predict_torchani_properties",
        lambda atoms, current_spec: {
            "torchani_total_energy_hartree": -76.38121032714844,
            "torchani_energy_per_atom_hartree": -25.460403442382812,
            "torchani_max_force_hartree_per_angstrom": 0.01,
        },
    )

    current_task = task("torchani_total_energy_hartree")
    result = torchani_properties.evaluate_torchani_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "ok"
    assert result["properties"]["torchani_total_energy_hartree"] == pytest.approx(-76.38121032714844)
    assert result["properties"]["torchani_energy_per_atom_hartree"] == pytest.approx(-25.460403442382812)
    assert result["properties"]["torchani_max_force_hartree_per_angstrom"] == pytest.approx(0.01)
    assert result["properties"]["formula"] == "H2O"
    assert result["scores"]["score"] == 1.0


def test_torchani_scores_force_property(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        torchani_properties,
        "predict_torchani_properties",
        lambda atoms, current_spec: {
            "torchani_total_energy_hartree": -76.0,
            "torchani_energy_per_atom_hartree": -25.333333333333332,
            "torchani_max_force_hartree_per_angstrom": 0.05,
        },
    )
    current_task = task("torchani_max_force_hartree_per_angstrom", "minimize_bounded")

    result = torchani_properties.evaluate_torchani_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec("torchani_max_force_hartree_per_angstrom"),
    )

    assert result["status"] == "ok"
    assert result["scores"]["score"] == pytest.approx(0.75)


def test_torchani_rejects_property_mismatch() -> None:
    current_task = task("torchani_total_energy_hartree")

    result = torchani_properties.evaluate_torchani_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec("torchani_energy_per_atom_hartree"),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_torchani_maps_missing_xyz_to_parse_error() -> None:
    current_task = task("torchani_total_energy_hartree")

    result = torchani_properties.evaluate_torchani_constraint(
        {"smiles": "O"},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_torchani_maps_model_import_error_to_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_model(atoms: object, current_spec: dict) -> dict:
        raise ModuleNotFoundError("No module named 'torchani'")

    monkeypatch.setattr(torchani_properties, "predict_torchani_properties", missing_model)
    current_task = task("torchani_total_energy_hartree")

    result = torchani_properties.evaluate_torchani_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert result["properties"]["formula"] == "H2O"
```

- [ ] **Step 2: Run TorchANI backend tests and verify they fail**

Run:

```bash
uv run pytest tests/test_torchani_properties_backend.py -v
```

Expected: FAIL with `ImportError` because `torchani_properties.py` does not exist.

- [ ] **Step 3: Implement TorchANI backend**

Create `src/verifiers/backends/torchani_properties.py` with these public functions and behavior:

- `evaluate_torchani_constraint(candidate, task, constraint, spec) -> dict`
  - Use `base_result(task["task_id"], spec.get("verifier_id"), torchani_versions(spec))`.
  - Reject mismatch unless `constraint["property"]` is `spec["property_name"]` or listed in `spec["additional_property_names"]`.
  - Accept only `candidate["xyz"]`.
  - Call local `parse_xyz_atoms(xyz)` in the same module.
  - Call local `inspect_xyz_atoms(atoms)` in the same module.
  - Call local `check_domain(properties, spec.get("domain") or {})` in the same module.
  - Call `predict_torchani_properties`.
  - Score with existing `score_constraint`.
  - Map `ModuleNotFoundError` and `ImportError` to `verifier_environment_error`.
  - Map all other model failures to `verifier_tool_error`.
- `parse_xyz_atoms(xyz: str) -> Any`
  - Import `ase.io.read` inside the function.
  - Parse the direct XYZ string through `read(StringIO(xyz), format="xyz")`.
  - Raise `ValueError("candidate must include an XYZ string")` for missing input.
  - Raise `ValueError(f"XYZ parse failed: {exc}")` for malformed XYZ.
- `inspect_xyz_atoms(atoms) -> dict[str, Any]`
  - Return `atom_count`, `heavy_atom_count`, sorted `elements`, Hill `formula`, and `pbc`.
  - For TorchANI, reject periodic input through domain checks unless all `pbc` values are false.
- `check_domain(properties, domain) -> str | None`
  - Support `allowed_elements`, `atom_count`, and `heavy_atom_count`.
  - Return messages matching the test assertions, such as `disallowed elements: Si` and `atom_count outside [2, 80]`.
- `predict_torchani_properties(atoms, spec) -> dict[str, float | str]`
  - Import `torch` and `torchani` inside the function.
  - Load only `ANI2x`; unsupported `model_name` raises `ValueError("unsupported TorchANI model_name: ...")`.
  - Use `torchani.models.ANI2x(periodic_table_index=True).to(device)`.
  - Convert ASE symbols to atomic numbers and positions to tensors with shape `(1, n_atoms)` and `(1, n_atoms, 3)`.
  - Set `coordinates.requires_grad_(True)`.
  - Get model energy and compute forces as `-torch.autograd.grad(energy.sum(), coordinates)[0]`.
  - Return total energy, energy per atom, max force norm, and units.
- `torchani_versions(spec) -> dict`
  - Include `verifier_image`, `torchani_backend`, configured model name, and package versions for `torchani`, `torch`, and `ase` when installed.

Use `functools.lru_cache(maxsize=None)` for model loading:

```python
@lru_cache(maxsize=None)
def load_torchani_model(model_name: str, device: str) -> Any:
    if model_name != "ANI2x":
        raise ValueError(f"unsupported TorchANI model_name: {model_name}")
    import torchani

    return torchani.models.ANI2x(periodic_table_index=True).to(device)
```

Supported properties must be:

```python
SUPPORTED_TORCHANI_PROPERTIES = {
    "torchani_total_energy_hartree",
    "torchani_energy_per_atom_hartree",
    "torchani_max_force_hartree_per_angstrom",
}
```

- [ ] **Step 4: Run TorchANI backend tests**

Run:

```bash
uv run pytest tests/test_torchani_properties_backend.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/verifiers/backends/torchani_properties.py tests/test_torchani_properties_backend.py
git commit -m "feat: add TorchANI backend"
```

## Task 3: TorchANI Property Scripts

**Files:**
- Create: `src/verifiers/quantum_ml/__init__.py`
- Create: `src/verifiers/quantum_ml/torchani_property_script.py`
- Create: `src/verifiers/quantum_ml/torchani_total_energy.py`
- Create: `src/verifiers/quantum_ml/torchani_energy_per_atom.py`
- Create: `src/verifiers/quantum_ml/torchani_max_force.py`
- Test: `tests/test_torchani_mace_task_scripts.py`

- [ ] **Step 1: Write failing TorchANI script tests**

Create the TorchANI section of `tests/test_torchani_mace_task_scripts.py`:

```python
from __future__ import annotations

from pathlib import Path

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def torchani_payload(spec_property: str = "torchani_energy_per_atom_hartree") -> dict:
    return {
        "task": {"task_id": "torchani_script_001"},
        "constraint": {
            "type": "window",
            "property": "torchani_total_energy_hartree",
            "verifier_id": "torchani_total_energy_ani2x_v1",
            "min": -80.0,
            "max": -70.0,
            "sigma": 2.0,
        },
        "verifier_spec": {
            "verifier_id": "torchani_total_energy_ani2x_v1",
            "verification_script": "verifiers/quantum_ml/torchani_total_energy.py",
            "property_name": spec_property,
            "backend": {"type": "native_torchani"},
        },
        "candidate": {},
    }


def test_torchani_property_script_rejects_property_mismatch() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "quantum_ml" / "torchani_total_energy.py",
        torchani_payload(),
        timeout_seconds=60,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
    assert result["message"] == (
        "script property 'torchani_total_energy_hartree' does not match "
        "verifier_spec property 'torchani_energy_per_atom_hartree'"
    )
```

- [ ] **Step 2: Run script tests and verify they fail**

Run:

```bash
uv run pytest tests/test_torchani_mace_task_scripts.py::test_torchani_property_script_rejects_property_mismatch -v
```

Expected: FAIL because the TorchANI script package does not exist.

- [ ] **Step 3: Implement TorchANI script package**

Create `src/verifiers/quantum_ml/__init__.py`:

```python
"""Quantum-ML verifier script entrypoints."""
```

Create `src/verifiers/quantum_ml/torchani_property_script.py`:

```python
from __future__ import annotations

from verifiers.backends.torchani_properties import evaluate_torchani_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_torchani_constraint,
        sort_keys=True,
    )
```

Create `src/verifiers/quantum_ml/torchani_total_energy.py`:

```python
from verifiers.quantum_ml.torchani_property_script import main


if __name__ == "__main__":
    main("torchani_total_energy_hartree")
```

Create `src/verifiers/quantum_ml/torchani_energy_per_atom.py`:

```python
from verifiers.quantum_ml.torchani_property_script import main


if __name__ == "__main__":
    main("torchani_energy_per_atom_hartree")
```

Create `src/verifiers/quantum_ml/torchani_max_force.py`:

```python
from verifiers.quantum_ml.torchani_property_script import main


if __name__ == "__main__":
    main("torchani_max_force_hartree_per_angstrom")
```

- [ ] **Step 4: Run TorchANI script tests**

Run:

```bash
uv run pytest tests/test_torchani_mace_task_scripts.py::test_torchani_property_script_rejects_property_mismatch -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/verifiers/quantum_ml tests/test_torchani_mace_task_scripts.py
git commit -m "feat: add TorchANI property scripts"
```

## Task 4: MACE-MP Backend

**Files:**
- Create: `src/verifiers/backends/mace_mp_properties.py`
- Test: `tests/test_mace_mp_properties_backend.py`

- [ ] **Step 1: Write failing MACE-MP backend tests**

Create `tests/test_mace_mp_properties_backend.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from verifiers.backends import mace_mp_properties


SI_CIF = (Path(__file__).resolve().parent / "fixtures" / "Si.cif").read_text()


def spec(property_name: str = "mace_mp_energy_per_atom_ev") -> dict:
    return {
        "verifier_id": f"{property_name}_small_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": property_name,
        "backend": {"type": "native_mace_mp"},
        "mace_mp": {"model": "small", "device": "cpu", "default_dtype": "float32"},
        "domain": {
            "allowed_elements": ["Si"],
            "atom_count": [1, 8],
            "volume": [1.0, 300.0],
        },
    }


def task(property_name: str, constraint_type: str = "window") -> dict:
    if constraint_type == "minimize_bounded":
        constraint = {"type": constraint_type, "property": property_name, "lower": 0.0, "upper": 1.0}
    else:
        constraint = {"type": "window", "property": property_name, "min": -6.0, "max": -4.0, "sigma": 0.5}
    constraint["verifier_id"] = f"{property_name}_small_v1"
    return {"task_id": f"{property_name}_task", "constraints": [constraint]}


def test_mace_scores_fake_energy_per_atom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mace_mp_properties,
        "predict_mace_mp_properties",
        lambda atoms, current_spec: {
            "mace_mp_energy_ev": -10.738468170166016,
            "mace_mp_energy_per_atom_ev": -5.369234085083008,
            "mace_mp_max_force_ev_per_angstrom": 0.000001,
            "mace_mp_stress_norm_ev_per_angstrom3": 0.0152,
        },
    )
    current_task = task("mace_mp_energy_per_atom_ev")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": SI_CIF},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "ok"
    assert result["properties"]["mace_mp_energy_per_atom_ev"] == pytest.approx(-5.369234085083008)
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["properties"]["atom_count"] == 2
    assert result["scores"]["score"] == 1.0


def test_mace_scores_force_property(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mace_mp_properties,
        "predict_mace_mp_properties",
        lambda atoms, current_spec: {
            "mace_mp_energy_ev": -10.7,
            "mace_mp_energy_per_atom_ev": -5.35,
            "mace_mp_max_force_ev_per_angstrom": 0.25,
            "mace_mp_stress_norm_ev_per_angstrom3": 0.1,
        },
    )
    current_task = task("mace_mp_max_force_ev_per_angstrom", "minimize_bounded")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": SI_CIF},
        current_task,
        current_task["constraints"][0],
        spec("mace_mp_max_force_ev_per_angstrom"),
    )

    assert result["status"] == "ok"
    assert result["scores"]["score"] == pytest.approx(0.75)


def test_mace_rejects_invalid_cif() -> None:
    current_task = task("mace_mp_energy_per_atom_ev")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": "not a cif"},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_mace_domain_error_preserves_structure_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_predict(atoms: object, current_spec: dict) -> dict:
        raise AssertionError("model should not run after domain error")

    monkeypatch.setattr(mace_mp_properties, "predict_mace_mp_properties", fail_predict)
    current_spec = spec()
    current_spec["domain"] = {**current_spec["domain"], "allowed_elements": ["C"]}
    current_task = task("mace_mp_energy_per_atom_ev")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": SI_CIF},
        current_task,
        current_task["constraints"][0],
        current_spec,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["scores"]["validity_gate"] == 1.0


def test_mace_maps_missing_package_to_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_model(atoms: object, current_spec: dict) -> dict:
        raise ModuleNotFoundError("No module named 'mace'")

    monkeypatch.setattr(mace_mp_properties, "predict_mace_mp_properties", missing_model)
    current_task = task("mace_mp_energy_per_atom_ev")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": SI_CIF},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert result["properties"]["reduced_formula"] == "Si"
```

- [ ] **Step 2: Run MACE backend tests and verify they fail**

Run:

```bash
uv run pytest tests/test_mace_mp_properties_backend.py -v
```

Expected: FAIL with `ImportError` because `mace_mp_properties.py` does not exist.

- [ ] **Step 3: Implement MACE-MP backend**

Create `src/verifiers/backends/mace_mp_properties.py` with these public functions and behavior:

- `evaluate_mace_mp_constraint(candidate, task, constraint, spec) -> dict`
  - Use `base_result(task["task_id"], spec.get("verifier_id"), mace_mp_versions(spec))`.
  - Accept only `candidate["cif"]`.
  - Call local `parse_cif_atoms(cif)` in the same module.
  - Call local `inspect_structure(structure, atoms)` in the same module.
  - Call local `check_domain(properties, spec.get("domain") or {})` in the same module.
  - Call `predict_mace_mp_properties`.
  - Score with `score_constraint`.
  - Map `ModuleNotFoundError` and `ImportError` to `verifier_environment_error`.
  - Map all other model failures to `verifier_tool_error`.
- `parse_cif_atoms(cif: str) -> tuple[Any, Any]`
  - Import `pymatgen.core.Structure` and `pymatgen.io.ase.AseAtomsAdaptor` inside the function.
  - Parse the CIF with `Structure.from_str(cif, fmt="cif")`.
  - Convert the structure to ASE `Atoms`.
  - Raise `ValueError("candidate must include a CIF string")` for missing input.
  - Raise `ValueError(f"CIF parse failed: {exc}")` for malformed CIF.
- `inspect_structure(structure, atoms) -> dict[str, Any]`
  - Return `reduced_formula`, `atom_count`, `volume`, sorted `elements`, and `pbc`.
- `check_domain(properties, domain) -> str | None`
  - Support `allowed_elements`, `atom_count`, and `volume`.
  - Return messages matching MatGL conventions, such as `disallowed elements: Si` and `volume outside [1.0, 300.0]`.
- `predict_mace_mp_properties(atoms, spec) -> dict[str, float | str]`
  - Import `mace.calculators.mace_mp` inside the function.
  - Load cached calculator using `model`, `device`, and `default_dtype`.
  - Assign `atoms.calc = calculator`.
  - Compute `atoms.get_potential_energy()`, `atoms.get_forces()`, and `atoms.get_stress()`.
  - Return energy, energy per atom, max force vector norm, stress norm, and unit fields.
- `mace_mp_versions(spec) -> dict`
  - Include `verifier_image`, `mace_mp_backend`, configured model, and package versions for `mace-torch`, `torch`, `ase`, and `pymatgen` when installed.

Use `functools.lru_cache(maxsize=None)` for calculator loading:

```python
@lru_cache(maxsize=None)
def load_mace_mp_calculator(model: str, device: str, default_dtype: str) -> Any:
    from mace.calculators import mace_mp

    return mace_mp(model=model, device=device, default_dtype=default_dtype)
```

Supported properties must be:

```python
SUPPORTED_MACE_MP_PROPERTIES = {
    "mace_mp_energy_ev",
    "mace_mp_energy_per_atom_ev",
    "mace_mp_max_force_ev_per_angstrom",
    "mace_mp_stress_norm_ev_per_angstrom3",
}
```

- [ ] **Step 4: Run MACE backend tests**

Run:

```bash
uv run pytest tests/test_mace_mp_properties_backend.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/verifiers/backends/mace_mp_properties.py tests/test_mace_mp_properties_backend.py
git commit -m "feat: add MACE-MP backend"
```

## Task 5: MACE-MP Property Scripts

**Files:**
- Create: `src/verifiers/materials/mace_mp_property_script.py`
- Create: `src/verifiers/materials/mace_mp_energy.py`
- Create: `src/verifiers/materials/mace_mp_energy_per_atom.py`
- Create: `src/verifiers/materials/mace_mp_max_force.py`
- Create: `src/verifiers/materials/mace_mp_stress_norm.py`
- Test: `tests/test_torchani_mace_task_scripts.py`

- [ ] **Step 1: Add failing MACE script mismatch test**

Append to `tests/test_torchani_mace_task_scripts.py`:

```python
def mace_payload(spec_property: str = "mace_mp_energy_ev") -> dict:
    return {
        "task": {"task_id": "mace_script_001"},
        "constraint": {
            "type": "window",
            "property": "mace_mp_energy_per_atom_ev",
            "verifier_id": "mace_mp_energy_per_atom_small_v1",
            "min": -6.0,
            "max": -4.0,
            "sigma": 0.5,
        },
        "verifier_spec": {
            "verifier_id": "mace_mp_energy_per_atom_small_v1",
            "verification_script": "verifiers/materials/mace_mp_energy_per_atom.py",
            "property_name": spec_property,
            "backend": {"type": "native_mace_mp"},
        },
        "candidate": {},
    }


def test_mace_property_script_rejects_property_mismatch() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "materials" / "mace_mp_energy_per_atom.py",
        mace_payload(),
        timeout_seconds=60,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
    assert result["message"] == (
        "script property 'mace_mp_energy_per_atom_ev' does not match "
        "verifier_spec property 'mace_mp_energy_ev'"
    )
```

- [ ] **Step 2: Run MACE script test and verify it fails**

Run:

```bash
uv run pytest tests/test_torchani_mace_task_scripts.py::test_mace_property_script_rejects_property_mismatch -v
```

Expected: FAIL because MACE scripts do not exist.

- [ ] **Step 3: Implement MACE scripts**

Create `src/verifiers/materials/mace_mp_property_script.py`:

```python
from __future__ import annotations

from verifiers.backends.mace_mp_properties import evaluate_mace_mp_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_mace_mp_constraint,
        sort_keys=True,
    )
```

Create `src/verifiers/materials/mace_mp_energy.py`:

```python
from verifiers.materials.mace_mp_property_script import main


if __name__ == "__main__":
    main("mace_mp_energy_ev")
```

Create `src/verifiers/materials/mace_mp_energy_per_atom.py`:

```python
from verifiers.materials.mace_mp_property_script import main


if __name__ == "__main__":
    main("mace_mp_energy_per_atom_ev")
```

Create `src/verifiers/materials/mace_mp_max_force.py`:

```python
from verifiers.materials.mace_mp_property_script import main


if __name__ == "__main__":
    main("mace_mp_max_force_ev_per_angstrom")
```

Create `src/verifiers/materials/mace_mp_stress_norm.py`:

```python
from verifiers.materials.mace_mp_property_script import main


if __name__ == "__main__":
    main("mace_mp_stress_norm_ev_per_angstrom3")
```

- [ ] **Step 4: Run script tests**

Run:

```bash
uv run pytest tests/test_torchani_mace_task_scripts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/verifiers/materials/mace_mp_*.py tests/test_torchani_mace_task_scripts.py
git commit -m "feat: add MACE-MP property scripts"
```

## Task 6: Environment Diagnostics

**Files:**
- Create: `scripts/check_torchani_env.py`
- Create: `scripts/check_mace_mp_env.py`
- Test: `tests/test_torchani_mace_env_scripts.py`

- [ ] **Step 1: Write failing diagnostic script tests**

Create `tests/test_torchani_mace_env_scripts.py`:

```python
from __future__ import annotations

import json
import sys
from argparse import Namespace
from typing import Any

import pytest

from scripts import check_mace_mp_env
from scripts import check_torchani_env


def test_check_torchani_env_reports_success_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "runtime": {"model_name": args.model_name, "device": args.device},
            "prediction": {"torchani_total_energy_hartree": -76.38121032714844},
        }

    monkeypatch.setattr(check_torchani_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_torchani_env.py", "--model-name", "ANI2x"])

    check_torchani_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["runtime"]["model_name"] == "ANI2x"


def test_check_mace_env_reports_success_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "runtime": {"model": args.model, "device": args.device},
            "prediction": {"mace_mp_energy_per_atom_ev": -5.369234085083008},
        }

    monkeypatch.setattr(check_mace_mp_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_mace_mp_env.py", "--model", "small"])

    check_mace_mp_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["runtime"]["model"] == "small"


def test_check_torchani_env_maps_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_predict(atoms: object, spec: dict[str, Any]) -> dict[str, Any]:
        raise ModuleNotFoundError("No module named 'torchani'")

    monkeypatch.setattr(check_torchani_env.torchani_properties, "predict_torchani_properties", fail_predict)
    args = Namespace(model_name="ANI2x", device="cpu")

    payload = check_torchani_env.build_payload(args)

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"


def test_check_mace_env_maps_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_predict(atoms: object, spec: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("checkpoint download failed")

    monkeypatch.setattr(check_mace_mp_env.mace_mp_properties, "predict_mace_mp_properties", fail_predict)
    args = Namespace(model="small", device="cpu", default_dtype="float32")

    payload = check_mace_mp_env.build_payload(args)

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_tool_error"
    assert "checkpoint download failed" in payload["message"]
```

- [ ] **Step 2: Run diagnostic tests and verify they fail**

Run:

```bash
uv run pytest tests/test_torchani_mace_env_scripts.py -v
```

Expected: FAIL because the diagnostic scripts do not exist.

- [ ] **Step 3: Implement diagnostic scripts**

Create `scripts/check_torchani_env.py`:

```python
#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from typing import Any

from verifiers.backends import torchani_properties


WATER_XYZ = """3
water
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284
"""


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    spec = {"torchani": {"model_name": args.model_name, "device": args.device}}
    try:
        atoms = torchani_properties.parse_xyz_atoms(WATER_XYZ)
        input_properties = torchani_properties.inspect_xyz_atoms(atoms)
        prediction = torchani_properties.predict_torchani_properties(atoms, spec)
    except (ImportError, ModuleNotFoundError) as exc:
        return {"status": "error", "failure_type": "verifier_environment_error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "failure_type": "verifier_tool_error", "message": str(exc)}
    return {
        "status": "ok",
        "failure_type": None,
        "message": None,
        "versions": {"torchani": package_version("torchani"), "torch": package_version("torch"), "ase": package_version("ase")},
        "runtime": {"model_name": args.model_name, "device": args.device},
        "input": input_properties,
        "prediction": prediction,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="ANI2x")
    parser.add_argument("--device", default="cpu")
    print(json.dumps(build_payload(parser.parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

Create `scripts/check_mace_mp_env.py` with the embedded silicon CIF from `scripts/check_matgl_env.py`. It should call `mace_mp_properties.parse_cif_atoms(SI_CIF_TEXT)`, derive `input_properties` with `mace_mp_properties.inspect_structure(structure, atoms)`, and then call `mace_mp_properties.predict_mace_mp_properties` with `{"mace_mp": {"model": args.model, "device": args.device, "default_dtype": args.default_dtype}}`. Use the same JSON shape as `check_torchani_env.py`, with versions for `mace-torch`, `torch`, `ase`, and `pymatgen`.

- [ ] **Step 4: Run diagnostic tests**

Run:

```bash
uv run pytest tests/test_torchani_mace_env_scripts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_torchani_env.py scripts/check_mace_mp_env.py tests/test_torchani_mace_env_scripts.py
git commit -m "feat: add MLIP environment diagnostics"
```

## Task 7: Opt-In Live Smoke Tests

**Files:**
- Create: `tests/test_torchani_mace_live_smoke.py`

- [ ] **Step 1: Write opt-in smoke tests**

Create `tests/test_torchani_mace_live_smoke.py`:

```python
from __future__ import annotations

import os
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("VGB_RUN_MLIP_SMOKE") != "1",
    reason="set VGB_RUN_MLIP_SMOKE=1 to run TorchANI/MACE live model smoke tests",
)


def test_check_torchani_env_live_smoke() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_torchani_env.py"],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert completed.returncode == 0
    assert '"status": "ok"' in completed.stdout
    assert "torchani_total_energy_hartree" in completed.stdout


def test_check_mace_mp_env_live_smoke() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_mace_mp_env.py"],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert completed.returncode == 0
    assert '"status": "ok"' in completed.stdout
    assert "mace_mp_energy_per_atom_ev" in completed.stdout
```

- [ ] **Step 2: Run default smoke tests and verify they skip**

Run:

```bash
uv run pytest tests/test_torchani_mace_live_smoke.py -v
```

Expected: SKIPPED because `VGB_RUN_MLIP_SMOKE` is not set.

- [ ] **Step 3: Run live smoke in the relevant optional environments**

Run after installing optional dependencies:

```bash
VGB_RUN_MLIP_SMOKE=1 uv run --group torchani pytest tests/test_torchani_mace_live_smoke.py::test_check_torchani_env_live_smoke -v
VGB_RUN_MLIP_SMOKE=1 uv run --group mace pytest tests/test_torchani_mace_live_smoke.py::test_check_mace_mp_env_live_smoke -v
```

Expected: both PASS on macOS arm64 CPU. The MACE smoke may download the `small` MACE-MP checkpoint into `~/.cache/mace`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_torchani_mace_live_smoke.py
git commit -m "test: add opt-in MLIP live smoke"
```

## Task 8: Backend Capability Documentation

**Files:**
- Create: `docs/tracks/TorchANI.md`
- Create: `docs/tracks/MACE-MP.md`

- [ ] **Step 1: Create TorchANI backend document**

Create `docs/tracks/TorchANI.md`:

```markdown
# TorchANI ANI-2x Backend

Status: backend capability document, not a registered formal benchmark track.

## Purpose

This backend wraps TorchANI ANI-2x as a native optional runtime for direct-XYZ
small-molecule quantum-ML energy and force properties.

## Input

The candidate must provide an `xyz` string. The backend does not generate
conformers from SMILES.

## Properties

| Verifier property | Unit | Meaning |
|---|---:|---|
| `torchani_total_energy_hartree` | Hartree | ANI-2x total molecular energy. |
| `torchani_energy_per_atom_hartree` | Hartree/atom | Total energy divided by atom count. |
| `torchani_max_force_hartree_per_angstrom` | Hartree/Angstrom | Maximum atomic force norm. |

## Runtime

Install the optional runtime with:

```bash
uv sync --group torchani
```

Run the local diagnostic:

```bash
uv run --group torchani python scripts/check_torchani_env.py
```

## Limitations

- ANI-2x supports a limited organic element domain: H, C, N, O, F, S, and Cl.
- Absolute total energy should be used only with carefully constrained formula
  or composition domains.
- This backend is CPU-usable but still loads PyTorch and TorchANI model weights.
```

- [ ] **Step 2: Create MACE-MP backend document**

Create `docs/tracks/MACE-MP.md`:

```markdown
# MACE-MP Backend

Status: backend capability document, not a registered formal benchmark track.

## Purpose

This backend wraps the MACE-MP foundation potential through the MACE ASE
calculator as a native optional runtime for periodic material energy, force,
and stress properties.

## Input

The candidate must provide a `cif` string. The backend parses the CIF with
pymatgen and converts the structure to ASE Atoms.

## Properties

| Verifier property | Unit | Meaning |
|---|---:|---|
| `mace_mp_energy_ev` | eV | MACE-MP total potential energy. |
| `mace_mp_energy_per_atom_ev` | eV/atom | Total potential energy divided by atom count. |
| `mace_mp_max_force_ev_per_angstrom` | eV/Angstrom | Maximum atomic force norm. |
| `mace_mp_stress_norm_ev_per_angstrom3` | eV/Angstrom^3 | Norm of ASE stress vector. |

## Runtime

Install the optional runtime with:

```bash
uv sync --group mace
```

Run the local diagnostic:

```bash
uv run --group mace python scripts/check_mace_mp_env.py
```

The first run may download the selected MACE-MP checkpoint into `~/.cache/mace`.

## Limitations

- Energy zero points and stress behavior are model-specific and must not be
  mixed with MatGL formation-energy labels.
- The first implementation uses the `small` MACE-MP model on CPU for verifier
  practicality.
- Formal benchmark tasks need calibration before this backend is exposed as a
  public track.
```

- [ ] **Step 3: Commit docs**

```bash
git add docs/tracks/TorchANI.md docs/tracks/MACE-MP.md
git commit -m "docs: document MLIP backend capabilities"
```

## Task 9: Final Verification

**Files:**
- All files touched in Tasks 1-8.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest \
  tests/test_mlip_optional_dependencies.py \
  tests/test_torchani_properties_backend.py \
  tests/test_mace_mp_properties_backend.py \
  tests/test_torchani_mace_task_scripts.py \
  tests/test_torchani_mace_env_scripts.py \
  tests/test_torchani_mace_live_smoke.py \
  -v
```

Expected: all non-live tests PASS and live smoke tests SKIP unless `VGB_RUN_MLIP_SMOKE=1`.

- [ ] **Step 2: Run existing adjacent tests**

Run:

```bash
uv run pytest \
  tests/test_matgl_properties_backend.py \
  tests/test_matgl_task_scripts.py \
  tests/test_xtb_properties_backend.py \
  tests/test_physchem_task_scripts.py \
  -v
```

Expected: PASS.

- [ ] **Step 3: Run optional live smokes**

Run when model dependencies are installed:

```bash
VGB_RUN_MLIP_SMOKE=1 uv run --group torchani pytest tests/test_torchani_mace_live_smoke.py::test_check_torchani_env_live_smoke -v
VGB_RUN_MLIP_SMOKE=1 uv run --group mace pytest tests/test_torchani_mace_live_smoke.py::test_check_mace_mp_env_live_smoke -v
```

Expected: PASS. Record any checkpoint download path in the final implementation summary.

- [ ] **Step 4: Verify packaging**

Run:

```bash
uv run pytest tests/test_packaging.py tests/test_public_api.py -v
```

Expected: PASS. The new script packages are included through the existing `src/verifiers` wheel package include.

- [ ] **Step 5: Final commit**

If the previous tasks were implemented in one branch but not committed task-by-task, make one final commit:

```bash
git status --short
git add pyproject.toml src/verifiers scripts tests docs/tracks
git commit -m "feat: add TorchANI and MACE-MP backends"
```

## Self-Review

- Spec coverage: The plan covers optional dependencies, TorchANI backend with local XYZ parsing, TorchANI scripts, MACE-MP backend with local CIF parsing, MACE-MP scripts, diagnostics, opt-in live smokes, and backend docs.
- Scope: The plan intentionally excludes task packs, registry changes, calibration thresholds, sample answers, FAIR-Chem UMA, Docker images, and public benchmark exposure.
- Type consistency: TorchANI property names use `torchani_*`; MACE property names use `mace_mp_*`; both evaluators return the existing result schema and use existing scoring.
- Deployment risk: TorchANI and MACE are optional groups because the current default environment should stay light. Live smoke tests are opt-in because they may download model weights and take longer than normal unit tests.
