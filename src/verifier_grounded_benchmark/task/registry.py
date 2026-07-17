"""Builtin and user-defined task-track registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from verifier_grounded_benchmark.task.resources import package_resource, repository_root, resolve_path


@dataclass(frozen=True)
class TrackDefinition:
    name: str
    version: str
    display_name: str
    task_pack_path: str | Path
    verifier_specs_path: str | Path
    sample_answers_path: str | Path | None = None
    status: str = "formal"
    tags: tuple[str, ...] = field(default_factory=tuple)
    requirements: tuple[str, ...] = field(default_factory=tuple)
    resource_root: str | Path | None = None
    resource_pack: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("name", "version", "display_name", "status"):
            if not isinstance(getattr(self, field_name), str) or not getattr(self, field_name):
                raise ValueError(f"TrackDefinition {field_name} must be non-empty")
        if self.resource_pack is not None and self.resource_root is not None:
            raise ValueError("resource_pack and resource_root are mutually exclusive")
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "requirements", tuple(self.requirements))

    @property
    def root(self) -> Path:
        return repository_root() if self.resource_root is None else Path(self.resource_root).resolve()

    def resolve_path(self, path: str | Path) -> Path:
        return resolve_path(path, base=self.root)

    def resource(self, path: str | Path | None) -> object | None:
        if path is None:
            return None
        if self.resource_pack is not None:
            return package_resource(self.resource_pack, str(path))
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        task_path = Path(self.task_pack_path)
        if task_path.is_absolute():
            return task_path.parent / candidate
        return self.resolve_path(candidate)


class Registry:
    def __init__(self, tracks: list[TrackDefinition] | None = None) -> None:
        self._tracks: dict[str, TrackDefinition] = {}
        for track in tracks or []:
            self.register_track(track)

    def register_track(self, track: TrackDefinition, *, replace: bool = False) -> None:
        if track.name in self._tracks and not replace:
            raise ValueError(f"Track {track.name!r} is already registered")
        self._tracks[track.name] = track

    def get_track_definition(self, name: str) -> TrackDefinition:
        try:
            return self._tracks[name]
        except KeyError as exc:
            raise KeyError(f"Unknown benchmark track {name!r}") from exc

    def list_tracks(self, status: str | None = "formal") -> list[TrackDefinition]:
        tracks = list(self._tracks.values())
        return tracks if status is None else [track for track in tracks if track.status == status]


def builtin_definitions() -> list[TrackDefinition]:
    return [
        TrackDefinition(
            name="rdkit", version="0.2.0", display_name="RDKit baseline small-molecule tasks",
            task_pack_path="tasks/rdkit_baseline/tasks.yaml",
            verifier_specs_path="tasks/rdkit_baseline/verifier_specs.yaml",
            sample_answers_path="tasks/rdkit_baseline/sample_answers.jsonl",
            tags=("small_molecule", "rdkit", "descriptor"), resource_root=repository_root(),
        ),
        TrackDefinition(
            name="xtb", version="0.2.0", display_name="xTB direct-XYZ small-molecule tasks",
            task_pack_path="tasks/xtb_xyz/tasks.yaml",
            verifier_specs_path="tasks/xtb_xyz/verifier_specs.yaml",
            sample_answers_path="tasks/xtb_xyz/sample_answers.jsonl",
            tags=("small_molecule_3d", "xtb", "xyz"),
            requirements=("xtb executable for real scoring",), resource_root=repository_root(),
        ),
        TrackDefinition(
            name="property_calculation", version="0.2.0", display_name="Fixed-input property calculation tasks",
            task_pack_path="tasks/property_calculation/tasks.yaml",
            verifier_specs_path="tasks/property_calculation/verifier_specs.yaml",
            sample_answers_path="tasks/property_calculation/sample_answers.jsonl",
            tags=("property_calculation", "fixed_input", "crystal"), resource_root=repository_root(),
        ),
    ]


DEFAULT_REGISTRY = Registry(builtin_definitions())
