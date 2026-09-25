# Profile ingredient eligibility review

This lexical screen inventories every distinct food name in the vegetarian and vegan source plans, with occurrence and plan counts. A Portuguese keyword set flags likely animal-derived wording, but it cannot inspect undisclosed recipe ingredients and may produce false positives (for example, *couve-manteiga*). It therefore never removes foods, validates a profile, or changes the staged optimizer pool.

Run and log the screen with:

```bash
python -m tests.run_experiments --experiments profile-ingredient-audit
```

The latest generated queue contains 364 profile-food rows. Of these, 359 remain pending ingredient verification, two exact vegan contradictions are excluded from derived optimizer inputs, and three rows carry target-specific evidence: `Feijoada vegetariana` for BRC0172T and the arugula/sun-dried-tomato salad for BRC0404B in both vegetarian and vegan profiles. This evidence does not verify every generated recipe or prompt provenance. Three vegan names trigger lexical review, including the documented beef-containing bean dish and chocolate-flavored cow milk, plus the ambiguous *couve-manteiga* name. Absence of a keyword is not proof of vegan/vegetarian eligibility.
