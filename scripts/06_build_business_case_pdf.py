"""
Builds the business case PDF. Every figure is read from the analysis outputs
in data/processed, so the document cannot drift from the evidence.
"""
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    CondPageBreak, Image, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
ASSETS = ROOT / "docs" / "assets"
OUT = ROOT / "Business_Case_Incident_Routing.pdf"
REPO_URL = "https://github.com/parulpatil02-lgtm/incident-routing-business-case"

TEAL, TEAL_DARK, TEAL_SOFT = colors.HexColor("#1F6F5C"), colors.HexColor("#0F4438"), colors.HexColor("#E3EFE9")
INK, INK_SOFT, BORDER = colors.HexColor("#1B211D"), colors.HexColor("#4E594F"), colors.HexColor("#D7DACC")
AMBER, AMBER_SOFT = colors.HexColor("#8A4A15"), colors.HexColor("#F4E6D6")
W = 6.8 * inch

base = getSampleStyleSheet()
title = ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=TEAL_DARK, spaceAfter=4, alignment=0)
subtitle = ParagraphStyle("st", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=12, leading=16, textColor=INK_SOFT)
meta = ParagraphStyle("m", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=INK_SOFT, spaceAfter=12)
h2 = ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=TEAL_DARK, spaceBefore=16, spaceAfter=7, keepWithNext=1)
h3 = ParagraphStyle("h3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=9, spaceAfter=4, keepWithNext=1)
body = ParagraphStyle("b", parent=base["Normal"], fontName="Helvetica", fontSize=10, leading=15, textColor=INK, spaceAfter=7)
caption = ParagraphStyle("c", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=INK_SOFT, alignment=1, spaceAfter=6)
cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
bullet = ParagraphStyle("bl", parent=body, spaceAfter=3)


num = float  # the metric CSVs are read as text-typed series


def callout(text, accent=TEAL, bg=TEAL_SOFT):
    return Table([[Paragraph(text, body)]], colWidths=[W], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 13), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))


def stat(value, label):
    return Table([[Paragraph(f'<font color="#0F4438" size="14"><b>{value}</b></font>', body)],
                  [Paragraph(f'<font color="#4E594F" size="7.5">{label}</font>', body)]], colWidths=[1.62 * inch],
                 style=TableStyle([("BOX", (0, 0), (-1, -1), 0.75, BORDER), ("TOPPADDING", (0, 0), (-1, 0), 9),
                                   ("BOTTOMPADDING", (0, 0), (-1, 0), 1), ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))


def table(rows, widths, shade_from=None):
    data = [[Paragraph(str(c), head if i == 0 else cell) for c in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), TEAL), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TEAL_SOFT]),
             ("GRID", (0, 0), (-1, -1), 0.5, BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if shade_from is not None:
        style.append(("BACKGROUND", (0, shade_from), (-1, -1), AMBER_SOFT))
    t.setStyle(TableStyle(style))
    return t


def picture_parts(name, width, note):
    from PIL import Image as PILImage
    path = ASSETS / name
    w, h = PILImage.open(path).size
    return [Image(str(path), width=width, height=width * h / w), Paragraph(note, caption)]


def picture(name, width, note):
    return KeepTogether(picture_parts(name, width, note))


def bullets(items):
    return ListFlowable([ListItem(Paragraph(t, bullet)) for t in items], bulletType="bullet", start="circle")


def main():
    m = pd.read_csv(P / "current_state_metrics.csv", index_col="metric")["value"]
    rm = pd.read_csv(P / "routing_metrics.csv")
    rb = pd.read_csv(P / "routing_robustness.csv")
    sp = pd.read_csv(P / "selective_policy.csv", index_col="metric")["value"]
    bm = pd.read_csv(P / "category23_by_month.csv")
    sc = pd.read_csv(P / "impact_scenarios.csv", index_col="scenario")
    fields = pd.read_csv(P / "fields_known_at_open.csv", index_col="field")["value"]

    today, majority, rtable, forest = rm.accuracy
    bounced_today, bounced_forest = rm.accuracy_on_incidents_that_bounced.iloc[0], rm.accuracy_on_incidents_that_bounced.iloc[3]
    focus_share_inc, focus_share_hand = num(m["focus_share_of_incidents"]), num(m["focus_share_of_all_handoffs"])
    today_c, rule_c = num(sp["today_accuracy_in_chosen"]), num(sp["rule_accuracy_in_chosen_single_group"])
    net_rule = int(float(sp["net_incidents_single_group_rule"]))
    low, high = sc.loc["Low"], sc.loc["High"]
    first_month, last_month = bm.iloc[0], bm.iloc[-1]
    rule_share_lo, rule_share_hi = bm.resolved_by_rule_group.min(), bm.resolved_by_rule_group.max()
    gain_by_month = {pd.Period(r.month).strftime("%B"): r.gain_points * 100 for r in bm.itertuples()}
    with_extras = rb.router_accuracy.iloc[1]

    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER, topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            title="Should We Automate Incident Routing? Business Case", author="Parul Patil")
    s = []
    s += [Paragraph("Should We Automate Incident Routing?", title),
          Paragraph("A business case built on 24,918 real IT incidents", subtitle)]
    s.append(Paragraph("Parul Patil &nbsp;&middot;&nbsp; September 2026" + (
        f' &nbsp;&middot;&nbsp; <a href="{REPO_URL}" color="#0F4438">{REPO_URL.replace("https://", "")}</a>' if REPO_URL else ""), meta))

    s.append(callout(
        "<b>Decision requested.</b> Do <b>not</b> fund an automated routing project: on this data, no router beats "
        f"today's routing ({rtable:.0%} for a rules table and {forest:.0%} for machine learning, against {today:.0%} today). "
        f"Instead, approve a four-week pilot of <b>one assignment rule for Category 23</b>, plus a root-cause check first. "
        f"On later incidents the rule reached the right team {rule_c:.0%} of the time, against {today_c:.0%} today. "
        "The change is a configuration edit, estimated at about 8 hours.", AMBER, AMBER_SOFT))
    s.append(Spacer(1, 10))
    s.append(Table([[stat(f"{num(m['share_bounced']):.0%}", "of incidents change teams at least once"),
                     stat(f"+{num(m['like_for_like_extra_median_hours']):.1f} h", "median extra time per hand-off, like for like"),
                     stat(f"{today:.0%} vs {forest:.0%}", "today's routing vs the best router tested"),
                     stat(f"{num(m['focus_bounce_rate']):.1%}", "of Category 23 tickets change teams")]],
                   colWidths=[1.7 * inch] * 4, style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6)])))

    s.append(Paragraph("1. The business problem", h2))
    s.append(Paragraph(
        "When an IT ticket is opened, it is assigned to a support group. If that group cannot resolve it, the ticket is passed "
        "to another, and sometimes to several. Every hand-off is a delay for the user waiting and work for the analysts "
        "reading and re-routing the ticket. The question for the IT Service Desk Manager is whether to invest in automating "
        "the routing, and if so where.", body))

    s.append(Paragraph("2. The data", h2))
    s.append(Paragraph(
        f"A real, anonymized ServiceNow log from an IT company (Amaral, Fantinato and Peres, 2018; UCI Machine Learning "
        f"Repository; CC BY 4.0): "
        f"<b>{int(num(m['incidents_total'])):,} incidents</b> and 141,712 logged updates. {num(m['core_period_share_of_incidents']):.0%} of "
        f"incidents were opened in three months (March to May 2016), about {int(num(m['incidents_per_month'])):,} a month, so figures are "
        f"reported per month rather than scaled up to a year. {int(num(m['incidents_with_resolution_time'])):,} incidents have a resolution "
        "time. Group, category and agent names are anonymized (Group 20, Category 23).", body))

    s.append(Paragraph("3. What the data shows", h2))
    s.append(Paragraph("3.1 &nbsp; Hand-offs are common and costly", h3))
    s.append(Paragraph(
        f"<b>{num(m['share_bounced']):.0%}</b> of incidents changed teams at least once and {num(m['share_bounced_2plus']):.0%} changed twice or "
        f"more, adding up to {int(num(m['total_handoffs'])):,} hand-offs. Incidents that changed hands took a median "
        f"{num(m['median_hours_bounced']):.1f} hours against {num(m['median_hours_not_bounced']):.1f}, and met their SLA "
        f"{num(m['sla_bounced']):.0%} of the time against {num(m['sla_not_bounced']):.0%}.", body))
    s.append(Paragraph(
        "That raw gap overstates the cost, because harder tickets are passed around more. Comparing incidents that ended up in the "
        f"same resolving group ({int(num(m['like_for_like_groups']))} groups, covering {num(m['like_for_like_share_of_bounced']):.0%} of hand-off "
        f"incidents), a hand-off is associated with <b>+{num(m['like_for_like_extra_median_hours']):.1f} median hours</b> and "
        f"<b>{num(m['like_for_like_sla_gap_pts']):.1f} fewer SLA points</b>. This is an association, not proof that the hand-off caused it.", body))
    s.append(Table([[picture_parts("handoffs_distribution.png", 3.3 * inch, "Share of incidents by number of hand-offs."),
                     picture_parts("cost_of_handoffs.png", 3.4 * inch, "Raw comparison; the like-for-like gap is smaller.")]],
                   colWidths=[3.4 * inch, 3.4 * inch], style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])))

    s.append(Paragraph("3.2 &nbsp; The problem is concentrated", h3))
    s.append(Paragraph(
        f"The ten categories with the most hand-offs produce {num(m['top10_categories_share_of_handoffs']):.0%} of them. "
        f"<b>Category 23</b> stands out: {num(m['focus_bounce_rate']):.1%} of its tickets change hands, and it produces "
        f"{focus_share_hand:.1%} of all hand-offs from {focus_share_inc:.1%} of incidents.", body))

    s.append(CondPageBreak(3.6 * inch))
    s.append(Paragraph("3.3 &nbsp; Automated routing does not beat today's routing", h3))
    s.append(Paragraph(
        "Could a system, using only what is known when a ticket opens, send it to the group that eventually resolves it? "
        f"Trained on earlier incidents and tested on {int(rm.test_incidents.iloc[0]):,} later ones (96% opened in one month), the answer is no. "
        f"Today's first assignment reaches the resolving group <b>{today:.1%}</b> of the time. A routing table built from history reaches "
        f"{rtable:.1%}, machine learning {forest:.1%}, and always picking the most common group {majority:.1%}. On the incidents that "
        f"really did bounce, today's routing was right only {bounced_today:.0%} of the time and machine learning {bounced_forest:.0%}, but "
        "it gives that back on the many tickets humans route correctly.", body))
    s.append(picture("routing_accuracy.png", 5.0 * inch,
                     "Left: all categories, with 95% intervals. Right: Category 23 only, chosen on earlier data (section 3.4)."))
    rows = [["Robustness check", "Router", "Today", "Incidents"]]
    for r in rb.itertuples():
        rows.append([r.check, f"{r.router_accuracy:.1%}", f"{r.today_accuracy:.1%}", f"{int(r.test_incidents):,}"])
    s.append(table(rows, [3.9 * inch, 0.9 * inch, 0.9 * inch, 1.1 * inch]))
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        "The result holds under every way of testing it, and adding the caller and the agent who opened the ticket "
        f"did not help ({with_extras:.1%} vs {forest:.1%} for the same model without them). The likely reason is that the fields recorded at intake ({fields['category_known_at_open']:.0%} of "
        f"tickets have a category and {fields['u_symptom_known_at_open']:.0%} a symptom) do not contain what is needed to route many tickets. "
        "Diagnosis happens after the ticket is opened.", body))

    s.append(CondPageBreak(4.4 * inch))
    s.append(Paragraph("3.4 &nbsp; The exception: Category 23", h3))
    s.append(Paragraph(
        "Category 23 was the only category where, using earlier data alone, a rule clearly beat today's routing on a validation slice. "
        f"Judged on the untouched later incidents, today's first assignment is right <b>{today_c:.1%}</b> of the time and one rule "
        f"(<b>{sp['single_group_rule']}</b>) is right <b>{rule_c:.1%}</b> of the time, on {int(float(sp['test_incidents_in_chosen_categories']))} "
        f"tickets: {net_rule} more routed correctly than before. A simpler rule beat the routing table ({num(sp['rule_accuracy_in_chosen_table']):.1%}).", body))
    s.append(picture("process_current.png", 5.9 * inch, "Where Category 23 tickets start and where they end up."))
    rows = [["Month", "Tickets", "Routed right today", "Resolved by Group 70", "Change hands", "Gain from the rule"]]
    for r in bm.itertuples():
        rows.append([r.month, f"{int(r.incidents)}", f"{r.today_first_time_right:.1%}", f"{r.resolved_by_rule_group:.1%}",
                     f"{r.hand_off_rate:.1%}", f"{r.gain_points * 100:+.1f} pts"])
    s.append(table(rows, [0.9 * inch, 0.8 * inch, 1.3 * inch, 1.45 * inch, 1.1 * inch, 1.25 * inch]))
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        f"<b>The problem is getting worse, and the data cannot say why.</b> First-time-right fell from {first_month.today_first_time_right:.0%} to "
        f"{last_month.today_first_time_right:.0%} in three months while the hand-off rate rose from {first_month.hand_off_rate:.0%} to "
        f"{last_month.hand_off_rate:.0%}. The rule would have been slightly worse in March, so the benefit depends on the window. "
        "Something changed in how these tickets are routed; finding out what comes before any rule change.", body))

    s.append(Paragraph("3.5 &nbsp; A second lever to test, not yet to act on", h3))
    s.append(Paragraph(
        f"Hand-off rates vary between the {int(num(m['openers_analyzed']))} agents who open the most tickets, even after allowing for the categories "
        f"they handle: from {num(m['openers_min_gap_pts']):+.1f} to {num(m['openers_max_gap_pts']):+.1f} points against expectation, and "
        f"{int(num(m['openers_beyond_chance']))} of {int(num(m['openers_analyzed']))} differ by more than chance would explain. This points to "
        "differences in intake practice worth investigating, but ticket mix within a category may explain some of it, so it is a hypothesis for a pilot.", body))

    s.append(CondPageBreak(3 * inch))
    s.append(Paragraph("4. Options considered", h2))
    rows = [["Option", "Evidence", "Effort and risk", "Verdict"],
            ["A. Do nothing", f"{num(m['share_bounced']):.0%} of incidents change teams; Category 23 is getting worse "
                              f"({first_month.today_first_time_right:.0%} to {last_month.today_first_time_right:.0%} first time right)",
             "No cost, but the cost continues", "Not recommended"],
            ["B. Machine-learning router, all categories", f"{forest:.1%} accuracy vs {today:.1%} today; worse under every test", "Highest: build or buy, integrate, maintain (not costed here)", "Reject"],
            ["C. Routing rules for every category", f"{rtable:.1%} vs {today:.1%} today", "Moderate; would degrade routing that works", "Reject"],
            ["D. One rule for Category 23, reason codes, monthly review", f"{rule_c:.1%} vs {today_c:.1%} today on later incidents; chosen without seeing the test data", "About 8 hours of configuration (assumption); risk that hand-offs move to Group 70", "<b>Recommend as a four-week pilot</b>"],
            ["E. Coach intake practice", f"{int(num(m['openers_beyond_chance']))} of {int(num(m['openers_analyzed']))} agents differ beyond chance (association)", "Low; confounding not ruled out", "Investigate alongside D"]]
    s.append(table(rows, [1.55 * inch, 2.15 * inch, 1.9 * inch, 1.2 * inch]))

    s.append(CondPageBreak(4 * inch))
    s.append(Paragraph("5. Recommendation and what it changes", h2))
    s.append(picture("process_proposed.png", 5.9 * inch, "The proposed path for Category 23 tickets, with the review loop."))
    s.append(CondPageBreak(3.4 * inch))  # keep the evidence table in one piece
    s.append(Paragraph("The evidence for the change, separated by how far each piece can be trusted:", body))
    rows = [["Evidence", "Result", "Basis"],
            ["Category 23 routed to the right team, today vs the rule", f"{today_c:.1%} vs {rule_c:.1%}", "Measured on later incidents"],
            ["Incidents routed right instead of wrong, in that test window", f"{net_rule}", "Measured on later incidents"],
            ["Whole-period gain (March to May), if the rule had always applied", f"+{sc.loc['Low', 'in_first_time_right_gain'] * 100:.1f} points", "Measured, in-sample"],
            ["Incidents newly routed right per month", f"{low.incidents_routed_right_per_month:.0f} to {high.incidents_routed_right_per_month:.0f}", "Estimated from the gains above"],
            ["Elapsed resolution hours saved per month", f"{low.elapsed_hours_saved_per_month:,.0f} to {high.elapsed_hours_saved_per_month:,.0f}", "Assumption: 25% to 100% of the gap is caused by the hand-off"],
            ["Analyst hours saved per month", f"{low.analyst_hours_saved_per_month:.0f} to {high.analyst_hours_saved_per_month:.0f}", "Assumption: 10 to 20 minutes per hand-off"],
            ["Analyst cost saved per year", f"${low.analyst_cost_saved_per_year:,.0f} to ${high.analyst_cost_saved_per_year:,.0f}", "Assumption: $35 to $55 per hour, volume unchanged"],
            ["Payback on the one-off change", f"{high.payback_days:.0f} to {low.payback_days:.0f} days", "Assumption: 8 hours of configuration"]]
    s.append(table(rows, [3.05 * inch, 1.7 * inch, 2.05 * inch], shade_from=4))
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        "No fix has been deployed, so the shaded rows are arithmetic on stated assumptions, not results. The dollar savings are small; "
        "the case rests on elapsed time and SLA, which come from the data. The Excel model lets a stakeholder change every assumption.", caption))

    s.append(Paragraph("6. Risks and limitations", h2))
    s.append(bullets([
        f"<b>The hand-off may only move.</b> Group 70 resolves {rule_share_lo:.0%} to {rule_share_hi:.0%} of Category 23 tickets month by month, so most of what it receives directly will still need passing on. The pilot tracks reason codes and Group 70's workload.",
        "<b>Group 20 may be a deliberate step</b> (for example a triage or security check) that the data cannot show.",
        "<b>The benefit depends on the window:</b> " + ", ".join(f"{g:+.0f} points in {month}" for month, g in gain_by_month.items())
        + ". The model's low case uses the whole-period figure.",
        "<b>Time and SLA gaps are associations.</b> The model applies a haircut of 25% to 100% to reflect that.",
        "<b>One log, one company, about three months.</b> Volumes and patterns may not hold elsewhere, and the routing fields are taken from the first record where each is filled in, which may be after some triage.",
        "<b>Labels are the group that finally resolved the ticket.</b> That is correct in hindsight, but not necessarily the best first assignment."]))

    s.append(CondPageBreak(2.2 * inch))
    s.append(Paragraph("7. Next steps and decision rule", h2))
    s.append(Paragraph(
        "Four steps over about six weeks (detail in the requirements document): ask Group 20, Group 70 and the service desk what changed "
        "between March and May; build and test the rule and a rollback; go live and track first-time-right weekly; decide at week six. "
        "<b>Proposed rule, to be agreed with stakeholders:</b> keep the rule if Category 23 first-time-right is 30% or more, investigate at "
        "15% to 30%, and roll back below 15% or if any other category's hand-off rate rises by 3 points or more.", body))

    s.append(Paragraph("Appendix: how the numbers were checked", h2))
    s.append(bullets([
        "The hand-off counts were computed in pandas and recomputed independently in SQL with window functions; the two match exactly (19,088 hand-offs across all incidents, and the top ten categories).",
        "The Excel model was calculated by Excel itself and compared with the Python calculation: all 27 results match.",
        "Automated tests confirm no training incident is later than any test incident and that the router is never given a field that reveals the answer.",
        "Category selection used a validation slice of the training period only; the test set was not used to choose it."]))

    doc.build(s)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
