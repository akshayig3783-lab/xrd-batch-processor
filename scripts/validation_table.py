"""Print the RRUFF validation results as a Markdown table for the README.

Usage: python scripts/validation_table.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from test_validation_rruff import DATA, MINERALS, validate  # noqa: E402

print("| Mineral | Found 2θ (°) | Calculated 2θ (°) | Δ (°) |")
print("|---|---|---|---|")
for mineral in MINERALS:
    if not (DATA / f"{mineral}.txt").exists():
        continue
    for found, ref_tt, delta in validate(mineral):
        print(f"| {mineral} | {found:.3f} | {ref_tt:.3f} | {delta:+.3f} |")
