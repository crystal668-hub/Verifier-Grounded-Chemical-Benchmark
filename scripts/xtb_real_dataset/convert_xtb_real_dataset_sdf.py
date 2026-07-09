#!/usr/bin/env python
"""Convert SDF files or tar archives of SDF files to normalized xTB JSONL records."""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rdkit import Chem


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="SDF file or .tar/.tar.gz archive containing SDF files")
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--record-id-property", default="SOURCE_ID")
    parser.add_argument("--geometry-source", default="sdf_3d")
    parser.add_argument(
        "--member-name-contains",
        action="append",
        default=[],
        help="Only process tar SDF members whose archive path contains this text. Can be repeated.",
    )
    parser.add_argument(
        "--allow-partial-archive",
        action="store_true",
        help="Keep records converted before a truncated tar/tar.gz archive read error.",
    )
    return parser.parse_args()


def member_selected(name: str, filters: list[str]) -> bool:
    return not filters or any(text in name for text in filters)


def iter_sdf_paths(
    path: Path,
    filters: list[str],
    allow_partial_archive: bool = False,
    summary: dict[str, int] | None = None,
) -> Iterable[tuple[str, Path, bool]]:
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            members = iter(archive)
            while True:
                try:
                    member = next(members)
                except StopIteration:
                    break
                except (EOFError, tarfile.ReadError):
                    if summary is not None:
                        summary["archive_read_errors"] = summary.get("archive_read_errors", 0) + 1
                    if allow_partial_archive:
                        break
                    raise
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
                    try:
                        for chunk in iter(lambda: extracted.read(1024 * 1024), b""):
                            handle.write(chunk)
                    except (EOFError, tarfile.ReadError):
                        if summary is not None:
                            summary["archive_read_errors"] = summary.get("archive_read_errors", 0) + 1
                        temp_path = Path(handle.name)
                        temp_path.unlink(missing_ok=True)
                        if allow_partial_archive:
                            return
                        raise
                    temp_path = Path(handle.name)
                try:
                    yield member.name, temp_path, True
                finally:
                    temp_path.unlink(missing_ok=True)
    else:
        yield path.name, path, True


def mol_to_xyz(mol: Chem.Mol, comment: str) -> str | None:
    if mol.GetNumConformers() == 0:
        return None
    conformer = mol.GetConformer()
    lines = [str(mol.GetNumAtoms()), comment]
    for atom in mol.GetAtoms():
        position = conformer.GetAtomPosition(atom.GetIdx())
        lines.append(f"{atom.GetSymbol()} {position.x:.8f} {position.y:.8f} {position.z:.8f}")
    return "\n".join(lines) + "\n"


def record_id_for(mol: Chem.Mol, source_name: str, mol_index: int, property_name: str) -> str:
    if mol.HasProp(property_name):
        value = mol.GetProp(property_name).strip()
        if value:
            return value
    stem = Path(source_name).stem
    return f"{stem}_{mol_index:06d}"


def disambiguated_record_id(record_id: str, seen_record_ids: Counter[str]) -> str:
    seen_record_ids[record_id] += 1
    occurrence = seen_record_ids[record_id]
    if occurrence == 1:
        return record_id
    return f"{record_id}__dup{occurrence:03d}"


def convert(args: argparse.Namespace) -> dict[str, int]:
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    seen = 0
    members_seen = 0
    members_selected = 0
    archive_summary = {"archive_read_errors": 0}
    duplicate_record_ids_disambiguated = 0
    seen_record_ids: Counter[str] = Counter()
    with args.output_jsonl.open("w") as output:
        for source_name, sdf_path, selected in iter_sdf_paths(
            args.input,
            args.member_name_contains,
            args.allow_partial_archive,
            archive_summary,
        ):
            members_seen += 1
            if not selected:
                continue
            members_selected += 1
            supplier = Chem.SDMolSupplier(str(sdf_path), removeHs=False, sanitize=False)
            for mol_index, mol in enumerate(supplier, start=1):
                seen += 1
                if mol is None:
                    skipped += 1
                    continue
                raw_record_id = record_id_for(mol, source_name, mol_index, args.record_id_property)
                record_id = disambiguated_record_id(raw_record_id, seen_record_ids)
                if record_id != raw_record_id:
                    duplicate_record_ids_disambiguated += 1
                xyz = mol_to_xyz(mol, f"{args.dataset_name} {record_id}")
                if xyz is None:
                    skipped += 1
                    continue
                record = {
                    "dataset_name": args.dataset_name,
                    "record_id": record_id,
                    "xyz": xyz,
                    "charge": 0,
                    "multiplicity": 1,
                    "geometry_source": args.geometry_source,
                    "source_file": source_name,
                }
                output.write(json.dumps(record, sort_keys=True) + "\n")
                written += 1
                if args.limit is not None and written >= args.limit:
                    return {
                        "seen": seen,
                        "written": written,
                        "skipped": skipped,
                        "members_seen": members_seen,
                        "members_selected": members_selected,
                        "archive_read_errors": archive_summary["archive_read_errors"],
                        "duplicate_record_ids_disambiguated": duplicate_record_ids_disambiguated,
                    }
    return {
        "seen": seen,
        "written": written,
        "skipped": skipped,
        "members_seen": members_seen,
        "members_selected": members_selected,
        "archive_read_errors": archive_summary["archive_read_errors"],
        "duplicate_record_ids_disambiguated": duplicate_record_ids_disambiguated,
    }


def main() -> int:
    args = parse_args()
    summary = convert(args)
    print(json.dumps({"status": "ok", "output_jsonl": str(args.output_jsonl), **summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
