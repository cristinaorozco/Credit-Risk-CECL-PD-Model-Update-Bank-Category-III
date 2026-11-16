# Executive Summary: PD Model Update, Consumer Portfolio
*Prepared by Cristina Orozco, Quantitative Credit Risk Modeler (Optimum Quants LLC). Illustrative case: fictional Category III bank, **synthetic data**. Not a real bank, portfolio or regulatory submission.*

## Decision requested
Approve the **recalibration of the lifetime PD model** (16 pools, four products) and acknowledge a **linked review of HELOC LGD** that this work uncovered.

## Why now
Twelve months after go-live, monitoring shows defaults above expectation: the observed default rate rose from 7.32% to 9.13%, the average pool actual-to-expected ratio is **1.25**, and regional unemployment and house-price inputs are in the red band. The model still **ranks** borrowers correctly (AUC 0.704 against 0.704 at development) but its **levels** are too low. That is a recalibration problem, not a redevelopment problem.

## What was done
The production method was kept unchanged (same pools, hazard buckets, tail rule and monotonicity) and re-estimated on development plus monitoring evidence (30,000 loans). Twenty percent of the data was held out before fitting to validate.

## Results
| | |
|---|---|
| Expected Loss, production model | $19,813,798 (4.60% of $430,631,113 funded) |
| Expected Loss, recalibrated | $20,733,968 (4.81%) |
| Change | **$920,170 (+4.64%)**, below the 10% internal threshold |
| Is the change real? | Yes. Paired bootstrap 95% interval 1.7% to 8.9% |
| Holdout validation | AUC 0.717, Gini 0.433, KS 0.362, aggregate A/E 1.001 |

## Three things the committee should know
1. **HELOC LGD moved.** Realized LGD rose from 0.30 to 0.36 (p < 0.001) while the other products did not. PD recalibration alone is +4.6%; adding HELOC LGD gives **+7.4% if the LGD evidence is pooled like the PD, and +12.2% if the monitoring-period LGD persists**. That range straddles the 10% threshold. The change should not be split to stay under the line, so the package is assessed jointly and treated as borderline until the LGD review says which end applies.
2. **The EL level is uncertain even though the change is not.** An unpaired bootstrap gives -8% to 19% for the new EL, driven by long-dated products (HELOC, auto) whose lifetime PD is extrapolated beyond 35 observed months.
3. **The recalibration does not settle the forecast question.** A pure scalar (all PDs × 1.25) gives +25%; the pooled method gives +4.6%. Where between them the allowance should sit depends on whether the current environment persists, which is the reasonable-and-supportable forecast judgement (ASC 326-20) owned by the allowance process, not by this model.

## Conditions attached to approval
Monthly (not quarterly) monitoring until the next quarterly cycle; HELOC LGD review opened and linked; a real fair-lending proxy requested from Compliance (the synthetic-proxy AIR is amber, 0.81; the product-level red for credit card, 0.73, is an artifact of one portfolio-wide cut-off and is 0.85 with product-level cut-offs); independent validation of the recalibration before the next allowance cycle.

Full detail: *Model Update Report*. Requested approvals: *Model Change Request*.
