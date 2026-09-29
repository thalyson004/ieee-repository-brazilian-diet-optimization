# Experiment commands

Run commands from the project root after installing the package and placing any required TBCA inputs locally as described in [data sources](../docs/data.md). Every name accepted by `--experiments` runs through the same entry point:

```bash
python -m tests.run_experiments --experiments NAME
```

The command prints the paths to a summary JSON file in `tests/results/`, a full log in `tests/logs/`, and an artifact workspace in `tests/results/artifacts/`. Outputs are placed in unique directories. The runner refuses to overwrite an existing run.

## Main commands

| Name | Purpose |
| --- | --- |
| `unit-tests` | Run the deterministic regression suite |
| `article-reconstruction` | Rebuild and check the supplied article tables and figures |
| `base-diet-audit` | Check the structure and mapped coverage of the 150 input plans |
| `lp-profile-scope` | Verify that LP-Food candidates come from the matching dietary profile |
| `ga-smoke` | Run one GA execution per profile and formulation to check the pipeline |
| `full-replication` | Run the specified number of independent GA seeds and the LP formulations |

For a ten-seed experiment:

```bash
python -m tests.run_experiments --experiments full-replication --runs 10 --seed 20260323
```

`ga-smoke` is a software check and does not estimate variability. The table reconstruction reads the supplied solutions and locally supplied table-input maps. `full-replication` computes new solutions from the local active maps and records the seed and effective configuration for each execution. A successful solver call does not imply that all nutritional bounds hold after rounding; inspect the post-solution diagnostics and any LP slack status.

## Data and sensitivity commands

The same entry point also accepts `nutrient-missingness-audit`, `tbca-marker-audit`, `profile-ingredient-audit`, `mapping-review-queue-current`, `portion-support-audit`, `environmental-source-audit`, `environmental-source-range-sensitivity`, `lp-slack-sensitivity`, `lp-food-diversity-sensitivity`, `lp-food-meal-structure-sensitivity`, `lp-daily-quantity-support-sensitivity`, `lp-meal-frequency-sensitivity`, `ga-hyperparameter-sensitivity`, `ga-objective-weight-sensitivity`, and `food-mapping-exclusion-sensitivity`. Run `python -m tests.run_experiments --help` for the complete accepted-name list and shared options.

Review commands such as `replication-resource-audit` and `ga-objective-trace-audit` take `--source-run-id` from a completed source experiment. They inspect saved artifacts without rerunning its optimizer. Sensitivity commands compare specified computational scenarios; they do not select a clinically preferred diet or repair uncertain source data.

The full regression suite uses local food-mapping fixtures that are not distributed because they contain TBCA-derived material. Generated result files and logs are intentionally excluded from the source package.
