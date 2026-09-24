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

Audit the corrected LP-Food candidate set for all three profiles without GA:

```bash
python -m tests.run_experiments --experiments lp-profile-scope
```

This command verifies that each selected food occurs in one of the 50 prepared
base diets of its own profile. Preparation removes only two exact, documented
vegan contradictions (five item occurrences), preserving the original files
and recording every removal. It uses historical numerical targets and is not
the revised article's final experiment. The remaining source foods still need
complete ingredient-level review before claiming vegan compliance.

New full replication:

```bash
python -m tests.run_experiments --experiments full-replication --runs 10 --seed 20260323
```

The smoke and full commands create new stochastic results. They do not recreate the unrecorded random streams used in March 2026.

Each new GA run writes `data/outputs/optimization_runs/ag-*/runs/<diet>/execution-<n>.json`
inside its result workspace. This file contains the effective configuration, seed,
fitness trajectory, stop reason, duration, final solution, daily and mean nutrient
and footprint metrics, and violations of the *historically implemented* bounds.
LP produces one `data/outputs/optimization_runs/pl-*/execution-<profile>.json`
per profile with solver status, fallback details, final solution, and diagnostics.
The workspace `run-manifest.json` captures the current OS, CPU, physical RAM,
Python/dependency versions, and SciPy/HiGHS backend. Archived mode describes
the machine doing the reconstruction, not the unknown original machine.

The base-diet audit writes item-, plan-, nutrient-, and summary-level evidence. It does not infer missing raw API responses, failures, or regeneration counts.
