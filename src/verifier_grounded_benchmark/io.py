"""Deprecated compatibility imports for task and answer I/O."""

from verifier_grounded_benchmark.task.loader import (
    load_answers_jsonl_file,
    load_tasks_file,
    load_verifier_specs_file,
)

__all__ = ["load_answers_jsonl_file", "load_tasks_file", "load_verifier_specs_file"]
