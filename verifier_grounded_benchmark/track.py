from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from verifier_grounded_benchmark.evaluator import (
    EvaluationConfig,
    EvaluationReport,
    Evaluator,
)
from verifier_grounded_benchmark.io import (
    load_answers_jsonl_file,
    load_tasks_file,
    load_verifier_specs_file,
)
from verifier_grounded_benchmark.registry import TrackDefinition
from verifier_grounded_benchmark.resources import materialize_verifier_specs


class Track:
    def __init__(self, definition: TrackDefinition) -> None:
        self.definition = definition
        self._tasks_by_id = load_tasks_file(
            _resolve_track_path(definition, definition.task_pack_path)
        )
        specs = load_verifier_specs_file(
            _resolve_track_path(definition, definition.verifier_specs_path)
        )
        self._verifier_specs_by_id = materialize_verifier_specs(
            specs,
            script_root=_script_root_for(definition),
        )

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def tasks_by_id(self) -> dict[str, dict[str, Any]]:
        return deepcopy(self._tasks_by_id)

    @property
    def verifier_specs_by_id(self) -> dict[str, dict[str, Any]]:
        return deepcopy(self._verifier_specs_by_id)

    def tasks(self) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self._tasks_by_id.values()]

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self._tasks_by_id[task_id])
        except KeyError as exc:
            raise KeyError(f"Unknown task_id for track {self.name!r}: {task_id}") from exc

    def prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for task in self._tasks_by_id.values():
            prompt = task.get("prompt")
            if isinstance(prompt, str):
                prompts.append(
                    {
                        "track": self.name,
                        "task_id": str(task["task_id"]),
                        "prompt": prompt,
                    }
                )
        return prompts

    def sample_answers(self) -> list[dict[str, Any]]:
        if self.definition.sample_answers_path is None:
            return []
        return load_answers_jsonl_file(
            _resolve_track_path(self.definition, self.definition.sample_answers_path)
        )

    def evaluator(self, *, config: EvaluationConfig | None = None) -> Evaluator:
        return Evaluator(self._tasks_by_id, self._verifier_specs_by_id, config=config)

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        return self.evaluator().evaluate_one(answer)

    def evaluate_answers(
        self,
        answers: list[dict[str, Any]],
        *,
        as_report: bool = False,
    ) -> dict[str, Any] | EvaluationReport:
        return self.evaluator().evaluate_many(answers, as_report=as_report)


class Suite:
    def __init__(self, tracks: Iterable[Track]) -> None:
        self._tracks = list(tracks)
        self._tasks_by_id: dict[str, dict[str, Any]] = {}
        self._verifier_specs_by_id: dict[str, dict[str, Any]] = {}

        for track in self._tracks:
            for task_id, task in track._tasks_by_id.items():
                if task_id in self._tasks_by_id:
                    raise ValueError(f"Duplicate task_id across suite tracks: {task_id}")
                self._tasks_by_id[task_id] = deepcopy(task)

            for verifier_id, spec in track._verifier_specs_by_id.items():
                existing = self._verifier_specs_by_id.get(verifier_id)
                if existing is not None and existing != spec:
                    raise ValueError(
                        f"Conflicting verifier spec across suite tracks: {verifier_id}"
                    )
                self._verifier_specs_by_id[verifier_id] = deepcopy(spec)

    def tracks(self) -> list[Track]:
        return list(self._tracks)

    @property
    def tasks_by_id(self) -> dict[str, dict[str, Any]]:
        return deepcopy(self._tasks_by_id)

    @property
    def verifier_specs_by_id(self) -> dict[str, dict[str, Any]]:
        return deepcopy(self._verifier_specs_by_id)

    def tasks(self) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self._tasks_by_id.values()]

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self._tasks_by_id[task_id])
        except KeyError as exc:
            raise KeyError(f"Unknown task_id for suite: {task_id}") from exc

    def prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for track in self._tracks:
            prompts.extend(track.prompts())
        return prompts

    def evaluator(self, *, config: EvaluationConfig | None = None) -> Evaluator:
        return Evaluator(self._tasks_by_id, self._verifier_specs_by_id, config=config)

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        return self.evaluator().evaluate_one(answer)

    def evaluate_answers(
        self,
        answers: list[dict[str, Any]],
        *,
        as_report: bool = False,
    ) -> dict[str, Any] | EvaluationReport:
        return self.evaluator().evaluate_many(answers, as_report=as_report)


def _script_root_for(definition: TrackDefinition) -> Path:
    if definition.resource_root is not None:
        return definition.root

    verifier_specs_path = _resolve_track_path(
        definition,
        definition.verifier_specs_path,
    )
    if verifier_specs_path is not None:
        return verifier_specs_path.parent

    task_pack_path = Path(definition.task_pack_path)
    if task_pack_path.is_absolute():
        return task_pack_path.parent

    return definition.root


def _resolve_track_path(
    definition: TrackDefinition,
    path: str | Path | None,
) -> Path | None:
    if path is None:
        return None

    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    if definition.resource_root is not None:
        return definition.resolve_path(path)

    task_pack_path = Path(definition.task_pack_path)
    if task_pack_path.is_absolute():
        return task_pack_path.parent / candidate

    return definition.resolve_path(path)
