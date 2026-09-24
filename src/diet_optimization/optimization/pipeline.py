"""Module pipeline."""

import copy
import hashlib
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from .data_types import ContextFiles, ExecutionResult, NutritionalContext
from .genetic_algorithm import GeneticAlgorithm
from .hyperparameters import (
    DAYS_PER_PLAN,
    GeneticAlgorithmHyperparameters,
    MEAL_ORDER,
    OPTIONAL_EMPTY_MEAL_TYPES,
    RESOLUTION_AG_ALIMENTOS,
    RESOLUTION_AG_REFEICOES,
    build_hyperparameter_export,
    build_hyperparameters_for_resolution,
)
from .utils import calculate_totals, load_json_file, save_json_file
from diet_optimization.experiments.diagnostics import evaluate_plan
from diet_optimization.experiments.resource_monitor import SampledProcessMemory


def build_context(context_files: ContextFiles) -> NutritionalContext:
    """Carrega os arquivos de contexto e monta o objeto NutritionalContext.

    Recebe:
        context_files: Dicionário com os caminhos dos três arquivos JSON de contexto
                       (mapeamento TBCA, base TBCA completa e mapa de pegadas).

    Retorna:
        Instância de NutritionalContext populada com os dados carregados.
        Dicionários vazios são usados como fallback caso algum arquivo falhe.
    """
    return NutritionalContext(
        tbca_map=load_json_file(Path(context_files["tbca_map"])) or {},
        tbca_database=load_json_file(Path(context_files["tbca_db"])) or {},
        footprint_map=load_json_file(Path(context_files["footprint_map"])) or {},
    )


def build_meal_and_food_pools(
    diets: List[Dict],
    nutritional_context: NutritionalContext,
) -> Tuple[Dict[str, List[Dict]], Dict[str, List[Dict]], List[List[Dict]]]:
    """Constrói os pools de refeições e alimentos a partir dos dados brutos de dieta.

    Percorre todas as dietas e dias fornecidos, calcula os totais nutricionais e
    de pegadas para cada refeição e agrupa os resultados por tipo de refeição.
    O pool de alimentos é deduplicado para evitar repetições.

    Recebe:
        diets:               Lista de planos de dieta; cada plano é um dicionário
                             de dias, e cada dia contém refeições com listas de alimentos.
        nutritional_context: Contexto com as bases de dados para cálculo dos totais.

    Retorna:
        Tupla com três componentes:
        - meal_pool: Listas de refeições completas (com nutrientes e pegadas calculados).
        - food_pool: Listas de alimentos únicos disponíveis para mutação local.
        - base_chromosomes: Cromossomos completos derivados das dietas base.
    """
    meal_pool = {meal_type_name: [] for meal_type_name in MEAL_ORDER}
    food_pool = {meal_type_name: [] for meal_type_name in MEAL_ORDER}
    base_chromosomes: List[List[Dict]] = []

    def _build_empty_meal() -> Dict:
        """Cria um gene de refeicao vazio para representar consumo opcional zero."""
        return {
            "itens": [],
            "nutrientes": {},
            "pegadas": {},
        }

    for diet_plan in diets:
        day_keys = sorted(
            [key for key, value in diet_plan.items() if isinstance(value, dict)],
            key=lambda day_key: (
                int(day_key) if str(day_key).isdigit() else str(day_key)
            ),
        )
        chromosome_candidate: List[Dict] = []

        if len(day_keys) >= DAYS_PER_PLAN:
            for day_name in day_keys[:DAYS_PER_PLAN]:
                day_meals = diet_plan[day_name]
                for meal_type_name in MEAL_ORDER:
                    meal_items = day_meals.get(meal_type_name, [])
                    if not isinstance(meal_items, list):
                        meal_items = []

                    if meal_items:
                        nutrients, footprints = calculate_totals(
                            meal_items, nutritional_context
                        )
                        chromosome_candidate.append(
                            {
                                "itens": copy.deepcopy(meal_items),
                                "nutrientes": nutrients,
                                "pegadas": footprints,
                            }
                        )
                    else:
                        chromosome_candidate.append(_build_empty_meal())

            if len(chromosome_candidate) == (DAYS_PER_PLAN * len(MEAL_ORDER)):
                base_chromosomes.append(chromosome_candidate)

        for day_name, day_meals in diet_plan.items():
            if not isinstance(day_meals, dict):
                continue

            for meal_type_name, meal_items in day_meals.items():
                if meal_type_name not in MEAL_ORDER:
                    continue
                if not isinstance(meal_items, list) or not meal_items:
                    continue

                nutrients, footprints = calculate_totals(
                    meal_items, nutritional_context
                )
                meal_pool[meal_type_name].append(
                    {
                        "itens": copy.deepcopy(meal_items),
                        "nutrientes": nutrients,
                        "pegadas": footprints,
                    }
                )

                for food_item in meal_items:
                    if food_item not in food_pool[meal_type_name]:
                        food_pool[meal_type_name].append(copy.deepcopy(food_item))

    for meal_type_name in OPTIONAL_EMPTY_MEAL_TYPES:
        if meal_type_name in meal_pool:
            meal_pool[meal_type_name].append(_build_empty_meal())

    return meal_pool, food_pool, base_chromosomes


def chromosome_to_optimized_diet(
    best_chromosome: List[Dict],
) -> Dict[str, Dict[str, List[Dict]]]:
    """Converte o melhor cromossomo encontrado para o formato de dieta otimizada.

    Reconstrói a estrutura hierárquica dia → refeição → alimentos a partir da
    lista linear de genes do cromossomo (30 genes = 5 dias × 6 refeições).

    Recebe:
        best_chromosome: Lista de 30 dicionários de refeição representando
                         5 dias × 6 refeições do melhor indivíduo encontrado.

    Retorna:
        Dicionário com chaves '1' a '5' (dias), cada uma mapeando o tipo de
        refeição para a lista de alimentos correspondente.
    """
    optimized_diet: Dict[str, Dict[str, List[Dict]]] = {}

    for day_index in range(DAYS_PER_PLAN):
        day_key = str(day_index + 1)
        optimized_diet[day_key] = {}
        for meal_index, meal_type_name in enumerate(MEAL_ORDER):
            chromosome_index = (day_index * len(MEAL_ORDER)) + meal_index
            optimized_diet[day_key][meal_type_name] = best_chromosome[chromosome_index][
                "itens"
            ]

    return optimized_diet


def process_optimization_pipeline(
    diet_files: List[str],
    context_files: ContextFiles,
    number_of_runs: int,
    hyperparameters: GeneticAlgorithmHyperparameters,
    base_seed: int | None = None,
) -> None:
    """Orquestra o pipeline completo de otimização para múltiplos arquivos de dieta.

    Para cada arquivo de dieta fornecido:
    1. Carrega o contexto nutricional e constrói os pools de refeições e alimentos.
    2. Executa o algoritmo genético pelo número de vezes solicitado.
    3. Registra os resultados de cada execução e identifica o melhor cromossomo global.
    4. Salva o resumo do experimento (JSON), a dieta otimizada (JSON) e os
       hiperparâmetros utilizados no diretório 'otimizado/'.

    Recebe:
        diet_files:     Lista de caminhos para os arquivos JSON de dieta a processar.
        context_files:  Dicionário com os caminhos dos arquivos de contexto nutricional.
        number_of_runs: Número de execuções independentes do AG por arquivo de dieta.
        hyperparameters: Conjunto de hiperparâmetros e pesos da função objetivo.

    Retorna:
        Nada. Todos os resultados são persistidos em disco no diretório 'otimizado/'.
    """
    optimization_runs_root = Path("data/outputs/optimization_runs")
    optimized_diets_root = Path("data/outputs/optimized_diets")
    optimization_runs_root.mkdir(parents=True, exist_ok=True)
    optimized_diets_root.mkdir(parents=True, exist_ok=True)

    nutritional_context = build_context(context_files)
    if not nutritional_context.tbca_map or not nutritional_context.tbca_database:
        print("Erro: falha ao carregar as bases de dados nutricionais.")
        return

    for resolution_label in [RESOLUTION_AG_REFEICOES, RESOLUTION_AG_ALIMENTOS]:
        tuned_hyperparameters = build_hyperparameters_for_resolution(
            resolution_label,
            hyperparameters,
        )

        optimization_runs_directory = optimization_runs_root / resolution_label
        optimized_diets_directory = optimized_diets_root / resolution_label
        optimization_runs_directory.mkdir(parents=True, exist_ok=True)
        optimized_diets_directory.mkdir(parents=True, exist_ok=True)

        hyperparameter_file_path = optimization_runs_directory / "hiperparametros.json"
        save_json_file(
            hyperparameter_file_path,
            build_hyperparameter_export(number_of_runs, tuned_hyperparameters),
        )
        print(
            f"[{resolution_label}] Hiperparametros salvos em: {hyperparameter_file_path}"
        )

        for diet_file_name in diet_files:
            diet_file_path = Path(diet_file_name)
            if not diet_file_path.exists():
                continue

            print("=" * 60)
            print(
                f"[{resolution_label}] Iniciando experimento para {diet_file_name} com {number_of_runs} execucoes"
            )
            print("=" * 60)

            diets = load_json_file(diet_file_path)
            if not diets:
                continue

            meal_pool, food_pool, base_chromosomes = build_meal_and_food_pools(
                diets, nutritional_context
            )
            candidate_food_names = sorted({
                item.get("alimento")
                for foods in food_pool.values()
                for item in foods
                if isinstance(item.get("alimento"), str)
            })
            if any(not meal_pool[meal_type_name] for meal_type_name in MEAL_ORDER):
                print(
                    f"Arquivo ignorado por falta de refeicoes completas: {diet_file_name}"
                )
                continue

            execution_results: List[ExecutionResult] = []
            overall_best_fitness = float("-inf")
            overall_best_chromosome: List[Dict] = []
            all_chromosomes: List[List[Dict]] = []
            per_run_directory = optimization_runs_directory / "runs" / diet_file_path.stem
            per_run_directory.mkdir(parents=True, exist_ok=True)

            for execution_identifier in range(1, number_of_runs + 1):
                execution_seed = derive_execution_seed(
                    base_seed,
                    resolution_label,
                    diet_file_path.stem,
                    execution_identifier,
                )
                if execution_seed is not None:
                    random.seed(execution_seed)
                print(
                    f"[{resolution_label}] Execucao {execution_identifier}/{number_of_runs} "
                    f"(seed={execution_seed})"
                )
                started_at = time.perf_counter()
                genetic_algorithm = GeneticAlgorithm(
                    meal_pool=meal_pool,
                    food_pool=food_pool,
                    nutritional_context=nutritional_context,
                    hyperparameters=tuned_hyperparameters,
                    initial_seed_chromosomes=base_chromosomes,
                )
                memory_sampler = SampledProcessMemory()
                memory_sampler.start()
                try:
                    best_chromosome, fitness_history, convergence_generation = (
                        genetic_algorithm.run()
                    )
                finally:
                    process_memory = memory_sampler.stop()
                final_fitness = fitness_history[-1]
                duration_seconds = time.perf_counter() - started_at
                final_plan = chromosome_to_optimized_diet(best_chromosome)
                run_artifact = per_run_directory / f"execution-{execution_identifier:03d}.json"
                run_payload = {
                    "schema_version": "1.0",
                    "resolution": resolution_label,
                    "source_diet_file": diet_file_path.name,
                    "candidate_pool_profile": diet_file_path.stem.removeprefix("dietas-"),
                    "candidate_food_count": len(candidate_food_names),
                    "candidate_food_names": candidate_food_names,
                    "execution_id": execution_identifier,
                    "effective_configuration": asdict(tuned_hyperparameters),
                    "seed": execution_seed,
                    "objective_by_generation": fitness_history,
                    "objective_direction": "maximize_fitness",
                    "stop_criterion": genetic_algorithm.stop_reason,
                    "stop_generation": convergence_generation,
                    "fitness_evaluation_count": genetic_algorithm.fitness_evaluation_count,
                    "process_memory": process_memory,
                    "duration_seconds": duration_seconds,
                    "final_fitness": final_fitness,
                    "final_solution": final_plan,
                    "metrics_and_violations": evaluate_plan(
                        final_plan, nutritional_context,
                        minimum_goals=tuned_hyperparameters.nutritional_minimum_goals,
                        maximum_goals=tuned_hyperparameters.nutritional_maximum_goals,
                        meal_energy_share_limits=tuned_hyperparameters.meal_energy_share_limits,
                        protocol_id=tuned_hyperparameters.nutrition_protocol_id,
                        data_quality_fields=(
                            set(tuned_hyperparameters.nutritional_minimum_goals)
                            | set(tuned_hyperparameters.nutritional_maximum_goals)
                            | {target["tbca_field"] for target in tuned_hyperparameters.secondary_nutrition_targets}
                            | {target["tbca_field"] for target in tuned_hyperparameters.descriptive_nutrition_targets}
                        ),
                    ),
                }
                save_json_file(run_artifact, run_payload)

                execution_results.append(
                    ExecutionResult(
                        execution_identifier=execution_identifier,
                        convergence_generation=convergence_generation,
                        final_fitness=final_fitness,
                        fitness_history=fitness_history,
                        random_seed=execution_seed,
                        duration_seconds=duration_seconds,
                    )
                )

                all_chromosomes.append(best_chromosome)

                if final_fitness > overall_best_fitness:
                    overall_best_fitness = final_fitness
                    overall_best_chromosome = best_chromosome

            average_convergence_generation = round(
                sum(
                    execution_result.convergence_generation
                    for execution_result in execution_results
                )
                / number_of_runs,
                2,
            )

            experiment_payload = {
                "arquivo_base": diet_file_name,
                "tipo_resolucao": resolution_label,
                "total_execucoes": number_of_runs,
                "semente_base": base_seed,
                "media_geracao_convergencia": average_convergence_generation,
                "melhor_fitness_global": overall_best_fitness,
                "execucoes": [
                    {
                        "id_execucao": execution_result.execution_identifier,
                        "geracao_convergencia": execution_result.convergence_generation,
                        "fitness_final": execution_result.final_fitness,
                        "historico_fitness": execution_result.fitness_history,
                        "semente": execution_result.random_seed,
                        "duracao_segundos": execution_result.duration_seconds,
                        "arquivo_execucao": str((per_run_directory / f"execution-{execution_result.execution_identifier:03d}.json").as_posix()),
                    }
                    for execution_result in execution_results
                ],
            }

            experiment_file_path = (
                optimization_runs_directory / f"experimento-{diet_file_path.name}"
            )
            save_json_file(experiment_file_path, experiment_payload)
            print(
                f"[{resolution_label}] Dados do experimento salvos em: {experiment_file_path}"
            )

            if overall_best_chromosome:
                optimized_diet_payload = [
                    chromosome_to_optimized_diet(chromosome)
                    for chromosome in all_chromosomes
                ]
                optimized_diet_file_path = (
                    optimized_diets_directory / f"otimizada-{diet_file_path.name}"
                )
                save_json_file(optimized_diet_file_path, optimized_diet_payload)
                print(
                    f"[{resolution_label}] {len(all_chromosomes)} dieta(s) otimizada(s) salva(s) em: {optimized_diet_file_path}"
                )


def derive_execution_seed(
    base_seed: int | None,
    resolution_label: str,
    diet_identifier: str,
    execution_identifier: int,
) -> int | None:
    """Derive a stable, independent seed for one GA execution."""
    if base_seed is None:
        return None
    material = (
        f"{base_seed}|{resolution_label}|{diet_identifier}|{execution_identifier}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
