"""Module mutation operators."""

import copy
import random
from typing import Any, Dict, List, Optional

from .data_types import NutritionalContext
from .hyperparameters import MEAL_ORDER
from .utils import calculate_totals


def choose_mutation_operator(
    random_probability: float,
    global_mutation_rate: float,
    local_mutation_rate: float,
) -> Optional[str]:
    """Escolhe qual operador de mutação será aplicado para um gene específico.

    Recebe:
        random_probability: Valor aleatório entre 0 e 1 usado para decisão.
        global_mutation_rate: Probabilidade de aplicar mutação global.
        local_mutation_rate: Probabilidade de aplicar mutação local após a faixa global.

    Retorna:
        Nome do operador selecionado:
        - "global_mutation" para mutação global
        - "local_mutation" para mutação local
        - None quando nenhum operador deve ser aplicado
    """
    if random_probability < global_mutation_rate:
        return "global_mutation"
    if random_probability < (global_mutation_rate + local_mutation_rate):
        return "local_mutation"
    return None


def apply_global_mutation(
    meal_pool: Dict[str, List[Dict[str, Any]]],
    meal_type_name: str,
) -> Dict[str, Any]:
    """Aplica mutação global substituindo uma refeição inteira por outra do mesmo tipo.

    Recebe:
        meal_pool: Dicionário com refeições candidatas disponíveis por tipo de refeição.
        meal_type_name: Nome do tipo de refeição que será mutado.

    Retorna:
        Novo gene de refeição, obtido por cópia profunda de uma opção aleatória do pool.
    """
    return copy.deepcopy(random.choice(meal_pool[meal_type_name]))


def apply_local_mutation(
    meal_data: Dict[str, Any],
    food_pool: Dict[str, List[Dict[str, Any]]],
    meal_type_name: str,
    nutritional_context: NutritionalContext,
    local_mutation_operations: List[str],
) -> Dict[str, Any]:
    """Aplica mutação local trocando apenas um alimento dentro da refeição.

    Após a troca do alimento, os nutrientes e as pegadas da refeição são
    recalculados para manter consistência com o novo conteúdo.

    Recebe:
        meal_data: Gene de refeição atual que será modificado.
        food_pool: Dicionário com alimentos disponíveis por tipo de refeição.
        meal_type_name: Nome do tipo de refeição do gene atual.
        nutritional_context: Contexto nutricional usado para recálculo dos totais.

    Retorna:
        Gene de refeição atualizado após a substituição local.
    """
    mutated_meal_data = copy.deepcopy(meal_data)
    available_foods = food_pool.get(meal_type_name, [])
    if not available_foods:
        return mutated_meal_data

    allowed_operations = [
        operation
        for operation in local_mutation_operations
        if operation in {"replace", "add", "remove"}
    ]
    if not allowed_operations:
        return mutated_meal_data

    items = mutated_meal_data.setdefault("itens", [])
    operation = random.choice(allowed_operations)

    if operation == "replace" and items:
        item_position = random.randint(0, len(items) - 1)
        replacement_item = copy.deepcopy(random.choice(available_foods))
        items[item_position] = replacement_item
    elif operation == "add":
        items.append(copy.deepcopy(random.choice(available_foods)))
    elif operation == "remove" and items:
        item_position = random.randint(0, len(items) - 1)
        items.pop(item_position)
    elif items:
        # Fallback para evitar mutacao nula quando operacao sorteada e invalida no estado atual.
        item_position = random.randint(0, len(items) - 1)
        items[item_position] = copy.deepcopy(random.choice(available_foods))
    else:
        items.append(copy.deepcopy(random.choice(available_foods)))

    recalculated_nutrients, recalculated_footprints = calculate_totals(
        mutated_meal_data["itens"],
        nutritional_context,
    )
    mutated_meal_data["nutrientes"] = recalculated_nutrients
    mutated_meal_data["pegadas"] = recalculated_footprints
    return mutated_meal_data


def mutate_chromosome(
    chromosome: List[Dict[str, Any]],
    meal_pool: Dict[str, List[Dict[str, Any]]],
    food_pool: Dict[str, List[Dict[str, Any]]],
    nutritional_context: NutritionalContext,
    global_mutation_rate: float,
    local_mutation_rate: float,
    enable_global_mutation: bool = True,
    enable_local_mutation: bool = True,
    local_mutation_operations: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Aplica operadores de mutação a um cromossomo, gerando uma nova variante.

    Para cada gene (refeição) do cromossomo, sorteia uma probabilidade e aplica
    um de dois tipos de mutação:
    - Mutação global: substitui a refeição inteira por outra do pool de refeições.
    - Mutação local:  substitui apenas um alimento aleatório dentro da refeição
                     por outro do pool de alimentos, recalculando nutrientes e pegadas.

    Recebe:
        chromosome:           Cromossomo a ser mutado (lista de dicionários de refeição).
        meal_pool:            Dicionário de refeições disponíveis por tipo de refeição.
        food_pool:            Dicionário de alimentos disponíveis por tipo de refeição.
        nutritional_context:  Contexto com as bases de dados para recálculo após mutação local.
        global_mutation_rate: Probabilidade de aplicar mutação global em cada gene.
        local_mutation_rate:  Probabilidade adicional (acumulada com a global) de
                              aplicar mutação local em cada gene.

    Retorna:
        Novo cromossomo (cópia independente) com as mutações aplicadas.
    """
    mutated_chromosome = copy.deepcopy(chromosome)
    effective_global_rate = global_mutation_rate if enable_global_mutation else 0.0
    effective_local_rate = local_mutation_rate if enable_local_mutation else 0.0
    effective_local_operations = (
        local_mutation_operations
        if local_mutation_operations is not None
        else ["replace"]
    )

    for chromosome_index, meal_data in enumerate(mutated_chromosome):
        meal_type_name = MEAL_ORDER[chromosome_index % len(MEAL_ORDER)]
        random_probability = random.random()
        selected_mutation_operator = choose_mutation_operator(
            random_probability,
            effective_global_rate,
            effective_local_rate,
        )

        if selected_mutation_operator == "global_mutation":
            mutated_chromosome[chromosome_index] = apply_global_mutation(
                meal_pool,
                meal_type_name,
            )
            continue

        if selected_mutation_operator == "local_mutation":
            mutated_chromosome[chromosome_index] = apply_local_mutation(
                meal_data,
                food_pool,
                meal_type_name,
                nutritional_context,
                effective_local_operations,
            )

    return mutated_chromosome
