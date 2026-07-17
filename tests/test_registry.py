from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import verifier_grounded_benchmark as vgb
from verifier_grounded_benchmark.io import load_answers_jsonl_file
from verifier_grounded_benchmark.registry import Registry, TrackDefinition
from verifier_grounded_benchmark.track import Suite, Track

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


def test_public_registry_exposes_all_formal_builtins() -> None:
    tracks = vgb.list_tracks()

    assert [track.name for track in tracks] == [
        "rdkit",
        "xtb",
        "property_calculation",
    ]
    assert tracks[0] == TrackDefinition(
        name="rdkit",
        version="0.2.0",
        display_name="RDKit baseline small-molecule tasks",
        task_pack_path="tasks/rdkit_baseline/tasks.yaml",
        verifier_specs_path="tasks/rdkit_baseline/verifier_specs.yaml",
        sample_answers_path="tasks/rdkit_baseline/sample_answers.jsonl",
        status="formal",
        tags=("small_molecule", "rdkit", "descriptor"),
        resource_root=ROOT,
    )
    assert tracks[1] == TrackDefinition(
        name="xtb",
        version="0.2.0",
        display_name="xTB direct-XYZ small-molecule tasks",
        task_pack_path="tasks/xtb_xyz/tasks.yaml",
        verifier_specs_path="tasks/xtb_xyz/verifier_specs.yaml",
        sample_answers_path="tasks/xtb_xyz/sample_answers.jsonl",
        status="formal",
        tags=("small_molecule_3d", "xtb", "xyz"),
        requirements=("xtb executable for real scoring",),
        resource_root=ROOT,
    )
    assert tracks[2] == TrackDefinition(
        name="property_calculation",
        version="0.2.0",
        display_name="Fixed-input property calculation tasks",
        task_pack_path="tasks/property_calculation/tasks.yaml",
        verifier_specs_path="tasks/property_calculation/verifier_specs.yaml",
        sample_answers_path="tasks/property_calculation/sample_answers.jsonl",
        status="formal",
        tags=("property_calculation", "fixed_input", "crystal"),
        resource_root=ROOT,
    )


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


def test_answers_jsonl_allows_repeated_task_ids(tmp_path: Path) -> None:
    answers_path = tmp_path / "answers.jsonl"
    answers_path.write_text(
        "\n".join(
            [
                '{"task_id": "example_task", "candidates": [{"value": 1}]}',
                '{"task_id": "example_task", "candidates": [{"value": 2}]}',
            ]
        ),
        encoding="utf-8",
    )

    assert load_answers_jsonl_file(answers_path) == [
        {"task_id": "example_task", "candidates": [{"value": 1}]},
        {"task_id": "example_task", "candidates": [{"value": 2}]},
    ]


def test_suite_rejects_duplicate_task_ids(tmp_path: Path) -> None:
    first = _write_track_files(
        tmp_path,
        "first",
        task_id="shared_task",
        verifier_id="first_v1",
        verification_script="first.py",
    )
    second = _write_track_files(
        tmp_path,
        "second",
        task_id="shared_task",
        verifier_id="second_v1",
        verification_script="second.py",
    )

    with pytest.raises(ValueError, match="Duplicate task_id"):
        Suite([first, second])


def test_suite_rejects_conflicting_same_verifier_id_specs(tmp_path: Path) -> None:
    first = _write_track_files(
        tmp_path,
        "first",
        task_id="first_task",
        verifier_id="shared_v1",
        verification_script="a.py",
    )
    second = _write_track_files(
        tmp_path,
        "second",
        task_id="second_task",
        verifier_id="shared_v1",
        verification_script="b.py",
    )

    with pytest.raises(ValueError, match="Conflicting verifier spec"):
        Suite([first, second])


def test_track_and_suite_tasks_by_id_return_mutation_safe_copies(
    tmp_path: Path,
) -> None:
    track = _write_track_files(
        tmp_path,
        "first",
        task_id="first_task",
        verifier_id="first_v1",
        verification_script="first.py",
    )
    suite = Suite([track])

    track.tasks_by_id["first_task"]["prompt"] = "mutated track prompt"
    suite.tasks_by_id["first_task"]["prompt"] = "mutated suite prompt"

    assert track.task("first_task")["prompt"] == "Prompt for first_task"
    assert suite.task("first_task")["prompt"] == "Prompt for first_task"
    assert track.prompts() == [
        {
            "track": "first",
            "task_id": "first_task",
            "prompt": "Prompt for first_task",
        }
    ]
    assert suite.prompts() == [
        {
            "track": "first",
            "task_id": "first_task",
            "prompt": "Prompt for first_task",
        }
    ]


def test_external_absolute_track_paths_resolve_scripts_from_spec_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "external_pack"
    root.mkdir()
    tasks_path = root / "tasks.yaml"
    specs_path = root / "verifier_specs.yaml"
    tasks_path.write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "task_id": "external_task",
                        "prompt": "External prompt",
                        "constraints": [{"verifier_id": "external_v1"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    specs_path.write_text(
        yaml.safe_dump(
            {
                "verifiers": [
                    {
                        "verifier_id": "external_v1",
                        "verification_script": "verifier.py",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    track = Track(
        TrackDefinition(
            name="external",
            version="1",
            display_name="External",
            task_pack_path=tasks_path,
            verifier_specs_path=specs_path,
        )
    )

    assert track.verifier_specs_by_id["external_v1"]["verification_script"] == str(
        root / "verifier.py"
    )


def test_external_absolute_task_path_resolves_relative_specs_and_samples(
    tmp_path: Path,
) -> None:
    root = tmp_path / "external_pack_with_relatives"
    root.mkdir()
    tasks_path = root / "tasks.yaml"
    tasks_path.write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "task_id": "external_relative_task",
                        "prompt": "External relative prompt",
                        "constraints": [{"verifier_id": "external_relative_v1"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "verifier_specs.yaml").write_text(
        yaml.safe_dump(
            {
                "verifiers": [
                    {
                        "verifier_id": "external_relative_v1",
                        "verification_script": "verifier.py",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "sample_answers.jsonl").write_text(
        '{"task_id": "external_relative_task", "candidates": [{"value": "C"}]}',
        encoding="utf-8",
    )

    track = Track(
        TrackDefinition(
            name="external-relative",
            version="1",
            display_name="External Relative",
            task_pack_path=tasks_path,
            verifier_specs_path="verifier_specs.yaml",
            sample_answers_path="sample_answers.jsonl",
        )
    )

    assert track.task("external_relative_task")["prompt"] == (
        "External relative prompt"
    )
    assert track.verifier_specs_by_id["external_relative_v1"][
        "verification_script"
    ] == str(root / "verifier.py")
    assert track.sample_answers() == [
        {
            "task_id": "external_relative_task",
            "candidates": [{"value": "C"}],
        }
    ]


def test_external_nested_relative_specs_resolve_scripts_from_specs_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "external_pack_with_nested_specs"
    specs_root = root / "specs"
    specs_root.mkdir(parents=True)
    tasks_path = root / "tasks.yaml"
    tasks_path.write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "task_id": "external_nested_task",
                        "prompt": "External nested prompt",
                        "constraints": [{"verifier_id": "external_nested_v1"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (specs_root / "verifier_specs.yaml").write_text(
        yaml.safe_dump(
            {
                "verifiers": [
                    {
                        "verifier_id": "external_nested_v1",
                        "verification_script": "runner.py",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    track = Track(
        TrackDefinition(
            name="external-nested",
            version="1",
            display_name="External Nested",
            task_pack_path=tasks_path,
            verifier_specs_path="specs/verifier_specs.yaml",
        )
    )

    assert track.verifier_specs_by_id["external_nested_v1"][
        "verification_script"
    ] == str(specs_root / "runner.py")


def _write_track_files(
    tmp_path: Path,
    name: str,
    *,
    task_id: str,
    verifier_id: str,
    verification_script: str,
) -> Track:
    root = tmp_path / name
    root.mkdir()
    (root / "tasks.yaml").write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "task_id": task_id,
                        "prompt": f"Prompt for {task_id}",
                        "constraints": [{"verifier_id": verifier_id}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "verifier_specs.yaml").write_text(
        yaml.safe_dump(
            {
                "verifiers": [
                    {
                        "verifier_id": verifier_id,
                        "verification_script": verification_script,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    definition = TrackDefinition(
        name=name,
        version="1",
        display_name=name.title(),
        task_pack_path="tasks.yaml",
        verifier_specs_path="verifier_specs.yaml",
        resource_root=root,
    )
    return Track(definition)
