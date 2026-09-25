# Experiment and regression commands

Every experiment is launched by a named command. Each invocation writes an immutable JSON summary to `tests/results/`, a complete execution log to `tests/logs/`, and heavy generated artifacts below `tests/results/artifacts/`.

Latest adjudication and sensitivity checkpoint (2026-09-25): official TBCA recipe evidence for `Feijoada vegetariana` (BRC0172T) supports only that standardized plant-based preparation, not the generated recipe or prompt provenance. The active ledger has 152 target decisions and 18 unresolved links (407 source occurrences before overlap with profile exclusions). Audits `base-diet-audit_20260925T003658202271Z_79a526ba` and `mapping-review-queue-current_20260925T003658596443Z_02f08ffd` confirm the current state. The lexical profile audit has 361 rows pending ingredient verification, one target-specific recipe-evidence row, and two configured exclusions. Sensitivity `food-mapping-exclusion-sensitivity_20260925T003703554510Z_a73bc617` and review `food-mapping-exclusion-review_20260925T005049261312Z_3945010c` passed at source commit `6b223451106da53978c5514bab469f886c1cdbe5`: 66 outputs per variant, 24 outcome and 24 computational paired contrasts; 5 outcome intervals and 5 computational intervals exclude zero before multiplicity adjustment. Exclusion removes incrementally 40 regular, 197 vegetarian, and 166 vegan occurrences (403); four further occurrences were already removed by profile rules. These remain diagnostics, not manuscript results.

Earlier mapping-review checkpoint (2026-09-24): 49 nutrition-target decisions were indexed and the active-map queue had 121 unresolved links. This historical snapshot does not adjudicate ingredient formulation, preparation, or environmental equivalence.

Latest audit refresh (2026-09-24): 151 target decisions are indexed and the active queue has 19 unresolved links. The latest audit is `base-diet-audit_20260924T201700269011Z_a24d8d01`; the queue refresh is `mapping-review-queue-current_20260924T201700618482Z_77923935`. The strict complete-case meal audit `nutrient-missingness-audit_20260924T202515873539Z_100f3faf` found no eligible mandatory breakfast/lunch candidates for regular and vegan profiles, so the filter cannot support a full meal-based comparison. The current deterministic suite has 38 tests. These diagnostics did not change nutrient/environmental mappings. Remaining blockers include source recipe/ingredient uncertainty, walnut species, oil/preparation differences, missingness, and POF-row environmental ambiguity; every rerun remains diagnostic.

LP-Food daily-quantity sensitivity (2026-09-24): `lp-daily-quantity-support-sensitivity_20260924T203346068167Z_7d3828fd` ran nine profile/scenario combinations. The caps are derived from positive per-food daily totals in the same profile's source diets: observed maximum and the 95th percentile when at least 20 positive days are available (otherwise an explicitly labeled observed-maximum fallback). This is a corpus-support sensitivity, not clinical serving advice; it does not add meal structure or establish an accepted primary cap. All nine scenarios returned a solution and selected quantities respected their caps. The two constrained vegan scenarios used LP relaxation, with vitamin D and B12 minimum shortfalls; those outputs remain diagnostic and are not manuscript results.

LP-Food diversity-floor sensitivity (2026-09-24): `lp-food-diversity-sensitivity_20260924T204207602863Z_2fbe7e88` ran nine LP/MILP scenarios using each profile's per-food observed-maximum daily caps and q25/median lower order statistics of distinct foods in 250 source days (regular: 15/16; vegetarian and vegan: 16/17). The regular MILPs selected 15 and 16 foods; vegetarian selected 16 and 17; vegan selected 23 under both floors. Vegan cases required nutrient relaxation, with vitamin D and B12 shortfalls unchanged from the capped baseline. These are daily aggregate baskets, not meal plans: no meal-slot, recipe compatibility, frequency, or clinical serving constraint is established. All results remain diagnostic under unresolved data and comparability gates.

Environmental-objective endpoints (2026-09-24): `environmental-objective-sensitivity_20260924T204613146732Z_fd0ea9dd` ran 18 solves: carbon, water, and ecological footprint optimized separately for both LP-Food (profile-specific observed-maximum caps) and LP-Meal across all three profiles. All returned a solution; all six vegan cases required relaxation. The vegan LP-Meal returned the same mean footprint vector under the three objectives, indicating that the common relaxed solution dominates this diagnostic endpoint grid. Other profiles show different footprint trade-offs across endpoints. The inputs' environmental food pairings are not fully adjudicated, objective units/scales differ, and method constraints differ; no composite weights, ranking, or manuscript claim are supported.

Pinned environmental-source audit (2026-09-24): `environmental-source-audit_20260924T205706574023Z_0d911e23` downloaded OSF file `655f914c79d42805e93e8434` and verified SHA-256 `988040f8e9c668d823c41b0839132a3494b9a3ad6e5a4945e18757542b16d4af`. All 1,170 distributed footprint-map labels matched the official 100-g preparation sheet and every coefficient was within the source's rounding precision. Among the 292 labels in the 150 preserved base diets (12,670 occurrences), 65 carbon, 35 water, and 37 ecological labels have multiple distinct official values associated with the same preparation label, affecting 2,741, 1,423, and 1,412 occurrences respectively. This verifies source lineage and numeric alignment, not which original POF item, geography, or system boundary is appropriate for each generated food; these ambiguities remain explicit blockers. The workbook is fetched to memory for the audit rather than redistributed with the repository.

LP-Meal frequency sensitivity (2026-09-24): `lp-meal-frequency-sensitivity_20260924T210812872195Z_ee1e352f` ran nine scenarios (three profiles × no cap, cap of one, and profile-specific q95 repeat cap). The q95 caps, derived from the maximum exact-meal recurrence within each source plan, are 3 for regular and 2 for vegetarian/vegan. Every returned plan respected its cap. Vegan cases required relaxation in all scenarios; limiting recurrence added a vitamin-D shortfall and a B12 shortfall in the capped vegan scenarios. Vegetarian capped cases required vitamin-D relaxation. Regular cap-1 had higher environmental cost and more diagnostic target violations than its uncapped solution, while the profile-q95 case changed the endpoint in the opposite direction. These patterns are solver/data diagnostics, not recommendations or manuscript results.

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

Compare profile-specific LP-Food without a cap, capped at the observed maximum
daily quantity, and capped at the empirical 95th percentile (with an explicit
observed-maximum fallback when support is sparse). Caps aggregate each food
across meal slots within a source day; they are not per-meal portions or
clinical recommendations. The registered run above is diagnostic only:

```bash
python -m tests.run_experiments --experiments lp-daily-quantity-support-sensitivity
```

Test an aggregate LP-Food/MILP basket with a minimum number of distinct foods.
The floors use the observed lower q25 and median order statistics by profile;
the MILP also requires a positive quantity of at least 1 g and finite observed-
maximum caps. It does not establish meal feasibility, recipe compatibility, or
clinical servings. Outputs are diagnostic only:

```bash
python -m tests.run_experiments --experiments lp-food-diversity-sensitivity
```

Optimize the three environmental indicators independently for profile-specific
LP-Food (using observed-maximum daily caps) and LP-Meal. This endpoint grid
does not combine differently scaled indicators into a weighted objective, and
it is not a fair causal comparison of the formulations:

```bash
python -m tests.run_experiments --experiments environmental-objective-sensitivity
```

Verify the distributed environmental coefficients against the pinned official
POF 2017--2018 workbook on OSF. The command checks the upstream SHA-256, parses
the 100-g preparation worksheet using only Python's standard library, and
records exact-label coverage, rounding agreement, and multiple-source-row
ambiguity for the preserved foods. Network access is required; a changed file
fails closed rather than silently updating the source:

```bash
python -m tests.run_experiments --experiments environmental-source-audit
```

Stress-test the LP endpoints against the per-label minimum and maximum values
among exact-label rows in the pinned source workbook. It varies one environmental
objective at a time and compares current/minimum/maximum maps within each profile
and formulation (54 solves). This is an outer source-row envelope, not a
probability interval: source rows may encode different foods, production origins,
or system boundaries. Every cell is diagnostic and retains solver fallback/slack
status; it must not be used as a primary result or a causal method comparison:

```bash
python -m tests.run_experiments --experiments environmental-source-range-sensitivity
```

Compare LP-Meal with no repeated-meal cap, a one-use-per-meal cap, and a
profile-specific cap equal to the observed q95 of maximum exact-meal recurrence
in the source plans. Identical meals are deduplicated only in capped scenarios,
and the cap remains hard during nutritional-slack fallback:

```bash
python -m tests.run_experiments --experiments lp-meal-frequency-sensitivity
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

Aggregate the per-execution runtime, exact GA fitness evaluations, stopping
generations, sampled resident memory, and LP fallback/slack details from a
completed full-replication workspace. The audit requires exactly 60 GA and 6 LP
execution records and creates its own immutable result and log:

```bash
python -m tests.run_experiments --experiments replication-resource-audit --source-run-id <full-replication-run-id>
```

The smoke and full commands create new stochastic results. They do not recreate the unrecorded random streams used in March 2026.

Each new GA run writes `data/outputs/optimization_runs/ag-*/runs/<diet>/execution-<n>.json`
inside its result workspace. This file contains the effective configuration, seed,
fitness trajectory, exact count of fitness-function evaluations, stop reason, duration, sampled process RSS (100-ms interval), final solution, daily and mean nutrient
and footprint metrics, and violations of the selected protocol's bounds.
LP produces one `data/outputs/optimization_runs/pl-*/execution-<profile>.json`
per profile with solver status, fallback details, final solution, and diagnostics.
The workspace `run-manifest.json` captures the current OS, CPU, physical RAM,
Python/dependency versions, and SciPy/HiGHS backend. Archived mode describes
the machine doing the reconstruction, not the unknown original machine.
The per-execution RSS is sampled process resident memory, not an allocation
trace, and short peaks between samples may be missed; report it as sampled
working-set usage rather than exact peak memory.

The base-diet audit writes item-, plan-, nutrient-, and summary-level evidence. It does not infer missing raw API responses, failures, or regeneration counts.

The registered GA sensitivity command is `python -m tests.run_experiments --experiments ga-hyperparameter-sensitivity --runs 10 --seed 20260936 --nutrition-protocol revised`. It pairs execution IDs under one base seed for baseline, reduced population, higher mutation, shorter stagnation, and crossover-repair disabled. Each nested manifest records the effective override payload and hash. The post-run review validates profile scope and writes paired differences with bootstrap intervals for scientific outcomes and computational measures (runtime, fitness evaluations, stopping generations, and sampled RSS). The repair-disabled arm is an algorithmic ablation, not a recommended configuration; the 1-run version is smoke validation only, not a sensitivity estimate.

Compare the relative environmental objective weight while holding the nutritional
weight at 1.0. The paired variants use environmental weights 0.5, 1.0, and 2.0
with identical input pools and seed IDs across all three profiles and both GA
granularities. These are computational sensitivity settings, not validated
clinical or policy preferences:

```bash
python -m tests.run_experiments --experiments ga-objective-weight-sensitivity --runs 10 --seed 20260935 --nutrition-protocol revised
python -m tests.run_experiments --experiments ga-objective-weight-review --source-run-id <printed-sensitivity-run-id>
```

The review accepts the printed run ID with or without the
`ga-objective-weight-sensitivity_` prefix and resolves the matrix summary in
the run's `audit/` workspace.

Measure the sensitivity to excluding, rather than reassigning, the 18 source
food labels whose TBCA targets remain unresolved (407 occurrences in the
adjudication queue; 403 incremental removals after profile exclusions). The baseline and exclusion variants share the same
versioned inputs and seed IDs; the exclusion copy records every removed
occurrence by profile. This is not a mapping decision or a primary result:

```bash
python -m tests.run_experiments --experiments food-mapping-exclusion-sensitivity --runs 10 --seed 20260937 --nutrition-protocol revised
python -m tests.run_experiments --experiments food-mapping-exclusion-review --source-run-id <printed-sensitivity-run-id>
```

The review checks input hashes, clean shared commit, ten paired IDs, all 66
outputs per variant, profile candidate scope, nutrient/environment outcomes,
and computational metrics. Its bootstrap intervals are unadjusted and the
excluded-label scenario does not adjudicate the actual food compositions.
