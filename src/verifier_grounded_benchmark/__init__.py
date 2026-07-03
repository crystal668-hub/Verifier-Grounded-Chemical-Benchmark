from __future__ import annotations

from verifier_grounded_benchmark.evaluator import (
    EvaluationConfig,
    EvaluationReport,
    Evaluator,
)
from verifier_grounded_benchmark.registry import DEFAULT_REGISTRY, Registry, TrackDefinition
from verifier_grounded_benchmark.track import Suite, Track


def list_tracks(status: str | None = "formal") -> list[TrackDefinition]:
    return DEFAULT_REGISTRY.list_tracks(status=status)


def load_track(name: str) -> Track:
    return Track(DEFAULT_REGISTRY.get_track_definition(name))


def load_suite(track_names: list[str] | None = None) -> Suite:
    if track_names is None:
        definitions = DEFAULT_REGISTRY.list_tracks()
        track_names = [definition.name for definition in definitions]
    return Suite([load_track(name) for name in track_names])


def register_track(track: TrackDefinition, *, replace: bool = False) -> None:
    DEFAULT_REGISTRY.register_track(track, replace=replace)


__all__ = [
    "EvaluationConfig",
    "EvaluationReport",
    "Evaluator",
    "Registry",
    "Suite",
    "Track",
    "TrackDefinition",
    "list_tracks",
    "load_suite",
    "load_track",
    "register_track",
]
