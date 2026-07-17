"""Package and filesystem resource location for task packs."""

from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from typing import Any


PACK_RESOURCE_PACKAGE = "verifier_grounded_benchmark.task.packs"


def package_resource(pack: str, filename: str) -> Any:
    return files(PACK_RESOURCE_PACKAGE).joinpath(pack, filename)


def repository_root() -> Path:
    package_path = Path(__file__).resolve().parents[2]
    for candidate in (package_path, *package_path.parents):
        if (candidate / "tasks").is_dir():
            return candidate
    if package_path.parent.name == "src":
        return package_path.parent.parent
    return package_path


def source_root() -> Path:
    root = repository_root()
    src = root / "src"
    return src if src.is_dir() else root


def resolve_path(path: str | Path, *, base: str | Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (Path(base) if base is not None else repository_root()).joinpath(candidate).resolve()


def resolve_script_path(path: str | Path, base: str | Path) -> Path:
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else resolve_path(candidate, base=base)
    if resolved.exists():
        return resolved
    source_candidate = (source_root() / candidate).resolve()
    return source_candidate if source_candidate.exists() else resolved


def materialize_verifier_specs(
    specs: dict[str, dict[str, Any]], script_root: str | Path
) -> dict[str, dict[str, Any]]:
    materialized = deepcopy(specs)
    for spec in materialized.values():
        verification_script = spec.get("verification_script")
        if isinstance(verification_script, str) and verification_script:
            spec["verification_script"] = str(resolve_script_path(verification_script, script_root))
    return materialized
