"""Module main."""

import argparse
from typing import Dict, List

from .hyperparameters import (
    ACTIVE_FOOTPRINTS_DEFAULT,
    ENVIRONMENTAL_CRITERION_WEIGHT,
    ENVIRONMENTAL_NORMALIZATION_REFERENCES,
    FOOTPRINT_NORMALIZATION_FUNCTIONS,
    FOOTPRINT_WEIGHTS_DEFAULT,
    GeneticAlgorithmHyperparameters,
    NUTRITIONAL_CRITERION_WEIGHT,
    default_context_files,
    default_input_diet_files,
)
from .pipeline import process_optimization_pipeline


def _parse_list_argument(raw_value: str) -> List[str]:
    """Converte argumento de lista separado por vírgula removendo espaços.

    Recebe:
        raw_value: Texto no formato "item1,item2,item3".

    Retorna:
        Lista de itens sem espacos vazios.
    """
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _parse_float_mapping_argument(raw_value: str) -> Dict[str, float]:
    """Converte argumento chave=valor em um dicionário de floats.

    Recebe:
        raw_value: Texto no formato "chave=valor,chave2=valor2".

    Retorna:
        Dicionario com valores float.
    """
    result: Dict[str, float] = {}
    for entry in _parse_list_argument(raw_value):
        if "=" not in entry:
            raise ValueError(f"Entrada invalida (esperado chave=valor): {entry}")
        key, value = entry.split("=", 1)
        result[key.strip()] = float(value.strip())
    return result


def _parse_string_mapping_argument(raw_value: str) -> Dict[str, str]:
    """Converte argumento chave=valor em um dicionário de strings.

    Recebe:
        raw_value: Texto no formato "chave=valor,chave2=valor2".

    Retorna:
        Dicionario com valores string.
    """
    result: Dict[str, str] = {}
    for entry in _parse_list_argument(raw_value):
        if "=" not in entry:
            raise ValueError(f"Entrada invalida (esperado chave=valor): {entry}")
        key, value = entry.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _build_hyperparameters_from_args(
    parsed_arguments: argparse.Namespace,
) -> GeneticAlgorithmHyperparameters:
    """Monta o objeto de hiperparâmetros do AG a partir da CLI.

    Recebe:
        parsed_arguments: Namespace retornado pelo argparse.

    Retorna:
        Instancia de GeneticAlgorithmHyperparameters configurada para a execucao.
    """
    active_footprints = (
        _parse_list_argument(parsed_arguments.active_footprints)
        if parsed_arguments.active_footprints
        else ACTIVE_FOOTPRINTS_DEFAULT.copy()
    )

    footprint_weights = FOOTPRINT_WEIGHTS_DEFAULT.copy()
    if parsed_arguments.footprint_weights:
        footprint_weights.update(
            _parse_float_mapping_argument(parsed_arguments.footprint_weights)
        )

    normalization_references = ENVIRONMENTAL_NORMALIZATION_REFERENCES.copy()
    if parsed_arguments.footprint_normalization_references:
        normalization_references.update(
            _parse_float_mapping_argument(
                parsed_arguments.footprint_normalization_references
            )
        )

    normalization_functions = FOOTPRINT_NORMALIZATION_FUNCTIONS.copy()
    if parsed_arguments.footprint_normalization_functions:
        normalization_functions.update(
            _parse_string_mapping_argument(
                parsed_arguments.footprint_normalization_functions
            )
        )

    return GeneticAlgorithmHyperparameters(
        nutritional_criterion_weight=parsed_arguments.nutritional_weight,
        environmental_criterion_weight=parsed_arguments.environmental_weight,
        active_footprints=active_footprints,
        footprint_weights=footprint_weights,
        footprint_normalization_references=normalization_references,
        footprint_normalization_functions=normalization_functions,
    )


def main() -> None:
    """Ponto de entrada da linha de comando para o otimizador de dietas.

    Analisa os argumentos da CLI, recupera os arquivos padrão de dieta e contexto
    nutricional e inicia o pipeline completo de otimização.

    Argumentos CLI:
        --runs (int): Número de execuções independentes do algoritmo genético
                      por arquivo de dieta (padrão: 1).

    Retorna:
        Nada. Delega toda a execução para process_optimization_pipeline.
    """
    argument_parser = argparse.ArgumentParser(
        description="Otimizador de dietas com algoritmo genetico e multiplas execucoes"
    )
    argument_parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Numero de execucoes por arquivo de dieta",
    )
    argument_parser.add_argument(
        "--nutritional-weight",
        type=float,
        default=NUTRITIONAL_CRITERION_WEIGHT,
        help="Peso global do criterio nutricional na funcao objetivo.",
    )
    argument_parser.add_argument(
        "--environmental-weight",
        type=float,
        default=ENVIRONMENTAL_CRITERION_WEIGHT,
        help="Peso global do criterio ambiental na funcao objetivo.",
    )
    argument_parser.add_argument(
        "--active-footprints",
        type=str,
        default=",".join(ACTIVE_FOOTPRINTS_DEFAULT),
        help=(
            "Lista de pegadas ativas separadas por virgula. "
            "Exemplo: carbon_footprint,water_footprint"
        ),
    )
    argument_parser.add_argument(
        "--footprint-weights",
        type=str,
        default="",
        help=(
            "Pesos por pegada no formato chave=valor separados por virgula. "
            "Exemplo: carbon_footprint=1.0,water_footprint=0.5"
        ),
    )
    argument_parser.add_argument(
        "--footprint-normalization-references",
        type=str,
        default="",
        help=(
            "Referencias de normalizacao por pegada no formato chave=valor. "
            "Exemplo: carbon_footprint=2000,water_footprint=1500"
        ),
    )
    argument_parser.add_argument(
        "--footprint-normalization-functions",
        type=str,
        default="",
        help=(
            "Funcao de normalizacao por pegada no formato chave=valor. "
            "Valores sugeridos: ratio, log_ratio, none. "
            "Exemplo: carbon_footprint=ratio,water_footprint=log_ratio"
        ),
    )
    parsed_arguments = argument_parser.parse_args()

    hyperparameters = _build_hyperparameters_from_args(parsed_arguments)

    process_optimization_pipeline(
        diet_files=default_input_diet_files(),
        context_files=default_context_files(),
        number_of_runs=parsed_arguments.runs,
        hyperparameters=hyperparameters,
    )


if __name__ == "__main__":
    main()
