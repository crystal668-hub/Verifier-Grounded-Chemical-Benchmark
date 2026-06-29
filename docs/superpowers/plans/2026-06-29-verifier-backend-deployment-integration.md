# Verifier Backend Deployment Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add locally deployable verifier backend support for ADMET-AI, OPERA, and native MatGL+pymatgen without adding formal benchmark tasks.

**Architecture:** Keep the current property-level script pattern: `verification_script -> shared backend -> result_schema`. Add backend modules and smoke-check scripts that prove each tool can be installed, discovered, and run locally. Do not add new `tasks/*` packs in this plan; use synthetic payloads and environment checks only.

**Tech Stack:** Python 3.12 via `uv`, pytest, RDKit for small-molecule parsing/domain gates, ADMET-AI/Chemprop for ADMET predictions, OPERA 2.9 command-line executable for QSAR predictions, MatGL+pymatgen for materials model loading/structure handling, existing verifier JSON result schema.

---

## Current Environment Audit

Checked on 2026-06-29 in `/Users/xutao/verifier-grounded-benchmark`:

- Host: macOS 26.5.1 arm64.
- Project Python: `.venv/bin/python3`, Python 3.12.13 via `uv run`.
- System Python: Python 3.14.4; do not use for project verifier scripts.
- `uv`: 0.11.7.
- Docker CLI: installed, but daemon is not currently running (`Cannot connect to the Docker daemon`).
- Disk free for repo/tmp: about 110 GiB.
- GPU: CUDA unavailable; Apple MPS available via Torch. Use CPU as default verifier device for reproducibility.
- `uv lock --check`: passes.
- `uv run python scripts/check_core_env.py`: passes.

Installed in the project venv:

- `admet-ai==2.0.1`
- `chemprop==2.2.3`
- `rdkit==2026.3.2`
- `pymatgen==2026.5.4`
- `ase==3.28.0`
- `torch==2.12.0`

Not installed in the project venv:

- `matgl`
- `chgnet`
- `huggingface_hub`
- `torch_geometric`

OPERA status:

- `opera` and `OPERA` are not on PATH.
- No local OPERA installation was found by a shallow search under `/Applications`, `/opt`, `/usr/local`, `/opt/homebrew`, or `$HOME`.
- Official OPERA 2.9 command-line assets are Linux/Windows archives around 2 GiB. Since the host is macOS arm64, OPERA should be validated through Docker/Linux or a dedicated Linux machine, not by assuming native macOS execution.

ADMET-AI smoke result:

- `ADMETModel(include_physchem=False, drugbank_path=None, num_workers=0)` loads.
- It reports two model groups: 31 classification endpoints and 10 regression endpoints.
- A single `CCO` prediction returns 41 ADMET endpoints, including `Solubility_AqSolDB`, `hERG`, `AMES`, `DILI`, `BBB_Martins`, and `Caco2_Wang`.
- ADMET-AI/Lightning/tqdm prints progress to stdout/stderr during prediction. Verifier scripts must suppress third-party output so stdout remains valid JSON.

MatGL dependency preflight:

- `uv pip install --dry-run matgl==4.0.2 --torch-backend cpu` resolves.
- It would install `matgl==4.0.2`, `huggingface-hub==1.21.0`, `torch-geometric==2.8.0`, `torchdata==0.11.0`, and related packages.
- It would downgrade `lightning` from 2.6.5 to 2.6.1. Treat this as a lockfile/test risk. Prefer an optional dependency group or direct `pyproject.toml` edit followed by `uv lock` and full tests.
- `uv pip install --dry-run chgnet==0.4.2 --torch-backend cpu` resolves lightly, but standalone CHGNet is not the preferred backend for this integration.

## File Structure

Create:

- `scripts/check_admet_ai_env.py` - smoke-check ADMET-AI package, model ensembles, endpoint metadata, and one quiet prediction.
- `scripts/check_opera_env.py` - discover OPERA executable/path, run `opera -h` if available, and optionally run a fixture input when configured.
- `scripts/check_matgl_env.py` - smoke-check MatGL import/model cache behavior and pymatgen structure parsing.
- `verifiers/backends/admet_ai_properties.py` - shared ADMET-AI backend for small-molecule endpoint evaluation.
- `verifiers/admet/__init__.py` - package marker for ADMET verifier scripts.
- `verifiers/admet/admet_ai_property_script.py` - shared CLI wrapper for ADMET-AI property scripts.
- `verifiers/admet/admet_ai_solubility_aqsoldb.py` - property script entry point.
- `verifiers/admet/admet_ai_herg.py` - property script entry point.
- `verifiers/admet/admet_ai_ames.py` - property script entry point.
- `verifiers/admet/admet_ai_bbb.py` - property script entry point.
- `verifiers/admet/admet_ai_caco2.py` - property script entry point.
- `verifiers/backends/opera_properties.py` - shared OPERA CLI backend/wrapper and output parser.
- `verifiers/opera/__init__.py` - package marker for OPERA verifier scripts.
- `verifiers/opera/opera_property_script.py` - shared CLI wrapper for OPERA property scripts.
- `verifiers/backends/matgl_properties.py` - native MatGL+pymatgen backend independent of AtomisticSkills MCP.
- `verifiers/materials/matgl_property_script.py` - shared CLI wrapper for native MatGL scripts.
- `verifiers/materials/matgl_bandgap.py` - native MatGL bandgap script entry point.
- `verifiers/materials/matgl_formation_energy.py` - native MatGL formation energy script entry point.
- `tests/test_admet_ai_env_script.py`
- `tests/test_admet_ai_properties_backend.py`
- `tests/test_admet_ai_task_scripts.py`
- `tests/test_opera_env_script.py`
- `tests/test_opera_properties_backend.py`
- `tests/test_matgl_env_script.py`
- `tests/test_matgl_properties_backend.py`
- `tests/test_matgl_task_scripts.py`

Modify:

- `pyproject.toml` - add MatGL dependency only after deciding whether it belongs in main dependencies or a dependency group.
- `uv.lock` - regenerate after dependency change.
- `scripts/check_core_env.py` - optionally include ADMET-AI smoke details, but keep heavyweight model prediction in `check_admet_ai_env.py`.

Do not create:

- New `tasks/*` packs.
- Formal task cards or sample answers.
- A Dockerfile for OPERA unless explicitly requested during implementation. This plan can add OPERA discovery and wrapper code without shipping the 2 GiB OPERA binary.

## Task 1: ADMET-AI Environment Smoke

**Files:**
- Create: `scripts/check_admet_ai_env.py`
- Test: `tests/test_admet_ai_env_script.py`

- [ ] **Step 1: Write tests for ADMET-AI smoke output**

Create `tests/test_admet_ai_env_script.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys


def test_check_admet_ai_env_outputs_json() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_admet_ai_env.py", "--smiles", "CCO"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["versions"]["admet-ai"] == "2.0.1"
    assert payload["models"]["num_ensembles"] == 2
    assert payload["models"]["task_group_sizes"] == [31, 10]
    assert payload["prediction"]["smiles"] == "CCO"
    for endpoint in ["Solubility_AqSolDB", "hERG", "AMES", "BBB_Martins", "Caco2_Wang"]:
        assert endpoint in payload["prediction"]["properties"]
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run pytest tests/test_admet_ai_env_script.py -q
```

Expected: fails because `scripts/check_admet_ai_env.py` does not exist.

- [ ] **Step 3: Implement `scripts/check_admet_ai_env.py`**

Create `scripts/check_admet_ai_env.py`:

```python
#!/usr/bin/env python
"""Smoke-check the ADMET-AI verifier environment."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata as metadata
import io
import json
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINTS = ["Solubility_AqSolDB", "hERG", "AMES", "BBB_Martins", "Caco2_Wang"]


def directory_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file():
            digest.update(str(file_path.relative_to(path)).encode())
            digest.update(str(file_path.stat().st_size).encode())
    return digest.hexdigest()


def quiet_predict(model: Any, smiles: str) -> dict[str, float]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        preds = model.predict(smiles=smiles)
    return {str(key): float(value) for key, value in dict(preds).items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smiles", default="CCO")
    args = parser.parse_args()

    from admet_ai import ADMETModel
    from admet_ai.constants import DEFAULT_ADMET_PATH, DEFAULT_MODELS_DIR

    model = ADMETModel(include_physchem=False, drugbank_path=None, num_workers=0)
    predictions = quiet_predict(model, args.smiles)
    selected = {endpoint: predictions[endpoint] for endpoint in DEFAULT_ENDPOINTS if endpoint in predictions}
    payload = {
        "status": "ok",
        "versions": {
            "admet-ai": metadata.version("admet-ai"),
            "chemprop": metadata.version("chemprop"),
            "torch": metadata.version("torch"),
        },
        "models": {
            "models_dir": str(DEFAULT_MODELS_DIR),
            "models_dir_fingerprint": directory_fingerprint(DEFAULT_MODELS_DIR),
            "admet_metadata": str(DEFAULT_ADMET_PATH),
            "num_ensembles": model.num_ensembles,
            "task_group_sizes": [len(tasks) for tasks in model.task_lists],
            "tasks": model.task_lists,
        },
        "prediction": {
            "smiles": args.smiles,
            "num_properties": len(predictions),
            "properties": selected,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify ADMET-AI smoke passes**

Run:

```bash
uv run pytest tests/test_admet_ai_env_script.py -q
uv run python scripts/check_admet_ai_env.py --smiles CCO
```

Expected: pytest passes and the script prints a single JSON object with `status: ok`.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_admet_ai_env.py tests/test_admet_ai_env_script.py
git commit -m "test: add admet ai environment smoke check"
```

## Task 2: ADMET-AI Backend and Script Entrypoints

**Files:**
- Create: `verifiers/backends/admet_ai_properties.py`
- Create: `verifiers/admet/__init__.py`
- Create: `verifiers/admet/admet_ai_property_script.py`
- Create: `verifiers/admet/admet_ai_solubility_aqsoldb.py`
- Create: `verifiers/admet/admet_ai_herg.py`
- Create: `verifiers/admet/admet_ai_ames.py`
- Create: `verifiers/admet/admet_ai_bbb.py`
- Create: `verifiers/admet/admet_ai_caco2.py`
- Test: `tests/test_admet_ai_properties_backend.py`
- Test: `tests/test_admet_ai_task_scripts.py`

- [ ] **Step 1: Write backend unit tests with a fake model**

Create `tests/test_admet_ai_properties_backend.py`:

```python
from __future__ import annotations

import pytest

from verifiers.backends import admet_ai_properties


def spec(endpoint: str = "hERG") -> dict:
    return {
        "verifier_id": f"admet_ai_{endpoint.lower()}_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": endpoint,
        "domain": {
            "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I", "H"],
            "heavy_atom_count": [2, 80],
            "mw": [20.0, 900.0],
            "formal_charge": [-2, 2],
        },
    }


def task(endpoint: str = "hERG") -> dict:
    return {
        "task_id": "admet_fake_task",
        "constraints": [
            {
                "type": "minimize_bounded",
                "property": endpoint,
                "verifier_id": f"admet_ai_{endpoint.lower()}_v1",
                "lower": 0.0,
                "upper": 1.0,
            }
        ],
    }


def test_admet_ai_scores_fake_prediction(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeModel:
        def predict(self, smiles: str) -> dict[str, float]:
            assert smiles == "CCO"
            return {"hERG": 0.2, "AMES": 0.4}

    monkeypatch.setattr(admet_ai_properties, "load_model", lambda spec: FakeModel())

    result = admet_ai_properties.evaluate_admet_ai_constraint(
        {"smiles": "CCO"},
        task("hERG"),
        task("hERG")["constraints"][0],
        spec("hERG"),
    )

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["hERG"] == pytest.approx(0.2)
    assert result["scores"]["score"] == pytest.approx(0.8)


def test_admet_ai_reports_missing_smiles() -> None:
    result = admet_ai_properties.evaluate_admet_ai_constraint(
        {},
        task("hERG"),
        task("hERG")["constraints"][0],
        spec("hERG"),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_admet_ai_reports_disallowed_element() -> None:
    result = admet_ai_properties.evaluate_admet_ai_constraint(
        {"smiles": "[Na+].[Cl-]"},
        task("hERG"),
        task("hERG")["constraints"][0],
        spec("hERG"),
    )

    assert result["status"] == "error"
    assert result["failure_type"] in {"validity_error", "domain_error"}


def test_admet_ai_reports_property_mismatch() -> None:
    result = admet_ai_properties.evaluate_admet_ai_constraint(
        {"smiles": "CCO"},
        task("AMES"),
        task("AMES")["constraints"][0],
        spec("hERG"),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
```

- [ ] **Step 2: Run failing backend tests**

Run:

```bash
uv run pytest tests/test_admet_ai_properties_backend.py -q
```

Expected: fails because `verifiers.backends.admet_ai_properties` does not exist.

- [ ] **Step 3: Implement `verifiers/backends/admet_ai_properties.py`**

Create `verifiers/backends/admet_ai_properties.py`:

```python
"""Shared ADMET-AI backend for small-molecule verifier scripts."""

from __future__ import annotations

import contextlib
import importlib.metadata as metadata
import io
from functools import lru_cache
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result, error_result


@lru_cache(maxsize=4)
def load_model_cached(include_physchem: bool, drugbank_percentiles: bool, num_workers: int):
    from admet_ai import ADMETModel

    return ADMETModel(
        include_physchem=include_physchem,
        drugbank_path=None if not drugbank_percentiles else None,
        num_workers=num_workers,
    )


def load_model(spec: dict[str, Any]):
    config = spec.get("admet_ai") or {}
    return load_model_cached(
        bool(config.get("include_physchem", False)),
        bool(config.get("drugbank_percentiles", False)),
        int(config.get("num_workers", 0)),
    )


def quiet_predict(model: Any, smiles: str) -> dict[str, float]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        predictions = model.predict(smiles=smiles)
    return {str(key): float(value) for key, value in dict(predictions).items()}


def evaluate_admet_ai_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    result = base_result(task_id, spec.get("verifier_id"), admet_ai_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )

    smiles = candidate.get("smiles")
    if not isinstance(smiles, str) or not smiles.strip():
        return error_result(result, "parse_error", "candidate must include a SMILES string")
    if "." in smiles:
        return error_result(result, "validity_error", "multi-component SMILES are not accepted")

    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        return error_result(result, "parse_error", "RDKit returned no molecule")

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    domain_properties = compute_domain_properties(mol)
    domain_error = check_domain(domain_properties, spec.get("domain", {}))
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=domain_properties)

    try:
        predictions = quiet_predict(load_model(spec), canonical_smiles)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", f"ADMET-AI prediction failed: {exc}")

    if property_name not in predictions:
        return error_result(result, "verifier_tool_error", f"ADMET-AI output missing property {property_name!r}")

    properties = {**domain_properties, property_name: predictions[property_name]}
    constraint_score = {
        "property": constraint["property"],
        "type": constraint["type"],
        "score": score_constraint(properties, constraint),
    }
    score = float(constraint_score["score"])
    result.update(
        {
            "status": "ok",
            "canonical_smiles": canonical_smiles,
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [constraint_score],
                "property_score": score,
                "score": score,
            },
        }
    )
    return result


def compute_domain_properties(mol: Chem.Mol) -> dict[str, Any]:
    return {
        "mw": float(Descriptors.MolWt(mol)),
        "heavy_atom_count": int(mol.GetNumHeavyAtoms()),
        "formal_charge": int(Chem.GetFormalCharge(mol)),
        "elements": sorted({atom.GetSymbol() for atom in mol.GetAtoms()}),
    }


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    allowed_elements = domain.get("allowed_elements")
    if allowed_elements:
        disallowed = sorted(set(properties["elements"]) - set(allowed_elements))
        if disallowed:
            return f"disallowed elements: {', '.join(disallowed)}"
    for name in ("heavy_atom_count", "mw", "formal_charge"):
        if name in domain:
            lower, upper = domain[name]
            value = properties[name]
            if not float(lower) <= float(value) <= float(upper):
                return f"{name} outside [{lower}, {upper}]"
    return None


def admet_ai_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "admet-ai": metadata.version("admet-ai"),
        "chemprop": metadata.version("chemprop"),
        "rdkit": metadata.version("rdkit"),
    }
```

- [ ] **Step 4: Implement ADMET-AI script wrappers**

Create `verifiers/admet/__init__.py`:

```python
"""ADMET verifier script entry points."""
```

Create `verifiers/admet/admet_ai_property_script.py`:

```python
"""Shared CLI helper for ADMET-AI verifier scripts."""

from __future__ import annotations

from verifiers.backends.admet_ai_properties import evaluate_admet_ai_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_admet_ai_constraint,
        sort_keys=True,
    )
```

Create each entry point:

```python
# verifiers/admet/admet_ai_solubility_aqsoldb.py
from __future__ import annotations

from verifiers.admet.admet_ai_property_script import main

if __name__ == "__main__":
    main("Solubility_AqSolDB")
```

```python
# verifiers/admet/admet_ai_herg.py
from __future__ import annotations

from verifiers.admet.admet_ai_property_script import main

if __name__ == "__main__":
    main("hERG")
```

```python
# verifiers/admet/admet_ai_ames.py
from __future__ import annotations

from verifiers.admet.admet_ai_property_script import main

if __name__ == "__main__":
    main("AMES")
```

```python
# verifiers/admet/admet_ai_bbb.py
from __future__ import annotations

from verifiers.admet.admet_ai_property_script import main

if __name__ == "__main__":
    main("BBB_Martins")
```

```python
# verifiers/admet/admet_ai_caco2.py
from __future__ import annotations

from verifiers.admet.admet_ai_property_script import main

if __name__ == "__main__":
    main("Caco2_Wang")
```

- [ ] **Step 5: Write script runner tests**

Create `tests/test_admet_ai_task_scripts.py`:

```python
from __future__ import annotations

from pathlib import Path

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def payload(property_name: str) -> dict:
    return {
        "task": {"task_id": "admet_script_smoke"},
        "candidate": {"smiles": "CCO"},
        "constraint": {
            "type": "minimize_bounded",
            "property": property_name,
            "verifier_id": "admet_ai_script_v1",
            "lower": 0.0,
            "upper": 1.0,
        },
        "verifier_spec": {
            "verifier_id": "admet_ai_script_v1",
            "verifier_image": "verifier-grounded:dev",
            "property_name": property_name,
            "domain": {
                "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I", "H"],
                "heavy_atom_count": [2, 80],
                "mw": [20.0, 900.0],
                "formal_charge": [-2, 2],
            },
            "admet_ai": {"include_physchem": False, "num_workers": 0},
        },
    }


def test_admet_ai_herg_script_outputs_json() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "admet" / "admet_ai_herg.py",
        payload("hERG"),
        timeout_seconds=90,
    )

    assert result["status"] == "ok"
    assert result["properties"]["hERG"] >= 0.0
    assert result["properties"]["hERG"] <= 1.0


def test_admet_ai_script_property_mismatch() -> None:
    data = payload("AMES")
    result = run_verification_script(
        ROOT / "verifiers" / "admet" / "admet_ai_herg.py",
        data,
        timeout_seconds=30,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
```

- [ ] **Step 6: Verify ADMET-AI backend**

Run:

```bash
uv run pytest tests/test_admet_ai_properties_backend.py tests/test_admet_ai_task_scripts.py -q
```

Expected: all tests pass and no JSON stdout contamination occurs.

- [ ] **Step 7: Commit**

```bash
git add verifiers/backends/admet_ai_properties.py verifiers/admet tests/test_admet_ai_properties_backend.py tests/test_admet_ai_task_scripts.py
git commit -m "feat: add admet ai verifier backend"
```

## Task 3: OPERA Discovery and CLI Wrapper

**Files:**
- Create: `scripts/check_opera_env.py`
- Create: `verifiers/backends/opera_properties.py`
- Create: `verifiers/opera/__init__.py`
- Create: `verifiers/opera/opera_property_script.py`
- Test: `tests/test_opera_env_script.py`
- Test: `tests/test_opera_properties_backend.py`

- [ ] **Step 1: Write OPERA env script tests**

Create `tests/test_opera_env_script.py`:

```python
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path


def test_check_opera_env_reports_missing_when_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("OPERA_EXECUTABLE", raising=False)
    completed = subprocess.run(
        [sys.executable, "scripts/check_opera_env.py"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] in {"missing", "ok"}
    if payload["status"] == "missing":
        assert payload["failure_type"] == "verifier_environment_error"


def test_check_opera_env_uses_configured_executable(tmp_path: Path) -> None:
    fake = tmp_path / "opera"
    fake.write_text("#!/usr/bin/env bash\necho 'OPERA help'\n")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

    env = os.environ.copy()
    env["OPERA_EXECUTABLE"] = str(fake)
    completed = subprocess.run(
        [sys.executable, "scripts/check_opera_env.py"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["executable"] == str(fake)
```

- [ ] **Step 2: Implement `scripts/check_opera_env.py`**

Create `scripts/check_opera_env.py`:

```python
#!/usr/bin/env python
"""Smoke-check OPERA command-line availability."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def find_opera() -> str | None:
    configured = os.environ.get("OPERA_EXECUTABLE")
    if configured:
        return configured
    for name in ("opera", "OPERA"):
        found = shutil.which(name)
        if found:
            return found
    return None


def main() -> None:
    executable = find_opera()
    if executable is None:
        print(
            json.dumps(
                {
                    "status": "missing",
                    "failure_type": "verifier_environment_error",
                    "message": "OPERA executable not found; set OPERA_EXECUTABLE or add opera to PATH",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    path = Path(executable)
    if not path.exists():
        print(
            json.dumps(
                {
                    "status": "missing",
                    "failure_type": "verifier_environment_error",
                    "executable": executable,
                    "message": "configured OPERA executable does not exist",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    completed = subprocess.run(
        [executable, "-h"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(
        json.dumps(
            {
                "status": "ok" if completed.returncode == 0 else "error",
                "executable": executable,
                "returncode": completed.returncode,
                "stdout_head": completed.stdout[:1000],
                "stderr_head": completed.stderr[:1000],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write OPERA backend parser/wrapper tests**

Create `tests/test_opera_properties_backend.py`:

```python
from __future__ import annotations

import stat
from pathlib import Path

import pytest

from verifiers.backends import opera_properties


def spec(property_name: str = "WS", executable: str | None = None) -> dict:
    payload = {
        "verifier_id": "opera_ws_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": property_name,
        "opera": {"model": property_name},
        "domain": {
            "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I", "H"],
            "heavy_atom_count": [2, 80],
            "mw": [20.0, 900.0],
            "formal_charge": [-2, 2],
        },
    }
    if executable:
        payload["opera"]["executable"] = executable
    return payload


def constraint(property_name: str = "WS") -> dict:
    return {
        "type": "window",
        "property": property_name,
        "verifier_id": "opera_ws_v1",
        "min": -4.0,
        "max": 0.0,
        "sigma": 1.0,
    }


def test_parse_opera_csv_property() -> None:
    parsed = opera_properties.parse_opera_output("ID,WS,AD_WS\\ncandidate,-1.25,1\\n", "WS")
    assert parsed["WS"] == pytest.approx(-1.25)
    assert parsed["AD_WS"] == 1


def test_opera_backend_maps_missing_executable() -> None:
    result = opera_properties.evaluate_opera_constraint(
        {"smiles": "CCO"},
        {"task_id": "opera_task"},
        constraint(),
        spec(executable="/missing/opera"),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"


def test_opera_backend_runs_fake_executable(tmp_path: Path) -> None:
    fake = tmp_path / "opera"
    fake.write_text("#!/usr/bin/env bash\nprintf 'ID,WS,AD_WS\\ncandidate,-1.25,1\\n' > \"$2\"\n")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

    result = opera_properties.evaluate_opera_constraint(
        {"smiles": "CCO"},
        {"task_id": "opera_task"},
        constraint(),
        spec(executable=str(fake)),
    )

    assert result["status"] == "ok"
    assert result["properties"]["WS"] == pytest.approx(-1.25)
    assert result["properties"]["AD_WS"] == 1
```

- [ ] **Step 4: Implement OPERA backend**

Create `verifiers/backends/opera_properties.py`:

```python
"""Shared OPERA command-line backend for verifier scripts."""

from __future__ import annotations

import csv
import importlib.metadata as metadata
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result, error_result


def find_opera_executable(spec: dict[str, Any]) -> str | None:
    configured = (spec.get("opera") or {}).get("executable") or os.environ.get("OPERA_EXECUTABLE")
    if configured:
        return str(configured)
    for name in ("opera", "OPERA"):
        found = shutil.which(name)
        if found:
            return found
    return None


def evaluate_opera_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    result = base_result(task_id, spec.get("verifier_id"), opera_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
        return error_result(result, "verifier_spec_error", "OPERA property does not match constraint property")

    smiles = candidate.get("smiles")
    if not isinstance(smiles, str) or not smiles.strip():
        return error_result(result, "parse_error", "candidate must include a SMILES string")
    if "." in smiles:
        return error_result(result, "validity_error", "multi-component SMILES are not accepted")
    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        return error_result(result, "parse_error", "RDKit returned no molecule")

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    domain_properties = compute_domain_properties(mol)
    domain_error = check_domain(domain_properties, spec.get("domain", {}))
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=domain_properties)

    executable = find_opera_executable(spec)
    if executable is None or not Path(executable).exists():
        return error_result(result, "verifier_environment_error", "OPERA executable not found")

    try:
        opera_properties = run_opera(executable, canonical_smiles, property_name, spec)
    except subprocess.TimeoutExpired:
        return error_result(result, "verifier_timeout", "OPERA execution timed out")
    except Exception as exc:
        return error_result(result, "verifier_tool_error", f"OPERA execution failed: {exc}")

    properties = {**domain_properties, **opera_properties}
    constraint_score = {
        "property": constraint["property"],
        "type": constraint["type"],
        "score": score_constraint(properties, constraint),
    }
    score = float(constraint_score["score"])
    result.update(
        {
            "status": "ok",
            "canonical_smiles": canonical_smiles,
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [constraint_score],
                "property_score": score,
                "score": score,
            },
        }
    )
    return result


def run_opera(executable: str, smiles: str, property_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    timeout = float(spec.get("timeout_seconds", 120.0))
    model = str((spec.get("opera") or {}).get("model", property_name))
    with tempfile.TemporaryDirectory(prefix="opera-verifier-") as temp_dir:
        temp = Path(temp_dir)
        input_path = temp / "candidate.smi"
        output_path = temp / "predictions.csv"
        input_path.write_text(f"{smiles}\\tcandidate\\n")
        command = [executable, str(input_path), str(output_path), model]
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"OPERA exited {completed.returncode}")
        if not output_path.exists():
            raise RuntimeError("OPERA did not create expected output file")
        return parse_opera_output(output_path.read_text(), property_name)


def parse_opera_output(text: str, property_name: str) -> dict[str, Any]:
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        raise ValueError("OPERA output CSV contained no rows")
    row = rows[0]
    if property_name not in row:
        raise ValueError(f"OPERA output missing {property_name!r}")
    parsed: dict[str, Any] = {property_name: float(row[property_name])}
    ad_key = f"AD_{property_name}"
    if ad_key in row and row[ad_key] != "":
        parsed[ad_key] = int(float(row[ad_key]))
    return parsed


def compute_domain_properties(mol: Chem.Mol) -> dict[str, Any]:
    return {
        "mw": float(Descriptors.MolWt(mol)),
        "heavy_atom_count": int(mol.GetNumHeavyAtoms()),
        "formal_charge": int(Chem.GetFormalCharge(mol)),
        "elements": sorted({atom.GetSymbol() for atom in mol.GetAtoms()}),
    }


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    allowed_elements = domain.get("allowed_elements")
    if allowed_elements:
        disallowed = sorted(set(properties["elements"]) - set(allowed_elements))
        if disallowed:
            return f"disallowed elements: {', '.join(disallowed)}"
    for name in ("heavy_atom_count", "mw", "formal_charge"):
        if name in domain:
            lower, upper = domain[name]
            if not float(lower) <= float(properties[name]) <= float(upper):
                return f"{name} outside [{lower}, {upper}]"
    return None


def opera_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "opera": str((spec.get("opera") or {}).get("version", "2.9")),
        "rdkit": metadata.version("rdkit"),
    }
```

- [ ] **Step 5: Add OPERA script package wrapper**

Create `verifiers/opera/__init__.py`:

```python
"""OPERA verifier script entry points."""
```

Create `verifiers/opera/opera_property_script.py`:

```python
"""Shared CLI helper for OPERA verifier scripts."""

from __future__ import annotations

from verifiers.backends.opera_properties import evaluate_opera_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_opera_constraint,
        sort_keys=True,
    )
```

- [ ] **Step 6: Verify OPERA discovery and backend tests**

Run:

```bash
uv run pytest tests/test_opera_env_script.py tests/test_opera_properties_backend.py -q
uv run python scripts/check_opera_env.py
```

Expected: tests pass. On the current macOS host without OPERA installed, `check_opera_env.py` should print `status: missing`, not crash.

- [ ] **Step 7: Commit**

```bash
git add scripts/check_opera_env.py verifiers/backends/opera_properties.py verifiers/opera tests/test_opera_env_script.py tests/test_opera_properties_backend.py
git commit -m "feat: add opera verifier backend wrapper"
```

## Task 4: Native MatGL Environment Setup

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `scripts/check_matgl_env.py`
- Test: `tests/test_matgl_env_script.py`

- [ ] **Step 1: Decide dependency placement**

Recommended default: add MatGL to an optional dependency group to avoid destabilizing the base RDKit/xTB/ADMET environment until MatGL smoke passes.

Add to `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest==8.4.2",
]
materials = [
    "matgl==4.0.2",
]
```

If `uv` rejects custom dependency groups for this repo, add `matgl==4.0.2` to main dependencies and accept the `lightning` lockfile change after full tests pass.

- [ ] **Step 2: Update lock and sync the group**

Run:

```bash
uv lock
uv sync --group dev --group materials
```

Expected: lock succeeds. If `lightning` changes from 2.6.5 to 2.6.1, record it in the commit body and run all ADMET tests because ADMET-AI uses Lightning.

- [ ] **Step 3: Write MatGL env tests**

Create `tests/test_matgl_env_script.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys


def test_check_matgl_env_reports_json() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_matgl_env.py", "--no-model-load"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] in {"ok", "missing"}
    if payload["status"] == "ok":
        assert "matgl" in payload["versions"]
        assert payload["pymatgen"]["fixture_formula"] == "Si"
```

- [ ] **Step 4: Implement `scripts/check_matgl_env.py`**

Create `scripts/check_matgl_env.py`:

```python
#!/usr/bin/env python
"""Smoke-check native MatGL+pymatgen verifier environment."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SI_FIXTURE = ROOT / "tasks" / "matgl_materials" / "fixtures" / "Si.cif"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="MEGNet-Eform-MP-2018.6.1")
    parser.add_argument("--no-model-load", action="store_true")
    args = parser.parse_args()

    try:
        import matgl
        from pymatgen.core import Structure
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "missing",
                    "failure_type": "verifier_environment_error",
                    "message": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    structure = Structure.from_file(SI_FIXTURE)
    payload = {
        "status": "ok",
        "versions": {
            "matgl": metadata.version("matgl"),
            "pymatgen": metadata.version("pymatgen"),
            "torch": metadata.version("torch"),
        },
        "pymatgen": {
            "fixture": str(SI_FIXTURE),
            "fixture_formula": structure.composition.reduced_formula,
            "atom_count": len(structure),
        },
        "model": {"loaded": False, "name": args.model},
    }
    if not args.no_model_load:
        model = matgl.load_model(args.model)
        payload["model"]["loaded"] = True
        payload["model"]["class"] = type(model).__name__
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Verify MatGL environment script**

Run:

```bash
uv run pytest tests/test_matgl_env_script.py -q
uv run python scripts/check_matgl_env.py --no-model-load
```

Expected: after dependency setup, both report `status: ok`. Before dependency setup, the script may report `missing`, but tests should tolerate that only until this task is completed. Tighten the test to require `status == "ok"` once MatGL is installed.

- [ ] **Step 6: Optional model load smoke**

Run only when network/model cache is acceptable:

```bash
uv run python scripts/check_matgl_env.py --model MEGNet-Eform-MP-2018.6.1
```

Expected: model loads or fails with an actionable Hugging Face/cache error. If model download is required, cache it during Docker build or local setup, not at benchmark scoring time.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock scripts/check_matgl_env.py tests/test_matgl_env_script.py
git commit -m "build: add native matgl environment support"
```

## Task 5: Native MatGL Backend

**Files:**
- Create: `verifiers/backends/matgl_properties.py`
- Create: `verifiers/materials/matgl_property_script.py`
- Create: `verifiers/materials/matgl_bandgap.py`
- Create: `verifiers/materials/matgl_formation_energy.py`
- Test: `tests/test_matgl_properties_backend.py`
- Test: `tests/test_matgl_task_scripts.py`

- [ ] **Step 1: Write Native MatGL backend tests with fake model**

Create `tests/test_matgl_properties_backend.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from verifiers.backends import matgl_properties


SI_CIF = (Path(__file__).resolve().parents[1] / "tasks" / "matgl_materials" / "fixtures" / "Si.cif").read_text()


def spec(property_name: str = "formation_energy") -> dict:
    return {
        "verifier_id": f"matgl_{property_name}_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": property_name,
        "domain": {"allowed_elements": ["Si"], "atom_count": [1, 8], "volume": [1.0, 300.0]},
        "matgl": {"model_name": "MEGNet-Eform-MP-2018.6.1"},
    }


def constraint(property_name: str = "formation_energy") -> dict:
    return {
        "type": "window",
        "property": property_name,
        "verifier_id": f"matgl_{property_name}_v1",
        "min": -0.1,
        "max": 0.1,
        "sigma": 0.1,
    }


def test_matgl_scores_fake_prediction(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeModel:
        def predict_structure(self, structure):
            assert structure.composition.reduced_formula == "Si"
            return 0.02

    monkeypatch.setattr(matgl_properties, "load_matgl_model", lambda spec: FakeModel())

    result = matgl_properties.evaluate_matgl_constraint(
        {"cif": SI_CIF},
        {"task_id": "matgl_task"},
        constraint(),
        spec(),
    )

    assert result["status"] == "ok"
    assert result["properties"]["formation_energy"] == pytest.approx(0.02)
    assert result["scores"]["score"] == 1.0


def test_matgl_reports_parse_error() -> None:
    result = matgl_properties.evaluate_matgl_constraint(
        {"cif": "not a cif"},
        {"task_id": "matgl_task"},
        constraint(),
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
```

- [ ] **Step 2: Implement native MatGL backend**

Create `verifiers/backends/matgl_properties.py`:

```python
"""Native MatGL+pymatgen material property backend."""

from __future__ import annotations

import importlib.metadata as metadata
from functools import lru_cache
from typing import Any

from pymatgen.core import Structure

from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result, error_result


@lru_cache(maxsize=8)
def load_matgl_model_by_name(model_name: str):
    import matgl

    return matgl.load_model(model_name)


def load_matgl_model(spec: dict[str, Any]):
    model_name = str((spec.get("matgl") or {}).get("model_name", "MEGNet-Eform-MP-2018.6.1"))
    return load_matgl_model_by_name(model_name)


def evaluate_matgl_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    result = base_result(task_id, spec.get("verifier_id"), matgl_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
        return error_result(result, "verifier_spec_error", "MatGL property does not match constraint property")

    cif = candidate.get("cif")
    if not isinstance(cif, str) or not cif.strip():
        return error_result(result, "parse_error", "candidate must include a CIF string")
    try:
        structure = Structure.from_str(cif, fmt="cif")
    except Exception as exc:
        return error_result(result, "parse_error", f"CIF parse failed: {exc}")

    structure_properties = inspect_structure(structure)
    domain_error = check_domain(structure_properties, spec.get("domain", {}))
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=structure_properties)

    try:
        properties = {**structure_properties, **predict_property(structure, property_name, spec)}
    except ModuleNotFoundError as exc:
        return error_result(result, "verifier_environment_error", f"MatGL is not installed: {exc}")
    except Exception as exc:
        return error_result(result, "verifier_tool_error", f"MatGL prediction failed: {exc}", properties=structure_properties)

    constraint_score = {
        "property": constraint["property"],
        "type": constraint["type"],
        "score": score_constraint(properties, constraint),
    }
    score = float(constraint_score["score"])
    result.update(
        {
            "status": "ok",
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [constraint_score],
                "property_score": score,
                "score": score,
            },
        }
    )
    return result


def predict_property(structure: Structure, property_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    model = load_matgl_model(spec)
    if property_name == "formation_energy":
        value = model.predict_structure(structure)
        return {"formation_energy": float_value(value), "formation_energy_unit": "eV/atom"}
    if property_name == "bandgap":
        value = model.predict_structure(structure)
        return {"bandgap": float_value(value), "bandgap_unit": "eV"}
    raise ValueError(f"unsupported Native MatGL property: {property_name}")


def inspect_structure(structure: Structure) -> dict[str, Any]:
    return {
        "reduced_formula": structure.composition.reduced_formula,
        "atom_count": len(structure),
        "volume": float(structure.volume),
        "elements": sorted({str(element) for element in structure.composition.elements}),
    }


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    allowed_elements = domain.get("allowed_elements")
    if allowed_elements:
        disallowed = sorted(set(properties["elements"]) - set(allowed_elements))
        if disallowed:
            return f"disallowed elements: {', '.join(disallowed)}"
    if "atom_count" in domain:
        lower, upper = domain["atom_count"]
        if not int(lower) <= int(properties["atom_count"]) <= int(upper):
            return f"atom_count outside [{lower}, {upper}]"
    if "volume" in domain:
        lower, upper = domain["volume"]
        if not float(lower) <= float(properties["volume"]) <= float(upper):
            return f"volume outside [{lower}, {upper}]"
    return None


def float_value(value: Any) -> float:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return float(value)


def matgl_versions(spec: dict[str, Any]) -> dict[str, Any]:
    versions = {
        "verifier_image": spec.get("verifier_image"),
        "pymatgen": metadata.version("pymatgen"),
    }
    try:
        versions["matgl"] = metadata.version("matgl")
    except metadata.PackageNotFoundError:
        versions["matgl"] = None
    return versions
```

- [ ] **Step 3: Implement script wrappers**

Create `verifiers/materials/matgl_property_script.py`:

```python
"""Shared CLI helper for native MatGL verifier scripts."""

from __future__ import annotations

from verifiers.backends.matgl_properties import evaluate_matgl_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_matgl_constraint,
        sort_keys=True,
    )
```

Create `verifiers/materials/matgl_formation_energy.py`:

```python
from __future__ import annotations

from verifiers.materials.matgl_property_script import main

if __name__ == "__main__":
    main("formation_energy")
```

Create `verifiers/materials/matgl_bandgap.py`:

```python
from __future__ import annotations

from verifiers.materials.matgl_property_script import main

if __name__ == "__main__":
    main("bandgap")
```

- [ ] **Step 4: Write native MatGL script tests**

Create `tests/test_matgl_task_scripts.py` with a mismatch-only test that does not require model download:

```python
from __future__ import annotations

from pathlib import Path

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def test_matgl_script_property_mismatch() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "materials" / "matgl_formation_energy.py",
        {
            "task": {"task_id": "matgl_mismatch"},
            "candidate": {"cif": "not used"},
            "constraint": {"type": "window", "property": "bandgap", "verifier_id": "matgl_v1"},
            "verifier_spec": {
                "verifier_id": "matgl_v1",
                "property_name": "bandgap",
                "verification_script": "verifiers/materials/matgl_formation_energy.py",
            },
        },
        timeout_seconds=10,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
```

- [ ] **Step 5: Verify native MatGL backend**

Run:

```bash
uv run pytest tests/test_matgl_properties_backend.py tests/test_matgl_task_scripts.py -q
```

Expected: tests pass without downloading a model because backend tests monkeypatch model loading and script test checks mismatch before evaluation.

- [ ] **Step 6: Optional live model smoke**

After model cache is available:

```bash
uv run python scripts/check_matgl_env.py --model MEGNet-Eform-MP-2018.6.1
```

Expected: model loads and reports class. If it downloads from Hugging Face, document cache path and add a Docker build cache step in a later task.

- [ ] **Step 7: Commit**

```bash
git add verifiers/backends/matgl_properties.py verifiers/materials/matgl_* tests/test_matgl_properties_backend.py tests/test_matgl_task_scripts.py
git commit -m "feat: add native matgl verifier backend"
```

## Task 6: Integration Verification and Documentation Notes

**Files:**
- Modify: `docs/research/2026-06-29-admet-opera-materials-verifier-deployment-report.md` only if implementation findings differ from the report.
- Optionally create: `docs/tracks/ADMET.md` only if the implementation needs a stable track note. Do not add task design content.

- [ ] **Step 1: Run targeted backend tests**

Run:

```bash
uv run pytest \
  tests/test_admet_ai_env_script.py \
  tests/test_admet_ai_properties_backend.py \
  tests/test_admet_ai_task_scripts.py \
  tests/test_opera_env_script.py \
  tests/test_opera_properties_backend.py \
  tests/test_matgl_env_script.py \
  tests/test_matgl_properties_backend.py \
  tests/test_matgl_task_scripts.py \
  -q
```

Expected: all targeted tests pass.

- [ ] **Step 2: Run environment scripts**

Run:

```bash
uv run python scripts/check_admet_ai_env.py --smiles CCO
uv run python scripts/check_opera_env.py
uv run python scripts/check_matgl_env.py --no-model-load
```

Expected:

- ADMET-AI reports `status: ok`.
- OPERA reports either `status: ok` when configured or `status: missing` with a clear remediation message.
- Native MatGL reports `status: ok` after MatGL is installed.

- [ ] **Step 3: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 4: Commit any documentation updates**

If documentation changed:

```bash
git add docs/research/2026-06-29-admet-opera-materials-verifier-deployment-report.md docs/tracks/ADMET.md
git commit -m "docs: update verifier backend deployment notes"
```

- [ ] **Step 5: Final status summary**

Report:

- ADMET-AI backend status and endpoint list.
- OPERA status: configured executable path or missing/Docker-required.
- MatGL native status: installed version, model cache status, and whether live model load was run.
- Test command and pass/fail result.

## Risks and Decisions

- **ADMET-AI stdout pollution:** Must be handled inside backend with `contextlib.redirect_stdout` and `redirect_stderr`. Do not change `run_verification_script` unless a later backend makes that unavoidable.
- **ADMET-AI singleton caching:** Use `lru_cache` so repeated constraints do not reload all Chemprop models.
- **OPERA host mismatch:** Current host is macOS arm64. OPERA 2.9 official command-line package is Linux/Windows. Treat OPERA as an external CLI backend that can be configured by `OPERA_EXECUTABLE`; validate real deployment through Docker or Linux.
- **OPERA package size:** About 2 GiB. Do not commit OPERA binaries. Do not auto-download in tests.
- **MatGL dependency conflict:** Installing `matgl==4.0.2` may downgrade `lightning`. Full test suite is mandatory after dependency changes because ADMET-AI uses Lightning.
- **MatGL model downloads:** Do not download models during ordinary unit tests. Keep live model smoke explicit and cache models during image build.
- **No task design:** This plan intentionally avoids new `tasks/*` files. Formal tasks and thresholds should be a later plan.
