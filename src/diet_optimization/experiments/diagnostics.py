"""Auditable diagnostics for newly executed optimization runs.

These checks describe the historical implemented constraints, not the revised
nutritional protocol. In particular, they do not certify clinical adequacy.
"""

from __future__ import annotations

import ctypes
import os
import platform
import subprocess
import sys
from importlib import metadata

from diet_optimization.optimization.hyperparameters import (
    LIMITES_ENERGIA_REFEICAO,
    MAXIMUM_GOALS,
    MINIMUM_GOALS,
)
from diet_optimization.optimization.utils import calculate_totals, parse_quantity_in_grams


def audit_nutrient_data_coverage(plan: dict, context, nutrient_fields: set[str]) -> dict:
    """Count missing TBCA cells actually encountered in a serialized plan."""
    report = {
        field: {"missing_occurrences": 0, "missing_quantity_g": 0.0, "food_names": set()}
        for field in sorted(nutrient_fields)
    }
    for meals in plan.values():
        if not isinstance(meals, dict):
            continue
        for items in meals.values():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                food_name = str(item.get("alimento", ""))
                code = context.tbca_map.get(food_name)
                nutrients = context.tbca_database.get(code, {}).get("nutrientes", {}) if code else {}
                try:
                    quantity_g = parse_quantity_in_grams(item.get("quantidade", 0))
                except (TypeError, ValueError):
                    quantity_g = 0.0
                for field in nutrient_fields:
                    if nutrients.get(field) is None:
                        report[field]["missing_occurrences"] += 1
                        report[field]["missing_quantity_g"] += quantity_g
                        report[field]["food_names"].add(food_name)
    return {
        "missing_values_are_currently_scored_as_zero": True,
        "by_nutrient": {
            field: {**values, "missing_quantity_g": round(values["missing_quantity_g"], 6),
                    "food_names": sorted(values["food_names"])}
            for field, values in report.items()
        },
    }


def evaluate_plan(
    plan: dict,
    context,
    minimum_goals: dict[str, float] | None = None,
    maximum_goals: dict[str, dict[str, float]] | None = None,
    meal_energy_share_limits: dict[str, dict[str, float]] | None = None,
    protocol_id: str = "historical-implemented-v1",
    data_quality_fields: set[str] | None = None,
) -> dict:
    """Recalculate daily and mean values from the serialized final solution."""
    minimum_goals = MINIMUM_GOALS if minimum_goals is None else minimum_goals
    maximum_goals = MAXIMUM_GOALS if maximum_goals is None else maximum_goals
    meal_energy_share_limits = (
        LIMITES_ENERGIA_REFEICAO if meal_energy_share_limits is None else meal_energy_share_limits
    )
    data_quality_fields = (
        set(minimum_goals) | set(maximum_goals)
        if data_quality_fields is None else set(data_quality_fields)
    )
    daily = []
    energy_by_meal: dict[str, float] = {}
    for day, meals in sorted(plan.items(), key=lambda item: int(item[0])):
        items = [food for meal in meals.values() for food in meal]
        nutrients, footprints = calculate_totals(items, context)
        meal_energies = {}
        for meal_name, foods in meals.items():
            meal_nutrients, _ = calculate_totals(foods, context)
            meal_energies[meal_name] = float(meal_nutrients.get("Energia", 0.0))
            energy_by_meal[meal_name] = energy_by_meal.get(meal_name, 0.0) + meal_energies[meal_name]
        violations = []
        for name, lower in minimum_goals.items():
            observed = float(nutrients.get(name, 0.0))
            if observed < lower - 1e-8:
                violations.append({"nutrient": name, "bound": "minimum", "target": lower,
                                   "observed": observed, "amount": lower - observed})
        for name, rule in maximum_goals.items():
            upper = float(rule["meta"]) * float(rule.get("tolerancia", 1.0))
            observed = float(nutrients.get(name, 0.0))
            if observed > upper + 1e-8:
                violations.append({"nutrient": name, "bound": "maximum", "target": upper,
                                   "observed": observed, "amount": observed - upper})
        meal_share_violations = []
        day_energy = float(nutrients.get("Energia", 0.0))
        if day_energy > 0:
            for meal_name, limits in meal_energy_share_limits.items():
                if meal_name not in meals:
                    continue
                share = meal_energies[meal_name] / day_energy
                for bound in ("min", "max"):
                    target = float(limits[bound])
                    amount = target - share if bound == "min" else share - target
                    if amount > 1e-8:
                        meal_share_violations.append({"meal": meal_name, "bound": bound,
                                                      "target_share": target, "observed_share": share,
                                                      "amount": amount})
        daily.append({"day": day, "nutrients": nutrients, "footprints": footprints,
                      "violations": violations, "meal_share_violations": meal_share_violations})

    keys = {key for row in daily for key in row["nutrients"]}
    footprint_keys = {key for row in daily for key in row["footprints"]}
    count = len(daily)
    mean_nutrients = {key: sum(row["nutrients"].get(key, 0.0) for row in daily) / count
                      for key in sorted(keys)} if count else {}
    mean_violations = []
    if count:
        for name, lower in minimum_goals.items():
            observed = float(mean_nutrients.get(name, 0.0))
            if observed < lower - 1e-8:
                mean_violations.append({"nutrient": name, "bound": "minimum", "target": lower,
                                        "observed": observed, "amount": lower - observed})
        for name, rule in maximum_goals.items():
            upper = float(rule["meta"]) * float(rule.get("tolerancia", 1.0))
            observed = float(mean_nutrients.get(name, 0.0))
            if observed > upper + 1e-8:
                mean_violations.append({"nutrient": name, "bound": "maximum", "target": upper,
                                        "observed": observed, "amount": observed - upper})
    lp_meal_energy_violations = []
    for meal_name, limits in meal_energy_share_limits.items():
        if meal_name not in energy_by_meal:
            continue
        observed = energy_by_meal[meal_name]
        for bound in ("min", "max"):
            target = count * maximum_goals["Energia"]["meta"] * float(limits[bound])
            amount = target - observed if bound == "min" else observed - target
            if amount > 1e-8:
                lp_meal_energy_violations.append({"meal": meal_name, "bound": bound,
                                                  "target_energy": target, "observed_energy": observed,
                                                  "amount": amount})
    return {
        "constraint_set": protocol_id,
        "nutrient_data_coverage": audit_nutrient_data_coverage(
            plan, context, data_quality_fields
        ),
        "daily": daily,
        "mean_daily_nutrients": mean_nutrients,
        "mean_daily_footprints": {key: sum(row["footprints"].get(key, 0.0) for row in daily) / count
                                  for key in sorted(footprint_keys)} if count else {},
        "violation_count": sum(len(row["violations"]) for row in daily),
        "mean_daily_violations": mean_violations,
        "lp_meal_energy_violations_after_rounding": lp_meal_energy_violations,
        "ga_daily_meal_share_violation_count": sum(len(row["meal_share_violations"]) for row in daily),
    }


def _memory_bytes() -> int | None:
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                        ("total_physical", ctypes.c_ulonglong), ("available_physical", ctypes.c_ulonglong),
                        ("total_page", ctypes.c_ulonglong), ("available_page", ctypes.c_ulonglong),
                        ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                        ("available_extended", ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical)
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo", encoding="ascii") as source:
                for line in source:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) * 1024
        except OSError:
            pass
    elif sys.platform == "darwin":
        try:
            return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        except (OSError, ValueError, subprocess.CalledProcessError):
            pass
    return None


def environment_metadata() -> dict:
    """Capture the runtime and the actual SciPy-backed LP solver provenance."""
    packages = ("brazilian-sustainable-diet-optimization", "Jinja2", "matplotlib",
                "numpy", "pandas", "scipy", "seaborn")
    versions = {}
    for package in packages:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    highs_version = None
    try:
        from scipy.optimize._highspy import _core  # SciPy's bundled HiGHS metadata
        highs_version = ".".join(str(getattr(_core, f"HIGHS_VERSION_{part}"))
                                 for part in ("MAJOR", "MINOR", "PATCH"))
    except (ImportError, AttributeError):
        pass
    return {
        "os": platform.platform(), "machine": platform.machine(),
        "cpu_model": platform.processor() or None, "logical_cpu_count": os.cpu_count(),
        "physical_ram_bytes": _memory_bytes(), "python": sys.version,
        "dependencies": versions,
        "lp_solver": {"interface": "scipy.optimize.linprog", "method": "highs",
                      "highs_version": highs_version, "scipy_version": versions["scipy"],
                      "options": {}, "bounds": "nonnegative", "fallback": "inequality slacks with penalty 10000"},
    }
