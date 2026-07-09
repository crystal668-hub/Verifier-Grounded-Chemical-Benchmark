#!/usr/bin/env python
"""Convert GEOM-style pickle conformer archives to normalized xTB JSONL records."""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import tarfile
from pathlib import Path
from typing import Any, BinaryIO

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rdkit import Chem


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="GEOM .tar/.tar.gz archive containing rd_mols pickle files")
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--dataset-name", default="geom_drugs")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--geometry-source", default="geom_pickle_rdkit_conformer")
    parser.add_argument("--max-conformers-per-molecule", type=int, default=1)
    parser.add_argument(
        "--max-member-bytes",
        type=int,
        default=50 * 1024 * 1024,
        help="Skip pickle members larger than this many bytes before reading. Use 0 or less to disable.",
    )
    return parser.parse_args()


def mol_to_xyz(mol: Chem.Mol, comment: str) -> str | None:
    if mol.GetNumConformers() == 0:
        return None
    conformer = mol.GetConformer()
    lines = [str(mol.GetNumAtoms()), comment]
    for atom in mol.GetAtoms():
        position = conformer.GetAtomPosition(atom.GetIdx())
        lines.append(f"{atom.GetSymbol()} {position.x:.8f} {position.y:.8f} {position.z:.8f}")
    return "\n".join(lines) + "\n"


def formal_charge(mol: Chem.Mol) -> int:
    return sum(atom.GetFormalCharge() for atom in mol.GetAtoms())


def molecule_stem(member_name: str) -> str:
    return Path(member_name).stem


def load_pickle_payload(handle: BinaryIO) -> dict[str, Any] | None:
    payload = pickle.loads(handle.read())
    if isinstance(payload, dict):
        return payload
    return None


def first_present(mapping: dict[str, Any], keys: tuple[str, ...], fallback: Any) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return fallback


def convert(args: argparse.Namespace) -> dict[str, int]:
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    pickle_members_seen = 0
    pickle_payloads_loaded = 0
    pickle_load_errors = 0
    non_dict_payloads = 0
    oversized_members = 0
    conformers_seen = 0
    written = 0
    skipped = 0
    with args.output_jsonl.open("w") as output:
        with tarfile.open(args.input) as archive:
            for member in archive:
                if not member.isfile() or not member.name.endswith(".pickle"):
                    continue
                pickle_members_seen += 1
                if args.max_member_bytes > 0 and member.size > args.max_member_bytes:
                    oversized_members += 1
                    skipped += 1
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    pickle_load_errors += 1
                    skipped += 1
                    continue
                try:
                    payload = load_pickle_payload(extracted)
                except Exception:
                    pickle_load_errors += 1
                    skipped += 1
                    continue
                if payload is None:
                    non_dict_payloads += 1
                    skipped += 1
                    continue
                pickle_payloads_loaded += 1
                conformers = payload.get("conformers", [])
                if not isinstance(conformers, list):
                    skipped += 1
                    continue
                selected_for_member = 0
                for conformer_index, conformer_payload in enumerate(conformers, start=1):
                    conformers_seen += 1
                    if args.max_conformers_per_molecule is not None and selected_for_member >= args.max_conformers_per_molecule:
                        skipped += 1
                        continue
                    if not isinstance(conformer_payload, dict):
                        skipped += 1
                        continue
                    mol = conformer_payload.get("rd_mol")
                    if not isinstance(mol, Chem.Mol):
                        skipped += 1
                        continue
                    xyz = mol_to_xyz(mol, f"{args.dataset_name} {molecule_stem(member.name)}")
                    if xyz is None:
                        skipped += 1
                        continue
                    geom_id = first_present(conformer_payload, ("geom_id", "confnum"), conformer_index)
                    record = {
                        "dataset_name": args.dataset_name,
                        "record_id": f"{molecule_stem(member.name)}_{geom_id}",
                        "xyz": xyz,
                        "charge": formal_charge(mol),
                        "multiplicity": 1,
                        "geometry_source": args.geometry_source,
                        "source_file": member.name,
                        "source_conformer_index": conformer_index,
                    }
                    output.write(json.dumps(record, sort_keys=True) + "\n")
                    written += 1
                    selected_for_member += 1
                    if args.limit is not None and written >= args.limit:
                        return {
                            "pickle_members_seen": pickle_members_seen,
                            "pickle_files_seen": pickle_members_seen,
                            "pickle_payloads_loaded": pickle_payloads_loaded,
                            "pickle_load_errors": pickle_load_errors,
                            "non_dict_payloads": non_dict_payloads,
                            "oversized_members": oversized_members,
                            "conformers_seen": conformers_seen,
                            "written": written,
                            "skipped": skipped,
                        }
    return {
        "pickle_members_seen": pickle_members_seen,
        "pickle_files_seen": pickle_members_seen,
        "pickle_payloads_loaded": pickle_payloads_loaded,
        "pickle_load_errors": pickle_load_errors,
        "non_dict_payloads": non_dict_payloads,
        "oversized_members": oversized_members,
        "conformers_seen": conformers_seen,
        "written": written,
        "skipped": skipped,
    }


def main() -> int:
    args = parse_args()
    summary = convert(args)
    print(json.dumps({"status": "ok", "output_jsonl": str(args.output_jsonl), **summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
