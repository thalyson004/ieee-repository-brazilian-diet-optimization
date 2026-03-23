# LP-Food: Linear Programming at Food-Level Granularity

## Overview

LP-Food optimizes a diet by selecting **individual foods** and their quantities using Linear Programming. Each decision variable represents the daily grams of a specific food item. The objective is to minimize the total carbon footprint subject to nutritional constraints. This formulation does not preserve meal structure: the output is a single pool of foods per day without grouping into meal types.

---

## Decision Variables

Let $n$ be the total number of foods available in both the TBCA nutritional database and the environmental footprint database. Each decision variable $x_i$ ($i = 1, \ldots, n$) represents the **daily grams** of food $i$ in the optimized diet.

---

## Objective Function

Minimize the total daily carbon footprint:

$$\min_{\mathbf{x}} \sum_{i=1}^{n} c_i \cdot x_i$$

where $c_i$ is the carbon footprint **per gram** of food $i$, computed as:

$$c_i = \frac{\text{carbon\_footprint}_i}{100}$$

The environmental footprint database stores values **per 100 g** of each food.

---

## Constraints

### Nutritional Minimum Constraints

For each nutrient $k$ with a minimum target $m_k$:

$$\sum_{i=1}^{n} a_{k,i} \cdot x_i \geq m_k$$

where $a_{k,i}$ is the amount of nutrient $k$ per gram of food $i$, computed from the TBCA database (values per 100 g divided by 100).

### Nutritional Maximum Constraints

For each nutrient $k$ with an upper limit:

$$\sum_{i=1}^{n} a_{k,i} \cdot x_i \leq u_k$$

where $u_k$ is the upper limit for nutrient $k$.

**Special cases:**
- **Energy:** $u_k = 2{,}000 \times 1.05 = 2{,}100$ kcal (5% tolerance above the target)
- **Sodium:** $u_k = 2{,}300$ mg (no additional tolerance)
- **Cholesterol:** $u_k = 300$ mg (no additional tolerance)

### Non-negativity

$$x_i \geq 0 \quad \forall \; i = 1, \ldots, n$$

---

## Complete Formulation

$$\begin{aligned}
\min_{\mathbf{x}} \quad & \sum_{i=1}^{n} c_i \cdot x_i \\
\text{s.t.} \quad & \sum_{i=1}^{n} a_{k,i} \cdot x_i \geq m_k, && \forall \; k \in K_{min} \\
& \sum_{i=1}^{n} a_{k,i} \cdot x_i \leq u_k, && \forall \; k \in K_{max} \\
& x_i \geq 0, && \forall \; i
\end{aligned}$$

### Sets

- $K_{min} = \{$Energy, Carbohydrate, Protein, Lipids, Fiber, Vitamin A, Vitamin C, Vitamin D, Vitamin E, Thiamine, Riboflavin, Niacin, Vitamin B6, Vitamin B12, Calcium, Magnesium$\}$
- $K_{max} = \{$Energy, Sodium, Cholesterol$\}$

Note that Energy appears in both sets: it has a minimum of 2,000 kcal and a maximum of 2,100 kcal.

---

## Nutritional Targets

| Nutrient | Minimum ($m_k$) | Maximum ($u_k$) |
|---|---|---|
| Energy | 2,000 kcal | 2,100 kcal |
| Carbohydrate | 302.5 g | — |
| Protein | 110.0 g | — |
| Lipids | 61.11 g | — |
| Fiber | 25.0 g | — |
| Vitamin A (RE) | 900.0 µg | — |
| Vitamin C | 90.0 mg | — |
| Vitamin D | 15.0 µg | — |
| Vitamin E | 15.0 mg | — |
| Thiamine | 1.2 mg | — |
| Riboflavin | 1.3 mg | — |
| Niacin | 16.0 mg | — |
| Vitamin B6 | 1.3 mg | — |
| Vitamin B12 | 2.4 µg | — |
| Calcium | 1,000 mg | — |
| Magnesium | 420.0 mg | — |
| Sodium | — | 2,300 mg |
| Cholesterol | — | 300 mg |

---

## Constraint Relaxation

If the LP is **infeasible** (no combination of foods satisfies all constraints simultaneously), the implementation applies a relaxed formulation.

### Relaxed Formulation

Nonnegative slack variables $s_r$ ($r = 1, \ldots, R$) are added to each inequality constraint:

$$\min_{\mathbf{x}, \mathbf{s}} \sum_{i=1}^{n} c_i \cdot x_i + M \sum_{r=1}^{R} s_r$$

subject to:

$$A \mathbf{x} - \mathbf{s} \leq \mathbf{b}$$
$$\mathbf{x} \geq 0, \quad \mathbf{s} \geq 0$$

where:
- $A \mathbf{x} \leq \mathbf{b}$ is the **stacked** system of all inequality constraints (both minimum and maximum, converted to $\leq$ form)
- $R$ is the total number of inequality constraints
- $M = 10{,}000$ is the Big-M penalty constant
- $s_r$ is the slack variable for the $r$-th constraint

**How the stacking works:**
- Minimum constraints ($\sum a_{k,i} x_i \geq m_k$) are converted to $\leq$ form: $-\sum a_{k,i} x_i \leq -m_k$
- Maximum constraints ($\sum a_{k,i} x_i \leq u_k$) stay as-is

**Interpretation:** The relaxed solution allows the minimum necessary violation of nutritional bounds, penalized proportionally by $M$. This produces a **best-effort** solution when the original problem has no feasible region.

---

## Solver

- **Method:** HiGHS (via `scipy.optimize.linprog`)
- **Variable type:** Continuous (grams)

---

## Output Processing

1. The solver returns a vector $\mathbf{x}^*$ of daily food quantities
2. Foods with $x_i^* < 1$ gram are discarded (threshold)
3. Remaining foods are rounded to 1 decimal place
4. All selected foods are grouped into a single meal called "Refeição LP"
5. The same food selection is replicated across all 5 days (identical daily plan)

### Output Structure

The output is a 5-day plan where each day contains a single aggregated meal ("Refeição LP") with all selected foods and their quantities. This means LP-Food does **not** produce distinct meals (breakfast, lunch, dinner, etc.) — it produces a nutritionally-optimized food pool.

---

## Key Characteristics

| Aspect | Description |
|---|---|
| Decision unit | Individual food items (grams/day) |
| Meal structure | Not preserved (single aggregated meal) |
| Energy share constraints | Not applied (no meal types) |
| Optimization type | Exact (global optimum) |
| Cultural coherence | Not considered |
| Typical result | 10 unique foods across all profiles |
