"""Smoke-check the local xTB verifier environment."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from verifiers.backends.xtb_properties import XTBRunner, parse_xtb_output  # noqa: E402


WATER_XYZ = """3
water
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284
"""


def main() -> int:
    executable = shutil.which("xtb")
    if executable is None:
        print(
            json.dumps(
                {
                    "status": "error",
                    "failure_type": "verifier_environment_error",
                    "message": "xTB executable not found on PATH",
                    "xtb_executable": None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    version = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False, timeout=20)
    checks: dict[str, object] = {
        "status": "ok",
        "xtb_executable": executable,
        "xtb_version": (version.stdout or version.stderr).strip(),
        "water_smoke": None,
    }
    with tempfile.TemporaryDirectory(prefix="xtb-env-check-") as temp_dir:
        xyz_path = Path(temp_dir) / "water.xyz"
        xyz_path.write_text(WATER_XYZ)
        runner = XTBRunner("xtb")
        result = runner.run(
            "optimize",
            xyz_path,
            120,
            spec={"backend": {"charge": 0, "uhf": 0}},
        )
        checks["water_smoke"] = parse_xtb_output(result.stdout, require_converged=True)

    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
