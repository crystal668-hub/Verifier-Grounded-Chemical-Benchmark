"""Evaluation failure scopes and stable failure-result semantics."""

from __future__ import annotations

from typing import Literal


FailureScope = Literal["candidate", "submission", "task", "infrastructure"]

CANDIDATE_FAILURE = "candidate"
SUBMISSION_FAILURE = "submission"
TASK_FAILURE = "task"
INFRASTRUCTURE_FAILURE = "infrastructure"
