# Verifier Package Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hard-cut `src/verifiers` into tool/model-family packages, remove legacy domain/backends packages, preserve one property-level script per verifier property, and delete the experimental OPERA implementation.

**Architecture:** Shared framework code moves to `verifiers.common`, while each verifier family owns its `backend.py`, `cli.py`, and property entrypoint scripts. No compatibility shims remain: task specs, scripts, tests, and current docs are migrated to the new paths in the same branch.

**Tech Stack:** Python 3.12, pytest, PyYAML task specs, existing subprocess verifier runner, RDKit/xTB/ADMET-AI/MatGL/MACE-MP/TorchANI/SolTranNet/MolGpKa/OpenMM optional backend modules.

---

## File Structure

Create these package directories:

- `src/verifiers/common/`: framework-level helpers shared across verifier families.
- `src/verifiers/rdkit_descriptors/`: RDKit descriptor backend, CLI binder, and descriptor property scripts.
- `src/verifiers/rdkit_forcefield/`: RDKit force-field backend, CLI binder, and force-field property scripts.
- `src/verifiers/admet_ai/`: ADMET-AI backend, CLI binder, and ADMET property scripts.
- `src/verifiers/matgl/`: MatGL backend, CLI binder, and material property scripts.
- `src/verifiers/mace_mp/`: MACE-MP backend, CLI binder, and material property scripts.
- `src/verifiers/torchani/`: TorchANI backend, CLI binder, and molecular ML property scripts.
- `src/verifiers/soltrannet/`: SolTranNet backend, CLI binder, and property script.
- `src/verifiers/molgpka/`: MolGpKa backend, CLI binder, and property scripts.
- `src/verifiers/openmm/`: OpenMM runtime and OpenMM backend modules.

Keep `src/verifiers/xtb/`, but rename its backend and CLI helper:

- `src/verifiers/xtb/backend.py`
- `src/verifiers/xtb/cli.py`

Delete these package directories after their content has moved:

- `src/verifiers/backends/`
- `src/verifiers/descriptors/`
- `src/verifiers/forcefield/`
- `src/verifiers/materials/`
- `src/verifiers/physchem/`
- `src/verifiers/quantum_ml/`
- `src/verifiers/opera/`

Delete OPERA support files:

- `scripts/check_opera_env.py`
- `tests/test_opera_env_script.py`
- `tests/test_opera_properties_backend.py`

## Task 1: Move Shared Framework Utilities

**Files:**
- Create: `src/verifiers/common/__init__.py`
- Move: `src/verifiers/result_schema.py` -> `src/verifiers/common/result_schema.py`
- Move: `src/verifiers/scoring.py` -> `src/verifiers/common/scoring.py`
- Move: `src/verifiers/script_cli.py` -> `src/verifiers/common/property_cli.py`
- Move: `src/verifiers/backends/docker_model_runtime.py` -> `src/verifiers/common/docker_model_runtime.py`
- Modify: `src/verifiers/backends/*.py`
- Modify: `src/verifiers/*/*_property_script.py`
- Modify: `scripts/check_soltrannet_env.py`
- Modify: `scripts/check_molgpka_env.py`
- Test: `tests/test_result_schema.py`
- Test: `tests/test_script_cli.py`
- Test: `tests/test_docker_model_runtime.py`
- Test: `tests/test_soltrannet_properties_backend.py`
- Test: `tests/test_molgpka_properties_backend.py`

- [ ] **Step 1: Update common utility tests to expect the new package paths**

Use `apply_patch` to make these test import replacements:

```python
# tests/test_result_schema.py
from verifiers.common.result_schema import base_result, error_result

# tests/test_script_cli.py
from verifiers.common.property_cli import run_property_script

# tests/test_docker_model_runtime.py
from verifiers.common import docker_model_runtime as runtime
```

- [ ] **Step 2: Run targeted tests to verify the hard-cut paths are not implemented yet**

Run:

```bash
uv run pytest tests/test_result_schema.py tests/test_script_cli.py tests/test_docker_model_runtime.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'verifiers.common'`.

- [ ] **Step 3: Move shared modules into `verifiers.common`**

Run:

```bash
mkdir -p src/verifiers/common
touch src/verifiers/common/__init__.py
git mv src/verifiers/result_schema.py src/verifiers/common/result_schema.py
git mv src/verifiers/scoring.py src/verifiers/common/scoring.py
git mv src/verifiers/script_cli.py src/verifiers/common/property_cli.py
git mv src/verifiers/backends/docker_model_runtime.py src/verifiers/common/docker_model_runtime.py
```

- [ ] **Step 4: Update source, script, and test imports for shared utilities**

Run:

```bash
rg -l "verifiers\\.result_schema|verifiers\\.scoring|verifiers\\.script_cli|verifiers\\.backends import docker_model_runtime|verifiers\\.backends\\.docker_model_runtime" src tests scripts | xargs perl -0pi -e '
  s/from verifiers\.result_schema import/from verifiers.common.result_schema import/g;
  s/from verifiers\.scoring import/from verifiers.common.scoring import/g;
  s/from verifiers\.script_cli import/from verifiers.common.property_cli import/g;
  s/from verifiers\.backends import docker_model_runtime as runtime/from verifiers.common import docker_model_runtime as runtime/g;
  s/from verifiers\.backends import docker_model_runtime/from verifiers.common import docker_model_runtime/g;
  s/from verifiers\.backends\.docker_model_runtime import/from verifiers.common.docker_model_runtime import/g;
'
```

- [ ] **Step 5: Run common utility and Docker-backed backend tests**

Run:

```bash
uv run pytest \
  tests/test_result_schema.py \
  tests/test_script_cli.py \
  tests/test_docker_model_runtime.py \
  tests/test_soltrannet_properties_backend.py \
  tests/test_molgpka_properties_backend.py \
  tests/test_soltrannet_molgpka_env_scripts.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit shared utility migration**

Run:

```bash
git status --short
git add -A src/verifiers tests scripts
git commit -m "refactor: move shared verifier utilities"
```

## Task 2: Move RDKit Descriptor and Force-Field Packages

**Files:**
- Create: `src/verifiers/rdkit_descriptors/__init__.py`
- Create: `src/verifiers/rdkit_forcefield/__init__.py`
- Move: `src/verifiers/backends/rdkit_descriptors.py` -> `src/verifiers/rdkit_descriptors/backend.py`
- Move: `src/verifiers/descriptors/rdkit_descriptor_script.py` -> `src/verifiers/rdkit_descriptors/cli.py`
- Move: `src/verifiers/descriptors/rdkit_*.py` -> `src/verifiers/rdkit_descriptors/`
- Move: `src/verifiers/backends/rdkit_forcefield.py` -> `src/verifiers/rdkit_forcefield/backend.py`
- Move: `src/verifiers/forcefield/rdkit_forcefield_property_script.py` -> `src/verifiers/rdkit_forcefield/cli.py`
- Move: `src/verifiers/forcefield/rdkit_*.py` -> `src/verifiers/rdkit_forcefield/`
- Modify: `tasks/rdkit_baseline/verifier_specs.yaml`
- Modify: `tasks/rdkit_forcefield/verifier_specs.yaml`
- Modify: `tests/test_rdkit_descriptor_backend.py`
- Modify: `tests/test_rdkit_forcefield_backend.py`
- Modify: `tests/test_rdkit_task_scripts.py`
- Modify: `tests/test_rdkit_forcefield_task_scripts.py`
- Modify: `tests/test_small_molecule_rdkit.py`
- Modify: `tests/test_verifier_script_runner.py`

- [ ] **Step 1: Update RDKit tests and specs to expect new paths**

Use `apply_patch` for these representative replacements:

```python
# tests/test_rdkit_descriptor_backend.py
from verifiers.rdkit_descriptors import backend as rdkit_descriptors
from verifiers.rdkit_descriptors.backend import evaluate_descriptor_constraint

# tests/test_rdkit_forcefield_backend.py
from verifiers.rdkit_forcefield.backend import evaluate_forcefield_constraint

# tests/test_small_molecule_rdkit.py
from verifiers.common.scoring import score_constraint
```

In `tasks/rdkit_baseline/verifier_specs.yaml`, replace:

```yaml
verification_script: verifiers/descriptors/rdkit_qed.py
```

with:

```yaml
verification_script: verifiers/rdkit_descriptors/rdkit_qed.py
```

Apply the same path replacement for every `verifiers/descriptors/*.py` entry. In
`tasks/rdkit_forcefield/verifier_specs.yaml`, replace `verifiers/forcefield/`
with `verifiers/rdkit_forcefield/`.

- [ ] **Step 2: Run RDKit tests to verify the new paths fail before the move**

Run:

```bash
uv run pytest \
  tests/test_rdkit_descriptor_backend.py \
  tests/test_rdkit_forcefield_backend.py \
  tests/test_small_molecule_rdkit.py \
  tests/test_rdkit_task_scripts.py \
  tests/test_rdkit_forcefield_task_scripts.py -q
```

Expected: FAIL with missing `verifiers.rdkit_descriptors` or missing
`verifiers.rdkit_forcefield`.

- [ ] **Step 3: Move RDKit descriptor and force-field files**

Run:

```bash
mkdir -p src/verifiers/rdkit_descriptors src/verifiers/rdkit_forcefield
touch src/verifiers/rdkit_descriptors/__init__.py
touch src/verifiers/rdkit_forcefield/__init__.py
git mv src/verifiers/backends/rdkit_descriptors.py src/verifiers/rdkit_descriptors/backend.py
git mv src/verifiers/descriptors/rdkit_descriptor_script.py src/verifiers/rdkit_descriptors/cli.py
git mv src/verifiers/descriptors/rdkit_fraction_csp3.py src/verifiers/rdkit_descriptors/rdkit_fraction_csp3.py
git mv src/verifiers/descriptors/rdkit_hba.py src/verifiers/rdkit_descriptors/rdkit_hba.py
git mv src/verifiers/descriptors/rdkit_hbd.py src/verifiers/rdkit_descriptors/rdkit_hbd.py
git mv src/verifiers/descriptors/rdkit_logp.py src/verifiers/rdkit_descriptors/rdkit_logp.py
git mv src/verifiers/descriptors/rdkit_mw.py src/verifiers/rdkit_descriptors/rdkit_mw.py
git mv src/verifiers/descriptors/rdkit_qed.py src/verifiers/rdkit_descriptors/rdkit_qed.py
git mv src/verifiers/descriptors/rdkit_sa_score.py src/verifiers/rdkit_descriptors/rdkit_sa_score.py
git mv src/verifiers/descriptors/rdkit_tpsa.py src/verifiers/rdkit_descriptors/rdkit_tpsa.py
git mv src/verifiers/backends/rdkit_forcefield.py src/verifiers/rdkit_forcefield/backend.py
git mv src/verifiers/forcefield/rdkit_forcefield_property_script.py src/verifiers/rdkit_forcefield/cli.py
git mv src/verifiers/forcefield/rdkit_convergence.py src/verifiers/rdkit_forcefield/rdkit_convergence.py
git mv src/verifiers/forcefield/rdkit_energy_range.py src/verifiers/rdkit_forcefield/rdkit_energy_range.py
rm src/verifiers/descriptors/__init__.py
rm src/verifiers/forcefield/__init__.py
rmdir src/verifiers/descriptors src/verifiers/forcefield
```

- [ ] **Step 4: Update RDKit source imports**

Run:

```bash
rg -l "verifiers\\.backends\\.rdkit_descriptors|verifiers\\.backends import rdkit_descriptors|verifiers\\.backends\\.rdkit_forcefield|verifiers\\.descriptors\\.rdkit_descriptor_script|verifiers\\.forcefield\\.rdkit_forcefield_property_script" src tests scripts | xargs perl -0pi -e '
  s/from verifiers\.backends\.rdkit_descriptors import/from verifiers.rdkit_descriptors.backend import/g;
  s/from verifiers\.backends import rdkit_descriptors/from verifiers.rdkit_descriptors import backend as rdkit_descriptors/g;
  s/from verifiers\.backends\.rdkit_forcefield import/from verifiers.rdkit_forcefield.backend import/g;
  s/from verifiers\.descriptors\.rdkit_descriptor_script import main/from verifiers.rdkit_descriptors.cli import main/g;
  s/from verifiers\.forcefield\.rdkit_forcefield_property_script import main/from verifiers.rdkit_forcefield.cli import main/g;
'
```

- [ ] **Step 5: Run RDKit tests**

Run:

```bash
uv run pytest \
  tests/test_rdkit_descriptor_backend.py \
  tests/test_rdkit_forcefield_backend.py \
  tests/test_rdkit_task_scripts.py \
  tests/test_rdkit_forcefield_task_scripts.py \
  tests/test_rdkit_forcefield_tasks.py \
  tests/test_small_molecule_rdkit.py \
  tests/test_verifier_script_runner.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit RDKit package migration**

Run:

```bash
git status --short
git add -A src/verifiers tasks tests
git commit -m "refactor: split rdkit verifier packages"
```

## Task 3: Move xTB Backend and CLI Binder

**Files:**
- Move: `src/verifiers/backends/xtb_properties.py` -> `src/verifiers/xtb/backend.py`
- Move: `src/verifiers/xtb/xtb_property_script.py` -> `src/verifiers/xtb/cli.py`
- Modify: `src/verifiers/xtb/xtb_*.py`
- Modify: `scripts/check_xtb_env.py`
- Modify: `scripts/prepare_xtb_real_dataset_sample.py`
- Modify: `scripts/run_xtb_real_dataset_distribution.py`
- Modify: `tests/test_xtb_properties_backend.py`
- Modify: `tests/test_xtb_task_scripts.py`
- Modify: `tests/test_xtb_xyz_tasks.py`

- [ ] **Step 1: Update xTB imports in tests and scripts to the target package**

Use `apply_patch` for these replacements:

```python
# tests/test_xtb_properties_backend.py
from verifiers.xtb import backend as xtb_properties

# scripts/check_xtb_env.py
from verifiers.xtb.backend import XTBRunner, parse_xtb_output

# scripts/prepare_xtb_real_dataset_sample.py
from verifiers.xtb.backend import XTBParseError, check_domain, inspect_xyz, parse_xyz

# scripts/run_xtb_real_dataset_distribution.py
from verifiers.xtb.backend import XTBParseError, check_domain, inspect_xyz, parse_xyz
```

- [ ] **Step 2: Run xTB tests to verify the target backend path fails before the move**

Run:

```bash
uv run pytest tests/test_xtb_properties_backend.py tests/test_xtb_task_scripts.py tests/test_xtb_xyz_tasks.py -q
```

Expected: FAIL with missing `verifiers.xtb.backend`.

- [ ] **Step 3: Move xTB backend and CLI helper**

Run:

```bash
git mv src/verifiers/backends/xtb_properties.py src/verifiers/xtb/backend.py
git mv src/verifiers/xtb/xtb_property_script.py src/verifiers/xtb/cli.py
```

- [ ] **Step 4: Update xTB entrypoint imports and backend internal imports**

Run:

```bash
rg -l "verifiers\\.xtb\\.xtb_property_script|verifiers\\.backends\\.xtb_properties|verifiers\\.backends import xtb_properties" src tests scripts | xargs perl -0pi -e '
  s/from verifiers\.xtb\.xtb_property_script import main/from verifiers.xtb.cli import main/g;
  s/from verifiers\.backends\.xtb_properties import/from verifiers.xtb.backend import/g;
  s/from verifiers\.backends import xtb_properties/from verifiers.xtb import backend as xtb_properties/g;
'
```

Confirm `src/verifiers/xtb/backend.py` imports shared scoring from:

```python
from verifiers.common.scoring import score_constraint
from verifiers.common.result_schema import base_result
from verifiers.common.result_schema import error_result
```

- [ ] **Step 5: Run xTB-focused tests**

Run:

```bash
uv run pytest \
  tests/test_xtb_properties_backend.py \
  tests/test_xtb_task_scripts.py \
  tests/test_xtb_xyz_tasks.py \
  tests/test_xtb_check_script.py \
  tests/test_xtb_real_dataset_distribution_scripts.py \
  tests/test_xtb_real_dataset_distribution_inputs.py \
  tests/test_xtb_quality_gate_regression.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit xTB migration**

Run:

```bash
git status --short
git add -A src/verifiers scripts tests
git commit -m "refactor: move xtb backend into xtb package"
```

## Task 4: Move ADMET-AI Package

**Files:**
- Create: `src/verifiers/admet_ai/__init__.py`
- Move: `src/verifiers/backends/admet_ai_properties.py` -> `src/verifiers/admet_ai/backend.py`
- Move: `src/verifiers/admet/admet_ai_property_script.py` -> `src/verifiers/admet_ai/cli.py`
- Move: `src/verifiers/admet/admet_ai_*.py` -> `src/verifiers/admet_ai/`
- Modify: `scripts/check_admet_ai_env.py`
- Modify: `tests/test_admet_ai_properties_backend.py`
- Modify: `tests/test_admet_ai_task_scripts.py`
- Modify: `tests/test_admet_ai_env_script.py`

- [ ] **Step 1: Update ADMET-AI tests and env script imports**

Use `apply_patch` for these replacements:

```python
# tests/test_admet_ai_properties_backend.py
from verifiers.admet_ai import backend as admet_ai_properties

# src/verifiers/admet_ai/cli.py after the move
from verifiers.admet_ai.backend import evaluate_admet_ai_constraint
from verifiers.common.property_cli import run_property_script
```

In inline task-script specs, replace `verifiers/admet/` with
`verifiers/admet_ai/`.

- [ ] **Step 2: Run ADMET-AI tests to verify the new package is missing**

Run:

```bash
uv run pytest tests/test_admet_ai_properties_backend.py tests/test_admet_ai_task_scripts.py tests/test_admet_ai_env_script.py -q
```

Expected: FAIL with missing `verifiers.admet_ai`.

- [ ] **Step 3: Move ADMET-AI files**

Run:

```bash
mkdir -p src/verifiers/admet_ai
touch src/verifiers/admet_ai/__init__.py
git mv src/verifiers/backends/admet_ai_properties.py src/verifiers/admet_ai/backend.py
git mv src/verifiers/admet/admet_ai_property_script.py src/verifiers/admet_ai/cli.py
git mv src/verifiers/admet/admet_ai_ames.py src/verifiers/admet_ai/admet_ai_ames.py
git mv src/verifiers/admet/admet_ai_bbb.py src/verifiers/admet_ai/admet_ai_bbb.py
git mv src/verifiers/admet/admet_ai_caco2.py src/verifiers/admet_ai/admet_ai_caco2.py
git mv src/verifiers/admet/admet_ai_herg.py src/verifiers/admet_ai/admet_ai_herg.py
git mv src/verifiers/admet/admet_ai_solubility_aqsoldb.py src/verifiers/admet_ai/admet_ai_solubility_aqsoldb.py
rm src/verifiers/admet/__init__.py
rmdir src/verifiers/admet
```

- [ ] **Step 4: Update ADMET-AI imports**

Run:

```bash
rg -l "verifiers\\.backends\\.admet_ai_properties|verifiers\\.backends import admet_ai_properties|verifiers\\.admet\\.admet_ai_property_script|verifiers/admet/" src tests scripts | xargs perl -0pi -e '
  s/from verifiers\.backends\.admet_ai_properties import/from verifiers.admet_ai.backend import/g;
  s/from verifiers\.backends import admet_ai_properties/from verifiers.admet_ai import backend as admet_ai_properties/g;
  s/from verifiers\.admet\.admet_ai_property_script import main/from verifiers.admet_ai.cli import main/g;
  s#verifiers/admet/#verifiers/admet_ai/#g;
'
```

- [ ] **Step 5: Run ADMET-AI tests**

Run:

```bash
uv run pytest tests/test_admet_ai_properties_backend.py tests/test_admet_ai_task_scripts.py tests/test_admet_ai_env_script.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit ADMET-AI migration**

Run:

```bash
git status --short
git add -A src/verifiers scripts tests
git commit -m "refactor: move admet ai verifier package"
```

## Task 5: Move MatGL, MACE-MP, and TorchANI Packages

**Files:**
- Create: `src/verifiers/matgl/__init__.py`
- Create: `src/verifiers/mace_mp/__init__.py`
- Create: `src/verifiers/torchani/__init__.py`
- Move: `src/verifiers/backends/matgl_properties.py` -> `src/verifiers/matgl/backend.py`
- Move: `src/verifiers/materials/matgl_property_script.py` -> `src/verifiers/matgl/cli.py`
- Move: `src/verifiers/materials/matgl_*.py` -> `src/verifiers/matgl/`
- Move: `src/verifiers/backends/mace_mp_properties.py` -> `src/verifiers/mace_mp/backend.py`
- Move: `src/verifiers/materials/mace_mp_property_script.py` -> `src/verifiers/mace_mp/cli.py`
- Move: `src/verifiers/materials/mace_mp_*.py` -> `src/verifiers/mace_mp/`
- Move: `src/verifiers/backends/torchani_properties.py` -> `src/verifiers/torchani/backend.py`
- Move: `src/verifiers/quantum_ml/torchani_property_script.py` -> `src/verifiers/torchani/cli.py`
- Move: `src/verifiers/quantum_ml/torchani_*.py` -> `src/verifiers/torchani/`
- Modify: `scripts/check_matgl_env.py`
- Modify: `scripts/check_mace_mp_env.py`
- Modify: `scripts/check_torchani_env.py`
- Modify: `tests/test_matgl_properties_backend.py`
- Modify: `tests/test_matgl_task_scripts.py`
- Modify: `tests/test_mace_mp_properties_backend.py`
- Modify: `tests/test_torchani_properties_backend.py`
- Modify: `tests/test_torchani_mace_task_scripts.py`
- Modify: `tests/test_torchani_mace_env_scripts.py`

- [ ] **Step 1: Update tests and env scripts to target new package paths**

Use `apply_patch` for these replacements:

```python
# tests/test_matgl_properties_backend.py
from verifiers.matgl import backend as matgl_properties

# tests/test_mace_mp_properties_backend.py
from verifiers.mace_mp import backend as mace_mp_properties

# tests/test_torchani_properties_backend.py
from verifiers.torchani import backend as torchani_properties
```

Replace inline script paths:

```python
"verification_script": "verifiers/matgl/matgl_bandgap.py"
"verification_script": "verifiers/mace_mp/mace_mp_energy_per_atom.py"
"verification_script": "verifiers/torchani/torchani_total_energy.py"
```

- [ ] **Step 2: Run ML/material tests to verify target packages are missing**

Run:

```bash
uv run pytest \
  tests/test_matgl_properties_backend.py \
  tests/test_matgl_task_scripts.py \
  tests/test_mace_mp_properties_backend.py \
  tests/test_torchani_properties_backend.py \
  tests/test_torchani_mace_task_scripts.py -q
```

Expected: FAIL with missing `verifiers.matgl`, `verifiers.mace_mp`, or
`verifiers.torchani`.

- [ ] **Step 3: Move MatGL, MACE-MP, and TorchANI files**

Run:

```bash
mkdir -p src/verifiers/matgl src/verifiers/mace_mp src/verifiers/torchani
touch src/verifiers/matgl/__init__.py src/verifiers/mace_mp/__init__.py src/verifiers/torchani/__init__.py
git mv src/verifiers/backends/matgl_properties.py src/verifiers/matgl/backend.py
git mv src/verifiers/materials/matgl_property_script.py src/verifiers/matgl/cli.py
git mv src/verifiers/materials/matgl_bandgap.py src/verifiers/matgl/matgl_bandgap.py
git mv src/verifiers/materials/matgl_formation_energy.py src/verifiers/matgl/matgl_formation_energy.py
git mv src/verifiers/backends/mace_mp_properties.py src/verifiers/mace_mp/backend.py
git mv src/verifiers/materials/mace_mp_property_script.py src/verifiers/mace_mp/cli.py
git mv src/verifiers/materials/mace_mp_energy.py src/verifiers/mace_mp/mace_mp_energy.py
git mv src/verifiers/materials/mace_mp_energy_per_atom.py src/verifiers/mace_mp/mace_mp_energy_per_atom.py
git mv src/verifiers/materials/mace_mp_max_force.py src/verifiers/mace_mp/mace_mp_max_force.py
git mv src/verifiers/materials/mace_mp_stress_norm.py src/verifiers/mace_mp/mace_mp_stress_norm.py
git mv src/verifiers/backends/torchani_properties.py src/verifiers/torchani/backend.py
git mv src/verifiers/quantum_ml/torchani_property_script.py src/verifiers/torchani/cli.py
git mv src/verifiers/quantum_ml/torchani_energy_per_atom.py src/verifiers/torchani/torchani_energy_per_atom.py
git mv src/verifiers/quantum_ml/torchani_max_force.py src/verifiers/torchani/torchani_max_force.py
git mv src/verifiers/quantum_ml/torchani_total_energy.py src/verifiers/torchani/torchani_total_energy.py
rm src/verifiers/materials/__init__.py
rm src/verifiers/quantum_ml/__init__.py
rmdir src/verifiers/materials src/verifiers/quantum_ml
```

- [ ] **Step 4: Update ML/material imports and inline verifier script paths**

Run:

```bash
rg -l "verifiers\\.backends\\.(matgl_properties|mace_mp_properties|torchani_properties)|verifiers\\.backends import (matgl_properties|mace_mp_properties|torchani_properties)|verifiers\\.materials\\.(matgl_property_script|mace_mp_property_script)|verifiers\\.quantum_ml\\.torchani_property_script|verifiers/(materials|quantum_ml)/" src tests scripts | xargs perl -0pi -e '
  s/from verifiers\.backends\.matgl_properties import/from verifiers.matgl.backend import/g;
  s/from verifiers\.backends import matgl_properties/from verifiers.matgl import backend as matgl_properties/g;
  s/from verifiers\.materials\.matgl_property_script import main/from verifiers.matgl.cli import main/g;
  s#from verifiers\.backends\.mace_mp_properties import#from verifiers.mace_mp.backend import#g;
  s/from verifiers\.backends import mace_mp_properties/from verifiers.mace_mp import backend as mace_mp_properties/g;
  s/from verifiers\.materials\.mace_mp_property_script import main/from verifiers.mace_mp.cli import main/g;
  s/from verifiers\.backends\.torchani_properties import/from verifiers.torchani.backend import/g;
  s/from verifiers\.backends import torchani_properties/from verifiers.torchani import backend as torchani_properties/g;
  s/from verifiers\.quantum_ml\.torchani_property_script import main/from verifiers.torchani.cli import main/g;
  s#verifiers/materials/matgl_#verifiers/matgl/matgl_#g;
  s#verifiers/materials/mace_mp_#verifiers/mace_mp/mace_mp_#g;
  s#verifiers/quantum_ml/torchani_#verifiers/torchani/torchani_#g;
'
```

- [ ] **Step 5: Run ML/material tests**

Run:

```bash
uv run pytest \
  tests/test_matgl_env_script.py \
  tests/test_matgl_properties_backend.py \
  tests/test_matgl_task_scripts.py \
  tests/test_mace_mp_properties_backend.py \
  tests/test_torchani_properties_backend.py \
  tests/test_torchani_mace_env_scripts.py \
  tests/test_torchani_mace_task_scripts.py \
  tests/test_torchani_mace_live_smoke.py -q
```

Expected: PASS with live smoke tests skipped unless optional live prerequisites
are available.

- [ ] **Step 6: Commit ML/material package migration**

Run:

```bash
git status --short
git add -A src/verifiers scripts tests
git commit -m "refactor: move mlip verifier packages"
```

## Task 6: Move SolTranNet and MolGpKa Packages

**Files:**
- Create: `src/verifiers/soltrannet/__init__.py`
- Create: `src/verifiers/molgpka/__init__.py`
- Move: `src/verifiers/backends/soltrannet_properties.py` -> `src/verifiers/soltrannet/backend.py`
- Move: `src/verifiers/physchem/soltrannet_property_script.py` -> `src/verifiers/soltrannet/cli.py`
- Move: `src/verifiers/physchem/soltrannet_log_s.py` -> `src/verifiers/soltrannet/soltrannet_log_s.py`
- Move: `src/verifiers/backends/molgpka_properties.py` -> `src/verifiers/molgpka/backend.py`
- Move: `src/verifiers/physchem/molgpka_property_script.py` -> `src/verifiers/molgpka/cli.py`
- Move: `src/verifiers/physchem/molgpka_*.py` -> `src/verifiers/molgpka/`
- Modify: `scripts/check_soltrannet_env.py`
- Modify: `scripts/check_molgpka_env.py`
- Modify: `tests/test_soltrannet_properties_backend.py`
- Modify: `tests/test_molgpka_properties_backend.py`
- Modify: `tests/test_physchem_task_scripts.py`
- Modify: `tests/test_soltrannet_molgpka_env_scripts.py`
- Modify: `tests/test_soltrannet_molgpka_docker_smoke.py`

- [ ] **Step 1: Update physchem tests and env scripts to target package paths**

Use `apply_patch` for these imports:

```python
# tests/test_soltrannet_properties_backend.py
from verifiers.soltrannet import backend as soltrannet_properties

# tests/test_molgpka_properties_backend.py
from verifiers.molgpka import backend as molgpka_properties

# tests/test_physchem_task_scripts.py
from verifiers.molgpka import cli as molgpka_property_script
from verifiers.soltrannet import cli as soltrannet_property_script
```

Replace inline script paths:

```python
"verification_script": "verifiers/soltrannet/soltrannet_log_s.py"
"verification_script": "verifiers/molgpka/molgpka_pka_count.py"
```

- [ ] **Step 2: Run physchem tests to verify target packages are missing**

Run:

```bash
uv run pytest \
  tests/test_soltrannet_properties_backend.py \
  tests/test_molgpka_properties_backend.py \
  tests/test_physchem_task_scripts.py \
  tests/test_soltrannet_molgpka_env_scripts.py -q
```

Expected: FAIL with missing `verifiers.soltrannet` or `verifiers.molgpka`.

- [ ] **Step 3: Move SolTranNet and MolGpKa files**

Run:

```bash
mkdir -p src/verifiers/soltrannet src/verifiers/molgpka
touch src/verifiers/soltrannet/__init__.py src/verifiers/molgpka/__init__.py
git mv src/verifiers/backends/soltrannet_properties.py src/verifiers/soltrannet/backend.py
git mv src/verifiers/physchem/soltrannet_property_script.py src/verifiers/soltrannet/cli.py
git mv src/verifiers/physchem/soltrannet_log_s.py src/verifiers/soltrannet/soltrannet_log_s.py
git mv src/verifiers/backends/molgpka_properties.py src/verifiers/molgpka/backend.py
git mv src/verifiers/physchem/molgpka_property_script.py src/verifiers/molgpka/cli.py
git mv src/verifiers/physchem/molgpka_min_pka.py src/verifiers/molgpka/molgpka_min_pka.py
git mv src/verifiers/physchem/molgpka_max_pka.py src/verifiers/molgpka/molgpka_max_pka.py
git mv src/verifiers/physchem/molgpka_pka_count.py src/verifiers/molgpka/molgpka_pka_count.py
rm src/verifiers/physchem/__init__.py
rmdir src/verifiers/physchem
```

- [ ] **Step 4: Update SolTranNet and MolGpKa imports**

Run:

```bash
rg -l "verifiers\\.backends\\.(soltrannet_properties|molgpka_properties)|verifiers\\.backends import (soltrannet_properties|molgpka_properties)|verifiers\\.physchem\\.(soltrannet_property_script|molgpka_property_script)|verifiers/physchem/" src tests scripts | xargs perl -0pi -e '
  s/from verifiers\.backends\.soltrannet_properties import/from verifiers.soltrannet.backend import/g;
  s/from verifiers\.backends import soltrannet_properties/from verifiers.soltrannet import backend as soltrannet_properties/g;
  s/from verifiers\.physchem\.soltrannet_property_script import main/from verifiers.soltrannet.cli import main/g;
  s/from verifiers\.backends\.molgpka_properties import/from verifiers.molgpka.backend import/g;
  s/from verifiers\.backends import molgpka_properties/from verifiers.molgpka import backend as molgpka_properties/g;
  s/from verifiers\.physchem\.molgpka_property_script import main/from verifiers.molgpka.cli import main/g;
  s#verifiers/physchem/soltrannet_#verifiers/soltrannet/soltrannet_#g;
  s#verifiers/physchem/molgpka_#verifiers/molgpka/molgpka_#g;
'
```

- [ ] **Step 5: Run Docker-backed physchem tests**

Run:

```bash
uv run pytest \
  tests/test_soltrannet_properties_backend.py \
  tests/test_molgpka_properties_backend.py \
  tests/test_physchem_task_scripts.py \
  tests/test_soltrannet_molgpka_env_scripts.py \
  tests/test_soltrannet_molgpka_docker_smoke.py -q
```

Expected: PASS with Docker smoke tests skipped unless explicitly enabled.

- [ ] **Step 6: Commit SolTranNet and MolGpKa migration**

Run:

```bash
git status --short
git add -A src/verifiers scripts tests
git commit -m "refactor: move docker model verifier packages"
```

## Task 7: Move OpenMM Family Package

**Files:**
- Create: `src/verifiers/openmm/__init__.py`
- Move: `src/verifiers/backends/openmm_runtime.py` -> `src/verifiers/openmm/runtime.py`
- Move: `src/verifiers/backends/openmm_core_properties.py` -> `src/verifiers/openmm/core_backend.py`
- Move: `src/verifiers/backends/openmm_openff_properties.py` -> `src/verifiers/openmm/openff_backend.py`
- Modify: `scripts/check_openmm_openff_env.py`
- Modify: `tests/test_openmm_core_backend.py`
- Modify: `tests/test_openmm_openff_backend.py`
- Modify: `tests/test_openmm_openff_env_script.py`
- Modify: `tests/test_openmm_openff_no_tasks.py`

- [ ] **Step 1: Update OpenMM tests and env script imports**

Use `apply_patch` for these imports:

```python
# tests/test_openmm_core_backend.py
from verifiers.openmm import core_backend as openmm_core_properties
from verifiers.openmm.runtime import OpenMMEnvironmentError, OpenMMToolError

# tests/test_openmm_openff_backend.py
from verifiers.openmm import openff_backend as openmm_openff_properties
from verifiers.openmm.runtime import OpenMMEnvironmentError, OpenMMToolError

# scripts/check_openmm_openff_env.py
from verifiers.openmm import runtime as openmm_runtime
```

- [ ] **Step 2: Run OpenMM tests to verify target package is missing**

Run:

```bash
uv run pytest tests/test_openmm_core_backend.py tests/test_openmm_openff_backend.py tests/test_openmm_openff_env_script.py -q
```

Expected: FAIL with missing `verifiers.openmm`.

- [ ] **Step 3: Move OpenMM modules**

Run:

```bash
mkdir -p src/verifiers/openmm
touch src/verifiers/openmm/__init__.py
git mv src/verifiers/backends/openmm_runtime.py src/verifiers/openmm/runtime.py
git mv src/verifiers/backends/openmm_core_properties.py src/verifiers/openmm/core_backend.py
git mv src/verifiers/backends/openmm_openff_properties.py src/verifiers/openmm/openff_backend.py
```

- [ ] **Step 4: Update OpenMM imports**

Run:

```bash
rg -l "verifiers\\.backends\\.openmm_runtime|verifiers\\.backends import openmm_runtime|verifiers\\.backends import openmm_core_properties|verifiers\\.backends import openmm_openff_properties" src tests scripts | xargs perl -0pi -e '
  s/from verifiers\.backends\.openmm_runtime import/from verifiers.openmm.runtime import/g;
  s/from verifiers\.backends import openmm_runtime/from verifiers.openmm import runtime as openmm_runtime/g;
  s/from verifiers\.backends import openmm_core_properties/from verifiers.openmm import core_backend as openmm_core_properties/g;
  s/from verifiers\.backends import openmm_openff_properties/from verifiers.openmm import openff_backend as openmm_openff_properties/g;
'
```

Confirm both OpenMM backends import generic scoring from:

```python
from verifiers.common.scoring import score_constraint
```

- [ ] **Step 5: Run OpenMM tests**

Run:

```bash
uv run pytest \
  tests/test_openmm_core_backend.py \
  tests/test_openmm_openff_backend.py \
  tests/test_openmm_openff_env_script.py \
  tests/test_openmm_openff_env_file.py \
  tests/test_openmm_openff_no_tasks.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit OpenMM migration**

Run:

```bash
git status --short
git add -A src/verifiers scripts tests
git commit -m "refactor: move openmm verifier package"
```

## Task 8: Remove Experimental OPERA Implementation

**Files:**
- Delete: `src/verifiers/backends/opera_properties.py`
- Delete: `src/verifiers/opera/__init__.py`
- Delete: `src/verifiers/opera/opera_property_script.py`
- Delete: `scripts/check_opera_env.py`
- Delete: `tests/test_opera_env_script.py`
- Delete: `tests/test_opera_properties_backend.py`
- Modify: `docs/research/2026-07-06-verifier-backend-property-inventory.md`

- [ ] **Step 1: Delete OPERA code, env script, and tests**

Run:

```bash
git rm src/verifiers/backends/opera_properties.py
git rm -r src/verifiers/opera
git rm scripts/check_opera_env.py
git rm tests/test_opera_env_script.py
git rm tests/test_opera_properties_backend.py
```

- [ ] **Step 2: Remove OPERA from current capability inventory**

Use `apply_patch` to delete the OPERA row from:

```text
docs/research/2026-07-06-verifier-backend-property-inventory.md
```

Also remove `src/verifiers/backends/opera_properties.py` from that document's
source-file list.

- [ ] **Step 3: Run OPERA absence checks**

Run:

```bash
rg -n "opera|OPERA" src tests scripts docs/tracks docs/design docs/research/2026-07-06-verifier-backend-property-inventory.md
```

Expected: no hits in `src`, `tests`, `scripts`, current track docs, current design
docs, or the current capability inventory. Hits in older historical research or
Superpowers plan files are acceptable only outside this command scope.

- [ ] **Step 4: Run default tests after deletion**

Run:

```bash
uv run pytest -q
```

Expected: PASS with the OPERA tests no longer collected.

- [ ] **Step 5: Commit OPERA removal**

Run:

```bash
git status --short
git add -A src/verifiers scripts tests docs/research/2026-07-06-verifier-backend-property-inventory.md
git commit -m "refactor: remove experimental opera verifier"
```

## Task 9: Update Current Docs and Final Hard-Cut Verification

**Files:**
- Modify: `docs/design/INITIAL-DESIGN.md`
- Modify: `docs/research/2026-06-30-verifier-backend-method-coverage-gap-report.md`
- Modify: `docs/research/2026-07-01-rdkit-forcefield-extended-property-candidates.md`
- Modify: `docs/research/2026-07-03-top20-deployable-physchem-quantum-material-ml-property-models.md`
- Modify: `docs/research/2026-07-06-verifier-backend-property-inventory.md`
- Modify: `docs/tracks/OpenMM-OpenFF.md`
- Modify: `docs/tracks/RDKit.md`
- Modify: `docs/tracks/RDKit-Forcefield.md`
- Modify: `docs/tracks/xTB.md`
- Modify: `tests/test_public_api.py`
- Modify: `tests/test_packaging.py`
- Modify: `tests/test_installed_wheel.py`

- [ ] **Step 1: Update current documentation path examples**

Use `apply_patch` to update current docs to the new path names. Required examples:

```text
verifiers/rdkit_descriptors/rdkit_qed.py
verifiers/rdkit_forcefield/rdkit_energy_range.py
verifiers/xtb/backend.py
verifiers/matgl/backend.py
verifiers/openmm/runtime.py
verifiers/common/scoring.py
```

Do not rewrite historical Superpowers implementation plans. The new restructure
design and plan documents are the authoritative migration record.

- [ ] **Step 2: Remove the empty `src/verifiers/backends` directory**

Run:

```bash
rm src/verifiers/backends/__init__.py
rmdir src/verifiers/backends
```

Expected: `rmdir` succeeds, proving no backend modules remain there.

- [ ] **Step 3: Run hard-cut path scan**

Run:

```bash
rg -n "verifiers\\.backends|verifiers/(backends|descriptors|forcefield|materials|physchem|quantum_ml|opera)|verifiers\\.(descriptors|forcefield|materials|physchem|quantum_ml|opera)" src tests tasks scripts docs/design docs/tracks docs/research/2026-07-06-verifier-backend-property-inventory.md
```

Expected: no hits. If the scan reports any source, test, task, script, current
track doc, current design doc, or current inventory hit, update that file to the
new package path and rerun the scan.

- [ ] **Step 4: Verify property-level script paths still exist**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml

root = Path.cwd()
for spec_path in sorted(Path("tasks").glob("*/verifier_specs.yaml")):
    payload = yaml.safe_load(spec_path.read_text())
    for spec in payload.get("verifiers", []):
        script = spec.get("verification_script")
        if script:
            path = root / "src" / script
            if not path.exists():
                raise SystemExit(f"missing script for {spec['verifier_id']}: {script}")
print("all verifier script paths exist")
PY
```

Expected output:

```text
all verifier script paths exist
```

- [ ] **Step 5: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: PASS. The exact pass count will be lower than the pre-removal baseline
because OPERA tests are deleted.

- [ ] **Step 6: Commit final docs and cleanup**

Run:

```bash
git status --short
git add -A docs tests src tasks scripts
git commit -m "docs: update verifier package paths"
```

## Final Review Checklist

- [ ] `git status --short` shows a clean worktree.
- [ ] `git log --oneline -8` shows the migration commits on `refactor/verifier-package-restructure`.
- [ ] `uv run pytest` passed after all moves and OPERA deletion.
- [ ] The hard-cut path scan has no hits in `src`, `tests`, `tasks`, `scripts`, `docs/design`, `docs/tracks`, or the current capability inventory.
- [ ] Every non-historical `verification_script` path points to an existing property-level script.
- [ ] There is no `src/verifiers/backends` directory.
- [ ] There is no `src/verifiers/opera` directory.
- [ ] The final code still exposes one runnable property script per property.
