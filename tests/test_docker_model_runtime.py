from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import Any

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common import docker_model_runtime as runtime


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


def test_http_json_post_sends_json_body(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"status": "ok"}'

    def fake_urlopen(request: urllib.request.Request, **kwargs: Any) -> FakeResponse:
        assert request.full_url == "http://localhost/predict"
        assert request.get_method() == "POST"
        assert request.data == b'{"smiles": "CCO"}'
        assert request.get_header("Content-type") == "application/json"
        assert kwargs["timeout"] == 7
        return FakeResponse()

    monkeypatch.setattr(runtime.urllib.request, "urlopen", fake_urlopen)

    assert runtime.http_json(
        "http://localhost/predict",
        method="POST",
        payload={"smiles": "CCO"},
        timeout_seconds=7,
    ) == {"status": "ok"}


def test_http_json_maps_url_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: urllib.request.Request, **kwargs: Any) -> None:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(runtime.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(runtime.DockerRuntimeToolError) as exc:
        runtime.http_json("http://localhost/ready")

    assert "HTTP request failed" in str(exc.value)


def test_http_json_maps_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"not json"

    monkeypatch.setattr(runtime.urllib.request, "urlopen", lambda request, **kwargs: FakeResponse())

    with pytest.raises(runtime.DockerRuntimeToolError) as exc:
        runtime.http_json("http://localhost/ready")

    assert "was not JSON" in str(exc.value)


def test_wait_for_http_json_retries_with_remaining_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monotonic_values = iter([10.0, 10.0, 11.7, 11.7])
    timeouts: list[float] = []
    sleeps: list[float] = []

    def fake_http_json(url: str, **kwargs: Any) -> Any:
        timeouts.append(kwargs["timeout_seconds"])
        if len(timeouts) == 1:
            raise runtime.DockerRuntimeToolError("not ready")
        return {"ready": True}

    monkeypatch.setattr(runtime, "http_json", fake_http_json)
    monkeypatch.setattr(runtime.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(runtime.time, "sleep", lambda seconds: sleeps.append(seconds))

    assert runtime.wait_for_http_json(
        "http://localhost/ready",
        startup_timeout_seconds=2,
        poll_interval_seconds=5,
    ) == {"ready": True}
    assert timeouts == [2.0, pytest.approx(0.3)]
    assert sleeps == [pytest.approx(0.3)]


def test_ensure_http_container_reuses_running_container(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    readiness_urls: list[str] = []

    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        calls.append(args)
        assert kwargs["check"] is False
        if args == ["container", "inspect", "-f", "{{.State.Running}}", "model"]:
            return runtime.DockerCommandResult(stdout="true\n", stderr="", returncode=0)
        if args == [
            "container",
            "inspect",
            "-f",
            "{{ index .Config.Labels \"verifier-grounded-benchmark.managed\" }}",
            "model",
        ]:
            return runtime.DockerCommandResult(stdout="true\n", stderr="", returncode=0)
        raise AssertionError(f"unexpected docker command: {args}")

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)
    monkeypatch.setattr(runtime, "wait_for_http_json", lambda url, **kwargs: readiness_urls.append(url))

    runtime.ensure_http_container(
        image="image:tag",
        container_name="model",
        host="127.0.0.1",
        port=8000,
        container_port=5000,
        readiness_url="http://127.0.0.1:8000/ready",
        startup_timeout_seconds=9,
    )

    assert calls == [
        ["container", "inspect", "-f", "{{.State.Running}}", "model"],
        [
            "container",
            "inspect",
            "-f",
            "{{ index .Config.Labels \"verifier-grounded-benchmark.managed\" }}",
            "model",
        ],
    ]
    assert readiness_urls == ["http://127.0.0.1:8000/ready"]


def test_ensure_http_container_removes_and_recreates_managed_stopped_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        calls.append(args)
        if args == ["container", "inspect", "-f", "{{.State.Running}}", "model"]:
            assert kwargs["check"] is False
            return runtime.DockerCommandResult(stdout="false\n", stderr="", returncode=0)
        if args == [
            "container",
            "inspect",
            "-f",
            "{{ index .Config.Labels \"verifier-grounded-benchmark.managed\" }}",
            "model",
        ]:
            assert kwargs["check"] is False
            return runtime.DockerCommandResult(stdout="true\n", stderr="", returncode=0)
        if args == ["rm", "model"]:
            return runtime.DockerCommandResult(stdout="removed\n", stderr="", returncode=0)
        if args[0] == "run":
            return runtime.DockerCommandResult(stdout="container-id\n", stderr="", returncode=0)
        raise AssertionError(f"unexpected docker command: {args}")

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)
    monkeypatch.setattr(runtime, "wait_for_http_json", lambda url, **kwargs: {"ready": True})

    runtime.ensure_http_container(
        image="image:tag",
        container_name="model",
        host="127.0.0.1",
        port=8000,
        container_port=5000,
        readiness_url="http://127.0.0.1:8000/ready",
        startup_timeout_seconds=9,
    )

    assert calls == [
        ["container", "inspect", "-f", "{{.State.Running}}", "model"],
        [
            "container",
            "inspect",
            "-f",
            "{{ index .Config.Labels \"verifier-grounded-benchmark.managed\" }}",
            "model",
        ],
        ["rm", "model"],
        [
            "run",
            "--rm",
            "-d",
            "--name",
            "model",
            "--label",
            runtime.VGB_DOCKER_LABEL,
            "-p",
            "127.0.0.1:8000:5000",
            "image:tag",
        ],
    ]


def test_ensure_http_container_rejects_unmanaged_running_container(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        calls.append(args)
        if args == ["container", "inspect", "-f", "{{.State.Running}}", "model"]:
            return runtime.DockerCommandResult(stdout="true\n", stderr="", returncode=0)
        if args == [
            "container",
            "inspect",
            "-f",
            "{{ index .Config.Labels \"verifier-grounded-benchmark.managed\" }}",
            "model",
        ]:
            return runtime.DockerCommandResult(stdout="", stderr="", returncode=0)
        raise AssertionError(f"unexpected docker command: {args}")

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)

    with pytest.raises(runtime.DockerRuntimeEnvironmentError) as exc:
        runtime.ensure_http_container(
            image="image:tag",
            container_name="model",
            host="127.0.0.1",
            port=8000,
            container_port=5000,
            readiness_url="http://127.0.0.1:8000/ready",
            startup_timeout_seconds=9,
        )

    assert "unmanaged container" in str(exc.value)
    assert calls == [
        ["container", "inspect", "-f", "{{.State.Running}}", "model"],
        [
            "container",
            "inspect",
            "-f",
            "{{ index .Config.Labels \"verifier-grounded-benchmark.managed\" }}",
            "model",
        ],
    ]


def test_ensure_http_container_cleans_up_new_container_when_readiness_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        calls.append(args)
        if args == ["container", "inspect", "-f", "{{.State.Running}}", "model"]:
            return runtime.DockerCommandResult(stdout="", stderr="not found", returncode=1)
        if args[0] == "run":
            return runtime.DockerCommandResult(stdout="container-id\n", stderr="", returncode=0)
        if args == ["rm", "-f", "model"]:
            assert kwargs["check"] is False
            return runtime.DockerCommandResult(stdout="removed\n", stderr="", returncode=0)
        raise AssertionError(f"unexpected docker command: {args}")

    def fake_wait_for_http_json(url: str, **kwargs: Any) -> Any:
        raise runtime.DockerRuntimeTimeout("not ready")

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)
    monkeypatch.setattr(runtime, "wait_for_http_json", fake_wait_for_http_json)

    with pytest.raises(runtime.DockerRuntimeTimeout):
        runtime.ensure_http_container(
            image="image:tag",
            container_name="model",
            host="127.0.0.1",
            port=8000,
            container_port=5000,
            readiness_url="http://127.0.0.1:8000/ready",
            startup_timeout_seconds=9,
        )

    assert calls == [
        ["container", "inspect", "-f", "{{.State.Running}}", "model"],
        [
            "run",
            "--rm",
            "-d",
            "--name",
            "model",
            "--label",
            runtime.VGB_DOCKER_LABEL,
            "-p",
            "127.0.0.1:8000:5000",
            "image:tag",
        ],
        ["rm", "-f", "model"],
    ]


def test_ensure_http_container_starts_labeled_container_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        calls.append(args)
        if args[:3] == ["container", "inspect", "-f"]:
            assert kwargs["check"] is False
            return runtime.DockerCommandResult(stdout="", stderr="not found", returncode=1)
        return runtime.DockerCommandResult(stdout="container-id\n", stderr="", returncode=0)

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)
    monkeypatch.setattr(runtime, "wait_for_http_json", lambda url, **kwargs: {"ready": True})

    runtime.ensure_http_container(
        image="image:tag",
        container_name="model",
        host="127.0.0.1",
        port=8000,
        container_port=5000,
        readiness_url="http://127.0.0.1:8000/ready",
        startup_timeout_seconds=9,
    )

    assert calls == [
        ["container", "inspect", "-f", "{{.State.Running}}", "model"],
        [
            "run",
            "--rm",
            "-d",
            "--name",
            "model",
            "--label",
            runtime.VGB_DOCKER_LABEL,
            "-p",
            "127.0.0.1:8000:5000",
            "image:tag",
        ],
    ]


def test_ensure_http_container_rejects_unmanaged_stopped_container(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_command(args: list[str], **kwargs: Any) -> runtime.DockerCommandResult:
        calls.append(args)
        if args == ["container", "inspect", "-f", "{{.State.Running}}", "model"]:
            return runtime.DockerCommandResult(stdout="false\n", stderr="", returncode=0)
        if args == [
            "container",
            "inspect",
            "-f",
            "{{ index .Config.Labels \"verifier-grounded-benchmark.managed\" }}",
            "model",
        ]:
            return runtime.DockerCommandResult(stdout="", stderr="", returncode=0)
        raise AssertionError(f"unexpected docker command: {args}")

    monkeypatch.setattr(runtime, "run_docker_command", fake_command)

    with pytest.raises(runtime.DockerRuntimeEnvironmentError) as exc:
        runtime.ensure_http_container(
            image="image:tag",
            container_name="model",
            host="127.0.0.1",
            port=8000,
            container_port=5000,
            readiness_url="http://127.0.0.1:8000/ready",
            startup_timeout_seconds=9,
        )

    assert "unmanaged container" in str(exc.value)
    assert calls == [
        ["container", "inspect", "-f", "{{.State.Running}}", "model"],
        [
            "container",
            "inspect",
            "-f",
            "{{ index .Config.Labels \"verifier-grounded-benchmark.managed\" }}",
            "model",
        ],
    ]
