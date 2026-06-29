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
from verifier_grounded_benchmark import load_track

DEFAULT_TASKS_PATH = Path("tasks/rdkit_baseline/tasks.yaml")
DEFAULT_SPECS_PATH = Path("tasks/rdkit_baseline/verifier_specs.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track")
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--specs", type=Path)
    parser.add_argument("--answers", required=True, type=Path)
    args = parser.parse_args()
    if args.track and (args.tasks is not None or args.specs is not None):
        parser.error("--track cannot be combined with --tasks or --specs")
    return args


def main() -> None:
    args = parse_args()
    answers = load_answers_jsonl(args.answers)
    if args.track:
        report = load_track(args.track).evaluate_answers(answers)
    else:
        report = evaluate_many(
            answers,
            load_tasks(args.tasks or DEFAULT_TASKS_PATH),
            load_verifier_specs(args.specs or DEFAULT_SPECS_PATH),
        )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
