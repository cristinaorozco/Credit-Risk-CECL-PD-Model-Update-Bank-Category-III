"""Step 2: the monitoring finding that triggers the Model Update."""
import sys; sys.path.insert(0, "src")
from mu_catiii import *
from plots import *
from scipy import stats

dev, mon, pd_old, lgd, ead = load_inputs()
pdm = pd_old.set_index("pool_id")["PD_lifetime_CECL"]

# --- PSI (development = benchmark)
rows = [{"metric": "PSI pool_id (score)", "object": "portfolio", "value": psi(dev.pool_id, mon.pool_id, categorical=True)}]
for seg in SEGMENTS:
    rows.append({"metric": "PSI fico_band", "object": seg,
                 "value": psi(dev[dev.segment == seg].fico_band, mon[mon.segment == seg].fico_band, categorical=True)})
for col in ["unemployment_rate_regional", "hpi_change_regional_pct"]:
    rows.append({"metric": f"PSI {col}", "object": "macro input", "value": psi(dev[col], mon[col], bins=10)})
psi_tab = pd.DataFrame(rows); psi_tab["status"] = psi_tab.value.map(lambda v: rag(v, PSI_AMBER, PSI_RED))

# --- Discrimination on monitoring outcomes (score = production lifetime PD)
auc_d, gini_d, ks_d = discrimination(dev.default_flag, dev.pool_id.map(pdm))
auc_m, gini_m, ks_m = discrimination(mon.default_flag, mon.pool_id.map(pdm))
disc = pd.DataFrame([
    {"metric": "AUC-ROC", "development": auc_d, "monitoring": auc_m, "change_pct": auc_m / auc_d - 1,
     "status": rag(auc_m, AUC_GREEN, AUC_RED, higher_is_worse=False)},
    {"metric": "Gini", "development": gini_d, "monitoring": gini_m, "change_pct": gini_m / gini_d - 1,
     "status": rag(-(gini_m / gini_d - 1), .10, .20)},
    {"metric": "KS", "development": ks_d, "monitoring": ks_m, "change_pct": ks_m / ks_d - 1,
     "status": rag(-(ks_m / ks_d - 1), .10, .20)}])
# note: status for Gini/KS uses relative DROP vs benchmark (10% amber, 20% red)

# --- Actual vs expected by pool, with exact binomial uncertainty
ae = []
for pid, g in mon.groupby("pool_id"):
    d = dev[dev.pool_id == pid]
    r_dev, r_mon, n = d.default_flag.mean(), g.default_flag.mean(), len(g)
    k = int(g.default_flag.sum())
    ci = stats.binomtest(k, n).proportion_ci(0.95, method="exact")
    p = stats.binomtest(k, n, r_dev).pvalue
    ae.append({"pool_id": pid, "n_dev": len(d), "n_mon": n, "rate_dev": r_dev, "rate_mon": r_mon, "AE_ratio": r_mon / r_dev,
               "AE_ci_low": ci.low / r_dev, "AE_ci_high": ci.high / r_dev, "p_value_vs_dev_rate": p})
ae = pd.DataFrame(ae).sort_values("AE_ratio", ascending=False).reset_index(drop=True)
ae["bonferroni_p"] = (ae.p_value_vs_dev_rate * len(ae)).clip(upper=1)
ae["significant_5pct_bonferroni"] = ae.bonferroni_p < .05
ae["status"] = ae.AE_ratio.map(lambda v: rag(v, AE_AMBER, AE_RED))

overall_ae_simple = ae.AE_ratio.mean()
overall_ae_pooled = mon.default_flag.mean() / dev.default_flag.mean()
print(psi_tab.round(4).to_string(index=False)); print(disc.round(4).to_string(index=False))
print(ae.round(4).to_string(index=False))
print(f"Simple mean of pool A/E = {overall_ae_simple:.4f}; portfolio default-rate ratio = {overall_ae_pooled:.4f}")
print(f"Pools with A/E > 1.10: {(ae.AE_ratio>AE_AMBER).sum()}/16 | > 1.35: {(ae.AE_ratio>AE_RED).sum()}/16 | significant: {ae.significant_5pct_bonferroni.sum()}")


# --- Is the shift uniform? Chi-square homogeneity test of a single multiplicative shift c across pools
O = mon.groupby("pool_id").default_flag.sum().reindex(ae.pool_id).to_numpy().astype(float)
E0 = (ae.rate_dev * ae.n_mon).to_numpy()
c = O.sum() / E0.sum()
chi2 = float((((O - c * E0) ** 2) / (c * E0)).sum()); dof = len(O) - 1
p_het = float(1 - stats.chi2.cdf(chi2, dof))
verdict = "cannot reject a single common shift" if p_het > .05 else "the shift is NOT uniform"
print(f"Single common shift c={c:.3f}; chi2={chi2:.1f} on {dof} df, p={p_het:.4f} -> {verdict}")

# --- Maturity-matched sensitivity: count only development defaults within the monitoring window (29 months)
dev29 = ((dev.default_flag == 1) & (dev.months_to_default <= 29)).astype(int)
ae_m = (mon.groupby("pool_id").default_flag.mean() / dev.assign(d29=dev29).groupby("pool_id").d29.mean())
print(f"Crude maturity truncation (dev defaults within 29m): simple mean {ae_m.mean():.4f}; range {ae_m.min():.3f}-{ae_m.max():.3f}")
hm = horizon_matched_ae(dev, mon)
hm_simple, hm_port = hm.AE_horizon_matched.mean(), hm.observed_defaults.sum() / hm.expected_defaults.sum()
print(f"Horizon-matched model-based A/E: simple mean {hm_simple:.4f}; portfolio {hm_port:.4f}; range {hm.AE_horizon_matched.min():.2f}-{hm.AE_horizon_matched.max():.2f}")
hm.to_csv(TABLES / "02_actual_vs_expected_horizon_matched.csv", index=False)

# --- Persist
psi_tab.to_csv(TABLES / "02_psi.csv", index=False)
disc.to_csv(TABLES / "02_discrimination_monitoring.csv", index=False)
ae.to_csv(TABLES / "02_actual_vs_expected_by_pool.csv", index=False)
pd.DataFrame([{"AE_simple_mean_of_pools": overall_ae_simple, "AE_portfolio_default_rate_ratio": overall_ae_pooled,
               "AE_dev_truncated_29m_simple_mean": ae_m.mean(), "AE_horizon_matched_simple_mean": hm_simple, "AE_horizon_matched_portfolio": hm_port, "common_shift_c": c, "heterogeneity_chi2": chi2,
               "heterogeneity_dof": dof, "heterogeneity_p": p_het,
               "pools_above_1p10": int((ae.AE_ratio > AE_AMBER).sum()), "pools_above_1p35": int((ae.AE_ratio > AE_RED).sum()),
               "pools_significant_bonferroni": int(ae.significant_5pct_bonferroni.sum())}]).to_csv(TABLES / "02_monitoring_summary.csv", index=False)

# --- Figures
fig, ax = plt.subplots(figsize=(8.5, 5.2))
a2 = ae.iloc[::-1]
cols = [RED if r > AE_RED else (AMBER if r > AE_AMBER else GREEN) for r in a2.AE_ratio]
ax.barh(a2.pool_id, a2.AE_ratio, color=cols, alpha=.85)
ax.errorbar(a2.AE_ratio, range(len(a2)), xerr=[a2.AE_ratio - a2.AE_ci_low, a2.AE_ci_high - a2.AE_ratio], fmt="none", ecolor="black", capsize=2, lw=.8)
ax.axvline(1, color="black", lw=1); ax.axvline(AE_AMBER, color=AMBER, ls="--", lw=1); ax.axvline(AE_RED, color=RED, ls="--", lw=1)
ax.set_xlabel("Actual / expected default rate (monitoring vs development), 95% exact CI"); ax.set_title("Actual exceeds expected in 15 of 16 pools; only 2 are individually significant")
fig.savefig(FIGS / "fig04_actual_vs_expected_by_pool.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
t = psi_tab.copy(); t["label"] = t.metric.str.replace("PSI ", "") + "\n" + t.object
ax[0].bar(range(len(t)), t.value, color=[{"GREEN": GREEN, "AMBER": AMBER, "RED": RED}[s] for s in t.status])
ax[0].set_yscale("symlog", linthresh=.01); ax[0].axhline(PSI_AMBER, color=AMBER, ls="--"); ax[0].axhline(PSI_RED, color=RED, ls="--")
ax[0].set_xticks(range(len(t))); ax[0].set_xticklabels(t.label, rotation=60, ha="right", fontsize=7); ax[0].set_title("PSI (development as benchmark)")
x = np.arange(3); w = .38
ax[1].bar(x - w/2, disc.development, w, color=BLUE, label="development"); ax[1].bar(x + w/2, disc.monitoring, w, color=ORANGE, label="monitoring")
ax[1].set_xticks(x); ax[1].set_xticklabels(disc.metric); ax[1].set_title("Rank ordering is intact (AUC, Gini, KS)"); ax[1].legend()
fig.savefig(FIGS / "fig05_psi_and_discrimination.png"); plt.close(fig)
