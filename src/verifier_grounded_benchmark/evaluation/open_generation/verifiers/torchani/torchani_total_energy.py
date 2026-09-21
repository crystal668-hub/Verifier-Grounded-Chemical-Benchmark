"""JSON verifier entry point for torchani_total_energy_hartree using TorchANI."""

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.torchani.cli import (
    main,
)

if __name__ == "__main__":
    main("torchani_total_energy_hartree")
