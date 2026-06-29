from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, base: str | Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()

    root = Path(base) if base is not None else package_root()
    return (root / candidate).resolve()


def materialize_verifier_specs(
    specs: dict[str, dict[str, Any]],
    script_root: str | Path,
) -> dict[str, dict[str, Any]]:
    materialized = deepcopy(specs)
    for spec in materialized.values():
        verification_script = spec.get("verification_script")
        if isinstance(verification_script, str) and verification_script:
            spec["verification_script"] = str(
                resolve_path(verification_script, base=script_root)
            )
    return materialized
