from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SCRIPT_PATHS = {
    "scripts/env/__init__.py",
    "scripts/env/check_admet_ai_env.py",
    "scripts/env/check_core_env.py",
    "scripts/env/check_mace_mp_env.py",
    "scripts/env/check_matgl_env.py",
    "scripts/env/check_molgpka_env.py",
    "scripts/env/check_openmm_openff_env.py",
    "scripts/env/check_soltrannet_env.py",
    "scripts/env/check_torchani_env.py",
    "scripts/env/check_xtb_env.py",
    "scripts/validation/__init__.py",
    "scripts/validation/check_xtb_xyz_samples.py",
    "scripts/xtb_calibration/__init__.py",
    "scripts/xtb_calibration/analyze_xtb_calibration.py",
    "scripts/xtb_calibration/generate_expert_candidates.py",
    "scripts/xtb_calibration/run_xtb_calibration.py",
    "scripts/xtb_real_dataset/__init__.py",
    "scripts/xtb_real_dataset/analyze_xtb_real_dataset_distribution.py",
    "scripts/xtb_real_dataset/convert_xtb_real_dataset_geom_pickle.py",
    "scripts/xtb_real_dataset/convert_xtb_real_dataset_sdf.py",
    "scripts/xtb_real_dataset/inspect_xtb_real_dataset_availability.py",
    "scripts/xtb_real_dataset/prepare_xtb_real_dataset_sample.py",
    "scripts/xtb_real_dataset/run_xtb_real_dataset_distribution.py",
}


def test_scripts_are_grouped_by_purpose() -> None:
    paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "scripts").rglob("*.py")
        if "__pycache__" not in path.parts
    }

    assert paths == EXPECTED_SCRIPT_PATHS | {"scripts/__init__.py"}


def test_scripts_top_level_only_contains_package_marker() -> None:
    top_level_python_files = {
        path.name
        for path in (ROOT / "scripts").glob("*.py")
        if "__pycache__" not in path.parts
    }

    assert top_level_python_files == {"__init__.py"}
