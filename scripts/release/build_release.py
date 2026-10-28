from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import Any

import yaml
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.registry import builtin_definitions

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "verifier-grounded-benchmark"
ARCHIVE_PACKAGES = ("verifier_grounded_benchmark", "vgb")
FORMAL_TRACK_PATHS = {
    "open_generation_rdkit": ROOT / "src" / "verifier_grounded_benchmark" / "task" / "packs" / "open_generation_rdkit" / "tasks.yaml",
    "open_generation_xtb": ROOT / "src" / "verifier_grounded_benchmark" / "task" / "packs" / "open_generation_xtb" / "tasks.yaml",
    "property_calculation_advanced": ROOT / "src" / "verifier_grounded_benchmark" / "task" / "packs" / "property_calculation_advanced" / "tasks.yaml",
    "property_calculation_basic": ROOT / "src" / "verifier_grounded_benchmark" / "task" / "packs" / "property_calculation_basic" / "tasks.yaml",
}


def project_version() -> str:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    raw = str(payload["project"]["version"])
    try:
        normalized = str(Version(raw))
    except InvalidVersion as exc:
        raise ValueError(f"Invalid project version: {raw!r}") from exc
    if raw != normalized:
        raise ValueError(f"Project version must be canonical: {raw!r}; use {normalized!r}")
    return normalized


def task_inventory(version: str) -> dict[str, Any]:
    tracks: dict[str, Any] = {}
    scoring_profiles: dict[str, Any] = {}
    scoring_versions: set[str] = set()
    definitions = {definition.name: definition for definition in builtin_definitions()}
    for track, path in FORMAL_TRACK_PATHS.items():
        specs_path = path.parent / "verifier_specs.yaml"
        pack = load_task_pack(
            path, specs_path if track.startswith("open_generation_") else None,
            path.parent / "scoring.yaml",
        )
        if pack.pack_id != track or pack.version != version or definitions[track].version != version:
            raise ValueError(f"Release version/identity mismatch for {track}: expected {version}")
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        tasks = payload.get("tasks") if isinstance(payload, dict) else None
        if not isinstance(tasks, list):
            raise ValueError(f"Invalid task pack: {path}")
        task_ids = [str(task["task_id"]) for task in tasks if isinstance(task, dict)]
        if len(task_ids) != len(tasks) or len(task_ids) != len(set(task_ids)):
            raise ValueError(f"Invalid or duplicate task IDs in {path}")
        task_pack = payload.get("task_pack")
        if not isinstance(task_pack, dict):
            raise ValueError(f"Invalid task-pack metadata: {path}")
        scoring_payload = yaml.safe_load((path.parent / "scoring.yaml").read_text(encoding="utf-8"))
        scoring_config = scoring_payload.get("scoring_config")
        if not isinstance(scoring_config, dict):
            raise ValueError(f"Invalid scoring config: {path.parent / 'scoring.yaml'}")
        scoring_version = str(scoring_config["scoring_version"])
        scoring_versions.add(scoring_version)
        tracks[track] = {
            "count": len(task_ids),
            "task_ids": task_ids,
            "tasks_sha256": sha256_file(path),
            "scoring_sha256": sha256_file(path.parent / "scoring.yaml"),
            "task_pack_version": payload["task_pack"]["version"],
            "scoring_version": scoring_version,
            "scoring_status": scoring_config.get("scoring_status", "formal"),
        }
        if specs_path.is_file():
            tracks[track]["verifier_specs_sha256"] = sha256_file(specs_path)
        for profile_id, profile in scoring_payload["scoring_profiles"].items():
            encoded = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()
            profile_hash = hashlib.sha256(encoded).hexdigest()
            existing = scoring_profiles.get(profile_id)
            if existing is not None and existing["sha256"] != profile_hash:
                raise ValueError(f"Conflicting scoring profile: {profile_id}")
            scoring_profiles[profile_id] = {
                "definition": profile,
                "sha256": profile_hash,
            }
    if len(scoring_versions) != 1:
        raise ValueError(f"Formal task packs must share one scoring version: {sorted(scoring_versions)}")
    return {
        "schema_version": 2,
        "package_version": version,
        "result_schema_version": "3",
        "scoring_version": scoring_versions.pop(),
        "tracks": tracks,
        "scoring_profiles": scoring_profiles,
    }


def normalized_release_payloads(
    wheel_path: Path,
    sdist_path: Path,
    *,
    archive_packages: tuple[str, ...] = ARCHIVE_PACKAGES,
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    wheel_payloads: dict[str, bytes] = {}
    with zipfile.ZipFile(wheel_path) as archive:
        for name in archive.namelist():
            normalized = _normalized_wheel_member(name, archive_packages)
            if normalized is not None:
                wheel_payloads[normalized] = archive.read(name)

    sdist_payloads: dict[str, bytes] = {}
    with tarfile.open(sdist_path, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            relative = "/".join(Path(member.name).parts[1:])
            if not _is_release_payload(relative, archive_packages):
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"Unable to read sdist member: {member.name}")
            sdist_payloads[relative] = extracted.read()
    return wheel_payloads, sdist_payloads


def verify_archive_payloads(
    wheel_path: Path,
    sdist_path: Path,
    *,
    additional_required: set[str] | None = None,
) -> dict[str, Any]:
    wheel_payloads, sdist_payloads = normalized_release_payloads(wheel_path, sdist_path)
    if wheel_payloads != sdist_payloads:
        wheel_only = sorted(wheel_payloads.keys() - sdist_payloads.keys())
        sdist_only = sorted(sdist_payloads.keys() - wheel_payloads.keys())
        changed = sorted(
            path
            for path in wheel_payloads.keys() & sdist_payloads.keys()
            if wheel_payloads[path] != sdist_payloads[path]
        )
        raise ValueError(
            "Wheel/sdist release payload mismatch: "
            f"wheel_only={wheel_only}, sdist_only={sdist_only}, changed={changed}"
        )
    required = {
        "src/verifier_grounded_benchmark/README.md",
        "src/verifier_grounded_benchmark/task/packs/open_generation_rdkit/tasks.yaml",
        "src/verifier_grounded_benchmark/task/packs/open_generation_rdkit/verifier_specs.yaml",
        "src/verifier_grounded_benchmark/task/packs/open_generation_xtb/tasks.yaml",
        "src/verifier_grounded_benchmark/task/packs/open_generation_xtb/verifier_specs.yaml",
    }
    required.update(additional_required or ())
    missing = sorted(required - wheel_payloads.keys())
    if missing:
        raise ValueError(f"Release payload is missing required files: {missing}")
    return {
        "file_count": len(wheel_payloads),
        "sha256": payload_digest(wheel_payloads),
    }


def release_preflight(*, output_dir: Path, metadata_dir: Path, tag: str) -> dict[str, Any]:
    """Validate immutable release identity and destinations without writing files."""
    version = project_version()
    _require_clean_worktree()
    source_commit = _git("rev-parse", "HEAD")
    _validate_release_tag(tag, source_commit)
    _require_new_destinations(output_dir, metadata_dir, version)
    inventory = task_inventory(version)
    _require_formal_inventory(inventory)
    return {
        "version": version,
        "tag": tag,
        "canonical_source": {
            "commit": source_commit,
            "tree": _git("rev-parse", "HEAD^{tree}"),
            "source_date_epoch": int(_git("show", "-s", "--format=%ct", "HEAD")),
        },
        "inventory": inventory,
    }


def _validate_release_tag(tag: str, source_commit: str) -> None:
    if not tag or tag.startswith("-"):
        raise ValueError("An explicit Git release tag is required")
    try:
        _git("check-ref-format", f"refs/tags/{tag}")
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"Invalid release tag: {tag!r}") from exc
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode == 0 and result.stdout.strip() != source_commit:
        raise RuntimeError(f"Release tag {tag!r} already points to another commit")


def _require_new_destinations(output_dir: Path, metadata_dir: Path, version: str) -> None:
    output_dir, metadata_dir = output_dir.resolve(), metadata_dir.resolve()
    if output_dir == metadata_dir or output_dir in metadata_dir.parents or metadata_dir in output_dir.parents:
        raise ValueError("Artifact and metadata directories must not overlap")
    if metadata_dir.exists() or metadata_dir.is_symlink():
        raise FileExistsError(f"Refusing to replace release metadata: {metadata_dir}")
    if output_dir.exists() and not output_dir.is_dir():
        raise FileExistsError(f"Artifact destination is not a directory: {output_dir}")
    for name in (f"verifier_grounded_benchmark-{version}-py3-none-any.whl",
                 f"verifier_grounded_benchmark-{version}.tar.gz"):
        destination = output_dir / name
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Refusing to overwrite release artifact: {destination}")


def _verify_artifact_versions(wheel_path: Path, sdist_path: Path, version: str) -> None:
    name, wheel_version, _build, _tags = parse_wheel_filename(wheel_path.name)
    if name != canonicalize_name(PACKAGE_NAME) or str(wheel_version) != version:
        raise ValueError("Wheel filename does not match the release identity")
    with zipfile.ZipFile(wheel_path) as archive:
        metadata = [item for item in archive.namelist() if item.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("Wheel must contain exactly one distribution METADATA")
        wheel_info = BytesParser().parsebytes(archive.read(metadata[0]))
    with tarfile.open(sdist_path, "r:gz") as archive:
        metadata = [item for item in archive.getmembers()
                    if len(Path(item.name).parts) == 2 and Path(item.name).name == "PKG-INFO"]
        if len(metadata) != 1:
            raise ValueError("Sdist must contain one root PKG-INFO")
        handle = archive.extractfile(metadata[0])
        if handle is None:
            raise ValueError("Unable to read sdist PKG-INFO")
        sdist_info = BytesParser().parsebytes(handle.read())
    for info in (wheel_info, sdist_info):
        if info.get("Version") != version or canonicalize_name(info.get("Name", "")) != canonicalize_name(PACKAGE_NAME):
            raise ValueError("Artifact metadata does not match the release identity")


def build_release(*, output_dir: Path, metadata_dir: Path, tag: str) -> dict[str, Any]:
    """Stage and verify a release, then create new artifacts without overwriting history."""
    state = release_preflight(output_dir=output_dir, metadata_dir=metadata_dir, tag=tag)
    version, inventory = state["version"], state["inventory"]
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = str(state["canonical_source"]["source_date_epoch"])
    with tempfile.TemporaryDirectory(prefix="vgb-release-") as temporary:
        staging = Path(temporary)
        subprocess.run(
            ["uv", "build", "--wheel", "--sdist", "--out-dir", str(staging)],
            cwd=ROOT, env=env, check=True,
        )
        wheel_path = staging / f"verifier_grounded_benchmark-{version}-py3-none-any.whl"
        sdist_path = staging / f"verifier_grounded_benchmark-{version}.tar.gz"
        if not wheel_path.is_file() or not sdist_path.is_file():
            raise FileNotFoundError("Expected canonical wheel and sdist were not both created")
        _verify_artifact_versions(wheel_path, sdist_path, version)
        required = set()
        for track in FORMAL_TRACK_PATHS:
            folder = f"src/verifier_grounded_benchmark/task/packs/{track}"
            required.update(f"{folder}/{name}" for name in ("tasks.yaml", "scoring.yaml"))
            if track.startswith("open_generation_"):
                required.add(f"{folder}/verifier_specs.yaml")
        payload = verify_archive_payloads(wheel_path, sdist_path, additional_required=required)
        artifacts = [
            {"filename": path.name, "sha256": sha256_file(path), "size": path.stat().st_size}
            for path in (wheel_path, sdist_path)
        ]
        manifest = {
            "schema_version": 1, "package": PACKAGE_NAME, "version": version,
            "result_schema_version": "3", "scoring_version": inventory["scoring_version"],
            "tag": tag, "canonical_source": state["canonical_source"],
            "artifacts": artifacts, "verified_payload": payload,
            "task_inventory": "task-inventory.json",
        }
        staged_metadata = staging / "metadata"
        staged_metadata.mkdir()
        _write_json(staged_metadata / "manifest.json", manifest)
        _write_json(staged_metadata / "task-inventory.json", inventory)
        (staged_metadata / "SHA256SUMS").write_text(
            "".join(f"{item['sha256']}  {item['filename']}\n" for item in artifacts), encoding="ascii",
        )
        _require_clean_worktree()
        if _git("rev-parse", "HEAD") != state["canonical_source"]["commit"]:
            raise RuntimeError("Source commit changed while building the release")
        _validate_release_tag(tag, state["canonical_source"]["commit"])
        _require_new_destinations(output_dir, metadata_dir, version)
        _publish_new_files((wheel_path, sdist_path), staged_metadata, output_dir, metadata_dir)
    return manifest


def _publish_new_files(artifacts, staged_metadata: Path, output_dir: Path, metadata_dir: Path) -> None:
    """Create files exclusively; roll back only files this invocation created on failure."""
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.parent.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(exist_ok=False)
    created: list[Path] = []
    try:
        pairs = [(source, output_dir / source.name) for source in artifacts]
        pairs.extend((source, metadata_dir / source.name) for source in staged_metadata.iterdir())
        for source, destination in pairs:
            with destination.open("xb") as output:
                created.append(destination)
                with source.open("rb") as input_file:
                    shutil.copyfileobj(input_file, output)
    except Exception:
        for path in reversed(created):
            path.unlink()
        if not any(metadata_dir.iterdir()):
            metadata_dir.rmdir()
        raise


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_digest(payloads: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path, content in sorted(payloads.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def _normalized_wheel_member(
    name: str, archive_packages: tuple[str, ...] = ARCHIVE_PACKAGES
) -> str | None:
    if name.startswith("tasks/"):
        return name
    if any(name.startswith(f"{package}/") for package in archive_packages):
        return f"src/{name}"
    return None


def _is_release_payload(
    path: str, archive_packages: tuple[str, ...] = ARCHIVE_PACKAGES
) -> bool:
    if path.startswith("tasks/"):
        return True
    return any(path.startswith(f"src/{package}/") for package in archive_packages)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_clean_worktree() -> None:
    status = _git("status", "--porcelain")
    if status:
        raise RuntimeError("Release builds require a clean Git worktree")


def _require_formal_inventory(inventory: dict[str, Any]) -> None:
    shadow_tracks = sorted(
        track
        for track, payload in inventory["tracks"].items()
        if payload.get("scoring_status", "formal") != "formal"
    )
    if shadow_tracks:
        raise RuntimeError(
            "Release contains task packs with unresolved scoring parameters: "
            + ", ".join(shadow_tracks)
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and attest a verifier-grounded release.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--metadata-dir", type=Path)
    parser.add_argument("--tag", required=True, help="Explicit Git release tag; independent of the Python version.")
    parser.add_argument("--check", action="store_true", help="Validate source, versions, tag and paths without building.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata_dir = args.metadata_dir or ROOT / "releases" / args.tag
    operation = release_preflight if args.check else build_release
    result = operation(
        output_dir=args.output_dir.expanduser().resolve(),
        metadata_dir=metadata_dir.expanduser().resolve(), tag=args.tag,
    )
    if args.check:
        result = {key: value for key, value in result.items() if key != "inventory"}
        result["status"] = "ready_to_build"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
