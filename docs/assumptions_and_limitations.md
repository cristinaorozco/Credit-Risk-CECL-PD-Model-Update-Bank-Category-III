# Assumptions and limitations

## Assumptions (each one changes a number if it is wrong)
1. **All data are synthetic**, including the portfolio, outcomes and macro series. The fair-lending proxy is synthetic too.
2. **Data cleaning:** invalid FICO (999) and negative DTI were set to missing and imputed; missing income, DTI and refreshed FICO were imputed or fell back to origination values. Every treatment is flagged in `data/processed` (raw columns are preserved). The imputation method is a documented assumption.
3. **Default is binary and observed within the extract.** Defaulted loans carry `months_on_book` = months to default; performing loans carry age at observation.
4. **Expected Loss** = PD × LGD × EAD$ × number of loans, using development average funded amount per pool. It is a reference calculation, not the allowance itself (no forecast overlay, no qualitative adjustment, no discounting).
5. **EAD$ per pool** = development EAD percentage × average funded amount. For revolving products the CCF (about 0.45 HELOC, 0.30 card) is a synthetic design value, not a benchmark.
6. **LGD and EAD are held at development values** in the headline result (scope). Their effect is quantified separately.
7. **Materiality threshold 10%, tail credibility 300, PSI/AUC/AIR/A-E bands** are internal judgements.
8. **A/E uses raw default rates** (monitoring over development) as the bank's pack does. That ignores that monitoring loans are younger; a horizon-matched, model-based A/E (expected = production cumulative PD to each loan's months on book) gives about 1.55 against 1.25. The horizon-matched version is the better measure of deterioration and is used in the discussion of forecast risk.

## Limitations
* **One monitoring period, one regime.** Twelve months of a rising-unemployment, falling-house-price environment. The pooled estimate cannot tell whether it persists.
* **Out-of-sample, not out-of-time** validation. The holdout is a random split of pooled loans from both periods. Its A/E sampling range is about 0.92 to 1.08, so it cannot detect small biases.
* **Level uncertainty is large for long-dated products.** Lifetime PD for HELOC (120 months) and auto (60) is mostly extrapolated from a tail hazard. The unpaired bootstrap interval for the new EL is about −8% to +19%. The *change* is much better determined (paired interval about +1.7% to +8.9%).
* **Pool-level A/E is noisy.** Only 2 of 16 pools are significant after correction.
* **HELOC LGD finding** rests on 137 monitoring defaults, and monitoring loans have had less time for recoveries; no way to rule out a maturity artifact entirely with this data, though other products show no such drift.
* **Bootstrap** resamples loans independently within pool. It ignores correlation by vintage or region, so intervals are, if anything, too narrow.
* **AIR** uses a simple approval rule (PD at or below the median) and a synthetic proxy; it illustrates the test and is not a fair-lending examination.
* **Data items that cannot be tested with this package:** the default definition, pre-default drawn balances (CCF), cancelability of revolving lines and the cumulative effect of earlier updates. See `docs/data_decisions_log.md`.
* **Card horizon.** All cards use the production 36-month horizon although about two thirds of card loans have 12- or 24-month terms; the direction of the effect is not tested.
* **Not a validation.** The author built the update; independent validation is a condition of the change.
* **No code-level production controls** (change tickets, versioning of the PD table in a model inventory, access control) are modelled.

## Things deliberately not done
* No new model form (the monitoring says ranking is intact).
* No pool-specific adjustment (it fits noise).
* No change to pools, default definition or segmentation.
* No attempt to forecast the macro environment; that belongs to the allowance process.
