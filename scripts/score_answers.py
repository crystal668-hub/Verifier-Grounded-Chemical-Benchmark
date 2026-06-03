#!/usr/bin/env python
"""Score answer JSONL files through configured verifier scripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.evaluate import evaluate_many, load_answers_jsonl, load_tasks, load_verifier_specs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="tasks/rdkit_baseline/tasks.yaml", type=Path)
    parser.add_argument("--specs", default="tasks/rdkit_baseline/verifier_specs.yaml", type=Path)
    parser.add_argument("--answers", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = evaluate_many(
        load_answers_jsonl(args.answers),
        load_tasks(args.tasks),
        load_verifier_specs(args.specs),
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
