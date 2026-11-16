# Model Change Request: PD Recalibration
*Prepared by Cristina Orozco, Quantitative Credit Risk Modeler (Optimum Quants LLC). Illustrative case: fictional Category III bank, **synthetic data**. Not a real bank, portfolio or regulatory submission.*

| | |
|---|---|
| Requestor | Quantitative Credit Risk Modeler |
| Model | Lifetime PD (CECL), consumer portfolio |
| Change | Recalibration of 16 pool PDs on development + monitoring evidence |
| Linked item | HELOC LGD review (opened, not part of this change) |

**1. Reason.** Monitoring: mean pool A/E 1.25, macro inputs red, rank ordering intact (AUC 0.704).

**2. Scope.** In: PD, all 16 pools. Out: LGD, EAD, segmentation, default definition, technique. LGD and EAD kept at production values.

**3. Classification.** Scope: minor. Magnitude: +4.64% EL (threshold 10%, internal [JUDGMENT]). Combined with the linked HELOC LGD item: +7.4% (pooled evidence) to +12.2% (monitoring regime persists), straddling the threshold. Recommended governance classification: **borderline, assessed jointly; potentially material until the LGD review concludes**. No supervisory pre-notification applies to a Category III bank under the advanced-approaches provisions; internal governance applies.

**4. Impact.** EL $19,813,798 → $20,733,968 ($920,170). Capital: standardized risk weights do not depend on this model; the effect on regulatory capital runs through the allowance. *Capital Management to quantify.* Downstream consumers of PD (allowance, reporting extracts, stress-testing inputs) to be listed and updated by their owners.

**5. Validation performed.** 20% stratified holdout (AUC 0.717, A/E 1.001); bootstrap of the change and of the level; method sensitivity; reproduction of production PDs on development data. Limits: out-of-sample, not out-of-time.

**6. Approvals requested.** (a) Model owner; (b) Model Risk Management / independent validation; (c) Allowance committee (CECL); (d) Compliance (fair-lending items).

**7. Implementation.** Replace the PD table with `pd_curves_by_pool_recalibrated.csv` effective with the next allowance cycle after approval. **Rollback:** restore the production table (`data/production_model/pd_curves_by_pool.csv`); no schema change.

**8. Conditions.** Monthly monitoring until next quarterly cycle; HELOC LGD review; forecast and reversion documented by the allowance process; independent validation before the next cycle.
