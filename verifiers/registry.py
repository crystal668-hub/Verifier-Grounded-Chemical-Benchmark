"""Legacy verifier registry used only for experimental specs that do not yet define verification_script."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from verifiers.atomisticskills import (
    evaluate_base_supercell as evaluate_atomisticskills_base_supercell,
)
from verifiers.atomisticskills import (
    evaluate_drugdisc_descriptors as evaluate_atomisticskills_drugdisc_descriptors,
)
from verifiers.atomisticskills import evaluate_xrd_peak as evaluate_atomisticskills_xrd_peak
from verifiers.small_molecule_rdkit import evaluate_answer as evaluate_small_molecule_rdkit

VerifierCallable = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]]

VERIFIER_REGISTRY: dict[str, VerifierCallable] = {
    "small_molecule_rdkit_v1": evaluate_small_molecule_rdkit,
    "atomisticskills_base_supercell_mcp_v1": evaluate_atomisticskills_base_supercell,
    "atomisticskills_drugdisc_descriptors_mcp_v1": evaluate_atomisticskills_drugdisc_descriptors,
    "atomisticskills_xrd_peak_script_v1": evaluate_atomisticskills_xrd_peak,
}


class UnknownVerifierError(KeyError):
    """Raised when a verifier_id is not present in the explicit registry."""


def get_verifier(verifier_id: str) -> VerifierCallable:
    try:
        return VERIFIER_REGISTRY[verifier_id]
    except KeyError as exc:
        raise UnknownVerifierError(f"unknown verifier_id: {verifier_id}") from exc
