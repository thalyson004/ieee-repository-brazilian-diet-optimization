# Results contract

`article_outputs/canonical_results_long.csv` is the single numerical boundary between an experiment and article-facing outputs. Tables, figures, percentage changes, and generated LaTeX macros must be derived from this file or from the in-memory frame written to it in the same command.

Each row identifies `profile`, `approach`, `metric`, `statistic`, `value`, `unit`, observation count `n`, and the comparison basis. This makes the historical inconsistency explicit: the submitted GA main tables used one selected solution (`n=1`), while the diversity table used ten runs (`n=10`).

The command

```bash
python -m tests.run_experiments --experiments archived-reconstruction
```

generates the canonical file together with:

- `tabela_consolidada.csv` and `variacao_percentual.csv`;
- profile and diversity LaTeX tables;
- the four article figures;
- `canonical_results_macros.tex` for prose values;
- reports and validation evidence.

The submitted numbers are a frozen historical baseline, not evidence for the revised conclusions. New results must use the same schema, but each stochastic result must retain one row per independent execution before aggregation.
