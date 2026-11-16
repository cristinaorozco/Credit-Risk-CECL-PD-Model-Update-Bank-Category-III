# Data decisions log

Decisions taken on the raw extracts **before** modelling, with counts (development / monitoring) and whether each one can move the PD. The raw values stay in `data/processed` (`*_raw` columns) and every treatment has a flag column. Row counts: 20,000 in and out (development), 10,000 in and out (monitoring).

| ID | Issue | Count (dev / mon) | Decision | Can it move the PD? |
|---|---|---|---|---|
| DD-01 | FICO at origination = 999 (invalid sentinel) | 20 / 10 | Flag; assign the segment median FICO (all land in the prime band) so the loan stays in a pool | **Yes** (band assignment). Small: 30 loans of 30,000 |
| DD-02 | Negative DTI (invalid) | 20 / 10 | Set to missing, flag, impute | No: DTI is not a model input |
| DD-03 | DTI missing | 399 / 200 | Impute, flag (`dti_ratio_imputed_flag`; 419 / 210 with the invalid values) | No |
| DD-04 | Annual income missing | 800 / 400 | Impute, flag | No |
| DD-05 | Refreshed FICO missing | 600 / 300 | Fall back to origination FICO, `fico_current_source` says so; never used as a predictor | No |
| DD-06 | Employment length as free text or blank | blank 600 / 300 | Parse to years; unknown flagged | No |
| DD-07 | Utilization empty on term loans | not applicable | Keep empty and set `utilization_applicable_flag` = 0; **never fill with zero** | No |
| DD-08 | Card utilization above 1.0 (over limit) | 577 / 269 | Keep as observed (a real over-limit balance), flag | No |
| DD-09 | `delinquency_bucket_current` is measured at the observation date, which for defaulted loans is **after** the default | all defaults: 1,464 / 913 | Not used as a predictor (it would leak the outcome) | No (excluded) |
| DD-10 | Card terms are 12, 24 and 36 months in the data (about two thirds below 36); the production model uses a 36-month horizon for all cards | 3,963 / 1,888 | Keep the production horizon so v1 and v2 are comparable; flag | **Yes** (card lifetime PD). Direction not tested; open question for the data owner |
| DD-11 | `state` and `zip_code` | all rows | Removed from the model data (kept separately for fair-lending review); never a model input | No |
| DD-12 | Duplicate `loan_id` | 0 | None found | No |

## How the decisions were checked
* The cleaned development data **reproduce the production PD and LGD tables** and the development AUC/Gini/KS from the documented method (re-estimating on development data alone returns a 0.00% change in expected loss, see `outputs/tables/03_alternatives_sensitivity.csv`).
* DD-01 is the only FICO-999 treatment that keeps the production tables and the bank's backtesting exactly reproducible.

## Open questions for the data owner
1. Default definition (the target was used as delivered).
2. Meaning of the card term in the data against the 36-month model horizon (DD-10).
3. Snapshot dates (months on book equal min(age, term) for every non-defaulted loan, so they are inferred).
4. Cancelability of card and HELOC lines.
5. Pre-default drawn balances: `credit_limit` equals `funded_amount` for every revolving loan, so a CCF review cannot be done reliably.
