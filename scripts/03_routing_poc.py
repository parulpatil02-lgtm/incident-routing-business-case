"""
Proof of concept: could incidents have been routed to the group that finally
resolved them, using only what is known when a ticket is opened?

Three questions, answered on incidents the router never saw:
  1. Would a learned router beat today's routing?          (comparison)
  2. Is that answer an artifact of how it was tested?      (robustness)
  3. Is there a place where a simple rule clearly beats
     today's routing?  Categories are chosen on a validation slice of the
     TRAINING period only, then judged on the untouched test set.  (selective)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OrdinalEncoder

ROOT = Path(__file__).resolve().parents[1]
INCIDENTS = ROOT / "data" / "processed" / "incidents.csv"
RAW = ROOT / "data" / "raw" / "incident_log.zip"
OUT = ROOT / "data" / "processed"
ASSETS = ROOT / "docs" / "assets"

FEATURES = ["category", "subcategory", "u_symptom", "location", "contact_type", "impact", "urgency"]
EXTRA_FEATURES = ["caller_id", "opened_by"]  # tried in the robustness checks only
TABLE_LEVELS = [["category", "subcategory", "u_symptom"], ["category", "subcategory"], ["category"]]
MIN_SUPPORT = 5      # a rule needs this many past incidents behind it
TEST_SHARE = 0.30
VAL_SHARE = 0.30     # share of the training period held back to choose categories
MIN_VAL_INCIDENTS = 30
MIN_GAIN = 0.10      # a category is chosen only if the rule beats today by this much on validation
SEED = 42


def load() -> pd.DataFrame:
    d = pd.read_csv(INCIDENTS, parse_dates=["opened_at"])
    d = d.dropna(subset=["initial_group", "final_group"]).sort_values("opened_at").reset_index(drop=True)
    d[FEATURES + EXTRA_FEATURES] = d[FEATURES + EXTRA_FEATURES].fillna("MISSING")
    return d


def fit_routing_table(train: pd.DataFrame) -> list[tuple[list[str], dict, pd.DataFrame]]:
    """Most common resolving group for each key, from most to least specific."""
    tables = []
    for cols in TABLE_LEVELS:
        counts = train.groupby(cols + ["final_group"]).size().rename("n").reset_index()
        counts["support"] = counts.groupby(cols)["n"].transform("sum")
        top = counts.sort_values("n", ascending=False).drop_duplicates(cols)
        top["confidence"] = top.n / top.support
        top = top[top.support >= MIN_SUPPORT]
        mapping = {tuple(k): g for k, g in zip(top[cols].itertuples(index=False, name=None), top.final_group)}
        tables.append((cols, mapping, top))
    return tables


def predict_routing_table(df: pd.DataFrame, tables, fallback: str) -> np.ndarray:
    """The most specific rule that applies wins; the least specific level is applied first and overwritten."""
    predicted = pd.Series(fallback, index=df.index, dtype=object)
    for cols, mapping, _ in reversed(tables):
        keys = pd.Series(list(df[cols].itertuples(index=False, name=None)), index=df.index)
        hit = keys.isin(mapping)
        predicted[hit] = keys[hit].map(mapping)
    return predicted.to_numpy()


def forest_predict(train: pd.DataFrame, test: pd.DataFrame, features: list[str] = FEATURES) -> np.ndarray:
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    forest = RandomForestClassifier(n_estimators=100, min_samples_leaf=2, n_jobs=1, random_state=SEED)
    forest.fit(encoder.fit_transform(train[features]), train.final_group)
    return forest.predict(encoder.transform(test[features]))


def known_at_open_share() -> dict:
    """Are the routing fields actually filled in on a ticket's first record?"""
    cols = ["category", "subcategory", "u_symptom"]
    events = pd.read_csv(RAW, usecols=["number", "sys_mod_count"] + cols)
    first = events.sort_values(["number", "sys_mod_count"], kind="stable").groupby("number").first()
    return {f"{c}_known_at_open": float((first[c] != "?").mean()) for c in cols}


def score(name: str, predicted: np.ndarray, test: pd.DataFrame, current_ok: np.ndarray) -> dict:
    ok = predicted == test.final_group.to_numpy()
    bounced = test.group_changes.to_numpy() > 0
    p = ok.mean()
    return {
        "approach": name,
        "accuracy": p,
        "ci95_halfwidth": 1.96 * np.sqrt(p * (1 - p) / len(ok)),
        "accuracy_on_incidents_that_bounced": ok[bounced].mean(),
        "net_gain_vs_current_incidents": int((ok & ~current_ok).sum() - (~ok & current_ok).sum()),
        "test_incidents": len(test),
    }


def robustness(d: pd.DataFrame) -> pd.DataFrame:
    def row(label, predicted, chunk):
        return (label, (predicted == chunk.final_group.to_numpy()).mean(), (chunk.initial_group == chunk.final_group).mean(), len(chunk))

    cut = int(len(d) * (1 - TEST_SHARE))
    order = np.random.default_rng(SEED).permutation(len(d))
    tr, te = d.iloc[order[:cut]], d.iloc[order[cut:]]
    rows = [row("Random 70/30 split (not how it would be deployed)", forest_predict(tr, te), te)]
    tr, te = d.iloc[:cut], d.iloc[cut:]
    rows.append(row("Main test split, with the caller and the agent who opened the ticket added as fields",
                    forest_predict(tr, te, FEATURES + EXTRA_FEATURES), te))
    months = d.opened_at.dt.to_period("M")
    for month, chunk in d.groupby(months):
        past = d[d.opened_at < chunk.opened_at.min()]
        if len(past) >= 3000 and len(chunk) >= 100:
            rows.append(row(f"Retrained on everything before {month}, tested on {month}", forest_predict(past, chunk), chunk))
    return pd.DataFrame(rows, columns=["check", "router_accuracy", "today_accuracy", "test_incidents"])


def selective_policy(train_all: pd.DataFrame, test: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    cut = int(len(train_all) * (1 - VAL_SHARE))
    early, val = train_all.iloc[:cut], train_all.iloc[cut:].copy()
    val["table_ok"] = predict_routing_table(val, fit_routing_table(early), early.final_group.mode().iloc[0]) == val.final_group
    val["today_ok"] = val.initial_group == val.final_group
    by_cat = val.groupby("category").agg(n_val=("table_ok", "size"), rule_accuracy=("table_ok", "mean"),
                                         today_accuracy=("today_ok", "mean"))
    by_cat["gain"] = by_cat.rule_accuracy - by_cat.today_accuracy
    chosen = by_cat[(by_cat.n_val >= MIN_VAL_INCIDENTS) & (by_cat.gain >= MIN_GAIN)].index.tolist()

    tables = fit_routing_table(train_all)
    fallback = train_all.final_group.mode().iloc[0]
    table_pred = predict_routing_table(test, tables, fallback)
    # The simplest possible fix: one group per category (a single assignment rule).
    one_group = train_all[train_all.category.isin(chosen)].groupby("category").final_group.agg(lambda s: s.mode().iloc[0])
    single_pred = test.category.map(one_group).fillna(test.initial_group).to_numpy()

    y = test.final_group.to_numpy()
    today = (test.initial_group == test.final_group).to_numpy()
    use = test.category.isin(chosen).to_numpy()
    policy_pred = np.where(use, table_pred, test.initial_group.to_numpy())
    ok = policy_pred == y
    single_ok = single_pred == y
    result = {
        "categories_chosen_on_validation": ", ".join(chosen),
        "test_incidents": len(test),
        "test_incidents_in_chosen_categories": int(use.sum()),
        "share_of_test_incidents_affected": use.mean(),
        "today_accuracy_in_chosen": today[use].mean(),
        "rule_accuracy_in_chosen_table": (table_pred == y)[use].mean(),
        "rule_accuracy_in_chosen_single_group": single_ok[use].mean(),
        "single_group_rule": "; ".join(f"{c} -> {g}" for c, g in one_group.items()),
        "overall_accuracy_today": today.mean(),
        "overall_accuracy_with_policy": ok.mean(),
        "net_incidents_routed_right_instead_of_wrong": int((ok & ~today).sum() - (~ok & today).sum()),
        "net_incidents_single_group_rule": int((single_ok & ~today).sum() - (~single_ok & today).sum()),
    }
    return result, by_cat.round(3)


def main():
    d = load()
    cut = int(len(d) * (1 - TEST_SHARE))
    train_all, test = d.iloc[:cut], d.iloc[cut:]
    core_test = (test.opened_at.dt.to_period("M") == test.opened_at.dt.to_period("M").mode().iloc[0]).mean()
    print(f"train {len(train_all):,} incidents ({train_all.opened_at.min().date()} to {train_all.opened_at.max().date()}); "
          f"test {len(test):,} ({core_test:.0%} of them opened in {test.opened_at.dt.to_period('M').mode().iloc[0]})")

    current_ok = (test.initial_group == test.final_group).to_numpy()
    majority = train_all.final_group.mode().iloc[0]
    tables = fit_routing_table(train_all)
    metrics = pd.DataFrame([
        score("Today's routing (first assignment)", test.initial_group.to_numpy(), test, current_ok),
        score("Always the most common group", np.full(len(test), majority), test, current_ok),
        score("Routing table (rules from history)", predict_routing_table(test, tables, majority), test, current_ok),
        score("Random forest (machine learning)", forest_predict(train_all, test), test, current_ok),
    ])
    metrics.to_csv(OUT / "routing_metrics.csv", index=False)

    robust = robustness(d)
    robust.to_csv(OUT / "routing_robustness.csv", index=False)

    policy, per_category = selective_policy(train_all, test)
    pd.Series(policy, name="value").to_frame().to_csv(OUT / "selective_policy.csv", index_label="metric")
    per_category.to_csv(OUT / "validation_by_category.csv", index_label="category")
    pd.Series(known_at_open_share(), name="value").to_frame().to_csv(OUT / "fields_known_at_open.csv", index_label="field")

    rules = tables[1][2][["category", "subcategory", "final_group", "support", "confidence"]]
    rules.rename(columns={"final_group": "route_to_group"}).sort_values("support", ascending=False) \
        .round({"confidence": 3}).to_csv(OUT / "routing_rules_category_subcategory.csv", index=False)

    print(metrics.round(3).to_string(index=False))
    print(robust.round(3).to_string(index=False))
    for k, v in policy.items():
        print(f"{k}: {round(v, 3) if isinstance(v, float) else v}")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axes[0]
    bars = ax.bar(["Today", "Most common\ngroup", "Routing\ntable", "Random\nforest"], metrics.accuracy * 100,
                  yerr=metrics.ci95_halfwidth * 100, color=["#1F6F5C", "#7C877D", "#7C877D", "#7C877D"], capsize=3)
    ax.bar_label(bars, fmt="%.1f%%", padding=6, fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Sent to resolving group (%)")
    ax.set_title("Across all categories: no router beats today", fontsize=8.5, fontweight="bold", color="#1B211D")
    ax = axes[1]
    bars = ax.bar(["Today", "Simple\nrule"], [policy["today_accuracy_in_chosen"] * 100,
                                          policy["rule_accuracy_in_chosen_single_group"] * 100], color=["#7C877D", "#AD5F1E"])
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_title(f"{policy['categories_chosen_on_validation']} only", fontsize=8.5, fontweight="bold", color="#1B211D")
    for a in axes:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "routing_accuracy.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
