"""Module genetic algorithm."""

import copy
import random
from typing import Dict, List, Optional, Tuple

from .crossover_operators import apply_crossover, repair_offspring_energy_limit
from .data_types import NutritionalContext
from .fitness_functions import evaluate_diet_fitness
from .hyperparameters import DAYS_PER_PLAN, GeneticAlgorithmHyperparameters, MEAL_ORDER
from .mutation_operators import mutate_chromosome
from .selection_operators import select_elite_individuals, tournament_selection


class GeneticAlgorithm:
    """Implementa o algoritmo genético multicriterio para otimização de dietas.

    Encapsula todo o ciclo evolutivo: inicialização, avaliação, seleção,
    crossover, mutação e critério de parada por estagnação (platô).
    Suporta hipermutação automática quando a população estagna por muitas gerações.
    """

    def __init__(
        self,
        meal_pool: Dict[str, List[Dict]],
        food_pool: Dict[str, List[Dict]],
        nutritional_context: NutritionalContext,
        hyperparameters: GeneticAlgorithmHyperparameters,
        initial_seed_chromosomes: Optional[List[List[Dict]]] = None,
    ) -> None:
        """Inicializa o algoritmo genético com os pools de dados e a configuração.

        Recebe:
            meal_pool:            Dicionário mapeando tipo de refeição para lista de
                                  refeições candidatas pré-calculadas (nutrientes e pegadas).
            food_pool:            Dicionário mapeando tipo de refeição para lista de
                                  alimentos disponíveis para mutação local.
            nutritional_context:  Bases de dados nutricionais e de pegadas para recálculos.
            hyperparameters:      Instância com todos os hiperparâmetros do algoritmo.
        """
        self.meal_pool = meal_pool
        self.food_pool = food_pool
        self.nutritional_context = nutritional_context
        self.hyperparameters = hyperparameters
        self.initial_seed_chromosomes = initial_seed_chromosomes or []

    def _evaluate_chromosome_fitness(self, chromosome: List[Dict]) -> float:
        """Avalia um cromossomo usando os hiperparâmetros ativos da execução."""
        return evaluate_diet_fitness(
            chromosome=chromosome,
            nutritional_criterion_weight=self.hyperparameters.nutritional_criterion_weight,
            environmental_criterion_weight=self.hyperparameters.environmental_criterion_weight,
            active_footprints=self.hyperparameters.active_footprints,
            footprint_weights=self.hyperparameters.footprint_weights,
            footprint_normalization_references=self.hyperparameters.footprint_normalization_references,
            footprint_normalization_functions=self.hyperparameters.footprint_normalization_functions,
            meal_energy_share_limits=self.hyperparameters.meal_energy_share_limits,
            meal_energy_share_penalty_weight=self.hyperparameters.meal_energy_share_penalty_weight,
            nutritional_minimum_goals=self.hyperparameters.nutritional_minimum_goals,
            nutritional_maximum_goals=self.hyperparameters.nutritional_maximum_goals,
        )

    def _candidate_meals_for_slot(
        self, meal_type_name: str, day_index: int
    ) -> List[Dict]:
        """Retorna candidatos de troca para um tipo/posição diária de refeição.

        Assume que o pool contém refeições em blocos de 5 dias por dieta de origem.
        Assim, para um dia específico, percorre todas as dietas de origem e coleta
        a refeição correspondente daquele dia.
        """
        pool = self.meal_pool.get(meal_type_name, [])
        if not pool:
            return []

        source_diet_count = max(1, len(pool) // DAYS_PER_PLAN)
        candidates: List[Dict] = []

        for source_diet_index in range(source_diet_count):
            candidate_index = (source_diet_index * DAYS_PER_PLAN) + day_index
            if candidate_index < len(pool):
                candidates.append(pool[candidate_index])

        return candidates

    def apply_constructive_greedy_expansion(
        self,
        population: List[List[Dict]],
    ) -> List[List[Dict]]:
        """Expande cada indivíduo com trocas gulosas antes dos operadores evolutivos.

        Para cada cromossomo, gera candidatos por troca de refeição no mesmo tipo,
        avalia todos, mantém os W melhores e sorteia K dentre eles para compor a
        população expandida da geração.
        """
        if (
            self.hyperparameters.constructive_expansion_sample_k <= 0
            or self.hyperparameters.constructive_expansion_top_w <= 0
        ):
            return population

        # Evita deepcopy massivo por candidato: usa cópia rasa para avaliação e
        # preserva cópia profunda apenas dos candidatos realmente selecionados.
        expanded_population: List[List[Dict]] = [list(ch) for ch in population]
        meal_count_per_day = len(MEAL_ORDER)

        for chromosome in population:
            greedy_candidates: List[Tuple[List[Dict], float]] = []

            for meal_position, meal_type_name in enumerate(MEAL_ORDER):
                for day_index in range(DAYS_PER_PLAN):
                    chromosome_index = (day_index * meal_count_per_day) + meal_position
                    current_meal = chromosome[chromosome_index]

                    slot_candidates = self._candidate_meals_for_slot(
                        meal_type_name,
                        day_index,
                    )
                    for candidate_meal in slot_candidates:
                        if candidate_meal.get("itens") == current_meal.get("itens"):
                            continue

                        candidate_chromosome = list(chromosome)
                        candidate_chromosome[chromosome_index] = candidate_meal
                        candidate_fitness = self._evaluate_chromosome_fitness(
                            candidate_chromosome
                        )
                        greedy_candidates.append(
                            (candidate_chromosome, candidate_fitness)
                        )

            if not greedy_candidates:
                continue

            greedy_candidates.sort(
                key=lambda candidate_entry: candidate_entry[1],
                reverse=True,
            )
            top_w = min(
                self.hyperparameters.constructive_expansion_top_w,
                len(greedy_candidates),
            )
            sample_k = min(
                self.hyperparameters.constructive_expansion_sample_k,
                top_w,
            )
            if sample_k <= 0:
                continue

            selected_candidates = random.sample(greedy_candidates[:top_w], sample_k)
            for candidate_chromosome, _candidate_fitness in selected_candidates:
                expanded_population.append(copy.deepcopy(candidate_chromosome))

        return expanded_population

    def initialize_population(self) -> List[List[Dict]]:
        """Gera a população inicial com cromossomos criados aleatoriamente.

        Cada cromossomo representa 5 dias de dieta, com 6 refeições por dia
        (conforme MEAL_ORDER), totalizando 30 genes por cromossomo. Cada gene
        é uma refeição sorteada aleatoriamente do pool correspondente.

        Retorna:
            Lista de cromossomos (cada cromossomo é uma lista de 30 dicionários
            de refeição) com tamanho igual a population_size.
        """
        initial_population: List[List[Dict]] = []

        if self.hyperparameters.seed_with_base_chromosomes:
            for chromosome in self.initial_seed_chromosomes:
                if len(initial_population) >= self.hyperparameters.population_size:
                    break
                initial_population.append(copy.deepcopy(chromosome))

        for _population_index in range(
            len(initial_population), self.hyperparameters.population_size
        ):
            chromosome: List[Dict] = []
            for _day_index in range(DAYS_PER_PLAN):
                for meal_type_name in MEAL_ORDER:
                    chromosome.append(
                        copy.deepcopy(random.choice(self.meal_pool[meal_type_name]))
                    )
            initial_population.append(chromosome)

        return initial_population

    def evaluate_population(
        self,
        population: List[List[Dict]],
    ) -> List[Tuple[List[Dict], float]]:
        """Avalia todos os cromossomos da população e os ordena do melhor para o pior.

        Recebe:
            population: Lista de cromossomos a serem avaliados.

        Retorna:
            Lista de tuplas (cromossomo, fitness) ordenada de forma decrescente pelo fitness.
        """
        scored_population: List[Tuple[List[Dict], float]] = []

        for chromosome in population:
            chromosome_fitness = self._evaluate_chromosome_fitness(chromosome)
            scored_population.append((chromosome, chromosome_fitness))

        scored_population.sort(
            key=lambda population_entry: population_entry[1],
            reverse=True,
        )
        return scored_population

    def choose_mutation_rates(self, stagnation_counter: int) -> Tuple[float, float]:
        """Decide as taxas de mutação a aplicar com base no nível de estagnação atual.

        Ativa o modo de hipermutação quando o contador de estagnação ultrapassa
        o limiar configurado, aumentando a diversidade genética para escapar de
        ótimos locais.

        Recebe:
            stagnation_counter: Número de gerações consecutivas sem melhora significativa.

        Retorna:
            Tupla (taxa_mutação_global, taxa_mutação_local) adequada ao contexto atual.
        """
        if stagnation_counter >= self.hyperparameters.hypermutation_trigger:
            return (
                self.hyperparameters.hyper_global_mutation_rate,
                self.hyperparameters.hyper_local_mutation_rate,
            )
        return (
            self.hyperparameters.default_global_mutation_rate,
            self.hyperparameters.default_local_mutation_rate,
        )

    def run(self) -> Tuple[List[Dict], List[float], int]:
        """Executa o ciclo evolutivo completo até o critério de parada ser atingido.

        O loop principal realiza: avaliação da população, verificação de convergência
        por platô, seleção por elitismo e torneio, crossover configurável,
        reparo pós-crossover opcional e mutação.
        O processo termina quando o fitness não melhora por max_stagnation_generations
        gerações consecutivas.

        Retorna:
            Tupla com três elementos:
            - O melhor cromossomo encontrado (lista de dicionários de refeição).
            - Histórico de fitness (melhor valor por geração, em ordem cronológica).
            - Geração em que o critério de convergência foi atingido.
        """
        population = self.initialize_population()
        generation_number = 0
        best_global_fitness = float("-inf")
        stagnation_counter = 0
        convergence_generation = 0
        fitness_history: List[float] = []
        self.stop_reason = None

        while True:
            population = self.apply_constructive_greedy_expansion(population)
            scored_population = self.evaluate_population(population)
            current_best_fitness = scored_population[0][1]
            fitness_history.append(current_best_fitness)

            if (
                current_best_fitness - best_global_fitness
            ) < self.hyperparameters.plateau_tolerance:
                stagnation_counter += 1
            else:
                best_global_fitness = current_best_fitness
                stagnation_counter = 0

            print(
                "   Geracao: "
                f"{generation_number:03d} | "
                f"Fitness: {current_best_fitness:.6f} | "
                f"Plato: {stagnation_counter}/{self.hyperparameters.max_stagnation_generations}",
                end="\r",
            )

            if stagnation_counter >= self.hyperparameters.max_stagnation_generations:
                convergence_generation = generation_number
                self.stop_reason = "stagnation_limit"
                print(
                    f"   Convergencia atingida na geracao {generation_number}.{' ' * 20}"
                )
                break

            if generation_number >= self.hyperparameters.max_generations:
                convergence_generation = generation_number
                self.stop_reason = "generation_limit"
                print(
                    f"   Limite maximo de geracoes ({self.hyperparameters.max_generations}) atingido.{' ' * 8}"
                )
                break

            global_mutation_rate, local_mutation_rate = self.choose_mutation_rates(
                stagnation_counter
            )
            elite_chromosomes = select_elite_individuals(
                scored_population,
                self.hyperparameters.elitism_rate,
            )

            new_population = [
                copy.deepcopy(chromosome) for chromosome in elite_chromosomes
            ]

            while len(new_population) < self.hyperparameters.population_size:
                first_parent = tournament_selection(scored_population)
                second_parent = tournament_selection(scored_population)

                offspring = apply_crossover(
                    first_parent,
                    second_parent,
                    self.hyperparameters.crossover_strategy,
                )
                if self.hyperparameters.enable_crossover_repair:
                    offspring = repair_offspring_energy_limit(
                        offspring,
                        self.meal_pool,
                        meal_order=MEAL_ORDER,
                        days_per_plan=DAYS_PER_PLAN,
                        max_repair_attempts_per_day=self.hyperparameters.repair_max_attempts_per_day,
                        energy_ceiling_kcal=(
                            self.hyperparameters.nutritional_maximum_goals["Energia"]["meta"]
                            * self.hyperparameters.nutritional_maximum_goals["Energia"].get("tolerancia", 1.0)
                        ),
                    )

                mutated_offspring = mutate_chromosome(
                    offspring,
                    self.meal_pool,
                    self.food_pool,
                    self.nutritional_context,
                    global_mutation_rate,
                    local_mutation_rate,
                    enable_global_mutation=self.hyperparameters.enable_global_mutation,
                    enable_local_mutation=self.hyperparameters.enable_local_mutation,
                    local_mutation_operations=self.hyperparameters.local_mutation_operations,
                )
                new_population.append(mutated_offspring)

            population = new_population
            generation_number += 1

        best_chromosome = scored_population[0][0]
        return best_chromosome, fitness_history, convergence_generation
