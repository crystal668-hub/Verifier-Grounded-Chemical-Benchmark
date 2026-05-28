"""Explicit verifier registry for routing task answers to verifier code."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from verifiers.small_molecule_rdkit import evaluate_answer as evaluate_small_molecule_rdkit

VerifierCallable = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]]

VERIFIER_REGISTRY: dict[str, VerifierCallable] = {
    "small_molecule_rdkit_v1": evaluate_small_molecule_rdkit,
}


class UnknownVerifierError(KeyError):
    """Raised when a verifier_id is not present in the explicit registry."""


def get_verifier(verifier_id: str) -> VerifierCallable:
    try:
        return VERIFIER_REGISTRY[verifier_id]
    except KeyError as exc:
        raise UnknownVerifierError(f"unknown verifier_id: {verifier_id}") from exc

