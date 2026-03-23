# GA-Food: Genetic Algorithm at Food-Level Granularity

## Overview

GA-Food optimizes a 5-day diet plan by manipulating **individual foods** within meals. Each food item can be replaced, added, or removed during mutation, giving the algorithm maximum freedom to recombine ingredients across the entire nutritional search space. Global mutation (replacing entire meals) is **disabled** in this mode.

---

## Chromosome Representation

A chromosome encodes a complete 5-day food plan:

| Symbol | Description | Value |
|---|---|---|
| D | Number of days | 5 |
| M | Meal types per day | 6 |
| G | Total genes (D × M) | 30 |

The chromosome is a vector of G = 30 genes:

**x** = (x_1, x_2, ..., x_30)

Each gene x_g stores one meal instance containing:
- A list of food items (name and quantity in grams)
- Precomputed nutrient totals (per meal)
- Precomputed environmental footprint totals (per meal)

Genes are arranged sequentially: genes 1–6 correspond to the 6 meals of day 1, genes 7–12 to day 2, and so on. Within each day, the meal order is: Café da Manhã, Lanche da Manhã, Almoço, Lanche da Tarde, Jantar, Ceia.

---

## Pool Construction

Before the GA runs, two pools are extracted from all 50 base diets of the target profile:

### Meal Pool

For each base diet, each day, each meal type:
- Extract the list of food items
- Compute total nutrients and footprints using TBCA data (per 100 g reference)
- Store as a candidate meal: `{itens, nutrientes, pegadas}`

For optional meal types (Lanche da Manhã, Lanche da Tarde, Ceia), an empty meal candidate is added.

The meal pool is grouped by meal type: `meal_pool[meal_type]` contains all candidate meals of that type.

### Food Pool

Individual food items are extracted from all meals across all base diets, deduplicated per meal type:
- `food_pool[meal_type]` contains unique food items that appeared in any meal of that type
- Each food item stores its name, quantity (grams), and per-item nutritional/footprint values
- Used exclusively by the local mutation operator

---

## Fitness Function

The GA **maximizes** a fitness value defined as the negative of a weighted penalty sum:

$$
F(\mathbf{x}) = -\Big( w_n \cdot P_{\text{nut}}(\mathbf{x}) + w_e \cdot P_{\text{env}}(\mathbf{x}) + P_{\text{share}}(\mathbf{x}) \Big)
$$

where:

| Symbol | Description | Value |
|---|---|---|
| w_n | Nutritional criterion weight | 1.0 |
| w_e | Environmental criterion weight | 1.0 |
| P_nut | Nutritional penalty | see below |
| P_env | Environmental penalty | see below |
| P_share | Energy-share penalty | see below |

Higher fitness (closer to zero) indicates a better diet. A perfect diet with no violations has fitness = −P_env (the irreducible environmental cost).

---

## Nutritional Penalty (P_nut)

### Daily Averages

For each nutrient *k*, the mean daily intake is computed from the chromosome:

$$
\bar{v}_k = \frac{1}{D} \sum_{g=1}^{G} v_{g,k}
$$

where v_{g,k} is the amount of nutrient *k* contributed by gene *g*.

### Penalty Computation

Nutrients are partitioned into:

- **K_min** (16 nutrients): nutrients with minimum daily targets
- **K_max** (3 nutrients): nutrients with upper daily limits

**For nutrients only in K_min** (e.g., protein, fiber):

$$
\text{penalty}_k = \max\!\left(0,\; \frac{m_k - \bar{v}_k}{m_k}\right) \times \lambda
$$

**For nutrients only in K_max** (e.g., sodium, cholesterol):

$$
\text{penalty}_k = \max\!\left(0,\; \frac{\bar{v}_k - u_k}{u_k}\right) \times \lambda
$$

**For nutrients in both K_min and K_max** (energy only):
- If v̄_k < m_k: penalty = ((m_k − v̄_k) / m_k) × λ
- If v̄_k > u_k × (1 + ε): penalty = ((v̄_k − u_k × (1 + ε)) / u_k) × λ
- Otherwise: no penalty

where:

| Symbol | Description | Value |
|---|---|---|
| λ | Nutrient penalty factor (`NUTRIENT_PENALTY_FACTOR`) | 10,007 |
| ε | Energy upper flexibility (`ENERGY_UPPER_FLEXIBILITY`) | 0.05 |
| m_k | Minimum target for nutrient *k* | see table below |
| u_k | Upper limit for nutrient *k* | see table below |

The total nutritional penalty is:

$$
P_{\text{nut}}(\mathbf{x}) = \sum_{k} \text{penalty}_k
$$

Note: The factor λ = 10,007 is already applied inside each individual penalty_k.

### Nutritional Targets

#### Minimum Targets (K_min)

| Nutrient | Code in system | Minimum (m_k) | Unit |
|---|---|---|---|
| Energy | Energia | 2,000 | kcal |
| Carbohydrate | Carboidrato total | 302.5 | g |
| Protein | Proteína | 110.0 | g |
| Lipids | Lipídios | 61.11 | g |
| Fiber | Fibra alimentar | 25.0 | g |
| Vitamin A (RE) | Vitamina A (RE) | 900.0 | µg |
| Vitamin C | Vitamina C | 90.0 | mg |
| Vitamin D | Vitamina D | 15.0 | µg |
| Vitamin E | Alfa-tocoferol (Vitamina E) | 15.0 | mg |
| Thiamine | Tiamina | 1.2 | mg |
| Riboflavin | Riboflavina | 1.3 | mg |
| Niacin | Niacina | 16.0 | mg |
| Vitamin B6 | Vitamina B6 | 1.3 | mg |
| Vitamin B12 | Vitamina B12 | 2.4 | µg |
| Calcium | Cálcio | 1,000 | mg |
| Magnesium | Magnésio | 420.0 | mg |

#### Upper Limits (K_max)

| Nutrient | Code in system | Target | Tolerance | Upper limit (u_k) | Unit |
|---|---|---|---|---|---|
| Energy | Energia | 2,000 | 1.05 | 2,100 | kcal |
| Sodium | Sódio | 2,300 | 1.00 | 2,300 | mg |
| Cholesterol | Colesterol | 300 | 1.00 | 300 | mg |

---

## Environmental Penalty (P_env)

The environmental penalty uses the mean daily footprint of the chromosome:

$$
\bar{z}_f = \frac{1}{D} \sum_{g=1}^{G} z_{g,f}
$$

where z_{g,f} is the footprint *f* contributed by gene *g*.

The penalty is:

$$
P_{\text{env}}(\mathbf{x}) = \sum_{f \in \mathcal{F}} \alpha_f \cdot \frac{\bar{z}_f}{r_f}
$$

| Symbol | Description | Value |
|---|---|---|
| F | Set of active footprints | {carbon_footprint} (in experiments) |
| α_f | Weight for footprint *f* | 1.0 (default) |
| r_f | Normalization reference for footprint *f* | see table below |

### Normalization References

| Footprint | Reference (r_f) | Normalization |
|---|---|---|
| Carbon (gCO₂eq/day) | 2,000 | ratio: z̄_f / r_f |
| Water (L/day) | 1,500 | ratio |
| Ecological (points/day) | 10 | ratio |

In the experiments, only carbon footprint was active.

---

## Energy-Share Penalty (P_share)

Controls the distribution of calories among meal types within each day. For day *d* and meal type *t*:

$$
s_{d,t} = \frac{E_{d,t}}{\sum_{j=1}^{M} E_{d,j}}
$$

where E_{d,t} is the energy of meal type *t* on day *d*.

The penalty is:

$$
P_{\text{share}}(\mathbf{x}) = \eta \sum_{d=1}^{D} \sum_{t=1}^{M} \left[ \max\!\left(0,\; \frac{s_t^{\min} - s_{d,t}}{s_t^{\min}}\right) + \max\!\left(0,\; \frac{s_{d,t} - s_t^{\max}}{s_t^{\max}}\right) \right]
$$

| Symbol | Description | Value |
|---|---|---|
| η | Energy-share penalty weight | 200 (`MEAL_ENERGY_SHARE_PENALTY_WEIGHT`) |

When s_t^min = 0 (optional meals), only the upper-bound term is active. If total daily energy is ≤ 0, the day is skipped.

### Energy Share Ranges

| Meal Type | Code in system | Min Share | Max Share |
|---|---|---|---|
| Breakfast | Café da Manhã | 15% | 25% |
| Morning Snack | Lanche da Manhã | 0% | 10% |
| Lunch | Almoço | 25% | 35% |
| Afternoon Snack | Lanche da Tarde | 0% | 15% |
| Dinner | Jantar | 20% | 30% |
| Supper | Ceia | 0% | 10% |

---

## Evolution Loop

### Population Initialization

- **Population size:** 45
- **Seed with base chromosomes:** No (disabled in food-level mode; `seed_with_base_chromosomes = False`)
- All individuals are generated by randomly sampling one meal from the meal pool for each of the 30 gene positions

### Selection

- **Tournament selection** with tournament size = 3
- Each parent is selected by sampling 3 individuals at random and choosing the one with highest fitness
- Called twice per offspring (once for each parent)

### Elitism

- **Elitism rate:** 5% (`ELITISM_RATE`)
- Floor of 5% × 45 = 2 elite individuals, minimum 1
- Elite individuals are deep-copied unchanged to the next generation

### Offspring Generation (per generation)

1. Copy elite individuals to new population
2. While population size < 45:
   a. Select parent 1 via tournament (size 3)
   b. Select parent 2 via tournament (size 3)
   c. Apply crossover to produce offspring
   d. Apply crossover repair if enabled
   e. Apply mutation with current rates
   f. Add offspring to new population

### Crossover

- **Strategy:** by-meal (`by_meal`)
- For each of the 30 gene positions, the offspring inherits from parent 1 with 50% probability and from parent 2 with 50% probability (independent coin flip per gene)
- Each inherited gene is a deep copy

### Crossover Repair (Energy Limit Enforcement)

After crossover, if any day exceeds the energy ceiling (2,100 kcal), a greedy repair is applied:

**Algorithm (per day):**
1. Compute total daily energy for the day
2. If daily energy ≤ 2,100 kcal, skip
3. Otherwise, search all 6 meals of that day:
   - For each meal position, try all candidate meals of the same type from the meal pool
   - Find the substitution that gives the **largest energy reduction** (greedy)
4. Apply the best substitution found
5. Repeat up to 12 times per day (`REPAIR_MAX_ATTEMPTS_PER_DAY = 12`)
6. Stop early if daily energy falls within the ceiling or no improvement is found

### Mutation (Food-Level Specific)

In food-level mode, **global mutation is disabled** (`enable_global_mutation = False`).

For each gene independently, a random number *p* ∈ [0, 1) is drawn:
- If p < 0 (global disabled): not applied
- If p < 0 + local_rate: apply **local mutation**
- Otherwise: no mutation

**Local mutation operations** (one is randomly selected per gene):
- **Replace:** Pick a random food position within the meal, swap it with a random food from `food_pool[meal_type]`
- **Add:** Append a random food from `food_pool[meal_type]` to the meal's item list
- **Remove:** Delete a random food from the meal's item list (only if more than zero items exist)
- **Fallback:** If the selected operation cannot be applied (e.g., remove on empty meal), it falls back to replace (if items exist) or add (if empty)

After any local mutation, the meal's nutrient and footprint totals are **recalculated** from the updated item list using TBCA data.

### Hypermutation

When the best fitness does not improve for **15 consecutive generations** (`HYPERMUTATION_TRIGGER = 15`), mutation rates are increased:

| Rate | Normal | Hypermutation |
|---|---|---|
| Local mutation | 15% | 30% |

Hypermutation is reset to normal rates when fitness improves by at least 1e-6 (`PLATEAU_TOLERANCE`).

### Stopping Criteria

The GA terminates when either:
- **18 generations** without fitness improvement (stagnation limit for food-level), OR
- **90 generations** total (absolute limit for food-level)

A generation is considered stagnant if the best fitness does not improve by at least `PLATEAU_TOLERANCE = 1e-6`.

---

## Complete Parameter Table

| Parameter | Value |
|---|---|
| Population size | 45 |
| Tournament size | 3 |
| Elitism rate | 5% |
| Max generations | 90 |
| Stagnation limit | 18 |
| Hypermutation trigger | 15 generations |
| Plateau tolerance | 1e-6 |
| Local mutation rate (normal) | 15% |
| Local mutation rate (hyper) | 30% |
| Global mutation | Disabled |
| Seed with base chromosomes | No |
| Crossover strategy | by_meal |
| Crossover repair | Enabled (max 12 attempts/day) |
| Energy ceiling for repair | 2,100 kcal |
| Local mutation operations | replace, add, remove |
| Number of independent runs | 10 per profile |
| Nutritional criterion weight (w_n) | 1.0 |
| Environmental criterion weight (w_e) | 1.0 |
| Nutrient penalty factor (λ) | 10,007 |
| Energy upper flexibility (ε) | 0.05 |
| Energy-share penalty weight (η) | 200 |
| Carbon footprint normalization reference | 2,000 |
| Days per plan (D) | 5 |
| Meals per day (M) | 6 |
| Total genes (G) | 30 |

---

## Output

The best chromosome from each of the 10 independent runs is converted back into a structured 5-day diet plan in JSON format. Each file contains all 10 resulting diets, enabling statistical analysis of optimization quality across stochastic runs.
