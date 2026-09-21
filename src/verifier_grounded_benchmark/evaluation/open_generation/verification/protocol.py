"""Logical property verifier protocol."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from verifier_grounded_benchmark.evaluation.open_generation.verification.evidence import (
    VerificationEvidence,
)


class PropertyVerifier(Protocol):
    """Interface for measuring candidate properties independently of scoring profiles."""
    def verify(
        self,
        candidate: dict[str, Any],
        task: Mapping[str, Any],
        constraint: Mapping[str, Any],
        spec: Mapping[str, Any],
    ) -> VerificationEvidence:
        """Return measured evidence or a classified failure for one candidate and verifier spec."""
        ...
