# Reproducibility package

This directory reconstructs the optimization and reporting pipeline used for the article. It separates two reproducibility claims that must not be conflated:

1. **Published-result reconstruction (`archived`)** rebuilds tables and figures from the exact released GA/LP solution files and archived GA traces.
2. **New deterministic replication (`rerun`)** executes the historical algorithm again with an explicit seed. It validates the implementation but is not expected to reproduce the exact stochastic GA solutions from March 2026 because the original random seeds were not recorded.

## Provenance

- Historical source snapshot: parent-repository commit `e5f760c` (23 March 2026), the commit that saved all 10 GA executions for each profile and granularity.
- The solution files in `../optimized-diets/` are semantically identical to the ten-run files at that commit.
- The main nutrition/carbon tables predate that change. `published-table-solutions/` preserves commit `fb34919`, in which each GA file contains the single selected solution actually used to generate those tables. The later ten-run files were used for the diversity analysis without regenerating the main tables.
- `code/otimizar/` and `code/scripts/calculate_statistics.py` are exact source snapshots. Path staging and seed recording live only in the new scripts under `scripts/`.
- `archived-runs/` contains the six per-profile GA experiment records and both effective hyperparameter exports from that commit.
- `inputs/` contains the two large source maps required by the historical code but previously absent from the public artifact.

The 150 base diets are archived inputs, not outputs that can currently be regenerated exactly. The original Gemini API-call logs, complete inference settings, failure/regeneration counts, and response-level seeds were not preserved. The prompts are available in `../prompts/`; this limitation must remain explicit in the manuscript and response to reviewers.

## Environment

The historical bytecode and repository records indicate Python 3.12, but the exact package lockfile was not preserved. Create a clean environment and install the compatible dependency ranges:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

On Linux/macOS, activate the environment using the platform-equivalent `bin/python` path.

## Rebuild the published tables and figures

This is the fast, non-stochastic verification path:

```bash
python scripts/run_experiments.py --mode archived
python scripts/validate_reconstruction.py
```

Outputs are written to `generated/article_outputs/`. A fresh output path can be selected with `--output-dir`.

Archived mode intentionally reconstructs the historical mixed aggregation: the main tables use the selected-solution snapshot and diversity uses all 10 GA solutions. This reproduces the submitted artifacts but exposes a unit-of-analysis inconsistency. The revised paper must replace this mixed protocol with tables and uncertainty estimates computed consistently from every independent run.

The validator compares all 33 rows of the reconstructed main table and the percentage-variation table with the submitted CSVs. It also checks the diversity values and the expected population sizes: 50 base diets per profile, one selected GA/LP solution per published-table file, and 10 solutions per archived GA configuration.

## Execute a new deterministic replication

The full historical settings use 10 GA executions for each of three profiles and two granularities (60 GA executions), followed by six LP optimizations:

```bash
python scripts/run_experiments.py --mode rerun --runs 10 --seed 20260323
```

For a bounded smoke test, use a fresh output path and one run:

```bash
python scripts/run_experiments.py --mode rerun --runs 1 --seed 20260323 --output-dir generated-smoke
```

The runner refuses to overwrite a non-empty output directory. Each run emits `run-manifest.json` with provenance, mode, seed, environment, and the executed command.

## What remains to satisfy the new review

This package recovers the historical experiment code and artifacts, but it does not by itself satisfy the newly requested experimental protocol. The revision still requires:

- independent per-run seeds rather than only one stream-level seed;
- SD, confidence intervals, effect sizes, and justified statistical tests;
- GA parameter and objective-weight sensitivity analyses;
- LP slack/penalty diagnostics and practical diversity/portion constraints;
- environmental-coefficient uncertainty analysis;
- complete LLM generation logs and expert nutritional validation, if obtainable.

These additions must be versioned as a new protocol rather than retroactively described as properties of the March 2026 experiment.

