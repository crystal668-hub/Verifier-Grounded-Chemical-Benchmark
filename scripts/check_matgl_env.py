#!/usr/bin/env python
"""Smoke-check native MatGL+pymatgen verifier environment."""

from __future__ import annotations

import argparse
import contextlib
import importlib.metadata as metadata
import io
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
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


def environment_error(message: str, **details: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "missing",
        "failure_type": "verifier_environment_error",
        "message": message,
    }
    payload.update({key: value for key, value in details.items() if value})
    return payload


def package_version(distribution: str) -> str:
    return metadata.version(distribution)


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import matgl
        from pymatgen.core import Structure
    except Exception as exc:
        return environment_error(
            f"failed to import MatGL/pymatgen: {exc}",
            install_hint="Run `uv sync --group materials` to install matgl==4.0.2 and its material-science dependencies.",
        )

    try:
        structure = Structure.from_str(SI_CIF_TEXT, fmt="cif")
    except Exception as exc:
        return {
            "status": "missing",
            "failure_type": "verifier_environment_error",
            "message": f"failed to parse embedded Si CIF fixture: {exc}",
        }

    payload: dict[str, Any] = {
        "status": "ok",
        "versions": {
            "matgl": package_version("matgl"),
            "pymatgen": package_version("pymatgen"),
            "torch": package_version("torch"),
        },
        "pymatgen": {
            "fixture": "embedded_si_cif",
            "fixture_formula": structure.composition.reduced_formula,
            "atom_count": len(structure),
        },
        "model": {
            "loaded": False,
            "name": args.model,
        },
    }

    if not args.no_model_load:
        model_stdout = io.StringIO()
        model_stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(model_stdout), contextlib.redirect_stderr(model_stderr):
                model = matgl.load_model(args.model)
        except Exception as exc:
            return environment_error(
                f"failed to load MatGL model {args.model}: {exc}",
                model_load_stdout=model_stdout.getvalue(),
                model_load_stderr=model_stderr.getvalue(),
            )
        payload["model"]["loaded"] = True
        payload["model"]["class"] = type(model).__name__

    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="MEGNet-Eform-MP-2018.6.1")
    parser.add_argument("--no-model-load", action="store_true")
    args = parser.parse_args()

    print(json.dumps(build_payload(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
