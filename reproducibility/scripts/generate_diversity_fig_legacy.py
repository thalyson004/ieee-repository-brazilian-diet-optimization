#!/usr/bin/env python3
"""Generate diversity figure for paper."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Setup paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
FIGURAS_DIR = SCRIPT_DIR / "figuras"
FIGURAS_DIR.mkdir(exist_ok=True)

# Configuration from notebook
plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.size": 16,
        "axes.titlesize": 16,
        "axes.labelsize": 16,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 14,
    }
)
sns.set_style("whitegrid")

# Constants
col_order_div = ["Base", "GA-Food", "GA-Meal", "LP-Food", "LP-Meal"]
APPROACH_COLORS = ["#8da0cb", "#66c2a5", "#fc8d62", "#e78ac3", "#a6d854"]

PROFILES = {
    "regular": "Regular",
    "vegetariana": "Vegetarian",
    "vegana": "Vegan",
}

APPROACH_PATHS = {
    "Base": "data/diets/base/dietas-{profile}.json",
    "GA-Food": "data/outputs/optimized_diets/ag-alimentos/otimizada-dietas-{profile}.json",
    "GA-Meal": "data/outputs/optimized_diets/ag-refeicoes/otimizada-dietas-{profile}.json",
    "LP-Food": "data/outputs/optimized_diets/pl-alimentos/otimizada-dietas-{profile}.json",
    "LP-Meal": "data/outputs/optimized_diets/pl-refeicoes/otimizada-dietas-{profile}.json",
}


def count_unique_foods(diet: dict) -> int:
    """Count unique food names across all days and meals of a single diet."""
    foods = set()
    for day in diet.values():
        for meal in day.values():
            for item in meal:
                foods.add(item["alimento"])
    return len(foods)


def build_diversity_dataframe() -> pd.DataFrame:
    """Load diet JSON files and compute mean unique food count per weekly diet."""
    data = {approach: [] for approach in col_order_div}

    for profile_key, profile_label in PROFILES.items():
        for approach, path_tpl in APPROACH_PATHS.items():
            path = PROJECT_DIR / path_tpl.format(profile=profile_key)
            diets = json.loads(path.read_text(encoding="utf-8"))
            counts = [count_unique_foods(d) for d in diets]
            data[approach].append(sum(counts) / len(counts))

    return pd.DataFrame(data, index=list(PROFILES.values()))


df_div_pivot = build_diversity_dataframe()
print("Computed unique food counts:")
print(df_div_pivot.to_string())


def annotate_bars(ax, fontsize=14, rotation=60, fmt=".0f"):
    """Add value labels above bars."""
    for bar in ax.patches:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h,
                f"{h:{fmt}}",
                ha="center",
                va="bottom",
                fontsize=fontsize,
                rotation=rotation,
            )


# Generate diversity figure
fig4, ax4 = plt.subplots(figsize=(10, 5))
x4 = np.arange(len(df_div_pivot.index))
width4 = 0.15
for i, col in enumerate(col_order_div):
    ax4.bar(
        x4 + i * width4,
        df_div_pivot[col].values,
        width4,
        label=col,
        color=APPROACH_COLORS[i],
    )

ax4.set_ylabel("Mean Unique Foods", fontsize=16)
ax4.set_xticks(x4 + width4 * 2)
ax4.set_xticklabels(df_div_pivot.index, fontsize=14)
ax4.legend(fontsize=12, loc="lower left")
ax4.grid(axis="y", alpha=0.3)
# Set Y-axis limit with 20% extra space for annotations
max_val = df_div_pivot.max().max()
ax4.set_ylim(0, max_val * 1.15)
annotate_bars(ax4, fontsize=14, rotation=60, fmt=".1f")
plt.tight_layout()
fig_path4 = FIGURAS_DIR / "diversidade_alimentar.png"
fig4.savefig(fig_path4, dpi=300, bbox_inches="tight")
plt.close()
print(f"Figure saved: {fig_path4}")
