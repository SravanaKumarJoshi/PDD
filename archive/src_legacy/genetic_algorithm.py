"""
NSGA-II multi-objective optimization on top-N candidates only.
Objectives: maximize strength, biodegradability, biocompatibility.
"""
import numpy as np
from deap import base, creator, tools, algorithms
from typing import Any


def _setup_deap():
    """Initialize DEAP types (safe for re-import)."""
    if not hasattr(creator, "FitnessMulti"):
        creator.create("FitnessMulti", base.Fitness, weights=(1.0, 1.0, 1.0))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMulti)


def _evaluate(individual, candidates):
    """Evaluate a candidate index. Returns (strength, biodeg, biocompat)."""
    idx = int(individual[0]) % len(candidates)
    mat = candidates[idx]
    # Normalize to 0-1 ranges for fair comparison
    strength = min(mat.get("tensile_strength", 0) / 300.0, 1.0)
    biodeg = 1.0 - min(mat.get("biodegradation_days", 365) / 730.0, 1.0)
    biocompat = min(mat.get("biocompatibility", 0) / 10.0, 1.0)
    return (strength, biodeg, biocompat)


def run_nsga2(
    candidates: list[dict],
    n_generations: int = 50,
    population_size: int = 40,
    random_seed: int = 42,
) -> dict[str, Any]:
    """
    Run NSGA-II on top-N candidate materials.

    Args:
        candidates: List of material dicts (from XGBoost top-N).
        n_generations: Number of GA generations.
        population_size: GA population size.

    Returns:
        Dict with pareto_front indices and objectives.
    """
    if len(candidates) < 2:
        # Not enough for optimization
        return {
            "pareto_indices": list(range(len(candidates))),
            "pareto_objectives": [_evaluate([i], candidates) for i in range(len(candidates))],
            "all_objectives": [],
        }

    _setup_deap()
    np.random.seed(random_seed)

    n_cands = len(candidates)
    toolbox = base.Toolbox()
    toolbox.register("attr_idx", np.random.randint, 0, n_cands)
    toolbox.register("individual", tools.initRepeat, creator.Individual,
                     toolbox.attr_idx, n=1)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", _evaluate, candidates=candidates)
    toolbox.register("mate", tools.cxUniform, indpb=0.5)
    toolbox.register("mutate", _mutate, n_cands=n_cands)
    toolbox.register("select", tools.selNSGA2)

    pop_size = min(population_size, n_cands * 4)
    pop = toolbox.population(n=pop_size)

    # Evaluate initial population
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)

    for _ in range(n_generations):
        offspring = algorithms.varAnd(pop, toolbox, cxpb=0.7, mutpb=0.3)
        for ind in offspring:
            if not ind.fitness.valid:
                ind.fitness.values = toolbox.evaluate(ind)
        pop = toolbox.select(offspring + pop, k=pop_size)

    # Extract Pareto front
    pareto = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]

    pareto_indices = list(set(int(ind[0]) % n_cands for ind in pareto))
    pareto_objectives = [_evaluate([i], candidates) for i in pareto_indices]

    return {
        "pareto_indices": pareto_indices,
        "pareto_objectives": pareto_objectives,
    }


def _mutate(individual, n_cands):
    """Mutate by randomly changing the candidate index."""
    individual[0] = np.random.randint(0, n_cands)
    return (individual,)


def get_pareto_materials(candidates: list[dict], pareto_result: dict) -> list[dict]:
    """Extract the actual Pareto-optimal materials."""
    return [candidates[i] for i in pareto_result["pareto_indices"]]
