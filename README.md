# Optimizing LLM-Generated Diets for Sustainability: A Comparison of Genetic Algorithms and Linear Programming Across Brazilian Dietary Profiles

This repository is the executable research project for the article **"Optimizing LLM-Generated Diets for Sustainability: A Comparison of Genetic Algorithms and Linear Programming Across Brazilian Dietary Profiles"**. It contains the optimization package, command-driven experiments, input data, historical artifacts, results, and execution logs.

The active implementation lives in [`src/diet_optimization/`](src/diet_optimization/). Every experiment is launched through [`tests/run_experiments.py`](tests/run_experiments.py), which creates a JSON result in `tests/results/` and a complete log in `tests/logs/`. Historical submitted artifacts are isolated in [`archive/`](archive/README.md); they are evidence, not the destination for new results.

## Installation and commands

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e .
.venv/Scripts/python -m unittest discover -s tests -v
.venv/Scripts/python -m tests.run_experiments --experiments archived-reconstruction
```

New bounded and full replications use the same command interface:

```bash
.venv/Scripts/python -m tests.run_experiments --experiments ga-smoke --seed 20260323
.venv/Scripts/python -m tests.run_experiments --experiments full-replication --runs 10 --seed 20260323
```

New reruns restrict LP-Food candidates to food names occurring in the 50 base
diets of the same profile. The original 150 diets remain unchanged. A derived
workspace copy excludes two exact, demonstrably non-vegan food names (five
occurrences) from the vegan input and records every removal in
`input-preparation.json`; this is **not** a complete ingredient-level review.
Verify candidate scope with:

```bash
.venv/Scripts/python -m tests.run_experiments --experiments lp-profile-scope
```

See [`tests/README.md`](tests/README.md) for the artifact contract and [`archive/README.md`](archive/README.md) for the limits of the recovered experiment. The complete food-linkage protocol and row-level audit are documented in [`docs/data-mapping.md`](docs/data-mapping.md). The preserved sustainable-name map contains identity and non-identity links; the latter cannot be classified as lexical normalizations or semantic substitutions without item-level review.

## Overview

This dataset accompanies the research on sustainable diet optimization combining Large Language Models (LLMs) with Genetic Algorithms (GA) and Linear Programming (LP). The study compares four optimization approaches across three dietary profiles (**Regular**, **Vegetarian**, and **Vegan**) with two granularity levels (**Food-level** and **Meal-level**).

### Summary

1. **Base Diets**: 150 normalized diets (50 per profile) preserved from the original LLM-generation stage, targeting 2,000 kcal/day (±5%). The exact Gemini model and inference settings are not recoverable from primary request logs; see [`generation/original-generation-metadata.json`](generation/original-generation-metadata.json).
2. **External Data Sources**: The knowledge maps in this repository were built from two external databases:
   - **TBCA** (Tabela Brasileira de Composição de Alimentos): nutritional composition per 100 g for 16 nutrients. Available at <https://www.tbca.net.br/>.
   - **Environmental footprint dataset**: updated Brazilian POF 2017--2018 tables released as an OSF workbook. The 100-g preparation sheet reports carbon (gCO₂e), water (L), and ecological (g·m²) values; see <https://osf.io/g9d5y/>. The revision's pinned audit verifies the workbook SHA-256 and map-label/value alignment while exposing multiple source rows for some standardized preparations.
3. **Optimization Approaches**:
   - **GA-Food**: Genetic Algorithm optimizing individual food items
   - **GA-Meal**: Genetic Algorithm optimizing complete meals
   - **LP-Food**: Linear Programming optimizing individual food items
   - **LP-Meal**: Linear Programming optimizing complete meals
4. **Objective**: Minimize carbon footprint while maintaining nutritional adequacy, energy balance, and diet diversity.
5. **Historical submitted results**: LP reported 93%+ carbon reductions but produced solutions with 10 unique foods. The submitted GA main table used one selected solution while diversity used 10 executions; these values are retained only as an auditable baseline and must not support the revised conclusions. See [`RESULTS-CONTRACT.md`](RESULTS-CONTRACT.md).

---

## Directory Structure

```
dataset-repository/
├── pyproject.toml                 # Installable Python project and CLI entry points
├── src/diet_optimization/         # Active optimization, analysis, and experiment code
├── tests/                         # Command runners, regressions, results, and logs
├── archive/                       # Immutable submitted-result lineage
├── maps/                          # Nutritional/environmental source and derived maps
├── diets-base/                    # 50 base diets per profile (150 total)
├── optimized-diets/               # Ten-run GA and deterministic LP historical outputs
├── formulations/                  # Mathematical formulations for each approach
└── prompts/                       # LLM prompts used for base diet generation
```

---

## Data Components

### 1. maps/ — Knowledge Maps

Intermediate maps linking food names to TBCA codes and sustainable alternatives. These maps were built by combining information from the two external databases listed above (TBCA for nutritional data and the environmental footprint dataset for carbon, water, and ecological footprints). The external databases themselves are not included in this repository; only the derived linking maps are provided.

#### base/

- **mapa-nome-tbca.json**: Maps food names (as they appear in the diets) to TBCA database codes.
- **mapa-sustentavel-nome.json**: Maps original food names to more sustainable variant names (e.g., white rice → wild rice).

#### derived/

- **mapa-sustentavel-tbca.json**: Maps sustainable food variant names to their corresponding TBCA codes. Derived by combining `mapa-sustentavel-nome.json` with `mapa-nome-tbca.json`.

The optimizer looks up the derived TBCA code by the original diet-food key. When the selected target name differs, nutrients are attributed through a non-identity link whose class and rationale were not preserved. The revised protocol treats these rows as a sensitivity factor rather than assuming equivalence.

### 2. diets-base/ — Base Dietary Profiles

The repository contains 50 normalized diets per profile. The automated audit verifies their present structure and mapping coverage but cannot reconstruct raw API failures or regeneration attempts.

- **dietas-regular.json**: 50 regular (omnivore) base diets
- **dietas-vegetariana.json**: 50 vegetarian base diets (no meat; includes dairy and eggs)
- **dietas-vegana.json**: 50 vegan base diets (no animal products)

Each file contains a JSON array of 50 diet objects. Each diet spans 5 days with 6 daily meals.

```json
[
  {
    "1": {
      "Café da Manhã": [{"alimento": "...", "quantidade": 50}, ...],
      "Lanche da Manhã": [...],
      "Almoço": [...],
      "Lanche da Tarde": [...],
      "Jantar": [...],
      "Ceia": [...]
    },
    "2": { ... },
    ...
    "5": { ... }
  }
]
```

### 3. optimized-diets/ — Optimization Results

Output diets from all four optimization approaches across three profiles.

#### ag-alimentos/ (GA-Food)
- **otimizada-dietas-regular.json**: 10 optimized regular diets (food-level GA, 10 independent runs)
- **otimizada-dietas-vegetariana.json**: 10 optimized vegetarian diets
- **otimizada-dietas-vegana.json**: 10 optimized vegan diets

GA-Food achieved carbon reductions of 2.5–26.3% across profiles, with 58.7–66.1 mean unique foods per week.

#### ag-refeicoes/ (GA-Meal)
- **otimizada-dietas-regular.json**: 10 optimized regular diets (meal-level GA, 10 independent runs)
- **otimizada-dietas-vegetariana.json**: 10 optimized vegetarian diets
- **otimizada-dietas-vegana.json**: 10 optimized vegan diets

GA-Meal achieved carbon reductions of 17.9–25.4% for regular and vegan profiles, with 56.8–64.6 mean unique foods per week and better energy adequacy than GA-Food.

#### pl-alimentos/ (LP-Food)
- **otimizada-dietas-regular.json**: 1 optimized regular diet (food-level LP)
- **otimizada-dietas-vegetariana.json**: 1 optimized vegetarian diet
- **otimizada-dietas-vegana.json**: 1 optimized vegan diet

LP-Food achieved 93–98% carbon reductions but concentrated the diet in 10 unique foods.

#### pl-refeicoes/ (LP-Meal)
- **otimizada-dietas-regular.json**: 1 optimized regular diet (meal-level LP)
- **otimizada-dietas-vegetariana.json**: 1 optimized vegetarian diet
- **otimizada-dietas-vegana.json**: 1 optimized vegan diet

LP-Meal achieved 3–62% carbon reductions with 23–32 unique foods, limited by the available meal pool.

### 4. formulations/ — Mathematical Formulations

Complete mathematical formulations for each optimization approach, including variables, constraints, penalty functions, hyperparameters, and (where applicable) constraint relaxation mechanisms.

- **ga-food.md**: GA at food-level granularity
- **ga-meal.md**: GA at meal-level granularity
- **lp-food.md**: LP at food-level granularity
- **lp-meal.md**: LP at meal-level granularity

### 5. prompts/ — LLM Prompts

The three complete published prompts and their SHA-256 manifest are preserved here. Byte identity across available repository copies is verified, but identity with the original API requests cannot be proven because request logs were not preserved.

- **prompt-regular.txt**: Prompt for generating regular diets
- **prompt-vegetariano.txt**: Prompt for generating vegetarian diets
- **prompt-vegana.txt**: Prompt for generating vegan diets

---
