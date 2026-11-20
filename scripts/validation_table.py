"""Print the RRUFF validation results as a Markdown table for the README.

Usage: python scripts/validation_table.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from test_validation_rruff import DATA, MINERALS, validate  # noqa: E402

print("| Mineral | Reference 2θ (°) | Found 2θ (°) | Δ (°) |")
print("|---|---|---|---|")
for mineral in MINERALS:
    if not (DATA / f"{mineral}.txt").exists():
        continue
    for ref_tt, found, delta in validate(mineral):
        print(f"| {mineral} | {ref_tt:.3f} | {found:.3f} | {delta:+.3f} |")
