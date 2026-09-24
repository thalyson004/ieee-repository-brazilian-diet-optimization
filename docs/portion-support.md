# Empirical food-by-meal quantity support

The 150 preserved base plans were summarized separately by dietary profile, food name, and meal slot. The audit reports positive occurrence counts, the number of distinct source plans, observed minimum/maximum quantities, and 5th/95th percentiles only when at least 20 positive observations are available. A row with fewer than five positive observations is marked as weak support.

Generate the versioned result and log with:

```bash
python -m tests.run_experiments --experiments portion-support-audit
```

The 1,033 profile-food-meal rows are also preserved in `archive/audits/food-meal-quantity-support.csv` and `.json`; 376 rows have fewer than five observations and 199 meet the percentile threshold. These empirical values describe the generated corpus only. They are not dietary recommendations or validated serving sizes. They are an input for a bounded-quantity sensitivity scenario; they do not yet impose those bounds in any optimizer.
