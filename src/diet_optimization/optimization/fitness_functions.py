"""Module fitness functions."""

import math
from collections import defaultdict
from typing import Dict, List, Tuple

from .hyperparameters import (
    DAYS_PER_PLAN,
    ENVIRONMENTAL_NORMALIZATION_REFERENCES,
    ENERGY_UPPER_FLEXIBILITY,
    LIMITES_ENERGIA_REFEICAO,
    MAXIMUM_GOALS,
    MEAL_ORDER,
    MINIMUM_GOALS,
)


def compute_daily_totals(
    chromosome: List[Dict],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Calcula os totais médios diários de nutrientes e pegadas ambientais de um cromossomo.

    Soma os valores de todos os genes (refeições de 5 dias) e divide pelo número de dias,
    obtendo a ingestão diária média representada pelo cromossomo.

    Recebe:
        chromosome: Lista de dicionários de refeição, cada um com as chaves
                    'nutrientes' e 'pegadas' já calculadas.

    Retorna:
        Uma tupla com dois dicionários:
        - O primeiro mapeia nome do nutriente para o valor médio diário.
        - O segundo mapeia nome da pegada ambiental para o valor médio diário.
    """
    nutrient_totals_per_day = defaultdict(float)
    footprint_totals_per_day = defaultdict(float)
    total_days = float(DAYS_PER_PLAN)

    for meal_data in chromosome:
        for nutrient_name, nutrient_value in meal_data["nutrientes"].items():
            nutrient_totals_per_day[nutrient_name] += nutrient_value / total_days
        for footprint_name, footprint_value in meal_data["pegadas"].items():
            footprint_totals_per_day[footprint_name] += footprint_value / total_days

    return dict(nutrient_totals_per_day), dict(footprint_totals_per_day)


NUTRIENT_PENALTY_FACTOR = 10007.0


def criterion_penalty_for_nutritional_constraints(
    daily_nutrients: Dict[str, float],
) -> float:
    """Calcula a penalidade nutricional para nutrientes fora de suas metas.

    Cada nutriente com meta minima ou maxima que ultrapasse seu intervalo aceitavel
    recebe uma penalidade proporcional à sua distancia da meta, multiplicada por 10007.
    Se o nutriente estiver dentro de seu intervalo aceitavel, nao ha penalizacao.

    Intervalo aceitavel por tipo de nutriente:
    - MINIMUM_GOALS (apenas): valor >= meta
    - MAXIMUM_GOALS (apenas): valor <= meta * tolerancia
    - Em ambos (Energia): meta <= valor <= meta * 1.05

    Recebe:
        daily_nutrients: Dicionário com totais diários de nutrientes.

    Retorna:
        Soma total das penalidades nutricionais.
    """
    total_penalty = 0.0

    # Processar nutrientes que estão somente em MINIMUM_GOALS
    for nutrient_name, min_target in MINIMUM_GOALS.items():
        nutrient_value = daily_nutrients.get(nutrient_name, 0.0)

        if nutrient_name in MAXIMUM_GOALS:
            # Nutriente tem tanto minimo quanto maximo (ex: Energia)
            max_rules = MAXIMUM_GOALS[nutrient_name]
            max_target = max_rules["meta"]

            if nutrient_name == "Energia":
                max_bound = max_target * (1.0 + ENERGY_UPPER_FLEXIBILITY)
            else:
                max_bound = max_target * max_rules.get("tolerancia", 1.0)

            # Verificar se está dentro do intervalo [min_target, max_bound]
            if nutrient_value < min_target:
                proportional_distance = (min_target - nutrient_value) / min_target
                total_penalty += proportional_distance * NUTRIENT_PENALTY_FACTOR
            elif nutrient_value > max_bound:
                proportional_distance = (nutrient_value - max_bound) / max_target
                total_penalty += proportional_distance * NUTRIENT_PENALTY_FACTOR
            # Caso contrário está dentro de ambos os limites, sem penalidade
        else:
            # Nutriente tem apenas minimo
            if nutrient_value < min_target:
                proportional_distance = (min_target - nutrient_value) / min_target
                total_penalty += proportional_distance * NUTRIENT_PENALTY_FACTOR

    # Processar nutrientes que estão somente em MAXIMUM_GOALS (ex: Sódio, Colesterol)
    for nutrient_name, max_rules in MAXIMUM_GOALS.items():
        if nutrient_name in MINIMUM_GOALS:
            continue  # Já processado acima

        nutrient_value = daily_nutrients.get(nutrient_name, 0.0)
        max_target = max_rules["meta"]
        max_bound = max_target * max_rules.get("tolerancia", 1.0)

        if nutrient_value > max_bound:
            proportional_distance = (nutrient_value - max_bound) / max_target
            total_penalty += proportional_distance * NUTRIENT_PENALTY_FACTOR

    return total_penalty


def _normalize_footprint_value(
    raw_value: float,
    reference_value: float,
    normalization_function_name: str,
) -> float:
    """Normaliza uma pegada com função de normalização configurável.

    Recebe:
        raw_value: Valor bruto da pegada.
        reference_value: Referencia numerica usada na normalizacao.
        normalization_function_name: Nome da funcao de normalizacao.

    Retorna:
        Valor normalizado para uso no criterio ambiental.
    """
    safe_reference = reference_value if reference_value > 0 else 1.0

    if normalization_function_name == "none":
        return raw_value
    if normalization_function_name == "log_ratio":
        return math.log1p(max(raw_value, 0.0)) / math.log1p(safe_reference)
    return raw_value / safe_reference


def criterion_penalty_for_environmental_footprints(
    daily_footprints: Dict[str, float],
    active_footprints: List[str],
    footprint_weights: Dict[str, float],
    normalization_references: Dict[str, float],
    normalization_functions: Dict[str, str],
) -> float:
    """Critério de penalidade baseado nas pegadas ambientais da dieta.

    Permite configurar:
    1. Quais pegadas participam do calculo.
    2. Peso individual por pegada.
    3. Funcao e referencia de normalizacao por pegada.

    Recebe:
        daily_footprints: Dicionário com os valores médios diários de
                          'carbon_footprint', 'water_footprint' e 'ecological_footprint'.
        active_footprints: Lista de chaves de pegadas ativas.
        footprint_weights: Pesos individuais por chave de pegada.
        normalization_references: Referencias numericas por pegada.
        normalization_functions: Nome da funcao de normalizacao por pegada.

    Retorna:
        Valor escalar da penalidade ambiental ponderada por pegada.
    """
    total_environmental_penalty = 0.0

    for footprint_name in active_footprints:
        raw_value = daily_footprints.get(footprint_name, 0.0)
        reference_value = float(
            normalization_references.get(
                footprint_name,
                ENVIRONMENTAL_NORMALIZATION_REFERENCES.get(footprint_name, 1.0),
            )
        )
        normalization_name = normalization_functions.get(footprint_name, "ratio")
        normalized_value = _normalize_footprint_value(
            raw_value,
            reference_value,
            normalization_name,
        )
        individual_weight = float(footprint_weights.get(footprint_name, 1.0))
        total_environmental_penalty += individual_weight * normalized_value

    return total_environmental_penalty


def criterion_penalty_for_nutritional_adequacy(
    daily_nutrients: Dict[str, float],
) -> float:
    """Calcula a penalidade nutricional total para um cromossomo.

    Utiliza a funcao unificada de penalidade para nutrientes fora de suas metas.

    Recebe:
        daily_nutrients: Tabela de nutrientes diarios.

    Retorna:
        Penalidade nutricional total.
    """
    return criterion_penalty_for_nutritional_constraints(daily_nutrients)


def criterion_penalty_for_meal_energy_share(
    chromosome: List[Dict],
    meal_energy_share_limits: Dict[str, Dict[str, float]],
    penalty_weight: float,
) -> float:
    """Penaliza distribuicao energetica diaria fora da faixa por tipo de refeicao.

    Para cada dia, calcula a fração da energia de cada refeicao em relacao ao
    total do dia e aplica penalizacao proporcional quando estiver abaixo do
    limite minimo ou acima do limite maximo configurado.
    """
    total_penalty = 0.0
    meal_count_per_day = len(MEAL_ORDER)

    for day_index in range(DAYS_PER_PLAN):
        start = day_index * meal_count_per_day
        end = start + meal_count_per_day
        day_meals = chromosome[start:end]

        day_energy = sum(
            float(meal.get("nutrientes", {}).get("Energia", 0.0)) for meal in day_meals
        )
        if day_energy <= 0:
            continue

        for meal_position, meal_name in enumerate(MEAL_ORDER):
            limits = meal_energy_share_limits.get(
                meal_name,
                LIMITES_ENERGIA_REFEICAO.get(meal_name, {"min": 0.0, "max": 1.0}),
            )
            min_share = float(limits.get("min", 0.0))
            max_share = float(limits.get("max", 1.0))

            meal_energy = float(
                day_meals[meal_position].get("nutrientes", {}).get("Energia", 0.0)
            )
            share = meal_energy / day_energy

            if share < min_share and min_share > 0:
                total_penalty += penalty_weight * ((min_share - share) / min_share)
            elif share > max_share and max_share > 0:
                total_penalty += penalty_weight * ((share - max_share) / max_share)

    return total_penalty


def aggregate_multi_criteria_penalty(
    nutritional_penalty: float,
    environmental_footprint_penalty: float,
    nutritional_criterion_weight: float,
    environmental_criterion_weight: float,
) -> float:
    """Agrega as penalidades de múltiplos critérios em um único valor escalar.

    Combina o criterio nutricional e o criterio ambiental por soma ponderada,
    permitindo variar os pesos entre os objetivos durante os experimentos.

    Recebe:
        nutritional_penalty:           Penalidade total nutricional.
        environmental_footprint_penalty: Penalidade total pelas pegadas ambientais.
        nutritional_criterion_weight:  Peso global do criterio nutricional.
        environmental_criterion_weight: Peso global do criterio ambiental.

    Retorna:
        Penalidade total multicriterio.
    """
    return (nutritional_criterion_weight * nutritional_penalty) + (
        environmental_criterion_weight * environmental_footprint_penalty
    )


def evaluate_diet_fitness(
    chromosome: List[Dict],
    nutritional_criterion_weight: float,
    environmental_criterion_weight: float,
    active_footprints: List[str],
    footprint_weights: Dict[str, float],
    footprint_normalization_references: Dict[str, float],
    footprint_normalization_functions: Dict[str, str],
    meal_energy_share_limits: Dict[str, Dict[str, float]],
    meal_energy_share_penalty_weight: float,
) -> float:
    """Avalia o fitness de um cromossomo de dieta considerando múltiplos critérios.

    Orquestra o calculo completo do objetivo multicriterio: computa medias diarias,
    calcula penalidades nutricionais e ambientais e agrega com pesos configuraveis.
    O valor retornado é o negativo da penalidade total para que o AG maximize
    fitness sem normalizar em [0, 1].

    Formula: FITNESS = -(Penalidades_Nutricionais + Pegadas_Ambientais)

    Recebe:
        chromosome:           Lista de dicionários de refeição (cromossomo a avaliar).
        nutritional_criterion_weight: Peso do criterio nutricional.
        environmental_criterion_weight: Peso do criterio ambiental.
        active_footprints:    Pegadas ambientais ativas no objetivo.
        footprint_weights:    Peso por pegada ambiental.
        footprint_normalization_references: Referencia numerica por pegada.
        footprint_normalization_functions: Funcao de normalizacao por pegada.
        meal_energy_share_limits: Limites de percentual energetico por refeicao.
        meal_energy_share_penalty_weight: Peso da penalizacao por faixa energetica.

    Retorna:
        Fitness escalar (quanto maior, melhor), definido como -penalidade_total.
    """
    daily_nutrients, daily_footprints = compute_daily_totals(chromosome)

    nutritional_penalty = criterion_penalty_for_nutritional_adequacy(daily_nutrients)

    environmental_penalty = criterion_penalty_for_environmental_footprints(
        daily_footprints,
        active_footprints,
        footprint_weights,
        footprint_normalization_references,
        footprint_normalization_functions,
    )

    meal_share_penalty = criterion_penalty_for_meal_energy_share(
        chromosome,
        meal_energy_share_limits,
        meal_energy_share_penalty_weight,
    )

    total_penalty = aggregate_multi_criteria_penalty(
        nutritional_penalty + meal_share_penalty,
        environmental_penalty,
        nutritional_criterion_weight,
        environmental_criterion_weight,
    )

    return -total_penalty
