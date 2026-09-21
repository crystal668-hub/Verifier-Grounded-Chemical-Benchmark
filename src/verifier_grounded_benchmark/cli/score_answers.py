"""Score answer JSONL files using verifiers or reference gold answers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from verifier_grounded_benchmark import load_track
from verifier_grounded_benchmark.evaluation import EvaluationEngine
from verifier_grounded_benchmark.evaluation.external_dependencies import (
    ExternalDependencyError,
    preflight_external_dependencies,
    verifier_specs_for_answers,
)
from verifier_grounded_benchmark.evaluation.io import load_answers_jsonl_file
from verifier_grounded_benchmark.task.loader import (
    load_task_pack,
)
from verifier_grounded_benchmark.task.models import TaskPack


def load_development_task_pack(
    tasks_path: Path,
    specs_path: Path | None = None,
    *,
    script_root: Path | None = None,
    scoring_path: Path | None = None,
) -> TaskPack:
    """Load a custom task pack; verifier specs are optional for property-only packs."""
    return load_task_pack(
        tasks_path,
        specs_path,
        scoring_path,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI options and reject incomplete or conflicting track/pack selections."""
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
    parser.add_argument(
        "--scoring",
        type=Path,
        help="Development-only scoring config override for maintaining task packs.",
    )
    parser.add_argument("--answers", required=True, type=Path)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit with an error unless submitted answers cover every task exactly once.",
    )
    args = parser.parse_args(argv)
    if args.track and any(x is not None for x in (args.tasks, args.specs, args.scoring)):
        parser.error("--track cannot be combined with --tasks, --specs, or --scoring")
    if (args.tasks is None) != (args.scoring is None):
        parser.error("--tasks and --scoring must be provided together")
    if args.specs is not None and args.tasks is None:
        parser.error("--specs requires --tasks and --scoring")
    return args


def main(argv: list[str] | None = None) -> int:
    """Score a JSONL submission; return 2 on dependency or required-coverage failure."""
    args = parse_args(argv)
    answers = load_answers_jsonl_file(args.answers)
    pack: TaskPack | None = None
    if args.track:
        track = load_track(args.track)
        tasks_by_id = track._task_pack.tasks_by_id
        specs_by_id = track.verifier_specs_by_id
    elif args.tasks is None:
        track = load_track("open_generation_rdkit")
        tasks_by_id = track._task_pack.tasks_by_id
        specs_by_id = track.verifier_specs_by_id
    else:
        assert args.scoring is not None
        pack = load_development_task_pack(
            args.tasks,
            args.specs,
            script_root=args.specs.resolve().parent if args.specs is not None else None,
            scoring_path=args.scoring,
        )
        tasks_by_id = pack.tasks_by_id
        specs_by_id = pack.verifier_specs_by_id

    required_specs = verifier_specs_for_answers(tasks_by_id, specs_by_id, answers)
    try:
        if required_specs:
            preflight_external_dependencies(required_specs)
    except ExternalDependencyError as exc:
        print(
            json.dumps(
                {
                    "error": "verifier_environment_error",
                    "message": "verifier dependency preflight failed",
                    "dependencies": exc.checks,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    if pack is None:
        report = track.evaluate_answers(answers)
    else:
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
