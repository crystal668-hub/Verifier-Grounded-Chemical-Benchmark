# xTB Real-Dataset Property Distribution Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible real-dataset distribution analysis workflow for xTB task properties so task thresholds are grounded in common chemical-world value ranges rather than only curated candidates.

**Architecture:** Add dataset-source manifests, deterministic sampling scripts, domain-filtered XYZ export, tiered xTB batch runners, distribution analyzers, and a dated research report. Keep official task thresholds unchanged in this plan; produce distribution evidence and threshold recommendations for a later threshold-update plan.

**Tech Stack:** Python 3.12, pytest, PyYAML, JSONL/CSV/JSON artifacts, RDKit for structure filters and stratification, existing xTB verifier backend, local xTB CLI for computed distributions, optional dataset downloads/caches outside committed source.

---

## Scope

This plan investigates value distributions for xTB direct-XYZ task properties across real or widely used molecular datasets. It covers all current xTB tasks:

- `xtb_gap_window_001`
- `xtb_dipole_window_002`
- `xtb_gap_max_003`
- `xtb_gap_min_004`
- `xtb_dipole_max_005`
- `xtb_low_gap_high_dipole_opt_006`
- `xtb_gap_dipole_window_007`
- `xtb_lumo_min_008`
- `xtb_polarizability_dipole_opt_009`
- `xtb_solvation_selectivity_alpb_010`
- `xtb_electrophilicity_max_011`
- `xtb_fukui_carbon_site_012`
- `xtb_hessian_thermo_stability_013`

It analyzes distributions for these computed properties:

- `homo_lumo_gap`
- `dipole_moment`
- `lumo_energy`
- `polarizability_per_heavy_atom`
- `alpb_water_hexane_selectivity`
- `global_electrophilicity`
- `max_f_plus_on_carbon`
- `f_plus_contrast`
- `imaginary_frequency_count`
- `entropy_298_per_heavy_atom`
- `relaxation_energy`

This plan does not add new benchmark tasks, change scoring thresholds, or make dataset labels a runtime oracle. Dataset records are offline calibration inputs only.

## Dataset Sources

Use four dataset families. Each source is included for a different chemical-world slice.

| Dataset | Required use | Target sample role | Why it matters | Notes |
| --- | --- | --- | --- | --- |
| QM9 | Required | small organic baseline | 133k small CHONF molecules with quantum-property precedent | Good for gap/dipole/LUMO/polarizability/hessian pilot; limited chemistry. |
| QMugs | Required | drug-like ChEMBL space | 665k+ drug-like molecules and conformers with xTB/DFT precedent | Best source for task 8-13 drug-like distributions. |
| GEOM-Drugs | Required for conformer/geometry subset | flexible conformer space | large conformer ensemble for drug-like molecules | Use only selected low-energy conformers; dataset is too large for exhaustive xTB. |
| Tartarus/OPV or equivalent OPV subset | Required if accessible, otherwise documented skip | organic electronics/materials-biased space | xTB/CREST-based molecular design benchmark includes frontier orbital objectives | Useful for low-gap, LUMO, dipole, polarizability extremes. |

If Tartarus/OPV cannot be fetched reproducibly, the plan should still run with QM9, QMugs, and GEOM-Drugs, and the final report must mark OPV coverage as `not_available`.

## Dataset Provenance Manifest

Create a versioned manifest. Do not commit downloaded raw datasets unless they are small and explicitly license-compatible.

**File:** `data/xtb_real_dataset_sources.yaml`

```yaml
version: 1
sources:
  qm9:
    status: required
    source_type: public_dataset
    preferred_format: xyz_or_sdf_with_3d
    url: "https://www.nature.com/articles/sdata201422"
    cache_path: ".cache/xtb_real_datasets/qm9"
    license_note: "Use only for offline calibration; do not redistribute raw records unless license permits."
  qmugs:
    status: required
    source_type: public_dataset
    preferred_format: sdf_or_xyz_conformers
    url: "https://www.nature.com/articles/s41597-022-01390-7"
    cache_path: ".cache/xtb_real_datasets/qmugs"
    license_note: "Use only for offline calibration; do not redistribute raw records unless license permits."
  geom_drugs:
    status: required_for_conformer_subset
    source_type: public_dataset
    preferred_format: conformer_records
    url: "https://www.nature.com/articles/s41597-022-01288-4"
    cache_path: ".cache/xtb_real_datasets/geom_drugs"
    license_note: "Use only sampled derived manifests in git."
  tartarus_opv:
    status: optional_if_unavailable
    source_type: benchmark_dataset
    preferred_format: smiles_plus_generated_geometry
    url: "https://papers.neurips.cc/paper_files/paper/2023/file/09f8b2469a3d1089a7c60d9ef1983271-Paper-Datasets_and_Benchmarks.pdf"
    cache_path: ".cache/xtb_real_datasets/tartarus_opv"
    license_note: "Record exact source and availability in final report."
```

## Domain Filter

Only records matching the current xTB direct-XYZ formal domain enter distribution runs:

```yaml
domain:
  format: xyz
  charge: 0
  multiplicity: 1
  allowed_elements: [H, C, N, O, F, P, S, Cl, Br]
  atom_count: [3, 80]
  heavy_atom_count: [1, 40]
  coordinate_units: angstrom
  max_absolute_coordinate: 30.0
  min_interatomic_distance: 0.45
  inferred_components: 1
  require_explicit_hydrogens: true
```

For hessian distribution runs, apply the stricter hessian domain:

```yaml
hessian_domain:
  atom_count: [6, 48]
  heavy_atom_count: [4, 18]
```

Do not generate conformers from SMILES for final calibration records unless the source dataset lacks 3D coordinates and the report explicitly labels the subset as `generated_geometry`. Prefer dataset-provided 3D conformers.

## Sampling Strategy

Use deterministic, stratified sampling. Every script must accept `--seed`, defaulting to `20260615`.

### Stratification Fields

Compute these fields before sampling:

- `dataset_name`
- `record_id`
- `formula`
- `atom_count`
- `heavy_atom_count`
- `carbon_count`
- `hetero_atom_count`
- `heavy_element_diversity`
- `contains_halogen`
- `contains_phosphorus_or_sulfur`
- `estimated_flexibility_bin`
- `geometry_source`

Use bins:

```yaml
heavy_atom_bins:
  small: [1, 8]
  medium: [9, 18]
  large: [19, 40]
hetero_atom_bins:
  low: [0, 1]
  medium: [2, 4]
  high: [5, 40]
flexibility_bins:
  low: [0, 2]
  medium: [3, 6]
  high: [7, 80]
```

`estimated_flexibility_bin` can be computed with RDKit rotatable-bond count when bond perception is available. If bond perception is not reliable for a source, set it to `unknown` and record that in the manifest.

### Sample Size Targets

Run in two phases: pilot and expanded.

| Property tier | Properties | Pilot sample size | Expanded sample size | Dataset coverage |
| --- | --- | ---: | ---: | --- |
| light | `homo_lumo_gap`, `dipole_moment`, `lumo_energy`, `polarizability_per_heavy_atom`, `relaxation_energy` | 1,000-3,000 total | 10,000-30,000 total | QM9 + QMugs + GEOM + OPV if available |
| medium | `alpb_water_hexane_selectivity`, `global_electrophilicity`, `max_f_plus_on_carbon`, `f_plus_contrast` | 300-1,000 total | 2,000-5,000 total | QMugs + GEOM + OPV; QM9 optional |
| expensive | `imaginary_frequency_count`, `entropy_298_per_heavy_atom` | 100-300 total | 500-1,000 total | QM9 + QMugs small/medium hessian-domain subset |

Minimum pilot quotas:

| Dataset | Light pilot | Medium pilot | Expensive pilot |
| --- | ---: | ---: | ---: |
| QM9 | 500 | 100 | 75 |
| QMugs | 1,000 | 300 | 150 |
| GEOM-Drugs | 500 | 200 | 75 |
| Tartarus/OPV | 250 if available | 100 if available | 0 unless small molecules pass hessian domain |

If a dataset has fewer eligible records than its quota after domain filtering, include all eligible records and record `quota_underfilled` in the sample manifest.

## Distribution Outputs

The real-dataset run must produce:

```text
artifacts/xtb_real_distribution/YYYY-MM-DD/
  source_manifest.resolved.yaml
  filtered_records.jsonl
  sampled_records.jsonl
  light_results.json
  medium_results.json
  expensive_results.json
  analysis/
    property_distribution_summary.json
    property_distribution_summary.csv
    property_distribution_summary.md
    per_dataset_quantiles.csv
    failure_summary.csv
    score_threshold_recommendations.md
```

Do not commit generated `artifacts/` files by default. Commit only scripts, tests, manifests, and the final human-readable report under `docs/research/`.

## Quantile Requirements

For every property and dataset slice, compute:

- count
- ok count
- error count
- error rate
- min
- p1
- p5
- p10
- p25
- p50
- p75
- p90
- p95
- p99
- max
- mean
- standard deviation

Also compute task scoring diagnostics:

- fraction with task score `>= 0.2`
- fraction with task score `>= 0.5`
- fraction with task score `>= 0.8`
- fraction with task score `>= 0.95`
- fraction failing `relaxation_energy` gate
- fraction failing hessian `stability_gate`, for hessian subset

## Threshold Recommendation Rules

The analysis report should assign one recommendation per task:

| Recommendation | Rule of thumb |
| --- | --- |
| `keep_thresholds` | Current high-score fraction is in a useful challenge range and positive controls remain reachable. |
| `tighten_thresholds` | More than 5% of broad real-dataset records score `>= 0.8`, or curated/real near-miss candidates saturate. |
| `loosen_thresholds` | Fewer than 0.1% of real records score `>= 0.5` and curated positives also struggle. |
| `split_by_domain` | QM9-like and QMugs/GEOM-like distributions differ enough that one threshold conflates small-molecule and drug-like regimes. |
| `needs_more_data` | Sample size or success rate is too low for a credible quantile. |
| `needs_parser_or_runtime_fix` | Parser/tool/timeout failures exceed 5% in a property tier after domain filtering. |

Use these defaults unless the report justifies a different rule.

## Task 1: Dataset Source Manifest and Schema Tests

**Files:**
- Create: `data/xtb_real_dataset_sources.yaml`
- Create: `tests/test_xtb_real_dataset_distribution_inputs.py`

- [ ] **Step 1: Write manifest schema tests**

Create `tests/test_xtb_real_dataset_distribution_inputs.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data" / "xtb_real_dataset_sources.yaml"


def test_xtb_real_dataset_source_manifest_exists() -> None:
    assert SOURCE_MANIFEST.exists()


def test_xtb_real_dataset_source_manifest_defines_required_sources() -> None:
    with SOURCE_MANIFEST.open() as handle:
        payload = yaml.safe_load(handle)

    assert payload["version"] == 1
    sources = payload["sources"]
    assert {"qm9", "qmugs", "geom_drugs", "tartarus_opv"}.issubset(sources)
    assert sources["qm9"]["status"] == "required"
    assert sources["qmugs"]["status"] == "required"
    assert sources["geom_drugs"]["status"] == "required_for_conformer_subset"
    assert sources["tartarus_opv"]["status"] == "optional_if_unavailable"
    for source in sources.values():
        assert source["url"].startswith("https://")
        assert source["cache_path"].startswith(".cache/xtb_real_datasets/")
        assert "license_note" in source
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_inputs.py -q
```

Expected: FAIL because `data/xtb_real_dataset_sources.yaml` does not exist.

- [ ] **Step 3: Add the source manifest**

Create `data/xtb_real_dataset_sources.yaml` using the manifest shown in the "Dataset Provenance Manifest" section.

- [ ] **Step 4: Run the manifest tests**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add data/xtb_real_dataset_sources.yaml tests/test_xtb_real_dataset_distribution_inputs.py
git commit -m "test: add xtb real dataset source manifest"
```

## Task 2: Dataset Preparation and Sampling CLI

**Files:**
- Create: `scripts/prepare_xtb_real_dataset_sample.py`
- Modify: `tests/test_xtb_real_dataset_distribution_inputs.py`

- [ ] **Step 1: Add failing CLI and deterministic sampling tests**

Append these tests:

```python
import json
import subprocess
import sys


def test_prepare_xtb_real_dataset_sample_help() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/prepare_xtb_real_dataset_sample.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--source-manifest" in completed.stdout
    assert "--output-dir" in completed.stdout
    assert "--seed" in completed.stdout
    assert "--pilot" in completed.stdout


def test_prepare_xtb_real_dataset_sample_can_process_tiny_fixture(tmp_path) -> None:
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "dataset_name": "unit_fixture",
                        "record_id": "water",
                        "xyz": "3\nwater\nO 0 0 0\nH 0.758602 0 0.504284\nH -0.758602 0 0.504284\n",
                        "charge": 0,
                        "multiplicity": 1,
                        "geometry_source": "fixture_xyz",
                    }
                ),
                json.dumps(
                    {
                        "dataset_name": "unit_fixture",
                        "record_id": "methanol",
                        "xyz": "6\nmethanol\nC 0 0 0\nO 1.43 0 0\nH -0.36 1.02 0\nH -0.36 -0.51 0.883346\nH -0.36 -0.51 -0.883346\nH 1.75 0 0.9\n",
                        "charge": 0,
                        "multiplicity": 1,
                        "geometry_source": "fixture_xyz",
                    }
                ),
            ]
        )
        + "\n"
    )
    output_dir = tmp_path / "out"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_xtb_real_dataset_sample.py",
            "--input-jsonl",
            str(fixture),
            "--output-dir",
            str(output_dir),
            "--seed",
            "123",
            "--pilot",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    sampled = [json.loads(line) for line in (output_dir / "sampled_records.jsonl").read_text().splitlines()]
    assert [row["record_id"] for row in sampled] == ["water", "methanol"]
    assert sampled[0]["dataset_name"] == "unit_fixture"
    assert "heavy_atom_count" in sampled[0]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_inputs.py -q
```

Expected: FAIL because `scripts/prepare_xtb_real_dataset_sample.py` does not exist.

- [ ] **Step 3: Implement minimal preparation CLI**

Implement `scripts/prepare_xtb_real_dataset_sample.py` with:

- `--source-manifest`
- `--input-jsonl`
- `--output-dir`
- `--seed`
- `--pilot`
- `--expanded`

The first implementation only needs to support `--input-jsonl` fixture records. It should:

1. parse XYZ;
2. compute domain fields;
3. filter by current xTB domain;
4. write `filtered_records.jsonl`;
5. deterministically sort and sample records;
6. write `sampled_records.jsonl`;
7. write `sample_manifest.json`.

Use existing `verifiers.backends.xtb_properties.parse_xyz`, `inspect_xyz`, and `check_domain` to avoid duplicate domain logic.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/prepare_xtb_real_dataset_sample.py tests/test_xtb_real_dataset_distribution_inputs.py
git commit -m "feat: prepare xtb real dataset samples"
```

## Task 3: Real-Dataset xTB Distribution Runner

**Files:**
- Create: `scripts/run_xtb_real_dataset_distribution.py`
- Create: `tests/test_xtb_real_dataset_distribution_scripts.py`

- [ ] **Step 1: Write failing runner tests**

Create `tests/test_xtb_real_dataset_distribution_scripts.py`:

```python
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_xtb_real_dataset_distribution_help() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_xtb_real_dataset_distribution.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--sampled-records" in completed.stdout
    assert "--tier" in completed.stdout
    assert "--output" in completed.stdout


def test_run_xtb_real_dataset_distribution_reports_missing_xtb(tmp_path) -> None:
    sampled = tmp_path / "sampled_records.jsonl"
    sampled.write_text(
        json.dumps(
            {
                "dataset_name": "unit_fixture",
                "record_id": "water",
                "xyz": "3\nwater\nO 0 0 0\nH 0.758602 0 0.504284\nH -0.758602 0 0.504284\n",
            }
        )
        + "\n"
    )
    env = {**os.environ, "PATH": str(tmp_path)}

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xtb_real_dataset_distribution.py",
            "--sampled-records",
            str(sampled),
            "--tier",
            "light",
            "--output",
            str(tmp_path / "results.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_scripts.py -q
```

Expected: FAIL because `scripts/run_xtb_real_dataset_distribution.py` does not exist.

- [ ] **Step 3: Implement the distribution runner**

Create `scripts/run_xtb_real_dataset_distribution.py` with CLI:

```text
--sampled-records PATH
--tier {light,medium,expensive}
--output PATH
--max-records INT
```

Tier mapping:

```yaml
light:
  properties:
    - homo_lumo_gap
    - dipole_moment
    - lumo_energy
    - polarizability_per_heavy_atom
    - relaxation_energy
medium:
  properties:
    - alpb_water_hexane_selectivity
    - global_electrophilicity
    - max_f_plus_on_carbon
    - f_plus_contrast
expensive:
  properties:
    - imaginary_frequency_count
    - entropy_298_per_heavy_atom
```

The runner should reuse `benchmark.evaluate.evaluate_one` by constructing temporary answer records for a hidden calibration task per property. Do not add these hidden tasks to `tasks/xtb_xyz/tasks.yaml`; define them in the script or a helper module so official benchmark tasks stay unchanged.

Record per-row output:

- `dataset_name`
- `record_id`
- `tier`
- `status`
- `failure_type`
- `runtime_seconds`
- `properties`
- `versions`

- [ ] **Step 4: Run runner tests**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_scripts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/run_xtb_real_dataset_distribution.py tests/test_xtb_real_dataset_distribution_scripts.py
git commit -m "feat: run xtb real dataset distributions"
```

## Task 4: Distribution Analyzer

**Files:**
- Create: `scripts/analyze_xtb_real_dataset_distribution.py`
- Modify: `tests/test_xtb_real_dataset_distribution_scripts.py`

- [ ] **Step 1: Add failing analyzer tests**

Append:

```python
def test_analyze_xtb_real_dataset_distribution_outputs_quantiles(tmp_path) -> None:
    results = tmp_path / "light_results.json"
    output_dir = tmp_path / "analysis"
    results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "light",
                "rows": [
                    {
                        "dataset_name": "qm9",
                        "record_id": "a",
                        "status": "ok",
                        "failure_type": None,
                        "properties": {"homo_lumo_gap": 5.0, "dipole_moment": 1.0},
                    },
                    {
                        "dataset_name": "qm9",
                        "record_id": "b",
                        "status": "ok",
                        "failure_type": None,
                        "properties": {"homo_lumo_gap": 7.0, "dipole_moment": 3.0},
                    },
                    {
                        "dataset_name": "qmugs",
                        "record_id": "c",
                        "status": "error",
                        "failure_type": "verifier_timeout",
                        "properties": {},
                    },
                ],
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_xtb_real_dataset_distribution.py",
            "--inputs",
            str(results),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    summary = json.loads((output_dir / "property_distribution_summary.json").read_text())
    assert "homo_lumo_gap" in summary["properties"]
    assert summary["properties"]["homo_lumo_gap"]["all"]["count"] == 2
    assert summary["properties"]["homo_lumo_gap"]["all"]["p50"] == 6.0
    assert (output_dir / "property_distribution_summary.md").exists()
    assert (output_dir / "failure_summary.csv").exists()
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_scripts.py::test_analyze_xtb_real_dataset_distribution_outputs_quantiles -q
```

Expected: FAIL because analyzer script does not exist.

- [ ] **Step 3: Implement analyzer**

Create `scripts/analyze_xtb_real_dataset_distribution.py` with:

- `--inputs` accepting one or more result JSON files;
- `--output-dir`;
- quantile computation for required percentiles;
- per-dataset and all-dataset summaries;
- failure summary by `failure_type`;
- markdown report table.

Do not require pandas; use only standard library to keep dependencies stable.

- [ ] **Step 4: Run analyzer tests**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_scripts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/analyze_xtb_real_dataset_distribution.py tests/test_xtb_real_dataset_distribution_scripts.py
git commit -m "feat: analyze xtb real dataset distributions"
```

## Task 5: Pilot Run Protocol

**Files:**
- Create: `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md`

- [ ] **Step 1: Resolve data availability**

Run dataset fetch/preparation outside git-controlled raw data paths. Use `.cache/xtb_real_datasets/`.

Required decision table in the report:

| Dataset | Status | Records available | Eligible after domain filter | Notes |
| --- | --- | ---: | ---: | --- |
| QM9 | available/unavailable | number | number | note |
| QMugs | available/unavailable | number | number | note |
| GEOM-Drugs | available/unavailable | number | number | note |
| Tartarus/OPV | available/unavailable | number | number | note |

- [ ] **Step 2: Prepare pilot sample**

Run:

```bash
uv run python scripts/prepare_xtb_real_dataset_sample.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --output-dir artifacts/xtb_real_distribution/2026-06-15 \
  --seed 20260615 \
  --pilot
```

Expected:

- `filtered_records.jsonl`
- `sampled_records.jsonl`
- `sample_manifest.json`

If a source requires manual download, first convert it to the normalized fixture format and pass `--input-jsonl` for that source. Record manual steps in the report.

- [ ] **Step 3: Run light tier**

Run:

```bash
uv run python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-15/sampled_records.jsonl \
  --tier light \
  --output artifacts/xtb_real_distribution/2026-06-15/light_results.json
```

Expected: output JSON with property rows and failure summary.

- [ ] **Step 4: Run medium tier**

Run:

```bash
uv run python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-15/sampled_records.jsonl \
  --tier medium \
  --output artifacts/xtb_real_distribution/2026-06-15/medium_results.json
```

Expected: output JSON with medium-tier property rows.

- [ ] **Step 5: Run expensive tier on hessian-domain subset**

Run:

```bash
uv run python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-15/sampled_records.jsonl \
  --tier expensive \
  --max-records 300 \
  --output artifacts/xtb_real_distribution/2026-06-15/expensive_results.json
```

Expected: output JSON with hessian rows. If runtime is too high, lower `--max-records` to 100 and record that decision.

- [ ] **Step 6: Analyze pilot results**

Run:

```bash
uv run python scripts/analyze_xtb_real_dataset_distribution.py \
  --inputs \
    artifacts/xtb_real_distribution/2026-06-15/light_results.json \
    artifacts/xtb_real_distribution/2026-06-15/medium_results.json \
    artifacts/xtb_real_distribution/2026-06-15/expensive_results.json \
  --output-dir artifacts/xtb_real_distribution/2026-06-15/analysis
```

Expected:

- `property_distribution_summary.json`
- `property_distribution_summary.csv`
- `property_distribution_summary.md`
- `per_dataset_quantiles.csv`
- `failure_summary.csv`
- `score_threshold_recommendations.md`

- [ ] **Step 7: Write research report**

Create `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md` with:

```markdown
# xTB Real-Dataset Property Distributions

## Environment

## Dataset Availability

## Sampling Method

## Domain Filter Results

## Property Distribution Summary

## Per-Task Threshold Implications

## Failure and Runtime Analysis

## Recommended Threshold Follow-Ups

## Limitations
```

Every task must end with one of:

- `keep_thresholds`
- `tighten_thresholds`
- `loosen_thresholds`
- `split_by_domain`
- `needs_more_data`
- `needs_parser_or_runtime_fix`

- [ ] **Step 8: Commit report**

Run:

```bash
git add docs/research/2026-06-15-xtb-real-dataset-property-distributions.md
git commit -m "docs: report xtb real dataset property distributions"
```

## Task 6: Expanded Run Decision

**Files:**
- Modify: `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md`

- [ ] **Step 1: Decide expanded sample sizes**

Based on pilot failure rates and runtimes, choose expanded sizes within:

- light: 10,000-30,000 records
- medium: 2,000-5,000 records
- expensive: 500-1,000 records

Record exact selected counts and why.

- [ ] **Step 2: Run expanded sampling**

Run:

```bash
uv run python scripts/prepare_xtb_real_dataset_sample.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --output-dir artifacts/xtb_real_distribution/2026-06-15-expanded \
  --seed 20260615 \
  --expanded
```

- [ ] **Step 3: Run expanded tiers**

Run the same three tier commands against `artifacts/xtb_real_distribution/2026-06-15-expanded/sampled_records.jsonl`.

- [ ] **Step 4: Analyze expanded outputs**

Run analyzer against expanded tier result JSON files and write outputs to `artifacts/xtb_real_distribution/2026-06-15-expanded/analysis`.

- [ ] **Step 5: Update report with expanded results**

Add an "Expanded Run" section to `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md` comparing pilot and expanded conclusions.

- [ ] **Step 6: Commit report update**

Run:

```bash
git add docs/research/2026-06-15-xtb-real-dataset-property-distributions.md
git commit -m "docs: update xtb distribution report with expanded run"
```

## Task 7: Full Verification

**Files:**
- Read-only verification.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
uv run pytest \
  tests/test_xtb_real_dataset_distribution_inputs.py \
  tests/test_xtb_real_dataset_distribution_scripts.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: PASS.

- [ ] **Step 3: Check generated artifacts are not staged**

Run:

```bash
git status --short
```

Expected: no generated `artifacts/xtb_real_distribution/` files are staged.

## Self-Review

- Spec coverage: This plan covers real dataset sources, domain filtering, stratified sampling, pilot and expanded sample sizes, xTB property tiers, distribution statistics, threshold recommendations, reports, and tests.
- Completeness scan: Every task has concrete files, commands, and expected outputs.
- Type consistency: Property names match `tasks/xtb_xyz/verifier_specs.yaml`; task IDs match `tasks/xtb_xyz/tasks.yaml`.
- Scope check: This plan produces distribution evidence only; threshold changes are intentionally deferred to a separate follow-up plan.
