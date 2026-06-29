from __future__ import annotations

from verifier_grounded_benchmark.registry import DEFAULT_REGISTRY, Registry, TrackDefinition


def list_tracks(status: str | None = "formal") -> list[TrackDefinition]:
    return DEFAULT_REGISTRY.list_tracks(status=status)


def register_track(track: TrackDefinition, *, replace: bool = False) -> None:
    DEFAULT_REGISTRY.register_track(track, replace=replace)


__all__ = [
    "Registry",
    "TrackDefinition",
    "list_tracks",
    "register_track",
]
