"""Module utils."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .data_types import NutritionalContext
from .hyperparameters import GRAMS_REFERENCE_FOOTPRINT, GRAMS_REFERENCE_TBCA


def load_json_file(file_path: Path) -> Optional[Any]:
    """Carrega e desserializa o conteúdo de um arquivo JSON.

    Recebe:
        file_path: Caminho absoluto ou relativo para o arquivo JSON a ser lido.

    Retorna:
        O conteúdo do arquivo convertido para estrutura Python (dict, list, etc.),
        ou None caso o arquivo não exista ou ocorra erro de decodificação.
    """
    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as input_file:
            return json.load(input_file)
    except json.JSONDecodeError as json_error:
        print(f"Erro ao decodificar JSON no arquivo {file_path}: {json_error}")
        return None


def save_json_file(file_path: Path, content: Any) -> None:
    """Serializa um objeto Python e grava o resultado em disco no formato JSON.

    Cria os diretórios intermediários automaticamente caso não existam.

    Recebe:
        file_path: Caminho do arquivo de destino.
        content:   Objeto Python serializável (dict, list, etc.) a ser gravado.

    Retorna:
        Nada. O arquivo é criado ou sobrescrito em disco.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as output_file:
        json.dump(content, output_file, indent=4, ensure_ascii=False)


def parse_quantity_in_grams(raw_quantity_value: Any) -> float:
    """Converte um valor bruto de quantidade para um número decimal em gramas.

    Normaliza vírgulas para pontos e tenta interpretar o valor como float.

    Recebe:
        raw_quantity_value: Valor de quantidade no formato original do JSON
                            (pode ser string com vírgula, int ou float).

    Retorna:
        Quantidade em gramas como float. Retorna 0.0 se a conversão falhar.
    """
    normalized_quantity = str(raw_quantity_value).replace(",", ".")
    try:
        return float(normalized_quantity)
    except ValueError:
        return 0.0


def calculate_totals(
    item_list: List[Dict[str, Any]],
    nutritional_context: NutritionalContext,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Calcula os totais nutricionais e de pegadas ambientais de uma lista de alimentos.

    Para cada alimento da lista, busca seus valores nutricionais na base TBCA e
    suas pegadas ambientais no mapa de pegadas, ponderando pela quantidade em gramas.

    Recebe:
        item_list:            Lista de dicionários, cada um com 'alimento' (nome) e
                              'quantidade' (em gramas) do alimento consumido.
        nutritional_context:  Contexto com as bases de dados TBCA e de pegadas ambientais.

    Retorna:
        Uma tupla com dois dicionários:
        - O primeiro mapeia nome do nutriente para o total acumulado (em unidades originais TBCA).
        - O segundo mapeia 'carbon_footprint', 'water_footprint' e 'ecological_footprint'
          para seus respectivos totais acumulados.
    """
    nutrients_total: Dict[str, float] = defaultdict(float)
    footprints_total = {
        "carbon_footprint": 0.0,
        "water_footprint": 0.0,
        "ecological_footprint": 0.0,
    }

    for food_item in item_list:
        food_name = food_item.get("alimento")
        quantity_grams = parse_quantity_in_grams(food_item.get("quantidade", "0"))

        tbca_code = nutritional_context.tbca_map.get(food_name)
        if tbca_code and tbca_code in nutritional_context.tbca_database:
            nutrient_factor = quantity_grams / GRAMS_REFERENCE_TBCA
            nutrient_data = nutritional_context.tbca_database[tbca_code].get(
                "nutrientes", {}
            )
            for nutrient_name, nutrient_value in nutrient_data.items():
                nutrients_total[nutrient_name] += (
                    float(nutrient_value) * nutrient_factor
                )

        if food_name in nutritional_context.footprint_map:
            footprint_factor = quantity_grams / GRAMS_REFERENCE_FOOTPRINT
            footprint_data = nutritional_context.footprint_map[food_name]
            footprints_total["carbon_footprint"] += (
                float(footprint_data.get("carbon_footprint", 0.0)) * footprint_factor
            )
            footprints_total["water_footprint"] += (
                float(footprint_data.get("water_footprint", 0.0)) * footprint_factor
            )
            footprints_total["ecological_footprint"] += (
                float(footprint_data.get("ecological_footprint", 0.0))
                * footprint_factor
            )

    return dict(nutrients_total), footprints_total
