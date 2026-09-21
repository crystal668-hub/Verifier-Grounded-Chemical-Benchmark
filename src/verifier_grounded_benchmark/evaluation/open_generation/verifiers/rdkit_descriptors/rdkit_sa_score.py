"""JSON verifier entry point for sa_score using RDKit descriptor."""

from __future__ import annotations

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.rdkit_descriptors.cli import (
    main,
)

if __name__ == "__main__":
    main("sa_score")
