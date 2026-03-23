# LP-Food: Linear Programming at Food-Level Granularity

## Overview

LP-Food optimizes a diet by selecting **individual foods** and their quantities using Linear Programming. Each decision variable represents the daily grams of a specific food item. The objective is to minimize the total carbon footprint subject to nutritional constraints. This formulation does not preserve meal structure: the output is a single pool of foods per day without grouping into meal types.

---

## Decision Variables

Let *n* be the total number of foods available in both the TBCA nutritional database and the environmental footprint database. Each decision variable x_i (i = 1, ..., n) represents the **daily grams** of food *i* in the optimized diet.

---

## Objective Function

Minimize the total daily carbon footprint:

$$
\min_{\mathbf{x}} \sum_{i=1}^{n} c_i \cdot x_i
$$

where c_i is the carbon footprint **per gram** of food *i*, computed as:

$$
c_i = \frac{\text{carbon\\_footprint}_i}{100}
$$

The environmental footprint database stores values per 100 g of each food (`GRAMS_REFERENCE_FOOTPRINT = 100`).

---

## Constraints

### Nutritional Minimum Constraints

For each nutrient *k* with a minimum target m_k:

$$
\sum_{i=1}^{n} a_{k,i} \cdot x_i \geq m_k
$$

where a_{k,i} is the amount of nutrient *k* per gram of food *i*, computed from the TBCA database (values per 100 g divided by 100; `GRAMS_REFERENCE_TBCA = 100`).

### Nutritional Maximum Constraints

For each nutrient *k* with an upper limit u_k:

$$
\sum_{i=1}^{n} a_{k,i} \cdot x_i \leq u_k
$$

Upper limit computation:

| Nutrient | Formula | Value |
|---|---|---|
| Energy | 2,000 × 1.05 | 2,100 kcal |
| Sodium | 2,300 × 1.00 | 2,300 mg |
| Cholesterol | 300 × 1.00 | 300 mg |

The energy tolerance factor is `ENERGY_UPPER_FLEXIBILITY = 0.05`. Sodium and cholesterol have tolerance 1.00 (no flexibility).

### Non-negativity

$$
x_i \geq 0 \quad \forall \; i = 1, \ldots, n
$$

---

## Complete Formulation

$$
\min_{\mathbf{x}} \sum_{i=1}^{n} c_i \cdot x_i
$$

subject to:

$$
\sum_{i=1}^{n} a_{k,i} \cdot x_i \geq m_k \quad \forall \; k \in K_{\min}
$$

$$
\sum_{i=1}^{n} a_{k,i} \cdot x_i \leq u_k \quad \forall \; k \in K_{\max}
$$

$$
x_i \geq 0 \quad \forall \; i
$$

### Sets

- **K_min** (16 nutrients with minimum targets): Energy, Carbohydrate, Protein, Lipids, Fiber, Vitamin A (RE), Vitamin C, Vitamin D, Vitamin E, Thiamine, Riboflavin, Niacin, Vitamin B6, Vitamin B12, Calcium, Magnesium
- **K_max** (3 nutrients with upper limits): Energy, Sodium, Cholesterol

Note: Energy appears in both sets — it has a minimum of 2,000 kcal and a maximum of 2,100 kcal.

---

## Nutritional Targets

### Minimum Targets (K_min)

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

### Upper Limits (K_max)

| Nutrient | Code in system | Target | Tolerance | Upper limit (u_k) | Unit |
|---|---|---|---|---|---|
| Energy | Energia | 2,000 | 1.05 | 2,100 | kcal |
| Sodium | Sódio | 2,300 | 1.00 | 2,300 | mg |
| Cholesterol | Colesterol | 300 | 1.00 | 300 | mg |

---

## Constraint Relaxation

If the LP is **infeasible** (no combination of foods satisfies all constraints simultaneously), the implementation applies a relaxed formulation.

### Relaxed Formulation

Nonnegative slack variables s_r (r = 1, ..., R) are added to each inequality constraint:

$$
\min_{\mathbf{x}, \mathbf{s}} \left( \sum_{i=1}^{n} c_i \cdot x_i + M \sum_{r=1}^{R} s_r \right)
$$

subject to:

$$
A\mathbf{x} - \mathbf{s} \leq \mathbf{b}, \quad \mathbf{x} \geq 0, \quad \mathbf{s} \geq 0
$$

where:

| Symbol | Description |
|---|---|
| A**x** ≤ **b** | Stacked system of all inequality constraints (min and max, converted to ≤ form) |
| R | Total number of inequality constraints |
| M | 10,000 (`BIG_M_PENALTY`) |
| s_r | Slack variable for the *r*-th constraint |

**How the stacking works:**
- Minimum constraints (∑ a_{k,i} x_i ≥ m_k) are negated: −∑ a_{k,i} x_i ≤ −m_k
- Maximum constraints (∑ a_{k,i} x_i ≤ u_k) stay as-is

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

1. The solver returns a vector **x**\* of daily food quantities
2. Foods with x_i\* < 1 gram are discarded (threshold)
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
