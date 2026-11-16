"""Step 1: portfolio context, raw-data audit, development vs monitoring comparison."""
import sys; sys.path.insert(0, "src")
from mu_catiii import *
from plots import *

dev, mon, *_ = load_inputs()
raw_d, raw_m = pd.read_csv(RAW / "development_raw.csv"), pd.read_csv(RAW / "monitoring_raw.csv")

# Portfolio summary by period and segment
rows = []
for per, d in (("development", dev), ("monitoring", mon)):
    for seg, g in d.groupby("segment"):
        rows.append({"period": per, "segment": seg, "loans": len(g), "funded_usd": g.funded_amount.sum(),
                     "default_rate": g.default_flag.mean(), "avg_fico": g.fico_origination.mean(),
                     "term_months": g.term_months.max(), "max_months_on_book": g.months_on_book.max()})
summ = pd.DataFrame(rows); summ.to_csv(TABLES / "01_portfolio_summary.csv", index=False)
print(summ.round(4).to_string(index=False))

# Raw data audit (what was wrong, how it was treated)
def cnt(r, s):
    return {
        "FICO at origination outside 300-850 (999)": (int(((r.fico_origination > 850) | (r.fico_origination < 300)).sum()), "set to missing, flagged, imputed (flag columns kept)"),
        "Negative DTI": (int((r.dti_ratio < 0).sum()), "set to missing, flagged, imputed"),
        "Missing annual income": (int(r.annual_income.isna().sum()), "imputed, `annual_income_imputed_flag`=1"),
        "Missing DTI": (int(r.dti_ratio.isna().sum()), "imputed, `dti_ratio_imputed_flag`=1"),
        "Missing refreshed FICO": (int(r.fico_current.isna().sum()), "fallback to origination FICO, `fico_current_source`"),
        "Employment length missing/free text": (int(r.emp_length_raw.isna().sum()), "parsed to years; unknown flagged"),
        "Utilization empty (term loans, not applicable)": (int(r.utilization_ratio.isna().sum()), "kept empty; `utilization_applicable_flag`=0 (NOT zero)"),
        "Duplicate loan_id": (int(r.duplicated("loan_id").sum()), "none found"),
    }
cd, cm = cnt(raw_d, dev), cnt(raw_m, mon)
audit = pd.DataFrame([{"issue": k, "development": cd[k][0], "monitoring": cm[k][0], "treatment": cd[k][1]} for k in cd])
audit.to_csv(TABLES / "01_raw_data_audit.csv", index=False); print(audit.to_string(index=False))

# Pool structure
pools = pd.concat([dev.assign(period="development"), mon.assign(period="monitoring")])
pool_n = pools.pivot_table(index="pool_id", columns="period", values="loan_id", aggfunc="count")
pool_n.to_csv(TABLES / "01_pool_counts.csv")

# Fig 1: portfolio mix and default rate dev vs mon
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
mix = summ.pivot(index="segment", columns="period", values="funded_usd").loc[SEGMENTS] / 1e6
mix.plot.bar(ax=ax[0], color=[BLUE, ORANGE], rot=0); ax[0].set_title("Funded amount by segment (USD millions)")
ax[0].set_xlabel("")
dr = summ.pivot(index="segment", columns="period", values="default_rate").loc[SEGMENTS] * 100
dr.plot.bar(ax=ax[1], color=[BLUE, ORANGE], rot=0); ax[1].set_title("Observed default rate (%)"); ax[1].set_xlabel("")
fig.savefig(FIGS / "fig01_portfolio_mix_and_default_rate.png"); plt.close(fig)

# Fig 2: default rate by FICO band, development vs monitoring
fig, ax = plt.subplots(1, 4, figsize=(11, 3.2), sharey=True)
for a, seg in zip(ax, SEGMENTS):
    for per, d, c in (("development", dev, BLUE), ("monitoring", mon, ORANGE)):
        r = d[d.segment == seg].groupby("fico_band").default_flag.mean().reindex(BAND_ORDER) * 100
        a.plot(range(4), r.values, marker="o", color=c, label=per)
    a.set_xticks(range(4)); a.set_xticklabels(["sub", "near", "prime", "super"]); a.set_title(seg)
ax[0].set_ylabel("default rate (%)"); ax[0].legend()
fig.suptitle("Default rate by FICO band: the whole curve shifts up, and the ranking holds", fontweight="bold")
fig.savefig(FIGS / "fig02_default_by_fico_band.png"); plt.close(fig)

# Fig 3: macro drift
fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
for a, col, ttl in zip(ax, ["unemployment_rate_regional", "hpi_change_regional_pct"],
                       ["Regional unemployment rate (%)", "Regional house price change (%)"]):
    a.hist(dev[col], bins=30, alpha=.65, color=BLUE, label="development", density=True)
    a.hist(mon[col], bins=30, alpha=.65, color=ORANGE, label="monitoring", density=True); a.set_title(ttl)
ax[0].legend(); fig.savefig(FIGS / "fig03_macro_drift.png"); plt.close(fig)
