"""Evaluation runtime configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationConfig:
    fail_fast: bool = False
