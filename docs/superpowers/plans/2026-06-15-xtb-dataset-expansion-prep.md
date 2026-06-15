# xTB Dataset Expansion Prep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible preparation layer needed to add bounded non-QM9 dataset coverage and run an intermediate xTB calibration before any full Expanded Run.

**Architecture:** Keep raw datasets outside git, inspect source availability from `data/xtb_real_dataset_sources.yaml`, convert bounded 3D records into the existing normalized JSONL schema, prepare tier-aware mixed samples, run a controlled intermediate calibration, and update the research report with an explicit Expanded Run readiness decision. The full Expanded Run remains blocked until at least one non-QM9 3D source is normalized, sampled, and successfully processed through xTB.

**Tech Stack:** Python 3.12, pytest, PyYAML, RDKit, JSONL/CSV/JSON artifacts, existing xTB verifier backend, local xTB CLI, ignored `.cache/` and `artifacts/` directories.

---

## Scope

This plan implements the next executable phase after the 2026-06-15 smoke rerun and dataset-access repair. It is a Dataset Expansion Prep phase, not the final Expanded Run.

The plan must answer four questions with evidence:

1. Can QMugs structures be accessed or manually cached and converted into normalized 3D JSONL records with bounded memory and disk use?
2. Can GEOM metadata and a small validation archive be accessed reproducibly, and can any usable SDF-like 3D records be normalized?
3. Can a mixed QM9 plus non-QM9 sample run through light, medium, and expensive xTB tiers at intermediate sizes without parser/runtime failures dominating the data?
4. Is the project ready for the formal Expanded Run, or does it need another access/runtime repair pass?

Do not change task thresholds in this plan. Do not add new benchmark tasks. Do not commit raw downloaded datasets or generated `artifacts/` outputs.

## Current Decision

Formal Expanded Run is not ready because the latest report only ran 60 QM9 records through xTB. Dataset Expansion Prep is ready because the smoke workflow is clean, property-level status accounting is fixed, and machine-readable access metadata now exists for QMugs and GEOM.

The execution target for this plan is an intermediate calibration:

| Tier | Target records | Required source coverage |
| --- | ---: | --- |
| light | 500-1000 | QM9 plus at least one non-QM9 normalized 3D source |
| medium | 200-500 | Carbon-containing subset from QM9 plus at least one non-QM9 source |
| expensive | 100-200 | Hessian-domain-aware subset; include non-QM9 if eligible records exist |

Proceed to the formal Expanded Run only after this plan produces:

- At least one non-QM9 normalized JSONL file with 100 or more domain-eligible records, or a documented proof that the source has fewer eligible records.
- Intermediate light and medium tier runs with property-level error rates at or below 5% for attempted properties, excluding intentional `domain_skip`.
- An expensive-tier run with no systematic hessian parser/runtime failure. Chemistry failures such as nonzero imaginary frequencies are distribution signal, not runtime failure.
- An updated `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md` readiness section.

## Files

Create:

- `scripts/inspect_xtb_real_dataset_availability.py`: reads `data/xtb_real_dataset_sources.yaml`, checks local cache files and optional remote metadata, writes a compact availability report.
- `tests/test_xtb_real_dataset_availability.py`: unit tests for manifest parsing, local-cache status reporting, and no-network default behavior.

Modify:

- `scripts/convert_xtb_real_dataset_sdf.py`: add bounded tar member extraction, optional member filtering, and explicit summary fields for large archive conversion.
- `scripts/prepare_xtb_real_dataset_sample.py`: add intermediate mode quotas and tier-aware output files for light, medium, and expensive samples.
- `scripts/analyze_xtb_real_dataset_distribution.py`: emit an Expanded Run readiness JSON/Markdown decision based on source coverage, counts, and property-level errors.
- `tests/test_xtb_real_dataset_distribution_inputs.py`: cover new manifest availability expectations and intermediate sampling behavior.
- `tests/test_xtb_real_dataset_distribution_scripts.py`: cover readiness analysis.
- `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md`: append Dataset Expansion Prep results and the final readiness judgment after running the intermediate calibration.

Generated but not committed by default:

- `.cache/xtb_real_datasets/qmugs/structures.tar.gz`
- `.cache/xtb_real_datasets/qmugs/qmugs_bounded.jsonl`
- `.cache/xtb_real_datasets/geom_drugs/censo.tar.gz`
- `.cache/xtb_real_datasets/geom_drugs/geom_validation.jsonl`
- `artifacts/xtb_real_distribution/2026-06-15-expansion-prep/`

## Task 1: Add Dataset Availability Inspector

**Files:**

- Create: `scripts/inspect_xtb_real_dataset_availability.py`
- Create: `tests/test_xtb_real_dataset_availability.py`

- [ ] **Step 1: Write failing tests for no-network local availability**

Add `tests/test_xtb_real_dataset_availability.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_inspect_xtb_real_dataset_availability_help() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/inspect_xtb_real_dataset_availability.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--source-manifest" in completed.stdout
    assert "--output-json" in completed.stdout
    assert "--check-remote" in completed.stdout


def test_inspect_xtb_real_dataset_availability_reports_missing_cache(tmp_path) -> None:
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "sources": {
                    "qmugs": {
                        "status": "required",
                        "cache_path": str(tmp_path / "missing_qmugs"),
                        "access": {
                            "type": "nextcloud_public_webdav",
                            "files": {
                                "structures.tar.gz": "https://example.invalid/structures.tar.gz",
                            },
                            "conversion": "scripts/convert_xtb_real_dataset_sdf.py",
                        },
                    },
                    "tartarus_opv": {
                        "status": "optional_if_unavailable",
                        "cache_path": str(tmp_path / "opv"),
                        "access": {"status": "manual_or_generated_geometry_required"},
                    },
                },
            },
            sort_keys=True,
        )
    )
    output = tmp_path / "availability.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_xtb_real_dataset_availability.py",
            "--source-manifest",
            str(manifest),
            "--output-json",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(output.read_text())
    assert payload["status"] == "ok"
    assert payload["remote_checked"] is False
    assert payload["sources"]["qmugs"]["local_files"]["structures.tar.gz"]["exists"] is False
    assert payload["sources"]["qmugs"]["conversion"] == "scripts/convert_xtb_real_dataset_sdf.py"
    assert payload["sources"]["tartarus_opv"]["access_status"] == "manual_or_generated_geometry_required"


def test_inspect_xtb_real_dataset_availability_reports_existing_cache(tmp_path) -> None:
    cache = tmp_path / "qmugs"
    cache.mkdir()
    cached_file = cache / "structures.tar.gz"
    cached_file.write_bytes(b"unit")
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "sources": {
                    "qmugs": {
                        "status": "required",
                        "cache_path": str(cache),
                        "access": {
                            "type": "nextcloud_public_webdav",
                            "files": {
                                "structures.tar.gz": "https://example.invalid/structures.tar.gz",
                            },
                        },
                    },
                },
            },
            sort_keys=True,
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_xtb_real_dataset_availability.py",
            "--source-manifest",
            str(manifest),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    cached = payload["sources"]["qmugs"]["local_files"]["structures.tar.gz"]
    assert cached["exists"] is True
    assert cached["size_bytes"] == 4
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_availability.py -q
```

Expected: FAIL because `scripts/inspect_xtb_real_dataset_availability.py` does not exist.

- [ ] **Step 3: Implement the availability inspector**

Create `scripts/inspect_xtb_real_dataset_availability.py`:

```python
#!/usr/bin/env python
"""Inspect local and optional remote availability for xTB real datasets."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "xtb_real_dataset_sources.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--check-remote", action="store_true")
    parser.add_argument("--remote-timeout", type=float, default=10.0)
    return parser.parse_args()


def cache_path_for(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


def local_file_status(cache_path: Path, files: dict[str, str]) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for file_name in sorted(files):
        path = cache_path / file_name
        statuses[file_name] = {
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
    return statuses


def remote_head(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "status": "ok",
                "http_status": response.status,
                "content_length": response.headers.get("Content-Length"),
            }
    except Exception as exc:  # noqa: BLE001 - diagnostics must preserve access failures.
        return {"status": "error", "message": str(exc)}


def inspect_manifest(manifest_path: Path, *, check_remote: bool, remote_timeout: float) -> dict[str, Any]:
    with manifest_path.open() as handle:
        manifest = yaml.safe_load(handle)

    sources: dict[str, Any] = {}
    for source_name, source in sorted((manifest.get("sources") or {}).items()):
        access = source.get("access") or {}
        files = access.get("files") or {}
        cache_path = cache_path_for(str(source.get("cache_path", "")))
        source_status: dict[str, Any] = {
            "status": source.get("status"),
            "cache_path": str(cache_path),
            "access_type": access.get("type"),
            "access_status": access.get("status"),
            "conversion": access.get("conversion"),
            "local_files": local_file_status(cache_path, files),
        }
        if check_remote:
            source_status["remote_files"] = {
                file_name: remote_head(url, remote_timeout)
                for file_name, url in sorted(files.items())
            }
        sources[source_name] = source_status

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(manifest_path),
        "remote_checked": check_remote,
        "sources": sources,
    }


def main() -> int:
    args = parse_args()
    payload = inspect_manifest(args.source_manifest, check_remote=args.check_remote, remote_timeout=args.remote_timeout)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests for the inspector**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_availability.py -q
```

Expected: PASS with 3 tests passing.

- [ ] **Step 5: Run the inspector against the real manifest**

Run:

```bash
uv run python scripts/inspect_xtb_real_dataset_availability.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --output-json artifacts/xtb_real_distribution/2026-06-15-expansion-prep/source_availability.local.json
```

Expected: JSON with `status: ok`, `remote_checked: false`, local cache file status for QM9/QMugs/GEOM, and `manual_or_generated_geometry_required` for Tartarus/OPV.

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/inspect_xtb_real_dataset_availability.py tests/test_xtb_real_dataset_availability.py
git commit -m "feat: inspect xtb dataset availability"
```

## Task 2: Harden SDF Archive Conversion for Large Dataset Prep

**Files:**

- Modify: `scripts/convert_xtb_real_dataset_sdf.py`
- Modify: `tests/test_xtb_real_dataset_distribution_inputs.py`

- [ ] **Step 1: Add failing tests for tar member filtering and summary fields**

Append this test to `tests/test_xtb_real_dataset_distribution_inputs.py`:

```python
def test_convert_xtb_real_dataset_sdf_filters_tar_members_and_reports_summary(tmp_path) -> None:
    import tarfile

    sdf_text = """methanol
  unit

  6  5  0  0  0  0            999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.4300    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3600    1.0200    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3600   -0.5100    0.8833 H   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3600   -0.5100   -0.8833 H   0  0  0  0  0  0  0  0  0  0  0  0
    1.7500    0.0000    0.9000 H   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  1  3  1  0
  1  4  1  0
  1  5  1  0
  2  6  1  0
M  END
>  <PUBCHEM_COMPOUND_CID>
887

$$$$
"""
    keep = tmp_path / "keep.sdf"
    keep.write_text(sdf_text)
    skip = tmp_path / "skip.sdf"
    skip.write_text(sdf_text.replace("887", "999"))
    archive = tmp_path / "fixture.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(keep, arcname="wanted/keep.sdf")
        handle.add(skip, arcname="ignored/skip.sdf")

    output = tmp_path / "out.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/convert_xtb_real_dataset_sdf.py",
            "--input",
            str(archive),
            "--dataset-name",
            "qmugs",
            "--output-jsonl",
            str(output),
            "--member-name-contains",
            "wanted/",
            "--record-id-property",
            "PUBCHEM_COMPOUND_CID",
            "--limit",
            "5",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    summary = json.loads(completed.stdout)
    assert summary["members_seen"] == 2
    assert summary["members_selected"] == 1
    assert summary["written"] == 1
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert rows[0]["record_id"] == "887"
    assert rows[0]["source_file"] == "wanted/keep.sdf"
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_inputs.py::test_convert_xtb_real_dataset_sdf_filters_tar_members_and_reports_summary -q
```

Expected: FAIL because `--member-name-contains`, `members_seen`, and `members_selected` are not implemented.

- [ ] **Step 3: Extend converter arguments**

Modify `parse_args()` in `scripts/convert_xtb_real_dataset_sdf.py` to include:

```python
    parser.add_argument(
        "--member-name-contains",
        action="append",
        default=[],
        help="Only process tar SDF members whose archive path contains this text. Can be repeated.",
    )
```

- [ ] **Step 4: Replace SDF path iteration with member stats**

Replace `iter_sdf_paths()` with this implementation:

```python
def member_selected(name: str, filters: list[str]) -> bool:
    return not filters or any(text in name for text in filters)


def iter_sdf_paths(path: Path, filters: list[str]) -> Iterable[tuple[str, Path, bool]]:
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            for member in archive:
                if not member.isfile() or not member.name.lower().endswith(".sdf"):
                    continue
                selected = member_selected(member.name, filters)
                if not selected:
                    yield member.name, Path(), False
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    yield member.name, Path(), False
                    continue
                with tempfile.NamedTemporaryFile(suffix=".sdf", delete=False) as handle:
                    for chunk in iter(lambda: extracted.read(1024 * 1024), b""):
                        handle.write(chunk)
                    temp_path = Path(handle.name)
                try:
                    yield member.name, temp_path, True
                finally:
                    temp_path.unlink(missing_ok=True)
    else:
        yield path.name, path, True
```

- [ ] **Step 5: Update conversion summary accounting**

Modify `convert()` so its loop starts with:

```python
    members_seen = 0
    members_selected = 0
    with args.output_jsonl.open("w") as output:
        for source_name, sdf_path, selected in iter_sdf_paths(args.input, args.member_name_contains):
            members_seen += 1
            if not selected:
                continue
            members_selected += 1
            supplier = Chem.SDMolSupplier(str(sdf_path), removeHs=False, sanitize=False)
```

Ensure both return statements include:

```python
{
    "seen": seen,
    "written": written,
    "skipped": skipped,
    "members_seen": members_seen,
    "members_selected": members_selected,
}
```

- [ ] **Step 6: Run converter tests**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_inputs.py::test_convert_xtb_real_dataset_sdf_to_jsonl_file_and_tar tests/test_xtb_real_dataset_distribution_inputs.py::test_convert_xtb_real_dataset_sdf_filters_tar_members_and_reports_summary -q
```

Expected: PASS with 2 tests passing.

- [ ] **Step 7: Commit**

Run:

```bash
git add scripts/convert_xtb_real_dataset_sdf.py tests/test_xtb_real_dataset_distribution_inputs.py
git commit -m "feat: harden xtb sdf archive conversion"
```

## Task 3: Add Intermediate Tier-Aware Sampling Mode

**Files:**

- Modify: `scripts/prepare_xtb_real_dataset_sample.py`
- Modify: `tests/test_xtb_real_dataset_distribution_inputs.py`

- [ ] **Step 1: Add failing test for intermediate outputs**

Append this test to `tests/test_xtb_real_dataset_distribution_inputs.py`:

```python
def test_prepare_xtb_real_dataset_sample_intermediate_writes_tier_files(tmp_path) -> None:
    def record(dataset_name: str, record_id: str, xyz: str) -> dict[str, object]:
        return {
            "dataset_name": dataset_name,
            "record_id": record_id,
            "xyz": xyz,
            "charge": 0,
            "multiplicity": 1,
            "geometry_source": "fixture_xyz",
        }

    methane = "5\nmethane\nC 0 0 0\nH 0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH -0.63 0.63 -0.63\nH 0.63 -0.63 -0.63\n"
    methanol = "6\nmethanol\nC 0 0 0\nO 1.43 0 0\nH -0.36 1.02 0\nH -0.36 -0.51 0.883346\nH -0.36 -0.51 -0.883346\nH 1.75 0 0.9\n"
    ethane = "8\nethane\nC 0 0 0\nC 1.54 0 0\nH -0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH -0.63 0 -0.89\nH 2.17 0.63 0.63\nH 2.17 -0.63 0.63\nH 2.17 0 -0.89\n"
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                record("qm9", "methane", methane),
                record("qm9", "methanol", methanol),
                record("qmugs", "ethane", ethane),
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
            "20260615",
            "--intermediate",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    manifest = json.loads((output_dir / "sample_manifest.json").read_text())
    assert manifest["mode"] == "intermediate"
    assert (output_dir / "sampled_records.light.jsonl").exists()
    assert (output_dir / "sampled_records.medium.jsonl").exists()
    assert (output_dir / "sampled_records.expensive.jsonl").exists()
    expensive = [json.loads(line) for line in (output_dir / "sampled_records.expensive.jsonl").read_text().splitlines()]
    assert [row["record_id"] for row in expensive] == ["methanol", "ethane"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_inputs.py::test_prepare_xtb_real_dataset_sample_intermediate_writes_tier_files -q
```

Expected: FAIL because `--intermediate` and tier-specific files are not implemented.

- [ ] **Step 3: Add quotas and hessian predicate**

Add constants to `scripts/prepare_xtb_real_dataset_sample.py`:

```python
INTERMEDIATE_LIGHT_QUOTAS = {"qm9": 250, "qmugs": 500, "geom_drugs": 250, "tartarus_opv": 100}
INTERMEDIATE_MEDIUM_QUOTAS = {"qm9": 100, "qmugs": 250, "geom_drugs": 150, "tartarus_opv": 50}
INTERMEDIATE_EXPENSIVE_QUOTAS = {"qm9": 75, "qmugs": 75, "geom_drugs": 50, "tartarus_opv": 0}
HESSIAN_DOMAIN = {"atom_count": [6, 48], "heavy_atom_count": [4, 18]}
```

Add:

```python
def is_hessian_eligible(record: dict[str, Any]) -> bool:
    atom_count = int(record.get("atom_count", 0))
    heavy_atom_count = int(record.get("heavy_atom_count", 0))
    return (
        HESSIAN_DOMAIN["atom_count"][0] <= atom_count <= HESSIAN_DOMAIN["atom_count"][1]
        and HESSIAN_DOMAIN["heavy_atom_count"][0] <= heavy_atom_count <= HESSIAN_DOMAIN["heavy_atom_count"][1]
    )
```

- [ ] **Step 4: Add intermediate CLI mode**

Change the mode group in `parse_args()`:

```python
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pilot", action="store_true")
    mode.add_argument("--intermediate", action="store_true")
    mode.add_argument("--expanded", action="store_true")
```

Add:

```python
def mode_name(args: argparse.Namespace) -> str:
    if args.expanded:
        return "expanded"
    if args.intermediate:
        return "intermediate"
    return "pilot"
```

- [ ] **Step 5: Generalize quota sampling**

Replace `sample_records()` with:

```python
def sample_records_with_quotas(
    records: list[dict[str, Any]],
    quotas: dict[str, int],
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_dataset: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_dataset.setdefault(str(record.get("dataset_name")), []).append(record)

    sampled: list[dict[str, Any]] = []
    quota_notes: list[dict[str, Any]] = []
    for dataset_name in sorted(by_dataset):
        dataset_records = sorted(by_dataset[dataset_name], key=output_order_key)
        quota = quotas.get(dataset_name, len(dataset_records))
        selected = stratified_sample(dataset_records, quota, seed)
        sampled.extend(selected)
        if len(dataset_records) < quota:
            quota_notes.append(
                {
                    "dataset_name": dataset_name,
                    "available": len(dataset_records),
                    "quota": quota,
                    "status": "quota_underfilled",
                }
            )
    return sorted(sampled, key=output_order_key), quota_notes


def sample_records(records: list[dict[str, Any]], seed: int, expanded: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    quotas = EXPANDED_LIGHT_QUOTAS if expanded else PILOT_LIGHT_QUOTAS
    return sample_records_with_quotas(records, quotas, seed)
```

- [ ] **Step 6: Write tier files for intermediate mode**

In `main()`, compute `mode = mode_name(args)`. For `mode == "intermediate"`, write:

```python
    if mode == "intermediate":
        light_records, light_notes = sample_records_with_quotas(filtered_records, INTERMEDIATE_LIGHT_QUOTAS, args.seed)
        medium_candidates = [record for record in filtered_records if int(record.get("carbon_count", 0)) > 0]
        medium_records, medium_notes = sample_records_with_quotas(medium_candidates, INTERMEDIATE_MEDIUM_QUOTAS, args.seed)
        expensive_candidates = [record for record in filtered_records if is_hessian_eligible(record)]
        expensive_records, expensive_notes = sample_records_with_quotas(expensive_candidates, INTERMEDIATE_EXPENSIVE_QUOTAS, args.seed)
        sampled_records = sorted({stable_key(row): row for row in [*light_records, *medium_records, *expensive_records]}.values(), key=output_order_key)
        quota_notes = [
            {"tier": "light", **note} for note in light_notes
        ] + [
            {"tier": "medium", **note} for note in medium_notes
        ] + [
            {"tier": "expensive", **note} for note in expensive_notes
        ]
        write_jsonl(output_dir / "sampled_records.light.jsonl", light_records)
        write_jsonl(output_dir / "sampled_records.medium.jsonl", medium_records)
        write_jsonl(output_dir / "sampled_records.expensive.jsonl", expensive_records)
    else:
        sampled_records, quota_notes = sample_records(filtered_records, args.seed, args.expanded)
```

Ensure the manifest uses:

```python
        "mode": mode,
```

- [ ] **Step 7: Run sampling tests**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_inputs.py::test_prepare_xtb_real_dataset_sample_can_process_tiny_fixture tests/test_xtb_real_dataset_distribution_inputs.py::test_prepare_xtb_real_dataset_sample_intermediate_writes_tier_files -q
```

Expected: PASS with 2 tests passing.

- [ ] **Step 8: Commit**

Run:

```bash
git add scripts/prepare_xtb_real_dataset_sample.py tests/test_xtb_real_dataset_distribution_inputs.py
git commit -m "feat: add xtb intermediate dataset sampling"
```

## Task 4: Acquire or Validate Bounded Non-QM9 Inputs

**Files:**

- Modify: `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md`

- [ ] **Step 1: Inspect local availability**

Run:

```bash
uv run python scripts/inspect_xtb_real_dataset_availability.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --output-json artifacts/xtb_real_distribution/2026-06-15-expansion-prep/source_availability.local.json
```

Expected: `status: ok`. If `.cache/xtb_real_datasets/qmugs/structures.tar.gz` exists, it reports a nonzero `size_bytes`.

- [ ] **Step 2: Check remote metadata only**

Run:

```bash
uv run python scripts/inspect_xtb_real_dataset_availability.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --check-remote \
  --remote-timeout 20 \
  --output-json artifacts/xtb_real_distribution/2026-06-15-expansion-prep/source_availability.remote.json
```

Expected: `remote_checked: true`. QMugs metadata files should be reachable. GEOM Dataverse API may respond, but slow file transfer is not a failure of this metadata check.

- [ ] **Step 3: Download or confirm QMugs structures archive**

If `.cache/xtb_real_datasets/qmugs/structures.tar.gz` is absent, run:

```bash
mkdir -p .cache/xtb_real_datasets/qmugs
curl -L --fail --continue-at - \
  "https://libdrive.ethz.ch/index.php/s/X5vOBNSITAG5vzM/download?path=%2F&files=structures.tar.gz" \
  -o .cache/xtb_real_datasets/qmugs/structures.tar.gz
```

Expected: file exists and is approximately 7.2 GB. If the transfer cannot complete in the current session, stop this task with `qmugs_structure_archive_missing` in the report and do not run formal Expanded Run.

- [ ] **Step 4: Convert a bounded QMugs JSONL**

Run:

```bash
uv run python scripts/convert_xtb_real_dataset_sdf.py \
  --input .cache/xtb_real_datasets/qmugs/structures.tar.gz \
  --dataset-name qmugs \
  --output-jsonl .cache/xtb_real_datasets/qmugs/qmugs_bounded.jsonl \
  --record-id-property PUBCHEM_COMPOUND_CID \
  --geometry-source dataset_sdf_3d \
  --limit 1000
```

Expected: JSON summary with `status: ok`, `written` greater than or equal to 100 unless the archive contains fewer eligible SDF molecules. Do not proceed to Expanded Run if `written` is 0.

- [ ] **Step 5: Retry GEOM small validation acquisition**

Run:

```bash
mkdir -p .cache/xtb_real_datasets/geom_drugs
curl -L --fail --continue-at - \
  "https://dataverse.harvard.edu/api/access/datafile/5858503" \
  -o .cache/xtb_real_datasets/geom_drugs/censo.tar.gz
```

Expected: `censo.tar.gz` exists and has nonzero size. If transfer stalls or the archive contains no SDF files, record `geom_validation_transfer_incomplete` or `geom_validation_no_sdf_members` in the research report.

- [ ] **Step 6: Attempt GEOM validation conversion**

Run:

```bash
uv run python scripts/convert_xtb_real_dataset_sdf.py \
  --input .cache/xtb_real_datasets/geom_drugs/censo.tar.gz \
  --dataset-name geom_drugs \
  --output-jsonl .cache/xtb_real_datasets/geom_drugs/geom_validation.jsonl \
  --geometry-source dataset_archive_3d \
  --limit 250
```

Expected: If the validation archive contains SDF members, `written` is greater than 0. If it does not, this is an access-format limitation to document, not a code failure.

- [ ] **Step 7: Record acquisition results in the research report**

Generate and append a `Dataset Expansion Prep Input Status` section from the files produced in this task:

```bash
uv run python - <<'PY'
from pathlib import Path

REPORT = Path("docs/research/2026-06-15-xtb-real-dataset-property-distributions.md")


def count_jsonl(path: str) -> int:
    file_path = Path(path)
    if not file_path.exists():
        return 0
    return sum(1 for line in file_path.read_text().splitlines() if line.strip())


qm9_count = count_jsonl(".cache/xtb_real_datasets/qm9/qm9_smoke60.jsonl")
qmugs_count = count_jsonl(".cache/xtb_real_datasets/qmugs/qmugs_bounded.jsonl")
geom_count = count_jsonl(".cache/xtb_real_datasets/geom_drugs/geom_validation.jsonl")
qmugs_status = "normalized_available" if qmugs_count >= 100 else "blocked_or_underfilled"
geom_status = "normalized_available" if geom_count > 0 else "validation_unavailable_or_no_sdf"
qmugs_decision = (
    "Use as the required non-QM9 source for intermediate calibration."
    if qmugs_count >= 100
    else "Do not run Expanded Run; complete QMugs archive conversion first."
)
geom_decision = (
    "Include as optional validation coverage."
    if geom_count > 0
    else "Do not count GEOM toward coverage until a usable 3D archive is normalized."
)

section = f"""
## Dataset Expansion Prep Input Status

| Source | Prep status | Normalized records | Decision |
| --- | --- | ---: | --- |
| QM9 | available | {qm9_count} | Keep as baseline source. |
| QMugs | {qmugs_status} | {qmugs_count} | {qmugs_decision} |
| GEOM-Drugs | {geom_status} | {geom_count} | {geom_decision} |
| Tartarus/OPV | manual_or_generated_geometry_required | 0 | Keep out of automatic calibration until provenance is explicit. |
"""

REPORT.write_text(REPORT.read_text().rstrip() + "\n\n" + section.strip() + "\n")
PY
```

Expected: the appended section contains concrete counts and decisions derived from local files.

- [ ] **Step 8: Commit if the report changed**

Run:

```bash
git add docs/research/2026-06-15-xtb-real-dataset-property-distributions.md
git commit -m "docs: record xtb expansion prep inputs"
```

Skip this commit only if no report text changed.

## Task 5: Build Mixed Intermediate Samples

**Files:**

- No source-code files required if Tasks 1-3 are complete.
- Generated: `artifacts/xtb_real_distribution/2026-06-15-expansion-prep/`

- [ ] **Step 1: Confirm at least one non-QM9 JSONL input exists**

Run:

```bash
test -s .cache/xtb_real_datasets/qmugs/qmugs_bounded.jsonl || test -s .cache/xtb_real_datasets/geom_drugs/geom_validation.jsonl
```

Expected: exit code 0. If exit code is 1, stop here and update the report with `not_ready_for_intermediate_calibration`.

- [ ] **Step 2: Prepare input argument list**

Use the QM9 smoke input from the prior run if present:

```bash
ls .cache/xtb_real_datasets/qm9/qm9_smoke60.jsonl
```

Expected: file exists. If absent, regenerate a bounded QM9 JSONL using the existing converter from the cached `gdb9.sdf` or `gdb9.tar.gz` before continuing.

- [ ] **Step 3: Run intermediate sample preparation**

Run this command when QMugs exists:

```bash
uv run python scripts/prepare_xtb_real_dataset_sample.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --input-jsonl .cache/xtb_real_datasets/qm9/qm9_smoke60.jsonl \
  --input-jsonl .cache/xtb_real_datasets/qmugs/qmugs_bounded.jsonl \
  --output-dir artifacts/xtb_real_distribution/2026-06-15-expansion-prep \
  --seed 20260615 \
  --intermediate
```

If GEOM validation JSONL exists, include:

```bash
  --input-jsonl .cache/xtb_real_datasets/geom_drugs/geom_validation.jsonl
```

Expected: `sample_manifest.json` reports `mode: intermediate` and writes `sampled_records.light.jsonl`, `sampled_records.medium.jsonl`, and `sampled_records.expensive.jsonl`.

- [ ] **Step 4: Validate mixed source coverage**

Run:

```bash
uv run python - <<'PY'
import json
from collections import Counter
from pathlib import Path

root = Path("artifacts/xtb_real_distribution/2026-06-15-expansion-prep")
for name in ["light", "medium", "expensive"]:
    path = root / f"sampled_records.{name}.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(name, len(rows), dict(Counter(row["dataset_name"] for row in rows)))
PY
```

Expected: light and medium contain `qm9` plus at least one of `qmugs` or `geom_drugs`. Expensive may be QM9-only if no non-QM9 hessian-domain records pass filtering, but this limitation must be recorded.

## Task 6: Run Intermediate xTB Calibration

**Files:**

- Generated: `artifacts/xtb_real_distribution/2026-06-15-expansion-prep/light_results.json`
- Generated: `artifacts/xtb_real_distribution/2026-06-15-expansion-prep/medium_results.json`
- Generated: `artifacts/xtb_real_distribution/2026-06-15-expansion-prep/expensive_results.json`

- [ ] **Step 1: Verify xTB environment**

Run:

```bash
uv run python scripts/check_xtb_env.py
```

Expected: JSON with `status: ok` and an xTB executable path.

- [ ] **Step 2: Run light tier**

Run:

```bash
uv run python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-15-expansion-prep/sampled_records.light.jsonl \
  --tier light \
  --output artifacts/xtb_real_distribution/2026-06-15-expansion-prep/light_results.json
```

Expected: JSON with `status: ok`. If runtime is too long, rerun with `--max-records 500` and record the cap in the report.

- [ ] **Step 3: Run medium tier**

Run:

```bash
uv run python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-15-expansion-prep/sampled_records.medium.jsonl \
  --tier medium \
  --output artifacts/xtb_real_distribution/2026-06-15-expansion-prep/medium_results.json
```

Expected: JSON with `status: ok`. Property-level errors above 5% require a repair pass before Expanded Run.

- [ ] **Step 4: Run expensive tier**

Run:

```bash
uv run python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-15-expansion-prep/sampled_records.expensive.jsonl \
  --tier expensive \
  --output artifacts/xtb_real_distribution/2026-06-15-expansion-prep/expensive_results.json
```

Expected: JSON with `status: ok`. Nonzero `imaginary_frequency_count` values are acceptable distribution signal. Parser/tool errors above 5% block Expanded Run.

## Task 7: Analyze Results and Emit Readiness Decision

**Files:**

- Modify: `scripts/analyze_xtb_real_dataset_distribution.py`
- Modify: `tests/test_xtb_real_dataset_distribution_scripts.py`
- Modify: `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md`

- [ ] **Step 1: Add failing readiness-analysis test**

Append this test to `tests/test_xtb_real_dataset_distribution_scripts.py`:

```python
def test_analyze_xtb_real_dataset_distribution_writes_expanded_readiness(tmp_path) -> None:
    light_results = tmp_path / "light_results.json"
    output_dir = tmp_path / "analysis"
    rows = []
    for index in range(120):
        rows.append(
            {
                "dataset_name": "qmugs",
                "record_id": f"q{index}",
                "status": "ok",
                "failure_type": None,
                "properties": {"homo_lumo_gap": 4.0 + index / 100.0},
                "property_statuses": {"homo_lumo_gap": {"status": "ok", "failure_type": None}},
            }
        )
    light_results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "light",
                "properties": ["homo_lumo_gap"],
                "rows": rows,
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_xtb_real_dataset_distribution.py",
            "--inputs",
            str(light_results),
            "--output-dir",
            str(output_dir),
            "--expanded-readiness",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    readiness = json.loads((output_dir / "expanded_run_readiness.json").read_text())
    assert readiness["non_qm9_ok_records"] == 120
    assert readiness["ready_for_expanded_run"] is True
    assert (output_dir / "expanded_run_readiness.md").read_text().startswith("# Expanded Run Readiness")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_scripts.py::test_analyze_xtb_real_dataset_distribution_writes_expanded_readiness -q
```

Expected: FAIL because `--expanded-readiness` is not implemented.

- [ ] **Step 3: Add analyzer argument**

Add to `parse_args()`:

```python
    parser.add_argument("--expanded-readiness", action="store_true")
```

- [ ] **Step 4: Add readiness calculation**

Add this function to `scripts/analyze_xtb_real_dataset_distribution.py`:

```python
def expanded_readiness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    non_qm9_ok = [
        row
        for row in rows
        if str(row.get("dataset_name")) != "qm9"
        and any(status.get("status") == "ok" for status in (row.get("property_statuses") or {}).values())
    ]
    attempted = 0
    errors = 0
    for row in rows:
        for status in (row.get("property_statuses") or {}).values():
            if status.get("status") == "skipped":
                continue
            attempted += 1
            if status.get("status") == "error":
                errors += 1
    property_error_rate = (errors / attempted) if attempted else None
    blockers: list[str] = []
    if len(non_qm9_ok) < 100:
        blockers.append("non_qm9_ok_records_below_100")
    if property_error_rate is None:
        blockers.append("no_attempted_properties")
    elif property_error_rate > 0.05:
        blockers.append("property_error_rate_above_5_percent")
    return {
        "ready_for_expanded_run": not blockers,
        "non_qm9_ok_records": len(non_qm9_ok),
        "attempted_property_count": attempted,
        "error_property_count": errors,
        "property_error_rate": property_error_rate,
        "blockers": blockers,
    }
```

Add:

```python
def write_readiness_markdown(readiness: dict[str, Any]) -> str:
    decision = "ready" if readiness["ready_for_expanded_run"] else "not_ready"
    lines = [
        "# Expanded Run Readiness",
        "",
        f"- Decision: `{decision}`",
        f"- Non-QM9 ok records: {readiness['non_qm9_ok_records']}",
        f"- Attempted property count: {readiness['attempted_property_count']}",
        f"- Error property count: {readiness['error_property_count']}",
        f"- Property error rate: {fmt(readiness['property_error_rate'])}",
        f"- Blockers: {', '.join(readiness['blockers']) if readiness['blockers'] else 'none'}",
        "",
    ]
    return "\n".join(lines)
```

In `main()`, after recommendations:

```python
    if args.expanded_readiness:
        readiness = expanded_readiness(rows)
        (args.output_dir / "expanded_run_readiness.json").write_text(json.dumps(readiness, indent=2, sort_keys=True))
        (args.output_dir / "expanded_run_readiness.md").write_text(write_readiness_markdown(readiness))
```

- [ ] **Step 5: Run analyzer readiness tests**

Run:

```bash
uv run pytest tests/test_xtb_real_dataset_distribution_scripts.py::test_analyze_xtb_real_dataset_distribution_writes_expanded_readiness -q
```

Expected: PASS.

- [ ] **Step 6: Analyze intermediate calibration outputs**

Run:

```bash
uv run python scripts/analyze_xtb_real_dataset_distribution.py \
  --inputs \
    artifacts/xtb_real_distribution/2026-06-15-expansion-prep/light_results.json \
    artifacts/xtb_real_distribution/2026-06-15-expansion-prep/medium_results.json \
    artifacts/xtb_real_distribution/2026-06-15-expansion-prep/expensive_results.json \
  --output-dir artifacts/xtb_real_distribution/2026-06-15-expansion-prep/analysis \
  --expanded-readiness
```

Expected: analysis files plus `expanded_run_readiness.json` and `expanded_run_readiness.md`.

- [ ] **Step 7: Update research report with calibration results**

Generate and append a `Dataset Expansion Prep Calibration Results` section from the intermediate result JSON files and readiness JSON:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

REPORT = Path("docs/research/2026-06-15-xtb-real-dataset-property-distributions.md")
ROOT = Path("artifacts/xtb_real_distribution/2026-06-15-expansion-prep")
READINESS = ROOT / "analysis" / "expanded_run_readiness.json"


def tier_line(tier: str) -> str:
    payload = json.loads((ROOT / f"{tier}_results.json").read_text())
    rows = payload.get("rows", [])
    non_qm9 = sum(1 for row in rows if row.get("dataset_name") != "qm9")
    attempted = 0
    errors = 0
    for row in rows:
        for status in (row.get("property_statuses") or {}).values():
            if status.get("status") == "skipped":
                continue
            attempted += 1
            if status.get("status") == "error":
                errors += 1
    error_rate = errors / attempted if attempted else 0.0
    decision = "pass" if error_rate <= 0.05 else "repair_required"
    return f"| {tier} | {len(rows)} | {non_qm9} | {error_rate:.4f} | {decision} |"


readiness = json.loads(READINESS.read_text())
readiness_label = "ready" if readiness["ready_for_expanded_run"] else "not_ready"
blockers = readiness["blockers"] or ["none"]
blocker_lines = "\n".join(f"- `{blocker}`" for blocker in blockers)
section = "\n".join(
    [
        "## Dataset Expansion Prep Calibration Results",
        "",
        "| Tier | Records run | Non-QM9 records | Property error rate | Decision |",
        "| --- | ---: | ---: | ---: | --- |",
        tier_line("light"),
        tier_line("medium"),
        tier_line("expensive"),
        "",
        f"Expanded Run readiness: `{readiness_label}`.",
        "",
        "Blockers:",
        "",
        blocker_lines,
        "",
    ]
)

REPORT.write_text(REPORT.read_text().rstrip() + "\n\n" + section)
PY
```

Expected: the appended section contains concrete tier counts, non-QM9 counts, property error rates, and readiness blockers. If the readiness JSON says `ready_for_expanded_run: false`, the committed report states that the next step is another targeted access/runtime repair pass, not Expanded Run.

- [ ] **Step 8: Commit analyzer and report changes**

Run:

```bash
git add scripts/analyze_xtb_real_dataset_distribution.py tests/test_xtb_real_dataset_distribution_scripts.py docs/research/2026-06-15-xtb-real-dataset-property-distributions.md
git commit -m "feat: report xtb expanded run readiness"
```

## Task 8: Final Verification

**Files:**

- All files changed in Tasks 1-7.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest \
  tests/test_xtb_real_dataset_availability.py \
  tests/test_xtb_real_dataset_distribution_inputs.py \
  tests/test_xtb_real_dataset_distribution_scripts.py \
  -q
```

Expected: all tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Inspect working tree**

Run:

```bash
git status --short
```

Expected: source, tests, and research docs are cleanly committed. `.cache/` and `artifacts/` outputs remain untracked or ignored.

- [ ] **Step 4: State final execution judgment**

Use the actual `artifacts/xtb_real_distribution/2026-06-15-expansion-prep/analysis/expanded_run_readiness.json` result:

- If `ready_for_expanded_run` is `true`, next step is the formal Expanded Run at the low end of planned quotas: 10,000 light, 2,000 medium, 500 expensive.
- If `ready_for_expanded_run` is `false`, next step is the blocker-specific repair named in `blockers`, usually non-QM9 source normalization or property runtime repair.

## Execution Notes

- Treat QMugs as the preferred non-QM9 source because machine-readable WebDAV metadata is already fixed.
- Treat GEOM validation as opportunistic until a small usable 3D archive is confirmed.
- Keep Tartarus/OPV out of automatic calibration until the source and geometry provenance are explicit.
- Do not silently generate conformers from SMILES for final calibration records. If generated geometry is used in a later plan, label `geometry_source` as `generated_geometry` and document the generator, seed, force field, and minimization settings.
- Do not commit `.cache/` or `artifacts/` outputs unless a later plan explicitly changes artifact retention policy.
