"""Shared CLI helper for RDKit descriptor verifier scripts."""

from __future__ import annotations

from verifiers.backends.rdkit_descriptors import evaluate_descriptor_constraint
from verifiers.common.property_cli import run_property_script


def main(descriptor: str) -> None:
    run_property_script(
        expected_name=descriptor,
        spec_field="descriptor",
        mismatch_label="descriptor",
        evaluator=evaluate_descriptor_constraint,
        sort_keys=True,
    )
