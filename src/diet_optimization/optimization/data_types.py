"""Module data types."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


class ContextFiles(TypedDict):
    """Dicionário tipado com os caminhos dos arquivos de contexto nutricional.

    Campos:
        tbca_map: Caminho para o arquivo JSON de mapeamento nome-do-alimento -> código TBCA.
        tbca_db:  Caminho para o arquivo JSON da base completa de nutrientes TBCA.
        footprint_map: Caminho para o arquivo JSON com pegadas ambientais por alimento.
    """

    tbca_map: str
    tbca_db: str
    footprint_map: str


@dataclass
class NutritionalContext:
    """Agrega todas as bases de dados necessárias para calcular nutrientes e pegadas.

    Campos:
        tbca_map:      Mapeamento de nome do alimento para o código TBCA correspondente.
        tbca_database: Base de dados TBCA com os valores nutricionais por 100 g de cada alimento.
        footprint_map: Mapeamento de nome do alimento para suas pegadas ambientais
                       (carbono, hídrica e ecológica) por 1000 g.
    """

    tbca_map: Dict[str, str]
    tbca_database: Dict[str, Any]
    footprint_map: Dict[str, Any]


@dataclass
class MealCandidate:
    """Representa uma refeição candidata dentro de um cromossomo do algoritmo genético.

    Campos:
        itens:     Lista de alimentos da refeição, cada um com nome e quantidade em gramas.
        nutrientes: Totais nutricionais já calculados para a refeição inteira.
        pegadas:   Totais de pegadas ambientais (carbono, hídrica, ecológica) da refeição.
    """

    itens: List[Dict[str, Any]]
    nutrientes: Dict[str, float]
    pegadas: Dict[str, float]


@dataclass
class ExecutionResult:
    """Armazena os resultados de uma única execução do algoritmo genético.

    Campos:
        execution_identifier:   Número sequencial que identifica a execução dentro do experimento.
        convergence_generation: Geração em que o critério de convergência foi atingido.
        final_fitness:          Melhor valor de fitness registrado ao final da execução.
        fitness_history:        Lista com o melhor fitness de cada geração, em ordem cronológica.
    """

    execution_identifier: int
    convergence_generation: int
    final_fitness: float
    fitness_history: List[float]
    random_seed: Optional[int] = None
    duration_seconds: Optional[float] = None


@dataclass
class ExperimentData:
    """Consolida os dados de todas as execuções de um experimento de otimização.

    Campos:
        source_file_name:               Nome do arquivo de dieta que serviu como base do experimento.
        total_executions:               Quantidade total de execuções realizadas.
        average_convergence_generation: Média das gerações de convergência entre todas as execuções.
        global_best_fitness:            Maior valor de fitness encontrado em qualquer execução.
        executions:                     Lista com o resultado detalhado de cada execução individual.
        best_chromosome:                Cromossomo (dieta) com o melhor fitness global encontrado.
    """

    source_file_name: str
    total_executions: int
    average_convergence_generation: float = 0.0
    global_best_fitness: float = 0.0
    executions: List[ExecutionResult] = field(default_factory=list)
    best_chromosome: Optional[List[MealCandidate]] = None
