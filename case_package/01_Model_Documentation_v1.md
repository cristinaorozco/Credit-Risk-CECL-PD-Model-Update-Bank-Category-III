# CECL Lifetime PD Model v1: model summary (from the model inventory)

**Owner:** Consumer Credit Modeling · **In production since:** development sample Jan 2022 to Jun 2023 · **Use:** allowance for credit losses (CECL), consumer portfolio.

## Portfolio and pools
Four products: credit card (36 months), auto loan (60), personal loan (36), HELOC (120, revolving). Four FICO-at-origination bands per product: subprime (<640), near-prime (640-679), prime (680-719), super-prime (720+). 16 pools in total.

## Method (as developed)
1. Life table by pool in 3-month age buckets: hazard = defaults ÷ loans at risk.
2. Beyond observed ages, a tail hazard equal to the pooled hazard of the last buckets until at least 300 loans of exposure.
3. Lifetime PD over the contractual term = 1 − Π(1 − hazard).
4. Monotonicity across FICO bands within each product (isotonic regression weighted by pool size).
5. Expected loss per pool = PD lifetime × LGD × EAD$ × number of loans. LGD and EAD come from separate tables (files in this folder). Reference EAD$ uses the average funded amount of the development sample.

## Parameters in production
`data/production_model/` (PD, LGD, EAD by pool). The code that produced them is not part of the case file.

## Known limitations recorded at approval
Single development window (18 months of originations); tail hazard extrapolated for long-dated products; macro variables are inputs to the forecast process, not to this model.
