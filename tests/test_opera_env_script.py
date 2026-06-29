from __future__ import annotations

import json
import os
import subprocess
import sys


def test_check_opera_env_missing_or_path_discovery(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OPERA_EXECUTABLE", raising=False)
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()
    monkeypatch.setenv("PATH", os.fspath(empty_path))

    completed = subprocess.run(
        [sys.executable, "scripts/check_opera_env.py"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "missing"
    assert payload["failure_type"] == "verifier_environment_error"


def test_check_opera_env_configured_executable_missing_mcr(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "fake_opera"
    executable.write_text("#!/bin/sh\nprintf 'OPERA help\\n'\n")
    executable.chmod(executable.stat().st_mode | 0o111)
    monkeypatch.setenv("OPERA_EXECUTABLE", os.fspath(executable))
    monkeypatch.delenv("OPERA_MCR_DIRECTORY", raising=False)

    completed = subprocess.run(
        [sys.executable, "scripts/check_opera_env.py"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "missing"
    assert payload["failure_type"] == "verifier_environment_error"
    assert payload["executable"] == os.fspath(executable)
    assert "mcr" in payload["message"].lower()


def test_check_opera_env_configured_executable_and_mcr(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "fake_opera"
    mcr_directory = tmp_path / "mcr"
    mcr_directory.mkdir()
    executable.write_text(
        "#!/bin/sh\n"
        "test \"$1\" = \"$OPERA_EXPECTED_MCR\" || exit 17\n"
        "test \"$2\" = \"-h\" || exit 18\n"
        "printf 'OPERA help\\n'\n"
    )
    executable.chmod(executable.stat().st_mode | 0o111)
    monkeypatch.setenv("OPERA_EXECUTABLE", os.fspath(executable))
    monkeypatch.setenv("OPERA_MCR_DIRECTORY", os.fspath(mcr_directory))
    monkeypatch.setenv("OPERA_EXPECTED_MCR", os.fspath(mcr_directory))

    completed = subprocess.run(
        [sys.executable, "scripts/check_opera_env.py"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["executable"] == os.fspath(executable)
    assert payload["mcr_directory"] == os.fspath(mcr_directory)
