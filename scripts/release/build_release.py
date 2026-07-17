from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "verifier-grounded-benchmark"
ARCHIVE_PACKAGES = ("verifier_grounded_benchmark", "vgb")
FORMAL_TRACK_PATHS = {
    "rdkit": ROOT / "src" / "verifier_grounded_benchmark" / "task" / "packs" / "rdkit" / "tasks.yaml",
    "xtb": ROOT / "src" / "verifier_grounded_benchmark" / "task" / "packs" / "xtb" / "tasks.yaml",
    "property_calculation": ROOT / "src" / "verifier_grounded_benchmark" / "task" / "packs" / "property_calculation" / "tasks.yaml",
}


def project_version() -> str:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def task_inventory(version: str) -> dict[str, Any]:
    tracks: dict[str, Any] = {}
    scoring_profiles: dict[str, Any] = {}
    for track, path in FORMAL_TRACK_PATHS.items():
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        tasks = payload.get("tasks") if isinstance(payload, dict) else None
        if not isinstance(tasks, list):
            raise ValueError(f"Invalid task pack: {path}")
        task_ids = [str(task["task_id"]) for task in tasks if isinstance(task, dict)]
        if len(task_ids) != len(tasks) or len(task_ids) != len(set(task_ids)):
            raise ValueError(f"Invalid or duplicate task IDs in {path}")
        tracks[track] = {
            "count": len(task_ids),
            "task_ids": task_ids,
            "tasks_sha256": sha256_file(path),
            "task_pack_version": payload["task_pack"]["version"],
            "scoring_version": payload["task_pack"]["scoring_version"],
        }
        for profile_id, profile in payload["scoring_profiles"].items():
            encoded = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()
            profile_hash = hashlib.sha256(encoded).hexdigest()
            existing = scoring_profiles.get(profile_id)
            if existing is not None and existing["sha256"] != profile_hash:
                raise ValueError(f"Conflicting scoring profile: {profile_id}")
            scoring_profiles[profile_id] = {
                "definition": profile,
                "sha256": profile_hash,
            }
    return {
        "schema_version": 2,
        "package_version": version,
        "result_schema_version": "2",
        "scoring_version": "linear_goal_v1",
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


def verify_archive_payloads(wheel_path: Path, sdist_path: Path) -> dict[str, Any]:
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
        "src/verifier_grounded_benchmark/task/packs/rdkit/tasks.yaml",
        "src/verifier_grounded_benchmark/task/packs/rdkit/verifier_specs.yaml",
        "src/verifier_grounded_benchmark/task/packs/xtb/tasks.yaml",
        "src/verifier_grounded_benchmark/task/packs/xtb/verifier_specs.yaml",
        "src/verifier_grounded_benchmark/task/packs/property_calculation/tasks.yaml",
        "src/verifier_grounded_benchmark/task/packs/property_calculation/verifier_specs.yaml",
    }
    missing = sorted(required - wheel_payloads.keys())
    if missing:
        raise ValueError(f"Release payload is missing required files: {missing}")
    return {
        "file_count": len(wheel_payloads),
        "sha256": payload_digest(wheel_payloads),
    }


def build_release(*, output_dir: Path, metadata_dir: Path) -> dict[str, Any]:
    version = project_version()
    _require_clean_worktree()
    source_commit = _git("rev-parse", "HEAD")
    source_tree = _git("rev-parse", "HEAD^{tree}")
    source_date_epoch = _git("show", "-s", "--format=%ct", "HEAD")
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = {
        output_dir / f"verifier_grounded_benchmark-{version}-py3-none-any.whl",
        output_dir / f"verifier_grounded_benchmark-{version}.tar.gz",
    }
    for path in expected:
        path.unlink(missing_ok=True)
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = source_date_epoch
    subprocess.run(
        ["uv", "build", "--wheel", "--sdist", "--out-dir", str(output_dir)],
        cwd=ROOT,
        env=env,
        check=True,
    )
    wheel_path = output_dir / f"verifier_grounded_benchmark-{version}-py3-none-any.whl"
    sdist_path = output_dir / f"verifier_grounded_benchmark-{version}.tar.gz"
    if not wheel_path.is_file() or not sdist_path.is_file():
        raise FileNotFoundError("Expected wheel and sdist were not both created")

    payload = verify_archive_payloads(wheel_path, sdist_path)
    inventory = task_inventory(version)
    artifacts = [
        {
            "filename": path.name,
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in (wheel_path, sdist_path)
    ]
    manifest = {
        "schema_version": 1,
        "package": PACKAGE_NAME,
        "version": version,
        "result_schema_version": "2",
        "scoring_version": "linear_goal_v1",
        "tag": f"v{version}",
        "canonical_source": {
            "commit": source_commit,
            "tree": source_tree,
            "source_date_epoch": int(source_date_epoch),
        },
        "artifacts": artifacts,
        "verified_payload": payload,
        "task_inventory": "task-inventory.json",
        "scoring_profiles": "scoring-profiles.json",
    }
    metadata_dir.mkdir(parents=True, exist_ok=True)
    _write_json(metadata_dir / "manifest.json", manifest)
    _write_json(metadata_dir / "task-inventory.json", inventory)
    _write_json(
        metadata_dir / "scoring-profiles.json",
        {
            "schema_version": 1,
            "package_version": version,
            "scoring_version": inventory["scoring_version"],
            "profiles": inventory["scoring_profiles"],
        },
    )
    (metadata_dir / "SHA256SUMS").write_text(
        "".join(f"{item['sha256']}  {item['filename']}\n" for item in artifacts),
        encoding="ascii",
    )
    return manifest


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and attest a verifier-grounded release.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--metadata-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    version = project_version()
    metadata_dir = args.metadata_dir or ROOT / "releases" / f"v{version}"
    manifest = build_release(
        output_dir=args.output_dir.expanduser().resolve(),
        metadata_dir=metadata_dir.expanduser().resolve(),
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
