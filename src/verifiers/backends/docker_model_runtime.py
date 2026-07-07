"""Shared helpers for Docker-backed model verifier runtimes."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


VGB_DOCKER_LABEL_KEY = "verifier-grounded-benchmark.managed"
VGB_DOCKER_LABEL_VALUE = "true"
VGB_DOCKER_LABEL = f"{VGB_DOCKER_LABEL_KEY}={VGB_DOCKER_LABEL_VALUE}"


class DockerRuntimeEnvironmentError(RuntimeError):
    """Raised when Docker, an image, or a model service is unavailable."""


class DockerRuntimeTimeout(RuntimeError):
    """Raised when a Docker command or model service exceeds its timeout."""


class DockerRuntimeToolError(RuntimeError):
    """Raised when a Docker-backed model returns an execution or schema error."""


@dataclass(frozen=True)
class DockerCommandResult:
    stdout: str
    stderr: str
    returncode: int


def resolve_docker_executable(docker_executable: str | None = None) -> str:
    configured = docker_executable or os.environ.get("VGB_DOCKER_EXECUTABLE") or "docker"
    if os.sep in configured:
        resolved = configured
    else:
        resolved = shutil.which(configured)
    if not resolved:
        raise DockerRuntimeEnvironmentError(f"Docker executable not found: {configured}")
    return resolved


def run_docker_command(
    args: list[str],
    *,
    docker_executable: str | None = None,
    timeout_seconds: float = 60,
    input_text: str | None = None,
    check: bool = True,
) -> DockerCommandResult:
    executable = resolve_docker_executable(docker_executable)
    command = [executable, *args]
    try:
        completed = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DockerRuntimeEnvironmentError(f"Docker executable not found: {executable}") from exc
    except subprocess.TimeoutExpired as exc:
        raise DockerRuntimeTimeout(f"Docker command timed out after {timeout_seconds:g} seconds") from exc

    result = DockerCommandResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"docker exited {result.returncode}"
        raise DockerRuntimeToolError(message)
    return result


def docker_image_inspect(
    image: str,
    *,
    docker_executable: str | None = None,
    timeout_seconds: float = 30,
) -> dict[str, Any]:
    result = run_docker_command(
        ["image", "inspect", image],
        docker_executable=docker_executable,
        timeout_seconds=timeout_seconds,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DockerRuntimeToolError(f"docker image inspect returned invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise DockerRuntimeToolError("docker image inspect returned no image object")
    return payload[0]


def run_one_shot_container(
    *,
    image: str,
    command: list[str],
    platform: str | None = None,
    docker_executable: str | None = None,
    timeout_seconds: float = 60,
    workdir: str | None = None,
) -> str:
    args = ["run", "--rm"]
    if platform:
        args.extend(["--platform", platform])
    if workdir:
        args.extend(["-w", workdir])
    args.append(image)
    args.extend(command)
    return run_docker_command(
        args,
        docker_executable=docker_executable,
        timeout_seconds=timeout_seconds,
    ).stdout


def http_json(
    url: str,
    *,
    method: str = "GET",
    payload: Any | None = None,
    timeout_seconds: float = 30,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            text = response.read().decode()
    except (TimeoutError, socket.timeout) as exc:
        raise DockerRuntimeTimeout(f"HTTP request timed out after {timeout_seconds:g} seconds: {url}") from exc
    except urllib.error.URLError as exc:
        raise DockerRuntimeToolError(f"HTTP request failed for {url}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DockerRuntimeToolError(f"HTTP response from {url} was not JSON: {exc.msg}") from exc


def wait_for_http_json(
    url: str,
    *,
    startup_timeout_seconds: float = 60,
    poll_interval_seconds: float = 1,
) -> Any:
    deadline = time.monotonic() + startup_timeout_seconds
    last_error: Exception | None = None
    while True:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            break
        try:
            return http_json(url, timeout_seconds=min(5.0, remaining_seconds))
        except (DockerRuntimeToolError, DockerRuntimeTimeout) as exc:
            last_error = exc
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                break
            time.sleep(min(poll_interval_seconds, remaining_seconds))
    raise DockerRuntimeTimeout(f"HTTP service did not become ready at {url}: {last_error}")


def ensure_http_container(
    *,
    image: str,
    container_name: str,
    host: str,
    port: int,
    container_port: int,
    readiness_url: str,
    docker_executable: str | None = None,
    startup_timeout_seconds: float = 60,
) -> None:
    inspect = run_docker_command(
        ["container", "inspect", "-f", "{{.State.Running}}", container_name],
        docker_executable=docker_executable,
        timeout_seconds=10,
        check=False,
    )
    if inspect.returncode == 0 and inspect.stdout.strip() == "true":
        wait_for_http_json(readiness_url, startup_timeout_seconds=startup_timeout_seconds)
        return
    if inspect.returncode == 0:
        label = run_docker_command(
            [
                "container",
                "inspect",
                "-f",
                f'{{{{ index .Config.Labels "{VGB_DOCKER_LABEL_KEY}" }}}}',
                container_name,
            ],
            docker_executable=docker_executable,
            timeout_seconds=10,
            check=False,
        )
        if label.returncode != 0:
            message = label.stderr.strip() or label.stdout.strip() or "failed to inspect container labels"
            raise DockerRuntimeEnvironmentError(message)
        if label.stdout.strip() != VGB_DOCKER_LABEL_VALUE:
            raise DockerRuntimeEnvironmentError(
                f"container name {container_name!r} is already used by an unmanaged container"
            )
        run_docker_command(
            ["rm", container_name],
            docker_executable=docker_executable,
            timeout_seconds=10,
        )

    run_docker_command(
        [
            "run",
            "--rm",
            "-d",
            "--name",
            container_name,
            "--label",
            VGB_DOCKER_LABEL,
            "-p",
            f"{host}:{port}:{container_port}",
            image,
        ],
        docker_executable=docker_executable,
        timeout_seconds=startup_timeout_seconds,
    )
    wait_for_http_json(readiness_url, startup_timeout_seconds=startup_timeout_seconds)
