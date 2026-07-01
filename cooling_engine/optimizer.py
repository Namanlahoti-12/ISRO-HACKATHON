"""
Multi-Objective Optimizer — NSGA-II for Cooling Intervention Planning
=======================================================================
Finds optimal intervention combinations that balance:
  Objective 1: Maximize temperature reduction (cooling effectiveness)
  Objective 2: Minimize total cost
  Objective 3: Maximize feasibility score
  Objective 4: Maximize co-benefit count

Uses NSGA-II (Non-dominated Sorting Genetic Algorithm II) which is
the gold standard for multi-objective optimization, producing a
Pareto front of non-dominated solutions.

Reference: Deb et al. (2002) "A Fast and Elitist Multiobjective Genetic Algorithm"
"""

import os
import pickle
import random
import time
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .intervention_library import INTERVENTION_LIBRARY, get_intervention
from .feature_modifier import FeatureModifier

warnings.filterwarnings('ignore')


class CoolingOptimizer:
    """
    NSGA-II multi-objective optimizer for urban cooling interventions.

    Chromosome encoding:
        Each solution is a vector of intervention coverages.
        Gene i = coverage fraction [0.0, 1.0] for intervention i.
        Gene = 0.0 means the intervention is not used.
    """

    def __init__(self, model_bundle: Dict, feature_columns: List[str]):
        """
        Args:
            model_bundle: Loaded trained_model.pkl dict
            feature_columns: List of feature column names used by the model
        """
        self.reg_model = model_bundle['regression_model']
        self.cls_model = model_bundle['classification_model']
        self.feature_columns = feature_columns
        self.modifier = FeatureModifier()

        # Intervention catalog (only interventions that affect model features)
        self.interventions = {}
        for iid, data in INTERVENTION_LIBRARY.items():
            # Check if any effect features overlap with model features
            effect_features = set(data['feature_effects'].keys())
            model_features = set(feature_columns)
            if effect_features & model_features:
                self.interventions[iid] = data

        self.intervention_ids = list(self.interventions.keys())
        self.n_interventions = len(self.intervention_ids)
        print(f'  [OK] Optimizer initialized with {self.n_interventions} '
              f'applicable interventions')

    def _decode_chromosome(self, chromosome: np.ndarray) -> List[Dict]:
        """Convert a chromosome vector to intervention list."""
        interventions = []
        for i, coverage in enumerate(chromosome):
            if coverage > 0.05:  # Minimum 5% coverage threshold
                interventions.append({
                    'id': self.intervention_ids[i],
                    'coverage': float(round(coverage, 2))
                })
        return interventions

    def _evaluate(self, chromosome: np.ndarray,
                  hotspot_features: pd.DataFrame) -> Tuple[float, ...]:
        """
        Evaluate a chromosome (solution) on the hotspot data.

        Returns tuple of objective values:
            (neg_temp_reduction, total_cost, neg_feasibility, neg_cobenefits)

        Note: NSGA-II minimizes, so we negate objectives we want to maximize.
        """
        interventions = self._decode_chromosome(chromosome)

        if not interventions:
            return (0.0, 0.0, 0.0, 0.0)

        # Apply interventions to feature values
        modified = self.modifier.apply_to_dataframe_vectorized(
            hotspot_features[self.feature_columns],
            interventions
        )

        # Predict new heat scores
        try:
            new_scores = self.reg_model.predict(modified[self.feature_columns])
            original_scores = self.reg_model.predict(
                hotspot_features[self.feature_columns]
            )
            temp_reduction = float(np.mean(original_scores - new_scores))
        except Exception:
            temp_reduction = 0.0

        # Calculate total cost (normalized per pixel)
        total_cost = 0.0
        feasibility_scores = []
        cobenefit_count = 0

        for spec in interventions:
            idata = self.interventions[spec['id']]
            unit_cost = idata['cost_per_unit']['value']
            coverage = spec['coverage']

            # Approximate cost scaling
            total_cost += unit_cost * coverage * 10  # Scale factor

            feasibility_scores.append(
                idata['feasibility_score'] * coverage
            )
            cobenefit_count += len(idata.get('co_benefits', []))

        avg_feasibility = (
            sum(feasibility_scores) / len(feasibility_scores)
            if feasibility_scores else 0
        )

        # Return objectives (all to minimize)
        return (
            -temp_reduction,       # Maximize temp reduction → minimize negative
            total_cost / 1000,     # Minimize cost (in thousands)
            -avg_feasibility,      # Maximize feasibility → minimize negative
            -cobenefit_count / 10, # Maximize co-benefits → minimize negative
        )

    def _initialize_population(self, pop_size: int) -> np.ndarray:
        """Create initial random population."""
        population = np.random.uniform(
            0.0, 0.8,
            size=(pop_size, self.n_interventions)
        )
        # Make solutions sparse — most interventions should be zero
        mask = np.random.random(population.shape) < 0.7
        population[mask] = 0.0

        # Ensure at least a few interventions per solution
        for i in range(pop_size):
            active = np.sum(population[i] > 0)
            if active < 2:
                idx = np.random.choice(self.n_interventions, 3, replace=False)
                population[i, idx] = np.random.uniform(0.1, 0.6, 3)

        return population

    def _crossover(self, parent1: np.ndarray, parent2: np.ndarray,
                   eta: float = 20.0) -> Tuple[np.ndarray, np.ndarray]:
        """Simulated Binary Crossover (SBX)."""
        child1 = parent1.copy()
        child2 = parent2.copy()

        for i in range(self.n_interventions):
            if random.random() < 0.5:
                if abs(parent1[i] - parent2[i]) > 1e-10:
                    if parent1[i] < parent2[i]:
                        x1, x2 = parent1[i], parent2[i]
                    else:
                        x1, x2 = parent2[i], parent1[i]

                    u = random.random()
                    if u <= 0.5:
                        beta = (2.0 * u) ** (1.0 / (eta + 1.0))
                    else:
                        beta = (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta + 1.0))

                    child1[i] = 0.5 * ((1 + beta) * x1 + (1 - beta) * x2)
                    child2[i] = 0.5 * ((1 - beta) * x1 + (1 + beta) * x2)

                    child1[i] = np.clip(child1[i], 0.0, 1.0)
                    child2[i] = np.clip(child2[i], 0.0, 1.0)

        return child1, child2

    def _mutate(self, individual: np.ndarray,
                mutation_rate: float = 0.1) -> np.ndarray:
        """Polynomial mutation."""
        mutant = individual.copy()
        for i in range(self.n_interventions):
            if random.random() < mutation_rate:
                if random.random() < 0.3:
                    # Toggle: set to 0 or random value
                    mutant[i] = 0.0 if mutant[i] > 0 else random.uniform(0.1, 0.5)
                else:
                    # Perturb
                    mutant[i] += random.gauss(0, 0.1)
                    mutant[i] = np.clip(mutant[i], 0.0, 1.0)
        return mutant

    def _fast_non_dominated_sort(self, fitness_values: np.ndarray) -> List[List[int]]:
        """NSGA-II fast non-dominated sorting."""
        n = len(fitness_values)
        domination_count = np.zeros(n, dtype=int)
        dominated_set = [[] for _ in range(n)]
        fronts = [[]]

        for i in range(n):
            for j in range(i + 1, n):
                if self._dominates(fitness_values[i], fitness_values[j]):
                    dominated_set[i].append(j)
                    domination_count[j] += 1
                elif self._dominates(fitness_values[j], fitness_values[i]):
                    dominated_set[j].append(i)
                    domination_count[i] += 1

            if domination_count[i] == 0:
                fronts[0].append(i)

        current_front = 0
        while fronts[current_front]:
            next_front = []
            for i in fronts[current_front]:
                for j in dominated_set[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            current_front += 1
            fronts.append(next_front)

        return fronts[:-1]  # Remove last empty front

    def _dominates(self, a: np.ndarray, b: np.ndarray) -> bool:
        """Check if solution a dominates solution b (all objectives minimized)."""
        return np.all(a <= b) and np.any(a < b)

    def _crowding_distance(self, fitness_values: np.ndarray,
                           front: List[int]) -> np.ndarray:
        """Calculate crowding distance for diversity preservation."""
        n = len(front)
        if n <= 2:
            return np.full(n, np.inf)

        distances = np.zeros(n)
        n_obj = fitness_values.shape[1]

        for m in range(n_obj):
            sorted_idx = np.argsort(fitness_values[front, m])
            distances[sorted_idx[0]] = np.inf
            distances[sorted_idx[-1]] = np.inf

            f_range = (fitness_values[front[sorted_idx[-1]], m] -
                       fitness_values[front[sorted_idx[0]], m])

            if f_range == 0:
                continue

            for i in range(1, n - 1):
                distances[sorted_idx[i]] += (
                    (fitness_values[front[sorted_idx[i + 1]], m] -
                     fitness_values[front[sorted_idx[i - 1]], m]) / f_range
                )

        return distances

    def optimize(
        self,
        hotspot_features: pd.DataFrame,
        pop_size: int = 60,
        n_generations: int = 40,
        max_interventions: int = 6,
        verbose: bool = True
    ) -> List[Dict]:
        """
        Run NSGA-II optimization.

        Args:
            hotspot_features: DataFrame of hotspot pixel features
            pop_size: Population size
            n_generations: Number of generations
            max_interventions: Maximum interventions per solution
            verbose: Print progress

        Returns:
            List of Pareto-optimal solutions, each a dict with:
                - interventions: List[Dict]
                - objectives: Dict
                - predicted_reduction: float
                - cost: float
                - feasibility: float
        """
        if verbose:
            print(f'\n  Starting NSGA-II optimization...')
            print(f'  Population: {pop_size} | Generations: {n_generations}')
            print(f'  Interventions: {self.n_interventions} | '
                  f'Max per solution: {max_interventions}')

        # Use a subsample for faster evaluation
        sample_size = min(100, len(hotspot_features))
        sample_df = hotspot_features.sample(
            n=sample_size, random_state=42
        ).reset_index(drop=True)

        # Initialize
        population = self._initialize_population(pop_size)
        t_start = time.time()

        for gen in range(n_generations):
            # Evaluate fitness
            fitness = np.array([
                self._evaluate(ind, sample_df) for ind in population
            ])

            # Generate offspring
            offspring = []
            for _ in range(pop_size // 2):
                # Tournament selection
                candidates = random.sample(range(len(population)), 4)
                p1 = min(candidates[:2], key=lambda x: fitness[x][0])
                p2 = min(candidates[2:], key=lambda x: fitness[x][0])

                c1, c2 = self._crossover(population[p1], population[p2])
                c1 = self._mutate(c1)
                c2 = self._mutate(c2)

                # Enforce max interventions constraint
                for child in [c1, c2]:
                    active = np.where(child > 0.05)[0]
                    if len(active) > max_interventions:
                        to_remove = np.random.choice(
                            active, len(active) - max_interventions, replace=False
                        )
                        child[to_remove] = 0.0

                offspring.extend([c1, c2])

            # Combine parent + offspring
            combined = np.vstack([population, np.array(offspring)])
            combined_fitness = np.array([
                self._evaluate(ind, sample_df) for ind in combined
            ])

            # NSGA-II selection
            fronts = self._fast_non_dominated_sort(combined_fitness)

            new_population = []
            for front in fronts:
                if len(new_population) + len(front) <= pop_size:
                    new_population.extend(front)
                else:
                    # Use crowding distance for remaining slots
                    distances = self._crowding_distance(combined_fitness, front)
                    remaining = pop_size - len(new_population)
                    sorted_by_dist = np.argsort(-distances)
                    new_population.extend([front[i] for i in sorted_by_dist[:remaining]])
                    break

            population = combined[new_population]

            if verbose and (gen + 1) % 10 == 0:
                best_reduction = -min(combined_fitness[new_population, 0])
                avg_cost = np.mean(combined_fitness[new_population, 1])
                print(f'    Gen {gen+1}/{n_generations}: '
                      f'Best reduction={best_reduction:.2f}, '
                      f'Avg cost={avg_cost:.1f}k')

        elapsed = time.time() - t_start

        # Extract Pareto front solutions
        final_fitness = np.array([
            self._evaluate(ind, sample_df) for ind in population
        ])
        fronts = self._fast_non_dominated_sort(final_fitness)
        pareto_indices = fronts[0] if fronts else list(range(min(5, len(population))))

        # Build results
        results = []
        for idx in pareto_indices:
            chromosome = population[idx]
            interventions = self._decode_chromosome(chromosome)
            obj = final_fitness[idx]

            if not interventions:
                continue

            # Calculate full metrics
            total_cost = 0
            total_feasibility = []
            total_cobenefits = set()
            cooling_potential = 0

            for spec in interventions:
                idata = self.interventions[spec['id']]
                cost = idata['cost_per_unit']['value'] * spec['coverage'] * 10
                total_cost += cost
                total_feasibility.append(idata['feasibility_score'])
                total_cobenefits.update(idata.get('co_benefits', []))
                cooling_potential += (
                    idata['cooling_potential_celsius']['typical'] * spec['coverage']
                )

            result = {
                'interventions': interventions,
                'objectives': {
                    'temperature_reduction': round(-obj[0], 2),
                    'cost_thousands': round(obj[1], 2),
                    'feasibility': round(-obj[2], 3),
                    'cobenefit_score': round(-obj[3], 2),
                },
                'predicted_reduction': round(-obj[0], 2),
                'estimated_cooling_celsius': round(cooling_potential, 2),
                'total_cost': round(total_cost, 0),
                'avg_feasibility': round(
                    np.mean(total_feasibility) if total_feasibility else 0, 3
                ),
                'co_benefits': sorted(total_cobenefits),
                'n_interventions': len(interventions),
                'confidence': round(min(0.95, 0.60 + 0.05 * len(interventions)), 2),
            }
            results.append(result)

        # Sort by temperature reduction (best first)
        results.sort(key=lambda x: x['predicted_reduction'], reverse=True)

        # Add priority ranking
        for i, r in enumerate(results):
            r['priority_rank'] = i + 1
            # Priority score: balance reduction, cost-effectiveness, and feasibility
            cost_eff = (r['predicted_reduction'] / max(r['total_cost'] / 1000, 0.1))
            r['priority_score'] = round(
                0.4 * r['predicted_reduction'] +
                0.3 * r['avg_feasibility'] * 10 +
                0.2 * cost_eff +
                0.1 * len(r['co_benefits']),
                2
            )

        # Re-sort by priority score
        results.sort(key=lambda x: x['priority_score'], reverse=True)
        for i, r in enumerate(results):
            r['priority_rank'] = i + 1

        if verbose:
            print(f'\n  Optimization complete in {elapsed:.1f}s')
            print(f'  Pareto-optimal solutions: {len(results)}')
            if results:
                best = results[0]
                print(f'  Best solution: {best["predicted_reduction"]:.2f} reduction, '
                      f'cost=${best["total_cost"]:.0f}, '
                      f'feasibility={best["avg_feasibility"]:.2f}')

        return results

    def get_best_solution(self, results: List[Dict],
                          strategy: str = 'balanced') -> Dict:
        """
        Select the single best solution from the Pareto front.

        Args:
            results: List of Pareto-optimal solutions
            strategy: Selection strategy:
                - 'balanced': Best priority score (default)
                - 'max_cooling': Maximum temperature reduction
                - 'min_cost': Minimum cost
                - 'max_feasibility': Most feasible

        Returns:
            Single best solution dict
        """
        if not results:
            return {}

        if strategy == 'max_cooling':
            return max(results, key=lambda x: x['predicted_reduction'])
        elif strategy == 'min_cost':
            return min(results, key=lambda x: x['total_cost'])
        elif strategy == 'max_feasibility':
            return max(results, key=lambda x: x['avg_feasibility'])
        else:  # balanced
            return results[0]  # Already sorted by priority_score


def run_optimization(hotspot_features: pd.DataFrame,
                     model_path: str = None,
                     pop_size: int = 60,
                     n_generations: int = 40) -> Tuple[List[Dict], Dict]:
    """
    Run the full optimization pipeline.

    Returns:
        Tuple of (pareto_results, best_solution)
    """
    # Load model
    if model_path is None:
        model_path = os.path.join(
            os.path.dirname(__file__), '..', 'models', 'output',
            'trained_model.pkl'
        )

    with open(model_path, 'rb') as f:
        model_bundle = pickle.load(f)

    feature_columns = model_bundle['feature_columns']

    # Initialize optimizer
    optimizer = CoolingOptimizer(model_bundle, feature_columns)

    # Run NSGA-II
    results = optimizer.optimize(
        hotspot_features,
        pop_size=pop_size,
        n_generations=n_generations,
    )

    best = optimizer.get_best_solution(results, strategy='balanced')

    return results, best
