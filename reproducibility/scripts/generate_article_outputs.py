#!/usr/bin/env python3
"""Generate the numerical tables and four article figures from diet JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPRO_DIR = SCRIPT_PATH.parents[1]
CODE_DIR = REPRO_DIR / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from scripts.calculate_statistics import (  # noqa: E402
    _filter_existing_files,
    _process_group,
    resolve_diet_file_groups,
)
from otimizar.hyperparameters import (  # noqa: E402
    RESOLUTION_AG_ALIMENTOS,
    RESOLUTION_AG_REFEICOES,
    RESOLUTION_PL_ALIMENTOS,
    RESOLUTION_PL_REFEICOES,
)
from otimizar.utils import load_json_file  # noqa: E402


PROFILES = ["Regular", "Vegetariana", "Vegana"]
PROFILE_KEYS = {"Regular": "regular", "Vegetariana": "vegetariana", "Vegana": "vegana"}
PROFILE_EN = {"Regular": "Regular", "Vegetariana": "Vegetarian", "Vegana": "Vegan"}
GROUPS = [
    "base",
    RESOLUTION_AG_ALIMENTOS,
    RESOLUTION_AG_REFEICOES,
    RESOLUTION_PL_ALIMENTOS,
    RESOLUTION_PL_REFEICOES,
]
LABELS = {
    "base": "Base",
    RESOLUTION_AG_ALIMENTOS: "GA-Food",
    RESOLUTION_AG_REFEICOES: "GA-Meal",
    RESOLUTION_PL_ALIMENTOS: "LP-Food",
    RESOLUTION_PL_REFEICOES: "LP-Meal",
}
COLORS = ["#8da0cb", "#66c2a5", "#fc8d62", "#e78ac3", "#a6d854"]
NUTRIENTS = [
    "Energia",
    "Proteína",
    "Lipídios",
    "Carboidrato disponível",
    "Fibra alimentar",
    "Cálcio",
    "Ferro",
    "Vitamina C",
    "Sódio",
    "Colesterol",
    "Pegada de Carbono",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    return parser.parse_args()


def load_consolidated(workspace: Path, output_dir: Path):
    tbca_map = load_json_file(
        workspace / "data" / "maps" / "derived" / "mapa-sustentavel-tbca.json"
    )
    tbca_database = load_json_file(
        workspace / "data" / "maps" / "base" / "mapa-tbca-completo.json"
    )
    footprint_map = load_json_file(
        workspace / "data" / "maps" / "base" / "mapa-sustentavel-pegadas.json"
    )
    grouped = resolve_diet_file_groups(workspace)
    reports = output_dir / "reports"
    figures = output_dir / "diagnostic-figures"
    consolidated = {}
    for group in GROUPS:
        files = _filter_existing_files(grouped.get(group, []))
        if files:
            consolidated[group] = _process_group(
                group,
                files,
                reports,
                figures,
                tbca_map,
                tbca_database,
                footprint_map,
            )
    return consolidated


def result_tables(consolidated, output_dir: Path) -> pd.DataFrame:
    rows = []
    for group, group_data in consolidated.items():
        for profile, values in group_data.items():
            for nutrient in NUTRIENTS:
                rows.append(
                    {
                        "Approach": LABELS[group],
                        "Diet": profile,
                        "Nutrient": nutrient,
                        "Value": values.get(nutrient, float("nan")),
                    }
                )
    pivot = pd.DataFrame(rows).pivot_table(
        index=["Diet", "Nutrient"], columns="Approach", values="Value"
    )
    # Preserve the column schema of the CSV files used by the submitted paper.
    pivot.index = pivot.index.set_names(["Dieta", "Nutriente"])
    columns = [x for x in LABELS.values() if x in pivot.columns]
    pivot = pivot[columns]
    pivot.round(2).to_csv(output_dir / "tabela_consolidada.csv", encoding="utf-8-sig")
    variation = pivot.copy()
    for column in columns:
        if column != "Base":
            variation[column] = ((pivot[column] - pivot["Base"]) / pivot["Base"]) * 100
    variation = variation.drop(columns=["Base"])
    variation.round(2).to_csv(output_dir / "variacao_percentual.csv", encoding="utf-8-sig")
    for profile in pivot.index.get_level_values("Dieta").unique():
        pivot.loc[profile].round(2).to_latex(
            output_dir / f"tabela_{profile.lower()}.tex",
            caption=f"Nutritional results -- {profile}",
            label=f"tab:{profile.lower()}",
            bold_rows=True,
        )
    return pivot


def count_unique_foods(diet: dict) -> int:
    return len(
        {
            item["alimento"]
            for day in diet.values()
            for meal in day.values()
            for item in meal
        }
    )


def count_unique_foods_across(diets: list[dict]) -> int:
    return len(
        {
            item["alimento"]
            for diet in diets
            for day in diet.values()
            for meal in day.values()
            for item in meal
        }
    )


def diversity_table(workspace: Path, output_dir: Path) -> pd.DataFrame:
    all_runs = workspace / "data" / "outputs" / "all_run_solutions"
    ga_root = (
        "data/outputs/all_run_solutions"
        if all_runs.exists()
        else "data/outputs/optimized_diets"
    )
    paths = {
        "Base": "data/diets/base/dietas-{profile}.json",
        "GA-Food": ga_root + "/ag-alimentos/otimizada-dietas-{profile}.json",
        "GA-Meal": ga_root + "/ag-refeicoes/otimizada-dietas-{profile}.json",
        "LP-Food": "data/outputs/optimized_diets/pl-alimentos/otimizada-dietas-{profile}.json",
        "LP-Meal": "data/outputs/optimized_diets/pl-refeicoes/otimizada-dietas-{profile}.json",
    }
    mean_rows = []
    total_rows = []
    long_rows = []
    for profile in PROFILES:
        mean_row = {"Profile": PROFILE_EN[profile]}
        total_row = {"Profile": PROFILE_EN[profile]}
        key = PROFILE_KEYS[profile]
        for approach, template in paths.items():
            diets = json.loads((workspace / template.format(profile=key)).read_text(encoding="utf-8"))
            counts = [count_unique_foods(diet) for diet in diets]
            total = count_unique_foods_across(diets)
            mean = sum(counts) / len(counts)
            mean_row[approach] = mean
            total_row[approach] = total
            long_rows.append(
                {
                    "Profile": PROFILE_EN[profile],
                    "Approach": approach,
                    "N": len(diets),
                    "Total": total,
                    "Mean/week": mean,
                }
            )
        mean_rows.append(mean_row)
        total_rows.append(total_row)
    means = pd.DataFrame(mean_rows).set_index("Profile")
    totals = pd.DataFrame(total_rows).set_index("Profile")
    totals.to_csv(output_dir / "diversity_unique_foods.csv")
    pd.DataFrame(long_rows).round(2).to_csv(
        output_dir / "diversity_summary.csv", index=False
    )
    combined = pd.concat({"Total": totals, "Mean/week": means}, axis=1).swaplevel(0, 1, axis=1)
    combined = combined.reindex(columns=pd.MultiIndex.from_product([list(paths), ["Total", "Mean/week"]]))
    combined.round(2).to_latex(
        output_dir / "tabela_diversity.tex",
        caption="Unique foods across recommendations and mean per weekly diet",
        label="tab:diversity",
    )
    return means


def annotate(ax, fmt: str = ".0f") -> None:
    for patch in ax.patches:
        height = patch.get_height()
        if height > 0:
            ax.text(
                patch.get_x() + patch.get_width() / 2,
                height,
                f"{height:{fmt}}",
                ha="center",
                va="bottom",
                fontsize=10,
                rotation=60,
            )


def article_figures(consolidated, diversity: pd.DataFrame, output_dir: Path) -> None:
    sns.set_style("whitegrid")
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    x = np.arange(len(PROFILES))
    width = 0.15

    for metric, ylabel, filename in [
        ("Pegada de Carbono", "Carbon Footprint (gCO2eq/day)", "pegada_carbono_comparativo.png"),
        ("Energia", "Energy (kcal/day)", "adequacao_energetica_comparativo.png"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 5))
        maximum = 0.0
        for index, group in enumerate(GROUPS):
            values = [consolidated[group][profile].get(metric, 0) for profile in PROFILES]
            maximum = max(maximum, *values)
            ax.bar(x + index * width, values, width, label=LABELS[group], color=COLORS[index])
        if metric == "Energia":
            ax.axhline(2000, color="red", linestyle="--", linewidth=1.2, label="Goal (2000 kcal)")
            ax.axhspan(1900, 2100, alpha=0.1, color="red", label="Range ±5%")
        ax.set_ylabel(ylabel)
        ax.set_xticks(x + width * 2)
        ax.set_xticklabels([PROFILE_EN[p] for p in PROFILES])
        ax.set_ylim(0, maximum * 1.18)
        ax.legend()
        annotate(ax)
        fig.tight_layout()
        fig.savefig(figure_dir / filename, dpi=300, bbox_inches="tight")
        plt.close(fig)

    nutrient_targets = {
        "Energia": 2000,
        "Proteína": 75,
        "Lipídios": 73,
        "Carboidrato disponível": 292,
        "Fibra alimentar": 25,
        "Cálcio": 1000,
        "Ferro": 18,
        "Vitamina C": 75,
    }
    heatmap_rows = []
    labels = []
    for group in GROUPS:
        for profile in PROFILES:
            labels.append(f"{LABELS[group]} ({PROFILE_EN[profile]})")
            heatmap_rows.append(
                {
                    nutrient: consolidated[group][profile].get(nutrient, 0) / target * 100
                    for nutrient, target in nutrient_targets.items()
                }
            )
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        pd.DataFrame(heatmap_rows, index=labels),
        annot=True,
        fmt=".0f",
        cmap="RdYlGn",
        center=100,
        vmin=50,
        vmax=200,
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "Adequacy (%)"},
    )
    fig.tight_layout()
    fig.savefig(figure_dir / "heatmap_adequacao_nutricional.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    for index, approach in enumerate(LABELS.values()):
        ax.bar(
            np.arange(len(diversity.index)) + index * width,
            diversity[approach].values,
            width,
            label=approach,
            color=COLORS[index],
        )
    ax.set_ylabel("Mean Unique Foods")
    ax.set_xticks(np.arange(len(diversity.index)) + width * 2)
    ax.set_xticklabels(diversity.index)
    ax.set_ylim(0, diversity.max().max() * 1.18)
    ax.legend(loc="lower left")
    annotate(ax, ".1f")
    fig.tight_layout()
    fig.savefig(figure_dir / "diversidade_alimentar.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    workspace = parse_args().workspace.resolve()
    output_dir = workspace / "article_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    consolidated = load_consolidated(workspace, output_dir)
    if set(consolidated) != set(GROUPS):
        missing = sorted(set(GROUPS) - set(consolidated))
        raise RuntimeError(f"Missing result groups: {missing}")
    pivot = result_tables(consolidated, output_dir)
    diversity = diversity_table(workspace, output_dir)
    article_figures(consolidated, diversity, output_dir)
    print(f"Generated {pivot.shape[0]} result rows in {output_dir}")


if __name__ == "__main__":
    main()

