#!/usr/bin/env python
"""Score answer JSONL files through configured verifier scripts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verifier_grounded_benchmark.cli.score_answers import main


if __name__ == "__main__":
    raise SystemExit(main())
