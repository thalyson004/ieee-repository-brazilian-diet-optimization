"""Diagnostic profile-specific LP-Food MILP with observed meal-slot support.

This is not a recipe or clinical meal planner. It assigns individual foods only
to meal types where they occur in the same profile's source plans, applies
corpus-derived daily diversity/repetition/quantity limits, and tests whether
the aggregate nutrient target set can be met. Ingredient compatibility within
a meal is not represented.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp

from diet_optimization.experiments.profile_integrity import load_exclusions, prepare_profile_diets
from diet_optimization.experiments.runner import source_provenance
from diet_optimization.optimization.hyperparameters import (
    DAYS_PER_PLAN,
    GRAMS_REFERENCE_TBCA,
    MEAL_ORDER,
    OPTIONAL_EMPTY_MEAL_TYPES,
)
from diet_optimization.optimization.linear_optimizer import (
    _build_nutrient_constraints,
    _compute_food_vectors,
    food_names_in_diets,
    optimize_food_level,
)
from diet_optimization.optimization.nutritional_targets import load_protocol
from diet_optimization.optimization.pipeline import build_context
from diet_optimization.optimization.utils import load_json_file, parse_quantity_in_grams
from diet_optimization.experiments.diagnostics import evaluate_plan


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("regular", "vegetariana", "vegana")
QUANTILE_RULE = "lower order statistic at floor(q*(n-1)); positive support only"
MILP_TIME_LIMIT_SECONDS = 120.0
MILP_RELATIVE_GAP = 0.01


def lower_order_statistic(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("At least one observed value is required")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be in [0, 1]")
    ordered = sorted(float(value) for value in values)
    return ordered[int(quantile * (len(ordered) - 1))]


def collect_source_support(
    plans: list[dict[str, Any]], context: Any, energy_key: str = "Energia"
) -> dict[str, Any]:
    """Summarize food/slot availability and per-day positive support."""
    food_slot_daily: dict[tuple[str, str], list[float]] = defaultdict(list)
    food_daily: dict[str, list[float]] = defaultdict(list)
    daily_diversity: list[int] = []
    slot_energy_shares: dict[str, list[float]] = {slot: [] for slot in MEAL_ORDER}
    all_foods: set[str] = set()

    for plan in plans:
        for day in plan.values():
            if not isinstance(day, dict):
                continue
            totals_by_slot: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
            for slot, items in day.items():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or not isinstance(item.get("alimento"), str):
                        continue
                    name = item["alimento"]
                    quantity = float(parse_quantity_in_grams(item.get("quantidade", 0)))
                    if quantity <= 0:
                        continue
                    totals_by_slot[slot][name] += quantity
            daily_food_totals: dict[str, float] = defaultdict(float)
            day_foods: set[str] = set()
            energy_by_slot: dict[str, float] = defaultdict(float)
            for slot, food_totals in totals_by_slot.items():
                for name, grams in food_totals.items():
                    all_foods.add(name)
                    day_foods.add(name)
                    daily_food_totals[name] += grams
                    code = context.tbca_map.get(name)
                    entry = context.tbca_database.get(code, {}) if code else {}
                    nutrients = entry.get("nutrientes", {})
                    energy_by_slot[slot] += grams * float(nutrients.get(energy_key, 0.0)) / GRAMS_REFERENCE_TBCA
                    food_slot_daily[(name, slot)].append(grams)
            total_energy = sum(energy_by_slot.values())
            if total_energy > 0:
                for slot in MEAL_ORDER:
                    slot_energy_shares[slot].append(energy_by_slot.get(slot, 0.0) / total_energy)
            for name, grams in daily_food_totals.items():
                food_daily[name].append(grams)
            daily_diversity.append(len(day_foods))

    plan_count = len(plans)
    # Count distinct days on which each food appears in each source plan.
    repeat_counts = {name: [] for name in all_foods}
    for plan in plans:
        counts: dict[str, int] = defaultdict(int)
        for day in plan.values():
            if not isinstance(day, dict):
                continue
            present: set[str] = set()
            for items in day.values():
                if isinstance(items, list):
                    present.update(
                        item["alimento"] for item in items
                        if isinstance(item, dict)
                        and isinstance(item.get("alimento"), str)
                        and float(parse_quantity_in_grams(item.get("quantidade", 0))) > 0
                    )
            for name in present:
                counts[name] += 1
        for name in all_foods:
            repeat_counts[name].append(counts.get(name, 0))

    return {
        "food_names": sorted(all_foods),
        "food_slot_daily_positive_g": dict(food_slot_daily),
        "food_daily_positive_g": dict(food_daily),
        "food_plan_day_counts": repeat_counts,
        "daily_distinct_food_counts": daily_diversity,
        "meal_energy_shares": slot_energy_shares,
        "source_plan_count": plan_count,
    }


def empirical_caps(support: dict[str, Any]) -> dict[str, Any]:
    """Build q95 quantity/repetition caps with max fallback for sparse cells."""
    food_day_caps: dict[str, float] = {}
    slot_day_caps: dict[tuple[str, str], float] = {}
    repeat_caps: dict[str, int] = {}
    for name, positive in support["food_daily_positive_g"].items():
        values = [float(value) for value in positive if value > 0]
        if values:
            q95 = lower_order_statistic(values, 0.95) if len(values) >= 20 else max(values)
            food_day_caps[name] = max(1.0, float(q95))
    for pair, positive in support["food_slot_daily_positive_g"].items():
        values = [float(value) for value in positive if value > 0]
        if values:
            q95 = lower_order_statistic(values, 0.95) if len(values) >= 20 else max(values)
            slot_day_caps[pair] = max(1.0, float(q95))
    for name, counts in support["food_plan_day_counts"].items():
        positive_days = [int(value) for value in counts if value > 0]
        if positive_days:
            repeat_caps[name] = max(1, int(lower_order_statistic(positive_days, 0.95)))
    shares: dict[str, tuple[float, float]] = {}
    for slot, values in support["meal_energy_shares"].items():
        observed = [float(value) for value in values]
        if observed:
            shares[slot] = (
                lower_order_statistic(observed, 0.05),
                lower_order_statistic(observed, 0.95),
            )
    diversity_floor = int(lower_order_statistic(
        [float(value) for value in support["daily_distinct_food_counts"]], 0.25
    ))
    return {
        "food_day_caps_g": food_day_caps,
        "food_slot_day_caps_g": slot_day_caps,
        "food_repeat_caps_days_per_plan": repeat_caps,
        "meal_energy_share_q05_q95": shares,
        "daily_distinct_food_q25_floor": diversity_floor,
        "quantile_rule": QUANTILE_RULE,
    }


def validate_structured_plan(
    plan: dict[str, Any], context: Any, support: dict[str, Any], caps: dict[str, Any]
) -> dict[str, Any]:
    """Independently check the exported plan against every hard model invariant."""
    violations: list[str] = []
    allowed_foods = set(support["food_names"])
    allowed_pairs = set(caps["food_slot_day_caps_g"])
    observed_days = list(plan.values())
    if len(observed_days) != DAYS_PER_PLAN:
        violations.append(f"plan has {len(observed_days)} days; expected {DAYS_PER_PLAN}")
    selected_food_days: dict[str, int] = defaultdict(int)
    for day_idx, day in enumerate(observed_days, start=1):
        food_totals: dict[str, float] = defaultdict(float)
        slot_energy: dict[str, float] = defaultdict(float)
        total_energy = 0.0
        selected: set[str] = set()
        for slot, items in day.items():
            for item in items:
                name = item["alimento"]
                grams = float(item["quantidade"])
                if name not in allowed_foods:
                    violations.append(f"day {day_idx}: food outside profile pool: {name}")
                if (name, slot) not in allowed_pairs:
                    violations.append(f"day {day_idx}: unsupported food/slot pair: {name} / {slot}")
                if grams <= 0:
                    violations.append(f"day {day_idx}: nonpositive quantity for {name}")
                    continue
                selected.add(name)
                food_totals[name] += grams
                if grams > caps["food_slot_day_caps_g"].get((name, slot), 0.0) + 0.03:
                    violations.append(f"day {day_idx}: slot cap exceeded for {name} / {slot}")
                code = context.tbca_map.get(name)
                entry = context.tbca_database.get(code, {}) if code else {}
                energy = grams * float(entry.get("nutrientes", {}).get("Energia", 0.0)) / GRAMS_REFERENCE_TBCA
                slot_energy[slot] += energy
                total_energy += energy
        if len(selected) < caps["daily_distinct_food_q25_floor"]:
            violations.append(f"day {day_idx}: daily diversity floor not met")
        for name, grams in food_totals.items():
            if grams > caps["food_day_caps_g"].get(name, 0.0) + 0.03:
                violations.append(f"day {day_idx}: daily quantity cap exceeded for {name}")
            selected_food_days[name] += 1
        if total_energy <= 0:
            violations.append(f"day {day_idx}: no positive total energy")
        else:
            for slot, (low, high) in caps["meal_energy_share_q05_q95"].items():
                share = slot_energy.get(slot, 0.0) / total_energy
                if share < low - 1e-5 or share > high + 1e-5:
                    violations.append(f"day {day_idx}: empirical energy-share range violated for {slot}")
    for name, observed_repeat in selected_food_days.items():
        allowed_repeat = caps["food_repeat_caps_days_per_plan"].get(name, 0)
        if observed_repeat > allowed_repeat:
            violations.append(f"food repeat cap exceeded for {name}")
    return {
        "status": "passed" if not violations else "failed",
        "checks": [
            "profile candidate pool",
            "profile-observed food/meal slots",
            "slot quantity caps",
            "daily food quantity caps",
            "daily diversity floor",
            "food repeat caps",
            "empirical meal energy-share ranges",
        ],
        "violation_count": len(violations),
        "violations": violations,
    }


def has_feasible_incumbent(
    result: Any,
    matrix: sparse.spmatrix,
    rhs: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    integrality: np.ndarray,
    tolerance: float = 1e-5,
) -> bool:
    """Check primal rows, bounds, and integrality even after a time-limit exit."""
    if result.x is None or len(result.x) != len(lower):
        return False
    values = np.asarray(result.x, dtype=float)
    if not np.all(np.isfinite(values)):
        return False
    if np.any(values < lower - tolerance) or np.any(values > upper + tolerance):
        return False
    integer_columns = np.flatnonzero(integrality)
    if len(integer_columns) and np.any(
        np.abs(values[integer_columns] - np.rint(values[integer_columns])) > tolerance
    ):
        return False
    return bool(np.all(np.asarray(matrix @ values).ravel() <= rhs + tolerance))


def solve_profile(
    profile: str,
    source_plans: list[dict[str, Any]],
    context: Any,
    protocol: dict[str, Any],
    exclusions: dict[str, list[str]],
) -> dict[str, Any]:
    plans, removals = prepare_profile_diets(source_plans, profile, exclusions[profile])
    support = collect_source_support(plans, context)
    caps = empirical_caps(support)
    candidates = food_names_in_diets(plans)
    food_names, footprints, nutrients = _compute_food_vectors(
        context.tbca_map, context.tbca_database, context.footprint_map,
        candidates, protocol["minimum_goals"], protocol["maximum_goals"],
    )
    if not food_names:
        raise ValueError(f"No mapped food candidates remain for {profile}")
    food_index = {name: index for index, name in enumerate(food_names)}
    available_slots = sorted({slot for _, slot in caps["food_slot_day_caps_g"]})
    variable_keys = [
        (day_idx, name, slot)
        for day_idx in range(DAYS_PER_PLAN)
        for name in food_names
        for slot in available_slots
        if (name, slot) in caps["food_slot_day_caps_g"]
    ]
    if not variable_keys:
        raise ValueError(f"No profile-specific food/meal-slot support for {profile}")
    x_count = len(variable_keys)
    food_day_keys = [
        (day_idx, name)
        for day_idx in range(DAYS_PER_PLAN)
        for name in food_names
        if name in caps["food_day_caps_g"]
    ]
    y_index = {key: x_count + index for index, key in enumerate(food_day_keys)}
    y_count = len(food_day_keys)

    n_constraints, n_rhs = _build_nutrient_constraints(
        nutrients, len(food_names), days_multiplier=1,
        minimum_goals=protocol["minimum_goals"], maximum_goals=protocol["maximum_goals"],
    )
    n_nutrients_per_day = n_constraints.shape[0]
    n_nutrients = n_nutrients_per_day * DAYS_PER_PLAN
    base_variable_count = x_count + y_count
    objective = np.zeros(base_variable_count + n_nutrients)
    carbon = footprints.get("carbon_footprint", np.zeros(len(food_names)))
    for idx, (_, name, _) in enumerate(variable_keys):
        objective[idx] = carbon[food_index[name]]
    slack_penalty = float(protocol.get("lp_slack_penalty", 10000.0))
    objective[x_count + y_count:] = slack_penalty
    integrality = np.concatenate([np.zeros(x_count), np.ones(y_count), np.zeros(n_nutrients)])
    lower_bounds = np.zeros(len(objective))
    upper_bounds = np.full(len(objective), np.inf)
    for idx, (day_idx, name, slot) in enumerate(variable_keys):
        upper_bounds[idx] = caps["food_slot_day_caps_g"][(name, slot)]
    for (day_idx, name), index in y_index.items():
        upper_bounds[index] = 1.0

    rows: list[dict[int, float]] = []
    rhs: list[float] = []
    row_kinds: list[str] = []

    nutrient_slack_column_by_constraint: dict[int, int] = {}
    # Enforce every nutritional target independently on every plan day.
    for day_idx in range(DAYS_PER_PLAN):
        for nutrient_row in range(n_constraints.shape[0]):
            row = {
                idx: float(n_constraints[nutrient_row, food_index[name]])
                for idx, (day, name, _) in enumerate(variable_keys)
                if day == day_idx and n_constraints[nutrient_row, food_index[name]] != 0
            }
            rows.append(row)
            rhs.append(float(n_rhs[nutrient_row]))
            row_kinds.append("nutrient")
            nutrient_slack_column_by_constraint[len(rows) - 1] = (
                x_count + y_count + day_idx * n_nutrients_per_day + nutrient_row
            )

    keys_by_day_food: dict[tuple[int, str], list[int]] = defaultdict(list)
    keys_by_day_slot: dict[tuple[int, str], list[int]] = defaultdict(list)
    for idx, (day_idx, name, slot) in enumerate(variable_keys):
        keys_by_day_food[(day_idx, name)].append(idx)
        keys_by_day_slot[(day_idx, slot)].append(idx)

    # Hard empirical daily diversity and food repetition limits.
    diversity_floor = caps["daily_distinct_food_q25_floor"]
    for day_idx in range(DAYS_PER_PLAN):
        row = {y_index[(day_idx, name)]: -1.0
               for name in food_names if (day_idx, name) in y_index}
        rows.append(row)
        rhs.append(float(-diversity_floor))
        row_kinds.append("daily_diversity")
    for name in food_names:
        cap = caps["food_repeat_caps_days_per_plan"].get(name)
        if cap is None:
            continue
        row = {y_index[(day_idx, name)]: 1.0 for day_idx in range(DAYS_PER_PLAN)
               if (day_idx, name) in y_index}
        if row:
            rows.append(row)
            rhs.append(float(cap))
            row_kinds.append("food_repeat_cap")

    # Link selected food/day binaries to finite observed food and slot caps.
    for key, x_indices in keys_by_day_food.items():
        day_idx, name = key
        y = y_index[key]
        row = {idx: 1.0 for idx in x_indices}
        row[y] = -float(caps["food_day_caps_g"][name])
        rows.append(row)
        rhs.append(0.0)
        row_kinds.append("daily_quantity_cap")
        row = {idx: -1.0 for idx in x_indices}
        row[y] = 1.0
        rows.append(row)
        rhs.append(0.0)
        row_kinds.append("binary_selection_link")

    # Daily energy shares are empirical q05-q95 ranges, not fixed clinical advice.
    energy = nutrients["Energia"]
    for day_idx in range(DAYS_PER_PLAN):
        day_vars = [idx for idx, (d, _, _) in enumerate(variable_keys) if d == day_idx]
        for slot in MEAL_ORDER:
            share_range = caps["meal_energy_share_q05_q95"].get(slot)
            slot_vars = keys_by_day_slot.get((day_idx, slot), [])
            if not slot_vars or not share_range:
                if slot not in OPTIONAL_EMPTY_MEAL_TYPES:
                    raise ValueError(f"Mandatory slot {slot!r} lacks empirical energy support in {profile}")
                continue
            low, high = share_range
            if slot not in OPTIONAL_EMPTY_MEAL_TYPES and (low <= 0 or high <= 0):
                raise ValueError(f"Mandatory slot {slot!r} has no positive empirical energy range in {profile}")
            if low > 0:
                row = {idx: float(low) * energy[food_index[variable_keys[idx][1]]]
                       for idx in day_vars}
                for idx in slot_vars:
                    name = variable_keys[idx][1]
                    row[idx] = row.get(idx, 0.0) - energy[food_index[name]]
                rows.append(row)
                rhs.append(0.0)
                row_kinds.append("meal_energy_share_min")
            row = {idx: -float(high) * energy[food_index[variable_keys[idx][1]]]
                   for idx in day_vars}
            for idx in slot_vars:
                name = variable_keys[idx][1]
                row[idx] = row.get(idx, 0.0) + energy[food_index[name]]
            rows.append(row)
            rhs.append(0.0)
            row_kinds.append("meal_energy_share_max")

    matrix = sparse.lil_matrix((len(rows), base_variable_count), dtype=float)
    for row_idx, row in enumerate(rows):
        for column, value in row.items():
            matrix[row_idx, column] = value
    matrix = matrix.tocsr()
    solver_options = {
        "disp": False,
        "time_limit": MILP_TIME_LIMIT_SECONDS,
        "mip_rel_gap": MILP_RELATIVE_GAP,
    }
    strict_result = milp(
        c=objective[:base_variable_count], integrality=integrality[:base_variable_count],
        bounds=Bounds(lower_bounds[:base_variable_count], upper_bounds[:base_variable_count]),
        constraints=LinearConstraint(matrix, np.full(len(rhs), -np.inf), np.asarray(rhs)),
        options=solver_options,
    )
    strict_status = int(strict_result.status)
    strict_feasible = has_feasible_incumbent(
        strict_result, matrix, np.asarray(rhs),
        lower_bounds[:base_variable_count], upper_bounds[:base_variable_count],
        integrality[:base_variable_count],
    )
    used_slack = False
    selected_result = strict_result
    selected_feasible = strict_feasible
    if not strict_feasible:
        # Retry only nutrient rows with nonnegative slack; empirical structure stays hard.
        slack_matrix = sparse.lil_matrix((len(rows), n_nutrients), dtype=float)
        for row_idx, slack_column in nutrient_slack_column_by_constraint.items():
            slack_matrix[row_idx, slack_column - base_variable_count] = -1.0
        relaxed_rows = sparse.hstack([matrix, slack_matrix], format="csr")
        relaxed_result = milp(
            c=objective, integrality=integrality,
            bounds=Bounds(lower_bounds, upper_bounds),
            constraints=LinearConstraint(
                relaxed_rows.tocsr(), np.full(len(rhs), -np.inf), np.asarray(rhs)
            ), options=solver_options,
        )
        selected_result = relaxed_result
        selected_feasible = has_feasible_incumbent(
            relaxed_result, relaxed_rows.tocsr(), np.asarray(rhs),
            lower_bounds, upper_bounds, integrality,
        )
        used_slack = selected_feasible
    result = selected_result
    optimality_proven = bool(result.status == 0 and result.success)

    report: dict[str, Any] = {
        "profile": profile,
        "status": (
            "solution_returned" if selected_feasible and optimality_proven
            else "feasible_incumbent_not_proven_optimal" if selected_feasible
            else "no_feasible_incumbent_within_solver_limit"
        ),
        "strict_solver_status": strict_status,
        "solver_status": int(result.status),
        "solver_optimality_proven": optimality_proven,
        "solver_time_limit_seconds_per_attempt": MILP_TIME_LIMIT_SECONDS,
        "solver_relative_gap_tolerance": MILP_RELATIVE_GAP,
        "relaxed_nutrient_fallback_used": used_slack,
        "n_continuous_food_day_slot_variables": x_count,
        "n_binary_food_day_variables": y_count,
        "n_constraints": len(rows),
        "n_source_diets": len(plans),
        "profile_rule_exclusions": len(removals),
        "profile_candidate_foods": len(candidates),
        "mapped_candidate_foods": len(food_names),
        "candidate_foods_by_slot": {
            slot: len({name for name in food_names if (name, slot) in caps["food_slot_day_caps_g"]})
            for slot in MEAL_ORDER
        },
        "empirical_rules": {
            "daily_unique_food_floor_q25": diversity_floor,
            "food_repeat_cap_q95_days": caps["food_repeat_caps_days_per_plan"],
            "meal_energy_share_q05_q95": caps["meal_energy_share_q05_q95"],
            "quantity_caps_rule": "positive source support q95 where n>=20, otherwise observed maximum; per profile and meal slot",
            "food_assignment_scope": "food may be assigned only to meal slots where it appears in this profile's source plans",
        },
        "strict_solver_message": str(strict_result.message),
        "solver_message": str(result.message),
        "objective_value": float(result.fun) if result.fun is not None else None,
    }
    if not selected_feasible or result.x is None:
        report["final_solution"] = None
        return report

    decision = result.x if used_slack else np.concatenate([result.x, np.zeros(n_nutrients)])
    x = decision[:x_count]
    y = decision[x_count:x_count + y_count]
    slacks = decision[x_count + y_count:]
    output_plan: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for day_idx in range(DAYS_PER_PLAN):
        output_plan[str(day_idx + 1)] = {slot: [] for slot in MEAL_ORDER}
    for idx, (day_idx, name, slot) in enumerate(variable_keys):
        if x[idx] > 1e-6:
            output_plan[str(day_idx + 1)][slot].append({
                "alimento": name, "quantidade": round(float(x[idx]), 4),
            })
    for day in output_plan.values():
        for slot in day:
            day[slot].sort(key=lambda item: item["alimento"])
    slack_labels = [
        f"day_{day_idx + 1}:{nutrient}:{bound}"
        for day_idx in range(DAYS_PER_PLAN)
        for nutrient, bound in (
            [(key, "minimum") for key in protocol["minimum_goals"]]
            + [(key, "maximum") for key in protocol["maximum_goals"]]
        )
    ]
    report.update({
        "selected_food_day_pairs": int(np.count_nonzero(y >= 0.5)),
        "daily_selected_food_counts": [
            int(sum(y[y_index[(day_idx, name)] - x_count] >= 0.5 for name in food_names
                    if (day_idx, name) in y_index))
            for day_idx in range(DAYS_PER_PLAN)
        ],
        "nonzero_nutrient_slack_count": int(np.count_nonzero(slacks > 1e-7)) if used_slack else 0,
        "nonzero_nutrient_slacks": [
            {"constraint": label, "amount": float(slacks[idx])}
            for idx, label in enumerate(slack_labels)
            if used_slack and idx < len(slacks) and slacks[idx] > 1e-7
        ],
        "metrics_and_violations": evaluate_plan(
            output_plan, context,
            minimum_goals=protocol["minimum_goals"],
            maximum_goals=protocol["maximum_goals"],
            protocol_id=protocol["protocol_id"],
            data_quality_fields=set(protocol["minimum_goals"]) | set(protocol["maximum_goals"]),
        ),
        "independent_constraint_validation": validate_structured_plan(
            output_plan, context, support, caps
        ),
        "final_solution": output_plan,
    })
    return report


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    context = build_context({
        "tbca_map": str(PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json"),
        "tbca_db": str(PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"),
        "footprint_map": str(PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json"),
    })
    protocol = load_protocol(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
    exclusions = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
    results = []
    for profile in PROFILES:
        source_plans = load_json_file(PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json")
        structured = solve_profile(profile, source_plans, context, protocol, exclusions)
        plans, _ = prepare_profile_diets(source_plans, profile, exclusions[profile])
        candidates = food_names_in_diets(plans)
        baseline_diagnostics: dict[str, Any] = {}
        baseline = optimize_food_level(
            context, allowed_food_names=candidates, diagnostics=baseline_diagnostics,
            minimum_goals=protocol["minimum_goals"], maximum_goals=protocol["maximum_goals"],
        )
        structured["aggregate_lp_food_baseline"] = {
            "status": "solution_returned" if baseline else "no_solution",
            "solver_status": baseline_diagnostics.get("initial_status"),
            "relaxed_fallback_used": baseline_diagnostics.get("fallback_used", False),
            "candidate_food_count": len(candidates),
            "solution": baseline[0] if baseline else None,
        }
        results.append(structured)
    report = {
        "schema_version": "1.0",
        "status": "diagnostic_only_structured_food_level_not_recipe_feasibility",
        "experiment": "lp-food-meal-structure-sensitivity",
        "protocol_id": protocol["protocol_id"],
        "source_provenance": source_provenance(),
        "model_scope": "profile-specific food variables assigned only to source-observed meal slots; q25 daily diversity, q95 food repeat/quantity support, and q05-q95 meal energy-share constraints",
        "limitations": [
            "The model does not preserve complete recipes or test ingredient compatibility within meals.",
            "Missing nutrient fields retain the current zero-contribution behavior; the missingness policy is not adjudicated.",
            "Corpus-derived ranges describe support in the generated source diets, not clinical serving or meal advice.",
            "Environmental line attribution and non-identity target decisions remain unresolved.",
        ],
        "results": results,
    }
    path = output_dir / "lp-food-meal-structure-sensitivity.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "profile_status": [{
            "profile": row["profile"], "status": row["status"],
            "strict_solver_status": row["strict_solver_status"],
            "fallback": row["relaxed_nutrient_fallback_used"],
            "daily_diversity_floor": row["empirical_rules"]["daily_unique_food_floor_q25"],
        } for row in results],
        "output": str(path),
    }, ensure_ascii=False, indent=2))
    invalid = [row["profile"] for row in results
               if row.get("independent_constraint_validation", {}).get("status") != "passed"]
    if invalid:
        raise RuntimeError(f"Structured LP-Food invariant validation failed for profiles: {invalid}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.output_dir.resolve())


if __name__ == "__main__":
    main()
