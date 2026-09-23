# Experiment and regression commands

Every experiment is launched by a named command. Each invocation writes an immutable JSON summary to `tests/results/`, a complete execution log to `tests/logs/`, and heavy generated artifacts below `tests/results/artifacts/`.

Fast deterministic regression tests:

```bash
python -m unittest discover -s tests -v
```

Exact reconstruction of the submitted artifacts:

```bash
python -m tests.run_experiments --experiments archived-reconstruction
```

Audit of all 150 normalized base diets:

```bash
python -m tests.run_experiments --experiments base-diet-audit
```

One-run GA/LP smoke replication:

```bash
python -m tests.run_experiments --experiments ga-smoke --seed 20260323
```

New full replication:

```bash
python -m tests.run_experiments --experiments full-replication --runs 10 --seed 20260323
```

The smoke and full commands create new stochastic results. They do not recreate the unrecorded random streams used in March 2026.

The base-diet audit writes item-, plan-, nutrient-, and summary-level evidence. It does not infer missing raw API responses, failures, or regeneration counts.
