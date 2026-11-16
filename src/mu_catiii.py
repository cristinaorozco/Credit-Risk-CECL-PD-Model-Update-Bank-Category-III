"""Core functions for the Category III PD Model Update (recalibration).

Everything the notebooks and scripts need lives here so that results are
reproducible from one place. Methodology follows the production model:
3-month life-table hazards, a credible-exposure tail hazard, monotonicity
across FICO bands (isotonic regression) and EL = PD x LGD x EAD x n_loans.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROD = ROOT / "data" / "production_model"
TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"

BUCKET = 3                      # months per hazard bucket
MIN_EXPOSURE_TAIL = 300         # credible exposure for the tail hazard [JUDGMENT]
BAND_RANK = {"subprime(<640)": 0, "near-prime(640-679)": 1,
             "prime(680-719)": 2, "super-prime(720+)": 3}
BAND_ORDER = list(BAND_RANK)
SEGMENTS = ["auto_loan", "personal_loan", "credit_card", "heloc"]

# Internal thresholds. All are [JUDGMENT]: the bank sets them, no rule prescribes them.
MATERIALITY_EL = 0.10
PSI_AMBER, PSI_RED = 0.10, 0.25
AUC_GREEN, AUC_RED = 0.65, 0.60
AIR_GREEN, AIR_RED = 0.90, 0.80
AE_AMBER, AE_RED = 1.10, 1.35


def load_inputs():
    dev = pd.read_csv(PROC / "development_segmented.csv")
    mon = pd.read_csv(PROC / "monitoring_segmented.csv")
    pd_old = pd.read_csv(PROD / "pd_curves_by_pool.csv")
    lgd = pd.read_csv(PROD / "lgd_by_pool.csv")
    ead = pd.read_csv(PROD / "ead_by_pool.csv")
    return dev, mon, pd_old, lgd, ead


# ---------------------------------------------------------------- PD engine
def life_table(sub, edges):
    rows = []
    mob, dflag = sub["months_on_book"].to_numpy(), sub["default_flag"].to_numpy()
    for start, end in zip(edges[:-1], edges[1:]):
        n_at_risk = int((mob >= start).sum())
        n_def = int(((dflag == 1) & (mob >= start) & (mob < end)).sum())
        hazard = n_def / n_at_risk if n_at_risk > 0 else np.nan
        rows.append({"bucket_start": start, "bucket_end": end, "n_at_risk": n_at_risk,
                     "n_default": n_def, "hazard": hazard})
    return pd.DataFrame(rows)


def tail_hazard(hz, min_exposure=MIN_EXPOSURE_TAIL):
    """Pooled hazard of the last buckets until credible exposure is reached."""
    valid = hz.dropna(subset=["hazard"])
    if valid.empty:
        return 0.0
    cum, nd, nr = 0, 0, 0
    for i in range(len(valid) - 1, -1, -1):
        r = valid.iloc[i]
        nd += r["n_default"]; nr += r["n_at_risk"]; cum += r["n_at_risk"]
        if cum >= min_exposure:
            break
    return nd / nr if nr > 0 else 0.0


def pd_curve(hz, term_months, min_exposure=MIN_EXPOSURE_TAIL):
    tail = tail_hazard(hz, min_exposure)
    surv, pd12 = 1.0, None
    for i in range(int(np.ceil(term_months / BUCKET))):
        h = hz.iloc[i]["hazard"] if i < len(hz) else tail
        h = tail if pd.isna(h) else h
        surv *= (1 - h)
        if (i + 1) * BUCKET >= 12 and pd12 is None:
            pd12 = 1 - surv
    return pd12, 1 - surv


def estimate_pd(data, term_by_segment, max_age=None, min_exposure=MIN_EXPOSURE_TAIL,
                monotone=True, col="PD_lifetime"):
    """Pool-level lifetime PD from loan-level data. Returns one row per pool."""
    max_age = int(data["months_on_book"].max()) if max_age is None else max_age
    edges = list(range(0, max_age + BUCKET, BUCKET))
    rows = []
    for pool_id, sub in data.groupby("pool_id", observed=True):
        seg = sub["segment"].iloc[0]
        p12, plife = pd_curve(life_table(sub, edges), term_by_segment[seg], min_exposure)
        rows.append({"pool_id": pool_id, "segment": seg, "n_loans_evidence": len(sub),
                     "raw_default_rate": sub["default_flag"].mean(),
                     "PD_12m": p12, "PD_lifetime_unconstrained": plife})
    out = pd.DataFrame(rows)
    out["fico_band"] = out["pool_id"].str.split(r" \| ").str[1]
    out["band_rank"] = out["fico_band"].map(BAND_RANK)
    out = out.sort_values(["segment", "band_rank"]).reset_index(drop=True)
    out[col] = out["PD_lifetime_unconstrained"]
    if monotone:
        for seg, idx in out.groupby("segment").groups.items():
            sub = out.loc[idx]
            iso = IsotonicRegression(increasing=False, out_of_bounds="clip")
            out.loc[idx, col] = iso.fit_transform(sub["band_rank"], sub["PD_lifetime_unconstrained"],
                                                  sample_weight=sub["n_loans_evidence"])
    return out


# ---------------------------------------------------------------- EL engine
def el_table(pd_table, pd_col, lgd, ead, dev):
    avg_amt = dev.groupby("pool_id", observed=True)["funded_amount"].mean().rename("avg_funded")
    n = dev.groupby("pool_id", observed=True).size().rename("n_loans")
    m = (pd_table[["pool_id", "segment", pd_col]]
         .merge(lgd[["pool_id", "LGD_expected_CECL", "LGD_downturn_stress"]], on="pool_id")
         .merge(ead[["pool_id", "EAD_pct_of_committed"]], on="pool_id")
         .merge(avg_amt, on="pool_id").merge(n, on="pool_id"))
    m["EAD_dollars"] = m["EAD_pct_of_committed"] * m["avg_funded"]
    m["exposure_funded"] = m["avg_funded"] * m["n_loans"]
    m["EL"] = m[pd_col] * m["LGD_expected_CECL"] * m["EAD_dollars"] * m["n_loans"]
    m["EL_downturn"] = m[pd_col] * m["LGD_downturn_stress"] * m["EAD_dollars"] * m["n_loans"]
    return m


# ---------------------------------------------------------------- monitoring metrics
def psi(expected, actual, bins=None, categorical=False, eps=1e-6):
    if categorical:
        cats = sorted(set(expected.dropna().unique()) | set(actual.dropna().unique()))
        e = expected.value_counts(normalize=True).reindex(cats).fillna(0) + eps
        a = actual.value_counts(normalize=True).reindex(cats).fillna(0) + eps
    else:
        edges = np.unique(np.quantile(expected.dropna(), np.linspace(0, 1, (bins or 10) + 1)))
        edges[0], edges[-1] = -np.inf, np.inf
        e = pd.Series(np.histogram(expected.dropna(), edges)[0]) / expected.notna().sum() + eps
        a = pd.Series(np.histogram(actual.dropna(), edges)[0]) / actual.notna().sum() + eps
    return float(((a - e) * np.log(a / e)).sum())


def discrimination(y, score):
    auc = roc_auc_score(y, score)
    fpr, tpr, _ = roc_curve(y, score)
    return auc, 2 * auc - 1, float(np.max(tpr - fpr))


def rag(value, amber, red, higher_is_worse=True):
    if higher_is_worse:
        return "RED" if value > red else ("AMBER" if value >= amber else "GREEN")
    return "RED" if value < red else ("AMBER" if value < amber else "GREEN")


# ---------------------------------------------------------------- fair lending proxy
def air_by_group(pooled_dev, pd_series, seed=999, within_segment=False):
    """Adverse Impact Ratio on a synthetic BISG-style proxy.

    The proxy is synthetic and built only to exercise the test. Approve = lifetime
    PD at or below the portfolio median (or the product median if within_segment); AIR = approval(protected) / approval(reference).
    """
    rng = np.random.default_rng(seed)
    z = (700 - pooled_dev["fico_origination"].to_numpy()) / 55
    p = 1 / (1 + np.exp(-(-0.40 + 0.35 * z + rng.normal(0, 1, len(z)))))
    protected = rng.random(len(z)) < p
    pdv = pd_series.to_numpy()
    seg = pooled_dev["segment"].to_numpy()
    if within_segment:   # cut-off = median PD inside each product (avoids a product-mix artifact)
        approved = np.zeros(len(pdv), dtype=bool)
        for sg in np.unique(seg):
            m = seg == sg; approved[m] = pdv[m] <= np.median(pdv[m])
    else:                # one portfolio-wide cut-off
        approved = pdv <= np.median(pdv)
    df = pd.DataFrame({"segment": seg, "protected": protected, "approved": approved})
    def air(d):
        ap, ar = d.loc[d.protected, "approved"].mean(), d.loc[~d.protected, "approved"].mean()
        return ap / ar
    out = {"all": air(df)}
    out.update({s: air(g) for s, g in df.groupby("segment")})
    return out


# ---------------------------------------------------------------- horizon-matched A/E
def _cum_pd(hazards, m):
    """Cumulative PD at m months on book from 3-month hazards (linear in cumulative hazard inside a bucket)."""
    ch = 0.0
    for i, hz in enumerate(hazards):
        lo = i * BUCKET
        if m >= lo + BUCKET:
            ch += -np.log(1 - hz)
        else:
            ch += -np.log(1 - hz) * max(0.0, m - lo) / BUCKET
            break
    return 1 - np.exp(-ch)


def horizon_matched_ae(dev, mon):
    """Model-based A/E: expected defaults of each monitoring loan = production cumulative PD up to its months on book.

    Unlike the raw rate ratio this respects that monitoring loans are younger than development loans.
    """
    edges = list(range(0, int(dev["months_on_book"].max()) + BUCKET, BUCKET))
    rows = []
    for pid, d in dev.groupby("pool_id", observed=True):
        lt = life_table(d, edges); tail = tail_hazard(lt); h = lt["hazard"].fillna(tail).to_numpy()
        mm = mon[mon["pool_id"] == pid]
        exp = float(sum(_cum_pd(h, x) for x in mm["months_on_book"])); obs = int(mm["default_flag"].sum())
        rows.append({"pool_id": pid, "observed_defaults": obs, "expected_defaults": exp, "AE_horizon_matched": obs / exp})
    return pd.DataFrame(rows)
