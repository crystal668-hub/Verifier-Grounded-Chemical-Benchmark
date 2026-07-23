from __future__ import annotations

import json
import sys

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.crest_pyrene import (
    evaluate_pyrene_energy_constraint,
)


def main() -> None:
    payload = json.load(sys.stdin)
    result = evaluate_pyrene_energy_constraint(
        payload.get("candidate", {}),
        payload.get("task", {}),
        payload.get("constraint", {}),
        payload.get("verifier_spec", {}),
    )
    json.dump(result, sys.stdout, sort_keys=True)


if __name__ == "__main__":
    main()
