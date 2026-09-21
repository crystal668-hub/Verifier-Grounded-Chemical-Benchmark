"""Evaluation runtime configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationConfig:
    """Runtime evaluation options; fail_fast raises on evaluator errors, not zero scores."""
    fail_fast: bool = False
