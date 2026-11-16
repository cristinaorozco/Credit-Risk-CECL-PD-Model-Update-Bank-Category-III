import sys; sys.path.insert(0, "tools")
from pathlib import Path
from nbbuild import run_notebook
ROOT = Path(__file__).resolve().parents[1]
HEAD = '''import sys; sys.path.insert(0, "../src")
from mu_catiii import *
from plots import *
pd.set_option("display.width", 160)
dev, mon, pd_old, lgd, ead = load_inputs()
pooled = pd.concat([dev, mon], ignore_index=True)
term_by_segment = pooled.groupby("segment")["term_months"].max().to_dict()'''
T = lambda n: f"pd.read_csv(TABLES / '{n}')"

NB1 = [
("md", """# 01 · Context and data
**Scenario (fictional):** a Category III U.S. bank holds a consumer portfolio of four products (credit card, auto, personal loan, HELOC). Its CECL lifetime-PD model went into production on development data (loans originated Jan 2022 to Jun 2023). Twelve months later, the quarterly monitoring pack shows defaults running above expectation. The task: decide whether the model needs a **Model Update**, scope it, do it, validate it, and document it.

All data are **synthetic**. This notebook introduces the portfolio and audits the raw extract before anything is modelled."""),
("code", HEAD),
("md", "## 1. The portfolio\nTwo extracts with the same 28 columns: development (20,000 loans) and monitoring (10,000 loans, out of time)."),
("code", "display(pd.read_csv(RAW / 'development_raw.csv').head(3).T.head(28))"),
("code", "s = pd.read_csv(TABLES / '01_portfolio_summary.csv'); s['funded_usd_m'] = s.funded_usd / 1e6; s.drop(columns='funded_usd')"),
("code", "print(f\"Development funded amount: ${dev.funded_amount.sum():,.0f}  |  default rate {dev.default_flag.mean():.2%}\")\nprint(f\"Monitoring  funded amount: ${mon.funded_amount.sum():,.0f}  |  default rate {mon.default_flag.mean():.2%}\")\nshow_image(FIGS / 'fig01_portfolio_mix_and_default_rate.png')"),
("md", "## 2. Raw-data audit\nThe extracts are raw on purpose. Each problem below was found, treated, **flagged** in the processed file and not silently overwritten (the `*_raw` and `*_flag` columns stay in `data/processed`). The treatment is a documented assumption, see `docs/assumptions_and_limitations.md`."),
("code", "pd.read_csv(TABLES / '01_raw_data_audit.csv')"),
("md", "Two points worth stating. First, utilization is empty for term loans because it does **not apply**, not because it is zero; a real 0% on a revolving line is a different fact. Second, `state` and `zip_code` are never model inputs: they are fair-lending review variables because geography can act as a proxy for protected classes."),
("md", "## 3. Pools\nCECL requires pooling loans with similar risk characteristics (ASC 326-20-30-2; characteristics listed in 55-5). Here: 4 segments × 4 FICO bands = 16 pools."),
("code", "pc = pd.read_csv(TABLES / '01_pool_counts.csv'); pc['mon_share_of_pool'] = pc.monitoring / (pc.development + pc.monitoring); pc"),
("md", "## 4. What changed between the two periods\nThe default rate rose and the macro inputs moved: unemployment up, house-price growth down. The mix of FICO bands did **not** move, so the pools are populated the same way; what changed is how they behave."),
("code", "show_image(FIGS / 'fig02_default_by_fico_band.png'); show_image(FIGS / 'fig03_macro_drift.png')"),
("code", "print(dev[['unemployment_rate_regional','hpi_change_regional_pct']].mean().round(2).to_dict())\nprint(mon[['unemployment_rate_regional','hpi_change_regional_pct']].mean().round(2).to_dict())"),
]

NB2 = [
("md", """# 02 · Monitoring: what triggered the Model Update
The monitoring plan has six metric families with green/amber/red bands. **All thresholds are internal [JUDGMENT]**; no rule prescribes them. Development is the benchmark."""),
("code", HEAD),
("md", "## 1. Population stability (PSI)\nThe pool distribution is stable, but the **macro inputs are red**. Cause and effect are different findings: the customers look the same, the environment does not."),
("code", "display(pd.read_csv(TABLES / '02_psi.csv'))"),
("md", "## 2. Rank ordering\nDoes the model still sort good from bad? AUC, Gini and KS computed on monitoring outcomes with the production PD as score."),
("code", "display(pd.read_csv(TABLES / '02_discrimination_monitoring.csv'))"),
("md", "Rank ordering is intact. This is the key to the scope decision: the model **ranks** risk correctly but **levels** are too low. A level problem is a recalibration problem, not a redevelopment problem."),
("md", "## 3. Levels: actual versus expected\nA/E = monitoring default rate ÷ development default rate, by pool, with exact binomial 95% intervals."),
("code", "ae = pd.read_csv(TABLES / '02_actual_vs_expected_by_pool.csv'); display(ae[['pool_id','n_mon','rate_dev','rate_mon','AE_ratio','AE_ci_low','AE_ci_high','bonferroni_p','status']])\nshow_image(FIGS / 'fig04_actual_vs_expected_by_pool.png')"),
("code", "sm = pd.read_csv(TABLES / '02_monitoring_summary.csv').iloc[0]; display(sm.to_frame('value'))"),
("md", """### How to read this honestly
* The signal is real in aggregate: the simple mean of pool A/E is **1.25**, and 14 of 16 pools are above 1.10.
* But **only 2 pools are individually significant** after a Bonferroni correction, and a chi-square test **cannot reject a single common shift** across all pools (p ≈ 0.52). The spread of A/E from 0.92 to 1.66 is what sampling noise looks like in pools of 200 to 1,000 loans.
* Consequence for method: fitting a separate adjustment to each pool would chase noise. That is why the update pools the evidence and keeps the monotonicity constraint, rather than scaling each pool by its own A/E (tested in notebook 03).
* Raw rates ignore that monitoring loans are younger (at most 29 months on book, against 35). Comparing with the **model's own cumulative PD up to each loan's months on book** (horizon-matched A/E) gives **about 1.55**, so the raw 1.25 **understates** the deterioration. A cruder truncation of development defaults at 29 months (1.28) still mixes loans of different ages. This does not change the recalibration, which uses life tables that already handle age; it changes how large a forecast adjustment the allowance committee may need to consider."""),
("code", "show_image(FIGS / 'fig05_psi_and_discrimination.png')"),
("md", "## 4. Decision\nLevels are off (A/E ≈ 1.25), ranking is fine (AUC 0.704 vs 0.704), macro inputs are red. That points to **recalibration of PD** on fresh evidence. It is not a new methodology. Next: classify the change and size it (notebook 03)."),
]

NB3 = [
("md", """# 03 · Recalibration, impact and materiality
The production method is kept **exactly**: same pools, same 3-month hazard buckets, same credible-exposure tail, same monotonicity constraint. Only the evidence changes: development + monitoring (30,000 loans)."""),
("code", HEAD),
("md", "## 1. Method in one picture\nA pool's lifetime PD is built from a **life table**: in each 3-month age bucket, hazard = defaults ÷ loans still at risk. Loans are only observed to 35 months, but a HELOC runs 120. Beyond the observed ages the curve needs a **tail hazard**: the pooled hazard of the last buckets until at least 300 loans of exposure are reached [JUDGMENT]."),
("code", """pid = 'credit_card | near-prime(640-679)'
sub = pooled[pooled.pool_id == pid]
edges = list(range(0, int(sub.months_on_book.max()) + BUCKET, BUCKET))
lt = life_table(sub, edges); display(lt)
print('tail hazard:', round(tail_hazard(lt), 4), '| lifetime PD (36m term):', round(pd_curve(lt, 36)[1], 4))
fig, ax = plt.subplots(figsize=(6, 3)); ax.bar(lt.bucket_start + 1.5, lt.hazard * 100, width=2.6, color=BLUE); ax.set_xlabel('months on book'); ax.set_ylabel('hazard per 3 months (%)'); ax.set_title(pid)"""),
("md", "## 2. Re-estimate on pooled evidence"),
("code", """new = estimate_pd(pooled, term_by_segment)
old = pd_old[['pool_id','PD_lifetime_CECL']].rename(columns={'PD_lifetime_CECL':'PD_old'})
comp = old.merge(new[['pool_id','PD_lifetime_unconstrained','PD_lifetime']], on='pool_id').rename(columns={'PD_lifetime':'PD_new'})
comp['change_pct'] = comp.PD_new / comp.PD_old - 1
comp['monotone_fix'] = (comp.PD_new - comp.PD_lifetime_unconstrained).abs() > 1e-12
display(comp)
print('Simple mean of pool PD changes:', f'{comp.change_pct.mean():.2%}')
show_image(FIGS / 'fig06_pd_old_vs_new.png')"""),
("md", "Two details. HELOC prime and super-prime come out with the same PD because the unconstrained estimates were reversed (prime 0.062 below super-prime 0.090, which would rank the better credit as riskier), so the isotonic step pools them at 0.0775; the production model had the same fix. And HELOC subprime goes **down** (−5.5%): its monitoring A/E was 0.92, in line with the noise story above."),
("md", "## 3. Impact on Expected Loss\nEL = PD × LGD × EAD$ × loans, with LGD and EAD unchanged (scope, see decision log)."),
("code", """imp = pd.read_csv(TABLES / '03_el_impact_summary.csv').iloc[0]
print(f"Reference portfolio: ${imp.exposure_funded:,.0f}")
print(f"EL production : ${imp.EL_old:,.0f}  ({imp.EL_old_pct_exposure:.2%} of funded)")
print(f"EL recalibrated: ${imp.EL_new:,.0f}  ({imp.EL_new_pct_exposure:.2%} of funded)")
print(f"Change         : ${imp.delta_EL:,.0f}  ({imp.EL_change_pct:+.2%})")
print(f"Simple mean of pool PD changes ({imp.PD_change_simple_mean:.2%}) is NOT the weighted change; the EL-weighted change is {imp.EL_change_pct:.2%}.")
display(pd.read_csv(TABLES / '03_el_impact_by_segment.csv'))
show_image(FIGS / 'fig09_el_by_segment.png')"""),
("md", "## 4. Materiality\nThe preliminary signal (25.1%, from raw default rates) was the trigger. The **final** number is the one that is sized on Expected Loss: **+4.64%**, below the 10% internal threshold [JUDGMENT]. The preliminary figure overstated the impact because the pooled recalibration dilutes the deteriorated period with the stable history."),
("code", "display(pd.read_csv(TABLES / '03_materiality_bridge.csv'))"),
("md", "## 5. Is +4.64% distinguishable from noise, and how sure are we?\nTwo different bootstraps answer two different questions.\n* **Paired** (development and monitoring resampled separately; old = estimator on the development resample, new = estimator on the pooled resample): *is the change real?*\n* **Unpaired** (production PD held fixed): *how uncertain is the new EL level?*"),
("code", "b = pd.read_csv(TABLES / '03_bootstrap_EL_change.csv'); import numpy as np\nfor c in b: print(f'{c:20s} mean {b[c].mean():+.2%}  95% [{np.percentile(b[c],2.5):+.2%}, {np.percentile(b[c],97.5):+.2%}]  share above 10%: {(b[c]>MATERIALITY_EL).mean():.1%}')\ndisplay(pd.read_csv(TABLES / '03_bootstrap_sd_by_segment.csv'))\nshow_image(FIGS / 'fig07_materiality_and_bootstrap.png')"),
("md", "The **change** is real and below 10% (paired interval about +1.7% to +8.9%). The **level** is much less certain (unpaired interval about −8% to +19%), and the uncertainty comes from the long-dated products (HELOC and auto) where most of the lifetime PD is extrapolated from a tail hazard. That belongs in the report, not under it."),
("md", "## 6. What if the method were different?"),
("code", "display(pd.read_csv(TABLES / '03_alternatives_sensitivity.csv'))\nshow_image(FIGS / 'fig08_method_sensitivity.png')"),
("md", """How to read the table:
* **Development only** returns exactly 0.00%: the code reproduces the production model, a necessary sanity check.
* **Monitoring only** gives +47%: a 29-month, single-regime sample, so it is a stress view and not an estimate.
* **Scalar 1.251** gives +25% (and a scalar at the horizon-matched 1.55 would give about +55%): it assumes the new regime lasts for the full life of every loan. The pooled method assumes the opposite end (history keeps two-thirds of the weight). The truth sits between them and is a **forecast question**, not a statistics question. CECL requires a reasonable and supportable forecast and a reversion approach; the Model Update recalibrates the model but does not replace that judgement. It is raised as a follow-up in the report.
* **Pool-specific scalar** gives +20% and overfits noise (see notebook 02)."""),
]

NB4 = [
("md", "# 04 · Validation, scope check and fair lending follow-up"),
("code", HEAD),
("md", """## 1. Out-of-sample validation
Recalibrating on **all** the evidence leaves no independent period to test on. So 20% of the pooled loans (stratified by pool) are set aside **before** fitting and the model is re-estimated on the other 80%.

*Limit that matters:* this is out-of-**sample**, not out-of-**time**. It shows the fit is not memorising rows. It does not prove the model will hold in conditions that have not happened yet; only time does, hence the reinforced monitoring condition."""),
("code", "h = pd.read_csv(TABLES / '04_holdout_validation.csv'); display(h.T)\ndisplay(pd.read_csv(TABLES / '04_holdout_calibration_by_pool.csv'))"),
("md", "Note the A/E sampling range [0.92, 1.08]: an aggregate A/E of 1.00 is a clean result, but this holdout could not have distinguished an error of ±8%. The comparison is raw rate against raw rate over comparable windows. (Comparing a raw rate with a *lifetime* PD would mix different horizons, so it is not done.)"),
("md", "## 2. Scope check: did LGD or EAD move too?\nThe Model Update was scoped to PD because the monitoring finding was about default rates. Before signing off a PD-only scope it is worth testing that nothing else moved."),
("code", "display(pd.read_csv(TABLES / '04_scope_test_lgd.csv'))\ndisplay(pd.read_csv(TABLES / '04_scope_test_ead.csv'))"),
("md", "**Finding: HELOC realized LGD rose from 0.30 to 0.36 (p < 0.0001).** The other three products did not move. The HPI fell from +4.0% to +1.0% in the same window, which is the collateral channel one would expect. By origination half-year:"),
("code", "display(pd.read_csv(TABLES / '04_heloc_lgd_by_vintage.csv'))"),
("md", "A break at the 2023H2 vintage, not a drift. Caveat: monitoring loans have had less time for recoveries to arrive, which could bias LGD upward; but the same shorter window did not move the other three products, which argues against a pure artifact. What it would do to the answer:"),
("code", "display(pd.read_csv(TABLES / '04_scope_scenario_heloc_lgd.csv'))"),
("md", "**Two readings of the same forecast question.** If HELOC LGD is re-estimated on pooled evidence (the same logic as the PD update), the combined change is **+7.4%**. If the monitoring-period LGD persists, it is **+12.2%**. The range straddles the 10% threshold. Changes should not be split to stay under a materiality line, so the report recommends assessing the PD and LGD items **together**, applying the policy's borderline rule, and treating the package as potentially material until the linked HELOC LGD review concludes."),
("md", "## 3. Fair lending follow-up\nA synthetic BISG-style proxy (never a model input) is used to compute an **Adverse Impact Ratio**: approval rate of the protected-proxy group ÷ approval rate of the reference group, with approval defined as lifetime PD at or below the portfolio median. Internal scale [JUDGMENT]: ≥ 0.90 green, 0.80 to 0.90 amber, < 0.80 red."),
("code", "air = pd.read_csv(TABLES / '04_adverse_impact_ratio.csv', index_col=0); display(air)\nshow_image(FIGS / 'fig10_holdout_and_air.png')"),
("md", """The recalibration leaves AIR unchanged at this precision: the update shifts levels, not the ordering of loans around the median that defines approval. The credit-card result (red, 0.73) is **an artifact of the cut-off rule, not a finding**: one portfolio-wide median leaves only 36% of cards under the cut-off, against about 65% for the other products, because cards carry higher PDs. With a cut-off inside each product the card AIR is 0.85, in line with the others (columns `*_within_product`).

Regulatory framing (see decision log): since the CFPB's April 2026 final rule (effective July 21, 2026), Regulation B no longer treats ECOA as providing a disparate-impact test, but proxy-based disparate **treatment** remains prohibited, and the Fair Housing Act (relevant to HELOC) continues to be read to cover disparate impact (*Inclusive Communities*, 2015). AIR is used here as an internal governance indicator, not as a legal test."""),
]
for name, cells in (("01_context_and_data", NB1), ("02_monitoring_trigger", NB2), ("03_recalibration_impact", NB3), ("04_validation_scope_fairlending", NB4)):
    run_notebook(cells, ROOT / "notebooks" / f"{name}.ipynb", ROOT / "notebooks"); print("built", name)
