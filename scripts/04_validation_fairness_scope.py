"""Step 4: out-of-sample validation, scope test (LGD/EAD), fair lending follow-up."""
import sys; sys.path.insert(0, "src")
from mu_catiii import *
from plots import *
from scipy import stats

dev, mon, pd_old, lgd, ead = load_inputs()
pooled = pd.concat([dev, mon], ignore_index=True)
tb = pooled.groupby("segment")["term_months"].max().to_dict()

# ---- 4a. Holdout validation (20%, stratified by pool, split BEFORE fitting)
train, hold = train_test_split(pooled, test_size=0.20, stratify=pooled["pool_id"], random_state=7)
fit = estimate_pd(train, tb, col="PD_holdout_fit")
val = hold.merge(fit[["pool_id", "PD_holdout_fit"]], on="pool_id")
auc, gini, ks = discrimination(val.default_flag, val.PD_holdout_fit)
r_tr, r_ho = train.groupby("pool_id").default_flag.mean(), hold.groupby("pool_id").default_flag.mean()
n_ho = hold.groupby("pool_id").size()
cal = pd.concat([r_tr.rename("rate_train"), r_ho.rename("rate_holdout"), n_ho.rename("n_holdout")], axis=1)
cal["AE_ratio"] = cal.rate_holdout / cal.rate_train
ae_agg = (r_ho * n_ho).sum() / (r_tr * n_ho).sum()
print(f"Holdout n={len(hold)}: AUC {auc:.4f} Gini {gini:.4f} KS {ks:.4f}; aggregate A/E {ae_agg:.4f}")
# Is the holdout A/E of 1.00 informative? Bootstrap its sampling range.
rng = np.random.default_rng(11); sims = []
for _ in range(500):
    h = hold.sample(len(hold), replace=True, random_state=int(rng.integers(1e9)))
    rh = h.groupby("pool_id").default_flag.mean(); nh = h.groupby("pool_id").size()
    sims.append((rh * nh).sum() / (r_tr * nh).sum())
ae_lo, ae_hi = np.percentile(sims, [2.5, 97.5]); print(f"A/E 95% sampling range [{ae_lo:.3f}, {ae_hi:.3f}]")
pd.DataFrame([{"holdout_loans": len(hold), "AUC": auc, "Gini": gini, "KS": ks, "AE_aggregate": ae_agg, "AE_low": ae_lo, "AE_high": ae_hi}]).to_csv(TABLES / "04_holdout_validation.csv", index=False)
cal.to_csv(TABLES / "04_holdout_calibration_by_pool.csv")

# ---- 4b. Scope test: did LGD or EAD move in monitoring? (justifies the PD-only scope)
def realized(d):
    x = d[d.default_flag == 1].copy(); x["lgd_realized"] = 1 - x.recovery_amount / x.exposure_at_default
    return x
rd, rm = realized(dev), realized(mon)
lgd_t = lgd.groupby("segment").LGD_expected_CECL.mean()
rows = []
for sg in SEGMENTS:
    a, b = rd[rd.segment == sg].lgd_realized, rm[rm.segment == sg].lgd_realized
    t = stats.ttest_ind(b, a, equal_var=False)
    rows.append({"segment": sg, "defaults_dev": len(a), "defaults_mon": len(b), "LGD_table_avg": lgd_t[sg],
                 "LGD_realized_dev": a.mean(), "LGD_realized_mon": b.mean(), "diff_mon_minus_dev": b.mean() - a.mean(), "p_value": t.pvalue})
lgd_chk = pd.DataFrame(rows)
rows = []
for sg in SEGMENTS:
    col = "ccf_realized" if sg in ("credit_card", "heloc") else "ead_ratio_realized"
    a, b = dev[(dev.segment == sg) & dev[col].notna()][col], mon[(mon.segment == sg) & mon[col].notna()][col]
    t = stats.ttest_ind(b, a, equal_var=False)
    rows.append({"segment": sg, "measure": col, "n_dev": len(a), "n_mon": len(b), "mean_dev": a.mean(), "mean_mon": b.mean(), "diff": b.mean() - a.mean(), "p_value": t.pvalue})
ead_chk = pd.DataFrame(rows)
print(lgd_chk.round(4).to_string(index=False)); print(ead_chk.round(4).to_string(index=False))
lgd_chk.to_csv(TABLES / "04_scope_test_lgd.csv", index=False); ead_chk.to_csv(TABLES / "04_scope_test_ead.csv", index=False)

# ---- 4c. Fair lending follow-up: AIR with production PD vs recalibrated PD (synthetic proxy)
new = pd.read_csv(ROOT / "outputs" / "pd_curves_by_pool_recalibrated.csv").set_index("pool_id").PD_lifetime_CECL_v2
old = pd_old.set_index("pool_id").PD_lifetime_CECL
a_old, a_new = air_by_group(dev, dev.pool_id.map(old)), air_by_group(dev, dev.pool_id.map(new))
w_old, w_new = air_by_group(dev, dev.pool_id.map(old), within_segment=True), air_by_group(dev, dev.pool_id.map(new), within_segment=True)
air = pd.DataFrame({"AIR_production": a_old, "AIR_recalibrated": a_new,
                    "AIR_production_within_product": w_old, "AIR_recalibrated_within_product": w_new}).reindex(["all"] + SEGMENTS)
air["share_below_portfolio_median"] = [np.nan] + [float((dev.pool_id.map(old)[dev.segment == sg] <= dev.pool_id.map(old).median()).mean()) for sg in SEGMENTS]
air["status_production"] = air.AIR_production.map(lambda v: rag(v, AIR_GREEN, AIR_RED, False))
air["status_recalibrated"] = air.AIR_recalibrated.map(lambda v: rag(v, AIR_GREEN, AIR_RED, False))
print(air.round(4)); air.to_csv(TABLES / "04_adverse_impact_ratio.csv")

# ---- 4d. What if the HELOC LGD drift is real? Two readings, bracketing the same forecast question as for PD.
#   pooled evidence    : HELOC LGD re-estimated on development + monitoring defaults (same logic as the PD update)
#   full persistence   : HELOC LGD moved to the monitoring-period level (the new regime lasts)
h = lgd_chk.set_index("segment").loc["heloc"]
pooled_lgd = (h.defaults_dev * h.LGD_realized_dev + h.defaults_mon * h.LGD_realized_mon) / (h.defaults_dev + h.defaults_mon)
scale_pool, scale_full = pooled_lgd / h.LGD_realized_dev, h.LGD_realized_mon / h.LGD_realized_dev
base = el_table(pd_old.rename(columns={"PD_lifetime_CECL": "PD"}), "PD", lgd, ead, dev)
newt = el_table(new.rename("PD").reset_index().assign(segment=lambda d: d.pool_id.str.split(r" \| ").str[0]), "PD", lgd, ead, dev)
isH = lambda t: np.where(t.segment == "heloc", 1.0, 0.0)
def el_with(t, sc): return float((t.EL * (1 + isH(t) * (sc - 1))).sum())
rows = [("PD recalibration only (the Model Update scope)", newt.EL.sum()),
        ("HELOC LGD only, pooled evidence", el_with(base, scale_pool)),
        ("PD recalibration + HELOC LGD, pooled evidence", el_with(newt, scale_pool)),
        ("HELOC LGD only, monitoring regime persists", el_with(base, scale_full)),
        ("PD recalibration + HELOC LGD, monitoring regime persists", el_with(newt, scale_full))]
comb = pd.DataFrame(rows, columns=["scenario", "EL"]); comb["change_vs_production"] = comb.EL / base.EL.sum() - 1
comb["above_10pct_threshold"] = comb.change_vs_production > MATERIALITY_EL
print(f"HELOC LGD: pooled {pooled_lgd:.4f} (x{scale_pool:.3f} vs dev realized), full persistence x{scale_full:.3f}")
print(comb.round(4).to_string(index=False)); comb.to_csv(TABLES / "04_scope_scenario_heloc_lgd.csv", index=False)
# HELOC realized LGD trend by origination half-year (is it a gradual move or a break?)
tr = pd.concat([rd, rm])[lambda d: d.segment == "heloc"].assign(half=lambda d: pd.to_datetime(d.origination_date).dt.year.astype(str) + "H" + ((pd.to_datetime(d.origination_date).dt.month > 6) + 1).astype(str))
heloc_trend = tr.groupby("half").agg(defaults=("lgd_realized", "size"), lgd_realized=("lgd_realized", "mean")); print(heloc_trend.round(4)); heloc_trend.to_csv(TABLES / "04_heloc_lgd_by_vintage.csv")

# ---- Figures
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
ax[0].scatter(cal.rate_train * 100, cal.rate_holdout * 100, color=BLUE, s=cal.n_holdout / 4)
m = cal[["rate_train", "rate_holdout"]].max().max() * 100 + 2; ax[0].plot([0, m], [0, m], color="black", lw=.8)
ax[0].set_xlabel("Training default rate (%)"); ax[0].set_ylabel("Holdout default rate (%)"); ax[0].set_title(f"Holdout: A/E {ae_agg:.3f}, AUC {auc:.3f} (bubble = holdout size)")
y = np.arange(len(air)); w = .38
ax[1].barh(y - w/2, air.AIR_production, w, color=BLUE, label="production PD"); ax[1].barh(y + w/2, air.AIR_recalibrated, w, color=ORANGE, label="recalibrated PD")
ax[1].set_yticks(y); ax[1].set_yticklabels(air.index); ax[1].axvline(AIR_GREEN, color=AMBER, ls="--"); ax[1].axvline(AIR_RED, color=RED, ls="--"); ax[1].set_xlim(.6, 1.05)
ax[1].set_title("Adverse Impact Ratio (synthetic proxy)"); ax[1].legend(loc="lower left")
fig.savefig(FIGS / "fig10_holdout_and_air.png"); plt.close(fig)
