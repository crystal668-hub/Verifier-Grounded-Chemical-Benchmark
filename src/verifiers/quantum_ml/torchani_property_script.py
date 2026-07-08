"""Shared CLI helper for native TorchANI property verifier scripts."""

from __future__ import annotations

from verifiers.backends.torchani_properties import evaluate_torchani_constraint
from verifiers.common.property_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_torchani_constraint,
        sort_keys=True,
    )
