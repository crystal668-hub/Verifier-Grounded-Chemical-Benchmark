from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repository_root() -> Path:
    package_path = package_root()
    for candidate in (package_path, *package_path.parents):
        if (candidate / "tasks").is_dir():
            return candidate
    package_parent = package_path.parent
    if package_parent.name == "src":
        return package_parent.parent
    return package_path


def source_root() -> Path:
    root = repository_root()
    src_root = root / "src"
    if src_root.is_dir():
        return src_root
    return root


def resolve_path(path: str | Path, base: str | Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()

    root = Path(base) if base is not None else repository_root()
    return (root / candidate).resolve()


def resolve_script_path(path: str | Path, base: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved
        try:
            relative = resolved.relative_to(repository_root())
        except ValueError:
            return resolved
        src_candidate = (source_root() / relative).resolve()
        if src_candidate.exists():
            return src_candidate
        return resolved

    resolved = resolve_path(candidate, base=base)
    if resolved.exists():
        return resolved

    src_candidate = (source_root() / candidate).resolve()
    if src_candidate.exists():
        return src_candidate
    return resolved


def materialize_verifier_specs(
    specs: dict[str, dict[str, Any]],
    script_root: str | Path,
) -> dict[str, dict[str, Any]]:
    materialized = deepcopy(specs)
    for spec in materialized.values():
        verification_script = spec.get("verification_script")
        if isinstance(verification_script, str) and verification_script:
            spec["verification_script"] = str(
                resolve_script_path(verification_script, base=script_root)
            )
    return materialized
