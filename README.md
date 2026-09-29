# Optimizing LLM-Generated Diets for Sustainability

Code and data for *Optimizing LLM-Generated Diets for Sustainability: A Comparison of Genetic Algorithms and Linear Programming Across Brazilian Dietary Profiles*.

## Study scope

The study starts from 150 five-day diets generated with Gemini 3 Flash through its chat interface, 50 each for regular, vegetarian, and vegan profiles. It compares genetic algorithms (GA) and linear programming (LP) at food and meal granularity. Nutrient values come from the Brazilian Food Composition Table (TBCA), and environmental coefficients come from a [Brazilian food-footprint workbook](https://osf.io/g9d5y/).

The supplied article tables use one selected solution per method and profile. Food diversity is calculated from a separate collection of ten GA solutions per method and profile; LP has one deterministic solution. These collections are kept separate in the analysis. New seeded runs can be executed with the same project, but they are not substituted for the supplied table solutions.

## Repository contents

| Path | Contents |
| --- | --- |
| `src/diet_optimization/` | Optimization, experiment, and analysis code |
| `diets-base/` | The 150 input diets |
| `maps/` and `configs/` | Redistributable footprint inputs, nutritional targets, and run settings; TBCA inputs are local-only |
| `artifacts/reference/` | Selected solutions and expected CSV files for the article tables; TBCA input maps are local-only |
| `optimized-diets/` | GA collections and LP solutions used for diversity |
| `prompts/` | Portuguese prompt templates |
| `formulations/` | Mathematical descriptions of the four methods |
| `tests/` | Regression tests, experiment commands, and generated results and logs |

## Install

Python 3.11 or newer is required. From the repository root, install the package in your Python environment and run the regression tests:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Run the analyses

TBCA does not permit redistribution of its material. This repository therefore does not include its nutrient records or food-name/code mappings. Both commands below require the researcher to provide those inputs locally in the paths described in [data sources](docs/data.md). There is no automated TBCA download or API integration. Without independently obtained TBCA data, the nutritional calculations and full experiment cannot be reproduced from this repository alone.

```bash
python -m tests.run_experiments --experiments article-reconstruction
```

With the local TBCA inputs in place, this command rebuilds the tables and figures from the supplied diets and selected solutions. It checks the generated CSV files against `artifacts/reference/reference-tables/`. It does not rerun the optimizer.

To run GA and LP again with explicit GA seeds:

```bash
python -m tests.run_experiments --experiments full-replication --runs 10 --seed 20260323
```

Named experiments write a JSON summary to `tests/results/`, a log to `tests/logs/`, and detailed files under `tests/results/artifacts/`. Existing runs are not overwritten. See [experiment commands](tests/README.md) for sensitivity analyses and checks, [data sources](docs/data.md) for the food-linking process, and [result files](docs/results.md) for output definitions.

## Data use

Optimization can be rerun from the supplied diets only after the necessary TBCA inputs have been obtained independently. The chat interactions that generated those diets are not part of the executable pipeline, and chat-only inference settings such as temperature and seed were not configured. See [TBCA's terms](https://www.tbca.net.br/) before using its material. The generated diets are research outputs, not individual dietary prescriptions.

## Citation

Pending...

<!--
For the manuscript, use the citation below until final publication details are available. [CITATION.cff](CITATION.cff) provides a machine-readable citation for the code repository.

```bibtex
@misc{daSilva2026DietOptimization,
  author = {da Silva, Thalyson G. N. and de Oliveira, Thiago Q. and de Campos, Gustavo A. L. and J{\'u}nior, Bonfim A. and Barros, Ana L. B. P.},
  title = {Optimizing LLM-Generated Diets for Sustainability: A Comparison of Genetic Algorithms and Linear Programming Across Brazilian Dietary Profiles},
  year = {2026},
  note = {Manuscript}
}
```
-->

## License

The software is licensed under the [MIT License](LICENSE). This license does not apply to third-party data, including TBCA material or the Brazilian food-footprint workbook.
