from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from verifiers.backends import docker_model_runtime as runtime


def test_run_docker_command_maps_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.shutil, "which", lambda command: None)

    with pytest.raises(runtime.DockerRuntimeEnvironmentError) as exc:
        runtime.run_docker_command(["version"], docker_executable="missing-docker", timeout_seconds=1)

    assert "Docker executable not found" in str(exc.value)


def test_run_docker_command_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["timeout"] == 5
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(runtime.shutil, "which", lambda command: "/usr/bin/docker")
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    result = runtime.run_docker_command(["image", "inspect", "example:latest"], timeout_seconds=5)

    assert result.stdout == "ok\n"
    assert calls == [["/usr/bin/docker", "image", "inspect", "example:latest"]]


def test_run_docker_command_maps_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 17, stdout="", stderr="boom")

    monkeypatch.setattr(runtime.shutil, "which", lambda command: "/usr/bin/docker")
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(runtime.DockerRuntimeToolError) as exc:
        runtime.run_docker_command(["run", "bad"], timeout_seconds=5)

    assert "boom" in str(exc.value)


def test_run_docker_command_maps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout=3)

    monkeypatch.setattr(runtime.shutil, "which", lambda command: "/usr/bin/docker")
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    with pytest.raises(runtime.DockerRuntimeTimeout) as exc:
        runtime.run_docker_command(["run", "slow"], timeout_seconds=3)

    assert "timed out" in str(exc.value)


def test_docker_image_inspect_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        assert args == ["image", "inspect", "example:latest"]
        return runtime.DockerCommandResult(stdout=json.dumps([{"Id": "sha256:123"}]), stderr="", returncode=0)

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)

    assert runtime.docker_image_inspect("example:latest") == {"Id": "sha256:123"}


def test_run_one_shot_container_builds_platform_command(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        assert args == [
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "image:tag",
            "python",
            "-c",
            "print(1)",
        ]
        return runtime.DockerCommandResult(stdout="1\n", stderr="", returncode=0)

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)

    assert runtime.run_one_shot_container(
        image="image:tag",
        command=["python", "-c", "print(1)"],
        platform="linux/amd64",
        timeout_seconds=10,
    ) == "1\n"
