"""
Map Generator — Spatial Heatmap Visualizations
=================================================
Generates before/after/difference/cooling potential/priority maps
as high-quality PNG images using matplotlib.

Maps generated:
  1. Before Heat Map — Original heat score distribution
  2. After Heat Map — Predicted heat scores post-intervention
  3. Difference Heat Map — Temperature reduction per pixel
  4. Cooling Potential Map — Maximum achievable cooling per area
  5. Priority Map — Intervention priority ranking
"""

import os
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import numpy as np
import pandas as pd


# Custom colormaps for UHI mapping
HEAT_CMAP = mcolors.LinearSegmentedColormap.from_list(
    'uhi_heat',
    ['#1a3678', '#2955bc', '#5699ff', '#8dbae9', '#caebf2',
     '#e0f3db', '#f7fcb9', '#fff7bc', '#fec44f', '#fe9929',
     '#ec7014', '#cc4c02', '#993404', '#662506'],
    N=256
)

COOLING_CMAP = mcolors.LinearSegmentedColormap.from_list(
    'uhi_cooling',
    ['#ffffff', '#c7e9c0', '#74c476', '#31a354',
     '#006d2c', '#00441b'],
    N=256
)

DIFF_CMAP = mcolors.LinearSegmentedColormap.from_list(
    'uhi_diff',
    ['#67001f', '#b2182b', '#d6604d', '#f4a582',
     '#fddbc7', '#f7f7f7', '#d1e5f0', '#92c5de',
     '#4393c3', '#2166ac', '#053061'],
    N=256
)

PRIORITY_CMAP = mcolors.LinearSegmentedColormap.from_list(
    'uhi_priority',
    ['#fee5d9', '#fcbba1', '#fc9272', '#fb6a4a',
     '#de2d26', '#a50f15'],
    N=256
)


class MapGenerator:
    """Generate spatial heat maps from model predictions."""

    def __init__(self, output_dir: str, dpi: int = 150):
        self.output_dir = output_dir
        self.dpi = dpi
        os.makedirs(output_dir, exist_ok=True)

    def _create_scatter_map(
        self,
        df: pd.DataFrame,
        value_col: str,
        title: str,
        filename: str,
        cmap=None,
        vmin: float = None,
        vmax: float = None,
        colorbar_label: str = '',
        figsize: tuple = (14, 10),
    ) -> str:
        """Create a scatter-based spatial map."""
        fig, ax = plt.subplots(figsize=figsize)

        if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
            # Fall back to grid-based visualization
            return self._create_grid_map(
                df, value_col, title, filename, cmap,
                vmin, vmax, colorbar_label, figsize
            )

        sc = ax.scatter(
            df['Longitude'], df['Latitude'],
            c=df[value_col],
            cmap=cmap or HEAT_CMAP,
            s=8, alpha=0.85,
            vmin=vmin, vmax=vmax,
            edgecolors='none',
            rasterized=True,
        )

        cbar = plt.colorbar(sc, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label(colorbar_label, fontsize=11, fontweight='bold')
        cbar.ax.tick_params(labelsize=9)

        ax.set_xlabel('Longitude', fontsize=11, fontweight='bold')
        ax.set_ylabel('Latitude', fontsize=11, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        # Stats box
        values = df[value_col].dropna()
        stats_text = (f'Mean: {values.mean():.1f}\n'
                      f'Max: {values.max():.1f}\n'
                      f'Min: {values.min():.1f}\n'
                      f'Std: {values.std():.1f}\n'
                      f'N: {len(values)}')
        props = dict(boxstyle='round,pad=0.5', facecolor='white',
                     alpha=0.9, edgecolor='gray')
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=9, verticalalignment='top', bbox=props,
                family='monospace')

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

        return filepath

    def _create_grid_map(
        self,
        df: pd.DataFrame,
        value_col: str,
        title: str,
        filename: str,
        cmap=None,
        vmin: float = None,
        vmax: float = None,
        colorbar_label: str = '',
        figsize: tuple = (14, 10),
    ) -> str:
        """Create a grid-based heatmap (histogram2d) for data without coordinates."""
        fig, ax = plt.subplots(figsize=figsize)

        values = df[value_col].dropna()

        # Create a 1D bar-style visualization sorted by value
        sorted_vals = values.sort_values(ascending=False).reset_index(drop=True)
        n = len(sorted_vals)
        grid_size = int(np.ceil(np.sqrt(n)))

        # Reshape into grid
        padded = np.full(grid_size * grid_size, np.nan)
        padded[:n] = sorted_vals.values
        grid = padded.reshape(grid_size, grid_size)

        im = ax.imshow(grid, cmap=cmap or HEAT_CMAP,
                       vmin=vmin, vmax=vmax,
                       aspect='auto', interpolation='nearest')

        cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label(colorbar_label, fontsize=11, fontweight='bold')

        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Grid Column', fontsize=10)
        ax.set_ylabel('Grid Row', fontsize=10)

        stats_text = (f'Mean: {values.mean():.1f}\n'
                      f'Max: {values.max():.1f}\n'
                      f'Min: {values.min():.1f}\n'
                      f'N: {len(values)}')
        props = dict(boxstyle='round,pad=0.5', facecolor='white',
                     alpha=0.9, edgecolor='gray')
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=9, verticalalignment='top', bbox=props,
                family='monospace')

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

        return filepath

    def generate_before_heat_map(self, df: pd.DataFrame) -> str:
        """Generate Before Heat Map showing original heat scores."""
        print('  Generating Before Heat Map...')
        return self._create_scatter_map(
            df,
            value_col='HeatScore_Predicted',
            title='Urban Heat Score — Before Intervention',
            filename='heatmap_before.png',
            cmap=HEAT_CMAP,
            vmin=0, vmax=100,
            colorbar_label='Heat Score (0-100)',
        )

    def generate_after_heat_map(self, df: pd.DataFrame) -> str:
        """Generate After Heat Map showing predicted post-intervention heat scores."""
        print('  Generating After Heat Map...')
        return self._create_scatter_map(
            df,
            value_col='HeatScore_Predicted',
            title='Urban Heat Score — After Intervention (Predicted)',
            filename='heatmap_after.png',
            cmap=HEAT_CMAP,
            vmin=0, vmax=100,
            colorbar_label='Heat Score (0-100)',
        )

    def generate_difference_map(self, before_df: pd.DataFrame,
                                after_df: pd.DataFrame) -> str:
        """Generate Difference Heat Map showing temperature reduction."""
        print('  Generating Difference Heat Map...')

        diff_df = before_df.copy()
        diff_df['HeatScore_Reduction'] = (
            before_df['HeatScore_Predicted'] - after_df['HeatScore_Predicted']
        )

        return self._create_scatter_map(
            diff_df,
            value_col='HeatScore_Reduction',
            title='Heat Score Reduction — Intervention Impact',
            filename='heatmap_difference.png',
            cmap=COOLING_CMAP,
            vmin=0, vmax=max(diff_df['HeatScore_Reduction'].max(), 5),
            colorbar_label='Heat Score Reduction',
        )

    def generate_cooling_potential_map(self, df: pd.DataFrame) -> str:
        """Generate Cooling Potential Map based on feature analysis."""
        print('  Generating Cooling Potential Map...')

        # Estimate cooling potential based on key features
        potential = pd.Series(0.0, index=df.index)

        # Higher NDBI → more room for albedo interventions
        if 'NDBI' in df.columns:
            potential += df['NDBI'].clip(0, 1) * 15

        # Low NDVI → room for greening
        if 'NDVI' in df.columns:
            potential += (1 - df['NDVI'].clip(0, 1)) * 10

        # High Impervious → room for surface replacement
        if 'Impervious_Frac' in df.columns:
            potential += df['Impervious_Frac'] * 12

        # Low Albedo → room for cool roofs
        if 'Albedo' in df.columns:
            potential += (0.7 - df['Albedo'].clip(0, 0.7)).clip(0) * 10

        # Distance from green space
        if 'Dist_Green' in df.columns:
            max_dist = df['Dist_Green'].max()
            if max_dist > 0:
                potential += (df['Dist_Green'] / max_dist) * 8

        potential = potential.clip(0, 50)

        potential_df = df.copy()
        potential_df['Cooling_Potential'] = potential

        return self._create_scatter_map(
            potential_df,
            value_col='Cooling_Potential',
            title='Cooling Potential — Intervention Opportunity Score',
            filename='heatmap_cooling_potential.png',
            cmap=COOLING_CMAP,
            vmin=0, vmax=50,
            colorbar_label='Cooling Potential Score',
        )

    def generate_priority_map(self, df: pd.DataFrame) -> str:
        """Generate Priority Map based on heat severity and intervention opportunity."""
        print('  Generating Priority Map...')

        priority = pd.Series(0.0, index=df.index)

        # Heat score drives priority
        if 'HeatScore_Predicted' in df.columns:
            priority += df['HeatScore_Predicted'] * 0.40

        # Population density amplifies priority
        if 'Population_Density' in df.columns:
            pop_norm = df['Population_Density'] / max(df['Population_Density'].max(), 1)
            priority += pop_norm * 25

        # Built-up areas are priority
        if 'Building_Density' in df.columns:
            bd_norm = df['Building_Density'] / max(df['Building_Density'].max(), 1)
            priority += bd_norm * 15

        # Distance from green/water increases priority
        if 'Dist_Green' in df.columns:
            dg_norm = df['Dist_Green'] / max(df['Dist_Green'].max(), 1)
            priority += dg_norm * 10

        # High nighttime lights = more activity/people affected
        if 'Nighttime_Lights' in df.columns:
            nl_norm = df['Nighttime_Lights'] / max(df['Nighttime_Lights'].max(), 1)
            priority += nl_norm * 10

        priority = priority.clip(0, 100)

        priority_df = df.copy()
        priority_df['Intervention_Priority'] = priority

        return self._create_scatter_map(
            priority_df,
            value_col='Intervention_Priority',
            title='Intervention Priority — Heat Stress × Vulnerability',
            filename='heatmap_priority.png',
            cmap=PRIORITY_CMAP,
            vmin=0, vmax=100,
            colorbar_label='Priority Score (0-100)',
        )

    def generate_all_maps(
        self,
        before_df: pd.DataFrame,
        after_df: pd.DataFrame,
        full_df: pd.DataFrame = None
    ) -> Dict[str, str]:
        """Generate all five maps and return file paths."""
        print('\n' + '=' * 70)
        print('  GENERATING HEAT MAPS')
        print('=' * 70)

        paths = {}
        paths['before'] = self.generate_before_heat_map(before_df)
        paths['after'] = self.generate_after_heat_map(after_df)
        paths['difference'] = self.generate_difference_map(before_df, after_df)

        target_df = full_df if full_df is not None else before_df
        paths['cooling_potential'] = self.generate_cooling_potential_map(target_df)
        paths['priority'] = self.generate_priority_map(target_df)

        print(f'\n  [OK] All 5 maps generated in {self.output_dir}')
        for name, path in paths.items():
            print(f'    {name}: {os.path.basename(path)}')

        return paths
