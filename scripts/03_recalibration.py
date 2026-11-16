"""Step 3: PD recalibration on pooled evidence, EL impact, materiality, sensitivity, bootstrap."""
import sys, time; sys.path.insert(0, "src")
from mu_catiii import *
from plots import *

N_BOOT = 200
dev, mon, pd_old, lgd, ead = load_inputs()
pooled = pd.concat([dev, mon], ignore_index=True)
tb = pooled.groupby("segment")["term_months"].max().to_dict()
old = pd_old.rename(columns={"PD_lifetime_CECL": "PD_old"})[["pool_id", "segment", "PD_old"]]

new = estimate_pd(pooled, tb)
comp = old.merge(new[["pool_id", "n_loans_evidence", "raw_default_rate", "PD_lifetime_unconstrained", "PD_lifetime"]], on="pool_id")
comp = comp.rename(columns={"PD_lifetime": "PD_new"})
comp["change_pct"] = comp.PD_new / comp.PD_old - 1
comp["isotonic_adjusted"] = (comp.PD_new - comp.PD_lifetime_unconstrained).abs() > 1e-12
el_old = el_table(old.rename(columns={"PD_old": "PD"}), "PD", lgd, ead, dev)
el_new = el_table(comp.rename(columns={"PD_new": "PDn"}), "PDn", lgd, ead, dev)
imp = el_old[["pool_id", "segment", "n_loans", "exposure_funded", "EL"]].rename(columns={"EL": "EL_old"}).merge(
    el_new[["pool_id", "EL"]].rename(columns={"EL": "EL_new"}), on="pool_id")
imp["delta_EL"] = imp.EL_new - imp.EL_old
imp["EL_change_pct"] = imp.EL_new / imp.EL_old - 1
tot_old, tot_new, expo = imp.EL_old.sum(), imp.EL_new.sum(), imp.exposure_funded.sum()
simple_mean = comp.change_pct.mean()
seg = imp.groupby("segment")[["exposure_funded", "EL_old", "EL_new"]].sum()
seg["EL_change_pct"] = seg.EL_new / seg.EL_old - 1; seg["EL_old_pct_exposure"] = seg.EL_old / seg.exposure_funded; seg["EL_new_pct_exposure"] = seg.EL_new / seg.exposure_funded
print(f"Evidence: {len(pooled)} loans. Exposure ${expo:,.0f}")
print(f"EL old ${tot_old:,.0f} ({tot_old/expo:.2%}) -> new ${tot_new:,.0f} ({tot_new/expo:.2%}); change ${tot_new-tot_old:,.0f} ({tot_new/tot_old-1:.2%})")
print(f"Simple mean of pool PD changes {simple_mean:.2%} | EL-weighted PD change {tot_new/tot_old-1:.2%}")
print(comp[["pool_id", "PD_old", "PD_new", "change_pct", "isotonic_adjusted"]].round(4).to_string(index=False)); print(seg.round(4))

# --- Materiality bridge
mon_sum = pd.read_csv(TABLES / "02_monitoring_summary.csv").iloc[0]
bridge = pd.DataFrame([
    {"step": "Preliminary signal: simple mean of pool A/E minus 1 (raw rates)", "value": mon_sum.AE_simple_mean_of_pools - 1},
    {"step": "Recalibrated PD change, simple mean across pools", "value": simple_mean},
    {"step": "Recalibrated change in Expected Loss (PD x LGD x EAD, LGD/EAD unchanged)", "value": tot_new / tot_old - 1},
    {"step": "Internal materiality threshold [JUDGMENT]", "value": MATERIALITY_EL}])
bridge.to_csv(TABLES / "03_materiality_bridge.csv", index=False)

# --- Alternatives & sensitivities (EL change vs production)
def el_change(pdtab, col):
    return el_table(pdtab, col, lgd, ead, dev).EL.sum() / tot_old - 1
alts = []
ae = pd.read_csv(TABLES / "02_actual_vs_expected_by_pool.csv").set_index("pool_id").AE_ratio
alts.append(("Chosen: pooled dev+monitoring, tail 300, monotone", tot_new / tot_old - 1))
for me in (150, 600):
    t = estimate_pd(pooled, tb, min_exposure=me); alts.append((f"Tail credible exposure = {me}", el_change(t, "PD_lifetime")))
t = estimate_pd(pooled, tb, monotone=False); alts.append(("No monotonicity constraint", el_change(t, "PD_lifetime")))
t = estimate_pd(mon, tb); alts.append(("Monitoring period only (29 months, 10,000 loans)", el_change(t, "PD_lifetime")))
t = estimate_pd(dev, tb); alts.append(("Development only (re-estimated, sanity check)", el_change(t, "PD_lifetime")))
s125 = old.assign(PD=old.PD_old * mon_sum.AE_simple_mean_of_pools); alts.append(("Scalar: every PD x 1.251 (monitoring regime persists in full)", el_change(s125, "PD")))
hm_s = mon_sum.AE_horizon_matched_simple_mean
s15 = old.assign(PD=(old.PD_old * hm_s).clip(upper=1)); alts.append((f"Scalar: every PD x {hm_s:.2f} (horizon-matched A/E, regime persists)", el_change(s15, "PD")))
sp = old.assign(PD=(old.PD_old * old.pool_id.map(ae)).clip(upper=1)); alts.append(("Pool-specific scalar: PD x pool A/E (overfits noise)", el_change(sp, "PD")))
alts = pd.DataFrame(alts, columns=["alternative", "EL_change_pct"]); alts["above_10pct_threshold"] = alts.EL_change_pct > MATERIALITY_EL
alts.to_csv(TABLES / "03_alternatives_sensitivity.csv", index=False); print(alts.round(4).to_string(index=False))

# --- Bootstrap. Two versions:
#  (a) unpaired: production PD held fixed, uncertainty only in the new estimate (what the point estimate is compared with)
#  (b) paired: dev and monitoring resampled separately; old = estimator on dev resample, new = estimator on pooled resample.
#      (b) answers "is the change distinguishable from estimation noise?" because dev data is 2/3 of the pooled sample.
rng = np.random.default_rng(2026); boots, boots_p, seg_el = [], [], []; t0 = time.time()
gp = {k: v.index.to_numpy() for k, v in pooled.groupby("pool_id")}
gd = {k: v.index.to_numpy() for k, v in dev.groupby("pool_id")}; gm = {k: v.index.to_numpy() for k, v in mon.groupby("pool_id")}
for b in range(N_BOOT):
    idx = np.concatenate([rng.choice(ix, len(ix), replace=True) for ix in gp.values()])
    bt = estimate_pd(pooled.loc[idx], tb); boots.append(el_change(bt, "PD_lifetime"))
    elb = el_table(bt, "PD_lifetime", lgd, ead, dev); seg_el.append(elb.groupby("segment").EL.sum() / seg.EL_old - 1)
    di = np.concatenate([rng.choice(ix, len(ix), replace=True) for ix in gd.values()])
    mi = np.concatenate([rng.choice(ix, len(ix), replace=True) for ix in gm.values()])
    d_b, m_b = dev.loc[di], mon.loc[mi]
    o_b = estimate_pd(d_b, tb); n_b = estimate_pd(pd.concat([d_b, m_b], ignore_index=True), tb)
    boots_p.append(el_table(n_b, "PD_lifetime", lgd, ead, dev).EL.sum() / el_table(o_b, "PD_lifetime", lgd, ead, dev).EL.sum() - 1)
boots, boots_p = np.array(boots), np.array(boots_p); seg_el = pd.DataFrame(seg_el)
lo, hi = np.percentile(boots, [2.5, 97.5]); plo, phi = np.percentile(boots_p, [2.5, 97.5])
print(f"Unpaired bootstrap {N_BOOT} reps ({time.time()-t0:.0f}s): mean {boots.mean():.2%}, 95% [{lo:.2%}, {hi:.2%}], share >10%: {(boots>MATERIALITY_EL).mean():.1%}")
print(f"Paired bootstrap: mean {boots_p.mean():.2%}, 95% [{plo:.2%}, {phi:.2%}], share >10%: {(boots_p>MATERIALITY_EL).mean():.1%}, share <=0: {(boots_p<=0).mean():.1%}")
print("Std of EL change by segment (unpaired):", seg_el.std().round(3).to_dict())
seg_el.std().rename("bootstrap_sd_EL_change").to_csv(TABLES / "03_bootstrap_sd_by_segment.csv")
pd.DataFrame({"EL_change_unpaired": boots, "EL_change_paired": boots_p}).to_csv(TABLES / "03_bootstrap_EL_change.csv", index=False)
pd.DataFrame([{"EL_old": tot_old, "EL_new": tot_new, "delta_EL": tot_new - tot_old, "EL_change_pct": tot_new / tot_old - 1,
               "exposure_funded": expo, "EL_old_pct_exposure": tot_old / expo, "EL_new_pct_exposure": tot_new / expo,
               "PD_change_simple_mean": simple_mean, "boot_low": lo, "boot_high": hi, "boot_share_above_10pct": (boots > MATERIALITY_EL).mean(), "paired_low": plo, "paired_high": phi, "paired_share_above_10pct": (boots_p > MATERIALITY_EL).mean(), "paired_share_nonpositive": (boots_p <= 0).mean()}]
             ).to_csv(TABLES / "03_el_impact_summary.csv", index=False)
comp.to_csv(TABLES / "03_pd_old_vs_new.csv", index=False); imp.to_csv(TABLES / "03_el_impact_by_pool.csv", index=False); seg.to_csv(TABLES / "03_el_impact_by_segment.csv")
# the updated production PD table (the deliverable that would go to the model inventory)
comp[["pool_id", "segment", "PD_new"]].rename(columns={"PD_new": "PD_lifetime_CECL_v2"}).to_csv(ROOT / "outputs" / "pd_curves_by_pool_recalibrated.csv", index=False)

# --- Figures
fig, ax = plt.subplots(1, 2, figsize=(11, 5))
c2 = comp.sort_values(["segment", "PD_old"]).reset_index(drop=True)
ax[0].scatter(c2.PD_old, range(len(c2)), color=BLUE, label="production (v1)", zorder=3); ax[0].scatter(c2.PD_new, range(len(c2)), color=ORANGE, label="recalibrated (v2)", zorder=3)
for i, r in c2.iterrows(): ax[0].plot([r.PD_old, r.PD_new], [i, i], color=GREY, lw=1)
ax[0].set_yticks(range(len(c2))); ax[0].set_yticklabels(c2.pool_id, fontsize=7); ax[0].set_xlabel("Lifetime CECL PD"); ax[0].set_title("Lifetime PD by pool: production vs recalibrated"); ax[0].legend()
ax[1].barh(c2.pool_id, c2.change_pct * 100, color=[BLUE if v >= 0 else ORANGE for v in c2.change_pct]); ax[1].axvline(0, color="black", lw=.8)
ax[1].set_yticklabels([]); ax[1].set_xlabel("PD change (%)"); ax[1].set_title("Relative change in PD")
fig.savefig(FIGS / "fig06_pd_old_vs_new.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
b = bridge.iloc[[0, 1, 2]]; ax[0].bar(range(3), b.value * 100, color=[GREY, GREY, BLUE])
ax[0].axhline(MATERIALITY_EL * 100, color=RED, ls="--"); ax[0].text(2.4, MATERIALITY_EL * 100 + .6, "10% threshold", color=RED, ha="right")
ax[0].set_xticks(range(3)); ax[0].set_xticklabels(["Preliminary\n(A/E-1)", "PD change\n(simple mean)", "EL change\n(final)"]); ax[0].set_ylabel("%"); ax[0].set_title("Materiality: the signal is diluted, the final number is below threshold")
ax[1].hist(boots * 100, bins=25, color=BLUE, alpha=.6, label="unpaired"); ax[1].hist(boots_p * 100, bins=25, color=ORANGE, alpha=.6, label="paired"); ax[1].legend(); ax[1].axvline(tot_new / tot_old * 100 - 100, color="black"); ax[1].axvline(MATERIALITY_EL * 100, color=RED, ls="--")
ax[1].set_xlabel("EL change (%)"); ax[1].set_title(f"Bootstrap ({N_BOOT} reps): 95% [{lo:.0%}, {hi:.0%}] unpaired, [{plo:.0%}, {phi:.0%}] paired")
fig.savefig(FIGS / "fig07_materiality_and_bootstrap.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 3.6)); a = alts.iloc[::-1]
ax.barh(a.alternative, a.EL_change_pct * 100, color=[RED if v else BLUE for v in a.above_10pct_threshold]); ax.axvline(MATERIALITY_EL * 100, color=RED, ls="--")
ax.set_xlabel("EL change vs production (%)"); ax.set_title("What the choice of method does to the answer"); ax.tick_params(axis="y", labelsize=7)
fig.savefig(FIGS / "fig08_method_sensitivity.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.5, 3.6)); x = np.arange(4); w = .38
ax.bar(x - w/2, seg.loc[SEGMENTS].EL_old / 1e6, w, color=BLUE, label="production"); ax.bar(x + w/2, seg.loc[SEGMENTS].EL_new / 1e6, w, color=ORANGE, label="recalibrated")
ax.set_xticks(x); ax.set_xticklabels(SEGMENTS); ax.set_ylabel("Expected loss (USD millions)"); ax.set_title("Expected loss by segment"); ax.legend()
fig.savefig(FIGS / "fig09_el_by_segment.png"); plt.close(fig)
