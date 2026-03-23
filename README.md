# Dataset Repository: Sustainable Diet Optimization Data

This repository contains all data used and generated in the article **"Neuro-Symbolic Approaches for Sustainable Diet Optimization: A Comparative Study of Genetic Algorithms and Linear Programming"**.

## Overview

This dataset serves as a comprehensive resource for the research on sustainable diet optimization combining neuro-symbolic AI techniques. The study compares two optimization paradigms (**Genetic Algorithm** and **Linear Programming**) across three dietary profiles (**Regular**, **Vegetarian**, and **Vegan**) with two resolution levels (**Food-level** and **Meal-level optimization**).

### Article Overview

The article investigates sustainable diet optimization through:

1. **Base Diets**: 50 typical diets per profile from Brazilian dietary patterns
2. **Data Sources**: TBCA (tabela brasileira de composição de alimentos) and UNEP/World Food LCA Database for nutritional and environmental data
3. **Optimization Methods**:
   - **GA-Food**: Genetic Algorithm optimizing individual food selections
   - **GA-Meal**: Genetic Algorithm optimizing meal compositions (higher-level search space)
   - **LP-Food**: Linear Programming optimizing individual food selections
   - **LP-Meal**: Linear Programming optimizing meal compositions

4. **Objectives**: Minimize carbon footprint while maintaining nutritional adequacy (energy, macronutrients, micronutrients, and food diversity)

5. **Key Results**: GA-Meal significantly outperforms GA-Food baseline in carbon reduction, nutritional adequacy, and dietary diversity due to the more constrained meal-level search space enabling better exploration of sustainable combinations.

---

## Directory Structure

```
dataset-repository/
├── README.md                    # This file
├── maps/                        # Knowledge maps for food/footprint data
├── diets-base/                  # 50 base diets per profile used as starting points
├── optimized-diets/             # Results from all optimization approaches
│   ├── ag-alimentos/            # GA-Food results
│   ├── ag-refeicoes/            # GA-Meal results
│   ├── pl-alimentos/            # LP-Food results
│   └── pl-refeicoes/            # LP-Meal results
└── prompts/                     # LLM prompts used for initial diet design
```

---

## Data Components

### 1. **maps/** — Knowledge Maps

Maps linking food names, nutritional values, and carbon footprint data used throughout optimization.

- **mapa-nome-tbca.json**: Mapping between food names and TBCA database entries
- **mapa-tbca-completo.json**: Complete TBCA mapping with all nutritional values
- **mapa-sustentavel-nome.json**: Mapping for sustainable food alternatives
- **mapa-sustentavel-pegadas.json**: Carbon footprint mappings for sustainable foods
- **derived/mapa-sustentavel-tbca.json**: Derived sustainable food map with integrated TBCA data

**Purpose**: These maps are essential inputs to the optimization pipeline, ensuring consistent food identification and nutritional/environmental data lookup across all algorithms.

### 2. **diets-base/** — Base Dietary Profiles

50 typical diets per profile representing current eating patterns in Brazil.

- **dietas-regular.json**: 50 regular (omnivore) base diets
- **dietas-vegetariana.json**: 50 vegetarian base diets (no meat, includes dairy/eggs)
- **dietas-vegana.json**: 50 vegan base diets (no animal products)

**Structure**: Each file contains a JSON array of 50 diet objects. Each diet spans 7 days with meals organized by meal type (breakfast, snacks, lunch, dinner, supper).

**Format**:
```json
[
  {
    "1": {
      "Café da Manhã": [...items...],
      "Lanche da Manhã": [...items...],
      "Almoço": [...items...],
      ...
    },
    "2": { ... next day ... }
  }
]
```

### 3. **optimized-diets/** — Optimization Results

Output diets from all four optimization approaches across three profiles.

#### **ag-alimentos/** (GA-Food)
- **otimizada-dietas-regular.json**: Optimized regular diets from food-level GA
- **otimizada-dietas-vegetariana.json**: Optimized vegetarian diets from food-level GA
- **otimizada-dietas-vegana.json**: Optimized vegan diets from food-level GA

*Results*: GA optimizing at food level typically achieves 30-40% carbon reduction but may sacrifice meal coherence.

#### **ag-refeicoes/** (GA-Meal)
- **otimizada-dietas-regular.json**: Optimized regular diets from meal-level GA
- **otimizada-dietas-vegetariana.json**: Optimized vegetarian diets from meal-level GA
- **otimizada-dietas-vegana.json**: Optimized vegan diets from meal-level GA

*Results*: GA optimizing at meal level achieves higher energy adequacy, reduced carbon footprint (~50% reduction), and better food diversity due to meaningful meal constraints.

#### **pl-alimentos/** (LP-Food)
- **otimizada-dietas-regular.json**: Optimized regular diets from food-level LP
- **otimizada-dietas-vegetariana.json**: Optimized vegetarian diets from food-level LP
- **otimizada-dietas-vegana.json**: Optimized vegan diets from food-level LP

*Results*: LP at food level achieves minimal solutions with < 20% of recommended energy due to unconstrained optimization.

#### **pl-refeicoes/** (LP-Meal)
- **otimizada-dietas-regular.json**: Optimized regular diets from meal-level LP
- **otimizada-dietas-vegetariana.json**: Optimized vegetarian diets from meal-level LP
- **otimizada-dietas-vegana.json**: Optimized vegan diets from meal-level LP

*Results*: LP at meal level achieves minimal solutions but respects meal allocations, similar limitations as LP-Food.

### 4. **prompts/** — LLM Prompts

Initial prompts used to generate the 50 base diets via large language models.

- **prompt-regular.txt**: Prompt for generating regular diets
- **prompt-vegetariana.txt**: Prompt for generating vegetarian diets
- **prompt-vegana.txt**: Prompt for generating vegan diets

**Purpose**: Full transparency on how base diets were generated and reproducibility of the dataset creation process.

---

## Data Format Details

### Diet Files Structure

Each diet file contains a JSON array where each element represents one diet plan:

```json
{
  "1": {  // Day 1
    "Café da Manhã": [  // Breakfast
      {
        "alimento": "Bread, white, toasted",
        "quantidade": 50,  // grams
        "ENERGIA": 130,
        "PROTEÍNA": 4.5,
        ...
      },
      ...
    ],
    "Lanche da Manhã": [...],
    "Almoço": [...],
    "Lanche da Tarde": [...],
    "Jantar": [...],
    "Ceia": [...]  // may be empty
  },
  "2": { ... day 2 ... },
  ...
  "7": { ... day 7 ... }
}
```

### Nutritional Values

Each food item includes:
- **ENERGIA**: Energy in kcal
- **PROTEÍNA**: Protein in grams
- **LIPÍDIOS**: Lipids in grams
- **CARBOIDRATO_DISPONÍVEL**: Available carbohydrates in grams
- **FIBRA_ALIMENTAR**: Dietary fiber in grams
- **CÁLCIO**: Calcium in mg
- **FERRO**: Iron in mg
- **VITAMINA_C**: Vitamin C in mg
- **SÓDIO**: Sodium in mg
- **COLESTEROL**: Cholesterol in mg
- **carbon_footprint**: Carbon footprint in gCO2eq per 100g

---

## Citation

If you use this dataset in your research, please cite:

```
[Author et al., "Neuro-Symbolic Approaches for Sustainable Diet Optimization..." Journal/Conference, Year]
```

---

## License

[Specify your license here: MIT, CC-BY-4.0, etc.]

---

## Contact

For questions about this dataset, contact: [Author email/institution]

---

## Note on Reproducibility

This dataset represents the complete input and output data from the optimization pipeline. To reproduce the results:

1. Load base diets from `diets-base/`
2. Use maps from `maps/` for food identification and data lookup
3. Run GA or LP optimizers with the specified hyperparameters (documented in the article)
4. Compare results against the corresponding `optimized-diets/` subdirectory

All source code for the optimization algorithms is available in the main repository.
