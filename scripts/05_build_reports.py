"""Step 5: write the deliverable reports from the result tables (numbers are never typed by hand)."""
import sys, subprocess; sys.path.insert(0, "src")
from mu_catiii import *

_dev, _mon = load_inputs()[:2]
T = lambda n: pd.read_csv(TABLES / n)
imp = T("03_el_impact_summary.csv").iloc[0]; mon_s = T("02_monitoring_summary.csv").iloc[0]
psi_t, disc, ae = T("02_psi.csv"), T("02_discrimination_monitoring.csv"), T("02_actual_vs_expected_by_pool.csv")
comp, seg, alts, bridge = T("03_pd_old_vs_new.csv"), T("03_el_impact_by_segment.csv"), T("03_alternatives_sensitivity.csv"), T("03_materiality_bridge.csv")
hold, cal = T("04_holdout_validation.csv").iloc[0], T("04_holdout_calibration_by_pool.csv")
lgd_c, ead_c, scen, air = T("04_scope_test_lgd.csv"), T("04_scope_test_ead.csv"), T("04_scope_scenario_heloc_lgd.csv"), pd.read_csv(TABLES / "04_adverse_impact_ratio.csv", index_col=0)
heloc_lgd = lgd_c.set_index("segment").loc["heloc"]
sc = scen.set_index("scenario")
S_PD, S_BOTH_POOL, S_BOTH_FULL = (sc.change_vs_production.iloc[i] for i in (0, 2, 4))
pct = lambda x, d=2: f"{x*100:.{d}f}%"
usd = lambda x: f"${x:,.0f}"
def md(df, floatfmt=".4f"): return df.to_markdown(index=False, floatfmt=floatfmt)
IMG = "../outputs/figures/"
HDR = "*Prepared by Cristina Orozco, Quantitative Credit Risk Modeler (Optimum Quants LLC). Illustrative case: fictional Category III bank, **synthetic data**. Not a real bank, portfolio or regulatory submission.*"

# ----------------------------------------------------------------- Executive summary
ex = f"""# Executive Summary: PD Model Update, Consumer Portfolio
{HDR}

## Decision requested
Approve the **recalibration of the lifetime PD model** (16 pools, four products) and acknowledge a **linked review of HELOC LGD** that this work uncovered.

## Why now
Twelve months after go-live, monitoring shows defaults above expectation: the observed default rate rose from {pct(_dev.default_flag.mean())} to {pct(_mon.default_flag.mean())}, the average pool actual-to-expected ratio is **{mon_s.AE_simple_mean_of_pools:.2f}**, and regional unemployment and house-price inputs are in the red band. The model still **ranks** borrowers correctly (AUC {disc.monitoring[0]:.3f} against {disc.development[0]:.3f} at development) but its **levels** are too low. That is a recalibration problem, not a redevelopment problem.

## What was done
The production method was kept unchanged (same pools, hazard buckets, tail rule and monotonicity) and re-estimated on development plus monitoring evidence (30,000 loans). Twenty percent of the data was held out before fitting to validate.

## Results
| | |
|---|---|
| Expected Loss, production model | {usd(imp.EL_old)} ({pct(imp.EL_old_pct_exposure)} of {usd(imp.exposure_funded)} funded) |
| Expected Loss, recalibrated | {usd(imp.EL_new)} ({pct(imp.EL_new_pct_exposure)}) |
| Change | **{usd(imp.delta_EL)} ({imp.EL_change_pct*100:+.2f}%)**, below the 10% internal threshold |
| Is the change real? | Yes. Paired bootstrap 95% interval {pct(imp.paired_low,1)} to {pct(imp.paired_high,1)} |
| Holdout validation | AUC {hold.AUC:.3f}, Gini {hold.Gini:.3f}, KS {hold.KS:.3f}, aggregate A/E {hold.AE_aggregate:.3f} |

## Three things the committee should know
1. **HELOC LGD moved.** Realized LGD rose from {heloc_lgd.LGD_realized_dev:.2f} to {heloc_lgd.LGD_realized_mon:.2f} (p < 0.001) while the other products did not. PD recalibration alone is {S_PD*100:+.1f}%; adding HELOC LGD gives **{S_BOTH_POOL*100:+.1f}% if the LGD evidence is pooled like the PD, and {S_BOTH_FULL*100:+.1f}% if the monitoring-period LGD persists**. That range straddles the 10% threshold. The change should not be split to stay under the line, so the package is assessed jointly and treated as borderline until the LGD review says which end applies.
2. **The EL level is uncertain even though the change is not.** An unpaired bootstrap gives {pct(imp.boot_low,0)} to {pct(imp.boot_high,0)} for the new EL, driven by long-dated products (HELOC, auto) whose lifetime PD is extrapolated beyond 35 observed months.
3. **The recalibration does not settle the forecast question.** A pure scalar (all PDs × {mon_s.AE_simple_mean_of_pools:.2f}) gives {alts.EL_change_pct.iloc[6]*100:+.0f}%; the pooled method gives {imp.EL_change_pct*100:+.1f}%. Where between them the allowance should sit depends on whether the current environment persists, which is the reasonable-and-supportable forecast judgement (ASC 326-20) owned by the allowance process, not by this model.

## Conditions attached to approval
Monthly (not quarterly) monitoring until the next quarterly cycle; HELOC LGD review opened and linked; a real fair-lending proxy requested from Compliance (the synthetic-proxy AIR is amber, {air.loc['all','AIR_production']:.2f}; the product-level red for credit card, {air.loc['credit_card','AIR_production']:.2f}, is an artifact of one portfolio-wide cut-off and is {air.loc['credit_card','AIR_production_within_product']:.2f} with product-level cut-offs); independent validation of the recalibration before the next allowance cycle.

Full detail: *Model Update Report*. Requested approvals: *Model Change Request*.
"""

# ----------------------------------------------------------------- Main report
tbl_pd = comp[["pool_id", "PD_old", "PD_new", "change_pct"]].rename(columns={"pool_id": "Pool", "PD_old": "PD v1", "PD_new": "PD v2", "change_pct": "Change"}); tbl_pd["Change"] = tbl_pd["Change"].map(lambda v: f"{v*100:+.1f}%")
ae_t = ae[["pool_id", "n_mon", "rate_dev", "rate_mon", "AE_ratio", "AE_ci_low", "AE_ci_high", "status"]].rename(columns={"pool_id": "Pool", "n_mon": "n (mon)", "rate_dev": "Dev rate", "rate_mon": "Mon rate", "AE_ratio": "A/E", "AE_ci_low": "CI low", "AE_ci_high": "CI high", "status": "Band"})
psi_md = psi_t.rename(columns={"metric": "Metric", "object": "Object", "value": "PSI", "status": "Band"})
disc_md = disc.rename(columns={"development": "Development", "monitoring": "Monitoring", "change_pct": "Change", "status": "Band"}); disc_md["Change"] = disc_md.Change.map(lambda v: f"{v*100:+.2f}%")
alts_md = alts.assign(**{"EL change": alts.EL_change_pct.map(lambda v: f"{v*100:+.2f}%"), "> 10%?": alts.above_10pct_threshold.map({True: "yes", False: "no"})})[["alternative", "EL change", "> 10%?"]].rename(columns={"alternative": "Alternative"})
seg_md = seg.reset_index()[["segment", "EL_old", "EL_new", "EL_change_pct"]].assign(EL_old=lambda d: d.EL_old.map(usd), EL_new=lambda d: d.EL_new.map(usd), EL_change_pct=lambda d: d.EL_change_pct.map(lambda v: f"{v*100:+.2f}%")).rename(columns={"segment": "Segment", "EL_old": "EL production", "EL_new": "EL recalibrated", "EL_change_pct": "Change"})
lgd_md = lgd_c.rename(columns={"segment": "Segment", "defaults_dev": "Defaults dev", "defaults_mon": "Defaults mon", "LGD_table_avg": "LGD in model", "LGD_realized_dev": "Realized dev", "LGD_realized_mon": "Realized mon", "diff_mon_minus_dev": "Diff", "p_value": "p-value"})
scen_md = scen.assign(EL=scen.EL.map(usd), change_vs_production=scen.change_vs_production.map(lambda v: f"{v*100:+.2f}%"), above_10pct_threshold=scen.above_10pct_threshold.map({True: "yes", False: "no"})).rename(columns={"scenario": "Scenario", "change_vs_production": "Change vs production", "above_10pct_threshold": "> 10%?"})
air_md = air.reset_index().rename(columns={"index": "Scope", "AIR_production": "AIR production", "AIR_recalibrated": "AIR recalibrated", "status_production": "Band (prod.)", "status_recalibrated": "Band (recal.)", "AIR_production_within_product": "AIR prod., product cut-off", "AIR_recalibrated_within_product": "AIR recal., product cut-off"})[["Scope", "AIR production", "AIR recalibrated", "Band (prod.)", "Band (recal.)", "AIR prod., product cut-off", "AIR recal., product cut-off"]]

rep = f"""# PD Model Update Report: Category III Bank, Consumer Portfolio
{HDR}

| | |
|---|---|
| Model | Lifetime PD (CECL), 16 pools = 4 products × 4 FICO bands |
| Change type | Recalibration (same methodology, new evidence) |
| Evidence | 30,000 loans: development (Jan 2022 to Jun 2023, 20,000) + monitoring (Jul 2023 to Jun 2024, 10,000) |
| Status | For model governance review |

## 1. Purpose and scope
This report documents the recalibration of the PD component of the bank's CECL model for its consumer portfolio (credit card, auto, personal loan, HELOC), the evidence behind the decision, the validation performed, and the limits of the result. **In scope:** PD. **Out of scope at kickoff:** LGD and EAD, because the monitoring finding concerned default rates. Section 8 tests that boundary and reports a finding that bears on it.

## 2. Background and regulatory context
The bank is treated as a **Category III** banking organization under the 2019 tailoring framework [RULE; library items 13a, 13b]. Consequences that shape this work (details and sources in `docs/regulatory_decision_log.md`):
* Category III banks use the **standardized approach** for risk-weighted assets; the advanced-approaches provisions (12 CFR 3.123 / 217.123) and the related interagency guidance on material changes (BCC 14-2 / GAA 2014-2) apply to advanced-approaches banks. They are **not triggered** here. The change is governed **internally** [JUDGMENT], not by a prior notice to supervisors.
* The model supports the allowance for credit losses under **CECL (ASC 326-20)**: pooling by shared risk characteristics (30-2, 55-5), reasonable and supportable forecasts, and reversion.
* Model risk is managed under the bank's policy, aligned with **SR 26-2** (April 17, 2026, non-binding supervisory guidance, which superseded SR 11-7) [GUIDANCE]. Proportionate documentation, validation and monitoring follow from that policy.
* Fair lending: see section 9.

## 3. Data
Raw extracts were audited before modelling (see `notebooks/01`). Issues found and treated (counts in development / monitoring): invalid FICO 999 ({T('01_raw_data_audit.csv').iloc[0].development} / {T('01_raw_data_audit.csv').iloc[0].monitoring}); negative DTI ({T('01_raw_data_audit.csv').iloc[1].development} / {T('01_raw_data_audit.csv').iloc[1].monitoring}); missing income, DTI, refreshed FICO and employment length; utilization not applicable for term loans (kept empty, not zero). Every treatment is flagged in the processed file. `state` and `zip_code` are not model inputs.

![Portfolio mix and default rate]({IMG}fig01_portfolio_mix_and_default_rate.png)

## 4. Monitoring findings
Internal thresholds, all [JUDGMENT]: PSI 0.10/0.25; AUC ≥ 0.65 green, 0.60 to 0.65 amber, < 0.60 red; Gini and KS relative drop 10%/20%; A/E 1.10/1.35.

**Stability.**
{md(psi_md)}

**Rank ordering.**
{md(disc_md)}

**Levels (actual versus expected).** Mean pool A/E {mon_s.AE_simple_mean_of_pools:.3f}; {int(mon_s.pools_above_1p10)} of 16 pools above 1.10, {int(mon_s.pools_above_1p35)} above 1.35. Raw rate ratios ignore that monitoring loans are younger (at most 29 months on book against 35). Comparing instead with the **model's own cumulative PD up to each loan's months on book** (horizon-matched A/E) gives a mean pool A/E of **{mon_s.AE_horizon_matched_simple_mean:.2f}** ({mon_s.AE_horizon_matched_portfolio:.2f} portfolio): the raw {mon_s.AE_simple_mean_of_pools:.2f} **understates** the deterioration. (A cruder truncation of development defaults at 29 months gives {mon_s.AE_dev_truncated_29m_simple_mean:.2f}; it still mixes loans of different ages and is not used.)

{md(ae_t, ".3f")}

![Actual vs expected]({IMG}fig04_actual_vs_expected_by_pool.png)

**Reading it honestly.** Only {int(mon_s.pools_significant_bonferroni)} pools are individually significant after Bonferroni correction, and a chi-square test does not reject a single common shift across all pools (χ² = {mon_s.heterogeneity_chi2:.1f}, {int(mon_s.heterogeneity_dof)} df, p = {mon_s.heterogeneity_p:.2f}). The spread of pool A/E (0.92 to 1.66) is consistent with sampling noise. This is why the update does not fit pool-specific adjustments.

**Diagnosis.** Ranking intact, levels low, macro inputs red: **recalibrate**. No evidence of a structural break in the pool mix (PSI of the pool distribution {psi_t.value[0]:.4f}).

## 5. Classification of the change
* **By scope:** minor. Pure recalibration: no change to the default definition, segmentation or technique [JUDGMENT].
* **By magnitude:** preliminary signal {bridge.value[0]*100:.1f}% (mean A/E − 1) would have exceeded the 10% internal threshold. The final, properly sized figure on Expected Loss is **{imp.EL_change_pct*100:+.2f}%**, below it. The preliminary figure overstated the impact because pooling the monitoring period with the stable history dilutes it (the simple mean of pool PD changes is {imp.PD_change_simple_mean*100:.2f}%; the EL-weighted change is {imp.EL_change_pct*100:.2f}%).
* **Combined with the HELOC LGD finding (section 8):** {S_BOTH_POOL*100:+.1f}% if HELOC LGD is re-estimated on pooled evidence (the same logic as the PD), {S_BOTH_FULL*100:+.1f}% if the monitoring-period LGD persists. The range straddles the threshold. **Recommendation:** assess the PD and LGD items **together** (the PD-only figure is under the threshold only because of where the scope boundary was drawn), apply the policy's borderline rule (sensitivity shown in section 8), and treat the package as potentially material for internal governance until the HELOC LGD review settles which reading applies. [JUDGMENT, for the governance committee to decide]

## 6. Method
Unchanged from production: 3-month life-table hazards by pool; a tail hazard from the pooled last buckets until at least {MIN_EXPOSURE_TAIL} loans of exposure [JUDGMENT]; isotonic regression across FICO bands within each segment so that a better band never carries a higher PD; EL = PD × LGD × EAD$ × loans with LGD and EAD unchanged. Only the evidence changes. Code: `src/mu_catiii.py`. Sanity check: re-estimating on development data alone reproduces the production PDs (EL change {alts.EL_change_pct.iloc[5]*100:.2f}%).

## 7. Results
**Expected Loss.** {usd(imp.EL_old)} ({pct(imp.EL_old_pct_exposure)}) → {usd(imp.EL_new)} ({pct(imp.EL_new_pct_exposure)}) of {usd(imp.exposure_funded)} funded; change {usd(imp.delta_EL)} (**{imp.EL_change_pct*100:+.2f}%**).

{md(seg_md)}

{md(tbl_pd, ".4f")}

![PD old vs new]({IMG}fig06_pd_old_vs_new.png)

HELOC prime and super-prime end at the same PD: the unconstrained estimates were reversed (prime below super-prime) and the monotonicity step pools them, as in production. HELOC subprime falls ({comp.set_index('pool_id').loc['heloc | subprime(<640)','change_pct']*100:+.1f}%), consistent with its A/E below 1.

**Out-of-sample validation.** 20% of the pooled loans (6,000), stratified by pool, were set aside before fitting. Holdout AUC {hold.AUC:.4f}, Gini {hold.Gini:.4f}, KS {hold.KS:.4f}; aggregate raw-rate A/E {hold.AE_aggregate:.4f} (sampling range {hold.AE_low:.2f} to {hold.AE_high:.2f}). *This is out-of-sample, not out-of-time*: it shows the fit is not memorising rows, not that the model will hold under conditions that have not occurred.

**Uncertainty.** Two bootstraps answer two questions.
* *Is the change real?* Paired bootstrap: 95% interval {pct(imp.paired_low,1)} to {pct(imp.paired_high,1)}; {imp.paired_share_above_10pct*100:.0f}% of resamples above 10%. Yes, and below the threshold.
* *How sure is the new level?* Unpaired bootstrap: 95% interval {pct(imp.boot_low,0)} to {pct(imp.boot_high,0)}; {imp.boot_share_above_10pct*100:.0f}% of resamples above 10% (largest contributors: HELOC and auto, where lifetime PD is mostly extrapolated).

![Materiality and bootstrap]({IMG}fig07_materiality_and_bootstrap.png)

**Method sensitivity.**
{md(alts_md)}

![Sensitivity]({IMG}fig08_method_sensitivity.png)

The pooled estimate and the scalar mark two ends of one question: does the monitoring-period environment persist? That is a forecast judgement, outside the model. The recalibrated PD is a better *base*; the allowance process still owns the forecast and reversion assumptions.

## 8. Scope check: LGD and EAD
Realized LGD (1 − recovery ÷ EAD on defaulted loans) and realized EAD measures were compared between periods.
{md(lgd_md)}

HELOC realized LGD rose by {heloc_lgd.diff_mon_minus_dev:.3f} (p {'< 0.0001' if heloc_lgd.p_value < 1e-4 else f'= {heloc_lgd.p_value:.4f}'}); the other products did not move. House-price growth fell from about +4.0% to +1.0% over the same window, the expected collateral channel. By vintage the move is a break at the 2023H2 originations. Caveat: monitoring loans have had less time to recover, which could bias LGD upward, but the same shorter window did not move the other three products. EAD measures show no change that survives correction for eight tests (personal-loan EAD ratio, p = {ead_c.set_index('segment').loc['personal_loan','p_value']:.3f}, is the closest).

{md(scen_md)}

The two readings bracket the same forecast question as for PD: do the monitoring conditions persist? Splitting a change to stay under a materiality line defeats the purpose of the line, so the recommendation in section 5 is to assess the package jointly. The PD update is delivered as scoped; a HELOC LGD review is opened as a **linked** item.

## 9. Fair lending
A synthetic BISG-style proxy (never a model input) was used to compute an Adverse Impact Ratio with approval defined as lifetime PD at or below the portfolio median. Internal scale [JUDGMENT]: ≥ 0.90 green, 0.80 to 0.90 amber, < 0.80 red.
{md(air_md)}

The recalibration leaves AIR unchanged at this precision (levels shift, the order of loans around the median does not). The product-level credit-card result ({air.loc['credit_card','AIR_production']:.2f}, red) is **a methodological artifact, not a finding**: with one portfolio-wide median cut-off only {air.loc['credit_card','share_below_portfolio_median']*100:.0f}% of cards fall under the cut-off (against about 65% for the other products), because cards carry higher PDs. With a cut-off set inside each product the card AIR is {air.loc['credit_card','AIR_production_within_product']:.2f}, in line with the other products. Regulatory framing: the CFPB final rule of April 22, 2026 (91 FR 21620, effective July 21, 2026) states that ECOA does not provide a disparate-impact (effects) test; proxy-based **disparate treatment** remains prohibited; for HELOC the Fair Housing Act is still read to cover disparate impact (*Inclusive Communities*, 2015). AIR is therefore used as an internal governance indicator, not as a legal test.

## 10. Limitations
See `docs/assumptions_and_limitations.md`. The ones that matter most: synthetic data and a synthetic proxy; one monitoring period (12 months, one regime); out-of-sample, not out-of-time validation; long-dated PDs rest on a tail extrapolation; LGD and EAD are held at development values; internal thresholds are judgement.

## 11. Conditions and recommendations
1. Approve the PD recalibration (v2 table in `outputs/pd_curves_by_pool_recalibrated.csv`).
2. Open a **HELOC LGD review**, linked to this change; assess the package jointly (range {S_BOTH_POOL*100:+.1f}% to {S_BOTH_FULL*100:+.1f}%, straddling the threshold).
3. **Monthly** monitoring until the next quarterly cycle: PSI (macro), A/E by pool, HELOC realized LGD.
4. Allowance process to document the forecast and reversion view in light of the macro PSI red and the range in section 7.
5. Ask Compliance for a real proxy and to confirm how the PDs are used downstream; the product-level AIR should use product-level cut-offs.
6. Independent validation of the recalibration before the next allowance cycle.
"""

# ----------------------------------------------------------------- Change request memo
mcr = f"""# Model Change Request: PD Recalibration
{HDR}

| | |
|---|---|
| Requestor | Quantitative Credit Risk Modeler |
| Model | Lifetime PD (CECL), consumer portfolio |
| Change | Recalibration of 16 pool PDs on development + monitoring evidence |
| Linked item | HELOC LGD review (opened, not part of this change) |

**1. Reason.** Monitoring: mean pool A/E {mon_s.AE_simple_mean_of_pools:.2f}, macro inputs red, rank ordering intact (AUC {disc.monitoring[0]:.3f}).

**2. Scope.** In: PD, all 16 pools. Out: LGD, EAD, segmentation, default definition, technique. LGD and EAD kept at production values.

**3. Classification.** Scope: minor. Magnitude: {imp.EL_change_pct*100:+.2f}% EL (threshold 10%, internal [JUDGMENT]). Combined with the linked HELOC LGD item: {S_BOTH_POOL*100:+.1f}% (pooled evidence) to {S_BOTH_FULL*100:+.1f}% (monitoring regime persists), straddling the threshold. Recommended governance classification: **borderline, assessed jointly; potentially material until the LGD review concludes**. No supervisory pre-notification applies to a Category III bank under the advanced-approaches provisions; internal governance applies.

**4. Impact.** EL {usd(imp.EL_old)} → {usd(imp.EL_new)} ({usd(imp.delta_EL)}). Capital: standardized risk weights do not depend on this model; the effect on regulatory capital runs through the allowance. *Capital Management to quantify.* Downstream consumers of PD (allowance, reporting extracts, stress-testing inputs) to be listed and updated by their owners.

**5. Validation performed.** 20% stratified holdout (AUC {hold.AUC:.3f}, A/E {hold.AE_aggregate:.3f}); bootstrap of the change and of the level; method sensitivity; reproduction of production PDs on development data. Limits: out-of-sample, not out-of-time.

**6. Approvals requested.** (a) Model owner; (b) Model Risk Management / independent validation; (c) Allowance committee (CECL); (d) Compliance (fair-lending items).

**7. Implementation.** Replace the PD table with `pd_curves_by_pool_recalibrated.csv` effective with the next allowance cycle after approval. **Rollback:** restore the production table (`data/production_model/pd_curves_by_pool.csv`); no schema change.

**8. Conditions.** Monthly monitoring until next quarterly cycle; HELOC LGD review; forecast and reversion documented by the allowance process; independent validation before the next cycle.
"""

# ----------------------------------------------------------------- Fair lending memo
fl = f"""# Fair Lending Follow-up
{HDR}

**Purpose.** Re-run the Adverse Impact Ratio (AIR) with the recalibrated PD and decide what follows.

**Method.** Synthetic BISG-style proxy, kept apart from the model and never an input; approval = lifetime PD at or below the portfolio median; AIR = approval rate (protected proxy) ÷ approval rate (reference). Internal scale [JUDGMENT]: ≥ 0.90 green, 0.80 to 0.90 amber, < 0.80 red.

{md(air_md)}

**Findings.**
1. The recalibration does **not** change AIR at this precision. It shifts PD levels, not the order of loans around the approval cut.
2. All scopes are amber (or red for card, see 3) **before and after**. The proxy is built to sit lower on FICO, so a gap is expected by construction; it is not an effect of the update.
3. The **credit-card red ({air.loc['credit_card','AIR_recalibrated']:.2f}) is an artifact of the single portfolio-wide cut-off** (only {air.loc['credit_card','share_below_portfolio_median']*100:.0f}% of cards fall under it). With product-level cut-offs the card AIR is {air.loc['credit_card','AIR_recalibrated_within_product']:.2f}, in line with the others. It is not escalated as a finding.

**Regulatory framing (as of the date of this memo).**
* The CFPB's final rule of April 22, 2026 (91 FR 21620; effective July 21, 2026) states that ECOA does not provide a disparate-impact (effects) test (12 CFR 1002.6(a)). Proxy-based **disparate treatment** is still prohibited (comment 6(a)-2).
* The Fair Housing Act continues to be read to cover disparate impact (*Texas Dept. of Housing v. Inclusive Communities*, 2015), which is relevant to HELOC.
* So AIR is a governance indicator and an early-warning signal. It is not the legal test, and a result below 0.80 is not by itself a finding of violation.

**Limits.** The proxy is synthetic and the approval rule is a simplification. A real review would use compliance-built proxies, actual decision data and less-discriminatory-alternative analysis.

**Requested actions.** Compliance to supply a real proxy and confirm how the PDs are used downstream; keep `state` and `zip_code` out of the model; continue quarterly AIR.
"""

# ----------------------------------------------------------------- Monitoring plan
plan = pd.DataFrame([
 ["PSI: pool distribution", "Portfolio", "< 0.10", "0.10 to 0.25", "> 0.25", "Quarterly", "Freeze for new originations; recalibrate"],
 ["PSI: FICO band within segment", "Each segment", "< 0.10", "0.10 to 0.25", "> 0.25", "Quarterly", "Review band definitions"],
 ["PSI: unemployment, HPI", "Macro inputs", "< 0.10", "0.10 to 0.25", "> 0.25", "**Monthly** (was quarterly)", "Allowance process to confirm forecast still reasonable and supportable"],
 ["Gini, KS (relative drop)", "Full model", "< 10%", "10% to 20%", "> 20%", "Quarterly", "Redevelop or recalibrate; classify Update vs New Methodology"],
 ["AUC-ROC (level)", "Full model", "≥ 0.65", "0.60 to 0.65", "< 0.60", "Quarterly", "Suspend automated use"],
 ["A/E default rate", "**Each of 16 pools + portfolio**", "≤ 1.10", "1.10 to 1.35", "> 1.35", "**Monthly** (was quarterly)", "Investigate; confirm significance before recalibrating pool-level"],
 ["**A/E horizon-matched, portfolio and each pool** (expected = production cumulative PD up to each loan's months on book; 95% interval; pools with < 20 defaults reported, not scored)", "Full model; 16 pools", "0.90 to 1.10", "1.10 to 1.25 (or 0.80 to 0.90)", "> 1.25 (or < 0.80)", "**Monthly** (was absent)", "Two consecutive reds: recalibration request"],
 ["**Heterogeneity of pool A/E** (Cochran Q or chi-square for one common shift)", "Full model", "p ≥ 0.10", "0.05 to 0.10", "< 0.05", "Quarterly (new)", "Structural review instead of a uniform recalibration"],
 ["**Realized CCF vs model**", "Card, HELOC", "within ±10 pp", "—", "≥ 10 pp", "Semi-annual (new)", "CCF review (needs pre-default drawn balances)"],
 ["Realized LGD (new)", "HELOC", "within ±0.03 of model", "±0.03 to ±0.06", "> ±0.06", "**Monthly**", "Complete linked LGD review"],
 ["Adverse Impact Ratio", "Proxy group; per segment", "≥ 0.90", "0.80 to 0.90", "< 0.80", "Quarterly", "Escalate to Compliance/Legal before continuing use"],
], columns=["Metric", "Object", "Green", "Amber", "Red", "Frequency", "Action if red"])
mp = f"""# Updated Monitoring Plan
{HDR}

All thresholds are internal [JUDGMENT]: no rule prescribes them. Changes against the previous plan are in **bold**. Reinforced (monthly) frequencies apply until the next quarterly cycle after approval; the reason is that the validation was out-of-sample, not out-of-time, so only elapsed time can confirm the recalibration.

{md(plan)}

**Rules of use.**
* Pool-level A/E is read with its confidence interval. In this case only {int(mon_s.pools_significant_bonferroni)} of 16 pools were individually significant; a single pool in red is not by itself a reason to recalibrate that pool.
* HELOC LGD bands are placeholders proposed by the modeler, to be set with the LGD review.
* Any red triggers the action in the last column and a note to the model owner within the period.
"""
OUT = ROOT / "reports"
for name, text in (("01_Executive_Summary", ex), ("02_Model_Update_Report", rep), ("03_Model_Change_Request", mcr), ("04_Fair_Lending_Followup", fl), ("05_Updated_Monitoring_Plan", mp)):
    (OUT / f"{name}.md").write_text(text)
    css = OUT / "report.css"
    subprocess.run(["pandoc", str(OUT / f"{name}.md"), "-f", "gfm", "-t", "html5", "-s", "--metadata", f"title={name.split('_',1)[1].replace('_',' ')}",
                    "-c", "report.css", "-o", str(OUT / f"{name}.html"), "--resource-path", str(OUT)], check=True)
    print("wrote", name)
