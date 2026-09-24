"""
Current-state analysis: how often do incidents change hands, what does it
cost in time and SLA, and where is it concentrated?

Two guards against overstating the case:
  * The raw gap between incidents that bounced and ones that didn't is inflated
    by difficulty (hard tickets get passed around), so delay is also measured
    like-for-like: within the group that finally resolved the ticket.
  * Volume is reported per month over the months the data really covers, not
    scaled up from the date span (98% of incidents were opened in 3 months).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INCIDENTS = ROOT / "data" / "processed" / "incidents.csv"
OUT = ROOT / "data" / "processed"
ASSETS = ROOT / "docs" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

ACCENT, WARN, INK = "#1F6F5C", "#AD5F1E", "#1B211D"
MIN_PER_ARM = 30  # each side of a like-for-like comparison needs enough incidents
MIN_OPENER_TICKETS = 200
CORE_MONTH_SHARE = 0.05  # a month counts as "covered" if it holds at least this share of incidents
FOCUS_CATEGORY = "Category 23"


def load() -> pd.DataFrame:
    d = pd.read_csv(INCIDENTS, parse_dates=["opened_at", "resolved_at"])
    d["bounced"] = d.group_changes > 0
    return d


def core_period(d: pd.DataFrame) -> tuple[pd.Series, int]:
    months = d.opened_at.dt.to_period("M")
    share = months.value_counts(normalize=True)
    core = share[share >= CORE_MONTH_SHARE].index
    return months.isin(core), len(core)


def like_for_like(resolved: pd.DataFrame) -> pd.DataFrame:
    """Bounced vs non-bounced, within the group that finally resolved the ticket."""
    rows = []
    for group, g in resolved.groupby("final_group"):
        ok, bounced = g[~g.bounced], g[g.bounced]
        if len(ok) >= MIN_PER_ARM and len(bounced) >= MIN_PER_ARM:
            rows.append(
                {
                    "final_group": group,
                    "n_bounced": len(bounced),
                    "n_not_bounced": len(ok),
                    "median_hours_bounced": bounced.resolution_hours.median(),
                    "median_hours_not_bounced": ok.resolution_hours.median(),
                    "sla_bounced": bounced.made_sla.mean(),
                    "sla_not_bounced": ok.made_sla.mean(),
                }
            )
    out = pd.DataFrame(rows)
    out["extra_median_hours"] = out.median_hours_bounced - out.median_hours_not_bounced
    out["sla_gap_pts"] = (out.sla_not_bounced - out.sla_bounced) * 100
    return out


def opener_variation(resolved: pd.DataFrame) -> pd.DataFrame:
    """Does the hand-off rate depend on who opened the ticket, beyond the mix of
    categories they handle? z compares actual with expected, using the binomial
    spread that chance alone would produce."""
    r = resolved.assign(p=resolved.groupby("category").bounced.transform("mean"))
    r["var"] = r.p * (1 - r.p)
    by = r.groupby("opened_by").agg(n=("bounced", "size"), actual=("bounced", "mean"),
                                    expected=("p", "mean"), var_sum=("var", "sum"))
    by = by[by.n >= MIN_OPENER_TICKETS].copy()
    by["gap_pts"] = (by.actual - by.expected) * 100
    by["z"] = (by.actual - by.expected) * by.n / np.sqrt(by.var_sum)
    return by.drop(columns="var_sum").sort_values("gap_pts")


def main():
    d = load()
    resolved = d[d.resolution_hours.notna()].copy()
    in_core, core_months = core_period(d)

    lfl = like_for_like(resolved)
    opener = opener_variation(resolved)
    by_cat = (
        resolved.groupby("category")
        .agg(incidents=("number", "size"), bounce_rate=("bounced", "mean"), handoffs=("group_changes", "sum"))
        .query("incidents >= 200")
        .sort_values("handoffs", ascending=False)
    )
    by_cat["share_of_handoffs"] = by_cat.handoffs / resolved.group_changes.sum()

    focus = resolved[resolved.category == FOCUS_CATEGORY]
    flows = (
        focus.dropna(subset=["initial_group", "final_group"])
        .groupby(["initial_group", "final_group"]).size().rename("incidents").reset_index()
        .sort_values("incidents", ascending=False)
    )
    flows["share_of_category"] = flows.incidents / len(focus)

    m = {
        "incidents_total": len(d),
        "incidents_with_resolution_time": len(resolved),
        "core_months": core_months,
        "core_period_start": d.opened_at[in_core].min().date().isoformat(),
        "core_period_end": d.opened_at[in_core].max().date().isoformat(),
        "core_period_share_of_incidents": in_core.mean(),
        "incidents_per_month": round(in_core.sum() / core_months),
        "share_bounced": resolved.bounced.mean(),
        "share_bounced_2plus": (resolved.group_changes >= 2).mean(),
        "total_handoffs": int(resolved.group_changes.sum()),
        "handoffs_per_bounced_incident": resolved[resolved.bounced].group_changes.mean(),
        "median_hours_not_bounced": resolved[~resolved.bounced].resolution_hours.median(),
        "median_hours_bounced": resolved[resolved.bounced].resolution_hours.median(),
        "sla_not_bounced": resolved[~resolved.bounced].made_sla.mean(),
        "sla_bounced": resolved[resolved.bounced].made_sla.mean(),
        "like_for_like_groups": len(lfl),
        "like_for_like_share_of_bounced": lfl.n_bounced.sum() / resolved.bounced.sum(),
        "like_for_like_extra_median_hours": float(np.average(lfl.extra_median_hours, weights=lfl.n_bounced)),
        "like_for_like_sla_gap_pts": float(np.average(lfl.sla_gap_pts, weights=lfl.n_bounced)),
        "top10_categories_share_of_handoffs": by_cat.share_of_handoffs.head(10).sum(),
        "openers_analyzed": len(opener),
        "openers_min_gap_pts": opener.gap_pts.min(),
        "openers_max_gap_pts": opener.gap_pts.max(),
        "openers_beyond_chance": int((opener.z.abs() > 2).sum()),
        "focus_category": FOCUS_CATEGORY,
        "focus_incidents": len(focus),
        "focus_bounce_rate": focus.bounced.mean(),
        "focus_share_of_all_handoffs": focus.group_changes.sum() / resolved.group_changes.sum(),
        "focus_share_of_incidents": len(focus) / len(resolved),
        "focus_initial_equals_final": (focus.initial_group == focus.final_group).mean(),
    }
    pd.Series(m, name="value").to_frame().to_csv(OUT / "current_state_metrics.csv", index_label="metric")
    lfl.to_csv(OUT / "like_for_like_by_group.csv", index=False)
    by_cat.to_csv(OUT / "bounce_by_category.csv")
    opener.round(3).to_csv(OUT / "opener_variation.csv", index_label="opened_by")
    flows.round(4).to_csv(OUT / "category23_flows.csv", index=False)

    for k, v in m.items():
        print(f"{k}: {round(v, 3) if isinstance(v, float) else v}")
    print("top flows in", FOCUS_CATEGORY, "\n", flows.head(4).round(3).to_string(index=False))

    counts = resolved.group_changes.clip(upper=5).value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(6, 3.4))
    bars = ax.bar(["0", "1", "2", "3", "4", "5+"], counts.values / len(resolved) * 100, color=[ACCENT] + [WARN] * 5)
    ax.bar_label(bars, fmt="%.1f%%", fontsize=8)
    ax.set_xlabel("Times an incident changed teams")
    ax.set_ylabel("Share of incidents (%)")
    ax.set_title("Only 59% of incidents are resolved without changing hands", color=INK, fontsize=10, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "handoffs_distribution.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.4))
    for ax, key, title in zip(axes, [("median_hours_not_bounced", "median_hours_bounced"), ("sla_not_bounced", "sla_bounced")],
                              ["Median hours to resolve", "Incidents meeting SLA (%)"]):
        scale = 1 if "hours" in key[0] else 100
        ax.bar(["No hand-off", "Changed hands"], [m[key[0]] * scale, m[key[1]] * scale], color=[ACCENT, WARN])
        ax.set_title(title, fontsize=9, color=INK, fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        ax.bar_label(ax.containers[0], fmt="%.1f", fontsize=8)
    fig.tight_layout()
    fig.savefig(ASSETS / "cost_of_handoffs.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
