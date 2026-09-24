# Experiment and regression commands

Every experiment is launched by a named command. Each invocation writes an immutable JSON summary to `tests/results/`, a complete execution log to `tests/logs/`, and heavy generated artifacts below `tests/results/artifacts/`.

New reruns also write `article_outputs/run_statistics/run-metrics-long.csv` and
`run-statistics.json` from **individual final solutions**, never from source
days or meals treated as independent runs. A one-run smoke test intentionally
has no standard deviation or confidence interval. LP has one deterministic
observation per profile and no sampling interval. No cross-method significance
test is reported while the formulations remain non-equivalent.

Both `ga-smoke` and `full-replication` run a post-execution candidate-scope
audit across GA-Food, GA-Meal, LP-Food, and LP-Meal. GA artifacts record their
input profile and exact candidate-food inventory; the audit checks selected
foods against that profile's staged base diets and writes
`article_outputs/profile-scope-validation.json`.

New GA/LP reruns default to `configs/revised-nutrition-protocol.json`; use
`--nutrition-protocol historical` only to reproduce the prior implemented
bounds. Each rerun stores `effective-nutrition-constraints.json`, its digest,
and `nutrition-field-coverage.json`. Reruns remain diagnostic until the
non-identity food mappings and missing nutrient values are adjudicated.

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

Create a ranked, non-accepting TBCA review queue for the 170 non-identity links:

```bash
python -m tests.run_experiments --experiments mapping-review-queue
```

Summarize positive food quantities by profile and meal for a bounded-quantity
sensitivity design (not clinical serving guidance):

```bash
python -m tests.run_experiments --experiments portion-support-audit
```

Create a lexical review queue for vegetarian/vegan source-food names. It flags
possible animal-derived terms but does not validate or filter foods:

```bash
python -m tests.run_experiments --experiments profile-ingredient-audit
```

One-run GA/LP smoke replication:

```bash
python -m tests.run_experiments --experiments ga-smoke --seed 20260323
```

Audit the corrected LP-Food candidate set for all three profiles without GA:

```bash
python -m tests.run_experiments --experiments lp-profile-scope
```

Inspect all four methods' candidate and output scope in an existing rerun
workspace:

```bash
python -m tests.validate_candidate_scope --workspace tests/results/artifacts/<run-id>
```

This command verifies that each selected food occurs in one of the 50 prepared
base diets of its own profile. Preparation removes only two exact, documented
vegan contradictions (five item occurrences), preserving the original files
and recording every removal. The remaining source foods still need complete
ingredient-level review before claiming vegan compliance.

New full replication:

```bash
python -m tests.run_experiments --experiments full-replication --runs 10 --seed 20260323
```

The smoke and full commands create new stochastic results. They do not recreate the unrecorded random streams used in March 2026.

Each new GA run writes `data/outputs/optimization_runs/ag-*/runs/<diet>/execution-<n>.json`
inside its result workspace. This file contains the effective configuration, seed,
fitness trajectory, stop reason, duration, final solution, daily and mean nutrient
and footprint metrics, and violations of the selected protocol's bounds.
LP produces one `data/outputs/optimization_runs/pl-*/execution-<profile>.json`
per profile with solver status, fallback details, final solution, and diagnostics.
The workspace `run-manifest.json` captures the current OS, CPU, physical RAM,
Python/dependency versions, and SciPy/HiGHS backend. Archived mode describes
the machine doing the reconstruction, not the unknown original machine.

The base-diet audit writes item-, plan-, nutrient-, and summary-level evidence. It does not infer missing raw API responses, failures, or regeneration counts.
