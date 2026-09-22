#!/usr/bin/env python3
"""Validate an archived reconstruction against the submitted CSV artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = PROJECT_ROOT / "archive"

EXPECTED_DIVERSITY = {
    ("Regular", "Base"): (50, 187, 61.94),
    ("Regular", "GA-Food"): (10, 155, 58.70),
    ("Regular", "GA-Meal"): (10, 147, 56.80),
    ("Regular", "LP-Food"): (1, 10, 10.00),
    ("Regular", "LP-Meal"): (1, 27, 27.00),
    ("Vegetarian", "Base"): (50, 207, 72.46),
    ("Vegetarian", "GA-Food"): (10, 173, 66.10),
    ("Vegetarian", "GA-Meal"): (10, 164, 64.60),
    ("Vegetarian", "LP-Food"): (1, 10, 10.00),
    ("Vegetarian", "LP-Meal"): (1, 32, 32.00),
    ("Vegan", "Base"): (50, 157, 68.68),
    ("Vegan", "GA-Food"): (10, 134, 57.50),
    ("Vegan", "GA-Meal"): (10, 131, 57.50),
    ("Vegan", "LP-Food"): (1, 10, 10.00),
    ("Vegan", "LP-Meal"): (1, 23, 23.00),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=PROJECT_ROOT / "tests" / "results" / "artifacts" / "manual-run",
        help="Workspace created by the archived experiment runner.",
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


def validate_archived_population() -> None:
    for path in sorted((ARCHIVE_ROOT / "published-table-solutions").rglob("*.json")):
        diets = json.loads(path.read_text(encoding="utf-8"))
        if len(diets) != 1:
            raise AssertionError(f"Expected one selected solution in {path}: {len(diets)}")

    for path in sorted((PROJECT_ROOT / "optimized-diets").glob("ag-*/*.json")):
        diets = json.loads(path.read_text(encoding="utf-8"))
        if len(diets) != 10:
            raise AssertionError(f"Expected ten GA solutions in {path}: {len(diets)}")

    for path in sorted((PROJECT_ROOT / "diets-base").glob("dietas-*.json")):
        diets = json.loads(path.read_text(encoding="utf-8"))
        if len(diets) != 50:
            raise AssertionError(f"Expected fifty base diets in {path}: {len(diets)}")


def validate_diversity(path: Path) -> None:
    frame = pd.read_csv(path).set_index(["Profile", "Approach"])
    if set(frame.index) != set(EXPECTED_DIVERSITY):
        raise AssertionError("Diversity profile/approach combinations differ from expected.")
    for key, (expected_n, expected_total, expected_mean) in EXPECTED_DIVERSITY.items():
        row = frame.loc[key]
        actual = (int(row["N"]), int(row["Total"]), float(row["Mean/week"]))
        expected = (expected_n, expected_total, expected_mean)
        if actual[:2] != expected[:2] or abs(actual[2] - expected[2]) > 1e-9:
            raise AssertionError(f"Diversity mismatch for {key}: {actual} != {expected}")


def main() -> None:
    workspace = parse_args().workspace.resolve()
    outputs = workspace / "article_outputs"
    submitted = ARCHIVE_ROOT / "submitted-results"

    assert_csv_equal(outputs / "tabela_consolidada.csv", submitted / "tabela_consolidada.csv")
    assert_csv_equal(outputs / "variacao_percentual.csv", submitted / "variacao_percentual.csv")
    validate_diversity(outputs / "diversity_summary.csv")
    validate_archived_population()
    print("Validated 33 main-table rows, variation values, diversity, and archived population sizes.")


if __name__ == "__main__":
    main()
