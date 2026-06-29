from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

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
        self.tasks_by_id = load_tasks_file(
            definition.resolve_path(definition.task_pack_path)
        )
        specs = load_verifier_specs_file(
            definition.resolve_path(definition.verifier_specs_path)
        )
        self.verifier_specs_by_id = materialize_verifier_specs(
            specs,
            script_root=definition.root,
        )

    @property
    def name(self) -> str:
        return self.definition.name

    def tasks(self) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self.tasks_by_id.values()]

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self.tasks_by_id[task_id])
        except KeyError as exc:
            raise KeyError(f"Unknown task_id for track {self.name!r}: {task_id}") from exc

    def prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for task in self.tasks_by_id.values():
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
            self.definition.resolve_path(self.definition.sample_answers_path)
        )


class Suite:
    def __init__(self, tracks: Iterable[Track]) -> None:
        self._tracks = list(tracks)
        self.tasks_by_id: dict[str, dict[str, Any]] = {}
        self.verifier_specs_by_id: dict[str, dict[str, Any]] = {}

        for track in self._tracks:
            for task_id, task in track.tasks_by_id.items():
                if task_id in self.tasks_by_id:
                    raise ValueError(f"Duplicate task_id across suite tracks: {task_id}")
                self.tasks_by_id[task_id] = deepcopy(task)

            for verifier_id, spec in track.verifier_specs_by_id.items():
                existing = self.verifier_specs_by_id.get(verifier_id)
                if existing is not None and existing != spec:
                    raise ValueError(
                        f"Conflicting verifier spec across suite tracks: {verifier_id}"
                    )
                self.verifier_specs_by_id[verifier_id] = deepcopy(spec)

    def tracks(self) -> list[Track]:
        return list(self._tracks)

    def tasks(self) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self.tasks_by_id.values()]

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self.tasks_by_id[task_id])
        except KeyError as exc:
            raise KeyError(f"Unknown task_id for suite: {task_id}") from exc

    def prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for track in self._tracks:
            prompts.extend(track.prompts())
        return prompts
