"""Load the test cases in eval/cases/."""

from __future__ import annotations

import json
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent.parent / "eval" / "cases"


def load_cases(case_dir: Path = CASE_DIR) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(case_dir.glob("*.json"))]
