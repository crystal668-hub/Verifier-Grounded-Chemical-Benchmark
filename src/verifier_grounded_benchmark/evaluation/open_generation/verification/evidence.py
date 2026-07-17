"""Score-free verifier evidence model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


EvidenceOutcome = Literal["verified", "candidate_rejected", "evaluation_failed"]


@dataclass(frozen=True)
class VerificationEvidence:
    outcome: EvidenceOutcome
    task_id: str
    verifier_id: str
    canonical_candidate: dict[str, Any]
    properties: dict[str, Any]
    diagnostics: dict[str, Any] = field(default_factory=dict)
    versions: dict[str, Any] = field(default_factory=dict)
    failure_type: str | None = None
    message: str | None = None
    failure_scope: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "task_id": self.task_id,
            "verifier_id": self.verifier_id,
            "canonical_candidate": self.canonical_candidate,
            "properties": self.properties,
            "diagnostics": self.diagnostics,
            "versions": self.versions,
            "failure_type": self.failure_type,
            "message": self.message,
            "failure_scope": self.failure_scope,
        }
