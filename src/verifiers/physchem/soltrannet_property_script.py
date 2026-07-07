"""Shared CLI helper for SolTranNet property verifier scripts."""

from __future__ import annotations

from verifiers.backends.soltrannet_properties import evaluate_soltrannet_constraint
from verifiers.script_cli import run_property_script


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_soltrannet_constraint,
        sort_keys=True,
    )


__all__ = ["main"]
