from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from verifier_grounded_benchmark.resources import repository_root, resolve_path


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

    def __post_init__(self) -> None:
        for field_name in ("name", "version", "display_name", "status"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"TrackDefinition {field_name} must be non-empty")

        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "requirements", tuple(self.requirements))

    @property
    def root(self) -> Path:
        if self.resource_root is None:
            return repository_root()
        return Path(self.resource_root).resolve()

    def resolve_path(self, path: str | Path) -> Path:
        return resolve_path(path, base=self.root)


class Registry:
    def __init__(self, tracks: list[TrackDefinition] | None = None) -> None:
        self._tracks: dict[str, TrackDefinition] = {}
        for track in tracks or []:
            self.register_track(track)

    def register_track(
        self,
        track: TrackDefinition,
        *,
        replace: bool = False,
    ) -> None:
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
        if status is None:
            return tracks
        return [track for track in tracks if track.status == status]


def builtin_definitions() -> list[TrackDefinition]:
    return [
        TrackDefinition(
            name="rdkit",
            version="0.1.0",
            display_name="RDKit baseline small-molecule tasks",
            task_pack_path="tasks/rdkit_baseline/tasks.yaml",
            verifier_specs_path="tasks/rdkit_baseline/verifier_specs.yaml",
            sample_answers_path="tasks/rdkit_baseline/sample_answers.jsonl",
            status="formal",
            tags=("small_molecule", "rdkit", "descriptor"),
            resource_root=repository_root(),
        ),
        TrackDefinition(
            name="xtb",
            version="0.1.0",
            display_name="xTB direct-XYZ small-molecule tasks",
            task_pack_path="tasks/xtb_xyz/tasks.yaml",
            verifier_specs_path="tasks/xtb_xyz/verifier_specs.yaml",
            sample_answers_path="tasks/xtb_xyz/sample_answers.jsonl",
            status="formal",
            tags=("small_molecule_3d", "xtb", "xyz"),
            requirements=("xtb executable for real scoring",),
            resource_root=repository_root(),
        ),
    ]


DEFAULT_REGISTRY = Registry(builtin_definitions())
