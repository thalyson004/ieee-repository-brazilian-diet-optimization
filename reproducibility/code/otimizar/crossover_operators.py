"""Module crossover operators."""

import copy
import random
from typing import Any, Dict, List

from .hyperparameters import DAYS_PER_PLAN, MAXIMUM_GOALS, MEAL_ORDER


def crossover_by_meal(
    first_parent: List[Any],
    second_parent: List[Any],
) -> List[Any]:
    """Executa crossover por refeição, escolhendo gene a gene entre os dois pais.

    Para cada refeição do cromossomo filho, existe 50% de chance de herdar do
    primeiro pai e 50% de chance de herdar do segundo pai.

    Recebe:
        first_parent: Cromossomo completo do primeiro progenitor.
        second_parent: Cromossomo completo do segundo progenitor.

    Retorna:
        Novo cromossomo filho com o mesmo comprimento dos pais.
    """
    offspring_chromosome: List[Any] = []
    for gene_index in range(len(first_parent)):
        inherited_gene = (
            first_parent[gene_index]
            if random.random() > 0.5
            else second_parent[gene_index]
        )
        offspring_chromosome.append(copy.deepcopy(inherited_gene))
    return offspring_chromosome


def crossover_by_day(
    first_parent: List[Any],
    second_parent: List[Any],
    meals_per_day: int = len(MEAL_ORDER),
    days_per_plan: int = DAYS_PER_PLAN,
) -> List[Any]:
    """Executa crossover por dia, herdando blocos diários inteiros de um dos pais.

    Para cada dia do plano alimentar, o filho herda todas as refeições daquele
    dia de um único pai escolhido com probabilidade de 50%.

    Recebe:
        first_parent: Cromossomo completo do primeiro progenitor.
        second_parent: Cromossomo completo do segundo progenitor.
        meals_per_day: Quantidade de refeições por dia no cromossomo.
        days_per_plan: Quantidade total de dias representados no cromossomo.

    Retorna:
        Novo cromossomo filho composto por blocos de dias inteiros.
    """
    offspring_chromosome: List[Any] = []

    for day_index in range(days_per_plan):
        start_index = day_index * meals_per_day
        end_index = start_index + meals_per_day
        selected_parent = first_parent if random.random() > 0.5 else second_parent
        for meal_index in range(start_index, end_index):
            offspring_chromosome.append(copy.deepcopy(selected_parent[meal_index]))

    return offspring_chromosome


def crossover_by_meal_type(
    first_parent: List[Any],
    second_parent: List[Any],
    meal_order: List[str] = MEAL_ORDER,
    days_per_plan: int = DAYS_PER_PLAN,
) -> List[Any]:
    """Executa crossover por tipo de refeição, herdando cada tipo de um dos pais.

    Para cada tipo de refeição (por exemplo, Café da Manhã, Almoço e Jantar),
    o filho escolhe um pai com probabilidade de 50% e herda esse mesmo tipo em
    todos os dias do plano.

    Recebe:
        first_parent: Cromossomo completo do primeiro progenitor.
        second_parent: Cromossomo completo do segundo progenitor.
        meal_order: Lista com a ordem e o nome dos tipos de refeição.
        days_per_plan: Quantidade total de dias representados no cromossomo.

    Retorna:
        Novo cromossomo filho composto por herança por tipo de refeição.
    """
    meals_per_day = len(meal_order)
    offspring_chromosome: List[Any] = [None] * (days_per_plan * meals_per_day)

    for meal_type_index, _meal_type_name in enumerate(meal_order):
        selected_parent = first_parent if random.random() > 0.5 else second_parent
        for day_index in range(days_per_plan):
            chromosome_index = (day_index * meals_per_day) + meal_type_index
            offspring_chromosome[chromosome_index] = copy.deepcopy(
                selected_parent[chromosome_index]
            )

    return offspring_chromosome


def apply_crossover(
    first_parent: List[Any],
    second_parent: List[Any],
    crossover_strategy: str,
) -> List[Any]:
    """Aplica a estratégia de crossover configurada e retorna o cromossomo filho.

    Estratégias disponíveis:
        - by_meal: crossover por refeição.
        - by_day: crossover por dia.
        - by_meal_type: crossover por tipo de refeição.

    Recebe:
        first_parent: Cromossomo do primeiro progenitor.
        second_parent: Cromossomo do segundo progenitor.
        crossover_strategy: Nome da estratégia de crossover a ser aplicada.

    Retorna:
        Cromossomo filho gerado pela estratégia selecionada.

    Lança:
        ValueError: Caso a estratégia informada não exista.
    """
    if crossover_strategy == "by_meal":
        return crossover_by_meal(first_parent, second_parent)
    if crossover_strategy == "by_day":
        return crossover_by_day(first_parent, second_parent)
    if crossover_strategy == "by_meal_type":
        return crossover_by_meal_type(first_parent, second_parent)

    raise ValueError(f"Estratégia de crossover inválida: {crossover_strategy}")


def calculate_daily_energy(
    chromosome: List[Dict[str, Any]],
    day_index: int,
    meals_per_day: int = len(MEAL_ORDER),
) -> float:
    """Calcula a energia total de um dia específico dentro do cromossomo.

    Recebe:
        chromosome: Cromossomo contendo os genes de refeição.
        day_index: Índice do dia a ser calculado (base zero).
        meals_per_day: Quantidade de refeições por dia.

    Retorna:
        Soma de energia do dia em análise.
    """
    day_start_index = day_index * meals_per_day
    day_end_index = day_start_index + meals_per_day
    day_energy = 0.0

    for chromosome_index in range(day_start_index, day_end_index):
        day_energy += float(
            chromosome[chromosome_index].get("nutrientes", {}).get("Energia", 0.0)
        )

    return day_energy


def repair_offspring_energy_limit(
    offspring_chromosome: List[Dict[str, Any]],
    meal_pool: Dict[str, List[Dict[str, Any]]],
    meal_order: List[str] = MEAL_ORDER,
    days_per_plan: int = DAYS_PER_PLAN,
    max_repair_attempts_per_day: int = 12,
) -> List[Dict[str, Any]]:
    """Repara cromossomo pós-crossover para respeitar limite diário de energia.

    Se um dia ultrapassar o teto de energia definido nas metas máximas, a função
    busca substituições de refeições por alternativas de menor energia para reduzir
    o excesso sem alterar o formato do cromossomo.

    Recebe:
        offspring_chromosome: Cromossomo recém-gerado pelo crossover.
        meal_pool: Dicionário de refeições disponíveis por tipo de refeição.
        meal_order: Lista com a ordem dos tipos de refeição no cromossomo.
        days_per_plan: Quantidade de dias representados no cromossomo.
        max_repair_attempts_per_day: Limite de tentativas de ajuste por dia.

    Retorna:
        Novo cromossomo reparado, mantendo o mesmo comprimento e estrutura.
    """
    repaired_chromosome = copy.deepcopy(offspring_chromosome)
    meals_per_day = len(meal_order)
    energy_target = float(MAXIMUM_GOALS["Energia"]["meta"])
    energy_ceiling = energy_target * float(MAXIMUM_GOALS["Energia"]["tolerancia"])

    for day_index in range(days_per_plan):
        repair_attempts = 0

        while repair_attempts < max_repair_attempts_per_day:
            current_day_energy = calculate_daily_energy(
                repaired_chromosome,
                day_index,
                meals_per_day,
            )
            if current_day_energy <= energy_ceiling:
                break

            best_replacement_index = None
            best_replacement_meal = None
            best_energy_reduction = 0.0

            for meal_index_within_day, meal_type_name in enumerate(meal_order):
                chromosome_index = (day_index * meals_per_day) + meal_index_within_day
                current_meal = repaired_chromosome[chromosome_index]
                current_meal_energy = float(
                    current_meal.get("nutrientes", {}).get("Energia", 0.0)
                )

                for candidate_meal in meal_pool.get(meal_type_name, []):
                    candidate_energy = float(
                        candidate_meal.get("nutrientes", {}).get("Energia", 0.0)
                    )
                    energy_reduction = current_meal_energy - candidate_energy
                    if energy_reduction > best_energy_reduction:
                        best_energy_reduction = energy_reduction
                        best_replacement_index = chromosome_index
                        best_replacement_meal = candidate_meal

            if best_replacement_index is None or best_replacement_meal is None:
                break

            repaired_chromosome[best_replacement_index] = copy.deepcopy(
                best_replacement_meal
            )
            repair_attempts += 1

    return repaired_chromosome
