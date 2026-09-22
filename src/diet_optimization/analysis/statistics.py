"""Module calculate statistics."""

import argparse
import json
import os
import shutil
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

os.environ["MPLBACKEND"] = "Agg"

from diet_optimization.optimization.hyperparameters import (
    RESOLUTION_AG_ALIMENTOS,
    RESOLUTION_AG_REFEICOES,
    RESOLUTION_PL_ALIMENTOS,
    RESOLUTION_PL_REFEICOES,
)

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

GRAMAS_REFERENCIA_TBCA = 100.0
GRAMAS_REFERENCIA_PEGADA = 100.0

METAS_NUTRICIONAIS = {
    "Energia": 2000.0,
    "Carboidrato total": 302.5,
    "Proteína": 110.0,
    "Lipídios": 61.11,
    "Fibra alimentar": 25.0,
    "Vitamina A (RE)": 900.0,
    "Vitamina C": 90.0,
    "Vitamina D": 15.0,
    "Alfa-tocoferol (Vitamina E)": 15.0,
    "Tiamina": 1.2,
    "Riboflavina": 1.3,
    "Niacina": 16.0,
    "Vitamina B6": 1.3,
    "Vitamina B12": 2.4,
    "Cálcio": 1000.0,
    "Magnésio": 420.0,
    "Sódio": 2300.0,
}

MAPA_NOMES_GRAFICO = {
    "Carboidrato total": "Carboidrato",
    "Fibra alimentar": "Fibra",
    "Alfa-tocoferol (Vitamina E)": "Vit. E",
    "Vitamina A (RE)": "Vit. A",
    "Lipídios": "Lipídios",
    "Proteína": "Proteína",
    "Cálcio": "Cálcio",
    "Magnésio": "Magnésio",
    "Sódio": "Sódio",
}

MACROS = ["Energia", "Carboidrato total", "Proteína", "Lipídios", "Fibra alimentar"]
MICROS = [
    "Vitamina A (RE)",
    "Vitamina C",
    "Vitamina D",
    "Alfa-tocoferol (Vitamina E)",
    "Tiamina",
    "Riboflavina",
    "Niacina",
    "Vitamina B6",
    "Vitamina B12",
    "Cálcio",
    "Magnésio",
    "Sódio",
]
PEGADAS = ["Pegada de Carbono", "Pegada Hídrica", "Pegada Ecológica"]

CHAVE_PEGADA_PARA_ARQUIVO = {
    "Pegada de Carbono": "carbono",
    "Pegada Hídrica": "hidrica",
    "Pegada Ecológica": "ecologica",
}

ORDEM_DIETAS_PADRAO = ["Regular", "Vegetariana", "Vegana"]

# Paleta clara: dietas base
CORES_DIETAS_BASE = {
    "Regular": "#93abd0",
    "Vegetariana": "#ebb597",
    "Vegana": "#99cba4",
}
# Paleta regular: otimizacao por Algoritmo Genetico (AG)
CORES_DIETAS_GA = {"Regular": "#4c72b0", "Vegetariana": "#dd8452", "Vegana": "#55a868"}
# Paleta escura: otimizacao por Programacao Linear (PL)
CORES_DIETAS_LINEAR = {
    "Regular": "#35507b",
    "Vegetariana": "#9b5c39",
    "Vegana": "#3c7649",
}

# Alias de retrocompatibilidade
CORES_DIETAS = CORES_DIETAS_GA


def load_json_file(file_path: Path) -> Any:
    """Carrega um arquivo JSON e retorna seu conteúdo.

    Recebe:
        file_path: Caminho absoluto ou relativo do arquivo JSON.

    Retorna:
        Conteúdo JSON carregado ou None se o arquivo nao existir ou for inválido.
    """
    if not file_path.exists():
        print(f"AVISO: Arquivo nao encontrado: {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as error:
        print(f"ERRO: Falha ao decodificar JSON em {file_path}: {error}")
        return None


def extract_diet_name(file_path: Path) -> str:
    """Extrai o nome canônico da dieta a partir do caminho do arquivo.

    Recebe:
        file_path: Caminho do JSON de dieta contendo regular, vegetariana ou vegana.

    Retorna:
        Nome canônico da dieta com capitalizacao padrao.
    """
    file_name = file_path.stem.lower()
    for expected_name in ORDEM_DIETAS_PADRAO:
        if expected_name.lower() in file_name:
            return expected_name
    return file_path.stem.replace("dietas-", "").replace("otimizada-", "").title()


def evaluate_diet_diversity(diets: List[Dict]) -> Tuple[int, int, float]:
    """Avalia a diversidade de cardápios e a presenca de arroz com feijao.

    Recebe:
        diets: Lista de dicionários com planos de dieta.

    Retorna:
        Tupla com quantidade de dias únicos, total de dias e taxa (%) de almocos
        com arroz e feijao.
    """
    daily_signatures = set()
    total_days = 0
    total_lunches = 0
    lunches_with_rice_beans = 0

    for diet_plan in diets:
        for _day_index, meals in diet_plan.items():
            if not isinstance(meals, dict):
                continue

            total_days += 1
            day_signature = []

            for meal_name, items in meals.items():
                if not isinstance(items, list):
                    continue

                food_names = [
                    str(item.get("alimento", "")).strip().lower()
                    for item in items
                    if item.get("alimento")
                ]
                day_signature.append(
                    (meal_name.strip().lower(), tuple(sorted(food_names)))
                )

                normalized_meal_name = (
                    unicodedata.normalize("NFKD", meal_name.strip().lower())
                    .encode("ascii", "ignore")
                    .decode("ascii")
                )
                if normalized_meal_name == "almoco":
                    total_lunches += 1
                    has_rice = any("arroz" in food for food in food_names)
                    has_beans = any(
                        "feijao" in food
                        or "feijao"
                        in unicodedata.normalize("NFKD", food)
                        .encode("ascii", "ignore")
                        .decode("ascii")
                        for food in food_names
                    )
                    if has_rice and has_beans:
                        lunches_with_rice_beans += 1

            daily_signatures.add(tuple(day_signature))

    rice_beans_rate = (
        (lunches_with_rice_beans / total_lunches * 100) if total_lunches else 0.0
    )
    return len(daily_signatures), total_days, rice_beans_rate


def _normalize_nutrient_names(raw_name: str) -> str:
    """Normaliza nomes de nutrientes para as chaves canônicas com acentuação portuguesa.

    Mantém a grafia original quando já está correta; corrige variantes sem
    acento para a forma canônica utilizada pela TBCA.

    Recebe:
        raw_name: Nome do nutriente vindo dos mapas nutricionais.

    Retorna:
        Nome canônico com acentuação portuguesa correta.
    """
    stripped = raw_name.strip()
    ascii_form = (
        unicodedata.normalize("NFKD", stripped)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    ascii_to_canonical = {
        "Proteina": "Proteína",
        "Lipidios": "Lipídios",
        "Calcio": "Cálcio",
        "Magnesio": "Magnésio",
        "Sodio": "Sódio",
        "Pegada Hidrica": "Pegada Hídrica",
        "Pegada Ecologica": "Pegada Ecológica",
    }
    return ascii_to_canonical.get(ascii_form, stripped)


def calculate_nutritional_values(
    diets: List[Dict],
    tbca_map: Dict,
    tbca_database: Dict,
    footprint_map: Dict,
) -> Tuple[Dict, Dict, set, set]:
    """Calcula totais de nutrientes e pegadas por dia e por refeicao.

    Recebe:
        diets: Lista de planos de dieta.
        tbca_map: Mapa nome do alimento -> codigo TBCA.
        tbca_database: Base de nutrientes TBCA indexada por codigo.
        footprint_map: Mapa de pegadas ambientais indexado por alimento.

    Retorna:
        Tupla com totais diários, totais por refeicao, alimentos ausentes na TBCA
        e alimentos ausentes no mapa de pegadas.
    """
    daily_totals = defaultdict(lambda: defaultdict(list))
    meal_totals = defaultdict(lambda: defaultdict(list))
    missing_in_tbca = set()
    missing_in_footprint = set()

    for diet_plan in diets:
        for _day, meals in diet_plan.items():
            if not isinstance(meals, dict):
                continue

            day_nutrients = defaultdict(float)

            for meal_name, items in meals.items():
                if not isinstance(items, list):
                    continue

                meal_nutrients = defaultdict(float)

                for item in items:
                    food_name = item.get("alimento")
                    if not food_name:
                        continue

                    quantity_raw = str(item.get("quantidade", "0")).replace(",", ".")
                    try:
                        quantity_grams = float(quantity_raw)
                    except ValueError:
                        quantity_grams = 0.0

                    tbca_code = tbca_map.get(food_name)
                    if tbca_code and tbca_code in tbca_database:
                        factor_tbca = quantity_grams / GRAMAS_REFERENCIA_TBCA
                        for nutrient_name, value_per_100g in (
                            tbca_database[tbca_code].get("nutrientes", {}).items()
                        ):
                            normalized_name = _normalize_nutrient_names(nutrient_name)
                            meal_nutrients[normalized_name] += (
                                float(value_per_100g) * factor_tbca
                            )
                    else:
                        missing_in_tbca.add(food_name)

                    if food_name in footprint_map:
                        factor_pegada = quantity_grams / GRAMAS_REFERENCIA_PEGADA
                        pegadas = footprint_map[food_name]
                        meal_nutrients["Pegada de Carbono"] += (
                            float(pegadas.get("carbon_footprint", 0.0)) * factor_pegada
                        )
                        meal_nutrients["Pegada Hídrica"] += (
                            float(pegadas.get("water_footprint", 0.0)) * factor_pegada
                        )
                        meal_nutrients["Pegada Ecológica"] += (
                            float(pegadas.get("ecological_footprint", 0.0))
                            * factor_pegada
                        )
                    else:
                        missing_in_footprint.add(food_name)

                for nutrient, value in meal_nutrients.items():
                    meal_totals[meal_name][nutrient].append(value)
                    day_nutrients[nutrient] += value

            for nutrient, value in day_nutrients.items():
                daily_totals["Geral"][nutrient].append(value)

    return daily_totals, meal_totals, missing_in_tbca, missing_in_footprint


def generate_text_report(
    output_path: Path,
    diet_name: str,
    total_days: int,
    unique_days: int,
    rice_beans_rate: float,
    daily_totals: Dict,
    meal_totals: Dict,
    missing_in_tbca: set,
    missing_in_footprint: set,
) -> None:
    """Gera relatorio textual com estatísticas comportamentais e nutricionais.

    Recebe:
        output_path: Caminho do arquivo TXT de saida.
        diet_name: Nome canônico da dieta.
        total_days: Número total de dias simulados.
        unique_days: Número de assinaturas diárias distintas.
        rice_beans_rate: Taxa de almocos com arroz e feijao.
        daily_totals: Mapa de totais diários.
        meal_totals: Mapa de totais por refeicao.
        missing_in_tbca: Alimentos ausentes no mapa TBCA.
        missing_in_footprint: Alimentos ausentes no mapa de pegadas.

    Retorna:
        None. Escreve o arquivo de relatorio em disco.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:

        def log(message: str) -> None:
            """Escreve uma linha no arquivo de relatorio atual.

            Recebe:
                message: Linha de texto.

            Retorna:
                None.
            """
            file.write(message + "\n")

        log(f"--- Relatorio Analitico: Dieta {diet_name} ---")
        log("========================================")
        log("ESTATISTICAS DO MODELO (COMPORTAMENTO)")
        log(f"Total de dias simulados: {total_days}")
        log(f"Dietas (dias) efetivamente unicas geradas: {unique_days}")
        variety_rate = (unique_days / total_days * 100) if total_days else 0.0
        log(f"Taxa de originalidade (variedade): {variety_rate:.1f}%")
        log(f"Taxa de presenca de Arroz e Feijao no Almoco: {rice_beans_rate:.1f}%")
        log("========================================\n")

        def format_section(title: str, data_dict: Dict) -> None:
            """Formata e escreve uma secao do relatorio.

            Recebe:
                title: Título da secao.
                data_dict: Mapa de categoria para series de nutrientes.

            Retorna:
                None.
            """
            log(f"\n>> {title}")
            key_nutrients = [
                "Energia",
                "Pegada de Carbono",
                "Pegada Hídrica",
                "Pegada Ecológica",
                "Carboidrato total",
                "Proteína",
                "Lipídios",
                "Fibra alimentar",
                "Sódio",
            ]
            expected_meal_order = [
                "Geral",
                "Cafe da Manha",
                "Lanche da Manha",
                "Almoco",
                "Lanche da Tarde",
                "Jantar",
                "Ceia",
                "Cafe da Manha",
                "Lanche da Manha",
                "Almoco",
            ]
            present_categories = [
                meal for meal in expected_meal_order if meal in data_dict
            ]
            present_categories += [
                meal for meal in data_dict.keys() if meal not in present_categories
            ]

            for category in present_categories:
                nutrients_map = data_dict[category]
                log(f"   [{category.upper()}]")

                available_nutrients = set(nutrients_map.keys())
                ordered_keys = [
                    key for key in key_nutrients if key in available_nutrients
                ]
                ordered_keys += sorted(list(available_nutrients - set(key_nutrients)))

                for nutrient in ordered_keys:
                    values = nutrients_map[nutrient]
                    if not values:
                        continue

                    mean_value = statistics.mean(values)
                    stdev_value = statistics.stdev(values) if len(values) > 1 else 0.0
                    if mean_value <= 0.1:
                        continue

                    if nutrient == "Energia":
                        unit = "kcal"
                    elif nutrient == "Sódio":
                        unit = "mg"
                    elif "Pegada" in nutrient:
                        unit = ""
                    else:
                        unit = "g"
                    log(
                        f"    {nutrient:.<25} {mean_value:>8.2f} +/- {stdev_value:<6.2f} {unit}"
                    )

        format_section("MEDIA DIARIA (RESUMO)", daily_totals)
        format_section("MEDIA POR REFEICAO", meal_totals)

        if missing_in_tbca or missing_in_footprint:
            log("\n========================================")
            log("ALIMENTOS NAO MAPEADOS (AVISOS)")
            log("========================================")
            if missing_in_tbca:
                log("\n--- Ausentes na base TBCA ---")
                for item in sorted(missing_in_tbca):
                    log(item)
            if missing_in_footprint:
                log("\n--- Ausentes na base de Pegadas Ambientais ---")
                for item in sorted(missing_in_footprint):
                    log(item)


def _dynamic_order(consolidated_data: Dict[str, Dict[str, float]]) -> List[str]:
    """Monta ordem dinâmica de dietas mantendo a prioridade padrao.

    Recebe:
        consolidated_data: Mapa dieta -> valores agregados.

    Retorna:
        Lista ordenada de nomes de dieta.
    """
    present_diets = list(consolidated_data.keys())
    order = [diet for diet in ORDEM_DIETAS_PADRAO if diet in present_diets]
    order.extend([diet for diet in present_diets if diet not in order])
    return order


def _format_bar_value(value: float) -> str:
    """Formata rotulos de barras de acordo com a escala do valor.

    Recebe:
        value: Altura numerica da barra.

    Retorna:
        Texto formatado para o rotulo.
    """
    if value >= 1000:
        return f"{value:.0f}"
    if value >= 100:
        return f"{value:.1f}"
    if value >= 10:
        return f"{value:.2f}"
    return f"{value:.3f}"


def _annotate_bars(axis: plt.Axes, rotation: int = 60) -> None:
    """Anota o valor de cada barra acima da coluna.

    Recebe:
        axis: Eixo Matplotlib contendo as barras.
        rotation: Ã‚ngulo de rotacao dos rotulos.

    Retorna:
        None.
    """
    max_height = max((patch.get_height() for patch in axis.patches), default=0.0)
    offset = max(max_height * 0.01, 0.02)

    for patch in axis.patches:
        height = patch.get_height()
        if height <= 0:
            continue
        center_x = patch.get_x() + (patch.get_width() / 2)
        axis.text(
            center_x,
            height + offset,
            _format_bar_value(float(height)),
            ha="center",
            va="bottom",
            rotation=rotation,
            fontsize=14,
            fontweight="bold",
            clip_on=False,
        )

    current_bottom, current_top = axis.get_ylim()
    desired_top = (max_height + offset) * 1.18 if max_height > 0 else current_top
    if desired_top > current_top:
        axis.set_ylim(current_bottom, desired_top)


def _style_axis_for_bars(
    axis: plt.Axes,
    x_rotation: int,
    y_label: str,
) -> None:
    """Aplica estilo visual consistente para graficos de barras.

    Recebe:
        axis: Eixo Matplotlib.
        x_rotation: Ã‚ngulo de rotacao dos ticks do eixo X.
        y_label: Rotulo do eixo Y.

    Retorna:
        None.
    """
    axis.set_xlabel("")
    axis.set_ylabel(y_label, fontsize=14)
    axis.tick_params(axis="x", labelsize=14)
    axis.tick_params(axis="y", labelsize=14)
    x_alignment = "center" if x_rotation == 0 else "right"
    plt.xticks(rotation=x_rotation, ha=x_alignment)


def plot_macro_chart(
    consolidated_data: Dict[str, Dict[str, float]],
    output_dir: Path,
    color_palette: Optional[Dict[str, str]] = None,
) -> None:
    """Gera grafico de adequacao de macronutrientes para um grupo de dietas.

    Recebe:
        consolidated_data: Mapa dieta -> medias diárias de nutrientes.
        output_dir: Pasta de saida.
        color_palette: Paleta de cores {nome_dieta: cor}. Usa CORES_DIETAS_GA se None.

    Retorna:
        None. Salva PNG em disco.
    """
    palette = color_palette if color_palette is not None else CORES_DIETAS_GA
    df_macro = pd.DataFrame(
        [
            {
                "Dieta": diet,
                "Nutriente": MAPA_NOMES_GRAFICO.get(macro, macro),
                "Percentual (%)": (
                    nutrients.get(macro, 0.0) / METAS_NUTRICIONAIS.get(macro, 1.0)
                )
                * 100,
            }
            for diet, nutrients in consolidated_data.items()
            for macro in MACROS
        ]
    )

    plt.figure(figsize=(14, 7))
    axis = sns.barplot(
        data=df_macro,
        x="Nutriente",
        y="Percentual (%)",
        hue="Dieta",
        palette=palette,
        hue_order=_dynamic_order(consolidated_data),
        edgecolor="black",
        linewidth=1.1,
    )
    axis.axhline(100, color="red", linestyle="--", linewidth=1.0)
    _style_axis_for_bars(
        axis,
        x_rotation=30,
        y_label="Percentual da Meta (%)",
    )
    _annotate_bars(axis)
    plt.tight_layout()
    plt.savefig(output_dir / "comparativo_macronutrientes_pct.png", dpi=120)
    plt.close()


def plot_micro_chart(
    consolidated_data: Dict[str, Dict[str, float]],
    output_dir: Path,
    color_palette: Optional[Dict[str, str]] = None,
) -> None:
    """Gera grafico de adequacao de micronutrientes para um grupo de dietas.

    Recebe:
        consolidated_data: Mapa dieta -> medias diárias de nutrientes.
        output_dir: Pasta de saida.
        color_palette: Paleta de cores {nome_dieta: cor}. Usa CORES_DIETAS_GA se None.

    Retorna:
        None. Salva PNG em disco.
    """
    palette = color_palette if color_palette is not None else CORES_DIETAS_GA
    df_micro = pd.DataFrame(
        [
            {
                "Dieta": diet,
                "Nutriente": MAPA_NOMES_GRAFICO.get(micro, micro),
                "Percentual (%)": (
                    nutrients.get(micro, 0.0) / METAS_NUTRICIONAIS.get(micro, 1.0)
                )
                * 100,
            }
            for diet, nutrients in consolidated_data.items()
            for micro in MICROS
        ]
    )

    plt.figure(figsize=(17, 8))
    axis = sns.barplot(
        data=df_micro,
        x="Nutriente",
        y="Percentual (%)",
        hue="Dieta",
        palette=palette,
        hue_order=_dynamic_order(consolidated_data),
        edgecolor="black",
        linewidth=1.0,
    )
    axis.axhline(100, color="red", linestyle="--", linewidth=1.0)
    _style_axis_for_bars(
        axis,
        x_rotation=45,
        y_label="Percentual da Meta (%)",
    )
    _annotate_bars(axis)
    plt.tight_layout()
    plt.savefig(output_dir / "comparativo_micronutrientes_pct.png", dpi=120)
    plt.close()


def _plot_single_footprint_chart(
    consolidated_data: Dict[str, Dict[str, float]],
    output_dir: Path,
    footprint_name: str,
    color_palette: Optional[Dict[str, str]] = None,
) -> None:
    """Gera um grafico dedicado para um tipo de pegada ambiental.

    Recebe:
        consolidated_data: Mapa dieta -> medias diárias de nutrientes e pegadas.
        output_dir: Pasta de saida.
        footprint_name: Metrica de pegada a ser exibida.
        color_palette: Paleta de cores {nome_dieta: cor}. Usa CORES_DIETAS_GA se None.

    Retorna:
        None. Salva um arquivo PNG.
    """
    palette = color_palette if color_palette is not None else CORES_DIETAS_GA
    chart_rows = [
        {
            "Dieta": diet,
            "Pegada": footprint_name,
            "Valor": nutrients.get(footprint_name, 0.0),
        }
        for diet, nutrients in consolidated_data.items()
    ]
    frame = pd.DataFrame(chart_rows)

    plt.figure(figsize=(11, 6))
    axis = sns.barplot(
        data=frame,
        x="Dieta",
        y="Valor",
        hue="Dieta",
        palette=palette,
        hue_order=_dynamic_order(consolidated_data),
        dodge=False,
        edgecolor="black",
        linewidth=1.1,
        legend=False,
    )
    _style_axis_for_bars(
        axis,
        x_rotation=20,
        y_label="Valor medio diário",
    )
    _annotate_bars(axis)
    plt.tight_layout()
    suffix = CHAVE_PEGADA_PARA_ARQUIVO.get(footprint_name, footprint_name.lower())
    plt.savefig(output_dir / f"comparativo_pegada_{suffix}.png", dpi=120)
    plt.close()


def plot_footprint_charts(
    consolidated_data: Dict[str, Dict[str, float]],
    output_dir: Path,
    color_palette: Optional[Dict[str, str]] = None,
) -> None:
    """Gera um grafico ambiental separado para cada tipo de pegada.

    Recebe:
        consolidated_data: Mapa dieta -> medias diárias de nutrientes e pegadas.
        output_dir: Pasta de saida.
        color_palette: Paleta de cores {nome_dieta: cor}. Usa CORES_DIETAS_GA se None.

    Retorna:
        None.
    """
    for footprint_name in PEGADAS:
        _plot_single_footprint_chart(
            consolidated_data, output_dir, footprint_name, color_palette
        )


def plot_group_charts(
    consolidated_data: Dict[str, Dict[str, float]],
    output_dir: Path,
    group_title: str,
    color_palette: Optional[Dict[str, str]] = None,
) -> None:
    """Gera todos os graficos de um grupo de dietas (base, AG ou PL).

    Recebe:
        consolidated_data: Mapa dieta -> medias diárias de nutrientes.
        output_dir: Diretorio de saida do grupo.
        group_title: Título descritivo para mensagens de log.
        color_palette: Paleta de cores {nome_dieta: cor}. Usa CORES_DIETAS_GA se None.

    Retorna:
        None.
    """
    if not consolidated_data:
        print(f"INFO: Nenhum dado consolidado para o grupo {group_title}.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")
    plot_macro_chart(consolidated_data, output_dir, color_palette)
    plot_micro_chart(consolidated_data, output_dir, color_palette)
    plot_footprint_charts(consolidated_data, output_dir, color_palette)
    print(f"Graficos gerados para {group_title}: {output_dir}")


def _palette_base_vs_optimized(diet_name: str) -> Dict[str, str]:
    """Cria a paleta de comparacao base (clara) vs AG (regular).

    Recebe:
        diet_name: Nome da dieta (Regular, Vegetariana ou Vegana).

    Retorna:
        Dicionário com as cores para Base e AG.
    """
    return {
        "Base": CORES_DIETAS_BASE.get(diet_name, "#93abd0"),
        "AG": CORES_DIETAS_GA.get(diet_name, "#4c72b0"),
    }


def _palette_ga_vs_linear(diet_name: str, linear_label: str = "PL") -> Dict[str, str]:
    """Cria a paleta de comparacao AG (regular) vs PL (escura).

    Recebe:
        diet_name:    Nome da dieta (Regular, Vegetariana ou Vegana).
        linear_label: Rotulo exato usado para o grupo linear no grafico.

    Retorna:
        Dicionário com as cores para AG e para o rotulo linear.
    """
    return {
        "AG": CORES_DIETAS_GA.get(diet_name, "#4c72b0"),
        linear_label: CORES_DIETAS_LINEAR.get(diet_name, "#35507b"),
    }


def _build_base_vs_optimized_rows(
    base_data: Dict[str, Dict[str, float]],
    optimized_data: Dict[str, Dict[str, float]],
    diet_name: str,
    metrics: List[str],
    metric_column_name: str,
    value_builder,
    label_a: str = "Base",
    label_b: str = "AG",
) -> pd.DataFrame:
    """Monta DataFrame longo para graficos comparativos entre dois grupos.

    Recebe:
        base_data: Metricas consolidadas do primeiro grupo.
        optimized_data: Metricas consolidadas do segundo grupo.
        diet_name: Nome canônico da dieta.
        metrics: Nomes das metricas incluídas no comparativo.
        metric_column_name: Nome da coluna que guarda o rotulo da metrica.
        value_builder: Funcao que converte (metrica, mapa de nutrientes) em valor.
        label_a: Rotulo do primeiro grupo (padrao: 'Base').
        label_b: Rotulo do segundo grupo (padrao: 'AG').

    Retorna:
        DataFrame com colunas Tipo, metric_column_name e Valor.
    """
    rows = []
    for metric in metrics:
        rows.append(
            {
                "Tipo": label_a,
                metric_column_name: MAPA_NOMES_GRAFICO.get(metric, metric),
                "Valor": value_builder(metric, base_data[diet_name]),
            }
        )
        rows.append(
            {
                "Tipo": label_b,
                metric_column_name: MAPA_NOMES_GRAFICO.get(metric, metric),
                "Valor": value_builder(metric, optimized_data[diet_name]),
            }
        )
    return pd.DataFrame(rows)


def _build_multi_group_rows(
    data_by_label: Dict[str, Dict[str, Dict[str, float]]],
    diet_name: str,
    metrics: List[str],
    metric_column_name: str,
    value_builder,
) -> pd.DataFrame:
    """Monta DataFrame longo para comparativos de 2 ou mais grupos.

    Recebe:
        data_by_label: Mapa rotulo -> mapa dieta -> metricas consolidadas.
        diet_name: Nome canônico da dieta.
        metrics: Nomes das metricas incluídas no comparativo.
        metric_column_name: Nome da coluna de metrica no DataFrame.
        value_builder: Funcao que converte (metrica, mapa de nutrientes) em valor.

    Retorna:
        DataFrame com colunas Tipo, metrica e Valor.
    """
    rows = []
    for metric in metrics:
        for label, group_data in data_by_label.items():
            rows.append(
                {
                    "Tipo": label,
                    metric_column_name: MAPA_NOMES_GRAFICO.get(metric, metric),
                    "Valor": value_builder(metric, group_data[diet_name]),
                }
            )
    return pd.DataFrame(rows)


def _plot_comparison_nutrients(
    data_by_label: Dict[str, Dict[str, Dict[str, float]]],
    diet_name: str,
    output_dir: Path,
    palette: Dict[str, str],
    file_suffix: str,
) -> None:
    """Gera comparativos de macro e micronutrientes para múltiplos grupos.

    Recebe:
        data_by_label: Mapa rotulo -> mapa dieta -> metricas consolidadas.
        diet_name: Nome canônico da dieta.
        output_dir: Diretorio de saida.
        palette: Paleta {rotulo: cor}.
        file_suffix: Sufixo para o nome dos arquivos.

    Retorna:
        None.
    """
    macro_df = _build_multi_group_rows(
        data_by_label,
        diet_name,
        metrics=MACROS,
        metric_column_name="Nutriente",
        value_builder=lambda metric, nutrients: (
            nutrients.get(metric, 0.0) / METAS_NUTRICIONAIS.get(metric, 1.0)
        )
        * 100,
    )

    plt.figure(figsize=(14, 7))
    axis = sns.barplot(
        data=macro_df,
        x="Nutriente",
        y="Valor",
        hue="Tipo",
        palette=palette,
        hue_order=list(data_by_label.keys()),
        edgecolor="black",
        linewidth=1.0,
    )
    axis.axhline(100, color="red", linestyle="--", linewidth=1.0)
    _style_axis_for_bars(axis, x_rotation=30, y_label="Percentual da Meta (%)")
    _annotate_bars(axis)
    plt.tight_layout()
    plt.savefig(
        output_dir / f"comparativo_{diet_name.lower()}_macro_{file_suffix}.png",
        dpi=120,
    )
    plt.close()

    micro_df = _build_multi_group_rows(
        data_by_label,
        diet_name,
        metrics=MICROS,
        metric_column_name="Nutriente",
        value_builder=lambda metric, nutrients: (
            nutrients.get(metric, 0.0) / METAS_NUTRICIONAIS.get(metric, 1.0)
        )
        * 100,
    )

    plt.figure(figsize=(17, 8))
    axis = sns.barplot(
        data=micro_df,
        x="Nutriente",
        y="Valor",
        hue="Tipo",
        palette=palette,
        hue_order=list(data_by_label.keys()),
        edgecolor="black",
        linewidth=1.0,
    )
    axis.axhline(100, color="red", linestyle="--", linewidth=1.0)
    _style_axis_for_bars(axis, x_rotation=45, y_label="Percentual da Meta (%)")
    _annotate_bars(axis)
    plt.tight_layout()
    plt.savefig(
        output_dir / f"comparativo_{diet_name.lower()}_micro_{file_suffix}.png",
        dpi=120,
    )
    plt.close()


def _plot_comparison_footprints(
    data_by_label: Dict[str, Dict[str, Dict[str, float]]],
    diet_name: str,
    output_dir: Path,
    palette: Dict[str, str],
    file_suffix: str,
) -> None:
    """Gera comparativos de pegadas para múltiplos grupos.

    Recebe:
        data_by_label: Mapa rotulo -> mapa dieta -> metricas consolidadas.
        diet_name: Nome canônico da dieta.
        output_dir: Diretorio de saida.
        palette: Paleta {rotulo: cor}.
        file_suffix: Sufixo para o nome dos arquivos.

    Retorna:
        None.
    """
    for footprint_name in PEGADAS:
        rows = []
        for label, group_data in data_by_label.items():
            rows.append(
                {
                    "Tipo": label,
                    "Pegada": footprint_name,
                    "Valor": group_data[diet_name].get(footprint_name, 0.0),
                }
            )
        frame = pd.DataFrame(rows)

        plt.figure(figsize=(9, 6))
        axis = sns.barplot(
            data=frame,
            x="Tipo",
            y="Valor",
            hue="Tipo",
            palette=palette,
            hue_order=list(data_by_label.keys()),
            edgecolor="black",
            linewidth=1.0,
            dodge=False,
            legend=False,
        )
        _style_axis_for_bars(axis, x_rotation=0, y_label="Valor medio diário")
        _annotate_bars(axis)
        plt.tight_layout()
        footprint_key = CHAVE_PEGADA_PARA_ARQUIVO[footprint_name]
        plt.savefig(
            output_dir
            / f"comparativo_{diet_name.lower()}_pegada_{footprint_key}_{file_suffix}.png",
            dpi=120,
        )
        plt.close()


def _plot_base_vs_optimized_nutrients(
    base_data: Dict[str, Dict[str, float]],
    optimized_data: Dict[str, Dict[str, float]],
    diet_name: str,
    output_dir: Path,
    palette: Optional[Dict[str, str]] = None,
    label_a: str = "Base",
    label_b: str = "AG",
    file_suffix: str = "base_vs_ag",
) -> None:
    """Gera comparativos de macro e micronutrientes entre dois grupos para uma dieta.

    Recebe:
        base_data: Metricas consolidadas do primeiro grupo.
        optimized_data: Metricas consolidadas do segundo grupo.
        diet_name: Nome canônico da dieta.
        output_dir: Diretorio de saida.
        palette: Paleta {rotulo: cor}. Usa _palette_base_vs_optimized se None.
        label_a: Rotulo do primeiro grupo.
        label_b: Rotulo do segundo grupo.
        file_suffix: Sufixo do nome do arquivo PNG.

    Retorna:
        None.
    """
    if palette is None:
        palette = _palette_base_vs_optimized(diet_name)
    macro_df = _build_base_vs_optimized_rows(
        base_data,
        optimized_data,
        diet_name,
        metrics=MACROS,
        metric_column_name="Nutriente",
        value_builder=lambda metric, nutrients: (
            nutrients.get(metric, 0.0) / METAS_NUTRICIONAIS.get(metric, 1.0)
        )
        * 100,
        label_a=label_a,
        label_b=label_b,
    )

    plt.figure(figsize=(14, 7))
    axis = sns.barplot(
        data=macro_df,
        x="Nutriente",
        y="Valor",
        hue="Tipo",
        palette=palette,
        edgecolor="black",
        linewidth=1.0,
    )
    axis.axhline(100, color="red", linestyle="--", linewidth=1.0)
    _style_axis_for_bars(
        axis,
        x_rotation=30,
        y_label="Percentual da Meta (%)",
    )
    _annotate_bars(axis)
    plt.tight_layout()
    plt.savefig(
        output_dir / f"comparativo_{diet_name.lower()}_macro_{file_suffix}.png",
        dpi=120,
    )
    plt.close()

    micro_df = _build_base_vs_optimized_rows(
        base_data,
        optimized_data,
        diet_name,
        metrics=MICROS,
        metric_column_name="Nutriente",
        value_builder=lambda metric, nutrients: (
            nutrients.get(metric, 0.0) / METAS_NUTRICIONAIS.get(metric, 1.0)
        )
        * 100,
        label_a=label_a,
        label_b=label_b,
    )

    plt.figure(figsize=(17, 8))
    axis = sns.barplot(
        data=micro_df,
        x="Nutriente",
        y="Valor",
        hue="Tipo",
        palette=palette,
        edgecolor="black",
        linewidth=1.0,
    )
    axis.axhline(100, color="red", linestyle="--", linewidth=1.0)
    _style_axis_for_bars(
        axis,
        x_rotation=45,
        y_label="Percentual da Meta (%)",
    )
    _annotate_bars(axis)
    plt.tight_layout()
    plt.savefig(
        output_dir / f"comparativo_{diet_name.lower()}_micro_{file_suffix}.png",
        dpi=120,
    )
    plt.close()


def _plot_base_vs_optimized_footprints(
    base_data: Dict[str, Dict[str, float]],
    optimized_data: Dict[str, Dict[str, float]],
    diet_name: str,
    output_dir: Path,
    palette: Optional[Dict[str, str]] = None,
    label_a: str = "Base",
    label_b: str = "AG",
    file_suffix: str = "base_vs_ag",
) -> None:
    """Gera comparativos de pegadas entre dois grupos para uma dieta.

    Recebe:
        base_data: Metricas consolidadas do primeiro grupo.
        optimized_data: Metricas consolidadas do segundo grupo.
        diet_name: Nome canônico da dieta.
        output_dir: Diretorio de saida.
        palette: Paleta {rotulo: cor}. Usa _palette_base_vs_optimized se None.
        label_a: Rotulo do primeiro grupo.
        label_b: Rotulo do segundo grupo.
        file_suffix: Sufixo do nome do arquivo PNG.

    Retorna:
        None.
    """
    if palette is None:
        palette = _palette_base_vs_optimized(diet_name)
    for footprint_name in PEGADAS:
        frame = pd.DataFrame(
            [
                {
                    "Tipo": label_a,
                    "Pegada": footprint_name,
                    "Valor": base_data[diet_name].get(footprint_name, 0.0),
                },
                {
                    "Tipo": label_b,
                    "Pegada": footprint_name,
                    "Valor": optimized_data[diet_name].get(footprint_name, 0.0),
                },
            ]
        )

        plt.figure(figsize=(9, 6))
        axis = sns.barplot(
            data=frame,
            x="Tipo",
            y="Valor",
            hue="Tipo",
            palette=palette,
            edgecolor="black",
            linewidth=1.0,
            dodge=False,
            legend=False,
        )
        _style_axis_for_bars(
            axis,
            x_rotation=0,
            y_label="Valor medio diário",
        )
        _annotate_bars(axis)
        plt.tight_layout()
        footprint_key = CHAVE_PEGADA_PARA_ARQUIVO[footprint_name]
        plt.savefig(
            output_dir
            / f"comparativo_{diet_name.lower()}_pegada_{footprint_key}_{file_suffix}.png",
            dpi=120,
        )
        plt.close()


def plot_base_vs_optimized_charts(
    base_data: Dict[str, Dict[str, float]],
    optimized_data: Dict[str, Dict[str, float]],
    output_dir: Path,
) -> None:
    """Gera todos os comparativos base vs AG por tipo de dieta.

    Recebe:
        base_data: Metricas consolidadas das dietas base.
        optimized_data: Metricas consolidadas das dietas otimizadas por AG.
        output_dir: Pasta de saida dos comparativos.

    Retorna:
        None.
    """
    common_diets = [
        diet
        for diet in ORDEM_DIETAS_PADRAO
        if diet in base_data and diet in optimized_data
    ]

    if not common_diets:
        print("INFO: Nao ha dietas em comum entre base e AG para gerar comparativos.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    for diet_name in common_diets:
        palette = _palette_base_vs_optimized(diet_name)
        _plot_base_vs_optimized_nutrients(
            base_data,
            optimized_data,
            diet_name,
            output_dir,
            palette=palette,
            label_b="AG",
            file_suffix="base_vs_ag",
        )
        _plot_base_vs_optimized_footprints(
            base_data,
            optimized_data,
            diet_name,
            output_dir,
            palette=palette,
            label_b="AG",
            file_suffix="base_vs_ag",
        )

    print(f"Graficos comparativos base vs AG gerados em: {output_dir}")


def plot_ga_vs_linear_charts(
    ga_data: Dict[str, Dict[str, float]],
    linear_data: Dict[str, Dict[str, float]],
    output_dir: Path,
    linear_label: str = "PL",
    base_data: Optional[Dict[str, Dict[str, float]]] = None,
    ag_label: str = "AG",
) -> None:
    """Gera comparativos AG vs Programacao Linear por tipo de dieta.

    Recebe:
        ga_data:      Metricas consolidadas das dietas otimizadas por AG.
        linear_data:  Metricas consolidadas das dietas otimizadas por PL.
        output_dir:   Pasta de saida dos comparativos.
        linear_label: Rotulo para o grupo linear no grafico (padrao: 'PL').

    Retorna:
        None.
    """
    common_diets = [
        diet for diet in ORDEM_DIETAS_PADRAO if diet in ga_data and diet in linear_data
    ]
    include_base = base_data is not None
    if include_base:
        common_diets = [diet for diet in common_diets if diet in base_data]

    if not common_diets:
        print(
            "INFO: Nao ha dietas em comum entre AG, PL e base para gerar comparativos."
            if include_base
            else "INFO: Nao ha dietas em comum entre AG e PL para gerar comparativos."
        )
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    for diet_name in common_diets:
        comparison_data: Dict[str, Dict[str, Dict[str, float]]] = {}
        comparison_data[ag_label] = ga_data
        comparison_data[linear_label] = linear_data
        if include_base and base_data is not None:
            comparison_data = {
                "Base": base_data,
                ag_label: ga_data,
                linear_label: linear_data,
            }

        palette = {
            "Base": CORES_DIETAS_BASE.get(diet_name, "#93abd0"),
            ag_label: CORES_DIETAS_GA.get(diet_name, "#4c72b0"),
            linear_label: CORES_DIETAS_LINEAR.get(diet_name, "#35507b"),
        }
        palette = {label: palette[label] for label in comparison_data.keys()}

        safe_linear_label = (
            unicodedata.normalize("NFKD", linear_label.lower())
            .encode("ascii", "ignore")
            .decode("ascii")
            .replace(" ", "_")
            .replace("-", "_")
        )
        file_suffix = (
            f"base_ag_vs_{safe_linear_label}"
            if include_base
            else f"ag_vs_{safe_linear_label}"
        )

        _plot_comparison_nutrients(
            data_by_label=comparison_data,
            diet_name=diet_name,
            output_dir=output_dir,
            palette=palette,
            file_suffix=file_suffix,
        )
        _plot_comparison_footprints(
            data_by_label=comparison_data,
            diet_name=diet_name,
            output_dir=output_dir,
            palette=palette,
            file_suffix=file_suffix,
        )

    print(
        f"Graficos comparativos {ag_label} vs {linear_label} gerados em: {output_dir}"
    )


def plot_base_vs_linear_charts(
    base_data: Dict[str, Dict[str, float]],
    linear_data: Dict[str, Dict[str, float]],
    output_dir: Path,
    linear_label: str,
    include_footprints: bool = False,
) -> None:
    """Gera comparativos base vs Programacao Linear por tipo de dieta.

    Recebe:
        base_data: Metricas consolidadas das dietas base.
        linear_data: Metricas consolidadas das dietas otimizadas por PL.
        output_dir: Pasta de saida dos comparativos.
        linear_label: Rotulo para o grupo linear no grafico.
        include_footprints: Se True, inclui graficos de pegada (pode ter deadlock matplotlib).

    Retorna:
        None.
    """
    common_diets = [
        diet
        for diet in ORDEM_DIETAS_PADRAO
        if diet in base_data and diet in linear_data
    ]
    if not common_diets:
        print("INFO: Nao ha dietas em comum entre base e PL para gerar comparativos.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_linear_label = (
        unicodedata.normalize("NFKD", linear_label.lower())
        .encode("ascii", "ignore")
        .decode("ascii")
        .replace(" ", "_")
        .replace("-", "_")
    )

    for diet_name in common_diets:
        comparison_data = {"Base": base_data, linear_label: linear_data}
        palette = {
            "Base": CORES_DIETAS_BASE.get(diet_name, "#93abd0"),
            linear_label: CORES_DIETAS_LINEAR.get(diet_name, "#35507b"),
        }
        _plot_comparison_nutrients(
            data_by_label=comparison_data,
            diet_name=diet_name,
            output_dir=output_dir,
            palette=palette,
            file_suffix=f"base_vs_{safe_linear_label}",
        )
        if include_footprints:
            _plot_comparison_footprints(
                data_by_label=comparison_data,
                diet_name=diet_name,
                output_dir=output_dir,
                palette=palette,
                file_suffix=f"base_vs_{safe_linear_label}",
            )

    print(f"Graficos comparativos base vs {linear_label} gerados em: {output_dir}")


def resolve_diet_file_groups(project_root: Path) -> Dict[str, List[Path]]:
    """Resolve os arquivos canônicos de dieta agrupados por origem.

    Recebe:
        project_root: Diretorio raiz do projeto.

    Retorna:
        Dicionário com as chaves base, ag-alimentos, ag-refeicoes,
        pl-alimentos e pl-refeicoes mapeadas para listas ordenadas de caminhos.
    """
    optimized_dir = project_root / "data" / "outputs" / "optimized_diets"
    return {
        "base": [
            project_root / "data" / "diets" / "base" / "dietas-regular.json",
            project_root / "data" / "diets" / "base" / "dietas-vegetariana.json",
            project_root / "data" / "diets" / "base" / "dietas-vegana.json",
        ],
        RESOLUTION_AG_ALIMENTOS: [
            optimized_dir / RESOLUTION_AG_ALIMENTOS / "otimizada-dietas-regular.json",
            optimized_dir
            / RESOLUTION_AG_ALIMENTOS
            / "otimizada-dietas-vegetariana.json",
            optimized_dir / RESOLUTION_AG_ALIMENTOS / "otimizada-dietas-vegana.json",
        ],
        RESOLUTION_AG_REFEICOES: [
            optimized_dir / RESOLUTION_AG_REFEICOES / "otimizada-dietas-regular.json",
            optimized_dir
            / RESOLUTION_AG_REFEICOES
            / "otimizada-dietas-vegetariana.json",
            optimized_dir / RESOLUTION_AG_REFEICOES / "otimizada-dietas-vegana.json",
        ],
        RESOLUTION_PL_ALIMENTOS: [
            optimized_dir / RESOLUTION_PL_ALIMENTOS / "otimizada-dietas-regular.json",
            optimized_dir
            / RESOLUTION_PL_ALIMENTOS
            / "otimizada-dietas-vegetariana.json",
            optimized_dir / RESOLUTION_PL_ALIMENTOS / "otimizada-dietas-vegana.json",
        ],
        RESOLUTION_PL_REFEICOES: [
            optimized_dir / RESOLUTION_PL_REFEICOES / "otimizada-dietas-regular.json",
            optimized_dir
            / RESOLUTION_PL_REFEICOES
            / "otimizada-dietas-vegetariana.json",
            optimized_dir / RESOLUTION_PL_REFEICOES / "otimizada-dietas-vegana.json",
        ],
    }


def _get_group_color_palette(group_name: str) -> Dict[str, str]:
    """Retorna a paleta de cores adequada para um grupo de dietas.

    Recebe:
        group_name: Identificador do grupo (base, ag, linear-*).

    Retorna:
        Dicionário nome_dieta -> codigo de cor hexadecimal.
    """
    if group_name == "base":
        return CORES_DIETAS_BASE
    if group_name in {RESOLUTION_AG_ALIMENTOS, RESOLUTION_AG_REFEICOES}:
        return CORES_DIETAS_GA
    return CORES_DIETAS_LINEAR


def _remove_output_path(path: Path) -> None:
    """Remove arquivo ou diretorio de saida, se existir.

    Recebe:
        path: Caminho alvo.

    Retorna:
        None.
    """
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _prepare_output_targets(
    reports_dir: Path,
    figures_dir: Path,
    requested_groups: Dict[str, List[Path]],
) -> None:
    """Limpa saidas antigas antes de regenerar estatísticas e graficos.

    Remove diretorios e arquivos do conjunto solicitado para evitar PNGs e TXTs
    obsoletos, inclusive nomes legados com `optimized`/`otimizada`.

    Recebe:
        reports_dir: Diretorio raiz de relatorios.
        figures_dir: Diretorio raiz de figuras.
        requested_groups: Grupos efetivamente solicitados na execucao.

    Retorna:
        None.
    """
    for group_name in requested_groups:
        _remove_output_path(reports_dir / group_name)
        _remove_output_path(figures_dir / group_name)

    for stale_figure in figures_dir.glob("*.png"):
        _remove_output_path(stale_figure)

    for stale_comparison in figures_dir.glob("comparativo_*"):
        _remove_output_path(stale_comparison)

    for stale_report in reports_dir.glob("*.txt"):
        _remove_output_path(stale_report)

    if (
        RESOLUTION_AG_ALIMENTOS in requested_groups
        or RESOLUTION_AG_REFEICOES in requested_groups
    ):
        _remove_output_path(reports_dir / "optimized")
        _remove_output_path(figures_dir / "optimized")

    if "base" in requested_groups and (
        RESOLUTION_AG_ALIMENTOS in requested_groups
        or RESOLUTION_AG_REFEICOES in requested_groups
    ):
        _remove_output_path(figures_dir / "comparativo_base_vs_ag")
        _remove_output_path(figures_dir / "comparativo_base_vs_otimizada")

    if (
        RESOLUTION_AG_ALIMENTOS in requested_groups
        or RESOLUTION_AG_REFEICOES in requested_groups
    ) and RESOLUTION_PL_ALIMENTOS in requested_groups:
        _remove_output_path(figures_dir / "comparativo_ag_vs_linear_alimentos")
        _remove_output_path(figures_dir / "comparativo_ga_vs_linear_alimentos")
    if "base" in requested_groups and RESOLUTION_PL_ALIMENTOS in requested_groups:
        _remove_output_path(figures_dir / "comparativo_base_vs_linear_alimentos")

    if (
        RESOLUTION_AG_ALIMENTOS in requested_groups
        or RESOLUTION_AG_REFEICOES in requested_groups
    ) and RESOLUTION_PL_REFEICOES in requested_groups:
        _remove_output_path(figures_dir / "comparativo_ag_vs_linear_refeicoes")
        _remove_output_path(figures_dir / "comparativo_ga_vs_linear_refeicoes")
    if "base" in requested_groups and RESOLUTION_PL_REFEICOES in requested_groups:
        _remove_output_path(figures_dir / "comparativo_base_vs_linear_refeicoes")


def _build_report_file_name(group_name: str, file_path: Path) -> str:
    """Monta o nome do relatorio conforme o grupo de saida.

    Recebe:
        group_name: Grupo atual (base, ag-* ou pl-*).
        file_path: Arquivo-fonte da dieta processada.

    Retorna:
        Nome do arquivo TXT do relatorio.
    """
    report_stem = file_path.stem
    if group_name == RESOLUTION_AG_ALIMENTOS:
        report_stem = report_stem.replace("otimizada-", "ag-alimentos-")
    elif group_name == RESOLUTION_AG_REFEICOES:
        report_stem = report_stem.replace("otimizada-", "ag-refeicoes-")
    elif group_name == RESOLUTION_PL_ALIMENTOS:
        report_stem = report_stem.replace("otimizada-", "pl-alimentos-")
    elif group_name == RESOLUTION_PL_REFEICOES:
        report_stem = report_stem.replace("otimizada-", "pl-refeicoes-")
    return f"{report_stem}-estatisticas.txt"


def _filter_existing_files(diet_files: List[Path]) -> List[Path]:
    """Filtra somente os arquivos existentes de uma lista de entrada.

    Recebe:
        diet_files: Caminhos candidatos.

    Retorna:
        Caminhos existentes preservando a ordem original.
    """
    return [file_path for file_path in diet_files if file_path.exists()]


def _process_group(
    group_name: str,
    diet_files: List[Path],
    reports_dir: Path,
    figures_dir: Path,
    tbca_map: Dict,
    tbca_database: Dict,
    footprint_map: Dict,
) -> Dict[str, Dict[str, float]]:
    """Processa um grupo de dietas e gera relatorios e graficos.

    Recebe:
        group_name: Identificador do grupo (base, ag-* ou pl-*).
        diet_files: Lista de arquivos de dieta do grupo.
        reports_dir: Pasta base de relatorios.
        figures_dir: Pasta base de figuras.
        tbca_map: Mapa nome do alimento -> TBCA.
        tbca_database: Base nutricional TBCA.
        footprint_map: Mapa de pegadas ambientais.

    Retorna:
        Mapa consolidado dieta -> medias diárias de nutrientes e pegadas.
    """
    if not diet_files:
        if group_name in {RESOLUTION_AG_ALIMENTOS, RESOLUTION_AG_REFEICOES}:
            print(
                "INFO: Nenhuma dieta AG encontrada. "
                "Os graficos e relatorios de AG nao serao gerados."
            )
        else:
            print(
                f"INFO: Nenhum arquivo de dieta encontrado para o grupo {group_name}."
            )
        return {}

    consolidated_chart_data: Dict[str, Dict[str, float]] = {}
    group_reports_dir = reports_dir / group_name
    group_figures_dir = figures_dir / group_name

    for file_path in diet_files:
        diets = load_json_file(file_path)
        if not diets:
            continue

        diet_name = extract_diet_name(file_path)
        unique_days, total_days, rice_beans_rate = evaluate_diet_diversity(diets)
        daily_totals, meal_totals, missing_in_tbca, missing_in_footprint = (
            calculate_nutritional_values(
                diets,
                tbca_map,
                tbca_database,
                footprint_map,
            )
        )

        report_path = group_reports_dir / _build_report_file_name(group_name, file_path)
        generate_text_report(
            report_path,
            diet_name,
            total_days,
            unique_days,
            rice_beans_rate,
            daily_totals,
            meal_totals,
            missing_in_tbca,
            missing_in_footprint,
        )
        print(f"Relatorio gerado: {report_path}")

        mean_nutrients = {
            nutrient: statistics.mean(values)
            for nutrient, values in daily_totals["Geral"].items()
            if values
        }
        consolidated_chart_data[diet_name] = mean_nutrients

    plot_group_charts(
        consolidated_chart_data,
        group_figures_dir,
        group_title=group_name,
        color_palette=_get_group_color_palette(group_name),
    )
    return consolidated_chart_data


def _resolve_requested_groups(
    mode: str,
    grouped_files: Dict[str, List[Path]],
) -> Dict[str, List[Path]]:
    """Resolve quais grupos devem ser processados conforme o modo da CLI.

    Recebe:
          mode: Opcao de modo da CLI (base, ag-alimentos, ag-refeicoes,
              pl-alimentos, pl-refeicoes, all).
        grouped_files: Grupos canônicos de arquivos de dieta.

    Retorna:
        Dicionário com os grupos selecionados.
    """
    if mode == "base":
        return {"base": grouped_files["base"]}
    if mode in {"ag", "optimized", RESOLUTION_AG_REFEICOES}:
        return {RESOLUTION_AG_REFEICOES: grouped_files[RESOLUTION_AG_REFEICOES]}
    if mode == RESOLUTION_AG_ALIMENTOS:
        return {RESOLUTION_AG_ALIMENTOS: grouped_files[RESOLUTION_AG_ALIMENTOS]}
    if mode == RESOLUTION_PL_ALIMENTOS:
        return {RESOLUTION_PL_ALIMENTOS: grouped_files[RESOLUTION_PL_ALIMENTOS]}
    if mode == RESOLUTION_PL_REFEICOES:
        return {RESOLUTION_PL_REFEICOES: grouped_files[RESOLUTION_PL_REFEICOES]}
    return grouped_files


def _sanitize_mode_for_pipeline(mode: str) -> str:
    """Normaliza aliases de modo para manter compatibilidade retroativa.

    Recebe:
        mode: Modo bruto recebido da CLI.

    Retorna:
        Modo saneado entre base, ag-alimentos, ag-refeicoes, pl-alimentos,
        pl-refeicoes e all.
    """
    if mode == "optimized":
        return RESOLUTION_AG_REFEICOES
    if mode == "ag":
        return RESOLUTION_AG_REFEICOES
    valid = {
        "base",
        RESOLUTION_AG_ALIMENTOS,
        RESOLUTION_AG_REFEICOES,
        RESOLUTION_PL_ALIMENTOS,
        RESOLUTION_PL_REFEICOES,
        "all",
    }
    return mode if mode in valid else "all"


def _safe_label_slug(label: str) -> str:
    """Converte um rotulo em slug seguro para nomes de arquivo/pasta.

    Recebe:
        label: Texto original do rotulo.

    Retorna:
        Texto em minúsculas com separador underscore e sem acentos comuns.
    """
    slug = (
        unicodedata.normalize("NFKD", label.lower())
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return slug.replace(" ", "-").replace("_", "-")


def _plot_pairwise_with_base(
    consolidated_by_group: Dict[str, Dict[str, Dict[str, float]]],
    figures_dir: Path,
) -> None:
    """Gera comparativos 2 a 2 entre resolucoes, sempre incluindo Base.

    Recebe:
        consolidated_by_group: Mapa grupo -> dieta -> metricas.
        figures_dir: Diretorio raiz de figuras.

    Retorna:
        None.
    """
    base_data = consolidated_by_group.get("base", {})
    if not base_data:
        print("INFO: Sem dados base; comparativos 2x2 com Base nao serao gerados.")
        return

    pair_specs = [
        (
            RESOLUTION_AG_ALIMENTOS,
            "AG-Alimentos",
            RESOLUTION_AG_REFEICOES,
            "AG-Refeições",
        ),
        (
            RESOLUTION_AG_ALIMENTOS,
            "AG-Alimentos",
            RESOLUTION_PL_ALIMENTOS,
            "PL-Alimentos",
        ),
        (
            RESOLUTION_AG_ALIMENTOS,
            "AG-Alimentos",
            RESOLUTION_PL_REFEICOES,
            "PL-Refeições",
        ),
        (
            RESOLUTION_AG_REFEICOES,
            "AG-Refeições",
            RESOLUTION_PL_ALIMENTOS,
            "PL-Alimentos",
        ),
        (
            RESOLUTION_AG_REFEICOES,
            "AG-Refeições",
            RESOLUTION_PL_REFEICOES,
            "PL-Refeições",
        ),
        (
            RESOLUTION_PL_ALIMENTOS,
            "PL-Alimentos",
            RESOLUTION_PL_REFEICOES,
            "PL-Refeições",
        ),
    ]

    for left_key, left_label, right_key, right_label in pair_specs:
        left_data = consolidated_by_group.get(left_key, {})
        right_data = consolidated_by_group.get(right_key, {})
        if not left_data or not right_data:
            continue

        comparison_dir = (
            figures_dir
            / f"comparativo_{_safe_label_slug(left_key)}_vs_{_safe_label_slug(right_key)}"
        )
        plot_ga_vs_linear_charts(
            ga_data=left_data,
            linear_data=right_data,
            output_dir=comparison_dir,
            linear_label=right_label,
            base_data=base_data,
            ag_label=left_label,
        )


def main() -> None:
    """Executa geracao de estatísticas para dietas base, AG-* e/ou PL-*.

    Recebe:
        Argumento de linha de comando --mode para selecionar os grupos.

    Retorna:
        None. Gera relatorios TXT e graficos PNG nos diretorios de saida.
    """
    parser = argparse.ArgumentParser(
        description="Calcula estatisticas e graficos das dietas."
    )
    parser.add_argument(
        "--mode",
        choices=[
            "base",
            RESOLUTION_AG_ALIMENTOS,
            RESOLUTION_AG_REFEICOES,
            RESOLUTION_PL_ALIMENTOS,
            RESOLUTION_PL_REFEICOES,
            "all",
        ],
        default="all",
        help="Conjunto de dietas a analisar.",
    )
    args = parser.parse_args()

    project_root = Path.cwd()
    reports_dir = project_root / "data" / "outputs" / "reports"
    figures_dir = project_root / "data" / "outputs" / "figures"

    tbca_map = load_json_file(
        project_root / "data" / "maps" / "derived" / "mapa-sustentavel-tbca.json"
    )
    tbca_database = load_json_file(
        project_root / "data" / "maps" / "base" / "mapa-tbca-completo.json"
    )
    footprint_map = load_json_file(
        project_root / "data" / "maps" / "base" / "mapa-sustentavel-pegadas.json"
    )

    if not all([tbca_map, tbca_database, footprint_map]):
        print("ERRO: Falha ao carregar os arquivos de contexto nutricional.")
        return

    grouped_files = resolve_diet_file_groups(project_root)
    requested_groups = _resolve_requested_groups(
        _sanitize_mode_for_pipeline(args.mode),
        grouped_files,
    )

    _prepare_output_targets(reports_dir, figures_dir, requested_groups)

    consolidated_by_group: Dict[str, Dict[str, Dict[str, float]]] = {}

    for group_name, diet_files in requested_groups.items():
        existing_files = _filter_existing_files(diet_files)
        consolidated_by_group[group_name] = _process_group(
            group_name=group_name,
            diet_files=existing_files,
            reports_dir=reports_dir,
            figures_dir=figures_dir,
            tbca_map=tbca_map,
            tbca_database=tbca_database,
            footprint_map=footprint_map,
        )

    _plot_pairwise_with_base(consolidated_by_group, figures_dir)


if __name__ == "__main__":
    main()
