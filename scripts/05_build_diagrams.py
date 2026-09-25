"""
Current-state and proposed-state process diagrams for the Category 23 path.
Every number on them is read from the analysis outputs.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
ASSETS = ROOT / "docs" / "assets"

TEAL, TEAL_SOFT, AMBER, AMBER_SOFT, GREY_SOFT, INK = "#1F6F5C", "#E3EFE9", "#AD5F1E", "#F4E6D6", "#EEF0EA", "#1B211D"


def box(ax, x, y, w, h, text, fill, edge, size=8.5, bold=False, dashed=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", fc=fill, ec=edge,
                                lw=1.4, ls="--" if dashed else "-"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=INK,
            fontweight="bold" if bold else "normal", linespacing=1.35)


def arrow(ax, x1, y1, x2, y2, label=None, color=INK, dashed=False):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3, ls="--" if dashed else "-", shrinkA=0, shrinkB=0))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.6, label, ha="center", va="bottom", fontsize=7.5, color=color)


def canvas(title):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")
    ax.text(1, 54, title, fontsize=11.5, fontweight="bold", color=INK, va="top")
    return fig, ax


def lanes(ax, labels):
    for y, label in labels:
        ax.add_patch(plt.Rectangle((0, y), 100, 15.5, fc=GREY_SOFT, ec="none", zorder=0))
        ax.text(1, y + 14.6, label, fontsize=7.5, color="#4E594F", va="top", fontweight="bold")


def current_state(m, flows, by_month):
    # Tickets that start in the most common first group, and where they end up.
    first_group = flows.groupby("initial_group").incidents.sum().idxmax()
    ends = flows[flows.initial_group == first_group].set_index("final_group").share_of_category
    top_two = ends.drop(first_group, errors="ignore").nlargest(2)
    stay = ends.get(first_group, 0.0)
    other = 1 - top_two.sum() - stay
    first, last = by_month.iloc[0], by_month.iloc[-1]
    month_name = lambda row: pd.Period(row.month).strftime("%b")

    fig, ax = canvas(f"Current state: {m['focus_category']} tickets, {m['core_period_start'][:7]} to {m['core_period_end'][:7]}")
    lanes(ax, [(34, "SERVICE DESK"), (18, f"{first_group.upper()} (first assignment)"), (2, "WHO ACTUALLY RESOLVES IT")])
    box(ax, 4, 38, 22, 8, f"Ticket opened\n{by_month.incidents.mean():.0f} per month", "white", TEAL)
    box(ax, 32, 38, 26, 8, f"Assigned to {first_group}\n(default for this category)", "white", TEAL)
    arrow(ax, 26.6, 42, 31.4, 42)
    box(ax, 32, 22, 26, 8, f"{first_group} cannot resolve it\n{m['focus_bounce_rate']:.0%} of tickets change hands", AMBER_SOFT, AMBER, bold=True)
    arrow(ax, 45, 37.6, 45, 30.8, color=AMBER)
    destinations = [(4, top_two.index[0], top_two.iloc[0]), (26, top_two.index[1], top_two.iloc[1]),
                    (48, f"{first_group} itself", stay), (70, "Many other\ngroups", other)]
    for x, name, share in destinations:
        box(ax, x, 5, 20, 8, f"{name}\n{share:.0%} of tickets", "white", AMBER if name.startswith("Many") else TEAL)
        arrow(ax, 45, 21.6, x + 13, 13.8, color=AMBER)
    ax.text(62, 34.3, f"First time right fell\nfrom {first.today_first_time_right:.0%} ({month_name(first)}) to {last.today_first_time_right:.0%} ({month_name(last)})", fontsize=8.5, color=AMBER,
            fontweight="bold", va="center", linespacing=1.4)
    ax.text(62, 28.6, f"Each hand-off: median +{m['like_for_like_extra_median_hours']:.1f} hours to resolve,\n"
                      f"{m['like_for_like_sla_gap_pts']:.0f} fewer points meeting SLA", fontsize=8, color=INK, va="center",
            linespacing=1.5)
    ax.text(62, 24.4, "(like-for-like, all categories;\nan association, not proof of cause)", fontsize=7, color="#4E594F",
            va="center", linespacing=1.4)
    fig.savefig(ASSETS / "process_current.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def proposed_state(policy):
    today, rule = float(policy["today_accuracy_in_chosen"]), float(policy["rule_accuracy_in_chosen_single_group"])
    rule_text = policy["single_group_rule"].replace(" -> ", " goes to ")
    category, group = policy["single_group_rule"].split(" -> ")
    fig, ax = canvas("Proposed state: one assignment rule, then measure and review")
    lanes(ax, [(34, "SERVICE DESK / ASSIGNMENT RULES"), (18, group.upper()), (2, "CONTINUOUS IMPROVEMENT")])
    box(ax, 4, 38, 18, 8, f"Ticket opened\n({category})", "white", TEAL)
    box(ax, 30, 38, 30, 8, f"Assignment rule\n{rule_text}", TEAL_SOFT, TEAL, bold=True)
    arrow(ax, 22.6, 42, 29.4, 42)
    box(ax, 30, 22, 30, 8, f"{group} works the ticket", "white", TEAL)
    arrow(ax, 45, 37.6, 45, 30.8)
    box(ax, 68, 22, 27, 8, f"Resolved by {group}\n{rule:.0%} of tickets in testing\n(today: {today:.0%})", TEAL_SOFT, TEAL, bold=True)
    arrow(ax, 60.6, 26, 67.4, 26)
    box(ax, 68, 38, 27, 8, "Not theirs: reassign and\nrecord a reason code", AMBER_SOFT, AMBER, dashed=True)
    arrow(ax, 60.6, 28.5, 68, 38.2, color=AMBER, dashed=True)
    box(ax, 4, 5, 26, 8, "Before go-live: ask what\nchanged between Mar and May", "white", AMBER, dashed=True)
    box(ax, 36, 5, 26, 8, f"Track first-time-right\nweekly for {category}", "white", TEAL)
    box(ax, 68, 5, 27, 8, "Monthly review of reason\ncodes; decide the next fix", "white", TEAL)
    arrow(ax, 30.6, 9, 35.4, 9)
    arrow(ax, 62.6, 9, 67.4, 9)
    # Route the reason-code feed down the right edge so it doesn't cross the "Resolved" box.
    ax.plot([95.6, 98.6, 98.6], [42, 42, 9], color=AMBER, lw=1.3, ls="--")
    arrow(ax, 98.6, 9, 95.6, 9, color=AMBER, dashed=True)
    fig.savefig(ASSETS / "process_proposed.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(PROCESSED / "current_state_metrics.csv", index_col="metric")["value"]
    m = metrics.to_dict()
    for k in ["focus_incidents", "core_months", "focus_bounce_rate", "like_for_like_extra_median_hours", "like_for_like_sla_gap_pts"]:
        m[k] = float(m[k])
    flows = pd.read_csv(PROCESSED / "category23_flows.csv")
    by_month = pd.read_csv(PROCESSED / "category23_by_month.csv")
    policy = pd.read_csv(PROCESSED / "selective_policy.csv", index_col="metric")["value"]
    current_state(m, flows, by_month)
    proposed_state(policy)
    print("wrote process_current.png and process_proposed.png")


if __name__ == "__main__":
    main()
