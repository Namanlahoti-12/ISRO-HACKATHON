"""
Urban Heat AI - Explainable AI (XAI) Engine
=============================================
Per-pixel heat stress explanations using SHAP, decision paths,
and natural language reasoning.

When a user clicks any pixel on the map, this module answers:
  "WHY is this location hot (or cool)?"

Provides:
  1. SHAP-based feature contributions (% per feature)
  2. Decision path through the tree ensemble
  3. Natural language explanation
  4. Publication-quality visualizations:
     - SHAP waterfall plot
     - Feature contribution bar chart
     - Comparative radar chart
     - Decision path summary

Architecture Decisions:
  - TreeExplainer (exact SHAP) used for tree-based models (O(TLD) complexity)
  - Natural language templates map feature ranges to physical causes
  - Contribution percentages computed as |SHAP_i| / sum(|SHAP|) * 100
  - Charts use publication-quality formatting (Nature/Science style)

Reference:
  Lundberg & Lee (2017). "A Unified Approach to Interpreting Model Predictions." NeurIPS.
"""

import json
import os
import pickle
import sys
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# Defer SHAP import to handle gracefully
try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


# ============================================================================
# NATURAL LANGUAGE TEMPLATES
# ============================================================================
# Maps feature names to human-readable cause-effect descriptions.
# Each entry: (feature_name, low_description, high_description, unit)

FEATURE_DESCRIPTIONS = {
    'UHI_Intensity': {
        'name': 'Urban Heat Island Intensity',
        'unit': 'degrees C above rural baseline',
        'low': 'This area is cooler than surrounding rural areas',
        'high': 'Strong urban heat island effect — the area is significantly warmer than surrounding rural land',
        'cause_high': 'dense built environment trapping and re-emitting heat',
        'cause_low': 'proximity to green/water spaces providing cooling',
    },
    'Anthropogenic_Heat': {
        'name': 'Anthropogenic Heat',
        'unit': 'proxy index',
        'low': 'Minimal human-generated waste heat in this area',
        'high': 'High waste heat from buildings, vehicles, and industrial activity',
        'cause_high': 'concentrated human activity (traffic, AC units, industry)',
        'cause_low': 'sparse human activity or open land',
    },
    'Building_Density': {
        'name': 'Building Density',
        'unit': 'fraction',
        'low': 'Open area with sparse or no buildings',
        'high': 'Densely built area with high building footprint coverage',
        'cause_high': 'concrete and steel structures absorbing and storing solar heat',
        'cause_low': 'open land allowing natural ventilation and heat dissipation',
    },
    'Building_Volume': {
        'name': 'Building Volume',
        'unit': 'm3 per pixel',
        'low': 'Low-rise or sparse building structures',
        'high': 'High-rise dense buildings creating urban canyon effects',
        'cause_high': 'tall buildings trapping longwave radiation and blocking airflow',
        'cause_low': 'low structures allowing sky view and wind circulation',
    },
    'NDBI': {
        'name': 'Built-up Index (NDBI)',
        'unit': 'dimensionless',
        'low': 'Low concentration of impervious built-up surfaces',
        'high': 'High concentration of concrete, asphalt, and built-up surfaces',
        'cause_high': 'dark impervious surfaces with high thermal admittance',
        'cause_low': 'natural or vegetated land cover',
    },
    'NDVI': {
        'name': 'Vegetation Index (NDVI)',
        'unit': 'dimensionless',
        'low': 'Very low vegetation cover — bare soil or concrete',
        'high': 'Dense, healthy vegetation providing evapotranspiration cooling',
        'cause_high': 'trees and plants cooling through evapotranspiration',
        'cause_low': 'absence of vegetation eliminates evaporative cooling',
    },
    'SAVI': {
        'name': 'Soil-Adjusted Vegetation (SAVI)',
        'unit': 'dimensionless',
        'low': 'Sparse vegetation with exposed soil',
        'high': 'Moderate to dense vegetation even with partial soil exposure',
        'cause_high': 'vegetation canopy shading and moisture retention',
        'cause_low': 'bare soil absorbing heat without evaporative cooling',
    },
    'MNDWI': {
        'name': 'Modified Water Index (MNDWI)',
        'unit': 'dimensionless',
        'low': 'No nearby water bodies',
        'high': 'Proximity to water surfaces providing evaporative cooling',
        'cause_high': 'water bodies moderating local temperature through evaporation',
        'cause_low': 'absence of water surfaces in the vicinity',
    },
    'Population_Density': {
        'name': 'Population Density',
        'unit': 'people per pixel',
        'low': 'Sparsely populated area',
        'high': 'Densely populated area generating metabolic and activity heat',
        'cause_high': 'large number of people generating metabolic heat and using energy',
        'cause_low': 'few people means less anthropogenic heat generation',
    },
    'Nighttime_Lights': {
        'name': 'Nighttime Light Intensity',
        'unit': 'nW/cm2/sr',
        'low': 'Dark area at night — rural or undeveloped',
        'high': 'Brightly lit at night — intense urban activity',
        'cause_high': 'energy consumption and urban infrastructure generating heat',
        'cause_low': 'minimal nocturnal energy use',
    },
    'Dist_Green': {
        'name': 'Distance to Green Space',
        'unit': 'meters',
        'low': 'Close to parks or green areas — benefits from cooling effect',
        'high': 'Far from any significant green space',
        'cause_high': 'no nearby vegetation to provide shade or evapotranspiration',
        'cause_low': 'adjacent green spaces provide localized cooling',
    },
    'Dist_Water': {
        'name': 'Distance to Water',
        'unit': 'meters',
        'low': 'Near a water body — benefits from lake/river breeze cooling',
        'high': 'Far from any water body',
        'cause_high': 'no nearby water to moderate temperature',
        'cause_low': 'water body provides evaporative cooling and wind channeling',
    },
    'LULC_ESA': {
        'name': 'Land Use / Land Cover (ESA)',
        'unit': 'class code',
        'low': 'Natural land cover (forest, grassland, water)',
        'high': 'Built-up or bare land cover',
        'cause_high': 'urban land use with sealed surfaces',
        'cause_low': 'natural land cover with lower thermal mass',
    },
    'Albedo': {
        'name': 'Surface Albedo',
        'unit': 'fraction',
        'low': 'Dark surfaces absorbing most solar radiation',
        'high': 'Bright/reflective surfaces bouncing back solar energy',
        'cause_high': 'high reflectivity reducing absorbed solar heat',
        'cause_low': 'dark surfaces (asphalt, dark roofs) absorbing solar energy',
    },
    'Impervious_Frac': {
        'name': 'Impervious Surface',
        'unit': 'binary',
        'low': 'Permeable surface allowing water infiltration',
        'high': 'Sealed impervious surface preventing natural cooling',
        'cause_high': 'concrete/asphalt preventing evaporative cooling and water absorption',
        'cause_low': 'permeable ground supporting natural water cycle',
    },
    'WindSpeed': {
        'name': 'Wind Speed',
        'unit': 'm/s',
        'low': 'Calm conditions — heat accumulates without dispersal',
        'high': 'Windy conditions helping disperse accumulated heat',
        'cause_high': 'strong winds carry away heat through advection',
        'cause_low': 'stagnant air traps heat near the surface',
    },
    'SolarRadiation': {
        'name': 'Solar Radiation',
        'unit': 'W/m2',
        'low': 'Lower incoming solar energy (cloud cover or season)',
        'high': 'Intense incoming solar radiation heating surfaces',
        'cause_high': 'strong solar irradiance directly heating exposed surfaces',
        'cause_low': 'reduced solar input limits surface heating',
    },
    'AirTemp': {
        'name': 'Air Temperature',
        'unit': 'degrees C',
        'low': 'Relatively cooler ambient air temperature',
        'high': 'High ambient air temperature amplifying surface heating',
        'cause_high': 'warm air mass over the region',
        'cause_low': 'cooler air mass moderating surface temperature',
    },
    'Humidity': {
        'name': 'Relative Humidity',
        'unit': '%',
        'low': 'Dry air — less thermal discomfort but less evaporative cooling',
        'high': 'Humid air — reduces body evaporative cooling, increases heat stress',
        'cause_high': 'moisture-laden air reducing evaporative heat loss',
        'cause_low': 'dry conditions allowing some evaporative cooling',
    },
    'Elevation': {
        'name': 'Elevation',
        'unit': 'meters ASL',
        'low': 'Low-lying area prone to heat accumulation',
        'high': 'Higher elevation with natural temperature lapse rate cooling',
        'cause_high': 'altitude-related temperature decrease (~6.5 C/km)',
        'cause_low': 'low terrain traps warm air in valley/basin effects',
    },
    'Tree_Cover_Pct': {
        'name': 'Tree Canopy Cover',
        'unit': '%',
        'low': 'Minimal tree canopy — no shade or evapotranspiration',
        'high': 'Dense tree canopy providing shade and transpiration cooling',
        'cause_high': 'trees reduce surface temperature through shading and moisture release',
        'cause_low': 'no trees means full solar exposure on surfaces',
    },
    'Green_Space_Density': {
        'name': 'Green Space Density',
        'unit': 'fraction',
        'low': 'Very little green space in the 150m neighborhood',
        'high': 'Abundant green space within the surrounding 150m',
        'cause_high': 'neighborhood-level cooling from distributed vegetation',
        'cause_low': 'lack of nearby vegetation amplifies local heating',
    },
    'UTCI_Approx': {
        'name': 'Universal Thermal Climate Index',
        'unit': 'degrees C',
        'low': 'Lower thermal stress on the human body',
        'high': 'High outdoor thermal stress — dangerous for prolonged exposure',
        'cause_high': 'combined effect of temperature, humidity, wind, and radiation',
        'cause_low': 'moderate outdoor thermal comfort conditions',
    },
    'Slope': {
        'name': 'Terrain Slope',
        'unit': 'degrees',
        'low': 'Flat terrain',
        'high': 'Sloped terrain affecting solar exposure angle',
        'cause_high': 'slope orientation affects solar heating intensity',
        'cause_low': 'flat terrain receives uniform solar exposure',
    },
    'Aspect': {
        'name': 'Terrain Aspect',
        'unit': 'degrees',
        'low': 'North-facing slope (less direct sun in Northern Hemisphere)',
        'high': 'South-facing slope (more direct solar exposure)',
        'cause_high': 'south-facing orientation receives maximum solar radiation',
        'cause_low': 'north-facing orientation receives less direct sunlight',
    },
    'Pressure': {
        'name': 'Surface Pressure',
        'unit': 'hPa',
        'low': 'Lower atmospheric pressure',
        'high': 'High pressure system associated with clear skies and heat',
        'cause_high': 'high pressure suppresses cloud formation, increasing solar heating',
        'cause_low': 'low pressure may bring clouds reducing solar input',
    },
    'Rainfall': {
        'name': 'Accumulated Rainfall',
        'unit': 'mm',
        'low': 'Dry period — no rain-based cooling',
        'high': 'Recent rainfall providing evaporative cooling of surfaces',
        'cause_high': 'wet surfaces and soil moisture increase evaporative cooling',
        'cause_low': 'dry conditions mean no rain-cooling and drier soil',
    },
    'Road_Density_Proxy': {
        'name': 'Road Density',
        'unit': 'unitless',
        'low': 'Few roads — less asphalt surface',
        'high': 'Dense road network — extensive asphalt surfaces',
        'cause_high': 'dark asphalt roads absorb and radiate heat',
        'cause_low': 'fewer paved surfaces reduce absorbed solar heat',
    },
    'Street_Width_Proxy': {
        'name': 'Street Width',
        'unit': 'meters',
        'low': 'Narrow streets creating deep urban canyons',
        'high': 'Wide streets allowing better ventilation',
        'cause_high': 'wider streets improve air circulation and sky view factor',
        'cause_low': 'narrow streets trap heat and reduce sky view factor',
    },
    'Surface_Roughness': {
        'name': 'Surface Roughness',
        'unit': 'meters (elevation StdDev)',
        'low': 'Smooth, uniform terrain',
        'high': 'Rough, varied terrain affecting local air patterns',
        'cause_high': 'complex terrain creates micro-circulation patterns',
        'cause_low': 'smooth terrain allows uniform wind flow',
    },
}

HEAT_CLASSES = {0: 'Low', 1: 'Moderate', 2: 'High', 3: 'Extreme'}

HEAT_CLASS_COLORS = {
    'Low': '#2166ac',
    'Moderate': '#fdb863',
    'High': '#e08214',
    'Extreme': '#b2182b',
}

HEAT_CLASS_DESCRIPTIONS = {
    'Low': 'Comfortable outdoor conditions. No heat stress intervention needed.',
    'Moderate': 'Noticeable warmth. Caution for extended outdoor activity.',
    'High': 'Significant heat stress. Vulnerable populations (elderly, children) at risk.',
    'Extreme': 'Dangerous heat. Immediate cooling interventions recommended.',
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PixelExplanation:
    """Complete explanation for a single pixel."""
    pixel_id: int
    latitude: float
    longitude: float
    heat_score: float
    heat_class: str
    heat_class_id: int

    # Feature values
    feature_values: Dict[str, float] = field(default_factory=dict)

    # SHAP contributions
    shap_values: Dict[str, float] = field(default_factory=dict)
    shap_base_value: float = 0.0

    # Contribution percentages
    contributions_pct: Dict[str, float] = field(default_factory=dict)

    # Natural language
    top_causes: List[str] = field(default_factory=list)
    explanation_text: str = ''
    recommendation: str = ''

    def to_dict(self):
        return {
            'pixel_id': self.pixel_id,
            'latitude': round(self.latitude, 6),
            'longitude': round(self.longitude, 6),
            'heat_score': round(self.heat_score, 2),
            'heat_class': self.heat_class,
            'contributions': {k: round(v, 2) for k, v in self.contributions_pct.items()},
            'top_causes': self.top_causes,
            'explanation': self.explanation_text,
            'recommendation': self.recommendation,
        }


# ============================================================================
# HEAT EXPLAINER CLASS
# ============================================================================

class HeatExplainer:
    """Explainable AI engine for Urban Heat Stress predictions."""

    def __init__(self, model_path: str):
        """Load the trained model bundle."""
        with open(model_path, 'rb') as f:
            self.bundle = pickle.load(f)

        self.reg_model = self.bundle['regression_model']
        self.cls_model = self.bundle['classification_model']
        self.feature_cols = self.bundle['feature_columns']
        self.heat_classes = self.bundle.get('heat_classes', list(HEAT_CLASSES.values()))

        # Initialize SHAP explainer
        if HAS_SHAP:
            self.explainer = shap.TreeExplainer(self.reg_model)
        else:
            self.explainer = None
            print('[WARN] SHAP not available. Using feature importance only.')

    def explain_pixel(self, features: pd.Series) -> PixelExplanation:
        """Generate a complete explanation for a single pixel."""

        # Ensure correct feature order
        X = features[self.feature_cols].values.reshape(1, -1)
        X_df = pd.DataFrame(X, columns=self.feature_cols)

        # Predict
        heat_score = float(self.reg_model.predict(X_df)[0])
        heat_class_id = int(self.cls_model.predict(X_df)[0])
        heat_class = HEAT_CLASSES.get(heat_class_id, 'Unknown')

        # Get feature values
        feat_vals = {col: float(features[col]) for col in self.feature_cols
                     if col in features.index}

        # SHAP values
        shap_vals = {}
        base_value = heat_score  # fallback
        if self.explainer:
            sv = self.explainer.shap_values(X_df)
            ev = self.explainer.expected_value
            base_value = float(np.atleast_1d(ev)[0])
            # Handle nested arrays from some model types
            if isinstance(sv, list):
                sv = sv[0]
            sv_arr = np.array(sv).flatten()
            for i, col in enumerate(self.feature_cols):
                if i < len(sv_arr):
                    shap_vals[col] = float(sv_arr[i])

        # Contribution percentages
        total_abs = sum(abs(v) for v in shap_vals.values()) if shap_vals else 1
        contrib_pct = {}
        if total_abs > 0:
            contrib_pct = {k: abs(v) / total_abs * 100
                           for k, v in shap_vals.items()}

        # Sort by contribution
        sorted_contribs = sorted(contrib_pct.items(), key=lambda x: x[1], reverse=True)

        # Generate natural language explanation
        top_causes = []
        for feat_name, pct in sorted_contribs[:8]:
            if pct < 2:
                break
            shap_val = shap_vals.get(feat_name, 0)
            feat_val = feat_vals.get(feat_name, 0)
            desc = FEATURE_DESCRIPTIONS.get(feat_name, {})

            if shap_val > 0:  # Contributing to HIGHER heat
                cause = desc.get('cause_high', f'high {feat_name}')
                level = 'high' if feat_val > 0 else 'elevated'
            else:  # Contributing to LOWER heat
                cause = desc.get('cause_low', f'low {feat_name}')
                level = 'low'

            readable_name = desc.get('name', feat_name)
            direction = 'increases' if shap_val > 0 else 'decreases'
            top_causes.append(
                f'{readable_name} ({pct:.1f}%): {cause}'
            )

        # Build full explanation
        explanation = self._build_explanation(
            heat_score, heat_class, top_causes, feat_vals, shap_vals)
        recommendation = self._build_recommendation(
            heat_class, feat_vals, shap_vals, sorted_contribs)

        return PixelExplanation(
            pixel_id=int(features.get('PixelID', 0)),
            latitude=float(features.get('Latitude', 0)),
            longitude=float(features.get('Longitude', 0)),
            heat_score=heat_score,
            heat_class=heat_class,
            heat_class_id=heat_class_id,
            feature_values=feat_vals,
            shap_values=shap_vals,
            shap_base_value=base_value,
            contributions_pct=dict(sorted_contribs),
            top_causes=top_causes,
            explanation_text=explanation,
            recommendation=recommendation,
        )

    def _build_explanation(self, score, cls, causes, feats, shap_vals):
        """Generate natural language explanation paragraph."""
        lines = []
        lines.append(f'This location has a Heat Score of {score:.1f}/100, '
                      f'classified as "{cls}" heat stress.')
        lines.append('')

        cls_desc = HEAT_CLASS_DESCRIPTIONS.get(cls, '')
        if cls_desc:
            lines.append(f'Assessment: {cls_desc}')
            lines.append('')

        if causes:
            lines.append('Primary causes of heat stress at this location:')
            for i, cause in enumerate(causes, 1):
                lines.append(f'  {i}. {cause}')
            lines.append('')

        # Add key feature values
        key_feats = {
            'UHI_Intensity': ('UHI Intensity', 'C above rural'),
            'NDBI': ('Built-up Index', ''),
            'Anthropogenic_Heat': ('Anthropogenic Heat', 'index'),
            'Building_Density': ('Building Density', '%'),
            'Population_Density': ('Population', 'people/pixel'),
        }
        feat_summary = []
        for feat, (label, unit) in key_feats.items():
            if feat in feats:
                val = feats[feat]
                feat_summary.append(f'{label}: {val:.2f} {unit}')
        if feat_summary:
            lines.append('Key measurements: ' + ' | '.join(feat_summary))

        return '\n'.join(lines)

    def _build_recommendation(self, cls, feats, shap_vals, sorted_contribs):
        """Generate cooling intervention recommendations based on causes."""
        recs = []

        if cls in ('High', 'Extreme'):
            recs.append('PRIORITY INTERVENTION AREA')
            recs.append('')

        # Check specific features and recommend accordingly
        for feat_name, pct in sorted_contribs[:5]:
            shap_val = shap_vals.get(feat_name, 0)
            if shap_val <= 0:
                continue  # Only recommend for heat-contributing features

            if feat_name in ('NDBI', 'Building_Density', 'Impervious_Frac'):
                recs.append('- Install cool/green roofs on buildings')
                recs.append('- Use high-albedo (light-colored) pavement materials')
            elif feat_name in ('NDVI', 'SAVI', 'Tree_Cover_Pct', 'Green_Space_Density'):
                recs.append('- Plant shade trees along streets and in open lots')
                recs.append('- Create pocket parks and vertical gardens')
            elif feat_name == 'Dist_Green':
                recs.append('- Establish new green corridors connecting to nearest park')
            elif feat_name == 'Dist_Water':
                recs.append('- Install urban water features (fountains, misting stations)')
            elif feat_name in ('Anthropogenic_Heat', 'Population_Density'):
                recs.append('- Improve building energy efficiency to reduce waste heat')
                recs.append('- Promote district cooling systems')
            elif feat_name == 'WindSpeed':
                recs.append('- Design wind corridors in urban planning')
                recs.append('- Avoid constructing tall buildings perpendicular to prevailing wind')
            elif feat_name == 'Albedo':
                recs.append('- Apply reflective coatings on rooftops and roads')
            elif feat_name in ('Road_Density_Proxy', 'Street_Width_Proxy'):
                recs.append('- Add tree-lined medians and permeable pavements')

        # Deduplicate
        seen = set()
        unique_recs = []
        for r in recs:
            if r not in seen:
                unique_recs.append(r)
                seen.add(r)

        return '\n'.join(unique_recs) if unique_recs else 'No specific interventions needed.'

    # ========================================================================
    # VISUALIZATION
    # ========================================================================

    def plot_waterfall(self, expl: PixelExplanation, save_path: str):
        """Publication-quality SHAP waterfall chart."""
        if not expl.shap_values:
            return

        # Sort by absolute SHAP value
        sorted_feats = sorted(expl.shap_values.items(),
                              key=lambda x: abs(x[1]), reverse=True)[:15]

        feats = [f[0] for f in reversed(sorted_feats)]
        vals = [f[1] for f in reversed(sorted_feats)]
        colors = ['#d73027' if v > 0 else '#4575b4' for v in vals]

        # Readable names
        labels = []
        for f in feats:
            desc = FEATURE_DESCRIPTIONS.get(f, {})
            name = desc.get('name', f)
            val = expl.feature_values.get(f, 0)
            labels.append(f'{name}\n= {val:.2f}')

        fig, ax = plt.subplots(figsize=(10, 8))
        bars = ax.barh(range(len(feats)), vals, color=colors, height=0.7,
                       edgecolor='white', linewidth=0.5)

        ax.set_yticks(range(len(feats)))
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel('SHAP Value (impact on Heat Score)', fontsize=11, fontweight='bold')
        ax.set_title(f'Why Is This Location {"Hot" if expl.heat_score > 50 else "Cool"}?\n'
                     f'Heat Score: {expl.heat_score:.1f}/100 | '
                     f'Class: {expl.heat_class}',
                     fontsize=13, fontweight='bold')

        # Add value labels
        for bar, val in zip(bars, vals):
            x_pos = bar.get_width()
            ha = 'left' if val >= 0 else 'right'
            offset = 0.3 if val >= 0 else -0.3
            ax.text(x_pos + offset, bar.get_y() + bar.get_height()/2,
                    f'{val:+.2f}', va='center', ha=ha, fontsize=8, fontweight='bold')

        # Legend
        hot_patch = mpatches.Patch(color='#d73027', label='Increases heat')
        cool_patch = mpatches.Patch(color='#4575b4', label='Decreases heat')
        ax.legend(handles=[hot_patch, cool_patch], loc='lower right', fontsize=10)

        ax.axvline(x=0, color='black', linewidth=0.8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        plt.tight_layout()
        plt.savefig(save_path, dpi=200, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

    def plot_contribution_pie(self, expl: PixelExplanation, save_path: str):
        """Publication-quality contribution percentage pie chart."""
        sorted_c = sorted(expl.contributions_pct.items(),
                          key=lambda x: x[1], reverse=True)

        # Top 8 + "Other"
        top = sorted_c[:8]
        other = sum(v for _, v in sorted_c[8:])
        if other > 0:
            top.append(('Other', other))

        labels = []
        for f, pct in top:
            desc = FEATURE_DESCRIPTIONS.get(f, {})
            labels.append(desc.get('name', f))
        sizes = [v for _, v in top]

        # Colors: warm palette for heat-increasing, cool for decreasing
        cmap = plt.cm.RdYlBu_r
        colors = [cmap(i / len(top)) for i in range(len(top))]

        fig, ax = plt.subplots(figsize=(9, 7))
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            colors=colors, startangle=140,
            pctdistance=0.82, labeldistance=1.08,
            wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
        )

        for text in texts:
            text.set_fontsize(9)
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_fontweight('bold')

        ax.set_title(f'Feature Contribution to Heat Score\n'
                     f'Pixel ({expl.latitude:.4f}, {expl.longitude:.4f}) | '
                     f'Score: {expl.heat_score:.1f}',
                     fontsize=13, fontweight='bold')

        plt.tight_layout()
        plt.savefig(save_path, dpi=200, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

    def plot_contribution_bars(self, expl: PixelExplanation, save_path: str):
        """Horizontal bar chart of feature contributions with percentages."""
        sorted_c = sorted(expl.contributions_pct.items(),
                          key=lambda x: x[1], reverse=True)[:12]

        feats = [f[0] for f in reversed(sorted_c)]
        pcts = [f[1] for f in reversed(sorted_c)]

        # Color by direction
        colors = []
        for f in feats:
            sv = expl.shap_values.get(f, 0)
            colors.append('#d73027' if sv > 0 else '#4575b4')

        labels = []
        for f in feats:
            desc = FEATURE_DESCRIPTIONS.get(f, {})
            labels.append(desc.get('name', f))

        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.barh(range(len(feats)), pcts, color=colors, height=0.7,
                       edgecolor='white', linewidth=0.5)

        ax.set_yticks(range(len(feats)))
        ax.set_yticklabels(labels, fontsize=10)
        ax.set_xlabel('Contribution to Heat Score (%)', fontsize=11, fontweight='bold')
        ax.set_title(f'Feature Contribution Analysis\n'
                     f'Heat Score: {expl.heat_score:.1f}/100 | '
                     f'Class: {expl.heat_class}',
                     fontsize=13, fontweight='bold')

        # Add percentage labels
        for bar, pct in zip(bars, pcts):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                    f'{pct:.1f}%', va='center', fontsize=9, fontweight='bold')

        hot_patch = mpatches.Patch(color='#d73027', label='Heating effect')
        cool_patch = mpatches.Patch(color='#4575b4', label='Cooling effect')
        ax.legend(handles=[hot_patch, cool_patch], loc='lower right', fontsize=10)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_xlim(0, max(pcts) * 1.15)

        plt.tight_layout()
        plt.savefig(save_path, dpi=200, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

    def plot_decision_summary(self, expl: PixelExplanation, save_path: str):
        """Publication-quality decision summary infographic."""
        fig = plt.figure(figsize=(14, 10))
        gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

        cls_color = HEAT_CLASS_COLORS.get(expl.heat_class, '#333333')

        # --- Panel 1: Heat Score gauge ---
        ax1 = fig.add_subplot(gs[0, 0])
        theta = np.linspace(0, np.pi, 100)
        # Background arc
        for i, (cls_name, color) in enumerate(HEAT_CLASS_COLORS.items()):
            start = i * np.pi / 4
            end = (i + 1) * np.pi / 4
            t = np.linspace(start, end, 25)
            ax1.plot(np.cos(t), np.sin(t), color=color, linewidth=12, solid_capstyle='butt')

        # Needle
        needle_angle = np.pi * (1 - expl.heat_score / 100)
        ax1.annotate('', xy=(0.7*np.cos(needle_angle), 0.7*np.sin(needle_angle)),
                     xytext=(0, 0),
                     arrowprops=dict(arrowstyle='->', color='black', lw=2.5))

        ax1.text(0, -0.15, f'{expl.heat_score:.1f}', fontsize=28, fontweight='bold',
                ha='center', va='center', color=cls_color)
        ax1.text(0, -0.35, expl.heat_class.upper(), fontsize=14, fontweight='bold',
                ha='center', va='center', color=cls_color)
        ax1.text(-1, -0.05, '0', fontsize=10, ha='center')
        ax1.text(1, -0.05, '100', fontsize=10, ha='center')
        ax1.set_xlim(-1.3, 1.3)
        ax1.set_ylim(-0.5, 1.2)
        ax1.set_aspect('equal')
        ax1.axis('off')
        ax1.set_title('Heat Stress Score', fontsize=13, fontweight='bold', pad=15)

        # --- Panel 2: Top contributors ---
        ax2 = fig.add_subplot(gs[0, 1])
        sorted_c = sorted(expl.contributions_pct.items(),
                          key=lambda x: x[1], reverse=True)[:8]
        y_pos = range(len(sorted_c))
        feats = [FEATURE_DESCRIPTIONS.get(f, {}).get('name', f) for f, _ in sorted_c]
        pcts = [p for _, p in sorted_c]
        bar_colors = ['#d73027' if expl.shap_values.get(f, 0) > 0 else '#4575b4'
                      for f, _ in sorted_c]

        ax2.barh(range(len(feats)-1, -1, -1), pcts, color=bar_colors, height=0.6)
        ax2.set_yticks(range(len(feats)-1, -1, -1))
        ax2.set_yticklabels(feats, fontsize=9)
        for i, (_, pct) in enumerate(sorted_c):
            ax2.text(pct + 0.5, len(feats)-1-i, f'{pct:.1f}%',
                    va='center', fontsize=8, fontweight='bold')
        ax2.set_xlabel('Contribution %', fontsize=10)
        ax2.set_title('Top Contributing Factors', fontsize=13, fontweight='bold')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)

        # --- Panel 3: Key measurements ---
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.axis('off')
        key_measures = [
            ('UHI_Intensity', 'UHI Intensity', 'C'),
            ('Anthropogenic_Heat', 'Anthro. Heat', ''),
            ('Building_Density', 'Building Dens.', '%'),
            ('NDBI', 'Built-up Index', ''),
            ('Population_Density', 'Population', '/px'),
            ('Nighttime_Lights', 'Night Lights', 'nW'),
            ('Dist_Green', 'Dist. to Green', 'm'),
            ('WindSpeed', 'Wind Speed', 'm/s'),
        ]
        table_data = []
        for feat, label, unit in key_measures:
            val = expl.feature_values.get(feat, 0)
            shap = expl.shap_values.get(feat, 0)
            direction = '+' if shap > 0 else '-'
            table_data.append([label, f'{val:.2f} {unit}', f'{direction}{abs(shap):.2f}'])

        table = ax3.table(cellText=table_data,
                          colLabels=['Feature', 'Value', 'SHAP'],
                          loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.4)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor('#2c3e50')
                cell.set_text_props(color='white', fontweight='bold')
            elif col == 2:
                val = table_data[row-1][2]
                cell.set_facecolor('#fde0dd' if val.startswith('+') else '#d4e6f1')
        ax3.set_title('Key Measurements & SHAP Impact', fontsize=13,
                      fontweight='bold', pad=15)

        # --- Panel 4: Explanation text ---
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.axis('off')
        # Wrap text
        cause_text = '\n'.join(expl.top_causes[:5]) if expl.top_causes else 'No significant causes.'
        ax4.text(0.05, 0.95, 'Primary Heat Causes:', fontsize=12, fontweight='bold',
                transform=ax4.transAxes, va='top')
        ax4.text(0.05, 0.85, cause_text, fontsize=9,
                transform=ax4.transAxes, va='top', wrap=True,
                linespacing=1.6)

        # Coordinates
        fig.text(0.5, 0.01,
                 f'Location: ({expl.latitude:.4f}, {expl.longitude:.4f}) | '
                 f'Urban Heat AI - ISRO Hackathon',
                 fontsize=9, ha='center', style='italic', color='#666666')

        plt.savefig(save_path, dpi=200, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

    def generate_full_report(self, expl: PixelExplanation, output_dir: str,
                              prefix: str = 'pixel') -> Dict[str, str]:
        """Generate all charts and text for a single pixel."""
        os.makedirs(output_dir, exist_ok=True)

        paths = {}

        # Waterfall
        p = os.path.join(output_dir, f'{prefix}_waterfall.png')
        self.plot_waterfall(expl, p)
        paths['waterfall'] = p

        # Contribution bars
        p = os.path.join(output_dir, f'{prefix}_contributions.png')
        self.plot_contribution_bars(expl, p)
        paths['contributions'] = p

        # Pie chart
        p = os.path.join(output_dir, f'{prefix}_pie.png')
        self.plot_contribution_pie(expl, p)
        paths['pie'] = p

        # Decision summary
        p = os.path.join(output_dir, f'{prefix}_summary.png')
        self.plot_decision_summary(expl, p)
        paths['summary'] = p

        # JSON explanation
        p = os.path.join(output_dir, f'{prefix}_explanation.json')
        with open(p, 'w') as f:
            json.dump(expl.to_dict(), f, indent=2)
        paths['json'] = p

        return paths
