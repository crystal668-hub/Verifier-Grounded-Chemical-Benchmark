"""Shared CLI helper for MACE material property verifier scripts."""

from __future__ import annotations

from verifiers.backends.mace_properties import evaluate_mace_property_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_mace_property_constraint,
        sort_keys=True,
    )
