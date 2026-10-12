#!/usr/bin/env python3
"""
Input:  data/07_opm_contract_labels.json       (Allium labels)
        data/07b_opm_contract_labels_dune.json (Dune labels)
Output: data/07c_opm_contract_labels_combined.json
Transform: join the two label sets on address. One row per address; Dune columns carry a dune_ prefix.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
allium = json.loads((root / "data/07_opm_contract_labels.json").read_text())
dune = {r["address"]: r for r in json.loads((root / "data/07b_opm_contract_labels_dune.json").read_text())}

dune_cols = ["dune_label_name", "dune_label_category", "dune_namespace", "dune_contract_name",
             "dune_owner", "dune_token_symbol", "dune_cex_name", "dune_persona"]
rows = [{**r, **{c: dune.get(r["address"], {}).get(c) for c in dune_cols}} for r in allium]
(root / "data/07c_opm_contract_labels_combined.json").write_text(json.dumps(rows, indent=2))
print(f"{len(rows):,} rows")
