"""
Report Generator — Output CSV/JSON Reports
=============================================
Generates all required output files:
  - recommendations.json
  - optimization_results.csv
  - before_after_predictions.csv
  - intervention_library.json
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class ReportGenerator:
    """Generate structured output reports from optimization results."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_recommendations_json(
        self,
        optimization_results: List[Dict],
        zone_profiles: Dict,
        best_solution: Dict,
        city_name: str = 'Delhi'
    ) -> str:
        """
        Generate recommendations.json with full intervention recommendations.
        """
        recommendations = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'city': city_name,
                'pipeline': 'UrbanHeatAI Cooling Optimization Engine v1.0',
                'model': 'GradientBoosting (R²=0.9995)',
                'optimization': 'NSGA-II Multi-Objective',
            },
            'summary': {
                'total_hotspot_zones': len(zone_profiles),
                'total_pareto_solutions': len(optimization_results),
                'best_predicted_reduction': best_solution.get('predicted_reduction', 0),
                'best_estimated_cooling_celsius': best_solution.get('estimated_cooling_celsius', 0),
                'best_total_cost': best_solution.get('total_cost', 0),
                'best_feasibility': best_solution.get('avg_feasibility', 0),
            },
            'best_recommendation': self._format_solution(best_solution),
            'all_recommendations': [
                self._format_solution(sol)
                for sol in optimization_results[:10]  # Top 10
            ],
            'zone_analysis': {},
            'implementation_priority': [],
        }

        # Zone analysis
        for zid, profile in zone_profiles.items():
            zone_rec = {
                'zone_id': zid,
                'n_pixels': profile['n_hotspots'],
                'avg_heat_score': profile['avg_heat_score'],
                'max_heat_score': profile['max_heat_score'],
                'top_contributing_factors': profile['contributing_factors'][:5],
                'vulnerabilities': {
                    k: v for k, v in profile.get('vulnerability_profile', {}).items()
                    if v is True
                },
            }
            if 'centroid' in profile:
                zone_rec['centroid'] = profile['centroid']
            recommendations['zone_analysis'][str(zid)] = zone_rec

        # Implementation priority
        for i, sol in enumerate(optimization_results[:5]):
            priority = {
                'rank': i + 1,
                'priority_score': sol.get('priority_score', 0),
                'interventions': [
                    {
                        'name': self._get_intervention_name(s['id']),
                        'coverage_pct': round(s['coverage'] * 100, 1),
                    }
                    for s in sol.get('interventions', [])
                ],
                'predicted_reduction': sol.get('predicted_reduction', 0),
                'cost': sol.get('total_cost', 0),
                'feasibility': sol.get('avg_feasibility', 0),
                'co_benefits': sol.get('co_benefits', []),
            }
            recommendations['implementation_priority'].append(priority)

        filepath = os.path.join(self.output_dir, 'recommendations.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, indent=2, ensure_ascii=False, default=str)

        print(f'  [OK] recommendations.json ({os.path.getsize(filepath)/1024:.1f} KB)')
        return filepath

    def generate_optimization_results_csv(
        self,
        optimization_results: List[Dict]
    ) -> str:
        """Generate optimization_results.csv with all Pareto solutions."""
        rows = []
        for sol in optimization_results:
            intervention_str = ' + '.join([
                f"{self._get_intervention_name(s['id'])} ({s['coverage']*100:.0f}%)"
                for s in sol.get('interventions', [])
            ])

            row = {
                'Priority_Rank': sol.get('priority_rank', 0),
                'Priority_Score': sol.get('priority_score', 0),
                'Predicted_Temp_Reduction': sol.get('predicted_reduction', 0),
                'Estimated_Cooling_Celsius': sol.get('estimated_cooling_celsius', 0),
                'Total_Cost_USD': sol.get('total_cost', 0),
                'Avg_Feasibility': sol.get('avg_feasibility', 0),
                'N_Interventions': sol.get('n_interventions', 0),
                'Confidence': sol.get('confidence', 0),
                'Interventions': intervention_str,
                'Co_Benefits_Count': len(sol.get('co_benefits', [])),
            }

            # Add individual intervention coverages
            for spec in sol.get('interventions', []):
                col_name = f"Coverage_{spec['id']}"
                row[col_name] = spec['coverage']

            rows.append(row)

        df = pd.DataFrame(rows)
        filepath = os.path.join(self.output_dir, 'optimization_results.csv')
        df.to_csv(filepath, index=False, float_format='%.4f')

        print(f'  [OK] optimization_results.csv '
              f'({len(rows)} solutions, {os.path.getsize(filepath)/1024:.1f} KB)')
        return filepath

    def generate_before_after_csv(
        self,
        original_df: pd.DataFrame,
        modified_df: pd.DataFrame,
        feature_columns: List[str],
        include_coords: bool = True
    ) -> str:
        """Generate before_after_predictions.csv with original and modified values."""
        rows = []

        for idx in range(len(original_df)):
            row = {}

            # Coordinates
            if include_coords:
                if 'Latitude' in original_df.columns:
                    row['Latitude'] = original_df.iloc[idx].get('Latitude', 0)
                if 'Longitude' in original_df.columns:
                    row['Longitude'] = original_df.iloc[idx].get('Longitude', 0)
                if 'PixelID' in original_df.columns:
                    row['PixelID'] = original_df.iloc[idx].get('PixelID', idx)

            # Heat scores
            if 'HeatScore_Predicted' in original_df.columns:
                row['HeatScore_Before'] = round(
                    original_df.iloc[idx]['HeatScore_Predicted'], 2
                )
            if 'HeatScore_Predicted' in modified_df.columns:
                row['HeatScore_After'] = round(
                    modified_df.iloc[idx]['HeatScore_Predicted'], 2
                )
                if 'HeatScore_Before' in row:
                    row['HeatScore_Reduction'] = round(
                        row['HeatScore_Before'] - row['HeatScore_After'], 2
                    )

            if 'HeatClass_Label' in original_df.columns:
                row['HeatClass_Before'] = original_df.iloc[idx]['HeatClass_Label']
            if 'HeatClass_Label' in modified_df.columns:
                row['HeatClass_After'] = modified_df.iloc[idx]['HeatClass_Label']

            # Feature values (before and after)
            for feat in feature_columns:
                if feat in original_df.columns:
                    row[f'{feat}_Before'] = round(
                        float(original_df.iloc[idx][feat]), 4
                    )
                if feat in modified_df.columns:
                    row[f'{feat}_After'] = round(
                        float(modified_df.iloc[idx][feat]), 4
                    )
                    if feat in original_df.columns:
                        row[f'{feat}_Change'] = round(
                            float(modified_df.iloc[idx][feat]) -
                            float(original_df.iloc[idx][feat]), 4
                        )

            rows.append(row)

        df = pd.DataFrame(rows)
        filepath = os.path.join(self.output_dir, 'before_after_predictions.csv')
        df.to_csv(filepath, index=False, float_format='%.4f')

        print(f'  [OK] before_after_predictions.csv '
              f'({len(rows)} rows, {os.path.getsize(filepath)/1024:.1f} KB)')
        return filepath

    def generate_intervention_library_json(self) -> str:
        """Export the complete intervention library as JSON."""
        from .intervention_library import export_library_json

        filepath = os.path.join(self.output_dir, 'intervention_library.json')
        export_library_json(filepath)

        print(f'  [OK] intervention_library.json '
              f'({os.path.getsize(filepath)/1024:.1f} KB)')
        return filepath

    def _format_solution(self, solution: Dict) -> Dict:
        """Format a solution dict for JSON output."""
        if not solution:
            return {}

        formatted = {
            'priority_rank': solution.get('priority_rank', 0),
            'priority_score': solution.get('priority_score', 0),
            'predicted_heat_score_reduction': solution.get('predicted_reduction', 0),
            'estimated_cooling_celsius': solution.get('estimated_cooling_celsius', 0),
            'total_cost_usd': solution.get('total_cost', 0),
            'avg_feasibility': solution.get('avg_feasibility', 0),
            'confidence': solution.get('confidence', 0),
            'interventions': [],
            'co_benefits': solution.get('co_benefits', []),
        }

        for spec in solution.get('interventions', []):
            from .intervention_library import get_intervention
            idata = get_intervention(spec['id'])
            if idata:
                formatted['interventions'].append({
                    'id': spec['id'],
                    'name': idata['name'],
                    'category': idata['category'],
                    'coverage_pct': round(spec['coverage'] * 100, 1),
                    'cooling_potential': idata['cooling_potential_celsius'],
                    'cost_per_unit': idata['cost_per_unit'],
                    'feasibility_score': idata['feasibility_score'],
                    'indian_suitability': idata.get('indian_suitability', 'medium'),
                })

        return formatted

    def _get_intervention_name(self, iid: str) -> str:
        """Get human-readable name for an intervention ID."""
        from .intervention_library import get_intervention
        idata = get_intervention(iid)
        return idata['name'] if idata else iid
