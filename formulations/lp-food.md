# LP-Food: Linear Programming at Food-Level Granularity

## Overview

LP-Food optimizes a diet by selecting **individual foods** and their quantities using Linear Programming. Each decision variable represents the daily grams of a specific food item. The objective is to minimize the total carbon footprint subject to nutritional constraints. This formulation does not preserve meal structure: the output is a single pool of foods per day without grouping into meal types.

---

## Decision Variables

Let *n* be the total number of foods available in both the TBCA nutritional database and the environmental footprint database. Each decision variable *x<sub>i</sub>* (*i* = 1, ..., *n*) represents the **daily grams** of food *i* in the optimized diet.

---

## Objective Function

Minimize the total daily carbon footprint:

min<sub>**x**</sub> ∑ (*c<sub>i</sub>* · *x<sub>i</sub>*)

where *c<sub>i</sub>* is the carbon footprint **per gram** of food *i*, computed as:

*c<sub>i</sub>* = (carbon_footprint<sub>*i*</sub>) / 100

The environmental footprint database stores values per 100 g of each food (`GRAMS_REFERENCE_FOOTPRINT = 100`).

---

## Constraints

### Nutritional Minimum Constraints

For each nutrient *k* with a minimum target *m<sub>k</sub>*:

∑ (*a<sub>k,i</sub>* · *x<sub>i</sub>*) ≥ *m<sub>k</sub>*

where *a<sub>k,i</sub>* is the amount of nutrient *k* per gram of food *i*, computed from the TBCA database (values per 100 g divided by 100; `GRAMS_REFERENCE_TBCA = 100`).

### Nutritional Maximum Constraints

For each nutrient *k* with an upper limit *u<sub>k</sub>*:

∑ (*a<sub>k,i</sub>* · *x<sub>i</sub>*) ≤ *u<sub>k</sub>*

Upper limit computation:

| Nutrient | Formula | Value |
|---|---|---|
| Energy | 2,000 × 1.05 | 2,100 kcal |
| Sodium | 2,300 × 1.00 | 2,300 mg |
| Cholesterol | 300 × 1.00 | 300 mg |

The energy tolerance factor is `ENERGY_UPPER_FLEXIBILITY = 0.05`. Sodium and cholesterol have tolerance 1.00 (no flexibility).

### Non-negativity

*x<sub>i</sub>* ≥ 0  (for all *i* = 1, ..., *n*)

---

## Complete Formulation

min<sub>**x**</sub> ∑ (*c<sub>i</sub>* · *x<sub>i</sub>*)

subject to:

∑ (*a<sub>k,i</sub>* · *x<sub>i</sub>*) ≥ *m<sub>k</sub>* (for all *k* ∈ K<sub>min</sub>)

∑ (*a<sub>k,i</sub>* · *x<sub>i</sub>*) ≤ *u<sub>k</sub>* (for all *k* ∈ K<sub>max</sub>)

*x<sub>i</sub>* ≥ 0  (for all *i*)

### Sets

- K<sub>min</sub> (16 nutrients with minimum targets): Energy, Carbohydrate, Protein, Lipids, Fiber, Vitamin A (RE), Vitamin C, Vitamin D, Vitamin E, Thiamine, Riboflavin, Niacin, Vitamin B6, Vitamin B12, Calcium, Magnesium
- K<sub>max</sub> (3 nutrients with upper limits): Energy, Sodium, Cholesterol

Note: Energy appears in both sets — it has a minimum of 2,000 kcal and a maximum of 2,100 kcal.

---

## Nutritional Targets

### Minimum Targets (K<sub>min</sub>)

| Nutrient | Code in system | Minimum (*m<sub>k</sub>*) | Unit |
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

### Upper Limits (K<sub>max</sub>)

| Nutrient | Code in system | Target | Tolerance | Upper limit (*u<sub>k</sub>*) | Unit |
|---|---|---|---|---|---|
| Energy | Energia | 2,000 | 1.05 | 2,100 | kcal |
| Sodium | Sódio | 2,300 | 1.00 | 2,300 | mg |
| Cholesterol | Colesterol | 300 | 1.00 | 300 | mg |

---

## Constraint Relaxation

If the LP is **infeasible** (no combination of foods satisfies all constraints simultaneously), the implementation applies a relaxed formulation.

### Relaxed Formulation

Nonnegative slack variables *s<sub>r</sub>* (*r* = 1, ..., R) are added to each inequality constraint:

min<sub>**x**, **s**</sub> [ ∑ (*c<sub>i</sub>* · *x<sub>i</sub>*) + M ∑ *s<sub>r</sub>* ]

subject to:

A**x** - **s** ≤ **b**,   **x** ≥ 0,   **s** ≥ 0

where:

| Symbol | Description |
|---|---|
| A**x** ≤ **b** | Stacked system of all inequality constraints (min and max, converted to ≤ form) |
| R | Total number of inequality constraints |
| M | 10,000 (`BIG_M_PENALTY`) |
| *s<sub>r</sub>* | Slack variable for the *r*-th constraint |

**How the stacking works:**
- Minimum constraints (∑ *a<sub>k,i</sub>* · *x<sub>i</sub>* ≥ *m<sub>k</sub>*) are negated: -∑ *a<sub>k,i</sub>* · *x<sub>i</sub>* ≤ -*m<sub>k</sub>*
- Maximum constraints (∑ *a<sub>k,i</sub>* · *x<sub>i</sub>* ≤ *u<sub>k</sub>*) stay as-is

The relaxed solution allows the minimum necessary violation of nutritional bounds, penalized proportionally by M. This produces a best-effort solution when the original problem has no feasible region.

---

## Solver

| Parameter | Value |
|---|---|
| Solver | HiGHS (via `scipy.optimize.linprog`) |
| Variable type | Continuous (grams) |
| Big-M penalty | 10,000 |

---

## Output Processing

1. The solver returns a vector **x*** of daily food quantities
2. Foods with *x<sub>i</sub>** < 1 gram are discarded (threshold)
3. Remaining foods are rounded to 1 decimal place
4. All selected foods are grouped into a single meal called "Refeição LP"
5. The same food selection is replicated across all 5 days (identical daily plan)

### Output Structure

The output is a 5-day plan where each day contains a single aggregated meal ("Refeição LP") with all selected foods and their quantities. LP-Food does **not** produce distinct meals (breakfast, lunch, dinner, etc.); it produces a nutritionally-optimized food pool.

---

## Key Characteristics

| Aspect | Description |
|---|---|
| Decision unit | Individual food items (grams/day) |
| Meal structure | Not preserved (single aggregated meal) |
| Energy share constraints | Not applied (no meal types) |
| Optimization type | Exact (global optimum via HiGHS) |
| Cultural coherence | Not considered |
| Number of days | 5 (identical daily plan) |
| Typical result | 10 unique foods across all profiles |