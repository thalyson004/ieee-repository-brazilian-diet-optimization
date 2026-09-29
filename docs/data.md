# Data sources and preparation

## Diet plans and prompts

`diets-base/` contains 50 normalized five-day plans for each regular, vegetarian, and vegan profile. Each day has six meal positions and item quantities in grams. Gemini 3 Flash generated the plans through its chat interface. The files in `prompts/` document the prompt structure. Optimization begins with the supplied plans; the chat interactions themselves are not rerun by this project.

The profiles describe which candidate foods are eligible for an optimizer. Both food-level methods draw candidates only from the matching profile's input plans. Profile labels alone do not verify every recipe ingredient. Exact known contradictions are listed in `configs/profile-exclusions.json`; other ingredient uncertainties remain visible in the generated profile check.

## Nutrient and footprint lookup

For each source food name, the optimizer follows these maps. The four TBCA-related files below are required local inputs, not repository contents:

1. `maps/base/mapa-sustentavel-nome.json` selects a TBCA target name.
2. `maps/base/mapa-nome-tbca.json` maps that name to a TBCA code.
3. `maps/derived/mapa-sustentavel-tbca.json` contains the composed food-to-code link used by the optimizer.
4. `maps/base/mapa-tbca-completo.json` supplies available nutrients per 100 g.
5. `maps/base/mapa-sustentavel-pegadas.json` supplies carbon, water, and ecological coefficients per 100 g for the source food name.

TBCA is available for consultation at <https://www.tbca.net.br/>. Its terms prohibit reproduction of the material, so this repository does not contain the four TBCA files or an automated way to obtain them. A researcher with independently obtained, lawfully usable inputs must place them at the four paths above for new runs. The article-table reconstruction requires the corresponding copies under `artifacts/reference/table-input-maps/`. The program does not fetch data from TBCA, and substituting another food-composition table would be a different experiment. The environmental coefficients originate from the [POF-based food-footprint workbook](https://osf.io/g9d5y/).

A successful name or code join does not establish that two preparations have identical ingredients or nutrient composition. Some names map to a different TBCA name, several POF rows share a standardized preparation label, and some nutrient fields are absent. These conditions affect the interpretation of totals and optimizer feasibility. The following commands write detailed diagnostics without changing the input plans:

```bash
python -m tests.run_experiments --experiments base-diet-audit
python -m tests.run_experiments --experiments profile-ingredient-audit
python -m tests.run_experiments --experiments nutrient-missingness-audit
python -m tests.run_experiments --experiments environmental-source-audit
```

Observed food quantities can be summarized by profile and meal with `--experiments portion-support-audit`. These are corpus statistics, not recommended serving sizes. The nutritional targets in `configs/study-nutrition-protocol.json` are computational constraints for the stated reference case, not an assessment of an individual's needs.

## Data use

TBCA-derived mapping-review fixtures are also excluded from the repository. The published aggregate result tables can be inspected without the private inputs, but independent reconstruction of their nutrient values requires access to the same underlying TBCA records and mappings. The original environmental workbook is not bundled and should be obtained from its source when independently checking coefficients.
