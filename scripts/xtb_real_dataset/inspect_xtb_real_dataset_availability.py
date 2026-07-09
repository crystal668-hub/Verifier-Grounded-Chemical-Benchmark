#!/usr/bin/env python
"""Inspect local and optional remote availability for xTB real datasets."""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data" / "xtb_real_dataset_sources.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--check-remote", action="store_true")
    parser.add_argument("--remote-timeout", type=float, default=10.0)
    return parser.parse_args()


def cache_path_for(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


def declared_file_urls(access: dict[str, Any]) -> dict[str, str]:
    urls: dict[str, str] = {}
    for file_name, metadata in (access.get("small_validation_files") or {}).items():
        if isinstance(metadata, dict) and metadata.get("url") is not None:
            urls[file_name] = str(metadata["url"])
    urls.update(access.get("files") or {})
    return urls


def local_file_status(cache_path: Path, files: dict[str, str]) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for file_name in sorted(files):
        path = cache_path / file_name
        statuses[file_name] = {
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
    return statuses


def remote_head(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "status": "ok",
                "http_status": response.status,
                "content_length": response.headers.get("Content-Length"),
            }
    except Exception as exc:  # noqa: BLE001 - diagnostics must preserve access failures.
        return {"status": "error", "message": str(exc)}


def inspect_manifest(manifest_path: Path, *, check_remote: bool, remote_timeout: float) -> dict[str, Any]:
    with manifest_path.open() as handle:
        manifest = yaml.safe_load(handle)

    sources: dict[str, Any] = {}
    for source_name, source in sorted((manifest.get("sources") or {}).items()):
        access = source.get("access") or {}
        files = declared_file_urls(access)
        cache_path = cache_path_for(str(source.get("cache_path", "")))
        source_status: dict[str, Any] = {
            "status": source.get("status"),
            "cache_path": str(cache_path),
            "access_type": access.get("type"),
            "access_status": access.get("status"),
            "conversion": access.get("conversion"),
            "local_files": local_file_status(cache_path, files),
        }
        if check_remote:
            source_status["remote_files"] = {
                file_name: remote_head(url, remote_timeout) for file_name, url in sorted(files.items())
            }
        sources[source_name] = source_status

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(manifest_path),
        "remote_checked": check_remote,
        "sources": sources,
    }


def main() -> int:
    args = parse_args()
    payload = inspect_manifest(args.source_manifest, check_remote=args.check_remote, remote_timeout=args.remote_timeout)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
