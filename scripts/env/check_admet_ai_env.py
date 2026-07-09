#!/usr/bin/env python
"""Smoke-check the ADMET-AI verifier environment."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata as metadata
import io
import json
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINTS = ["Solubility_AqSolDB", "hERG", "AMES", "BBB_Martins", "Caco2_Wang"]


def directory_fingerprint(path: Path | str) -> str:
    root = Path(path)
    digest = hashlib.sha256()
    for file_path in sorted(root.rglob("*")):
        if file_path.is_file():
            digest.update(str(file_path.relative_to(root)).encode())
            digest.update(b"\0")
            with file_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest()


def quiet_predict(model: Any, smiles: str) -> dict[str, float]:
    predictions = model.predict(smiles=smiles)
    return {str(key): float(value) for key, value in dict(predictions).items()}


def load_admet_smoke(smiles: str) -> tuple[Any, dict[str, float], Path, Path]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        from admet_ai import ADMETModel
        from admet_ai.constants import DEFAULT_ADMET_PATH, DEFAULT_MODELS_DIR

        model = ADMETModel(include_physchem=False, drugbank_path=None, num_workers=0)
        predictions = quiet_predict(model, smiles)
    return model, predictions, DEFAULT_ADMET_PATH, DEFAULT_MODELS_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smiles", default="CCO")
    args = parser.parse_args()

    model, predictions, default_admet_path, default_models_dir = load_admet_smoke(args.smiles)
    selected_properties = {
        endpoint: predictions[endpoint] for endpoint in DEFAULT_ENDPOINTS if endpoint in predictions
    }

    payload = {
        "status": "ok",
        "versions": {
            "admet-ai": metadata.version("admet-ai"),
            "chemprop": metadata.version("chemprop"),
            "torch": metadata.version("torch"),
        },
        "models": {
            "models_dir": str(default_models_dir),
            "models_dir_fingerprint": directory_fingerprint(default_models_dir),
            "admet_metadata": str(default_admet_path),
            "num_ensembles": model.num_ensembles,
            "task_group_sizes": [len(tasks) for tasks in model.task_lists],
            "tasks": model.task_lists,
        },
        "prediction": {
            "smiles": args.smiles,
            "num_properties": len(predictions),
            "properties": selected_properties,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
