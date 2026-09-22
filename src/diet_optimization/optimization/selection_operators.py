"""Module selection operators."""

import random
from typing import Any, List, Sequence, Tuple


def tournament_selection(
    scored_population: Sequence[Tuple[Any, float]],
    tournament_size: int = 3,
) -> Any:
    """Seleciona um indivíduo da população pelo método de torneio.

    Amostra aleatoriamente um subconjunto da população e retorna o indivíduo
    com maior fitness entre os amostrados. Favorece indivíduos mais aptos
    sem eliminar completamente os menos aptos.

    Recebe:
        scored_population: Sequência de tuplas (cromossomo, fitness), ordenada
                           do maior para o menor fitness.
        tournament_size:   Número de indivíduos amostrados para o torneio (padrão: 3).

    Retorna:
        O cromossomo vencedor do torneio (com maior fitness entre os amostrados).
    """
    sampled_individuals = random.sample(list(scored_population), tournament_size)
    selected_individual, _ = max(
        sampled_individuals,
        key=lambda candidate_entry: candidate_entry[1],
    )
    return selected_individual


def select_elite_individuals(
    scored_population: Sequence[Tuple[Any, float]],
    elite_rate: float,
) -> List[Any]:
    """Seleciona os melhores indivíduos da população para preservação por elitismo.

    Garante que pelo menos um indivíduo seja selecionado, mesmo quando a taxa
    elite_rate resultar em zero após o truncamento inteiro.

    Recebe:
        scored_population: Sequência de tuplas (cromossomo, fitness) já ordenada
                           do maior para o menor fitness.
        elite_rate:        Fração da população a ser preservada (ex.: 0.05 = 5%).

    Retorna:
        Lista com os cromossomos de elite, sem as pontuações de fitness.
    """
    elite_count = max(1, int(len(scored_population) * elite_rate))
    return [individual for individual, _ in scored_population[:elite_count]]
