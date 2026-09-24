"""
Turns the raw event log (one row per ticket update) into one row per incident,
with the fields the analysis needs: who it was first assigned to, who finally
resolved it, how many times it changed hands, and how long it took.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "incident_log.zip"
OUT = ROOT / "data" / "processed" / "incidents.csv"

DATE_FORMAT = "%d/%m/%Y %H:%M"
# Attributes known when a ticket is opened: what a router could use.
OPEN_TIME_FIELDS = [
    "category", "subcategory", "u_symptom", "location", "contact_type", "impact", "urgency",
    "caller_id", "opened_by",
]


def first_known(series: pd.Series) -> str | None:
    known = series[series != "?"]
    return known.iloc[0] if len(known) else None


def build_incident_table(raw_path: Path = RAW) -> pd.DataFrame:
    events = pd.read_csv(raw_path, low_memory=False)
    # sys_mod_count increases with every update to a ticket, so it gives event order.
    events = events.sort_values(["number", "sys_mod_count"], kind="stable")

    # Group changes: compare each known assignment group with the previous known one.
    known = events[events["assignment_group"] != "?"].copy()
    previous = known.groupby("number")["assignment_group"].shift()
    known["changed"] = previous.notna() & (known["assignment_group"] != previous)
    group_stats = known.groupby("number").agg(
        initial_group=("assignment_group", "first"),
        final_group=("assignment_group", "last"),
        group_changes=("changed", "sum"),
    )

    by_incident = events.groupby("number")
    incidents = pd.DataFrame(
        {
            "opened_at": pd.to_datetime(by_incident["opened_at"].first(), format=DATE_FORMAT, errors="coerce"),
            "resolved_at": pd.to_datetime(by_incident["resolved_at"].last(), format=DATE_FORMAT, errors="coerce"),
            "final_state": by_incident["incident_state"].last(),
            "priority": by_incident["priority"].last(),
            "made_sla": by_incident["made_sla"].last(),
            "reopen_count": by_incident["reopen_count"].max(),
            "n_events": by_incident.size(),
        }
    )
    for field in OPEN_TIME_FIELDS:
        incidents[field] = by_incident[field].agg(first_known)

    incidents = incidents.join(group_stats)
    incidents["group_changes"] = incidents["group_changes"].fillna(0).astype(int)
    incidents["resolution_hours"] = (incidents["resolved_at"] - incidents["opened_at"]).dt.total_seconds() / 3600
    return incidents.reset_index()


def main():
    incidents = build_incident_table()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    incidents.to_csv(OUT, index=False)
    print(f"{len(incidents):,} incidents -> {OUT}")


if __name__ == "__main__":
    main()
