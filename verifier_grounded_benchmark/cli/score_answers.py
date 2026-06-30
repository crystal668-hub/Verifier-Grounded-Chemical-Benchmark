"""Score answer JSONL files through configured verifier scripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmark.evaluate import (
    evaluate_many,
    load_answers_jsonl,
    load_tasks,
    load_verifier_specs,
)
from verifier_grounded_benchmark import load_track

DEFAULT_TASKS_PATH = Path("tasks/rdkit_baseline/tasks.yaml")
DEFAULT_SPECS_PATH = Path("tasks/rdkit_baseline/verifier_specs.yaml")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track")
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--specs", type=Path)
    parser.add_argument("--answers", required=True, type=Path)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit with an error unless submitted answers cover every task exactly once.",
    )
    args = parser.parse_args(argv)
    if args.track and (args.tasks is not None or args.specs is not None):
        parser.error("--track cannot be combined with --tasks or --specs")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    answers = load_answers_jsonl(args.answers)
    if args.track:
        report = load_track(args.track).evaluate_answers(answers)
    else:
        report = evaluate_many(
            answers,
            load_tasks(args.tasks or DEFAULT_TASKS_PATH),
            load_verifier_specs(args.specs or DEFAULT_SPECS_PATH),
        )

    if args.require_complete:
        coverage = report.get("summary", {}).get("coverage")
        if isinstance(coverage, dict) and not coverage.get("complete", False):
            print(
                json.dumps(
                    {
                        "error": "incomplete_submission",
                        "coverage": coverage,
                    },
                    indent=2,
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
