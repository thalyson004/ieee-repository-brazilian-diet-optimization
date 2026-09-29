# GA-Meal: Genetic Algorithm at Meal-Level Granularity

## Overview

GA-Meal optimizes a 5-day diet plan by treating **entire meals** as atomic units. Each gene stores a complete meal instance; mutation and crossover operate at this coarser granularity. Unlike GA-Food, **global mutation is enabled**, allowing entire meals to be swapped from the meal pool, and the initial population is **seeded with base chromosomes** built from the original LLM-generated diets.

---

## Chromosome Representation

Same structure as GA-Food:

| Symbol | Description | Value |
|---|---|---|
| D | Number of days | 5 |
| M | Meal types per day | 6 |
| G | Total genes (D × M) | 30 |

**x** = (x₁, x₂, ..., x₃₀)

Each gene *x<sub>g</sub>* stores one meal instance containing:
- A list of food items (name and quantity in grams)
- Precomputed nutrient totals (per meal)
- Precomputed environmental footprint totals (per meal)

Gene-to-day-and-meal mapping is identical to GA-Food (genes 1–6 → day 1, ..., genes 25–30 → day 5; within each day: Café da Manhã, Lanche da Manhã, Almoço, Lanche da Tarde, Jantar, Ceia).

---

## Pool Construction

Pools are constructed identically to GA-Food, from all 50 base diets:

### Meal Pool

- One candidate meal per (base diet, day, meal type) triplet
- Each candidate stores: items list, aggregated nutrients, aggregated footprints
- Optional meal types (Lanche da Manhã, Lanche da Tarde, Ceia) include an empty meal candidate
- Grouped by meal type: `meal_pool[meal_type]`

### Food Pool

- Individual food items deduplicated per meal type from all base diets
- `food_pool[meal_type]` used by **local mutation** (add/replace/remove operations within a meal's item list)

The food pool exists in meal-level mode as well: local mutation still operates at food-level granularity within a gene.

---

## Fitness Function

Identical to GA-Food:

F(**x**) = - [ *w<sub>n</sub>* · P<sub>nut</sub>(**x**) + *w<sub>e</sub>* · P<sub>env</sub>(**x**) + P<sub>share</sub>(**x**) ]

All three penalty components (nutritional, environmental, energy-share) use the same formulas, parameters, and targets as GA-Food. See the [GA-Food formulation](ga-food.md) for the complete penalty definitions. The key constants are repeated below for reference:

| Symbol | Description | Value |
|---|---|---|
| *w<sub>n</sub>* | Nutritional criterion weight | 1.0 |
| *w<sub>e</sub>* | Environmental criterion weight | 1.0 |
| λ | Nutrient penalty factor (`NUTRIENT_PENALTY_FACTOR`) | 10,007 |
| ε | Energy upper flexibility (`ENERGY_UPPER_FLEXIBILITY`) | 0.05 |
| η | Energy-share penalty weight (`MEAL_ENERGY_SHARE_PENALTY_WEIGHT`) | 200 |
| *r*<sub>carbon</sub> | Carbon footprint normalization reference | 2,000 |

---

## Evolution Loop

### Population Initialization

- **Population size:** 60
- **Seed with base chromosomes:** Yes (`seed_with_base_chromosomes = True`)
  - Base chromosomes are built from the original 50 LLM-generated diets
  - Each base diet is converted to a 30-gene chromosome with precomputed nutrient/footprint totals
  - These occupy up to 50 slots in the initial population; the remainder are filled by random sampling from the meal pool
  - If base chromosomes exceed the population size, only the first 60 are used

### Selection

- **Tournament selection** with tournament size = 3
- Identical to GA-Food

### Elitism

- **Elitism rate:** 5% (`ELITISM_RATE`)
- Floor of 5% × 60 = 3 elite individuals, minimum 1

### Offspring Generation (per generation)

1. Copy elite individuals to new population
2. While population size < 60:
   a. Select parent 1 via tournament (size 3)
   b. Select parent 2 via tournament (size 3)
   c. Apply crossover to produce offspring
   d. Apply crossover repair if enabled
   e. Apply mutation with current rates
   f. Add offspring to new population

### Crossover

- **Strategy:** by-meal (`by_meal`)
- For each of the 30 gene positions, the offspring inherits from parent 1 with 50% probability and parent 2 with 50% probability (independent coin flip per gene)
- Same mechanism as GA-Food

### Crossover Repair (Energy Limit Enforcement)

Identical to GA-Food: greedy largest-reduction replacement per day, max 12 attempts per day, triggered when any day exceeds 2,100 kcal. See [GA-Food: Crossover Repair](ga-food.md#crossover-repair-energy-limit-enforcement) for the full algorithm.

### Mutation (Meal-Level Specific)

In meal-level mode, **both global and local mutation are enabled**.

For each gene independently, a random number *p* ∈ [0, 1) is drawn:
- If *p* < `global_rate`: apply **global mutation**
- If *p* < `global_rate` + `local_rate`: apply **local mutation**
- Otherwise: no mutation

**Global mutation (replaces the entire meal):**
- Replace the gene's entire meal instance with a random candidate from `meal_pool[meal_type]`
- The replacement is a deep copy, including all precomputed nutrients and footprints
- This operation discards all food items in the current meal

**Local mutation (modifies individual foods within the meal):**
- Same operations as GA-Food: replace, add, remove, with fallback logic
- After mutation, the meal's nutrient/footprint totals are recalculated from the updated item list

### Hypermutation

When the best fitness does not improve for **15 consecutive generations** (`HYPERMUTATION_TRIGGER = 15`), mutation rates are increased:

| Rate | Normal | Hypermutation |
|---|---|---|
| Global mutation | 5% | 15% |
| Local mutation | 15% | 30% |

Hypermutation is reset to normal rates when fitness improves by at least 1e-6 (`PLATEAU_TOLERANCE`).

### Stopping Criteria

The GA terminates when either:
- **20 generations** without fitness improvement (stagnation limit for meal-level), OR
- **120 generations** total (absolute limit for meal-level)

A generation is considered stagnant if the best fitness does not improve by at least `PLATEAU_TOLERANCE = 1e-6`.

---

## Key Differences from GA-Food

| Parameter | GA-Food | GA-Meal |
|---|---|---|
| Population size | 45 | 60 |
| Max generations | 90 | 120 |
| Stagnation limit | 18 | 20 |
| Global mutation (normal) | Disabled | 5% |
| Global mutation (hyper) | Disabled | 15% |
| Seed with base chromosomes | No | Yes |
| Local mutation (normal) | 15% | 15% |
| Local mutation (hyper) | 30% | 30% |

GA-Meal has a larger population, runs longer, and uses global mutation to explore the meal-pool search space. Seeding with base chromosomes provides a warm start, leveraging the LLM-generated solutions as high-quality initial candidates.

---

## Complete Parameter Table

| Parameter | Value |
|---|---|
| Population size | 60 |
| Tournament size | 3 |
| Elitism rate | 5% |
| Max generations | 120 |
| Stagnation limit | 20 |
| Hypermutation trigger | 15 generations |
| Plateau tolerance | 1e-6 |
| Global mutation rate (normal) | 5% |
| Global mutation rate (hyper) | 15% |
| Local mutation rate (normal) | 15% |
| Local mutation rate (hyper) | 30% |
| Seed with base chromosomes | Yes |
| Crossover strategy | `by_meal` |
| Crossover repair | Enabled (max 12 attempts/day) |
| Energy ceiling for repair | 2,100 kcal |
| Local mutation operations | replace, add, remove |
| Number of independent runs | 10 per profile |
| Nutritional criterion weight (*w<sub>n</sub>*) | 1.0 |
| Environmental criterion weight (*w<sub>e</sub>*) | 1.0 |
| Nutrient penalty factor (λ) | 10,007 |
| Energy upper flexibility (ε) | 0.05 |
| Energy-share penalty weight (η) | 200 |
| Carbon footprint normalization reference | 2,000 |
| Days per plan (D) | 5 |
| Meals per day (M) | 6 |
| Total genes (G) | 30 |

---

## Output

Same as GA-Food: the best chromosome from each of the 10 independent runs is saved in a single JSON file containing all 10 optimized diets per profile.