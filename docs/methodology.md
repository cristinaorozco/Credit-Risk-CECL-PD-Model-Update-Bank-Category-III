# Methodology

Implemented in `src/mu_catiii.py`; steps in `scripts/` and `notebooks/`.

## Pool PD (lifetime)
1. **Life table.** Age buckets of 3 months. For each pool and bucket: *at risk* = loans with age ≥ bucket start; *defaults* = defaults with age inside the bucket; *hazard* = defaults ÷ at risk.
2. **Tail hazard.** Loans are observed up to 35 months but products run up to 120. Beyond the observed range (or where a bucket is empty) use the pooled hazard of the last buckets, taking buckets from the end until cumulative exposure reaches 300 loans.
3. **Lifetime PD.** `1 − Π(1 − hazard_i)` over the buckets in the contractual term. **PD 12m** is read at the 12-month mark.
4. **Monotonicity.** Within a segment, isotonic regression (non-increasing in FICO band, weighted by pool size) so that a better band never has a higher PD.

## Expected Loss
`EL_pool = PD_lifetime × LGD_expected × EAD_pct × avg_funded × n_loans`, summed across pools. LGD and EAD tables are the production tables.

## Model Update logic
* **Production** = estimator on development data (reproduced exactly: re-estimating on development alone gives a 0.00% EL change).
* **Update** = the same estimator on development + monitoring (30,000 loans).
* **Materiality** = change in total EL vs the 10% internal threshold.

## Monitoring metrics
* **PSI**: development as benchmark; deciles for continuous variables, categories otherwise.
* **AUC/Gini/KS** on monitoring outcomes, with production lifetime PD as the score.
* **A/E** = monitoring default rate ÷ development default rate by pool; exact binomial 95% interval; Bonferroni across 16 pools; chi-square homogeneity test for a single common shift.

## Validation
* **Holdout:** 20% of pooled loans, stratified by pool, split **before** fitting (seed 7); re-estimate on 80%; AUC/Gini/KS on the 20%; A/E = raw rate vs raw rate (never raw rate vs lifetime PD).
* **Bootstrap (200 reps, seed 2026):** *paired* (development and monitoring resampled separately; old = estimator on the development resample; new = estimator on the pooled resample) tests whether the change is real; *unpaired* (production fixed) measures the uncertainty of the new level.
* **Sensitivity:** tail exposure 150/600, no monotonicity, monitoring-only, development-only, scalar, pool-specific scalar.

## Scope test
Realized LGD = 1 − recovery ÷ EAD on defaulted loans; realized CCF (revolving) and EAD ratio (amortizing). Welch t-tests between periods; HELOC LGD examined by vintage; EL scenario with HELOC LGD scaled to the monitoring level.

## Fair lending
Synthetic proxy ~ Bernoulli(sigmoid(−0.40 + 0.35·z + ε)), z = (700 − FICO)/55, ε ~ N(0,1), seed 999. Approve if PD ≤ portfolio median. AIR = approval rate of the proxy group ÷ approval rate of the rest.
