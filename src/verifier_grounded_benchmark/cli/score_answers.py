"""Score answer JSONL files through configured verifier scripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from benchmark.evaluate import (
    evaluate_many,
    load_answers_jsonl,
)
from verifier_grounded_benchmark import load_track
from verifier_grounded_benchmark.io import load_tasks_file, load_verifier_specs_file
from verifier_grounded_benchmark.resources import materialize_verifier_specs

DEFAULT_TASKS_PATH = Path("tasks/rdkit_baseline/tasks.yaml")
DEFAULT_SPECS_PATH = Path("tasks/rdkit_baseline/verifier_specs.yaml")


def load_development_task_pack(
    tasks_path: Path,
    specs_path: Path,
    *,
    script_root: Path | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    resolved_script_root = script_root or specs_path.resolve().parent
    specs = load_verifier_specs_file(specs_path)
    return (
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
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    answers = load_answers_jsonl(args.answers)
    if args.track:
        report = load_track(args.track).evaluate_answers(answers)
    else:
        specs_path = args.specs or DEFAULT_SPECS_PATH
        script_root = specs_path.resolve().parent if args.specs is not None else Path.cwd()
        tasks, specs = load_development_task_pack(
            args.tasks or DEFAULT_TASKS_PATH,
            specs_path,
            script_root=script_root,
        )
        report = evaluate_many(
            answers,
            tasks,
            specs,
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
