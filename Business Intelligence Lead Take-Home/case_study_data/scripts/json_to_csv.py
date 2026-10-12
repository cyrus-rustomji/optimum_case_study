#!/usr/bin/env python3
"""
Input:  data/*.json   (bare JSON arrays from allium_query.py / defillama run.py)
Output: csv/*.csv     (same file stem, one column per key, header row first)
Transform: none, format change only. Booleans are written as true/false; nulls as empty cells.
The two single-source label files (07, 07b) are skipped; the combined file 07c is written as
csv/07_opm_contract_labels.csv.
"""
import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
SKIP = {"07_opm_contract_labels", "07b_opm_contract_labels_dune"}
RENAME = {"07c_opm_contract_labels_combined": "07_opm_contract_labels"}

for src in sorted((root / "data").glob("*.json")):
    if src.stem in SKIP:
        continue
    rows = json.loads(src.read_text())
    cols = list(rows[0].keys())
    out = root / "csv" / f"{RENAME.get(src.stem, src.stem)}.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r[c] is None else str(r[c]).lower() if isinstance(r[c], bool) else r[c] for c in cols])
    print(f"{out.name}: {len(rows):,} rows")
