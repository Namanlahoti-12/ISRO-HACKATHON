"""
Feature Modifier — Physics-Informed Feature Value Modification
================================================================
Applies intervention effects to dataset features using the physics-based
parameters from the intervention library.

This module is the bridge between the intervention library (what changes)
and the trained ML model (predicting the outcome). It modifies feature
values in a physically consistent way, respecting:
  - Feature value bounds (e.g., NDVI ∈ [-1, 1], Albedo ∈ [0, 1])
  - Nonlinear interactions between interventions
  - Diminishing returns for stacked interventions
  - Spatial coverage fractions (e.g., 40% cool roofs)
"""

import copy
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .intervention_library import INTERVENTION_LIBRARY, get_intervention


# =============================================================================
# FEATURE BOUNDS — Physical constraints on feature values
# =============================================================================

FEATURE_BOUNDS = {
    'NDVI':              (-1.0, 1.0),
    'NDBI':              (-1.0, 1.0),
    'NDWI':              (-1.0, 1.0),
    'MNDWI':             (-1.0, 1.0),
    'SAVI':              (-1.0, 1.0),
    'Albedo':            (0.0, 1.0),
    'Impervious_Frac':   (0.0, 1.0),
    'Tree_Cover_Pct':    (0.0, 100.0),
    'Building_Density':  (0.0, None),
    'Building_Height':   (0.0, None),
    'Building_Volume':   (0.0, None),
    'Population_Density': (0.0, None),
    'WindSpeed':         (0.0, None),
    'Humidity':          (0.0, 100.0),
    'AirTemp':           (-50.0, 60.0),
    'SolarRadiation':    (0.0, None),
    'Nighttime_Lights':  (0.0, None),
    'Anthropogenic_Heat': (0.0, None),
    'Green_Space_Density': (0.0, 1.0),
    'Surface_Roughness': (0.0, None),
    'Dist_Water':        (0.0, None),
    'Dist_Green':        (0.0, None),
    'UHI_Intensity':     (None, None),
    'UTFVI':             (None, None),
    'Elevation':         (None, None),
    'Slope':             (0.0, 90.0),
}


class FeatureModifier:
    """
    Modifies feature values based on intervention specifications.

    Handles three modification modes:
        - 'add': Feature += value * coverage_fraction
        - 'multiply': Feature *= (1 + (value - 1) * coverage_fraction)
        - 'set_max': Feature = max(Feature, value * coverage_fraction)

    Also handles:
        - Diminishing returns for multiple interventions on same feature
        - Physical bounds enforcement
        - Uncertainty estimation
    """

    # Diminishing returns factor for stacked interventions
    # 2nd intervention on same feature gets 80% effectiveness, 3rd gets 65%, etc.
    STACKING_FACTORS = [1.0, 0.80, 0.65, 0.52, 0.42, 0.35]

    def __init__(self):
        self.modification_log = []

    def apply_intervention_combo(
        self,
        features: pd.Series,
        interventions: List[Dict],
        return_details: bool = False
    ) -> Tuple[pd.Series, Dict]:
        """
        Apply a combination of interventions to a feature vector.

        Args:
            features: pandas Series of current feature values
            interventions: List of dicts, each with:
                - 'id': intervention ID from the library
                - 'coverage': fraction of area covered (0.0 - 1.0)
                  e.g., 0.40 for "40% cool roofs"
            return_details: If True, include per-intervention modification details

        Returns:
            Tuple of (modified_features, modification_summary)
        """
        modified = features.copy()
        summary = {
            'interventions_applied': [],
            'features_modified': {},
            'total_modifications': 0,
        }

        # Track how many times each feature has been modified
        # (for diminishing returns calculation)
        feature_mod_count = {}

        for intervention_spec in interventions:
            iid = intervention_spec['id']
            coverage = intervention_spec.get('coverage', 1.0)

            intervention = get_intervention(iid)
            if intervention is None:
                print(f'  [WARN] Unknown intervention: {iid}')
                continue

            effects = intervention['feature_effects']
            intervention_summary = {
                'id': iid,
                'name': intervention['name'],
                'category': intervention['category'],
                'coverage': coverage,
                'modifications': {},
            }

            for feat_name, effect in effects.items():
                if feat_name not in modified.index:
                    continue

                old_value = float(modified[feat_name])
                mode = effect['delta_mode']
                delta_value = effect['value']

                # Track stacking and get diminishing returns factor
                mod_idx = feature_mod_count.get(feat_name, 0)
                stack_factor = (
                    self.STACKING_FACTORS[mod_idx]
                    if mod_idx < len(self.STACKING_FACTORS)
                    else self.STACKING_FACTORS[-1]
                )
                feature_mod_count[feat_name] = mod_idx + 1

                # Apply modification based on mode
                if mode == 'add':
                    # Additive: feature += delta * coverage * stacking
                    change = delta_value * coverage * stack_factor
                    new_value = old_value + change

                elif mode == 'multiply':
                    # Multiplicative: feature *= adjusted_multiplier
                    # Interpolate between 1.0 (no change) and delta_value
                    effective_mult = 1.0 + (delta_value - 1.0) * coverage * stack_factor
                    new_value = old_value * effective_mult
                    change = new_value - old_value

                elif mode == 'set_max':
                    # Set to a maximum value, weighted by coverage
                    target = delta_value
                    change = (target - old_value) * coverage * stack_factor
                    new_value = old_value + max(change, 0)

                else:
                    continue

                # Enforce physical bounds
                bounds = FEATURE_BOUNDS.get(feat_name, (None, None))
                if bounds[0] is not None:
                    new_value = max(new_value, bounds[0])
                if bounds[1] is not None:
                    new_value = min(new_value, bounds[1])

                modified[feat_name] = new_value
                summary['total_modifications'] += 1

                if return_details:
                    intervention_summary['modifications'][feat_name] = {
                        'old': round(old_value, 6),
                        'new': round(new_value, 6),
                        'change': round(new_value - old_value, 6),
                        'change_pct': round(
                            (new_value - old_value) / abs(old_value) * 100
                            if old_value != 0 else 0, 2
                        ),
                        'mode': mode,
                        'stack_factor': stack_factor,
                    }

                # Track per-feature summary
                if feat_name not in summary['features_modified']:
                    summary['features_modified'][feat_name] = {
                        'original': round(old_value, 6),
                        'final': round(float(modified[feat_name]), 6),
                        'total_change': 0,
                    }
                summary['features_modified'][feat_name]['final'] = round(
                    float(modified[feat_name]), 6
                )
                summary['features_modified'][feat_name]['total_change'] = round(
                    float(modified[feat_name]) -
                    summary['features_modified'][feat_name]['original'], 6
                )

            summary['interventions_applied'].append(intervention_summary)

        return modified, summary

    def apply_to_dataframe(
        self,
        df: pd.DataFrame,
        interventions: List[Dict],
        feature_columns: List[str] = None,
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Apply interventions to an entire DataFrame of hotspot pixels.

        Args:
            df: DataFrame of hotspot pixels
            interventions: Intervention specifications (see apply_intervention_combo)
            feature_columns: Columns to consider (defaults to all available)

        Returns:
            Tuple of (modified_dataframe, list_of_summaries)
        """
        modified_df = df.copy()
        summaries = []

        for idx in range(len(df)):
            row = df.iloc[idx]
            mod_row, summary = self.apply_intervention_combo(
                row, interventions, return_details=False
            )
            for col in mod_row.index:
                if col in modified_df.columns:
                    modified_df.iloc[idx][col] = mod_row[col]
            summaries.append(summary)

        return modified_df, summaries

    def apply_to_dataframe_vectorized(
        self,
        df: pd.DataFrame,
        interventions: List[Dict],
    ) -> pd.DataFrame:
        """
        Vectorized version of apply_to_dataframe for performance.
        Applies the same interventions uniformly to all rows.

        This is much faster than row-by-row application.
        """
        modified = df.copy()
        feature_mod_count = {}

        for intervention_spec in interventions:
            iid = intervention_spec['id']
            coverage = intervention_spec.get('coverage', 1.0)

            intervention = get_intervention(iid)
            if intervention is None:
                continue

            for feat_name, effect in intervention['feature_effects'].items():
                if feat_name not in modified.columns:
                    continue

                mode = effect['delta_mode']
                delta_value = effect['value']

                # Stacking factor
                mod_idx = feature_mod_count.get(feat_name, 0)
                stack_factor = (
                    self.STACKING_FACTORS[mod_idx]
                    if mod_idx < len(self.STACKING_FACTORS)
                    else self.STACKING_FACTORS[-1]
                )
                feature_mod_count[feat_name] = mod_idx + 1

                if mode == 'add':
                    change = delta_value * coverage * stack_factor
                    modified[feat_name] = modified[feat_name] + change

                elif mode == 'multiply':
                    effective_mult = 1.0 + (delta_value - 1.0) * coverage * stack_factor
                    modified[feat_name] = modified[feat_name] * effective_mult

                elif mode == 'set_max':
                    target = delta_value
                    old_vals = modified[feat_name]
                    change = (target - old_vals) * coverage * stack_factor
                    modified[feat_name] = old_vals + change.clip(lower=0)

                # Enforce bounds
                bounds = FEATURE_BOUNDS.get(feat_name, (None, None))
                if bounds[0] is not None:
                    modified[feat_name] = modified[feat_name].clip(lower=bounds[0])
                if bounds[1] is not None:
                    modified[feat_name] = modified[feat_name].clip(upper=bounds[1])

        return modified

    def estimate_uncertainty(
        self,
        features: pd.Series,
        interventions: List[Dict],
        n_samples: int = 50
    ) -> Dict:
        """
        Monte Carlo uncertainty estimation for intervention effects.

        Samples from the intervention effect ranges to estimate
        confidence intervals on the modified feature values.

        Args:
            features: Original feature values
            interventions: Intervention specifications
            n_samples: Number of Monte Carlo samples

        Returns:
            Dict with mean, std, and confidence intervals for each feature
        """
        samples = {feat: [] for feat in features.index}

        for _ in range(n_samples):
            # Create perturbed interventions using range values
            perturbed = copy.deepcopy(interventions)
            for spec in perturbed:
                intervention = get_intervention(spec['id'])
                if intervention is None:
                    continue

                # Sample from effect ranges
                for feat, effect in intervention['feature_effects'].items():
                    if 'range' in effect:
                        low, high = effect['range']
                        effect['value'] = np.random.uniform(low, high)

            # Apply and record
            mod_features, _ = self.apply_intervention_combo(
                features, perturbed, return_details=False
            )
            for feat in features.index:
                samples[feat].append(float(mod_features[feat]))

        # Compute statistics
        uncertainty = {}
        for feat in features.index:
            vals = np.array(samples[feat])
            uncertainty[feat] = {
                'mean': round(float(np.mean(vals)), 4),
                'std': round(float(np.std(vals)), 4),
                'ci_5': round(float(np.percentile(vals, 5)), 4),
                'ci_95': round(float(np.percentile(vals, 95)), 4),
                'original': round(float(features[feat]), 4),
            }

        return uncertainty

    @staticmethod
    def generate_scenario(
        tree_cover_pct: float = 0,
        cool_roof_pct: float = 0,
        green_roof_pct: float = 0,
        water_body_pct: float = 0,
        albedo_change: float = 0,
        impervious_reduction_pct: float = 0,
        building_density_reduction_pct: float = 0,
    ) -> List[Dict]:
        """
        Generate an intervention list from simplified scenario parameters.
        This is the interface for the interactive Scenario Simulator.

        Args:
            tree_cover_pct: Percentage of area to add street trees (0-100)
            cool_roof_pct: Percentage of roofs to make cool (0-100)
            green_roof_pct: Percentage of roofs to green (0-100)
            water_body_pct: Percentage of area as water features (0-100)
            albedo_change: Additional albedo change (0-0.5)
            impervious_reduction_pct: Percentage reduction in impervious surface (0-100)
            building_density_reduction_pct: Percentage reduction in building density (0-100)

        Returns:
            List of intervention dicts ready for apply_intervention_combo
        """
        interventions = []

        if tree_cover_pct > 0:
            interventions.append({
                'id': 'street_trees',
                'coverage': min(tree_cover_pct / 100.0, 1.0)
            })

        if cool_roof_pct > 0:
            interventions.append({
                'id': 'cool_roofs',
                'coverage': min(cool_roof_pct / 100.0, 1.0)
            })

        if green_roof_pct > 0:
            interventions.append({
                'id': 'green_roofs',
                'coverage': min(green_roof_pct / 100.0, 1.0)
            })

        if water_body_pct > 0:
            # Split between ponds and rain gardens
            interventions.append({
                'id': 'ponds',
                'coverage': min(water_body_pct / 200.0, 0.5)
            })
            interventions.append({
                'id': 'rain_gardens',
                'coverage': min(water_body_pct / 200.0, 0.5)
            })

        if albedo_change > 0:
            interventions.append({
                'id': 'high_albedo_materials',
                'coverage': min(albedo_change / 0.3, 1.0)
            })

        if impervious_reduction_pct > 0:
            interventions.append({
                'id': 'impervious_surface_reduction',
                'coverage': min(impervious_reduction_pct / 100.0, 1.0)
            })

        if building_density_reduction_pct > 0:
            interventions.append({
                'id': 'building_spacing',
                'coverage': min(building_density_reduction_pct / 100.0, 1.0)
            })

        return interventions
