#!/usr/bin/env python
"""Smoke-check native MACE-MP verifier environment."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from typing import Any

from verifiers.backends import mace_mp_properties


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


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    spec = {
        "mace_mp": {
            "model": args.model,
            "device": args.device,
            "default_dtype": args.default_dtype,
        }
    }
    try:
        structure, atoms = mace_mp_properties.parse_cif_atoms(SI_CIF_TEXT)
        input_properties = mace_mp_properties.inspect_structure(structure, atoms)
        prediction = mace_mp_properties.predict_mace_mp_properties(atoms, spec)
    except (ImportError, ModuleNotFoundError) as exc:
        return {"status": "error", "failure_type": "verifier_environment_error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "failure_type": "verifier_tool_error", "message": str(exc)}

    return {
        "status": "ok",
        "failure_type": None,
        "message": None,
        "versions": {
            "mace-torch": package_version("mace-torch"),
            "torch": package_version("torch"),
            "ase": package_version("ase"),
            "pymatgen": package_version("pymatgen"),
        },
        "runtime": {
            "model": args.model,
            "device": args.device,
            "default_dtype": args.default_dtype,
        },
        "input": input_properties,
        "prediction": prediction,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--default-dtype", default="float32")
    print(json.dumps(build_payload(parser.parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
