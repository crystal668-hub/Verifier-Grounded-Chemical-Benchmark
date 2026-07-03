from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_openmm_backend_does_not_create_task_pack() -> None:
    assert not (ROOT / "tasks" / "openmm_openff").exists()
    assert not (ROOT / "tasks" / "openmm_core").exists()


def test_openmm_backend_is_not_registered_as_formal_track() -> None:
    registry = (ROOT / "src" / "verifier_grounded_benchmark" / "registry.py").read_text()

    assert "openmm_openff" not in registry
    assert "openmm_core" not in registry
