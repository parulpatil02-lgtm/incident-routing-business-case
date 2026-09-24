# Business Requirements: Category 23 Routing Fix and Pilot

**Status:** proposed, for approval by the IT Service Desk Manager
**Companion documents:** [Business case (PDF)](../Business_Case_Incident_Routing.pdf), [impact model (Excel)](../Incident_Routing_Impact_Model.xlsx)

> The incident data is anonymized (Group 20, Category 23, and so on). The roles below are
> the ones a real deployment of this change would involve; they are not people named in the data.

## 1. Purpose and scope

Reduce how often Category 23 incidents change hands between teams, by changing the rule that assigns them
on creation, and by measuring the result for a four-week pilot.

**In scope**
- One assignment rule change for Category 23 tickets.
- A required reason code whenever a Category 23 ticket is reassigned.
- A weekly report of hand-off and resolution metrics.
- A short root-cause check before go-live.

**Out of scope**
- Machine-learning routing for all categories (the business case shows it does not beat today's routing).
- Changes to other categories (see FR-6 for the evidence needed first).
- Changes to team structure or staffing.

## 2. Background

Over March to May 2016, 41% of incidents changed teams at least once. Comparing like with like, each
hand-off adds a median 62.5 hours to resolution and costs 17 points of SLA attainment.

Category 23 is the clearest case: 84.5% of its tickets change hands (versus 41% overall), it produces
8.9% of all hand-offs from 4.6% of incidents, and 89% of its tickets are first assigned to Group 20, which
resolves only 13% of them. Group 70 resolves 35%. Its first-time-right rate fell from 36% in March to 7%
in May, and the data cannot say why.

## 3. Stakeholders

| Role | Interest | Involvement |
|---|---|---|
| IT Service Desk Manager | Owns hand-off and SLA performance | **Decision maker**; approves the pilot and the go/no-go |
| Group 20 lead | Currently receives all Category 23 tickets first | **Consulted** on why they are assigned there; agrees the change |
| Group 70 lead | Would receive Category 23 tickets directly | **Consulted**; confirms capacity; owns reason-code follow-up |
| Group 72 lead | Resolves 13% of Category 23 tickets | **Informed**; consulted on reason codes |
| ServiceNow administrator | Implements and can roll back the rule | **Responsible** for the configuration |
| Service desk agents | Open and assign tickets | **Informed**; briefed on the change |
| Reporting analyst | Produces the weekly metrics | **Responsible** for the report |
| End users | Wait for resolution | **Affected**; no direct involvement |

## 4. Business requirements

| ID | Requirement | Evidence it matters |
|---|---|---|
| BR-1 | Reduce hand-offs for Category 23 tickets | 84.5% change hands today; 96.1% in May |
| BR-2 | Improve SLA attainment for Category 23 tickets | Hand-offs are associated with 17 fewer SLA points, like-for-like |
| BR-3 | Understand why first-time-right fell between March and May before relying on a rule | 35.7% to 6.7% in three months, cause unknown |
| BR-4 | Do not make other categories worse | The rule touches Category 23 only |

## 5. Functional requirements (MoSCoW)

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| FR-1 | Must | New Category 23 tickets are assigned to Group 70 on creation | 100% of new Category 23 tickets show Group 70 as the first assignment |
| FR-2 | Must | The rule can be switched off | An administrator can disable it within one working day; tested before go-live |
| FR-3 | Must | Reassigning a Category 23 ticket requires a reason code from an agreed list | No Category 23 ticket can be reassigned without a code |
| FR-4 | Should | Weekly report by category: first-time-right, hand-off rate, median resolution hours, SLA attainment | Report available every Monday for the pilot period |
| FR-5 | Should | Monthly review of reason codes by the Service Desk Manager and group leads | A dated list of follow-up actions per meeting |
| FR-6 | Could | Extend the approach to another category | Only if the same test used here (rule chosen on earlier data, judged on later data) shows a clear gain |
| FR-7 | Won't | Machine-learning routing across all categories | Evidence does not support it (business case, section 3.3) |

## 6. Non-functional requirements

- **No added delay** when a ticket is created.
- **Auditability:** every rule change is logged with who made it and when.
- **Reversibility:** see FR-2.
- **Data protection:** reports use ticket attributes only, no caller names.

## 7. Success measures

Baselines are measured from the data. **The thresholds are proposals to be agreed with stakeholders.**

| Measure | Baseline (from data) | Expected from testing | Proposed decision rule at four weeks |
|---|---|---|---|
| Category 23 first-time-right | 6.7% in May (about 20% over Mar to May) | 33% to 43% | **Keep** at 30% or more; **investigate** at 15% to 30%; **roll back** below 15% |
| Category 23 hand-off rate | 84.5% (96.1% in May) | Falls as first-time-right rises | Reported weekly |
| Median resolution hours, Category 23 | Reported weekly from go-live | Not forecast | Reported; no threshold set |
| Other categories' hand-off rate | 41% overall | Unchanged | Any rise of 3 points or more triggers a review |

## 8. Assumptions, dependencies and risks

| Risk or assumption | Effect | Mitigation |
|---|---|---|
| **Group 70 receives tickets it does not resolve** (57% to 65% of Category 23 tickets are resolved elsewhere) | The hand-off may just move, and Group 70's workload rises | Reason codes (FR-3); Group 70 lead confirms capacity; four-week pilot with a rollback threshold |
| **Group 20 may be a deliberate triage step** (for example a security check) that the data cannot show | The rule could bypass a needed control | Root-cause conversation before go-live (BR-3) |
| The gain depends on the window measured: the rule would have been slightly worse in March, +24 points in April, +36 in May | The benefit may be smaller than the held-out figure | The impact model uses a low case (+19.5 points, whole period) |
| Time and SLA gaps are associations, not proof that hand-offs cause them | Benefits may be overstated | The model applies a haircut of 25% to 100% (an assumption) |
| Analyst minutes per hand-off and cost per hour are not in the data | Dollar savings are uncertain | Shown as ranges; the Excel model lets stakeholders change them |
| Volume stays near 355 Category 23 tickets a month | Annual figures change | Volume was steady across all three months (350, 359, 356) |

## 9. Rollout plan

| Week | Activity | Owner |
|---|---|---|
| 0 | Root-cause conversations with Group 20, Group 70 and the service desk; agree reason codes and thresholds | Service Desk Manager |
| 1 | Build and test the rule and the rollback in a non-production instance | ServiceNow administrator |
| 2 | Go live; brief agents | Administrator, Service Desk Manager |
| 3 to 5 | Weekly reports; watch Group 70 workload | Reporting analyst |
| 6 | Go, investigate or roll back against the decision rule; decide on FR-6 | Service Desk Manager |

## 10. Open questions

1. What changed between March and May that pushed first-time-right from 36% to 7%?
2. Is Group 20's first assignment a required step for this category?
3. What does Group 70's current capacity look like against roughly 355 extra first assignments a month?
4. Which reason codes are useful without being tedious to select?
