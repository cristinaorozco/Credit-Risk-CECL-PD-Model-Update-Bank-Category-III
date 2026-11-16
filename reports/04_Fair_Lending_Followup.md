# Fair Lending Follow-up
*Prepared by Cristina Orozco, Quantitative Credit Risk Modeler (Optimum Quants LLC). Illustrative case: fictional Category III bank, **synthetic data**. Not a real bank, portfolio or regulatory submission.*

**Purpose.** Re-run the Adverse Impact Ratio (AIR) with the recalibrated PD and decide what follows.

**Method.** Synthetic BISG-style proxy, kept apart from the model and never an input; approval = lifetime PD at or below the portfolio median; AIR = approval rate (protected proxy) ÷ approval rate (reference). Internal scale [JUDGMENT]: ≥ 0.90 green, 0.80 to 0.90 amber, < 0.80 red.

| Scope         |   AIR production |   AIR recalibrated | Band (prod.)   | Band (recal.)   |   AIR prod., product cut-off |   AIR recal., product cut-off |
|:--------------|-----------------:|-------------------:|:---------------|:----------------|-----------------------------:|------------------------------:|
| all           |           0.8138 |             0.8138 | AMBER          | AMBER           |                       0.8387 |                        0.8387 |
| auto_loan     |           0.8360 |             0.8360 | AMBER          | AMBER           |                       0.8360 |                        0.8360 |
| personal_loan |           0.8376 |             0.8376 | AMBER          | AMBER           |                       0.8376 |                        0.8376 |
| credit_card   |           0.7342 |             0.7342 | RED            | RED             |                       0.8479 |                        0.8479 |
| heloc         |           0.8284 |             0.8284 | AMBER          | AMBER           |                       0.8284 |                        0.8284 |

**Findings.**
1. The recalibration does **not** change AIR at this precision. It shifts PD levels, not the order of loans around the approval cut.
2. All scopes are amber (or red for card, see 3) **before and after**. The proxy is built to sit lower on FICO, so a gap is expected by construction; it is not an effect of the update.
3. The **credit-card red (0.73) is an artifact of the single portfolio-wide cut-off** (only 36% of cards fall under it). With product-level cut-offs the card AIR is 0.85, in line with the others. It is not escalated as a finding.

**Regulatory framing (as of the date of this memo).**
* The CFPB's final rule of April 22, 2026 (91 FR 21620; effective July 21, 2026) states that ECOA does not provide a disparate-impact (effects) test (12 CFR 1002.6(a)). Proxy-based **disparate treatment** is still prohibited (comment 6(a)-2).
* The Fair Housing Act continues to be read to cover disparate impact (*Texas Dept. of Housing v. Inclusive Communities*, 2015), which is relevant to HELOC.
* So AIR is a governance indicator and an early-warning signal. It is not the legal test, and a result below 0.80 is not by itself a finding of violation.

**Limits.** The proxy is synthetic and the approval rule is a simplification. A real review would use compliance-built proxies, actual decision data and less-discriminatory-alternative analysis.

**Requested actions.** Compliance to supply a real proxy and confirm how the PDs are used downstream; keep `state` and `zip_code` out of the model; continue quarterly AIR.
