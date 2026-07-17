"""Shared CLI helper for ADMET-AI property verifier scripts."""

from __future__ import annotations

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.admet_ai.backend import evaluate_admet_ai_constraint
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.property_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_admet_ai_constraint,
        sort_keys=True,
    )


__all__ = ["main"]
