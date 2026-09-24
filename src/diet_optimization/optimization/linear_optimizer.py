"""Otimizador de dietas usando Programação Linear (PL).

Oferece duas variantes:

1. **Nível de alimentos** (`optimize_food_level`): seleciona quantidades em gramas
   apenas dos alimentos observados nas dietas-base do perfil em análise,
   minimizando a pegada escolhida sujeito a metas nutricionais.

2. **Nível de refeições** (`optimize_meal_level`): seleciona, entre as refeições
   existentes na dieta base, quantas vezes cada refeição deve aparecer no plano,
   minimizando a pegada ambiental e respeitando restrições nutricionais e de
   completude por tipo de refeição.

Formulação geral (nível de alimentos):

    min  c^T x
    s.t. A_min x >= b_min   (metas mínimas de nutrientes)
         A_max x <= b_max   (tetos máximos de nutrientes; energia com +5%)
         x >= 0

Formulação (nível de refeições):

    min  c^T x
    s.t. A_min x >= D * b_min
         A_max x <= D * b_max
            A_energy_type x >= D * E_meta * r_min
            A_energy_type x <= D * E_meta * r_max
         sum_{k de tipo t} x_k = D  para cada tipo t
         x >= 0

onde D = days_per_plan e x_k = quantas vezes a refeição k é incluída.
"""

import copy
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import linprog

from .data_types import NutritionalContext
from .hyperparameters import (
    DAYS_PER_PLAN,
    ENERGY_UPPER_FLEXIBILITY,
    GRAMS_REFERENCE_FOOTPRINT,
    GRAMS_REFERENCE_TBCA,
    LIMITES_ENERGIA_REFEICAO,
    MAXIMUM_GOALS,
    MEAL_ORDER,
    MINIMUM_GOALS,
    OPTIONAL_EMPTY_MEAL_TYPES,
)
from .utils import calculate_totals, parse_quantity_in_grams


# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------


def _compute_food_vectors(
    tbca_map: Dict[str, str],
    tbca_database: Dict[str, Any],
    footprint_map: Dict[str, Any],
    allowed_food_names: set[str],
) -> Tuple[List[str], Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """Constrói vetores de pegada e nutrientes por grama para cada alimento disponível.

    Itera sobre todos os alimentos presentes tanto no mapa TBCA quanto no mapa de
    pegadas e calcula, para cada um, o valor por grama de cada pegada e nutriente
    relevante (metas mínimas e máximas).

    Recebe:
        tbca_map:       Mapeamento nome do alimento -> código TBCA.
        tbca_database:  Base TBCA indexada por código.
        footprint_map:  Mapa de pegadas por alimento (valores por 1000 g).

    Retorna:
        Tupla com:
        - lista de nomes de alimentos disponíveis;
        - dicionário {chave_pegada: array de pegada por grama};
        - dicionário {nutriente: array de valor por grama}.
    """
    food_names: List[str] = []
    footprint_lists: Dict[str, List[float]] = defaultdict(list)
    nutrient_lists: Dict[str, List[float]] = defaultdict(list)

    all_nutrient_keys = set(MINIMUM_GOALS.keys()) | set(MAXIMUM_GOALS.keys())

    for food_name, tbca_code in tbca_map.items():
        if food_name not in allowed_food_names:
            continue
        if food_name not in footprint_map:
            continue
        if tbca_code not in tbca_database:
            continue

        tbca_entry = tbca_database[tbca_code].get("nutrientes", {})
        pegadas = footprint_map[food_name]

        food_names.append(food_name)

        for fp_key in ["carbon_footprint", "water_footprint", "ecological_footprint"]:
            per_gram = float(pegadas.get(fp_key, 0.0)) / GRAMS_REFERENCE_FOOTPRINT
            footprint_lists[fp_key].append(per_gram)

        for nutrient in all_nutrient_keys:
            per_gram = float(tbca_entry.get(nutrient, 0.0)) / GRAMS_REFERENCE_TBCA
            nutrient_lists[nutrient].append(per_gram)

    footprint_arrays: Dict[str, np.ndarray] = {
        k: np.array(v) for k, v in footprint_lists.items()
    }
    nutrient_arrays: Dict[str, np.ndarray] = {
        k: np.array(v) for k, v in nutrient_lists.items()
    }
    return food_names, footprint_arrays, nutrient_arrays


def food_names_in_diets(base_diets: List[Dict]) -> set[str]:
    """Return the exact source-food names present in one profile's base plans."""
    names: set[str] = set()
    for plan in base_diets:
        for meals in plan.values():
            if not isinstance(meals, dict):
                continue
            for items in meals.values():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, dict) and isinstance(item.get("alimento"), str):
                        names.add(item["alimento"])
    return names


def _build_nutrient_constraints(
    nutrient_arrays: Dict[str, np.ndarray],
    n_vars: int,
    days_multiplier: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Monta as linhas da matriz de desigualdades para restrições nutricionais.

    Converte metas mínimas em A_ub x <= b_ub com sinal negado e adiciona
    restrições de teto para metas máximas.

    Recebe:
        nutrient_arrays:  Mapeamento nutriente -> vetor de valores por variável.
        n_vars:           Número de variáveis de decisão.
        days_multiplier:  Multiplicador aplicado às metas (1 para alimentos, D para refeições).

    Retorna:
        Tupla (A_ub, b_ub) com a matriz e vetor de desigualdades.
    """
    A_rows: List[np.ndarray] = []
    b_rows: List[float] = []

    for nutrient, min_target in MINIMUM_GOALS.items():
        vec = nutrient_arrays.get(nutrient, np.zeros(n_vars))
        A_rows.append(-vec)
        b_rows.append(-min_target * days_multiplier)

    for nutrient, rules in MAXIMUM_GOALS.items():
        vec = nutrient_arrays.get(nutrient, np.zeros(n_vars))
        if nutrient == "Energia":
            ceiling = rules["meta"] * (1.0 + ENERGY_UPPER_FLEXIBILITY)
        else:
            ceiling = rules["meta"] * rules["tolerancia"]
        A_rows.append(vec)
        b_rows.append(ceiling * days_multiplier)

    return np.vstack(A_rows), np.array(b_rows)


def _build_meal_energy_share_constraints(
    meal_pool: Dict[str, List[Dict]],
    variable_list: List[Tuple[str, int]],
    n_vars: int,
    days_per_plan: int,
    meal_energy_share_limits: Dict[str, Dict[str, float]],
) -> Tuple[np.ndarray, np.ndarray]:
    """Monta restricoes de faixa de energia por tipo de refeicao no plano.

    Cada tipo de refeicao t deve contribuir com energia total do plano dentro de:
        D * E_meta * min_t <= sum_k energia_k * x_k <= D * E_meta * max_t
    onde E_meta e a meta diaria de energia.
    """
    A_rows: List[np.ndarray] = []
    b_rows: List[float] = []

    energy_target = float(MAXIMUM_GOALS.get("Energia", {}).get("meta", 0.0))
    if energy_target <= 0:
        return np.zeros((0, n_vars)), np.zeros(0)

    for meal_type in MEAL_ORDER:
        if meal_type not in meal_energy_share_limits:
            continue

        limits = meal_energy_share_limits[meal_type]
        min_share = float(limits.get("min", 0.0))
        max_share = float(limits.get("max", 1.0))

        row = np.zeros(n_vars)
        for var_idx, (mtype, meal_idx) in enumerate(variable_list):
            if mtype != meal_type:
                continue
            row[var_idx] = float(
                meal_pool[mtype][meal_idx].get("nutrientes", {}).get("Energia", 0.0)
            )

        if np.any(row):
            min_target = min_share * energy_target * float(days_per_plan)
            max_target = max_share * energy_target * float(days_per_plan)
            A_rows.append(-row)
            b_rows.append(-min_target)
            A_rows.append(row)
            b_rows.append(max_target)

    if not A_rows:
        return np.zeros((0, n_vars)), np.zeros(0)

    return np.vstack(A_rows), np.array(b_rows)


# ---------------------------------------------------------------------------
# Variante 1 – nível de alimentos
# ---------------------------------------------------------------------------


def optimize_food_level(
    nutritional_context: NutritionalContext,
    allowed_food_names: set[str],
    footprint_key: str = "carbon_footprint",
    days_per_plan: int = DAYS_PER_PLAN,
    diagnostics: Optional[Dict] = None,
) -> Optional[List[Dict]]:
    """Otimiza a dieta no nível de alimentos usando Programação Linear.

    Cada variável representa a quantidade diária em gramas de um alimento
    observado nas dietas-base do perfil e disponível nas bases. O objetivo é minimizar a pegada ambiental
    escolhida satisfazendo as restrições de adequação nutricional.

    Formulação:
        min  c^T x              (pegada por grama * gramas)
        s.t. A_min x >= b_min  (metas mínimas de nutrientes)
             A_max x <= b_max  (tetos de nutrientes máximos)
             x >= 0

    Recebe:
        nutritional_context: Contexto com bases de dados TBCA e de pegadas.
        footprint_key:       Chave da pegada a minimizar (padrão: 'carbon_footprint').
        days_per_plan:       Número de dias no plano gerado.

    Retorna:
        Lista com um plano de dieta em formato JSON compatível com o pipeline,
        ou None se o problema for infeasível ou os dados forem insuficientes.
    """
    food_names, footprint_arrays, nutrient_arrays = _compute_food_vectors(
        nutritional_context.tbca_map,
        nutritional_context.tbca_database,
        nutritional_context.footprint_map,
        allowed_food_names,
    )

    if diagnostics is not None:
        diagnostics.update({"allowed_source_food_count": len(allowed_food_names),
                            "eligible_mapped_food_count": len(food_names),
                            "candidate_food_names": food_names})

    if not food_names:
        print("ERRO: Nenhum alimento disponivel para otimizacao PL nivel de alimentos.")
        return None

    n_foods = len(food_names)
    c = footprint_arrays.get(footprint_key, np.zeros(n_foods))

    A_ub, b_ub = _build_nutrient_constraints(nutrient_arrays, n_foods)
    bounds = [(0.0, None)] * n_foods

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if diagnostics is not None:
        diagnostics.update({"initial_status": int(result.status), "initial_message": result.message,
                            "method": "highs", "options": {}, "fallback_used": False,
                            "n_variables": n_foods, "n_inequalities": int(A_ub.shape[0])})

    if result.status != 0:
        print(
            f"AVISO: PL nivel de alimentos nao convergiu "
            f"(status={result.status}: {result.message}). Tentando versão relaxada..."
        )
        n_ineq = A_ub.shape[0]
        c_relax = np.concatenate([c, 1e4 * np.ones(n_ineq)])
        # Coeficiente -1: A @ x - s <= b  <=>  A @ x <= b + s (relaxa corretamente)
        A_ub_relax = np.hstack([A_ub, -np.eye(n_ineq)])
        bounds_relax = [(0.0, None)] * n_foods + [(0.0, None)] * n_ineq
        result_relax = linprog(
            c_relax, A_ub=A_ub_relax, b_ub=b_ub, bounds=bounds_relax, method="highs"
        )
        if diagnostics is not None:
            diagnostics.update({"fallback_used": True, "fallback_status": int(result_relax.status),
                                "fallback_message": result_relax.message, "slack_penalty": 1e4})
        if result_relax.status != 0:
            print("AVISO: Versao relaxada tambem inviavel.")
            return None
        x = result_relax.x[:n_foods]
        print("INFO: Solucao obtida via PL relaxado (melhor esforco nutricional).")
    else:
        x = result.x
    threshold_grams = 1.0
    food_items = [
        {"alimento": food_names[i], "quantidade": str(round(float(x[i]), 1))}
        for i in range(n_foods)
        if x[i] >= threshold_grams
    ]

    if not food_items:
        print(
            "AVISO: PL nivel de alimentos retornou solucao sem alimentos significativos."
        )
        return None

    single_day: Dict = {"Refeição LP": food_items}
    plan: Dict = {str(day + 1): single_day for day in range(days_per_plan)}
    return [plan]


# ---------------------------------------------------------------------------
# Variante 2 – nível de refeições
# ---------------------------------------------------------------------------


def _extract_meal_pool(
    base_diets: List[Dict],
    nutritional_context: NutritionalContext,
) -> Dict[str, List[Dict]]:
    """Extrai pool de refeições da dieta base agrupadas por tipo de refeição.

    Para cada dia e refeição na dieta base, calcula os totais de nutrientes e
    pegadas e armazena a refeição no pool correspondente ao seu tipo.

    Recebe:
        base_diets:          Lista de planos de dieta base.
        nutritional_context: Contexto para cálculo de nutrientes e pegadas.

    Retorna:
        Dicionário {tipo_refeição: [{"itens": [...], "nutrientes": {...}, "pegadas": {...}}]}.
    """
    meal_pool: Dict[str, List[Dict]] = {meal_type: [] for meal_type in MEAL_ORDER}

    def _empty_meal_candidate() -> Dict:
        """Retorna uma refeicao vazia para representar consumo opcional zero."""
        return {
            "itens": [],
            "nutrientes": {},
            "pegadas": {},
        }

    for diet_plan in base_diets:
        for _day, day_meals in diet_plan.items():
            if not isinstance(day_meals, dict):
                continue
            for meal_type, items in day_meals.items():
                if meal_type not in MEAL_ORDER:
                    continue
                if not isinstance(items, list):
                    continue
                if not items:
                    if meal_type in OPTIONAL_EMPTY_MEAL_TYPES:
                        meal_pool[meal_type].append(_empty_meal_candidate())
                    continue
                nutrients, footprints = calculate_totals(items, nutritional_context)
                meal_pool[meal_type].append(
                    {
                        "itens": copy.deepcopy(items),
                        "nutrientes": nutrients,
                        "pegadas": footprints,
                    }
                )

    for meal_type in OPTIONAL_EMPTY_MEAL_TYPES:
        if meal_type in meal_pool:
            meal_pool[meal_type].append(_empty_meal_candidate())

    return meal_pool


def _round_lp_solution_to_integers(
    x_raw: np.ndarray,
    variable_list: List[Tuple[str, int]],
    meal_type_to_vars: Dict[str, List[int]],
    active_meal_types: List[str],
    days_per_plan: int,
) -> Dict[str, List[int]]:
    """Arredonda a solução LP (contínua) para alocação inteira de refeições.

    Usa o método de arredondamento pelo maior resto fracionário para garantir
    que cada tipo de refeição tenha exatamente days_per_plan instâncias.

    Recebe:
        x_raw:             Vetor de variáveis reais da solução LP.
        variable_list:     Lista de (tipo_refeição, índice_refeição) por variável.
        meal_type_to_vars: Índices de variável agrupados por tipo de refeição.
        active_meal_types: Tipos de refeição com pelo menos uma instância.
        days_per_plan:     Número total de dias por tipo de refeição.

    Retorna:
        Dicionário {tipo_refeição: [índice_de_refeição * dias]}.
    """
    int_assignments: Dict[str, List[int]] = {mt: [] for mt in MEAL_ORDER}

    for mtype in active_meal_types:
        var_indices = meal_type_to_vars[mtype]
        fractional = [(vi, x_raw[vi]) for vi in var_indices]

        floors = {vi: int(v) for vi, v in fractional}
        total_floored = sum(floors.values())
        remaining = days_per_plan - total_floored

        fractions_sorted = sorted(
            fractional, key=lambda iv: iv[1] - int(iv[1]), reverse=True
        )
        for i in range(max(0, remaining)):
            if i < len(fractions_sorted):
                floors[fractions_sorted[i][0]] += 1

        for var_idx, count in floors.items():
            _, meal_idx = variable_list[var_idx]
            int_assignments[mtype].extend([meal_idx] * count)

    return int_assignments


def _solve_relaxed_meal_level(
    c: np.ndarray,
    A_ub: np.ndarray,
    b_ub: np.ndarray,
    A_eq: np.ndarray,
    b_eq: np.ndarray,
    variable_list: List[Tuple[str, int]],
    days_per_plan: int,
    big_m: float = 1e4,
    diagnostics: Optional[Dict] = None,
) -> Optional[np.ndarray]:
    """Resolve o PL de refeições com todas as restrições de desigualdade relaxadas.

    Quando o problema original é inviável (ex.: dietas veganas sem B12 suficiente),
    adiciona variáveis de folga com coeficiente -1 para TODAS as linhas de A_ub,
    penalizando cada violação com big_m no objetivo. A formulação correta é:

        A_ub[i] @ x - s_i <= b_ub[i]
        <=> A_ub[i] @ x <= b_ub[i] + s_i  (permite exceder/reduzir em s_i)

    Com s_i >= 0 e penalidade big_m * s_i, esta versão é sempre viável
    quando as restrições de igualdade admitem solução.

    Recebe:
        c:             Vetor objetivo original.
        A_ub:          Matriz de desigualdades.
        b_ub:          Vetor de lados direitos.
        A_eq:          Matriz de igualdades.
        b_eq:          Vetor de igualdades.
        variable_list: Lista de (tipo_refeição, índice).
        days_per_plan: Número de dias por plano.
        big_m:         Coeficiente de penalização por violação.

    Retorna:
        Vetor x (somente variáveis originais, sem os slacks) ou None se ainda
        inviável.
    """
    n_orig = len(c)
    n_ineq = A_ub.shape[0]

    # Coeficiente -1 para slacks: A @ x - s <= b  <=>  A @ x <= b + s (correto)
    # Relaxa TODAS as desigualdades (min e max), garantindo viabilidade.
    c_relax = np.concatenate([c, big_m * np.ones(n_ineq)])
    A_ub_relax = np.hstack([A_ub, -np.eye(n_ineq)])
    A_eq_relax = np.hstack([A_eq, np.zeros((A_eq.shape[0], n_ineq))])
    bounds_relax = [(0.0, None)] * n_orig + [(0.0, None)] * n_ineq

    result = linprog(
        c_relax,
        A_ub=A_ub_relax,
        b_ub=b_ub,
        A_eq=A_eq_relax,
        b_eq=b_eq,
        bounds=bounds_relax,
        method="highs",
    )
    if diagnostics is not None:
        diagnostics.update({"fallback_used": True, "fallback_status": int(result.status),
                            "fallback_message": result.message, "slack_penalty": big_m})

    if result.status != 0:
        return None

    return result.x[:n_orig]


def optimize_meal_level(
    base_diets: List[Dict],
    nutritional_context: NutritionalContext,
    footprint_key: str = "carbon_footprint",
    days_per_plan: int = DAYS_PER_PLAN,
    meal_energy_share_limits: Dict[str, Dict[str, float]] = LIMITES_ENERGIA_REFEICAO,
    diagnostics: Optional[Dict] = None,
) -> Optional[List[Dict]]:
    """Otimiza a dieta selecionando refeições existentes via Programação Linear.

    Seleciona, entre as refeições existentes na dieta base, quantas vezes cada
    uma deve aparecer no plano otimizado, minimizando a pegada ambiental e
    respeitando restrições nutricionais e de completude por tipo de refeição.

    Formulação:
        min  c^T x
        s.t. A_nut x >= D * b_min   (nutrientes mínimos no plano)
             A_nut x <= D * b_max   (tetos de nutrientes no plano)
        A_energy x dentro da faixa por tipo de refeição
             sum_{k de tipo t} x_k = D  para cada tipo t
             x >= 0

    Recebe:
        base_diets:          Planos de dieta base com as refeições disponíveis.
        nutritional_context: Contexto para cálculo de nutrientes e pegadas.
        footprint_key:       Chave de pegada a minimizar (padrão: 'carbon_footprint').
        days_per_plan:       Número de dias no plano gerado.
        meal_energy_share_limits: Limites de percentual energético por tipo de refeição.

    Retorna:
        Lista com um plano de dieta em formato JSON compatível com o pipeline,
        ou None se o problema for infeasível ou os dados forem insuficientes.
    """
    meal_pool = _extract_meal_pool(base_diets, nutritional_context)

    variable_list: List[Tuple[str, int]] = []
    for meal_type in MEAL_ORDER:
        for idx in range(len(meal_pool[meal_type])):
            variable_list.append((meal_type, idx))

    if not variable_list:
        print("ERRO: Pool de refeicoes vazio para otimizacao PL nivel de refeicoes.")
        return None

    n_vars = len(variable_list)

    # Vetor objetivo: pegada total por seleção de refeição
    c = np.array(
        [
            meal_pool[mtype][midx]["pegadas"].get(footprint_key, 0.0)
            for mtype, midx in variable_list
        ]
    )

    # Restrições de nutrientes (escalonadas por D)
    nutrient_arrays: Dict[str, np.ndarray] = {}
    all_nutrient_keys = set(MINIMUM_GOALS.keys()) | set(MAXIMUM_GOALS.keys())
    for nutrient in all_nutrient_keys:
        nutrient_arrays[nutrient] = np.array(
            [
                meal_pool[mtype][midx]["nutrientes"].get(nutrient, 0.0)
                for mtype, midx in variable_list
            ]
        )

    A_ub, b_ub = _build_nutrient_constraints(
        nutrient_arrays, n_vars, days_multiplier=float(days_per_plan)
    )
    meal_energy_A_ub, meal_energy_b_ub = _build_meal_energy_share_constraints(
        meal_pool=meal_pool,
        variable_list=variable_list,
        n_vars=n_vars,
        days_per_plan=days_per_plan,
        meal_energy_share_limits=meal_energy_share_limits,
    )
    if meal_energy_A_ub.shape[0] > 0:
        A_ub = np.vstack([A_ub, meal_energy_A_ub])
        b_ub = np.concatenate([b_ub, meal_energy_b_ub])

    # Restrições de igualdade: completude por tipo de refeição
    meal_type_to_vars: Dict[str, List[int]] = defaultdict(list)
    for var_idx, (mtype, _) in enumerate(variable_list):
        meal_type_to_vars[mtype].append(var_idx)

    active_meal_types = [mt for mt in MEAL_ORDER if meal_type_to_vars[mt]]
    n_eq = len(active_meal_types)
    A_eq = np.zeros((n_eq, n_vars))
    b_eq = np.full(n_eq, float(days_per_plan))
    for eq_idx, mtype in enumerate(active_meal_types):
        for var_idx in meal_type_to_vars[mtype]:
            A_eq[eq_idx, var_idx] = 1.0

    bounds = [(0.0, None)] * n_vars

    result = linprog(
        c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs"
    )
    if diagnostics is not None:
        diagnostics.update({"initial_status": int(result.status), "initial_message": result.message,
                            "method": "highs", "options": {}, "fallback_used": False,
                            "n_variables": n_vars, "n_inequalities": int(A_ub.shape[0]),
                            "n_equalities": int(A_eq.shape[0])})

    if result.status != 0:
        print(
            f"AVISO: PL nivel de refeicoes nao convergiu "
            f"(status={result.status}: {result.message}). Tentando versao relaxada..."
        )
        x_relaxed = _solve_relaxed_meal_level(
            c, A_ub, b_ub, A_eq, b_eq, variable_list, days_per_plan,
            diagnostics=diagnostics,
        )
        if x_relaxed is None:
            print(
                "AVISO: Versao relaxada tambem inviavel. Sem solucao PL para esta dieta."
            )
            return None
        x = x_relaxed
        print("INFO: Solucao obtida via PL relaxado (melhor esforco nutricional).")
    else:
        x = result.x

    int_assignments = _round_lp_solution_to_integers(
        x, variable_list, meal_type_to_vars, active_meal_types, days_per_plan
    )

    # Montar plano de 5 dias
    plan: Dict[str, Dict] = {}
    for day_idx in range(days_per_plan):
        day_key = str(day_idx + 1)
        plan[day_key] = {}
        for mtype in MEAL_ORDER:
            assignments = int_assignments[mtype]
            if day_idx < len(assignments):
                meal_idx = assignments[day_idx]
                plan[day_key][mtype] = copy.deepcopy(
                    meal_pool[mtype][meal_idx]["itens"]
                )
            elif meal_pool[mtype]:
                # Fallback: usa primeira refeição disponível
                plan[day_key][mtype] = copy.deepcopy(meal_pool[mtype][0]["itens"])

    return [plan]
