#!/usr/bin/env python3
"""Validate the article tables against the supplied CSV files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = PROJECT_ROOT / "artifacts" / "reference"

EXPECTED_DIVERSITY = {
    ("Regular", "Base"): (50, 187, 61.94, 15.09),
    ("Regular", "GA-Food"): (10, 155, 58.70, 4.35),
    ("Regular", "GA-Meal"): (10, 147, 56.80, 3.36),
    ("Regular", "LP-Food"): (1, 10, 10.00, None),
    ("Regular", "LP-Meal"): (1, 27, 27.00, None),
    ("Vegetarian", "Base"): (50, 207, 72.46, 5.80),
    ("Vegetarian", "GA-Food"): (10, 173, 66.10, 3.45),
    ("Vegetarian", "GA-Meal"): (10, 164, 64.60, 5.76),
    ("Vegetarian", "LP-Food"): (1, 10, 10.00, None),
    ("Vegetarian", "LP-Meal"): (1, 32, 32.00, None),
    ("Vegan", "Base"): (50, 157, 68.68, 8.94),
    ("Vegan", "GA-Food"): (10, 134, 57.50, 3.89),
    ("Vegan", "GA-Meal"): (10, 131, 57.50, 5.58),
    ("Vegan", "LP-Food"): (1, 10, 10.00, None),
    ("Vegan", "LP-Meal"): (1, 23, 23.00, None),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=PROJECT_ROOT / "tests" / "results" / "artifacts" / "manual-run",
        help="Workspace created by the article reconstruction command.",
    )
    return parser.parse_args()


def assert_csv_equal(generated: Path, expected: Path) -> None:
    generated_frame = pd.read_csv(generated)
    expected_frame = pd.read_csv(expected)
    pd.testing.assert_frame_equal(
        generated_frame,
        expected_frame,
        check_dtype=False,
        check_exact=False,
        atol=1e-12,
        rtol=0,
    )


def validate_supplied_population() -> None:
    for path in sorted((REFERENCE_ROOT / "table-solutions").rglob("*.json")):
        diets = json.loads(path.read_text(encoding="utf-8"))
        if len(diets) != 1:
            raise AssertionError(f"Expected one selected solution in {path}: {len(diets)}")

    for path in sorted((PROJECT_ROOT / "optimized-diets").glob("ag-*/*.json")):
        diets = json.loads(path.read_text(encoding="utf-8"))
        if len(diets) != 10:
            raise AssertionError(f"Expected ten GA solutions in {path}: {len(diets)}")

    for method in ("ag-alimentos", "ag-refeicoes"):
        for profile in ("regular", "vegetariana", "vegana"):
            selected_path = (
                REFERENCE_ROOT / "table-solutions" / method
                / f"otimizada-dietas-{profile}.json"
            )
            all_runs_path = (
                PROJECT_ROOT / "optimized-diets" / method
                / f"otimizada-dietas-{profile}.json"
            )
            selected = json.loads(selected_path.read_text(encoding="utf-8"))[0]
            all_runs = json.loads(all_runs_path.read_text(encoding="utf-8"))
            if any(selected == run for run in all_runs):
                raise AssertionError(
                    f"Selected {method}/{profile} table solution unexpectedly "
                    "appears in the separate ten-plan diversity collection."
                )

    for path in sorted((PROJECT_ROOT / "diets-base").glob("dietas-*.json")):
        diets = json.loads(path.read_text(encoding="utf-8"))
        if len(diets) != 50:
            raise AssertionError(f"Expected fifty base diets in {path}: {len(diets)}")


def validate_diversity(path: Path) -> None:
    frame = pd.read_csv(path).set_index(["Profile", "Approach"])
    if set(frame.index) != set(EXPECTED_DIVERSITY):
        raise AssertionError("Diversity profile/approach combinations differ from expected.")
    for key, (expected_n, expected_total, expected_mean, expected_sd) in EXPECTED_DIVERSITY.items():
        row = frame.loc[key]
        actual = (int(row["N"]), int(row["Total"]), float(row["Mean/week"]))
        expected = (expected_n, expected_total, expected_mean)
        if actual[:2] != expected[:2] or abs(actual[2] - expected[2]) > 1e-9:
            raise AssertionError(f"Diversity mismatch for {key}: {actual} != {expected}")
        actual_sd = row["SD/week"]
        if expected_sd is None:
            if not pd.isna(actual_sd):
                raise AssertionError(f"Expected no SD for deterministic single plan {key}: {actual_sd}")
        elif abs(float(actual_sd) - expected_sd) > 1e-9:
            raise AssertionError(f"Diversity SD mismatch for {key}: {actual_sd} != {expected_sd}")


def validate_metric_results(path: Path) -> None:
    frame = pd.read_csv(path)
    expected_columns = {
        "profile",
        "approach",
        "metric",
        "statistic",
        "value",
        "unit",
        "n",
        "comparison_basis",
    }
    if set(frame.columns) != expected_columns:
        raise AssertionError(f"Unexpected result columns: {list(frame.columns)}")
    if len(frame) != 327:
        raise AssertionError(f"Expected 327 result rows, found {len(frame)}")
    ga_main = frame[
        (frame["approach"].isin(["GA-Food", "GA-Meal"]))
        & (frame["statistic"] == "mean_daily")
    ]
    if set(ga_main["n"]) != {1}:
        raise AssertionError("The main GA table must remain marked as n=1.")
    ga_diversity = frame[
        (frame["approach"].isin(["GA-Food", "GA-Meal"]))
        & (frame["statistic"] == "unique_foods_mean_per_week")
    ]
    if set(ga_diversity["n"]) != {10}:
        raise AssertionError("The GA diversity result must remain marked as n=10.")


def main() -> None:
    workspace = parse_args().workspace.resolve()
    outputs = workspace / "article_outputs"
    reference_tables = REFERENCE_ROOT / "reference-tables"

    assert_csv_equal(outputs / "tabela_consolidada.csv", reference_tables / "tabela_consolidada.csv")
    assert_csv_equal(outputs / "variacao_percentual.csv", reference_tables / "variacao_percentual.csv")
    assert_csv_equal(outputs / "results_by_metric.csv", reference_tables / "results_by_metric.csv")
    validate_diversity(outputs / "diversity_summary.csv")
    validate_metric_results(outputs / "results_by_metric.csv")
    validate_supplied_population()
    print("Validated 33 main-table rows, variation values, diversity, and supplied population sizes.")
    print("Verified that the six selected GA table solutions are distinct from the ten-plan diversity collection.")


if __name__ == "__main__":
    main()
