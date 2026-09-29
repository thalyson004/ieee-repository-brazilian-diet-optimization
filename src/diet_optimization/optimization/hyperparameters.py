"""Module hyperparameters."""

from dataclasses import dataclass, field
from typing import Dict, List


GRAMS_REFERENCE_TBCA = 100.0
GRAMS_REFERENCE_FOOTPRINT = 100.0

DAYS_PER_PLAN = 5

SHORTAGE_WEIGHT_BASE = 50.0
BIG_M_PENALTY = 10000.0
MEAL_ENERGY_SHARE_PENALTY_WEIGHT = 200.0

NUTRITIONAL_CRITERION_WEIGHT = 1.0
ENVIRONMENTAL_CRITERION_WEIGHT = 1.0

ACTIVE_FOOTPRINTS_DEFAULT = ["carbon_footprint"]
FOOTPRINT_WEIGHTS_DEFAULT = {
    "carbon_footprint": 1.0,
    "water_footprint": 1.0,
    "ecological_footprint": 1.0,
}

POPULATION_SIZE_DEFAULT = 150
PLATEAU_TOLERANCE = 1e-6
MAX_STAGNATION_GENERATIONS = 40
MAX_GENERATIONS = 600
HYPERMUTATION_TRIGGER = 15
ELITISM_RATE = 0.05

MUTATION_RATES_DEFAULT = {
    "global_mutation": 0.05,
    "local_mutation": 0.15,
}

MUTATION_RATES_HYPERMUTATION = {
    "global_mutation": 0.15,
    "local_mutation": 0.30,
}

CROSSOVER_STRATEGIES = {
    "by_meal": "by_meal",
    "by_day": "by_day",
    "by_meal_type": "by_meal_type",
}

DEFAULT_CROSSOVER_STRATEGY = CROSSOVER_STRATEGIES["by_meal"]
ENABLE_CROSSOVER_REPAIR = True
REPAIR_MAX_ATTEMPTS_PER_DAY = 12

ENERGY_UPPER_FLEXIBILITY = 0.05

LIMITES_ENERGIA_REFEICAO = {
    "Café da Manhã": {"min": 0.15, "max": 0.25},
    "Lanche da Manhã": {"min": 0.00, "max": 0.10},
    "Almoço": {"min": 0.25, "max": 0.35},
    "Lanche da Tarde": {"min": 0.00, "max": 0.15},
    "Jantar": {"min": 0.20, "max": 0.30},
    "Ceia": {"min": 0.00, "max": 0.10},
}

OPTIONAL_EMPTY_MEAL_TYPES = {
    "Lanche da Manhã",
    "Lanche da Tarde",
    "Ceia",
}

CONSTRUCTIVE_EXPANSION_TOP_W = 10
CONSTRUCTIVE_EXPANSION_SAMPLE_K = 5

RESOLUTION_AG_ALIMENTOS = "ag-alimentos"
RESOLUTION_AG_REFEICOES = "ag-refeicoes"
RESOLUTION_PL_ALIMENTOS = "pl-alimentos"
RESOLUTION_PL_REFEICOES = "pl-refeicoes"

MEAL_ORDER = [
    "Café da Manhã",
    "Lanche da Manhã",
    "Almoço",
    "Lanche da Tarde",
    "Jantar",
    "Ceia",
]

MAXIMUM_GOALS = {
    "Energia": {"meta": 2000.0, "tolerancia": 1.05},
    "Sódio": {"meta": 2300.0, "tolerancia": 1.00},
    "Colesterol": {"meta": 300.0, "tolerancia": 1.00},
}

ENVIRONMENTAL_NORMALIZATION_REFERENCES = {
    "carbon_footprint": 2000.0,
    "water_footprint": 1500.0,
    "ecological_footprint": 10.0,
}

FOOTPRINT_NORMALIZATION_FUNCTIONS = {
    "carbon_footprint": "ratio",
    "water_footprint": "ratio",
    "ecological_footprint": "ratio",
}

MINIMUM_GOALS = {
    "Energia": 2000.0,
    "Carboidrato total": 302.5,
    "Proteína": 110.0,
    "Lipídios": 61.11,
    "Fibra alimentar": 25.0,
    "Vitamina A (RE)": 900.0,
    "Vitamina C": 90.0,
    "Vitamina D": 15.0,
    "Alfa-tocoferol (Vitamina E)": 15.0,
    "Tiamina": 1.2,
    "Riboflavina": 1.3,
    "Niacina": 16.0,
    "Vitamina B6": 1.3,
    "Vitamina B12": 2.4,
    "Cálcio": 1000.0,
    "Magnésio": 420.0,
}


@dataclass
class GeneticAlgorithmHyperparameters:
    """Agrupa todos os hiperparâmetros utilizados pelo algoritmo genético.

    Todos os campos possuem valores padrão definidos pelas constantes do módulo,
    permitindo sobrescrita pontual sem alterar as constantes globais.

    Campos principais:
        population_size:              Número de indivíduos na população a cada geração.
        plateau_tolerance:            Variação mínima de fitness para não ser considerada estagnação.
        max_stagnation_generations:   Número máximo de gerações sem melhora antes de encerrar.
        max_generations:              Limite absoluto de geracoes para evitar execucao indefinida.
        hypermutation_trigger:        Gerações de estagnação necessárias para ativar hipermutação.
        elitism_rate:                 Fração da população preservada por elitismo a cada geração.
        shortage_weight_base:         Peso base da penalidade por déficit nutricional.
        nutritional_criterion_weight: Peso global do critério nutricional.
        environmental_criterion_weight:
                          Peso global do critério ambiental.
        active_footprints:            Lista de pegadas ativas no experimento.
        footprint_weights:            Pesos por pegada (carbono, hídrica, ecológica).
        footprint_normalization_references:
                          Referências numéricas usadas na normalização.
        footprint_normalization_functions:
                          Função de normalização por pegada (ex.: ratio/log_ratio).
        big_m_penalty:                Fator de penalidade severa (Big-M) para violações de limites máximos.
        meal_energy_share_penalty_weight:
                  Peso de penalidade para violacoes de faixa energetica por refeicao.
        default_global_mutation_rate: Taxa de mutação global em modo normal.
        default_local_mutation_rate:  Taxa de mutação local em modo normal.
        hyper_global_mutation_rate:   Taxa de mutação global em modo hipermutação.
        hyper_local_mutation_rate:    Taxa de mutação local em modo hipermutação.
        crossover_strategy:           Estratégia de crossover aplicada para gerar filhos.
        enable_crossover_repair:      Define se o operador de reparo será executado após o crossover.
        repair_max_attempts_per_day:  Quantidade máxima de tentativas de reparo por dia.
        meal_energy_share_limits:     Faixas min/max de contribuicao energetica por tipo de refeicao.
        constructive_expansion_top_w: Quantidade de candidatos gulosos elegiveis por individuo.
        constructive_expansion_sample_k:
                  Quantidade de candidatos sorteados dentre os melhores por individuo.
        enable_global_mutation:     Ativa mutacao global (troca refeicao inteira).
        enable_local_mutation:      Ativa mutacao local no interior da refeicao.
        local_mutation_operations:  Operacoes locais permitidas (replace/add/remove).
        seed_with_base_chromosomes: Define se dietas base completas entram na populacao inicial.
        resolution_label:           Identificador textual do resolvedor associado.
    """

    population_size: int = POPULATION_SIZE_DEFAULT
    plateau_tolerance: float = PLATEAU_TOLERANCE
    max_stagnation_generations: int = MAX_STAGNATION_GENERATIONS
    max_generations: int = MAX_GENERATIONS
    hypermutation_trigger: int = HYPERMUTATION_TRIGGER
    elitism_rate: float = ELITISM_RATE
    shortage_weight_base: float = SHORTAGE_WEIGHT_BASE
    nutritional_criterion_weight: float = NUTRITIONAL_CRITERION_WEIGHT
    environmental_criterion_weight: float = ENVIRONMENTAL_CRITERION_WEIGHT
    active_footprints: List[str] = field(
        default_factory=lambda: ACTIVE_FOOTPRINTS_DEFAULT.copy()
    )
    footprint_weights: Dict[str, float] = field(
        default_factory=lambda: FOOTPRINT_WEIGHTS_DEFAULT.copy()
    )
    footprint_normalization_references: Dict[str, float] = field(
        default_factory=lambda: ENVIRONMENTAL_NORMALIZATION_REFERENCES.copy()
    )
    footprint_normalization_functions: Dict[str, str] = field(
        default_factory=lambda: FOOTPRINT_NORMALIZATION_FUNCTIONS.copy()
    )
    big_m_penalty: float = BIG_M_PENALTY
    meal_energy_share_penalty_weight: float = MEAL_ENERGY_SHARE_PENALTY_WEIGHT
    nutritional_minimum_goals: Dict[str, float] = field(
        default_factory=lambda: MINIMUM_GOALS.copy()
    )
    nutritional_maximum_goals: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            name: rules.copy() for name, rules in MAXIMUM_GOALS.items()
        }
    )
    nutrition_protocol_id: str = "historical-implemented-v1"
    secondary_nutrition_targets: List[Dict[str, object]] = field(default_factory=list)
    descriptive_nutrition_targets: List[Dict[str, object]] = field(default_factory=list)
    default_global_mutation_rate: float = MUTATION_RATES_DEFAULT["global_mutation"]
    default_local_mutation_rate: float = MUTATION_RATES_DEFAULT["local_mutation"]
    hyper_global_mutation_rate: float = MUTATION_RATES_HYPERMUTATION["global_mutation"]
    hyper_local_mutation_rate: float = MUTATION_RATES_HYPERMUTATION["local_mutation"]
    crossover_strategy: str = DEFAULT_CROSSOVER_STRATEGY
    enable_crossover_repair: bool = ENABLE_CROSSOVER_REPAIR
    repair_max_attempts_per_day: int = REPAIR_MAX_ATTEMPTS_PER_DAY
    meal_energy_share_limits: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            meal_name: limits.copy()
            for meal_name, limits in LIMITES_ENERGIA_REFEICAO.items()
        }
    )
    constructive_expansion_top_w: int = CONSTRUCTIVE_EXPANSION_TOP_W
    constructive_expansion_sample_k: int = CONSTRUCTIVE_EXPANSION_SAMPLE_K
    enable_global_mutation: bool = True
    enable_local_mutation: bool = True
    local_mutation_operations: List[str] = field(
        default_factory=lambda: ["replace", "add", "remove"]
    )
    seed_with_base_chromosomes: bool = True
    resolution_label: str = RESOLUTION_AG_REFEICOES


def build_hyperparameters_for_resolution(
    resolution_label: str,
    base_hyperparameters: GeneticAlgorithmHyperparameters,
) -> GeneticAlgorithmHyperparameters:
    """Cria copia dos hiperparametros ajustada para um tipo de resolucao AG.

    Recebe:
        resolution_label: Identificador da resolucao AG (ag-alimentos/ag-refeicoes).
        base_hyperparameters: Configuracao base recebida da CLI.

    Retorna:
        Nova instancia de GeneticAlgorithmHyperparameters apropriada ao modo.
    """
    tuned = GeneticAlgorithmHyperparameters(**vars(base_hyperparameters))
    tuned.resolution_label = resolution_label

    if resolution_label == RESOLUTION_AG_ALIMENTOS:
        tuned.population_size = min(tuned.population_size, 45)
        tuned.max_stagnation_generations = min(tuned.max_stagnation_generations, 18)
        tuned.max_generations = min(tuned.max_generations, 90)
        tuned.enable_global_mutation = False
        tuned.enable_local_mutation = True
        tuned.local_mutation_operations = ["replace", "add", "remove"]
        tuned.constructive_expansion_top_w = 0
        tuned.constructive_expansion_sample_k = 0
        tuned.seed_with_base_chromosomes = False
    else:
        tuned.population_size = min(tuned.population_size, 60)
        tuned.max_stagnation_generations = min(tuned.max_stagnation_generations, 20)
        tuned.max_generations = min(tuned.max_generations, 120)
        tuned.enable_global_mutation = True
        tuned.enable_local_mutation = True
        tuned.local_mutation_operations = ["replace", "add", "remove"]
        tuned.constructive_expansion_top_w = 0
        tuned.constructive_expansion_sample_k = 0
        tuned.seed_with_base_chromosomes = True

    return tuned


def build_hyperparameter_export(
    number_of_runs: int,
    hyperparameters: GeneticAlgorithmHyperparameters,
) -> Dict[str, object]:
    """Constrói um dicionário serializável com todos os hiperparâmetros do experimento.

    Recebe:
        number_of_runs: Número de execuções planejadas para o experimento.
        hyperparameters: Instância com os hiperparâmetros efetivos da execução.

    Retorna:
        Dicionário com estrutura hierárquica contendo tamanho de população,
        taxa de elitismo, pesos da função objetivo, parâmetros de convergência
        e taxas de mutação. Adequado para serialização direta em JSON.
    """
    return {
        "execucoes_por_arquivo": number_of_runs,
        "tamanho_populacao": hyperparameters.population_size,
        "elitismo_taxa": hyperparameters.elitism_rate,
        "pesos_funcao_objetivo": {
            "peso_falta_base": hyperparameters.shortage_weight_base,
            "peso_criterio_nutricional": hyperparameters.nutritional_criterion_weight,
            "peso_criterio_ambiental": hyperparameters.environmental_criterion_weight,
            "penalidade_big_m": hyperparameters.big_m_penalty,
            "peso_faixa_energia_por_refeicao": hyperparameters.meal_energy_share_penalty_weight,
        },
        "parametros_convergencia": {
            "tolerancia_plato": hyperparameters.plateau_tolerance,
            "max_geracoes_estagnacao": hyperparameters.max_stagnation_generations,
            "max_geracoes_absoluto": hyperparameters.max_generations,
            "limiar_ativacao_hipermutacao": hyperparameters.hypermutation_trigger,
        },
        "taxas_mutacao": {
            "padrao": {
                "mutacao_global": hyperparameters.default_global_mutation_rate,
                "mutacao_local": hyperparameters.default_local_mutation_rate,
            },
            "hipermutacao": {
                "mutacao_global": hyperparameters.hyper_global_mutation_rate,
                "mutacao_local": hyperparameters.hyper_local_mutation_rate,
            },
        },
        "crossover": {
            "estrategia": hyperparameters.crossover_strategy,
            "estrategias_disponiveis": list(CROSSOVER_STRATEGIES.values()),
            "habilitar_reparo": hyperparameters.enable_crossover_repair,
            "max_tentativas_reparo_por_dia": hyperparameters.repair_max_attempts_per_day,
        },
        "restricoes_energia": {
            "tolerancia_superior_energia_total": ENERGY_UPPER_FLEXIBILITY,
            "limites_por_refeicao": hyperparameters.meal_energy_share_limits,
        },
        "expansao_construtiva_gulosa": {
            "top_w": hyperparameters.constructive_expansion_top_w,
            "sample_k": hyperparameters.constructive_expansion_sample_k,
        },
        "algoritmo_genetico": {
            "tipo_resolucao": hyperparameters.resolution_label,
            "mutacao_global_habilitada": hyperparameters.enable_global_mutation,
            "mutacao_local_habilitada": hyperparameters.enable_local_mutation,
            "operacoes_mutacao_local": hyperparameters.local_mutation_operations,
            "inicializar_com_dietas_base": hyperparameters.seed_with_base_chromosomes,
        },
        "normalizacao_ambiental": hyperparameters.footprint_normalization_references,
        "configuracao_pegadas": {
            "pegadas_ativas": hyperparameters.active_footprints,
            "pesos_por_pegada": hyperparameters.footprint_weights,
            "funcoes_normalizacao_por_pegada": hyperparameters.footprint_normalization_functions,
        },
        "estrutura_cromossomo": {
            "dias_por_plano": DAYS_PER_PLAN,
            "refeicoes_por_dia": len(MEAL_ORDER),
        },
    }


def default_input_diet_files() -> List[str]:
    """Retorna a lista padrão dos arquivos de dieta que serão processados pelo pipeline.

    Retorna:
        Lista de nomes de arquivos JSON (caminhos relativos ao diretório de trabalho)
        contendo as dietas regular, vegetariana e vegana.
    """
    return [
        "data/diets/base/dietas-regular.json",
        "data/diets/base/dietas-vegetariana.json",
        "data/diets/base/dietas-vegana.json",
    ]


def default_context_files() -> Dict[str, str]:
    """Retorna o dicionário padrão com os caminhos dos arquivos de contexto nutricional.

    Retorna:
        Dicionário com as chaves 'tbca_map', 'tbca_db' e 'footprint_map',
        apontando para os arquivos JSON de mapeamento e bases de dados
        utilizados nos cálculos de nutrientes e pegadas ambientais.
    """
    return {
        "tbca_map": "data/maps/derived/mapa-sustentavel-tbca.json",
        "tbca_db": "data/maps/base/mapa-tbca-completo.json",
        "footprint_map": "data/maps/base/mapa-sustentavel-pegadas.json",
    }
