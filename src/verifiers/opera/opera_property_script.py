"""Shared CLI helper for OPERA property verifier scripts."""

from __future__ import annotations

from verifiers.backends.opera_properties import evaluate_opera_constraint
from verifiers.common.property_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_opera_constraint,
        sort_keys=True,
    )


__all__ = ["main"]
