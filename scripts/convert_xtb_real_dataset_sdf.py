#!/usr/bin/env python
"""Convert SDF files or tar archives of SDF files to normalized xTB JSONL records."""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
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
    return parser.parse_args()


def iter_sdf_paths(path: Path) -> Iterable[tuple[str, Path]]:
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            for member in archive:
                if not member.isfile() or not member.name.lower().endswith(".sdf"):
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                with tempfile.NamedTemporaryFile(suffix=".sdf", delete=False) as handle:
                    handle.write(extracted.read())
                    temp_path = Path(handle.name)
                try:
                    yield member.name, temp_path
                finally:
                    temp_path.unlink(missing_ok=True)
    else:
        yield path.name, path


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


def convert(args: argparse.Namespace) -> dict[str, int]:
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    seen = 0
    with args.output_jsonl.open("w") as output:
        for source_name, sdf_path in iter_sdf_paths(args.input):
            supplier = Chem.SDMolSupplier(str(sdf_path), removeHs=False, sanitize=False)
            for mol_index, mol in enumerate(supplier, start=1):
                seen += 1
                if mol is None:
                    skipped += 1
                    continue
                record_id = record_id_for(mol, source_name, mol_index, args.record_id_property)
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
                    return {"seen": seen, "written": written, "skipped": skipped}
    return {"seen": seen, "written": written, "skipped": skipped}


def main() -> int:
    args = parse_args()
    summary = convert(args)
    print(json.dumps({"status": "ok", "output_jsonl": str(args.output_jsonl), **summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
