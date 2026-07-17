"""Logical property verifier protocol."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from verifier_grounded_benchmark.evaluation.open_generation.verification.evidence import (
    VerificationEvidence,
)


class PropertyVerifier(Protocol):
    def verify(
        self,
        candidate: dict[str, Any],
        task: Mapping[str, Any],
        constraint: Mapping[str, Any],
        spec: Mapping[str, Any],
    ) -> VerificationEvidence: ...
