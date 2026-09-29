# Results and generated files

With the locally supplied TBCA inputs described in [data sources](data.md), `python -m tests.run_experiments --experiments article-reconstruction` rebuilds the article tables and figures. Its workspace is printed by the command. Under `article_outputs/`, the main files are:

| File | Contents |
| --- | --- |
| `results_by_metric.csv` | Long-format metric values, units, observation counts, and comparison basis |
| `tabela_consolidada.csv` | Main nutrient and footprint table |
| `variacao_percentual.csv` | Change relative to the matching base-profile mean |
| `diversity_summary.csv` | Unique-food counts by profile and method |
| `figures/` | Article plots generated from the same inputs |
| `results_macros.tex` | Optional LaTeX value definitions from `results_by_metric.csv` |

The long-format file has `profile`, `approach`, `metric`, `statistic`, `value`, `unit`, `n`, and `comparison_basis` columns. The supplied main GA table has one selected solution for each method and profile (`n=1`). The supplied diversity data contain ten GA solutions for each method and profile (`n=10`). Those are separate collections. LP outputs contain one solution per method and profile. The observation count must be considered when interpreting any comparison.

Every new experiment writes a JSON summary to `tests/results/`, a full log to `tests/logs/`, and detailed artifacts under `tests/results/artifacts/`. The run manifest records input hashes, effective settings, seed, solver information, and status. New GA runs retain one record per independent execution before any summary is calculated. LP reports distinguish strict solver status from a penalized-slack fallback and include post-solution nutrient checks.

The files in `artifacts/reference/reference-tables/` are expected outputs for the reconstruction command. They are computational results, not individual dietary recommendations.
