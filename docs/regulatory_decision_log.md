# Regulatory and accounting decision log

Every modelling or governance decision that depends on a rule, an accounting standard, supervisory guidance or an internal judgement is recorded here with its basis. Labels:

* **[RULE]** binding regulation or statute · **[ACCOUNTING]** U.S. GAAP · **[GUIDANCE]** supervisory guidance (non-binding) · **[JUDGMENT]** the bank's own choice, no rule prescribes it · **[HISTORICAL]** superseded, not used as current.

"Library item" refers to the numbered source documents the analysis was checked against. Status was checked on **2026-11-08**. This log is an analyst's working record for a fictional bank, not legal advice.

## A. Who is this bank, and what does that switch on or off?

| # | Decision | Basis | Label | Consequence for this project |
|---|---|---|---|---|
| A1 | The bank is **Category III**. | 2019 tailoring rules: Category III = at least $250 billion in total assets, or at least $100 billion with at least $75 billion in weighted short-term wholesale funding, nonbank assets or off-balance-sheet exposure, and not Category I/II. Library items 13a, 13b. | [RULE] | Sets which capital and reporting regimes apply (below). |
| A2 | Risk-weighted assets use the **standardized approach**. | Advanced approaches are required for Category I and II only. | [RULE] | Risk weights are prescribed. The PD model drives the **allowance (CECL)**, not RWA. Effect on regulatory capital runs through the allowance; Capital Management to quantify. |
| A3 | **No pre-notification** of this model change to supervisors under the advanced-approaches provisions. | 12 CFR 3.123(a) (OCC) / 217.123(a) (Fed) and the interagency guidance BCC 14-2 / GAA 2014-2 address advanced-approaches banks. Library items 12, 18, 19, 21, 22. | [RULE] / [GUIDANCE] | Change is governed **internally**. **Open point:** the library marks BCC 14-2 / GAA 2014-2 as "current per user, not verified as unrescinded". It does not matter here because the guidance does not apply to Category III, but it is not cited as current. |

## B. Accounting basis (CECL)

| # | Decision | Basis | Label | Consequence |
|---|---|---|---|---|
| B1 | Loans are **pooled by shared risk characteristics**: product × FICO band = 16 pools. | ASC 326-20-30-2 (pooling) and 55-5 (examples of characteristics). Library item 1. | [ACCOUNTING] | Pool design is not changed by the Model Update. |
| B2 | A lifetime PD is built over the **contractual term** (36, 60 and 120 months by product). | ASC 326-20 (contractual term, adjusted for expected prepayments where applied). | [ACCOUNTING] | Long terms mean most of the lifetime PD for HELOC and auto is extrapolated from a tail hazard (see C3). |
| B3 | The recalibration **does not replace the reasonable and supportable forecast or reversion**. It gives a better base; the forecast stays with the allowance process. | ASC 326-20-30-9. Library item 1. | [ACCOUNTING] | The report presents the range between the pooled estimate (+4.6%) and a full-persistence scalar (+25%) and hands the judgement to the allowance committee instead of choosing for it. The red macro PSI is the evidence they need. |
| B4 | **HELOC and credit card are revolving**: they carry a credit limit, utilization and a realized CCF. Unconditionally cancellable undrawn amounts are treated per the standard. | ASC 326-20-30-11 (off-balance-sheet credit exposures). Library items 1, 7. | [ACCOUNTING] | Utilization is "not applicable" for term loans, not zero. HELOC is not modelled as an amortizing loan. |
| B5 | Model change is documented and independently reviewed as part of the allowance process. | Interagency Policy Statement on Allowances for Credit Losses (rev. 2023). Library item 7. | [GUIDANCE] | Change request lists approvals including independent validation before the next allowance cycle. |

## C. Model-risk governance

| # | Decision | Basis | Label | Consequence |
|---|---|---|---|---|
| C1 | Model risk is managed under **SR 26-2** (April 17, 2026), which superseded SR 11-7; the OCC rescinded OCC 2011-12 by OCC Bulletin 2026-13. SR 11-7 and OCC 2011-12 appear in the library only as **[HISTORICAL]** and are not cited as current. | Library items 9, 10, 11. | [GUIDANCE] | Non-binding. The bank applies it through its own policy; documentation, validation and monitoring are scaled to the change. |
| C2 | **Materiality threshold for a Model Update = 10% change in Expected Loss.** 9% to 11% is "borderline" and triggers a sensitivity. | The bank's own policy. | [JUDGMENT] | No rule sets 10%. The project tests the decision against it three ways (point estimate, bootstrap, combined scope). |
| C3 | **Tail hazard:** pooled hazard of the last buckets until 300 loans of exposure. | Credibility rule of the production model. | [JUDGMENT] | Sensitivity shown: 150 → +0.4%, 600 → +4.0% (vs +4.6% at 300). |
| C4 | **Monotonicity:** a better FICO band never has a higher PD; isotonic regression within segment, weighted by pool size. | Economic reasonableness of the pooling. | [JUDGMENT] | Applied to HELOC prime/super-prime (estimates were reversed). Without it: +4.5%. |
| C5 | **Scope = PD only.** LGD and EAD unchanged. | The monitoring finding was about default rates. | [JUDGMENT] | **Revisited after a scope test:** HELOC realized LGD rose from 0.30 to 0.36. PD-only: +4.6%; with HELOC LGD: +7.4% (pooled evidence) to +12.2% (monitoring regime persists). See C6. |
| C6 | **Do not split the change to stay below the threshold.** Assess the PD and LGD items **together**. The combined range (+7.4% to +12.2%) straddles 10%, so apply the borderline rule and treat the package as potentially material until the linked HELOC LGD review concludes. | Intent of a materiality policy. | [JUDGMENT] | Recommendation to the governance committee, who decide. |
| C7 | **Validation = out-of-sample holdout** (20%, stratified by pool, split before fitting, seed 7), with raw rate vs raw rate over comparable windows. | Recalibrating on all evidence leaves no independent period. | [JUDGMENT] | It is **not out-of-time**; that is why monitoring becomes monthly until the next quarterly cycle. |
| C8 | **Thresholds in the monitoring plan** (PSI 0.10/0.25; AUC 0.65/0.60; Gini/KS drop 10%/20%; AIR 0.90/0.80; A/E 1.10/1.35). | Industry convention for PSI; the rest are the bank's own. | [JUDGMENT] | All labelled internal in every document. |
| C9 | **Read A/E with its interval.** Two of sixteen pools are significant after Bonferroni; a chi-square test cannot reject a single common shift (p = 0.52). | Statistical caution. | [JUDGMENT] | The update pools evidence instead of fitting per-pool adjustments (which gives +20% and overfits). |

## D. Fair lending

| # | Decision | Basis | Label | Consequence |
|---|---|---|---|---|
| D1 | **No protected-class variable and no `state`/`zip_code` in the model.** | Fair-lending exam procedures (library item 16) on proxy risk; 12 CFR Part 1002. | [GUIDANCE] / [RULE] | Geography is a review variable, not an input. |
| D2 | Since the CFPB final rule of **April 22, 2026** (FR Doc 2026-07804, 91 FR 21620; **effective July 21, 2026**), Regulation B states that ECOA does **not** provide a disparate-impact (effects) test (12 CFR 1002.6(a)). **Proxy-based disparate treatment** remains prohibited (comment 6(a)-2). Library items 17, 30. | | [RULE] | Adverse Impact Ratio is kept as an **internal governance indicator**, not as a legal test. A result below 0.80 is a trigger for review, not a finding of violation. |
| D3 | For **HELOC**, the **Fair Housing Act** continues to be read to cover disparate impact. | FHA §805; *Texas Dept. of Housing v. Inclusive Communities* (2015). Library items 28, 29. **Verify no later overruling.** | [RULE] | HELOC fair-lending review stays in scope regardless of D2. |
| D4 | The proxy used for AIR is **synthetic** (BISG-style). In practice compliance builds it and it never enters the model. | | [JUDGMENT] | Results demonstrate the test, not a real finding. |
| D5 | Credit-card AIR of 0.73 (red) with one portfolio-wide cut-off is an **artifact of the cut-off rule** (only 36% of cards fall under the median PD); with product-level cut-offs it is 0.85 (amber). Not escalated as a finding; Compliance is asked for a real proxy and the downstream use of the PDs. | Internal judgement on test design. | [JUDGMENT] | Product-level AIR uses product-level cut-offs. |

## E. Downstream consumers

| # | Decision | Basis | Label | Consequence |
|---|---|---|---|---|
| E1 | Owners of downstream uses of PD (allowance, regulatory extracts, stress-testing inputs) must be told and must update. | If the bank files FR Y-14M, the instructions are library item 25. | [RULE] | The change request lists the consumers to be confirmed; this project does not assess them. |

## F. What was checked and what was not

* Checked against the library on 2026-11-08: the rule dates and labels above, and the status of SR 26-2, SR 11-7, OCC 2011-12 and the Regulation B rule.
* **Not verified:** whether BCC 14-2 / GAA 2014-2 has been rescinded (not blocking, see A3); later overruling of *Inclusive Communities* (see D3).
* Paragraph-level ASC references are cited from the standard as held in the library; confirm against the Codification before using them externally.
