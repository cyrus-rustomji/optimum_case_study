"""Shared paths, analysis windows, and a DuckDB connection with every case-study CSV registered as a view.

Every downstream script imports from here so the window and the source paths are defined once.
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "Business Intelligence Lead Take-Home" / "case_study_data" / "csv"
EXTERNAL = ROOT / "external"
SQL = ROOT / "sql"
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"

# Last 12 months of data (data ends 2026-09-15) and the 12 months before it.
L12M = ("2025-09-16", "2026-09-15")
P12M = ("2024-09-16", "2025-09-15")  # data only starts 2025-01-01, so this is a partial prior period
FIRST_DAY = "2025-01-01"

VIEWS = {
    "fees": "01_opm_fees_daily",
    "eth_price": "02_eth_price_daily",
    "activity": "03_opm_activity_daily",
    "new_addr": "04_opm_new_addresses_daily",
    "deploys": "05_opm_contract_deployments_daily",
    "contract_activity": "06_opm_contract_activity_daily",
    "labels": "07_opm_contract_labels",
    "app_fees": "08_opm_app_fees_revenue_daily",
    "dex": "09_opm_dex_volume_daily",
    "lending": "10_opm_lending_daily",
    "tvl": "11_opm_tvl_by_protocol_daily",
    "stables": "12_opm_stablecoins_daily",
    "bridges": "13_opm_bridge_flows_daily",
    "cex": "14_opm_cex_flows_daily",
}


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for view, stem in VIEWS.items():
        # all_varchar off; let DuckDB sniff types. Labels file is all text by nature.
        con.execute(f"CREATE VIEW {view} AS SELECT * FROM read_csv_auto('{DATA / (stem + '.csv')}', header=true)")
    l1 = EXTERNAL / "l1_costs_daily.csv"
    if l1.exists():
        # explicit types: the on-chain columns can be entirely empty, which the sniffer would read as VARCHAR
        # (read_csv's `columns` is positional, so build it in the file's header order)
        header = l1.open().readline().strip().split(",")
        cols = {c: "DATE" if c == "date" else "DOUBLE" for c in header}
        con.execute(f"CREATE VIEW l1_costs AS SELECT * FROM read_csv('{l1}', header=true, columns={cols})")
    con.execute(f"SET VARIABLE l12m_start = DATE '{L12M[0]}'")
    con.execute(f"SET VARIABLE l12m_end = DATE '{L12M[1]}'")
    return con


def run_sql(con: duckdb.DuckDBPyConnection, name: str):
    """Run sql/<name>.sql and return a DataFrame. SQL files may contain several statements; the last one returns."""
    text = (SQL / f"{name}.sql").read_text()
    # drop full-line comments first so a ';' inside a comment can't split a statement
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--"))
    stmts = [s for s in text.split(";") if s.strip()]
    for s in stmts[:-1]:
        con.execute(s)
    return con.execute(stmts[-1]).df()


def save(df, name: str):
    TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / f"{name}.csv", index=False)
    return df
