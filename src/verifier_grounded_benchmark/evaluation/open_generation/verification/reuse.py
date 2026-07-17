"""Evidence reuse keys that exclude all scoring state."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def evidence_reuse_key(
    candidate: Mapping[str, Any], spec: Mapping[str, Any]
) -> tuple[str, str, str, str]:
    verifier_id = str(spec["verifier_id"])
    executor = spec.get("executor")
    if isinstance(executor, Mapping):
        entrypoint = str(executor.get("module"))
    else:
        entrypoint = str(spec.get("verification_script"))
    candidate_hash = _hash(candidate)
    protocol = {
        key: value for key, value in spec.items()
        if key not in {"timeout_seconds", "resources", "scoring"}
    }
    return verifier_id, entrypoint, candidate_hash, _hash(protocol)


def _hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()
