# Data dictionary: synthetic consumer portfolio (Category III bank scenario)

**All data in this repository is synthetic.** It does not describe any real bank, borrower or portfolio.

## Files

| File | Origination period | Rows | Use |
|---|---|---|---|
| `raw/development_raw.csv` | Jan 2022 to Jun 2023 | 20,000 | Development: calibrate PD, LGD and EAD. Its variable distributions are the benchmark for PSI. |
| `raw/monitoring_raw.csv` | Jul 2023 to Jun 2024 | 10,000 | Monitoring (out of time): PSI, Gini/KS recomputed on realized outcomes, actual vs expected defaults. |

Both files share the same 28 columns. They are **raw on purpose**: they contain the data quality problems a real extract would have, so that a cleaning step can be exercised and audited.

Portfolio mix (development): credit card 5,985; auto loan 5,969; personal loan 5,045; HELOC 3,001. Total funded amount: about $430.6 million. Observed default rate: 7.32% (development) and 9.13% (monitoring).

## Columns

| Column | Type | Description | Note |
|---|---|---|---|
| `loan_id` | string | Unique loan identifier | |
| `segment` | category | `auto_loan`, `personal_loan`, `credit_card`, `heloc` | Basis of the CECL pooling (ASC 326-20-30-2, 55-5) |
| `origination_date` | date | Origination date | Anchor for vintage analysis |
| `funded_amount` | number | Amount funded | |
| `term_months` | number | Contractual term | |
| `interest_rate` | number | Interest rate (percent) | |
| `fico_origination` | number | FICO at origination | 20 values equal 999 (invalid, outside 300 to 850) |
| `fico_current` | number | Refreshed FICO | About 3% missing |
| `dti_ratio` | number | Debt to income, in percent | About 2% missing; 20 negative values (invalid) |
| `annual_income` | number | Self-reported annual income | About 4% missing |
| `home_ownership` | category | RENT / OWN / MORTGAGE | |
| `verification_status` | category | Verified / Source Verified / Not Verified | |
| `purpose` | category | `car`, `credit_card`, `debt_consolidation`, `home_improvement` | |
| `state` | category | US state (2 letters, 25 distinct) | Fair lending review variable: possible geographic proxy for protected classes. Not a model input. |
| `zip_code` | string | ZIP code | Same risk as `state`, higher granularity. Not a model input. |
| `utilization_ratio` | number | Utilization, as a fraction | Applies only to `credit_card` and `heloc` (revolving). Empty for term loans (not applicable, not zero). A real 0 on a revolving line is different from not applicable. |
| `delinquency_bucket_current` | category | Days past due: 0, 30, 60, 90 | Measured at the observation date, **including after default** for defaulted loans (see limitations) |
| `months_on_book` | number | Account age at the observation date | Maximum 35 (development) and 29 (monitoring) |
| `unemployment_rate_regional` | number | Regional unemployment rate (percent) | Macro input for the reasonable and supportable forecast |
| `hpi_change_regional_pct` | number | Regional house price index change (percent) | Collateral value channel (HELOC, auto) |
| `default_flag` | binary | 1 = default observed | Dependent variable for PD |
| `months_to_default` | number | Months from origination to default | Only when `default_flag = 1` |
| `exposure_at_default` | number | Exposure at default | Only when `default_flag = 1` |
| `recovery_amount` | number | Amount recovered | Only when `default_flag = 1`; input to LGD |
| `credit_limit` | number | Credit line | Populated for `credit_card` and `heloc`; empty for term loans. In this synthetic data it equals `funded_amount` for every revolving loan. |
| `ccf_realized` | number | Realized credit conversion factor | Only for defaulted `credit_card` and `heloc` |
| `ead_ratio_realized` | number | Realized EAD as a share of funded amount | Only for defaulted amortizing loans |
| `emp_length_raw` | string | Employment length as inconsistent text | About 3% missing; needs parsing |

## Built-in features of the data

1. **No protected-class variables.** Fair lending is tested with a synthetic proxy (BISG-style) kept in a separate reference file. In a real bank that proxy is built by compliance and is never a model input.
2. **Intentional drift** between periods: regional unemployment rises (about 3.8% to 4.6%) and house price growth falls (about 4.0% to 1.0%), so the default rate goes from 7.32% to 9.13%. Monitoring should detect it.
3. **HELOC is revolving.** It has utilization, a credit line and a realized CCF. A model that treats it as an amortizing loan is wrong for this portfolio.
4. **The CCF in the data is a synthetic assumption** (about 0.45 for HELOC and 0.30 for credit cards as design values). It is illustrative, not a benchmark.

---

# Project files added for the Model Update case

## `processed/` (cleaned and segmented loan-level data)
`development_segmented.csv` (20,000 rows) and `monitoring_segmented.csv` (10,000 rows). Same loans as the raw files, after cleaning and pool assignment. `state` and `zip_code` are **removed** (not model inputs).

| New or changed column | Description |
|---|---|
| `fico_origination`, `dti_ratio`, `annual_income` | Cleaned values (invalid set to missing, then imputed) |
| `*_raw` | Value before cleaning, kept for audit |
| `fico_origination_flag_invalid`, `dti_ratio_flag_invalid` | 1 = raw value invalid (FICO outside 300 to 850; negative DTI) |
| `annual_income_imputed_flag`, `dti_ratio_imputed_flag`, `fico_origination_imputed_flag` | 1 = value was imputed |
| `fico_current_source` | `refreshed`, `fallback_origination`, or `fallback_origination_imputed` |
| `emp_length_years`, `emp_length_unknown_flag` | Parsed employment length; 1 = unknown |
| `utilization_applicable_flag` | 1 for revolving products; 0 means utilization is **not applicable** (empty), not zero |
| `fico_band` | `subprime(<640)`, `near-prime(640-679)`, `prime(680-719)`, `super-prime(720+)` |
| `pool_id` | `segment \| fico_band` (16 pools) |
| `vintage_half` | Origination half-year, e.g. `2023H2` |

## `production_model/` (the model in production before the update)
| File | Content |
|---|---|
| `pd_curves_by_pool.csv` | Production lifetime and 12-month PD by pool (`PD_lifetime_CECL` is after the monotonicity step; `PD_lifetime_unconstrained` before it) |
| `lgd_by_pool.csv` | Expected-CECL LGD and downturn LGD by pool |
| `ead_by_pool.csv` | EAD as a share of the committed amount, by pool |

## Outputs
Everything under `outputs/` and `reports/` is generated by the scripts and can be regenerated.
