"""Score answer JSONL files through configured verifier scripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from verifier_grounded_benchmark import load_track
from verifier_grounded_benchmark.evaluation import EvaluationEngine
from verifier_grounded_benchmark.evaluation.io import load_answers_jsonl_file
from verifier_grounded_benchmark.task.loader import (
    load_tasks_file,
    load_verifier_specs_file,
    task_pack_from_mappings,
)
from verifier_grounded_benchmark.task.models import TaskPack
from verifier_grounded_benchmark.task.resources import materialize_verifier_specs


def load_development_task_pack(
    tasks_path: Path,
    specs_path: Path,
    *,
    script_root: Path | None = None,
) -> TaskPack:
    resolved_script_root = script_root or specs_path.resolve().parent
    specs = load_verifier_specs_file(specs_path)
    return task_pack_from_mappings(
        load_tasks_file(tasks_path),
        materialize_verifier_specs(specs, script_root=resolved_script_root),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--track",
        help="Public scoring path for built-in benchmark tracks.",
    )
    parser.add_argument(
        "--tasks",
        type=Path,
        help="Development-only override for maintaining task packs.",
    )
    parser.add_argument(
        "--specs",
        type=Path,
        help="Development-only verifier spec override for maintaining task packs.",
    )
    parser.add_argument("--answers", required=True, type=Path)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit with an error unless submitted answers cover every task exactly once.",
    )
    args = parser.parse_args(argv)
    if args.track and (args.tasks is not None or args.specs is not None):
        parser.error("--track cannot be combined with --tasks or --specs")
    if (args.tasks is None) != (args.specs is None):
        parser.error("--tasks and --specs must be provided together")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    answers = load_answers_jsonl_file(args.answers)
    if args.track:
        report = load_track(args.track).evaluate_answers(answers)
    elif args.tasks is None:
        report = load_track("rdkit").evaluate_answers(answers)
    else:
        assert args.specs is not None
        pack = load_development_task_pack(
            args.tasks,
            args.specs,
            script_root=args.specs.resolve().parent,
        )
        report = EvaluationEngine(pack).evaluate_many(answers).to_dict()

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
