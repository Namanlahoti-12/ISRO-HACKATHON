"""
Cooling Engine — Main Orchestrator
=====================================
Physics-Informed Urban Cooling Optimization Engine.

Orchestrates the full pipeline:
  1. Load trained model and dataset
  2. Detect UHI hotspots
  3. Profile hotspot features
  4. Run NSGA-II optimization for best intervention combinations
  5. Apply best interventions and predict new temperatures
  6. Generate all output reports and maps
  7. Export results

Usage:
    python -m cooling_engine.cooling_engine
    python -m cooling_engine.cooling_engine --data path/to/dataset.csv
"""

import argparse
import json
import os
import pickle
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cooling_engine.hotspot_detector import HotspotDetector
from cooling_engine.feature_modifier import FeatureModifier
from cooling_engine.optimizer import CoolingOptimizer
from cooling_engine.intervention_library import (
    get_all_interventions, export_library_json, get_category_summary
)
from cooling_engine.report_generator import ReportGenerator
from cooling_engine.map_generator import MapGenerator


class UrbanCoolingEngine:
    """
    Main orchestrator for the Physics-Informed Urban Cooling Optimization Engine.

    Integrates all components:
      - HotspotDetector: Finds UHI hotspots
      - FeatureModifier: Applies physics-based feature changes
      - CoolingOptimizer: NSGA-II multi-objective optimization
      - ReportGenerator: CSV/JSON output
      - MapGenerator: Spatial visualizations
    """

    def __init__(self, data_path: str, model_path: str = None,
                 output_dir: str = None, city_name: str = 'Delhi'):
        """
        Args:
            data_path: Path to master_dataset.csv
            model_path: Path to trained_model.pkl (auto-detected if None)
            output_dir: Output directory (default: outputs/cooling_analysis)
            city_name: City name for report metadata
        """
        self.data_path = data_path
        self.city_name = city_name

        # Auto-detect paths relative to project structure
        project_root = os.path.join(os.path.dirname(__file__), '..')

        self.model_path = model_path or os.path.join(
            project_root, 'models', 'output', 'trained_model.pkl'
        )
        self.output_dir = output_dir or os.path.join(
            project_root, 'outputs', 'cooling_analysis'
        )

        os.makedirs(self.output_dir, exist_ok=True)

        # Components (initialized lazily)
        self.detector = None
        self.modifier = None
        self.optimizer = None
        self.report_gen = None
        self.map_gen = None

        # Data
        self.df = None
        self.hotspots = None
        self.zone_profiles = None
        self.optimization_results = None
        self.best_solution = None
        self.modified_df = None
        self.model_bundle = None

    def run(self, n_zones: int = 5, pop_size: int = 60,
            n_generations: int = 40) -> Dict:
        """
        Run the complete cooling optimization pipeline.

        Args:
            n_zones: Number of hotspot zones for clustering
            pop_size: NSGA-II population size
            n_generations: NSGA-II generations

        Returns:
            Dict with all results and file paths
        """
        t_start = time.time()

        print('\n' + '#' * 70)
        print('#    PHYSICS-INFORMED URBAN COOLING OPTIMIZATION ENGINE')
        print('#    ISRO Bharatiya Antariksh Hackathon')
        print('#' * 70)
        print(f'\n  City:    {self.city_name}')
        print(f'  Data:    {self.data_path}')
        print(f'  Model:   {self.model_path}')
        print(f'  Output:  {self.output_dir}')

        # ── Step 1: Load Data and Model ──────────────────────────────
        self._step1_load()

        # ── Step 2: Detect Hotspots ──────────────────────────────────
        self._step2_detect_hotspots(n_zones)

        # ── Step 3: Optimize Interventions ───────────────────────────
        self._step3_optimize(pop_size, n_generations)

        # ── Step 4: Apply Best Solution ──────────────────────────────
        self._step4_apply_best()

        # ── Step 5: Generate Reports ─────────────────────────────────
        report_paths = self._step5_generate_reports()

        # ── Step 6: Generate Maps ────────────────────────────────────
        map_paths = self._step6_generate_maps()

        # ── Summary ──────────────────────────────────────────────────
        elapsed = time.time() - t_start

        results = {
            'city': self.city_name,
            'total_pixels': len(self.df),
            'hotspot_pixels': len(self.hotspots),
            'zones': len(self.zone_profiles),
            'pareto_solutions': len(self.optimization_results),
            'best_solution': self.best_solution,
            'report_paths': report_paths,
            'map_paths': map_paths,
            'elapsed_seconds': round(elapsed, 1),
        }

        self._print_summary(results)

        return results

    def _step1_load(self):
        """Load dataset and model."""
        print('\n' + '=' * 70)
        print('  STEP 1: LOAD DATA & MODEL')
        print('=' * 70)

        # Load dataset
        self.df = pd.read_csv(self.data_path)
        print(f'  [OK] Dataset: {self.df.shape[0]} rows × {self.df.shape[1]} cols')

        # Load model
        with open(self.model_path, 'rb') as f:
            self.model_bundle = pickle.load(f)

        model_name = self.model_bundle['best_model_name']
        n_features = len(self.model_bundle['feature_columns'])
        print(f'  [OK] Model: {model_name} ({n_features} features)')

        # Initialize detector
        self.detector = HotspotDetector()
        self.detector.model_bundle = self.model_bundle
        self.detector.reg_model = self.model_bundle['regression_model']
        self.detector.cls_model = self.model_bundle['classification_model']
        self.detector.feature_columns = self.model_bundle['feature_columns']
        self.detector.heat_classes = self.model_bundle['heat_classes']

        # Initialize other components
        self.modifier = FeatureModifier()
        self.report_gen = ReportGenerator(self.output_dir)
        self.map_gen = MapGenerator(self.output_dir)

    def _step2_detect_hotspots(self, n_zones: int):
        """Detect and cluster hotspots."""
        print('\n' + '=' * 70)
        print('  STEP 2: DETECT UHI HOTSPOTS')
        print('=' * 70)

        # Predict heat scores
        self.df = self.detector.predict(self.df)
        print(f'  [OK] Heat Score range: '
              f'{self.df["HeatScore_Predicted"].min():.1f} - '
              f'{self.df["HeatScore_Predicted"].max():.1f}')

        # Detect hotspots (High + Extreme class)
        self.hotspots = self.detector.detect_hotspots(self.df, min_class=2)

        # Cluster into zones
        self.hotspots = self.detector.cluster_hotspots(
            self.hotspots, n_clusters=n_zones
        )

        # Profile zones
        self.zone_profiles = self.detector.get_zone_profiles(
            self.hotspots, self.df
        )

        # Print vulnerability summary
        print('\n  Vulnerability Summary:')
        for zid, profile in self.zone_profiles.items():
            vulns = [k for k, v in profile.get('vulnerability_profile', {}).items()
                     if v is True]
            print(f'    Zone {zid}: score={profile["avg_heat_score"]:.1f}, '
                  f'vulnerabilities={vulns[:3]}')

    def _step3_optimize(self, pop_size: int, n_generations: int):
        """Run NSGA-II optimization."""
        print('\n' + '=' * 70)
        print('  STEP 3: NSGA-II OPTIMIZATION')
        print('=' * 70)

        feature_columns = self.model_bundle['feature_columns']

        # Initialize optimizer
        self.optimizer = CoolingOptimizer(self.model_bundle, feature_columns)

        # Run optimization on hotspot data
        self.optimization_results = self.optimizer.optimize(
            self.hotspots,
            pop_size=pop_size,
            n_generations=n_generations,
        )

        # Select best solution
        self.best_solution = self.optimizer.get_best_solution(
            self.optimization_results, strategy='balanced'
        )

        if self.best_solution:
            print(f'\n  Best Solution:')
            for spec in self.best_solution.get('interventions', []):
                name = spec['id'].replace('_', ' ').title()
                print(f'    • {name}: {spec["coverage"]*100:.0f}% coverage')
            print(f'    Predicted reduction: '
                  f'{self.best_solution["predicted_reduction"]:.2f}')
            print(f'    Estimated cost: ${self.best_solution["total_cost"]:.0f}')

    def _step4_apply_best(self):
        """Apply the best intervention to hotspots and re-predict."""
        print('\n' + '=' * 70)
        print('  STEP 4: APPLY BEST INTERVENTION & RE-PREDICT')
        print('=' * 70)

        if not self.best_solution or not self.best_solution.get('interventions'):
            print('  [WARN] No valid solution to apply')
            self.modified_df = self.hotspots.copy()
            return

        feature_columns = self.model_bundle['feature_columns']

        # Apply interventions to all hotspot pixels
        self.modified_df = self.modifier.apply_to_dataframe_vectorized(
            self.hotspots,
            self.best_solution['interventions']
        )

        # Re-predict with modified features
        X_modified = self.modified_df[feature_columns].copy()
        nan_cols = X_modified.columns[X_modified.isna().any()].tolist()
        if nan_cols:
            X_modified = X_modified.fillna(X_modified.median())

        self.modified_df['HeatScore_Predicted'] = (
            self.model_bundle['regression_model']
            .predict(X_modified).clip(0, 100).round(2)
        )
        self.modified_df['HeatClass_Predicted'] = (
            self.model_bundle['classification_model'].predict(X_modified)
        )
        self.modified_df['HeatClass_Label'] = (
            self.modified_df['HeatClass_Predicted'].map(
                {i: name for i, name in enumerate(self.model_bundle['heat_classes'])}
            )
        )

        # Calculate reduction
        before_mean = self.hotspots['HeatScore_Predicted'].mean()
        after_mean = self.modified_df['HeatScore_Predicted'].mean()
        reduction = before_mean - after_mean

        print(f'  [OK] Before: avg HeatScore = {before_mean:.2f}')
        print(f'  [OK] After:  avg HeatScore = {after_mean:.2f}')
        print(f'  [OK] Reduction: {reduction:.2f} points')

        # Class transition analysis
        before_classes = self.hotspots['HeatClass_Label'].value_counts()
        after_classes = self.modified_df['HeatClass_Label'].value_counts()
        print(f'\n  Class transitions:')
        print(f'    Before: {dict(before_classes)}')
        print(f'    After:  {dict(after_classes)}')

    def _step5_generate_reports(self) -> Dict[str, str]:
        """Generate all output files."""
        print('\n' + '=' * 70)
        print('  STEP 5: GENERATE REPORTS')
        print('=' * 70)

        paths = {}

        # recommendations.json
        paths['recommendations'] = self.report_gen.generate_recommendations_json(
            self.optimization_results,
            self.zone_profiles,
            self.best_solution or {},
            self.city_name
        )

        # optimization_results.csv
        paths['optimization'] = self.report_gen.generate_optimization_results_csv(
            self.optimization_results
        )

        # before_after_predictions.csv
        feature_columns = self.model_bundle['feature_columns']
        paths['before_after'] = self.report_gen.generate_before_after_csv(
            self.hotspots, self.modified_df,
            feature_columns
        )

        # intervention_library.json
        paths['library'] = self.report_gen.generate_intervention_library_json()

        return paths

    def _step6_generate_maps(self) -> Dict[str, str]:
        """Generate all spatial visualizations."""
        return self.map_gen.generate_all_maps(
            before_df=self.hotspots,
            after_df=self.modified_df,
            full_df=self.df
        )

    def _print_summary(self, results: Dict):
        """Print final summary."""
        print('\n' + '#' * 70)
        print('#    COOLING OPTIMIZATION COMPLETE')
        print('#' * 70)
        print(f'\n  City: {results["city"]}')
        print(f'  Total pixels: {results["total_pixels"]}')
        print(f'  Hotspot pixels: {results["hotspot_pixels"]} '
              f'({results["hotspot_pixels"]/results["total_pixels"]*100:.1f}%)')
        print(f'  Intervention zones: {results["zones"]}')
        print(f'  Pareto solutions: {results["pareto_solutions"]}')

        best = results.get('best_solution', {})
        if best:
            print(f'\n  Best Intervention Package:')
            for spec in best.get('interventions', []):
                print(f'    • {spec["id"]}: {spec["coverage"]*100:.0f}%')
            print(f'    Predicted reduction: {best.get("predicted_reduction", 0):.2f}')
            print(f'    Cost: ${best.get("total_cost", 0):.0f}')
            print(f'    Feasibility: {best.get("avg_feasibility", 0):.2f}')
            print(f'    Confidence: {best.get("confidence", 0):.2f}')

        print(f'\n  Output Files:')
        for name, path in results.get('report_paths', {}).items():
            print(f'    {name}: {os.path.basename(path)}')
        for name, path in results.get('map_paths', {}).items():
            print(f'    {name}: {os.path.basename(path)}')

        print(f'\n  Total time: {results["elapsed_seconds"]:.1f}s')
        print(f'  Output dir: {self.output_dir}')
        print()

    def predict_scenario(self, **kwargs) -> Dict:
        """
        Run a scenario simulation with custom intervention parameters.
        This is the API for the interactive Scenario Simulator.

        Args:
            tree_cover_pct: Percentage of area for street trees (0-100)
            cool_roof_pct: Percentage of roofs to make cool (0-100)
            green_roof_pct: Percentage of roofs to green (0-100)
            water_body_pct: Percentage of area as water features (0-100)
            albedo_change: Additional albedo change (0-0.5)
            impervious_reduction_pct: Reduction in impervious surface (0-100)
            building_density_reduction_pct: Reduction in building density (0-100)

        Returns:
            Dict with scenario results including before/after predictions
        """
        if self.df is None or self.model_bundle is None:
            self._step1_load()
            self.df = self.detector.predict(self.df)
            self.hotspots = self.detector.detect_hotspots(self.df, min_class=2)

        # Generate intervention list from scenario params
        interventions = FeatureModifier.generate_scenario(**kwargs)

        if not interventions:
            return {
                'before_mean': float(self.hotspots['HeatScore_Predicted'].mean()),
                'after_mean': float(self.hotspots['HeatScore_Predicted'].mean()),
                'reduction': 0.0,
                'interventions': [],
            }

        # Apply to hotspots
        modified = self.modifier.apply_to_dataframe_vectorized(
            self.hotspots, interventions
        )

        # Re-predict
        feature_columns = self.model_bundle['feature_columns']
        X_mod = modified[feature_columns].fillna(0)
        modified['HeatScore_Predicted'] = (
            self.model_bundle['regression_model']
            .predict(X_mod).clip(0, 100).round(2)
        )

        before_mean = float(self.hotspots['HeatScore_Predicted'].mean())
        after_mean = float(modified['HeatScore_Predicted'].mean())

        return {
            'before_mean': round(before_mean, 2),
            'after_mean': round(after_mean, 2),
            'reduction': round(before_mean - after_mean, 2),
            'before_max': round(float(self.hotspots['HeatScore_Predicted'].max()), 2),
            'after_max': round(float(modified['HeatScore_Predicted'].max()), 2),
            'interventions': [
                {'id': s['id'], 'coverage': s['coverage']}
                for s in interventions
            ],
            'n_hotspots': len(self.hotspots),
            'before_distribution': {
                label: int((self.hotspots['HeatClass_Label'] == label).sum())
                for label in self.hotspots['HeatClass_Label'].unique()
            },
        }


def main():
    parser = argparse.ArgumentParser(
        description='Physics-Informed Urban Cooling Optimization Engine'
    )
    parser.add_argument('--data', '-d', default=None,
                        help='Path to master_dataset.csv')
    parser.add_argument('--model', '-m', default=None,
                        help='Path to trained_model.pkl')
    parser.add_argument('--output', '-o', default=None,
                        help='Output directory')
    parser.add_argument('--city', '-c', default='Delhi',
                        help='City name')
    parser.add_argument('--zones', type=int, default=5,
                        help='Number of hotspot zones')
    parser.add_argument('--pop-size', type=int, default=60,
                        help='NSGA-II population size')
    parser.add_argument('--generations', type=int, default=40,
                        help='NSGA-II generations')
    args = parser.parse_args()

    # Default data path
    data_path = args.data or os.path.join(
        os.path.dirname(__file__), '..', 'data', 'final', 'master_dataset.csv'
    )

    engine = UrbanCoolingEngine(
        data_path=data_path,
        model_path=args.model,
        output_dir=args.output,
        city_name=args.city,
    )

    results = engine.run(
        n_zones=args.zones,
        pop_size=args.pop_size,
        n_generations=args.generations,
    )

    return results


if __name__ == '__main__':
    main()
