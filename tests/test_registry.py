from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from verifier_grounded_benchmark.registry import Registry, TrackDefinition

ROOT = Path(__file__).resolve().parents[1]


def test_registry_lists_only_formal_tracks_by_default() -> None:
    registry = Registry(
        [
            TrackDefinition(
                name="formal",
                version="1",
                display_name="Formal Track",
                task_pack_path="tasks/formal/tasks.yaml",
                verifier_specs_path="tasks/formal/verifier_specs.yaml",
                status="formal",
            ),
            TrackDefinition(
                name="experimental",
                version="1",
                display_name="Experimental Track",
                task_pack_path="tasks/experimental/tasks.yaml",
                verifier_specs_path="tasks/experimental/verifier_specs.yaml",
                status="experimental",
            ),
        ]
    )

    assert [track.name for track in registry.list_tracks()] == ["formal"]
    assert [track.name for track in registry.list_tracks(status=None)] == [
        "formal",
        "experimental",
    ]


def test_registry_rejects_duplicate_track_names() -> None:
    registry = Registry()
    track = TrackDefinition(
        name="rdkit",
        version="1",
        display_name="RDKit",
        task_pack_path="tasks/rdkit_baseline/tasks.yaml",
        verifier_specs_path="tasks/rdkit_baseline/verifier_specs.yaml",
    )

    registry.register_track(track)

    with pytest.raises(ValueError, match="rdkit"):
        registry.register_track(track)


def test_registry_replace_allows_explicit_override() -> None:
    registry = Registry()
    original = TrackDefinition(
        name="rdkit",
        version="1",
        display_name="RDKit",
        task_pack_path="tasks/rdkit_baseline/tasks.yaml",
        verifier_specs_path="tasks/rdkit_baseline/verifier_specs.yaml",
    )
    replacement = TrackDefinition(
        name="rdkit",
        version="2",
        display_name="RDKit Replacement",
        task_pack_path="tasks/rdkit_baseline/tasks-v2.yaml",
        verifier_specs_path="tasks/rdkit_baseline/verifier_specs-v2.yaml",
    )

    registry.register_track(original)
    registry.register_track(replacement, replace=True)

    assert registry.get_track_definition("rdkit") == replacement


def test_track_definition_resolves_relative_paths_from_resource_root(
    tmp_path: Path,
) -> None:
    task_pack = {
        "tasks": [
            {
                "task_id": "example_task",
                "prompt": "Example",
            }
        ]
    }
    tasks_path = tmp_path / "packs" / "example" / "tasks.yaml"
    tasks_path.parent.mkdir(parents=True)
    tasks_path.write_text(yaml.safe_dump(task_pack), encoding="utf-8")

    track = TrackDefinition(
        name="example",
        version="1",
        display_name="Example",
        task_pack_path="packs/example/tasks.yaml",
        verifier_specs_path="packs/example/verifier_specs.yaml",
        resource_root=tmp_path,
    )

    assert track.resolve_path(track.task_pack_path) == tasks_path.resolve()
