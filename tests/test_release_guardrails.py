from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.release import build_release as release


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@pytest.fixture
def repository(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "release-test@example.invalid")
    git(root, "config", "user.name", "Release test")
    (root / "pyproject.toml").write_text('[project]\nversion = "1.0.0rc1"\n')
    git(root, "add", "pyproject.toml")
    git(root, "commit", "-qm", "fixture source")
    monkeypatch.setattr(release, "ROOT", root)
    monkeypatch.setattr(release, "task_inventory", lambda version: {
        "package_version": version, "scoring_version": "linear_goal_v2",
        "tracks": {"test": {"count": 1, "scoring_status": "formal"}},
    })
    return root


def destinations(root):
    return {"output_dir": root.parent / "dist",
            "metadata_dir": root.parent / "release", "tag": "v1.0.0-rc"}


def test_preflight_binds_explicit_tag_without_writing(repository):
    args = destinations(repository)
    state = release.release_preflight(**args)
    assert state["version"] == "1.0.0rc1"
    assert state["tag"] == "v1.0.0-rc"
    assert state["canonical_source"]["commit"] == git(repository, "rev-parse", "HEAD")
    assert not args["output_dir"].exists()
    assert not args["metadata_dir"].exists()


@pytest.mark.parametrize("version", ["1.0.0-rc", "v1.0.0rc1", "not-a-version"])
def test_noncanonical_versions_fail_before_build(repository, version):
    (repository / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    with pytest.raises(ValueError, match="version"):
        release.build_release(**destinations(repository))


def test_dirty_source_is_rejected(repository):
    (repository / "uncommitted.txt").write_text("not accepted")
    with pytest.raises(RuntimeError, match="clean Git"):
        release.build_release(**destinations(repository))


@pytest.mark.parametrize("kind", ["wheel", "sdist", "metadata"])
def test_existing_outputs_are_never_replaced(repository, kind):
    args = destinations(repository)
    if kind == "metadata":
        args["metadata_dir"].mkdir()
        target = args["metadata_dir"] / "manifest.json"
    else:
        args["output_dir"].mkdir()
        suffix = "-py3-none-any.whl" if kind == "wheel" else ".tar.gz"
        target = args["output_dir"] / f"verifier_grounded_benchmark-1.0.0rc1{suffix}"
    target.write_bytes(b"historical release")
    with pytest.raises(FileExistsError, match="Refusing"):
        release.build_release(**args)
    assert target.read_bytes() == b"historical release"


def test_tag_cannot_rebind_to_another_commit(repository):
    git(repository, "tag", "v1.0.0-rc")
    original = git(repository, "rev-parse", "HEAD")
    git(repository, "commit", "--allow-empty", "-qm", "another commit")
    with pytest.raises(RuntimeError, match="another commit"):
        release.build_release(**destinations(repository))
    assert git(repository, "rev-parse", "v1.0.0-rc") == original


def test_matching_tag_is_accepted(repository):
    git(repository, "tag", "v1.0.0-rc")
    assert release.release_preflight(**destinations(repository))["tag"] == "v1.0.0-rc"


@pytest.mark.parametrize("tag", ["", "../escape", "bad tag", "--option"])
def test_invalid_tags_fail_before_writes(repository, tag):
    args = {**destinations(repository), "tag": tag}
    with pytest.raises(ValueError):
        release.build_release(**args)
    assert not args["output_dir"].exists()


def test_failed_build_leaves_no_release_files(repository, monkeypatch):
    original_run = subprocess.run
    def fail_build(command, **kwargs):
        if command[0] == "uv":
            raise subprocess.CalledProcessError(1, command)
        return original_run(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", fail_build)
    args = destinations(repository)
    with pytest.raises(subprocess.CalledProcessError):
        release.build_release(**args)
    assert not args["metadata_dir"].exists()
    assert not args["output_dir"].exists()


def test_publish_collision_preserves_existing_file_and_rolls_back_own_files(tmp_path):
    source = tmp_path / "staging"
    source.mkdir()
    first, second = source / "wheel", source / "sdist"
    first.write_bytes(b"new wheel")
    second.write_bytes(b"new sdist")
    staged_metadata = source / "metadata"
    staged_metadata.mkdir()
    (staged_metadata / "manifest.json").write_text("{}")
    output = tmp_path / "dist"
    output.mkdir()
    (output / second.name).write_bytes(b"existing artifact")
    metadata = tmp_path / "release"
    with pytest.raises(FileExistsError):
        release._publish_new_files((first, second), staged_metadata, output, metadata)
    assert (output / second.name).read_bytes() == b"existing artifact"
    assert not (output / first.name).exists()
    assert not metadata.exists()


def test_inventory_binds_all_formal_configuration_files():
    inventory = release.task_inventory(release.project_version())
    assert sum(track["count"] for track in inventory["tracks"].values()) == 100
    for name, track in inventory["tracks"].items():
        assert len(track["tasks_sha256"]) == len(track["scoring_sha256"]) == 64
        assert ("verifier_specs_sha256" in track) == name.startswith("open_generation_")


def test_inventory_rejects_unrelated_release_version():
    with pytest.raises(ValueError, match="version/identity mismatch"):
        release.task_inventory("999.0.0")
