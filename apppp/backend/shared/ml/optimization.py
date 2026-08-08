"""NSGA-II multi-objective optimization on top candidates."""

import numpy as np
from typing import List, Dict, Any

try:
    from deap import base, creator, tools, algorithms
    HAS_DEAP = True
except ImportError:
    HAS_DEAP = False

def _setup_deap():
    if HAS_DEAP:
        if not hasattr(creator, "FitnessMulti"):
            creator.create("FitnessMulti", base.Fitness, weights=(1.0, 1.0, 1.0))
        if not hasattr(creator, "Individual"):
            creator.create("Individual", list, fitness=creator.FitnessMulti)

def _evaluate_candidate(ind, candidates: List[Dict[str, Any]]) -> tuple:
    idx = int(ind[0]) % len(candidates)
    mat = candidates[idx]
    strength = min(float(mat.get("tensile_strength", 0.0)) / 300.0, 1.0)
    biodeg = 1.0 - min(float(mat.get("biodegradation_days", 365.0)) / 730.0, 1.0)
    biocompat = min(float(mat.get("biocompatibility", 0.0)) / 10.0, 1.0)
    return (strength, biodeg, biocompat)

def _mutate_ind(individual, n_cands):
    individual[0] = np.random.randint(0, n_cands)
    return (individual,)

def run_nsga2_optimization(
    candidates: List[Dict[str, Any]],
    n_generations: int = 40,
    population_size: int = 30,
    random_seed: int = 42,
) -> List[int]:
    """Run NSGA-II to find Pareto-optimal candidate indices."""
    if len(candidates) < 2 or not HAS_DEAP:
        return list(range(len(candidates)))

    _setup_deap()
    np.random.seed(random_seed)
    n_cands = len(candidates)

    toolbox = base.Toolbox()
    toolbox.register("attr_idx", np.random.randint, 0, n_cands)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_idx, n=1)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", _evaluate_candidate, candidates=candidates)
    toolbox.register("mate", tools.cxUniform, indpb=0.5)
    toolbox.register("mutate", _mutate_ind, n_cands=n_cands)
    toolbox.register("select", tools.selNSGA2)

    pop_size = min(population_size, n_cands * 4)
    pop = toolbox.population(n=pop_size)

    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)

    for _ in range(n_generations):
        offspring = algorithms.varAnd(pop, toolbox, cxpb=0.7, mutpb=0.3)
        for ind in offspring:
            if not ind.fitness.valid:
                ind.fitness.values = toolbox.evaluate(ind)
        pop = toolbox.select(offspring + pop, k=pop_size)

    pareto = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
    pareto_indices = sorted(list(set(int(ind[0]) % n_cands for ind in pareto)))
    return pareto_indices
