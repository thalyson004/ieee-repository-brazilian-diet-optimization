# Profile ingredient eligibility review

This lexical screen inventories every distinct food name in the vegetarian and vegan source plans, with occurrence and plan counts. A Portuguese keyword set flags likely animal-derived wording, but it cannot inspect undisclosed recipe ingredients and may produce false positives (for example, *couve-manteiga*). It therefore never removes foods, validates a profile, or changes the staged optimizer pool.

Run and log the screen with:

```bash
python -m tests.run_experiments --experiments profile-ingredient-audit
```

The 364 profile-food rows are preserved in `archive/audits/profile-ingredient-review-queue.csv` and `.json`. Three vegan names trigger lexical review, including the documented beef-containing bean dish and chocolate-flavored cow milk, plus the ambiguous *couve-manteiga* name. Every row remains pending manual ingredient verification; absence of a keyword is not proof of vegan/vegetarian eligibility.
