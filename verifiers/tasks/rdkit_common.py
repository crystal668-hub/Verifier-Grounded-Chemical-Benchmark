from __future__ import annotations

import json
import sys
from typing import Any

from verifiers.backends.rdkit_descriptors import evaluate_candidate


def main() -> None:
    payload: dict[str, Any] = json.load(sys.stdin)
    result = evaluate_candidate(payload.get("candidate", {}), payload.get("task", {}), payload.get("verifier_spec", {}))
    json.dump(result, sys.stdout, sort_keys=True)
