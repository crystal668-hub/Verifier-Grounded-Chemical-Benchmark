"""Submitted task coverage analysis."""

from __future__ import annotations

from typing import Any


def summarize_coverage(
    answers: list[dict[str, Any]], task_ids: list[str]
) -> dict[str, Any]:
    task_id_set = set(task_ids)
    submitted_ids = [
        answer.get("task_id")
        for answer in answers
        if isinstance(answer.get("task_id"), str) and answer.get("task_id")
    ]
    submitted_set = set(submitted_ids)
    duplicate_ids = sorted(
        task_id for task_id in submitted_set if submitted_ids.count(task_id) > 1
    )
    unknown_ids = sorted(submitted_set - task_id_set)
    answered_known = submitted_set & task_id_set
    missing_ids = [task_id for task_id in task_ids if task_id not in answered_known]
    return {
        "num_tasks_total": len(task_ids),
        "num_rows_submitted": len(answers),
        "num_task_ids_submitted": len(submitted_set),
        "num_tasks_answered": len(answered_known),
        "missing_task_ids": missing_ids,
        "duplicate_task_ids": duplicate_ids,
        "unknown_task_ids": unknown_ids,
        "complete": not missing_ids and not duplicate_ids and not unknown_ids,
    }
