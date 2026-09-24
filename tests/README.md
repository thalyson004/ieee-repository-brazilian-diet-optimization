# Experiment and regression commands

Every experiment is launched by a named command. Each invocation writes an immutable JSON summary to `tests/results/`, a complete execution log to `tests/logs/`, and heavy generated artifacts below `tests/results/artifacts/`.

Earlier mapping-review checkpoint (2026-09-24): 49 nutrition-target decisions were indexed and the active-map queue had 121 unresolved links. This historical snapshot does not adjudicate ingredient formulation, preparation, or environmental equivalence.

Latest audit refresh (2026-09-24): 151 target decisions are indexed and the active queue has 19 unresolved links. The latest audit is `base-diet-audit_20260924T201700269011Z_a24d8d01`; the queue refresh is `mapping-review-queue-current_20260924T201700618482Z_77923935`. The 31-test suite passed. A later `nutrient-missingness-audit_20260924T202515873539Z_100f3faf` adds strict complete-case meal support: mandatory breakfast/lunch pools have zero eligible meals in the regular and vegan profiles, so that filter cannot support a full meal-based comparison. These diagnostics did not change nutrient/environmental codes or optimizer outputs. Remaining blockers include source recipe/ingredient uncertainty, walnut species, oil/preparation differences, missingness, and environmental pairings; every rerun remains diagnostic.

Latest ten-seed rerun after adding provenance tracking: `full-replication_20260924T191513576820Z_55610f6d`, 66 outputs (60 GA + 6 LP), seed-base 20260929, 369.1 s, `status=passed`; scope validation passed with no items outside profile pools. Its manifest records clean source commit `1804a2dde338be0c6e5136fdd8ac4c1dc8c21478` and SHA-256 for the protocol, exclusions, source diets, and nutrition/environment maps. It remains diagnostic; no result is approved for the manuscript. The preceding seed-20260928 run and complete nine-command battery also passed; see `EXPERIMENT-EXECUTION-PLAN.md` for blockers.

The profile-ingredient audit is a lexical screen, not a vegan/vegetarian certificate. It recognizes `couve-manteiga` as a vegetable variety, flags the ambiguous vegetarian item `Omelete, frios` for manual review, and distinguishes a coconut-milk label from explicit cow/condensed milk. Only the two exact configured vegan contradictions are excluded from derived optimizer inputs; the other 362 profile-food rows remain pending ingredient verification.

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

Quantify missing nutrient fields by profile and measure how a strict
complete-case food pool would reduce observed foods, occurrences, and grams.
The strict scenario is an attrition sensitivity only; it does not choose a
primary missing-data policy or treat missing values as true zero:

```bash
python -m tests.run_experiments --experiments nutrient-missingness-audit
```

Create a ranked, non-accepting TBCA review queue for the 170 non-identity links:

```bash
python -m tests.run_experiments --experiments mapping-review-queue
```

Create a separate queue from active maps, excluding foods with a dated target
decision. Its current count is recorded in `EXPERIMENT-EXECUTION-PLAN.md`;
rows are ranked by occurrence, and the name-similarity suggestions are not
equivalence evidence and are never applied automatically:

```bash
python -m tests.run_experiments --experiments mapping-review-queue-current
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

Compare LP slack penalties (100, 1,000, 10,000, and 100,000) for both LP
formulations and all three profiles. Each row exports labeled constraint slacks
and metrics for the constructed plan:

```bash
python -m tests.run_experiments --experiments lp-slack-sensitivity
```

This is a diagnostic sensitivity, not a policy recommendation: the same penalty
coefficient multiplies slacks with different physical units, so those units and
the resulting violations must be interpreted separately.

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

The registered GA sensitivity command is `python -m tests.run_experiments --experiments ga-hyperparameter-sensitivity --runs 10 --seed 20260931 --nutrition-protocol revised`. It pairs execution IDs under one base seed for baseline, reduced population, higher mutation, and shorter stagnation. Each nested manifest records the effective override payload and hash. The post-run review command is `python -m tests.ga_sensitivity_review --source-run-id 20260924T193117251885Z_3da6e240`; it validates profile scope and writes paired differences with bootstrap intervals. The 1-run version is smoke validation only, not a sensitivity estimate.
