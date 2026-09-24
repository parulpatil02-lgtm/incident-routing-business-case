"""
Checks that the analysis can be trusted.

  1. Independent recomputation: the hand-off counts derived in pandas are
     recomputed in SQL (window functions) and must match exactly.
  2. Data invariants on the incident table.
  3. No leakage: the router is trained only on earlier incidents than it is
     tested on, and is never given a field that reveals the answer.

Run:  python tests/test_analysis.py
"""
import importlib.util
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sql_results() -> tuple[pd.Series, pd.DataFrame]:
    events = pd.read_csv(ROOT / "data" / "raw" / "incident_log.zip",
                         usecols=["number", "sys_mod_count", "assignment_group", "category"])
    conn = sqlite3.connect(":memory:")
    events.to_sql("events", conn, index=False)  # rowid follows file order, matching the stable sort in pandas
    totals = pd.read_sql((ROOT / "sql" / "01_handoffs.sql").read_text(encoding="utf-8"), conn).iloc[0]
    by_category = pd.read_sql((ROOT / "sql" / "02_handoffs_by_category.sql").read_text(encoding="utf-8"), conn)
    conn.close()
    return totals, by_category


def main():
    failures = 0

    def check(ok: bool, label: str):
        nonlocal failures
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")

    incidents = pd.read_csv(ROOT / "data" / "processed" / "incidents.csv", parse_dates=["opened_at", "resolved_at"])
    has_group = incidents.dropna(subset=["initial_group"])

    # 1. SQL vs pandas
    totals, by_category = sql_results()
    check(int(totals.incidents_with_a_group) == len(has_group), f"incidents with a group: SQL {int(totals.incidents_with_a_group):,} = pandas {len(has_group):,}")
    check(int(totals.total_handoffs) == int(incidents.group_changes.sum()), f"total hand-offs: SQL {int(totals.total_handoffs):,} = pandas {int(incidents.group_changes.sum()):,}")
    check(int(totals.incidents_that_changed_hands) == int((incidents.group_changes > 0).sum()), "incidents that changed hands: SQL = pandas")
    pandas_by_cat = incidents.dropna(subset=["category", "initial_group"]).groupby("category").group_changes.sum()
    top = by_category.head(10)
    same = all(int(pandas_by_cat[row.category]) == int(row.handoffs) for row in top.itertuples())
    check(same, "hand-offs for the top 10 categories: SQL = pandas")

    # 2. Invariants
    check(incidents.number.is_unique and len(incidents) == 24918, "24,918 unique incidents")
    check((incidents.group_changes >= 0).all(), "no negative hand-off counts")
    check((incidents.resolution_hours.dropna() >= 0).all(), "no negative resolution times")
    check(incidents.initial_group.isna().sum() == 373, "373 incidents never had a group assigned (documented in the README)")

    # 3. No leakage
    poc = load_script("03_routing_poc")
    d = poc.load()
    cut = int(len(d) * (1 - poc.TEST_SHARE))
    train, test = d.iloc[:cut], d.iloc[cut:]
    check(train.opened_at.max() <= test.opened_at.min(), "every training incident was opened before every test incident")
    forbidden = {"final_group", "initial_group", "group_changes", "resolved_at", "resolution_hours", "made_sla", "reopen_count"}
    check(not (forbidden & set(poc.FEATURES)), "router features exclude anything that reveals the outcome")

    print(f"\n{'ALL PASSED' if not failures else f'{failures} FAILURE(S)'}")
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
