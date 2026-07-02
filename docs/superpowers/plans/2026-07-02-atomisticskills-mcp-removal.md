# AtomisticSkills MCP Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the active AtomisticSkills MCP prototype path while preserving the native MatGL Python verifier implementation.

**Architecture:** Delete the experimental AtomisticSkills/MCP task packs, adapters, scripts, and tests. Move the silicon CIF fixture needed by native MatGL tests out of deleted task packs, and keep native MatGL code independent of task-pack resources. Update packaging and current-state docs so the active published surface is RDKit/xTB plus native MatGL code behind the materials extra, without MCP.

**Tech Stack:** Python 3.12, pytest, uv, hatchling, PyYAML, pymatgen, optional MatGL.

---

## File Structure

- Create `tests/fixtures/Si.cif`: shared test fixture copied from `tasks/matgl_materials/fixtures/Si.cif`.
- Modify `scripts/check_matgl_env.py`: remove dependency on `tasks/matgl_materials/fixtures/Si.cif`; use an internal temporary Si fixture.
- Modify `tests/test_matgl_properties_backend.py`: read `tests/fixtures/Si.cif`.
- Modify `tests/test_answer_extraction.py`: replace AtomisticSkills task ids used only as answer-extraction examples with neutral ids.
- Modify `tests/test_packaging.py`: assert removed prototype task packs are absent from built artifacts and the `mcp` dependency is absent from metadata.
- Modify `tests/test_public_api.py`: assert built-in suite excludes deleted prototype prefixes including `atomisticskills_`.
- Modify `pyproject.toml`: remove `mcp>=1.27.2`; remove wheel force-includes for deleted prototype task packs.
- Modify `uv.lock`: refresh after dependency removal.
- Modify `docs/design/INITIAL-DESIGN.md`: replace active AtomisticSkills/MCP prototype status with removal/current native-MatGL direction.
- Modify `docs/superpowers/specs/2026-06-29-pipeline-package-framework-design.md`: update non-goals and test descriptions to reflect removed prototype packs.
- Delete `tasks/atomisticskills_smoke/`.
- Delete `tasks/mace_materials/`.
- Delete `tasks/matgl_materials/`.
- Delete `verifiers/atomisticskills_backend.py`.
- Delete `verifiers/atomisticskills_mcp_shims/`.
- Delete `verifiers/backends/atomisticskills_matgl_properties.py`.
- Delete `verifiers/backends/mace_properties.py`.
- Delete `verifiers/materials/atomisticskills_matgl_bandgap.py`.
- Delete `verifiers/materials/atomisticskills_matgl_formation_energy.py`.
- Delete `verifiers/materials/atomisticskills_matgl_property_script.py`.
- Delete `verifiers/materials/mace_energy.py`.
- Delete `verifiers/materials/mace_property_script.py`.
- Delete `scripts/check_atomisticskills_env.py`.
- Delete `scripts/check_atomisticskills_matgl_env.py`.
- Delete `scripts/check_atomisticskills_mace_env.py`.
- Delete `scripts/setup_atomisticskills_first_batch.sh`.
- Delete `scripts/setup_atomisticskills_matgl.sh`.
- Delete `scripts/setup_atomisticskills_mace.sh`.
- Delete `tests/test_atomisticskills_adapters.py`.
- Delete `tests/test_atomisticskills_check_script.py`.
- Delete `tests/test_atomisticskills_mace_scripts.py`.
- Delete `tests/test_atomisticskills_matgl_material_tasks.py`.
- Delete `tests/test_atomisticskills_matgl_properties_backend.py`.
- Delete `tests/test_atomisticskills_matgl_scripts.py`.
- Delete `tests/test_atomisticskills_matgl_task_scripts.py`.
- Delete `tests/test_atomisticskills_setup_script.py`.
- Delete `tests/test_mace_material_tasks.py`.
- Delete `tests/test_mace_properties_backend.py`.
- Delete `tests/test_mace_task_scripts.py`.

### Task 1: Preserve Native MatGL Fixture Independence

**Files:**
- Create: `tests/fixtures/Si.cif`
- Modify: `scripts/check_matgl_env.py`
- Modify: `tests/test_matgl_properties_backend.py`
- Test: `tests/test_matgl_env_script.py`
- Test: `tests/test_matgl_properties_backend.py`

- [ ] **Step 1: Add a stable test fixture outside prototype task packs**

Copy the current Si CIF fixture before deleting task packs:

```bash
mkdir -p tests/fixtures
cp tasks/matgl_materials/fixtures/Si.cif tests/fixtures/Si.cif
```

Expected: `tests/fixtures/Si.cif` exists and contains a parseable Si CIF.

- [ ] **Step 2: Update native MatGL backend tests to use the new fixture**

In `tests/test_matgl_properties_backend.py`, replace:

```python
SI_CIF = (Path(__file__).resolve().parents[1] / "tasks" / "matgl_materials" / "fixtures" / "Si.cif").read_text()
```

with:

```python
SI_CIF = (Path(__file__).resolve().parent / "fixtures" / "Si.cif").read_text()
```

- [ ] **Step 3: Make `check_matgl_env.py` independent of deleted task packs**

In `scripts/check_matgl_env.py`, add this constant after `ROOT`:

```python
SI_CIF_TEXT = """# generated using pymatgen
data_Si
_symmetry_space_group_name_H-M   'P 1'
_cell_length_a   3.8401979337
_cell_length_b   3.8401989943
_cell_length_c   3.8401979337
_cell_angle_alpha   119.9999908638
_cell_angle_beta   90.0000000000
_cell_angle_gamma   60.0000091371
_symmetry_Int_Tables_number   1
_chemical_formula_structural   Si
_chemical_formula_sum   Si2
_cell_volume   40.0478694978
_cell_formula_units_Z   2
loop_
 _symmetry_equiv_pos_site_id
 _symmetry_equiv_pos_as_xyz
  1  'x, y, z'
loop_
 _atom_site_type_symbol
 _atom_site_label
 _atom_site_symmetry_multiplicity
 _atom_site_fract_x
 _atom_site_fract_y
 _atom_site_fract_z
 _atom_site_occupancy
  Si  Si0  1  0.8750000000  0.8750000000  0.8750000000  1
  Si  Si1  1  0.1250000000  0.1250000000  0.1250000000  1
"""
```

Remove:

```python
SI_FIXTURE = ROOT / "tasks" / "matgl_materials" / "fixtures" / "Si.cif"
```

Inside `build_payload`, replace:

```python
structure = Structure.from_file(SI_FIXTURE)
```

with:

```python
structure = Structure.from_str(SI_CIF_TEXT, fmt="cif")
```

Replace the fixture parse error block:

```python
"message": f"failed to parse fixture {SI_FIXTURE}: {exc}",
```

with:

```python
"message": f"failed to parse embedded Si CIF fixture: {exc}",
```

Replace payload fixture metadata:

```python
"fixture": str(SI_FIXTURE),
```

with:

```python
"fixture": "embedded_si_cif",
```

- [ ] **Step 4: Run native MatGL tests**

Run:

```bash
uv run pytest tests/test_matgl_env_script.py tests/test_matgl_properties_backend.py tests/test_matgl_task_scripts.py -q
```

Expected: all selected tests pass.

### Task 2: Remove AtomisticSkills, MCP, MACE Prototype Code And Tests

**Files:**
- Delete the task packs, AtomisticSkills/MCP verifier files, MACE verifier files, AtomisticSkills scripts, and exclusive tests listed in the File Structure section.
- Modify: `tests/test_answer_extraction.py`
- Modify: `tests/test_public_api.py`
- Test: `tests/test_answer_extraction.py`
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Delete task packs**

Run:

```bash
rm -rf tasks/atomisticskills_smoke tasks/mace_materials tasks/matgl_materials
```

Expected: those directories no longer exist.

- [ ] **Step 2: Delete AtomisticSkills/MCP and MACE implementation files**

Run:

```bash
rm -rf \
  verifiers/atomisticskills_backend.py \
  verifiers/atomisticskills_mcp_shims \
  verifiers/backends/atomisticskills_matgl_properties.py \
  verifiers/backends/mace_properties.py \
  verifiers/materials/atomisticskills_matgl_bandgap.py \
  verifiers/materials/atomisticskills_matgl_formation_energy.py \
  verifiers/materials/atomisticskills_matgl_property_script.py \
  verifiers/materials/mace_energy.py \
  verifiers/materials/mace_property_script.py
```

Expected: those files/directories no longer exist.

- [ ] **Step 3: Delete AtomisticSkills setup and check scripts**

Run:

```bash
rm -f \
  scripts/check_atomisticskills_env.py \
  scripts/check_atomisticskills_matgl_env.py \
  scripts/check_atomisticskills_mace_env.py \
  scripts/setup_atomisticskills_first_batch.sh \
  scripts/setup_atomisticskills_matgl.sh \
  scripts/setup_atomisticskills_mace.sh
```

Expected: those scripts no longer exist.

- [ ] **Step 4: Delete exclusive AtomisticSkills/MACE tests**

Run:

```bash
rm -f \
  tests/test_atomisticskills_adapters.py \
  tests/test_atomisticskills_check_script.py \
  tests/test_atomisticskills_mace_scripts.py \
  tests/test_atomisticskills_matgl_material_tasks.py \
  tests/test_atomisticskills_matgl_properties_backend.py \
  tests/test_atomisticskills_matgl_scripts.py \
  tests/test_atomisticskills_matgl_task_scripts.py \
  tests/test_atomisticskills_setup_script.py \
  tests/test_mace_material_tasks.py \
  tests/test_mace_properties_backend.py \
  tests/test_mace_task_scripts.py
```

Expected: those tests no longer exist.

- [ ] **Step 5: Rewrite answer-extraction example task ids**

In `tests/test_answer_extraction.py`, replace every `atomisticskills_base_supercell_001` with `json_final_answer_example_001`.

Replace every `atomisticskills_xrd_peak_001` with `number_final_answer_example_001`.

No expected assertions should change.

- [ ] **Step 6: Strengthen public API exclusion test**

In `tests/test_public_api.py`, in `test_load_suite_defaults_to_formal_tracks_only`, add:

```python
assert not any(task_id.startswith("atomisticskills_") for task_id in task_ids)
```

Expected: the suite still exposes only formal RDKit/xTB tasks.

- [ ] **Step 7: Run focused non-MCP tests**

Run:

```bash
uv run pytest tests/test_answer_extraction.py tests/test_public_api.py tests/test_matgl_env_script.py tests/test_matgl_properties_backend.py tests/test_matgl_task_scripts.py -q
```

Expected: all selected tests pass.

### Task 3: Remove MCP Dependency And Prototype Packaging

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `tests/test_packaging.py`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Update `pyproject.toml` dependencies and force-includes**

In `pyproject.toml`, remove this dependency line:

```toml
    "mcp>=1.27.2",
```

Remove these wheel force-includes:

```toml
"tasks/atomisticskills_smoke" = "tasks/atomisticskills_smoke"
"tasks/mace_materials" = "tasks/mace_materials"
"tasks/matgl_materials" = "tasks/matgl_materials"
```

Keep:

```toml
"tasks/rdkit_baseline" = "tasks/rdkit_baseline"
"tasks/xtb_xyz/sample_answers.jsonl" = "tasks/xtb_xyz/sample_answers.jsonl"
"tasks/xtb_xyz/tasks.yaml" = "tasks/xtb_xyz/tasks.yaml"
"tasks/xtb_xyz/verifier_specs.yaml" = "tasks/xtb_xyz/verifier_specs.yaml"
```

- [ ] **Step 2: Update packaging tests for removed prototype task packs and MCP dependency**

In `tests/test_packaging.py`, add:

```python
REMOVED_PROTOTYPE_TASK_PACKS = {
    "tasks/atomisticskills_smoke/tasks.yaml",
    "tasks/mace_materials/tasks.yaml",
    "tasks/matgl_materials/tasks.yaml",
}
```

In `test_distribution_artifacts_exclude_private_xtb_calibration_data`, after the existing private calibration assertions, add:

```python
assert REMOVED_PROTOTYPE_TASK_PACKS.isdisjoint(wheel_members)
assert REMOVED_PROTOTYPE_TASK_PACKS.isdisjoint(sdist_members)
```

In `test_wheel_metadata_publishes_matgl_materials_extra_only`, after `requires_dist` is defined, add:

```python
assert not any(requirement.startswith("mcp") for requirement in requires_dist)
```

- [ ] **Step 3: Refresh lockfile**

Run:

```bash
uv lock
```

Expected: `uv.lock` updates and no longer includes `mcp` as a direct project dependency. Transitive packages formerly pulled only by `mcp` may also be removed.

- [ ] **Step 4: Run packaging tests**

Run:

```bash
uv run pytest tests/test_packaging.py -q
```

Expected: packaging tests pass.

### Task 4: Update Current Documentation

**Files:**
- Modify: `docs/design/INITIAL-DESIGN.md`
- Modify: `docs/superpowers/specs/2026-06-29-pipeline-package-framework-design.md`
- Test: documentation reference scans.

- [ ] **Step 1: Update `docs/design/INITIAL-DESIGN.md` current material backend section**

Replace the heading:

```markdown
### 12.3 探索中：MACE、MatGL 与 AtomisticSkills MCP
```

with:

```markdown
### 12.3 材料类 verifier 的当前边界
```

Replace the paragraph and bullets under that heading through the sentence ending with `正式 failure policy。` with:

```markdown
AtomisticSkills MCP、MACE MCP 和 MatGL MCP prototype 已从当前 active codebase 中移除。当前正式发布面仍以 RDKit 与 xTB 为主；材料方向不再保留依赖外部 AtomisticSkills checkout、MCP server 或 agent-specific conda environment 的可执行路径。

保留的材料方向基础是 native MatGL Python backend：`verifiers/backends/matgl_properties.py` 与 `verifiers/materials/matgl_*.py`。这部分用于后续正式 MatGL task specs 的实现基础，但当前不作为内置正式 track 发布，也不复用已删除的 Si-only MCP prototype task pack。

MACE 将在 native Python backend、模型版本冻结、候选材料 domain、资源模型和正式 task design 明确后重新接入。后续材料类正式题目应参考 RDKit 与 xTB 已成型的分层结构，重新完成材料 verifier 的题目设计、domain 设计、资源约束和正式 failure policy。
```

In section 13.1, replace:

```markdown
- 统一 `formal_track`、`experimental_smoke`、`prototype` 等状态标记，避免 MACE/MatGL 这类仍在测试阶段的题目被误认为已完成正式设计。
```

with:

```markdown
- 统一 `formal_track`、`experimental_smoke`、`prototype` 等状态标记，避免未来材料类实验题目被误认为已完成正式设计。
```

In section 13.2, replace:

```markdown
- 明确哪些依赖必须进入镜像，哪些可以是外部可选依赖；xTB、MACE、MatGL、AtomisticSkills 这类外部工具需要有清晰的降级和环境错误报告。
```

with:

```markdown
- 明确哪些依赖必须进入镜像，哪些可以是外部可选依赖；xTB、native MatGL、未来 native MACE 这类本地工具需要有清晰的降级和环境错误报告。
```

In section 13.3, replace:

```markdown
- 重新设计 MACE 与 MatGL 正式任务，而不是只沿用当前 Si-only prototype。需要确定候选材料空间、结构大小、允许元素、晶胞 sanity、去重规则和 domain gate。
```

with:

```markdown
- 重新设计 MACE 与 MatGL 正式任务，不沿用已移除的 Si-only MCP prototype。需要确定候选材料空间、结构大小、允许元素、晶胞 sanity、去重规则和 domain gate。
```

Remove these bullets from section 13.3:

```markdown
- 评估 AtomisticSkills MCP 是否作为正式 verifier 后端进入官方 image，或仅作为本地实验/适配层保留。
- 如果继续使用 MCP，需要固定 server 配置发现机制、conda/env 依赖策略、stdio timeout、JSON payload unwrap 规则和工具版本记录。
```

- [ ] **Step 2: Update pipeline package framework spec references**

In `docs/superpowers/specs/2026-06-29-pipeline-package-framework-design.md`, replace this non-goal:

```markdown
- 不把 `matgl_materials`、`mace_materials` 或 `atomisticskills_smoke` 暴露为默认正式 track。
```

with:

```markdown
- 不重新引入已移除的 `matgl_materials`、`mace_materials` 或 `atomisticskills_smoke` prototype task packs。
```

Replace this test description:

```markdown
- `vgb.load_suite()` 默认包含 rdkit/xtb，不包含 matgl/mace/atomisticskills。
```

with:

```markdown
- `vgb.load_suite()` 默认包含 rdkit/xtb，不包含 matgl/mace/atomisticskills prototype tasks。
```

- [ ] **Step 3: Run documentation scans**

Run:

```bash
rg -n "tasks/(atomisticskills_smoke|mace_materials|matgl_materials)|atomisticskills_mcp|mace-agent|matgl-agent|base-agent|drugdisc-agent|xrd-agent" docs/design docs/superpowers/specs
```

Expected: no current design/spec references that describe the deleted paths as active. Historical mentions in old implementation plans may remain only if clearly historical; do not edit `docs/research/`.

### Task 5: Final Acceptance Verification And Commit

**Files:**
- All files changed by Tasks 1-4.
- Test: full repository test suite and acceptance scans.

- [ ] **Step 1: Run active-code AtomisticSkills scan**

Run:

```bash
rg -n "AtomisticSkills|atomisticskills|atomisticskills_mcp|mace-agent|matgl-agent|base-agent|drugdisc-agent|xrd-agent" verifiers scripts tests tasks pyproject.toml
```

Expected: no output.

- [ ] **Step 2: Run active-code MCP scan**

Run:

```bash
rg -n "\bmcp\b" pyproject.toml verifiers scripts tests tasks
```

Expected: no output.

- [ ] **Step 3: Check lockfile consistency**

Run:

```bash
uv lock --check
```

Expected: succeeds with no lockfile updates required.

- [ ] **Step 4: Run full tests**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 5: Inspect git diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: only files listed in this plan changed or deleted.

- [ ] **Step 6: Commit cleanup**

Run:

```bash
git add -A
git commit -m "refactor: remove AtomisticSkills MCP prototype path"
```

Expected: commit succeeds after tests pass.
