# Should We Automate Incident Routing?

**A business case built on 24,918 real IT incidents. The answer is not broadly: fix one rule, then test one more lever.**

Start with the [business case (PDF)](Business_Case_Incident_Routing.pdf), then the
[requirements document](docs/business_requirements.md) and the
[impact model (Excel)](Incident_Routing_Impact_Model.xlsx).

## The business problem

When an IT ticket is opened it is assigned to a support group. If that group cannot resolve it, the ticket
is passed on, sometimes several times. Each hand-off is a delay for the person waiting and work for the
analysts re-routing it. The decision: should the IT Service Desk invest in automating the routing, and if so where?

## The data

A real, anonymized ServiceNow log from an IT company: **24,918 incidents and 141,712 logged updates**
([UCI Machine Learning Repository](https://doi.org/10.24432/C57S4H), Amaral, Fantinato and Peres, 2018, CC BY 4.0).
98% of incidents were opened in three months (March to May 2016), about 8,100 a month, so figures are
reported per month and not scaled up to a year. Group, category and agent names are anonymized.

## What I found

- **Hand-offs are common and costly.** 41% of incidents change teams at least once. Comparing incidents that
  ended up in the same resolving group, a hand-off is associated with **+62.5 median hours** and **17.3 fewer
  SLA points**. (The raw gap is larger, but harder tickets get passed around more, so I don't use it.)
- **They are concentrated.** Ten categories produce 73% of hand-offs. **Category 23** changes hands 84.5% of
  the time, and produces 8.9% of all hand-offs from 4.6% of incidents.
- **Automated routing does not beat today's routing.** Trained on earlier incidents and tested on later ones,
  today's first assignment reaches the resolving group **66.3%** of the time, against 55.9% for a routing
  table and 61.3% for machine learning. This held under a random split, under retraining month by month, and
  with extra fields added. Funding an automation project would have made routing worse.
- **The exception is Category 23.** On later incidents, a single rule (**Category 23 goes to Group 70**) reaches
  the right team **42.4%** of the time, against **6.7%** today (330 tickets, 118 more routed correctly). The
  category was chosen using only earlier data.
- **It is getting worse, and the data can't say why.** Category 23's first-time-right rate fell from 35.7% in
  March to 18.1% in April to 6.7% in May.

## What it changes

**Recommendation:** do not fund an ML routing project. Approve a four-week pilot of one assignment rule for
Category 23 with reason codes on reassignment, after a root-cause check on what changed between March and May.

| Evidence | Result | Basis |
|---|---|---|
| Category 23 routed to the right team: today vs the rule | 6.7% vs 42.4% | Measured, on later incidents |
| Whole-period gain if the rule had always applied | +19.5 points | Measured, in-sample |
| Incidents newly routed right per month | 69 to 127 | Estimated from the gains |
| Elapsed resolution hours saved per month | 1,084 to 7,936 | **Assumption:** 25% to 100% of the time gap is caused by the hand-off |
| Analyst cost saved per year | $4,853 to $53,061 | **Assumption:** 10 to 20 minutes per hand-off, $35 to $55 per hour |
| Payback on the one-off change | 3 to 21 days | **Assumption:** 8 hours of configuration |

No fix has been deployed, so the last four rows are arithmetic on stated assumptions, not results. The dollar
savings are small; the case rests on elapsed time and SLA, which come from the data. The Excel model has live
formulas so every assumption can be changed.

## How I checked the numbers

- **Independent recomputation.** The hand-off counts come from pandas and were recomputed in SQL with window
  functions ([`sql/`](sql)); the two match exactly. `python tests/test_analysis.py` runs 13 checks, including that
  no training incident is later than any test incident, that the router never sees a field that reveals the answer,
  and that the Category 23 headline (42.4% vs 6.7%) is reproduced with plain loops.
- **Excel verified by Excel.** `tests/verify_excel_model.ps1` opens the workbook in Excel, lets it calculate every
  formula, and compares all 27 results with the Python calculation.
- **A result I did not expect.** My first hypothesis was that a model would beat human routing. I tested it, it
  didn't, and I checked that this wasn't an artifact of how I tested (three ways). Two figures in my early drafts were
  also wrong and were corrected: a yearly volume scaled up from a date span (most tickets were opened in
  three months), and a "later" test set that turned out to be 96% one month.

## What's in here

```
Business_Case_Incident_Routing.pdf      the decision document (6 pages)
Incident_Routing_Impact_Model.xlsx      impact model with live formulas
docs/
  business_requirements.md              requirements, stakeholders, risks, rollout, success measures
  assets/                               charts and process diagrams
sql/
  01_handoffs.sql                       hand-offs per incident (LAG window function)
  02_handoffs_by_category.sql           where hand-offs concentrate
scripts/
  01_build_incident_table.py            one row per incident from the raw event log
  02_current_state.py                   cost of hand-offs, like-for-like comparison, concentration
  03_routing_poc.py                     router vs today, robustness checks, the Category 23 test
  04_impact_model.py                    scenario model and the Excel workbook
  05_build_diagrams.py                  current-state and proposed-state process diagrams
  06_build_business_case_pdf.py         the PDF
tests/
  test_analysis.py                      SQL cross-check, data checks, leakage checks
  verify_excel_model.ps1                Excel calculates the model; compared with Python
data/raw/incident_log.zip               the source data
data/processed/                         metrics and scenario tables (generated)
```

## How to reproduce

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python scripts\01_build_incident_table.py
.venv\Scripts\python scripts\02_current_state.py
.venv\Scripts\python scripts\03_routing_poc.py
.venv\Scripts\python scripts\04_impact_model.py
.venv\Scripts\python scripts\05_build_diagrams.py
.venv\Scripts\python scripts\06_build_business_case_pdf.py
.venv\Scripts\python tests\test_analysis.py
```

## Limitations

- One log, one company, about three months. Patterns may not hold elsewhere.
- Time and SLA gaps are associations, not proof that hand-offs cause them.
- The labels are the group that finally resolved each ticket: right in hindsight, but not necessarily the best
  first assignment. Routing fields are taken from the first record where they are filled in, which may be after some triage.
- The benefit of the Category 23 rule depends on the window (slightly negative in March, +24 points in April, +36 in May).
- Group 70 resolves only 33% to 43% of Category 23 tickets, depending on the month, so the hand-off may partly move rather than disappear.
- Nothing here has been piloted. The agent-level variation (13 of 21 agents differ beyond chance) is a hypothesis, not a finding to act on.

## Stack

Python (pandas, scikit-learn) · SQL (SQLite window functions) · Excel (live formulas, verified by Excel) · matplotlib and reportlab for the diagrams and PDF
