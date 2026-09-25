# Experiment and regression commands

Latest mapping checkpoint (2026-09-25): wholegrain homemade bread remains linked to BRC0149A as a table target based on six exact POF records sharing C0149A, matching nutrient vectors, and rounded environmental values. This does not establish the home recipe or vegan ingredient eligibility. The ledger has 162 adjudicated targets and 8 unresolved labels (256 occurrences); active numeric maps did not change. Latest unit suite: `unit-tests_20260925T075104371665Z_3b1fe28e` (67 tests). Current queue: `mapping-review-queue-current_20260925T074632140954Z_1eec4b77`. Ten-seed paired exclusion sensitivity `food-mapping-exclusion-sensitivity_20260925T072906762035Z_d74c5ebd` passed in 758.1 s on clean commit `fcce9835e38476149936702873f3c51057de80d3`; independent review `food-mapping-exclusion-review_20260925T074157959578Z_772a448f` passed. Both variants produced 66 outputs, 132 profile-scope checks passed without violations, and all 14 input hashes matched. Exclusion removed 17/107/132 occurrences (regular/vegetarian/vegan). One of 24 unadjusted paired outcome intervals and 12/24 computational intervals excluded zero; the latter remain exploratory and multiplicity is unadjusted. Both variants returned all six LP solutions, with five strict solves plus the vegan LP-Meal fallback; every LP solution retained nutrient violations. Diagnostic only, not a primary result or mapping adjudication.

Latest adjudication/sensitivity checkpoint (2026-09-25): tapioca with condensed milk and coconut remains on BRC0839B, now supported by exact POF records `6904501#99` and `6904502#99` (shared historical code C0839B, equal nutrients and footprints); distributed footprints match after rounding. Recipe proportions remain unknown, so evidence is item-level only. The ledger now records 159 decisions and 11 unresolved labels (296 occurrences); the active map/numeric coefficients did not change. Clean queue `mapping-review-queue-current_20260925T062127043266Z_3c6580de`; the updated exclusion sensitivity `food-mapping-exclusion-sensitivity_20260925T062221024841Z_adbd4dcb` (753.6 s) passed paired review `food-mapping-exclusion-review_20260925T063503267801Z_83ce90f0` on clean commit `3c67e899dbf1f31f2191aa39e67b0f0ce7dfdbc1`. Both variants produced 66 outputs and all 132 profile-scope checks passed; 14 input hashes matched. Exclusion removed 23/128/145 occurrences (regular/vegetarian/vegan). No unadjusted 95% paired bootstrap interval excluded zero among 24 outcome groups; 5/24 computational groups did, all sampled peak RSS. All six LP solutions per variant persisted; five were strict and vegan LP-Meal used fallback, with nutrient violations in all LPs. These remain diagnostic contrasts, not primary paper results.

Post-adjudication full replication: `full-replication_20260925T060754912020Z_f95ab0db` passed with 10 seeds, seed base 20260937, revised protocol, and clean source commit `d6556529d561bdcc701185351e63a8df1adc5862`; 60 GA + 6 LP outputs passed all 66 profile-scope checks in 372.1 s. Resource audit `replication-resource-audit_20260925T061411287950Z_33be89b3` passed (60 GA, 6 LP); mean GA runtime was 4.57–8.05 s and sampled peak RSS maxima 116.3–118.6 MB across profile/method groups. All six LP records still have nutrient violations (15, 25, 20, 30, 19, 24 in profile/method order); vegan LP-Meal required penalized-slack fallback. The input manifest records `scientific_readiness=diagnostic_pending_food_mapping_review_and_nutrient_missingness_sensitivity`; no result is promoted to the paper.

Latest mapping review (2026-09-25): grilled eggplant was adjudicated only as a target-specific TBCA nutrition match for BRC0287B using the shared POF code C0287B; this does not claim exact recipe equivalence or resolve the distinct environmental source rows. The mapping ledger now has 158 decisions and 12 pending labels (298 occurrences). The pending-label exclusion sensitivity `food-mapping-exclusion-sensitivity_20260925T055302321871Z_21b8844f` completed in 739.7 s and passed paired review `food-mapping-exclusion-review_20260925T060527147876Z_383406c1` on clean commit `3aad24d6728048f9d20010681210f2bc071927e5`. Both variants produced 66 outputs; all 132 profile-scope checks passed with zero violations and the 14 input hashes matched. Excluding the pending labels removed 23/130/145 occurrences (regular/vegetarian/vegan). Unadjusted paired bootstrap intervals excluded zero for 1/24 outcome groups (vegetarian GA-Food energy; mean difference -46.64 kcal/day, 95% CI [-70.35, -15.54]) and 6/24 computational groups, all sampled peak RSS. Both variants returned all six LP solutions, with five strict solves and the vegan LP-Meal fallback; all LPs still had nutrient violations. This is diagnostic sensitivity, not evidence that the remaining map is correct or a primary manuscript result.

Every experiment is launched by a named command. Each invocation writes an immutable JSON summary to `tests/results/`, a complete execution log to `tests/logs/`, and heavy generated artifacts below `tests/results/artifacts/`.

Run the deterministic suite through the same result/log wrapper (one command, one JSON result, one full log):

```bash
python -m tests.run_experiments --experiments unit-tests
```

Latest adjudication and audit checkpoint (2026-09-25): soybean oil was remapped from the unsupported fried entry BRC0048D to exact POF/TBCA lineage `8400301#99`/C0030D → BRC0030D; the three distributed environmental coefficients round to the POF row. The vegan evidence is specific to this listed plant-oil item, not the full generated meal. The index now has 157 target decisions and 13 unresolved links (320 occurrences). Clean-commit audits on `72ced5b`: `unit-tests_20260925T051341885344Z_b11cbb8f` (61 tests), `base-diet-audit_20260925T051345741752Z_09f6571b` (150 valid plans, 12,670 food occurrences, 1,600 diagnostic nutrient violations), `mapping-review-queue-current_20260925T051346053816Z_e61d4605` (13 unresolved names), `profile-ingredient-audit_20260925T051346880274Z_ff7264a3` (364 rows; 358 pending, 4 target-specific recipe-evidence rows, 2 exclusions), `nutrient-missingness-audit_20260925T051347135722Z_7b8b97a8`, `environmental-source-audit_20260925T051347518952Z_199c8379`, and `lp-profile-scope_20260925T051350969643Z_84281fdf`; all passed. Missingness still leaves no complete-case mandatory breakfast/lunch in regular and vegan, nor breakfast in vegan. Environmental coefficients align after rounding, but unresolved environmental and recipe-equivalence issues remain.

Current 13-label mapping-exclusion sensitivity: `food-mapping-exclusion-sensitivity_20260925T051444530975Z_e685ede1`, reviewed as `food-mapping-exclusion-review_20260925T052651655998Z_f565356f`. Ten paired seeds produced 66 outputs per variant with clean commit `9d1661dae2d0dbd2997b12de46b0844eb77a6602`, 14 identical input hashes, and zero profile-scope violations. Exclusion removed 23/151/146 source occurrences (regular/vegetarian/vegan). Unadjusted 95% paired bootstrap intervals excluded zero for 1/24 outcome groups and 8/24 computational groups. Both variants returned all six LP solutions; one LP-Meal vegan record per variant used penalized-slack fallback. These are diagnostic inclusion/exclusion effects, not evidence of correct target mappings or primary manuscript results.

Post-soybean-oil full diagnostic replication: `full-replication_20260925T053216544609Z_cb310d0e` completed 60 GA + 6 LP in 374.4 s, with ten seeds, seed base 20260937, revised protocol, clean input commit `57e5e3cbf1ef93b8d9fea9f100ee5d93de308a24`, and 66/66 profile-scope checks passing. Five LPs solved strictly; vegan LP-Meal used penalized slacks, and all six rounded/daily plans still had nutritional violations. Resource audit `replication-resource-audit_20260925T053834929034Z_e7b89ae8` passed (60 GA and six LP); GA group means were 4.81–8.03 s and sampled peak RSS 116.7–119.6 MB. The run remains diagnostic and must not be used as the primary paper result while mapping, ingredient eligibility, missingness, and GA/LP comparability gates remain open.

Current-source audits on the same clean commit are recorded as `base-diet-audit_20260925T054040921896Z_030028eb`, `mapping-review-queue-current_20260925T054041286285Z_92afdb48`, `profile-ingredient-audit_20260925T054042137048Z_86617e0b`, `nutrient-missingness-audit_20260925T054042382460Z_0d6ed230`, `environmental-source-audit_20260925T054042742725Z_8b7f5a69`, and `lp-profile-scope_20260925T054046236064Z_26d296ba`; all passed. The counts are unchanged: 157 target decisions, 13 pending labels, 358/364 ingredient-review rows pending, and 1,600 diagnostic nutrient violations in the 150 input plans.

Historical, superseded 14-label sensitivity `food-mapping-exclusion-sensitivity_20260925T024820232971Z_5026a88b` and review `food-mapping-exclusion-review_20260925T030219207327Z_ce8ed847` passed at clean input commit `b17cd1cb04fef4fc6082c9f7a630d18f85c310bc`: 66 outputs per variant and valid profile scope. This older queue is replaced by the 13-label run recorded above; retain its contrasts as historical diagnostics only.

After the cacao candidate update, current-map LP diagnostics were rerun with result/log wrappers: `lp-slack-sensitivity_20260925T030538411621Z_8da28c21` (24 penalty cases; 20 strict solutions and all four vegan LP-Meal cases relaxed, with a vitamin-D shortfall throughout); `lp-daily-quantity-support-sensitivity_20260925T030715563869Z_f0fd31e6` (nine cap/profile cases); `lp-food-diversity-sensitivity_20260925T030716367994Z_1929b386` (nine MILP cases); `lp-meal-frequency-sensitivity_20260925T030717215080Z_480d01b6` (nine cases); `environmental-objective-sensitivity_20260925T030748473674Z_fda0c243` (18 endpoints); and `environmental-source-range-sensitivity_20260925T030749809827Z_1ef6673d` (54 solves, 18 profile-method-objective cells). All commands passed. In the environmental outer-envelope review, selected plans changed between source-minimum/current/source-maximum in 7/18 cells; six vegan cells used relaxed solutions. The envelope is not probabilistic and cannot adjudicate which POF line applies. All are diagnostic; none is a manuscript result.

The meal-level portion-support inventory was also refreshed at `portion-support-audit_20260925T030943782569Z_415c41e3` (1,033 profile-food-meal rows). It supports data-derived cap exploration only; sparse strata and the absence of clinical validation preclude treating these values as portion recommendations.

The five-condition GA sensitivity was rerun after mapping corrections: `ga-hyperparameter-sensitivity_20260925T031113132706Z_794836cd`, ten paired seeds, seed base 20260939, and 66 outputs for each of baseline, reduced population, higher mutation, shorter stagnation, and crossover repair disabled. Review `ga-sensitivity-review_20260925T033517625676Z_440000c9` passed profile-scope checks for all 330 outputs and computed 96 outcome plus 96 computational paired contrasts. Unadjusted 95% bootstrap intervals excluded zero in 35/96 outcome and 69/96 computational contrasts; no multiplicity adjustment or recommendation is implied. All outputs are diagnostics while the data and method-equivalence gates remain open.

The GA environmental-objective weight matrix was rerun from a clean commit: `ga-objective-weight-sensitivity_20260925T035603975889Z_791f4615` (ten paired seeds, seed base 20260941; baseline weight 1.0 versus 0.5 and 2.0, with the nutritional weight fixed at 1.0). Review `ga-objective-weight-review_20260925T041504321536Z_fb2d88a3` passed all 66 output scope checks per condition and verified paired inputs. It produced 48 contrasts; 1/48 unadjusted bootstrap intervals excluded zero. This does not justify selecting a different weight, and the environmental weight remains a modeling sensitivity rather than a normative parameter.

Earlier mapping-review checkpoint (2026-09-24): 49 nutrition-target decisions were indexed and the active-map queue had 121 unresolved links. This historical snapshot does not adjudicate ingredient formulation, preparation, or environmental equivalence.

Post-sensitivity audits (2026-09-25): `base-diet-audit_20260925T012817831241Z_ae7a4e6f`, `profile-ingredient-audit_20260925T012818208337Z_f755651d`, `nutrient-missingness-audit_20260925T012818456433Z_87350307`, `environmental-source-audit_20260925T012818814448Z_defd93ef`, and `lp-profile-scope_20260925T012826303453Z_bff7d01b` all passed. Current results reconfirm 150 valid plans, 153 target decisions, 17 unresolved links, and open ingredient, missingness-policy, environmental-row attribution, and LP/GA-comparability limits; see the Phase 4 plan for exact counts and interpretation.

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

Query the official TBCA statistical pages for the mapped foods actually present
in the preserved source diets. The report stores only aggregate counts of
`NA`, trace, blank, and numeric provenance categories by nutrient/profile; it
does not persist food-level compositions, numeric nutrient values, or source
pages, and it does not impute values or modify the optimizer maps. Network
access is required:

```bash
python -m tests.run_experiments --experiments tbca-marker-audit
```

Compare the preserved numeric snapshot with an exact-name scenario excluding
the vegan-only food whose current official TBCA record page is blank. This
paired experiment reruns all four formulations over repeated seeds and writes
scope, source-hash, LP-status, outcome, and computational contrasts. It is an
availability sensitivity only, not an adjudication or primary input policy:

```bash
python -m tests.run_experiments --experiments tbca-record-availability-sensitivity --runs 10 --seed 20260938
```

If optimization completes but report post-processing fails, review the saved
variant workspaces without rerunning them (the source run ID is the suffix in
its JSON/log filename):

```bash
python -m tests.run_experiments --experiments tbca-record-availability-review --source-run-id 20260925T084335974487Z_8badb72d
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

Measure the sensitivity to excluding, rather than reassigning, the source
food labels whose TBCA targets remain unresolved (13 labels, 320 occurrences
in the current adjudication queue). The baseline and exclusion variants share the same
versioned inputs and seed IDs; the exclusion copy records every removed
occurrence by profile. This is not a mapping decision or a primary result:

```bash
python -m tests.run_experiments --experiments food-mapping-exclusion-sensitivity --runs 10 --seed 20260937 --nutrition-protocol revised
python -m tests.run_experiments --experiments food-mapping-exclusion-review --source-run-id <printed-sensitivity-run-id>
```

The review checks input hashes, clean shared commit, ten paired IDs, all 66
outputs per variant, profile candidate scope, nutrient/environment outcomes,
computational metrics, and all six LP execution records per variant (three per
method). A completed run can include a documented relaxed LP solution.
Bootstrap intervals are unadjusted and the excluded-label scenario does not
adjudicate the actual food compositions.

Run the profile-specific LP-Food meal-slot structure diagnostic:

```bash
python -m tests.run_experiments --experiments lp-food-meal-structure-sensitivity
```

This five-day MILP assigns foods only to meal slots observed in the same
profile's source diets and applies empirical daily diversity, repeat, quantity,
and meal-energy-share bounds. Nutrient targets are imposed separately on each
day. If strict optimization has no feasible solution, only nutrient rows may
receive nonnegative slack; all structural bounds remain hard. The JSON exports
solver statuses, slack and nutrient diagnostics, the five-day plan, and an
independent check of each structural invariant. A returned plan is therefore
not proof of strict nutrient feasibility, ingredient compatibility, complete
recipes, clinical suitability, or source-data validity. It is a diagnostic
comparison with the existing aggregate LP-Food formulation, not a primary
result.
