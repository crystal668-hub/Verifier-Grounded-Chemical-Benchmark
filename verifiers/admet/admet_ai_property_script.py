"""Shared CLI helper for ADMET-AI property verifier scripts."""

from __future__ import annotations

from verifiers.backends.admet_ai_properties import evaluate_admet_ai_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_admet_ai_constraint,
        sort_keys=True,
    )


__all__ = ["main"]
